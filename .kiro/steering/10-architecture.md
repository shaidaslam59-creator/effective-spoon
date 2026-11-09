# Architecture Constraints

- Python 3.11+; FastAPI API boundary; Pydantic task contracts.
- SQLAlchemy async persistence; PostgreSQL is the production target; SQLite is for local development and tests.
- Orchestrator dispatch is capability- and policy-governed, bounded by concurrency and timeout limits.
- Agent implementations must not receive ambient shell, filesystem, network or credential access.
- Persist task lifecycle transitions through the injected TaskPersister callback.
- EventBus is currently process-local and best-effort; do not describe it as a durable message broker.
- Built-in agents are deterministic examples, not autonomous production integrations.
- Schema changes require Alembic migrations for production.
- External integrations must be explicit adapters with least-privilege credentials, timeouts, retries, audit events and tests.
