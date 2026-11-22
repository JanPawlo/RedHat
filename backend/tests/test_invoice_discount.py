from datetime import date
from types import SimpleNamespace

from app.services.invoice_validator import discount_reference_day


def test_discount_is_judged_on_the_latest_bank_data_day():
    context = SimpleNamespace(inputs=SimpleNamespace(as_of=date(2025, 12, 31)))

    assert discount_reference_day(context) == date(2025, 12, 31)


def test_discount_falls_back_to_today_without_bank_data():
    assert discount_reference_day(None) == date.today()
