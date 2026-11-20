# Project

## Challenge

Collabothon 2026 (Commerzbank), Red Hat challenge "Autonomous CFO": an AI-based CFO assistant for small and medium-sized companies. Details, requirements and scoring: `spec/wyzwanie.md`.

## Topic

An intelligent CFO assistant for SMEs monitoring cash liquidity (Liquidity Agent), forecasting account balances, and generating explainable financial recommendations (Decision Cards: credit lines, liquidity buffers, spending management). Analysis is based on bank statements (e.g. Commerzbank / Pizzeria Amalfi), with an optional KSeF invoice module.

## Sources

- Repo: https://github.com/JanPawlo/RedHat
- Brainstorming notes in Figma (Figma Spec): https://www.figma.com/spec/XcQ8glduBgAVS43S1A06o7/Notatki-z-brainstormingu
  - last sync to `decisions/pomysly.md`: 2026-11-20

## Tech stack

- Detailed architecture in `TECH_STACK.md`.
- **Backend:** Python 3.11, FastAPI, Pydantic v2, Pandas (financial modeling).
- **Database & Migrations:** PostgreSQL 16 + Alembic (SQLAlchemy 2.0).
- **Frontend:** React 18, Vite, TailwindCSS, Recharts, Lucide Icons.
- **Environment & Deployment:** `docker-compose` locally, containers deployed on Red Hat OpenShift, open-weights models (Qwen3 / Granite) served on Red Hat OpenShift AI (RHOAI vLLM / MaaS).
