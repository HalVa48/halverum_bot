"""
Модели базы данных для VPN-бота
"""

from datetime import datetime, timedelta

from peewee import *

# Подключение к базе данных (в реальном приложении URL будет из конфига)
db = SqliteDatabase("vpn_bot.db")


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    """Модель пользователя"""

    user_id = BigIntegerField(primary_key=True)
    username = CharField(null=True)
    first_name = CharField(null=True)
    last_name = CharField(null=True)
    email = CharField(null=True)
    created_at = DateTimeField(default=datetime.now)
    subscription_expires_at = DateTimeField(null=True)
    is_active = BooleanField(default=True)
    tariff_id = IntegerField(null=True)

    @classmethod
    def get_or_create(cls, user_id):
        """Получение или создание пользователя"""
        try:
            # Попробуем получить существующего пользователя
            user = cls.get(cls.user_id == user_id)
            return user
        except DoesNotExist:
            # Если пользователя нет, создадим нового
            user = cls.create(user_id=user_id, created_at=datetime.now())
            return user

    def activate_subscription(self, tariff_id, duration_days=30):
        """Активация подписки для пользователя"""
        from tariffs.tariff_plans import get_tariff_by_id

        tariff = get_tariff_by_id(tariff_id)
        if tariff:
            duration_days = tariff.get("duration_days", 30)

        self.subscription_expires_at = datetime.now() + timedelta(days=duration_days)
        self.is_active = True
        self.tariff_id = tariff_id
        self.save()

    def deactivate_subscription(self):
        """Деактивация подписки для пользователя"""
        self.subscription_expires_at = None
        self.is_active = False
        self.tariff_id = None
        self.save()

    def is_subscription_active(self):
        """Проверка активности подписки"""
        if not self.subscription_expires_at:
            return False
        return self.subscription_expires_at > datetime.now()


class Invoice(BaseModel):
    """Модель счета на оплату"""

    id = AutoField()
    user_id = BigIntegerField()
    tariff_id = IntegerField()
    amount = FloatField()
    currency = CharField(default="RUB")
    description = TextField()
    status = CharField(default="created")  # created, paid, cancelled
    external_id = CharField(null=True)  # ID во внешней платежной системе
    transaction_id = CharField(null=True)
    payment_type = CharField(default="yookassa")  # Тип платежной системы
    confirmation_url = CharField(null=True)  # URL для подтверждения оплаты
    created_at = DateTimeField(default=datetime.now)
    paid_at = DateTimeField(null=True)

    @classmethod
    def create(cls, **kwargs):
        """Создание нового инвойса"""
        return super().create(**kwargs)

    @classmethod
    def get_by_id(cls, invoice_id):
        """Получение инвойса по ID"""
        try:
            return cls.get(cls.id == invoice_id)
        except DoesNotExist:
            return None

    @classmethod
    def get_by_user_id(cls, user_id):
        """Получение всех инвойсов пользователя"""
        return cls.select().where(cls.user_id == user_id)


class TariffPlan(BaseModel):
    """Модель тарифного плана"""

    id = AutoField()
    name = CharField()
    description = TextField()
    price = FloatField()
    currency = CharField(default="RUB")
    duration_days = IntegerField(default=30)
    max_devices = IntegerField(default=5)
    speed_limit = CharField(default="unlimited")  # unlimited, 10Mbps, 100Mbps, etc.
    created_at = DateTimeField(default=datetime.now)
    is_active = BooleanField(default=True)

    @property
    def features_list(self):
        """Получение списка возможностей тарифа"""
        # В реальном приложении это может быть связанная таблица
        features = []
        if self.speed_limit != "unlimited":
            features.append(f"Ограничение скорости: {self.speed_limit}")
        features.append(f"Максимум устройств: {self.max_devices}")
        features.append(f"Длительность: {self.duration_days} дней")
        return features


def initialize_database():
    """Инициализация базы данных"""
    db.connect()
    db.create_tables([User, Invoice, TariffPlan], safe=True)

    # Добавление тестовых тарифов, если их нет
    if TariffPlan.select().count() == 0:
        test_tariffs = [
            {
                "name": "Базовый",
                "description": "Подходит для обычного серфинга",
                "price": 199.0,
                "duration_days": 30,
                "max_devices": 2,
                "speed_limit": "100Mbps",
            },
            {
                "name": "Стандарт",
                "description": "Для более требовательных пользователей",
                "price": 399.0,
                "duration_days": 30,
                "max_devices": 5,
                "speed_limit": "500Mbps",
            },
            {
                "name": "Премиум",
                "description": "Максимальная скорость без ограничений",
                "price": 599.0,
                "duration_days": 30,
                "max_devices": 10,
                "speed_limit": "unlimited",
            },
        ]

        for tariff_data in test_tariffs:
            TariffPlan.create(**tariff_data)


# Инициализация базы данных при импорте модуля
initialize_database()
