import asyncio
import secrets
from datetime import date, datetime
from time import perf_counter
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.application.agent.privacy import SanitizedAgentMessage, ShiftTarget
from app.application.agent.use_case import AgentRunResult, AgentService
from app.application.llm.ports import LlmMessage, LlmRole
from app.application.shifts.dto import ShiftSignupStatus
from app.application.shifts.use_case import ShiftService
from app.domain.entities import Worker
from app.keyboards import (
    AgentShiftCancelConfirm,
    AgentShiftSignupConfirm,
    AgentTargetChoice,
    build_agent_shift_cancel_confirm_keyboard,
    build_agent_shift_signup_confirm_keyboard,
    build_agent_target_choice_keyboard,
)
from app.logger import setup_logger

logger = setup_logger("agent", "agent.log")

ASK_PROMPT = "Задайте вопрос по базе знаний клиники или по сменам. Для выхода — /stop."
ASK_STOPPED = "Режим вопросов завершён."
ASK_ERROR = "Не удалось получить ответ, попробуйте позже."
ASK_TIMEOUT = "Агент отвечает слишком долго. Попробуйте ещё раз чуть позже."
EMPTY_ANSWER = "Пустой ответ."
AGENT_THINKING = "ИИ-агент думает..."
WORKER_NOT_FOUND_MSG = "Мы не нашли вас в базе, сначала зарегистрируйтесь."
TARGET_NOT_FOUND_MSG = "Цель смены не найдена."

MAX_HISTORY_MESSAGES = 10
AGENT_RESPONSE_TIMEOUT_SECONDS = 45
PENDING_TTL_SECONDS = 10 * 60
PENDING_ACTIONS_KEY = "agent_pending_actions"


class AgentState(StatesGroup):
    asking = State()


def create_agent_router(agent: AgentService, shift_service: ShiftService) -> Router:
    router = Router()

    def build_history(history_raw: list[list[str]]) -> list[LlmMessage]:
        return [LlmMessage(role=LlmRole(role), content=content) for role, content in history_raw]

    def fresh_pending_actions(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        now = datetime.now().timestamp()
        raw_actions = data.get(PENDING_ACTIONS_KEY, {})
        return {
            token: action
            for token, action in raw_actions.items()
            if now - float(action.get("created_at", 0)) <= PENDING_TTL_SECONDS
        }

    async def store_pending_action(state: FSMContext, kind: str, payload: dict[str, Any]) -> str:
        data = await state.get_data()
        actions = fresh_pending_actions(data)
        token = secrets.token_hex(4)
        actions[token] = {"kind": kind, "created_at": datetime.now().timestamp(), **payload}
        await state.update_data(**{PENDING_ACTIONS_KEY: actions})
        return token

    async def pop_pending_action(state: FSMContext, token: str, kind: str) -> dict[str, Any] | None:
        data = await state.get_data()
        actions = fresh_pending_actions(data)
        action = actions.pop(token, None)
        await state.update_data(**{PENDING_ACTIONS_KEY: actions})
        if not action or action.get("kind") != kind:
            return None
        return action

    async def result_markup(state: FSMContext, result: AgentRunResult) -> InlineKeyboardMarkup | None:
        pending = result.pending_action
        if result.candidates:
            workers = [Worker(id=c.worker_id, full_name=c.label) for c in result.candidates]
            token = await store_pending_action(
                state,
                "target_choice",
                {
                    "sanitized_text": result.sanitized_user_message,
                    "target_ref": result.ambiguous_ref,
                    "candidate_ids": [c.worker_id for c in result.candidates],
                },
            )
            return build_agent_target_choice_keyboard(workers, token)
        if not pending:
            return None
        if pending.kind == "shift_signup" and pending.target_id and pending.shift_date and pending.shift_type:
            token = await store_pending_action(
                state,
                "shift_signup",
                {
                    "target_id": pending.target_id,
                    "shift_date": pending.shift_date,
                    "shift_type": pending.shift_type,
                    "manual": pending.manual,
                },
            )
            return build_agent_shift_signup_confirm_keyboard(token)
        if pending.kind == "shift_cancel" and pending.shift_date and pending.shift_type:
            token = await store_pending_action(
                state,
                "shift_cancel",
                {
                    "shift_date": pending.shift_date,
                    "shift_type": pending.shift_type,
                },
            )
            return build_agent_shift_cancel_confirm_keyboard(token)
        return None

    def is_current_slot(shift_date: date, shift_type: str) -> bool:
        current_type, current_date = shift_service.guess_shift_type_from_now()
        return current_type is not None and current_date == shift_date and str(current_type) == shift_type

    async def build_confirmation_text(reply: AgentRunResult) -> str:
        # Для подтверждаемых действий не используем формулировку модели
        # (она путается в названиях кнопок и markdown), а собираем текст сами.
        pending = reply.pending_action
        if pending is None:
            return reply.text or EMPTY_ANSWER
        if pending.kind == "shift_signup":
            target = await shift_service.get_worker_by_id(pending.target_id) if pending.target_id else None
            name = target.full_name if target else "выбранному сотруднику"
            question = f"Создать ручную смену с {name}?" if pending.manual else f"Записать вас на смену к {name}?"
            return f"{question}\n\nНажмите «Да» для подтверждения или «Нет» для отмены."
        if pending.kind == "shift_cancel":
            return "Отменить вашу текущую смену?\n\nНажмите «Да» для подтверждения или «Нет» для отмены."
        return reply.text or EMPTY_ANSWER

    async def save_history(
        state: FSMContext,
        history_raw: list[list[str]],
        user_message: str,
        assistant_text: str,
    ) -> None:
        updated = (history_raw + [["user", user_message], ["assistant", assistant_text]])[-MAX_HISTORY_MESSAGES:]
        await state.update_data(history=updated)

    async def safe_edit_progress(
        progress: Message,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> None:
        try:
            await progress.edit_text(text, reply_markup=reply_markup)
        except Exception:
            logger.exception("agent.progress edit failed chat_id=%s", progress.chat.id)
            await progress.answer(text, reply_markup=reply_markup)

    async def answer_question(
        message: Message,
        state: FSMContext,
        question: str,
        *,
        progress_message: Message | None = None,
        preprocessed: SanitizedAgentMessage | None = None,
        actor_id: int | None = None,
    ) -> None:
        if not question:
            await message.answer(ASK_PROMPT)
            return

        data = await state.get_data()
        history_raw: list[list[str]] = data.get("history", [])
        history = build_history(history_raw)
        progress = progress_message or await message.answer(AGENT_THINKING)
        started = perf_counter()
        chat_id = actor_id if actor_id is not None else message.from_user.id
        logger.info(
            "agent.handler start chat_id=%s question_chars=%d history=%d preprocessed=%s",
            chat_id,
            len(question),
            len(history),
            preprocessed is not None,
        )

        try:
            await message.bot.send_chat_action(message.chat.id, "typing")
            try:
                reply = await asyncio.wait_for(
                    agent.run_with_context(chat_id, question, history, preprocessed=preprocessed),
                    timeout=AGENT_RESPONSE_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                logger.warning(
                    "agent.handler timeout chat_id=%s elapsed_ms=%d timeout=%s",
                    chat_id,
                    int((perf_counter() - started) * 1000),
                    AGENT_RESPONSE_TIMEOUT_SECONDS,
                )
                await safe_edit_progress(progress, ASK_TIMEOUT)
                return

            markup = await result_markup(state, reply)
            if not reply.is_ambiguous:
                await save_history(state, history_raw, reply.sanitized_user_message, reply.sanitized_text)

            text = await build_confirmation_text(reply)
            await safe_edit_progress(progress, text, reply_markup=markup)
            logger.info(
                "agent.handler done chat_id=%s elapsed_ms=%d pending=%s ambiguous=%s answer_chars=%d",
                chat_id,
                int((perf_counter() - started) * 1000),
                reply.pending_action.kind if reply.pending_action else None,
                reply.is_ambiguous,
                len(reply.sanitized_text),
            )
        except Exception:
            logger.exception(
                "agent.handler failed chat_id=%s elapsed_ms=%d",
                chat_id,
                int((perf_counter() - started) * 1000),
            )
            await safe_edit_progress(progress, ASK_ERROR)

    @router.message(Command("ask"))
    async def start_ask(message: Message, state: FSMContext, command: CommandObject) -> None:
        await state.set_state(AgentState.asking)
        await state.update_data(history=[])
        await answer_question(message, state, (command.args or "").strip())

    @router.message(StateFilter(AgentState.asking), Command("stop"))
    async def stop_ask(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(ASK_STOPPED)

    @router.message(StateFilter(AgentState.asking), F.text & ~F.text.startswith("/"))
    async def ask_question(message: Message, state: FSMContext) -> None:
        await answer_question(message, state, (message.text or "").strip())

    @router.callback_query(AgentTargetChoice.filter())
    async def choose_agent_target(callback: CallbackQuery, callback_data: AgentTargetChoice, state: FSMContext) -> None:
        action = await pop_pending_action(state, callback_data.token, "target_choice")
        if not action:
            await callback.answer("Запрос устарел", show_alert=True)
            return
        sanitized_text = action.get("sanitized_text")
        target_ref = action.get("target_ref")
        candidate_ids = action.get("candidate_ids", [])
        if callback_data.worker_id not in candidate_ids or not sanitized_text or not target_ref:
            await callback.answer("Запрос устарел", show_alert=True)
            return

        target = await shift_service.get_worker_by_id(callback_data.worker_id)
        if not target or target.id is None:
            await callback.answer(TARGET_NOT_FOUND_MSG, show_alert=True)
            return

        await callback.message.edit_text(AGENT_THINKING)
        preprocessed = SanitizedAgentMessage(
            text=sanitized_text,
            targets={target_ref: ShiftTarget(ref=target_ref, worker_id=target.id, label=target.full_name)},
        )
        await answer_question(
            callback.message,
            state,
            sanitized_text,
            progress_message=callback.message,
            preprocessed=preprocessed,
            actor_id=callback.from_user.id,
        )
        await callback.answer()

    @router.callback_query(AgentShiftSignupConfirm.filter())
    async def confirm_agent_shift_signup(
        callback: CallbackQuery,
        callback_data: AgentShiftSignupConfirm,
        state: FSMContext,
    ) -> None:
        action = await pop_pending_action(state, callback_data.token, "shift_signup")
        if not action:
            await callback.answer("Запрос устарел", show_alert=True)
            return

        worker = await shift_service.get_worker(callback.from_user.id)
        if not worker:
            await callback.answer(WORKER_NOT_FOUND_MSG, show_alert=True)
            return

        shift_date = date.fromisoformat(str(action["shift_date"]))
        shift_type = str(action["shift_type"])
        if not is_current_slot(shift_date, shift_type):
            await callback.message.edit_text("Запрос устарел. Проверьте текущую смену заново.")
            await callback.answer()
            return

        target_id = int(action["target_id"])
        if action.get("manual"):
            signup = await shift_service.confirm_manual_signup(
                worker,
                target_id,
                shift_date,
                shift_type,
            )
        else:
            signup = await shift_service.signup_to_doctor(
                worker,
                target_id,
                shift_date,
                shift_type,
            )

        target = signup.doctor
        if not target:
            await callback.answer(TARGET_NOT_FOUND_MSG, show_alert=True)
            return

        if signup.requires_confirmation:
            reason = (
                "Этого сотрудника сейчас нет в графике работы."
                if not signup.has_schedule_slots
                else "У этого сотрудника уже заняты все слоты."
            )
            token = await store_pending_action(
                state,
                "shift_signup",
                {
                    "target_id": target.id,
                    "shift_date": shift_date.isoformat(),
                    "shift_type": shift_type,
                    "manual": True,
                },
            )
            await callback.message.edit_text(
                f"{reason} Создать ручную смену с {target.full_name}?",
                reply_markup=build_agent_shift_signup_confirm_keyboard(token),
            )
            await callback.answer()
            return

        if signup.status == ShiftSignupStatus.ALREADY_HAS_SHIFT:
            await callback.message.edit_text("У вас уже есть смена на этот слот.")
        elif signup.success:
            await callback.message.edit_text(f"Готово: смена с {target.full_name} закреплена за вами.")
        else:
            await callback.message.edit_text("Не удалось записаться на смену. Возможно, слот уже заняли.")
        await callback.answer()

    @router.callback_query(AgentShiftCancelConfirm.filter())
    async def confirm_agent_shift_cancel(
        callback: CallbackQuery,
        callback_data: AgentShiftCancelConfirm,
        state: FSMContext,
    ) -> None:
        action = await pop_pending_action(state, callback_data.token, "shift_cancel")
        if not action:
            await callback.answer("Запрос устарел", show_alert=True)
            return

        worker = await shift_service.get_worker(callback.from_user.id)
        if not worker:
            await callback.answer(WORKER_NOT_FOUND_MSG, show_alert=True)
            return
        shift_date = date.fromisoformat(str(action["shift_date"]))
        shift_type = str(action["shift_type"])
        if not is_current_slot(shift_date, shift_type):
            await callback.message.edit_text("Запрос устарел. Проверьте текущую смену заново.")
            await callback.answer()
            return
        await shift_service.remove_shift(
            worker.id,
            shift_date,
            shift_type,
        )
        await callback.message.edit_text("Смена отменена.")
        await callback.answer()

    @router.callback_query(F.data == "agent_action_cancel")
    async def cancel_agent_action(callback: CallbackQuery, state: FSMContext) -> None:
        await state.update_data(**{PENDING_ACTIONS_KEY: {}})
        await callback.message.edit_text("Действие отменено.")
        await callback.answer()

    return router
