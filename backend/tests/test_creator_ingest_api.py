import json
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENABLE_COMPUTER_USE"] = "true"
os.environ["COMPUTER_USE_INGEST_TOKEN"] = "api-smoke-ingest-token"

from fastapi.testclient import TestClient

from app.config import get_settings

get_settings.cache_clear()
from app.main import app

runtime_settings = get_settings()
runtime_settings.enable_computer_use = True
runtime_settings.computer_use_ingest_token = "api-smoke-ingest-token"


def test_creator_collector_ingest_end_to_end() -> None:
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={"email": "admin@vidinsight.local", "password": runtime_settings.admin_password})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        created = client.post("/api/v1/accounts", headers=headers, json={"nickname": "Smoke account", "platform_open_id": "smoke-open-id"})
        assert created.status_code == 201
        account_id = created.json()["id"]
        raw = {"data": {"open_id": "smoke-open-id", "follower_count": 1234, "list": [{"item_id": "smoke-item-1", "title": "Smoke video", "statistics": {"play_count": 1000, "digg_count": 88, "comment_count": 12, "share_count": 6, "forward_count": 3, "finish_rate": 42, "follow_rate": 1.5}}]}}
        response = client.post("/api/self-data/ingest", headers={"X-Ingest-Token": "api-smoke-ingest-token"}, json={"account_id": account_id, "kind": "creator", "source": "creator", "source_url": "https://creator.douyin.com/insight", "payload": json.dumps(raw), "captured_at": "2026-08-06T10:00:00Z"})
        assert response.status_code == 200
        assert response.json()["parsed"] == 2
        videos = client.get(f"/api/v1/videos?account_id={account_id}", headers=headers)
        assert videos.status_code == 200
        metric = videos.json()[0]["latest_metrics"]
        assert metric["play_count"] == 1000
        assert metric["completion_rate"] == 0.42
        assert metric["video_follow_conversion"] == 0.015
        rejected = client.post("/api/self-data/ingest", headers={"X-Ingest-Token": "wrong"}, json={"account_id": account_id, "kind": "creator", "source": "creator", "source_url": "https://creator.douyin.com/insight", "payload": "{}", "captured_at": "2026-08-06T10:00:00Z"})
        assert rejected.status_code == 403
