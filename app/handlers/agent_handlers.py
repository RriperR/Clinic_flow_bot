from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from app.application.agent.use_case import AgentService
from app.application.llm.ports import LlmMessage, LlmRole
from app.logger import setup_logger

logger = setup_logger("agent", "agent.log")

ASK_PROMPT = "Задайте вопрос по базе знаний клиники. Для выхода — /stop."
ASK_STOPPED = "Режим вопросов завершён."
ASK_ERROR = "Не удалось получить ответ, попробуйте позже."
EMPTY_ANSWER = "Пустой ответ."

# Сколько последних реплик (user/assistant) держим в контексте диалога.
MAX_HISTORY_MESSAGES = 10


class AgentState(StatesGroup):
    asking = State()


def create_agent_router(agent: AgentService) -> Router:
    router = Router()

    async def answer_question(message: Message, state: FSMContext, question: str) -> None:
        if not question:
            await message.answer(ASK_PROMPT)
            return

        data = await state.get_data()
        history_raw: list[list[str]] = data.get("history", [])
        history = [LlmMessage(role=LlmRole(role), content=content) for role, content in history_raw]

        await message.bot.send_chat_action(message.chat.id, "typing")
        try:
            reply = await agent.run(question, history)
        except Exception:
            logger.exception("agent.run failed for chat=%s", message.chat.id)
            await message.answer(ASK_ERROR)
            return

        history_raw = (history_raw + [["user", question], ["assistant", reply]])[-MAX_HISTORY_MESSAGES:]
        await state.update_data(history=history_raw)
        await message.answer(reply or EMPTY_ANSWER)

    @router.message(Command("ask"))
    async def start_ask(message: Message, state: FSMContext, command: CommandObject) -> None:
        await state.set_state(AgentState.asking)
        await state.update_data(history=[])
        await answer_question(message, state, (command.args or "").strip())

    @router.message(StateFilter(AgentState.asking), Command("stop"))
    async def stop_ask(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(ASK_STOPPED)

    # Обычный текст (не команда) в режиме вопросов уходит агенту; команды
    # проваливаются дальше к своим роутерам.
    @router.message(StateFilter(AgentState.asking), F.text & ~F.text.startswith("/"))
    async def ask_question(message: Message, state: FSMContext) -> None:
        await answer_question(message, state, (message.text or "").strip())

    return router
