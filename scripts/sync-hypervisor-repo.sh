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
python3 -m pip install -q -e "${REPO_ROOT}/shared/huy_telemetry"

echo "Installing libvirt agent..."
cd "${AGENT_DIR}"
python3 -m pip install -q -e ".[libvirt]"

if systemctl is-active --quiet huy-libvirt-agent 2>/dev/null; then
  echo "Restarting huy-libvirt-agent..."
  sudo systemctl restart huy-libvirt-agent
  systemctl is-active huy-libvirt-agent
else
  echo "huy-libvirt-agent systemd unit not active; skip restart."
fi

echo "Done. HEAD: $(git -C "${REPO_ROOT}" rev-parse --short HEAD)"
