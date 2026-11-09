"""FastAPI app factory and task submission endpoint."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status

from agents.builder import BuilderAgent
from agents.inspector import InspectorAgent
from agents.researcher import ResearcherAgent
from agents.security_guard import SecurityGuardAgent
from agents.tester import TesterAgent
from api.config import Settings
from core.event_bus import EventBus
from core.models import TaskRecord, TaskRequest
from core.orchestrator import Orchestrator, TaskPersister
from core.policy import DispatchPolicy
from core.registry import AgentRegistry
from persistence.database import build_engine, build_session_factory, initialize_schema
from persistence.repository import TaskRepository
from security.authentication import APIKeyAuthenticator


def build_orchestrator(
    settings: Settings,
    persister: TaskPersister | None = None,
) -> Orchestrator:
    registry = AgentRegistry()
    for agent in (
        InspectorAgent(),
        ResearcherAgent(),
        BuilderAgent(),
        TesterAgent(),
        SecurityGuardAgent(),
    ):
        registry.register(agent)
    return Orchestrator(
        registry,
        DispatchPolicy(),
        EventBus(),
        settings.max_concurrent_tasks,
        settings.task_timeout_seconds,
        persister=persister,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings.from_environment()
    engine = build_engine(config.database_url)
    sessions = build_session_factory(engine)
    auth = APIKeyAuthenticator(list(config.api_keys))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await initialize_schema(engine)
        yield
        await engine.dispose()

    app = FastAPI(title="OmniSphere 360 API", version="0.1.0", lifespan=lifespan)
    app.state.sessions = sessions

    async def persist_task(task: TaskRecord) -> None:
        async with sessions() as session:
            await TaskRepository(session).save(task)

    app.state.orchestrator = build_orchestrator(config, persist_task)

    async def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
        if not auth.verify(x_api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="unauthorized",
            )
        return "api_key"

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "omnisphere-360"}

    @app.post("/v1/tasks", response_model=TaskRecord, status_code=status.HTTP_202_ACCEPTED)
    async def submit_task(
        payload: TaskRequest,
        request: Request,
        actor: str = Depends(require_api_key),
    ) -> TaskRecord:
        return await request.app.state.orchestrator.submit(payload)

    return app


app = create_app()
