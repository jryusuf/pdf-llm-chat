from fastapi import UploadFile
import uuid
from datetime import datetime, timezone

from app.core.config import Settings
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

from typing import Callable, Coroutine, Any

DeferPDFParseTaskType = Callable[[str, int], Coroutine[Any, Any, None]]


class PDFApplicationService:
    def __init__(
        self,
        pdf_repo: IPDFRepository,
        settings: Settings,
        defer_parse_task: DeferPDFParseTaskType,
    ):
        """Initializes the PDFApplicationService.

        Args:
            pdf_repo: The PDF repository implementation.
            settings: The application settings.
            defer_parse_task: A callable to defer the PDF parsing task.
        """
        self.pdf_repo = pdf_repo
        self.settings = settings
        self.defer_parse_task = defer_parse_task

    async def upload_pdf(self, current_user_id: int, file: UploadFile) -> PDFMetadataResponse:
        """Handles the upload of a PDF file, saves the binary content and metadata.

        Args:
            current_user_id: The ID of the current authenticated user.
            file: The uploaded PDF file.

        Returns:
            A PDFMetadataResponse containing the metadata of the newly uploaded PDF.

        Raises:
            InvalidPDFFileTypeError: If the uploaded file is not a PDF.
        """
        if file.content_type != "application/pdf":
            raise InvalidPDFFileTypeError(provided_type=str(file.content_type))

        internal_gridfs_filename = str(uuid.uuid4())

        gridfs_id = await self.pdf_repo.save_pdf_binary(
            filename=internal_gridfs_filename,
            content=await file.read(),
            user_id=current_user_id,
            content_type=str(file.content_type),
        )

        pdf_doc_domain = PDFDocument(
            id="temp_id_before_mongo_insert",
            user_id=current_user_id,
            gridfs_file_id=gridfs_id,
            original_filename=file.filename or "untitled.pdf",
            upload_date=datetime.now(timezone.utc),
            parse_status=PDFParseStatus.UNPARSED,
        )

        persisted_pdf_doc = await self.pdf_repo.save_pdf_meta(pdf_doc_domain)
        return PDFMetadataResponse.model_validate(persisted_pdf_doc)

    async def list_pdfs_for_user(
        self, current_user_id: int, page: int, size: int
    ) -> PaginatedPDFListResponse:
        """Retrieves a paginated list of PDF metadata for a specific user.

        Args:
            current_user_id: The ID of the current authenticated user.
            page: The page number for pagination.
            size: The number of items per page.

        Returns:
            A PaginatedPDFListResponse containing the PDF metadata entries for the requested page.
        """
        skip = (page - 1) * size
        pdf_docs_domain = await self.pdf_repo.get_all_pdf_meta_for_user(
            user_id=current_user_id, skip=skip, limit=size
        )
        total_items = await self.pdf_repo.count_all_pdf_meta_for_user(user_id=current_user_id)
        total_pages = (total_items + size - 1) // size if total_items > 0 else 0

        response_data = [PDFMetadataResponse.model_validate(doc) for doc in pdf_docs_domain]
        return PaginatedPDFListResponse(
            total_items=total_items,
            total_pages=total_pages,
            current_page=page,
            page_size=size,
            data=response_data,
        )

    async def request_pdf_parsing(
        self,
        current_user_id: int,
        pdf_id: str,
    ) -> PDFParseResponse:
        """Initiates parsing for a specific PDF.

        Args:
            current_user_id: The ID of the current authenticated user.
            pdf_id: The ID of the PDF document to parse.

        Returns:
            A PDFParseResponse indicating the status of the parsing request.

        Raises:
            PDFNotFoundError: If the PDF document is not found or not owned by the user.
            PDFAlreadyParsingError: If the PDF is already being parsed or has been successfully parsed.
        """
        pdf_doc = await self.pdf_repo.get_pdf_meta_by_id(pdf_id=pdf_id, user_id=current_user_id)

        if not pdf_doc:
            raise PDFNotFoundError(pdf_id=pdf_id)

        if (
            pdf_doc.parse_status == PDFParseStatus.PARSING
            or pdf_doc.parse_status == PDFParseStatus.PARSED_SUCCESS
        ):
            raise PDFAlreadyParsingError(pdf_id=pdf_doc.id)

        pdf_doc.mark_as_parsing()
        await self.pdf_repo.update_pdf_meta(pdf_doc)

        await self.defer_parse_task(pdf_doc.id, current_user_id)

        return PDFParseResponse(
            pdf_id=pdf_doc.id, status=pdf_doc.parse_status, message="PDF parsing initiated."
        )

    async def select_pdf_for_chat(
        self,
        current_user_id: int,
        pdf_id: str,
    ) -> PDFSelectResponse:
        """Selects a specific PDF document for chat for the current user.

        Args:
            current_user_id: The ID of the current authenticated user.
            pdf_id: The ID of the PDF document to select.

        Returns:
            A PDFSelectResponse indicating the success of the selection.

        Raises:
            PDFNotFoundError: If the PDF document is not found or not owned by the user.
            PDFNotParsedError: If the PDF document has not been successfully parsed.
            PDFDomainError: If there is an unexpected repository issue during selection.
        """
        pdf_doc = await self.pdf_repo.get_pdf_meta_by_id(pdf_id=pdf_id, user_id=current_user_id)

        if not pdf_doc:
            raise PDFNotFoundError(pdf_id=pdf_id)

        try:
            pdf_doc.select_for_chat()
        except PDFNotParsedError as e:
            raise e

        success = await self.pdf_repo.set_pdf_selected_for_chat(
            user_id=current_user_id, pdf_id_to_select=pdf_doc.id
        )
        if not success:
            raise PDFDomainError("Failed to select PDF for chat due to an unexpected repository issue.")

        return PDFSelectResponse(
            pdf_id=pdf_doc.id, message="PDF selected successfully for chat.", is_selected_for_chat=True
        )
