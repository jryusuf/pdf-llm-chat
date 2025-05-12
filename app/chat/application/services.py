from typing import List, Optional, Callable, Coroutine, Any
from datetime import datetime, timezone

from app.core.config import Settings
from app.chat.domain.models import ChatMessageTurn, LLMResponseStatus
from app.chat.infrastructure.repositories.chat_repository import IChatRepository
from app.chat.domain.exceptions import (
    NoPDFSelectedForChatError,
    PDFNotParsedForChatError,
    ChatDomainError,
)
from app.pdf.infrastucture.repositories.pdf_repository import IPDFRepository

from app.pdf.domain.models import PDFDocument, PDFParseStatus
from app.pdf.domain.exceptions import PDFNotFoundError
from app.chat.application.schemas import (
    ChatMessageRequest,
    ChatMessageTurnResponse,
    PaginatedChatHistoryResponse,
)


DeferLLMTaskType = Callable[[int, int], Coroutine[Any, Any, None]]


class ChatApplicationService:
    def __init__(
        self,
        chat_repo: IChatRepository,
        pdf_repo: IPDFRepository,
        settings: Settings,
        defer_llm_task: DeferLLMTaskType,
    ):
        self.chat_repo = chat_repo
        self.pdf_repo = pdf_repo
        self.settings = settings
        self.defer_llm_task = defer_llm_task

    async def submit_user_message(
        self, current_user_id: int, message_data: ChatMessageRequest
    ) -> ChatMessageTurnResponse:
        selected_pdf_domain_obj: Optional[PDFDocument] = await self.pdf_repo.get_selected_pdf_for_user(
            user_id=current_user_id
        )

        if not selected_pdf_domain_obj:
            raise NoPDFSelectedForChatError()

        if selected_pdf_domain_obj.parse_status != PDFParseStatus.PARSED_SUCCESS:
            raise PDFNotParsedForChatError(pdf_id=selected_pdf_domain_obj.id)

        chat_turn_domain = ChatMessageTurn(
            user_id=current_user_id,
            pdf_document_id=selected_pdf_domain_obj.id,
            pdf_original_filename=selected_pdf_domain_obj.original_filename,
            user_message_content=message_data.message,
            user_message_timestamp=datetime.now(timezone.utc),
        )

        persisted_turn = await self.chat_repo.create_chat_turn(chat_turn_domain)

        if persisted_turn.id is None:
            raise ChatDomainError("Failed to persist chat message properly before LLM task.")

        await self.defer_llm_task(persisted_turn.id, current_user_id)

        return ChatMessageTurnResponse.from_orm(persisted_turn)

    async def get_chat_history(
        self, current_user_id: int, page: int = 1, size: int = 20
    ) -> PaginatedChatHistoryResponse:
        skip = (page - 1) * size
        history_items_domain: List[ChatMessageTurn] = await self.chat_repo.get_chat_history_for_user(
            user_id=current_user_id, skip=skip, limit=size
        )

        total_items: int = await self.chat_repo.count_chat_history_for_user(user_id=current_user_id)
        total_pages: int = (total_items + size - 1) // size if total_items > 0 else 0

        total_items: int = await self.chat_repo.count_chat_history_for_user(user_id=current_user_id)
        total_pages: int = (total_items + size - 1) // size if total_items > 0 else 0

        response_data = [ChatMessageTurnResponse.from_orm(item) for item in history_items_domain]

        return PaginatedChatHistoryResponse(
            total_items=total_items,
            total_pages=total_pages,
            current_page=page,
            page_size=size,
            data=response_data,
        )
