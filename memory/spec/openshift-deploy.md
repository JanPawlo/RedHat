# Deploying a Pushed GitHub Branch to the OpenShift App Link (Instrukcja wdrożenia gałęzi na OpenShift)

Public application URL on the Red Hat OpenShift cluster:
- **App URL:** https://cfo-frontend-autonomous-cfo.apps.ocp.4xxsd.sandbox2810.opentlc.com/
- **OpenShift Console:** https://console-openshift-console.apps.ocp.4xxsd.sandbox2810.opentlc.com
- **OpenShift Project (Namespace):** `autonomous-cfo`
- **Services in `autonomous-cfo`:**
  - `cfo-frontend` (React SPA + Node reverse proxy for `/api/` → `cfo-backend:8000`; it also has `/vllm/` → `qwen3-8b-predictor.my-first-model.svc.cluster.local:8080`, which must go, see section 8)
  - `cfo-backend` (FastAPI + Alembic migrations on startup)
  - `postgres` (PostgreSQL 16 database)

---

## 1. Log in to `oc` (Zaloguj się w terminalu `oc`)

1. Open the OpenShift Web Console: https://console-openshift-console.apps.ocp.4xxsd.sandbox2810.opentlc.com
2. Click your username in the top-right corner (`Admin Demo ▾`) → **Copy login command** → **Display Token**.
3. Copy the `oc login --token=... --server=...` line and run it in your terminal.
4. Switch to the `autonomous-cfo` project:
   ```bash
   oc project autonomous-cfo
   ```

---

## 2. Check which branch is currently deployed (Sprawdź, jaka gałąź jest aktualnie na linku)

```bash
oc get bc -n autonomous-cfo
```
Look at the `FROM` column (e.g. `Git@master`, `Git@test-calosci`, `Git@natalia-frontend`).

---

## 3. Case A: You pushed new commits to the SAME branch (Nowe commity na tej samej gałęzi)

If you ran `git push` to the branch that is already listed in `oc get bc -n autonomous-cfo`, just trigger a rebuild:

- **Rebuild frontend only:**
  ```bash
  oc start-build bc/cfo-frontend -n autonomous-cfo --follow
  ```
- **Rebuild backend only:**
  ```bash
  oc start-build bc/cfo-backend -n autonomous-cfo --follow
  ```
- **Rebuild both:**
  ```bash
  oc start-build bc/cfo-backend -n autonomous-cfo
  oc start-build bc/cfo-frontend -n autonomous-cfo --follow
  ```

Once the build prints `Push successful`, OpenShift automatically rolls out the new pod in ~10 seconds. Refresh the browser with `Ctrl + Shift + R`.

---

## 4. Case B: Switch the OpenShift link to a DIFFERENT pushed branch (Przełączenie linku na inną gałąź z GitHuba)

First make sure your branch is pushed to GitHub (`git push origin <BRANCH_NAME>`).
Then replace `<BRANCH_NAME>` below (e.g. `master`, `test-calosci`, `natalia-frontend`):

### On Linux / macOS (Bash / Zsh):
```bash
# 1. Point frontend and backend BuildConfigs to your branch
oc patch bc/cfo-frontend -n autonomous-cfo --type=merge -p '{"spec":{"source":{"git":{"ref":"<BRANCH_NAME>"}}}}'
oc patch bc/cfo-backend -n autonomous-cfo --type=merge -p '{"spec":{"source":{"git":{"ref":"<BRANCH_NAME>"}}}}'

# 2. Trigger builds
oc start-build bc/cfo-backend -n autonomous-cfo
oc start-build bc/cfo-frontend -n autonomous-cfo --follow
```

### On Windows (PowerShell):
```powershell
# 1. Point frontend and backend BuildConfigs to your branch
oc patch bc/cfo-frontend -n autonomous-cfo --type=merge -p '{\"spec\":{\"source\":{\"git\":{\"ref\":\"<BRANCH_NAME>\"}}}}'
oc patch bc/cfo-backend -n autonomous-cfo --type=merge -p '{\"spec\":{\"source\":{\"git\":{\"ref\":\"<BRANCH_NAME>\"}}}}'

# 2. Trigger builds
oc start-build bc/cfo-backend -n autonomous-cfo
oc start-build bc/cfo-frontend -n autonomous-cfo --follow
```

---

## 5. Verify pods & logs (Sprawdzenie statusu podów i logów)

```bash
oc get pods -n autonomous-cfo
oc logs deployment/cfo-backend -n autonomous-cfo --tail=50
oc logs deployment/cfo-frontend -n autonomous-cfo --tail=50
```

---

## 6. Re-seed PostgreSQL on OpenShift if the DB is empty (Wgranie danych Pizzerii Amalfi do bazy na OpenShift)

Since 2026-11-22 the backend image contains its own copy of the demo statement (`backend/sample_data/pizzeria-amalfi-bank-statement-2025-v6.csv`, the seed default), so `/demo-reset` on the cluster seeds the data by itself. Keep both copies identical if the statement changes (`memory/reference/sample-data/` is the original, used by Docker Compose). The manual steps below are only a fallback if the database on OpenShift was wiped and the running image is older:

### Linux / macOS (Bash):
```bash
BACKEND_POD=$(oc get pods -n autonomous-cfo -l deployment=cfo-backend -o jsonpath='{.items[0].metadata.name}')
cat memory/reference/sample-data/pizzeria-amalfi-bank-statement-2025-v6.csv | oc exec -i "$BACKEND_POD" -n autonomous-cfo -- sh -c "cat > /tmp/amalfi.csv && SEED_CSV_PATH=/tmp/amalfi.csv python -m app.services.seed"
```

### Windows (PowerShell):
```powershell
$backendPod = (oc get pods -n autonomous-cfo -l deployment=cfo-backend -o jsonpath='{.items[0].metadata.name}')
Get-Content "memory\reference\sample-data\pizzeria-amalfi-bank-statement-2025-v6.csv" -Raw | oc exec -i $backendPod -n autonomous-cfo -- sh -c "cat > /tmp/amalfi.csv && SEED_CSV_PATH=/tmp/amalfi.csv python -m app.services.seed"
```

---

## 7. Route timeout for long requests (Limit czasu na route)

The demo reset (`/demo-reset`, `POST /api/v1/demo/reset`) takes about 50 s (estimated 1.5–2 min from `feature/nemo-guardrails-rebased` on, where card generation leaves one model slot free for people), because the seed asks qwen3-8b to write the decision cards. The OpenShift router (HAProxy) cuts any request after **30 s** by default with a 504. A reset cut halfway leaves the database empty (it truncates first, then seeds). Never close the page while a reset is running.

The `cfo-frontend` route therefore waits up to 5 minutes (set 2026-11-22):

```bash
oc annotate route cfo-frontend -n autonomous-cfo haproxy.router.openshift.io/timeout=300s --overwrite
```

- Check: `oc get route cfo-frontend -n autonomous-cfo -o jsonpath='{.metadata.annotations}'`
- Undo: `oc annotate route cfo-frontend -n autonomous-cfo haproxy.router.openshift.io/timeout-`
- The route was created by hand (no GitOps, no owner), so the setting survives every `oc start-build` and rollout. It is lost only if the route is deleted and created again (`oc expose ...`). Then run the command again.
- On the cluster the frontend is served by a small Node server (inline in the `cfo-frontend` deployment command, S2I `nodejs-20` build), not by nginx. `frontend/nginx.conf` (with its own `proxy_read_timeout 300s`) is used only by local Docker Compose. Node's proxy has no shorter limit, so the route is the only timeout to care about on the cluster.

---

## 8. Close the `/vllm/` route (Zamknij trasę `/vllm/`) – open, 2026-11-22

Found 2026-11-22: `https://cfo-frontend-autonomous-cfo.apps.ocp.4xxsd.sandbox2810.opentlc.com/vllm/v1/models` answers
**without logging in**. The Node proxy of `cfo-frontend` forwards `/vllm/` straight to the qwen3-8b predictor, so anyone
with the link can use the GPU model directly: no login, no guardrails (ours or NeMo), no load limits. A judge who opens
the browser's network tab finds it in a minute. It existed only for the sidebar badge; from
`feature/nemo-guardrails-rebased` on, the frontend asks only the backend (`GET /api/v1/ai/health`), so the route can go.

Not changed yet: the cluster is shared, so this needs the team's go-ahead. Steps:
1. Find the proxy: `oc get deploy cfo-frontend -n autonomous-cfo -o yaml` (the Node server is inline in the container
   command) and remove the `/vllm` branch, keeping `/api/`.
2. `oc rollout status deploy/cfo-frontend -n autonomous-cfo`, then the link above must return the app's page or 404,
   not the model list.
3. Optional, so nothing can go around the backend inside the cluster either: a NetworkPolicy in `my-first-model`
   that lets only `cfo-backend` and `nemo-guardrails` (namespace `autonomous-cfo`) reach the predictor's port 8080.
   Check first that the RHOAI dashboard and your own `oc port-forward` still work.
