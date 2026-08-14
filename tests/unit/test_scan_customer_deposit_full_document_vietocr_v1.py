from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/scan_customer_deposit_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_customer_deposit_full_document_vietocr_v1", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _page() -> dict[str, object]:
    surfaces = [
        ("Tiền gửi của khách hàng", 0, 0),
        ("30/06/2026", 650, 25),
        ("31/12/2025", 820, 25),
        ("Tiền gửi không kỳ hạn", 0, 60),
        ("100", 650, 60),
        ("Tiền gửi có kỳ hạn", 0, 100),
        ("200", 650, 100),
        ("Tiền ký quỹ", 0, 140),
        ("30", 650, 140),
        ("Tiền gửi vốn chuyên dùng", 0, 180),
        ("40", 650, 180),
    ]
    return {
        "lines": [
            {
                "bbox": [x, y, x + 130, y + 20],
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

    result = scanner.build_customer_deposit_full_document_scan_v1({"opaque": "upstream"})

    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        scanner.EXPECTED_DOCUMENT_ORDER
    )
    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "complete_panel_count": 8,
        "continuation_region_count": 0,
        "customer_deposit_region_count": 8,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 0,
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
    result = scanner.build_customer_deposit_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["regions"][0]["cluster_boundary"]["last_parent_role"] = (
        "TERM"
    )
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "cdfdsv1:scan:" + scanner.canonical_json_sha256_v1(material)

    with pytest.raises(scanner.CustomerDepositFullDocumentScanV1Error, match="replay exactly"):
        scanner.validate_customer_deposit_full_document_scan_replay_v1(forged, {})


def test_provenance_relabel_and_bool_as_int_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    axis["documents"][0]["document_provenance"] = "MBB"
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )
    with pytest.raises(scanner.CustomerDepositFullDocumentScanV1Error, match="trial identity"):
        scanner.build_customer_deposit_full_document_scan_v1({})

    clean_axis = _axis()
    clean_axis["documents"][0]["pages"][0]["primary_numeric_authority"] = 0
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: clean_axis
    )
    with pytest.raises(Exception, match="exact bool"):
        scanner.build_customer_deposit_full_document_scan_v1({})


def test_current_eight_pdf_scan_locks_unique_boundaries_and_continuation() -> None:
    semantic_index = json.loads((scanner.PROJECT_ROOT / scanner.DEFAULT_INPUT).read_text("utf-8"))

    result = scanner.build_customer_deposit_full_document_scan_v1(semantic_index)

    assert result["scan_id"] == (
        "cdfdsv1:scan:31a5c2f86cdcc4a30cd6b45c8974edb09ba0ce305dfdc7a8eb7ab74664c4094e"
    )
    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "complete_panel_count": 9,
        "continuation_region_count": 1,
        "customer_deposit_region_count": 8,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 35,
        "unresolved_document_count": 0,
    }
    assert [
        trial["matcher_result"]["regions"][0]["page_sequences"] for trial in result["trials"]
    ] == [[21], [43], [55], [31], [35], [42], [25], [41, 42]]
    assert [
        trial["matcher_result"]["regions"][0]["cluster_boundary"] for trial in result["trials"]
    ] == [
        {
            "first_page_sequence": 21,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 13,
            "last_page_sequence": 21,
            "last_parent_role": "DEDICATED",
            "last_source_line_index": 67,
        },
        {
            "first_page_sequence": 43,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 6,
            "last_page_sequence": 43,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 27,
        },
        {
            "first_page_sequence": 55,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 12,
            "last_page_sequence": 55,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 45,
        },
        {
            "first_page_sequence": 31,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 33,
            "last_page_sequence": 31,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 54,
        },
        {
            "first_page_sequence": 35,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 14,
            "last_page_sequence": 35,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 35,
        },
        {
            "first_page_sequence": 42,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 9,
            "last_page_sequence": 42,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 36,
        },
        {
            "first_page_sequence": 25,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 40,
            "last_page_sequence": 25,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 67,
        },
        {
            "first_page_sequence": 41,
            "first_parent_role": "NO_TERM",
            "first_source_line_index": 12,
            "last_page_sequence": 42,
            "last_parent_role": "ESCROW",
            "last_source_line_index": 51,
        },
    ]
