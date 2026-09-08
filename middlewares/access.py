"""Access control middleware — whitelist only."""
from typing import Any, Callable, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from loguru import logger
from config import ALLOWED_USER_IDS


class AccessMiddleware(BaseMiddleware):
    """
    Blocks all messages/callbacks from users not in ALLOWED_USER_IDS.
    If ALLOWED_USER_IDS is empty — allows everyone (dev mode).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not ALLOWED_USER_IDS:
            return await handler(event, data)

        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id if event.from_user else None

        if user_id and user_id not in ALLOWED_USER_IDS:
            logger.warning(
                f"Blocked access from user {user_id} "
                f"(username={getattr(event.from_user, 'username', 'N/A')})"
            )
            if isinstance(event, Message):
                await event.answer("🔒 Этот бот доступен только владельцу.")
            elif isinstance(event, CallbackQuery):
                await event.answer("🔒 Доступ запрещён", show_alert=True)
            return None

        return await handler(event, data)
