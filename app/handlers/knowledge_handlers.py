from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import app.keyboards as kb
from app.application.knowledge_base.use_case import KnowledgeBaseService

KNOWLEDGE_BASE_NOT_CONFIGURED_TEXT = "База знаний не настроена: не указана таблица KNOWLEDGE_TABLE."
KNOWLEDGE_BASE_EMPTY_TEXT = "База знаний пока не загружена. Обратитесь к администратору."
SECTION_MENU_TEXT = "База знаний: выберите раздел:"
INVALID_SELECTION_TEXT = "Неверный выбор."


def create_knowledge_router(service: KnowledgeBaseService) -> Router:
    router = Router()

    async def render_section_menu(target: Message | CallbackQuery) -> None:
        if not service.is_configured():
            if isinstance(target, CallbackQuery):
                await target.answer(KNOWLEDGE_BASE_NOT_CONFIGURED_TEXT, show_alert=True)
            else:
                await target.answer(KNOWLEDGE_BASE_NOT_CONFIGURED_TEXT)
            return

        sections = await service.list_sections()
        if not sections:
            if isinstance(target, CallbackQuery):
                await target.answer(KNOWLEDGE_BASE_EMPTY_TEXT, show_alert=True)
            else:
                await target.answer(KNOWLEDGE_BASE_EMPTY_TEXT)
            return

        markup = kb.build_knowledge_section_keyboard(sections)
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(SECTION_MENU_TEXT, reply_markup=markup)
            await target.answer()
        else:
            await target.answer(SECTION_MENU_TEXT, reply_markup=markup)

    async def render_manipulation_menu(
        callback: CallbackQuery,
        section_id: int,
        page: int = 0,
    ) -> None:
        section = await service.get_section(section_id)
        if section is None:
            await callback.answer(INVALID_SELECTION_TEXT, show_alert=True)
            return

        manipulations = await service.list_manipulations(section_id)
        if not manipulations:
            await callback.message.edit_text(
                f"В разделе '{section.title}' пока нет доступных манипуляций.",
                reply_markup=kb.build_knowledge_section_keyboard(await service.list_sections()),
            )
            await callback.answer()
            return

        max_page = (len(manipulations) - 1) // kb.KNOWLEDGE_MANIPULATIONS_PER_PAGE
        page = max(0, min(page, max_page))

        await callback.message.edit_text(
            f"Раздел {section.title}: выберите манипуляцию:",
            reply_markup=kb.build_knowledge_manipulation_keyboard(
                section_id=section_id,
                manipulations=manipulations,
                page=page,
            ),
        )
        await callback.answer()

    @router.message(Command("base"))
    async def open_knowledge(message: Message) -> None:
        await render_section_menu(message)

    @router.callback_query(F.data == "kb_menu")
    async def open_knowledge_by_button(callback: CallbackQuery) -> None:
        await render_section_menu(callback)

    @router.callback_query(F.data.startswith("kb_section:"))
    async def select_section(callback: CallbackQuery) -> None:
        try:
            section_id = int(callback.data.split(":", 1)[1])
        except ValueError:
            await callback.answer(INVALID_SELECTION_TEXT, show_alert=True)
            return

        await render_manipulation_menu(callback, section_id=section_id, page=0)

    @router.callback_query(F.data.startswith("kb_manipulations_page:"))
    async def change_manipulations_page(callback: CallbackQuery) -> None:
        try:
            _, section_id_text, page_text = callback.data.split(":", 2)
            section_id = int(section_id_text)
            page = int(page_text)
        except ValueError:
            await callback.answer(INVALID_SELECTION_TEXT, show_alert=True)
            return

        await render_manipulation_menu(
            callback,
            section_id=section_id,
            page=page,
        )

    @router.callback_query(F.data.startswith("kb_manipulation:"))
    async def select_manipulation(callback: CallbackQuery) -> None:
        try:
            _, section_id_text, manipulation_id_text, page_text = callback.data.split(":", 3)
            section_id = int(section_id_text)
            manipulation_id = int(manipulation_id_text)
            page = int(page_text)
        except ValueError:
            await callback.answer(INVALID_SELECTION_TEXT, show_alert=True)
            return

        manipulation = await service.get_manipulation(manipulation_id)
        if manipulation is None or manipulation.section_id != section_id:
            await callback.answer(INVALID_SELECTION_TEXT, show_alert=True)
            return

        text = await service.build_manipulation_text(manipulation_id)
        await callback.message.edit_text(
            f"📌 {manipulation.title}\n\n{text}",
            reply_markup=kb.build_knowledge_manipulation_back_keyboard(
                section_id=section_id,
                page=page,
            ),
        )
        await callback.answer()

    return router
