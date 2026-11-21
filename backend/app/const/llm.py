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
    "Keep your explanation concise (2-4 short sentences)."
)
