# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS development
COPY . .
CMD ["uvicorn", "agentnet.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production
COPY . .
RUN addgroup --system --gid 1001 app && useradd --system --uid 1001 app
USER app
CMD ["uvicorn", "agentnet.main:app", "--host", "0.0.0.0", "--port", "8000"]
