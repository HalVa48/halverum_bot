"""
Клавиатуры для взаимодействия с пользователем
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_tariff_keyboard():
    """Клавиатура с выбором тарифов"""
    keyboard = [
        [
            InlineKeyboardButton("Тариф 1", callback_data="tariff_1"),
            InlineKeyboardButton("Тариф 2", callback_data="tariff_2"),
        ],
        [InlineKeyboardButton("Тариф 3", callback_data="tariff_3")],
        [InlineKeyboardButton("Назад", callback_data="back_to_main")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_main_keyboard():
    """Основная клавиатура с главными командами"""
    keyboard = [
        [
            InlineKeyboardButton("Посмотреть тарифы", callback_data="show_tariffs"),
            InlineKeyboardButton("Купить подписку", callback_data="buy_subscription"),
        ],
        [
            InlineKeyboardButton("Моя подписка", callback_data="my_subscription"),
            InlineKeyboardButton("Получить VPN-конфиг", callback_data="get_vpn_config"),
        ],
        [InlineKeyboardButton("Поддержка", callback_data="support")],
    ]

    return InlineKeyboardMarkup(keyboard)
