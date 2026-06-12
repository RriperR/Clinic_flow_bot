from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.application.instruments.admin_use_case import InstrumentAdminService
from app.domain.entities import InstrumentMove
from app.logger import setup_logger

logger = setup_logger("moves", "moves.log")


def create_moves_router(moves_service: InstrumentAdminService) -> Router:
    router = Router()

    def build_moves_keyboard(moves: list[InstrumentMove]):
        builder = InlineKeyboardBuilder()
        for move in moves:
            builder.row(
                InlineKeyboardButton(
                    text=f"📷 До #{move.id}",
                    callback_data=f"moves_photo:before:{move.id}",
                ),
                InlineKeyboardButton(
                    text=f"📷 После #{move.id}",
                    callback_data=f"moves_photo:after:{move.id}",
                ),
            )
        builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="moves_refresh"))
        return builder.as_markup()

    async def render_moves(target: Message | CallbackQuery):
        moves = await moves_service.list_recent_moves(limit=10)
        cabinets = await moves_service.list_cabinets(include_archived=True)
        cabinet_map = {c.id: c.name for c in cabinets}

        instruments = []
        for cabinet in cabinets:
            instruments.extend(await moves_service.list_instruments(cabinet.id, include_archived=True))
        instrument_map = {i.id: i.name for i in instruments}

        if not moves:
            text = "📦 Перемещений пока нет."
        else:
            blocks = []
            for move in moves:
                inst_name = instrument_map.get(move.instrument_id, f"#{move.instrument_id}")
                from_name = cabinet_map.get(move.from_cabinet_id, f"#{move.from_cabinet_id}")
                to_name = cabinet_map.get(move.to_cabinet_id, f"#{move.to_cabinet_id}")
                blocks.append(f"#{move.id} 🕒 {move.moved_at} — {inst_name}\n{from_name} ➡️ {to_name}")
            text = "📦 Последние перемещения:\n" + "\n\n".join(blocks)

        markup = build_moves_keyboard(moves) if moves else None
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=markup)
        else:
            await target.answer(text, reply_markup=markup)

    @router.message(Command("moves"))
    async def moves_list(message: Message):
        await render_moves(message)

    @router.callback_query(F.data == "moves_refresh")
    async def moves_refresh(callback: CallbackQuery):
        await render_moves(callback)
        await callback.answer()

    @router.callback_query(F.data.startswith("moves_photo:"))
    async def moves_photo(callback: CallbackQuery):
        _, kind, move_id = callback.data.split(":")
        move = await moves_service.get_move(int(move_id))
        if not move:
            await callback.answer("⛔ Перемещение не найдено", show_alert=True)
            return
        photo_id = move.before_photo_id if kind == "before" else move.after_photo_id
        if not photo_id:
            await callback.answer("📭 Фото отсутствует", show_alert=True)
            return
        caption = "📷 Фото до" if kind == "before" else "📷 Фото после"
        await callback.message.answer_photo(photo=photo_id, caption=caption)
        await callback.answer()

    return router
