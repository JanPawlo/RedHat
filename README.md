# Redline

> **Collabothon 2026 · Project Card**

## One-Line Summary

Redline is an AI CFO for small business owners: it forecasts cash flow, spots trouble weeks ahead and turns it into simple swipe-to-decide cards with clear reasoning.

## Technology Stack

- **Languages:** Python 3.11, JavaScript
- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2.0 (async, asyncpg), Alembic, PyJWT
- **Frontend:** React 18, Vite, Tailwind CSS, Recharts, Framer Motion, React Router, Lucide Icons
- **Database:** PostgreSQL 16
- **AI:** Qwen3-8B (open-weights LLM) served by vLLM on Red Hat OpenShift AI (NVIDIA L4 GPU), OpenAI-compatible API; NVIDIA NeMo Guardrails
- **Platform:** Red Hat OpenShift (S2I builds, TLS Routes); Docker Compose for local development
- **CI/CD:** GitHub Actions (pytest, ruff, frontend build, tagged releases)
- **Data & APIs:** organizers' sample bank statement; simulated PSD2 bank connection and payments; KSeF-shaped e-invoice data (mocked)

## Project Overview

### The Problem

Every day, hundreds of small business owners open their books, see the numbers and still don't know what to do with them. Those who don't check every day get caught out by sudden expenses: rent, payroll and taxes landing in the same week, or an invoice discount that quietly expired. Small companies rarely have a CFO, so cash-flow planning lands on an owner who is already overworked. We want owners to focus on running their company, not on worrying about next week's cash.

### Our Solution

Redline works like a semi-autonomous CFO. It tracks income and expenses, finds recurring patterns, projects the balance into the coming weeks and decides whether anything needs attention. It then picks the best options and presents them as bite-sized decision cards. Swipe right to approve, left to decline, or tap "Ask why" for the reasoning.

The core principle is **"the engine calculates, the AI explains."** Every number comes from a deterministic forecasting engine: balances, liquidity gaps, the effect of each decision, and the confidence level, which is computed across pessimistic, base and optimistic scenarios. The LLM only puts that into plain language and answers follow-up questions, so it never invents figures. The UX is built around this: the owner decides how much effort to put in, from a two-minute swipe through today's cards to a deep dive with the advisor.

### The Working Prototype

Implemented and working today:

- **Dashboard** with a cash-flow forecast chart showing the baseline, the liquidity gap and the "after approved actions" line.
- **Decision card deck:** cards are generated from real data (e.g. liquidity gaps, early-payment discounts) and come with a recommendation and a confidence level. Approving a card recalculates the forecast immediately.
- **"Ask why":** the card flips to show the data behind the recommendation, and the LLM explains it, including "what if" questions.
- **AI Advisor chat** that answers questions about the company's finances using the engine's data.
- **Analysis, Invoices and Risk pages**, all computed from the database, plus a data-quality check on imported transactions.
- **Guardrails:** NeMo Guardrails block off-topic, illegal or personal-data requests.
- **Login/registration** and a demo-reset mode.
- **Deployment:** everything runs on Red Hat OpenShift, with the model served on OpenShift AI.

Simulated or mocked: bank connection (PSD2) and payments (the user can "pay" in-app, but it is simulated), KSeF invoice import, and outgoing e-mails.

### Behind the Build

Imported bank transactions and invoices are stored in PostgreSQL. A deterministic forecast engine written in pure Python detects recurring payments, models revenue seasonality and builds three cash-flow scenarios. Rule-based agents use those scenarios to spot situations that need a decision, such as a liquidity gap, a discount worth taking or a supplier concentration risk, and turn them into cards. The LLM (Qwen3-8B on vLLM, Red Hat OpenShift AI) writes the card text and answers questions, while NeMo Guardrails filter what goes in. If the model is slow or unavailable, cards fall back to deterministic templates, so the app keeps working. The React frontend calls a FastAPI REST API.

Key technical decisions:

- Numbers only from code, never from the LLM.
- An open-weights model hosted on our own cluster, so financial data stays in-house.
- A request limiter and answer caching to share a single GPU.

Built upon: FastAPI, React, vLLM, Qwen3-8B, NeMo Guardrails, the OpenShift AI cluster and sample data provided by the organizers. Created by our team during the hackathon: the forecast engine, the card agents and templates, the data validation and currency normalization, the LLM integration layer with fallbacks, the full UI, and the OpenShift deployment.

### Challenges and Discoveries

- **LLMs and numbers don't mix.** Early on, the model would make up or round amounts. Splitting the work so the engine calculates and the AI only explains solved this and made every recommendation traceable.
- **One GPU, many requests.** With several parallel requests, the model slowed down sharply. We added a request limiter, response caching, prefetching and template fallbacks, which taught us to design for a degraded model rather than assume it is always fast.
- **Messy real-world data.** The sample statement mixed currencies (CHF transfers on a EUR account). We added a currency normalizer and a data-quality notice that tells the user about it.
- **Infrastructure details.** OpenShift's default 30-second route timeout cut off long operations, and we had to tune timeouts across the router and proxy.
- **Team integration.** Five people built the engine, cards, UI and guardrails in parallel. We learned to integrate early and often through CI and pull requests.

### Results and Next Steps

We built a smooth, controllable workflow that is instantly understandable. The interface lets users decide for themselves how much effort to put into managing their finances, without sacrificing the quality of the decisions or the user experience. We are most proud that every recommendation can be explained down to the transactions behind it.

Limitations: there is no real integration with KSeF or payment systems yet. We show that data flows into the app and that the user can pay instantly in-app, but those parts are simulated. Next, we want to make these integrations real so the experience is fully seamless. Our ambitious plan is to offer Redline to banks as a white-label service they can integrate into their apps, with our support, to strengthen their offering for business clients.

---

# RedHat
The name was available.
Collabothon Red Hat's challenge about creating an autonomus CFO agent for small-medium companies.

## Where is what

| **Path** | **What is there** |
| --- | --- |
| [`backend/`](backend/) | Python API (FastAPI, SQLAlchemy, Alembic, PostgreSQL) |
| [`frontend/`](frontend/) | React SPA (Vite, TailwindCSS) |
| [`memory/`](memory/) | Shared project memory: everything we know and decide (plain Markdown, in English) |
| [`memory/reference/`](memory/reference/) | Original files from the challenge organizers (challenge card, slides, survival guide, project card, sample data); index in [`memory/reference/README.md`](memory/reference/README.md) |
| [`docker-compose.yml`](docker-compose.yml) | Local stack: PostgreSQL + backend + frontend |
| [`TECH_STACK.md`](TECH_STACK.md) | Why we chose this stack and how to run it |
| [`DOCKER_SETUP.md`](DOCKER_SETUP.md) | Step-by-step Docker setup and running the project on Windows 11 (in Polish) |
| [`AGENTS.md`](AGENTS.md) | Instructions for AI assistants: read `memory/` first, write new findings back there, follow the coding rules |
| `CLAUDE.md`, `GEMINI.md` | Only import `AGENTS.md`, so Claude Code and Gemini CLI load it automatically |

## Project structure

### Backend

```
backend/
├── Dockerfile, requirements.txt, .env.example
├── alembic.ini
├── alembic/versions/            database migrations (applied automatically when the API starts)
├── scripts/                     standalone checks run by hand (validator test, demo math audit)
└── app/
    ├── main.py                  app start: migrations → admin account → CORS → routers
    ├── api/
    │   ├── deps.py              get_current_user (checks the JWT)
    │   ├── errors.py            ready-made HTTP errors (401, 404, 400, 409, 503)
    │   └── v1/
    │       ├── router.py        only includes the controller routers under /api/v1
    │       └── controllers/     one file per resource: auth, company, accounts, transactions,
    │                            statements, actions, ai, invoices
    ├── managers/                business logic and DB queries, one per controller (<resource>_manager.py)
    ├── services/                bigger standalone modules: CSV parser, invoice validator, LLM client, seed script
    ├── models/                  SQLAlchemy tables
    ├── schemas/                 Pydantic request/response models
    ├── const/                   constants only (messages, limits, statuses, names)
    └── core/                    infrastructure: config, database session, security (hash, JWT), migrations, SQL helpers
```

A request goes through three layers:

1. **Controller** (`api/v1/controllers/<resource>.py`) checks access (`Depends(get_current_user)`), calls the manager and turns its result into an HTTP response or error.
2. **Manager** (`managers/<resource>_manager.py`) does the work: queries, rules, saving. It knows nothing about HTTP.
3. **Service** (`services/`) is a bigger reusable piece of domain logic that a manager calls (parsing a statement, validating an invoice, asking the model).

### Frontend

```
frontend/
├── Dockerfile, nginx.conf       production: nginx serves the build and forwards /api/ to the backend
├── vite.config.js               development: proxy /api → backend:8000
└── src/
    ├── main.jsx                 React entry point
    ├── App.jsx                  checks the session: login page or dashboard
    ├── const/                   constants (API base URL, token key, endpoint paths)
    ├── api/
    │   ├── client.js            apiFetch: the only place that calls fetch (token, errors, 401 → logout)
    │   └── <resource>Api.js     one file per backend controller, e.g. authApi.js
    └── pages/                   screens (LoginPage, Dashboard); they call only api/*Api.js
```

### Deployment extras

```
devfile.yaml                     OpenShift Dev Spaces workspace (Python, Node, PostgreSQL containers + commands)
deploy/
└── nemo-guardrails/             NeMo Guardrails server in front of the model: Dockerfile, rails config, OpenShift manifests
```

NeMo Guardrails is optional: `GUARDRAILS_ENABLED=true docker compose --profile nemo up --build` runs it locally and
routes the backend's model calls through it. Steps for the cluster: `memory/decisions/bonusy.md`.

## Running locally

```
docker compose up --build
```

- Frontend: http://localhost:3000, API docs (Swagger): http://localhost:8000/docs
- Every endpoint except `/api/health` (also `/health` for probes), `/api/v1/auth/login` and `/api/v1/auth/register` needs a JWT. Log in or register, then use **Authorize** in Swagger.
- Registration is open only when `APP_ENV=development`, unless `ALLOW_REGISTRATION` says otherwise. Set it to `False` on a shared deployment and use the admin account.
- Demo data: `docker compose exec backend python -m app.services.seed` loads Pizzeria Amalfi (the sample CSV is mounted into the container).
- Local admin account: `admin` / `admin` (created on startup; override with `ADMIN_LOGIN` / `ADMIN_PASSWORD` in a root `.env` file, use a strong password on a shared deployment).
- Local login (values from the root `.env`, local Docker only):

  | What | Login | Password |
  |---|---|---|
  | App (http://localhost:3000, Swagger) | `admin` | `admin` |
  | PostgreSQL | `cfo_user` | `cfo_password` |

  The login request body uses the field `email` even for `admin`: `POST /api/v1/auth/login` with `{"email": "admin", "password": "..."}`.
- On a shared deployment set `APP_ENV` to something other than `development` and a real `JWT_SECRET_KEY` (e.g. `openssl rand -hex 32`); otherwise the API refuses to start. Keep `SQL_ECHO` off there: it logs query parameters such as emails and password hashes.
- The frontend calls `/api/v1/...` and `/api/health`; Vite (dev) and nginx (Docker) forward `/api` to the backend unchanged. In OpenShift the backend service must be named `backend` (or change `frontend/nginx.conf`).

## CI and releases

Two GitHub Actions workflows live in `.github/workflows/`:

| **Workflow** | **Runs on** | **Checks** |
| --- | --- | --- |
| `ci.yml` | push and pull request to `master` | Backend compiles and `app.main` imports, test scripts in `backend/scripts/` (SQLite), frontend build. Quick smoke check, no real database. |
| `release.yml` | push of a tag starting with `v` | Everything below, then creates a GitHub Release with notes generated from the commits. |

`release.yml` checks:
- lint for syntax errors and undefined names (`ruff`),
- Alembic migrations on an empty PostgreSQL 16,
- API tests from `backend/tests/` (pytest, real PostgreSQL): login and registration, statement CSV import (duplicates, bad values), invoices,
- frontend build and Docker build of both images (images are not pushed anywhere yet).

Release a version (tags follow [semantic versioning](https://semver.org/), e.g. `v0.2.0`):

```
git tag v0.2.0
git push origin v0.2.0
```

If a check fails, no release is created. Fix the code, delete the tag (`git tag -d v0.2.0`, `git push origin :refs/tags/v0.2.0`) and tag again.

Run the API tests locally against the Docker database: `docker compose exec backend python -m pytest` (install `pytest` in the container first: `pip install pytest`). They leave test users and accounts in that database.

To block merging into `master` without green CI, turn on branch protection in GitHub: Settings → Branches → require the "Backend tests" and "Frontend build" status checks.

## Project memory

Everything we know and decide about the project lives in [`memory/`](memory/) as plain Markdown (written in English), so it works with any AI assistant, not only Claude Code.

| **File** | **Purpose** |
| --- | --- |
| [`memory/README.md`](memory/README.md) | Index of memory files and the rules for editing them |
| [`memory/spec/`](memory/spec/) | The essentials: project description, challenge summary (requirements, scoring), features, our OpenShift AI cluster and model deployment |
| [`memory/decisions/`](memory/decisions/) | Decisions (incl. LLM choice and code structure) and rejected ideas, brainstorm ideas, external review of the concept |
| [`memory/examples/`](memory/examples/) | Sample data analysis (Pizzeria Amalfi 2025) and example companies; copy `firmy/_szablon.md` to add one |
| [`memory/reference/`](memory/reference/) | Organizers' original files (read-only) |
| [`memory/zadania.md`](memory/zadania.md) | To-do list |

### Using it with your assistant

- **Claude Code, Gemini CLI, Codex, Copilot:** open the repo; they pick up `AGENTS.md` (or `CLAUDE.md` / `GEMINI.md`) on their own.
- **ChatGPT, Gemini or Claude in the browser:** paste or upload `AGENTS.md` and the files from `memory/` at the start of the chat, then ask it to return the updated files and commit them.
