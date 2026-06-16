from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from app.application.llm.ports import ToolSpec


@dataclass(frozen=True)
class AgentPendingAction:
    kind: str
    target_id: int | None = None
    target_ref: str | None = None
    shift_date: str | None = None
    shift_type: str | None = None
    manual: bool = False


@dataclass
class AgentToolContext:
    chat_id: int | None = None
    targets: dict[str, int] | None = None
    labels: dict[str, str] | None = None

    def target_id(self, ref: str) -> int | None:
        return (self.targets or {}).get(ref)

    def remember_label(self, label: str, prefix: str = "PRIVATE_NAME") -> str:
        labels = self.labels if self.labels is not None else {}
        self.labels = labels
        for ref, existing in labels.items():
            if existing == label:
                return ref
        ref = f"[{prefix}_{len(labels) + 1}]"
        labels[ref] = label
        return ref

    def restore_labels(self, text: str) -> str:
        result = text
        for ref, label in (self.labels or {}).items():
            result = result.replace(ref, label)
        return result


@dataclass(frozen=True)
class ToolExecutionResult:
    content: str
    pending_action: AgentPendingAction | None = None


ToolHandler = Callable[[dict[str, Any], AgentToolContext | None], Awaitable[str | ToolExecutionResult]]


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

    async def invoke(
        self,
        name: str,
        arguments: dict[str, Any],
        context: AgentToolContext | None = None,
    ) -> ToolExecutionResult:
        # Ошибка тула не должна ронять агентский цикл — возвращаем её как
        # результат, чтобы модель могла отреагировать.
        tool = self._tools.get(name)
        if tool is None:
            return ToolExecutionResult(f"Error: unknown tool '{name}'")
        try:
            result = await tool.handler(arguments, context)
        except Exception as exc:
            return ToolExecutionResult(f"Error: {type(exc).__name__}: {exc}")
        if isinstance(result, ToolExecutionResult):
            return result
        return ToolExecutionResult(result)
