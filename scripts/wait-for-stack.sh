#!/usr/bin/env bash
# Poll Compose service /health endpoints until ready (used by CI after `docker compose up`).
set -euo pipefail

IAM_URL="${HUY_IAM_URL:-http://127.0.0.1:8081}"
REGISTRY_URL="${HUY_REGISTRY_URL:-http://127.0.0.1:8082}"
INVENTORY_URL="${HUY_INVENTORY_URL:-http://127.0.0.1:8083}"
PROJECTS_URL="${HUY_PROJECTS_URL:-http://127.0.0.1:8084}"
BREAKOUT_URL="${HUY_BREAKOUT_URL:-http://127.0.0.1:8085}"
WEB_URL="${HUY_WEB_URL:-http://127.0.0.1:5173}"

urls=(
  "${IAM_URL}/health"
  "${REGISTRY_URL}/health"
  "${INVENTORY_URL}/health"
  "${PROJECTS_URL}/health"
  "${BREAKOUT_URL}/health"
  "${WEB_URL}/health"
)

max_attempts="${HUY_STACK_WAIT_ATTEMPTS:-90}"
sleep_secs="${HUY_STACK_WAIT_INTERVAL:-5}"

for attempt in $(seq 1 "$max_attempts"); do
  ready=true
  for url in "${urls[@]}"; do
    if ! curl -sf --max-time 5 "$url" >/dev/null; then
      ready=false
      break
    fi
  done
  if $ready; then
    echo "All stack health endpoints ready (attempt ${attempt}/${max_attempts})"
    exit 0
  fi
  echo "Waiting for stack health (${attempt}/${max_attempts})..."
  sleep "$sleep_secs"
done

echo "Stack did not become healthy within $((max_attempts * sleep_secs))s" >&2
exit 1
