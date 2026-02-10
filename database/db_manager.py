"""
Управление базой данных
"""

from playhouse.migrate import SqliteMigrator

from database.models import Invoice, TariffPlan, User, db


class DatabaseManager:
    """Класс для управления базой данных"""

    def __init__(self):
        self.db = db
        self.migrator = SqliteMigrator(self.db)

    def connect(self):
        """Подключение к базе данных"""
        if not self.db.is_closed():
            self.db.close()
        self.db.connect()

    def close(self):
        """Закрытие соединения с базой данных"""
        if not self.db.is_closed():
            self.db.close()

    def backup_database(self, backup_path):
        """Создание резервной копии базы данных"""
        import shutil

        self.db.close()
        shutil.copyfile("vpn_bot.db", backup_path)
        self.db.connect()

    def restore_database(self, backup_path):
        """Восстановление базы данных из резервной копии"""
        import shutil

        self.db.close()
        shutil.copyfile(backup_path, "vpn_bot.db")
        self.db.connect()

    def get_statistics(self):
        """Получение статистики по базе данных"""
        total_users = User.select().count()
        active_users = User.select().where(User.is_active == True).count()
        total_revenue = (
            Invoice.select(fn.SUM(Invoice.amount))
            .where(Invoice.status == "paid")
            .scalar()
            or 0
        )
        total_invoices = Invoice.select().count()
        paid_invoices = Invoice.select().where(Invoice.status == "paid").count()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_revenue": total_revenue,
            "total_invoices": total_invoices,
            "paid_invoices": paid_invoices,
        }

    def cleanup_expired_subscriptions(self):
        """Очистка просроченных подписок"""
        from datetime import datetime

        expired_users = User.select().where(
            (User.subscription_expires_at < datetime.now()) & (User.is_active == True)
        )

        count = 0
        for user in expired_users:
            user.is_active = False
            user.tariff_id = None
            user.save()
            count += 1

        return count

    def add_tariff_plan(
        self,
        name,
        description,
        price,
        duration_days,
        max_devices,
        speed_limit="unlimited",
    ):
        """Добавление нового тарифного плана"""
        tariff = TariffPlan.create(
            name=name,
            description=description,
            price=price,
            duration_days=duration_days,
            max_devices=max_devices,
            speed_limit=speed_limit,
        )
        return tariff

    def update_tariff_plan(self, tariff_id, **kwargs):
        """Обновление тарифного плана"""
        query = TariffPlan.update(**kwargs).where(TariffPlan.id == tariff_id)
        return query.execute()

    def delete_tariff_plan(self, tariff_id):
        """Удаление тарифного плана"""
        tariff = TariffPlan.get_by_id(tariff_id)
        if tariff:
            tariff.delete_instance()
            return True
        return False
