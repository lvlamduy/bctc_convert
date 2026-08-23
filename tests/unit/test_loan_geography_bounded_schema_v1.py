from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest

from bctc_ai.mapping.loan_geography_bounded_schema_v1 import (
    LoanGeographyBoundedSchemaV1Error,
    build_loan_geography_bounded_schema_projection_v1,
    validate_loan_geography_bounded_schema_projection_replay_v1,
    validate_loan_geography_bounded_schema_projection_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_NAMES = {
    716: "Cho vay khách hàng",
    759: "Phân tích theo khu vực địa lý",
    5752: "+ Trong nước",
    760: "+ Thành phố Hồ Chí Minh",
    761: "+ Đồng bằng sông Cửu Long",
    762: "+ Miền Trung và Tây nguyên",
    763: "+ Miền Bắc",
    764: "+ Miền Đông nam bộ",
    765: "+ Nước ngoài",
}
_PARENTS = {
    716: 560,
    759: 716,
    5752: 759,
    760: 5752,
    761: 5752,
    762: 5752,
    763: 5752,
    764: 5752,
    765: 759,
}
_PATHS = {
    716: (560, 716),
    759: (560, 716, 759),
    5752: (560, 716, 759, 5752),
    760: (560, 716, 759, 5752, 760),
    761: (560, 716, 759, 5752, 761),
    762: (560, 716, 759, 5752, 762),
    763: (560, 716, 759, 5752, 763),
    764: (560, 716, 759, 5752, 764),
    765: (560, 716, 759, 765),
}


def _fixtures() -> tuple[dict[int, SimpleNamespace], dict[int, SimpleNamespace]]:
    schema: dict[int, SimpleNamespace] = {}
    contexts: dict[int, SimpleNamespace] = {}
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
            derived_hierarchy_level={716: 1, 759: 2, 5752: 3, 765: 3}.get(identifier, 4),
            mapping_eligible=True,
            note_family_root_id=716,
            parent_report_norm_id=_PARENTS[identifier],
            report_norm_id=identifier,
            section="BALANCE_SHEET_NOTES",
            section_root_id=560,
            statement_type="TM",
        )
    schema[716].children = [759]
    schema[759].children = [5752, 765]
    schema[5752].children = [760, 761, 762, 763, 764]
    return schema, contexts


def _append_child(
    schema: dict[int, SimpleNamespace],
    contexts: dict[int, SimpleNamespace],
    *,
    parent_id: int,
    identifier: int,
    eligible: bool,
) -> None:
    schema[parent_id].children.append(identifier)
    schema[identifier] = SimpleNamespace(schema_id=identifier)
    contexts[identifier] = SimpleNamespace(report_norm_id=identifier, mapping_eligible=eligible)


def test_projection_is_append_stable_exact_and_replayable() -> None:
    schema, contexts = _fixtures()
    first = build_loan_geography_bounded_schema_projection_v1(schema, contexts)
    assert [item["report_norm_id"] for item in first["mapped_roles"]] == [5752, 765]
    assert [item["report_norm_id"] for item in first["known_nested_domestic_descendants"]] == [
        760,
        761,
        762,
        763,
        764,
    ]
    assert first["accounting_population_policy"]["mapped_parent_report_norm_ids"] == []
    assert first["family_context"]["disposition"] == "FAMILY_CONTEXT_ONLY_NOT_EMITTED"
    assert validate_loan_geography_bounded_schema_projection_v1(first) == first
    assert (
        validate_loan_geography_bounded_schema_projection_replay_v1(first, schema, contexts)
        == first
    )

    for node in schema.values():
        node.display_order = getattr(node, "display_order", 0) + 10_000
    schema[9001] = SimpleNamespace(schema_id=9001, display_order=1)
    contexts[9001] = SimpleNamespace(report_norm_id=9001, mapping_eligible=True)
    second = build_loan_geography_bounded_schema_projection_v1(schema, contexts)
    assert second["projection_id"] == first["projection_id"]


@pytest.mark.parametrize("parent_id", [759, 5752, 765])
def test_unclassified_eligible_descendant_fails_closed(parent_id: int) -> None:
    schema, contexts = _fixtures()
    _append_child(schema, contexts, parent_id=parent_id, identifier=9002, eligible=False)
    expected = build_loan_geography_bounded_schema_projection_v1(schema, contexts)
    assert expected["mapped_roles"][0]["report_norm_id"] == 5752

    _append_child(schema, contexts, parent_id=parent_id, identifier=9003, eligible=True)
    with pytest.raises(LoanGeographyBoundedSchemaV1Error, match="unclassified"):
        build_loan_geography_bounded_schema_projection_v1(schema, contexts)


def test_missing_or_moved_family_edges_fail_closed() -> None:
    schema, contexts = _fixtures()
    schema[759].children.remove(765)
    with pytest.raises(LoanGeographyBoundedSchemaV1Error, match="lacks"):
        build_loan_geography_bounded_schema_projection_v1(schema, contexts)

    schema, contexts = _fixtures()
    schema[5752].children.remove(764)
    with pytest.raises(LoanGeographyBoundedSchemaV1Error, match="lacks"):
        build_loan_geography_bounded_schema_projection_v1(schema, contexts)

    schema, contexts = _fixtures()
    schema[759].parent_id = 560
    with pytest.raises(LoanGeographyBoundedSchemaV1Error, match="drifted"):
        build_loan_geography_bounded_schema_projection_v1(schema, contexts)


@pytest.mark.parametrize(
    ("identifier", "field", "value"),
    [
        (759, "canonical_name", "Phân tích địa lý"),
        (5752, "parent_id", 716),
        (760, "scope", ["CONSOLIDATED"]),
        (765, "allowed_sign", ["POSITIVE", "ZERO"]),
    ],
)
def test_material_schema_drift_fails_closed(identifier: int, field: str, value: object) -> None:
    schema, contexts = _fixtures()
    setattr(schema[identifier], field, value)
    with pytest.raises(LoanGeographyBoundedSchemaV1Error, match="drifted"):
        build_loan_geography_bounded_schema_projection_v1(schema, contexts)


def test_context_eligibility_and_coordinated_rehash_tamper_fail_closed() -> None:
    schema, contexts = _fixtures()
    contexts[763].mapping_eligible = False
    with pytest.raises(LoanGeographyBoundedSchemaV1Error, match="drifted"):
        build_loan_geography_bounded_schema_projection_v1(schema, contexts)

    schema, contexts = _fixtures()
    result = build_loan_geography_bounded_schema_projection_v1(schema, contexts)
    tampered = copy.deepcopy(result)
    tampered["mapped_roles"][0]["report_norm_id"] = 759
    material = copy.deepcopy(tampered)
    material.pop("projection_id")
    tampered["projection_id"] = "lgbspv1:projection:" + canonical_json_sha256_v1(material)
    with pytest.raises(LoanGeographyBoundedSchemaV1Error, match="contract"):
        validate_loan_geography_bounded_schema_projection_v1(tampered)


def test_mapping_keys_must_match_embedded_exact_identities() -> None:
    schema, contexts = _fixtures()
    schema[5752].schema_id = 765
    with pytest.raises(LoanGeographyBoundedSchemaV1Error, match="identities"):
        build_loan_geography_bounded_schema_projection_v1(schema, contexts)
