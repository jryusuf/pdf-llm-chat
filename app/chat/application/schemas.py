from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.chat.domain.models import LLMResponseStatus, MessageSenderType


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class ChatMessageTurnResponse(BaseModel):
    id: int
    pdf_id: str
    pdf_filename: str
    user_message: str
    user_timestamp: datetime
    llm_response: Optional[str]
    llm_status: LLMResponseStatus
    llm_timestamp: Optional[datetime]

    class Config:
        orm_mode = True


class PaginatedChatHistoryResponse(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    page_size: int
    data: List[ChatMessageTurnResponse]
