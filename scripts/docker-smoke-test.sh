#!/usr/bin/env bash
# Post-start smoke test for docker compose stack.
set -euo pipefail

API="${API_URL:-http://localhost:8000}"
UI="${UI_URL:-http://localhost:3000}"

echo "==> Health: GET ${API}/"
curl -sf "${API}/" | head -c 200
echo

echo "==> Dashboard: GET ${API}/analytics/dashboard"
curl -sf "${API}/analytics/dashboard" | head -c 400
echo

echo "==> Frontend: GET ${UI}/"
code=$(curl -s -o /dev/null -w "%{http_code}" "${UI}/")
echo "HTTP ${code}"
test "${code}" = "200"

echo "Smoke test passed."
