from huy_ssh_onboard import build_guest_onboard_bundle


def test_build_guest_onboard_bundle_embeds_ca_and_user() -> None:
    out = build_guest_onboard_bundle(
        ca_public_key_openssh="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI test",
        linux_username="huygens",
        organization_id="org-1",
        vm_name="web-01",
    )
    assert out["filename"] == "huy-ssh-onboard-web-01.sh"
    assert "huygens" in out["script"]
    assert "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI test" in out["script"]
    assert "TrustedUserCAKeys" in out["script"] or "huy-org-ca.pem" in out["script"]
    assert out["script"].startswith("#!/usr/bin/env bash")
