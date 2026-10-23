"""INACTIVE synthetic primitive regressions; not public-pipeline/source approval.

Materialize only after root review. No actual PRIMARY registration is supplied.
These tests do not establish PDF authentication, unit ownership or admission.
"""
from __future__ import annotations

from copy import deepcopy

import pytest
import test_gemini_json_operating_expense_family_v1 as fixture

from bctc_ai.evaluation import gemini_json_operating_expense_family_v1 as family
from bctc_ai.evaluation import gemini_json_operating_expense_primary_witness_v1 as witness
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

VID = "gfpstorev1:json:" + "1" * 64


def _object_hashes(page):
    section = page["sections"][0]
    table = section["tables"][0]
    return {
        "original_page_json_sha256": canonical_json_sha256_v1(page),
        "original_section_json_sha256": canonical_json_sha256_v1(section),
        "original_table_json_sha256": canonical_json_sha256_v1(table),
        "original_row_json_sha256": canonical_json_sha256_v1(table["rows"][1]),
    }


def _seal(spec):
    for item in spec["witnesses"]:
        item["witness_id"] = "gjoepwv1:witness:" + canonical_json_sha256_v1(
            {k: v for k, v in item.items() if k != "witness_id"}
        )
    spec["witness_axis_sha256"] = canonical_json_sha256_v1(spec["witnesses"])
    return spec


def _case():
    source = {"source_logical_name": "synthetic/primary.pdf",
              "source_sha256": "2" * 64, "source_size_bytes": 4096}
    document = {"document_id": "gfpstorev1:document:" + canonical_json_sha256_v1(source),
                "document_ordinal": 7, "source_logical_name": source["source_logical_name"],
                "source_sha256": source["source_sha256"]}
    columns = [{"header_path_exact": ["Quý I", year], "value_kind": "MONEY"}
               for year in ("Năm nay", "Năm trước", "Lũy kế năm nay", "Lũy kế năm trước")]
    row = {"label_exact": "Chi phí hoạt động", "hierarchy_path_exact": ["Chi phí hoạt động"],
           "row_kind": "ITEM", "values_exact": ["123", None, None, None]}
    table = {"title_exact": "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG",
             "unit_exact": "Triệu đồng", "columns": columns,
             "rows": [{"label_exact": "Unrelated", "row_kind": "ITEM",
                       "hierarchy_path_exact": [], "values_exact": ["1", "-", None, "2"]}, row]}
    section = {"title_exact": "BÁO CÁO KẾT QUẢ HOẠT ĐỘNG",
               "content_kind": "PRIMARY_STATEMENT", "statement_type": "INCOME_STATEMENT",
               "tables": [table], "narratives": ["Unchanged narrative"]}
    page = {"status": "PRIMARY_FINANCIAL_STATEMENT", "sections": [section], "unrelated": None}
    pages = {VID: page}
    axis = [{**document, "page_json_version_id": VID,
             "physical_page": 6, "selected_page_ordinal": 6}]
    declarations = []
    for column, after in zip((2, 3, 4), ("(456,789)", "-123,456", "789.123"), strict=True):
        declarations.append({
            "witness_kind": witness.KIND, "source": deepcopy(source),
            "locator": {"page_json_version_id": VID, "physical_page": 6,
                        "selected_page_ordinal": 6, "section_id": "s1",
                        "table_id": "t1", "row_ordinal": 2, "column_ordinal": column},
            "original_object_hashes": _object_hashes(page),
            "expected_context": {
                "page_status": page["status"], "content_kind": section["content_kind"],
                "statement_type": section["statement_type"], "row_label_exact": row["label_exact"],
                "hierarchy_path_exact": deepcopy(row["hierarchy_path_exact"]),
                "row_kind": row["row_kind"],
                "column_header_path_exact": deepcopy(columns[column - 1]["header_path_exact"]),
                "column_value_kind": "MONEY",
            },
            "before_exact": None, "after_exact": after, "observed_pdf_glyph": after,
            "render": {"image_sha256": "3" * 64, "image_size_bytes": 5000,
                       "media_type": "image/png", "physical_page": 6, "pixel_height": 100,
                       "pixel_width": 200, "render_dpi": 300, "render_receipt_sha256": "4" * 64},
            "crop_evidence": {"bbox_pixels_xyxy": [column * 20, 20, column * 20 + 10, 30],
                              "pixel_height": 10, "pixel_width": 10, "rgb_sha256": "5" * 64},
        })
    spec = _seal({"family_id": "OPERATING_EXPENSE", "format_version": witness.FORMAT,
                  "policy": witness.POLICY, "render_contract": deepcopy(witness.RENDER_CONTRACT),
                  "witnesses": declarations})
    return pages, document, axis, spec


def _compiled(spec):
    return family.compile_gemini_json_operating_expense_family_specs_v1(
        fixture._json("tm-operating-expense-topology-v1.json"),
        fixture._json("tm-operating-expense-evaluation-v1.json"),
        fixture._json("tm-operating-expense-schema-binding-v1.json"), None, spec,
    )


def _project(pages, document, axis, spec):
    return family._primary_witness_projection_v1(
        pages=pages, document=document, selected_page_axis=axis, compiled_specs=_compiled(spec)
    )


def test_three_original_same_row_nulls_project_atomically_with_no_other_change():
    pages, document, axis, spec = _case()
    before = canonical_json_bytes_v1([pages, document, axis, spec])
    private, receipts = _project(pages, document, axis, spec)
    expected = deepcopy(pages)
    expected[VID]["sections"][0]["tables"][0]["rows"][1]["values_exact"] = [
        "123", "(456,789)", "-123,456", "789.123"
    ]
    assert same_typed_json_v1(private, expected)
    assert len(receipts) == 3
    assert len({r["witness"]["witness_id"] for r in receipts}) == 3
    assert len({r["original_object_hashes"]["original_row_json_sha256"] for r in receipts}) == 1
    final_hashes = _object_hashes(private[VID])
    for receipt in receipts:
        assert receipt["evaluation_object_hashes"] == {
            k.replace("original_", "evaluation_", 1): v for k, v in final_hashes.items()
        }
        assert set(receipt["permissions"].values()) == {False}
        material = {k: v for k, v in receipt.items() if k != "receipt_id"}
        assert receipt["receipt_id"] == "gjoepwv1:projection:" + canonical_json_sha256_v1(material)
    private[VID]["sections"][0]["narratives"].append("poison")
    receipts[0]["witness"]["expected_context"]["hierarchy_path_exact"].append("poison")
    assert canonical_json_bytes_v1([pages, document, axis, spec]) == before


@pytest.mark.parametrize("field", [
    "original_page_json_sha256", "original_section_json_sha256",
    "original_table_json_sha256", "original_row_json_sha256",
])
def test_named_original_hash_mismatch_even_resealed_rejects(field):
    pages, document, axis, spec = _case()
    for item in spec["witnesses"]:
        item["original_object_hashes"][field] = "9" * 64
    _seal(spec)
    before = deepcopy(pages)
    with pytest.raises(witness.F36PrimaryWitnessV1Error, match="ORIGINAL"):
        _project(pages, document, axis, spec)
    assert same_typed_json_v1(pages, before)


@pytest.mark.parametrize("attack", [
    "source_sha", "source_name", "source_size", "vid", "physical", "selected",
    "section", "table", "row", "column", "document_ordinal_bool",
    "axis_ordinal_float", "missing_page", "duplicate_page",
])
def test_full_typed_source_and_positional_axes_fail_closed(attack):
    pages, document, axis, spec = _case()
    if attack == "source_sha":
        document["source_sha256"] = axis[0]["source_sha256"] = "8" * 64
    elif attack == "source_name":
        document["source_logical_name"] = axis[0]["source_logical_name"] = "wrong.pdf"
    elif attack == "source_size":
        for item in spec["witnesses"]:
            item["source"]["source_size_bytes"] += 1
    elif attack in {"vid", "physical", "selected", "section", "table", "row", "column"}:
        field, value = {
            "vid": ("page_json_version_id", "gfpstorev1:json:" + "8" * 64),
            "physical": ("physical_page", 7), "selected": ("selected_page_ordinal", 7),
            "section": ("section_id", "s2"), "table": ("table_id", "t2"),
            "row": ("row_ordinal", 3), "column": ("column_ordinal", 9),
        }[attack]
        targets = spec["witnesses"] if attack != "column" else spec["witnesses"][-1:]
        for item in targets:
            item["locator"][field] = value
            if attack == "physical":
                item["render"]["physical_page"] = value
    elif attack == "document_ordinal_bool":
        document["document_ordinal"] = axis[0]["document_ordinal"] = True
    elif attack == "axis_ordinal_float":
        axis[0]["selected_page_ordinal"] = 6.0
    elif attack == "missing_page":
        pages.clear()
    else:
        axis.append(deepcopy(axis[0]))
    _seal(spec)
    snapshot = deepcopy(pages)
    with pytest.raises(witness.F36PrimaryWitnessV1Error):
        _project(pages, document, axis, spec)
    assert same_typed_json_v1(pages, snapshot)


@pytest.mark.parametrize("field,value", [
    ("row_ordinal", True), ("row_ordinal", 2.0), ("column_ordinal", True),
    ("physical_page", 6.0), ("selected_page_ordinal", False),
])
def test_declared_bool_float_ordinals_rejected_before_lookup(field, value):
    _pages, _doc, _axis, spec = _case()
    for item in spec["witnesses"]:
        item["locator"][field] = value
    _seal(spec)
    with pytest.raises(witness.F36PrimaryWitnessV1Error):
        witness.validate_f36_primary_witness_spec_v1(spec)


@pytest.mark.parametrize("attack", [
    "page_kind", "section_kind", "statement", "header", "value_kind",
    "owner_not_configured", "late_nonnull", "row_kind",
])
def test_resealed_original_hashes_cannot_waive_raw_context_or_before_null(attack):
    pages, document, axis, spec = _case()
    page = pages[VID]
    section, table = page["sections"][0], page["sections"][0]["tables"][0]
    row = table["rows"][1]
    if attack == "page_kind":
        page["status"] = "FINANCIAL_NOTES"
    elif attack == "section_kind":
        section["content_kind"] = "FINANCIAL_NOTE"
    elif attack == "statement":
        section["statement_type"] = "CASH_FLOW"
    elif attack == "header":
        table["columns"][3]["header_path_exact"] = ["Conflicting period"]
    elif attack == "value_kind":
        table["columns"][3]["value_kind"] = "UNKNOWN"
    elif attack == "owner_not_configured":
        row["label_exact"] = "Thu nhập lãi"
        for item in spec["witnesses"]:
            item["expected_context"]["row_label_exact"] = row["label_exact"]
    elif attack == "late_nonnull":
        row["values_exact"][3] = "7"
    else:
        row["row_kind"] = "GROUP"
    for item in spec["witnesses"]:
        item["original_object_hashes"] = _object_hashes(page)
    _seal(spec)
    snapshot = canonical_json_bytes_v1(pages)
    with pytest.raises(witness.F36PrimaryWitnessV1Error):
        _project(pages, document, axis, spec)
    assert canonical_json_bytes_v1(pages) == snapshot


@pytest.mark.parametrize("token", [
    "", "-", "−", "0", "(0)", "-0", "0,000", "000", " 123", "123 ", "+123",
    "12.34", "1,23", "1,234.567", "１23", "١٢٣", "123\u0301", "(123", "123\n",
])
def test_non_integer_dash_blank_zero_decimal_unicode_tokens_not_granted(token):
    _pages, _document, _axis, spec = _case()
    spec["witnesses"][2]["after_exact"] = token
    spec["witnesses"][2]["observed_pdf_glyph"] = token
    _seal(spec)
    with pytest.raises(witness.F36PrimaryWitnessV1Error):
        witness.validate_f36_primary_witness_spec_v1(spec)


@pytest.mark.parametrize("attack", [
    "duplicate_cell", "duplicate_id", "axis_hash", "render_bool",
    "crop_float", "crop_bounds", "different_original_row", "extra_permission",
])
def test_spec_duplicate_render_crop_and_declared_axis_negatives(attack):
    _pages, _document, _axis, spec = _case()
    if attack == "duplicate_cell":
        spec["witnesses"][2] = deepcopy(spec["witnesses"][1])
    elif attack == "duplicate_id":
        _seal(spec)
        spec["witnesses"][2]["witness_id"] = spec["witnesses"][1]["witness_id"]
    elif attack == "axis_hash":
        spec["witness_axis_sha256"] = "9" * 64
    elif attack == "render_bool":
        for item in spec["witnesses"]:
            item["render"]["render_dpi"] = True
    elif attack == "crop_float":
        spec["witnesses"][2]["crop_evidence"]["bbox_pixels_xyxy"][0] = 60.0
    elif attack == "crop_bounds":
        spec["witnesses"][2]["crop_evidence"]["bbox_pixels_xyxy"][2] = 1000
    elif attack == "different_original_row":
        spec["witnesses"][2]["locator"]["row_ordinal"] = 1
    else:
        spec["approved"] = True
    if attack not in {"duplicate_id", "axis_hash"}:
        _seal(spec)
    with pytest.raises(witness.F36PrimaryWitnessV1Error):
        witness.validate_f36_primary_witness_spec_v1(spec)


def test_compiled_spec_reseal_is_not_a_pixel_or_financial_permission():
    pages, document, axis, spec = _case()
    spec["witnesses"][0]["after_exact"] = spec["witnesses"][0]["observed_pdf_glyph"] = "999"
    _seal(spec)  # Syntactic self-consistency is deliberately NOT approval.
    compiled = _compiled(spec)
    _private, receipts = family._primary_witness_projection_v1(
        pages=pages, document=document, selected_page_axis=axis, compiled_specs=compiled
    )
    assert all(set(receipt["permissions"].values()) == {False} for receipt in receipts)
    compiled[witness.HASH_KEY] = "9" * 64
    with pytest.raises(witness.F36PrimaryWitnessV1Error, match="compiled"):
        family._primary_witness_projection_v1(
            pages=pages, document=document, selected_page_axis=axis, compiled_specs=compiled
        )


def test_default_none_keeps_four_argument_compiled_and_old_dash_receipts_typed_exact():
    topology = fixture._json("tm-operating-expense-topology-v1.json")
    evaluation = fixture._json("tm-operating-expense-evaluation-v1.json")
    schema = fixture._json("tm-operating-expense-schema-binding-v1.json")
    dash = fixture._source_repair_spec()
    old_call = family.compile_gemini_json_operating_expense_family_specs_v1(topology, evaluation, schema, dash)
    explicit_none = family.compile_gemini_json_operating_expense_family_specs_v1(
        topology, evaluation, schema, dash, None
    )
    assert same_typed_json_v1(old_call, explicit_none)
    assert witness.SPEC_KEY not in old_call and witness.HASH_KEY not in old_call
    assert old_call["operating_expense_source_repairs"] == dash["repairs"]
    page = fixture._operating_page()
    page["sections"][0]["tables"][0]["rows"][12]["values_exact"][1] = None
    region = fixture._cluster(page)["component_regions"]
    inputs = {"pages": {fixture.VERSION_ID: page}, "regions": region}
    old_pages, old_receipts = family._apply_authenticated_source_repairs(
        **inputs, compiled_specs=old_call
    )
    none_pages, none_receipts = family._apply_authenticated_source_repairs(
        **inputs, compiled_specs=explicit_none
    )
    assert same_typed_json_v1([old_pages, old_receipts], [none_pages, none_receipts])
    assert len(old_receipts) == 1
    assert old_receipts[0]["repair"]["repair_id"] == dash["repairs"][0]["repair_id"]
    assert old_receipts[0]["receipt_id"].startswith("gjoefav1:source-repair-receipt:")
    legacy = fixture._json("tm-operating-expense-source-repair-v1.json")
    assert len(legacy["repairs"]) == 20
    legacy_compiled = family.compile_gemini_json_operating_expense_family_specs_v1(
        topology, evaluation, schema, legacy
    )
    legacy_none = family.compile_gemini_json_operating_expense_family_specs_v1(
        topology, evaluation, schema, legacy, None
    )
    assert same_typed_json_v1(legacy_compiled, legacy_none)
    assert legacy_compiled["operating_expense_source_repairs"] == legacy["repairs"]


def test_no_spec_and_unrelated_source_are_private_noop_not_permission():
    pages, document, axis, spec = _case()
    compiled = fixture._adapter_compiled()
    private, receipts = family._primary_witness_projection_v1(
        pages=pages, document=document, selected_page_axis=axis, compiled_specs=compiled
    )
    assert same_typed_json_v1(private, pages) and private is not pages and receipts == []
    foreign = {"source_logical_name": "other.pdf", "source_sha256": "8" * 64, "source_size_bytes": 8192}
    document["document_id"] = "gfpstorev1:document:" + canonical_json_sha256_v1(foreign)
    document["source_logical_name"], document["source_sha256"] = foreign["source_logical_name"], foreign["source_sha256"]
    for field in document:
        axis[0][field] = document[field]
    private, receipts = _project(pages, document, axis, spec)
    assert same_typed_json_v1(private, pages) and private is not pages and receipts == []


def _foreign_internal_borrow_case():
    pages, document, axis, spec = _case()
    foreign = {"source_logical_name": "foreign.pdf", "source_sha256": "8" * 64, "source_size_bytes": 8192}
    document.update(source_logical_name=foreign["source_logical_name"], source_sha256=foreign["source_sha256"],
                    document_id="gfpstorev1:document:" + canonical_json_sha256_v1(foreign))
    for field, value in document.items():
        axis[0][field] = value
    return pages, document, axis, spec


@pytest.mark.parametrize("mode", ["NO_SPEC", "FOREIGN", "APPLICABLE"])
def test_internal_borrow_only_changes_foreign_container_ownership_not_projection_facts(mode):
    pages, document, axis, spec = _foreign_internal_borrow_case() if mode == "FOREIGN" else _case()
    compiled = fixture._adapter_compiled() if mode == "NO_SPEC" else _compiled(spec)
    before = deepcopy([pages, document, axis, compiled])
    default, default_receipts = witness._primary_witness_projection_v1(
        pages=pages, document=document, selected_page_axis=axis, compiled_specs=compiled)
    internal, internal_receipts = witness._primary_witness_projection_v1(
        pages=pages, document=document, selected_page_axis=axis, compiled_specs=compiled,
        _borrow_nonapplicable_pages_v1=True)
    assert default is not pages
    assert (internal is pages) is (mode == "FOREIGN")
    assert same_typed_json_v1([default, default_receipts], [internal, internal_receipts])
    assert [pages, document, axis, compiled] == before
    assert bool(internal_receipts) is (mode == "APPLICABLE")


@pytest.mark.parametrize("flag", [0, 1, None, "true", {"approved": True}])
def test_internal_borrow_mode_is_not_a_coerced_or_json_approval_flag(flag):
    pages, document, axis, spec = _foreign_internal_borrow_case()
    with pytest.raises(witness.F36PrimaryWitnessV1Error, match="internal PRIMARY projection mode"):
        witness._primary_witness_projection_v1(pages=pages, document=document,
            selected_page_axis=axis, compiled_specs=_compiled(spec), _borrow_nonapplicable_pages_v1=flag)


@pytest.mark.parametrize("attack", ["logical-collision", "sha-collision", "document-collision",
                                   "missing-page", "extra-page", "spec-sha"])
def test_internal_foreign_borrow_preserves_all_identity_axis_and_spec_checks(attack):
    pages, document, axis, spec = _foreign_internal_borrow_case()
    compiled = _compiled(spec)
    source = spec["witnesses"][0]["source"]
    if attack == "logical-collision":
        document["source_logical_name"] = source["source_logical_name"]
    elif attack == "sha-collision":
        document["source_sha256"] = source["source_sha256"]
    elif attack == "document-collision":
        document["document_id"] = "gfpstorev1:document:" + canonical_json_sha256_v1(source)
    elif attack == "missing-page":
        pages.clear()
    elif attack == "extra-page":
        pages["gfpstorev1:json:" + "9" * 64] = deepcopy(next(iter(pages.values())))
    else:
        compiled[witness.HASH_KEY] = "0" * 64
    for field, value in document.items():
        axis[0][field] = value
    with pytest.raises(witness.F36PrimaryWitnessV1Error):
        witness._primary_witness_projection_v1(pages=pages, document=document,
            selected_page_axis=axis, compiled_specs=compiled, _borrow_nonapplicable_pages_v1=True)
