from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.const.action import (
    ADVISOR_HISTORY_MAX_TURNS,
    ADVISOR_HISTORY_ROLES,
    ADVISOR_TURN_MAX_LENGTH,
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
    response_source: str = Field("model", description="'model', 'deterministic_fallback' when the LLM did not respond, or 'guardrail' when the request was refused")


class DirectExplainRequest(BaseModel):
    facts: Dict[str, Any]
    question: str = Field(default=EXPLAIN_DEFAULT_QUESTION, min_length=1, max_length=EXPLAIN_QUESTION_MAX_LENGTH)
    history: List[Dict[str, str]] = Field(
        default_factory=list,
        max_length=ADVISOR_HISTORY_MAX_TURNS,
        description="Earlier chat turns as {role: 'user' | 'assistant', content}; used only by the advisor chat",
    )

    @field_validator("history")
    @classmethod
    def _valid_turns(cls, turns: List[Dict[str, str]]) -> List[Dict[str, str]]:
        for turn in turns:
            if turn.get("role") not in ADVISOR_HISTORY_ROLES or not isinstance(turn.get("content"), str):
                raise ValueError("Each history turn needs role 'user' or 'assistant' and a text content")
            if len(turn["content"]) > ADVISOR_TURN_MAX_LENGTH:
                raise ValueError(f"A history turn can have at most {ADVISOR_TURN_MAX_LENGTH} characters")

        return [{"role": turn["role"], "content": turn["content"]} for turn in turns]
