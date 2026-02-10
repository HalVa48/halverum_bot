"""
Управление счетами и оплатами
"""

import time

from database.models import Invoice, User
from payments.payment_system import get_payment_system


def create_invoice(user_id, tariff, payment_type="yookassa"):
    """Создание счета на оплату для пользователя"""
    # Получаем настройки платежной системы из конфига
    payment_system = get_payment_system(payment_type)

    # Создаем запись о счете в базе данных
    invoice = Invoice.create(
        user_id=user_id,
        tariff_id=tariff["id"],
        amount=tariff["price"],
        currency=tariff["currency"],
        description=f"Оплата за тариф {tariff['name']}",
        status="created",
        payment_type=payment_type,
    )

    # Создаем инвойс в платежной системе
    payment_data = payment_system.create_invoice(
        user_id=user_id,
        amount=tariff["price"],
        currency=tariff["currency"],
        description=f"Оплата за тариф {tariff['name']}",
        success_url="https://t.me/vpn_bot",
        fail_url="https://t.me/vpn_bot",
    )

    # Обновляем данные инвойса в базе
    invoice.external_id = payment_data["id"]
    invoice.confirmation_url = payment_data.get("confirmation_url")
    invoice.save()

    return {
        "id": invoice.id,
        "external_id": invoice.external_id,
        "confirmation_url": invoice.confirmation_url,
        "status": invoice.status,
        "amount": invoice.amount,
        "currency": invoice.currency,
    }


def process_payment(invoice_id):
    """Обработка оплаты по инвойсу"""
    invoice = Invoice.get_by_id(invoice_id)

    if not invoice:
        raise ValueError(f"Инвойс с ID {invoice_id} не найден")

    # Получаем платежную систему, которая была использована для создания инвойса
    payment_system = get_payment_system(invoice.payment_type)

    # Проверяем статус оплаты во внешней платежной системе
    payment_status = payment_system.check_payment_status(invoice.external_id)

    if payment_status["paid"]:
        # Обновляем статус инвойса
        invoice.status = "paid"
        invoice.paid_at = time.time()
        invoice.transaction_id = payment_status["id"]
        invoice.save()

        # Активируем подписку для пользователя
        user = User.get_or_create(user_id=invoice.user_id)
        user.activate_subscription(invoice.tariff_id)

        return True

    return False


def get_user_invoices(user_id):
    """Получение списка инвойсов пользователя"""
    return Invoice.get_by_user_id(user_id)


def check_pending_payments():
    """Проверка всех незавершенных платежей"""
    pending_invoices = Invoice.select().where(Invoice.status == "created")
    processed_count = 0

    for invoice in pending_invoices:
        try:
            if process_payment(invoice.id):
                processed_count += 1
        except Exception as e:
            print(f"Ошибка при обработке инвойса {invoice.id}: {e}")

    return processed_count
