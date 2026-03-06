from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class VkOAuthResult:
    access_token: str
    user_id: int | None
    expires_in: int | None


def exchange_code_for_token(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    timeout_s: int = 30,
) -> VkOAuthResult:
    resp = requests.get(
        "https://oauth.vk.com/access_token",
        params={
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
        },
        timeout=timeout_s,
    )
    resp.raise_for_status()
    payload = resp.json()
    if "error" in payload:
        raise RuntimeError(f"VK access_token exchange failed: {payload!r}")
    token = payload.get("access_token")
    if not token:
        raise RuntimeError(f"VK access_token exchange missing access_token: {payload!r}")
    user_id = payload.get("user_id")
    expires_in = payload.get("expires_in")
    return VkOAuthResult(
        access_token=str(token),
        user_id=int(user_id) if user_id is not None else None,
        expires_in=int(expires_in) if expires_in is not None else None,
    )

