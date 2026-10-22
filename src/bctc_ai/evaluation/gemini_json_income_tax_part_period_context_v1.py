"""Pure F39 printed part-period syntax and registered source-binding replay.

Nothing in this module opens a file, authenticates caller-supplied registry
JSON, verifies a PDF, changes source JSON, or grants family acceptance. The
production wrapper must independently pin the registry and authenticate its
PDF evidence. Replay results are provisional source bindings, not that wrapper.
"""

from __future__ import annotations

import calendar
import json
import re
import unicodedata
from datetime import date
from hashlib import sha256
from typing import Any

REGISTRY_FORMAT_VERSION = "INCOME_TAX_REGISTERED_PART_PERIOD_CONTEXTS_V1"
FAMILY_ID = "INCOME_TAX"
BASE_GIT_COMMIT = "8efd618b6c77f0cdbb402a440e7ba3b3549184f1"
PART_PERIOD_HEADING_EXACT = (
    "Thông tin bổ sung cho các khoản mục trình bày trong "
    "Báo cáo kết quả hoạt động kinh doanh"
)
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_VID = re.compile(r"gfpstorev1:json:[0-9a-f]{64}\Z")
_DOC = re.compile(r"gfpstorev1:document:[0-9a-f]{64}\Z")
_DATE = r"[0-9]{1,2}/[0-9]{1,2}/[0-9]{4}"
_CLAUSE = re.compile(
    r"các thông tin trình bày trong phần này: "
    r"kỳ này bắt đầu từ (?P<current_start>" + _DATE + r") "
    r"đến (?P<current_end>" + _DATE + r"); "
    r"kỳ trước bắt đầu từ (?P<comparative_start>" + _DATE + r") "
    r"đến (?P<comparative_end>" + _DATE + r")\.?"
)
_MOTIF = re.compile(r"kỳ này|kỳ trước|bắt đầu từ|trong phần này|thông tin bổ sung|khoản mục trình bày")
_RESET = re.compile(
    r"(?:[ivxlcdm0-9]+[.)]?\s+)?(?:thông tin bổ sung cho các khoản mục|"
    r"các thông tin trình bày trong phần này|kỳ (?:này|trước) bắt đầu từ|"
    r"bảng cân đối kế toán|báo cáo tình hình tài chính|báo cáo lưu chuyển tiền tệ|"
    r"phần (?:[ivxlcdm]+|[0-9]+)\b)"
)
_PERMISSIONS = {
    "statement": False, "report_scope": False, "entity": False, "unit": False,
    "source_value": False, "production_year_scope": False, "acceptance": False,
}
_PAGE_KEYS = {
    "physical_page", "selected_page_ordinal", "page_json_version_id",
    "original_page_json_sha256", "evaluation_page_json_sha256",
}
_OCC_KEYS = {
    "page_json_version_id", "physical_page", "carrier_kind", "section_id", "table_id",
    "narrative_ordinal", "source_exact", "source_sha256", "span_start", "span_end",
    "substring_exact", "original_section_json_sha256", "evaluation_section_json_sha256",
}
_TARGET_KEYS = {
    "page_json_version_id", "physical_page", "selected_page_ordinal", "section_id", "table_id",
    "original_section_json_sha256", "evaluation_section_json_sha256",
    "original_table_json_sha256", "evaluation_table_json_sha256", "money_column_ordinals",
    "header_paths_exact", "column_value_kinds", "period_order",
}


class GeminiJsonIncomeTaxPartPeriodContextV1Error(ValueError):
    """A malformed registration or changed source must fail closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GeminiJsonIncomeTaxPartPeriodContextV1Error(message)


def _canonical(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                           allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as error:
        raise GeminiJsonIncomeTaxPartPeriodContextV1Error("Noncanonical JSON source") from error


def _plain_json(value: Any) -> None:
    _require(type(value) in {dict, list, str, int, bool, type(None)}, "Only plain typed JSON is supported")
    if type(value) is str:
        _require(not any(unicodedata.category(char) == "Cs" for char in value), "Raw source contains surrogate")
    elif type(value) is list:
        for item in value:
            _plain_json(item)
    elif type(value) is dict:
        for key, item in value.items():
            _require(type(key) is str, "JSON keys must be plain strings")
            _plain_json(key)
            _plain_json(item)


def _clone(value: Any) -> Any:
    _plain_json(value)
    return json.loads(_canonical(value))


def _shape(value: Any, keys: set[str], name: str) -> None:
    _require(type(value) is dict and set(value) == keys, name + " schema differs")


def _integer(value: Any, name: str, *, minimum: int = 1) -> None:
    _require(type(value) is int and value >= minimum, name + " must be a plain bounded integer")


def _text(value: Any, name: str) -> None:
    _require(type(value) is str and bool(value.strip()), name + " must be a nonempty plain string")
    _require(not any(unicodedata.category(char) == "Cs" for char in value), name + " contains surrogate")


def _hash(value: Any, name: str) -> None:
    _require(type(value) is str and _SHA.fullmatch(value) is not None, name + " must be SHA256")


def _identifier(value: Any, prefix: str) -> None:
    _require(type(value) is str and re.fullmatch(prefix + r"[1-9][0-9]*", value) is not None,
             "Invalid source section/table identifier")


def _faults(value: str) -> list[str]:
    reasons = []
    if any(unicodedata.category(char) == "Cc" and char not in "\t\r\n" for char in value):
        reasons.append("UNSUPPORTED_RAW_CONTROL_CHARACTER")
    if any(unicodedata.category(char) in {"Cf", "Cs"} for char in value):
        reasons.append("UNSUPPORTED_RAW_FORMAT_OR_SURROGATE_CHARACTER")
    return reasons


def _layout(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value.replace("\\n", "\n")).split()).casefold()


def _lexical_faults(value: str) -> list[str]:
    reasons = _faults(value)
    marks = "\u0300\u0301\u0302\u0303\u0306\u0309\u031b\u0323"
    for char in value:
        if char.isascii() or char in marks or unicodedata.category(char) in {"Zs", "Zl", "Zp"}:
            continue
        if char in "đĐ":
            continue
        decomposed = unicodedata.normalize("NFD", char)
        vietnamese_letter = (
            (0x00C0 <= ord(char) <= 0x024F or 0x1EA0 <= ord(char) <= 0x1EF9)
            and all((part.isascii() and part.isalpha()) or part in marks for part in decomposed)
        )
        if not vietnamese_letter:
            reasons.append("UNSUPPORTED_RAW_LEXICAL_CHARACTER")
            break
    return reasons


def parse_part_scoped_period_lexical_v1(*, heading_exact: str, clause_exact: str) -> dict[str, Any]:
    """Recognize whole finite strings and explicit calendars, not ownership."""
    _text(heading_exact, "heading_exact")
    _text(clause_exact, "clause_exact")
    faults = sorted(set(_lexical_faults(heading_exact) + _lexical_faults(clause_exact)))
    heading = _layout(heading_exact) if not faults else None
    clause = _layout(clause_exact) if not faults else None
    heading_matches = heading == _layout(PART_PERIOD_HEADING_EXACT)
    relevant = bool(heading_matches or (heading is not None and clause is not None
                                       and _MOTIF.search(heading + " " + clause)))
    reasons, semantics, tokens = list(faults), None, None
    if faults:
        status = "ALGORITHM_HOLD"
    elif not relevant:
        status = "NOT_APPLICABLE"
        reasons.append("NO_RECOGNIZED_PART_PERIOD_ASSERTION")
    elif not heading_matches:
        status = "ALGORITHM_HOLD"
        reasons.append("WHOLE_PRINTED_HEADING_NOT_SUPPORTED")
    else:
        match = _CLAUSE.fullmatch(clause)
        if match is None:
            status = "ALGORITHM_HOLD"
            reasons.append("WHOLE_PRINTED_PERIOD_CLAUSE_NOT_SUPPORTED")
        else:
            tokens = match.groupdict()
            try:
                parsed = {key: date(*(int(part) for part in reversed(token.split("/"))))
                          for key, token in tokens.items()}
            except ValueError:
                status = "ALGORITHM_HOLD"
                reasons.append("INVALID_PRINTED_CALENDAR_DATE")
            else:
                for prefix in ("current", "comparative"):
                    first, last = parsed[prefix + "_start"], parsed[prefix + "_end"]
                    if (first.month, first.day) != (1, 1):
                        reasons.append("PRINTED_START_NOT_JANUARY_FIRST:" + prefix)
                    if first.year != last.year:
                        reasons.append("PRINTED_WINDOW_CROSSES_YEAR:" + prefix)
                    if last.month not in {3, 6, 9, 12} or last.day != calendar.monthrange(last.year, last.month)[1]:
                        reasons.append("PRINTED_END_NOT_SUPPORTED_QUARTER_OR_YEAR_END:" + prefix)
                if parsed["current_end"].month != parsed["comparative_end"].month:
                    reasons.append("PRINTED_DURATION_LENGTHS_DIFFER")
                if parsed["comparative_start"].year >= parsed["current_start"].year:
                    reasons.append("COMPARATIVE_PRINTED_YEAR_NOT_EARLIER")
                status = "ALGORITHM_HOLD" if reasons else "PASS"
                if not reasons:
                    months = parsed["current_end"].month
                    semantics = {
                        "kind": "ANNUAL" if months == 12 else "YTD", "printed_months": months,
                        **{prefix: {"start_date": parsed[prefix + "_start"].isoformat(),
                                    "end_date": parsed[prefix + "_end"].isoformat(),
                                    "printed_year": parsed[prefix + "_start"].year}
                           for prefix in ("current", "comparative")},
                        "comparative_origin": "EXPLICIT_PRINTED_DATE_PAIR",
                        "comparative_year_inferred": False, "start_dates_inferred": False,
                    }
    sources = {"heading_exact": heading_exact, "clause_exact": clause_exact}
    material = {
        "format_version": "INCOME_TAX_PART_PERIOD_LEXICAL_V1", "status": status,
        "reasons": sorted(set(reasons)), "whole_heading_lexically_matches": heading_matches,
        "calendar_only_semantics": semantics, "printed_date_tokens_normalized_layout_only": tokens,
        "raw_sources_exact": sources,
        "raw_source_sha256": {key: sha256(raw.encode("utf-8")).hexdigest() for key, raw in sources.items()},
        "raw_source_size_bytes": {key: len(raw.encode("utf-8")) for key, raw in sources.items()},
        "raw_source_lines_exact": {key: raw.splitlines(keepends=True) for key, raw in sources.items()},
        "owner_span_status": "UNPROVEN_SEPARATE_NARRATIVE_AND_TABLE_EVENT_AXIS_NOT_BOUND",
        "permission_grants": {"owner_span": False, **_PERMISSIONS},
        "amounts_used_as_authority": False, "source_period_keys_modified": False,
        "source_values_modified": False, "receipt_hash_is_source_authentication": False,
    }
    return {**material, "receipt_id": "gjitppcv1:lexical:" + sha256(_canonical(material)).hexdigest()}


def _ref(value: Any) -> None:
    _shape(value, {"path", "sha256", "size_bytes"}, "Evidence ref")
    _text(value["path"], "Evidence path")
    _require(not any(char in value["path"] for char in "\x00\r\n")
             and ".." not in value["path"].replace("\\", "/").split("/")
             and value["path"].replace("\\", "/").split("/")[-1].casefold()
             not in {"openrouter_api.txt", "codex-session.passphrase"}, "Unsafe evidence ref")
    _hash(value["sha256"], "Evidence SHA")
    _integer(value["size_bytes"], "Evidence bytes")


def _section_hashes(item: dict[str, Any]) -> None:
    for key in ("original_section_json_sha256", "evaluation_section_json_sha256"):
        _hash(item[key], key)


def _page_identity(item: dict[str, Any], pages: dict[str, dict[str, Any]]) -> None:
    _require(type(item["page_json_version_id"]) is str and item["page_json_version_id"] in pages,
             "Occurrence/target outside registered span")
    page = pages[item["page_json_version_id"]]
    _require(type(item["physical_page"]) is int and item["physical_page"] == page["physical_page"],
             "Registered occurrence/target physical page differs")
    _identifier(item["section_id"], "s")
    _section_hashes(item)


def _carrier_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (item["page_json_version_id"], item["section_id"], item["carrier_kind"],
            item["table_id"], item["narrative_ordinal"])


def validate_registered_part_period_registry_v1(registry: Any) -> dict[str, Any]:
    """Strict schema/lexical checks only; caller JSON never authenticates itself."""
    value = _clone(registry)
    _shape(value, {"format_version", "family_id", "base_git_commit", "contexts"}, "Registry")
    _require(value["format_version"] == REGISTRY_FORMAT_VERSION and value["family_id"] == FAMILY_ID
             and value["base_git_commit"] == BASE_GIT_COMMIT, "Registry identity differs")
    _require(type(value["contexts"]) is list, "Contexts must be a plain list")
    ids, target_keys, spans = set(), set(), []
    document_sources, source_documents = {}, {}
    for context in value["contexts"]:
        _shape(context, {"context_id", "pdf_source", "document_id", "provenance_document_ordinal",
                         "span_pages", "heading_occurrences", "period_occurrences", "target_tables",
                         "review_evidence"}, "Context")
        cid = context["context_id"]
        _require(type(cid) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}", cid) is not None
                 and cid not in ids, "Context ID invalid or duplicate")
        ids.add(cid)
        pdf = context["pdf_source"]
        _shape(pdf, {"logical_name", "sha256", "size_bytes"}, "PDF source")
        _text(pdf["logical_name"], "PDF logical name")
        _require(not pdf["logical_name"].startswith("/") and "\\" not in pdf["logical_name"]
                 and ":" not in pdf["logical_name"]
                 and not any(unicodedata.category(char) in {"Cc", "Cf", "Cs"} for char in pdf["logical_name"])
                 and not {"", ".", ".."} & set(pdf["logical_name"].split("/")), "Unsafe PDF logical name")
        _hash(pdf["sha256"], "PDF source SHA")
        _integer(pdf["size_bytes"], "PDF bytes")
        _require(type(context["document_id"]) is str and _DOC.fullmatch(context["document_id"]) is not None,
                 "Document ID invalid")
        _integer(context["provenance_document_ordinal"], "Provenance ordinal")
        pages = context["span_pages"]
        _require(type(pages) is list and bool(pages), "Finite nonempty span required")
        by_vid = {}
        for offset, page in enumerate(pages):
            _shape(page, _PAGE_KEYS, "Span page")
            _integer(page["physical_page"], "Physical page")
            _integer(page["selected_page_ordinal"], "Selected ordinal")
            vid = page["page_json_version_id"]
            _require(type(vid) is str and _VID.fullmatch(vid) is not None and vid not in by_vid,
                     "Span VID invalid or duplicate")
            for key in ("original_page_json_sha256", "evaluation_page_json_sha256"):
                _hash(page[key], key)
            _require(page["physical_page"] == pages[0]["physical_page"] + offset
                     and page["selected_page_ordinal"] == pages[0]["selected_page_ordinal"] + offset,
                     "Span must be explicitly contiguous in both axes")
            by_vid[vid] = page
        source_key = (pdf["logical_name"], pdf["sha256"])
        _require(document_sources.setdefault(context["document_id"], source_key) == source_key
                 and source_documents.setdefault(source_key, context["document_id"]) == context["document_id"],
                 "Registered document/source identity aliases")
        for other_source, first, last in spans:
            _require(source_key != other_source or pages[-1]["physical_page"] < first
                     or pages[0]["physical_page"] > last, "Registered part spans overlap")
        spans.append((source_key, pages[0]["physical_page"], pages[-1]["physical_page"]))
        carriers = {}
        lexical = []
        for field in ("heading_occurrences", "period_occurrences"):
            occurrences = context[field]
            _require(type(occurrences) is list and bool(occurrences), "Heading and clause occurrences required")
            for occurrence in occurrences:
                _shape(occurrence, _OCC_KEYS, "Occurrence")
                _page_identity(occurrence, by_vid)
                kind = occurrence["carrier_kind"]
                _require(type(kind) is str and kind in {"NARRATIVE", "SECTION_TITLE", "TABLE_TITLE"},
                         "Unreviewed carrier kind")
                if kind == "TABLE_TITLE":
                    _identifier(occurrence["table_id"], "t")
                else:
                    _require(occurrence["table_id"] is None, "Non-table carrier must have null table ID")
                if kind == "NARRATIVE":
                    _integer(occurrence["narrative_ordinal"], "Narrative ordinal")
                else:
                    _require(occurrence["narrative_ordinal"] is None, "Non-narrative ordinal must be null")
                for key in ("source_exact", "substring_exact"):
                    _text(occurrence[key], key)
                    _require(not _faults(occurrence[key]), "Unsupported raw carrier characters")
                _hash(occurrence["source_sha256"], "Carrier source SHA")
                _require(sha256(occurrence["source_exact"].encode("utf-8")).hexdigest()
                         == occurrence["source_sha256"], "Carrier SHA differs")
                _integer(occurrence["span_start"], "Span start", minimum=0)
                _integer(occurrence["span_end"], "Span end")
                _require(occurrence["span_start"] < occurrence["span_end"] <= len(occurrence["source_exact"])
                         and occurrence["source_exact"][occurrence["span_start"]:occurrence["span_end"]]
                         == occurrence["substring_exact"], "Exact carrier character slice differs")
                key = _carrier_key(occurrence)
                prior = carriers.setdefault(key, [])
                _require(all(other["source_exact"] == occurrence["source_exact"]
                             and (occurrence["span_end"] <= other["span_start"]
                                  or occurrence["span_start"] >= other["span_end"]) for other in prior),
                         "Carrier occurrences duplicate, overlap or disagree")
                prior.append(occurrence)
                if field == "heading_occurrences":
                    _require(not _lexical_faults(occurrence["substring_exact"])
                             and _layout(occurrence["substring_exact"]) == _layout(PART_PERIOD_HEADING_EXACT),
                             "Whole registered heading not supported")
                else:
                    proof = parse_part_scoped_period_lexical_v1(
                        heading_exact=PART_PERIOD_HEADING_EXACT, clause_exact=occurrence["substring_exact"])
                    _require(proof["status"] == "PASS", "Registered clause not lexically complete")
                    lexical.append(proof)
        _require(all(item["calendar_only_semantics"] == lexical[0]["calendar_only_semantics"] for item in lexical),
                 "Competing registered calendar clauses")
        for occurrences in carriers.values():
            remainder = occurrences[0]["source_exact"]
            for occurrence in sorted(occurrences, key=lambda item: item["span_start"], reverse=True):
                remainder = remainder[:occurrence["span_start"]] + " " + remainder[occurrence["span_end"]:]
            # A numbered income-note caption can share the same title carrier;
            # its exact raw source remains retained, never an owner reset waiver.
            tail = _layout(remainder)
            _require(not tail or re.fullmatch(r"[1-9][0-9]*\. thu nhập lãi thuần", tail) is not None,
                     "Unconsumed carrier prefix/suffix assertion")
        targets = context["target_tables"]
        _require(type(targets) is list and bool(targets), "At least one explicit target required")
        for target in targets:
            _shape(target, _TARGET_KEYS, "Target")
            _page_identity(target, by_vid)
            page = by_vid[target["page_json_version_id"]]
            _require(type(target["selected_page_ordinal"]) is int
                     and target["selected_page_ordinal"] == page["selected_page_ordinal"], "Target selected axis differs")
            _identifier(target["table_id"], "t")
            for key in ("original_table_json_sha256", "evaluation_table_json_sha256"):
                _hash(target[key], key)
            columns = target["money_column_ordinals"]
            _require(type(columns) is list and len(columns) == 2
                     and all(type(column) is int and column >= 1 for column in columns)
                     and len(set(columns)) == 2, "Two distinct raw column ordinals required")
            paths = target["header_paths_exact"]
            _require(type(paths) is list and len(paths) == 2, "Two exact header paths required")
            for path in paths:
                _require(type(path) is list and bool(path), "Header paths must be nonempty plain lists")
                for part in path:
                    _text(part, "Header component")
            kinds = target["column_value_kinds"]
            _require(type(kinds) is list and len(kinds) == 2
                     and all(type(kind) is str and kind in {"MONEY", "UNKNOWN"} for kind in kinds),
                     "Target column metadata must remain MONEY or UNKNOWN")
            _require(target["period_order"] == ["CURRENT", "COMPARATIVE"], "Literal period orientation differs")
            key = (*source_key, context["document_id"], target["page_json_version_id"], target["section_id"], target["table_id"])
            _require(key not in target_keys, "Target duplicated across registered contexts")
            target_keys.add(key)
        first_assertion = min(item["physical_page"] for field in ("heading_occurrences", "period_occurrences") for item in context[field])
        last_assertion = max(item["physical_page"] for field in ("heading_occurrences", "period_occurrences") for item in context[field])
        _require(pages[0]["physical_page"] == first_assertion
                 and pages[-1]["physical_page"] == max(item["physical_page"] for item in targets)
                 and last_assertion <= min(item["physical_page"] for item in targets),
                 "Part span is not the minimal prefix-to-target endpoint")
        review = context["review_evidence"]
        _shape(review, {"manual_review_ref", "visual_refs", "no_reset_observation_exact"}, "Review evidence")
        _ref(review["manual_review_ref"])
        _text(review["no_reset_observation_exact"], "Positive no-reset observation")
        _require(type(review["visual_refs"]) is list and bool(review["visual_refs"]), "Positive visual refs required")
        visual_pages, visual_keys = set(), set()
        for visual in review["visual_refs"]:
            _shape(visual, {"png_ref", "render_receipt_ref", "physical_page", "renderer_version", "dpi",
                            "width_pixels", "height_pixels"}, "Visual evidence")
            _ref(visual["png_ref"])
            _ref(visual["render_receipt_ref"])
            _text(visual["renderer_version"], "Renderer version")
            for key in ("physical_page", "dpi", "width_pixels", "height_pixels"):
                _integer(visual[key], key)
            vkey = (visual["physical_page"], visual["png_ref"]["path"])
            _require(vkey not in visual_keys, "Duplicate visual evidence")
            visual_keys.add(vkey)
            visual_pages.add(visual["physical_page"])
        _require({item["physical_page"] for field in ("heading_occurrences", "period_occurrences")
                  for item in context[field]} <= visual_pages, "Prefix source pages lack registered visual evidence")
    return value


def _section(record: dict[str, Any], identifier: str) -> dict[str, Any]:
    try:
        return record["page_json"]["sections"][int(identifier[1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise GeminiJsonIncomeTaxPartPeriodContextV1Error("Source section locator drifted") from error


def _table(section: dict[str, Any], identifier: str) -> dict[str, Any]:
    try:
        return section["tables"][int(identifier[1:]) - 1]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise GeminiJsonIncomeTaxPartPeriodContextV1Error("Source table locator drifted") from error


def _domain(actual: str, original: str, evaluation: str, stage: str | None = None) -> str:
    _require(actual in {original, evaluation}, "Original/evaluation source hash drifted")
    found = "ORIGINAL_AND_EVALUATION_IDENTICAL" if original == evaluation else "ORIGINAL" if actual == original else "EVALUATION"
    _require(stage is None or found == "ORIGINAL_AND_EVALUATION_IDENTICAL" or stage == found,
             "Mixed original/evaluation hash domains")
    return found


def _validate_source_page(page: Any) -> None:
    """Check traversal types without interpreting or normalizing raw content."""
    _require(type(page) is dict and type(page.get("sections")) is list, "Original page section axis malformed")
    for section in page["sections"]:
        _require(type(section) is dict and type(section.get("tables")) is list
                 and type(section.get("narratives_exact")) is list, "Original section axes malformed")
        _require(section.get("title_exact") is None or type(section.get("title_exact")) is str,
                 "Original section title malformed")
        _require(all(type(text) is str for text in section["narratives_exact"]), "Original narrative axis malformed")
        for table in section["tables"]:
            _require(type(table) is dict and type(table.get("columns")) is list and type(table.get("rows")) is list,
                     "Original table axes malformed")
            _require(table.get("title_exact") is None or type(table.get("title_exact")) is str,
                     "Original table title malformed")
            for column in table["columns"]:
                _require(type(column) is dict and type(column.get("header_path_exact")) is list,
                         "Original column axis malformed")
            for row in table["rows"]:
                _require(type(row) is dict and type(row.get("hierarchy_path_exact")) is list
                         and type(row.get("values_exact")) is list
                         and len(row["values_exact"]) == len(table["columns"]), "Original row/column width malformed")
                _require(row.get("label_exact") is None or type(row.get("label_exact")) is str,
                         "Original row label malformed")
                _require(all(value is None or type(value) is str for value in row["hierarchy_path_exact"]),
                         "Original hierarchy axis malformed")


def _surface_axis(record: dict[str, Any]) -> list[tuple[tuple[Any, ...], str]]:
    surfaces = []
    vid = record["page_json_version_id"]
    for si, section in enumerate(record["page_json"].get("sections") or [], 1):
        sid = f"s{si}"
        surfaces.append(((vid, sid, "SECTION_TITLE", None, None), section.get("title_exact")))
        for ni, text in enumerate(section.get("narratives_exact") or [], 1):
            surfaces.append(((vid, sid, "NARRATIVE", None, ni), text))
        for ti, table in enumerate(section.get("tables") or [], 1):
            surfaces.append(((vid, sid, "TABLE_TITLE", f"t{ti}", None), table.get("title_exact")))
            for ri, row in enumerate(table.get("rows") or [], 1):
                surfaces.append(((vid, sid, "ROW_LABEL", f"t{ti}", ri), row.get("label_exact")))
                for pi, text in enumerate(row.get("hierarchy_path_exact") or [], 1):
                    surfaces.append(((vid, sid, "ROW_PATH", f"t{ti}", ri, pi), text))
    return surfaces


def replay_registered_part_period_contexts_v1(page_records: Any, *, registry: Any) -> list[dict[str, Any]]:
    """Bind a separately approved registry to fresh source objects, without I/O.

    A PASS is NOT PDF/registry authentication. Runtime ordinals are retained in
    target locators; registered corpus ordinals are provenance only.
    """
    registered = validate_registered_part_period_registry_v1(registry)
    records = _clone(page_records)
    _require(type(records) is list and bool(records), "Nonempty source page records required")
    identity_keys = ("document_id", "document_ordinal", "source_logical_name", "source_sha256")
    identities, versions, physicals, selected = set(), set(), set(), set()
    for record in records:
        _require(type(record) is dict and all(key in record for key in (*identity_keys, "physical_page",
                     "selected_page_ordinal", "page_json_version_id", "page_json")), "Source record axis incomplete")
        for key in ("document_ordinal", "physical_page", "selected_page_ordinal"):
            _integer(record[key], key)
        _require(type(record["page_json_version_id"]) is str and _VID.fullmatch(record["page_json_version_id"]) is not None,
                 "Runtime source VID invalid")
        _require(type(record["document_id"]) is str and _DOC.fullmatch(record["document_id"]) is not None,
                 "Runtime document ID invalid")
        _hash(record["source_sha256"], "Runtime source SHA")
        _text(record["source_logical_name"], "Runtime source logical name")
        _validate_source_page(record["page_json"])
        identities.add(tuple(record[key] for key in identity_keys))
        for value, seen in ((record["page_json_version_id"], versions), (record["physical_page"], physicals),
                            (record["selected_page_ordinal"], selected)):
            _require(value not in seen, "Duplicate runtime source axis")
            seen.add(value)
    _require(len(identities) == 1, "Foreign/multiple runtime document identities")
    identity = records[0]
    by_vid = {record["page_json_version_id"]: record for record in records}
    receipts = []
    for context in registered["contexts"]:
        pdf = context["pdf_source"]
        match_fields = (context["document_id"] == identity["document_id"],
                        pdf["logical_name"] == identity["source_logical_name"], pdf["sha256"] == identity["source_sha256"])
        if not any(match_fields):
            continue
        _require(all(match_fields), "Registered document/source identity drifted")
        span = context["span_pages"]
        actual_axis = sorted((record["physical_page"], record["selected_page_ordinal"], record["page_json_version_id"])
                             for record in records if span[0]["physical_page"] <= record["physical_page"] <= span[-1]["physical_page"])
        _require(actual_axis == [(page["physical_page"], page["selected_page_ordinal"], page["page_json_version_id"])
                                 for page in span], "Registered span has omitted, extra or changed source pages")
        stages = set()
        for page in span:
            record = by_vid.get(page["page_json_version_id"])
            _require(record is not None, "Registered span source page missing")
            stage = _domain(sha256(_canonical(record["page_json"])).hexdigest(),
                            page["original_page_json_sha256"], page["evaluation_page_json_sha256"])
            if stage != "ORIGINAL_AND_EVALUATION_IDENTICAL":
                stages.add(stage)
        _require(len(stages) <= 1, "Mixed original/evaluation page stages")
        stage = next(iter(stages)) if stages else "ORIGINAL_AND_EVALUATION_IDENTICAL"
        occurrences_by_key = {}
        for field in ("heading_occurrences", "period_occurrences"):
            for occurrence in context[field]:
                record = by_vid[occurrence["page_json_version_id"]]
                section = _section(record, occurrence["section_id"])
                _domain(sha256(_canonical(section)).hexdigest(), occurrence["original_section_json_sha256"],
                        occurrence["evaluation_section_json_sha256"], stage if stages else None)
                actual = dict(_surface_axis(record)).get(_carrier_key(occurrence))
                _require(actual == occurrence["source_exact"], "Registered carrier source text drifted")
                occurrences_by_key.setdefault(_carrier_key(occurrence), []).append(occurrence)
        # Freshly inspect every retained part surface, not only target rows or
        # one caller-selected heading. Known new part/reset assertions cannot
        # be hidden by updating page hashes in caller-supplied registration.
        reset_axis = []
        for page in span:
            for key, raw in _surface_axis(by_vid[page["page_json_version_id"]]):
                if raw is None:
                    continue
                _require(type(raw) is str, "Part source surface is not a plain string")
                remainder = raw
                for occurrence in sorted(occurrences_by_key.get(key, []), key=lambda item: item["span_start"], reverse=True):
                    remainder = remainder[:occurrence["span_start"]] + " " + remainder[occurrence["span_end"]:]
                _require(not _faults(raw), "Unsupported raw control/format in registered part surface")
                for line in re.split(r"\r\n|\r|\n|\\n", remainder):
                    _require(_RESET.match(_layout(line)) is None, "Unregistered part heading, clause or reset source assertion")
                reset_axis.append({"source_surface_key": list(key), "source_exact": raw,
                                   "source_sha256": sha256(raw.encode("utf-8")).hexdigest(),
                                   "registered_occurrence_count": len(occurrences_by_key.get(key, []))})
        proof = parse_part_scoped_period_lexical_v1(
            heading_exact=context["heading_occurrences"][0]["substring_exact"],
            clause_exact=context["period_occurrences"][0]["substring_exact"])
        semantics = proof["calendar_only_semantics"]
        months = semantics["printed_months"]
        periods = [["ANNUAL_YEAR", semantics[key]["printed_year"]] if months == 12
                   else ["SOURCE_YTD_QUARTER", semantics[key]["printed_year"], months // 3]
                   for key in ("current", "comparative")]
        for target in context["target_tables"]:
            record = by_vid[target["page_json_version_id"]]
            section = _section(record, target["section_id"])
            table = _table(section, target["table_id"])
            _require(record["page_json"].get("status") == "FINANCIAL_NOTE_CONTENT"
                     and section.get("content_kind") == "FINANCIAL_NOTE"
                     and section.get("statement_type") == "NOT_APPLICABLE", "Registered target is not original FINANCIAL_NOTE")
            _domain(sha256(_canonical(section)).hexdigest(), target["original_section_json_sha256"],
                    target["evaluation_section_json_sha256"], stage if stages else None)
            _domain(sha256(_canonical(table)).hexdigest(), target["original_table_json_sha256"],
                    target["evaluation_table_json_sha256"], stage if stages else None)
            columns, rows = table.get("columns"), table.get("rows")
            _require(type(columns) is list and type(rows) is list and all(type(row) is dict
                     and type(row.get("values_exact")) is list and len(row["values_exact"]) == len(columns)
                     for row in rows), "Original target row/column width differs")
            ordinals = target["money_column_ordinals"]
            _require(all(ordinal <= len(columns) for ordinal in ordinals), "Registered raw column missing")
            actual_columns = [columns[ordinal - 1] for ordinal in ordinals]
            _require([column.get("header_path_exact") for column in actual_columns] == target["header_paths_exact"]
                     and [column.get("value_kind") for column in actual_columns] == target["column_value_kinds"],
                     "Original target header orientation or metadata drifted")
            locator = {key: record[key] for key in (*identity_keys, "page_json_version_id", "physical_page", "selected_page_ordinal")}
            locator.update(section_id=target["section_id"], table_id=target["table_id"])
            material = {
                "format_version": "INCOME_TAX_REGISTERED_PART_PERIOD_SOURCE_BINDING_V1",
                "status": "PASS_REGISTERED_SOURCE_BINDINGS_NOT_PDF_AUTHENTICATION", "complete": True,
                "context_id": context["context_id"], "source_stage": stage, "target_locator": locator,
                "raw_column_ordinals": ordinals, "header_paths_exact": target["header_paths_exact"],
                "column_value_kinds": target["column_value_kinds"], "unknown_columns_promoted": False,
                "resolved_source_duration_semantics": periods, "calendar_lexical_receipt": proof,
                "registry_sha256": sha256(_canonical(registered)).hexdigest(),
                "registered_context_exact": context, "target_registration_exact": target,
                "fresh_part_surface_axis": reset_axis,
                "original_and_evaluation_hash_domains_distinct": True,
                "registry_json_authenticated": False, "pdf_evidence_authenticated": False,
                "receipt_hash_is_source_authentication": False, "permission_grants": _PERMISSIONS,
                "comparative_year_inferred": False, "start_dates_inferred": False,
                "source_period_keys_modified": False, "source_values_modified": False,
                "amounts_used_as_authority": False,
            }
            receipts.append({**_clone(material), "receipt_id": "gjitppcv1:source-binding:" + sha256(_canonical(material)).hexdigest()})
    return receipts
