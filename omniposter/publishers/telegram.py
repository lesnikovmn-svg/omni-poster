from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass(frozen=True)
class TelegramPublisher:
    bot_token: str
    timeout_s: int = 30

    def _api(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}/{method}"

    def send_message(self, *, chat_id: str, text: str, parse_mode: str | None = None) -> None:
        payload: dict[str, object] = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        resp = requests.post(self._api("sendMessage"), json=payload, timeout=self.timeout_s)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram sendMessage failed: {data!r}")

    def send_photo(
        self,
        *,
        chat_id: str,
        image_path: Path,
        caption: str | None = None,
        parse_mode: str | None = None,
    ) -> None:
        files = {"photo": (image_path.name, image_path.read_bytes())}
        data: dict[str, object] = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        resp = requests.post(self._api("sendPhoto"), data=data, files=files, timeout=self.timeout_s)
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram sendPhoto failed: {payload!r}")

