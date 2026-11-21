import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.const.invoice import SEVERITY_CRITICAL, STANDARD_VAT_RATES
from app.schemas.invoice import InvoiceValidateRequest, ValidationFlag
from app.services.forecast_engine import ForecastInputs
from app.services.invoice_validator import (
    CashPosition,
    _Findings,
    _action_card,
    _check_early_discount,
    _check_liquidity,
    _usable_position,
    _vat_rates_text,
    is_payable,
    payment_impact,
    reference_mentions_number,
)
from tests.conftest import API_PREFIX

AS_OF = date(2025, 12, 31)
VALIDATE_URL = f"{API_PREFIX}/invoices/validate"
UPLOAD_URL = f"{API_PREFIX}/statements/upload/csv"
HEADER = '"Account Number";"Booking Date";"Value Date";"Transaction Type";"Payment Reference";' \
         '"Beneficiary/Payer";"Counterparty Account";"Bank Code";"Amount";"Currency";"Info"'


def position(opening="10000.00", buffer="5000.00", overdraft="0", currency="EUR") -> CashPosition:
    inputs = ForecastInputs(as_of=AS_OF, opening_balance=Decimal(opening), safety_buffer=Decimal(buffer), horizon_days=30)
    return CashPosition(inputs=inputs, currency=currency, overdraft_limit=Decimal(overdraft))


def request(**overrides) -> InvoiceValidateRequest:
    values = dict(
        invoice_number="INV-1",
        issue_date=AS_OF,
        due_date=AS_OF + timedelta(days=10),
        counterparty_name="Supplier GmbH",
        net_amount=Decimal("100.00"),
        tax_amount=Decimal("19.00"),
        gross_amount=Decimal("119.00"),
    )
    values.update(overrides)
    return InvoiceValidateRequest(**values)


def codes(findings: _Findings):
    return [flag.code for flag in findings.flags]


def test_invoice_number_must_be_a_whole_token_in_the_reference():
    assert reference_mentions_number("Invoice 12 March", "12")
    assert reference_mentions_number("inv/AS-69664", "AS-69664")
    assert not reference_mentions_number("Invoice 1234", "12")
    assert not reference_mentions_number(None, "12")


def test_sales_invoices_and_credit_notes_are_not_payables():
    assert is_payable("incoming_expense")
    assert is_payable("receipt")
    assert not is_payable("outgoing_revenue")
    assert not is_payable("credit_note")


def test_payment_impact_uses_the_forecast_on_the_due_date():
    impact = payment_impact(position(), Decimal("6000.00"), AS_OF + timedelta(days=10), "test")

    assert impact.lowest_before == Decimal("10000.00")
    assert impact.lowest_after == Decimal("4000.00")
    assert impact.lowest_date == AS_OF + timedelta(days=10)


def test_payment_impact_extends_horizon_and_gives_up_beyond_the_maximum():
    assert payment_impact(position(), Decimal("1.00"), AS_OF + timedelta(days=80), "test") is not None
    assert payment_impact(position(), Decimal("1.00"), AS_OF + timedelta(days=200), "test") is None


def test_liquidity_buffer_breach_is_a_warning():
    findings = _Findings()

    assert _check_liquidity(request(gross_amount=Decimal("6000.00"), net_amount=Decimal("6000.00"), tax_amount=Decimal("0")), position(), findings)
    assert codes(findings) == ["SAFETY_BUFFER_BREACH"]


def test_overdraft_limit_decides_between_warning_and_critical():
    big = dict(gross_amount=Decimal("12000.00"), net_amount=Decimal("12000.00"), tax_amount=Decimal("0"))

    within = _Findings()
    assert _check_liquidity(request(**big), position(overdraft="5000"), within) is False
    assert codes(within) == ["OVERDRAFT_USED"]

    beyond = _Findings()
    assert _check_liquidity(request(**big), position(overdraft="1000"), beyond) is False
    assert codes(beyond) == ["INSOLVENCY_DEFICIT_RISK"]


def test_payment_after_due_inflow_is_safe():
    findings = _Findings()

    assert _check_liquidity(request(), position(), findings) is True
    assert findings.flags == []


def test_invoice_in_other_currency_is_not_compared_with_the_balance():
    findings = _Findings()

    assert _usable_position(request(currency="PLN"), position(currency="EUR"), findings) is None
    assert codes(findings) == ["CURRENCY_NOT_CONVERTED"]


def test_expired_early_discount_is_not_recommended():
    findings = _Findings()
    expired = request(issue_date=AS_OF - timedelta(days=20), early_discount_percent=Decimal("2"), early_discount_days=10)

    discount, impact = _check_early_discount(expired, position(), findings)

    assert discount is None and impact is None
    assert codes(findings) == ["EARLY_DISCOUNT_EXPIRED"]


def test_valid_early_discount_is_checked_against_the_forecast():
    findings = _Findings()
    offer = request(early_discount_percent=Decimal("2"), early_discount_days=10)

    discount, impact = _check_early_discount(offer, position(), findings)

    assert discount.is_liquidity_safe is True
    assert discount.savings_amount == Decimal("2.38")
    assert impact.lowest_after == Decimal("10000.00") - discount.effective_payable


def test_critical_flag_creates_a_card_even_when_the_score_is_only_high():
    findings = _Findings()
    findings.add(ValidationFlag(code="X", severity=SEVERITY_CRITICAL, title="t", description="critical text"), 40)

    card = _action_card(request(), findings, is_valid=False, discount=None, discount_impact=None)

    assert card is not None and card["body"] == "critical text"


def test_vat_message_lists_the_configured_rates():
    text = _vat_rates_text()

    assert all(f"{rate.normalize()}%" in text for rate in STANDARD_VAT_RATES)


def _upload(client, auth_headers, rows):
    account_number = f"DE{uuid.uuid4().int % 10**20:020d}"
    lines = [
        f'"{account_number}";"01.03.25";"01.03.25";"Transfer";"{reference}";"{name}";"{iban}";"";"{amount}";"EUR";""'
        for reference, name, iban, amount in rows
    ]
    response = client.post(UPLOAD_URL, headers=auth_headers, files={"file": ("s.csv", "\n".join([HEADER, *lines]).encode(), "text/csv")})
    assert response.status_code == 200, response.text


def _validate(client, auth_headers, card=False, **fields):
    payload = {
        "invoice_number": f"N-{uuid.uuid4().hex[:6]}",
        "issue_date": "2025-03-01",
        "due_date": "2025-03-15",
        "counterparty_name": "Nobody",
        "net_amount": "100.00",
        "tax_amount": "19.00",
        "gross_amount": "119.00",
    }
    payload.update(fields)
    response = client.post(f"{VALIDATE_URL}?auto_create_card={'true' if card else 'false'}", headers=auth_headers, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _flag_codes(report):
    return {flag["code"] for flag in report["flags"]}


def test_already_paid_needs_same_counterparty_and_whole_number(client, auth_headers):
    vendor = f"Paid Vendor {uuid.uuid4().hex[:8]}"
    _upload(client, auth_headers, [("Invoice 1234", vendor, "", "-119,00")])

    assert "INVOICE_ALREADY_PAID" not in _flag_codes(_validate(client, auth_headers, invoice_number="12", counterparty_name=vendor))
    assert "INVOICE_ALREADY_PAID" not in _flag_codes(_validate(client, auth_headers, invoice_number="1234", counterparty_name="Someone Else"))
    assert "INVOICE_ALREADY_PAID" in _flag_codes(_validate(client, auth_headers, invoice_number="1234", counterparty_name=vendor))


def test_vendor_name_fragment_is_not_the_same_vendor(client, auth_headers):
    tag = uuid.uuid4().hex[:8]
    _upload(client, auth_headers, [("", f"{tag} Metropolitan", "DE89370400440532013000", "-50,00")])

    report = _validate(client, auth_headers, counterparty_name=f"{tag} Metro", counterparty_iban="DE02120300000000202051")

    assert report["iban_status"] == "NEW_COUNTERPARTY"
    assert "IBAN_MISMATCH_SUSPECTED_PHISHING" not in _flag_codes(report)


def test_price_spike_ignores_money_received_from_the_vendor(client, auth_headers):
    vendor = f"Spike Vendor {uuid.uuid4().hex[:8]}"
    _upload(client, auth_headers, [
        ("a", vendor, "", "-100,00"),
        ("b", vendor, "", "-100,00"),
        ("refund", vendor, "", "5000,00"),
    ])

    report = _validate(client, auth_headers, counterparty_name=vendor, net_amount="1000.00", tax_amount="0", gross_amount="1000.00")

    assert report["price_anomaly_detected"] is True


def test_sales_invoice_is_never_an_overdraft(client, auth_headers):
    report = _validate(
        client, auth_headers,
        invoice_type="outgoing_revenue",
        net_amount="900000000.00", tax_amount="0", gross_amount="900000000.00",
    )

    assert report["liquidity_safe"] is True
    assert not {"INSOLVENCY_DEFICIT_RISK", "OVERDRAFT_USED", "SAFETY_BUFFER_BREACH"} & _flag_codes(report)


def test_repeated_validation_creates_one_card(client, auth_headers):
    number = f"DUP-{uuid.uuid4().hex[:6]}"
    broken = dict(invoice_number=number, gross_amount="500.00")

    _validate(client, auth_headers, card=True, **broken)
    _validate(client, auth_headers, card=True, **broken)

    actions = client.get(f"{API_PREFIX}/actions", headers=auth_headers).json()
    assert sum(1 for action in actions if number in action["title"]) == 1
