from typing import Protocol


class MessageSender(Protocol):
    async def send_message(self, chat_id: str, text: str, parse_mode: str | None = None) -> object: ...
