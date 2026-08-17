from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/scan_provision_movement_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_provision_movement_full_document_vietocr_v1", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _page() -> dict[str, object]:
    surfaces = [
        ("Biến động dự phòng rủi ro cho vay khách hàng", 0, 0),
        ("Dự phòng chung", 0, 35),
        ("Số dư đầu kỳ", 0, 80),
        ("100", 650, 80),
        ("Trích lập dự phòng trong kỳ", 0, 125),
        ("20", 650, 125),
        ("Sử dụng dự phòng để xử lý các khoản nợ", 0, 170),
        ("(10)", 650, 170),
        ("Số dư cuối kỳ", 0, 215),
        ("110", 650, 215),
    ]
    return {
        "lines": [
            {
                "bbox": [x, y, x + 140, y + 22],
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
            for index, (text, x, y) in enumerate(surfaces)
        ],
        "page_sequence": 1,
        "primary_numeric_authority": False,
    }


def _axis() -> dict[str, object]:
    return {
        "documents": [
            {
                "document_ordinal": ordinal,
                "document_provenance": code,
                "pages": [_page()],
                "source_pdf": {
                    "path": f"corpus/{code}/report.pdf",
                    "sha256": f"{ordinal:064x}",
                    "size_bytes": ordinal,
                },
            }
            for ordinal, code in enumerate(scanner.EXPECTED_DOCUMENT_ORDER, 1)
        ],
        "projection_id": "fdvaav1:projection:" + "1" * 64,
        "semantic_axis_sha256": "2" * 64,
    }


def test_one_bank_blind_matcher_scans_all_eight_complete_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )

    result = scanner.build_provision_movement_full_document_scan_v1({"opaque": "upstream"})

    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        scanner.EXPECTED_DOCUMENT_ORDER
    )
    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "accounting_corroborated_semantic_lane_count": 8,
        "continuation_region_count": 0,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "movement_panel_count": 8,
        "near_region_count": 0,
        "provision_region_count": 8,
        "unresolved_document_count": 0,
    }
    assert result["authority"]["bank_identity_used_for_matching_or_routing"] is False


def test_exact_replay_rejects_coordinated_match_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )
    result = scanner.build_provision_movement_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["graphs"][0]["panels"][0]["rows"][0]["role"] = "OTHER"
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "pmfdsv1:scan:" + scanner.canonical_json_sha256_v1(material)

    with pytest.raises(scanner.ProvisionMovementFullDocumentScanV1Error, match="replay exactly"):
        scanner.validate_provision_movement_full_document_scan_replay_v1(forged, {})


def test_provenance_relabel_and_bool_as_int_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    axis = _axis()
    axis["documents"][0]["document_provenance"] = "MBB"
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )
    with pytest.raises(scanner.ProvisionMovementFullDocumentScanV1Error, match="trial identity"):
        scanner.build_provision_movement_full_document_scan_v1({})

    clean_axis = _axis()
    clean_axis["documents"][0]["pages"][0]["primary_numeric_authority"] = 0
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: clean_axis
    )
    with pytest.raises(Exception, match="exact bool"):
        scanner.build_provision_movement_full_document_scan_v1({})


def test_current_eight_pdf_scan_locks_unique_regions_and_continuation() -> None:
    semantic_index = json.loads((scanner.PROJECT_ROOT / scanner.DEFAULT_INPUT).read_text("utf-8"))

    result = scanner.build_provision_movement_full_document_scan_v1(semantic_index)

    assert result["scan_id"] == (
        "pmfdsv1:scan:61e30d784dd91ec666d6db7e46833c9a3493d51c4451ab11b97ae7771b2b9e5a"
    )
    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "accounting_corroborated_semantic_lane_count": 3,
        "continuation_region_count": 1,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "movement_panel_count": 16,
        "near_region_count": 11,
        "provision_region_count": 8,
        "unresolved_document_count": 0,
    }
    assert [
        trial["matcher_result"]["graphs"][0]["page_sequences"] for trial in result["trials"]
    ] == [[18], [34], [45], [28], [31], [39], [23], [34, 35]]


def test_annual_2025_extended_variants_find_one_region_in_every_pdf() -> None:
    semantic_index = json.loads(
        (
            scanner.PROJECT_ROOT / "output/calibration/annual-2025-8bank-full-document-vietocr-v1/"
            "verified-index/semantic_index.json"
        ).read_text("utf-8")
    )

    result = scanner.build_provision_movement_full_document_scan_v1(
        semantic_index,
        enable_extended_reporting_period_variants=True,
    )

    assert result["scan_id"] == (
        "pmfdsv1:scan:89af751681a703ee5f93c7fb1381fbb3bda6c97a75a3e17e997173f27e9b862c"
    )
    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "accounting_corroborated_semantic_lane_count": 5,
        "continuation_region_count": 0,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "movement_panel_count": 16,
        "near_region_count": 15,
        "provision_region_count": 8,
        "unresolved_document_count": 0,
    }
    assert [
        trial["matcher_result"]["graphs"][0]["page_sequences"] for trial in result["trials"]
    ] == [[51], [53], [48], [38], [41], [44], [43], [39]]
