from __future__ import annotations

import argparse
import copy
import importlib.util
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    ROOT
    / "scripts/experiments/"
    "run_gemini_json_loan_interest_accrual_classification_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location("run_family26_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _audit() -> dict:
    material = {
        "axis_counts": {"mappings": 0, "residuals": 0, "trials": 0},
        "axis_sha256": {},
        "cross_family_disjointness_receipt": {"overlap_count": 0},
        "family_id": runner.FAMILY_ID,
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_comparator_receipt": {
            "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
            "policy": runner.DISJOINT_EXPANSION,
        },
        "indexed_query_receipt": {},
        "pdf_residuals": [],
        "pdf_visible_source_row_audit_receipt": {
            "authenticated": True,
            "coverage_receipt_id": "coverage",
            "uncovered_source_row_count": 0,
        },
        "source_observation_contract": {"violation_count": 0},
        "source_row_coverage_receipt": {
            "receipt_id": "coverage",
            "violation_count": 0,
        },
        "spec_refs": {},
        "sweep_id": "sweep",
        "sweep_output": "/tmp/family26.json",
    }
    return {
        **material,
        "audit_id": "glicafauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def _reseal(audit: dict) -> None:
    material = {key: item for key, item in audit.items() if key != "audit_id"}
    audit["audit_id"] = "glicafauditv1:audit:" + canonical_json_sha256_v1(material)


def test_runner_rejects_strict_policy_before_reading_inputs() -> None:
    with pytest.raises(
        runner.RunGeminiJsonLoanInterestAccrualClassificationV1Error,
        match="requires DISJOINT_EXPANSION",
    ):
        runner.run(argparse.Namespace(historical_comparator_policy="STRICT_RELEASE"))


def test_current_corpus_gate_rejects_historical_document() -> None:
    with pytest.raises(
        runner.RunGeminiJsonLoanInterestAccrualClassificationV1Error,
        match="pre-2025",
    ):
        runner._assert_current_corpus(
            {"documents": [{"relative_path": "bank/2024/report.pdf"}]}
        )


def test_shared_implementation_pin_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "_sha256", lambda _: "0" * 64)

    with pytest.raises(
        runner.RunGeminiJsonLoanInterestAccrualClassificationV1Error,
        match="implementation pin drifted",
    ):
        runner._assert_shared_implementation_pins_v1()


def test_audit_rejects_cross_family_overlap_and_source_invention() -> None:
    assert runner.validate_experimental_audit_content_v1(_audit())

    overlap = copy.deepcopy(_audit())
    overlap["cross_family_disjointness_receipt"]["overlap_count"] = 1
    _reseal(overlap)
    with pytest.raises(
        runner.RunGeminiJsonLoanInterestAccrualClassificationV1Error,
        match="audit content is invalid",
    ):
        runner.validate_experimental_audit_content_v1(overlap)

    invented = copy.deepcopy(_audit())
    invented["source_observation_contract"]["violation_count"] = 1
    _reseal(invented)
    with pytest.raises(
        runner.RunGeminiJsonLoanInterestAccrualClassificationV1Error,
        match="audit content is invalid",
    ):
        runner.validate_experimental_audit_content_v1(invented)

    uncovered = copy.deepcopy(_audit())
    uncovered["source_row_coverage_receipt"]["violation_count"] = 1
    _reseal(uncovered)
    with pytest.raises(
        runner.RunGeminiJsonLoanInterestAccrualClassificationV1Error,
        match="audit content is invalid",
    ):
        runner.validate_experimental_audit_content_v1(uncovered)

    pdf_uncovered = copy.deepcopy(_audit())
    pdf_uncovered["pdf_visible_source_row_audit_receipt"][
        "uncovered_source_row_count"
    ] = 1
    _reseal(pdf_uncovered)
    with pytest.raises(
        runner.RunGeminiJsonLoanInterestAccrualClassificationV1Error,
        match="audit content is invalid",
    ):
        runner.validate_experimental_audit_content_v1(pdf_uncovered)


def test_pdf_residual_identity_tampering_fails_closed() -> None:
    material = {
        "disposition": "TRUE_NOT_OBSERVED_NO_PDF_VISIBLE_SCHEMA_MAPPABLE_FAMILY26_ROW",
        "document_ordinal": 1,
        "pdf_page_axis": [
            {
                "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
                "pdf_page_render_sha256": "2" * 64,
                "physical_page": 1,
            }
        ],
        "source_logical_name": "bank/2025/report.pdf",
        "source_sha256": "3" * 64,
        "source_size_bytes": 1,
        "trial_status": runner.NOT_OBSERVED,
    }
    residual = {
        **material,
        "residual_audit_id": (
            "glicafv1:residual:" + canonical_json_sha256_v1(material)
        ),
    }
    spec = {
        "corpus_manifest_index_id": "gjfccmiv1:index:" + "4" * 64,
        "family_id": runner.FAMILY_ID,
        "format_version": runner.PDF_RESIDUAL_FORMAT_VERSION,
        "residuals": [residual],
        "review_contract": {
            "render_contract": {
                "alpha": False,
                "colorspace": "RGB",
                "format": "PNG",
                "matrix": [1, 1],
                "renderer": "PyMuPDF",
            },
            "scope": (
                "EVERY_PDF_PAGE_FOR_EVERY_NOT_OBSERVED_OR_UNRESOLVED_DOCUMENT"
            ),
            "visual_disposition_rule": (
                "NO_PDF_VISIBLE_SCHEMA_MAPPABLE_FAMILY26_ROW_OR_EXPLICIT_SOURCE_AMBIGUITY"
            ),
        },
    }
    assert runner._validate_pdf_residual_spec_v1(spec)

    spec["residuals"][0]["pdf_page_axis"][0]["physical_page"] = 2
    with pytest.raises(
        runner.RunGeminiJsonLoanInterestAccrualClassificationV1Error,
        match="identity drifted",
    ):
        runner._validate_pdf_residual_spec_v1(spec)


def test_pdf_visible_axis_covers_classified_and_raw_only_rows_exactly() -> None:
    classified = {
        "coverage": "MAPPED_EXACT_SOURCE_ROW",
        "document_ordinal": 1,
        "hierarchy_path_exact": ["Các khoản lãi, phí phải thu"],
        "label_exact": "Các khoản lãi, phí phải thu",
        "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
        "physical_page": 1,
        "report_norm_id": 982,
        "role": "INTEREST_FEE_RECEIVABLES",
        "row_id": "r1",
        "row_ordinal": 1,
        "section_id": "s1",
        "source_logical_name": "bank/2025/report.pdf",
        "source_sha256": "2" * 64,
        "table_id": "t1",
        "values_exact": ["1", "2"],
    }
    raw_duplicate = copy.deepcopy(classified)
    raw_duplicate["coverage"] = "ACCOUNTED_CLASSIFIED_SOURCE_ROW"
    raw_duplicate.pop("report_norm_id")
    raw_duplicate.pop("role")
    raw_only = copy.deepcopy(raw_duplicate)
    raw_only.update(
        {
            "coverage": "ALLOWED_GENERAL_RECEIVABLES_SUPPORT_PROGRAM",
            "label_exact": (
                "Phải thu liên quan đến các chương trình hỗ trợ lãi suất"
            ),
            "row_id": "r2",
            "row_ordinal": 2,
        }
    )
    candidate_total = copy.deepcopy(raw_duplicate)
    candidate_total.update(
        {
            "coverage": "OUTSIDE_FAMILY26_FOLLOWING_OTHER_NOTE_TOTAL",
            "label_exact": "Cộng",
            "row_id": "r3",
            "row_ordinal": 3,
        }
    )
    coverage = {
        "candidate_table_total_row_axis": [candidate_total],
        "raw_target_like_row_axis": [raw_duplicate, raw_only],
        "source_row_axis": [classified],
        "violation_count": 0,
    }

    rows = runner._expected_pdf_visible_audit_rows_v1(coverage)

    assert len(rows) == 3
    assert {row["axis_kind"] for row in rows} == {
        "CANDIDATE_TABLE_TOTAL_DISPOSITION",
        "CLASSIFIED_SOURCE_ROW",
        "RAW_TARGET_LIKE_SOURCE_ROW",
    }
    assert {row["row_ordinal"] for row in rows} == {1, 2, 3}
