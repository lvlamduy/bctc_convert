from __future__ import annotations

import pytest

from bctc_ai.ingestion.discovery import DiscoveredSource
from bctc_ai.ingestion.registry import SourceRegistryConflict, register_sources


def _source(path) -> DiscoveredSource:
    return DiscoveredSource(path=path, kind="PDF", bank="TEST", year=2026)


def test_source_registration_is_idempotent_and_preserves_first_seen_time(tmp_path):
    source = tmp_path / "input.pdf"
    source.write_bytes(b"%PDF-1.4\nimmutable\n%%EOF\n")
    registry = tmp_path / "registry.jsonl"

    first, first_hash = register_sources([_source(source)], tmp_path, registry)
    first_bytes = registry.read_bytes()
    second, second_hash = register_sources([_source(source)], tmp_path, registry)

    assert second_hash == first_hash
    assert second[0].registered_at == first[0].registered_at
    assert registry.read_bytes() == first_bytes


def test_source_registration_rejects_changed_content_at_registered_path(tmp_path):
    source = tmp_path / "input.pdf"
    source.write_bytes(b"%PDF-1.4\nfirst\n%%EOF\n")
    registry = tmp_path / "registry.jsonl"
    register_sources([_source(source)], tmp_path, registry)
    source.write_bytes(b"%PDF-1.4\nchanged\n%%EOF\n")

    with pytest.raises(SourceRegistryConflict, match="content changed"):
        register_sources([_source(source)], tmp_path, registry)


def test_source_registration_rejects_disappearing_registered_path(tmp_path):
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    first.write_bytes(b"%PDF-1.4\nfirst\n%%EOF\n")
    second.write_bytes(b"%PDF-1.4\nsecond\n%%EOF\n")
    registry = tmp_path / "registry.jsonl"
    register_sources([_source(first), _source(second)], tmp_path, registry)

    with pytest.raises(SourceRegistryConflict, match="disappeared"):
        register_sources([_source(first)], tmp_path, registry)
