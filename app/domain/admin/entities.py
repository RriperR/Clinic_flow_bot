from dataclasses import dataclass
from datetime import datetime


@dataclass(kw_only=True)
class AdminUser:
    id: int | None = None
    chat_id: str
    added_at: datetime | None = None
