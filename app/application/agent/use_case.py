from collections.abc import Sequence

from app.application.agent.tools import ToolRegistry
from app.application.llm.ports import LlmClient, LlmMessage, LlmRole


class AgentService:
    """Агент на ручном цикле tool-use поверх провайдер-агностичного LlmClient.

    Шаг: вызвать модель → если она запросила тулы, исполнить их через реестр
    и вернуть результаты → повторить, пока не получим финальный текст или не
    упрёмся в лимит шагов.
    """

    def __init__(
        self,
        llm: LlmClient,
        tools: ToolRegistry,
        system_prompt: str,
        max_steps: int = 5,
    ):
        self._llm = llm
        self._tools = tools
        self._system_prompt = system_prompt
        self._max_steps = max_steps

    async def run(self, user_message: str, history: Sequence[LlmMessage] | None = None) -> str:
        messages: list[LlmMessage] = list(history or [])
        messages.append(LlmMessage(role=LlmRole.USER, content=user_message))
        tools = self._tools.specs() or None

        for _ in range(self._max_steps):
            completion = await self._llm.complete(messages, system=self._system_prompt, tools=tools)
            if not completion.tool_calls:
                return completion.text or ""

            messages.append(
                LlmMessage(
                    role=LlmRole.ASSISTANT,
                    content=completion.text or "",
                    tool_calls=completion.tool_calls,
                )
            )
            for call in completion.tool_calls:
                result = await self._tools.invoke(call.name, call.arguments)
                messages.append(LlmMessage(role=LlmRole.TOOL, content=result, tool_call_id=call.id))

        # Лимит шагов исчерпан — последний вызов без тулов, чтобы вернуть текст.
        final = await self._llm.complete(messages, system=self._system_prompt)
        return final.text or ""
