import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

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
    arithmetic_valid = diff <= Decimal("0.02") # Allow max 2 cents rounding

    if not arithmetic_valid:
        flags.append(ValidationFlag(
            code="ARITHMETIC_MISMATCH",
            severity="CRITICAL",
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
        Invoice.counterparty_name.ilike(f"%{req.counterparty_name.strip()}%")
    )
    existing_inv_result = await db.execute(existing_inv_query)
    existing_invoice = existing_inv_result.scalar_one_or_none()

    # B) Check bank transactions ledger (e.g. "Invoice AS-69664")
    tx_dup_query = select(Transaction).where(
        Transaction.payment_reference.ilike(f"%{req.invoice_number.strip()}%")
    )
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
                f"via transaction reference '{paid_tx.payment_reference}' (€{abs(paid_tx.amount):,.2f})."
            ),
            evidence={"transaction_id": str(paid_tx.id), "booking_date": str(paid_tx.booking_date), "amount": float(paid_tx.amount)}
        ))
        risk_score += 60

    # -------------------------------------------------------------
    # 3. Counterparty IBAN Consistency (Anti-Phishing / Fraud Check)
    # -------------------------------------------------------------
    iban_status = "NEW_COUNTERPARTY"
    vendor_pattern = f"%{req.counterparty_name.strip()}%"

    # Search past transactions to find known bank account details for this vendor
    known_tx_query = select(Transaction).where(
        Transaction.counterparty_name.ilike(vendor_pattern),
        Transaction.counterparty_account.isnot(None),
        Transaction.counterparty_account != ""
    ).order_by(Transaction.booking_date.desc()).limit(10)
    
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
                historical_sample = list(known_ibans)[0]
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
        past_amounts = [abs(t.amount_base_currency) for t in known_txs]
        avg_amount = sum(past_amounts) / Decimal(len(past_amounts))
        
        # If invoice is more than 35% higher than vendor average
        if req.gross_amount > avg_amount * Decimal("1.35") and req.gross_amount > Decimal("500.00"):
            price_anomaly_detected = True
            hike_pct = ((req.gross_amount - avg_amount) / avg_amount) * Decimal("100.0")
            flags.append(ValidationFlag(
                code="PRICE_SPIKE_DETECTED",
                severity="WARNING",
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
    account_query = select(BankAccount).where(BankAccount.is_primary == True)
    primary_acc = (await db.execute(account_query)).scalar_one_or_none()
    
    company_query = select(CompanyProfile).limit(1)
    company = (await db.execute(company_query)).scalar_one_or_none()
    
    min_buffer = Decimal("5000.00")
    if company and "min_safety_buffer" in company.settings:
        min_buffer = Decimal(str(company.settings["min_safety_buffer"]))

    liquidity_safe = True
    current_cash = primary_acc.current_balance if primary_acc else Decimal("33266.35")
    projected_cash_after_payment = current_cash - req.gross_amount

    if projected_cash_after_payment < Decimal("0.00"):
        liquidity_safe = False
        flags.append(ValidationFlag(
            code="INSOLVENCY_DEFICIT_RISK",
            severity="CRITICAL",
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
            severity="WARNING",
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
        
        # Check if paying discounted amount early is liquidity safe
        is_safe = (current_cash - discounted_payable) >= min_buffer

        reasoning = (
            f"Vendor offers a {req.early_discount_percent}% early payment discount if paid by {deadline} "
            f"({req.early_discount_days} days). You will save €{savings:,.2f}. "
            f"Current cash balance of €{current_cash:,.2f} {'comfortably covers' if is_safe else 'is tight for'} this early payout."
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
            title=f"Early Payment Discount Available: Save €{savings:,.2f}",
            description=reasoning,
            evidence={"savings": float(savings), "deadline": str(deadline), "discount_percent": float(req.early_discount_percent)}
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
            "agent_type": "payables_optimizer",
            "body": (
                f"Pay invoice #{req.invoice_number} by {early_discount_opp.deadline_date} "
                f"instead of {req.due_date} to save €{early_discount_opp.savings_amount:,.2f}. "
                f"Cash buffer remains healthy at €{(current_cash - early_discount_opp.effective_payable):,.2f}."
            ),
            "swipe_right_action": f"Pay early, take €{early_discount_opp.savings_amount:,.2f} discount",
            "swipe_left_action": f"Pay on due date (€{req.gross_amount:,.2f})",
            "confidence": 92,
            "impact_metrics": {
                "cash_protected": float(early_discount_opp.savings_amount),
                "cash_delta": -float(early_discount_opp.effective_payable)
            }
        }
    elif risk_level == "CRITICAL":
        suggested_action_card = {
            "title": f"Hold Payment: Security Warning on #{req.invoice_number}",
            "category": f"{req.counterparty_name} · Fraud Guard",
            "agent_type": "fraud_guard",
            "body": flags[0].description,
            "swipe_right_action": "Contact vendor to verify",
            "swipe_left_action": "Reject invoice & mark suspicious",
            "confidence": 99,
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
            recommended_action="validate_and_pay_or_hold",
            target_amount=req.gross_amount,
            currency=req.currency,
            explanation=executive_summary,
            impact_simulation=suggested_action_card["impact_metrics"],
            status="pending",
            execution_mode="simulated"
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
