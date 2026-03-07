from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass(frozen=True)
class MaxGatewayPublisher:
    token: str
    base_url: str = "https://botapi.max.ru"
    timeout_s: int = 30

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def send_message(self, *, chat_id: str, text: str) -> None:
        url = self._url("messages")
        params = {"access_token": self.token, "chat_id": chat_id}
        resp = requests.post(url, params=params, json={"text": text}, timeout=self.timeout_s)
        resp.raise_for_status()

    def send_file_url(self, *, chat_id: str, file_url: str, caption: str | None = None) -> None:
        url = self._url("messages")
        params = {"access_token": self.token, "chat_id": chat_id}
        payload: dict = {
            "attachments": [{"type": "image", "payload": {"url": file_url}}]
        }
        if caption:
            payload["text"] = caption
        resp = requests.post(url, params=params, json=payload, timeout=self.timeout_s)
        resp.raise_for_status()
