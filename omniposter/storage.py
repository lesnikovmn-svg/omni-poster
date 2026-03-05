from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .models import Post, Target


def _parse_datetime(value: str) -> datetime:
    # Accepts ISO-8601 like: 2026-03-05T12:00:00+03:00
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("publish_at must include timezone offset, e.g. +03:00")
    return parsed


def load_posts(posts_dir: Path) -> list[Post]:
    if not posts_dir.exists():
        raise FileNotFoundError(f"posts dir not found: {posts_dir}")

    posts: list[Post] = []
    for path in sorted(posts_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        post_id = str(raw["id"])
        text = str(raw["text"])
        publish_at = raw.get("publish_at")
        image = raw.get("image")
        image_url = raw.get("image_url")
        targets_raw = raw.get("targets", [])
        if not isinstance(targets_raw, list) or not targets_raw:
            raise ValueError(f"{path}: targets must be a non-empty array")

        targets: list[Target] = []
        for t in targets_raw:
            if not isinstance(t, dict) or "type" not in t:
                raise ValueError(f"{path}: invalid target: {t!r}")
            targets.append(
                Target(
                    type=str(t["type"]),
                    chat_id=(str(t["chat_id"]) if "chat_id" in t and t["chat_id"] is not None else None),
                    parse_mode=(str(t["parse_mode"]) if "parse_mode" in t and t["parse_mode"] is not None else None),
                    url=(str(t["url"]) if "url" in t and t["url"] is not None else None),
                    headers=(dict(t["headers"]) if isinstance(t.get("headers"), dict) else None),
                )
            )

        posts.append(
            Post(
                id=post_id,
                text=text,
                targets=targets,
                publish_at=_parse_datetime(str(publish_at)) if publish_at else None,
                image=str(image) if image else None,
                image_url=str(image_url) if image_url else None,
            )
        )
    return posts


def serialize_post(post: Post) -> dict:
    data = asdict(post)
    if post.publish_at is not None:
        data["publish_at"] = post.publish_at.isoformat()
    return data
