from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.application.admin.sync_use_case import AdminSyncService


def create_admin_router(admin: AdminSyncService) -> Router:
    router = Router()

    @router.message(Command("upd"))
    async def update_db(message: Message):
        msg = await message.answer("Обновляем все данные из таблиц...")
        await admin.sync_all()
        await msg.edit_text("Данные из Google Sheets обновлены")

    @router.message(Command("upd_workers"))
    async def update_workers(message: Message):
        msg = await message.answer("Обновляем список сотрудников...")
        created = await admin.sync_workers()
        await msg.edit_text(f"Сотрудники обновлены. Добавлено новых: {created}")

    @router.message(Command("upd_pairs"))
    async def update_pairs(message: Message):
        msg = await message.answer("Обновляем пары для опросов...")
        created = await admin.sync_pairs()
        await msg.edit_text(f"Пары на сегодня обновлены. Добавлено: {created}")

    @router.message(Command("upd_surveys"))
    async def update_surveys(message: Message):
        msg = await message.answer("Обновляем опросники...")
        created = await admin.sync_surveys()
        await msg.edit_text(f"Опросники перезагружены. Добавлено: {created}")

    @router.message(Command("upd_shifts"))
    async def update_shifts(message: Message):
        msg = await message.answer("Обновляем смены...")
        count = await admin.sync_shifts()
        await msg.edit_text(f"Смены обновлены. Загружено строк: {count}")

    @router.message(Command("upd_knowledge"))
    async def update_knowledge(message: Message):
        msg = await message.answer("Обновляем базу знаний...")
        count = await admin.sync_knowledge_base()
        await msg.edit_text(f"База знаний обновлена. Загружено манипуляций: {count}")

    @router.message(Command("export"))
    async def export_data(message: Message):
        msg = await message.answer("Готовим выгрузку ответов...")
        await admin.export_answers()
        await msg.edit_text("Ответы выгружены в Google Sheets")

    @router.message(Command("exp_shifts"))
    async def export_shifts(message: Message):
        msg = await message.answer("Готовим выгрузку смен...")
        today_str = datetime.now().strftime("%d.%m.%Y")
        await admin.export_shifts(today_str)
        await msg.edit_text("Отчёт по сменам обновлён")

    return router
