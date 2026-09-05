from __future__ import annotations

import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    compile_gemini_json_flat_family_specs_v1,
)
from bctc_ai.evaluation.historical_comparator_policy_v1 import (
    DISJOINT_EXPANSION,
    NOT_APPLICABLE_DISJOINT_CORPUS,
)
from scripts.experiments import (
    run_gemini_json_other_assets_accounting_family_v1 as runner,
)

ROOT = Path(__file__).resolve().parents[2]


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def test_runner_pins_shared_engine_and_f22_emits_no_f26_schema_ids() -> None:
    runner._assert_shared_implementation_pins_v1()
    compiled = compile_gemini_json_flat_family_specs_v1(
        _json("tm-other-assets-topology-v1.json"),
        _json("tm-other-assets-evaluation-v1.json"),
        _json("tm-other-assets-schema-binding-v1.json"),
    )

    assert compiled["validation_only_roles"] == ["INTEREST_FEE_RECEIVABLES"]
    assert not runner.F26_REPORT_NORM_IDS.intersection(compiled["bindings"].values())
    assert not {
        "CREDIT_INTEREST",
        "DEPOSIT_INTEREST",
        "DERIVATIVE_INTEREST",
        "OTHER_INTEREST",
    }.intersection(compiled["child_by_role"])


def test_pdf_residual_contract_accepts_an_empty_axis_before_current_census() -> None:
    checked = runner._validate_pdf_residual_spec_v1(
        {
            "corpus_manifest_index_id": "gjfccmiv1:index:" + "1" * 64,
            "family_id": runner.FAMILY_ID,
            "format_version": runner.PDF_RESIDUAL_FORMAT_VERSION,
            "residuals": [],
            "review_contract": {
                "alpha": False,
                "colorspace": "RGB",
                "format": "PNG",
                "matrix": [1, 1],
                "renderer": "PyMuPDF",
                "scope": (
                    "EVERY_PRIMARY_BALANCE_STATEMENT_PAGE_FOR_EVERY_NOT_OBSERVED_DOCUMENT"
                ),
                "visual_disposition_rule": (
                    "NO_PDF_VISIBLE_SCHEMA_MAPPABLE_FAMILY22_ROOT_OR_DETAIL_ROW"
                ),
            },
        }
    )
    assert checked["residuals"] == []


def _audit(*, report_norm_id: int) -> dict:
    mapping = {
        "item_mapping_id": "mapping",
        "report_norm_id": report_norm_id,
        "role": "RECEIVABLES",
        "values": [
            {"coefficient": 1, "source_text": "1", "state": "SOURCE_VISIBLE"},
            {"coefficient": 2, "source_text": "2", "state": "SOURCE_VISIBLE"},
        ],
    }
    candidate = {
        "candidate_id": "candidate",
        "closure_receipt": {"equations": []},
        "component_regions": [],
        "mappings": [mapping],
    }
    trial = {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": 1,
        "mappings": [mapping],
        "source_logical_name": "vietstock_bctc/ABC/2025/example.pdf",
        "source_sha256": "1" * 64,
        "status": runner.READY,
    }
    return runner.build_experimental_audit_v1(
        sweep={
            "metrics": {
                "document_count": 1,
                "mapping_count": 1,
                "not_observed_count": 0,
                "ready_count": 1,
                "unresolved_count": 0,
            },
            "sweep_id": "sweep",
            "trials": [trial],
        },
        sweep_output=Path("sweep.json"),
        indexed_query_evidence={"query_receipt": {}},
        historical_receipt={
            "comparison_axis": [],
            "corpus_relation": {"overlap_count": 0},
            "disposition": NOT_APPLICABLE_DISJOINT_CORPUS,
            "policy": DISJOINT_EXPANSION,
        },
        observation_contract={"status": "PASS", "violation_count": 0},
        pdf_residuals=[],
        source_role_coverage_contract={
            "row_axis": [],
            "row_axis_sha256": runner.canonical_json_sha256_v1([]),
            "status": "PASS",
            "violation_count": 0,
        },
        spec_refs={},
    )


def test_audit_accepts_disjoint_current_mapping_and_rejects_f26_ids() -> None:
    assert runner.validate_experimental_audit_content_v1(
        _audit(report_norm_id=967)
    )["axis_counts"]["mappings"] == 1
    with pytest.raises(
        runner.RunGeminiJsonOtherAssetsAccountingFamilyV1Error,
        match="semantic gate",
    ):
        runner.validate_experimental_audit_content_v1(_audit(report_norm_id=982))


def _source_role_coverage_fixture(
    *, source_text: str | None, row_kind: str, mapped: bool
) -> tuple[dict, list[dict], dict[int, dict[str, dict]]]:
    page_id = "gfpstorev1:json:" + "3" * 64
    locator = {
        "page_json_version_id": page_id,
        "physical_page": 7,
        "section_id": "s1",
        "selected_page_ordinal": 7,
        "table_id": "t1",
    }
    region = {
        **locator,
        "component_roles": ["OTHER_ASSET_BRANCH"],
        "document_id": "gfpstorev1:document:" + "4" * 64,
        "document_ordinal": 1,
        "fragment_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": "5" * 64,
    }
    inventory = {
        "classification": {
            "money_column_ordinals": [1],
            "role_hits": [
                {
                    "role": "OTHER_ASSET_BRANCH",
                    "row_kind": row_kind,
                    "row_ordinal": 1,
                    "source_order": 1,
                }
            ],
        },
        "disposition": "SELECTED_FAMILY_COMPONENT",
        "page_json_version_id": page_id,
        "physical_page": 7,
        "position": [7, 1, 1],
        "section_id": "s1",
        "table_id": "t1",
    }
    cluster = {
        "component_regions": [region],
        "declared_money_table_inventory": [inventory],
        "document_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": "5" * 64,
    }
    source_ref = {
        "hierarchy_path_exact": ["Tài sản Có khác"],
        "label_exact": "Tài sản Có khác",
        "locator": locator,
        "money_column_ordinals": [1],
        "row_id": "r1",
        "row_ordinal": 1,
    }
    mappings = (
        [
            {
                "report_norm_id": 987,
                "role": "OTHER_ASSET_BRANCH",
                "source_refs": [source_ref],
            }
        ]
        if mapped
        else []
    )
    trial = {
        "candidates": [
            {
                "closure_receipt": {
                    "equations": [],
                    "table_receipts": [],
                    "validation_only_roles": [],
                },
                "component_regions": [region],
                "mappings": mappings,
            }
        ],
        "document_ordinal": 1,
        "status": runner.READY,
    }
    pages = {
        1: {
            page_id: {
                "sections": [
                    {
                        "tables": [
                            {
                                "columns": [
                                    {
                                        "header_path_exact": ["Kỳ này"],
                                        "value_kind": "MONEY",
                                    }
                                ],
                                "rows": [
                                    {
                                        "hierarchy_path_exact": [
                                            "Tài sản Có khác"
                                        ],
                                        "label_exact": "Tài sản Có khác",
                                        "row_kind": row_kind,
                                        "values_exact": [source_text],
                                    }
                                ],
                            }
                        ]
                    }
                ]
            }
        }
    }
    return {"accepted_clusters": [cluster]}, [trial], pages


def test_source_role_coverage_maps_visible_rows_and_types_blank_groups() -> None:
    indexed, trials, pages = _source_role_coverage_fixture(
        source_text="100", row_kind="SUBTOTAL", mapped=True
    )
    mapped = runner.build_source_role_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
    )
    assert mapped["row_axis"][0]["coverage_disposition"] == (
        "DIRECT_SCHEMA_MAPPING_SOURCE"
    )

    indexed, trials, pages = _source_role_coverage_fixture(
        source_text=None, row_kind="GROUP", mapped=False
    )
    blank = runner.build_source_role_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
    )
    assert blank["row_axis"][0]["coverage_disposition"] == (
        "ALL_BLANK_STRUCTURAL_GROUP_NON_OBSERVATION"
    )
    assert blank["row_axis"][0]["source_cells"] == [
        {
            "column_ordinal": 1,
            "observation_state": "BLANK_SOURCE_CELL",
            "source_text": None,
        }
    ]


def test_source_role_coverage_rejects_visible_unconsumed_subtotal() -> None:
    indexed, trials, pages = _source_role_coverage_fixture(
        source_text="100", row_kind="SUBTOTAL", mapped=False
    )
    with pytest.raises(
        runner.RunGeminiJsonOtherAssetsAccountingFamilyV1Error,
        match=r"source-role coverage has 1 violation\(s\)",
    ):
        runner.build_source_role_coverage_receipt_v1(
            indexed_query_evidence=indexed,
            trials=trials,
            page_json_by_document=pages,
        )
