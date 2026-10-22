"""Pure synthetic clone tests; no registry/source/pixel approval or acceptance."""
from __future__ import annotations

import unittest
from copy import deepcopy
from hashlib import sha256

from bctc_ai.evaluation import gemini_json_income_tax_section_caption_repair_v1 as core


def fixture():
    pdf = {"logical_name": "synthetic/report.pdf", "sha256": "a" * 64, "size_bytes": 123}
    record = {
        "document_id": core._document_id(pdf), "document_ordinal": 7,
        "source_sha256": pdf["sha256"], "source_logical_name": pdf["logical_name"],
        "page_json_version_id": "gfpstorev1:json:" + "c" * 64,
        "physical_page": 4, "selected_page_ordinal": 3,
        "page_json": {"status": "PRIMARY_FINANCIAL_STATEMENT", "sections": [{
            "content_kind": "PRIMARY_STATEMENT", "statement_type": "CASH_FLOW",
            "title_exact": "Printed caption, transcribed incorrectly",
            "narratives_exact": ["Raw text retained."],
            "tables": [{"title_exact": None, "columns": [
                {"value_kind": "UNKNOWN", "header_path_exact": ["Kỳ này"]},
                {"value_kind": "MONEY", "header_path_exact": ["Kỳ trước"]},
            ], "rows": [{"row_kind": "GROUP", "label_exact": "Raw owner",
                         "hierarchy_path_exact": ["Raw owner"], "values_exact": [None, ""]},
                        {"row_kind": "ITEM", "label_exact": "Raw amount",
                         "hierarchy_path_exact": ["Raw owner", "Raw amount"], "values_exact": ["-", "(14)"]}]}],
        }]},
    }
    after = deepcopy(record["page_json"])
    after["sections"][0]["title_exact"] = "Exact printed replacement caption"
    ref = {"path": "/synthetic/not-opened.json", "sha256": "d" * 64, "size_bytes": 99}
    repair = {
        "repair_id": "synthetic:caption:one", "repair_kind": "SECTION_TITLE_PDF_VISIBLE_EXACT",
        "locator": {"page_json_version_id": record["page_json_version_id"], "physical_page": 4,
                    "selected_page_ordinal": 3, "section_id": "s1", "json_pointer": "/sections/0/title_exact"},
        "before_exact": record["page_json"]["sections"][0]["title_exact"],
        "after_exact": after["sections"][0]["title_exact"],
        "original_page_object_canonical_sha256": core._digest(record["page_json"]), "evaluation_page_object_canonical_sha256": core._digest(after),
        "original_section_object_canonical_sha256": core._digest(record["page_json"]["sections"][0]),
        "evaluation_section_object_canonical_sha256": core._digest(after["sections"][0]),
        "review_evidence": {"manual_review_ref": deepcopy(ref), "pixel_candidate_ref": deepcopy(ref)},
    }
    registry = {"format_version": core._FORMAT, "family_id": "INCOME_TAX",
                "sources": [{"document_id": record["document_id"], "pdf_source": deepcopy(pdf), "repairs": [repair]}]}
    return [record], registry, pdf


def apply(records, registry, pdf, legacy=None):
    return core.apply_registered_section_caption_repairs_v1(
        records, registry=registry, source_pdf_identity=pdf,
        legacy_repair_page_axis=[] if legacy is None else legacy,
    )


class SectionCaptionRepairTests(unittest.TestCase):
    def test_document_id_matches_independent_one_lf_storage_golden(self):
        # Fixed bytes and digest are independent of this core's JSON/ID helpers.
        # This is synthetic identity evidence only, never a real source pin.
        material = (
            b'{"source_logical_name":"synthetic/report.pdf",'
            b'"source_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
            b'"source_size_bytes":123}\n'
        )
        expected_hash = "064e2f569817c0d61491e768fcf9b4c89646ba280de516a1aa9bc418491d8843"
        expected_id = "gfpstorev1:document:" + expected_hash
        self.assertEqual(len(material), 154)
        self.assertTrue(material.endswith(b"\n"))
        self.assertFalse(material.endswith(b"\n\n"))
        self.assertEqual(sha256(material).hexdigest(), expected_hash)
        self.assertNotEqual(sha256(material[:-1]).hexdigest(), expected_hash)
        self.assertNotEqual(sha256(material + b"\n").hexdigest(), expected_hash)
        records, registry, pdf = fixture()
        self.assertEqual(core._document_id(pdf), expected_id)
        self.assertEqual(records[0]["document_id"], expected_id)
        self.assertEqual(registry["sources"][0]["document_id"], expected_id)

    def test_actual_record_shape_omits_pdf_size_and_keeps_table_title_null(self):
        records, registry, pdf = fixture()
        self.assertEqual(set(records[0]), {
            "document_id", "document_ordinal", "source_sha256", "source_logical_name",
            "page_json_version_id", "physical_page", "selected_page_ordinal", "page_json",
        })
        self.assertNotIn("source_size_bytes", records[0])
        self.assertNotIn("size_bytes", records[0])
        result, receipt = apply(records, registry, pdf)
        self.assertEqual(set(result[0]), set(records[0]))
        self.assertIsNone(records[0]["page_json"]["sections"][0]["tables"][0]["title_exact"])
        self.assertIsNone(result[0]["page_json"]["sections"][0]["tables"][0]["title_exact"])
        self.assertEqual(receipt["occurrences"][0]["pdf_source"]["size_bytes"], 123)
        self.assertFalse(any(receipt["capabilities"].values()))

    def test_exact_one_field_only_no_authority_no_source_mutation(self):
        records, registry, pdf = fixture()
        before = deepcopy((records, registry, pdf))
        result, receipt = apply(records, registry, pdf)
        self.assertEqual((records, registry, pdf), before)
        self.assertNotEqual(result, records)
        self.assertTrue(receipt["private_caption_modified"])
        self.assertTrue(all(value is False for value in receipt["capabilities"].values()))
        self.assertFalse(receipt["receipt_hash_is_approval"])
        self.assertFalse(receipt["original_source_modified"])
        self.assertFalse(receipt["monetary_cells_modified"])
        self.assertEqual(result[0]["page_json"]["sections"][0]["tables"],
                         records[0]["page_json"]["sections"][0]["tables"])
        self.assertEqual(result[0]["page_json"]["sections"][0]["narratives_exact"], ["Raw text retained."])
        self.assertIsNone(result[0]["page_json"]["sections"][0]["tables"][0]["title_exact"])
        occurrence = receipt["occurrences"][0]
        self.assertEqual(occurrence["before_utf8_sha256"],
                         sha256(occurrence["before_exact"].encode("utf-8")).hexdigest())

    def test_fresh_original_replay_exact_and_clone_is_not_original_input(self):
        records, registry, pdf = fixture()
        result, receipt = apply(records, registry, pdf)
        replay = core.replay_registered_section_caption_repairs_v1(
            records, result, receipt, registry=registry, source_pdf_identity=pdf, legacy_repair_page_axis=[])
        self.assertEqual(replay, receipt)
        with self.assertRaises(core.SectionCaptionRepairV1Error):
            apply(result, registry, pdf)

    def test_pointer_locator_before_and_hash_drift(self):
        for key, bad in [
            ("json_pointer", "/sections/0/tables/0/title_exact"), ("section_id", "s2"),
            ("physical_page", 5), ("selected_page_ordinal", 4),
            ("page_json_version_id", "gfpstorev1:json:" + "e" * 64),
            ("before_exact", "Not the original"), ("original_page_object_canonical_sha256", "e" * 64),
            ("evaluation_page_object_canonical_sha256", "e" * 64), ("original_section_object_canonical_sha256", "e" * 64),
            ("evaluation_section_object_canonical_sha256", "e" * 64),
        ]:
            with self.subTest(key=key):
                records, registry, pdf = fixture()
                repair = registry["sources"][0]["repairs"][0]
                (repair["locator"] if key in repair["locator"] else repair)[key] = bad
                with self.assertRaises(core.SectionCaptionRepairV1Error):
                    apply(records, registry, pdf)

    def test_partial_registered_or_runtime_source_identity_rejected(self):
        for target, key, bad in [
            ("registered", "document_id", "gfpstorev1:document:" + "e" * 64),
            ("pdf", "logical_name", "synthetic/foreign.pdf"), ("pdf", "sha256", "e" * 64),
            ("pdf", "size_bytes", 124), ("runtime", "document_id", "not-an-id"),
            ("runtime", "source_sha256", "e" * 64),
        ]:
            with self.subTest(target=target, key=key):
                records, registry, pdf = fixture()
                if target == "registered":
                    registry["sources"][0][key] = bad
                elif target == "pdf":
                    registry["sources"][0]["pdf_source"][key] = bad
                else:
                    records[0][key] = bad
                with self.assertRaises(core.SectionCaptionRepairV1Error):
                    apply(records, registry, pdf)

    def test_duplicate_source_repair_or_raw_axis_rejected(self):
        for mutation in ("source", "repair", "runtime"):
            with self.subTest(mutation=mutation):
                records, registry, pdf = fixture()
                if mutation == "source":
                    registry["sources"].append(deepcopy(registry["sources"][0]))
                elif mutation == "repair":
                    registry["sources"][0]["repairs"].append(deepcopy(registry["sources"][0]["repairs"][0]))
                else:
                    records.append(deepcopy(records[0]))
                with self.assertRaises(core.SectionCaptionRepairV1Error):
                    apply(records, registry, pdf)

    def test_second_caption_same_page_requires_separate_composition(self):
        records, registry, pdf = fixture()
        second = deepcopy(registry["sources"][0]["repairs"][0])
        second["repair_id"] = "synthetic:caption:two"
        second["locator"]["section_id"] = "s2"
        second["locator"]["json_pointer"] = "/sections/1/title_exact"
        registry["sources"][0]["repairs"].append(second)
        with self.assertRaises(core.SectionCaptionRepairV1Error):
            apply(records, registry, pdf)

    def test_legacy_page_overlap_or_partial_identity_rejected(self):
        for mutation in ("same_vid", "same_physical", "foreign_pdf_same_vid"):
            with self.subTest(mutation=mutation):
                records, registry, pdf = fixture()
                old = {"repair_id": "old:repair:metadata-not-approval", "pdf_source": deepcopy(pdf),
                       "page_json_version_id": records[0]["page_json_version_id"], "physical_page": 4}
                if mutation == "same_physical":
                    old["page_json_version_id"] = "gfpstorev1:json:" + "e" * 64
                elif mutation == "foreign_pdf_same_vid":
                    old["pdf_source"]["sha256"] = "e" * 64
                with self.assertRaises(core.SectionCaptionRepairV1Error):
                    apply(records, registry, pdf, [old])

    def test_disjoint_legacy_target_is_retained_as_unapproved_metadata(self):
        records, registry, pdf = fixture()
        legacy = [{"repair_id": "old:repair:one", "pdf_source": deepcopy(pdf),
                   "page_json_version_id": "gfpstorev1:json:" + "e" * 64, "physical_page": 5}]
        result, receipt = apply(records, registry, pdf, legacy)
        self.assertEqual(receipt["declared_legacy_axis_object_canonical_sha256"], core._digest(legacy))
        self.assertFalse(receipt["capabilities"]["legacy_axis_independently_authenticated"])
        self.assertEqual(len(result), 1)

    def test_noncaption_original_poison_cannot_match_before_hash(self):
        for mutation in ("table", "row", "header", "blank", "dash", "unknown_kind", "narrative"):
            with self.subTest(mutation=mutation):
                records, registry, pdf = fixture()
                section = records[0]["page_json"]["sections"][0]
                table = section["tables"][0]
                if mutation == "table":
                    table["title_exact"] = "Unexpected"
                elif mutation == "row":
                    table["rows"].reverse()
                elif mutation == "header":
                    table["columns"][0]["header_path_exact"].append("2026")
                elif mutation == "blank":
                    table["rows"][0]["values_exact"][0] = "0"
                elif mutation == "dash":
                    table["rows"][1]["values_exact"][0] = "0"
                elif mutation == "unknown_kind":
                    table["columns"][0]["value_kind"] = "MONEY"
                else:
                    section["narratives_exact"].append("Unexpected")
                with self.assertRaises(core.SectionCaptionRepairV1Error):
                    apply(records, registry, pdf)

    def test_resealed_receipt_cannot_hide_output_or_receipt_poison(self):
        for mutation in ("value", "extra_receipt", "drop_occurrence", "claim_approval"):
            with self.subTest(mutation=mutation):
                records, registry, pdf = fixture()
                result, receipt = apply(records, registry, pdf)
                if mutation == "value":
                    result[0]["page_json"]["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = "0"
                    receipt["evaluation_records_object_canonical_sha256"] = core._digest(result)
                elif mutation == "extra_receipt":
                    receipt["occurrences"].append(deepcopy(receipt["occurrences"][0]))
                elif mutation == "drop_occurrence":
                    receipt["occurrences"] = []
                else:
                    receipt["capabilities"]["production_permission_granted"] = True
                receipt["receipt_id"] = "f39captionclonev1:" + core._digest(
                    {key: value for key, value in receipt.items() if key != "receipt_id"})
                with self.assertRaises(core.SectionCaptionRepairV1Error):
                    core.replay_registered_section_caption_repairs_v1(
                        records, result, receipt, registry=registry,
                        source_pdf_identity=pdf, legacy_repair_page_axis=[])

    def test_no_caller_hash_or_flag_can_turn_candidate_into_approval(self):
        for key, value in (("approved", True), ("expected_registry_sha256", "e" * 64)):
            records, registry, pdf = fixture()
            registry[key] = value
            with self.assertRaises(core.SectionCaptionRepairV1Error):
                apply(records, registry, pdf)
        records, registry, pdf = fixture()
        registry["activation_status"] = "INACTIVE_NOT_APPROVED"
        with self.assertRaises(core.SectionCaptionRepairV1Error):
            apply(records, registry, pdf)

    def test_fully_rewritten_declaration_is_not_a_trusted_registry(self):
        records, registry, pdf = fixture()
        repair = registry["sources"][0]["repairs"][0]
        repair["after_exact"] = "Different unapproved candidate, not accepted PDF text"
        after = deepcopy(records[0]["page_json"])
        after["sections"][0]["title_exact"] = repair["after_exact"]
        repair["evaluation_page_object_canonical_sha256"] = core._digest(after)
        repair["evaluation_section_object_canonical_sha256"] = core._digest(after["sections"][0])
        _, receipt = apply(records, registry, pdf)
        self.assertTrue(all(value is False for value in receipt["capabilities"].values()))
        self.assertEqual(receipt["status"], core._STATUS)

    def test_foreign_document_is_unchanged_not_a_caption_permission(self):
        records, registry, pdf = fixture()
        registry["sources"][0]["pdf_source"] = {"logical_name": "other.pdf", "sha256": "f" * 64, "size_bytes": 2}
        registry["sources"][0]["document_id"] = core._document_id(registry["sources"][0]["pdf_source"])
        registry["sources"][0]["repairs"][0]["locator"]["page_json_version_id"] = "gfpstorev1:json:" + "e" * 64
        result, receipt = apply(records, registry, pdf)
        self.assertEqual(result, records)
        self.assertEqual(receipt["occurrences"], [])
        self.assertFalse(receipt["private_caption_modified"])

    def test_plain_types_nonfinite_surrogate_and_noops_are_rejected(self):
        for mutation in ("bool_ordinal", "nan", "surrogate", "noop", "tuple_records"):
            with self.subTest(mutation=mutation):
                records, registry, pdf = fixture()
                repair = registry["sources"][0]["repairs"][0]
                if mutation == "bool_ordinal":
                    repair["locator"]["physical_page"] = True
                elif mutation == "nan":
                    records[0]["page_json"]["bad"] = float("nan")
                elif mutation == "surrogate":
                    repair["after_exact"] = "\ud800"
                elif mutation == "noop":
                    repair["after_exact"] = repair["before_exact"]
                else:
                    records = tuple(records)
                with self.assertRaises(core.SectionCaptionRepairV1Error):
                    apply(records, registry, pdf)


    def test_derived_document_identity_cannot_be_opaque_or_ambiguous(self):
        for field, value in (("logical_name", "renamed.pdf"), ("sha256", "e" * 64), ("size_bytes", 124)):
            with self.subTest(field=field):
                records, registry, pdf = fixture()
                registry["sources"][0]["pdf_source"][field] = value
                with self.assertRaises(core.SectionCaptionRepairV1Error):
                    apply(records, registry, pdf)
        records, registry, pdf = fixture()
        records[0]["document_id"] = "gfpstorev1:document:" + "e" * 64
        with self.assertRaises(core.SectionCaptionRepairV1Error):
            apply(records, registry, pdf)

    def test_same_vid_foreign_derived_source_cannot_be_silently_ignored(self):
        records, registry, pdf = fixture()
        foreign = registry["sources"][0]
        foreign["pdf_source"] = {"logical_name": "foreign.pdf", "sha256": "e" * 64, "size_bytes": 124}
        foreign["document_id"] = core._document_id(foreign["pdf_source"])
        with self.assertRaises(core.SectionCaptionRepairV1Error):
            apply(records, registry, pdf)

    def test_identical_pdf_bytes_different_logical_names_remain_distinct(self):
        records, registry, pdf = fixture()
        foreign = deepcopy(registry["sources"][0])
        foreign["pdf_source"]["logical_name"] = "other/same-bytes.pdf"
        foreign["document_id"] = core._document_id(foreign["pdf_source"])
        foreign["repairs"][0]["repair_id"] = "synthetic:foreign"
        foreign["repairs"][0]["locator"]["page_json_version_id"] = "gfpstorev1:json:" + "e" * 64
        registry["sources"].append(foreign)
        result, receipt = apply(records, registry, pdf)
        self.assertNotEqual(result, records)
        self.assertEqual(len(receipt["occurrences"]), 1)
        self.assertFalse(any(receipt["capabilities"].values()))

    def test_record_order_is_exact_source_axis_not_implicitly_sorted(self):
        records, registry, pdf = fixture()
        other = deepcopy(records[0])
        other.update(page_json_version_id="gfpstorev1:json:" + "e" * 64,
                     physical_page=5, selected_page_ordinal=4)
        records.append(other)
        result, receipt = apply(records, registry, pdf)
        self.assertEqual([record["physical_page"] for record in result], [4, 5])
        with self.assertRaises(core.SectionCaptionRepairV1Error):
            apply(list(reversed(records)), registry, pdf)
        with self.assertRaises(core.SectionCaptionRepairV1Error):
            core.replay_registered_section_caption_repairs_v1(
                records, list(reversed(result)), receipt, registry=registry,
                source_pdf_identity=pdf, legacy_repair_page_axis=[])

    def test_non_target_poison_and_reseal_fail_against_unchanged_original(self):
        records, registry, pdf = fixture()
        other = deepcopy(records[0])
        other.update(page_json_version_id="gfpstorev1:json:" + "e" * 64,
                     physical_page=5, selected_page_ordinal=4)
        records.append(other)
        result, receipt = apply(records, registry, pdf)
        result[1]["page_json"]["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = "0"
        receipt["evaluation_records_object_canonical_sha256"] = core._digest(result)
        receipt["receipt_id"] = "f39captionclonev1:" + core._digest(
            {key: value for key, value in receipt.items() if key != "receipt_id"})
        with self.assertRaises(core.SectionCaptionRepairV1Error):
            core.replay_registered_section_caption_repairs_v1(
                records, result, receipt, registry=registry,
                source_pdf_identity=pdf, legacy_repair_page_axis=[])

    def test_non_target_foreign_identity_and_duplicate_axes_reject(self):
        for field, value in (("document_id", "gfpstorev1:document:" + "f" * 64),
                             ("document_ordinal", 8), ("physical_page", 4), ("selected_page_ordinal", 3)):
            records, registry, pdf = fixture()
            other = deepcopy(records[0])
            other.update(page_json_version_id="gfpstorev1:json:" + "e" * 64,
                         physical_page=5, selected_page_ordinal=4)
            other[field] = value
            records.append(other)
            with self.subTest(field=field), self.assertRaises(core.SectionCaptionRepairV1Error):
                apply(records, registry, pdf)

    def test_returned_clones_cannot_poison_a_later_declaration_replay(self):
        records, registry, pdf = fixture()
        result, receipt = apply(records, registry, pdf)
        copied = core.validate_section_caption_registry_v1(registry)
        copied["sources"][0]["repairs"][0]["after_exact"] = "Poisoned clone"
        result[0]["page_json"]["sections"][0]["title_exact"] = "Poisoned clone"
        receipt["capabilities"]["production_permission_granted"] = True
        actual, fresh = apply(records, registry, pdf)
        self.assertEqual(actual[0]["page_json"]["sections"][0]["title_exact"],
                         registry["sources"][0]["repairs"][0]["after_exact"])
        self.assertFalse(any(fresh["capabilities"].values()))

    def test_declarative_schema_rejects_all_approval_activation_flag_variants(self):
        for field, value in (("approved", True), ("approved", False),
                             ("expected_registry_sha256", "e" * 64),
                             ("activation_status", "ACTIVE"), ("activation_status", "INACTIVE_NOT_APPROVED")):
            records, registry, pdf = fixture()
            registry[field] = value
            with self.subTest(field=field), self.assertRaises(core.SectionCaptionRepairV1Error):
                apply(records, registry, pdf)



    def test_shared_python_page_alias_cannot_modify_a_non_target_page(self):
        records, registry, pdf = fixture()
        other = deepcopy(records[0])
        other.update(page_json_version_id="gfpstorev1:json:" + "e" * 64,
                     physical_page=5, selected_page_ordinal=4)
        other["page_json"] = records[0]["page_json"]
        records.append(other)
        original = deepcopy(records)
        result, receipt = apply(records, registry, pdf)
        self.assertEqual(records, original)
        self.assertEqual(result[1], original[1])
        self.assertNotEqual(result[0]["page_json"]["sections"][0]["title_exact"],
                            result[1]["page_json"]["sections"][0]["title_exact"])
        self.assertFalse(any(receipt["capabilities"].values()))


    def test_object_hash_domain_does_not_claim_blob_or_validator_hash_equivalence(self):
        records, registry, pdf = fixture()
        records[0]["stored_blob_sha256"] = "e" * 64
        records[0]["validated_json_sha256"] = "f" * 64
        result, receipt = apply(records, registry, pdf)
        self.assertEqual(result[0]["stored_blob_sha256"], "e" * 64)
        self.assertEqual(result[0]["validated_json_sha256"], "f" * 64)
        self.assertEqual(receipt["object_hash_domain"], core._OBJECT_HASH_DOMAIN)
        self.assertFalse(receipt["official_stored_blob_or_validator_hash_equivalence_claimed"])
        self.assertEqual(receipt["occurrences"][0]["original_page_object_canonical_sha256"],
                         core._digest(records[0]["page_json"]))

if __name__ == "__main__":
    unittest.main()
