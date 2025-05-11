from typing import List, Optional
from app.core.config import Settings  # Assuming get_settings is used to inject
# from app.application.tasks import enqueue_llm_response_generation (or from app.chat.application.tasks)
# from procrastinate import App # App instance for deferring tasks

# To avoid circular dependencies if tasks.py imports services,
#  services should not import tasks directly for deferring.
# The deferring logic is usually called from the router or another orchestrator.
# For this example, let's assume a defer_llm_task function is available or passed.
from typing import Callable, Coroutine, Any

DeferLLMTaskType = Callable[[int], Coroutine[Any, Any, None]]


# For interfaces from other modules, they'd be imported properly
# from app.pdf.domain.interfaces.pdf_repository import IPDFRepository
# from app.account.domain.interfaces.user_repository import IUserRepository
# Placeholder interfaces for PDF and User repo for this standalone example
class IPDFRepositoryPlaceholder(Protocol):
    async def get_selected_pdf_for_user(self, user_id: int) -> Optional[Any]:  # Any = PDFDocument-like obj
        ...

    async def get_parsed_text_for_pdf(self, pdf_id: str) -> Optional[str]:
        ...


class IUserRepositoryPlaceholder(Protocol):
    async def get_by_uuid(self, user_uuid: str) -> Optional[Any]:  # Any = User-like obj with id
        ...


class ChatApplicationService:
    def __init__(
        self,
        chat_repo: IChatRepository,
        pdf_repo: IPDFRepositoryPlaceholder,  # Use actual IPDFRepository in real app
        user_repo: IUserRepositoryPlaceholder,  # Use actual IUserRepository in real app
        settings: Settings,
        defer_llm_task: DeferLLMTaskType,  # Function to enqueue Procrastinate task
    ):
        self.chat_repo = chat_repo
        self.pdf_repo = pdf_repo
        self.user_repo = user_repo
        self.settings = settings
        self.defer_llm_task = defer_llm_task

    async def submit_user_message(
        self, user_uuid_str: str, message_data: ChatMessageRequest
    ) -> ChatMessageTurnResponse:
        user = await self.user_repo.get_by_uuid(user_uuid_str)
        if not user:
            raise UserNotFoundError(
                identifier=user_uuid_str
            )  # Assuming UserNotFoundError from account.domain

        user_id_int = user.id  # Get the internal integer ID

        selected_pdf = await self.pdf_repo.get_selected_pdf_for_user(user_id=user_id_int)
        if not selected_pdf:
            raise NoPDFSelectedForChatError()

        if selected_pdf.parse_status != "PARSED_SUCCESS":  # Assuming PDFDocument has parse_status
            raise PDFNotParsedForChatError(pdf_id=str(selected_pdf.id))  # selected_pdf.id is Mongo ObjectID

        chat_turn_domain = ChatMessageTurn(
            user_id=user_id_int,
            pdf_document_id=str(selected_pdf.id),  # Mongo ObjectID as string
            pdf_original_filename=selected_pdf.original_filename,  # Assuming PDFDocument has this
            user_message_content=message_data.message,
        )

        persisted_turn = await self.chat_repo.create_chat_turn(chat_turn_domain)

        await self.defer_llm_task(persisted_turn.id)  # Enqueue background LLM processing

        return ChatMessageTurnResponse.from_orm(persisted_turn)

    async def get_chat_history(
        self, user_uuid_str: str, page: int = 1, size: int = 20
    ) -> PaginatedChatHistoryResponse:
        user = await self.user_repo.get_by_uuid(user_uuid_str)
        if not user:
            raise UserNotFoundError(identifier=user_uuid_str)
        user_id_int = user.id

        skip = (page - 1) * size
        history_items_domain = await self.chat_repo.get_chat_history_for_user(
            user_id=user_id_int, skip=skip, limit=size
        )

        total_items = await self.chat_repo.count_chat_history_for_user(user_id=user_id_int)
        total_pages = (total_items + size - 1) // size if total_items > 0 else 0

        response_data = [ChatMessageTurnResponse.from_orm(item) for item in history_items_domain]

        return PaginatedChatHistoryResponse(
            total_items=total_items,
            total_pages=total_pages,
            current_page=page,
            page_size=size,
            data=response_data,
        )
