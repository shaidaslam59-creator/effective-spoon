"""Deny-by-default dispatch policy."""
from dataclasses import dataclass
from core.models import TaskRecord

@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    reason: str

class DispatchPolicy:
    def __init__(self, allowed_task_types: frozenset[str] | None = None) -> None:
        self._allowed = allowed_task_types or frozenset({"inspect", "research", "build_plan", "test", "security_review"})

    def evaluate(self, task: TaskRecord, capabilities: frozenset[str]) -> PolicyDecision:
        if task.task_type not in self._allowed:
            return PolicyDecision(False, "task_type_not_allowlisted")
        if task.task_type not in capabilities:
            return PolicyDecision(False, "agent_capability_missing")
        return PolicyDecision(True, "allowed")
