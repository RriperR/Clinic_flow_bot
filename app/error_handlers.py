from uuid import uuid4

from aiogram.types import CallbackQuery, ErrorEvent, Message, Update

from app.domain.repositories import WorkerRepository
from app.logger import setup_logger
from app.logging_middleware import UserLogContext

errors_logger = setup_logger("errors", "errors.log")


class GlobalErrorHandler:
    def __init__(self, workers: WorkerRepository):
        self.workers = workers

    async def __call__(
        self,
        event: ErrorEvent,
        user_log_context: UserLogContext | None = None,
        action_name: str | None = None,
        **_: object,
    ) -> bool:
        error_id = uuid4().hex[:8]
        context = user_log_context or await self._build_context(event.update)
        action = action_name or self._describe_update(event.update)
        exception = event.exception

        file_message = (
            "Unhandled update error "
            f"error_id={error_id} action={action} "
            f"chat_id={context.chat_id} username={context.username} "
            f"worker_id={context.worker_id} full_name={context.full_name}"
        )
        telegram_message = self._format_telegram_error(
            error_id=error_id,
            context=context,
            action=action,
            exception=exception,
        )
        errors_logger.error(
            file_message,
            exc_info=(type(exception), exception, exception.__traceback__),
            extra={
                "send_to_telegram": True,
                "telegram_message": telegram_message,
            },
        )

        await self._answer_user(event.update, error_id)
        return True

    async def _build_context(self, update: Update) -> UserLogContext:
        user = None
        if update.message:
            user = update.message.from_user
        elif update.callback_query:
            user = update.callback_query.from_user

        context = UserLogContext(
            event_id=uuid4().hex[:10],
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

    def _describe_update(self, update: Update) -> str:
        if update.message:
            return self._describe_message(update.message)
        if update.callback_query:
            return self._describe_callback(update.callback_query)
        return "update:unknown"

    def _describe_message(self, message: Message) -> str:
        if message.text and message.text.startswith("/"):
            return f"message:{message.text.split(maxsplit=1)[0]}"
        if message.photo:
            return "message:photo"
        if message.document:
            return "message:document"
        if message.text:
            return "message:text"
        return "message:other"

    def _describe_callback(self, callback: CallbackQuery) -> str:
        callback_data = callback.data or ""
        callback_prefix = callback_data.split(":", 1)[0] if callback_data else "empty"
        return f"callback:{callback_prefix}"

    def _format_telegram_error(
        self,
        *,
        error_id: str,
        context: UserLogContext,
        action: str,
        exception: Exception,
    ) -> str:
        username = f"@{context.username}" if context.username else "-"
        lines = [
            f"❌ ERROR {error_id}",
            f"👤 {context.display_name} | chat_id={context.chat_id} | {username}",
            f"Действие: {action}",
            f"Ошибка: {type(exception).__name__}: {exception}",
        ]
        if context.worker_id is not None:
            lines.append(f"worker_id={context.worker_id}")
        if context.db_error:
            lines.append(f"db_user_lookup_error={context.db_error}")
        return "\n".join(lines)

    async def _answer_user(self, update: Update, error_id: str) -> None:
        text = (
            "Произошла ошибка. "
            f"Код ошибки: {error_id}. "
            "Сообщите его администратору."
        )
        try:
            if update.callback_query:
                await update.callback_query.answer(text, show_alert=True)
                return
            if update.message:
                await update.message.answer(text)
        except Exception:
            errors_logger.exception("Failed to send error message to user")
