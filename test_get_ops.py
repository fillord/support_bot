# test_get_ops.py

import asyncio
from bot.crud import get_active_operator_ids

async def main():
    ops = await get_active_operator_ids(1)
    print("⊛ Результат get_active_operator_ids(1):", ops)

if __name__ == "__main__":
    asyncio.run(main())
