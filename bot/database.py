# bot/database.py
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from bot.config import config

# Создаём движок
engine = create_async_engine(
    config.database_url,
    echo=False,  # можно включить для отладки SQL-запросов
    future=True,
)

# Фабрика асинхронных сессий
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
Base = declarative_base()
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
