from app.creator_ingest import _number, _rate


def test_creator_numeric_normalisation() -> None:
    assert _number("12.9") == 12
    assert _number(-1) == 0
    assert _number("not-a-number") is None


def test_creator_rate_normalisation() -> None:
    assert _rate("42") == 0.42
    assert _rate(0.42) == 0.42
    assert _rate(101) is None
