from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from app.pdf.domain.models import PDFParseStatus


class PDFMetadataResponse(BaseModel):
    id: str
    user_id: str
    original_filename: str
    upload_date: datetime
    parse_status: PDFParseStatus
    is_selected_for_chat: bool
    parse_error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedPDFListResponse(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    page_size: int
    data: List[PDFMetadataResponse]


class PDFParseRequest(BaseModel):
    pdf_id: str


class PDFParseResponse(BaseModel):
    pdf_id: str
    status: PDFParseStatus
    message: str


class PDFSelectRequest(BaseModel):
    pdf_id: str


class PDFSelectResponse(BaseModel):
    pdf_id: str
    message: str
    is_selected_for_chat: bool
