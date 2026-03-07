from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from app.application.use_cases.shift_management import ShiftService
from app.application.use_cases.worker_report import WorkerReportService
from app.keyboards import (
    build_shift_keyboard,
    build_all_doctors_keyboard,
    build_cancel_shift_keyboard,
    build_manual_shift_confirm_keyboard,
    DoctorsPage,
    ManualShiftConfirm,
    SelectDoctor,
)
from app.logger import setup_logger

logger = setup_logger("shift", "shift.log")
SHIFT_TIME_MSG = "Записываться на смену можно с 07:30 до 20:30"
WORKER_NOT_FOUND_MSG = "Мы не нашли вас в базе"
WORKER_NOT_FOUND_START_MSG = "Мы не нашли вас в базе, сначала зарегистрируйтесь"
DOCTOR_NOT_FOUND_MSG = "Доктор не найден"


def create_shift_router(
    shift_service: ShiftService,
    report_service: WorkerReportService | None = None,
) -> Router:
    router = Router()

    def readable_shift(shift_type: str) -> str:
        return "Утренняя" if shift_type == "morning" else "Вечерняя"

    async def resolve_worker_message(chat_id: int) -> str | None:
        inactive = await shift_service.get_worker(chat_id, include_inactive=True)
        if inactive and not inactive.is_active:
            return "Ваш аккаунт деактивирован. Обратитесь к администратору."
        return None

    async def get_worker_for_message(message: Message):
        worker = await shift_service.get_worker(message.from_user.id)
        if worker:
            return worker
        inactive_msg = await resolve_worker_message(message.from_user.id)
        await message.answer(inactive_msg or WORKER_NOT_FOUND_START_MSG)
        return None

    async def get_worker_for_callback(callback: CallbackQuery):
        worker = await shift_service.get_worker(callback.from_user.id)
        if worker:
            return worker
        inactive_msg = await resolve_worker_message(callback.from_user.id)
        await callback.answer(
            inactive_msg or WORKER_NOT_FOUND_MSG,
            show_alert=True,
        )
        return None

    async def build_report_suffix(worker) -> str:
        if not report_service:
            return ""
        try:
            report_text = report_service.build_report_for_worker(worker)
        except Exception:
            logger.exception("Failed to build shift report for worker=%s", worker.id)
            return ""
        if not report_text:
            return ""
        return f"\n\n{report_text}"

    @router.message(Command("shift"))
    async def show_doctors(message: Message):
        shift_type, date_str = shift_service.guess_shift_type_from_now()
        if not shift_type:
            await message.answer(SHIFT_TIME_MSG)
            return

        worker = await get_worker_for_message(message)
        if not worker:
            return

        current_shift = await shift_service.get_current_shift(worker.id, date_str, shift_type)
        if current_shift:
            await message.answer(
                f"У вас уже есть смена с {current_shift.doctor_name}",
                reply_markup=build_cancel_shift_keyboard(shift_type),
            )
            return

        free_shifts = await shift_service.list_free_shifts(
            date_str, shift_type, worker.full_name
        )
        if not free_shifts:
            await message.answer(
                "Свободных смен не осталось",
                reply_markup=build_shift_keyboard([]),
            )
            return
        await message.answer(
            "Выберите доктора:",
            reply_markup=build_shift_keyboard(free_shifts),
        )

    @router.callback_query(F.data.startswith("select_shift:"))
    async def mark_shift(callback: CallbackQuery):
        shift_id = int(callback.data.split(":", 1)[1])
        shift_type, date_str = shift_service.guess_shift_type_from_now()
        if not shift_type:
            await callback.answer(SHIFT_TIME_MSG, show_alert=True)
            return

        worker = await get_worker_for_callback(callback)
        if not worker:
            return

        shift = await shift_service.get_shift_by_id(shift_id)
        if not shift or shift.date != date_str or shift.type != shift_type:
            await callback.answer("Эта смена недоступна", show_alert=True)
            return

        success = await shift_service.add_shift_by_id(
            worker.id,
            worker.full_name,
            shift_id,
        )
        if success:
            report_suffix = await build_report_suffix(worker)
            await callback.message.edit_text(
                f"Готово ✔ {readable_shift(shift_type)} смена у {shift.doctor_name} закреплена за вами"
                f"{report_suffix}"
            )
        else:
            await callback.message.edit_text(
                "Не удалось записаться на смену. Скорее всего, её уже заняли."
            )
        await callback.answer()

    @router.callback_query(F.data.startswith("cancel_shift:"))
    async def cancel_shift(callback: CallbackQuery):
        shift_type = callback.data.split(":", 1)[1]
        now = datetime.now()
        date_str = now.strftime("%d.%m.%Y")
        worker = await shift_service.get_worker(callback.from_user.id)
        if worker:
            await shift_service.remove_shift(worker.id, date_str, shift_type)
            await callback.message.edit_text("Смена отменена")
        await callback.answer()

    @router.callback_query(F.data == "shift_show_all")
    async def show_all_doctors(callback: CallbackQuery):
        shift_type, date_str = shift_service.guess_shift_type_from_now()
        if not shift_type:
            await callback.answer(SHIFT_TIME_MSG, show_alert=True)
            return

        worker = await get_worker_for_callback(callback)
        if not worker:
            return

        current_shift = await shift_service.get_current_shift(worker.id, date_str, shift_type)
        if current_shift:
            await callback.message.edit_text(
                f"У вас уже есть смена с {current_shift.doctor_name}",
                reply_markup=build_cancel_shift_keyboard(shift_type),
            )
            await callback.answer()
            return

        workers = await shift_service.list_all_doctors()
        await callback.message.edit_text(
            "Выберите доктора:",
            reply_markup=build_all_doctors_keyboard(workers, page=0),
        )
        await callback.answer()

    @router.callback_query(DoctorsPage.filter())
    async def doctors_paginate(cb: CallbackQuery, callback_data: DoctorsPage):
        workers = await shift_service.list_all_doctors()
        await cb.message.edit_reply_markup(
            reply_markup=build_all_doctors_keyboard(workers, page=callback_data.page)
        )
        await cb.answer()

    @router.callback_query(SelectDoctor.filter())
    async def doctor_selected(cb: CallbackQuery, callback_data: SelectDoctor):
        shift_type, date_str = shift_service.guess_shift_type_from_now()
        if not shift_type:
            await cb.answer(SHIFT_TIME_MSG, show_alert=True)
            return

        worker = await get_worker_for_callback(cb)
        if not worker:
            return

        doctor = await shift_service.get_worker_by_id(callback_data.doctor_id)
        if not doctor:
            await cb.answer(DOCTOR_NOT_FOUND_MSG, show_alert=True)
            return

        doctor_shifts = await shift_service.list_doctor_shifts(
            date_str, shift_type, doctor.full_name
        )
        if not doctor_shifts:
            await cb.message.edit_text(
                "Этого врача сейчас нет в графике работы. Вы уверены что хотите создать с ним смену?",
                reply_markup=build_manual_shift_confirm_keyboard(doctor.id),
            )
            await cb.answer()
            return

        free_slot = await shift_service.get_preferred_free_doctor_slot(
            date_str,
            shift_type,
            doctor.full_name,
            worker.full_name,
        )
        if free_slot and free_slot.id is not None:
            success = await shift_service.add_shift_by_id(
                worker.id,
                worker.full_name,
                free_slot.id,
            )
            if success:
                report_suffix = await build_report_suffix(worker)
                await cb.message.edit_text(
                    f"Готово ✔ {readable_shift(shift_type)} смена у {doctor.full_name} закреплена за вами"
                    f"{report_suffix}"
                )
            else:
                await cb.message.edit_text(
                    "Не удалось записаться на смену. Скорее всего, её уже заняли."
                )
            await cb.answer()
            return

        await cb.message.edit_text(
            "‼️‼️ Внимание! ‼️‼️\n"
            "У этого врача уже есть смена с другим ассистентом, вы уверены что хотите создать с ним дополнительную смену?",
            reply_markup=build_manual_shift_confirm_keyboard(doctor.id),
        )
        await cb.answer()
        return

    @router.callback_query(ManualShiftConfirm.filter())
    async def confirm_manual_shift(cb: CallbackQuery, callback_data: ManualShiftConfirm):
        shift_type, date_str = shift_service.guess_shift_type_from_now()
        if not shift_type:
            await cb.answer(SHIFT_TIME_MSG, show_alert=True)
            return

        worker = await get_worker_for_callback(cb)
        if not worker:
            return

        doctor = await shift_service.get_worker_by_id(callback_data.doctor_id)
        if not doctor:
            await cb.answer(DOCTOR_NOT_FOUND_MSG, show_alert=True)
            return

        free_slot = await shift_service.get_preferred_free_doctor_slot(
            date_str,
            shift_type,
            doctor.full_name,
            worker.full_name,
        )
        if free_slot and free_slot.id is not None:
            success = await shift_service.add_shift_by_id(
                worker.id,
                worker.full_name,
                free_slot.id,
            )
        else:
            success = await shift_service.add_manual_shift(
                worker.id,
                worker.full_name,
                doctor.full_name,
                shift_type,
                date_str,
            )

        if success:
            report_suffix = await build_report_suffix(worker)
            await cb.message.edit_text(
                f"Готово ✔ {readable_shift(shift_type)} смена у {doctor.full_name} закреплена за вами"
                f"{report_suffix}"
            )
        else:
            await cb.message.edit_text("Не удалось записаться на смену")
        await cb.answer()

    @router.callback_query(F.data == "manual_shift_cancel")
    async def cancel_manual_shift(cb: CallbackQuery):
        await cb.message.edit_text("Выбор отменён.")
        await cb.answer()

    return router
