API_TITLE_DESCRIPTION = """
Agentic Autonomous CFO for SMEs (Red Hat Collabothon 2026).

**Principle:** the engine calculates, the AI explains. Every number comes from deterministic code;
the language model only puts it into words.

**How to start testing**

1. `POST /api/v1/auth/login` with your login and password, copy `access_token`.
2. Click **Authorize** (top right) and paste the token.
3. With demo data seeded (Pizzeria Amalfi) try `GET /api/v1/forecast`, then `POST /api/v1/forecast/simulate`.

Every endpoint except login, register and health needs the token.
Grouped view of the same API: [/redoc](/redoc).
"""

TAG_HEALTH = "Access · Health"
TAG_AUTH = "Access · Auth"
TAG_COMPANY = "Company data · Profile"
TAG_ACCOUNTS = "Company data · Accounts"
TAG_TRANSACTIONS = "Company data · Transactions"
TAG_STATEMENTS = "Company data · Statement import"
TAG_FORECAST = "Engine · Forecast"
TAG_INVOICES = "Invoices · Validation"
TAG_ACTIONS = "Cards & AI · Decision cards"
TAG_AI = "Cards & AI · Model"

OPENAPI_TAGS = [
    {"name": TAG_HEALTH, "description": "Is the API running. Public, no token."},
    {"name": TAG_AUTH, "description": "Login and registration. Returns the JWT used by every other endpoint."},
    {"name": TAG_COMPANY, "description": "Company profile and agent settings (safety buffer, forecast horizon)."},
    {"name": TAG_ACCOUNTS, "description": "Bank accounts with their current balance. The primary account is used by default."},
    {"name": TAG_TRANSACTIONS, "description": "Booked bank transactions (history the engine learns from)."},
    {"name": TAG_STATEMENTS, "description": "Import of bank statement CSV files into transactions."},
    {"name": TAG_FORECAST, "description": "Deterministic cash forecast: scenarios, indicators and 'what if' simulation. Source of the chart and of card numbers."},
    {"name": TAG_INVOICES, "description": "Invoice checks: math, duplicates, IBAN phishing, price spikes, liquidity impact, early payment discount."},
    {"name": TAG_ACTIONS, "description": "Decision cards for the swipe deck: list, approve/reject, 'Ask why' explained by the LLM."},
    {"name": TAG_AI, "description": "Connection to the language model on OpenShift AI (vLLM)."},
]

OPENAPI_TAG_GROUPS = [
    {"name": "Access", "tags": [TAG_HEALTH, TAG_AUTH]},
    {"name": "Company data", "tags": [TAG_COMPANY, TAG_ACCOUNTS, TAG_TRANSACTIONS, TAG_STATEMENTS]},
    {"name": "Engine", "tags": [TAG_FORECAST]},
    {"name": "Invoices", "tags": [TAG_INVOICES]},
    {"name": "Cards & AI", "tags": [TAG_ACTIONS, TAG_AI]},
]
OPENAPI_TAG_GROUPS_KEY = "x-tagGroups"

SWAGGER_UI_PARAMETERS = {
    "docExpansion": "none",
    "filter": True,
    "persistAuthorization": True,
    "displayRequestDuration": True,
    "tryItOutEnabled": True,
}

RESPONSE_UNAUTHORIZED = {401: {"description": "Missing or invalid token"}}

EXAMPLE_LOGIN = {"email": "admin", "password": "admin"}

EXAMPLE_SIMULATION = {
    "changes": [
        {"on_date": "2026-01-05", "amount": "-25000.00", "label": "New pizza oven"},
        {"on_date": "2026-01-10", "amount": "15000.00", "label": "Commerzbank credit line"},
    ]
}

EXAMPLE_INVOICE = {
    "invoice_number": "AS-80115",
    "invoice_type": "incoming_expense",
    "issue_date": "2026-01-02",
    "due_date": "2026-01-30",
    "counterparty_name": "Asimex Wholesale Ltd",
    "counterparty_iban": "DE33500105170011223344",
    "net_amount": "600.00",
    "tax_amount": "42.00",
    "gross_amount": "642.00",
    "currency": "EUR",
    "early_discount_percent": "2.00",
    "early_discount_days": 10,
    "description": "Food & Italian ingredients delivery",
}
