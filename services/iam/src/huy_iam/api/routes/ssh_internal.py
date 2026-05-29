"""Internal SSH APIs for ssh-gateway and agents."""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException

from huy_iam.api.deps_internal import InternalServiceDep, SettingsDep
from huy_iam.auth_context import AuthContext, OrgMembership, ProjectRoleGrant
from huy_iam.api.deps import SessionDep
from huy_iam.schemas import (
    SshAuthorizeRequest,
    SshAuthorizeResponse,
    SshPolicySnapshotOut,
    SshSignCertRequest,
    SshSignCertResponse,
    SshAccountMappingOut,
    SshSudoRuleOut,
)
from huy_iam.services import ssh_authorize_service, ssh_ca_service, ssh_policy_service

router = APIRouter(prefix="/internal/v1/ssh", tags=["ssh-internal"])


@router.post("/authorize", response_model=SshAuthorizeResponse)
async def authorize(
    body: SshAuthorizeRequest,
    _svc: InternalServiceDep,
    session: SessionDep,
    settings: SettingsDep,
) -> SshAuthorizeResponse:
    user = AuthContext(
        user_id=body.user_id,
        email=body.user_email,
        username=body.user_username,
        platform_roles=body.platform_roles,
        org_memberships=[
            OrgMembership(organization_id=m.organization_id, roles=m.roles)
            for m in body.org_memberships
        ],
        project_roles=[
            ProjectRoleGrant(
                organization_id=g.organization_id,
                project_id=g.project_id,
                role=g.role,
            )
            for g in body.project_roles
        ],
    )
    result = await ssh_authorize_service.authorize_ssh_session(
        session,
        settings,
        user=user,
        organization_id=body.organization_id,
        project_id=body.project_id,
        vm_name=body.vm_name,
        vm_assigned_to_project=body.vm_assigned_to_project,
    )
    return SshAuthorizeResponse(
        allowed=result.allowed,
        reason=result.reason,
        linux_username=result.linux_username,
        sudoers_lines=result.sudoers_lines or [],
        ca_public_key=result.ca_public_key,
    )


@router.post("/sign-cert", response_model=SshSignCertResponse)
async def sign_cert(
    body: SshSignCertRequest,
    _svc: InternalServiceDep,
    session: SessionDep,
    settings: SettingsDep,
) -> SshSignCertResponse:
    ca = await ssh_ca_service.ensure_org_ca(session, settings, body.organization_id)
    private_pem = ssh_ca_service.decrypt_ca_private_key(settings, ca)
    ttl = settings.ssh_cert_ttl_seconds
    now = int(time.time())
    valid_before = now + ttl
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        ca_path = tmp_path / "ca"
        pub_path = tmp_path / "user.pub"
        cert_path = tmp_path / "user-cert.pub"
        ca_path.write_text(private_pem)
        pub_path.write_text(body.public_key_openssh.strip() + "\n")
        subprocess.run(
            [
                "ssh-keygen",
                "-s",
                str(ca_path),
                "-I",
                body.session_id[:64],
                "-n",
                body.linux_username,
                "-V",
                f"{now}:{valid_before}",
                str(pub_path),
            ],
            check=True,
            capture_output=True,
        )
        cert_line = cert_path.read_text().strip()
    return SshSignCertResponse(
        certificate_openssh=cert_line,
        valid_after=now,
        valid_before=valid_before,
    )


@router.get("/policy-snapshot/{organization_id}", response_model=SshPolicySnapshotOut)
async def policy_snapshot(
    organization_id: str,
    _svc: InternalServiceDep,
    session: SessionDep,
    settings: SettingsDep,
) -> SshPolicySnapshotOut:
    ca = await ssh_ca_service.ensure_org_ca(session, settings, organization_id)
    mappings = await ssh_policy_service.list_account_mappings(session, organization_id)
    rules = await ssh_policy_service.list_sudo_rules(session, organization_id)
    return SshPolicySnapshotOut(
        organization_id=organization_id,
        ca_public_key_openssh=ca.public_key_openssh,
        mappings=[SshAccountMappingOut.model_validate(m) for m in mappings],
        sudo_rules=[
            SshSudoRuleOut(
                id=r.id,
                organization_id=r.organization_id,
                name=r.name,
                command_allow_list=json.loads(r.command_allow_list or "[]"),
                sudoers_fragment=r.sudoers_fragment,
                allow_root=r.allow_root,
                enabled=r.enabled,
                created_at=r.created_at,
                group_ids=[b.group_id for b in r.group_bindings],
            )
            for r in rules
        ],
    )
