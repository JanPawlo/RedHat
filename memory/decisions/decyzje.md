# Decyzje

Format: `- RRRR-MM-DD: decyzja (dlaczego)`

- 2026-11-20: Pamięć projektu trzymamy w folderze `memory/` w repo jako zwykły Markdown (część zespołu używa Gemini i ChatGPT, a nie Claude Code, więc kontekst musi być niezależny od narzędzia).
- 2026-11-20: Główne funkcjonalności to talia kart ze swipe (prawo = tak, lewo = nie), „Ask why”, które odwraca kartę i otwiera czat, oraz wykresy prognozy gotówki. Opis: `spec/funkcjonalnosci.md` (tak wynika z pierwszego szkicu interfejsu).
- 2026-11-20: Prognoza gotówki jest na ekranie głównym jako jeden z najważniejszych elementów; grafika ze szkiców jest wstępna i będzie się zmieniać.
- 2026-11-20: Aplikacja jest ogólna, dla różnych firm, a nie pod jedną konkretną (Pizzeria Amalfi to tylko jeden z przykładów danych).

## Wybór modelu LLM (propozycja, czeka na zatwierdzenie zespołu)

Stan wiedzy: 2026-11-20. Klaster ma **1× NVIDIA L4, 24 GB VRAM**, które może używać tylko jeden pod naraz. Modele wdrażamy z `modelcar-catalog`. Szczegóły, lista modeli z katalogu i test obecnego `llama-32-3b-instruct` (za słaby, nie wywołuje narzędzi) są w `spec/openshift-ai.md`. W praktyce limit to model 7–8B w FP16/BF16.

| | **Qwen** (Alibaba) | **Granite** (IBM) | **Mistral** |
| --- | --- | --- | --- |
| Kandydaci z katalogu, które mieszczą się na L4 | `qwen3-8b` (~16 GB) | `granite-3.3-8b-instruct` (~16 GB), `granite-4.0-h-tiny` (lekki MoE) | tylko `ministral-3-3b-instruct-2512` (3B, za słaby do agenta) |
| Odpadają przez 24 GB | `qwen3-14b`, `qwen3.8-27b` | `granite-4.0-h-small` | większe Mistrale nie są w katalogu |
| Licencja | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| Tool calling / agenci | bardzo dobre, dobrze wspierane w vLLM | dobre, model projektowany pod agentowe workflow w firmach | dobre |
| Język polski | dobry (model wielojęzyczny) | słaby, polskiego nie ma na liście oficjalnie wspieranych języków | dobry |
| Walidacja Red Hat | jest w katalogu validated models | walidowany (wersje FP8 na RHOAI 3.3); to „domowy” model Red Hat/IBM, co może się podobać jury | jest w katalogu validated models |
| Ryzyko | niskie; 8B zostawia ok. 8 GB na KV cache | odpowiedzi po polsku mogą być słabe | w katalogu nie ma wersji, która nadaje się do agenta |

**Propozycja:** podmienić `llama-32-3b-instruct` na **`qwen3-8b`**. Ma najlepszą kombinację tool callingu i polskiego (użytkownik i faktury KSeF są po polsku), a na L4 mieści się z zapasem. Zapasowo bierzemy **`granite-3.3-8b-instruct`**, jeśli Qwen zawiedzie albo chcemy pokazać jury model Red Hat/IBM. Ponieważ GPU jest jedno, guardrails i embeddingi muszą iść na CPU (patrz `spec/openshift-ai.md`).

**Przy wdrożeniu `qwen3-8b`:** w vLLM ustawić `--enable-auto-tool-choice --tool-call-parser=hermes` (dla Qwen3 jest to parser `hermes`, a nie `llama3_json` jak przy obecnej Llamie). `max_model_len` dobrać tak, żeby KV cache zmieścił się w ok. 8 GB, które zostają na L4. Potem powtórzyć test z `spec/openshift-ai.md`: pytanie o piec za 10 000 EUR i wywołanie narzędzia `get_balance`.

Źródła: [Red Hat AI validated models](https://docs.redhat.com/en/documentation/red_hat_ai/3/html-single/validated_models), [macierz wsparcia modeli](https://docs.redhat.com/en/documentation/red_hat_ai/3/html/validated_models/model-support-matrix_validated-models), [Red Hat AI Q3 2026](https://www.redhat.com/rhdc/managed-files/Red-Hat-AI-Q3-2026-Whats-New-Whats-Next.pdf).

## Odrzucone

Format: `- RRRR-MM-DD: pomysł (powód odrzucenia)`

- (brak)
