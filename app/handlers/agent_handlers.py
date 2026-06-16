from datetime import date

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.application.agent.privacy import SanitizedAgentMessage, ShiftTarget
from app.application.agent.tools import AgentPendingAction
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
EMPTY_ANSWER = "Пустой ответ."
AGENT_THINKING = "Агент думает..."
WORKER_NOT_FOUND_MSG = "Мы не нашли вас в базе, сначала зарегистрируйтесь."
TARGET_NOT_FOUND_MSG = "Цель смены не найдена."

MAX_HISTORY_MESSAGES = 10


class AgentState(StatesGroup):
    asking = State()


def create_agent_router(agent: AgentService, shift_service: ShiftService) -> Router:
    router = Router()

    def build_history(history_raw: list[list[str]]) -> list[LlmMessage]:
        return [LlmMessage(role=LlmRole(role), content=content) for role, content in history_raw]

    def result_markup(result: AgentRunResult) -> InlineKeyboardMarkup | None:
        pending = result.pending_action
        if result.candidates:
            workers = [Worker(id=c.worker_id, full_name=c.label) for c in result.candidates]
            return build_agent_target_choice_keyboard(workers)
        if not pending:
            return None
        if pending.kind == "shift_signup" and pending.target_id and pending.shift_date and pending.shift_type:
            return build_agent_shift_signup_confirm_keyboard(
                pending.target_id,
                pending.shift_date,
                pending.shift_type,
                manual=pending.manual,
            )
        if pending.kind == "shift_cancel" and pending.shift_date and pending.shift_type:
            return build_agent_shift_cancel_confirm_keyboard(pending.shift_date, pending.shift_type)
        return None

    def append_confirmation_prompt(text: str, pending: AgentPendingAction | None) -> str:
        if not pending:
            return text
        if pending.kind == "shift_signup":
            prompt = "Подтвердить создание ручной смены?" if pending.manual else "Подтвердить запись на смену?"
            return f"{text}\n\n{prompt}"
        if pending.kind == "shift_cancel":
            return f"{text}\n\nПодтвердить отмену смены?"
        return text

    async def save_history(
        state: FSMContext,
        history_raw: list[list[str]],
        user_message: str,
        assistant_text: str,
    ) -> None:
        updated = (history_raw + [["user", user_message], ["assistant", assistant_text]])[-MAX_HISTORY_MESSAGES:]
        await state.update_data(history=updated)

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

        await message.bot.send_chat_action(message.chat.id, "typing")
        try:
            chat_id = actor_id if actor_id is not None else message.from_user.id
            reply = await agent.run_with_context(chat_id, question, history, preprocessed=preprocessed)
        except Exception:
            logger.exception("agent.run failed for chat=%s", message.chat.id)
            await progress.edit_text(ASK_ERROR)
            return

        markup = result_markup(reply)
        if reply.is_ambiguous:
            await state.update_data(
                agent_pending_sanitized_text=reply.sanitized_user_message,
                agent_pending_ref=reply.ambiguous_ref,
            )
        else:
            await save_history(state, history_raw, reply.sanitized_user_message, reply.sanitized_text)

        text = append_confirmation_prompt(reply.text or EMPTY_ANSWER, reply.pending_action)
        await progress.edit_text(text, reply_markup=markup)

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
        data = await state.get_data()
        sanitized_text = data.get("agent_pending_sanitized_text")
        target_ref = data.get("agent_pending_ref")
        if not sanitized_text or not target_ref:
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
        await state.update_data(agent_pending_sanitized_text=None, agent_pending_ref=None)
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
    ) -> None:
        worker = await shift_service.get_worker(callback.from_user.id)
        if not worker:
            await callback.answer(WORKER_NOT_FOUND_MSG, show_alert=True)
            return

        shift_date = date.fromisoformat(callback_data.shift_date)
        if callback_data.manual:
            signup = await shift_service.confirm_manual_signup(
                worker,
                callback_data.target_id,
                shift_date,
                callback_data.shift_type,
            )
        else:
            signup = await shift_service.signup_to_doctor(
                worker,
                callback_data.target_id,
                shift_date,
                callback_data.shift_type,
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
            await callback.message.edit_text(
                f"{reason} Создать ручную смену с {target.full_name}?",
                reply_markup=build_agent_shift_signup_confirm_keyboard(
                    target.id,
                    callback_data.shift_date,
                    callback_data.shift_type,
                    manual=True,
                ),
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
    ) -> None:
        worker = await shift_service.get_worker(callback.from_user.id)
        if not worker:
            await callback.answer(WORKER_NOT_FOUND_MSG, show_alert=True)
            return
        await shift_service.remove_shift(
            worker.id,
            date.fromisoformat(callback_data.shift_date),
            callback_data.shift_type,
        )
        await callback.message.edit_text("Смена отменена.")
        await callback.answer()

    @router.callback_query(F.data == "agent_action_cancel")
    async def cancel_agent_action(callback: CallbackQuery, state: FSMContext) -> None:
        await state.update_data(agent_pending_sanitized_text=None, agent_pending_ref=None)
        await callback.message.edit_text("Действие отменено.")
        await callback.answer()

    return router
