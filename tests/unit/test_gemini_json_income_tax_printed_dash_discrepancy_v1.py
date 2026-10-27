"""Synthetic negative cell observations; no real source/PDF approval is asserted."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled, _page, _primary_page, _record
from test_gemini_json_income_tax_source_label_discrepancy_v1 import (
    _one_pixel_rgb_png,
    _reseal,
    _reseal_candidate,
    _reseal_registry,
)

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation import gemini_json_income_tax_source_label_discrepancy_v1 as negative
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import READY, UNRESOLVED, _sum_record_cells
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

REASON = "SOURCE_PRINTED_DASH_VS_JSON_NUMERIC_DISCREPANCY"
CASES = ("primary_both", "primary_current", "note_comparative")
SYNTHETIC_PDF = b"%PDF-unit-owned-printed-dash-fixture\n"


def _fixture(monkeypatch, *, case="primary_both", ordinal=1):
    """Use the documented registry-loader seam, real source/context/hold checks."""
    note = case == "note_comparative"
    row_number, money = (4, [1, 2]) if note else (19, [4, 5])
    columns = [2] if note else ([4, 5] if case == "primary_both" else [4])
    before = {
        "label_exact": "Thu nhập không chịu thuế" if note else "8 Chi phí thuế TNDN hoãn lại",
        "hierarchy_path_exact": ["Thu nhập không chịu thuế" if note else "8 Chi phí thuế TNDN hoãn lại"],
        "row_kind": "ITEM",
        "values_exact": ["(60)", "0"] if note else [None, "-", "-", "0", "0" if case == "primary_both" else "(9.923)"],
    }
    rows = [{"label_exact": f"Khoản mục tham chiếu {n}", "hierarchy_path_exact": [f"Khoản mục tham chiếu {n}"],
             "row_kind": "ITEM", "values_exact": ["1", "1"] if note else [None, "1", "1", "1", "1"]}
            for n in range(1, row_number)]
    rows.append(deepcopy(before))
    page = _page(rows) if note else _primary_page(rows)
    if not note:
        section, table = page["sections"][0], page["sections"][0]["tables"][0]
        section["title_exact"] = ("Báo cáo kết quả hoạt động riêng\n"
                                  "cho giai đoạn từ ngày 01 tháng 01 năm 2025 đến ngày 31 tháng 3 năm 2025")
        table["columns"] = [
            {"header_path_exact": ["Thuyết minh"], "value_kind": "TEXT"},
            {"header_path_exact": ["Quý I", "Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Quý I", "Năm 2024", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Lũy kế từ đầu năm", "Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Lũy kế từ đầu năm", "Năm 2024", "Triệu đồng"], "value_kind": "MONEY"},
        ]
    source = {"source_logical_name": "synthetic/2025/printed-dash.pdf",
              "source_sha256": sha256(SYNTHETIC_PDF).hexdigest(), "source_size_bytes": len(SYNTHETIC_PDF)}
    source["document_id"] = "gfpstorev1:document:" + canonical_json_sha256_v1(source)
    png = _one_pixel_rgb_png()
    observation = {
        "classification": negative.PRINTED_DASH_CLASSIFICATION,
        "expected_role": "NON_TAXABLE_AGGREGATE" if note else "DEFERRED_TAX_NET",
        "source": source, "source_page_status": page["status"],
        "source_section_kind": "FINANCIAL_NOTE" if note else "PRIMARY_STATEMENT",
        "source_statement_type": "NOT_APPLICABLE" if note else "INCOME_STATEMENT",
        "locator": {"page_json_version_id": "gfpstorev1:json:" + "b" * 64, "physical_page": 63 if note else 7,
                    "section_id": "s1", "table_id": "t1", "row_ordinal": row_number,
                    "row_id": f"r{row_number}", "money_column_ordinals": money},
        "before_reference": before, "printed_dash_money_column_ordinals": columns,
        "review": {"authority": "SYNTHETIC_UNIT_LOADER_FIXTURE_NOT_REAL_APPROVAL",
                   "decision": "PRINTED_DASH_DIFFERS_FROM_JSON_NUMERIC_HOLD_NO_REPAIR",
                   "source_values_changed": False, "text_layer_claimed": False,
                   "printed_glyph_by_money_column": {str(n): "-" for n in columns},
                   "page_render": {"renderer": "pdftoppm", "resolution_dpi": 100, "format": "PNG",
                                   "alpha": False, "colorspace": "RGB", "width_pixels": 1, "height_pixels": 1,
                                   "sha256": sha256(png).hexdigest(), "size_bytes": len(png)}},
    }
    registry = {"format_version": "INCOME_TAX_REGISTERED_SOURCE_LABEL_DISCREPANCIES_V1",
                "family_id": "INCOME_TAX", "observations": [observation]}
    _reseal_registry(registry)
    monkeypatch.setattr(negative, "load_registered_negative_source_label_observations_v1", lambda: deepcopy(registry))
    record = _record(page)
    record.update(**{key: value for key, value in source.items() if key != "source_size_bytes"},
                  document_ordinal=ordinal, page_json_version_id=observation["locator"]["page_json_version_id"],
                  physical_page=observation["locator"]["physical_page"],
                  selected_page_ordinal=observation["locator"]["physical_page"])
    compiled = _adapter_compiled()
    context = family._source_context_receipt(
        compiled_specs=compiled, repair_receipts=[], root_controls=[], page_records=[record],
    )
    locator = {key: record[key] for key in negative._LOCATOR_KEYS}
    locator.update(section_id="s1", table_id="t1")
    mapping = {
        "role": observation["expected_role"], "report_norm_id": 5729 if note else 5726,
        "state": "SOURCE_OBSERVED_ROLE_ROW", "unit": "MILLION_VND",
        "values": [family._source_money(before["values_exact"][n - 1]) for n in money],
        "source_refs": [{"locator": locator, "row_ordinal": row_number, "row_id": f"r{row_number}",
                         "money_column_ordinals": money,
                         **{key: deepcopy(value) for key, value in before.items() if key != "values_exact"}}],
    }
    candidate = {"status": READY, "reasons": [], "closure_receipt": {}, "mappings": [mapping]}
    _reseal_candidate(candidate)
    return registry, candidate, context, [record], compiled, png


def _conflicts(fixture):
    _registry, candidate, context, records, compiled, _png = fixture
    return family._registered_negative_source_label_conflicts_v1(
        candidate, source_context=context, repaired_records=records, compiled_specs=compiled,
    )


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("ordinal", [1, 17, 204])
def test_registered_printed_dash_holds_exact_source_without_global_ordinal_routing(monkeypatch, case, ordinal):
    fixture = _fixture(monkeypatch, case=case, ordinal=ordinal)
    before = deepcopy(fixture[1:5])
    conflicts = _conflicts(fixture)
    assert len(conflicts) == 1
    assert conflicts[0]["classification"] == negative.PRINTED_DASH_CLASSIFICATION
    assert conflicts[0]["source_values_changed"] is False
    assert conflicts[0]["fresh_pdf_authentication_claimed"] is False
    assert fixture[1:5] == before


@pytest.mark.parametrize("case", CASES)
def test_ready_seal_withholds_whole_document_preserves_raw_zero_dash_and_other_lane(monkeypatch, case):
    fixture = _fixture(monkeypatch, case=case)
    _registry, candidate, context, records, compiled, _png = fixture
    before = deepcopy((candidate, context, records))
    result = family._seal_income_tax_source_controls(
        candidate, source_context=context, repaired_records=records, compiled_specs=compiled,
    )
    assert result["status"] == UNRESOLVED and result["mappings"] == [] and result["reasons"] == [REASON]
    assert (candidate, context, records) == before
    material = {key: value for key, value in result.items() if key != "candidate_id"}
    assert result["candidate_id"] == "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)
    if case == "primary_current":
        assert records[0]["page_json"]["sections"][0]["tables"][0]["rows"][-1]["values_exact"][-1] == "(9.923)"
    if case == "note_comparative":
        assert records[0]["page_json"]["sections"][0]["tables"][0]["rows"][-1]["values_exact"][0] == "(60)"


def test_a_different_mapping_role_cannot_hide_a_registered_bad_source_cell(monkeypatch):
    fixture = _fixture(monkeypatch)
    fixture[1]["mappings"][0]["role"] = "FAMILY_ROOT_TOTAL"
    _reseal_candidate(fixture[1])
    assert len(_conflicts(fixture)) == 1


@pytest.mark.parametrize("different", ["section", "table"])
def test_same_page_different_actual_table_with_repeated_local_row_ids_is_unrelated(monkeypatch, different):
    fixture = _fixture(monkeypatch)
    _registry, candidate, _context, records, compiled, _png = fixture
    page = records[0]["page_json"]
    if different == "section":
        other = deepcopy(page["sections"][0])
        page["sections"].append(other)
        table, section_id, table_id = other["tables"][0], "s2", "t1"
    else:
        table = deepcopy(page["sections"][0]["tables"][0])
        page["sections"][0]["tables"].append(table)
        section_id, table_id = "s1", "t2"
    table["rows"][-1]["values_exact"][-2:] = ["7", "8"]
    candidate["mappings"][0]["source_refs"][0]["locator"].update(section_id=section_id, table_id=table_id)
    candidate["mappings"][0]["values"] = [family._source_money(value) for value in ("7", "8")]
    _reseal_candidate(candidate)
    context = family._source_context_receipt(
        compiled_specs=compiled, repair_receipts=[], root_controls=[], page_records=records,
    )
    assert _conflicts((fixture[0], candidate, context, records, compiled, fixture[5])) == []


def test_actual_target_table_partial_source_identity_still_fails_closed(monkeypatch):
    fixture = _fixture(monkeypatch)
    fixture[1]["mappings"][0]["source_refs"][0]["locator"]["page_json_version_id"] = "gfpstorev1:json:" + "c" * 64
    _reseal_candidate(fixture[1])
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="partial registered-source locator"):
        _conflicts(fixture)


def test_actual_supported_same_role_aggregate_still_holds_its_bad_cited_source(monkeypatch):
    fixture = _fixture(monkeypatch)
    mapping = fixture[1]["mappings"][0]
    row = fixture[3][0]["page_json"]["sections"][0]["tables"][0]["rows"][0]
    other = deepcopy(mapping["source_refs"][0])
    other.update(row_ordinal=1, row_id="r1", **{key: deepcopy(row[key]) for key in (
        "label_exact", "hierarchy_path_exact", "row_kind",
    )})
    mapping["source_refs"].append(other)
    mapping["state"] = "SOURCE_SAME_ROLE_ROWS_AGGREGATED_AFTER_TABLE_CLOSURE"
    mapping["values"] = _sum_record_cells(
        [{"cells": deepcopy(mapping["values"])},
         {"cells": [family._source_money(row["values_exact"][n - 1]) for n in (4, 5)]}],
        exact_state="EXACT_SAME_ROLE_SOURCE_ROW_SUM",
    )
    _reseal_candidate(fixture[1])
    assert all(value["source_text"] is None and value["coefficient"] == 1 for value in mapping["values"])
    before = deepcopy(fixture[1:5])
    assert len(_conflicts(fixture)) == 1
    assert fixture[1:5] == before


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("value", [None, "-", "1", 0, False])
def test_changed_exact_raw_cell_requires_new_review_not_repair_or_numeric_equality(monkeypatch, case, value):
    fixture = _fixture(monkeypatch, case=case)
    observation = fixture[0]["observations"][0]
    column = observation["printed_dash_money_column_ordinals"][0]
    fixture[3][0]["page_json"]["sections"][0]["tables"][0]["rows"][-1]["values_exact"][column - 1] = value
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="before-image"):
        _conflicts(fixture)


@pytest.mark.parametrize("case", CASES)
def test_new_selected_version_cannot_borrow_the_old_printed_dash_review(monkeypatch, case):
    fixture = _fixture(monkeypatch, case=case)
    fixture[3][0]["page_json_version_id"] = "gfpstorev1:json:" + "c" * 64
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="selected JSON version"):
        _conflicts(fixture)


@pytest.mark.parametrize("field", ["original_page_json_sha256", "original_table_json_sha256", "source_table_rows_exact"])
def test_note_population_resealing_cannot_replace_actual_source_inventory(monkeypatch, field):
    fixture = _fixture(monkeypatch, case="note_comparative")
    population = fixture[2]["tax_population_inventory"][0]
    population[field] = [] if field == "source_table_rows_exact" else "0" * 64
    _reseal(population, "receipt_id", "gjitfav1:tax-population:")
    _reseal(fixture[2], "receipt_id", "gjitfav1:source-context:")
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error, match="population replay"):
        _conflicts(fixture)


@pytest.mark.parametrize("kind", ["nonzero_lane", "all_columns", "blank", "glyph", "source_size"])
def test_resealed_registry_cannot_expand_or_rewrite_the_reviewed_discrepancy(monkeypatch, kind):
    fixture = _fixture(monkeypatch, case="primary_current")
    registry, observation = fixture[0], fixture[0]["observations"][0]
    if kind == "nonzero_lane":
        observation["printed_dash_money_column_ordinals"] = [5]
    elif kind == "all_columns":
        observation["printed_dash_money_column_ordinals"] = [4, 5]
    elif kind == "blank":
        observation["before_reference"]["values_exact"][3] = None
    elif kind == "glyph":
        observation["review"]["printed_glyph_by_money_column"] = {"4": "0"}
    else:
        observation["source"]["source_size_bytes"] += 1
    _reseal_registry(registry)
    with pytest.raises(negative.IncomeTaxSourceLabelDiscrepancyV1Error):
        negative._validate_registry(registry)


@pytest.mark.parametrize("case", CASES)
def test_fresh_pdf_pixels_are_independently_authenticated_on_both_calls(monkeypatch, tmp_path, case):
    fixture = _fixture(monkeypatch, case=case)
    path = tmp_path / "synthetic-owned-source.pdf"
    path.write_bytes(SYNTHETIC_PDF)
    source = fixture[0]["observations"][0]["source"]
    calls = []

    def render(pdf_path, physical_page):
        calls.append((pdf_path, physical_page))
        return fixture[5]

    monkeypatch.setattr(negative, "_render_registered_page_v1", render)
    for _ in range(2):
        receipts = negative.authenticate_registered_negative_source_labels_v1(
            document_source=source, original_records=fixture[3], pdf_path=path,
        )
        assert len(receipts) == 1 and receipts[0]["source_values_changed"] is False
        assert receipts[0]["source_observation_receipt"]["classification"] == negative.PRINTED_DASH_CLASSIFICATION
    assert len(calls) == 2


@pytest.mark.parametrize("failure", ["wrong_pdf", "wrong_pixels", "pdf_changed_during_render"])
def test_printed_dash_pixel_protocol_fails_closed_on_input_or_callback_drift(monkeypatch, tmp_path, failure):
    fixture = _fixture(monkeypatch, case="note_comparative")
    path = tmp_path / "synthetic-owned-source.pdf"
    path.write_bytes(b"X" * len(SYNTHETIC_PDF) if failure == "wrong_pdf" else SYNTHETIC_PDF)
    source = fixture[0]["observations"][0]["source"]

    def render(_pdf_path, _physical_page):
        if failure == "pdf_changed_during_render":
            path.write_bytes(b"Y" * len(SYNTHETIC_PDF))
        return b"not reviewed pixels" if failure == "wrong_pixels" else fixture[5]

    monkeypatch.setattr(negative, "_render_registered_page_v1", render)
    with pytest.raises(negative.IncomeTaxSourceLabelDiscrepancyV1Error):
        negative.authenticate_registered_negative_source_labels_v1(
            document_source=source, original_records=fixture[3], pdf_path=path,
        )
