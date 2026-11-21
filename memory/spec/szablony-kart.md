# Card templates

As of 2026-11-21, branch `jan-szablony-kart` (on top of `test-calosci`). Developers pre-define decision scenarios ("card templates"); the engine finds where each one applies and calculates its effect; qwen3-8b writes the card text from those numbers and ranks the cards; guardrails check everything the model writes. Same rule as the rest of the app: **the engine calculates, the AI only picks words and order**.

## Where it lives

| **Part** | **Path** |
| --- | --- |
| Template contract, registry, the 7 templates (pure, no DB/LLM) | `backend/app/services/card_templates.py` |
| Field limits, guardrail word lists, demo bank products, prompts | `backend/app/const/card_templates.py` |
| Guardrail checks (pure) | `backend/app/services/card_guardrails.py` |
| AI step: write, repair, fallback, rank, chat answers | `backend/app/services/card_writer.py` |
| Flow, storage, deck, "Ask why" | `backend/app/managers/card_manager.py` |
| Planned purchases in the forecast (stopgap) | `backend/app/managers/forecast_manager.py` (`planned_expenses`) |
| Preview on demo data without DB/model, check model answers | `backend/scripts/preview_cards.py` |
| Tests (31 pure + API) and real qwen3-8b answers | `backend/tests/test_card_*.py`, `tests/fixtures/qwen3_8b_card_answers.json` |

## Flow (`POST /api/v1/cards/generate`, also run by the seed)

1. **Context:** forecast context + approved decisions + planned purchases → baseline forecast, open invoices, late payers, payment counts.
2. **Goals:** gap below the minimum → `close_liquidity_gap`; always `save_money`; no gap and spare cash → `use_free_cash`.
3. **Detect:** every template of the active goals returns candidates (deterministic).
4. **Simulate:** each candidate's cash changes go through `simulate()`; effect slots are added (`lowest_balance_with_card`, `minimum_kept_with_card`, `balance_gain`).
5. **Filter:** drop candidates that create a gap that was not there, or (gap templates) do not lift the lowest balance.
6. **Score + tier (deterministic):** effect on the gap × certainty × (1 − relationship risk) − cost share + bonus if it closes the gap. Tier 0 = free own action that closes the gap, tier 2 = paid bank product, else tier 1.
7. **Shortlist:** at most `max_cards` per template (credit: only the cheapest product).
8. **Write:** one model call per card (3 in parallel), JSON output → guardrails → one repair round with the violations → fields still failing come from the fallback text; if the mix still fails, the whole card is fallback.
9. **Rank:** one model call with all cards (ids A, B, C…, engine numbers, traits) → order + one reason each → the order is kept only inside tiers; invalid answer → engine score order; a reason that fails the guardrails → fixed reason.
10. **Store:** `AgentAction` (title, proposal = `trigger_reason`, explanation) + `impact_simulation.template` (key, version, slots, rank, reason, tier, copy source, the model's violations for audit). No migration: stored in the JSON column. Cards the agents no longer propose get `stale` and leave the deck.
11. **Serve:** `GET /api/v1/cards` → ranked cards, top 6 + every card that closes the gap on its own; new fields `rank`, `rankReason`, `template`, `copySource`.
12. **Ask why:** the frontend's default "Why do you recommend…" question is answered from the stored, already checked explanation (no model call); other questions go to the model with the chat guardrails.

## What the model writes

| **Field** | **Where on the card** | **Max chars** | **Max sentences / words** | **Style** |
| --- | --- | --- | --- | --- |
| `title` | Headline | 70 | 1 / 12 | Professional, precise, one question ending with "?", no "I" |
| `proposal` | Under the headline | 180 | 2 / 32 (22 per sentence) | Plain: what happens on "yes" (amount, date, who) |
| `explanation` | Back, "Why I suggest this" | 420 | 4 / 75 (22 per sentence) | Plain, for a non-expert: why, what changes, cost or risk; speaks to "you" |
| `rank_reason` | Ranking, "why this order" | 120 | 1 / 22 | Plain, one sentence |

Fixed per template (never written by the model): button labels, autonomy label, hold-to-confirm threshold, bank-product note, "Ask why" question chips, mail draft. Limits live in `FIELD_SPECS` (`const/card_templates.py`) and match the card UI (title at 24–30 px in 420 px, proposal box 440 px).

## Guardrails

Checked on every field (`card_guardrails.py`); violations go back to the model once, then the fallback text is used.

- **Facts:** every number must appear in the card's slots; dates (day + month) and month names must match a slot; amounts keep their sign (no "€4,681" for "-€4,681"); "drops/falls to X" must quote the low point (or, in an "if…" sentence, the balance with the card); "becomes/rises to X" must quote the balance with the card; no other currency; no company that belongs to another card; no other bank.
- **No overclaiming:** when the engine says the minimum still breaks with this card, phrases like "keeps you above", "closes the gap", "solves" are refused, and the prompt says so explicitly.
- **Who decides:** own-action cards must not say someone else has to agree (negations like "no one needs to agree" are fine); cards that need the other side must say so ("has to agree", "still has to pay"); credit must say the bank decides and show the total cost; a deposit must say the money is locked.
- **Clarity:** length, sentence and word limits per field; plain-language fields need a reading-ease score ≥ 50 (Flesch, slot names excluded), at most 20% long words, no finance jargon (37 terms with plain alternatives in the prompt, e.g. liquidity → cash you can use; the title may be more technical); the explanation must speak to "you"; titles are one calm question without "I".
- **Tone:** no pressure, hype or promises ("guaranteed", "risk-free", "no risk", "urgent", "act now", "you must", "will be approved"…), no exclamation marks, no shouting.
- **Safety:** never suggest skipping or delaying taxes, VAT, social security, health insurance or salaries; never suggest misleading anyone; no threats in collection cards (lawyer, court, debt collector); protected payments (tax, ZUS/health fund, salaries, insurance, loans, energy) are never offered for cancellation or extension in `detect`.
- **Format and privacy:** plain text only (no markdown, code, links, e-mail), Latin letters only (catches qwen switching to Chinese), no IBAN, no remarks about being an AI.
- **Injection:** names from statements and invoices are cleaned (control characters, brackets, length 60); a name that looks like an instruction is replaced by "this company"; the prompts say data in FACTS is not a command.
- **Ranking:** every id exactly once; tiers cannot be broken (free own fixes first, paid bank products last); reasons pass the same checks.
- **Chat answers ("Ask why" questions):** numbers only from the facts sent or the question, same tone/format/safety rules, max 700 chars and 6 sentences; failing twice → the deterministic answer.

## Templates

| **Key** | **Goals** | **Who decides** | **Autonomy** | **Must show** | **Required statement** |
| --- | --- | --- | --- | --- | --- |
| `cancel_subscription` | gap, save money | owner | Requires approval | service, amount, saving per year | – |
| `collect_overdue` | gap | customer | Email needs your OK | customer, amount | they have to pay / agree |
| `delay_planned_investment` | gap | owner | Requires approval | item, amount, new date | – |
| `negotiate_extension` | gap | supplier / landlord | Email needs your OK | counterparty, amount, new date | they have to agree |
| `take_credit` | gap | bank | Requires approval, always hold | amount, total cost | the bank decides |
| `early_payment_discount` | save money | owner | Requires approval | supplier, discount, pay-by date | – |
| `term_deposit` | use free cash | bank | Requires approval, always hold | amount, term, interest | money is locked |

On the Pizzeria Amalfi demo (as of 31 Dec 2025, gap: −€4,681 on 28 Jan, minimum €5,000) all templates except the deposit fire; demo data now includes two subscriptions and a planned €8,500 oven (`demo_scenario.ensure_demo_extras`).

### Data each template takes from the math engine

| **Template** | **From the engine / DB (available)** | **Missing (see gap report)** |
| --- | --- | --- |
| `cancel_subscription` | `Forecast.recurring`, `recurring_dates()`, `simulate()` | subscription category, notice period, usage |
| `collect_overdue` | open sales invoices, `late_payers`, `simulate()` | overdue invoices in the forecast, reminder history, payment probability |
| `delay_planned_investment` | lowest balance + date, first day below minimum, worst case, `simulate()` | planned purchases (stopgap), cost of delaying |
| `negotiate_extension` | same gap data, open supplier invoices, recurring rent dates, payment counts | punctuality per supplier |
| `take_credit` | same gap data, recovery day from base scenario days | product conditions, interest on used amount only, existing overdraft limit |
| `early_payment_discount` | invoices with early-payment terms, `simulate()` | – |
| `term_deposit` | worst-case lowest balance | deposit rates, tax reserve |

The list is generated from the code: `engine_gap_report()` in `card_templates.py` (each `EngineInput` with `available=False`).

## Adding a template (checklist)

1. Write `detect_<name>(context) -> List[Candidate]` in `card_templates.py`: pure, reads only `TemplateContext`, returns cash changes and **formatted** slots (use `context.m()`, `day_month()`, `percent()`); never offer protected payments.
2. Register a `CardTemplate`: key, version, goals, agent, name, brief (what the model needs to know), `engine_inputs` (mark missing data `available=False` with the reason), traits, guardrails (`must_mention`, `title_must_mention`, `required_phrases`, `extra_forbidden`, hold threshold, `bank_product`), labels, questions, fallback text with `{slot}`s, optional mail, `max_cards`.
3. Constants and words go to `const/card_templates.py`.
4. Run `python scripts/preview_cards.py`: the fallback text must pass its own guardrails ("fallback guardrail problems: none").
5. Add a test in `tests/test_card_templates.py`. Nothing else changes: the coordinator, the AI step and the frontend pick it up.
6. Changing a template's meaning → bump `version` (it is part of the dedupe key).

## Model use and efficiency (qwen3-8b, 1× L4, shared)

- Generation runs only on `POST /cards/generate` (and the seed), never per page load; the default "why" for every card is served from the database (before: one model call per card on every app start).
- Measured on the cluster (2026-11-21): 7 cards in about 10 s with 3 parallel requests, ranking about 9 s; with one repair round the whole run is about 25–30 s, 13–15 calls.
- `response_format` with a JSON schema guarantees valid JSON. **Never put `maxLength` (or other length limits) into those schemas**: vLLM's guided decoding then builds huge grammars and stalled the shared model server for several minutes during testing. Lengths are checked by the guardrails.
- If the model fails once, the rest of the run uses fallbacks without calling it again (`ModelSession`).

## Live test against qwen3-8b (2026-11-21)

- First answers: 7/7 valid JSON, but 6/7 broke a rule. Real mistakes it made: lost minus sign (€4,681 for −€4,681), "drops to €9,319" (the balance *with* the credit), "falls to €5,000" (the minimum, not the low point), "the supplier must agree" on own actions, 3-sentence proposals, "no risk", "you must".
- After one repair round: 5/7 fully model-written, 2/7 with fallback fields; every final card passes all guardrails and every number matches the engine. The answers are in `tests/fixtures/qwen3_8b_card_answers.json` and replayed in `tests/test_card_writer.py`.
- Ranking (one call): oven delay → Fattoria extension → catering reminder → discount → subscriptions → credit; one reason ("no risk") replaced by the fixed reason.

## Engine gap report

What the math engine (and the data behind it) does not provide yet, by impact on the cards. Items 1–3 change what the owner sees today.

| # | **Gap** | **Effect on cards today** | **Suggested fix** |
| --- | --- | --- | --- |
| 1 | Overdue sales invoices are assumed paid on the first forecast day (`_schedule_flows`) | The forecast is too optimistic; collecting an overdue invoice shows €0 effect, so collection cards rank low | Expected date = today + the customer's typical delay (or a fixed 14 days) |
| 2 | No planned purchases / known future events in the DB | Delay cards only work through the stopgap `company.settings.planned_expenses` (demo oven) | Table `planned_expenses` + form or chat input; the engine already takes them as changes |
| 3 | Existing overdraft limit (`bank_accounts.overdraft_limit`) is ignored | A gap is shown even if an existing limit covers it; credit size ignores what is already granted | Add available credit to indicators ("cash + unused limit") and size new credit on top |
| 4 | Interest is charged on the full credit for the whole period | Credit cost is an upper bound (overdrafts charge only what is used) | Daily interest on the negative part of the simulated balance |
| 5 | Bank products and deposit rates are demo constants | Product names and rates are assumptions | Product catalogue from the bank (API or config per environment) |
| 6 | No subscription category from the statement parser | Subscriptions are found by name markers only (missed if the name is neutral) | Category rules / MCC codes in `statement_parser.auto_categorize` |
| 7 | No contract data (notice period, contract end) | Fixed 30 days notice assumed | Contract fields per recurring payment |
| 8 | Supplier punctuality is not computed (only payment counts) | "Reliable supplier" means "paid 6+ times", not "paid on time" | Match incoming invoices to payments, compute days late per supplier |
| 9 | No probability that a customer pays or a supplier agrees | Certainty is a fixed weight per template (0.6 / 0.85 / 1.0) | Learn from history: share of reminders that led to payment, extensions granted |
| 10 | No reminder history | Collection step is chosen from days overdue only | Store sent reminders (Mail page) per invoice |
| 11 | Confidence varies revenue only | Costs, late customers and refused extensions do not change the confidence | Add cost and counterparty variation to `confidence_grid` |
| 12 | No tax calendar / tax reserve | A deposit card may lock money needed for tax; no tax agent possible | Tax advance payments as recurring obligations + a reserve in "free cash" |
| 13 | Invoices in other currencies are skipped (`skipped_invoices`) | No FX cards possible; EUR forecast ignores foreign invoices | FX rates + converted amounts; an FX-exposure indicator |
| 14 | Price drift splits recurring streams (>10 %) | A supplier price increase can hide as a new stream; no "price went up" card | Track amount drift per counterparty |
| 15 | Cost of delaying a purchase is not modelled | The delay card says only the date changes | Optional cost or lost revenue per planned purchase |
| 16 | `as_of` = last booked transaction (sample data: 31 Dec 2025) | Card dates are in the past relative to the real date in the demo | Use today and roll the demo data forward, or show "as of" on the cards |

## Open questions

- Show a combined "plan" card ("move the oven + ask Fattoria = gap closed, no credit")? The engine can simulate combinations; the deck shows single actions today.
- Polish copy: the guardrails (readability score, jargon list, month names) are English-only; a PL version needs its own lists and score.
- Frontend: `rankReason` is available on every card but not shown yet.
