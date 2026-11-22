"""
Red-team check of both guardrail layers on tests/fixtures/guardrails_redteam.json.

    python scripts/redteam_guardrails.py --model http://localhost:8080/v1      # NeMo's judge prompt sent to the model
    python scripts/redteam_guardrails.py --nemo http://localhost:8001/v1       # through a running NeMo Guardrails

Layer 1 = the backend's keyword rules (services/guardrails.py). Layer 2 = NeMo's `self check input`: with --model the
judge prompt from deploy/nemo-guardrails/config/cfo/prompts.yml is rendered here and sent to the model (no NeMo
needed); with --nemo each question goes through NeMo and the activated-rails log says what stopped it.
Prints how many questions of each list were refused and which ones went the wrong way.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.const.llm import RAIL_ADVISOR  # noqa: E402
from app.services.guardrails import GuardrailBlockedError, check_request  # noqa: E402

REDTEAM = ROOT / "backend" / "tests" / "fixtures" / "guardrails_redteam.json"
PROMPTS = ROOT / "deploy" / "nemo-guardrails" / "config" / "cfo" / "prompts.yml"
LISTS = ("block", "allow", "block_holdout", "allow_holdout")


def keyword_layer(question: str) -> bool:
    try:
        check_request([question], RAIL_ADVISOR)
        return False
    except GuardrailBlockedError:
        return True


def judge_direct(client: httpx.Client, url: str, model: str, prompt: dict, user_input: str) -> bool:
    content = prompt["content"].replace("{{ user_input }}", user_input)
    body = {
        "model": model,
        "temperature": 0.001,
        "max_tokens": prompt.get("max_tokens", 5),
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [{"role": "user", "content": content}],
    }
    text = client.post(f"{url}/chat/completions", json=body).json()["choices"][0]["message"]["content"].lower()
    return "yes" in text or "unsafe" in text  # NeMo's is_content_safe: yes = refuse


def judge_nemo(client: httpx.Client, url: str, model: str, user_input: str) -> bool:
    body = {
        "model": model,
        "max_tokens": 60,
        "messages": [{"role": "system", "content": "You are a CFO assistant."}, {"role": "user", "content": user_input}],
        "guardrails": {"config_id": "cfo", "options": {"log": {"activated_rails": True}}},
    }
    data = client.post(f"{url}/chat/completions", json=body).json()
    rails = ((data.get("guardrails") or {}).get("log") or {}).get("activated_rails") or []
    return any(rail.get("stop") and rail.get("type") == "input" for rail in rails)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--model", help="OpenAI-compatible model base URL, e.g. http://localhost:8080/v1")
    target.add_argument("--nemo", help="NeMo Guardrails base URL, e.g. http://localhost:8001/v1")
    parser.add_argument("--model-name", default="qwen3-8b")
    args = parser.parse_args()

    data = json.loads(REDTEAM.read_text(encoding="utf-8"))
    prompt = yaml.safe_load(PROMPTS.read_text(encoding="utf-8"))["prompts"][0]
    facts = json.dumps(data["facts"], ensure_ascii=False)
    times = []

    with httpx.Client(timeout=60) as client:
        for name in LISTS:
            refused = {"keywords": [], "nemo": [], "either": []}
            for question in data.get(name, []):
                user_input = f"FACTS:\n{facts}\n\nQUESTION:\n{question}"
                started = time.perf_counter()
                nemo = (
                    judge_nemo(client, args.nemo, args.model_name, user_input)
                    if args.nemo
                    else judge_direct(client, args.model, args.model_name, prompt, user_input)
                )
                times.append(time.perf_counter() - started)
                keywords = keyword_layer(question)
                for layer, hit in (("keywords", keywords), ("nemo", nemo), ("either", keywords or nemo)):
                    refused[layer].append(hit)
                should_refuse = name.startswith("block")
                if (keywords or nemo) != should_refuse:
                    print(f"  WRONG [{name}] {'let through' if should_refuse else 'refused'}: {question}")
            total = len(refused["either"])
            print(f"{name:14} refused: keywords {sum(refused['keywords'])}/{total}, NeMo {sum(refused['nemo'])}/{total}, "
                  f"together {sum(refused['either'])}/{total}")

    print(f"NeMo check: {sum(times) / len(times):.2f} s on average, {max(times):.2f} s max")


if __name__ == "__main__":
    main()
