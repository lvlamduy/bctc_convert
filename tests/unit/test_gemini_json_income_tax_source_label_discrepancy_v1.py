"""Source-bound negative label controls; synthetic JSON is never a real PDF observation."""

from __future__ import annotations

import struct
import zlib
from copy import deepcopy
from hashlib import sha256

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled, _primary_page, _record

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation import gemini_json_income_tax_source_label_discrepancy_v1 as negative
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import READY, UNRESOLVED
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

REASON = "SOURCE_TRANSCRIPTION_DISCREPANCY"


def _reseal_candidate(candidate):
    material = {key: value for key, value in candidate.items() if key != "candidate_id"}
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)


def _reseal(value, key, prefix):
    material = {name: item for name, item in value.items() if name != key}
    value[key] = prefix + canonical_json_sha256_v1(material)


def _reseal_registry(registry):
    for observation in registry["observations"]:
        _reseal(observation, "observation_id", "gjitflabelv1:observation:")
    _reseal(registry, "registry_id", "gjitflabelv1:registry:")


@pytest.fixture
def registry(monkeypatch):
    """Keep the registered authority intact; replace only its documented loader seam."""
    value = deepcopy(negative.load_registered_negative_source_label_observations_v1())
    monkeypatch.setattr(
        negative, "load_registered_negative_source_label_observations_v1", lambda: deepcopy(value)
    )
    return value


def _fixture(registry, *, ordinal=1, values=("-", " -", " -", " -")):
    observation = registry["observations"][0]
    before, location = observation["before_reference"], observation["locator"]
    rows = [
        {
            "label_exact": f"Khoản mục tham chiếu {number}",
            "hierarchy_path_exact": [f"Khoản mục tham chiếu {number}"],
            "row_kind": "ITEM",
            "values_exact": [None, "1", "1", "1", "1"],
        }
        for number in range(1, 16)
    ]
    current_label = "Chi phí thuế thu nhập doanh nghiệp hiện hành"
    rows.append({
        "label_exact": current_label,
        "hierarchy_path_exact": [current_label],
        "row_kind": "ITEM",
        "values_exact": [None, "-", "-", "-", "-"],
    })
    rows.append({**deepcopy(before), "values_exact": [None, *values]})
    page = _primary_page(rows)
    section, table = page["sections"][0], page["sections"][0]["tables"][0]
    section["title_exact"] = (
        "Báo cáo kết quả hoạt động riêng\n"
        "cho giai đoạn từ ngày 01 tháng 01 năm 2025 đến ngày 31 tháng 3 năm 2025"
    )
    table["columns"] = [
        {"header_path_exact": ["Thuyết minh"], "value_kind": "TEXT"},
        {"header_path_exact": ["Quý I", "Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Quý I", "Năm 2024", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Lũy kế từ đầu năm", "Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["Lũy kế từ đầu năm", "Năm 2024", "Triệu đồng"], "value_kind": "MONEY"},
    ]
    record = _record(page)
    record.update(
        **observation["source"], document_ordinal=ordinal,
        page_json_version_id=location["page_json_version_id"],
        physical_page=location["physical_page"], selected_page_ordinal=location["physical_page"],
    )
    compiled = _adapter_compiled()
    context = family._source_context_receipt(
        compiled_specs=compiled, repair_receipts=[], root_controls=[], page_records=[record],
    )
    locator = {
        **{key: record[key] for key in (
            "document_id", "document_ordinal", "source_logical_name", "source_sha256",
            "page_json_version_id", "physical_page", "selected_page_ordinal",
        )},
        "section_id": location["section_id"], "table_id": location["table_id"],
    }

    def mapping(row_ordinal, role, rnid):
        row = rows[row_ordinal - 1]
        return {
            "role": role, "report_norm_id": rnid, "state": "SOURCE_OBSERVED_ROLE_ROW",
            "unit": "MILLION_VND",
            "values": [family._source_money(row["values_exact"][n - 1])
                       for n in location["money_column_ordinals"]],
            "source_refs": [{
                "locator": deepcopy(locator), "row_ordinal": row_ordinal,
                "row_id": f"r{row_ordinal}", "row_kind": row["row_kind"],
                "label_exact": row["label_exact"],
                "hierarchy_path_exact": deepcopy(row["hierarchy_path_exact"]),
                "money_column_ordinals": deepcopy(location["money_column_ordinals"]),
            }],
        }

    candidate = {
        "status": READY, "reasons": [], "closure_receipt": {},
        "mappings": [mapping(16, "CURRENT_TAX_PARENT", 5723),
                     mapping(location["row_ordinal"], observation["expected_role"], 5726)],
    }
    _reseal_candidate(candidate)
    return candidate, context, [record], compiled


def _conflicts(fixture):
    candidate, context, records, compiled = fixture
    return family._registered_negative_source_label_conflicts_v1(
        candidate, source_context=context, repaired_records=records, compiled_specs=compiled,
    )


@pytest.mark.parametrize("ordinal", [1, 110, 204])
def test_registered_source_label_is_bound_without_a_global_document_ordinal(registry, ordinal):
    fixture = _fixture(registry, ordinal=ordinal)
    before = deepcopy(fixture[:3])
    assert len(_conflicts(fixture)) == 1
    assert fixture[:3] == before


@pytest.mark.parametrize("values", [
    ("0", "0", "0", "0"), ("-", "-", "-", "-"),
    (None, None, None, None), ("9", "8", "7", "6"),
])
def test_values_cannot_grant_a_printed_role_or_disable_the_negative_observation(registry, values):
    fixture = _fixture(registry, values=values)
    before = deepcopy(fixture[:3])
    assert len(_conflicts(fixture)) == 1
    assert fixture[:3] == before


def test_ready_seal_withholds_all_mappings_and_reseals_source_discrepancy(registry):
    candidate, context, records, compiled = _fixture(registry)
    before = deepcopy(candidate)
    result = family._seal_income_tax_source_controls(
        candidate, source_context=context, repaired_records=records, compiled_specs=compiled,
    )
    assert result["status"] == UNRESOLVED
    assert result["mappings"] == []
    assert result["reasons"] == [REASON]
    evidence = result["closure_receipt"]["income_tax_unresolved_evidence_receipt"]
    material = {key: value for key, value in evidence.items() if key != "receipt_id"}
    assert evidence["receipt_id"] == "gjitfav1:unresolved:" + canonical_json_sha256_v1(material)
    material = {key: value for key, value in result.items() if key != "candidate_id"}
    assert result["candidate_id"] == "gjmthfcv1:candidate:" + canonical_json_sha256_v1(material)
    assert candidate == before


def test_hold_binds_runtime_source_hashes_and_never_claims_fresh_pdf_authentication(registry):
    fixture = _fixture(registry)
    proof = _conflicts(fixture)[0]
    observed = proof["source_observation"]
    page = fixture[2][0]["page_json"]
    table = page["sections"][0]["tables"][0]
    assert observed["original_page_json_sha256"] == canonical_json_sha256_v1(page)
    assert observed["original_table_json_sha256"] == canonical_json_sha256_v1(table)
    assert observed["original_source_row_exact"] == table["rows"][16]
    assert proof["candidate_id_before_hold"] == fixture[0]["candidate_id"]
    assert proof["source_context_receipt_id"] == fixture[1]["receipt_id"]
    assert proof["fresh_pdf_authentication_claimed"] is False
    assert observed["fresh_pdf_authentication_claimed"] is False
    assert proof["source_values_changed"] is False
    for value, prefix in ((proof, "gjitflabelv1:hold:"), (observed, "gjitflabelv1:source:")):
        material = {key: item for key, item in value.items() if key != "receipt_id"}
        assert value["receipt_id"] == prefix + canonical_json_sha256_v1(material)


def test_no_selected_deferred_role_does_not_borrow_the_negative_observation(registry):
    fixture = _fixture(registry)
    fixture[0]["mappings"] = fixture[0]["mappings"][:1]
    _reseal_candidate(fixture[0])
    assert _conflicts(fixture) == []


def test_nonready_seal_never_enters_the_new_negative_source_guard(registry, monkeypatch):
    candidate, _context, _records, compiled = _fixture(registry)
    candidate.update(status=UNRESOLVED, mappings=[], reasons=["EXISTING_HOLD"])

    def must_not_enter(*_args, **_kwargs):
        pytest.fail("A non-READY candidate entered the registered negative-source guard")

    monkeypatch.setattr(family, "_registered_negative_source_label_conflicts_v1", must_not_enter)
    result = family._seal_income_tax_source_controls(
        candidate, source_context={}, repaired_records=[], compiled_specs=compiled,
    )
    assert result == candidate
    assert result is not candidate


def test_a_different_pdf_cannot_borrow_the_registered_negative_observation(registry):
    candidate, _context, records, compiled = _fixture(registry)
    records[0].update(
        document_id="gfpstorev1:document:" + "b" * 64,
        source_logical_name="vietstock_bctc/OTHER/2025/fixture.pdf",
        source_sha256="a" * 64, page_json_version_id="gfpstorev1:json:" + "c" * 64,
    )
    context = family._source_context_receipt(
        compiled_specs=compiled, repair_receipts=[], root_controls=[], page_records=records,
    )
    for mapping in candidate["mappings"]:
        for ref in mapping["source_refs"]:
            for key in ("document_id", "source_logical_name", "source_sha256", "page_json_version_id"):
                ref["locator"][key] = records[0][key]
    _reseal_candidate(candidate)
    assert _conflicts((candidate, context, records, compiled)) == []
    assert "registered_source_label_discrepancy_observations" not in context


def test_same_pdf_new_selected_version_requires_a_new_reviewed_binding(registry):
    _candidate, _context, records, compiled = _fixture(registry)
    records[0]["page_json_version_id"] = "gfpstorev1:json:" + "e" * 64
    with pytest.raises(negative.IncomeTaxSourceLabelDiscrepancyV1Error, match="selected JSON version"):
        family._source_context_receipt(
            compiled_specs=compiled, repair_receipts=[], root_controls=[], page_records=records,
        )


@pytest.mark.parametrize("kind", ["candidate", "context", "row", "money_columns", "partial_locator"])
def test_runtime_binding_drift_raises_instead_of_waiving_the_hold(registry, kind):
    fixture = _fixture(registry)
    candidate, context, records, _compiled = fixture
    ref = candidate["mappings"][-1]["source_refs"][0]
    if kind == "candidate":
        candidate["mappings"][-1]["values"][0]["source_text"] = "changed"
    elif kind == "context":
        context["rule"] = "forged"
    elif kind == "row":
        records[0]["page_json"]["sections"][0]["tables"][0]["rows"][16]["row_kind"] = "TOTAL"
    elif kind == "money_columns":
        ref["money_column_ordinals"] = [2, 3]
        _reseal_candidate(candidate)
    else:
        ref["locator"]["page_json_version_id"] = "gfpstorev1:json:" + "e" * 64
        _reseal_candidate(candidate)
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        _conflicts(fixture)


@pytest.mark.parametrize("field", [
    "original_page_json_sha256", "original_section_json_sha256", "original_table_json_sha256",
])
def test_resealed_primary_inventory_cannot_replace_the_actual_source_hashes(registry, field):
    fixture = _fixture(registry)
    context = fixture[1]
    inventory = context["document_statement_period_inventory"]
    inventory["sources"][0][field] = "0" * 64
    _reseal(inventory, "receipt_id", "gjitfav1:document-statement-periods:")
    _reseal(context, "receipt_id", "gjitfav1:source-context:")
    with pytest.raises(family.GeminiJsonIncomeTaxFamilyV1Error):
        _conflicts(fixture)


@pytest.mark.parametrize("kind", ["not_primary", "not_income", "not_money"])
def test_registered_profile_requires_the_actual_primary_income_and_money_axis(registry, kind):
    _candidate, _context, records, _compiled = _fixture(registry)
    section = records[0]["page_json"]["sections"][0]
    if kind == "not_primary":
        section["content_kind"] = "FINANCIAL_NOTE"
    elif kind == "not_income":
        section["statement_type"] = "CASH_FLOW"
    else:
        section["tables"][0]["columns"][3]["value_kind"] = "TEXT"
    with pytest.raises(negative.IncomeTaxSourceLabelDiscrepancyV1Error):
        negative.registered_negative_source_label_observation_axis_v1(records)


@pytest.mark.parametrize("field", ["printed_counterpart_for_claimed_role", "source_values_changed", "text_layer_claimed"])
def test_resealing_cannot_turn_the_negative_review_into_positive_or_repaired_authority(registry, field):
    registry["observations"][0]["review"][field] = True
    _reseal_registry(registry)
    with pytest.raises(negative.IncomeTaxSourceLabelDiscrepancyV1Error):
        negative._validate_registry(registry)


def test_changed_registry_file_is_rejected_by_the_fixed_production_hash(tmp_path, monkeypatch):
    raw = negative.REGISTRY_PATH.read_bytes()
    changed = tmp_path / "changed-registry.json"
    changed.write_bytes(raw + b" ")
    monkeypatch.setattr(negative, "REGISTRY_PATH", changed)
    with pytest.raises(negative.IncomeTaxSourceLabelDiscrepancyV1Error, match="approval bytes"):
        negative.load_registered_negative_source_label_observations_v1()


def _one_pixel_rgb_png():
    def chunk(kind, payload):
        material = kind + payload
        return struct.pack(">I", len(payload)) + material + struct.pack(">I", zlib.crc32(material))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff")) + chunk(b"IEND", b""))


def _pixel_protocol_fixture(registry, tmp_path):
    """Owned synthetic bytes only; the renderer seam never opens a real PDF."""
    pdf_bytes, png_bytes = b"%PDF-synthetic-unit-fixture\n", _one_pixel_rgb_png()
    observation = registry["observations"][0]
    observation["source"]["source_sha256"] = sha256(pdf_bytes).hexdigest()
    source_identity = {
        "source_logical_name": observation["source"]["source_logical_name"],
        "source_sha256": observation["source"]["source_sha256"],
        "source_size_bytes": len(pdf_bytes),
    }
    observation["source"]["document_id"] = (
        "gfpstorev1:document:" + canonical_json_sha256_v1(source_identity)
    )
    observation["review"]["page_render"].update(
        sha256=sha256(png_bytes).hexdigest(), size_bytes=len(png_bytes),
        width_pixels=1, height_pixels=1,
    )
    _reseal_registry(registry)
    fixture = _fixture(registry)
    path = tmp_path / "synthetic-source.pdf"
    path.write_bytes(pdf_bytes)
    source = {**observation["source"], "source_size_bytes": len(pdf_bytes)}
    return path, source, fixture[2], png_bytes


def test_fresh_pixel_authentication_repeats_the_real_byte_guards_on_each_call(registry, tmp_path, monkeypatch):
    path, source, records, png = _pixel_protocol_fixture(registry, tmp_path)
    calls = []

    def render(pdf_path, physical_page):
        calls.append((pdf_path, physical_page))
        return png

    monkeypatch.setattr(negative, "_render_registered_page_v1", render)
    for _ in range(2):
        receipts = negative.authenticate_registered_negative_source_labels_v1(
            document_source=source, original_records=records, pdf_path=path,
        )
        assert len(receipts) == 1
        receipt = receipts[0]
        material = {key: value for key, value in receipt.items() if key != "receipt_id"}
        assert receipt["receipt_id"] == "gjitflabelv1:pdf-auth:" + canonical_json_sha256_v1(material)
        assert receipt["source_values_changed"] is False
        assert receipt["text_layer_claimed"] is False
    assert calls == [(path, 6), (path, 6)]


@pytest.mark.parametrize("failure", ["changed_pdf", "wrong_pixels", "pdf_changed_during_render"])
def test_pixel_protocol_rejects_wrong_bytes_and_post_callback_mutation(registry, tmp_path, monkeypatch, failure):
    path, source, records, png = _pixel_protocol_fixture(registry, tmp_path)
    if failure == "changed_pdf":
        path.write_bytes(b"X" * source["source_size_bytes"])

    def render(_pdf_path, _physical_page):
        if failure == "pdf_changed_during_render":
            path.write_bytes(b"Y" * source["source_size_bytes"])
        return b"not the reviewed pixels" if failure == "wrong_pixels" else png

    monkeypatch.setattr(negative, "_render_registered_page_v1", render)
    with pytest.raises(negative.IncomeTaxSourceLabelDiscrepancyV1Error):
        negative.authenticate_registered_negative_source_labels_v1(
            document_source=source, original_records=records, pdf_path=path,
        )
