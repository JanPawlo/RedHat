# Decyzje

Format: `- RRRR-MM-DD: decyzja (dlaczego)`

- 2026-11-20: Pamięć projektu trzymamy w folderze `memory/` w repo jako zwykły Markdown (część zespołu używa Gemini i ChatGPT, a nie Claude Code, więc kontekst musi być niezależny od narzędzia).
- 2026-11-20: Stack technologiczny: Backend w Python (FastAPI + Pydantic + Pandas), baza PostgreSQL z migracjami przez Alembic, frontend w React (Vite + TailwindCSS + Recharts). Do rozwoju lokalnego `docker-compose`, a docelowo wdrożenie na Red Hat OpenShift z modelem open-weights na RHOAI (FastAPI idealnie integruje się z endpointem vLLM i bibliotekami AI).
- 2026-11-20: Zakres KSeF odłożony na dalszy plan jako opcjonalny moduł (główny fokus to wyzwanie Liquidity Agent z danymi bankowymi Pizzeria Amalfi i wytłumaczalne Action Cards w UI).
- 2026-11-20: Architektura bazy: Single-tenant / per-company (instancja bazy i aplikacji jest lokalna dla danej firmy/klienta na klastrze, brak tabeli multi-tenant `companies`). Dane firmy w `company_profile`, a transakcje mają znormalizowane kolumny bankowe oraz kolumnę `metadata_payload` (JSONB), aby nie ograniczać się na sztywno wyłącznie do 11 kolumn z przykładowego CSV Amalfi.
- 2026-11-20: Główne funkcjonalności to talia kart ze swipe (prawo = tak, lewo = nie), „Ask why”, które odwraca kartę i otwiera czat, oraz wykresy prognozy gotówki. Opis: `funkcjonalnosci.md` (tak wynika z pierwszego szkicu interfejsu).
- 2026-11-20: Prognoza gotówki jest na ekranie głównym jako jeden z najważniejszych elementów; grafika ze szkiców jest wstępna i będzie się zmieniać.
- 2026-11-20: Aplikacja jest ogólna, dla różnych firm, a nie pod jedną konkretną (Pizzeria Amalfi to tylko jeden z przykładów danych).

## Wybór modelu LLM (propozycja, czeka na zatwierdzenie zespołu)

Stan wiedzy: 2026-11-20. Klastra jeszcze nie widzieliśmy, więc nie znamy typu i ilości pamięci GPU (wiemy tylko, że to 32 CPU i 128 GB RAM). Ostateczny wybór zależy od tego, co jest w katalogu modeli RHOAI 3.5 i ile VRAM ma GPU.

| | **Qwen** (Alibaba) | **Granite** (IBM) | **Mistral** |
| --- | --- | --- | --- |
| Kandydaci | Qwen3 8B / 14B; Qwen 3.6, jeśli jest w katalogu RHOAI 3.5 | Granite 4.0-H-Tiny (7B MoE, ok. 1B aktywnych), Granite 4.0-H-Small (32B MoE, 9B aktywnych) | Ministral 3 8B / 14B, Mistral Small 3.2 (24B); Mistral Small 4 (119B MoE) jest za duży na jedno GPU |
| Licencja | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| Tool calling / agenci | bardzo dobre, dobrze wspierane w vLLM | dobre, model projektowany pod agentowe workflow w firmach | dobre |
| Język polski | dobry (model wielojęzyczny) | słaby, polskiego nie ma na liście oficjalnie wspieranych języków | dobry |
| Walidacja Red Hat | jest w katalogu validated models | walidowany (wersje FP8 na RHOAI 3.3); to „domowy” model Red Hat/IBM, co może się podobać jury | jest w katalogu validated models |
| Wymagania sprzętowe | 8B mieści się na każdym GPU; 14B potrzebuje ok. 32 GB VRAM albo kwantyzacji | Tiny jest bardzo lekki; Small w FP8 potrzebuje ok. 40 GB VRAM | 8B lekki; 24B potrzebuje ok. 48 GB VRAM albo FP8 |
| Ryzyko | niskie | odpowiedzi po polsku mogą być słabe | Small 4 nie zmieści się na klastrze |

**Propozycja:** głównym modelem jest **Qwen3** (8B, a jeśli GPU pozwoli, 14B lub Qwen 3.6). Za tym wyborem przemawia najlepsza kombinacja tool callingu, polskiego (użytkownik i faktury KSeF są po polsku) oraz małych wymagań sprzętowych. Zapasowym modelem jest **Granite 4.0-H-Tiny**, jeśli chcemy pokazać jury model Red Hat/IBM albo potrzebujemy czegoś bardzo lekkiego, np. do klasyfikacji faktur, gdzie język ma mniejsze znaczenie.

**Do sprawdzenia po dostaniu klastra:** typ GPU i ilość VRAM, lista modeli w katalogu RHOAI, to, czy model jest serwowany przez vLLM (bonus +1), oraz włączenie tool callingu w vLLM (parser odpowiedni dla danego modelu).

Źródła: [Red Hat AI validated models](https://docs.redhat.com/en/documentation/red_hat_ai/3/html-single/validated_models), [macierz wsparcia modeli](https://docs.redhat.com/en/documentation/red_hat_ai/3/html/validated_models/model-support-matrix_validated-models), [Red Hat AI Q3 2026](https://www.redhat.com/rhdc/managed-files/Red-Hat-AI-Q3-2026-Whats-New-Whats-Next.pdf).

## Odrzucone

Format: `- RRRR-MM-DD: pomysł (powód odrzucenia)`

- 2026-11-20: Centralna baza z tabelą `companies` i kluczami obcymi do firm (aplikacja działa jako autonomiczny, lokalny asystent finansowy dedykowany dla konkretnej firmy / wdrożenia, a nie multi-tenant SaaS).
