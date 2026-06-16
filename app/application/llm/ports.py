from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class LlmRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolSpec:
    """Описание тула для модели: имя, описание и JSON-schema входных параметров."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class LlmMessage:
    role: LlmRole
    content: str
    # role == TOOL: id вызова, на который это ответ.
    tool_call_id: str | None = None
    # role == ASSISTANT: тулы, которые модель попросила выполнить.
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(frozen=True)
class LlmCompletion:
    """Результат вызова модели: либо текст, либо запрошенные тул-коллы."""

    text: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str | None = None


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
        system: str | None = None,
        tools: Sequence[ToolSpec] | None = None,
        tool_choice: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LlmCompletion: ...
