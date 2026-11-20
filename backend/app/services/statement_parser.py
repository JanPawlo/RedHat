import csv
import re
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Tuple, Optional
import io


def parse_german_decimal(val: str) -> Decimal:
    """Parse string numbers with German format (e.g. '-3200,00' or '1.149,36') to Decimal."""
    cleaned = val.strip().replace('"', '').replace("'", "")
    if not cleaned:
        return Decimal("0.00")
    # Remove thousands separators if present
    if "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "")
    cleaned = cleaned.replace(",", ".")
    return Decimal(cleaned)


def parse_flexible_date(val: str) -> date:
    """Parse various bank date formats (DD.MM.YY, DD.MM.YYYY, YYYY-MM-DD)."""
    cleaned = val.strip().replace('"', '')
    for fmt in ("%d.%m.%y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {val}")


def auto_categorize(tx_type: str, counterparty: str, reference: str) -> str:
    """Derive financial category based on transaction markers."""
    text = f"{tx_type} {counterparty} {reference}".lower()

    if "salary" in text or "gehalt" in text or "lohn" in text:
        return "payroll"
    elif "tax" in text or "finanzamt" in text or "steuer" in text:
        return "tax"
    elif "rent" in text or "miete" in text or "immobilien" in text:
        return "rent"
    elif "kredit" in text or "loan" in text or "darlehen" in text:
        return "financing"
    elif "international wire" in text or "chf" in text or "ristorante zurich" in text:
        return "fx_transfer"
    elif "card settlement" in text or "credit card payout" in text or "revenue" in text:
        return "revenue_pos"
    elif "supplier" in text or "wholesale" in text or "asimex" in text or "vino" in text:
        return "supplier"
    elif "utility" in text or "stadtwerke" in text or "strom" in text or "energy" in text:
        return "utility"
    elif "krankenkasse" in text or "social security" in text:
        return "social_security"
    return "other"


def extract_fx_rate(reference: str) -> Optional[Decimal]:
    """Extract exchange rate if present in reference (e.g. '@ 1.047 EUR/CHF')."""
    match = re.search(r"@\s*([0-9]+[.,][0-9]+)\s*EUR/CHF", reference, re.IGNORECASE)
    if match:
        rate_str = match.group(1).replace(",", ".")
        return Decimal(rate_str)
    return None


def parse_bank_statement_csv(
    file_content: str,
    delimiter: str = ";"
) -> List[Dict[str, Any]]:
    """
    Parses a bank statement CSV into normalized transaction dictionaries.
    Any extra or unmapped columns are preserved inside `metadata_payload`.
    """
    reader = csv.DictReader(io.StringIO(file_content), delimiter=delimiter)
    transactions = []

    for row in reader:
        # Strip whitespace and quotes from keys and values
        clean_row = {
            k.strip().replace('"', ''): (v.strip().replace('"', '') if v else "")
            for k, v in row.items() if k
        }

        account_number = clean_row.get("Account Number", "")
        booking_date_str = clean_row.get("Booking Date", "")
        value_date_str = clean_row.get("Value Date", "")
        tx_type = clean_row.get("Transaction Type", "")
        reference = clean_row.get("Payment Reference", "")
        counterparty = clean_row.get("Beneficiary/Payer", "")
        cp_account = clean_row.get("Counterparty Account", "")
        bank_code = clean_row.get("Bank Code", "")
        amount_str = clean_row.get("Amount", "0,00")
        currency = clean_row.get("Currency", "EUR")
        info = clean_row.get("Info", "")

        booking_date = parse_flexible_date(booking_date_str)
        value_date = parse_flexible_date(value_date_str) if value_date_str else booking_date
        amount = parse_german_decimal(amount_str)

        # Base currency calculation (handles foreign currencies like CHF)
        if currency.upper() == "CHF":
            rate = extract_fx_rate(reference) or Decimal("1.04")
            # Negative amount in CHF multiplied by EUR/CHF rate gives EUR outflow
            amount_base = (amount * rate).quantize(Decimal("0.01"))
        else:
            amount_base = amount

        category = auto_categorize(tx_type, counterparty, reference)

        # Retain original row in metadata for full fidelity and auditability
        metadata = {k: v for k, v in clean_row.items()}

        transactions.append({
            "account_number": account_number,
            "booking_date": booking_date,
            "value_date": value_date,
            "amount": amount,
            "currency": currency,
            "amount_base_currency": amount_base,
            "transaction_type": tx_type,
            "category": category,
            "counterparty_name": counterparty,
            "counterparty_account": cp_account,
            "counterparty_bank_code": bank_code,
            "payment_reference": reference,
            "info": info,
            "is_recurring": category in ("payroll", "rent", "social_security", "tax", "fx_transfer"),
            "metadata_payload": metadata,
        })

    return transactions
