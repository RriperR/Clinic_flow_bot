from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.application.use_cases.admin_access import AdminAccessService
from app.application.use_cases.instrument_admin import InstrumentAdminService
from app.domain.entities import Cabinet, Instrument, Worker
from app.logger import setup_logger
from app.text_utils import normalize_text


logger = setup_logger("admin_panel", "admin_panel.log")
PER_PAGE = 10


class InstrumentAdminState(StatesGroup):
    waiting_cabinet_name = State()
    waiting_cabinet_rename = State()
    waiting_instrument_name = State()
    waiting_instrument_rename = State()
    waiting_admin_chat_id = State()


def create_admin_panel_router(
    admin_service: InstrumentAdminService,
    admin_access: AdminAccessService,
) -> Router:
    router = Router()

    def build_admin_menu():
        builder = InlineKeyboardBuilder()
        builder.button(text="🗓 Смены", callback_data="admin_shifts")
        builder.button(text="🏢 Кабинеты", callback_data="admin_cabinets")
        builder.button(text="🧰 Инструменты", callback_data="admin_instruments")
        builder.button(text="👮 Админы", callback_data="admin_users")
        builder.adjust(1)
        return builder.as_markup()

    def build_cabinet_list_keyboard(cabinets: list[Cabinet], view: str):
        builder = InlineKeyboardBuilder()
        for cabinet in cabinets:
            label = cabinet.name
            if not cabinet.is_active:
                label = f"{label} (🗄️ архив)"
            builder.button(text=label[:64], callback_data=f"cabinet_manage:{cabinet.id}")

        toggle_view = "archived" if view == "active" else "active"
        toggle_label = "🗂️ Показать архив" if view == "active" else "✅ Показать активные"
        builder.button(text=toggle_label, callback_data=f"cabinet_list:{toggle_view}")
        builder.button(text="➕ Добавить кабинет", callback_data="cabinet_add")
        builder.button(text="⬅️ Назад", callback_data="admin_back")
        builder.adjust(1)
        return builder.as_markup()

    def build_cabinet_manage_keyboard(cabinet: Cabinet):
        builder = InlineKeyboardBuilder()
        builder.button(text="✏️ Переименовать", callback_data=f"cabinet_rename:{cabinet.id}")
        if cabinet.is_active:
            builder.button(text="🗄️ Архивировать", callback_data=f"cabinet_archive:{cabinet.id}")
        else:
            builder.button(text="♻️ Вернуть из архива", callback_data=f"cabinet_restore:{cabinet.id}")
        builder.button(text="🗑️ Удалить", callback_data=f"cabinet_delete:{cabinet.id}")
        builder.button(text="⬅️ К списку", callback_data="cabinet_list:active")
        builder.adjust(1)
        return builder.as_markup()

    def build_cabinet_delete_keyboard(cabinet_id: int):
        builder = InlineKeyboardBuilder()
        builder.button(
            text="🗑️ Подтвердить удаление",
            callback_data=f"cabinet_delete_confirm:{cabinet_id}",
        )
        builder.button(text="↩️ Отмена", callback_data=f"cabinet_manage:{cabinet_id}")
        builder.adjust(1)
        return builder.as_markup()

    def build_cabinet_select_keyboard(cabinets: list[Cabinet], view: str):
        builder = InlineKeyboardBuilder()
        for cabinet in cabinets:
            label = cabinet.name
            if not cabinet.is_active:
                label = f"{label} (🗄️ архив)"
            builder.button(
                text=label[:64], callback_data=f"instrument_list:{cabinet.id}:{view}"
            )
        toggle_view = "archived" if view == "active" else "active"
        toggle_label = (
            "🗂️ Показать архивные" if view == "active" else "✅ Показать активные"
        )
        builder.button(text=toggle_label, callback_data=f"instrument_cabinets:{toggle_view}")
        builder.button(text="⬅️ Назад", callback_data="admin_back")
        builder.adjust(1)
        return builder.as_markup()

    def build_instrument_list_keyboard(
        instruments: list[Instrument],
        cabinet_id: int,
        view: str,
    ):
        builder = InlineKeyboardBuilder()
        for instrument in instruments:
            label = instrument.name
            if not instrument.is_active:
                label = f"{label} (🗄️ архив)"
            builder.button(
                text=label[:64],
                callback_data=f"instrument_manage:{instrument.id}:{cabinet_id}:{view}",
            )
        toggle_view = "archived" if view == "active" else "active"
        toggle_label = (
            "🗂️ Показать архивные" if view == "active" else "✅ Показать активные"
        )
        builder.button(
            text=toggle_label, callback_data=f"instrument_list:{cabinet_id}:{toggle_view}"
        )
        builder.button(text="➕ Добавить инструмент", callback_data=f"instrument_add:{cabinet_id}")
        builder.button(text="🏢 К кабинетам", callback_data="admin_instruments")
        builder.adjust(1)
        return builder.as_markup()

    def build_instrument_manage_keyboard(
        instrument: Instrument, cabinet_id: int, view: str
    ):
        builder = InlineKeyboardBuilder()
        builder.button(
            text="✏️ Переименовать",
            callback_data=f"instrument_rename:{instrument.id}:{cabinet_id}:{view}",
        )
        if instrument.is_active:
            builder.button(
                text="🗄️ Архивировать",
                callback_data=f"instrument_archive:{instrument.id}:{cabinet_id}:{view}",
            )
        else:
            builder.button(
                text="♻️ Вернуть из архива",
                callback_data=f"instrument_restore:{instrument.id}:{cabinet_id}:{view}",
            )
        builder.button(
            text="🗑️ Удалить",
            callback_data=f"instrument_delete:{instrument.id}:{cabinet_id}:{view}",
        )
        builder.button(
            text="⬅️ К списку",
            callback_data=f"instrument_list:{cabinet_id}:{view}",
        )
        builder.adjust(1)
        return builder.as_markup()

    def build_instrument_delete_keyboard(instrument_id: int, cabinet_id: int, view: str):
        builder = InlineKeyboardBuilder()
        builder.button(
            text="🗑️ Подтвердить удаление",
            callback_data=f"instrument_delete_confirm:{instrument_id}:{cabinet_id}:{view}",
        )
        builder.button(
            text="↩️ Отмена",
            callback_data=f"instrument_manage:{instrument_id}:{cabinet_id}:{view}",
        )
        builder.adjust(1)
        return builder.as_markup()

    def build_admins_menu():
        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Добавить админа", callback_data="admin_user_add")
        builder.button(text="➖ Удалить админа", callback_data="admin_user_remove_menu")
        builder.button(text="⬅️ Назад", callback_data="admin_back")
        builder.adjust(1)
        return builder.as_markup()

    def build_admin_remove_keyboard(admins: list[tuple[str, str]]):
        builder = InlineKeyboardBuilder()
        for chat_id, label in admins:
            builder.button(text=label[:64], callback_data=f"admin_user_remove:{chat_id}")
        builder.button(text="⬅️ Назад", callback_data="admin_users")
        builder.adjust(1)
        return builder.as_markup()

    def build_admin_add_menu():
        builder = InlineKeyboardBuilder()
        builder.button(text="👤 Выбрать сотрудника", callback_data="admin_user_add_choose")
        builder.button(text="✍️ Ввести chat id", callback_data="admin_user_add_manual")
        builder.button(text="⬅️ Назад", callback_data="admin_users")
        builder.adjust(1)
        return builder.as_markup()

    def build_admin_add_workers_keyboard(workers: list[Worker], page: int):
        total = len(workers)
        start = page * PER_PAGE
        end = min(start + PER_PAGE, total)

        builder = InlineKeyboardBuilder()
        for worker in workers[start:end]:
            label = f"{worker.full_name} ({worker.chat_id})"
            builder.button(
                text=label[:64],
                callback_data=f"admin_user_add_select:{worker.chat_id}",
            )

        nav = InlineKeyboardBuilder()
        if start > 0:
            nav.button(text="Назад", callback_data=f"admin_user_add_page:{page - 1}")
        if end < total:
            nav.button(text="Вперёд", callback_data=f"admin_user_add_page:{page + 1}")
        if nav.buttons:
            builder.row(*nav.buttons)

        builder.button(text="⬅️ Назад", callback_data="admin_user_add")
        builder.adjust(1)
        return builder.as_markup()


    async def require_admin(callback: CallbackQuery | Message) -> bool:
        user_id = callback.from_user.id
        if not await admin_access.is_admin(user_id):
            if isinstance(callback, CallbackQuery):
                await callback.answer("⛔ Нет доступа", show_alert=True)
            else:
                await callback.answer("⛔ Нет доступа")
            return False
        return True

    async def render_cabinet_list(callback: CallbackQuery, view: str):
        cabinets = await admin_service.list_cabinets(include_archived=True)
        if view == "archived":
            cabinets = [c for c in cabinets if not c.is_active]
        else:
            cabinets = [c for c in cabinets if c.is_active]
        text = "🏢 Кабинеты (архив)" if view == "archived" else "🏢 Кабинеты"
        await callback.message.edit_text(
            text,
            reply_markup=build_cabinet_list_keyboard(cabinets, view=view),
        )

    async def render_instrument_cabinets(callback: CallbackQuery, view: str):
        cabinets = await admin_service.list_cabinets(include_archived=True)
        if view == "archived":
            cabinets = [c for c in cabinets if not c.is_active]
        else:
            cabinets = [c for c in cabinets if c.is_active]
        await callback.message.edit_text(
            "🏢 Выберите кабинет:",
            reply_markup=build_cabinet_select_keyboard(cabinets, view=view),
        )

    async def render_instrument_list(callback: CallbackQuery, cabinet_id: int, view: str):
        cabinet = await admin_service.get_cabinet(cabinet_id)
        if not cabinet:
            await callback.answer("⛔ Кабинет не найден", show_alert=True)
            return
        instruments = await admin_service.list_instruments(
            cabinet_id, include_archived=True
        )
        if view == "archived":
            instruments = [item for item in instruments if not item.is_active]
        else:
            instruments = [item for item in instruments if item.is_active]
        header = f"🧰 Инструменты в кабинете: {cabinet.name}"
        if view == "archived":
            header += " (🗄️ архив)"
        await callback.message.edit_text(
            header,
            reply_markup=build_instrument_list_keyboard(
                instruments, cabinet_id=cabinet_id, view=view
            ),
        )

    async def format_admin_entry(chat_id: str) -> str:
        name = await admin_access.resolve_worker_name(chat_id)
        if name:
            return f"{chat_id} - {name}"
        return chat_id

    async def render_admins(target: CallbackQuery | Message):
        super_admins = admin_access.list_super_admins()
        db_admins = await admin_access.list_admins()
        super_set = set(super_admins)
        db_admins = [admin for admin in db_admins if admin.chat_id not in super_set]
        lines = ["👮 Админы:"]
        if super_admins:
            lines.append("⭐ Супер-админы (ENV):")
            for chat_id in super_admins:
                lines.append(f"- {await format_admin_entry(chat_id)}")
        else:
            lines.append("⭐ Супер-админы (ENV): нет")
        if db_admins:
            lines.append("👤 Админы (БД):")
            for admin in db_admins:
                lines.append(f"- {await format_admin_entry(admin.chat_id)}")
        else:
            lines.append("👤 Админы (БД): нет")
        text = "\n".join(lines)
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=build_admins_menu())
        else:
            await target.answer(text, reply_markup=build_admins_menu())

    async def render_admin_add_workers(callback: CallbackQuery, page: int):
        workers = await admin_access.list_registered_workers()
        admin_ids = {admin.chat_id for admin in await admin_access.list_admins()}
        admin_ids.update(admin_access.list_super_admins())
        available = [worker for worker in workers if worker.chat_id not in admin_ids]
        available.sort(key=lambda w: normalize_text(w.full_name))
        if not available:
            await callback.message.edit_text(
                "ℹ️ Нет доступных сотрудников для добавления.",
                reply_markup=build_admin_add_menu(),
            )
            return
        max_page = (len(available) - 1) // PER_PAGE
        page = max(0, min(page, max_page))
        await callback.message.edit_text(
            "👤 Выберите сотрудника для добавления в админы:",
            reply_markup=build_admin_add_workers_keyboard(available, page),
        )


    @router.message(Command("admin"))
    async def admin_menu(message: Message, state: FSMContext):
        if not await admin_access.is_admin(message.from_user.id):
            chat_id = message.from_user.id
            await message.answer(f"⚠️ Нет доступа. Ваш chat id: {chat_id}")
            return
        await state.clear()
        await message.answer("🛠️ Админка:", reply_markup=build_admin_menu())

    @router.callback_query(F.data == "admin_back")
    async def admin_back(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        await state.clear()
        await callback.message.edit_text(
            "🛠️ Админка:", reply_markup=build_admin_menu()
        )
        await callback.answer()

    @router.callback_query(F.data == "admin_users")
    async def admin_users(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        await state.clear()
        await render_admins(callback)
        await callback.answer()

    @router.callback_query(F.data == "admin_user_add")
    async def admin_user_add(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        await state.clear()
        await callback.message.edit_text(
            "👮 Как добавить админа?", reply_markup=build_admin_add_menu()
        )
        await callback.answer()

    @router.callback_query(F.data == "admin_user_add_manual")
    async def admin_user_add_manual(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        await state.clear()
        await state.set_state(InstrumentAdminState.waiting_admin_chat_id)
        await callback.message.edit_text("👮 Отправьте chat id нового админа:")
        await callback.answer()

    @router.callback_query(F.data == "admin_user_add_choose")
    async def admin_user_add_choose(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        await render_admin_add_workers(callback, page=0)
        await callback.answer()

    @router.callback_query(F.data.startswith("admin_user_add_page:"))
    async def admin_user_add_page(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, page_str = callback.data.split(":")
        await render_admin_add_workers(callback, page=int(page_str))
        await callback.answer()

    @router.callback_query(F.data.startswith("admin_user_add_select:"))
    async def admin_user_add_select(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, chat_id = callback.data.split(":", 1)
        if admin_access.is_super_admin(chat_id):
            await callback.answer("⭐ Уже супер-админ", show_alert=True)
            return
        if await admin_access.is_admin(chat_id):
            await callback.answer("ℹ️ Админ уже добавлен", show_alert=True)
            return
        success = await admin_access.add_admin(chat_id)
        if success:
            await callback.answer("✅ Админ добавлен")
        else:
            await callback.answer("ℹ️ Админ уже добавлен", show_alert=True)
        await render_admins(callback)

    @router.message(StateFilter(InstrumentAdminState.waiting_admin_chat_id))
    async def admin_user_add_chat_id(message: Message, state: FSMContext):
        if not await require_admin(message):
            return
        chat_id = message.text.strip()
        if not chat_id.isdigit():
            await message.answer("⛔ Нужен числовой chat id. Попробуйте ещё раз.")
            return
        if admin_access.is_super_admin(chat_id):
            await state.clear()
            await message.answer("⭐ Этот chat id уже указан в ADMIN_CHAT_IDS.")
            await render_admins(message)
            return
        if await admin_access.is_admin(chat_id):
            await state.clear()
            await message.answer("ℹ️ Админ уже добавлен.")
            await render_admins(message)
            return
        success = await admin_access.add_admin(chat_id)
        await state.clear()
        if success:
            await message.answer("✅ Админ добавлен.")
        else:
            await message.answer("ℹ️ Админ уже добавлен.")
        await render_admins(message)

    @router.callback_query(F.data == "admin_user_remove_menu")
    async def admin_user_remove_menu(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        admins = await admin_access.list_admins()
        admins = [admin for admin in admins if not admin_access.is_super_admin(admin.chat_id)]
        if not admins:
            await callback.answer("ℹ️ В БД нет админов", show_alert=True)
            await render_admins(callback)
            return
        labels: list[tuple[str, str]] = []
        for admin in admins:
            label = await format_admin_entry(admin.chat_id)
            labels.append((admin.chat_id, label))
        await callback.message.edit_text(
            "🗑️ Выберите админа для удаления:",
            reply_markup=build_admin_remove_keyboard(labels),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin_user_remove:"))
    async def admin_user_remove(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, chat_id = callback.data.split(":", 1)
        if admin_access.is_super_admin(chat_id):
            await callback.answer("⛔ Нельзя удалить супер-админа", show_alert=True)
            return
        if chat_id == str(callback.from_user.id) and not admin_access.is_super_admin(
            callback.from_user.id
        ):
            await callback.answer("⛔ Нельзя удалить себя", show_alert=True)
            return
        success = await admin_access.remove_admin(chat_id)
        if success:
            await callback.answer("🗑️ Админ удалён")
        else:
            await callback.answer("⛔ Админ не найден", show_alert=True)
        await render_admins(callback)

    @router.callback_query(F.data == "admin_cabinets")
    async def admin_cabinets(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        await state.clear()
        await render_cabinet_list(callback, view="active")
        await callback.answer()

    @router.callback_query(F.data.startswith("cabinet_list:"))
    async def cabinet_list(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, view = callback.data.split(":", 1)
        await render_cabinet_list(callback, view=view)
        await callback.answer()

    @router.callback_query(F.data == "cabinet_add")
    async def cabinet_add(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        await state.clear()
        await state.set_state(InstrumentAdminState.waiting_cabinet_name)
        await callback.message.edit_text("📝 Введите название нового кабинета:")
        await callback.answer()

    @router.message(StateFilter(InstrumentAdminState.waiting_cabinet_name))
    async def cabinet_add_name(message: Message, state: FSMContext):
        if not await require_admin(message):
            return
        name = message.text.strip()
        if not name:
            await message.answer("⚠️ Название не может быть пустым. Попробуйте ещё раз.")
            return
        await admin_service.add_cabinet(name)
        await state.clear()
        await message.answer("✅ Кабинет добавлен.")
        await message.answer("🏢 Кабинеты:", reply_markup=build_admin_menu())

    @router.callback_query(F.data.startswith("cabinet_manage:"))
    async def cabinet_manage(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        cabinet = await admin_service.get_cabinet(cabinet_id)
        if not cabinet:
            await callback.answer("⛔ Кабинет не найден", show_alert=True)
            return
        status = "✅ активен" if cabinet.is_active else "🗄️ архив"
        await callback.message.edit_text(
            f"🏢 Кабинет: {cabinet.name}\nСтатус: {status}",
            reply_markup=build_cabinet_manage_keyboard(cabinet),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("cabinet_rename:"))
    async def cabinet_rename(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        await state.set_state(InstrumentAdminState.waiting_cabinet_rename)
        await state.update_data(cabinet_id=cabinet_id)
        await callback.message.edit_text("✏️ Введите новое название кабинета:")
        await callback.answer()

    @router.message(StateFilter(InstrumentAdminState.waiting_cabinet_rename))
    async def cabinet_rename_name(message: Message, state: FSMContext):
        if not await require_admin(message):
            return
        name = message.text.strip()
        if not name:
            await message.answer("⚠️ Название не может быть пустым. Попробуйте ещё раз.")
            return
        data = await state.get_data()
        cabinet_id = data.get("cabinet_id")
        if not cabinet_id:
            await state.clear()
            await message.answer("⚠️ Сессия сброшена. Откройте /admin заново.")
            return
        await admin_service.rename_cabinet(cabinet_id, name)
        await state.clear()
        await message.answer("✅ Название обновлено.")

    @router.callback_query(F.data.startswith("cabinet_archive:"))
    async def cabinet_archive(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        await admin_service.set_cabinet_active(cabinet_id, False)
        await callback.answer("🗄️ Кабинет архивирован")
        await cabinet_manage(callback)

    @router.callback_query(F.data.startswith("cabinet_restore:"))
    async def cabinet_restore(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        await admin_service.set_cabinet_active(cabinet_id, True)
        await callback.answer("♻️ Кабинет восстановлен")
        await cabinet_manage(callback)

    @router.callback_query(F.data.startswith("cabinet_delete:"))
    async def cabinet_delete(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        cabinet = await admin_service.get_cabinet(cabinet_id)
        if not cabinet:
            await callback.answer("⛔ Кабинет не найден", show_alert=True)
            return
        await callback.message.edit_text(
            f"🗑️ Удалить кабинет «{cabinet.name}»?",
            reply_markup=build_cabinet_delete_keyboard(cabinet_id),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("cabinet_delete_confirm:"))
    async def cabinet_delete_confirm(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        success = await admin_service.delete_cabinet(cabinet_id)
        if success:
            await callback.answer("🗑️ Кабинет удалён")
            await render_cabinet_list(callback, view="active")
        else:
            await callback.answer(
                "⛔ Нельзя удалить кабинет с инструментами", show_alert=True
            )

    @router.callback_query(F.data == "admin_instruments")
    async def admin_instruments(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        await state.clear()
        await render_instrument_cabinets(callback, view="active")
        await callback.answer()

    @router.callback_query(F.data.startswith("instrument_cabinets:"))
    async def instrument_cabinets(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, view = callback.data.split(":", 1)
        await render_instrument_cabinets(callback, view=view)
        await callback.answer()

    @router.callback_query(F.data.startswith("instrument_list:"))
    async def instrument_list(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, cabinet_id, view = callback.data.split(":")
        await render_instrument_list(callback, cabinet_id=int(cabinet_id), view=view)
        await callback.answer()

    @router.callback_query(F.data.startswith("instrument_manage:"))
    async def instrument_manage(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, instrument_id, cabinet_id, view = callback.data.split(":")
        instrument = await admin_service.get_instrument(int(instrument_id))
        if not instrument:
            await callback.answer("⛔ Инструмент не найден", show_alert=True)
            return
        status = "✅ активен" if instrument.is_active else "🗄️ архив"
        await callback.message.edit_text(
            f"🧰 Инструмент: {instrument.name}\nСтатус: {status}",
            reply_markup=build_instrument_manage_keyboard(
                instrument, cabinet_id=int(cabinet_id), view=view
            ),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("instrument_add:"))
    async def instrument_add(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        cabinet_id = int(callback.data.split(":", 1)[1])
        await state.set_state(InstrumentAdminState.waiting_instrument_name)
        await state.update_data(cabinet_id=cabinet_id)
        await callback.message.edit_text("📝 Введите название нового инструмента:")
        await callback.answer()

    @router.message(StateFilter(InstrumentAdminState.waiting_instrument_name))
    async def instrument_add_name(message: Message, state: FSMContext):
        if not await require_admin(message):
            return
        name = message.text.strip()
        if not name:
            await message.answer("⚠️ Название не может быть пустым. Попробуйте ещё раз.")
            return
        data = await state.get_data()
        cabinet_id = data.get("cabinet_id")
        if not cabinet_id:
            await state.clear()
            await message.answer("⚠️ Сессия сброшена. Откройте /admin заново.")
            return
        await admin_service.add_instrument(cabinet_id, name)
        await state.clear()
        instruments = await admin_service.list_instruments(
            cabinet_id, include_archived=True
        )
        instruments = [item for item in instruments if item.is_active]
        await message.answer("✅ Инструмент добавлен.")
        await message.answer(
            "🧰 Инструменты:",
            reply_markup=build_instrument_list_keyboard(
                instruments, cabinet_id=cabinet_id, view="active"
            ),
        )

    @router.callback_query(F.data.startswith("instrument_rename:"))
    async def instrument_rename(callback: CallbackQuery, state: FSMContext):
        if not await require_admin(callback):
            return
        _, instrument_id, cabinet_id, view = callback.data.split(":")
        await state.set_state(InstrumentAdminState.waiting_instrument_rename)
        await state.update_data(
            instrument_id=int(instrument_id),
            cabinet_id=int(cabinet_id),
            view=view,
        )
        await callback.message.edit_text("✏️ Введите новое название инструмента:")
        await callback.answer()

    @router.message(StateFilter(InstrumentAdminState.waiting_instrument_rename))
    async def instrument_rename_name(message: Message, state: FSMContext):
        if not await require_admin(message):
            return
        name = message.text.strip()
        if not name:
            await message.answer("⚠️ Название не может быть пустым. Попробуйте ещё раз.")
            return
        data = await state.get_data()
        instrument_id = data.get("instrument_id")
        cabinet_id = data.get("cabinet_id")
        view = data.get("view", "active")
        if not instrument_id or not cabinet_id:
            await state.clear()
            await message.answer("⚠️ Сессия сброшена. Откройте /admin заново.")
            return
        await admin_service.rename_instrument(instrument_id, name)
        await state.clear()
        await message.answer("✅ Название обновлено.")
        instruments = await admin_service.list_instruments(
            cabinet_id, include_archived=True
        )
        if view == "archived":
            instruments = [item for item in instruments if not item.is_active]
        else:
            instruments = [item for item in instruments if item.is_active]
        await message.answer(
            "🧰 Инструменты:",
            reply_markup=build_instrument_list_keyboard(
                instruments, cabinet_id=cabinet_id, view=view
            ),
        )

    @router.callback_query(F.data.startswith("instrument_archive:"))
    async def instrument_archive(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, instrument_id, cabinet_id, view = callback.data.split(":")
        await admin_service.set_instrument_active(int(instrument_id), False)
        await callback.answer("🗄️ Инструмент архивирован")
        await render_instrument_list(callback, int(cabinet_id), view=view)

    @router.callback_query(F.data.startswith("instrument_restore:"))
    async def instrument_restore(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, instrument_id, cabinet_id, view = callback.data.split(":")
        await admin_service.set_instrument_active(int(instrument_id), True)
        await callback.answer("♻️ Инструмент восстановлен")
        await render_instrument_list(callback, int(cabinet_id), view=view)

    @router.callback_query(F.data.startswith("instrument_delete:"))
    async def instrument_delete(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, instrument_id, cabinet_id, view = callback.data.split(":")
        instrument = await admin_service.get_instrument(int(instrument_id))
        if not instrument:
            await callback.answer("⛔ Инструмент не найден", show_alert=True)
            return
        await callback.message.edit_text(
            f"🗑️ Удалить инструмент «{instrument.name}»?",
            reply_markup=build_instrument_delete_keyboard(
                int(instrument_id), int(cabinet_id), view
            ),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("instrument_delete_confirm:"))
    async def instrument_delete_confirm(callback: CallbackQuery):
        if not await require_admin(callback):
            return
        _, instrument_id, cabinet_id, view = callback.data.split(":")
        await admin_service.delete_instrument(int(instrument_id))
        await callback.answer("🗑️ Инструмент удалён")
        await render_instrument_list(callback, int(cabinet_id), view=view)

    return router
