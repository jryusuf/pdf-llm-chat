from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any  # Any for GridFS file reference initially
import uuid  # If using UUIDs for PDF domain IDs, distinct from Mongo's ObjectId
from app.pdf.domain.exceptions import PDFNotParsedError


class PDFParseStatus(str, Enum):
    UNPARSED = "UNPARSED"
    PARSING = "PARSING"
    PARSED_SUCCESS = "PARSED_SUCCESS"
    PARSED_FAILURE = "PARSED_FAILURE"


class PDFDocument:
    id: str  # MongoDB's ObjectId as string
    user_id: int  # Internal DB User ID
    gridfs_file_id: str  # GridFS ObjectId as string for the binary
    original_filename: str
    upload_date: datetime
    parse_status: PDFParseStatus
    parse_error_message: Optional[str]
    is_selected_for_chat: bool
    parsed_text_id: Optional[str]  # ObjectId of doc in parsed_pdf_texts_collection

    def __init__(
        self,
        id: str,
        user_id: int,
        gridfs_file_id: str,
        original_filename: str,
        upload_date: Optional[datetime] = None,
        parse_status: PDFParseStatus = PDFParseStatus.UNPARSED,
        parse_error_message: Optional[str] = None,
        is_selected_for_chat: bool = False,
        parsed_text_id: Optional[str] = None,
    ):
        self.id = id
        self.user_id = user_id
        self.gridfs_file_id = gridfs_file_id
        self.original_filename = original_filename
        self.upload_date = upload_date or datetime.now(timezone.utc)
        self.parse_status = parse_status
        self.parse_error_message = parse_error_message
        self.is_selected_for_chat = is_selected_for_chat
        self.parsed_text_id = parsed_text_id

    def mark_as_parsing(self):
        if self.parse_status not in [PDFParseStatus.UNPARSED, PDFParseStatus.PARSED_FAILURE]:
            # Potentially raise a domain exception if trying to parse an already parsed/parsing doc
            pass  # Or handle idempotency
        self.parse_status = PDFParseStatus.PARSING
        self.parse_error_message = None

    def mark_parse_success(self, parsed_text_document_id: str):
        self.parse_status = PDFParseStatus.PARSED_SUCCESS
        self.parsed_text_id = parsed_text_document_id
        self.parse_error_message = None

    def mark_parse_failure(self, error_message: str):
        self.parse_status = PDFParseStatus.PARSED_FAILURE
        self.parse_error_message = error_message

    def select_for_chat(self):
        if self.parse_status != PDFParseStatus.PARSED_SUCCESS:
            raise PDFNotParsedError(pdf_id=self.id)  # From domain exceptions
        self.is_selected_for_chat = True

    def deselect_for_chat(self):
        self.is_selected_for_chat = False
