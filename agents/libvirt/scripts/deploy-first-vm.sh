#!/usr/bin/env bash
# Bootstrap libvirt "default" NAT network (if missing) and create the first dev VM via the agent API.
set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/huy-libvirt-agent/env}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

TOKEN="${HUY_AGENT_TOKEN:?HUY_AGENT_TOKEN required}"
PORT="${HUY_BIND_PORT:-8765}"
TLS="${HUY_TLS_ENABLED:-false}"
VM_NAME="${VM_NAME:-web-01}"
IMAGE="${IMAGE_NAME:-ubuntu-noble}"
PROFILE="${CLOUD_INIT_PROFILE:-test}"
NETWORK="${LIBVIRT_NETWORK:-lab0}"

if [[ "$TLS" == "true" ]]; then
  BASE="https://127.0.0.1:${PORT}"
  CURL_TLS=(-k)
else
  BASE="http://127.0.0.1:${PORT}"
  CURL_TLS=()
fi

auth=(-H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json")

if ! virsh net-info "$NETWORK" &>/dev/null; then
  echo "Create isolated network via API first, e.g.:"
  echo "  POST /api/v1/networks {\"name\":\"lab0\",\"ipv4_cidr\":\"192.168.200.0/24\",\"bridge\":\"br-lab0\"}"
  exit 1
fi

if curl -s "${CURL_TLS[@]}" "${auth[@]}" "$BASE/api/v1/vms/${VM_NAME}" | grep -q "\"name\""; then
  echo "VM ${VM_NAME} already exists"
else
  echo "Creating VM ${VM_NAME}..."
  curl -sS "${CURL_TLS[@]}" -X POST "${auth[@]}" \
    -d "{\"name\":\"${VM_NAME}\",\"image_name\":\"${IMAGE}\",\"cloud_init_profile\":\"${PROFILE}\",\"network\":\"${NETWORK}\",\"vcpu\":2,\"memory_mib\":2048,\"start\":true}" \
    "$BASE/api/v1/vms"
  echo
fi

echo "=== API ==="
curl -s "${CURL_TLS[@]}" "${auth[@]}" "$BASE/api/v1/vms/${VM_NAME}"
echo
echo "=== virsh ==="
virsh dominfo "$VM_NAME" || true
virsh list --all
