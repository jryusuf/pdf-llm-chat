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


# Reusable OAuth2 scheme - define once
# tokenUrl should point to your actual login endpoint if you use
# Swagger UI's "Authorize" button
# For just backend validation, the exact tokenUrl string doesn't
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/account/login")


def create_access_token(data: dict, settings: Settings, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user_payload(
    token: Annotated[str, Depends(oauth2_scheme)], app_settings: Annotated[Settings, Depends(get_settings)]
) -> TokenPayload:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, app_settings.JWT_SECRET_KEY, algorithms=[app_settings.ALGORITHM])
        user_uuid: str = payload.get("sub")
        if user_uuid is None:
            raise credentials_exception

        # Optional: Check token expiration if not automatically handled by jwt.decode
        # exp = payload.get("exp")
        # if exp is None or datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
        #     logger.warning("Token has expired.")
        #     raise credentials_exception # jwt.decode usually handles 'exp'

        token_data = TokenPayload(sub=user_uuid, exp=payload.get("exp"))
        return token_data
    except JWTError as e:
        raise credentials_exception
    except ValidationError:
        raise credentials_exception
