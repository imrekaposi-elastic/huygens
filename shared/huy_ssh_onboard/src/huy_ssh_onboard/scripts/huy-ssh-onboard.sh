#!/usr/bin/env bash
# Huygens guest SSH onboarding — run as root on the Linux guest.
# Hypervisor-agnostic (KVM, VMware, cloud VM, bare metal, etc.).
#
# Preferred: use a bundle from the control plane (env vars pre-set), e.g.
#   sudo bash huy-ssh-onboard-myvm.sh
#
# Manual:
#   export HUY_SSH_CA_PUBLIC_KEY='ssh-ed25519 AAAA... comment'
#   export HUY_LINUX_USER='huygens'
#   sudo -E bash huy-ssh-onboard.sh
#
# Or:
#   sudo bash huy-ssh-onboard.sh --ca-file /path/to/org-ca.pub --linux-user huygens

set -euo pipefail

CA_FILE="/etc/ssh/huy-org-ca.pem"
SSHD_DROPIN="/etc/ssh/sshd_config.d/99-huy-org-ca.conf"
LINUX_USER="${HUY_LINUX_USER:-}"
CA_INLINE="${HUY_SSH_CA_PUBLIC_KEY:-}"

usage() {
  cat <<'EOF'
Usage: huy-ssh-onboard.sh [options]

Configures OpenSSH to trust the Huygens organization SSH CA for audited access.
Idempotent — safe to re-run.

Options:
  --ca-file PATH       File containing org CA public key (OpenSSH one-line format)
  --linux-user NAME    Ensure this local account exists (optional)
  -h, --help           Show help

Environment:
  HUY_SSH_CA_PUBLIC_KEY   Org CA public key (OpenSSH one-line)
  HUY_LINUX_USER          Linux account for audited SSH (optional)
EOF
}

log() { echo "==> $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "$(id -u)" -ne 0 ]]; then
  die "run as root (sudo bash $0)"
fi

CA_PATH=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ca-file)
      CA_PATH="${2:-}"
      shift 2
      ;;
    --linux-user)
      LINUX_USER="${2:-}"
      shift 2
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

if [[ -n "$CA_PATH" ]]; then
  [[ -f "$CA_PATH" ]] || die "CA file not found: $CA_PATH"
  CA_INLINE="$(tr -d '\n' < "$CA_PATH")"
fi

[[ -n "$CA_INLINE" ]] || die "set HUY_SSH_CA_PUBLIC_KEY or pass --ca-file"

case "$CA_INLINE" in
  ssh-rsa\ *|ssh-ed25519\ *|ecdsa-sha2-*|sk-ssh-*)
    ;;
  *)
    die "CA key must be OpenSSH one-line format (ssh-ed25519, ssh-rsa, ...)"
    ;;
esac

log "Installing org CA to $CA_FILE"
install -d -m 755 /etc/ssh
printf '%s\n' "$CA_INLINE" > "$CA_FILE"
chmod 644 "$CA_FILE"

if [[ -d /etc/ssh/sshd_config.d ]]; then
  log "Writing $SSHD_DROPIN"
  printf 'TrustedUserCAKeys %s\n' "$CA_FILE" > "$SSHD_DROPIN"
  chmod 644 "$SSHD_DROPIN"
else
  log "sshd_config.d missing — appending TrustedUserCAKeys to sshd_config"
  if ! grep -q "^TrustedUserCAKeys $CA_FILE" /etc/ssh/sshd_config 2>/dev/null; then
    printf '\nTrustedUserCAKeys %s\n' "$CA_FILE" >> /etc/ssh/sshd_config
  fi
fi

if [[ -n "$LINUX_USER" ]]; then
  if id "$LINUX_USER" >/dev/null 2>&1; then
    log "Linux user $LINUX_USER already exists"
  else
    log "Creating linux user $LINUX_USER"
    useradd -m -s /bin/bash "$LINUX_USER" || die "useradd failed"
  fi
fi

log "Reloading sshd"
if systemctl reload sshd 2>/dev/null; then
  :
elif systemctl reload ssh 2>/dev/null; then
  :
elif service ssh reload 2>/dev/null; then
  :
else
  die "could not reload sshd — run: systemctl reload sshd"
fi

log "Done. Guest trusts Huygens org SSH CA."
log "Connect via Huygens ssh-gateway with IAM-signed user certificates (not passwords)."
