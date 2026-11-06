"""Agent protocol and immutable execution context."""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from core.models import AgentResult, TaskRecord

@dataclass(frozen=True, slots=True)
class AgentContext:
    task_id: str
    correlation_id: str | None
    deadline_seconds: float

@runtime_checkable
class Agent(Protocol):
    name: str
    capabilities: frozenset[str]
    async def execute(self, task: TaskRecord, context: AgentContext) -> AgentResult: ...
