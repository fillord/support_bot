# bot/filters.py

from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from bot.config import config
from bot.database import async_session
from bot.crud import get_operators


# --- 1) Фильтр IsAdmin ---
class IsAdmin(BaseFilter):
    async def __call__(self, message: Union[Message, CallbackQuery]) -> bool:
        if isinstance(message, CallbackQuery):
            user_id = message.from_user.id
        else:
            user_id = message.from_user.id

        return user_id in config.get_admin_list


# --- 2) Фильтр IsOperator ---
class IsOperator(BaseFilter):
    async def __call__(self, message: Union[Message, CallbackQuery]) -> bool:
        if isinstance(message, CallbackQuery):
            user_id = message.from_user.id
        else:
            user_id = message.from_user.id

        async with async_session() as session:
            ops = await get_operators(session, company_id=1)
        return any(int(op.telegram_id) == user_id for op in ops)


# --- 3) Фильтр IsUser (ни админ, ни оператор) ---
class IsUser(BaseFilter):
    async def __call__(self, message: Union[Message, CallbackQuery]) -> bool:
        if isinstance(message, CallbackQuery):
            user_id = message.from_user.id
        else:
            user_id = message.from_user.id

        # Если админ — не пользователь
        if user_id in config.get_admin_list:
            return False

        # Если оператор — не пользователь
        async with async_session() as session:
            ops = await get_operators(session, company_id=1)
        if any(int(op.telegram_id) == user_id for op in ops):
            return False

        return True
