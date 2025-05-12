from loguru import logger
from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings, Settings


class TokenPayload(BaseModel):
    sub: str
    exp: Optional[int] = None


class AuthenticatedUser(BaseModel):
    id: str


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/account/login")


def create_access_token(data: dict, settings: Settings, expires_delta: Optional[timedelta] = None) -> str:
    logger.info("Attempting to create access token.")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
        logger.debug(f"Token expires in: {expires_delta}")
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        logger.debug(f"Token expires in: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.info("Access token created successfully.")
    return encoded_jwt


async def get_current_user_payload(
    token: Annotated[str, Depends(oauth2_scheme)], app_settings: Annotated[Settings, Depends(get_settings)]
) -> TokenPayload:
    logger.info("Attempting to get current user payload.")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, app_settings.JWT_SECRET_KEY, algorithms=[app_settings.ALGORITHM])
        logger.debug(f"Token decoded successfully. Payload: {payload}")
        user_uuid: str = payload.get("sub")
        if user_uuid is None:
            logger.warning("User UUID not found in token payload.")
            raise credentials_exception

        token_data = TokenPayload(sub=user_uuid, exp=payload.get("exp"))
        logger.info(f"Successfully extracted token payload for user: {user_uuid}")
        return token_data
    except JWTError as e:
        logger.error(f"JWT Error during token decoding: {e}")
        raise credentials_exception
    except ValidationError:
        logger.error("Validation Error during token payload parsing.")
        raise credentials_exception


async def get_current_authenticated_user(
    token: Annotated[str, Depends(oauth2_scheme)], app_settings: Annotated[Settings, Depends(get_settings)]
) -> AuthenticatedUser:  # Returns an object with the user's integer ID
    logger.info("Attempting to get current authenticated user.")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, app_settings.JWT_SECRET_KEY, algorithms=[app_settings.ALGORITHM])
        logger.debug(f"Token decoded successfully for authentication. Payload: {payload}")
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            logger.warning("User ID (sub) not found in token payload for authentication.")
            raise credentials_exception

        try:
            user_id_int = user_id_str
            logger.debug(f"Successfully converted user ID string to integer: {user_id_int}")
        except ValueError:
            logger.error(f"ValueError: Could not convert user ID '{user_id_str}' to integer.")
            raise credentials_exception

        logger.info(f"Successfully authenticated user with ID: {user_id_int}")
        return AuthenticatedUser(id=user_id_int)
    except JWTError as e:
        logger.error(f"JWT Error during authentication token decoding: {e}")
        raise credentials_exception
    except ValidationError:
        logger.error("Validation Error during authenticated user payload parsing.")
        raise credentials_exception
