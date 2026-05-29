"""SSH account mappings, access groups, and sudo rules."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from huy_iam.models import (
    SshAccessGroup,
    SshAccessGroupMember,
    SshAccountMapping,
    SshSudoRule,
    SshSudoRuleGroupBinding,
    UserIdpGroup,
)


async def list_account_mappings(
    session: AsyncSession, organization_id: str
) -> list[SshAccountMapping]:
    result = await session.scalars(
        select(SshAccountMapping)
        .where(SshAccountMapping.organization_id == organization_id)
        .order_by(SshAccountMapping.linux_username)
    )
    return list(result.all())


async def create_account_mapping(
    session: AsyncSession,
    *,
    organization_id: str,
    user_id: str,
    linux_username: str,
    project_id: str | None = None,
    default_shell: str = "/bin/bash",
    auto_provision: bool = True,
) -> SshAccountMapping:
    row = SshAccountMapping(
        organization_id=organization_id,
        user_id=user_id,
        project_id=project_id,
        linux_username=linux_username,
        default_shell=default_shell,
        auto_provision=auto_provision,
    )
    session.add(row)
    await session.flush()
    return row


async def get_account_mapping(session: AsyncSession, mapping_id: str) -> SshAccountMapping | None:
    return await session.get(SshAccountMapping, mapping_id)


async def delete_account_mapping(session: AsyncSession, row: SshAccountMapping) -> None:
    await session.delete(row)


async def resolve_linux_username(
    session: AsyncSession,
    *,
    organization_id: str,
    user_id: str,
    project_id: str | None,
) -> SshAccountMapping | None:
    result = await session.scalars(
        select(SshAccountMapping).where(
            SshAccountMapping.organization_id == organization_id,
            SshAccountMapping.user_id == user_id,
        )
    )
    rows = list(result.all())
    if not rows:
        return None
    if project_id:
        for row in rows:
            if row.project_id == project_id:
                return row
    for row in rows:
        if row.project_id is None:
            return row
    return rows[0]


async def list_access_groups(session: AsyncSession, organization_id: str) -> list[SshAccessGroup]:
    result = await session.scalars(
        select(SshAccessGroup)
        .where(SshAccessGroup.organization_id == organization_id)
        .options(selectinload(SshAccessGroup.members))
        .order_by(SshAccessGroup.name)
    )
    return list(result.all())


async def create_access_group(
    session: AsyncSession,
    *,
    organization_id: str,
    name: str,
    description: str | None = None,
    idp_group_name: str | None = None,
) -> SshAccessGroup:
    row = SshAccessGroup(
        organization_id=organization_id,
        name=name,
        description=description,
        idp_group_name=idp_group_name,
    )
    session.add(row)
    await session.flush()
    return row


async def add_group_member(
    session: AsyncSession, group: SshAccessGroup, user_id: str
) -> SshAccessGroupMember:
    member = SshAccessGroupMember(group_id=group.id, user_id=user_id)
    session.add(member)
    await session.flush()
    return member


async def list_sudo_rules(session: AsyncSession, organization_id: str) -> list[SshSudoRule]:
    result = await session.scalars(
        select(SshSudoRule)
        .where(SshSudoRule.organization_id == organization_id)
        .options(selectinload(SshSudoRule.group_bindings))
        .order_by(SshSudoRule.name)
    )
    return list(result.all())


async def create_sudo_rule(
    session: AsyncSession,
    *,
    organization_id: str,
    name: str,
    command_allow_list: list[str],
    sudoers_fragment: str | None = None,
    allow_root: bool = False,
) -> SshSudoRule:
    row = SshSudoRule(
        organization_id=organization_id,
        name=name,
        command_allow_list=json.dumps(command_allow_list),
        sudoers_fragment=sudoers_fragment,
        allow_root=allow_root,
    )
    session.add(row)
    await session.flush()
    return row


async def bind_sudo_rule_to_group(
    session: AsyncSession, rule: SshSudoRule, group: SshAccessGroup
) -> SshSudoRuleGroupBinding:
    binding = SshSudoRuleGroupBinding(rule_id=rule.id, group_id=group.id)
    session.add(binding)
    await session.flush()
    return binding


async def user_group_ids(session: AsyncSession, organization_id: str, user_id: str) -> set[str]:
    groups = await list_access_groups(session, organization_id)
    member_group_ids: set[str] = set()
    idp_names = {
        g.group_name
        for g in (
            await session.scalars(select(UserIdpGroup).where(UserIdpGroup.user_id == user_id))
        ).all()
    }
    for group in groups:
        if any(m.user_id == user_id for m in group.members):
            member_group_ids.add(group.id)
        elif group.idp_group_name and group.idp_group_name in idp_names:
            member_group_ids.add(group.id)
    return member_group_ids


async def sudo_rules_for_user(
    session: AsyncSession, organization_id: str, user_id: str
) -> list[SshSudoRule]:
    group_ids = await user_group_ids(session, organization_id, user_id)
    if not group_ids:
        return []
    rules = await list_sudo_rules(session, organization_id)
    allowed: list[SshSudoRule] = []
    for rule in rules:
        if not rule.enabled:
            continue
        if any(b.group_id in group_ids for b in rule.group_bindings):
            allowed.append(rule)
    return allowed


def sudoers_lines_for_rules(linux_username: str, rules: list[SshSudoRule]) -> list[str]:
    lines: list[str] = []
    for rule in rules:
        if rule.sudoers_fragment:
            lines.append(rule.sudoers_fragment.strip())
            continue
        try:
            commands = json.loads(rule.command_allow_list or "[]")
        except json.JSONDecodeError:
            commands = []
        if not commands and not rule.allow_root:
            continue
        if rule.allow_root and not commands:
            lines.append(f"{linux_username} ALL=(ALL:ALL) ALL")
        elif commands:
            cmd_list = ", ".join(commands)
            lines.append(f"{linux_username} ALL=(ALL) NOPASSWD: {cmd_list}")
    return lines


async def policy_snapshot_for_user(
    session: AsyncSession,
    *,
    organization_id: str,
    user_id: str,
    project_id: str | None,
) -> dict:
    mapping = await resolve_linux_username(
        session, organization_id=organization_id, user_id=user_id, project_id=project_id
    )
    rules = await sudo_rules_for_user(session, organization_id, user_id)
    linux_user = mapping.linux_username if mapping else None
    sudoers = sudoers_lines_for_rules(linux_user, rules) if linux_user else []
    return {
        "linux_username": linux_user,
        "default_shell": mapping.default_shell if mapping else "/bin/bash",
        "auto_provision": mapping.auto_provision if mapping else False,
        "sudoers_lines": sudoers,
        "sudo_rule_ids": [r.id for r in rules],
    }
