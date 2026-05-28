#!/usr/bin/env bash
# Bootstrap a RHEL/Alma/Fedora hypervisor for huy-libvirt-agent (dev).
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

echo "==> Installing packages"
dnf install -y \
  libvirt-daemon-kvm libvirt-client libvirt-devel \
  qemu-kvm qemu-img \
  cloud-init \
  wireguard-tools nftables iptables-nft \
  iproute dnsmasq \
  python3-pip python3-devel gcc pkgconf-pkg-config git \
  xorriso

# mkisofs (from xorriso) is used when genisoimage package is absent (Alma 10+)
if ! command -v genisoimage >/dev/null 2>&1 && command -v mkisofs >/dev/null 2>&1; then
  ln -sf "$(command -v mkisofs)" /usr/local/bin/genisoimage
fi

echo "==> Enabling libvirt and IP forwarding"
systemctl enable --now libvirtd
sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-huy-libvirt-agent.conf

REPO_DIR="${REPO_DIR:-/opt/huygens}"
if [[ ! -d "$REPO_DIR/.git" ]]; then
  git clone https://github.com/imrekaposi-elastic/huygens.git "$REPO_DIR"
fi
git -C "$REPO_DIR" pull origin main

echo "==> Installing agent"
python3 -m pip install -e "$REPO_DIR/shared/huy_telemetry"
python3 -m pip install -e "$REPO_DIR/agents/libvirt[libvirt]"

mkdir -p /etc/huy-libvirt-agent /var/lib/huy-libvirt-agent
if [[ ! -f /etc/huy-libvirt-agent/env ]]; then
  cat > /etc/huy-libvirt-agent/env <<'ENV'
HUY_AGENT_TOKEN=change-me
HUY_AGENT_COUNTRY=NL
HUY_AGENT_CITY=Amsterdam
HUY_AGENT_COMPANY=Huygens
HUY_DATA_DIR=/var/lib/huy-libvirt-agent
HUY_BIND_HOST=0.0.0.0
HUY_BIND_PORT=8765
HUY_TLS_ENABLED=true
HUY_CLOUD_INIT_VALIDATION=schema
# HUY_PUBLIC_BASE_URL=https://your-hostname:8765
ENV
  echo "Edit /etc/huy-libvirt-agent/env (set HUY_AGENT_TOKEN)."
fi

echo "==> Install systemd service"
bash "$REPO_DIR/agents/libvirt/scripts/install-systemd.sh"

echo "==> Done. API: https://<host>:8765/docs (when HUY_TLS_ENABLED=true)"
