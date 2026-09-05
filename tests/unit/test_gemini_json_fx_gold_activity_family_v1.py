from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_fx_gold_activity_family_v1 import (
    GeminiJsonFxGoldActivityFamilyV1Error,
    _apply_authenticated_source_repairs_v1,
    _compile_authenticated_source_repair_artifact_v1,
    adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1,
    build_gemini_json_fx_gold_activity_region_query_receipt_v1,
    build_gemini_json_fx_gold_activity_trials_v1,
    compile_gemini_json_fx_gold_activity_family_specs_v1,
    evaluate_gemini_json_fx_gold_activity_family_cluster_v1,
    validate_gemini_json_fx_gold_activity_family_candidate_replay_v1,
    validate_gemini_json_fx_gold_activity_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    GeminiJsonMultitableHierarchicalFamilyV1Error,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    classify_gemini_json_multitable_hierarchical_table_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
SOURCE_SHA256 = "b" * 64


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-fx-gold-activity-topology-v1.json"),
        _json("tm-fx-gold-activity-evaluation-v1.json"),
        _json("tm-fx-gold-activity-schema-binding-v1.json"),
    )


def _adapter_compiled(
    source_repair_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return compile_gemini_json_fx_gold_activity_family_specs_v1(
        _json("tm-fx-gold-activity-topology-v1.json"),
        _json("tm-fx-gold-activity-evaluation-v1.json"),
        _json("tm-fx-gold-activity-schema-binding-v1.json"),
        source_repair_spec,
    )


def _columns() -> list[dict[str, Any]]:
    return [
        {"header_path_exact": ["Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Năm 2024", "Triệu đồng"], "value_kind": "MONEY"},
    ]


def _row(
    label: str | None,
    values: list[str | None],
    *,
    kind: str = "ITEM",
    parent: str | None = None,
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": [label] if parent is None else [parent, label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table(
    rows: list[dict[str, Any]],
    *,
    columns: list[dict[str, Any]] | None = None,
    unit: str = "Triệu đồng",
) -> dict[str, Any]:
    return {
        "columns": _columns() if columns is None else columns,
        "continuation": "NONE",
        "rows": rows,
        "title_exact": "Lãi thuần từ hoạt động kinh doanh ngoại hối",
        "unit_exact": unit,
    }


def _page(table: dict[str, Any], *, primary: bool = False) -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT" if primary else "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "INCOME_STATEMENT" if primary else "NOT_APPLICABLE",
                "tables": [table],
                "title_exact": "Lãi thuần từ hoạt động kinh doanh ngoại hối",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT" if primary else "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict[str, Any], ordinal: int) -> dict[str, Any]:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + str(ordinal) * 64,
        "physical_page": ordinal,
        "selected_page_ordinal": ordinal,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _synthetic_source_repair() -> tuple[dict[str, Any], str, dict[str, Any]]:
    page = _page(
        _table(
            [
                _row(
                    "Chi về kinh doanh vàng",
                    [None, "1"],
                    parent="Chi phí từ hoạt động kinh doanh ngoại hối",
                )
            ]
        )
    )
    source = {
        "source_logical_name": "fixture.pdf",
        "source_sha256": "c" * 64,
        "source_size_bytes": 12345,
    }
    document_id = "gfpstorev1:document:" + canonical_json_sha256_v1(source)
    source_binding = {
        **source,
        "document_id": document_id,
        "image_sha256": "d" * 64,
        "image_size_bytes": 54321,
        "media_type": "image/png",
        "physical_page": 1,
        "pixel_height": 2000,
        "pixel_width": 1400,
        "render_dpi": 300,
    }
    source_binding["page_id"] = "gfpstorev1:page:" + canonical_json_sha256_v1(
        {
            "document_id": document_id,
            "image_sha256": source_binding["image_sha256"],
            "image_size_bytes": source_binding["image_size_bytes"],
            "media_type": source_binding["media_type"],
            "physical_page": source_binding["physical_page"],
            "pixel_height": source_binding["pixel_height"],
            "pixel_width": source_binding["pixel_width"],
            "render_dpi": source_binding["render_dpi"],
        }
    )
    extraction_run_id = "gfpstorev1:run:" + "e" * 64
    stored_sha = canonical_json_sha256_v1(page)
    version_id = "gfpstorev1:json:" + canonical_json_sha256_v1(
        {
            "canonical_json_sha256": stored_sha,
            "extraction_run_id": extraction_run_id,
            "page_id": source_binding["page_id"],
        }
    )
    effective = copy.deepcopy(page)
    effective["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "-"
    repair = {
        "base_page_json_sha256": stored_sha,
        "base_page_json_version_id": version_id,
        "cell_repairs": [
            {
                "after_exact": "-",
                "before_exact": None,
                "cell_id": "r1:c1",
                "column_header_path_exact": _columns()[0]["header_path_exact"],
                "crop_bbox_pixels_xyxy": [900, 700, 1100, 850],
                "crop_rgb_sha256": "f" * 64,
                "row_hierarchy_path_exact": [
                    "Chi phí từ hoạt động kinh doanh ngoại hối",
                    "Chi về kinh doanh vàng",
                ],
                "row_label_exact": "Chi về kinh doanh vàng",
                "visual_state": "DASH",
            }
        ],
        "effective_page_json_sha256": canonical_json_sha256_v1(effective),
        "extraction_run_id": extraction_run_id,
        "repair_reason": "VISIBLE_PDF_TRANSCRIPTION_MISMATCH",
        "source_binding": source_binding,
        "stored_canonical_json_sha256": stored_sha,
        "table_ref": {
            "base_table_sha256": canonical_json_sha256_v1(page["sections"][0]["tables"][0]),
            "effective_table_sha256": canonical_json_sha256_v1(
                effective["sections"][0]["tables"][0]
            ),
            "section_id": "s1",
            "table_id": "t1",
        },
        "visual_evidence": {
            "evidence_kind": "AUTHENTICATED_MANUAL_VISUAL_TRANSCRIPTION",
            "render_mode": "PDF_PAGE_GET_PIXMAP_DPI_EXACT_RGB",
            "reviewed_utc_date": "2026-09-04",
            "table_crop_bbox_pixels_xyxy": [100, 300, 1300, 1200],
            "table_crop_rgb_sha256": "1" * 64,
        },
    }
    repair["repair_id"] = "gjfgaasrv1:repair:" + canonical_json_sha256_v1(repair)
    artifact = {
        "family_id": "FX_GOLD_ACTIVITY",
        "format_version": ("GEMINI_JSON_FX_GOLD_ACTIVITY_AUTHENTICATED_SOURCE_REPAIR_ARTIFACT_V1"),
        "repairs": [repair],
        "review_policy": (
            "TRANSCRIBE_ONLY_AUTHENTICATED_PDF_VISIBLE_DASH_NO_EQUATION_BACKSOLVE_"
            "NO_BLANK_TO_ZERO_NO_PROVIDER"
        ),
    }
    artifact["overlay_id"] = "gjfgaasrv1:overlay:" + canonical_json_sha256_v1(artifact)
    return artifact, version_id, page


def test_fx_gold_registered_source_repairs_are_content_addressed() -> None:
    raw = json.loads(
        (ROOT / "data/registered/gemini_json_fx_gold_activity_source_repairs_v1.json").read_bytes()
    )
    compiled = _compile_authenticated_source_repair_artifact_v1(raw)
    assert canonical_json_sha256_v1(raw) == (
        "41f7cff4c6a3f26d2e0bb7b68f6714d063392a6142657e1af8f159fca8594e72"
    )
    assert compiled["overlay_id"] == (
        "gjfgaasrv1:overlay:1884ea4794e734989fb819b24a75143da063dbf98bc74b2204f5d59b40b9e398"
    )
    assert len(compiled["repairs"]) == 4
    assert sum(len(repair["cell_repairs"]) for repair in compiled["repairs"]) == 7
    assert _adapter_compiled()["fx_gold_activity_source_repair_spec_sha256"] == (
        canonical_json_sha256_v1(raw)
    )


def test_fx_gold_source_repair_applies_only_to_a_private_clone() -> None:
    artifact, version_id, page = _synthetic_source_repair()
    compiled = _adapter_compiled(artifact)
    effective, receipts = _apply_authenticated_source_repairs_v1(
        pages={version_id: page},
        compiled_specs=compiled,
    )
    assert page["sections"][0]["tables"][0]["rows"][0]["values_exact"] == [
        None,
        "1",
    ]
    assert effective[version_id]["sections"][0]["tables"][0]["rows"][0]["values_exact"] == [
        "-",
        "1",
    ]
    assert receipts == artifact["repairs"]
    replay, replay_receipts = _apply_authenticated_source_repairs_v1(
        pages={version_id: page},
        compiled_specs=compiled,
    )
    assert replay == effective
    assert replay_receipts == receipts


def test_fx_gold_source_repair_rejects_base_page_drift() -> None:
    artifact, version_id, page = _synthetic_source_repair()
    page["sections"][0]["tables"][0]["rows"][0]["values_exact"][1] = "2"
    with pytest.raises(
        GeminiJsonFxGoldActivityFamilyV1Error,
        match="base page drifted",
    ):
        _apply_authenticated_source_repairs_v1(
            pages={version_id: page},
            compiled_specs=_adapter_compiled(artifact),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "overlay-id",
        "repair-id",
        "source-identity",
        "after-value",
        "cell-order",
    ],
)
def test_fx_gold_source_repair_registry_tamper_fails_closed(
    mutation: str,
) -> None:
    if mutation == "cell-order":
        artifact = json.loads(
            (
                ROOT / "data/registered/gemini_json_fx_gold_activity_source_repairs_v1.json"
            ).read_bytes()
        )
        artifact["repairs"][0]["cell_repairs"].reverse()
    else:
        artifact, _version_id, _page = _synthetic_source_repair()
        if mutation == "overlay-id":
            artifact["overlay_id"] = "gjfgaasrv1:overlay:" + "0" * 64
        elif mutation == "repair-id":
            artifact["repairs"][0]["repair_id"] = "gjfgaasrv1:repair:" + "0" * 64
        elif mutation == "source-identity":
            artifact["repairs"][0]["source_binding"]["source_sha256"] = "0" * 64
        elif mutation == "after-value":
            artifact["repairs"][0]["cell_repairs"][0]["after_exact"] = "0"
    with pytest.raises(GeminiJsonFxGoldActivityFamilyV1Error):
        _compile_authenticated_source_repair_artifact_v1(artifact)


def _primary_rows(net: tuple[str, str] = ("70", "60")) -> list[dict[str, Any]]:
    return [_row("Lãi thuần từ hoạt động kinh doanh ngoại hối", list(net), kind="TOTAL")]


def _detail_rows(
    *,
    expense: tuple[str, str] = ("30", "20"),
    one_child: bool = False,
    combined: bool = False,
) -> list[dict[str, Any]]:
    income_parent = "Thu nhập từ hoạt động kinh doanh ngoại hối"
    expense_parent = "Chi phí từ hoạt động kinh doanh ngoại hối"
    if combined:
        income_children = [
            _row(
                "Thu từ kinh doanh ngoại tệ giao ngay và vàng",
                ["100", "80"],
                parent=income_parent,
            )
        ]
        expense_children = [
            _row(
                "Chi về kinh doanh ngoại tệ giao ngay và vàng",
                list(expense),
                parent=expense_parent,
            )
        ]
    elif one_child:
        income_children = [
            _row("Thu từ kinh doanh ngoại tệ giao ngay", ["100", "80"], parent=income_parent)
        ]
        expense_children = [
            _row("Chi từ kinh doanh ngoại tệ giao ngay", list(expense), parent=expense_parent)
        ]
    else:
        income_children = [
            _row("Thu từ kinh doanh ngoại tệ giao ngay", ["60", "50"], parent=income_parent),
            _row(
                "Thu từ các công cụ tài chính phái sinh tiền tệ",
                ["40", "30"],
                parent=income_parent,
            ),
        ]
        negative = all(value.startswith("(") for value in expense)
        expense_children = [
            _row(
                "Chi từ kinh doanh ngoại tệ giao ngay",
                ["(10)", "(5)"] if negative else ["10", "5"],
                parent=expense_parent,
            ),
            _row(
                "Chi về các công cụ tài chính phái sinh tiền tệ",
                ["(20)", "(15)"] if negative else ["20", "15"],
                parent=expense_parent,
            ),
        ]
    return [
        _row(income_parent, ["100", "80"], kind="TOTAL"),
        *income_children,
        _row(expense_parent, list(expense), kind="TOTAL"),
        *expense_children,
        _row("Lãi thuần từ hoạt động kinh doanh ngoại hối", ["70", "60"], kind="TOTAL"),
    ]


def _coalesce(pages: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records = [_record(page, ordinal) for ordinal, page in enumerate(pages, start=1)]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records,
        compiled_specs=_compiled(),
    )
    return cluster, records


def _indexed(
    cluster: dict[str, Any], records: list[dict[str, Any]], compiled: dict[str, Any]
) -> dict[str, Any]:
    document = {
        key: records[0][key]
        for key in (
            "document_id",
            "document_ordinal",
            "source_logical_name",
            "source_sha256",
        )
    }
    return build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=[document],
        selected_page_axis=[
            {
                **document,
                "page_json_version_id": record["page_json_version_id"],
                "physical_page": record["physical_page"],
                "selected_page_ordinal": record["selected_page_ordinal"],
            }
            for record in records
        ],
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )


def _evaluate(
    *,
    detail_rows: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]] | None = None,
    detail_unit: str = "Triệu đồng",
    detail_columns: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pages = [
        _page(_table(_primary_rows() if primary_rows is None else primary_rows), primary=True),
        _page(_table(detail_rows, columns=detail_columns, unit=detail_unit)),
    ]
    return _evaluate_pages(pages)


def _evaluate_pages(pages: list[dict[str, Any]]) -> dict[str, Any]:
    cluster, records = _coalesce(pages)
    assert cluster["status"] == READY
    return evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={
            record["page_json_version_id"]: record["page_json"] for record in records
        },
        compiled_specs=_compiled(),
        query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
            cluster["component_regions"]
        ),
    )


def _evaluate_note_only_adapter(
    detail_rows: list[dict[str, Any]],
    *,
    owner_title: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    page = _page(_table(detail_rows))
    if owner_title is not None:
        page["sections"][0]["title_exact"] = owner_title
        page["sections"][0]["tables"][0]["title_exact"] = None
    record = _record(page, 1)
    compiled = _adapter_compiled()
    section = page["sections"][0]
    table = section["tables"][0]
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page,
        section,
        table,
        compiled_specs=compiled,
    )
    region = {
        "component_roles": sorted({hit["role"] for hit in classification["role_hits"]}),
        "document_id": record["document_id"],
        "document_ordinal": record["document_ordinal"],
        "fragment_ordinal": 1,
        "page_json_version_id": record["page_json_version_id"],
        "physical_page": record["physical_page"],
        "section_id": "s1",
        "selected_page_ordinal": record["selected_page_ordinal"],
        "source_logical_name": record["source_logical_name"],
        "source_sha256": record["source_sha256"],
        "table_id": "t1",
    }
    regions = [region]
    pages = {record["page_json_version_id"]: page}
    query_receipt = build_gemini_json_fx_gold_activity_region_query_receipt_v1(regions)
    candidate = evaluate_gemini_json_fx_gold_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages,
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )
    return candidate, regions, pages


def test_fx_gold_split_rows_close_signed_root() -> None:
    candidate = _evaluate(detail_rows=_detail_rows())
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert set(by_role) >= {
        "INCOME_PARENT",
        "INCOME_SPOT_FX",
        "INCOME_CURRENCY_DERIVATIVES",
        "EXPENSE_PARENT",
        "EXPENSE_SPOT_FX",
        "EXPENSE_CURRENCY_DERIVATIVES",
        "FAMILY_ROOT_TOTAL",
    }
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [70, 60]


def test_fx_gold_note_terminal_source_root_replaces_wrong_direct_sum() -> None:
    candidate, regions, pages = _evaluate_note_only_adapter(_detail_rows())
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    root = by_role["FAMILY_ROOT_TOTAL"]
    assert [cell["coefficient"] for cell in root["values"]] == [70, 60]
    assert {ref["row_ordinal"] for ref in root["source_refs"]} == {7}
    assert root["state"] == (
        "SOURCE_VISIBLE_FAMILY_ROOT_VALIDATED_BY_UNIQUE_SIGNED_COMPONENT_EQUATION"
    )
    adapter_receipt = candidate["closure_receipt"]["fx_gold_activity_adapter_receipt"][
        "source_visible_signed_root_receipt"
    ]
    assert adapter_receipt["signed_root_receipt"]["multipliers"] == [1, -1]
    root_equations = [
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["result_role"] == "FAMILY_ROOT_TOTAL"
    ]
    assert len(root_equations) == 1
    assert root_equations[0]["result_coefficients"] == [70, 60]
    assert root_equations[0]["multipliers"] == [1, -1]
    compiled = _adapter_compiled()
    query_receipt = build_gemini_json_fx_gold_activity_region_query_receipt_v1(regions)
    assert (
        validate_gemini_json_fx_gold_activity_family_candidate_replay_v1(
            candidate,
            regions=regions,
            page_json_by_version=pages,
            compiled_specs=compiled,
            query_receipt=query_receipt,
        )
        == candidate
    )


def test_fx_gold_unlabeled_terminal_root_replaces_positive_expense_sum() -> None:
    candidate, _regions, _pages = _evaluate_note_only_adapter(
        [
            _row(
                "Thu nhập từ hoạt động kinh doanh ngoại hối",
                ["100", "80"],
            ),
            _row(
                "Chi phí hoạt động kinh doanh ngoại hối",
                ["30", "20"],
            ),
            _row(None, ["70", "60"], kind="TOTAL"),
        ]
    )
    assert candidate["status"] == READY
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert root["state"] == (
        "SOURCE_VISIBLE_FAMILY_ROOT_VALIDATED_BY_UNIQUE_SIGNED_COMPONENT_EQUATION"
    )
    assert [cell["coefficient"] for cell in root["values"]] == [70, 60]
    assert {ref["row_ordinal"] for ref in root["source_refs"]} == {3}
    signed = candidate["closure_receipt"]["fx_gold_activity_adapter_receipt"][
        "source_visible_signed_root_receipt"
    ]["signed_root_receipt"]
    assert signed["multipliers"] == [1, -1]
    assert signed["source_root_detection_state"] == (
        "SOURCE_VISIBLE_UNLABELED_TERMINAL_ROOT_PENDING_UNIQUE_SIGNED_COMPONENT_PROOF"
    )


def test_fx_gold_unlabeled_terminal_root_mismatch_fails_closed() -> None:
    with pytest.raises(
        GeminiJsonFxGoldActivityFamilyV1Error,
        match="sign orientation is not unique",
    ):
        _evaluate_note_only_adapter(
            [
                _row(
                    "Thu nhập từ hoạt động kinh doanh ngoại hối",
                    ["100", "80"],
                ),
                _row(
                    "Chi phí hoạt động kinh doanh ngoại hối",
                    ["30", "20"],
                ),
                _row(None, ["71", "60"], kind="TOTAL"),
            ]
        )


def test_fx_gold_detailed_unlabeled_terminal_root_is_direct_source_observation() -> None:
    income_parent = "Thu nhập từ hoạt động kinh doanh ngoại hối"
    expense_parent = "Chi phí hoạt động kinh doanh ngoại hối"
    candidate, _regions, _pages = _evaluate_note_only_adapter(
        [
            _row(income_parent, ["100", "80"], kind="SUBTOTAL"),
            _row(
                "Thu từ kinh doanh ngoại tệ giao ngay và chênh lệch đánh giá ngoại tệ kinh doanh",
                ["60", "50"],
                parent=income_parent,
            ),
            _row(
                "Thu từ các công cụ tài chính phái sinh tiền tệ",
                ["40", "30"],
                parent=income_parent,
            ),
            _row(expense_parent, ["(30)", "(20)"], kind="SUBTOTAL"),
            _row(
                "Chi từ kinh doanh ngoại tệ giao ngay và chênh lệch đánh giá lại ngoại tệ kinh doanh",
                ["(10)", "(5)"],
                parent=expense_parent,
            ),
            _row(
                "Chi từ các công cụ tài chính phái sinh tiền tệ",
                ["(20)", "(15)"],
                parent=expense_parent,
            ),
            _row(None, ["70", "60"], kind="TOTAL"),
        ]
    )
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert "INCOME_SPOT_FX_AND_REVALUATION_SOURCE_ONLY" not in by_role
    assert "EXPENSE_SPOT_FX_AND_REVALUATION_SOURCE_ONLY" not in by_role
    root = by_role["FAMILY_ROOT_TOTAL"]
    assert root["state"] == (
        "SOURCE_VISIBLE_FAMILY_ROOT_VALIDATED_BY_UNIQUE_SIGNED_COMPONENT_EQUATION"
    )
    assert [cell["coefficient"] for cell in root["values"]] == [70, 60]
    assert {ref["row_ordinal"] for ref in root["source_refs"]} == {7}
    signed = candidate["closure_receipt"]["fx_gold_activity_adapter_receipt"][
        "source_visible_signed_root_receipt"
    ]["signed_root_receipt"]
    assert signed["multipliers"] == [1, 1]
    assert signed["source_root_detection_state"] == (
        "SOURCE_VISIBLE_UNLABELED_TERMINAL_ROOT_PENDING_UNIQUE_SIGNED_COMPONENT_PROOF"
    )


def test_fx_gold_component_named_owner_still_retains_unlabeled_terminal_root() -> None:
    income_parent = "Lãi từ hoạt động kinh doanh ngoại hối"
    expense_parent = "Lỗ từ hoạt động kinh doanh ngoại hối"
    candidate, _regions, _pages = _evaluate_note_only_adapter(
        [
            _row(income_parent, ["100", "80"], kind="SUBTOTAL"),
            _row(
                "Lãi từ kinh doanh ngoại tệ giao ngay và vàng",
                ["60", "50"],
                parent=income_parent,
            ),
            _row(
                "Lãi từ các công cụ tài chính phái sinh tiền tệ",
                ["40", "30"],
                parent=income_parent,
            ),
            _row(expense_parent, ["(30)", "(20)"], kind="SUBTOTAL"),
            _row(
                "Lỗ từ kinh doanh ngoại tệ giao ngay và vàng",
                ["(10)", "(5)"],
                parent=expense_parent,
            ),
            _row(
                "Lỗ từ các công cụ tài chính phái sinh tiền tệ",
                ["(20)", "(15)"],
                parent=expense_parent,
            ),
            _row(None, ["70", "60"], kind="TOTAL"),
        ],
        owner_title="31. Lãi từ hoạt động kinh doanh ngoại hối",
    )
    assert candidate["status"] == READY
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert root["state"] == (
        "SOURCE_VISIBLE_FAMILY_ROOT_VALIDATED_BY_UNIQUE_SIGNED_COMPONENT_EQUATION"
    )
    assert [cell["coefficient"] for cell in root["values"]] == [70, 60]
    assert {ref["row_ordinal"] for ref in root["source_refs"]} == {7}


def test_fx_gold_detailed_unlabeled_terminal_root_rejects_unclassified_row() -> None:
    income_parent = "Thu nhập từ hoạt động kinh doanh ngoại hối"
    expense_parent = "Chi phí hoạt động kinh doanh ngoại hối"
    with pytest.raises(
        GeminiJsonFxGoldActivityFamilyV1Error,
        match="source-visible family root is not one complete terminal row",
    ):
        _evaluate_note_only_adapter(
            [
                _row(income_parent, ["100", "80"], kind="SUBTOTAL"),
                _row(
                    "Thu từ kinh doanh ngoại tệ giao ngay",
                    ["100", "80"],
                    parent=income_parent,
                ),
                _row(expense_parent, ["(30)", "(20)"], kind="SUBTOTAL"),
                _row(
                    "Dòng kiểm soát không khai báo",
                    ["(30)", "(20)"],
                    parent=expense_parent,
                ),
                _row(None, ["70", "60"], kind="TOTAL"),
            ]
        )


def test_fx_gold_label_only_parents_bind_printed_subtotals_and_source_root() -> None:
    income_parent = "Lãi từ kinh doanh ngoại hối"
    expense_parent = "Chi phí cho hoạt động kinh doanh ngoại hối"
    rows = [
        _row(income_parent, [None, None], kind="GROUP"),
        _row(
            "Thu từ kinh doanh ngoại tệ giao ngay",
            ["60", "50"],
            parent=income_parent,
        ),
        _row(
            "Thu từ các công cụ tài chính phái sinh tiền tệ",
            ["40", "30"],
            parent=income_parent,
        ),
        _row(None, ["100", "80"], kind="SUBTOTAL", parent=income_parent),
        _row(expense_parent, [None, None], kind="GROUP"),
        _row(
            "Chi từ kinh doanh ngoại tệ giao ngay",
            ["10", "5"],
            parent=expense_parent,
        ),
        _row(
            "Chi về các công cụ tài chính phái sinh tiền tệ",
            ["20", "15"],
            parent=expense_parent,
        ),
        _row(None, ["30", "20"], kind="SUBTOTAL", parent=expense_parent),
        _row(
            "Lãi thuần từ hoạt động kinh doanh ngoại hối",
            ["70", "60"],
            kind="TOTAL",
        ),
    ]
    candidate, _regions, _pages = _evaluate_note_only_adapter(rows)
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    label_only_state = "DECLARED_LABEL_ONLY_STRUCTURAL_GROUP_BOUND_TO_EXACT_PRINTED_RESULT"
    assert by_role["INCOME_PARENT"]["state"] == label_only_state
    assert by_role["EXPENSE_PARENT"]["state"] == label_only_state
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [70, 60]
    receipt = candidate["closure_receipt"]["fx_gold_activity_adapter_receipt"][
        "source_visible_signed_root_receipt"
    ]
    assert receipt["signed_root_receipt"]["multipliers"] == [1, -1]


def test_fx_gold_terminal_source_root_rejects_missing_declared_parent() -> None:
    income_parent = "Lãi từ kinh doanh ngoại hối"
    unknown_expense_parent = "Chi phí đối với hoạt động kinh doanh ngoại hối"
    rows = [
        _row(income_parent, [None, None], kind="GROUP"),
        _row(
            "Thu từ kinh doanh ngoại tệ giao ngay",
            ["60", "50"],
            parent=income_parent,
        ),
        _row(
            "Thu từ các công cụ tài chính phái sinh tiền tệ",
            ["40", "30"],
            parent=income_parent,
        ),
        _row(None, ["100", "80"], kind="SUBTOTAL", parent=income_parent),
        _row(unknown_expense_parent, [None, None], kind="GROUP"),
        _row(
            "Chi từ kinh doanh ngoại tệ giao ngay",
            ["10", "5"],
            parent=unknown_expense_parent,
        ),
        _row(
            "Chi về các công cụ tài chính phái sinh tiền tệ",
            ["20", "15"],
            parent=unknown_expense_parent,
        ),
        _row(
            None,
            ["30", "20"],
            kind="SUBTOTAL",
            parent=unknown_expense_parent,
        ),
        _row(
            "Lãi thuần từ hoạt động kinh doanh ngoại hối",
            ["70", "60"],
            kind="TOTAL",
        ),
    ]
    with pytest.raises(
        GeminiJsonFxGoldActivityFamilyV1Error,
        match="one complete source-observed EXPENSE_PARENT mapping",
    ):
        _evaluate_note_only_adapter(rows)


@pytest.mark.parametrize(
    "mutation,error",
    [
        (
            lambda rows: rows[-1]["values_exact"].__setitem__(0, "71"),
            "sign orientation is not unique",
        ),
        (
            lambda rows: rows.append(_row("Thu nhập khác", ["1", "1"])),
            "not one complete terminal row",
        ),
        (
            lambda rows: rows.insert(
                -1,
                _row(
                    "Lãi/lỗ thuần từ hoạt động kinh doanh ngoại hối",
                    ["71", "60"],
                    kind="TOTAL",
                ),
            ),
            "not one complete terminal row",
        ),
        (
            lambda rows: (
                rows[3].update(values_exact=["-", "-"]),
                rows[4].update(values_exact=["-", "-"]),
                rows[5].update(values_exact=["-", "-"]),
                rows[-1].update(values_exact=["100", "80"]),
            ),
            "sign orientation is not unique",
        ),
    ],
    ids=["mismatch", "nonterminal", "duplicate-root", "zero-expense-sign-ambiguous"],
)
def test_fx_gold_note_terminal_source_root_signed_projection_fails_closed(
    mutation: Any,
    error: str,
) -> None:
    rows = _detail_rows()
    mutation(rows)
    with pytest.raises(GeminiJsonFxGoldActivityFamilyV1Error, match=error):
        _evaluate_note_only_adapter(rows)


def test_fx_gold_combined_spot_and_gold_rows_remain_combined_schema_roles() -> None:
    candidate = _evaluate(detail_rows=_detail_rows(combined=True))
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert by_role["INCOME_SPOT_FX_AND_GOLD"]["report_norm_id"] == 6026
    assert by_role["EXPENSE_SPOT_FX_AND_GOLD"]["report_norm_id"] == 6027
    assert "INCOME_SPOT_FX" not in by_role
    assert "INCOME_GOLD" not in by_role


def test_fx_gold_single_declared_child_per_explicit_root_is_evaluated() -> None:
    candidate = _evaluate(detail_rows=_detail_rows(one_child=True))
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "INCOME_SPOT_FX",
        "EXPENSE_SPOT_FX",
        "FAMILY_ROOT_TOTAL",
    }


def test_fx_gold_lai_lo_source_vocabulary_maps_to_income_expense_graph() -> None:
    income_parent = "Lãi từ hoạt động kinh doanh ngoại hối"
    expense_parent = "Lỗ từ hoạt động kinh doanh ngoại hối"
    candidate = _evaluate(
        detail_rows=[
            _row(income_parent, ["100", "80"], kind="SUBTOTAL"),
            _row("Lãi từ kinh doanh ngoại tệ giao ngay", ["60", "50"], parent=income_parent),
            _row(
                "Lãi từ các công cụ tài chính phái sinh tiền tệ",
                ["40", "30"],
                parent=income_parent,
            ),
            _row(expense_parent, ["(30)", "(20)"], kind="SUBTOTAL"),
            _row("Lỗ từ kinh doanh ngoại tệ giao ngay", ["(10)", "(5)"], parent=expense_parent),
            _row(
                "Lỗ từ các công cụ tài chính phái sinh tiền tệ",
                ["(20)", "(15)"],
                parent=expense_parent,
            ),
            _row("Lãi thuần từ hoạt động kinh doanh ngoại hối", ["70", "60"], kind="TOTAL"),
        ]
    )
    assert candidate["status"] == READY


def test_fx_gold_abbreviated_parent_and_root_source_vocabulary_closes() -> None:
    income_parent = "Thu về hoạt động kinh doanh ngoại hối"
    expense_parent = "Lỗ từ kinh doanh ngoại hối"
    candidate = _evaluate(
        detail_rows=[
            _row(income_parent, ["100", "80"], kind="SUBTOTAL"),
            _row(
                "Thu từ kinh doanh ngoại tệ giao ngay",
                ["60", "50"],
                parent=income_parent,
            ),
            _row(
                "Thu từ các công cụ tài chính phái sinh tiền tệ",
                ["40", "30"],
                parent=income_parent,
            ),
            _row(expense_parent, ["30", "20"], kind="SUBTOTAL"),
            _row(
                "Chi về kinh doanh ngoại tệ giao ngay",
                ["10", "5"],
                parent=expense_parent,
            ),
            _row(
                "Chi về các công cụ tài chính phái sinh tiền tệ",
                ["20", "15"],
                parent=expense_parent,
            ),
            _row(
                "Lãi/lỗ thuần từ kinh doanh ngoại hối",
                ["70", "60"],
                kind="TOTAL",
            ),
        ]
    )
    assert candidate["status"] == READY


def test_fx_gold_combined_spot_and_revaluation_rows_are_validation_only() -> None:
    income_parent = "Thu nhập từ hoạt động kinh doanh ngoại hối"
    expense_parent = "Chi phí hoạt động kinh doanh ngoại hối"
    candidate = _evaluate(
        detail_rows=[
            _row(income_parent, ["100", "80"], kind="SUBTOTAL"),
            _row(
                "Thu từ kinh doanh ngoại tệ giao ngay và chênh lệch đánh giá ngoại tệ kinh doanh",
                ["60", "50"],
                parent=income_parent,
            ),
            _row(
                "Thu từ các công cụ tài chính phái sinh tiền tệ",
                ["40", "30"],
                parent=income_parent,
            ),
            _row(expense_parent, ["30", "20"], kind="SUBTOTAL"),
            _row(
                "Chi từ kinh doanh ngoại tệ giao ngay và chênh lệch đánh giá ngoại tệ kinh doanh",
                ["10", "5"],
                parent=expense_parent,
            ),
            _row(
                "Chi từ các công cụ tài chính phái sinh tiền tệ",
                ["20", "15"],
                parent=expense_parent,
            ),
            _row(
                "Lãi thuần từ hoạt động kinh doanh ngoại hối",
                ["70", "60"],
                kind="TOTAL",
            ),
        ]
    )
    assert candidate["status"] == READY
    roles = {mapping["role"] for mapping in candidate["mappings"]}
    assert "INCOME_SPOT_FX_AND_REVALUATION_SOURCE_ONLY" not in roles
    assert "EXPENSE_SPOT_FX_AND_REVALUATION_SOURCE_ONLY" not in roles
    assert {"INCOME_PARENT", "EXPENSE_PARENT", "FAMILY_ROOT_TOTAL"} <= roles


def test_fx_gold_negative_expense_presentation_closes_without_sign_rewrite() -> None:
    candidate = _evaluate(
        detail_rows=_detail_rows(expense=("(30)", "(20)")),
        primary_rows=_primary_rows(),
    )
    assert candidate["status"] == READY
    signed = [
        receipt
        for receipt in candidate["closure_receipt"]["root_component_sum_receipts"]
        if "multipliers" in receipt
    ]
    assert [receipt["multipliers"] for receipt in signed] == [[1, 1]]


def test_fx_gold_source_visible_vnd_unit_is_accepted_without_scale_inference() -> None:
    vnd_columns = [
        {"header_path_exact": ["Năm 2025", "VND"], "value_kind": "MONEY"},
        {"header_path_exact": ["Năm 2024", "VND"], "value_kind": "MONEY"},
    ]
    candidate = _evaluate_pages(
        [
            _page(_table(_primary_rows(), unit="VND", columns=vnd_columns), primary=True),
            _page(_table(_detail_rows(), unit="VND", columns=vnd_columns)),
        ]
    )
    assert candidate["status"] == READY
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"VND"}


def test_fx_gold_hdkd_and_combined_source_vocabulary_maps_exact_roles() -> None:
    income_parent = "Thu nhập từ HĐKD ngoại hối"
    expense_parent = "Chi phí HĐKD ngoại hối"
    candidate = _evaluate(
        detail_rows=[
            _row(income_parent, ["100", "80"], kind="SUBTOTAL"),
            _row(
                "Lãi từ kinh doanh ngoại tệ giao ngay và vàng",
                ["60", "50"],
                parent=income_parent,
            ),
            _row(
                "Thu từ công cụ tài chính phái sinh tiền tệ",
                ["40", "30"],
                parent=income_parent,
            ),
            _row(expense_parent, ["30", "20"], kind="SUBTOTAL"),
            _row(
                "Lỗ từ kinh doanh ngoại tệ giao ngay và vàng",
                ["10", "5"],
                parent=expense_parent,
            ),
            _row(
                "Chi về công cụ tài chính phái sinh tiền tệ",
                ["20", "15"],
                parent=expense_parent,
            ),
            _row("Lãi thuần từ hoạt động kinh doanh ngoại hối", ["70", "60"], kind="TOTAL"),
        ]
    )
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert by_role["INCOME_SPOT_FX_AND_GOLD"]["report_norm_id"] == 6026
    assert by_role["EXPENSE_SPOT_FX_AND_GOLD"]["report_norm_id"] == 6027


def test_fx_gold_pdf_visible_vab_thu_thi_typo_is_an_exact_gold_alias() -> None:
    income_parent = "Thu nhập từ HĐKD ngoại hối"
    expense_parent = "Chi phí HĐKD ngoại hối"
    candidate = _evaluate(
        detail_rows=[
            _row(income_parent, ["100", "80"], kind="SUBTOTAL"),
            _row(
                "Thu từ kinh doanh ngoại tệ giao ngay",
                ["60", "50"],
                parent=income_parent,
            ),
            _row("Thu thì kinh doanh vàng", ["10", "5"], parent=income_parent),
            _row(
                "Thu từ công cụ tài chính phái sinh tiền tệ",
                ["30", "25"],
                parent=income_parent,
            ),
            _row(expense_parent, ["30", "20"], kind="SUBTOTAL"),
            _row(
                "Chi về kinh doanh ngoại tệ giao ngay",
                ["10", "5"],
                parent=expense_parent,
            ),
            _row("Chi về kinh doanh vàng", ["5", "5"], parent=expense_parent),
            _row(
                "Chi về công cụ tài chính phái sinh tiền tệ",
                ["15", "10"],
                parent=expense_parent,
            ),
            _row(
                "Lãi/lỗ thuần từ hoạt động kinh doanh ngoại hối",
                ["70", "60"],
                kind="TOTAL",
            ),
        ]
    )
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["INCOME_GOLD"]["values"]] == [
        10,
        5,
    ]


def test_fx_gold_true_blank_child_lane_stays_null_while_observed_lanes_close() -> None:
    income_parent = "Thu nhập từ hoạt động kinh doanh ngoại hối"
    expense_parent = "Chi phí từ hoạt động kinh doanh ngoại hối"
    candidate, _regions, _pages = _evaluate_note_only_adapter(
        [
            _row(income_parent, ["100", "80"], kind="TOTAL"),
            _row("Thu từ kinh doanh ngoại tệ giao ngay", ["60", "80"], parent=income_parent),
            _row(
                "Thu từ các công cụ tài chính phái sinh tiền tệ",
                ["40", None],
                parent=income_parent,
            ),
            _row(expense_parent, ["30", "20"], kind="TOTAL"),
            _row("Chi từ kinh doanh ngoại tệ giao ngay", ["10", "5"], parent=expense_parent),
            _row(
                "Chi về các công cụ tài chính phái sinh tiền tệ",
                ["20", "15"],
                parent=expense_parent,
            ),
            _row("Lãi thuần từ hoạt động kinh doanh ngoại hối", ["70", "60"], kind="TOTAL"),
        ]
    )
    assert candidate["status"] == READY
    derivative = next(
        mapping
        for mapping in candidate["mappings"]
        if mapping["role"] == "INCOME_CURRENCY_DERIVATIVES"
    )
    assert [value["coefficient"] for value in derivative["values"]] == [40, None]
    assert [value["state"] for value in derivative["values"]] == [
        "RAW_SIGNED_INTEGER",
        "BLANK_SOURCE_CELL",
    ]


def test_fx_gold_source_visible_net_mismatch_is_unresolved() -> None:
    candidate = _evaluate(
        detail_rows=_detail_rows(),
        primary_rows=_primary_rows(net=("71", "61")),
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_fx_gold_duplicate_complete_detail_population_is_unresolved() -> None:
    detail = _page(_table(_detail_rows()))
    candidate = _evaluate_pages([_page(_table(_primary_rows()), primary=True), detail, detail])
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_fx_gold_unmapped_direct_money_child_is_unresolved() -> None:
    rows = _detail_rows()
    rows.insert(
        6,
        _row(
            "Khoản kinh doanh ngoại hối chưa khai báo",
            ["1", "1"],
            parent="Chi phí từ hoạt động kinh doanh ngoại hối",
        ),
    )
    rows[3]["values_exact"] = ["31", "21"]
    rows[-1]["values_exact"] = ["69", "59"]
    candidate = _evaluate(
        detail_rows=rows,
        primary_rows=_primary_rows(net=("69", "59")),
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert "UNMAPPED_DIRECT_FAMILY_SOURCE_MONEY_ROW" in candidate["reasons"]


def test_fx_gold_primary_source_result_without_detail_is_not_observed_by_generic_query() -> None:
    cluster, _records = _coalesce([_page(_table(_primary_rows()), primary=True)])
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_fx_gold_adapter_maps_unshadowed_primary_result_with_raw_source_identity() -> None:
    page = _page(
        _table(
            [
                _row("Thu nhập lãi thuần", ["9", "8"]),
                *_primary_rows(),
            ]
        ),
        primary=True,
    )
    compiled = _adapter_compiled()
    records = [_record(page, 1)]
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert raw_cluster["status"] == NOT_OBSERVED
    adapted, receipts = adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1(
        _indexed(raw_cluster, records, compiled),
        page_json_by_document={1: {records[0]["page_json_version_id"]: page}},
        compiled_specs=compiled,
    )
    assert len(receipts) == 1
    cluster = adapted["accepted_clusters"][0]
    region = cluster["component_regions"][0]
    query_receipt = build_gemini_json_fx_gold_activity_region_query_receipt_v1([region])
    candidate = evaluate_gemini_json_fx_gold_activity_family_cluster_v1(
        regions=[region],
        page_json_by_version={records[0]["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )
    assert candidate["status"] == READY
    assert [mapping["role"] for mapping in candidate["mappings"]] == ["FAMILY_ROOT_TOTAL"]
    mapping = candidate["mappings"][0]
    assert [cell["coefficient"] for cell in mapping["values"]] == [70, 60]
    assert {ref["row_ordinal"] for ref in mapping["source_refs"]} == {2}
    assert {ref["row_kind"] for ref in mapping["source_refs"]} == {"TOTAL"}
    assert (
        candidate["closure_receipt"]["fx_gold_activity_adapter_receipt"][
            "primary_root_projection_receipt"
        ]["primary_root_query_receipt_id"]
        == receipts[0]["primary_root_query_receipt_id"]
    )
    assert (
        validate_gemini_json_fx_gold_activity_family_candidate_replay_v1(
            candidate,
            regions=[region],
            page_json_by_version={records[0]["page_json_version_id"]: page},
            compiled_specs=compiled,
            query_receipt=query_receipt,
        )
        == candidate
    )

    tampered = copy.deepcopy(page)
    tampered["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = "71"
    with pytest.raises(
        GeminiJsonFxGoldActivityFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_fx_gold_activity_family_candidate_replay_v1(
            candidate,
            regions=[region],
            page_json_by_version={records[0]["page_json_version_id"]: tampered},
            compiled_specs=compiled,
            query_receipt=query_receipt,
        )


def test_fx_gold_adapter_selects_cumulative_pair_from_parallel_quarter_root() -> None:
    columns = [
        {"header_path_exact": ["Quý 4", "Năm nay"], "value_kind": "MONEY"},
        {"header_path_exact": ["Quý 4", "Năm trước"], "value_kind": "MONEY"},
        {
            "header_path_exact": [
                "Lũy kế từ đầu năm nay đến cuối quý này",
                "Năm nay",
            ],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": [
                "Lũy kế từ đầu năm nay đến cuối quý này",
                "Năm trước",
            ],
            "value_kind": "MONEY",
        },
    ]
    page = _page(
        _table(
            [
                _row(
                    "Lãi thuần từ hoạt động kinh doanh ngoại hối",
                    ["1", "2", "70", "60"],
                    kind="TOTAL",
                )
            ],
            columns=columns,
        ),
        primary=True,
    )
    compiled = _adapter_compiled()
    records = [_record(page, 1)]
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    adapted, receipts = adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1(
        _indexed(raw_cluster, records, compiled),
        page_json_by_document={1: {records[0]["page_json_version_id"]: page}},
        compiled_specs=compiled,
    )
    assert receipts[0]["money_column_ordinals"] == [3, 4]
    assert receipts[0]["source_money_column_ordinals"] == [1, 2, 3, 4]
    region = adapted["accepted_clusters"][0]["component_regions"][0]
    query_receipt = build_gemini_json_fx_gold_activity_region_query_receipt_v1([region])
    candidate = evaluate_gemini_json_fx_gold_activity_family_cluster_v1(
        regions=[region],
        page_json_by_version={records[0]["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=query_receipt,
    )
    assert candidate["status"] == READY
    assert [cell["coefficient"] for cell in candidate["mappings"][0]["values"]] == [70, 60]


def _primary_only_unit_context_pages(
    *,
    context_units: tuple[str, ...] = ("VND",),
    target_unit: str | None = None,
) -> list[dict[str, Any]]:
    columns = [
        {"header_path_exact": ["Năm 2025"], "value_kind": "MONEY"},
        {"header_path_exact": ["Năm 2024"], "value_kind": "MONEY"},
    ]
    target = _page(
        _table(
            _primary_rows(),
            columns=copy.deepcopy(columns),
            unit=target_unit,  # type: ignore[arg-type]
        ),
        primary=True,
    )
    contexts = []
    for unit in context_units:
        context = _page(
            _table(
                [_row("Thu nhập lãi thuần", ["9", "8"], kind="TOTAL")],
                columns=copy.deepcopy(columns),
                unit=unit,
            ),
            primary=True,
        )
        context["sections"][0]["title_exact"] = "Báo cáo kết quả hoạt động kinh doanh"
        context["sections"][0]["tables"][0]["title_exact"] = "Báo cáo kết quả hoạt động kinh doanh"
        contexts.append(context)
    return [target, *contexts]


def _evaluate_primary_only_unit_context(
    pages: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]]]:
    compiled = _adapter_compiled()
    records = [_record(page, ordinal) for ordinal, page in enumerate(pages, start=1)]
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )
    adapted, receipts = adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1(
        _indexed(raw_cluster, records, compiled),
        page_json_by_document={
            1: {record["page_json_version_id"]: record["page_json"] for record in records}
        },
        compiled_specs=compiled,
    )
    if not adapted["accepted_clusters"]:
        return adapted, None, records
    regions = adapted["accepted_clusters"][0]["component_regions"]
    candidate = evaluate_gemini_json_fx_gold_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version={
            record["page_json_version_id"]: record["page_json"] for record in records
        },
        compiled_specs=compiled,
        query_receipt=build_gemini_json_fx_gold_activity_region_query_receipt_v1(regions),
    )
    assert len(receipts) == 1
    return adapted, candidate, records


def test_fx_gold_unitless_primary_root_uses_unique_primary_statement_unit_context() -> None:
    pages = _primary_only_unit_context_pages()
    adapted, candidate, records = _evaluate_primary_only_unit_context(pages)
    assert candidate is not None
    assert candidate["status"] == READY
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"VND"}
    unit_receipt = candidate["closure_receipt"]["fx_gold_activity_adapter_receipt"][
        "primary_root_projection_receipt"
    ]["unit_context_receipt"]
    assert unit_receipt["canonical_unit"] == "VND"
    assert len(unit_receipt["evidence_axis"]) == 1
    assert (
        unit_receipt["target_locator"]["page_json_version_id"]
        == (records[0]["page_json_version_id"])
    )
    assert pages[0]["sections"][0]["tables"][0]["unit_exact"] is None

    regions = adapted["accepted_clusters"][0]["component_regions"]
    page_json_by_version = {
        record["page_json_version_id"]: record["page_json"] for record in records
    }
    assert (
        validate_gemini_json_fx_gold_activity_family_candidate_replay_v1(
            candidate,
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=_adapter_compiled(),
            query_receipt=build_gemini_json_fx_gold_activity_region_query_receipt_v1(regions),
        )
        == candidate
    )
    tampered = copy.deepcopy(page_json_by_version)
    tampered[records[1]["page_json_version_id"]]["sections"][0]["tables"][0]["unit_exact"] = (
        "Triệu đồng"
    )
    with pytest.raises(
        GeminiJsonFxGoldActivityFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_fx_gold_activity_family_candidate_replay_v1(
            candidate,
            regions=regions,
            page_json_by_version=tampered,
            compiled_specs=_adapter_compiled(),
            query_receipt=build_gemini_json_fx_gold_activity_region_query_receipt_v1(regions),
        )


@pytest.mark.parametrize(
    "context_units",
    [(), ("VND", "Triệu đồng"), ("Nghìn đồng",)],
    ids=["no-explicit-context", "conflicting-primary-units", "unaccepted-unit"],
)
def test_fx_gold_unitless_primary_root_unit_context_fails_closed(
    context_units: tuple[str, ...],
) -> None:
    adapted, candidate, _records = _evaluate_primary_only_unit_context(
        _primary_only_unit_context_pages(context_units=context_units)
    )
    assert candidate is None
    assert adapted["accepted_clusters"] == []


def test_fx_gold_explicit_primary_root_unit_preempts_other_statement_context() -> None:
    _adapted, candidate, _records = _evaluate_primary_only_unit_context(
        _primary_only_unit_context_pages(context_units=("Triệu đồng",), target_unit="VND")
    )
    assert candidate is not None
    assert candidate["status"] == READY
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"VND"}
    assert (
        candidate["closure_receipt"]["fx_gold_activity_adapter_receipt"][
            "primary_root_projection_receipt"
        ]["unit_context_receipt"]
        is None
    )


def _evaluate_with_unit_corroboration(
    *,
    primary_pages: list[dict[str, Any]],
    detail_unit: str | None,
    detail_net: tuple[str, str] = ("70", "60"),
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    detail_columns = [
        {"header_path_exact": ["Năm 2025"], "value_kind": "MONEY"},
        {"header_path_exact": ["Năm 2024"], "value_kind": "MONEY"},
    ]
    detail = _page(
        _table(
            _detail_rows(),
            columns=detail_columns,
            unit=detail_unit,  # type: ignore[arg-type]
        )
    )
    detail["sections"][0]["tables"][0]["rows"][-1]["values_exact"] = list(detail_net)
    pages = [*primary_pages, detail]
    compiled = _adapter_compiled()
    records = [_record(page, ordinal) for ordinal, page in enumerate(pages, start=1)]
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_fx_gold_activity_region_query_receipt_v1(
        cluster["component_regions"]
    )
    page_json_by_version = {
        record["page_json_version_id"]: record["page_json"] for record in records
    }
    candidate = evaluate_gemini_json_fx_gold_activity_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return candidate, cluster["component_regions"], page_json_by_version


def _parallel_primary_unit_page(
    *, net: tuple[str, str] = ("70", "60"), unit: str = "Đvt: triệu VNĐ"
) -> dict[str, Any]:
    columns = [
        {"header_path_exact": ["Quý 4", "Năm nay"], "value_kind": "MONEY"},
        {"header_path_exact": ["Quý 4", "Năm trước"], "value_kind": "MONEY"},
        {
            "header_path_exact": [
                "Lũy kế từ đầu năm nay đến cuối quý này",
                "Năm nay",
            ],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": [
                "Lũy kế từ đầu năm nay đến cuối quý này",
                "Năm trước",
            ],
            "value_kind": "MONEY",
        },
    ]
    return _page(
        _table(
            [
                _row(
                    "Lãi thuần từ hoạt động kinh doanh ngoại hối",
                    ["1", "2", *net],
                    kind="TOTAL",
                )
            ],
            columns=columns,
            unit=unit,
        ),
        primary=True,
    )


def _unitless_reciprocal_continuation_pages() -> list[dict[str, Any]]:
    income_parent = "Thu nhập từ hoạt động kinh doanh ngoại hối"
    expense_parent = "Chi phí từ hoạt động kinh doanh ngoại hối"
    detail_columns = [
        {"header_path_exact": ["Năm 2025"], "value_kind": "MONEY"},
        {"header_path_exact": ["Năm 2024"], "value_kind": "MONEY"},
    ]
    sender = _page(
        _table(
            [
                _row(income_parent, ["100", "80"], kind="GROUP"),
                _row(
                    "Thu từ kinh doanh ngoại tệ giao ngay",
                    ["60", "50"],
                    parent=income_parent,
                ),
                _row(
                    "Thu từ các công cụ tài chính phái sinh tiền tệ",
                    ["40", "30"],
                    parent=income_parent,
                ),
                _row(expense_parent, ["(30)", "(20)"], kind="GROUP"),
                _row(
                    "Chi từ kinh doanh ngoại tệ giao ngay",
                    ["(10)", "(5)"],
                    parent=expense_parent,
                ),
                _row("Chi từ kinh doanh vàng", ["(5)", "(5)"], parent=expense_parent),
            ],
            columns=detail_columns,
            unit=None,  # type: ignore[arg-type]
        )
    )
    sender["sections"][0]["tables"][0]["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    receiver = _page(
        _table(
            [
                _row(
                    "Chi từ các công cụ tài chính phái sinh tiền tệ",
                    ["(15)", "(10)"],
                    parent=expense_parent,
                ),
                _row(
                    "Lãi thuần từ hoạt động kinh doanh ngoại hối",
                    ["70", "60"],
                    kind="TOTAL",
                ),
            ],
            columns=[
                {"header_path_exact": [None], "value_kind": "MONEY"},
                {"header_path_exact": [None], "value_kind": "MONEY"},
            ],
            unit=None,  # type: ignore[arg-type]
        )
    )
    receiver["sections"][0]["title_exact"] = None
    receiver["sections"][0]["tables"][0]["title_exact"] = None
    receiver["sections"][0]["tables"][0]["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    return [
        _parallel_primary_unit_page(),
        sender,
        receiver,
    ]


def _evaluate_reciprocal_continuation_pages(
    pages: list[dict[str, Any]],
    *,
    mutate_records: Any = None,
) -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]]]:
    compiled = _adapter_compiled()
    records = [_record(page, ordinal) for ordinal, page in enumerate(pages, start=1)]
    if mutate_records is not None:
        mutate_records(records)
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )
    adapted, _receipts = adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1(
        _indexed(raw_cluster, records, compiled),
        page_json_by_document={
            1: {record["page_json_version_id"]: record["page_json"] for record in records}
        },
        compiled_specs=compiled,
    )
    if not adapted["accepted_clusters"]:
        return adapted, None, records
    cluster = adapted["accepted_clusters"][0]
    regions = cluster["component_regions"]
    receipt = build_gemini_json_fx_gold_activity_region_query_receipt_v1(regions)
    candidate = evaluate_gemini_json_fx_gold_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version={
            record["page_json_version_id"]: record["page_json"] for record in records
        },
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return adapted, candidate, records


def test_fx_gold_unitless_reciprocal_continuation_uses_exact_primary_unit() -> None:
    pages = _unitless_reciprocal_continuation_pages()
    adapted, candidate, records = _evaluate_reciprocal_continuation_pages(pages)
    assert candidate is not None
    assert candidate["status"] == READY
    assert [
        region["physical_page"] for region in adapted["accepted_clusters"][0]["component_regions"]
    ] == [
        2,
        3,
    ]
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        70,
        60,
    ]
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"MILLION_VND"}
    adapter = candidate["closure_receipt"]["fx_gold_activity_adapter_receipt"]
    assert len(adapter["unit_corroboration_receipts"]) == 1
    assert (
        adapter["unit_corroboration_receipts"][0]["continuation"]["receiver_locator"][
            "physical_page"
        ]
        == 3
    )
    assert (
        validate_gemini_json_fx_gold_activity_family_candidate_replay_v1(
            candidate,
            regions=adapted["accepted_clusters"][0]["component_regions"],
            page_json_by_version={
                record["page_json_version_id"]: record["page_json"] for record in records
            },
            compiled_specs=_adapter_compiled(),
            query_receipt=build_gemini_json_fx_gold_activity_region_query_receipt_v1(
                adapted["accepted_clusters"][0]["component_regions"]
            ),
        )
        == candidate
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda pages: pages[1]["sections"][0]["tables"][0].update(continuation="NONE"),
        lambda pages: pages[2]["sections"][0]["tables"][0]["columns"][0].update(
            header_path_exact=["Năm 2023"]
        ),
        lambda pages: pages[0]["sections"][0]["tables"][0]["rows"][0]["values_exact"].__setitem__(
            2, "71"
        ),
    ],
    ids=["missing-sender-marker", "receiver-period-conflict", "root-vector-mismatch"],
)
def test_fx_gold_reciprocal_continuation_unit_corroboration_fails_closed(
    mutation: Any,
) -> None:
    pages = _unitless_reciprocal_continuation_pages()
    mutation(pages)
    _adapted, candidate, _records = _evaluate_reciprocal_continuation_pages(pages)
    assert candidate is None or candidate["status"] == UNRESOLVED
    if candidate is not None:
        assert candidate["mappings"] == []


def test_fx_gold_reciprocal_continuation_requires_physical_adjacency() -> None:
    pages = _unitless_reciprocal_continuation_pages()

    def break_physical_adjacency(records: list[dict[str, Any]]) -> None:
        records[-1]["physical_page"] += 1

    _adapted, candidate, _records = _evaluate_reciprocal_continuation_pages(
        pages,
        mutate_records=break_physical_adjacency,
    )
    assert candidate is None or candidate["status"] == UNRESOLVED


def test_fx_gold_unitless_detail_uses_unique_exact_primary_root_vector_unit() -> None:
    primary = _parallel_primary_unit_page()
    alternate_vnd = _parallel_primary_unit_page(net=("70000000", "60000000"), unit="VND")
    candidate, regions, page_json_by_version = _evaluate_with_unit_corroboration(
        primary_pages=[primary, alternate_vnd], detail_unit=None
    )
    assert candidate["status"] == READY
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"MILLION_VND"}
    receipts = candidate["closure_receipt"]["fx_gold_activity_adapter_receipt"][
        "unit_corroboration_receipts"
    ]
    assert len(receipts) == 1
    assert receipts[0]["canonical_unit"] == "MILLION_VND"
    assert receipts[0]["target"]["vector"] == [70, 60]
    assert receipts[0]["governor"]["vector"] == [70, 60]
    primary_context = candidate["closure_receipt"]["fx_gold_activity_adapter_receipt"][
        "primary_result_context_receipt"
    ]
    assert {item["disposition"] for item in primary_context["primary_source_results"]} == {
        "EXACT_SAME_UNIT_ROOT_VECTOR_CORROBORATION",
        "EXPLICIT_ALTERNATE_UNIT_PRIMARY_RESULT_CONTEXT_ONLY",
    }
    assert primary["sections"][0]["tables"][0]["unit_exact"] == "Đvt: triệu VNĐ"
    detail_page = page_json_by_version["gfpstorev1:json:" + "3" * 64]
    assert detail_page["sections"][0]["tables"][0]["unit_exact"] is None
    assert (
        validate_gemini_json_fx_gold_activity_family_candidate_replay_v1(
            candidate,
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=_adapter_compiled(),
            query_receipt=build_gemini_json_fx_gold_activity_region_query_receipt_v1(regions),
        )
        == candidate
    )

    tampered = copy.deepcopy(page_json_by_version)
    tampered["gfpstorev1:json:" + "2" * 64]["sections"][0]["tables"][0]["rows"][0]["values_exact"][
        2
    ] = "70000001"
    with pytest.raises(
        GeminiJsonFxGoldActivityFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_fx_gold_activity_family_candidate_replay_v1(
            candidate,
            regions=regions,
            page_json_by_version=tampered,
            compiled_specs=_adapter_compiled(),
            query_receipt=build_gemini_json_fx_gold_activity_region_query_receipt_v1(regions),
        )


@pytest.mark.parametrize(
    ("primary_pages", "detail_unit", "detail_net"),
    [
        ([_parallel_primary_unit_page(net=("71", "60"))], None, ("70", "60")),
        (
            [
                _parallel_primary_unit_page(),
                _parallel_primary_unit_page(unit="VND"),
            ],
            None,
            ("70", "60"),
        ),
        (
            [
                _parallel_primary_unit_page(),
                _parallel_primary_unit_page(net=("71", "60")),
            ],
            None,
            ("70", "60"),
        ),
        ([_parallel_primary_unit_page()], "Nghìn đồng", ("70", "60")),
    ],
    ids=[
        "root-vector-mismatch",
        "duplicate-governors",
        "same-unit-primary-conflict",
        "explicit-conflicting-unit",
    ],
)
def test_fx_gold_primary_root_unit_corroboration_fails_closed(
    primary_pages: list[dict[str, Any]],
    detail_unit: str | None,
    detail_net: tuple[str, str],
) -> None:
    candidate, _regions, _pages = _evaluate_with_unit_corroboration(
        primary_pages=primary_pages,
        detail_unit=detail_unit,
        detail_net=detail_net,
    )
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    adapter_receipt = candidate["closure_receipt"].get("fx_gold_activity_adapter_receipt")
    if adapter_receipt is not None:
        assert adapter_receipt["primary_result_context_receipt"] is None


def test_fx_gold_adapter_does_not_replace_an_observed_note_population() -> None:
    pages = [
        _page(_table(_primary_rows()), primary=True),
        _page(_table(_detail_rows())),
    ]
    compiled = _adapter_compiled()
    records = [_record(page, ordinal) for ordinal, page in enumerate(pages, start=1)]
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert raw_cluster["status"] == READY
    adapted, receipts = adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1(
        _indexed(raw_cluster, records, compiled),
        page_json_by_document={
            1: {record["page_json_version_id"]: record["page_json"] for record in records}
        },
        compiled_specs=compiled,
    )
    assert receipts == []
    assert adapted["accepted_clusters"][0]["cluster_id"] == raw_cluster["cluster_id"]


def test_fx_gold_indexed_trial_axis_and_replay_are_source_deterministic() -> None:
    pages = [
        _page(_table(_primary_rows()), primary=True),
        _page(_table(_detail_rows())),
    ]
    compiled = _adapter_compiled()
    records = [_record(page, ordinal) for ordinal, page in enumerate(pages, start=1)]
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )
    base = _indexed(raw_cluster, records, compiled)
    pages_by_document = {
        1: {record["page_json_version_id"]: record["page_json"] for record in records}
    }
    adapted, _query_receipts = adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1(
        base,
        page_json_by_document=pages_by_document,
        compiled_specs=compiled,
    )
    trials = build_gemini_json_fx_gold_activity_trials_v1(
        indexed_query_evidence=adapted,
        page_json_by_document=pages_by_document,
        compiled_specs=compiled,
    )
    assert len(trials) == 1
    assert trials[0]["status"] == READY
    assert trials[0]["candidate_count"] == 1
    replay = validate_gemini_json_fx_gold_activity_replay_v1(
        base_indexed_query_evidence=base,
        indexed_query_evidence=adapted,
        trials=trials,
        page_json_by_document=pages_by_document,
        compiled_specs=compiled,
    )
    assert replay["trial_axis_sha256"] == canonical_json_sha256_v1(trials)

    tampered = copy.deepcopy(trials)
    tampered[0]["mappings"][0]["values"][0]["coefficient"] += 1
    with pytest.raises(
        GeminiJsonFxGoldActivityFamilyV1Error,
        match="trial replay drifted",
    ):
        validate_gemini_json_fx_gold_activity_replay_v1(
            base_indexed_query_evidence=base,
            indexed_query_evidence=adapted,
            trials=tampered,
            page_json_by_document=pages_by_document,
            compiled_specs=compiled,
        )


def test_fx_gold_single_generic_other_note_row_does_not_veto_primary_root() -> None:
    primary = _page(_table(_primary_rows()), primary=True)
    unrelated = _page(_table([_row("Chi phí khác", ["20", "15"])]))
    unrelated["sections"][0]["title_exact"] = "Chi phí hoạt động khác"
    unrelated["sections"][0]["tables"][0]["title_exact"] = "Chi phí hoạt động khác"
    compiled = _adapter_compiled()
    records = [_record(page, ordinal) for ordinal, page in enumerate([primary, unrelated], 1)]
    raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )
    assert raw_cluster["status"] == NOT_OBSERVED
    adapted, receipts = adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1(
        _indexed(raw_cluster, records, compiled),
        page_json_by_document={
            1: {record["page_json_version_id"]: record["page_json"] for record in records}
        },
        compiled_specs=compiled,
    )
    assert len(receipts) == 1
    assert adapted["accepted_clusters"][0]["status"] == READY


def test_fx_gold_adapter_rejects_duplicate_primary_results_and_blank_root() -> None:
    compiled = _adapter_compiled()
    for page in (
        _page(_table([*_primary_rows(), *_primary_rows()]), primary=True),
        _page(
            _table([_row("Lãi thuần từ hoạt động kinh doanh ngoại hối", [None, None])]),
            primary=True,
        ),
    ):
        records = [_record(page, 1)]
        raw_cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
            page_records=records, compiled_specs=compiled
        )
        adapted, receipts = adapt_gemini_json_fx_gold_activity_indexed_query_evidence_v1(
            _indexed(raw_cluster, records, compiled),
            page_json_by_document={1: {records[0]["page_json_version_id"]: page}},
            compiled_specs=compiled,
        )
        assert receipts == []
        assert adapted["accepted_clusters"] == []


def test_fx_gold_partial_detail_root_graph_is_unresolved() -> None:
    income_parent = "Thu nhập từ hoạt động kinh doanh ngoại hối"
    partial = [
        _row(income_parent, ["100", "80"], kind="TOTAL"),
        _row("Thu từ kinh doanh ngoại tệ giao ngay", ["100", "80"], parent=income_parent),
        _row("Lãi thuần từ hoạt động kinh doanh ngoại hối", ["100", "80"], kind="TOTAL"),
    ]
    cluster, _records = _coalesce(
        [_page(_table(_primary_rows(net=("100", "80"))), primary=True), _page(_table(partial))]
    )
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []


def test_fx_gold_generic_other_rows_without_explicit_root_are_not_observed() -> None:
    page = _page(_table([_row("Chi khác", ["20", "15"])]))
    page["sections"][0]["title_exact"] = "Chi phí hoạt động khác"
    page["sections"][0]["tables"][0]["title_exact"] = "Chi phí hoạt động khác"
    cluster, _records = _coalesce([page])
    assert cluster["status"] == NOT_OBSERVED


def test_fx_gold_root_row_inside_foreign_dimension_table_is_not_a_detail_signal() -> None:
    table = _table(
        [
            _row("Lãi thuần từ hoạt động kinh doanh ngoại hối", ["10", "8"]),
            _row("Lãi thuần từ hoạt động dịch vụ", ["20", "15"]),
        ]
    )
    table["title_exact"] = "Mức độ tập trung theo khu vực địa lý"
    page = _page(table)
    page["sections"][0]["title_exact"] = "Mức độ tập trung theo khu vực địa lý"
    cluster, _records = _coalesce([page])
    assert cluster["status"] == NOT_OBSERVED


@pytest.mark.parametrize(
    "control_title",
    [
        "39. Giao dịch với các bên liên quan (tiếp theo)",
        "39. Giao dịch chủ yếu với các bên liên quan (tiếp theo)",
        "23.2. Báo cáo bộ phận riêng theo khu vực địa lý",
        "Các khoản mục xử lý theo phương án cơ cấu lại giai đoạn 2023-2025",
    ],
)
def test_fx_gold_root_label_inside_declared_control_view_is_not_observed(
    control_title: str,
) -> None:
    table = _table(_primary_rows())
    table["title_exact"] = control_title
    page = _page(table)
    page["sections"][0]["title_exact"] = control_title
    cluster, _records = _coalesce([page])
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []


def test_fx_gold_related_party_row_population_under_generic_note_is_excluded() -> None:
    table = _table(
        [
            _row("Các công ty con", ["100", "80"], kind="GROUP"),
            _row(
                "Thu nhập từ hoạt động kinh doanh ngoại hối",
                ["100", "80"],
                parent="Các công ty con",
            ),
            _row(
                "Lãi thuần từ hoạt động kinh doanh ngoại hối",
                ["100", "80"],
                kind="TOTAL",
            ),
        ]
    )
    table["title_exact"] = "Giao dịch phát sinh trong năm"
    page = _page(table)
    page["sections"][0]["title_exact"] = "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT (tiếp theo)"
    cluster, _records = _coalesce([page])
    assert cluster["status"] == UNRESOLVED
    assert cluster["component_regions"] == []
    assert cluster["declared_money_table_inventory"][0]["disposition"] == ("EXCLUDED_TYPED_CONTROL")
    assert (
        cluster["declared_money_table_inventory"][0]["classification"]["typed_control_disposition"]
        == "RELATED_PARTY_ROW_POPULATION_VIEW"
    )


def test_fx_gold_conflicting_unit_and_period_evidence_fail_closed() -> None:
    unit_candidate = _evaluate(
        detail_rows=_detail_rows(),
        detail_unit="Triệu đồng; Nghìn đồng",
    )
    assert unit_candidate["status"] == UNRESOLVED
    assert unit_candidate["mappings"] == []
    period_candidate = _evaluate(
        detail_rows=_detail_rows(),
        detail_columns=[
            {"header_path_exact": ["Năm 2025", "Năm trước", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Năm 2024", "Triệu đồng"], "value_kind": "MONEY"},
        ],
    )
    assert period_candidate["status"] == UNRESOLVED
    assert period_candidate["mappings"] == []


def test_fx_gold_candidate_replay_rejects_coherent_signed_root_receipt_drift() -> None:
    pages = [
        _page(_table(_primary_rows()), primary=True),
        _page(_table(_detail_rows())),
    ]
    cluster, records = _coalesce(pages)
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        cluster["component_regions"]
    )
    page_json_by_version = {
        record["page_json_version_id"]: record["page_json"] for record in records
    }
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version=page_json_by_version,
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["root_component_sum_receipts"][0]["multipliers"] = [1, 1]
    forged["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in forged.items() if key != "candidate_id"}
    )
    with pytest.raises(
        GeminiJsonMultitableHierarchicalFamilyV1Error,
        match="candidate replay drifted",
    ):
        validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version=page_json_by_version,
            compiled_specs=_compiled(),
            query_receipt=receipt,
        )


def _terminal_cong_pages() -> list[dict[str, Any]]:
    income_parent = "Thu nhập từ hoạt động kinh doanh ngoại hối"
    expense_parent = "Chi phí từ hoạt động kinh doanh ngoại hối"
    sender = _page(
        _table(
            [
                _row(income_parent, [None, None], kind="GROUP"),
                _row(
                    "Thu từ kinh doanh ngoại tệ giao ngay",
                    ["60", "50"],
                    parent=income_parent,
                ),
                _row(
                    "Thu từ các công cụ tài chính phái sinh tiền tệ",
                    ["40", "30"],
                    parent=income_parent,
                ),
            ]
        )
    )
    sender["sections"][0]["tables"][0]["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    receiver = _page(
        _table(
            [
                _row(expense_parent, [None, None], kind="GROUP"),
                _row(
                    "Chi về kinh doanh ngoại tệ giao ngay",
                    ["(10)", "(5)"],
                    parent=expense_parent,
                ),
                _row(
                    "Chi về các công cụ tài chính phái sinh tiền tệ",
                    ["(20)", "(15)"],
                    parent=expense_parent,
                ),
                _row("Cộng", ["70", "60"], kind="TOTAL"),
            ]
        )
    )
    receiver["sections"][0]["title_exact"] = None
    receiver["sections"][0]["tables"][0]["title_exact"] = None
    receiver["sections"][0]["tables"][0]["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    return [
        _parallel_primary_unit_page(),
        sender,
        receiver,
    ]


def test_fx_gold_terminal_cong_continuation_projects_only_source_rows() -> None:
    pages = _terminal_cong_pages()
    adapted, candidate, records = _evaluate_reciprocal_continuation_pages(pages)
    assert candidate is not None
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [
        70,
        60,
    ]
    root_ref = by_role["FAMILY_ROOT_TOTAL"]["source_refs"][0]
    assert root_ref["locator"]["page_json_version_id"] == records[2]["page_json_version_id"]
    assert root_ref["row_id"] == "r4"
    assert root_ref["label_exact"] == "Cộng"
    receipt = candidate["closure_receipt"]["fx_gold_activity_adapter_receipt"][
        "terminal_cong_continuation_projection_receipt"
    ]
    assert receipt["branch_equation"]["result_vector"] == [70, 60]
    assert receipt["receiver_table"]["continuation"] == ("CONTINUES_FROM_PREVIOUS_PAGE")
    regions = adapted["accepted_clusters"][0]["component_regions"]
    page_json_by_version = {
        record["page_json_version_id"]: record["page_json"] for record in records
    }
    assert (
        validate_gemini_json_fx_gold_activity_family_candidate_replay_v1(
            candidate,
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=_adapter_compiled(),
            query_receipt=build_gemini_json_fx_gold_activity_region_query_receipt_v1(regions),
        )
        == candidate
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda pages: pages[1]["sections"][0]["tables"][0].update(continuation="NONE"),
        lambda pages: pages[2]["sections"][0]["tables"][0]["columns"][0].update(
            header_path_exact=["Năm 2023", "Triệu đồng"]
        ),
        lambda pages: pages[2]["sections"][0]["tables"][0]["rows"][-1]["values_exact"].__setitem__(
            0, "71"
        ),
        lambda pages: pages[2]["sections"][0]["tables"][0]["rows"].append(
            _row("Chi phí hoạt động khác", ["1", "1"])
        ),
    ],
    ids=["missing-marker", "conflicting-lane", "root-mismatch", "nonterminal-total"],
)
def test_fx_gold_terminal_cong_continuation_fails_closed(mutation: Any) -> None:
    pages = _terminal_cong_pages()
    mutation(pages)
    _adapted, candidate, _records = _evaluate_reciprocal_continuation_pages(pages)
    assert candidate is None or candidate["status"] == UNRESOLVED
    if candidate is not None:
        assert candidate["mappings"] == []


def test_fx_gold_terminal_cong_continuation_requires_physical_adjacency() -> None:
    pages = _terminal_cong_pages()

    def break_adjacency(records: list[dict[str, Any]]) -> None:
        records[-1]["physical_page"] += 1

    _adapted, candidate, _records = _evaluate_reciprocal_continuation_pages(
        pages, mutate_records=break_adjacency
    )
    assert candidate is None or candidate["status"] == UNRESOLVED


def _unlabeled_subtotals_pages() -> list[dict[str, Any]]:
    income_parent = "Thu nhập từ hoạt động kinh doanh ngoại hối"
    expense_parent = "Chi phí hoạt động kinh doanh ngoại hối"
    detail = _page(
        _table(
            [
                _row(income_parent, [None, None], kind="GROUP"),
                _row(
                    "Thu từ kinh doanh ngoại tệ giao ngay",
                    ["60", "50"],
                    parent=income_parent,
                ),
                _row(
                    "Thu từ kinh doanh vàng",
                    ["5", "5"],
                    parent=income_parent,
                ),
                _row(
                    "Thu từ các công cụ tài chính phái sinh tiền tệ",
                    ["35", "25"],
                    parent=income_parent,
                ),
                _row(None, ["100", "80"], kind="SUBTOTAL"),
                _row(expense_parent, [None, None], kind="GROUP"),
                _row(
                    "Chi về kinh doanh ngoại tệ giao ngay",
                    ["(10)", "(5)"],
                    parent=expense_parent,
                ),
                _row(
                    "Chi về kinh doanh vàng",
                    [None, "(5)"],
                    parent=expense_parent,
                ),
                _row(
                    "Chi về các công cụ tài chính phái sinh tiền tệ",
                    ["(20)", "(10)"],
                    parent=expense_parent,
                ),
                _row(None, ["(30)", "(20)"], kind="SUBTOTAL"),
                _row(None, ["70", "60"], kind="TOTAL"),
            ]
        )
    )
    return [_parallel_primary_unit_page(), detail]


def _evaluate_unlabeled_subtotals_pages(
    pages: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Evaluate the note region while retaining primary pages as controls."""

    compiled = _adapter_compiled()
    records = [_record(page, ordinal) for ordinal, page in enumerate(pages, start=1)]
    detail_record = records[-1]
    detail_page = detail_record["page_json"]
    detail_section = detail_page["sections"][0]
    detail_table = detail_section["tables"][0]
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        detail_page,
        detail_section,
        detail_table,
        compiled_specs=compiled,
    )
    regions = [
        {
            "component_roles": sorted(
                {
                    hit["role"]
                    for hit in classification["role_hits"]
                    if type(hit) is dict and type(hit.get("role")) is str
                }
            ),
            "document_id": detail_record["document_id"],
            "document_ordinal": detail_record["document_ordinal"],
            "fragment_ordinal": 1,
            "page_json_version_id": detail_record["page_json_version_id"],
            "physical_page": detail_record["physical_page"],
            "section_id": "s1",
            "selected_page_ordinal": detail_record["selected_page_ordinal"],
            "source_logical_name": detail_record["source_logical_name"],
            "source_sha256": detail_record["source_sha256"],
            "table_id": "t1",
        }
    ]
    page_json_by_version = {
        record["page_json_version_id"]: record["page_json"] for record in records
    }
    candidate = evaluate_gemini_json_fx_gold_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version=page_json_by_version,
        compiled_specs=compiled,
        query_receipt=build_gemini_json_fx_gold_activity_region_query_receipt_v1(regions),
    )
    return candidate, regions, records


def test_fx_gold_unlabeled_subtotals_and_root_preserve_source_locators() -> None:
    pages = _unlabeled_subtotals_pages()
    candidate, regions, records = _evaluate_unlabeled_subtotals_pages(pages)
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["EXPENSE_GOLD"]["values"]] == [
        None,
        -5,
    ]
    assert by_role["EXPENSE_GOLD"]["values"][0]["state"] == "BLANK_SOURCE_CELL"
    assert by_role["INCOME_PARENT"]["source_refs"][0]["row_id"] == ("r5")
    assert by_role["EXPENSE_PARENT"]["source_refs"][0]["row_id"] == ("r10")
    root_ref = by_role["FAMILY_ROOT_TOTAL"]["source_refs"][0]
    assert root_ref["row_id"] == "r11"
    assert root_ref["label_exact"] is None
    receipt = candidate["closure_receipt"]["fx_gold_activity_adapter_receipt"][
        "unlabeled_subtotals_and_root_projection_receipt"
    ]
    assert receipt["root_equation"]["result_vector"] == [70, 60]
    page_json_by_version = {
        record["page_json_version_id"]: record["page_json"] for record in records
    }
    assert (
        validate_gemini_json_fx_gold_activity_family_candidate_replay_v1(
            candidate,
            regions=regions,
            page_json_by_version=page_json_by_version,
            compiled_specs=_adapter_compiled(),
            query_receipt=build_gemini_json_fx_gold_activity_region_query_receipt_v1(regions),
        )
        == candidate
    )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda pages: pages[1]["sections"][0]["tables"][0]["rows"][4].update(
            label_exact="Tổng thu",
            hierarchy_path_exact=["Tổng thu"],
        ),
        lambda pages: pages[1]["sections"][0]["tables"][0]["rows"][-1]["values_exact"].__setitem__(
            0, "71"
        ),
        lambda pages: pages[1]["sections"][0]["tables"][0]["rows"].append(
            _row("Chi phí hoạt động khác", ["1", "1"])
        ),
    ],
    ids=["labeled-subtotal", "root-mismatch", "nonterminal-root"],
)
def test_fx_gold_unlabeled_subtotals_and_root_projection_fails_closed(
    mutation: Any,
) -> None:
    pages = _unlabeled_subtotals_pages()
    mutation(pages)
    candidate, _regions, _records = _evaluate_unlabeled_subtotals_pages(pages)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_fx_gold_unlabeled_root_requires_unique_primary_governor() -> None:
    pages = _unlabeled_subtotals_pages()
    pages.insert(1, _parallel_primary_unit_page())
    candidate, _regions, _records = _evaluate_unlabeled_subtotals_pages(pages)
    assert candidate["status"] == UNRESOLVED


def test_fx_gold_combined_revaluation_rows_are_validation_only() -> None:
    income_parent = "Thu nhập từ hoạt động kinh doanh ngoại hối"
    expense_parent = "Chi phí hoạt động kinh doanh ngoại hối"
    candidate = _evaluate(
        detail_rows=[
            _row(income_parent, ["100", "80"], kind="TOTAL"),
            _row(
                "Lãi từ kinh doanh ngoại tệ giao ngay",
                ["60", "50"],
                parent=income_parent,
            ),
            _row(
                "Lãi từ các công cụ tài chính phái sinh tiền tệ",
                ["30", "20"],
                parent=income_parent,
            ),
            _row("Lãi từ kinh doanh vàng", ["5", "5"], parent=income_parent),
            _row(
                "Lãi từ việc đánh giá lại ngoại tệ, vàng và các công cụ tài chính",
                ["5", "5"],
                parent=income_parent,
            ),
            _row(expense_parent, ["30", "20"], kind="TOTAL"),
            _row(
                "Lỗ từ kinh doanh ngoại tệ giao ngay",
                ["20", "10"],
                parent=expense_parent,
            ),
            _row(
                "Lỗ từ các công cụ tài chính phái sinh tiền tệ",
                ["5", "5"],
                parent=expense_parent,
            ),
            _row("Lỗ từ kinh doanh vàng", ["3", "3"], parent=expense_parent),
            _row(
                "Lỗ từ việc đánh giá lại ngoại tệ, vàng và các công cụ tài chính",
                ["2", "2"],
                parent=expense_parent,
            ),
            _row(
                "Lãi thuần từ hoạt động kinh doanh ngoại hối",
                ["70", "60"],
                kind="TOTAL",
            ),
        ]
    )
    assert candidate["status"] == READY
    roles = {mapping["role"] for mapping in candidate["mappings"]}
    assert "INCOME_FX_GOLD_AND_FINANCIAL_INSTRUMENT_REVALUATION_SOURCE_ONLY" not in roles
    assert "EXPENSE_FX_GOLD_AND_FINANCIAL_INSTRUMENT_REVALUATION_SOURCE_ONLY" not in roles
