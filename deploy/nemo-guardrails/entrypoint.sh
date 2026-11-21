#!/bin/sh
# Renders the rails config with the model endpoint from env (ConfigMap / compose), then starts the NeMo server.
set -eu

: "${MODEL_ENDPOINT_URL:?MODEL_ENDPOINT_URL must point at the OpenAI-compatible model, e.g. the vLLM predictor /v1}"
export MODEL_API_KEY="${MODEL_API_KEY:-not-needed}"

RENDERED=/tmp/rails
SOURCE="${RAILS_CONFIG_DIR:-/opt/nemo/config}/${GUARDRAILS_CONFIG_ID}"

rm -rf "$RENDERED"
mkdir -p "$RENDERED/$GUARDRAILS_CONFIG_ID"
cp "$SOURCE"/* "$RENDERED/$GUARDRAILS_CONFIG_ID/"
python -c 'import os, sys; p = sys.argv[1]; t = open(p).read(); open(p, "w").write(os.path.expandvars(t))' \
    "$RENDERED/$GUARDRAILS_CONFIG_ID/config.yml"

exec nemoguardrails server \
    --config "$RENDERED" \
    --default-config-id "$GUARDRAILS_CONFIG_ID" \
    --port "$PORT" \
    --disable-chat-ui
