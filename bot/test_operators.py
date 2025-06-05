from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from bot.models import Operator
import asyncio

async def test_operators():
    engine = create_async_engine("sqlite+aiosqlite:///F:/Project/support_bot/support_bot.db", echo=False)
    async with AsyncSession(engine) as session:
        q = await session.execute(select(Operator).where(Operator.is_active == True, Operator.company_id == 1))
        ops = q.scalars().all()
        print("Активные операторы из БД:", ops)
        print([op.telegram_id for op in ops])

asyncio.run(test_operators())
