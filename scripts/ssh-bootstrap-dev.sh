#!/usr/bin/env bash
# Bootstrap SSH policy + VM trust for local Phase 9 testing.
set -euo pipefail

IAM_URL="${HUY_IAM_URL:-http://127.0.0.1:8081}"
AGENT_URL="${HUY_AGENT_URL:-}"
ORG_ID="${HUY_ORG_ID:-}"
PROJECT_ID="${HUY_PROJECT_ID:-}"
AGENT_ID="${HUY_AGENT_ID:-}"
VM_NAME="${HUY_VM_NAME:-}"
LINUX_USER="${HUY_LINUX_USER:-}"
USERNAME="${HUY_USERNAME:-platform-admin}"
PASSWORD="${HUY_PASSWORD:-platform-admin-secret-12}"
USER_ID="${HUY_USER_ID:-}"

usage() {
  cat <<'EOF'
Usage: ssh-bootstrap-dev.sh [options]

Required env (or flags):
  HUY_ORG_ID          Organization UUID
  HUY_PROJECT_ID      Project UUID
  HUY_AGENT_ID        Libvirt agent UUID
  HUY_VM_NAME         VM name on hypervisor
  HUY_LINUX_USER      Linux account on guest (e.g. ubuntu)
  HUY_AGENT_URL       Agent base URL (e.g. http://192.168.1.10:9100)

Optional:
  HUY_IAM_URL         Default http://127.0.0.1:8081
  HUY_USERNAME        IAM login user (default platform-admin)
  HUY_PASSWORD        IAM login password
  HUY_USER_ID         Huygens user UUID for account mapping (fetched from /me if unset)

Steps: login → org SSH CA → account mapping → project ssh_access grant → agent ssh-trust
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --org) ORG_ID="$2"; shift 2 ;;
    --project) PROJECT_ID="$2"; shift 2 ;;
    --agent) AGENT_ID="$2"; shift 2 ;;
    --vm) VM_NAME="$2"; shift 2 ;;
    --linux-user) LINUX_USER="$2"; shift 2 ;;
    --agent-url) AGENT_URL="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

for var in ORG_ID PROJECT_ID AGENT_ID VM_NAME LINUX_USER AGENT_URL; do
  if [[ -z "${!var}" ]]; then
    echo "Missing required value: $var" >&2
    usage
    exit 1
  fi
done

api() {
  local method="$1" url="$2"
  shift 2
  curl -fsS -X "$method" "$url" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    "$@"
}

echo "==> IAM login"
TOKEN=$(curl -fsS -X POST "$IAM_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" | jq -r .access_token)

if [[ -z "$USER_ID" || "$USER_ID" == "null" ]]; then
  USER_ID=$(api GET "$IAM_URL/api/v1/auth/me" | jq -r .id)
fi
echo "    user_id=$USER_ID"

echo "==> Org SSH CA"
CA=$(api GET "$IAM_URL/api/v1/organizations/$ORG_ID/ssh/ca" | jq -r .public_key_openssh)

echo "==> Account mapping"
api POST "$IAM_URL/api/v1/organizations/$ORG_ID/ssh/account-mappings" \
  -d "{\"user_id\":\"$USER_ID\",\"linux_username\":\"$LINUX_USER\",\"project_id\":null}" \
  >/dev/null 2>&1 || true

echo "==> Project ssh_access role"
api POST "$IAM_URL/api/v1/organizations/$ORG_ID/users/$USER_ID/project-roles" \
  -d "{\"project_id\":\"$PROJECT_ID\",\"role\":\"ssh_access\"}" \
  >/dev/null 2>&1 || true

REGISTRY_URL="${HUY_REGISTRY_URL:-http://127.0.0.1:8082}"
AGENT_TOKEN=$(curl -fsS "$REGISTRY_URL/api/v1/internal/agents/$AGENT_ID/connect" \
  -H "X-Huy-Service-Token: ${PROJECTS_SERVICE_TOKEN:-dev-projects-service-token}" 2>/dev/null | jq -r .agent_token) || true

if [[ -z "$AGENT_TOKEN" || "$AGENT_TOKEN" == "null" ]]; then
  echo "    (skip agent token — set PROJECTS_SERVICE_TOKEN or apply trust via console)"
  echo "    CA ready; mapping + role configured."
  exit 0
fi

echo "==> Agent ssh-trust on $VM_NAME"
curl -fsS -X PUT "$AGENT_URL/api/v1/vms/$VM_NAME/ssh-trust" \
  -H "Authorization: Bearer $AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"ca_public_key_openssh\":$(jq -Rs . <<<"$CA"),\"linux_username\":\"$LINUX_USER\",\"sudoers_lines\":[]}"

echo "Done. New VMs need cloud-init with this trust; existing guests may need recreate/reboot with updated ISO."
echo "Connect: eval \$(huy login -q $USERNAME '$PASSWORD' --org $ORG_ID)"
echo "         huy ssh $VM_NAME --project $PROJECT_ID"
