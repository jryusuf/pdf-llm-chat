from typing import List, Optional, Callable, Coroutine, Any
from datetime import datetime, timezone  # Ensure timezone for datetime.now()

# Core imports (assuming they exist and are correct)
from app.core.config import Settings  # For LLM_RETRY_ATTEMPTS if used by service directly
from app.chat.domain.models import ChatMessageTurn, LLMResponseStatus
from app.chat.infrastructure.repositories.chat_repository import IChatRepository
from app.chat.domain.exceptions import (
    NoPDFSelectedForChatError,
    PDFNotParsedForChatError,
    ChatDomainError,  # For generic chat related domain errors
)
from app.pdf.infrastucture.repositories.pdf_repository import IPDFRepository  # To get selected PDF info

# Assuming PDFDocument domain model is accessible or its relevant parts are returned by IPDFRepository
from app.pdf.domain.models import PDFDocument, PDFParseStatus
from app.pdf.domain.exceptions import PDFNotFoundError  # Can be raised by PDF repo

from app.chat.application.schemas import (
    ChatMessageRequest,
    ChatMessageTurnResponse,
    PaginatedChatHistoryResponse,
)

# Type hint for the function that defers Procrastinate tasks
DeferLLMTaskType = Callable[[int], Coroutine[Any, Any, None]]  # Takes chat_turn_id (int)


class ChatApplicationService:
    def __init__(
        self,
        chat_repo: IChatRepository,
        pdf_repo: IPDFRepository,  # Dependency to get selected PDF details and parsed text
        settings: Settings,  # For LLM_RETRY_ATTEMPTS, etc.
        defer_llm_task: DeferLLMTaskType,
    ):
        self.chat_repo = chat_repo
        self.pdf_repo = pdf_repo
        self.settings = settings
        self.defer_llm_task = defer_llm_task

    async def submit_user_message(
        self, current_user_id: int, message_data: ChatMessageRequest
    ) -> ChatMessageTurnResponse:
        # 1. Get the currently selected PDF for the user
        # The IPDFRepository should have a method for this.
        # This method in IPDFRepository would query MongoDB for the PDF where
        # user_id == current_user_id AND is_selected_for_chat == true
        selected_pdf_domain_obj: Optional[PDFDocument] = await self.pdf_repo.get_selected_pdf_for_user(
            user_id=current_user_id
        )

        if not selected_pdf_domain_obj:
            raise NoPDFSelectedForChatError()

        # 2. Check if the selected PDF is successfully parsed
        if selected_pdf_domain_obj.parse_status != PDFParseStatus.PARSED_SUCCESS:
            raise PDFNotParsedForChatError(pdf_id=selected_pdf_domain_obj.id)

        # 3. Create the chat turn domain object
        chat_turn_domain = ChatMessageTurn(
            user_id=current_user_id,
            pdf_document_id=selected_pdf_domain_obj.id,  # This is the MongoDB _id string
            pdf_original_filename=selected_pdf_domain_obj.original_filename,
            user_message_content=message_data.message,
            user_message_timestamp=datetime.now(timezone.utc),
            # llm_response_status defaults to PENDING in the domain model
        )

        # 4. Persist the initial chat turn (user message + LLM placeholder)
        persisted_turn = await self.chat_repo.create_chat_turn(chat_turn_domain)

        # 5. Enqueue the background task for LLM response generation
        if persisted_turn.id is None:  # Should not happen if repo.create returns with ID
            # logger.error("Persisted chat turn did not receive an ID from the repository.")
            raise ChatDomainError("Failed to persist chat message properly before LLM task.")

        await self.defer_llm_task(persisted_turn.id)

        # 6. Return the initial state of the turn to the user
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

        response_data = [ChatMessageTurnResponse.from_orm(item) for item in history_items_domain]

        return PaginatedChatHistoryResponse(
            total_items=total_items,
            total_pages=total_pages,
            current_page=page,
            page_size=size,
            data=response_data,
        )
