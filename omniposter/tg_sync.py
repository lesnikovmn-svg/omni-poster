import time
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import requests

from .publishers.vk import VkPublisher
from .publishers.max_gateway import MaxGatewayPublisher


@dataclass(frozen=True)
class TgSyncConfig:
    telegram_bot_token: str | None
    vk_access_token: str | None
    vk_user_access_token: str | None
    vk_group_id: int | None
    max_api_token: str | None = None
    max_api_base: str = "https://botapi.max.ru"
    max_chat_id: str | None = None
    links_file: str | None = None
    timeout_s: int = 30


class TgSync:
    def __init__(self, *, config: TgSyncConfig):
        self._config = config
        self._links = self._load_links()

    def _load_links(self) -> list[dict[str, str]]:
        candidate = self._config.links_file or "secrets/tg_links.json"
        path = Path(candidate)
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError(f"tg links file must be a JSON array: {path}")
        links: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            label = item.get("label")
            url = item.get("url")
            if not label or not url:
                continue
            links.append({"label": str(label), "url": str(url)})
        return links

    def _fix_tg_mentions(self, text: str) -> str:
        import re
        return re.sub(r'@([A-Za-z0-9_]+)', r't.me/\1', text)

    def _fix_tg_mentions(self, text: str) -> str:
        import re
        return re.sub(r'@([A-Za-z0-9_]+)', r't.me/\1', text)

    def _append_links(self, text: str) -> str:
        if not self._links:
            return text
        lines = [text, "", "Ссылки:"]
        for link in self._links:
            label = link.get("label")
            url = link.get("url")
            if label and url:
                lines.append(f"{label} {url}")
        return "\n".join(lines)

    def _tg_api(self, method: str) -> str:
        if not self._config.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required for tg-sync")
        return f"https://api.telegram.org/bot{self._config.telegram_bot_token}/{method}"

    def _tg_file_url(self, file_path: str) -> str:
        if not self._config.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required for tg-sync")
        return f"https://api.telegram.org/file/bot{self._config.telegram_bot_token}/{file_path}"

    def _load_json(self, path: Path, default):
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_json(self, path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _extract_source_key(self, source: str) -> tuple[str, int | None]:
        s = source.strip()
        if s.startswith("@"):
            return ("username", s[1:])
        if s.lstrip("-").isdigit():
            return ("chat_id", int(s))
        return ("username", s)

    def _pick_video_file_id(self, message: dict) -> str | None:
        video = message.get("video")
        if isinstance(video, dict):
            return video.get("file_id")
        return None

    def _pick_biggest_photo_file_id(self, message: dict) -> str | None:
        photos = message.get("photo")
        if not isinstance(photos, list) or not photos:
            return None
        best = None
        best_area = -1
        for p in photos:
            if not isinstance(p, dict):
                continue
            fid = p.get("file_id")
            w = p.get("width") or 0
            h = p.get("height") or 0
            area = int(w) * int(h)
            if fid and area > best_area:
                best = str(fid)
                best_area = area
        return best

    def _get_file_path(self, file_id: str) -> str:
        resp = requests.get(self._tg_api("getFile"), params={"file_id": file_id}, timeout=self._config.timeout_s)
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram getFile failed: {payload!r}")
        result = payload.get("result") or {}
        file_path = result.get("file_path")
        if not file_path:
            raise RuntimeError(f"Telegram getFile missing file_path: {payload!r}")
        return str(file_path)

    def _download_file(self, file_id: str, dest_dir: Path) -> Path:
        file_path = self._get_file_path(file_id)
        url = self._tg_file_url(file_path)
        dest_dir.mkdir(parents=True, exist_ok=True)
        name = Path(file_path).name
        if '.' not in name:
            name = name + '.jpg'
        dest = dest_dir / name
        r = requests.get(url, timeout=self._config.timeout_s)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return dest

    def run(
        self,
        *,
        source: str,
        offset_state_path: Path,
        seen_state_path: Path,
        dry_run: bool,
    ) -> int:
        if not self._config.vk_access_token or not self._config.vk_group_id:
            raise RuntimeError("VK_ACCESS_TOKEN and VK_GROUP_ID are required for tg-sync -> vk")
        vk = VkPublisher(
            access_token=self._config.vk_access_token,
            group_id=self._config.vk_group_id,
            user_access_token=self._config.vk_user_access_token,
        )
        max_pub = (
            MaxGatewayPublisher(token=self._config.max_api_token, base_url=self._config.max_api_base)
            if self._config.max_api_token and self._config.max_chat_id
            else None
        )

        offset_state = self._load_json(offset_state_path, {"offset": 0})
        offset = int(offset_state.get("offset") or 0)
        seen_state = self._load_json(seen_state_path, {"seen": {}})
        seen = seen_state.get("seen") or {}
        pending_albums: dict[str, list[dict]] = seen_state.get("pending_albums") or {}
        if not isinstance(seen, dict):
            seen = {}

        stype, sval = self._extract_source_key(source)

        resp = requests.get(
            self._tg_api("getUpdates"),
            params={"timeout": 0, "offset": offset, "limit": 100},
            timeout=self._config.timeout_s,
        )
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram getUpdates failed: {payload!r}")
        updates = payload.get("result") or []
        if not isinstance(updates, list):
            raise RuntimeError(f"Telegram getUpdates malformed: {payload!r}")

        matched_messages = 0

        # advance offset (only persist when not dry_run)
        max_update_id = None
        for u in updates:
            if isinstance(u, dict) and "update_id" in u:
                uid = int(u["update_id"])
                if max_update_id is None or uid > max_update_id:
                    max_update_id = uid
        if max_update_id is not None:
            offset = max_update_id + 1

        # collect channel posts, group albums by media_group_id
        albums: dict[str, list[dict]] = {}
        singles: list[dict] = []

        for u in updates:
            if not isinstance(u, dict):
                continue
            msg = u.get("channel_post") or u.get("message")
            if not isinstance(msg, dict):
                continue
            chat = msg.get("chat") or {}
            if not isinstance(chat, dict):
                continue

            if stype == "chat_id":
                if int(chat.get("id") or 0) != int(sval):
                    continue
            else:
                username = chat.get("username")
                if not username or str(username).lower() != str(sval).lower():
                    continue

            matched_messages += 1
            mgid = msg.get("media_group_id")
            if mgid:
                albums.setdefault(str(mgid), []).append(msg)
            else:
                singles.append(msg)

        # Объединяем с pending альбомами из прошлого запуска
        for mgid, msgs in pending_albums.items():
            if mgid in albums:
                existing_ids = {m.get("message_id") for m in albums[mgid]}
                for m in msgs:
                    if m.get("message_id") not in existing_ids:
                        albums[mgid].append(m)
            else:
                albums[mgid] = msgs

        def _msg_key(m: dict, mgid: str | None = None) -> str:
            chat = m.get("chat") or {}
            if mgid:
                return f"tg:{chat.get('id')}:album:{mgid}"
            return f"tg:{chat.get('id')}:{m.get('message_id')}"

        # Откладываем альбомы где есть видео но нет фото — ждём следующего запуска
        new_pending: dict[str, list[dict]] = {}
        complete_albums = {}
        now_ts = int(time.time())
        for mgid, msgs in albums.items():
            has_photo = any(self._pick_biggest_photo_file_id(m) for m in msgs)
            has_video = any(self._pick_video_file_id(m) for m in msgs)
            if has_video and not has_photo:
                # Если альбом в pending дольше 10 минут — постим как есть
                msg_ts = int(msgs[0].get("date") or 0)
                if now_ts - msg_ts > 600:
                    complete_albums[mgid] = msgs
                else:
                    new_pending[mgid] = msgs
            else:
                complete_albums[mgid] = msgs
        pending_albums = new_pending

        all_items: list[tuple[list[dict], str | None]] = [
            (msgs, mgid) for mgid, msgs in complete_albums.items()
        ] + [([m], None) for m in singles]
        all_items.sort(key=lambda gi: int((gi[0][0].get("message_id") or 0)))

        processed = 0
        skipped_seen = 0
        for group, mgid in all_items:
            key = _msg_key(group[0], mgid)
            if seen.get(key):
                skipped_seen += 1
                continue

            text = ""
            for m in group:
                if m.get("caption"):
                    text = str(m.get("caption"))
                    break
                if m.get("text"):
                    text = str(m.get("text"))
                    break
            text = self._append_links(self._fix_tg_mentions(text))

            # debug
            for m in group:
                keys = [k for k in m.keys() if k not in ('date','message_id','chat','from','sender_chat')]
                if any(k in m for k in ('video','animation','document')):
                    print(f'[DEBUG] msg keys: {keys}')
            file_ids: list[str] = []
            video_ids: list[str] = []
            for m in group:
                vid = self._pick_video_file_id(m)
                if vid:
                    video_ids.append(vid)
                    continue  # не обрабатываем видео как фото
                fid = self._pick_biggest_photo_file_id(m)
                if fid:
                    file_ids.append(fid)

            if dry_run:
                print(f"[dry-run] tg-sync {source} -> vk: {key} photos={len(file_ids)} videos={len(video_ids)}")
                processed += 1
                continue

            dest_dir = Path(".state/tg_media") / key.replace(":", "_")
            paths: list[Path] = []
            video_paths: list[Path] = []

            if file_ids:
                paths = [self._download_file(fid, dest_dir) for fid in file_ids]

            if video_ids:
                for vid in video_ids:
                    try:
                        vp = self._download_file(vid, dest_dir)
                        if not vp.suffix:
                            vp = vp.rename(vp.with_suffix('.mp4'))
                        video_paths.append(vp)
                    except Exception as e:
                        print(f"[WARN] video download failed, skipping: {e}")

            if paths:
                vk.post_photos(text=text, image_paths=paths)
            video_url: str | None = None
            if video_paths:
                video_url = vk.post_video(text=text, video_path=video_paths[0])
            if not paths and not video_paths and text:
                vk.post_text(text=text)

            if max_pub and self._config.max_chat_id:
                if paths:
                    max_pub.send_photos(chat_id=self._config.max_chat_id, image_paths=paths, text=text)
                if video_paths:
                    max_pub.send_video(chat_id=self._config.max_chat_id, video_path=video_paths[0], text=text if not paths else '', video_url=video_url)
                if not paths and not video_paths and text:
                    max_pub.send_message(chat_id=self._config.max_chat_id, text=text)

            seen[key] = "posted"
            processed += 1

        if not dry_run:
            self._save_json(offset_state_path, {"offset": offset})
            self._save_json(seen_state_path, {"seen": seen, "pending_albums": pending_albums})

        if processed == 0:
            print(
                f"No new Telegram posts for {source}. "
                f"updates={len(updates)} matched={matched_messages} skipped_seen={skipped_seen}."
            )
            if matched_messages == 0:
                print(
                    "Tip: bots do not backfill history. Publish a new post after adding the bot as admin, "
                    "then run tg-sync again."
                )
        return 0
