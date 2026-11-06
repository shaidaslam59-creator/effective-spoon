"""Builder: creates an implementation plan; never executes arbitrary code."""
from core.agent import AgentContext
from core.models import AgentResult, TaskRecord

class BuilderAgent:
    name = "builder"
    capabilities = frozenset({"build_plan"})
    async def execute(self, task: TaskRecord, context: AgentContext) -> AgentResult:
        objective = str(task.payload.get("objective", "")).strip()[:500]
        return AgentResult(agent_name=self.name, output={
            "objective": objective, "status": "plan_only",
            "steps": ["acceptance criteria", "interfaces and data contracts", "small vertical slice",
                      "unit and integration tests", "static and security analysis", "release evidence"]})
