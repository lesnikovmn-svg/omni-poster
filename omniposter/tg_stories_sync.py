from __future__ import annotations
import os
import asyncio
import requests
import base64
from pathlib import Path


class TgStoriesSync:
    def __init__(self, session_string: str, api_id: int, api_hash: str):
        self._session_string = session_string
        self._api_id = api_id
        self._api_hash = api_hash

    async def _get_recent_stories(self, dest_dir: Path) -> list[Path]:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        files = []
        async with TelegramClient(StringSession(self._session_string), self._api_id, self._api_hash) as client:
            result = await client(client._TelegramClient__help_get_app_update())
            stories = await client.get_stories("me")
            for story in stories:
                if hasattr(story, "media") and story.media:
                    path = dest_dir / f"story_{story.id}"
                    await client.download_media(story.media, str(path))
                    # Найдём скачанный файл
                    for f in dest_dir.glob(f"story_{story.id}*"):
                        files.append(f)
                        break
        return files

    def post_to_instagram_story(self, file_path: Path, ig_token: str, ig_account_id: str) -> bool:
        suffix = file_path.suffix.lower()
        is_video = suffix in (".mp4", ".mov", ".avi")

        if is_video:
            # Загружаем видео на cloudinary
            try:
                import cloudinary
                import cloudinary.uploader
                result = cloudinary.uploader.upload(str(file_path), resource_type="video")
                media_url = result["secure_url"]
                r = requests.post(
                    f"https://graph.instagram.com/v21.0/{ig_account_id}/media",
                    params={"access_token": ig_token},
                    json={"media_type": "STORIES", "video_url": media_url},
                    timeout=30,
                )
            except Exception as e:
                print(f"[Stories] video upload failed: {e}")
                return False
        else:
            # Фото через imgbb
            imgbb_key = os.environ.get("IMGBB_API_KEY")
            with open(file_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            r2 = requests.post(
                "https://api.imgbb.com/1/upload",
                data={"key": imgbb_key, "image": data},
                timeout=60,
            )
            r2.raise_for_status()
            media_url = r2.json()["data"]["url"]
            r = requests.post(
                f"https://graph.instagram.com/v21.0/{ig_account_id}/media",
                params={"access_token": ig_token},
                json={"media_type": "STORIES", "image_url": media_url},
                timeout=30,
            )

        if r.status_code != 200:
            print(f"[Stories] create container failed: {r.text}")
            return False

        container_id = r.json()["id"]
        # Публикуем
        r2 = requests.post(
            f"https://graph.instagram.com/v21.0/{ig_account_id}/media_publish",
            params={"access_token": ig_token},
            json={"creation_id": container_id},
            timeout=30,
        )
        if r2.status_code == 200:
            print(f"[Stories] published: {r2.json().get('id')}")
            return True
        print(f"[Stories] publish failed: {r2.text}")
        return False

    def run(self, dest_dir: Path, ig_token: str, ig_account_id: str, seen_path: Path) -> int:
        import json
        seen = set()
        if seen_path.exists():
            seen = set(json.loads(seen_path.read_text()))

        dest_dir.mkdir(parents=True, exist_ok=True)
        files = asyncio.run(self._get_recent_stories(dest_dir))
        posted = 0
        new_seen = set(seen)

        for f in files:
            story_id = f.stem
            if story_id in seen:
                continue
            ok = self.post_to_instagram_story(f, ig_token, ig_account_id)
            if ok:
                new_seen.add(story_id)
                posted += 1

        seen_path.write_text(json.dumps(list(new_seen)))
        return posted
