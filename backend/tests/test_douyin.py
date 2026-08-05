from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from app import douyin
from app.douyin import decrypt, encrypt, new_state, state_hash


def test_tokens_are_encrypted_and_round_trip() -> None:
    token = "act.secret-token"
    encrypted = encrypt(token)
    assert token not in encrypted
    assert decrypt(encrypted) == token


def test_oauth_state_is_random_and_hashable() -> None:
    first, second = new_state(), new_state()
    assert first != second
    assert len(state_hash(first)) == 64


def test_authorization_url_uses_official_oauth_parameters(monkeypatch) -> None:
    monkeypatch.setattr(douyin, "get_settings", lambda: SimpleNamespace(douyin_client_key="client-key", douyin_redirect_uri="https://app.example/callback", douyin_scope_list=["user_info", "video.data"]))
    query = parse_qs(urlparse(douyin.authorization_url("state-value")).query)
    assert query == {"client_key": ["client-key"], "response_type": ["code"], "scope": ["user_info,video.data"], "redirect_uri": ["https://app.example/callback"], "state": ["state-value"]}
