from dataclasses import dataclass


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
