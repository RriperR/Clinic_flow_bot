from aiogram import F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.application.use_cases.registration import RegistrationService
import app.keyboards as kb
from app.logger import setup_logger


logger = setup_logger("reg_handlers", "reg.log")

class RegistrationState(StatesGroup):
    waiting_photo = State()


def create_register_router(registration: RegistrationService) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def start(message: Message):
        user = message.from_user
        logger.info(
            "User (id=%s, username=%s) triggered '/start'", user.id, user.username
        )
        await message.answer(
            "Привет! Выбери себя в списке, чтобы зарегистрироваться:",
            reply_markup=await kb.build_worker_keyboard(registration),
        )

    @router.callback_query(F.data.startswith("select_worker:"))
    async def register_worker(callback: CallbackQuery):
        worker_id = int(callback.data.split(":", 1)[1])
        worker = await registration.get_by_id(worker_id)

        logger.info("User (id=%s) chose %s", callback.from_user.id, worker.full_name)

        await callback.message.edit_text(
            f"Это ты: {worker.full_name}?",
            reply_markup=kb.build_confirm_keyboard(worker_id),
            parse_mode="HTML",
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("confirm_yes:"))
    async def confirm_register(callback: CallbackQuery, state: FSMContext):
        worker_id = int(callback.data.split(":", 1)[1])
        success = await registration.set_chat_id(worker_id, str(callback.from_user.id))

        if not success:
            worker = await registration.get_by_chat_id(callback.from_user.id)
            await callback.message.edit_text(
                f"Этот аккаунт уже привязан к {worker.full_name}"
            )
            await callback.answer()
            logger.info("User (id=%s) tried to relink account", callback.from_user.id)
            return

        await callback.message.edit_text(
            "Готово! Теперь отправь фото, чтобы мы закрепили его за твоим профилем (не обязательно)"
        )
        await state.set_state(RegistrationState.waiting_photo)
        await callback.answer()

        logger.info("User (id=%s) linked account", callback.from_user.id)

    @router.callback_query(F.data == "confirm_no")
    async def cancel_register(callback: CallbackQuery):
        await callback.message.edit_text(
            "Хорошо, попробуй выбрать себя ещё раз:",
            reply_markup=await kb.build_worker_keyboard(registration),
        )
        await callback.answer()

        logger.info("User (id=%s) canceled worker selection", callback.from_user.id)

    @router.message(StateFilter(RegistrationState.waiting_photo), F.photo)
    async def handle_worker_photo(message: Message, state: FSMContext):
        photo = message.photo[-1]
        file_id = photo.file_id

        worker = await registration.get_by_chat_id(message.from_user.id)

        if not worker:
            inactive = await registration.get_by_chat_id(
                message.from_user.id, include_inactive=True
            )
            if inactive and not inactive.is_active:
                await message.answer(
                    "Ваш аккаунт деактивирован. Обратитесь к администратору."
                )
            else:
                await message.answer(
                    "Похоже, ты ещё не выбрал(а) себя. Вернись к /start и зарегистрируйся."
                )
            await state.clear()
            return

        try:
            await registration.set_worker_photo(worker.id, file_id)
            await message.answer("Фото сохранено. Спасибо!")
            await state.clear()
        except Exception:
            await message.answer("Не удалось сохранить фото, попробуй позже.")
            await state.clear()

    return router
