from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy import String, Numeric, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class AgentAction(Base, UUIDMixin, TimestampMixin):
    """
    Explainable recommendation or action created by the Autonomous CFO agent.
    Implements the Hackathon's Human-In-The-Loop requirement:
    - Analyzes risk autonomously
    - Recommends an action with full reasoning
    - Awaits human approval / simulation before execution
    """
    __tablename__ = "agent_actions"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    # Examples: 'liquidity_guard', 'fx_hedging', 'tax_optimizer', 'investment'

    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(128), nullable=False)
    # Examples: 'request_credit_line', 'delay_supplier_payment', 'hedge_fx_chf', 'move_to_deposit'

    target_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)

    # Explainable business justification for the business owner
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    # Financial simulation numbers: before vs after cash flow impact
    impact_simulation: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Workflow state: pending -> simulated -> approved / rejected -> executed
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(32), default="simulated", nullable=False)

    # Owner feedback / notes when approving or rejecting
    user_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
