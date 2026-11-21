"""
Seeded generator of larger bank statements for the target-group companies (memory/examples/firmy/target-group-profiles.md).

The output uses the same CSV layout as the organizers' sample statement, so it goes through the real parser
(`app.services.statement_parser`) and the real forecast engine. Each profile has 2+ years of history with
weekday rhythm, monthly seasonality, public holidays and company closures, late-paying clients, supplier
price drift and one-off shocks. `backtest` trains the engine on the history before a split date and
measures how far the forecast balance is from the generated "real" balance afterwards.

Usage (inside the backend container, from /app or backend/):
    python scripts/generate_test_data.py --profile pizzeria --years 2 --seed 7 --out /tmp/pizzeria.csv
    python scripts/generate_test_data.py --all --out-dir /tmp/generated --backtest
"""

import argparse
import os
import random
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.const.calendar import EVENT_KIND_HOLIDAY  # noqa: E402
from app.services.calendar_events import calendar_occurrences  # noqa: E402
from app.services.forecast_engine import CashRecord, ForecastInputs, build_forecast  # noqa: E402
from app.services.statement_parser import parse_bank_statement_csv  # noqa: E402

HEADER = (
    '"Account Number";"Booking Date";"Value Date";"Transaction Type";"Payment Reference";'
    '"Beneficiary/Payer";"Counterparty Account";"Bank Code";"Amount";"Currency";"Info"'
)
DEFAULT_END = date(2025, 12, 31)
DEFAULT_YEARS = 2
DEFAULT_SEED = 42
BACKTEST_HORIZON_DAYS = 60
CENT = Decimal("0.01")
ZERO = Decimal("0")


@dataclass(frozen=True)
class Client:
    name: str
    monthly_amount: int
    typical_delay_days: int
    prefix: str


@dataclass(frozen=True)
class Fixed:
    counterparty: str
    reference: str
    amount: int
    day: int
    every_months: int = 1


@dataclass(frozen=True)
class Supplier:
    counterparty: str
    reference: str
    amount: int
    weekdays: Tuple[int, ...]
    yearly_drift: float


@dataclass(frozen=True)
class Shock:
    day_offset: int
    counterparty: str
    reference: str
    amount: int


@dataclass(frozen=True)
class Profile:
    name: str
    country: str
    currency: str
    account: str
    opening_balance: int
    weekday_revenue: Tuple[int, ...] = (0, 0, 0, 0, 0, 0, 0)
    revenue_noise: float = 0.15
    month_factors: Dict[int, float] = field(default_factory=dict)
    holiday_sensitivity: float = 1.0
    closures: Tuple[Tuple[str, str], ...] = ()
    clients: Tuple[Client, ...] = ()
    salaries: Tuple[Tuple[str, int], ...] = ()
    payday: int = 28
    fixed: Tuple[Fixed, ...] = ()
    suppliers: Tuple[Supplier, ...] = ()
    shocks: Tuple[Shock, ...] = ()


PROFILES: Dict[str, Profile] = {
    "pizzeria": Profile(
        name="Pizzeria Napoli", country="DE", currency="EUR", account="DE10500105170000000001", opening_balance=18000,
        weekday_revenue=(900, 950, 1050, 1250, 1900, 2500, 1700),
        month_factors={1: 0.85, 2: 0.9, 3: 0.95, 7: 1.15, 8: 1.2, 11: 1.05, 12: 1.15},
        closures=(("06-02", "06-22"),),
        salaries=(("Salary Marco Rossi", 2600), ("Salary Anna Weber", 2200), ("Salary Luca Bianchi", 2000), ("Salary Eva Klein", 1500)),
        fixed=(
            Fixed("Main Street Immobilien GmbH", "Rent restaurant", 3800, 1),
            Fixed("Stadtwerke Frankfurt", "Energy bill electricity and gas", 650, 15),
            Fixed("AOK Krankenkasse", "Social security contributions", 2400, 15),
            Fixed("Tax Office Frankfurt", "Tax prepayment VAT", 1300, 10),
            Fixed("Tax Office Frankfurt", "Tax prepayment income", 2100, 10, every_months=3),
        ),
        suppliers=(
            Supplier("Asimex Wholesale Ltd", "Wholesale food order", 720, (0, 3), 0.08),
            Supplier("Central Wholesale Market", "Wholesale produce purchase", 270, (0, 1, 2, 3, 4, 5), 0.05),
            Supplier("Fattoria La Vino GmbH", "Wine supplier order", 640, (2,), 0.04),
        ),
        shocks=(Shock(430, "Ofenbau Service GmbH", "Oven repair", -4200), Shock(610, "Insurance refund AG", "Water damage refund", 2500)),
    ),
    "software_house": Profile(
        name="Kodmistrz Sp. z o.o.", country="PL", currency="PLN", account="PL61109010140000071219812874", opening_balance=180000,
        clients=(
            Client("Nordic Retail AB", 52000, 21, "NR"),
            Client("Bank Polski SA", 38000, 4, "BP"),
            Client("Startup Labs Sp. z o.o.", 16000, 35, "SL"),
        ),
        salaries=tuple((f"Salary developer {index:02d}", 11000 + 400 * (index % 5)) for index in range(1, 13)),
        payday=10,
        fixed=(
            Fixed("Biurowiec Centrum Sp. z o.o.", "Rent office", 18000, 1),
            Fixed("Amazon Web Services EMEA", "Cloud subscription supplier invoice", 4200, 3),
            Fixed("ZUS", "Social security contributions", 26000, 15),
            Fixed("Urzad Skarbowy", "Tax VAT", 21000, 25),
        ),
        suppliers=(Supplier("SaaS Tools Wholesale", "Supplier licences", 900, (1,), 0.10),),
        shocks=(Shock(300, "Komputronik SA", "Supplier laptops for new hires", -48000),),
    ),
    "transport": Profile(
        name="TransBalt Sp. j.", country="PL", currency="PLN", account="PL27114020040000300201355387", opening_balance=95000,
        clients=(
            Client("Spedycja Europa Sp. z o.o.", 120000, 52, "SE"),
            Client("Logistik Hamburg GmbH", 85000, 60, "LH"),
            Client("Hurtownia Mazowsze", 30000, 14, "HM"),
        ),
        salaries=tuple((f"Salary driver {index:02d}", 7200 + 300 * (index % 4)) for index in range(1, 11)),
        payday=10,
        fixed=(
            Fixed("Leasing Pojazdy SA", "Leasing trucks", 38000, 5),
            Fixed("Plac Manewrowy Sp. z o.o.", "Rent yard", 9000, 1),
            Fixed("ZUS", "Social security contributions", 19000, 15),
            Fixed("Urzad Skarbowy", "Tax VAT", 24000, 25),
        ),
        suppliers=(
            Supplier("Orlen Fuel Wholesale", "Supplier fuel cards", 6800, (0, 2, 4), 0.06),
            Supplier("e-TOLL Wholesale", "Supplier highway tolls", 2100, (1, 3), 0.03),
        ),
        shocks=(Shock(250, "Serwis Ciezarowek", "Engine repair truck 4", -32000), Shock(480, "Insurance refund SA", "Accident refund", 18000)),
    ),
    "beauty_salon": Profile(
        name="Salon Urody Bella", country="PL", currency="PLN", account="PL83102055581111123456789012", opening_balance=22000,
        weekday_revenue=(600, 1100, 1300, 1400, 1900, 2300, 0),
        month_factors={1: 0.8, 2: 0.85, 5: 1.1, 6: 1.2, 8: 0.85, 12: 1.3},
        holiday_sensitivity=2.5,
        salaries=(("Salary stylist Ola", 5200), ("Salary cosmetologist Kasia", 5600)),
        payday=10,
        fixed=(
            Fixed("Galeria Rynek Sp. z o.o.", "Rent salon", 6500, 1),
            Fixed("Leasing Medyczny SA", "Leasing laser device", 2900, 5),
            Fixed("ZUS", "Social security contributions", 4100, 15),
            Fixed("Urzad Skarbowy", "Tax PIT", 2600, 20),
            Fixed("Tauron Energy", "Energy bill", 700, 18),
        ),
        suppliers=(Supplier("Kosmetyki Wholesale", "Supplier cosmetics order", 1800, (1,), 0.09),),
        shocks=(Shock(380, "Laser Serwis", "Laser head replacement", -9500),),
    ),
    "developer": Profile(
        name="Budomex Development SA", country="PL", currency="PLN", account="PL02124055421111000049470036", opening_balance=6500000,
        clients=(
            Client("Apartment buyers escrow tranche", 2400000, 10, "ESC"),
            Client("Commercial unit buyers", 600000, 30, "COM"),
        ),
        salaries=(("Salary batch office staff", 520000), ("Salary batch construction site", 780000)),
        payday=10,
        fixed=(
            Fixed("Biurowiec Development", "Rent office", 60000, 1),
            Fixed("ZUS", "Social security contributions", 410000, 15),
            Fixed("Urzad Skarbowy", "Tax VAT", 350000, 25),
            Fixed("Bank Budowlany SA", "Loan instalment kredyt", 900000, 20, every_months=3),
        ),
        suppliers=(
            Supplier("Beton Wholesale SA", "Supplier concrete delivery", 95000, (0, 2, 4), 0.07),
            Supplier("Stal Wholesale Sp. z o.o.", "Supplier steel rebar", 120000, (1,), 0.10),
        ),
        shocks=(Shock(200, "Gmina Miasto", "Land plot purchase", -8000000), Shock(210, "Bank Budowlany SA", "Construction loan tranche kredyt", 5000000)),
    ),
}


@dataclass
class _Row:
    day: date
    tx_type: str
    reference: str
    counterparty: str
    amount: Decimal


def _money(rng: random.Random, base: float, noise: float) -> Decimal:
    return Decimal(str(round(base * (1 + rng.uniform(-noise, noise)), 2))).quantize(CENT)


def _days(start: date, end: date) -> List[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _parse_month_day(text: str, year: int) -> date:
    month, day = (int(part) for part in text.split("-"))
    return date(year, month, day)


def _closed_days(profile: Profile, start: date, end: date) -> set:
    closed = set()
    for year in range(start.year, end.year + 1):
        for first, last in profile.closures:
            closed.update(_days(_parse_month_day(first, year), _parse_month_day(last, year)))
    return closed


def _holiday_factors(profile: Profile, start: date, end: date) -> Dict[date, float]:
    factors: Dict[date, float] = {}
    for occurrence in calendar_occurrences(profile.country, start.year, end.year):
        if occurrence.kind != EVENT_KIND_HOLIDAY:
            continue

        factor = max(0.0, 1 + float(occurrence.assumed_effect) * profile.holiday_sensitivity)
        for day in occurrence.days():
            factors[day] = factor
    return factors


def _revenue_rows(profile: Profile, rng: random.Random, start: date, end: date) -> List[_Row]:
    closed = _closed_days(profile, start, end)
    holidays = _holiday_factors(profile, start, end)
    rows = []
    for day in _days(start, end):
        base = profile.weekday_revenue[day.weekday()] * profile.month_factors.get(day.month, 1.0) * holidays.get(day, 1.0)
        if not base or day in closed:
            continue

        amount = _money(rng, base, profile.revenue_noise)
        reference = f"Daily Card Revenue Settlement {day:%d.%m.%y}"
        rows.append(_Row(day, "CARD SETTLEMENT", reference, f"{profile.name} Customers (Card)", amount))
    return rows


def _client_rows(profile: Profile, rng: random.Random, start: date, end: date) -> List[_Row]:
    rows = []
    for client in profile.clients:
        issue = date(start.year, start.month, 1)
        while issue <= end:
            due = issue + timedelta(days=30)
            paid = due + timedelta(days=max(0, client.typical_delay_days + rng.randint(-3, 3)))
            if start <= paid <= end:
                reference = f"Invoice {client.prefix}-{issue:%Y%m}"
                rows.append(_Row(paid, "SEPA CREDIT TRANSFER", reference, client.name, _money(rng, client.monthly_amount, 0.1)))
            issue = date(issue.year + issue.month // 12, issue.month % 12 + 1, 1)
    return rows


def _month_starts(start: date, end: date) -> List[date]:
    months = []
    current = date(start.year, start.month, 1)
    while current <= end:
        months.append(current)
        current = date(current.year + current.month // 12, current.month % 12 + 1, 1)
    return months


def _fixed_rows(profile: Profile, rng: random.Random, start: date, end: date) -> List[_Row]:
    rows = []
    for index, month in enumerate(_month_starts(start, end)):
        for salary_name, amount in profile.salaries:
            day = month.replace(day=min(profile.payday, 28))
            rows.append(_Row(day, "SEPA TRANSFER", f"{salary_name} {month:%m/%Y}", salary_name.replace("Salary ", ""), -Decimal(amount)))

        for fixed in profile.fixed:
            if index % fixed.every_months:
                continue
            day = month.replace(day=min(fixed.day, 28))
            rows.append(_Row(day, "SEPA DIRECT DEBIT", f"{fixed.reference} {month:%m/%Y}", fixed.counterparty, -_money(rng, fixed.amount, 0.03)))

    return [row for row in rows if start <= row.day <= end]


def _supplier_rows(profile: Profile, rng: random.Random, start: date, end: date) -> List[_Row]:
    rows = []
    closed = _closed_days(profile, start, end)
    for supplier in profile.suppliers:
        for number, day in enumerate(day for day in _days(start, end) if day.weekday() in supplier.weekdays and day not in closed):
            years = (day - start).days / 365.0
            base = supplier.amount * (1 + supplier.yearly_drift) ** years
            reference = f"Invoice {supplier.counterparty.split()[0].upper()[:4]}-{number + 1:05d} {supplier.reference}"
            rows.append(_Row(day, "SEPA TRANSFER", reference, supplier.counterparty, -_money(rng, base, 0.12)))
    return rows


def _shock_rows(profile: Profile, start: date, end: date) -> List[_Row]:
    rows = []
    for shock in profile.shocks:
        day = start + timedelta(days=shock.day_offset)
        if shock.amount and day <= end:
            rows.append(_Row(day, "SEPA TRANSFER", shock.reference, shock.counterparty, Decimal(shock.amount)))
    return rows


def _format_amount(amount: Decimal) -> str:
    return f"{amount:.2f}".replace(".", ",")


def _csv_line(profile: Profile, row: _Row) -> str:
    booked = f"{row.day:%d.%m.%y}"
    values = (profile.account, booked, booked, row.tx_type, row.reference, row.counterparty, "", "", _format_amount(row.amount), profile.currency, "Generated")
    return ";".join(f'"{value}"' for value in values)


def generate_rows(profile_key: str, years: int = DEFAULT_YEARS, seed: int = DEFAULT_SEED, end: date = DEFAULT_END) -> List[_Row]:
    profile = PROFILES[profile_key]
    rng = random.Random(f"{profile_key}:{seed}")
    start = date(end.year - years + 1, 1, 1)

    rows = [
        *_revenue_rows(profile, rng, start, end),
        *_client_rows(profile, rng, start, end),
        *_fixed_rows(profile, rng, start, end),
        *_supplier_rows(profile, rng, start, end),
        *_shock_rows(profile, start, end),
    ]
    return sorted(rows, key=lambda row: (row.day, row.counterparty, row.amount))


def generate_statement(profile_key: str, years: int = DEFAULT_YEARS, seed: int = DEFAULT_SEED, end: date = DEFAULT_END) -> str:
    """CSV text of a generated bank statement in the sample-statement layout (newest booking first)."""
    profile = PROFILES[profile_key]
    rows = generate_rows(profile_key, years, seed, end)
    return "\n".join([HEADER, *(_csv_line(profile, row) for row in reversed(rows))]) + "\n"


@dataclass(frozen=True)
class BacktestResult:
    profile: str
    split: date
    horizon_days: int
    mean_abs_error: Decimal
    end_error: Decimal
    average_daily_revenue: Decimal

    @property
    def relative_error(self) -> Decimal:
        return (self.mean_abs_error / self.average_daily_revenue).quantize(CENT) if self.average_daily_revenue else ZERO


def _balances(profile: Profile, records: Sequence[CashRecord]) -> Dict[date, Decimal]:
    balance = Decimal(profile.opening_balance)
    by_day: Dict[date, Decimal] = {}
    for record in sorted(records, key=lambda item: item.booking_date):
        balance += record.amount
        by_day[record.booking_date] = balance
    return by_day


def _balance_on(by_day: Dict[date, Decimal], day: date, opening: Decimal) -> Decimal:
    known = [known_day for known_day in by_day if known_day <= day]
    return by_day[max(known)] if known else opening


def _events(profile: Profile, records: Sequence[CashRecord], split: date, horizon_days: int):
    first_year = min(record.booking_date for record in records).year
    return calendar_occurrences(profile.country, first_year, (split + timedelta(days=horizon_days)).year)


def backtest(
    profile_key: str,
    csv_text: str,
    split: Optional[date] = None,
    horizon_days: int = BACKTEST_HORIZON_DAYS,
    use_calendar: bool = True,
) -> BacktestResult:
    """Train on the history up to `split` (default: one year before the last booking) and compare the base forecast with the generated balance."""
    profile = PROFILES[profile_key]
    parsed = parse_bank_statement_csv(csv_text)
    records = [CashRecord(tx["booking_date"], tx["amount_base_currency"], tx["counterparty_name"], tx["category"]) for tx in parsed]

    last = max(record.booking_date for record in records)
    split = split or last - timedelta(days=365)
    by_day = _balances(profile, records)
    opening = Decimal(profile.opening_balance)

    inputs = ForecastInputs(
        as_of=split,
        opening_balance=_balance_on(by_day, split, opening),
        safety_buffer=ZERO,
        horizon_days=horizon_days,
        history=tuple(record for record in records if record.booking_date <= split),
        events=_events(profile, records, split, horizon_days) if use_calendar else (),
    )
    forecast_days = build_forecast(inputs).scenarios["base"].days

    errors = [abs(day.balance - _balance_on(by_day, day.day, opening)) for day in forecast_days]
    revenue = sum((record.amount for record in records if record.amount > 0 and split < record.booking_date <= split + timedelta(days=horizon_days)), ZERO)

    return BacktestResult(
        profile=profile_key,
        split=split,
        horizon_days=horizon_days,
        mean_abs_error=(sum(errors, ZERO) / Decimal(len(errors))).quantize(CENT),
        end_error=errors[-1].quantize(CENT),
        average_daily_revenue=(revenue / Decimal(horizon_days)).quantize(CENT),
    )


def _write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate seeded bank statements for the target-group companies.")
    parser.add_argument("--profile", choices=sorted(PROFILES), help="one profile")
    parser.add_argument("--all", action="store_true", help="every profile")
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", help="output file for --profile")
    parser.add_argument("--out-dir", help="output folder for --all")
    parser.add_argument("--backtest", action="store_true", help="print the forecast error after one year of training")
    args = parser.parse_args()

    keys = sorted(PROFILES) if args.all else [args.profile] if args.profile else []
    if not keys:
        parser.error("choose --profile or --all")

    for key in keys:
        text = generate_statement(key, args.years, args.seed)
        target = args.out if args.profile and args.out else os.path.join(args.out_dir or ".", f"{key}-statement.csv")
        _write(target, text)
        print(f"{key}: {text.count(chr(10)) - 1} rows -> {target}")

        if args.backtest:
            for use_calendar in (False, True):
                result = backtest(key, text, use_calendar=use_calendar)
                print(f"  backtest from {result.split}, {result.horizon_days} days, calendar {'on' if use_calendar else 'off'}: "
                      f"mean abs error {result.mean_abs_error}, end error {result.end_error}, = {result.relative_error} x average daily revenue")


if __name__ == "__main__":
    main()
