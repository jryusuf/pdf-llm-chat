import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone, timedelta
from typing import Optional, List, AsyncIterator

from app.chat.infrastructure.repositories.sqlalchmey_chat_repository import (
    Base,
    ChatLogDB,
    SQLAlchemyChatRepository,
)
from app.chat.domain.models import ChatMessageTurn, LLMResponseStatus


DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncIterator[AsyncSession]:
    """Fixture that provides a new async session with tables created and dropped."""
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create a new session for the test
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    # Drop tables after the test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def chat_repository(db_session: AsyncSession) -> SQLAlchemyChatRepository:
    """Fixture that provides a SQLAlchemyChatRepository instance."""
    return SQLAlchemyChatRepository(db_session)


@pytest.fixture
def sample_chat_turn() -> ChatMessageTurn:
    """Provides a sample ChatMessageTurn domain object."""
    return ChatMessageTurn(
        user_id=1,
        pdf_document_id="mongo_pdf_id_123",
        pdf_original_filename="test_document.pdf",
        user_message_content="What is the main topic of the document?",
        user_message_timestamp=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_create_chat_turn(
    chat_repository: SQLAlchemyChatRepository, sample_chat_turn: ChatMessageTurn
):
    """Test creating a chat turn in the repository."""
    created_turn = await chat_repository.create_chat_turn(sample_chat_turn)

    assert created_turn is not None
    assert created_turn.id is not None  # ID should be assigned by the database
    assert created_turn.user_id == sample_chat_turn.user_id
    assert created_turn.pdf_document_id == sample_chat_turn.pdf_document_id
    assert created_turn.pdf_original_filename == sample_chat_turn.pdf_original_filename
    assert created_turn.user_message_content == sample_chat_turn.user_message_content
    # Compare timestamps carefully, potentially truncate microseconds or compare within a delta
    # For simplicity, checking core fields.
    assert (
        created_turn.user_message_timestamp == sample_chat_turn.user_message_timestamp
    )  # May fail due to precision

    # Verify it exists in the database
    retrieved_turn = await chat_repository.get_chat_turn_by_id(created_turn.id, created_turn.user_id)
    assert retrieved_turn is not None
    assert retrieved_turn.id == created_turn.id
    assert retrieved_turn.user_id == str(created_turn.user_id)
    assert retrieved_turn.pdf_document_id == retrieved_turn.pdf_document_id
    assert retrieved_turn.pdf_original_filename == retrieved_turn.pdf_original_filename
    assert retrieved_turn.user_message_content == retrieved_turn.user_message_content


@pytest.mark.asyncio
async def test_get_chat_turn_by_id(
    chat_repository: SQLAlchemyChatRepository, sample_chat_turn: ChatMessageTurn
):
    """Test retrieving a chat turn by ID."""
    created_turn = await chat_repository.create_chat_turn(sample_chat_turn)
    retrieved_turn = await chat_repository.get_chat_turn_by_id(created_turn.id, created_turn.user_id)

    assert retrieved_turn is not None
    assert retrieved_turn.id == created_turn.id
    assert retrieved_turn.user_id == str(created_turn.user_id)
    assert retrieved_turn.pdf_document_id == created_turn.pdf_document_id
    assert retrieved_turn.pdf_original_filename == created_turn.pdf_original_filename
    assert retrieved_turn.user_message_content == created_turn.user_message_content
    # Note: Timestamps and other fields might need careful comparison
    # depending on precision/timezone handling
    # For simplicity, checking core fields.

    # Test getting a non-existent turn
    non_existent_turn = await chat_repository.get_chat_turn_by_id(999, sample_chat_turn.user_id)
    assert non_existent_turn is None

    # Test getting a turn with incorrect user_id
    incorrect_user_turn = await chat_repository.get_chat_turn_by_id(created_turn.id, 999)
    assert incorrect_user_turn is None


@pytest.mark.asyncio
async def test_update_llm_response_in_turn(
    chat_repository: SQLAlchemyChatRepository, sample_chat_turn: ChatMessageTurn
):
    """Test updating the LLM response in a chat turn."""
    created_turn = await chat_repository.create_chat_turn(sample_chat_turn)

    # Simulate updating the domain object
    created_turn.mark_llm_processing()
    updated_content = "This is the LLM's response."
    created_turn.set_llm_response_success(updated_content)
    created_turn.increment_retry()

    updated_turn = await chat_repository.update_llm_response_in_turn(created_turn)

    assert updated_turn is not None
    assert updated_turn.id == created_turn.id
    assert updated_turn.llm_response_content == updated_content
    assert updated_turn.llm_response_status == LLMResponseStatus.COMPLETED_SUCCESS
    assert isinstance(updated_turn.llm_response_timestamp, datetime)
    assert updated_turn.llm_response_timestamp.tzinfo is not None
    assert updated_turn.llm_response_timestamp.tzinfo == timezone.utc
    assert updated_turn.retry_attempts == 1

    # Verify changes in the database
    retrieved_turn = await chat_repository.get_chat_turn_by_id(updated_turn.id, updated_turn.user_id)
    assert retrieved_turn is not None
    assert retrieved_turn.llm_response_content == updated_content
    assert retrieved_turn.llm_response_status == LLMResponseStatus.COMPLETED_SUCCESS
    assert isinstance(retrieved_turn.llm_response_timestamp, datetime)
    # More robust timezone check for retrieved timestamp - compare naive UTC times within a delta
    assert retrieved_turn.llm_response_timestamp is not None
    # Compare naive UTC times within a small delta (e.g., 5 seconds)
    time_delta = abs(
        retrieved_turn.llm_response_timestamp.replace(tzinfo=None)
        - updated_turn.llm_response_timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    )
    assert time_delta.total_seconds() < 5  # Allow a small difference
    assert retrieved_turn.retry_attempts == 1


@pytest.mark.asyncio
async def test_get_chat_history_for_user(chat_repository: SQLAlchemyChatRepository):
    """Test retrieving chat history for a user."""
    user_id_1 = 1
    user_id_2 = 2

    # Create some chat turns for user 1
    turn1_user1 = ChatMessageTurn(
        user_id=user_id_1,
        pdf_document_id="pdfA",
        pdf_original_filename="docA.pdf",
        user_message_content="Msg 1 A",
        user_message_timestamp=datetime.now(timezone.utc).replace(microsecond=0),
    )
    turn2_user1 = ChatMessageTurn(
        user_id=user_id_1,
        pdf_document_id="pdfB",
        pdf_original_filename="docB.pdf",
        user_message_content="Msg 2 B",
        user_message_timestamp=datetime.now(timezone.utc).replace(microsecond=0),
    )
    turn3_user1 = ChatMessageTurn(
        user_id=user_id_1,
        pdf_document_id="pdfA",
        pdf_original_filename="docA.pdf",
        user_message_content="Msg 3 A",
        user_message_timestamp=datetime.now(timezone.utc).replace(microsecond=0),
    )

    # Create a chat turn for user 2
    turn1_user2 = ChatMessageTurn(
        user_id=user_id_2,
        pdf_document_id="pdfC",
        pdf_original_filename="docC.pdf",
        user_message_content="Msg 1 C",
        user_message_timestamp=datetime.now(timezone.utc).replace(microsecond=0),
    )

    # Introduce small delays to ensure distinct timestamps for ordering tests
    import asyncio

    await chat_repository.create_chat_turn(turn1_user1)
    await asyncio.sleep(0.01)
    await chat_repository.create_chat_turn(turn2_user1)
    await asyncio.sleep(0.01)
    await chat_repository.create_chat_turn(turn3_user1)
    await asyncio.sleep(0.01)
    await chat_repository.create_chat_turn(turn1_user2)

    # Get history for user 1 (should be ordered by timestamp/id descending)
    history_user1 = await chat_repository.get_chat_history_for_user(user_id_1)
    assert len(history_user1) == 3
    # Check order (most recent first - turn3, then turn2, then turn1
    # based on creation order/implicit timestamp)
    assert history_user1[0].user_message_content == "Msg 3 A"
    assert history_user1[1].user_message_content == "Msg 2 B"
    assert history_user1[2].user_message_content == "Msg 1 A"

    # Get history for user 2
    history_user2 = await chat_repository.get_chat_history_for_user(user_id_2)
    assert len(history_user2) == 1
    assert history_user2[0].user_message_content == "Msg 1 C"

    # Test pagination (skip=1, limit=1 for user 1)
    paginated_history_user1 = await chat_repository.get_chat_history_for_user(user_id_1, skip=1, limit=1)
    assert len(paginated_history_user1) == 1
    assert paginated_history_user1[0].user_message_content == "Msg 2 B"  # Should get the second most recent

    # Test empty history
    history_user_none = await chat_repository.get_chat_history_for_user(999)
    assert len(history_user_none) == 0


@pytest.mark.asyncio
async def test_count_chat_history_for_user(chat_repository: SQLAlchemyChatRepository):
    """Test counting chat history for a user."""
    user_id_1 = 1
    user_id_2 = 2

    # Create some chat turns for user 1
    turn1_user1 = ChatMessageTurn(
        user_id=user_id_1,
        pdf_document_id="pdfA",
        pdf_original_filename="docA.pdf",
        user_message_content="Msg 1 A",
    )
    turn2_user1 = ChatMessageTurn(
        user_id=user_id_1,
        pdf_document_id="pdfB",
        pdf_original_filename="docB.pdf",
        user_message_content="Msg 2 B",
    )

    # Create a chat turn for user 2
    turn1_user2 = ChatMessageTurn(
        user_id=user_id_2,
        pdf_document_id="pdfC",
        pdf_original_filename="docC.pdf",
        user_message_content="Msg 1 C",
    )

    await chat_repository.create_chat_turn(turn1_user1)
    await chat_repository.create_chat_turn(turn2_user1)
    await chat_repository.create_chat_turn(turn1_user2)

    # Count history for user 1
    count_user1 = await chat_repository.count_chat_history_for_user(user_id_1)
    assert count_user1 == 2

    # Count history for user 2
    count_user2 = await chat_repository.count_chat_history_for_user(user_id_2)
    assert count_user2 == 1

    # Count history for non-existent user
    count_user_none = await chat_repository.count_chat_history_for_user(999)
    assert count_user_none == 0
