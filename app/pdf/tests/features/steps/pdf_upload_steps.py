from behave import given, when, then
from fastapi.testclient import TestClient
from fastapi import UploadFile  # Import UploadFile
from unittest.mock import MagicMock
from io import BytesIO
from app.pdf.domain.models import PDFParseStatus
from app.pdf.application.schemas import PDFMetadataResponse
import json  # Import json to parse response body

# Scenario: Successful PDF upload with valid PDF type


@given("a user is authenticated")
def step_impl(context):
    """
    Simulates an authenticated user by setting a user ID in the context.
    In a real application, this would involve setting headers or session data.
    """
    # Use a dummy user ID for testing purposes
    context.user_id = 123


@given("the user has a valid PDF file")
def step_impl(context):
    """
    Stores details about a valid PDF file in the context.
    """
    context.file_content = b"%PDF-1.4\n...\n%%EOF"  # Minimal valid PDF content
    context.file_name = "valid_document.pdf"
    context.content_type = "application/pdf"


@when("the user attempts to upload the {file_type} file to /pdf-upload")
def step_impl(context, file_type):
    """
    Sends a file upload request to the /pdf-upload endpoint.
    Assumes context.client and context.upload_file are set up.
    """
    # file_type argument is captured from the step text but not used in this step's logic.
    # The TestClient expects files in a specific format for upload
    # The TestClient expects files in a specific format for upload.
    # Pass the raw bytes directly.
    files = {"file": (context.file_name, context.file_content, context.content_type)}

    # Make the POST request using the test client.
    # The URL should be relative to the test client's base URL (http://testserver).
    # The feature file says "/pdf-upload". Let's use that.
    # We need to simulate the authenticated user. This is typically done by
    # overriding a dependency in the FastAPI app for testing.
    # Let's assume the environment.py will handle this dependency override
    # to return context.user_id when the current user dependency is called.
    # So, the request itself doesn't need to explicitly pass the user_id in headers
    # if the dependency override is set up correctly.
    context.response = context.client.post("/pdf-upload", files=files)


@then("the system stores the file in GridFS")
def step_impl(context):
    """
    Verifies that the PDF binary content was stored in the mock repository.
    Assumes context.pdf_repo and context.file_content are set up.
    """
    # Check if the PDF binary was saved in the mock repository
    # The mock repository stores binaries by gridfs_id, which is generated during save.
    # We need to find the PDF metadata first to get the gridfs_file_id.
    # Assuming the response body contains the new PDF's ID.
    response_body = context.response.json()
    pdf_id = response_body.get("id")
    assert pdf_id is not None, "Response body does not contain the new PDF's ID."

    # Retrieve the PDF metadata from the mock repo using the ID
    # Need to run this in an async context if the repo method is async.
    # Assuming environment.py sets up an async loop and makes it available in context.
    pdf_doc = context.loop.run_until_complete(
        context.pdf_repo.get_pdf_meta_by_id(pdf_id=pdf_id, user_id=context.user_id)
    )

    assert pdf_doc is not None, f"PDF metadata with ID {pdf_id} not found in the repository."
    assert pdf_doc.gridfs_file_id is not None, "PDF metadata does not contain gridfs_file_id."

    # Retrieve the binary content using the gridfs_file_id
    binary_content = context.loop.run_until_complete(
        context.pdf_repo.get_pdf_binary_content(gridfs_file_id=pdf_doc.gridfs_file_id)
    )

    assert binary_content is not None, (
        f"PDF binary content with GridFS ID {pdf_doc.gridfs_file_id} not found."
    )
    assert binary_content == context.file_content, (
        "Stored PDF binary content does not match the uploaded content."
    )


@then("the system stores the metadata in the database")
def step_impl(context):
    """
    Verifies that the PDF metadata was stored in the mock repository.
    Assumes context.pdf_repo and context.user_id are set up, and the response
    contains the new PDF's ID.
    """
    # Check if the PDF metadata was saved in the mock repository
    # Assuming the response body contains the new PDF's ID.
    response_body = context.response.json()
    pdf_id = response_body.get("id")
    assert pdf_id is not None, "Response body does not contain the new PDF's ID."

    # Retrieve the PDF metadata from the mock repo using the ID
    # Need to run this in an async context if the repo method is async.
    # Assuming environment.py sets up an async loop and makes it available in context.
    pdf_doc = context.loop.run_until_complete(
        context.pdf_repo.get_pdf_meta_by_id(pdf_id=pdf_id, user_id=context.user_id)
    )

    assert pdf_doc is not None, f"PDF metadata with ID {pdf_id} not found in the repository."
    assert pdf_doc.user_id == context.user_id, "Stored PDF metadata has incorrect user ID."
    assert pdf_doc.original_filename == context.file_name, "Stored PDF metadata has incorrect filename."
    assert pdf_doc.parse_status == PDFParseStatus.UNPARSED, (
        "Stored PDF metadata has incorrect initial parse status."
    )
    # We can add more assertions here for other fields like upload_date if needed.


@then("the system returns an HTTP 201 Created response with the new PDF's ID")
def step_impl(context):
    """
    Verifies that the HTTP response status code is 201 and the response body
    contains the ID of the newly created PDF.
    Assumes context.response is set up.
    """
    assert context.response.status_code == 201, (
        f"Expected status code 201, but got {context.response.status_code}"
    )

    # Check the response body
    response_body = context.response.json()
    assert "id" in response_body, "Response body does not contain 'id'."
    assert isinstance(response_body["id"], str) and len(response_body["id"]) > 0, (
        "PDF ID in response is invalid."
    )
    # Optionally, check other fields in the response body if the schema is known
    # e.g., assert "original_filename" in response_body
    # assert response_body.get("original_filename") == context.file_name


# Scenario: Attempt to upload a non-PDF file type


@given("the user has a non-PDF file")
def step_impl(context):
    """
    Stores details about a non-PDF file in the context.
    """
    context.file_content = b"This is not a PDF file."  # Non-PDF content
    context.file_name = "invalid_document.txt"
    context.content_type = "text/plain"  # Non-PDF content type


@then("the system rejects the upload")
def step_impl(context):
    """
    Verifies that no PDF binary or metadata was stored in the mock repository.
    Assumes context.pdf_repo is set up.
    """
    # Check that no PDF binary was saved
    assert len(context.pdf_repo._pdf_binaries) == 0, "PDF binary was unexpectedly stored."

    # Check that no PDF metadata was saved
    assert len(context.pdf_repo._pdfs) == 0, "PDF metadata was unexpectedly stored."


@then("the system returns an HTTP 415 Unsupported Media Type or HTTP 400 Bad Request")
def step_impl(context):
    """
    Verifies that the HTTP response status code is 415 or 400.
    Assumes context.response is set up.
    """
    # The router is implemented to return 415 for invalid file types
    assert context.response.status_code in [
        415,
        400,
    ], f"Expected status code 415 or 400, but got {context.response.status_code}"


# Scenario: Attempt to upload PDF without authentication


@given("a user is not authenticated")
def step_impl(context):
    """
    Simulates a non-authenticated user by ensuring user_id is None in the context.
    The environment setup handles the dependency override based on context.user_id.
    """
    context.user_id = None  # Explicitly set user_id to None


@then("the system returns an HTTP 401 Unauthorized response")
def step_impl(context):
    """
    Verifies that the HTTP response status code is 401.
    Assumes context.response is set up.
    """
    assert context.response.status_code == 401, (
        f"Expected status code 401, but got {context.response.status_code}"
    )
