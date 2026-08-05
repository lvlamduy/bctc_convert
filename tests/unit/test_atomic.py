from __future__ import annotations

import json

from bctc_ai.core.atomic import atomic_write_json, atomic_write_text
from bctc_ai.core.hashing import sha256_bytes, sha256_file


def test_atomic_text_write_is_hash_verified(tmp_path):
    path = tmp_path / "nested" / "artifact.txt"
    digest = atomic_write_text(path, "bằng chứng\n")
    assert path.read_text(encoding="utf-8") == "bằng chứng\n"
    assert digest == sha256_file(path) == sha256_bytes("bằng chứng\n".encode())
    assert not list(path.parent.glob(f".{path.name}.*"))


def test_atomic_json_has_stable_key_order(tmp_path):
    path = tmp_path / "manifest.json"
    atomic_write_json(path, {"z": 1, "a": 2})
    assert list(json.loads(path.read_text()).keys()) == ["a", "z"]
