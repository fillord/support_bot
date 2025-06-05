# bot/states.py

from aiogram.fsm.state import State, StatesGroup

class OperatorStates(StatesGroup):
    # Это состояние говорит, что оператор находится в режиме “отвечать клиенту”
    # и может использовать `current_ticket` из FSMContext, чтобы понимать, кому шлёт сообщение
    chatting = State()
