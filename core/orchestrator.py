"""Bounded, timeout-controlled, policy-enforced task execution."""
import asyncio
from datetime import UTC, datetime
from core.agent import AgentContext
from core.event_bus import EventBus
from core.models import AgentResult, TaskRecord, TaskRequest, TaskStatus
from core.policy import DispatchPolicy
from core.registry import AgentRegistry

class Orchestrator:
    def __init__(self, registry: AgentRegistry, policy: DispatchPolicy, events: EventBus,
                 max_concurrent_tasks: int = 8, timeout_seconds: float = 120.0) -> None:
        if max_concurrent_tasks < 1 or timeout_seconds <= 0:
            raise ValueError("invalid_orchestration_limits")
        self.registry, self.policy, self.events = registry, policy, events
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.timeout_seconds = timeout_seconds

    async def submit(self, request: TaskRequest) -> TaskRecord:
        task = TaskRecord(task_type=request.task_type, payload=request.payload,
                          requested_agent=request.requested_agent, correlation_id=request.correlation_id)
        try:
            agent = self.registry.select(task.task_type, task.requested_agent)
        except LookupError:
            return await self._reject(task, "agent_unavailable")
        decision = self.policy.evaluate(task, agent.capabilities)
        if not decision.allowed:
            return await self._reject(task, decision.reason)

        async with self._semaphore:
            task.status, task.started_at = TaskStatus.RUNNING, datetime.now(UTC)
            await self.events.publish("task.started", task_id=str(task.id), agent=agent.name)
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    result: AgentResult = await agent.execute(
                        task, AgentContext(str(task.id), task.correlation_id, self.timeout_seconds))
                task.result = result.model_dump(mode="json")
                task.status = TaskStatus.SUCCEEDED
                await self.events.publish("task.succeeded", task_id=str(task.id), agent=agent.name)
            except TimeoutError:
                task.status, task.error_code = TaskStatus.TIMED_OUT, "execution_timeout"
                await self.events.publish("task.failed", task_id=str(task.id), reason=task.error_code)
            except asyncio.CancelledError:
                task.status, task.error_code = TaskStatus.FAILED, "execution_cancelled"
                raise
            except Exception:
                task.status, task.error_code = TaskStatus.FAILED, "agent_execution_failed"
                await self.events.publish("task.failed", task_id=str(task.id), reason=task.error_code)
            finally:
                task.finished_at = datetime.now(UTC)
        return task

    async def _reject(self, task: TaskRecord, reason: str) -> TaskRecord:
        task.status, task.error_code = TaskStatus.REJECTED, reason
        task.finished_at = datetime.now(UTC)
        await self.events.publish("task.rejected", task_id=str(task.id), reason=reason)
        return task
