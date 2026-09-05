from __future__ import annotations

import argparse
import copy
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from scripts.experiments import (
    run_gemini_json_operating_expense_accounting_family_v1 as runner,
)


def test_real_sqlite_runner_normalizes_page_map_only_at_coverage_boundary(tmp_path):
    from test_build_f36_diagnostic_from_corpus_v1 import _run_real_sqlite_subprocess

    _run_real_sqlite_subprocess(tmp_path, check_runner=True)


def _sealed(material: dict, prefix: str) -> dict:
    return {**material, "receipt_id": prefix + canonical_json_sha256_v1(material)}


def _audit() -> dict:
    """Build a synthetic envelope fixture, not proof of actual PDF authentication."""

    source_sha = "2" * 64
    repair = {
        "repair_id": "gjoefav1:source-repair:" + "1" * 64,
        "source": {"source_sha256": source_sha},
    }
    adapter = {
        "all_blank_validation_role_omission_receipts": [],
        "continuation_projection_receipts": [],
        "nonexhaustive_parent_receipts": [],
        "root_closure_receipts": [],
        "source_repair_receipts": [{"repair": repair}],
        "unit_corroboration_receipts": [],
    }
    trials = [
        {
            "status": runner.generic.READY,
            "document_ordinal": 1,
            "source_logical_name": "bank/2025/synthetic.pdf",
            "source_sha256": source_sha,
            "mappings": [{"role": "ROOT", "values": ["1", "1"]}],
            "candidates": [{"closure_receipt": {"operating_expense_adapter_receipt": adapter}}],
        }
    ]
    application = runner._source_repair_application_receipt_v1(
        index={"documents": [{"source_sha256": source_sha}]},
        compiled_specs={
            "operating_expense_source_repairs": [repair],
            "operating_expense_source_repair_spec_sha256": "3" * 64,
        },
        trials=trials,
    )
    authentication = _sealed(
        {
            "applicable_repair_count": 1,
            "authenticated": True,
            "declared_repair_count": 1,
            "out_of_corpus_repair_axis": [],
            "out_of_corpus_repair_axis_sha256": canonical_json_sha256_v1([]),
            "out_of_corpus_repair_count": 0,
            "repair_axis": [repair],
            "repair_axis_sha256": canonical_json_sha256_v1([repair]),
            "repair_count": 1,
            "source_pdf_count": 1,
            "unverified_repair_count": 0,
        },
        "gjoerunv1:source-repair-auth:",
    )
    row = {
        "coverage": "MAPPED_EXACT_SOURCE_ROLE_ROW",
        "document_ordinal": 1,
        "label_exact": "Chi phí hoạt động",
        "page_json_version_id": "gfpstorev1:json:" + "4" * 64,
        "physical_page": 1,
        "role": "ROOT",
        "row_id": "row-1",
        "row_ordinal": 1,
        "section_id": "section-1",
        "source_logical_name": "bank/2025/synthetic.pdf",
        "source_sha256": source_sha,
        "table_id": "table-1",
        "values_exact": ["1", "1"],
    }
    coverage = _sealed(
        {
            "candidate_table_total_disposition_counts": {},
            "candidate_table_total_row_axis": [],
            "candidate_table_total_row_axis_sha256": canonical_json_sha256_v1([]),
            "family_id": runner.FAMILY_ID,
            "format_version": "OPERATING_EXPENSE_SOURCE_ROW_COVERAGE_V1",
            "raw_target_like_disposition_counts": {},
            "raw_target_like_row_axis": [],
            "raw_target_like_row_axis_sha256": canonical_json_sha256_v1([]),
            "source_row_axis": [row],
            "source_row_axis_sha256": canonical_json_sha256_v1([row]),
            "source_row_disposition_counts": {"MAPPED_EXACT_SOURCE_ROLE_ROW": 1},
            "violation_axis": [],
            "violation_count": 0,
        },
        "gjoefav1:source-row-coverage:",
    )
    pdf_visible = {
        "audit_id": "gjoefav1:pdf-visible:" + "5" * 64,
        "authenticated": True,
        "counts": {
            "authenticated_source_pdfs": 1,
            "manual_exception_category_pages": 1,
            "rendered_source_row_pages": 1,
            "source_rows_bound_to_renders": 1,
        },
        "coverage_receipt_id": coverage["receipt_id"],
        "manual_exception_category_review_axis_sha256": "6" * 64,
        "pdf_page_render_axis_sha256": "7" * 64,
        "source_pdf_authentication_axis_sha256": "8" * 64,
        "uncovered_source_row_count": 0,
    }
    return runner.build_operating_expense_experimental_audit_v1(
        sweep={"sweep_id": "synthetic-sweep"},
        output=Path("synthetic-sweep.json"),
        indexed={
            "candidate_dispositions": [{"cluster": {}}],
            "query_receipt": {"synthetic": True},
            "query_evidence_id": "synthetic-query",
        },
        trials=trials,
        historical_receipt={
            "corpus_relation": {"overlap_count": 0},
            "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
            "policy": runner.DISJOINT_EXPANSION,
        },
        observation_contract={"status": "PASS", "violation_count": 0},
        source_repair_application=application,
        source_repair_authentication=authentication,
        source_row_coverage=coverage,
        pdf_visible_source_row_audit=pdf_visible,
        pdf_residuals=[],
        selected_ids=[row["page_json_version_id"]],
        spec_refs={
            name: {"path": name + ".json", "sha256": "9" * 64, "size_bytes": 1}
            for name in (
                "evaluation",
                "pdf_residual_audit",
                "pdf_visible_source_row_audit",
                "schema_binding",
                "source_repair",
                "topology",
            )
        },
    )


def _reseal(audit: dict) -> None:
    material = {key: value for key, value in audit.items() if key != "audit_id"}
    audit["audit_id"] = "gjoefauditv1:audit:" + canonical_json_sha256_v1(material)


def test_runner_pins_shared_engine_and_runner() -> None:
    runner._assert_shared_pins_v1()


def test_runner_rejects_non_disjoint_policy_before_reading_inputs() -> None:
    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="requires DISJOINT_EXPANSION",
    ):
        runner.run(argparse.Namespace(historical_comparator_policy="STRICT_RELEASE"))


def test_current_corpus_gate_rejects_historical_document() -> None:
    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="outside the current reporting scope",
    ):
        runner._assert_current_corpus({"documents": [{"relative_path": "bank/2024/report.pdf"}]})


def test_source_repair_authentication_requires_real_pdf_root(tmp_path: Path) -> None:
    page_id = "gfpstorev1:json:" + "4" * 64
    repair = {
        "crop_evidence": {
            "bbox_pixels_xyxy": [0, 0, 1, 1],
            "pixel_height": 1,
            "pixel_width": 1,
            "rgb_sha256": "1" * 64,
        },
        "locator": {"physical_page": 1, "page_json_version_id": page_id},
        "render": {},
        "source": {
            "source_logical_name": "missing.pdf",
            "source_sha256": "2" * 64,
            "source_size_bytes": 1,
        },
    }
    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="source PDF path is unavailable",
    ):
        runner._authenticate_source_repairs_v1(
            compiled_specs={"operating_expense_source_repairs": [repair]},
            index={
                "documents": [
                    {
                        "relative_path": "missing.pdf",
                        "source_sha256": "2" * 64,
                        "source_size_bytes": 1,
                    }
                ]
            },
            selected_page_axis=[
                {
                    "page_json_version_id": page_id,
                    "source_sha256": "2" * 64,
                    "physical_page": 1,
                }
            ],
            source_pdf_root=tmp_path,
        )


def test_source_repair_application_is_exactly_once_and_corpus_scoped() -> None:
    repair = {
        "repair_id": "gjoefav1:source-repair:" + "1" * 64,
        "source": {"source_sha256": "2" * 64},
    }
    receipt = runner._source_repair_application_receipt_v1(
        index={"documents": [{"source_sha256": "2" * 64}]},
        compiled_specs={
            "operating_expense_source_repairs": [repair],
            "operating_expense_source_repair_spec_sha256": "3" * 64,
        },
        trials=[
            {
                "candidates": [
                    {
                        "closure_receipt": {
                            "operating_expense_adapter_receipt": {
                                "source_repair_receipts": [{"repair": repair}]
                            }
                        }
                    }
                ]
            }
        ],
    )
    assert receipt["violation_count"] == 0
    assert receipt["expected_repair_ids"] == receipt["applied_repair_ids"]

    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="application gate failed",
    ):
        runner._source_repair_application_receipt_v1(
            index={"documents": [{"source_sha256": "2" * 64}]},
            compiled_specs={
                "operating_expense_source_repairs": [repair],
                "operating_expense_source_repair_spec_sha256": "3" * 64,
            },
            trials=[],
        )


def test_audit_rejects_contract_violation_after_resealing() -> None:
    assert runner.validate_operating_expense_experimental_audit_v1(_audit())

    invented = copy.deepcopy(_audit())
    invented["source_observation_contract"]["violation_count"] = 1
    _reseal(invented)
    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="audit content is invalid",
    ):
        runner.validate_operating_expense_experimental_audit_v1(invented)

    missing_repair = copy.deepcopy(_audit())
    missing_repair["source_repair_application"]["violation_count"] = 1
    _reseal(missing_repair)
    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="audit content is invalid",
    ):
        runner.validate_operating_expense_experimental_audit_v1(missing_repair)


def test_audit_rejects_identity_tamper_with_valid_content() -> None:
    tampered = _audit()
    assert runner.validate_operating_expense_experimental_audit_v1(tampered)
    tampered["audit_id"] = "gjoefauditv1:audit:" + "0" * 64
    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="audit identity drifted",
    ):
        runner.validate_operating_expense_experimental_audit_v1(tampered)


@pytest.mark.parametrize("changed_field", ["sweep_id", "sweep_ref"])
def test_audit_rejects_sweep_reference_mismatch_after_resealing(
    changed_field: str,
) -> None:
    tampered = _audit()
    assert runner.validate_operating_expense_experimental_audit_v1(tampered)
    if changed_field == "sweep_id":
        tampered["sweep_id"] = "different-sweep"
    else:
        tampered["sweep_ref"]["sweep_id"] = "different-sweep"
    _reseal(tampered)
    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="audit content is invalid",
    ):
        runner.validate_operating_expense_experimental_audit_v1(tampered)


@pytest.mark.parametrize(
    ("field", "prefix", "error"),
    [
        (
            "source_repair_application",
            "gjoerunv1:source-repair-application:",
            "source-repair application identity drifted",
        ),
        (
            "source_repair_authentication_receipt",
            "gjoerunv1:source-repair-auth:",
            "source-repair authentication identity drifted",
        ),
        (
            "source_row_coverage_receipt",
            "gjoefav1:source-row-coverage:",
            "source-row coverage identity drifted",
        ),
    ],
)
def test_audit_rejects_nested_receipt_identity_tamper_after_resealing(
    field: str,
    prefix: str,
    error: str,
) -> None:
    tampered = _audit()
    assert runner.validate_operating_expense_experimental_audit_v1(tampered)
    tampered[field]["receipt_id"] = prefix + "0" * 64
    if field == "source_row_coverage_receipt":
        # Keep the outer binding coherent to reach the nested identity validator.
        tampered["pdf_visible_source_row_audit_receipt"]["coverage_receipt_id"] = tampered[field][
            "receipt_id"
        ]
    _reseal(tampered)
    with pytest.raises(runner.RunGeminiJsonOperatingExpenseV1Error, match=error):
        runner.validate_operating_expense_experimental_audit_v1(tampered)
