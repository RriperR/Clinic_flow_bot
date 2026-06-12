from dataclasses import dataclass


@dataclass
class Cabinet:
    id: int | None
    name: str
    is_active: bool = True


@dataclass
class Instrument:
    id: int | None
    name: str
    cabinet_id: int
    is_active: bool = True


@dataclass
class InstrumentMove:
    id: int | None
    instrument_id: int
    from_cabinet_id: int
    to_cabinet_id: int
    before_photo_id: str | None
    after_photo_id: str | None
    moved_by_chat_id: str | None
    moved_at: str
