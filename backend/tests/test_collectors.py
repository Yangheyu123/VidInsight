from types import SimpleNamespace

import pytest

from app.collectors import _force_payload_source, _validated_base_url


def test_contract_payload_provenance_is_server_controlled() -> None:
    payload = {
        "account_snapshot": {"source": "authorized_import"},
        "videos": [{"source": "authorized_import"}, {"platform_item_id": "item-2"}],
    }
    _force_payload_source(payload, "computer_use")
    assert payload["account_snapshot"]["source"] == "computer_use"
    assert [item["source"] for item in payload["videos"]] == ["computer_use", "computer_use"]


def test_source_requires_https() -> None:
    settings = SimpleNamespace(crawler_domain_list=[])
    with pytest.raises(ValueError, match="HTTPS"):
        _validated_base_url("http://provider.example", settings)


def test_crawler_source_requires_explicit_allowlist() -> None:
    settings = SimpleNamespace(crawler_domain_list=["approved.example"])
    assert _validated_base_url("https://approved.example/worker", settings, require_crawler_allowlist=True) == "https://approved.example/worker"
    with pytest.raises(ValueError, match="ALLOWED_DOMAINS"):
        _validated_base_url("https://other.example/worker", settings, require_crawler_allowlist=True)
