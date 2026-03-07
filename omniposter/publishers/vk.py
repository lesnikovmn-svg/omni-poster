from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests
from requests import RequestException


@dataclass(frozen=True)
class VkPublisher:
    access_token: str
    group_id: int
    user_access_token: str | None = None
    api_version: str = "5.131"
    timeout_s: int = 30

    def _call(self, method: str, params: dict[str, object], *, token: str | None = None) -> dict:
        url = f"https://api.vk.com/method/{method}"
        merged = dict(params)
        merged["access_token"] = token or self.access_token
        merged["v"] = self.api_version
        try:
            # Use POST to avoid putting tokens into the URL query string (safer for logs/stacktraces).
            resp = requests.post(url, data=merged, timeout=self.timeout_s)
        except RequestException as e:
            raise RuntimeError(f"VK request failed ({method}): network/DNS error") from e
        resp.raise_for_status()
        payload = resp.json()
        if "error" in payload:
            err = payload["error"]
            if isinstance(err, dict) and err.get("error_code") == 27 and self.user_access_token is None:
                raise RuntimeError(
                    "VK group token can't upload photos for wall posting. "
                    "Create a VK user access token and set VK_USER_ACCESS_TOKEN, then retry. "
                    f"Details: {err!r}"
                )
            raise RuntimeError(f"VK {method} error: {err!r}")
        return payload["response"]

    def post_text(self, *, text: str) -> None:
        upload_token = self.user_access_token or self.access_token
        self._call(
            "wall.post",
            {
                "owner_id": -abs(int(self.group_id)),
                "from_group": 1,
                "message": text,
            },
            token=upload_token,
        )

    def post_photo(self, *, text: str, image_path: Path) -> None:
        self.post_photos(text=text, image_paths=[image_path])

    def post_photos(self, *, text: str, image_paths: list[Path]) -> None:
        if not image_paths:
            raise ValueError("image_paths must be non-empty")
        upload_token = self.user_access_token or self.access_token
        server = self._call(
            "photos.getWallUploadServer",
            {"group_id": abs(int(self.group_id))},
            token=upload_token,
        )
        upload_url = server["upload_url"]

        attachments = []
        for p in image_paths:
            server = self._call(
                "photos.getWallUploadServer",
                {"group_id": abs(int(self.group_id))},
                token=upload_token,
            )
            upload_url = server["upload_url"]
            try:
                upload_resp = requests.post(upload_url, files={"photo": (p.name, p.read_bytes(), "image/jpeg")}, timeout=self.timeout_s)
            except RequestException as e:
                raise RuntimeError("VK upload failed: network/DNS error") from e
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
                token=upload_token,
            )
            if not isinstance(saved, list) or not saved:
                raise RuntimeError(f"VK saveWallPhoto response malformed: {saved!r}")
            for photo in saved:
                attachments.append(f"photo{photo['owner_id']}_{photo['id']}")

        self._call(
            "wall.post",
            {
                "owner_id": -abs(int(self.group_id)),
                "from_group": 1,
                "message": text,
                "attachments": ",".join(attachments),
            },
            token=upload_token,
        )
