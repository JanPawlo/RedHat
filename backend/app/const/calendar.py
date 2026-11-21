from decimal import Decimal

EVENT_KIND_HOLIDAY = "public_holiday"
EVENT_KIND_SCHOOL_BREAK = "school_break"
EVENT_KIND_SEASON = "season"
EVENT_KIND_LOCAL = "local_event"
EVENT_KIND_COMPANY = "company_event"

EFFECT_SOURCE_MEASURED = "measured"
EFFECT_SOURCE_ESTIMATE = "estimate"

DEFAULT_COUNTRY = "PL"
COMPANY_EVENTS_SETTING_KEY = "calendar_events"

EVENT_NORM_DAYS = 28
EVENT_MIN_NORM_DAYS = 14
EVENT_EFFECT_MIN = Decimal("-1")
EVENT_EFFECT_MAX = Decimal("2")
EVENT_MIN_RELEVANT_EFFECT = Decimal("0.02")
EVENT_DRIVER_PREFIX = "Calendar: "
EVENT_DRIVER_LABEL = EVENT_DRIVER_PREFIX + "{name} ({source})"
EVENT_REBALANCE_LABEL = EVENT_DRIVER_PREFIX + "rest of month around {name} ({source})"

# Fixed-date events: (key, name, kind, (start month, day), (end month, day), assumed revenue effect).
# Assumed effects are rough estimates for a small consumer-facing business (share of normal daily revenue,
# -0.30 = 30% less). They are used only when the company's own history does not cover the event yet,
# and are always labelled "estimate". Ranges may wrap over New Year (end before start).
FIXED_EVENTS = {
    "PL": (
        ("pl_new_year", "Nowy Rok", EVENT_KIND_HOLIDAY, (1, 1), (1, 1), Decimal("-0.40")),
        ("pl_epiphany", "Trzech Króli", EVENT_KIND_HOLIDAY, (1, 6), (1, 6), Decimal("-0.20")),
        ("pl_winter_break", "Ferie zimowe (approx.)", EVENT_KIND_SCHOOL_BREAK, (1, 19), (2, 22), Decimal("-0.05")),
        ("pl_labour_day", "Święto Pracy", EVENT_KIND_HOLIDAY, (5, 1), (5, 1), Decimal("-0.20")),
        ("pl_constitution_day", "Święto Konstytucji 3 Maja", EVENT_KIND_HOLIDAY, (5, 3), (5, 3), Decimal("-0.20")),
        ("pl_summer_season", "Sezon letni / wakacje", EVENT_KIND_SEASON, (6, 28), (8, 31), Decimal("0.05")),
        ("pl_assumption", "Wniebowzięcie NMP", EVENT_KIND_HOLIDAY, (8, 15), (8, 15), Decimal("-0.20")),
        ("pl_all_saints", "Wszystkich Świętych", EVENT_KIND_HOLIDAY, (11, 1), (11, 1), Decimal("-0.30")),
        ("pl_independence_day", "Narodowe Święto Niepodległości", EVENT_KIND_HOLIDAY, (11, 11), (11, 11), Decimal("-0.20")),
        ("pl_christmas_market", "Jarmark bożonarodzeniowy", EVENT_KIND_LOCAL, (12, 1), (12, 22), Decimal("0.10")),
        ("pl_christmas", "Wigilia i Boże Narodzenie", EVENT_KIND_HOLIDAY, (12, 24), (12, 26), Decimal("-0.50")),
    ),
    "DE": (
        ("de_new_year", "Neujahr", EVENT_KIND_HOLIDAY, (1, 1), (1, 1), Decimal("-0.40")),
        ("de_labour_day", "Tag der Arbeit", EVENT_KIND_HOLIDAY, (5, 1), (5, 1), Decimal("-0.20")),
        ("de_summer_holidays", "Sommerferien Hessen (approx.)", EVENT_KIND_SCHOOL_BREAK, (7, 1), (8, 10), Decimal("-0.05")),
        ("de_unity_day", "Tag der Deutschen Einheit", EVENT_KIND_HOLIDAY, (10, 3), (10, 3), Decimal("-0.20")),
        ("de_book_fair", "Frankfurter Buchmesse (approx.)", EVENT_KIND_LOCAL, (10, 14), (10, 18), Decimal("0.15")),
        ("de_christmas_market", "Frankfurter Weihnachtsmarkt", EVENT_KIND_LOCAL, (11, 24), (12, 22), Decimal("0.10")),
        ("de_christmas", "Weihnachten", EVENT_KIND_HOLIDAY, (12, 24), (12, 26), Decimal("-0.50")),
        ("de_new_years_eve", "Silvester", EVENT_KIND_HOLIDAY, (12, 31), (12, 31), Decimal("-0.20")),
    ),
}

# Events tied to Easter Sunday: (key, name, kind, first day offset, last day offset, assumed revenue effect).
EASTER_EVENTS = {
    "PL": (
        ("pl_easter", "Wielkanoc", EVENT_KIND_HOLIDAY, 0, 1, Decimal("-0.40")),
        ("pl_pentecost", "Zielone Świątki", EVENT_KIND_HOLIDAY, 49, 49, Decimal("-0.20")),
        ("pl_corpus_christi", "Boże Ciało", EVENT_KIND_HOLIDAY, 60, 60, Decimal("-0.20")),
    ),
    "DE": (
        ("de_easter", "Ostern (Karfreitag – Ostermontag)", EVENT_KIND_HOLIDAY, -2, 1, Decimal("-0.30")),
        ("de_ascension", "Christi Himmelfahrt", EVENT_KIND_HOLIDAY, 39, 39, Decimal("-0.20")),
        ("de_whit_monday", "Pfingstmontag", EVENT_KIND_HOLIDAY, 50, 50, Decimal("-0.20")),
        ("de_corpus_christi", "Fronleichnam", EVENT_KIND_HOLIDAY, 60, 60, Decimal("-0.20")),
    ),
}

EVENT_FACTS_MEANING = (
    "revenue_effect_percent = change of daily revenue in the event window vs. normal days; effect_source 'measured' = "
    "from this company's own history, 'estimate' = assumption because the history does not cover the event yet; "
    "revenue_change_on_event_days = revenue the event adds or removes on its own days; net_revenue_change_in_forecast = "
    "the same after the rest of the month is re-balanced (close to 0 when last year's month seasonality already held the event)"
)

SEASONAL_CARD_PREFIX = "Seasonal liquidity · {event}: "
SEASONAL_CARD_REASON = " {event} ({start} – {end}) changes daily revenue by {percent}% ({source}), {change} on those days."
SEASONAL_CAUSE_MIN_SHARE = Decimal("0.25")
