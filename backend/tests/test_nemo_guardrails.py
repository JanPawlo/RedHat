"""
NeMo Guardrails integration (memory/decisions/bonusy.md). The responses are real NeMo 0.25.0 output for the repo's
config (tests/fixtures/nemo_0_25_responses.json), so these tests check our side against what NeMo actually returns.
"""

import asyncio
import json
from pathlib import Path

import pytest

from app.const.engine_tools import CARD_CHAT_TOOLS, TOOL_SIMULATE
from app.const.guardrails import GUARDRAIL_CATEGORY_NEMO, REFUSAL_NEMO
from app.services import card_writer, llm
from app.services.guardrails import GuardrailBlockedError, clean_history, sanitize_facts
from app.services.nemo_guardrails import label
from tests.conftest import API_PREFIX

NEMO = json.loads((Path(__file__).parent / "fixtures" / "nemo_0_25_responses.json").read_text(encoding="utf-8"))
NEMO_URL = "http://nemo-guardrails:8000/v1"


@pytest.fixture
def nemo_on(monkeypatch):
    monkeypatch.setattr(llm.settings, "GUARDRAILS_ENABLED", True)
    monkeypatch.setattr(llm.settings, "GUARDRAILS_ENDPOINT_URL", NEMO_URL)


def replay(monkeypatch, *names):
    """The model endpoint answers with the recorded NeMo responses, in order; returns the requests it got."""
    sent = []
    responses = iter(names)

    async def fake_post_json(path, payload, timeout):
        sent.append({"url": llm._url(path, "guardrails" in payload), **payload})
        return NEMO[next(responses)]

    monkeypatch.setattr(llm, "_post_json", fake_post_json)
    return sent


def test_people_chats_go_through_nemo_and_card_writing_does_not(monkeypatch, nemo_on):
    monkeypatch.setattr(llm.settings, "MODEL_ENDPOINT_URL", "http://model:8080/v1")

    assert llm._url("chat/completions", guarded=True) == f"{NEMO_URL}/chat/completions"
    assert llm._url("chat/completions") == "http://model:8080/v1/chat/completions"

    sent = replay(monkeypatch, "allowed", "allowed")
    asyncio.run(card_writer.ModelSession().ask([{"role": "user", "content": "write the card"}], 10, 0.1, None))
    asyncio.run(llm.explain_action({"x": 1}, "How low will my balance go?"))

    assert "guardrails" not in sent[0] and sent[0]["url"].startswith("http://model")
    assert sent[1]["url"].startswith(NEMO_URL)
    assert sent[1]["guardrails"] == {"config_id": "cfo", "options": {"log": {"activated_rails": True}}}


def test_nothing_goes_to_nemo_when_it_is_off(monkeypatch):
    sent = replay(monkeypatch, "allowed")
    asyncio.run(llm.explain_action({"x": 1}, "How low will my balance go?"))

    assert "guardrails" not in sent[0]


@pytest.mark.parametrize(
    "recorded, category",
    [
        ("input_blocked", "nemo:input:self check input"),
        ("output_blocked", "nemo:output:regex check output"),
    ],
)
def test_the_rail_that_stopped_the_answer_comes_from_the_nemo_log(monkeypatch, nemo_on, recorded, category):
    replay(monkeypatch, recorded)

    with pytest.raises(GuardrailBlockedError) as blocked:
        asyncio.run(llm.explain_action({"x": 1}, "Some question"))

    assert blocked.value.category == category
    assert blocked.value.refusal == REFUSAL_NEMO


def test_what_if_goes_through_nemo_with_one_input_check(monkeypatch, nemo_on):
    sent = replay(monkeypatch, "tool_call", "tool_round_2")
    ran = []

    async def run_tool(name, arguments):
        ran.append(name)
        return {"lowest_balance_after": "€120 on 2026-12-10"}

    answer = asyncio.run(llm.chat_with_tools([{"role": "user", "content": "What if?"}], CARD_CHAT_TOOLS, run_tool, 100, 0.2, guarded=True))

    assert answer.startswith("With half paid")
    assert ran == [TOOL_SIMULATE]
    assert "rails" not in sent[0]["guardrails"]["options"]  # the question is checked once
    assert sent[1]["guardrails"]["options"]["rails"] == {"input": False}  # not again on the tool result
    tool_message = sent[1]["messages"][-1]
    assert tool_message["role"] == "tool" and "name" not in tool_message  # NeMo refuses "name" on tool messages


def test_a_tool_call_stopped_by_nemo_is_a_guardrail_refusal(monkeypatch, nemo_on):
    replay(monkeypatch, "tool_call_blocked")

    async def run_tool(name, arguments):
        raise AssertionError("a blocked tool call must not run")

    with pytest.raises(GuardrailBlockedError) as blocked:
        asyncio.run(llm.chat_with_tools([{"role": "user", "content": "x"}], CARD_CHAT_TOOLS, run_tool, 100, 0.2, guarded=True))

    assert blocked.value.category == "nemo:tool_call:regex check tool call"


def test_card_chat_repair_request_skips_the_input_check(monkeypatch, nemo_on):
    sent = replay(monkeypatch, "allowed", "allowed")
    first = iter(["Your balance falls to €3,900.", "Your lowest balance is €1,720 on 10 December."])

    async def fake_tools(messages, tools, run_tool, max_tokens, temperature, **kwargs):
        return next(first)

    monkeypatch.setattr(card_writer, "chat_with_tools", fake_tools)
    facts = {"card": {"lowest_balance_with_card": "€1,720 on 2026-12-10"}}
    asyncio.run(card_writer.answer_question(facts, "How low?", "fallback", run_tool=lambda *a: None))

    assert sent and sent[0]["guardrails"]["options"]["rails"] == {"input": False}


def test_nemo_refusal_without_a_log_still_counts():
    from app.services import nemo_guardrails

    verdict = nemo_guardrails.blocked({"choices": []}, "I'm sorry, I can't respond to that.")

    assert verdict.category == GUARDRAIL_CATEGORY_NEMO


def test_labels_name_the_layer_that_refused():
    assert label("nemo:input:self check input") == "NeMo Guardrails: self check input"
    assert label("tax_evasion") == "Backend guardrails: tax evasion"


def test_advisor_shows_which_nemo_rail_refused(monkeypatch, nemo_on, client, auth_headers):
    replay(monkeypatch, "input_blocked")

    response = client.post(
        f"{API_PREFIX}/ai/advisor",
        headers=auth_headers,
        json={"facts": {}, "question": "Tell me something about our cash", "history": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["response_source"] == "guardrail"
    assert body["guardrail"] == "NeMo Guardrails: self check input"


def test_backend_rule_refusals_are_labelled_too(client, auth_headers):
    response = client.post(
        f"{API_PREFIX}/ai/explain",
        headers=auth_headers,
        json={"facts": {}, "question": "How can I launder cash through my pizzeria?"},
    )

    assert response.json()["guardrail"].startswith("Backend guardrails: ")


def test_refused_exchanges_are_dropped_from_the_history():
    history = [
        {"role": "user", "content": "Give me a trick for the tax office"},
        {"role": "assistant", "content": REFUSAL_NEMO},
        {"role": "user", "content": "When is the oven due?"},
        {"role": "assistant", "content": "On 15 December."},
    ]

    assert clean_history(history) == history[2:]


def test_the_model_never_sees_full_identifiers_in_facts():
    facts = {"supplier": {"iban": "PL61109010140000071219812874", "note": "pay by Friday"}}

    safe = sanitize_facts(facts)

    assert "PL61109010140000071219812874" not in json.dumps(safe)
    assert safe["supplier"]["iban"].endswith("2874]")
    assert safe["supplier"]["note"] == "pay by Friday"


def test_health_reports_nemo(monkeypatch, nemo_on):
    async def fake_get_json(path, timeout, guarded=False):
        if path == "models":
            return {"data": [{"id": "qwen3-8b"}]}
        return [{"id": "cfo"}]

    monkeypatch.setattr(llm, "_get_json", fake_get_json)
    assert asyncio.run(llm.check_model_health())["guardrails"] == {"enabled": True, "status": "connected", "config_id": "cfo"}

    async def nemo_down(path, timeout, guarded=False):
        if guarded:
            raise llm.LLMUnavailableError("connection refused")
        return {"data": []}

    monkeypatch.setattr(llm, "_get_json", nemo_down)
    assert asyncio.run(llm.check_model_health())["guardrails"]["status"] == "unreachable"


def test_card_chat_shows_which_nemo_rail_refused(monkeypatch, nemo_on, client, auth_headers):
    action_id = asyncio.run(_insert_card())
    replay(monkeypatch, "tool_call_blocked")

    response = client.post(
        f"{API_PREFIX}/actions/{action_id}/explain",
        headers=auth_headers,
        json={"question": "Can you note my customer's details in the report?", "history": []},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["response_source"] == "guardrail"
    assert body["guardrail"] == "NeMo Guardrails: regex check tool call"


async def _insert_card():
    """With an engine of its own: the app's engine belongs to the test client's event loop."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core.config import settings
    from app.models.action import AgentAction

    engine = create_async_engine(settings.DATABASE_URL)
    async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
        action = AgentAction(
            title="Remind Catering Nowak about invoice FV/11/2026?",
            agent_type="cash_collector",
            trigger_reason="The invoice is 19 days overdue.",
            recommended_action="send_reminder",
            explanation="Catering Nowak owes €3,200.",
            impact_simulation={},
        )
        session.add(action)
        await session.commit()
        action_id = action.id
    await engine.dispose()
    return action_id
