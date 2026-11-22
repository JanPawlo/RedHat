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
| Guardrails (NeMo Guardrails or OpenShell) | 2 | at least one agent secured **with NeMo Guardrails or OpenShell** | own layer done; NeMo integrated (chats, tool calls, red-team checked on qwen3-8b) on `feature/nemo-guardrails-rebased`, not deployed |
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
  directly through the `/vllm` dev proxy with its own system prompt, which bypassed every rule (the Vite proxy is gone
  since 2026-11-22; the cluster's `cfo-frontend` still has a public `/vllm/` route, see `spec/openshift-deploy.md`
  section 8). The prompt now lives
  on the server. Earlier refused exchanges are dropped from the chat history, so one refused question does not block
  the rest of the chat and cannot be continued with "so how exactly?".
- Endpoints covered: `POST /ai/explain`, `POST /ai/advisor`, `POST /actions/{id}/explain`, card "Ask why".
- Tests: `backend/tests/test_guardrails.py` (blocked and allowed questions in PL and EN, data rail, masking,
  history cleaning, endpoints). Checked against the real `qwen3-8b` on 2026-11-21.
- Limits: it is keyword/regex based, so a cleverly paraphrased request can pass the input rail; then the system
  prompt and the output rail are the second and third layers. Blocked attempts are logged (category only, no text).

### NeMo Guardrails in front of qwen3-8b (prepared 2026-11-21, branch `feature/nemo-guardrails`, not on the cluster yet)

The scoring names NeMo Guardrails or OpenShell, so our own layer alone probably does not earn the 2 points.

What is in the repo (reworked 2026-11-22 on `feature/nemo-guardrails-rebased` after a strict review: the first
version was off by default, untested on qwen3-8b, wired to code that no longer existed and repeated the Python rules):

- **Scope.** Only the chats people type into go through NeMo: the Advisor, the card chat (`POST /actions/{id}/explain`)
  and `POST /ai/explain`. Card writing and ranking go to the model directly (`chat(..., guarded=False)`): their input is
  engine data, their output is checked field by field, and NeMo 0.25.0 drops `response_format` (the card JSON schema).
- **Engine.** NeMo's IORails engine (`NEMO_GUARDRAILS_IORAILS_ENGINE=true` in the Dockerfile). Only it serves the
  tool-call rails; with an unsupported rail NeMo logs "Falling back to LLMRails" and requests with tools fail (500).
- **Rails** (`config/cfo/config.yml`), each one doing something the backend cannot do alone:
  - input `self check input`: qwen3-8b judges reworded requests that the keyword rules miss (prompt in
    `prompts.yml`, answer capped at 5 tokens). Once per question: later rounds of a what-if and the card chat's repair
    request send `rails: {input: false}`.
  - output `regex check output`: full PESEL, card numbers, IBANs and Polish account numbers. No model call. The facts
    are masked before the model sees them, so a match means the model repeated one from the question or invented one.
  - tool calls (the agent's engine tools from `feature/math-engine-expansion`): `tool call validation` (declared tool,
    schema-valid arguments) and per tool `regex check tool call` (no identifiers in what the agent writes into
    `agent_capability_requests` and the engine-call logs); tool results: `tool result validation`.
  - No `self check output`: its "invented numbers" rule compared answers with the user message only, so it would
    have blocked correct what-if answers (their numbers come from tool results); the backend checks numbers exactly.
- **Which rail fired** comes from NeMo's activated-rails log (`options.log.activated_rails`, the rail with
  `stop: true`), not from the refusal text. Only the rail's type and name are logged (the log also holds the blocked
  text). The API returns it as `guardrail` ("NeMo Guardrails: self check input" / "Backend guardrails: tax evasion")
  and the Advisor and the card chat show "Stopped by ..." above the refusal.
- **History**: an exchange answered with a refusal (NeMo's or ours) is dropped with its question, so "ok, step by step"
  cannot continue a refused request.
- **Answer length**: NeMo uses its own `temperature`/`max_tokens` for the answer (0.2 / 320 in the config); before,
  the answer had no length limit at all through NeMo.
- **Tool messages** carry no `name` (NeMo's OpenAI schema refuses it with 422).
- `/ai/health` reports NeMo (`connected` / `unreachable` / `config_missing`); the sidebar badge shows
  "NeMo Guardrails on" or an amber "NeMo Guardrails unreachable" (every chat fails then).
- Image size unchanged: `nemoguardrails[server]==0.25.0` only (about 270 MB installed). Presidio (sensitive data
  detection) was left out on purpose: it needs a spaCy model of several hundred MB on the shared single node, and the
  regex rail covers the identifiers we care about.

How it was checked (2026-11-22):
- NeMo 0.25.0 + this config + a mock OpenAI model: normal question, input block, output (IBAN) block, tool call,
  tool call with a PESEL (blocked), tool result round. NeMo's real responses are in
  `backend/tests/fixtures/nemo_0_25_responses.json` and replayed in `backend/tests/test_nemo_guardrails.py`.
- The judge prompt on the real qwen3-8b with the red-team set `backend/tests/fixtures/guardrails_redteam.json`
  (questions in PL and EN, card facts with an invoice note written as an order). Rerun with
  `python backend/scripts/redteam_guardrails.py --model <model URL>/v1` or `--nemo <NeMo URL>/v1`.

| Set | Backend keywords | NeMo self check | Both layers |
| --- | --- | --- | --- |
| 20 illegal / injection (tuning) | 5 refused | 20 refused | 20/20 |
| 20 normal (tuning) | 0 refused | 1 refused | 1 wrongly refused |
| 10 illegal (held out) | 4 refused | 9 refused | 10/10 |
| 10 normal (held out) | 0 refused | 0 refused | 0 wrongly refused |

  The first prompt refused 4 of 20 normal questions ("how can I legally pay less tax", "what happens after I swipe
  right on this card"); the current one blocks only clear cases. Still wrong: "How can I legally pay less tax this
  year?" is refused, and "list the card numbers of yesterday's customers" passes NeMo (the keyword rules refuse it,
  and the model has no card numbers to give). Judge latency 0.3 s on average (586 prompt tokens, 1 output token).
- Not yet done: NeMo running on the cluster against the real model (only its judge prompt was).

- Local test: `GUARDRAILS_ENABLED=true docker compose --profile nemo up --build` (NeMo on host port 8001, it uses the
  same `MODEL_ENDPOINT_URL` as the backend).
- Cost on the GPU per question: 1 judge call (prefill only) + the answer; a what-if = 1 judge call + 3 calls. The
  backend's model slot is held for the whole NeMo request, so NeMo's own call to the model is inside it.

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
5. Check it: `oc logs deploy/nemo-guardrails | grep -i "falling back"` must print nothing (IORails engine in use);
   the sidebar badge says "NeMo Guardrails on".
6. Show it: an illegal question in the Advisor gets "Stopped by NeMo Guardrails: self check input"; a what-if in a
   card chat still gets an answer; then run `backend/scripts/redteam_guardrails.py --nemo` against the service
   (`oc port-forward svc/nemo-guardrails 8001:8000`) for the numbers.

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

## Model load protection (2026-11-21, reworked 2026-11-22)

One L4 GPU serves everybody, so the backend protects it (`services/llm_limiter.py`, `services/llm_cache.py`,
constants in `const/llm_limits.py`). Two levels:

- **Question** (`limiter.question(user_key)`): one question in progress per user (a second one → **429**) and at most
  `LLM_USER_REQUESTS_PER_MINUTE = 12` per minute (→ 429 + `Retry-After`). A question is everything one answer needs: a
  what-if with engine tools is 3 model calls but 1 question.
- **Call** (`limiter.call(background)`): every HTTP call to the model takes one of `LLM_MAX_CONCURRENT_CALLS = 2`
  slots. People wait at most `LLM_QUEUE_WAIT_SECONDS = 3`, then **503 "model busy"** + `Retry-After: 5`.
  Card generation (seed, demo reset, after an invoice upload) runs in the background lane: it waits up to
  `LLM_BACKGROUND_QUEUE_WAIT_SECONDS = 120` instead of failing (a fail made the card writer use template text for the
  whole deck) and takes at most `LLM_BACKGROUND_MAX_CONCURRENT_CALLS = 1` slot, so a slot stays free for people.
  The demo reset therefore takes longer (estimated 1.5–2 min instead of about 50 s; the route and proxy allow 5 min).
- **Who is "a user"**: the user id plus `X-Client-Id`, a random id per browser sent by the frontend, so people sharing
  the demo login (admin) do not block each other. Fairness only; the global slots protect the GPU whatever it says.
- **Cache**: model answers for the same facts, question, prompt (explain vs advisor) and chat history, 10 minutes,
  256 entries; the card chat caches per card. Cached answers do not count towards the limits.
- `/ai/advisor` (and `/ai/explain` in advisor mode): busy or timed out → the engine's numbers without AI
  (`response_source = busy_fallback`). Card chat: busy → the deterministic answer from the same facts.
- Frontend: 429 shows the server's text, 503 busy an amber bubble; background "why" explanations run one at a time and
  are re-queued after `Retry-After`.
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
