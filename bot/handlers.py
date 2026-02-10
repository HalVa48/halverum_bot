"""
Обработчики команд и сообщений для Telegram-бота
"""

from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards import get_main_keyboard, get_tariff_keyboard
from database.models import User
from payments.invoice_manager import create_invoice
from tariffs.tariff_plans import get_tariff_plans
from vpn.config_generator import ConfigGenerator, save_config_to_file


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    # Проверяем, есть ли пользователь в базе данных
    user = User.get_or_create(user_id=user_id)

    welcome_message = (
        f"Привет, {username}!\n\n"
        "Добро пожаловать в наш VPN-сервис на базе AmneziaVPN.\n"
        "У нас вы можете приобрести подписку по выгодным ценам."
    )

    await update.message.reply_text(welcome_message, reply_markup=get_main_keyboard())


async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображение доступных тарифов"""
    query = update.callback_query
    await query.answer()

    tariffs = get_tariff_plans()

    message = "Доступные тарифы:\n\n"
    for i, tariff in enumerate(tariffs, 1):
        message += (
            f"{i}. {tariff['name']}\n"
            f"Описание: {tariff['description']}\n"
            f"Цена: {tariff['price']} {tariff['currency']}\n"
            f"Период: {tariff['duration_days']} дней\n"
            f"Скорость: {tariff['speed_limit']}\n"
            f"Устройства: до {tariff['max_devices']} шт.\n\n"
        )

    await query.edit_message_text(text=message, reply_markup=get_tariff_keyboard())


async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка покупки подписки"""
    query = update.callback_query
    await query.answer()

    # В реальном приложении здесь будет выбор тарифа
    selected_tariff = get_tariff_plans()[0]  # Для примера берем первый тариф

    invoice = create_invoice(user_id=update.effective_user.id, tariff=selected_tariff)

    await query.edit_message_text(text=f"Создан счет для оплаты: {invoice['id']}")


async def get_vpn_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдача конфигурации VPN пользователю"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    # Проверяем, есть ли активная подписка у пользователя
    user = User.get_or_create(user_id=user_id)

    if not user.is_subscription_active():
        await query.edit_message_text(
            text="У вас нет активной подписки. Приобретите тариф для получения доступа к VPN."
        )
        return

    # Генерируем конфигурацию для пользователя
    config_generator = ConfigGenerator()
    selected_tariff = (
        get_tariff_plans()[user.tariff_id - 1]
        if user.tariff_id
        else get_tariff_plans()[0]
    )

    config_data = config_generator.generate_config(user_id, selected_tariff)

    # Сохраняем конфигурацию во временный файл
    config_file_path = save_config_to_file(config_data)

    # Отправляем файл пользователю
    with open(config_file_path, "rb") as config_file:
        # Сначала отправляем файл
        await query.message.reply_document(
            document=config_file,
            caption=f"Ваша конфигурация VPN для тарифа {selected_tariff['name']}",
        )
        # Затем редактируем предыдущее сообщение
        await query.edit_message_text(text="Ваша конфигурация VPN готова!")


async def my_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о текущей подписке пользователя"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    user = User.get_or_create(user_id=user_id)

    if user.is_subscription_active():
        remaining_time = user.subscription_expires_at - datetime.now()
        days_left = remaining_time.days

        message = (
            f"Ваша подписка активна!\n"
            f"Тариф: {user.tariff_id}\n"
            f"Осталось дней: {days_left}\n"
            f"Дата окончания: {user.subscription_expires_at.strftime('%d.%m.%Y')}"
        )
    else:
        message = "У вас нет активной подписки. Приобретите тариф для получения доступа к VPN."

    await query.edit_message_text(text=message)
