"""Record the date represented by each bank account balance.

Revision ID: 007_account_balance_as_of
Revises: 006_action_sources
Create Date: 2026-11-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_account_balance_as_of"
down_revision: Union[str, None] = "006_action_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bank_accounts", sa.Column("balance_as_of", sa.Date(), nullable=True))
    op.execute(
        """
        UPDATE bank_accounts AS account
        SET balance_as_of = (
            SELECT MAX(tx.booking_date)
            FROM transactions AS tx
            WHERE tx.account_id = account.id
        )
        """
    )


def downgrade() -> None:
    op.drop_column("bank_accounts", "balance_as_of")
