from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/scan_loan_industry_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_loan_industry_full_document_vietocr_v1", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _loan_industry_page() -> dict[str, object]:
    rows = [
        ("Nông nghiệp, lâm nghiệp và thủy sản", 10, 9),
        ("Công nghiệp chế biến, chế tạo", 20, 18),
        ("Xây dựng", 30, 27),
        ("Vận tải kho bãi", 15, 14),
        ("Hoạt động tài chính và bảo hiểm", 5, 4),
        ("Khác", 20, 18),
    ]
    surfaces: list[tuple[str, int, int]] = [
        ("5. Cho vay khách hàng", 0, 0),
        ("Phân tích dư nợ cho vay theo ngành", 0, 35),
        ("30/06/2026", 500, 75),
        ("31/12/2025", 800, 75),
        ("Triệu đồng", 500, 105),
        ("Triệu đồng", 800, 105),
    ]
    for offset, (label, current, previous) in enumerate(rows):
        y = 150 + offset * 45
        surfaces.extend([(label, 0, y), (str(current), 500, y), (str(previous), 800, y)])
    surfaces.extend([("100", 500, 430), ("90", 800, 430)])
    return {
        "lines": [
            {
                "bbox": [x, y, x + 140, y + 24],
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
                "pages": [_loan_industry_page()],
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


def test_all_documents_use_one_industry_matcher_without_bank_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )
    result = scanner.build_loan_industry_full_document_scan_v1({"opaque": "upstream"})

    assert result["state"] == "FULL_DOCUMENT_LOAN_INDUSTRY_STRUCTURE_SCAN_COMPLETE"
    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "branch_table_region_count": 8,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 0,
        "semantic_proposal_accounting_corroborated_lane_count": 16,
        "structure_resolved_numeric_unresolved_count": 8,
        "unresolved_document_count": 0,
    }
    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        scanner.EXPECTED_DOCUMENT_ORDER
    )
    assert result["authority"]["bank_identity_used_for_matching_or_routing"] is False


def test_scan_exact_replay_rebuilds_every_document(monkeypatch: pytest.MonkeyPatch) -> None:
    axis = _axis()
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )
    result = scanner.build_loan_industry_full_document_scan_v1({})
    assert scanner.validate_loan_industry_full_document_scan_replay_v1(result, {}) == result


def test_scan_extended_annual_profile_is_forwarded_and_replayed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    for document in axis["documents"]:
        document["pages"][0]["lines"][1]["vietocr_text"] = "Theo ngành nghề kinh doanh"
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )

    result = scanner.build_loan_industry_full_document_scan_v1(
        {}, enable_extended_annual_variants=True
    )

    assert result["metrics"]["document_unique_structural_match_count"] == 8
    assert (
        scanner.validate_loan_industry_full_document_scan_replay_v1(
            result, {}, enable_extended_annual_variants=True
        )
        == result
    )


def test_coordinated_match_tamper_is_rejected_by_public_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )
    result = scanner.build_loan_industry_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["graphs"][0]["rows"][0]["label"]["surface"] = "forged"
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "lifdsv1:scan:" + scanner.canonical_json_sha256_v1(material)

    with pytest.raises(scanner.LoanIndustryFullDocumentScanV1Error, match="replay exactly"):
        scanner.validate_loan_industry_full_document_scan_replay_v1(forged, {})


def test_provenance_relabel_is_rejected_without_becoming_matcher_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    axis["documents"][0]["document_provenance"] = "MBB"
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )
    with pytest.raises(scanner.LoanIndustryFullDocumentScanV1Error, match="trial identity"):
        scanner.build_loan_industry_full_document_scan_v1({})
