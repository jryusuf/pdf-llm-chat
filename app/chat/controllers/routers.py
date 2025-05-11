from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.chat.application.services import ChatApplicationService
from app.chat.application.schemas import (
    ChatMessageRequest,
    ChatMessageTurnResponse,
    PaginatedChatHistoryResponse,
)
from app.chat.domain.exceptions import NoPDFSelectedForChatError, PDFNotParsedForChatError
from app.lib.security import get_current_user_payload, TokenPayload
from app.chat.controllers.dependencies import get_chat_application_service
from typing import Annotated

router = APIRouter(
    prefix="/chat",
    tags=["Chat Service"],
)


# This is a simplified dependency setup. In a full app, get_chat_application_service
# would be properly defined in dependencies.py and handle Procrastinate app injection.
# For this example, we'll assume direct instantiation or a simpler DI.
# For now, let's use a placeholder dependency factory.
def get_chat_service_placeholder() -> ChatApplicationService:
    # This is NOT how you'd do it in production. Repos need sessions etc.
    # This is just to make the router syntactically runnable for the example.
    raise NotImplementedError("Chat service DI needs full setup with DB sessions and Procrastinate app.")


@router.post("/pdf-chat", response_model=ChatMessageTurnResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_chat_message(
    message_data: ChatMessageRequest,
    current_user: Annotated[TokenPayload, Depends(get_current_user_payload)],
    chat_service: Annotated[
        ChatApplicationService, Depends(get_chat_service_placeholder)
    ],  # Replace with real DI
):
    try:
        # Pass user_uuid from token payload
        response_turn = await chat_service.submit_user_message(
            user_uuid_str=current_user.sub, message_data=message_data
        )
        return response_turn
    except NoPDFSelectedForChatError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PDFNotParsedForChatError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except UserNotFoundError:  # Assuming UserNotFoundError from account domain is caught by global handler
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found, re-authenticate."
        )
    # Other exceptions would be caught by global handlers


@router.get("/chat-history", response_model=PaginatedChatHistoryResponse)
async def get_user_chat_history(
    current_user: Annotated[TokenPayload, Depends(get_current_user_payload)],
    chat_service: Annotated[
        ChatApplicationService, Depends(get_chat_service_placeholder)
    ],  # Replace with real DI
    page: int = Query(1, ge=1, description="Page number to retrieve"),
    size: int = Query(20, ge=1, le=100, description="Number of items per page"),
):
    try:
        history_response = await chat_service.get_chat_history(
            user_uuid_str=current_user.sub, page=page, size=size
        )
        return history_response
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found, re-authenticate."
        )
