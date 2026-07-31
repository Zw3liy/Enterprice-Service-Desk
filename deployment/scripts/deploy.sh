#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "[deploy] Building image..."
docker build -t enterprise-service-desk:latest .

echo "[deploy] Running migrations..."
docker compose run --rm web python manage.py migrate --noinput

echo "[deploy] Collecting static..."
docker compose run --rm web python manage.py collectstatic --noinput

echo "[deploy] Starting stack..."
docker compose up -d

echo "[deploy] Done."
