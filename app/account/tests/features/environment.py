import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.account.infrastructure.repositories.sqlalchemy_user_repository import Base
from app.core.dependencies import get_db_session

# Removed account_router import as it's included in app.main
from app.account.domain.models import User as UserDomainModel
from app.account.infrastructure.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
    UserDB,
)


# Define an asynchronous engine for an in-memory SQLite database
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Use a global event loop for the test environment
# Moved to before_all hook


async def start_db():
    """Creates the database engine and tables."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


async def stop_db(engine):
    """Drops the database tables and disposes the engine."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def before_all(context):
    """Set up the test environment before all scenarios."""
    context.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(context.loop)
    context.engine = context.loop.run_until_complete(start_db())
    # TestClient will be created in before_scenario
    # context.client = TestClient(app)


def after_all(context):
    """Clean up the test environment after all scenarios."""
    # TestClient does not have a shutdown method
    context.loop.run_until_complete(stop_db(context.engine))
    context.loop.close()
    asyncio.set_event_loop(None)  # Unset the event loop


async def create_test_session_async(engine):
    """Creates and returns an asynchronous session."""
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session_maker() as session:
        # We yield the session here, but in the sync hook we'll just get the session object
        yield session


def before_scenario(context, scenario):
    """Set up before each scenario."""
    # Create a new session for each scenario using the async helper
    session_generator = create_test_session_async(context.engine)
    context.session = context.loop.run_until_complete(session_generator.__anext__())

    # Override the dependency for the TestClient for this scenario on the main app
    app.dependency_overrides[get_db_session] = lambda: context.session

    # Create TestClient here for each scenario with the main app
    context.client = TestClient(app)


def after_scenario(context, scenario):
    """Clean up after each scenario."""
    # Rollback and close the session after each scenario
    context.loop.run_until_complete(context.session.rollback())
    # Manually close the session obtained via __anext__
    context.loop.run_until_complete(context.session.close())
    # Clear the dependency override on the main app
    app.dependency_overrides = {}


# Helper function to add a user directly via the repository for test setup
async def add_user_via_repo(session: AsyncSession, email: str, plain_password: str) -> UserDomainModel:
    user_domain = UserDomainModel.create_new(email=email, plain_password=plain_password)
    # Create a UserDB instance from the domain model
    user_db = UserDB(
        user_uuid=user_domain.user_uuid,
        email=user_domain.email,
        hashed_password=user_domain.hashed_password,
        is_active=user_domain.is_active,
        created_at=user_domain.created_at,
        updated_at=user_domain.updated_at,
    )
    repo = SQLAlchemyUserRepository(session)
    # Add the mapped UserDB instance to the session (remove await)
    repo.session.add(user_db)
    await repo.session.flush()  # Flush to assign primary key if needed, but don't commit
    # Return the domain model instance for consistency with the original function signature
    return user_domain


# Make helper available in context - need to run this in before_all or similar if it depends on context
# context.add_user_via_repo = add_user_via_repo
# Instead, we'll make the async helper available and run it with context.loop.run_until_complete
def before_feature(context, feature):
    context.add_user_via_repo = add_user_via_repo  # Make helper available per feature or scenario
