from typing import Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from sqlalchemy import select

from database.models import User


class AuthMiddleware(BaseMiddleware):
    def __init__(self, session_pool):
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, any]], Awaitable[any]],
        event: TelegramObject,
        data: dict[str, any],
    ) -> any:
        user: User | None = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        data["session_pool"] = self.session_pool

        async with self.session_pool() as session:
            stmt = select(User).where(User.telegram_id == user.id)
            result = await session.execute(stmt)
            db_user = result.scalar_one_or_none()

            data["db_user"] = db_user
            data["session"] = session

            return await handler(event, data)
