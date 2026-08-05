from urllib.parse import parse_qs, urlparse

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
