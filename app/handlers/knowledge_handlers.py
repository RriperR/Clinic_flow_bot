from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import app.keyboards as kb
from app.application.use_cases.knowledge_base import KnowledgeBaseService
from app.logger import setup_logger

logger = setup_logger("knowledge_base", "knowledge_base.log")


def create_knowledge_router(service: KnowledgeBaseService) -> Router:
    router = Router()

    async def render_section_menu(target):
        await target.answer(
            "База знаний: выберите раздел:",
            reply_markup=kb.build_knowledge_section_keyboard(service.list_sections()),
        )

    @router.message(Command("kb"))
    async def open_knowledge(message: Message):
        await render_section_menu(message)

    @router.callback_query(F.data == "kb_menu")
    async def open_knowledge_by_button(callback: CallbackQuery):
        await callback.message.edit_text(
            "База знаний: выберите раздел:",
            reply_markup=kb.build_knowledge_section_keyboard(service.list_sections()),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("kb_section:"))
    async def select_section(callback: CallbackQuery):
        section = callback.data.split(":", 1)[1]
        manipulations = service.list_manipulations(section)

        if not manipulations:
            await callback.message.edit_text(
                f"В разделе '{section}' пока нет доступных манипуляций.",
                reply_markup=kb.build_knowledge_section_keyboard(service.list_sections()),
            )
            await callback.answer()
            return

        await callback.message.edit_text(
            f"Раздел {section}: выберите манипуляцию:",
            reply_markup=kb.build_knowledge_manipulation_keyboard(section, manipulations),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("kb_manipulation:"))
    async def select_manipulation(callback: CallbackQuery):
        _, section, index_text = callback.data.split(":", 2)
        try:
            index = int(index_text)
        except ValueError:
            await callback.answer("Неверный выбор.", show_alert=True)
            return

        manipulations = service.list_manipulations(section)
        if index < 0 or index >= len(manipulations):
            await callback.answer("Неверный выбор.", show_alert=True)
            return

        manipulation = manipulations[index]
        text = service.build_manipulation_text(section, manipulation)
        await callback.message.edit_text(
            f"📌 {manipulation}\n\n{text}",
            reply_markup=kb.build_knowledge_manipulation_back_keyboard(),
        )
        await callback.answer()

    return router
