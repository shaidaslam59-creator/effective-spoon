"""Regression tests for the documented OmniSphere environment settings."""

from api.config import Settings


def test_settings_read_exact_prefixed_environment_variables(monkeypatch):
    monkeypatch.setenv(
        "OMNISPHERE_DATABASE_URL",
        "postgresql+asyncpg://user:pass@localhost/omnisphere",
    )
    monkeypatch.setenv("OMNISPHERE_API_KEYS", "alpha, beta,,")
    monkeypatch.setenv("OMNISPHERE_MAX_CONCURRENT_TASKS", "4")
    monkeypatch.setenv("OMNISPHERE_TASK_TIMEOUT_SECONDS", "45.5")

    # Unprefixed names are not part of the application's configuration contract.
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./wrong.db")
    monkeypatch.setenv("API_KEYS", "wrong-key")
    monkeypatch.setenv("MAX_CONCURRENT_TASKS", "99")
    monkeypatch.setenv("TASK_TIMEOUT_SECONDS", "999")

    settings = Settings.from_environment()

    assert settings.database_url == "postgresql+asyncpg://user:pass@localhost/omnisphere"
    assert settings.api_keys == ("alpha", "beta")
    assert settings.max_concurrent_tasks == 4
    assert settings.task_timeout_seconds == 45.5


def test_settings_use_safe_defaults_when_prefixed_variables_are_absent(monkeypatch):
    for name in (
        "OMNISPHERE_DATABASE_URL",
        "OMNISPHERE_API_KEYS",
        "OMNISPHERE_MAX_CONCURRENT_TASKS",
        "OMNISPHERE_TASK_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://wrong")
    monkeypatch.setenv("API_KEYS", "wrong-key")
    monkeypatch.setenv("MAX_CONCURRENT_TASKS", "99")
    monkeypatch.setenv("TASK_TIMEOUT_SECONDS", "999")

    settings = Settings.from_environment()

    assert settings.database_url == "sqlite+aiosqlite:///./omnisphere.db"
    assert settings.api_keys == ()
    assert settings.max_concurrent_tasks == 8
    assert settings.task_timeout_seconds == 120.0
