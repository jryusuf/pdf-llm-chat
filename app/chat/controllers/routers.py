from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Annotated

from app.lib.security import get_current_authenticated_user, AuthenticatedUser

from app.chat.application.services import ChatApplicationService
from app.chat.application.schemas import (
    ChatMessageRequest,
    ChatMessageTurnResponse,
    PaginatedChatHistoryResponse,
)

from app.chat.domain.exceptions import NoPDFSelectedForChatError, PDFNotParsedForChatError, ChatDomainError

from app.pdf.domain.exceptions import PDFNotFoundError

from app.chat.controllers.dependencies import get_chat_application_service
from loguru import logger

router = APIRouter(
    dependencies=[Depends(get_current_authenticated_user)],
)


@router.post("/pdf-chat", response_model=ChatMessageTurnResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_chat_message(
    message_data: ChatMessageRequest,
    current_auth_user: Annotated[AuthenticatedUser, Depends(get_current_authenticated_user)],
    chat_service: Annotated[ChatApplicationService, Depends(get_chat_application_service)],
):
    logger.info(f"Received chat message from user: {current_auth_user.id}")
    try:
        response_turn = await chat_service.submit_user_message(
            current_user_id=current_auth_user.id, message_data=message_data
        )
        logger.info(
            f"Chat message submitted successfully for user: {current_auth_user.id}, : {response_turn.id}"
        )
        return response_turn
    except NoPDFSelectedForChatError as e:
        logger.warning(f"No PDF selected for chat for user: {current_auth_user.id}, error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PDFNotParsedForChatError as e:
        logger.warning(
            f"Selected PDF not parsed for chat for user: {current_auth_user.id}, error: {str(e)}"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except PDFNotFoundError as e:
        logger.warning(f"Selected PDF not found for chat for user: {current_auth_user.id}, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Selected PDF for chat not found: {str(e)}"
        )
    except ChatDomainError as e:
        logger.error(f"Chat domain error for user: {current_auth_user.id}, error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error submitting chat message for user: {current_auth_user.id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred."
        )


@router.get("/chat-history", response_model=PaginatedChatHistoryResponse)
async def get_user_chat_history(
    current_auth_user: Annotated[AuthenticatedUser, Depends(get_current_authenticated_user)],
    chat_service: Annotated[ChatApplicationService, Depends(get_chat_application_service)],
    page: int = Query(1, ge=1, description="Page number to retrieve"),
    size: int = Query(20, ge=1, le=100, description="Number of items per page"),
):
    logger.info(
        f"Received request for chat history for user: {current_auth_user.id}, page: {page}, size: {size}"
    )
    try:
        history_response = await chat_service.get_chat_history(
            current_user_id=current_auth_user.id, page=page, size=size
        )
        logger.info(f"Successfully retrieved chat history for user: {current_auth_user.id}")
        return history_response
    except Exception as e:
        logger.exception(f"Unexpected error retrieving chat history for user: {current_auth_user.id}")
