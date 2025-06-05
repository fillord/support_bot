# bot/models.py

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, ForeignKey, DateTime
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    # При необходимости можно добавить домен, логотип, настройки и т.д.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связанные объекты:
    faq_entries = relationship("FAQEntry", back_populates="company", cascade="all, delete-orphan")
    operators = relationship("Operator", back_populates="company", cascade="all, delete-orphan")

class FAQEntry(Base):
    __tablename__ = "faq_entries"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    question = Column(String(255), nullable=False)
    answer = Column(Text, nullable=False)
    # Можно завести поле tags = Column(String(255)), чтобы “тегировать” вопросы для быстрого поиска
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="faq_entries")

class Operator(Base):
    __tablename__ = "operators"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    telegram_id = Column(String(32), nullable=False, unique=True)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="operators")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    user_id = Column(String(32), nullable=False)       # Telegram user_id клиента
    operator_id = Column(String(32), nullable=True)    # Telegram user_id оператора, когда взял тикет
    question_text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="open")  
        # “open” (новый, не назначен), “in_progress” (принят оператором), “closed”
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # company и оператор можно подключить через relationship, но для простоты достаточно хранить поля.

class UserSession(Base):
    """
    Вспомогательная таблица для хранения состояния взаимодействия клиента с ботом.
    Например, клиент выбрал FAQ, но ещё не ввёл текст, или находится в режиме переписки с оператором.
    """
    __tablename__ = "user_sessions"

    user_id = Column(String(32), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    state = Column(String(50), nullable=True)  
      # Пример состояний: "browsing_faq", "contacting_operator", "in_ticket#42", "admin_mode"
    data = Column(Text, nullable=True)  
      # Дополнительные данные в формате JSON, если нужно хранить промежуточный контекст
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company = relationship("Company")
