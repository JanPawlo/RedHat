"""Initial database schema for single-tenant Autonomous CFO

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Company Profile
    op.create_table(
        'company_profile',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('country', sa.String(length=10), server_default='DE', nullable=False),
        sa.Column('base_currency', sa.String(length=3), server_default='EUR', nullable=False),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('tax_identifier', sa.String(length=50), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 2. Bank Accounts
    op.create_table(
        'bank_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_number', sa.String(length=64), nullable=False),
        sa.Column('account_name', sa.String(length=128), server_default='Main Operating Account', nullable=False),
        sa.Column('bank_name', sa.String(length=128), server_default='Commerzbank', nullable=False),
        sa.Column('bank_code', sa.String(length=32), nullable=True),
        sa.Column('currency', sa.String(length=3), server_default='EUR', nullable=False),
        sa.Column('current_balance', sa.Numeric(precision=15, scale=2), server_default='0.00', nullable=False),
        sa.Column('overdraft_limit', sa.Numeric(precision=15, scale=2), server_default='0.00', nullable=False),
        sa.Column('is_primary', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_bank_accounts_account_number', 'bank_accounts', ['account_number'], unique=True)

    # 3. Transactions
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('booking_date', sa.Date(), nullable=False),
        sa.Column('value_date', sa.Date(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='EUR', nullable=False),
        sa.Column('amount_base_currency', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('transaction_type', sa.String(length=64), nullable=True),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('counterparty_name', sa.String(length=255), nullable=True),
        sa.Column('counterparty_account', sa.String(length=64), nullable=True),
        sa.Column('counterparty_bank_code', sa.String(length=32), nullable=True),
        sa.Column('payment_reference', sa.Text(), nullable=True),
        sa.Column('info', sa.Text(), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('metadata_payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['bank_accounts.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_transactions_account_id', 'transactions', ['account_id'])
    op.create_index('ix_transactions_booking_date', 'transactions', ['booking_date'])
    op.create_index('ix_transactions_category', 'transactions', ['category'])
    op.create_index('ix_transactions_transaction_type', 'transactions', ['transaction_type'])
    op.create_index('ix_transactions_counterparty_name', 'transactions', ['counterparty_name'])
    op.create_index('ix_transactions_account_date', 'transactions', ['account_id', 'booking_date'])

    # 4. Liquidity Forecasts
    op.create_table(
        'liquidity_forecasts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('forecast_date', sa.Date(), nullable=False),
        sa.Column('projected_balance', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('projected_inflows', sa.Numeric(precision=15, scale=2), server_default='0.00', nullable=False),
        sa.Column('projected_outflows', sa.Numeric(precision=15, scale=2), server_default='0.00', nullable=False),
        sa.Column('is_deficit', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('scenario_name', sa.String(length=64), server_default='baseline', nullable=False),
        sa.Column('drivers', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['bank_accounts.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_liquidity_forecasts_account_id', 'liquidity_forecasts', ['account_id'])
    op.create_index('ix_liquidity_forecasts_forecast_date', 'liquidity_forecasts', ['forecast_date'])
    op.create_index('ix_liquidity_forecasts_scenario_name', 'liquidity_forecasts', ['scenario_name'])

    # 5. Agent Actions (Human-in-the-loop recommendations)
    op.create_table(
        'agent_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('agent_type', sa.String(length=64), nullable=False),
        sa.Column('trigger_reason', sa.Text(), nullable=False),
        sa.Column('recommended_action', sa.String(length=128), nullable=False),
        sa.Column('target_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=3), server_default='EUR', nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('impact_simulation', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('execution_mode', sa.String(length=32), server_default='simulated', nullable=False),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_agent_actions_agent_type', 'agent_actions', ['agent_type'])
    op.create_index('ix_agent_actions_status', 'agent_actions', ['status'])


def downgrade() -> None:
    op.drop_table('agent_actions')
    op.drop_table('liquidity_forecasts')
    op.drop_table('transactions')
    op.drop_table('bank_accounts')
    op.drop_table('company_profile')
