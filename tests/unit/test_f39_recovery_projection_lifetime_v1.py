"""Same-invocation projection reuse preserves real source and independent replay."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled
from test_gemini_json_income_tax_observed_subtotal_root_v1 import _original_records
from test_gemini_json_income_tax_original_unit_scope_v2 import _audit_replay, _public

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _base(records, compiled):
    return family.coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled)


def _parent_operation_path(records, base, compiled):
    """Actual parent sequence: prepare/core, then a second outer projection rebuild."""
    cluster = family._recover_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled)
    _, _, projection = family._prepare_income_tax_evaluation_records_v1(
        records, compiled_specs=compiled)
    return family._reseal_cluster(cluster, income_tax_section_caption_projection_receipt=projection)


@pytest.mark.parametrize("case", ["bab-doc020", "eib-doc039"])
def test_actual_sources_match_parent_operation_path_and_keep_independent_prepare(case, monkeypatch):
    _metadata, records = _original_records(case)
    compiled = _adapter_compiled()
    base = _base(records, compiled)
    before = canonical_json_bytes_v1([records, base, compiled])
    actual_prepare = family._prepare_income_tax_evaluation_records_v1
    calls = []

    def witnessed_prepare(*args, **kwargs):
        value = actual_prepare(*args, **kwargs)
        calls.append(value)
        return value

    monkeypatch.setattr(family, "_prepare_income_tax_evaluation_records_v1", witnessed_prepare)
    expected = _parent_operation_path(records, base, compiled)
    assert len(calls) == 3
    calls.clear()
    actual = family.recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled)
    # One fresh public preparation plus the unchanged independent source-context
    # reconstruction. The witness invokes the actual implementation every time.
    assert len(calls) == 2
    assert calls[0][0] is not calls[1][0]
    assert calls[0][2] is not calls[1][2]
    assert canonical_json_bytes_v1(actual) == canonical_json_bytes_v1(expected)
    assert actual["income_tax_section_caption_projection_receipt"] == calls[0][2]
    assert actual["income_tax_section_caption_projection_receipt"] is not calls[0][2]
    assert before == canonical_json_bytes_v1([records, base, compiled])


@pytest.mark.parametrize("case", ["bab-doc020", "eib-doc039"])
def test_actual_original_financial_decisions_raw_units_and_source_replay_remain(case):
    _metadata, records = _original_records(case)
    before = canonical_json_bytes_v1(records)
    candidate, options = _public(records)
    assert options is not None
    independent = family._evaluate_income_tax_before_original_unit_control_v2(**options)
    if case == "bab-doc020":
        assert candidate["status"] == independent["status"] == family.READY
        assert candidate["mappings"] == independent["mappings"]
        control = candidate["closure_receipt"]["income_tax_original_unit_scope_receipt"]
        assert control["failures"] == []
        assert control["document_consensus_equal_amount_or_private_unit_projection_permission"] is False
        assert all(check["status"] == "SOURCE_OWNED" for check in control["checks"])
    else:
        assert candidate["status"] == family.UNRESOLVED
        assert candidate["reasons"] == ["SIGN_INVERTED_DIRECT_NOTE_AND_PRIMARY_INCOME_TAX_PRESENTATIONS"]
        assert candidate["mappings"] == []
        assert canonical_json_bytes_v1(candidate) == canonical_json_bytes_v1(independent)
    # This existing helper runs real indexed->trial reconstruction, whole,
    # financial and retained observation audits, then actual fresh family replay.
    _audit_replay(candidate, options)
    assert canonical_json_bytes_v1(records) == before


def test_returned_projection_is_not_an_alias_or_cross_call_cache(monkeypatch):
    _metadata, records = _original_records("bab-doc020")
    compiled = _adapter_compiled()
    base = _base(records, compiled)
    before = canonical_json_bytes_v1([records, base, compiled])
    actual_prepare = family._prepare_income_tax_evaluation_records_v1
    preparations = []

    def witnessed_prepare(*args, **kwargs):
        value = actual_prepare(*args, **kwargs)
        preparations.append(value)
        return value

    monkeypatch.setattr(family, "_prepare_income_tax_evaluation_records_v1", witnessed_prepare)
    first = family.recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled)
    first_bytes = canonical_json_bytes_v1(first)
    prepared_before = canonical_json_bytes_v1(list(preparations[0]))
    first["income_tax_section_caption_projection_receipt"]["permission_grants"]["unit"] = True
    assert canonical_json_bytes_v1(list(preparations[0])) == prepared_before
    assert first["owner_receipt"]["income_tax_source_context_receipt"][
        "section_caption_projection_receipt"]["permission_grants"]["unit"] is False
    second = family.recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled)
    assert len(preparations) == 4
    assert preparations[0][2] is not preparations[2][2]
    assert canonical_json_bytes_v1(second) == first_bytes
    assert canonical_json_bytes_v1([records, base, compiled]) == before


def test_changed_original_cells_require_fresh_projection_and_reject_old_query():
    metadata, records = _original_records("bab-doc020")
    compiled = _adapter_compiled()
    candidate, options = _public(records, compiled)
    assert candidate["status"] == family.READY and options is not None
    first = family.recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=_base(records, compiled), compiled_specs=compiled)
    changed = deepcopy(records)
    row = changed[0]["page_json"]["sections"][0]["tables"][0]["rows"][metadata["root_row_ordinal"] - 1]
    row["values_exact"][-1] = "999999"
    changed_before = canonical_json_bytes_v1(changed)
    second = family.recover_gemini_json_income_tax_query_cluster_v1(
        page_records=changed, base_cluster=_base(changed, compiled), compiled_specs=compiled)
    first_projection = first["income_tax_section_caption_projection_receipt"]
    second_projection = second["income_tax_section_caption_projection_receipt"]
    assert first_projection["original_records_object_canonical_sha256"] != second_projection[
        "original_records_object_canonical_sha256"]
    assert second_projection["original_records_object_canonical_sha256"] == canonical_json_sha256_v1(changed)
    stale = {**options, "page_json_by_version": {
        record["page_json_version_id"]: record["page_json"] for record in changed}}
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="source context query replay drifted"):
        family.evaluate_gemini_json_income_tax_family_cluster_v1(**stale)
    assert canonical_json_bytes_v1(changed) == changed_before


@pytest.mark.parametrize("target", ["raw", "base", "compiled", "prepared", "repairs", "caption", "part"])
def test_late_actual_core_mutation_cannot_escape_as_prepared_authority(target, monkeypatch):
    _metadata, records = _original_records("bab-doc020")
    compiled = _adapter_compiled()
    base = _base(records, compiled)
    actual_core = family._recover_income_tax_query_cluster_from_prepared_v1

    def changed_after_real_core(**kwargs):
        result = actual_core(**kwargs)
        if target == "raw":
            kwargs["page_records"][0]["page_json"]["sections"][0]["title_exact"] += " changed"
        elif target == "base":
            kwargs["base_cluster"]["reasons"].append("changed")
        elif target == "compiled":
            kwargs["compiled_specs"]["income_tax_adapter_spec_sha256"] = "0" * 64
        elif target == "prepared":
            kwargs["prepared"][0][0]["page_json"]["sections"][0]["title_exact"] += " changed"
        elif target == "repairs":
            kwargs["prepared"][1].append({"changed": True})
        elif target == "caption":
            kwargs["prepared"][2]["permission_grants"]["unit"] = True
        else:
            kwargs["prepared"][2]["part_period_disjointness_receipt"]["selected_context_ids"].append("changed")
        return result

    monkeypatch.setattr(family, "_recover_income_tax_query_cluster_from_prepared_v1", changed_after_real_core)
    with family.income_tax_document_period_evaluation_scope_v1(enabled=False):
        with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="prepared recovery inputs changed"):
            family.recover_gemini_json_income_tax_query_cluster_v1(
                page_records=records, base_cluster=base, compiled_specs=compiled)


@pytest.mark.parametrize("relative", [
    family.DEFAULT_SECTION_CAPTION_AUTH_ENVELOPE_PATH,
    "src/bctc_ai/evaluation/gemini_json_income_tax_section_caption_repair_v1.py",
    family.DEFAULT_SOURCE_REPAIR_SPEC_PATH,
    family.DEFAULT_PART_PERIOD_CONTEXT_REGISTRY_PATH,
    family.DEFAULT_PART_PERIOD_COMMON204_REGISTRY_PATH,
])
def test_late_fixed_authority_byte_drift_still_rejects_without_period_cache(relative, monkeypatch):
    _metadata, records = _original_records("bab-doc020")
    compiled = _adapter_compiled()
    base = _base(records, compiled)
    actual_core = family._recover_income_tax_query_cluster_from_prepared_v1
    actual_read = Path.read_bytes
    core_completed = False
    changed_reads = 0
    target = ROOT / relative

    def real_core_then_change_epoch(**kwargs):
        nonlocal core_completed
        result = actual_core(**kwargs)
        core_completed = True
        return result

    def changed_source_read(path):
        nonlocal changed_reads
        raw = actual_read(path)
        if core_completed and path == target:
            changed_reads += 1
            return raw + b"\n"
        return raw

    monkeypatch.setattr(family, "_recover_income_tax_query_cluster_from_prepared_v1", real_core_then_change_epoch)
    # Negative I/O injection only: actual reads and every financial validator run.
    # No source file is written and no passing financial result is fabricated.
    monkeypatch.setattr(Path, "read_bytes", changed_source_read)
    expected_error = (
        r"^income-tax caption envelope declaration is invalid$"
        if relative == family.DEFAULT_SOURCE_REPAIR_SPEC_PATH
        else r"authority.*(bytes|pin)"
    )
    with family.income_tax_document_period_evaluation_scope_v1(enabled=False):
        with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match=expected_error) as caught:
            family.recover_gemini_json_income_tax_query_cluster_v1(
                page_records=records, base_cluster=base, compiled_specs=compiled)
    assert core_completed, "Actual recovery core must finish before the late authority check"
    assert changed_reads > 0, "The late target authority read must actually receive changed bytes"
    if relative == family.DEFAULT_SOURCE_REPAIR_SPEC_PATH:
        assert type(caught.value.__cause__) is family.GeminiJsonIncomeTaxFamilyV1Error
        assert str(caught.value.__cause__) == "income-tax caption authority actual bytes differ from independent pin"


@pytest.mark.parametrize("name", [
    "_recover_income_tax_query_cluster_from_prepared_v1",
    "_checked_income_tax_caption_preparation_authority_v1",
    "_checked_income_tax_caption_legacy_axis_v1",
])
def test_new_private_entry_replacement_after_real_core_is_caught_at_owner_exit(name, monkeypatch):
    _metadata, records = _original_records("bab-doc020")
    compiled = _adapter_compiled()
    base = _base(records, compiled)
    actual_core = family._recover_income_tax_query_cluster_from_prepared_v1
    actual_entry = getattr(family, name)

    def replacement(*args, **kwargs):
        return actual_entry(*args, **kwargs)

    def real_core_then_replace(**kwargs):
        result = actual_core(**kwargs)
        monkeypatch.setattr(family, name, replacement)
        return result

    monkeypatch.setattr(family, "_recover_income_tax_query_cluster_from_prepared_v1", real_core_then_replace)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="callable changed during operation"):
        family.recover_gemini_json_income_tax_query_cluster_v1(
            page_records=records, base_cluster=base, compiled_specs=compiled)


@pytest.mark.parametrize("records", [None, [], (), {}])
def test_invalid_public_raw_axis_keeps_original_error(records):
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="page-record axis is invalid"):
        family.recover_gemini_json_income_tax_query_cluster_v1(
            page_records=records, base_cluster={}, compiled_specs={})
