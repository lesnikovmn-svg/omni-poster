from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str | None
    webhook_default_url: str | None
    vk_access_token: str | None
    vk_group_id: int | None
    ig_access_token: str | None
    ig_user_id: str | None
    ig_graph_version: str
    max_api_token: str | None
    max_api_base: str


def load_config() -> Config:
    dotenv_path = os.getenv("DOTENV_PATH")
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path)
    else:
        secrets_env = Path("secrets/.env")
        if secrets_env.exists():
            load_dotenv(dotenv_path=secrets_env)
        else:
            load_dotenv()
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN") or None
    webhook_default_url = os.getenv("WEBHOOK_DEFAULT_URL") or None
    vk_access_token = os.getenv("VK_ACCESS_TOKEN") or None
    vk_group_id_raw = os.getenv("VK_GROUP_ID") or ""
    vk_group_id = int(vk_group_id_raw) if vk_group_id_raw.strip() else None
    ig_access_token = os.getenv("IG_ACCESS_TOKEN") or None
    ig_user_id = os.getenv("IG_USER_ID") or None
    ig_graph_version = os.getenv("IG_GRAPH_VERSION") or "v20.0"
    max_api_token = os.getenv("MAX_API_TOKEN") or None
    max_api_base = os.getenv("MAX_API_BASE") or "https://app.api-messenger.com/max-v1"
    return Config(
        telegram_bot_token=telegram_bot_token,
        webhook_default_url=webhook_default_url,
        vk_access_token=vk_access_token,
        vk_group_id=vk_group_id,
        ig_access_token=ig_access_token,
        ig_user_id=ig_user_id,
        ig_graph_version=ig_graph_version,
        max_api_token=max_api_token,
        max_api_base=max_api_base,
    )
