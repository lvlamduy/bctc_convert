from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from scripts.experiments import run_gemini_json_fx_gold_activity_accounting_family_v1 as runner

ROOT = Path(__file__).resolve().parents[2]
VERSION_ID = "gfpstorev1:json:" + "a" * 64


def _compiled() -> dict:
    return runner.compile_gemini_json_fx_gold_activity_family_specs_v1(
        json.loads(runner.TOPOLOGY_SPEC_PATH.read_bytes()),
        json.loads(runner.EVALUATION_SPEC_PATH.read_bytes()),
        json.loads(runner.SCHEMA_BINDING_SPEC_PATH.read_bytes()),
        json.loads(runner.SOURCE_REPAIR_PATH.read_bytes()),
    )


def _nested_receipt(*, format_version: str, axis_name: str, axis: list[dict], prefix: str) -> dict:
    material = {
        "claim_boundary": "fixture",
        "disposition_counts": {},
        "format_version": format_version,
        "indexed_query_evidence_id": "query",
        axis_name: axis,
        f"{axis_name}_sha256": canonical_json_sha256_v1(axis),
        "trial_axis_sha256": "1" * 64,
        "violation_count": 0,
        "violations": [],
    }
    return {**material, "receipt_id": prefix + canonical_json_sha256_v1(material)}


def _audit() -> dict:
    source_authentication_axis = [{"repair_id": "repair"}]
    source_coverage = _nested_receipt(
        format_version=runner.SOURCE_ROW_COVERAGE_FORMAT_VERSION,
        axis_name="row_axis",
        axis=[],
        prefix="f31srcrowv1:receipt:",
    )
    primary = _nested_receipt(
        format_version=runner.PRIMARY_PRESENTATION_FORMAT_VERSION,
        axis_name="presentation_axis",
        axis=[],
        prefix="f31prpav1:receipt:",
    )
    material = {
        "axis_counts": {"trials": 1},
        "axis_sha256": {"trials": "2" * 64},
        "family_id": runner.FAMILY_ID,
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": {
            "corpus_relation": {"overlap_count": 0},
            "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
            "policy": runner.DISJOINT_EXPANSION,
        },
        "indexed_query_receipt": {},
        "primary_root_presentation_receipt": primary,
        "source_authentication_axis": source_authentication_axis,
        "source_authentication_axis_sha256": canonical_json_sha256_v1(source_authentication_axis),
        "source_authentication_count": 1,
        "source_observation_contract": {"violation_count": 0},
        "source_row_coverage_receipt": source_coverage,
        "spec_refs": {},
        "sweep_id": "sweep",
        "sweep_output": "/dev/shm/family31.json",
    }
    return {
        **material,
        "audit_id": "gjfgaauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def _reseal(audit: dict) -> None:
    material = {key: value for key, value in audit.items() if key != "audit_id"}
    audit["audit_id"] = "gjfgaauditv1:audit:" + canonical_json_sha256_v1(material)


def _page(*, root_label: str = "Lãi thuần từ hoạt động kinh doanh ngoại hối") -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": "INCOME_STATEMENT",
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
                                "hierarchy_path_exact": [root_label],
                                "label_exact": root_label,
                                "row_kind": "TOTAL",
                                "values_exact": ["70", "60"],
                            },
                            {
                                "hierarchy_path_exact": [None],
                                "label_exact": None,
                                "row_kind": "TOTAL",
                                "values_exact": ["7", "6"],
                            },
                        ],
                        "title_exact": root_label,
                        "unit_exact": "Triệu đồng",
                    }
                ],
                "title_exact": root_label,
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }


def _coverage_fixture() -> tuple[dict, list[dict], dict[int, dict[str, dict]]]:
    locator = {
        "page_json_version_id": VERSION_ID,
        "section_id": "s1",
        "table_id": "t1",
    }
    inventory = {
        "classification": {
            "family_root_row_ordinals": [1],
            "money_column_ordinals": [1, 2],
            "role_hits": [],
            "typed_control_disposition": None,
            "unbound_money_row_ordinals": [2],
        },
        "disposition": "SELECTED_FAMILY_COMPONENT",
        **locator,
        "physical_page": 1,
    }
    region = {**locator, "physical_page": 1}
    mapping = {
        "role": "FAMILY_ROOT_TOTAL",
        "source_refs": [
            {
                "locator": locator,
                "row_ordinal": 1,
            }
        ],
    }
    closure = {
        "proof": {
            "before_locator": locator,
            "before_row_ordinal": 2,
        },
        "validation_only_roles": [],
    }
    candidate = {
        "closure_receipt": closure,
        "component_regions": [region],
        "mappings": [mapping],
    }
    indexed = {
        "accepted_clusters": [
            {
                "declared_money_table_inventory": [inventory],
                "document_ordinal": 1,
            }
        ],
        "query_evidence_id": "query",
    }
    trials = [
        {
            "candidate_count": 1,
            "candidates": [candidate],
            "document_ordinal": 1,
            "mappings": [mapping],
            "source_logical_name": "fixture.pdf",
            "source_sha256": "b" * 64,
        }
    ]
    return indexed, trials, {1: {VERSION_ID: _page()}}


def test_runner_pins_shared_engine_and_runner() -> None:
    runner._assert_shared_pins_v1()


def test_runner_rejects_non_disjoint_policy_before_reading_inputs() -> None:
    with pytest.raises(
        runner.RunGeminiJsonFxGoldActivityV1Error,
        match="requires DISJOINT_EXPANSION",
    ):
        runner.run(argparse.Namespace(historical_comparator_policy="STRICT_RELEASE"))


def test_current_corpus_and_pdf_root_fail_closed(tmp_path: Path) -> None:
    runner._assert_current_corpus(
        {"documents": [{"relative_path": "vietstock_bctc/BANK/2025/report.pdf"}]}
    )
    with pytest.raises(
        runner.RunGeminiJsonFxGoldActivityV1Error,
        match="outside the current reporting scope",
    ):
        runner._assert_current_corpus(
            {"documents": [{"relative_path": "vietstock_bctc/BANK/2024/report.pdf"}]}
        )
    with pytest.raises(
        runner.RunGeminiJsonFxGoldActivityV1Error,
        match="source-PDF root is unavailable",
    ):
        runner._authenticate_source_repair_images_v1(
            repairs=[], source_pdf_root=tmp_path / "missing"
        )


def test_audit_rejects_nested_violation_and_identity_tamper() -> None:
    assert runner.validate_fx_gold_activity_experimental_audit_v1(_audit())

    invented = copy.deepcopy(_audit())
    receipt = invented["source_row_coverage_receipt"]
    receipt["violation_count"] = 1
    material = {key: value for key, value in receipt.items() if key != "receipt_id"}
    receipt["receipt_id"] = "f31srcrowv1:receipt:" + canonical_json_sha256_v1(material)
    _reseal(invented)
    with pytest.raises(
        runner.RunGeminiJsonFxGoldActivityV1Error,
        match="audit content is invalid",
    ):
        runner.validate_fx_gold_activity_experimental_audit_v1(invented)

    tampered = _audit()
    tampered["sweep_id"] = "tampered"
    with pytest.raises(
        runner.RunGeminiJsonFxGoldActivityV1Error,
        match="audit identity drifted",
    ):
        runner.validate_fx_gold_activity_experimental_audit_v1(tampered)


def test_source_row_coverage_binds_projection_before_locator() -> None:
    indexed, trials, pages = _coverage_fixture()
    receipt = runner._source_row_coverage_receipt_v1(
        indexed=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=_compiled(),
    )
    assert receipt["violation_count"] == 0
    assert receipt["disposition_counts"] == {
        "DIRECT_MAPPING_SOURCE": 1,
        "SELECTED_EXACT_PROOF_SOURCE": 1,
    }

    del trials[0]["candidates"][0]["closure_receipt"]["proof"]
    drifted = runner._source_row_coverage_receipt_v1(
        indexed=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=_compiled(),
    )
    assert drifted["violation_count"] == 1


def test_primary_root_presentation_is_source_bound() -> None:
    indexed, trials, pages = _coverage_fixture()
    inventory = indexed["accepted_clusters"][0]["declared_money_table_inventory"][0]
    inventory["classification"]["typed_control_disposition"] = "PRIMARY_FINANCIAL_STATEMENT_SUMMARY"
    trials[0]["mappings"][0].update(
        {
            "state": "SOURCE_VISIBLE_PRIMARY_STATEMENT_EXACT_RESULT",
            "unit": "MILLION_VND",
            "values": [
                {"coefficient": 70, "source_text": "70", "state": "RAW_SIGNED_INTEGER"},
                {"coefficient": 60, "source_text": "60", "state": "RAW_SIGNED_INTEGER"},
            ],
        }
    )
    receipt = runner._primary_root_presentation_receipt_v1(
        indexed=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=_compiled(),
    )
    assert receipt["violation_count"] == 0
    assert receipt["disposition_counts"] == {"EXACT_SAME_UNIT_AND_VECTOR": 1}

    pages[1][VERSION_ID] = _page(root_label="Unrelated result")
    drifted = runner._primary_root_presentation_receipt_v1(
        indexed=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=_compiled(),
    )
    assert drifted["violation_count"] == 1


def test_exact_million_scale_relation_is_typed_and_directional() -> None:
    assert runner._exact_million_scale_relation(
        source_vector=[70_000_000, 60_000_000],
        source_unit="VND",
        mapped_vector=[70, 60],
        mapped_unit="MILLION_VND",
    )
    assert not runner._exact_million_scale_relation(
        source_vector=[70_000_001, 60_000_000],
        source_unit="VND",
        mapped_vector=[70, 60],
        mapped_unit="MILLION_VND",
    )
    assert runner._within_explicit_million_display_interval(
        source_vector=[4_045_013_419, -1_467_310_194],
        source_unit="VND",
        mapped_vector=[4_045, -1_467],
        mapped_unit="MILLION_VND",
    )
    assert not runner._within_explicit_million_display_interval(
        source_vector=[4_045_500_000],
        source_unit="VND",
        mapped_vector=[4_045],
        mapped_unit="MILLION_VND",
    )


def test_implementation_receipt_is_unique_and_family_local() -> None:
    refs = runner._implementation_refs()
    paths = [ref["path"] for ref in refs]
    assert refs[0]["path"] == (
        "scripts/experiments/run_gemini_json_fx_gold_activity_accounting_family_v1.py"
    )
    assert len(paths) == len(set(paths))
    assert set(paths) >= {
        "data/registered/gemini_json_fx_gold_activity_source_repairs_v1.json",
        "src/bctc_ai/evaluation/gemini_json_fx_gold_activity_family_v1.py",
        "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
    }
