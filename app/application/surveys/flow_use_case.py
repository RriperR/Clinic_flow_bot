from datetime import datetime

from app.domain.entities import Answer, Pair
from app.domain.repositories import (
    AnswerRepository,
    PairRepository,
    SurveyRepository,
    WorkerRepository,
)


class SurveyFlowService:
    def __init__(
        self,
        workers: WorkerRepository,
        pairs: PairRepository,
        surveys: SurveyRepository,
        answers: AnswerRepository,
    ):
        self.workers = workers
        self.pairs = pairs
        self.surveys = surveys
        self.answers = answers

    async def get_ready_pairs_for_today(self, today: str) -> list[Pair]:
        return list(await self.pairs.list_ready_by_date(today))

    async def reset_incomplete(self) -> None:
        await self.pairs.reset_incomplete()

    async def mark_pair_status(self, pair_id: int, status: str) -> None:
        await self.pairs.update_status(pair_id, status)

    async def get_next_ready_pair(self, subject: str) -> Pair | None:
        return await self.pairs.next_ready_for_subject(subject)

    async def get_worker(self, full_name: str):
        return await self.workers.get_by_fullname(full_name)

    async def get_worker_file_id(self, name: str) -> str | None:
        worker = await self.workers.get_by_fullname(name)
        if worker and worker.file_id:
            return worker.file_id
        return None

    async def get_survey(self, name: str):
        return await self.surveys.get_by_name(name)

    async def save_answers(self, pair: Pair, survey, answers: list[str]) -> None:
        now = datetime.now()
        a1, a2, a3, a4, a5 = answers

        new_answer = Answer(
            subject=pair.subject,
            object=pair.object,
            survey=pair.survey,
            survey_date=pair.date,
            completed_at=str(now),
            question1=survey.question1,
            answer1=a1,
            question2=survey.question2,
            answer2=a2,
            question3=survey.question3,
            answer3=a3,
            question4=survey.question4,
            answer4=a4,
            question5=survey.question5,
            answer5=a5,
        )

        await self.answers.save(new_answer)
