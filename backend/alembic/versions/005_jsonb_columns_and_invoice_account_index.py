"""Store JSON columns as JSONB with an empty-object default and index invoices.account_id

Revision ID: 005_jsonb_and_invoice_index
Revises: 004_seed_default_admin
Create Date: 2026-11-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '005_jsonb_and_invoice_index'
down_revision: Union[str, None] = '004_seed_default_admin'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON_COLUMNS = [
    ('company_profile', 'settings'),
    ('transactions', 'metadata_payload'),
    ('liquidity_forecasts', 'drivers'),
    ('agent_actions', 'impact_simulation'),
    ('invoices', 'validation_details'),
    ('invoices', 'raw_metadata'),
]


def upgrade() -> None:
    for table, column in JSON_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=postgresql.JSONB(),
            existing_type=sa.JSON(),
            existing_nullable=False,
            postgresql_using=f'{column}::jsonb',
            server_default=sa.text("'{}'::jsonb"),
        )

    op.create_index('ix_invoices_account_id', 'invoices', ['account_id'])


def downgrade() -> None:
    op.drop_index('ix_invoices_account_id', table_name='invoices')

    for table, column in JSON_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.JSON(),
            existing_type=postgresql.JSONB(),
            existing_nullable=False,
            postgresql_using=f'{column}::json',
            server_default=None,
        )
