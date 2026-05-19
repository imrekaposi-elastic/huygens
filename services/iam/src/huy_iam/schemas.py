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
