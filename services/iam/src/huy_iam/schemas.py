"""API request/response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class OrgMembershipOut(BaseModel):
    organization_id: str
    roles: list[str]


class ProjectRoleOut(BaseModel):
    organization_id: str
    project_id: str
    role: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    username: str
    display_name: str | None
    is_active: bool
    platform_roles: list[str]
    org_memberships: list[OrgMembershipOut]
    project_roles: list[ProjectRoleOut]


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=256)
    display_name: str | None = None
    org_roles: list[str] = Field(default_factory=list)


class UserRolesUpdate(BaseModel):
    org_roles: list[str]


class PlatformRoleAssign(BaseModel):
    role: str = "platform_admin"


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


class ApiKeyCreated(BaseModel):
    id: str
    name: str
    key_prefix: str
    api_key: str
    expires_at: datetime | None


class ProjectRoleAssign(BaseModel):
    project_id: str
    role: str


class IdpGroupMappingCreate(BaseModel):
    idp_group_name: str = Field(min_length=1, max_length=255)
    match_type: str = Field(default="exact", pattern=r"^(exact|regex)$")
    huy_role: str = Field(min_length=1, max_length=64)
    priority: int = Field(default=0)
    enabled: bool = True


class IdpGroupMappingUpdate(BaseModel):
    idp_group_name: str | None = Field(default=None, min_length=1, max_length=255)
    match_type: str | None = Field(default=None, pattern=r"^(exact|regex)$")
    huy_role: str | None = Field(default=None, min_length=1, max_length=64)
    priority: int | None = None
    enabled: bool | None = None


class IdpGroupMappingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str | None
    idp_group_name: str
    match_type: str
    huy_role: str
    priority: int
    enabled: bool
    created_by: str | None
    created_at: datetime


class IdpGroupsOut(BaseModel):
    groups: list[str]
    organization_id: str | None = None


class OidcAuthorizeOut(BaseModel):
    authorization_url: str


# --- Phase 9 SSH policy ---


class SshAccountMappingCreate(BaseModel):
    user_id: str
    linux_username: str = Field(min_length=1, max_length=64, pattern=r"^[a-z_][a-z0-9_-]*$")
    project_id: str | None = None
    default_shell: str = "/bin/bash"
    auto_provision: bool = True


class SshAccountMappingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    user_id: str
    project_id: str | None
    linux_username: str
    default_shell: str
    auto_provision: bool
    created_at: datetime


class SshAccessGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    idp_group_name: str | None = None


class SshAccessGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    description: str | None
    idp_group_name: str | None
    created_at: datetime
    member_user_ids: list[str] = Field(default_factory=list)


class SshAccessGroupMemberAdd(BaseModel):
    user_id: str


class SshSudoRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    command_allow_list: list[str] = Field(default_factory=list)
    sudoers_fragment: str | None = None
    allow_root: bool = False


class SshSudoRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    command_allow_list: list[str]
    sudoers_fragment: str | None
    allow_root: bool
    enabled: bool
    created_at: datetime
    group_ids: list[str] = Field(default_factory=list)


class SshSudoRuleGroupBind(BaseModel):
    group_id: str


class SshCaPublicOut(BaseModel):
    organization_id: str
    public_key_openssh: str


class SshAuthorizeRequest(BaseModel):
    organization_id: str
    project_id: str
    vm_name: str
    vm_assigned_to_project: bool = True
    user_id: str
    user_email: str = ""
    user_username: str = ""
    platform_roles: list[str] = Field(default_factory=list)
    org_memberships: list[OrgMembershipOut] = Field(default_factory=list)
    project_roles: list[ProjectRoleOut] = Field(default_factory=list)


class SshAuthorizeResponse(BaseModel):
    allowed: bool
    reason: str
    linux_username: str | None = None
    sudoers_lines: list[str] = Field(default_factory=list)
    ca_public_key: str | None = None


class SshSignCertRequest(BaseModel):
    organization_id: str
    linux_username: str
    session_id: str
    public_key_openssh: str


class SshSignCertResponse(BaseModel):
    certificate_openssh: str
    valid_after: int
    valid_before: int


class SshPolicySnapshotOut(BaseModel):
    organization_id: str
    ca_public_key_openssh: str
    mappings: list[SshAccountMappingOut]
    sudo_rules: list[SshSudoRuleOut]
