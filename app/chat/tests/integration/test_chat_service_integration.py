import pytest
from typing import List, Optional, Callable, Coroutine, Any
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

# Assuming necessary imports from the application
from app.core.config import Settings
from app.chat.domain.models import ChatMessageTurn, LLMResponseStatus
from app.chat.infrastructure.repositories.chat_repository import IChatRepository
from app.chat.domain.exceptions import (
    NoPDFSelectedForChatError,
    PDFNotParsedForChatError,
    ChatDomainError,
)
from app.pdf.infrastucture.repositories.pdf_repository import IPDFRepository
from app.pdf.domain.models import PDFDocument, PDFParseStatus
from app.pdf.domain.exceptions import PDFNotFoundError

from app.chat.application.schemas import (
    ChatMessageRequest,
    ChatMessageTurnResponse,
    PaginatedChatHistoryResponse,
)
from app.chat.application.services import ChatApplicationService


# Mock implementations for dependencies
class MockChatRepository(IChatRepository):
    def __init__(self):
        self._chat_turns: List[ChatMessageTurn] = []
        self._next_id = 1

    async def create_chat_turn(self, chat_turn: ChatMessageTurn) -> ChatMessageTurn:
        # Simulate database assignment of ID (using int)
        if chat_turn.id is None:
            chat_turn.id = self._next_id  # Assign integer ID
            self._next_id += 1
        self._chat_turns.append(chat_turn)
        return chat_turn

    async def get_chat_turn_by_id(
        self, turn_id: int
    ) -> Optional[ChatMessageTurn]:  # Changed type hint to int
        for turn in self._chat_turns:
            if turn.id == turn_id:
                return turn
        return None

    async def update_chat_turn(self, chat_turn: ChatMessageTurn) -> ChatMessageTurn:
        for i, turn in enumerate(self._chat_turns):
            if turn.id == chat_turn.id:
                self._chat_turns[i] = chat_turn
                return chat_turn
        raise ValueError(f"Chat turn with ID {chat_turn.id} not found")  # Or a specific exception

    async def get_chat_history_for_user(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> List[ChatMessageTurn]:
        user_history = [turn for turn in self._chat_turns if turn.user_id == user_id]
        # Sort by timestamp descending for history
        user_history.sort(key=lambda x: x.user_message_timestamp, reverse=True)
        return user_history[skip : skip + limit]

    async def count_chat_history_for_user(self, user_id: int) -> int:
        return len([turn for turn in self._chat_turns if turn.user_id == user_id])


class MockPDFRepository(IPDFRepository):
    def __init__(self):
        self._pdfs: List[PDFDocument] = []

    async def create_pdf_document(self, pdf_document: PDFDocument) -> PDFDocument:
        # Simulate database assignment of ID
        if pdf_document.id is None:
            pdf_document.id = f"pdf_{len(self._pdfs) + 1}"
        self._pdfs.append(pdf_document)
        return pdf_document

    async def get_pdf_document_by_id(self, pdf_id: str) -> Optional[PDFDocument]:
        for pdf in self._pdfs:
            if pdf.id == pdf_id:
                return pdf
        return None

    async def get_selected_pdf_for_user(self, user_id: int) -> Optional[PDFDocument]:
        for pdf in self._pdfs:
            if pdf.user_id == user_id and pdf.is_selected_for_chat:
                return pdf
        return None

    async def update_pdf_document(self, pdf_document: PDFDocument) -> PDFDocument:
        for i, pdf in enumerate(self._pdfs):
            if pdf.id == pdf_document.id:
                self._pdfs[i] = pdf_document
                return pdf_document
        raise ValueError(f"PDF document with ID {pdf_document.id} not found")  # Or a specific exception

    async def list_pdf_documents_for_user(self, user_id: int) -> List[PDFDocument]:
        return [pdf for pdf in self._pdfs if pdf.user_id == user_id]

    async def delete_pdf_document(self, pdf_id: str) -> bool:
        initial_count = len(self._pdfs)
        self._pdfs = [pdf for pdf in self._pdfs if pdf.id != pdf_id]
        return len(self._pdfs) < initial_count

    async def get_pdf_text_content(self, pdf_id: str) -> Optional[str]:
        pdf = await self.get_pdf_document_by_id(pdf_id)
        if pdf and pdf.parse_status == PDFParseStatus.PARSED_SUCCESS:
            # In a real mock, you might store text content or return a placeholder
            return f"Mock text content for PDF {pdf_id}"
        return None


# Mock Settings
class MockSettings(Settings):
    # Override settings relevant to the service if needed
    LLM_RETRY_ATTEMPTS: int = 3
    # Add other settings used by the service


# Mock defer_llm_task
async def mock_defer_llm_task(chat_turn_id: int):
    # This mock function does nothing, or could record calls for assertion
    print(f"Mock defer_llm_task called for chat_turn_id: {chat_turn_id}")
    pass  # Simulate deferring the task


# Fixture for the ChatApplicationService with mock dependencies
@pytest.fixture
def chat_service():
    chat_repo = MockChatRepository()
    pdf_repo = MockPDFRepository()
    settings = MockSettings()
    # Use AsyncMock if you need to assert calls or return specific values
    defer_llm_task_mock = AsyncMock(side_effect=mock_defer_llm_task)
    service = ChatApplicationService(
        chat_repo=chat_repo,
        pdf_repo=pdf_repo,
        settings=settings,
        defer_llm_task=defer_llm_task_mock,
    )
    # Attach mocks to the service instance for potential inspection in tests
    service.chat_repo = chat_repo
    service.pdf_repo = pdf_repo
    service.defer_llm_task = defer_llm_task_mock
    return service


# --- Test Implementations ---


# test_submit_user_message_success
@pytest.mark.asyncio
async def test_submit_user_message_success(chat_service):
    # Setup: Create a user and a selected, parsed PDF in the mock PDF repo
    user_id = 123
    pdf_id = "pdf_abc"
    selected_pdf = PDFDocument(
        id=pdf_id,
        user_id=user_id,
        gridfs_file_id="mock_gridfs_id",  # Added gridfs_file_id
        original_filename="test.pdf",
        parse_status=PDFParseStatus.PARSED_SUCCESS,
        upload_date=datetime.now(timezone.utc),
        is_selected_for_chat=True,
        # Add other required PDFDocument fields if any
    )
    await chat_service.pdf_repo.create_pdf_document(selected_pdf)  # Use the mock repo directly

    # Input message data
    message_data = ChatMessageRequest(message="Hello, PDF!")

    # Execute the service method
    response = await chat_service.submit_user_message(user_id, message_data)

    # Assertions
    # 1. Check the response structure and content
    assert isinstance(response, ChatMessageTurnResponse)
    assert response.user_id == user_id
    assert response.pdf_document_id == pdf_id
    assert response.user_message_content == message_data.message
    assert response.llm_response_status == LLMResponseStatus.PENDING  # Should be PENDING initially
    assert response.id is not None  # Should have received an ID from the mock repo

    # 2. Check if the chat turn was persisted in the mock chat repo
    persisted_turn = await chat_service.chat_repo.get_chat_turn_by_id(response.id)
    assert persisted_turn is not None
    assert persisted_turn.user_id == user_id
    assert persisted_turn.pdf_document_id == pdf_id
    assert persisted_turn.user_message_content == message_data.message
    assert persisted_turn.llm_response_status == LLMResponseStatus.PENDING

    # 3. Check if the background task was deferred
    chat_service.defer_llm_task.assert_called_once_with(
        int(response.id)
    )  # Assuming ID is int in defer_llm_task


# test_submit_user_message_no_pdf_selected
@pytest.mark.asyncio
async def test_submit_user_message_no_pdf_selected(chat_service):
    # Setup: Ensure no PDF is selected for the user in the mock PDF repo
    user_id = 456
    # The default state of MockPDFRepository is no PDFs, so no explicit setup needed here
    # unless we had added PDFs in a previous test run within the same fixture scope (not the case here)

    # Input message data
    message_data = ChatMessageRequest(message="Hello without PDF!")

    # Execute the service method and assert that it raises NoPDFSelectedForChatError
    with pytest.raises(NoPDFSelectedForChatError):
        await chat_service.submit_user_message(user_id, message_data)

    # Optional: Assert that no chat turn was created and no task was deferred
    assert await chat_service.chat_repo.count_chat_history_for_user(user_id) == 0
    chat_service.defer_llm_task.assert_not_called()


# test_submit_user_message_pdf_not_parsed
@pytest.mark.asyncio
async def test_submit_user_message_pdf_not_parsed(chat_service):
    # Setup: Create a user and a selected, but not parsed, PDF in the mock PDF repo
    user_id = 789
    pdf_id = "pdf_def"
    selected_pdf = PDFDocument(
        id=pdf_id,
        user_id=user_id,
        gridfs_file_id="mock_gridfs_id_2",
        original_filename="unparsed.pdf",
        parse_status=PDFParseStatus.UNPARSED,  # Set status to UNPARSED
        upload_date=datetime.now(timezone.utc),
        is_selected_for_chat=True,
        # Add other required PDFDocument fields if any
    )
    await chat_service.pdf_repo.create_pdf_document(selected_pdf)

    # Input message data
    message_data = ChatMessageRequest(message="Hello to unparsed PDF!")

    # Execute the service method and assert that it raises PDFNotParsedForChatError
    with pytest.raises(PDFNotParsedForChatError) as excinfo:
        await chat_service.submit_user_message(user_id, message_data)

    # Optional: Assert the exception details
    assert excinfo.value.pdf_id == pdf_id

    # Optional: Assert that no chat turn was created and no task was deferred
    assert await chat_service.chat_repo.count_chat_history_for_user(user_id) == 0
    chat_service.defer_llm_task.assert_not_called()


# test_submit_user_message_repo_create_fails
@pytest.mark.asyncio
async def test_submit_user_message_repo_create_fails(chat_service):
    # Setup: Create a user and a selected, parsed PDF in the mock PDF repo
    user_id = 1011
    pdf_id = "pdf_ghi"
    selected_pdf = PDFDocument(
        id=pdf_id,
        user_id=user_id,
        gridfs_file_id="mock_gridfs_id_3",
        original_filename="parsed_fail.pdf",
        parse_status=PDFParseStatus.PARSED_SUCCESS,
        upload_date=datetime.now(timezone.utc),
        is_selected_for_chat=True,
    )
    await chat_service.pdf_repo.create_pdf_document(selected_pdf)

    # Setup: Configure the mock chat repo to raise an exception on create_chat_turn
    # We need to replace the create_chat_turn method on the mock instance for this test
    # Setup: Configure the mock chat repo to return a ChatMessageTurn with id=None on create_chat_turn
    # This simulates the scenario where the repository fails to assign an ID.
    original_create_chat_turn = chat_service.chat_repo.create_chat_turn

    async def returning_none_id_turn(chat_turn: ChatMessageTurn) -> ChatMessageTurn:
        # Return the turn object but with id explicitly set to None
        chat_turn.id = None
        return chat_turn

    chat_service.chat_repo.create_chat_turn = AsyncMock(side_effect=returning_none_id_turn)

    # Input message data
    message_data = ChatMessageRequest(message="Message that should result in None ID")

    # Execute the service method and assert that it raises ChatDomainError
    with pytest.raises(ChatDomainError) as excinfo:
        await chat_service.submit_user_message(user_id, message_data)

    # Assert the exception message
    assert "Failed to persist chat message properly before LLM task." in str(excinfo.value)

    # Assert that the defer_llm_task was NOT called because the service should raise
    # the error before deferring the task if the ID is None.
    chat_service.defer_llm_task.assert_not_called()

    # Restore the original method (good practice)
    # chat_service.chat_repo.create_chat_turn = original_create_chat_turn


# test_get_chat_history_success
@pytest.mark.asyncio
async def test_get_chat_history_success(chat_service):
    # Setup: Add some chat turns for a user to the mock chat repo
    user_id = 2022
    pdf_id = "pdf_jkl"
    turn1 = ChatMessageTurn(
        user_id=user_id,
        pdf_document_id=pdf_id,
        pdf_original_filename="history.pdf",
        user_message_content="Message 1",
        user_message_timestamp=datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        llm_response_status=LLMResponseStatus.COMPLETED_SUCCESS,  # Changed to COMPLETED_SUCCESS
        llm_response_content="Response 1",
        llm_response_timestamp=datetime(2023, 1, 1, 10, 1, 0, tzinfo=timezone.utc),
    )
    turn2 = ChatMessageTurn(
        user_id=user_id,
        pdf_document_id=pdf_id,
        pdf_original_filename="history.pdf",
        user_message_content="Message 2",
        user_message_timestamp=datetime(2023, 1, 1, 10, 2, 0, tzinfo=timezone.utc),
        llm_response_status=LLMResponseStatus.COMPLETED_SUCCESS,  # Changed to COMPLETED_SUCCESS
        llm_response_content="Response 2",
        llm_response_timestamp=datetime(2023, 1, 1, 10, 3, 0, tzinfo=timezone.utc),
    )
    turn3 = ChatMessageTurn(
        user_id=user_id,
        pdf_document_id=pdf_id,
        pdf_original_filename="history.pdf",
        user_message_content="Message 3",
        user_message_timestamp=datetime(2023, 1, 1, 10, 4, 0, tzinfo=timezone.utc),
        llm_response_status=LLMResponseStatus.COMPLETED_SUCCESS,  # Changed to COMPLETED_SUCCESS
        llm_response_content="Response 3",
        llm_response_timestamp=datetime(2023, 1, 1, 10, 5, 0, tzinfo=timezone.utc),
    )
    # Add turns in non-chronological order to test sorting in mock repo
    await chat_service.chat_repo.create_chat_turn(turn2)
    await chat_service.chat_repo.create_chat_turn(turn1)
    await chat_service.chat_repo.create_chat_turn(turn3)

    # Execute the service method
    response = await chat_service.get_chat_history(user_id)

    # Assertions
    assert isinstance(response, PaginatedChatHistoryResponse)
    assert response.total_items == 3
    assert response.total_pages == 1
    assert response.current_page == 1
    assert response.page_size == 20
    assert len(response.data) == 3

    # Check if the data is sorted by user_message_timestamp descending
    assert response.data[0].user_message_content == "Message 3"
    assert response.data[1].user_message_content == "Message 2"
    assert response.data[2].user_message_content == "Message 1"

    # Check content of the first item
    assert response.data[0].user_id == user_id
    assert response.data[0].pdf_document_id == pdf_id
    assert response.data[0].pdf_original_filename == "history.pdf"
    assert response.data[0].user_message_content == "Message 3"
    assert (
        response.data[0].llm_response_status == LLMResponseStatus.COMPLETED_SUCCESS
    )  # Changed to COMPLETED_SUCCESS
    assert response.data[0].llm_response_content == "Response 3"
    assert response.data[0].id is not None


# test_get_chat_history_pagination
@pytest.mark.asyncio
async def test_get_chat_history_pagination(chat_service):
    # Setup: Add many chat turns for a user to the mock chat repo
    user_id = 3033
    pdf_id = "pdf_mno"
    num_turns = 25
    turns = []
    for i in range(num_turns):
        # Create turns with timestamps in increasing order
        turn = ChatMessageTurn(
            user_id=user_id,
            pdf_document_id=pdf_id,
            pdf_original_filename="paginated.pdf",
            user_message_content=f"Message {i + 1}",
            user_message_timestamp=datetime(2023, 1, 1, 10, 0, i, tzinfo=timezone.utc),
            llm_response_status=LLMResponseStatus.COMPLETED_SUCCESS,
            llm_response_content=f"Response {i + 1}",
            llm_response_timestamp=datetime(2023, 1, 1, 10, 0, i + 1, tzinfo=timezone.utc),
        )
        turns.append(turn)

    # Add turns to the repo (order doesn't strictly matter due to sorting in mock repo)
    for turn in turns:
        await chat_service.chat_repo.create_chat_turn(turn)

    # Test Page 1, Size 10
    response_page1 = await chat_service.get_chat_history(user_id, page=1, size=10)
    assert isinstance(response_page1, PaginatedChatHistoryResponse)
    assert response_page1.total_items == num_turns
    assert response_page1.total_pages == 3  # 25 items, size 10 -> 3 pages (10, 10, 5)
    assert response_page1.current_page == 1
    assert response_page1.page_size == 10
    assert len(response_page1.data) == 10
    # Check order (most recent first) and content
    for i in range(10):
        expected_message_num = num_turns - i  # Messages are 25, 24, ..., 16
        assert response_page1.data[i].user_message_content == f"Message {expected_message_num}"

    # Test Page 2, Size 10
    response_page2 = await chat_service.get_chat_history(user_id, page=2, size=10)
    assert isinstance(response_page2, PaginatedChatHistoryResponse)
    assert response_page2.total_items == num_turns
    assert response_page2.total_pages == 3
    assert response_page2.current_page == 2
    assert response_page2.page_size == 10
    assert len(response_page2.data) == 10
    # Check order and content
    for i in range(10):
        expected_message_num = num_turns - 10 - i  # Messages are 15, 14, ..., 6
        assert response_page2.data[i].user_message_content == f"Message {expected_message_num}"

    # Test Page 3, Size 10 (last page with fewer items)
    response_page3 = await chat_service.get_chat_history(user_id, page=3, size=10)
    assert isinstance(response_page3, PaginatedChatHistoryResponse)
    assert response_page3.total_items == num_turns
    assert response_page3.total_pages == 3
    assert response_page3.current_page == 3
    assert response_page3.page_size == 10
    assert len(response_page3.data) == 5  # Remaining 5 messages
    # Check order and content
    for i in range(5):
        expected_message_num = num_turns - 20 - i  # Messages are 5, 4, ..., 1
        assert response_page3.data[i].user_message_content == f"Message {expected_message_num}"

    # Test a page beyond the last page
    response_page4 = await chat_service.get_chat_history(user_id, page=4, size=10)
    assert isinstance(response_page4, PaginatedChatHistoryResponse)
    assert response_page4.total_items == num_turns
    assert response_page4.total_pages == 3
    assert response_page4.current_page == 4  # Service might return the requested page number even if empty
    assert response_page4.page_size == 10
    assert len(response_page4.data) == 0  # Should be empty


# test_get_chat_history_empty
@pytest.mark.asyncio
async def test_get_chat_history_empty(chat_service):
    # Setup: Ensure no chat history exists for the user in the mock chat repo
    user_id = 4044
    # The default state of MockChatRepository is empty, so no explicit setup needed here

    # Execute the service method
    response = await chat_service.get_chat_history(user_id)

    # Assertions
    assert isinstance(response, PaginatedChatHistoryResponse)
    assert response.total_items == 0
    assert response.total_pages == 0
    assert response.current_page == 1  # Should still return page 1 even if empty
    assert response.page_size == 20  # Should still return the default page size
    assert len(response.data) == 0  # Data list should be empty


# --- End Test Implementations ---
