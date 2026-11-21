from decimal import Decimal

CARD_HORIZON_DAYS = 60
CARD_WEEKS = 8
BAR_MAX_HEIGHT = 70
BAR_MIN_HEIGHT = 4

AGENT_LIQUIDITY = "liquidity_guard"
AGENT_PAYABLES = "payables_optimizer"
AGENT_RECEIVABLES = "receivables_agent"
AGENT_INVESTMENT = "investment_agent"

AGENT_DISPLAY = {
    AGENT_LIQUIDITY: ("Liquidity", "LIQUIDITY", "landmark", True),
    AGENT_PAYABLES: ("Payables", "PAYABLES", "package", False),
    AGENT_RECEIVABLES: ("Collections", "COLLECTIONS", "users", False),
    AGENT_INVESTMENT: ("Investment", "INVESTMENT", "trendingUp", True),
}
DEFAULT_AGENT_DISPLAY = ("Agent", "AGENT", "file", False)

SOURCE_FORECAST = "forecast"
SOURCE_INVOICE = "invoice"

CREDIT_LINE_STEP = Decimal("1000")
CREDIT_LINE_YEARLY_RATE = Decimal("0.08")
DEPOSIT_YEARLY_RATE = Decimal("0.03")
DEPOSIT_MIN_FREE_CASH = Decimal("5000")
DEPOSIT_SHARE_OF_FREE_CASH = Decimal("0.6")
DEPOSIT_TERM_DAYS = 30
DEFER_DAYS = 30
DEFER_WINDOW_BEFORE_DAYS = 10
DEFER_WINDOW_AFTER_DAYS = 5
RELIABLE_SUPPLIER_MIN_PAYMENTS = 6
ON_TIME_DISCOUNT_PERCENT = Decimal("2")
MONTHS_PER_YEAR = Decimal("12")
INTEREST_DAYS = 30
HOLD_TO_CONFIRM_ABOVE = Decimal("10000")
TAX_COUNTERPARTY_MARKERS = ("tax", "finanzamt", "urząd skarbowy", "zus")

AUTONOMY_REQUIRES_APPROVAL = "Requires approval"
CARD_SOURCES = "Bank statement · open invoices · recurring payments · forecast engine"
RESULT_SUFFIX = " · SIMULATED"

PRIORITY_KEY = "priority"
SWIPE_RIGHT_KEY = "swipe_right_label"
SWIPE_LEFT_KEY = "swipe_left_label"
MAIL_KEY = "mail"
NEXT_SUB_KEY = "next_sub"

EXPLAIN_FALLBACK_MODEL = "forecast engine (model unavailable)"
CONFIDENCE_METHOD = (
    "Expected revenue is varied in {steps} steps from {low}% to {high}% of the expected level "
    "(spread from weekly revenue volatility, at least ±10%). Confidence = (safe steps + 1) / (steps + 2), where a safe step "
    "keeps the balance above the safety buffer during the next {days} days; the +1 / +2 keeps it below 100% and above 0%, "
    "because the forecast can never be certain."
)
RESPONSE_SOURCE_MODEL = "model"
RESPONSE_SOURCE_FALLBACK = "deterministic_fallback"
