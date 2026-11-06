"""Research planner; does not invent findings or claim external research."""
from core.agent import AgentContext
from core.models import AgentResult, TaskRecord

class ResearcherAgent:
    name = "researcher"
    capabilities = frozenset({"research"})
    async def execute(self, task: TaskRecord, context: AgentContext) -> AgentResult:
        topic = str(task.payload.get("topic", "")).strip()[:500]
        return AgentResult(agent_name=self.name, output={
            "topic": topic, "status": "plan_only_no_research_connector",
            "steps": ["define scope", "identify primary sources", "capture dated evidence and provenance",
                      "separate facts from hypotheses", "record gaps and confidence"]})
