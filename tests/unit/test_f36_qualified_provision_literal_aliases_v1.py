"""Synthetic config regressions; no actual-source or PDF acceptance is claimed.

The two declarations retain their printed note annotations. They use the existing
unscoped provision matchers, not a newly invented structural provision parent.
The publication disclosure remains unclassified by this change.
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

from bctc_ai.evaluation import gemini_json_operating_expense_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    classify_gemini_json_multitable_hierarchical_table_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(family.__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location(
    "_f36_qualified_provision_existing_fixtures",
    _ROOT / "tests/unit/test_gemini_json_operating_expense_family_v1.py",
)
assert _SPEC is not None and _SPEC.loader is not None
fixture = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fixture)

INVESTMENT = (
    "Trích lập/(hoàn nhập) dự phòng giảm giá đầu tư tài chính dài hạn "
    "(Thuyết minh 11)"
)
OTHER_ASSET = "Dự phòng rủi ro tài sản khác (Thuyết minh 14)"
DECLARATIONS = (
    (INVESTMENT, "LONG_TERM_BAD_DEBT_PROVISION", 1218),
    (OTHER_ASSET, "OTHER_ASSET_PROVISION", 1220),
)


def _classification(page):
    section = page["sections"][0]
    return classify_gemini_json_multitable_hierarchical_table_v1(
        page, section, section["tables"][0],
        compiled_specs=fixture._adapter_compiled(),
    )


def _page(investment=INVESTMENT, other_asset=OTHER_ASSET):
    return fixture._operating_page([
        fixture._row("Chi nộp thuế và các khoản phí, lệ phí", "1", "1"),
        fixture._row("Chi phí cho nhân viên", "2", "2"),
        fixture._row("Chi về tài sản", "3", "3"),
        fixture._row("Chi cho hoạt động quản lý công vụ", "4", "4"),
        fixture._row(investment, "5", "7"),
        fixture._row(other_asset, "6", "(3)"),
        fixture._row("Tổng", "21", "14", kind="TOTAL"),
    ])


def _public(page):
    before = copy.deepcopy(page)
    indexed, trials, pages, compiled = fixture._source_row_coverage_inputs(page)
    family.validate_gemini_json_operating_expense_replay_v1(
        indexed_query_evidence=indexed, trials=trials,
        page_json_by_document=pages, compiled_specs=compiled,
    )
    assert page == before
    assert pages == {1: {fixture.VERSION_ID: before}}
    assert len(trials) == 1
    return indexed, trials[0], pages, compiled


def test_real_config_adds_only_whole_literals_to_existing_unscoped_matchers():
    topology = fixture._json("tm-operating-expense-topology-v1.json")
    compiled = fixture._adapter_compiled()
    by_role = {child["role"]: child for child in topology["children"]}
    for label, role, report_norm_id in DECLARATIONS:
        occurrences = [
            matcher for matcher in by_role[role]["matchers"]
            if label in matcher["aliases"]
        ]
        assert len(occurrences) == 1
        assert occurrences[0]["within_role"] is None
        assert compiled["bindings"][role] == report_norm_id
    assert by_role["GENERIC_PROVISION_SOURCE_ONLY"]["role_kind"] == "ADDITIVE_CHILD"
    assert compiled["owner_complete_population_policy"] == "EXACT_OWNER_WHOLE_MONEY_TABLE"
    assert topology["presence_evidence_mode"] == "WITHIN_EXPLICIT_PARENT_CLUSTER"
    assert "Chi xuất bản tài liệu, quảng cáo" not in {
        alias for child in topology["children"]
        for matcher in child["matchers"] for alias in matcher["aliases"]
    }


@pytest.mark.parametrize("label,role,_report_norm_id", DECLARATIONS)
@pytest.mark.parametrize("nested", [False, True])
def test_qualified_meaning_is_recognized_without_fabricating_structural_parent(
    label, role, _report_norm_id, nested,
):
    parent = "Chi phí dự phòng"
    rows = []
    if nested:
        rows.extend([
            fixture._row(parent, "5", "7"),
            fixture._row("Trong đó:", None, None, kind="GROUP", path=[parent, "Trong đó:"]),
        ])
    rows.append(fixture._row(
        label, "5", "7", path=[parent, "Trong đó:", label] if nested else [label],
    ))
    page = fixture._operating_page(rows)
    before = copy.deepcopy(page)
    classification = _classification(page)
    assert classification["owner_visible"] is True
    assert [hit["row_ordinal"] for hit in classification["role_hits"] if hit["role"] == role] == [len(rows)]
    assert not any(hit["role"] == "PROVISION_GROUP_SOURCE_ONLY" for hit in classification["role_hits"])
    assert page == before


def test_public_flat_literals_keep_signed_values_units_source_refs_and_replay():
    page = _page()
    before = copy.deepcopy(page)
    indexed, trial, pages, compiled = _public(page)
    assert trial["status"] == READY
    assert trial["reasons"] == []
    assert validate_source_observation_mapping_contract_v1(trial)["violation_count"] == 0
    by_id = {mapping["report_norm_id"]: mapping for mapping in trial["mappings"]}
    for report_norm_id, ordinal, label, texts, coefficients in (
        (1218, 5, INVESTMENT, ["5", "7"], [5, 7]),
        (1220, 6, OTHER_ASSET, ["6", "(3)"], [6, -3]),
    ):
        mapping = by_id[report_norm_id]
        assert mapping["unit"] == "MILLION_VND"
        assert [value["source_text"] for value in mapping["values"]] == texts
        assert [value["coefficient"] for value in mapping["values"]] == coefficients
        assert all(value["state"] != "DERIVED" for value in mapping["values"])
        assert {ref["row_ordinal"] for ref in mapping["source_refs"]} == {ordinal}
        assert {ref["label_exact"] for ref in mapping["source_refs"]} == {label}
        assert all(ref["hierarchy_path_exact"] == [label] for ref in mapping["source_refs"])
    coverage = family.build_operating_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed, trials=[trial],
        page_json_by_document=pages, compiled_specs=compiled,
    )
    assert coverage["violation_count"] == 0
    assert page == before


@pytest.mark.parametrize("owner", [
    "Cho vay khách hàng", "Chứng khoán kinh doanh", "Chứng khoán đầu tư",
    "Chi phí dự phòng rủi ro tín dụng", "Chi phí hoạt động dịch vụ",
])
def test_foreign_note_owner_does_not_gain_provision_mappings(owner):
    page = _page()
    page["sections"][0]["title_exact"] = owner
    _indexed, trial, _pages, _compiled = _public(page)
    assert trial["status"] != READY
    assert trial["mappings"] == []


@pytest.mark.parametrize("label,role,_report_norm_id", DECLARATIONS)
@pytest.mark.parametrize("tail", [
    " và dự phòng rủi ro tín dụng",
    " và dự phòng giảm giá chứng khoán kinh doanh",
    " và dự phòng giảm giá chứng khoán đầu tư",
])
def test_compound_population_tail_cannot_use_qualified_alias_prefix(
    label, role, _report_norm_id, tail,
):
    # A failing assertion exposes existing prefix-policy behavior; do not relax
    # this negative or relabel a mixed population as the reviewed literal.
    changed = label + tail
    page = _page(investment=changed) if role == DECLARATIONS[0][1] else _page(other_asset=changed)
    classification = _classification(page)
    assert role not in {
        hit["role"] for hit in classification["role_hits"]
        if hit["row_ordinal"] == (5 if role == DECLARATIONS[0][1] else 6)
    }
    _indexed, trial, _pages, _compiled = _public(page)
    assert trial["status"] != READY
    assert trial["mappings"] == []


@pytest.mark.parametrize("label,role,_report_norm_id", DECLARATIONS)
@pytest.mark.parametrize("change", ["WRONG_NOTE", "LOAN", "TRADING", "EXTRA_ANNOTATION"])
def test_nearby_unreviewed_whole_labels_do_not_gain_the_target_role(
    label, role, _report_norm_id, change,
):
    if change == "WRONG_NOTE":
        changed = label.replace("11)", "12)").replace("14)", "15)")
    elif change == "LOAN":
        changed = label.replace("đầu tư tài chính dài hạn", "cho vay khách hàng").replace("tài sản khác", "tín dụng")
    elif change == "TRADING":
        changed = label.replace("đầu tư tài chính dài hạn", "chứng khoán kinh doanh").replace("tài sản khác", "chứng khoán kinh doanh")
    else:
        changed = label.replace(")", "; điều chỉnh)")
    page = fixture._operating_page([fixture._row(changed, "5", "7")])
    assert role not in {hit["role"] for hit in _classification(page)["role_hits"]}


@pytest.mark.parametrize("conflict", ["UNIT", "PERIOD"])
def test_literal_role_cannot_waive_existing_unit_or_period_gate(conflict):
    page = _page()
    table = page["sections"][0]["tables"][0]
    if conflict == "UNIT":
        table["columns"][1]["header_path_exact"][-1] = "Nghìn đồng"
    else:
        table["columns"][1]["header_path_exact"] = copy.deepcopy(table["columns"][0]["header_path_exact"])
    _indexed, trial, _pages, _compiled = _public(page)
    assert trial["status"] != READY
    assert trial["mappings"] == []


def test_resealed_trial_cannot_redirect_a_new_literal_mapping_to_its_neighbor():
    page = _page()
    indexed, trial, pages, compiled = _public(page)
    assert trial["status"] == READY
    attacked = copy.deepcopy(trial)
    mapping = next(item for item in attacked["mappings"] if item["report_norm_id"] == 1218)
    mapping["source_refs"][0]["row_ordinal"] = 6
    mapping["source_refs"][0]["label_exact"] = OTHER_ASSET
    mapping["source_refs"][0]["hierarchy_path_exact"] = [OTHER_ASSET]
    material = {key: value for key, value in mapping.items() if key != "item_mapping_id"}
    mapping["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
    with pytest.raises(family.GeminiJsonOperatingExpenseFamilyV1Error, match="replay drifted"):
        family.validate_gemini_json_operating_expense_replay_v1(
            indexed_query_evidence=indexed, trials=[attacked],
            page_json_by_document=pages, compiled_specs=compiled,
        )
