"""Deterministic rules that turn stored finance records into decision cards."""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import BankAccount
from app.models.action import AgentAction
from app.models.company import CompanyProfile
from app.models.invoice import Invoice

CENT = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_early_discount(gross_amount: Decimal, discount_percent: Decimal) -> tuple[Decimal, Decimal]:
    """Return (discount, payable) using exact decimal arithmetic and cent rounding."""
    discount = money(gross_amount * discount_percent / Decimal("100"))
    return discount, money(gross_amount - discount)


def _skip(invoice: Invoice, reason: str) -> dict[str, Any]:
    return {"invoice_id": invoice.id, "invoice_number": invoice.invoice_number, "reason": reason}


def _has_critical_validation_flag(invoice: Invoice) -> bool:
    flags = (invoice.validation_details or {}).get("flags", [])
    return any(isinstance(flag, dict) and flag.get("severity") == "CRITICAL" for flag in flags)


def _balance_path(
    starting_balance: Decimal,
    flows: dict[date, Decimal],
    start_date: date,
    end_date: date,
) -> tuple[Decimal, date, Decimal]:
    balance = starting_balance
    lowest = balance
    lowest_date = start_date
    for offset in range((end_date - start_date).days + 1):
        flow_date = start_date + timedelta(days=offset)
        balance = money(balance + flows.get(flow_date, Decimal("0")))
        if balance < lowest:
            lowest = balance
            lowest_date = flow_date
    return lowest, lowest_date, balance


async def generate_invoice_recommendations(
    db: AsyncSession,
    today: date | None = None,
) -> dict[str, Any]:
    """Create only evidence-backed early-payment recommendations.

    The LLM is deliberately not involved in selecting actions or computing effects.
    Every card is linked to an invoice row and has an idempotency key.
    """
    today = today or date.today()
    account_result = await db.execute(
        select(BankAccount)
        .where(BankAccount.is_primary.is_(True))
        .order_by(BankAccount.created_at, BankAccount.id)
        .limit(1)
    )
    account = account_result.scalar_one_or_none()
    profile_result = await db.execute(select(CompanyProfile).order_by(CompanyProfile.created_at).limit(1))
    profile = profile_result.scalar_one_or_none()

    invoices_result = await db.execute(
        select(Invoice)
        .where(
            Invoice.is_paid.is_(False),
            Invoice.is_validated.is_(True),
            Invoice.invoice_type == "incoming_expense",
            Invoice.early_discount_percent.is_not(None),
            Invoice.early_discount_percent > 0,
            Invoice.early_discount_days.is_not(None),
            Invoice.early_discount_days > 0,
        )
        .order_by(Invoice.due_date, Invoice.created_at)
        .with_for_update()
    )
    invoices = list(invoices_result.scalars().all())
    created: list[AgentAction] = []
    skipped: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not account:
        if invoices:
            skipped.extend(_skip(invoice, "No primary bank account is stored, so early-payment liquidity cannot be checked.") for invoice in invoices)
        return {"generated_actions": created, "skipped_invoices": skipped, "warnings": warnings}
    balance_age = (today - account.balance_as_of).days if account.balance_as_of else None
    if balance_age is None or not 0 <= balance_age <= 30:
        age = "unknown" if balance_age is None else f"{balance_age} days old"
        warnings.append(f"Primary account balance is {age}; update the balance snapshot before generating liquidity recommendations.")
        skipped.extend(_skip(invoice, "The primary account balance is missing or older than 30 days, so liquidity safety cannot be verified.") for invoice in invoices)
        return {"generated_actions": created, "skipped_invoices": skipped, "warnings": warnings}
    if not profile:
        if invoices:
            skipped.extend(_skip(invoice, "No company profile or safety-buffer setting is stored.") for invoice in invoices)
        return {"generated_actions": created, "skipped_invoices": skipped, "warnings": warnings}

    configured_buffer = (profile.settings or {}).get("min_safety_buffer")
    if configured_buffer is None:
        if invoices:
            skipped.extend(_skip(invoice, "The company safety buffer is not configured.") for invoice in invoices)
        return {"generated_actions": created, "skipped_invoices": skipped, "warnings": warnings}

    if account.currency != profile.base_currency:
        warnings.append(
            f"Primary account currency {account.currency} differs from company base currency {profile.base_currency}; "
            "the company safety buffer cannot be compared to this account."
        )
        skipped.extend(_skip(invoice, "Account and company base currencies differ; no exchange rate is available to validate the safety buffer.") for invoice in invoices)
        return {"generated_actions": created, "skipped_invoices": skipped, "warnings": warnings}

    try:
        buffer = Decimal(str(configured_buffer))
    except (InvalidOperation, TypeError, ValueError):
        buffer = Decimal("NaN")
    if not buffer.is_finite() or buffer < 0:
        if invoices:
            skipped.extend(_skip(invoice, "The configured safety buffer is negative and cannot be used for a safe liquidity check.") for invoice in invoices)
        return {"generated_actions": created, "skipped_invoices": skipped, "warnings": warnings}
    schedule_result = await db.execute(
        select(Invoice).where(
            Invoice.is_paid.is_(False),
            Invoice.invoice_type.in_(("incoming_expense", "outgoing_revenue")),
        ).order_by(Invoice.due_date)
    )
    scheduled_invoices = [
        item for item in schedule_result.scalars().all()
        if item.currency == account.currency and item.account_id in (None, account.id)
    ]
    base_flows: dict[date, Decimal] = {}
    for scheduled in scheduled_invoices:
        scheduled_date = max(today, scheduled.due_date)
        signed_amount = -scheduled.gross_amount if scheduled.invoice_type == "incoming_expense" else scheduled.gross_amount
        base_flows[scheduled_date] = base_flows.get(scheduled_date, Decimal("0")) + signed_amount

    for invoice in invoices:
        key = f"invoice:{invoice.id}:early_discount:v1"
        existing_result = await db.execute(select(AgentAction.id).where(AgentAction.dedupe_key == key))
        if existing_result.scalar_one_or_none():
            continue

        if invoice.validation_status == "flagged_risk" or invoice.risk_score >= 60 or _has_critical_validation_flag(invoice):
            skipped.append(_skip(invoice, "The invoice has a critical validation risk; the engine will not recommend early payment."))
            continue
        deadline = invoice.issue_date + timedelta(days=invoice.early_discount_days)
        if deadline < today:
            skipped.append(_skip(invoice, f"The early-payment deadline ({deadline.isoformat()}) has passed."))
            continue
        if deadline > invoice.due_date:
            skipped.append(_skip(invoice, "The discount deadline falls after the invoice due date."))
            continue
        if invoice.currency != account.currency:
            skipped.append(_skip(invoice, f"Invoice currency {invoice.currency} does not match primary account currency {account.currency}."))
            continue
        if invoice.account_id is not None and invoice.account_id != account.id:
            skipped.append(_skip(invoice, "The invoice is assigned to a different account."))
            continue

        discount, payable = calculate_early_discount(invoice.gross_amount, invoice.early_discount_percent)
        if discount <= 0:
            skipped.append(_skip(invoice, "The calculated discount is less than one minor currency unit."))
            continue
        balance = Decimal(account.current_balance)
        due_date = max(today, invoice.due_date)
        planned_flows = dict(base_flows)
        # Replace this invoice's due-date gross outflow with its discounted early payment.
        planned_flows[due_date] = planned_flows.get(due_date, Decimal("0")) + invoice.gross_amount
        planned_flows[deadline] = planned_flows.get(deadline, Decimal("0")) - payable
        forecast_end = max(today + timedelta(days=90), deadline)
        baseline_low, baseline_low_date, _ = _balance_path(balance, base_flows, today, forecast_end)
        planned_low, planned_low_date, _ = _balance_path(balance, planned_flows, today, forecast_end)
        if planned_low < buffer:
            skipped.append(_skip(
                invoice,
                f"Including other stored unpaid invoices, the planned schedule reaches {planned_low:.2f} "
                f"{account.currency} on {planned_low_date.isoformat()}, below the configured safety buffer "
                f"of {buffer:.2f} {account.currency}.",
            ))
            continue
        projected_at_deadline = money(balance + sum((value for day, value in planned_flows.items() if day <= deadline), Decimal("0")))

        explanation = (
            f"Invoice {invoice.invoice_number} from {invoice.counterparty_name} is due {invoice.due_date.isoformat()}. "
            f"Paying {payable:.2f} {invoice.currency} by {deadline.isoformat()} captures a {discount:.2f} "
            f"{invoice.currency} discount. The stored primary-account balance is {balance:.2f} {account.currency}; "
            f"after the planned payment it would be {projected_at_deadline:.2f} {account.currency}. "
            f"Including other stored unpaid invoices, the lowest projected balance is {planned_low:.2f} "
            f"{account.currency} on {planned_low_date.isoformat()}, versus {baseline_low:.2f} {account.currency} "
            f"on {baseline_low_date.isoformat()}. "
            f"The planned path stays above the configured {buffer:.2f} {account.currency} safety buffer. "
            "This recommendation does not make a payment."
        )
        impact = {
            "invoice_number": invoice.invoice_number,
            "counterparty_name": invoice.counterparty_name,
            "gross_amount": str(invoice.gross_amount),
            "discount_percent": str(invoice.early_discount_percent),
            "savings_amount": str(discount),
            "payable_amount": str(payable),
            "discount_deadline": deadline.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "account_id": str(account.id),
            "account_balance": str(balance),
            "projected_balance_after_payment": str(projected_at_deadline),
            "baseline_low_balance": str(baseline_low),
            "baseline_low_date": baseline_low_date.isoformat(),
            "planned_low_balance": str(planned_low),
            "planned_low_date": planned_low_date.isoformat(),
            "safety_buffer": str(buffer),
            "liquidity_safe": True,
            "balance_as_of": account.balance_as_of.isoformat(),
            "calculation_source": "deterministic_decision_engine_v1",
        }
        action = AgentAction(
            title=f"Pay {invoice.counterparty_name} early and save {discount:.2f} {invoice.currency}?",
            agent_type="payables_optimizer",
            trigger_reason=(
                f"Invoice {invoice.invoice_number} has a {invoice.early_discount_percent}% early-payment discount "
                f"through {deadline.isoformat()}."
            ),
            recommended_action="pay_early_discount",
            target_amount=payable,
            currency=invoice.currency,
            explanation=explanation,
            impact_simulation=impact,
            status="pending",
            execution_mode="simulated",
            source_type="invoice",
            source_id=str(invoice.id),
            dedupe_key=key,
        )
        db.add(action)
        await db.flush()
        created.append(action)

    return {"generated_actions": created, "skipped_invoices": skipped, "warnings": warnings}


async def load_action_database_context(
    db: AsyncSession,
    action: AgentAction | None = None,
    fallback_facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble concise, current financial context from PostgreSQL for explanations."""
    fallback_facts = fallback_facts or {}
    result: dict[str, Any] = {"evidence_source": "PostgreSQL"}
    profile_result = await db.execute(select(CompanyProfile).order_by(CompanyProfile.created_at).limit(1))
    profile = profile_result.scalar_one_or_none()
    if profile:
        result["company"] = {
            "name": profile.name,
            "base_currency": profile.base_currency,
            "industry": profile.industry,
            "minimum_safety_buffer": (profile.settings or {}).get("min_safety_buffer"),
        }

    invoice: Invoice | None = None
    if action and action.source_type == "invoice" and action.source_id:
        try:
            invoice_id = UUID(action.source_id)
        except ValueError:
            invoice_id = None
        if invoice_id:
            invoice_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
            invoice = invoice_result.scalar_one_or_none()

    if invoice is None and fallback_facts.get("invoice_number"):
        invoice_result = await db.execute(
            select(Invoice)
            .where(Invoice.invoice_number == str(fallback_facts["invoice_number"]))
            .order_by(Invoice.created_at.desc())
            .limit(1)
        )
        invoice = invoice_result.scalar_one_or_none()

    account_result = await db.execute(
        select(BankAccount)
        .where(BankAccount.is_primary.is_(True))
        .order_by(BankAccount.created_at, BankAccount.id)
        .limit(1)
    )
    account = account_result.scalar_one_or_none()
    if account:
        result["primary_account"] = {
            "currency": account.currency,
            "current_balance": str(account.current_balance),
            "balance_as_of": account.balance_as_of.isoformat() if account.balance_as_of else None,
            "balance_is_current": bool(account.balance_as_of and 0 <= (date.today() - account.balance_as_of).days <= 30),
            "overdraft_limit": str(account.overdraft_limit),
        }
        since = date.today() - timedelta(days=365)
        totals_result = await db.execute(
            select(
                Transaction.category,
                func.count(Transaction.id),
                func.coalesce(func.sum(Transaction.amount_base_currency), 0),
            )
            .where(Transaction.account_id == account.id, Transaction.booking_date >= since)
            .group_by(Transaction.category)
            .order_by(Transaction.category)
        )
        result["transaction_totals_last_365_days"] = [
            {"category": category or "uncategorized", "count": count, "net_amount_base_currency": str(total)}
            for category, count, total in totals_result.all()
        ]

        recent_query = select(Transaction).where(Transaction.account_id == account.id)
        if invoice:
            recent_query = recent_query.where(
                func.lower(func.trim(Transaction.counterparty_name)) == invoice.counterparty_name.strip().lower()
            )
        recent_result = await db.execute(
            recent_query.order_by(Transaction.booking_date.desc(), Transaction.id).limit(5)
        )
        recent = list(recent_result.scalars().all())
        result["recent_transactions"] = [
            {
                "booking_date": item.booking_date.isoformat(),
                "amount": str(item.amount),
                "currency": item.currency,
                "category": item.category,
                "counterparty": item.counterparty_name,
            }
            for item in recent
        ]
    else:
        result["primary_account"] = None
        result["transaction_totals_last_365_days"] = []
        result["recent_transactions"] = []

    if invoice:
        result["source_invoice"] = {
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "invoice_type": invoice.invoice_type,
            "counterparty": invoice.counterparty_name,
            "gross_amount": str(invoice.gross_amount),
            "currency": invoice.currency,
            "issue_date": invoice.issue_date.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "is_paid": invoice.is_paid,
            "validation_status": invoice.validation_status,
            "risk_score": invoice.risk_score,
            "early_discount_percent": str(invoice.early_discount_percent) if invoice.early_discount_percent is not None else None,
            "early_discount_days": invoice.early_discount_days,
        }
    if action:
        result["stored_action"] = {
            "title": action.title,
            "trigger_reason": action.trigger_reason,
            "recommended_action": action.recommended_action,
            "target_amount": str(action.target_amount) if action.target_amount is not None else None,
            "currency": action.currency,
            "deterministic_explanation": action.explanation,
            "calculation_snapshot": action.impact_simulation,
            "status": action.status,
        }
    if not invoice and not action:
        result["recommendation_evidence"] = "No stored action or invoice could be matched to this request. Do not infer recommendation facts from client-supplied display data."
    return result
