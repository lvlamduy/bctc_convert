from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/scan_exchange_rate_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_exchange_rate_full_document_vietocr_v1_test_target", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _axis(semantic_axis_sha256: str) -> dict[str, object]:
    return {
        "documents": [
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "pages": [],
                "source_pdf": {"sha256": f"{ordinal:064x}"},
            }
            for ordinal, code in enumerate(scanner.EXPECTED_DOCUMENT_ORDER, 1)
        ],
        "projection_id": "fdvaav1:projection:" + "1" * 64,
        "semantic_axis_sha256": semantic_axis_sha256,
    }


def _matcher_result() -> dict[str, object]:
    return {
        "format_version": scanner.MATCHER_FORMAT,
        "metrics": {
            "complete_region_count": 0,
            "complete_source_row_count": 0,
            "near_region_count": 0,
            "supported_schema_row_count": 0,
        },
        "uniqueness": {"status": "NO_UNIQUE_FULL_MATCH"},
    }


def test_scan_binds_the_registered_input_axis_without_one_corpus_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    annual_axis_sha256 = "a" * 64
    monkeypatch.setattr(
        scanner,
        "project_full_document_vietocr_accounting_axis_v1",
        lambda _value: _axis(annual_axis_sha256),
    )
    monkeypatch.setattr(
        scanner,
        "_load_matcher",
        lambda: SimpleNamespace(
            build_exchange_rate_variant_graph_document_v1=lambda _pages: _matcher_result()
        ),
    )

    result = scanner.build_exchange_rate_full_document_scan_v1({})

    assert result["input_semantic_axis_sha256"] == annual_axis_sha256
    assert result["metrics"]["document_count"] == 8
    forged = copy.deepcopy(result)
    forged["input_semantic_axis_sha256"] = "b" * 64
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "erfdsv1:scan:" + scanner.canonical_json_sha256_v1(material)
    with pytest.raises(scanner.ExchangeRateFullDocumentScanV1Error, match="replay exactly"):
        scanner.validate_exchange_rate_full_document_scan_replay_v1(forged, {})


def test_live_index_reader_rejects_duplicate_keys_and_leaf_symlinks(tmp_path: Path) -> None:
    regular = tmp_path / "index.json"
    regular.write_text('{"a":1}', encoding="utf-8")
    assert scanner._stable_json(regular) == {"a": 1}

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(scanner.ExchangeRateFullDocumentScanV1Error, match="strict UTF-8 JSON"):
        scanner._stable_json(duplicate)

    symlink = tmp_path / "linked.json"
    symlink.symlink_to(regular)
    with pytest.raises(scanner.ExchangeRateFullDocumentScanV1Error, match="nofollow"):
        scanner._stable_json(symlink)
