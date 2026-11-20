# OpenShift AI: what from the documentation will be useful to us

As of 2026-11-20. docs.redhat.com blocks automated fetching, so the sources are: the upstream Open Data Hub documentation (archived copy, RHOAI 3.5 may differ) and the Red Hat course "vLLM on OpenShift AI". Anything unverified is marked "(?)".

## Our cluster

- OpenShift AI Dashboard: https://data-science-gateway.apps.ocp.4xxsd.sandbox2810.opentlc.com
- OpenShift Console: https://console-openshift-console.apps.ocp.4xxsd.sandbox2810.opentlc.com
- API (for `oc login`): https://api.ocp.4xxsd.sandbox2810.opentlc.com:6443
- Login and password: in the message from the organizers. **Do not put them in the repo.**
- Single node (AWS `g6.8xlarge`), 32 CPU, 128 GB RAM.
- **GPU (checked on the cluster 2026-11-20): 1× NVIDIA L4, 24 GB VRAM** (Ada Lovelace architecture, compute 8.9). No sharing (`sharing-strategy: none`), so **only one pod can use the GPU at a time**.
- **The GPU is already taken** by a sample model deployed by the organizers on 2026-11-19:
  - project `my-first-model`, InferenceService `llama-32-3b-instruct` (Llama 3.2 3B Instruct, vLLM runtime `registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.2.4`),
  - model loaded from OCI: `oci://quay.io/redhat-ai-services/modelcar-catalog:llama-3.2-3b-instruct`,
  - in-cluster address: `http://llama-32-3b-instruct-predictor.my-first-model.svc.cluster.local:8080` (OpenAI-compatible API, paths `/v1/...`).
  - We can use it from the app right away, or delete it and deploy our own model. We cannot run two models on the GPU at once.
  - Other models in the same format: `quay.io/redhat-ai-services/modelcar-catalog:<nazwa>` (list below).

### Test of the `llama-32-3b-instruct` model (2026-11-20)

- **Works and responds fast** (approx. 2.5 s for a short answer). `GET /v1/models` and `POST /v1/chat/completions` work, `max_model_len` = 20,000 tokens.
- vLLM is started with `--enable-auto-tool-choice --tool-call-parser=llama3_json`, so **tool calling is enabled**.
- **Poor quality:**
  - to the question "a pizzeria has 33,000 EUR, rent 3,800 EUR/month, can it afford an oven for 10,000 EUR?" it answered incorrectly (that it can't, because "10,000 EUR per month"),
  - with the `get_balance` tool in the request it **did not call it**, and instead replied with the text "you can use the get_balance function".
  - This model is too weak for a CFO agent; it needs to be replaced with a 7–8B one.
- Access:
  - **no external route**;
  - in the cluster, port 80 of the `llama-32-3b-instruct-predictor` service goes straight to vLLM, without a token;
  - port 8443 goes through `kube-rbac-proxy` and requires a token;
  - from outside we tested via the Kubernetes API proxy with an admin token.

### Models available in `modelcar-catalog` (Quay, 2026-11-20)

What will reasonably fit on an L4 24 GB (FP16 / BF16):

| **Model** | **Size** | **Notes** |
| --- | --- | --- |
| `qwen3-8b` | 8B (~16 GB) | **Favorite:** good tool calling, reasoning mode |
| `granite-3.3-8b-instruct` | 8B (~16 GB) | IBM / Red Hat model, "in line with" the organizers |
| `llama-3.1-8b-instruct` | 8B (~16 GB) | Proven, tool support |
| `granite-4.0-h-tiny` | small MoE | Lightweight, fast |
| `qwen3-4b`, `granite-3.3-2b-instruct`, `ministral-3-3b-instruct-2512`, `llama-3.2-1b/3b-instruct`, `granite-4.0-h-micro` | 1–4B | Small, fast, weaker |
| `gemma-7b` | 7B | Older |

Too large or risky on the L4:
- `qwen3-14b`, `gemma-3-12b-it`: ~24–28 GB in FP16, will not fit without quantization;
- `granite-4.0-h-small`, `muse-glimmer-30b`, `qwen3.8-27b`: too large;
- `*-nvfp4` variants: FP4 format for newer GPUs (Blackwell), the L4 does not support it (?);
- `gpt-oss-20b`: approx. 13–16 GB, but requires special kernels; uncertain on the L4 (?).

Auxiliary:
- `granite-guardian-3.3-8b`, `granite-guardian-hap-38m`, `llama-guard-4-12b`: safety models (for guardrails);
- `granite-embedding-english-r2`, `all-minilm-l6-v2`: embeddings (for RAG);
- `granite-vision-3.3-2b`, `llama-3.2-11b-vision-instruct`: vision models.

Remember there is only one GPU: a second model on the GPU (e.g. guardian) will not fit next to the main one. Small models, like `granite-guardian-hap-38m` or embeddings, may run on CPU (?).

## 1. Deploying a model with vLLM (hard requirement)

From the dashboard:
1. Projects → our project → **Deployments** tab → **Deploy model**.
2. Model location: OCI registry, S3 storage or URI (e.g. Hugging Face). Model type: **Generative AI model**.
3. **Hardware profile**: choose a profile with a GPU, if there is one.
4. Serving runtime: **"vLLM NVIDIA GPU ServingRuntime for KServe"** (there is also a CPU version (?), AMD and Intel Gaudi). There is also an "Auto-select" option.
5. Advanced: check **external route** (Model access) and **Require token authentication**, then note the service account name.
6. Endpoint address: AI hub → Deployments → "Inference endpoints" field.

API: the runtime starts `vllm.entrypoints.openai.api_server`, so the endpoint is **OpenAI-compatible** (`/v1/chat/completions`, `/v1/models`). The app can use a regular OpenAI client with our `base_url` and token. We have not confirmed the exact path in the docs (?).

## 2. What model will fit on the GPU

GPU memory (GB) ≈ number of parameters (billions) × bits / 8, plus KV cache and 10–20% overhead.

| **Model** | **FP16** | **INT8** | **INT4** |
| --- | --- | --- | --- |
| 3B | ~6 GB | ~3 GB | ~1.5 GB |
| 7–8B | ~14–16 GB | ~7–8 GB | ~3.5–4 GB |
| 13B | ~26 GB | ~13 GB | ~6.5 GB |

On our L4 (24 GB), 7–8B models fit in FP16 with room for the KV cache (e.g. Granite 8B, Qwen 7B, Llama 3.1 8B). Larger ones (13B+) only after quantization. For agents with tool calling, a 7–8B model is a better choice than the current 3B.

## 3. Bonuses: what the docs say

- **vLLM** (1 pt): we do it anyway for the hard requirement, so it is a free point.
- **NeMo Guardrails** (2 pts): available in RHOAI as a **Technology Preview**. Requires a deployed model and admin permissions to create service accounts, secrets and CRs. The docs promise "sensitive data detection, content filtering, custom validation rules". The configuration format, and whether rules like "approved recipients only" or "amount ≤ X" can be enforced, are to be checked (?).
  - **Important:** a guardrail that checks content will not stop a call to the `send_email` tool. The rules (recipient list, amount limit) must be **hard-checked in the tool code**, and the guardrail treated as a second layer.
- **ogx + MCP** (1 pt): we could not determine what exactly "ogx" is (?). The upstream docs have **Llama Stack** (CR `LlamaStackDistribution`, port 8321), which connects to the vLLM model via `VLLM_URL`. It requires the Llama Stack Operator to be enabled and **its own PostgreSQL 14+**. Worth asking on Discord #Red-Hat whether ogx is the same thing.
- **MaaS** (1 pt): a gateway to models with API keys and an OpenAI-compatible API. Probably Technology Preview (?). The steps to enable it have not been read (?).
- **MLflow** (1 pt): we did not find it in the docs (?).
- The organizers warn that enabling everything at once may bring down the single-node cluster.

## 4. Ready-made examples from Red Hat (worth a look)

- https://github.com/rh-ai-quickstart:
  - `ai-architecture-charts`: Helm charts for LLM, Llama Stack, pgvector, minio,
  - `lemonade-stand-assistant`: guardrails with detector models,
  - `multi-agent-loan-origination` and `portfolio-manager-agent`: agent orchestration in the financial domain.
- vLLM course: https://redhatquickcourses.github.io/genai-vllm/genai-vllm/1/index.html

## 5. To check on the cluster (first hour)

- [x] Is there a GPU and how much memory does it have: 1× L4 24 GB, taken by `llama-32-3b-instruct` (above)
- [x] Does the model work: yes, but 3B is too weak (wrong calculations, does not call tools)
- [ ] Replace `llama-32-3b-instruct` with an 8B model (proposal: `qwen3-8b`) and expose a route with a token
- [ ] Which serving runtimes are enabled (Settings → Serving runtimes)
- [ ] Are there ready models in the model catalog (AI hub)
- [ ] Ask on Discord #Red-Hat: what "ogx" is and whether MLflow is available
