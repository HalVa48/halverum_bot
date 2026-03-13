from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📁 Мои конфиги", callback_data="my_configs"))
    builder.row(
        InlineKeyboardButton(text="➕ Создать конфиг", callback_data="create_config")
    )
    builder.row(InlineKeyboardButton(text="📖 Инструкция", callback_data="instruction"))
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="stats"))
    return builder.as_markup()


def get_back_keyboard(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """Back button keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data))
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def get_configs_keyboard(configs: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    """Keyboard with list of user configs"""
    builder = InlineKeyboardBuilder()
    for cfg in configs:
        builder.row(
            InlineKeyboardButton(
                text=f"📁 {cfg['name']}", callback_data=f"config_{cfg['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    return builder.as_markup()


def get_config_actions_keyboard(
    config_id: int, is_revoked: bool = False
) -> InlineKeyboardMarkup:
    """Keyboard with actions for a specific config"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📋 Получить конфиг", callback_data=f"copy_config_{config_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="📱 QR-код", callback_data=f"qr_config_{config_id}")
    )
    if is_revoked:
        builder.row(
            InlineKeyboardButton(
                text="✅ Восстановить", callback_data=f"restore_config_{config_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="⏸️ Отключить", callback_data=f"revoke_config_{config_id}"
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="🗑️ Удалить", callback_data=f"delete_config_{config_id}"
        )
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="my_configs"))
    return builder.as_markup()


def get_servers_keyboard(servers: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    """Keyboard with server selection"""
    builder = InlineKeyboardBuilder()
    for server in servers:
        builder.row(
            InlineKeyboardButton(
                text=f"🖥️ {server['name']}", callback_data=f"server_{server['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def get_confirm_keyboard(
    confirm_data: str, cancel_data: str = "cancel"
) -> InlineKeyboardMarkup:
    """Confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_data),
        InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_data),
    )
    return builder.as_markup()


def get_device_select_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for device selection"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🍎 Apple (iOS)", callback_data="device_ios"))
    builder.row(InlineKeyboardButton(text="🤖 Android", callback_data="device_android"))
    builder.row(InlineKeyboardButton(text="🪟 Windows", callback_data="device_windows"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    return builder.as_markup()
