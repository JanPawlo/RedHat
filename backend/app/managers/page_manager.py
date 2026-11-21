from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.const.forecast import DRIVER_EXPECTED_REVENUE, DRIVER_VARIABLE_COSTS
from app.const.pages import (
    ADVISOR_SPENDING_SEARCH_DAYS,
    ADVISOR_UPCOMING_LIMIT,
    CALENDAR_DAY_NAMES,
    CALENDAR_LEVEL_TOP,
    CALENDAR_WEEKS,
    CATEGORY_LABELS,
    COUNTERPARTY_CATEGORIES,
    DEFAULT_ICON,
    INVOICE_DISCOUNT_SOON_DAYS,
    INVOICE_GROUPS,
    INVOICE_WEEK_DAYS,
    LATE_HIGH_DAYS,
    LATE_MEDIUM_DAYS,
    LEVEL_HIGH,
    LEVEL_LOW,
    LEVEL_MEDIUM,
    LEVEL_POINTS,
    LEVEL_TONES,
    PAID_INVOICE_CATEGORIES,
    REVENUE_CATEGORIES,
    RISK_HISTORY_DAYS,
    RISK_LOOKBACK_DAYS,
    RISK_SCORE_HIGH,
    RISK_SCORE_MEDIUM,
    RISK_SOURCES,
    SHARE_HIGH_PCT,
    SHARE_MEDIUM_PCT,
    STABILITY_MONTHS,
    TAX_DUE_SOON_DAYS,
)
from app.const.invoice import INVOICE_TYPE_INCOMING_EXPENSE, VALIDATION_STATUS_VALID
from app.managers.card_manager import money, short_date
from app.managers.forecast_manager import ForecastContext, load_context
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.services.forecast_engine import SCENARIO_BASE, ScenarioForecast, build_forecast

ZERO = Decimal("0")
HUNDRED = Decimal("100")


@dataclass(frozen=True)
class PageContext:
    forecast_context: ForecastContext
    base: ScenarioForecast
    with_decisions: ScenarioForecast

    @property
    def as_of(self) -> date:
        return self.forecast_context.inputs.as_of

    @property
    def currency(self) -> str:
        return self.forecast_context.account.currency

    @property
    def buffer(self) -> Decimal:
        return self.forecast_context.inputs.safety_buffer

    @property
    def company_name(self) -> str:
        company = self.forecast_context.company
        return company.name if company else self.forecast_context.account.account_name


async def _page_context(db: AsyncSession) -> Optional[PageContext]:
    context = await load_context(db, None, None)
    if not context:
        return None

    base = build_forecast(context.inputs).scenarios[SCENARIO_BASE]
    with_decisions = build_forecast(context.inputs, context.planned_changes).scenarios[SCENARIO_BASE] if context.planned_changes else base
    return PageContext(context, base, with_decisions)


async def _transactions_since(db: AsyncSession, account_id, start: date) -> List[Transaction]:
    query = select(Transaction).where(Transaction.account_id == account_id, Transaction.booking_date >= start).order_by(Transaction.booking_date)
    return list((await db.execute(query)).scalars().all())


async def _all_invoices(db: AsyncSession) -> List[Invoice]:
    return list((await db.execute(select(Invoice))).scalars().all())


def _pct(part: Decimal, whole: Decimal) -> int:
    return int(part / whole * 100) if whole else 0


def _counterparty_categories(rows: Sequence[Transaction]) -> Dict[str, str]:
    counts: Dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        if row.counterparty_name and row.category:
            counts[row.counterparty_name][row.category] += 1

    return {name: counter.most_common(1)[0][0] for name, counter in counts.items()}


def _category_info(category: Optional[str]) -> Dict[str, str]:
    label, icon = CATEGORY_LABELS.get(category or "", ("Payables", DEFAULT_ICON))
    return {"label": label, "icon": icon}


# ---------- Invoices ----------

def _discount(invoice: Invoice, as_of: date) -> Optional[Dict[str, Any]]:
    if not invoice.early_discount_percent or invoice.early_discount_days is None:
        return None

    deadline = invoice.issue_date + timedelta(days=invoice.early_discount_days)
    if deadline < as_of:
        return None

    saving = (invoice.gross_amount * invoice.early_discount_percent / HUNDRED).quantize(Decimal("0.01"))
    return {"deadline": deadline, "days_left": (deadline - as_of).days, "saving": saving, "percent": invoice.early_discount_percent}


def _invoice_group(invoice: Invoice, as_of: date, discount: Optional[Dict[str, Any]]) -> str:
    if invoice.due_date < as_of:
        return "overdue"
    if invoice.due_date == as_of or (discount and discount["days_left"] <= INVOICE_DISCOUNT_SOON_DAYS):
        return "today"
    if (invoice.due_date - as_of).days <= INVOICE_WEEK_DAYS:
        return "week"
    return "later"


def _urgency(invoice: Invoice, as_of: date, discount: Optional[Dict[str, Any]]) -> str:
    days = (invoice.due_date - as_of).days
    if days < 0:
        return f"Overdue {-days} days"
    if discount:
        return f"{discount['percent'].normalize():f}% off until {short_date(discount['deadline'])}"
    if days == 0:
        return "Due today"
    return f"Due in {days} days"


def _progress(invoice: Invoice, as_of: date) -> float:
    term = (invoice.due_date - invoice.issue_date).days
    if term <= 0:
        return 1.0
    return round(min(1.0, max(0.0, (as_of - invoice.issue_date).days / term)), 2)


def _invoice_tile(invoice: Invoice, as_of: date, categories: Dict[str, str], currency: str) -> Dict[str, Any]:
    discount = _discount(invoice, as_of)
    info = _category_info(categories.get(invoice.counterparty_name))
    due = f"Due {short_date(invoice.due_date)}"
    if discount:
        due += f" · {money(invoice.gross_amount - discount['saving'], currency)} until {short_date(discount['deadline'])}"

    details = invoice.validation_details or {}
    return {
        "id": str(invoice.id),
        "supplier": invoice.counterparty_name,
        "category": info["label"],
        "icon": info["icon"],
        "amount": float(invoice.gross_amount),
        "number": invoice.invoice_number,
        "due": due,
        "dueDate": str(invoice.due_date),
        "group": _invoice_group(invoice, as_of, discount),
        "urgency": _urgency(invoice, as_of, discount),
        "progress": _progress(invoice, as_of),
        "discount": bool(discount),
        "discountSaving": float(discount["saving"]) if discount else 0,
        "discountDeadline": str(discount["deadline"]) if discount else None,
        "verified": invoice.validation_status == VALIDATION_STATUS_VALID,
        "riskScore": invoice.risk_score,
        "riskNote": details.get("executive_summary"),
    }


def _paid_this_month(rows: Sequence[Transaction], as_of: date, currency: str) -> Dict[str, Any]:
    month_start = date(as_of.year, as_of.month, 1)
    paid = [row for row in rows if row.booking_date >= month_start and row.amount < 0 and row.category in PAID_INVOICE_CATEGORIES]
    total = sum((-row.amount for row in paid), ZERO)
    return {"count": len(paid), "amount": money(total, currency), "note": f"bank transfers to suppliers and offices in {as_of.strftime('%B')}"}


async def build_invoices_page(db: AsyncSession) -> Optional[Dict[str, Any]]:
    """Open payables grouped by urgency on the forecast start date, plus supplier payments of that month."""
    page = await _page_context(db)
    if not page:
        return None

    as_of = page.as_of
    rows = await _transactions_since(db, page.forecast_context.account.id, as_of - timedelta(days=RISK_HISTORY_DAYS))
    categories = _counterparty_categories(rows)
    invoices = await _all_invoices(db)
    open_payables = [inv for inv in invoices if not inv.is_paid and inv.invoice_type == INVOICE_TYPE_INCOMING_EXPENSE]
    open_payables.sort(key=lambda inv: inv.due_date)

    groups = [dict(group) for group in INVOICE_GROUPS]
    for group in groups:
        if group["id"] == "later":
            group["note"] = f"after {short_date(as_of + timedelta(days=INVOICE_WEEK_DAYS))}"

    return {
        "company": page.company_name,
        "currency": page.currency,
        "today": str(as_of),
        "groups": groups,
        "invoices": [_invoice_tile(inv, as_of, categories, page.currency) for inv in open_payables],
        "paidThisMonth": _paid_this_month(rows, as_of, page.currency),
    }


# ---------- Cash calendar ----------

def _calendar_level(balance: Decimal, buffer: Decimal, top: Decimal) -> int:
    if balance < buffer:
        return 1
    if top <= buffer:
        return CALENDAR_LEVEL_TOP

    share = (balance - buffer) / (top - buffer)
    return min(CALENDAR_LEVEL_TOP, 2 + int(share * (CALENDAR_LEVEL_TOP - 1)))


def _hardest_week(days, currency: str) -> str:
    if not days:
        return "No forecast days."

    weeks: Dict[date, list] = defaultdict(list)
    for day in days:
        weeks[day.day - timedelta(days=day.day.weekday())].append(day)

    start, week = min(weeks.items(), key=lambda item: min(d.balance for d in item[1]))
    outflows: Dict[str, Decimal] = defaultdict(lambda: ZERO)
    for day in week:
        for driver in day.drivers:
            if driver.amount < 0 and driver.label != DRIVER_VARIABLE_COSTS:
                outflows[driver.label] += -driver.amount

    top = [label for label, _ in sorted(outflows.items(), key=lambda item: item[1], reverse=True)[:3]]
    lowest = min(week, key=lambda d: d.balance)
    end = start + timedelta(days=6)
    paid = f" {', '.join(top)} leave that week." if top else ""
    return f"Hardest week: {short_date(start)} – {short_date(end)}. Lowest balance {money(lowest.balance, currency)} on {short_date(lowest.day)}.{paid}"


async def build_cash_calendar(db: AsyncSession) -> Optional[Dict[str, Any]]:
    """Five weeks from the Monday of the forecast start: one heat level per day (1 = under the buffer, 5 = most room)."""
    page = await _page_context(db)
    if not page:
        return None

    as_of = page.as_of
    start = as_of - timedelta(days=as_of.weekday())
    end = start + timedelta(days=CALENDAR_WEEKS * 7 - 1)
    forecast_days = [day for day in page.with_decisions.days if day.day <= end]
    by_date = {day.day: day for day in forecast_days}
    top = max([day.balance for day in forecast_days] + [page.forecast_context.inputs.opening_balance])

    days = []
    current = start
    while current <= end:
        forecast_day = by_date.get(current)
        balance = forecast_day.balance if forecast_day else (page.forecast_context.inputs.opening_balance if current == as_of else None)
        days.append({
            "date": str(current),
            "day": current.day,
            "month": current.strftime("%b"),
            "level": _calendar_level(balance, page.buffer, top) if balance is not None and current >= as_of else 0,
            "balance": float(balance) if balance is not None else None,
            "today": current == as_of,
        })
        current += timedelta(days=1)

    return {
        "range": f"{short_date(start)} – {short_date(end)}",
        "dayNames": CALENDAR_DAY_NAMES,
        "days": days,
        "hardestWeek": _hardest_week(forecast_days, page.currency),
    }


# ---------- Risk ----------

def _level_for_share(share: int) -> str:
    if share >= SHARE_HIGH_PCT:
        return LEVEL_HIGH
    if share >= SHARE_MEDIUM_PCT:
        return LEVEL_MEDIUM
    return LEVEL_LOW


def _liquidity_factor(page: PageContext) -> Dict[str, str]:
    indicators = page.base.indicators
    if indicators.first_below_zero_date:
        return {"label": "Liquidity", "note": f"Balance goes below zero on {short_date(indicators.first_below_zero_date)}", "level": LEVEL_HIGH}
    if indicators.first_below_buffer_date:
        return {"label": "Liquidity", "note": f"Under the buffer from {short_date(indicators.first_below_buffer_date)}, lowest {money(indicators.lowest_balance, page.currency)}", "level": LEVEL_MEDIUM}
    return {"label": "Liquidity", "note": f"Lowest balance {money(indicators.lowest_balance, page.currency)} stays above the buffer", "level": LEVEL_LOW}


def _supplier_factor(rows: Sequence[Transaction]) -> Dict[str, str]:
    spend: Dict[str, Decimal] = defaultdict(lambda: ZERO)
    for row in rows:
        if row.category == "supplier" and row.amount < 0:
            spend[row.counterparty_name or "Other"] += -row.amount

    total = sum(spend.values(), ZERO)
    if not total:
        return {"label": "Supplier dependency", "note": "No supplier payments in the last 90 days", "level": LEVEL_LOW}

    name, amount = max(spend.items(), key=lambda item: item[1])
    share = _pct(amount, total)
    return {"label": "Supplier dependency", "note": f"{name} = {share}% of purchases", "level": _level_for_share(share)}


def _customer_factor(rows: Sequence[Transaction]) -> Dict[str, str]:
    revenue = sum((row.amount for row in rows if row.amount > 0 and row.category in REVENUE_CATEGORIES), ZERO)
    by_client: Dict[str, Decimal] = defaultdict(lambda: ZERO)
    for row in rows:
        if row.category == "revenue_b2b" and row.amount > 0:
            by_client[row.counterparty_name or "Other"] += row.amount

    if not by_client or not revenue:
        return {"label": "Customer concentration", "note": "Revenue comes from the till, no single big client", "level": LEVEL_LOW}

    name, amount = max(by_client.items(), key=lambda item: item[1])
    share = _pct(amount, revenue)
    return {"label": "Customer concentration", "note": f"Top client {name} = {share}% of revenue", "level": _level_for_share(share)}


def _tax_factor(invoices: Sequence[Invoice], rows: Sequence[Transaction], as_of: date, currency: str) -> Dict[str, str]:
    tax_names = {row.counterparty_name for row in rows if row.category in ("tax", "social_security")}
    open_tax = [inv for inv in invoices if not inv.is_paid and inv.counterparty_name in tax_names]
    overdue = [inv for inv in open_tax if inv.due_date < as_of]
    if overdue:
        return {"label": "Taxes & social security", "note": f"{len(overdue)} tax payment overdue", "level": LEVEL_HIGH}
    if open_tax:
        nearest = min(open_tax, key=lambda inv: inv.due_date)
        soon = (nearest.due_date - as_of).days <= TAX_DUE_SOON_DAYS
        return {"label": "Taxes & social security", "note": f"{money(nearest.gross_amount, currency)} due {short_date(nearest.due_date)}, nothing overdue", "level": LEVEL_MEDIUM if soon else LEVEL_LOW}
    return {"label": "Taxes & social security", "note": "Paid every month, nothing open", "level": LEVEL_LOW}


def _fx_factor(rows: Sequence[Transaction]) -> Dict[str, str]:
    costs = sum((-row.amount for row in rows if row.amount < 0), ZERO)
    foreign = sum((-row.amount for row in rows if row.amount < 0 and row.category == "fx_transfer"), ZERO)
    share = _pct(foreign, costs)
    if not foreign:
        return {"label": "Currency (FX)", "note": "No transfers in other currencies", "level": LEVEL_LOW}
    level = LEVEL_MEDIUM if share >= 10 else LEVEL_LOW
    return {"label": "Currency (FX)", "note": f"Transfers abroad = {share}% of costs", "level": level}


def _monthly_revenue(rows: Sequence[Transaction], as_of: date) -> List[Decimal]:
    totals: Dict[tuple, Decimal] = defaultdict(lambda: ZERO)
    for row in rows:
        if row.amount > 0:
            totals[(row.booking_date.year, row.booking_date.month)] += row.amount

    current = (as_of.year, as_of.month)
    months = sorted(key for key in totals if key <= current)[-STABILITY_MONTHS:]
    return [totals[key] for key in months]


def _payment_discipline(invoices: Sequence[Invoice], as_of: date) -> Dict[str, str]:
    payables = [inv for inv in invoices if inv.invoice_type == INVOICE_TYPE_INCOMING_EXPENSE]
    overdue = [inv for inv in payables if not inv.is_paid and inv.due_date < as_of]
    tone = "green" if not overdue else "amber" if len(overdue) < 3 else "red"
    return {"label": "Payment discipline", "value": f"{len(overdue)} overdue", "note": f"of {len(payables)} supplier invoices on file", "tone": tone}


def _lender(page: PageContext, rows: Sequence[Transaction], invoices: Sequence[Invoice]) -> Dict[str, Any]:
    monthly = _monthly_revenue(rows, page.as_of)
    stability = int(pstdev([float(v) for v in monthly]) / mean([float(v) for v in monthly]) * 100) if len(monthly) > 1 and mean([float(v) for v in monthly]) else 0
    loans = [row for row in rows if row.category in ("loan", "leasing")]
    runway = page.base.indicators.runway_months
    runway_text = f"{runway} months" if runway is not None else "Not falling"
    discipline = _payment_discipline(invoices, page.as_of)

    metrics = [
        {"label": "Revenue stability", "value": f"±{stability}%", "note": f"month to month, last {len(monthly)} months", "tone": "green" if stability < 15 else "amber" if stability < 30 else "red"},
        {"label": "Debt service", "value": "No loans" if not loans else f"{len(loans)} payments", "note": "loan or leasing transfers in the statement", "tone": "green" if not loans else "amber"},
        discipline,
        {"label": "Runway", "value": runway_text, "note": "at current costs", "tone": "green" if runway is None or runway >= 6 else "amber" if runway >= 3 else "red"},
    ]
    bad = sum(1 for metric in metrics if metric["tone"] == "red")
    warn = sum(1 for metric in metrics if metric["tone"] == "amber")
    rating = "Weak" if bad else "Fair" if warn > 1 else "Good"

    lowest = page.base.indicators
    insight = (
        f"Revenue moves about ±{stability}% a month and the lowest balance in the next {len(page.base.days)} days is "
        f"{money(lowest.lowest_balance, page.currency)} on {short_date(lowest.lowest_balance_date)}. "
        "This is what a bank looks at before an overdraft; compare any credit offer with simply moving a payment."
    )
    return {"rating": rating, "metrics": metrics, "insight": insight}


def _known_accounts(rows: Sequence[Transaction]) -> Dict[str, set]:
    accounts: Dict[str, set] = defaultdict(set)
    for row in rows:
        if row.counterparty_name and row.counterparty_account:
            accounts[row.counterparty_name].add(row.counterparty_account.replace(" ", "").upper())
    return accounts


def _account_signal(name: str, invoices: Sequence[Invoice], known: Dict[str, set]) -> List[str]:
    ibans = {inv.counterparty_iban.replace(" ", "").upper() for inv in invoices if inv.counterparty_name == name and inv.counterparty_iban}
    if not ibans:
        return ["Matches bank history" if known.get(name) else "No account on file", "green" if known.get(name) else "neutral"]
    if known.get(name) and not ibans <= known[name]:
        return ["Invoice IBAN not in bank history", "red"]
    if not known.get(name):
        return ["New account, never paid", "amber"]
    return ["Invoice IBAN matches payments", "green"]


def _payments_signal(name: str, role: str, late: Dict[str, Any], invoices: Sequence[Invoice], as_of: date, count: int) -> List[str]:
    if role == "Client":
        if name in late:
            days = late[name].typical_delay_days
            return [f"Pays {days} days late", "red" if days >= LATE_HIGH_DAYS else "amber" if days >= LATE_MEDIUM_DAYS else "green"]
        return [f"{count} payments, on time", "green"]

    overdue = [inv for inv in invoices if inv.counterparty_name == name and not inv.is_paid and inv.due_date < as_of]
    if overdue:
        days = max((as_of - inv.due_date).days for inv in overdue)
        return [f"We are {days} days late", "amber"]
    return [f"{count} payments, regular", "green"]


def _counterparty_score(signals: Sequence[List[str]], share: int) -> str:
    tones = [tone for _, tone in signals]
    if "red" in tones:
        return LEVEL_HIGH
    if "amber" in tones or share >= SHARE_MEDIUM_PCT:
        return LEVEL_MEDIUM
    return LEVEL_LOW


def _counterparties(page: PageContext, rows: Sequence[Transaction], invoices: Sequence[Invoice]) -> List[Dict[str, Any]]:
    late = {payer.counterparty: payer for payer in page.forecast_context.late_payers}
    known = _known_accounts(rows)
    totals: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if row.category not in COUNTERPARTY_CATEGORIES or not row.counterparty_name:
            continue
        entry = totals.setdefault(row.counterparty_name, {"amount": ZERO, "count": 0, "category": row.category})
        entry["amount"] += row.amount
        entry["count"] += 1

    spend = sum((-entry["amount"] for entry in totals.values() if entry["amount"] < 0), ZERO)
    income = sum((entry["amount"] for entry in totals.values() if entry["amount"] > 0), ZERO)
    not_connected = ["Not connected", "neutral"]

    result = []
    for name, entry in sorted(totals.items(), key=lambda item: abs(item[1]["amount"]), reverse=True):
        role = "Client" if entry["amount"] > 0 else "Supplier"
        share = _pct(abs(entry["amount"]), income if role == "Client" else spend)
        payments = _payments_signal(name, role, late, invoices, page.as_of, entry["count"])
        account = _account_signal(name, invoices, known)
        score = _counterparty_score([payments, account], share)
        result.append({
            "name": name,
            "role": role,
            "category": _category_info(entry["category"])["label"],
            "share": share,
            "total": money(abs(entry["amount"]), page.currency),
            "score": score,
            "google": not_connected,
            "krz": not_connected,
            "payments": payments,
            "statements": not_connected,
            "account": account,
            "watch": score != LEVEL_LOW,
        })
    return result


def _watch_item(company: Dict[str, Any], currency: str, invoices: Sequence[Invoice], as_of: date) -> Dict[str, str]:
    name = company["name"]
    open_amount = sum((inv.gross_amount for inv in invoices if inv.counterparty_name == name and not inv.is_paid), ZERO)
    open_text = f" ({money(open_amount, currency)} open now)" if open_amount else ""

    if company["account"][1] == "red":
        return {"icon": "landmark", "title": f"{name} put a bank account on the invoice that we never paid before", "note": f"Classic invoice fraud pattern. Confirm the account by phone before paying{open_text}.", "tone": "red"}
    if company["role"] == "Client":
        return {"icon": "building", "title": f"{name}: {company['payments'][0].lower()}", "note": f"Ask for a prepayment or shorter terms on the next order{open_text}.", "tone": "red" if company["score"] == LEVEL_HIGH else "amber"}
    if company["share"] >= SHARE_MEDIUM_PCT:
        return {"icon": "package", "title": f"{name} is {company['share']}% of your purchases", "note": "If they stop delivering, the kitchen stops. Keep a second supplier quoted.", "tone": "amber"}
    return {"icon": "fileText", "title": f"{name}: {company['payments'][0].lower()}", "note": f"Check the open invoices{open_text}.", "tone": "amber"}


def _risk_score(factors: Sequence[Dict[str, str]]) -> int:
    return round(mean(LEVEL_POINTS[factor["level"]] for factor in factors))


def _risk_label(score: int, page: PageContext) -> str:
    level = LEVEL_HIGH if score >= RISK_SCORE_HIGH else LEVEL_MEDIUM if score >= RISK_SCORE_MEDIUM else LEVEL_LOW
    low_date = page.base.indicators.first_below_buffer_date
    return f"{level} · watch {low_date.strftime('%B')}" if low_date else f"{level} · no gap ahead"


async def build_risk_page(db: AsyncSession) -> Optional[Dict[str, Any]]:
    """Business risk from fixed rules on the bank statement, invoices and forecast; external registries are not connected yet."""
    page = await _page_context(db)
    if not page:
        return None

    as_of = page.as_of
    year_rows = await _transactions_since(db, page.forecast_context.account.id, as_of - timedelta(days=RISK_HISTORY_DAYS))
    recent = [row for row in year_rows if row.booking_date > as_of - timedelta(days=RISK_LOOKBACK_DAYS)]
    invoices = await _all_invoices(db)

    factors = [
        _liquidity_factor(page),
        _supplier_factor(recent),
        _customer_factor(recent),
        _tax_factor(invoices, year_rows, as_of, page.currency),
        _fx_factor(recent),
    ]
    score = _risk_score(factors)
    companies = _counterparties(page, year_rows, invoices)
    watch = [company for company in companies if company["watch"]]

    return {
        "company": page.company_name,
        "today": str(as_of),
        "score": score,
        "label": _risk_label(score, page),
        "tone": LEVEL_TONES[LEVEL_HIGH if score >= RISK_SCORE_HIGH else LEVEL_MEDIUM if score >= RISK_SCORE_MEDIUM else LEVEL_LOW],
        "factors": factors,
        "lender": _lender(page, year_rows, invoices),
        "counterparties": companies,
        "counts": {
            "all": len(companies),
            "clients": sum(1 for company in companies if company["role"] == "Client"),
            "suppliers": sum(1 for company in companies if company["role"] == "Supplier"),
            "watchlist": len(watch),
        },
        "watchlist": [_watch_item(company, page.currency, invoices, as_of) for company in watch],
        "sources": RISK_SOURCES,
    }


# ---------- Advisor ----------

def _upcoming_payments(page: PageContext, limit: int) -> List[Dict[str, Any]]:
    payments = []
    for day in page.base.days:
        for driver in day.drivers:
            if driver.amount and driver.label not in (DRIVER_EXPECTED_REVENUE, DRIVER_VARIABLE_COSTS):
                payments.append({"date": str(day.day), "what": driver.label, "amount": float(driver.amount)})
    return payments[:limit]


def _spending_room(days, buffer: Decimal, search_days: int) -> Dict[str, Any]:
    rooms = []
    lowest_ahead = None
    for day in reversed(days):
        lowest_ahead = day.balance if lowest_ahead is None else min(lowest_ahead, day.balance)
        rooms.append((day.day, lowest_ahead - buffer))
    rooms.reverse()

    candidates = rooms[:search_days]
    if not candidates:
        return {}

    best_day, best_room = max(candidates, key=lambda item: item[1])
    first_ok = next((day for day, room in candidates if room > 0), None)
    return {
        "meaning": "largest one-off payment possible on that day without the balance going under the safety buffer on any later day",
        "can_spend_now": float(max(ZERO, candidates[0][1])),
        "first_date_with_room": str(first_ok) if first_ok else None,
        "best_date_to_pay": str(best_day),
        "can_spend_on_best_date": float(max(ZERO, best_room)),
    }


async def build_advisor_facts(db: AsyncSession) -> Optional[Dict[str, Any]]:
    """Engine numbers the advisor chat may quote: balance, buffer, lowest point, runway and the next payments."""
    page = await _page_context(db)
    if not page:
        return None

    base = page.base.indicators
    after = page.with_decisions.indicators
    context = page.forecast_context

    return {
        "company": page.company_name,
        "currency": page.currency,
        "today": str(page.as_of),
        "bank_balance": float(context.inputs.opening_balance),
        "safety_buffer": float(page.buffer),
        "runway_months": float(base.runway_months) if base.runway_months is not None else "not falling",
        "lowest_balance_next_days": {
            "days": len(page.base.days),
            "amount": float(base.lowest_balance),
            "date": str(base.lowest_balance_date),
            "is_below_safety_buffer": base.lowest_balance < page.buffer,
            "short_of_buffer_by": float(max(ZERO, page.buffer - base.lowest_balance)),
            "first_day_below_buffer": str(base.first_below_buffer_date) if base.first_below_buffer_date else None,
        },
        "lowest_balance_after_approved_decisions": {
            "amount": float(after.lowest_balance),
            "date": str(after.lowest_balance_date),
            "is_below_safety_buffer": after.lowest_balance < page.buffer,
        },
        "spending_room": _spending_room(page.with_decisions.days, page.buffer, ADVISOR_SPENDING_SEARCH_DAYS),
        "approved_decisions": [decision.action.title for decision in context.decisions],
        "late_paying_clients": [
            {"client": late.counterparty, "invoice": late.invoice_number, "amount": float(late.amount), "due": str(late.due_date), "expected": str(late.expected_date)}
            for late in context.late_payers
        ],
        "upcoming_payments": _upcoming_payments(page, ADVISOR_UPCOMING_LIMIT),
    }
