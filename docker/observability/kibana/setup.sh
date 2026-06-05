#!/bin/sh
set -eu

KIBANA_URL="${KIBANA_URL:-http://kibana:5601}"
KIBANA_USER="${KIBANA_USERNAME:-elastic}"
KIBANA_PASS="${ELASTIC_PASSWORD:?ELASTIC_PASSWORD is required}"
AUTH="-u ${KIBANA_USER}:${KIBANA_PASS}"

upsert_data_view() {
  id="$1"
  title="$2"
  name="$3"

  echo "Upserting Kibana data view ${id} (${title})..."
  curl -sf ${AUTH} -X POST "${KIBANA_URL}/api/data_views/data_view" \
    -H 'kbn-xsrf: true' \
    -H 'Content-Type: application/json' \
    --data-binary "$(cat <<EOF
{
  "override": true,
  "data_view": {
    "id": "${id}",
    "title": "${title}",
    "name": "${name}",
    "timeFieldName": "@timestamp"
  }
}
EOF
)" >/dev/null
  echo "  ok"
}

echo "Waiting for Kibana at ${KIBANA_URL}..."
until curl -sf ${AUTH} "${KIBANA_URL}/api/status" >/dev/null; do
  sleep 3
done

upsert_data_view "huy-sessions" "huy-sessions" "Huy SSH Sessions"
upsert_data_view "huy-audit" "huy-audit" "Huy Audit"

echo "Kibana data views installed."
