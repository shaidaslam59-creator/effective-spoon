"""Bounded asynchronous orchestration with deny-by-default policy enforcement.

The orchestrator does not execute arbitrary code and does not grant agents ambient
network, filesystem, credential, or shell access. Durable task storage is injected
through a trusted async callback; the default is intentionally in-memory only.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from core.agent import Agent, AgentContext
from core.event_bus import EventBus
from core.models import AgentResult, TaskRecord, TaskRequest, TaskStatus
from core.policy import DispatchPolicy
from core.registry import AgentRegistry

logger = logging.getLogger(__name__)
TaskPersister = Callable[[TaskRecord], Awaitable[None]]

_DEFAULT_MAX_PAYLOAD_BYTES = 256 * 1024
_DEFAULT_MAX_PAYLOAD_DEPTH = 16
_RESERVED_KEYS = frozenset({"__proto__", "prototype", "constructor"})


class PayloadValidationError(ValueError):
    """Raised when task input is not bounded, plain JSON data."""


def _validate_json_value(value: Any, *, depth: int = 0) -> None:
    if depth > _DEFAULT_MAX_PAYLOAD_DEPTH:
        raise PayloadValidationError("payload_nesting_limit_exceeded")
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            raise PayloadValidationError("non_finite_number_not_allowed")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise PayloadValidationError("payload_object_keys_must_be_strings")
            if key.lower() in _RESERVED_KEYS:
                raise PayloadValidationError("reserved_payload_key")
            _validate_json_value(item, depth=depth + 1)
        return
    raise PayloadValidationError("payload_must_contain_only_json_values")


def validate_task_payload(payload: dict[str, object], max_bytes: int = _DEFAULT_MAX_PAYLOAD_BYTES) -> None:
    """Validate structure, depth and serialized size before dispatch."""
    _validate_json_value(payload)
    try:
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise PayloadValidationError("payload_is_not_valid_json") from exc
    if len(encoded.encode("utf-8")) > max_bytes:
        raise PayloadValidationError("payload_size_limit_exceeded")


class Orchestrator:
    """Coordinates registered agents under concurrency, timeout and policy limits."""

    def __init__(
        self,
        registry: AgentRegistry,
        policy: DispatchPolicy,
        events: EventBus,
        max_concurrent_tasks: int = 8,
        timeout_seconds: float = 120.0,
        *,
        max_payload_bytes: int = _DEFAULT_MAX_PAYLOAD_BYTES,
        persister: TaskPersister | None = None,
    ) -> None:
        if max_concurrent_tasks < 1 or timeout_seconds <= 0 or max_payload_bytes < 1:
            raise ValueError("invalid_orchestration_limits")
        self.registry = registry
        self.policy = policy
        self.events = events
        self.timeout_seconds = float(timeout_seconds)
        self.max_payload_bytes = max_payload_bytes
        self.persister = persister
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._closed = False

    async def submit(self, request: TaskRequest) -> TaskRecord:
        """Validate, authorize and execute one task; never expose raw exception text."""
        if self._closed:
            raise RuntimeError("orchestrator_closed")

        task = TaskRecord(
            task_type=request.task_type,
            payload=request.payload,
            requested_agent=request.requested_agent,
            correlation_id=request.correlation_id,
        )

        try:
            validate_task_payload(task.payload, self.max_payload_bytes)
            agent = self.registry.select(task.task_type, task.requested_agent)
        except PayloadValidationError:
            return await self._reject(task, "invalid_task_payload")
        except LookupError:
            return await self._reject(task, "agent_unavailable")

        decision = self.policy.evaluate(task, agent.capabilities)
        if not decision.allowed:
            return await self._reject(task, decision.reason)

        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(UTC)
            try:
                await self._persist(task)
            except Exception:
                logger.exception("task_persistence_failed", extra={"task_id": str(task.id)})
                task.status = TaskStatus.FAILED
                task.error_code = "task_persistence_failed"
                task.finished_at = datetime.now(UTC)
                return task

            await self._publish("task.started", task_id=str(task.id), agent=agent.name)
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    result: AgentResult = await agent.execute(
                        task,
                        AgentContext(
                            task_id=str(task.id),
                            correlation_id=task.correlation_id,
                            deadline_seconds=self.timeout_seconds,
                        ),
                    )
                if result.agent_name != agent.name:
                    raise ValueError("agent_identity_mismatch")
                task.result = result.model_dump(mode="json")
                task.status = TaskStatus.SUCCEEDED
                await self._publish("task.succeeded", task_id=str(task.id), agent=agent.name)
            except TimeoutError:
                task.status = TaskStatus.TIMED_OUT
                task.error_code = "execution_timeout"
                await self._publish("task.failed", task_id=str(task.id), reason=task.error_code)
            except asyncio.CancelledError:
                task.status = TaskStatus.FAILED
                task.error_code = "execution_cancelled"
                task.finished_at = datetime.now(UTC)
                try:
                    await asyncio.shield(self._persist(task))
                except Exception:
                    logger.exception("cancelled_task_persistence_failed",
                                     extra={"task_id": str(task.id)})
                raise
            except Exception:
                logger.exception("agent_execution_failed",
                                 extra={"task_id": str(task.id), "agent": agent.name})
                task.status = TaskStatus.FAILED
                task.error_code = "agent_execution_failed"
                await self._publish("task.failed", task_id=str(task.id), reason=task.error_code)
            finally:
                task.finished_at = task.finished_at or datetime.now(UTC)
                try:
                    await self._persist(task)
                except Exception:
                    logger.exception("terminal_task_persistence_failed",
                                     extra={"task_id": str(task.id)})
                    if task.status is TaskStatus.SUCCEEDED:
                        task.status = TaskStatus.FAILED
                        task.error_code = "terminal_persistence_failed"
        return task

    async def _reject(self, task: TaskRecord, reason: str) -> TaskRecord:
        task.status = TaskStatus.REJECTED
        task.error_code = reason
        task.finished_at = datetime.now(UTC)
        await self._publish("task.rejected", task_id=str(task.id), reason=reason)
        try:
            await self._persist(task)
        except Exception:
            logger.exception("rejected_task_persistence_failed",
                             extra={"task_id": str(task.id)})
        return task

    async def _persist(self, task: TaskRecord) -> None:
        if self.persister is not None:
            await self.persister(task)

    async def _publish(self, event_name: str, **attributes: Any) -> None:
        try:
            await self.events.publish(event_name, **attributes)
        except Exception:
            # Event delivery is best-effort; task execution state remains authoritative.
            logger.exception("domain_event_delivery_failed",
                             extra={"event_name": event_name})

    async def close(self) -> None:
        """Reject new submissions. The host owns cancellation/draining of active work."""
        self._closed = True
