from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from bctc_ai.mapping.loan_maturity_bounded_schema_v1 import (
    LoanMaturityBoundedSchemaV1Error,
    build_loan_maturity_bounded_schema_projection_v1,
    validate_loan_maturity_bounded_schema_projection_replay_v1,
    validate_loan_maturity_bounded_schema_projection_v1,
)

_NAMES = {
    716: "Cho vay khách hàng",
    752: "Phân tích dư nợ theo thời gian đáo hạn",
    753: "+ Ngắn hạn",
    754: "+ Trung hạn",
    755: "+ Dài hạn",
    5747: "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
    1944: "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
}
_PARENTS = {716: 560, 752: 716, 753: 752, 754: 752, 755: 752, 5747: 752, 1944: None}
_PATHS = {
    716: (560, 716),
    752: (560, 716, 752),
    753: (560, 716, 752, 753),
    754: (560, 716, 752, 754),
    755: (560, 716, 752, 755),
    5747: (560, 716, 752, 5747),
    1944: (1944,),
}


def _fixtures() -> tuple[dict[int, SimpleNamespace], dict[int, SimpleNamespace]]:
    schema = {}
    contexts = {}
    for index, identifier in enumerate(_NAMES):
        eligible = identifier != 1944
        schema[identifier] = SimpleNamespace(
            allowed_period_type=["SNAPSHOT", "DURATION"],
            allowed_sign=["POSITIVE", "NEGATIVE", "ZERO"],
            canonical_name=_NAMES[identifier],
            children=[],
            display_order=100 + index,
            parent_id=_PARENTS[identifier],
            schema_id=identifier,
            scope=["SEPARATE", "CONSOLIDATED"],
            statement_type="TM",
        )
        contexts[identifier] = SimpleNamespace(
            ancestor_path=_PATHS[identifier],
            canonical_name=_NAMES[identifier],
            context_status="RESOLVED" if eligible else "UNRESOLVED_ORPHAN",
            derived_hierarchy_level={716: 1, 752: 2}.get(identifier, 3 if eligible else None),
            mapping_eligible=eligible,
            note_family_root_id=716 if eligible else None,
            parent_report_norm_id=_PARENTS[identifier],
            report_norm_id=identifier,
            section="BALANCE_SHEET_NOTES" if eligible else None,
            section_root_id=560 if eligible else None,
            statement_type="TM",
        )
    schema[716].children = [752]
    schema[752].children = [753, 754, 755, 5747]
    return schema, contexts


def test_projection_is_exact_append_stable_and_replayable() -> None:
    schema, contexts = _fixtures()
    first = build_loan_maturity_bounded_schema_projection_v1(schema, contexts)
    assert [item["report_norm_id"] for item in first["mapped_roles"]] == [
        753,
        754,
        755,
        5747,
    ]
    assert first["owner_context"]["disposition"] == "OWNER_CONTEXT_ONLY_NOT_EMITTED"
    assert first["family_context"]["disposition"] == "FAMILY_CONTEXT_ONLY_NOT_EMITTED"
    assert first["accounting_population_policy"]["mapped_parent_report_norm_ids"] == []
    assert validate_loan_maturity_bounded_schema_projection_v1(first) == first
    assert (
        validate_loan_maturity_bounded_schema_projection_replay_v1(first, schema, contexts) == first
    )

    for node in schema.values():
        node.display_order += 10_000
    schema[9001] = SimpleNamespace(display_order=1)
    contexts[9001] = SimpleNamespace(mapping_eligible=True)
    second = build_loan_maturity_bounded_schema_projection_v1(schema, contexts)
    assert second["projection_id"] == first["projection_id"]


def test_unclassified_ineligible_child_does_not_enter_identity() -> None:
    schema, contexts = _fixtures()
    expected = build_loan_maturity_bounded_schema_projection_v1(schema, contexts)
    schema[752].children.append(9002)
    contexts[9002] = SimpleNamespace(mapping_eligible=False)
    actual = build_loan_maturity_bounded_schema_projection_v1(schema, contexts)
    assert actual["projection_id"] == expected["projection_id"]


def test_unclassified_mapping_eligible_child_fails_closed() -> None:
    schema, contexts = _fixtures()
    schema[752].children.append(9003)
    contexts[9003] = SimpleNamespace(mapping_eligible=True)
    with pytest.raises(LoanMaturityBoundedSchemaV1Error, match="unclassified"):
        build_loan_maturity_bounded_schema_projection_v1(schema, contexts)


@pytest.mark.parametrize(
    ("identifier", "field", "value"),
    [
        (753, "canonical_name", "+ Ngắn"),
        (754, "parent_id", 716),
        (755, "scope", ["CONSOLIDATED"]),
        (5747, "allowed_sign", ["POSITIVE", "ZERO"]),
    ],
)
def test_material_target_schema_drift_fails_closed(
    identifier: int, field: str, value: object
) -> None:
    schema, contexts = _fixtures()
    setattr(schema[identifier], field, value)
    with pytest.raises(LoanMaturityBoundedSchemaV1Error, match="drifted"):
        build_loan_maturity_bounded_schema_projection_v1(schema, contexts)


def test_material_context_and_projection_tamper_fail_closed() -> None:
    schema, contexts = _fixtures()
    contexts[753].mapping_eligible = False
    with pytest.raises(LoanMaturityBoundedSchemaV1Error, match="context drifted"):
        build_loan_maturity_bounded_schema_projection_v1(schema, contexts)

    schema, contexts = _fixtures()
    result = build_loan_maturity_bounded_schema_projection_v1(schema, contexts)
    tampered = copy.deepcopy(result)
    tampered["mapped_roles"][0]["canonical_name"] = "tampered"
    with pytest.raises(LoanMaturityBoundedSchemaV1Error, match="identity"):
        validate_loan_maturity_bounded_schema_projection_v1(tampered)
