from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from app.application.llm.ports import ToolSpec

ToolHandler = Callable[[dict[str, Any]], Awaitable[str]]


@dataclass(frozen=True)
class Tool:
    """Связка описания тула (для модели) с обработчиком (вызывает use case)."""

    spec: ToolSpec
    handler: ToolHandler


class ToolRegistry:
    """Реестр доступных агенту тулов: отдаёт их описания и исполняет вызовы."""

    def __init__(self, tools: Sequence[Tool] = ()):
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        self._tools[tool.spec.name] = tool

    def specs(self) -> list[ToolSpec]:
        return [tool.spec for tool in self._tools.values()]

    async def invoke(self, name: str, arguments: dict[str, Any]) -> str:
        # Ошибка тула не должна ронять агентский цикл — возвращаем её как
        # результат, чтобы модель могла отреагировать.
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'"
        try:
            return await tool.handler(arguments)
        except Exception as exc:
            return f"Error: {type(exc).__name__}: {exc}"
