"""Registre sécurité/santé — intégrité (chaîne SHA-256, annulation, exports, sceaux).

v2026.09.004 : le registre est un journal append-only chaîné ; l'annulation
remplace la suppression ; les exports (CSV + dossier JSON) et les sceaux
(RFC 3161 + email) servent la consultation par l'ITM (art. L.414-14).
"""

from app.core.database import SessionLocal
from app.models import (
    EmailConfig,
    EmailOutbox,
    SafetyRegisterEntry,
    SafetyRegisterEvent,
    SafetyRegisterSeal,
)
from app.models.email import EmailEventType, TransportMode
from app.services import register_chain
from tests.helpers import create_invitation, fetch_captcha


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _join(client, email, code, first, last, password="test123456"):
    cid, ans = fetch_captcha(client)
    r = client.post("/api/join", json={
        "email": email, "password": password,
        "first_name": first, "last_name": last,
        "invitation_code": code,
        "captcha_id": cid, "captcha_answer": ans,
    })
    assert r.status_code == 201, f"join failed: {r.text}"
    return r.json()["access_token"]


def _create(client, token, desc="Fuite d'eau au plafond", day="2026-09-01", loc="Atelier 2"):
    r = client.post("/api/safety-register", json={"entry_date": day, "location": loc, "description": desc},
                    headers=_h(token))
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _enable_email(db, org_id):
    db.add(EmailConfig(organization_id=org_id, enabled=True, transport_mode=TransportMode.eml,
                       from_name="Délégation", from_email="dp@testpv.lu"))
    db.commit()


# ───────────────────────────────────────────── chaîne + projection


def test_chain_appended_on_create_countersign_void(client, org_with_users):
    eid = _create(client, org_with_users["marc_token"])
    d = client.get("/api/safety-register/integrity", headers=_h(org_with_users["tom_token"])).json()
    assert d["ok"] is True and d["chain_ok"] is True and d["projection_ok"] is True
    assert d["event_count"] == 1 and len(d["head_hash"]) == 64

    client.post(f"/api/safety-register/{eid}/countersign",
                json={"chef_service_name": "M. Kirch"}, headers=_h(org_with_users["sophie_token"]))
    client.post(f"/api/safety-register/{eid}/void",
                json={"reason": "Doublon de la constatation du 28/08"}, headers=_h(org_with_users["sophie_token"]))

    d = client.get("/api/safety-register/integrity", headers=_h(org_with_users["marc_token"])).json()
    assert d["event_count"] == 3 and d["ok"] is True

    # L'entrée est TOUJOURS listée (annulée, jamais supprimée)
    entries = client.get("/api/safety-register", headers=_h(org_with_users["tom_token"])).json()
    e = next(x for x in entries if x["id"] == eid)
    assert e["status"] == "voided" and e["void_reason"].startswith("Doublon")
    assert e["event_hash"] and e["voided_at"]

    # Le journal rejoué reproduit l'état affiché (projection)
    db = SessionLocal()
    events = db.query(SafetyRegisterEvent).order_by(SafetyRegisterEvent.id.asc()).all()
    states = register_chain.replay_entries(events)
    assert states[eid]["status"] == "voided"
    db.close()


def test_delete_endpoint_removed(client, org_with_users):
    eid = _create(client, org_with_users["marc_token"])
    r = client.delete(f"/api/safety-register/{eid}", headers=_h(org_with_users["marc_token"]))
    assert r.status_code in (404, 405)  # la suppression définitive n'existe plus
    entries = client.get("/api/safety-register", headers=_h(org_with_users["marc_token"])).json()
    assert any(e["id"] == eid for e in entries)


def test_chain_detects_payload_tampering(client, org_with_users):
    _create(client, org_with_users["marc_token"])
    db = SessionLocal()
    ev = db.query(SafetyRegisterEvent).order_by(SafetyRegisterEvent.id.asc()).first()
    ev.payload_json = ev.payload_json.replace("Fuite", "Inondation")
    db.commit()
    db.close()
    d = client.get("/api/safety-register/integrity", headers=_h(org_with_users["marc_token"])).json()
    assert d["chain_ok"] is False and d["ok"] is False
    assert d["first_broken_event_id"] is not None


def test_chain_detects_event_deletion(client, org_with_users):
    _create(client, org_with_users["marc_token"], "Première constatation")
    _create(client, org_with_users["marc_token"], "Deuxième constatation")
    db = SessionLocal()
    first = db.query(SafetyRegisterEvent).order_by(SafetyRegisterEvent.id.asc()).first()
    db.delete(first)
    db.commit()
    db.close()
    d = client.get("/api/safety-register/integrity", headers=_h(org_with_users["marc_token"])).json()
    assert d["chain_ok"] is False and d["ok"] is False


def test_chain_detects_direct_entry_modification(client, org_with_users):
    """La chaîne intacte ne suffit pas : la projection détecte une réécriture en base."""
    eid = _create(client, org_with_users["marc_token"])
    db = SessionLocal()
    e = db.get(SafetyRegisterEntry, eid)
    e.description = "Description réécrite directement en base"
    db.commit()
    db.close()
    d = client.get("/api/safety-register/integrity", headers=_h(org_with_users["marc_token"])).json()
    assert d["chain_ok"] is True
    assert d["projection_ok"] is False and d["ok"] is False
    assert any(m["entry_id"] == eid and m["field"] == "description" for m in d["projection_mismatches"])


# ───────────────────────────────────────────── annulation (permissions)


def test_void_permissions(client, org_with_users):
    oid = org_with_users["org_id"]
    db = SessionLocal()
    from app.models.user import User
    sophie = db.query(User).filter(User.email == "sophie@testpv.lu").first()
    create_invitation(db, "emma@testpv.lu", oid, sophie.id, "EMMA123",
                      delegue_status="employe", is_delegue_securite_sante=True)
    db.close()
    emma_token = _join(client, "emma@testpv.lu", "EMMA123", "Emma", "Dubois")

    # Désignée S&S : peut écrire
    eid = _create(client, emma_token, "Fenêtre du réfectoire qui ferme mal")
    # Auteur + en attente → peut annuler
    r = client.post(f"/api/safety-register/{eid}/void",
                    json={"reason": "Erreur de saisie"}, headers=_h(emma_token))
    assert r.status_code == 200 and r.json()["status"] == "voided"

    # Contresignée → l'auteur ne peut plus annuler, le bureau oui
    eid2 = _create(client, emma_token, "Extincteur manquant au sous-sol")
    client.post(f"/api/safety-register/{eid2}/countersign",
                json={"chef_service_name": "Mme Reis"}, headers=_h(org_with_users["marc_token"]))
    r = client.post(f"/api/safety-register/{eid2}/void",
                    json={"reason": "Tentative auteur"}, headers=_h(emma_token))
    assert r.status_code == 403
    r = client.post(f"/api/safety-register/{eid2}/void",
                    json={"reason": "Constatation reclassée en remarque"}, headers=_h(org_with_users["marc_token"]))
    assert r.status_code == 200 and r.json()["status"] == "voided"

    # Ni membre simple ni motif trop court
    eid3 = _create(client, emma_token, "Prise endommagée")
    r = client.post(f"/api/safety-register/{eid3}/void", json={"reason": "ok"}, headers=_h(org_with_users["tom_token"]))
    assert r.status_code in (403, 422)  # membre simple → 403 ; motif trop court → 422
    r = client.post(f"/api/safety-register/{eid3}/void", json={"reason": "ok"}, headers=_h(emma_token))
    assert r.status_code == 422


def test_cross_org_isolation(client, org_with_users):
    eid = _create(client, org_with_users["marc_token"])
    r = client.post(f"/api/safety-register/{eid}/void",
                    json={"reason": "tentative externe"}, headers=_h(org_with_users["other_token"]))
    assert r.status_code == 404


# ───────────────────────────────────────────── exports ITM


def test_export_csv(client, org_with_users):
    _create(client, org_with_users["marc_token"], "Extincteur manquant", day="2026-09-02")
    r = client.get("/api/safety-register/export.csv", headers=_h(org_with_users["tom_token"]))
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "attachment" in r.headers["content-disposition"]
    text = r.content.decode("utf-8")
    assert text.startswith("\ufeff")  # BOM Excel
    assert "Constatation" in text and "Empreinte" in text
    assert "Extincteur manquant" in text and "Atelier 2" in text


def test_export_json_report_is_recomputable(client, org_with_users):
    _create(client, org_with_users["marc_token"])
    r = client.get("/api/safety-register/export.json", headers=_h(org_with_users["marc_token"]))
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    d = r.json()
    assert d["format"] == "delegatum-safety-register-integrity"
    assert d["chain"]["event_count"] == 1
    assert d["verification"]["ok"] is True
    ev = d["events"][0]
    # La règle de hachage documentée doit recalculer le hash stocké
    assert register_chain.compute_event_hash(ev["prev_hash"], ev["payload_json"]) == ev["event_hash"]
    assert d["entries"][0]["event_hash"] == ev["event_hash"]


# ───────────────────────────────────────────── sceaux


def test_seal_creation_tsa_and_email(client, org_with_users, monkeypatch):
    db = SessionLocal()
    _enable_email(db, org_with_users["org_id"])
    db.close()
    _create(client, org_with_users["marc_token"])

    calls = {}

    def fake_tsa(manifest):
        calls["manifest"] = manifest
        return ("ok", "http://tsa.test", "dGVzdC10b2tlbg==")

    monkeypatch.setattr(register_chain, "tsa_stamp", fake_tsa)
    r = client.post("/api/safety-register/seal", headers=_h(org_with_users["sophie_token"]))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["tsa_status"] == "ok" and d["event_count"] == 1 and len(d["head_hash"]) == 64
    assert d["emails_queued"] >= 1
    assert f"head_hash: {d['head_hash']}" in calls["manifest"]
    assert "sealed_at: " in calls["manifest"]

    integ = client.get("/api/safety-register/integrity", headers=_h(org_with_users["sophie_token"])).json()
    assert integ["seals_ok"] is True and integ["seals_checked"] == 1

    db = SessionLocal()
    mails = db.query(EmailOutbox).filter(EmailOutbox.event_type == EmailEventType.register_seal).all()
    assert len(mails) >= 1
    assert d["head_hash"][:16] in (mails[0].body_html or "")
    db.close()


def test_seal_detects_tampered_history(client, org_with_users, monkeypatch):
    """Un passé réécrit en base ne peut pas reproduire le sceau déjà émis."""
    monkeypatch.setattr(register_chain, "tsa_stamp", lambda m: ("ok", "http://tsa.test", None))
    _create(client, org_with_users["marc_token"])
    client.post("/api/safety-register/seal", headers=_h(org_with_users["sophie_token"]))

    db = SessionLocal()
    ev = db.query(SafetyRegisterEvent).order_by(SafetyRegisterEvent.id.asc()).first()
    # Réécriture cohérente : payload modifié ET chaîne recalculée (attaquant admin)
    payload = ev.payload_json.replace("Fuite", "Inondation")
    ev.payload_json = payload
    ev.event_hash = register_chain.compute_event_hash(ev.prev_hash, payload)
    db.commit()
    db.close()

    d = client.get("/api/safety-register/integrity", headers=_h(org_with_users["marc_token"])).json()
    assert d["chain_ok"] is True  # chaîne recalculée par l'attaquant…
    assert d["seals_ok"] is False and d["ok"] is False  # …mais le sceau déjà émis la contredit


def test_seal_permission_bureau_only(client, org_with_users, monkeypatch):
    monkeypatch.setattr(register_chain, "tsa_stamp", lambda m: ("ok", "http://tsa.test", None))
    r = client.post("/api/safety-register/seal", headers=_h(org_with_users["tom_token"]))
    assert r.status_code == 403


def test_seal_survives_tsa_failure(client, org_with_users, monkeypatch):
    monkeypatch.setattr(register_chain, "tsa_stamp", lambda m: ("failed", "http://tsa.test", None))
    _create(client, org_with_users["marc_token"])
    r = client.post("/api/safety-register/seal", headers=_h(org_with_users["sophie_token"]))
    assert r.status_code == 200
    assert r.json()["tsa_status"] == "failed"


def test_auto_seal_only_when_new_events(client, org_with_users, monkeypatch):
    monkeypatch.setattr(register_chain, "tsa_stamp", lambda m: ("ok", "http://tsa.test", None))
    db = SessionLocal()
    seals, _ = register_chain.auto_seal_all(db, base_url="")
    assert seals == 0  # registre vide → rien à sceller
    db.close()

    _create(client, org_with_users["marc_token"])
    db = SessionLocal()
    seals, _ = register_chain.auto_seal_all(db, base_url="")
    assert seals == 1
    seals, _ = register_chain.auto_seal_all(db, base_url="")
    assert seals == 0  # rien de nouveau → pas de sceau supplémentaire
    db.close()

    _create(client, org_with_users["marc_token"], "Nouvelle constatation")
    db = SessionLocal()
    seals, _ = register_chain.auto_seal_all(db, base_url="")
    assert seals == 1
    assert db.query(SafetyRegisterSeal).count() == 2
    db.close()
