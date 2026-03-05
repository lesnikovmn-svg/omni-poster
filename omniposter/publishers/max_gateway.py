from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class MaxGatewayPublisher:
    token: str
    base_url: str = "https://app.api-messenger.com/max-v1"
    timeout_s: int = 30

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def send_message(self, *, chat_id: str, text: str) -> None:
        url = self._url("sendMessage")
        params = {"token": self.token}
        payload = [{"chatId": chat_id, "message": text}]
        resp = requests.post(url, params=params, json=payload, timeout=self.timeout_s)
        resp.raise_for_status()

    def send_file_url(self, *, chat_id: str, file_url: str, caption: str | None = None) -> None:
        url = self._url("sendFileUrl")
        params = {"token": self.token}
        message: dict[str, object] = {"chatId": chat_id, "url": file_url}
        if caption:
            message["caption"] = caption
        payload = [message]
        resp = requests.post(url, params=params, json=payload, timeout=self.timeout_s)
        resp.raise_for_status()

