from dataclasses import dataclass
from datetime import datetime


@dataclass(kw_only=True)
class Cabinet:
    id: int | None = None
    name: str
    is_active: bool = True


@dataclass(kw_only=True)
class Instrument:
    id: int | None = None
    name: str
    cabinet_id: int
    is_active: bool = True


@dataclass(kw_only=True)
class InstrumentMove:
    id: int | None = None
    instrument_id: int
    from_cabinet_id: int
    to_cabinet_id: int
    before_photo_id: str | None
    after_photo_id: str | None
    moved_by_chat_id: str | None
    moved_at: datetime
