from typing import Protocol, List, Optional
from app.chat.domain.models import ChatMessageTurn


class IChatRepository(Protocol):
    async def create_chat_turn(self, chat_turn: ChatMessageTurn) -> ChatMessageTurn:
        ...

    async def get_chat_turn_by_id(self, turn_id: int, user_id: int) -> Optional[ChatMessageTurn]:
        ...

    async def update_llm_response_in_turn(self, chat_turn: ChatMessageTurn) -> ChatMessageTurn:
        ...

    async def get_chat_history_for_user(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> List[ChatMessageTurn]:
        ...

    async def count_chat_history_for_user(self, user_id: int) -> int:
        ...
