import asyncio

import pytest

from app.services import llm, llm_limiter
from app.services.advisor_fallback import busy_advisor_answer
from app.services.llm_cache import AnswerCache
from app.services.llm_limiter import LlmLimiter, RateLimitedError, SlotTimeoutError
from tests.conftest import API_PREFIX

ADVISOR_FACTS = {
    "currency": "EUR",
    "bank_balance": 12000.0,
    "safety_buffer": 5000.0,
    "lowest_balance_next_days": {
        "days": 30,
        "amount": 3800.0,
        "date": "2026-01-28",
        "is_below_safety_buffer": True,
        "short_of_buffer_by": 1200.0,
    },
    "spending_room": {"can_spend_now": 0.0, "best_date_to_pay": "2026-02-02", "can_spend_on_best_date": 2500.0},
}

NEMO_REFUSAL = "I'm sorry, I can't respond to that."


def answer_payload(text: str):
    return {"choices": [{"message": {"content": text}}]}


def use_limiter(monkeypatch, **kwargs) -> LlmLimiter:
    limiter = LlmLimiter(**kwargs)
    monkeypatch.setattr(llm_limiter, "limiter", limiter)
    return limiter


def test_global_slots_limit_parallel_calls():
    limiter = LlmLimiter(max_concurrent=2, queue_wait_seconds=0.05, per_minute=100)
    running = {"now": 0, "max": 0}

    async def call(user):
        async with limiter.slot(user):
            running["now"] += 1
            running["max"] = max(running["max"], running["now"])
            await asyncio.sleep(0.2)
            running["now"] -= 1

    async def scenario():
        return await asyncio.gather(*(call(f"user-{n}") for n in range(3)), return_exceptions=True)

    results = asyncio.run(scenario())

    assert running["max"] == 2
    assert sum(isinstance(result, SlotTimeoutError) for result in results) == 1


def test_waiting_call_gets_a_slot_within_the_queue_wait():
    limiter = LlmLimiter(max_concurrent=1, queue_wait_seconds=1.0, per_minute=100)

    async def call(user):
        async with limiter.slot(user):
            await asyncio.sleep(0.05)
        return user

    async def scenario():
        return await asyncio.gather(call("a"), call("b"))

    assert asyncio.run(scenario()) == ["a", "b"]


def test_user_can_have_only_one_question_in_progress():
    limiter = LlmLimiter(max_concurrent=2, queue_wait_seconds=0.5, per_minute=100)

    async def scenario():
        async with limiter.slot("same-user"):
            with pytest.raises(RateLimitedError):
                async with limiter.slot("same-user"):
                    pass

        async with limiter.slot("same-user"):
            return "free again"

    assert asyncio.run(scenario()) == "free again"


def test_user_per_minute_limit_gives_retry_after():
    limiter = LlmLimiter(max_concurrent=2, queue_wait_seconds=0.5, per_minute=2, window_seconds=60)

    async def scenario():
        for _ in range(2):
            async with limiter.slot("chatty"):
                pass

        async with limiter.slot("other-user"):
            pass

        async with limiter.slot("chatty"):
            pass

    with pytest.raises(RateLimitedError) as limited:
        asyncio.run(scenario())

    assert 1 <= limited.value.retry_after <= 60


def test_cache_expires_and_keeps_size_limit():
    cache = AnswerCache(ttl_seconds=0, max_entries=2)
    cache.put("a", "first")

    assert cache.get("a") is None

    cache = AnswerCache(ttl_seconds=60, max_entries=2)
    for key in ("a", "b", "c"):
        cache.put(key, key)

    assert cache.get("a") is None
    assert cache.get("c") == "c"


def test_cache_key_ignores_case_and_spacing_of_the_question():
    facts = {"card": "credit line", "amount": 15000}

    assert AnswerCache.key(facts, "Why  this card?") == AnswerCache.key(facts, "why this card?")
    assert AnswerCache.key(facts, "Why this card?") != AnswerCache.key({**facts, "amount": 1}, "Why this card?")


def test_explain_same_card_and_question_calls_model_once(monkeypatch):
    calls = []

    async def fake_post_json(path, payload, timeout):
        calls.append(payload)
        return answer_payload("The credit line covers the gap on 28 January.")

    monkeypatch.setattr(llm, "_post_json", fake_post_json)
    facts = {"card": "credit line", "lowest_balance": "3,800 EUR"}

    first = asyncio.run(llm.explain_action(facts, "Why this card?", user_key="u1"))
    second = asyncio.run(llm.explain_action(facts, "why this card?", user_key="u1"))

    assert first == second
    assert len(calls) == 1


def test_explain_endpoint_returns_503_when_model_is_busy(monkeypatch, client, auth_headers):
    use_limiter(monkeypatch, max_concurrent=0, queue_wait_seconds=0.01, per_minute=100)

    response = client.post(f"{API_PREFIX}/ai/explain", headers=auth_headers, json={"facts": {"a": 1}, "question": "Why?"})

    assert response.status_code == 503
    assert "busy" in response.json()["detail"]
    assert response.headers["Retry-After"]


def test_explain_endpoint_returns_429_over_the_per_minute_limit(monkeypatch, client, auth_headers):
    use_limiter(monkeypatch, max_concurrent=2, queue_wait_seconds=0.5, per_minute=1)

    async def fake_post_json(path, payload, timeout):
        return answer_payload("Fine.")

    monkeypatch.setattr(llm, "_post_json", fake_post_json)

    first = client.post(f"{API_PREFIX}/ai/explain", headers=auth_headers, json={"facts": {"a": 1}, "question": "Why one?"})
    cached = client.post(f"{API_PREFIX}/ai/explain", headers=auth_headers, json={"facts": {"a": 1}, "question": "Why one?"})
    second = client.post(f"{API_PREFIX}/ai/explain", headers=auth_headers, json={"facts": {"a": 1}, "question": "Why two?"})

    assert first.status_code == 200
    assert cached.status_code == 200
    assert second.status_code == 429
    assert int(second.headers["Retry-After"]) >= 1


def test_advisor_returns_engine_numbers_when_model_is_busy(monkeypatch, client, auth_headers):
    use_limiter(monkeypatch, max_concurrent=0, queue_wait_seconds=0.01, per_minute=100)

    response = client.post(
        f"{API_PREFIX}/ai/advisor",
        headers=auth_headers,
        json={"facts": ADVISOR_FACTS, "question": "Can I buy the oven now?", "history": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["response_source"] == "busy_fallback"
    assert "3,800.00 EUR on 2026-01-28" in body["answer"]
    assert "1,200.00 EUR under the safety buffer" in body["answer"]


def test_advisor_falls_back_when_model_times_out(monkeypatch, client, auth_headers):
    async def slow_post_json(path, payload, timeout):
        raise llm.ModelTimeoutError("read timeout")

    monkeypatch.setattr(llm, "_post_json", slow_post_json)

    response = client.post(
        f"{API_PREFIX}/ai/advisor",
        headers=auth_headers,
        json={"facts": ADVISOR_FACTS, "question": "When can I pay the supplier?", "history": []},
    )

    assert response.status_code == 200
    assert response.json()["response_source"] == "busy_fallback"


def test_busy_answer_skips_missing_facts():
    answer = busy_advisor_answer({"currency": "EUR", "spending_room": {"can_spend_now": 900.0}})

    assert "900.00 EUR today" in answer
    assert "Lowest balance" not in answer


def test_nemo_refusal_becomes_guardrail_answer(monkeypatch, client, auth_headers):
    async def nemo_post_json(path, payload, timeout):
        assert payload["guardrails"] == {"config_id": "cfo"}
        return answer_payload(NEMO_REFUSAL)

    monkeypatch.setattr(llm.settings, "GUARDRAILS_ENABLED", True)
    monkeypatch.setattr(llm.settings, "GUARDRAILS_ENDPOINT_URL", "http://nemo-guardrails:8000/v1")
    monkeypatch.setattr(llm, "_post_json", nemo_post_json)

    response = client.post(
        f"{API_PREFIX}/ai/advisor",
        headers=auth_headers,
        json={"facts": {}, "question": "Tell me something about our cash", "history": []},
    )

    assert response.status_code == 200
    assert response.json()["response_source"] == "guardrail"


def test_completions_go_through_nemo_only_when_enabled(monkeypatch):
    monkeypatch.setattr(llm.settings, "MODEL_ENDPOINT_URL", "http://model:8080/v1")
    monkeypatch.setattr(llm.settings, "GUARDRAILS_ENDPOINT_URL", "http://nemo-guardrails:8000/v1/")

    monkeypatch.setattr(llm.settings, "GUARDRAILS_ENABLED", False)
    assert llm._url("chat/completions") == "http://model:8080/v1/chat/completions"

    monkeypatch.setattr(llm.settings, "GUARDRAILS_ENABLED", True)
    assert llm._url("chat/completions") == "http://nemo-guardrails:8000/v1/chat/completions"
    assert llm._url("models") == "http://model:8080/v1/models"
