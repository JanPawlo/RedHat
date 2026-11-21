"""
Rules of the AI guardrail layer (see `app/services/guardrails.py`).

Patterns are matched against text that is lower-cased and stripped of Polish diacritics,
so one pattern covers both "pranie pieniędzy" and "pranie pieniedzy".
"""

GUARDRAIL_CATEGORY_MONEY_LAUNDERING = "money_laundering"
GUARDRAIL_CATEGORY_TAX_EVASION = "tax_evasion"
GUARDRAIL_CATEGORY_FRAUD = "fraud_or_forgery"
GUARDRAIL_CATEGORY_DATA_THEFT = "personal_or_banking_data"
GUARDRAIL_CATEGORY_BRIBERY_SANCTIONS = "bribery_or_sanctions"
GUARDRAIL_CATEGORY_PROMPT_INJECTION = "prompt_injection"

INTENT = r"\b(jak|how\s+(do|can|to|could|would)|pomoz\w*|help\s+(me|us)|chce\w*|want\s+to|sposob\w*\s+na|way\s+to|napisz|write)\b"

ILLEGAL_REQUEST_PATTERNS = {
    GUARDRAIL_CATEGORY_MONEY_LAUNDERING: [
        r"\bpran\w*\s+(brudnych\s+)?pieniedzy",
        r"\bwypra\w*\s+(pieniadz|pieniedz|kas|gotowk)",
        r"\blaunder",
        r"\bsmurfing\b",
        r"\bstructur\w*\s+(the\s+)?(deposit|payment|transfer)s?\b.*\b(avoid|below|under)\b",
        r"\b(rozbi|podziel)\w*\s+.*\b(wplat|przelew|depozyt)\w*.*\b(zglosz|raport|limit|giif|urzad)",
        r"\bbrudn\w*\s+(pieniadz|pieniedz|kas|gotowk)",
        r"\bdirty\s+money\b",
    ],
    GUARDRAIL_CATEGORY_TAX_EVASION: [
        r"\b(unik|unikn|uchyl|omin|obejs|obchodz)\w*\s+(placenia\s+|zaplaty\s+)?(podatk|podatek|vat|zus|pit|cit|akcyz|cla)",
        r"\b(ukry|ukryc|zatai|schowa)\w*\s+.*\b(dochod|przychod|obrot|sprzedaz|zysk)\w*.*\b(przed\s+)?(urzad|skarbow|fisk|us\b|kas)",
        r"\b(ukry|zatai)\w*\s+(dochod|przychod|obrot|sprzedaz|zysk)",
        r"\b(evade|evading|dodge|dodging|avoid\s+paying|not\s+pay)\s+(the\s+)?(\w+\s+)?tax",
        r"\bhide\s+(part\s+of\s+)?(my\s+|our\s+|the\s+|this\s+|that\s+|some\s+|these\s+|those\s+)?(income|revenue|sales|profits?|cash|money|earnings)\b",
        r"\b(fikcyjn|pust|lew|falszyw|podrobion|sfalszowan)\w*\s+(faktur|rachun|paragon|kosztow)",
        r"\b(fake|false|forged|bogus|fictitious)\s+(invoice|receipt|expense|bill)",
        r"\bkaruzel\w*\s+vat",
        r"\bvat\s+carousel\b",
        r"\b(pod\s+stolem|na\s+czarno|bez\s+paragonu)\b",
        r"\boff\s+the\s+books\b",
        r"\b(gotowk|platnos|przychod|sprzedaz|utarg|wplyw)\w*.*\b(nigdzie\s+(sie\s+)?nie|bez\s+sladu)",
        r"\b(zeby|aby|jak)\b.*\b(gotowk|platnos|przychod|sprzedaz|utarg|wplyw)\w*.*\bnie\s+(bylo\s+widac|wykaz|zaksieg|zglos)",
        r"\b(how\s+(can|do|to)|so\s+that|make)\b.*\b(cash|payments?|sales|income|revenue|takings)\b.*\b(not\s+show\s+up|off\s+the\s+record|without\s+a\s+trace|untraceable|invisible\s+to)",
    ],
    GUARDRAIL_CATEGORY_FRAUD: [
        r"\b(sfalszow|podrob|podrabi|falszow|przerob)\w*\s+.*\b(dokument|podpis|faktur|umow|wyciag|zaswiadcz|piecz)",
        r"\b(forge|forging|counterfeit|falsify|falsifying)\b",
        rf"{INTENT}.*\b(wyludz|oszuk|naciag|defraud|scam|cheat)\w*",
        r"\b(napisz|stworz|przygotuj|zrob|wygeneruj|write|create|make|generate|draft)\w*\s+.*\bphishing",
        r"\b(fake|false)\s+(bank\s+statement|balance|financial\s+statement)",
        r"\b(zawyz|zanizy)\w*\s+.*\b(bilans|sprawozdan|wynik|saldo)\w*.*\b(bank|kredyt)",
    ],
    GUARDRAIL_CATEGORY_DATA_THEFT: [
        rf"{INTENT}.*\b(wykrasc|wykradn|ukrasc|zhakowa|wlamac|wlamanie|steal|hack\s+into|break\s+into)\w*",
        r"\b(pesel|numer\w*\s+(karty|kart|dowodu|paszportu)|cvv|cvc|pin\w*|hasl\w*|login\w*|dane\s+osobowe)\b.*\b(klient|pracownik|kontrahent|innej\s+osoby|innych\s+osob|kogos|sasiad|konkurenc)",
        r"\b(personal\s+data|card\s+numbers?|passwords?|credentials|cvv|pin\s+codes?|social\s+security)\b.*\b(customer|client|employee|someone|other\s+people|competitor)",
        r"\b(klient|pracownik|kontrahent|konkurenc)\w*\s+.*\b(pesel|haslo|hasla|numer\w*\s+kart|cvv|dane\s+logowania)\b",
        r"\b(customer|client|employee|competitor)s?'?\s+.*\b(passwords?|card\s+numbers?|credentials|cvv)\b",
    ],
    GUARDRAIL_CATEGORY_BRIBERY_SANCTIONS: [
        r"\blapow\w*",
        r"\b(bribe|bribing|bribery|kickback)",
        r"\b(omin|obejs|obchodz|unikn)\w*\s+sankcj",
        r"\b(evade|evading|bypass|circumvent|avoid)\w*\s+(the\s+)?sanction",
    ],
}

UNSAFE_ANSWER_PATTERNS = [
    *ILLEGAL_REQUEST_PATTERNS[GUARDRAIL_CATEGORY_MONEY_LAUNDERING],
    *ILLEGAL_REQUEST_PATTERNS[GUARDRAIL_CATEGORY_TAX_EVASION],
    *ILLEGAL_REQUEST_PATTERNS[GUARDRAIL_CATEGORY_BRIBERY_SANCTIONS],
    ILLEGAL_REQUEST_PATTERNS[GUARDRAIL_CATEGORY_FRAUD][0],
]

PROMPT_INJECTION_PATTERNS = [
    r"\b(ignore|disregard|forget|override)\s+(all\s+|any\s+)?(the\s+|your\s+)?(previous|prior|above|earlier|system)\s+(instructions|rules|prompts?|messages)",
    r"\b(zignoruj|pomin|zapomnij|olej)\w*\s+(wszystkie\s+|wszelkie\s+)?(poprzedni|wczesniejsz|powyzsz|systemow|swoje)\w*\s+(instrukcj|polecen|zasad|regul)",
    r"\b(system\s+prompt|prompt\s+systemowy|developer\s+mode|tryb\s+deweloper\w*|jailbreak)",
    r"\b(you\s+are\s+now|od\s+teraz\s+jestes|udawaj\s+ze\s+jestes|pretend\s+(to\s+be|you\s+are)|act\s+as\s+if\s+you\s+have\s+no)",
    r"\b(reveal|show|print|repeat|ujawnij|pokaz|wypisz|powtorz)\w*\s+(me\s+|mi\s+)?(your\s+|swoje\s+|twoje\s+)?(hidden\s+|ukryte\s+)?(instructions|instrukcj\w*|prompt|system\s+message)",
    r"\b(no\s+restrictions|without\s+(any\s+)?(rules|restrictions|filters)|bez\s+(zadnych\s+)?(ograniczen|zasad|filtrow))",
]

INJECTION_PLACEHOLDER = "[removed: instruction-like text]"

REFUSAL_ILLEGAL = (
    "I can't help with that. I only explain your company's finances within the law, so I won't assist with "
    "money laundering, tax evasion, fraud, forged documents, bribery or getting other people's personal or banking data. "
    "Ask me about your cash, invoices, forecast or a legal way to close a liquidity gap."
)
REFUSAL_INJECTION = (
    "I can't follow instructions that try to change my rules. "
    "Ask me about your company's cash, invoices or forecast instead."
)
REFUSAL_UNSAFE_ANSWER = (
    "I can't share that answer because it may describe something illegal. "
    "Ask me about a legal way to handle your cash flow, for example a credit line, payment terms or a cost cut."
)

REFUSAL_BY_CATEGORY = {category: REFUSAL_ILLEGAL for category in ILLEGAL_REQUEST_PATTERNS}
REFUSAL_BY_CATEGORY[GUARDRAIL_CATEGORY_PROMPT_INJECTION] = REFUSAL_INJECTION

GUARDRAIL_MODEL_NAME = "guardrail"
GUARDRAIL_BLOCKED_LOG = "Guardrail blocked a %s request (%s)"
GUARDRAIL_REDACTED_LOG = "Guardrail redacted %d sensitive value(s) from a model answer"

PESEL_PATTERN = r"(?<!\d)\d{11}(?!\d)"
PESEL_WEIGHTS = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
CARD_NUMBER_PATTERN = r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"
CARD_NUMBER_MIN_DIGITS = 13
IBAN_PATTERN = r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?\b"
IBAN_VISIBLE_TAIL = 4

REDACTED_PESEL = "[PESEL hidden]"
REDACTED_CARD = "[card number hidden]"
REDACTED_IBAN_PREFIX = "[IBAN ending "
REDACTED_IBAN_SUFFIX = "]"

DIACRITICS_MAP = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
