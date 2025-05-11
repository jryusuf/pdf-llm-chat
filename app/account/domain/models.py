import uuid
from passlib.context import CryptContext
from typing import Optional
from datetime import datetime, UTC

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User:
    id: int
    user_uuid: uuid.UUID
    email: str
    hashed_password: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    def __init__(
        self,
        id: Optional[int],
        user_uuid: uuid.UUID,
        email: str,
        hashed_password: str,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.user_uuid = user_uuid
        self.email = email.lower()
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.created_at = created_at if created_at else datetime.now(UTC)
        self.updated_at = updated_at

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str) -> bool:
        """Verifies a plain password against the stored hashed password."""
        return pwd_context.verify(plain_password, self.hashed_password)

    @classmethod
    def create_new(cls, email: str, plain_password: str) -> "User":
        hashed_password = cls.hash_password(plain_password)
        return cls(
            id=None,
            user_uuid=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password,
            is_active=True,
        )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
