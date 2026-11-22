LLM_MAX_CONCURRENT_CALLS = 2
LLM_QUEUE_WAIT_SECONDS = 3.0

# Card generation (seed, demo reset, after an invoice upload) waits instead of failing, and leaves a slot for people.
# With 1 slot the demo reset takes roughly twice as long (about 1.5-2 min); the route and proxy allow 5 min.
LLM_BACKGROUND_MAX_CONCURRENT_CALLS = 1
LLM_BACKGROUND_QUEUE_WAIT_SECONDS = 120.0

# Tells apart people who share one login (the demo admin): a random id per browser, sent by the frontend.
# Only for fairness between them; the global slots protect the GPU whatever the client sends.
CLIENT_ID_HEADER = "X-Client-Id"
CLIENT_ID_PATTERN = r"^[A-Za-z0-9-]{8,64}$"

LLM_USER_REQUESTS_PER_MINUTE = 12
LLM_RATE_WINDOW_SECONDS = 60.0

EXPLAIN_CACHE_TTL_SECONDS = 600.0
EXPLAIN_CACHE_MAX_ENTRIES = 256

RETRY_AFTER_HEADER = "Retry-After"
MODEL_BUSY_RETRY_AFTER_SECONDS = 5

BUSY_FALLBACK_MODEL = "forecast-engine"

ADVISOR_FALLBACK_INTRO = "The AI model is busy right now, so here are the forecast engine's numbers without AI."
ADVISOR_FALLBACK_BALANCE = "Bank balance {balance}, safety buffer {buffer}."
ADVISOR_FALLBACK_LOWEST_BELOW = "Lowest balance in the next {days} days: {amount} on {date}, which is {short} under the safety buffer."
ADVISOR_FALLBACK_LOWEST_OK = "Lowest balance in the next {days} days: {amount} on {date}, still above the safety buffer."
ADVISOR_FALLBACK_SPEND_NOW = "You can pay up to {amount} today without going under the buffer later."
ADVISOR_FALLBACK_BEST_DATE = "The best day for a bigger payment is {date} (up to {amount})."
ADVISOR_FALLBACK_OUTRO = "Ask again in a minute for a full answer."
ADVISOR_FALLBACK_DEFAULT_DAYS = "coming"
