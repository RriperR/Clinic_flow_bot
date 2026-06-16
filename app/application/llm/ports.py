from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class LlmRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class LlmMessage:
    role: LlmRole
    content: str


class LlmClient(Protocol):
    """Провайдер-агностичный доступ к LLM.

    Реализация выбирается и настраивается в инфраструктуре/контейнере;
    приложение зависит только от этого порта. Модель можно задать по
    умолчанию в настройках и переопределить на конкретный вызов.
    """

    async def complete(
        self,
        messages: Sequence[LlmMessage],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str: ...
