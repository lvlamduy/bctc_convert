from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from bctc_ai.mapping.loan_enterprise_bounded_schema_v1 import (
    LoanEnterpriseBoundedSchemaV1Error,
    build_live_loan_enterprise_bounded_schema_projection_v1,
    build_loan_enterprise_bounded_schema_projection_v1,
    validate_loan_enterprise_bounded_schema_projection_replay_v1,
    validate_loan_enterprise_bounded_schema_projection_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]
_LIVE_PROJECTION_ID = (
    "lebspv1:projection:af352038c11dacfa3baef5116b296184a0d80a7edd781868bbd028e7ca17c228"
)
_CHILD_IDS = (
    *range(767, 777),
    6074,
    *range(777, 783),
    5748,
)
_NAMES = {
    716: "Cho vay khách hàng",
    727: "Phân tích theo ngành nghề kinh doanh",
    766: "Phân tích theo loại hình doanh nghiệp",
    767: "- Doanh nghiệp nhà nước",
    768: "- Công ty TNHH",
    769: "+ Công ty TNHH MTV vốn nhà nước 100%",
    770: "Công ty TNHH MTV (hoặc trên MTV) vốn nhà nước trên 50%",
    771: "+ Công ty TNHH khác",
    772: "- Công ty cổ phần có vốn nhà nước trên 50%",
    773: "- Công ty cổ phần khác",
    774: "- Doanh nghiệp tư nhân",
    775: "- Công ty CP, TNHH, DN tư nhân",
    776: "- Hợp tác xã và liên hợp tác xã",
    777: "- Công ty liên doanh, hợp doanh",
    778: "- Công ty hợp danh",
    779: "- Công ty vốn nước ngoài",
    780: "- Hộ kinh doanh, cá nhân",
    781: "- Dịch vụ hành chính sự nghiệp, Đảng, đoàn thể, hiệp hội",
    782: "- Khác",
    5748: "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
    6074: "+ Hợp tác xã và công ty tư nhân",
    6058: "+ Cho vay tại Chi nhánh và ngân hàng con nước ngoài",
    1055: "Tiền gửi của khách hàng",
    1075: "Theo loại hình doanh nghiệp",
    1259: "IV. MỘT SỐ THÔNG TIN KHÁC",
    5750: "Giao dịch với các bên liên quan",
    5751: "Giao dịch tiền gửi tại MB",
}
_PARENTS = {
    716: 560,
    727: 716,
    766: 716,
    **{identifier: 766 for identifier in _CHILD_IDS},
    6058: 727,
    1055: 560,
    1075: 1055,
    1259: None,
    5750: 1259,
    5751: 5750,
}


def _context_fields(identifier: int) -> tuple[tuple[int, ...], int, str, int, int | None]:
    if identifier == 716:
        return (560, 716), 1, "BALANCE_SHEET_NOTES", 560, 716
    if identifier in {727, 766}:
        return (560, 716, identifier), 2, "BALANCE_SHEET_NOTES", 560, 716
    if identifier in _CHILD_IDS:
        return (560, 716, 766, identifier), 3, "BALANCE_SHEET_NOTES", 560, 716
    if identifier == 6058:
        return (560, 716, 727, 6058), 3, "BALANCE_SHEET_NOTES", 560, 716
    if identifier == 1055:
        return (560, 1055), 1, "BALANCE_SHEET_NOTES", 560, 1055
    if identifier == 1075:
        return (560, 1055, 1075), 2, "BALANCE_SHEET_NOTES", 560, 1055
    if identifier == 1259:
        return (1259,), 0, "OTHER_QUANTITATIVE_NOTES", 1259, None
    if identifier == 5750:
        return (1259, 5750), 1, "OTHER_QUANTITATIVE_NOTES", 1259, 5750
    return (1259, 5750, 5751), 2, "OTHER_QUANTITATIVE_NOTES", 1259, 5750


def _fixtures() -> tuple[dict[int, SimpleNamespace], dict[int, SimpleNamespace]]:
    schema: dict[int, SimpleNamespace] = {
        560: SimpleNamespace(schema_id=560, children=[716, 1055], display_order=0)
    }
    contexts: dict[int, SimpleNamespace] = {
        560: SimpleNamespace(report_norm_id=560, mapping_eligible=True)
    }
    for index, identifier in enumerate(_NAMES):
        path, level, section, section_root, family_root = _context_fields(identifier)
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
            ancestor_path=path,
            canonical_name=_NAMES[identifier],
            context_status="RESOLVED",
            derived_hierarchy_level=level,
            mapping_eligible=True,
            note_family_root_id=family_root,
            parent_report_norm_id=_PARENTS[identifier],
            report_norm_id=identifier,
            section=section,
            section_root_id=section_root,
            statement_type="TM",
        )
    schema[716].children = [727, 766]
    schema[727].children = [6058]
    schema[766].children = list(_CHILD_IDS)
    schema[1055].children = [1075]
    schema[1259].children = [5750]
    schema[5750].children = [5751]
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
    schema[identifier] = SimpleNamespace(schema_id=identifier, children=[], display_order=1)
    contexts[identifier] = SimpleNamespace(report_norm_id=identifier, mapping_eligible=eligible)


def test_projection_closes_exact_18_leaves_and_preserves_source_only_ambiguity() -> None:
    schema, contexts = _fixtures()
    result = build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)

    assert [item["report_norm_id"] for item in result["mapped_leaves"]] == list(_CHILD_IDS)
    assert all(
        item["presence"] == "OPTIONAL_WHEN_EXACT_SOURCE_SEMANTICS_PROVEN"
        for item in result["mapped_leaves"]
    )
    assert result["emission_policy"] == {
        "ambiguous_source_disposition": "RETAIN_SOURCE_ONLY_WITHOUT_FORCED_SCHEMA_ID",
        "cross_family_industry_context_report_norm_ids": [727, 6058],
        "deposit_analogue_context_report_norm_ids": [1055, 1075],
        "emittable_exact_leaf_report_norm_ids": list(_CHILD_IDS),
        "family_parent_report_norm_id": 766,
        "mapped_parent_report_norm_ids": [],
        "related_party_context_report_norm_ids": [1259, 5750, 5751],
        "required_per_document_report_norm_ids": [],
        "source_customer_loan_total_report_norm_id": None,
    }
    assert 6058 not in result["emission_policy"]["emittable_exact_leaf_report_norm_ids"]
    assert [
        item["report_norm_id"] for item in result["excluded_context"]["cross_family_industry"]
    ] == [727, 6058]
    assert [
        item["report_norm_id"] for item in result["excluded_context"]["customer_deposit_analogue"]
    ] == [1055, 1075]
    assert [item["report_norm_id"] for item in result["excluded_context"]["related_party"]] == [
        1259,
        5750,
        5751,
    ]
    assert validate_loan_enterprise_bounded_schema_projection_v1(result) == result
    assert (
        validate_loan_enterprise_bounded_schema_projection_replay_v1(result, schema, contexts)
        == result
    )


def test_live_projection_matches_frozen_bounded_identity_without_corpus_or_auth() -> None:
    result = build_live_loan_enterprise_bounded_schema_projection_v1(_ROOT)

    assert result["projection_id"] == _LIVE_PROJECTION_ID
    assert [item["report_norm_id"] for item in result["mapped_leaves"]] == list(_CHILD_IDS)
    assert result["owner_context"]["report_norm_id"] == 716
    assert result["family_context"]["report_norm_id"] == 766


def test_unrelated_and_explicitly_ineligible_appends_are_identity_stable() -> None:
    schema, contexts = _fixtures()
    expected = build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)

    for node in schema.values():
        node.display_order = getattr(node, "display_order", 0) + 100_000
    _append_child(schema, contexts, parent_id=716, identifier=9001, eligible=True)
    _append_child(schema, contexts, parent_id=766, identifier=9002, eligible=False)
    _append_child(schema, contexts, parent_id=767, identifier=9003, eligible=False)
    schema[9100] = SimpleNamespace(schema_id=9100, children=[], display_order=1)
    contexts[9100] = SimpleNamespace(report_norm_id=9100, mapping_eligible=True)

    actual = build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)
    assert actual["projection_id"] == expected["projection_id"]


def test_new_eligible_direct_or_nested_child_fails_closed() -> None:
    schema, contexts = _fixtures()
    _append_child(schema, contexts, parent_id=766, identifier=9004, eligible=True)
    with pytest.raises(LoanEnterpriseBoundedSchemaV1Error, match="eligible child population"):
        build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)

    schema, contexts = _fixtures()
    _append_child(schema, contexts, parent_id=767, identifier=9005, eligible=True)
    with pytest.raises(LoanEnterpriseBoundedSchemaV1Error, match="eligible child population"):
        build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)


@pytest.mark.parametrize("removed_id", _CHILD_IDS)
def test_removing_any_one_of_the_18_eligible_children_fails_closed(removed_id: int) -> None:
    schema, contexts = _fixtures()
    schema[766].children.remove(removed_id)

    with pytest.raises(LoanEnterpriseBoundedSchemaV1Error, match="missing"):
        build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)


@pytest.mark.parametrize(
    ("identifier", "new_parent"),
    (
        (766, 560),
        (767, 716),
        (6074, 727),
        (5748, 727),
        (6058, 766),
        (1075, 716),
        (5750, 560),
        (5751, 1259),
    ),
)
def test_schema_parent_drift_across_family_and_lookalike_branches_fails_closed(
    identifier: int, new_parent: int
) -> None:
    schema, contexts = _fixtures()
    schema[identifier].parent_id = new_parent

    with pytest.raises(LoanEnterpriseBoundedSchemaV1Error, match="drifted"):
        build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)


def test_context_parent_and_required_edge_drift_fail_closed() -> None:
    schema, contexts = _fixtures()
    contexts[6058].parent_report_norm_id = 766
    with pytest.raises(LoanEnterpriseBoundedSchemaV1Error, match="drifted"):
        build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)

    schema, contexts = _fixtures()
    schema[716].children.remove(766)
    with pytest.raises(LoanEnterpriseBoundedSchemaV1Error, match="lacks required child"):
        build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)


@pytest.mark.parametrize(
    ("identifier", "field", "value"),
    (
        (766, "canonical_name", "Phân tích doanh nghiệp"),
        (770, "scope", ["CONSOLIDATED"]),
        (782, "allowed_sign", ["POSITIVE", "ZERO"]),
        (1075, "canonical_name", "Theo khách hàng"),
        (5750, "statement_type", "CDKT"),
    ),
)
def test_material_family_or_lookalike_identity_drift_fails_closed(
    identifier: int, field: str, value: object
) -> None:
    schema, contexts = _fixtures()
    setattr(schema[identifier], field, value)

    with pytest.raises(LoanEnterpriseBoundedSchemaV1Error, match="drifted"):
        build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)


def test_mapping_eligibility_and_mapping_key_identity_falsifiers_fail_closed() -> None:
    schema, contexts = _fixtures()
    contexts[6074].mapping_eligible = False
    with pytest.raises(LoanEnterpriseBoundedSchemaV1Error, match="eligible child population"):
        build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)

    schema, contexts = _fixtures()
    schema[6074].schema_id = 5748
    with pytest.raises(LoanEnterpriseBoundedSchemaV1Error, match="identities"):
        build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)


def test_coordinated_rehash_cannot_force_ambiguous_source_mapping() -> None:
    schema, contexts = _fixtures()
    result = build_loan_enterprise_bounded_schema_projection_v1(schema, contexts)
    tampered = copy.deepcopy(result)
    tampered["emission_policy"]["ambiguous_source_disposition"] = "FORCE_TO_NEAREST_SCHEMA_LEAF"
    material = copy.deepcopy(tampered)
    material.pop("projection_id")
    tampered["projection_id"] = "lebspv1:projection:" + canonical_json_sha256_v1(material)

    with pytest.raises(LoanEnterpriseBoundedSchemaV1Error, match="contract"):
        validate_loan_enterprise_bounded_schema_projection_v1(tampered)
