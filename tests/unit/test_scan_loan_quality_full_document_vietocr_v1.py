from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/scan_loan_quality_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_loan_quality_full_document_vietocr_v1", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _quality_page() -> dict[str, object]:
    surfaces = [
        ("5. Cho vay khách hàng", 0),
        ("Phân tích chất lượng nợ cho vay", 0),
        ("30/06/2026", 300),
        ("31/12/2025", 600),
        ("Triệu đồng", 300),
        ("Triệu đồng", 600),
        ("Nợ đủ tiêu chuẩn", 0),
        ("100", 300),
        ("90", 600),
        ("Nợ cần chú ý", 0),
        ("10", 300),
        ("9", 600),
        ("Nợ dưới tiêu chuẩn", 0),
        ("5", 300),
        ("4", 600),
        ("Nợ nghi ngờ", 0),
        ("3", 300),
        ("2", 600),
        ("Nợ có khả năng mất vốn", 0),
        ("2", 300),
        ("1", 600),
        ("120", 300),
        ("106", 600),
    ]
    return {
        "lines": [
            {
                "bbox": [x, index * 20, x + 80, index * 20 + 14],
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
            for index, (text, x) in enumerate(surfaces)
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
                "pages": [_quality_page()],
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


def test_all_eight_documents_use_one_matcher_and_remain_numeric_unresolved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )
    result = scanner.build_loan_quality_full_document_scan_v1({"opaque": "upstream"})

    assert result["state"] == "FULL_DOCUMENT_LOAN_QUALITY_STRUCTURE_SCAN_COMPLETE"
    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 0,
        "ordered_anchor_region_count": 8,
        "structure_resolved_numeric_unresolved_count": 8,
        "unresolved_document_count": 0,
    }
    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        scanner.EXPECTED_DOCUMENT_ORDER
    )
    assert all(
        trial["matcher_result"]["graphs"][0]["status"] == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
        for trial in result["trials"]
    )
    assert result["authority"]["bank_identity_used_for_matching_or_routing"] is False


def test_scan_exact_replay_rebuilds_every_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )
    result = scanner.build_loan_quality_full_document_scan_v1({})
    assert scanner.validate_loan_quality_full_document_scan_replay_v1(result, {}) == result


def test_extended_annual_profile_is_forwarded_without_changing_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    for document in axis["documents"]:
        page = document["pages"][0]
        page["lines"][0]["vietocr_text"] = "Theo chất lượng nợ cho vay"
        page["lines"][1]["vietocr_text"] = "Số cuối năm"
        page["lines"][2]["vietocr_text"] = "Số đầu năm"
        page["lines"][3]["vietocr_text"] = "Triệu đồng"
        page["lines"][4]["vietocr_text"] = "Triệu đồng"
        page["lines"][5]["vietocr_text"] = "Cho vay khách hàng"
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )

    default = scanner.build_loan_quality_full_document_scan_v1({})
    annual = scanner.build_loan_quality_full_document_scan_v1(
        {},
        enable_extended_annual_variants=True,
    )

    assert default["metrics"]["document_unique_structural_match_count"] == 0
    assert annual["metrics"]["document_unique_structural_match_count"] == 8
    assert (
        scanner.validate_loan_quality_full_document_scan_replay_v1(
            annual,
            {},
            enable_extended_annual_variants=True,
        )
        == annual
    )


def test_coordinated_persisted_match_tamper_is_rejected_by_public_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )
    result = scanner.build_loan_quality_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["graphs"][0]["rows"][0]["label"]["surface"] = "forged"
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "lqfdsv1:scan:" + scanner.canonical_json_sha256_v1(material)

    with pytest.raises(scanner.LoanQualityFullDocumentScanV1Error, match="replay exactly"):
        scanner.validate_loan_quality_full_document_scan_replay_v1(forged, {})


def test_provenance_relabel_is_rejected_even_when_matching_payload_is_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    axis["documents"][0]["document_provenance"] = "MBB"
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )
    with pytest.raises(scanner.LoanQualityFullDocumentScanV1Error, match="trial identity"):
        scanner.build_loan_quality_full_document_scan_v1({})
