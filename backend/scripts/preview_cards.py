"""
Preview the card templates on the Pizzeria Amalfi demo data without a database or a model.

    python scripts/preview_cards.py                    # candidates, engine effect, ranking tiers, fallback cards
    python scripts/preview_cards.py --prompts out.json # also write the exact prompts the model would get
    python scripts/preview_cards.py --answers in.json  # check model answers ({key: raw answer}) with the guardrails

Useful when tuning a template, its slots or the guardrails: the fallback text is checked by the same guardrails
as model output, so a template whose own fallback fails is easy to spot.
"""

import argparse
import json
import os
import sys
import uuid
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.const.company import DEFAULT_MIN_SAFETY_BUFFER  # noqa: E402
from app.const.cards import CARD_HORIZON_DAYS  # noqa: E402
from app.managers.card_manager import _copy_request, _rank_item, evaluate, shortlist, situation  # noqa: E402
from app.models.account import BankAccount  # noqa: E402
from app.services import demo_scenario  # noqa: E402
from app.services.card_guardrails import check_card  # noqa: E402
from app.services.card_templates import (  # noqa: E402
    InvoiceView,
    LatePayerView,
    PlannedExpense,
    TemplateContext,
    active_goals,
    templates_for,
)
from app.services.card_writer import copy_messages, fallback_copy, parse_json, rank_messages  # noqa: E402
from app.services.forecast_engine import CashChange, CashRecord, ForecastInputs, OpenInvoice, build_forecast  # noqa: E402
from app.services.statement_parser import parse_bank_statement_csv  # noqa: E402

CSV = Path(__file__).resolve().parents[2] / "memory" / "reference" / "sample-data" / "pizzeria-amalfi-bank-statement-2025-v6.csv"
OPENING_BALANCE = Decimal("33266.35")


def demo_context() -> TemplateContext:
    rows = parse_bank_statement_csv(CSV.read_text(encoding="utf-8"))
    history = [CashRecord(r["booking_date"], r["amount_base_currency"], r["counterparty_name"] or "", r["category"] or "") for r in rows]
    as_of = max(record.booking_date for record in history)

    account = BankAccount(id=uuid.uuid4(), currency="EUR")
    for tx in demo_scenario._subscription_history(account, as_of):
        history.append(CashRecord(tx.booking_date, tx.amount_base_currency, tx.counterparty_name, tx.category))

    paid = [record for record in demo_scenario._paid_customer_history(account, as_of) if hasattr(record, "invoice_type")]
    delays = defaultdict(list)
    for invoice in paid:
        delays[invoice.counterparty_name].append((invoice.paid_transaction.booking_date - invoice.due_date).days)
    for invoice in paid:
        history.append(CashRecord(invoice.paid_transaction.booking_date, invoice.paid_transaction.amount, invoice.counterparty_name, "revenue_b2b"))

    views, open_invoices, late = [], [], []
    for invoice in demo_scenario._open_invoices(account, as_of):
        revenue = invoice.invoice_type == "outgoing_revenue"
        views.append(InvoiceView(invoice.invoice_number, invoice.counterparty_name, revenue, invoice.gross_amount, invoice.currency,
                                 invoice.issue_date, invoice.due_date, invoice.early_discount_percent, invoice.early_discount_days))
        delay = int(median(delays[invoice.counterparty_name])) if revenue and delays.get(invoice.counterparty_name) else 0
        due = invoice.due_date + timedelta(days=delay)
        if delay:
            late.append(LatePayerView(invoice.counterparty_name, invoice.invoice_number, invoice.gross_amount, invoice.due_date, due, delay, len(delays[invoice.counterparty_name])))
        open_invoices.append(OpenInvoice(invoice.invoice_number, invoice.counterparty_name, due, invoice.gross_amount * (1 if revenue else -1)))

    expense = demo_scenario.DEMO_PLANNED_EXPENSE
    planned_expense = PlannedExpense(expense["label"], Decimal(expense["amount"]), as_of + timedelta(days=expense["days_from_now"]), expense["movable"])
    planned = (CashChange(planned_expense.on_date, -planned_expense.amount, planned_expense.label),)

    inputs = ForecastInputs(as_of, OPENING_BALANCE, Decimal(str(DEFAULT_MIN_SAFETY_BUFFER)), CARD_HORIZON_DAYS, tuple(history), tuple(open_invoices))
    counts = defaultdict(int)
    for record in history:
        if record.amount < 0 and record.counterparty:
            counts[" ".join(record.counterparty.lower().split())] += 1

    return TemplateContext(
        inputs=inputs, planned=planned, baseline=build_forecast(inputs, planned), currency="EUR",
        owner_name="Vincenzo Amalfi", company_name="Pizzeria Amalfi", invoices=tuple(views), late_payers=tuple(late),
        payment_counts=dict(counts), planned_expenses=(planned_expense,),
    )


def run(prompts_path=None, answers_path=None):
    context = demo_context()
    goals = active_goals(context)
    print(f"as of {context.as_of} · goals {goals} · {situation(context)}")
    evaluated = [item for template in templates_for(goals) for candidate in template.detect(context) for item in [evaluate(context, template, candidate)] if item]
    kept = shortlist(evaluated)
    print(f"{len(evaluated)} candidates, {len(kept)} shortlisted\n")

    prompts, answers = {}, json.loads(Path(answers_path).read_text()) if answers_path else {}
    for item in kept:
        request = _copy_request(item, kept, context)
        copy = fallback_copy(request)
        problems = {k: v for k, v in check_card(copy, request.check, item.template.guardrails.must_mention, item.template.guardrails.title_must_mention, item.template.guardrails.required_phrases).items() if v}
        print(f"[{item.template.key}] tier {item.tier} score {item.score:.3f} gain {item.improvement} closes gap {item.closes_gap} cost {item.candidate.cost}")
        for name, text in copy.items():
            print(f"  {name} ({len(text)}): {text}")
        print(f"  fallback guardrail problems: {problems or 'none'}")
        prompts[item.dedupe_key] = copy_messages(request)
        if item.dedupe_key in answers:
            data = parse_json(answers[item.dedupe_key]) or {}
            found = {k: v for k, v in check_card({k: str(data.get(k, '')) for k in copy}, request.check, item.template.guardrails.must_mention, item.template.guardrails.title_must_mention, item.template.guardrails.required_phrases).items() if v}
            print(f"  MODEL: {json.dumps(data, ensure_ascii=False)}\n  model problems: {found or 'none'}")
        print()

    items = [_rank_item(item, context) for item in kept]
    labels = {item.key: chr(ord("A") + index) for index, item in enumerate(items)}
    prompts["__rank__"] = rank_messages(items, situation(context), labels)
    prompts["__rank_labels__"] = labels
    if prompts_path:
        Path(prompts_path).write_text(json.dumps(prompts, ensure_ascii=False, indent=1))
        print(f"prompts written to {prompts_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts")
    parser.add_argument("--answers")
    arguments = parser.parse_args()
    run(arguments.prompts, arguments.answers)
