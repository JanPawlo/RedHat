# Decyzje

Format: `- RRRR-MM-DD: decyzja (dlaczego)`

- 2026-11-20: Pamięć projektu trzymamy w folderze `memory/` w repo jako zwykły Markdown (część zespołu używa Gemini i ChatGPT, a nie Claude Code, więc kontekst musi być niezależny od narzędzia).
- 2026-11-20: Stack technologiczny: Backend w Python (FastAPI + Pydantic + Pandas), baza PostgreSQL z migracjami przez Alembic, frontend w React (Vite + TailwindCSS + Recharts). Do rozwoju lokalnego `docker-compose`, a docelowo wdrożenie na Red Hat OpenShift z modelem open-weights na RHOAI (FastAPI idealnie integruje się z endpointem vLLM i bibliotekami AI).
- 2026-11-20: Zakres KSeF odłożony na dalszy plan jako opcjonalny moduł (główny fokus to wyzwanie Liquidity Agent z danymi bankowymi Pizzeria Amalfi i wytłumaczalne Action Cards w UI).
- 2026-11-20: Architektura bazy: Single-tenant / per-company (instancja bazy i aplikacji jest lokalna dla danej firmy/klienta na klastrze, brak tabeli multi-tenant `companies`). Dane firmy w `company_profile`, a transakcje mają znormalizowane kolumny bankowe oraz kolumnę `metadata_payload` (JSONB), aby nie ograniczać się na sztywno wyłącznie do 11 kolumn z przykładowego CSV Amalfi.

## Odrzucone

Format: `- RRRR-MM-DD: pomysł (powód odrzucenia)`

- 2026-11-20: Centralna baza z tabelą `companies` i kluczami obcymi do firm (aplikacja działa jako autonomiczny, lokalny asystent finansowy dedykowany dla konkretnej firmy / wdrożenia, a nie multi-tenant SaaS).
