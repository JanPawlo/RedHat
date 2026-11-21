# Decisions

Format: `- YYYY-MM-DD: decision (why)`

- 2026-11-20: We keep the project memory in the `memory/` folder in the repo as plain Markdown (part of the team uses Gemini and ChatGPT rather than Claude Code, so the context must be tool-independent).
- 2026-11-20: Tech stack: Python backend (FastAPI + Pydantic + Pandas), PostgreSQL with Alembic migrations, React frontend (Vite + TailwindCSS + Recharts). Local development via `docker-compose`, production deployment to Red Hat OpenShift with open-weights model on RHOAI (FastAPI integrates natively with vLLM / OpenAI-compatible endpoint). Documented in `TECH_STACK.md`.
- 2026-11-20: Scope prioritization: KSeF placed as an optional secondary module to focus squarely on the core Liquidity Agent challenge with bank statements (Pizzeria Amalfi) and explainable Action Cards.
- 2026-11-20: Implemented the Invoice & Receipt Validation Engine with LLM tool-calling API support (`/api/v1/invoices/validate` and `/api/v1/invoices/tools/llm-schema`). It enforces deterministic fraud checks (IBAN mismatch detection, duplicate detection), math verification (net + VAT == gross), vendor price spike detection, liquidity buffer impact, and Skonto early discount opportunity detection, feeding directly into the Decision Card swipe deck.
- 2026-11-20: Database architecture: Single-tenant / per-company deployment (dedicated instance for the business on OpenShift, no multi-tenant `companies` table). Company parameters stored in `company_profile`, and transactions use normalized banking fields plus an extensible `metadata_payload` (JSONB) column so the schema is not constrained to fixed CSV columns.
- 2026-11-20: The main features are a card deck with swipe (right = yes, left = no), "Ask why", which flips the card and opens a chat, and cash forecast charts. Description: `spec/funkcjonalnosci.md` (this follows from the first interface sketch).
- 2026-11-20: The cash forecast is on the main screen as one of the most important elements; the graphics from the sketches are preliminary and will change.
- 2026-11-20: The app is general-purpose, for various companies, not tailored to one specific company (Pizzeria Amalfi is just one example dataset).
- 2026-11-21: The organizers' original files moved from `materials/` to `memory/reference/` (all project knowledge, including source files, lives in one place). Coding rules for people and assistants are in `AGENTS.md` ("Writing code"), the project structure in `README.md`.

- 2026-11-21: Frontend main screen shows one centered decision card. Tap flips it; a decision needs drag past the edge (or a side button) held for 0.6 s, 1.2 s above the amount set in Rules, then a Confirmation screen. Keyboard shortcuts removed. (Against accidental decisions, per the new Figma.)
- 2026-11-21: "Ledger" replaced by "History" (every decision as a card, with the AI answer saved at decision time). The Autopilot toggle moved from the sidebar to the Rules page.
- 2026-11-21: Main card is portrait again (about 2:3). The side "Swipe left / Swipe right" buttons are gone: you decide only by dragging the card (front or back, grabbed anywhere) and holding; a green (right) or red (left) gradient overlay shows the decision label and the hold progress. An animated hand under the card hints at the gesture. (UX feedback: buttons duplicated the gesture, the card looked too flat.)
- 2026-11-21 (replaces the overlay above): no gradient on the card itself while dragging. Desktop (≥1024 px): two frames the size of the card beside it, NO (left) and YES (right), with the decision and its consequences (`outcomes` on each card); the frame's red/green gradient grows as the card is dragged toward it. Phone: the card switches to the outcome view (YES/NO + consequences + hold progress) and gets a green (right) or red (left) glow.
- 2026-11-21: "Live data" page removed (it was the old dashboard kept only to show API data; the API files stay).
- 2026-11-21: Alerts are only in the notifications panel under the bell (top right); no alert banner on the dashboard. Dashboard search and the sidebar company switcher removed (single-company deployment, see the database decision above).
- 2026-11-21: Analysis shows Q4 (1 Oct – 31 Dec): weekly money in vs out with vertical markers for larger payments in/out (rent, payroll, ZUS, VAT, client invoices); December is the engine's forecast. Invoices got a donut "Where the money goes" (expense categories).
- 2026-11-21: New page **Advisor** (`/advisor`): the owner adds text notes, voice messages (recorded in the browser, live transcript where the browser supports it) and meeting recordings (upload + key points), and chats with the model, which reads them together with the engine's numbers (when to buy, risks, "are you sure"). Text is saved in the browser; audio only for the session. There is no speech-to-text for uploaded recordings yet.
- 2026-11-21: In History every decision can be changed (approve ↔ decline); the earlier choice is kept in the entry (`changes`).
- 2026-11-21: The AI explanation for every card is generated in the background at app start and cached in the browser (localStorage, per card id + hash of its facts), so the model is not asked again after a refresh. (The model on the L4 is too slow to answer live when a card is flipped.)

## LLM model choice

As of: 2026-11-20. The cluster has **1× NVIDIA L4, 24 GB VRAM**, which only one pod can use at a time. We deploy models from `modelcar-catalog`. Details, the list of models in the catalog and the test of the current `llama-32-3b-instruct` (too weak, does not call tools) are in `spec/openshift-ai.md`. In practice the limit is a 7–8B model in FP16/BF16.

| | **Qwen** (Alibaba) | **Granite** (IBM) | **Mistral** |
| --- | --- | --- | --- |
| Catalog candidates that fit on the L4 | `qwen3-8b` (~16 GB) | `granite-3.3-8b-instruct` (~16 GB), `granite-4.0-h-tiny` (lightweight MoE) | only `ministral-3-3b-instruct-2512` (3B, too weak for an agent) |
| Ruled out by the 24 GB limit | `qwen3-14b`, `qwen3.8-27b` | `granite-4.0-h-small` | larger Mistrals are not in the catalog |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| Tool calling / agents | very good, well supported in vLLM | good, model designed for agentic workflows in companies | good |
| Polish language | good (multilingual model) | weak, Polish is not on the list of officially supported languages | good |
| Red Hat validation | in the validated models catalog | validated (FP8 versions on RHOAI 3.3); it is Red Hat/IBM's "home" model, which the jury may like | in the validated models catalog |
| Risk | low; 8B leaves about 8 GB for the KV cache | answers in Polish may be weak | the catalog has no version suitable for an agent |

**Decision (2026-11-21, deployed): `qwen3-8b` replaced `llama-32-3b-instruct` on the cluster; details and test in `spec/openshift-ai.md`.** Original proposal: replace `llama-32-3b-instruct` with **`qwen3-8b`**. It has the best combination of tool calling and Polish (the user and the invoices from KSeF, Poland's national e-invoicing system, are in Polish), and it fits on the L4 with room to spare. As a fallback we take **`granite-3.3-8b-instruct`**, if Qwen fails or we want to show the jury a Red Hat/IBM model. Since there is only one GPU, guardrails and embeddings must run on CPU (see `spec/openshift-ai.md`).

**When deploying `qwen3-8b`:** in vLLM set `--enable-auto-tool-choice --tool-call-parser=hermes` (for Qwen3 the parser is `hermes`, not `llama3_json` as with the current Llama). Choose `max_model_len` so that the KV cache fits in the roughly 8 GB left on the L4. Then repeat the test from `spec/openshift-ai.md`: the question about a 10,000 EUR oven and the call to the `get_balance` tool.

Sources: [Red Hat AI validated models](https://docs.redhat.com/en/documentation/red_hat_ai/3/html-single/validated_models), [model support matrix](https://docs.redhat.com/en/documentation/red_hat_ai/3/html/validated_models/model-support-matrix_validated-models), [Red Hat AI Q3 2026](https://www.redhat.com/rhdc/managed-files/Red-Hat-AI-Q3-2026-Whats-New-Whats-Next.pdf).

## Code structure and auth (2026-11-21, branch `feature/auth`)

- Backend layers: `app/api/v1/controllers/<resource>.py` (one router per resource; only access check + HTTP errors) → `app/managers/<resource>_manager.py` (all logic and DB queries) → `app/services/` (parser, invoice validator, LLM; unchanged).
- Every endpoint except `/auth/login` and `/auth/register` requires a JWT: parameter `current_user: User = Depends(get_current_user)` in the controller. `/health` (outside `/api/v1`) stays public.
- JWT is issued by the API (`app/core/security.py`, HS256, `sub` = user id).
- HTTP error helpers live in `app/api/errors.py`; managers return `None` when something is not found, the controller turns it into 404.
- Constants: backend in `app/const/`, frontend in `src/const/`. No magic strings in code.
- Frontend: only `src/api/client.js` (`apiFetch`) calls `fetch`; it adds the Bearer token and logs out on 401 (other errors are shown, not logged out). One `src/api/<resource>Api.js` per backend controller; pages call only these.
- One `/api` prefix end to end: frontend calls `/api/v1/...`, Vite and nginx forward `/api` unchanged. Health is `/api/health` (and `/health` for probes).
- DB writes: managers `flush()`, only `get_db` commits (one transaction per request). `POST /invoices/validate` saves a card only with `auto_create_card=true`.
- Agent action status flow: pending → simulated/approved/rejected, simulated → approved/rejected, approved → executed/rejected/pending (undo), rejected → pending (undo), executed is final. Other changes return 409.
- Registration is open only in development unless `ALLOW_REGISTRATION` is set; on a shared deployment use the admin account.
- JSON columns are JSONB on PostgreSQL (migration 005). Without a bank account the invoice validator returns `liquidity_safe = null` and a `NO_ACCOUNT_DATA` flag instead of assuming a balance.

## Rejected

Format: `- YYYY-MM-DD: idea (reason for rejection)`

- 2026-11-20: Central database with a multi-tenant `companies` table (the app operates as an autonomous, local financial assistant dedicated to a specific company deployment).
