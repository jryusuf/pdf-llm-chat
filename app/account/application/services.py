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
from app.core.config import get_settings, Settings
from app.lib.security import create_access_token
from .schemas import (
    UserCreateRequest,
    UserRegisteredResponse,
    UserLoginRequest,
    TokenResponse,
)

from jose import jwt, JWTError


class AccountApplicationService:
    def __init__(self, user_repo: IUserRepository, settings: Settings):
        """Initializes the AccountApplicationService.

        Args:
            user_repo: The user repository implementation.
            settings: The application settings.
        """
        self.user_repo = user_repo
        self.settings = settings

    async def register_user(self, user_data: UserCreateRequest) -> UserRegisteredResponse:
        """Registers a new user in the system.

        Args:
            user_data: The data for the new user, including email and password.

        Returns:
            A UserRegisteredResponse containing the new user's UUID and email.

        Raises:
            UserAlreadyExistsError: If a user with the provided email already exists.
        """
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise UserAlreadyExistsError()

        new_user_domain_obj = User.create_new(email=user_data.email, plain_password=user_data.password)

        persisted_user = await self.user_repo.add(new_user_domain_obj)

        return UserRegisteredResponse(user_uuid=persisted_user.user_uuid, email=persisted_user.email)

    async def login_user(self, login_data: UserLoginRequest) -> TokenResponse:
        """Authenticates a user and generates an access token upon successful login.

        Args:
            login_data: The login credentials, including email and password.

        Returns:
            A TokenResponse containing the access token and user UUID.

        Raises:
            InvalidCredentialsError: If the email or password is incorrect, or if the user is inactive.
        """
        user_domain_obj = await self.user_repo.get_by_email(login_data.email)

        if not user_domain_obj or not user_domain_obj.verify_password(login_data.password):
            raise InvalidCredentialsError

        if not user_domain_obj.is_active:
            raise InvalidCredentialsError

        access_token_data = {"sub": str(user_domain_obj.user_uuid)}
        access_token = create_access_token(data=access_token_data, settings=self.settings)

        return TokenResponse(access_token=access_token, user_uuid=user_domain_obj.user_uuid)

    async def get_user_by_uuid_for_auth(self, user_uuid_str: str) -> Optional[User]:
        """Retrieves an active user by their UUID, primarily for authentication purposes.

        Args:
            user_uuid_str: The string representation of the user's UUID.

        Returns:
            The User domain object if found and active, otherwise None.
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
        return None
