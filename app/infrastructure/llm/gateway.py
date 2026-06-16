from collections.abc import Sequence
from typing import Any

import aiohttp

from app.application.llm.ports import LlmMessage
from app.config import LlmSettings


class OpenAICompatibleLlmClient:
    """LLM-клиент поверх OpenAI-совместимого Chat Completions API.

    Провайдер не зашит в код: его выбирает base_url из настроек (OpenAI,
    OpenRouter, локальный сервер, совместимый режим Anthropic и т.д.),
    модель — settings.model с возможностью переопределить на вызов.
    """

    def __init__(self, settings: LlmSettings):
        self._settings = settings

    def _build_payload(
        self,
        messages: Sequence[LlmMessage],
        *,
        model: str | None,
        max_tokens: int | None,
        temperature: float | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model or self._settings.model,
            "messages": [{"role": str(m.role), "content": m.content} for m in messages],
            "max_tokens": max_tokens or self._settings.max_tokens,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        return payload

    async def complete(
        self,
        messages: Sequence[LlmMessage],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        if not self._settings.base_url or not self._settings.api_key:
            raise RuntimeError("LLM не сконфигурирован: задайте LLM_BASE_URL и LLM_API_KEY")

        payload = self._build_payload(
            messages, model=model, max_tokens=max_tokens, temperature=temperature
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
        return data["choices"][0]["message"]["content"]
