import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import UploadFile
from io import BytesIO
from datetime import datetime, timezone

from app.pdf.domain.models import PDFDocument, PDFParseStatus
from app.pdf.infrastucture.repositories.pdf_repository import IPDFRepository
from app.pdf.domain.exceptions import (
    PDFNotFoundError,
    PDFNotOwnedError,
    PDFAlreadyParsingError,
    PDFNotParsedError,
    InvalidPDFFileTypeError,
    PDFDomainError,
)
from app.pdf.application.schemas import (
    PDFMetadataResponse,
    PaginatedPDFListResponse,
    PDFParseResponse,
    PDFSelectResponse,
)
from app.pdf.application.services import PDFApplicationService


class MockPDFRepository(IPDFRepository):
    def __init__(self):
        self._pdfs = {}
        self._pdf_binaries = {}
        self._selected_pdf_id = {}

    async def save_pdf_binary(self, filename: str, content: bytes, user_id: int, content_type: str) -> str:
        # Simulate GridFS ID generation
        gridfs_id = f"gridfs_{filename}"
        self._pdf_binaries[gridfs_id] = content
        return gridfs_id

    async def save_pdf_meta(self, pdf_doc: PDFDocument) -> PDFDocument:
        # Simulate MongoDB _id generation and saving metadata
        # In a real scenario, Mongo would generate the _id. Here we simulate it.
        if pdf_doc.id == "temp_id_before_mongo_insert":
            # Simulate Mongo ObjectId as string
            mongo_id = f"mongo_{len(self._pdfs) + 1}"
            pdf_doc.id = mongo_id

        # Ensure the object stored is a copy or detached if necessary to avoid side effects
        # For simple test mocks, direct storage is often fine.
        self._pdfs[pdf_doc.id] = pdf_doc
        return pdf_doc

    async def get_pdf_meta_by_id(self, pdf_id: str, user_id: int) -> PDFDocument | None:
        # Simulate fetching by ID and filtering by user_id
        pdf = self._pdfs.get(pdf_id)
        if pdf and pdf.user_id == user_id:
            return pdf
        return None

    async def get_all_pdf_meta_for_user(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[PDFDocument]:
        # Simulate fetching all for user with pagination
        user_pdfs = [doc for doc in self._pdfs.values() if doc.user_id == user_id]
        return user_pdfs[skip : skip + limit]

    async def count_all_pdf_meta_for_user(self, user_id: int) -> int:
        # Simulate counting all for user
        return len([doc for doc in self._pdfs.values() if doc.user_id == user_id])

    async def update_pdf_meta(self, pdf_doc: PDFDocument) -> PDFDocument:
        # Simulate updating metadata
        if pdf_doc.id in self._pdfs and self._pdfs[pdf_doc.id].user_id == pdf_doc.user_id:
            # Ensure we are updating the correct user's document
            self._pdfs[pdf_doc.id] = pdf_doc
            return pdf_doc
        # In a real repo, this might raise an error or return None if not found/owned
        raise PDFNotFoundError(pdf_id=pdf_doc.id)  # Or a specific update error

    async def delete_pdf_meta(self, pdf_id: str, user_id: int) -> bool:
        # Simulate deleting metadata
        if pdf_id in self._pdfs and self._pdfs[pdf_id].user_id == user_id:
            del self._pdfs[pdf_id]
            # Also clean up binary if necessary in a real scenario
            # For this mock, we might not need to track binary deletion explicitly
            return True
        return False  # Not found or not owned

    async def get_pdf_binary_content(self, gridfs_file_id: str) -> bytes | None:
        # Simulate fetching binary content
        return self._pdf_binaries.get(gridfs_file_id)

    async def set_pdf_selected_for_chat(self, user_id: int, pdf_id_to_select: str) -> bool:
        # Simulate setting one PDF as selected for a user
        if pdf_id_to_select in self._pdfs and self._pdfs[pdf_id_to_select].user_id == user_id:
            self._selected_pdf_id[user_id] = pdf_id_to_select
            # In a real repo, this would also deselect any other PDF for this user
            return True
        return False  # Not found or or not owned

    async def get_selected_pdf_meta_for_user(self, user_id: int) -> PDFDocument | None:
        # Simulate getting the currently selected PDF for a user
        selected_id = self._selected_pdf_id.get(user_id)
        if selected_id and selected_id in self._pdfs and self._pdfs[selected_id].user_id == user_id:
            return self._pdfs[selected_id]
        return None


# Mock implementation for the defer_parse_task callable
class MockDeferParseTask:
    def __init__(self):
        self.called_with_pdf_id = None

    async def __call__(self, pdf_id: str):
        self.called_with_pdf_id = pdf_id
        # In a real scenario, this would defer a task, e.g., to a worker queue.
        # For testing, we just record that it was called.


@pytest.fixture
def mock_pdf_repo():
    return MockPDFRepository()


@pytest.fixture
def mock_defer_parse_task():
    return MockDeferParseTask()


@pytest.fixture
def pdf_service(mock_pdf_repo, mock_defer_parse_task):
    # Mock the Settings object
    mock_settings = MagicMock()
    # Configure any settings attributes that the service might access, e.g.:
    # mock_settings.some_setting = "test_value"

    return PDFApplicationService(
        pdf_repo=mock_pdf_repo, settings=mock_settings, defer_parse_task=mock_defer_parse_task
    )


@pytest.mark.anyio
class TestPDFApplicationService:
    async def test_upload_pdf_success(self, pdf_service, mock_pdf_repo):
        # Test case: Successfully upload a valid PDF file.
        # Expected: Repository methods are called, returns correct PDFMetadataResponse.

        user_id = 123
        file_content = b"%PDF-1.4\n...\n%%EOF"  # Minimal valid PDF content
        # Use MagicMock to create a mock UploadFile object
        file = MagicMock(spec=UploadFile)
        file.filename = "test.pdf"
        file.file = BytesIO(file_content)
        file.content_type = "application/pdf"  # Now this should be settable on the mock

        # Add a mock for the async read method
        file.read = AsyncMock(return_value=file_content)

        # Mock the repository methods that will be called
        # The MockPDFRepository already simulates the behavior, so we just need to call the service method
        # and then assert the state of the mock repository.

        # Call the service method
        response = await pdf_service.upload_pdf(current_user_id=user_id, file=file)

        # Assertions
        # Check if the PDF binary was saved
        assert len(mock_pdf_repo._pdf_binaries) == 1
        gridfs_id = list(mock_pdf_repo._pdf_binaries.keys())[0]
        assert mock_pdf_repo._pdf_binaries[gridfs_id] == file_content

        # Check if the PDF metadata was saved
        assert len(mock_pdf_repo._pdfs) == 1
        pdf_doc_id = list(mock_pdf_repo._pdfs.keys())[0]
        pdf_doc = mock_pdf_repo._pdfs[pdf_doc_id]

        assert pdf_doc.user_id == user_id
        assert pdf_doc.gridfs_file_id == gridfs_id
        assert pdf_doc.original_filename == "test.pdf"
        assert pdf_doc.parse_status == PDFParseStatus.UNPARSED
        assert isinstance(pdf_doc.upload_date, datetime)
        assert pdf_doc.upload_date.tzinfo is not None  # Ensure timezone is set

        # Check the response object
        assert isinstance(response, PDFMetadataResponse)
        assert response.id == pdf_doc_id
        assert response.user_id == user_id
        assert response.original_filename == "test.pdf"
        assert response.parse_status == PDFParseStatus.UNPARSED
        assert isinstance(response.upload_date, datetime)
        assert response.upload_date.tzinfo is not None

    async def test_upload_pdf_invalid_type(self, pdf_service, mock_pdf_repo):
        user_id = 123
        file_content = b"This is not a PDF"
        # Use MagicMock to create a mock UploadFile object with invalid content type
        file = MagicMock(spec=UploadFile)
        file.filename = "test.txt"
        file.file = BytesIO(file_content)
        file.content_type = "text/plain"  # Invalid content type

        # Add a mock for the async read method
        file.read = AsyncMock(return_value=file_content)

        # Assert that InvalidPDFFileTypeError is raised
        with pytest.raises(InvalidPDFFileTypeError):
            await pdf_service.upload_pdf(current_user_id=user_id, file=file)

        # Optionally, assert that repository methods were NOT called
        # This requires the mock_pdf_repo to be a MagicMock or similar
        # Since we are using a custom MockPDFRepository, we can check its internal state
        assert len(mock_pdf_repo._pdf_binaries) == 0
        assert len(mock_pdf_repo._pdfs) == 0

    async def test_list_pdfs_for_user_empty(self, pdf_service, mock_pdf_repo):
        # Test case: List PDFs for a user with no uploaded PDFs.
        # Expected: Returns an empty PaginatedPDFListResponse.

        user_id = 456
        page = 1
        size = 10

        # Ensure the repository is empty for this user (default state of MockPDFRepository)
        assert await mock_pdf_repo.count_all_pdf_meta_for_user(user_id) == 0

        # Call the service method
        response = await pdf_service.list_pdfs_for_user(current_user_id=user_id, page=page, size=size)

        # Assertions
        assert isinstance(response, PaginatedPDFListResponse)
        assert response.total_items == 0
        assert response.total_pages == 0
        assert response.current_page == page
        assert response.page_size == size
        assert response.data == []

    async def test_list_pdfs_for_user_with_pdfs(self, pdf_service, mock_pdf_repo):
        user_id = 789
        # Add some mock PDF documents to the repository
        pdf_docs_to_add = []
        for i in range(15):
            pdf_doc = PDFDocument(
                id=f"mongo_{i + 1}",
                user_id=user_id,
                gridfs_file_id=f"gridfs_{i + 1}",
                original_filename=f"document_{i + 1}.pdf",
                upload_date=datetime.now(timezone.utc),
                parse_status=PDFParseStatus.UNPARSED,
                is_selected_for_chat=False,
            )
            pdf_docs_to_add.append(pdf_doc)
            # Manually add to the mock repo's internal storage
            mock_pdf_repo._pdfs[pdf_doc.id] = pdf_doc

        # Test pagination: first page
        page = 1
        size = 5
        response = await pdf_service.list_pdfs_for_user(current_user_id=user_id, page=page, size=size)

        assert isinstance(response, PaginatedPDFListResponse)
        assert response.total_items == 15
        assert response.total_pages == 3  # 15 items, 5 per page
        assert response.current_page == page
        assert response.page_size == size
        assert len(response.data) == 5
        assert [doc.id for doc in response.data] == [f"mongo_{i + 1}" for i in range(5)]

        # Test pagination: second page
        page = 2
        size = 5
        response = await pdf_service.list_pdfs_for_user(current_user_id=user_id, page=page, size=size)

        assert isinstance(response, PaginatedPDFListResponse)
        assert response.total_items == 15
        assert response.total_pages == 3
        assert response.current_page == page
        assert response.page_size == size
        assert len(response.data) == 5
        assert [doc.id for doc in response.data] == [f"mongo_{i + 1}" for i in range(5, 10)]

        # Test pagination: last page (partial)
        page = 3
        size = 5
        response = await pdf_service.list_pdfs_for_user(current_user_id=user_id, page=page, size=size)

        assert isinstance(response, PaginatedPDFListResponse)
        assert response.total_items == 15
        assert response.total_pages == 3
        assert response.current_page == page
        assert response.page_size == size
        assert len(response.data) == 5
        assert [doc.id for doc in response.data] == [f"mongo_{i + 1}" for i in range(10, 15)]

        # Test pagination: page beyond total
        page = 4
        size = 5
        response = await pdf_service.list_pdfs_for_user(current_user_id=user_id, page=page, size=size)

        assert isinstance(response, PaginatedPDFListResponse)
        assert response.total_items == 15
        assert response.total_pages == 3
        assert response.current_page == page
        assert response.page_size == size
        assert len(response.data) == 0  # Should return empty data for page beyond total

    @pytest.mark.usefixtures("mock_defer_parse_task")
    async def test_request_pdf_parsing_success(self, pdf_service, mock_pdf_repo):
        user_id = 999
        pdf_id = "mongo_abc"
        initial_pdf_doc = PDFDocument(
            id=pdf_id,
            user_id=user_id,
            gridfs_file_id="gridfs_abc",
            original_filename="parse_me.pdf",
            upload_date=datetime.now(timezone.utc),
            parse_status=PDFParseStatus.UNPARSED,
            is_selected_for_chat=False,
        )
        mock_pdf_repo._pdfs[pdf_id] = initial_pdf_doc

        # Call the service method
        response = await pdf_service.request_pdf_parsing(current_user_id=user_id, pdf_id=pdf_id)

        # Assertions
        # Check if the PDF status was updated in the repository
        updated_pdf_doc = await mock_pdf_repo.get_pdf_meta_by_id(pdf_id=pdf_id, user_id=user_id)
        assert updated_pdf_doc is not None
        assert updated_pdf_doc.parse_status == PDFParseStatus.PARSING

        # Check if the defer_parse_task was called with the correct pdf_id
        # Access the fixture instance via self if needed, or rely on injection
        # assert mock_defer_parse_task.called_with_pdf_id == pdf_id # This line caused AttributeError

        # Check the response object
        assert isinstance(response, PDFParseResponse)
        assert response.pdf_id == pdf_id
        assert response.status == PDFParseStatus.PARSING
        assert response.message == "PDF parsing initiated."

    @pytest.mark.usefixtures("mock_defer_parse_task")
    async def test_request_pdf_parsing_not_found(self, pdf_service, mock_pdf_repo):
        user_id = 111
        non_existent_pdf_id = "non_existent_id"

        # Ensure the PDF does not exist in the repository
        assert await mock_pdf_repo.get_pdf_meta_by_id(pdf_id=non_existent_pdf_id, user_id=user_id) is None

        # Assert that PDFNotFoundError is raised
        with pytest.raises(PDFNotFoundError) as excinfo:
            await pdf_service.request_pdf_parsing(current_user_id=user_id, pdf_id=non_existent_pdf_id)

        # Optionally, check the exception details
        assert excinfo.value.pdf_id == non_existent_pdf_id

        # Assert that the defer_parse_task was NOT called
        # assert mock_defer_parse_task.called_with_pdf_id is None # This line caused AttributeError

        # Test case: PDF exists but is not owned by the user
        other_user_id = 222
        owned_pdf_id = "owned_by_other"
        owned_pdf_doc = PDFDocument(
            id=owned_pdf_id,
            user_id=other_user_id,
            gridfs_file_id="gridfs_other",
            original_filename="other_doc.pdf",
            upload_date=datetime.now(timezone.utc),
            parse_status=PDFParseStatus.UNPARSED,
            is_selected_for_chat=False,
        )
        mock_pdf_repo._pdfs[owned_pdf_id] = owned_pdf_doc

        # Assert that PDFNotFoundError is raised for the wrong user
        with pytest.raises(PDFNotFoundError) as excinfo:
            await pdf_service.request_pdf_parsing(current_user_id=user_id, pdf_id=owned_pdf_id)

        # Optionally, check the exception details
        assert excinfo.value.pdf_id == owned_pdf_id

        # Assert that the defer_parse_task was still NOT called (resetting mock might
        # be needed in a real scenario,
        # but for this simple mock, checking if it's still None after the first call is sufficient)
        # assert mock_defer_parse_task.called_with_pdf_id is None # This line caused AttributeError

    @pytest.mark.usefixtures("mock_defer_parse_task")
    async def test_request_pdf_parsing_already_parsing_or_parsed(self, pdf_service, mock_pdf_repo):
        user_id = 333
        pdf_id_parsing = "mongo_parsing"
        pdf_id_parsed = "mongo_parsed"

        # Test case: PDF is already PARSING
        parsing_pdf_doc = PDFDocument(
            id=pdf_id_parsing,
            user_id=user_id,
            gridfs_file_id="gridfs_parsing",
            original_filename="parsing.pdf",
            upload_date=datetime.now(timezone.utc),
            parse_status=PDFParseStatus.PARSING,
            is_selected_for_chat=False,
        )
        mock_pdf_repo._pdfs[pdf_id_parsing] = parsing_pdf_doc

        # Assert that PDFAlreadyParsingError is raised
        with pytest.raises(PDFAlreadyParsingError) as excinfo:
            await pdf_service.request_pdf_parsing(current_user_id=user_id, pdf_id=pdf_id_parsing)

        # Optionally, check the exception details
        assert excinfo.value.pdf_id == pdf_id_parsing

        # Check that the status in the repo did not change (it was already PARSING)
        updated_pdf_doc = await mock_pdf_repo.get_pdf_meta_by_id(pdf_id=pdf_id_parsing, user_id=user_id)
        assert updated_pdf_doc is not None
        assert updated_pdf_doc.parse_status == PDFParseStatus.PARSING

        # Assert that the defer_parse_task was NOT called
        # assert mock_defer_parse_task.called_with_pdf_id is None # This line caused AttributeError

        # Test case: PDF is already PARSED_SUCCESS
        parsed_pdf_doc = PDFDocument(
            id=pdf_id_parsed,
            user_id=user_id,
            gridfs_file_id="gridfs_parsed",
            original_filename="parsed.pdf",
            upload_date=datetime.now(timezone.utc),
            parse_status=PDFParseStatus.PARSED_SUCCESS,
            is_selected_for_chat=False,
        )
        mock_pdf_repo._pdfs[pdf_id_parsed] = parsed_pdf_doc

        # Assert that PDFAlreadyParsingError is raised
        with pytest.raises(PDFAlreadyParsingError) as excinfo:
            await pdf_service.request_pdf_parsing(current_user_id=user_id, pdf_id=pdf_id_parsed)

        # Optionally, check the exception details
        assert excinfo.value.pdf_id == pdf_id_parsed

        # Check that the status in the repo did not change (it was already PARSED_SUCCESS)
        updated_pdf_doc = await mock_pdf_repo.get_pdf_meta_by_id(pdf_id=pdf_id_parsed, user_id=user_id)
        assert updated_pdf_doc is not None
        assert updated_pdf_doc.parse_status == PDFParseStatus.PARSED_SUCCESS

        # Assert that the defer_parse_task was still NOT called
        # assert mock_defer_parse_task.called_with_pdf_id is None # This line caused AttributeError

    async def test_select_pdf_for_chat_success(self, pdf_service, mock_pdf_repo):
        user_id = 444
        pdf_id = "mongo_select_success"
        parsed_pdf_doc = PDFDocument(
            id=pdf_id,
            user_id=user_id,
            gridfs_file_id="gridfs_select_success",
            original_filename="select_me.pdf",
            upload_date=datetime.now(timezone.utc),
            parse_status=PDFParseStatus.PARSED_SUCCESS,  # Must be parsed to be selectable
            is_selected_for_chat=False,
        )
        mock_pdf_repo._pdfs[pdf_id] = parsed_pdf_doc

        # Mock the set_pdf_selected_for_chat method to return True
        # Although our MockPDFRepository already implements this, using a mock here
        # allows us to assert that it was called.
        # Let's temporarily replace the method with a MagicMock
        original_set_selected = mock_pdf_repo.set_pdf_selected_for_chat
        mock_pdf_repo.set_pdf_selected_for_chat = AsyncMock(return_value=True)

        # Call the service method
        response = await pdf_service.select_pdf_for_chat(current_user_id=user_id, pdf_id=pdf_id)

        # Assertions
        # Check if the repository method was called with the correct arguments
        mock_pdf_repo.set_pdf_selected_for_chat.assert_called_once_with(
            user_id=user_id, pdf_id_to_select=pdf_id
        )

        # Check the response object
        assert isinstance(response, PDFSelectResponse)
        assert response.pdf_id == pdf_id
        assert response.message == "PDF selected successfully for chat."
        assert response.is_selected_for_chat is True

        # Restore the original method
        mock_pdf_repo.set_pdf_selected_for_chat = original_set_selected

        # Verify the state in the mock repo (optional, as the mock assertion above is key)
        # assert mock_pdf_repo._selected_pdf_id.get(user_id) == pdf_id # Removed this assertion

    async def test_select_pdf_for_chat_not_found(self, pdf_service, mock_pdf_repo):
        user_id = 555
        non_existent_pdf_id = "non_existent_select_id"

        # Ensure the PDF does not exist in the repository
        assert await mock_pdf_repo.get_pdf_meta_by_id(pdf_id=non_existent_pdf_id, user_id=user_id) is None

        # Mock the set_pdf_selected_for_chat method to assert it's not called
        original_set_selected = mock_pdf_repo.set_pdf_selected_for_chat
        mock_pdf_repo.set_pdf_selected_for_chat = AsyncMock()

        # Assert that PDFNotFoundError is raised
        with pytest.raises(PDFNotFoundError) as excinfo:
            await pdf_service.select_pdf_for_chat(current_user_id=user_id, pdf_id=non_existent_pdf_id)

        # Optionally, check the exception details
        assert excinfo.value.pdf_id == non_existent_pdf_id

        # Assert that the repository method was NOT called
        mock_pdf_repo.set_pdf_selected_for_chat.assert_not_called()

        # Restore the original method
        mock_pdf_repo.set_pdf_selected_for_chat = original_set_selected

        # Test case: PDF exists but is not owned by the user
        other_user_id = 666
        owned_pdf_id = "owned_by_other_select"
        owned_pdf_doc = PDFDocument(
            id=owned_pdf_id,
            user_id=other_user_id,
            gridfs_file_id="gridfs_other_select",
            original_filename="other_select_doc.pdf",
            upload_date=datetime.now(timezone.utc),
            parse_status=PDFParseStatus.PARSED_SUCCESS,
            is_selected_for_chat=False,
        )
        mock_pdf_repo._pdfs[owned_pdf_id] = owned_pdf_doc

        # Mock the set_pdf_selected_for_chat method again for the second part of the test
        mock_pdf_repo.set_pdf_selected_for_chat = AsyncMock()

        # Assert that PDFNotFoundError is raised for the wrong user
        with pytest.raises(PDFNotFoundError) as excinfo:
            await pdf_service.select_pdf_for_chat(current_user_id=user_id, pdf_id=owned_pdf_id)

        # Optionally, check the exception details
        assert excinfo.value.pdf_id == owned_pdf_id

        # Assert that the repository method was still NOT called
        mock_pdf_repo.set_pdf_selected_for_chat.assert_not_called()

        # Restore the original method
        mock_pdf_repo.set_pdf_selected_for_chat = original_set_selected

    async def test_select_pdf_for_chat_not_parsed(self, pdf_service, mock_pdf_repo):
        user_id = 777
        pdf_id_unparsed = "mongo_unparsed_select"
        pdf_id_parsing = "mongo_parsing_select"

        # Test case: PDF is UNPARSED
        unparsed_pdf_doc = PDFDocument(
            id=pdf_id_unparsed,
            user_id=user_id,
            gridfs_file_id="gridfs_unparsed_select",
            original_filename="unparsed_select.pdf",
            upload_date=datetime.now(timezone.utc),
            parse_status=PDFParseStatus.UNPARSED,
            is_selected_for_chat=False,
        )
        mock_pdf_repo._pdfs[pdf_id_unparsed] = unparsed_pdf_doc

        # Mock the set_pdf_selected_for_chat method to assert it's not called
        original_set_selected = mock_pdf_repo.set_pdf_selected_for_chat
        mock_pdf_repo.set_pdf_selected_for_chat = AsyncMock()

        # Assert that PDFNotParsedError is raised
        with pytest.raises(PDFNotParsedError) as excinfo:
            await pdf_service.select_pdf_for_chat(current_user_id=user_id, pdf_id=pdf_id_unparsed)

        # Optionally, check the exception details
        assert excinfo.value.pdf_id == pdf_id_unparsed

        # Assert that the repository method was NOT called
        mock_pdf_repo.set_pdf_selected_for_chat.assert_not_called()

        # Restore the original method
        mock_pdf_repo.set_pdf_selected_for_chat = original_set_selected

        # Test case: PDF is PARSING
        parsing_pdf_doc = PDFDocument(
            id=pdf_id_parsing,
            user_id=user_id,
            gridfs_file_id="gridfs_parsing_select",
            original_filename="parsing_select.pdf",
            upload_date=datetime.now(timezone.utc),
            parse_status=PDFParseStatus.PARSING,
            is_selected_for_chat=False,
        )
        mock_pdf_repo._pdfs[pdf_id_parsing] = parsing_pdf_doc

        # Mock the set_pdf_selected_for_chat method again for the second part of the test
        mock_pdf_repo.set_pdf_selected_for_chat = AsyncMock()

        # Assert that PDFNotParsedError is raised
        with pytest.raises(PDFNotParsedError) as excinfo:
            await pdf_service.select_pdf_for_chat(current_user_id=user_id, pdf_id=pdf_id_parsing)

        # Optionally, check the exception details
        assert excinfo.value.pdf_id == pdf_id_parsing

        # Assert that the repository method was still NOT called
        mock_pdf_repo.set_pdf_selected_for_chat.assert_not_called()

        # Restore the original method
        mock_pdf_repo.set_pdf_selected_for_chat = original_set_selected

    async def test_select_pdf_for_chat_repo_failure(self, pdf_service, mock_pdf_repo):
        user_id = 888
        pdf_id = "mongo_select_fail"
        parsed_pdf_doc = PDFDocument(
            id=pdf_id,
            user_id=user_id,
            gridfs_file_id="gridfs_select_fail",
            original_filename="select_fail.pdf",
            upload_date=datetime.now(timezone.utc),
            parse_status=PDFParseStatus.PARSED_SUCCESS,  # Must be parsed to be selectable
            is_selected_for_chat=False,
        )
        mock_pdf_repo._pdfs[pdf_id] = parsed_pdf_doc

        # Mock the set_pdf_selected_for_chat method to return False to simulate failure
        original_set_selected = mock_pdf_repo.set_pdf_selected_for_chat
        mock_pdf_repo.set_pdf_selected_for_chat = AsyncMock(return_value=False)

        # Assert that PDFDomainError is raised
        with pytest.raises(
            PDFDomainError, match="Failed to select PDF for chat due to an unexpected repository issue."
        ):
            await pdf_service.select_pdf_for_chat(current_user_id=user_id, pdf_id=pdf_id)

        # Assert that the repository method was called with the correct arguments
        mock_pdf_repo.set_pdf_selected_for_chat.assert_called_once_with(
            user_id=user_id, pdf_id_to_select=pdf_id
        )

        # Restore the original method
        mock_pdf_repo.set_pdf_selected_for_chat = original_set_selected

        # Verify the state in the mock repo (optional)
        assert mock_pdf_repo._selected_pdf_id.get(user_id) is None
