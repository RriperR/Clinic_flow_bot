from datetime import datetime
from typing import Sequence

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.application.use_cases.registration import RegistrationService
from app.domain.entities import Worker, Cabinet, Instrument


class SelectDoctor(CallbackData, prefix="msd"):
    doctor_id: int


class DoctorsPage(CallbackData, prefix="dpg"):
    page: int


async def build_worker_keyboard(registration: RegistrationService) -> InlineKeyboardMarkup:
    workers = await registration.list_unregistered()

    builder = InlineKeyboardBuilder()

    if not workers:
        builder.button(
            text="Нет доступных сотрудников: все уже зарегистрированы",
            callback_data="noop",
        )

    for worker in workers:
        builder.button(
            text=worker.full_name,
            callback_data=f"select_worker:{worker.id}",
        )

    builder.adjust(1)
    return builder.as_markup()


def build_confirm_keyboard(worker_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, это я", callback_data=f"confirm_yes:{worker_id}",
                ),
                InlineKeyboardButton(
                    text="Нет", callback_data="confirm_no",
                ),
            ]
        ]
    )


async def build_int_keyboard(question_index) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    timestamp = int(datetime.now().timestamp())

    for i in range(1, 6):
        builder.button(
            text=str(i),
            callback_data=f"rate:{question_index}:{i}:{timestamp}",
        )
    builder.adjust(5)
    return builder.as_markup()


def build_shift_keyboard(
    shifts: list[tuple[int, str]], include_show_all: bool = True
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for shift_id, name in shifts:
        builder.button(
            text=name,
            callback_data=f"select_shift:{shift_id}",
        )
    if include_show_all:
        builder.button(
            text="Показать всех врачей",
            callback_data="shift_show_all",
        )
    builder.adjust(1)
    return builder.as_markup()


def build_cabinet_keyboard(
    cabinets: Sequence[Cabinet],
    prefix: str = "cabinet",
    exclude_id: int | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cabinet in cabinets:
        if exclude_id is not None and cabinet.id == exclude_id:
            continue
        builder.button(
            text=cabinet.name[:64],
            callback_data=f"{prefix}:{cabinet.id}",
        )
    builder.adjust(1)
    return builder.as_markup()


def build_instrument_keyboard(instruments: Sequence[Instrument]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for instrument in instruments:
        builder.button(
            text=instrument.name[:64],
            callback_data=f"instrument:{instrument.id}",
        )
    builder.adjust(1)
    return builder.as_markup()


PER_PAGE = 10


def build_all_doctors_keyboard(
    workers: Sequence[Worker], page: int = 0
) -> InlineKeyboardMarkup:
    total = len(workers)
    start = page * PER_PAGE
    end = min(start + PER_PAGE, total)

    builder = InlineKeyboardBuilder()

    for w in workers[start:end]:
        builder.button(
            text=w.full_name[:64],
            callback_data=SelectDoctor(doctor_id=w.id).pack(),
        )

    nav = InlineKeyboardBuilder()
    if start > 0:
        nav.button(text="Назад", callback_data=DoctorsPage(page=page - 1).pack())
    if end < total:
        nav.button(text="Вперёд", callback_data=DoctorsPage(page=page + 1).pack())

    builder.adjust(1)
    if nav.buttons:
        builder.row(*nav.buttons)

    return builder.as_markup()


def build_cancel_shift_keyboard(shift_type: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Отменить смену",
        callback_data=f"cancel_shift:{shift_type}",
    )
    builder.adjust(1)
    return builder.as_markup()
