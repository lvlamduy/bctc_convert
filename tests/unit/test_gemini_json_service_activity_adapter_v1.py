from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    classify_gemini_json_multitable_hierarchical_table_v1,
)
from bctc_ai.evaluation.gemini_json_service_activity_family_v1 import (
    ADJACENT_COMPLEMENTARY_PARENT_POLICY,
    DOCUMENT_DECLARED_RECOVERY_POLICY,
    OWNER_ONLY_CONTINUATION_CONFIG_GATE,
    OWNER_ONLY_CONTINUATION_POLICY,
    PRIMARY_SOURCE_RESULT_AUGMENTATION_POLICY,
    ROOT_ALTERNATIVE_LEGACY_FALLBACK_POLICY,
    ROOT_ALTERNATIVE_PRIMARY_PARENT_CONTROL_FALLBACK_POLICY,
    ROOT_ALTERNATIVE_PRIMARY_SOURCE_RESULT_FALLBACK_POLICY,
    GeminiJsonServiceActivityFamilyV1Error,
    _apply_authenticated_source_repairs_v1,
    _bind_exact_primary_statement_units_v1,
    _compile_authenticated_source_repair_artifact_v1,
    _normalize_governed_duration_headers_v1,
    build_gemini_json_service_activity_region_query_receipt_v1,
    coalesce_gemini_json_service_activity_document_v1,
    compile_gemini_json_service_activity_family_specs_v1,
    evaluate_gemini_json_service_activity_family_cluster_v1,
    recover_gemini_json_service_activity_query_cluster_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
REPAIR_PATH = ROOT / "data/registered/gemini_json_service_activity_source_repairs_v1.json"


def _json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_service_activity_family_specs_v1(
        _json("config/families/tm-service-activity-topology-v1.json"),
        _json("config/families/tm-service-activity-evaluation-v1.json"),
        _json("config/families/tm-service-activity-schema-binding-v1.json"),
        _json("data/registered/gemini_json_service_activity_source_repairs_v1.json"),
    )


def _fixture_artifact() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    page = {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["2025", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["2024", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [
                            {
                                "hierarchy_path_exact": ["Thụ từ dịch vụ ngân quỹ"],
                                "label_exact": "Thụ từ dịch vụ ngân quỹ",
                                "row_kind": "ITEM",
                                "values_exact": ["10", "8"],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Thu nhập từ hoạt động dịch vụ",
                                    "Dịch vụ tư vấn",
                                ],
                                "label_exact": "Dịch vụ tư vấn",
                                "row_kind": "ITEM",
                                "values_exact": ["5", None],
                            },
                        ],
                        "title_exact": "Lãi thuần từ hoạt động dịch vụ",
                        "unit_exact": "Triệu đồng",
                    }
                ],
                "title_exact": "Lãi thuần từ hoạt động dịch vụ",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    logical_name = "vietstock_bctc/FIXTURE/2025/report.pdf"
    source_sha256 = "1" * 64
    source_size_bytes = 100
    document_id = "gfpstorev1:document:" + canonical_json_sha256_v1(
        {
            "source_logical_name": logical_name,
            "source_sha256": source_sha256,
            "source_size_bytes": source_size_bytes,
        }
    )
    source = {
        "document_id": document_id,
        "image_sha256": "2" * 64,
        "image_size_bytes": 200,
        "media_type": "image/png",
        "physical_page": 2,
        "pixel_height": 100,
        "pixel_width": 100,
        "render_dpi": 300,
        "source_logical_name": logical_name,
        "source_sha256": source_sha256,
        "source_size_bytes": source_size_bytes,
    }
    source["page_id"] = "gfpstorev1:page:" + canonical_json_sha256_v1(
        {
            "document_id": document_id,
            "image_sha256": source["image_sha256"],
            "image_size_bytes": source["image_size_bytes"],
            "media_type": source["media_type"],
            "physical_page": source["physical_page"],
            "pixel_height": source["pixel_height"],
            "pixel_width": source["pixel_width"],
            "render_dpi": source["render_dpi"],
        }
    )
    extraction_run_id = "gfpstorev1:run:" + "3" * 64
    stored_sha256 = "4" * 64
    version_id = "gfpstorev1:json:" + canonical_json_sha256_v1(
        {
            "canonical_json_sha256": stored_sha256,
            "extraction_run_id": extraction_run_id,
            "page_id": source["page_id"],
        }
    )
    table = page["sections"][0]["tables"][0]
    effective = copy.deepcopy(page)
    effective_table = effective["sections"][0]["tables"][0]
    effective_table["rows"][1]["values_exact"][1] = "-"
    effective_table["rows"][0]["label_exact"] = "Thu từ dịch vụ ngân quỹ"
    effective_table["rows"][0]["hierarchy_path_exact"] = ["Thu từ dịch vụ ngân quỹ"]
    repair = {
        "base_page_json_sha256": canonical_json_sha256_v1(page),
        "base_page_json_version_id": version_id,
        "cell_repairs": [
            {
                "after_exact": "-",
                "before_exact": None,
                "cell_id": "r2:c2",
                "column_header_path_exact": ["2024", "Triệu đồng"],
                "crop_bbox_pixels_xyxy": [50, 30, 90, 50],
                "crop_rgb_sha256": "5" * 64,
                "row_hierarchy_path_exact": [
                    "Thu nhập từ hoạt động dịch vụ",
                    "Dịch vụ tư vấn",
                ],
                "row_label_exact": "Dịch vụ tư vấn",
                "visual_state": "DASH",
            }
        ],
        "effective_page_json_sha256": canonical_json_sha256_v1(effective),
        "extraction_run_id": extraction_run_id,
        "repair_reason": "VISIBLE_PDF_TRANSCRIPTION_MISMATCH",
        "row_repairs": [
            {
                "after_hierarchy_path_exact": ["Thu từ dịch vụ ngân quỹ"],
                "after_label_exact": "Thu từ dịch vụ ngân quỹ",
                "before_hierarchy_path_exact": ["Thụ từ dịch vụ ngân quỹ"],
                "before_label_exact": "Thụ từ dịch vụ ngân quỹ",
                "crop_bbox_pixels_xyxy": [5, 10, 45, 30],
                "crop_rgb_sha256": "6" * 64,
                "row_id": "r1",
                "row_kind": "ITEM",
                "visual_state": "PRINTED_LABEL",
            }
        ],
        "source_binding": source,
        "stored_canonical_json_sha256": stored_sha256,
        "table_ref": {
            "base_table_sha256": canonical_json_sha256_v1(table),
            "effective_table_sha256": canonical_json_sha256_v1(effective_table),
            "section_id": "s1",
            "table_id": "t1",
        },
        "visual_evidence": {
            "evidence_kind": "AUTHENTICATED_MANUAL_VISUAL_TRANSCRIPTION",
            "render_mode": "PDF_PAGE_GET_PIXMAP_DPI_EXACT",
            "reviewed_utc_date": "2026-09-04",
            "table_crop_bbox_pixels_xyxy": [0, 0, 100, 100],
            "table_crop_rgb_sha256": "7" * 64,
        },
    }
    repair["repair_id"] = "gjsafav1:repair:" + canonical_json_sha256_v1(repair)
    material = {
        "family_id": "SERVICE_ACTIVITY",
        "format_version": ("GEMINI_JSON_SERVICE_ACTIVITY_AUTHENTICATED_SOURCE_REPAIR_ARTIFACT_V1"),
        "repairs": [repair],
        "review_policy": (
            "TRANSCRIBE_ONLY_PDF_VISIBLE_TOKENS_NO_EQUATION_BACKSOLVE_NO_BLANK_TO_ZERO_NO_PROVIDER"
        ),
    }
    artifact = {
        **material,
        "overlay_id": "gjsafav1:overlay:" + canonical_json_sha256_v1(material),
    }
    region = {
        "page_json_version_id": version_id,
        "physical_page": 2,
        "section_id": "s1",
        "source_logical_name": logical_name,
        "source_sha256": source_sha256,
        "table_id": "t1",
    }
    return artifact, page, region


def test_registered_service_activity_repairs_compile_and_seal_exact_axis() -> None:
    raw = json.loads(REPAIR_PATH.read_bytes())
    compiled = _compile_authenticated_source_repair_artifact_v1(raw)
    assert compiled["overlay_id"] == (
        "gjsafav1:overlay:33575846ee64630de7c4fc5bcc906be946a983b04c8558f7189bf1fc533111f3"
    )
    assert len(compiled["repairs"]) == 8
    assert sum(len(item["cell_repairs"]) for item in compiled["repairs"]) == 15
    assert sum(len(item["row_repairs"]) for item in compiled["repairs"]) == 1
    assert _compiled()["service_activity_source_repair_overlay"] == compiled


@pytest.mark.parametrize("tamper_kind", ["cell", "image", "bbox", "overlay"])
def test_service_activity_repair_artifact_tampering_fails_closed(
    tamper_kind: str,
) -> None:
    artifact, _page, _region = _fixture_artifact()
    tampered = copy.deepcopy(artifact)
    if tamper_kind == "cell":
        tampered["repairs"][0]["cell_repairs"][0]["after_exact"] = "0"
    elif tamper_kind == "image":
        tampered["repairs"][0]["source_binding"]["image_sha256"] = "8" * 64
    elif tamper_kind == "bbox":
        tampered["repairs"][0]["cell_repairs"][0]["crop_bbox_pixels_xyxy"] = [90, 30, 101, 50]
    else:
        tampered["overlay_id"] = "gjsafav1:overlay:" + "9" * 64
    with pytest.raises(GeminiJsonServiceActivityFamilyV1Error):
        _compile_authenticated_source_repair_artifact_v1(tampered)


def test_service_activity_cell_and_label_repairs_are_private_clone_only() -> None:
    artifact, page, region = _fixture_artifact()
    compiled = {
        "service_activity_source_repair_overlay": (
            _compile_authenticated_source_repair_artifact_v1(artifact)
        )
    }
    effective, receipts = _apply_authenticated_source_repairs_v1(
        regions=[region],
        page_json_by_version={region["page_json_version_id"]: page},
        compiled_specs=compiled,
    )
    effective_rows = effective[region["page_json_version_id"]]["sections"][0]["tables"][0]["rows"]
    assert effective_rows[0]["label_exact"] == "Thu từ dịch vụ ngân quỹ"
    assert effective_rows[1]["values_exact"][1] == "-"
    original_rows = page["sections"][0]["tables"][0]["rows"]
    assert original_rows[0]["label_exact"] == "Thụ từ dịch vụ ngân quỹ"
    assert original_rows[1]["values_exact"][1] is None
    assert len(receipts) == 1
    assert receipts[0]["status"] == "AUTHENTICATED_PDF_VISIBLE_SOURCE_TRANSCRIBED"

    drifted = copy.deepcopy(page)
    drifted["sections"][0]["tables"][0]["rows"][1]["values_exact"][1] = "0"
    with pytest.raises(
        GeminiJsonServiceActivityFamilyV1Error,
        match="base page drifted",
    ):
        _apply_authenticated_source_repairs_v1(
            regions=[region],
            page_json_by_version={region["page_json_version_id"]: drifted},
            compiled_specs=compiled,
        )


@pytest.mark.parametrize(
    "governor",
    [
        "Lũy kế từ đầu kỳ đến",
        "Lũy kế từ đầu năm đến cuối kỳ này",
        "9 tháng đầu năm",
    ],
)
def test_service_activity_duration_governor_removes_only_whole_components(
    governor: str,
) -> None:
    artifact, page, region = _fixture_artifact()
    del artifact
    table = page["sections"][0]["tables"][0]
    table["columns"][0]["header_path_exact"] = [
        governor,
        "31/12/2025",
        "Triệu đồng",
    ]
    table["columns"][1]["header_path_exact"] = [
        governor,
        "31/12/2024",
        "Triệu đồng",
    ]
    pages = {region["page_json_version_id"]: page}
    receipts = _normalize_governed_duration_headers_v1(
        pages=pages,
        regions=[region],
    )
    assert [column["header_path_exact"] for column in table["columns"]] == [
        ["31/12/2025", "Triệu đồng"],
        ["31/12/2024", "Triệu đồng"],
    ]
    assert len(receipts) == 1


def test_service_activity_duration_normalization_fails_closed_on_mixed_axis() -> None:
    _artifact, page, region = _fixture_artifact()
    table = page["sections"][0]["tables"][0]
    table["columns"][0]["header_path_exact"] = [
        "Lũy kế từ đầu kỳ đến",
        "31/12/2025",
    ]
    table["columns"][1]["header_path_exact"] = ["31/12/2024"]
    before = copy.deepcopy(table["columns"])
    assert (
        _normalize_governed_duration_headers_v1(
            pages={region["page_json_version_id"]: page},
            regions=[region],
        )
        == []
    )
    assert table["columns"] == before


def _unit_control_page(
    *,
    primary: bool,
    unit_exact: str | None,
    income: list[str | None],
    expense: list[str | None],
    root: list[str | None],
) -> dict[str, Any]:
    columns = (
        [
            {"header_path_exact": ["Quý này"], "value_kind": "MONEY"},
            {"header_path_exact": ["Quý trước"], "value_kind": "MONEY"},
            {"header_path_exact": ["Lũy kế năm nay"], "value_kind": "MONEY"},
            {"header_path_exact": ["Lũy kế năm trước"], "value_kind": "MONEY"},
        ]
        if primary
        else [
            {"header_path_exact": ["Kỳ này"], "value_kind": "MONEY"},
            {"header_path_exact": ["Kỳ trước"], "value_kind": "MONEY"},
        ]
    )
    rows = [
        {
            "hierarchy_path_exact": ["3- Thu nhập từ hoạt động dịch vụ"],
            "label_exact": "3- Thu nhập từ hoạt động dịch vụ",
            "row_kind": "SUBTOTAL",
            "values_exact": income,
        },
        {
            "hierarchy_path_exact": ["4- Chi phí hoạt động dịch vụ"],
            "label_exact": "4- Chi phí hoạt động dịch vụ",
            "row_kind": "SUBTOTAL",
            "values_exact": expense,
        },
        {
            "hierarchy_path_exact": ["II- Lãi thuần từ hoạt động dịch vụ"],
            "label_exact": "II- Lãi thuần từ hoạt động dịch vụ",
            "row_kind": "TOTAL",
            "values_exact": root,
        },
    ]
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT" if primary else "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "INCOME_STATEMENT" if primary else "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": columns,
                        "continuation": "NONE",
                        "rows": rows,
                        "title_exact": "Lãi thuần từ hoạt động dịch vụ",
                        "unit_exact": unit_exact,
                    }
                ],
                "title_exact": "Lãi thuần từ hoạt động dịch vụ",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT" if primary else "FINANCIAL_NOTE_CONTENT",
    }


def _unit_region(version_id: str) -> dict[str, Any]:
    return {
        "page_json_version_id": version_id,
        "physical_page": 42,
        "section_id": "s1",
        "table_id": "t1",
    }


def test_service_activity_unitless_note_binds_exact_same_role_parent_control() -> None:
    primary_id = "gfpstorev1:json:" + "a" * 64
    note_id = "gfpstorev1:json:" + "b" * 64
    primary = _unit_control_page(
        primary=True,
        unit_exact="Triệu đồng",
        income=["1", "2", "102", "81"],
        expense=["3", "4", "(30)", "(20)"],
        root=["4", "6", "72", "61"],
    )
    note = _unit_control_page(
        primary=False,
        unit_exact=None,
        income=["101", "80"],
        expense=["(30)", "(20)"],
        root=["71", "60"],
    )
    receipts = _bind_exact_primary_statement_units_v1(
        pages={primary_id: primary, note_id: note},
        regions=[_unit_region(note_id)],
        compiled_specs=_compiled(),
    )
    assert note["sections"][0]["tables"][0]["unit_exact"] == "Triệu đồng"
    assert len(receipts) == 1
    assert receipts[0]["canonical_unit"] == "MILLION_VND"
    assert [item["semantic_role"] for item in receipts[0]["matched_target_controls"]] == [
        "EXPENSE_PARENT"
    ]
    assert [item["semantic_role"] for item in receipts[0]["matched_primary_controls"]] == [
        "EXPENSE_PARENT"
    ]
    assert receipts[0]["matched_primary_controls"][0]["matched_primary_money_column_ordinals"] == [
        3,
        4,
    ]
    assert "NO_MAGNITUDE_INFERENCE" in receipts[0]["rule"]


@pytest.mark.parametrize(
    "failure_kind",
    [
        "PARTIAL_TARGET",
        "OTHER_ROLE_VALUE_ONLY",
        "CONFLICTING_CANONICAL_UNITS",
        "ALL_ZERO_CONTROL",
    ],
)
def test_service_activity_primary_control_unit_corroboration_fails_closed(
    failure_kind: str,
) -> None:
    primary_id = "gfpstorev1:json:" + "c" * 64
    note_id = "gfpstorev1:json:" + "d" * 64
    primary = _unit_control_page(
        primary=True,
        unit_exact="Triệu đồng",
        income=["1", "2", "102", "81"],
        expense=["3", "4", "(31)", "(21)"],
        root=["5", "6", "72", "61"],
    )
    note = _unit_control_page(
        primary=False,
        unit_exact=None,
        income=["101", "80"],
        expense=["(30)", "(20)"],
        root=["71", "60"],
    )
    pages = {primary_id: primary, note_id: note}
    if failure_kind == "PARTIAL_TARGET":
        note["sections"][0]["tables"][0]["rows"][1]["values_exact"][1] = None
    elif failure_kind == "OTHER_ROLE_VALUE_ONLY":
        primary["sections"][0]["tables"][0]["rows"][2]["values_exact"][2:] = [
            "(30)",
            "(20)",
        ]
    elif failure_kind == "CONFLICTING_CANONICAL_UNITS":
        primary["sections"][0]["tables"][0]["rows"][1]["values_exact"][2:] = [
            "(30)",
            "(20)",
        ]
        vnd_id = "gfpstorev1:json:" + "e" * 64
        pages[vnd_id] = _unit_control_page(
            primary=True,
            unit_exact="VND",
            income=["1", "2", "102", "81"],
            expense=["3", "4", "(30)", "(20)"],
            root=["5", "6", "72", "61"],
        )
    else:
        note["sections"][0]["tables"][0]["rows"][1]["values_exact"] = ["0", "0"]
    receipts = _bind_exact_primary_statement_units_v1(
        pages=pages,
        regions=[_unit_region(note_id)],
        compiled_specs=_compiled(),
    )
    assert receipts == []
    assert note["sections"][0]["tables"][0]["unit_exact"] is None


def test_service_activity_unit_corroboration_accepts_repeated_exact_q1_period_vector() -> None:
    primary_id = "gfpstorev1:json:" + "1" * 64
    note_id = "gfpstorev1:json:" + "2" * 64
    primary = _unit_control_page(
        primary=True,
        unit_exact="Triệu đồng",
        income=["1", "2", "102", "81"],
        expense=["(30)", "(20)", "(30)", "(20)"],
        root=["5", "6", "72", "61"],
    )
    note = _unit_control_page(
        primary=False,
        unit_exact=None,
        income=["101", "80"],
        expense=["(30)", "(20)"],
        root=["71", "60"],
    )
    receipts = _bind_exact_primary_statement_units_v1(
        pages={primary_id: primary, note_id: note},
        regions=[_unit_region(note_id)],
        compiled_specs=_compiled(),
    )
    assert note["sections"][0]["tables"][0]["unit_exact"] == "Triệu đồng"
    assert len(receipts) == 1
    matches = receipts[0]["matched_primary_controls"]
    assert len(matches) == 1
    assert matches[0]["semantic_role"] == "EXPENSE_PARENT"
    assert matches[0]["matched_primary_money_column_ordinal_axes"] == [
        [1, 2],
        [3, 4],
    ]
    assert "matched_primary_money_column_ordinals" not in matches[0]
    assert "NO_MAGNITUDE_INFERENCE" in receipts[0]["rule"]


def _owner_only_page(title: str = "26. Lãi thuần từ hoạt động dịch vụ") -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [],
                "title_exact": title,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _from_previous_service_page() -> dict[str, Any]:
    income = "Thu phí dịch vụ"
    expense = "Chi về dịch vụ"
    rows = [
        {
            "hierarchy_path_exact": [income],
            "label_exact": income,
            "row_kind": "GROUP",
            "values_exact": ["100", "80"],
        },
        {
            "hierarchy_path_exact": [income, "Dịch vụ thanh toán"],
            "label_exact": "Dịch vụ thanh toán",
            "row_kind": "ITEM",
            "values_exact": ["60", "50"],
        },
        {
            "hierarchy_path_exact": [income, "Dịch vụ Ngân quỹ"],
            "label_exact": "Dịch vụ Ngân quỹ",
            "row_kind": "ITEM",
            "values_exact": ["10", "5"],
        },
        {
            "hierarchy_path_exact": [income, "Dịch vụ khác"],
            "label_exact": "Dịch vụ khác",
            "row_kind": "ITEM",
            "values_exact": ["30", "25"],
        },
        {
            "hierarchy_path_exact": [expense],
            "label_exact": expense,
            "row_kind": "GROUP",
            "values_exact": ["(30)", "(20)"],
        },
        {
            "hierarchy_path_exact": [expense, "Dịch vụ thanh toán"],
            "label_exact": "Dịch vụ thanh toán",
            "row_kind": "ITEM",
            "values_exact": ["(10)", "(5)"],
        },
        {
            "hierarchy_path_exact": [expense, "Dịch vụ khác"],
            "label_exact": "Dịch vụ khác",
            "row_kind": "ITEM",
            "values_exact": ["(20)", "(15)"],
        },
        {
            "hierarchy_path_exact": ["Lãi thuần từ hoạt động dịch vụ"],
            "label_exact": "Lãi thuần từ hoạt động dịch vụ",
            "row_kind": "TOTAL",
            "values_exact": ["70", "60"],
        },
    ]
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": [
                            {"header_path_exact": ["Kỳ này"], "value_kind": "MONEY"},
                            {"header_path_exact": ["Kỳ trước"], "value_kind": "MONEY"},
                        ],
                        "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
                        "rows": rows,
                        "title_exact": None,
                        "unit_exact": None,
                    }
                ],
                "title_exact": None,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _page_record(
    page: dict[str, Any], *, selected_ordinal: int, physical_page: int
) -> dict[str, Any]:
    return {
        "document_id": "gfpstorev1:document:" + "a" * 64,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + str(selected_ordinal) * 64,
        "physical_page": physical_page,
        "selected_page_ordinal": selected_ordinal,
        "source_logical_name": "vietstock_bctc/VAB/2026/report.pdf",
        "source_sha256": "b" * 64,
    }


def _two_parent_service_page_without_explicit_root() -> dict[str, Any]:
    income = "Thu nhập từ hoạt động dịch vụ"
    expense = "Chi phí hoạt động dịch vụ"
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["Năm 2025", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Năm 2024", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [
                            {
                                "hierarchy_path_exact": [income],
                                "label_exact": income,
                                "row_kind": "TOTAL",
                                "values_exact": ["100", "80"],
                            },
                            {
                                "hierarchy_path_exact": [income, "Thu từ dịch vụ thanh toán"],
                                "label_exact": "Thu từ dịch vụ thanh toán",
                                "row_kind": "ITEM",
                                "values_exact": ["60", "50"],
                            },
                            {
                                "hierarchy_path_exact": [income, "Thu nhập khác"],
                                "label_exact": "Thu nhập khác",
                                "row_kind": "ITEM",
                                "values_exact": ["40", "30"],
                            },
                            {
                                "hierarchy_path_exact": [expense],
                                "label_exact": expense,
                                "row_kind": "TOTAL",
                                "values_exact": ["(30)", "(20)"],
                            },
                            {
                                "hierarchy_path_exact": [expense, "Chi về dịch vụ thanh toán"],
                                "label_exact": "Chi về dịch vụ thanh toán",
                                "row_kind": "ITEM",
                                "values_exact": ["(10)", "(5)"],
                            },
                            {
                                "hierarchy_path_exact": [expense, "Chi phí khác"],
                                "label_exact": "Chi phí khác",
                                "row_kind": "ITEM",
                                "values_exact": ["(20)", "(15)"],
                            },
                        ],
                        "title_exact": "Lãi thuần từ hoạt động dịch vụ",
                        "unit_exact": "Triệu đồng",
                    }
                ],
                "title_exact": "Lãi thuần từ hoạt động dịch vụ",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _evaluate_two_parent_service_page(page: dict[str, Any]) -> dict[str, Any]:
    record = _page_record(page, selected_ordinal=1, physical_page=1)
    compiled = _compiled()
    section = page["sections"][0]
    table = section["tables"][0]
    classification = classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, table, compiled_specs=compiled
    )
    component_roles = sorted(
        {
            hit["role"]
            for hit in classification["role_hits"]
        }
        | set(classification["context_roles"])
    )
    regions = [
        {
            "component_roles": component_roles,
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
    ]
    receipt = build_gemini_json_service_activity_region_query_receipt_v1(
        regions
    )
    return evaluate_gemini_json_service_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version={record["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )


def test_service_activity_root_alternatives_preserve_complete_legacy_two_parent_sum() -> None:
    candidate = _evaluate_two_parent_service_page(
        _two_parent_service_page_without_explicit_root()
    )
    assert candidate["status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    root = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL")
    assert [value["coefficient"] for value in root["values"]] == [70, 60]
    fallback = candidate["closure_receipt"]["service_activity_adapter_receipt"][
        "root_alternative_legacy_fallback_receipt"
    ]
    assert fallback["policy"] == ROOT_ALTERNATIVE_LEGACY_FALLBACK_POLICY
    assert fallback["first_declared_legacy_alternative"]["roles"] == [
        "INCOME_PARENT",
        "EXPENSE_PARENT",
    ]


def test_service_activity_root_alternative_legacy_fallback_requires_complete_frontier() -> None:
    page = _two_parent_service_page_without_explicit_root()
    del page["sections"][0]["tables"][0]["rows"][3:]
    candidate = _evaluate_two_parent_service_page(page)
    assert candidate["status"] == "UNRESOLVED_GEMINI_JSON_FAMILY"
    assert candidate["mappings"] == []
    assert "service_activity_adapter_receipt" not in candidate["closure_receipt"]


def test_service_activity_owner_only_adjacent_section_recovers_exact_receiver() -> None:
    owner = _owner_only_page()
    receiver = _from_previous_service_page()
    before = copy.deepcopy([owner, receiver])
    compiled = _compiled()
    assert compiled["continuation_leading_child_scope_policy"] == (
        OWNER_ONLY_CONTINUATION_CONFIG_GATE
    )
    assert "service_activity_owner_only_continuation_policy" not in compiled["query_policy"]
    cluster = coalesce_gemini_json_service_activity_document_v1(
        page_records=[
            _page_record(owner, selected_ordinal=1, physical_page=42),
            _page_record(receiver, selected_ordinal=2, physical_page=43),
        ],
        compiled_specs=compiled,
    )
    assert cluster["status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    assert [(item["physical_page"], item["section_id"], item["table_id"]) for item in cluster["component_regions"]] == [
        (43, "s1", "t1")
    ]
    receipt = cluster["owner_receipt"]
    assert receipt["policy"] == OWNER_ONLY_CONTINUATION_POLICY
    assert receipt["owner_section"]["source_exact"] == (
        "26. Lãi thuần từ hoạt động dịch vụ"
    )
    assert receipt["owner_section"]["money_table_count"] == 0
    assert receipt["receiver_table"]["explicit_period_axis"]["semantic_roles"] == [
        "CURRENT_PERIOD",
        "COMPARATIVE_PERIOD",
    ]
    assert [owner, receiver] == before


def test_service_activity_owner_only_recovery_requires_exact_family_config_gate() -> None:
    owner = _owner_only_page()
    receiver = _from_previous_service_page()
    compiled = _compiled()
    compiled["continuation_leading_child_scope_policy"] = "DISABLED"
    cluster = coalesce_gemini_json_service_activity_document_v1(
        page_records=[
            _page_record(owner, selected_ordinal=1, physical_page=42),
            _page_record(receiver, selected_ordinal=2, physical_page=43),
        ],
        compiled_specs=compiled,
    )
    assert cluster["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert cluster["component_regions"] == []


def _document_declared_recovery_fixture() -> list[dict[str, Any]]:
    note = _from_previous_service_page()
    note_section = note["sections"][0]
    note_table = note_section["tables"][0]
    note_section["title_exact"] = "26. Lãi thuần từ hoạt động dịch vụ"
    note_table["continuation"] = "NONE"
    note_table["unit_exact"] = "Triệu đồng"
    primary = _unit_control_page(
        primary=True,
        unit_exact="Triệu đồng",
        income=["100", "80"],
        expense=["(30)", "(20)"],
        root=["70", "60"],
    )
    primary_table = primary["sections"][0]["tables"][0]
    primary_table["columns"] = copy.deepcopy(
        note_table["columns"]
    )
    primary_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    primary_table["rows"][0]["row_kind"] = "ITEM"
    primary_table["rows"][1]["row_kind"] = "ITEM"
    primary_table["rows"][2]["row_kind"] = "SUBTOTAL"
    return [
        _page_record(primary, selected_ordinal=1, physical_page=10),
        _page_record(note, selected_ordinal=2, physical_page=42),
    ]


def test_service_activity_recovers_exact_document_declared_source_result_graph() -> None:
    records = _document_declared_recovery_fixture()
    before = copy.deepcopy(records)
    compiled = _compiled()
    preliminary = coalesce_gemini_json_service_activity_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )
    base = _reseal_test_cluster(
        {
            **preliminary,
            "component_regions": [],
            "owner_receipt": None,
            "reasons": ["COMPLETE_OWNER_CLUSTER_NOT_RESOLVED"],
            "status": "UNRESOLVED_GEMINI_JSON_FAMILY",
        }
    )
    cluster = recover_gemini_json_service_activity_query_cluster_v1(
        page_records=records,
        base_cluster=base,
        compiled_specs=compiled,
    )
    assert records == before
    assert cluster["status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    assert [
        (region["physical_page"], region["section_id"], region["table_id"])
        for region in cluster["component_regions"]
    ] == [(10, "s1", "t1"), (42, "s1", "t1")]
    assert cluster["owner_receipt"][
        "service_activity_document_declared_recovery_policy"
    ] == DOCUMENT_DECLARED_RECOVERY_POLICY

    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_service_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version={
            record["page_json_version_id"]: record["page_json"] for record in records
        },
        compiled_specs=compiled,
        query_receipt=build_gemini_json_service_activity_region_query_receipt_v1(
            regions
        ),
    )
    assert candidate["status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    root = next(
        mapping
        for mapping in candidate["mappings"]
        if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [value["coefficient"] for value in root["values"]] == [70, 60]
    assert all(value["state"] == "RAW_SIGNED_INTEGER" for value in root["values"])


def test_service_activity_primary_statement_only_is_not_a_detail_population() -> None:
    primary = _unit_control_page(
        primary=True,
        unit_exact="Triệu đồng",
        income=["1", "2", "100", "80"],
        expense=["3", "4", "(30)", "(20)"],
        root=["4", "6", "70", "60"],
    )
    primary["sections"][0]["tables"][0]["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    records = [_page_record(primary, selected_ordinal=1, physical_page=10)]
    preliminary = coalesce_gemini_json_service_activity_document_v1(
        page_records=records,
        compiled_specs=_compiled(),
    )
    base = _reseal_test_cluster(
        {
            **preliminary,
            "component_regions": [],
            "owner_receipt": None,
            "reasons": ["COMPLETE_OWNER_CLUSTER_NOT_RESOLVED"],
            "status": "UNRESOLVED_GEMINI_JSON_FAMILY",
        }
    )
    cluster = recover_gemini_json_service_activity_query_cluster_v1(
        page_records=records,
        base_cluster=base,
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert cluster["component_regions"] == []
    assert cluster["owner_receipt"]["detailed_root_roles"] == []
    assert cluster["owner_receipt"][
        "service_activity_document_declared_recovery_policy"
    ] == DOCUMENT_DECLARED_RECOVERY_POLICY


@pytest.mark.parametrize(
    "failure_kind",
    ["POLICY_DISABLED", "INCOMPLETE_DETAIL", "DUPLICATE_PRIMARY", "DUPLICATE_DETAIL"],
)
def test_service_activity_document_declared_recovery_fails_closed(
    failure_kind: str,
) -> None:
    records = _document_declared_recovery_fixture()
    compiled = _compiled()
    if failure_kind == "POLICY_DISABLED":
        compiled["document_cluster_policy"] = "ONE_EXPLICIT_OWNER_RESET_FENCE"
    elif failure_kind == "INCOMPLETE_DETAIL":
        del records[1]["page_json"]["sections"][0]["tables"][0]["rows"][3:]
    elif failure_kind == "DUPLICATE_PRIMARY":
        duplicate = copy.deepcopy(records[0]["page_json"])
        records.insert(
            1,
            _page_record(duplicate, selected_ordinal=2, physical_page=11),
        )
        records[2]["selected_page_ordinal"] = 3
        records[2]["page_json_version_id"] = "gfpstorev1:json:" + "3" * 64
    else:
        duplicate = copy.deepcopy(records[1]["page_json"])
        records.append(
            _page_record(duplicate, selected_ordinal=3, physical_page=43),
        )
    cluster = coalesce_gemini_json_service_activity_document_v1(
        page_records=records,
        compiled_specs=compiled,
    )
    assert cluster["owner_receipt"] is None or (
        "service_activity_document_declared_recovery_policy"
        not in cluster["owner_receipt"]
    )


@pytest.mark.parametrize(
    "failure_kind",
    [
        "NONADJACENT_OWNER",
        "DUPLICATE_OWNER",
        "RESET_AFTER_OWNER",
        "OWNER_SECTION_HAS_MONEY_TABLE",
        "DUPLICATE_RECEIVER",
    ],
)
def test_service_activity_owner_only_continuation_recovery_fails_closed(
    failure_kind: str,
) -> None:
    owner = _owner_only_page()
    receiver = _from_previous_service_page()
    receiver_physical_page = 43
    if failure_kind == "NONADJACENT_OWNER":
        receiver_physical_page = 44
    elif failure_kind == "DUPLICATE_OWNER":
        owner["sections"].append(copy.deepcopy(owner["sections"][0]))
    elif failure_kind == "RESET_AFTER_OWNER":
        owner["sections"].append(
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [],
                "title_exact": "27. Lãi thuần từ hoạt động kinh doanh ngoại hối",
            }
        )
    elif failure_kind == "OWNER_SECTION_HAS_MONEY_TABLE":
        owner["sections"][0]["tables"] = copy.deepcopy(
            receiver["sections"][0]["tables"]
        )
    elif failure_kind == "DUPLICATE_RECEIVER":
        receiver["sections"][0]["tables"].append(
            copy.deepcopy(receiver["sections"][0]["tables"][0])
        )
    cluster = coalesce_gemini_json_service_activity_document_v1(
        page_records=[
            _page_record(owner, selected_ordinal=1, physical_page=42),
            _page_record(
                receiver,
                selected_ordinal=2,
                physical_page=receiver_physical_page,
            ),
        ],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] != "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    assert cluster["component_regions"] == []


def _split_parent_table(parent: str) -> dict[str, Any]:
    columns = [
        {
            "header_path_exact": [
                "Năm tài chính kết thúc ngày",
                "31.12.2025",
                "Triệu đồng",
            ],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": [
                "Năm tài chính kết thúc ngày",
                "31.12.2024",
                "Triệu đồng",
            ],
            "value_kind": "MONEY",
        },
    ]
    if parent == "INCOME_PARENT":
        rows = [
            {
                "hierarchy_path_exact": ["Dịch vụ thanh toán"],
                "label_exact": "Dịch vụ thanh toán",
                "row_kind": "ITEM",
                "values_exact": ["60", "50"],
            },
            {
                "hierarchy_path_exact": ["Dịch vụ khác"],
                "label_exact": "Dịch vụ khác",
                "row_kind": "ITEM",
                "values_exact": ["40", "30"],
            },
            {
                "hierarchy_path_exact": [None],
                "label_exact": None,
                "row_kind": "TOTAL",
                "values_exact": ["100", "80"],
            },
        ]
    else:
        rows = [
            {
                "hierarchy_path_exact": ["Chi phí dịch vụ thanh toán"],
                "label_exact": "Chi phí dịch vụ thanh toán",
                "row_kind": "ITEM",
                "values_exact": ["(10)", "(5)"],
            },
            {
                "hierarchy_path_exact": ["Chi phí dịch vụ khác"],
                "label_exact": "Chi phí dịch vụ khác",
                "row_kind": "ITEM",
                "values_exact": ["(20)", "(15)"],
            },
            {
                "hierarchy_path_exact": [None],
                "label_exact": None,
                "row_kind": "TOTAL",
                "values_exact": ["(30)", "(20)"],
            },
        ]
    return {
        "columns": columns,
        "continuation": "NONE",
        "rows": rows,
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }


def _split_parent_section(parent: str) -> dict[str, Any]:
    title = (
        "21 THU NHẬP TỪ HOẠT ĐỘNG DỊCH VỤ"
        if parent == "INCOME_PARENT"
        else "22 CHI PHÍ TỪ HOẠT ĐỘNG DỊCH VỤ"
    )
    return {
        "content_kind": "FINANCIAL_NOTE",
        "narratives_exact": [],
        "statement_type": "NOT_APPLICABLE",
        "tables": [_split_parent_table(parent)],
        "title_exact": title,
    }


def _note_page(sections: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": sections,
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _reseal_test_cluster(cluster: dict[str, Any]) -> dict[str, Any]:
    material = {key: copy.deepcopy(value) for key, value in cluster.items() if key != "cluster_id"}
    return {
        **material,
        "cluster_id": "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material),
    }


def _split_parent_recovery_fixture(
    *, same_page: bool, candidate_physical_page: int = 52
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    compiled = _compiled()
    if same_page:
        page = _note_page(
            [_split_parent_section("INCOME_PARENT"), _split_parent_section("EXPENSE_PARENT")]
        )
        records = [_page_record(page, selected_ordinal=1, physical_page=51)]
        locators = [(records[0], 1, 1), (records[0], 2, 1)]
    else:
        income_page = _note_page([_split_parent_section("INCOME_PARENT")])
        expense_page = _note_page([_split_parent_section("EXPENSE_PARENT")])
        records = [
            _page_record(income_page, selected_ordinal=1, physical_page=51),
            _page_record(
                expense_page,
                selected_ordinal=2,
                physical_page=candidate_physical_page,
            ),
        ]
        locators = [(records[0], 1, 1), (records[1], 1, 1)]

    items = []
    for ordinal, (record, section_ordinal, table_ordinal) in enumerate(locators):
        page = record["page_json"]
        section = page["sections"][section_ordinal - 1]
        table = section["tables"][table_ordinal - 1]
        classification = classify_gemini_json_multitable_hierarchical_table_v1(
            page,
            section,
            table,
            compiled_specs=compiled,
        )
        items.append(
            {
                "classification": classification,
                "disposition": (
                    "SELECTED_FAMILY_COMPONENT"
                    if ordinal == 0
                    else "OUTSIDE_SELECTED_OWNER_FENCE"
                ),
                "page_json_version_id": record["page_json_version_id"],
                "physical_page": record["physical_page"],
                "position": [record["physical_page"], section_ordinal, table_ordinal],
                "section_id": f"s{section_ordinal}",
                "table_id": f"t{table_ordinal}",
            }
        )
    income_classification = items[0]["classification"]
    income_roles = sorted(
        {
            hit["role"] for hit in income_classification["role_hits"]
        }
        | set(income_classification["context_roles"])
    )
    income_record, income_section_ordinal, income_table_ordinal = locators[0]
    region = {
        "component_roles": income_roles,
        "document_id": income_record["document_id"],
        "document_ordinal": income_record["document_ordinal"],
        "fragment_ordinal": 1,
        "page_json_version_id": income_record["page_json_version_id"],
        "physical_page": income_record["physical_page"],
        "section_id": f"s{income_section_ordinal}",
        "selected_page_ordinal": income_record["selected_page_ordinal"],
        "source_logical_name": income_record["source_logical_name"],
        "source_sha256": income_record["source_sha256"],
        "table_id": f"t{income_table_ordinal}",
    }
    material = {
        "component_regions": [region],
        "declared_money_table_inventory": items,
        "document_id": income_record["document_id"],
        "document_ordinal": income_record["document_ordinal"],
        "owner_receipt": {
            "alias": "thu nhap tu hoat dong dich vu",
            "leading_component_positions": [],
            "leading_component_rule": (
                "CONTIGUOUS_SAME_PAGE_DECLARED_ROOT_COMPONENT_SUFFIX_BEFORE_OWNER"
            ),
            "outline_top_level_number": 21,
            "position": items[0]["position"],
            "source_exact": "21 THU NHẬP TỪ HOẠT ĐỘNG DỊCH VỤ",
        },
        "reasons": [],
        "source_logical_name": income_record["source_logical_name"],
        "source_sha256": income_record["source_sha256"],
        "status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
    }
    return records, {
        **material,
        "cluster_id": "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material),
    }


@pytest.mark.parametrize("same_page", [True, False])
def test_service_activity_adjacent_complementary_parent_recovers_exact_expense_table(
    same_page: bool,
) -> None:
    records, base = _split_parent_recovery_fixture(same_page=same_page)
    before = copy.deepcopy(records)
    compiled = _compiled()
    cluster = recover_gemini_json_service_activity_query_cluster_v1(
        page_records=records,
        base_cluster=base,
        compiled_specs=compiled,
    )
    assert records == before
    assert [region["fragment_ordinal"] for region in cluster["component_regions"]] == [1, 2]
    assert [
        (region["physical_page"], region["section_id"], region["table_id"])
        for region in cluster["component_regions"]
    ] == ([(51, "s1", "t1"), (51, "s2", "t1")] if same_page else [(51, "s1", "t1"), (52, "s1", "t1")])
    recovery = cluster["owner_receipt"][
        "service_activity_adjacent_complementary_parent_receipt"
    ]
    assert recovery["policy"] == ADJACENT_COMPLEMENTARY_PARENT_POLICY
    assert recovery["canonical_unit"] == "MILLION_VND"
    assert recovery["selected_income_parent"]["source_coefficients"] == [100, 80]
    assert recovery["candidate_expense_parent"]["source_coefficients"] == [-30, -20]

    regions = cluster["component_regions"]
    receipt = build_gemini_json_service_activity_region_query_receipt_v1(regions)
    candidate = evaluate_gemini_json_service_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version={
            record["page_json_version_id"]: record["page_json"] for record in records
        },
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    root = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [value["coefficient"] for value in root["values"]] == [70, 60]


@pytest.mark.parametrize(
    "failure_kind",
    [
        "NONADJACENT",
        "INTERVENING_MONEY_TABLE",
        "DUPLICATE_COMPLEMENT",
        "REVERSED_PERIOD_AXIS",
        "CONFLICTING_PERIOD_AXIS",
        "CONFLICTING_UNIT",
    ],
)
def test_service_activity_adjacent_complementary_parent_recovery_fails_closed(
    failure_kind: str,
) -> None:
    records, base = _split_parent_recovery_fixture(
        same_page=False,
        candidate_physical_page=53 if failure_kind == "NONADJACENT" else 52,
    )
    if failure_kind == "INTERVENING_MONEY_TABLE":
        intervening = copy.deepcopy(base["declared_money_table_inventory"][1])
        intervening["classification"]["context_roles"] = []
        intervening["classification"]["owner_visible"] = False
        intervening["classification"]["role_hits"] = []
        intervening["position"] = [51, 2, 1]
        intervening["section_id"] = "s2"
        intervening["page_json_version_id"] = records[0]["page_json_version_id"]
        intervening["physical_page"] = 51
        base["declared_money_table_inventory"].insert(1, intervening)
        base = _reseal_test_cluster(base)
    elif failure_kind == "DUPLICATE_COMPLEMENT":
        duplicate = copy.deepcopy(base["declared_money_table_inventory"][1])
        duplicate["position"] = [52, 2, 1]
        duplicate["section_id"] = "s2"
        base["declared_money_table_inventory"].append(duplicate)
        base = _reseal_test_cluster(base)
    else:
        table = records[1]["page_json"]["sections"][0]["tables"][0]
        if failure_kind == "REVERSED_PERIOD_AXIS":
            table["columns"].reverse()
        elif failure_kind == "CONFLICTING_PERIOD_AXIS":
            table["columns"][0]["header_path_exact"][1] = "31.12.2023"
        elif failure_kind == "CONFLICTING_UNIT":
            table["unit_exact"] = "VND"

    cluster = recover_gemini_json_service_activity_query_cluster_v1(
        page_records=records,
        base_cluster=base,
        compiled_specs=_compiled(),
    )
    assert cluster["component_regions"] == base["component_regions"]
    assert "service_activity_adjacent_complementary_parent_receipt" not in cluster[
        "owner_receipt"
    ]


def _split_parent_with_primary_control_fixture() -> tuple[
    list[dict[str, Any]], dict[str, Any]
]:
    records, base = _split_parent_recovery_fixture(same_page=True)
    old_version_id = records[0]["page_json_version_id"]
    note_version_id = "gfpstorev1:json:" + "2" * 64
    records[0]["selected_page_ordinal"] = 2
    records[0]["page_json_version_id"] = note_version_id
    for region in base["component_regions"]:
        if region["page_json_version_id"] == old_version_id:
            region["page_json_version_id"] = note_version_id
            region["selected_page_ordinal"] = 2
    for item in base["declared_money_table_inventory"]:
        if item["page_json_version_id"] == old_version_id:
            item["page_json_version_id"] = note_version_id

    primary = _unit_control_page(
        primary=True,
        unit_exact="Triệu đồng",
        income=["100", "80"],
        expense=["(30)", "(20)"],
        root=["70", "60"],
    )
    primary_table = primary["sections"][0]["tables"][0]
    primary_table["columns"] = copy.deepcopy(
        records[0]["page_json"]["sections"][0]["tables"][0]["columns"]
    )
    primary_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    primary_table["rows"][0]["row_kind"] = "ITEM"
    primary_table["rows"][1]["row_kind"] = "ITEM"
    primary_table["rows"][2]["row_kind"] = "SUBTOTAL"
    primary_record = _page_record(primary, selected_ordinal=1, physical_page=10)
    primary_classification = classify_gemini_json_multitable_hierarchical_table_v1(
        primary,
        primary["sections"][0],
        primary_table,
        compiled_specs=_compiled(),
    )
    base["declared_money_table_inventory"].insert(
        0,
        {
            "classification": primary_classification,
            "disposition": "EXCLUDED_TYPED_CONTROL",
            "page_json_version_id": primary_record["page_json_version_id"],
            "physical_page": primary_record["physical_page"],
            "position": [1, 1, 1],
            "section_id": "s1",
            "table_id": "t1",
        },
    )
    return [primary_record, *records], _reseal_test_cluster(base)


def test_service_activity_split_parent_cluster_adds_exact_primary_result_control() -> None:
    records, base = _split_parent_with_primary_control_fixture()
    before = copy.deepcopy(records)
    compiled = _compiled()
    cluster = recover_gemini_json_service_activity_query_cluster_v1(
        page_records=records,
        base_cluster=base,
        compiled_specs=compiled,
    )
    assert records == before
    assert [
        (region["physical_page"], region["section_id"], region["table_id"])
        for region in cluster["component_regions"]
    ] == [(10, "s1", "t1"), (51, "s1", "t1"), (51, "s2", "t1")]
    primary_receipt = cluster["owner_receipt"][
        "service_activity_primary_source_result_receipt"
    ]
    assert primary_receipt["policy"] == PRIMARY_SOURCE_RESULT_AUGMENTATION_POLICY
    assert primary_receipt["canonical_unit"] == "MILLION_VND"

    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_service_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version={
            record["page_json_version_id"]: record["page_json"] for record in records
        },
        compiled_specs=compiled,
        query_receipt=build_gemini_json_service_activity_region_query_receipt_v1(
            regions
        ),
    )
    assert candidate["status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    root = next(
        mapping
        for mapping in candidate["mappings"]
        if mapping["role"] == "FAMILY_ROOT_TOTAL"
    )
    assert [value["coefficient"] for value in root["values"]] == [70, 60]
    fallback = candidate["closure_receipt"]["service_activity_adapter_receipt"][
        "root_alternative_legacy_fallback_receipt"
    ]
    assert fallback["policy"] == (
        ROOT_ALTERNATIVE_PRIMARY_SOURCE_RESULT_FALLBACK_POLICY
    )


@pytest.mark.parametrize(
    "failure_kind", ["DUPLICATE_PRIMARY", "CONFLICTING_PERIOD_AXIS", "CONFLICTING_UNIT"]
)
def test_service_activity_primary_result_augmentation_fails_closed(
    failure_kind: str,
) -> None:
    records, base = _split_parent_with_primary_control_fixture()
    if failure_kind == "DUPLICATE_PRIMARY":
        duplicate = copy.deepcopy(base["declared_money_table_inventory"][0])
        duplicate["page_json_version_id"] = "gfpstorev1:json:" + "3" * 64
        duplicate["position"] = [3, 1, 1]
        base["declared_money_table_inventory"].append(duplicate)
        duplicate_record = copy.deepcopy(records[0])
        duplicate_record["page_json_version_id"] = duplicate["page_json_version_id"]
        duplicate_record["selected_page_ordinal"] = 3
        records.append(duplicate_record)
    elif failure_kind == "CONFLICTING_PERIOD_AXIS":
        records[0]["page_json"]["sections"][0]["tables"][0]["columns"][0][
            "header_path_exact"
        ][1] = "31.12.2023"
    else:
        records[0]["page_json"]["sections"][0]["tables"][0]["unit_exact"] = "VND"
    cluster = recover_gemini_json_service_activity_query_cluster_v1(
        page_records=records,
        base_cluster=_reseal_test_cluster(base),
        compiled_specs=_compiled(),
    )
    assert "service_activity_primary_source_result_receipt" not in cluster[
        "owner_receipt"
    ]


def _label_only_parent_with_primary_control_fixture(
    *, primary_parent_conflict: bool = False
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    income = "Thu nhập từ hoạt động dịch vụ"
    expense = "Chi phí hoạt động dịch vụ"
    note = _note_page(
        [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["Năm 2025", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Năm 2024", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [
                            {
                                "hierarchy_path_exact": [income],
                                "label_exact": income,
                                "row_kind": "GROUP",
                                "values_exact": [None, None],
                            },
                            {
                                "hierarchy_path_exact": [income, "Thu từ dịch vụ thanh toán"],
                                "label_exact": "Thu từ dịch vụ thanh toán",
                                "row_kind": "ITEM",
                                "values_exact": ["60", "50"],
                            },
                            {
                                "hierarchy_path_exact": [income, "Thu nhập khác"],
                                "label_exact": "Thu nhập khác",
                                "row_kind": "ITEM",
                                "values_exact": ["40", "30"],
                            },
                            {
                                "hierarchy_path_exact": [income, None],
                                "label_exact": None,
                                "row_kind": "SUBTOTAL",
                                "values_exact": ["100", "80"],
                            },
                            {
                                "hierarchy_path_exact": [expense],
                                "label_exact": expense,
                                "row_kind": "GROUP",
                                "values_exact": [None, None],
                            },
                            {
                                "hierarchy_path_exact": [expense, "Chi về dịch vụ thanh toán"],
                                "label_exact": "Chi về dịch vụ thanh toán",
                                "row_kind": "ITEM",
                                "values_exact": ["(30)", "(20)"],
                            },
                            {
                                "hierarchy_path_exact": [expense, "Chi phí khác"],
                                "label_exact": "Chi phí khác",
                                "row_kind": "ITEM",
                                "values_exact": ["-", None],
                            },
                            {
                                "hierarchy_path_exact": [expense, None],
                                "label_exact": None,
                                "row_kind": "SUBTOTAL",
                                "values_exact": ["(30)", "(20)"],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Lãi thuần từ hoạt động dịch vụ"
                                ],
                                "label_exact": "Lãi thuần từ hoạt động dịch vụ",
                                "row_kind": "TOTAL",
                                "values_exact": ["70", "60"],
                            },
                        ],
                        "title_exact": "Lãi thuần từ hoạt động dịch vụ",
                        "unit_exact": "Triệu đồng",
                    }
                ],
                "title_exact": "Lãi thuần từ hoạt động dịch vụ",
            }
        ]
    )
    primary = _unit_control_page(
        primary=True,
        unit_exact="Triệu đồng",
        income=["101", "80"] if primary_parent_conflict else ["100", "80"],
        expense=["(31)", "(20)"] if primary_parent_conflict else ["(30)", "(20)"],
        root=["70", "60"],
    )
    primary_table = primary["sections"][0]["tables"][0]
    primary_table["columns"] = copy.deepcopy(
        note["sections"][0]["tables"][0]["columns"]
    )
    primary_table["rows"][0]["row_kind"] = "ITEM"
    primary_table["rows"][1]["row_kind"] = "ITEM"
    primary_table["rows"][2]["row_kind"] = "SUBTOTAL"
    records = [
        _page_record(primary, selected_ordinal=1, physical_page=10),
        _page_record(note, selected_ordinal=2, physical_page=42),
    ]
    compiled = _compiled()
    inventory = []
    for record in records:
        page = record["page_json"]
        section = page["sections"][0]
        table = section["tables"][0]
        inventory.append(
            {
                "classification": (
                    classify_gemini_json_multitable_hierarchical_table_v1(
                        page,
                        section,
                        table,
                        compiled_specs=compiled,
                    )
                ),
                "disposition": (
                    "EXCLUDED_TYPED_CONTROL"
                    if page["status"] == "PRIMARY_FINANCIAL_STATEMENT"
                    else "SELECTED_FAMILY_COMPONENT"
                ),
                "page_json_version_id": record["page_json_version_id"],
                "physical_page": record["physical_page"],
                "position": [record["physical_page"], 1, 1],
                "section_id": "s1",
                "table_id": "t1",
            }
        )
    note_record = records[1]
    note_classification = inventory[1]["classification"]
    note_region = {
        "component_roles": sorted(
            {
                hit["role"] for hit in note_classification["role_hits"]
            }
            | set(note_classification["context_roles"])
        ),
        "document_id": note_record["document_id"],
        "document_ordinal": note_record["document_ordinal"],
        "fragment_ordinal": 1,
        "page_json_version_id": note_record["page_json_version_id"],
        "physical_page": note_record["physical_page"],
        "section_id": "s1",
        "selected_page_ordinal": note_record["selected_page_ordinal"],
        "source_logical_name": note_record["source_logical_name"],
        "source_sha256": note_record["source_sha256"],
        "table_id": "t1",
    }
    material = {
        "component_regions": [note_region],
        "declared_money_table_inventory": inventory,
        "document_id": note_record["document_id"],
        "document_ordinal": note_record["document_ordinal"],
        "owner_receipt": {
            "alias": "lai thuan tu hoat dong dich vu",
            "leading_component_positions": [],
            "leading_component_rule": (
                "CONTIGUOUS_SAME_PAGE_DECLARED_ROOT_COMPONENT_SUFFIX_BEFORE_OWNER"
            ),
            "outline_top_level_number": 2,
            "position": [42, 1, 1],
            "source_exact": "2. Lãi thuần từ hoạt động dịch vụ",
        },
        "reasons": [],
        "source_logical_name": note_record["source_logical_name"],
        "source_sha256": note_record["source_sha256"],
        "status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
    }
    return records, _reseal_test_cluster(material)


def test_service_activity_partial_label_only_parent_maps_exact_primary_source_row() -> None:
    records, base = _label_only_parent_with_primary_control_fixture()
    before = copy.deepcopy(records)
    compiled = _compiled()
    cluster = recover_gemini_json_service_activity_query_cluster_v1(
        page_records=records,
        base_cluster=base,
        compiled_specs=compiled,
    )
    assert records == before
    assert [region["physical_page"] for region in cluster["component_regions"]] == [
        10,
        42,
    ]
    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_service_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version={
            record["page_json_version_id"]: record["page_json"] for record in records
        },
        compiled_specs=compiled,
        query_receipt=build_gemini_json_service_activity_region_query_receipt_v1(
            regions
        ),
    )
    assert candidate["status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    expense = next(
        mapping
        for mapping in candidate["mappings"]
        if mapping["role"] == "EXPENSE_PARENT"
    )
    assert [cell["coefficient"] for cell in expense["values"]] == [-30, -20]
    assert expense["state"] == (
        "SOURCE_OBSERVED_PRIMARY_STATEMENT_ROOT_COMPONENT_CONTROL"
    )
    assert [source_ref["locator"]["physical_page"] for source_ref in expense["source_refs"]] == [
        10
    ]
    fallback = candidate["closure_receipt"]["service_activity_adapter_receipt"][
        "root_alternative_legacy_fallback_receipt"
    ]
    assert fallback["policy"] == (
        ROOT_ALTERNATIVE_PRIMARY_PARENT_CONTROL_FALLBACK_POLICY
    )
    assert validate_source_observation_mapping_contract_v1(candidate)["status"] == "PASS"


def test_service_activity_partial_parent_primary_observed_conflict_fails_closed() -> None:
    records, base = _label_only_parent_with_primary_control_fixture(
        primary_parent_conflict=True
    )
    cluster = recover_gemini_json_service_activity_query_cluster_v1(
        page_records=records,
        base_cluster=base,
        compiled_specs=_compiled(),
    )
    assert [region["physical_page"] for region in cluster["component_regions"]] == [42]
    regions = cluster["component_regions"]
    candidate = evaluate_gemini_json_service_activity_family_cluster_v1(
        regions=regions,
        page_json_by_version={
            record["page_json_version_id"]: record["page_json"] for record in records
        },
        compiled_specs=_compiled(),
        query_receipt=build_gemini_json_service_activity_region_query_receipt_v1(
            regions
        ),
    )
    assert candidate["status"] == "UNRESOLVED_GEMINI_JSON_FAMILY"
    assert candidate["mappings"] == []
    assert "service_activity_adapter_receipt" not in candidate["closure_receipt"]


def test_service_activity_vib_income_insurance_alias_maps_visible_source_row() -> None:
    page = _from_previous_service_page()
    section = page["sections"][0]
    table = section["tables"][0]
    section["title_exact"] = "Lãi thuần từ hoạt động dịch vụ"
    table["title_exact"] = "Lãi thuần từ hoạt động dịch vụ"
    table["continuation"] = "NONE"
    table["unit_exact"] = "Triệu đồng"
    table["rows"].insert(
        2,
        {
            "hierarchy_path_exact": [
                "Thu phí dịch vụ",
                "Thu phí đại lý bảo hiểm",
            ],
            "label_exact": "Thu phí đại lý bảo hiểm",
            "row_kind": "ITEM",
            "values_exact": ["5", "4"],
        },
    )
    table["rows"][0]["values_exact"] = ["105", "84"]
    table["rows"][-1]["values_exact"] = ["75", "64"]
    candidate = _evaluate_two_parent_service_page(page)
    assert candidate["status"] == "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
    insurance = next(
        mapping
        for mapping in candidate["mappings"]
        if mapping["role"] == "INCOME_INSURANCE"
    )
    assert [cell["coefficient"] for cell in insurance["values"]] == [5, 4]
