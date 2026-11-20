from typing import List, Optional
from uuid import UUID
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.core.database import get_db
from app.models.company import CompanyProfile
from app.models.account import BankAccount
from app.models.transaction import Transaction
from app.models.forecast import LiquidityForecast
from app.models.action import AgentAction
from app.schemas.company import CompanyProfileResponse, CompanyProfileUpdate
from app.schemas.account import BankAccountResponse
from app.schemas.transaction import TransactionResponse
from app.schemas.forecast import LiquidityForecastResponse
from app.schemas.action import AgentActionResponse, AgentActionUpdate
from app.services.statement_parser import parse_bank_statement_csv

api_router = APIRouter(prefix="/v1")


# --- Company Profile ---
@api_router.get("/company", response_model=CompanyProfileResponse, tags=["Company"])
async def get_company_profile(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CompanyProfile).limit(1))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not configured")
    return profile


@api_router.put("/company", response_model=CompanyProfileResponse, tags=["Company"])
async def update_company_profile(payload: CompanyProfileUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CompanyProfile).limit(1))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile


# --- Bank Accounts ---
@api_router.get("/accounts", response_model=List[BankAccountResponse], tags=["Accounts"])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankAccount).order_by(desc(BankAccount.is_primary)))
    return result.scalars().all()


@api_router.get("/accounts/{account_id}", response_model=BankAccountResponse, tags=["Accounts"])
async def get_account(account_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankAccount).where(BankAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


# --- Transactions ---
@api_router.get("/transactions", response_model=List[TransactionResponse], tags=["Transactions"])
async def list_transactions(
    account_id: Optional[UUID] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Transaction).order_by(desc(Transaction.booking_date))

    if account_id:
        query = query.where(Transaction.account_id == account_id)
    if category:
        query = query.where(Transaction.category == category)
    if start_date:
        query = query.where(Transaction.booking_date >= start_date)
    if end_date:
        query = query.where(Transaction.booking_date <= end_date)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# --- Ingest Statement CSV ---
@api_router.post("/statements/upload", tags=["Statements"])
async def upload_bank_statement(
    file: UploadFile = File(...),
    account_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    contents = (await file.read()).decode("utf-8")
    parsed_txs = parse_bank_statement_csv(contents)

    if not parsed_txs:
        raise HTTPException(status_code=400, detail="No valid transactions parsed from CSV")

    # If account_id not provided, find primary or match account_number from CSV
    if not account_id:
        first_acc_num = parsed_txs[0]["account_number"]
        result = await db.execute(select(BankAccount).where(BankAccount.account_number == first_acc_num))
        account = result.scalar_one_or_none()
        if not account:
            # Create account if it doesn't exist
            account = BankAccount(
                account_number=first_acc_num or "UNKNOWN-ACCOUNT",
                account_name="Imported Bank Account",
                currency="EUR",
            )
            db.add(account)
            await db.flush()
        account_id = account.id

    inserted = 0
    for tx in parsed_txs:
        db_tx = Transaction(
            account_id=account_id,
            booking_date=tx["booking_date"],
            value_date=tx["value_date"],
            amount=tx["amount"],
            currency=tx["currency"],
            amount_base_currency=tx["amount_base_currency"],
            transaction_type=tx["transaction_type"],
            category=tx["category"],
            counterparty_name=tx["counterparty_name"],
            counterparty_account=tx["counterparty_account"],
            counterparty_bank_code=tx["counterparty_bank_code"],
            payment_reference=tx["payment_reference"],
            info=tx["info"],
            is_recurring=tx["is_recurring"],
            metadata_payload=tx["metadata_payload"],
        )
        db.add(db_tx)
        inserted += 1

    await db.commit()
    return {"status": "success", "transactions_imported": inserted}


# --- Agent Actions (Human-in-the-Loop) ---
@api_router.get("/actions", response_model=List[AgentActionResponse], tags=["Agent Actions"])
async def list_agent_actions(
    status: Optional[str] = None,
    agent_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(AgentAction).order_by(desc(AgentAction.created_at))
    if status:
        query = query.where(AgentAction.status == status)
    if agent_type:
        query = query.where(AgentAction.agent_type == agent_type)

    result = await db.execute(query)
    return result.scalars().all()


@api_router.post("/actions/{action_id}/update-status", response_model=AgentActionResponse, tags=["Agent Actions"])
async def update_action_status(
    action_id: UUID,
    payload: AgentActionUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AgentAction).where(AgentAction.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Agent action not found")

    if payload.status:
        action.status = payload.status
    if payload.execution_mode:
        action.execution_mode = payload.execution_mode
    if payload.user_feedback:
        action.user_feedback = payload.user_feedback

    await db.commit()
    await db.refresh(action)
    return action
