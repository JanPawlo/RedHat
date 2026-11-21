# Tasks

- [x] Choose at least one of the 4 use cases: **Liquidity Agent** chosen as the core use case (cash flow forecast & Commerzbank credit line proposals).
- [x] Settle the tech stack & architecture (Python FastAPI, PostgreSQL + Alembic, React/Vite/Tailwind, Docker Compose, OpenShift); documented in `TECH_STACK.md`.
- [x] Design single-tenant database schema & initial Alembic migration (accounts, transactions with `metadata_payload`, forecasts, agent actions).
- [x] Implement bank statement CSV parser (flexible formats, CHF/EUR FX conversion) & seeding script.
- [x] Implement domain math & liquidity simulation verification script (`backend/scripts/simulate_demo.py`).
- [x] Implement Invoice & Receipt Validation Engine with LLM tool-calling API (`/api/v1/invoices/validate`, IBAN anti-phishing, duplicates, Skonto early discount, math integrity).
- [x] Basic login & registration (branch `feature/auth`, verified in GitHub Codespaces 2026-11-20, not merged to `main` yet): JWT `POST /api/v1/auth/register`, `/login`, `GET /me`, `users` table (migration `003`), React login/register page in front of the dashboard; since 2026-11-21 the admin account is created on API startup only when env `ADMIN_PASSWORD` is set (login from `ADMIN_LOGIN`, default `admin`); migration `004` is now empty. Migrations run automatically when the API starts (FastAPI `lifespan` → `app/core/migrations.py`, upgrade to `head`; if it fails the API does not start). With `APP_ENV` other than `development` the API refuses to start while `JWT_SECRET_KEY` is the dev default, so set a real secret on the cluster. Smoke-test before merging to `main`.
- [x] Review fixes K1–K5 (2026-11-21, `feature/auth`): login required on every domain endpoint; no hard-coded admin; JWT secret guard; invoice validation no longer crashes with several primary accounts / duplicate invoices / short invoice numbers (LIKE wildcards escaped); CSV upload: `.csv` only, max 5 MB, UTF-8/cp1252/cp1250, row errors → 400 with row number, unknown `account_id` → 404, duplicates (same date + amount + reference) skipped, account balance updated, imported accounts are not primary.
- [x] Review fixes W1–W18 (2026-11-21, `feature/auth`): input validation matching DB columns, action status flow, no internal URLs in errors, LLM errors → 503, logging, `DEBUG`/`SQL_ECHO` off by default, single commit per request, CORS from env, password hashing off the event loop, registration flag, no demo balance in validator, JSONB + missing index (migration 005), dashboard reads real data, single `/api` prefix, non-root containers, dependency upper bounds, scripts moved to `backend/scripts/`.
- [x] Review fixes, third round (2026-11-21): statement import matches duplicates one to one (date + amount + reference + counterparty) and locks the account row; CSV upload moved to `POST /api/v1/statements/upload/csv`; NaN/huge amounts, over-long fields and bad currency → 400; DB session `db_session` with FastAPI scope `function` (commit before the response, FastAPI >= 0.121); invoice with unknown `account_id` → 404; startup migrations behind a Postgres advisory lock. Admin `admin/admin` stays on existing DBs for now (known risk, team decision).
- [x] CI and releases (2026-11-21): `ci.yml` = quick smoke check on `master`; `release.yml` runs on tags `v*` (team format `v0.0.HHMM.DDMMYY`): ruff, migrations + pytest API tests (`backend/tests/`) on PostgreSQL, frontend build, Docker builds, then a GitHub Release. Details in `README.md` ("CI and releases").
- [ ] Smoke-test `master` with `docker compose up --build` (login, dashboard, CSV upload, seed, migration 005 on an existing DB) and check the first release run in GitHub Actions.
- [ ] Deploy backend, frontend and PostgreSQL on the team OpenShift cluster (hard requirement): `oc new-app` with `--context-dir=backend` / `frontend` and the Dockerfiles, config via Secret / `oc set env` (real `JWT_SECRET_KEY`, `APP_ENV` not `development`, `ADMIN_PASSWORD`, `ALLOW_REGISTRATION=False`), backend service named `backend`, model URL pointing at the in-cluster predictor.
- [ ] Commit `frontend/package-lock.json` (run `npm install` once) and switch the frontend Dockerfile back to `npm ci`.
- [x] Forecast engine + API (2026-11-21, branch `feature/forecast-engine`): `GET /api/v1/forecast`, `POST /api/v1/forecast/simulate`; details, known gaps and the invoice validator bug list in `spec/silnik.md`.
- [x] Forecast chart and decision deck on the dashboard; approved cards change the forecast (2026-11-21, `spec/silnik.md`). Merged with the `natalia-frontend` design (branch `test-calosci`); `/demo-reset` puts the data and all decisions back to the demo start state.
- [ ] Fix the invoice validator bugs listed in `spec/silnik.md`.
- [ ] Generator of larger test data (plan in `spec/silnik.md`).
- [x] Registration does not work (reported 2026-11-21): checked the same day, registration works locally (localhost:3000, 201) and on the cluster route (201, `ALLOW_REGISTRATION=true` in every `cfo-backend` revision). Not reproduced, so no code change. It is refused only for logins without `@` (e.g. `admin2`) and reserved domains (e.g. `x@test.local`) because the field must be a real e-mail. If it fails again, note the exact e-mail and the error text shown under the form.
- [-] ~~Optional, after the demo: rate limit on `/auth/login`.~~ Not doing (decision 2026-11-21).
- [-] ~~Review `spec/funkcjonalnosci.md` as a team and approve the MVP scope (P1) in `decisions/decyzje.md`.~~ Not doing (decision 2026-11-21).
- [x] Deploy model on the cluster: `qwen3-8b` replaced the weak 3B model on 2026-11-21 (details in `spec/openshift-ai.md`).
- [x] Choose bonuses (2026-11-21): Guardrails, MaaS, Dev Spaces, Pipelines/GitOps (the last one gives no points). Exact plan, steps and status per bonus: `decisions/bonusy.md`.
- [ ] Bonus Dev Spaces: install the operator, add `devfile.yaml`, code part of the work there (steps in `decisions/bonusy.md`).
- [ ] Bonus NeMo Guardrails on RHOAI (TrustyAI, Technology Preview) in front of `qwen3-8b` (steps in `decisions/bonusy.md`).
- [ ] Bonus MaaS: the backend reaches `qwen3-8b` through the model gateway with an API key (steps in `decisions/bonusy.md`).
- [ ] Optional, no points: Tekton pipeline for redeploys (`decisions/bonusy.md`).

## Card templates (spec/szablony-kart.md)

Developers define decision scenarios as templates; the engine finds and simulates candidates; qwen3-8b writes the card text and ranks them; guardrails check every word. Implemented 2026-11-21 on branch `jan-szablony-kart` (details, guardrails, field limits and the engine gap report in `spec/szablony-kart.md`).

- [x] Template contract and registry (`app/services/card_templates.py`, constants in `app/const/card_templates.py`).
- [x] Coordinator: goals → detect → engine simulation per candidate → filter, engine score, tiers, shortlist (`card_manager.generate_cards`).
- [x] AI fill + rank with guardrails, one repair round, fallback text; chat answers checked too (`card_guardrails.py`, `card_writer.py`).
- [x] Store template data, rank and reason in `impact_simulation.template` (no migration); stale cards leave the deck; `GET /cards` sorted by rank.
- [x] Port the old generators (credit line, defer invoice, late payer, early discount, deposit) to templates.
- [x] Templates `cancel_subscription`, `collect_overdue`, `delay_planned_investment`, `negotiate_extension`, `take_credit`.
- [x] Remove the hand-written "Seasonal Liquidity Buffer" action from `seed.py`; demo extras (2 subscriptions, planned oven).
- [x] Tests: 31 pure tests + cards API test; real qwen3-8b answers replayed from `tests/fixtures/`.
- [ ] Regenerate cards when data changes (statement upload, invoice added or paid, decision made), not only in the seed or via `POST /cards/generate`.
- [ ] Engine gaps 1–3 from `spec/szablony-kart.md` (overdue invoices in the forecast, planned purchases table, existing overdraft limit).
- [ ] Show `rankReason` on the card in the frontend.
- [ ] Merge into `test-calosci` after team review, then deploy (backend on the cluster calls the in-cluster predictor directly).

## After the hackathon (out of hackathon scope)

- [x] Guardrails for the AI agent, own layer (2026-11-21, branch `feature/register-guardrails-bank`): input, data and output rails on every LLM call; refuses money laundering, tax evasion, fraud, bribery, other people's personal or banking data and prompt injection; masks PESEL, card numbers and IBANs in answers; Advisor chat moved behind the backend (`POST /api/v1/ai/advisor`). Details in `decisions/bonusy.md` section 1. Keeping the model from inventing numbers stays a system-prompt rule.
- [x] Bank integration mockup (2026-11-21, branch `feature/register-guardrails-bank`): Settings page (`/settings`, sidebar "Settings") with 4 mock banks; Connect (simulated PSD2 consent, 90 days) creates the bank's accounts and imports 60 days of generated transactions, Sync imports only new ones and takes the balance from the bank, Disconnect removes them. API `/api/v1/bank-connections`. Connected accounts are extra (not primary), so the forecast still runs on the main account; making a connected account the forecast source is a possible next step.
