from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.const.demo import DEMO_PROFILE_FILES, DEMO_PROFILES
from app.services.seed import _profile_csv_path
from app.services.statement_parser import parse_bank_statement_csv


def test_default_demo_profiles_have_packaged_statements():
    for profile_name in DEMO_PROFILES:
        assert Path(_profile_csv_path(profile_name)).is_file()
        assert DEMO_PROFILE_FILES[profile_name] in _profile_csv_path(profile_name)


def test_northstar_demo_statement_matches_seed_profile():
    path = Path(_profile_csv_path("northstar"))
    parsed = parse_bank_statement_csv(path.read_text(encoding="utf-8"))

    assert len(parsed) == 1125
    assert min(tx["booking_date"] for tx in parsed) == date(2025, 1, 1)
    assert max(tx["booking_date"] for tx in parsed) == date(2025, 12, 31)
    assert {tx["account_number"] for tx in parsed} == {"DE00000000000000000000"}
    assert sum((tx["amount_base_currency"] for tx in parsed), Decimal("0.00")) == DEMO_PROFILES["northstar"]["balance"]

    categories = Counter(tx["category"] for tx in parsed)
    assert categories["revenue_b2b"] == 208
    assert categories["vehicle_fuel"] == 300
    assert categories["vehicle_tolls"] == 250
    assert categories["vehicle_maintenance"] == 45
    assert categories["payroll"] == 48
    assert categories["rent"] == 12
