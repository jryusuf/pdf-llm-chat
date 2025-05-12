from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, asc
from app.chat.domain.models import ChatMessageTurn, LLMResponseStatus
from app.chat.infrastructure.repositories.chat_repository import IChatRepository
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime, Integer, Text, Enum as DBEnum, ForeignKey
from datetime import datetime, timezone
from typing import Optional, List

from app.account.infrastructure.repositories.sqlalchemy_user_repository import Base


class ChatLogDB(Base):
    __tablename__ = "chat_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    pdf_document_id: Mapped[str] = mapped_column(Text, index=True)
    pdf_original_filename: Mapped[str] = mapped_column(String(255))
    user_message_content: Mapped[str] = mapped_column(Text)
    user_message_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    llm_response_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_response_status: Mapped[LLMResponseStatus] = mapped_column(
        DBEnum(LLMResponseStatus), default=LLMResponseStatus.PENDING
    )
    llm_response_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_attempts: Mapped[int] = mapped_column(Integer, default=0)

    def to_domain(self) -> ChatMessageTurn:
        return ChatMessageTurn(...)

    @staticmethod
    def from_domain(turn: ChatMessageTurn) -> "ChatLogDB":
        return ChatLogDB(...)


class SQLAlchemyChatRepository(IChatRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_chat_turn(self, chat_turn: ChatMessageTurn) -> ChatMessageTurn:
        db_chat_log = ChatLogDB(
            user_id=chat_turn.user_id,
            pdf_document_id=chat_turn.pdf_document_id,
            pdf_original_filename=chat_turn.pdf_original_filename,
            user_message_content=chat_turn.user_message_content,
            user_message_timestamp=chat_turn.user_message_timestamp,
            llm_response_status=LLMResponseStatus.PENDING,
        )
        self.session.add(db_chat_log)
        await self.session.commit()
        await self.session.refresh(db_chat_log)

        chat_turn.id = db_chat_log.id
        chat_turn.llm_response_status = db_chat_log.llm_response_status
        return chat_turn

    async def get_chat_turn_by_id(self, turn_id: int, user_id: int) -> Optional[ChatMessageTurn]:
        stmt = select(ChatLogDB).where(ChatLogDB.id == turn_id, ChatLogDB.user_id == user_id)
        result = await self.session.execute(stmt)
        db_log = result.scalar_one_or_none()

        if db_log:
            return ChatMessageTurn(
                id=db_log.id,
                user_id=db_log.user_id,
                pdf_document_id=db_log.pdf_document_id,
                pdf_original_filename=db_log.pdf_original_filename,
                user_message_content=db_log.user_message_content,
                user_message_timestamp=db_log.user_message_timestamp,
                llm_response_content=db_log.llm_response_content,
                llm_response_status=db_log.llm_response_status,
                llm_response_timestamp=db_log.llm_response_timestamp,
                retry_attempts=db_log.retry_attempts,
            )
        return None

    async def update_llm_response_in_turn(self, chat_turn: ChatMessageTurn) -> ChatMessageTurn:
        stmt = select(ChatLogDB).where(ChatLogDB.id == chat_turn.id, ChatLogDB.user_id == chat_turn.user_id)
        result = await self.session.execute(stmt)
        db_log = result.scalar_one_or_none()
        if not db_log:
            raise Exception(f"Chat log with ID {chat_turn.id} not found for update.")

        db_log.llm_response_content = chat_turn.llm_response_content
        db_log.llm_response_status = chat_turn.llm_response_status
        db_log.llm_response_timestamp = chat_turn.llm_response_timestamp
        db_log.retry_attempts = chat_turn.retry_attempts

        db_log.llm_response_content = chat_turn.llm_response_content
        db_log.llm_response_status = chat_turn.llm_response_status
        db_log.llm_response_timestamp = chat_turn.llm_response_timestamp
        db_log.retry_attempts = chat_turn.retry_attempts

        await self.session.commit()
        await self.session.refresh(db_log)

        return chat_turn

    async def get_chat_history_for_user(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> List[ChatMessageTurn]:
        stmt = (
            select(ChatLogDB)
            .where(ChatLogDB.user_id == user_id)
            .order_by(desc(ChatLogDB.user_message_timestamp), desc(ChatLogDB.id))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        db_logs = result.scalars().all()

        return [
            ChatMessageTurn(
                id=log.id,
                user_id=log.user_id,
                pdf_document_id=log.pdf_document_id,
                pdf_original_filename=log.pdf_original_filename,
                user_message_content=log.user_message_content,
                user_message_timestamp=log.user_message_timestamp,
                llm_response_content=log.llm_response_content,
                llm_response_status=log.llm_response_status,
                llm_response_timestamp=log.llm_response_timestamp,
                retry_attempts=log.retry_attempts,
            )
            for log in db_logs
        ]

    async def count_chat_history_for_user(self, user_id: int) -> int:
        stmt = select(func.count(ChatLogDB.id)).where(ChatLogDB.user_id == user_id)
        result = await self.session.execute(stmt)
        count = result.scalar_one()
        return count
