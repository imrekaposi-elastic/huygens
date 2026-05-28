# Host package requirements

The agent requires the following OS packages on the KVM hypervisor. Install for your distribution before deploying the agent.

## Capability matrix

| Capability | Commands | Debian 12 / Ubuntu 22.04+ | RHEL 9 / Rocky 9 / Alma 9 | Fedora 40+ | openSUSE Leap 15.6+ |
|------------|----------|---------------------------|---------------------------|------------|---------------------|
| KVM / libvirt | virsh, libvirt API | libvirt-daemon-system, libvirt-clients, qemu-system-x86, qemu-utils | libvirt-daemon-kvm, libvirt-client, qemu-kvm, qemu-img | same as RHEL | libvirt-daemon-qemu, libvirt-client, qemu-kvm, qemu-tools |
| DHCP (vnet) | dnsmasq | dnsmasq (libvirt dep) | dnsmasq | dnsmasq | dnsmasq |
| Disk images | qemu-img | qemu-utils | qemu-img | qemu-img | qemu-tools |
| Cloud-init validation | cloud-init schema | **cloud-init** | **cloud-init** | **cloud-init** | **cloud-init** |
| Cloud-init ISO | cloud-localds | cloud-image-utils | genisoimage (fallback) | cloud-image-utils | cloud-image-utils or genisoimage |
| Cloud-init fallback | genisoimage | genisoimage | genisoimage | genisoimage | genisoimage |
| Cloud-init (Alma 10+) | — | `xorriso` → `mkisofs` | — | — | — |
| WireGuard breakout | wg, wg-quick | wireguard, wireguard-tools | wireguard-tools | wireguard-tools | wireguard-tools |
| Flat L2 breakout | ip, bridge | iproute2, bridge-utils | iproute, bridge-utils | iproute, bridge-utils | iproute2, bridge-utils |
| Firewall / NAT | nft, iptables | nftables, iptables | nftables, iptables-nft | nftables, iptables-nft | nftables, iptables |

## Install one-liners

### Debian / Ubuntu

```bash
sudo apt update && sudo apt install -y \
  libvirt-daemon-system libvirt-clients qemu-system-x86 qemu-utils \
  cloud-init cloud-image-utils genisoimage wireguard wireguard-tools \
  nftables iptables iproute2 bridge-utils dnsmasq
sudo usermod -aG libvirt "$USER"
```

### RHEL / Rocky / Alma

```bash
sudo dnf install -y \
  libvirt-daemon-kvm libvirt-client libvirt-devel qemu-kvm qemu-img \
  cloud-init wireguard-tools nftables iptables-nft \
  iproute dnsmasq python3-pip python3-devel gcc pkgconf-pkg-config git \
  xorriso
# Alma 10+: genisoimage package absent; agent accepts mkisofs from xorriso
sudo ln -sf "$(command -v mkisofs)" /usr/local/bin/genisoimage 2>/dev/null || true
sudo systemctl enable --now libvirtd
```

Or run [`scripts/setup-hypervisor.sh`](../scripts/setup-hypervisor.sh) on the host.

### Fedora

```bash
sudo dnf install -y \
  libvirt-daemon-kvm libvirt-client qemu-kvm qemu-img cloud-init cloud-image-utils \
  genisoimage wireguard-tools nftables iptables-nft iproute bridge-utils dnsmasq
```

### openSUSE Leap

```bash
sudo zypper install -y \
  libvirt-daemon-qemu libvirt-client qemu-kvm qemu-tools cloud-init \
  genisoimage wireguard-tools nftables iptables iproute2 bridge-utils dnsmasq
```

### Arch Linux

```bash
sudo pacman -S libvirt qemu-full cloud-init iptables-nft nftables wireguard-tools cdrtools iproute2 bridge-utils dnsmasq
```

## Python (pip)

From the monorepo root (e.g. `/opt/huygens`):

```bash
pip install -e shared/huy_telemetry
pip install -e "agents/libvirt[libvirt]"
```

`huy-telemetry` is not published to PyPI; plain `pip install` on the agent alone will fail.

Pulls agent dependencies including `jsonschema` (used with the system `cloud-init` package for schema validation).

## Non-package requirements

| Requirement | Detail |
|-------------|--------|
| cloud-init | **Required** OS package for profile validation (`requirements-host.txt`) |
| CPU | Intel VT-x or AMD-V; KVM module loaded |
| Permissions | `libvirt` group; `CAP_NET_ADMIN` for networking (agent typically runs as root) |
| Sysctl | `net.ipv4.ip_forward=1` when SNAT/DNAT is used |
| libvirt URI | `qemu:///system` |
| Python | 3.11+ for the agent (installed via pip, not distro meta-package) |
| Metrics | `psutil` (installed via pip with the agent) for host CPU/memory/disk on `/metrics` |

## Sysctl

```bash
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-huy-libvirt-agent.conf
sudo sysctl --system
```
