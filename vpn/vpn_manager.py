"""
Управление VPN-подключениями
"""

import requests

from config import AMNEZIA_API_KEY, AMNEZIA_API_URL


class VPNManager:
    """Класс для управления VPN-подключениями через AmneziaAPI"""

    def __init__(self):
        self.api_url = AMNEZIA_API_URL
        self.api_key = AMNEZIA_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def create_user(self, user_id, tariff_plan):
        """Создание пользователя в системе VPN"""
        # В реальном приложении это будет вызов API Amnezia для создания клиента
        endpoint = f"{self.api_url}/users"

        user_data = {"user_id": user_id, "tariff_plan": tariff_plan, "enabled": True}

        try:
            response = requests.post(endpoint, headers=self.headers, json=user_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при создании пользователя: {e}")
            return None

    def remove_user(self, user_id):
        """Удаление пользователя из системы VPN"""
        endpoint = f"{self.api_url}/users/{user_id}"

        try:
            response = requests.delete(endpoint, headers=self.headers)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при удалении пользователя: {e}")
            return False

    def enable_user(self, user_id):
        """Активация пользователя в системе VPN"""
        endpoint = f"{self.api_url}/users/{user_id}/enable"

        try:
            response = requests.post(endpoint, headers=self.headers)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при активации пользователя: {e}")
            return False

    def disable_user(self, user_id):
        """Деактивация пользователя в системе VPN"""
        endpoint = f"{self.api_url}/users/{user_id}/disable"

        try:
            response = requests.delete(endpoint, headers=self.headers)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при деактивации пользователя: {e}")
            return False

    def get_user_config(self, user_id):
        """Получение конфигурации для пользователя"""
        endpoint = f"{self.api_url}/users/{user_id}/config"

        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении конфигурации пользователя: {e}")
            return None

    def get_server_info(self):
        """Получение информации о сервере"""
        endpoint = f"{self.api_url}/server/info"

        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении информации о сервере: {e}")
            return None

    def get_active_users_count(self):
        """Получение количества активных пользователей"""
        endpoint = f"{self.api_url}/stats/active_users"

        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            return response.json()["count"]
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении количества активных пользователей: {e}")
            return 0
