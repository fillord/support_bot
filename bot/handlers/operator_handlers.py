# bot/handlers/operator_handlers.py

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.database import async_session
from bot.crud import (
    get_open_tickets,
    get_ticket_by_id,
    assign_ticket,
    get_tickets_by_operator,
    close_ticket
)
from bot.keyboards import (
    operator_main_menu,
    operator_tickets_keyboard,
    ticket_actions_keyboard,
    select_ticket_keyboard,
    operator_my_tickets_keyboard
)
from bot.states import OperatorStates

router = Router()

# 0) /start_operator → показывает ReplyKeyboard меню оператора
@router.message(Command("start_operator"))
async def cmd_start_operator(message: Message):
    await message.answer(
        "Система техподдержки — меню оператора. Выберите действие:",
        reply_markup=operator_main_menu()
    )

@router.message(Command("tickets"))
async def cmd_list_tickets_command(message: Message):
    """
    Позволяет оператору вызвать список открытых тикетов командой /tickets,
    если он не хочет нажимать кнопку “📋 Открытые тикеты”.
    """
    await show_open_tickets(message)

# 1) Reply “📋 Открытые тикеты” (эквивалент /tickets)
@router.message(F.text == "📋 Открытые тикеты")
async def show_open_tickets(message: Message):
    operator_id = str(message.from_user.id)
    company_id = 1
    async with async_session() as session:
        open_tickets = await get_open_tickets(session, company_id)
        simplified = [(t.id, t.question_text) for t in open_tickets]

    if not simplified:
        await message.answer("Пока нет новых тикетов.")
        return

    await message.answer(
        "Список открытых тикетов:",
        reply_markup=operator_tickets_keyboard(simplified)
    )

# 2) Reply “📂 Мои тикеты” (эквивалент /my_tickets)
@router.message(F.text == "📂 Мои тикеты")
async def show_my_tickets(message: Message):
    operator_id = str(message.from_user.id)
    company_id = 1
    async with async_session() as session:
        tickets = await get_tickets_by_operator(session, operator_id, company_id)
        simplified = [(t.id, t.question_text) for t in tickets]

    if not simplified:
        await message.answer("У вас нет активных тикетов.")
        return

    await message.answer(
        "Ваши активные тикеты:",
        reply_markup=operator_my_tickets_keyboard(simplified)
    )

# 2.2) Хэндлер команды /my_tickets (если захотите вручную вводить /my_tickets)
@router.message(Command("my_tickets"))
async def cmd_list_my_tickets_command(message: Message):
    await show_my_tickets(message)


# ───────────────────────────────────────────────────────────────────────────────
# 3) Когда оператор нажал на кнопку тикета из списка Открытые: callback_data="open_ticket:<ticket_id>"
@router.callback_query(F.data.startswith("open_ticket:"))
async def handle_open_ticket(callback_query: CallbackQuery):
    """
    Показывает окно действий (Принять/Закрыть/Назад) для тикета,
    выбранного из списка Открытых тикетов.
    """
    ticket_id = int(callback_query.data.split(":")[1])
    # Рисуем инлайн-кнопки с origin="open"
    await callback_query.message.edit_text(
        f"Тикет #{ticket_id}: выберите действие",
        reply_markup=ticket_actions_keyboard(ticket_id, origin="open")
    )
    await callback_query.answer()


# ───────────────────────────────────────────────────────────────────────────────
# 4) Когда оператор нажал на кнопку тикета из списка Мои тикеты: callback_data="my_ticket:<ticket_id>"
@router.callback_query(F.data.startswith("my_ticket:"))
async def handle_my_ticket(callback_query: CallbackQuery):
    """
    Показывает окно действий (Принять/Закрыть/Назад) для тикета,
    выбранного из списка Мои тикеты.
    """
    ticket_id = int(callback_query.data.split(":")[1])
    # Рисуем инлайн-кнопки с origin="my"
    await callback_query.message.edit_text(
        f"Тикет #{ticket_id}: выберите действие",
        reply_markup=ticket_actions_keyboard(ticket_id, origin="my")
    )
    await callback_query.answer()


# 3) Reply “🔄 Переключить тикет” (эквивалент /select_ticket)
@router.message(F.text == "🔄 Переключить тикет")
async def prompt_select_ticket(message: Message):
    operator_id = str(message.from_user.id)
    company_id = 1
    async with async_session() as session:
        tickets = await get_tickets_by_operator(session, operator_id, company_id)
        simplified = [(t.id, t.question_text) for t in tickets]

    if not simplified:
        await message.answer("У вас нет активных тикетов для переключения.")
        return

    await message.answer(
        "Выберите тикет, в который хотите перейти:",
        reply_markup=select_ticket_keyboard(simplified)
    )

# 4) Callback “select:<id>” – оператор выбрал «текущий» тикет
@router.callback_query(F.data.startswith("select:"))
async def handle_select_ticket(callback_query: CallbackQuery, state: FSMContext):
    data = callback_query.data.split(":")
    action = data[1]  # либо "back", либо "<ticket_id>"
    operator_id = str(callback_query.from_user.id)
    company_id = 1

    if action == "back":
        await callback_query.message.edit_text(
            "Возвращаемся в меню оператора.",
            reply_markup=None
        )
        await callback_query.message.answer("Меню оператора:", reply_markup=operator_main_menu())
        await callback_query.answer()
        return

    ticket_id = int(action)
    async with async_session() as session:
        tickets = await get_tickets_by_operator(session, operator_id, company_id)
        ids = [t.id for t in tickets]
    if ticket_id not in ids:
        await callback_query.message.edit_text("У вас нет такого активного тикета.")
        await callback_query.answer()
        return

    await state.update_data(current_ticket=ticket_id)
    await state.set_state(OperatorStates.chatting)
    await callback_query.message.edit_text(f"✅ Переключились на тикет #{ticket_id}. Ваши сообщения пойдут клиенту.")
    await callback_query.answer()

# 5) Callback “ticket:<id>” – показать кнопки «Принять/Закрыть/Назад»
@router.callback_query(F.data.startswith("ticket:"))
async def show_ticket_actions(callback_query: CallbackQuery):
    ticket_id = int(callback_query.data.split(":")[1])
    await callback_query.message.edit_reply_markup(
        reply_markup=ticket_actions_keyboard(ticket_id)
    )
    await callback_query.answer()

# 6) Callback “ticket_action:assign:<id>” / “ticket_action:close:<id>”
@router.callback_query(F.data.startswith("ticket_action:"))
async def handle_ticket_action(callback_query: CallbackQuery, state: FSMContext):
    parts = callback_query.data.split(":")
    action = parts[1]   # "assign" или "close"
    ticket_id = int(parts[2])
    operator_id = str(callback_query.from_user.id)
    company_id = 1

    async with async_session() as session:
        ticket = await get_ticket_by_id(session, ticket_id)
        if not ticket or ticket.company_id != company_id:
            await callback_query.message.answer("Тикет не найден или не к вашей компании.")
            await callback_query.answer()
            return

        if action == "assign":
            if ticket.status != "open":
                await callback_query.message.answer("Этот тикет уже взят или закрыт.")
                await callback_query.answer()
                return

            # 5.1) Принимаем тикет, переводим в in_progress и сохраняем в FSMContext
            await assign_ticket(session, ticket_id, operator_id)
            await state.update_data(current_ticket=ticket_id)
            await state.set_state(OperatorStates.chatting)

            # 5.2) Отправляем оператору сообщение, что тикет принят
            await callback_query.message.answer(
                f"✅ Вы приняли тикет #{ticket_id}. Теперь ваши сообщения пойдут клиенту."
            )
            # 5.3) Сразу пересылаем оператору исходное сообщение клиента
            await callback_query.message.answer(
                f"✉️ Сообщение от клиента:\n\n{ticket.question_text}"
            )
            # 5.4) Уведомляем клиента в Telegram, что его тикет взят в работу
            await callback_query.bot.send_message(
                chat_id=int(ticket.user_id),
                text=f"Оператор взялся за ваш тикет #{ticket_id}. Сейчас можете спрашивать."
            )
            await callback_query.answer()
            return

        elif action == "close":
            # 5.5) Закрытие тикета
            if ticket.operator_id != operator_id:
                await callback_query.message.answer("Вы не закреплены за этим тикетом.")
                await callback_query.answer()
                return

            await close_ticket(session, ticket_id)

            data = await state.get_data()
            current = data.get("current_ticket")
            if current == ticket_id:
                await state.clear()
                await callback_query.message.answer(f"✅ Тикет #{ticket_id} закрыт. Вы не связаны ни с одним тикетом.")
            else:
                await callback_query.message.answer(f"✅ Тикет #{ticket_id} закрыт.")

            await callback_query.bot.send_message(
                chat_id=int(ticket.user_id),
                text=f"Ваш тикет #{ticket_id} был закрыт оператором. Спасибо за обращение!"
            )
            await callback_query.answer()
            return

        else:
            await callback_query.answer()

# 7) Callback “tickets:refresh” – обновить список открытых тикетов
@router.callback_query(F.data == "tickets:refresh")
async def refresh_tickets_list(callback_query: CallbackQuery):
    company_id = 1
    async with async_session() as session:
        open_tickets = await get_open_tickets(session, company_id)
        simplified = [(t.id, t.question_text) for t in open_tickets]

    if not simplified:
        await callback_query.message.edit_text("Пока нет новых тикетов.")
    else:
        await callback_query.message.edit_text(
            "Список открытых тикетов:",
            reply_markup=operator_tickets_keyboard(simplified)
        )
    await callback_query.answer()

# 8) Callback “tickets:back” – выйти из списка открытых тикетов и вернуть ReplyKeyboard
@router.callback_query(F.data == "tickets:back")
async def go_back_from_tickets(callback_query: CallbackQuery):
    await callback_query.message.edit_text("Возвращаемся в меню оператора.")
    await callback_query.message.answer("Меню оператора:", reply_markup=operator_main_menu())
    await callback_query.answer()

# 8) Обработчик «🔙 Назад» когда мы в actions-окне для Open Tickets:
@router.callback_query(F.data == "back_to_open")
async def back_to_open_list(callback_query: CallbackQuery):
    """
    Возвращаемся к списку Открытых тикетов (Open Tickets).
    То есть заново показываем operator_tickets_keyboard.
    """
    company_id = 1
    async with async_session() as session:
        open_tickets = await get_open_tickets(session, company_id)
        simplified = [(t.id, t.question_text) for t in open_tickets]

    if not simplified:
        await callback_query.message.edit_text("Пока нет новых тикетов.")
    else:
        await callback_query.message.edit_text(
            "Список открытых тикетов:",
            reply_markup=operator_tickets_keyboard(simplified)
        )
    await callback_query.answer()


# ───────────────────────────────────────────────────────────────────────────────
# 9) Обработчик «🔙 Назад» когда мы в actions-окне для My Tickets:
@router.callback_query(F.data == "back_to_my")
async def back_to_my_list(callback_query: CallbackQuery):
    """
    Возвращаемся к списку «Моих тикетов» (in_progress).
    То есть заново показываем operator_my_tickets_keyboard.
    """
    operator_id = str(callback_query.from_user.id)
    company_id = 1
    async with async_session() as session:
        tickets = await get_tickets_by_operator(session, operator_id, company_id)
        simplified = [(t.id, t.question_text) for t in tickets]

    if not simplified:
        # Если вдруг все тикеты закрыты, можно вывести сообщение
        await callback_query.message.edit_text("У вас нет активных тикетов.")
    else:
        await callback_query.message.edit_text(
            "Ваши активные тикеты:",
            reply_markup=operator_my_tickets_keyboard(simplified)
        )
    await callback_query.answer()


# 9) “Ловушка” для любых текстов оператора – пересылаем текущему клиенту
@router.message(~F.text.startswith("/"))
async def forward_messages_between(message: Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = data.get("current_ticket")

    if not ticket_id:
        await message.answer(
            "⚠️ У вас нет текущего тикета.\n"
            "Чтобы начать, нажмите «📋 Открытые тикеты» или выберите нужный через «🔄 Переключить тикет»."
        )
        return

    async with async_session() as session:
        ticket = await get_ticket_by_id(session, ticket_id)

    if not ticket:
        await state.clear()
        await message.answer("Текущий тикет не найден. Выберите новый.")
        return

    await message.bot.send_message(
        chat_id=int(ticket.user_id),
        text=f"💬 Оператор: {message.text}"
    )
