from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

SHIFT_DATE_FORMAT = "%d.%m.%Y"


class ShiftType(StrEnum):
    MORNING = "morning"
    EVENING = "evening"


@dataclass(frozen=True)
class ShiftImportRow:
    """Строка графика смен из внешнего источника для массовой загрузки."""

    doctor_name: str
    date: str
    type: ShiftType | str
    scheduled_assistant_name: str | None = None
    speciality: str | None = None
    cabinet: str | None = None


def format_shift_date(value: date | datetime) -> str:
    return value.strftime(SHIFT_DATE_FORMAT)


def parse_shift_type(value: str | ShiftType) -> ShiftType:
    return value if isinstance(value, ShiftType) else ShiftType(value)
