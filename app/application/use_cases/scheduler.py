from collections import defaultdict
from datetime import datetime

from aiogram import Bot, Dispatcher
from app.application.use_cases.survey_flow import SurveyFlowService
from app.domain.entities import Pair
from app.handlers.survey_handlers import start_pair_survey
from app.logger import setup_logger


class SurveyScheduler:
    def __init__(self, survey_flow: SurveyFlowService):
        self.survey_flow = survey_flow
        self.logger = setup_logger("surveys", "surveys.log")

    async def send_surveys(self, bot: Bot, dp: Dispatcher) -> None:
        self.logger.info("📤 Запуск рассылки опросов")
        await self.survey_flow.reset_incomplete()

        today = datetime.now().strftime("%d.%m.%Y")
        pairs = await self.survey_flow.get_ready_pairs_for_today(today)

        by_user: dict[str, list[Pair]] = defaultdict(list)
        for p in pairs:
            by_user[p.subject].append(p)

        for subject, user_pairs in by_user.items():
            try:
                worker = await self.survey_flow.get_worker(subject)
            except Exception as exc:
                self.logger.error("get_worker_by_fullname: %s. subject: %s.", exc, subject)
                continue

            if not worker or not worker.chat_id:
                self.logger.warning("Не найден chat_id для %s", subject)
                continue

            if any(p.status == "in_progress" for p in user_pairs):
                self.logger.warning("У %s уже есть незавершённый опрос", subject)
                continue

            pair = user_pairs[0]

            try:
                await self.survey_flow.mark_pair_status(pair.id, "in_progress")
                file_id = await self.survey_flow.get_worker_file_id(pair.object)
                await start_pair_survey(
                    bot,
                    int(worker.chat_id),
                    pair,
                    self.survey_flow,
                    dp=dp,
                    file_id=file_id,
                )
                self.logger.info("Отправлен опрос для %s от %s, id: %s", pair.subject, pair.date, pair.id)
            except Exception as exc:
                self.logger.error("Failed to start pair survey: %s. id: %s", exc, pair.id)
