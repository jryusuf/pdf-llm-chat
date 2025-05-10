import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.account.domain.models import User as UserDomainModel
from app.account.infrastructure.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
    Base,
    UserDB,
)
from app.account.infrastructure.repositories.user_repository import IUserRepository

# Define an asynchronous engine for an in-memory SQLite database
DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Fixture for creating an asynchronous engine."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine):
    """Fixture for providing an asynchronous session with rollback."""
    async_session_maker = async_sessionmaker(
        async_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def user_repository(async_session: AsyncSession) -> SQLAlchemyUserRepository:
    """Fixture for providing a SQLAlchemyUserRepository instance."""
    return SQLAlchemyUserRepository(async_session)


# Helper function to create and add a user directly via the repository for test setup
async def add_user_via_repo(
    repo: SQLAlchemyUserRepository, email: str, plain_password: str
) -> UserDomainModel:
    user_domain = UserDomainModel.create_new(email=email, plain_password=plain_password)
    return await repo.add(user_domain)


# Helper function to create a dummy domain user for testing
def create_dummy_domain_user(
    email="test@example.com",
    plain_password="password123",
    is_active=True,
):
    # Use UserDomainModel.create_new to ensure password hashing is done correctly
    return UserDomainModel.create_new(email=email, plain_password=plain_password)
