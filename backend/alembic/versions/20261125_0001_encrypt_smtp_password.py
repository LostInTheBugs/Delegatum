"""encrypt existing smtp_password values + rename column

Renomme smtp_password → _smtp_password et chiffre toutes les valeurs
en clair existantes avec AES-256-GCM (SD_SECRET_KEY).

Les valeurs déjà chiffrées (format nonce:ciphertext) sont conservées telles
quelles — ce qui arrive uniquement si la migration précédente a été partiellement
appliquée puis rollbackée.
"""
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from alembic import op
import sqlalchemy as sa

revision = "20261125_0001_encrypt_smtp_password"
down_revision = "20261124_0023_election_eligibility_derogation"
branch_labels = None
depends_on = None


def _aes_key() -> bytes:
    secret = os.environ.get("SD_SECRET_KEY", "")
    if not secret:
        return b"\x00" * 32
    try:
        return bytes.fromhex(secret[:64])
    except ValueError:
        import hashlib
        return hashlib.sha256(secret.encode()).digest()[:32]


def _is_encrypted(value: str) -> bool:
    if ":" not in value:
        return False
    nonce_hex, _ = value.split(":", 1)
    if len(nonce_hex) != 24:
        return False
    try:
        bytes.fromhex(nonce_hex)
        return True
    except ValueError:
        return False


def _encrypt(plaintext: str) -> str:
    key = _aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return f"{nonce.hex()}:{ciphertext.hex()}"


def upgrade() -> None:
    conn = op.get_bind()
    table = sa.table("email_configs", sa.column("smtp_password", sa.String))

    # 1. Chiffrer les mots de passe en clair existants
    # On récupère tout en Python — _is_encrypted est un filtre Python, pas SQL.
    rows = conn.execute(
        sa.select(table.c.smtp_password).where(
            table.c.smtp_password.isnot(None)
        )
    )
    for (plain,) in rows:
        if plain and not _is_encrypted(plain):
            conn.execute(
                table.update()
                .where(table.c.smtp_password == plain)
                .values(smtp_password=_encrypt(plain))
            )

    # 2. Renommer la colonne smtp_password → _smtp_password
    with op.batch_alter_table("email_configs", schema=None) as batch_op:
        batch_op.alter_column("smtp_password", new_column_name="_smtp_password")


def downgrade() -> None:
    with op.batch_alter_table("email_configs", schema=None) as batch_op:
        batch_op.alter_column("_smtp_password", new_column_name="smtp_password")
