from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session, get_current_user
from app.const.docs import RESPONSE_UNAUTHORIZED, TAG_DEMO
from app.managers import demo_manager
from app.models.user import User

demo_router = APIRouter(prefix="/demo", tags=[TAG_DEMO], responses=RESPONSE_UNAUTHORIZED)


@demo_router.post("/reset", summary="Reset the database to the demo start state")
async def reset_demo(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = db_session,
) -> Dict[str, str]:
    """
    Deletes the company profile, bank accounts, transactions, invoices, forecasts and all decision cards,
    then runs the seed again (statement CSV, demo scenario, cards from the engine). User accounts stay.
    """
    await demo_manager.reset_demo(db)
    return {"status": "reset"}
