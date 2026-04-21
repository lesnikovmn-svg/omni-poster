from __future__ import annotations

import os
import requests


class AIRewriter:
    """Переписывает текст поста через Claude API."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY не задан")

    def rewrite(self, text: str, prompt: str | None = None) -> str:
        if not text.strip():
            return text

        system = prompt or (
            "Ты помогаешь переписывать посты для автомобильного бизнеса. "
            "Перепиши текст: сохрани смысл и факты, но сделай текст живым, "
            "естественным и привлекательным для VK/MAX аудитории. "
            "Убери упоминания других каналов и ссылки на Telegram. "
            "Верни только готовый текст без пояснений."
        )

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "system": system,
                "messages": [{"role": "user", "content": text}],
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"].strip()
