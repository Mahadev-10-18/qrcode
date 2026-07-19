import logging
from sqlmodel.ext.asyncio.session import AsyncSession
from ..models import AuditLog
from ..db import engine

logger = logging.getLogger(__name__)


async def log_audit(
    action: str,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
) -> None:
    try:
        async with AsyncSession(engine) as session:
            entry = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                detail=detail,
                ip_address=ip_address,
            )
            session.add(entry)
            await session.commit()
    except Exception as e:
        logger.error("Failed to write audit log: %s", e)
