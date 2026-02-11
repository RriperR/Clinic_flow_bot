import os

from dotenv import load_dotenv
from sqlalchemy import BigInteger, String, Text, Column, Boolean, select
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


engine = create_async_engine(
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class AdminUser(Base):
    __tablename__ = "admins"
    id = Column(BigInteger, primary_key=True)
    chat_id = Column(String(31), unique=True, nullable=False)
    added_at = Column(String(63))


class Worker(Base):
    __tablename__ = "workers"
    id = Column(BigInteger, primary_key=True)
    full_name = Column(Text)
    file_id = Column(String(255))
    chat_id = Column(String(31))
    speciality = Column(String(255))
    phone = Column(String(31))


class Pair(Base):
    __tablename__ = "pairs"
    id = Column(BigInteger, primary_key=True)
    subject = Column(Text)
    object = Column(Text)
    survey = Column(Text)
    weekday = Column(String(31))
    date = Column(String(31))
    status = Column(String(15), default="ready")


class Survey(Base):
    __tablename__ = "surveys"
    id = Column(BigInteger, primary_key=True)
    speciality = Column(String(511))
    question1 = Column(Text)
    question1_type = Column(String(7))
    question2 = Column(Text)
    question2_type = Column(String(7))
    question3 = Column(Text)
    question3_type = Column(String(7))
    question4 = Column(Text)
    question4_type = Column(String(7))
    question5 = Column(Text)
    question5_type = Column(String(7))


class Answer(Base):
    __tablename__ = "answers"
    id = Column(BigInteger, primary_key=True)
    subject = Column(Text)
    object = Column(Text)
    survey = Column(Text)
    survey_date = Column(String(31))
    completed_at = Column(String(63))
    question1 = Column(Text)
    answer1 = Column(Text)
    question2 = Column(Text)
    answer2 = Column(Text)
    question3 = Column(Text)
    answer3 = Column(Text)
    question4 = Column(Text)
    answer4 = Column(Text)
    question5 = Column(Text)
    answer5 = Column(Text)


class Shift(Base):
    __tablename__ = "shifts"
    id = Column(BigInteger, primary_key=True)
    assistant_id = Column(BigInteger)
    doctor_name = Column(Text)
    date = Column(String(31))
    type = Column(String(10))
    scheduled_assistant_name = Column(Text, nullable=True)
    speciality = Column(Text, nullable=True)
    cabinet = Column(Text, nullable=True)
    assistant_name = Column(Text, nullable=True)
    manual = Column(Boolean, default=False)


class Cabinet(Base):
    __tablename__ = "cabinets"
    id = Column(BigInteger, primary_key=True)
    name = Column(Text)
    is_active = Column(Boolean, default=True)


class Instrument(Base):
    __tablename__ = "instruments"
    id = Column(BigInteger, primary_key=True)
    name = Column(Text)
    cabinet_id = Column(BigInteger)
    is_active = Column(Boolean, default=True)


class InstrumentMove(Base):
    __tablename__ = "instrument_moves"
    id = Column(BigInteger, primary_key=True)
    instrument_id = Column(BigInteger)
    from_cabinet_id = Column(BigInteger)
    to_cabinet_id = Column(BigInteger)
    before_photo_id = Column(String(255))
    after_photo_id = Column(String(255))
    moved_by_chat_id = Column(String(31))
    moved_at = Column(String(63))


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        result = await session.execute(
            select(Cabinet).where(Cabinet.name == "Стерилизационная")
        )
        if result.scalar_one_or_none() is None:
            session.add(Cabinet(name="Стерилизационная", is_active=True))
            await session.commit()
