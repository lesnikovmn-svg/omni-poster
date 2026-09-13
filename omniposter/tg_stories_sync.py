from __future__ import annotations
import os
import asyncio
import requests
import base64
from pathlib import Path


class TgStoriesSync:
    def __init__(
        self,
        session_string: str,
        api_id: int,
        api_hash: str,
        allowed_peers: list[str] | None = None,
    ):
        self._session_string = session_string
        self._api_id = api_id
        self._api_hash = api_hash
        # T-170 (13.09.2026, по запросу пользователя после проверки исходников -
        # "любые видимые peer'ы" из TASKS.md означало буквально ЛЮБОЙ Telegram
        # peer (канал/группу/личный контакт), чью сторис видит эта userbot-сессия:
        # GetAllStoriesRequest ничем не фильтровался, в отличие от tg-sync, где
        # --source обязателен. Теперь - allowlist по username ("me" = свой личный
        # аккаунт), резолвится в peer_id один раз за прогон в
        # _resolve_allowed_peer_ids(). Список можно переопределить через
        # STORIES_SYNC_ALLOWED_PEERS (см. cli.py); если не задан - безопасный
        # дефолт (не "всё", а только два рабочих канала + личный).
        self._allowed_usernames = (
            allowed_peers if allowed_peers is not None else ["MY_Avto5", "My_Avto_Optimal", "me"]
        )

    async def _resolve_allowed_peer_ids(self, client) -> set[int]:
        from telethon.utils import get_peer_id
        allowed_ids: set[int] = set()
        for username in self._allowed_usernames:
            name = username.strip()
            if not name:
                continue
            try:
                entity = await client.get_entity(name)
                allowed_ids.add(get_peer_id(entity))
            except Exception as e:
                print(f"[stories-sync] could not resolve allowed peer {name!r}: {e}")
        return allowed_ids

    async def _get_recent_stories(self, dest_dir: Path, already_seen: set[str]) -> list[tuple[str, Path]]:
        """T-164 (12.09.2026, найдено при работе над myavto-agregator T-163 -
        в .state/tg_stories/ обнаружены десятки дублей одного и того же
        файла сторис: story_471.mp4, story_471 (2).mp4 ... story_471 (24).mp4):

        Раньше эта функция на КАЖДЫЙ прогон (крон - каждые 5 минут, см.
        .github/workflows/omni-poster.yml) заново скачивала КАЖДУЮ видимую
        в Telegram сторис, не проверяя already_seen до скачивания. Локальный
        путь файла был "story_{id}" без привязки к тому, ОТ КОГО сторис
        (peer) - а Telegram нумерует id сторис отдельным счётчиком на
        каждого автора, поэтому сторис #5 канала A и сторис #5 канала B (или
        личного контакта) физически претендовали на один и тот же путь на
        диске. Из-за занятого имени Telethon сам добавлял " (n)" при каждом
        повторном скачивании - и именно этот "(n)" в ИМЕНИ ФАЙЛА (а не сам
        Telegram story id) использовался как ключ дедупа в run()
        (story_id = f.stem). У каждого прогона получался НОВЫЙ, отличающийся
        stem - "уже виденная" проверка никогда не срабатывала, run() считал
        сторис "новой" и публиковал её в Instagram Stories ПОВТОРНО,
        потенциально каждые 5 минут на всё время жизни сторис (обычно
        24-48ч), пока она не пропадала из GetAllStories.

        Исправлено: ключ дедупа - f"{peer_id}_{story.id}", собран из самого
        Telegram (peer + id), стабилен между прогонами и не коллизирует
        между разными авторами; already_seen проверяется ДО скачивания (не
        только перед публикацией) - уже опубликованные сторис вообще не
        скачиваются повторно. Это заодно останавливает бесконтрольный рост
        .state/tg_stories/ (на момент находки - сотни файлов, суммарно сотни
        МБ, закоммиченных в историю git через "chore: update state" коммиты
        крона).

        T-170 (13.09.2026): добавлен allowlist по peer - раньше скачивались
        и публиковались сторис ЛЮБОГО peer'а, видимого этой сессии (личные
        контакты, случайные каналы), т.к. GetAllStoriesRequest ничем не
        фильтровался. Теперь peer_key сверяется с заранее резолвленным
        множеством allowed_peer_ids (self._allowed_usernames) - всё, чего
        нет в allowlist, пропускается ДО скачивания."""
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.tl.functions.stories import GetAllStoriesRequest
        from telethon.utils import get_peer_id
        results: list[tuple[str, Path]] = []
        client = TelegramClient(StringSession(self._session_string), self._api_id, self._api_hash)
        await client.connect()
        try:
            allowed_peer_ids = await self._resolve_allowed_peer_ids(client)
            if not allowed_peer_ids:
                print("[stories-sync] no allowed peers could be resolved, skipping this run")
                return results
            result = await client(GetAllStoriesRequest(next=False, hidden=False))
            for peer_stories in result.peer_stories:
                peer_key = get_peer_id(peer_stories.peer)
                if peer_key not in allowed_peer_ids:
                    continue
                for story in peer_stories.stories:
                    if not (hasattr(story, "media") and story.media):
                        continue
                    story_key = f"{peer_key}_{story.id}"
                    if story_key in already_seen:
                        continue
                    path = dest_dir / story_key
                    downloaded = await client.download_media(story.media, str(path))
                    if downloaded:
                        results.append((story_key, Path(downloaded)))
        except Exception as e:
            print(f"[stories-sync] TG error: {e}")
        finally:
            await client.disconnect()
        return results

    def post_to_instagram_story(self, file_path: Path, ig_token: str, ig_account_id: str) -> bool:
        suffix = file_path.suffix.lower()
        is_video = suffix in (".mp4", ".mov", ".avi")

        if is_video:
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
        downloaded = asyncio.run(self._get_recent_stories(dest_dir, seen))
        posted = 0
        new_seen = set(seen)

        for story_key, f in downloaded:
            ok = self.post_to_instagram_story(f, ig_token, ig_account_id)
            if ok:
                new_seen.add(story_key)
                posted += 1
            # T-164: чистим локальный файл в ЛЮБОМ случае (успех/провал) -
            # успешные уже не скачаются снова (story_key в new_seen), а
            # неудачные просто перекачаются заново на следующем прогоне,
            # пока сторис ещё жива в Telegram. Не даём .state/tg_stories/
            # расти бесконтрольно ни в одном из исходов.
            try:
                f.unlink()
            except OSError:
                pass

        seen_path.write_text(json.dumps(sorted(new_seen)))
        return posted
