import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.company import CompanyProfile
from app.models.account import BankAccount
from app.models.transaction import Transaction
from app.models.invoice import Invoice
from app.schemas.invoice import (
    InvoiceValidateRequest,
    ValidationReport,
    ValidationFlag,
    EarlyDiscountOpportunity,
)
from app.services.decision_engine import calculate_early_discount


def normalize_iban(iban: Optional[str]) -> str:
    """Strip spaces and uppercase IBAN for reliable comparison."""
    if not iban:
        return ""
    return re.sub(r"\s+", "", iban).upper()


async def validate_invoice_logic(
    db: AsyncSession,
    req: InvoiceValidateRequest,
    auto_create_action_card: bool = False,
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
    arithmetic_valid = diff <= Decimal("0.02") # Allow max 2 cents rounding

    if not arithmetic_valid:
        flags.append(ValidationFlag(
            code="ARITHMETIC_MISMATCH",
            severity="CRITICAL",
            title="Math Calculation Error on Invoice",
            description=(
                f"Net amount ({req.net_amount:,.2f} {req.currency}) + tax ({req.tax_amount:,.2f} {req.currency}) "
                f"equals {expected_gross:,.2f} {req.currency}, which does not match the stated gross payable "
                f"of {req.gross_amount:,.2f} {req.currency}."
            ),
            evidence={"net": float(req.net_amount), "tax": float(req.tax_amount), "stated_gross": float(req.gross_amount)}
        ))
        risk_score += 40
    else:
        # Check if tax rate is reasonable when tax is present
        if req.net_amount > 0 and req.tax_amount > 0:
            effective_rate = (req.tax_amount / req.net_amount) * Decimal("100.00")
            # Common European VAT rates: 19%, 7% (DE), 23%, 8%, 5% (PL)
            standard_rates = [Decimal("7.0"), Decimal("19.0"), Decimal("5.0"), Decimal("8.0"), Decimal("23.0")]
            if not any(abs(effective_rate - r) < Decimal("0.8") for r in standard_rates):
                flags.append(ValidationFlag(
                    code="NON_STANDARD_TAX_RATE",
                    severity="WARNING",
                    title="Non-Standard VAT Rate Detected",
                    description=f"Calculated tax rate is {effective_rate:.1f}%, which deviates from standard rates (19%, 7%, 23%, 8%).",
                    evidence={"effective_tax_rate": float(effective_rate)}
                ))
                risk_score += 15

    if req.gross_amount <= Decimal("0.00"):
        flags.append(ValidationFlag(
            code="INVALID_AMOUNT",
            severity="CRITICAL",
            title="Gross Amount Must Be Positive",
            description=f"Invoice has an invalid non-positive gross amount: {req.gross_amount} {req.currency}.",
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
        func.lower(func.trim(Invoice.counterparty_name)) == req.counterparty_name.strip().lower(),
    ).limit(1)
    existing_inv_result = await db.execute(existing_inv_query)
    existing_invoice = existing_inv_result.scalar_one_or_none()

    # B) Check bank transactions ledger (e.g. "Invoice AS-69664")
    tx_dup_query = select(Transaction).where(
        Transaction.payment_reference.icontains(req.invoice_number.strip(), autoescape=True),
        Transaction.currency == req.currency,
    ).limit(1)
    tx_dup_result = await db.execute(tx_dup_query)
    paid_tx = tx_dup_result.scalar_one_or_none()

    if existing_invoice:
        duplicate_detected = True
        flags.append(ValidationFlag(
            code="DUPLICATE_INVOICE_RECORD",
            severity="CRITICAL",
            title="Duplicate Invoice Detected",
            description=f"Invoice #{req.invoice_number} from '{req.counterparty_name}' has already been registered in the system.",
            evidence={"existing_invoice_id": str(existing_invoice.id), "status": existing_invoice.validation_status}
        ))
        risk_score += 50
    elif paid_tx:
        duplicate_detected = True
        flags.append(ValidationFlag(
            code="INVOICE_ALREADY_PAID",
            severity="CRITICAL",
            title="Invoice Already Paid in Bank Ledger",
            description=(
                f"Invoice #{req.invoice_number} appears to have already been settled on {paid_tx.booking_date} "
                f"via transaction reference '{paid_tx.payment_reference}' ({abs(paid_tx.amount):,.2f} {req.currency})."
            ),
            evidence={"transaction_id": str(paid_tx.id), "booking_date": str(paid_tx.booking_date), "amount": float(paid_tx.amount)}
        ))
        risk_score += 60

    # -------------------------------------------------------------
    # 3. Counterparty IBAN Consistency (Anti-Phishing / Fraud Check)
    # -------------------------------------------------------------
    iban_status = "NEW_COUNTERPARTY"
    # Search only currency-comparable transaction history for this vendor.
    known_tx_query = select(Transaction).where(
        func.lower(func.trim(Transaction.counterparty_name)) == req.counterparty_name.strip().lower(),
        Transaction.currency == req.currency,
    ).order_by(Transaction.booking_date.desc()).limit(100)
    
    known_txs = (await db.execute(known_tx_query)).scalars().all()
    known_ibans = {normalize_iban(t.counterparty_account) for t in known_txs if t.counterparty_account}

    if clean_iban:
        if known_ibans:
            if clean_iban in known_ibans:
                iban_status = "VERIFIED_KNOWN"
                flags.append(ValidationFlag(
                    code="IBAN_VERIFIED",
                    severity="INFO",
                    title="Vendor IBAN Verified",
                    description=f"IBAN matches previously verified payments to {req.counterparty_name}.",
                    evidence={"matched_iban": clean_iban}
                ))
            else:
                iban_status = "MISMATCH_ALERT"
                historical_sample = sorted(known_ibans)[0]
                flags.append(ValidationFlag(
                    code="IBAN_MISMATCH_SUSPECTED_PHISHING",
                    severity="CRITICAL",
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
            iban_status = "NEW_COUNTERPARTY"
            flags.append(ValidationFlag(
                code="NEW_VENDOR_IBAN",
                severity="INFO",
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
        past_amounts = [abs(t.amount) for t in known_txs]
        avg_amount = sum(past_amounts) / Decimal(len(past_amounts))

        # If invoice is more than 35% higher than vendor average
        if avg_amount > 0 and req.gross_amount > avg_amount * Decimal("1.35") and req.gross_amount > Decimal("500.00"):
            price_anomaly_detected = True
            hike_pct = ((req.gross_amount - avg_amount) / avg_amount) * Decimal("100.0")
            flags.append(ValidationFlag(
                code="PRICE_SPIKE_DETECTED",
                severity="WARNING",
                title="Abnormal Spending Spike for Vendor",
                description=(
                    f"Invoice gross amount ({req.gross_amount:,.2f} {req.currency}) is {hike_pct:.1f}% higher "
                    f"than historical average payment ({avg_amount:,.2f} {req.currency}) for '{req.counterparty_name}'."
                ),
                evidence={"average_amount": str(avg_amount), "hike_percent": str(hike_pct), "currency": req.currency}
            ))
            risk_score += 20

    # -------------------------------------------------------------
    # 5. Liquidity Impact & Safety Buffer Check
    # -------------------------------------------------------------
    account_query = select(BankAccount).where(BankAccount.is_primary.is_(True)).order_by(BankAccount.created_at, BankAccount.id).limit(1)
    primary_acc = (await db.execute(account_query)).scalar_one_or_none()
    
    company_query = select(CompanyProfile).limit(1)
    company = (await db.execute(company_query)).scalar_one_or_none()
    
    configured_buffer = (company.settings or {}).get("min_safety_buffer") if company else None
    currency_matches = bool(primary_acc and primary_acc.currency == req.currency)
    current_cash = Decimal(primary_acc.current_balance) if currency_matches else None
    balance_is_current = bool(
        primary_acc and primary_acc.balance_as_of
        and 0 <= (date.today() - primary_acc.balance_as_of).days <= 30
    )
    if not balance_is_current:
        current_cash = None
    min_buffer = Decimal(str(configured_buffer)) if configured_buffer is not None and company and company.base_currency == req.currency else None
    projected_cash_after_payment = current_cash - req.gross_amount if current_cash is not None else None
    liquidity_safe: Optional[bool] = None

    if current_cash is not None and projected_cash_after_payment is not None and projected_cash_after_payment < -Decimal(primary_acc.overdraft_limit):
        liquidity_safe = False
        flags.append(ValidationFlag(
            code="INSOLVENCY_DEFICIT_RISK",
            severity="CRITICAL",
            title="Payment Will Cause Immediate Account Overdraft",
            description=(
                f"Paying {req.gross_amount:,.2f} {req.currency} will reduce the stored account balance from "
                f"{current_cash:,.2f} {req.currency} to {projected_cash_after_payment:,.2f} {req.currency}, "
                f"below the available overdraft limit of {primary_acc.overdraft_limit:,.2f} {req.currency}."
            ),
            evidence={"current_balance": str(current_cash), "projected_balance": str(projected_cash_after_payment), "overdraft_limit": str(primary_acc.overdraft_limit)}
        ))
        risk_score += 45
    elif min_buffer is not None and projected_cash_after_payment is not None and projected_cash_after_payment < min_buffer:
        liquidity_safe = False
        flags.append(ValidationFlag(
            code="SAFETY_BUFFER_BREACH",
            severity="WARNING",
            title="Payment Violates Cash Safety Buffer",
            description=(
                f"Paying {req.gross_amount:,.2f} {req.currency} leaves {projected_cash_after_payment:,.2f} "
                f"{req.currency}, below the configured safety threshold of {min_buffer:,.2f} {req.currency}."
            ),
            evidence={"min_buffer": str(min_buffer), "projected_balance": str(projected_cash_after_payment)}
        ))
        risk_score += 15
    elif min_buffer is not None and projected_cash_after_payment is not None:
        liquidity_safe = True
    elif not primary_acc:
        flags.append(ValidationFlag(
            code="NO_ACCOUNT_DATA",
            severity="INFO",
            title="Liquidity Not Checked",
            description="No primary bank account is stored, so the payment's effect on company liquidity cannot be calculated.",
            evidence={},
        ))
    elif not currency_matches:
        flags.append(ValidationFlag(
            code="ACCOUNT_CURRENCY_MISMATCH",
            severity="INFO",
            title="Liquidity Not Checked",
            description=f"The primary account is denominated in {primary_acc.currency}; this invoice is in {req.currency}. No exchange rate was applied.",
            evidence={"account_currency": primary_acc.currency, "invoice_currency": req.currency},
        ))
    elif not balance_is_current:
        flags.append(ValidationFlag(
            code="STALE_ACCOUNT_BALANCE",
            severity="INFO",
            title="Liquidity Not Checked",
            description="The primary account balance is missing or older than 30 days; update the balance snapshot before using liquidity checks.",
            evidence={"balance_as_of": primary_acc.balance_as_of.isoformat() if primary_acc.balance_as_of else None},
        ))

    # -------------------------------------------------------------
    # 6. Early Payment Discount (Skonto) Opportunity Check
    # -------------------------------------------------------------
    early_discount_opp: Optional[EarlyDiscountOpportunity] = None
    if req.early_discount_percent and req.early_discount_percent > Decimal("0.00") and req.early_discount_days:
        deadline = req.issue_date + timedelta(days=req.early_discount_days)
        savings, discounted_payable = calculate_early_discount(req.gross_amount, req.early_discount_percent)
        
        # Check if paying discounted amount early is liquidity safe
        discounted_projected = current_cash - discounted_payable if current_cash is not None else None
        is_safe = discounted_projected >= min_buffer if discounted_projected is not None and min_buffer is not None else None

        reasoning = (
            f"Vendor offers a {req.early_discount_percent}% early payment discount if paid by {deadline} "
            f"({req.early_discount_days} days), saving {savings:,.2f} {req.currency}. "
            + (
                f"The stored balance would be {discounted_projected:,.2f} {req.currency}, above the configured "
                f"safety buffer of {min_buffer:,.2f} {req.currency}."
                if is_safe is True else
                f"The stored balance would be {discounted_projected:,.2f} {req.currency}, below the configured "
                f"safety buffer of {min_buffer:,.2f} {req.currency}."
                if is_safe is False else
                " Liquidity safety cannot be determined from the available account and buffer data."
            )
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
            severity="INFO",
            title=f"Early Payment Discount Available: Save {savings:,.2f} {req.currency}",
            description=reasoning,
            evidence={"savings": str(savings), "deadline": str(deadline), "discount_percent": str(req.early_discount_percent)},
        ))

    # -------------------------------------------------------------
    # Synthesize Final Verdict & Suggested Swipe Action Card
    # -------------------------------------------------------------
    risk_score = min(max(risk_score, 0), 100)
    
    if risk_score >= 60:
        risk_level = "CRITICAL"
    elif risk_score >= 35:
        risk_level = "HIGH"
    elif risk_score >= 15:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    is_valid = risk_level in ("LOW", "MEDIUM")

    # Generate Plain-Language Executive Summary for the LLM
    if risk_level == "CRITICAL":
        executive_summary = (
            f"BLOCK PAYMENT: Critical risk detected on invoice #{req.invoice_number} from {req.counterparty_name} "
            f"(Risk Score: {risk_score}/100). Flags: {', '.join(f.title for f in flags if f.severity == 'CRITICAL')}."
        )
    elif early_discount_opp and early_discount_opp.is_liquidity_safe is True:
        executive_summary = (
            f"INVOICE VERIFIED WITH SAVINGS: Invoice #{req.invoice_number} is valid. "
            f"Recommendation: Pay early by {early_discount_opp.deadline_date} to capture a {early_discount_opp.savings_amount:,.2f} {req.currency} cash discount."
        )
    elif is_valid:
        executive_summary = (
            f"INVOICE VERIFIED: Invoice #{req.invoice_number} from {req.counterparty_name} passes all compliance checks. "
            f"Amount: {req.gross_amount:,.2f} {req.currency}, due on {req.due_date}."
        )
    else:
        executive_summary = (
            f"CAUTION: Invoice #{req.invoice_number} has warnings (Risk Score: {risk_score}/100). "
            f"Review flags before scheduling payment."
        )

    # Prepare Action Card Structure (Matching spec/funkcjonalnosci.md swipe cards)
    suggested_action_card: Optional[Dict[str, Any]] = None
    if early_discount_opp and early_discount_opp.is_liquidity_safe is True and is_valid:
        suggested_action_card = {
            "title": f"Take {req.early_discount_percent}% Early Discount with {req.counterparty_name}?",
            "category": f"{req.counterparty_name} · Accounts Payable",
            "agent_type": "payables_optimizer",
            "body": (
                f"Pay invoice #{req.invoice_number} by {early_discount_opp.deadline_date} "
                f"instead of {req.due_date} to save {early_discount_opp.savings_amount:,.2f} {req.currency}. "
                f"Projected cash after payment is {discounted_projected:,.2f} {req.currency}, above the configured buffer."
            ),
            "swipe_right_action": f"Pay early, take {early_discount_opp.savings_amount:,.2f} {req.currency} discount",
            "swipe_left_action": f"Pay on due date ({req.gross_amount:,.2f} {req.currency})",
            "impact_metrics": {
                "cash_protected": float(early_discount_opp.savings_amount),
                "cash_delta": -float(early_discount_opp.effective_payable)
            }
        }
    elif risk_level == "CRITICAL":
        critical_flag = next((flag for flag in flags if flag.severity == "CRITICAL"), None)
        suggested_action_card = {
            "title": f"Hold Payment: Security Warning on #{req.invoice_number}",
            "category": f"{req.counterparty_name} · Fraud Guard",
            "agent_type": "fraud_guard",
            "body": critical_flag.description if critical_flag else executive_summary,
            "swipe_right_action": "Contact vendor to verify",
            "swipe_left_action": "Reject invoice & mark suspicious",
            "impact_metrics": {
                "prevented_loss": float(req.gross_amount)
            }
        }

    # Validation returns a preview only; persisted recommendations must link to a stored invoice.
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
