/** Map ssh-gateway WebSocket errors to operator-friendly guidance. */
export function explainSshSessionError(raw: string): string {
  const msg = raw.replace(/^session failed:\s*/i, "").trim();
  if (!msg) return raw;

  if (/VM guest IP unknown|guest IP unknown/i.test(msg)) {
    return `${msg} — set guest_ip in agent metadata or wait for inventory poll after the VM gets an IP.`;
  }
  if (/no_account_mapping|account mapping/i.test(msg)) {
    return `${msg} — create an IAM SSH account mapping (Huygens user → linux username) or run scripts/ssh-bootstrap-dev.sh.`;
  }
  if (/rbac_denied|rbac denied/i.test(msg)) {
    return `${msg} — grant ssh_access on the project (or use org admin).`;
  }
  if (/ssh connect|unable to authenticate|handshake failed|publickey/i.test(msg)) {
    return (
      `${msg} — audited SSH uses IAM-signed certificates, not passwords. ` +
      "Create a new VM with org SSH CA merged into cloud-init, or download the guest onboard script and run it on the VM as root."
    );
  }
  if (/relay|9122|connection refused|dial tcp/i.test(msg)) {
    return (
      `${msg} — ssh-gateway could not reach the hypervisor relay. ` +
      "Upgrade the libvirt agent (WebSocket relay on :8765) or set SSH_RELAY_BIND=0.0.0.0 on the hypervisor."
    );
  }
  if (/sign cert|sign-cert/i.test(msg)) {
    return `${msg} — check IAM is up and SSH CA exists for the organization.`;
  }
  return msg;
}
