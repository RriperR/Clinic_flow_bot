from datetime import date, datetime
from enum import StrEnum

SHIFT_DATE_FORMAT = "%d.%m.%Y"


class ShiftType(StrEnum):
    MORNING = "morning"
    EVENING = "evening"


def format_shift_date(value: date | datetime) -> str:
    return value.strftime(SHIFT_DATE_FORMAT)


def parse_shift_type(value: str | ShiftType) -> ShiftType:
    return value if isinstance(value, ShiftType) else ShiftType(value)
