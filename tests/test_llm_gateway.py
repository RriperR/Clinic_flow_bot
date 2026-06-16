from collections.abc import Sequence

from app.application.llm.ports import LlmClient, LlmMessage, LlmRole
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


def test_payload_uses_defaults_from_settings() -> None:
    client = OpenAICompatibleLlmClient(_settings())
    payload = client._build_payload(
        [LlmMessage(role=LlmRole.USER, content="hi")],
        model=None,
        max_tokens=None,
        temperature=None,
    )
    assert payload == {
        "model": "default-model",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 256,
    }


def test_payload_overrides_and_temperature() -> None:
    client = OpenAICompatibleLlmClient(_settings())
    payload = client._build_payload(
        [
            LlmMessage(role=LlmRole.SYSTEM, content="sys"),
            LlmMessage(role=LlmRole.USER, content="q"),
        ],
        model="other-model",
        max_tokens=10,
        temperature=0.2,
    )
    assert payload["model"] == "other-model"
    assert payload["max_tokens"] == 10
    assert payload["temperature"] == 0.2
    assert [m["role"] for m in payload["messages"]] == ["system", "user"]


async def test_fake_client_satisfies_port() -> None:
    class FakeLlmClient:
        def __init__(self) -> None:
            self.calls: list[Sequence[LlmMessage]] = []

        async def complete(self, messages, *, model=None, max_tokens=None, temperature=None) -> str:
            self.calls.append(list(messages))
            return "stub answer"

    client: LlmClient = FakeLlmClient()
    answer = await client.complete([LlmMessage(role=LlmRole.USER, content="hello")])
    assert answer == "stub answer"
