#!/usr/bin/env bash
# Fast local validation: start Postgres + Redis only, run API tests
set -euo pipefail

echo "=== AgentNet Dev Up ==="
docker compose up -d db redis
echo "Waiting for DB..."
until docker compose exec db pg_isready -U agentnet 2>/dev/null; do sleep 1; done
echo "DB ready."
echo "Running API tests..."
docker compose run --rm api pytest -v
echo "=== Done ==="
