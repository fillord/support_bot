# bot/utils.py

from aiogram import Bot
from bot.crud import get_operators
from bot.database import async_session

async def notify_operators(bot: Bot, company_id: int, ticket_id: int, ticket_text: str):
    """
    Уведомляет всех активных операторов о новом тикете.
    Можно сделать текст вида: "Новый тикет #ID: текст (первые 50 символов). 
    Для принятия нажмите /take_ticket_<ID>"
    """
    async with async_session() as session:
        operators = await get_operators(session, company_id)
    if not operators:
        return
    for op in operators:
        try:
            await bot.send_message(
                chat_id=int(op.telegram_id),
                text=(
                    f"🆕 *Новый тикет* #{ticket_id}\n"
                    f"Текст: {ticket_text[:100]}...\n\n"
                    f"Чтобы принять: нажмите /take_ticket_{ticket_id}"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            # Логируем ошибку, если, например, бот заблокирован оператором
            print(f"Не удалось уведомить оператора {op.telegram_id}: {e}")
