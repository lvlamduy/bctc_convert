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
    "run_gemini_json_credit_risk_provision_expense_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location("run_family37_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _audit() -> dict:
    material = {
        "axis_counts": {"mappings": 0, "residuals": 0, "trials": 0},
        "axis_sha256": {},
        "family_id": runner.FAMILY_ID,
        "family_ownership_receipt": {
            "disposition": runner.FAMILY_OWNERSHIP_DISPOSITION,
            "shared_file_mutation_count": 0,
        },
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
        "source_repair_authentication_receipt": {
            "authenticated": True,
            "unverified_repair_count": 0,
        },
        "source_row_coverage_receipt": {
            "receipt_id": "coverage",
            "violation_count": 0,
        },
        "spec_refs": {},
        "sweep_id": "sweep",
        "sweep_output": "/tmp/family37.json",
    }
    return {
        **material,
        "audit_id": "gjcrpefauditv1:audit:"
        + canonical_json_sha256_v1(material),
    }


def _reseal(audit: dict) -> None:
    material = {key: item for key, item in audit.items() if key != "audit_id"}
    audit["audit_id"] = (
        "gjcrpefauditv1:audit:" + canonical_json_sha256_v1(material)
    )


def test_runner_rejects_strict_policy_before_reading_inputs() -> None:
    with pytest.raises(
        runner.RunGeminiJsonCreditRiskProvisionExpenseV1Error,
        match="requires DISJOINT_EXPANSION",
    ):
        runner.run(argparse.Namespace(historical_comparator_policy="STRICT_RELEASE"))


def test_current_corpus_gate_rejects_historical_document() -> None:
    with pytest.raises(
        runner.RunGeminiJsonCreditRiskProvisionExpenseV1Error,
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
        runner.RunGeminiJsonCreditRiskProvisionExpenseV1Error,
        match="implementation pin drifted",
    ):
        runner._assert_shared_implementation_pins_v1()


def test_audit_requires_coverage_observation_repair_and_ownership_gates() -> None:
    assert runner.validate_experimental_audit_content_v1(_audit())
    mutations = (
        ("source_observation_contract", "violation_count", 1),
        ("source_row_coverage_receipt", "violation_count", 1),
        (
            "source_repair_authentication_receipt",
            "unverified_repair_count",
            1,
        ),
        ("family_ownership_receipt", "shared_file_mutation_count", 1),
    )
    for container, field, value in mutations:
        drifted = copy.deepcopy(_audit())
        drifted[container][field] = value
        _reseal(drifted)
        with pytest.raises(
            runner.RunGeminiJsonCreditRiskProvisionExpenseV1Error,
            match="audit content is invalid",
        ):
            runner.validate_experimental_audit_content_v1(drifted)


def test_pdf_visible_axis_adds_unclassified_movement_row_once() -> None:
    def row(row_ordinal: int, coverage: str) -> dict:
        return {
            "coverage": coverage,
            "document_ordinal": 1,
            "hierarchy_path_exact": ["Dự phòng cho vay khách hàng"],
            "label_exact": "Trích lập dự phòng trong kỳ",
            "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
            "physical_page": 3,
            "report_norm_id": 1224,
            "role": "CUSTOMER_GENERAL",
            "row_id": f"r{row_ordinal}",
            "row_ordinal": row_ordinal,
            "section_id": "s1",
            "source_logical_name": "bank/2025/report.pdf",
            "source_sha256": "2" * 64,
            "table_id": "t1",
            "values_exact": ["1", "2"],
        }

    movement = row(2, "MAPPED_FROM_EXACT_SOURCE_OBSERVATION")
    duplicate_lane = copy.deepcopy(movement)
    duplicate_lane["role"] = "CUSTOMER_SPECIFIC"
    coverage = {
        "candidate_table_total_row_axis": [],
        "movement_cell_axis": [movement, duplicate_lane],
        "raw_target_like_row_axis": [],
        "source_row_axis": [row(1, "MAPPED_EXACT_SOURCE_ROLE_ROW")],
        "violation_count": 0,
    }
    expected = runner._expected_pdf_visible_audit_rows_v1(coverage)
    assert len(expected) == 2
    assert {item["axis_kind"] for item in expected} == {
        "CLASSIFIED_SOURCE_ROW",
        "CUSTOMER_MOVEMENT_SOURCE_ROW",
    }


def test_manual_pdf_review_requires_every_exact_category_on_its_bound_page() -> None:
    expected_rows = [
        {"axis_kind": "CLASSIFIED_SOURCE_ROW", "coverage": "MAPPED"},
        {"axis_kind": "RAW_TARGET_LIKE_SOURCE_ROW", "coverage": "SOURCE_ONLY"},
    ]
    pages = {}
    manual = []
    for physical_page, row in enumerate(expected_rows, start=1):
        page = {
            "document_ordinal": 1,
            "page_json_version_id": "gfpstorev1:json:" + str(physical_page) * 64,
            "physical_page": physical_page,
            "render_sha256": str(physical_page + 2) * 64,
            "source_logical_name": "bank/2025/report.pdf",
            "source_row_axis": [row],
            "source_sha256": "a" * 64,
        }
        pages[(page["source_sha256"], physical_page)] = page
        manual.append(
            {
                "document_ordinal": 1,
                "evidence": "Visually authenticated category sample.",
                "page_json_version_id": page["page_json_version_id"],
                "physical_page": physical_page,
                "render_sha256": page["render_sha256"],
                "review_kind": f"{row['axis_kind']}__{row['coverage']}",
                "source_logical_name": page["source_logical_name"],
                "source_sha256": page["source_sha256"],
            }
        )
    runner._validate_manual_pdf_review_category_frontier_v1(
        manual_axis=manual,
        expected_rows=expected_rows,
        rendered_by_source_page=pages,
    )
    with pytest.raises(
        runner.RunGeminiJsonCreditRiskProvisionExpenseV1Error,
        match="category frontier is incomplete",
    ):
        runner._validate_manual_pdf_review_category_frontier_v1(
            manual_axis=manual[1:],
            expected_rows=expected_rows,
            rendered_by_source_page=pages,
        )
    wrong_page = copy.deepcopy(manual)
    wrong_page[0]["review_kind"] = manual[1]["review_kind"]
    with pytest.raises(
        runner.RunGeminiJsonCreditRiskProvisionExpenseV1Error,
        match="binding drifted",
    ):
        runner._validate_manual_pdf_review_category_frontier_v1(
            manual_axis=wrong_page,
            expected_rows=expected_rows,
            rendered_by_source_page=pages,
        )


def test_pdf_residual_identity_tampering_fails_closed() -> None:
    material = {
        "disposition": (
            "TRUE_NOT_OBSERVED_PRIMARY_ROOT_CARRIER_ONLY_NO_VISIBLE_DETAIL"
        ),
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
            "gjcrpefav1:residual:" + canonical_json_sha256_v1(material)
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
                "NO_PDF_VISIBLE_SCHEMA_MAPPABLE_FAMILY37_ROW_OR_EXPLICIT_SOURCE_AMBIGUITY"
            ),
        },
    }
    assert runner._validate_pdf_residual_spec_v1(spec)
    spec["residuals"][0]["pdf_page_axis"][0]["physical_page"] = 2
    with pytest.raises(
        runner.RunGeminiJsonCreditRiskProvisionExpenseV1Error,
        match="identity drifted",
    ):
        runner._validate_pdf_residual_spec_v1(spec)


def test_source_repair_authentication_types_out_of_corpus_repairs(
    tmp_path: Path,
) -> None:
    receipt = runner._authenticate_source_repairs_v1(
        compiled_specs={
            "credit_risk_provision_expense_source_repairs": [
                {
                    "locator": {
                        "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
                        "physical_page": 1,
                        "section_id": "s1",
                        "table_id": "t1",
                    },
                    "repair_id": "gjcrpefav1:repair:" + "2" * 64,
                    "repair_kind": "MONEY_CELL_PDF_VISIBLE_EXACT",
                    "source_sha256": "3" * 64,
                }
            ]
        },
        index={"documents": []},
        selected_page_axis=[],
        source_pdf_root=tmp_path,
    )
    assert receipt["authenticated"] is True
    assert receipt["applicable_repair_count"] == 0
    assert receipt["out_of_corpus_repair_count"] == 1
    assert receipt["unverified_repair_count"] == 0
