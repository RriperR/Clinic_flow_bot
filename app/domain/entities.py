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


@dataclass
class AdminUser:
    id: int | None
    chat_id: str
    added_at: str | None = None


@dataclass
class Pair:
    id: int | None
    subject: str
    object: str
    survey: str
    weekday: str
    date: str
    status: str = "ready"


@dataclass
class Survey:
    id: int | None
    speciality: str
    question1: str
    question1_type: str
    question2: str
    question2_type: str
    question3: str
    question3_type: str
    question4: str
    question4_type: str
    question5: str
    question5_type: str


@dataclass
class Answer:
    id: int | None
    subject: str
    object: str
    survey: str
    survey_date: str
    completed_at: str
    question1: str
    answer1: str
    question2: str
    answer2: str
    question3: str
    answer3: str
    question4: str
    answer4: str
    question5: str
    answer5: str


@dataclass
class Shift:
    id: int | None
    assistant_id: int | None
    doctor_name: str
    date: str
    type: str
    scheduled_assistant_name: str | None = None
    speciality: str | None = None
    cabinet: str | None = None
    assistant_name: str | None = None
    manual: bool = False


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
