import pytest

from agents.security_guard import SecurityGuardAgent
from core.agent import AgentContext
from core.models import TaskRecord
from security.authentication import APIKeyAuthenticator


def test_api_key_verification():
    auth = APIKeyAuthenticator(["correct-key"])
    assert auth.verify("correct-key")
    assert not auth.verify("wrong-key")
    assert not auth.verify(None)


@pytest.mark.asyncio
async def test_security_guard_finds_nested_sensitive_field_names_without_returning_values():
    task = TaskRecord(task_type="security_review", payload={
        "settings": {
            "API-Key": "do-not-return",
            "oauth": {"refresh_token": "also-secret"},
        },
        "records": [
            {"Password": "hidden"},
            {"description": "ordinary"},
        ],
    })
    context = AgentContext(task_id=str(task.id), correlation_id=None, deadline_seconds=5)

    result = await SecurityGuardAgent().execute(task, context)

    assert result.output["sensitive_field_names_detected"] == [
        "records[0].Password",
        "settings.API-Key",
        "settings.oauth.refresh_token",
    ]
    serialized = str(result.model_dump())
    assert "do-not-return" not in serialized
    assert "also-secret" not in serialized
    assert "hidden" not in serialized


@pytest.mark.asyncio
async def test_security_guard_ignores_ordinary_payload_fields():
    task = TaskRecord(
        task_type="security_review",
        payload={"topic": "documentation", "count": 2},
    )
    context = AgentContext(task_id=str(task.id), correlation_id=None, deadline_seconds=5)

    result = await SecurityGuardAgent().execute(task, context)

    assert result.output["sensitive_field_names_detected"] == []
