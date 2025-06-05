# bot/crud.py

import json
from typing import List, Optional

from sqlalchemy.future import select
from sqlalchemy import update, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession      # ← добавили этот импорт

from bot.database import async_session
from bot.models import Company, FAQEntry, Operator, Ticket, UserSession
from bot.models import Ticket

async def get_active_ticket_by_user(session, user_id: str) -> Optional[Ticket]:
    """
    Возвращает тикет в статусе 'in_progress' для данного клиента (user_id),
    или None, если такого нет.
    """
    result = await session.execute(
        select(Ticket).where(
            Ticket.user_id == user_id,
            Ticket.status == "in_progress"
        )
    )
    return result.scalars().first()
# +++ НОВАЯ ФУНКЦИЯ: get_active_operator_ids +++
async def get_active_operator_ids(company_id: int) -> List[int]:
    """
    Возвращает список telegram_id (int) всех операторов с is_active=True для данной компании.
    """
    print(f"[DEBUG get_active_operator_ids] Запрашиваю операторов для company_id={company_id}")
    async with async_session() as session:
        result = await session.execute(
            select(Operator.telegram_id).where(
                Operator.company_id == company_id,
                Operator.is_active == True
            )
        )
        rows = result.all()
    ids = [int(r[0]) for r in rows]
    print(f"[DEBUG get_active_operator_ids] Найдено telegram_id операторов: {ids}")
    return ids

# === COMPANY ===

async def get_or_create_company(session: AsyncSession, name: str) -> Company:
    """
    Получаем или создаём компанию по имени.
    """
    result = await session.execute(select(Company).where(Company.name == name))
    company = result.scalars().first()
    if not company:
        company = Company(name=name)
        session.add(company)
        await session.commit()
        await session.refresh(company)
    return company


# === FAQ ===

async def get_faq_entries(session: AsyncSession, company_id: int) -> List[FAQEntry]:
    result = await session.execute(
        select(FAQEntry).where(FAQEntry.company_id == company_id)
    )
    return result.scalars().all()


async def get_faq_by_id(session: AsyncSession, entry_id: int) -> Optional[FAQEntry]:
    result = await session.execute(
        select(FAQEntry).where(FAQEntry.id == entry_id)
    )
    return result.scalars().first()


async def get_faq_by_keyword(session: AsyncSession, company_id: int, keyword: str) -> List[FAQEntry]:
    result = await session.execute(
        select(FAQEntry).where(
            FAQEntry.company_id == company_id,
            or_(
                FAQEntry.question.ilike(f"%{keyword}%"),
                FAQEntry.answer.ilike(f"%{keyword}%")
            )
        )
    )
    return result.scalars().all()


async def create_faq_entry(session: AsyncSession, company_id: int, question: str, answer: str) -> FAQEntry:
    new_entry = FAQEntry(company_id=company_id, question=question, answer=answer)
    session.add(new_entry)
    await session.commit()
    await session.refresh(new_entry)
    return new_entry


async def delete_faq_entry(session: AsyncSession, entry_id: int) -> None:
    await session.execute(delete(FAQEntry).where(FAQEntry.id == entry_id))
    await session.commit()


async def update_faq_entry(session: AsyncSession, entry_id: int, question: str, answer: str) -> None:
    await session.execute(
        update(FAQEntry)
        .where(FAQEntry.id == entry_id)
        .values(question=question, answer=answer)
    )
    await session.commit()


# === OPERATOR ===

async def add_operator(
    session: AsyncSession,
    company_id: int,
    telegram_id: str,
    full_name: str
) -> Operator:
    """
    Если оператор с таким telegram_id уже существует (в любых статусах), 
    то просто выставляем ему is_active=True и обновляем full_name (если нужно).
    Если не найден — создаём новый.
    """
    # 1) Попробуем найти оператора с таким telegram_id
    result = await session.execute(
        select(Operator).where(Operator.telegram_id == telegram_id)
    )
    existing = result.scalars().first()

    if existing:
        # Если такой оператор есть, даже если он был отключён (is_active=False),
        # просто обновляем у него флаг и, при желании, имя.
        existing.is_active = True
        existing.full_name = full_name  # обновляем имя, если оно могло измениться
        # company_id, скорее всего, не меняется, но если нужна логика “несколько компаний” – можно добавить.
        await session.commit()
        await session.refresh(existing)
        return existing

    # 2) Если оператора нет, создаём нового
    new_op = Operator(
        company_id=company_id,
        telegram_id=telegram_id,
        full_name=full_name,
        is_active=True
    )
    session.add(new_op)
    await session.commit()
    await session.refresh(new_op)
    return new_op

async def get_operators(session: AsyncSession, company_id: int) -> List[Operator]:
    result = await session.execute(
        select(Operator).where(Operator.company_id == company_id, Operator.is_active == True)
    )
    return result.scalars().all()



async def deactivate_operator(session: AsyncSession, operator_id: int) -> None:
    """
    Снимаем is_active у оператора, то есть "отключаем" его.
    """
    await session.execute(
        update(Operator).where(Operator.id == operator_id).values(is_active=False)
    )
    await session.commit()


# === TICKETS ===

async def create_ticket(
    session: AsyncSession,
    company_id: int,
    user_id: str,
    question_text: str
) -> Ticket:
    new_ticket = Ticket(company_id=company_id, user_id=user_id, question_text=question_text, status="open")
    session.add(new_ticket)
    await session.commit()
    await session.refresh(new_ticket)
    return new_ticket


async def get_open_tickets(session: AsyncSession, company_id: int) -> List[Ticket]:
    result = await session.execute(
        select(Ticket).where(Ticket.company_id == company_id, Ticket.status == "open")
    )
    return result.scalars().all()


async def get_ticket_by_id(session: AsyncSession, ticket_id: int) -> Optional[Ticket]:
    result = await session.execute(
        select(Ticket).where(Ticket.id == ticket_id)
    )
    return result.scalars().first()


async def assign_ticket(session: AsyncSession, ticket_id: int, operator_id: str) -> None:
    await session.execute(
        update(Ticket)
        .where(Ticket.id == ticket_id)
        .values(operator_id=operator_id, status="in_progress")
    )
    await session.commit()


async def get_tickets_by_operator(session: AsyncSession, operator_id: str, company_id: int) -> List[Ticket]:
    result = await session.execute(
        select(Ticket).where(Ticket.operator_id == operator_id, Ticket.company_id == company_id, Ticket.status == "in_progress")
    )
    return result.scalars().all()


async def close_ticket(session: AsyncSession, ticket_id: int) -> None:
    await session.execute(
        update(Ticket).where(Ticket.id == ticket_id).values(status="closed")
    )
    await session.commit()


# === USER SESSION ===

async def create_or_update_user_session(
    session: AsyncSession,
    user_id: str,
    company_id: int,
    state: str
) -> UserSession:
    """
    Если сессия уже есть, обновляем state. Если нет — создаём.
    """
    result = await session.execute(
        select(UserSession).where(UserSession.user_id == user_id, UserSession.company_id == company_id)
    )
    us = result.scalars().first()
    if not us:
        us = UserSession(user_id=user_id, company_id=company_id, state=state)
        session.add(us)
    else:
        us.state = state
    await session.commit()
    await session.refresh(us)
    return us


async def get_user_session(session: AsyncSession, user_id: str) -> Optional[UserSession]:
    result = await session.execute(
        select(UserSession).where(UserSession.user_id == user_id)
    )
    return result.scalars().first()


async def delete_user_session(session: AsyncSession, user_id: str) -> None:
    await session.execute(delete(UserSession).where(UserSession.user_id == user_id))
    await session.commit()
