from typing import Protocol

from app.domain.entities import Pair


class SurveyDelivery(Protocol):
    async def start_pair_survey(
        self,
        chat_id: int,
        pair: Pair,
        file_id: str | None = None,
    ) -> None: ...
