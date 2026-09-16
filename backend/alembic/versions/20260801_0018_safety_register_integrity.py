"""registre sécurité/santé — chaîne d'intégrité (journal chaîné + sceaux + annulation)

Revision ID: 20260801_0018
Revises: 20260801_0017
Create Date: 2026-09-16

- safety_register_entries : + voided_at / voided_by_id / void_reason (l'annulation
  motivée remplace la suppression définitive — un registre ne perd jamais d'entrée)
- safety_register_events : journal append-only chaîné SHA-256
  (event_hash = sha256(prev_hash + "|" + payload_json))
- safety_register_seals : sceaux horodatés RFC 3161 (preuve externe)
- Backfill : les entrées créées AVANT cette version reçoivent des événements
  synthétiques marqués backfilled=true — la chaîne couvre tout l'historique.

Idempotente (gardes _has_table/_has_column) — create_all du démarrage peut
créer tables/colonnes AVANT la migration. Le backfill est gardé par
« aucune ligne dans safety_register_events » — PAS par _has_table (create_all
pré-crée la table VIDE → le garde sauterait le repli silencieusement : incident
vécu sur la migration 0016).
"""

import hashlib
import json

import sqlalchemy as sa
from alembic import op

revision = "20260801_0018"
down_revision = "20260801_0017"
branch_labels = None
depends_on = None

GENESIS = "0" * 64


def _has_column(table: str, col: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return any(c["name"] == col for c in insp.get_columns(table))


def _has_table(name: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return insp.has_table(name)


def _canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _event_hash(prev: str, payload_json: str) -> str:
    return hashlib.sha256((prev + "|" + payload_json).encode("utf-8")).hexdigest()


def _iso(v) -> str | None:
    """Normalise une valeur datetime/date/texte (lecture brute sqlite) en ISO 'T'."""
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    s = str(v)
    if len(s) >= 19 and s[4] == "-" and s[10] == " ":
        return s[:10] + "T" + s[11:]
    return s


def _col_dt(v):
    """Format attendu par le dialecte pour les colonnes DateTime (espace, pas 'T')."""
    iso = _iso(v)
    return iso.replace("T", " ", 1) if iso else None


def upgrade() -> None:
    if not _has_column("safety_register_entries", "voided_at"):
        op.add_column("safety_register_entries", sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True))
    if not _has_column("safety_register_entries", "voided_by_id"):
        # ⚠️ SQLite : pas d'ALTER de contrainte — colonne simple SANS ForeignKey
        # (la FK reste déclarée au niveau ORM ; SQLite n'applique pas les FK par
        # défaut de toute façon). Vécu : NotImplementedError « No support for
        # ALTER of constraints in SQLite dialect » au premier passage.
        op.add_column("safety_register_entries", sa.Column("voided_by_id", sa.Integer(), nullable=True))
    if not _has_column("safety_register_entries", "void_reason"):
        op.add_column("safety_register_entries", sa.Column("void_reason", sa.Text(), nullable=True))

    if not _has_table("safety_register_events"):
        op.create_table(
            "safety_register_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False, index=True),
            sa.Column("entry_id", sa.Integer(), sa.ForeignKey("safety_register_entries.id"), nullable=True),
            sa.Column("action", sa.String(20), nullable=False),
            sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("actor_name", sa.String(200), nullable=True),
            sa.Column("at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("prev_hash", sa.String(64), nullable=False),
            sa.Column("event_hash", sa.String(64), nullable=False),
        )

    if not _has_table("safety_register_seals"):
        op.create_table(
            "safety_register_seals",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False, index=True),
            sa.Column("sealed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("event_count", sa.Integer(), nullable=False),
            sa.Column("head_hash", sa.String(64), nullable=False),
            sa.Column("manifest", sa.Text(), nullable=False),
            sa.Column("tsa_status", sa.String(20), nullable=False, server_default="none"),
            sa.Column("tsa_url", sa.String(300), nullable=True),
            sa.Column("tsa_token_b64", sa.Text(), nullable=True),
            sa.Column("auto", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    _backfill(op.get_bind())


def _backfill(bind) -> None:
    """Événements synthétiques pour les entrées antérieures à la chaîne.

    Garde : on ne backfill QUE si le journal est vide (create_all peut avoir
    pré-créé la table vide — le backfill doit quand même tourner).
    """
    count = bind.execute(sa.text("SELECT COUNT(*) FROM safety_register_events")).scalar() or 0
    if count:
        return
    rows = bind.execute(sa.text(
        "SELECT id, organization_id, delegate_id, entry_date, location, description, status, "
        "chef_service_name, countersigned_at, created_at, created_by_id "
        "FROM safety_register_entries ORDER BY organization_id, created_at, id"
    )).mappings().all()
    if not rows:
        return

    insert_sql = sa.text(
        "INSERT INTO safety_register_events "
        "(organization_id, entry_id, action, actor_id, actor_name, at, payload_json, prev_hash, event_hash) "
        "VALUES (:org, :entry, :action, :actor, NULL, :at, :payload, :prev, :hash)"
    )
    chains: dict[int, str] = {}
    for r in rows:
        org = r["organization_id"]
        prev = chains.get(org, GENESIS)

        at_iso = _iso(r["created_at"])
        payload = _canonical({
            "action": "create",
            "entry_id": r["id"],
            "at": at_iso,
            "backfilled": True,
            "entry_date": _iso(r["entry_date"]),
            "location": r["location"] or "",
            "description": r["description"] or "",
            "delegate_id": r["delegate_id"],
        })
        h = _event_hash(prev, payload)
        bind.execute(insert_sql, {
            "org": org, "entry": r["id"], "action": "create", "actor": r["created_by_id"],
            "at": _col_dt(r["created_at"]), "payload": payload, "prev": prev, "hash": h,
        })
        prev = h

        if (r["status"] or "") == "countersigned" and r["countersigned_at"] is not None:
            cat_iso = _iso(r["countersigned_at"])
            payload2 = _canonical({
                "action": "countersign",
                "entry_id": r["id"],
                "at": cat_iso,
                "backfilled": True,
                "chef_service_name": r["chef_service_name"] or "",
                "countersigned_at": cat_iso,
            })
            h2 = _event_hash(prev, payload2)
            bind.execute(insert_sql, {
                "org": org, "entry": r["id"], "action": "countersign", "actor": None,
                "at": _col_dt(r["countersigned_at"]), "payload": payload2, "prev": prev, "hash": h2,
            })
            prev = h2

        chains[org] = prev


def downgrade() -> None:
    op.drop_table("safety_register_seals")
    op.drop_table("safety_register_events")
    op.drop_column("safety_register_entries", "void_reason")
    op.drop_column("safety_register_entries", "voided_by_id")
    op.drop_column("safety_register_entries", "voided_at")
