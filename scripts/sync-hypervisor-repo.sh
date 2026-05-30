#!/usr/bin/env bash
# Sync a hypervisor checkout (e.g. dommel) to origin/main and restart the libvirt agent.
# Use when git pull fails due to old local patches (path_safety, CodeQL fixes) that are
# already on main — discard them and take the repo version.
set -euo pipefail

REPO_ROOT="${1:-/opt/huygens}"
AGENT_DIR="${REPO_ROOT}/agents/libvirt"

cd "${REPO_ROOT}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not a git repository: ${REPO_ROOT}" >&2
  exit 1
fi

echo "Fetching origin..."
git fetch origin

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Discarding local modifications (security fixes are on origin/main)..."
  git reset --hard HEAD
  git clean -fd
fi

# Untracked files that would block merge (e.g. old path_safety.py copies)
git clean -fd

echo "Resetting to origin/main..."
git reset --hard origin/main

echo "Installing shared huy-telemetry (local path; not on PyPI)..."
/usr/bin/python3 -m pip install -q -e "${REPO_ROOT}/shared/huy_telemetry"

echo "Installing libvirt agent (same interpreter as systemd: /usr/bin/python3)..."
cd "${AGENT_DIR}"
/usr/bin/python3 -m pip install -q -e ".[libvirt]"

echo "Installed agent package:"
/usr/bin/python3 -c "import huy_libvirt_agent; print(huy_libvirt_agent.__file__)"

if systemctl is-active --quiet huy-libvirt-agent 2>/dev/null; then
  echo "Restarting huy-libvirt-agent..."
  sudo systemctl restart huy-libvirt-agent
  systemctl is-active huy-libvirt-agent
else
  echo "huy-libvirt-agent systemd unit not active; skip restart."
fi

AGENT_BASE="${HUY_AGENT_BASE_URL:-}"
if [[ -n "$AGENT_BASE" ]]; then
  echo "Checking SSH relay WebSocket (set HUY_AGENT_BASE_URL to skip)..."
  if curl -k -sS -o /dev/null -w "%{http_code}" -H "Connection: Upgrade" -H "Upgrade: websocket" \
    "${AGENT_BASE%/}/api/v1/ssh/relay/ws" | grep -qE '^(101|400|426)'; then
    echo "    relay route reachable (WebSocket upgrade accepted or negotiable)"
  else
    echo "    WARNING: relay WebSocket may not be running — check agent logs and SSH_GATEWAY_SERVICE_TOKEN" >&2
  fi
fi

echo "Done. HEAD: $(git -C "${REPO_ROOT}" rev-parse --short HEAD)"
