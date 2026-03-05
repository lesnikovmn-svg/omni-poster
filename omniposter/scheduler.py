from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import Post


@dataclass(frozen=True)
class DueResult:
    due: list[Post]
    skipped_future: list[Post]


def select_due(posts: list[Post], now: datetime | None = None) -> DueResult:
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    due: list[Post] = []
    skipped_future: list[Post] = []
    for post in posts:
        if post.publish_at is None:
            due.append(post)
            continue
        if post.publish_at <= now.astimezone(post.publish_at.tzinfo):
            due.append(post)
        else:
            skipped_future.append(post)

    return DueResult(due=due, skipped_future=skipped_future)

