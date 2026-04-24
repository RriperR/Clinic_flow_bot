import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.domain.repositories import WorkerRepository
from app.logger import setup_logger

actions_logger = setup_logger("actions", "actions.log")


@dataclass
class UserLogContext:
    event_id: str
    chat_id: int | None
    username: str | None
    telegram_full_name: str | None
    worker_id: int | None = None
    full_name: str | None = None
    db_error: str | None = None

    @property
    def display_name(self) -> str:
        return self.full_name or self.telegram_full_name or "unknown"


class UserActionLoggingMiddleware(BaseMiddleware):
    def __init__(self, workers: WorkerRepository):
        self.workers = workers

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        started_at = time.monotonic()
        context = await self._build_context(event)
        action = self._describe_action(event)
        state_name = await self._get_state_name(data.get("state"))
        data["user_log_context"] = context
        data["action_name"] = action

        try:
            result = await handler(event, data)
        except Exception as exc:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            self._log_action(
                context=context,
                action=action,
                state_name=state_name,
                status="error",
                duration_ms=duration_ms,
                error=exc,
            )
            raise

        duration_ms = int((time.monotonic() - started_at) * 1000)
        self._log_action(
            context=context,
            action=action,
            state_name=state_name,
            status="ok",
            duration_ms=duration_ms,
        )
        return result

    async def _build_context(self, event: TelegramObject) -> UserLogContext:
        event_id = uuid4().hex[:10]
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        context = UserLogContext(
            event_id=event_id,
            chat_id=user.id if user else None,
            username=user.username if user else None,
            telegram_full_name=user.full_name if user else None,
        )

        if not context.chat_id:
            return context

        try:
            worker = await self.workers.get_by_chat_id(
                context.chat_id,
                include_inactive=True,
            )
        except Exception as exc:
            context.db_error = f"{type(exc).__name__}: {exc}"
            return context

        if worker:
            context.worker_id = worker.id
            context.full_name = worker.full_name
        return context

    async def _get_state_name(self, state: FSMContext | None) -> str | None:
        if not state:
            return None
        try:
            return await state.get_state()
        except Exception as exc:
            return f"state_error:{type(exc).__name__}"

    def _describe_action(self, event: TelegramObject) -> str:
        if isinstance(event, Message):
            if event.text and event.text.startswith("/"):
                return event.text.split(maxsplit=1)[0]
            if event.photo:
                return "photo"
            if event.document:
                return "document"
            if event.text:
                return "text"
            return "other_message"

        if isinstance(event, CallbackQuery):
            button_text = self._resolve_callback_button_text(event)
            if button_text:
                return f"кнопка: {button_text}"
            callback_data = event.data or ""
            callback_prefix = callback_data.split(":", 1)[0] if callback_data else "empty"
            return f"кнопка: {callback_prefix}"

        return type(event).__name__

    def _resolve_callback_button_text(self, event: CallbackQuery) -> str | None:
        if not event.message or not event.message.reply_markup:
            return None

        callback_data = event.data or ""
        for row in event.message.reply_markup.inline_keyboard:
            for button in row:
                if button.callback_data == callback_data:
                    return button.text
        return None

    def _log_action(
        self,
        *,
        context: UserLogContext,
        action: str,
        state_name: str | None,
        status: str,
        duration_ms: int,
        error: Exception | None = None,
    ) -> None:
        level = actions_logger.warning if context.db_error or error else actions_logger.info
        icon = "✅" if status == "ok" else "❌"
        username = f"@{context.username}" if context.username else "-"
        file_parts = [
            f"👤 {context.display_name} | chat_id={context.chat_id} | {username}",
            f"➡️ {action}",
            f"{icon} {status} · {duration_ms}ms",
        ]
        if context.worker_id is not None:
            file_parts.append(f"worker_id={context.worker_id}")
        if state_name:
            file_parts.append(f"state={state_name}")
        if context.db_error:
            file_parts.append(f"db_user_lookup_error={context.db_error}")
        if error:
            file_parts.append(f"error={type(error).__name__}: {error}")

        telegram_parts = [
            f"👤 {context.display_name}",
            action,
            f"{icon} {status}",
        ]
        if error:
            telegram_parts.append(type(error).__name__)

        level(
            "\n".join(file_parts),
            extra={
                "send_to_telegram": True,
                "telegram_message": "\n".join(telegram_parts),
            },
        )
