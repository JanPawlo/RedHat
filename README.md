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
