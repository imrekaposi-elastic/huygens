"""First-run bootstrap: platform admin user."""

from __future__ import annotations

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_iam.config import Settings
from huy_iam.models import User
from huy_iam.roles import PlatformRole
from huy_iam.services import user_service

logger = structlog.get_logger(__name__)


async def bootstrap_platform_admin(session: AsyncSession, settings: Settings) -> None:
    count = await session.scalar(select(func.count()).select_from(User))
    if count and count > 0:
        return

    user = await user_service.create_user(
        session,
        email=settings.bootstrap_admin_email,
        username=settings.bootstrap_admin_username,
        password=settings.bootstrap_admin_password,
        display_name="Platform Administrator",
    )
    await user_service.grant_platform_role(session, user.id, PlatformRole.PLATFORM_ADMIN)
    await session.commit()
    logger.warning(
        "bootstrap_platform_admin_created",
        username=settings.bootstrap_admin_username,
        hint="Change BOOTSTRAP_ADMIN_PASSWORD and rotate JWT_SECRET before production",
    )
