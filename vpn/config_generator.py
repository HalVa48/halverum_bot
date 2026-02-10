"""
Генерация конфигураций AmneziaVPN
"""

import base64
import json
import secrets
import tempfile

from cryptography.fernet import Fernet

from config import AMNEZIA_API_KEY, AMNEZIA_API_URL
from vpn.vpn_manager import VPNManager


class ConfigGenerator:
    """Класс для генерации конфигураций AmneziaVPN"""

    def __init__(self):
        self.api_url = AMNEZIA_API_URL
        self.api_key = AMNEZIA_API_KEY
        self.vpn_manager = VPNManager()

    def generate_config(self, user_id, tariff_plan):
        """Генерация конфигурации для пользователя на основе тарифного плана"""
        # Получаем параметры сервера и протокола из тарифного плана
        server_config = self._get_server_config(tariff_plan)
        protocol = tariff_plan.get("protocol", "wireguard")

        # Создаем конфигурацию в зависимости от протокола
        if protocol == "wireguard":
            config = self._generate_wireguard_config(
                user_id, server_config, tariff_plan
            )
        elif protocol == "openvpn":
            config = self._generate_openvpn_config(user_id, server_config, tariff_plan)
        elif protocol == "shadowsocks":
            config = self._generate_shadowsocks_config(
                user_id, server_config, tariff_plan
            )
        elif protocol == "awg":  # Amnezia WireGuard
            config = self._generate_awg_config(user_id, server_config, tariff_plan)
        elif protocol == "l2tp":
            config = self._generate_l2tp_config(user_id, server_config, tariff_plan)
        elif protocol == "sstp":
            config = self._generate_sstp_config(user_id, server_config, tariff_plan)
        elif protocol == "ikev2":
            config = self._generate_ikev2_config(user_id, server_config, tariff_plan)
        else:
            raise ValueError(f"Неподдерживаемый протокол: {protocol}")

        return config

    def _get_server_config(self, tariff_plan):
        """Получение конфигурации сервера для тарифного плана"""
        # В реальном приложении это будет запрос к API Amnezia или к базе данных
        # с информацией о доступных серверах
        # Для демонстрации возвращаем фиксированную конфигурацию
        return {
            "host": "vpn.example.com",
            "port": 51820,
            "public_key": "dummy_public_key",
            "private_key": "dummy_private_key",
            "allowed_ips": "0.0.0.0/0",
            "dns": "8.8.8.8,8.8.4.4",
        }

    def _generate_wireguard_config(self, user_id, server_config, tariff_plan):
        """Генерация WireGuard конфигурации"""
        client_private_key, client_public_key = self._generate_wireguard_keys()

        # Определяем IP-адрес клиента на основе user_id
        client_ip = f"10.8.{(user_id // 250) % 250}.{(user_id % 250) + 2}/32"

        config = f"""[Interface]
PrivateKey = {client_private_key}
Address = {client_ip}
DNS = {server_config["dns"]}

[Peer]
PublicKey = {server_config["public_key"]}
AllowedIPs = {server_config["allowed_ips"]}
Endpoint = {server_config["host"]}:{server_config["port"]}
PersistentKeepalive = 25
"""

        return {
            "config": config,
            "filename": f"amnezia_vpn_wireguard_{user_id}.conf",
            "protocol": "wireguard",
        }

    def _generate_awg_config(self, user_id, server_config, tariff_plan):
        """Генерация Amnezia WireGuard (Awg) конфигурации"""
        client_private_key, client_public_key = self._generate_wireguard_keys()

        # Amnezia WireGuard использует дополнительные параметры
        psk = self._generate_psk()  # Предварительно разделенный ключ

        client_ip = f"10.8.{(user_id // 250) % 250}.{(user_id % 250) + 2}/32"

        config = f"""[Interface]
PrivateKey = {client_private_key}
Address = {client_ip}
DNS = {server_config["dns"]}

[Peer]
PublicKey = {server_config["public_key"]}
PresharedKey = {psk}
AllowedIPs = {server_config["allowed_ips"]}
Endpoint = {server_config["host"]}:{server_config["port"]}
PersistentKeepalive = 25
"""

        return {
            "config": config,
            "filename": f"amnezia_vpn_awg_{user_id}.conf",
            "protocol": "awg",
        }

    def _generate_openvpn_config(self, user_id, server_config, tariff_plan):
        """Генерация OpenVPN конфигурации"""
        # Генерация сертификатов и ключей (в реальном приложении через API)
        ca_cert = "-----BEGIN CERTIFICATE-----\nMIIC..."
        client_cert = f"-----BEGIN CERTIFICATE-----\nMIIC...{user_id}"
        client_key = f"-----BEGIN PRIVATE KEY-----\nMIIE...{user_id}"

        config = f"""client
dev tun
proto udp
remote {server_config["host"]} {server_config["port"]}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
auth SHA256
cipher AES-256-CBC
verb 3
sndbuf 393216
rcvbuf 393216

# Сертификаты
<ca>
{ca_cert}
</ca>

<cert>
{client_cert}
</cert>

<key>
{client_key}
</key>
"""

        return {
            "config": config,
            "filename": f"amnezia_vpn_openvpn_{user_id}.ovpn",
            "protocol": "openvpn",
        }

    def _generate_shadowsocks_config(self, user_id, server_config, tariff_plan):
        """Генерация ShadowSocks конфигурации"""
        password = secrets.token_urlsafe(32)
        method = "chacha20-ietf-poly1305"

        config = {
            "server": server_config["host"],
            "server_port": server_config["port"],
            "password": password,
            "method": method,
            "plugin": "",
            "plugin_opts": "",
            "remarks": f"AmneziaVPN_ShadowSocks_{user_id}",
            "timeout": 600,
        }

        return {
            "config": json.dumps(config, indent=2),
            "filename": f"amnezia_vpn_shadowsocks_{user_id}.json",
            "protocol": "shadowsocks",
        }

    def _generate_l2tp_config(self, user_id, server_config, tariff_plan):
        """Генерация L2TP/IPSec конфигурации"""
        # L2TP не требует сложной конфигурации, только учетные данные
        username = f"user_{user_id}"
        password = secrets.token_urlsafe(16)

        config_data = {
            "server": server_config["host"],
            "username": username,
            "password": password,
            "pre_shared_key": secrets.token_urlsafe(16),
            "type": "l2tp",
            "notes": f"L2TP/IPSec конфигурация для пользователя {user_id}",
        }

        return {
            "config": json.dumps(config_data, indent=2),
            "filename": f"amnezia_vpn_l2tp_{user_id}.json",
            "protocol": "l2tp",
        }

    def _generate_sstp_config(self, user_id, server_config, tariff_plan):
        """Генерация SSTP конфигурации"""
        config = f"""# SSTP VPN Configuration
# Server: {server_config["host"]}
# Username: user_{user_id}
# Password: {secrets.token_urlsafe(16)}

sstpc {server_config["host"]} --user="user_{user_id}" --password="{secrets.token_urlsafe(16)}"
"""

        return {
            "config": config,
            "filename": f"amnezia_vpn_sstp_{user_id}.sh",
            "protocol": "sstp",
        }

    def _generate_ikev2_config(self, user_id, server_config, tariff_plan):
        """Генерация IKEv2 конфигурации"""
        config_data = {
            "server": server_config["host"],
            "username": f"user_{user_id}",
            "password": secrets.token_urlsafe(16),
            "identity": f"user_{user_id}@amneziavpn.com",
            "pre_shared_key": secrets.token_urlsafe(16),
            "type": "ikev2",
            "notes": f"IKEv2 конфигурация для пользователя {user_id}",
        }

        return {
            "config": json.dumps(config_data, indent=2),
            "filename": f"amnezia_vpn_ikev2_{user_id}.json",
            "protocol": "ikev2",
        }

    def _generate_wireguard_keys(self):
        """Генерация пары ключей для WireGuard"""
        import subprocess

        try:
            # Генерация приватного ключа
            private_key_result = subprocess.run(
                ["wg", "genkey"], capture_output=True, text=True, check=True
            )
            private_key = private_key_result.stdout.strip()

            # Генерация публичного ключа из приватного
            public_key_result = subprocess.run(
                ["wg", "pubkey"],
                input=private_key,
                capture_output=True,
                text=True,
                check=True,
            )
            public_key = public_key_result.stdout.strip()

            return private_key, public_key
        except Exception:
            # Если wg недоступен, генерируем ключи программно
            # WireGuard использует Curve25519, поэтому генерируем 32-байтовый ключ
            private_key = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")
            # Публичный ключ должен быть вычислен из приватного, но для демонстрации генерируем случайный
            public_key = base64.b64encode(secrets.token_bytes(32)).decode("utf-8")
            return private_key, public_key

    def _generate_psk(self):
        """Генерация предварительно разделенного ключа для Awg"""
        return base64.b64encode(secrets.token_bytes(32)).decode("utf-8")

    def encrypt_config(self, config_data, encryption_key=None):
        """Шифрование конфигурации"""
        if encryption_key is None:
            encryption_key = Fernet.generate_key()

        f = Fernet(encryption_key)
        encrypted_data = f.encrypt(config_data.encode())

        return {
            "encrypted_config": encrypted_data.decode(),
            "encryption_key": encryption_key.decode(),
        }

    def decrypt_config(self, encrypted_config, encryption_key):
        """Расшифровка конфигурации"""
        f = Fernet(encryption_key.encode())
        decrypted_data = f.decrypt(encrypted_config.encode())

        return decrypted_data.decode()


def save_config_to_file(config_data):
    """Сохранение конфигурации во временный файл"""
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=f".{config_data['filename'].split('.')[-1]}"
    ) as f:
        f.write(config_data["config"])
        return f.name
