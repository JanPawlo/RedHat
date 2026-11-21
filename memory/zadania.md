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
- [ ] Registration does not work (reported 2026-11-21): find the cause (check `ALLOW_REGISTRATION`, `POST /api/v1/auth/register` and the register form on the front) and fix it.
- [ ] Optional, after the demo: rate limit on `/auth/login`.
- [ ] Review `spec/funkcjonalnosci.md` as a team and approve the MVP scope (P1) in `decisions/decyzje.md`.
- [x] Deploy model on the cluster: `qwen3-8b` replaced the weak 3B model on 2026-11-21 (details in `spec/openshift-ai.md`).
- [ ] Choose 2–4 bonuses that fit the stack (vLLM already included, MaaS, NeMo Guardrails, Dev Spaces).

## After the hackathon (out of hackathon scope)

- [ ] Guardrails for the AI agent (e.g. NeMo Guardrails): input/output rails on `/ai/explain` and card explanations, block prompt injection from invoice/statement text, keep the model from inventing numbers that the engine did not compute, refuse topics outside company finance.
- [ ] Bank integration mockup: a mock open-banking (PSD2-style) API that returns accounts, balances and transactions in place of the CSV statement upload, so the forecast and cards can run on a "connected bank" flow in the demo/UI.
