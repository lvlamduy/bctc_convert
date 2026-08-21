from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import family_first_accounting_schema_mapping_v1 as subject
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _family_spec() -> dict[str, object]:
    return {
        "children": [
            {
                "aliases": ["Tiền mặt bằng VND"],
                "presence": "REQUIRED",
                "role": "CASH_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Tiền mặt bằng ngoại tệ"],
                "presence": "REQUIRED",
                "role": "CASH_FOREIGN",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "CASH_PRECIOUS_METALS",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V1",
        "hard_negative_aliases": ["Rủi ro tiền tệ"],
        "limits": {
            "max_cluster_span_lines": 30,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Tiền, kim loại quý và đá quý"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "CASH_PRECIOUS_METALS",
        },
        "structural_reset_aliases": ["Tiền gửi tại Ngân hàng Nhà nước"],
    }


def _evaluation_spec() -> dict[str, object]:
    return {
        "closure_policy": "REQUIRE_EXACT_UNIQUE_VISIBLE_TRAILING_TOTAL",
        "expected_lane_unit_kinds": ["MONEY", "MONEY"],
        "family_id": "CASH_PRECIOUS_METALS",
        "format_version": "ACCOUNTING_FAMILY_EVALUATION_SPEC_V1",
        "period_semantics": "BALANCE_COMPARATIVE",
    }


def _binding_spec() -> dict[str, object]:
    return {
        "family_id": "CASH_PRECIOUS_METALS",
        "family_report_norm_id": 561,
        "format_version": subject.SPEC_FORMAT_VERSION,
        "role_bindings": [
            {"report_norm_id": 562, "role": "CASH_VND"},
            {"report_norm_id": 563, "role": "CASH_FOREIGN"},
        ],
    }


def _schema_payload(*, foreign_parent: int = 561) -> bytes:
    nodes = [
        {
            "canonical_name": "Tiền, kim loại quý và đá quý",
            "children": [562, 563],
            "parent_id": 560,
            "schema_id": 561,
            "statement_type": "TM",
        },
        {
            "canonical_name": "Tiền mặt bằng VNĐ",
            "children": [],
            "parent_id": 561,
            "schema_id": 562,
            "statement_type": "TM",
        },
        {
            "canonical_name": "Tiền mặt bằng ngoại tệ",
            "children": [],
            "parent_id": foreign_parent,
            "schema_id": 563,
            "statement_type": "TM",
        },
    ]
    return (
        b"\n".join(
            json.dumps(node, ensure_ascii=False, sort_keys=True).encode("utf-8") for node in nodes
        )
        + b"\n"
    )


def _ref(ordinal: int) -> dict[str, object]:
    return {
        "path": f"opaque/value-{ordinal:04d}.png",
        "sha256": f"{ordinal:064x}",
        "size_bytes": 100 + ordinal,
    }


def _value(
    ordinal: int,
    column: int,
    coefficient: int,
    raw_prediction: str,
    *,
    dash: bool = False,
) -> dict[str, object]:
    return {
        "bbox": [600 + 200 * column, 100 + ordinal * 20, 700 + 200 * column, 122 + ordinal * 20],
        "column_ordinal": column,
        "crop_ref": _ref(ordinal * 10 + column),
        "page_sequence": 1,
        "parsed_token": {
            "classification": "DASH_ZERO" if dash else "SIGNED_NUMBER",
            "coefficient": coefficient,
            "scale": 0,
        },
        "raw_prediction": raw_prediction,
        "sample_id": f"sample-{ordinal * 10 + column:09d}",
    }


def _row(role: str, surface: str, ordinal: int, amounts: tuple[int, int]) -> dict[str, object]:
    return {
        "label_match": {"surface": surface},
        "role": role,
        "status": "VISIBLE_VALUE_LANES_BOUND",
        "values": [
            _value(ordinal, 0, amounts[0], str(amounts[0])),
            _value(
                ordinal,
                1,
                amounts[1],
                "-" if amounts[1] == 0 else str(amounts[1]),
                dash=amounts[1] == 0,
            ),
        ],
    }


def _ready_trial() -> dict[str, object]:
    rows = [
        _row("CASH_VND", "Tiền mặt bằng VND", 1, (100, 90)),
        _row("CASH_FOREIGN", "Tiền mặt bằng ngoại tệ", 2, (20, 0)),
    ]
    total = {
        "candidate_ordinal": 0,
        "status": "COMPLETE_VISIBLE_TRAILING_VALUE_ROW",
        "values": [_value(3, 0, 120, "120"), _value(3, 1, 90, "90")],
    }
    return {
        "additive_closure": {
            "exact_total_candidates": [{"candidate_ordinal": 0}],
            "status": "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL",
        },
        "column_context": {
            "period_axis": [
                {
                    "column_ordinal": 0,
                    "resolved_period": {"as_of_date": "2025-12-31", "kind": "SNAPSHOT"},
                },
                {
                    "column_ordinal": 1,
                    "resolved_period": {"as_of_date": "2024-12-31", "kind": "SNAPSHOT"},
                },
            ],
            "status": "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY",
            "unit_axis": [
                {
                    "column_ordinal": 0,
                    "currency": "VND",
                    "magnitude_power10": 6,
                    "unit_kind": "MONEY",
                },
                {
                    "column_ordinal": 1,
                    "currency": "VND",
                    "magnitude_power10": 6,
                    "unit_kind": "MONEY",
                },
            ],
        },
        "document_ordinal": 1,
        "evidence_status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
        "private_provenance": {"opaque_filing": "filing-0001"},
        "row_axis": {"rows": rows, "trailing_value_rows": [total]},
        "source_pdf_ref": {
            "path": "opaque/source-0001.pdf",
            "sha256": "1" * 64,
            "size_bytes": 1000,
        },
        "unresolved_reasons": [],
    }


def _sweep() -> dict[str, object]:
    return {
        "family_id": "CASH_PRECIOUS_METALS",
        "sweep_id": "ffaesv1:sweep:" + "4" * 64,
        "trials": [
            _ready_trial(),
            {
                "document_ordinal": 2,
                "evidence_status": "NOT_OBSERVED_PROPOSAL_ONLY",
                "private_provenance": {"opaque_filing": "filing-0002"},
                "source_pdf_ref": {
                    "path": "opaque/source-0002.pdf",
                    "sha256": "2" * 64,
                    "size_bytes": 1001,
                },
                "unresolved_reasons": [],
            },
            {
                "document_ordinal": 3,
                "evidence_status": "UNRESOLVED_EVIDENCE_GATES",
                "private_provenance": {"opaque_filing": "filing-0003"},
                "source_pdf_ref": {
                    "path": "opaque/source-0003.pdf",
                    "sha256": "3" * 64,
                    "size_bytes": 1002,
                },
                "unresolved_reasons": ["VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE"],
            },
        ],
    }


def _patch_live(monkeypatch):
    state = {"graph": _schema_payload(), "sweep": _sweep()}
    monkeypatch.setattr(subject.archive_v1, "_root", lambda value: Path(value))
    monkeypatch.setattr(
        subject.archive_v1,
        "_root_bytes",
        lambda _root, _path, _label: state["graph"],
    )
    monkeypatch.setattr(
        subject.evidence_v1,
        "build_authenticated_family_first_accounting_evidence_sweep_v1",
        lambda *_args: copy.deepcopy(state["sweep"]),
    )
    return state


def _build() -> dict[str, object]:
    return subject.build_authenticated_family_first_accounting_schema_mapping_v1(
        Path("/repo"), object(), object(), _family_spec(), _evaluation_spec(), _binding_spec()
    )


def test_live_ready_not_observed_and_unresolved_outcomes(monkeypatch) -> None:
    _patch_live(monkeypatch)

    result = _build()

    assert result["metrics"] == {
        "document_count": 3,
        "not_observed_proposal_count": 1,
        "unresolved_document_count": 1,
        "verified_document_count": 1,
        "verified_mapping_count": 3,
    }
    verified, not_observed, unresolved = result["trials"]
    assert verified["mapping_status"] == "VERIFIED_BY_CODEX"
    assert [item["report_norm_id"] for item in verified["mappings"]] == [562, 563, 561]
    assert verified["mappings"][1]["values"][1]["numeric_value"] == {
        "coefficient": 0,
        "scale": 0,
    }
    assert verified["mappings"][1]["values"][1]["source_zero_kind"] == "VISIBLE_DASH"
    assert verified["mappings"][0]["values"][0]["period"]["as_of_date"] == "2025-12-31"
    assert verified["mappings"][0]["values"][0]["magnitude_power10"] == 6
    assert not_observed["mapping_status"] == "NOT_OBSERVED_PROPOSAL_ONLY"
    assert not_observed["mappings"] == []
    assert unresolved["mapping_status"] == "UNRESOLVED"
    assert unresolved["unresolved_reasons"] == ["VISIBLE_ROLE_ROW_LANES_NOT_COMPLETE"]
    assert result["authority"]["persisted_result_self_authenticating"] is False


def test_exact_live_replay_rejects_coordinated_persisted_numeric_change(monkeypatch) -> None:
    _patch_live(monkeypatch)
    result = _build()
    forged = copy.deepcopy(result)
    mapping = forged["trials"][0]["mappings"][0]
    mapping["values"][0]["numeric_value"]["coefficient"] = 999
    material = copy.deepcopy(forged)
    material.pop("mapping_id")
    forged["mapping_id"] = "ffasmv1:mapping:" + canonical_json_sha256_v1(material)

    with pytest.raises(subject.FamilyFirstAccountingSchemaMappingV1Error, match="replay exactly"):
        subject.validate_authenticated_family_first_accounting_schema_mapping_replay_v1(
            forged,
            Path("/repo"),
            object(),
            object(),
            _family_spec(),
            _evaluation_spec(),
            _binding_spec(),
        )


def test_live_schema_graph_drift_rejects_direct_child_binding(monkeypatch) -> None:
    state = _patch_live(monkeypatch)
    state["graph"] = _schema_payload(foreign_parent=999)

    with pytest.raises(
        subject.FamilyFirstAccountingSchemaMappingV1Error, match="direct live child"
    ):
        _build()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.__setitem__("family_report_norm_id", True),
        lambda value: value["role_bindings"][0].__setitem__("report_norm_id", 563),
        lambda value: value["role_bindings"].reverse(),
        lambda value: value["role_bindings"][0].__setitem__("role", "BANK_SPECIFIC"),
    ],
)
def test_schema_binding_spec_type_identity_and_role_axis_fail_closed(monkeypatch, mutation) -> None:
    _patch_live(monkeypatch)
    spec = _binding_spec()
    mutation(spec)

    with pytest.raises(subject.FamilyFirstAccountingSchemaMappingV1Error):
        subject.build_authenticated_family_first_accounting_schema_mapping_v1(
            Path("/repo"), object(), object(), _family_spec(), _evaluation_spec(), spec
        )


def test_mapper_contains_no_bank_page_year_or_filing_specific_route() -> None:
    payload = Path(subject.__file__).read_text(encoding="utf-8")
    for token in ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB", "2025", "2026"):
        assert token not in payload
