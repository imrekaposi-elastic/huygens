# Hypervisor agents

| Agent | Hypervisor | Status |
|-------|------------|--------|
| [libvirt](libvirt/) | KVM / libvirt | Production on dommel |

**Release coupling:** Phase 6 topology and breakout require the libvirt agent version that
matches the control plane (`projects` / `breakout-controller`). Upgrade agents after every
control-plane deploy — [upgrade checklist](libvirt/README.md#upgrading-the-agent-phase-6).

**Phases 15–18 (lowest priority, adoption track):** **15** Proxmox · **16** AWS (RO) · **17** GCP (RO) · **18** Azure (RO) — see [docs/PHASED_PLAN.md](../docs/PHASED_PLAN.md#phases-1518--platform-adoption-track-lowest-priority). Libvirt remains the only CRUD and Phase 6 breakout path until a later phase.
