"""Chaîne d'intégrité du registre sécurité/santé (Art. L.414-14).

Modèle de preuve (v2026.09.004) :

1. JOURNAL APPEND-ONLY — chaque action sur le registre (create / countersign /
   void) écrit un SafetyRegisterEvent. Un événement n'est jamais modifié ni
   supprimé.
2. CHAÎNE SHA-256 — chaque événement est haché :
       event_hash = sha256_hex(prev_hash + "|" + payload_json)
   prev_hash = event_hash de l'événement précédent de la MÊME organisation
   ("0"*64 pour le premier). Toute altération du payload, du hash ou toute
   suppression d'un maillon casse la chaîne — détectable par simple recalcul
   (endpoint /api/safety-register/integrity, page publique /verify).
3. PROJECTION VÉRIFIABLE — la table safety_register_entries est rejouable à
   partir du journal : le rapport d'intégrité compare l'état attendu (replay)
   à l'état en base, ce qui détecte une modification directe de la table.
4. SCEAUX — un sceau fige {event_count, head_hash} à un instant donné ; il est
   horodaté RFC 3161 (jeton vérifiable hors de l'application, openssl) et
   envoyé par email au bureau (copie externe). Un passé réécrit en base ne
   peut pas reproduire les sceaux déjà émis.

Limites honnêtes : la chaîne protège à partir de son activation ; contre un
administrateur qui réécrirait TOUTE la base, ce sont les sceaux externes
(email + jeton RFC 3161) qui constituent la preuve opposable.

Note concurrence : uvicorn tourne en un seul worker, SQLite sérialise les
écritures — l'ajout d'un événement suit immédiatement la lecture du dernier
hash dans la même transaction (commit par l'appelant).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.safety_register import SafetyRegisterEntry, SafetyRegisterEvent, SafetyRegisterSeal

GENESIS = "0" * 64
HASH_RULE = "sha256_hex(prev_hash + '|' + payload_json_utf8)"
# Autorités d'horodatage RFC 3161 (sans authentification). Surcharge : SD_TSA_URL ;
# désactivation : SD_TSA_DISABLED=1.
DEFAULT_TSA_URLS = [
    "http://timestamp.digicert.com",
    "http://timestamp.sectigo.com",
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def canonical_json(obj: dict) -> str:
    """Sérialisation canonique (clés triées, séparateurs compacts, ASCII)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_event_hash(prev_hash: str, payload_json: str) -> str:
    return sha256_hex(prev_hash + "|" + payload_json)


# ─────────────────────────────────────────────── journal (append-only)


def last_event(db: Session, org_id: int) -> Optional[SafetyRegisterEvent]:
    return (
        db.query(SafetyRegisterEvent)
        .filter(SafetyRegisterEvent.organization_id == org_id)
        .order_by(SafetyRegisterEvent.id.desc())
        .first()
    )


def append_event(
    db: Session,
    *,
    org_id: int,
    entry_id: Optional[int],
    action: str,
    actor,
    data: dict,
    at: Optional[datetime] = None,
) -> SafetyRegisterEvent:
    """Ajoute un maillon à la chaîne. Ne commite PAS (transaction de l'appelant)."""
    at = at or now_utc()
    payload = {"action": action, "entry_id": entry_id, "at": at.isoformat(), **data}
    payload_json = canonical_json(payload)
    prev = last_event(db, org_id)
    prev_hash = prev.event_hash if prev else GENESIS
    ev = SafetyRegisterEvent(
        organization_id=org_id,
        entry_id=entry_id,
        action=action,
        actor_id=getattr(actor, "id", None),
        actor_name=(getattr(actor, "full_name", None) or getattr(actor, "email", None)) if actor else None,
        at=at,
        payload_json=payload_json,
        prev_hash=prev_hash,
        event_hash=compute_event_hash(prev_hash, payload_json),
    )
    db.add(ev)
    db.flush()
    return ev


# ─────────────────────────────────────────────── vérification


def check_chain(events: list[SafetyRegisterEvent]) -> dict:
    """Recalcule la chaîne. Retourne {ok, checked, first_broken_index, first_broken_event_id}."""
    prev = GENESIS
    for idx, ev in enumerate(events):
        if ev.prev_hash != prev or ev.event_hash != compute_event_hash(ev.prev_hash, ev.payload_json):
            return {"ok": False, "checked": idx, "first_broken_index": idx, "first_broken_event_id": ev.id}
        prev = ev.event_hash
    return {"ok": True, "checked": len(events), "first_broken_index": None, "first_broken_event_id": None}


def replay_entries(events: list[SafetyRegisterEvent]) -> dict[int, dict]:
    """Rejoue le journal → état attendu de chaque entrée (projection)."""
    states: dict[int, dict] = {}
    for ev in events:
        try:
            p = json.loads(ev.payload_json)
        except (ValueError, TypeError):
            continue
        eid = p.get("entry_id")
        if eid is None:
            continue
        st = states.setdefault(eid, {})
        action = p.get("action")
        if action == "create":
            st["entry_date"] = p.get("entry_date")
            st["location"] = p.get("location", "")
            st["description"] = p.get("description", "")
            st["status"] = "pending"
            st["chef_service_name"] = ""
            st["countersigned_at"] = None
            st["void_reason"] = ""
            st["voided_at"] = None
        elif action == "countersign":
            st["status"] = "countersigned"
            st["chef_service_name"] = p.get("chef_service_name", "")
            st["countersigned_at"] = p.get("countersigned_at")
        elif action == "void":
            st["status"] = "voided"
            st["void_reason"] = p.get("reason", "")
            st["voided_at"] = p.get("voided_at")
    return states


def _entry_actual(e: SafetyRegisterEntry) -> dict:
    return {
        "entry_date": e.entry_date.isoformat() if e.entry_date else None,
        "location": e.location or "",
        "description": e.description or "",
        "status": e.status,
        "chef_service_name": e.chef_service_name or "",
        "countersigned_at": e.countersigned_at.isoformat() if e.countersigned_at else None,
        "void_reason": e.void_reason or "",
        "voided_at": e.voided_at.isoformat() if e.voided_at else None,
    }


_VERIFIED_FIELDS = (
    "entry_date", "location", "description", "status",
    "chef_service_name", "countersigned_at", "void_reason", "voided_at",
)


def verify_org(db: Session, org_id: int) -> dict:
    """Vérifie chaîne + projection + sceaux pour une organisation."""
    events = (
        db.query(SafetyRegisterEvent)
        .filter(SafetyRegisterEvent.organization_id == org_id)
        .order_by(SafetyRegisterEvent.id.asc())
        .all()
    )
    chain = check_chain(events)
    states = replay_entries(events)
    mismatches: list[dict] = []
    entries = (
        db.query(SafetyRegisterEntry)
        .filter(SafetyRegisterEntry.organization_id == org_id)
        .order_by(SafetyRegisterEntry.id.asc())
        .all()
    )
    for e in entries:
        expected = states.get(e.id)
        if expected is None:
            mismatches.append({"entry_id": e.id, "field": "*", "expected": "(aucun événement)",
                               "actual": "(entrée présente en base)"})
            continue
        actual = _entry_actual(e)
        for f in _VERIFIED_FIELDS:
            if str(expected.get(f)) != str(actual.get(f)):
                mismatches.append({
                    "entry_id": e.id, "field": f,
                    "expected": str(expected.get(f))[:120], "actual": str(actual.get(f))[:120],
                })

    seals = (
        db.query(SafetyRegisterSeal)
        .filter(SafetyRegisterSeal.organization_id == org_id)
        .order_by(SafetyRegisterSeal.id.asc())
        .all()
    )
    broken_seals: list[int] = []
    for s in seals:
        if s.event_count == 0:
            expected_head = GENESIS
        elif s.event_count <= len(events):
            expected_head = events[s.event_count - 1].event_hash
        else:
            expected_head = None
        ok = expected_head == s.head_hash and f"head_hash: {s.head_hash}" in (s.manifest or "")
        if not ok:
            broken_seals.append(s.id)

    head = events[-1].event_hash if events else None
    ok = chain["ok"] and not mismatches and not broken_seals
    return {
        "ok": ok,
        "event_count": len(events),
        "head_hash": head,
        "last_event_at": events[-1].at.isoformat() if events else None,
        "chain_ok": chain["ok"],
        "first_broken_index": chain["first_broken_index"],
        "first_broken_event_id": chain["first_broken_event_id"],
        "projection_ok": not mismatches,
        "projection_mismatches": mismatches,
        "seals_ok": not broken_seals,
        "seals_checked": len(seals),
        "broken_seals": broken_seals,
    }


def entry_hashes(events: list[SafetyRegisterEvent]) -> dict[int, str]:
    """Dernier hash de chaîne par entrée (pour affichage/export)."""
    out: dict[int, str] = {}
    for ev in events:
        try:
            eid = json.loads(ev.payload_json).get("entry_id")
        except (ValueError, TypeError):
            eid = None
        if eid is not None:
            out[eid] = ev.event_hash
    return out


def integrity_report(db: Session, org: Organization) -> dict:
    """Dossier d'intégrité complet (fichier .json remis à l'ITM / page /verify).

    Contient l'état du registre, le journal complet (chaîne), les sceaux
    (avec jetons RFC 3161) et le résultat de vérification au moment de
    l'export. C'est LE document qui permet à un tiers de recalculer tout.
    """
    events = (
        db.query(SafetyRegisterEvent)
        .filter(SafetyRegisterEvent.organization_id == org.id)
        .order_by(SafetyRegisterEvent.id.asc())
        .all()
    )
    entries = (
        db.query(SafetyRegisterEntry)
        .filter(SafetyRegisterEntry.organization_id == org.id)
        .order_by(SafetyRegisterEntry.id.asc())
        .all()
    )
    seals = (
        db.query(SafetyRegisterSeal)
        .filter(SafetyRegisterSeal.organization_id == org.id)
        .order_by(SafetyRegisterSeal.id.asc())
        .all()
    )
    hashes = entry_hashes(events)
    return {
        "format": "delegatum-safety-register-integrity",
        "version": 1,
        "generated_at": now_utc().isoformat(),
        "organization": {"id": org.id, "name": org.name},
        "chain": {
            "algorithm": "sha256",
            "genesis": GENESIS,
            "hash_rule": HASH_RULE,
            "event_count": len(events),
            "head_hash": events[-1].event_hash if events else None,
        },
        "entries": [
            {
                "id": e.id,
                "entry_date": e.entry_date.isoformat() if e.entry_date else None,
                "location": e.location or "",
                "description": e.description or "",
                "status": e.status,
                "chef_service_name": e.chef_service_name or "",
                "countersigned_at": e.countersigned_at.isoformat() if e.countersigned_at else None,
                "voided_at": e.voided_at.isoformat() if e.voided_at else None,
                "void_reason": e.void_reason or "",
                "delegate_name": e.delegate.full_name if e.delegate else "",
                "created_by_name": e.created_by.full_name if e.created_by else "",
                "event_hash": hashes.get(e.id),
            }
            for e in entries
        ],
        "events": [
            {
                "id": ev.id,
                "entry_id": ev.entry_id,
                "action": ev.action,
                "actor_name": ev.actor_name or "",
                "at": ev.at.isoformat() if ev.at else None,
                "payload_json": ev.payload_json,
                "prev_hash": ev.prev_hash,
                "event_hash": ev.event_hash,
            }
            for ev in events
        ],
        "seals": [
            {
                "id": s.id,
                "sealed_at": s.sealed_at.isoformat() if s.sealed_at else None,
                "event_count": s.event_count,
                "head_hash": s.head_hash,
                "manifest": s.manifest,
                "tsa_status": s.tsa_status,
                "tsa_url": s.tsa_url,
                "tsa_token_b64": s.tsa_token_b64,
                "auto": bool(s.auto),
            }
            for s in seals
        ],
        "verification": verify_org(db, org.id),
    }


# ─────────────────────────────────────────────── sceaux + horodatage


def build_manifest(org: Organization, event_count: int, head_hash: str, sealed_at: datetime) -> str:
    """Texte exact qui sera horodaté (RFC 3161) et conservé avec le sceau."""
    return (
        "DELEGATUM SAFETY REGISTER v1\n"
        f"org_id: {org.id}\n"
        f"org_name: {org.name}\n"
        f"events: {event_count}\n"
        f"head_hash: {head_hash}\n"
        f"sealed_at: {sealed_at.isoformat()}\n"
    )


def _tsa_urls() -> list[str]:
    override = os.environ.get("SD_TSA_URL")
    if override:
        return [override]
    return list(DEFAULT_TSA_URLS)


def tsa_stamp(manifest: str) -> tuple[str, Optional[str], Optional[str]]:
    """Horodate le manifeste via RFC 3161. Retourne (status, url, token_b64).

    status ∈ {ok, failed, unavailable, disabled}. Jamais d'exception : un TSA
    injoignable ne doit pas empêcher la création du sceau.
    """
    if os.environ.get("SD_TSA_DISABLED") == "1":
        return ("disabled", None, None)
    if shutil.which("openssl") is None:
        return ("unavailable", None, None)
    try:
        with tempfile.TemporaryDirectory() as td:
            mpath = Path(td) / "manifest.txt"
            mpath.write_bytes(manifest.encode("utf-8"))
            qpath = Path(td) / "req.tsq"
            proc = subprocess.run(
                ["openssl", "ts", "-query", "-data", str(mpath), "-sha256", "-cert", "-out", str(qpath)],
                capture_output=True, timeout=20,
            )
            if proc.returncode != 0 or not qpath.exists():
                return ("failed", None, None)
            tsq = qpath.read_bytes()
    except Exception:  # noqa: BLE001
        return ("failed", None, None)

    import httpx  # dépendance applicative (requirements.txt)

    for url in _tsa_urls():
        try:
            resp = httpx.post(
                url,
                content=tsq,
                headers={"Content-Type": "application/timestamp-query", "Accept": "application/timestamp-reply"},
                timeout=12.0,
                follow_redirects=True,
            )
            if resp.status_code == 200 and resp.content:
                return ("ok", url, base64.b64encode(resp.content).decode("ascii"))
        except Exception:  # noqa: BLE001
            continue
    return ("failed", _tsa_urls()[-1], None)


_TSA_NOTES = {
    "fr": {
        "ok": "Horodatage RFC 3161 : ✓ ({url}) — le jeton d'horodatage est inclus dans l'export du registre.",
        "ko": "Horodatage RFC 3161 : indisponible pour ce sceau (l'empreinte ci-dessus reste valable et conservée dans cet email).",
    },
    "en": {
        "ok": "RFC 3161 timestamp: ✓ ({url}) — the timestamp token is included in the register export.",
        "ko": "RFC 3161 timestamp: unavailable for this seal (the fingerprint above remains valid and is kept in this email).",
    },
    "de": {
        "ok": "RFC-3161-Zeitstempel: ✓ ({url}) — das Zeitstempel-Token ist im Registerexport enthalten.",
        "ko": "RFC-3161-Zeitstempel: für dieses Siegel nicht verfügbar (der obige Fingerabdruck bleibt gültig und ist in dieser E-Mail enthalten).",
    },
    "pt": {
        "ok": "Carimbo temporal RFC 3161: ✓ ({url}) — o token está incluído na exportação do registo.",
        "ko": "Carimbo temporal RFC 3161: indisponível para este selo (a impressão digital acima continua válida e fica neste email).",
    },
}


def tsa_note(lang: str, status: str, url: Optional[str]) -> str:
    notes = _TSA_NOTES.get(lang, _TSA_NOTES["fr"])
    if status == "ok":
        return notes["ok"].format(url=url or "")
    if status == "disabled":
        return {"fr": "Horodatage RFC 3161 : désactivé sur cette instance.",
                "en": "RFC 3161 timestamp: disabled on this instance.",
                "de": "RFC-3161-Zeitstempel: auf dieser Instanz deaktiviert.",
                "pt": "Carimbo temporal RFC 3161: desativado nesta instância."}.get(lang, "Horodatage RFC 3161 : désactivé.")
    return notes["ko"]


def create_seal(db: Session, org: Organization, actor=None, auto: bool = False, do_tsa: bool = True) -> tuple[SafetyRegisterSeal, int]:
    """Fige l'état de la chaîne, l'horodate et prévient le bureau. Retourne (sceau, emails en file)."""
    events = (
        db.query(SafetyRegisterEvent)
        .filter(SafetyRegisterEvent.organization_id == org.id)
        .order_by(SafetyRegisterEvent.id.asc())
        .all()
    )
    count = len(events)
    head = events[-1].event_hash if events else GENESIS
    sealed_at = now_utc()
    manifest = build_manifest(org, count, head, sealed_at)
    if do_tsa:
        status, url, token = tsa_stamp(manifest)
    else:
        status, url, token = ("none", None, None)
    seal = SafetyRegisterSeal(
        organization_id=org.id,
        sealed_at=sealed_at,
        event_count=count,
        head_hash=head,
        manifest=manifest,
        tsa_status=status,
        tsa_url=url,
        tsa_token_b64=token,
        auto=auto,
        created_by_id=getattr(actor, "id", None),
    )
    db.add(seal)
    db.commit()
    db.refresh(seal)

    # Notification au bureau + admin (copie externe du sceau)
    queued = 0
    try:
        from app.models.email import EmailEventType
        from app.models.user import DelegueRole, User
        from app.services.email_service import queue_email

        base_url = os.environ.get("SD_BASE_URL", "")
        bureau = db.query(User).filter(
            User.organization_id == org.id,
            User.is_active == True,  # noqa: E712
            (User.role == "admin") | (User.delegue_role.in_([DelegueRole.president, DelegueRole.vice_president, DelegueRole.secretaire])),
        ).all()
        for u in bureau:
            if not u.email:
                continue
            lang = u.language or "fr"
            ctx = {
                "recipient_name": u.full_name or u.email,
                "sealed_at": sealed_at.isoformat(timespec="seconds"),
                "event_count": count,
                "head_hash": head,
                "head_short": head[:16],
                "tsa_note": tsa_note(lang, status, url),
                "register_url": f"{base_url}/safety-register" if base_url else "",
                "base_url": base_url,
            }
            if queue_email(db, org.id, EmailEventType.register_seal.value, u.full_name, u.email, lang, ctx):
                queued += 1
    except Exception as e:  # noqa: BLE001 — un email raté ne remet pas le sceau en cause
        print(f"[register-seal] notification ignorée : {e}")
    return seal, queued


def auto_seal_all(db: Session, base_url: str = "") -> tuple[int, int]:
    """Scelle chaque organisation dont le registre a des événements NON scellés.

    Idempotent : ne crée un sceau que si le nombre d'événements a augmenté
    depuis le dernier sceau. Retourne (nb de sceaux créés, nb d'emails en file).
    """
    seals_created = emails = 0
    orgs = db.query(Organization).all()
    for org in orgs:
        count = (
            db.query(SafetyRegisterEvent)
            .filter(SafetyRegisterEvent.organization_id == org.id)
            .count()
        )
        if count == 0:
            continue
        last = (
            db.query(SafetyRegisterSeal)
            .filter(SafetyRegisterSeal.organization_id == org.id)
            .order_by(SafetyRegisterSeal.id.desc())
            .first()
        )
        if last is not None and last.event_count >= count:
            continue
        _, queued = create_seal(db, org, actor=None, auto=True)
        seals_created += 1
        emails += queued
    return seals_created, emails
