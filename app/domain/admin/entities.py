from dataclasses import dataclass


@dataclass
class AdminUser:
    id: int | None
    chat_id: str
    added_at: str | None = None
