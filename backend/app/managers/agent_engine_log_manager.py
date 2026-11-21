from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_engine_call import AgentCapabilityRequest, AgentEngineCall


async def record_engine_call(
    db: AsyncSession,
    *,
    request_id: UUID,
    action_id: Optional[UUID],
    user_id: Optional[UUID],
    tool_name: str,
    arguments: Dict[str, Any],
    result: Dict[str, Any],
    status: str,
    error_message: Optional[str],
    duration_ms: int,
) -> AgentEngineCall:
    entry = AgentEngineCall(
        request_id=request_id,
        action_id=action_id,
        user_id=user_id,
        tool_name=tool_name[:100],
        arguments=arguments,
        result=result,
        status=status,
        error_message=error_message,
        duration_ms=max(0, duration_ms),
    )
    db.add(entry)
    await db.flush()
    return entry


async def record_capability_request(
    db: AsyncSession,
    *,
    request_id: UUID,
    action_id: Optional[UUID],
    user_id: Optional[UUID],
    capability: str,
    business_need: str,
) -> AgentCapabilityRequest:
    entry = AgentCapabilityRequest(
        request_id=request_id,
        action_id=action_id,
        user_id=user_id,
        capability=capability.strip()[:160],
        business_need=business_need.strip(),
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_engine_calls(
    db: AsyncSession,
    *,
    action_id: Optional[UUID],
    request_id: Optional[UUID],
    limit: int,
    offset: int,
) -> List[AgentEngineCall]:
    query = select(AgentEngineCall).order_by(desc(AgentEngineCall.created_at), desc(AgentEngineCall.id))
    if action_id:
        query = query.where(AgentEngineCall.action_id == action_id)
    if request_id:
        query = query.where(AgentEngineCall.request_id == request_id)
    result = await db.execute(query.offset(offset).limit(limit))
    return list(result.scalars().all())


async def list_capability_requests(
    db: AsyncSession,
    *,
    action_id: Optional[UUID],
    request_id: Optional[UUID],
    limit: int,
    offset: int,
) -> List[AgentCapabilityRequest]:
    query = select(AgentCapabilityRequest).order_by(
        desc(AgentCapabilityRequest.created_at), desc(AgentCapabilityRequest.id)
    )
    if action_id:
        query = query.where(AgentCapabilityRequest.action_id == action_id)
    if request_id:
        query = query.where(AgentCapabilityRequest.request_id == request_id)
    result = await db.execute(query.offset(offset).limit(limit))
    return list(result.scalars().all())
