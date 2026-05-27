# Hypervisor agents

| Agent | Hypervisor | Status |
|-------|------------|--------|
| [libvirt](libvirt/) | KVM / libvirt | Production on dommel |

**Release coupling:** Phase 6 topology and breakout require the libvirt agent version that
matches the control plane (`projects` / `breakout-controller`). Upgrade agents after every
control-plane deploy — [upgrade checklist](libvirt/README.md#upgrading-the-agent-phase-6).

Future: additional agents may live here under the same monorepo layout.
