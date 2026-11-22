## How this release runs

- Deployed on Red Hat OpenShift (namespace `autonomous-cfo`): `cfo-frontend`, `cfo-backend`, `postgres` and `nemo-guardrails`, all built from this tag's branch.
- The model is `qwen3-8b`, served by vLLM on Red Hat OpenShift AI.
- **The app runs with NeMo Guardrails switched on** (`GUARDRAILS_ENABLED=true`): every chat question (Advisor, card chat, "Ask why") goes backend → NeMo Guardrails (IORails engine, input self check, output and tool-call rails) → qwen3-8b. The backend's own guardrail layer stays in front of it.
- Deployment steps: `memory/spec/openshift-deploy.md`; NeMo setup and red-team results: `memory/decisions/bonusy.md`.
