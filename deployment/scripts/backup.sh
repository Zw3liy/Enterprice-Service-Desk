#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${ROOT}/backups"
mkdir -p "$OUT"

if [[ -f "${ROOT}/db.sqlite3" ]]; then
  cp "${ROOT}/db.sqlite3" "${OUT}/db_${STAMP}.sqlite3"
  echo "SQLite backup -> ${OUT}/db_${STAMP}.sqlite3"
else
  echo "No sqlite database found; use pg_dump for Postgres deployments."
fi

if [[ -d "${ROOT}/media" ]]; then
  tar -czf "${OUT}/media_${STAMP}.tar.gz" -C "${ROOT}" media
  echo "Media backup -> ${OUT}/media_${STAMP}.tar.gz"
fi
