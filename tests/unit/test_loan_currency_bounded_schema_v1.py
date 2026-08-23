from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from bctc_ai.mapping.loan_currency_bounded_schema_v1 import (
    LoanCurrencyBoundedSchemaV1Error,
    build_loan_currency_bounded_schema_projection_v1,
    validate_loan_currency_bounded_schema_projection_replay_v1,
    validate_loan_currency_bounded_schema_projection_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_NAMES = {
    716: "Cho vay khách hàng",
    756: "Phân tích theo loại hình tiền tệ",
    757: "+ Cho vay bằng đồng Việt Nam",
    758: "+ Cho vay bằng ngoại tệ và vàng",
}
_PARENTS = {716: 560, 756: 716, 757: 756, 758: 756}
_PATHS = {
    716: (560, 716),
    756: (560, 716, 756),
    757: (560, 716, 756, 757),
    758: (560, 716, 756, 758),
}


def _fixtures() -> tuple[dict[int, SimpleNamespace], dict[int, SimpleNamespace]]:
    schema = {}
    contexts = {}
    for index, identifier in enumerate(_NAMES):
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
            context_status="RESOLVED",
            derived_hierarchy_level={716: 1, 756: 2}.get(identifier, 3),
            mapping_eligible=True,
            note_family_root_id=716,
            parent_report_norm_id=_PARENTS[identifier],
            report_norm_id=identifier,
            section="BALANCE_SHEET_NOTES",
            section_root_id=560,
            statement_type="TM",
        )
    schema[716].children = [756]
    schema[756].children = [757, 758]
    return schema, contexts


def test_projection_is_exact_append_stable_and_replayable() -> None:
    schema, contexts = _fixtures()
    first = build_loan_currency_bounded_schema_projection_v1(schema, contexts)
    assert [item["report_norm_id"] for item in first["mapped_roles"]] == [757, 758]
    assert first["owner_context"]["disposition"] == "OWNER_CONTEXT_ONLY_NOT_EMITTED"
    assert first["family_context"]["disposition"] == "FAMILY_CONTEXT_ONLY_NOT_EMITTED"
    assert first["accounting_population_policy"]["mapped_parent_report_norm_ids"] == []
    assert validate_loan_currency_bounded_schema_projection_v1(first) == first
    assert (
        validate_loan_currency_bounded_schema_projection_replay_v1(first, schema, contexts) == first
    )

    for node in schema.values():
        node.display_order += 10_000
    schema[9001] = SimpleNamespace(display_order=1)
    contexts[9001] = SimpleNamespace(mapping_eligible=True)
    second = build_loan_currency_bounded_schema_projection_v1(schema, contexts)
    assert second["projection_id"] == first["projection_id"]


def test_unclassified_ineligible_append_is_ignored_but_eligible_child_fails_closed() -> None:
    schema, contexts = _fixtures()
    expected = build_loan_currency_bounded_schema_projection_v1(schema, contexts)
    schema[756].children.append(9002)
    contexts[9002] = SimpleNamespace(mapping_eligible=False)
    actual = build_loan_currency_bounded_schema_projection_v1(schema, contexts)
    assert actual["projection_id"] == expected["projection_id"]

    schema[756].children.append(9003)
    contexts[9003] = SimpleNamespace(mapping_eligible=True)
    with pytest.raises(LoanCurrencyBoundedSchemaV1Error, match="unclassified"):
        build_loan_currency_bounded_schema_projection_v1(schema, contexts)


@pytest.mark.parametrize(
    ("identifier", "field", "value"),
    [
        (756, "canonical_name", "Theo tiền tệ"),
        (757, "parent_id", 716),
        (758, "scope", ["CONSOLIDATED"]),
        (758, "allowed_sign", ["POSITIVE", "ZERO"]),
    ],
)
def test_material_schema_drift_fails_closed(identifier: int, field: str, value: object) -> None:
    schema, contexts = _fixtures()
    setattr(schema[identifier], field, value)
    with pytest.raises(LoanCurrencyBoundedSchemaV1Error, match="drifted"):
        build_loan_currency_bounded_schema_projection_v1(schema, contexts)


def test_context_and_rehashed_projection_tamper_fail_closed() -> None:
    schema, contexts = _fixtures()
    contexts[757].mapping_eligible = False
    with pytest.raises(LoanCurrencyBoundedSchemaV1Error, match="drifted"):
        build_loan_currency_bounded_schema_projection_v1(schema, contexts)

    schema, contexts = _fixtures()
    result = build_loan_currency_bounded_schema_projection_v1(schema, contexts)
    tampered = copy.deepcopy(result)
    tampered["mapped_roles"][0]["canonical_name"] = "tampered"
    material = copy.deepcopy(tampered)
    material.pop("projection_id")
    tampered["projection_id"] = "lcbspv1:projection:" + canonical_json_sha256_v1(material)
    with pytest.raises(LoanCurrencyBoundedSchemaV1Error, match="contract"):
        validate_loan_currency_bounded_schema_projection_v1(tampered)
