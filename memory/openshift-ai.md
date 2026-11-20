# OpenShift AI: co z dokumentacji nam się przyda

Stan na 2026-11-20. docs.redhat.com blokuje automatyczne pobieranie, więc źródłem są: upstream dokumentacja Open Data Hub (archiwalna kopia, RHOAI 3.5 może się różnić) i kurs Red Hat „vLLM on OpenShift AI”. Co niezweryfikowane, jest oznaczone „(?)”.

## Nasz klaster

- OpenShift AI Dashboard: https://data-science-gateway.apps.ocp.4xxsd.sandbox2810.opentlc.com
- OpenShift Console: https://console-openshift-console.apps.ocp.4xxsd.sandbox2810.opentlc.com
- API (dla `oc login`): https://api.ocp.4xxsd.sandbox2810.opentlc.com:6443
- Login i hasło: w wiadomości od organizatorów. **Nie wpisywać ich do repo.**
- Single node (AWS `g6.8xlarge`), 32 CPU, 128 GB RAM.
- **GPU (sprawdzone na klastrze 2026-11-20): 1× NVIDIA L4, 24 GB VRAM** (architektura Ada Lovelace, compute 8.9). Brak współdzielenia (`sharing-strategy: none`), więc **GPU może używać tylko jeden pod naraz**.
- **GPU jest już zajęte** przez przykładowy model wdrożony przez organizatorów 2026-11-19:
  - projekt `my-first-model`, InferenceService `llama-32-3b-instruct` (Llama 3.2 3B Instruct, runtime vLLM `registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.2.4`),
  - model ładowany z OCI: `oci://quay.io/redhat-ai-services/modelcar-catalog:llama-3.2-3b-instruct`,
  - adres w klastrze: `http://llama-32-3b-instruct-predictor.my-first-model.svc.cluster.local:8080` (API zgodne z OpenAI, ścieżki `/v1/...`).
  - Możemy go od razu używać z aplikacji albo usunąć i wdrożyć własny model. Dwóch modeli na GPU naraz nie uruchomimy.
  - Inne modele w tym samym formacie: `quay.io/redhat-ai-services/modelcar-catalog:<nazwa>` (lista niżej).

### Test modelu `llama-32-3b-instruct` (2026-11-20)

- **Działa i odpowiada szybko** (ok. 2,5 s na krótką odpowiedź). `GET /v1/models` i `POST /v1/chat/completions` działają, `max_model_len` = 20 000 tokenów.
- vLLM jest uruchomiony z `--enable-auto-tool-choice --tool-call-parser=llama3_json`, więc **wywoływanie narzędzi jest włączone**.
- **Jakość słaba:**
  - na pytanie „pizzeria ma 33 000 EUR, czynsz 3800 EUR/mies., czy stać ją na piec za 10 000 EUR?” odpowiedział błędnie (że nie stać, bo „10 000 EUR miesięcznie”),
  - z narzędziem `get_balance` w zapytaniu **nie wywołał go**, tylko odpisał tekstem „możesz użyć funkcji get_balance”.
  - Do agenta CFO ten model jest za słaby; trzeba podmienić na 7–8B.
- Dostęp:
  - **brak zewnętrznego route'a**;
  - w klastrze port 80 serwisu `llama-32-3b-instruct-predictor` trafia prosto do vLLM, bez tokena;
  - port 8443 idzie przez `kube-rbac-proxy` i wymaga tokena;
  - z zewnątrz testowaliśmy przez proxy API Kubernetes z tokenem admina.

### Modele dostępne w `modelcar-catalog` (Quay, 2026-11-20)

Co sensownie zmieści się na L4 24 GB (FP16 / BF16):

| **Model** | **Rozmiar** | **Uwagi** |
| --- | --- | --- |
| `qwen3-8b` | 8B (~16 GB) | **Faworyt:** dobre wywoływanie narzędzi, tryb rozumowania |
| `granite-3.3-8b-instruct` | 8B (~16 GB) | Model IBM / Red Hat, „po linii” organizatorów |
| `llama-3.1-8b-instruct` | 8B (~16 GB) | Sprawdzony, obsługa narzędzi |
| `granite-4.0-h-tiny` | mały MoE | Lekki, szybki |
| `qwen3-4b`, `granite-3.3-2b-instruct`, `ministral-3-3b-instruct-2512`, `llama-3.2-1b/3b-instruct`, `granite-4.0-h-micro` | 1–4B | Małe, szybkie, słabsze |
| `gemma-7b` | 7B | Starszy |

Za duże albo ryzykowne na L4:
- `qwen3-14b`, `gemma-3-12b-it`: ~24–28 GB w FP16, nie zmieszczą się bez kwantyzacji;
- `granite-4.0-h-small`, `muse-glimmer-30b`, `qwen3.8-27b`: za duże;
- warianty `*-nvfp4`: format FP4 dla nowszych GPU (Blackwell), L4 go nie obsługuje (?);
- `gpt-oss-20b`: ok. 13–16 GB, ale wymaga specjalnych kerneli; na L4 niepewne (?).

Pomocnicze:
- `granite-guardian-3.3-8b`, `granite-guardian-hap-38m`, `llama-guard-4-12b`: modele bezpieczeństwa (do guardrails);
- `granite-embedding-english-r2`, `all-minilm-l6-v2`: embeddingi (do RAG);
- `granite-vision-3.3-2b`, `llama-3.2-11b-vision-instruct`: modele z obrazem.

Pamiętać, że GPU jest jedno: drugi model na GPU (np. guardian) nie wejdzie obok głównego. Małe modele, jak `granite-guardian-hap-38m` czy embeddingi, mogą działać na CPU (?).

## 1. Wdrożenie modelu z vLLM (wymaganie twarde)

Z dashboardu:
1. Projects → nasz projekt → zakładka **Deployments** → **Deploy model**.
2. Model location: rejestr OCI, magazyn S3 albo URI (np. Hugging Face). Model type: **Generative AI model**.
3. **Hardware profile**: wybrać profil z GPU, jeśli jest.
4. Serving runtime: **„vLLM NVIDIA GPU ServingRuntime for KServe”** (jest też wersja CPU (?), AMD i Intel Gaudi). Jest też opcja „Auto-select”.
5. Advanced: zaznaczyć **zewnętrzny route** (Model access) i **Require token authentication**, a potem zanotować nazwę service account.
6. Adres endpointu: AI hub → Deployments → pole „Inference endpoints”.

API: runtime uruchamia `vllm.entrypoints.openai.api_server`, więc endpoint jest **zgodny z OpenAI** (`/v1/chat/completions`, `/v1/models`). Aplikacja może użyć zwykłego klienta OpenAI z naszym `base_url` i tokenem. Dokładnej ścieżki nie potwierdziliśmy w docs (?).

## 2. Jaki model zmieści się na GPU

Pamięć GPU (GB) ≈ liczba parametrów (mld) × bity / 8, plus KV cache i 10–20% narzutu.

| **Model** | **FP16** | **INT8** | **INT4** |
| --- | --- | --- | --- |
| 3B | ~6 GB | ~3 GB | ~1,5 GB |
| 7–8B | ~14–16 GB | ~7–8 GB | ~3,5–4 GB |
| 13B | ~26 GB | ~13 GB | ~6,5 GB |

Na naszym L4 (24 GB) mieszczą się modele 7–8B w FP16 z zapasem na KV cache (np. Granite 8B, Qwen 7B, Llama 3.1 8B). Większe (13B+) tylko po kwantyzacji. Do agentów z wywoływaniem narzędzi lepiej wziąć model 7–8B niż obecny 3B.

## 3. Bonusy: co mówią docs

- **vLLM** (1 pkt): robimy go i tak przy wymaganiu twardym, więc to darmowy punkt.
- **NeMo Guardrails** (2 pkt): w RHOAI dostępne jako **Technology Preview**. Wymaga wdrożonego modelu i uprawnień admina do tworzenia service accountów, secretów i CR. Docs obiecują „sensitive data detection, content filtering, custom validation rules”. Format konfiguracji i to, czy da się wymusić zasady w stylu „tylko zatwierdzeni odbiorcy” albo „kwota ≤ X”, są do sprawdzenia (?).
  - **Ważne:** guardrail sprawdzający treść nie zatrzyma wywołania narzędzia `send_email`. Zasady (lista odbiorców, limit kwoty) trzeba **twardo sprawdzać w kodzie narzędzia**, a guardrail traktować jako drugą warstwę.
- **ogx + MCP** (1 pkt): nie udało się ustalić, czym dokładnie jest „ogx” (?). W upstream docs jest **Llama Stack** (CR `LlamaStackDistribution`, port 8321), który łączy się z modelem vLLM przez `VLLM_URL`. Wymaga włączonego Llama Stack Operatora i **własnego PostgreSQL 14+**. Warto zapytać na Discordzie #Red-Hat, czy ogx to to samo.
- **MaaS** (1 pkt): bramka do modeli z kluczami API i API zgodnym z OpenAI. Prawdopodobnie Technology Preview (?). Kroki włączenia nie zostały przeczytane (?).
- **MLflow** (1 pkt): nie znaleźliśmy w docs (?).
- Organizatorzy ostrzegają, że włączenie wszystkiego naraz może położyć klaster single-node.

## 4. Gotowe przykłady od Red Hata (warto przejrzeć)

- https://github.com/rh-ai-quickstart:
  - `ai-architecture-charts`: Helm charty dla LLM, Llama Stack, pgvector, minio,
  - `lemonade-stand-assistant`: guardrails z modelami detektorów,
  - `multi-agent-loan-origination` i `portfolio-manager-agent`: orkiestracja agentów w domenie finansowej.
- Kurs vLLM: https://redhatquickcourses.github.io/genai-vllm/genai-vllm/1/index.html

## 5. Do sprawdzenia na klastrze (pierwsza godzina)

- [x] Czy jest GPU i ile ma pamięci: 1× L4 24 GB, zajęte przez `llama-32-3b-instruct` (wyżej)
- [x] Czy model działa: tak, ale 3B jest za słaby (błędne liczenie, nie wywołuje narzędzi)
- [ ] Podmienić `llama-32-3b-instruct` na model 8B (propozycja: `qwen3-8b`) i wystawić route z tokenem
- [ ] Jakie serving runtimes są włączone (Settings → Serving runtimes)
- [ ] Czy są gotowe modele w katalogu modeli (AI hub)
- [ ] Zapytać na Discordzie #Red-Hat: czym jest „ogx” i czy MLflow jest dostępny
