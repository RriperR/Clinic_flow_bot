import os
from datetime import date, datetime

from dotenv import load_dotenv
from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, select, String, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncAttrs, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


engine = create_async_engine(f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class AdminUser(Base):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(String(31), unique=True, nullable=False)
    added_at: Mapped[datetime | None] = mapped_column(DateTime)


class Worker(Base):
    __tablename__ = "workers"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    full_name: Mapped[str | None] = mapped_column(Text)
    file_id: Mapped[str | None] = mapped_column(String(255))
    chat_id: Mapped[str | None] = mapped_column(String(31))
    speciality: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(31))
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True)
    shifts_week: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shifts_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    given_week: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    given_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    replacement_week: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    replacement_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manual_week: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manual_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Pair(Base):
    __tablename__ = "pairs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subject: Mapped[str | None] = mapped_column(Text)
    object: Mapped[str | None] = mapped_column(Text)
    survey: Mapped[str | None] = mapped_column(Text)
    weekday: Mapped[str | None] = mapped_column(String(31))
    date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(15), default="ready")


class Survey(Base):
    __tablename__ = "surveys"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    speciality: Mapped[str | None] = mapped_column(String(511))
    question1: Mapped[str | None] = mapped_column(Text)
    question1_type: Mapped[str | None] = mapped_column(String(7))
    question2: Mapped[str | None] = mapped_column(Text)
    question2_type: Mapped[str | None] = mapped_column(String(7))
    question3: Mapped[str | None] = mapped_column(Text)
    question3_type: Mapped[str | None] = mapped_column(String(7))
    question4: Mapped[str | None] = mapped_column(Text)
    question4_type: Mapped[str | None] = mapped_column(String(7))
    question5: Mapped[str | None] = mapped_column(Text)
    question5_type: Mapped[str | None] = mapped_column(String(7))


class Answer(Base):
    __tablename__ = "answers"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subject: Mapped[str | None] = mapped_column(Text)
    object: Mapped[str | None] = mapped_column(Text)
    survey: Mapped[str | None] = mapped_column(Text)
    survey_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    question1: Mapped[str | None] = mapped_column(Text)
    answer1: Mapped[str | None] = mapped_column(Text)
    question2: Mapped[str | None] = mapped_column(Text)
    answer2: Mapped[str | None] = mapped_column(Text)
    question3: Mapped[str | None] = mapped_column(Text)
    answer3: Mapped[str | None] = mapped_column(Text)
    question4: Mapped[str | None] = mapped_column(Text)
    answer4: Mapped[str | None] = mapped_column(Text)
    question5: Mapped[str | None] = mapped_column(Text)
    answer5: Mapped[str | None] = mapped_column(Text)


class Shift(Base):
    __tablename__ = "shifts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    assistant_id: Mapped[int | None] = mapped_column(BigInteger)
    doctor_name: Mapped[str | None] = mapped_column(Text)
    date: Mapped[date | None] = mapped_column(Date)
    type: Mapped[str | None] = mapped_column(String(10))
    scheduled_assistant_name: Mapped[str | None] = mapped_column(Text)
    speciality: Mapped[str | None] = mapped_column(Text)
    cabinet: Mapped[str | None] = mapped_column(Text)
    assistant_name: Mapped[str | None] = mapped_column(Text)
    manual: Mapped[bool | None] = mapped_column(Boolean, default=False)

    # Один ассистент — не больше одной смены в слоте (дата + тип).
    # В Postgres NULL-значения assistant_id считаются различными,
    # поэтому свободные смены (assistant_id IS NULL) индекс не ограничивает.
    __table_args__ = (UniqueConstraint("assistant_id", "date", "type", name="uq_shift_assistant_slot"),)


class Cabinet(Base):
    __tablename__ = "cabinets"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True)


class Instrument(Base):
    __tablename__ = "instruments"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(Text)
    cabinet_id: Mapped[int | None] = mapped_column(BigInteger)
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True)


class InstrumentMove(Base):
    __tablename__ = "instrument_moves"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int | None] = mapped_column(BigInteger)
    from_cabinet_id: Mapped[int | None] = mapped_column(BigInteger)
    to_cabinet_id: Mapped[int | None] = mapped_column(BigInteger)
    before_photo_id: Mapped[str | None] = mapped_column(String(255))
    after_photo_id: Mapped[str | None] = mapped_column(String(255))
    moved_by_chat_id: Mapped[str | None] = mapped_column(String(31))
    moved_at: Mapped[datetime | None] = mapped_column(DateTime)


class KnowledgeSection(Base):
    __tablename__ = "knowledge_sections"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class KnowledgeManipulation(Base):
    __tablename__ = "knowledge_manipulations"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    manipulation_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    item_number: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str | None] = mapped_column(Text)
    extra: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


async def async_main():
    # Схему создаёт и мигрирует Alembic (`alembic upgrade head`), а не приложение.
    # Здесь остаётся только засев обязательных данных.
    async with async_session() as session:
        result = await session.execute(select(Cabinet).where(Cabinet.name == "Стерилизационная"))
        if result.scalar_one_or_none() is None:
            session.add(Cabinet(name="Стерилизационная", is_active=True))
            await session.commit()
