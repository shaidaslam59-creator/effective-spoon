"""Validated task and result contracts."""
from __future__ import annotations
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field

class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"

class TaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    task_type: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    payload: dict[str, object] = Field(default_factory=dict)
    requested_agent: str | None = Field(default=None, min_length=1, max_length=80)
    correlation_id: str | None = Field(default=None, max_length=128)

class TaskRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID = Field(default_factory=uuid4)
    task_type: str
    payload: dict[str, object]
    requested_agent: str | None = None
    correlation_id: str | None = None
    status: TaskStatus = TaskStatus.QUEUED
    result: dict[str, object] | None = None
    error_code: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None

class AgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_name: str
    output: dict[str, object]
    metadata: dict[str, str] = Field(default_factory=dict)
