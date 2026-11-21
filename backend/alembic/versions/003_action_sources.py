"""Link generated recommendations to database records and deduplicate them.

Revision ID: 003_action_sources
Revises: 002_add_invoices_table
Create Date: 2026-11-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_action_sources"
down_revision: Union[str, None] = "002_add_invoices_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_actions", sa.Column("source_type", sa.String(length=32), nullable=True))
    op.add_column("agent_actions", sa.Column("source_id", sa.String(length=64), nullable=True))
    op.add_column("agent_actions", sa.Column("dedupe_key", sa.String(length=160), nullable=True))
    op.create_index("ix_agent_actions_source_type", "agent_actions", ["source_type"])
    op.create_index("ix_agent_actions_source_id", "agent_actions", ["source_id"])
    op.create_index("ix_agent_actions_dedupe_key", "agent_actions", ["dedupe_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_agent_actions_dedupe_key", table_name="agent_actions")
    op.drop_index("ix_agent_actions_source_id", table_name="agent_actions")
    op.drop_index("ix_agent_actions_source_type", table_name="agent_actions")
    op.drop_column("agent_actions", "dedupe_key")
    op.drop_column("agent_actions", "source_id")
    op.drop_column("agent_actions", "source_type")
