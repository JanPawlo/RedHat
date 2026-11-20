"""Add invoices table for invoice and receipt validation

Revision ID: 002_add_invoices_table
Revises: 001_initial_schema
Create Date: 2026-11-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002_add_invoices_table'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invoice_number', sa.String(length=128), nullable=False),
        sa.Column('invoice_type', sa.String(length=32), server_default='incoming_expense', nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('counterparty_name', sa.String(length=255), nullable=False),
        sa.Column('counterparty_tax_id', sa.String(length=64), nullable=True),
        sa.Column('counterparty_iban', sa.String(length=64), nullable=True),
        sa.Column('counterparty_bic', sa.String(length=32), nullable=True),
        sa.Column('net_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=15, scale=2), server_default='0.00', nullable=False),
        sa.Column('gross_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='EUR', nullable=False),
        sa.Column('early_discount_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('early_discount_days', sa.Integer(), nullable=True),
        sa.Column('is_validated', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('validation_status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('risk_score', sa.Integer(), server_default='0', nullable=False),
        sa.Column('validation_details', sa.JSON(), nullable=False),
        sa.Column('is_paid', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('paid_transaction_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('raw_metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['bank_accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['paid_transaction_id'], ['transactions.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'])
    op.create_index('ix_invoices_invoice_type', 'invoices', ['invoice_type'])
    op.create_index('ix_invoices_due_date', 'invoices', ['due_date'])
    op.create_index('ix_invoices_counterparty_name', 'invoices', ['counterparty_name'])
    op.create_index('ix_invoices_validation_status', 'invoices', ['validation_status'])
    op.create_index('ix_invoices_is_paid', 'invoices', ['is_paid'])


def downgrade() -> None:
    op.drop_table('invoices')
