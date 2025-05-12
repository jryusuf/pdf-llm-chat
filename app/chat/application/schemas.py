from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from app.chat.domain.models import LLMResponseStatus, MessageSenderType


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class ChatMessageTurnResponse(BaseModel):
    id: int
    user_id: str  # Reverted back to str from int
    pdf_document_id: str
    pdf_original_filename: str
    user_message_content: str
    user_message_timestamp: datetime
    llm_response_content: Optional[str]
    llm_response_status: LLMResponseStatus
    llm_response_timestamp: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PaginatedChatHistoryResponse(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    page_size: int
    data: List[ChatMessageTurnResponse]
