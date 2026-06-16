from datetime import date

from app.application.surveys.flow_use_case import SurveyFlowService
from app.domain.entities import Pair, Survey


class FakeAnswerRepository:
    def __init__(self):
        self.saved = []

    async def save(self, answer):
        self.saved.append(answer)


class FakePairRepository:
    pass


class FakeSurveyRepository:
    pass


class FakeWorkerRepository:
    pass


async def test_save_answers_creates_new_answer_without_id() -> None:
    answers = FakeAnswerRepository()
    service = SurveyFlowService(
        FakeWorkerRepository(),
        FakePairRepository(),
        FakeSurveyRepository(),
        answers,
    )
    pair = Pair(
        id=1,
        subject="Subject",
        object="Object",
        survey="Therapy",
        weekday="Monday",
        date=date(2026, 1, 2),
    )
    survey = Survey(
        id=1,
        speciality="Therapy",
        question1="Q1",
        question1_type="int",
        question2="Q2",
        question2_type="int",
        question3="Q3",
        question3_type="int",
        question4="Q4",
        question4_type="str",
        question5="Q5",
        question5_type="str",
    )

    await service.save_answers(pair, survey, ["5", "4", "3", "comment", "note"])

    assert len(answers.saved) == 1
    assert answers.saved[0].id is None
    assert answers.saved[0].subject == "Subject"
    assert answers.saved[0].answer5 == "note"
