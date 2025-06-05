# bot/keyboards.py

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)


# === Главное меню (ReplyKeyboardMarkup) ===
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 FAQ")],
            [KeyboardButton(text="👨‍💻 Связаться с оператором")],
            [KeyboardButton(text="ℹ️ О компании")]
        ],
        resize_keyboard=True
    )
    return kb


# === Inline-клавиатура для списка FAQ ===
def faq_list_keyboard(faq_entries: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """
    faq_entries = [(id1, "Вопрос1"), (id2, "Вопрос2"), ...]
    Построим inline_keyboard как список списков:
    [
      [InlineKeyboardButton(text="Вопрос1", callback_data="faq:1")],
      [InlineKeyboardButton(text="Вопрос2", callback_data="faq:2")],
      ...
      [InlineKeyboardButton(text="🔙 Назад", callback_data="faq:back")]
    ]
    """
    # Сначала формируем «двумерный» список рядов (каждый ряд — это список из одной кнопки)
    rows: list[list[InlineKeyboardButton]] = []
    for entry_id, question_text in faq_entries:
        rows.append([
            InlineKeyboardButton(
                text=question_text,
                callback_data=f"faq:{entry_id}"
            )
        ])
    # Добавляем в конце кнопку «Назад» (её тоже кладём в собственный ряд)
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="faq:back")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# === Inline-клавиатура для списка открытых тикетов у оператора ===
def operator_tickets_keyboard(tickets: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """
    tickets: список кортежей (ticket_id, ticket_preview)
    Формирует InlineKeyboard для Open Tickets:
      • для каждого тикета — кнопка с callback_data="open_ticket:<ticket_id>"
      • внизу две кнопки: 🔄 Обновить (callback_data="tickets:refresh") и 🔙 Назад (callback_data="tickets:back")
    """
    rows: list[list[InlineKeyboardButton]] = []
    for ticket_id, preview in tickets:
        rows.append([
            InlineKeyboardButton(
                text=f"Тикет #{ticket_id}: {preview[:30]}…",
                callback_data=f"open_ticket:{ticket_id}"
            )
        ])
    # Нижняя строка: «Обновить» + «Назад»
    rows.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="tickets:refresh"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="tickets:back")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# 3) inline-клавиатура для списка МОИХ тикетов (in_progress)
def operator_my_tickets_keyboard(tickets: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """
    tickets: список кортежей (ticket_id, ticket_preview)
    Формирует InlineKeyboard для My Tickets:
      • для каждого тикета — кнопка с callback_data="my_ticket:<ticket_id>"
      • внизу — только кнопка 🔙 Назад (callback_data="tickets:back")
    """
    rows: list[list[InlineKeyboardButton]] = []
    for ticket_id, preview in tickets:
        rows.append([
            InlineKeyboardButton(
                text=f"Тикет #{ticket_id}: {preview[:30]}…",
                callback_data=f"my_ticket:{ticket_id}"
            )
        ])
    # Нижняя строка: только «Назад»
    rows.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="tickets:back")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# === Inline-клавиатура внутри одного тикета (действия оператора) ===
def ticket_actions_keyboard(ticket_id: int, origin: str) -> InlineKeyboardMarkup:
    """
    Формирует InlineKeyboard с кнопками «Принять», «Закрыть», «Назад».
    origin: "open"   — из Open Tickets
            "my"     — из My Tickets
    В зависимости от origin, кнопка «Назад» получит разный callback_data:
      • если origin="open", то callback_data="back_to_open"
      • если origin="my",   то callback_data="back_to_my"
    """
    rows: list[list[InlineKeyboardButton]] = []

    # Кнопка «Принять тикет»
    rows.append([
        InlineKeyboardButton(
            text="✅ Принять тикет",
            callback_data=f"ticket_action:assign:{ticket_id}"
        )
    ])
    # Кнопка «Закрыть тикет»
    rows.append([
        InlineKeyboardButton(
            text="❌ Закрыть тикет",
            callback_data=f"ticket_action:close:{ticket_id}"
        )
    ])
    # Кнопка «Назад» — разная callback_data, в зависимости от origin
    if origin == "open":
        back_data = "back_to_open"
    else:  # origin == "my"
        back_data = "back_to_my"

    rows.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data=back_data)
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)

# +++ НОВОЕ: 5) ReplyKeyboardMarkup для операторов +++
def operator_main_menu() -> ReplyKeyboardMarkup:
    """
    Показывает три кнопки:
      📋 Открытые тикеты
      📂 Мои тикеты
      🔄 Переключить тикет
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Открытые тикеты")],
            [KeyboardButton(text="📂 Мои тикеты")],
            [KeyboardButton(text="🔄 Переключить тикет")]
        ],
        resize_keyboard=True
    )


# +++ НОВОЕ: 6) Inline-клавиатура для «Переключить тикет» +++
def select_ticket_keyboard(tickets: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """
    tickets = [(id1, preview1), (id2, preview2), ...], но это именно их in_progress-список.
    Формируем InlineKeyboard, где каждая кнопка — «Выбрать тикет #<id>»:
      [InlineKeyboardButton(text="Выбрать #5: <preview>...", callback_data="select:5")]
      [InlineKeyboardButton(text="Выбрать #7: <preview>...", callback_data="select:7")]
      [InlineKeyboardButton(text="🔙 Назад", callback_data="select:back")]
    """
    rows: list[list[InlineKeyboardButton]] = []
    for ticket_id, preview in tickets:
        rows.append([
            InlineKeyboardButton(
                text=f"Выбрать #{ticket_id}: {preview[:30]}...",
                callback_data=f"select:{ticket_id}"
            )
        ])
    # Кнопка «Назад» для отмены
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="select:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)