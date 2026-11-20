# OpenShift AI: co z dokumentacji nam się przyda

Stan na 2026-11-20. docs.redhat.com blokuje automatyczne pobieranie, więc źródłem są: upstream dokumentacja Open Data Hub (archiwalna kopia, RHOAI 3.5 może się różnić) i kurs Red Hat „vLLM on OpenShift AI”. Co niezweryfikowane, jest oznaczone „(?)”.

## Nasz klaster

- OpenShift AI Dashboard: https://data-science-gateway.apps.ocp.4xxsd.sandbox2810.opentlc.com
- OpenShift Console: https://console-openshift-console.apps.ocp.4xxsd.sandbox2810.opentlc.com
- API (dla `oc login`): https://api.ocp.4xxsd.sandbox2810.opentlc.com:6443
- Login i hasło: w wiadomości od organizatorów. **Nie wpisywać ich do repo.**
- Single node, 32 CPU, 128 GB RAM. GPU: challenge card mówi „GPU-backed instance”, ale trzeba to sprawdzić (niżej).

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

Bezpieczny wybór na start: mały Granite (np. 3B–8B) albo Qwen 7B. Najpierw trzeba sprawdzić, ile pamięci ma GPU.

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

- [ ] Czy jest GPU i ile ma pamięci: Dashboard → Settings → Hardware profiles; w konsoli Compute → Nodes → node → szczegóły (zasób `nvidia.com/gpu`)
- [ ] Jakie serving runtimes są włączone (Settings → Serving runtimes)
- [ ] Czy są gotowe modele w katalogu modeli (AI hub)
- [ ] Zapytać na Discordzie #Red-Hat: czym jest „ogx” i czy MLflow jest dostępny
