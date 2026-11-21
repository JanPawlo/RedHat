import re
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Sequence, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.const.action import (
    ACTION_STATUS_PENDING,
    AGENT_TYPE_FRAUD_GUARD,
    AGENT_TYPE_PAYABLES_OPTIMIZER,
    EXECUTION_MODE_SIMULATED,
    INVOICE_ACTION_RECOMMENDATION,
)
from app.const.cards import SOURCE_INVOICE
from app.const.forecast import FORECAST_HORIZON_MAX_DAYS, SCENARIO_BASE
from app.const.invoice import (
    ARITHMETIC_TOLERANCE,
    DEDUPE_KEY_MAX_LENGTH,
    IBAN_STATUS_MISMATCH,
    IBAN_STATUS_NEW,
    IBAN_STATUS_VERIFIED,
    INVOICE_CARD_DEDUPE_KEY,
    INVOICE_PAYMENT_LABEL,
    KNOWN_VENDOR_TRANSACTIONS_LIMIT,
    PAID_CANDIDATES_LIMIT,
    PAYABLE_INVOICE_TYPES,
    PRICE_SPIKE_MIN_AMOUNT,
    PRICE_SPIKE_RATIO,
    RISK_LEVEL_CRITICAL,
    RISK_LEVEL_HIGH,
    RISK_LEVEL_LOW,
    RISK_LEVEL_MEDIUM,
    RISK_SCORE_CRITICAL,
    RISK_SCORE_HIGH,
    RISK_SCORE_MAX,
    RISK_SCORE_MEDIUM,
    RISK_WEIGHT_ALREADY_PAID,
    RISK_WEIGHT_ARITHMETIC,
    RISK_WEIGHT_BUFFER_BREACH,
    RISK_WEIGHT_DUPLICATE,
    RISK_WEIGHT_IBAN_MISMATCH,
    RISK_WEIGHT_INSOLVENCY,
    RISK_WEIGHT_INVALID_AMOUNT,
    RISK_WEIGHT_NEW_VENDOR,
    RISK_WEIGHT_NON_STANDARD_VAT,
    RISK_WEIGHT_OVERDRAFT_USED,
    RISK_WEIGHT_PRICE_SPIKE,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    SOURCE_ID_MAX_LENGTH,
    STANDARD_VAT_RATES,
    VAT_RATE_TOLERANCE,
)
from app.const.messages import NO_ACCOUNT_DATA_DESCRIPTION, NO_ACCOUNT_DATA_TITLE
from app.const.sql import LIKE_ESCAPE_CHAR
from app.core.sql import contains_pattern
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.models.action import AgentAction
from app.schemas.invoice import (
    InvoiceValidateRequest,
    ValidationReport,
    ValidationFlag,
    EarlyDiscountOpportunity,
)
from app.services.forecast_engine import CashChange, ForecastInputs, simulate

ZERO = Decimal("0.00")
HUNDRED = Decimal("100.00")
CENT = Decimal("0.01")


@dataclass(frozen=True)
class CashPosition:
    """Forecast inputs of the paying account, so liquidity is checked over time, not against today's balance."""

    inputs: ForecastInputs
    currency: str
    overdraft_limit: Decimal = ZERO
    planned: Tuple[CashChange, ...] = ()


@dataclass(frozen=True)
class PaymentImpact:
    payment_day: date
    lowest_before: Decimal
    lowest_after: Decimal
    lowest_date: date


@dataclass
class _Findings:
    flags: List[ValidationFlag] = field(default_factory=list)
    risk_score: int = 0

    def add(self, flag: ValidationFlag, weight: int = 0) -> None:
        self.flags.append(flag)
        self.risk_score += weight

    @property
    def has_critical(self) -> bool:
        return any(flag.severity == SEVERITY_CRITICAL for flag in self.flags)


def normalize_iban(iban: Optional[str]) -> str:
    """Strip spaces and uppercase IBAN for reliable comparison."""
    if not iban:
        return ""
    return re.sub(r"\s+", "", iban).upper()


def normalize_name(name: Optional[str]) -> str:
    """Lower-case and collapse whitespace so 'ASIMEX  Ltd' and 'Asimex Ltd' are the same counterparty."""
    return " ".join((name or "").lower().split())


def is_payable(invoice_type: str) -> bool:
    """Money leaves the account for costs and receipts; sales invoices and credit notes bring money in."""
    return invoice_type in PAYABLE_INVOICE_TYPES


def reference_mentions_number(reference: Optional[str], invoice_number: str) -> bool:
    """The invoice number appears as a whole token, so '12' does not match 'Invoice 1234'."""
    if not reference:
        return False

    pattern = rf"(?<![A-Za-z0-9]){re.escape(invoice_number)}(?![A-Za-z0-9])"
    return re.search(pattern, reference, flags=re.IGNORECASE) is not None


def payment_impact(position: CashPosition, amount: Decimal, on_date: date, label: str) -> Optional[PaymentImpact]:
    """Lowest base-scenario balance with and without paying `amount` on `on_date`; None when beyond the horizon."""
    needed_days = (on_date - position.inputs.as_of).days
    if needed_days > FORECAST_HORIZON_MAX_DAYS:
        return None

    inputs = replace(position.inputs, horizon_days=max(position.inputs.horizon_days, needed_days, 1))
    result = simulate(inputs, [CashChange(on_date=on_date, amount=-amount, label=label)], position.planned)

    before = result.baseline.scenarios[SCENARIO_BASE].indicators
    after = result.simulated.scenarios[SCENARIO_BASE].indicators
    return PaymentImpact(
        payment_day=max(on_date, inputs.as_of + timedelta(days=1)),
        lowest_before=before.lowest_balance,
        lowest_after=after.lowest_balance,
        lowest_date=after.lowest_balance_date,
    )


def _first_critical_description(flags: List[ValidationFlag]) -> str:
    critical = next((flag for flag in flags if flag.severity == SEVERITY_CRITICAL), flags[0])
    return critical.description


def _vat_rates_text() -> str:
    return ", ".join(f"{rate.normalize()}%" for rate in STANDARD_VAT_RATES)


def _check_arithmetic(req: InvoiceValidateRequest, findings: _Findings) -> bool:
    expected_gross = req.net_amount + req.tax_amount
    arithmetic_valid = abs(expected_gross - req.gross_amount) <= ARITHMETIC_TOLERANCE

    if not arithmetic_valid:
        findings.add(ValidationFlag(
            code="ARITHMETIC_MISMATCH",
            severity=SEVERITY_CRITICAL,
            title="Math Calculation Error on Invoice",
            description=(
                f"Net amount ({req.net_amount:,.2f}) + Tax ({req.tax_amount:,.2f}) equals {expected_gross:,.2f}, "
                f"which does not match the stated gross payable of {req.gross_amount:,.2f} {req.currency}."
            ),
            evidence={"net": float(req.net_amount), "tax": float(req.tax_amount), "stated_gross": float(req.gross_amount)}
        ), RISK_WEIGHT_ARITHMETIC)
    elif req.net_amount > 0 and req.tax_amount > 0:
        effective_rate = (req.tax_amount / req.net_amount) * HUNDRED
        if not any(abs(effective_rate - rate) < VAT_RATE_TOLERANCE for rate in STANDARD_VAT_RATES):
            findings.add(ValidationFlag(
                code="NON_STANDARD_TAX_RATE",
                severity=SEVERITY_WARNING,
                title="Non-Standard VAT Rate Detected",
                description=f"Calculated tax rate is {effective_rate:.1f}%, which deviates from standard rates ({_vat_rates_text()}).",
                evidence={"effective_tax_rate": float(effective_rate)}
            ), RISK_WEIGHT_NON_STANDARD_VAT)

    if req.gross_amount <= ZERO:
        findings.add(ValidationFlag(
            code="INVALID_AMOUNT",
            severity=SEVERITY_CRITICAL,
            title="Gross Amount Must Be Positive",
            description=f"Invoice has an invalid non-positive gross amount: {req.gross_amount} {req.currency}.",
            evidence={"gross_amount": float(req.gross_amount)}
        ), RISK_WEIGHT_INVALID_AMOUNT)

    return arithmetic_valid


def _same_counterparty(column, name: str):
    return func.lower(func.trim(column)) == normalize_name(name)


async def _existing_invoice(db: AsyncSession, req: InvoiceValidateRequest) -> Optional[Invoice]:
    query = select(Invoice).where(
        Invoice.invoice_number == req.invoice_number,
        _same_counterparty(Invoice.counterparty_name, req.counterparty_name),
    ).order_by(Invoice.created_at.desc()).limit(1)
    return (await db.execute(query)).scalars().first()


async def _paying_transaction(db: AsyncSession, req: InvoiceValidateRequest) -> Optional[Transaction]:
    query = select(Transaction).where(
        Transaction.payment_reference.ilike(contains_pattern(req.invoice_number), escape=LIKE_ESCAPE_CHAR),
        _same_counterparty(Transaction.counterparty_name, req.counterparty_name),
    ).order_by(Transaction.booking_date.desc()).limit(PAID_CANDIDATES_LIMIT)

    payable = is_payable(req.invoice_type)
    for transaction in (await db.execute(query)).scalars().all():
        right_direction = (transaction.amount < 0) == payable
        if right_direction and reference_mentions_number(transaction.payment_reference, req.invoice_number):
            return transaction

    return None


async def _check_duplicates(db: AsyncSession, req: InvoiceValidateRequest, findings: _Findings) -> bool:
    existing_invoice = await _existing_invoice(db, req)
    if existing_invoice:
        findings.add(ValidationFlag(
            code="DUPLICATE_INVOICE_RECORD",
            severity=SEVERITY_CRITICAL,
            title="Duplicate Invoice Detected",
            description=f"Invoice #{req.invoice_number} from '{req.counterparty_name}' has already been registered in the system.",
            evidence={"existing_invoice_id": str(existing_invoice.id), "status": existing_invoice.validation_status}
        ), RISK_WEIGHT_DUPLICATE)
        return True

    paid_tx = await _paying_transaction(db, req)
    if paid_tx:
        findings.add(ValidationFlag(
            code="INVOICE_ALREADY_PAID",
            severity=SEVERITY_CRITICAL,
            title="Invoice Already Paid in Bank Ledger",
            description=(
                f"Invoice #{req.invoice_number} appears to have already been settled on {paid_tx.booking_date} "
                f"via transaction reference '{paid_tx.payment_reference}' ({abs(paid_tx.amount):,.2f} {paid_tx.currency})."
            ),
            evidence={"transaction_id": str(paid_tx.id), "booking_date": str(paid_tx.booking_date), "amount": float(paid_tx.amount)}
        ), RISK_WEIGHT_ALREADY_PAID)
        return True

    return False


async def _vendor_payments(db: AsyncSession, req: InvoiceValidateRequest) -> List[Transaction]:
    query = select(Transaction).where(
        _same_counterparty(Transaction.counterparty_name, req.counterparty_name),
        Transaction.amount < 0,
    ).order_by(Transaction.booking_date.desc()).limit(KNOWN_VENDOR_TRANSACTIONS_LIMIT)
    return list((await db.execute(query)).scalars().all())


def _check_iban(req: InvoiceValidateRequest, vendor_payments: Sequence[Transaction], findings: _Findings) -> str:
    clean_iban = normalize_iban(req.counterparty_iban)
    if not clean_iban:
        return IBAN_STATUS_NEW

    known_ibans = {normalize_iban(t.counterparty_account) for t in vendor_payments if t.counterparty_account}
    if not known_ibans:
        findings.add(ValidationFlag(
            code="NEW_VENDOR_IBAN",
            severity=SEVERITY_INFO,
            title="First Time Vendor",
            description=f"No prior payment history found for vendor '{req.counterparty_name}'.",
            evidence={"new_iban": clean_iban}
        ), RISK_WEIGHT_NEW_VENDOR)
        return IBAN_STATUS_NEW

    if clean_iban in known_ibans:
        findings.add(ValidationFlag(
            code="IBAN_VERIFIED",
            severity=SEVERITY_INFO,
            title="Vendor IBAN Verified",
            description=f"IBAN matches previously verified payments to {req.counterparty_name}.",
            evidence={"matched_iban": clean_iban}
        ))
        return IBAN_STATUS_VERIFIED

    historical_sample = sorted(known_ibans)[0]
    findings.add(ValidationFlag(
        code="IBAN_MISMATCH_SUSPECTED_PHISHING",
        severity=SEVERITY_CRITICAL,
        title="Account Number Mismatch (Potential Phishing)",
        description=(
            f"CRITICAL WARNING: Vendor '{req.counterparty_name}' has historically been paid to {historical_sample}, "
            f"but this invoice requests payment to a DIFFERENT account: {clean_iban}. "
            f"Verify this change directly with the vendor before approving payment."
        ),
        evidence={"invoice_iban": clean_iban, "known_historical_ibans": sorted(known_ibans)}
    ), RISK_WEIGHT_IBAN_MISMATCH)
    return IBAN_STATUS_MISMATCH


def _check_price_spike(req: InvoiceValidateRequest, vendor_payments: Sequence[Transaction], findings: _Findings) -> bool:
    past_amounts = [abs(t.amount) for t in vendor_payments if t.currency == req.currency]
    if not past_amounts or req.gross_amount <= ZERO:
        return False

    avg_amount = sum(past_amounts) / Decimal(len(past_amounts))
    if req.gross_amount <= avg_amount * PRICE_SPIKE_RATIO or req.gross_amount <= PRICE_SPIKE_MIN_AMOUNT:
        return False

    hike_pct = ((req.gross_amount - avg_amount) / avg_amount) * HUNDRED
    findings.add(ValidationFlag(
        code="PRICE_SPIKE_DETECTED",
        severity=SEVERITY_WARNING,
        title="Abnormal Spending Spike for Vendor",
        description=(
            f"Invoice gross amount ({req.gross_amount:,.2f} {req.currency}) is {hike_pct:.1f}% higher "
            f"than historical average payment ({avg_amount:,.2f} {req.currency}) for '{req.counterparty_name}'."
        ),
        evidence={"average_amount": float(avg_amount), "hike_percent": float(hike_pct)}
    ), RISK_WEIGHT_PRICE_SPIKE)
    return True


def _info_flag(code: str, title: str, description: str) -> ValidationFlag:
    return ValidationFlag(code=code, severity=SEVERITY_INFO, title=title, description=description)


def _usable_position(req: InvoiceValidateRequest, position: Optional[CashPosition], findings: _Findings) -> Optional[CashPosition]:
    if position is None:
        findings.add(_info_flag("NO_ACCOUNT_DATA", NO_ACCOUNT_DATA_TITLE, NO_ACCOUNT_DATA_DESCRIPTION))
        return None

    if position.currency != req.currency:
        findings.add(_info_flag(
            "CURRENCY_NOT_CONVERTED",
            "Liquidity Not Checked: Different Currency",
            f"The invoice is in {req.currency} but the account is in {position.currency}; "
            f"there is no exchange rate to convert it, so the cash impact was not calculated.",
        ))
        return None

    return position


def _check_liquidity(req: InvoiceValidateRequest, position: CashPosition, findings: _Findings) -> Optional[bool]:
    label = INVOICE_PAYMENT_LABEL.format(number=req.invoice_number, counterparty=req.counterparty_name)
    impact = payment_impact(position, req.gross_amount, req.due_date, label)
    if impact is None:
        findings.add(_info_flag(
            "DUE_DATE_BEYOND_FORECAST",
            "Liquidity Not Checked: Due Date Too Far Ahead",
            f"The due date {req.due_date} is more than {FORECAST_HORIZON_MAX_DAYS} days after the last bank data "
            f"({position.inputs.as_of}), beyond the forecast horizon.",
        ))
        return None

    buffer = position.inputs.safety_buffer
    evidence = {
        "payment_day": str(impact.payment_day),
        "lowest_balance_without_payment": float(impact.lowest_before),
        "lowest_balance_with_payment": float(impact.lowest_after),
        "lowest_balance_date": str(impact.lowest_date),
        "overdraft_limit": float(position.overdraft_limit),
        "min_buffer": float(buffer),
    }

    if impact.lowest_after < -position.overdraft_limit:
        findings.add(ValidationFlag(
            code="INSOLVENCY_DEFICIT_RISK",
            severity=SEVERITY_CRITICAL,
            title="Payment Exceeds Overdraft Limit",
            description=(
                f"Paying {req.gross_amount:,.2f} {req.currency} on {impact.payment_day} takes the forecast balance down to "
                f"{impact.lowest_after:,.2f} on {impact.lowest_date}, beyond the overdraft limit of {position.overdraft_limit:,.2f}."
            ),
            evidence=evidence,
        ), RISK_WEIGHT_INSOLVENCY)
        return False

    if impact.lowest_after < ZERO:
        findings.add(ValidationFlag(
            code="OVERDRAFT_USED",
            severity=SEVERITY_WARNING,
            title="Payment Pushes the Account into Overdraft",
            description=(
                f"Paying {req.gross_amount:,.2f} {req.currency} on {impact.payment_day} leaves a forecast balance of "
                f"{impact.lowest_after:,.2f} on {impact.lowest_date}, inside the overdraft limit of {position.overdraft_limit:,.2f}."
            ),
            evidence=evidence,
        ), RISK_WEIGHT_OVERDRAFT_USED)
        return False

    if impact.lowest_after < buffer:
        findings.add(ValidationFlag(
            code="SAFETY_BUFFER_BREACH",
            severity=SEVERITY_WARNING,
            title="Payment Violates Cash Safety Buffer",
            description=(
                f"Paying {req.gross_amount:,.2f} {req.currency} on {impact.payment_day} leaves a forecast low of "
                f"{impact.lowest_after:,.2f} on {impact.lowest_date}, below your safety threshold of {buffer:,.2f}."
            ),
            evidence=evidence,
        ), RISK_WEIGHT_BUFFER_BREACH)

    return True


def _check_early_discount(
    req: InvoiceValidateRequest,
    position: Optional[CashPosition],
    findings: _Findings,
) -> Tuple[Optional[EarlyDiscountOpportunity], Optional[PaymentImpact]]:
    if not (req.early_discount_percent and req.early_discount_percent > ZERO and req.early_discount_days):
        return None, None

    deadline = req.issue_date + timedelta(days=req.early_discount_days)
    today = position.inputs.as_of if position else date.today()
    if deadline < today:
        findings.add(ValidationFlag(
            code="EARLY_DISCOUNT_EXPIRED",
            severity=SEVERITY_INFO,
            title="Early Payment Discount Expired",
            description=f"The {req.early_discount_percent}% discount ended on {deadline}; today is {today}. Pay the full amount by {req.due_date}.",
            evidence={"deadline": str(deadline), "today": str(today)},
        ))
        return None, None

    savings = (req.gross_amount * (req.early_discount_percent / HUNDRED)).quantize(CENT)
    discounted_payable = req.gross_amount - savings

    impact = None
    if position:
        label = INVOICE_PAYMENT_LABEL.format(number=req.invoice_number, counterparty=req.counterparty_name)
        impact = payment_impact(position, discounted_payable, deadline, label)
    is_safe = None if impact is None else impact.lowest_after >= position.inputs.safety_buffer

    reasoning = (
        f"Vendor offers a {req.early_discount_percent}% early payment discount if paid by {deadline} "
        f"({req.early_discount_days} days). You will save {savings:,.2f} {req.currency}."
    )
    if impact is not None:
        reasoning += (
            f" Paying early keeps the forecast low at {impact.lowest_after:,.2f} "
            f"({'above' if is_safe else 'below'} the safety buffer)."
        )

    opportunity = EarlyDiscountOpportunity(
        is_available=True,
        discount_percent=req.early_discount_percent,
        deadline_date=deadline,
        savings_amount=savings,
        effective_payable=discounted_payable,
        is_liquidity_safe=is_safe,
        reasoning=reasoning,
    )
    findings.add(ValidationFlag(
        code="EARLY_DISCOUNT_AVAILABLE",
        severity=SEVERITY_INFO,
        title=f"Early Payment Discount Available: Save {savings:,.2f} {req.currency}",
        description=reasoning,
        evidence={"savings": float(savings), "deadline": str(deadline), "discount_percent": float(req.early_discount_percent)}
    ))
    return opportunity, impact


def _risk_level(risk_score: int) -> str:
    if risk_score >= RISK_SCORE_CRITICAL:
        return RISK_LEVEL_CRITICAL
    if risk_score >= RISK_SCORE_HIGH:
        return RISK_LEVEL_HIGH
    if risk_score >= RISK_SCORE_MEDIUM:
        return RISK_LEVEL_MEDIUM
    return RISK_LEVEL_LOW


def _executive_summary(
    req: InvoiceValidateRequest,
    findings: _Findings,
    is_valid: bool,
    discount: Optional[EarlyDiscountOpportunity],
) -> str:
    if findings.has_critical:
        return (
            f"BLOCK PAYMENT: Critical risk detected on invoice #{req.invoice_number} from {req.counterparty_name} "
            f"(Risk Score: {findings.risk_score}/100). Flags: {', '.join(f.title for f in findings.flags if f.severity == SEVERITY_CRITICAL)}."
        )
    if discount and discount.is_liquidity_safe and is_valid:
        return (
            f"INVOICE VERIFIED WITH SAVINGS: Invoice #{req.invoice_number} is valid. "
            f"Recommendation: Pay early by {discount.deadline_date} to capture a {discount.savings_amount:,.2f} {req.currency} cash discount."
        )
    if is_valid:
        return (
            f"INVOICE VERIFIED: Invoice #{req.invoice_number} from {req.counterparty_name} passes all compliance checks. "
            f"Amount: {req.gross_amount:,.2f} {req.currency}, due on {req.due_date}."
        )
    return (
        f"CAUTION: Invoice #{req.invoice_number} has warnings (Risk Score: {findings.risk_score}/100). "
        f"Review flags before scheduling payment."
    )


def _action_card(
    req: InvoiceValidateRequest,
    findings: _Findings,
    is_valid: bool,
    discount: Optional[EarlyDiscountOpportunity],
    discount_impact: Optional[PaymentImpact],
) -> Optional[Dict[str, Any]]:
    if findings.has_critical:
        return {
            "title": f"Hold Payment: Critical Warning on #{req.invoice_number}",
            "category": f"{req.counterparty_name} · Fraud Guard",
            "agent_type": AGENT_TYPE_FRAUD_GUARD,
            "body": _first_critical_description(findings.flags),
            "swipe_right_action": "Contact vendor to verify",
            "swipe_left_action": "Reject invoice & mark suspicious",
            "impact_metrics": {"prevented_loss": float(req.gross_amount)},
        }

    if discount and discount.is_liquidity_safe and is_valid and discount_impact:
        return {
            "title": f"Take {req.early_discount_percent}% Early Discount with {req.counterparty_name}?",
            "category": f"{req.counterparty_name} · Accounts Payable",
            "agent_type": AGENT_TYPE_PAYABLES_OPTIMIZER,
            "body": (
                f"Pay invoice #{req.invoice_number} by {discount.deadline_date} "
                f"instead of {req.due_date} to save {discount.savings_amount:,.2f} {req.currency}. "
                f"The forecast low stays at {discount_impact.lowest_after:,.2f}, above the safety buffer."
            ),
            "swipe_right_action": f"Pay early, take {discount.savings_amount:,.2f} {req.currency} discount",
            "swipe_left_action": f"Pay on due date ({req.gross_amount:,.2f} {req.currency})",
            "impact_metrics": {
                "cash_protected": float(discount.savings_amount),
                "cash_delta": -float(discount.effective_payable),
            },
        }

    return None


def _card_dedupe_key(req: InvoiceValidateRequest, agent_type: str) -> str:
    key = INVOICE_CARD_DEDUPE_KEY.format(
        counterparty=normalize_name(req.counterparty_name),
        number=req.invoice_number,
        agent=agent_type,
    )
    return key[:DEDUPE_KEY_MAX_LENGTH]


async def _save_card_once(db: AsyncSession, req: InvoiceValidateRequest, card: Dict[str, Any], summary: str) -> None:
    dedupe_key = _card_dedupe_key(req, card["agent_type"])
    exists = await db.execute(select(AgentAction.id).where(AgentAction.dedupe_key == dedupe_key).limit(1))
    if exists.first():
        return

    db.add(AgentAction(
        title=card["title"],
        agent_type=card["agent_type"],
        trigger_reason=card["body"],
        recommended_action=INVOICE_ACTION_RECOMMENDATION,
        target_amount=req.gross_amount,
        currency=req.currency,
        explanation=summary,
        impact_simulation=card["impact_metrics"],
        source_type=SOURCE_INVOICE,
        source_id=req.invoice_number[:SOURCE_ID_MAX_LENGTH],
        dedupe_key=dedupe_key,
        status=ACTION_STATUS_PENDING,
        execution_mode=EXECUTION_MODE_SIMULATED,
    ))
    await db.flush()


async def validate_invoice_logic(
    db: AsyncSession,
    req: InvoiceValidateRequest,
    auto_create_action_card: bool = True,
    position: Optional[CashPosition] = None,
) -> ValidationReport:
    """
    Core deterministic validation mechanic for invoices and receipts.
    Evaluates:
      1. Arithmetic integrity (Net + VAT == Gross)
      2. Duplicate invoice detection (same counterparty, invoice number as a whole token)
      3. Counterparty IBAN verification & anti-phishing (payables only)
      4. Price creep / abnormal spending anomaly (past payments in the same currency)
      5. Liquidity over the forecast up to the due date, incl. overdraft limit (payables only)
      6. Early payment discount (Skonto) that has not expired yet

    Sales invoices and credit notes bring money in, so they skip the payable-only checks.
    Follows the architectural rule: 'Silnik liczy, AI tłumaczy'.
    """
    findings = _Findings()
    payable = is_payable(req.invoice_type)

    arithmetic_valid = _check_arithmetic(req, findings)
    duplicate_detected = await _check_duplicates(db, req, findings)

    iban_status = IBAN_STATUS_NEW
    price_anomaly_detected = False
    liquidity_safe: Optional[bool] = True
    discount: Optional[EarlyDiscountOpportunity] = None
    discount_impact: Optional[PaymentImpact] = None

    if payable:
        vendor_payments = await _vendor_payments(db, req)
        iban_status = _check_iban(req, vendor_payments, findings)
        price_anomaly_detected = _check_price_spike(req, vendor_payments, findings)

        usable = _usable_position(req, position, findings)
        liquidity_safe = _check_liquidity(req, usable, findings) if usable else None
        discount, discount_impact = _check_early_discount(req, usable, findings)

    findings.risk_score = min(max(findings.risk_score, 0), RISK_SCORE_MAX)
    risk_level = _risk_level(findings.risk_score)
    is_valid = risk_level in (RISK_LEVEL_LOW, RISK_LEVEL_MEDIUM) and not findings.has_critical

    executive_summary = _executive_summary(req, findings, is_valid, discount)
    suggested_action_card = _action_card(req, findings, is_valid, discount, discount_impact)

    if auto_create_action_card and suggested_action_card:
        await _save_card_once(db, req, suggested_action_card, executive_summary)

    return ValidationReport(
        invoice_number=req.invoice_number,
        counterparty_name=req.counterparty_name,
        gross_amount=req.gross_amount,
        currency=req.currency,
        is_valid=is_valid,
        risk_level=risk_level,
        risk_score=findings.risk_score,
        arithmetic_valid=arithmetic_valid,
        duplicate_detected=duplicate_detected,
        iban_status=iban_status,
        price_anomaly_detected=price_anomaly_detected,
        liquidity_safe=liquidity_safe,
        flags=findings.flags,
        early_discount=discount,
        executive_summary=executive_summary,
        suggested_action_card=suggested_action_card
    )
