# OmniSphere 360 — Batch 01

Policy-governed asynchronous multi-agent orchestration foundation.

Batch 01 supplies validated task contracts, capability-based agent registration, policy enforcement, bounded async execution, an in-process event bus, SQLAlchemy persistence, API-key authentication, audit storage, and a FastAPI boundary.

## Run locally

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export OMNISPHERE_API_KEYS='replace-this-development-key'
uvicorn api.application:app --host 127.0.0.1 --port 8000
```

Authenticated routes require `X-API-Key`. Health is available at `GET /health`; submit work with `POST /v1/tasks`.

Configure these exact environment variables:

- `OMNISPHERE_DATABASE_URL`: database URL; defaults to `sqlite+aiosqlite:///./omnisphere.db`.
- `OMNISPHERE_API_KEYS`: comma-separated API keys; configure at least one key to enable authenticated task submission.
- `OMNISPHERE_MAX_CONCURRENT_TASKS`: maximum concurrent tasks; defaults to `8`.
- `OMNISPHERE_TASK_TIMEOUT_SECONDS`: task execution timeout in seconds; defaults to `120`.

## Boundaries

Built-in agents are deterministic examples. They do not browse, execute arbitrary code, access external systems, or receive credentials. The event bus is process-local, not a durable broker. The API is a baseline, not a production certification.

Before production: use managed secrets, TLS, a production database, rate limiting, authorization scopes, durable queueing, observability, backup/restore, migration tooling, threat modeling, dependency scanning, and deployment-specific security review. Run tests and static checks in the target environment.
