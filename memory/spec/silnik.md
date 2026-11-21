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
- [x] Use the forecast in the invoice validator: liquidity check over the horizon instead of "balance today − invoice" (2026-11-21).
- [x] Generated test data at larger scale (2026-11-21, see "Test data generator" below).

## Invoice validator: bugs found in the review (2026-11-21)

`backend/app/services/invoice_validator.py`. All fixed on 2026-11-21 (branch `feature/quality-fixes`, see "Invoice validator: fixes" below):

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
- Still mock: Mail page; "Make a card" on Risk only shows a toast; Invoices "Pay now" stays a SIMULATED front-end action. Since 2026-11-21 from the DB: Analysis (`GET /analysis`), Invoices (`GET /analysis/invoices`), Risk + Analysis risk tile (`GET /analysis/risk`, fixed rules, Google/KRZ/eKRS shown as "Not connected"), cash calendar component (`GET /analysis/calendar`, still not placed on any page), Advisor facts (`GET /analysis/advisor-facts`, incl. `spending_room` = largest one-off payment per day that keeps the buffer). Code: `app/managers/page_manager.py`, constants `app/const/pages.py`.
- Advisor chat: always through the backend `POST /ai/explain` with `mode: "advisor"` (prompt `ADVISOR_PROMPT` stays on the server) and `history` (max 12 turns, roles user/assistant only). qwen3-8b gets wrong answers when it has to compare numbers itself, so give it precomputed facts (e.g. `is_below_safety_buffer`, `spending_room`) instead of raw balances.

## Invoice validator: fixes (2026-11-21, branch `feature/quality-fixes`)

Decisions taken while fixing the 8 bugs above (tests: `backend/tests/test_invoice_validator.py`):

1. Direction comes from `invoice_type`: `incoming_expense` and `receipt` are payables (money out); `outgoing_revenue` and `credit_note` bring money in, so they skip the IBAN, price-spike, liquidity and Skonto checks (`PAYABLE_INVOICE_TYPES` in `const/invoice.py`).
2. "Already paid" needs the same counterparty (normalized: lower-case, trimmed), the invoice number as a whole token in the reference (`12` no longer matches `Invoice 1234`) and the right direction (an outflow for a payable).
3. Vendor history, duplicates and the IBAN check use the same normalized full name, never a fragment (`Metro` ≠ `Metropolitan`).
4. Invoice currency ≠ account currency → INFO flag `CURRENCY_NOT_CONVERTED`, liquidity not checked (there is no FX rate source); the price spike compares only past payments in the invoice currency (original `amount`).
5. The price spike averages only outflows to that vendor (refunds no longer inflate the average).
6. Liquidity runs the forecast engine (`payment_impact`): the invoice is paid on its due date on top of the approved decisions; the horizon is extended up to 90 days, beyond that INFO `DUE_DATE_BEYOND_FORECAST`. Lowest base balance below −overdraft limit → CRITICAL `INSOLVENCY_DEFICIT_RISK`; below 0 but within the limit → WARNING `OVERDRAFT_USED` (new); below the buffer → WARNING `SAFETY_BUFFER_BREACH`. The account (given `account_id` or the primary one) comes from `invoice_manager._cash_position`.
7. The Skonto deadline is compared with the forecast start (`as_of`, the "today" of the bank data; `date.today()` only without account data). Expired → INFO `EARLY_DISCOUNT_EXPIRED`, no recommendation. Paying early is checked with the engine on the deadline.
8. Any CRITICAL flag makes the invoice invalid and creates the hold card (even when the score is only HIGH); cards get `dedupe_key = invoice:<counterparty>:<number>:<agent>`, so repeated `/validate?auto_create_card=true` calls create one card; the VAT message lists `STANDARD_VAT_RATES`; risk weights are `RISK_WEIGHT_*` constants.

## Supplier dependency: one definition (2026-11-21)

Analysis said "Asimex 35% of supplier costs" (calendar quarter) and Risk "Fattoria 35% of purchases" (90 days). Both now use `app/services/supplier_share.py`: payments with category `supplier` (outflows only) in the **last 90 days up to the forecast start** (`SUPPLIER_SHARE_WINDOW_DAYS`), share = this supplier ÷ all suppliers. Rent, utilities, tax and payroll are not suppliers. The text names the window ("… of supplier spend in the last 90 days"). On the demo data both pages show Fattoria La Vino GmbH = 35 %. The Risk watchlist item "X is N% of …" uses the same number. The counterparty table `share` (all counterparty categories, 1 year) is unchanged and not shown in the UI.

## Calendar events in the forecast (2026-11-21)

- Calendar in `app/const/calendar.py`: public holidays (fixed and Easter-based), school breaks, season and local events for **PL** (default) and **DE** (the demo company is in Frankfurt, taken from `company.country`). The owner can add own yearly events in `company.settings["calendar_events"]` (`[{name, start: "MM-DD", end: "MM-DD", assumed_effect}]`); the seed adds the Pizzeria June closure.
- Effect = revenue in the event window ÷ normal revenue of the **same weekdays** in the 28 days before and after (other events left out), averaged over past occurrences fully inside the history (`services/calendar_events.py`). Without such an occurrence the constant `assumed_effect` is used and marked `estimate`.
- No double counting: with ≥ 300 days of history the month factor already holds last year's event spread over its month. Then event days get `(1+e)/(1+e·s)` and the rest of that month `1/(1+e·s)` (s = event days ÷ month days), so the month total stays the same. Without month seasonality (or when the event fell in another month last time, e.g. Easter) the full `(1+e)` is applied on the event days.
- Each change is its own forecast driver (`Calendar: <name> (measured|estimate)`), so every number keeps a source. `GET /forecast` returns `events` (effect, source, `already_in_base`, `event_days_change`, net `revenue_change`).
- LLM: `calendar_events` + `calendar_events_meaning` in the card "Ask why" facts and in the advisor facts; `CALENDAR_RULE` in both prompts says to name the event and whether it is measured or an estimate, and never to compute it.
- Credit-line card: when one event removes ≥ 25 % of the shortfall before the lowest day, the title gets "Seasonal liquidity · <event>:" and the reason names the event. This is how a seasonal card is produced now.
- Demo data (horizon 2025-12-31 + 90 days): only Neujahr falls inside, measured +6 % (the pizzeria is open), so no seasonal card.
- The old static card "Seasonal Liquidity Buffer: Projected June Deficit Warning" was removed from `backend/app/services/seed.py` (decision 2026-11-22, Kacper): it had 2025 numbers and pointed at June, outside the forecast that ends in March. Seasonal cards now come only from the calendar events mechanism. Databases seeded before keep the old card until a reseed or manual delete.

## Test data generator (2026-11-21)

- `backend/scripts/generate_test_data.py`: seeded statements in the sample CSV layout for 5 profiles (pizzeria DE/EUR; software house, transport, beauty salon, developer PL/PLN) with weekday rhythm, month seasonality, holidays (from the calendar constants), company closures, late-paying clients, supplier price drift and one-off shocks. Profile definitions live in the script (test tooling, not app constants).
- `python scripts/generate_test_data.py --all --out-dir /tmp --backtest` (inside the backend container) prints the backtest: train on year 1, forecast 60 days of year 2, error vs the generated balance, with the calendar off and on.
- Seed 42, mean absolute error in days of average revenue: pizzeria 2.3, beauty salon 8.6, developer 7.1, transport 8.8, software house 12.8–13.9. The B2B profiles are weak because client invoice income is lumpy and not recurring; open sales invoices (not part of a statement) would fix most of it. The calendar changes little in a January–February window (only New Year and Epiphany).
- Tests: `backend/tests/test_generated_data.py` (parser accepts every profile, 2 years, deterministic seed, drift, closure, late client, backtest runs).
