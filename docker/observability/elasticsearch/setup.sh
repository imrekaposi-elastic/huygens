#!/bin/sh
set -eu

ES_URL="${ELASTICSEARCH_URL:-http://elasticsearch:9200}"
ES_USER="${ELASTICSEARCH_USERNAME:-elastic}"
ES_PASS="${ELASTIC_PASSWORD:?ELASTIC_PASSWORD is required}"
SETUP_DIR="${SETUP_DIR:-/setup}"
AUTH="-u ${ES_USER}:${ES_PASS}"

echo "Waiting for Elasticsearch at ${ES_URL}..."
until curl -sf ${AUTH} "${ES_URL}/_cluster/health?wait_for_status=yellow&timeout=60s" >/dev/null; do
  sleep 2
done

echo "Setting kibana_system password..."
curl -sf ${AUTH} -X POST "${ES_URL}/_security/user/kibana_system/_password" \
  -H "Content-Type: application/json" \
  --data-binary "{\"password\":\"${ES_PASS}\"}" >/dev/null
echo "  ok"

put_json() {
  path="$1"
  file="$2"
  echo "PUT ${path} <- ${file}"
  curl -sf ${AUTH} -X PUT "${ES_URL}${path}" \
    -H "Content-Type: application/json" \
    --data-binary "@${file}"
  echo
}

for pipeline in "${SETUP_DIR}"/pipelines/*.json; do
  name="$(basename "${pipeline}" .json)"
  put_json "/_ingest/pipeline/${name}" "${pipeline}"
done

for policy in "${SETUP_DIR}"/ilm/*.json; do
  name="$(basename "${policy}" .json)-ilm"
  put_json "/_ilm/policy/${name}" "${policy}"
done

for template in "${SETUP_DIR}"/templates/*.json; do
  name="$(basename "${template}" .json)"
  put_json "/_index_template/${name}" "${template}"
done

# Remove legacy daily index templates (superseded by data streams).
for legacy in huy-sessions-legacy huy-audit-legacy; do
  curl -sf ${AUTH} -X DELETE "${ES_URL}/_index_template/${legacy}" >/dev/null 2>&1 || true
done

# Ensure data streams exist (recreated automatically after delete when template is present).
for stream in huy-sessions huy-audit; do
  echo "Ensuring data stream ${stream}..."
  if curl -sf ${AUTH} -X PUT "${ES_URL}/_data_stream/${stream}" >/dev/null 2>&1; then
    echo "  created ${stream}"
  else
    echo "  ${stream} already exists or will be created on first ingest"
  fi
done

echo "Elasticsearch ILM policies, ingest pipelines, index templates, and data streams installed."
