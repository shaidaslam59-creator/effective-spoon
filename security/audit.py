"""Structured audit event writer."""
import json
from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from persistence.models import AuditRow

class AuditLogger:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(self, event_type: str, actor: str, subject_id: str | None = None,
                     details: dict[str, object] | None = None) -> None:
        self.session.add(AuditRow(
            occurred_at=datetime.now(UTC), event_type=event_type[:100], actor=actor[:128],
            subject_id=subject_id[:128] if subject_id else None,
            details=json.dumps(details or {}, sort_keys=True, separators=(",", ":"), default=str)))
        await self.session.commit()
