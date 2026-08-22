from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.accounting_family_row_axis_v1 import (
    build_accounting_family_row_axis_v1,
)
from bctc_ai.evaluation.accounting_hierarchical_table_closure_v1 import (
    AccountingHierarchicalTableClosureV1Error,
    build_accounting_hierarchical_table_closure_v1,
    validate_accounting_hierarchical_table_closure_replay_v1,
)


def _matcher(alias: str, within_role: str | None = None) -> dict[str, object]:
    return {"aliases": [alias], "within_role": within_role}


def _topology_spec() -> dict[str, object]:
    return {
        "children": [
            {
                "matchers": [_matcher("Tiền gửi tại TCTD khác")],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [_matcher("Bằng VND", "DEPOSIT_GROUP")],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Bằng ngoại tệ", "DEPOSIT_GROUP")],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_FOREIGN_CURRENCY",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Cho vay TCTD khác")],
                "presence": "OPTIONAL",
                "role": "LOAN_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [_matcher("Bằng VND", "LOAN_GROUP")],
                "presence": "OPTIONAL",
                "role": "LOAN_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Bằng ngoại tệ", "LOAN_GROUP")],
                "presence": "OPTIONAL",
                "role": "LOAN_FOREIGN_CURRENCY",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Tổng cộng")],
                "presence": "OPTIONAL",
                "role": "EXPLICIT_FAMILY_TOTAL",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "INTERBANK_DEPOSITS_AND_LOANS",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3",
        "hard_negative_aliases": [],
        "limits": {
            "max_cluster_span_lines": 40,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Tiền gửi và cho vay các TCTD khác"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "INTERBANK_DEPOSITS_AND_LOANS",
        },
        "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
        "required_role_combinations": [["DEPOSIT_GROUP", "LOAN_GROUP"]],
        "structural_reset_aliases": [],
    }


def _hierarchy_spec() -> dict[str, object]:
    return {
        "equations": [
            {
                "component_roles": ["DEPOSIT_VND", "DEPOSIT_FOREIGN_CURRENCY"],
                "minimum_component_count": 1,
                "result_role": "DEPOSIT_GROUP",
                "trailing_result_policy": "IGNORE",
                "visible_result_roles": ["DEPOSIT_GROUP"],
            },
            {
                "component_roles": ["LOAN_VND", "LOAN_FOREIGN_CURRENCY"],
                "minimum_component_count": 1,
                "result_role": "LOAN_GROUP",
                "trailing_result_policy": "IGNORE",
                "visible_result_roles": ["LOAN_GROUP"],
            },
            {
                "component_roles": ["DEPOSIT_GROUP", "LOAN_GROUP"],
                "minimum_component_count": 2,
                "result_role": "INTERBANK_DEPOSITS_AND_LOANS",
                "trailing_result_policy": "CORROBORATE_IF_PRESENT",
                "visible_result_roles": ["EXPLICIT_FAMILY_TOTAL"],
            },
        ],
        "family_id": "INTERBANK_DEPOSITS_AND_LOANS",
        "format_version": "ACCOUNTING_HIERARCHICAL_CLOSURE_SPEC_V1",
    }


def _line(ordinal: int, text: str, numeric: str, bbox: list[int]) -> dict[str, object]:
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": numeric, "reader_score": 0.95},
        "sample_id": f"sample-{ordinal + 1:09d}",
        "vietocr_text": text,
    }


def _page(rows: list[tuple[str, str, str]]) -> list[dict[str, object]]:
    lines = [
        _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 450, 42]),
        _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
        _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
    ]
    ordinal = 3
    for label, current, comparative in rows:
        top = 80 + ordinal * 25
        lines.extend(
            [
                _line(ordinal, label, "", [50, top, 360, top + 20]),
                _line(ordinal + 1, current, current, [600, top, 700, top + 20]),
                _line(
                    ordinal + 2,
                    comparative,
                    comparative,
                    [800, top, 900, top + 20],
                ),
            ]
        )
        ordinal += 3
    return [{"lines": lines, "page_sequence": 1, "page_width": 1000}]


def _detail_pages(*, family_total: tuple[str, str] | None = ("150", "125")) -> list[dict]:
    rows = [
        ("Tiền gửi tại TCTD khác", "", ""),
        ("Bằng VND", "100", "80"),
        ("Bằng ngoại tệ", "20", "15"),
        ("Cho vay TCTD khác", "", ""),
        ("Bằng VND", "25", "25"),
        ("Bằng ngoại tệ", "5", "5"),
    ]
    if family_total is not None:
        rows.append(("Tổng cộng", *family_total))
    return _page(rows)


def _build(pages: list[dict]) -> tuple[dict, dict]:
    axis = build_accounting_family_row_axis_v1(pages, _topology_spec())
    closure = build_accounting_hierarchical_table_closure_v1(
        axis,
        pages,
        _topology_spec(),
        _hierarchy_spec(),
    )
    return axis, closure


def test_detail_children_derive_groups_and_corroborate_visible_family_total() -> None:
    pages = _detail_pages()
    axis, closure = _build(pages)

    assert axis["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    roles = {record["role"]: record for record in closure["resolved_roles"]}
    assert roles["DEPOSIT_GROUP"]["resolution_kind"] == "DERIVED_EXACT_COMPONENT_SUM"
    assert roles["LOAN_GROUP"]["resolution_kind"] == "DERIVED_EXACT_COMPONENT_SUM"
    assert roles["INTERBANK_DEPOSITS_AND_LOANS"]["resolution_kind"] == (
        "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS"
    )
    assert [value["number"]["coefficient"] for value in roles["DEPOSIT_GROUP"]["values"]] == [
        120,
        95,
    ]
    assert closure["metrics"]["derived_role_count"] == 2


def test_summary_rows_are_retained_without_inventing_missing_detail_children() -> None:
    pages = _page(
        [
            ("Tiền gửi tại TCTD khác", "120", "95"),
            ("Cho vay TCTD khác", "30", "30"),
        ]
    )
    _axis, closure = _build(pages)

    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    roles = {record["role"]: record for record in closure["resolved_roles"]}
    assert roles["DEPOSIT_GROUP"]["resolution_kind"] == "VISIBLE_SOURCE_ROLE"
    assert roles["LOAN_GROUP"]["resolution_kind"] == "VISIBLE_SOURCE_ROLE"
    assert roles["INTERBANK_DEPOSITS_AND_LOANS"]["resolution_kind"] == (
        "DERIVED_EXACT_COMPONENT_SUM"
    )
    assert "DEPOSIT_VND" not in roles


def test_visible_total_mismatch_is_veto_and_never_repairs_source_digits() -> None:
    pages = _detail_pages(family_total=("151", "125"))
    _axis, closure = _build(pages)

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert closure["unresolved_reasons"] == [
        "VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_DEPOSITS_AND_LOANS"
    ]
    total = next(
        record for record in closure["resolved_roles"] if record["role"] == "EXPLICIT_FAMILY_TOTAL"
    )
    assert total["values"][0]["number"]["coefficient"] == 151


def test_unique_unlabelled_trailing_total_is_corroborated() -> None:
    pages = _detail_pages(family_total=None)
    last = pages[0]["lines"][-1]["line_ordinal"] + 1
    pages[0]["lines"].extend(
        [
            _line(last, "150", "150", [600, 420, 700, 440]),
            _line(last + 1, "125", "125", [800, 420, 900, 440]),
        ]
    )
    _axis, closure = _build(pages)

    family = next(
        record
        for record in closure["resolved_roles"]
        if record["role"] == "INTERBANK_DEPOSITS_AND_LOANS"
    )
    assert family["resolution_kind"] == "VISIBLE_TRAILING_TOTAL_CORROBORATED_BY_COMPONENTS"


def test_explicit_corroborated_total_is_not_vetoed_by_later_unlabelled_numeric_row() -> None:
    pages = _detail_pages()
    last = pages[0]["lines"][-1]["line_ordinal"] + 1
    pages[0]["lines"].extend(
        [
            _line(last, "999", "999", [600, 460, 700, 480]),
            _line(last + 1, "998", "998", [800, 460, 900, 480]),
        ]
    )
    _axis, closure = _build(pages)

    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    family = next(
        record
        for record in closure["resolved_roles"]
        if record["role"] == "INTERBANK_DEPOSITS_AND_LOANS"
    )
    assert family["resolution_kind"] == "VISIBLE_SOURCE_ROLE_CORROBORATED_BY_COMPONENTS"


def test_partial_unlabelled_trailing_row_is_ineligible_as_total_without_veto() -> None:
    pages = _detail_pages(family_total=None)
    last = pages[0]["lines"][-1]["line_ordinal"] + 1
    pages[0]["lines"].append(
        _line(last, "150", "150", [600, 420, 700, 440]),
    )

    _axis, closure = _build(pages)

    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    assert closure["unresolved_reasons"] == []
    family = next(
        record
        for record in closure["resolved_roles"]
        if record["role"] == "INTERBANK_DEPOSITS_AND_LOANS"
    )
    assert family["resolution_kind"] == "DERIVED_EXACT_COMPONENT_SUM"


def test_child_subtotals_are_not_competing_parent_totals() -> None:
    lines = [
        _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 450, 42]),
        _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
        _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
        _line(3, "Tiền gửi tại TCTD khác", "", [50, 100, 360, 120]),
        _line(4, "Bằng VND", "", [50, 130, 360, 150]),
        _line(5, "100", "100", [600, 130, 700, 150]),
        _line(6, "80", "80", [800, 130, 900, 150]),
        _line(7, "Bằng ngoại tệ", "", [50, 160, 360, 180]),
        _line(8, "20", "20", [600, 160, 700, 180]),
        _line(9, "15", "15", [800, 160, 900, 180]),
        _line(10, "120", "120", [600, 190, 700, 210]),
        _line(11, "95", "95", [800, 190, 900, 210]),
        _line(12, "Cho vay TCTD khác", "", [50, 220, 360, 240]),
        _line(13, "Bằng VND", "", [50, 250, 360, 270]),
        _line(14, "25", "25", [600, 250, 700, 270]),
        _line(15, "25", "25", [800, 250, 900, 270]),
        _line(16, "Bằng ngoại tệ", "", [50, 280, 360, 300]),
        _line(17, "5", "5", [600, 280, 700, 300]),
        _line(18, "5", "5", [800, 280, 900, 300]),
        _line(19, "30", "30", [600, 310, 700, 330]),
        _line(20, "30", "30", [800, 310, 900, 330]),
    ]
    pages = [{"lines": lines, "page_sequence": 1, "page_width": 1000}]

    axis, closure = _build(pages)

    assert len(axis["trailing_value_rows"]) == 1
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    family = next(
        record
        for record in closure["resolved_roles"]
        if record["role"] == "INTERBANK_DEPOSITS_AND_LOANS"
    )
    assert family["resolution_kind"] == "DERIVED_EXACT_COMPONENT_SUM"
    assert [value["number"]["coefficient"] for value in family["values"]] == [150, 125]


def test_replay_rejects_coordinated_role_value_and_identity_mutation() -> None:
    pages = _detail_pages()
    axis, closure = _build(pages)
    forged = copy.deepcopy(closure)
    forged["resolved_roles"][0]["values"][0]["number"]["coefficient"] += 1
    material = copy.deepcopy(forged)
    material.pop("closure_id")
    from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

    forged["closure_id"] = "ahtcv1:closure:" + canonical_json_sha256_v1(material)

    with pytest.raises(
        AccountingHierarchicalTableClosureV1Error,
        match="does not replay exactly",
    ):
        validate_accounting_hierarchical_table_closure_replay_v1(
            forged,
            axis,
            pages,
            _topology_spec(),
            _hierarchy_spec(),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda spec: spec["equations"][0].__setitem__("minimum_component_count", True),
        lambda spec: spec["equations"][0]["component_roles"].append("UNKNOWN_ROLE"),
        lambda spec: spec["equations"][1].__setitem__(
            "component_roles", ["INTERBANK_DEPOSITS_AND_LOANS"]
        ),
    ],
)
def test_hierarchy_spec_rejects_type_unknown_role_and_dependency_drift(mutation) -> None:
    pages = _detail_pages()
    axis = build_accounting_family_row_axis_v1(pages, _topology_spec())
    spec = _hierarchy_spec()
    mutation(spec)

    with pytest.raises(AccountingHierarchicalTableClosureV1Error):
        build_accounting_hierarchical_table_closure_v1(
            axis,
            pages,
            _topology_spec(),
            spec,
        )
