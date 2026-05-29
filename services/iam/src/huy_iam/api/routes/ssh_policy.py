"""SSH policy administration (Phase 9)."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from huy_iam.api.deps import CurrentUserDep, SessionDep
from huy_iam.roles import PERM_SSH_POLICY_MANAGE
from huy_iam.schemas import (
    SshAccessGroupCreate,
    SshAccessGroupMemberAdd,
    SshAccessGroupOut,
    SshAccountMappingCreate,
    SshAccountMappingOut,
    SshCaPublicOut,
    SshSudoRuleCreate,
    SshSudoRuleGroupBind,
    SshSudoRuleOut,
)
from huy_iam.services import audit, ssh_ca_service, ssh_policy_service, user_service

router = APIRouter(prefix="/api/v1/organizations", tags=["ssh-policy"])


def _require_policy_manage(user: CurrentUserDep, organization_id: str) -> None:
    if not user.has_permission(PERM_SSH_POLICY_MANAGE, organization_id):
        raise HTTPException(status_code=403, detail="Cannot manage SSH policy")


@router.get("/{organization_id}/ssh/ca", response_model=SshCaPublicOut)
async def get_ssh_ca(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> SshCaPublicOut:
    if not user.can_access_org(organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    from huy_iam.config import get_settings

    ca = await ssh_ca_service.ensure_org_ca(session, get_settings(), organization_id)
    await session.commit()
    return SshCaPublicOut(organization_id=organization_id, public_key_openssh=ca.public_key_openssh)


@router.get("/{organization_id}/ssh/guest-onboard")
async def get_guest_onboard_bundle(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
    linux_username: str | None = None,
    vm_name: str | None = None,
) -> dict:
    """Hypervisor-agnostic script to run on an existing Linux guest (any platform)."""
    from huy_iam.config import get_settings
    from huy_ssh_onboard import build_guest_onboard_bundle

    if not user.can_access_org(organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    settings = get_settings()
    ca = await ssh_ca_service.ensure_org_ca(session, settings, organization_id)
    resolved = linux_username
    if not resolved:
        mapping = await ssh_policy_service.resolve_linux_username(
            session,
            organization_id=organization_id,
            user_id=user.user_id,
            project_id=None,
        )
        resolved = mapping.linux_username if mapping else None
    if not resolved:
        resolved = "huygens"
    await session.commit()
    return build_guest_onboard_bundle(
        ca_public_key_openssh=ca.public_key_openssh,
        linux_username=resolved,
        organization_id=organization_id,
        vm_name=vm_name,
    )


@router.get("/{organization_id}/ssh/account-mappings", response_model=list[SshAccountMappingOut])
async def list_mappings(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[SshAccountMappingOut]:
    if not user.can_access_org(organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    rows = await ssh_policy_service.list_account_mappings(session, organization_id)
    return [SshAccountMappingOut.model_validate(r) for r in rows]


@router.post(
    "/{organization_id}/ssh/account-mappings",
    response_model=SshAccountMappingOut,
    status_code=201,
)
async def create_mapping(
    organization_id: str,
    body: SshAccountMappingCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> SshAccountMappingOut:
    _require_policy_manage(user, organization_id)
    row = await ssh_policy_service.create_account_mapping(
        session,
        organization_id=organization_id,
        user_id=body.user_id,
        linux_username=body.linux_username,
        project_id=body.project_id,
        default_shell=body.default_shell,
        auto_provision=body.auto_provision,
    )
    await session.commit()
    await audit.record_audit(
        organization_id=organization_id,
        actor_user_id=user.user_id,
        action="ssh.account_mapping.create",
        resource_type="ssh_account_mapping",
        resource_id=row.id,
        message=body.linux_username,
    )
    await session.commit()
    return SshAccountMappingOut.model_validate(row)


@router.delete("/{organization_id}/ssh/account-mappings/{mapping_id}", status_code=204)
async def delete_mapping(
    organization_id: str,
    mapping_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    _require_policy_manage(user, organization_id)
    row = await ssh_policy_service.get_account_mapping(session, mapping_id)
    if row is None or row.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Mapping not found")
    await ssh_policy_service.delete_account_mapping(session, row)
    await session.commit()
    await audit.record_audit(
        organization_id=organization_id,
        actor_user_id=user.user_id,
        action="ssh.account_mapping.delete",
        resource_type="ssh_account_mapping",
        resource_id=mapping_id,
    )
    await session.commit()


@router.get("/{organization_id}/ssh/access-groups", response_model=list[SshAccessGroupOut])
async def list_groups(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[SshAccessGroupOut]:
    if not user.can_access_org(organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    rows = await ssh_policy_service.list_access_groups(session, organization_id)
    return [
        SshAccessGroupOut(
            id=g.id,
            organization_id=g.organization_id,
            name=g.name,
            description=g.description,
            idp_group_name=g.idp_group_name,
            created_at=g.created_at,
            member_user_ids=[m.user_id for m in g.members],
        )
        for g in rows
    ]


@router.post(
    "/{organization_id}/ssh/access-groups",
    response_model=SshAccessGroupOut,
    status_code=201,
)
async def create_group(
    organization_id: str,
    body: SshAccessGroupCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> SshAccessGroupOut:
    _require_policy_manage(user, organization_id)
    row = await ssh_policy_service.create_access_group(
        session,
        organization_id=organization_id,
        name=body.name,
        description=body.description,
        idp_group_name=body.idp_group_name,
    )
    await session.commit()
    await audit.record_audit(
        organization_id=organization_id,
        actor_user_id=user.user_id,
        action="ssh.access_group.create",
        resource_type="ssh_access_group",
        resource_id=row.id,
        message=body.name,
    )
    await session.commit()
    return SshAccessGroupOut(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        description=row.description,
        idp_group_name=row.idp_group_name,
        created_at=row.created_at,
        member_user_ids=[],
    )


@router.post(
    "/{organization_id}/ssh/access-groups/{group_id}/members",
    status_code=204,
)
async def add_group_member(
    organization_id: str,
    group_id: str,
    body: SshAccessGroupMemberAdd,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    _require_policy_manage(user, organization_id)
    groups = await ssh_policy_service.list_access_groups(session, organization_id)
    group = next((g for g in groups if g.id == group_id), None)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    await ssh_policy_service.add_group_member(session, group, body.user_id)
    await session.commit()


@router.get("/{organization_id}/ssh/sudo-rules", response_model=list[SshSudoRuleOut])
async def list_sudo_rules(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[SshSudoRuleOut]:
    if not user.can_access_org(organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    rows = await ssh_policy_service.list_sudo_rules(session, organization_id)
    out: list[SshSudoRuleOut] = []
    for r in rows:
        out.append(
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
        )
    return out


@router.post(
    "/{organization_id}/ssh/sudo-rules",
    response_model=SshSudoRuleOut,
    status_code=201,
)
async def create_sudo_rule(
    organization_id: str,
    body: SshSudoRuleCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> SshSudoRuleOut:
    _require_policy_manage(user, organization_id)
    row = await ssh_policy_service.create_sudo_rule(
        session,
        organization_id=organization_id,
        name=body.name,
        command_allow_list=body.command_allow_list,
        sudoers_fragment=body.sudoers_fragment,
        allow_root=body.allow_root,
    )
    await session.commit()
    await audit.record_audit(
        organization_id=organization_id,
        actor_user_id=user.user_id,
        action="ssh.sudo_rule.create",
        resource_type="ssh_sudo_rule",
        resource_id=row.id,
        message=body.name,
    )
    await session.commit()
    return SshSudoRuleOut(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        command_allow_list=body.command_allow_list,
        sudoers_fragment=row.sudoers_fragment,
        allow_root=row.allow_root,
        enabled=row.enabled,
        created_at=row.created_at,
        group_ids=[],
    )


@router.post(
    "/{organization_id}/ssh/sudo-rules/{rule_id}/groups",
    status_code=204,
)
async def bind_sudo_group(
    organization_id: str,
    rule_id: str,
    body: SshSudoRuleGroupBind,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    _require_policy_manage(user, organization_id)
    rules = await ssh_policy_service.list_sudo_rules(session, organization_id)
    rule = next((r for r in rules if r.id == rule_id), None)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    groups = await ssh_policy_service.list_access_groups(session, organization_id)
    group = next((g for g in groups if g.id == body.group_id), None)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    await ssh_policy_service.bind_sudo_rule_to_group(session, rule, group)
    await session.commit()
