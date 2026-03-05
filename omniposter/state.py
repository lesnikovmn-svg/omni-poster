from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class State:
    posted: dict[str, dict[str, str]]


def load_state(path: Path) -> State:
    if not path.exists():
        return State(posted={})
    raw = json.loads(path.read_text(encoding="utf-8"))
    posted = raw.get("posted", {})
    if not isinstance(posted, dict):
        raise ValueError("invalid state file: posted must be an object")
    normalized: dict[str, dict[str, str]] = {}
    for post_id, targets in posted.items():
        if not isinstance(targets, dict):
            continue
        normalized[str(post_id)] = {str(k): str(v) for k, v in targets.items()}
    return State(posted=normalized)


def mark_posted(state: State, *, post_id: str, target_key: str, when: datetime | None = None) -> State:
    if when is None:
        when = datetime.now(timezone.utc)
    when_s = when.astimezone(timezone.utc).isoformat()
    posted = {k: dict(v) for k, v in state.posted.items()}
    posted.setdefault(post_id, {})[target_key] = when_s
    return State(posted=posted)


def save_state(path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"posted": state.posted}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

