"""UNRUN source-only F30 controls; exact packet contexts never access a store."""
from __future__ import annotations

import copy
import json
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_service_activity_adapter_v1 import (
    _compiled,
    _page_record,
    _two_parent_service_page_without_explicit_root,
    _unit_control_page,
)

from bctc_ai.evaluation import gemini_json_service_activity_family_v1 as family
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    READY,
    UNRESOLVED,
    classify_gemini_json_multitable_hierarchical_table_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (
    audit_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/source_structure/f30-sgb-printed-net-20261028-v1"
VERSION = "gfpstorev1:json:0c49ade72e727b7fc02b44a3f95b519e48c8d4d90dc87ed0b9ca1de5357b12f5"


def _decode(envelope):
    payload = envelope["canonical_json"].encode("utf-8")
    assert len(payload) == envelope["size_bytes"]
    assert sha256(payload).hexdigest() == envelope["sha256"]
    decoded = json.loads(payload)
    assert canonical_json_bytes_v1(decoded) == payload
    return decoded


def _packet_options():
    raw = (FIXTURES / "packet.json").read_bytes()
    assert sha256(raw).hexdigest() == "85771acdfdd2dbea87f97e170dec3d01caf8a7ef24e4891a371eb97e44581a47"
    packet = json.loads(raw)
    original = packet["candidates"][0]["candidate_bytes"]
    assert canonical_json_sha256_v1(original) == packet["candidates"][0]["candidate_sha256"]
    page_raw = (FIXTURES / "page-033-0c49ade72e727b7f.json").read_bytes()
    assert len(page_raw) == 6490
    assert sha256(page_raw).hexdigest() == "f61d8367c2496943faa655f4d3742f2afb5c1a2e3ad3717c48afb6f716466c3a"
    excerpt_raw = (FIXTURES / "selected-axis-p33.json").read_bytes()
    assert sha256(excerpt_raw).hexdigest() == "a9f60c23587484ca21c8d8f89b48774ef6a31e8f1af2474ca9badca47b922b81"
    excerpt = json.loads(excerpt_raw)
    page_entry = next(item for item in excerpt["document_manifest_ref_entries"] if item["json_path"] == "/pages[32]")
    assert page_entry["page_json_version_id"] == VERSION
    assert page_entry["canonical_json_sha256"] == sha256(page_raw).hexdigest()
    assert excerpt["document"]["source_ordinal"] == 147
    assert original["component_regions"][0]["selected_page_ordinal"] == 33
    assert packet["family_run"][0]["implementation_axis_sha256"] == "ac6158571c9ae7881e2a5a0148e5a83539dae8bf5d901d2105eb5efdc4df47db"
    assert next(item for item in packet["family_run"][0]["implementation_refs_json"]
                if item["path"].endswith("gemini_json_service_activity_family_v1.py"))["sha256"] == (
        "18a3e57cdd82ee70fd65a8b623af8c27077281e4e35561ed0dcf0d3a3437ddd8"
    )  # Old producer evidence; never asserted to be the changed source.
    return packet, {
        "regions": copy.deepcopy(original["component_regions"]),
        "page_json_by_version": {VERSION: json.loads(page_raw)},
        "compiled_specs": _compiled(),
        "query_receipt": copy.deepcopy(original["closure_receipt"]["query_receipt"]),
    }


def _before_controls(options):
    compiled, regions = options["compiled_specs"], options["regions"]
    pages, _repairs = family._apply_authenticated_source_repairs_v1(
        regions=regions, page_json_by_version=options["page_json_by_version"], compiled_specs=compiled,
    )
    contexts = family._apply_registered_page_unit_contexts_v1(
        original_pages=options["page_json_by_version"], pages=pages,
        regions=regions, compiled_specs=compiled,
    )
    family._normalize_governed_duration_headers_v1(pages=pages, regions=regions)
    family._bind_exact_primary_statement_units_v1(pages=pages, regions=regions, compiled_specs=compiled)
    initial = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions, page_json_by_version=pages, compiled_specs=compiled,
        query_receipt=options["query_receipt"],
    )
    candidate, fallback = family._evaluate_root_alternative_legacy_fallback_v1(
        initial_candidate=initial, regions=regions, pages=pages,
        compiled_specs=compiled, query_receipt=options["query_receipt"],
    )
    assert candidate["status"] == READY, candidate["reasons"]
    return candidate, fallback, contexts, pages


def _control(candidate):
    return candidate["closure_receipt"]["service_activity_adapter_receipt"]["printed_net_source_control_receipt"]


def _root(candidate):
    return next(item for item in candidate["mappings"] if item["role"] == "FAMILY_ROOT_TOTAL")


def test_actual_packet_printed_net_replaces_global_sum_with_unsigned_expenses_unchanged():
    packet, options = _packet_options()
    original = copy.deepcopy(options["page_json_by_version"])
    before, fallback, contexts, private = _before_controls(options)
    assert [cell["coefficient"] for cell in _root(before)["values"]] == [73896, 69886]
    actual = family.evaluate_gemini_json_service_activity_family_cluster_v1(**options)
    assert actual["status"] == READY, actual["reasons"]
    root = _root(actual)
    region = options["regions"][0]
    assert root["source_refs"] == [{"locator": region, "row_ordinal": 10, "row_id": "r10", "row_kind": "TOTAL",
        "label_exact": "Lãi/lỗ thuần từ hoạt động dịch vụ",
        "hierarchy_path_exact": ["Lãi/lỗ thuần từ hoạt động dịch vụ"], "money_column_ordinals": [1, 2]}]
    assert root["values"] == [
        {"coefficient": 29278, "source_text": "29.278", "state": "RAW_SIGNED_INTEGER"},
        {"coefficient": 25222, "source_text": "25.222", "state": "RAW_SIGNED_INTEGER"},
    ]
    assert [item for item in actual["mappings"] if item["role"] != "FAMILY_ROOT_TOTAL"] == [
        item for item in packet["candidates"][0]["candidate_bytes"]["mappings"] if item["role"] != "FAMILY_ROOT_TOTAL"
    ]
    expense = next(item for item in actual["mappings"] if item["role"] == "EXPENSE_PARENT")
    assert [cell["source_text"] for cell in expense["values"]] == ["22.309", "22.332"]
    assert [cell["coefficient"] for cell in expense["values"]] == [22309, 22332]
    receipt = _control(actual)
    retired = _decode(receipt["retired_root_authority"])
    kind = "EXACT_COMPLETE_TOP_LEVEL_COMPONENT_SUM_DERIVES_FAMILY_ROOT"
    assert retired["root_mappings"] == [_root(before)]
    assert retired["global_root_equations"] == [item for item in before["closure_receipt"]["equations"] if item["equation_kind"] == kind]
    assert retired["root_permissions"] == before["closure_receipt"]["root_component_sum_receipts"]
    assert retired["fallback_permission"] == fallback
    assert retired["structural_root_receipt"] == before["closure_receipt"]["structural_root_receipt"]
    assert actual["closure_receipt"]["equations"] == [item for item in before["closure_receipt"]["equations"] if item["equation_kind"] != kind]
    assert actual["closure_receipt"]["root_component_sum_receipts"] == []
    assert actual["closure_receipt"]["structural_root_receipt"] == {
        "emitted_mapping": True, "mapping_policy": "EXACT_SOURCE_OWNED_PRINTED_NET_TOTAL_ONLY",
        "report_norm_id": 5989, "role": "NET_SERVICE_ACTIVITY",
        "source_control_receipt_id": receipt["receipt_id"],
        "source_total_mapping_id": root["item_mapping_id"],
        "active_permission": "SOURCE_OWNED_PRINTED_NET_ROW",
    }
    assert "root_alternative_legacy_fallback_receipt" not in actual["closure_receipt"]["service_activity_adapter_receipt"]
    assert receipt["direct_printed_net_binding"]["comparison_only_parent_orientations"] == [-1]
    assert receipt["source_values_changed"] is False and receipt["withheld_mappings"] is None
    assert len(contexts) == 1
    compiled = options["compiled_specs"]
    assert contexts[0]["compiled_context_sha256"] == compiled["service_activity_page_unit_context_compiled_sha256"] == canonical_json_sha256_v1({
        "family_id": "SERVICE_ACTIVITY", "registry_sha256": family._PAGE_UNIT_CONTEXT_REGISTRY_SHA256,
        "registry": compiled["service_activity_page_unit_context_registry"],
    })
    assert original[VERSION]["sections"][0]["tables"][3]["unit_exact"] is None
    assert private[VERSION]["sections"][0]["tables"][3]["unit_exact"] == "Triệu Đồng Việt Nam"
    assert private[VERSION]["sections"][0]["tables"][:3] == original[VERSION]["sections"][0]["tables"][:3]
    assert original[VERSION]["sections"][0]["tables"][0]["unit_exact"] == "ĐVT: Triệu cổ phiếu"
    assert audit_source_observation_mapping_contract_v1(actual)["mapping_count"] == len(actual["mappings"]) == 10
    assert family.validate_gemini_json_service_activity_family_candidate_replay_v1(actual, **options) == actual
    assert options["page_json_by_version"] == original


def test_registered_page_unit_context_binds_two_lf_store_blob_and_one_lf_tables():
    _, options = _packet_options()
    page = options["page_json_by_version"][VERSION]
    original = copy.deepcopy(page)
    raw = (FIXTURES / "page-033-0c49ade72e727b7f.json").read_bytes()
    object_bytes = canonical_json_bytes_v1(page)
    assert len(object_bytes) == 6489 and object_bytes.endswith(b"}\n")
    assert sha256(object_bytes).hexdigest() == "4330f03a88aa4eceefeb7609307bccc132cd808a0deeefe4bb3976d21f3a52ed"
    assert object_bytes + b"\n" == raw and raw.endswith(b"}\n\n")
    context = options["compiled_specs"]["service_activity_page_unit_context_registry"]["contexts"][0]
    assert context["source"]["original_page_json_sha256"] == sha256(raw).hexdigest()
    assert context["source"]["original_page_json_size_bytes"] == len(raw) == 6490
    table = page["sections"][0]["tables"][3]
    assert canonical_json_sha256_v1(table) == context["target"]["original_table_json_sha256"]
    assert len(canonical_json_bytes_v1(table)) == context["target"]["original_table_json_size_bytes"] == 2187
    private = copy.deepcopy(options["page_json_by_version"])
    receipts = family._apply_registered_page_unit_contexts_v1(
        original_pages=options["page_json_by_version"], pages=private,
        regions=options["regions"], compiled_specs=options["compiled_specs"],
    )
    assert len(receipts) == 1
    assert receipts[0]["original_page_json_encoding"] == (
        "GEMINI_FINANCIAL_PAGE_STORE_V1_CANONICAL_JSON_PLUS_ONE_LF_BLOB"
    )
    assert receipts[0]["original_page_json_size_bytes"] == 6490
    assert page == original
    projected = private[VERSION]["sections"][0]["tables"][3]
    assert canonical_json_sha256_v1(projected) == context["target"]["proposed_private_table_json_sha256"]
    assert len(canonical_json_bytes_v1(projected)) == context["target"]["proposed_private_table_json_size_bytes"] == 2211


@pytest.mark.parametrize("blob_lf_count", [1, 3])
def test_registered_page_unit_context_rejects_other_page_encoding_domains(monkeypatch, blob_lf_count):
    _, options = _packet_options()
    page = options["page_json_by_version"][VERSION]
    original = copy.deepcopy(options["page_json_by_version"])
    canonical_serializer = family.canonical_json_bytes_v1

    def wrong_page_domain(value):
        encoded = canonical_serializer(value)
        if value is page:
            # The production page-store boundary adds one LF. Inject only
            # the page serializer domain; all approved registry/table bytes
            # and their independent pins remain unchanged.
            return encoded[:-1] if blob_lf_count == 1 else encoded + b"\n"
        return encoded

    private = copy.deepcopy(options["page_json_by_version"])
    monkeypatch.setattr(family, "canonical_json_bytes_v1", wrong_page_domain)
    with pytest.raises(family.GeminiJsonServiceActivityFamilyV1Error,
                       match="original before-image or explicit override drifted"):
        family._apply_registered_page_unit_contexts_v1(
            original_pages=options["page_json_by_version"], pages=private,
            regions=options["regions"], compiled_specs=options["compiled_specs"],
        )
    assert options["page_json_by_version"] == original and private == original


def test_actual_unknown_unit_cannot_use_old_numeric_primary_receipt_without_registered_context():
    packet, options = _packet_options()
    before = copy.deepcopy(packet["candidates"][0]["candidate_bytes"])
    actual, proof, fallback = family._apply_printed_net_source_controls_v1(
        before, original_pages=options["page_json_by_version"], regions=options["regions"],
        compiled_specs=options["compiled_specs"], root_fallback_receipt=before["closure_receipt"][
            "service_activity_adapter_receipt"]["root_alternative_legacy_fallback_receipt"],
    )
    assert actual["status"] == UNRESOLVED and actual["mappings"] == [] and fallback is None
    assert proof["failures"] == ["SOURCE_LOCAL_UNIT_NOT_OWNED"]
    assert _decode(proof["withheld_mappings"]) == packet["candidates"][0]["candidate_bytes"]["mappings"]
    assert audit_source_observation_mapping_contract_v1(actual)["mapping_count"] == 0


@pytest.mark.parametrize("field,value", [
    ("document_id", "gfpstorev1:document:" + "f" * 64),
    ("source_sha256", "f" * 64), ("source_logical_name", "other.pdf"), ("physical_page", 34),
])
def test_registered_unit_context_rejects_mismatched_source_identity(field, value):
    _, options = _packet_options()
    options["regions"][0][field] = value
    with pytest.raises(family.GeminiJsonServiceActivityFamilyV1Error, match="source identity drifted"):
        family._apply_registered_page_unit_contexts_v1(original_pages=options["page_json_by_version"],
            pages=copy.deepcopy(options["page_json_by_version"]), regions=options["regions"],
            compiled_specs=options["compiled_specs"])


@pytest.mark.parametrize("mutation", ["explicit_unit", "value", "columns", "title", "other_table"])
def test_registered_unit_context_requires_exact_raw_beforeimage_and_never_overrides_units(mutation):
    _, options = _packet_options()
    page = options["page_json_by_version"][VERSION]
    table = page["sections"][0]["tables"][3]
    if mutation == "explicit_unit":
        table["unit_exact"] = "VND"
    elif mutation == "value":
        table["rows"][-1]["values_exact"][0] = "29.279"
    elif mutation == "columns":
        table["columns"].reverse()
    elif mutation == "title":
        table["title_exact"] += " của công ty con"
    else:
        page["sections"][0]["tables"][0]["unit_exact"] = "VND"
    with pytest.raises(family.GeminiJsonServiceActivityFamilyV1Error, match="before-image or explicit override drifted"):
        family._apply_registered_page_unit_contexts_v1(original_pages=options["page_json_by_version"],
            pages=copy.deepcopy(options["page_json_by_version"]), regions=options["regions"],
            compiled_specs=options["compiled_specs"])


def test_context_is_content_bound_not_routed_by_historical_full_ordinal():
    _, options = _packet_options()
    options["regions"][0].update(document_ordinal=1, selected_page_ordinal=1)
    pages = copy.deepcopy(options["page_json_by_version"])
    receipts = family._apply_registered_page_unit_contexts_v1(original_pages=options["page_json_by_version"],
        pages=pages, regions=options["regions"], compiled_specs=options["compiled_specs"])
    assert len(receipts) == 1 and receipts[0]["ordinal_routing_permitted"] is False
    assert receipts[0]["target_locator"]["selected_page_ordinal"] == 1
    assert pages[VERSION]["sections"][0]["tables"][3]["unit_exact"] == "Triệu Đồng Việt Nam"


@pytest.mark.parametrize("field,value", [
    ("page_json_version_id", "gfpstorev1:json:" + "e" * 64),
    ("section_id", "s2"), ("table_id", "t2"),
])
def test_registered_unit_context_does_not_donate_to_another_version_or_table(field, value):
    _, options = _packet_options()
    options["regions"][0][field] = value
    pages = copy.deepcopy(options["page_json_by_version"])
    assert family._apply_registered_page_unit_contexts_v1(
        original_pages=options["page_json_by_version"], pages=pages,
        regions=options["regions"], compiled_specs=options["compiled_specs"],
    ) == []
    assert pages == options["page_json_by_version"]
    assert pages[VERSION]["sections"][0]["tables"][3]["unit_exact"] is None


def test_resealed_compiled_registry_cannot_replace_the_independently_pinned_approval():
    _, options = _packet_options()
    registry = options["compiled_specs"]["service_activity_page_unit_context_registry"]
    registry["contexts"][0]["target"]["assigned_unit_exact"] = "VND"
    context = registry["contexts"][0]
    context["unit_context_receipt_id"] = "gjsafav1:page-unit-context:" + canonical_json_sha256_v1(
        {key: value for key, value in context.items() if key != "unit_context_receipt_id"})
    options["compiled_specs"]["service_activity_page_unit_context_compiled_sha256"] = canonical_json_sha256_v1({
        "family_id": "SERVICE_ACTIVITY", "registry_sha256": family._PAGE_UNIT_CONTEXT_REGISTRY_SHA256, "registry": registry,
    })
    with pytest.raises(family.GeminiJsonServiceActivityFamilyV1Error, match="compiled page-unit context registry drifted"):
        family.evaluate_gemini_json_service_activity_family_cluster_v1(**options)


def _synthetic_options():
    page = _two_parent_service_page_without_explicit_root()
    rows = page["sections"][0]["tables"][0]["rows"]
    for row in rows[3:]:
        row["values_exact"] = [value.strip("()") for value in row["values_exact"]]
    label = "Lãi/lỗ thuần từ hoạt động dịch vụ"
    rows.append({"label_exact": label, "hierarchy_path_exact": [label], "row_kind": "TOTAL", "values_exact": ["70", "60"]})
    record = _page_record(page, selected_ordinal=1, physical_page=1)
    compiled = _compiled()
    classification = classify_gemini_json_multitable_hierarchical_table_v1(page, page["sections"][0],
        page["sections"][0]["tables"][0], compiled_specs=compiled)
    region = {**{key: value for key, value in record.items() if key != "page_json"}, "section_id": "s1", "table_id": "t1",
        "fragment_ordinal": 1, "component_roles": sorted(family._classification_roles_v1(classification))}
    return {"regions": [region], "page_json_by_version": {record["page_json_version_id"]: page},
        "compiled_specs": compiled, "query_receipt": family.build_gemini_json_service_activity_region_query_receipt_v1([region])}


def test_synthetic_source_owned_net_does_not_need_registered_unit_or_rewrite_positive_expense():
    options = _synthetic_options()
    original = copy.deepcopy(options["page_json_by_version"])
    actual = family.evaluate_gemini_json_service_activity_family_cluster_v1(**options)
    assert actual["status"] == READY, actual["reasons"]
    assert [value["source_text"] for value in _root(actual)["values"]] == ["70", "60"]
    expense = next(item for item in actual["mappings"] if item["role"] == "EXPENSE_PARENT")
    assert [value["coefficient"] for value in expense["values"]] == [30, 20]
    assert options["page_json_by_version"] == original


def test_public_unknown_note_unit_stays_hold_despite_matching_primary_and_unit_consensus():
    options = _synthetic_options()
    note = next(iter(options["page_json_by_version"].values()))
    table = note["sections"][0]["tables"][0]
    table["unit_exact"] = None
    for column in table["columns"]:
        column["header_path_exact"] = [value for value in column["header_path_exact"] if value != "Triệu đồng"]
    primary = _unit_control_page(primary=True, unit_exact="Triệu đồng",
        income=["1", "2", "100", "80"], expense=["3", "4", "30", "20"], root=["4", "6", "70", "60"])
    for suffix in ("a", "b"):
        options["page_json_by_version"]["gfpstorev1:json:" + suffix * 64] = copy.deepcopy(primary)
    before = copy.deepcopy(options["page_json_by_version"])
    actual = family.evaluate_gemini_json_service_activity_family_cluster_v1(**options)
    assert actual["status"] == UNRESOLVED and actual["mappings"] == []
    assert actual["closure_receipt"].get("service_activity_adapter_receipt", {}).get("unit_corroboration_receipts", []) == []
    assert audit_source_observation_mapping_contract_v1(actual)["mapping_count"] == 0
    assert options["page_json_by_version"] == before


@pytest.mark.parametrize("mutation", [
    "blank_net", "mismatched_net", "qualified_net", "qualified_net_label", "nonterminal_net", "duplicate_net",
    "wrong_owner", "wrong_period", "unit_missing", "parent_blank", "child_changed", "resealed_child_equation",
])
def test_printed_net_requires_complete_fresh_owned_source_not_equal_amounts_or_stale_equations(mutation):
    options = _synthetic_options()
    before, fallback, contexts, _pages = _before_controls(options)
    original_mappings = copy.deepcopy(before["mappings"])
    page = next(iter(options["page_json_by_version"].values()))
    table = page["sections"][0]["tables"][0]
    if mutation == "blank_net":
        table["rows"][-1]["values_exact"][0] = None
    elif mutation == "mismatched_net":
        table["rows"][-1]["values_exact"][0] = "71"
    elif mutation == "qualified_net":
        table["rows"][-1]["hierarchy_path_exact"].insert(0, "Công ty con")
    elif mutation == "qualified_net_label":
        table["rows"][-1]["label_exact"] += " của công ty con"
        table["rows"][-1]["hierarchy_path_exact"] = [table["rows"][-1]["label_exact"]]
    elif mutation == "nonterminal_net":
        table["rows"].append(copy.deepcopy(table["rows"][1]))
    elif mutation == "duplicate_net":
        table["rows"].append(copy.deepcopy(table["rows"][-1]))
    elif mutation == "wrong_owner":
        table["title_exact"] = page["sections"][0]["title_exact"] = "Thu nhập từ hoạt động khác"
    elif mutation == "wrong_period":
        table["columns"][0]["header_path_exact"] = ["Năm 2026", "Triệu đồng"]
    elif mutation == "unit_missing":
        table["unit_exact"] = None
        for column in table["columns"]:
            column["header_path_exact"] = [value for value in column["header_path_exact"] if value != "Triệu đồng"]
    elif mutation == "parent_blank":
        table["rows"][3]["values_exact"][0] = None
    elif mutation == "child_changed":
        table["rows"][1]["values_exact"][0] = "61"
    else:
        equation = next(item for item in before["closure_receipt"]["equations"]
                        if item["equation_kind"] == "EXACT_VISIBLE_HIERARCHY_DIRECT_CHILDREN_EQUAL_CARRIER")
        equation["component_source_refs"].reverse()
        equation["equation_id"] = "gjfoltiev1:equation:" + canonical_json_sha256_v1(
            {key: value for key, value in equation.items() if key != "equation_id"})
    actual, proof, active_fallback = family._apply_printed_net_source_controls_v1(before,
        original_pages=options["page_json_by_version"], regions=options["regions"], compiled_specs=options["compiled_specs"],
        root_fallback_receipt=fallback, context_receipts=contexts)
    assert actual["status"] == UNRESOLVED and actual["mappings"] == []
    assert active_fallback is None and proof["failures"]
    assert _decode(proof["withheld_mappings"]) == original_mappings
    assert actual["closure_receipt"]["root_component_sum_receipts"] == []
    assert actual["closure_receipt"]["structural_root_receipt"]["emitted_mapping"] is False
    assert actual["closure_receipt"]["structural_root_receipt"]["source_total_mapping_id"] is None
    assert actual["closure_receipt"]["structural_root_receipt"]["active_permission"] == "NONE_SOURCE_CONTROL_HOLD"
    assert audit_source_observation_mapping_contract_v1(actual)["mapping_count"] == 0
    if mutation == "qualified_net_label":
        assert proof["failures"] == ["PRINTED_NET_LABEL_HAS_UNPROVEN_SOURCE_QUALIFIER"]
        assert proof["qualified_net_rows"] == [{
            "locator": options["regions"][0], "row_ordinal": len(table["rows"]),
            "source_row_exact": table["rows"][-1],
        }]


def test_public_qualified_net_label_cannot_fall_through_to_global_derived_root():
    options = _synthetic_options()
    row = next(iter(options["page_json_by_version"].values()))["sections"][0]["tables"][0]["rows"][-1]
    row["label_exact"] += " của công ty con"
    row["hierarchy_path_exact"] = [row["label_exact"]]
    before = copy.deepcopy(options["page_json_by_version"])
    actual = family.evaluate_gemini_json_service_activity_family_cluster_v1(**options)
    assert actual["status"] == UNRESOLVED and actual["mappings"] == []
    assert audit_source_observation_mapping_contract_v1(actual)["mapping_count"] == 0
    assert options["page_json_by_version"] == before
    assert family.validate_gemini_json_service_activity_family_candidate_replay_v1(actual, **options) == actual


@pytest.mark.parametrize("field", ["unit_context", "retired_authority", "printed_root_ref"])
def test_actual_fresh_replay_rejects_self_resealed_context_retirement_or_root_tamper(field):
    _, options = _packet_options()
    actual = family.evaluate_gemini_json_service_activity_family_cluster_v1(**options)
    assert actual["status"] == READY
    adapter = actual["closure_receipt"]["service_activity_adapter_receipt"]
    if field == "unit_context":
        receipt = adapter["page_unit_context_receipts"][0]
        receipt["unit_after_exact"] = "VND"
        receipt["receipt_id"] = "gjsafav1:page-unit-replay:" + canonical_json_sha256_v1(
            {key: value for key, value in receipt.items() if key != "receipt_id"})
    elif field == "retired_authority":
        receipt = _control(actual)
        receipt["retired_root_authority"] = family._mapping_evidence_v1(None)
        receipt["receipt_id"] = "gjsafav1:printed-net:" + canonical_json_sha256_v1(
            {key: value for key, value in receipt.items() if key != "receipt_id"})
        actual["closure_receipt"]["structural_root_receipt"]["source_control_receipt_id"] = receipt["receipt_id"]
    else:
        root = _root(actual)
        root["source_refs"][0]["row_ordinal"] = 5
        root["item_mapping_id"] = "gjmthfmv1:item:" + canonical_json_sha256_v1(
            {key: value for key, value in root.items() if key != "item_mapping_id"})
    adapter["adapter_receipt_id"] = "gjsafav1:receipt:" + canonical_json_sha256_v1(
        {key: value for key, value in adapter.items() if key != "adapter_receipt_id"})
    actual["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in actual.items() if key != "candidate_id"})
    with pytest.raises(family.GeminiJsonServiceActivityFamilyV1Error, match="candidate replay drifted"):
        family.validate_gemini_json_service_activity_family_candidate_replay_v1(actual, **options)
