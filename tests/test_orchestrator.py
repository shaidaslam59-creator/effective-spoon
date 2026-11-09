from uuid import UUID

from agents.inspector import InspectorAgent
from core.event_bus import EventBus
from core.models import TaskRecord, TaskRequest, TaskStatus
from core.orchestrator import Orchestrator
from core.policy import DispatchPolicy
from core.registry import AgentRegistry


async def test_inspector_task_succeeds():
    registry = AgentRegistry()
    registry.register(InspectorAgent())
    service = Orchestrator(registry, DispatchPolicy(), EventBus())
    result = await service.submit(TaskRequest(task_type="inspect", payload={"sample": 1}))
    assert result.status is TaskStatus.SUCCEEDED
    assert result.result is not None


async def test_unknown_task_is_rejected():
    registry = AgentRegistry()
    registry.register(InspectorAgent())
    service = Orchestrator(registry, DispatchPolicy(), EventBus())
    result = await service.submit(TaskRequest(task_type="unknown"))
    assert result.status is TaskStatus.REJECTED


async def test_persister_records_running_and_terminal_states():
    persisted_states: list[tuple[UUID, TaskStatus]] = []

    async def persist(task: TaskRecord) -> None:
        persisted_states.append((task.id, task.status))

    registry = AgentRegistry()
    registry.register(InspectorAgent())
    service = Orchestrator(registry, DispatchPolicy(), EventBus(), persister=persist)

    result = await service.submit(TaskRequest(task_type="inspect", payload={"sample": 1}))

    assert result.status is TaskStatus.SUCCEEDED
    assert persisted_states == [
        (result.id, TaskStatus.RUNNING),
        (result.id, TaskStatus.SUCCEEDED),
    ]
