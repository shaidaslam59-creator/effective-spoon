"""Task persistence repository."""
from sqlalchemy.ext.asyncio import AsyncSession
from core.models import TaskRecord
from persistence.models import TaskRow

class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, task: TaskRecord) -> None:
        row = await self.session.get(TaskRow, str(task.id))
        values = dict(task_type=task.task_type, status=task.status.value, payload=task.payload,
                      result=task.result, error_code=task.error_code, correlation_id=task.correlation_id,
                      created_at=task.created_at, started_at=task.started_at, finished_at=task.finished_at)
        if row is None:
            self.session.add(TaskRow(id=str(task.id), **values))
        else:
            for key, value in values.items():
                setattr(row, key, value)
        await self.session.commit()
