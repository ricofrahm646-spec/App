#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${PROJECT_ROOT}"
docker compose up -d --build

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:3000" >/dev/null 2>&1 || true
fi
