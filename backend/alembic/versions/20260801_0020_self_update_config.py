"""Provide update_config table.

Revision ID: 20260801_0020_self_update_config
Revises: 20260801_0019_instance_profile_migration
Create Date: 2026-11-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260801_0020_self_update_config"
down_revision: Union[str, None] = "20260801_0019_instance_profile_migration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "update_config",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value", sa.String(length=500), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("update_config")
