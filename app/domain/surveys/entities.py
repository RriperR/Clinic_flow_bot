from dataclasses import dataclass
from datetime import date, datetime


@dataclass(kw_only=True)
class Pair:
    id: int | None = None
    subject: str
    object: str
    survey: str
    weekday: str
    date: date
    status: str = "ready"


@dataclass(kw_only=True)
class Survey:
    id: int | None = None
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


@dataclass(kw_only=True)
class Answer:
    id: int | None = None
    subject: str
    object: str
    survey: str
    survey_date: date
    completed_at: datetime
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
