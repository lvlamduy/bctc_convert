"""Public F39 integration of independently loaded registered NOTE periods.

The patched loader is a synthetic fixture for the immutable authority boundary,
not a production approval flag. PRIMARY periods remain independently printed.
Raw-position snapshots below are test immutability checks, not authenticated
production raw-census receipts or PDF acceptance claims.
"""

from __future__ import annotations

import unicodedata
from copy import deepcopy
from hashlib import sha256

import pytest
from test_gemini_json_income_tax_family_v1 import (
    _adapter_compiled,
    _original_note_production_records,
    _page,
    _primary_page,
    _primary_record,
    _record,
    _row,
)
from test_gemini_json_income_tax_root_controls_v1 import _evaluate_query
from test_gemini_json_income_tax_signed_display_v1 import (
    _contextual_period_locator,
    _contextual_period_records,
)

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation.gemini_json_income_tax_part_period_context_v1 import (
    GeminiJsonIncomeTaxPartPeriodContextV1Error,
    validate_registered_part_period_registry_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

HEADING = (
    "Thông tin bổ sung cho các khoản mục trình bày trong "
    "Báo cáo kết quả hoạt động kinh doanh"
)
BASE_COMMIT = "8efd618b6c77f0cdbb402a440e7ba3b3549184f1"


def _fixture_records(*, original_note=False, absolute_primary=True):
    if original_note:
        records = _original_note_production_records(expense_component="Kỳ hiện hành")
        months = 12
    else:
        records = _contextual_period_records(
            quarter="II", absolute_primary=absolute_primary, include_cash_flow=False,
        )
        months = 6
        records[1]["page_json"]["sections"][0]["title_exact"] = (
            "Báo cáo kết quả hoạt động riêng giữa niên độ cho giai đoạn "
            "từ ngày 01/01/2026 đến ngày 30/06/2026"
        )
    for record in records:
        record["physical_page"] += 1
        record["selected_page_ordinal"] += 1
    note = records[0]["page_json"]["sections"][0]
    for table in note["tables"]:
        for column, label in zip(table["columns"], ("Kỳ này", "Kỳ trước"), strict=True):
            column["header_path_exact"] = [label]
    day = 31 if months == 12 else 30
    owner = _record(_page([], owner=HEADING, tables=[]))
    owner.update(page_json_version_id="gfpstorev1:json:" + "f" * 64)
    owner["page_json"]["sections"][0]["narratives_exact"] = [
        "Các thông tin trình bày trong phần này: "
        f"Kỳ này bắt đầu từ 01/01/2026 đến {day:02}/{months:02}/2026; "
        f"Kỳ trước bắt đầu từ 01/01/2025 đến {day:02}/{months:02}/2025",
    ]
    return [owner, *records]


def _ref(path, token):
    return {"path": path, "sha256": sha256(token.encode()).hexdigest(), "size_bytes": 123}


def _registry(records):
    owner, note = records[:2]
    owner_section = owner["page_json"]["sections"][0]
    note_section = note["page_json"]["sections"][0]

    def occurrence(kind, raw, narrative=None):
        section_sha = canonical_json_sha256_v1(owner_section)
        return {
            "page_json_version_id": owner["page_json_version_id"],
            "physical_page": owner["physical_page"], "carrier_kind": kind,
            "section_id": "s1", "table_id": None, "narrative_ordinal": narrative,
            "source_exact": raw, "source_sha256": sha256(raw.encode("utf-8")).hexdigest(),
            "span_start": 0, "span_end": len(raw), "substring_exact": raw,
            "original_section_json_sha256": section_sha,
            "evaluation_section_json_sha256": section_sha,
        }

    targets = []
    for ordinal, table in enumerate(note_section["tables"], 1):
        targets.append({
            "page_json_version_id": note["page_json_version_id"],
            "physical_page": note["physical_page"],
            "selected_page_ordinal": note["selected_page_ordinal"],
            "section_id": "s1", "table_id": "t" + str(ordinal),
            "original_section_json_sha256": canonical_json_sha256_v1(note_section),
            "evaluation_section_json_sha256": canonical_json_sha256_v1(note_section),
            "original_table_json_sha256": canonical_json_sha256_v1(table),
            "evaluation_table_json_sha256": canonical_json_sha256_v1(table),
            "money_column_ordinals": [1, 2],
            "header_paths_exact": [deepcopy(column["header_path_exact"]) for column in table["columns"]],
            "column_value_kinds": [column["value_kind"] for column in table["columns"]],
            "period_order": ["CURRENT", "COMPARATIVE"],
        })
    context = {
        "context_id": "test-fixture:registered-note-part-period:1",
        "pdf_source": {"logical_name": note["source_logical_name"],
                       "sha256": note["source_sha256"], "size_bytes": 2000},
        "document_id": note["document_id"],
        "provenance_document_ordinal": note["document_ordinal"],
        "span_pages": [{
            "physical_page": record["physical_page"],
            "selected_page_ordinal": record["selected_page_ordinal"],
            "page_json_version_id": record["page_json_version_id"],
            "original_page_json_sha256": canonical_json_sha256_v1(record["page_json"]),
            "evaluation_page_json_sha256": canonical_json_sha256_v1(record["page_json"]),
        } for record in (owner, note)],
        "heading_occurrences": [occurrence("SECTION_TITLE", owner_section["title_exact"])],
        "period_occurrences": [occurrence("NARRATIVE", owner_section["narratives_exact"][0], 1)],
        "target_tables": targets,
        "review_evidence": {
            "manual_review_ref": _ref("/external/test-only-part-review.json", "manual-review"),
            "visual_refs": [{
                "png_ref": _ref(f"/external/test-only-page-{record['physical_page']}.png", "png-" + str(record["physical_page"])),
                "render_receipt_ref": _ref(f"/external/test-only-page-{record['physical_page']}.json", "render-" + str(record["physical_page"])),
                "physical_page": record["physical_page"], "renderer_version": "Poppler pdftoppm 24.02.0",
                "dpi": 144, "width_pixels": 1176, "height_pixels": 1680,
            } for record in (owner, note)],
            "no_reset_observation_exact": "Synthetic fixture complete prefix: no intervening reset before the exact tax targets; no part-end claim.",
        },
    }
    return {"format_version": "INCOME_TAX_REGISTERED_PART_PERIOD_CONTEXTS_V1", "family_id": "INCOME_TAX",
            "base_git_commit": BASE_COMMIT, "contexts": [context]}


def _install_registry(monkeypatch, registry):
    calls = []

    def independent_fixture_loader():
        calls.append(True)
        validated = validate_registered_part_period_registry_v1(deepcopy(registry))
        raw = canonical_json_bytes_v1(registry)
        return validated, {"path": "config/families/tm-income-tax-part-period-contexts-v1.json",
                           "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}

    monkeypatch.setattr(family, "_load_registered_part_period_registry_v1", independent_fixture_loader)
    return _adapter_compiled(), calls


def _positions(records):
    """Exact test-position snapshot, not a production authenticated census."""
    return deepcopy([{
        "record_axis": {key: value for key, value in record.items() if key != "page_json"},
        "page_json": record["page_json"],
    } for record in records])


def _period(records, compiled, left=1, right=2, *, inventory=None, left_table="t1", right_table="t1"):
    inventory = (family._document_statement_period_inventory(records, compiled_specs=compiled)
                 if inventory is None else inventory)

    def selector(index, table_id):
        record = records[index]
        section = record["page_json"]["sections"][0]
        table = section["tables"][int(table_id[1:]) - 1]
        lane = family._multitable_lane_axis(section, table, compiled_specs=compiled)
        locator = _contextual_period_locator(record) | {"table_id": table_id}
        return locator, lane.get("money_column_ordinals") or []

    first, first_columns = selector(left, left_table)
    last, last_columns = selector(right, right_table)
    return family._source_period_correspondence_receipt(
        left_locator=first, left_money_column_ordinals=first_columns,
        right_locator=last, right_money_column_ordinals=last_columns,
        page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
    )


def _public(records, compiled):
    base = coalesce_gemini_json_multitable_hierarchical_document_v1(page_records=records, compiled_specs=compiled)
    cluster = family.recover_gemini_json_income_tax_query_cluster_v1(
        page_records=records, base_cluster=base, compiled_specs=compiled,
    )
    if cluster["status"] != READY:
        return cluster, None, cluster
    query = family.build_gemini_json_income_tax_region_query_receipt_v1(cluster["component_regions"], cluster=cluster)
    return cluster, query, _evaluate_query(records, compiled, cluster, query)


def _assert_hold(candidate):
    assert candidate["status"] == UNRESOLVED, candidate.get("reasons")
    assert candidate.get("mappings", []) == []


@pytest.mark.parametrize("left,right", [(1, 1), (2, 2), (1, 2), (2, 1)])
def test_registered_note_and_independent_primary_all_self_and_cross_period_consumers(monkeypatch, left, right):
    records = _fixture_records()
    before = _positions(records)
    compiled, calls = _install_registry(monkeypatch, _registry(records))
    proof = _period(records, compiled, left, right)
    assert proof["complete"] is True, proof["reasons"]
    assert all(item["resolved_source_duration_semantics"] == [
        ["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2],
    ] for item in proof["period_resolution_evidence"])
    assert proof["source_period_keys_modified"] is False
    assert proof["amounts_used_as_authority"] is False
    assert proof["start_dates_inferred"] is False
    assert len(calls) > 1
    assert _positions(records) == before


def test_registered_part_period_reaches_signed_display_and_final_source_control_without_raw_edits(monkeypatch):
    records = _fixture_records()
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    assert inventory["registered_part_period_contexts"]
    cluster, query, candidate = _public(records, compiled)
    assert cluster["status"] == candidate["status"] == READY, candidate.get("reasons")
    assert query["source_context_receipt"]["document_statement_period_inventory"] == inventory
    adapter = candidate["closure_receipt"]["income_tax_adapter_receipt"]
    signed = adapter["primary_candidate_proof"]["signed_display_proof"]
    assert signed["note_source_tables"]
    assert all(table["source_period_correspondence_receipt"]["complete"] for table in signed["note_source_tables"])
    seal = candidate["closure_receipt"]["income_tax_source_control_receipt"]
    assert seal["primary_source_period_receipts"]
    assert seal["cross_source_mapping_period_receipts"]
    assert all(proof["complete"] for proof in seal["primary_source_period_receipts"] + seal["cross_source_mapping_period_receipts"])
    roles = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["source_text"] for cell in roles["CURRENT_TAX_PARENT"]["values"]] == ["20", "16"]
    assert [cell["source_text"] for cell in roles["FAMILY_ROOT_TOTAL"]["values"]] == ["(22)", "(17)"]
    assert _positions(records) == before
    note = records[1]["page_json"]["sections"][0]
    lane = family._multitable_lane_axis(note, note["tables"][0], compiled_specs=compiled)
    assert lane["source_lane_keys"] == [["SEMANTIC_ALIAS", "CURRENT_PERIOD"], ["SEMANTIC_ALIAS", "COMPARATIVE_PERIOD"]]


def test_registered_period_reaches_original_note_population_self_pair_and_public_seal(monkeypatch):
    records = _fixture_records(original_note=True)
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    _cluster, query, candidate = _public(records, compiled)
    assert candidate["status"] == READY, candidate.get("reasons")
    assert query["adapter_receipt"]["adapter_format_version"] == "GEMINI_JSON_INCOME_TAX_ORIGINAL_NOTE_ADAPTER_V1"
    populations = query["adapter_receipt"]["independent_population_receipt"]
    assert all(item["self_source_duration_proven"] for item in populations["populations"])
    assert populations["pairwise_proofs"]
    assert all(item["same_source_period"] and item["source_period_correspondence_receipt"]["complete"]
               for item in populations["pairwise_proofs"])
    assert candidate["closure_receipt"]["income_tax_source_control_receipt"]["primary_source_period_receipts"]
    assert _positions(records) == before


def test_unregistered_literal_note_cannot_borrow_primary_period_by_matching_values(monkeypatch):
    records = _fixture_records()
    registry = _registry(records)
    registry["contexts"] = []
    compiled, _calls = _install_registry(monkeypatch, registry)
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    assert "registered_part_period_contexts" not in inventory
    assert _period(records, compiled, 1, 1)["complete"] is False
    assert _period(records, compiled, 2, 2)["complete"] is True
    _assert_hold(_public(records, compiled)[2])


@pytest.mark.parametrize("mutation", ["wrong_table", "wrong_page", "wrong_source", "overlap"])
def test_public_registry_binding_rejects_wrong_targets_sources_or_overlapping_permissions(monkeypatch, mutation):
    records = _fixture_records()
    registry = _registry(records)
    context = registry["contexts"][0]
    if mutation == "wrong_table":
        context["target_tables"][0]["table_id"] = "t9"
    elif mutation == "wrong_page":
        context["target_tables"][0]["physical_page"] = 1
    elif mutation == "wrong_source":
        context["pdf_source"]["sha256"] = "0" * 64
    else:
        duplicate = deepcopy(context)
        duplicate["context_id"] += ":overlap"
        registry["contexts"].append(duplicate)
    with pytest.raises((family.GeminiJsonIncomeTaxFamilyV1Error, GeminiJsonIncomeTaxPartPeriodContextV1Error)):
        compiled, _calls = _install_registry(monkeypatch, registry)
        _public(records, compiled)


@pytest.mark.parametrize("mutation", ["registry", "registry_ref"])
def test_compiled_registry_or_ref_reseal_is_not_the_independent_loader_authority(monkeypatch, mutation):
    records = _fixture_records()
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    changed = deepcopy(compiled)
    if mutation == "registry":
        changed["income_tax_part_period_registry"]["contexts"][0]["context_id"] += ":forged"
    else:
        changed["income_tax_part_period_registry_ref"]["sha256"] = "0" * 64
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="authority drifted"):
        _public(records, changed)


def test_query_source_inventory_self_reseal_cannot_replace_registered_printed_period(monkeypatch):
    records = _fixture_records()
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    cluster, query, candidate = _public(records, compiled)
    assert candidate["status"] == READY, candidate.get("reasons")
    forged = deepcopy(query)
    inventory = forged["source_context_receipt"]["document_statement_period_inventory"]
    inventory["registered_part_period_contexts"][0]["resolved_source_duration_semantics"][0][1] = 2024
    for value, key in ((inventory, "receipt_id"), (forged["source_context_receipt"], "receipt_id"),
                       (forged, "query_receipt_id")):
        value[key] = value[key].rsplit(":", 1)[0] + ":" + canonical_json_sha256_v1({name: item for name, item in value.items() if name != key})
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="drifted"):
        _evaluate_query(records, compiled, cluster, forged)


def test_registry_loader_is_rechecked_after_successful_query_not_cached_as_ready(monkeypatch):
    records = _fixture_records()
    registry = _registry(records)
    compiled, calls = _install_registry(monkeypatch, registry)
    cluster, query, candidate = _public(records, compiled)
    assert candidate["status"] == READY
    previous_calls = len(calls)
    registry["contexts"][0]["context_id"] += ":changed-after-query"
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="authority drifted"):
        _evaluate_query(records, compiled, cluster, query)
    assert len(calls) > previous_calls


@pytest.mark.parametrize("mutation", ["unknown_all_scope", "note_entity", "primary_entity"])
def test_registered_calendar_pair_cannot_grant_report_scope_or_entity_population(monkeypatch, mutation):
    records = _fixture_records()
    if mutation == "unknown_all_scope":
        for record in records:
            section = record["page_json"]["sections"][0]
            if section["title_exact"] is not None:
                section["title_exact"] = section["title_exact"].replace(" riêng", "")
    else:
        section = records[1 if mutation == "note_entity" else 2]["page_json"]["sections"][0]
        section["tables"][0]["rows"][0]["hierarchy_path_exact"].insert(0, "Công ty con")
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    _assert_hold(_public(records, compiled)[2])
    assert _positions(records) == before


@pytest.mark.parametrize("surface", ["section_title", "table_title", "narrative", "ancestor"])
def test_registered_dates_cannot_override_contrary_local_source_assertions(monkeypatch, surface):
    records = _fixture_records()
    section = records[1]["page_json"]["sections"][0]
    contrary = "Cho kỳ hoạt động 3 tháng kết thúc ngày 31 tháng 3 năm 2026"
    if surface == "section_title":
        section["title_exact"] += "\n" + contrary
    elif surface == "table_title":
        section["tables"][0]["title_exact"] = contrary
    elif surface == "narrative":
        section["narratives_exact"].append(contrary)
    else:
        section["tables"][0]["rows"][0]["hierarchy_path_exact"].insert(0, contrary)
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    assert _period(records, compiled, 1, 1)["complete"] is False
    _assert_hold(_public(records, compiled)[2])
    assert _positions(records) == before


def test_unknown_raw_columns_are_retained_not_promoted_by_registered_period_context(monkeypatch):
    records = _fixture_records()
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    for column in table["columns"]:
        column["value_kind"] = "UNKNOWN"
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    assert inventory["registered_part_period_contexts"]
    context = inventory["registered_part_period_contexts"][0]
    assert context["column_value_kinds"] == ["UNKNOWN", "UNKNOWN"]
    assert context["permission_grants"]["unit"] is False
    assert context["unknown_columns_promoted"] is False
    assert _period(records, compiled, 1, 1)["complete"] is True
    assert compiled["accepted_value_column_kinds"] == ["MONEY", "UNKNOWN"]
    _cluster, _query, candidate = _public(records, compiled)
    assert candidate["status"] == READY, candidate.get("reasons")
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"MILLION_VND"}
    current = next(mapping for mapping in candidate["mappings"] if mapping["role"] == "CURRENT_TAX_PARENT")
    assert [cell["source_text"] for cell in current["values"]] == ["20", "16"]
    seal = candidate["closure_receipt"]["income_tax_source_control_receipt"]
    assert seal["primary_source_period_receipts"] and seal["cross_source_mapping_period_receipts"]
    assert all(proof["complete"] for proof in seal["primary_source_period_receipts"] + seal["cross_source_mapping_period_receipts"])
    assert [column["value_kind"] for column in table["columns"]] == ["UNKNOWN", "UNKNOWN"]
    assert _positions(records) == before


def _append_cash_flow(records, *, mode="relative", physical=4):
    page = _primary_page([_row("Lưu chuyển tiền thuần từ hoạt động kinh doanh", "7", "8")])
    section = page["sections"][0]
    section["statement_type"] = "CASH_FLOW"
    section["title_exact"] = "Báo cáo lưu chuyển tiền tệ riêng"
    table = section["tables"][0]
    table["columns"] = [{"value_kind": "MONEY", "header_path_exact": [label]}
                        for label in ("Kỳ này", "Kỳ trước")]
    if mode != "relative":
        first = ["Kỳ 6 tháng kết thúc ngày", "30/6/2026", "Triệu đồng"]
        if mode == "wrong_duration":
            first = ["Kỳ 3 tháng kết thúc ngày", "31/3/2026", "Triệu đồng"]
        elif mode == "wrong_current_year":
            first[1] = "30/6/2024"
        elif mode == "wrong_current_endpoint":
            first[1] = "31/3/2026"
        table["columns"][0]["header_path_exact"] = first
        if mode == "matching":
            table["columns"][1]["header_path_exact"] = ["Kỳ 6 tháng kết thúc ngày", "30/6/2025", "Triệu đồng"]
    records.append(_primary_record(
        page, page_json_version_id="gfpstorev1:json:" + str(physical) * 64,
        physical_page=physical, selected_page_ordinal=physical,
    ))


@pytest.mark.parametrize("mode", ["relative", "current_known_comparative_unknown"])
def test_cf_unknown_pair_cannot_erase_independently_printed_primary_period_or_supply_authority(monkeypatch, mode):
    records = _fixture_records()
    _append_cash_flow(records, mode=mode)
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    proof = _period(records, compiled)
    assert proof["complete"] is True, proof["reasons"]
    assert all(item["cash_flow_used_as_period_authority"] is False for item in proof["period_resolution_evidence"])
    _cluster, _query, candidate = _public(records, compiled)
    assert candidate["status"] == READY, candidate.get("reasons")
    assert _positions(records) == before


@pytest.mark.parametrize("mode", ["wrong_duration", "wrong_current_year", "wrong_current_endpoint"])
def test_positive_cf_current_conflict_vetoes_even_when_comparative_period_unknown(monkeypatch, mode):
    records = _fixture_records()
    _append_cash_flow(records, mode=mode)
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    assert _period(records, compiled, 2, 2)["complete"] is False
    _assert_hold(_public(records, compiled)[2])
    assert _positions(records) == before


def test_one_contrary_cf_continuation_is_not_hidden_by_a_matching_first_table(monkeypatch):
    records = _fixture_records()
    _append_cash_flow(records, mode="matching")
    _append_cash_flow(records, mode="wrong_duration", physical=5)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    assert _period(records, compiled, 2, 2)["complete"] is False
    _assert_hold(_public(records, compiled)[2])


def test_relative_primary_without_its_own_independent_absolute_authority_stays_unresolved(monkeypatch):
    records = _fixture_records(absolute_primary=False)
    _append_cash_flow(records, mode="relative")
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    assert _period(records, compiled, 1, 1)["complete"] is True
    assert _period(records, compiled, 2, 2)["complete"] is False
    _assert_hold(_public(records, compiled)[2])


def _unknown_note(records):
    table = records[1]["page_json"]["sections"][0]["tables"][0]
    for column in table["columns"]:
        column["value_kind"] = "UNKNOWN"
    return table


def test_registered_unknown_period_does_not_supply_missing_local_or_independent_money_unit(monkeypatch):
    records = _fixture_records()
    table = _unknown_note(records)
    for record in records:
        for section in record["page_json"]["sections"]:
            for source_table in section["tables"]:
                source_table["unit_exact"] = None
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    assert _period(records, compiled, 1, 1)["complete"] is True
    assert family._primary_statement_unit_corroboration(records, compiled_specs=compiled) is None
    unit_axis = family._unit_axis(table, compiled_specs=compiled)
    assert unit_axis["complete"] is False
    assert family._local_money_unit_is_truly_absent(unit_axis) is True
    assert family._supplemental_presentations(records, compiled_specs=compiled) == []
    _assert_hold(_public(records, compiled)[2])
    assert [column["value_kind"] for column in table["columns"]] == ["UNKNOWN", "UNKNOWN"]
    assert _positions(records) == before


@pytest.mark.parametrize("unit", ["Nghìn đồng", "Triệu VND / Đồng"])
def test_registered_unknown_note_only_period_cannot_replace_unsupported_or_conflicting_unit(monkeypatch, unit):
    # Isolate the NOTE gate: a different independently valid PRIMARY may retain
    # its own mappings under the existing supplemental-fallback contract.
    records = _fixture_records()[:2]
    table = _unknown_note(records)
    table["unit_exact"] = unit
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    assert _period(records, compiled, 1, 1)["complete"] is True
    unit_axis = family._unit_axis(table, compiled_specs=compiled)
    assert unit_axis["complete"] is False
    assert unit_axis["evidence"] or unit_axis["undeclared_evidence"]
    assert family._local_money_unit_is_truly_absent(unit_axis) is False
    assert family._supplemental_presentations(records, compiled_specs=compiled) == []
    assert family._primary_statement_unit_corroboration(records, compiled_specs=compiled) is None
    _assert_hold(_public(records, compiled)[2])
    assert [column["value_kind"] for column in table["columns"]] == ["UNKNOWN", "UNKNOWN"]
    assert _positions(records) == before


def test_registered_unknown_columns_do_not_grant_tax_owner_permission(monkeypatch):
    records = _fixture_records()[:2]
    table = _unknown_note(records)
    section = records[1]["page_json"]["sections"][0]
    section["title_exact"] = "Tình hình thu nhập của cán bộ, nhân viên riêng"
    table["title_exact"] = "Tình hình thu nhập của cán bộ, nhân viên"
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    inventory = family._document_statement_period_inventory(records, compiled_specs=compiled)
    assert inventory["registered_part_period_contexts"][0]["column_value_kinds"] == ["UNKNOWN", "UNKNOWN"]
    lane = family._multitable_lane_axis(section, table, compiled_specs=compiled)
    receipt = family._registered_part_period_receipt(
        section, table, lane, locator=_contextual_period_locator(records[1]),
        page_records=records, compiled_specs=compiled, document_period_inventory=inventory,
    )
    assert receipt["complete"] is False
    assert "REGISTERED_PART_PERIOD_TAX_OWNER_NOT_PROVEN" in receipt["reasons"]
    assert _period(records, compiled, 1, 1)["complete"] is False
    assert _positions(records) == before


def _unrelated_control_records(records):
    unrelated = deepcopy(records)
    for record in unrelated:
        record.update(document_id="gfpstorev1:document:" + "e" * 64,
                      source_logical_name="unrelated-unit-control.pdf", source_sha256="b" * 64)
    # This legacy control is deliberately not a registered-part source shape.
    # The wrapper must grant no authority, not deep-validate unrelated rows.
    unrelated[1]["page_json"]["sections"][0]["tables"][0]["rows"] = [{"legacy_unit_control": True}]
    return unrelated


def test_registry_wrapper_unrelated_legacy_unit_control_receives_no_period_authority(monkeypatch):
    records = _fixture_records()
    compiled, calls = _install_registry(monkeypatch, _registry(records))
    unrelated = _unrelated_control_records(records)
    before = _positions(unrelated)
    previous_calls = len(calls)
    assert family._registered_part_period_contexts_v1(unrelated, compiled_specs=compiled) == []
    assert len(calls) > previous_calls
    assert _positions(unrelated) == before


@pytest.mark.parametrize("identity_key", ["document_id", "source_logical_name", "source_sha256"])
def test_registry_wrapper_any_partial_source_identity_match_keeps_strict_validation(monkeypatch, identity_key):
    records = _fixture_records()
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    partial = _unrelated_control_records(records)
    for record in partial:
        record[identity_key] = records[0][identity_key]
    before = _positions(partial)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="source binding drifted"):
        family._registered_part_period_contexts_v1(partial, compiled_specs=compiled)
    assert _positions(partial) == before


@pytest.mark.parametrize("mutation", ["registry", "registry_ref"])
def test_registry_wrapper_checks_fresh_authority_before_unrelated_source_shortcut(monkeypatch, mutation):
    records = _fixture_records()
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    changed = deepcopy(compiled)
    if mutation == "registry":
        changed["income_tax_part_period_registry"]["contexts"][0]["context_id"] += ":forged"
    else:
        changed["income_tax_part_period_registry_ref"]["sha256"] = "0" * 64
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="authority drifted"):
        family._registered_part_period_contexts_v1(_unrelated_control_records(records), compiled_specs=changed)


def _note_report_quarter_caption(*, quarter="II", year=2026, scope="riêng", interim=False):
    return (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH"
        + (" " + scope if scope else "")
        + (" GIỮA NIÊN ĐỘ" if interim else "")
        + "\nQUÝ " + quarter + " NĂM " + str(year)
    )


def _note_report_quarter_constraint(raw, *, source_kind="SECTION_TITLE", section=None):
    if section is None:
        section = {"content_kind": "FINANCIAL_NOTE", "statement_type": "NOT_APPLICABLE"}
    return family._owned_note_report_quarter_constraint_v1(
        section, source_kind=source_kind, source_exact=raw,
    )


@pytest.mark.parametrize("quarter,number", [("I", 1), ("II", 2), ("III", 3), ("IV", 4)])
@pytest.mark.parametrize("source_kind", ["SECTION_TITLE", "TABLE_TITLE"])
@pytest.mark.parametrize("form", ["NFC", "NFD"])
def test_note_report_quarter_whole_typed_caption_is_endpoint_only(quarter, number, source_kind, form):
    raw = unicodedata.normalize(form, _note_report_quarter_caption(quarter=quarter))
    receipt = _note_report_quarter_constraint(raw, source_kind=source_kind)
    assert receipt["supported"] is True
    assert receipt["printed_reporting_quarter"] == number and receipt["printed_year"] == 2026
    assert "printed_months" not in receipt and "printed_start_date" not in receipt
    evidence = receipt["source_note_report_quarter_evidence"]
    assert evidence["source_exact"] == raw
    assert evidence["source_sha256"] == sha256(raw.encode("utf-8")).hexdigest()
    assert evidence["endpoint_only"] is True
    assert all(evidence[name] is False for name in (
        "duration_permission_granted", "report_scope_permission_granted", "entity_permission_granted",
        "unit_permission_granted", "comparative_year_permission_granted", "registry_permission_granted",
        "source_values_modified", "amounts_used_as_authority", "start_dates_inferred",
        "source_period_keys_modified",
    ))
    material = {key: value for key, value in evidence.items() if key != "receipt_id"}
    assert evidence["receipt_id"] == "gjitfav1:owned-note-report-quarter:" + canonical_json_sha256_v1(material)


@pytest.mark.parametrize("layout", ["serialized", "crlf", "tabs", "nbsp", "upper", "interim_continued", "unqualified"])
def test_note_report_quarter_finite_layout_preserves_all_source_bytes(layout):
    raw = _note_report_quarter_caption()
    if layout == "serialized":
        raw = raw.replace("\n", "\\n")
    elif layout == "crlf":
        raw = raw.replace("\n", "\r\n")
    elif layout == "tabs":
        raw = raw.replace(" ", "\t")
    elif layout == "nbsp":
        raw = raw.replace(" ", "\u00a0")
    elif layout == "upper":
        raw = raw.upper()
    elif layout == "interim_continued":
        raw = _note_report_quarter_caption(scope="hợp nhất", interim=True) + " (tiếp theo)"
    else:
        raw = _note_report_quarter_caption(scope="")
    receipt = _note_report_quarter_constraint(raw)
    assert receipt["supported"] is True
    assert receipt["source_note_report_quarter_evidence"]["source_exact"] == raw


@pytest.mark.parametrize("mutation", [
    "prefix", "entity_prefix", "suffix", "second_clause", "year_suffix", "unicode_quarter",
    "accented_quarter", "fullwidth_year", "year_combining", "year_zero", "quarter_zero", "quarter_v",
    "zwsp", "bom", "vt", "ff", "nel",
])
def test_note_report_quarter_relevant_malformed_source_stays_unsupported(mutation):
    raw = _note_report_quarter_caption()
    if mutation == "prefix":
        raw = "Mẫu số B05/TCTD\n" + raw
    elif mutation == "entity_prefix":
        raw = "Ngân hàng mẹ\n" + raw
    elif mutation == "suffix":
        raw += " cho bộ phận kinh doanh"
    elif mutation == "second_clause":
        raw += "\nQUÝ I NĂM 2026"
    elif mutation == "year_suffix":
        raw += "*"
    elif mutation == "unicode_quarter":
        raw = raw.replace("QUÝ II", "QUÝ Ⅱ")
    elif mutation == "accented_quarter":
        raw = raw.replace("QUÝ II", "QUÝ I\u0301I")
    elif mutation == "fullwidth_year":
        raw = raw.replace("2026", "２０２６")
    elif mutation == "year_combining":
        raw = raw.replace("2026", "2026\u0301")
    elif mutation == "year_zero":
        raw = raw.replace("2026", "0000")
    elif mutation == "quarter_zero":
        raw = raw.replace("QUÝ II", "QUÝ 0")
    elif mutation == "quarter_v":
        raw = raw.replace("QUÝ II", "QUÝ V")
    else:
        char = {"zwsp": "\u200b", "bom": "\ufeff", "vt": "\v", "ff": "\f", "nel": "\x85"}[mutation]
        raw = raw.replace("\n", char)
    receipt = _note_report_quarter_constraint(raw)
    assert receipt is not None and receipt["supported"] is False
    evidence = receipt["source_note_report_quarter_evidence"]
    assert evidence["reasons"] and evidence["source_exact"] == raw
    assert "printed_reporting_quarter" not in receipt and "printed_year" not in receipt


@pytest.mark.parametrize("content_kind,statement_type,source_kind", [
    ("PRIMARY_STATEMENT", "INCOME_STATEMENT", "SECTION_TITLE"),
    ("FINANCIAL_NOTE", "NOTES", "SECTION_TITLE"),
    ("FINANCIAL_NARRATIVE", "NOT_APPLICABLE", "SECTION_TITLE"),
    ("FINANCIAL_NOTE", "NOT_APPLICABLE", "OWNED_NARRATIVE"),
    ("FINANCIAL_NOTE", "NOT_APPLICABLE", "SOURCE_ROW_ANCESTOR"),
])
def test_note_report_quarter_never_waives_other_typed_carriers(content_kind, statement_type, source_kind):
    section = {"content_kind": content_kind, "statement_type": statement_type}
    assert _note_report_quarter_constraint(
        _note_report_quarter_caption(), source_kind=source_kind, section=section,
    ) is None


def _registered_note_report_quarter_records(*, serialized=False):
    records = _fixture_records()
    section = records[1]["page_json"]["sections"][0]
    section["title_exact"] = _note_report_quarter_caption()
    if serialized:
        section["title_exact"] = section["title_exact"].replace("\n", "\\n")
    section["tables"][0]["title_exact"] = "32. Chi phí thuế thu nhập doanh nghiệp"
    return records


@pytest.mark.parametrize("left,right", [(1, 1), (1, 2), (2, 1)])
@pytest.mark.parametrize("serialized", [False, True])
def test_registered_whole_note_report_endpoint_keeps_self_and_cross_period_proofs(monkeypatch, left, right, serialized):
    records = _registered_note_report_quarter_records(serialized=serialized)
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    proof = _period(records, compiled, left, right)
    assert proof["complete"] is True, proof["reasons"]
    assert all(item["resolved_source_duration_semantics"] == [
        ["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2],
    ] for item in proof["period_resolution_evidence"])
    note_receipt = next(
        item["registered_part_period_receipt"] for item in proof["period_resolution_evidence"]
        if item["registered_part_period_receipt"] is not None
    )
    caption = next(item for item in note_receipt["local_period_surface_census"] if item["kind"] == "SECTION_TITLE")
    assert caption["finite_owned_note_reporting_quarter_endpoint_caption"] is True
    assert caption["owned_note_report_quarter_caption_evidence"]["source_exact"] == records[1]["page_json"]["sections"][0]["title_exact"]
    assert _positions(records) == before


@pytest.mark.parametrize("serialized", [False, True])
def test_registered_whole_note_report_endpoint_reaches_signed_display_and_final_seal(monkeypatch, serialized):
    records = _registered_note_report_quarter_records(serialized=serialized)
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    _cluster, _query, candidate = _public(records, compiled)
    assert candidate["status"] == READY, candidate.get("reasons")
    signed = candidate["closure_receipt"]["income_tax_adapter_receipt"]["primary_candidate_proof"]["signed_display_proof"]
    assert signed["note_source_tables"]
    assert all(item["source_period_correspondence_receipt"]["complete"] for item in signed["note_source_tables"])
    seal = candidate["closure_receipt"]["income_tax_source_control_receipt"]
    assert seal["primary_source_period_receipts"] and seal["cross_source_mapping_period_receipts"]
    assert all(item["complete"] for item in seal["primary_source_period_receipts"] + seal["cross_source_mapping_period_receipts"])
    assert _positions(records) == before


def test_note_report_endpoint_without_registered_or_other_period_authority_stays_hold(monkeypatch):
    records = _registered_note_report_quarter_records()
    registry = _registry(records)
    registry["contexts"] = []
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, registry)
    assert _period(records, compiled, 1, 1)["complete"] is False
    _assert_hold(_public(records, compiled)[2])
    assert _positions(records) == before


@pytest.mark.parametrize("surrogate", ["\ud800", "\udfff"])
def test_note_report_quarter_noncanonical_surrogate_cannot_create_a_source_receipt(surrogate):
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="noncanonical surrogate"):
        _note_report_quarter_constraint(_note_report_quarter_caption() + surrogate)


@pytest.mark.parametrize("quarter,year", [("I", 2026), ("II", 2025), ("IV", 2026)])
def test_note_report_endpoint_must_match_independently_printed_current_window(monkeypatch, quarter, year):
    records = _registered_note_report_quarter_records()
    records[1]["page_json"]["sections"][0]["title_exact"] = _note_report_quarter_caption(quarter=quarter, year=year)
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    assert _period(records, compiled, 1, 1)["complete"] is False
    _assert_hold(_public(records, compiled)[2])
    assert _positions(records) == before


@pytest.mark.parametrize("carrier", ["ancestor", "narrative"])
def test_note_report_caption_endpoint_permission_does_not_extend_to_other_surfaces(monkeypatch, carrier):
    records = _fixture_records()
    section = records[1]["page_json"]["sections"][0]
    raw = _note_report_quarter_caption()
    if carrier == "ancestor":
        section["tables"][0]["rows"][0]["hierarchy_path_exact"].insert(0, raw)
    else:
        section["narratives_exact"].append(raw)
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    assert _period(records, compiled, 1, 1)["complete"] is False
    _assert_hold(_public(records, compiled)[2])
    assert _positions(records) == before


def test_note_report_endpoint_does_not_supply_unknown_report_scope(monkeypatch):
    records = _registered_note_report_quarter_records()
    for record in records:
        for section in record["page_json"]["sections"]:
            if section["title_exact"] is not None:
                section["title_exact"] = section["title_exact"].replace(" riêng", "").replace(" RIÊNG", "")
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    assert _period(records, compiled, 1, 1)["complete"] is False
    _assert_hold(_public(records, compiled)[2])
    assert _positions(records) == before


@pytest.mark.parametrize("quarter,number", [("I", 1), ("II", 2)])
def test_finite_legacy_note_cho_quarter_keeps_existing_parser_without_endpoint_exemption(quarter, number):
    raw = _note_report_quarter_caption(quarter=quarter).replace("QUÝ", "CHO QUÝ")
    assert _note_report_quarter_constraint(raw) is None
    section = {"content_kind": "FINANCIAL_NOTE", "statement_type": "NOT_APPLICABLE",
               "title_exact": raw, "tables": [], "narratives_exact": []}
    constraints = family._owned_current_period_constraints(section, {})
    assert len(constraints) == 1 and constraints[0]["supported"] is True
    assert constraints[0]["printed_reporting_quarter"] == number
    assert "source_note_report_quarter_evidence" not in constraints[0]


@pytest.mark.parametrize("suffix", ["*", "\u200b", " cho bộ phận kinh doanh"])
def test_malformed_legacy_note_cho_quarter_cannot_defer_to_punctuation_normalizer(suffix):
    raw = _note_report_quarter_caption(quarter="I").replace("QUÝ", "CHO QUÝ") + suffix
    assert _note_report_quarter_constraint(raw)["supported"] is False


def test_legacy_note_cho_quarter_cannot_relabel_registered_half_year(monkeypatch):
    records = _registered_note_report_quarter_records()
    section = records[1]["page_json"]["sections"][0]
    section["title_exact"] = section["title_exact"].replace("QUÝ", "CHO QUÝ")
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    assert _period(records, compiled, 1, 1)["complete"] is False
    _assert_hold(_public(records, compiled)[2])
    assert _positions(records) == before


def test_serialized_note_caption_with_unknown_extra_clause_still_holds(monkeypatch):
    records = _registered_note_report_quarter_records(serialized=True)
    records[1]["page_json"]["sections"][0]["title_exact"] += "\\ncho bộ phận kinh doanh"
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    assert _period(records, compiled, 1, 1)["complete"] is False
    _assert_hold(_public(records, compiled)[2])


def test_note_report_endpoint_cannot_hide_conflicting_printed_report_scope(monkeypatch):
    records = _registered_note_report_quarter_records()
    records[1]["page_json"]["sections"][0]["title_exact"] = _note_report_quarter_caption(scope="hợp nhất")
    before = _positions(records)
    compiled, _calls = _install_registry(monkeypatch, _registry(records))
    # Independently printed dates may coincide across different populations.
    # A temporal receipt must retain that distinction, not grant merge scope.
    period = _period(records, compiled, 1, 2)
    assert period["complete"] is True and period["reasons"] == []
    assert period["status"] == "PASS_REGISTERED_PART_SOURCE_PERIOD_PAIR"
    scopes = [item["scope_receipt"] for item in period["source_selectors"]]
    assert [item["report_scope"] for item in scopes] == ["CONSOLIDATED", "SEPARATE"]
    assert all(not item["conflict"] and item["origin"] == "LOCAL_PRINTED_SOURCE" for item in scopes)
    assert records[1]["page_json"]["sections"][0]["title_exact"] in scopes[0]["source_surfaces_exact"]
    assert family._document_report_scope_receipt(records)["report_scope"] is None
    assert all(item["resolved_source_duration_semantics"] == [
        ["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2025, 2],
    ] for item in period["period_resolution_evidence"])
    registered = [item["registered_part_period_receipt"] for item in period["period_resolution_evidence"]
                  if item["registered_part_period_receipt"] is not None]
    assert registered
    assert all(item["report_scope_permission_granted"] is False
               and item["registered_source_context"]["permission_grants"]["report_scope"] is False
               for item in registered)
    # The public mapping gate, unlike the dates-only comparison, must refuse
    # to combine CONSOLIDATED NOTE with SEPARATE PRIMARY and emit no mapping.
    _assert_hold(_public(records, compiled)[2])
    assert _positions(records) == before
