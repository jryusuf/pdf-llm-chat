from typing import Protocol, Optional
from app.account.domain.models import User


class IUserRepository(Protocol):
    async def get_by_email(self, email: str) -> Optional[User]:
        """Retrieves a user by their email address."""
        ...

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Retrieves a user by their internal database ID."""
        ...

    async def get_by_uuid(self, user_uuid: str) -> Optional[User]:
        """Retrieves a user by their public UUID."""
        ...

    async def add(self, user: User) -> User:
        """Adds a new user to the repository and returns the persisted user"""
        ...
