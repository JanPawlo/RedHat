FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including build tools for psycopg2 / asyncpg if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure directory permissions are compatible with OpenShift arbitrary UIDs
RUN chgrp -R 0 /app && chmod -R g=u /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
