# Card templates

As of 2026-11-21. Proposal: developers pre-define decision scenarios ("card templates"); the engine finds where each one applies and calculates its effect; the AI writes the card text from those numbers and ranks the candidates. Builds on the card generation on branch `test-calosci` (`spec/silnik.md`, "Integration branch").

## Idea in one line

- **Template** (code, written by us) → **candidates** (engine finds every place it applies) → **effect** (engine simulates each one) → **AI** fills the text and ranks → **cards** (owner swipes).
- Same rule as the rest of the app: the engine calculates every number, the AI only picks words and order. The AI never invents an amount, date or rate; it can only use slot values.

## What a template is

One entry in a template registry. Fields:

| **Field** | **What it holds** | **Example (take credit)** |
| --- | --- | --- |
| `key`, `version` | Unique id; the version goes into the dedupe key | `take_credit`, `v1` |
| `goal` | Which problem it solves; the coordinator only asks templates of the current goal | `close_liquidity_gap` |
| `agent` | Agent shown on the card | `liquidity_guard` |
| `detect(context)` | Deterministic: returns 0..n candidates from the forecast context (one per subscription, invoice, product...) | one candidate per credit product |
| `cash_changes(candidate)` | Deterministic: the candidate's effect as engine changes (date, amount, label) | +amount on draw day, −interest after 30 days |
| `slots(candidate)` | Named values the AI may use in text: numbers already formatted, names, dates | `amount`, `draw_date`, `monthly_interest`, `product_name` |
| `traits` | Fixed facts used in ranking: `cost`, `certainty` (own action / needs the other side to agree), `relationship_risk`, `reversible`, `effort`, `days_to_effect` | certainty: needs bank approval; reversible: yes |
| `copy_brief` | Instructions for the AI: what the card must say, tone, what never to say | "Say it is a Commerzbank product; mention the cheaper alternatives if they close the gap" |
| `fallback_copy` | Fixed text with `{slot}` placeholders, used when the model is down or its answer fails validation | "Pre-activate a {amount} credit line before {breach_date}?" |
| `guardrails` | `requires_approval`, hold-to-confirm threshold, `never_when` conditions | never when the gap is already closed by free options |
| `follow_ups` | Mail draft template, calendar reminder | mail to the bank relationship manager |
| `questions` | Suggested "Ask why" questions for this template | "What does it cost in total?" |

## Templates for the goal "close a liquidity gap"

| **Key** | **Detect (deterministic)** | **Effect in the engine** | **Slots** | **Traits** | **Data we still miss** |
| --- | --- | --- | --- | --- | --- |
| `cancel_subscription` | Recurring outflows (engine `recurring`) that are not essential: not rent, salaries, tax, ZUS/health fund, energy, loans; list of essential categories in `const/` | Remove future occurrences after the notice period | name, monthly amount, saving in the horizon, saving per year, notice period | own action, low relationship risk, reversible, small effect | Category of a recurring payment (subscription/software vs essential); notice period (default constant) |
| `collect_overdue` | Open sales invoices past due, and customers who usually pay late (engine `late_payers`) | Expected inflow moves from "due + typical delay" to the new promised date | customer, invoice number, amount, days overdue, typical delay, KRZ status | needs the customer to act, medium relationship risk | Escalation step per invoice (reminder → reminder with discount → formal demand → payment plan); today only "late payer" exists |
| `delay_planned_investment` | Planned purchases (machine, renovation) dated inside or just before the gap | Outflow moves to the first date after the gap that keeps the buffer | item, amount, planned date, proposed date | own action, no relationship risk, reversible | Planned purchases are not in the DB: needs a "planned expenses / known events" table (also an open gap in `spec/silnik.md`) |
| `negotiate_extension` | Supplier invoices and recurring payments (rent) due in the gap window, counterparty paid on time ≥ N times; never tax or ZUS | Payment moves by N days | counterparty, amount, due date, new date, on-time payment count | needs the other side to agree, medium relationship risk | Landlord = recurring payment, not an invoice: extend today's `_defer_cards` to recurring payments |
| `take_credit` | Gap in the base or pessimistic scenario; one candidate per credit product (overdraft, revolving credit line, short-term loan) | +amount on draw day, interest (and fees) later, repayment | product name, amount, draw date, rate, monthly interest, total cost | needs bank approval, costs money, reversible | Product catalogue (name, rate, fee, min/max, term) in `const/`, marked as demo assumptions; today one fixed 8 % rate |

Existing generators on `test-calosci` map to templates: credit line → `take_credit`; defer invoice → `negotiate_extension`; late payer 2 % → `collect_overdue` (one escalation step); early discount and deposit → templates of other goals (`save_money`, `use_free_cash`).

## Flow with templates

1. **Trigger:** new transactions, new or paid invoices, a decision, or a daily run → recalculate the forecast. Today generation runs only in the seed or via `POST /cards/generate`.
2. **Goal:** the coordinator reads the forecast: buffer breached → goal `close_liquidity_gap`; free cash → `use_free_cash`; always → `save_money`.
3. **Detect:** every template of the goal returns its candidates.
4. **Simulate:** the engine previews every candidate (as `preview_result` does today): change of the lowest balance, gap closed yes/no, confidence before/after, cost.
5. **Filter (deterministic):** drop candidates that do not improve anything or break a guardrail.
6. **Pre-score (deterministic):** score from engine numbers + traits, e.g. gap closed per unit of cost, certainty, relationship risk. This is the ranking when the model is down.
7. **AI fill + rank:** one LLM call with the shortlist (slots, engine effect, traits, `copy_brief` of each). It returns JSON: per candidate the card title, proposal, back description, and a rank with a one-sentence reason. Optionally a "plan": the smallest set of cards that closes the gap.
8. **Validate:** every number in the AI text must be a slot value; only known candidate ids; required wording present (e.g. "bank product"). Failure → `fallback_copy` and the pre-score order.
9. **Store:** `AgentAction` with `template_key`, `template_version`, `slots`, AI text, rank, reason, `cash_changes` and the dedupe key (`<template>:<source>:<version>`).
10. **Serve:** `GET /cards` sorted by rank; "Ask why" gets the slots + engine facts as today; swipe → status → forecast "after decisions" → back to step 1.

## How to add a template (checklist)

1. Add the entry to the registry: key, version, goal, agent, traits, guardrails.
2. Write `detect` and `cash_changes` as pure functions over the forecast context (no DB, no LLM).
3. Define `slots`, `copy_brief`, `fallback_copy`, `questions`; texts and limits in `const/`.
4. Unit test with a small hand-made context: candidates found, cash changes exact, fallback text renders.
5. No change needed in the coordinator, the AI step or the frontend: the card format stays the `DecisionCard` format from `GET /cards`.

## Open questions

- Ranking: the AI orders the shortlist, but should a free and certain option (delay own purchase, cancel subscription) always be shown before credit? Proposal: deterministic rule "free own actions first when they close the gap", AI orders within.
- One card per candidate, or a combined "plan" card ("move rent + collect hotel invoice = gap closed, no credit needed")?
- Where the registry lives in the code (new folder `app/services/card_templates/` vs one file): agree with the team (AGENTS.md: no new folders without agreement).
