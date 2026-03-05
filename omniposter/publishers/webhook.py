from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass(frozen=True)
class WebhookPublisher:
    timeout_s: int = 30

    def post_json(self, *, url: str, payload: dict, headers: dict[str, str] | None = None) -> None:
        resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout_s)
        resp.raise_for_status()

    def post_multipart(
        self,
        *,
        url: str,
        payload: dict,
        file_path: Path,
        file_field: str = "file",
        headers: dict[str, str] | None = None,
    ) -> None:
        form = {"payload": json.dumps(payload, ensure_ascii=False)}
        files = {file_field: (file_path.name, file_path.read_bytes())}
        resp = requests.post(url, data=form, files=files, headers=headers, timeout=self.timeout_s)
        resp.raise_for_status()

