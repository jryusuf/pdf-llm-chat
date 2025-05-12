from typing import Protocol, List, Optional, Any  # Any for file stream
from app.pdf.domain.models import PDFDocument


class IPDFRepository(Protocol):
    async def save_pdf_meta(self, pdf_doc: PDFDocument) -> PDFDocument: ...

    async def save_pdf_binary(
        self, filename: str, content: Any, user_id: int, content_type: str = "application/pdf"
    ) -> str:  # Returns GridFS file ID
        ...

    async def get_pdf_meta_by_id(self, pdf_id: str, user_id: int) -> Optional[PDFDocument]: ...

    async def get_pdf_binary_stream_by_gridfs_id(
        self, gridfs_id: str
    ) -> Optional[Any]:  # Returns a stream-like object
        ...

    async def get_all_pdf_meta_for_user(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> List[PDFDocument]: ...

    async def count_all_pdf_meta_for_user(self, user_id: int) -> int: ...

    async def update_pdf_meta(self, pdf_doc: PDFDocument) -> PDFDocument: ...

    async def set_pdf_selected_for_chat(
        self, user_id: int, pdf_id_to_select: str
    ) -> bool:  # Returns success
        ...

    async def save_parsed_text(
        self, pdf_meta_id: str, text_content: str
    ) -> str:  # Returns ID of parsed text doc
        ...

    async def get_parsed_text_by_pdf_meta_id(self, pdf_meta_id: str) -> Optional[str]: ...

    async def get_selected_pdf_for_user(self, user_id: int) -> Optional[PDFDocument]:
        """Retrieves the PDF document currently selected for chat by the user."""
        ...
