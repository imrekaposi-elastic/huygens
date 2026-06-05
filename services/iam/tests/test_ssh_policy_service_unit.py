"""SSH policy service unit tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from huy_iam.models import Base, SshAccessGroup, SshSudoRule
from huy_iam.services import ssh_policy_service


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


@pytest.mark.asyncio
async def test_resolve_linux_username_prefers_project_mapping(session: AsyncSession) -> None:
    org_id = "org-1"
    user_id = "user-1"
    await ssh_policy_service.create_account_mapping(
        session,
        organization_id=org_id,
        user_id=user_id,
        linux_username="default-user",
        project_id=None,
    )
    await ssh_policy_service.create_account_mapping(
        session,
        organization_id=org_id,
        user_id=user_id,
        linux_username="project-user",
        project_id="proj-1",
    )
    resolved = await ssh_policy_service.resolve_linux_username(
        session,
        organization_id=org_id,
        user_id=user_id,
        project_id="proj-1",
    )
    assert resolved is not None
    assert resolved.linux_username == "project-user"


@pytest.mark.asyncio
async def test_sudo_rules_for_user_via_group(session: AsyncSession) -> None:
    org_id = "org-2"
    user_id = "user-2"
    group = await ssh_policy_service.create_access_group(
        session, organization_id=org_id, name="sudoers"
    )
    await ssh_policy_service.add_group_member(session, group, user_id)
    rule = await ssh_policy_service.create_sudo_rule(
        session,
        organization_id=org_id,
        name="status",
        command_allow_list=["/bin/systemctl status *"],
    )
    await ssh_policy_service.bind_sudo_rule_to_group(session, rule, group)
    rules = await ssh_policy_service.sudo_rules_for_user(session, org_id, user_id)
    assert len(rules) == 1
    assert rules[0].name == "status"


def test_sudoers_lines_fragment_and_commands() -> None:
    fragment_rule = SshSudoRule(
        organization_id="o",
        name="frag",
        command_allow_list="[]",
        sudoers_fragment="huygens ALL=(ALL) NOPASSWD: /bin/true",
        allow_root=False,
        enabled=True,
    )
    cmd_rule = SshSudoRule(
        organization_id="o",
        name="cmd",
        command_allow_list='["/usr/bin/journalctl"]',
        sudoers_fragment=None,
        allow_root=False,
        enabled=True,
    )
    root_rule = SshSudoRule(
        organization_id="o",
        name="root",
        command_allow_list="[]",
        sudoers_fragment=None,
        allow_root=True,
        enabled=True,
    )
    lines = ssh_policy_service.sudoers_lines_for_rules(
        "huygens", [fragment_rule, cmd_rule, root_rule]
    )
    assert "huygens ALL=(ALL) NOPASSWD: /bin/true" in lines
    assert "huygens ALL=(ALL) NOPASSWD: /usr/bin/journalctl" in lines
    assert "huygens ALL=(ALL:ALL) ALL" in lines


@pytest.mark.asyncio
async def test_policy_snapshot_for_user(session: AsyncSession) -> None:
    org_id = "org-3"
    user_id = "user-3"
    await ssh_policy_service.create_account_mapping(
        session,
        organization_id=org_id,
        user_id=user_id,
        linux_username="snap-user",
    )
    snap = await ssh_policy_service.policy_snapshot_for_user(
        session, organization_id=org_id, user_id=user_id, project_id=None
    )
    assert snap["linux_username"] == "snap-user"
    assert snap["auto_provision"] is True
