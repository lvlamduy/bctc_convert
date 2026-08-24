from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation.accounting_family_coextensive_parent_total_v1 import (
    AccountingFamilyCoextensiveParentTotalV1Error,
    project_accounting_family_coextensive_parent_total_region_v1,
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
