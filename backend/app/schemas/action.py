from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class AgentActionBase(BaseModel):
    title: str
    agent_type: str
    trigger_reason: str
    recommended_action: str
    target_amount: Optional[Decimal] = None
    currency: str = "EUR"
    explanation: str
    impact_simulation: Dict[str, Any] = {}
    status: str = "pending"
    execution_mode: str = "simulated"
    user_feedback: Optional[str] = None


class AgentActionCreate(AgentActionBase):
    pass


class AgentActionUpdate(BaseModel):
    status: Optional[str] = None
    execution_mode: Optional[str] = None
    user_feedback: Optional[str] = None


class AgentActionResponse(AgentActionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
