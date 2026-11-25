"""renamed smtp_password -> _smtp_password for encryption

Changement de nom de la colonne pour stocker le mot de passe SMTP
chiffré (AES-256-GCM). Aucune donnée n'est perdue.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261125_0001_encrypt_smtp_password"
down_revision = "20261124_0023_election_eligibility_derogation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Renommer la colonne smtp_password → _smtp_password
    # SQLite ne supporte pas ALTER COLUMN RENAME directement,
    # donc on utilise batch mode pour la compatibilité.
    with op.batch_alter_table("email_configs", schema=None) as batch_op:
        batch_op.alter_column("smtp_password", new_column_name="_smtp_password")


def downgrade() -> None:
    with op.batch_alter_table("email_configs", schema=None) as batch_op:
        batch_op.alter_column("_smtp_password", new_column_name="smtp_password")
