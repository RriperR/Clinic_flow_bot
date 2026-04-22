from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.application.use_cases.survey_flow import SurveyFlowService
from app.domain.entities import Pair
from app.keyboards import build_int_keyboard
from app.logger import setup_logger

logger = setup_logger("actions", "actions.log")


class SurveyState(StatesGroup):
    answers = State()


async def start_pair_survey(
    bot: Bot,
    chat_id: int,
    pair: Pair,
    survey_service: SurveyFlowService,
    state: FSMContext | None = None,
    dp: Dispatcher | None = None,
    file_id: str | None = None,
) -> None:
    intro = f"{pair.date} с вами работает: {pair.object}.\nПожалуйста, оцените коллегу: {pair.survey}"
    if file_id:
        await bot.send_photo(chat_id=chat_id, photo=file_id, caption=intro)
    else:
        await bot.send_message(chat_id, text=intro)

    if state is None:
        state = dp.fsm.get_context(bot, chat_id, chat_id)

    survey = await survey_service.get_survey(pair.survey)
    await state.update_data(survey=survey, pair=pair, answers=[])

    await ask_next_question(
        bot=bot,
        user_id=chat_id,
        question_index=1,
        state=state,
    )


async def ask_next_question(bot, user_id: int, question_index: int, state: FSMContext) -> None:
    data = await state.get_data()
    survey = data.get("survey")

    q_text = getattr(survey, f"question{question_index}")
    q_type = getattr(survey, f"question{question_index}_type")

    if q_type == "int":
        await bot.send_message(chat_id=user_id, text=q_text, reply_markup=await build_int_keyboard(question_index))
    else:
        await state.set_state(SurveyState.answers)
        await bot.send_message(chat_id=user_id, text=q_text)


def create_survey_router(survey_service: SurveyFlowService) -> Router:
    router = Router()

    @router.callback_query(F.data.startswith("rate:"))
    async def handle_rate(callback: CallbackQuery, state: FSMContext):
        _, question_index, rate, timestamp = callback.data.split(":")
        idx = int(question_index)

        created_time = datetime.fromtimestamp(int(timestamp))
        now = datetime.now()

        if (now - created_time).total_seconds() > 86400:
            await callback.message.edit_text(text="Время для ответа истекло", reply_markup=None)
            return

        data = await state.get_data()
        answers: list = data.get("answers")
        if idx > 1 and len(answers) == 0:
            await callback.message.edit_text(text="Время для ответа истекло", reply_markup=None)
            return

        answers.append(rate)
        await state.update_data(answers=answers)

        await callback.answer(f"Вы выбрали: {rate}")

        pair = data.get("pair")
        subject = pair.subject

        user = callback.from_user
        logger.info(
            "User %s (id=%s, username=%s) answered via callback_data='%s'",
            subject,
            user.id,
            user.username,
            callback.data,
        )

        text = callback.message.text
        text += f"\n\n Вы выбрали: {rate}"

        await callback.message.edit_text(text=text, reply_markup=None)

        await ask_next_question(bot=callback.bot, user_id=callback.from_user.id, question_index=idx + 1, state=state)

    @router.message(StateFilter(SurveyState.answers))
    async def handle_text_answer(message: Message, state: FSMContext):
        data = await state.get_data()
        answers: list = data.get("answers")
        answers.append(message.text)
        await state.update_data(answers=answers)

        idx = len(answers)

        pair: Pair = data.get("pair")
        subject: str = pair.subject
        user = message.from_user
        logger.info(
            "User %s (id=%s, username=%s) answered '%s' to question %s. pair id: %s",
            subject,
            user.id,
            user.username,
            message.text,
            idx,
            pair.id,
        )

        if idx < 5:
            await ask_next_question(bot=message.bot, user_id=message.from_user.id, question_index=idx + 1, state=state)
        else:
            survey = data.get("survey")
            try:
                await survey_service.save_answers(pair, survey, data.get("answers"))
                await survey_service.mark_pair_status(pair.id, "done")
            except Exception as exc:
                logger.error("Failed to save answers for pair %s: %s", pair.id, exc)

            await state.clear()

            next_pair = await survey_service.get_next_ready_pair(pair.subject)
            if next_pair:
                await survey_service.mark_pair_status(next_pair.id, "in_progress")
                file_id = await survey_service.get_worker_file_id(next_pair.object)
                await start_pair_survey(
                    message.bot,
                    message.from_user.id,
                    next_pair,
                    survey_service,
                    state=state,
                    file_id=file_id,
                )
            else:
                await message.answer("Спасибо! На сегодня опросы закончились.")

    return router
