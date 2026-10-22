"""Operation-local memoization must preserve fresh original-source authentication."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_income_tax_comparative_flow_policy_v1 import (
    _comparative_flow_records,
    _policy_section,
    _public_query,
    _reseal_receipts,
)
from test_gemini_json_income_tax_family_v1 import (
    _adapter_compiled,
    _adapter_compiled_with_fixture_row_repair,
    _honest_income_recognition_repair_records,
)
from test_gemini_json_income_tax_root_controls_v1 import _evaluate_query
from test_gemini_json_income_tax_signed_display_v1 import (
    _contextual_period_locator,
    _contextual_period_records,
    _document_annual_relative_note_records,
)
from test_run_gemini_json_income_tax_accounting_family_v1 import (
    _fixture as _runner_fixture,
)
from test_run_gemini_json_income_tax_accounting_family_v1 import runner

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    same_typed_json_v1,
)

ERROR = family.GeminiJsonIncomeTaxFamilyV1Error
DEPENDENCY_FILES = (
    "evaluation/gemini_json_income_tax_section_caption_repair_v1.py",
    "evaluation/gemini_json_income_tax_family_v1.py",
    "evaluation/gemini_json_income_tax_part_period_context_v1.py",
    "evaluation/gemini_json_multitable_hierarchical_family_v1.py",
    "evaluation/gemini_json_hierarchical_accounting_family_v1.py",
    "evaluation/gemini_json_customer_deposit_family_v1.py",
    "evaluation/gemini_json_other_long_term_investments_family_v1.py",
    "evaluation/accounting_variant_graph_engine_v1.py",
    "evaluation/source_observation_lane_math_v1.py",
    "evaluation/gemini_json_flat_accounting_family_v1.py",
    "source_structure/contracts_v1.py",
    "config/families/tm-income-tax-part-period-contexts-v1.json",
    "config/families/tm-income-tax-part-period-contexts-common204-v1.json",
    "config/families/tm-income-tax-source-repair-v1.json",
    "config/families/tm-income-tax-section-caption-repair-auth-v2.json",
)
CALLABLE_NAMES = (
    "_build_document_statement_period_inventory_uncached_v1",
    "_document_report_scope_receipt",
    "_document_comparative_flow_policy_receipt",
    "_document_annual_period_receipt",
    "_multitable_lane_axis",
    "_owned_current_period_constraints",
    "_note_report_scope_receipt",
    "_printed_duration_lengths",
    "_absolute_source_duration_semantics",
    "_owned_relative_year_duration_evidence",
    "_printed_ytd_sibling_period_evidence",
    "_load_registered_part_period_registry_v1",
    "_load_registered_part_period_common204_registry_v1",
    "_load_registered_part_period_catalog_v1",
    "_checked_registered_part_period_catalog_v1",
    "_registered_part_original_identity_stage_v1",
    "_compile_source_repairs",
    "_registered_part_period_source_view_v1",
    "_registered_part_period_contexts_v1",
    "_approved_registered_part_period_loader_v1",
    "select_declared_part_period_registry_variant_v1",
    "replay_registered_part_period_contexts_v1",
    "validate_registered_part_period_registry_v1",
    "_registered_part_period_receipt",
    "_owned_flow_report_quarter_constraint",
    "_owned_note_report_quarter_constraint_v1",
    "_cash_flow_partial_current_header_assertion_v1",
    "_cash_flow_printed_period_control_v1",
    "_recognition_immediate_ancestor_owner_v1",
    "_recognition_expense_source_frontier",
    "_recognition_rate_effect_forward_control",
    "_load_registered_section_caption_auth_envelope_v1", "_section_caption_core_ref_v1",
    "_section_caption_pinned_bytes_v1", "_section_caption_part_span_disjointness_v1",
    "_prepare_income_tax_evaluation_records_v1", "_recover_income_tax_query_cluster_v1",
)
SPEC_AXES = (
    "topology", "evaluation", "schema", "query_policy",
    "income_tax_adapter_spec", "income_tax_adapter_spec_sha256",
    "income_tax_source_repairs", "income_tax_source_repair_spec_sha256",
    "income_tax_original_basis_source_specs", "income_tax_primary_both_specs",
    "income_tax_primary_current_specs", "income_tax_primary_detail_specs",
    "income_tax_supplemental_specs", "income_tax_original_rate_specs",
    "income_tax_original_income_specs",
    "income_tax_section_caption_auth_envelope", "income_tax_section_caption_auth_envelope_ref",
    "income_tax_section_caption_clone_core_ref",
)


def _inventory(records, compiled):
    return family._document_statement_period_inventory(records, compiled_specs=compiled)


def _spy_builder(monkeypatch):
    original = family._build_document_statement_period_inventory_uncached_v1
    calls = []

    def counted(records, *, compiled_specs):
        calls.append((deepcopy(records), deepcopy(compiled_specs)))
        return original(records, compiled_specs=compiled_specs)

    monkeypatch.setattr(family, "_build_document_statement_period_inventory_uncached_v1", counted)
    return original, calls


def _proof(records, compiled, inventory):
    return family._source_period_correspondence_receipt(
        left_locator=_contextual_period_locator(records[0]),
        right_locator=_contextual_period_locator(records[1]),
        left_money_column_ordinals=[1, 2], right_money_column_ordinals=[1, 2],
        page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
    )


def _change_source(records, mutation):
    changed = deepcopy(records)
    section = changed[1]["page_json"]["sections"][0]
    table = section["tables"][0]
    if mutation == "money":
        table["rows"][0]["values_exact"][0] = "101"
    elif mutation == "label":
        table["rows"][0]["label_exact"] += " khác"
    elif mutation == "header":
        table["columns"][0]["header_path_exact"] = ["Kỳ chưa xác định"]
    elif mutation == "unit":
        table["unit_exact"] = "VND"
    elif mutation == "caption":
        section["title_exact"] = section["title_exact"].replace("2026", "2025")
    elif mutation == "narrative":
        section["narratives_exact"].append("Cho kỳ hoạt động 3 tháng kết thúc ngày 30 tháng 6 năm 2026")
    elif mutation == "unmapped_ancestry":
        row = changed[0]["page_json"]["sections"][0]["tables"][0]["rows"][0]
        row["hierarchy_path_exact"].insert(0, "Quý III năm 2026")
    elif mutation == "policy":
        policy = _policy_section(changed)
        policy["narratives_exact"] = [line.replace("2024", "2023") for line in policy["narratives_exact"]]
    elif mutation == "kind":
        changed[2]["page_json"]["sections"][0]["content_kind"] = "FINANCIAL_NARRATIVE"
    elif mutation == "remove_cf":
        changed.pop(2)
    elif mutation == "duplicate_page":
        changed.append(deepcopy(changed[2]))
    else:
        raise AssertionError(mutation)
    return changed


@pytest.mark.parametrize("route", ["comparative", "annual", "ytd"])
def test_inventory_memo_is_content_equal_to_cold_build_and_returns_independent_objects(monkeypatch, route):
    factories = {"comparative": _comparative_flow_records, "annual": _document_annual_relative_note_records,
                 "ytd": _contextual_period_records}
    records, compiled = factories[route](), _adapter_compiled()
    before = deepcopy((records, compiled))
    original, calls = _spy_builder(monkeypatch)
    cold = original(records, compiled_specs=compiled)
    with family.income_tax_document_period_evaluation_scope_v1() as metrics:
        first = _inventory(records, compiled)
        second = _inventory(deepcopy(records), deepcopy(compiled))
        assert same_typed_json_v1(first, cold) and same_typed_json_v1(second, cold)
        assert first is not second and first["selected_page_axis"] is not second["selected_page_axis"]
        assert metrics["requests"] == 2 and metrics["builds"] == 1 and metrics["hits"] == 1
        assert metrics["disabled_requests"] == 0 and metrics["peak_entries"] == 1
        assert metrics["peak_stored_bytes"] == len(canonical_json_bytes_v1(cold))
        state = family._DOCUMENT_PERIOD_OPERATION.get()
        assert all(type(entry[0]) is bytes for entry in state["entries"].values())
        assert all(metrics[name] >= 0 for name in ("key_seconds", "build_seconds", "clone_seconds"))
    assert len(calls) == 1 and (records, compiled) == before
    assert metrics["dependency_checks"] == 2 and metrics["dependency_check_seconds"] >= 0
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None


@pytest.mark.parametrize("mutation", [
    "money", "label", "header", "unit", "caption", "narrative", "unmapped_ancestry",
    "policy", "kind", "remove_cf", "duplicate_page",
])
def test_same_id_raw_source_mutation_is_cache_miss_and_stale_inventory_is_not_authority(monkeypatch, mutation):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    changed = _change_source(records, mutation)
    changed_before = deepcopy(changed)
    original, calls = _spy_builder(monkeypatch)
    expected = original(changed, compiled_specs=compiled)
    with family.income_tax_document_period_evaluation_scope_v1() as metrics:
        stale = _inventory(records, compiled)
        fresh = _inventory(changed, compiled)
        assert same_typed_json_v1(fresh, expected)
        assert metrics["builds"] == 2 and metrics["hits"] == 0 and len(calls) == 2
        with pytest.raises(ERROR, match="drifted"):
            _proof(changed, compiled, stale)
    assert changed == changed_before


@pytest.mark.parametrize("field,value", [
    ("document_id", "other-document"), ("document_ordinal", 91),
    ("source_sha256", "f" * 64), ("source_logical_name", "other-source.pdf"),
    ("physical_page", 90), ("selected_page_ordinal", 91),
    ("page_json_version_id", "gfpstorev1:json:" + "a" * 64),
])
def test_every_selected_source_metadata_axis_is_part_of_the_content_key(monkeypatch, field, value):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    changed = deepcopy(records)
    changed[1][field] = value
    original, calls = _spy_builder(monkeypatch)
    expected = original(changed, compiled_specs=compiled)
    with family.income_tax_document_period_evaluation_scope_v1() as metrics:
        stale = _inventory(records, compiled)
        assert same_typed_json_v1(_inventory(changed, compiled), expected)
        assert metrics["builds"] == 2 and len(calls) == 2
        with pytest.raises(ERROR, match="drifted"):
            _proof(changed, compiled, stale)


def test_ordered_raw_records_are_not_reduced_to_a_set_of_page_ids(monkeypatch):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    original, calls = _spy_builder(monkeypatch)
    reversed_records = list(reversed(deepcopy(records)))
    with family.income_tax_document_period_evaluation_scope_v1() as metrics:
        _inventory(records, compiled)
        reordered = _inventory(reversed_records, compiled)
        assert same_typed_json_v1(reordered, original(reversed_records, compiled_specs=compiled))
        assert metrics["builds"] == 2 and metrics["hits"] == 0 and len(calls) == 2


@pytest.mark.parametrize("axis", SPEC_AXES)
def test_full_compiled_spec_content_not_only_declared_semantic_hash_invalidates_memo(monkeypatch, axis):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    changed = deepcopy(compiled)
    value = changed[axis]
    if type(value) is dict:
        value["cache_dependency_test_marker"] = "changed-with-original-declared-hashes-retained"
    elif type(value) is list:
        value.append({"cache_dependency_test_marker": "unused-compilation-dependency"})
    else:
        changed[axis] = "0" * 64
    original, calls = _spy_builder(monkeypatch)
    expected = original(records, compiled_specs=changed)
    with family.income_tax_document_period_evaluation_scope_v1() as metrics:
        _inventory(records, compiled)
        fresh = _inventory(records, changed)
        assert same_typed_json_v1(fresh, expected)
        assert metrics["builds"] == 2 and metrics["hits"] == 0 and len(calls) == 2
    assert changed != compiled


def test_actual_private_row_repair_same_ids_uses_a_distinct_content_entry(monkeypatch):
    compiled = _adapter_compiled_with_fixture_row_repair()
    records = _honest_income_recognition_repair_records()
    repaired, repairs = family._apply_source_repairs(records, compiled_specs=compiled)
    assert repairs and records != repaired
    assert [r["page_json_version_id"] for r in records] == [r["page_json_version_id"] for r in repaired]
    original, calls = _spy_builder(monkeypatch)
    with family.income_tax_document_period_evaluation_scope_v1() as metrics:
        raw = _inventory(records, compiled)
        corrected = _inventory(repaired, compiled)
        assert raw != corrected
        assert same_typed_json_v1(corrected, original(repaired, compiled_specs=compiled))
        assert metrics["builds"] == 2 and len(calls) == 2


@pytest.mark.parametrize("mutation", ["source", "columns", "scope", "policy", "extra"])
def test_poisoning_returned_inventory_cannot_modify_immutable_cached_bytes(mutation):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    before = deepcopy((records, compiled))
    with family.income_tax_document_period_evaluation_scope_v1() as metrics:
        inventory = _inventory(records, compiled)
        pristine = deepcopy(inventory)
        if mutation == "source":
            inventory["selected_page_axis"][0]["original_page_json_sha256"] = "0" * 64
        elif mutation == "columns":
            inventory["sources"][0]["columns_exact"][0]["header_path_exact"].append("forged")
        elif mutation == "scope":
            inventory["document_report_scope_receipt"]["report_scope"] = "CONSOLIDATED"
        elif mutation == "policy":
            inventory["document_comparative_flow_policy_receipt"]["complete"] = False
        else:
            inventory["unregistered_assertion"] = {"complete": True}
        _reseal_receipts(inventory)
        second = _inventory(records, compiled)
        assert same_typed_json_v1(second, pristine)
        assert metrics["hits"] == 1
        with pytest.raises(ERROR, match="drifted"):
            _proof(records, compiled, inventory)
        assert _proof(records, compiled, second)["complete"] is True
    assert (records, compiled) == before


@pytest.mark.parametrize("mutation", ["policy", "source", "scope"])
def test_warm_public_evaluator_still_rejects_fully_self_resealed_query(mutation):
    records = _comparative_flow_records()
    compiled, cluster, query = _public_query(records)
    assert query is not None
    forged = deepcopy(query)
    inventory = forged["source_context_receipt"]["document_statement_period_inventory"]
    if mutation == "policy":
        inventory["document_comparative_flow_policy_receipt"]["complete"] = False
    elif mutation == "source":
        inventory["sources"][0]["original_table_json_sha256"] = "0" * 64
    else:
        inventory["document_report_scope_receipt"]["report_scope"] = "CONSOLIDATED"
    _reseal_receipts(forged)
    before = deepcopy(records)
    with family.income_tax_document_period_evaluation_scope_v1():
        assert _evaluate_query(records, compiled, cluster, query)["status"] == family.READY
        with pytest.raises(ERROR, match="drifted"):
            _evaluate_query(records, compiled, cluster, forged)
        assert _evaluate_query(records, compiled, cluster, query)["status"] == family.READY
    assert records == before


def test_cache_entries_are_bounded_and_evicted_content_is_recomputed_not_omitted(monkeypatch):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    variants = [records, _change_source(records, "money"), _change_source(records, "policy")]
    original, calls = _spy_builder(monkeypatch)
    expected = [original(r, compiled_specs=compiled) for r in variants]
    with family.income_tax_document_period_evaluation_scope_v1() as metrics:
        for records_variant, cold in zip(variants, expected, strict=True):
            assert same_typed_json_v1(_inventory(records_variant, compiled), cold)
            assert len(family._DOCUMENT_PERIOD_OPERATION.get()["entries"]) <= 2
        assert same_typed_json_v1(_inventory(variants[0], compiled), expected[0])
        assert metrics["builds"] == 4 and len(calls) == 4 and metrics["peak_entries"] == 2
        assert metrics["peak_stored_bytes"] <= sum(sorted(len(canonical_json_bytes_v1(x)) for x in expected)[-2:])


@pytest.mark.parametrize("mutation", ["policy", "document_identity"])
def test_distinct_document_contexts_cannot_borrow_cached_period_authority(monkeypatch, mutation):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    changed = _change_source(records, "policy") if mutation == "policy" else deepcopy(records)
    if mutation == "document_identity":
        for r in changed:
            r.update(document_id="another-document", document_ordinal=99, source_sha256="a" * 64,
                     source_logical_name="another-document.pdf")
    original, calls = _spy_builder(monkeypatch)
    with family.income_tax_document_period_evaluation_scope_v1() as metrics:
        first = _inventory(records, compiled)
        other = _inventory(changed, compiled)
        assert same_typed_json_v1(other, original(changed, compiled_specs=compiled))
        assert same_typed_json_v1(_inventory(records, compiled), first)
        assert metrics["builds"] == 2 and metrics["hits"] == 1 and len(calls) == 2
        with pytest.raises(ERROR, match="drifted"):
            _proof(changed, compiled, first)


def test_operation_exit_exception_and_fresh_scope_never_reuse_previous_entries(monkeypatch):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    _original, calls = _spy_builder(monkeypatch)
    captured = None
    with pytest.raises(RuntimeError, match="intentional"):
        with family.income_tax_document_period_evaluation_scope_v1():
            _inventory(records, compiled)
            captured = family._DOCUMENT_PERIOD_OPERATION.get()
            raise RuntimeError("intentional")
    assert captured["closed"] is True and captured["entries"] == {}
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None
    with family.income_tax_document_period_evaluation_scope_v1() as metrics:
        _inventory(records, compiled)
        assert metrics["builds"] == 1 and metrics["hits"] == 0
    assert len(calls) == 2 and family._DOCUMENT_PERIOD_OPERATION.get() is None


def test_nested_enabled_disabled_enabled_restores_parent_and_disabled_is_sticky():
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    with family.income_tax_document_period_evaluation_scope_v1() as outer:
        _inventory(records, compiled)
        outer_state = family._DOCUMENT_PERIOD_OPERATION.get()
        with family.income_tax_document_period_evaluation_scope_v1(enabled=False) as disabled:
            assert family._DOCUMENT_PERIOD_OPERATION.get() is not outer_state
            with family.income_tax_document_period_evaluation_scope_v1(enabled=True) as nested:
                assert nested is disabled
                _inventory(records, compiled)
                _inventory(records, compiled)
            assert disabled["requests"] == disabled["disabled_requests"] == disabled["builds"] == 2
            assert disabled["hits"] == disabled["peak_entries"] == disabled["peak_stored_bytes"] == 0
        assert disabled["dependency_checks"] == 0 and disabled["dependency_check_seconds"] == 0.0
        assert family._DOCUMENT_PERIOD_OPERATION.get() is outer_state
        _inventory(records, compiled)
        assert outer["builds"] == 1 and outer["hits"] == 1 and outer["disabled_requests"] == 0
    assert outer["dependency_checks"] == 2
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None


@pytest.mark.parametrize("enabled", [0, 1, None, "false"])
def test_cache_switch_requires_a_boolean(enabled):
    with pytest.raises(ERROR, match="switch is invalid"):
        with family.income_tax_document_period_evaluation_scope_v1(enabled=enabled):
            raise AssertionError("invalid scope entered")


def test_dependency_refs_are_actual_complete_reviewed_file_bytes():
    refs = family._period_inventory_dependency_refs_v1()
    assert [r["path"] for r in refs] == list(DEPENDENCY_FILES)
    root = Path(family.__file__).resolve().parents[1]
    for reference in refs:
        dependency_root = root.parents[1] if reference["path"].startswith("config/") else root
        raw = (dependency_root / reference["path"]).read_bytes()
        assert reference["size_bytes"] == len(raw)
        assert reference["sha256"] == sha256(raw).hexdigest()
    assert len(refs) == len({ref["path"] for ref in refs}) == 15
    assert [ref["sha256"] for ref in refs[-4:]] == [
        "c98624ac7822b44fa53c055ad094968a7fb11f3e96751a1c06e875b4999c140b",
        "7ba529e7878c1fd5d6af27abe4b5a7d2937bd395b40e3ea1160ee261448adaeb",
        "9aac4e448b82ee0078c007ca06a36f0e3f11c2b4f694266a1211929f16228ea4",
        "dc80fc86b1e718117e5a6ea80bf9a45d5c7a04a6cf084db89daa8621f4a14c74",
    ]


@pytest.mark.parametrize("axis", ["income_tax_part_period_registry", "income_tax_part_period_registry_ref"])
def test_changed_registered_authority_cannot_reuse_prior_successful_inventory(axis):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    changed = deepcopy(compiled)
    changed[axis]["caller_resealed_marker"] = "not-approved"
    with pytest.raises(ERROR, match="compiled part-period authority drifted"):
        with family.income_tax_document_period_evaluation_scope_v1() as metrics:
            _inventory(records, compiled)
            state = family._DOCUMENT_PERIOD_OPERATION.get()
            _inventory(records, changed)
    assert metrics["hits"] == 0 and metrics["builds"] == 1
    assert state["closed"] is True and state["entries"] == {}
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None


@pytest.mark.parametrize("file_index", range(len(DEPENDENCY_FILES)))
def test_each_dependency_file_drift_blocks_handoff_at_owning_exit_without_modifying_files(monkeypatch, file_index):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    refs = family._period_inventory_dependency_refs_v1()
    supplied = deepcopy(refs)
    monkeypatch.setattr(family, "_period_inventory_dependency_refs_v1", lambda: deepcopy(supplied))
    handed_off = []
    with pytest.raises(ERROR, match="changed during operation"):
        with family.income_tax_document_period_evaluation_scope_v1() as metrics:
            pristine = _inventory(records, compiled)
            state = family._DOCUMENT_PERIOD_OPERATION.get()
            supplied[file_index]["sha256"] = "0" * 64
            # A nested result remains provisional; disk verification belongs
            # to the owning exit, not to every unchanged source-content hit.
            assert same_typed_json_v1(_inventory(records, compiled), pristine)
            assert metrics["dependency_checks"] == 1
        handed_off.append(pristine)
    assert handed_off == [] and state["closed"] is True and state["entries"] == {}
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None and metrics["dependency_checks"] == 2
    supplied[:] = deepcopy(refs)
    with family.income_tax_document_period_evaluation_scope_v1():
        assert same_typed_json_v1(_inventory(records, compiled), pristine)


@pytest.mark.parametrize("name", CALLABLE_NAMES)
def test_declared_callable_replacement_is_fail_closed_not_new_authority(monkeypatch, name):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    original = getattr(family, name)

    def replacement(*args, **kwargs):
        return original(*args, **kwargs)

    with pytest.raises(ERROR, match="invalidated"):
        with family.income_tax_document_period_evaluation_scope_v1():
            pristine = _inventory(records, compiled)
            monkeypatch.setattr(family, name, replacement)
            with pytest.raises(ERROR, match="changed during operation"):
                _inventory(records, compiled)
            monkeypatch.setattr(family, name, original)
            with pytest.raises(ERROR, match="closed or invalidated"):
                _inventory(records, compiled)
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None
    monkeypatch.setattr(family, name, replacement)
    with family.income_tax_document_period_evaluation_scope_v1():
        assert same_typed_json_v1(_inventory(records, compiled), pristine)


@pytest.mark.parametrize("failure_phase", ["first_lookup", "owning_exit"])
def test_dependency_provider_failure_blocks_acceptance_and_always_cleans_up(monkeypatch, failure_phase):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    original = family._period_inventory_dependency_refs_v1

    def absent():
        raise ERROR("income-tax period inventory implementation dependency is absent")

    handed_off = []
    if failure_phase == "first_lookup":
        monkeypatch.setattr(family, "_period_inventory_dependency_refs_v1", absent)
    with pytest.raises(ERROR):
        with family.income_tax_document_period_evaluation_scope_v1():
            state = family._DOCUMENT_PERIOD_OPERATION.get()
            result = _inventory(records, compiled)
            monkeypatch.setattr(family, "_period_inventory_dependency_refs_v1", absent)
        handed_off.append(result)
    assert handed_off == [] and state["closed"] is True and state["entries"] == {}
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None
    monkeypatch.setattr(family, "_period_inventory_dependency_refs_v1", original)
    with family.income_tax_document_period_evaluation_scope_v1():
        assert _inventory(records, compiled)["receipt_id"]


@pytest.mark.parametrize("target", ["source", "spec"])
def test_input_mutation_during_builder_is_latched_before_any_result_is_returned(monkeypatch, target):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    original = family._build_document_statement_period_inventory_uncached_v1
    before_records, before_compiled = deepcopy(records), deepcopy(compiled)

    def changing(source_records, *, compiled_specs):
        result = original(source_records, compiled_specs=compiled_specs)
        if target == "source":
            source_records[0]["page_json"]["sections"][0]["title_exact"] += " changed"
        else:
            compiled_specs["cache_dependency_test_marker"] = True
        return result

    monkeypatch.setattr(family, "_build_document_statement_period_inventory_uncached_v1", changing)
    with pytest.raises(ERROR, match="invalidated"):
        with family.income_tax_document_period_evaluation_scope_v1():
            with pytest.raises(ERROR, match="changed during construction"):
                _inventory(records, compiled)
            records[:] = deepcopy(before_records)
            compiled.clear()
            compiled.update(deepcopy(before_compiled))
            with pytest.raises(ERROR, match="closed or invalidated"):
                _inventory(records, compiled)
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None


@pytest.mark.parametrize("entry", ["inventory", "scope"])
def test_copied_context_cannot_resurrect_closed_operation_in_same_execution_owner(entry):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    with family.income_tax_document_period_evaluation_scope_v1():
        _inventory(records, compiled)
        copied = copy_context()

    def reused():
        if entry == "inventory":
            return _inventory(records, compiled)
        with family.income_tax_document_period_evaluation_scope_v1():
            return _inventory(records, compiled)

    with pytest.raises(ERROR, match="closed or invalidated"):
        copied.run(reused)
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None


@pytest.mark.parametrize("entry", ["inventory", "scope"])
def test_inherited_context_cannot_share_operation_with_another_thread(entry):
    records, compiled = _comparative_flow_records(), _adapter_compiled()

    def other_owner():
        if entry == "inventory":
            return _inventory(records, compiled)
        with family.income_tax_document_period_evaluation_scope_v1():
            return _inventory(records, compiled)

    with family.income_tax_document_period_evaluation_scope_v1():
        _inventory(records, compiled)
        inherited = copy_context()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(inherited.run, other_owner)
            with pytest.raises(ERROR, match="cross tasks or threads"):
                future.result(timeout=10)
        assert _inventory(records, compiled)["receipt_id"]


@pytest.mark.parametrize("entry", ["inventory", "scope"])
def test_inherited_context_cannot_share_operation_with_another_async_task(entry):
    records, compiled = _comparative_flow_records(), _adapter_compiled()

    async def child():
        if entry == "inventory":
            return _inventory(records, compiled)
        with family.income_tax_document_period_evaluation_scope_v1():
            return _inventory(records, compiled)

    async def parent():
        with family.income_tax_document_period_evaluation_scope_v1():
            _inventory(records, compiled)
            task = asyncio.create_task(child())
            with pytest.raises(ERROR, match="cross tasks or threads"):
                await task
            assert _inventory(records, compiled)["receipt_id"]

    asyncio.run(parent())


def test_public_recover_and_evaluate_create_and_cleanup_standalone_operations(monkeypatch):
    records = _comparative_flow_records()
    _original, calls = _spy_builder(monkeypatch)
    compiled, cluster, query = _public_query(records)
    assert query is not None and calls and family._DOCUMENT_PERIOD_OPERATION.get() is None
    recovery_calls = len(calls)
    first = _evaluate_query(records, compiled, cluster, query)
    assert first["status"] == family.READY
    assert len(calls) > recovery_calls and family._DOCUMENT_PERIOD_OPERATION.get() is None
    evaluation_calls = len(calls)
    second = _evaluate_query(records, compiled, cluster, query)
    assert same_typed_json_v1(first, second) and len(calls) > evaluation_calls
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None


def test_public_warm_and_explicit_cold_results_are_exact_including_all_nested_receipts():
    records = _comparative_flow_records()
    before = deepcopy(records)
    with family.income_tax_document_period_evaluation_scope_v1() as cached:
        compiled, cluster, query = _public_query(records)
        first = _evaluate_query(records, compiled, cluster, query)
        second = _evaluate_query(records, compiled, cluster, query)
        assert cached["hits"] > 0 and cached["builds"] < cached["requests"]
    with family.income_tax_document_period_evaluation_scope_v1(enabled=False) as cold:
        cold_compiled, cold_cluster, cold_query = _public_query(records)
        actual = _evaluate_query(records, cold_compiled, cold_cluster, cold_query)
        assert cold["requests"] == cold["disabled_requests"] == cold["builds"] > 0
        assert cold["hits"] == cold["peak_entries"] == cold["peak_stored_bytes"] == 0
    assert cached["dependency_checks"] == 2
    assert cold["dependency_checks"] == 0 and cold["dependency_check_seconds"] == 0.0
    assert first["status"] == family.READY
    assert same_typed_json_v1(cluster, cold_cluster) and same_typed_json_v1(query, cold_query)
    assert same_typed_json_v1(first, second) and same_typed_json_v1(first, actual)
    assert records == before


def test_disabled_public_operations_never_consult_the_cache_key_or_dependency_provider(monkeypatch):
    records = _comparative_flow_records()

    def forbidden(*args, **kwargs):
        raise AssertionError("Explicit cold replay consulted inventory memoization")

    monkeypatch.setattr(family, "_period_inventory_key_v1", forbidden)
    monkeypatch.setattr(family, "_period_inventory_dependency_refs_v1", forbidden)
    with family.income_tax_document_period_evaluation_scope_v1(enabled=False) as metrics:
        compiled, cluster, query = _public_query(records)
        assert _evaluate_query(records, compiled, cluster, query)["status"] == family.READY
        assert metrics["requests"] == metrics["disabled_requests"] == metrics["builds"] > 0
        assert metrics["hits"] == metrics["peak_entries"] == metrics["peak_stored_bytes"] == 0
    assert metrics["dependency_checks"] == 0 and metrics["dependency_check_seconds"] == 0.0


def test_runner_shares_document_scope_and_actual_independent_replay_is_explicitly_cold(tmp_path):
    database, document, specs, compiled = _runner_fixture(tmp_path)
    indexed, trials, timing = runner._evaluate_stream_v1(database, [document], compiled)
    metrics = timing["document_period_inventory_cache"]
    assert trials[0]["status"] == runner.READY
    assert metrics["requests"] > metrics["builds"] > 0 and metrics["hits"] > 0
    assert metrics["disabled_requests"] == 0
    assert metrics["dependency_checks"] == 2 and metrics["dependency_check_seconds"] >= 0
    replay_metrics = {}
    replay = runner.replay_income_tax_trials_from_source_v1(
        source_page_database=database, selected_page_json_version_ids=tuple(document["ids"]),
        indexed_query_evidence=indexed,
        compiled_specs=runner.compile_gemini_json_flat_family_specs_v1(
            specs["topology"], specs["evaluation"], specs["schema"],
        ), replay_metrics=replay_metrics,
    )
    assert same_typed_json_v1(replay, trials)
    cold = replay_metrics["document_period_inventory_cache"]
    assert cold["requests"] == cold["disabled_requests"] == cold["builds"] > 0
    assert cold["hits"] == cold["peak_entries"] == cold["peak_stored_bytes"] == 0
    assert cold["dependency_checks"] == 0 and cold["dependency_check_seconds"] == 0.0
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None


class _NonPlainReplayMetrics(dict):
    pass


@pytest.mark.parametrize("sink", [[], {"not_fresh": True}, _NonPlainReplayMetrics()])
def test_independent_replay_metrics_sink_cannot_supply_preexisting_state(tmp_path, sink):
    database, document, specs, compiled = _runner_fixture(tmp_path)
    indexed, _trials, _timing = runner._evaluate_stream_v1(database, [document], compiled)
    before = deepcopy(sink)
    with pytest.raises(runner.RunGeminiJsonIncomeTaxV1Error):
        runner.replay_income_tax_trials_from_source_v1(
            source_page_database=database, selected_page_json_version_ids=tuple(document["ids"]),
            indexed_query_evidence=indexed,
            compiled_specs=runner.compile_gemini_json_flat_family_specs_v1(
                specs["topology"], specs["evaluation"], specs["schema"],
            ), replay_metrics=sink,
        )
    assert sink == before


def test_dependency_hashing_occurs_only_on_first_use_and_successful_owning_exit(monkeypatch):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    refs = family._period_inventory_dependency_refs_v1()
    checks = []

    def counted_refs():
        checks.append(True)
        return deepcopy(refs)

    monkeypatch.setattr(family, "_period_inventory_dependency_refs_v1", counted_refs)
    with family.income_tax_document_period_evaluation_scope_v1() as metrics:
        state = family._DOCUMENT_PERIOD_OPERATION.get()
        assert checks == [] and metrics["dependency_checks"] == 0
        first = _inventory(records, compiled)
        assert len(checks) == metrics["dependency_checks"] == 1
        with family.income_tax_document_period_evaluation_scope_v1() as nested:
            assert nested is metrics and family._DOCUMENT_PERIOD_OPERATION.get() is state
            assert same_typed_json_v1(_inventory(records, compiled), first)
        assert state["closed"] is False and len(checks) == 1
        assert same_typed_json_v1(_inventory(records, compiled), first)
    assert len(checks) == metrics["dependency_checks"] == 2
    assert metrics["dependency_check_seconds"] >= 0
    assert state["closed"] is True and state["entries"] == {}
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None


@pytest.mark.parametrize("enabled", [True, False])
def test_unused_scope_has_no_implementation_dependency_checks(monkeypatch, enabled):
    def forbidden():
        raise AssertionError("An unused inventory scope read implementation bytes")

    monkeypatch.setattr(family, "_period_inventory_dependency_refs_v1", forbidden)
    with family.income_tax_document_period_evaluation_scope_v1(enabled=enabled) as metrics:
        state = family._DOCUMENT_PERIOD_OPERATION.get()
        with family.income_tax_document_period_evaluation_scope_v1():
            pass
    assert metrics["requests"] == metrics["dependency_checks"] == 0
    assert metrics["dependency_check_seconds"] == 0.0
    assert state["closed"] is True and family._DOCUMENT_PERIOD_OPERATION.get() is None


@pytest.mark.parametrize("axis", ["size_bytes", "path"])
def test_dependency_metadata_drift_after_last_getter_blocks_external_handoff(monkeypatch, axis):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    supplied = family._period_inventory_dependency_refs_v1()
    monkeypatch.setattr(family, "_period_inventory_dependency_refs_v1", lambda: deepcopy(supplied))
    accepted = []
    with pytest.raises(ERROR, match="changed during operation"):
        with family.income_tax_document_period_evaluation_scope_v1() as metrics:
            result = _inventory(records, compiled)
            state = family._DOCUMENT_PERIOD_OPERATION.get()
            if axis == "size_bytes":
                supplied[0][axis] += 1
            else:
                supplied[0][axis] += ".different"
            # No further lookup can serve as the final acceptance guard.
        accepted.append(result)
    assert accepted == [] and metrics["dependency_checks"] == 2
    assert state["closed"] is True and state["entries"] == {}
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None


@pytest.mark.parametrize("entry", ["recover", "evaluate"])
def test_standalone_public_return_is_blocked_by_dependency_exit_barrier(monkeypatch, entry):
    records = _comparative_flow_records()
    compiled, cluster, query = _public_query(records)
    supplied = family._period_inventory_dependency_refs_v1()
    original_context = family._source_context_receipt
    checks = []
    context_calls = []

    def current_refs():
        checks.append(True)
        return deepcopy(supplied)

    def context_then_drift(*args, **kwargs):
        result = original_context(*args, **kwargs)
        context_calls.append(True)
        supplied[0]["sha256"] = "0" * 64
        return result

    monkeypatch.setattr(family, "_period_inventory_dependency_refs_v1", current_refs)
    monkeypatch.setattr(family, "_source_context_receipt", context_then_drift)
    accepted = []
    with pytest.raises(ERROR, match="changed during operation"):
        if entry == "recover":
            result = _public_query(records)
        else:
            result = _evaluate_query(records, compiled, cluster, query)
        accepted.append(result)
    assert context_calls and len(checks) == 2 and accepted == []
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None


@pytest.mark.parametrize("name", CALLABLE_NAMES)
def test_callable_changed_after_last_getter_is_rejected_at_owning_exit(monkeypatch, name):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    original = getattr(family, name)

    def replacement(*args, **kwargs):
        return original(*args, **kwargs)

    accepted = []
    with pytest.raises(ERROR, match="changed during operation"):
        with family.income_tax_document_period_evaluation_scope_v1() as metrics:
            result = _inventory(records, compiled)
            state = family._DOCUMENT_PERIOD_OPERATION.get()
            monkeypatch.setattr(family, name, replacement)
        accepted.append(result)
    assert accepted == [] and metrics["dependency_checks"] == 2
    assert state["closed"] is True and state["invalidated"] is True and state["entries"] == {}
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None


def test_caught_callable_drift_cannot_be_restored_to_bypass_exit_without_another_lookup(monkeypatch):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    original = family._document_report_scope_receipt

    def replacement(*args, **kwargs):
        return original(*args, **kwargs)

    accepted = []
    with pytest.raises(ERROR, match="invalidated"):
        with family.income_tax_document_period_evaluation_scope_v1():
            result = _inventory(records, compiled)
            state = family._DOCUMENT_PERIOD_OPERATION.get()
            monkeypatch.setattr(family, "_document_report_scope_receipt", replacement)
            with pytest.raises(ERROR, match="changed during operation"):
                _inventory(records, compiled)
            monkeypatch.setattr(family, "_document_report_scope_receipt", original)
            # Even restored dependencies cannot revive a caught invalidation.
        accepted.append(result)
    assert accepted == [] and state["invalidated"] is True and state["closed"] is True
    assert state["entries"] == {} and family._DOCUMENT_PERIOD_OPERATION.get() is None


class _InventoryScopeAbort(BaseException):
    pass


@pytest.mark.parametrize("exception_type", [KeyboardInterrupt, _InventoryScopeAbort])
def test_baseexception_still_closes_clears_and_resets_owning_operation(exception_type):
    records, compiled = _comparative_flow_records(), _adapter_compiled()
    with pytest.raises(exception_type):
        with family.income_tax_document_period_evaluation_scope_v1() as metrics:
            _inventory(records, compiled)
            state = family._DOCUMENT_PERIOD_OPERATION.get()
            raise exception_type("abort before acceptance")
    assert metrics["dependency_checks"] == 2
    assert state["closed"] is True and state["entries"] == {}
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None
    with family.income_tax_document_period_evaluation_scope_v1():
        assert _inventory(records, compiled)["receipt_id"]


def test_runner_cannot_index_or_return_document_when_last_trial_dependency_check_fails(monkeypatch, tmp_path):
    database, document, _specs, compiled = _runner_fixture(tmp_path)
    supplied = family._period_inventory_dependency_refs_v1()
    original_trial = runner._trial_v1
    trial_calls = []
    indexed_calls = []

    def trial_then_drift(*args, **kwargs):
        result = original_trial(*args, **kwargs)
        trial_calls.append(True)
        supplied[0]["sha256"] = "0" * 64
        return result

    def forbidden_index(*args, **kwargs):
        indexed_calls.append(True)
        raise AssertionError("A provisional failed document reached indexed evidence")

    monkeypatch.setattr(family, "_period_inventory_dependency_refs_v1", lambda: deepcopy(supplied))
    monkeypatch.setattr(runner, "_trial_v1", trial_then_drift)
    monkeypatch.setattr(runner, "build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1", forbidden_index)
    accepted = []
    with pytest.raises(ERROR, match="changed during operation"):
        accepted.append(runner._evaluate_stream_v1(database, [document], compiled))
    assert trial_calls and indexed_calls == [] and accepted == []
    assert family._DOCUMENT_PERIOD_OPERATION.get() is None
