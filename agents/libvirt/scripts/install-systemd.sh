#!/usr/bin/env bash
# Install or refresh huy-libvirt-agent systemd unit (run as root on hypervisor).
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

REPO_DIR="${REPO_DIR:-/opt/huygens}"
AGENT_DIR="$REPO_DIR/agents/libvirt"
UNIT_SRC="$AGENT_DIR/systemd/huy-libvirt-agent.service"
UNIT_DST="/etc/systemd/system/huy-libvirt-agent.service"

if [[ ! -f "$UNIT_SRC" ]]; then
  echo "Missing $UNIT_SRC" >&2
  exit 1
fi

echo "==> Check host packages"
if ! command -v cloud-init >/dev/null 2>&1; then
  echo "Missing cloud-init (required). Install with:" >&2
  echo "  dnf install -y cloud-init   # RHEL/Alma/Fedora" >&2
  echo "  apt install -y cloud-init   # Debian/Ubuntu" >&2
  echo "See $AGENT_DIR/requirements-host.txt" >&2
  exit 1
fi

echo "==> Sync repo and Python package"
git -C "$REPO_DIR" pull origin main
python3 -m pip install -e "$AGENT_DIR[libvirt]"

echo "==> Install systemd unit"
cp "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload

echo "==> Stop manual/nohup instances"
pkill -f "python3 -m huy_libvirt_agent.main" 2>/dev/null || true
sleep 1

if [[ ! -f /etc/huy-libvirt-agent/env ]]; then
  echo "Create /etc/huy-libvirt-agent/env first (see .env.example)." >&2
  exit 1
fi

systemctl enable --now huy-libvirt-agent
systemctl status huy-libvirt-agent --no-pager
echo "Logs: journalctl -u huy-libvirt-agent -f"
