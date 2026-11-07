"""ajoute meetings + safety_register aux modules org existants

Revision ID: 20260801_0019_instance_profile_migration
Revises: 20260801_0018_safety_register_integrity
Create Date: 2026-11-06

Lorsqu'une instance est déployée en profil restreint (sst ou egalite),
les organisations existantes avec enabled_modules non NULL doivent
bénéficier automatiquement des modules meetings (réunions/PV/coffre)
et, si legal était présent, safety_register (registre sécurité-santé).
"""

from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision = "20260801_0019_instance_profile_migration"
down_revision = "20260801_0018"
branch_labels = None
depends_on = None


def _do_upgrade(conn) -> None:
    """Upgrade applicable depuis un test avec une connexion directe."""
    result = conn.execute(sa.text("SELECT id, enabled_modules FROM organizations WHERE enabled_modules IS NOT NULL AND enabled_modules != '' AND enabled_modules != 'null'"))
    rows = result.fetchall()
    updated = 0
    for org_id, raw_modules in rows:
        try:
            modules = json.loads(raw_modules)
            if not isinstance(modules, list):
                continue
        except (json.JSONDecodeError, TypeError):
            continue
        added = False
        if "meetings" not in modules:
            modules.append("meetings")
            added = True
        if "legal" in modules and "safety_register" not in modules:
            modules.append("safety_register")
            added = True
        if added:
            conn.execute(
                sa.text("UPDATE organizations SET enabled_modules = :val WHERE id = :id"),
                {"val": json.dumps(modules), "id": org_id},
            )
            updated += 1
    print(f"Upgrade: {updated} organisation(s) mise(s) à jour")


def upgrade() -> None:
    """Ajoute meetings à toute liste non NULL, et safety_register si legal présent."""
    conn = op.get_bind()
    _do_upgrade(conn)


def downgrade() -> None:
    """Retire meetings et safety_register ajoutés par l'upgrade."""
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT id, enabled_modules FROM organizations WHERE enabled_modules IS NOT NULL AND enabled_modules != '' AND enabled_modules != 'null'"))
    rows = result.fetchall()
    removed = 0
    for org_id, raw_modules in rows:
        try:
            modules = json.loads(raw_modules)
            if not isinstance(modules, list):
                continue
        except (json.JSONDecodeError, TypeError):
            continue
        # Retire meetings et safety_register (même ceux qui existaient avant).
        # On ne peut pas distinguer exactement — c'est un downgrade, la perte
        # d'un module ajouté manuellement entre-temps est acceptable.
        modules = [m for m in modules if m not in ("meetings", "safety_register")]
        # Ne pas ajouter de module arbitrairement — laisser tel quel.
        conn.execute(
            sa.text("UPDATE organizations SET enabled_modules = :val WHERE id = :id"),
            {"val": json.dumps(modules), "id": org_id},
        )
        removed += 1
    print(f"Downgrade: {removed} organisation(s) mise(s) à jour")
