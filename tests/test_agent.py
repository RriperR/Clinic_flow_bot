from app.application.agent.tools import Tool, ToolRegistry
from app.application.agent.use_case import AgentService
from app.application.llm.ports import LlmCompletion, LlmMessage, LlmRole, ToolCall, ToolSpec


class ScriptedLlmClient:
    """Возвращает заранее заданную последовательность ответов и пишет вызовы."""

    def __init__(self, completions: list[LlmCompletion]):
        self._completions = list(completions)
        self.calls: list[list[LlmMessage]] = []

    async def complete(self, messages, **kwargs) -> LlmCompletion:
        self.calls.append(list(messages))
        return self._completions.pop(0)


def _echo_tool(recorder: list[dict]) -> Tool:
    async def handler(arguments: dict) -> str:
        recorder.append(arguments)
        return "tool-result"

    return Tool(
        ToolSpec(name="lookup", description="d", parameters={"type": "object", "properties": {}}),
        handler,
    )


async def test_agent_executes_tool_then_returns_text() -> None:
    invoked: list[dict] = []
    llm = ScriptedLlmClient(
        [
            LlmCompletion(tool_calls=(ToolCall(id="c1", name="lookup", arguments={"q": "x"}),)),
            LlmCompletion(text="final answer"),
        ]
    )
    agent = AgentService(llm, ToolRegistry([_echo_tool(invoked)]), system_prompt="sys")

    answer = await agent.run("вопрос")

    assert answer == "final answer"
    assert invoked == [{"q": "x"}]
    # Второй вызов модели получил результат тула в истории.
    second_call = llm.calls[1]
    assert second_call[-1].role == LlmRole.TOOL
    assert second_call[-1].content == "tool-result"
    assert second_call[-1].tool_call_id == "c1"


async def test_agent_returns_text_without_tools() -> None:
    llm = ScriptedLlmClient([LlmCompletion(text="just text")])
    agent = AgentService(llm, ToolRegistry(), system_prompt="sys")

    assert await agent.run("привет") == "just text"
    assert len(llm.calls) == 1


async def test_registry_reports_unknown_tool() -> None:
    registry = ToolRegistry()
    assert await registry.invoke("missing", {}) == "Error: unknown tool 'missing'"


async def test_registry_wraps_handler_errors() -> None:
    async def boom(_arguments: dict) -> str:
        raise ValueError("nope")

    registry = ToolRegistry([Tool(ToolSpec(name="boom", description="d", parameters={}), boom)])
    assert await registry.invoke("boom", {}) == "Error: ValueError: nope"
