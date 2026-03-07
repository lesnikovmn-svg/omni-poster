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

    def _upload_photo(self, image_path: Path) -> dict:
        # Получаем URL для загрузки
        r = requests.post(
            self._url("uploads"),
            params={"access_token": self.token, "type": "image"},
            timeout=self.timeout_s,
        )
        r.raise_for_status()
        upload_url = r.json()["url"]

        # Загружаем фото
        with open(image_path, "rb") as f:
            r2 = requests.post(upload_url, files={"data": (image_path.name, f, "image/jpeg")}, timeout=self.timeout_s)
        r2.raise_for_status()
        print(f"MAX upload response: {r2.json()}")
        return r2.json()

    def send_message(self, *, chat_id: str, text: str) -> None:
        url = self._url("messages")
        params = {"access_token": self.token, "chat_id": chat_id}
        resp = requests.post(url, params=params, json={"text": text}, timeout=self.timeout_s)
        resp.raise_for_status()

    def send_photos(self, *, chat_id: str, image_paths: list[Path], text: str) -> None:
        attachments = []
        for p in image_paths:
            try:
                photo_data = self._upload_photo(p)
                # MAX возвращает photos список
                photos = photo_data.get("photos") or []
                if photos:
                    token = photos[0].get("token")
                    if token:
                        attachments.append({"type": "image", "payload": {"token": token}})
            except Exception as e:
                print(f"MAX photo upload failed for {p}: {e}")

        url = self._url("messages")
        params = {"access_token": self.token, "chat_id": chat_id}
        payload: dict = {"text": text}
        if attachments:
            payload["attachments"] = attachments
        resp = requests.post(url, params=params, json=payload, timeout=self.timeout_s)
        resp.raise_for_status()
