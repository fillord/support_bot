# bot/handlers/admin_handlers.py

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import config
from bot.database import async_session
from bot.crud import (
    create_faq_entry,
    delete_faq_entry,
    update_faq_entry,
    get_faq_entries,
    add_operator,
    deactivate_operator,
    get_operators
)

router = Router()


def admin_only(handler):
    async def wrapper(message: Message, *args, **kwargs):
        user_id = message.from_user.id
        if user_id not in config.get_admin_list:
            await message.answer("⛔ У вас нет прав для выполнения этой команды.")
            return
        return await handler(message)
    return wrapper


@router.message(Command("add_operator"))
@admin_only
async def cmd_add_operator(message: Message):
    text = message.text or ""
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "Неверный формат. Используйте:\n"
            "/add_operator <telegram_id> <имя>\n\n"
            "Пример: /add_operator 7171742441 Иван Иванов"
        )
        return

    _, tg_id, full_name = parts
    if not tg_id.isdigit():
        await message.answer("Неверный Telegram ID. Должны быть только цифры.")
        return

    company_id = 1
    async with async_session() as session:
        await add_operator(session, company_id, telegram_id=tg_id, full_name=full_name)
    await message.answer(f"✅ Оператор {full_name} (ID={tg_id}) добавлен.")


@router.message(Command("remove_operator"))
@admin_only
async def cmd_remove_operator(message: Message):
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Неверный формат. Используйте /remove_operator <telegram_id>")
        return

    tg_id = parts[1]
    company_id = 1
    async with async_session() as session:
        operators = await get_operators(session, company_id)
        op = next((o for o in operators if o.telegram_id == tg_id), None)
        if not op:
            await message.answer("Оператор с таким ID не найден.")
            return
        await deactivate_operator(session, op.id)
    await message.answer(f"✅ Оператор {tg_id} отключён.")


@router.message(Command("add_faq"))
@admin_only
async def cmd_add_faq(message: Message):
    text = message.text or ""
    args = text[len("/add_faq"):].strip()
    if "|" not in args:
        await message.answer("Неверный формат. Используйте:\n/add_faq Вопрос? | Ответ")
        return

    question, answer = [part.strip() for part in args.split("|", maxsplit=1)]
    if not question or not answer:
        await message.answer("И вопрос, и ответ должны быть непустыми.")
        return

    company_id = 1
    async with async_session() as session:
        faq = await create_faq_entry(session, company_id, question, answer)
    await message.answer(f"✅ Добавлен новый пункт FAQ: #{faq.id}")


@router.message(Command("del_faq"))
@admin_only
async def cmd_del_faq(message: Message):
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Неверный формат. Используйте /del_faq <id>")
        return

    entry_id = int(parts[1])
    async with async_session() as session:
        await delete_faq_entry(session, entry_id)
    await message.answer(f"✅ Удалён пункт FAQ #{entry_id}")


@router.message(Command("edit_faq"))
@admin_only
async def cmd_edit_faq(message: Message):
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Неверный формат. Используйте:\n/edit_faq <id> Вопрос? | Ответ"
        )
        return

    rest = parts[1].strip()
    try:
        id_str, qa = rest.split(maxsplit=1)
        entry_id = int(id_str)
    except Exception:
        await message.answer("Неверный формат. Правильно: /edit_faq <id> Вопрос? | Ответ")
        return

    if "|" not in qa:
        await message.answer("Неверный формат. Между вопросом и ответом нужен символ '|'.")
        return

    question, answer = [part.strip() for part in qa.split("|", maxsplit=1)]
    if not question or not answer:
        await message.answer("И вопрос, и ответ должны быть непустыми.")
        return

    async with async_session() as session:
        await update_faq_entry(session, entry_id, question, answer)
    await message.answer(f"✅ Обновлён пункт FAQ #{entry_id}")


@router.message(Command("list_faq"))
@admin_only
async def cmd_list_faq(message: Message):
    company_id = 1
    async with async_session() as session:
        entries = await get_faq_entries(session, company_id)

    if not entries:
        await message.answer("Сейчас в FAQ нет ни одного пункта.")
        return

    text = "<b>Список текущих FAQ:</b>\n"
    for entry in entries:
        text += f"{entry.id}. {entry.question}\n"
    await message.answer(text)
