from behave import given, when, then
from fastapi.testclient import TestClient
from app.pdf.tests.integration.test_pdf_service_integration import (
    MockPDFRepository,
)  # Import MockPDFRepository
from app.pdf.domain.models import PDFDocument, PDFParseStatus  # Import PDFDocument and PDFParseStatus
from app.pdf.application.schemas import PaginatedPDFListResponse  # Import PaginatedPDFListResponse
from datetime import datetime, timezone, timedelta  # Import datetime, timezone, and timedelta
import asyncio  # Import asyncio for running async methods

# Scenario: Retrieve list of uploaded PDFs (first page)


@given("the user has uploaded at least one PDF")
def step_impl(context):
    """
    Adds mock PDF documents to the mock repository for the authenticated user.
    """
    # Ensure context.pdf_repo is available (set up in environment.py)
    assert hasattr(context, "pdf_repo"), "MockPDFRepository not available in context."

    user_id = context.user_id
    # Add a mock PDF document
    pdf_doc = PDFDocument(
        id="mongo_pdf_1",
        user_id=user_id,
        gridfs_file_id="gridfs_file_1",
        original_filename="document_1.pdf",
        upload_date=datetime.now(timezone.utc),
        parse_status=PDFParseStatus.UNPARSED,
        is_selected_for_chat=False,
    )
    # Manually add to the mock repo's internal storage
    # Need to run this in an async context if the repo method is async.
    # MockPDFRepository save_pdf_meta is async.
    context.loop.run_until_complete(context.pdf_repo.save_pdf_meta(pdf_doc))


@when("the user requests their list of PDFs")
def step_impl(context):
    """
    Sends a GET request to the /pdf-list endpoint.
    Assumes context.client is set up and authentication is handled by environment.py.
    """
    # The actual endpoint path might be different, e.g., "/pdf/list"
    # Let's assume the endpoint is "/pdf-list" as per the user story.
    # The TestClient URL should be relative to http://testserver.
    # We need to simulate the authenticated user. This is handled by the
    # dependency override in environment.py using context.user_id.
    context.response = context.client.get("/pdf-list")


@then("the system returns an HTTP 200 OK response")
def step_impl(context):
    """
    Verifies that the HTTP response status code is 200.
    Assumes context.response is set up.
    """
    assert (
        context.response.status_code == 200
    ), f"Expected status code 200, but got {context.response.status_code}"


@then("the response contains a paginated list of PDFs")
def step_impl(context):
    """
    Verifies that the response body has the structure of a paginated list.
    Assumes context.response is set up.
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
    #     PaginatedPDFListResponse.model_validate(response_body)
    # except Exception as e:
    #     assert False, f"Response body does not match PaginatedPDFListResponse schema: {e}"


@then("the list contains the user's uploaded PDFs for the first page")
def step_impl(context):
    """
    Verifies that the data list in the response contains the expected PDFs for the first page.
    Assumes context.response, context.user_id, and context.pdf_repo are set up.
    """
    response_body = context.response.json()
    data = response_body.get("data", [])
    assert len(data) > 0, "The data list is empty, but expected PDFs."

    # Retrieve the expected PDFs from the mock repo for the first page (default pagination)
    expected_pdfs = context.loop.run_until_complete(
        context.pdf_repo.get_all_pdf_meta_for_user(
            user_id=context.user_id, skip=0, limit=100
        )  # Default limit in service is 100
    )

    assert len(data) == len(expected_pdfs), "Number of PDFs in response does not match expected."

    # Compare the IDs of the PDFs in the response with the expected IDs
    response_pdf_ids = [item.get("id") for item in data]
    expected_pdf_ids = [doc.id for doc in expected_pdfs]

    assert sorted(response_pdf_ids) == sorted(
        expected_pdf_ids
    ), "PDF IDs in response do not match expected IDs."

    # Further assertions can be added to check other fields like filename, upload_date, parse_status


@then("the PDFs in the list are ordered by upload date descending")
def step_impl(context):
    """
    Verifies that the PDFs in the data list are ordered by upload date descending.
    Assumes context.response is set up.
    """
    response_body = context.response.json()
    data = response_body.get("data", [])

    if not data:
        # If the list is empty, it's considered sorted
        return

    # Extract upload dates (assuming they are in ISO format strings or similar)
    # Need to parse dates for comparison
    upload_dates = [
        datetime.fromisoformat(item.get("upload_date").replace("Z", "+00:00"))
        for item in data
        if item.get("upload_date")
    ]

    # Check if the list of dates is sorted in descending order
    # A list is sorted descending if each element is greater than or equal to the next element
    is_sorted_descending = all(upload_dates[i] >= upload_dates[i + 1] for i in range(len(upload_dates) - 1))

    assert is_sorted_descending, "PDFs in the response are not ordered by upload date descending."


# Scenario: Retrieve list when no PDFs uploaded by user


@given("the user has not uploaded any PDFs")
def step_impl(context):
    """
    Ensures the mock repository is empty for the authenticated user.
    This is primarily handled by the before_scenario hook, but we can assert it.
    """
    # Ensure context.pdf_repo is available
    assert hasattr(context, "pdf_repo"), "MockPDFRepository not available in context."

    # Assert that there are no PDFs for the current user in the mock repo
    user_pdfs = context.loop.run_until_complete(
        context.pdf_repo.get_all_pdf_meta_for_user(user_id=context.user_id)
    )
    assert len(user_pdfs) == 0, "Expected no PDFs for the user, but found some."


@then("the response contains a paginated list with zero total items")
def step_impl(context):
    """
    Verifies that the response body represents an empty paginated list.
    Assumes context.response is set up.
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
    # assert response_body.get("page_size") == 10


# Scenario: Retrieve subsequent pages of PDFs using pagination parameters


@given("the user has uploaded multiple PDFs")
def step_impl(context):
    """
    Adds multiple mock PDF documents to the mock repository for the authenticated user
    to test pagination. Adds more than the default page size.
    """
    # Ensure context.pdf_repo is available
    assert hasattr(context, "pdf_repo"), "MockPDFRepository not available in context."

    user_id = context.user_id
    num_pdfs_to_add = 15  # Add more than the default page size (10)

    # Add mock PDF documents with distinct upload dates for ordering
    # Create dates in descending order to easily check sorting later
    base_date = datetime.now(timezone.utc)
    pdfs_to_save = []
    for i in range(num_pdfs_to_add):
        # Create slightly different dates for each PDF
        upload_date = base_date - timedelta(minutes=i)  # Corrected timedelta usage
        pdf_doc = PDFDocument(
            id=f"mongo_pdf_{i + 1}",
            user_id=user_id,
            gridfs_file_id=f"gridfs_file_{i + 1}",
            original_filename=f"document_{i + 1}.pdf",
            upload_date=upload_date,
            parse_status=PDFParseStatus.UNPARSED,
            is_selected_for_chat=False,
        )
        pdfs_to_save.append(pdf_doc)

    # Save all mock PDFs
    for pdf_doc in pdfs_to_save:
        context.loop.run_until_complete(context.pdf_repo.save_pdf_meta(pdf_doc))

    # Store the expected total number of PDFs for later verification
    context.expected_total_pdfs = num_pdfs_to_add


@when("the user requests the second page of their PDFs with a size of 10")
def step_impl(context):
    """
    Sends a GET request to the /pdf-list endpoint with pagination parameters for the second page.
    Assumes context.client is set up and authentication is handled by environment.py.
    """
    # Request the second page with a size of 10
    page = 2
    size = 10
    context.response = context.client.get(f"/pdf-list?page={page}&size={size}")

    # Store the requested page and size for later assertions
    context.requested_page = page
    context.requested_size = size


@then("the list contains the user's uploaded PDFs for the second page")
def step_impl(context):
    """
    Verifies that the data list in the response contains the expected PDFs for the second page
    and that pagination details are correct.
    Assumes context.response, context.user_id, context.pdf_repo, context.requested_page,
    context.requested_size, and context.expected_total_pdfs are set up.
    """
    response_body = context.response.json()
    data = response_body.get("data", [])

    # Verify pagination details in the response
    assert response_body.get("total_items") == context.expected_total_pdfs, "Total items mismatch."
    expected_total_pages = (
        context.expected_total_pdfs + context.requested_size - 1
    ) // context.requested_size
    assert response_body.get("total_pages") == expected_total_pages, "Total pages mismatch."
    assert response_body.get("current_page") == context.requested_page, "Current page mismatch."
    assert response_body.get("page_size") == context.requested_size, "Page size mismatch."

    # Calculate the expected slice of PDFs for the second page
    skip = (context.requested_page - 1) * context.requested_size
    limit = context.requested_size

    # Retrieve ALL expected PDFs from the mock repo (to slice them correctly)
    all_expected_pdfs = context.loop.run_until_complete(
        context.pdf_repo.get_all_pdf_meta_for_user(
            user_id=context.user_id, skip=0, limit=context.expected_total_pdfs
        )
    )

    # The mock repo's get_all_pdf_meta_for_user already handles pagination,
    # but let's get all and slice here to be explicit about expected content.
    # Note: The mock repo's get_all_pdf_meta_for_user also returns in upload_date descending order.
    expected_pdfs_on_page = all_expected_pdfs[skip : skip + limit]

    assert len(data) == len(expected_pdfs_on_page), "Number of PDFs on the second page mismatch."

    # Compare the IDs of the PDFs in the response with the expected IDs for the second page
    response_pdf_ids = [item.get("id") for item in data]
    expected_pdf_ids_on_page = [doc.id for doc in expected_pdfs_on_page]

    assert (
        response_pdf_ids == expected_pdf_ids_on_page
    ), "PDF IDs on the second page do not match expected IDs."

    # The ordering check is handled by the separate
    # "And the PDFs in the list are ordered by upload date descending" step.
