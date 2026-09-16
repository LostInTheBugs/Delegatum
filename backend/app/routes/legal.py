"""Chantier C — congé-formation (L.415-9), registre sécurité/santé (L.414-14),
périodes protégées (L.415-10/11).

Registre sécurité/santé (v2026.09.004) : journal append-only chaîné SHA-256
(create / countersign / void), annulation motivée au lieu de la suppression,
exports ITM (CSV + dossier d'intégrité JSON) et sceaux horodatés RFC 3161.
Logique de chaîne : app/services/register_chain.py ; vérification publique : /verify.
"""

import csv
import io
import json
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_module
from app.models import (
    Organization,
    SafetyRegisterEntry,
    SafetyRegisterEvent,
    SafetyRegisterSeal,
    User,
)
from app.models.election import Election, ElectionStatus
from app.models.time_entry import TimeEntry
from app.services import register_chain

router = APIRouter(prefix="/api", tags=["legal"], dependencies=[Depends(require_module("legal"))])

WORK_HOURS_PER_WEEK = 40  # base conventionnelle : 1 semaine = 40 h
PRIMO_BONUS_HOURS = 16  # L.415-9(3) : +16 h pour les primo-élus


def formation_entitlement_hours(org: Organization, user: User) -> int:
    """Droit de congé-formation (L.415-9) en heures, par membre.

    15-49 salariés : 1 semaine par mandat · 50-150 : 2 semaines par mandat
    · >150 : 1 semaine par an. Primo-élus : +16 h. Suppléants : moitié.
    """
    n = org.employee_count or 0
    if n <= 49:
        base = WORK_HOURS_PER_WEEK
    elif n <= 150:
        base = 2 * WORK_HOURS_PER_WEEK
    else:
        base = WORK_HOURS_PER_WEEK  # par année
    if user.delegue_status and user.delegue_status.value == "suppleant":
        base //= 2
    if user.is_first_mandate:
        base += PRIMO_BONUS_HOURS
    return base


def _is_bureau(user: User) -> bool:
    # même prédicat que le tableau d'affichage : admin ou président/vice-président/secrétaire
    return user.role == "admin" or (
        user.delegue_role is not None and user.delegue_role.value in ("president", "vice_president", "secretaire")
    )


def _is_secu_or_bureau(user: User) -> bool:
    return _is_bureau(user) or bool(user.is_delegue_securite_sante)


# ---------------------------------------------------------------- formation


class PrimoUpdate(BaseModel):
    is_first_mandate: bool


@router.get("/formation/overview")
def formation_overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(404, "Organisation non trouvée")
    members = db.query(User).filter(
        User.organization_id == org.id, User.is_active == True  # noqa: E712
    ).all()
    year = datetime.now(timezone.utc).replace(tzinfo=None).year
    out = []
    for u in members:
        used = db.query(TimeEntry).filter(
            TimeEntry.user_id == u.id,
            TimeEntry.category == "formation",
            TimeEntry.date >= date(year, 1, 1),
            TimeEntry.date <= date(year, 12, 31),
        ).all()
        used_h = sum((t.hours or 0) for t in used)
        ent = formation_entitlement_hours(org, u)
        out.append({
            "user_id": u.id,
            "full_name": u.full_name,
            "delegue_status": u.delegue_status.value if u.delegue_status else "employe",
            "is_first_mandate": bool(u.is_first_mandate),
            "entitlement_hours": ent,
            "used_hours": round(used_h, 1),
            "remaining_hours": round(max(ent - used_h, 0), 1),
        })
    return {"year": year, "members": sorted(out, key=lambda x: x["full_name"])}


@router.put("/formation/primo/{user_id}")
def set_primo(user_id: int, body: PrimoUpdate,
              current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _is_bureau(current_user):
        raise HTTPException(403, "Réservé au bureau")
    u = db.query(User).filter(User.id == user_id, User.organization_id == current_user.organization_id).first()
    if not u:
        raise HTTPException(404, "Membre non trouvé")
    u.is_first_mandate = body.is_first_mandate
    db.commit()
    return {"ok": True, "is_first_mandate": bool(u.is_first_mandate)}


# ------------------------------------------------------- registre sécurité/santé
#
# ⚠️ Routes statiques (/integrity, /export.*, /seal) définies AVANT les routes
# dynamiques /{entry_id}/… — pitfall FastAPI déjà vécu sur ce projet.


class RegisterEntryCreate(BaseModel):
    entry_date: str = Field(min_length=8)
    location: str = Field(default="", max_length=200)
    description: str = Field(min_length=3, max_length=5000)


class RegisterCountersign(BaseModel):
    chef_service_name: str = Field(min_length=2, max_length=200)


class RegisterVoid(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


def _org_events(db: Session, org_id: int) -> list[SafetyRegisterEvent]:
    return (
        db.query(SafetyRegisterEvent)
        .filter(SafetyRegisterEvent.organization_id == org_id)
        .order_by(SafetyRegisterEvent.id.asc())
        .all()
    )


@router.get("/safety-register")
def list_register(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entries = db.query(SafetyRegisterEntry).filter(
        SafetyRegisterEntry.organization_id == current_user.organization_id
    ).order_by(SafetyRegisterEntry.entry_date.desc(), SafetyRegisterEntry.id.desc()).all()
    hashes = register_chain.entry_hashes(_org_events(db, current_user.organization_id))
    return [{
        "id": e.id,
        "entry_date": e.entry_date.isoformat(),
        "location": e.location or "",
        "description": e.description,
        "status": e.status,
        "chef_service_name": e.chef_service_name or "",
        "countersigned_at": e.countersigned_at.isoformat() if e.countersigned_at else None,
        "voided_at": e.voided_at.isoformat() if e.voided_at else None,
        "void_reason": e.void_reason or "",
        "voided_by_name": e.voided_by.full_name if e.voided_by else "",
        "delegate_name": e.delegate.full_name if e.delegate else "",
        "created_by_name": e.created_by.full_name if e.created_by else "",
        "event_hash": hashes.get(e.id),
        "can_countersign": _is_bureau(current_user),
        "can_void": _is_bureau(current_user) or (e.created_by_id == current_user.id and e.status == "pending"),
    } for e in entries]


@router.get("/safety-register/integrity")
def register_integrity(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Vérifie chaîne + projection + sceaux. ok=false = altération détectée."""
    org = db.get(Organization, current_user.organization_id)
    if not org:
        raise HTTPException(404, "Organisation non trouvée")
    report = register_chain.verify_org(db, org.id)
    seals = db.query(SafetyRegisterSeal).filter(
        SafetyRegisterSeal.organization_id == org.id
    ).order_by(SafetyRegisterSeal.id.desc()).all()
    report["seals"] = [{
        "id": s.id,
        "sealed_at": s.sealed_at.isoformat() if s.sealed_at else None,
        "event_count": s.event_count,
        "head_signature": s.head_hash[:16],
        "tsa_status": s.tsa_status,
        "auto": bool(s.auto),
    } for s in seals]
    return report


@router.get("/safety-register/export.csv")
def export_register_csv(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Export CSV du registre complet (actif + annulé) — remise possible à l'ITM."""
    entries = db.query(SafetyRegisterEntry).filter(
        SafetyRegisterEntry.organization_id == current_user.organization_id
    ).order_by(SafetyRegisterEntry.entry_date.asc(), SafetyRegisterEntry.id.asc()).all()
    hashes = register_chain.entry_hashes(_org_events(db, current_user.organization_id))
    status_labels = {"pending": "En attente", "countersigned": "Contresigné", "voided": "Annulé"}
    buf = io.StringIO()
    buf.write("\ufeff")  # BOM UTF-8 (Excel)
    writer = csv.writer(buf)
    writer.writerow([
        "Date", "Lieu", "Constatation", "Statut", "Constaté par", "Contresigné par",
        "Date contreseing", "Annulé le", "Motif annulation", "Empreinte (chaîne)",
    ])
    for e in entries:
        writer.writerow([
            e.entry_date.isoformat() if e.entry_date else "",
            e.location or "",
            e.description or "",
            status_labels.get(e.status, e.status),
            e.delegate.full_name if e.delegate else "",
            e.chef_service_name or "",
            e.countersigned_at.isoformat() if e.countersigned_at else "",
            e.voided_at.isoformat() if e.voided_at else "",
            e.void_reason or "",
            hashes.get(e.id) or "",
        ])
    filename = f"registre_securite_{date.today().isoformat()}.csv"
    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/safety-register/export.json")
def export_register_integrity(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Dossier d'intégrité complet (registre + journal chaîné + sceaux + jetons TSA).

    Ce fichier est vérifiable hors de l'application : page /verify, ou recalcul
    manuel — event_hash = sha256(prev_hash + "|" + payload_json).
    """
    org = db.get(Organization, current_user.organization_id)
    if not org:
        raise HTTPException(404, "Organisation non trouvée")
    report = register_chain.integrity_report(db, org)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    filename = f"registre_securite_integrite_{date.today().isoformat()}.json"
    return Response(
        content=payload.encode("utf-8"),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/safety-register/seal")
def seal_register(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fige {nombre d'événements, empreinte} et l'horodate (RFC 3161) — bureau."""
    if not _is_bureau(current_user):
        raise HTTPException(403, "Le scellement est réservé au bureau")
    org = db.get(Organization, current_user.organization_id)
    if not org:
        raise HTTPException(404, "Organisation non trouvée")
    seal, queued = register_chain.create_seal(db, org, actor=current_user, auto=False)
    return {
        "id": seal.id,
        "sealed_at": seal.sealed_at.isoformat(),
        "event_count": seal.event_count,
        "head_hash": seal.head_hash,
        "tsa_status": seal.tsa_status,
        "tsa_url": seal.tsa_url,
        "emails_queued": queued,
    }


@router.post("/safety-register")
def create_register_entry(body: RegisterEntryCreate,
                          current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _is_secu_or_bureau(current_user):
        raise HTTPException(403, "Réservé au délégué sécurité/santé et au bureau")
    try:
        d = date.fromisoformat(body.entry_date)
    except ValueError:
        raise HTTPException(422, "Date invalide")
    e = SafetyRegisterEntry(
        organization_id=current_user.organization_id,
        delegate_id=current_user.id,
        entry_date=d,
        location=body.location.strip(),
        description=body.description.strip(),
        status="pending",
        created_by_id=current_user.id,
    )
    db.add(e)
    db.flush()
    register_chain.append_event(
        db,
        org_id=current_user.organization_id,
        entry_id=e.id,
        action="create",
        actor=current_user,
        data={
            "entry_date": d.isoformat(),
            "location": e.location or "",
            "description": e.description,
            "delegate_id": current_user.id,
        },
    )
    db.commit()
    db.refresh(e)
    return {"id": e.id, "status": "pending"}


@router.post("/safety-register/{entry_id}/countersign")
def countersign_entry(entry_id: int, body: RegisterCountersign,
                      current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not _is_bureau(current_user):
        raise HTTPException(403, "Le contreseing est enregistré par le bureau")
    e = db.query(SafetyRegisterEntry).filter(
        SafetyRegisterEntry.id == entry_id,
        SafetyRegisterEntry.organization_id == current_user.organization_id,
    ).first()
    if not e:
        raise HTTPException(404, "Entrée non trouvée")
    if e.status != "pending":
        raise HTTPException(409, "Entrée déjà contresignée ou annulée")
    at = register_chain.now_utc()
    e.status = "countersigned"
    e.chef_service_name = body.chef_service_name.strip()
    e.countersigned_at = at
    register_chain.append_event(
        db,
        org_id=e.organization_id,
        entry_id=e.id,
        action="countersign",
        actor=current_user,
        data={"chef_service_name": e.chef_service_name, "countersigned_at": at.isoformat()},
        at=at,
    )
    db.commit()
    return {"id": e.id, "status": "countersigned"}


@router.post("/safety-register/{entry_id}/void")
def void_register_entry(entry_id: int, body: RegisterVoid,
                        current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Annule une entrée (jamais de suppression) — motif obligatoire, tracé.

    Bureau : à tout moment. Auteur : uniquement tant que l'entrée n'est pas
    contresignée (une fois contresignée, seul le bureau peut annuler).
    """
    e = db.query(SafetyRegisterEntry).filter(
        SafetyRegisterEntry.id == entry_id,
        SafetyRegisterEntry.organization_id == current_user.organization_id,
    ).first()
    if not e:
        raise HTTPException(404, "Entrée non trouvée")
    if e.status == "voided":
        raise HTTPException(409, "Entrée déjà annulée")
    is_author_pending = e.created_by_id == current_user.id and e.status == "pending"
    if not (_is_bureau(current_user) or is_author_pending):
        raise HTTPException(403, "Seul le bureau peut annuler une entrée contresignée")
    at = register_chain.now_utc()
    e.status = "voided"
    e.void_reason = body.reason.strip()
    e.voided_at = at
    e.voided_by_id = current_user.id
    register_chain.append_event(
        db,
        org_id=e.organization_id,
        entry_id=e.id,
        action="void",
        actor=current_user,
        data={"reason": e.void_reason, "voided_at": at.isoformat()},
        at=at,
    )
    db.commit()
    return {"id": e.id, "status": "voided"}


# ----------------------------------------------------------- protection L.415-10


@router.get("/protection")
def protection_overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(404, "Organisation non trouvée")
    today = date.today()
    people = []

    # Membres : protection = mandat (en cours) + 6 mois après la fin
    members = db.query(User).filter(
        User.organization_id == org.id, User.is_active == True,  # noqa: E712
        User.delegue_status.in_(["titulaire", "suppleant"]),
    ).all()
    for u in members:
        end = org.mandate_end_date
        if end:
            end = end.date() if isinstance(end, datetime) else end
            protected_until = end + timedelta(days=182)  # +6 mois (mois civils approximés)
            days_left = (protected_until - today).days
            status = "protected" if days_left >= 0 else "expired"
        else:
            protected_until, days_left, status = None, None, "unknown"
        people.append({
            "kind": "member",
            "name": u.full_name,
            "role": u.delegue_status.value,
            "protected_until": protected_until.isoformat() if protected_until else None,
            "days_left": days_left,
            "status": status,
        })

    # Candidats aux élections : protection 3 mois après le scrutin (L.415-10)
    elections = db.query(Election).filter(
        Election.organization_id == org.id,
        Election.status == ElectionStatus.closed.value,
        Election.election_date.isnot(None),
    ).all()
    seen = set()
    for el in elections:
        ed = el.election_date
        ed = ed.date() if isinstance(ed, datetime) else ed
        protected_until = ed + timedelta(days=92)  # +3 mois
        days_left = (protected_until - today).days
        for c in el.candidates:
            key = c.full_name.lower()
            if key in seen:
                continue
            seen.add(key)
            people.append({
                "kind": "candidate",
                "name": c.full_name,
                "role": "candidat",
                "election": el.title,
                "protected_until": protected_until.isoformat(),
                "days_left": days_left,
                "status": "protected" if days_left >= 0 else "expired",
            })
    return {"today": today.isoformat(), "people": sorted(people, key=lambda p: (p["name"].lower()))}
