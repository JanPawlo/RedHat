# Decisions

Format: `- YYYY-MM-DD: decision (why)`

- 2026-11-20: We keep the project memory in the `memory/` folder in the repo as plain Markdown (part of the team uses Gemini and ChatGPT rather than Claude Code, so the context must be tool-independent).
- 2026-11-20: Tech stack: Python backend (FastAPI + Pydantic + Pandas), PostgreSQL with Alembic migrations, React frontend (Vite + TailwindCSS + Recharts). Local development via `docker-compose`, production deployment to Red Hat OpenShift with open-weights model on RHOAI (FastAPI integrates natively with vLLM / OpenAI-compatible endpoint). Documented in `TECH_STACK.md`.
- 2026-11-20: Scope prioritization: KSeF placed as an optional secondary module to focus squarely on the core Liquidity Agent challenge with bank statements (Pizzeria Amalfi) and explainable Action Cards.
- 2026-11-20: Database architecture: Single-tenant / per-company deployment (dedicated instance for the business on OpenShift, no multi-tenant `companies` table). Company parameters stored in `company_profile`, and transactions use normalized banking fields plus an extensible `metadata_payload` (JSONB) column so the schema is not constrained to fixed CSV columns.
- 2026-11-20: The main features are a card deck with swipe (right = yes, left = no), "Ask why", which flips the card and opens a chat, and cash forecast charts. Description: `spec/funkcjonalnosci.md` (this follows from the first interface sketch).
- 2026-11-20: The cash forecast is on the main screen as one of the most important elements; the graphics from the sketches are preliminary and will change.
- 2026-11-20: The app is general-purpose, for various companies, not tailored to one specific company (Pizzeria Amalfi is just one example dataset).

## LLM model choice (proposal, awaiting team approval)

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

**Proposal:** replace `llama-32-3b-instruct` with **`qwen3-8b`**. It has the best combination of tool calling and Polish (the user and the invoices from KSeF, Poland's national e-invoicing system, are in Polish), and it fits on the L4 with room to spare. As a fallback we take **`granite-3.3-8b-instruct`**, if Qwen fails or we want to show the jury a Red Hat/IBM model. Since there is only one GPU, guardrails and embeddings must run on CPU (see `spec/openshift-ai.md`).

**When deploying `qwen3-8b`:** in vLLM set `--enable-auto-tool-choice --tool-call-parser=hermes` (for Qwen3 the parser is `hermes`, not `llama3_json` as with the current Llama). Choose `max_model_len` so that the KV cache fits in the roughly 8 GB left on the L4. Then repeat the test from `spec/openshift-ai.md`: the question about a 10,000 EUR oven and the call to the `get_balance` tool.

Sources: [Red Hat AI validated models](https://docs.redhat.com/en/documentation/red_hat_ai/3/html-single/validated_models), [model support matrix](https://docs.redhat.com/en/documentation/red_hat_ai/3/html/validated_models/model-support-matrix_validated-models), [Red Hat AI Q3 2026](https://www.redhat.com/rhdc/managed-files/Red-Hat-AI-Q3-2026-Whats-New-Whats-Next.pdf).

## Rejected

Format: `- YYYY-MM-DD: idea (reason for rejection)`

- 2026-11-20: Central database with a multi-tenant `companies` table (the app operates as an autonomous, local financial assistant dedicated to a specific company deployment).
