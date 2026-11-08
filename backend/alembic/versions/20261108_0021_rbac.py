"""account types, expiry, permission matrix

Revision ID: 20261108_0021_rbac
Revises: 20260801_0020_self_update_config
Create Date: 2026-11-08

R1 — RBAC backend :
- User + Invitation : account_type (delegation | salarie_designe | rh | itm | police)
- User + Invitation : access_expires_at (DateTime nullable)
- role_permissions (PermissionMatrix) table : org × role × module × level
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261108_0021_rbac"
down_revision: Union[str, None] = "20260801_0020_self_update_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── User ────────────────────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column("account_type", sa.String(50), nullable=True, server_default="delegation"),
    )
    op.add_column(
        "users",
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Invitation ──────────────────────────────────────────────────────
    op.add_column(
        "invitations",
        sa.Column("account_type", sa.String(50), nullable=True, server_default="delegation"),
    )
    op.add_column(
        "invitations",
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── role_permissions (PermissionMatrix) ─────────────────────────────
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("role_key", sa.String(50), nullable=False),
        sa.Column("module", sa.String(50), nullable=False),
        sa.Column("level", sa.String(10), nullable=False, server_default="none"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "role_key", "module", name="uq_role_permission"),
    )


def downgrade() -> None:
    op.drop_table("role_permissions")

    op.drop_column("invitations", "access_expires_at")
    op.drop_column("invitations", "account_type")
    op.drop_column("users", "access_expires_at")
    op.drop_column("users", "account_type")
