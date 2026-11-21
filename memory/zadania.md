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
- [x] Forecast chart and decision deck on the dashboard; approved cards change the forecast (2026-11-21, `spec/silnik.md`). Merge with the `natalia-frontend` design still to do.
- [ ] Fix the invoice validator bugs listed in `spec/silnik.md`.
- [ ] Generator of larger test data (plan in `spec/silnik.md`).
- [ ] Optional, after the demo: rate limit on `/auth/login`.
- [ ] Review `spec/funkcjonalnosci.md` as a team and approve the MVP scope (P1) in `decisions/decyzje.md`.
- [x] Deploy model on the cluster: `qwen3-8b` replaced the weak 3B model on 2026-11-21 (details in `spec/openshift-ai.md`).
- [ ] Choose 2–4 bonuses that fit the stack (vLLM already included, MaaS, NeMo Guardrails, Dev Spaces).

## Card templates (spec/szablony-kart.md)

Developers define decision scenarios as templates; the engine finds and simulates candidates; the AI writes the card text and ranks them. New template = one registry entry + `detect` + `cash_changes` + texts + a unit test (checklist in the spec).

- [ ] Template contract and registry: `CardTemplate` (key, version, goal, agent, detect, cash_changes, slots, traits, copy_brief, fallback_copy, guardrails, follow_ups, questions); agree with the team where it lives in `backend/app/`.
- [ ] Coordinator: goal from the forecast (`close_liquidity_gap`, `use_free_cash`, `save_money`) → detect → engine preview per candidate → deterministic filter and pre-score.
- [ ] AI fill + rank step: one LLM call with the shortlist, JSON output (title, proposal, description, rank, reason), validation (numbers only from slots, known candidate ids), fallback to `fallback_copy` and the pre-score order.
- [ ] Store `template_key`, `template_version`, `slots`, rank and reason on `AgentAction` (new migration); `GET /cards` sorted by rank.
- [ ] Port the existing generators from `test-calosci` `card_manager.py` to templates (credit line, defer invoice, late payer, early discount, deposit).
- [ ] Template `cancel_subscription`: non-essential recurring outflows (essential categories list in `const/`), effect after the notice period.
- [ ] Template `collect_overdue`: overdue and usually-late sales invoices, escalation steps (reminder → reminder with discount → formal demand → payment plan).
- [ ] Template `delay_planned_investment`: needs a "planned expenses / known events" table and a way for the owner to add them (form or chat).
- [ ] Template `negotiate_extension`: supplier invoices and recurring payments such as rent due in the gap; never tax or ZUS.
- [ ] Template `take_credit`: product catalogue in `const/` (overdraft, revolving credit line, short-term loan; demo rates marked as assumptions), one candidate per product.
- [ ] Regenerate cards when data changes (statement upload, invoice added or paid, decision made), not only in the seed.
- [ ] Remove the hand-written "Seasonal Liquidity Buffer" action from `seed.py` (stale July 2025 card without cash changes).
