"""Async SQLAlchemy engine and schema lifecycle."""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from persistence.models import Base

def build_engine(database_url: str):
    return create_async_engine(database_url, pool_pre_ping=True)

def build_session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def initialize_schema(engine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
