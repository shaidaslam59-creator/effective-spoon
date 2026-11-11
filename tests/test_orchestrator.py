import asyncio

import pytest

from agents.inspector import InspectorAgent
from core.event_bus import EventBus
from core.models import AgentResult, TaskRequest, TaskStatus
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


async def test_task_is_persisted_before_execution_and_after_completion():
    registry = AgentRegistry()
    registry.register(InspectorAgent())
    persisted_statuses: list[TaskStatus] = []

    async def persist(task):
        persisted_statuses.append(task.status)

    service = Orchestrator(
        registry,
        DispatchPolicy(),
        EventBus(),
        persister=persist,
    )

    result = await service.submit(TaskRequest(task_type="inspect", payload={"sample": 1}))

    assert result.status is TaskStatus.SUCCEEDED
    assert persisted_statuses == [TaskStatus.RUNNING, TaskStatus.SUCCEEDED]


async def test_rejected_task_is_persisted():
    registry = AgentRegistry()
    registry.register(InspectorAgent())
    persisted_statuses: list[TaskStatus] = []

    async def persist(task):
        persisted_statuses.append(task.status)

    service = Orchestrator(
        registry,
        DispatchPolicy(),
        EventBus(),
        persister=persist,
    )

    result = await service.submit(TaskRequest(task_type="unknown"))

    assert result.status is TaskStatus.REJECTED
    assert persisted_statuses == [TaskStatus.REJECTED]


async def test_timed_out_task_persists_terminal_status():
    class SlowInspector:
        name = "slow-inspector"
        capabilities = frozenset({"inspect"})

        async def execute(self, task, context):
            await asyncio.sleep(0.1)
            return AgentResult(agent_name=self.name, output={})

    registry = AgentRegistry()
    registry.register(SlowInspector())
    persisted_statuses: list[TaskStatus] = []

    async def persist(task):
        persisted_statuses.append(task.status)

    service = Orchestrator(
        registry,
        DispatchPolicy(),
        EventBus(),
        timeout_seconds=0.01,
        persister=persist,
    )

    result = await service.submit(TaskRequest(task_type="inspect"))

    assert result.status is TaskStatus.TIMED_OUT
    assert result.error_code == "execution_timeout"
    assert persisted_statuses == [TaskStatus.RUNNING, TaskStatus.TIMED_OUT]


async def test_cancelled_task_records_failure_before_propagating_cancellation():
    started = asyncio.Event()
    persisted_statuses: list[TaskStatus] = []

    class BlockingInspector:
        name = "blocking-inspector"
        capabilities = frozenset({"inspect"})

        async def execute(self, task, context):
            started.set()
            await asyncio.Event().wait()
            return AgentResult(agent_name=self.name, output={})

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

    assert persisted_statuses[0] is TaskStatus.RUNNING
    assert TaskStatus.FAILED in persisted_statuses


async def test_running_state_persistence_failure_prevents_agent_execution():
    class CountingInspector:
        name = "counting-inspector"
        capabilities = frozenset({"inspect"})

        def __init__(self):
            self.calls = 0

        async def execute(self, task, context):
            self.calls += 1
            return AgentResult(agent_name=self.name, output={})

    agent = CountingInspector()
    registry = AgentRegistry()
    registry.register(agent)

    async def fail_persistence(task):
        raise RuntimeError("storage unavailable")

    service = Orchestrator(
        registry,
        DispatchPolicy(),
        EventBus(),
        persister=fail_persistence,
    )

    result = await service.submit(TaskRequest(task_type="inspect"))

    assert result.status is TaskStatus.FAILED
    assert result.error_code == "task_persistence_failed"
    assert agent.calls == 0


async def test_terminal_persistence_failure_marks_returned_task_failed():
    registry = AgentRegistry()
    registry.register(InspectorAgent())
    persistence_calls = 0

    async def fail_terminal_persistence(task):
        nonlocal persistence_calls
        persistence_calls += 1
        if persistence_calls == 2:
            raise RuntimeError("terminal write unavailable")

    service = Orchestrator(
        registry,
        DispatchPolicy(),
        EventBus(),
        persister=fail_terminal_persistence,
    )

    result = await service.submit(TaskRequest(task_type="inspect"))

    assert persistence_calls == 2
    assert result.status is TaskStatus.FAILED
    assert result.error_code == "terminal_persistence_failed"
