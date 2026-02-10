"""
Модуль для работы с платежами
"""

import hashlib
import hmac
import time
import uuid
from abc import ABC, abstractmethod

import requests

from config import PAYMENT_TOKEN, SHOP_ID


class PaymentSystem(ABC):
    """Абстрактный класс для работы с платежной системой"""

    def __init__(self, token, shop_id):
        self.token = token
        self.shop_id = shop_id

    @abstractmethod
    def create_invoice(
        self, user_id, amount, currency, description, success_url=None, fail_url=None
    ):
        """Создание счета на оплату"""
        pass

    @abstractmethod
    def check_payment_status(self, invoice_id):
        """Проверка статуса оплаты"""
        pass

    @abstractmethod
    def refund_payment(self, payment_id, amount=None):
        """Возврат средств"""
        pass


class YooKassaPayment(PaymentSystem):
    """Интеграция с YooKassa"""

    def __init__(self, token, shop_id):
        super().__init__(token, shop_id)
        self.api_url = "https://api.yookassa.ru/v3"
        self.headers = {
            "Idempotence-Key": str(uuid.uuid4()),
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    def create_invoice(
        self, user_id, amount, currency, description, success_url=None, fail_url=None
    ):
        """Создание платежа в YooKassa"""
        payload = {
            "amount": {"value": f"{amount:.2f}", "currency": currency},
            "capture": True,
            "description": description,
            "metadata": {"user_id": user_id},
            "payment_method_data": {"type": "bank_card"},
            "confirmation": {
                "type": "redirect",
                "return_url": success_url or "https://t.me/vpn_bot",
            },
            "save_payment_method": False,
            "capture": True,
        }

        response = requests.post(
            f"{self.api_url}/payments", json=payload, headers=self.headers
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "id": data["id"],
                "status": data["status"],
                "confirmation_url": data["confirmation_url"],
                "created_at": data["created_at"],
                "amount": data["amount"],
            }
        else:
            raise Exception(f"Ошибка при создании платежа: {response.text}")

    def check_payment_status(self, payment_id):
        """Проверка статуса платежа в YooKassa"""
        response = requests.get(
            f"{self.api_url}/payments/{payment_id}", headers=self.headers
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "id": data["id"],
                "status": data["status"],
                "paid": data["paid"],
                "amount": data["amount"],
                "created_at": data["created_at"],
            }
        else:
            raise Exception(f"Ошибка при проверке статуса платежа: {response.text}")

    def refund_payment(self, payment_id, amount=None):
        """Создание возврата в YooKassa"""
        payload = {
            "payment_id": payment_id,
        }

        if amount:
            payload["amount"] = {"value": f"{amount:.2f}", "currency": "RUB"}

        response = requests.post(
            f"{self.api_url}/refunds", json=payload, headers=self.headers
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Ошибка при создании возврата: {response.text}")


class TinkoffPayment(PaymentSystem):
    """Интеграция с Tinkoff"""

    def __init__(self, token, terminal_key):
        super().__init__(token, terminal_key)
        self.api_url = "https://securepay.tinkoff.ru/v2"

    def create_invoice(
        self, user_id, amount, currency, description, success_url=None, fail_url=None
    ):
        """Создание платежа в Tinkoff"""
        # Генерация OrderId
        order_id = f"order_{user_id}_{int(time.time())}"

        payload = {
            "TerminalKey": self.shop_id,
            "OrderId": order_id,
            "Amount": int(amount * 100),  # Сумма в копейках
            "Description": description,
            "DATA": {"Phone": "", "Email": "", "UserId": str(user_id)},
        }

        # Добавление реквизитов, если сумма больше 10000
        if amount >= 10000:
            payload["Receipt"] = {
                "Email": "",
                "Taxation": "osn",
                "Items": [
                    {
                        "Name": description,
                        "Price": int(amount * 100),
                        "Quantity": 1,
                        "Amount": int(amount * 100),
                        "Tax": "none",
                    }
                ],
            }

        # Вычисление контрольной суммы
        payload["Token"] = self._calculate_token(payload)

        response = requests.post(f"{self.api_url}/Init", json=payload)

        if response.status_code == 200:
            data = response.json()
            if data.get("Success"):
                return {
                    "id": data["PaymentId"],
                    "status": "pending",
                    "confirmation_url": "https://securepay.tinkoff.ru/v2/GetQr/?"
                    + f"TerminalKey={self.shop_id}&PaymentId={data['PaymentId']}",
                    "created_at": time.time(),
                    "amount": amount,
                }
            else:
                raise Exception(f"Ошибка при создании платежа: {data.get('Message')}")
        else:
            raise Exception(f"Ошибка при создании платежа: {response.text}")

    def check_payment_status(self, payment_id):
        """Проверка статуса платежа в Tinkoff"""
        payload = {"TerminalKey": self.shop_id, "PaymentId": payment_id}

        payload["Token"] = self._calculate_token(payload)

        response = requests.post(f"{self.api_url}/GetState", json=payload)

        if response.status_code == 200:
            data = response.json()
            if data.get("Success"):
                return {
                    "id": payment_id,
                    "status": data["Status"],
                    "paid": data["Status"] == "CONFIRMED",
                    "amount": data.get("Amount", 0)
                    / 100,  # Переводим из копеек в рубли
                    "created_at": time.time(),
                }
            else:
                raise Exception(f"Ошибка при проверке статуса: {data.get('Message')}")
        else:
            raise Exception(f"Ошибка при проверке статуса: {response.text}")

    def refund_payment(self, payment_id, amount=None):
        """Создание возврата в Tinkoff"""
        payload = {"TerminalKey": self.shop_id, "PaymentId": payment_id}

        if amount:
            payload["Amount"] = int(amount * 100)  # Сумма в копейках

        payload["Token"] = self._calculate_token(payload)

        response = requests.post(f"{self.api_url}/Cancel", json=payload)

        if response.status_code == 200:
            data = response.json()
            if data.get("Success"):
                return data
            else:
                raise Exception(f"Ошибка при создании возврата: {data.get('Message')}")
        else:
            raise Exception(f"Ошибка при создании возврата: {response.text}")

    def _calculate_token(self, params):
        """Вычисление контрольной суммы для Tinkoff"""
        # Исключаем Token из вычислении
        filtered_params = {k: v for k, v in params.items() if k != "Token"}

        # Сортируем параметры по имени
        sorted_params = sorted(filtered_params.items())

        # Формируем строку для хэширования
        values = [str(v) for k, v in sorted_params]
        values.append(self.token)  # Добавляем пароль в конец

        # Вычисляем SHA-256 хэш
        hash_string = "".join(values)
        token = hmac.new(
            self.token.encode("utf-8"), hash_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return token


class CryptoPayment(PaymentSystem):
    """Интеграция с криптоплатежами (например, через CoinGate или другие сервисы)"""

    def __init__(self, token, api_url="https://api.coingate.net/v2"):
        super().__init__(token, api_url)
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def create_invoice(
        self, user_id, amount, currency, description, success_url=None, fail_url=None
    ):
        """Создание криптоплатежа"""
        payload = {
            "order_id": f"vpn_order_{user_id}_{int(time.time())}",
            "price_amount": amount,
            "price_currency": currency,
            "receive_currency": "BTC",  # Можно настроить на любую криптовалюту
            "title": description,
            "description": f"VPN-подписка для пользователя {user_id}",
            "success_url": success_url or "https://t.me/vpn_bot",
            "cancel_url": fail_url or "https://t.me/vpn_bot",
        }

        response = requests.post(
            f"{self.api_url}/orders", json=payload, headers=self.headers
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "id": data["id"],
                "status": data["status"],
                "payment_address": data["payment_address"],
                "price_amount": data["price_amount"],
                "price_currency": data["price_currency"],
                "receive_amount": data["receive_amount"],
                "receive_currency": data["receive_currency"],
                "created_at": data["created_at"],
                "expire_at": data["expire_at"],
            }
        else:
            raise Exception(f"Ошибка при создании криптоплатежа: {response.text}")

    def check_payment_status(self, order_id):
        """Проверка статуса криптоплатежа"""
        response = requests.get(
            f"{self.api_url}/orders/{order_id}", headers=self.headers
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "id": data["id"],
                "status": data["status"],
                "paid": data["status"] in ["paid", "confirmed"],
                "amount": data["price_amount"],
                "currency": data["price_currency"],
                "created_at": data["created_at"],
            }
        else:
            raise Exception(
                f"Ошибка при проверке статуса криптоплатежа: {response.text}"
            )

    def refund_payment(self, payment_id, amount=None):
        """Возврат криптоплатежа (обычно невозможен, но можно реализовать внутренний возврат)"""
        # Криптоплатежи обычно не поддерживают возврат средств напрямую
        # Вместо этого можно реализовать внутренний возврат средств пользователю
        raise NotImplementedError("Возврат криптоплатежей не поддерживается")


def get_payment_system(payment_type="yookassa"):
    """Фабрика для получения экземпляра платежной системы"""
    if payment_type.lower() == "yookassa":
        return YooKassaPayment(PAYMENT_TOKEN, SHOP_ID)
    elif payment_type.lower() == "tinkoff":
        return TinkoffPayment(PAYMENT_TOKEN, SHOP_ID)
    elif payment_type.lower() == "crypto":
        return CryptoPayment(PAYMENT_TOKEN)
    else:
        raise ValueError(f"Неизвестная платежная система: {payment_type}")
