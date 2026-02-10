"""
Вспомогательные функции для бота
"""

import os
from datetime import datetime, timedelta


def load_config():
    """Загрузка конфигурации из файла"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.py")
    config = {}

    with open(config_path, "r", encoding="utf-8") as f:
        exec(f.read(), {}, config)

    return config


def format_date(date_obj):
    """Форматирование даты для отображения"""
    return date_obj.strftime("%d.%m.%Y")


def validate_email(email):
    """Проверка корректности email"""
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def generate_unique_id():
    """Генерация уникального ID"""
    import uuid

    return str(uuid.uuid4())


def check_subscription_status(user_id):
    """Проверка статуса подписки пользователя"""
    # В реальном приложении здесь будет обращение к базе данных
    # Возвращаем заглушку
    return {
        "active": True,
        "expires_at": datetime.now() + timedelta(days=30),
        "tariff_name": "Premium",
    }
