from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentEngineCallLogResponse(BaseModel):
    id: UUID
    request_id: UUID
    action_id: Optional[UUID]
    user_id: Optional[UUID]
    tool_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    status: str
    error_message: Optional[str]
    duration_ms: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentCapabilityRequestResponse(BaseModel):
    id: UUID
    request_id: UUID
    action_id: Optional[UUID]
    user_id: Optional[UUID]
    capability: str
    business_need: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
