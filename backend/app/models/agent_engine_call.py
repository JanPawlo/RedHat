from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import JSONType, UUIDMixin


class AgentEngineCall(Base, UUIDMixin):
    """Append-only trace of a model-requested deterministic engine tool call."""

    __tablename__ = "agent_engine_calls"

    request_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), index=True, nullable=False)
    action_id: Mapped[Optional[UUID]] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("agent_actions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    arguments: Mapped[Dict[str, Any]] = mapped_column(JSONType, nullable=False)
    result: Mapped[Dict[str, Any]] = mapped_column(JSONType, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)


class AgentCapabilityRequest(Base, UUIDMixin):
    """A model-reported need that the currently exposed engine tools cannot answer."""

    __tablename__ = "agent_capability_requests"

    request_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), index=True, nullable=False)
    action_id: Mapped[Optional[UUID]] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("agent_actions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    capability: Mapped[str] = mapped_column(String(160), nullable=False)
    business_need: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
