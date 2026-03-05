from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass(frozen=True)
class VkPublisher:
    access_token: str
    group_id: int
    api_version: str = "5.131"
    timeout_s: int = 30

    def _call(self, method: str, params: dict[str, object]) -> dict:
        url = f"https://api.vk.com/method/{method}"
        merged = dict(params)
        merged["access_token"] = self.access_token
        merged["v"] = self.api_version
        resp = requests.get(url, params=merged, timeout=self.timeout_s)
        resp.raise_for_status()
        payload = resp.json()
        if "error" in payload:
            raise RuntimeError(f"VK {method} error: {payload['error']!r}")
        return payload["response"]

    def post_text(self, *, text: str) -> None:
        self._call(
            "wall.post",
            {
                "owner_id": -abs(int(self.group_id)),
                "from_group": 1,
                "message": text,
            },
        )

    def post_photo(self, *, text: str, image_path: Path) -> None:
        server = self._call("photos.getWallUploadServer", {"group_id": abs(int(self.group_id))})
        upload_url = server["upload_url"]

        files = {"photo": (image_path.name, image_path.read_bytes())}
        upload_resp = requests.post(upload_url, files=files, timeout=self.timeout_s)
        upload_resp.raise_for_status()
        upload_data = upload_resp.json()
        if not all(k in upload_data for k in ("server", "photo", "hash")):
            raise RuntimeError(f"VK upload response malformed: {upload_data!r}")

        saved = self._call(
            "photos.saveWallPhoto",
            {
                "group_id": abs(int(self.group_id)),
                "server": upload_data["server"],
                "photo": upload_data["photo"],
                "hash": upload_data["hash"],
            },
        )
        if not isinstance(saved, list) or not saved:
            raise RuntimeError(f"VK saveWallPhoto response malformed: {saved!r}")
        photo = saved[0]
        owner_id = photo["owner_id"]
        photo_id = photo["id"]
        attachment = f"photo{owner_id}_{photo_id}"

        self._call(
            "wall.post",
            {
                "owner_id": -abs(int(self.group_id)),
                "from_group": 1,
                "message": text,
                "attachments": attachment,
            },
        )

