from behave import given, when, then
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import asyncio
import json

from app.pdf.tests.integration.test_pdf_service_integration import MockPDFRepository
from app.pdf.domain.models import PDFDocument, PDFParseStatus
from app.chat.application.schemas import (
    ChatMessageRequest,
    ChatMessageTurnResponse,
    PaginatedChatHistoryResponse,
)
from app.chat.domain.models import ChatMessageTurn, LLMResponseStatus
from datetime import datetime, timezone, timedelta

# Assuming environment.py in app/chat/tests/features will set up:
# context.client: TestClient instance
# context.user_id: Authenticated user ID
# context.pdf_repo: MockPDFRepository instance (or similar mock for PDF access)
# context.chat_repo: MockChatRepository instance (or similar mock for Chat access)
# context.defer_llm_task: Mock callable for deferring LLM task


# Helper function to add a mock PDF to the repo
async def add_mock_pdf(context, pdf_id, parse_status, is_selected=False, user_id=None):
    if user_id is None:
        user_id = context.user_id
    pdf_doc = PDFDocument(
        id=pdf_id,
        user_id=user_id,
        gridfs_file_id=f"gridfs_{pdf_id}",
        original_filename=f"{pdf_id}.pdf",
        upload_date=datetime.now(timezone.utc),
        parse_status=parse_status,
        is_selected_for_chat=is_selected,
    )
    await context.pdf_repo.save_pdf_meta(pdf_doc)
    return pdf_doc


# Helper function to add mock chat history entries
async def add_mock_chat_history(context, user_id, pdf_document_id, pdf_original_filename, num_entries):
    chat_entries = []
    base_time = datetime.now(timezone.utc)
    for i in range(num_entries):
        chat_turn = ChatMessageTurn(
            id=f"chat_turn_{i+1}",
            user_id=user_id,
            pdf_document_id=pdf_document_id,
            pdf_original_filename=pdf_original_filename,
            user_message_content=f"User message {i+1}",
            llm_response_content=f"LLM response {i+1}",
            llm_response_status=LLMResponseStatus.COMPLETED_SUCCESS,
            user_message_timestamp=base_time
            - timedelta(seconds=num_entries - 1 - i),  # Ensure descending order by timestamp
            llm_response_timestamp=base_time
            - timedelta(seconds=num_entries - 1 - i)
            + timedelta(seconds=1),
        )
        await context.chat_repo.save_chat_turn(chat_turn)
        chat_entries.append(chat_turn)
    return chat_entries


# --- New Step Definitions ---


@given("a user is authenticated")
def step_impl(context):
    """
    Sets a mock user ID in the context to simulate authentication.
    """
    context.user_id = "mock_authenticated_user_id"


@then("the system returns an HTTP 202 Accepted response")
def step_impl(context):
    """
    Verifies that the HTTP response status code is 202.
    """
    assert (
        context.response.status_code == 202
    ), f"Expected status code 202, but got {context.response.status_code}"


@then("the system returns an HTTP 200 OK response")
def step_impl(context):
    """
    Verifies that the HTTP response status code is 200.
    """
    assert (
        context.response.status_code == 200
    ), f"Expected status code 200, but got {context.response.status_code}"


# --- End New Step Definitions ---


# Scenario: Successfully initiate chat interaction with a selected and parsed PDF


@given("the user has a successfully parsed PDF selected for chat")
def step_impl(context):
    """
    Adds a mock PARSED_SUCCESS PDF selected for chat to the mock repo.
    """
    context.selected_pdf_id = "selected_parsed_pdf_1"
    context.selected_pdf_filename = "selected_parsed_document.pdf"
    context.loop.run_until_complete(
        add_mock_pdf(
            context,
            context.selected_pdf_id,
            PDFParseStatus.PARSED_SUCCESS,
            is_selected=True,
        )
    )


@given("the user provides a chat message")
def step_impl(context):
    """
    Stores a mock chat message in the context.
    """
    context.chat_message_content = "What is the main topic of the document?"


@when("the user submits the chat message via POST /pdf-chat")
def step_impl(context):
    """
    Sends a POST request to the /pdf-chat endpoint with the chat message.
    """
    request_body = {"message": context.chat_message_content}
    context.response = context.client.post("/pdf-chat", json=request_body)


@then("the system saves the user message and an LLM placeholder in chat history with status PENDING")
def step_impl(context):
    """
    Verifies that a new chat turn is saved in the mock chat repo with PENDING status.
    """
    assert hasattr(context, "chat_repo"), "MockChatRepository not available in context."
    assert hasattr(context, "user_id"), "User ID not available in context."
    assert hasattr(context, "selected_pdf_id"), "Selected PDF ID not available in context."
    assert hasattr(context, "chat_message_content"), "Chat message content not available in context."

    # In the mock repo, we expect a new chat turn to have been saved.
    # We need to retrieve it and check its contents.
    # The service should have created a new chat turn and saved it.
    # We can check the last saved item in the mock repo's internal storage.
    # Assuming MockChatRepository has a way to access saved turns.
    assert hasattr(context, "chat_repo"), "MockChatRepository not available in context."
    assert hasattr(context, "user_id"), "User ID not available in context."
    assert hasattr(context, "selected_pdf_id"), "Selected PDF ID not available in context."
    assert hasattr(context, "chat_message_content"), "Chat message content not available in context."

    # Verify that chat_repo.save_chat_turn was called exactly once
    # We check the method_calls list on the mock object
    assert (
        len(context.chat_repo.method_calls) == 1
    ), f"Expected 1 call to chat_repo methods, but got {len(context.chat_repo.method_calls)}"
    call_name, call_args, call_kwargs = context.chat_repo.method_calls[0]

    assert call_name == "save_chat_turn", f"Expected call to 'save_chat_turn', but got '{call_name}'"
    assert (
        len(call_args) == 1
    ), f"Expected save_chat_turn to be called with 1 argument, but got {len(call_args)}"

    saved_chat_turn = call_args[0]

    assert isinstance(
        saved_chat_turn, ChatMessageTurn
    ), f"Expected argument to be ChatMessageTurn, but got {type(saved_chat_turn)}"

    assert saved_chat_turn.user_id == context.user_id, "Saved chat turn has incorrect user ID."
    assert (
        saved_chat_turn.pdf_document_id == context.selected_pdf_id
    ), "Saved chat turn has incorrect PDF ID."
    assert (
        saved_chat_turn.user_message_content == context.chat_message_content
    ), "Saved user message content is incorrect."
    assert (
        saved_chat_turn.llm_response_content is None
    ), "Saved LLM response content should be None initially."
    assert (
        saved_chat_turn.llm_response_status == LLMResponseStatus.PENDING
    ), "Saved LLM response status should be PENDING."
    assert (
        saved_chat_turn.pdf_original_filename == context.selected_pdf_filename
    ), "Saved chat turn has incorrect PDF filename."

    # Store the ID of the newly created chat turn for later steps if needed
    # The mock service creates the ChatMessageTurn, so we get the ID from there
    context.new_chat_turn_id = saved_chat_turn.id


@then("the system enqueues an LLM processing task")
def step_impl(context):
    """
    Verifies that the mock defer_llm_task callable was called with the correct chat turn ID.
    """
    assert hasattr(context, "defer_llm_task"), "Mock defer_llm_task not available in context."
    # Verify that defer_llm_task was awaited exactly once with the correct chat turn ID
    context.defer_llm_task.assert_awaited_once_with(chat_turn_id=context.new_chat_turn_id)


@then("the response contains the initial chat turn with the user message and PENDING LLM response")
def step_impl(context):
    """
    Verifies the structure and content of the 202 Accepted response body.
    """
    response_body = context.response.json()
    assert isinstance(response_body, dict), "Response body is not a dictionary."

    # Validate against the schema (optional but good practice)
    try:
        ChatMessageTurnResponse.model_validate(response_body)
    except Exception as e:
        assert False, f"Response body does not match ChatMessageTurnResponse schema: {e}"

    assert (
        response_body.get("user_message_content") == context.chat_message_content
    ), "Response user message content is incorrect."
    assert (
        response_body.get("llm_response_content") is None
    ), "Response LLM response content should be None."
    assert (
        response_body.get("llm_response_status") == LLMResponseStatus.PENDING.value
    ), "Response LLM status should be PENDING."
    assert (
        response_body.get("pdf_original_filename") == context.selected_pdf_filename
    ), "Response PDF filename is incorrect."
    # Check if the response ID matches the newly created turn ID
    # The mock service returns a fixed ID (1), so we check against that
    assert response_body.get("id") == 1, "Response ID does not match the expected mock ID (1)."


# Scenario: Attempt to initiate chat interaction when no PDF is selected


@given("no PDF is selected for chat")
def step_impl(context):
    """
    Ensures no PDF is marked as selected for the user in the mock repo.
    """
    assert hasattr(context, "pdf_repo"), "MockPDFRepository not available in context."
    user_id = context.user_id
    # Ensure no PDF for this user has is_selected_for_chat = True
    all_user_pdfs = context.loop.run_until_complete(
        context.pdf_repo.get_all_pdf_meta_for_user(user_id=user_id)
    )
    for pdf in all_user_pdfs:
        assert pdf.is_selected_for_chat is False, f"PDF {pdf.id} is unexpectedly selected for chat."


@then("the system returns an HTTP 400 Bad Request response")
def step_impl(context):
    """
    Verifies that the HTTP response status code is 400.
    """
    assert (
        context.response.status_code == 400
    ), f"Expected status code 400, but got {context.response.status_code}"


@then("the response indicates that no PDF is selected for chat")
def step_impl(context):
    """
    Verifies the error message in the 400 response body.
    """
    response_body = context.response.json()
    assert isinstance(response_body, dict), "Response body is not a dictionary."
    assert "detail" in response_body, "Response body does not contain 'detail'."
    assert (
        "No PDF selected for chat" in response_body["detail"]
    ), f"Expected error message 'No PDF selected for chat', but got '{response_body['detail']}'"


# Scenario: Attempt to initiate chat interaction when the selected PDF is not parsed


@given("the user has a PDF selected for chat with parse status {status}")
def step_impl(context, status):
    """
    Adds a mock PDF with the specified parse status, selected for chat, to the mock repo.
    Handles the special case where the status string is "UNPARSED or PARSING or PARSED_FAILURE".
    """
    if status == "UNPARSED or PARSING or PARSED_FAILURE":
        # This scenario tests the case where the PDF is NOT successfully parsed.
        # We don't need to add a specific PDF here, as the test setup
        # should ensure that if a PDF is selected, it's not PARSED_SUCCESS.
        # However, the scenario implies a PDF *is* selected, just not parsed.
        # Let's add a PDF with UNPARSED status for this specific case.
        context.selected_pdf_id = "selected_unparsed_pdf_1"
        context.selected_pdf_filename = "selected_unparsed_document.pdf"
        context.loop.run_until_complete(
            add_mock_pdf(
                context,
                context.selected_pdf_id,
                PDFParseStatus.UNPARSED,  # Use UNPARSED as a representative non-parsed status
                is_selected=True,
            )
        )
    else:
        context.selected_pdf_id = f"selected_pdf_status_{status.lower()}_1"
        context.selected_pdf_filename = f"selected_document_status_{status.lower()}.pdf"
        try:
            parse_status_enum = PDFParseStatus[status]
        except KeyError:
            assert False, f"""Invalid parse status provided: {status}.
                Must be one of {list(PDFParseStatus.__members__.keys())}
                or "UNPARSED or PARSING or PARSED_FAILURE"."""

        context.loop.run_until_complete(
            add_mock_pdf(
                context,
                context.selected_pdf_id,
                parse_status_enum,
                is_selected=True,
            )
        )


@then("the system returns an HTTP 409 Conflict response")
def step_impl(context):
    """
    Verifies that the HTTP response status code is 409.
    """
    assert (
        context.response.status_code == 409
    ), f"Expected status code 409, but got {context.response.status_code}"


@then("the response indicates that the selected PDF is not parsed")
def step_impl(context):
    """
    Verifies the error message in the 409 response body.
    """
    response_body = context.response.json()
    assert isinstance(response_body, dict), "Response body is not a dictionary."
    assert "detail" in response_body, "Response body does not contain 'detail'."
    # The exact error message might vary, check for a substring
    assert (
        "PDF not parsed for chat" in response_body["detail"]
    ), f"Expected error message containing 'PDF not parsed for chat', but got '{response_body['detail']}'"


# Scenario: Attempt to initiate chat interaction when the selected PDF is not found


@given("the user has selected a PDF that does not exist")
def step_impl(context):
    """
    Sets the selected PDF ID in the context to a value that does not exist in the mock repo.
    """
    context.selected_pdf_id = "non_existent_pdf_id"
    # No need to add a PDF to the repo in this case


@then("the system returns an HTTP 404 Not Found response")
def step_impl(context):
    """
    Verifies that the HTTP response status code is 404.
    """
    assert (
        context.response.status_code == 404
    ), f"Expected status code 404, but got {context.response.status_code}"


@then("the response indicates that the selected PDF was not found")
def step_impl(context):
    """
    Verifies the error message in the 404 response body.
    """
    response_body = context.response.json()
    assert isinstance(response_body, dict), "Response body is not a dictionary."
    assert "detail" in response_body, "Response body does not contain 'detail'."
    assert "Selected PDF for chat not found" in response_body["detail"], f"""Expected error message
    containing 'Selected PDF for chat not found', but got '{response_body['detail']}'"""


# Scenario: Successfully retrieve paginated chat history


@given("the user has previous chat history entries")
def step_impl(context):
    """
    Adds mock chat history entries to the mock chat repo for the authenticated user.
    """
    assert hasattr(context, "chat_repo"), "MockChatRepository not available in context."
    assert hasattr(context, "user_id"), "User ID not available in context."

    # Add a mock selected PDF first, as chat entries are linked to a PDF
    context.selected_pdf_id = "chat_history_pdf_1"
    context.selected_pdf_filename = "chat_history_document.pdf"
    context.loop.run_until_complete(
        add_mock_pdf(
            context,
            context.selected_pdf_id,
            PDFParseStatus.PARSED_SUCCESS,
            is_selected=True,
        )
    )

    # Add mock chat entries
    num_entries = 15  # Add enough entries to test pagination later
    context.loop.run_until_complete(
        add_mock_chat_history(
            context, context.user_id, context.selected_pdf_id, context.selected_pdf_filename, num_entries
        )
    )
    context.expected_total_chat_entries = num_entries


@when("the user requests their chat history via GET /chat-history")
def step_impl(context):
    """
    Sends a GET request to the /chat-history endpoint.
    """
    context.response = context.client.get("/chat-history")


@then("the response contains a paginated list of chat history entries")
def step_impl(context):
    """
    Verifies that the response body has the structure of a paginated list.
    """
    response_body = context.response.json()
    assert isinstance(response_body, dict), "Response body is not a dictionary."
    assert "total_items" in response_body, "Response body does not contain 'total_items'."
    assert "total_pages" in response_body, "Response body does not contain 'total_pages'."
    assert "current_page" in response_body, "Response body does not contain 'current_page'."
    assert "page_size" in response_body, "Response body does not contain 'page_size'."
    assert "data" in response_body, "Response body does not contain 'data'."
    assert isinstance(response_body["data"], list), "'data' field is not a list."

    # Optionally, validate the schema of items in the data list
    # try:
    #     PaginatedChatHistoryResponse.model_validate(response_body)
    # except Exception as e:
    #     assert False, f"Response body does not match PaginatedChatHistoryResponse schema: {e}"


@then("the chat history entries are ordered by timestamp descending")
def step_impl(context):
    """
    Verifies that the chat history entries in the data list are ordered by timestamp descending.
    """
    response_body = context.response.json()
    data = response_body.get("data", [])

    if not data:
        # If the list is empty, it's considered sorted
        return

    # Extract timestamps
    timestamps = [item.get("timestamp") for item in data if item.get("timestamp") is not None]

    # Check if the list of timestamps is sorted in descending order
    is_sorted_descending = all(timestamps[i] >= timestamps[i + 1] for i in range(len(timestamps) - 1))

    assert (
        is_sorted_descending
    ), "Chat history entries in the response are not ordered by timestamp descending."


# Scenario: Retrieve chat history when no entries exist for the user


@given("the user has no previous chat history entries")
def step_impl(context):
    """
    Ensures the mock chat repository is empty for the authenticated user.
    """
    assert hasattr(context, "chat_repo"), "MockChatRepository not available in context."
    user_id = context.user_id
    # Assert that there are no chat entries for the current user in the mock repo
    user_chat_history = context.loop.run_until_complete(
        context.chat_repo.get_chat_history_for_user(user_id=user_id)  # Assuming this method exists
    )
    assert len(user_chat_history) == 0, "Expected no chat entries for the user, but found some."


@then("the response contains a paginated list with zero total items")
def step_impl(context):
    """
    Verifies that the response body represents an empty paginated list.
    """
    response_body = context.response.json()
    assert isinstance(response_body, dict), "Response body is not a dictionary."
    assert "total_items" in response_body, "Response body does not contain 'total_items'."
    assert response_body["total_items"] == 0, "Expected total_items to be 0."
    assert "data" in response_body, "Response body does not contain 'data'."
    assert isinstance(response_body["data"], list), "'data' field is not a list."
    assert len(response_body["data"]) == 0, "Expected data list to be empty."
    # Optionally, check total_pages, current_page, page_size if they
    # have specific expected values for an empty list
    # assert response_body.get("total_pages") == 0
    # assert response_body.get("current_page") == 1
    # assert response_body.get("page_size") == 20 # Default size


# Scenario: Retrieve subsequent pages of chat history using pagination parameters


@given("the user has multiple pages of chat history entries")
def step_impl(context):
    """
    Adds multiple mock chat history entries to the mock chat repo for the authenticated user
    to test pagination. Adds more than the default page size (20).
    """
    assert hasattr(context, "chat_repo"), "MockChatRepository not available in context."
    assert hasattr(context, "user_id"), "User ID not available in context."

    # Add a mock selected PDF first
    context.selected_pdf_id = "chat_history_pagination_pdf_1"
    context.selected_pdf_filename = "chat_history_pagination_document.pdf"
    context.loop.run_until_complete(
        add_mock_pdf(
            context,
            context.selected_pdf_id,
            PDFParseStatus.PARSED_SUCCESS,
            is_selected=True,
        )
    )

    # Add mock chat entries
    num_entries = 35  # More than default page size 20
    context.loop.run_until_complete(
        add_mock_chat_history(
            context, context.user_id, context.selected_pdf_id, context.selected_pdf_filename, num_entries
        )
    )
    context.expected_total_chat_entries = num_entries


@when("the user requests the second page of their chat history with a size of 10")
def step_impl(context):
    """
    Sends a GET request to the /chat-history endpoint with pagination parameters for the second page.
    """
    page = 2
    size = 10
    context.response = context.client.get(f"/chat-history?page={page}&size={size}")

    # Store the requested page and size for later assertions
    context.requested_page = page
    context.requested_size = size


@then("the list contains the user's chat history entries for the second page")
def step_impl(context):
    """
    Verifies that the data list in the response contains the expected chat history entries
    for the second page and that pagination details are correct.
    """
    response_body = context.response.json()
    data = response_body.get("data", [])

    # Verify pagination details in the response
    assert response_body.get("total_items") == context.expected_total_chat_entries, "Total items mismatch."
    expected_total_pages = (
        context.expected_total_chat_entries + context.requested_size - 1
    ) // context.requested_size
    assert response_body.get("total_pages") == expected_total_pages, "Total pages mismatch."
    assert response_body.get("current_page") == context.requested_page, "Current page mismatch."
    assert response_body.get("page_size") == context.requested_size, "Page size mismatch."

    # Calculate the expected slice indices based on total entries and pagination params
    skip = (context.requested_page - 1) * context.requested_size
    limit = context.requested_size
    end_index = skip + limit

    # Generate the expected list of entry IDs for the requested page
    # The mock data in environment.py generates IDs from total_entries down to 1
    # and sorts them descending by timestamp (which aligns with descending ID).
    # So, the expected IDs for page 2, size 10 (from 35 total) are 25 down to 16.
    # The IDs are total_entries, total_entries-1, ..., 1.
    # The entries for the first page (skip=0, limit=10) are IDs total_entries
    # down to total_entries - limit + 1.
    # The entries for the second page (skip=10, limit=10) are IDs total_entries -
    # skip down to total_entries - skip - limit + 1.
    # Example: total=35, page=2, size=10. skip=10, limit=10.
    # Expected IDs: 35-10=25 down to 35-10-10+1=16.
    expected_entry_ids_on_page = list(
        range(
            context.expected_total_chat_entries - skip,
            context.expected_total_chat_entries - end_index,  # range is exclusive of stop
            -1,  # Descending order
        )
    )

    # Compare the IDs of the chat entries in the response with the expected IDs
    response_entry_ids = [item.get("id") for item in data]

    assert response_entry_ids == expected_entry_ids_on_page, (
        f"Chat entry IDs on the second page do not match expected IDs.\n"
        f"Expected: {expected_entry_ids_on_page}\n"
        f"Received: {response_entry_ids}"
    )

    # The ordering check is handled by the separate
    # "And the chat history entries are ordered by timestamp descending" step.
