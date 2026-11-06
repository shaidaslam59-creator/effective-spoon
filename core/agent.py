"""Agent contracts and a policy-enforcing base implementation.

Agents receive validated task data, never credentials or ambient tool access.
External I/O and tool permissions must be injected explicitly by a trusted host.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from pydantic import ValidationError

from core.models import AgentResult, TaskRecord


@dataclass(frozen=True, slots=True)
class AgentContext:
    """Immutable execution metadata; deadline_seconds is a relative budget."""

    task_id: str
    correlation_id: str | None
    deadline_seconds: float
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.task_id or self.deadline_seconds <= 0:
            raise ValueError("invalid_agent_context")


@runtime_checkable
class Agent(Protocol):
    """Structural interface accepted by the registry and orchestrator."""

    name: str
    capabilities: frozenset[str]

    async def execute(self, task: TaskRecord, context: AgentContext) -> AgentResult: ...


class BaseAgent(ABC):
    """Template-method base class enforcing capability and result contracts."""

    name: str
    capabilities: frozenset[str]

    def __init__(self) -> None:
        name = getattr(self, "name", None)
        capabilities = getattr(self, "capabilities", None)
        if not isinstance(name, str) or not name or len(name) > 80:
            raise ValueError("invalid_agent_name")
        if not isinstance(capabilities, frozenset) or not capabilities:
            raise ValueError("invalid_agent_capabilities")
        if any(not isinstance(item, str) or not item for item in capabilities):
            raise ValueError("invalid_agent_capabilities")

    async def execute(self, task: TaskRecord, context: AgentContext) -> AgentResult:
        if task.task_type not in self.capabilities:
            raise PermissionError("agent_capability_missing")
        if context.task_id != str(task.id):
            raise PermissionError("agent_task_context_mismatch")
        result = await self.run(task, context)
        if not isinstance(result, AgentResult):
            raise TypeError("agent_result_contract_violation")
        if result.agent_name != self.name:
            raise ValidationError.from_exception_data(
                "AgentResult", [{"type": "value_error", "loc": ("agent_name",),
                                 "input": result.agent_name, "ctx": {"error": ValueError(
                                     "agent_identity_mismatch")}}]
            )
        return result

    @abstractmethod
    async def run(self, task: TaskRecord, context: AgentContext) -> AgentResult:
        """Implement the agent's bounded task; do not execute untrusted instructions."""
        raise NotImplementedError
