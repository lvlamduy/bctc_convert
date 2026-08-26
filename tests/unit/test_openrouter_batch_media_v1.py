from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bctc_ai.evaluation import openrouter_batch_media_v1 as target


def test_presigned_media_is_content_addressed_and_public_receipt_omits_url(
    monkeypatch, tmp_path: Path
) -> None:
    payload = b"png-image"
    captured = {}
    settings = SimpleNamespace(
        bucket="bucket",
        prefix="prefix",
        content_prefix="objects/sha256",
        profile="profile",
        region="region",
    )

    class FakeAws:
        def __init__(self, value):
            assert value is settings

        def preflight(self):
            return {}

        def put_content(self, path, *, key, digest):
            captured["payload"] = path.read_bytes()
            captured["key"] = key
            return SimpleNamespace(disposition="UPLOADED")

    monkeypatch.setattr(target, "load_settings", lambda path: settings)
    monkeypatch.setattr(target, "AwsCli", FakeAws)
    monkeypatch.setattr(
        target,
        "_presign",
        lambda **kwargs: (
            "https://bucket.s3.example/prefix/objects/sha256/4c/"
            "4c21065a5135366eef72e22c4b8ea8d55e98d379f2e64a224099a3cb3ad95d40"
            "?X-Amz-Credential=credential&X-Amz-Signature=signature"
        ),
    )
    result = target.materialize_openrouter_batch_media_v1(
        payload=payload, media_type="image/png", s3_config_path=tmp_path / "s3.toml"
    )
    assert captured["payload"] == payload
    assert captured["key"].endswith(result.payload_sha256)
    receipt = result.public_receipt()
    assert "url" not in receipt
    assert receipt["url_sha256"] == result.url_sha256
