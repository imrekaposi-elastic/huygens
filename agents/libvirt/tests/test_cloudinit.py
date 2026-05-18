"""Cloud-init builder tests."""

from pathlib import Path
from unittest.mock import patch

from huy_libvirt_agent.services.cloudinit import CloudInitBuilder


def test_build_with_genisoimage(tmp_path: Path) -> None:
    iso = tmp_path / "cidata.iso"
    with patch("shutil.which") as which:
        which.side_effect = lambda cmd: "/usr/bin/genisoimage" if cmd == "genisoimage" else None
        with patch("subprocess.run") as run:
            run.return_value = type("R", (), {"returncode": 0})()
            CloudInitBuilder().build(
                iso,
                "#cloud-config\npackages: []\n",
                "instance-id: test\n",
                ssh_keys=["ssh-rsa AAAAB3"],
            )
            assert run.called
            cmd = run.call_args[0][0]
            assert "genisoimage" in cmd[0]
