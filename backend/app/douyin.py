"""Official Douyin OAuth helpers for website applications."""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet

from app.config import get_settings

AUTHORIZE_URL = "https://open.douyin.com/platform/oauth/connect/"
TOKEN_URL = "https://open.douyin.com/oauth/access_token/"
REFRESH_URL = "https://open.douyin.com/oauth/refresh_token/"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def cipher() -> Fernet:
    raw_key = hashlib.sha256(get_settings().token_encryption_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw_key))


def encrypt(value: str) -> str:
    return cipher().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return cipher().decrypt(value.encode()).decode()


def new_state() -> str:
    return secrets.token_urlsafe(32)


def state_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def authorization_url(state: str) -> str:
    settings = get_settings()
    if not settings.douyin_client_key or not settings.douyin_redirect_uri:
        raise RuntimeError("DOUYIN_CLIENT_KEY and DOUYIN_REDIRECT_URI must be configured")
    query = urlencode({"client_key": settings.douyin_client_key, "response_type": "code", "scope": ",".join(settings.douyin_scope_list), "redirect_uri": settings.douyin_redirect_uri, "state": state})
    return f"{AUTHORIZE_URL}?{query}"


async def exchange_code(code: str) -> dict:
    settings = get_settings()
    if not settings.douyin_client_key or not settings.douyin_client_secret:
        raise RuntimeError("DOUYIN_CLIENT_KEY and DOUYIN_CLIENT_SECRET must be configured")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(TOKEN_URL, data={"client_key": settings.douyin_client_key, "client_secret": settings.douyin_client_secret, "code": code, "grant_type": "authorization_code"})
        response.raise_for_status()
    payload = response.json().get("data", {})
    if payload.get("error_code", 0) != 0 or not payload.get("access_token") or not payload.get("open_id"):
        raise ValueError("Douyin did not return a usable access token")
    return payload


async def refresh_access_token(refresh_token: str) -> dict:
    settings = get_settings()
    if not settings.douyin_client_key:
        raise RuntimeError("DOUYIN_CLIENT_KEY must be configured")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(REFRESH_URL, data={"client_key": settings.douyin_client_key, "grant_type": "refresh_token", "refresh_token": refresh_token})
        response.raise_for_status()
    payload = response.json().get("data", {})
    if payload.get("error_code", 0) != 0 or not payload.get("access_token"):
        raise ValueError("Douyin did not return a refreshed access token")
    return payload


def expiration(seconds: int | str | None) -> datetime | None:
    return utcnow() + timedelta(seconds=int(seconds)) if seconds else None
