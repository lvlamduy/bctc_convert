from __future__ import annotations

import calendar
import json
import unicodedata
from copy import deepcopy
from hashlib import sha256

import pytest

from bctc_ai.evaluation.gemini_json_income_tax_part_period_context_v1 import (
    BASE_GIT_COMMIT,
    FAMILY_ID,
    PART_PERIOD_HEADING_EXACT,
    REGISTRY_FORMAT_VERSION,
    GeminiJsonIncomeTaxPartPeriodContextV1Error,
    parse_part_scoped_period_lexical_v1,
    replay_registered_part_period_contexts_v1,
    validate_registered_part_period_registry_v1,
)

HEADING = PART_PERIOD_HEADING_EXACT
CLAUSE = (
    "Các thông tin trình bày trong phần này: "
    "Kỳ này bắt đầu từ 01/01/2026 đến 30/06/2026; "
    "Kỳ trước bắt đầu từ 01/01/2023 đến 30/06/2023"
)
ERROR = GeminiJsonIncomeTaxPartPeriodContextV1Error


def _sha(value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return sha256(raw).hexdigest()


def _ref(path):
    return {"path": path, "sha256": "a" * 64, "size_bytes": 1}


def _fixture(*, combined=False, heading_kind="NARRATIVE", column_kind="MONEY"):
    """Synthetic JSON bindings, deliberately NOT PDF/registry authentication."""
    prefix = {
        "status": "FINANCIAL_NOTE_CONTENT",
        "sections": [{"content_kind": "FINANCIAL_NARRATIVE", "statement_type": "NOT_APPLICABLE",
                      "title_exact": None, "narratives_exact": [HEADING, CLAUSE], "tables": []}],
    }
    target = {
        "status": "FINANCIAL_NOTE_CONTENT",
        "sections": [{"content_kind": "FINANCIAL_NOTE", "statement_type": "NOT_APPLICABLE",
                      "title_exact": "Chi phí thuế thu nhập doanh nghiệp", "narratives_exact": [],
                      "tables": [{"title_exact": None, "unit_exact": None, "continuation": "NONE",
                                  "columns": [{"header_path_exact": ["Kỳ này"], "value_kind": column_kind},
                                              {"header_path_exact": ["Kỳ trước"], "value_kind": column_kind}],
                                  "rows": [{"label_exact": "Chi phí thuế TNDN hiện hành", "row_kind": "ITEM",
                                            "hierarchy_path_exact": ["Chi phí thuế TNDN hiện hành"],
                                            "values_exact": [None, "-"]}]}]}],
    }
    if combined:
        prefix["sections"][0]["narratives_exact"] = [HEADING + "\n" + CLAUSE]
    if heading_kind == "SECTION_TITLE":
        prefix["sections"][0]["title_exact"] = HEADING
        prefix["sections"][0]["narratives_exact"] = [CLAUSE]
    elif heading_kind == "TABLE_TITLE":
        prefix["sections"][0]["tables"] = [{"title_exact": HEADING + "\n25. Thu nhập lãi thuần",
                                           "columns": [], "rows": [], "unit_exact": None, "continuation": "NONE"}]
        prefix["sections"][0]["narratives_exact"] = [CLAUSE]
    records = []
    for index, page in enumerate((prefix, target), 1):
        records.append({"document_id": "gfpstorev1:document:" + "d" * 64, "document_ordinal": 7,
                        "source_logical_name": "reports/2026/source.pdf", "source_sha256": "b" * 64,
                        "page_json_version_id": "gfpstorev1:json:" + str(index) * 64,
                        "physical_page": index + 3, "selected_page_ordinal": index,
                        "page_json": page})
    section = prefix["sections"][0]

    def occurrence(kind, raw, fragment, narrative_ordinal=None, table_id=None):
        start = raw.index(fragment)
        return {"page_json_version_id": records[0]["page_json_version_id"], "physical_page": 4,
                "carrier_kind": kind, "section_id": "s1", "table_id": table_id,
                "narrative_ordinal": narrative_ordinal, "source_exact": raw,
                "source_sha256": sha256(raw.encode("utf-8")).hexdigest(),
                "span_start": start, "span_end": start + len(fragment), "substring_exact": fragment,
                "original_section_json_sha256": _sha(section), "evaluation_section_json_sha256": _sha(section)}

    if heading_kind == "SECTION_TITLE":
        headings = [occurrence(heading_kind, HEADING, HEADING)]
    elif heading_kind == "TABLE_TITLE":
        headings = [occurrence(heading_kind, section["tables"][0]["title_exact"], HEADING, table_id="t1")]
    else:
        headings = [occurrence("NARRATIVE", section["narratives_exact"][0], HEADING, 1)]
    clause_ordinal = 1 if combined or heading_kind != "NARRATIVE" else 2
    clauses = [occurrence("NARRATIVE", section["narratives_exact"][clause_ordinal - 1], CLAUSE, clause_ordinal)]
    target_section = target["sections"][0]
    table = target_section["tables"][0]
    context = {
        "context_id": "synthetic-part-context", "pdf_source": {"logical_name": records[0]["source_logical_name"],
                                                                "sha256": "b" * 64, "size_bytes": 123},
        "document_id": records[0]["document_id"], "provenance_document_ordinal": 54,
        "span_pages": [{"physical_page": record["physical_page"], "selected_page_ordinal": record["selected_page_ordinal"],
                        "page_json_version_id": record["page_json_version_id"],
                        "original_page_json_sha256": _sha(record["page_json"]),
                        "evaluation_page_json_sha256": _sha(record["page_json"])} for record in records],
        "heading_occurrences": headings, "period_occurrences": clauses,
        "target_tables": [{"page_json_version_id": records[1]["page_json_version_id"], "physical_page": 5,
                           "selected_page_ordinal": 2, "section_id": "s1", "table_id": "t1",
                           "original_section_json_sha256": _sha(target_section), "evaluation_section_json_sha256": _sha(target_section),
                           "original_table_json_sha256": _sha(table), "evaluation_table_json_sha256": _sha(table),
                           "money_column_ordinals": [1, 2], "header_paths_exact": [["Kỳ này"], ["Kỳ trước"]],
                           "column_value_kinds": [column_kind, column_kind], "period_order": ["CURRENT", "COMPARATIVE"]}],
        "review_evidence": {"manual_review_ref": _ref("/external/review.json"),
                            "visual_refs": [{"png_ref": _ref("/external/prefix.png"),
                                             "render_receipt_ref": _ref("/external/render.json"),
                                             "physical_page": 4, "renderer_version": "synthetic-unverified-renderer",
                                             "dpi": 300, "width_pixels": 100, "height_pixels": 200}],
                            "no_reset_observation_exact": "Synthetic reviewed bounded prefix-to-target span; not actual PDF authority."},
    }
    return records, {"format_version": REGISTRY_FORMAT_VERSION, "family_id": FAMILY_ID,
                     "base_git_commit": BASE_GIT_COMMIT, "contexts": [context]}


def _rehash_original(records, registry):
    """For adversarial registration tests; this does not make it approved."""
    context = registry["contexts"][0]
    by_vid = {record["page_json_version_id"]: record for record in records}
    for page in context["span_pages"]:
        digest = _sha(by_vid[page["page_json_version_id"]]["page_json"])
        page["original_page_json_sha256"] = page["evaluation_page_json_sha256"] = digest
    for item in [*context["heading_occurrences"], *context["period_occurrences"], *context["target_tables"]]:
        section = by_vid[item["page_json_version_id"]]["page_json"]["sections"][int(item["section_id"][1:]) - 1]
        item["original_section_json_sha256"] = item["evaluation_section_json_sha256"] = _sha(section)
        if "money_column_ordinals" in item:
            table = section["tables"][int(item["table_id"][1:]) - 1]
            item["original_table_json_sha256"] = item["evaluation_table_json_sha256"] = _sha(table)


@pytest.mark.parametrize("months", [3, 6, 9, 12])
def test_lexical_explicit_calendar_pair_no_comparative_offset(months):
    day = calendar.monthrange(2026, months)[1]
    raw = CLAUSE.replace("30/06/", f"{day:02}/{months:02}/")
    proof = parse_part_scoped_period_lexical_v1(heading_exact=HEADING, clause_exact=raw)
    assert proof["status"] == "PASS"
    assert proof["calendar_only_semantics"]["comparative"]["printed_year"] == 2023
    assert proof["calendar_only_semantics"]["comparative_year_inferred"] is False
    assert all(value is False for value in proof["permission_grants"].values())
    assert "UNPROVEN" in proof["owner_span_status"]


@pytest.mark.parametrize("layout", ["upper", "nfd", "literal_newline", "nbsp", "narrow_space", "paragraph", "tab", "crlf", "unpadded", "full_stop"])
def test_lexical_layout_retains_every_raw_character_and_sha(layout):
    heading, clause = HEADING, CLAUSE
    if layout == "upper":
        heading, clause = heading.upper(), clause.upper()
    elif layout == "nfd":
        heading, clause = unicodedata.normalize("NFD", heading), unicodedata.normalize("NFD", clause)
    elif layout == "unpadded":
        clause = clause.replace("01/01/", "1/1/").replace("30/06/", "30/6/")
    elif layout == "full_stop":
        clause += "."
    else:
        space = {"literal_newline": "\\n", "nbsp": "\u00a0", "narrow_space": "\u202f",
                 "paragraph": "\u2029", "tab": "\t", "crlf": "\r\n"}[layout]
        # Whitespace may not split digits or date tokens.
        heading, clause = heading.replace(" ", space), clause.replace(" ", space)
    proof = parse_part_scoped_period_lexical_v1(heading_exact=heading, clause_exact=clause)
    assert proof["status"] == "PASS"
    assert proof["raw_sources_exact"] == {"heading_exact": heading, "clause_exact": clause}
    for key, value in proof["raw_sources_exact"].items():
        assert proof["raw_source_sha256"][key] == sha256(value.encode("utf-8")).hexdigest()
        assert "".join(proof["raw_source_lines_exact"][key]) == value


@pytest.mark.parametrize("bad", [
    "31/02/2026", "30/13/2026", "00/06/2026", "30/06/0000", "29/06/2026", "31/05/2026",
    "30/06/2027", "30/06/２０２６", "30/06/٢٠٢٦", "30/06/2026\u0301", "30/06/2026¹",
    "30/06/20 26", "30/06/20\u00a026", "30／06／2026", "30/06/2026 (*)",
])
def test_lexical_invalid_or_annotated_date_does_not_gain_calendar_authority(bad):
    proof = parse_part_scoped_period_lexical_v1(heading_exact=HEADING, clause_exact=CLAUSE.replace("30/06/2026", bad))
    assert proof["status"] == "ALGORITHM_HOLD"
    assert proof["calendar_only_semantics"] is None


@pytest.mark.parametrize("character", ["\v", "\f", "\u0085", "\0", "\x7f", "\u200b", "\u2060", "\ufeff"])
@pytest.mark.parametrize("surface", ["heading", "clause"])
def test_lexical_raw_controls_cannot_disappear_before_layout(character, surface):
    heading = HEADING.replace(" ", character, 1) if surface == "heading" else HEADING
    clause = CLAUSE.replace(" ", character, 1) if surface == "clause" else CLAUSE
    assert parse_part_scoped_period_lexical_v1(heading_exact=heading, clause_exact=clause)["status"] == "ALGORITHM_HOLD"


@pytest.mark.parametrize("mutation", ["current_start", "prior_start", "same_prior_year", "future_prior_year", "unequal_duration",
                                    "missing_prior", "duplicate_clause", "extra_prose", "negation", "method", "unknown_escape", "wrong_heading"])
def test_lexical_whole_assertion_not_a_substring_match(mutation):
    heading, clause = HEADING, CLAUSE
    if mutation == "current_start":
        clause = clause.replace("01/01/2026", "02/01/2026")
    elif mutation == "prior_start":
        clause = clause.replace("01/01/2023", "01/04/2023")
    elif mutation == "same_prior_year":
        clause = clause.replace("2023", "2026")
    elif mutation == "future_prior_year":
        clause = clause.replace("2023", "2027")
    elif mutation == "unequal_duration":
        clause = clause.replace("30/06/2023", "31/03/2023")
    elif mutation == "missing_prior":
        clause = clause.split("; ")[0]
    elif mutation == "duplicate_clause":
        clause += "\n" + clause
    elif mutation == "extra_prose":
        clause += " Các thông tin khác năm 2024."
    elif mutation == "negation":
        clause = "Không: " + clause
    elif mutation == "method":
        clause += " (Phương pháp trực tiếp)"
    elif mutation == "unknown_escape":
        clause = clause.replace(" Kỳ trước", "\\NKỳ trước")
    else:
        heading = "Thông tin bổ sung cho Báo cáo lưu chuyển tiền tệ"
    proof = parse_part_scoped_period_lexical_v1(heading_exact=heading, clause_exact=clause)
    assert proof["status"] == "ALGORITHM_HOLD"
    assert proof["calendar_only_semantics"] is None


@pytest.mark.parametrize("bad", [None, True, 2026, [], {}, "\ud800"])
def test_lexical_rejects_nonstring_or_surrogate_with_family_error(bad):
    with pytest.raises(ERROR):
        parse_part_scoped_period_lexical_v1(heading_exact=bad, clause_exact=CLAUSE)


def test_irrelevant_lexical_strings_return_explicit_not_applicable():
    proof = parse_part_scoped_period_lexical_v1(heading_exact="Giới thiệu", clause_exact="Ngân hàng được thành lập.")
    assert proof["status"] == "NOT_APPLICABLE"
    assert proof["calendar_only_semantics"] is None


@pytest.mark.parametrize("surface", ["long_s", "kelvin"])
def test_unicode_casefold_cannot_erase_unknown_source_glyphs(surface):
    heading = HEADING.replace("sung", "ſung") if surface == "long_s" else HEADING
    clause = CLAUSE.replace("Kỳ", "Kỳ") if surface == "kelvin" else CLAUSE
    proof = parse_part_scoped_period_lexical_v1(heading_exact=heading, clause_exact=clause)
    assert proof["status"] == "ALGORITHM_HOLD"
    assert "UNSUPPORTED_RAW_LEXICAL_CHARACTER" in proof["reasons"]


@pytest.mark.parametrize("combined,heading_kind,column_kind", [
    (False, "NARRATIVE", "MONEY"), (True, "NARRATIVE", "MONEY"),
    (False, "SECTION_TITLE", "MONEY"), (False, "TABLE_TITLE", "MONEY"),
    (False, "NARRATIVE", "UNKNOWN"),
])
def test_registered_binding_replays_full_span_and_exact_metadata_without_authentication_claim(combined, heading_kind, column_kind):
    records, registry = _fixture(combined=combined, heading_kind=heading_kind, column_kind=column_kind)
    before = deepcopy((records, registry))
    assert validate_registered_part_period_registry_v1(registry) == registry
    receipts = replay_registered_part_period_contexts_v1(records, registry=registry)
    assert len(receipts) == 1
    receipt = receipts[0]
    assert receipt["complete"] is True
    assert receipt["status"] == "PASS_REGISTERED_SOURCE_BINDINGS_NOT_PDF_AUTHENTICATION"
    assert receipt["target_locator"]["document_ordinal"] == 7
    assert receipt["registered_context_exact"]["provenance_document_ordinal"] == 54
    assert receipt["raw_column_ordinals"] == [1, 2]
    assert receipt["column_value_kinds"] == [column_kind, column_kind]
    assert receipt["unknown_columns_promoted"] is False
    assert receipt["resolved_source_duration_semantics"] == [["SOURCE_YTD_QUARTER", 2026, 2], ["SOURCE_YTD_QUARTER", 2023, 2]]
    assert receipt["source_stage"] == "ORIGINAL_AND_EVALUATION_IDENTICAL"
    assert receipt["registry_json_authenticated"] is False and receipt["pdf_evidence_authenticated"] is False
    assert all(permission is False for permission in receipt["permission_grants"].values())
    assert (records, registry) == before


def test_registry_and_replay_returned_objects_do_not_poison_next_call():
    records, registry = _fixture()
    pristine = deepcopy(registry)
    checked = validate_registered_part_period_registry_v1(registry)
    checked["contexts"][0]["pdf_source"]["sha256"] = "f" * 64
    first = replay_registered_part_period_contexts_v1(records, registry=registry)
    expected = deepcopy(first)
    first[0]["registered_context_exact"]["target_tables"].clear()
    first[0]["permission_grants"]["acceptance"] = True
    assert registry == pristine
    assert replay_registered_part_period_contexts_v1(records, registry=registry) == expected


@pytest.mark.parametrize("mutation", [
    "format", "family", "base", "extra_top", "duplicate_context", "duplicate_target", "overlap_context",
    "bool_provenance", "bool_physical", "bool_selected", "bool_bytes", "bool_offset", "bool_column", "bad_sha",
    "span_gap", "duplicate_vid", "reverse_span", "absent_target_page", "wrong_target_selected", "bad_section",
    "wrong_carrier_kind", "bad_carrier_sha", "bad_slice", "overlap_occurrences", "extra_carrier_prose",
    "wrong_period_order", "wrong_column_kind", "bad_kind_type", "missing_visual", "wrong_visual_page",
    "empty_review", "duplicate_visual", "float_metadata", "extra_context", "bad_pdf_path",
])
def test_registry_malformed_or_ambiguous_axes_fail_closed(mutation):
    _records, registry = _fixture()
    c = registry["contexts"][0]
    t = c["target_tables"][0]
    h = c["heading_occurrences"][0]
    if mutation in {"format", "family", "base"}:
        registry[{"format": "format_version", "family": "family_id", "base": "base_git_commit"}[mutation]] = "wrong"
    elif mutation == "extra_top":
        registry["authenticated"] = True
    elif mutation in {"duplicate_context", "overlap_context"}:
        other = deepcopy(c)
        if mutation == "overlap_context":
            other["context_id"] = "other"
        registry["contexts"].append(other)
    elif mutation == "duplicate_target":
        c["target_tables"].append(deepcopy(t))
    elif mutation == "bool_provenance":
        c["provenance_document_ordinal"] = True
    elif mutation == "bool_physical":
        c["span_pages"][0]["physical_page"] = True
    elif mutation == "bool_selected":
        c["span_pages"][0]["selected_page_ordinal"] = True
    elif mutation == "bool_bytes":
        c["pdf_source"]["size_bytes"] = True
    elif mutation == "bool_offset":
        h["span_start"] = False
    elif mutation == "bool_column":
        t["money_column_ordinals"][0] = True
    elif mutation == "bad_sha":
        c["span_pages"][0]["original_page_json_sha256"] = "a" * 63
    elif mutation == "span_gap":
        c["span_pages"][1]["physical_page"] += 1
    elif mutation == "duplicate_vid":
        c["span_pages"][1]["page_json_version_id"] = c["span_pages"][0]["page_json_version_id"]
    elif mutation == "reverse_span":
        c["span_pages"].reverse()
    elif mutation == "absent_target_page":
        t["page_json_version_id"] = "gfpstorev1:json:" + "f" * 64
    elif mutation == "wrong_target_selected":
        t["selected_page_ordinal"] = 1
    elif mutation == "bad_section":
        t["section_id"] = "s0"
    elif mutation == "wrong_carrier_kind":
        h["carrier_kind"] = "ROW_LABEL"
    elif mutation == "bad_carrier_sha":
        h["source_sha256"] = "f" * 64
    elif mutation == "bad_slice":
        h["span_end"] -= 1
    elif mutation == "overlap_occurrences":
        c["heading_occurrences"].append(deepcopy(h))
    elif mutation == "extra_carrier_prose":
        h["source_exact"] += "\nKỳ vô định 2026"
        h["source_sha256"] = sha256(h["source_exact"].encode("utf-8")).hexdigest()
    elif mutation == "wrong_period_order":
        t["period_order"].reverse()
    elif mutation == "wrong_column_kind":
        t["column_value_kinds"][0] = "TEXT"
    elif mutation == "bad_kind_type":
        t["column_value_kinds"][0] = []
    elif mutation == "missing_visual":
        c["review_evidence"]["visual_refs"] = []
    elif mutation == "wrong_visual_page":
        c["review_evidence"]["visual_refs"][0]["physical_page"] = 5
    elif mutation == "empty_review":
        c["review_evidence"]["no_reset_observation_exact"] = ""
    elif mutation == "duplicate_visual":
        c["review_evidence"]["visual_refs"].append(deepcopy(c["review_evidence"]["visual_refs"][0]))
    elif mutation == "float_metadata":
        c["pdf_source"]["size_bytes"] = 123.0
    elif mutation == "extra_context":
        c["owner_approved"] = True
    else:
        c["pdf_source"]["logical_name"] = "reports/../secret.pdf"
    with pytest.raises(ERROR):
        validate_registered_part_period_registry_v1(registry)


@pytest.mark.parametrize("mutation", ["source_sha", "logical_name", "document_id", "ordinal_bool", "physical", "selected", "vid",
                                    "late_cell", "late_unit", "late_header", "late_kind", "late_caption", "early_clause",
                                    "omit_page", "duplicate_page", "target_width", "target_owner", "target_primary"])
def test_fresh_source_drift_fails_without_trusting_self_sealed_receipt(mutation):
    records, registry = _fixture()
    if mutation in {"source_sha", "logical_name", "document_id"}:
        key = {"source_sha": "source_sha256", "logical_name": "source_logical_name", "document_id": "document_id"}[mutation]
        for record in records:
            record[key] = "reports/other.pdf" if mutation == "logical_name" else ("gfpstorev1:document:" if mutation == "document_id" else "") + "f" * 64
    elif mutation == "ordinal_bool":
        records[0]["document_ordinal"] = True
    elif mutation in {"physical", "selected", "vid"}:
        key = {"physical": "physical_page", "selected": "selected_page_ordinal", "vid": "page_json_version_id"}[mutation]
        records[-1][key] = "gfpstorev1:json:" + "f" * 64 if mutation == "vid" else 9
    elif mutation == "omit_page":
        records.pop(0)
    elif mutation == "duplicate_page":
        records.append(deepcopy(records[-1]))
    elif mutation == "early_clause":
        records[0]["page_json"]["sections"][0]["narratives_exact"][1] = CLAUSE.replace("2023", "2025")
    else:
        section = records[-1]["page_json"]["sections"][0]
        table = section["tables"][0]
        if mutation == "late_cell":
            table["rows"][0]["values_exact"][0] = "0"
        elif mutation == "late_unit":
            table["unit_exact"] = "Triệu đồng"
        elif mutation == "late_header":
            table["columns"][0]["header_path_exact"] = ["Kỳ trước"]
        elif mutation == "late_kind":
            table["columns"][0]["value_kind"] = "UNKNOWN"
        elif mutation == "late_caption":
            section["title_exact"] += " năm 2025"
        elif mutation == "target_width":
            table["rows"][0]["values_exact"].pop()
        elif mutation == "target_owner":
            section["content_kind"] = "FINANCIAL_NARRATIVE"
        else:
            records[-1]["page_json"]["status"] = "PRIMARY_FINANCIAL_STATEMENT"
            section.update(content_kind="PRIMARY_STATEMENT", statement_type="INCOME_STATEMENT")
    with pytest.raises(ERROR):
        replay_registered_part_period_contexts_v1(records, registry=registry)


@pytest.mark.parametrize("surface", ["narrative", "section", "table", "item_label", "ancestor"])
def test_self_rehashed_unregistered_reset_still_cannot_inherit(surface):
    records, registry = _fixture()
    section = records[1]["page_json"]["sections"][0]
    table = section["tables"][0]
    reset = "Thông tin bổ sung cho các khoản mục trình bày trong Báo cáo lưu chuyển tiền tệ"
    if surface == "narrative":
        section["narratives_exact"].append(reset)
    elif surface == "section":
        section["title_exact"] = reset
    elif surface == "table":
        table["title_exact"] = reset
    elif surface == "item_label":
        table["rows"][0]["label_exact"] = reset
    else:
        table["rows"][0]["hierarchy_path_exact"].insert(0, reset)
    _rehash_original(records, registry)
    with pytest.raises(ERROR, match="reset"):
        replay_registered_part_period_contexts_v1(records, registry=registry)


def test_original_and_evaluation_hash_domains_are_explicit_not_interchangeable():
    original, registry = _fixture()
    evaluation = deepcopy(original)
    section = evaluation[-1]["page_json"]["sections"][0]
    section["tables"][0]["rows"][0]["values_exact"][0] = "-"
    c = registry["contexts"][0]
    c["span_pages"][-1]["evaluation_page_json_sha256"] = _sha(evaluation[-1]["page_json"])
    c["target_tables"][0]["evaluation_section_json_sha256"] = _sha(section)
    c["target_tables"][0]["evaluation_table_json_sha256"] = _sha(section["tables"][0])
    assert replay_registered_part_period_contexts_v1(original, registry=registry)[0]["source_stage"] == "ORIGINAL"
    receipt = replay_registered_part_period_contexts_v1(evaluation, registry=registry)[0]
    assert receipt["source_stage"] == "EVALUATION"
    assert receipt["source_values_modified"] is False  # Replay itself changes nothing.
    assert receipt["pdf_evidence_authenticated"] is False
    assert original[-1]["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] is None


def test_mixed_original_and_evaluation_pages_cannot_form_a_part_receipt():
    original, registry = _fixture()
    evaluation = deepcopy(original)
    evaluation[0]["page_json"]["sections"][0]["narratives_exact"].append("Thông tin lịch sử không cấp quyền kỳ.")
    evaluation[1]["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "-"
    context = registry["contexts"][0]
    for page, record in zip(context["span_pages"], evaluation, strict=True):
        page["evaluation_page_json_sha256"] = _sha(record["page_json"])
    for occurrence in [*context["heading_occurrences"], *context["period_occurrences"]]:
        occurrence["evaluation_section_json_sha256"] = _sha(evaluation[0]["page_json"]["sections"][0])
    target = context["target_tables"][0]
    section = evaluation[1]["page_json"]["sections"][0]
    target["evaluation_section_json_sha256"] = _sha(section)
    target["evaluation_table_json_sha256"] = _sha(section["tables"][0])
    mixed = [evaluation[0], original[1]]
    with pytest.raises(ERROR, match="Mixed original/evaluation"):
        replay_registered_part_period_contexts_v1(mixed, registry=registry)


def test_same_logical_pdf_cannot_be_registered_under_a_second_document_identity():
    _records, registry = _fixture()
    other = deepcopy(registry["contexts"][0])
    other["context_id"] = "second-source-alias"
    other["document_id"] = "gfpstorev1:document:" + "e" * 64
    registry["contexts"].append(other)
    with pytest.raises(ERROR, match="identity aliases"):
        validate_registered_part_period_registry_v1(registry)


def test_unrelated_source_has_no_registered_context_or_approval():
    records, registry = _fixture()
    for record in records:
        record.update(document_id="gfpstorev1:document:" + "e" * 64, source_sha256="f" * 64,
                      source_logical_name="reports/2026/unregistered.pdf")
    assert replay_registered_part_period_contexts_v1(records, registry=registry) == []
