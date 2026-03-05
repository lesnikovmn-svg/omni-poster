from __future__ import annotations

import time
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class InstagramGraphPublisher:
    access_token: str
    ig_user_id: str
    api_version: str = "v20.0"
    base_url: str = "https://graph.facebook.com"
    timeout_s: int = 30

    def _url(self, path: str) -> str:
        path = path.lstrip("/")
        return f"{self.base_url}/{self.api_version}/{path}"

    def _get(self, path: str, params: dict[str, object]) -> dict:
        merged = dict(params)
        merged["access_token"] = self.access_token
        resp = requests.get(self._url(path), params=merged, timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict[str, object]) -> dict:
        merged = dict(data)
        merged["access_token"] = self.access_token
        resp = requests.post(self._url(path), data=merged, timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.json()

    def publish_photo(self, *, image_url: str, caption: str) -> None:
        create = self._post(f"{self.ig_user_id}/media", {"image_url": image_url, "caption": caption})
        creation_id = create.get("id")
        if not creation_id:
            raise RuntimeError(f"IG create media failed: {create!r}")

        deadline = time.time() + 30
        while time.time() < deadline:
            status = self._get(str(creation_id), {"fields": "status_code"})
            code = status.get("status_code")
            if code == "FINISHED":
                break
            if code == "ERROR":
                raise RuntimeError(f"IG container error: {status!r}")
            time.sleep(2)

        publish = self._post(f"{self.ig_user_id}/media_publish", {"creation_id": creation_id})
        if "id" not in publish:
            raise RuntimeError(f"IG publish failed: {publish!r}")

