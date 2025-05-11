import pytest
from datetime import datetime, timezone
from app.chat.domain.models import ChatMessageTurn, LLMResponseStatus


def test_chat_message_turn_initialization():
    """Test initialization of ChatMessageTurn with required parameters."""
    user_id = 1
    pdf_document_id = "pdf123"
    pdf_original_filename = "document.pdf"
    user_message_content = "Hello, PDF!"

    chat_turn = ChatMessageTurn(
        user_id=user_id,
        pdf_document_id=pdf_document_id,
        pdf_original_filename=pdf_original_filename,
        user_message_content=user_message_content,
    )

    assert chat_turn.id is None
    assert chat_turn.user_id == user_id
    assert chat_turn.pdf_document_id == pdf_document_id
    assert chat_turn.pdf_original_filename == pdf_original_filename
    assert chat_turn.user_message_content == user_message_content
    assert isinstance(chat_turn.user_message_timestamp, datetime)
    assert chat_turn.user_message_timestamp.tzinfo == timezone.utc
    assert chat_turn.llm_response_content is None
    assert chat_turn.llm_response_status == LLMResponseStatus.PENDING
    assert chat_turn.llm_response_timestamp is None
    assert chat_turn.retry_attempts == 0


def test_chat_message_turn_initialization_with_optional_params():
    """Test initialization with all optional parameters."""
    user_id = 2
    pdf_document_id = "pdf456"
    pdf_original_filename = "another_doc.pdf"
    user_message_content = "Another message."
    turn_id = 10
    user_timestamp = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    llm_content = "LLM response."
    llm_status = LLMResponseStatus.COMPLETED_SUCCESS
    llm_timestamp = datetime(2023, 1, 1, 10, 5, 0, tzinfo=timezone.utc)
    retry_attempts = 3

    chat_turn = ChatMessageTurn(
        user_id=user_id,
        pdf_document_id=pdf_document_id,
        pdf_original_filename=pdf_original_filename,
        user_message_content=user_message_content,
        id=turn_id,
        user_message_timestamp=user_timestamp,
        llm_response_content=llm_content,
        llm_response_status=llm_status,
        llm_response_timestamp=llm_timestamp,
        retry_attempts=retry_attempts,
    )

    assert chat_turn.id == turn_id
    assert chat_turn.user_id == user_id
    assert chat_turn.pdf_document_id == pdf_document_id
    assert chat_turn.pdf_original_filename == pdf_original_filename
    assert chat_turn.user_message_content == user_message_content
    assert chat_turn.user_message_timestamp == user_timestamp
    assert chat_turn.llm_response_content == llm_content
    assert chat_turn.llm_response_status == llm_status
    assert chat_turn.llm_response_timestamp == llm_timestamp
    assert chat_turn.retry_attempts == retry_attempts


def test_mark_llm_processing():
    """Test mark_llm_processing method."""
    chat_turn = ChatMessageTurn(
        user_id=1,
        pdf_document_id="pdf123",
        pdf_original_filename="document.pdf",
        user_message_content="Hello, PDF!",
    )
    initial_timestamp = chat_turn.llm_response_timestamp

    chat_turn.mark_llm_processing()

    assert chat_turn.llm_response_status == LLMResponseStatus.PROCESSING
    assert isinstance(chat_turn.llm_response_timestamp, datetime)
    assert chat_turn.llm_response_timestamp.tzinfo == timezone.utc
    assert chat_turn.llm_response_timestamp > initial_timestamp if initial_timestamp else True


def test_set_llm_response_success():
    """Test set_llm_response_success method."""
    chat_turn = ChatMessageTurn(
        user_id=1,
        pdf_document_id="pdf123",
        pdf_original_filename="document.pdf",
        user_message_content="Hello, PDF!",
    )
    initial_timestamp = chat_turn.llm_response_timestamp
    success_content = "This is a successful response."

    chat_turn.set_llm_response_success(success_content)

    assert chat_turn.llm_response_content == success_content
    assert chat_turn.llm_response_status == LLMResponseStatus.COMPLETED_SUCCESS
    assert isinstance(chat_turn.llm_response_timestamp, datetime)
    assert chat_turn.llm_response_timestamp.tzinfo == timezone.utc
    assert chat_turn.llm_response_timestamp > initial_timestamp if initial_timestamp else True


def test_set_llm_response_failure():
    """Test set_llm_response_failure method."""
    chat_turn = ChatMessageTurn(
        user_id=1,
        pdf_document_id="pdf123",
        pdf_original_filename="document.pdf",
        user_message_content="Hello, PDF!",
    )
    initial_timestamp = chat_turn.llm_response_timestamp

    chat_turn.set_llm_response_failure()

    assert chat_turn.llm_response_status == LLMResponseStatus.FAILED_RETRIES_EXHAUSTED
    assert isinstance(chat_turn.llm_response_timestamp, datetime)
    assert chat_turn.llm_response_timestamp.tzinfo == timezone.utc
    assert chat_turn.llm_response_timestamp > initial_timestamp if initial_timestamp else True


def test_increment_retry():
    """Test increment_retry method."""
    chat_turn = ChatMessageTurn(
        user_id=1,
        pdf_document_id="pdf123",
        pdf_original_filename="document.pdf",
        user_message_content="Hello, PDF!",
    )
    initial_retry_attempts = chat_turn.retry_attempts

    chat_turn.increment_retry()

    assert chat_turn.retry_attempts == initial_retry_attempts + 1

    chat_turn.increment_retry()
    assert chat_turn.retry_attempts == initial_retry_attempts + 2
