"""Cloud-init ISO generation."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


def _iso_tool() -> str | None:
    for name in ("cloud-localds", "genisoimage", "mkisofs"):
        if shutil.which(name):
            return name
    return None


class CloudInitBuilder:
    def build(
        self,
        output_iso: Path,
        user_data: str,
        meta_data: str,
        network_config: str | None = None,
        ssh_keys: list[str] | None = None,
    ) -> Path:
        user_data_final = user_data
        if ssh_keys and "ssh_authorized_keys" not in user_data:
            keys_yaml = "\n".join(f"    - {k}" for k in ssh_keys)
            if "#cloud-config" in user_data:
                user_data_final = user_data.rstrip() + f"\nssh_authorized_keys:\n{keys_yaml}\n"
            else:
                user_data_final = f"#cloud-config\nssh_authorized_keys:\n{keys_yaml}\n" + user_data

        output_iso.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "user-data").write_text(user_data_final)
            (tmp_path / "meta-data").write_text(meta_data)
            if network_config:
                (tmp_path / "network-config").write_text(network_config)

            tool = _iso_tool()
            if tool == "cloud-localds":
                cmd = ["cloud-localds", str(output_iso), str(tmp_path / "user-data")]
                if network_config:
                    cmd.extend(["--network-config", str(tmp_path / "network-config")])
                cmd.append(str(tmp_path / "meta-data"))
                subprocess.run(cmd, check=True, capture_output=True)
            elif tool in ("genisoimage", "mkisofs"):
                subprocess.run(
                    [
                        tool,
                        "-output",
                        str(output_iso),
                        "-volid",
                        "cidata",
                        "-joliet",
                        "-rock",
                        str(tmp_path / "user-data"),
                        str(tmp_path / "meta-data"),
                    ]
                    + ([str(tmp_path / "network-config")] if network_config else []),
                    check=True,
                    capture_output=True,
                )
            else:
                raise RuntimeError("No cloud-localds, genisoimage, or mkisofs found on PATH")

        logger.info("cloud_init_iso_created", path=str(output_iso))
        return output_iso
