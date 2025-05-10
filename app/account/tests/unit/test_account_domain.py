import sys
import os


import pytest
import uuid
from datetime import datetime, timezone

from app.account.domain.models import User, pwd_context


# Helper function to create a dummy user for testing
def create_dummy_user(
    id=1,
    user_uuid=None,
    email="test@example.com",
    plain_password="password123",
    is_active=True,
    created_at=None,
    updated_at=None,
):
    if user_uuid is None:
        user_uuid = uuid.uuid4()
    if created_at is None:
        created_at = datetime.now(timezone.utc)  # Use timezone-aware datetime
    hashed_password = User.hash_password(plain_password)
    return User(
        id=id,
        user_uuid=user_uuid,
        email=email,
        hashed_password=hashed_password,
        is_active=is_active,
        created_at=created_at,
        updated_at=updated_at,
    )


# Tests for User model
def test_user_init():
    user_uuid = uuid.uuid4()
    created_at = datetime.now(timezone.utc)
    user = User(
        id=1,
        user_uuid=user_uuid,
        email="Test@Example.com",
        hashed_password="hashed_password_string",
        is_active=False,
        created_at=created_at,
        updated_at=None,
    )
    assert user.id == 1
    assert user.user_uuid == user_uuid
    assert user.email == "test@example.com"
    assert user.hashed_password == "hashed_password_string"
    assert user.is_active is False
    assert user.created_at == created_at
    assert user.updated_at is None


def test_user_init_defaults():
    user_uuid = uuid.uuid4()
    user = User(
        id=None,
        user_uuid=user_uuid,
        email="default@example.com",
        hashed_password="hashed_password_string",
    )
    assert user.id is None
    assert user.user_uuid == user_uuid
    assert user.email == "default@example.com"
    assert user.hashed_password == "hashed_password_string"
    assert user.is_active is True
    assert isinstance(user.created_at, datetime)
    assert user.updated_at is None


def test_user_hash_password():
    password = "securepassword"
    hashed = User.hash_password(password)
    assert isinstance(hashed, str)
    assert pwd_context.verify(password, hashed)


def test_user_verify_password_success():
    user = create_dummy_user(plain_password="correctpassword")
    assert user.verify_password("correctpassword") is True


def test_user_verify_password_failure():
    user = create_dummy_user(plain_password="correctpassword")
    assert user.verify_password("wrongpassword") is False


def test_user_create_new():
    email = "newuser@example.com"
    password = "newpassword"
    user = User.create_new(email, password)

    assert user.id is None
    assert isinstance(user.user_uuid, uuid.UUID)
    assert user.email == email
    assert isinstance(user.hashed_password, str)
    assert pwd_context.verify(password, user.hashed_password)
    assert user.is_active is True
    assert isinstance(user.created_at, datetime)
    assert user.updated_at is None


def test_user_repr():
    user = create_dummy_user(id=5, email="reprtest@example.com")
    assert repr(user) == "<User(id=5, email='reprtest@example.com')>"
