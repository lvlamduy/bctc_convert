from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/scan_trading_securities_full_document_vietocr_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "scan_trading_securities_full_document_vietocr_v1", _MODULE_PATH
)
assert _SPEC is not None and _SPEC.loader is not None
scanner = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = scanner
_SPEC.loader.exec_module(scanner)


def _page() -> dict[str, object]:
    surfaces = [
        ("Chứng khoán kinh doanh", 0, 0),
        ("30/06/2026", 650, 25),
        ("31/12/2025", 820, 25),
        ("Triệu đồng", 650, 45),
        ("Triệu đồng", 820, 45),
        ("Chứng khoán nợ", 0, 70),
        ("Chứng khoán Chính phủ", 0, 100),
        ("100", 650, 100),
        ("Chứng khoán vốn", 0, 140),
        ("Do các TCTD khác trong nước phát hành", 0, 170),
        ("200", 650, 170),
        ("300", 650, 205),
        ("Dự phòng rủi ro chứng khoán kinh doanh", 0, 240),
        ("(30)", 650, 240),
        ("270", 650, 280),
        ("Dự phòng chứng khoán kinh doanh", 0, 340),
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

    result = scanner.build_trading_securities_full_document_scan_v1({"opaque": "upstream"})

    assert [trial["document_provenance"] for trial in result["trials"]] == list(
        scanner.EXPECTED_DOCUMENT_ORDER
    )
    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "trading_securities_region_count": 8,
        "document_count": 8,
        "document_unique_structural_match_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 8,
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
    result = scanner.build_trading_securities_full_document_scan_v1({})
    forged = copy.deepcopy(result)
    forged["trials"][0]["matcher_result"]["regions"][0]["cluster_boundary"]["last_item_role"] = (
        "DEBT"
    )
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "tsfdsv1:scan:" + scanner.canonical_json_sha256_v1(material)

    with pytest.raises(scanner.TradingSecuritiesFullDocumentScanV1Error, match="replay exactly"):
        scanner.validate_trading_securities_full_document_scan_replay_v1(forged, {})


def test_provenance_relabel_and_bool_as_int_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    axis = _axis()
    axis["documents"][0]["document_provenance"] = "MBB"
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: axis
    )
    with pytest.raises(scanner.TradingSecuritiesFullDocumentScanV1Error, match="trial identity"):
        scanner.build_trading_securities_full_document_scan_v1({})

    clean_axis = _axis()
    clean_axis["documents"][0]["pages"][0]["primary_numeric_authority"] = 0
    monkeypatch.setattr(
        scanner, "project_full_document_vietocr_accounting_axis_v1", lambda _value: clean_axis
    )
    with pytest.raises(Exception, match="exact bool"):
        scanner.build_trading_securities_full_document_scan_v1({})


def test_current_eight_pdf_scan_locks_unique_boundaries_layouts_and_negative() -> None:
    semantic_index = json.loads((scanner.PROJECT_ROOT / scanner.DEFAULT_INPUT).read_text("utf-8"))

    result = scanner.build_trading_securities_full_document_scan_v1(semantic_index)

    assert result["scan_id"] == (
        "tsfdsv1:scan:e3c26b48abdf6f792c153c7953fe6772611dcfaeaa17d7e286998b7f76873243"
    )
    assert result["metrics"] == {
        "accepted_numeric_graph_count": 0,
        "trading_securities_region_count": 7,
        "document_count": 8,
        "document_unique_structural_match_count": 7,
        "mapping_verified_count": 0,
        "near_region_count": 175,
        "unresolved_document_count": 1,
    }
    assert [
        trial["matcher_result"]["regions"][0]["page_sequence"]
        if trial["matcher_result"]["regions"]
        else None
        for trial in result["trials"]
    ] == [16, 31, 40, 24, 30, 37, 20, None]
    assert [
        trial["matcher_result"]["regions"][0]["cluster_boundary"]
        if trial["matcher_result"]["regions"]
        else None
        for trial in result["trials"]
    ] == [
        {
            "first_item_role": "TRADING_SECURITIES_OWNER",
            "first_page_sequence": 16,
            "first_source_line_index": 42,
            "last_item_role": "NET",
            "last_page_sequence": 16,
            "last_source_line_index": 76,
            "selection_rule": (
                "OWNER_THEN_REQUIRED_DEBT_EQUITY_PROVISION_PARENTS_THROUGH_LAST_"
                "NET_OR_PROVISION_ITEM_BEFORE_DISTINCT_NEXT_FAMILY"
            ),
        },
        {
            "first_item_role": "TRADING_SECURITIES_OWNER",
            "first_page_sequence": 31,
            "first_source_line_index": 1,
            "last_item_role": "NET",
            "last_page_sequence": 31,
            "last_source_line_index": 27,
            "selection_rule": (
                "OWNER_THEN_REQUIRED_DEBT_EQUITY_PROVISION_PARENTS_THROUGH_LAST_"
                "NET_OR_PROVISION_ITEM_BEFORE_DISTINCT_NEXT_FAMILY"
            ),
        },
        {
            "first_item_role": "TRADING_SECURITIES_OWNER",
            "first_page_sequence": 40,
            "first_source_line_index": 7,
            "last_item_role": "NET",
            "last_page_sequence": 40,
            "last_source_line_index": 40,
            "selection_rule": (
                "OWNER_THEN_REQUIRED_DEBT_EQUITY_PROVISION_PARENTS_THROUGH_LAST_"
                "NET_OR_PROVISION_ITEM_BEFORE_DISTINCT_NEXT_FAMILY"
            ),
        },
        {
            "first_item_role": "TRADING_SECURITIES_OWNER",
            "first_page_sequence": 24,
            "first_source_line_index": 31,
            "last_item_role": "NET",
            "last_page_sequence": 24,
            "last_source_line_index": 59,
            "selection_rule": (
                "OWNER_THEN_REQUIRED_DEBT_EQUITY_PROVISION_PARENTS_THROUGH_LAST_"
                "NET_OR_PROVISION_ITEM_BEFORE_DISTINCT_NEXT_FAMILY"
            ),
        },
        {
            "first_item_role": "TRADING_SECURITIES_OWNER",
            "first_page_sequence": 30,
            "first_source_line_index": 8,
            "last_item_role": "NET",
            "last_page_sequence": 30,
            "last_source_line_index": 37,
            "selection_rule": (
                "OWNER_THEN_REQUIRED_DEBT_EQUITY_PROVISION_PARENTS_THROUGH_LAST_"
                "NET_OR_PROVISION_ITEM_BEFORE_DISTINCT_NEXT_FAMILY"
            ),
        },
        {
            "first_item_role": "TRADING_SECURITIES_OWNER",
            "first_page_sequence": 37,
            "first_source_line_index": 30,
            "last_item_role": "NET",
            "last_page_sequence": 37,
            "last_source_line_index": 63,
            "selection_rule": (
                "OWNER_THEN_REQUIRED_DEBT_EQUITY_PROVISION_PARENTS_THROUGH_LAST_"
                "NET_OR_PROVISION_ITEM_BEFORE_DISTINCT_NEXT_FAMILY"
            ),
        },
        {
            "first_item_role": "TRADING_SECURITIES_OWNER",
            "first_page_sequence": 20,
            "first_source_line_index": 48,
            "last_item_role": "NET",
            "last_page_sequence": 20,
            "last_source_line_index": 79,
            "selection_rule": (
                "OWNER_THEN_REQUIRED_DEBT_EQUITY_PROVISION_PARENTS_THROUGH_LAST_"
                "NET_OR_PROVISION_ITEM_BEFORE_DISTINCT_NEXT_FAMILY"
            ),
        },
        None,
    ]
    assert [
        trial["matcher_result"]["regions"][0]["layout"]["branch_variant"]
        if trial["matcher_result"]["regions"]
        else None
        for trial in result["trials"]
    ] == [
        "ISSUER_CLASSIFICATION",
        "LISTED_UNLISTED_CLASSIFICATION",
        "ISSUER_CLASSIFICATION",
        "ISSUER_CLASSIFICATION",
        "ISSUER_CLASSIFICATION",
        "ISSUER_CLASSIFICATION",
        "ISSUER_CLASSIFICATION",
        None,
    ]
    assert all(
        trial["matcher_result"]["regions"][0]["layout"]["meaningful_axes"]["period_header_count"]
        >= 2
        and trial["matcher_result"]["regions"][0]["layout"]["meaningful_axes"]["unit_header_count"]
        >= 1
        for trial in result["trials"][:7]
    )
    bid_events = result["trials"][6]["matcher_result"]["regions"][0]["events"]
    assert any(
        event["role_kind"] == "CHILD" and event["role"] == "FOREIGN_TCKT" for event in bid_events
    )
    assert (
        result["trials"][6]["matcher_result"]["regions"][0]["layout"]["meaningful_axes"][
            "unit_header_count"
        ]
        == 1
    )
