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
        """Initializes the ChatApplicationService.

        Args:
            chat_repo: The chat repository implementation.
            pdf_repo: The PDF repository implementation.
            settings: The application settings.
            defer_llm_task: A callable to defer the LLM processing task.
        """
        self.chat_repo = chat_repo
        self.pdf_repo = pdf_repo
        self.settings = settings
        self.defer_llm_task = defer_llm_task

    async def submit_user_message(
        self, current_user_id: int, message_data: ChatMessageRequest
    ) -> ChatMessageTurnResponse:
        """Submits a user's chat message, creates a chat turn, and defers an LLM processing task.

        Args:
            current_user_id: The ID of the current authenticated user.
            message_data: The user's chat message request data.

        Returns:
            A ChatMessageTurnResponse representing the created chat turn with initial PENDING status.

        Raises:
            NoPDFSelectedForChatError: If no PDF is currently selected for the user.
            PDFNotParsedForChatError: If the selected PDF has not been successfully parsed.
            ChatDomainError: If there is an issue persisting the chat message before deferring the LLM task.
        """
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
        """Retrieves paginated chat history for a specific user.

        Args:
            current_user_id: The ID of the current authenticated user.
            page: The page number for pagination (default is 1).
            size: The number of items per page (default is 20).

        Returns:
            A PaginatedChatHistoryResponse containing the chat history entries for the requested page.
        """
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
