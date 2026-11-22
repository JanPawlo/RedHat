import asyncio
import json
from pathlib import Path

from app.const.card_templates import MODEL_CONCURRENCY, COPY_SOURCE_FALLBACK, COPY_SOURCE_MIXED, COPY_SOURCE_MODEL, RANK_SOURCE_FALLBACK, RANK_SOURCE_MODEL
from app.managers.card_manager import _copy_request, _rank_item, situation
from app.services import card_writer
from app.services.card_guardrails import check_card
from app.services.llm import LLMUnavailableError
from tests.card_demo import demo_shortlist

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "qwen3_8b_card_answers.json").read_text(encoding="utf-8"))


class ReplaySession(card_writer.ModelSession):
    """Answers with the recorded qwen3-8b output: first answer, then the answer to the repair round."""

    def __init__(self, key):
        super().__init__()
        self.key = key

    async def ask(self, messages, max_tokens, temperature, schema):
        self.calls += 1
        return FIXTURE["first"][self.key] if self.calls == 1 else FIXTURE["repair"].get(self.key)


def test_replayed_model_answers_end_as_valid_cards():
    context, items = demo_shortlist()
    sources = {}
    for item in items:
        request = _copy_request(item, items, context)
        session = ReplaySession(item.dedupe_key)
        copy = asyncio.run(card_writer.write_copy(session, request))
        sources[item.template.key, item.candidate.source_id] = copy.source

        guardrails = item.template.guardrails
        final = check_card(copy.fields, request.check, guardrails.must_mention, guardrails.title_must_mention, guardrails.required_phrases)
        assert not any(final.values()), (item.template.key, final)
        assert session.calls <= 2

    assert list(sources.values()).count(COPY_SOURCE_MODEL) >= 4
    assert COPY_SOURCE_MIXED in sources.values()


def test_model_down_gives_fallback_text(monkeypatch):
    calls = []

    async def down(*args, **kwargs):
        calls.append(1)
        await asyncio.sleep(0)
        raise LLMUnavailableError("connection refused")

    monkeypatch.setattr(card_writer, "chat", down)
    context, items = demo_shortlist()
    session = card_writer.ModelSession()
    copies = asyncio.run(card_writer.write_all(session, [_copy_request(item, items, context) for item in items]))

    assert all(copy.source == COPY_SOURCE_FALLBACK for copy in copies.values())
    assert not session.available
    assert len(calls) <= MODEL_CONCURRENCY  # requests already in flight; nothing new is sent after the first failure


class RankSession(card_writer.ModelSession):
    def __init__(self, answer):
        super().__init__()
        self.answer = answer

    async def ask(self, messages, max_tokens, temperature, schema):
        self.calls += 1
        return self.answer


def _rank_items():
    context, items = demo_shortlist()
    return context, [_rank_item(item, context) for item in items]


def test_model_ranking_is_kept_inside_tiers_and_bad_reasons_are_replaced():
    context, items = _rank_items()
    labels = [chr(ord("A") + index) for index in range(len(items))]
    credit_label = labels[next(i for i, item in enumerate(items) if item.key.startswith("tmpl:take_credit"))]
    order = [credit_label, *[label for label in labels if label != credit_label]]
    answer = json.dumps({"ranking": [{"id": label, "reason": "No cost, no risk at all." if label == labels[0] else "Free and simple."} for label in order]})

    ranking = asyncio.run(card_writer.rank(RankSession(answer), items, situation(context)))

    assert ranking.source == RANK_SOURCE_MODEL
    assert ranking.order[-1].startswith("tmpl:take_credit")  # paid bank product cannot jump the queue
    first_key = items[0].key
    assert ranking.reasons[first_key] == items[0].fallback_reason  # "no risk" is not allowed
    assert any("order changed" in note for note in ranking.violations)


def test_invalid_ranking_falls_back_to_engine_score():
    context, items = _rank_items()
    ranking = asyncio.run(card_writer.rank(RankSession('{"ranking": [{"id": "A", "reason": "x"}]}'), items, situation(context)))
    assert ranking.source == RANK_SOURCE_FALLBACK
    assert sorted(ranking.order) == sorted(item.key for item in items)


def test_chat_answer_with_invented_numbers_falls_back(monkeypatch):
    answers = iter(["Your balance falls to -€3,900 next week.", "It will be around €3,950."])

    async def fake_chat(messages, max_tokens, temperature, json_schema=None, timeout=60, **kwargs):
        return next(answers)

    monkeypatch.setattr(card_writer, "chat", fake_chat)
    facts = {"engine": {"lowest": "-€4,681 on 2026-01-28"}}
    answer, source = asyncio.run(card_writer.answer_question(facts, "How low will it go?", "fallback text"))
    assert (answer, source) == ("fallback text", "guardrail_fallback")


def test_chat_answer_raises_when_model_is_down(monkeypatch):
    async def down(*args, **kwargs):
        raise LLMUnavailableError("down")

    monkeypatch.setattr(card_writer, "chat", down)
    try:
        asyncio.run(card_writer.answer_question({}, "Why?", "fallback"))
    except LLMUnavailableError:
        return
    raise AssertionError("expected LLMUnavailableError")


def test_after_approval_says_what_the_app_and_the_owner_do():
    from app.services.card_templates import TEMPLATES_BY_KEY, after_approval

    delay = after_approval(TEMPLATES_BY_KEY["delay_planned_investment"], {"item": "new pizza oven", "new_date": "5 Feb"})
    assert "This card has no email draft." in delay["the_app_does"]
    assert "new pizza oven" in delay["you_do_yourself"] and "5 Feb" in delay["you_do_yourself"]

    extension = after_approval(TEMPLATES_BY_KEY["negotiate_extension"], {"counterparty": "Fattoria La Vino GmbH", "document": "invoice X", "amount": "€1", "due_date": "25 Jan", "new_date": "24 Feb"})
    assert any("schedule an email to Fattoria La Vino GmbH" in line for line in extension["the_app_does"])


def test_chat_fallback_answers_the_kind_of_question():
    from app.managers.card_manager import chat_fallback

    facts = {
        "card": {"explanation_on_the_card": "Card text."},
        "after_you_say_yes": {"the_app_does": ["Saves your decision."], "you_do_yourself": "Call the seller."},
    }
    assert "Call the seller." in chat_fallback(facts, "Do I have to do it myself?")
    assert "Card text." in chat_fallback(facts, "Why this card?")


def test_owner_tasks_may_say_you_must_but_reruns_are_refused(monkeypatch):
    earlier = "The app saves your decision. You must call the seller yourself."
    answers = iter([
        "The app saves your decision. You must call the seller yourself.",  # a rerun of the last answer
        "No email is drafted for this card. You must call the seller yourself.",
    ])

    async def fake_chat(messages, max_tokens, temperature, json_schema=None, timeout=60, **kwargs):
        return next(answers)

    monkeypatch.setattr(card_writer, "chat", fake_chat)
    history = [{"role": "user", "content": "What happens?"}, {"role": "assistant", "content": earlier}]
    answer, source = asyncio.run(card_writer.answer_question({}, "Do I do it myself?", "fallback", history=history))
    assert source == "model" and answer.startswith("No email is drafted")
