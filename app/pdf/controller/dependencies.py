from fastapi import Depends
from motor.motor_asyncio import (
    AsyncIOMotorDatabase,
    AsyncIOMotorGridFSBucket,
)
from app.core.database_mongo import get_mongo_db
from app.pdf.infrastucture.repositories.pdf_repository import IPDFRepository
from app.pdf.infrastucture.repositories.mongo_pdf_repository import MongoPDFRepository
from app.pdf.application.services import PDFApplicationService
from app.account.infrastructure.repositories.user_repository import IUserRepository
from app.core.config import Settings, get_settings
from app.pdf.domain.exceptions import PDFNotFoundError
from app.pdf.domain.models import PDFDocument, PDFParseStatus
from pypdf import PdfReader
import io
from loguru import logger


async def get_repository_for_task() -> IPDFRepository:
    logger.warning(
        "get_repository_for_task is a placeholder and needs to be implemented "
        "based on your Procrastinate and DI setup."
    )
    db = await get_mongo_db()
    fs = AsyncIOMotorGridFSBucket(db)
    return MongoPDFRepository(db, fs)


async def dummy_defer_parse_task(pdf_id: str, user_id: int):
    logger.info(f"Starting PDF parsing task for PDF ID: {pdf_id}, User ID: {user_id}")
    pdf_repo: IPDFRepository = await get_repository_for_task()
    pdf_doc: PDFDocument | None = None

    try:
        pdf_doc = await pdf_repo.get_pdf_meta_by_id(pdf_id=pdf_id, user_id=user_id)
        if not pdf_doc:
            logger.error(f"PDF not found for ID: {pdf_id} and User ID: {user_id}")
            return

        pdf_binary_stream = await pdf_repo.get_pdf_binary_stream_by_gridfs_id(pdf_doc.gridfs_file_id)
        if not pdf_binary_stream:
            error_msg = f"PDF binary not found for GridFS ID: {pdf_doc.gridfs_file_id}"
            logger.error(error_msg)
            pdf_doc.mark_parse_failure(error_msg)
            await pdf_repo.update_pdf_meta(pdf_doc)
            return

        pdf_content = await pdf_binary_stream.read()
        pdf_file_like_object = io.BytesIO(pdf_content)

        reader = PdfReader(pdf_file_like_object)
        extracted_text_parts = []
        for page_num, page in enumerate(reader.pages):
            try:
                extracted_text_parts.append(page.extract_text())
            except Exception as e:
                logger.warning(f"Could not extract text from page {page_num} for PDF {pdf_id}: {e}")
                extracted_text_parts.append(f"[Error extracting page {page_num}]")

        full_extracted_text = " ".join(filter(None, extracted_text_parts))

        parsed_text_id = await pdf_repo.save_parsed_text(
            pdf_meta_id=pdf_doc.id, text_content=full_extracted_text
        )

        pdf_doc.mark_parse_success(parsed_text_document_id=parsed_text_id)
        await pdf_repo.update_pdf_meta(pdf_doc)
        logger.info(f"Successfully parsed PDF {pdf_id}. Parsed text ID: {parsed_text_id}")

    except PDFNotFoundError:
        logger.error(f"PDF not found during parsing task for ID: {pdf_id}")

    except Exception as e:
        error_msg = f"Error during PDF parsing task for PDF ID {pdf_id}: {str(e)}"
        logger.exception(error_msg)
        if pdf_doc:
            pdf_doc.mark_parse_failure(error_msg)
            try:
                await pdf_repo.update_pdf_meta(pdf_doc)
            except Exception as update_e:
                logger.error(f"Failed to update PDF meta after parsing failure for {pdf_id}: {update_e}")
    finally:
        if "pdf_file_like_object" in locals() and hasattr(pdf_file_like_object, "close"):
            pass
            # pdf_file_like_object.close()
        if (
            "pdf_binary_stream" in locals()
            and pdf_binary_stream is not None
            and hasattr(pdf_binary_stream, "close")
            and callable(getattr(pdf_binary_stream, "close", None))
        ):
            # await pdf_binary_stream.close()
            pass


async def get_pdf_repository(db: AsyncIOMotorDatabase = Depends(get_mongo_db)) -> IPDFRepository:
    fs = AsyncIOMotorGridFSBucket(db)
    return MongoPDFRepository(db, fs)


def get_pdf_application_service(
    pdf_repo: IPDFRepository = Depends(get_pdf_repository), settings: Settings = Depends(get_settings)
) -> PDFApplicationService:
    return PDFApplicationService(
        pdf_repo=pdf_repo, settings=settings, defer_parse_task=dummy_defer_parse_task
    )
