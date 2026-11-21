FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    GUARDRAILS_CONFIG_ID=cfo \
    MODEL_NAME=qwen3-8b \
    PORT=8000

RUN pip install --no-cache-dir "nemoguardrails[server]==0.25.0"

WORKDIR /opt/nemo
COPY config/ /opt/nemo/config/
COPY entrypoint.sh /opt/nemo/entrypoint.sh
RUN chmod 0755 /opt/nemo/entrypoint.sh && chmod -R a+rX /opt/nemo

USER 1001

EXPOSE 8000

ENTRYPOINT ["/opt/nemo/entrypoint.sh"]
