from __future__ import annotations

import pytest

from bctc_ai.core.contracts import DatasetRole
from bctc_ai.ingestion.dataset_roles import DatasetRoleConflict, assign_dataset_role
from bctc_ai.storage.content_store import materialize_immutable


def test_content_store_is_hash_addressed_read_only_and_idempotent(tmp_path):
    source = tmp_path / "input.pdf"
    source.write_bytes(b"%PDF-1.4\nsource evidence\n%%EOF\n")
    first, digest = materialize_immutable(source, tmp_path / "immutable")
    second, second_digest = materialize_immutable(source, tmp_path / "immutable")
    assert first == second
    assert digest == second_digest
    assert first.read_bytes() == source.read_bytes()
    assert first.stat().st_mode & 0o222 == 0


def test_dataset_role_cannot_be_relabelled_as_untouched(tmp_path):
    registry = tmp_path / "dataset_roles.jsonl"
    assign_dataset_role(
        registry,
        document_id="sha256:abc",
        role=DatasetRole.LOGIC_DEVELOPMENT,
        source_path="source.pdf",
    )
    with pytest.raises(DatasetRoleConflict):
        assign_dataset_role(
            registry,
            document_id="sha256:abc",
            role=DatasetRole.UNTOUCHED_HOLDOUT,
            source_path="source.pdf",
        )
