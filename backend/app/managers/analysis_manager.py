from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.managers.card_manager import money, short_date
from app.managers.forecast_manager import load_context
from app.models.account import BankAccount
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.services.cash_flow import validate_transactions
from app.services.currency_normalizer import normalize_to_base_currency
from app.services.forecast_engine import SCENARIO_BASE, build_forecast

ZERO = Decimal("0")
WEEK_DAYS = 7
QUARTER_MONTHS = 3

CATEGORY_REVENUE_POS = "revenue_pos"
CATEGORY_SUPPLIER = "supplier"
CATEGORY_PAYROLL = "payroll"
CATEGORY_SOCIAL = "social_security"

EVENT_LABELS = {
    "rent": "Rent",
    "payroll": "Payroll",
    "social_security": "Social security",
    "tax": "Tax",
    "utility": "Energy & utilities",
    "fx_transfer": "Transfer abroad",
    "revenue_b2b": "Catering invoice",
}

DATA_ISSUE_LABELS = {
    "missing_or_invalid_date": "without a valid date",
    "missing_account": "without an account",
    "account_mismatch": "from another account",
    "missing_currency": "without a currency",
    "currency_mismatch": "in another currency",
    "missing_or_invalid_amount": "without a valid amount",
    "missing_category": "without a category",
    "unclassified_category": "marked as 'other'",
    "possible_duplicate": "possible duplicates",
}

BREAKDOWN_GROUPS = [
    ("Payroll & social security", ("payroll", "social_security"), "bg-green-900", "#23382B"),
    ("Ingredients & suppliers", ("supplier",), "bg-green-700", "#3F5E4A"),
    ("Rent", ("rent",), "bg-green-500", "#6F8F78"),
    ("Energy & utilities", ("utility",), "bg-heat-4", "#B8D3BE"),
    ("Taxes & other", None, "bg-heat-3", "#E2B45C"),
]


@dataclass(frozen=True)
class Quarter:
    start: date
    end: date
    today: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def offset(self, day: date) -> int:
        return (day - self.start).days


def _quarter(as_of: date) -> Quarter:
    first_month = (as_of.month - 1) // QUARTER_MONTHS * QUARTER_MONTHS + 1
    start = date(as_of.year, first_month, 1)
    next_start = date(start.year + 1, 1, 1) if first_month + QUARTER_MONTHS > 12 else date(start.year, first_month + QUARTER_MONTHS, 1)
    return Quarter(start=start, end=next_start - timedelta(days=1), today=as_of)


def _month_start(day: date) -> date:
    return date(day.year, day.month, 1)


def _next_month(day: date) -> date:
    return date(day.year + 1, 1, day.day) if day.month == 12 else date(day.year, day.month + 1, min(day.day, 28))


def _pct(part: Decimal, whole: Decimal) -> int:
    return int(part / whole * 100) if whole else 0


async def _transactions(db: AsyncSession, account: BankAccount, start: date, end: date) -> List[Transaction]:
    query = select(Transaction).where(
        Transaction.account_id == account.id, Transaction.booking_date >= start, Transaction.booking_date <= end
    ).order_by(Transaction.booking_date)
    rows = (await db.execute(query)).scalars().all()

    return normalize_to_base_currency(rows, account.currency)


async def _invoices(db: AsyncSession) -> List[Invoice]:
    return list((await db.execute(select(Invoice))).scalars().all())


def _last_week(quarter: Quarter) -> int:
    return (quarter.days - WEEK_DAYS) // WEEK_DAYS * WEEK_DAYS


def _weeks(rows: Sequence[Transaction], quarter: Quarter) -> List[Dict[str, Any]]:
    weeks: Dict[int, Dict[str, Decimal]] = defaultdict(lambda: {"revenue": ZERO, "expenses": ZERO})
    for row in rows:
        bucket = min(quarter.offset(row.booking_date) // WEEK_DAYS * WEEK_DAYS, _last_week(quarter))
        key = "revenue" if row.amount > 0 else "expenses"
        weeks[bucket][key] += abs(row.amount)

    return [
        {"day": day, "revenue": float(weeks[day]["revenue"]), "expenses": float(weeks[day]["expenses"])}
        for day in range(0, _last_week(quarter) + 1, WEEK_DAYS)
    ]


def _events(rows: Sequence[Transaction], quarter: Quarter) -> List[Dict[str, Any]]:
    grouped: Dict[tuple, Dict[str, Any]] = {}
    for row in rows:
        if row.category not in EVENT_LABELS:
            continue

        key = (row.booking_date, row.category)
        event = grouped.setdefault(key, {"amount": ZERO, "who": set()})
        event["amount"] += row.amount
        event["who"].add(row.counterparty_name or "")

    events = []
    for (day, category), event in sorted(grouped.items()):
        who = sorted(name for name in event["who"] if name)
        events.append({
            "day": quarter.offset(day),
            "kind": "in" if event["amount"] > 0 else "out",
            "label": EVENT_LABELS[category],
            "who": f"{len(who)} people" if category == CATEGORY_PAYROLL else ", ".join(who),
            "amount": float(abs(event["amount"])),
        })
    return events


def _breakdown(rows: Sequence[Transaction], quarter: Quarter, currency: str) -> Dict[str, Any]:
    by_category: Dict[str, Decimal] = defaultdict(lambda: ZERO)
    by_supplier: Dict[str, Decimal] = defaultdict(lambda: ZERO)
    for row in rows:
        if row.amount >= 0:
            continue

        by_category[row.category or ""] += -row.amount
        if row.category == CATEGORY_SUPPLIER:
            by_supplier[row.counterparty_name or "Other"] += -row.amount

    named = {category for _, categories, _, _ in BREAKDOWN_GROUPS if categories for category in categories}
    items = []
    for label, categories, color, hex_color in BREAKDOWN_GROUPS:
        amount = sum((by_category[c] for c in categories), ZERO) if categories else sum(
            (value for category, value in by_category.items() if category not in named), ZERO
        )
        items.append({"label": label, "amount": float(amount), "color": color, "hex": hex_color})

    supplier_total = sum(by_supplier.values(), ZERO)
    top = max(by_supplier.items(), key=lambda item: item[1]) if by_supplier else None
    insight = (
        f"{top[0]} is {_pct(top[1], supplier_total)}% of supplier costs this quarter ({money(top[1], currency)} of {money(supplier_total, currency)})."
        if top else "No supplier payments in this quarter."
    )
    period = f"{short_date(quarter.start)} – {short_date(min(quarter.end, quarter.today))}"
    return {"period": period, "items": items, "insight": insight}


def _last_month_payroll(rows: Sequence[Transaction]) -> List[Transaction]:
    payroll = [row for row in rows if row.category == CATEGORY_PAYROLL]
    if not payroll:
        return []

    last_month = _month_start(payroll[-1].booking_date)
    return [row for row in payroll if _month_start(row.booking_date) == last_month]


def _team(rows: Sequence[Transaction], owner: Optional[str], currency: str) -> Dict[str, Any]:
    payroll = _last_month_payroll(rows)
    social = sum((-row.amount for row in rows if row.category == CATEGORY_SOCIAL and payroll and _month_start(row.booking_date) == _month_start(payroll[-1].booking_date)), ZERO)
    total = sum((-row.amount for row in payroll), ZERO)

    team = [
        {
            "name": row.counterparty_name,
            "role": "Owner" if owner and row.counterparty_name == owner else "Staff",
            "status": f"Paid {short_date(row.booking_date)}",
            "tone": "green",
            "pay": money(-row.amount, currency),
        }
        for row in sorted(payroll, key=lambda item: item.amount)
    ]
    insight = (
        f"Payroll last month was {money(total, currency)} for {len(team)} people; social security added {money(social, currency)}."
        if team else "No payroll transfers found in this quarter."
    )
    return {"team": team, "teamMore": 0, "teamTotal": money(total, currency), "teamInsight": insight, "payroll_total": total, "social": social}


def _invoice_gauge(invoices: Sequence[Invoice], as_of: date, currency: str) -> Dict[str, Any]:
    paid = [invoice for invoice in invoices if invoice.is_paid]
    open_ = [invoice for invoice in invoices if not invoice.is_paid]
    overdue = [invoice for invoice in open_ if invoice.due_date and invoice.due_date < as_of]
    to_pay = [invoice for invoice in open_ if invoice not in overdue]

    def total(items: Sequence[Invoice]) -> Decimal:
        return sum((invoice.gross_amount for invoice in items), ZERO)

    return {
        "paidPct": _pct(Decimal(len(paid)), Decimal(len(invoices))),
        "paidCount": len(paid),
        "totalCount": len(invoices),
        "rows": [
            {"label": f"Paid · {len(paid)}", "amount": money(total(paid), currency), "color": "bg-green-700"},
            {"label": f"To pay · {len(to_pay)}", "amount": money(total(to_pay), currency), "color": "bg-heat-3"},
            {"label": f"Overdue · {len(overdue)}", "amount": money(total(overdue), currency), "color": "bg-status-red"},
        ],
    }


def _kpis(rows: Sequence[Transaction], invoices: Sequence[Invoice], team: Dict[str, Any], as_of: date, currency: str) -> List[Dict[str, Any]]:
    payroll = _last_month_payroll(rows)
    next_payroll = _next_month(payroll[-1].booking_date) if payroll else None
    expenses = [invoice for invoice in invoices if not invoice.is_paid and invoice.invoice_type == "incoming_expense"]
    overdue = [invoice for invoice in expenses if invoice.due_date and invoice.due_date < as_of]
    expense_total = sum((invoice.gross_amount for invoice in expenses), ZERO)
    overdue_total = sum((invoice.gross_amount for invoice in overdue), ZERO)

    return [
        {
            "icon": "calendar",
            "label": "Next payroll",
            "value": f"in {(next_payroll - as_of).days} days" if next_payroll else "not planned",
            "sub": f"{short_date(next_payroll)} · {team['teamTotal']}" if next_payroll else "no payroll history",
            "highlight": True,
        },
        {"icon": "wallet", "label": "Payroll last month", "value": team["teamTotal"], "sub": f"plus social security {money(team['social'], currency)}"},
        {"icon": "users", "label": "Team", "value": f"{len(team['team'])} people", "sub": "from payroll transfers"},
        {
            "icon": "fileText",
            "label": "Invoices to pay",
            "value": f"{len(expenses)} · {money(expense_total, currency)}",
            "sub": f"{len(overdue)} overdue · {money(overdue_total, currency)}",
        },
    ]


def _data_quality(rows: Sequence[Transaction], account_id, currency: str) -> Dict[str, Any]:
    validation = validate_transactions(rows, account_id, currency)

    counts: Dict[str, int] = defaultdict(int)
    for issue in (*validation.errors, *validation.warnings):
        counts[issue.code] += len(issue.transaction_indexes) or 1

    issues = [{"code": code, "count": count, "label": DATA_ISSUE_LABELS.get(code, code)} for code, count in counts.items()]

    return {
        "checked": len(rows),
        "errors": len(validation.errors),
        "warnings": len(validation.warnings),
        "issues": issues,
    }


def _meters(rows: Sequence[Transaction], balance: Decimal, runway: Any, currency: str) -> List[Dict[str, Any]]:
    revenue = sum((row.amount for row in rows if row.amount > 0), ZERO)
    costs = sum((-row.amount for row in rows if row.amount < 0), ZERO)
    margin = _pct(revenue - costs, revenue)
    pos_share = _pct(sum((row.amount for row in rows if row.category == CATEGORY_REVENUE_POS), ZERO), revenue)
    runway_text = f"{runway} months" if isinstance(runway, (int, float, Decimal)) else "Not falling"

    return [
        {"icon": "wallet", "label": "Cash", "value": money(balance, currency), "pct": min(100, _pct(balance, costs / QUARTER_MONTHS)), "sub": "in the bank today"},
        {"icon": "hourglass", "label": "Runway", "value": runway_text, "pct": 100 if runway_text == "Not falling" else min(100, int(Decimal(str(runway)) * 10)), "sub": "at current costs"},
        {"icon": "users", "label": "Margin", "value": f"{margin}%", "pct": max(0, margin), "sub": f"revenue {money(revenue, currency)} this quarter", "warn": margin < 10},
        {"icon": "shield", "label": "Card & cash sales", "value": f"{pos_share}%", "pct": pos_share, "sub": "of revenue from the till"},
    ]


async def build_analysis(db: AsyncSession) -> Optional[Dict[str, Any]]:
    """Analysis page data computed from the bank statement and invoices in the database (same shape as the frontend mock)."""
    context = await load_context(db, None, None)
    if not context:
        return None

    account = context.account
    currency = account.currency
    as_of = context.inputs.as_of
    quarter = _quarter(as_of)

    rows = await _transactions(db, account, quarter.start, quarter.end)
    invoices = await _invoices(db)
    owner = (context.company.settings or {}).get("owner_name") if context.company else None

    forecast = build_forecast(context.inputs, context.planned_changes)
    runway = forecast.scenarios[SCENARIO_BASE].indicators.runway_months
    team = _team(rows, owner, currency)

    months = []
    month = quarter.start
    while month <= quarter.end:
        months.append({"day": quarter.offset(month), "label": month.strftime("%b")})
        month = _next_month(month)

    return {
        "company": context.company.name if context.company else account.account_name,
        "currency": currency,
        "label": f"Q{(quarter.start.month - 1) // QUARTER_MONTHS + 1} {quarter.start.year} · {quarter.start.strftime('%b')}–{quarter.end.strftime('%b')}",
        "range": f"{short_date(quarter.start)} – {short_date(quarter.end)} {quarter.end.year}",
        "kpis": _kpis(rows, invoices, team, as_of, currency),
        "q4": {
            "label": f"Q{(quarter.start.month - 1) // QUARTER_MONTHS + 1} {quarter.start.year} · {quarter.start.strftime('%b')}–{quarter.end.strftime('%b')}",
            "start": str(quarter.start),
            "days": quarter.days,
            "today": min(quarter.offset(as_of), quarter.days),
            "months": months,
            "weeks": _weeks(rows, quarter),
            "events": _events(rows, quarter),
        },
        "breakdown": _breakdown(rows, quarter, currency),
        "team": team["team"],
        "teamMore": team["teamMore"],
        "teamTotal": team["teamTotal"],
        "teamInsight": team["teamInsight"],
        "invoiceGauge": _invoice_gauge(invoices, as_of, currency),
        "meters": _meters(rows, account.current_balance, runway, currency),
        "dataQuality": _data_quality(rows, account.id, currency),
    }
