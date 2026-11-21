from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, ConfigDict, Field

from app.const.llm import (
    CHAT_HISTORY_MAX_TURNS,
    CHAT_MESSAGE_MAX_LENGTH,
    CHAT_ROLES,
    EXPLAIN_MODE_CARD,
    EXPLAIN_MODES,
)
from app.const.action import (
    ACTION_STATUS_PENDING,
    ACTION_STATUSES,
    EXECUTION_MODE_SIMULATED,
    EXECUTION_MODES,
    EXPLAIN_DEFAULT_QUESTION,
    EXPLAIN_QUESTION_MAX_LENGTH,
    USER_FEEDBACK_MAX_LENGTH,
)

ActionStatus = Literal[ACTION_STATUSES]
ExecutionMode = Literal[EXECUTION_MODES]
ExplainMode = Literal[EXPLAIN_MODES]
ChatRole = Literal[CHAT_ROLES]


class AgentActionBase(BaseModel):
    title: str
    agent_type: str
    trigger_reason: str
    recommended_action: str
    target_amount: Optional[Decimal] = None
    currency: str = "EUR"
    explanation: str
    impact_simulation: Dict[str, Any] = {}
    status: ActionStatus = ACTION_STATUS_PENDING
    execution_mode: ExecutionMode = EXECUTION_MODE_SIMULATED
    user_feedback: Optional[str] = None


class AgentActionCreate(AgentActionBase):
    pass


class AgentActionUpdate(BaseModel):
    status: Optional[ActionStatus] = None
    execution_mode: Optional[ExecutionMode] = None
    user_feedback: Optional[str] = Field(default=None, max_length=USER_FEEDBACK_MAX_LENGTH)


class AgentActionResponse(AgentActionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExplainActionRequest(BaseModel):
    question: str = Field(default=EXPLAIN_DEFAULT_QUESTION, min_length=1, max_length=EXPLAIN_QUESTION_MAX_LENGTH)


class ExplainActionResponse(BaseModel):
    action_id: Optional[UUID] = None
    model: str
    question: str
    answer: str
    facts_used: Dict[str, Any]
    response_source: str = Field("model", description="'model' or 'deterministic_fallback' when the LLM did not respond")


class ChatTurn(BaseModel):
    role: ChatRole
    content: str = Field(..., min_length=1, max_length=CHAT_MESSAGE_MAX_LENGTH)


class DirectExplainRequest(BaseModel):
    facts: Dict[str, Any]
    question: str = Field(default=EXPLAIN_DEFAULT_QUESTION, min_length=1, max_length=EXPLAIN_QUESTION_MAX_LENGTH)
    mode: ExplainMode = Field(EXPLAIN_MODE_CARD, description="'card' = explain one recommendation, 'advisor' = general CFO chat with the owner's notes")
    history: List[ChatTurn] = Field(default_factory=list, max_length=CHAT_HISTORY_MAX_TURNS, description="Earlier chat turns, oldest first")
