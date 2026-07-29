"""Централизованная конфигурация из переменных окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
USERS_DIR = BASE_DIR / "users"


@dataclass(frozen=True, slots=True)
class Settings:
    vk_token: str
    proxy_api_key: str
    gemini_model: str
    proxyapi_google_base_url: str
    max_history_messages: int
    max_message_length: int
    users_dir: Path
    fallback_reply: str

    @classmethod
    def from_env(cls) -> Settings:
        vk_token = (os.getenv("VK_TOKEN") or "").strip()
        proxy_api_key = (
            os.getenv("PROXY_API_KEY")
            or os.getenv("PROXI_API_KEY")
            or ""
        ).strip()

        if not vk_token:
            raise ValueError("Не задан VK_TOKEN в .env")
        if not proxy_api_key:
            raise ValueError("Не задан PROXY_API_KEY / PROXI_API_KEY в .env")

        return cls(
            vk_token=vk_token,
            proxy_api_key=proxy_api_key,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
            proxyapi_google_base_url=os.getenv(
                "PROXYAPI_GOOGLE_BASE_URL",
                "https://api.proxyapi.ru/google",
            ).strip(),
            max_history_messages=int(os.getenv("MAX_HISTORY_MESSAGES", "100")),
            max_message_length=int(os.getenv("MAX_MESSAGE_LENGTH", "3500")),
            users_dir=USERS_DIR,
            fallback_reply=(
                "Сейчас не удалось получить ответ от AI. "
                "Попробуйте ещё раз чуть позже."
            ),
        )


settings = Settings.from_env()
