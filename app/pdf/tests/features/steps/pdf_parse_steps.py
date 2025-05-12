from behave import given, when, then
from fastapi.testclient import TestClient
from app.pdf.tests.integration.test_pdf_service_integration import (
    MockPDFRepository,
    MockDeferParseTask,
)  # Import mocks
from app.pdf.domain.models import PDFDocument, PDFParseStatus  # Import domain models
from datetime import datetime, timezone  # Import datetime and timezone
import asyncio  # Import asyncio for running async methods
import json  # Import json for request/response bodies

# Reuse the authenticated user step from pdf_upload_steps.py
# from app.pdf.tests.features.steps.pdf_upload_steps import step_impl as user_is_authenticated_step_impl
# @given("a user is authenticated")
# def step_impl(context):
#     user_is_authenticated_step_impl(context)

# Scenario: Successfully initiate PDF parsing for an unparsed PDF


@given("the user has an unparsed PDF")
def step_impl(context):
    """
    Adds a mock PDF document with UNPARSED status to the mock repository
    and stores its ID in the context.
    """
    # Ensure context.pdf_repo is available (set up in environment.py)
    assert hasattr(context, "pdf_repo"), "MockPDFRepository not available in context."

    user_id = context.user_id
    # Add a mock PDF document with UNPARSED status
    pdf_doc = PDFDocument(
        id="mongo_unparsed_pdf_1",
        user_id=user_id,
        gridfs_file_id="gridfs_file_unparsed_1",
        original_filename="unparsed_document.pdf",
        upload_date=datetime.now(timezone.utc),
        parse_status=PDFParseStatus.UNPARSED,  # Set initial status to UNPARSED
        is_selected_for_chat=False,
    )
    # Manually add to the mock repo's internal storage
    context.loop.run_until_complete(context.pdf_repo.save_pdf_meta(pdf_doc))

    # Store the ID of the unparsed PDF in the context
    context.unparsed_pdf_id = pdf_doc.id
    context.pdf_id_to_select = pdf_doc.id  # Also store in pdf_id_to_select for reuse in other features


@when("the user requests parsing for the PDF")
def step_impl(context):
    """
    Sends a POST request to the /pdf-parse endpoint with the PDF ID.
    Assumes context.client is set up and authentication is handled by environment.py.
    Assumes context.unparsed_pdf_id is set.
    """
    # Ensure context.unparsed_pdf_id is available
    assert hasattr(context, "unparsed_pdf_id"), "Unparsed PDF ID not found in context."

    # The actual endpoint path might be different, e.g., "/pdf/parse"
    # Let's assume the endpoint is "/pdf-parse" as per the user story.
    # The TestClient URL should be relative to http://testserver.
    # The request body should contain the pdf_id.
    request_body = {"pdf_id": context.unparsed_pdf_id}

    context.response = context.client.post("/pdf-parse", json=request_body)


@then("the system updates the PDF parse status to PARSING")
def step_impl(context):
    """
    Verifies that the PDF's parse status in the mock repository is updated to PARSING.
    Assumes context.pdf_repo, context.user_id, and context.unparsed_pdf_id are set.
    """
    # Ensure context.pdf_repo and context.unparsed_pdf_id are available
    assert hasattr(context, "pdf_repo"), "MockPDFRepository not available in context."
    assert hasattr(context, "unparsed_pdf_id"), "Unparsed PDF ID not found in context."

    # Retrieve the PDF metadata from the mock repo using the stored ID
    pdf_doc = context.loop.run_until_complete(
        context.pdf_repo.get_pdf_meta_by_id(pdf_id=context.unparsed_pdf_id, user_id=context.user_id)
    )

    assert pdf_doc is not None, (
        f"PDF metadata with ID {context.unparsed_pdf_id} not found in the repository."
    )
    assert pdf_doc.parse_status == PDFParseStatus.PARSING, (
        f"Expected parse status PARSING, but got {pdf_doc.parse_status}"
    )


@then("the system enqueues a PDF parsing task")
def step_impl(context):
    """
    Verifies that the mock defer_parse_task callable was called with the correct PDF ID.
    Assumes context.defer_parse_task and context.unparsed_pdf_id are set.
    """
    # Ensure context.defer_parse_task and context.unparsed_pdf_id are available
    assert hasattr(context, "defer_parse_task"), "MockDeferParseTask not available in context."
    assert isinstance(context.defer_parse_task, MockDeferParseTask), (
        "context.defer_parse_task is not a MockDeferParseTask instance."
    )
    assert hasattr(context, "unparsed_pdf_id"), "Unparsed PDF ID not found in context."

    # Check if the mock defer_parse_task was called with the correct PDF ID
    assert context.defer_parse_task.called_with_pdf_id == context.unparsed_pdf_id, (
        f"Expected defer_parse_task to be called with {context.unparsed_pdf_id}, "
        f"but it was called with {context.defer_parse_task.called_with_pdf_id}"
    )


@then("the system returns an HTTP 202 Accepted response")
def step_impl(context):
    """
    Verifies that the HTTP response status code is 202.
    Assumes context.response is set up.
    """
    assert context.response.status_code == 202, (
        f"Expected status code 202, but got {context.response.status_code}"
    )


# Scenario: User observes successful PDF parsing status


@given("the user has a PDF with parse status PARSING")
def step_impl(context):
    """
    Adds a mock PDF document with PARSING status to the mock repository
    and stores its ID in the context.
    """
    # Ensure context.pdf_repo is available
    assert hasattr(context, "pdf_repo"), "MockPDFRepository not available in context."

    user_id = context.user_id
    # Add a mock PDF document with PARSING status
    pdf_doc = PDFDocument(
        id="mongo_parsing_pdf_1",
        user_id=user_id,
        gridfs_file_id="gridfs_file_parsing_1",
        original_filename="parsing_document.pdf",
        upload_date=datetime.now(timezone.utc),
        parse_status=PDFParseStatus.PARSING,  # Set initial status to PARSING
        is_selected_for_chat=False,
    )
    # Manually add to the mock repo's internal storage
    context.loop.run_until_complete(context.pdf_repo.save_pdf_meta(pdf_doc))

    # Store the ID of the PDF in the context
    context.pdf_id_to_observe = pdf_doc.id
    context.pdf_id_to_select = pdf_doc.id  # Also store in pdf_id_to_select for reuse in other features


@given("the background parsing task for the PDF completes successfully")
def step_impl(context):
    """
    Simulates the successful completion of the background parsing task
    by updating the PDF's status in the mock repository to PARSED_SUCCESS.
    Assumes context.pdf_repo and context.pdf_id_to_observe are set.
    """
    # Ensure context.pdf_repo and context.pdf_id_to_observe are available
    assert hasattr(context, "pdf_repo"), "MockPDFRepository not available in context."
    assert hasattr(context, "pdf_id_to_observe"), "PDF ID to observe not found in context."

    # Retrieve the PDF metadata from the mock repo
    pdf_doc = context.loop.run_until_complete(
        context.pdf_repo.get_pdf_meta_by_id(pdf_id=context.pdf_id_to_observe, user_id=context.user_id)
    )

    assert pdf_doc is not None, (
        f"PDF metadata with ID {context.pdf_id_to_observe} not found in the repository."
    )

    # Update the parse status to PARSED_SUCCESS
    pdf_doc.parse_status = PDFParseStatus.PARSED_SUCCESS
    context.loop.run_until_complete(context.pdf_repo.update_pdf_meta(pdf_doc))


@then("the list contains the PDF with parse status PARSED_SUCCESS")
def step_impl(context):
    """
    Verifies that the PDF with the stored ID in the response list has PARSED_SUCCESS status.
    Assumes context.response and context.pdf_id_to_observe are set.
    """
    response_body = context.response.json()
    data = response_body.get("data", [])

    # Find the PDF with the stored ID in the response data
    observed_pdf = next((item for item in data if item.get("id") == context.pdf_id_to_observe), None)

    assert observed_pdf is not None, (
        f"PDF with ID {context.pdf_id_to_observe} not found in the response list."
    )
    assert observed_pdf.get("parse_status") == PDFParseStatus.PARSED_SUCCESS.value, (
        f"Expected parse status PARSED_SUCCESS for PDF {context.pdf_id_to_observe}, "
        f"but got {observed_pdf.get('parse_status')}"
    )


# Scenario: User observes failed PDF parsing status


@given("the background parsing task for the PDF fails")
def step_impl(context):
    """
    Simulates the failure of the background parsing task
    by updating the PDF's status in the mock repository to PARSED_FAILURE
    and adding a mock error message.
    Assumes context.pdf_repo and context.pdf_id_to_observe are set.
    """
    # Ensure context.pdf_repo and context.pdf_id_to_observe are available
    assert hasattr(context, "pdf_repo"), "MockPDFRepository not available in context."
    assert hasattr(context, "pdf_id_to_observe"), "PDF ID to observe not found in context."

    # Retrieve the PDF metadata from the mock repo
    pdf_doc = context.loop.run_until_complete(
        context.pdf_repo.get_pdf_meta_by_id(pdf_id=context.pdf_id_to_observe, user_id=context.user_id)
    )

    assert pdf_doc is not None, (
        f"PDF metadata with ID {context.pdf_id_to_observe} not found in the repository."
    )

    # Update the parse status to PARSED_FAILURE and add an error message
    pdf_doc.parse_status = PDFParseStatus.PARSED_FAILURE
    pdf_doc.parse_error_message = "Mock parsing failed due to an error."
    context.loop.run_until_complete(context.pdf_repo.update_pdf_meta(pdf_doc))


@then("the list contains the PDF with parse status PARSED_FAILURE")
def step_impl(context):
    """
    Verifies that the PDF with the stored ID in the response list has PARSED_FAILURE status.
    Assumes context.response and context.pdf_id_to_observe are set.
    """
    response_body = context.response.json()
    data = response_body.get("data", [])

    # Find the PDF with the stored ID in the response data
    observed_pdf = next((item for item in data if item.get("id") == context.pdf_id_to_observe), None)

    assert observed_pdf is not None, (
        f"PDF with ID {context.pdf_id_to_observe} not found in the response list."
    )
    assert observed_pdf.get("parse_status") == PDFParseStatus.PARSED_FAILURE.value, (
        f"Expected parse status PARSED_FAILURE for PDF {context.pdf_id_to_observe}, "
        f"but got {observed_pdf.get('parse_status')}"
    )


@then("the list contains a parse error message for the PDF")
def step_impl(context):
    """
    Verifies that the PDF with the stored ID in the response list has a non-empty parse error message.
    Assumes context.response and context.pdf_id_to_observe are set.
    """
    response_body = context.response.json()
    data = response_body.get("data", [])

    # Find the PDF with the stored ID in the response data
    observed_pdf = next((item for item in data if item.get("id") == context.pdf_id_to_observe), None)

    assert observed_pdf is not None, (
        f"PDF with ID {context.pdf_id_to_observe} not found in the response list."
    )
    assert "parse_error_message" in observed_pdf, "PDF in response does not contain 'parse_error_message'."
    assert isinstance(observed_pdf.get("parse_error_message"), str), "Parse error message is not a string."
    assert len(observed_pdf.get("parse_error_message")) > 0, "Parse error message is empty."
