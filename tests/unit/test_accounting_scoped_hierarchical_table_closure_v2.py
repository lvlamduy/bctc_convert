from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import accounting_family_occurrence_row_axis_v2 as occurrence_v2
from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_v1
from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import accounting_scoped_hierarchical_table_closure_v2 as subject
from bctc_ai.evaluation import family_first_accounting_schema_mapping_v1 as mapping_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _matcher(alias: str, within: str | None = None) -> dict[str, object]:
    return {"aliases": [alias], "within_role": within}


def _topology() -> dict[str, object]:
    return {
        "children": [
            {
                "matchers": [_matcher("Tiền gửi tại TCTD khác")],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
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
                "matchers": [_matcher("Dự phòng cho vay TCTD khác", "LOAN_GROUP")],
                "presence": "OPTIONAL",
                "role": "LOAN_PROVISION",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [_matcher("Tổng cộng")],
                "presence": "OPTIONAL",
                "role": "EXPLICIT_FAMILY_TOTAL",
                "role_kind": "TOTAL",
            },
        ],
        "family_id": "INTERBANK",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3",
        "hard_negative_aliases": [],
        "limits": {
            "max_cluster_span_lines": 50,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Tiền gửi và cho vay TCTD khác"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "INTERBANK",
        },
        "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
        "required_role_combinations": [["DEPOSIT_GROUP", "LOAN_GROUP"]],
        "structural_reset_aliases": [],
    }


def _alternative(roles: list[str], *, derive: bool = True) -> dict[str, object]:
    return {
        "component_roles": roles,
        "coverage_policy": "EXHAUSTIVE_COMPONENT_SET",
        "derivation_policy": (
            "ALLOW_DERIVATION_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"
            if derive
            else "VISIBLE_RESULT_CORROBORATION_ONLY"
        ),
    }


def _hierarchy() -> dict[str, object]:
    return {
        "equations": [
            {
                "application_policy": "REQUIRED_WHEN_ANY_DECLARED_ROLE_VISIBLE",
                "component_role_alternatives": [
                    _alternative(["LOAN_VND", "LOAN_FOREIGN_CURRENCY"]),
                    _alternative(["LOAN_VND", "LOAN_FOREIGN_CURRENCY", "LOAN_PROVISION"]),
                ],
                "result_role": "LOAN_GROUP",
                "trailing_result_policy": "IGNORE",
                "visible_result_roles": ["LOAN_GROUP"],
                "visible_source_policy": "ALLOW_ONLY_WHEN_NO_DECLARED_COMPONENT_ROLE_VISIBLE",
            },
            {
                "application_policy": "REQUIRED_WHEN_ANY_DECLARED_ROLE_VISIBLE",
                "component_role_alternatives": [
                    _alternative(["DEPOSIT_GROUP", "LOAN_GROUP"]),
                    _alternative(["DEPOSIT_GROUP", "LOAN_GROUP", "LOAN_PROVISION"]),
                ],
                "result_role": "INTERBANK",
                "trailing_result_policy": "CORROBORATE_IF_PRESENT",
                "visible_result_roles": ["EXPLICIT_FAMILY_TOTAL"],
                "visible_source_policy": "REQUIRE_EXHAUSTIVE_COMPONENTS",
            },
        ],
        "family_id": "INTERBANK",
        "format_version": subject.SPEC_FORMAT_VERSION,
        "repeated_role_policy": {
            "aggregate_roles": [
                "LOAN_FOREIGN_CURRENCY",
                "LOAN_GROUP",
                "LOAN_VND",
            ],
            "local_subtotal_roles": ["LOAN_GROUP"],
        },
    }


def _hierarchy_v2(*, source_only_veto_roles: list[str] | None = None) -> dict[str, object]:
    hierarchy = copy.deepcopy(_hierarchy())
    hierarchy["format_version"] = subject.SPEC_FORMAT_VERSION_V2
    hierarchy["source_role_policy"] = {
        "one_edit_role_or_scope_match_policy": "VETO",
        "source_only_veto_roles": sorted(source_only_veto_roles or []),
    }
    return hierarchy


def _line(ordinal: int, text: str, numeric: str, bbox: list[int]) -> dict[str, object]:
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": numeric, "reader_score": 0.98},
        "sample_id": f"sample-{ordinal + 1:09d}",
        "vietocr_text": text,
    }


def _pages(
    rows: list[tuple[str, str, str]],
    *,
    trailing: list[tuple[str | None, str | None]] | None = None,
) -> list[dict[str, object]]:
    lines = [
        _line(0, "Tiền gửi và cho vay TCTD khác", "", [25, 15, 460, 38]),
        _line(1, "31/12/2025", "", [610, 45, 700, 65]),
        _line(2, "31/12/2024", "", [810, 45, 900, 65]),
        _line(3, "Đơn vị: Triệu đồng", "", [610, 72, 900, 94]),
    ]
    for row_index, (label, current, prior) in enumerate(rows):
        ordinal = len(lines)
        top = 110 + row_index * 50
        lines.extend(
            [
                _line(ordinal, label, "", [45, top, 430, top + 20]),
                _line(ordinal + 1, current, current, [610, top, 700, top + 20]),
                _line(ordinal + 2, prior, prior, [810, top, 900, top + 20]),
            ]
        )
    trailing_top = 110 + len(rows) * 50
    for trailing_index, (current, prior) in enumerate(trailing or []):
        ordinal = len(lines)
        top = trailing_top + trailing_index * 24
        if current is not None:
            lines.append(_line(ordinal, current, current, [610, top, 700, top + 20]))
            ordinal += 1
        if prior is not None:
            lines.append(_line(ordinal, prior, prior, [810, top, 900, top + 20]))
    return [{"lines": lines, "page_sequence": 1, "page_width": 1000}]


def _acb_shaped_preceding_subtotal_pages(
    *, demand_subtotal_current: str = "30", demand_subtotal_prior: str = "20"
) -> list[dict[str, object]]:
    """Provider-order fixture: prior subtotal touches the next group label."""

    lines = [
        _line(0, "Tiền gửi và cho vay các TCTD khác", "", [25, 15, 500, 49]),
        _line(1, "31/12/2025", "", [610, 65, 700, 92]),
        _line(2, "31/12/2024", "", [810, 65, 900, 92]),
        _line(3, "Đơn vị: Triệu đồng", "", [610, 96, 900, 123]),
        _line(4, "Tiền gửi không kỳ hạn", "", [45, 120, 430, 154]),
        _line(5, "Bằng Đồng Việt Nam", "", [65, 155, 430, 189]),
        _line(6, "20", "20", [610, 157, 700, 184]),
        _line(7, "15", "15", [810, 157, 900, 184]),
        _line(8, "Bằng ngoại tệ", "", [65, 190, 430, 224]),
        _line(9, "10", "10", [610, 192, 700, 219]),
        _line(10, "5", "5", [810, 192, 900, 219]),
        _line(
            11,
            demand_subtotal_current,
            demand_subtotal_current,
            [610, 245, 700, 279],
        ),
        _line(
            12,
            demand_subtotal_prior,
            demand_subtotal_prior,
            [810, 245, 900, 279],
        ),
        _line(13, "Tiền gửi có kỳ hạn", "", [45, 274, 430, 314]),
        _line(14, "Bằng Đồng Việt Nam", "", [65, 309, 430, 343]),
        _line(15, "100", "100", [610, 311, 700, 338]),
        _line(16, "80", "80", [810, 311, 900, 338]),
        _line(17, "Bằng ngoại tệ", "", [65, 344, 430, 378]),
        _line(18, "20", "20", [610, 346, 700, 373]),
        _line(19, "10", "10", [810, 346, 900, 373]),
        _line(20, "Cho vay các TCTD khác", "", [45, 410, 430, 444]),
        _line(21, "50", "50", [610, 412, 700, 439]),
        _line(22, "40", "40", [810, 412, 900, 439]),
        _line(
            23,
            "Tổng tiền gửi và cho vay các TCTD khác",
            "",
            [45, 470, 500, 504],
        ),
        _line(24, "200", "200", [610, 472, 700, 499]),
        _line(25, "150", "150", [810, 472, 900, 499]),
    ]
    return [{"lines": lines, "page_sequence": 1, "page_width": 1000}]


def _axis(pages: list[dict[str, object]], topology: dict[str, object] | None = None) -> dict:
    topology = _topology() if topology is None else topology
    scan = topology_v1.build_accounting_family_topology_scan_v1(
        row_v1._topology_pages(pages), topology
    )
    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    return occurrence_v2.build_accounting_family_occurrence_row_axis_v2(
        pages,
        topology,
        scan,
        scan["regions"][0],
        {
            "format_version": occurrence_v2.POLICY_FORMAT_VERSION,
            "require_authenticated_existing_dash_pixels": True,
            "retain_all_context_bound_role_occurrences": True,
        },
    )


def _closure(
    pages: list[dict[str, object]],
    *,
    topology: dict[str, object] | None = None,
    hierarchy: dict[str, object] | None = None,
) -> tuple[dict, dict]:
    topology = _topology() if topology is None else topology
    hierarchy = _hierarchy() if hierarchy is None else hierarchy
    axis = _axis(pages, topology)
    closure = subject.build_accounting_scoped_hierarchical_table_closure_v2(
        axis, topology, hierarchy
    )
    return axis, closure


def _coherently_rehash_closure(closure: dict) -> None:
    closure["metrics"] = subject._metrics(
        closure["resolved_roles"],
        closure["equations"]["global"],
        closure["equations"]["local"],
        closure["coverage_receipt"],
        closure["unresolved_reasons"],
    )
    material = copy.deepcopy(closure)
    material.pop("closure_id")
    closure["closure_id"] = "ashtcv2:closure:" + canonical_json_sha256_v1(material)


def _insert_internal_numeric_pair(pages: list[dict], token: str) -> None:
    lines = pages[0]["lines"]
    lines[7:7] = [
        _line(999, token, token, [610, 185, 700, 205]),
        _line(1_000, token, token, [810, 185, 900, 205]),
    ]
    for ordinal, line in enumerate(lines):
        line["line_ordinal"] = ordinal
        line["sample_id"] = f"sample-{ordinal + 1:09d}"
        line["crop_ref"] = {
            "path": f"opaque/crop-{ordinal + 1:04d}.png",
            "sha256": f"{ordinal + 1:064x}",
            "size_bytes": 100 + ordinal,
        }


@pytest.mark.parametrize("token", ["0", "7", "-"])
def test_internal_typed_money_lane_sample_is_source_only_and_always_vetoes(
    token: str,
) -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
        ]
    )
    _insert_internal_numeric_pair(pages, token)

    axis, closure = _closure(pages)

    assert len(axis["internal_unassigned_numeric_clusters"]) == 1
    cluster = axis["internal_unassigned_numeric_clusters"][0]
    source_only = [
        sample
        for sample in axis["numeric_sample_universe"]
        if sample["owner_kind"] == "SOURCE_ONLY_INTERNAL_CLUSTER"
    ]
    assert [sample["sample_id"] for sample in source_only] == cluster["sample_ids"]
    assert {sample["parsed_token"]["classification"] for sample in source_only} == {
        "DASH_ZERO" if token == "-" else "SIGNED_NUMBER"
    }
    receipt = next(
        record
        for record in closure["coverage_receipt"]
        if record["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
    )
    assert receipt["sample_ids"] == cluster["sample_ids"]
    assert receipt["disposition"] == "UNRESOLVED_SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER"
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert (
        f"SOURCE_ONLY_INTERNAL_NUMERIC_CLUSTER_VETO:{cluster['cluster_id']}"
        in closure["unresolved_reasons"]
    )
    assert len(
        [sample_id for record in closure["coverage_receipt"] for sample_id in record["sample_ids"]]
    ) == len(axis["numeric_sample_universe"])


def test_numeric_universe_sample_cannot_lose_its_only_receipt_after_coherent_rehash() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
        ]
    )
    _insert_internal_numeric_pair(pages, "7")
    _axis_value, closure = _closure(pages)
    attacked = copy.deepcopy(closure)
    source_only = next(
        record
        for record in attacked["coverage_receipt"]
        if record["row_kind"] == "INTERNAL_UNASSIGNED_NUMERIC_CLUSTER"
    )
    source_only["sample_ids"].pop()
    source_only["source_record"]["sample_ids"].pop()
    source_only["source_record"]["column_ordinals"].pop()
    _coherently_rehash_closure(attacked)

    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="internal numeric cluster|exactly one owning coverage receipt",
    ):
        subject._validate_result(attacked)


def test_one_edit_role_match_cannot_close_while_exact_source_can() -> None:
    exact_pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Tổng cộng", "150", "130"),
        ]
    )
    typo_pages = copy.deepcopy(exact_pages)
    typo_pages[0]["lines"][4]["vietocr_text"] = "Tiền gửi tại TCTD kháx"

    _exact_axis, exact = _closure(exact_pages, hierarchy=_hierarchy_v2())
    typo_axis, typo = _closure(typo_pages, hierarchy=_hierarchy_v2())

    assert exact["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    deposit = next(row for row in typo_axis["row_axis"]["rows"] if row["role"] == "DEPOSIT_GROUP")
    assert deposit["label_match"]["match_kind"].startswith("ONE_EDIT_")
    receipt = next(
        record for record in typo["coverage_receipt"] if record["role"] == "DEPOSIT_GROUP"
    )
    assert receipt["disposition"] == "UNRESOLVED_ONE_EDIT_ROLE_OR_SCOPE_MATCH"
    assert typo["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"


def test_other_requires_an_exact_unique_scope_owner_before_it_can_close() -> None:
    topology = copy.deepcopy(_topology())
    topology["children"].insert(
        -1,
        {
            "matchers": [_matcher("Khác", "LOAN_GROUP")],
            "presence": "OPTIONAL",
            "role": "LOAN_OTHER",
            "role_kind": "ADDITIVE_CHILD",
        },
    )
    hierarchy = _hierarchy_v2()
    hierarchy["equations"][0]["component_role_alternatives"].append(
        _alternative(["LOAN_OTHER"], derive=False)
    )
    hierarchy["repeated_role_policy"]["aggregate_roles"].append("LOAN_OTHER")
    hierarchy["repeated_role_policy"]["aggregate_roles"].sort()
    exact_pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "5", "4"),
            ("Khác", "5", "4"),
            ("Tổng cộng", "105", "94"),
        ]
    )
    typo_pages = copy.deepcopy(exact_pages)
    typo_pages[0]["lines"][7]["vietocr_text"] = "Cho vay TCTD kháx"

    _exact_axis, exact = _closure(exact_pages, topology=topology, hierarchy=hierarchy)
    typo_axis, typo = _closure(typo_pages, topology=topology, hierarchy=hierarchy)

    assert exact["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    exact_other = next(
        record for record in exact["coverage_receipt"] if record["role"] == "LOAN_OTHER"
    )
    assert exact_other["disposition"] == "LOCAL_EXHAUSTIVE_COMPONENT_OCCURRENCE"
    typo_other_occurrence = next(
        occurrence
        for occurrence in typo_axis["role_occurrences"]
        if occurrence["role"] == "LOAN_OTHER"
    )
    assert typo_other_occurrence["scope_owner_match_kind"].startswith("ONE_EDIT_")
    typo_other = next(
        record for record in typo["coverage_receipt"] if record["role"] == "LOAN_OTHER"
    )
    assert typo_other["disposition"] == "UNRESOLVED_ONE_EDIT_ROLE_OR_SCOPE_MATCH"
    assert typo["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"


def test_declared_source_only_role_is_typed_but_never_accounting_resolved() -> None:
    topology = copy.deepcopy(_topology())
    topology["children"].insert(
        -1,
        {
            "matchers": [_matcher("Dự phòng rủi ro")],
            "presence": "OPTIONAL",
            "role": "AMBIGUOUS_PROVISION",
            "role_kind": "NONADDITIVE_CHILD",
        },
    )
    hierarchy = _hierarchy_v2(source_only_veto_roles=["AMBIGUOUS_PROVISION"])
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Dự phòng rủi ro", "-5", "-4"),
            ("Tổng cộng", "150", "130"),
        ]
    )

    _axis_value, closure = _closure(pages, topology=topology, hierarchy=hierarchy)

    receipt = next(
        record for record in closure["coverage_receipt"] if record["role"] == "AMBIGUOUS_PROVISION"
    )
    assert receipt["disposition"] == "UNRESOLVED_SOURCE_ONLY_SCHEMA_INELIGIBLE_ROLE"
    assert "AMBIGUOUS_PROVISION" not in {record["role"] for record in closure["resolved_roles"]}
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"


@pytest.mark.parametrize(
    ("label", "expected_role", "source_only"),
    [
        (
            "Chiết khấu, tái chiết khấu bằng VND",
            "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_VND",
            False,
        ),
        (
            "Chiết khấu, tái chiết khấu bằng ngoại tệ",
            "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_FOREIGN_CURRENCY",
            False,
        ),
        (
            "Chiết khấu, tái chiết khấu",
            "INTERBANK_LOAN_DISCOUNT_REDISCOUNT_AMBIGUOUS",
            True,
        ),
        ("Dự phòng rủi ro", "INTERBANK_PROVISION_AMBIGUOUS", True),
        (
            "Bằng vàng và ngoại tệ",
            "INTERBANK_LOAN_GOLD_AND_FOREIGN_CURRENCY",
            True,
        ),
    ],
)
def test_real_family3_currency_specific_roles_close_but_ambiguous_roles_veto(
    label: str,
    expected_role: str,
    source_only: bool,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]
    pages = _pages(
        [
            ("Tiền gửi tại các TCTD khác", "100", "90"),
            ("Cho vay các TCTD khác", "50", "40"),
            (label, "5", "4"),
        ]
    )
    pages[0]["lines"][0]["vietocr_text"] = "Tiền gửi và cho vay các TCTD khác"
    for ordinal, token, bbox in (
        (1, "150", [610, 15, 700, 38]),
        (2, "130", [810, 15, 900, 38]),
    ):
        pages[0]["lines"][ordinal]["vietocr_text"] = token
        pages[0]["lines"][ordinal]["numeric_recognition"]["raw_prediction"] = token
        pages[0]["lines"][ordinal]["bbox"] = bbox

    _axis_value, closure = _closure(pages, topology=topology, hierarchy=hierarchy)

    receipt = next(
        record for record in closure["coverage_receipt"] if record["role"] == expected_role
    )
    if source_only:
        assert receipt["disposition"] == "UNRESOLVED_SOURCE_ONLY_SCHEMA_INELIGIBLE_ROLE"
        assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
        assert expected_role not in {record["role"] for record in closure["resolved_roles"]}
    else:
        assert receipt["disposition"] == "NONADDITIVE_VISIBLE_SOURCE_ROLE"
        assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
        assert expected_role in {record["role"] for record in closure["resolved_roles"]}


@pytest.mark.parametrize(
    ("loan_values", "root_values", "local_components", "root_components"),
    [
        (
            ("50", "40"),
            ("145", "126"),
            ["LOAN_VND", "LOAN_FOREIGN_CURRENCY"],
            ["DEPOSIT_GROUP", "LOAN_GROUP", "LOAN_PROVISION"],
        ),
        (
            ("45", "36"),
            ("145", "126"),
            ["LOAN_VND", "LOAN_FOREIGN_CURRENCY", "LOAN_PROVISION"],
            ["DEPOSIT_GROUP", "LOAN_GROUP"],
        ),
    ],
)
def test_visible_equations_adjudicate_root_sibling_or_local_provision_once(
    loan_values: tuple[str, str],
    root_values: tuple[str, str],
    local_components: list[str],
    root_components: list[str],
) -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", *loan_values),
            ("Bằng VND", "30", "25"),
            ("Bằng ngoại tệ", "20", "15"),
            ("Dự phòng cho vay TCTD khác", "-5", "-4"),
            ("Tổng cộng", *root_values),
        ]
    )
    axis, closure = _closure(pages)

    assert axis["status"] == (
        "OCCURRENCE_ROW_AXIS_BOUND_WITH_AUTHENTICATED_EXISTING_DASHES_PROPOSAL_ONLY"
    )
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    global_by_role = {item["result_role"]: item for item in closure["equations"]["global"]}
    assert global_by_role["LOAN_GROUP"]["component_roles_present"] == local_components
    assert global_by_role["INTERBANK"]["component_roles_present"] == root_components
    provision = next(
        item for item in closure["coverage_receipt"] if item["role"] == "LOAN_PROVISION"
    )
    assert provision["disposition"] in {
        "GLOBAL_HIERARCHY_SOURCE_OCCURRENCE",
        "LOCAL_EXHAUSTIVE_COMPONENT_OCCURRENCE",
    }
    assert (
        subject.validate_accounting_scoped_hierarchical_table_closure_replay_v2(
            closure, axis, _topology(), _hierarchy()
        )
        == closure
    )


def test_repeated_role_under_same_owner_and_partial_equation_fail_closed() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "20", "15"),
            ("Bằng VND", "30", "25"),
            ("Tổng cộng", "150", "130"),
        ]
    )
    _axis_value, closure = _closure(pages)

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        reason.startswith("REPEATED_ROLE_SCOPE_IS_NOT_DISJOINT:LOAN_VND")
        for reason in closure["unresolved_reasons"]
    )
    assert any(
        reason.startswith("LOCAL_VISIBLE_RESULT_LACKS_EXHAUSTIVE_COMPONENT_SET")
        for reason in closure["unresolved_reasons"]
    )


def test_repeated_local_subtotals_are_corroborated_before_disjoint_aggregation() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "30", "25"),
            ("Bằng VND", "20", "15"),
            ("Bằng ngoại tệ", "10", "10"),
            ("Cho vay TCTD khác", "12", "10"),
            ("Bằng VND", "9", "8"),
            ("Bằng ngoại tệ", "3", "2"),
            ("Tổng cộng", "142", "125"),
        ]
    )
    _axis_value, closure = _closure(pages)

    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    loan = next(item for item in closure["resolved_roles"] if item["role"] == "LOAN_GROUP")
    assert loan["resolution_kind"] == (
        "DERIVED_EXACT_DISJOINT_OCCURRENCE_SUM_CORROBORATED_BY_COMPONENTS"
    )
    assert (
        len(
            [
                item
                for item in closure["equations"]["local"]
                if item["status"]
                == "LOCAL_VISIBLE_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS"
            ]
        )
        == 2
    )


def test_one_label_only_local_scope_can_use_exhaustive_global_derivation() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "", ""),
            ("Cho vay TCTD khác", "", ""),
            ("Bằng VND", "30", "25"),
            ("Bằng ngoại tệ", "20", "15"),
        ],
        trailing=[("150", "130")],
    )
    _axis_value, closure = _closure(pages)

    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    assert [record["status"] for record in closure["equations"]["local"]] == [
        "LOCAL_SINGLE_SCOPE_WITHOUT_VISIBLE_SUBTOTAL_DEFERRED_TO_EXHAUSTIVE_GLOBAL_EQUATION"
    ]
    loan = next(record for record in closure["resolved_roles"] if record["role"] == "LOAN_GROUP")
    assert loan["resolution_kind"] == "DERIVED_EXACT_COMPONENT_SUM"
    assert loan["component_roles"] == ["LOAN_VND", "LOAN_FOREIGN_CURRENCY"]


def test_missing_local_subtotals_cannot_authorize_cross_scope_leaf_aggregation() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "", ""),
            ("Bằng VND", "20", "15"),
            ("Bằng ngoại tệ", "10", "10"),
            ("Cho vay TCTD khác", "", ""),
            ("Bằng VND", "9", "8"),
            ("Bằng ngoại tệ", "3", "2"),
        ],
        trailing=[("142", "125")],
    )
    _axis_value, closure = _closure(pages)

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert [record["status"] for record in closure["equations"]["local"]] == [
        "LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE_VETO",
        "LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE_VETO",
    ]
    assert (
        len(
            [
                reason
                for reason in closure["unresolved_reasons"]
                if reason.startswith("LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE:LOAN_GROUP:")
            ]
        )
        == 2
    )
    assert any(
        reason.startswith("LOCAL_COMPONENT_SCOPE_LACKS_CORROBORATED_SUBTOTAL:LOAN_VND:")
        for reason in closure["unresolved_reasons"]
    )
    assert not any(
        record["role"] in {"LOAN_VND", "LOAN_FOREIGN_CURRENCY", "LOAN_GROUP", "INTERBANK"}
        for record in closure["resolved_roles"]
    )
    assert not any(
        record["resolution_kind"] == "DERIVED_EXACT_DISJOINT_OCCURRENCE_SUM"
        for record in closure["resolved_roles"]
    )


def test_real_v4_config_rejects_singleton_that_omits_visible_deposit_subtree() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]
    pages = _pages(
        [
            ("Tiền gửi tại các TCTD khác", "60", "50"),
            ("Tiền gửi không kỳ hạn", "60", "50"),
            ("Bằng VND", "60", "50"),
            ("Tiền gửi có kỳ hạn", "40", "30"),
            ("Bằng VND", "40", "30"),
            ("Cho vay các TCTD khác", "50", "40"),
            ("Bằng VND", "50", "40"),
        ],
        trailing=[("110", "90")],
    )
    pages[0]["lines"][0]["vietocr_text"] = "Tiền gửi và cho vay các TCTD khác"

    _axis_value, closure = _closure(pages, topology=topology, hierarchy=hierarchy)

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    deposit = next(
        record
        for record in closure["equations"]["global"]
        if record["result_role"] == "INTERBANK_DEPOSIT_GROUP"
    )
    assert deposit["status"] == "VISIBLE_RESULT_MISMATCH_VETO"
    assert deposit["component_roles_present"] == []
    assert (
        "VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:INTERBANK_DEPOSIT_GROUP"
        in closure["unresolved_reasons"]
    )
    assert any(
        reason.startswith("ACCOUNTING_COMPONENT_ROLE_USE_COUNT_NOT_ONE:TERM_DEPOSIT_GROUP:")
        for reason in closure["unresolved_reasons"]
    )


def test_real_v4_acb_shaped_preceding_demand_subtotal_is_not_reused_as_term_total() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]

    axis, closure = _closure(
        _acb_shaped_preceding_subtotal_pages(),
        topology=topology,
        hierarchy=hierarchy,
    )

    assert "TERM_DEPOSIT_GROUP" not in {row["role"] for row in axis["row_axis"]["rows"]}
    assert [evidence["status"] for evidence in axis["coextensive_structural_numeric_evidence"]] == [
        "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED"
    ]
    assert closure["status"] == "HIERARCHICAL_ROLE_AXIS_RESOLVED_WITHOUT_ACCOUNTING_VETO"
    resolved = {record["role"]: record for record in closure["resolved_roles"]}
    assert [
        value["number"]["coefficient"] for value in resolved["TERM_DEPOSIT_GROUP"]["values"]
    ] == [
        120,
        90,
    ]
    assert [
        value["number"]["coefficient"]
        for value in resolved["INTERBANK_DEPOSITS_AND_LOANS"]["values"]
    ] == [200, 150]
    receipt = next(
        record
        for record in closure["coverage_receipt"]
        if record["row_kind"] == "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE"
    )
    assert receipt["disposition"] == "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_ALREADY_OWNED"
    assert (
        subject.validate_accounting_scoped_hierarchical_table_closure_replay_v2(
            closure,
            axis,
            topology,
            hierarchy,
        )
        == closure
    )


def test_validator_rejects_duplicate_coextensive_receipt_after_coherent_rehash() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]
    _axis_value, closure = _closure(
        _acb_shaped_preceding_subtotal_pages(),
        topology=topology,
        hierarchy=hierarchy,
    )
    attacked = copy.deepcopy(closure)
    duplicate = copy.deepcopy(
        next(
            record
            for record in attacked["coverage_receipt"]
            if record["row_kind"] == "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE"
        )
    )
    duplicate["coverage_id"] += ":duplicate"
    attacked["coverage_receipt"].append(duplicate)
    _coherently_rehash_closure(attacked)

    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="coverage receipt drifted",
    ):
        subject._validate_result(attacked)


def test_real_v4_acb_shaped_one_unit_prior_subtotal_conflict_is_not_suppressed() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]

    axis, closure = _closure(
        _acb_shaped_preceding_subtotal_pages(demand_subtotal_current="31"),
        topology=topology,
        hierarchy=hierarchy,
    )

    assert axis["coextensive_structural_numeric_evidence"] == []
    assert next(row for row in axis["row_axis"]["rows"] if row["role"] == "TERM_DEPOSIT_GROUP")
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        reason.startswith("LOCAL_VISIBLE_RESULT_NOT_EXACT_COMPONENT_SUM:TERM_DEPOSIT_GROUP:")
        for reason in closure["unresolved_reasons"]
    )


def test_real_v4_equal_prior_and_current_scope_subtotal_is_ambiguous_veto() -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]
    pages = _acb_shaped_preceding_subtotal_pages()
    replacements = {15: "20", 16: "15", 18: "10", 19: "5", 24: "110", 25: "80"}
    for line in pages[0]["lines"]:
        if line["line_ordinal"] in replacements:
            replacement = replacements[line["line_ordinal"]]
            line["vietocr_text"] = replacement
            line["numeric_recognition"]["raw_prediction"] = replacement

    axis, closure = _closure(pages, topology=topology, hierarchy=hierarchy)

    term_row = next(row for row in axis["row_axis"]["rows"] if row["role"] == "TERM_DEPOSIT_GROUP")
    assert [value["parsed_token"]["coefficient"] for value in term_row["values"]] == [30, 20]
    assert [evidence["status"] for evidence in axis["coextensive_structural_numeric_evidence"]] == [
        "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_AMBIGUOUS_OWNERSHIP_VETO"
    ]
    assert axis["status"] == "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        reason.startswith("COEXTENSIVE_PRECEDING_NUMERIC_SOURCE_AMBIGUOUS_OWNERSHIP_VETO:")
        for reason in closure["unresolved_reasons"]
    )
    assert not any(
        record["row_kind"] == "COEXTENSIVE_PRECEDING_NUMERIC_SOURCE"
        for record in closure["coverage_receipt"]
    )
    local = next(
        record
        for record in closure["equations"]["local"]
        if record["result_role"] == "TERM_DEPOSIT_GROUP"
    )
    assert local["status"] == "LOCAL_VISIBLE_SUBTOTAL_CORROBORATED_BY_EXACT_SCOPED_COMPONENTS"


@pytest.mark.parametrize("tamper", ["EMPTY_EVIDENCE", "UNKNOWN_STATUS"])
def test_validator_rejects_malformed_ambiguous_evidence_after_coherent_rehash(
    tamper: str,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    topology = json.loads(
        (project_root / "config/families/tm-interbank-deposits-loans-topology-v4.json").read_text()
    )
    hierarchy = json.loads(
        (
            project_root / "config/families/tm-interbank-deposits-loans-evaluation-v4.json"
        ).read_text()
    )["hierarchical_closure_spec"]
    pages = _acb_shaped_preceding_subtotal_pages()
    replacements = {15: "20", 16: "15", 18: "10", 19: "5", 24: "110", 25: "80"}
    for line in pages[0]["lines"]:
        if line["line_ordinal"] in replacements:
            replacement = replacements[line["line_ordinal"]]
            line["vietocr_text"] = replacement
            line["numeric_recognition"]["raw_prediction"] = replacement
    _axis_value, closure = _closure(pages, topology=topology, hierarchy=hierarchy)
    attacked = copy.deepcopy(closure)
    if tamper == "EMPTY_EVIDENCE":
        attacked["coextensive_structural_numeric_evidence"] = [{}]
    else:
        attacked["coextensive_structural_numeric_evidence"][0]["status"] = "GARBAGE"
    _coherently_rehash_closure(attacked)

    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error,
        match="coextensive source receipt drifted",
    ):
        subject._validate_result(attacked)


def test_partial_and_unbound_visible_numeric_occurrences_each_receive_one_veto_receipt() -> None:
    topology = _topology()
    topology["children"].append(
        {
            "matchers": [_matcher("Khoản mục ngoài phương trình")],
            "presence": "OPTIONAL",
            "role": "UNBOUND_ADDITIVE_ROLE",
            "role_kind": "ADDITIVE_CHILD",
        }
    )
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "20", ""),
            ("Khoản mục ngoài phương trình", "7", "6"),
            ("Tổng cộng", "150", "130"),
        ]
    )
    _axis_value, closure = _closure(pages, topology=topology)

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    dispositions = {item["role"]: item["disposition"] for item in closure["coverage_receipt"]}
    assert dispositions["LOAN_VND"] == "UNRESOLVED_PARTIAL_ROLE_NUMERIC_OCCURRENCE"
    assert dispositions["UNBOUND_ADDITIVE_ROLE"] == "UNBOUND_VISIBLE_ACCOUNTING_OCCURRENCE"
    assert (
        len(
            {
                item["coverage_id"]
                for item in closure["coverage_receipt"]
                if item["role"] in {"LOAN_VND", "UNBOUND_ADDITIVE_ROLE"}
            }
        )
        == 2
    )


def test_partial_local_subtotal_without_children_is_one_typed_veto_not_an_exception() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", ""),
            ("Tổng cộng", "150", "130"),
        ]
    )

    axis, closure = _closure(pages)

    assert axis["status"] == "UNRESOLVED_OCCURRENCE_ROW_AXIS_OR_EXISTING_DASH_EVIDENCE"
    local = next(
        record for record in closure["equations"]["local"] if record["result_role"] == "LOAN_GROUP"
    )
    assert local["status"] == "LOCAL_SUBTOTAL_RESULT_PARTIAL_VALUE_LANES_VETO"
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        reason.startswith("LOCAL_SUBTOTAL_RESULT_PARTIAL_VALUE_LANES:LOAN_GROUP:")
        for reason in closure["unresolved_reasons"]
    )
    receipt = next(
        record for record in closure["coverage_receipt"] if record["role"] == "LOAN_GROUP"
    )
    assert receipt["disposition"] == "UNRESOLVED_PARTIAL_ROLE_NUMERIC_OCCURRENCE"


def test_empty_local_subtotal_without_children_is_typed_instead_of_raising() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "", ""),
            ("Tổng cộng", "150", "130"),
        ]
    )

    _axis_value, closure = _closure(pages)

    local = next(
        record for record in closure["equations"]["local"] if record["result_role"] == "LOAN_GROUP"
    )
    assert local["status"] == "LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE_VETO"
    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    assert any(
        reason.startswith("LOCAL_SUBTOTAL_RESULT_MISSING_OR_INCOMPLETE:LOAN_GROUP:")
        for reason in closure["unresolved_reasons"]
    )


def test_printed_residual_two_is_persisted_and_never_backsolved() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "50000000", "50000000"),
            ("Cho vay TCTD khác", "22305188", "22305188"),
        ],
        trailing=[("72305188", "72305186")],
    )
    _axis_value, closure = _closure(pages)

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    root = next(
        item for item in closure["equations"]["global"] if item["result_role"] == "INTERBANK"
    )
    assert root["status"] == "TRAILING_NUMERIC_CHALLENGER_VETO"
    evidence = root["residual_evidence"][0]
    assert evidence["convention"] == "PRINTED_RESULT_MINUS_EXHAUSTIVE_COMPONENT_SUM"
    assert [lane["residual_number"]["coefficient"] for lane in evidence["lanes"]] == [
        0,
        -2,
    ]
    assert "INTERBANK" not in {item["role"] for item in closure["resolved_roles"]}
    assert all(
        item["resolution_kind"] != "DERIVED_EXACT_COMPONENT_SUM" or item["role"] != "INTERBANK"
        for item in closure["resolved_roles"]
    )
    mapping = mapping_v1._trial(
        {
            "additive_closure": closure,
            "column_context": None,
            "document_ordinal": 18,
            "evidence_status": "UNRESOLVED_EVIDENCE_GATES",
            "private_provenance": {"scope": "CONSOLIDATED"},
            "row_axis": None,
            "source_pdf_ref": {
                "path": "fixture/trial-18.pdf",
                "sha256": "2" * 64,
                "size_bytes": 2,
            },
            "unresolved_reasons": closure["unresolved_reasons"],
        },
        {},
        {},
        [],
        schema_period_type="SNAPSHOT",
        schema_binding_spec={},
    )
    assert mapping["mapping_status"] == "UNRESOLVED"
    assert mapping["mappings"] == []
    assert root["residual_evidence"][0]["lanes"][1]["residual_number"]["coefficient"] == -2


@pytest.mark.parametrize(
    ("trailing", "expected_disposition"),
    [
        (
            [("150", "130"), ("150", "130")],
            "UNRESOLVED_UNSELECTED_COMPLETE_TRAILING_NUMERIC_CHALLENGER",
        ),
        (
            [(None, "21")],
            "UNRESOLVED_PARTIAL_TRAILING_NUMERIC_CHALLENGER",
        ),
    ],
)
def test_duplicate_total_and_numeric_page_footer_are_typed_trailing_challengers(
    trailing: list[tuple[str | None, str | None]], expected_disposition: str
) -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
        ],
        trailing=trailing,
    )
    _axis_value, closure = _closure(pages)

    assert closure["status"] == "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    trailing_receipts = [
        item for item in closure["coverage_receipt"] if item["row_kind"] == "TRAILING_VALUE_ROW"
    ]
    assert trailing_receipts
    assert {item["disposition"] for item in trailing_receipts} == {expected_disposition}


def test_closure_coherent_rehash_tamper_is_rejected_by_exact_replay() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Tổng cộng", "150", "130"),
        ]
    )
    axis, closure = _closure(pages)
    attacked = copy.deepcopy(closure)
    attacked["unresolved_reasons"] = ["FORGED_REASON"]
    attacked["status"] = "UNRESOLVED_HIERARCHICAL_ACCOUNTING_VETO"
    attacked["metrics"]["accounting_veto_count"] = 1
    material = copy.deepcopy(attacked)
    material.pop("closure_id")
    attacked["closure_id"] = "ashtcv2:closure:" + canonical_json_sha256_v1(material)

    with pytest.raises(
        subject.AccountingScopedHierarchicalTableClosureV2Error, match="replay exactly"
    ):
        subject.validate_accounting_scoped_hierarchical_table_closure_replay_v2(
            attacked, axis, _topology(), _hierarchy()
        )


def test_scoped_closure_contract_maps_through_existing_schema_mapper_without_adapter() -> None:
    pages = _pages(
        [
            ("Tiền gửi tại TCTD khác", "100", "90"),
            ("Cho vay TCTD khác", "50", "40"),
            ("Bằng VND", "30", "25"),
            ("Bằng ngoại tệ", "20", "15"),
            ("Dự phòng cho vay TCTD khác", "-5", "-4"),
            ("Tổng cộng", "145", "126"),
        ]
    )
    axis, closure = _closure(pages)
    nodes, _schema_ref = mapping_v1._schema_graph(Path(__file__).resolve().parents[2])
    report_norm_ids = {
        "DEPOSIT_GROUP": 576,
        "LOAN_GROUP": 585,
        "LOAN_VND": 586,
        "LOAN_FOREIGN_CURRENCY": 588,
        "LOAN_PROVISION": 590,
    }
    binding = {
        "family_id": "INTERBANK",
        "family_report_norm_id": 575,
        "format_version": mapping_v1.SPEC_FORMAT_VERSION_V3,
        "ignored_roles": ["EXPLICIT_FAMILY_TOTAL"],
        "role_bindings": [
            {"report_norm_id": report_norm_id, "role": role}
            for role, report_norm_id in report_norm_ids.items()
        ],
    }
    context = {
        "period_axis": [
            {"column_ordinal": 0, "resolved_period": "31/12/2025"},
            {"column_ordinal": 1, "resolved_period": "31/12/2024"},
        ],
        "period_semantics": "BALANCE_COMPARATIVE",
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
    }
    trial = {
        "additive_closure": closure,
        "column_context": context,
        "document_ordinal": 1,
        "evidence_status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
        "private_provenance": {"scope": "CONSOLIDATED"},
        "row_axis": axis["row_axis"],
        "source_pdf_ref": {"path": "fixture/source.pdf", "sha256": "1" * 64, "size_bytes": 1},
        "unresolved_reasons": [],
    }

    result = mapping_v1._trial(
        trial,
        nodes[575],
        {role: nodes[report_norm_id] for role, report_norm_id in report_norm_ids.items()},
        [],
        schema_period_type="SNAPSHOT",
        schema_binding_spec=binding,
    )

    assert result["mapping_status"] == "VERIFIED_BY_CODEX"
    assert [item["report_norm_id"] for item in result["mappings"]] == [
        575,
        576,
        585,
        586,
        588,
        590,
    ]
