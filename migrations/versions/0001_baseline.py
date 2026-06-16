"""baseline: текущая схема (строковые даты)

Зафиксированный снимок схемы на момент внедрения Alembic. На существующих
БД не выполняется (их помечают `alembic stamp 0001_baseline`); на чистых —
создаёт все таблицы, далее тип дат меняет миграция 0002.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-13
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admins",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.String(31), nullable=False, unique=True),
        sa.Column("added_at", sa.String(63), nullable=True),
    )
    op.create_table(
        "workers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("file_id", sa.String(255), nullable=True),
        sa.Column("chat_id", sa.String(31), nullable=True),
        sa.Column("speciality", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(31), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("shifts_week", sa.Integer(), nullable=False),
        sa.Column("shifts_month", sa.Integer(), nullable=False),
        sa.Column("given_week", sa.Integer(), nullable=False),
        sa.Column("given_month", sa.Integer(), nullable=False),
        sa.Column("replacement_week", sa.Integer(), nullable=False),
        sa.Column("replacement_month", sa.Integer(), nullable=False),
        sa.Column("manual_week", sa.Integer(), nullable=False),
        sa.Column("manual_month", sa.Integer(), nullable=False),
    )
    op.create_table(
        "pairs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("object", sa.Text(), nullable=True),
        sa.Column("survey", sa.Text(), nullable=True),
        sa.Column("weekday", sa.String(31), nullable=True),
        sa.Column("date", sa.String(31), nullable=True),
        sa.Column("status", sa.String(15), nullable=True),
    )
    op.create_table(
        "surveys",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("speciality", sa.String(511), nullable=True),
        sa.Column("question1", sa.Text(), nullable=True),
        sa.Column("question1_type", sa.String(7), nullable=True),
        sa.Column("question2", sa.Text(), nullable=True),
        sa.Column("question2_type", sa.String(7), nullable=True),
        sa.Column("question3", sa.Text(), nullable=True),
        sa.Column("question3_type", sa.String(7), nullable=True),
        sa.Column("question4", sa.Text(), nullable=True),
        sa.Column("question4_type", sa.String(7), nullable=True),
        sa.Column("question5", sa.Text(), nullable=True),
        sa.Column("question5_type", sa.String(7), nullable=True),
    )
    op.create_table(
        "answers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("object", sa.Text(), nullable=True),
        sa.Column("survey", sa.Text(), nullable=True),
        sa.Column("survey_date", sa.String(31), nullable=True),
        sa.Column("completed_at", sa.String(63), nullable=True),
        sa.Column("question1", sa.Text(), nullable=True),
        sa.Column("answer1", sa.Text(), nullable=True),
        sa.Column("question2", sa.Text(), nullable=True),
        sa.Column("answer2", sa.Text(), nullable=True),
        sa.Column("question3", sa.Text(), nullable=True),
        sa.Column("answer3", sa.Text(), nullable=True),
        sa.Column("question4", sa.Text(), nullable=True),
        sa.Column("answer4", sa.Text(), nullable=True),
        sa.Column("question5", sa.Text(), nullable=True),
        sa.Column("answer5", sa.Text(), nullable=True),
    )
    op.create_table(
        "shifts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("assistant_id", sa.BigInteger(), nullable=True),
        sa.Column("doctor_name", sa.Text(), nullable=True),
        sa.Column("date", sa.String(31), nullable=True),
        sa.Column("type", sa.String(10), nullable=True),
        sa.Column("scheduled_assistant_name", sa.Text(), nullable=True),
        sa.Column("speciality", sa.Text(), nullable=True),
        sa.Column("cabinet", sa.Text(), nullable=True),
        sa.Column("assistant_name", sa.Text(), nullable=True),
        sa.Column("manual", sa.Boolean(), nullable=True),
        sa.UniqueConstraint("assistant_id", "date", "type", name="uq_shift_assistant_slot"),
    )
    op.create_table(
        "cabinets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
    )
    op.create_table(
        "instruments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("cabinet_id", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
    )
    op.create_table(
        "instrument_moves",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("instrument_id", sa.BigInteger(), nullable=True),
        sa.Column("from_cabinet_id", sa.BigInteger(), nullable=True),
        sa.Column("to_cabinet_id", sa.BigInteger(), nullable=True),
        sa.Column("before_photo_id", sa.String(255), nullable=True),
        sa.Column("after_photo_id", sa.String(255), nullable=True),
        sa.Column("moved_by_chat_id", sa.String(31), nullable=True),
        sa.Column("moved_at", sa.String(63), nullable=True),
    )
    op.create_table(
        "knowledge_sections",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "knowledge_manipulations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("section_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "knowledge_items",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("manipulation_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("item_number", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("extra", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("knowledge_items")
    op.drop_table("knowledge_manipulations")
    op.drop_table("knowledge_sections")
    op.drop_table("instrument_moves")
    op.drop_table("instruments")
    op.drop_table("cabinets")
    op.drop_table("shifts")
    op.drop_table("answers")
    op.drop_table("surveys")
    op.drop_table("pairs")
    op.drop_table("workers")
    op.drop_table("admins")
