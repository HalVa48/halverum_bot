from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.keyboards import get_main_menu_keyboard
from bot.scheduler import backup_all_servers
from database.models import User

router = Router()


@router.message(Command("backup"))
async def manual_backup(message: Message, db_user: User | None):
    """Manual backup command (admin only)"""
    if not config.is_admin(message.from_user.id):
        return

    await message.answer("🔄 Создаю бэкап всех серверов...")

    try:
        await backup_all_servers()
        await message.answer("✅ Бэкап успешно завершен!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при создании бэкапа: {e}")


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery, db_user: User | None):
    """Show main menu"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            "🏠 <b>Главное меню</b>\n\nВыберите действие:",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard(),
        )
