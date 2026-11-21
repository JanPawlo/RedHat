# Forecast engine

As of 2026-11-21, branch `feature/forecast-engine`. The deterministic "engine" from `spec/funkcjonalnosci.md` (F4): plain code calculates every number, the LLM only explains it.

## Where it lives

| **Part** | **Path** |
| --- | --- |
| Engine (pure functions, no DB) | `backend/app/services/forecast_engine.py` |
| Tunable constants | `backend/app/const/forecast.py` |
| Loading data from the DB | `backend/app/managers/forecast_manager.py` |
| API | `GET /api/v1/forecast`, `POST /api/v1/forecast/simulate` (`controllers/forecast.py`) |
| Tests | `backend/tests/test_forecast_engine.py` (unit, incl. Pizzeria CSV), `backend/tests/test_forecast_api.py` |

## How it calculates (v1)

- **Start point:** `as_of` = date of the account's last booked transaction (sample data is from 2025), opening balance = account balance.
- **Recurring payments:** transactions are grouped by counterparty, then split by amount (±10 %). A group with at least 3 payments at monthly (25–35 days) or quarterly (85–95 days) intervals is a recurring payment, placed on its usual day of the month. One counterparty can have several streams (Pizzeria: Tax Office monthly 880, quarterly 225 and 1150). A stream with no payment for longer than its interval + 10 days counts as ended.
- **Revenue:** average inflow per weekday over the last 56 days (non-recurring transactions only). With at least 300 days of history, a month factor adds seasonality (Pizzeria: June = 0 because of the shutdown).
- **Variable costs:** a share of revenue (non-recurring outflows ÷ inflows over the same 56 days).
- **Invoices:** unpaid `incoming_expense` (out) and `outgoing_revenue` (in) on their due date; overdue ones on the first forecast day; different currency than the account → left out and listed in `skipped_invoices`. A recurring payment is skipped when an open invoice from the same counterparty falls within 10 days of it (no double counting).
- **Scenarios:** revenue × factor. Spread = weekly revenue volatility, at least ±10 %, clamped to 0.5–1.5.
- **Confidence:** share of 11 revenue factors between pessimistic and optimistic in which the balance never drops below the buffer. This is the source for "86 % confident" on cards.
- **Indicators per scenario:** lowest balance and date, first day below buffer / below zero, days to buffer breach, runway in months (only when the balance falls), free cash = lowest balance − buffer.
- **Simulation:** `simulate` takes a list of changes (date, signed amount, label), e.g. credit line +25,000, invoice moved (two changes), known event ("closed in July" as negative revenue). Returns baseline, simulated and the change of the lowest balance.
- Every forecast day lists its top 5 drivers (revenue, variable costs, recurring payment, invoice, change), so each number has a source.

## Checked on Pizzeria Amalfi (2026-11-21)

- 11 recurring payments found correctly (rent, 4 salaries, health fund, energy, CHF tranche, 3 Tax Office streams).
- Backtest from 2025-05-15: 15 days ahead the forecast hits the real balance almost exactly (2,496 vs 2,491). The June shutdown is not predicted: less than a year of history means no seasonality. This is a job for known events entered by the owner (or the chat) as simulation changes.

## Known gaps / next steps

- [ ] Customer payment delay for sales invoices (spec F4: due date + typical delay of that customer).
- [ ] Known future events stored in the DB (now only as simulation changes per request).
- [ ] Amount drift in recurring payments (price increase > 10 % splits the stream).
- [ ] Variable costs are 0 when the lookback window has no revenue (e.g. forecast made during a shutdown).
- [ ] Frontend: chart from `GET /forecast` instead of `frontend/src/utils/forecast.js` mock points (branch `natalia-frontend`).
- [ ] Use the forecast in the invoice validator: liquidity check over the horizon instead of "balance today − invoice".
- [ ] Generated test data at larger scale (see below).

## Invoice validator: review items (2026-11-21)

The first six items below were addressed on `feature/math-engine-expansion`: exact vendor and invoice token matching; currency and direction-aware checks; forecast simulation for due-date cash impact; and discount recommendation gated by deadline and pessimistic liquidity. Validation-only calls no longer write unlinked cards. Saved invoices are stored before deterministic card generation, and generated cards are linked to that invoice.

Remaining invoice review items:

- Credit-note cash direction is ambiguous and is left out of liquidity simulation with an explicit flag.
- Sales invoice customer delay logic is in forecast context, but the validation report should expose a clear due-date-plus-typical-delay comparison.
- VAT message lists rates that may not match the configured constants; risk weights remain magic numbers.
- Duplicate checks still have a fixed limit of 100 candidate transactions before exact token matching; a dedicated indexed reference field would scale better.

## Test data plan

- Unit tests use small hand-made data with exact expected values.
- Larger scale: a seeded generator script (same CSV format as the bank statement, so it goes through the real parser) for the company profiles in `examples/firmy/target-group-profiles.md`: 2+ years of history, seasonality, late-paying customers, price drift, one-off shocks. Year 1 trains, year 2 checks the forecast error (backtest) and runs simulations at scale.

## Decisions change the forecast (2026-11-21)

- A decision card can carry cash changes in `impact_simulation.cash_changes`: `[{"day_offset": 19, "amount": "15000.00", "label": "..."}]`, days counted from the forecast start (`as_of`).
- Cards with status `approved`, `simulated` or `executed` are added to the forecast: `GET /forecast` keeps `scenarios` as "do nothing" and adds `after_decisions` (base scenario with the approved cards), `after_decisions_confidence` and `decisions_applied`. Undo (status back to `pending`) removes them.
- `GET /forecast/actions/{id}/preview` = forecast with the other approved cards vs. the same plus this card (effect before the swipe). `POST /forecast/simulate` also starts from the approved cards.
- Frontend dashboard (`frontend/src/pages/Dashboard.jsx`, `components/forecast/`, `hooks/useForecastDeck.js`): indicator tiles, chart with scenario band / "do nothing" / "after your decisions" / "if you approve this card", deck with the engine's effect (lowest balance, confidence, buffer) and "I'd swipe left/right" derived from it, decision list with Undo, keyboard ← →.
- Demo scenario (`backend/app/services/demo_scenario.py`, added by the seed also to an existing DB): 3 open invoices (2024 income tax €21,000 due Jan 20, Asimex €6,420 with 2% Skonto, Fattoria La Vino €4,760) create a gap below the buffer on Jan 28; 6 cards: credit line (fixes it), move the wine invoice, Asimex early payment, 1-month deposit (makes it worse), oven for cash (worse), oven leasing.
- Recurring payment is replaced by an invoice only when the amounts are similar (the yearly tax invoice no longer hides the monthly 880).

## Local testing without login

- `AUTH_DISABLED=true` in the root `.env` (passed by docker compose): requests without a token act as the admin account; the frontend skips the login screen automatically. The API refuses to start with it unless `APP_ENV=development`, and logs a warning on startup. Never set it on the cluster.

## Integration branch `test-calosci` (2026-11-21)

Natalia's latest frontend + forecast engine + card logic from `feature/card_backend` (ported, that branch is on the old single-router structure), login on.

- **Cards from the engine** (`backend/app/managers/card_manager.py`, `POST /api/v1/cards/generate`, run by the seed): liquidity gap → credit line sized to cover the pessimistic scenario; early-payment discount (card_backend rules: linked invoice, dedupe key, deadline checks); supplier invoice due in the gap week from a supplier paid ≥ 6 times → ask to move 30 days; customer who pays late → offer 2% for paying on time; free cash in the pessimistic scenario → deposit. Card text quotes the engine's numbers. Migration `006_action_sources` (source_type, source_id, dedupe_key) from card_backend's `003`.
- **`GET /api/v1/cards`** returns pending cards in the frontend `DecisionCard` format; confidence, recommendation (right/left), 8-week bars, facts on the back all come from the engine's preview of that card.
- **"Ask why" is separate from the card front**: `POST /actions/{id}/explain` sends the engine's facts (lowest balance with/without, the 11 revenue levels behind the confidence and which keep the buffer, biggest outflows near the lowest day, recurring payments, revenue model, late payers) to the LLM. Without the model it returns a deterministic answer from the same facts (`response_source = deterministic_fallback`, idea from card_backend).
- **Forecast extras**: `history` (reconstructed past balance, 60 days) and `late_payers` (typical delay per customer from paid sales invoices; open ones are expected on due date + delay).
- **Frontend**: `AppState` loads cards, forecast and company from the API (mock stays as fallback); swipes save the status and reload, undo/reset set cards back to pending; alerts come from the forecast; `ForecastCard` (Analysis page) shows past + forecast + after decisions; currency follows the data (`setDisplayCurrency`).
- Still mock: the rest of Analysis (payroll, revenue vs expenses), Invoices, Risk, Mail pages.

## Expansion on `feature/math-engine-expansion` (2026-11-21)

Started from the fetched `origin/master` tip. The implementation now advances the engine/API in these areas:

- Forecast volatility uses `Decimal` throughout instead of converting weekly inflows through binary floats.
- Bank accounts can store `balance_as_of`. Alembic migration `007_account_balance_as_of` backfills it from each account's latest transaction date. `PUT /api/v1/accounts/{id}/balance` records an explicit balance snapshot and rejects future dates.
- Forecast context uses the later of the explicit snapshot date and latest transaction date. When transactions were booked after the snapshot, their base-currency amounts are added to the snapshot to obtain the forecast opening balance. Statement imports advance the snapshot date as they add transaction amounts to the account balance.
- Invoice liquidity validation now runs the deterministic forecast simulator, placing the candidate invoice at its due date and including already-approved/simulated decisions. It evaluates the pessimistic lowest balance against both the safety buffer and account overdraft floor. Unsupported currencies, credit notes, and invoices beyond the horizon are explicitly left unchecked.
- Early-payment discounts are only recommended when the deadline is still actionable, falls before the due date, and the pessimistic forecast stays above the required floor.
- Invoice duplicate checks require an exact normalized vendor match and invoice-number token boundary; vendor history for IBAN and price comparisons also uses exact normalized names. Price comparisons stay in invoice currency and use outflow transactions only.
- Invoice creation saves the invoice before generating cards; card generation accepts the invoice account and links resulting cards to the saved invoice. The validation-only endpoint no longer writes unlinked action rows.

No tests have been run. Remaining review items include verifying the new balance-snapshot semantics against statement-import behavior, handling sales-invoice customer payment delays consistently in validation, separating credit-note direction, and expanding stored engine inputs for payroll, subscriptions and other obligations that are not represented in the current schema.

## Model tool integration (2026-11-21)

Commit `8ad0f6d` contains the engine expansion. Current code adds read-only OpenAI-compatible tools to `POST /api/v1/actions/{id}/explain` and `POST /api/v1/ai/explain`: `get_cash_forecast` and `simulate_cash_changes`. The model requests calls; the backend validates bounded arguments and calls the forecast manager, which alone loads database state and runs deterministic calculations. The model receives concise scenario indicators, not raw database access or the full time series. The response's `facts_used.engine_tool_calls` contains calls/results, with persistent traces described below. Tool support depends on the configured vLLM endpoint accepting OpenAI-compatible `tools` / `tool_choice` payloads, with auto tool choice and a matching parser enabled server-side; this has not yet been exercised against the cluster model.

## Model call logs in progress (2026-11-21)

- Migration `008_agent_engine_logs` adds append-only `agent_engine_calls` traces (request/card/user IDs, tool name, arguments, result, status, duration and timestamp) and `agent_capability_requests` (the model's description of a missing data/calc capability and business need).
- Planned authenticated reads: `GET /api/v1/ai/engine-calls` and `GET /api/v1/ai/capability-requests`, filterable by explanation `request_id` or card `action_id`.
- `report_missing_engine_capability` is an explicit model tool. These reports are hypotheses from the model, not verified gaps, and require human review before prioritizing engine work.
- Logs are written in the request's PostgreSQL transaction. They contain financial tool inputs and summarized results; retention and redaction policy remain to be decided. Calls are only created when vLLM actually returns tool calls, so unsupported server tool-calling configuration yields no engine call rows.
