from typing import Optional
import uuid
from datetime import timedelta, datetime, timezone

from app.account.domain.models import User
from app.account.infrastructure.repositories.user_repository import IUserRepository
from app.account.domain.exceptions import (
    UserAlreadyExistsError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from .schemas import (
    UserCreateRequest,
    UserRegisteredResponse,
    UserLoginRequest,
    TokenResponse,
)

from jose import jwt, JWTError

JWT_SECRET_KEY = "your-super-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


class AccountApplicationService:
    def __init__(self, user_repo: IUserRepository):
        self.user_repo = user_repo

    async def register_user(
        self, user_data: UserCreateRequest
    ) -> UserRegisteredResponse:
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise UserAlreadyExistsError()

        new_user_domain_obj = User.create_new(
            email=user_data.email, plain_password=user_data.password
        )

        persisted_user = await self.user_repo.add(new_user_domain_obj)

        return UserRegisteredResponse(
            user_uuid=persisted_user.user_uuid, email=persisted_user.email
        )

    async def login_user(self, login_data: UserLoginRequest) -> TokenResponse:
        user_domain_obj = await self.user_repo.get_by_email(login_data.email)

        if not user_domain_obj or not user_domain_obj.verify_password(
            login_data.password
        ):
            raise InvalidCredentialsError

        if not user_domain_obj.is_active:
            raise InvalidCredentialsError

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token_data = {"sub": str(user_domain_obj.user_uuid)}
        access_token = create_access_token(
            data=access_token_data, expires_delta=access_token_expires
        )

        return TokenResponse(
            access_token=access_token, user_uuid=user_domain_obj.user_uuid
        )

    async def get_user_by_uuid_for_auth(self, user_uuid_str: str) -> Optional[User]:
        """
        Service method specifically for the auth dependency to get a user.
        Returns the domain User object.
        """
        try:
            user_uuid = uuid.UUID(user_uuid_str)
        except ValueError:
            return None

        user = await self.user_repo.get_by_uuid(str(user_uuid))
        if user and user.is_active:
            return user
        if user and not user.is_active:
            return None
