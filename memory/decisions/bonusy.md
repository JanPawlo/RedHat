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
| Guardrails (NeMo Guardrails or OpenShell) | 2 | at least one agent secured **with NeMo Guardrails or OpenShell** | own layer done; NeMo still to do |
| MaaS (model gateway) | 1 | the app reaches the model through the gateway | to do |
| Dev Spaces | 2 | 5/10 = some coding done there, 10/10 = all coding | to do |
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

### To do for the points: NeMo Guardrails on RHOAI

The scoring names NeMo Guardrails or OpenShell, so our own layer alone probably does not earn the 2 points.
In RHOAI 3.5 NeMo Guardrails is a **Technology Preview** run by the TrustyAI operator.

Exact steps:
1. Enable the TrustyAI component in the `DataScienceCluster` (`oc edit datasciencecluster`, `trustyai: managementState: Managed`).
2. Create a NeMo Guardrails config (Colang rails + `config.yml`) in a ConfigMap: input rail "refuse illegal financial
   requests" and output rail "no personal identifiers", same categories as our own layer.
3. Create the guardrails CR in namespace `my-first-model`, pointing at `qwen3-8b-predictor` as the main model.
4. Point the backend `MODEL_ENDPOINT_URL` at the guardrails service instead of the predictor (OpenAI-compatible
   endpoint, so `services/llm.py` needs no code change). Our own layer stays as the first line.
5. Show it to the organizers: a refused prompt in the Advisor and the guardrails pod logs.

Cost: about 2–3 h, risk: Tech Preview, extra pod on the single node. Needs cluster admin (we have it).

## 2. MaaS – model gateway (1 point)

Counts when the app reaches the model through the gateway instead of the predictor service.

Exact steps:
1. Check in the RHOAI dashboard (Settings → Models as a Service) whether MaaS is available in 3.5.3; Authorino,
   which it needs for API keys, is already installed.
2. Publish `qwen3-8b` through MaaS and create an API key for our app.
3. Put the key in a Secret and set on `cfo-backend`: `MODEL_ENDPOINT_URL=<gateway URL>/v1`, `MODEL_API_KEY=<key>`.
   The backend already sends `Authorization: Bearer <MODEL_API_KEY>` (`services/llm.py`), so no code change.
4. Check `GET /api/v1/ai/health` and the model badge in the sidebar.

Order with NeMo Guardrails: app → guardrails → MaaS gateway → vLLM, or app → MaaS → vLLM if NeMo is skipped.
Cost: about 1–2 h if MaaS is available in the dashboard; if it needs an extra operator, decide again.

## 3. Dev Spaces (2 points)

Counts by how much coding is done in Dev Spaces (5/10 = some, 10/10 = all).

Exact steps:
1. Install the Red Hat OpenShift Dev Spaces operator from OperatorHub and create the `CheCluster` (default settings).
2. Add `devfile.yaml` to the repo root: Python 3.11 + Node 20 containers, PostgreSQL 16 container, commands
   "backend: run" (uvicorn on 8000), "backend: tests" (pytest), "frontend: dev" (Vite on 5173), env
   `MODEL_ENDPOINT_URL=http://qwen3-8b-predictor.my-first-model.svc.cluster.local:8080/v1`.
3. Open the workspace from the GitHub URL, log in with GitHub, and make at least part of the real commits from there
   (the more coding there, the more points). Keep screenshots and the workspace for the organizers.
4. Optional extra 2 points later: an OSS code assistant (Continue or OpenCode) in the same workspace wired to `qwen3-8b`.

Cost: operator + devfile about 1 h; the points depend on actually coding there.
Risk: Dev Spaces uses a few GB of RAM per workspace on the single node; keep at most 1–2 workspaces running.

## 4. Pipelines / GitOps (0 points, convenience only)

Not in the scoring table. OpenShift Pipelines (Tekton) is already installed; GitOps (Argo CD) is not.
Today the app redeploys via the existing BuildConfigs (`cfo-backend` Docker, `cfo-frontend` Source, both `Git@master`).

If time is left:
1. Tekton `Pipeline` in `openshift/pipeline.yaml`: git clone → backend tests → `oc start-build cfo-backend` and
   `cfo-frontend` → `oc rollout status`.
2. A GitHub webhook `EventListener` so a push to `master` runs it.
3. GitOps (installing Argo CD) is skipped: more load on the single node and no points.

## Order and next step

1. Merge the own guardrail layer (done on the branch, needs a merge into `test-calosci` / `master` and a redeploy).
2. Dev Spaces (2 points, low risk).
3. NeMo Guardrails (2 points, medium risk).
4. MaaS (1 point).
5. Pipelines only if time is left.

Cluster changes (installing operators, changing the backend endpoint) are done only after the team agrees,
because the cluster is shared and single-node. After each finished bonus: tell Georg and Karsten.
