from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime, Integer, UUID as DB_UUID
import uuid
from datetime import datetime

from app.account.domain.models import User as UserDomainModel
from app.account.infrastructure.repositories.user_repository import IUserRepository


Base = declarative_base()


class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_uuid: Mapped[uuid.UUID] = mapped_column(
        DB_UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=datetime.utcnow, nullable=True
    )

    def to_domain(self) -> UserDomainModel:
        return UserDomainModel(
            id=self.id,
            user_uuid=self.user_uuid,
            email=self.email,
            hashed_password=self.hashed_password,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @staticmethod
    def from_domain(user_domain: UserDomainModel) -> "UserDB":
        return UserDB(
            id=user_domain.id,
            user_uuid=user_domain.user_uuid,
            email=user_domain.email,
            hashed_password=user_domain.hashed_password,
            is_active=user_domain.is_active,
            created_at=user_domain.created_at,
            updated_at=user_domain.updated_at,
        )


class SQLAlchemyUserRepository(IUserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> Optional[UserDomainModel]:
        stmt = select(UserDB).where(UserDB.email == email.lower())
        result = await self.session.execute(stmt)
        db_user = result.scalar_one_or_none()
        return db_user.to_domain() if db_user else None

    async def get_by_id(self, user_id: int) -> Optional[UserDomainModel]:
        stmt = select(UserDB).where(UserDB.id == user_id)
        result = await self.session.execute(stmt)
        db_user = result.scalar_one_or_none()
        return db_user.to_domain() if db_user else None

    async def get_by_uuid(self, user_uuid_str: str) -> Optional[UserDomainModel]:
        try:
            user_uuid_obj = uuid.UUID(user_uuid_str)
        except ValueError:
            return None
        stmt = select(UserDB).where(UserDB.user_uuid == user_uuid_obj)
        result = await self.session.execute(stmt)
        db_user = result.scalar_one_or_none()
        return db_user.to_domain() if db_user else None

    async def add(self, user_domain: UserDomainModel) -> UserDomainModel:
        db_user = UserDB.from_domain(user_domain)
        if db_user.user_uuid is None:
            db_user.user_uuid = uuid.uuid4()

        self.session.add(db_user)
        await self.session.commit()
        await self.session.refresh(db_user)
        return db_user.to_domain()
