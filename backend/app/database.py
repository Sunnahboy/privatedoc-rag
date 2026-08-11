from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """
    Base class for all sqlalchemy ORM models.

    why:
        -Every database table model inherits from this.
        -Base.metadata is used to create tables during development.
    """


engine = create_async_engine(settings.database_url, echo=settings.database_echo)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
     FastAPI dependency that provides one database session per request.
    Why:
    - Each request gets its own session.
    - Sessions should not be shared across concurrent requests.
    - This keeps database access clean and testable.
    """
    async with AsyncSessionLocal() as session:
        yield session



