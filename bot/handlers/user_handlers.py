# bot/handlers/user_handlers.py

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.database import async_session
from bot.crud import (
    get_faq_entries,
    get_faq_by_id,
    get_faq_by_keyword,
    create_ticket,
    create_or_update_user_session,
    get_user_session,
    delete_user_session,
    get_active_operator_ids,
    get_active_ticket_by_user   # ← импорт нашей новой функции
)
from bot.keyboards import main_menu_keyboard, faq_list_keyboard, operator_tickets_keyboard, ticket_actions_keyboard
from bot.states import OperatorStates

router = Router()

# === Обработка команды /start ===

@router.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        f"Здравствуйте, {message.from_user.full_name}!\n"
        "Я бот техподдержки. Чем могу помочь?\n\n"
        "Выберите действие ниже:"
    )
    # Отправляем пользователю главное меню (ReplyKeyboardMarkup)
    await message.answer(text, reply_markup=main_menu_keyboard())


# === Кнопка “📚 FAQ” ===

@router.message(F.text == "📚 FAQ")
async def show_faq_list(message: Message):
    company_id = 1  # пока жёстко, потом можно брать из базы

    # Получаем все записи FAQ для компании
    async with async_session() as session:
        faqs = await get_faq_entries(session, company_id)
        simplified = [(f.id, f.question) for f in faqs]

    if not simplified:
        await message.answer("Извините, у нас пока нет доступных вопросов.")
        return

    # Сохраняем, что пользователь сейчас в состоянии “browsing_faq”
    async with async_session() as session:
        await create_or_update_user_session(
            session,
            user_id=str(message.from_user.id),
            company_id=company_id,
            state="browsing_faq"
        )

    # Отправляем список вопросов в виде Inline-клавиатуры
    await message.answer(
        "Выберите вопрос из списка:",
        reply_markup=faq_list_keyboard(simplified)
    )


# === Обработка нажатий по FAQ (callback_data “faq:{id}” или “faq:back”) ===

@router.callback_query(F.data.startswith("faq:"))
async def handle_faq_selection(callback: CallbackQuery):
    data = callback.data.split(":")
    action = data[1]
    user_id = str(callback.from_user.id)
    company_id = 1

    if action == "back":
        async with async_session() as session:
            await delete_user_session(session, user_id)
        await callback.message.answer("Возвращаемся в главное меню.", reply_markup=main_menu_keyboard())
        await callback.answer()
        return

    entry_id = int(action)
    async with async_session() as session:
        entry = await get_faq_by_id(session, entry_id)

    if entry:
        await callback.message.answer(entry.answer, reply_markup=main_menu_keyboard())
    else:
        await callback.message.answer("К сожалению, ответ не найден.", reply_markup=main_menu_keyboard())

    async with async_session() as session:
        await delete_user_session(session, user_id)

    await callback.answer()


# === Кнопка “👨‍💻 Связаться с оператором” ===

@router.message(F.text == "👨‍💻 Связаться с оператором")
async def start_ticket_flow(message: Message):
    user_id = str(message.from_user.id)
    company_id = 1

    async with async_session() as session:
        await create_or_update_user_session(
            session,
            user_id=user_id,
            company_id=company_id,
            state="awaiting_ticket_text"
        )

    await message.answer(
        "Опишите свою проблему (напишите текст сообщения). Один из операторов свяжется с вами в ближайшее время."
    )


# === Кнопка “ℹ️ О компании” ===

@router.message(F.text == "ℹ️ О компании")
async def show_info_about_company(message: Message):
    text = (
        "📄 *О нашей компании*\n\n"
        "Мы — компания «Название».\n"
        "Предоставляем круглосуточную техническую поддержку.\n"
        "Наши операторы на связи 24/7.\n"
        "Адрес: ул. Примерная, д. 123, г. Город.\n"
        "Телефон: +7 (123) 456-78-90\n"
        "Сайт: https://example.com\n\n"
        "_Если у вас остались вопросы, выберите действие из меню ниже:_"
    )
    await message.answer(text, reply_markup=main_menu_keyboard())


# === “Ловушка” для всего остального текста (не начинающегося с “/”) ===

@router.message(~F.text.startswith("/"))
async def handle_text_during_states(message: Message):
    user_id = str(message.from_user.id)
    # Получаем текущее состояние клиента (если есть)
    async with async_session() as session:
        us = await get_user_session(session, user_id)

    # 1) Если клиент находится в режиме ввода текста для нового тикета
    if us and us.state == "awaiting_ticket_text":
        question_text = message.text.strip()

        # 1.1) Создаём тикет
        async with async_session() as session:
            ticket = await create_ticket(
                session,
                company_id=us.company_id,
                user_id=user_id,
                question_text=question_text
            )

        # 1.2) Разсылаем оповещение всем активным операторам
        operator_ids = await get_active_operator_ids(us.company_id)
        print(f"[DEBUG user_handlers] operator_ids = {operator_ids}, ticket.id = {ticket.id}")

        notif_text = (
            f"📥 <b>Новый тикет #{ticket.id}</b>:\n\n"
            f"{ticket.question_text}\n\n"
            "Чтобы посмотреть список открытых тикетов, нажмите /tickets"
        )
        for op_id in operator_ids:
            try:
                print(f"[DEBUG user_handlers] Шлю уведомление оператору с ID={op_id}")
                await message.bot.send_message(
                    chat_id=op_id,
                    text=notif_text,
                    reply_markup=ticket_actions_keyboard(ticket.id, origin="open")
                )
            except Exception as e:
                print(f"[ERROR user_handlers] Не удалось отправить уведомление operator_id={op_id}: {e}")
                continue

        # 1.3) Удаляем состояние клиента (он завершил ввод проблемы)
        async with async_session() as session:
            await delete_user_session(session, user_id)

        # --- ШАГ 4: Отвечаем клиенту, что тикет зарегистрирован ---
        await message.answer(
            "Ваш запрос зарегистрирован. Операторы уведомлены и скоро свяжутся с вами.",
            reply_markup=main_menu_keyboard()
        )
        return  # дальше не идём, т.к. уже создали тикет

    # 2) Если клиент находится в режиме «просмотра FAQ»
    if us and us.state == "browsing_faq":
        keyword = message.text.strip()
        async with async_session() as session:
            results = await get_faq_by_keyword(session, us.company_id, keyword)

        if results:
            text = "Найдены следующие вопросы:\n\n"
            simplified = []
            for entry in results:
                text += f"• {entry.question}\n"
                simplified.append((entry.id, entry.question))
            await message.answer(text, reply_markup=faq_list_keyboard(simplified))
        else:
            await message.answer(
                "Ничего не найдено по вашему запросу. "
                "Попробуйте другое слово или нажмите \"🔙 Назад\" для возврата."
            )
        return

    # 3) НОВАЯ ЛОГИКА: если у клиента есть тикет со статусом in_progress —
    #    пересылаем любое его сообщение оператору, назначенному за тикетом.
    async with async_session() as session:
        active_ticket = await get_active_ticket_by_user(session, user_id)
    if active_ticket:
        # Пересылаем текст оператору
        operator_chat_id = int(active_ticket.operator_id)
        await message.bot.send_message(
            chat_id=operator_chat_id,
            text=f"💬 Клиент #{active_ticket.id}: {message.text}"
        )
        return

    # 4) Иначе (если ни FAQ, ни awaiting_ticket_text, ни in_progress) —
    #    просто шлём главное меню клиенту
    await message.answer(
        "Извините, я не распознал запрос. Пожалуйста, выберите действие из меню.",
        reply_markup=main_menu_keyboard()
    )
# Дальше — ваш отладочный «ловец» (необязательный)
@router.message()
async def catch_all(message: Message):
    print(f"Необработанное сообщение: {repr(message.text)}")

@router.message(Command("test_kb"))
async def test_kb(message: Message):
    kb = main_menu_keyboard()
    print("Клавиатура:", kb)
    await message.answer("Тест клавиатуры", reply_markup=kb)