from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import requests


@dataclass(frozen=True)
class TelegramPublisher:
    bot_token: str
    timeout_s: int = 30

    def _api(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}/{method}"

    def send_message(
        self,
        *,
        chat_id: str,
        text: str,
        parse_mode: str | None = None,
        reply_markup: dict | None = None,
    ) -> None:
        payload: dict[str, object] = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup
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
        reply_markup: dict | None = None,
    ) -> None:
        files = {"photo": (image_path.name, image_path.read_bytes())}
        data: dict[str, object] = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        resp = requests.post(self._api("sendPhoto"), data=data, files=files, timeout=self.timeout_s)
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram sendPhoto failed: {payload!r}")

    def send_media_group(
        self,
        *,
        chat_id: str,
        image_paths: list[Path],
        caption: str | None = None,
        parse_mode: str | None = None,
    ) -> None:
        if not image_paths:
            raise ValueError("image_paths must be non-empty")
        if len(image_paths) > 10:
            raise ValueError("Telegram media groups support up to 10 items")

        files: dict[str, tuple[str, bytes]] = {}
        media: list[dict[str, object]] = []
        for idx, path in enumerate(image_paths, start=1):
            key = f"file{idx}"
            files[key] = (path.name, path.read_bytes())
            item: dict[str, object] = {"type": "photo", "media": f"attach://{key}"}
            if idx == 1 and caption:
                item["caption"] = caption
            if idx == 1 and parse_mode:
                item["parse_mode"] = parse_mode
            media.append(item)

        data = {"chat_id": chat_id, "media": json.dumps(media, ensure_ascii=False)}
        resp = requests.post(self._api("sendMediaGroup"), data=data, files=files, timeout=self.timeout_s)
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram sendMediaGroup failed: {payload!r}")
