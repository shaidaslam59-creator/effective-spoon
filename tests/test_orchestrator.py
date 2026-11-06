from agents.inspector import InspectorAgent
from core.event_bus import EventBus
from core.models import TaskRequest, TaskStatus
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
