"""normalize dates: строковые даты/время -> DATE/TIMESTAMP

Конвертирует исторические строковые значения в нативные типы Postgres.
Перед применением убедитесь, что в колонках нет значений, не подходящих под
указанные форматы (см. README, раздел про миграцию дат).

Revision ID: 0002_normalize_dates
Revises: 0001_baseline
Create Date: 2026-06-13
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_normalize_dates"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Логические даты, формат "%d.%m.%Y".
    op.alter_column(
        "shifts", "date", type_=sa.Date(), postgresql_using="to_date(date, 'DD.MM.YYYY')"
    )
    op.alter_column(
        "pairs", "date", type_=sa.Date(), postgresql_using="to_date(date, 'DD.MM.YYYY')"
    )
    op.alter_column(
        "answers",
        "survey_date",
        type_=sa.Date(),
        postgresql_using="to_date(NULLIF(survey_date, ''), 'DD.MM.YYYY')",
    )
    # Таймстампы с разными форматами в источнике.
    op.alter_column(
        "answers",
        "completed_at",
        type_=sa.DateTime(),
        postgresql_using="NULLIF(completed_at, '')::timestamp",  # 'YYYY-MM-DD HH:MM:SS.ffffff'
    )
    op.alter_column(
        "admins",
        "added_at",
        type_=sa.DateTime(),
        postgresql_using="NULLIF(added_at, '')::timestamp",  # ISO 8601 c 'T'
    )
    op.alter_column(
        "instrument_moves",
        "moved_at",
        type_=sa.DateTime(),
        postgresql_using="to_timestamp(moved_at, 'DD.MM.YYYY HH24:MI:SS')",
    )


def downgrade() -> None:
    op.alter_column(
        "instrument_moves",
        "moved_at",
        type_=sa.String(63),
        postgresql_using="to_char(moved_at, 'DD.MM.YYYY HH24:MI:SS')",
    )
    op.alter_column(
        "admins",
        "added_at",
        type_=sa.String(63),
        postgresql_using="""to_char(added_at, 'YYYY-MM-DD"T"HH24:MI:SS')""",
    )
    op.alter_column(
        "answers",
        "completed_at",
        type_=sa.String(63),
        postgresql_using="to_char(completed_at, 'YYYY-MM-DD HH24:MI:SS.US')",
    )
    op.alter_column(
        "answers",
        "survey_date",
        type_=sa.String(31),
        postgresql_using="to_char(survey_date, 'DD.MM.YYYY')",
    )
    op.alter_column(
        "pairs", "date", type_=sa.String(31), postgresql_using="to_char(date, 'DD.MM.YYYY')"
    )
    op.alter_column(
        "shifts", "date", type_=sa.String(31), postgresql_using="to_char(date, 'DD.MM.YYYY')"
    )
