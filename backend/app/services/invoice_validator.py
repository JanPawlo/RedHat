import re
from datetime import timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.const.action import (
    ACTION_STATUS_PENDING,
    AGENT_TYPE_FRAUD_GUARD,
    AGENT_TYPE_PAYABLES_OPTIMIZER,
    EXECUTION_MODE_SIMULATED,
    INVOICE_ACTION_RECOMMENDATION,
)
from app.const.company import DEFAULT_MIN_SAFETY_BUFFER, MIN_SAFETY_BUFFER_KEY
from app.const.invoice import (
    ARITHMETIC_TOLERANCE,
    IBAN_STATUS_MISMATCH,
    IBAN_STATUS_NEW,
    IBAN_STATUS_VERIFIED,
    KNOWN_VENDOR_TRANSACTIONS_LIMIT,
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
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    STANDARD_VAT_RATES,
    VAT_RATE_TOLERANCE,
)
from app.const.messages import NO_ACCOUNT_DATA_DESCRIPTION, NO_ACCOUNT_DATA_TITLE
from app.const.sql import LIKE_ESCAPE_CHAR
from app.core.sql import contains_pattern
from app.models.company import CompanyProfile
from app.models.account import BankAccount
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.models.action import AgentAction
from app.schemas.invoice import (
    InvoiceValidateRequest,
    ValidationReport,
    ValidationFlag,
    EarlyDiscountOpportunity,
)


def normalize_iban(iban: Optional[str]) -> str:
    """Strip spaces and uppercase IBAN for reliable comparison."""
    if not iban:
        return ""
    return re.sub(r"\s+", "", iban).upper()


def _first_critical_description(flags: List[ValidationFlag]) -> str:
    critical = next((flag for flag in flags if flag.severity == SEVERITY_CRITICAL), flags[0])
    return critical.description


async def validate_invoice_logic(
    db: AsyncSession,
    req: InvoiceValidateRequest,
    auto_create_action_card: bool = True,
) -> ValidationReport:
    """
    Core deterministic validation mechanic for invoices and receipts.
    Evaluates:
      1. Arithmetic integrity (Net + VAT == Gross)
      2. Duplicate invoice detection
      3. Counterparty IBAN verification & anti-phishing
      4. Price creep / abnormal spending anomaly
      5. Cash flow & safety buffer breach impact
      6. Early payment discount (Skonto) opportunity

    Follows the architectural rule: 'Silnik liczy, AI tłumaczy'.
    """
    flags: List[ValidationFlag] = []
    risk_score = 0
    clean_iban = normalize_iban(req.counterparty_iban)

    # -------------------------------------------------------------
    # 1. Arithmetic & Tax Integrity Check
    # -------------------------------------------------------------
    expected_gross = req.net_amount + req.tax_amount
    diff = abs(expected_gross - req.gross_amount)
    arithmetic_valid = diff <= ARITHMETIC_TOLERANCE

    if not arithmetic_valid:
        flags.append(ValidationFlag(
            code="ARITHMETIC_MISMATCH",
            severity=SEVERITY_CRITICAL,
            title="Math Calculation Error on Invoice",
            description=(
                f"Net amount (€{req.net_amount:,.2f}) + Tax (€{req.tax_amount:,.2f}) equals €{expected_gross:,.2f}, "
                f"which does not match the stated gross payable of €{req.gross_amount:,.2f}."
            ),
            evidence={"net": float(req.net_amount), "tax": float(req.tax_amount), "stated_gross": float(req.gross_amount)}
        ))
        risk_score += 40
    else:
        # Check if tax rate is reasonable when tax is present
        if req.net_amount > 0 and req.tax_amount > 0:
            effective_rate = (req.tax_amount / req.net_amount) * Decimal("100.00")
            if not any(abs(effective_rate - rate) < VAT_RATE_TOLERANCE for rate in STANDARD_VAT_RATES):
                flags.append(ValidationFlag(
                    code="NON_STANDARD_TAX_RATE",
                    severity=SEVERITY_WARNING,
                    title="Non-Standard VAT Rate Detected",
                    description=f"Calculated tax rate is {effective_rate:.1f}%, which deviates from standard rates (19%, 7%, 23%, 8%).",
                    evidence={"effective_tax_rate": float(effective_rate)}
                ))
                risk_score += 15

    if req.gross_amount <= Decimal("0.00"):
        flags.append(ValidationFlag(
            code="INVALID_AMOUNT",
            severity=SEVERITY_CRITICAL,
            title="Gross Amount Must Be Positive",
            description=f"Invoice has an invalid non-positive gross amount: €{req.gross_amount}.",
            evidence={"gross_amount": float(req.gross_amount)}
        ))
        risk_score += 50

    # -------------------------------------------------------------
    # 2. Duplicate Detection Check
    # -------------------------------------------------------------
    duplicate_detected = False
    
    # A) Check invoices table
    existing_inv_query = select(Invoice).where(
        Invoice.invoice_number == req.invoice_number,
        Invoice.counterparty_name.ilike(contains_pattern(req.counterparty_name), escape=LIKE_ESCAPE_CHAR)
    ).order_by(Invoice.created_at.desc()).limit(1)
    existing_inv_result = await db.execute(existing_inv_query)
    existing_invoice = existing_inv_result.scalars().first()

    # B) Check bank transactions ledger (e.g. "Invoice AS-69664")
    tx_dup_query = select(Transaction).where(
        Transaction.payment_reference.ilike(contains_pattern(req.invoice_number), escape=LIKE_ESCAPE_CHAR)
    ).order_by(Transaction.booking_date.desc()).limit(1)
    tx_dup_result = await db.execute(tx_dup_query)
    paid_tx = tx_dup_result.scalars().first()

    if existing_invoice:
        duplicate_detected = True
        flags.append(ValidationFlag(
            code="DUPLICATE_INVOICE_RECORD",
            severity=SEVERITY_CRITICAL,
            title="Duplicate Invoice Detected",
            description=f"Invoice #{req.invoice_number} from '{req.counterparty_name}' has already been registered in the system.",
            evidence={"existing_invoice_id": str(existing_invoice.id), "status": existing_invoice.validation_status}
        ))
        risk_score += 50
    elif paid_tx:
        duplicate_detected = True
        flags.append(ValidationFlag(
            code="INVOICE_ALREADY_PAID",
            severity=SEVERITY_CRITICAL,
            title="Invoice Already Paid in Bank Ledger",
            description=(
                f"Invoice #{req.invoice_number} appears to have already been settled on {paid_tx.booking_date} "
                f"via transaction reference '{paid_tx.payment_reference}' (€{abs(paid_tx.amount):,.2f})."
            ),
            evidence={"transaction_id": str(paid_tx.id), "booking_date": str(paid_tx.booking_date), "amount": float(paid_tx.amount)}
        ))
        risk_score += 60

    # -------------------------------------------------------------
    # 3. Counterparty IBAN Consistency (Anti-Phishing / Fraud Check)
    # -------------------------------------------------------------
    iban_status = IBAN_STATUS_NEW
    vendor_pattern = contains_pattern(req.counterparty_name)

    # Search past transactions to find known bank account details for this vendor
    known_tx_query = select(Transaction).where(
        Transaction.counterparty_name.ilike(vendor_pattern, escape=LIKE_ESCAPE_CHAR),
        Transaction.counterparty_account.isnot(None),
        Transaction.counterparty_account != ""
    ).order_by(Transaction.booking_date.desc()).limit(KNOWN_VENDOR_TRANSACTIONS_LIMIT)
    
    known_txs = (await db.execute(known_tx_query)).scalars().all()
    known_ibans = {normalize_iban(t.counterparty_account) for t in known_txs if t.counterparty_account}

    if clean_iban:
        if known_ibans:
            if clean_iban in known_ibans:
                iban_status = IBAN_STATUS_VERIFIED
                flags.append(ValidationFlag(
                    code="IBAN_VERIFIED",
                    severity=SEVERITY_INFO,
                    title="Vendor IBAN Verified",
                    description=f"IBAN matches previously verified payments to {req.counterparty_name}.",
                    evidence={"matched_iban": clean_iban}
                ))
            else:
                iban_status = IBAN_STATUS_MISMATCH
                historical_sample = list(known_ibans)[0]
                flags.append(ValidationFlag(
                    code="IBAN_MISMATCH_SUSPECTED_PHISHING",
                    severity=SEVERITY_CRITICAL,
                    title="Account Number Mismatch (Potential Phishing)",
                    description=(
                        f"CRITICAL WARNING: Vendor '{req.counterparty_name}' has historically been paid to {historical_sample}, "
                        f"but this invoice requests payment to a DIFFERENT account: {clean_iban}. "
                        f"Verify this change directly with the vendor before approving payment."
                    ),
                    evidence={"invoice_iban": clean_iban, "known_historical_ibans": list(known_ibans)}
                ))
                risk_score += 65
        else:
            iban_status = IBAN_STATUS_NEW
            flags.append(ValidationFlag(
                code="NEW_VENDOR_IBAN",
                severity=SEVERITY_INFO,
                title="First Time Vendor",
                description=f"No prior payment history found for vendor '{req.counterparty_name}'.",
                evidence={"new_iban": clean_iban}
            ))
            risk_score += 5

    # -------------------------------------------------------------
    # 4. Price Anomaly & Margin Creep Check
    # -------------------------------------------------------------
    price_anomaly_detected = False
    if known_txs and req.gross_amount > Decimal("0.00"):
        past_amounts = [abs(t.amount_base_currency) for t in known_txs]
        avg_amount = sum(past_amounts) / Decimal(len(past_amounts))

        if req.gross_amount > avg_amount * PRICE_SPIKE_RATIO and req.gross_amount > PRICE_SPIKE_MIN_AMOUNT:
            price_anomaly_detected = True
            hike_pct = ((req.gross_amount - avg_amount) / avg_amount) * Decimal("100.0")
            flags.append(ValidationFlag(
                code="PRICE_SPIKE_DETECTED",
                severity=SEVERITY_WARNING,
                title="Abnormal Spending Spike for Vendor",
                description=(
                    f"Invoice gross amount (€{req.gross_amount:,.2f}) is {hike_pct:.1f}% higher "
                    f"than historical average payment (€{avg_amount:,.2f}) for '{req.counterparty_name}'."
                ),
                evidence={"average_amount": float(avg_amount), "hike_percent": float(hike_pct)}
            ))
            risk_score += 20

    # -------------------------------------------------------------
    # 5. Liquidity Impact & Safety Buffer Check
    # -------------------------------------------------------------
    account_query = select(BankAccount).where(BankAccount.is_primary == True).order_by(BankAccount.created_at).limit(1)
    primary_acc = (await db.execute(account_query)).scalars().first()
    
    company_query = select(CompanyProfile).order_by(CompanyProfile.created_at).limit(1)
    company = (await db.execute(company_query)).scalars().first()

    min_buffer = Decimal(str(DEFAULT_MIN_SAFETY_BUFFER))
    if company and MIN_SAFETY_BUFFER_KEY in company.settings:
        min_buffer = Decimal(str(company.settings[MIN_SAFETY_BUFFER_KEY]))

    current_cash: Optional[Decimal] = primary_acc.current_balance if primary_acc else None
    liquidity_safe: Optional[bool] = None

    if current_cash is None:
        flags.append(ValidationFlag(
            code="NO_ACCOUNT_DATA",
            severity=SEVERITY_INFO,
            title=NO_ACCOUNT_DATA_TITLE,
            description=NO_ACCOUNT_DATA_DESCRIPTION,
        ))
    else:
        liquidity_safe = True
        projected_cash_after_payment = current_cash - req.gross_amount

        if projected_cash_after_payment < Decimal("0.00"):
            liquidity_safe = False
            flags.append(ValidationFlag(
                code="INSOLVENCY_DEFICIT_RISK",
                severity=SEVERITY_CRITICAL,
                title="Payment Will Cause Immediate Account Overdraft",
                description=(
                    f"Paying €{req.gross_amount:,.2f} will reduce your cash balance from €{current_cash:,.2f} "
                    f"to -€{abs(projected_cash_after_payment):,.2f}."
                ),
                evidence={"current_balance": float(current_cash), "projected_balance": float(projected_cash_after_payment)}
            ))
            risk_score += 45
        elif projected_cash_after_payment < min_buffer:
            flags.append(ValidationFlag(
                code="SAFETY_BUFFER_BREACH",
                severity=SEVERITY_WARNING,
                title="Payment Violates Cash Safety Buffer",
                description=(
                    f"Paying €{req.gross_amount:,.2f} leaves €{projected_cash_after_payment:,.2f}, "
                    f"which falls below your safety threshold of €{min_buffer:,.2f}."
                ),
                evidence={"min_buffer": float(min_buffer), "projected_balance": float(projected_cash_after_payment)}
            ))
            risk_score += 15

    # -------------------------------------------------------------
    # 6. Early Payment Discount (Skonto) Opportunity Check
    # -------------------------------------------------------------
    early_discount_opp: Optional[EarlyDiscountOpportunity] = None
    if req.early_discount_percent and req.early_discount_percent > Decimal("0.00") and req.early_discount_days:
        deadline = req.issue_date + timedelta(days=req.early_discount_days)
        savings = (req.gross_amount * (req.early_discount_percent / Decimal("100.00"))).quantize(Decimal("0.01"))
        discounted_payable = req.gross_amount - savings
        
        is_safe = None if current_cash is None else (current_cash - discounted_payable) >= min_buffer

        reasoning = (
            f"Vendor offers a {req.early_discount_percent}% early payment discount if paid by {deadline} "
            f"({req.early_discount_days} days). You will save €{savings:,.2f}."
        )
        if current_cash is not None:
            reasoning += (
                f" Current cash balance of €{current_cash:,.2f} "
                f"{'comfortably covers' if is_safe else 'is tight for'} this early payout."
            )

        early_discount_opp = EarlyDiscountOpportunity(
            is_available=True,
            discount_percent=req.early_discount_percent,
            deadline_date=deadline,
            savings_amount=savings,
            effective_payable=discounted_payable,
            is_liquidity_safe=is_safe,
            reasoning=reasoning,
        )

        flags.append(ValidationFlag(
            code="EARLY_DISCOUNT_AVAILABLE",
            severity=SEVERITY_INFO,
            title=f"Early Payment Discount Available: Save €{savings:,.2f}",
            description=reasoning,
            evidence={"savings": float(savings), "deadline": str(deadline), "discount_percent": float(req.early_discount_percent)}
        ))

    # -------------------------------------------------------------
    # Synthesize Final Verdict & Suggested Swipe Action Card
    # -------------------------------------------------------------
    risk_score = min(max(risk_score, 0), RISK_SCORE_MAX)
    
    if risk_score >= RISK_SCORE_CRITICAL:
        risk_level = RISK_LEVEL_CRITICAL
    elif risk_score >= RISK_SCORE_HIGH:
        risk_level = RISK_LEVEL_HIGH
    elif risk_score >= RISK_SCORE_MEDIUM:
        risk_level = RISK_LEVEL_MEDIUM
    else:
        risk_level = RISK_LEVEL_LOW

    is_valid = risk_level in (RISK_LEVEL_LOW, RISK_LEVEL_MEDIUM)

    # Generate Plain-Language Executive Summary for the LLM
    if risk_level == RISK_LEVEL_CRITICAL:
        executive_summary = (
            f"BLOCK PAYMENT: Critical risk detected on invoice #{req.invoice_number} from {req.counterparty_name} "
            f"(Risk Score: {risk_score}/100). Flags: {', '.join(f.title for f in flags if f.severity == SEVERITY_CRITICAL)}."
        )
    elif early_discount_opp and early_discount_opp.is_liquidity_safe:
        executive_summary = (
            f"INVOICE VERIFIED WITH SAVINGS: Invoice #{req.invoice_number} is valid. "
            f"Recommendation: Pay early by {early_discount_opp.deadline_date} to capture a €{early_discount_opp.savings_amount:,.2f} cash discount."
        )
    elif is_valid:
        executive_summary = (
            f"INVOICE VERIFIED: Invoice #{req.invoice_number} from {req.counterparty_name} passes all compliance checks. "
            f"Amount: €{req.gross_amount:,.2f}, due on {req.due_date}."
        )
    else:
        executive_summary = (
            f"CAUTION: Invoice #{req.invoice_number} has warnings (Risk Score: {risk_score}/100). "
            f"Review flags before scheduling payment."
        )

    # Prepare Action Card Structure (Matching spec/funkcjonalnosci.md swipe cards)
    suggested_action_card: Optional[Dict[str, Any]] = None
    if early_discount_opp and early_discount_opp.is_liquidity_safe and is_valid:
        suggested_action_card = {
            "title": f"Take {req.early_discount_percent}% Early Discount with {req.counterparty_name}?",
            "category": f"{req.counterparty_name} · Accounts Payable",
            "agent_type": AGENT_TYPE_PAYABLES_OPTIMIZER,
            "body": (
                f"Pay invoice #{req.invoice_number} by {early_discount_opp.deadline_date} "
                f"instead of {req.due_date} to save €{early_discount_opp.savings_amount:,.2f}. "
                f"Cash buffer remains healthy at €{(current_cash - early_discount_opp.effective_payable):,.2f}."
            ),
            "swipe_right_action": f"Pay early, take €{early_discount_opp.savings_amount:,.2f} discount",
            "swipe_left_action": f"Pay on due date (€{req.gross_amount:,.2f})",
            "impact_metrics": {
                "cash_protected": float(early_discount_opp.savings_amount),
                "cash_delta": -float(early_discount_opp.effective_payable)
            }
        }
    elif risk_level == RISK_LEVEL_CRITICAL:
        suggested_action_card = {
            "title": f"Hold Payment: Security Warning on #{req.invoice_number}",
            "category": f"{req.counterparty_name} · Fraud Guard",
            "agent_type": AGENT_TYPE_FRAUD_GUARD,
            "body": _first_critical_description(flags),
            "swipe_right_action": "Contact vendor to verify",
            "swipe_left_action": "Reject invoice & mark suspicious",
            "impact_metrics": {
                "prevented_loss": float(req.gross_amount)
            }
        }

    # Optionally persist as an AgentAction in DB if card was generated
    if auto_create_action_card and suggested_action_card:
        db_action = AgentAction(
            title=suggested_action_card["title"],
            agent_type=suggested_action_card["agent_type"],
            trigger_reason=suggested_action_card["body"],
            recommended_action=INVOICE_ACTION_RECOMMENDATION,
            target_amount=req.gross_amount,
            currency=req.currency,
            explanation=executive_summary,
            impact_simulation=suggested_action_card["impact_metrics"],
            status=ACTION_STATUS_PENDING,
            execution_mode=EXECUTION_MODE_SIMULATED,
        )
        db.add(db_action)
        await db.flush()

    return ValidationReport(
        invoice_number=req.invoice_number,
        counterparty_name=req.counterparty_name,
        gross_amount=req.gross_amount,
        currency=req.currency,
        is_valid=is_valid,
        risk_level=risk_level,
        risk_score=risk_score,
        arithmetic_valid=arithmetic_valid,
        duplicate_detected=duplicate_detected,
        iban_status=iban_status,
        price_anomaly_detected=price_anomaly_detected,
        liquidity_safe=liquidity_safe,
        flags=flags,
        early_discount=early_discount_opp,
        executive_summary=executive_summary,
        suggested_action_card=suggested_action_card
    )
