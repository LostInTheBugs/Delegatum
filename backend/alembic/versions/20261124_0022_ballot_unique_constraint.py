"""Add unique constraint on election_ballots(election_id, user_id).

Prevents double-voting at the database level (race-condition safety net).

Revision ID: 20261124_0022_ballot_unique_constraint
Revises: 20261108_0021_rbac
Create Date: 2026-11-24

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261124_0022_ballot_unique_constraint"
down_revision: Union[str, None] = "20261108_0021_rbac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_ballots_election_user",
        "election_ballots",
        ["election_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_ballots_election_user",
        "election_ballots",
        type_="unique",
    )
