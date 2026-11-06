"""Inspector: inventories input keys; treats payload values as untrusted data."""
from core.agent import AgentContext
from core.models import AgentResult, TaskRecord

class InspectorAgent:
    name = "inspector"
    capabilities = frozenset({"inspect"})
    async def execute(self, task: TaskRecord, context: AgentContext) -> AgentResult:
        keys = sorted(str(key) for key in task.payload)
        return AgentResult(agent_name=self.name, output={
            "task_id": context.task_id, "input_key_count": len(keys), "input_keys": keys,
            "note": "Payload values were not interpreted as instructions."})
