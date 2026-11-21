# Instructions for AI assistants

Knowledge about the project is in the `memory/` folder. Before working, read all files from this folder:

@memory/README.md
@memory/spec/projekt.md
@memory/spec/wyzwanie.md
@memory/spec/funkcjonalnosci.md
@memory/spec/openshift-ai.md
@memory/decisions/decyzje.md
@memory/decisions/pomysly.md
@memory/decisions/recenzja-pomyslu.md
@memory/examples/dane-przykladowe.md
@memory/examples/firmy/README.md
@memory/zadania.md

The most important are the files in `memory/spec/` (what we are building and on what) and `memory/decisions/decyzje.md` (what we have agreed on). Descriptions of example companies are in `memory/examples/firmy/`. Read them when a task concerns specific clients, test data or demo scenarios.

The organizers' original materials (PDFs, sample CSV data) are in `memory/reference/`, and their index is in `memory/reference/README.md`. Do not edit them. Refer to them when the summary in `memory/` is not enough.

When you learn something or something gets decided, add it to the appropriate file in `memory/` following the rules from `memory/README.md`.
Do not put project knowledge into this file or into `CLAUDE.md` or `GEMINI.md`; this file holds only these instructions and the coding rules below. `CLAUDE.md` and `GEMINI.md` only import this one.

## Writing code

The project structure is described in `README.md` ("Project structure"). Follow it; do not invent new layers or folders without agreeing it with the team.

### General rules

- **Single responsibility:** one function does one thing, one file covers one resource or one topic. When a function does several steps, split them into small, well-named helper functions.
- **No magic values:** texts (error messages, statuses), limits and names go into constants: backend `backend/app/const/<topic>.py`, frontend `frontend/src/const/<topic>.js`. Add to an existing file when the topic matches.
- **Readable functions:** separate logically different steps inside a function with an empty line. Prefer early returns to deep nesting.
- **Names and docs in English.** Do not add comments that only repeat what the code says.
- **Secrets only from env** (`core/config.py` / `.env`). Never commit passwords, tokens or keys, never hard-code accounts in migrations.
- **Keep changes small:** do not delete or rewrite code you think is unused without asking the team.

### Backend: where what goes

| **Layer** | **Path** | **Does** | **Does not** |
| --- | --- | --- | --- |
| Router | `app/api/v1/router.py` | Includes controller routers | Contain endpoints |
| Controller | `app/api/v1/controllers/<resource>.py` | Declares endpoints, checks access, validates input via schemas, calls the manager, maps `None`/exceptions to HTTP errors from `app/api/errors.py` | Run DB queries or business rules |
| Manager | `app/managers/<resource>_manager.py` | Business logic, DB queries, saving; returns models or `None`; raises its own exceptions for expected failures | Import FastAPI or raise `HTTPException` |
| Service | `app/services/` | Bigger reusable domain logic (CSV parsing, invoice validation, LLM calls) used by managers | Know about HTTP or controllers |
| Model | `app/models/` | SQLAlchemy tables | Logic |
| Schema | `app/schemas/` | Pydantic request/response models and their validation | DB access |
| Constants | `app/const/` | Values only | Imports from the app or logic |
| Core | `app/core/` | Config, DB session, security (password hash, JWT), migrations, generic helpers | Domain logic |

**Access:** every endpoint except `/auth/login` and `/auth/register` takes `current_user: User = Depends(get_current_user)` in the controller. Never protect endpoints only in the frontend.

**Adding an endpoint:**

1. Logic as a function in `managers/<resource>_manager.py` (new manager file for a new resource).
2. Endpoint in `controllers/<resource>.py` with `Depends(get_current_user)`; new controller → include it in `router.py`.
3. Request/response models in `schemas/`, texts and limits in `const/`. Every input field gets limits matching the DB column (`max_length`, `ge`, `pattern`); fixed sets of values (statuses, types) are `Literal[...]` built from a tuple in `const/`.
4. Model change → new Alembic migration in `alembic/versions/` (next number, `down_revision` = previous). It runs automatically when the API starts. Never edit a migration that is already on `main`; add a new one.

**Transactions:** managers never call `commit()`; they `flush()` (and `refresh()` when they need DB-generated values). `get_db` commits once per request and rolls back on error. Controllers and dependencies always take the session as `db: AsyncSession = db_session` (`app/api/deps.py`, scope `function`), never `Depends(get_db)`: this commits before the response is sent and keeps one shared session per request.

**Errors and logs:** use `logging.getLogger(__name__)`, never `print`. Details of a failure (exception, internal URLs) go to the log; the client gets a short message from `const/messages.py`.

**Database queries:** a lookup that can match several rows uses `order_by(...)` + `limit(1)` / `.scalars().first()`, never `scalar_one_or_none()`. User input in `ilike` goes through `contains_pattern()` with `escape=LIKE_ESCAPE_CHAR` (`app/core/sql.py`). Bad user data must end as 400/404, never 500.

### Frontend: where what goes

| **Path** | **Does** |
| --- | --- |
| `src/api/client.js` | `apiFetch`: the only place that calls `fetch`; adds the token, parses errors, logs out on 401 |
| `src/api/<resource>Api.js` | Thin functions 1:1 with backend endpoints of one controller (e.g. `invoiceApi.js` ↔ `controllers/invoices.py`) |
| `src/pages/` | Screens; call only functions from `src/api/*Api.js` |
| `src/const/` | Constants (API base URL, endpoint paths, keys) |

Logic shared by several screens (combining requests, state) goes into a hook in `src/hooks/` when it is needed, not into the page.
