import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_IDS", "")
    if not raw:
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    VPN_API_URL: str = os.getenv("VPN_API_URL", "http://localhost:8082")
    VPN_API_EMAIL: str = os.getenv("VPN_API_EMAIL", "admin@amnez.ia")
    VPN_API_PASSWORD: str = os.getenv("VPN_API_PASSWORD", "admin123")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///vpn_bot.db")

    ACCESS_PASSWORD: str = os.getenv("ACCESS_PASSWORD", "vpn2024")

    MAX_CONFIGS_PER_USER: int = 3

    ADMIN_IDS: list[int] = field(default_factory=_parse_admin_ids)

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.ADMIN_IDS


config = Config()
