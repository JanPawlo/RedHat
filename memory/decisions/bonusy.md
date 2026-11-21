# Bonuses: what we chose and exactly what we do

Decision 2026-11-21 (Kacper): Guardrails, MaaS, Dev Spaces and Pipelines/GitOps. vLLM is already done (free point).
Scoring source: `spec/wyzwanie.md` (table) and `spec/openshift-ai.md` section 3. Organizers: at most 2–4 bonuses,
report finished ones to Georg and Karsten, and do not enable everything at once (single-node cluster).

Cluster state checked 2026-11-21 (`oc get csv -A`): installed = RHOAI 3.5.3 (`rhods-operator`), Authorino,
OpenShift Pipelines, Serverless, GPU operator. Available in the catalogue but **not installed** = Dev Spaces,
OpenShift GitOps, 3scale.

| Bonus | Points | Counts when | Status |
| --- | --- | --- | --- |
| vLLM | 1 | model served by vLLM on RHOAI | done (`qwen3-8b`) |
| Guardrails (NeMo Guardrails or OpenShell) | 2 | at least one agent secured **with NeMo Guardrails or OpenShell** | own layer done; NeMo service + backend switch ready on `feature/nemo-guardrails`, not deployed |
| MaaS (model gateway) | 1 | the app reaches the model through the gateway | to do (steps ready, no code change needed) |
| Dev Spaces | 2 | 5/10 = some coding done there, 10/10 = all coding | `devfile.yaml` ready; operator not installed |
| Pipelines / GitOps | **0** | **not a bonus in the scoring table** | optional, only for our own convenience |

Total reachable: 1 + 2 + 1 + 2 = 6 points (of 14 for all bonuses). Pipelines/GitOps adds no points; it only makes
redeploys repeatable. The team chose it anyway, so it is listed last and done only if time is left.

## 1. Guardrails (2 points)

### Done: own guardrail layer in the backend (2026-11-21, branch `feature/register-guardrails-bank`)

Goal from the team: nobody can get illegal data or information out of the AI agent.

- Every LLM call goes through `backend/app/services/guardrails.py`; rules and texts are in `backend/app/const/guardrails.py`.
- **Input rail:** the question is checked before the model is called. Refused categories: money laundering,
  tax evasion (hiding income, fake invoices, VAT carousel, cash "off the books"), fraud and forged documents,
  other people's personal or banking data (PESEL, passwords, card numbers of customers/employees), bribery and
  getting around sanctions, plus prompt injection ("ignore previous instructions", "show your system prompt").
  Text is lower-cased and stripped of Polish diacritics first, so Polish and English both work.
  A refused question returns HTTP 200 with a polite refusal, `model = "guardrail"`, `response_source = "guardrail"`.
- **Data rail:** facts sent to the model (invoice and statement text, owner's notes) are data. Strings in them that
  look like instructions are replaced with `[removed: instruction-like text]`; numbers stay.
- **Output rail:** the answer is checked again; illegal how-to content is replaced by a refusal, and PESEL numbers,
  card numbers (Luhn check) and full IBANs (only the last 4 characters stay) are masked.
- **System prompt:** `SAFETY_RULES` in `backend/app/const/llm.py` are appended to both prompts (card explanations and
  the Advisor chat).
- **Advisor chat** now goes through the backend (`POST /api/v1/ai/advisor`). Before, the browser called vLLM
  directly through the `/vllm` dev proxy with its own system prompt, which bypassed every rule. The prompt now lives
  on the server. Earlier refused exchanges are dropped from the chat history, so one refused question does not block
  the rest of the chat and cannot be continued with "so how exactly?".
- Endpoints covered: `POST /ai/explain`, `POST /ai/advisor`, `POST /actions/{id}/explain`, card "Ask why".
- Tests: `backend/tests/test_guardrails.py` (blocked and allowed questions in PL and EN, data rail, masking,
  history cleaning, endpoints). Checked against the real `qwen3-8b` on 2026-11-21.
- Limits: it is keyword/regex based, so a cleverly paraphrased request can pass the input rail; then the system
  prompt and the output rail are the second and third layers. Blocked attempts are logged (category only, no text).

### NeMo Guardrails in front of qwen3-8b (prepared 2026-11-21, branch `feature/nemo-guardrails`, not on the cluster yet)

The scoring names NeMo Guardrails or OpenShell, so our own layer alone probably does not earn the 2 points.

What is in the repo:

- `deploy/nemo-guardrails/`: `Dockerfile` (python:3.11-slim + `nemoguardrails[server]==0.25.0`, runs as non-root,
  works with OpenShift random UIDs), `entrypoint.sh` (puts `MODEL_ENDPOINT_URL` / `MODEL_NAME` from env into the
  config, then `nemoguardrails server --default-config-id cfo --disable-chat-ui` on port 8000),
  `config/cfo/config.yml` (main model = `qwen3-8b` through the OpenAI-compatible vLLM endpoint, thinking off,
  rails `self check input` + `self check output`, `passthrough: true`), `config/cfo/prompts.yml` (the policies),
  `k8s/configmap.yaml` (endpoint, model name, config id; placeholders only), `k8s/deployment.yaml` (probes on
  `/v1/rails/configs`, API key from the optional Secret `nemo-guardrails-model-key`), `k8s/service.yaml` (port 8000).
- Policies: input = illegal requests (money laundering, tax evasion, fake invoices, fraud, bribery, sanctions),
  other people's personal or banking data, prompt injection (also hidden in FACTS / NOTES), asking the model to make
  up numbers; output = illegal how-to, personal identifiers (PESEL, card numbers, full IBANs, passwords), revealing
  the prompt, **numbers that are not in the user message** (invented amounts, percentages or dates).
- Backend switch (`core/config.py`): `GUARDRAILS_ENABLED=false` by default; with `true` the chat completions go to
  `GUARDRAILS_ENDPOINT_URL` (e.g. `http://nemo-guardrails:8000/v1`) with `"guardrails": {"config_id": "cfo"}`
  (`GUARDRAILS_CONFIG_ID`), the health check still asks the model directly. The API refuses to start with the switch
  on and no URL. Our own Python guardrails stay the **first layer**; NeMo's refusal text
  ("I'm sorry, I can't respond to that.") is turned into our normal guardrail answer (`response_source = guardrail`).
- `passthrough: true` is required: without it NeMo (Colang 1 "general" mode) flattens the chat into its own prompt
  and **drops our system prompt** (`SYSTEM_PROMPT` / `ADVISOR_PROMPT` with the strict number rules). With passthrough
  our messages reach the model unchanged and NeMo only runs the input and output rails. Checked on 2026-11-21.
- Local test: `GUARDRAILS_ENABLED=true docker compose --profile nemo up --build` (NeMo on host port 8001, it uses the
  same `MODEL_ENDPOINT_URL` as the backend). Checked locally on 2026-11-21 with a mock OpenAI-compatible model
  (backend `services/llm.py` → NeMo container started with a random UID → mock): allowed question answered with our
  system prompt intact, a question flagged by the input rail refused (→ our guardrail answer), `GET /v1/rails/configs`
  = `[{"id": "cfo"}]`. Not yet tested against the real `qwen3-8b` (how strict its Yes/No self-checks are, especially
  the "invented numbers" rule, must be checked on the cluster; loosen `prompts.yml` if it blocks normal answers).
- Cost on the GPU: each question = up to 3 model calls (input check, answer, output check). The backend semaphore
  (2 calls at a time) counts backend calls, so the GPU can see up to 6. If answers get too slow, set
  `LLM_MAX_CONCURRENT_CALLS = 1` in `const/llm_limits.py`.

Deploying on RHOAI, two options. Decision: **option A first** (no Tech Preview operator, fully under our control, same
NeMo server); option B only if the organizers want the RHOAI-managed variant and the CRD exists.

Option A, our own Deployment in `autonomous-cfo` (about 30 min):
1. `oc project autonomous-cfo`
2. Build from the repo: `oc new-build https://github.com/JanPawlo/RedHat#<branch> --name nemo-guardrails --strategy docker --context-dir deploy/nemo-guardrails`
   then `oc set image-lookup nemo-guardrails` (so the Deployment's `image: nemo-guardrails:latest` resolves to the ImageStream).
3. `oc apply -f deploy/nemo-guardrails/k8s/`, then put the real endpoint only on the cluster (never in git):
   `oc set data configmap/nemo-guardrails MODEL_ENDPOINT_URL=http://<model>-predictor.<model-namespace>.svc.cluster.local:8080/v1`
   and `oc rollout restart deploy/nemo-guardrails`; wait for `oc rollout status deploy/nemo-guardrails`.
4. Switch the backend: `oc set env deploy/cfo-backend GUARDRAILS_ENABLED=true GUARDRAILS_ENDPOINT_URL=http://nemo-guardrails:8000/v1`.
   Back to the direct model: `oc set env deploy/cfo-backend GUARDRAILS_ENABLED=false`.
5. Show it: an illegal question in the Advisor is refused, and `oc logs deploy/nemo-guardrails` shows the
   `self_check_input` call; a normal question still gets an answer.

Option B, TrustyAI-managed NeMo Guardrails (Technology Preview in RHOAI 3.x):
1. Enable TrustyAI: `oc edit datasciencecluster` → `trustyai: managementState: Managed`.
2. Check the CRD and its fields first: `oc get crd | grep -i nemo`, then `oc explain nemoguardrails.spec` (field names
   change between Tech Preview versions, so do not trust examples blindly).
3. Render our config with real values into a local, uncommitted copy (replace `${MODEL_ENDPOINT_URL}` and
   `${MODEL_NAME}` in `config.yml`), then `oc create configmap nemo-cfo-rails --from-file=<that folder>`.
4. Create the `NemoGuardrails` CR in the model's namespace pointing at that ConfigMap; it creates the service.
5. Point `GUARDRAILS_ENDPOINT_URL` of `cfo-backend` at the service it created (step 4 of option A).

With MaaS (section 2): NeMo's `MODEL_ENDPOINT_URL` = gateway URL and the key in the Secret
`nemo-guardrails-model-key` (`oc create secret generic nemo-guardrails-model-key --from-literal=MODEL_API_KEY=<key>`).
Order: app (own rails) → NeMo → MaaS gateway → vLLM.

## Model load protection (2026-11-21, branch `feature/nemo-guardrails`)

One L4 GPU serves everybody, so the backend protects it (`services/llm_limiter.py`, `services/llm_cache.py`,
constants in `const/llm_limits.py`):

- Global `asyncio.Semaphore`: at most `LLM_MAX_CONCURRENT_CALLS = 2` model calls at a time; a call waits at most
  `LLM_QUEUE_WAIT_SECONDS = 3` for a slot, then fails fast with **503 "model busy"** + `Retry-After: 5` instead of a
  60 s timeout.
- Per user: one question in progress (a second one → **429**), at most `LLM_USER_REQUESTS_PER_MINUTE = 12`
  per minute (→ 429 with `Retry-After` = seconds until the oldest call leaves the window). In memory, per API pod.
- Cache of `explain` answers: key = hash of the facts + the question (lower-case, spaces collapsed), 10 minutes,
  256 entries. Cached answers do not count towards the limits. The facts contain the engine's numbers, so a changed
  card gets a new key.
- `/ai/advisor`: when the model is busy or times out, the answer is built from the engine's facts without AI
  (`response_source = busy_fallback`, `model = forecast-engine`): balance, buffer, lowest balance, what can be
  paid today and the best date for a bigger payment. Card "Ask why" already had a deterministic fallback; a busy
  model now lands there too. `/ai/explain` returns 503 busy.
- Frontend: 429 shows the server's text ("previous question still being answered" / "try again in N s"), 503 busy
  shows "model busy" in an amber bubble; a busy-fallback advisor answer gets a "Model busy · numbers straight from the
  forecast engine" label. Background card explanations run one at a time and are re-queued after `Retry-After`.
- Tests: `backend/tests/test_llm_limits.py`.

## 2. MaaS – model gateway (1 point)

Counts when the app reaches the model through the gateway instead of the predictor service.

Exact steps:
1. Check in the RHOAI dashboard (Settings → Models as a Service) whether MaaS is available in 3.5.3; Authorino,
   which it needs for API keys, is already installed. From the CLI: `oc get crd | grep -iE "maas|gateway|kuadrant"`.
   If it needs Gateway API / Red Hat Connectivity Link that is not installed, decide again (extra operators on the
   single node).
2. Publish `qwen3-8b` through MaaS (model deployment → "Make available as a service"), create an API key for the app
   and note the gateway URL (OpenAI-compatible, ends with `/v1`). Test it once from a terminal:
   `curl -H "Authorization: Bearer <key>" <gateway URL>/v1/models` must list `qwen3-8b`.
3. Key only in a Secret, never in git or in plain `oc set env`:
   `oc create secret generic cfo-model-key -n autonomous-cfo --from-literal=MODEL_API_KEY=<key>`
   `oc set env deploy/cfo-backend --from=secret/cfo-model-key`
   `oc set env deploy/cfo-backend MODEL_ENDPOINT_URL=<gateway URL>/v1`
   The backend already sends `Authorization: Bearer <MODEL_API_KEY>` (`services/llm.py`), so no code change.
4. With NeMo in front (section 1): put the same key into `nemo-guardrails-model-key` and the gateway URL into the
   `nemo-guardrails` ConfigMap (`MODEL_ENDPOINT_URL`); the backend keeps `MODEL_ENDPOINT_URL` = gateway (used by the
   health check) and `GUARDRAILS_ENDPOINT_URL` = NeMo.
5. Check `GET /api/v1/ai/health` (`configured_model`, `available_models`) and the model badge in the sidebar; ask one
   Advisor question and look for it in the MaaS usage / gateway logs (proof for the organizers).
6. Rollback: `oc set env deploy/cfo-backend MODEL_ENDPOINT_URL=<predictor URL>/v1 MODEL_API_KEY-`.

Order with NeMo Guardrails: app → guardrails → MaaS gateway → vLLM, or app → MaaS → vLLM if NeMo is skipped.
Cost: about 1–2 h if MaaS is available in the dashboard; if it needs an extra operator, decide again.

## 3. Dev Spaces (2 points)

Counts by how much coding is done in Dev Spaces (5/10 = some, 10/10 = all).

Exact steps:
1. Install the Red Hat OpenShift Dev Spaces operator from OperatorHub and create the `CheCluster` (default settings).
2. Done 2026-11-21 (branch `feature/nemo-guardrails`): `devfile.yaml` in the repo root (schema 2.2.0). Containers:
   `python` (ubi9/python-311, the editor runs here, venv in `/projects/.venv-cfo`), `node` (ubi9/nodejs-20, Vite on
   3000, public endpoint, `VITE_ALLOW_ALL_HOSTS=true` so Vite 5.4 accepts the workspace host), `postgres`
   (sclorg postgresql-16, `cfo_user/cfo_password/cfo_db` like docker compose, 1 Gi volume). All containers share the
   pod, so the backend reaches Postgres and Vite reaches the backend on `localhost`. Commands: "backend: install",
   "backend: run (uvicorn :8000)", "backend: seed demo data", "backend: tests (pytest)", "backend: lint (ruff, CI
   rules)", "frontend: install" (`npm ci`), "frontend: dev (Vite :3000)", "frontend: build". Admin `admin/admin` as
   agreed. `MODEL_ENDPOINT_URL` is a placeholder (no cluster data in git): set the real predictor or MaaS URL in the
   workspace (Dev Spaces → User Preferences → or edit the env in the running workspace) before using the AI.
   `SEED_CSV_PATH` assumes the repo is cloned to `/projects/RedHat` (default for this GitHub repo).
   First start: run "backend: install" and "frontend: install" once, then the two run commands.
3. Open the workspace from the GitHub URL, log in with GitHub, and make at least part of the real commits from there
   (the more coding there, the more points). Keep screenshots and the workspace for the organizers.
4. Optional extra 2 points later: an OSS code assistant (Continue or OpenCode) in the same workspace wired to `qwen3-8b`.

Cost: operator + devfile about 1 h; the points depend on actually coding there.
Risk: Dev Spaces uses a few GB of RAM per workspace on the single node; keep at most 1–2 workspaces running.

## 4. Pipelines / GitOps (0 points, convenience only)

Not in the scoring table. OpenShift Pipelines (Tekton) is already installed; GitOps (Argo CD) is not.
Today the app redeploys via the existing BuildConfigs (`cfo-backend` Docker, `cfo-frontend` Source, both `Git@master`).

If time is left (nothing created on the cluster or in the repo yet; manifests would go to `deploy/tekton/`):
1. Workspace: a `PersistentVolumeClaim` (1 Gi) shared by the tasks, plus the GitHub webhook secret
   `oc create secret generic github-webhook --from-literal=secret=<random>` (value only on the cluster).
2. `Pipeline cfo-redeploy` (params `git-url`, `git-revision`), tasks taken from the cluster resolver
   (`resolver: cluster`, namespace `openshift-pipelines`) so nothing has to be installed:
   - `git-clone` → workspace `source`;
   - `pytest`: a custom inline task, image `python:3.11-slim` with a `postgres:16-alpine` **sidecar** and
     `DATABASE_URL` / `SYNC_DATABASE_URL` on `localhost`, script: `pip install -r backend/requirements.txt pytest ruff`,
     `ruff check app --select E9,F63,F7,F82 --no-cache`, `alembic upgrade head`, `python -m pytest -q`
     (same as `release.yml`); a failing test stops the pipeline;
   - `buildah` twice (`CONTEXT=backend` / `frontend`, `IMAGE=image-registry.openshift-image-registry.svc:5000/autonomous-cfo/cfo-backend:latest`
     and `.../cfo-frontend:latest`), needs the `pipeline` service account (it can push to the internal registry);
   - `openshift-client`: `oc rollout restart deploy/cfo-backend deploy/cfo-frontend` then
     `oc rollout status deploy/cfo-backend --timeout=5m` (and the same for the frontend).
   This replaces the BuildConfigs for the push path; keep them for manual `oc start-build` as a fallback.
3. Trigger on push: `TriggerBinding` (`git-url` = `$(body.repository.clone_url)`, `git-revision` = `$(body.after)`),
   `TriggerTemplate` creating a `PipelineRun` of `cfo-redeploy`, `EventListener` with the `github` interceptor
   (secret `github-webhook`, `eventTypes: ["push"]`) and a CEL filter `body.ref == 'refs/heads/master'`;
   `oc expose svc el-cfo-listener` gives the URL for GitHub → Settings → Webhooks (content type JSON, same secret).
4. Check: push a commit, `tkn pipelinerun logs -f --last`, the new pods roll out.
5. GitOps (installing Argo CD) is skipped: more load on the single node and no points.

## Order and next step

1. Merge the own guardrail layer (done on the branch, needs a merge into `test-calosci` / `master` and a redeploy).
2. Dev Spaces (2 points, low risk).
3. NeMo Guardrails (2 points, medium risk).
4. MaaS (1 point).
5. Pipelines only if time is left.

Cluster changes (installing operators, changing the backend endpoint) are done only after the team agrees,
because the cluster is shared and single-node. After each finished bonus: tell Georg and Karsten.
