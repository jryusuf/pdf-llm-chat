import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.account.domain.models import User as UserDomainModel
from app.account.infrastructure.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.account.infrastructure.repositories.user_repository import IUserRepository

from app.account.tests.integration.conftest import (
    user_repository,
    create_dummy_domain_user,
    add_user_via_repo,
)


# Integration tests for SQLAlchemyUserRepository
@pytest.mark.asyncio
async def test_add_user(user_repository: SQLAlchemyUserRepository):
    """Test adding a user to the repository."""
    user_domain = create_dummy_domain_user(email="addtest@example.com")
    added_user = await user_repository.add(user_domain)

    assert added_user is not None
    assert added_user.id is not None
    assert isinstance(added_user.user_uuid, uuid.UUID)
    assert added_user.email == "addtest@example.com"
    assert added_user.hashed_password == user_domain.hashed_password
    assert added_user.is_active is True
    assert isinstance(added_user.created_at, datetime)
    assert added_user.updated_at is None

    # Verify the user exists in the database by fetching it
    fetched_user = await user_repository.get_by_id(added_user.id)
    assert fetched_user is not None
    assert fetched_user.email == "addtest@example.com"


@pytest.mark.asyncio
async def test_get_by_email(user_repository: SQLAlchemyUserRepository):
    """Test retrieving a user by email."""
    user_domain = create_dummy_domain_user(email="emailtest@example.com")
    await user_repository.add(user_domain)

    fetched_user = await user_repository.get_by_email("emailtest@example.com")
    assert fetched_user is not None
    assert fetched_user.email == "emailtest@example.com"
    assert fetched_user.hashed_password == user_domain.hashed_password


@pytest.mark.asyncio
async def test_get_by_email_not_found(user_repository: SQLAlchemyUserRepository):
    """Test retrieving a non-existent user by email."""
    fetched_user = await user_repository.get_by_email("nonexistent@example.com")
    assert fetched_user is None


@pytest.mark.asyncio
async def test_get_by_id(user_repository: SQLAlchemyUserRepository):
    """Test retrieving a user by ID."""
    user_domain = create_dummy_domain_user(email="idtest@example.com")
    added_user = await user_repository.add(user_domain)

    fetched_user = await user_repository.get_by_id(added_user.id)
    assert fetched_user is not None
    assert fetched_user.id == added_user.id
    assert fetched_user.email == "idtest@example.com"


@pytest.mark.asyncio
async def test_get_by_id_not_found(user_repository: SQLAlchemyUserRepository):
    """Test retrieving a non-existent user by ID."""
    fetched_user = await user_repository.get_by_id(
        999
    )  # Assuming ID 999 does not exist
    assert fetched_user is None


@pytest.mark.asyncio
async def test_get_by_uuid(user_repository: SQLAlchemyUserRepository):
    """Test retrieving a user by UUID."""
    user_domain = create_dummy_domain_user(email="uuidtest@example.com")
    await user_repository.add(user_domain)  # UUID is generated on add if not provided

    # Need to fetch the user first to get the generated UUID
    added_user = await user_repository.get_by_email("uuidtest@example.com")
    assert added_user is not None
    assert added_user.user_uuid is not None

    fetched_user = await user_repository.get_by_uuid(str(added_user.user_uuid))
    assert fetched_user is not None
    assert fetched_user.user_uuid == added_user.user_uuid
    assert fetched_user.email == "uuidtest@example.com"


@pytest.mark.asyncio
async def test_get_by_uuid_invalid_format(user_repository: SQLAlchemyUserRepository):
    """Test retrieving a user with an invalid UUID format."""
    fetched_user = await user_repository.get_by_uuid("invalid-uuid-format")
    assert fetched_user is None
