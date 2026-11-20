# Tech Stack & Architecture Guide

This document outlines the technology stack, project directory layout, and deployment model for the **Autonomous CFO** hackathon project (Red Hat & Commerzbank Collabothon 2026).

---

## 1. High-Level Architecture

```
                      +---------------------------------------+
                      |       Web Browser (User / Owner)      |
                      +---------------------------------------+
                                          |
                                          | HTTP / REST
                                          v
                      +---------------------------------------+
                      |         Frontend (React + Vite)       |
                      |   - Metric Cards & Liquidity Curves   |
                      |   - Action Cards (Explain & Approve)  |
                      |   - TailwindCSS + Recharts            |
                      +---------------------------------------+
                                          |
                                          | /api/ (JSON / REST)
                                          v
                      +---------------------------------------+
                      |         Backend (FastAPI / Python)    |
                      |   - Financial Calculations (Pandas)   |
                      |   - Liquidity Forecasting Engine      |
                      |   - AI Agent Orchestration            |
                      +-------------------+-------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v                                   v
        +-------------------------------+   +-------------------------------+
        |    Database (PostgreSQL)      |   |  OpenShift AI (RHOAI / vLLM)  |
        | - Single-tenant / per-company |   | - Open-weights model (Granite)|
        | - Company profile & parameters|   | - Explainable recommendations |
        | - Accounts & Ledger           |   | - MaaS / vLLM REST Endpoint   |
        | - Extensible JSONB metadata   |   |                               |
        | - Forecasts & Agent Actions   |   |                               |
        +-------------------------------+   +-------------------------------+
```

---

## 2. Technology Choices & Justification

| Layer | Technology | Justification |
|---|---|---|
| **Backend Framework** | **Python 3.11 + FastAPI** | Native async for LLM response streaming, Pydantic type safety for financial data, high-performance REST APIs, auto-generated Swagger UI (`/docs`). |
| **Data & Financial Math**| **Pandas + NumPy** | Standard tools for calculating running balances, moving averages, and cash-flow projections from bank statement CSVs. |
| **Database** | **PostgreSQL 16** | ACID-compliant relational storage for bank accounts, transactions, forecast snapshots, and human-in-the-loop action audit logs. |
| **DB Migrations** | **Alembic + SQLAlchemy 2.0** | Python-native migration system. Seamless integration into container startup (`alembic upgrade head`), version-controlled migrations without Java dependencies. |
| **Frontend Framework** | **React 18 + Vite** | Fast build times, instant Hot Module Reloading (HMR), clean component ecosystem. |
| **UI Styling & Icons** | **TailwindCSS + Lucide** | Rapid design of accessible, modern UI ("Innovations for all generations" theme) with clear visual hierarchy. |
| **Visualizations** | **Recharts** | Responsive SVG charts for daily balances, overdraft thresholds, and forecast horizons. |
| **Local Environment** | **Docker Compose / Podman** | One-command local startup (`docker compose up`) of PostgreSQL, FastAPI, and React for full offline development. |
| **Production Target** | **Red Hat OpenShift (RHOAI)** | Hard requirement for hackathon scoring: backend and database deployed to OpenShift cluster; OSS models served via OpenShift AI. |

---

## 3. Repository Directory Structure

```text
projekt_redhat/
├── .gitignore                     # Git ignore rules for Python, Node, Postgres, env
├── docker-compose.yml             # Local multi-container orchestrator
├── TECH_STACK.md                  # This architecture and tech stack reference
├── AGENTS.md                      # Assistant operating guidelines (memory-first)
├── README.md                      # Repository entry point
│
├── backend/                       # Python FastAPI Backend
│   ├── app/
│   │   ├── api/                   # API route handlers (v1 endpoints)
│   │   ├── core/                  # Configuration, database session & engine
│   │   ├── models/                # SQLAlchemy ORM models (Accounts, Transactions, etc.)
│   │   ├── schemas/               # Pydantic schemas (request/response validation)
│   │   ├── services/              # Domain logic (Liquidity math, AI agent logic)
│   │   └── main.py                # FastAPI entry point
│   ├── alembic/                   # Database migrations
│   │   ├── versions/              # Migration scripts (e.g. V1, V2)
│   │   ├── env.py                 # Alembic environment configuration
│   │   └── script.py.mako         # Migration template
│   ├── alembic.ini                # Alembic CLI configuration
│   ├── Dockerfile                 # OpenShift-compatible container image build
│   ├── requirements.txt           # Python package dependencies
│   └── .env.example               # Environment variables template
│
├── frontend/                      # React SPA Frontend
│   ├── public/                    # Static assets
│   ├── src/
│   │   ├── assets/                # Images & SVGs
│   │   ├── components/            # Reusable UI cards, tables, charts
│   │   ├── App.jsx                # Main dashboard view
│   │   ├── index.css              # Tailwind base imports
│   │   └── main.jsx               # React DOM bootstrap
│   ├── Dockerfile                 # Multi-stage build (Vite -> Nginx)
│   ├── nginx.conf                 # Production Nginx reverse proxy configuration
│   ├── package.json               # NPM scripts and dependencies
│   ├── vite.config.js             # Vite configuration with backend proxy
│   └── tailwind.config.js         # Tailwind theme configuration
│
├── memory/                        # Living project memory (Plain Markdown, Polish)
│   ├── README.md                  # Memory index and contribution rules
│   ├── projekt.md                 # Project goals and active stack decisions
│   ├── wyzwanie.md                # Hackathon rules, scoring criteria & RHOAI guide
│   ├── dane-przykladowe.md        # Amalfi dataset breakdown & financial traps
│   ├── decyzje.md                 # Architectural & business decisions log
│   ├── zadania.md                 # Hackathon task backlog
│   ├── pomysly.md                 # Feature brainstorms & questions
│   └── firmy/                     # Target SME customer profiles (Pizzeria Amalfi, etc.)
│
└── materials/                     # Original hackathon PDFs, slides & raw sample data
    └── sample-data/               # Pizzeria Amalfi CSV, DOCX scenario & PNG chart
```

---

## 4. Running Locally

### Option A: Via Docker Compose (Recommended)

1. Make sure Docker (or Podman) is running.
2. In the project root, run:
   ```bash
   docker compose up --build
   ```
3. Open your browser:
   - **Frontend:** http://localhost:3000
   - **Backend API:** http://localhost:8000
   - **Swagger Docs:** http://localhost:8000/docs
   - **PostgreSQL:** `localhost:5432` (`user: cfo_user`, `pass: cfo_password`, `db: cfo_db`)

### Option B: Local Native Development

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## 5. OpenShift & OpenShift AI (RHOAI) Readiness

- **OpenShift Security (Arbitrary UIDs):** Both `backend/Dockerfile` and `frontend/Dockerfile` configure root-group write permissions (`chmod -R g=u` / `chmod -R 777`) so they run without issues under OpenShift's default non-root random UID security context.
- **RHOAI Model Integration:** The backend includes `MODEL_ENDPOINT_URL` configuration to point directly to the vLLM / MaaS OpenAI-compatible endpoint deployed in the RHOAI single-node cluster.
