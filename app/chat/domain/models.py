from datetime import datetime, timezone
from enum import Enum
import uuid
from typing import Optional


class MessageSenderType(str, Enum):
    USER = "USER"
    LLM = "LLM"


class LLMResponseStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED_SUCCESS = "COMPLETED_SUCCESS"
    FAILED_RETRIES_EXHAUSTED = "FAILED_RETRIES_EXHAUSTED"


class ChatMessageTurn:
    id: Optional[int]
    user_id: int
    pdf_document_id: str
    pdf_original_filename: str

    user_message_content: str
    user_message_timestamp: datetime

    llm_response_content: Optional[str]
    llm_response_status: LLMResponseStatus
    llm_response_timestamp: Optional[datetime]

    retry_attempts: int

    def __init__(
        self,
        user_id: int,
        pdf_document_id: str,
        pdf_original_filename: str,
        user_message_content: str,
        id: Optional[int] = None,
        user_message_timestamp: Optional[datetime] = None,
        llm_response_content: Optional[str] = None,
        llm_response_status: LLMResponseStatus = LLMResponseStatus.PENDING,
        llm_response_timestamp: Optional[datetime] = None,
        retry_attempts: int = 0,
    ):
        self.id = id
        self.user_id = user_id
        self.pdf_document_id = pdf_document_id
        self.pdf_original_filename = pdf_original_filename
        self.user_message_content = user_message_content
        self.user_message_timestamp = user_message_timestamp or datetime.now(timezone.utc)
        self.llm_response_content = llm_response_content
        self.llm_response_status = llm_response_status
        self.llm_response_timestamp = llm_response_timestamp
        self.retry_attempts = retry_attempts

    def mark_llm_processing(self):
        self.llm_response_status = LLMResponseStatus.PROCESSING
        self.llm_response_timestamp = datetime.now(timezone.utc)

    def set_llm_response_success(self, content: str):
        self.llm_response_content = content
        self.llm_response_status = LLMResponseStatus.COMPLETED_SUCCESS
        self.llm_response_timestamp = datetime.now(timezone.utc)

    def set_llm_response_failure(self):
        self.llm_response_status = LLMResponseStatus.FAILED_RETRIES_EXHAUSTED
        self.llm_response_timestamp = datetime.now(timezone.utc)

    def increment_retry(self):
        self.retry_attempts += 1
