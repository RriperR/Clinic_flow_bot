from dataclasses import dataclass
from datetime import date as date_type

from app.domain.shifts.value_objects import ShiftType


@dataclass(kw_only=True)
class Shift:
    id: int | None = None
    assistant_id: int | None
    doctor_name: str
    date: date_type
    type: ShiftType
    scheduled_assistant_name: str | None = None
    speciality: str | None = None
    cabinet: str | None = None
    assistant_name: str | None = None
    manual: bool = False
