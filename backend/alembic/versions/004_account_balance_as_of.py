"""Record the date of each stored bank balance snapshot.

Revision ID: 004_balance_as_of
Revises: 003_action_sources
Create Date: 2026-11-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_balance_as_of"
down_revision: Union[str, None] = "003_action_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bank_accounts", sa.Column("balance_as_of", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("bank_accounts", "balance_as_of")
