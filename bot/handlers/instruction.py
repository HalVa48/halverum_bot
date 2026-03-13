from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.keyboards import get_back_keyboard, get_device_select_keyboard
from database.models import User

router = Router()

INSTRUCTIONS = {
    "ios": (
        "🍎 <b>Настройка VPN на iOS</b>\n\n"
        "1. Установите приложение <b>AmneziaVPN</b> или <b>DefaultVPN</b> из App Store:\n"
        "   • AmneziaVPN: https://apps.apple.com/us/app/amneziavpn/id1600529900\n"
        "   • DefaultVPN: https://apps.apple.com/us/app/defaultvpn/id6744725017\n\n"
        "2. Получите конфиг в боте (кнопка 'Мои конфиги')\n\n"
        "3. Откройте приложение и импортируйте конфиг:\n"
        "   • Через QR-код (сканировать из бота)\n"
        "   • Или через файл (.conf)\n\n"
        "4. Подключитесь к серверу"
    ),
    "android": (
        "🤖 <b>Настройка VPN на Android</b>\n\n"
        "1. Установите приложение <b>AmneziaVPN</b> из Google Play:\n"
        "   https://play.google.com/store/apps/details?id=org.amnezia.vpn\n\n"
        "2. Получите конфиг в боте (кнопка 'Мои конфиги')\n\n"
        "3. Откройте AmneziaVPN и добавьте туннель:\n"
        "   • '+' → 'Сканировать QR-код' (из бота)\n"
        "   • Или 'Импортировать из файла' (.conf)\n\n"
        "4. Нажмите на туннель для подключения"
    ),
    "windows": (
        "🪟 <b>Настройка VPN на Windows</b>\n\n"
        "1. Скачайте и установите клиент AmneziaVPN:\n"
        "   https://amnezia.org/ru/downloads\n\n"
        "2. Получите конфиг в боте (кнопка 'Мои конфиги')\n\n"
        "3. Откройте AmneziaVPN и нажмите '+':\n"
        "   • '+' → 'Файл с настройками подключения'\n"
        "   • Выберите скачанный .conf файл\n\n"
        "4. Нажмите 'Подключить'"
    ),
}


@router.callback_query(F.data == "instruction")
async def show_instruction(callback: CallbackQuery, db_user: User | None):
    """Show instruction menu"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    await callback.message.edit_text(
        "📖 <b>Инструкция по настройке</b>\n\nВыберите ваше устройство:",
        parse_mode="HTML",
        reply_markup=get_device_select_keyboard(),
    )


@router.callback_query(F.data == "device_ios")
async def show_ios_instruction(callback: CallbackQuery, db_user: User | None):
    """Show iOS instruction"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    await callback.message.edit_text(
        INSTRUCTIONS["ios"],
        parse_mode="HTML",
        reply_markup=get_back_keyboard("instruction"),
    )


@router.callback_query(F.data == "device_android")
async def show_android_instruction(callback: CallbackQuery, db_user: User | None):
    """Show Android instruction"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    await callback.message.edit_text(
        INSTRUCTIONS["android"],
        parse_mode="HTML",
        reply_markup=get_back_keyboard("instruction"),
    )


@router.callback_query(F.data == "device_windows")
async def show_windows_instruction(callback: CallbackQuery, db_user: User | None):
    """Show Windows instruction"""
    if not db_user or not db_user.is_authorized:
        await callback.answer("Сначала введите пароль для доступа", show_alert=True)
        return

    await callback.message.edit_text(
        INSTRUCTIONS["windows"],
        parse_mode="HTML",
        reply_markup=get_back_keyboard("instruction"),
    )
