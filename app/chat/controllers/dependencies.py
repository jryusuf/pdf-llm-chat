from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorDatabase
from procrastinate import App as ProcrastinateApp  # Assuming this is your Procrastinate App type

from app.core.config import Settings, get_settings
from app.core.database import get_db_session  # Your SQLAlchemy session factory
from app.core.database_mongo import get_mongo_db  # Your MongoDB client/db factory
from app.core.procrastinate_app import get_procrastinate_app  # Your Procrastinate App factory

from app.chat.infrastructure.repositories.chat_repository import IChatRepository
from app.chat.infrastructure.repositories.sqlalchmey_chat_repository import SQLAlchemyChatRepository
from app.chat.application.services import ChatApplicationService, DeferLLMTaskType

# Dependencies from other modules/services
from app.pdf.infrastucture.repositories.pdf_repository import IPDFRepository
from app.pdf.infrastucture.repositories.mongo_pdf_repository import MongoPDFRepository  # Concrete PDF repo

# For User ID resolution, this is now handled by the auth dependency.
# The ChatApplicationService itself no longer needs IUserRepository.


# Procrastinate task deferral function
# This function will be created within the scope where procrastinate_app is available
async def _defer_llm_task_via_procrastinate(procrastinate_app: ProcrastinateApp, chat_turn_id: int):
    from app.application.tasks import (
        generate_llm_response_task,
    )  # Import task here to avoid circularity at module level

    await procrastinate_app.defer_async(generate_llm_response_task, chat_turn_id=chat_turn_id)


# Dependency for Chat Repository
def get_chat_repository(session: AsyncSession = Depends(get_db_session)) -> IChatRepository:
    return SQLAlchemyChatRepository(session=session)


# Dependency for PDF Repository (needed by Chat Service)
# This assumes MongoPDFRepository is the concrete implementation you want to use here.
def get_pdf_repository_for_chat_service(db: AsyncIOMotorDatabase = Depends(get_mongo_db)) -> IPDFRepository:
    return MongoPDFRepository(db=db)


# Dependency for Chat Application Service
def get_chat_application_service(
    chat_repo: IChatRepository = Depends(get_chat_repository),
    pdf_repo: IPDFRepository = Depends(get_pdf_repository_for_chat_service),
    settings: Settings = Depends(get_settings),
    procrastinate_app: ProcrastinateApp = Depends(get_procrastinate_app),  # Inject Procrastinate App
) -> ChatApplicationService:
    # Create the specific deferral function using the injected procrastinate_app
    async def actual_defer_llm_task(chat_turn_id: int):
        await _defer_llm_task_via_procrastinate(procrastinate_app, chat_turn_id)

    return ChatApplicationService(
        chat_repo=chat_repo, pdf_repo=pdf_repo, settings=settings, defer_llm_task=actual_defer_llm_task
    )
