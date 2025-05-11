import asyncio
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock  # Import AsyncMock

# Import the actual AuthenticatedUser model
from app.lib.security import AuthenticatedUser

# Import the actual dependencies module
from app.chat.controllers import dependencies as chat_dependencies
from app.lib import security  # Import the module containing the actual dependency

# Import response schemas and domain models for mocking return values
from app.chat.application.schemas import ChatMessageTurnResponse, PaginatedChatHistoryResponse
from app.chat.domain.models import ChatMessageTurn, LLMResponseStatus
from datetime import datetime, timezone, timedelta

# Import specific exceptions for side effects
from app.chat.domain.exceptions import NoPDFSelectedForChatError, PDFNotParsedForChatError
from app.pdf.domain.exceptions import PDFNotFoundError


# Assuming these mocks exist or need to be created
# For now, we'll use MagicMock as placeholders
class MockPDFRepository(MagicMock):
    async def save_pdf_meta(self, pdf_doc):
        # Simulate saving
        pass

    async def get_all_pdf_meta_for_user(self, user_id):
        # Simulate returning an empty list by default
        return []

    async def get_pdf_meta_by_id(self, pdf_id):
        # Simulate not finding a PDF by default
        return None


class MockChatRepository(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_turns = []  # Internal storage for saved turns

    async def save_chat_turn(self, chat_turn):
        # Simulate saving
        self._saved_turns.append(chat_turn)

    def get_saved_turns(self):
        # Helper for tests to inspect saved turns
        return self._saved_turns

    async def get_chat_history_for_user(self, user_id, skip=0, limit=20):
        # Simulate retrieving chat history, ordered by timestamp descending
        # Need to ensure the mock data added in steps is accessible here or handle it differently
        # For now, return a slice of saved turns (assuming they are added in order or sorted)
        # A more robust mock might store turns keyed by user_id and sort them
        # Let's assume for now get_chat_history_for_user gives us all turns and we filter/sort here
        all_turns = sorted(self._saved_turns, key=lambda x: x.user_message_timestamp, reverse=True)
        user_turns = [turn for turn in all_turns if turn.user_id == user_id]
        return user_turns[skip : skip + limit]

    async def count_chat_history_for_user(self, user_id):
        all_turns = sorted(self._saved_turns, key=lambda x: x.user_message_timestamp, reverse=True)
        user_turns = [turn for turn in all_turns if turn.user_id == user_id]
        return len(user_turns)


# Define a mock dependency for authentication that accepts context
def mock_get_current_authenticated_user(context):
    """
    Mock dependency to simulate an authenticated user.
    Returns an AuthenticatedUser instance using the user_id from context.
    """
    # Ensure user_id is set in context, e.g., by a 'Given a user is authenticated' step
    # Ensure user_id is set in context and is an integer
    if not hasattr(context, "user_id") or not isinstance(context.user_id, int):
        # Provide a default integer ID if not set or not an integer
        context.user_id = 123
    return AuthenticatedUser(id=int(context.user_id))  # Explicitly cast to int


def before_scenario(context, scenario):
    """
    Set up the test environment before each scenario.
    """
    # Set up an asyncio event loop
    try:
        context.loop = asyncio.get_running_loop()
    except RuntimeError:
        context.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(context.loop)

    # Set up the FastAPI test client
    # Assuming the FastAPI app is available via an import path like 'app.main:app'
    # You might need to adjust this import based on your project structure
    from app.main import app

    context.client = TestClient(app)

    # Set up mock repositories and defer task callable using AsyncMock where needed
    context.pdf_repo = AsyncMock()  # Use AsyncMock for async methods
    context.chat_repo = AsyncMock()  # Use AsyncMock for async methods
    context.defer_llm_task = AsyncMock()  # Use AsyncMock for async calls

    # Set up mock ChatApplicationService using AsyncMock
    context.chat_service = AsyncMock()

    # Define mock async functions for service methods that need scenario-specific behavior
    async def mock_submit_user_message(current_user_id, message_data):
        # Simulate creating the chat turn object
        mock_chat_turn = ChatMessageTurn(
            id=1,  # Use a consistent mock integer ID
            user_id=current_user_id,
            pdf_document_id=context.selected_pdf_id,  # Assuming selected_pdf_id is set in a Given step
            pdf_original_filename=context.selected_pdf_filename,  # Assuming selected_pdf_filename is set
            user_message_content=message_data.message,
            llm_response_content=None,
            llm_response_status=LLMResponseStatus.PENDING,
            user_message_timestamp=datetime.now(timezone.utc),
            llm_response_timestamp=None,
        )
        # Simulate saving the chat turn by awaiting the mock repo method
        await context.chat_repo.save_chat_turn(mock_chat_turn)

        # Simulate enqueuing the LLM task by awaiting the mock defer task
        await context.defer_llm_task(chat_turn_id=mock_chat_turn.id)

        # Return a dictionary matching the ChatMessageTurnResponse schema
        return {
            "id": mock_chat_turn.id,  # Use the ID from the created mock turn
            "user_id": current_user_id,
            "pdf_document_id": context.selected_pdf_id,
            "pdf_original_filename": context.selected_pdf_filename,  # Corrected attribute name
            "user_message_content": mock_chat_turn.user_message_content,
            "llm_response_content": None,  # LLM response is PENDING
            "llm_response_status": LLMResponseStatus.PENDING.value,
            "user_message_timestamp": mock_chat_turn.user_message_timestamp.isoformat(),
            "llm_response_timestamp": None,
        }

    async def mock_get_chat_history(current_user_id, page, size):
        # Simulate retrieving chat history
        # Create mock chat turns based on the expected total number of entries
        total_entries = context.expected_total_chat_entries  # Use the expected total from context
        mock_chat_turns = []
        # Create entries in reverse order of ID to simulate descending timestamp order
        for i in range(total_entries, 0, -1):
            mock_chat_turns.append(
                ChatMessageTurn(
                    id=i,
                    user_id=current_user_id,
                    pdf_document_id="mock_pdf_id",
                    pdf_original_filename="mock_document.pdf",
                    user_message_content=f"User message {i}",
                    llm_response_content=f"LLM response {i}",
                    llm_response_status=LLMResponseStatus.COMPLETED_SUCCESS,
                    user_message_timestamp=datetime.now(timezone.utc)
                    - timedelta(minutes=total_entries - i),  # Ensure descending order by timestamp
                    llm_response_timestamp=datetime.now(timezone.utc)
                    - timedelta(minutes=total_entries - i)
                    + timedelta(seconds=1),
                )
            )

        # Simulate pagination
        skip = (page - 1) * size
        paginated_turns = mock_chat_turns[skip : skip + size]

        # Format turns for the response schema
        formatted_turns = []
        for turn in paginated_turns:
            formatted_turns.append(
                {
                    "id": turn.id,
                    "user_id": turn.user_id,
                    "pdf_document_id": turn.pdf_document_id,
                    "pdf_original_filename": turn.pdf_original_filename,
                    "user_message_content": turn.user_message_content,
                    "llm_response_content": turn.llm_response_content,
                    "llm_response_status": turn.llm_response_status.value,
                    "user_message_timestamp": turn.user_message_timestamp.isoformat(),
                    "llm_response_timestamp": turn.llm_response_timestamp.isoformat(),
                }
            )

        # Calculate total pages
        total_pages = (total_entries + size - 1) // size

        # Return a dictionary matching the PaginatedChatHistoryResponse schema
        return {
            "total_items": total_entries,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": size,
            "data": formatted_turns,
        }

    async def mock_get_chat_history_empty(current_user_id, page, size):
        # Simulate retrieving an empty chat history
        return {
            "total_items": 0,
            "total_pages": 0,
            "current_page": page,
            "page_size": size,
            "data": [],
        }

    # Configure mock chat_service methods based on the scenario name
    if scenario.name == "Successfully initiate chat interaction with a selected and parsed PDF":
        context.chat_service.submit_user_message.side_effect = mock_submit_user_message
    elif scenario.name == "Attempt to initiate chat interaction when no PDF is selected":
        context.chat_service.submit_user_message.side_effect = NoPDFSelectedForChatError(
            "No PDF selected for chat"
        )
    elif scenario.name == "Attempt to initiate chat interaction when the selected PDF is not parsed":
        context.chat_service.submit_user_message.side_effect = PDFNotParsedForChatError(
            "PDF not parsed for chat"
        )
    elif scenario.name == "Attempt to initiate chat interaction when the selected PDF is not found":
        context.chat_service.submit_user_message.side_effect = PDFNotFoundError(
            "Selected PDF for chat not found"
        )
    elif scenario.name == "Successfully retrieve paginated chat history":
        context.chat_service.get_chat_history.side_effect = mock_get_chat_history
    elif scenario.name == "Retrieve chat history when no entries exist for the user":
        context.chat_service.get_chat_history.side_effect = mock_get_chat_history_empty
    elif scenario.name == "Retrieve subsequent pages of chat history using pagination parameters":
        context.chat_service.get_chat_history.side_effect = mock_get_chat_history

    # Set a default authenticated user ID (can be overridden by steps)
    context.user_id = 123  # Use an integer ID

    # Mock dependencies in the FastAPI app
    # This requires knowing how dependencies are injected in app.main or routers
    app.dependency_overrides[chat_dependencies.get_chat_application_service] = lambda: context.chat_service
    # Assuming get_pdf_repository is also a dependency used by the chat service
    # If not, this override might not be necessary for chat tests
    # app.dependency_overrides[chat_dependencies.get_pdf_repository] = lambda: context.pdf_repo
    # Pass the current context to the mock dependency function using a lambda
    app.dependency_overrides[security.get_current_authenticated_user] = (
        lambda: mock_get_current_authenticated_user(context)
    )
    # Assuming defer_llm_processing_task is a dependency provided elsewhere, e.g., in chat.application.tasks
    # from app.chat.application import tasks # Import the module containing the actual dependency
    # app.dependency_overrides[tasks.defer_llm_processing_task] = lambda: context.defer_llm_task


def after_scenario(context, scenario):
    """
    Clean up the test environment after each scenario.
    """
    # Close the asyncio loop if it was created in before_scenario
    if hasattr(context, "loop") and not context.loop.is_running():
        context.loop.close()
        asyncio.set_event_loop(None)

    # Clean up dependency overrides if they were set
    # if 'app' in locals(): # Check if app was imported
    #     if chat_dependencies.get_pdf_repository in app.dependency_overrides:
    #         del app.dependency_overrides[chat_dependencies.get_pdf_repository]
    #     if chat_dependencies.get_chat_repository in app.dependency_overrides:
    #         del app.dependency_overrides[chat_dependencies.get_chat_repository]
    #     if chat_dependencies.defer_llm_processing_task in app.dependency_overrides:
    #         del app.dependency_overrides[tasks.defer_llm_processing_task]
