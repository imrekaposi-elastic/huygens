# Guest SSH onboarding (existing VMs)

Hypervisor-agnostic: run on the **Linux guest**, not on the hypervisor.

Canonical script (packaged for API bundles):

`shared/huy_ssh_onboard/src/huy_ssh_onboard/scripts/huy-ssh-onboard.sh`

## Control plane

- **Console:** Projects → VM → **Onboard script** (downloads a bundle with org CA + linux user).
- **API:** `GET /api/v1/projects/{project_id}/agents/{agent_id}/vms/{name}/guest-onboard`
- **Org API:** `GET /api/v1/organizations/{org_id}/ssh/guest-onboard?linux_username=huygens`

## On the guest

```bash
sudo bash huy-ssh-onboard-myvm.sh
```

Or manually:

```bash
export HUY_SSH_CA_PUBLIC_KEY='ssh-ed25519 AAAA... org-ca'
export HUY_LINUX_USER='huygens'
sudo -E bash huy-ssh-onboard.sh
```

No passwords are sent through the control plane. Use any existing admin path to copy/run the script (hypervisor console, serial, your CM tool, break-glass SSH, etc.).

## New VMs

Org SSH CA is merged into cloud-init automatically on create (see phase9-ssh-gateway.md). Use this guest script for **existing** workloads only.
