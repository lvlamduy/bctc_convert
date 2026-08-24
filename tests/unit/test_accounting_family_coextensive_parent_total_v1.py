from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation.accounting_family_coextensive_parent_total_v1 import (
    AccountingFamilyCoextensiveParentTotalV1Error,
    project_accounting_family_coextensive_parent_total_region_v1,
    project_accounting_family_coextensive_structural_numeric_rows_v1,
)


def _spec() -> dict:
    parent_aliases = ["Tiền gửi và cho vay TCTD khác", "Tiền gửi và cấp tín dụng TCTD khác"]
    return {
        "children": [
            {
                "matchers": [{"aliases": ["Tiền gửi tại TCTD khác"], "within_role": None}],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [{"aliases": ["Cho vay TCTD khác"], "within_role": None}],
                "presence": "OPTIONAL",
                "role": "LOAN_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [
                    {
                        "aliases": [*parent_aliases, "Tổng tiền gửi và cho vay TCTD khác"],
                        "within_role": None,
                    }
                ],
                "presence": "OPTIONAL",
                "role": "FAMILY_TOTAL",
                "role_kind": "TOTAL",
            },
        ],
        "family_id": "INTERBANK_ASSET",
        "format_version": topology_v1.SPEC_FORMAT_VERSION_V3,
        "hard_negative_aliases": ["Tiền gửi và vay TCTD khác"],
        "limits": {
            "max_cluster_span_lines": 12,
            "max_continuation_pages": 0,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": parent_aliases,
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "INTERBANK_ASSET",
        },
        "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
        "required_role_combinations": [["DEPOSIT_GROUP", "LOAN_GROUP"]],
        "structural_reset_aliases": ["Chứng khoán kinh doanh"],
    }


def _line(index: int, text: str) -> dict:
    top = 100 + index * 40
    return {
        "bbox": [80, top, 520, top + 24],
        "source_line_index": index,
        "source_text": None,
        "vietocr_text": text,
    }


def _pages(parent: str = "Tiền gửi và cho vay TCTD khác", *, explicit_total: bool = False):
    labels = [parent, "Tiền gửi tại TCTD khác", "Cho vay TCTD khác"]
    if explicit_total:
        labels.append("Tổng tiền gửi và cho vay TCTD khác")
    return [
        {
            "lines": [_line(index, text) for index, text in enumerate(labels)],
            "page_sequence": 1,
        }
    ]


def _scan(spec: dict, pages: list[dict]) -> dict:
    return topology_v1.build_accounting_family_topology_scan_v1(pages, spec)


def test_exact_owner_row_is_projected_as_one_declared_total_without_mutating_scan() -> None:
    spec = _spec()
    scan = _scan(spec, _pages())
    frozen_scan = copy.deepcopy(scan)
    region = scan["regions"][0]

    projected = project_accounting_family_coextensive_parent_total_region_v1(spec, scan, region)

    total = next(item for item in projected["child_matches"] if item["role"] == "FAMILY_TOTAL")
    parent = projected["parent_match"]
    locator_fields = (
        "document_line_ordinal",
        "end_document_line_ordinal",
        "page_sequence",
        "source_line_index",
        "end_source_line_index",
    )
    assert {key: total[key] for key in locator_fields} == {
        key: parent[key] for key in locator_fields
    }
    assert total["role_kind"] == "TOTAL"
    assert total["matched_within_role"] is None
    assert projected["observed_roles"] == [
        "FAMILY_TOTAL",
        "DEPOSIT_GROUP",
        "LOAN_GROUP",
    ]
    assert scan == frozen_scan


def test_one_edit_parent_never_becomes_a_coextensive_total() -> None:
    spec = _spec()
    scan = _scan(spec, _pages("Tiền gửi và cho vay TCTD khacx"))
    region = scan["regions"][0]
    assert region["parent_match"]["match_kind"].startswith("ONE_EDIT_ALIAS")

    projected = project_accounting_family_coextensive_parent_total_region_v1(spec, scan, region)

    assert projected == region
    assert all(item["role"] != "FAMILY_TOTAL" for item in projected["child_matches"])


def test_partial_parent_alias_overlap_is_not_an_opt_in() -> None:
    spec = _spec()
    spec["children"][-1]["matchers"][0]["aliases"].remove("Tiền gửi và cấp tín dụng TCTD khác")
    scan = _scan(spec, _pages())
    region = scan["regions"][0]

    projected = project_accounting_family_coextensive_parent_total_region_v1(spec, scan, region)

    assert projected == region


def test_existing_explicit_total_is_not_duplicated() -> None:
    spec = _spec()
    scan = _scan(spec, _pages(explicit_total=True))
    region = scan["regions"][0]
    assert [item["role"] for item in region["child_matches"]].count("FAMILY_TOTAL") == 1

    projected = project_accounting_family_coextensive_parent_total_region_v1(spec, scan, region)

    assert projected == region
    assert [item["role"] for item in projected["child_matches"]].count("FAMILY_TOTAL") == 1


def test_multiple_parent_covering_total_roles_fail_closed() -> None:
    spec = _spec()
    competing = copy.deepcopy(spec["children"][-1])
    competing["role"] = "COMPETING_FAMILY_TOTAL"
    spec["children"].append(competing)
    scan = _scan(spec, _pages())

    with pytest.raises(
        AccountingFamilyCoextensiveParentTotalV1Error,
        match="multiple TOTAL roles",
    ):
        project_accounting_family_coextensive_parent_total_region_v1(spec, scan, scan["regions"][0])


def test_same_boundary_caller_enrichment_is_not_accepted_as_a_source_region() -> None:
    spec = _spec()
    scan = _scan(spec, _pages())
    invented = copy.deepcopy(scan["regions"][0])
    invented["child_matches"].append(
        {
            **copy.deepcopy(invented["parent_match"]),
            "matched_within_role": None,
            "preferred_ordinal": 99,
            "presence": "OPTIONAL",
            "role": "INVENTED_TOTAL",
            "role_kind": "TOTAL",
        }
    )

    with pytest.raises(
        AccountingFamilyCoextensiveParentTotalV1Error,
        match="not one exact complete scan candidate",
    ):
        project_accounting_family_coextensive_parent_total_region_v1(spec, scan, invented)


def _numeric_value(
    *, coefficient: int, lane: int, line_ordinal: int, affinity: float, sample: str
) -> dict:
    return {
        "column_ordinal": lane,
        "line_ordinal": line_ordinal,
        "parsed_token": {
            "coefficient": coefficient,
            "percentage_mark_present": False,
            "scale": 0,
        },
        "row_affinity": affinity,
        "sample_id": sample,
    }


def _numeric_row(
    role: str,
    occurrence: str,
    source_line: int,
    values: list[dict],
    *,
    structural: bool = False,
) -> dict:
    return {
        "label_match": {
            "end_source_line_index": source_line,
            "occurrence_id": occurrence,
            "source_line_index": source_line,
        },
        "role": role,
        "role_kind": "STRUCTURAL_GROUP" if structural else "ADDITIVE_CHILD",
        "status": "VISIBLE_VALUE_LANES_BOUND",
        "values": values,
    }


def _coextensive_projection_fixture() -> tuple[dict, list[dict]]:
    root = "root-scope"
    matches = [
        {
            "document_line_ordinal": 10,
            "end_document_line_ordinal": 10,
            "occurrence_id": "demand",
            "page_sequence": 1,
            "role": "DEMAND_GROUP",
            "role_kind": "STRUCTURAL_GROUP",
            "scope_owner_occurrence_id": root,
        },
        {
            "document_line_ordinal": 11,
            "end_document_line_ordinal": 11,
            "occurrence_id": "demand-vnd",
            "page_sequence": 1,
            "role": "DEMAND_VND",
            "role_kind": "ADDITIVE_CHILD",
            "scope_owner_occurrence_id": "demand",
        },
        {
            "document_line_ordinal": 14,
            "end_document_line_ordinal": 14,
            "occurrence_id": "demand-fx",
            "page_sequence": 1,
            "role": "DEMAND_FX",
            "role_kind": "ADDITIVE_CHILD",
            "scope_owner_occurrence_id": "demand",
        },
        {
            "document_line_ordinal": 20,
            "end_document_line_ordinal": 20,
            "occurrence_id": "term",
            "page_sequence": 1,
            "role": "TERM_GROUP",
            "role_kind": "STRUCTURAL_GROUP",
            "scope_owner_occurrence_id": root,
        },
        {
            "document_line_ordinal": 21,
            "end_document_line_ordinal": 21,
            "occurrence_id": "term-vnd",
            "page_sequence": 1,
            "role": "TERM_VND",
            "role_kind": "ADDITIVE_CHILD",
            "scope_owner_occurrence_id": "term",
        },
        {
            "document_line_ordinal": 24,
            "end_document_line_ordinal": 24,
            "occurrence_id": "term-fx",
            "page_sequence": 1,
            "role": "TERM_FX",
            "role_kind": "ADDITIVE_CHILD",
            "scope_owner_occurrence_id": "term",
        },
    ]
    rows = [
        _numeric_row(
            "DEMAND_VND",
            "demand-vnd",
            11,
            [
                _numeric_value(coefficient=20, lane=0, line_ordinal=12, affinity=2.0, sample="dv0"),
                _numeric_value(coefficient=15, lane=1, line_ordinal=13, affinity=2.0, sample="dv1"),
            ],
        ),
        _numeric_row(
            "DEMAND_FX",
            "demand-fx",
            14,
            [
                _numeric_value(coefficient=10, lane=0, line_ordinal=15, affinity=2.0, sample="df0"),
                _numeric_value(coefficient=5, lane=1, line_ordinal=16, affinity=2.0, sample="df1"),
            ],
        ),
        _numeric_row(
            "TERM_GROUP",
            "term",
            20,
            [
                _numeric_value(
                    coefficient=30, lane=0, line_ordinal=18, affinity=-0.5, sample="subtotal0"
                ),
                _numeric_value(
                    coefficient=20, lane=1, line_ordinal=19, affinity=-0.5, sample="subtotal1"
                ),
            ],
            structural=True,
        ),
        _numeric_row(
            "TERM_VND",
            "term-vnd",
            21,
            [
                _numeric_value(
                    coefficient=100, lane=0, line_ordinal=22, affinity=2.0, sample="tv0"
                ),
                _numeric_value(coefficient=80, lane=1, line_ordinal=23, affinity=2.0, sample="tv1"),
            ],
        ),
        _numeric_row(
            "TERM_FX",
            "term-fx",
            24,
            [
                _numeric_value(coefficient=20, lane=0, line_ordinal=25, affinity=2.0, sample="tf0"),
                _numeric_value(coefficient=10, lane=1, line_ordinal=26, affinity=2.0, sample="tf1"),
            ],
        ),
    ]
    match_by_occurrence = {match["occurrence_id"]: match for match in matches}
    for row in rows:
        row["label_match"] = {
            **match_by_occurrence[row["label_match"]["occurrence_id"]],
            **row["label_match"],
        }
    return {"rows": rows}, matches


def test_exact_preceding_scope_subtotal_is_not_reused_by_next_structural_group() -> None:
    axis, matches = _coextensive_projection_fixture()

    projected, receipts = project_accounting_family_coextensive_structural_numeric_rows_v1(
        axis, matches
    )

    assert "TERM_GROUP" not in {row["role"] for row in projected["rows"]}
    assert [receipt["status"] for receipt in receipts] == [
        "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED"
    ]
    assert receipts[0]["owner_role"] == "DEMAND_GROUP"
    assert receipts[0]["source_sample_ids"] == ["subtotal0", "subtotal1"]


@pytest.mark.parametrize(
    "control",
    [
        "CURRENT_EXACT_SUBTOTAL",
        "SOURCE_CONFLICT",
        "TRUE_SUBTOTAL",
        "VALUES_BEFORE_LABEL",
    ],
)
def test_coextensive_preceding_scope_gate_retains_nonproved_numeric_rows(control: str) -> None:
    axis, matches = _coextensive_projection_fixture()
    term = next(row for row in axis["rows"] if row["role"] == "TERM_GROUP")
    if control == "CURRENT_EXACT_SUBTOTAL":
        coefficients = {
            "TERM_VND": (20, 15),
            "TERM_FX": (10, 5),
        }
        for row in axis["rows"]:
            if row["role"] in coefficients:
                for value, coefficient in zip(
                    row["values"], coefficients[row["role"]], strict=True
                ):
                    value["parsed_token"]["coefficient"] = coefficient
    elif control == "SOURCE_CONFLICT":
        term["values"][0]["parsed_token"]["coefficient"] += 1
    elif control == "TRUE_SUBTOTAL":
        for value in term["values"]:
            value["row_affinity"] = 1.5
    else:
        for row in axis["rows"]:
            if row["role"] in {"TERM_VND", "TERM_FX"}:
                for value in row["values"]:
                    value["line_ordinal"] = row["label_match"]["source_line_index"] - 1

    projected, receipts = project_accounting_family_coextensive_structural_numeric_rows_v1(
        axis, matches
    )

    assert next(row for row in projected["rows"] if row["role"] == "TERM_GROUP") == term
    assert [receipt["status"] for receipt in receipts] == (
        ["COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_AMBIGUOUS_OWNERSHIP_VETO"]
        if control == "CURRENT_EXACT_SUBTOTAL"
        else []
    )


def test_wrapped_child_with_interleaved_values_is_not_treated_as_after_label() -> None:
    axis, matches = _coextensive_projection_fixture()
    term_vnd = next(row for row in axis["rows"] if row["role"] == "TERM_VND")
    term_vnd["label_match"]["end_source_line_index"] = 24
    term_vnd["label_match"]["source_line_indices"] = [21, 24]
    term_fx = next(row for row in axis["rows"] if row["role"] == "TERM_FX")
    term_fx["label_match"]["source_line_index"] = 25
    term_fx["label_match"]["end_source_line_index"] = 25
    for lane, value in enumerate(term_fx["values"]):
        value["line_ordinal"] = 26 + lane
    term_fx_match = next(match for match in matches if match["role"] == "TERM_FX")
    term_fx_match["document_line_ordinal"] = 25
    term_fx_match["end_document_line_ordinal"] = 25

    projected, receipts = project_accounting_family_coextensive_structural_numeric_rows_v1(
        axis, matches
    )

    assert next(row for row in projected["rows"] if row["role"] == "TERM_GROUP")
    assert receipts == []
