import time
from typing import Callable, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, limit: float = 1.0):
        self.limit = limit
        self.last_calls: dict[int, float] = {}
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Any],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id if hasattr(event, "from_user") and event.from_user else None
        if not user_id:
            return await handler(event, data)

        now = time.time()
        if user_id in self.last_calls:
            if now - self.last_calls[user_id] < self.limit:
                return None

        self.last_calls[user_id] = now
        return await handler(event, data)
