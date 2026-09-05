from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from scripts.experiments import (
    run_gemini_json_interest_expense_accounting_family_v1 as runner,
)

ROOT = Path(__file__).resolve().parents[2]


def _audit() -> dict:
    source_authentication_axis = [{"repair_id": "repair"}]
    material = {
        "axis_counts": {
            "equations": 1,
            "mappings": 2,
            "query_repairs": 1,
            "source_repairs": 1,
            "trials": 1,
            "unit_corroborations": 1,
        },
        "axis_sha256": {},
        "family_id": runner.FAMILY_ID,
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": {
            "corpus_relation": {"overlap_count": 0},
            "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
            "policy": runner.DISJOINT_EXPANSION,
        },
        "indexed_query_receipt": {},
        "source_authentication_axis": source_authentication_axis,
        "source_authentication_axis_sha256": canonical_json_sha256_v1(
            source_authentication_axis
        ),
        "source_authentication_count": 1,
        "source_observation_contract": {"violation_count": 0},
        "spec_refs": {},
        "sweep_id": "sweep",
        "sweep_output": "/dev/shm/family29.json",
    }
    return {
        **material,
        "audit_id": "gjiefauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def _reseal(audit: dict) -> None:
    material = {key: value for key, value in audit.items() if key != "audit_id"}
    audit["audit_id"] = "gjiefauditv1:audit:" + canonical_json_sha256_v1(material)


def test_runner_pins_shared_engine_and_runner() -> None:
    runner._assert_shared_pins_v1()


def test_runner_rejects_non_disjoint_policy_before_reading_inputs() -> None:
    with pytest.raises(
        runner.RunGeminiJsonInterestExpenseV1Error,
        match="requires DISJOINT_EXPANSION",
    ):
        runner.run(argparse.Namespace(historical_comparator_policy="STRICT_RELEASE"))


def test_current_corpus_gate_rejects_historical_document() -> None:
    with pytest.raises(
        runner.RunGeminiJsonInterestExpenseV1Error,
        match="outside the current reporting scope",
    ):
        runner._assert_current_corpus(
            {"documents": [{"relative_path": "bank/2024/report.pdf"}]}
        )


def test_render_authentication_requires_real_pdf_root(tmp_path: Path) -> None:
    with pytest.raises(
        runner.RunGeminiJsonInterestExpenseV1Error,
        match="source-PDF root is unavailable",
    ):
        runner._render_authentication(
            document={
                "relative_path": "fixture.pdf",
                "source_sha256": "1" * 64,
                "source_size_bytes": 1,
            },
            physical_page=1,
            expected_render_sha256="2" * 64,
            source_pdf_root=tmp_path / "missing",
            payload_cache={},
            render_cache={},
        )


def test_cross_source_authentication_binds_selected_json_value(monkeypatch) -> None:
    spec = json.loads(
        (ROOT / "config/families/tm-interest-expense-source-repair-v1.json").read_bytes()
    )
    repair = next(item for item in spec["repairs"] if "corroboration" in item)
    target_sha = repair["source_sha256"]
    corroboration = repair["corroboration"]
    target_document = {
        "relative_path": "target.pdf",
        "source_sha256": target_sha,
        "source_size_bytes": 1,
    }
    corroborating_document = {
        "relative_path": corroboration["source_logical_name"],
        "source_sha256": corroboration["source_sha256"],
        "source_size_bytes": 1,
    }
    selected_documents = [
        {
            "document_ordinal": 1,
            "source_sha256": target_sha,
        },
        {
            "document_ordinal": 2,
            "source_sha256": corroboration["source_sha256"],
        },
    ]
    selected_pages = [
        {
            "document_ordinal": 1,
            "page_json_version_id": repair["locator"]["page_json_version_id"],
            "physical_page": repair["locator"]["physical_page"],
            "source_sha256": target_sha,
        },
        {
            "document_ordinal": 2,
            "page_json_version_id": corroboration["page_json_version_id"],
            "physical_page": corroboration["physical_page"],
            "source_sha256": corroboration["source_sha256"],
        },
    ]
    rows = [
        {
            "hierarchy_path_exact": ["Trả lãi tiền gửi"],
            "label_exact": "Trả lãi tiền gửi",
            "row_kind": "ITEM",
            "values_exact": ["1", corroboration["value_exact"]],
        }
    ]
    page = {
        "sections": [
            {
                "tables": [
                    {"columns": [], "rows": []},
                    {
                        "columns": [
                            {"header_path_exact": ["Năm nay"], "value_kind": "MONEY"},
                            {"header_path_exact": ["Năm trước"], "value_kind": "MONEY"},
                        ],
                        "rows": rows,
                    }
                ]
            }
        ]
    }
    monkeypatch.setattr(
        runner,
        "_render_authentication",
        lambda **kwargs: {
            "physical_page": kwargs["physical_page"],
            "source_sha256": kwargs["document"]["source_sha256"],
        },
    )

    checked = runner._authenticate_applicable_source_repairs_v1(
        repairs=[repair],
        index={"documents": [target_document, corroborating_document]},
        indexed_query_evidence={
            "selected_document_axis": selected_documents,
            "selected_page_axis": selected_pages,
        },
        page_json_by_document={
            2: {corroboration["page_json_version_id"]: page}
        },
        source_pdf_root=Path("."),
    )

    assert len(checked) == 1
    assert checked[0]["repair_id"] == repair["repair_id"]

    rows[0]["values_exact"][1] = "tampered"
    with pytest.raises(
        runner.RunGeminiJsonInterestExpenseV1Error,
        match="corroborating selected JSON value drifted",
    ):
        runner._authenticate_applicable_source_repairs_v1(
            repairs=[repair],
            index={"documents": [target_document, corroborating_document]},
            indexed_query_evidence={
                "selected_document_axis": selected_documents,
                "selected_page_axis": selected_pages,
            },
            page_json_by_document={
                2: {corroboration["page_json_version_id"]: page}
            },
            source_pdf_root=Path("."),
        )


def test_audit_rejects_contract_violation_and_identity_tamper() -> None:
    assert runner.validate_interest_expense_experimental_audit_v1(_audit())

    invented = copy.deepcopy(_audit())
    invented["source_observation_contract"]["violation_count"] = 1
    _reseal(invented)
    with pytest.raises(
        runner.RunGeminiJsonInterestExpenseV1Error,
        match="audit content is invalid",
    ):
        runner.validate_interest_expense_experimental_audit_v1(invented)

    tampered = _audit()
    tampered["sweep_id"] = "tampered"
    with pytest.raises(
        runner.RunGeminiJsonInterestExpenseV1Error,
        match="audit identity drifted",
    ):
        runner.validate_interest_expense_experimental_audit_v1(tampered)
