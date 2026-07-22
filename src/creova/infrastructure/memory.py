from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from creova.domain.enums import AccessRole, AccessStatus, ConversationStage
from creova.domain.models import AccessGrant, ImageConversation


class BootstrapAccessGrantRepository:
    """Development/bootstrap repository. Replace with PostgreSQL in Prompt 03."""

    def __init__(self, admin_ids: frozenset[int], allowed_ids: frozenset[int]) -> None:
        self._admin_ids = admin_ids
        self._allowed_ids = allowed_ids | admin_ids

    async def find_effective_by_telegram_user_id(self, telegram_user_id: int) -> AccessGrant | None:
        if telegram_user_id not in self._allowed_ids:
            return None
        role = AccessRole.ADMIN if telegram_user_id in self._admin_ids else AccessRole.USER
        return AccessGrant(
            id=uuid4(),
            telegram_user_id=telegram_user_id,
            role=role,
            status=AccessStatus.ACTIVE,
            valid_from=datetime(2020, 1, 1, tzinfo=UTC),
        )


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self._conversations: dict[UUID, ImageConversation] = {}

    async def add(self, conversation: ImageConversation) -> None:
        self._conversations[conversation.id] = conversation

    async def get(self, conversation_id: UUID) -> ImageConversation | None:
        return self._conversations.get(conversation_id)

    async def save(self, conversation: ImageConversation) -> None:
        self._conversations[conversation.id] = conversation

    async def get_active(
        self,
        *,
        owner_telegram_user_id: int,
        chat_id: int,
    ) -> ImageConversation | None:
        for conversation in self._conversations.values():
            if (
                conversation.owner_telegram_user_id == owner_telegram_user_id
                and conversation.chat_id == chat_id
                and conversation.stage not in _TERMINAL_STAGES
            ):
                return conversation
        return None


_TERMINAL_STAGES = frozenset(
    {
        ConversationStage.QUEUED,
        ConversationStage.GENERATING,
        ConversationStage.COMPLETED,
        ConversationStage.FAILED,
        ConversationStage.CANCELLED,
        ConversationStage.EXPIRED,
    }
)
