from fastapi import APIRouter

from app.api.v1.controllers.accounts import accounts_router
from app.api.v1.controllers.actions import actions_router
from app.api.v1.controllers.ai import ai_router
from app.api.v1.controllers.analysis import analysis_router
from app.api.v1.controllers.auth import auth_router
from app.api.v1.controllers.cards import cards_router
from app.api.v1.controllers.company import company_router
from app.api.v1.controllers.demo import demo_router
from app.api.v1.controllers.forecast import forecast_router
from app.api.v1.controllers.invoices import invoices_router
from app.api.v1.controllers.statements import statements_router
from app.api.v1.controllers.transactions import transactions_router

api_router = APIRouter(prefix="/v1")

api_router.include_router(auth_router)
api_router.include_router(company_router)
api_router.include_router(accounts_router)
api_router.include_router(transactions_router)
api_router.include_router(statements_router)
api_router.include_router(actions_router)
api_router.include_router(ai_router)
api_router.include_router(invoices_router)
api_router.include_router(forecast_router)
api_router.include_router(analysis_router)
api_router.include_router(cards_router)
api_router.include_router(demo_router)
