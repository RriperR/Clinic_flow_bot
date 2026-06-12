from dataclasses import dataclass


@dataclass
class Worker:
    id: int | None
    full_name: str
    file_id: str | None = None
    chat_id: str | None = None
    speciality: str | None = None
    phone: str | None = None
    is_active: bool = True
    shifts_week: int = 0
    shifts_month: int = 0
    given_week: int = 0
    given_month: int = 0
    replacement_week: int = 0
    replacement_month: int = 0
    manual_week: int = 0
    manual_month: int = 0
