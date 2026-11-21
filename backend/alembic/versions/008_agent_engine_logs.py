"""Persist engine tool call traces and model-reported capability gaps.

Revision ID: 008_agent_engine_logs
Revises: 007_account_balance_as_of
Create Date: 2026-11-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "008_agent_engine_logs"
down_revision: Union[str, None] = "007_account_balance_as_of"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_engine_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("arguments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["action_id"], ["agent_actions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_engine_calls_request_id", "agent_engine_calls", ["request_id"])
    op.create_index("ix_agent_engine_calls_action_id", "agent_engine_calls", ["action_id"])
    op.create_index("ix_agent_engine_calls_user_id", "agent_engine_calls", ["user_id"])
    op.create_index("ix_agent_engine_calls_created_at", "agent_engine_calls", ["created_at"])

    op.create_table(
        "agent_capability_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("capability", sa.String(length=160), nullable=False),
        sa.Column("business_need", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["action_id"], ["agent_actions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_capability_requests_request_id", "agent_capability_requests", ["request_id"])
    op.create_index("ix_agent_capability_requests_action_id", "agent_capability_requests", ["action_id"])
    op.create_index("ix_agent_capability_requests_user_id", "agent_capability_requests", ["user_id"])
    op.create_index("ix_agent_capability_requests_created_at", "agent_capability_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_capability_requests_created_at", table_name="agent_capability_requests")
    op.drop_index("ix_agent_capability_requests_user_id", table_name="agent_capability_requests")
    op.drop_index("ix_agent_capability_requests_action_id", table_name="agent_capability_requests")
    op.drop_index("ix_agent_capability_requests_request_id", table_name="agent_capability_requests")
    op.drop_table("agent_capability_requests")
    op.drop_index("ix_agent_engine_calls_user_id", table_name="agent_engine_calls")
    op.drop_index("ix_agent_engine_calls_action_id", table_name="agent_engine_calls")
    op.drop_index("ix_agent_engine_calls_request_id", table_name="agent_engine_calls")
    op.drop_index("ix_agent_engine_calls_created_at", table_name="agent_engine_calls")
    op.drop_table("agent_engine_calls")
