from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.account.infrastructure.repositories.sqlalchemy_user_repository import (
    Base,
)  # Assuming Base is defined here or imported

# Define the database URL for SQLite
DATABASE_URL = "sqlite+aiosqlite:///./sql_app.db"  # Using a file-based SQLite DB

# Create an asynchronous engine
async_engine = create_async_engine(DATABASE_URL, echo=True)

# Create an asynchronous session maker
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session() -> AsyncSession:
    """
    Database session dependency.

    Yields an asynchronous SQLAlchemy session.
    """
    async with AsyncSessionLocal() as session:
        yield session


# Note: You will need to create the database tables on application startup.
# This can be done by importing Base and running Base.metadata.create_all(async_engine)
# within an asynchronous context during your application's startup event.
