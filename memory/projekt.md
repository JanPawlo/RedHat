# Projekt

## Wyzwanie

Collabothon 2026 (Commerzbank), challenge Red Hat „Autonomous CFO”: asystent CFO oparty na AI dla małych i średnich firm. Szczegóły, wymagania i punktacja: `wyzwanie.md`.

## Temat

Inteligentny asystent CFO dla MŚP monitorujący płynność finansową (Liquidity Agent), prognozujący stan konta i generujący wytłumaczalne rekomendacje finansowe (Action Cards: limity kredytowe, bufor płynności, zarządzanie wydatkami). Analiza oparta na wyciągach bankowych (przykładowo Commerzbank / Pizzeria Amalfi), z opcjonalnym modułem faktur KSeF.

## Źródła

- Repo: https://github.com/JanPawlo/RedHat
- Notatki z brainstormingu w Figmie (Figma Spec): https://www.figma.com/spec/XcQ8glduBgAVS43S1A06o7/Notatki-z-brainstormingu
  - ostatnia synchronizacja do `pomysly.md`: 2026-11-20

## Stack technologiczny

- Szczegółowy opis w `TECH_STACK.md`.
- **Backend:** Python 3.11, FastAPI, Pydantic v2, Pandas (analiza finansowa).
- **Baza danych i migracje:** PostgreSQL 16 + Alembic (SQLAlchemy 2.0).
- **Frontend:** React 18, Vite, TailwindCSS, Recharts, Lucide Icons.
- **Środowisko i wdrożenie:** `docker-compose` lokalnie, kontenery na Red Hat OpenShift, modele open-weights (Granite / Mistral / Qwen) wdrożone na Red Hat OpenShift AI (RHOAI vLLM / MaaS).
