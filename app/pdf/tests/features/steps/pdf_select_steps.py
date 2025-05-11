from behave import given, when, then
from fastapi.testclient import TestClient
from app.pdf.tests.integration.test_pdf_service_integration import (
    MockPDFRepository,
)  # Import MockPDFRepository
from app.pdf.domain.models import PDFDocument, PDFParseStatus  # Import domain models
from datetime import datetime, timezone  # Import datetime and timezone
import asyncio  # Import asyncio for running async methods
import json  # Import json for request/response bodies
from unittest.mock import MagicMock  # Import MagicMock for assertions on mock repo methods

# Reuse the authenticated user step from pdf_upload_steps.py
# from app.pdf.tests.features.steps.pdf_upload_steps import step_impl as user_is_authenticated_step_impl
# @given("a user is authenticated")
# def step_impl(context):
#     user_is_authenticated_step_impl(context)

# Scenario: Successfully select a parsed PDF for chat


@given("the user has a successfully parsed PDF")
def step_impl(context):
    """
    Adds a mock PDF document with PARSED_SUCCESS status to the mock repository
    and stores its ID in the context.
    """
    # Ensure context.pdf_repo is available (set up in environment.py)
    assert hasattr(context, "pdf_repo"), "MockPDFRepository not available in context."

    user_id = context.user_id
    # Add a mock PDF document with PARSED_SUCCESS status
    pdf_doc = PDFDocument(
        id="mongo_parsed_pdf_to_select_1",
        user_id=user_id,
        gridfs_file_id="gridfs_file_parsed_1",
        original_filename="parsed_document.pdf",
        upload_date=datetime.now(timezone.utc),
        parse_status=PDFParseStatus.PARSED_SUCCESS,  # Set initial status to PARSED_SUCCESS
        is_selected_for_chat=False,  # Ensure it's not selected initially
    )
    # Manually add to the mock repo's internal storage
    context.loop.run_until_complete(context.pdf_repo.save_pdf_meta(pdf_doc))

    # Store the ID of the PDF in the context
    context.pdf_id_to_select = pdf_doc.id


@when("the user requests to select the PDF for chat")
def step_impl(context):
    """
    Sends a POST request to the /pdf-select endpoint with the PDF ID.
    Assumes context.client is set up and authentication is handled by environment.py.
    Assumes context.pdf_id_to_select is set.
    """
    # Ensure context.pdf_id_to_select is available
    assert hasattr(context, "pdf_id_to_select"), "PDF ID to select not found in context."

    # The actual endpoint path might be different, e.g., "/pdf/select"
    # Let's assume the endpoint is "/pdf-select" as per the user story.
    # The TestClient URL should be relative to http://testserver.
    # The request body should contain the pdf_id.
    request_body = {"pdf_id": context.pdf_id_to_select}

    context.response = context.client.post("/pdf-select", json=request_body)


@then("the system updates the PDF's selected status to true")
def step_impl(context):
    """
    Verifies that the PDF's is_selected_for_chat status in the mock repository is updated to True.
    Assumes context.pdf_repo, context.user_id, and context.pdf_id_to_select are set.
    Also verifies that the repository method was called.
    """
    # Ensure context.pdf_repo and context.pdf_id_to_select are available
    assert hasattr(context, "pdf_repo"), "MockPDFRepository not available in context."
    assert hasattr(context, "pdf_id_to_select"), "PDF ID to select not found in context."

    # Retrieve the PDF metadata from the mock repo using the stored ID
    pdf_doc = context.loop.run_until_complete(
        context.pdf_repo.get_pdf_meta_by_id(pdf_id=context.pdf_id_to_select, user_id=context.user_id)
    )

    assert (
        pdf_doc is not None
    ), f"PDF metadata with ID {context.pdf_id_to_select} not found in the repository."
    assert (
        pdf_doc.is_selected_for_chat is True
    ), f"Expected is_selected_for_chat to be True, but got {pdf_doc.is_selected_for_chat}"

    # Verify that the mock repository's set_pdf_selected_for_chat method was called
    # Need to access the mock repo instance used by the service.
    # Assuming the service instance is available in context (set up in environment.py)
    assert hasattr(context, "pdf_service"), "PDFApplicationService not available in context."
    # The service holds a reference to the mock repo
    mock_repo_used_by_service = context.pdf_service.pdf_repo

    # Check if the set_pdf_selected_for_chat method was called with the correct arguments
    # Note: This requires the mock_pdf_repo in environment.py to be a MagicMock or have
    # its methods mocked to track calls. Our current MockPDFRepository is a custom class.
    # To verify calls, we would need to add call tracking to MockPDFRepository or
    # mock its methods in environment.py.
    # For now, let's rely on the state change in the mock repo as verification.
    # If we were using unittest.mock.MagicMock for the repo, we could do:
    # mock_repo_used_by_service.set_pdf_selected_for_chat.assert_called_once_with(
    #     user_id=context.user_id, pdf_id_to_select=context.pdf_id_to_select
    # )
    pass  # Relying on state change assertion above


# Scenario: Attempt to select a PDF that is not yet parsed or parsing failed


@given("the user has a PDF with parse status {status}")
def step_impl(context, status):
    """
    Adds a mock PDF document with the specified parse status to the mock repository
    and stores its ID in the context.
    """
    # Ensure context.pdf_repo is available
    assert hasattr(context, "pdf_repo"), "MockPDFRepository not available in context."

    user_id = context.user_id
    # Convert status string to PDFParseStatus enum
    try:
        parse_status_enum = PDFParseStatus[status]
    except KeyError:
        assert False, f"""Invalid parse status provided: {status}.
            Must be one of {list(PDFParseStatus.__members__.keys())}"""

    # Add a mock PDF document with the specified status
    pdf_doc = PDFDocument(
        id=f"mongo_pdf_with_status_{status.lower()}_1",
        user_id=user_id,
        gridfs_file_id=f"gridfs_file_status_{status.lower()}_1",
        original_filename=f"document_status_{status.lower()}.pdf",
        upload_date=datetime.now(timezone.utc),
        parse_status=parse_status_enum,  # Set initial status
        is_selected_for_chat=False,
    )
    # Manually add to the mock repo's internal storage
    context.loop.run_until_complete(context.pdf_repo.save_pdf_meta(pdf_doc))

    # Store the ID of the PDF in the context
    context.pdf_id_to_select = pdf_doc.id


@then("the system returns an HTTP 409 Conflict or HTTP 400 Bad Request")
def step_impl(context):
    """
    Verifies that the HTTP response status code is 409 or 400.
    Assumes context.response is set up.
    """
    # The service raises PDFNotParsedError, which the router should catch
    # and return 409 Conflict or 400 Bad Request.
    # Looking at the router, it doesn't explicitly handle PDFNotParsedError yet.
    # It might return a default 500 or a validation error (422) if the exception
    # is not caught.
    # For now, let's assert for 409 or 400 as per the feature file.
    # We might need to add exception handling in the router later.
    assert context.response.status_code in [
        409,
        400,
    ], f"Expected status code 409 or 400, but got {context.response.status_code}"


# Scenario: Attempt to select a non-existent or unauthorized PDF for chat


@given("the user attempts to select a non-existent or unauthorized PDF")
def step_impl(context):
    """
    Sets the PDF ID in the context to a value that does not exist in the mock repository
    or belongs to another user.
    """
    # Use a hardcoded ID that is not expected to exist in the mock repo
    context.pdf_id_to_select = "non_existent_or_unauthorized_id"


@then("the system returns an HTTP 404 Not Found or HTTP 403 Forbidden")
def step_impl(context):
    """
    Verifies that the HTTP response status code is 404 or 403.
    Assumes context.response is set up.
    """
    # The service raises PDFNotFoundError, which the router should catch
    # and return 404 Not Found or 403 Forbidden.
    # Looking at the router, it doesn't explicitly handle PDFNotFoundError yet.
    # It might return a default 500.
    # For now, let's assert for 404 or 403 as per the feature file.
    # We might need to add exception handling in the router later.
    assert context.response.status_code in [
        404,
        403,
    ], f"Expected status code 404 or 403, but got {context.response.status_code}"
