# Decyzje

Format: `- RRRR-MM-DD: decyzja (dlaczego)`

- 2026-11-20: Pamięć projektu trzymamy w folderze `memory/` w repo jako zwykły Markdown (część zespołu używa Gemini i ChatGPT, a nie Claude Code, więc kontekst musi być niezależny od narzędzia).
- 2026-11-20: Stack technologiczny: Backend w Python (FastAPI + Pydantic + Pandas), baza PostgreSQL z migracjami przez Alembic, frontend w React (Vite + TailwindCSS + Recharts). Do rozwoju lokalnego `docker-compose`, a docelowo wdrożenie na Red Hat OpenShift z modelem open-weights na RHOAI (FastAPI idealnie integruje się z endpointem vLLM i bibliotekami AI).
- 2026-11-20: Zakres KSeF odłożony na dalszy plan jako opcjonalny moduł (główny fokus to wyzwanie Liquidity Agent z danymi bankowymi Pizzeria Amalfi i wytłumaczalne Action Cards w UI).

## Odrzucone

Format: `- RRRR-MM-DD: pomysł (powód odrzucenia)`

- (brak)
