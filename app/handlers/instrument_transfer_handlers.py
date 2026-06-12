from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import app.keyboards as kb
from app.application.instruments.transfer_use_case import InstrumentTransferService
from app.logger import setup_logger

logger = setup_logger("instrument_transfer", "instrument_transfer.log")


class InstrumentTransferState(StatesGroup):
    waiting_before_photo = State()
    choosing_destination = State()
    waiting_after_photo = State()


def create_instrument_transfer_router(
    transfer_service: InstrumentTransferService,
) -> Router:
    router = Router()

    @router.message(Command("move_instrument"))
    async def start_transfer(message: Message, state: FSMContext):
        await state.clear()
        cabinets = await transfer_service.list_cabinets()
        if not cabinets:
            await message.answer("Список кабинетов пуст. Обратитесь к администратору.")
            return

        await message.answer(
            "Выберите кабинет, в котором сейчас находится инструмент:",
            reply_markup=kb.build_cabinet_keyboard(cabinets, prefix="src_cabinet"),
        )

    @router.callback_query(F.data.startswith("src_cabinet:"))
    async def select_source_cabinet(callback: CallbackQuery, state: FSMContext):
        current_state = await state.get_state()
        if current_state:
            await state.clear()

        cabinet_id = int(callback.data.split(":", 1)[1])
        cabinet = await transfer_service.get_cabinet(cabinet_id)
        if not cabinet:
            await callback.answer("Кабинет не найден", show_alert=True)
            return

        instruments = await transfer_service.list_instruments(cabinet_id)
        if not instruments:
            cabinets = await transfer_service.list_cabinets()
            await callback.message.edit_text(
                f"В кабинете «{cabinet.name}» нет инструментов. Выберите другой кабинет:",
                reply_markup=kb.build_cabinet_keyboard(cabinets, prefix="src_cabinet"),
            )
            await callback.answer()
            return

        await state.update_data(
            source_cabinet_id=cabinet_id,
            source_cabinet_name=cabinet.name,
        )
        await callback.message.edit_text(
            f"Кабинет: {cabinet.name}\nВыберите инструмент:",
            reply_markup=kb.build_instrument_keyboard(instruments),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("instrument:"))
    async def select_instrument(callback: CallbackQuery, state: FSMContext):
        current_state = await state.get_state()
        if current_state:
            await callback.answer(
                "Сначала завершите текущий перенос или начните заново через /move_instrument",
                show_alert=True,
            )
            return

        instrument_id = int(callback.data.split(":", 1)[1])
        data = await state.get_data()
        source_cabinet_id = data.get("source_cabinet_id")
        if source_cabinet_id is None:
            await callback.answer("Сначала выберите кабинет", show_alert=True)
            return

        instrument = await transfer_service.get_instrument(instrument_id)
        if not instrument or instrument.cabinet_id != source_cabinet_id:
            await callback.answer("Инструмент недоступен", show_alert=True)
            return

        await state.update_data(
            instrument_id=instrument_id,
            instrument_name=instrument.name,
        )
        await state.set_state(InstrumentTransferState.waiting_before_photo)
        await callback.message.edit_text(f"Инструмент: {instrument.name}\nОтправьте фото инструмента перед переносом.")
        await callback.answer()

    @router.message(StateFilter(InstrumentTransferState.waiting_before_photo), F.photo)
    async def handle_before_photo(message: Message, state: FSMContext):
        photo_id = message.photo[-1].file_id
        data = await state.get_data()
        instrument_id = data.get("instrument_id")
        source_cabinet_id = data.get("source_cabinet_id")
        if source_cabinet_id is None or instrument_id is None:
            await state.clear()
            await message.answer("Сессия переноса сброшена. Начните заново: /move_instrument")
            return

        await state.update_data(before_photo_id=photo_id)
        await state.set_state(InstrumentTransferState.choosing_destination)

        sterilization = await transfer_service.get_sterilization_cabinet()
        if not sterilization:
            await state.clear()
            await message.answer("Кабинет «Стерилизационная» не найден. Обратитесь к администратору.")
            return

        if sterilization.id == source_cabinet_id:
            last_move = await transfer_service.get_last_move_for_instrument(instrument_id)
            if last_move and last_move.to_cabinet_id == sterilization.id:
                dest_cabinet = await transfer_service.get_cabinet(last_move.from_cabinet_id)
                if not dest_cabinet:
                    await state.clear()
                    await message.answer("Кабинет возврата не найден. Обратитесь к администратору.")
                    return
                await state.update_data(allowed_dest_cabinet_ids=[dest_cabinet.id])
                await message.answer(
                    "Выберите кабинет, куда возвращаем инструмент:",
                    reply_markup=kb.build_cabinet_keyboard([dest_cabinet], prefix="dest_cabinet"),
                )
                return

            cabinets = await transfer_service.list_cabinets()
            dest_cabinets = [cabinet for cabinet in cabinets if cabinet.id != sterilization.id]
            if not dest_cabinets:
                await state.clear()
                await message.answer("Нет доступных кабинетов для возврата. Обратитесь к администратору.")
                return
            await state.update_data(allowed_dest_cabinet_ids=[cabinet.id for cabinet in dest_cabinets])
            await message.answer(
                "История перемещения не найдена. Выберите кабинет возврата:",
                reply_markup=kb.build_cabinet_keyboard(dest_cabinets, prefix="dest_cabinet"),
            )
            return

        await state.update_data(allowed_dest_cabinet_ids=[sterilization.id])
        await message.answer(
            "Выберите кабинет, куда переносим инструмент:",
            reply_markup=kb.build_cabinet_keyboard([sterilization], prefix="dest_cabinet"),
        )

    @router.message(StateFilter(InstrumentTransferState.waiting_before_photo))
    async def handle_before_photo_text(message: Message):
        await message.answer("Пожалуйста, отправьте фото инструмента.")

    @router.callback_query(
        StateFilter(InstrumentTransferState.choosing_destination),
        F.data.startswith("dest_cabinet:"),
    )
    async def select_destination_cabinet(callback: CallbackQuery, state: FSMContext):
        cabinet_id = int(callback.data.split(":", 1)[1])
        data = await state.get_data()
        source_cabinet_id = data.get("source_cabinet_id")
        allowed_dest_cabinet_ids = data.get("allowed_dest_cabinet_ids")
        if source_cabinet_id is None:
            await state.clear()
            await callback.answer(
                "Сессия переноса сброшена. Начните заново: /move_instrument",
                show_alert=True,
            )
            return
        if not allowed_dest_cabinet_ids:
            await state.clear()
            await callback.answer(
                "Сессия переноса сброшена. Начните заново: /move_instrument",
                show_alert=True,
            )
            return

        if cabinet_id == source_cabinet_id:
            await callback.answer("Нужно выбрать другой кабинет", show_alert=True)
            return

        if cabinet_id not in allowed_dest_cabinet_ids:
            sterilization = await transfer_service.get_sterilization_cabinet()
            if sterilization and source_cabinet_id == sterilization.id:
                await callback.answer(
                    "Выберите кабинет из списка",
                    show_alert=True,
                )
            else:
                await callback.answer("Перенос возможен только в «Стерилизационную»", show_alert=True)
            return

        cabinet = await transfer_service.get_cabinet(cabinet_id)
        if not cabinet:
            await callback.answer("Кабинет не найден", show_alert=True)
            return

        await state.update_data(
            dest_cabinet_id=cabinet_id,
            dest_cabinet_name=cabinet.name,
        )
        await state.set_state(InstrumentTransferState.waiting_after_photo)
        await callback.message.edit_text(
            f"Кабинет назначения: {cabinet.name}\nОтправьте фото инструмента в новом кабинете."
        )
        await callback.answer()

    @router.message(StateFilter(InstrumentTransferState.waiting_after_photo), F.photo)
    async def handle_after_photo(message: Message, state: FSMContext):
        photo_id = message.photo[-1].file_id
        data = await state.get_data()
        instrument_id = data.get("instrument_id")
        source_cabinet_id = data.get("source_cabinet_id")
        dest_cabinet_id = data.get("dest_cabinet_id")
        before_photo_id = data.get("before_photo_id")

        if instrument_id is None or source_cabinet_id is None or dest_cabinet_id is None or before_photo_id is None:
            await state.clear()
            await message.answer("Сессия переноса сброшена. Начните заново: /move_instrument")
            return

        success = await transfer_service.transfer_instrument(
            instrument_id=instrument_id,
            from_cabinet_id=source_cabinet_id,
            to_cabinet_id=dest_cabinet_id,
            before_photo_id=before_photo_id,
            after_photo_id=photo_id,
            moved_by_chat_id=str(message.from_user.id),
        )

        if success:
            instrument_name = data.get("instrument_name", "Инструмент")
            source_name = data.get("source_cabinet_name", "")
            dest_name = data.get("dest_cabinet_name", "")
            details = f"Перенос сохранен: {instrument_name}"
            if source_name and dest_name:
                details += f" ({source_name} -> {dest_name})"
            await message.answer(details)
            logger.info(
                "Instrument %s moved from %s to %s by chat_id=%s",
                instrument_id,
                source_cabinet_id,
                dest_cabinet_id,
                message.from_user.id,
            )
        else:
            await message.answer("Не удалось сохранить перенос. Проверьте данные и повторите.")
            logger.warning(
                "Failed to move instrument %s from %s to %s by chat_id=%s",
                instrument_id,
                source_cabinet_id,
                dest_cabinet_id,
                message.from_user.id,
            )

        await state.clear()

    @router.message(StateFilter(InstrumentTransferState.waiting_after_photo))
    async def handle_after_photo_text(message: Message):
        await message.answer("Пожалуйста, отправьте фото инструмента в новом кабинете.")

    return router
