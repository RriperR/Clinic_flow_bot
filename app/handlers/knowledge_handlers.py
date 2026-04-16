from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import app.keyboards as kb
from app.application.use_cases.knowledge_base import KnowledgeBaseService
from app.logger import setup_logger

logger = setup_logger("knowledge_base", "knowledge_base.log")

KNOWLEDGE_BASE_UNAVAILABLE_TEXT = (
    "База знаний недоступна: не настроена таблица KNOWLEDGE_TABLE."
)
SECTION_MENU_TEXT = "База знаний: выберите раздел:"
INVALID_SELECTION_TEXT = "Неверный выбор."


def create_knowledge_router(service: KnowledgeBaseService) -> Router:
    router = Router()

    async def render_section_menu(target: Message | CallbackQuery) -> None:
        if not service.is_configured():
            if isinstance(target, CallbackQuery):
                await target.answer(KNOWLEDGE_BASE_UNAVAILABLE_TEXT, show_alert=True)
            else:
                await target.answer(KNOWLEDGE_BASE_UNAVAILABLE_TEXT)
            return

        markup = kb.build_knowledge_section_keyboard(service.list_sections())
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(SECTION_MENU_TEXT, reply_markup=markup)
            await target.answer()
        else:
            await target.answer(SECTION_MENU_TEXT, reply_markup=markup)

    def get_sections() -> list[str]:
        return service.list_sections()

    def get_section_name(section_index: int) -> str | None:
        sections = get_sections()
        if 0 <= section_index < len(sections):
            return sections[section_index]
        return None

    async def render_manipulation_menu(
        callback: CallbackQuery,
        section_index: int,
        page: int = 0,
    ) -> None:
        section = get_section_name(section_index)
        if section is None:
            await callback.answer(INVALID_SELECTION_TEXT, show_alert=True)
            return

        manipulations = service.list_manipulations(section)
        if not manipulations:
            await callback.message.edit_text(
                f"В разделе '{section}' пока нет доступных манипуляций.",
                reply_markup=kb.build_knowledge_section_keyboard(get_sections()),
            )
            await callback.answer()
            return

        max_page = (len(manipulations) - 1) // kb.KNOWLEDGE_MANIPULATIONS_PER_PAGE
        page = max(0, min(page, max_page))

        await callback.message.edit_text(
            f"Раздел {section}: выберите манипуляцию:",
            reply_markup=kb.build_knowledge_manipulation_keyboard(
                section_index=section_index,
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
            section_index = int(callback.data.split(":", 1)[1])
        except ValueError:
            await callback.answer(INVALID_SELECTION_TEXT, show_alert=True)
            return

        await render_manipulation_menu(callback, section_index=section_index, page=0)

    @router.callback_query(F.data.startswith("kb_manipulations_page:"))
    async def change_manipulations_page(callback: CallbackQuery) -> None:
        try:
            _, section_index_text, page_text = callback.data.split(":", 2)
            section_index = int(section_index_text)
            page = int(page_text)
        except ValueError:
            await callback.answer(INVALID_SELECTION_TEXT, show_alert=True)
            return

        await render_manipulation_menu(
            callback,
            section_index=section_index,
            page=page,
        )

    @router.callback_query(F.data.startswith("kb_manipulation:"))
    async def select_manipulation(callback: CallbackQuery) -> None:
        try:
            _, section_index_text, manipulation_index_text, page_text = callback.data.split(
                ":", 3
            )
            section_index = int(section_index_text)
            manipulation_index = int(manipulation_index_text)
            page = int(page_text)
        except ValueError:
            await callback.answer(INVALID_SELECTION_TEXT, show_alert=True)
            return

        section = get_section_name(section_index)
        if section is None:
            await callback.answer(INVALID_SELECTION_TEXT, show_alert=True)
            return

        manipulations = service.list_manipulations(section)
        if manipulation_index < 0 or manipulation_index >= len(manipulations):
            await callback.answer(INVALID_SELECTION_TEXT, show_alert=True)
            return

        manipulation = manipulations[manipulation_index]
        text = service.build_manipulation_text(section, manipulation)
        await callback.message.edit_text(
            f"📌 {manipulation}\n\n{text}",
            reply_markup=kb.build_knowledge_manipulation_back_keyboard(
                section_index=section_index,
                page=page,
            ),
        )
        await callback.answer()

    return router
