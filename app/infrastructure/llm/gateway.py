import json
from collections.abc import Sequence
from typing import Any

import aiohttp

from app.application.llm.ports import LlmCompletion, LlmMessage, LlmRole, ToolCall, ToolSpec
from app.config import LlmSettings


class OpenAICompatibleLlmClient:
    """LLM-клиент поверх OpenAI-совместимого Chat Completions API.

    Провайдер не зашит в код: его выбирает base_url из настроек (OpenAI,
    OpenRouter, локальный сервер, совместимый режим Anthropic и т.д.),
    модель — settings.model с возможностью переопределить на вызов.
    Поддерживает function calling (tools) — провайдер-агностичный стандарт.
    """

    def __init__(self, settings: LlmSettings):
        self._settings = settings

    @staticmethod
    def _message_to_dict(message: LlmMessage) -> dict[str, Any]:
        if message.role == LlmRole.TOOL:
            return {"role": "tool", "tool_call_id": message.tool_call_id, "content": message.content}
        if message.role == LlmRole.ASSISTANT and message.tool_calls:
            return {
                "role": "assistant",
                "content": message.content or None,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": json.dumps(call.arguments, ensure_ascii=False)},
                    }
                    for call in message.tool_calls
                ],
            }
        return {"role": str(message.role), "content": message.content}

    def _build_payload(
        self,
        messages: Sequence[LlmMessage],
        *,
        system: str | None,
        tools: Sequence[ToolSpec] | None,
        tool_choice: str | None,
        model: str | None,
        max_tokens: int | None,
        temperature: float | None,
    ) -> dict[str, Any]:
        chat: list[dict[str, Any]] = []
        if system:
            chat.append({"role": "system", "content": system})
        chat.extend(self._message_to_dict(message) for message in messages)

        payload: dict[str, Any] = {
            "model": model or self._settings.model,
            "messages": chat,
            "max_tokens": max_tokens or self._settings.max_tokens,
        }
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
                }
                for t in tools
            ]
            if tool_choice:
                payload["tool_choice"] = tool_choice
        if temperature is not None:
            payload["temperature"] = temperature
        return payload

    @staticmethod
    def _parse_response(data: dict[str, Any]) -> LlmCompletion:
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        calls: list[ToolCall] = []
        for raw in message.get("tool_calls") or []:
            function = raw.get("function") or {}
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {}
            calls.append(ToolCall(id=raw.get("id", ""), name=function.get("name", ""), arguments=arguments))
        return LlmCompletion(
            text=message.get("content"),
            tool_calls=tuple(calls),
            finish_reason=choice.get("finish_reason"),
        )

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
    ) -> LlmCompletion:
        if not self._settings.base_url or not self._settings.api_key:
            raise RuntimeError("LLM не сконфигурирован: задайте LLM_BASE_URL и LLM_API_KEY")

        payload = self._build_payload(
            messages,
            system=system,
            tools=tools,
            tool_choice=tool_choice,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
        }
        timeout = aiohttp.ClientTimeout(total=self._settings.timeout)
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(
                f"{self._settings.base_url}/chat/completions",
                json=payload,
                headers=headers,
            ) as response,
        ):
            response.raise_for_status()
            data = await response.json()
        return self._parse_response(data)
