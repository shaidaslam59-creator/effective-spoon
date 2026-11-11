import asyncio

import pytest

from core.event_bus import EventBus
from core.models import TaskRequest, TaskStatus
from core.orchestrator import Orchestrator
from core.policy import DispatchPolicy
from core.registry import AgentRegistry


async def test_cancelled_task_persists_terminal_state_once():
    started = asyncio.Event()
    persisted_statuses: list[TaskStatus] = []

    class BlockingInspector:
        name = "blocking-inspector"
        capabilities = frozenset({"inspect"})

        async def execute(self, task, context):
            started.set()
            await asyncio.Event().wait()

    registry = AgentRegistry()
    registry.register(BlockingInspector())

    async def persist(task):
        persisted_statuses.append(task.status)

    service = Orchestrator(
        registry,
        DispatchPolicy(),
        EventBus(),
        persister=persist,
    )

    pending = asyncio.create_task(service.submit(TaskRequest(task_type="inspect")))
    await asyncio.wait_for(started.wait(), timeout=1)
    pending.cancel()

    with pytest.raises(asyncio.CancelledError):
        await pending

    assert persisted_statuses == [TaskStatus.RUNNING, TaskStatus.FAILED]
