import pytest
from datetime import timedelta, datetime, timezone
from unittest.mock import MagicMock

from fastapi import HTTPException, status
from jose import jwt, JWTError
from pydantic import ValidationError

from app.lib.security import create_access_token, get_current_user_payload, TokenPayload
from app.core.config import Settings

mock_settings = Settings(JWT_SECRET_KEY="testsecretkey", ALGORITHM="HS256", ACCESS_TOKEN_EXPIRE_MINUTES=15)


# Test cases for create_access_token
def test_create_access_token_with_expires_delta():
    data = {"sub": "testuser"}
    expires_delta = timedelta(minutes=60)
    token = create_access_token(data, mock_settings, expires_delta=expires_delta)

    # Verify token is created
    assert isinstance(token, str)
    assert len(token) > 0

    # Verify token payload
    decoded_payload = jwt.decode(token, mock_settings.JWT_SECRET_KEY, algorithms=[mock_settings.ALGORITHM])
    assert decoded_payload["sub"] == "testuser"
    assert "exp" in decoded_payload
    # Check expiration is approximately 60 minutes from now
    # Capture time before creating token for more accurate comparison
    start_time = datetime.now(timezone.utc)
    expected_expire_timestamp = (start_time + expires_delta).timestamp()
    # Check that the decoded expiration timestamp is within a small window around the expected timestamp
    decoded_expire_timestamp = decoded_payload["exp"]
    assert decoded_expire_timestamp == pytest.approx(expected_expire_timestamp, abs=2)


def test_create_access_token_without_expires_delta():
    data = {"sub": "testuser"}
    token = create_access_token(data, mock_settings)  # Use default expiry

    # Verify token is created
    assert isinstance(token, str)
    assert len(token) > 0

    # Verify token payload
    decoded_payload = jwt.decode(token, mock_settings.JWT_SECRET_KEY, algorithms=[mock_settings.ALGORITHM])
    assert decoded_payload["sub"] == "testuser"
    assert "exp" in decoded_payload
    # Check expiration is approximately default minutes from now
    # Capture time before creating token for more accurate comparison
    start_time = datetime.now(timezone.utc)
    expected_expire_timestamp = (
        start_time + timedelta(minutes=mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    ).timestamp()
    # Check that the decoded expiration timestamp is within a small window around the expected timestamp
    decoded_expire_timestamp = decoded_payload["exp"]
    assert decoded_expire_timestamp == pytest.approx(expected_expire_timestamp, abs=2)


# Test cases for get_current_user_payload
@pytest.mark.asyncio
async def test_get_current_user_payload_valid_token():
    # Create a valid token
    user_uuid = "valid-uuid"
    token_data = {"sub": user_uuid}
    valid_token = create_access_token(token_data, mock_settings)

    # Mock dependencies
    mock_oauth2_scheme = MagicMock()
    mock_oauth2_scheme.return_value = valid_token
    mock_get_settings = MagicMock()
    mock_get_settings.return_value = mock_settings

    # Call the function with mocked dependencies
    # In a real FastAPI test, Depends would handle this, but for unit test we call directly
    # Need to simulate the dependency injection by passing the values directly
    payload = await get_current_user_payload(valid_token, mock_settings)

    assert isinstance(payload, TokenPayload)
    assert payload.sub == user_uuid
    assert payload.exp is not None


@pytest.mark.asyncio
async def test_get_current_user_payload_invalid_token():
    invalid_token = "invalid.token.string"

    # Mock dependencies
    mock_oauth2_scheme = MagicMock()
    mock_oauth2_scheme.return_value = invalid_token
    mock_get_settings = MagicMock()
    mock_get_settings.return_value = mock_settings

    # Expect HTTPException for invalid token
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user_payload(invalid_token, mock_settings)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert excinfo.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_payload_expired_token():
    # Create an expired token
    user_uuid = "expired-uuid"
    token_data = {"sub": user_uuid}
    # Set expiry to the past
    expired_delta = timedelta(minutes=-1)
    expired_token = create_access_token(token_data, mock_settings, expires_delta=expired_delta)

    # Mock dependencies
    mock_oauth2_scheme = MagicMock()
    mock_oauth2_scheme.return_value = expired_token
    mock_get_settings = MagicMock()
    mock_get_settings.return_value = mock_settings

    # Expect HTTPException for expired token (jwt.decode should handle this)
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user_payload(expired_token, mock_settings)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert excinfo.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_payload_token_missing_sub():
    # Create a token missing the 'sub' claim
    token_data = {"not_sub": "some_value"}
    token_missing_sub = jwt.encode(
        token_data, mock_settings.JWT_SECRET_KEY, algorithm=mock_settings.ALGORITHM
    )

    # Mock dependencies
    mock_oauth2_scheme = MagicMock()
    mock_oauth2_scheme.return_value = token_missing_sub
    mock_get_settings = MagicMock()
    mock_get_settings.return_value = mock_settings

    # Expect HTTPException for missing 'sub'
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user_payload(token_missing_sub, mock_settings)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert excinfo.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_payload_invalid_payload_structure():
    # Create a token with a payload that doesn't match TokenPayload model
    token_data = {"sub": 123}  # sub should be string
    invalid_payload_token = jwt.encode(
        token_data, mock_settings.JWT_SECRET_KEY, algorithm=mock_settings.ALGORITHM
    )

    # Mock dependencies
    mock_oauth2_scheme = MagicMock()
    mock_oauth2_scheme.return_value = invalid_payload_token
    mock_get_settings = MagicMock()
    mock_get_settings.return_value = mock_settings

    # Expect HTTPException due to ValidationError
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user_payload(invalid_payload_token, mock_settings)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert excinfo.value.detail == "Could not validate credentials"
