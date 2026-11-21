UNKNOWN_MODEL_NAME = "unknown"
MODEL_STATUS_CONNECTED = "connected"

HEALTH_TIMEOUT_SECONDS = 10.0
COMPLETION_TIMEOUT_SECONDS = 60.0
COMPLETION_TEMPERATURE = 0.2
COMPLETION_MAX_TOKENS = 250
CHAT_TEMPLATE_KWARGS = {"enable_thinking": False}

SYSTEM_PROMPT = (
    "You are an Autonomous CFO assistant for small and medium-sized business owners. "
    "Explain financial recommendations in simple, friendly, plain language without corporate jargon. "
    "STRICT RULE: Never invent or calculate any numbers yourself. Use ONLY the exact numbers provided in FACTS. "
    "When FACTS contain an engine section, the confidence comes from it: explain it with confidence_method and "
    "revenue_scenarios_with_card (how many revenue levels keep the safety buffer), and name the payments that cause the gap. "
    "Keep your explanation concise (2-4 short sentences)."
)

ADVISOR_MAX_TOKENS = 320
ADVISOR_PROMPT = (
    "You are the CFO advisor of a small business owner. You read FACTS (numbers from the forecast engine) and NOTES "
    "(the owner's own notes, voice messages and meeting summaries). Answer in plain, friendly language. "
    "When the owner plans a purchase or expense, answer WHEN to pay from FACTS.spending_room: if the amount is not more than "
    "can_spend_now they can pay now; otherwise recommend best_date_to_pay and say how much can_spend_on_best_date allows; "
    "if the amount is larger than both, say it would push the balance under the safety buffer. "
    "Never recommend paying on or before the lowest balance date when lowest_balance_next_days.is_below_safety_buffer is true. "
    "Warn about risks (late paying clients, big upcoming payments) and if the expense is large, ask them to confirm they really want it. "
    "STRICT RULE: use ONLY numbers that appear in FACTS, NOTES or earlier messages, never calculate or invent new ones. "
    "Amounts are in the currency given in FACTS. Answer in the language of the question. Keep it to 3-5 short sentences."
)

EXPLAIN_MODE_CARD = "card"
EXPLAIN_MODE_ADVISOR = "advisor"
EXPLAIN_MODES = (EXPLAIN_MODE_CARD, EXPLAIN_MODE_ADVISOR)
CHAT_ROLES = ("user", "assistant")
CHAT_HISTORY_MAX_TURNS = 12
CHAT_MESSAGE_MAX_LENGTH = 4000
