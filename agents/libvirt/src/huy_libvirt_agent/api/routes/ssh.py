"""SSH trust bootstrap and relay status."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from huy_libvirt_agent.api.deps import StateDep, verify_token
from huy_libvirt_agent.services.ssh_trust import build_ssh_trust_cloud_config

router = APIRouter(
    prefix="/api/v1/vms",
    tags=["ssh"],
    dependencies=[Depends(verify_token)],
)


class SshTrustBody(BaseModel):
    ca_public_key_openssh: str = Field(min_length=20)
    linux_username: str = Field(min_length=1, max_length=64)
    sudoers_lines: list[str] = Field(default_factory=list)
    default_shell: str = "/bin/bash"


class SshTrustOut(BaseModel):
    vm_name: str
    cloud_config_snippet: str


@router.put("/{name}/ssh-trust", response_model=SshTrustOut)
async def apply_ssh_trust(name: str, body: SshTrustBody, state: StateDep) -> SshTrustOut:
    if state.libvirt is None:
        raise HTTPException(status_code=503, detail="libvirt unavailable")
    snippet = build_ssh_trust_cloud_config(
        ca_public_key_openssh=body.ca_public_key_openssh,
        linux_username=body.linux_username,
        sudoers_lines=body.sudoers_lines,
        default_shell=body.default_shell,
    )
    trust_dir = state.settings.data_dir / "ssh-trust" / name
    trust_dir.mkdir(parents=True, exist_ok=True)
    (trust_dir / "cloud-config.yaml").write_text(snippet, encoding="utf-8")
    return SshTrustOut(vm_name=name, cloud_config_snippet=snippet)


@router.get("/{name}/ssh-trust", response_model=SshTrustOut)
async def get_ssh_trust(name: str, state: StateDep) -> SshTrustOut:
    path = state.settings.data_dir / "ssh-trust" / name / "cloud-config.yaml"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="SSH trust not configured")
    return SshTrustOut(vm_name=name, cloud_config_snippet=path.read_text(encoding="utf-8"))
