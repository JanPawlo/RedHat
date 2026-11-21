"""
Holidays, school breaks, seasons and local events in the cash forecast.

Pure functions without database access. For every event the effect on daily revenue is measured from
the company's own history (revenue in the event window vs. the weeks around it). When the history does
not cover the event yet, the assumed effect from `const/calendar.py` is used and marked as an estimate.

No double counting: when the forecast already uses month seasonality and the event happened in the same
month last time, the month factor already holds its effect spread over the whole month. Then only the
difference is applied (event days down, the rest of that month back up), so the month total stays the same.
"""

import calendar as month_calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from app.const.calendar import (
    DEFAULT_COUNTRY,
    EASTER_EVENTS,
    EFFECT_SOURCE_ESTIMATE,
    EFFECT_SOURCE_MEASURED,
    EVENT_DRIVER_LABEL,
    EVENT_EFFECT_MAX,
    EVENT_EFFECT_MIN,
    EVENT_KIND_COMPANY,
    EVENT_MIN_NORM_DAYS,
    EVENT_MIN_RELEVANT_EFFECT,
    EVENT_NORM_DAYS,
    EVENT_REBALANCE_LABEL,
    FIXED_EVENTS,
)

ZERO = Decimal("0")
ONE = Decimal("1")
EFFECT_PRECISION = Decimal("0.0001")
HUNDRED = Decimal("100")
MONTH_DAY_FORMAT_PARTS = 2


@dataclass(frozen=True)
class EventOccurrence:
    """One concrete occurrence of a calendar event (both dates inclusive)."""

    key: str
    name: str
    kind: str
    start: date
    end: date
    assumed_effect: Decimal

    def days(self) -> List[date]:
        return [self.start + timedelta(days=offset) for offset in range((self.end - self.start).days + 1)]


@dataclass(frozen=True)
class MeasuredEffect:
    effect: Decimal
    occurrences: int
    months: Tuple[int, ...]


@dataclass(frozen=True)
class EventEffect:
    """An event inside the forecast horizon and the revenue effect the forecast applies for it."""

    key: str
    name: str
    kind: str
    start: date
    end: date
    effect: Decimal
    source: str
    measured_occurrences: int
    already_in_base: bool
    revenue_change: Decimal = ZERO
    event_days_change: Decimal = ZERO


@dataclass(frozen=True)
class DayAdjustment:
    multiplier: Decimal
    label: str
    key: str
    on_event_day: bool = True


def easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday (anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, month, day + 1)


def _safe_date(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, month_calendar.monthrange(year, month)[1]))


def _fixed_occurrence(definition: Tuple, year: int) -> EventOccurrence:
    key, name, kind, (start_month, start_day), (end_month, end_day), effect = definition
    start = _safe_date(year, start_month, start_day)
    end_year = year + 1 if (end_month, end_day) < (start_month, start_day) else year
    return EventOccurrence(key, name, kind, start, _safe_date(end_year, end_month, end_day), effect)


def _easter_occurrence(definition: Tuple, year: int) -> EventOccurrence:
    key, name, kind, first_offset, last_offset, effect = definition
    easter = easter_sunday(year)
    return EventOccurrence(key, name, kind, easter + timedelta(days=first_offset), easter + timedelta(days=last_offset), effect)


def _parse_month_day(text: Any) -> Optional[Tuple[int, int]]:
    parts = str(text or "").split("-")
    if len(parts) != MONTH_DAY_FORMAT_PARTS or not all(part.isdigit() for part in parts):
        return None

    month, day = int(parts[0]), int(parts[1])
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return month, day


def _parse_effect(value: Any) -> Optional[Decimal]:
    try:
        effect = Decimal(str(value))
    except InvalidOperation:
        return None

    if not effect.is_finite():
        return None
    return min(max(effect, EVENT_EFFECT_MIN), EVENT_EFFECT_MAX)


def company_event_definitions(raw_events: Any) -> Tuple[Tuple, ...]:
    """Owner's own yearly events from company settings: [{"name", "start": "MM-DD", "end": "MM-DD", "assumed_effect"}]."""
    if not isinstance(raw_events, list):
        return ()

    definitions = []
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            continue

        start = _parse_month_day(raw.get("start"))
        end = _parse_month_day(raw.get("end"))
        effect = _parse_effect(raw.get("assumed_effect", 0))
        name = str(raw.get("name") or "").strip()
        if start and end and effect is not None and name:
            definitions.append((f"company_{index}", name, EVENT_KIND_COMPANY, start, end, effect))

    return tuple(definitions)


def calendar_occurrences(
    country: Optional[str],
    first_year: int,
    last_year: int,
    company_events: Sequence[Tuple] = (),
) -> Tuple[EventOccurrence, ...]:
    """All event occurrences from `first_year` to `last_year` for the country (default PL) plus the company's own events."""
    code = (country or DEFAULT_COUNTRY).upper()
    fixed = (*FIXED_EVENTS.get(code, FIXED_EVENTS[DEFAULT_COUNTRY]), *company_events)
    movable = EASTER_EVENTS.get(code, EASTER_EVENTS[DEFAULT_COUNTRY])

    occurrences: List[EventOccurrence] = []
    for year in range(first_year, last_year + 1):
        occurrences.extend(_fixed_occurrence(definition, year) for definition in fixed)
        occurrences.extend(_easter_occurrence(definition, year) for definition in movable)

    return tuple(sorted(occurrences, key=lambda occurrence: (occurrence.start, occurrence.key)))


def _covered_days(occurrences: Iterable[EventOccurrence]) -> Set[date]:
    return {day for occurrence in occurrences for day in occurrence.days()}


def _norm_days(occurrence: EventOccurrence, history_start: date, as_of: date, event_days: Set[date]) -> List[date]:
    before = [occurrence.start - timedelta(days=offset) for offset in range(1, EVENT_NORM_DAYS + 1)]
    after = [occurrence.end + timedelta(days=offset) for offset in range(1, EVENT_NORM_DAYS + 1)]
    return [day for day in (*before, *after) if history_start <= day <= as_of and day not in event_days]


def _average(inflows: Mapping[date, Decimal], days: Sequence[date]) -> Decimal:
    return sum((inflows.get(day, ZERO) for day in days), ZERO) / Decimal(len(days))


def _measure_occurrence(
    occurrence: EventOccurrence,
    inflows: Mapping[date, Decimal],
    history_start: date,
    as_of: date,
    event_days: Set[date],
) -> Optional[Decimal]:
    if occurrence.start < history_start or occurrence.end > as_of:
        return None

    norm_days = _norm_days(occurrence, history_start, as_of, event_days)
    if len(norm_days) < EVENT_MIN_NORM_DAYS:
        return None

    expected = sum((_weekday_norm(inflows, norm_days, day) for day in occurrence.days()), ZERO)
    if expected <= ZERO:
        return None

    actual = sum((inflows.get(day, ZERO) for day in occurrence.days()), ZERO)
    effect = actual / expected - ONE
    return min(max(effect, EVENT_EFFECT_MIN), EVENT_EFFECT_MAX)


def _weekday_norm(inflows: Mapping[date, Decimal], norm_days: Sequence[date], day: date) -> Decimal:
    """Normal revenue for this weekday around the event (a Sunday is compared with Sundays), else the plain average."""
    same_weekday = [norm_day for norm_day in norm_days if norm_day.weekday() == day.weekday()]
    return _average(inflows, same_weekday or norm_days)


def measure_effects(
    occurrences: Sequence[EventOccurrence],
    inflows: Mapping[date, Decimal],
    history_start: date,
    as_of: date,
) -> Dict[str, MeasuredEffect]:
    """Average revenue effect per event key over the occurrences fully inside the history."""
    event_days = _covered_days(occurrences)
    found: Dict[str, List[Decimal]] = defaultdict(list)
    months: Dict[str, Set[int]] = defaultdict(set)

    for occurrence in occurrences:
        effect = _measure_occurrence(occurrence, inflows, history_start, as_of, event_days - set(occurrence.days()))
        if effect is None:
            continue

        found[occurrence.key].append(effect)
        months[occurrence.key].update(day.month for day in occurrence.days())

    return {
        key: MeasuredEffect(
            effect=(sum(values, ZERO) / Decimal(len(values))).quantize(EFFECT_PRECISION),
            occurrences=len(values),
            months=tuple(sorted(months[key])),
        )
        for key, values in found.items()
    }


def upcoming_effects(
    occurrences: Sequence[EventOccurrence],
    measured: Mapping[str, MeasuredEffect],
    as_of: date,
    horizon_days: int,
    seasonality_active: bool,
) -> Tuple[EventEffect, ...]:
    """Events overlapping the forecast horizon with the effect to apply (measured, else the estimate)."""
    first_day = as_of + timedelta(days=1)
    last_day = as_of + timedelta(days=horizon_days)

    effects: List[EventEffect] = []
    for occurrence in occurrences:
        if occurrence.end < first_day or occurrence.start > last_day:
            continue

        found = measured.get(occurrence.key)
        effect = found.effect if found else occurrence.assumed_effect
        if abs(effect) < EVENT_MIN_RELEVANT_EFFECT:
            continue

        in_base = bool(seasonality_active and found and set(found.months) & {day.month for day in occurrence.days()})
        effects.append(EventEffect(
            key=occurrence.key,
            name=occurrence.name,
            kind=occurrence.kind,
            start=occurrence.start,
            end=occurrence.end,
            effect=effect,
            source=EFFECT_SOURCE_MEASURED if found else EFFECT_SOURCE_ESTIMATE,
            measured_occurrences=found.occurrences if found else 0,
            already_in_base=in_base,
        ))

    return tuple(effects)


def _month_key(day: date) -> Tuple[int, int]:
    return day.year, day.month


def _event_share_by_month(effect: EventEffect) -> Dict[Tuple[int, int], Decimal]:
    counts: Dict[Tuple[int, int], int] = defaultdict(int)
    day = effect.start
    while day <= effect.end:
        counts[_month_key(day)] += 1
        day += timedelta(days=1)

    return {
        month: Decimal(count) / Decimal(month_calendar.monthrange(month[0], month[1])[1])
        for month, count in counts.items()
    }


def _event_multiplier(effect: EventEffect, share: Decimal) -> Decimal:
    if not effect.already_in_base:
        return ONE + effect.effect

    spread = ONE + effect.effect * share
    return (ONE + effect.effect) / spread if spread > ZERO else ONE


def _rest_of_month_multiplier(effect: EventEffect, share: Decimal) -> Decimal:
    spread = ONE + effect.effect * share
    return ONE / spread if spread > ZERO else ONE


def day_adjustments(effects: Sequence[EventEffect], as_of: date, horizon_days: int) -> Dict[date, List[DayAdjustment]]:
    """Revenue multipliers per forecast day, each with a label so the change shows up as its own driver."""
    adjustments: Dict[date, List[DayAdjustment]] = defaultdict(list)

    for effect in effects:
        shares = _event_share_by_month(effect)
        event_label = EVENT_DRIVER_LABEL.format(name=effect.name, source=effect.source)
        rest_label = EVENT_REBALANCE_LABEL.format(name=effect.name, source=effect.source)

        for offset in range(1, horizon_days + 1):
            day = as_of + timedelta(days=offset)
            share = shares.get(_month_key(day))
            if share is None:
                continue

            if effect.start <= day <= effect.end:
                adjustments[day].append(DayAdjustment(_event_multiplier(effect, share), event_label, effect.key))
            elif effect.already_in_base:
                adjustments[day].append(DayAdjustment(_rest_of_month_multiplier(effect, share), rest_label, effect.key, on_event_day=False))

    return adjustments


def event_facts(effects: Sequence[EventEffect]) -> List[Dict[str, Any]]:
    """Calendar events as ready numbers for the LLM, so it explains them instead of calculating."""
    return [
        {
            "event": effect.name,
            "kind": effect.kind,
            "from": str(effect.start),
            "to": str(effect.end),
            "revenue_effect_percent": int((effect.effect * HUNDRED).to_integral_value()),
            "effect_source": effect.source,
            "measured_in_past_occurrences": effect.measured_occurrences,
            "partly_in_month_seasonality_already": effect.already_in_base,
            "revenue_change_on_event_days": float(effect.event_days_change),
            "net_revenue_change_in_forecast": float(effect.revenue_change),
        }
        for effect in effects
    ]
