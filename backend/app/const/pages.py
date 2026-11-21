LEVEL_LOW = "Low"
LEVEL_MEDIUM = "Medium"
LEVEL_HIGH = "High"
LEVEL_POINTS = {LEVEL_LOW: 15, LEVEL_MEDIUM: 50, LEVEL_HIGH: 85}
LEVEL_TONES = {LEVEL_LOW: "green", LEVEL_MEDIUM: "amber", LEVEL_HIGH: "red"}

RISK_SCORE_MEDIUM = 40
RISK_SCORE_HIGH = 70
RISK_LOOKBACK_DAYS = 90
RISK_HISTORY_DAYS = 365
STABILITY_MONTHS = 6
SHARE_MEDIUM_PCT = 40
SHARE_HIGH_PCT = 60
LATE_MEDIUM_DAYS = 3
LATE_HIGH_DAYS = 14
TAX_DUE_SOON_DAYS = 30

COUNTERPARTY_CATEGORIES = ("supplier", "revenue_b2b", "rent", "utility", "fx_transfer")
REVENUE_CATEGORIES = ("revenue_pos", "revenue_b2b")
PAID_INVOICE_CATEGORIES = ("supplier", "rent", "utility", "tax", "social_security")

DEFAULT_ICON = "fileText"
CATEGORY_LABELS = {
    "supplier": ("Ingredients · Payables", "package"),
    "rent": ("Rent · Fixed cost", "building"),
    "utility": ("Energy · Utilities", "flame"),
    "tax": ("Tax office", "landmark"),
    "social_security": ("Social security", "shield"),
    "fx_transfer": ("Transfer abroad", "wallet"),
    "revenue_b2b": ("Catering client", "building"),
}

INVOICE_WEEK_DAYS = 7
INVOICE_DISCOUNT_SOON_DAYS = 1
INVOICE_GROUPS = (
    {"id": "overdue", "label": "Overdue", "tone": "red", "note": "pay today"},
    {"id": "today", "label": "Today", "tone": "blue", "note": "due today or discount ends"},
    {"id": "week", "label": "This week", "tone": "amber"},
    {"id": "later", "label": "Later", "tone": "green"},
)

CALENDAR_WEEKS = 5
CALENDAR_LEVEL_TOP = 5
CALENDAR_DAY_NAMES = ["M", "T", "W", "T", "F", "S", "S"]

ADVISOR_UPCOMING_LIMIT = 25
ADVISOR_SPENDING_SEARCH_DAYS = 60

RISK_SOURCES = (
    {"icon": "fileText", "label": "Your history", "note": "Bank statement + invoices: who pays late, who we depend on"},
    {"icon": "landmark", "label": "Bank account check", "note": "Invoice IBAN compared with accounts we already paid"},
    {"icon": "trendingUp", "label": "Cash forecast", "note": "Lowest balance and the buffer from the forecast engine"},
    {"icon": "star", "label": "Google reviews", "note": "Not connected yet"},
    {"icon": "ban", "label": "Debtor registries", "note": "Not connected yet"},
)
