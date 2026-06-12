from aiogram import Bot, Dispatcher

from app.application.surveys.flow_use_case import SurveyFlowService
from app.domain.entities import Pair
from app.handlers.survey_handlers import start_pair_survey


class AiogramSurveyDelivery:
    def __init__(self, bot: Bot, dispatcher: Dispatcher, survey_flow: SurveyFlowService):
        self.bot = bot
        self.dispatcher = dispatcher
        self.survey_flow = survey_flow

    async def start_pair_survey(
        self,
        chat_id: int,
        pair: Pair,
        file_id: str | None = None,
    ) -> None:
        await start_pair_survey(
            self.bot,
            chat_id,
            pair,
            self.survey_flow,
            dp=self.dispatcher,
            file_id=file_id,
        )
