"""Security review agent: flags sensitive-looking field names only."""
from core.agent import AgentContext
from core.models import AgentResult, TaskRecord


_SENSITIVE_FIELD_NAMES = frozenset({
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "apikey",
    "accesstoken",
    "refreshtoken",
    "bearertoken",
    "privatekey",
    "signingkey",
    "otp",
    "authorization",
    "credential",
    "credentials",
    "seedphrase",
    "recoveryphrase",
})


def _sensitive_field_paths(value: object) -> list[str]:
    """Find sensitive-looking keys recursively without reading or returning values."""
    found: list[str] = []
    pending: list[tuple[object, str]] = [(value, "")]

    while pending:
        current, parent_path = pending.pop()
        if isinstance(current, dict):
            for key, nested in current.items():
                key_text = str(key)
                path = f"{parent_path}.{key_text}" if parent_path else key_text
                normalized = "".join(char for char in key_text.casefold() if char.isalnum())
                if normalized in _SENSITIVE_FIELD_NAMES:
                    found.append(path)
                if isinstance(nested, (dict, list)):
                    pending.append((nested, path))
        elif isinstance(current, list):
            for index, nested in enumerate(current):
                if isinstance(nested, (dict, list)):
                    pending.append((nested, f"{parent_path}[{index}]"))

    return sorted(found)


class SecurityGuardAgent:
    name = "security_guard"
    capabilities = frozenset({"security_review"})

    async def execute(self, task: TaskRecord, context: AgentContext) -> AgentResult:
        flagged = _sensitive_field_paths(task.payload)
        return AgentResult(agent_name=self.name, output={
            "sensitive_field_names_detected": flagged,
            "recommendation": "Never place credentials or authentication secrets in task payloads.",
            "secret_scanning": "not_implemented",
        })
