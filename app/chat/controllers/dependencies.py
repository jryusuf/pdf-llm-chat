from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import Settings, get_settings
from app.chat.domain.interfaces.chat_repository import IChatRepository
from app.chat.infrastructure.repositories.sqlalchemy_chat_repository import SQLAlchemyChatRepository
from app.chat.application.services import ChatApplicationService
from app.pdf.domain.interfaces.pdf_repository import IPDFRepository  # Actual import path
from app.account.domain.interfaces.user_repository import IUserRepository  # Actual import path

# from app.pdf.presentation.dependencies import get_pdf_repository # If PDF repo is complex to get
# from app.account.presentation.dependencies import get_user_repository # If User repo is complex
from app.core.database import get_db_session  # Your actual DB session factory

# Placeholder for PDF and User Repositories - in real app, these would be properly injected
# This highlights the need for clear dependency management across modules if they become services
from app.pdf.infrastructure.repositories.mongo_pdf_repository import MongoPDFRepository  # Example
from app.account.infrastructure.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)  # Example
from app.core.database_mongo import get_mongo_db  # Example
from motor.motor_asyncio import AsyncIOMotorDatabase


def get_pdf_repository_placeholder(
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> IPDFRepositoryPlaceholder:
    return MongoPDFRepository(db)  # Assuming MongoPDFRepository implements the placeholder for now


def get_user_repository_placeholder(
    session: AsyncSession = Depends(get_db_session),
) -> IUserRepositoryPlaceholder:
    return SQLAlchemyUserRepository(session)  # Assuming this implements the placeholder


# Placeholder for Procrastinate defer function
async def dummy_defer_llm_task(chat_turn_id: int):
    print(f"Dummy defer LLM task for chat_turn_id: {chat_turn_id}")
    pass


def get_chat_application_service(
    chat_repo: IChatRepository = Depends(SQLAlchemyChatRepository),  # FastAPI can inject session to repo
    pdf_repo: IPDFRepositoryPlaceholder = Depends(get_pdf_repository_placeholder),
    user_repo: IUserRepositoryPlaceholder = Depends(get_user_repository_placeholder),
    settings: Settings = Depends(get_settings),
    # procrastinate_app: App = Depends(get_procrastinate_app) # If procrastinate app is a dependency
) -> ChatApplicationService:
    return ChatApplicationService(
        chat_repo=chat_repo,
        pdf_repo=pdf_repo,
        user_repo=user_repo,
        settings=settings,
        defer_llm_task=dummy_defer_llm_task,  # Replace with actual Procrastinate deferral
    )
