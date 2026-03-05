from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Target:
    type: str
    chat_id: str | None = None
    parse_mode: str | None = None
    url: str | None = None
    headers: dict[str, str] | None = None


@dataclass(frozen=True)
class Link:
    label: str
    url: str


@dataclass(frozen=True)
class Post:
    id: str
    text: str
    targets: list[Target]
    publish_at: datetime | None = None
    image: str | None = None  # legacy single local image
    image_url: str | None = None  # legacy single public image URL
    images: list[str] | None = None  # local image paths
    image_urls: list[str] | None = None  # public image URLs
    links: list[Link] | None = None
