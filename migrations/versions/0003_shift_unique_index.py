"""ensure unique index uq_shift_assistant_slot

Индекс объявлен в моделях и baseline, но на части БД его нет: исторически
он создавался идемпотентным DDL в async_main, который теперь убран. Создаём
его явной идемпотентной миграцией, чтобы инвариант «один ассистент — одна
смена в слоте» был защищён на уровне БД везде.

Revision ID: 0003_shift_unique_index
Revises: 0002_normalize_dates
Create Date: 2026-06-13
"""

from alembic import op

revision = "0003_shift_unique_index"
down_revision = "0002_normalize_dates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_shift_assistant_slot ON shifts (assistant_id, date, type)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_shift_assistant_slot")
