from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.account.infrastructure.repositories.sqlalchemy_user_repository import (
    Base,
)
from app.core.config import get_settings

settings = get_settings()

async_engine = create_async_engine(settings.DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session() -> AsyncSession:
    """
    Database session dependency.

    Yields an asynchronous SQLAlchemy session.
    """
    async with AsyncSessionLocal() as session:
        yield session
