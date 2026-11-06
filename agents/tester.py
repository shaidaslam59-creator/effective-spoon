"""Payload contract tester; does not execute submitted code."""
from core.agent import AgentContext
from core.models import AgentResult, TaskRecord

class TesterAgent:
    name = "tester"
    capabilities = frozenset({"test"})
    async def execute(self, task: TaskRecord, context: AgentContext) -> AgentResult:
        required = task.payload.get("required_keys", [])
        if not isinstance(required, list) or any(not isinstance(k, str) for k in required):
            return AgentResult(agent_name=self.name, output={"valid": False, "reason": "invalid_required_keys"})
        missing = sorted(set(required) - set(task.payload))
        return AgentResult(agent_name=self.name, output={
            "valid": not missing, "missing_keys": missing, "scope": "payload_contract_only"})
