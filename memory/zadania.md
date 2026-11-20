# Tasks

- [x] ~~Send the organizers the repo URL to get access to the OpenShift AI environment~~: we got the environment on 2026-11-20 (addresses in `spec/openshift-ai.md`)
- [x] Choose at least one of the 4 use cases: **Liquidity Agent** chosen as the core use case (cash flow forecast & Commerzbank credit line proposals).
- [x] Decide what to do with the KSeF ideas: KSeF placed as an optional secondary module to focus on the core hackathon criteria.
- [x] Settle the tech stack & architecture (Python FastAPI, PostgreSQL + Alembic, React/Vite/Tailwind, Docker Compose, OpenShift); documented in `TECH_STACK.md`.
- [x] Design single-tenant database schema & initial Alembic migration (accounts, transactions with `metadata_payload`, forecasts, agent actions).
- [x] Implement bank statement CSV parser (flexible formats, CHF/EUR FX conversion) & seeding script.
- [x] Implement domain math & liquidity simulation verification script (`backend/app/services/simulate_demo.py`).
- [ ] Review `spec/funkcjonalnosci.md` as a team and approve the MVP scope (P1) in `decisions/decyzje.md`.
- [ ] Deploy model on the cluster (switch from weak 3B model to `qwen3-8b` or `granite-3.3-8b-instruct`) as detailed in `decisions/decyzje.md`.
- [ ] Choose 2–4 bonuses that fit the stack (vLLM already included, MaaS, NeMo Guardrails, Dev Spaces).
- [ ] At the end, fill in the Project Card (`materials/project-card-fillable.pdf`).
