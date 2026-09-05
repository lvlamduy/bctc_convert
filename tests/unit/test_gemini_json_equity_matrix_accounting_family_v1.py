from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import gemini_json_equity_matrix_accounting_family_v1 as subject
from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    GeminiJsonEquityMatrixAccountingFamilyV1Error,
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    classify_gemini_json_equity_matrix_table_v1,
    coalesce_gemini_json_equity_matrix_document_v1,
    compile_gemini_json_equity_matrix_family_specs_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
    validate_gemini_json_equity_matrix_family_candidate_replay_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "b" * 64
SOURCE_SHA256 = "c" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_equity_matrix_family_specs_v1(
        _json("tm-capital-and-funds-topology-v1.json"),
        _json("tm-capital-and-funds-evaluation-v1.json"),
        _json("tm-capital-and-funds-schema-binding-v1.json"),
    )


def _column(label: str) -> dict:
    return {"header_path_exact": [label], "value_kind": "MONEY"}


def _row(label: str | None, values: list[str | None], *, kind: str = "ITEM") -> dict:
    return {
        "hierarchy_path_exact": [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _component_column_table(
    *,
    opening: list[str | None] | None = None,
    details: list[list[str | None]] | None = None,
    closing: list[str | None] | None = None,
    unit: str | None = "Triệu đồng",
) -> dict:
    return {
        "columns": [
            _column("Vốn điều lệ"),
            _column("Thặng dư vốn cổ phần"),
            _column("Lợi ích cổ đông không kiểm soát"),
            _column("Tổng cộng"),
        ],
        "continuation": "NONE",
        "rows": [
            _row("Số dư đầu kỳ tại ngày 01/01/2025", opening or ["100", "20", "30", "150"]),
            *[
                _row(f"Biến động {ordinal}", values)
                for ordinal, values in enumerate(
                    details or [["10", " — ", "5", "15"], ["(5)", "_", "(2)", "(7)"]],
                    start=1,
                )
            ],
            _row("Số dư cuối kỳ tại ngày 31/12/2025", closing or ["105", "20", "33", "158"]),
        ],
        "title_exact": None,
        "unit_exact": unit,
    }


def _component_row_table() -> dict:
    return {
        "columns": [
            _column("Số dư đầu kỳ"),
            _column("Tăng trong kỳ"),
            _column("Giảm trong kỳ"),
            _column("Số dư cuối kỳ"),
        ],
        "continuation": "NONE",
        "rows": [
            _row("Vốn điều lệ", ["100", "10", "5", "105"]),
            _row("Thặng dư vốn cổ phần", ["20", "-", "-", "20"]),
            _row("Lợi nhuận sau thuế chưa phân phối", ["30", "5", "2", "33"]),
            _row("Tổng cộng", ["150", "15", "7", "158"], kind="TOTAL"),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _reciprocal_component_row_pages(*, blank_second_headers: bool = True) -> list[dict]:
    first = _component_row_table()
    first["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    first["rows"] = first["rows"][:2]
    second = _component_row_table()
    second["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    second["rows"] = [
        _row("Lợi nhuận sau thuế chưa phân phối", ["30", "5", "2", "33"]),
        _row("Quỹ dự trữ bổ sung vốn điều lệ", ["10", "1", "-", "11"]),
        _row("Tổng cộng", ["160", "16", "7", "169"], kind="TOTAL"),
    ]
    second["unit_exact"] = None
    if blank_second_headers:
        second["columns"] = [
            {"header_path_exact": [None], "value_kind": "MONEY"}
            for _column_item in second["columns"]
        ]
    return [
        _record(_page(_section("Vốn chủ sở hữu", first)), ordinal=1),
        _record(_page(_section("Tiếp theo", second)), ordinal=2),
    ]


def _primary_and_supplemental_fund_tables() -> tuple[dict, dict]:
    primary = {
        "columns": [
            _column("Vốn điều lệ"),
            _column("Quỹ của TCTD"),
            _column("Lợi nhuận chưa phân phối"),
            _column("Tổng cộng"),
        ],
        "continuation": "NONE",
        "rows": [
            _row("Số dư đầu kỳ", ["100", "30", "20", "150"]),
            _row("Tăng trong kỳ", ["10", "3", "2", "15"]),
            _row("Giảm trong kỳ", ["-", "-", "-", "-"]),
            _row("Số dư cuối kỳ", ["110", "33", "22", "165"]),
        ],
        "title_exact": "Báo cáo tình hình thay đổi vốn chủ sở hữu",
        "unit_exact": "Triệu đồng",
    }
    supplemental = {
        "columns": [
            _column("Quỹ dự trữ bổ sung vốn điều lệ"),
            _column("Quỹ dự phòng tài chính"),
            _column("Các quỹ khác"),
            _column("Tổng cộng"),
        ],
        "continuation": "NONE",
        "rows": [
            _row("Số dư đầu kỳ", ["10", "15", "5", "30"]),
            _row("Tăng trong kỳ", ["1", "2", "-", "3"]),
            _row("Giảm trong kỳ", ["-", "-", "-", "-"]),
            _row("Số dư cuối kỳ", ["11", "17", "5", "33"]),
        ],
        "title_exact": "(*) Các quỹ của Ngân hàng",
        "unit_exact": None,
    }
    return primary, supplemental


def _fund_period_snapshot(*, period: str, values: list[str]) -> dict:
    return {
        "columns": [
            {
                "header_path_exact": [period, label],
                "value_kind": "MONEY",
            }
            for label in (
                "Quỹ dự trữ bổ sung vốn điều lệ",
                "Quỹ dự phòng tài chính",
                "Các quỹ khác",
                "Tổng cộng",
            )
        ],
        "continuation": "NONE",
        "rows": [_row("Số dư đầu kỳ và cuối kỳ", values)],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _section(title: str, *tables: dict) -> dict:
    return {
        "content_kind": "FINANCIAL_NOTE",
        "narratives_exact": [],
        "statement_type": "NOT_APPLICABLE",
        "tables": list(tables),
        "title_exact": title,
    }


def _page(*sections: dict) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": list(sections),
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict, *, ordinal: int = 1) -> dict:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + f"{ordinal:064x}",
        "physical_page": ordinal,
        "selected_page_ordinal": ordinal,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate_records(records: list[dict]) -> tuple[dict, dict, dict]:
    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    pages = {record["page_json_version_id"]: record["page_json"] for record in records}
    receipt = build_gemini_json_equity_matrix_region_query_receipt_v1(
        cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
    )
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=receipt,
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    return compiled, cluster, candidate


def _evaluate_table(table: dict) -> tuple[dict, dict, dict]:
    return _evaluate_records([_record(_page(_section("Vốn chủ sở hữu", table)))])


def test_registered_equity_matrix_source_repair_artifact_is_content_addressed() -> None:
    raw = json.loads(
        (ROOT / "data/registered/gemini_json_equity_matrix_source_repairs_v1.json").read_bytes()
    )
    checked = subject._validate_authenticated_source_repair_artifact_v1(
        raw, family_id="CAPITAL_AND_FUNDS"
    )
    assert checked["repair_count"] == 12
    assert checked["repair_axis_sha256"] == raw["repair_axis_sha256"]

    missing = copy.deepcopy(raw)
    missing["repairs"][0].pop("column_axis_exact")
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="source-repair fields drifted",
    ):
        subject._validate_authenticated_source_repair_artifact_v1(
            missing, family_id="CAPITAL_AND_FUNDS"
        )

    extra = copy.deepcopy(raw)
    extra["repairs"][0]["unexpected"] = True
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="source-repair fields drifted",
    ):
        subject._validate_authenticated_source_repair_artifact_v1(
            extra, family_id="CAPITAL_AND_FUNDS"
        )

    duplicate = copy.deepcopy(raw)
    duplicate["repairs"].append(copy.deepcopy(duplicate["repairs"][0]))
    duplicate["repair_count"] += 1
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="page binding is invalid",
    ):
        subject._validate_authenticated_source_repair_artifact_v1(
            duplicate, family_id="CAPITAL_AND_FUNDS"
        )

    duplicate_cell = copy.deepcopy(raw)
    cells = duplicate_cell["repairs"][0]["row_repairs"][0]["cell_repairs"]
    cells.append(copy.deepcopy(cells[0]))
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="source-repair cell is invalid",
    ):
        subject._validate_authenticated_source_repair_artifact_v1(
            duplicate_cell, family_id="CAPITAL_AND_FUNDS"
        )

    unit_surface_missing = copy.deepcopy(raw)
    unit_repair = next(
        repair
        for repair in unit_surface_missing["repairs"]
        if repair["table_unit_repair"] is not None
    )
    unit_repair["table_unit_repair"]["source_surface_axis_exact"].pop()
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="table unit surface axis is invalid",
    ):
        subject._validate_authenticated_source_repair_artifact_v1(
            unit_surface_missing, family_id="CAPITAL_AND_FUNDS"
        )

    unit_surface_tampered = copy.deepcopy(raw)
    unit_repair = next(
        repair
        for repair in unit_surface_tampered["repairs"]
        if repair["table_unit_repair"] is not None
    )
    unit_repair["table_unit_repair"]["after_exact"] = "VND"
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="table unit surface axis is invalid",
    ):
        subject._validate_authenticated_source_repair_artifact_v1(
            unit_surface_tampered, family_id="CAPITAL_AND_FUNDS"
        )


def test_registered_repairs_cover_pdf_visible_bid_and_vib_old8_regressions() -> None:
    raw = json.loads(
        (ROOT / "data/registered/gemini_json_equity_matrix_source_repairs_v1.json").read_bytes()
    )
    by_source = {
        repair["source_binding"]["source_logical_name"]: repair
        for repair in raw["repairs"]
    }

    bid = by_source[
        "vietstock_bctc/BID/2026/BCTC Hợp nhất quý 1 năm 2026.pdf"
    ]
    assert bid["source_binding"]["physical_page"] == 26
    assert bid["row_repairs"] == [
        {
            "after_values_exact": [
                "-",
                "-",
                "-",
                "177,437",
                "-",
                "-",
                "(98)",
                "-",
                "982",
                "-",
                "178,321",
            ],
            "before_values_exact": [
                "-",
                "-",
                "-",
                "177,437",
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                "178,321",
            ],
            "cell_repairs": bid["row_repairs"][0]["cell_repairs"],
            "row_hierarchy_path_exact": ["Chênh lệch tỷ giá hối đoái"],
            "row_id": "r4",
            "row_kind": "ITEM",
            "row_label_exact": "Chênh lệch tỷ giá hối đoái",
        },
        {
            "after_values_exact": [
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                "(77)",
                "70,268",
                "70,191",
            ],
            "before_values_exact": [
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                "(98)",
                "-",
                "982",
                "-",
                "70,191",
            ],
            "cell_repairs": bid["row_repairs"][1]["cell_repairs"],
            "row_hierarchy_path_exact": ["Tăng/ (Giảm) khác"],
            "row_id": "r5",
            "row_kind": "ITEM",
            "row_label_exact": "Tăng/ (Giảm) khác",
        }
    ]
    assert [
        [cell["column_ordinal"] for cell in row["cell_repairs"]]
        for row in bid["row_repairs"]
    ] == [[7, 9], [7, 9, 10]]

    vib = by_source[
        "vietstock_bctc/VIB/2025/BCTC Hợp nhất Soát xét quý 1 năm 2025.pdf"
    ]
    assert vib["source_binding"]["physical_page"] == 50
    assert [row["row_id"] for row in vib["row_repairs"]] == [
        "r1",
        "r2",
        "r3",
        "r4",
        "r5",
        "r6",
    ]
    assert sum(len(row["cell_repairs"]) for row in vib["row_repairs"]) == 17
    assert all(
        cell["after_exact"] == "-" and cell["visual_state"] == "DASH"
        for row in vib["row_repairs"]
        for cell in row["cell_repairs"]
        if cell["before_exact"] is None
    )


def test_registered_source_repair_rejects_blank_to_numeric_zero_and_ref_tamper() -> None:
    raw = json.loads(
        (ROOT / "data/registered/gemini_json_equity_matrix_source_repairs_v1.json").read_bytes()
    )
    blank_cell = next(
        (row, cell)
        for repair in raw["repairs"]
        for row in repair["row_repairs"]
        for cell in row["cell_repairs"]
        if cell["before_exact"] is None
    )
    row, cell = blank_cell
    cell["after_exact"] = "0"
    cell["visual_state"] = "PRINTED_MONEY"
    row["after_values_exact"][cell["column_ordinal"] - 1] = "0"
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="source-repair cell is invalid",
    ):
        subject._validate_authenticated_source_repair_artifact_v1(
            raw, family_id="CAPITAL_AND_FUNDS"
        )

    evaluation = _json("tm-capital-and-funds-evaluation-v1.json")
    evaluation["authenticated_source_repair_artifact_ref"]["sha256"] = "0" * 64
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="artifact bytes drifted",
    ):
        compile_gemini_json_equity_matrix_family_specs_v1(
            _json("tm-capital-and-funds-topology-v1.json"),
            evaluation,
            _json("tm-capital-and-funds-schema-binding-v1.json"),
        )


def test_authenticated_source_repair_is_clone_only_and_fails_on_before_image_drift() -> None:
    table = _component_column_table()
    table["rows"][1]["values_exact"][1] = None
    page = _page(_section("Vốn chủ sở hữu", table))
    record = _record(page)
    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    region = cluster["component_regions"][0]
    effective_page = copy.deepcopy(page)
    effective_table = effective_page["sections"][0]["tables"][0]
    before_values = copy.deepcopy(table["rows"][1]["values_exact"])
    after_values = copy.deepcopy(before_values)
    after_values[1] = "-"
    effective_table["rows"][1]["values_exact"] = after_values
    repair = {
        "base_page_json_sha256": subject.canonical_json_sha256_v1(page),
        "base_page_json_version_id": region["page_json_version_id"],
        "column_axis_exact": copy.deepcopy(table["columns"]),
        "effective_page_json_sha256": subject.canonical_json_sha256_v1(effective_page),
        "extraction_run_id": "gfpstorev1:run:" + "1" * 64,
        "repair_id": "gjeqmsrv1:repair:" + "2" * 64,
        "repair_reason": "VISIBLE_PDF_ROW_CELL_AXIS_MISALIGNED_IN_SELECTED_JSON",
        "row_repairs": [
            {
                "after_values_exact": after_values,
                "before_values_exact": before_values,
                "cell_repairs": [
                    {
                        "after_exact": "-",
                        "before_exact": None,
                        "cell_id": "r2:c2",
                        "column_header_path_exact": copy.deepcopy(
                            table["columns"][1]["header_path_exact"]
                        ),
                        "column_ordinal": 2,
                        "visual_state": "DASH",
                    }
                ],
                "row_hierarchy_path_exact": copy.deepcopy(
                    table["rows"][1]["hierarchy_path_exact"]
                ),
                "row_id": "r2",
                "row_kind": table["rows"][1]["row_kind"],
                "row_label_exact": table["rows"][1]["label_exact"],
            }
        ],
        "source_binding": {
            "document_id": region["document_id"],
            "image_sha256": "3" * 64,
            "image_size_bytes": 1,
            "media_type": "image/png",
            "page_id": "gfpstorev1:page:" + "4" * 64,
            "physical_page": region["physical_page"],
            "pixel_height": 10,
            "pixel_width": 10,
            "render_dpi": 300,
            "source_logical_name": region["source_logical_name"],
            "source_sha256": region["source_sha256"],
            "source_size_bytes": 1,
        },
        "stored_canonical_json_sha256": "5" * 64,
        "table_unit_repair": None,
        "table_ref": {
            "base_table_sha256": subject.canonical_json_sha256_v1(table),
            "effective_table_sha256": subject.canonical_json_sha256_v1(effective_table),
            "section_id": region["section_id"],
            "table_id": region["table_id"],
        },
        "visual_evidence": {
            "evidence_kind": "AUTHENTICATED_MANUAL_VISUAL_ROW_CELL_TRANSCRIPTION",
            "render_mode": "PDF_PAGE_GET_PIXMAP_DPI_EXACT",
            "reviewed_utc_date": "2026-09-04",
            "table_crop_bbox_pixels_xyxy": [0, 0, 10, 10],
            "table_crop_rgb_sha256": "6" * 64,
        },
    }
    compiled["source_repair_overlay"] = {
        "overlay_id": "gjeqmsrv1:overlay:" + "7" * 64,
        "repairs": [repair],
    }
    original = copy.deepcopy(page)
    effective, receipts = subject._apply_authenticated_source_repair_artifact_v1(
        page_json_by_version={region["page_json_version_id"]: page},
        compiled_specs=compiled,
        regions=[region],
    )
    assert page == original
    assert effective[region["page_json_version_id"]]["sections"][0]["tables"][0]["rows"][1][
        "values_exact"
    ][1] == "-"
    assert [item["repair_id"] for item in receipts] == [repair["repair_id"]]

    tampered = copy.deepcopy(page)
    tampered["sections"][0]["tables"][0]["rows"][1]["values_exact"][1] = "0"
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="base page drifted",
    ):
        subject._apply_authenticated_source_repair_artifact_v1(
            page_json_by_version={region["page_json_version_id"]: tampered},
            compiled_specs=compiled,
            regions=[region],
        )


def test_authenticated_source_repair_can_restore_only_a_directly_visible_table_unit() -> None:
    table = _component_column_table()
    table["unit_exact"] = None
    page = _page(_section("Vốn chủ sở hữu", table))
    record = _record(page)
    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    region = cluster["component_regions"][0]
    effective_page = copy.deepcopy(page)
    effective_table = effective_page["sections"][0]["tables"][0]
    effective_table["unit_exact"] = "Triệu VND"
    repair = {
        "base_page_json_sha256": subject.canonical_json_sha256_v1(page),
        "base_page_json_version_id": region["page_json_version_id"],
        "column_axis_exact": copy.deepcopy(table["columns"]),
        "effective_page_json_sha256": subject.canonical_json_sha256_v1(effective_page),
        "extraction_run_id": "gfpstorev1:run:" + "1" * 64,
        "repair_id": "gjeqmsrv1:repair:" + "2" * 64,
        "repair_reason": "VISIBLE_PDF_TABLE_UNIT_MISSING_IN_SELECTED_JSON",
        "row_repairs": [],
        "source_binding": {
            "document_id": region["document_id"],
            "image_sha256": "3" * 64,
            "image_size_bytes": 1,
            "media_type": "image/png",
            "page_id": "gfpstorev1:page:" + "4" * 64,
            "physical_page": region["physical_page"],
            "pixel_height": 10,
            "pixel_width": 10,
            "render_dpi": 300,
            "source_logical_name": region["source_logical_name"],
            "source_sha256": region["source_sha256"],
            "source_size_bytes": 1,
        },
        "stored_canonical_json_sha256": "5" * 64,
        "table_unit_repair": {
            "after_exact": "Triệu VND",
            "before_exact": None,
            "source_surface_axis_exact": [
                {"column_id": f"c{ordinal}", "source_exact": "Triệu VND"}
                for ordinal in range(1, len(table["columns"]) + 1)
            ],
            "visual_state": "PRINTED_UNIT",
        },
        "table_ref": {
            "base_table_sha256": subject.canonical_json_sha256_v1(table),
            "effective_table_sha256": subject.canonical_json_sha256_v1(effective_table),
            "section_id": region["section_id"],
            "table_id": region["table_id"],
        },
        "visual_evidence": {
            "evidence_kind": "AUTHENTICATED_MANUAL_VISUAL_ROW_CELL_TRANSCRIPTION",
            "render_mode": "PDF_PAGE_GET_PIXMAP_DPI_EXACT",
            "reviewed_utc_date": "2026-09-04",
            "table_crop_bbox_pixels_xyxy": [0, 0, 10, 10],
            "table_crop_rgb_sha256": "6" * 64,
        },
    }
    compiled["source_repair_overlay"] = {
        "overlay_id": "gjeqmsrv1:overlay:" + "7" * 64,
        "repairs": [repair],
    }
    original = copy.deepcopy(page)
    effective, receipts = subject._apply_authenticated_source_repair_artifact_v1(
        page_json_by_version={region["page_json_version_id"]: page},
        compiled_specs=compiled,
        regions=[region],
    )
    assert page == original
    assert (
        effective[region["page_json_version_id"]]["sections"][0]["tables"][0][
            "unit_exact"
        ]
        == "Triệu VND"
    )
    assert receipts[0]["table_unit_repair"]["after_exact"] == "Triệu VND"

    drifted = copy.deepcopy(page)
    drifted["sections"][0]["tables"][0]["unit_exact"] = "VND"
    repair["base_page_json_sha256"] = subject.canonical_json_sha256_v1(drifted)
    compiled["source_repair_overlay"]["repairs"] = [repair]
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="base table drifted",
    ):
        subject._apply_authenticated_source_repair_artifact_v1(
            page_json_by_version={region["page_json_version_id"]: drifted},
            compiled_specs=compiled,
            regions=[region],
        )


def test_component_columns_close_without_exposing_graph_logic_to_gemini() -> None:
    _compiled_specs, _cluster, candidate = _evaluate_table(_component_column_table())
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["orientation"] == "COMPONENT_COLUMNS"
    assert [item["coefficient"] for item in by_role["CHARTER_CAPITAL"]["values"]] == [
        100,
        105,
    ]
    assert all(
        equation["status"] == "EXACT" for equation in candidate["closure_receipt"]["equations"]
    )


def test_exact_english_owner_component_and_balance_aliases_map_same_schema_roles() -> None:
    table = {
        "columns": [
            _column("Charter capital\n1"),
            _column("Share premium\n2"),
            _column("Retained earnings\n10"),
            _column("Total\n13"),
        ],
        "continuation": "NONE",
        "rows": [
            _row("Balance at 1 January 2025", ["100", "20", "30", "150"]),
            _row("Net profit for the year", ["-", "-", "5", "5"]),
            _row("Balance at 31 December 2025", ["100", "20", "35", "155"]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    records = [
        _record(_page(_section("13.1 Statement of changes in owners' equity", table)))
    ]
    _compiled_specs, _cluster, candidate = _evaluate_records(records)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert [item["coefficient"] for item in by_role["CHARTER_CAPITAL"]["values"]] == [
        100,
        100,
    ]
    assert [item["coefficient"] for item in by_role["RETAINED_EARNINGS"]["values"]] == [
        30,
        35,
    ]


def test_flat_declared_fund_subtotal_owns_only_contiguous_preceding_fund_columns() -> None:
    table = {
        "columns": [
            _column("Vốn điều lệ"),
            _column("Quỹ dự trữ bổ sung vốn điều lệ"),
            _column("Quỹ dự phòng tài chính"),
            _column("Các quỹ khác"),
            _column("Tổng cộng các quỹ"),
            _column("Lợi nhuận chưa phân phối"),
            _column("Tổng cộng"),
        ],
        "continuation": "NONE",
        "rows": [
            _row("Số dư đầu kỳ", ["100", "10", "20", "5", "35", "30", "165"]),
            _row("Tăng trong kỳ", ["10", "1", "2", "-", "3", "5", "18"]),
            _row("Giảm trong kỳ", ["(5)", "-", "-", "-", "-", "(2)", "(7)"]),
            _row("Số dư cuối kỳ", ["105", "11", "22", "5", "38", "33", "176"]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == READY
    axis = candidate["closure_receipt"]["component_axis"]
    subtotal = next(item for item in axis if item["members_exact"] == ["Tổng cộng các quỹ"])
    assert subtotal["hierarchy_resolution"] == {
        "child_axis_ids": ["c2", "c3", "c4"],
        "rule": "FLAT_DECLARED_GROUP_TOTAL_OWNS_CONTIGUOUS_TOKEN_MATCHING_CHILDREN",
    }
    assert all(equation["status"] == "EXACT" for equation in candidate["closure_receipt"]["equations"])


@pytest.mark.parametrize(
    "subtotal_path",
    [
        ["Quỹ của TCTD", "Tổng cộng Quỹ của TCTD"],
        ["Tổng cộng Quỹ của TCTD"],
    ],
)
def test_declared_repeated_group_name_subtotal_is_not_a_second_leaf(
    subtotal_path: list[str],
) -> None:
    def grouped_column(*members: str) -> dict:
        return {"header_path_exact": list(members), "value_kind": "MONEY"}

    table = {
        "columns": [
            _column("Vốn điều lệ"),
            grouped_column("Quỹ của TCTD", "Quỹ dự phòng tài chính"),
            grouped_column("Quỹ của TCTD", "Quỹ dự trữ bổ sung vốn điều lệ"),
            grouped_column(*subtotal_path),
            _column("Lợi nhuận chưa phân phối"),
            _column("Tổng cộng"),
        ],
        "continuation": "NONE",
        "rows": [
            _row("Số dư đầu kỳ", ["100", "10", "20", "30", "40", "170"]),
            _row("Tăng trong kỳ", ["10", "1", "2", "3", "5", "18"]),
            _row("Giảm trong kỳ", ["(5)", "-", "-", "-", "(2)", "(7)"]),
            _row("Số dư cuối kỳ", ["105", "11", "22", "33", "43", "181"]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == READY
    axis = candidate["closure_receipt"]["component_axis"]
    subtotal = next(item for item in axis if item["axis_id"] == "c4")
    assert subtotal["kind"] == "GROUP_TOTAL"
    assert subtotal["role"] is None
    assert subtotal["group_prefix"] == ["quy cua tctd"]
    assert all(equation["status"] == "EXACT" for equation in candidate["closure_receipt"]["equations"])


def test_component_rows_resolve_positive_decrease_presentation_locally() -> None:
    _compiled_specs, _cluster, candidate = _evaluate_table(_component_row_table())
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["orientation"] == "COMPONENT_ROWS"
    assert by_role["DECREASE_TOTAL"]["values"][0]["equation_multiplier"] == -1
    assert [item["coefficient"] for item in by_role["RETAINED_EARNINGS"]["values"]] == [
        30,
        5,
        2,
        33,
    ]


def test_exact_adjacent_directional_child_row_is_a_control_not_a_second_term() -> None:
    table = _component_column_table()
    table["rows"][1]["label_exact"] = "Tăng trong kỳ"
    table["rows"][1]["hierarchy_path_exact"] = ["Tăng trong kỳ"]
    table["rows"][2]["label_exact"] = "Giảm trong kỳ"
    table["rows"][2]["hierarchy_path_exact"] = ["Giảm trong kỳ"]
    duplicate = copy.deepcopy(table["rows"][2])
    duplicate["label_exact"] = "Giảm khác"
    duplicate["hierarchy_path_exact"] = ["Giảm khác"]
    table["rows"].insert(3, duplicate)

    _compiled_specs, _cluster, candidate = _evaluate_table(table)

    assert candidate["status"] == READY
    receipt = next(
        item
        for item in candidate["closure_receipt"]["alignment_receipts"]
        if item["rule"].startswith("EXACT_ADJACENT_DECLARED_DIRECTIONAL_CHILD_ROW")
    )
    assert receipt["axis_role"] == "DECREASE"
    assert receipt["retained_source_ref"]["row_id"] == "r3"
    assert receipt["corroborating_source_ref"]["row_id"] == "r4"
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_directional_child_row_with_different_source_vector_is_not_collapsed() -> None:
    table = _component_column_table()
    table["rows"][1]["label_exact"] = "Tăng trong kỳ"
    table["rows"][1]["hierarchy_path_exact"] = ["Tăng trong kỳ"]
    table["rows"][2]["label_exact"] = "Giảm trong kỳ"
    table["rows"][2]["hierarchy_path_exact"] = ["Giảm trong kỳ"]
    different = copy.deepcopy(table["rows"][2])
    different["label_exact"] = "Giảm khác"
    different["hierarchy_path_exact"] = ["Giảm khác"]
    different["values_exact"][0] = "(4)"
    table["rows"].insert(3, different)

    _compiled_specs, _cluster, candidate = _evaluate_table(table)

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_exact_cumulative_directional_row_replaces_included_adjacent_detail() -> None:
    table = _component_column_table(
        opening=["100", "20", "30", "150"],
        details=[["10", "-", "5", "15"], ["-", "-", "(2)", "(2)"]],
        closing=["110", "19", "33", "162"],
    )
    table["rows"][1]["label_exact"] = "Tăng trong kỳ"
    table["rows"][1]["hierarchy_path_exact"] = ["Tăng trong kỳ"]
    table["rows"][2]["label_exact"] = "Giảm trong kỳ"
    table["rows"][2]["hierarchy_path_exact"] = ["Giảm trong kỳ"]
    cumulative = _row("Giảm khác", ["-", "(1)", "(2)", "(3)"])
    table["rows"].insert(3, cumulative)

    _compiled_specs, _cluster, candidate = _evaluate_table(table)

    assert candidate["status"] == READY
    receipt = next(
        item
        for item in candidate["closure_receipt"]["alignment_receipts"]
        if item["rule"].startswith("UNIQUE_EXACT_ADJACENT_DIRECTIONAL_CUMULATIVE_ROW")
    )
    assert receipt["discarded_source_ref"]["row_id"] == "r3"
    assert receipt["retained_source_ref"]["row_id"] == "r4"
    decrease = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "DECREASE_TOTAL"
    )
    assert decrease["values"][0]["coefficient"] == -3
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_same_label_observed_subset_duplicate_preserves_blanks_as_unobserved() -> None:
    table = _component_column_table()
    table["rows"][1]["label_exact"] = "Tăng trong kỳ"
    table["rows"][1]["hierarchy_path_exact"] = ["Tăng trong kỳ"]
    subset = _row("Tăng trong kỳ", [None, None, "5", "15"])
    table["rows"].insert(2, subset)

    _compiled_specs, _cluster, candidate = _evaluate_table(table)

    assert candidate["status"] == READY
    receipt = next(
        item
        for item in candidate["closure_receipt"]["alignment_receipts"]
        if item["rule"].startswith("EXACT_OBSERVED_SUBSET_SAME_LABEL_ADJACENT_ROW")
    )
    assert receipt["corroborating_source_ref"]["row_id"] == "r3"
    assert receipt["retained_source_ref"]["row_id"] == "r2"
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


@pytest.mark.parametrize("blank_second_headers", [True, False])
def test_reciprocal_adjacent_component_row_fragments_form_one_source_matrix(
    blank_second_headers: bool,
) -> None:
    records = _reciprocal_component_row_pages(blank_second_headers=blank_second_headers)

    _compiled_specs, cluster, candidate = _evaluate_records(records)

    assert len(cluster["component_regions"]) == 2
    assert candidate["status"] == READY
    receipt = next(
        item
        for item in candidate["closure_receipt"]["alignment_receipts"]
        if item["rule"]
        == "EXPLICIT_RECIPROCAL_ADJACENT_COMPONENT_ROW_FRAGMENTS_FORM_ONE_COMPLEMENTARY_COMPONENT_AXIS"
    )
    assert receipt["money_header_rule"] == (
        "SECOND_FRAGMENT_INHERITS_IDENTICAL_POSITIONAL_MONEY_AXIS"
        if blank_second_headers
        else "SECOND_FRAGMENT_REPEATS_EXACT_NORMALIZED_MONEY_AXIS"
    )
    retained = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "RETAINED_EARNINGS"
    )
    assert all(
        value["cell_ref"]["locator"]["physical_page"] == 2
        for value in retained["values"]
    )
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_reciprocal_page_boundary_blank_label_tail_is_joined_without_values() -> None:
    records = _reciprocal_component_row_pages()
    first = records[0]["page_json"]["sections"][0]["tables"][0]
    second = records[1]["page_json"]["sections"][0]["tables"][0]
    first["rows"].append(
        _row("Quỹ dự trữ bổ sung vốn", ["10", "1", "-", "11"])
    )
    second["rows"] = [
        _row("điều lệ", [None, None, None, None]),
        _row("Lợi nhuận sau thuế chưa phân phối", ["30", "5", "2", "33"]),
        _row("Các quỹ khác", ["5", "-", "-", "5"]),
        _row("Tổng cộng", ["165", "16", "7", "174"], kind="TOTAL"),
    ]

    _compiled_specs, cluster, candidate = _evaluate_records(records)

    assert cluster["status"] == READY
    assert candidate["status"] == READY
    receipt = candidate["closure_receipt"]["alignment_receipts"][0]
    assert receipt["split_label_receipt"]["combined_label_exact"] == (
        "Quỹ dự trữ bổ sung vốn điều lệ"
    )
    assert receipt["split_label_receipt"]["recovered_role"] == "CAPITAL_RESERVE"


@pytest.mark.parametrize(
    "mutation",
    [
        "ONE_SIDED_CONTINUATION",
        "MISMATCHED_MONEY_AXIS",
        "DUPLICATE_GRAND_TOTAL",
        "NONBLANK_LABEL_TAIL",
        "UNDECLARED_JOINED_LABEL",
    ],
)
def test_component_row_continuation_adversarial_cases_fail_closed(mutation: str) -> None:
    records = _reciprocal_component_row_pages()
    first = records[0]["page_json"]["sections"][0]["tables"][0]
    second = records[1]["page_json"]["sections"][0]["tables"][0]
    if mutation == "ONE_SIDED_CONTINUATION":
        second["continuation"] = "NONE"
    elif mutation == "MISMATCHED_MONEY_AXIS":
        second["columns"] = copy.deepcopy(first["columns"])
        second["columns"][1] = _column("Tăng trong năm")
    elif mutation == "DUPLICATE_GRAND_TOTAL":
        first["rows"].append(_row("Tổng cộng", ["120", "10", "5", "125"], kind="TOTAL"))
    else:
        first["rows"].append(
            _row("Quỹ dự trữ bổ sung vốn", ["10", "1", "-", "11"])
        )
        second["rows"].insert(
            0,
            _row(
                "điều lệ" if mutation == "NONBLANK_LABEL_TAIL" else "không xác định",
                ["1", None, None, None]
                if mutation == "NONBLANK_LABEL_TAIL"
                else [None, None, None, None],
            ),
        )
    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []


def test_explicit_supplemental_fund_matrix_maps_children_after_exact_group_reconciliation() -> None:
    primary, supplemental = _primary_and_supplemental_fund_tables()
    unrelated = {
        "columns": [_column("Loại cổ phiếu")],
        "continuation": "NONE",
        "rows": [_row("Phổ thông", ["100"])],
        "title_exact": "Cổ phiếu",
        "unit_exact": None,
    }
    records = [
        _record(
            _page(_section("Vốn chủ sở hữu", primary, unrelated, supplemental)),
            ordinal=1,
        )
    ]

    _compiled_specs, cluster, candidate = _evaluate_records(records)

    assert [region["table_id"] for region in cluster["component_regions"]] == ["t1", "t3"]
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [
        value["coefficient"] for value in by_role["CAPITAL_RESERVE"]["values"]
    ] == [10, 1, 0, 11]
    assert [
        value["coefficient"] for value in by_role["FINANCIAL_RESERVE"]["values"]
    ] == [15, 2, 0, 17]
    assert [value["coefficient"] for value in by_role["OTHER_FUNDS"]["values"]] == [
        5,
        0,
        0,
        5,
    ]
    assert all(
        value["cell_ref"]["locator"]["table_id"] == "t3"
        for role in ("CAPITAL_RESERVE", "FINANCIAL_RESERVE", "OTHER_FUNDS")
        for value in by_role[role]["values"]
    )
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_supplemental_matrix_conflict_with_primary_group_total_remains_unresolved() -> None:
    primary, supplemental = _primary_and_supplemental_fund_tables()
    supplemental["rows"][-1]["values_exact"][-1] = "34"
    records = [
        _record(
            _page(_section("Vốn chủ sở hữu", primary, supplemental)),
            ordinal=1,
        )
    ]

    _compiled_specs, cluster, candidate = _evaluate_records(records)

    assert cluster["status"] == READY
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any(
        reason.startswith("SUPPLEMENTAL_COMPONENT_GROUP:")
        for reason in candidate["reasons"]
    )


def test_supplemental_matrix_without_explicit_group_owner_is_not_admitted() -> None:
    primary, supplemental = _primary_and_supplemental_fund_tables()
    supplemental["title_exact"] = None
    records = [
        _record(
            _page(_section("Vốn chủ sở hữu", primary, supplemental)),
            ordinal=1,
        )
    ]

    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )

    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []


def test_supplemental_matrix_inherits_explicit_adjacent_family_owner_continuation() -> None:
    primary, supplemental = _primary_and_supplemental_fund_tables()
    supplemental["title_exact"] = None
    records = [
        _record(_page(_section("Vốn chủ sở hữu", primary)), ordinal=1),
        _record(
            _page(_section("Vốn chủ sở hữu (tiếp theo)", supplemental)),
            ordinal=2,
        ),
    ]

    _compiled_specs, cluster, candidate = _evaluate_records(records)

    assert candidate["status"] == READY
    receipt = cluster["owner_receipt"]["supplemental_component_group_receipt"]
    assert receipt["supplemental_owner"]["rule"].startswith(
        "ADJACENT_FAMILY_OWNER_CONTINUATION"
    )


def test_inherited_supplemental_group_period_selects_unique_current_relative_block() -> None:
    primary, current = _primary_and_supplemental_fund_tables()
    current["title_exact"] = None
    current["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    current["rows"][0]["label_exact"] = "Số dư đầu năm nay"
    current["rows"][0]["hierarchy_path_exact"] = ["Số dư đầu năm nay"]
    current["rows"][-1]["label_exact"] = "Số dư cuối kỳ này"
    current["rows"][-1]["hierarchy_path_exact"] = ["Số dư cuối kỳ này"]
    previous = copy.deepcopy(current)
    previous["continuation"] = "NONE"
    previous["title_exact"] = "Các quỹ của TCTD"
    previous["rows"] = [
        _row("Số dư đầu năm trước", ["8", "12", "4", "24"]),
        _row("Tăng trong kỳ", ["2", "3", "1", "6"]),
        _row("Giảm trong kỳ", ["-", "-", "-", "-"]),
        _row("Số dư cuối kỳ trước", ["10", "15", "5", "30"]),
    ]
    records = [
        _record(
            _page(
                _section("Vốn chủ sở hữu", primary),
                _section("Các quỹ của TCTD", previous),
            ),
            ordinal=1,
        ),
        _record(_page(_section("Thuyết minh (tiếp theo)", current)), ordinal=2),
    ]

    _compiled_specs, cluster, candidate = _evaluate_records(records)

    assert candidate["status"] == READY
    receipt = cluster["owner_receipt"]["supplemental_component_group_receipt"]
    assert receipt["fragment_positions"] == [[1, 1, 1, 0], [2, 1, 1, 0]]
    assert receipt["authenticated_comparative_snapshots"][0]["position"] == [
        1,
        2,
        1,
        0,
    ]
    assert receipt["supplemental_owner"]["rule"].startswith(
        "STRUCTURED_FROM_PREVIOUS_PAGE"
    )


def test_unique_high_dimension_matrix_plus_supplemental_group_authenticates_owner() -> None:
    primary = {
        "columns": [
            _column("Vốn điều lệ"),
            _column("Thặng dư vốn cổ phần"),
            _column("Quỹ dự phòng tài chính"),
            _column("Quỹ dự trữ bổ sung vốn điều lệ"),
            _column("Lợi nhuận chưa phân phối"),
            _column("Tổng cộng"),
        ],
        "continuation": "NONE",
        "rows": [
            _row("Số dư đầu kỳ", ["100", "20", "15", "10", "5", "150"]),
            _row("Tăng trong kỳ", ["10", "-", "2", "1", "2", "15"]),
            _row("Giảm trong kỳ", ["-", "-", "-", "-", "-", "-"]),
            _row("Số dư cuối kỳ", ["110", "20", "17", "11", "7", "165"]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    _unused, supplemental = _primary_and_supplemental_fund_tables()
    records = [
        _record(_page(_section("Thuyết minh báo cáo", primary)), ordinal=1),
        _record(_page(_section("Các quỹ của TCTD", supplemental)), ordinal=2),
    ]

    _compiled_specs, cluster, candidate = _evaluate_records(records)

    assert candidate["status"] == READY
    assert cluster["owner_receipt"]["rule"].startswith(
        "UNIQUE_COMPLETE_HIGH_DIMENSION_EQUITY_MATRIX"
    )


def test_latest_explicit_fund_period_snapshot_projects_both_declared_boundaries() -> None:
    primary, _supplemental = _primary_and_supplemental_fund_tables()
    primary["rows"][1]["values_exact"] = ["10", "-", "2", "12"]
    primary["rows"][-1]["values_exact"] = ["110", "30", "22", "162"]
    comparative = _fund_period_snapshot(
        period="Kỳ sáu tháng kết thúc ngày 30 tháng 6 năm 2024",
        values=["8", "12", "4", "24"],
    )
    current = _fund_period_snapshot(
        period="Kỳ sáu tháng kết thúc ngày 30 tháng 6 năm 2025",
        values=["10", "15", "5", "30"],
    )
    records = [
        _record(_page(_section("Vốn chủ sở hữu", primary)), ordinal=1),
        _record(
            _page(_section("(c) Các quỹ của TCTD", current, comparative)),
            ordinal=2,
        ),
    ]

    _compiled_specs, cluster, candidate = _evaluate_records(records)

    assert [region["table_id"] for region in cluster["component_regions"]] == ["t1", "t1"]
    receipt = cluster["owner_receipt"]["supplemental_component_group_receipt"]
    assert receipt["mode"] == "EXPLICIT_OPENING_AND_CLOSING_PERIOD_SNAPSHOT"
    assert receipt["authenticated_comparative_snapshots"][0]["period_date"] == "2024-06-30"
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [
        value["coefficient"] for value in by_role["CAPITAL_RESERVE"]["values"]
    ] == [10, 10]
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_fund_period_snapshots_with_tied_dates_remain_unresolved() -> None:
    primary, _supplemental = _primary_and_supplemental_fund_tables()
    first = _fund_period_snapshot(
        period="Kỳ sáu tháng kết thúc ngày 30 tháng 6 năm 2025",
        values=["10", "15", "5", "30"],
    )
    second = copy.deepcopy(first)
    records = [
        _record(_page(_section("Vốn chủ sở hữu", primary)), ordinal=1),
        _record(_page(_section("Các quỹ của TCTD", first, second)), ordinal=2),
    ]

    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )

    assert cluster["status"] == UNRESOLVED
    assert "MULTIPLE_SUPPLEMENTAL_COMPONENT_GROUP_MATRIX_PAIRS" in cluster["reasons"]


def test_fund_period_snapshot_must_explicitly_apply_to_opening_and_closing() -> None:
    primary, _supplemental = _primary_and_supplemental_fund_tables()
    snapshot = _fund_period_snapshot(
        period="Kỳ sáu tháng kết thúc ngày 30 tháng 6 năm 2025",
        values=["10", "15", "5", "30"],
    )
    snapshot["rows"][0]["label_exact"] = "Số dư cuối kỳ"
    snapshot["rows"][0]["hierarchy_path_exact"] = ["Số dư cuối kỳ"]
    records = [
        _record(_page(_section("Vốn chủ sở hữu", primary)), ordinal=1),
        _record(_page(_section("Các quỹ của TCTD", snapshot)), ordinal=2),
    ]

    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )

    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []


@pytest.mark.parametrize("source_text", ["100(*)", "100 (*)", "100带有-"])
def test_single_leading_numeric_token_with_source_suffix_is_graph_gated(
    source_text: str,
) -> None:
    table = _component_row_table()
    table["rows"][0]["values_exact"][0] = source_text

    _compiled_specs, _cluster, candidate = _evaluate_table(table)

    assert candidate["status"] == READY
    charter = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "CHARTER_CAPITAL")
    opening = next(value for value in charter["values"] if value["axis_role"] == "OPENING")
    assert opening["coefficient"] == 100
    assert opening["source_text"] == source_text
    assert opening["state"] == "NORMALIZED_SINGLE_NUMERIC_TOKEN_PENDING_GRAPH"
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


@pytest.mark.parametrize(
    "source_text",
    [
        "-(100)",
        "note 100",
        "100 note 200",
        "null",
    ],
)
def test_ambiguous_or_nonleading_numeric_surface_is_not_scalar_normalized(
    source_text: str,
) -> None:
    table = _component_row_table()
    table["rows"][0]["values_exact"][0] = source_text

    _compiled_specs, _cluster, candidate = _evaluate_table(table)

    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any(reason.startswith("MONEY_CELL_INVALID:") for reason in candidate["reasons"])


@pytest.mark.parametrize("months", ["3", "03", "06", "09", "12"])
def test_component_rows_accept_exact_duration_movement_headers(months: str) -> None:
    table = _component_row_table()
    table["columns"][1] = _column(f"Tăng trong {months} tháng")
    table["columns"][2] = _column(f"Giảm trong {months} tháng")

    _compiled_specs, _cluster, candidate = _evaluate_table(table)

    assert candidate["status"] == READY
    movement = candidate["closure_receipt"]["movement_axis"]
    assert [item["axis_role"] for item in movement] == [
        "OPENING",
        "INCREASE",
        "DECREASE",
        "CLOSING",
    ]
    assert movement[1]["members_exact"] == [f"Tăng trong {months} tháng"]
    assert movement[2]["members_exact"] == [f"Giảm trong {months} tháng"]


def test_component_rows_accept_split_duration_header_and_ignore_enumeration_stub() -> None:
    table = _component_row_table()
    table["columns"].insert(0, {"header_path_exact": ["A"], "value_kind": "TEXT"})
    table["columns"][2] = {
        "header_path_exact": ["Tăng trong", "09 tháng"],
        "value_kind": "MONEY",
    }
    table["columns"][3] = {
        "header_path_exact": ["Giảm trong", "09 tháng"],
        "value_kind": "MONEY",
    }
    for ordinal, row in enumerate(table["rows"], start=1):
        row["values_exact"].insert(0, None if row["row_kind"] == "TOTAL" else str(ordinal))

    _compiled_specs, _cluster, candidate = _evaluate_table(table)

    assert candidate["status"] == READY
    movement = candidate["closure_receipt"]["movement_axis"]
    assert [item["axis_id"] for item in movement] == ["c2", "c3", "c4", "c5"]
    assert [item["axis_role"] for item in movement] == [
        "OPENING",
        "INCREASE",
        "DECREASE",
        "CLOSING",
    ]


@pytest.mark.parametrize(
    "header",
    [
        "Tăng trong 13 tháng",
        "Tăng trong 03 tháng đầu năm 2025",
        "Giảm trong năm 2025",
        "Tăng từ tháng 1 đến tháng 3",
    ],
)
def test_duration_movement_header_grammar_is_fail_closed(header: str) -> None:
    table = _component_row_table()
    table["columns"][1] = _column(header)

    compiled = _compiled()
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(_page(_section("Vốn chủ sở hữu", table)))],
        compiled_specs=compiled,
    )

    assert cluster["status"] == READY
    candidate = evaluate_gemini_json_equity_matrix_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={
            "gfpstorev1:json:" + f"{1:064x}": _page(_section("Vốn chủ sở hữu", table))
        },
        compiled_specs=compiled,
        query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
            cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
        ),
        document_unit_context_evidence=cluster["document_unit_context_evidence"],
    )
    assert candidate["status"] == UNRESOLVED
    assert "EXACT_OPENING_INCREASE_DECREASE_CLOSING_COLUMN_AXIS_REQUIRED" in candidate["reasons"]


def test_component_columns_map_only_source_visible_explicit_movement_totals() -> None:
    table = _component_column_table()
    table["rows"][2]["label_exact"] = "Giảm trong kỳ"
    table["rows"][2]["hierarchy_path_exact"] = ["Giảm trong kỳ"]
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert by_role["DECREASE_TOTAL"]["values"][0]["coefficient"] == -7
    assert [item["axis_role"] for item in by_role["CHARTER_CAPITAL"]["values"]] == [
        "OPENING",
        "DECREASE",
        "CLOSING",
    ]
    assert "INCREASE_TOTAL" not in by_role


def test_component_columns_use_exact_parent_movement_not_parent_plus_children() -> None:
    table = _component_column_table(
        details=[],
        closing=["105", "20", "33", "158"],
    )
    table["rows"] = [
        _row("Số dư đầu kỳ", ["100", "20", "30", "150"]),
        _row("Tăng trong kỳ", ["10", "-", "5", "15"], kind="GROUP"),
        _row("- Tăng vốn", ["10", "-", "-", "10"]),
        _row("- Lợi nhuận trong kỳ", ["-", "-", "5", "5"]),
        _row("Giảm trong kỳ", ["(5)", "-", "(2)", "(7)"], kind="GROUP"),
        _row("- Phân phối lợi nhuận", ["(5)", "-", "(2)", "(7)"]),
        _row("Số dư cuối kỳ", ["105", "20", "33", "158"], kind="TOTAL"),
    ]
    table["rows"][2]["hierarchy_path_exact"] = ["Tăng trong kỳ", "- Tăng vốn"]
    table["rows"][3]["hierarchy_path_exact"] = [
        "Tăng trong kỳ",
        "- Lợi nhuận trong kỳ",
    ]
    table["rows"][5]["hierarchy_path_exact"] = [
        "Giảm trong kỳ",
        "- Phân phối lợi nhuận",
    ]

    _compiled_specs, _cluster, candidate = _evaluate_table(table)

    assert candidate["status"] == READY
    assert [item["axis_role"] for item in candidate["closure_receipt"]["movement_axis"]] == [
        "OPENING",
        "INCREASE",
        "DECREASE",
        "CLOSING",
    ]
    receipts = [
        item
        for item in candidate["closure_receipt"]["alignment_receipts"]
        if item["rule"]
        == "EXACT_FULLY_OBSERVED_PARENT_MOVEMENT_VECTOR_EQUALS_CONTIGUOUS_DECLARED_HIERARCHY_CHILD_SUM"
    ]
    assert [item["axis_role"] for item in receipts] == ["INCREASE", "DECREASE"]
    assert receipts[0]["parent_vector"] == [10, 0, 5, 15]


def test_component_columns_do_not_collapse_parent_when_child_sum_mismatches() -> None:
    table = _component_column_table()
    table["rows"] = [
        _row("Số dư đầu kỳ", ["100", "20", "30", "150"]),
        _row("Tăng trong kỳ", ["10", "-", "5", "15"], kind="GROUP"),
        _row("- Tăng vốn", ["9", "-", "-", "9"]),
        _row("- Lợi nhuận trong kỳ", ["-", "-", "5", "5"]),
        _row("Giảm trong kỳ", ["(5)", "-", "(2)", "(7)"], kind="GROUP"),
        _row("Số dư cuối kỳ", ["105", "20", "33", "158"], kind="TOTAL"),
    ]
    table["rows"][2]["hierarchy_path_exact"] = ["Tăng trong kỳ", "- Tăng vốn"]
    table["rows"][3]["hierarchy_path_exact"] = [
        "Tăng trong kỳ",
        "- Lợi nhuận trong kỳ",
    ]

    _compiled_specs, _cluster, candidate = _evaluate_table(table)

    assert candidate["status"] == UNRESOLVED
    assert all(
        item["rule"]
        != "EXACT_FULLY_OBSERVED_PARENT_MOVEMENT_VECTOR_EQUALS_CONTIGUOUS_DECLARED_HIERARCHY_CHILD_SUM"
        for item in candidate["closure_receipt"]["alignment_receipts"]
    )


def test_latest_dated_block_wins_even_when_comparative_block_is_printed_after_it() -> None:
    table = _component_column_table()
    table["rows"].extend(
        [
            _row("Số dư đầu kỳ tại ngày 01/01/2024", ["80", "20", "20", "120"]),
            _row("Biến động năm trước", ["5", "-", "-", "5"]),
            _row("Số dư cuối kỳ tại ngày 31/12/2024", ["85", "20", "20", "125"]),
        ]
    )
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert [item["coefficient"] for item in by_role["OPENING_TOTAL"]["values"]] == [150]
    assert [item["coefficient"] for item in by_role["CLOSING_TOTAL"]["values"]] == [158]
    receipt = candidate["closure_receipt"]["period_block_receipt"]
    assert receipt["rule"] == "UNIQUE_LATEST_SOURCE_DATED_COMPLETE_BALANCE_BLOCK"
    assert len(receipt["candidate_blocks"]) == 2


def test_explicit_current_relative_block_wins_over_complete_prior_relative_block() -> None:
    table = _component_column_table()
    table["rows"] = [
        _row("Số dư đầu năm trước", ["80", "20", "20", "120"]),
        _row("Tăng trong năm", ["5", "-", "5", "10"]),
        _row("Giảm trong năm", ["-", "-", "-", "-"]),
        _row("Số dư cuối năm trước", ["85", "20", "25", "130"]),
        _row("Số dư đầu kỳ này", ["100", "20", "30", "150"]),
        _row("Tăng trong kỳ", ["10", "-", "5", "15"]),
        _row("Giảm trong kỳ", ["(5)", "-", "(2)", "(7)"]),
        _row("Số dư cuối kỳ này", ["105", "20", "33", "158"], kind="TOTAL"),
    ]

    _compiled_specs, _cluster, candidate = _evaluate_table(table)

    assert candidate["status"] == READY
    receipt = candidate["closure_receipt"]["period_block_receipt"]
    assert receipt["rule"] == "UNIQUE_EXPLICIT_CURRENT_RELATIVE_BALANCE_BLOCK"
    assert receipt["selected_opening_axis_id"] == "f1:r5"
    assert receipt["selected_closing_axis_id"] == "f1:r8"


def test_standalone_date_rows_are_exact_balance_boundaries() -> None:
    table = _component_column_table()
    table["rows"][0]["label_exact"] = "Ngày 1 tháng 1 năm 2025"
    table["rows"][0]["hierarchy_path_exact"] = ["Ngày 1 tháng 1 năm 2025"]
    table["rows"][1]["label_exact"] = (
        "Lợi nhuận từ ngày 1 tháng 1 năm 2025 đến ngày 31 tháng 12 năm 2025"
    )
    table["rows"][1]["hierarchy_path_exact"] = [table["rows"][1]["label_exact"]]
    table["rows"][-1]["label_exact"] = "Ngày 31 tháng 12 năm 2025"
    table["rows"][-1]["hierarchy_path_exact"] = ["Ngày 31 tháng 12 năm 2025"]

    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == READY
    assert "MOVEMENT_AXIS_SURFACE_HAS_MULTIPLE_DATES" not in candidate["reasons"]
    assert candidate["closure_receipt"]["period_block_receipt"]["rule"] == (
        "ONLY_COMPLETE_ORDERED_BALANCE_BLOCK"
    )


def test_relative_current_year_boundaries_exclude_prior_year_block() -> None:
    table = _component_column_table()
    table["rows"] = [
        _row("Số dư đầu năm trước", ["80", "20", "20", "120"]),
        _row("Lợi nhuận năm trước", ["20", "-", "10", "30"]),
        _row("Số dư đầu năm nay", ["100", "20", "30", "150"], kind="SUBTOTAL"),
        _row("Lợi nhuận năm nay", ["10", "-", "5", "15"]),
        _row("Sử dụng trong năm", ["(5)", "-", "(2)", "(7)"]),
        _row("Số dư cuối năm nay", ["105", "20", "33", "158"], kind="TOTAL"),
    ]
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert [item["coefficient"] for item in by_role["OPENING_TOTAL"]["values"]] == [150]
    receipt = candidate["closure_receipt"]["period_block_receipt"]
    assert receipt["rule"] == "ONLY_COMPLETE_ORDERED_BALANCE_BLOCK"
    assert receipt["selected_opening_axis_id"] == "f1:r3"


def test_multiple_dates_on_balance_boundary_remain_unresolved() -> None:
    table = _component_column_table()
    label = "Số dư đầu kỳ tại ngày 01/01/2025 và ngày 02/01/2025"
    table["rows"][0]["label_exact"] = label
    table["rows"][0]["hierarchy_path_exact"] = [label]
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == UNRESOLVED
    assert "MOVEMENT_AXIS_SURFACE_HAS_MULTIPLE_DATES" in candidate["reasons"]


def test_exact_duplicate_parent_child_movement_row_is_one_additive_frontier() -> None:
    table = _component_column_table()
    table["rows"][1]["label_exact"] = "Tăng trong kỳ"
    table["rows"][1]["hierarchy_path_exact"] = ["Tăng trong kỳ"]
    duplicate = copy.deepcopy(table["rows"][1])
    duplicate["label_exact"] = "- Tăng trong kỳ"
    duplicate["hierarchy_path_exact"] = ["Tăng trong kỳ", "- Tăng trong kỳ"]
    table["rows"].insert(2, duplicate)

    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == READY
    receipts = candidate["closure_receipt"]["alignment_receipts"]
    assert [receipt["rule"] for receipt in receipts] == [
        "EXACT_DUPLICATE_DECLARED_MOVEMENT_ROW_IS_CORROBORATING_CONTROL_NOT_SECOND_ADDITIVE_TERM"
    ]
    increase = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "INCREASE_TOTAL"
    )
    assert [value["coefficient"] for value in increase["values"]] == [15]


def test_same_declared_movement_label_with_different_values_is_not_deduplicated() -> None:
    table = _component_column_table()
    table["rows"][1]["label_exact"] = "Tăng trong kỳ"
    table["rows"][1]["hierarchy_path_exact"] = ["Tăng trong kỳ"]
    duplicate = copy.deepcopy(table["rows"][1])
    duplicate["values_exact"] = ["1", "-", "-", "1"]
    table["rows"].insert(2, duplicate)
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == UNRESOLVED
    assert "DUPLICATE_EXPLICIT_MOVEMENT_TOTAL_ROLE" in candidate["reasons"]


def test_multiple_undated_complete_blocks_do_not_use_source_order_as_period_authority() -> None:
    table = _component_column_table()
    table["rows"][0]["label_exact"] = "Số dư đầu kỳ"
    table["rows"][0]["hierarchy_path_exact"] = ["Số dư đầu kỳ"]
    table["rows"][-1]["label_exact"] = "Số dư cuối kỳ"
    table["rows"][-1]["hierarchy_path_exact"] = ["Số dư cuối kỳ"]
    table["rows"].extend(
        [
            _row("Số dư đầu kỳ", ["80", "20", "20", "120"]),
            _row("Biến động trước", ["5", "-", "-", "5"]),
            _row("Số dư cuối kỳ", ["85", "20", "20", "125"]),
        ]
    )
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "CURRENT_MOVEMENT_BLOCK_PERIOD_NOT_UNIQUE" in candidate["reasons"]


def test_equal_row_and_column_role_populations_are_orientation_ambiguous() -> None:
    table = _component_row_table()
    table["columns"] = [
        _column("Vốn điều lệ"),
        _column("Thặng dư vốn cổ phần"),
        _column("Lợi nhuận sau thuế chưa phân phối"),
        _column("Tổng cộng"),
    ]
    classification = classify_gemini_json_equity_matrix_table_v1(table, compiled_specs=_compiled())
    assert classification["status"] == "NOT_MATRIX"
    assert "BOTH_MATRIX_ORIENTATIONS_MATCH" in classification["reasons"]


@pytest.mark.parametrize(
    ("row_index", "source_label", "expected_role"),
    [
        (0, "Vốn góp chủ sở hữu", "CHARTER_CAPITAL"),
        (0, "Vốn cổ phần", "CHARTER_CAPITAL"),
        (1, "Thặng dư vốn", "SHARE_PREMIUM"),
        (0, "Quỹ bổ sung vốn điều lệ", "CAPITAL_RESERVE"),
        (2, "Lợi nhuận chưa phân phối lũy kế", "RETAINED_EARNINGS"),
        (2, "Lợi nhuận chưa phân phối/lỗ lũy kế", "RETAINED_EARNINGS"),
        (2, "Lợi nhuận để lại", "RETAINED_EARNINGS"),
        (2, "Lợi nhuận sau thuế/ Lỗ lũy kế", "RETAINED_EARNINGS"),
        (
            2,
            "Lợi nhuận sau thuế chưa phân phối lãi/lỗ lũy kế",
            "RETAINED_EARNINGS",
        ),
        (2, "LN sau thuế chưa phân phối/ Lỗ lũy kế", "RETAINED_EARNINGS"),
        (0, "Lợi ích của cổ đông thiểu số", "NON_CONTROLLING_INTEREST"),
        (
            0,
            "Lợi ích của cổ đông thiểu số (Trình bày lại)",
            "NON_CONTROLLING_INTEREST",
        ),
    ],
)
def test_pdf_observed_component_aliases_resolve_to_existing_schema_roles(
    row_index: int, source_label: str, expected_role: str
) -> None:
    table = _component_row_table()
    table["rows"][row_index]["label_exact"] = source_label
    table["rows"][row_index]["hierarchy_path_exact"] = [source_label]
    classification = classify_gemini_json_equity_matrix_table_v1(
        table, compiled_specs=_compiled()
    )
    matching = [
        item for item in classification["component_axis"] if item["role"] == expected_role
    ]
    assert classification["status"] == "MATRIX_FRAGMENT"
    assert len(matching) == 1
    assert matching[0]["kind"] == "MAPPED_COMPONENT"


def test_pdf_observed_non_schema_axes_remain_source_only_controls() -> None:
    table = _component_row_table()
    table["rows"] = [
        _row("Vốn góp chủ sở hữu", ["100", "0", "0", "100"]),
        _row("Thặng dư vốn", ["20", "0", "0", "20"]),
        _row("Vốn đầu tư XDCB, mua sắm TSCĐ", ["1", "0", "0", "1"]),
        _row("Các quỹ của TCTD", ["2", "0", "0", "2"]),
        _row("Cổ phiếu ưu đãi", ["3", "0", "0", "3"]),
        _row("Khác", ["4", "0", "0", "4"]),
        _row("Cộng", ["130", "0", "0", "130"], kind="TOTAL"),
    ]
    classification = classify_gemini_json_equity_matrix_table_v1(
        table, compiled_specs=_compiled()
    )
    source_only = {
        item["role"]
        for item in classification["component_axis"]
        if item["kind"] == "SOURCE_ONLY_COMPONENT"
    }
    assert classification["status"] == "MATRIX_FRAGMENT"
    assert source_only == {
        "BASIC_CONSTRUCTION_CAPITAL",
        "FUNDS_OF_CREDIT_INSTITUTION",
        "OTHER_UNSPECIFIED_COMPONENT",
        "PREFERRED_SHARES",
    }
    assert all(
        item["role"] not in source_only
        for item in classification["component_axis"]
        if item["kind"] == "MAPPED_COMPONENT"
    )


def test_hierarchical_fund_subtotal_is_control_not_duplicate_schema_mapping() -> None:
    table = _component_column_table()
    table["columns"] = [
        _column("Vốn điều lệ"),
        {"header_path_exact": ["Các quỹ", "Quỹ dự trữ bổ sung vốn điều lệ"], "value_kind": "MONEY"},
        {"header_path_exact": ["Các quỹ", "Quỹ dự phòng tài chính"], "value_kind": "MONEY"},
        {"header_path_exact": ["Các quỹ", "Tổng cộng các quỹ"], "value_kind": "MONEY"},
        _column("Tổng cộng"),
    ]
    for row in table["rows"]:
        row["values_exact"] = ["100", "10", "20", "30", "130"]
    classification = classify_gemini_json_equity_matrix_table_v1(
        table, compiled_specs=_compiled()
    )
    fund_total = next(
        item
        for item in classification["component_axis"]
        if item["members_exact"] == ["Các quỹ", "Tổng cộng các quỹ"]
    )
    assert classification["status"] == "MATRIX_FRAGMENT"
    assert fund_total["kind"] == "GROUP_TOTAL"
    assert fund_total["role"] is None
    assert fund_total["group_prefix"] == ["cac quy"]

    flat_subtotal = copy.deepcopy(table)
    flat_subtotal["columns"][3]["header_path_exact"] = ["Tổng cộng các quỹ"]
    flat_classification = classify_gemini_json_equity_matrix_table_v1(
        flat_subtotal, compiled_specs=_compiled()
    )
    flat_fund_total = next(
        item
        for item in flat_classification["component_axis"]
        if item["members_exact"] == ["Tổng cộng các quỹ"]
    )
    assert flat_classification["status"] == "MATRIX_FRAGMENT"
    assert flat_fund_total["kind"] == "GROUP_TOTAL"
    assert flat_fund_total["role"] is None
    assert flat_fund_total["group_prefix"] == ["cac quy"]


def test_row_alignment_never_uses_blank_slots_as_numeric_zero_placeholders() -> None:
    table = _component_column_table(
        details=[["5", "5", None, None], ["3", "3", None, None]],
        closing=["105", "20", "33", "158"],
    )
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["closure_receipt"]["alignment_receipts"] == []
    assert "ROW_ALIGNMENT_HAS_NO_HORIZONTAL_EXACT_PLACEMENT" in candidate["reasons"]


def test_nonunique_row_alignment_remains_unresolved() -> None:
    table = _component_column_table(
        details=[["5", "5", None, None], ["5", "5", None, None]],
        closing=["105", "25", "30", "160"],
    )
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "ROW_ALIGNMENT_HAS_NO_HORIZONTAL_EXACT_PLACEMENT" in candidate["reasons"]


def test_row_alignment_without_horizontal_exact_placement_remains_unresolved() -> None:
    table = _component_column_table(
        details=[["5", "6", None, None]],
        closing=["105", "20", "30", "155"],
    )
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "ROW_ALIGNMENT_HAS_NO_HORIZONTAL_EXACT_PLACEMENT" in candidate["reasons"]


def test_row_alignment_never_reorders_visible_numeric_tokens() -> None:
    table = _component_column_table(
        details=[["5", "3", "8", None]],
        closing=["103", "25", "30", "158"],
    )
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "ROW_ALIGNMENT_HAS_NO_HORIZONTAL_EXACT_PLACEMENT" in candidate["reasons"]


def test_partial_blank_lanes_remain_null_without_blocking_observed_mappings() -> None:
    table = _component_column_table(
        details=[["10", None, "5", None], ["(5)", None, "(2)", "(7)"]],
    )
    table["rows"][1]["label_exact"] = "Tăng trong kỳ"
    table["rows"][1]["hierarchy_path_exact"] = ["Tăng trong kỳ"]
    table["rows"][2]["label_exact"] = "Giảm trong kỳ"
    table["rows"][2]["hierarchy_path_exact"] = ["Giảm trong kỳ"]

    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert candidate["reasons"] == []
    assert "INCREASE_TOTAL" not in by_role
    assert candidate["closure_receipt"]["omitted_all_blank_mapping_roles"] == [
        "INCREASE_TOTAL"
    ]
    assert [
        (value["coefficient"], value["state"])
        for value in by_role["SHARE_PREMIUM"]["values"]
    ] == [
        (20, "RAW_SIGNED_INTEGER"),
        (None, "BLANK_SOURCE_CELL"),
        (None, "BLANK_SOURCE_CELL"),
        (20, "RAW_SIGNED_INTEGER"),
    ]
    assert any(
        equation["status"] == "INCOMPLETE_BLANK_SOURCE_CELL"
        for equation in candidate["closure_receipt"]["equations"]
    )
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_component_role_with_every_source_lane_blank_is_omitted() -> None:
    table = _component_column_table(
        opening=["100", None, "30", "130"],
        details=[["10", None, "5", "15"], ["(5)", None, "(2)", "(7)"]],
        closing=["105", None, "33", "138"],
    )
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert "SHARE_PREMIUM" not in by_role
    assert candidate["closure_receipt"]["omitted_all_blank_mapping_roles"] == [
        "SHARE_PREMIUM"
    ]
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_unrelated_incomplete_role_table_without_owner_is_not_observed() -> None:
    statement_detail = {
        "columns": [_column("31/12/2025"), _column("31/12/2024")],
        "continuation": "NONE",
        "rows": [
            _row("Vốn điều lệ", ["100", "100"]),
            _row("Thặng dư vốn cổ phần", ["20", "20"]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page(_section("Báo cáo tình hình tài chính", statement_detail))
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["declared_table_inventory"] == []
    assert cluster["reasons"] == []


def test_incomplete_role_table_under_explicit_owner_remains_unresolved() -> None:
    incomplete_matrix = {
        "columns": [_column("31/12/2025"), _column("31/12/2024")],
        "continuation": "NONE",
        "rows": [
            _row("Vốn điều lệ", ["100", "100"]),
            _row("Thặng dư vốn cổ phần", ["20", "20"]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page(_section("Vốn chủ sở hữu", incomplete_matrix))
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert len(cluster["declared_table_inventory"]) == 1
    assert "DECLARED_COMPONENT_EVIDENCE_NOT_COMPLETE_MATRIX" in cluster["reasons"]


def test_complete_matrix_without_explicit_owner_remains_unresolved() -> None:
    page = _page(_section("Thuyết minh khác", _component_column_table()))
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert len(cluster["declared_table_inventory"]) == 1
    assert cluster["component_regions"] == []
    assert "EXPLICIT_BOUNDED_MATRIX_OWNER_NOT_VISIBLE" in cluster["reasons"]


def test_unconsumed_declared_role_table_after_selected_matrix_fails_closed() -> None:
    foreign = {
        "columns": [_column("31/12/2025"), _column("31/12/2024")],
        "continuation": "NONE",
        "rows": [
            _row("Vốn điều lệ", ["1", "1"]),
            _row("Thặng dư vốn cổ phần", ["1", "1"]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page(_section("Vốn chủ sở hữu", _component_column_table(), foreign))
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert "UNCONSUMED_DECLARED_COMPONENT_EVIDENCE_IN_OWNER_INTERVAL" in cluster["reasons"]


def test_single_component_percentage_control_is_not_a_competing_matrix() -> None:
    ownership = {
        "columns": [
            _column("Vốn cổ phần"),
            {"header_path_exact": ["Tỷ lệ sở hữu"], "value_kind": "PERCENTAGE"},
        ],
        "continuation": "NONE",
        "rows": [_row("Cổ đông A", ["100", "10%"]), _row(None, ["100", "100%"], kind="TOTAL")],
        "title_exact": None,
        "unit_exact": None,
    }
    page = _page(_section("Vốn chủ sở hữu", _component_column_table(), ownership))

    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )

    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 1
    assert len(cluster["declared_table_inventory"]) == 1


def test_reset_ends_owner_scope_before_later_declared_role_table() -> None:
    foreign = {
        "columns": [_column("31/12/2025"), _column("31/12/2024")],
        "continuation": "NONE",
        "rows": [
            _row("Vốn điều lệ", ["1", "1"]),
            _row("Thặng dư vốn cổ phần", ["1", "1"]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    page = _page(
        _section("Vốn chủ sở hữu", _component_column_table()),
        _section("Cổ phiếu", foreign),
    )
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 1


def test_share_word_inside_narrative_is_not_a_structural_reset() -> None:
    section = _section("Vốn chủ sở hữu", _component_column_table())
    section["narratives_exact"] = [
        "Ngân hàng đã phát hành cổ phiếu để trả cổ tức trong kỳ."
    ]
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(_page(section))], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 1
    assert cluster["owner_receipt"]["reset_fence_axis"] == []


@pytest.mark.parametrize(
    "reset_heading",
    [
        "Chi tiết vốn cổ phần của Ngân hàng tại thời điểm cuối kỳ như sau:",
        "Chi tiết phần vốn đầu tư của Ngân hàng như sau:",
        "Lãi cơ bản trên cổ phiếu",
    ],
)
def test_ordered_detail_narrative_fences_incomplete_table_on_next_page(
    reset_heading: str,
) -> None:
    detail = {
        "columns": [_column("31/12/2025"), _column("31/12/2024")],
        "continuation": "NONE",
        "rows": [
            _row("Vốn điều lệ", ["1", "1"]),
            _row("Thặng dư vốn cổ phần", ["1", "1"]),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    continuation = _section("Vốn và quỹ của Tổ chức tín dụng (tiếp theo)", detail)
    continuation["narratives_exact"] = [reset_heading]
    records = [
        _record(_page(_section("Vốn chủ sở hữu", _component_column_table())), ordinal=1),
        _record(_page(continuation), ordinal=2),
    ]
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=records, compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 1
    assert cluster["component_regions"][0]["physical_page"] == 1


def test_explicit_same_section_detail_reset_fences_only_later_table() -> None:
    detail = {
        "columns": [_column("31/12/2025"), _column("31/12/2024")],
        "continuation": "NONE",
        "rows": [
            _row("Vốn góp của cổ đông", ["1", "1"]),
            _row("Thặng dư vốn cổ phần", ["1", "1"]),
            _row("Cổ phiếu quỹ", ["-", "-"]),
            _row(None, ["2", "2"], kind="TOTAL"),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }
    section = _section("Vốn chủ sở hữu", _component_column_table(), detail)
    section["narratives_exact"] = ["Chi tiết phần vốn của TCTD như sau:"]
    cluster = coalesce_gemini_json_equity_matrix_document_v1(
        page_records=[_record(_page(section))], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 1


def test_adjacent_continuation_fragments_form_one_complete_graph() -> None:
    first = _component_column_table()
    second = copy.deepcopy(first)
    first["rows"] = first["rows"][:2]
    second["rows"] = second["rows"][2:]
    first["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    second["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    records = [
        _record(_page(_section("Vốn chủ sở hữu", first)), ordinal=1),
        _record(_page(_section("Tiếp theo", second)), ordinal=2),
    ]
    _compiled_specs, cluster, candidate = _evaluate_records(records)
    assert cluster["status"] == READY
    assert len(cluster["component_regions"]) == 2
    assert candidate["status"] == READY


def test_latest_dated_component_column_matrix_wins_over_comparative_table() -> None:
    current = _component_column_table()
    comparative = _component_column_table(
        opening=["80", "20", "10", "110"],
        details=[["5", "-", "2", "7"], ["-", "-", "-", "-"]],
        closing=["85", "20", "12", "117"],
    )
    comparative["columns"][2] = _column("Vốn khác")
    comparative["rows"][0]["label_exact"] = "Số dư tại ngày 01/01/2024"
    comparative["rows"][0]["hierarchy_path_exact"] = ["Số dư tại ngày 01/01/2024"]
    comparative["rows"][-1]["label_exact"] = "Số dư tại ngày 31/12/2024"
    comparative["rows"][-1]["hierarchy_path_exact"] = ["Số dư tại ngày 31/12/2024"]
    records = [
        _record(_page(_section("Vốn chủ sở hữu", current)), ordinal=1),
        _record(_page(_section("Tiếp theo", comparative)), ordinal=2),
    ]
    _compiled_specs, cluster, candidate = _evaluate_records(records)
    assert candidate["status"] == READY
    assert len(cluster["component_regions"]) == 1
    assert cluster["component_regions"][0]["physical_page"] == 1
    assert cluster["owner_receipt"]["period_selection_receipt"]["rule"] == (
        "UNIQUE_LATEST_SOURCE_DATED_COMPONENT_COLUMN_MATRIX"
    )


def test_conflicting_money_magnitudes_fail_closed() -> None:
    table = _component_column_table(unit="Triệu đồng; Nghìn đồng")
    _compiled_specs, _cluster, candidate = _evaluate_table(table)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any("UNIT" in reason for reason in candidate["reasons"])


@pytest.mark.parametrize(
    "surface",
    [
        "Triệu đồng Việt Nam",
        "Đơn vị tính: Triệu đồng Việt Nam",
    ],
)
def test_compound_million_vietnamese_dong_is_one_unit_declaration(surface: str) -> None:
    _compiled_specs, _cluster, candidate = _evaluate_table(
        _component_column_table(unit=surface)
    )
    assert candidate["status"] == READY
    receipt = candidate["closure_receipt"]["unit_receipt"]
    assert receipt["canonical_unit"] == "MILLION_VND"
    assert receipt["fragment_unit_axes"][0]["reasons"] == []
    assert [
        evidence["matched_alias"]
        for evidence in receipt["fragment_unit_axes"][0]["evidence"]
    ] in [["trieu dong"], ["don vi tinh trieu dong"]]


@pytest.mark.parametrize(
    "surface",
    [
        "VND million",
        "VND milion",
        "Unit: VND million",
        "Unit : VND milion",
    ],
)
def test_exact_english_million_vnd_unit_is_not_shadowed_by_bare_vnd(
    surface: str,
) -> None:
    _compiled_specs, _cluster, candidate = _evaluate_table(
        _component_column_table(unit=surface)
    )
    assert candidate["status"] == READY
    receipt = candidate["closure_receipt"]["unit_receipt"]
    assert receipt["canonical_unit"] == "MILLION_VND"
    assert receipt["fragment_unit_axes"][0]["reasons"] == []
    assert len(receipt["fragment_unit_axes"][0]["evidence"]) == 1


def test_separate_million_and_vnd_declarations_remain_conflicting() -> None:
    _compiled_specs, _cluster, candidate = _evaluate_table(
        _component_column_table(unit="Triệu đồng; VND")
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == [
        "FRAGMENT_1:CONFLICTING_DECLARED_UNIT_ALIASES_ON_ONE_SURFACE"
    ]


def test_exact_vnd_unit_is_preserved_without_rescaling_source_digits() -> None:
    _compiled_specs, _cluster, candidate = _evaluate_table(
        _component_column_table(unit="VND")
    )
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["unit_receipt"]["canonical_unit"] == "VND"
    charter = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "CHARTER_CAPITAL"
    )
    assert [value["coefficient"] for value in charter["values"]] == [100, 105]
    assert charter["unit"] == "VND"


def test_missing_local_and_document_unit_remains_unresolved() -> None:
    _compiled_specs, _cluster, candidate = _evaluate_table(
        _component_column_table(unit=None)
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS_UNAVAILABLE" in candidate["reasons"]


def _primary_statement_root_table(
    *,
    values: list[str | None],
    unit: str | None = None,
    header_unit: str | None = "VND",
    continuation: str = "NONE",
) -> dict:
    suffix = f" {header_unit}" if header_unit is not None else ""
    return {
        "columns": [
            _column(f"Số cuối kỳ{suffix}"),
            _column(f"Số đầu kỳ{suffix}"),
        ],
        "continuation": continuation,
        "rows": [_row("Vốn và các quỹ", values)],
        "title_exact": "Báo cáo tình hình tài chính",
        "unit_exact": unit,
    }


def _unrelated_unit_table(unit: str) -> dict:
    return {
        "columns": [_column("Giá trị")],
        "continuation": "NONE",
        "rows": [_row("Khoản mục khác", ["1"])],
        "title_exact": "Chi tiết khác",
        "unit_exact": unit,
    }


def _primary_statement_page(*tables: dict) -> dict:
    page = _page(_section("Báo cáo tình hình tài chính", *tables))
    page["status"] = "PRIMARY_FINANCIAL_STATEMENT"
    return page


def test_unitless_matrix_uses_unique_exact_primary_statement_root_vector_unit() -> None:
    records = [
        _record(_primary_statement_page(_primary_statement_root_table(values=["158", "150"]))),
        _record(
            _page(
                _section("Vốn chủ sở hữu", _component_column_table(unit=None)),
                _section("Chi tiết khác", _unrelated_unit_table("Triệu đồng")),
            ),
            ordinal=2,
        ),
    ]
    _compiled_specs, cluster, candidate = _evaluate_records(records)
    assert cluster["document_unit_context_evidence"]["status"] != (
        "UNIQUE_AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS"
    )
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["unit_receipt"]["canonical_unit"] == "VND"
    assert candidate["closure_receipt"]["unit_receipt"]["source"] == (
        "EXACT_PRIMARY_STATEMENT_FAMILY_ROOT_BOUNDARY_VECTOR_UNIT"
    )


@pytest.mark.parametrize(
    "primary_values",
    [
        ["159", "150"],
        ["158", None],
    ],
)
def test_primary_statement_unit_does_not_govern_without_exact_two_lane_root_match(
    primary_values: list[str | None],
) -> None:
    records = [
        _record(
            _primary_statement_page(
                _primary_statement_root_table(values=primary_values)
            )
        ),
        _record(
            _page(
                _section("Vốn chủ sở hữu", _component_column_table(unit=None)),
                _section("Chi tiết khác", _unrelated_unit_table("Triệu đồng")),
            ),
            ordinal=2,
        ),
    ]
    _compiled_specs, _cluster, candidate = _evaluate_records(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS_UNAVAILABLE" in candidate["reasons"]


def test_duplicate_matching_primary_root_vectors_do_not_choose_a_unit() -> None:
    records = [
        _record(
            _primary_statement_page(
                _primary_statement_root_table(values=["158", "150"]),
                _primary_statement_root_table(
                    values=["158", "150"], unit="Triệu đồng", header_unit=None
                ),
            )
        ),
        _record(
            _page(_section("Vốn chủ sở hữu", _component_column_table(unit=None))),
            ordinal=2,
        ),
    ]
    _compiled_specs, _cluster, candidate = _evaluate_records(records)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "AUTHENTICATED_DOCUMENT_MONEY_UNIT_CONSENSUS_UNAVAILABLE" in candidate["reasons"]


def test_primary_root_unit_may_inherit_only_from_reciprocal_adjacent_continuation() -> None:
    first = _primary_statement_root_table(
        values=["1", "1"],
        unit="Triệu đồng",
        header_unit=None,
        continuation="CONTINUES_ON_NEXT_PAGE",
    )
    first["rows"] = [_row("Tài sản", ["1", "1"])]
    continued = _primary_statement_root_table(
        values=["158", "150"],
        header_unit=None,
        continuation="CONTINUES_FROM_PREVIOUS_PAGE",
    )
    records = [
        _record(_primary_statement_page(first)),
        _record(_primary_statement_page(continued), ordinal=2),
        _record(
            _page(
                _section("Vốn chủ sở hữu", _component_column_table(unit=None)),
                _section("Chi tiết khác", _unrelated_unit_table("VND")),
            ),
            ordinal=3,
        ),
    ]
    _compiled_specs, cluster, candidate = _evaluate_records(records)
    root_evidence = cluster["document_unit_context_evidence"][
        "primary_statement_root_unit_evidence"
    ]
    assert root_evidence[0]["unit_governor"]["rule"] == (
        "EXPLICIT_RECIPROCAL_ADJACENT_PRIMARY_STATEMENT_CONTINUATION_UNIT"
    )
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["unit_receipt"]["canonical_unit"] == "MILLION_VND"


def test_candidate_replay_rejects_coherent_receipt_drift() -> None:
    compiled, cluster, candidate = _evaluate_table(_component_column_table())
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["component_axis"][0]["members_exact"] = ["Vốn giả"]
    with pytest.raises(
        GeminiJsonEquityMatrixAccountingFamilyV1Error,
        match="does not replay",
    ):
        validate_gemini_json_equity_matrix_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={
                cluster["component_regions"][0]["page_json_version_id"]: _page(
                    _section("Vốn chủ sở hữu", _component_column_table())
                )
            },
            compiled_specs=compiled,
            query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                cluster["component_regions"], owner_receipt=cluster["owner_receipt"]
            ),
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )
