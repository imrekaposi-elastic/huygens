"""SQLAlchemy models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    members: Mapped[list[OrganizationMember]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    external_subject: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    keycloak_realm: Mapped[str | None] = mapped_column(String(128), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    platform_roles: Mapped[list[UserPlatformRole]] = relationship(back_populates="user")
    org_memberships: Mapped[list[OrganizationMember]] = relationship(back_populates="user")
    api_keys: Mapped[list[ApiKey]] = relationship(back_populates="user")
    project_roles: Mapped[list[ProjectRoleAssignment]] = relationship(back_populates="user")
    idp_groups_seen: Mapped[list[UserIdpGroup]] = relationship(back_populates="user")


class UserPlatformRole(Base):
    __tablename__ = "user_platform_roles"
    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_user_platform_role"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)

    user: Mapped[User] = relationship(back_populates="platform_roles")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_org_member"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="org_memberships")
    organization: Mapped[Organization] = relationship(back_populates="members")
    roles: Mapped[list[OrganizationMemberRole]] = relationship(
        back_populates="member", cascade="all, delete-orphan"
    )


class OrganizationMemberRole(Base):
    __tablename__ = "organization_member_roles"
    __table_args__ = (UniqueConstraint("member_id", "role", name="uq_member_role"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    member_id: Mapped[str] = mapped_column(
        ForeignKey("organization_members.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False)

    member: Mapped[OrganizationMember] = relationship(back_populates="roles")


class ProjectRoleAssignment(Base):
    """Stub for Phase 1a — project service validates project_id in Phase 3."""

    __tablename__ = "project_role_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", "project_id", "role", name="uq_project_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="project_roles")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="api_keys")

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(UTC) >= self.expires_at


class IdpGroupMapping(Base):
    __tablename__ = "idp_group_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    idp_group_name: Mapped[str] = mapped_column(String(255), nullable=False)
    match_type: Mapped[str] = mapped_column(String(16), nullable=False, default="exact")
    huy_role: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserIdpGroup(Base):
    """Last IdP groups observed at SSO login (admin troubleshooting)."""

    __tablename__ = "user_idp_groups"
    __table_args__ = (UniqueConstraint("user_id", "group_name", name="uq_user_idp_group"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    group_name: Mapped[str] = mapped_column(String(255), nullable=False)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship(back_populates="idp_groups_seen")


class OidcLoginState(Base):
    __tablename__ = "oidc_login_states"

    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    code_verifier: Mapped[str] = mapped_column(String(128), nullable=False)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SshOrgCa(Base):
    """Per-organization SSH certificate authority (Phase 9)."""

    __tablename__ = "ssh_org_cas"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    public_key_openssh: Mapped[str] = mapped_column(Text, nullable=False)
    private_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SshAccountMapping(Base):
    __tablename__ = "ssh_account_mappings"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            "project_id",
            name="uq_ssh_account_mapping",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    linux_username: Mapped[str] = mapped_column(String(64), nullable=False)
    default_shell: Mapped[str] = mapped_column(String(128), nullable=False, default="/bin/bash")
    auto_provision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SshAccessGroup(Base):
    __tablename__ = "ssh_access_groups"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_ssh_access_group_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    idp_group_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    members: Mapped[list[SshAccessGroupMember]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    sudo_bindings: Mapped[list[SshSudoRuleGroupBinding]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class SshAccessGroupMember(Base):
    __tablename__ = "ssh_access_group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_ssh_group_member"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(
        ForeignKey("ssh_access_groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    group: Mapped[SshAccessGroup] = relationship(back_populates="members")


class SshSudoRule(Base):
    __tablename__ = "ssh_sudo_rules"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_ssh_sudo_rule_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    sudoers_fragment: Mapped[str | None] = mapped_column(Text, nullable=True)
    command_allow_list: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    allow_root: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    group_bindings: Mapped[list[SshSudoRuleGroupBinding]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class SshSudoRuleGroupBinding(Base):
    __tablename__ = "ssh_sudo_rule_group_bindings"
    __table_args__ = (UniqueConstraint("rule_id", "group_id", name="uq_ssh_sudo_rule_group"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    rule_id: Mapped[str] = mapped_column(
        ForeignKey("ssh_sudo_rules.id", ondelete="CASCADE"), nullable=False
    )
    group_id: Mapped[str] = mapped_column(
        ForeignKey("ssh_access_groups.id", ondelete="CASCADE"), nullable=False
    )

    rule: Mapped[SshSudoRule] = relationship(back_populates="group_bindings")
    group: Mapped[SshAccessGroup] = relationship(back_populates="sudo_bindings")
