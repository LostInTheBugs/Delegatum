"""Add eligibility derogation fields to elections table.

Before opening a scrutin, the bureau must decide whether to allow
ineligible candidates (derogation_motivated + derogation_reason) or
block the opening entirely.

Revision ID: 20261124_0023_election_eligibility_derogation
Revises: 20261124_0022_ballot_unique_constraint
Create Date: 2026-11-24

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261124_0023_election_eligibility_derogation"
down_revision: Union[str, None] = "20261124_0022_ballot_unique_constraint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("elections") as batch_op:
        batch_op.add_column(
            op.Column("derogation_motivated", op.Boolean(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            op.Column("derogation_reason", op.String(2000), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("elections") as batch_op:
        batch_op.drop_column("derogation_reason")
        batch_op.drop_column("derogation_motivated")
