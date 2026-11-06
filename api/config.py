"""Environment settings with safe local defaults."""
import os
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    api_keys: tuple[str, ...]
    max_concurrent_tasks: int
    task_timeout_seconds: float

    @classmethod
    def from_environment(cls) -> "Settings":
        keys = tuple(k.strip() for k in os.getenv("OMNISPHERE_API_KEYS", "").split(",") if k.strip())
        return cls(
            database_url=os.getenv("OMNISPHERE_DATABASE_URL", "sqlite+aiosqlite:///./omnisphere.db"),
            api_keys=keys,
            max_concurrent_tasks=max(1, int(os.getenv("OMNISPHERE_MAX_CONCURRENT_TASKS", "8"))),
            task_timeout_seconds=max(1.0, float(os.getenv("OMNISPHERE_TASK_TIMEOUT_SECONDS", "120"))))
