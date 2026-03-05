from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import load_config
from .scheduler import select_due
from .storage import load_posts, serialize_post
from .state import load_state, mark_posted, save_state
from .tg_sync import TgSync, TgSyncConfig
from .publishers import (
    InstagramGraphPublisher,
    MaxGatewayPublisher,
    TelegramPublisher,
    VkPublisher,
    WebhookPublisher,
)

def _render_links_text(links) -> str:
    if not links:
        return ""
    lines = ["", "Ссылки:"]
    for link in links:
        label = getattr(link, "label", None)
        url = getattr(link, "url", None)
        if label and url:
            lines.append(f"- {label}: {url}")
    return "\n".join(lines) if len(lines) > 2 else ""


def _telegram_keyboard(links):
    if not links:
        return None
    buttons = []
    for link in links:
        label = getattr(link, "label", None)
        url = getattr(link, "url", None)
        if label and url:
            buttons.append({"text": str(label), "url": str(url)})
    if not buttons:
        return None
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return {"inline_keyboard": rows}


def _target_key(target_type: str, *, chat_id: str | None = None, url: str | None = None) -> str:
    if target_type == "telegram":
        return f"telegram:{chat_id or ''}"
    if target_type == "webhook":
        return f"webhook:{url or ''}"
    if target_type == "vk":
        return "vk"
    if target_type == "instagram":
        return "instagram"
    if target_type == "max":
        return f"max:{chat_id or ''}"
    return target_type


def _run(posts_dir: Path, *, dry_run: bool, state_path: Path | None) -> int:
    config = load_config()
    posts = load_posts(posts_dir)
    now = datetime.now(timezone.utc)
    due = select_due(posts, now=now)

    if due.skipped_future:
        print(f"Skipped (future publish_at): {len(due.skipped_future)}")
    print(f"Due: {len(due.due)}")

    telegram = TelegramPublisher(config.telegram_bot_token) if config.telegram_bot_token else None
    webhook = WebhookPublisher()
    vk = (
        VkPublisher(config.vk_access_token, config.vk_group_id)
        if config.vk_access_token and config.vk_group_id
        else None
    )
    ig = (
        InstagramGraphPublisher(
            access_token=config.ig_access_token,
            ig_user_id=config.ig_user_id,
            api_version=config.ig_graph_version,
        )
        if config.ig_access_token and config.ig_user_id
        else None
    )
    max_gateway = (
        MaxGatewayPublisher(token=config.max_api_token, base_url=config.max_api_base)
        if config.max_api_token
        else None
    )

    base_dir = Path(__file__).resolve().parents[1]
    state = load_state(state_path) if state_path else None

    for post in due.due:
        text_with_links = post.text + _render_links_text(post.links)
        for target in post.targets:
            if target.type == "telegram":
                if not target.chat_id:
                    raise ValueError(f"post {post.id}: telegram target requires chat_id")
                tkey = _target_key("telegram", chat_id=target.chat_id)
                if state is not None and post.id in state.posted and tkey in state.posted[post.id]:
                    print(f"Skip (already posted): {post.id} -> {tkey}")
                    continue
                if dry_run:
                    print(f"[dry-run] telegram -> {target.chat_id}: {post.id}")
                    continue
                if telegram is None:
                    raise RuntimeError("TELEGRAM_BOT_TOKEN is required for telegram targets")
                keyboard = _telegram_keyboard(post.links)
                images = post.images or ([post.image] if post.image else None)
                if images:
                    image_paths = [(base_dir / p).resolve() for p in images]
                    for p in image_paths:
                        if not p.exists():
                            raise FileNotFoundError(f"post {post.id}: image not found: {p}")
                    if len(image_paths) == 1:
                        telegram.send_photo(
                            chat_id=target.chat_id,
                            image_path=image_paths[0],
                            caption=text_with_links,
                            parse_mode=target.parse_mode,
                            reply_markup=keyboard,
                        )
                    else:
                        telegram.send_media_group(
                            chat_id=target.chat_id,
                            image_paths=image_paths,
                            caption=text_with_links,
                            parse_mode=target.parse_mode,
                        )
                        if keyboard:
                            telegram.send_message(
                                chat_id=target.chat_id,
                                text="Открыть ссылки:",
                                reply_markup=keyboard,
                            )
                else:
                    telegram.send_message(
                        chat_id=target.chat_id,
                        text=text_with_links,
                        parse_mode=target.parse_mode,
                        reply_markup=keyboard,
                    )
                if state is not None:
                    state = mark_posted(state, post_id=post.id, target_key=tkey)
                continue

            if target.type == "webhook":
                url = target.url or config.webhook_default_url
                tkey = _target_key("webhook", url=url)
                if state is not None and post.id in state.posted and tkey in state.posted[post.id]:
                    print(f"Skip (already posted): {post.id} -> {tkey}")
                    continue
                payload = {"post": serialize_post(post), "target": {"type": "webhook"}}
                if dry_run:
                    print(f"[dry-run] webhook -> {url or '<missing url>'}: {post.id}")
                    continue
                if not url:
                    raise RuntimeError("webhook target requires url (or WEBHOOK_DEFAULT_URL)")
                if post.image:
                    image_path = (base_dir / post.image).resolve()
                    if not image_path.exists():
                        raise FileNotFoundError(f"post {post.id}: image not found: {image_path}")
                    webhook.post_multipart(url=url, payload=payload, file_path=image_path, headers=target.headers)
                else:
                    webhook.post_json(url=url, payload=payload, headers=target.headers)
                if state is not None:
                    state = mark_posted(state, post_id=post.id, target_key=tkey)
                continue

            if target.type == "vk":
                tkey = _target_key("vk")
                if state is not None and post.id in state.posted and tkey in state.posted[post.id]:
                    print(f"Skip (already posted): {post.id} -> {tkey}")
                    continue
                if dry_run:
                    print(f"[dry-run] vk -> group {config.vk_group_id or '<missing VK_GROUP_ID>'}: {post.id}")
                    continue
                if vk is None:
                    raise RuntimeError("VK_ACCESS_TOKEN and VK_GROUP_ID are required for vk targets")
                images = post.images or ([post.image] if post.image else None)
                if images:
                    image_paths = [(base_dir / p).resolve() for p in images]
                    for p in image_paths:
                        if not p.exists():
                            raise FileNotFoundError(f"post {post.id}: image not found: {p}")
                    if len(image_paths) == 1:
                        vk.post_photo(text=text_with_links, image_path=image_paths[0])
                    else:
                        vk.post_photos(text=text_with_links, image_paths=image_paths)
                else:
                    vk.post_text(text=text_with_links)
                if state is not None:
                    state = mark_posted(state, post_id=post.id, target_key=tkey)
                continue

            if target.type == "instagram":
                tkey = _target_key("instagram")
                if state is not None and post.id in state.posted and tkey in state.posted[post.id]:
                    print(f"Skip (already posted): {post.id} -> {tkey}")
                    continue
                if dry_run:
                    print(f"[dry-run] instagram -> ig_user {config.ig_user_id or '<missing IG_USER_ID>'}: {post.id}")
                    continue
                if ig is None:
                    raise RuntimeError("IG_ACCESS_TOKEN and IG_USER_ID are required for instagram targets")
                image_urls = post.image_urls or ([post.image_url] if post.image_url else None)
                if not image_urls:
                    raise RuntimeError(
                        f"post {post.id}: instagram requires image_url (public URL); "
                        "Instagram feed posts cannot be text-only"
                    )
                ig.publish_photos(image_urls=image_urls, caption=text_with_links)
                if state is not None:
                    state = mark_posted(state, post_id=post.id, target_key=tkey)
                continue

            if target.type == "max":
                if not target.chat_id:
                    raise ValueError(f"post {post.id}: max target requires chat_id")
                tkey = _target_key("max", chat_id=target.chat_id)
                if state is not None and post.id in state.posted and tkey in state.posted[post.id]:
                    print(f"Skip (already posted): {post.id} -> {tkey}")
                    continue
                if dry_run:
                    print(f"[dry-run] max -> {target.chat_id}: {post.id}")
                    continue
                if max_gateway is None:
                    raise RuntimeError("MAX_API_TOKEN is required for max targets")
                if post.image_url:
                    max_gateway.send_file_url(chat_id=target.chat_id, file_url=post.image_url, caption=post.text)
                else:
                    max_gateway.send_message(chat_id=target.chat_id, text=post.text)
                if state is not None:
                    state = mark_posted(state, post_id=post.id, target_key=tkey)
                continue

            raise ValueError(f"post {post.id}: unknown target type: {target.type}")

    if not dry_run and state_path and state is not None:
        save_state(state_path, state)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="omniposter")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Publish due posts from a folder")
    run.add_argument("--posts", default="./posts", help="Folder with *.json posts")
    run.add_argument("--dry-run", action="store_true", help="Do not send, only print actions")
    run.add_argument(
        "--state",
        default="./.state/state.json",
        help="Path to state file (set to empty string to disable state)",
    )

    tg = sub.add_parser("tg-sync", help="Sync Telegram channel posts -> other targets (start with VK)")
    tg.add_argument(
        "--source",
        required=True,
        help="Telegram source channel username (e.g. @MY_Avto5) or numeric chat_id",
    )
    tg.add_argument(
        "--offset-state",
        default="./.state/tg_offset.json",
        help="Path to Telegram offset state (per source recommended)",
    )
    tg.add_argument(
        "--seen-state",
        default="./.state/tg_seen.json",
        help="Path to Telegram seen/posted state (per source recommended)",
    )
    tg.add_argument(
        "--links-file",
        default="secrets/tg_links.json",
        help="JSON file with links to append when reposting to VK",
    )
    tg.add_argument("--dry-run", action="store_true", help="Do not send, only print actions")

    args = parser.parse_args(argv)
    if args.cmd == "run":
        state_path = Path(args.state) if str(args.state).strip() else None
        return _run(Path(args.posts), dry_run=bool(args.dry_run), state_path=state_path)
    if args.cmd == "tg-sync":
        config = load_config()
        sync = TgSync(
            config=TgSyncConfig(
                telegram_bot_token=config.telegram_bot_token,
                vk_access_token=config.vk_access_token,
                vk_group_id=config.vk_group_id,
                links_file=str(args.links_file).strip() or None,
            )
        )
        return sync.run(
            source=str(args.source),
            offset_state_path=Path(args.offset_state),
            seen_state_path=Path(args.seen_state),
            dry_run=bool(args.dry_run),
        )
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
