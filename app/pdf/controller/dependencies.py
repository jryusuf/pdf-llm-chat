from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database_mongo import get_mongo_db  # Your actual MongoDB session factory
from app.pdf.infrastucture.repositories.pdf_repository import IPDFRepository
from app.pdf.infrastucture.repositories.mongo_pdf_repository import MongoPDFRepository
from app.pdf.application.services import PDFApplicationService
from app.account.infrastructure.repositories.user_repository import IUserRepository  # Actual import
from app.core.config import Settings, get_settings


async def dummy_defer_parse_task(pdf_id: str):
    print(f"Dummy defer parse task for PDF ID: {pdf_id}")
    pass


def get_pdf_repository(db: AsyncIOMotorDatabase = Depends(get_mongo_db)) -> IPDFRepository:
    return MongoPDFRepository(db)


def get_pdf_application_service(
    pdf_repo: IPDFRepository = Depends(get_pdf_repository), settings: Settings = Depends(get_settings)
) -> PDFApplicationService:
    return PDFApplicationService(
        pdf_repo=pdf_repo, settings=settings, defer_parse_task=dummy_defer_parse_task
    )
