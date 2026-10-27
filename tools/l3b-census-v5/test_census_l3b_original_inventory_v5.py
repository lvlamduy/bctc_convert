"""PLANNED, UNRUN stdlib controls. No project, DB, PDF or real inventory import.

Run only after root captures/reviews this packet under its serialized lease.
All record bodies below come from explicitly synthetic fixture metadata.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("_l3b_external_census_v1", ROOT / "census_l3b_original_inventory_v5.py")
census = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = census
SPEC.loader.exec_module(census)


def plan():
    families = []
    for number, owner in ((49, "Rủi ro lãi suất"), (50, "Rủi ro thanh khoản"), (53, "Theo khu vực địa lý")):
        aliases = [{"literal": owner, "kind": "OWNER_ALIAS"},
                   {"literal": "Tổng tài sản", "kind": "COMPONENT_ALIAS"},
                   {"literal": "Khác", "kind": "COMPONENT_ALIAS"},
                   {"literal": "Từ 1 tháng đến 3 tháng", "kind": "MATRIX_AXIS_ALIAS"},
                   {"literal": "Trên 5 năm", "kind": "MATRIX_AXIS_ALIAS"}]
        if number == 53:
            aliases += [{"literal": "Trong nước", "kind": "COMPONENT_ALIAS"}]
        families.append({"family_number": number, "family_id": "SYNTHETIC_" + str(number), "aliases": aliases,
                         "owner_specificity_limit": "GENERIC_GEOGRAPHY_REQUIRES_ADDITIONAL_SECURITIES_CONTEXT" if number == 53 else "REGISTERED_PARENT_LITERAL_ONLY_NOT_FINANCIAL_OWNERSHIP"})
    return census.LiteralPlan(families)


def fixture():
    raw = (ROOT / "synthetic-fixtures/selected-original-inventory.SYNTHETIC.jsonl").read_bytes()
    metadata = json.loads((ROOT / "synthetic-fixtures/SYNTHETIC_FIXTURE_CONTRACT_V1.json").read_text(encoding="utf-8"))
    if hashlib.sha256(raw).hexdigest() != metadata["stream_sha256"] or len(raw) != metadata["stream_size_bytes"]:
        raise AssertionError("Synthetic fixture bytes drifted")
    return [json.loads(line) for line in raw.splitlines()], metadata


def scan(records, metadata, selected_plan=None):
    occurrences = []
    frontier = census.Frontier(selected_plan or plan(), lambda family, item: occurrences.append((family, item)))
    for item in records:
        frontier.add(item)
    result = frontier.finish(metadata["counts"], metadata["ordered_selected_page_axis_one_lf_sha256"])
    return frontier, result, occurrences


def synthetic_completion():
    # UNIT structure only: main still requires the independent immutable raw
    #493637/98a067 receipts and561678 stream. This object cannot pass Held pins.
    inventory = {
        "format_version": "F36_NEUTRAL_SELECTED_ORIGINAL_INVENTORY_V1",
        "status": "COMPLETE_NEUTRAL_INVENTORY_NOT_FAMILY_OR_PDF_PROOF", "errors": [],
        "source_context_successfully_exited": True, "complete_selected_page_frontier": True,
        "status_filter_applied": False, "expected_documents": 271, "expected_pages": 14945,
        "counts": dict(census.EXPECTED), "sql_integrity": [{"quick_check": "ok", "foreign_key_check": "EMPTY"}] * 2,
        "financial_acceptance": False, "family_seal": False, "pdf_absence_proved": False,
        "role_unit_period_or_value_permission_granted": False, "provider_or_reextraction_performed": False,
        "database_ref": copy.deepcopy(census.DATABASE_REF), "corpus_index_ref": copy.deepcopy(census.CORPUS_INDEX_REF),
        "stream_ref": {k: census.INPUTS["stream"][k] for k in ("sha256", "size_bytes")},
        "stream_path": census.INPUTS["stream"]["path"],
    }
    material = {k: v for k, v in inventory.items() if k not in {"errors", "sql_integrity", "inventory_id", "stream_path"}}
    inventory["inventory_id"] = "f36originalinventoryv1:" + census.digest(material)
    producer_refs = json.loads((ROOT / "PRODUCER_REFERENCE_METADATA_V5.json").read_text(encoding="utf-8"))["producer_refs"]
    controlled = {
        "format_version": "F36_CONTROLLED_NEUTRAL_ORIGINAL_INVENTORY_RUN_V1",
        "status": "PASS_NEUTRAL_ORIGINAL_INVENTORY_NOT_FINANCIAL_OR_PDF_PROOF", "errors": [], "profile": "full271",
        "implementation_inputs_unchanged": True, "inventory_result": copy.deepcopy(inventory),
        "inventory_stream_ref": copy.deepcopy(producer_refs["inventory_stream_ref"]),
        "inventory_receipt_ref": copy.deepcopy(producer_refs["inventory_receipt_ref"]),
    }
    return inventory, controlled


def punctuation_plan(*, normal=False, punctuation_kind="MATRIX_AXIS_ALIAS"):
    aliases = []
    if normal:
        aliases = [{"literal": "Specific Financial Assets Disclosure", "kind": "OWNER_ALIAS"},
                   {"literal": "BucketAlpha", "kind": "MATRIX_AXIS_ALIAS"},
                   {"literal": "Assets", "kind": "COMPONENT_ALIAS"}]
    aliases += [{"literal": "*", "kind": punctuation_kind}, {"literal": "(*)", "kind": punctuation_kind}]
    return census.LiteralPlan([{"family_number": 47, "family_id": "SYNTHETIC_PUNCTUATION_ONLY",
                               "aliases": aliases,
                               "owner_specificity_limit": "REGISTERED_PARENT_LITERAL_ONLY_NOT_FINANCIAL_OWNERSHIP"}])


def punctuation_table():
    records, _meta = fixture()
    section = copy.deepcopy(next(r for r in records if r["record_type"] == "section"))
    section["fields"]["title_exact"]["value"] = "Unrelated synthetic section"
    record = copy.deepcopy(next(r for r in records if r["record_type"] == "table"))
    record["fields"]["title_exact"]["value"] = "Unrelated synthetic table"
    columns = copy.deepcopy([r for r in records if r["record_type"] == "column"][:2])
    rows = copy.deepcopy([r for r in records if r["record_type"] == "row"][:2])
    for index, token in enumerate(("*", "(*)")):
        columns[index]["column_exact"]["header_path_exact"] = [token, "opening" if index == 0 else "closing"]
        rows[index]["fields"]["label_exact"]["value"] = token
        rows[index]["fields"]["hierarchy_path_exact"]["value"] = []
    return {"section": section, "record": record, "columns": columns, "rows": rows,
            "unsupported": [], "literal_issues": []}


class CensusControls(unittest.TestCase):
    def test_all_synthetic_records_close_exact_source_version_frontier(self):
        records, meta = fixture()
        frontier, result, occurrences = scan(records, meta)
        self.assertEqual(result["counts"], meta["counts"])
        self.assertEqual(result["selected_source_version_count"], 2)
        self.assertFalse(result["source_versions_collapsed"])
        self.assertEqual(frontier.unsupported_documents, {2: 1})
        self.assertTrue(occurrences)

    def test_identical_pdf_sha_never_collapses_distinct_document_vid_contexts(self):
        records, meta = fixture()
        _frontier, _result, occurrences = scan(records, meta)
        identities = {item["source_identity"]["page_json_version_id"] for _family, item in occurrences}
        self.assertEqual(len(identities), 2)
        self.assertEqual({item["source_identity"]["source_sha256"] for _family, item in occurrences}, {"a" * 64})
        self.assertEqual({item["source_identity"]["document_ordinal"] for _family, item in occurrences}, {1, 2})

    def test_strong_owner_is_local_and_not_continuation_propagation(self):
        records, meta = fixture()
        _frontier, _result, occurrences = scan(records, meta)
        items = [item for family, item in occurrences if family == 49]
        first = next(item for item in items if item["source_identity"]["document_ordinal"] == 1 and item["table_id"] == "t1")
        self.assertEqual(first["classification"], "STRONG_OWNER_LITERAL_OCCURRENCE_NOT_OWNERSHIP_PROOF")
        for item in items:
            if item is not first:
                self.assertEqual(item["classification"], "WEAK_GENERIC_COMPONENT_OR_ROW_OWNER_LITERAL_ONLY")
            self.assertFalse(item["continuation_propagated"])

    def test_competing_reset_literal_is_ambiguous_not_a_resolved_owner(self):
        records, meta = fixture()
        selected = plan()
        selected.families[49]["aliases"].append({"literal": "Tổng tài sản", "kind": "RESET_ALIAS"})
        selected = census.LiteralPlan(list(selected.families.values()))
        _frontier, _result, occurrences = scan(records, meta, selected)
        item = next(item for family, item in occurrences if family == 49 and item["source_identity"]["document_ordinal"] == 1 and item["table_id"] == "t1")
        self.assertEqual(item["classification"], "OWNER_AND_COMPETING_RESET_LITERALS_AMBIGUOUS")

    def test_generic_geography_owner_needs_securities_context(self):
        records, meta = fixture()
        table = next(r for r in records if r["record_type"] == "table")
        table["fields"]["title_exact"]["value"] = "Theo khu vực địa lý"
        _frontier, _result, occurrences = scan(records, meta)
        items = [item for family, item in occurrences if family == 53]
        self.assertTrue(items)
        self.assertTrue(all(item["classification"] == "WEAK_GENERIC_COMPONENT_OR_ROW_OWNER_LITERAL_ONLY" for item in items))

    def test_nulls_and_zero_hashes_are_metadata_not_numeric_values(self):
        records, meta = fixture()
        _frontier, _result, occurrences = scan(records, meta)
        for _family, item in occurrences:
            self.assertIsNone(item["blank_metadata"]["numeric_zero_count"])
            self.assertFalse(item["blank_metadata"]["raw_blank_strings_detectable"])
            self.assertFalse(item["occurrence_is_financial_acceptance"])
            self.assertNotIn("values_exact", item)
        self.assertTrue(any(item["blank_metadata"]["null_value_slot_count"] > 0 for _family, item in occurrences))

    def test_typed_presence_envelope_never_confuses_missing_with_empty(self):
        self.assertEqual(census.field({"fields": {"x": {"present": False, "value": None}}}, "x"), {"present": False, "value": None})
        self.assertEqual(census.field({"fields": {"x": {"present": True, "value": ""}}}, "x"), {"present": True, "value": ""})
        with self.assertRaises(census.CensusError):
            census.field({"fields": {"x": {"present": False, "value": "0"}}}, "x")
        with self.assertRaises(census.CensusError):
            census.field({"fields": {"x": "raw-legacy-field"}}, "x")

    def test_foreign_vid_node_is_rejected(self):
        records, meta = fixture()
        row = next(r for r in records if r["record_type"] == "row")
        row["page_json_version_id"] = "gfpstorev1:json:" + "f" * 64
        with self.assertRaisesRegex(census.CensusError, "VID"):
            scan(records, meta)

    def test_boolean_global_document_or_page_ordinals_are_rejected(self):
        for target in ("document", "page"):
            with self.subTest(target=target):
                records, meta = fixture()
                r = next(r for r in records if r["record_type"] == target)
                if target == "document":
                    r["index_document"]["source_ordinal"] = True
                else:
                    r["axis"]["selected_page_ordinal"] = True
                with self.assertRaises(census.CensusError):
                    scan(records, meta)

    def test_boolean_page_proof_physical_number_is_rejected(self):
        records, meta = fixture()
        next(r for r in records if r["record_type"] == "page")["source_proof"]["physical_page"] = True
        with self.assertRaises(census.CensusError):
            scan(records, meta)

    def test_missing_duplicate_or_reordered_row_is_never_silently_skipped(self):
        for mutation in ("missing", "duplicate", "reordered"):
            with self.subTest(mutation=mutation):
                records, meta = fixture()
                indices = [i for i, r in enumerate(records) if r["record_type"] == "row"]
                if mutation == "missing":
                    del records[indices[0]]
                elif mutation == "duplicate":
                    records.insert(indices[0], copy.deepcopy(records[indices[0]]))
                else:
                    records[indices[0]], records[indices[1]] = records[indices[1]], records[indices[0]]
                with self.assertRaises(census.CensusError):
                    scan(records, meta)

    def test_row_null_axis_requires_exact_none_type_positions(self):
        records, meta = fixture()
        row = next(r for r in records if r["record_type"] == "row")
        row["value_axis"]["null_column_ordinals"] = []
        with self.assertRaisesRegex(census.CensusError, "null"):
            scan(records, meta)

    def test_unsupported_shape_is_retained_and_counted_not_dropped(self):
        records, meta = fixture()
        frontier, result, occurrences = scan(records, meta)
        self.assertEqual(result["counts"]["unsupported_shape"], 1)
        self.assertEqual(frontier.unsupported_documents[2], 1)
        self.assertTrue(any(item["unsupported_shape_records"] for _family, item in occurrences))

    def test_mixed_hierarchy_keeps_string_members_at_original_ordinals_and_reports_unknowns(self):
        records, meta = fixture()
        row = next(r for r in records if r["record_type"] == "row")
        row["fields"]["label_exact"]["value"] = "Unregistered synthetic row label"
        row["fields"]["hierarchy_path_exact"]["value"] = ["Rủi ro lãi suất", None, "Khác", 1]
        frontier, _result, occurrences = scan(records, meta)
        item = next(item for family, item in occurrences if family == 49 and item["source_identity"]["document_ordinal"] == 1 and item["table_id"] == "t1")
        hierarchy = [hit for hit in item["label_hits"] if hit["context"] == "ROW_HIERARCHY" and hit["pointer"] == row["pointer"]]
        self.assertEqual([h["path_ordinal"] for h in hierarchy], [1, 3])
        issues = [issue for issue in item["unsupported_literal_field_shapes"] if issue["field"] == "hierarchy_path_exact"]
        self.assertEqual([i["member_ordinal"] for i in issues], [2, 4])
        self.assertGreaterEqual(frontier.unsupported_documents[1], 2)

    def test_mixed_header_keeps_string_levels_without_coercing_null_into_text(self):
        records, meta = fixture()
        column = next(r for r in records if r["record_type"] == "column")
        column["column_exact"]["header_path_exact"] = ["Rủi ro lãi suất", None, "Từ 1 tháng đến 3 tháng"]
        _frontier, _result, occurrences = scan(records, meta)
        item = next(item for family, item in occurrences if family == 49 and item["source_identity"]["document_ordinal"] == 1 and item["table_id"] == "t1")
        header = item["header_grammar"]["columns"][0]
        self.assertEqual([h["header_level_ordinal"] for h in header["header_path_strings"]], [1, 3])
        self.assertEqual(header["unsupported_header_members"][0]["header_level_ordinal"], 2)
        self.assertEqual(header["unsupported_header_members"][0]["json_type"], "NoneType")

    def test_unknown_record_kind_or_unclosed_document_rejects_completion(self):
        for mutation in ("unknown", "unclosed"):
            with self.subTest(mutation=mutation):
                records, meta = fixture()
                if mutation == "unknown":
                    records[2]["record_type"] = "silently-ignore-me"
                else:
                    records.pop()
                with self.assertRaises(census.CensusError):
                    scan(records, meta)

    def test_page_frontier_digest_and_complete_denominator_are_independent_gates(self):
        for mutation in ("digest", "denominator"):
            with self.subTest(mutation=mutation):
                records, meta = fixture()
                if mutation == "digest":
                    meta["ordered_selected_page_axis_one_lf_sha256"] = "0" * 64
                else:
                    meta["counts"]["table"] -= 1
                with self.assertRaises(census.CensusError):
                    scan(records, meta)

    def test_normalization_is_whole_token_and_preserves_raw_label(self):
        selected = plan()
        self.assertIn(49, selected.hits("RỦI RO LÃI SUẤT (tiếp theo)"))
        self.assertEqual(selected.hits("prefixTổng tài sảnsuffix"), {})
        self.assertEqual(census.normalized("Điều chỉnh\nthuế"), "dieu chinh thue")

    def test_duplicate_nonfinite_blank_line_and_unterminated_tail_are_rejected(self):
        for raw in (b'{"a":1,"a":2}\n', b'{"a":NaN}\n', b'\n', b'{}'):
            with self.subTest(raw=raw):
                reference = {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
                with self.assertRaises((census.CensusError, ValueError)):
                    list(census.stream_records(io.BytesIO(raw), reference, lambda: None))

    def test_stream_raw_hash_is_checked_after_whole_single_parse(self):
        records, _meta = fixture()
        raw = b"".join(census.canonical(r) for r in records)
        reference = {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
        self.assertEqual(list(census.stream_records(io.BytesIO(raw), reference, lambda: None)), records)
        with self.assertRaisesRegex(census.CensusError, "raw hash"):
            list(census.stream_records(io.BytesIO(raw), {**reference, "sha256": "0" * 64}, lambda: None))

    def test_synthetic_completion_structure_cannot_change_profile_source_or_safety_boundary(self):
        inventory, controlled = synthetic_completion()
        self.assertEqual(census.validate_completion(inventory, controlled), census.EXPECTED)
        for key, value in (("status", "FAIL"), ("complete_selected_page_frontier", False), ("status_filter_applied", True),
                           ("financial_acceptance", True), ("expected_documents", 204)):
            with self.subTest(key=key):
                broken = {**inventory, key: value}
                with self.assertRaises(census.CensusError):
                    census.validate_completion(broken, controlled)
        broken = copy.deepcopy(inventory)
        broken["database_ref"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(census.CensusError, "authority"):
            census.validate_completion(broken, controlled)

    def test_completion_reseal_and_wrong_outer_result_do_not_pass_bindings(self):
        inventory, controlled = synthetic_completion()
        with self.assertRaisesRegex(census.CensusError, "content ID"):
            census.validate_completion({**inventory, "inventory_id": "caller-reseal"}, controlled)
        broken = copy.deepcopy(controlled)
        broken["inventory_result"]["counts"]["table"] -= 1
        with self.assertRaisesRegex(census.CensusError, "binding"):
            census.validate_completion(inventory, broken)

    def test_runtime_catalog_remains_all13_pinned_static_expectations(self):
        raw = (ROOT / "REGISTERED_LITERAL_CATALOG_V1.json").read_bytes()
        self.assertEqual((hashlib.sha256(raw).hexdigest(), len(raw)), (census.CATALOG_SHA, census.CATALOG_BYTES))
        catalog = json.loads(raw)
        self.assertEqual([f["family_number"] for f in catalog["families"]], list(range(41, 54)))
        self.assertEqual(sum(len(f["aliases"]) for f in catalog["families"]), 1030)
        self.assertEqual(catalog["status"], "STATIC_EXPECTATIONS_NOT_SOURCE_OCCURRENCES")

    def test_memory_floor_is_checked_from_exact_available_field_not_total_ram(self):
        with patch.object(Path, "read_text", return_value="MemTotal: 99999999 kB\nMemAvailable: 1 kB\n"):
            with self.assertRaisesRegex(census.CensusError, "MemAvailable"):
                census.mem_available()
        with patch.object(Path, "read_text", return_value="MemAvailable: 1572864 kB\n"):
            census.mem_available()
        with patch.object(Path, "read_text", return_value="MemAvailable: 1572864 kB\nMemAvailable: 1572864 kB\n"):
            with self.assertRaises(census.CensusError):
                census.mem_available()

    @unittest.skipUnless(sys.platform == "linux", "Held descriptors require the later Linux test lease")
    def test_held_descriptor_final_barrier_rejects_mutated_owned_synthetic_file(self):
        # ROOT must itself be under an authorized CODEX/home capture prefix.
        with tempfile.TemporaryDirectory(prefix="synthetic-owned-held-", dir=ROOT) as temporary:
            path = Path(temporary) / "unit-only.txt"
            path.write_bytes(b"old")
            reference = {"path": str(path), "sha256": hashlib.sha256(b"old").hexdigest(), "size_bytes": 3}
            held = census.Held()
            try:
                held.open(reference)
                path.write_bytes(b"new")
                with self.assertRaisesRegex(census.CensusError, "Final held input drift"):
                    held.validate()
            finally:
                held.close()


    def test_declared_four_status_axis_preserves_explicit_zero_categories(self):
        records, meta = fixture()
        document = next(r for r in records if r["record_type"] == "document")
        self.assertEqual(set(document["index_document"]["page_status_counts"]), set(census.PAGE_STATUSES))
        self.assertEqual(sum(n == 0 for n in document["index_document"]["page_status_counts"].values()), 3)
        frontier, _result, _occurrences = scan(records, meta)
        self.assertEqual(dict(frontier.statuses), {"FINANCIAL_NOTE_CONTENT": 1})

    def test_unknown_status_boolean_zero_or_sparse_declared_axis_rejects(self):
        for mutation in ("unknown", "boolean_zero", "sparse"):
            with self.subTest(mutation=mutation):
                records, meta = fixture()
                declared = next(r for r in records if r["record_type"] == "document")["index_document"]["page_status_counts"]
                if mutation == "unknown":
                    declared["UNKNOWN_STATUS"] = declared.pop("MIXED_FINANCIAL_CONTENT")
                elif mutation == "boolean_zero":
                    declared["MIXED_FINANCIAL_CONTENT"] = False
                else:
                    del declared["MIXED_FINANCIAL_CONTENT"]
                with self.assertRaises(census.CensusError):
                    scan(records, meta)

    def test_wrong_sparse_observed_frontier_or_unknown_page_status_rejects(self):
        for mutation in ("frontier_zero", "page_status"):
            with self.subTest(mutation=mutation):
                records, meta = fixture()
                if mutation == "frontier_zero":
                    next(r for r in records if r["record_type"] == "document_frontier_verified")["page_status_counts"]["MIXED_FINANCIAL_CONTENT"] = 0
                else:
                    next(r for r in records if r["record_type"] == "page")["source_proof"]["page_status"] = "UNKNOWN_STATUS"
                with self.assertRaises(census.CensusError):
                    scan(records, meta)

    def test_actual_pinned_catalog_constructor_keeps_all1030_including_two_footnotes(self):
        raw = (ROOT / "REGISTERED_LITERAL_CATALOG_V1.json").read_bytes()
        self.assertEqual((hashlib.sha256(raw).hexdigest(), len(raw)), (census.CATALOG_SHA, census.CATALOG_BYTES))
        catalog = json.loads(raw)
        selected = census.LiteralPlan(catalog["families"])
        self.assertEqual(selected.registered_alias_count, 1030)
        self.assertEqual(selected.punctuation_alias_count, 2)
        self.assertEqual(sum(len(items) for items in selected.first_token.values()), 1028)
        self.assertEqual([h["catalog_alias_ordinal"] for h in selected.hits("*")[47]], [94])
        self.assertEqual([h["catalog_alias_ordinal"] for h in selected.hits("(*)")[47]], [95])

    def test_punctuation_matches_only_distinct_whole_nfc_outer_trimmed_fields(self):
        selected = punctuation_plan()
        self.assertEqual([h["catalog_alias_ordinal"] for h in selected.hits(" * ")[47]], [1])
        self.assertEqual([h["catalog_alias_ordinal"] for h in selected.hits("(*)")[47]], [2])
        for literal in ("", " ", "total *", "(*) note", "*anything", ".*", "(**)", "( * )", "\u00a0( * )\u00a0"):
            with self.subTest(literal=literal):
                self.assertEqual(selected.hits(literal), {})
        self.assertEqual([h["catalog_alias_ordinal"] for h in selected.hits("\u00a0*\u00a0")[47]], [1])
        for hit in selected.hits("*")[47]:
            self.assertTrue(hit["punctuation_only"])
            self.assertTrue(hit["generic_short_phrase"])
            self.assertEqual(hit["evidence_only"], "WEAK_WHOLE_FIELD_PUNCTUATION_SIDE_EVIDENCE")

    def test_two_footnotes_never_infer_matrix_transpose_or_unrelated_rollforward(self):
        table = punctuation_table()
        items = list(census.table_occurrences(table, punctuation_plan()))
        self.assertEqual(len(items), 1)
        family, item = items[0]
        self.assertEqual(family, 47)
        self.assertEqual(item["classification"], "WEAK_GENERIC_COMPONENT_OR_ROW_OWNER_LITERAL_ONLY")
        self.assertEqual(item["shape_candidates"], ["NO_LAYOUT_OR_AXIS_INFERENCE"])
        self.assertEqual(item["header_grammar"]["literal_rollforward_words"], ["opening", "closing"])
        self.assertTrue(all(a["punctuation_only"] for h in item["label_hits"] for a in h["alias_hits"]))
        self.assertFalse(item["financial_acceptance"])

    def test_punctuation_parent_or_reset_literals_remain_weak_side_evidence(self):
        for kind in ("OWNER_ALIAS", "RESET_ALIAS", "HARD_NEGATIVE_ALIAS", "MATRIX_AXIS_ALIAS"):
            with self.subTest(kind=kind):
                table = punctuation_table()
                table["record"]["fields"]["title_exact"]["value"] = "*"
                item = list(census.table_occurrences(table, punctuation_plan(punctuation_kind=kind)))[0][1]
                self.assertEqual(item["classification"], "WEAK_GENERIC_COMPONENT_OR_ROW_OWNER_LITERAL_ONLY")
                self.assertEqual(item["shape_candidates"], ["NO_LAYOUT_OR_AXIS_INFERENCE"])

    def test_normal_cooccurrence_preserves_normal_hits_without_footnote_axis_inflation(self):
        mixed = punctuation_plan(normal=True)
        family = copy.deepcopy(mixed.families[47])
        family["aliases"] = family["aliases"][:3]
        normal = census.LiteralPlan([family])
        table = punctuation_table()
        table["record"]["fields"]["title_exact"]["value"] = "Specific Financial Assets Disclosure"
        table["columns"][0]["column_exact"]["header_path_exact"] = ["BucketAlpha", "*"]
        table["rows"][0]["fields"]["label_exact"]["value"] = "Assets"
        with_punctuation = list(census.table_occurrences(table, mixed))[0][1]
        without_punctuation = list(census.table_occurrences(table, normal))[0][1]
        self.assertEqual(with_punctuation["classification"], "STRONG_OWNER_LITERAL_OCCURRENCE_NOT_OWNERSHIP_PROOF")
        self.assertEqual(with_punctuation["shape_candidates"], without_punctuation["shape_candidates"])
        self.assertNotIn("MATRIX_COLUMN_AXIS_LITERAL_CANDIDATE", with_punctuation["shape_candidates"])
        self.assertNotIn("TRANSPOSE_OR_REPEATED_ROW_AXIS_LITERAL_CANDIDATE_UNPROVEN", with_punctuation["shape_candidates"])
        kept = []
        for match in with_punctuation["label_hits"]:
            ordinary = [hit for hit in match["alias_hits"] if not hit.get("punctuation_only", False)]
            if ordinary:
                kept.append({**match, "alias_hits": ordinary})
        self.assertEqual(kept, without_punctuation["label_hits"])

    def test_empty_and_unsupported_normalized_aliases_still_fail_closed(self):
        for literal in ("", " ", "\u0301", "\x00"):
            with self.subTest(literal=literal):
                selected = punctuation_plan().families[47]
                selected["aliases"] = [{"literal": literal, "kind": "MATRIX_AXIS_ALIAS"}]
                with self.assertRaisesRegex(census.CensusError, "Empty or unsupported"):
                    census.LiteralPlan([selected])

    def test_actual_producer_reference_metadata_retains_all_four_fields_and_six_integers(self):
        metadata = json.loads((ROOT / "PRODUCER_REFERENCE_METADATA_V5.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["authority"]["inner_receipt_raw_sha256"], census.INPUTS["inventory"]["sha256"])
        self.assertEqual(metadata["authority"]["outer_receipt_raw_sha256"], census.INPUTS["controlled"]["sha256"])
        for field, expected in (("inventory_stream_ref", census.INPUTS["stream"]),
                                ("inventory_receipt_ref", census.INPUTS["inventory"])):
            with self.subTest(field=field):
                reference = metadata["producer_refs"][field]
                validated = census.validate_historical_producer_ref(reference, expected)
                self.assertEqual(validated, reference)
                self.assertEqual(set(validated), {"path", "sha256", "size_bytes", "identity"})
                self.assertEqual(len(validated["identity"]), 6)
                self.assertTrue(all(type(n) is int for n in validated["identity"]))
                self.assertIsNot(validated, reference)
                validated["identity"][1] += 1
                self.assertNotEqual(validated["identity"], reference["identity"])

    def test_full_completion_accepts_real_wrapper_reference_shape_and_keeps_inner_equality(self):
        inventory, controlled = synthetic_completion()
        original_inventory = copy.deepcopy(inventory)
        original_controlled = copy.deepcopy(controlled)
        self.assertEqual(census.validate_completion(inventory, controlled), census.EXPECTED)
        self.assertEqual(inventory, original_inventory)
        self.assertEqual(controlled, original_controlled)
        controlled["inventory_result"]["counts"]["table"] -= 1
        with self.assertRaisesRegex(census.CensusError, "Controlled completion/inner inventory binding"):
            census.validate_completion(inventory, controlled)

    def test_historical_reference_missing_and_unknown_fields_are_not_ignored(self):
        for field in ("inventory_stream_ref", "inventory_receipt_ref"):
            for mutation in ("missing_identity", "extra_key", "missing_entire_ref"):
                with self.subTest(field=field, mutation=mutation):
                    inventory, controlled = synthetic_completion()
                    if mutation == "missing_identity":
                        del controlled[field]["identity"]
                    elif mutation == "extra_key":
                        controlled[field]["unknown_identity_waiver"] = True
                    else:
                        del controlled[field]
                    with self.assertRaisesRegex(census.CensusError, "Historical producer reference fields"):
                        census.validate_completion(inventory, controlled)

    def test_historical_identity_rejects_wrong_types_lengths_modes_sizes_and_bounds(self):
        inventory, controlled = synthetic_completion()
        reference = controlled["inventory_stream_ref"]
        mutations = []
        mutations.append(("short", lambda r: r.update(identity=r["identity"][:-1])))
        mutations.append(("long", lambda r: r.update(identity=r["identity"] + [1])))
        mutations.append(("tuple", lambda r: r.update(identity=tuple(r["identity"]))))
        for index in range(6):
            mutations.append(("bool_" + str(index), lambda r, i=index: r["identity"].__setitem__(i, True)))
        mutations += [
            ("float", lambda r: r["identity"].__setitem__(4, 1.0)),
            ("negative_device", lambda r: r["identity"].__setitem__(0, -1)),
            ("zero_inode", lambda r: r["identity"].__setitem__(1, 0)),
            ("negative_mode", lambda r: r["identity"].__setitem__(2, -1)),
            ("directory", lambda r: r["identity"].__setitem__(2, 0o040700)),
            ("symlink", lambda r: r["identity"].__setitem__(2, 0o120777)),
            ("wrong_stat_size", lambda r: r["identity"].__setitem__(3, r["size_bytes"] + 1)),
            ("negative_mtime", lambda r: r["identity"].__setitem__(4, -1)),
            ("negative_ctime", lambda r: r["identity"].__setitem__(5, -1)),
        ]
        for name, mutate in mutations:
            with self.subTest(mutation=name):
                broken = copy.deepcopy(reference)
                mutate(broken)
                with self.assertRaises(census.CensusError):
                    census.validate_historical_producer_ref(broken, census.INPUTS["stream"])
        self.assertEqual(census.validate_completion(inventory, controlled), census.EXPECTED)

    def test_historical_reference_path_sha_and_both_sizes_remain_immutable(self):
        _inventory, controlled = synthetic_completion()
        reference = controlled["inventory_receipt_ref"]
        mutations = [
            ("path", lambda r: r.update(path=r["path"] + ".foreign")),
            ("sha", lambda r: r.update(sha256="0" * 64)),
            ("short_sha", lambda r: r.update(sha256="a" * 63)),
            ("bool_size", lambda r: r.update(size_bytes=True)),
            ("reference_size", lambda r: r.update(size_bytes=r["size_bytes"] + 1)),
            ("both_sizes", lambda r: (r.update(size_bytes=r["size_bytes"] + 1), r["identity"].__setitem__(3, r["size_bytes"]))),
        ]
        for name, mutate in mutations:
            with self.subTest(mutation=name):
                broken = copy.deepcopy(reference)
                mutate(broken)
                with self.assertRaises(census.CensusError):
                    census.validate_historical_producer_ref(broken, census.INPUTS["inventory"])

    def test_historical_identity_is_not_compared_with_current_inode_and_validator_performs_no_io(self):
        _inventory, controlled = synthetic_completion()
        reference = copy.deepcopy(controlled["inventory_stream_ref"])
        reference["identity"][0] += 1
        reference["identity"][1] += 1000
        reference["identity"][4] += 1
        reference["identity"][5] += 1
        # Structural metadata test only. In main, changing the outer receipt
        # bytes would still fail its independent immutable raw SHA pin.
        with patch.object(census.os, "stat", side_effect=AssertionError("No real path stat allowed")), \
             patch.object(census.os, "open", side_effect=AssertionError("No real path open allowed")), \
             patch.object(census.os, "pread", side_effect=AssertionError("No real byte read allowed")):
            validated = census.validate_historical_producer_ref(reference, census.INPUTS["stream"])
        self.assertEqual(validated, reference)
        self.assertNotEqual(validated["identity"], controlled["inventory_stream_ref"]["identity"])

if __name__ == "__main__":
    unittest.main()
