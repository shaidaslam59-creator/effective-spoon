"""Security review agent: flags sensitive-looking field names only."""
from core.agent import AgentContext
from core.models import AgentResult, TaskRecord

class SecurityGuardAgent:
    name = "security_guard"
    capabilities = frozenset({"security_review"})
    async def execute(self, task: TaskRecord, context: AgentContext) -> AgentResult:
        names = {"password", "secret", "token", "api_key", "private_key", "otp"}
        flagged = sorted(str(key) for key in task.payload if str(key).lower() in names)
        return AgentResult(agent_name=self.name, output={
            "sensitive_field_names_detected": flagged,
            "recommendation": "Never place credentials or authentication secrets in task payloads.",
            "secret_scanning": "not_implemented"})
