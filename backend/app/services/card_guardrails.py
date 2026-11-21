"""
Guardrails for everything the AI writes on and about decision cards.

Pure checks with no model or database access. Each check returns human-readable violations; the writer feeds
them back to the model once and falls back to the template's fixed text if they remain. Rules (also in
memory/spec/szablony-kart.md):

- Facts: every number, date, currency, company and bank in the text must come from the card's slots.
- Form: length, sentences and words per field; plain text only; English letters only; no links, e-mail or IBAN.
- Clarity: plain-language fields pass a readability score, avoid finance jargon and speak to the owner as "you".
- Tone: no pressure, hype or promises; titles are calm, precise questions.
- Safety: never suggest skipping taxes, social security or salaries, or misleading anyone; template-specific
  required statements (the other side must agree, the bank decides, the money is locked).
- Injection: untrusted names are cleaned before they reach a prompt.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from app.const.card_templates import (
    ALLOWED_SCRIPT_PATTERN,
    CONDITIONAL_MARKERS,
    DROP_SLOTS,
    DROP_VERBS,
    RISE_VERBS,
    WITH_CARD_SLOTS,
    COPY_FIELDS,
    CURRENCY_TOKENS,
    EXPLAIN_ANSWER_MAX_CHARS,
    EXPLAIN_ANSWER_MAX_SENTENCES,
    FIELD_EXPLANATION,
    FIELD_PROPOSAL,
    FIELD_RANK_REASON,
    FIELD_SPECS,
    FIELD_TITLE,
    FORBIDDEN_ADVICE_PATTERNS,
    FORBIDDEN_PHRASES,
    FORMAT_LEAK_PATTERNS,
    IBAN_PATTERN,
    INJECTION_MARKERS,
    JARGON_PLAIN_ALTERNATIVES,
    MAX_HARD_WORD_SHARE,
    MIN_READING_EASE,
    MONTH_WORDS,
    OTHER_BANKS,
    REDACTED_NAME,
    UNTRUSTED_TEXT_MAX_CHARS,
    WORDS_COUNTED_AS_EASY,
)

NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)*")
SENTENCE_END = re.compile(r"(?<=[.?!])\s+(?=[A-Z0-9€$£\"'(])")
WORD_PATTERN = re.compile(r"[A-Za-zÀ-ɏ']+")
FIRST_PERSON_TITLE = re.compile(r"\b(i|i'll|i'm|i've|me|my)\b", re.IGNORECASE)
YOU_PATTERN = re.compile(r"\b(you|your|you're|you'll)\b", re.IGNORECASE)
MONTH_ALTERNATION = "|".join(sorted(MONTH_WORDS, key=len, reverse=True))
DATE_PATTERN = re.compile(rf"\b(\d{{1,2}})\s+({MONTH_ALTERNATION})\b|\b({MONTH_ALTERNATION})\s+(\d{{1,2}})\b", re.IGNORECASE)
MONTH_ONLY_PATTERN = re.compile(rf"\b({'|'.join(w for w in MONTH_WORDS if w not in ('may', 'mar', 'dec'))})\b", re.IGNORECASE)
SHOUTING = re.compile(r"\b[A-Z]{5,}\b")
MONEY_PATTERN = re.compile(r"(?P<sign>-|−|minus\s+)?(?P<symbol>[€$£])\s?(?P<number>\d[\d,]*(?:\.\d+)?)|(?P<sign2>-|−|minus\s+)?(?P<number2>\d[\d,]*(?:\.\d+)?)\s?(?P<code>EUR|PLN|USD|GBP|CHF|zł)\b")
DROP_CLAIM = re.compile(rf"\b{DROP_VERBS}\s+(?:down\s+)?(?:to\s+|at\s+|below\s+)?(?P<money>(?:-|−|minus\s+)?[€$£]\s?\d[\d,]*)", re.IGNORECASE)
RISE_CLAIM = re.compile(rf"\b{RISE_VERBS}\b[^.?!]{{0,40}}?\b(?:to|is|be)\s+(?P<money>(?:-|−|minus\s+)?[€$£]\s?\d[\d,]*)", re.IGNORECASE)


@dataclass
class CheckContext:
    """What a piece of text may refer to."""

    slots: Dict[str, str]
    currency: str
    own_names: Tuple[str, ...] = ()  # companies this card is about
    other_names: Tuple[str, ...] = ()  # companies that belong to other cards
    extra_forbidden: Tuple[str, ...] = ()
    extra_allowed_text: str = ""  # e.g. engine facts for a chat answer

    allowed_numbers: Set[str] = field(init=False)
    allowed_dates: Set[Tuple[str, str]] = field(init=False)
    allowed_months: Set[str] = field(init=False)

    def __post_init__(self):
        source = " ".join(self.slots.values()) + " " + self.extra_allowed_text
        self.allowed_numbers = numbers_in(source)
        self.allowed_dates = dates_in(source)
        self.allowed_months = {m.lower()[:3] for m in MONTH_ONLY_PATTERN.findall(source)} | {d[1] for d in self.allowed_dates}


# ---------------------------------------------------------------- small text helpers

def normalize_number(raw: str) -> str:
    text = raw.replace(",", "")
    if "." in text:
        text = text.rstrip("0").rstrip(".") if re.fullmatch(r"\d+\.\d+", text) else text.replace(".", "")
    return text.lstrip("0") or "0"


def numbers_in(text: str) -> Set[str]:
    return {normalize_number(raw) for raw in NUMBER_PATTERN.findall(text)}


def dates_in(text: str) -> Set[Tuple[str, str]]:
    found: Set[Tuple[str, str]] = set()
    for day_a, month_a, month_b, day_b in DATE_PATTERN.findall(text):
        day, month = (day_a, month_a) if day_a else (day_b, month_b)
        found.add((str(int(day)), month.lower()[:3]))
    return found


def sentences(text: str) -> List[str]:
    return [part for part in SENTENCE_END.split(text.strip()) if part]


def words(text: str) -> List[str]:
    return WORD_PATTERN.findall(text)


def contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z]){re.escape(phrase.lower())}(?![a-z])", text.lower()) is not None


NEGATIONS = ("no one", "nobody", "not", "n't", "no", "without", "never")


def negated(text: str, phrase: str) -> bool:
    """True when every occurrence of `phrase` follows a negation ("no one needs to agree")."""
    hits = [m.start() for m in re.finditer(rf"(?<![a-z]){re.escape(phrase.lower())}(?![a-z])", text.lower())]
    return bool(hits) and all(
        re.search(rf"\b({'|'.join(re.escape(n) for n in NEGATIONS)})\s+(\w+\s+){{0,2}}$", text.lower()[max(0, start - 30):start])
        for start in hits
    )


def strip_values(text: str, values: Iterable[str]) -> str:
    """Remove slot values that are names or phrases (not numbers or short words) so they are not judged as the model's wording."""
    names = (v for v in values if v and len(v) >= 4 and re.search(r"[A-Za-z]{3,}", v) and not re.fullmatch(r"[-−]?[€$£]?[\d,.\s%]+[A-Za-z]{0,3}", v))
    for value in sorted(names, key=len, reverse=True):
        text = re.sub(re.escape(value), " X ", text, flags=re.IGNORECASE)
    return text


def syllables(word: str) -> int:
    word = word.lower().strip("'")
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and not word.endswith(("le", "ee")) and count > 1:
        count -= 1
    return max(1, count)


def reading_ease(text: str) -> Decimal:
    """Flesch Reading Ease (English). 60-70 = plain English, 50 = fairly difficult."""
    parts = sentences(text) or [text]
    tokens = words(text)
    if not tokens:
        return Decimal("100")

    syllable_count = sum(syllables(token) for token in tokens)
    score = 206.835 - 1.015 * (len(tokens) / len(parts)) - 84.6 * (syllable_count / len(tokens))
    return Decimal(str(round(score, 1)))


def hard_word_share(text: str) -> Decimal:
    tokens = words(text)
    if not tokens:
        return Decimal("0")
    hard = sum(1 for token in tokens if syllables(token) > WORDS_COUNTED_AS_EASY)
    return Decimal(hard) / Decimal(len(tokens))


# ---------------------------------------------------------------- untrusted input

def sanitize_untrusted(text: Optional[str]) -> Tuple[str, bool]:
    """Clean a name or description from a statement or invoice before it goes into a prompt. Returns (text, flagged)."""
    if not text:
        return "", False

    cleaned = re.sub(r"[\x00-\x1f\x7f`{}<>\[\]|\\#*_~]", " ", text)
    cleaned = " ".join(cleaned.split())[:UNTRUSTED_TEXT_MAX_CHARS].strip()
    lowered = cleaned.lower()
    flagged = any(re.search(rf"\b{re.escape(marker)}\b", lowered) for marker in INJECTION_MARKERS) and len(cleaned.split()) > 3
    if flagged or not re.match(ALLOWED_SCRIPT_PATTERN, cleaned):
        return REDACTED_NAME, True

    return cleaned, False


# ---------------------------------------------------------------- checks shared by every text the model writes

def check_common(text: str, check: CheckContext, plain_language: bool) -> List[str]:
    problems: List[str] = []
    own_text = strip_values(text, [*check.slots.values(), *check.own_names])
    lowered = own_text.lower()

    if not text.strip():
        return ["is empty"]
    if not re.match(ALLOWED_SCRIPT_PATTERN, text):
        problems.append("uses letters from another alphabet; write in English only")
    for pattern in FORMAT_LEAK_PATTERNS:
        if re.search(pattern, own_text, re.IGNORECASE):
            problems.append("contains formatting, code, links or remarks about yourself; write plain sentences only")
            break
    if "!" in text:
        problems.append("uses an exclamation mark")
    if re.search(IBAN_PATTERN, text):
        problems.append("contains an account number")
    if SHOUTING.search(own_text):
        problems.append("uses words in capital letters")

    for phrase in FORBIDDEN_PHRASES:
        if contains_phrase(lowered, phrase):
            problems.append(f"uses the pushy or promising phrase '{phrase}'")
    for phrase in check.extra_forbidden:
        if contains_phrase(lowered, phrase) and not negated(lowered, phrase):
            problems.append(f"says '{phrase}', which is not true or not allowed for this card")
    for pattern in FORBIDDEN_ADVICE_PATTERNS:
        if re.search(pattern, lowered):
            problems.append("suggests skipping taxes, social security or salaries, or misleading someone")
    for bank in OTHER_BANKS:
        if contains_phrase(lowered, bank):
            problems.append(f"mentions another bank ('{bank}')")

    problems.extend(_check_facts(text, check))
    if plain_language:
        problems.extend(_check_jargon(lowered))

    return problems


def signed_amount(raw: str) -> Optional[Decimal]:
    match = MONEY_PATTERN.search(raw)
    if not match:
        return None
    number = match.group("number") or match.group("number2")
    sign = match.group("sign") or match.group("sign2")
    value = Decimal(number.replace(",", ""))
    return -value if sign else value


def amounts_in(text: str) -> List[Decimal]:
    return [amount for amount in (signed_amount(m.group(0)) for m in MONEY_PATTERN.finditer(text)) if amount is not None]


def _slot_amount(check: CheckContext, key: str) -> Optional[Decimal]:
    value = check.slots.get(key)
    return signed_amount(value) if value else None


def _check_signs(text: str, check: CheckContext) -> List[str]:
    allowed = {amount for value in check.slots.values() for amount in amounts_in(value)}
    allowed |= set(amounts_in(check.extra_allowed_text))
    problems = []
    for amount in amounts_in(text):
        if amount not in allowed and -amount in allowed:
            problems.append(f"drops or adds a minus sign: FACTS have {'-' if amount > 0 else ''}{abs(amount):,.0f}, not {amount:,.0f}")
    return problems


def _check_value_claims(text: str, check: CheckContext) -> List[str]:
    """'drops to X' must quote the low point; 'becomes X' must quote the balance with the card."""
    problems: List[str] = []
    drop = {a for a in (_slot_amount(check, key) for key in DROP_SLOTS) if a is not None}
    with_card = {a for a in (_slot_amount(check, key) for key in WITH_CARD_SLOTS) if a is not None}
    if not drop and not with_card:
        return problems

    for sentence in sentences(text):
        conditional = any(marker in sentence.lower() for marker in CONDITIONAL_MARKERS)
        for match in DROP_CLAIM.finditer(sentence):
            amount = signed_amount(match.group("money"))
            allowed = drop | (with_card if conditional else set())
            about_balance = re.search(r"\b(balance|cash|account|money in the bank)\b", sentence, re.IGNORECASE)
            if amount is not None and not about_balance and amount not in with_card | drop:
                continue  # an amount that is not a balance (e.g. a price) is checked by the number rules
            if amount is not None and allowed and amount not in allowed:
                problems.append(f"says the balance drops to {match.group('money')}, but the lowest balance is {check.slots.get(DROP_SLOTS[0])}")
        for match in RISE_CLAIM.finditer(sentence):
            amount = signed_amount(match.group("money"))
            if amount is not None and with_card and amount in drop and amount not in with_card:
                problems.append(f"says the balance becomes {match.group('money')}, but with this card it is {check.slots.get(WITH_CARD_SLOTS[0])}")
    return problems


def _check_facts(text: str, check: CheckContext) -> List[str]:
    problems: List[str] = [*_check_signs(text, check), *_check_value_claims(text, check)]

    invented = sorted(numbers_in(text) - check.allowed_numbers, key=len)
    if invented:
        problems.append(f"uses numbers that are not in FACTS: {', '.join(invented[:5])}")

    wrong_dates = sorted(dates_in(text) - check.allowed_dates)
    if wrong_dates:
        problems.append(f"uses dates that are not in FACTS: {', '.join(f'{d} {m}' for d, m in wrong_dates[:3])}")
    months = {m.lower()[:3] for m in MONTH_ONLY_PATTERN.findall(text)} - check.allowed_months
    if months:
        problems.append(f"mentions months that are not in FACTS: {', '.join(sorted(months))}")

    for code, tokens in CURRENCY_TOKENS.items():
        if code == check.currency:
            continue
        for token in tokens:
            hit = token in text if len(token) == 1 else contains_phrase(text, token)
            if hit:
                problems.append(f"uses another currency ('{token}'); amounts are in {check.currency}")
                break

    for name in check.other_names:
        if len(name) >= 4 and contains_phrase(text, name) and not any(contains_phrase(own, name) for own in check.own_names):
            problems.append(f"mentions {name}, which belongs to another card")

    return problems


def _check_jargon(lowered: str) -> List[str]:
    found = [term for term in JARGON_PLAIN_ALTERNATIVES if contains_phrase(lowered, term)]
    # Report the longest matches only ("accounts payable", not also "payable").
    found = [term for term in found if not any(term != other and term in other for other in found)]
    return [f"uses the finance word '{term}'; say '{JARGON_PLAIN_ALTERNATIVES[term]}' instead" for term in found]


# ---------------------------------------------------------------- one field

def check_field(name: str, text: str, check: CheckContext) -> List[str]:
    spec = FIELD_SPECS[name]
    plain = spec["plain_language"]
    problems = check_common(text, check, plain)
    if not text.strip():
        return problems

    length = len(text)
    if length > spec["max_chars"]:
        problems.append(f"is {length} characters long; the limit is {spec['max_chars']}")
    if length < spec["min_chars"]:
        problems.append(f"is too short ({length} characters); write at least {spec['min_chars']}")

    parts = sentences(text)
    if len(parts) > spec["max_sentences"]:
        problems.append(f"has {len(parts)} sentences; the limit is {spec['max_sentences']}")
    if len(words(text)) > spec["max_words"]:
        problems.append(f"has more than {spec['max_words']} words")
    long_sentence = max((len(words(part)) for part in parts), default=0)
    if long_sentence > spec["max_sentence_words"]:
        problems.append(f"has a sentence of {long_sentence} words; keep sentences under {spec['max_sentence_words'] + 1} words")

    if name == FIELD_TITLE:
        problems.extend(_check_title(text, check))
    if plain:
        problems.extend(_check_readability(name, text, check))

    return problems


def _check_title(text: str, check: CheckContext) -> List[str]:
    problems: List[str] = []
    stripped = text.strip()
    if not stripped.endswith("?"):
        problems.append("must be one question ending with '?'")
    if stripped and not stripped[0].isupper():
        problems.append("must start with a capital letter")
    own_text = strip_values(stripped, check.slots.values())
    if FIRST_PERSON_TITLE.search(own_text):
        problems.append("must not use 'I', 'me' or 'my'")
    return problems


def _check_readability(name: str, text: str, check: CheckContext) -> List[str]:
    problems: List[str] = []
    own_text = strip_values(text, [*check.slots.values(), *check.own_names])

    if name == FIELD_EXPLANATION and not YOU_PATTERN.search(text):
        problems.append("must speak to the owner as 'you'")
    if name in (FIELD_PROPOSAL, FIELD_EXPLANATION, FIELD_RANK_REASON) and len(words(own_text)) >= 12:
        score = reading_ease(own_text)
        if score < MIN_READING_EASE:
            problems.append(f"is hard to read (reading ease {score}, needs {MIN_READING_EASE}); use shorter words and sentences")
        share = hard_word_share(own_text)
        if share > MAX_HARD_WORD_SHARE:
            problems.append("uses too many long words; prefer short everyday words")

    return problems


# ---------------------------------------------------------------- a whole card

def check_card(
    copy: Dict[str, str],
    check: CheckContext,
    must_mention: Sequence[str] = (),
    title_must_mention: Sequence[str] = (),
    required_phrases: Sequence[Sequence[str]] = (),
) -> Dict[str, List[str]]:
    """Violations per field; card-level rules are attached to the field that should carry them."""
    problems = {name: check_field(name, copy.get(name, ""), check) for name in COPY_FIELDS}

    whole = " ".join(copy.get(name, "") for name in COPY_FIELDS)
    for key in must_mention:
        value = check.slots.get(key)
        if value and not contains_phrase(whole, value):
            problems[FIELD_EXPLANATION].append(f"must show '{value}' ({key}) on the card")

    title = copy.get(FIELD_TITLE, "")
    for key in title_must_mention:
        value = check.slots.get(key)
        if value and not contains_phrase(title, value):
            problems[FIELD_TITLE].append(f"must name '{value}'")

    body = " ".join(copy.get(name, "") for name in (FIELD_PROPOSAL, FIELD_EXPLANATION))
    for group in required_phrases:
        if not any(contains_phrase(body, phrase) for phrase in group):
            problems[FIELD_EXPLANATION].append(f"must say plainly that {_describe_group(group)}")

    return problems


def _describe_group(group: Sequence[str]) -> str:
    return f"(one of: '{group[0]}', '{group[1]}', ...)" if len(group) > 1 else f"'{group[0]}'"


# ---------------------------------------------------------------- ranking and chat answers

def check_rank_reason(reason: str, check: CheckContext) -> List[str]:
    return check_field(FIELD_RANK_REASON, reason, check)


def check_ranking(ids: Sequence[str], expected: Sequence[str]) -> List[str]:
    problems: List[str] = []
    if sorted(ids) != sorted(expected):
        missing = set(expected) - set(ids)
        unknown = set(ids) - set(expected)
        duplicates = {item for item in ids if ids.count(item) > 1}
        if missing:
            problems.append(f"leaves out {', '.join(sorted(missing))}")
        if unknown:
            problems.append(f"uses unknown ids {', '.join(sorted(unknown))}")
        if duplicates:
            problems.append(f"lists {', '.join(sorted(duplicates))} more than once")
    return problems


def enforce_tiers(order: Sequence[str], tiers: Dict[str, int]) -> List[str]:
    """Keep the model's order inside each tier, but never let a higher tier come first (stable sort)."""
    position = {item: index for index, item in enumerate(order)}
    return sorted(order, key=lambda item: (tiers.get(item, 99), position[item]))


def check_answer(answer: str, check: CheckContext) -> List[str]:
    problems = check_common(answer, check, plain_language=True)
    if len(answer) > EXPLAIN_ANSWER_MAX_CHARS:
        problems.append(f"is {len(answer)} characters long; the limit is {EXPLAIN_ANSWER_MAX_CHARS}")
    if len(sentences(answer)) > EXPLAIN_ANSWER_MAX_SENTENCES:
        problems.append(f"has more than {EXPLAIN_ANSWER_MAX_SENTENCES} sentences")
    return problems
