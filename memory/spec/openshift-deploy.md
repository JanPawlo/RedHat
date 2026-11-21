# Deploying a Pushed GitHub Branch to the OpenShift App Link (Instrukcja wdrożenia gałęzi na OpenShift)

Public application URL on the Red Hat OpenShift cluster:
- **App URL:** https://cfo-frontend-autonomous-cfo.apps.ocp.4xxsd.sandbox2810.opentlc.com/
- **OpenShift Console:** https://console-openshift-console.apps.ocp.4xxsd.sandbox2810.opentlc.com
- **OpenShift Project (Namespace):** `autonomous-cfo`
- **Services in `autonomous-cfo`:**
  - `cfo-frontend` (React SPA + Node reverse proxy for `/api/` → `cfo-backend:8000` and `/vllm/` → `qwen3-8b-predictor.my-first-model.svc.cluster.local:8080`)
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

If the database on OpenShift was wiped and needs the Pizzeria Amalfi CSV seeded into the running `cfo-backend` pod:

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
