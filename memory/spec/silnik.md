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

## Invoice validator: bugs found in the review (2026-11-21)

`backend/app/services/invoice_validator.py`, not fixed yet:

1. `invoice_type` is ignored: a sales invoice or credit note is subtracted from the balance like a cost (false overdraft).
2. "Already paid" matches any transaction whose reference contains the invoice number, without checking the counterparty: number `12` matches `Invoice 1234` → +60 risk → CRITICAL.
3. The vendor is matched by a fragment of the name (`Metro` matches `Metropolitan`) → false IBAN phishing alarm and wrong price spike.
4. Currencies are mixed: a PLN invoice is subtracted from an EUR balance; price spike compares without conversion.
5. Price spike averages inflows too (`abs()` of all transactions of that counterparty).
6. Liquidity = balance today − invoice; ignores due date, future flows and `overdraft_limit` (fix via the forecast engine).
7. Skonto deadline is never checked against today: an expired discount is still recommended.
8. Smaller: CRITICAL flag but HIGH risk level gives no card; each `/validate?auto_create_card=true` call creates another card; VAT message lists different rates than the constant; risk weights are magic numbers.

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
