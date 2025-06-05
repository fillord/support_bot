# bot/main.py

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.database import init_models
from bot.handlers.admin_handlers import router as admin_router
from bot.handlers.operator_handlers import router as operator_router
from bot.handlers.user_handlers import router as user_router
from bot.filters import IsAdmin, IsOperator, IsUser


async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"Admin IDs loaded: {config.get_admin_list}")

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher(storage=MemoryStorage())

    # --- 1) Подключаем фильтр IsAdmin к admin_router
    admin_router.message.filter(IsAdmin())
    admin_router.callback_query.filter(IsAdmin())

    # --- 2) Подключаем фильтр IsOperator к operator_router
    operator_router.message.filter(IsOperator())
    operator_router.callback_query.filter(IsOperator())

    # --- 3) Подключаем фильтр IsUser к user_router
    user_router.message.filter(IsUser())
    user_router.callback_query.filter(IsUser())

    # После прикрепления фильтров — регистрируем роутеры в любом порядке:
    dp.include_router(admin_router)
    dp.include_router(operator_router)
    dp.include_router(user_router)

    # Создаём таблицы в БД при первом запуске
    await init_models()

    logger.info("Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
