from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_issued_valuable_papers_family_v1 import (
    GeminiJsonIssuedValuablePapersFamilyV1Error,
    _apply_primary_root_projection_receipt_v1,
    _primary_statement_exact_root_projection_v1,
    _project_adjacent_source_syntax_v1,
    _project_face_value_wrappers,
    _project_maturity_context_and_prune_validations_v1,
    adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1,
    build_gemini_json_issued_valuable_papers_region_query_receipt_v1,
    compile_gemini_json_issued_valuable_papers_family_specs_v1,
    evaluate_gemini_json_issued_valuable_papers_family_cluster_v1,
    validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "1" * 64
VERSION_ID = "gfpstorev1:json:" + "2" * 64
SOURCE_SHA256 = "3" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-issued-valuable-papers-topology-v1.json"),
        _json("tm-issued-valuable-papers-evaluation-v1.json"),
        _json("tm-issued-valuable-papers-schema-binding-v1.json"),
    )


def _repair_spec(*repairs: dict) -> dict:
    checked = []
    for repair in repairs:
        material = copy.deepcopy(repair)
        material["repair_id"] = (
            "gjivpfav1:source-repair:" + canonical_json_sha256_v1(material)
        )
        checked.append(material)
    return {
        "family_id": "ISSUED_VALUABLE_PAPERS",
        "format_version": (
            "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_AUTHENTICATED_SOURCE_REPAIR_SPEC_V1"
        ),
        "policy": (
            "ONLY_PDF_VISIBLE_ACCOUNTING_DASH_MISSING_AS_NULL_NO_BLANK_ZERO_INFERENCE"
        ),
        "render_contract": {
            "alpha": False,
            "colorspace": "RGB",
            "format": "PNG",
            "render_dpi": 300,
            "renderer": "BCTC_AI_FULL_PDF_PAGE_RENDER_V1_PYMUPDF",
        },
        "repair_axis_sha256": canonical_json_sha256_v1(checked),
        "repairs": checked,
    }


def _dash_repair(*, row_ordinal: int, column_ordinal: int) -> dict:
    return {
        "after_exact": "-",
        "before_exact": None,
        "crop_evidence": {
            "bbox_pixels_xyxy": [10, 20, 30, 40],
            "pixel_height": 20,
            "pixel_width": 20,
            "rgb_sha256": "4" * 64,
        },
        "locator": {
            "column_ordinal": column_ordinal,
            "page_json_version_id": VERSION_ID,
            "physical_page": 1,
            "row_ordinal": row_ordinal,
            "section_id": "s2",
            "table_id": "t1",
        },
        "observed_pdf_glyph": "-",
        "repair_kind": "MONEY_CELL_VISIBLE_DASH",
        "render": {
            "image_sha256": "5" * 64,
            "image_size_bytes": 100,
            "media_type": "image/png",
            "physical_page": 1,
            "pixel_height": 100,
            "pixel_width": 100,
            "render_dpi": 300,
            "render_receipt_sha256": "6" * 64,
        },
        "source": {
            "source_logical_name": "fixture.pdf",
            "source_sha256": SOURCE_SHA256,
            "source_size_bytes": 1000,
        },
    }


def _row(label: str | None, values: list[str | None], *, kind: str, path: list[str | None]):
    return {
        "hierarchy_path_exact": path,
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _instrument_columns() -> list[dict]:
    return [
        {"header_path_exact": ["Kỳ phiếu", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Trái phiếu ghi sổ", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Chứng chỉ tiền gửi", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Tổng cộng", "Triệu đồng"], "value_kind": "MONEY"},
    ]


def _one_period_rows() -> list[dict]:
    return [
        _row("Dưới 12 tháng", [None] * 4, kind="GROUP", path=["Dưới 12 tháng"]),
        _row(
            "Mệnh giá",
            ["10", "-", "30", "40"],
            kind="ITEM",
            path=["Dưới 12 tháng", "Mệnh giá"],
        ),
        _row(
            "Từ 12 tháng đến 5 năm",
            [None] * 4,
            kind="GROUP",
            path=["Từ 12 tháng đến 5 năm"],
        ),
        _row(
            "Mệnh giá",
            ["-", "20", "5", "25"],
            kind="ITEM",
            path=["Từ 12 tháng đến 5 năm", "Mệnh giá"],
        ),
        _row("Trên 5 năm", [None] * 4, kind="GROUP", path=["Trên 5 năm"]),
        _row(
            "Mệnh giá",
            ["-", "-", "7", "7"],
            kind="ITEM",
            path=["Trên 5 năm", "Mệnh giá"],
        ),
        _row(None, ["10", "20", "42", "72"], kind="TOTAL", path=[None]),
    ]


def _table(rows: list[dict]) -> dict:
    return {
        "columns": _instrument_columns(),
        "continuation": "NONE",
        "rows": rows,
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _ordinary_period_table() -> dict:
    return {
        "columns": [
            {"header_path_exact": ["30/6/2025", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2024", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row("Trái phiếu", [None, None], kind="GROUP", path=["Trái phiếu"]),
            _row(
                "Từ 12 tháng đến dưới 5 năm",
                ["16.000.000", "16.948.000"],
                kind="ITEM",
                path=["Trái phiếu", "Từ 12 tháng đến dưới 5 năm"],
            ),
            _row(
                "Từ 5 năm trở lên",
                ["4.000.000", "4.000.000"],
                kind="ITEM",
                path=["Trái phiếu", "Từ 5 năm trở lên"],
            ),
            _row(
                "Chứng chỉ tiền gửi",
                [None, None],
                kind="GROUP",
                path=["Chứng chỉ tiền gửi"],
            ),
            _row(
                "Từ 6 tháng đến dưới 12 tháng",
                ["100.000", None],
                kind="ITEM",
                path=["Chứng chỉ tiền gửi", "Từ 6 tháng đến dưới 12 tháng"],
            ),
            _row(
                "Từ 12 tháng đến 5 năm",
                ["9.100.000", "2.300.000"],
                kind="ITEM",
                path=["Chứng chỉ tiền gửi", "Từ 12 tháng đến 5 năm"],
            ),
            _row(
                "Từ 5 năm trở lên",
                ["-", "54.579"],
                kind="ITEM",
                path=["Chứng chỉ tiền gửi", "Từ 5 năm trở lên"],
            ),
            _row(None, ["29.200.000", "23.302.579"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _section(title: str, tables: list[dict]) -> dict:
    return {
        "content_kind": "FINANCIAL_NOTE",
        "narratives_exact": [],
        "statement_type": "NOT_APPLICABLE",
        "tables": tables,
        "title_exact": title,
    }


def _page(rows: list[dict]) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            _section(
                "THUYẾT MINH BÁO CÁO TÀI CHÍNH Tại ngày 31/03/2026",
                [],
            ),
            _section("10. PHÁT HÀNH GIẤY TỜ CÓ GIÁ", [_table(rows)]),
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict) -> dict:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _indexed(cluster: dict) -> dict:
    document = {
        key: _record({})[key]
        for key in (
            "document_id",
            "document_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    }
    selected_page = {
        **document,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
    }
    return build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=[document],
        selected_page_axis=[selected_page],
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(_compiled()["query_policy"]),
    )


def _evaluate(page: dict) -> dict:
    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    return evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )


def _evaluate_with_repairs(page: dict, *repairs: dict) -> tuple[dict, dict]:
    compiled = compile_gemini_json_issued_valuable_papers_family_specs_v1(
        _json("tm-issued-valuable-papers-topology-v1.json"),
        _json("tm-issued-valuable-papers-evaluation-v1.json"),
        _json("tm-issued-valuable-papers-schema-binding-v1.json"),
        _repair_spec(*repairs),
    )
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return candidate, {
        "compiled_specs": compiled,
        "query_receipt": receipt,
        "regions": cluster["component_regions"],
    }


def test_transposed_one_current_period_is_closed_locally() -> None:
    candidate = _evaluate(_page(_one_period_rows()))
    assert candidate["status"] == READY
    assert {
        item["role"]: [cell["coefficient"] for cell in item["values"]]
        for item in candidate["mappings"]
    } == {
        "BOND": [20],
        "BOND_LONG": [0],
        "BOND_MEDIUM": [20],
        "BOND_SHORT": [0],
        "CD_LONG": [7],
        "CD_MEDIUM": [5],
        "CD_SHORT": [30],
        "CERTIFICATE_OF_DEPOSIT": [42],
        "FAMILY_ROOT_TOTAL": [72],
        "PROMISSORY_AND_BOND_LONG": [0],
        "PROMISSORY_AND_BOND_MEDIUM": [20],
        "PROMISSORY_AND_BOND_SHORT": [10],
        "PROMISSORY_AND_BOND_TOTAL": [30],
        "PROMISSORY_LONG": [0],
        "PROMISSORY_MEDIUM": [0],
        "PROMISSORY_NOTE": [10],
        "PROMISSORY_SHORT": [10],
    }


def test_transposed_single_instrument_plus_total_is_structurally_sufficient() -> None:
    table = {
        "columns": [
            {"header_path_exact": ["Trái phiếu", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Tổng cộng", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Từ 12 tháng đến dưới 5 năm",
                [None, None],
                kind="GROUP",
                path=["Từ 12 tháng đến dưới 5 năm"],
            ),
            _row(
                "Mệnh giá",
                ["20", "20"],
                kind="ITEM",
                path=["Từ 12 tháng đến dưới 5 năm", "Mệnh giá"],
            ),
            _row(None, ["20", "20"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    candidate = _evaluate(page)
    by_role = {
        item["role"]: [cell["coefficient"] for cell in item["values"]]
        for item in candidate["mappings"]
    }
    assert by_role["BOND_MEDIUM"] == [20]
    assert by_role["BOND"] == [20]
    assert by_role["FAMILY_ROOT_TOTAL"] == [20]


def test_transposed_instrument_totals_without_tenor_breakdown_are_mappable() -> None:
    table = {
        "columns": [
            {"header_path_exact": ["Trái phiếu", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Chứng chỉ tiền gửi", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Tổng cộng", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [_row(None, ["20", "30", "50"], kind="TOTAL", path=[None])],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    candidate = _evaluate(page)
    by_role = {
        item["role"]: [cell["coefficient"] for cell in item["values"]]
        for item in candidate["mappings"]
    }
    assert by_role["BOND"] == [20]
    assert by_role["CERTIFICATE_OF_DEPOSIT"] == [30]
    assert by_role["FAMILY_ROOT_TOTAL"] == [50]


def test_transposed_exact_tpb_tenor_labels_map_instrument_columns() -> None:
    table = {
        "columns": [
            {"header_path_exact": ["Trái phiếu", "Triệu đồng"], "value_kind": "MONEY"},
            {
                "header_path_exact": ["Chứng chỉ tiền gửi", "Triệu đồng"],
                "value_kind": "MONEY",
            },
            {"header_path_exact": ["Tổng cộng", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Kỳ hạn đến 1 năm",
                [None, None, None],
                kind="GROUP",
                path=["Kỳ hạn đến 1 năm"],
            ),
            _row(
                "- Bằng VND",
                ["1", "2", "3"],
                kind="ITEM",
                path=["Kỳ hạn đến 1 năm", "Bằng VND"],
            ),
            _row(
                "Kỳ hạn trên 1 năm đến 5 năm",
                [None, None, None],
                kind="GROUP",
                path=["Kỳ hạn trên 1 năm đến 5 năm"],
            ),
            _row(
                "- Bằng VND",
                ["4", "5", "9"],
                kind="ITEM",
                path=["Kỳ hạn trên 1 năm đến 5 năm", "Bằng VND"],
            ),
            _row(
                "Kỳ hạn trên 5 năm",
                [None, None, None],
                kind="GROUP",
                path=["Kỳ hạn trên 5 năm"],
            ),
            _row(
                "- Bằng VND",
                ["6", "7", "13"],
                kind="ITEM",
                path=["Kỳ hạn trên 5 năm", "Bằng VND"],
            ),
            _row(None, ["11", "14", "25"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    candidate = _evaluate(page)
    by_role = {
        item["role"]: [cell["coefficient"] for cell in item["values"]]
        for item in candidate["mappings"]
    }
    assert by_role["BOND_SHORT"] == [1]
    assert by_role["CD_SHORT"] == [2]
    assert by_role["BOND_MEDIUM"] == [4]
    assert by_role["CD_MEDIUM"] == [5]
    assert by_role["BOND_LONG"] == [6]
    assert by_role["CD_LONG"] == [7]


def test_foreign_currency_registered_bond_parent_keeps_visible_tenor_child() -> None:
    table = {
        "columns": [
            {"header_path_exact": ["Cuối kỳ", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Đầu kỳ", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Trái phiếu bằng ngoại tệ",
                ["5", "4"],
                kind="GROUP",
                path=["Trái phiếu bằng ngoại tệ"],
            ),
            _row(
                "- Từ 1 năm đến 5 năm",
                ["5", "4"],
                kind="ITEM",
                path=["Trái phiếu bằng ngoại tệ", "- Từ 1 năm đến 5 năm"],
            ),
            _row(None, ["5", "4"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    candidate = _evaluate(page)
    by_role = {
        item["role"]: [cell["coefficient"] for cell in item["values"]]
        for item in candidate["mappings"]
    }
    assert by_role["BOND"] == [5, 4]
    assert by_role["BOND_MEDIUM"] == [5, 4]


def test_transposed_semantic_current_and_comparative_blocks_are_supported() -> None:
    current = _one_period_rows()
    comparative = copy.deepcopy(_one_period_rows())
    comparative[-1]["values_exact"] = ["8", "15", "35", "58"]
    comparative[1]["values_exact"] = ["8", "-", "25", "33"]
    comparative[3]["values_exact"] = ["-", "15", "4", "19"]
    comparative[5]["values_exact"] = ["-", "-", "6", "6"]
    rows = [
        _row("Số cuối kỳ", [None] * 4, kind="GROUP", path=["Số cuối kỳ"]),
        *current,
        _row("Số dư đầu kỳ", [None] * 4, kind="GROUP", path=["Số dư đầu kỳ"]),
        *comparative,
    ]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == READY
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [72, 58]


def test_transposed_dated_current_and_comparative_markers_bind_exact_dates() -> None:
    current = _one_period_rows()
    comparative = copy.deepcopy(_one_period_rows())
    comparative[-1]["values_exact"] = ["8", "15", "35", "58"]
    comparative[1]["values_exact"] = ["8", "-", "25", "33"]
    comparative[3]["values_exact"] = ["-", "15", "4", "19"]
    comparative[5]["values_exact"] = ["-", "-", "6", "6"]
    rows = [
        _row(
            "Số cuối kỳ tại 31/03/2026",
            [None] * 4,
            kind="GROUP",
            path=["Số cuối kỳ tại 31/03/2026"],
        ),
        *current,
        _row(
            "Số dư đầu kỳ tại 31/12/2025",
            [None] * 4,
            kind="GROUP",
            path=["Số dư đầu kỳ tại 31/12/2025"],
        ),
        *comparative,
    ]
    candidate = _evaluate(_page(rows))
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert [cell["coefficient"] for cell in root["values"]] == [72, 58]
    blocks = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]["blocks"]
    assert [block["lane_key"] for block in blocks] == [
        ["DATE", "2026-03-31"],
        ["DATE", "2025-12-31"],
    ]


def test_transposed_row_blocks_reject_column_period_evidence() -> None:
    rows = [
        _row("Số cuối kỳ", [None] * 4, kind="GROUP", path=["Số cuối kỳ"]),
        *_one_period_rows(),
        _row("Số dư đầu kỳ", [None] * 4, kind="GROUP", path=["Số dư đầu kỳ"]),
        *copy.deepcopy(_one_period_rows()),
    ]
    page = _page(rows)
    for column in page["sections"][1]["tables"][0]["columns"]:
        column["header_path_exact"].append("31/03/2026")
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    reasons = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]["reasons"]
    assert "TRANSPOSED_ROW_BLOCKS_CONFLICT_WITH_COLUMN_PERIOD_EVIDENCE" in reasons


def test_transposed_period_marker_cannot_carry_money_values() -> None:
    rows = [
        _row("Số cuối kỳ", ["1", "2", "3", "6"], kind="ITEM", path=["Số cuối kỳ"]),
        *_one_period_rows(),
    ]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    reasons = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]["reasons"]
    assert "TRANSPOSED_ROW_PERIOD_MARKER_HAS_MONEY_VALUES:r1" in reasons


def test_role_visible_only_in_current_block_remains_mappable() -> None:
    current = _one_period_rows()
    comparative = copy.deepcopy(_one_period_rows())
    comparative[1]["values_exact"] = ["8", "-", "25", "33"]
    comparative[3]["values_exact"] = ["-", "15", "4", "19"]
    comparative = comparative[:4] + comparative[6:]
    comparative[-1]["values_exact"] = ["8", "15", "29", "52"]
    rows = [
        _row("Số cuối kỳ", [None] * 4, kind="GROUP", path=["Số cuối kỳ"]),
        *current,
        _row("Số dư đầu kỳ", [None] * 4, kind="GROUP", path=["Số dư đầu kỳ"]),
        *comparative,
    ]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == READY
    cd_long = next(item for item in candidate["mappings"] if item["role"] == "CD_LONG")
    assert [cell["coefficient"] for cell in cd_long["values"]] == [7]


def test_transposed_horizontal_mismatch_is_unresolved() -> None:
    rows = _one_period_rows()
    rows[1]["values_exact"][-1] = "41"
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any(
        "TRANSPOSED_ROW_HORIZONTAL_EQUATION_MISMATCH" in item for item in candidate["reasons"]
    )


def test_transposed_total_column_must_be_explicit_and_unique() -> None:
    page = _page(_one_period_rows())
    table = page["sections"][1]["tables"][0]
    table["columns"][-1]["header_path_exact"] = ["Không rõ", "Triệu đồng"]
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_transposed_suffix_alignment_cannot_backsolve_blank_instrument_lane() -> None:
    rows = _one_period_rows()
    rows[1]["values_exact"] = ["10", "30", "40", None]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert "value_alignment_receipt" not in receipt
    assert "TRANSPOSED_ROW_HORIZONTAL_EQUATION_MISMATCH:r1" in receipt["transposed_reasons"]


def test_dash_only_neighbors_cannot_authenticate_missing_instrument_lane() -> None:
    rows = _one_period_rows()
    rows[1]["values_exact"] = ["10", "30", "40", None]
    rows[2:2] = [
        _row(
            "Chiết khấu",
            ["-", None, "-", None],
            kind="ITEM",
            path=["Dưới 12 tháng", "Chiết khấu"],
        ),
        _row(
            "Phụ trội",
            ["-", None, "-", None],
            kind="ITEM",
            path=["Dưới 12 tháng", "Phụ trội"],
        ),
    ]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert "value_alignment_receipt" not in receipt


def test_transposed_multiple_row_suffix_shifts_cannot_backsolve_blank_lanes() -> None:
    rows = _one_period_rows()
    rows[1]["values_exact"] = ["10", "30", "40", None]
    rows[5]["values_exact"] = [None, "7", "7", None]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert "value_alignment_receipt" not in receipt


def test_transposed_multiple_equation_closing_alignments_remain_unresolved() -> None:
    rows = _one_period_rows()
    rows[1]["values_exact"] = ["-", "10", "10", None]
    rows[-1]["values_exact"] = ["-", "20", "22", "42"]
    candidate = _evaluate(_page(rows))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "value_alignment_receipt" not in candidate["closure_receipt"]["table_receipts"][0]


def test_label_only_parent_exact_frontier_preserves_blank_child_lane() -> None:
    page = _page([])
    page["sections"][1]["tables"] = [_ordinary_period_table()]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    by_role = {item["role"]: item for item in candidate["mappings"]}
    short = by_role["CD_SHORT"]
    assert [cell["coefficient"] for cell in short["values"]] == [100000, None]
    assert short["state"] == "PARTIAL_SOURCE_OBSERVATION"
    assert short["values"][1] == {
        "coefficient": None,
        "source_text": None,
        "state": "BLANK_SOURCE_CELL",
    }
    assert [cell["coefficient"] for cell in by_role["BOND"]["values"]] == [
        20000000,
        20948000,
    ]
    assert [
        cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]
    ] == [29200000, 23302579]


def test_authenticated_pdf_dash_repairs_exact_null_cell_without_backsolve() -> None:
    page = _page([])
    page["sections"][1]["tables"] = [_ordinary_period_table()]
    candidate, replay = _evaluate_with_repairs(
        page, _dash_repair(row_ordinal=5, column_ordinal=2)
    )
    assert candidate["status"] == READY
    short = next(item for item in candidate["mappings"] if item["role"] == "CD_SHORT")
    assert [cell["coefficient"] for cell in short["values"]] == [100000, 0]
    assert short["values"][1]["source_text"] == "-"
    adapter = candidate["closure_receipt"]["issued_valuable_papers_adapter_receipt"]
    assert len(adapter["authenticated_source_repairs"]) == 1
    assert validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
        candidate,
        regions=replay["regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=replay["compiled_specs"],
        query_receipt=replay["query_receipt"],
    ) == candidate


def test_authenticated_pdf_dash_repair_fails_closed_on_before_image_drift() -> None:
    page = _page([])
    page["sections"][1]["tables"] = [_ordinary_period_table()]
    page["sections"][1]["tables"][0]["rows"][4]["values_exact"][1] = "1"
    with pytest.raises(
        GeminiJsonIssuedValuablePapersFamilyV1Error,
        match="before-image drifted",
    ):
        _evaluate_with_repairs(page, _dash_repair(row_ordinal=5, column_ordinal=2))


def test_source_repair_axis_and_candidate_replay_tamper_fail_closed() -> None:
    repair_spec = _repair_spec(_dash_repair(row_ordinal=5, column_ordinal=2))
    repair_spec["repairs"][0]["crop_evidence"]["rgb_sha256"] = "7" * 64
    with pytest.raises(
        GeminiJsonIssuedValuablePapersFamilyV1Error,
        match="identity drifted",
    ):
        compile_gemini_json_issued_valuable_papers_family_specs_v1(
            _json("tm-issued-valuable-papers-topology-v1.json"),
            _json("tm-issued-valuable-papers-evaluation-v1.json"),
            _json("tm-issued-valuable-papers-schema-binding-v1.json"),
            repair_spec,
        )

    page = _page([])
    page["sections"][1]["tables"] = [_ordinary_period_table()]
    candidate, replay = _evaluate_with_repairs(
        page, _dash_repair(row_ordinal=5, column_ordinal=2)
    )
    candidate["mappings"][0]["values"][0]["coefficient"] += 1
    with pytest.raises(
        GeminiJsonIssuedValuablePapersFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
            candidate,
            regions=replay["regions"],
            page_json_by_version={VERSION_ID: page},
            compiled_specs=replay["compiled_specs"],
            query_receipt=replay["query_receipt"],
        )


def test_registered_source_repair_artifact_compiles_exact_axis() -> None:
    artifact = json.loads(
        (
            ROOT
            / "data/registered/gemini_json_issued_valuable_papers_source_repairs_v1.json"
        ).read_bytes()
    )
    compiled = compile_gemini_json_issued_valuable_papers_family_specs_v1(
        _json("tm-issued-valuable-papers-topology-v1.json"),
        _json("tm-issued-valuable-papers-evaluation-v1.json"),
        _json("tm-issued-valuable-papers-schema-binding-v1.json"),
        artifact,
    )
    repairs = compiled["issued_valuable_papers_source_repairs"]
    assert len(repairs) == 28
    assert sum(
        repair["source"]["source_logical_name"].startswith(
            "vietstock_bctc/ABB/"
        )
        for repair in repairs
    ) == 15
    assert sum(
        repair["source"]["source_logical_name"].startswith(
            "vietstock_bctc/SGB/"
        )
        for repair in repairs
    ) == 8
    assert sum(
        repair["source"]["source_logical_name"]
        == "vietstock_bctc/VAB/2026/BCTC Công ty mẹ quý 2 năm 2026.pdf"
        for repair in repairs
    ) == 1
    assert sum(
        repair["source"]["source_logical_name"]
        == (
            "vietstock_bctc/TPB/2025/"
            "BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf"
        )
        for repair in repairs
    ) == 4
    vab_repair = next(
        repair
        for repair in repairs
        if repair["source"]["source_logical_name"]
        == "vietstock_bctc/VAB/2026/BCTC Công ty mẹ quý 2 năm 2026.pdf"
    )
    assert vab_repair["locator"]["column_ordinal"] == 2
    assert vab_repair["crop_evidence"]["bbox_pixels_xyxy"] == [
        2195,
        1970,
        2262,
        2025,
    ]
    assert (
        compiled["issued_valuable_papers_source_repair_spec_sha256"]
        == canonical_json_sha256_v1(artifact)
    )


def test_declared_metric_header_excludes_non_accounting_terms_control() -> None:
    page = _page([])
    control = {
        "columns": [
            {
                "header_path_exact": ["Số lượng đã phát hành (Trái phiếu)"],
                "value_kind": "MONEY",
            },
            {"header_path_exact": ["Giá trị (USD)"], "value_kind": "MONEY"},
            {
                "header_path_exact": ["Giá chuyển đổi dự kiến (VND/cổ phần)"],
                "value_kind": "MONEY",
            },
        ],
        "continuation": "NONE",
        "rows": [_row("Trái phiếu chuyển đổi", ["10", "20", "30"], kind="ITEM", path=[])],
        "title_exact": None,
        "unit_exact": None,
    }
    page["sections"][1]["tables"] = [_ordinary_period_table(), control]
    compiled = _compiled()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 1
    control_inventory = next(
        item for item in cluster["declared_money_table_inventory"] if item["table_id"] == "t2"
    )
    assert control_inventory["disposition"] == "EXCLUDED_TYPED_CONTROL"
    assert (
        control_inventory["classification"]["typed_control_disposition"]
        == "NON_ACCOUNTING_CONVERTIBLE_BOND_TERMS_CONTROL"
    )


def test_control_header_cannot_hide_a_declared_family_role() -> None:
    page = _page([])
    control = {
        "columns": [
            {
                "header_path_exact": ["Số lượng đã phát hành (Trái phiếu)"],
                "value_kind": "MONEY",
            }
        ],
        "continuation": "NONE",
        "rows": [_row("Trái phiếu", ["10"], kind="GROUP", path=["Trái phiếu"])],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page["sections"][1]["tables"] = [_ordinary_period_table(), control]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert any("TYPED_CONTROL_AND_DECLARED_FAMILY_ROLE_CONFLICT" in x for x in cluster["reasons"])


def _two_date_context_table() -> dict:
    return {
        "columns": [
            {"header_path_exact": ["31/03/2026", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [_row("Khoản mục khác", ["1", "1"], kind="ITEM", path=[])],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def test_transposed_document_period_context_requires_repeated_tables() -> None:
    page = _page(_one_period_rows())
    page["sections"][0]["title_exact"] = "THUYẾT MINH BÁO CÁO TÀI CHÍNH"
    page["sections"][0]["tables"] = [_two_date_context_table()]
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["closure_receipt"]["document_period_context"]["resolution"] == (
        "EXACT_TWO_DATE_MONEY_TABLE_CONTEXT_NOT_REPEATED"
    )


def test_transposed_document_period_context_uses_repeated_table_consensus() -> None:
    page = _page(_one_period_rows())
    page["sections"][0]["title_exact"] = "THUYẾT MINH BÁO CÁO TÀI CHÍNH"
    page["sections"][0]["tables"] = [_two_date_context_table(), _two_date_context_table()]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    root = next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")
    assert root["values"][0]["coefficient"] == 72


def test_transposed_date_and_semantic_period_conflict_is_unresolved() -> None:
    page = _page(_one_period_rows())
    for column in page["sections"][1]["tables"][0]["columns"]:
        column["header_path_exact"].extend(["31/03/2026", "Số dư đầu kỳ"])
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    lane_reasons = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]["reasons"]
    assert "TRANSPOSED_DATE_SEMANTIC_PERIOD_CONFLICT" in lane_reasons


def test_transposed_conflicting_semantic_period_aliases_are_unresolved() -> None:
    page = _page(_one_period_rows())
    page["sections"][0]["title_exact"] = "THUYẾT MINH BÁO CÁO TÀI CHÍNH"
    for column in page["sections"][1]["tables"][0]["columns"]:
        column["header_path_exact"].extend(["Số cuối kỳ", "Số dư đầu kỳ"])
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    lane_reasons = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]["reasons"]
    assert any("PERIOD_ROLE" in reason for reason in lane_reasons)


def test_transposed_conflicting_money_magnitudes_are_unresolved() -> None:
    page = _page(_one_period_rows())
    page["sections"][1]["tables"][0]["columns"][0]["header_path_exact"].append("Nghìn VND")
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    unit_axis = candidate["closure_receipt"]["table_receipts"][0]["unit_axis"]
    assert unit_axis["complete"] is False


def test_transposed_unclassified_money_column_is_not_silently_ignored() -> None:
    page = _page(_one_period_rows())
    table = page["sections"][1]["tables"][0]
    table["columns"].insert(
        -1,
        {"header_path_exact": ["Giá trị khác", "Triệu đồng"], "value_kind": "MONEY"},
    )
    for row in table["rows"]:
        row["values_exact"].insert(-1, "999")
    candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    lane_axis = candidate["closure_receipt"]["table_receipts"][0]["lane_axis"]
    assert lane_axis["unclassified_money_column_ordinals"] == [4]


def test_tenor_parent_instrument_child_hierarchy_is_resolved_generically() -> None:
    table = {
        "columns": [
            {"header_path_exact": ["Số cuối kỳ", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số đầu kỳ", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row("Dưới 12 tháng", ["30", "25"], kind="SUBTOTAL", path=["Dưới 12 tháng"]),
            _row(
                "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ["30", "25"],
                kind="ITEM",
                path=["Dưới 12 tháng", "Mệnh giá chứng chỉ tiền gửi bằng VND"],
            ),
            _row(
                "Từ 12 tháng đến dưới 5 năm",
                ["25", "20"],
                kind="SUBTOTAL",
                path=["Từ 12 tháng đến dưới 5 năm"],
            ),
            _row(
                "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ["5", "4"],
                kind="ITEM",
                path=[
                    "Từ 12 tháng đến dưới 5 năm",
                    "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ],
            ),
            _row(
                "Mệnh giá trái phiếu bằng VND",
                ["20", "16"],
                kind="ITEM",
                path=["Từ 12 tháng đến dưới 5 năm", "Mệnh giá trái phiếu bằng VND"],
            ),
            _row("Từ 5 năm trở lên", ["7", "6"], kind="SUBTOTAL", path=["Từ 5 năm trở lên"]),
            _row(
                "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ["7", "6"],
                kind="ITEM",
                path=["Từ 5 năm trở lên", "Mệnh giá chứng chỉ tiền gửi bằng VND"],
            ),
            _row(None, ["62", "51"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    by_role = {
        item["role"]: [cell["coefficient"] for cell in item["values"]]
        for item in candidate["mappings"]
    }
    assert by_role["CERTIFICATE_OF_DEPOSIT"] == [42, 35]
    assert by_role["BOND"] == [20, 16]
    assert by_role["CD_SHORT"] == [30, 25]
    assert by_role["CD_MEDIUM"] == [5, 4]
    assert by_role["CD_LONG"] == [7, 6]
    assert by_role["BOND_MEDIUM"] == [20, 16]
    assert by_role["FAMILY_ROOT_TOTAL"] == [62, 51]


def test_instrument_child_with_two_tenor_ancestors_is_ambiguous() -> None:
    table = {
        "columns": [
            {"header_path_exact": ["Số cuối kỳ", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số đầu kỳ", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row("Dưới 12 tháng", ["10", "9"], kind="SUBTOTAL", path=["Dưới 12 tháng"]),
            _row(
                "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ["10", "9"],
                kind="ITEM",
                path=[
                    "Dưới 12 tháng",
                    "Từ 12 tháng đến dưới 5 năm",
                    "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ],
            ),
            _row(None, ["10", "9"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    # The validation-only generic-paper row keeps this owner table in the
    # audited candidate frontier, but cannot resolve the contradictory
    # CD_SHORT/CD_MEDIUM hierarchy path into a schema mapping.
    assert cluster["status"] == READY
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == ["AMBIGUOUS_DECLARED_SOURCE_ROW_ROLE"]


def test_generic_capital_bond_alias_accepts_issuer_suffix_without_routing() -> None:
    table = {
        "columns": [
            {"header_path_exact": ["30/06/2026", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Trái phiếu tăng vốn BIDV",
                ["5", "4"],
                kind="ITEM",
                path=["Trái phiếu tăng vốn BIDV"],
            ),
            _row(None, ["5", "4"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    candidate = _evaluate(page)
    by_role = {
        item["role"]: [cell["coefficient"] for cell in item["values"]]
        for item in candidate["mappings"]
    }
    assert by_role["OTHER_ISSUED_PAPER"] == [5, 4]
    assert by_role["FAMILY_ROOT_TOTAL"] == [5, 4]


def test_exact_bond_over_one_year_source_row_maps_the_printed_bond_total() -> None:
    table = {
        "columns": [
            {"header_path_exact": ["30/6/2025"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2024"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Chứng chỉ tiền gửi dưới 1 năm",
                ["10", "4"],
                kind="ITEM",
                path=["Chứng chỉ tiền gửi dưới 1 năm"],
            ),
            _row(
                "Chứng chỉ tiền gửi từ 1 năm trở lên",
                ["12", "12"],
                kind="ITEM",
                path=["Chứng chỉ tiền gửi từ 1 năm trở lên"],
            ),
            _row(
                "Trái phiếu trên 1 năm",
                ["3", "3"],
                kind="ITEM",
                path=["Trái phiếu trên 1 năm"],
            ),
            _row(None, ["25", "19"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    candidate = _evaluate(page)
    assert candidate["status"] == READY
    by_role = {
        item["role"]: [cell["coefficient"] for cell in item["values"]]
        for item in candidate["mappings"]
    }
    assert by_role["BOND"] == [3, 3]
    assert by_role["FAMILY_ROOT_TOTAL"] == [25, 19]


def test_declared_alias_prefix_policy_rejects_unknown_role() -> None:
    evaluation = _json("tm-issued-valuable-papers-evaluation-v1.json")
    evaluation["row_alias_prefix_roles"] = ["UNKNOWN_ROLE"]
    with pytest.raises(ValueError, match="row_alias_prefix_roles"):
        compile_gemini_json_multitable_hierarchical_family_specs_v1(
            _json("tm-issued-valuable-papers-topology-v1.json"),
            evaluation,
            _json("tm-issued-valuable-papers-schema-binding-v1.json"),
        )


def _narrative_owner_page() -> dict:
    page = _page([])
    section = page["sections"][1]
    section["title_exact"] = "THUYẾT MINH BÁO CÁO TÀI CHÍNH (tiếp theo)"
    section["narratives_exact"] = [
        "Quý 4 năm 2025",
        "20. PHÁT HÀNH GIẤY TỜ CÓ GIÁ",
    ]
    section["tables"] = [_ordinary_period_table()]
    return page


def test_exact_narrative_owner_recovers_only_the_sole_local_money_table() -> None:
    page = _narrative_owner_page()
    compiled = _compiled()
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert raw_cluster["status"] == NOT_OBSERVED
    adapted, receipts = (
        adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
            _indexed(raw_cluster),
            page_json_by_document={1: {VERSION_ID: page}},
            compiled_specs=compiled,
        )
    )
    assert adapted["accepted_clusters"][0]["status"] == READY
    assert receipts[0]["owner_source_kind"] == "SECTION_NARRATIVE"
    assert receipts[0]["owner_surface_ordinal"] == 2
    regions = adapted["accepted_clusters"][0]["component_regions"]
    candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
        regions=regions,
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
            regions
        ),
    )
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "BOND_MEDIUM",
        "CERTIFICATE_OF_DEPOSIT",
        "FAMILY_ROOT_TOTAL",
    }


@pytest.mark.parametrize("failure_kind", ["duplicate_owner", "second_table", "reset"])
def test_local_owner_recovery_rejects_ambiguous_or_reset_section(
    failure_kind: str,
) -> None:
    page = _narrative_owner_page()
    section = page["sections"][1]
    if failure_kind == "duplicate_owner":
        section["narratives_exact"].append("Phát hành giấy tờ có giá")
    elif failure_kind == "second_table":
        section["tables"].append(copy.deepcopy(_ordinary_period_table()))
    else:
        section["narratives_exact"].append("21. Vốn và các quỹ")
    compiled = _compiled()
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    adapted, receipts = (
        adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
            _indexed(raw_cluster),
            page_json_by_document={1: {VERSION_ID: page}},
            compiled_specs=compiled,
        )
    )
    assert adapted["accepted_clusters"] == []
    assert receipts == []


def test_local_owner_recovery_rejects_unsealed_raw_query_tamper() -> None:
    page = _narrative_owner_page()
    compiled = _compiled()
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    indexed = _indexed(raw_cluster)
    indexed["candidate_dispositions"][0]["cluster"]["source_sha256"] = "9" * 64
    with pytest.raises(ValueError, match="binding drifted"):
        adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
            indexed,
            page_json_by_document={1: {VERSION_ID: page}},
            compiled_specs=compiled,
        )


def _internal_root_row_page() -> dict:
    root = "10 Phát hành giấy tờ có giá :"
    table = {
        "columns": [
            {"header_path_exact": ["Cuối kỳ"], "value_kind": "MONEY"},
            {"header_path_exact": ["Đầu năm"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(root, [None, None], kind="GROUP", path=[root]),
            _row(
                "Trái phiếu",
                ["5", "4"],
                kind="ITEM",
                path=[root, "Trái phiếu"],
            ),
            _row("Tổng", ["5", "4"], kind="TOTAL", path=[root, "Tổng"]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [_section(None, [table])],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def test_unique_internal_root_row_recovers_terminal_total_without_mapping_blank_owner() -> None:
    page = _internal_root_row_page()
    source_rows = copy.deepcopy(page["sections"][0]["tables"][0]["rows"])
    compiled = _compiled()
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert raw_cluster["status"] == NOT_OBSERVED
    matching_inventory = [
        item
        for item in raw_cluster["declared_money_table_inventory"]
        if item["classification"].get("family_root_row_ordinals") == [1]
    ]
    assert len(matching_inventory) == 1
    assert matching_inventory[0]["disposition"] == "OUTSIDE_SELECTED_OWNER_FENCE"

    adapted, receipts = (
        adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
            _indexed(raw_cluster),
            page_json_by_document={1: {VERSION_ID: page}},
            compiled_specs=compiled,
        )
    )
    assert len(receipts) == 1
    receipt = receipts[0]
    assert receipt["format_version"] == (
        "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_INTERNAL_ROOT_ROW_QUERY_RECEIPT_V1"
    )
    assert receipt["raw_source_row_axis"] == source_rows
    assert receipt["root_row_exact"]["values_exact"] == [None, None]
    assert receipt["terminal_root_row_exact"] == {
        "hierarchy_path_exact": [
            "10 Phát hành giấy tờ có giá :",
            "Tổng",
        ],
        "label_exact": "Tổng",
        "row_kind": "TOTAL",
        "row_ordinal": 3,
        "values_exact": ["5", "4"],
    }
    cluster = adapted["accepted_clusters"][0]
    assert cluster["owner_receipt"]["internal_root_row_query_receipt_id"] == receipt[
        "internal_root_row_query_receipt_id"
    ]
    regions = cluster["component_regions"]
    query_receipt = build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
        regions
    )
    candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
        regions=regions,
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["BOND"]["values"]] == [5, 4]
    assert [
        cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]
    ] == [5, 4]
    assert {
        source_ref["row_ordinal"]
        for mapping in candidate["mappings"]
        for source_ref in mapping["source_refs"]
    } == {2, 3}
    assert {
        source_ref["row_ordinal"]
        for source_ref in by_role["FAMILY_ROOT_TOTAL"]["source_refs"]
    } == {3}
    assert validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
        candidate,
        regions=regions,
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=query_receipt,
    ) == candidate

    tampered = copy.deepcopy(page)
    tampered["sections"][0]["tables"][0]["rows"][2]["values_exact"][0] = "6"
    with pytest.raises(
        GeminiJsonIssuedValuablePapersFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
            candidate,
            regions=regions,
            page_json_by_version={VERSION_ID: tampered},
            compiled_specs=compiled,
            query_receipt=query_receipt,
        )


@pytest.mark.parametrize(
    "failure_kind",
    ["duplicate", "ambiguous", "reset", "nonterminal", "control"],
)
def test_internal_root_row_recovery_fails_closed_on_nonunique_or_unsafe_shape(
    failure_kind: str,
) -> None:
    page = _internal_root_row_page()
    table = page["sections"][0]["tables"][0]
    root = table["rows"][0]["label_exact"]
    if failure_kind == "duplicate":
        page["sections"][0]["tables"].append(copy.deepcopy(table))
    elif failure_kind == "ambiguous":
        table["rows"].insert(
            1,
            _row(
                "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ["1", "1"],
                kind="ITEM",
                path=[
                    root,
                    "Dưới 12 tháng",
                    "Từ 12 tháng đến dưới 5 năm",
                    "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ],
            ),
        )
        table["rows"][-1]["values_exact"] = ["6", "5"]
    elif failure_kind == "reset":
        table["rows"].insert(
            -1,
            _row(
                "Vốn và các quỹ",
                [None, None],
                kind="GROUP",
                path=[root, "Vốn và các quỹ"],
            ),
        )
    elif failure_kind == "nonterminal":
        table["rows"].append(
            _row(
                "Khoản khác",
                ["1", "1"],
                kind="ITEM",
                path=[root, "Khoản khác"],
            )
        )
    else:
        table["title_exact"] = "Rủi ro thanh khoản"

    compiled = _compiled()
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    root_classifications = [
        item["classification"]
        for item in raw_cluster["declared_money_table_inventory"]
        if item["classification"].get("family_root_row_ordinals") == [1]
    ]
    if failure_kind == "duplicate":
        assert len(root_classifications) == 2
    elif failure_kind == "ambiguous":
        assert len(root_classifications) == 1
        assert root_classifications[0]["ambiguous_rows"]
    elif failure_kind == "control":
        assert len(root_classifications) == 1
        assert root_classifications[0]["typed_control_disposition"] is not None

    adapted, receipts = (
        adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
            _indexed(raw_cluster),
            page_json_by_document={1: {VERSION_ID: page}},
            compiled_specs=compiled,
        )
    )
    assert adapted["accepted_clusters"] == []
    assert receipts == []


def test_immediately_prior_numbered_validation_table_is_not_a_leading_component() -> None:
    prior_table = {
        "columns": [
            {"header_path_exact": ["30/6/2025"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2024"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Bằng VND",
                ["115", "86"],
                kind="ITEM",
                path=["Vốn tài trợ", "Bằng VND"],
            ),
            _row(None, ["115", "86"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            _section("20. Vốn tài trợ, ủy thác đầu tư", [prior_table]),
            _section("21. PHÁT HÀNH GIẤY TỜ CÓ GIÁ", [_ordinary_period_table()]),
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    compiled = _compiled()
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert raw_cluster["status"] == READY
    assert len(raw_cluster["component_regions"]) == 2
    assert raw_cluster["owner_receipt"]["leading_component_positions"] == [
        [1, 1, 1]
    ]

    adapted, receipts = (
        adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
            _indexed(raw_cluster),
            page_json_by_document={1: {VERSION_ID: page}},
            compiled_specs=compiled,
        )
    )
    cluster = adapted["accepted_clusters"][0]
    assert len(cluster["component_regions"]) == 1
    assert cluster["component_regions"][0]["section_id"] == "s2"
    assert cluster["component_regions"][0]["fragment_ordinal"] == 1
    assert cluster["owner_receipt"]["leading_component_positions"] == []
    assert receipts[0]["format_version"] == (
        "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_"
        "VALIDATION_ONLY_LEADING_PRUNE_RECEIPT_V1"
    )
    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
        regions=regions,
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=(
            build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
                regions
            )
        ),
    )
    assert candidate["status"] == READY


def _face_value_wrapper_page(*, short_current: str = "1") -> dict:
    table = {
        "columns": [
            {"header_path_exact": ["Cuối kỳ", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Đầu kỳ", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row("Trái phiếu", [None, None], kind="GROUP", path=["Trái phiếu"]),
            _row(
                "- Mệnh giá",
                ["5", "4"],
                kind="SUBTOTAL",
                path=["Trái phiếu", "Mệnh giá"],
            ),
            _row(
                "+ Kỳ hạn dưới 12 tháng",
                [short_current, "1"],
                kind="ITEM",
                path=["Trái phiếu- Mệnh giá+ Kỳ hạn dưới 12 tháng"],
            ),
            _row(
                "+ Kỳ hạn từ 12 tháng đến dưới 5 năm",
                ["4", "3"],
                kind="ITEM",
                path=["Trái phiếu", "Mệnh giá", "Kỳ hạn từ 12 tháng đến dưới 5 năm"],
            ),
            _row("Tổng", ["5", "4"], kind="TOTAL", path=["Tổng"]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    return page


def test_face_value_wrapper_projection_maps_visible_tenors_and_restores_source_paths() -> None:
    page = _face_value_wrapper_page()
    candidate, _replay = _evaluate_with_repairs(page)
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["BOND_SHORT"]["values"]] == [1, 1]
    assert [cell["coefficient"] for cell in by_role["BOND_MEDIUM"]["values"]] == [4, 3]
    assert by_role["BOND_SHORT"]["source_refs"][0]["hierarchy_path_exact"] == [
        "Trái phiếu- Mệnh giá+ Kỳ hạn dưới 12 tháng"
    ]
    adapter = candidate["closure_receipt"][
        "issued_valuable_papers_adapter_receipt"
    ]
    wrapper = adapter["face_value_wrapper_receipts"][0]
    assert len(wrapper["projections"]) == 2
    assert all("values_exact" not in projection for projection in wrapper["projections"])


def test_face_value_wrapper_projection_requires_immediate_exact_wrapper() -> None:
    page = _face_value_wrapper_page()
    page["sections"][1]["tables"][0]["rows"][1]["label_exact"] = "- Giá trị hợp lý"
    candidate, _replay = _evaluate_with_repairs(page)
    assert candidate["status"] == READY
    assert "issued_valuable_papers_adapter_receipt" not in candidate["closure_receipt"]
    short = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "BOND_SHORT")
    assert short["source_refs"][0]["hierarchy_path_exact"] == [
        "Trái phiếu- Mệnh giá+ Kỳ hạn dưới 12 tháng"
    ]


def _flattened_tenor_carrier_page() -> dict:
    table = {
        "columns": [
            {"header_path_exact": ["Số cuối kỳ", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số đầu kỳ", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Dưới 12 tháng",
                ["18.300", "7.200"],
                kind="ITEM",
                path=["Dưới 12 tháng"],
            ),
            _row(
                "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ["18.300", "7.200"],
                kind="ITEM",
                path=["Mệnh giá chứng chỉ tiền gửi bằng VND"],
            ),
            _row(
                "Từ 12 tháng đến dưới 5 năm",
                ["1.780", "3.680"],
                kind="ITEM",
                path=["Từ 12 tháng đến dưới 5 năm"],
            ),
            _row(
                "Mệnh giá chứng chỉ tiền gửi bằng VND",
                ["200", "-"],
                kind="ITEM",
                path=["Mệnh giá chứng chỉ tiền gửi bằng VND"],
            ),
            _row(
                "Mệnh giá trái phiếu bằng VND",
                ["1.580", "3.680"],
                kind="ITEM",
                path=["Mệnh giá trái phiếu bằng VND"],
            ),
            _row(
                "Chi phí phát hành",
                ["-", "-"],
                kind="ITEM",
                path=["Chi phí phát hành"],
            ),
            _row(
                "Tổng cộng",
                ["20.080", "10.880"],
                kind="TOTAL",
                path=["Tổng cộng"],
            ),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page([])
    page["sections"][1]["tables"] = [table]
    return page


def test_flattened_tenor_carrier_projection_maps_instruments_and_restores_paths() -> None:
    page = _flattened_tenor_carrier_page()
    candidate, replay = _evaluate_with_repairs(page)
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert {"CD_SHORT", "CD_MEDIUM", "BOND_MEDIUM"} <= set(by_role)
    assert by_role["CD_SHORT"]["source_refs"][0]["hierarchy_path_exact"] == [
        "Mệnh giá chứng chỉ tiền gửi bằng VND"
    ]
    assert by_role["CD_MEDIUM"]["source_refs"][0]["hierarchy_path_exact"] == [
        "Mệnh giá chứng chỉ tiền gửi bằng VND"
    ]
    assert by_role["BOND_MEDIUM"]["source_refs"][0]["hierarchy_path_exact"] == [
        "Mệnh giá trái phiếu bằng VND"
    ]
    adapter = candidate["closure_receipt"][
        "issued_valuable_papers_adapter_receipt"
    ]
    projection_receipts = adapter["tenor_instrument_projection_receipts"]
    assert len(projection_receipts) == 1
    assert len(projection_receipts[0]["projections"]) == 3
    assert all(
        "values_exact" not in projection
        for projection in projection_receipts[0]["projections"]
    )
    assert (
        validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
            candidate,
            regions=replay["regions"],
            page_json_by_version={VERSION_ID: page},
            compiled_specs=replay["compiled_specs"],
            query_receipt=replay["query_receipt"],
        )
        == candidate
    )


@pytest.mark.parametrize("failure_kind", ["intervening_row", "conflicting_path"])
def test_tenor_carrier_projection_requires_adjacent_flattened_source_rows(
    failure_kind: str,
) -> None:
    page = _flattened_tenor_carrier_page()
    rows = page["sections"][1]["tables"][0]["rows"]
    if failure_kind == "intervening_row":
        rows.insert(
            1,
            _row(
                "Dòng xen kẽ không xác định",
                ["-", "-"],
                kind="ITEM",
                path=["Dòng xen kẽ không xác định"],
            ),
        )
    else:
        rows[1]["hierarchy_path_exact"] = [
            "Dưới 12 tháng",
            "Từ 12 tháng đến dưới 5 năm",
            "Mệnh giá chứng chỉ tiền gửi bằng VND",
        ]
    candidate, _replay = _evaluate_with_repairs(page)
    adapter = candidate["closure_receipt"][
        "issued_valuable_papers_adapter_receipt"
    ]
    projections = adapter["tenor_instrument_projection_receipts"][0]["projections"]
    assert "CD_SHORT" not in {projection["child_role"] for projection in projections}


def test_exact_visible_dash_transcription_token_is_repaired_but_near_token_is_not() -> None:
    page = _face_value_wrapper_page(short_current="- 特別")
    candidate, _replay = _evaluate_with_repairs(page)
    assert candidate["status"] == READY
    adapter = candidate["closure_receipt"][
        "issued_valuable_papers_adapter_receipt"
    ]
    assert adapter["visible_dash_transcription_repairs"] == [
        {
            "after_source_text": "-",
            "before_source_text": "- 特別",
            "column_ordinal": 1,
            "locator": {
                "page_json_version_id": VERSION_ID,
                "physical_page": 1,
                "section_id": "s2",
                "table_id": "t1",
            },
            "row_ordinal": 3,
            "rule": "EXACT_PDF_VISIBLE_DASH_TRANSCRIPTION_TOKEN",
        }
    ]

    near = _face_value_wrapper_page(short_current="- 特別x")
    rejected, _replay = _evaluate_with_repairs(near)
    assert rejected["status"] == UNRESOLVED
    assert rejected["reasons"] == ["INVALID_VISIBLE_SOURCE_MONEY_CELL"]

    underscore = _face_value_wrapper_page(short_current="_")
    accepted, _replay = _evaluate_with_repairs(underscore)
    assert accepted["status"] == READY
    underscore_repairs = accepted["closure_receipt"][
        "issued_valuable_papers_adapter_receipt"
    ]["visible_dash_transcription_repairs"]
    assert underscore_repairs[0]["before_source_text"] == "_"
    assert underscore_repairs[0]["after_source_text"] == "-"


def _primary_root_page() -> dict:
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": "BALANCE_SHEET",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["Thuyết minh"],
                                "value_kind": "TEXT",
                            },
                            {
                                "header_path_exact": ["Cuối kỳ"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Đầu kỳ"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
                        "rows": [
                            _row(
                                "NỢ PHẢI TRẢ",
                                [None, None, None],
                                kind="GROUP",
                                path=["NỢ PHẢI TRẢ"],
                            ),
                            _row(
                                "VI. Phát hành giấy tờ có giá",
                                [None, "7", "3"],
                                kind="ITEM",
                                path=[
                                    "NỢ PHẢI TRẢ",
                                    "VI. Phát hành giấy tờ có giá",
                                ],
                            ),
                            _row(
                                "Tiền gửi khách hàng",
                                [None, "100", "90"],
                                kind="ITEM",
                                path=["NỢ PHẢI TRẢ", "Tiền gửi khách hàng"],
                            ),
                        ],
                        "title_exact": None,
                        "unit_exact": "Triệu đồng",
                    }
                ],
                "title_exact": "Báo cáo tình hình tài chính",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }


def _custom_indexed(clusters: list[dict], records: list[dict], compiled: dict) -> dict:
    documents = []
    seen_documents = set()
    selected_pages = []
    for record in records:
        document = {
            key: record[key]
            for key in (
                "document_id",
                "document_ordinal",
                "source_logical_name",
                "source_sha256",
            )
        }
        identity = (document["document_id"], document["document_ordinal"])
        if identity not in seen_documents:
            documents.append(document)
            seen_documents.add(identity)
        selected_pages.append(
            {
                **document,
                "page_json_version_id": record["page_json_version_id"],
                "physical_page": record["physical_page"],
                "selected_page_ordinal": record["selected_page_ordinal"],
            }
        )
    return build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=documents,
        selected_page_axis=selected_pages,
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )


def test_unshadowed_primary_statement_root_is_mapped_with_raw_source_identity() -> None:
    page = _primary_root_page()
    compiled = _compiled()
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert raw_cluster["status"] == NOT_OBSERVED
    adapted, receipts = (
        adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
            _indexed(raw_cluster),
            page_json_by_document={1: {VERSION_ID: page}},
            compiled_specs=compiled,
        )
    )
    assert len(receipts) == 1
    assert receipts[0]["non_primary_direct_family_candidate_axis"] == []
    region = adapted["accepted_clusters"][0]["component_regions"][0]
    query_receipt = build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
        [region]
    )
    candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
        regions=[region],
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )
    assert candidate["status"] == READY
    assert [mapping["role"] for mapping in candidate["mappings"]] == [
        "FAMILY_ROOT_TOTAL"
    ]
    mapping = candidate["mappings"][0]
    assert [cell["coefficient"] for cell in mapping["values"]] == [7, 3]
    assert {ref["row_ordinal"] for ref in mapping["source_refs"]} == {2}
    assert {ref["row_kind"] for ref in mapping["source_refs"]} == {"ITEM"}
    adapter = candidate["closure_receipt"][
        "issued_valuable_papers_adapter_receipt"
    ]
    assert (
        adapter["primary_root_projection_receipt"][
            "primary_root_query_receipt_id"
        ]
        == receipts[0]["primary_root_query_receipt_id"]
    )


def test_primary_root_projection_rejects_duplicate_and_detects_source_tamper() -> None:
    page = _primary_root_page()
    compiled = _compiled()
    region = {
        key: _record(page)[key]
        for key in (
            "document_id",
            "document_ordinal",
            "page_json_version_id",
            "physical_page",
            "selected_page_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    }
    region.update(
        {"component_roles": [], "fragment_ordinal": 1, "section_id": "s1", "table_id": "t1"}
    )
    projected = _primary_statement_exact_root_projection_v1(
        region=region,
        page_json_by_version={VERSION_ID: page},
        compiled_specs=compiled,
    )
    assert projected is not None
    _pages, receipt = projected
    page["sections"][0]["tables"][0]["rows"][1]["values_exact"][1] = "8"
    with pytest.raises(
        GeminiJsonIssuedValuablePapersFamilyV1Error,
        match="source shape drifted",
    ):
        _apply_primary_root_projection_receipt_v1(
            page_json_by_version={VERSION_ID: page}, receipt=receipt
        )

    duplicate = _primary_root_page()
    duplicate["sections"][0]["tables"][0]["rows"].append(
        copy.deepcopy(duplicate["sections"][0]["tables"][0]["rows"][1])
    )
    assert (
        _primary_statement_exact_root_projection_v1(
            region=region,
            page_json_by_version={VERSION_ID: duplicate},
            compiled_specs=compiled,
        )
        is None
    )


def test_internal_root_note_preempts_primary_root_fallback() -> None:
    primary = _primary_root_page()
    detail_version = "gfpstorev1:json:" + "7" * 64
    detail = {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            _section(
                "THUYẾT MINH BÁO CÁO TÀI CHÍNH",
                [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["Cuối kỳ"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Đầu kỳ"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [
                            _row(
                                "10. Phát hành giấy tờ có giá",
                                [None, None],
                                kind="GROUP",
                                path=["10. Phát hành giấy tờ có giá"],
                            ),
                            _row(
                                "Trái phiếu",
                                ["7", "3"],
                                kind="ITEM",
                                path=[
                                    "10. Phát hành giấy tờ có giá",
                                    "Trái phiếu",
                                ],
                            ),
                            _row(
                                "Tổng",
                                ["7", "3"],
                                kind="TOTAL",
                                path=["10. Phát hành giấy tờ có giá", "Tổng"],
                            ),
                        ],
                        "title_exact": None,
                        "unit_exact": "Triệu đồng",
                    }
                ],
            )
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    records = [
        _record(primary),
        {
            **_record(detail),
            "page_json": detail,
            "page_json_version_id": detail_version,
            "physical_page": 2,
            "selected_page_ordinal": 2,
        },
    ]
    compiled = _compiled()
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    adapted, receipts = (
        adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
            _custom_indexed([raw_cluster], records, compiled),
            page_json_by_document={
                1: {VERSION_ID: primary, detail_version: detail}
            },
            compiled_specs=compiled,
        )
    )
    assert len(adapted["accepted_clusters"]) == 1
    assert len(receipts) == 1
    assert receipts[0]["format_version"] == (
        "GEMINI_JSON_ISSUED_VALUABLE_PAPERS_INTERNAL_ROOT_ROW_QUERY_RECEIPT_V1"
    )
    region = adapted["accepted_clusters"][0]["component_regions"][0]
    assert region["page_json_version_id"] == detail_version
    assert region["physical_page"] == 2
    query_receipt = build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
        [region]
    )
    candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
        regions=[region],
        page_json_by_version={VERSION_ID: primary, detail_version: detail},
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )
    assert candidate["status"] == READY
    root = next(
        mapping
        for mapping in candidate["mappings"]
        if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [cell["coefficient"] for cell in root["values"]] == [7, 3]
    assert {ref["locator"]["page_json_version_id"] for ref in root["source_refs"]} == {
        detail_version
    }
    assert {ref["row_ordinal"] for ref in root["source_refs"]} == {3}


def test_primary_root_recovery_ignores_validation_only_noise_in_unrelated_note() -> None:
    primary = _primary_root_page()
    detail_version = "gfpstorev1:json:" + "6" * 64
    detail = {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            _section(
                "6. Cho vay khách hàng",
                [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["Cuối kỳ"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Đầu kỳ"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [
                            _row(
                                "Bằng VND",
                                ["90", "80"],
                                kind="ITEM",
                                path=["Cho vay khách hàng", "Bằng VND"],
                            ),
                            _row(
                                "Tổng cộng",
                                ["90", "80"],
                                kind="TOTAL",
                                path=["Cho vay khách hàng", "Tổng cộng"],
                            ),
                        ],
                        "title_exact": None,
                        "unit_exact": "Triệu đồng",
                    }
                ],
            )
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    records = [
        _record(primary),
        {
            **_record(detail),
            "page_json": detail,
            "page_json_version_id": detail_version,
            "physical_page": 2,
            "selected_page_ordinal": 2,
        },
    ]
    compiled = _compiled()
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    adapted, receipts = (
        adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
            _custom_indexed([raw_cluster], records, compiled),
            page_json_by_document={
                1: {VERSION_ID: primary, detail_version: detail}
            },
            compiled_specs=compiled,
        )
    )
    assert len(adapted["accepted_clusters"]) == 1
    assert len(receipts) == 1
    assert receipts[0]["non_primary_direct_family_candidate_axis"] == []


def test_primary_root_recovery_ignores_explicit_currency_risk_control() -> None:
    primary = _primary_root_page()
    risk_version = "gfpstorev1:json:" + "8" * 64
    risk = {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            _section(
                "39.3 Rủi ro tiền tệ",
                [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["VND"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Tổng"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [
                            _row(
                                "Phát hành giấy tờ có giá",
                                ["7", "7"],
                                kind="ITEM",
                                path=[
                                    "Nợ phải trả",
                                    "Phát hành giấy tờ có giá",
                                ],
                            )
                        ],
                        "title_exact": None,
                        "unit_exact": "Triệu đồng",
                    }
                ],
            )
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    records = [
        _record(primary),
        {
            **_record(risk),
            "page_json": risk,
            "page_json_version_id": risk_version,
            "physical_page": 2,
            "selected_page_ordinal": 2,
        },
    ]
    compiled = _compiled()
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    risk_item = next(
        item
        for item in raw_cluster["declared_money_table_inventory"]
        if item["page_json_version_id"] == risk_version
    )
    assert (
        risk_item["classification"]["typed_control_disposition"]
        == "MATURITY_OR_RISK_ANALYSIS_CONTROL_OUTSIDE_FAMILY_SOURCE"
    )
    adapted, receipts = (
        adapt_gemini_json_issued_valuable_papers_indexed_query_evidence_v1(
            _custom_indexed([raw_cluster], records, compiled),
            page_json_by_document={1: {VERSION_ID: primary, risk_version: risk}},
            compiled_specs=compiled,
        )
    )
    assert len(adapted["accepted_clusters"]) == 1
    assert len(receipts) == 1
    assert receipts[0]["non_primary_direct_family_candidate_axis"] == []


def _family_compiled_without_repairs() -> dict:
    return compile_gemini_json_issued_valuable_papers_family_specs_v1(
        _json("tm-issued-valuable-papers-topology-v1.json"),
        _json("tm-issued-valuable-papers-evaluation-v1.json"),
        _json("tm-issued-valuable-papers-schema-binding-v1.json"),
        _repair_spec(),
    )


def _adjacent_generic_root_fixture() -> tuple[dict[str, dict], list[dict]]:
    sender_version = "gfpstorev1:json:" + "a" * 64
    receiver_version = "gfpstorev1:json:" + "b" * 64
    columns = [
        {"header_path_exact": ["Cuối kỳ"], "value_kind": "MONEY"},
        {"header_path_exact": ["Đầu kỳ"], "value_kind": "MONEY"},
    ]
    sender_table = {
        "columns": copy.deepcopy(columns),
        "continuation": "CONTINUES_ON_NEXT_PAGE",
        "rows": [
            _row(
                "- Kỳ hạn dưới 1 năm",
                ["3", "1"],
                kind="ITEM",
                path=["- Kỳ hạn dưới 1 năm"],
            ),
            _row(
                "- Kỳ hạn 1 tới năm 5 năm",
                ["-", "1"],
                kind="ITEM",
                path=["- Kỳ hạn 1 tới năm 5 năm"],
            ),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    receiver_table = {
        "columns": [
            {"header_path_exact": [None], "value_kind": "MONEY"},
            {"header_path_exact": [None], "value_kind": "MONEY"},
        ],
        "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
        "rows": [
            _row(
                "- Kỳ hạn trên 5 năm",
                ["1", "1"],
                kind="ITEM",
                path=["- Kỳ hạn trên 5 năm"],
            ),
            _row(None, ["4", "3"], kind="TOTAL", path=[None]),
        ],
        "title_exact": None,
        "unit_exact": None,
    }
    pages = {
        sender_version: {
            "completion": {
                "all_relevant_content_transcribed": True,
                "uncertainty_exact": [],
            },
            "sections": [
                _section("17. Phát hành giấy tờ có giá", [sender_table])
            ],
            "status": "FINANCIAL_NOTE_CONTENT",
        },
        receiver_version: {
            "completion": {
                "all_relevant_content_transcribed": True,
                "uncertainty_exact": [],
            },
            "sections": [_section(None, [receiver_table])],
            "status": "FINANCIAL_NOTE_CONTENT",
        },
    }
    base = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    regions = [
        {
            **base,
            "component_roles": ["GENERIC_ISSUED_PAPER_SOURCE"],
            "fragment_ordinal": 1,
            "page_json_version_id": sender_version,
            "physical_page": 10,
            "section_id": "s1",
            "selected_page_ordinal": 10,
            "table_id": "t1",
        },
        {
            **base,
            "component_roles": ["GENERIC_ISSUED_PAPER_SOURCE"],
            "fragment_ordinal": 2,
            "page_json_version_id": receiver_version,
            "physical_page": 11,
            "section_id": "s1",
            "selected_page_ordinal": 11,
            "table_id": "t1",
        },
    ]
    return pages, regions


def test_adjacent_generic_bucket_population_maps_only_visible_family_root() -> None:
    pages, regions = _adjacent_generic_root_fixture()
    compiled = _family_compiled_without_repairs()
    query_receipt = build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
        regions
    )
    candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )

    assert candidate["status"] == READY
    assert [mapping["role"] for mapping in candidate["mappings"]] == [
        "FAMILY_ROOT_TOTAL"
    ]
    assert [cell["coefficient"] for cell in candidate["mappings"][0]["values"]] == [
        4,
        3,
    ]
    source_ref = candidate["mappings"][0]["source_refs"][0]
    assert source_ref["label_exact"] is None
    assert source_ref["hierarchy_path_exact"] == [None]
    assert source_ref["row_ordinal"] == 2
    adapter_receipt = candidate["closure_receipt"][
        "issued_valuable_papers_adapter_receipt"
    ]
    assert any(
        projection["projection_kind"]
        == (
            "TITLELESS_RECEIVER_TOTAL_SCOPED_BY_EXACT_ADJACENT_OWNER_AND_"
            "ALL_LANE_GENERIC_BUCKET_EQUATION"
        )
        for receipt in adapter_receipt[
            "adjacent_source_syntax_projection_receipts"
        ]
        for projection in receipt["table_projections"]
    )
    validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
        candidate,
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )


@pytest.mark.parametrize("drift", ["owner", "nonadjacent", "reset", "equation"])
def test_adjacent_generic_root_recovery_fails_closed_on_scope_drift(
    drift: str,
) -> None:
    pages, regions = _adjacent_generic_root_fixture()
    sender = pages[regions[0]["page_json_version_id"]]
    receiver = pages[regions[1]["page_json_version_id"]]
    if drift == "owner":
        sender["sections"][0]["title_exact"] = "17. Vốn và các quỹ"
    elif drift == "nonadjacent":
        regions[1]["physical_page"] = 12
    elif drift == "reset":
        receiver["sections"][0]["title_exact"] = "Vốn và các quỹ"
    else:
        receiver["sections"][0]["tables"][0]["rows"][-1]["values_exact"][0] = "5"

    _projected_pages, projected_regions, receipts = (
        _project_adjacent_source_syntax_v1(
            pages=pages,
            regions=regions,
            compiled_specs=_family_compiled_without_repairs(),
        )
    )
    assert len(projected_regions) == 2
    assert not any(
        projection.get("projection_kind")
        == (
            "TITLELESS_RECEIVER_TOTAL_SCOPED_BY_EXACT_ADJACENT_OWNER_AND_"
            "ALL_LANE_GENERIC_BUCKET_EQUATION"
        )
        for receipt in receipts
        for projection in receipt["table_projections"]
    )


def _combined_stb_maturity_fixture() -> tuple[dict[str, dict], list[dict]]:
    version = "gfpstorev1:json:" + "c" * 64
    table = {
        "columns": [
            {"header_path_exact": ["Cuối kỳ"], "value_kind": "MONEY"},
            {"header_path_exact": ["Đầu năm"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Phát hành trái phiếu theo thời gian (*)",
                [None, None],
                kind="GROUP",
                path=["Phát hành trái phiếu theo thời gian (*)"],
            ),
            _row(
                "Dưới 1 năm",
                ["-", " - "],
                kind="ITEM",
                path=["Phát hành trái phiếu theo thời gian (*)", "Dưới 1 năm"],
            ),
            _row(
                "Từ 1 đến 5 năm",
                ["5", "5"],
                kind="ITEM",
                path=[
                    "Phát hành trái phiếu theo thời gian (*)",
                    "Từ 1 đến 5 năm",
                ],
            ),
            _row(
                "Trên 5 năm",
                ["-", " - "],
                kind="ITEM",
                path=["Phát hành trái phiếu theo thời gian (*)", "Trên 5 năm"],
            ),
            _row(
                "Cộng",
                ["5", "5"],
                kind="TOTAL",
                path=["Phát hành trái phiếu theo thời gian (*)", "Cộng"],
            ),
            _row(
                "Phát hành GTCG theo thời gian",
                [None, None],
                kind="GROUP",
                path=["Phát hành GTCG theo thời gian"],
            ),
            _row(
                "Dưới 1 năm",
                ["1", "2"],
                kind="ITEM",
                path=["Phát hành GTCG theo thời gian", "Dưới 1 năm"],
            ),
            _row(
                "Từ 1 đến 5 năm",
                ["2", "3"],
                kind="ITEM",
                path=["Phát hành GTCG theo thời gian", "Từ 1 đến 5 năm"],
            ),
            _row(
                "Trên 5 năm",
                ["3", "4"],
                kind="ITEM",
                path=["Phát hành GTCG theo thời gian", "Trên 5 năm"],
            ),
            _row(
                "Cộng",
                ["6", "9"],
                kind="TOTAL",
                path=["Phát hành GTCG theo thời gian", "Cộng"],
            ),
            _row("Tổng", ["11", "14"], kind="TOTAL", path=["Tổng"]),
        ],
        "title_exact": "10 Phát hành giấy tờ có giá :",
        "unit_exact": "Triệu đồng",
    }
    page = {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [_section(None, [table])],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    region = {
        "component_roles": [
            "BOND",
            "BOND_LONG",
            "BOND_MEDIUM",
            "BOND_SHORT",
            "GENERIC_ISSUED_PAPER_SOURCE",
        ],
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "fragment_ordinal": 1,
        "page_json_version_id": version,
        "physical_page": 10,
        "section_id": "s1",
        "selected_page_ordinal": 10,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
        "table_id": "t1",
    }
    return {version: page}, [region]


def test_combined_bond_and_gtcg_maturity_syntax_maps_direct_source_population() -> None:
    pages, regions = _combined_stb_maturity_fixture()
    compiled = _family_compiled_without_repairs()
    query_receipt = build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
        regions
    )
    candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )

    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "BOND",
        "BOND_LONG",
        "BOND_MEDIUM",
        "BOND_SHORT",
        "CD_LONG",
        "CD_MEDIUM",
        "CD_SHORT",
        "CERTIFICATE_OF_DEPOSIT",
        "FAMILY_ROOT_TOTAL",
    }
    root = next(
        mapping
        for mapping in candidate["mappings"]
        if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [cell["coefficient"] for cell in root["values"]] == [11, 14]
    assert root["source_refs"][0]["label_exact"] == "Tổng"
    validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
        candidate,
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )


def _combined_stb_maturity_with_leading_owner_fixture() -> (
    tuple[dict[str, dict], list[dict]]
):
    pages, regions = _combined_stb_maturity_fixture()
    table = pages[regions[0]["page_json_version_id"]]["sections"][0]["tables"][0]
    owner = table["title_exact"]
    table["title_exact"] = None
    for row in table["rows"]:
        row["hierarchy_path_exact"] = [owner, *row["hierarchy_path_exact"]]
    table["rows"][4]["row_kind"] = "SUBTOTAL"
    table["rows"][9]["row_kind"] = "SUBTOTAL"
    table["rows"].insert(
        0,
        _row(owner, [None, None], kind="GROUP", path=[owner]),
    )
    return pages, regions


def test_combined_maturity_leading_owner_maps_visible_parent_and_root_rows() -> None:
    pages, regions = _combined_stb_maturity_with_leading_owner_fixture()
    compiled = _family_compiled_without_repairs()
    query_receipt = build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
        regions
    )
    candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )

    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "BOND",
        "BOND_LONG",
        "BOND_MEDIUM",
        "BOND_SHORT",
        "CD_LONG",
        "CD_MEDIUM",
        "CD_SHORT",
        "CERTIFICATE_OF_DEPOSIT",
        "FAMILY_ROOT_TOTAL",
    }
    parent_and_root_refs = {
        mapping["role"]: mapping["source_refs"][0]
        for mapping in candidate["mappings"]
        if mapping["role"]
        in {"BOND", "CERTIFICATE_OF_DEPOSIT", "FAMILY_ROOT_TOTAL"}
    }
    assert {
        role: (ref["row_ordinal"], ref["label_exact"], ref["row_kind"])
        for role, ref in parent_and_root_refs.items()
    } == {
        "BOND": (6, "Cộng", "SUBTOTAL"),
        "CERTIFICATE_OF_DEPOSIT": (11, "Cộng", "SUBTOTAL"),
        "FAMILY_ROOT_TOTAL": (12, "Tổng", "TOTAL"),
    }
    assert not any(
        ref["row_ordinal"] == 1
        for mapping in candidate["mappings"]
        for ref in mapping["source_refs"]
    )
    receipts = candidate["closure_receipt"][
        "issued_valuable_papers_adapter_receipt"
    ]["maturity_validation_projection_receipts"]
    assert len(receipts) == 1
    projection = receipts[0]["table_projections"][0]
    assert projection["leading_owner_row_ordinal"] == 1
    assert projection["source_owner_alias"] == "phat hanh giay to co gia"
    assert projection["source_row_ordinals"] == {
        "bond_children": [3, 4, 5],
        "bond_group": 2,
        "bond_total": 6,
        "cd_children": [8, 9, 10],
        "cd_group": 7,
        "cd_total": 11,
        "family_total": 12,
    }
    assert projection["raw_source_rows"] == pages[
        regions[0]["page_json_version_id"]
    ]["sections"][0]["tables"][0]["rows"]
    validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
        candidate,
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )


@pytest.mark.parametrize(
    "drift",
    ["owner", "owner_value", "bond_total", "hierarchy", "shape", "nonterminal"],
)
def test_combined_maturity_leading_owner_fails_closed_on_source_drift(
    drift: str,
) -> None:
    pages, regions = _combined_stb_maturity_with_leading_owner_fixture()
    table = pages[regions[0]["page_json_version_id"]]["sections"][0]["tables"][0]
    rows = table["rows"]
    if drift == "owner":
        rows[0]["label_exact"] = "17. Vốn và các quỹ"
        rows[0]["hierarchy_path_exact"] = ["17. Vốn và các quỹ"]
    elif drift == "owner_value":
        rows[0]["values_exact"] = ["-", "-"]
    elif drift == "bond_total":
        rows[5]["values_exact"][0] = "6"
    elif drift == "hierarchy":
        rows[11]["hierarchy_path_exact"].insert(1, "Tiểu mục khác")
    elif drift == "shape":
        rows[5]["row_kind"] = "TOTAL"
    else:
        rows.append(
            _row(
                "Thuyết minh kiểm soát",
                [None, None],
                kind="GROUP",
                path=["Thuyết minh kiểm soát"],
            )
        )

    _projected_pages, _projected_regions, receipts = (
        _project_maturity_context_and_prune_validations_v1(
            pages=pages,
            regions=regions,
            compiled_specs=_family_compiled_without_repairs(),
        )
    )
    assert not any(receipt.get("table_projections") for receipt in receipts)


@pytest.mark.parametrize("drift", ["bond_total", "cd_total", "root_total", "shape"])
def test_combined_maturity_syntax_requires_every_exact_source_equation(
    drift: str,
) -> None:
    pages, regions = _combined_stb_maturity_fixture()
    rows = pages[regions[0]["page_json_version_id"]]["sections"][0]["tables"][0][
        "rows"
    ]
    if drift == "bond_total":
        rows[4]["values_exact"][0] = "6"
    elif drift == "cd_total":
        rows[9]["values_exact"][0] = "7"
    elif drift == "root_total":
        rows[10]["values_exact"][0] = "12"
    else:
        rows[9]["row_kind"] = "SUBTOTAL"

    _projected_pages, _projected_regions, receipts = (
        _project_maturity_context_and_prune_validations_v1(
            pages=pages,
            regions=regions,
            compiled_specs=_family_compiled_without_repairs(),
        )
    )
    assert not any(receipt.get("table_projections") for receipt in receipts)


def _abb_three_face_value_block_page(
    *,
    cd_medium_comparative: str | None = None,
    root_current: str = "11",
) -> dict:
    rows = [
        _row("Trái phiếu", [None, None], kind="GROUP", path=["Trái phiếu"]),
        _row(
            "- Mệnh giá",
            ["5", "4"],
            kind="SUBTOTAL",
            path=[
                "Trái phiếu CPU/General/Placeholder? No visible sub header? "
                "Keep direct:",
                "Trái phiếu",
                "- Mệnh giá",
            ],
        ),
        _row(
            "+ Kỳ hạn dưới 12 tháng",
            ["-", "-"],
            kind="ITEM",
            path=["Trái phiếu", "- Mệnh giá", "+ Kỳ hạn dưới 12 tháng"],
        ),
        _row(
            "+ Kỳ hạn từ 12 tháng đến dưới 5 năm",
            ["4", "3"],
            kind="ITEM",
            path=[
                "Trái phiếu",
                "- Mệnh giá",
                "+ Kỳ hạn từ 12 tháng đến dưới 5 năm",
            ],
        ),
        _row(
            "+ Kỳ hạn từ 5 năm trở lên",
            ["1", "1"],
            kind="ITEM",
            path=[
                "Trái phiếu",
                "- Mệnh giá",
                "+ Kỳ hạn từ 5 năm trở lên",
            ],
        ),
        _row("Kỳ phiếu", [None, None], kind="GROUP", path=["Kỳ phiếu"]),
        _row(
            "- Mệnh giá",
            ["-", "-"],
            kind="SUBTOTAL",
            path=["Kỳ phiếu", "- Mệnh giá"],
        ),
        _row(
            "+ Kỳ hạn dưới 12 tháng",
            ["-", "-"],
            kind="ITEM",
            path=["Kỳ phiếu", "- Mệnh giá", "+ Kỳ hạn dưới 12 tháng"],
        ),
        _row(
            "+ Kỳ hạn từ 12 tháng đến dưới 5 năm",
            ["-", "-"],
            kind="ITEM",
            path=[
                "Kỳ phiếu",
                "- Mệnh giá",
                "+ Kỳ hạn từ 12 tháng đến dưới 5 năm",
            ],
        ),
        _row(
            "+ Kỳ hạn từ 5 năm trở lên",
            ["-", "-"],
            kind="ITEM",
            path=[
                "Kỳ phiếu",
                "- Mệnh giá",
                "+ Kỳ hạn từ 5 năm trở lên",
            ],
        ),
        _row(
            "Chứng chỉ tiền gửi",
            [None, None],
            kind="GROUP",
            path=["Chứng chỉ tiền gửi"],
        ),
        _row(
            "- Mệnh giá",
            ["6", "5"],
            kind="SUBTOTAL",
            path=["Chứng chỉ tiền gửi", "- Mệnh giá"],
        ),
        _row(
            "+ Kỳ hạn dưới 12 tháng",
            ["5", "5"],
            kind="ITEM",
            path=[
                "Chứng chỉ tiền gửi",
                "- Mệnh giá",
                "+ Kỳ hạn dưới 12 tháng",
            ],
        ),
        _row(
            "+ Kỳ hạn từ 12 tháng đến dưới 5 năm",
            ["1", cd_medium_comparative],
            kind="ITEM",
            path=[
                "Chứng chỉ tiền gửi",
                "- Mệnh giá",
                "+ Kỳ hạn từ 12 tháng đến dưới 5 năm",
            ],
        ),
        _row(
            "+ Kỳ hạn từ 5 năm trở lên",
            ["-", "-"],
            kind="ITEM",
            path=[
                "Chứng chỉ tiền gửi",
                "- Mệnh giá",
                "+ Kỳ hạn từ 5 năm trở lên",
            ],
        ),
        _row("Tổng", [root_current, "9"], kind="TOTAL", path=["Tổng"]),
    ]
    page = _page([])
    page["sections"][1]["tables"] = [
        {
            "columns": [
                {"header_path_exact": ["Cuối kỳ"], "value_kind": "MONEY"},
                {"header_path_exact": ["Đầu kỳ"], "value_kind": "MONEY"},
            ],
            "continuation": "NONE",
            "rows": rows,
            "title_exact": None,
            "unit_exact": "Triệu đồng",
        }
    ]
    return page


def test_three_face_value_blocks_map_visible_parents_without_backsolving_blank_lane() -> None:
    page = _abb_three_face_value_block_page()
    candidate, replay = _evaluate_with_repairs(page)

    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert by_role["CD_MEDIUM"]["values"][1] == {
        "coefficient": None,
        "source_text": None,
        "state": "BLANK_SOURCE_CELL",
    }
    assert by_role["CD_MEDIUM"]["state"] == "PARTIAL_SOURCE_OBSERVATION"
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        11,
        9,
    ]
    assert by_role["BOND"]["source_refs"][0]["label_exact"] == "- Mệnh giá"
    assert by_role["BOND"]["source_refs"][0]["hierarchy_path_exact"] == [
        "Trái phiếu CPU/General/Placeholder? No visible sub header? Keep direct:",
        "Trái phiếu",
        "- Mệnh giá",
    ]
    adapter = candidate["closure_receipt"][
        "issued_valuable_papers_adapter_receipt"
    ]
    table_projection = adapter["face_value_wrapper_receipts"][0][
        "table_projections"
    ][0]
    assert table_projection["complete_lane_equations"] == [
        {
            "component_coefficients": [5, 0, 6],
            "component_sum": 11,
            "lane_ordinal": 1,
            "root_coefficient": 11,
            "status": "EXACT",
        },
        {
            "component_coefficients": [4, 0, 5],
            "component_sum": 9,
            "lane_ordinal": 2,
            "root_coefficient": 9,
            "status": "EXACT",
        },
    ]
    assert (
        validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
            candidate,
            regions=replay["regions"],
            page_json_by_version={VERSION_ID: page},
            compiled_specs=replay["compiled_specs"],
            query_receipt=replay["query_receipt"],
        )
        == candidate
    )


def test_three_face_value_block_projection_requires_visible_terminal_root_equation() -> None:
    page = _abb_three_face_value_block_page(root_current="12")
    compiled = _family_compiled_without_repairs()
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )

    projected_pages, _regions, receipts = _project_face_value_wrappers(
        pages={VERSION_ID: page},
        regions=cluster["component_regions"],
        compiled_specs=compiled,
    )

    assert not any(receipt["table_projections"] for receipt in receipts)
    projected_rows = projected_pages[VERSION_ID]["sections"][1]["tables"][0]["rows"]
    assert projected_rows[0]["label_exact"] == "Trái phiếu"
    assert projected_rows[1]["label_exact"] == "- Mệnh giá"


def _shb_repeated_summary_fixture() -> tuple[dict[str, dict], list[dict]]:
    version = "gfpstorev1:json:" + "d" * 64
    summary = {
        "columns": [
            {"header_path_exact": ["Số cuối năm", "Triệu VND"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số đầu năm", "Triệu VND"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Giấy tờ có giá bằng VND",
                ["53.096.625", "39.248.195"],
                kind="ITEM",
                path=["Giấy tờ có giá bằng VND"],
            ),
            _row(
                "Mệnh giá",
                ["53.096.625", "39.248.195"],
                kind="TOTAL",
                path=["Mệnh giá"],
            ),
            _row(
                None,
                ["53.096.625", "39.248.195"],
                kind="TOTAL",
                path=[None],
            ),
        ],
        "title_exact": None,
        "unit_exact": "Triệu VND",
    }
    detail_rows = []
    for owner, vectors in (
        (
            "Số dư cuối năm",
            [
                ("Dưới 12 tháng", ["-", "18.000.000", "18.000.000"]),
                ("Từ 12 tháng đến dưới 5 năm", ["2.000.000", "13", "2.000.013"]),
                ("Từ 5 năm trở lên", ["13.030.000", "20.066.612", "33.096.612"]),
            ],
        ),
        (
            "Số dư đầu năm",
            [
                ("Dưới 12 tháng", ["-", "12.500.000", "12.500.000"]),
                ("Từ 12 tháng đến dưới 5 năm", ["4.000.000", "12", "4.000.012"]),
                ("Từ 5 năm trở lên", ["2.448.100", "20.300.083", "22.748.183"]),
            ],
        ),
    ):
        detail_rows.append(_row(owner, [None] * 3, kind="GROUP", path=[owner]))
        for label, values in vectors:
            detail_rows.extend(
                [
                    _row(label, values, kind="ITEM", path=[owner, label]),
                    _row(
                        "- Bằng VND",
                        values,
                        kind="ITEM",
                        path=[owner, label, "- Bằng VND"],
                    ),
                ]
            )
        detail_rows.append(
            _row(
                None,
                ["15.030.000", "38.066.625", "53.096.625"]
                if owner == "Số dư cuối năm"
                else ["6.448.100", "32.800.095", "39.248.195"],
                kind="TOTAL",
                path=[owner, None],
            )
        )
    detail = {
        "columns": [
            {"header_path_exact": ["Trái phiếu", "Triệu VND"], "value_kind": "MONEY"},
            {
                "header_path_exact": ["Chứng chỉ tiền gửi", "Triệu VND"],
                "value_kind": "MONEY",
            },
            {"header_path_exact": ["Tổng cộng", "Triệu VND"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": detail_rows,
        "title_exact": "Chi tiết kỳ hạn của các giấy tờ có giá phát hành:",
        "unit_exact": "Triệu VND",
    }
    page = {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [_section("22. PHÁT HÀNH GIẤY TỜ CÓ GIÁ", [summary, detail])],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    base = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json_version_id": version,
        "physical_page": 45,
        "section_id": "s1",
        "selected_page_ordinal": 45,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    return {version: page}, [
        {
            **base,
            "component_roles": ["GENERIC_ISSUED_PAPER_SOURCE"],
            "fragment_ordinal": 1,
            "table_id": "t1",
        },
        {
            **base,
            "component_roles": [
                "BOND",
                "BOND_LONG",
                "BOND_MEDIUM",
                "BOND_SHORT",
                "CD_LONG",
                "CD_MEDIUM",
                "CD_SHORT",
                "CERTIFICATE_OF_DEPOSIT",
                "GENERIC_ISSUED_PAPER_SOURCE",
            ],
            "fragment_ordinal": 2,
            "table_id": "t2",
        },
    ]


def test_repeated_face_value_summary_is_pruned_before_complete_shb_detail() -> None:
    pages, regions = _shb_repeated_summary_fixture()
    compiled = _family_compiled_without_repairs()
    query_receipt = build_gemini_json_issued_valuable_papers_region_query_receipt_v1(
        regions
    )
    candidate = evaluate_gemini_json_issued_valuable_papers_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )

    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "BOND",
        "BOND_LONG",
        "BOND_MEDIUM",
        "BOND_SHORT",
        "CD_LONG",
        "CD_MEDIUM",
        "CD_SHORT",
        "CERTIFICATE_OF_DEPOSIT",
        "FAMILY_ROOT_TOTAL",
    }
    root = next(
        mapping
        for mapping in candidate["mappings"]
        if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [cell["coefficient"] for cell in root["values"]] == [
        53096625,
        39248195,
    ]
    adapter = candidate["closure_receipt"][
        "issued_valuable_papers_adapter_receipt"
    ]
    assert any(
        receipt["rule"]
        == (
            "EXACT_REPEATED_FACE_VALUE_SUMMARY_PRUNED_BEFORE_ADJACENT_"
            "COMPLETE_TRANSPOSED_BOND_CD_MATURITY_PRESENTATION"
        )
        for receipt in adapter["maturity_validation_projection_receipts"]
    )
    validate_gemini_json_issued_valuable_papers_family_candidate_replay_v1(
        candidate,
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )


def test_repeated_face_value_summary_is_not_pruned_when_detail_root_differs() -> None:
    pages, regions = _shb_repeated_summary_fixture()
    page = pages[regions[0]["page_json_version_id"]]
    page["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "53.096.624"

    _projected_pages, projected_regions, receipts = (
        _project_maturity_context_and_prune_validations_v1(
            pages=pages,
            regions=regions,
            compiled_specs=_family_compiled_without_repairs(),
        )
    )

    assert len(projected_regions) == 2
    assert not any(
        receipt["rule"]
        == (
            "EXACT_REPEATED_FACE_VALUE_SUMMARY_PRUNED_BEFORE_ADJACENT_"
            "COMPLETE_TRANSPOSED_BOND_CD_MATURITY_PRESENTATION"
        )
        for receipt in receipts
    )
