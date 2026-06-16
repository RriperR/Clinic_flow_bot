from app.application.llm.ports import LlmCompletion, LlmMessage, LlmRole, ToolCall, ToolSpec
from app.config import LlmSettings
from app.infrastructure.llm.gateway import OpenAICompatibleLlmClient


def _settings(model: str = "default-model", max_tokens: int = 256) -> LlmSettings:
    return LlmSettings(
        api_key="key",
        base_url="https://example.test/v1",
        model=model,
        max_tokens=max_tokens,
        timeout=30,
    )


def _payload(client: OpenAICompatibleLlmClient, messages, **kwargs):
    defaults = dict(system=None, tools=None, tool_choice=None, model=None, max_tokens=None, temperature=None)
    defaults.update(kwargs)
    return client._build_payload(messages, **defaults)


def test_payload_uses_defaults_and_prepends_system() -> None:
    client = OpenAICompatibleLlmClient(_settings())
    payload = _payload(client, [LlmMessage(role=LlmRole.USER, content="hi")], system="be brief")
    assert payload["model"] == "default-model"
    assert payload["max_tokens"] == 256
    assert payload["messages"] == [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "hi"},
    ]
    assert "tools" not in payload


def test_payload_serializes_tools_and_tool_messages() -> None:
    client = OpenAICompatibleLlmClient(_settings())
    tool = ToolSpec(name="lookup", description="d", parameters={"type": "object", "properties": {}})
    messages = [
        LlmMessage(
            role=LlmRole.ASSISTANT,
            content="",
            tool_calls=(ToolCall(id="c1", name="lookup", arguments={"q": "x"}),),
        ),
        LlmMessage(role=LlmRole.TOOL, content="result", tool_call_id="c1"),
    ]
    payload = _payload(client, messages, tools=[tool], tool_choice="auto")

    assert payload["tools"][0]["type"] == "function"
    assert payload["tools"][0]["function"]["name"] == "lookup"
    assert payload["tool_choice"] == "auto"

    assistant = payload["messages"][0]
    assert assistant["tool_calls"][0]["function"]["name"] == "lookup"
    assert assistant["tool_calls"][0]["function"]["arguments"] == '{"q": "x"}'
    assert payload["messages"][1] == {"role": "tool", "tool_call_id": "c1", "content": "result"}


def test_parse_text_response() -> None:
    data = {"choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}]}
    completion = OpenAICompatibleLlmClient._parse_response(data)
    assert completion.text == "hello"
    assert completion.tool_calls == ()
    assert completion.finish_reason == "stop"


def test_parse_tool_call_response() -> None:
    data = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [{"id": "c1", "function": {"name": "lookup", "arguments": '{"q": "x"}'}}],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }
    completion = OpenAICompatibleLlmClient._parse_response(data)
    assert completion.text is None
    assert completion.tool_calls == (ToolCall(id="c1", name="lookup", arguments={"q": "x"}),)


async def test_fake_client_satisfies_port() -> None:
    class FakeLlmClient:
        async def complete(self, messages, **kwargs) -> LlmCompletion:
            return LlmCompletion(text="stub answer")

    client = FakeLlmClient()
    answer = await client.complete([LlmMessage(role=LlmRole.USER, content="hello")])
    assert answer.text == "stub answer"
