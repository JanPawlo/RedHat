from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, Literal, List
from pydantic import BaseModel, ConfigDict, Field


class AgentActionBase(BaseModel):
    title: str
    agent_type: str
    trigger_reason: str
    recommended_action: str
    target_amount: Optional[Decimal] = None
    currency: str = "EUR"
    explanation: str
    impact_simulation: Dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "approved", "rejected", "executed"] = "pending"
    execution_mode: str = "simulated"
    user_feedback: Optional[str] = None


class AgentActionCreate(AgentActionBase):
    pass


class AgentActionUpdate(BaseModel):
    status: Optional[Literal["pending", "approved", "rejected", "executed"]] = None
    execution_mode: Optional[str] = None
    user_feedback: Optional[str] = None


class AgentActionResponse(AgentActionBase):
    id: UUID
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExplainActionRequest(BaseModel):
    question: str = Field(
        default="Why do you recommend this action and how does it affect my cash flow?",
        min_length=1,
        max_length=1000,
    )


class SkippedRecommendation(BaseModel):
    invoice_id: UUID
    invoice_number: str
    reason: str


class ActionGenerationResponse(BaseModel):
    generated_count: int
    generated_actions: List[AgentActionResponse]
    skipped_invoices: List[SkippedRecommendation] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ExplainActionResponse(BaseModel):
    action_id: Optional[UUID] = None
    model: str
    question: str
    answer: str
    facts_used: Dict[str, Any]
    response_source: Literal["model", "deterministic_fallback"] = "model"


class DirectExplainRequest(BaseModel):
    facts: Dict[str, Any] = Field(default_factory=dict, description="Legacy display context; financial evidence is loaded from PostgreSQL.")
    action_id: Optional[UUID] = None
    question: str = Field(default="Explain the recommendation and its cash-flow impact.", min_length=1, max_length=1000)
