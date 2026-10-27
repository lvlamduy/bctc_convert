"""UNRUN stdlib census of fixed, completed ORIGINAL metadata; no financial acceptance.

Linux Python3.12 -I -B. Root alone may schedule this after reviewed synthetic
controls and N1/N2. No project import, SQLite, PDF, extraction or provider access.
One JSON parse pass feeds all13 literal catalogs. Hash-only byte passes are
separate from that parse pass. Source-version identities are never collapsed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import stat
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from contextlib import ExitStack
from pathlib import Path

CATALOG_SHA = "13fc0706cfe231af1eb65335d0a81b77600be68a76be657d730eaa4621259b30"
CATALOG_BYTES = 551625
SOURCE_ROOT = "/srv/bctc-receipts/f36-neutral-original-inventory-full271-20261025-v1"
INPUTS = {
    "stream": {"path": SOURCE_ROOT + "/inventory/selected-original-inventory.jsonl",
               "sha256": "56167838f53dfd967c4d91ed7ae269350dd465ecfb19d8c1f529aafb77e99fe5", "size_bytes": 228533818},
    "inventory": {"path": SOURCE_ROOT + "/inventory/F36_NEUTRAL_SELECTED_ORIGINAL_INVENTORY_V1.json",
                  "sha256": "4936372ac91816ff50825eca3783e1292091e39c98ca199e244f7721f5ea9437", "size_bytes": 1949},
    "controlled": {"path": SOURCE_ROOT + "/F36_CONTROLLED_NEUTRAL_ORIGINAL_INVENTORY_RUN_V1.json",
                   "sha256": "98a0677d48d6d52fba37a0cde4b2dc83df064ba65a26537c5b6e98df1457511c", "size_bytes": 1097083},
}
PAGE_STATUSES = ("FINANCIAL_NOTE_CONTENT", "MIXED_FINANCIAL_CONTENT", "NO_RELEVANT_FINANCIAL_CONTENT", "PRIMARY_FINANCIAL_STATEMENT")
EXPECTED = {"document": 271, "page": 14945, "table": 19465, "row": 171311, "value_slots": 581227}
DATABASE_REF = {"path": "current-corpus-freeze-inputs/store-ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7.sqlite3",
                "sha256": "ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7", "size_bytes": 573145088}
CORPUS_INDEX_REF = {"path": "current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json",
                    "sha256": "969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219", "size_bytes": 422971}
MAX_LINE = 8 * 1024**2
MAX_TABLE_METADATA = 8 * 1024**2
MAX_OUTPUT = 512 * 1024**2
MIN_MEM = 1536 * 1024**2
KINDS = {"document", "page", "section", "table", "column", "row", "unsupported_shape", "document_frontier_verified"}
SHA = re.compile(r"[0-9a-f]{64}\Z")
POINTER = re.compile(r"/sections/(0|[1-9][0-9]*)(?:/tables/(0|[1-9][0-9]*)(?:/(columns|rows)/(0|[1-9][0-9]*))?)?\Z")


class CensusError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise CensusError(message)


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(CensusError("Nonfinite JSON:" + token)))


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def field(record, key):
    """Read the producer's actual presence/value envelope, never value fallback."""
    fields = record.get("fields")
    need(type(fields) is dict and key in fields, "Missing typed field envelope:" + key)
    envelope = fields[key]
    need(type(envelope) is dict and set(envelope) == {"present", "value"}
         and type(envelope["present"]) is bool, "Malformed presence/value envelope:" + key)
    need(envelope["present"] or envelope["value"] is None, "Absent field carries a value:" + key)
    return envelope


def normalized(text):
    need(type(text) is str, "Only literal source strings can be normalized")
    text = unicodedata.normalize("NFD", unicodedata.normalize("NFC", text).casefold()).replace("đ", "d")
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).translate(
        str.maketrans({c: " " for c in set(text) if not c.isalnum() and not c.isspace()})).split())


class LiteralPlan:
    """Token-dispatched literal search; none of these hits is semantic acceptance."""
    def __init__(self, families):
        self.families = {f["family_number"]: f for f in families}
        need(len(self.families) == len(families), "Duplicate family catalog")
        self.first_token = defaultdict(list)
        self.punctuation_exact = defaultdict(list)
        self.registered_alias_count = 0
        self.punctuation_alias_count = 0
        for family in families:
            for ordinal, alias in enumerate(family["aliases"], 1):
                text = normalized(alias["literal"])
                self.registered_alias_count += 1
                if not text:
                    literal = unicodedata.normalize("NFC", alias["literal"]).strip()
                    need(bool(literal) and all(unicodedata.category(char)[0] in {"P", "S"} or char.isspace() for char in literal),
                         "Empty or unsupported non-punctuation normalized registered alias")
                    self.punctuation_exact[literal].append((family["family_number"], ordinal, alias["kind"]))
                    self.punctuation_alias_count += 1
                    continue
                self.first_token[text.split()[0]].append((family["family_number"], ordinal, text, alias["kind"]))

    def hits(self, text):
        key = normalized(text)
        result = defaultdict(list)
        padded = " " + key + " "
        for first in sorted(set(key.split())):
            for family, ordinal, alias, kind in self.first_token.get(first, ()):
                if " " + alias + " " in padded:
                    result[family].append({"catalog_alias_ordinal": ordinal, "kind": kind,
                                           "match": "NORMALIZED_WHOLE_TOKEN_LITERAL", "generic_short_phrase": len(alias.split()) <= 3})
        literal = unicodedata.normalize("NFC", text).strip()
        for family, ordinal, kind in self.punctuation_exact.get(literal, ()):
            result[family].append({"catalog_alias_ordinal": ordinal, "kind": kind,
                                   "match": "NFC_OUTER_TRIM_WHOLE_FIELD_EXACT_PUNCTUATION", "generic_short_phrase": True,
                                   "punctuation_only": True, "evidence_only": "WEAK_WHOLE_FIELD_PUNCTUATION_SIDE_EVIDENCE"})
        return dict(result)


def identity(value):
    return tuple(getattr(value, key) for key in ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns"))


def safe(path):
    path = Path(path)
    need(path.is_absolute() and ".." not in path.parts, "Absolute path without '..' required")
    for component in (path, *path.parents):
        need(not component.is_symlink(), "Symlink path prohibited")
    return path


class Held:
    def __init__(self):
        self.items = {}

    @staticmethod
    def hash_fd(fd):
        value, offset = hashlib.sha256(), 0
        while block := os.pread(fd, 1024**2, offset):
            value.update(block)
            offset += len(block)
        return value.hexdigest(), offset

    def open(self, reference):
        need(type(reference) is dict and set(reference) == {"path", "sha256", "size_bytes"}
             and type(reference["sha256"]) is str and SHA.fullmatch(reference["sha256"])
             and integer(reference["size_bytes"], 1), "Exact positive-byte reference required")
        path = safe(reference["path"])
        key = str(path)
        if key not in self.items:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                before = os.fstat(fd)
                need(stat.S_ISREG(before.st_mode) and self.hash_fd(fd) == (reference["sha256"], reference["size_bytes"])
                     and identity(before) == identity(os.fstat(fd)) == identity(os.stat(path, follow_symlinks=False)), "Held input pin/identity differs")
            except BaseException:
                os.close(fd)
                raise
            self.items[key] = (fd, identity(before), dict(reference))
        need(self.items[key][2] == reference, "Conflicting pins for one input")
        return self.items[key][0]

    def read_json(self, reference, maximum):
        need(reference["size_bytes"] <= maximum, "Metadata exceeds fixed bound")
        fd = self.open(reference)
        raw = os.pread(fd, reference["size_bytes"] + 1, 0)
        need((hashlib.sha256(raw).hexdigest(), len(raw)) == (reference["sha256"], reference["size_bytes"]), "Captured metadata differs")
        return strict_json(raw)

    def validate(self):
        for path, (fd, initial, reference) in self.items.items():
            need(initial == identity(os.fstat(fd)) == identity(os.stat(path, follow_symlinks=False))
                 and self.hash_fd(fd) == (reference["sha256"], reference["size_bytes"]), "Final held input drift:" + path)

    def close(self):
        for fd, _identity, _ref in self.items.values():
            os.close(fd)


def validate_historical_producer_ref(reference, expected):
    """Validate the exact wrapper ref shape; historical inode is not live authority.

    The wrapper's raw receipt is independently pinned before this function. This
    metadata check performs no I/O and never compares historical inode numbers
    with a restored file. Held supplies separate fresh FD/hash/identity barriers.
    """
    need(type(reference) is dict and set(reference) == {"path", "sha256", "size_bytes", "identity"},
         "Historical producer reference fields differ")
    need(type(expected) is dict and set(expected) == {"path", "sha256", "size_bytes"}
         and type(reference["path"]) is str and type(reference["sha256"]) is str
         and SHA.fullmatch(reference["sha256"]) and integer(reference["size_bytes"], 1),
         "Historical producer path/SHA/size types differ")
    captured = reference["identity"]
    need(type(captured) is list and len(captured) == 6 and all(type(value) is int for value in captured),
         "Historical producer identity must have six plain integers")
    need(captured[0] >= 0 and captured[1] > 0 and captured[2] >= 0 and stat.S_ISREG(captured[2])
         and captured[3] > 0 and captured[3] == reference["size_bytes"] == expected["size_bytes"]
         and captured[4] >= 0 and captured[5] >= 0, "Historical producer identity mode/size/bounds differ")
    need(canonical({key: reference[key] for key in ("path", "sha256", "size_bytes")}) == canonical(expected),
         "Historical producer path/SHA/size differs from immutable input")
    return strict_json(canonical(reference))


def validate_completion(inventory, controlled):
    need(inventory["format_version"] == "F36_NEUTRAL_SELECTED_ORIGINAL_INVENTORY_V1"
         and inventory["status"] == "COMPLETE_NEUTRAL_INVENTORY_NOT_FAMILY_OR_PDF_PROOF"
         and inventory["errors"] == [] and inventory["source_context_successfully_exited"] is True
         and inventory["complete_selected_page_frontier"] is True and inventory["status_filter_applied"] is False,
         "Original neutral completion is failed, partial or filtered")
    need(inventory["expected_documents"] == 271 and inventory["expected_pages"] == 14945
         and type(inventory["counts"]) is dict
         and all(integer(v) for v in inventory["counts"].values())
         and all(inventory["counts"][key] == value for key, value in EXPECTED.items()), "Original fixed FULL denominators differ")
    need(canonical(inventory["database_ref"]) == canonical(DATABASE_REF)
         and canonical(inventory["corpus_index_ref"]) == canonical(CORPUS_INDEX_REF), "Original FULL index/database authority differs")
    need(inventory["sql_integrity"] == [{"quick_check": "ok", "foreign_key_check": "EMPTY"}] * 2,
         "Producer completion lacks both original integrity results")
    for key in ("financial_acceptance", "family_seal", "pdf_absence_proved", "role_unit_period_or_value_permission_granted", "provider_or_reextraction_performed"):
        need(inventory[key] is False, "Original neutral authority boundary differs:" + key)
    need(inventory["stream_ref"] == {k: INPUTS["stream"][k] for k in ("sha256", "size_bytes")}
         and inventory["stream_path"] == INPUTS["stream"]["path"], "Completed stream reference differs")
    material = {k: v for k, v in inventory.items() if k not in {"errors", "sql_integrity", "inventory_id", "stream_path"}}
    need(inventory["inventory_id"] == "f36originalinventoryv1:" + digest(material), "Neutral inventory content ID differs")
    need(controlled["format_version"] == "F36_CONTROLLED_NEUTRAL_ORIGINAL_INVENTORY_RUN_V1"
         and controlled["status"] == "PASS_NEUTRAL_ORIGINAL_INVENTORY_NOT_FINANCIAL_OR_PDF_PROOF"
         and controlled["errors"] == [] and controlled["profile"] == "full271"
         and controlled["implementation_inputs_unchanged"] is True
         and canonical(controlled["inventory_result"]) == canonical(inventory), "Controlled completion/inner inventory binding differs")
    validate_historical_producer_ref(controlled.get("inventory_stream_ref"), INPUTS["stream"])
    validate_historical_producer_ref(controlled.get("inventory_receipt_ref"), INPUTS["inventory"])
    return inventory["counts"]


def grammar(columns):
    headers, value_kinds, issues = [], [], []
    for column in columns:
        value = column["column_exact"]
        if type(value) is not dict:
            issues.append("NON_OBJECT_COLUMN")
            continue
        paths = value.get("header_path_exact")
        if type(paths) is not list:
            issues.append("UNSUPPORTED_HEADER_PATH")
        else:
            headers.append({"column_ordinal": column["column_ordinal"],
                            "header_path_strings": [{"header_level_ordinal": i, "literal": text}
                                                    for i, text in enumerate(paths, 1) if type(text) is str],
                            "unsupported_header_members": [{"header_level_ordinal": i, "json_type": type(text).__name__, "one_lf_sha256": digest(text)}
                                                           for i, text in enumerate(paths, 1) if type(text) is not str]})
            if not all(type(p) is str for p in paths):
                issues.append("MIXED_HEADER_PATH_MEMBER_TYPES")
        kind = value.get("value_kind")
        if type(kind) is str:
            value_kinds.append(kind)
        else:
            issues.append("UNKNOWN_VALUE_KIND")
    raw_header_text = " ".join(s["literal"] for h in headers for s in h["header_path_strings"])
    text = normalized(raw_header_text)
    return {"columns": headers, "value_kind_counts": dict(Counter(value_kinds)), "issues": issues,
            "literal_date_tokens": re.findall(r"\b(?:[0-3]?\d/[01]?\d/(?:19|20)\d\d|(?:19|20)\d\d-[01]\d-[0-3]\d)\b", raw_header_text),
            "literal_rollforward_words": [p for p in ("dau ky", "cuoi ky", "tang trong ky", "giam trong ky", "opening", "closing") if " " + p + " " in " " + text + " "],
            "resolved_period_or_unit": None}


def literal_shape_issues(record):
    """Expose malformed literal axes without dropping their valid string members."""
    issues = []
    kind = record["record_type"]
    if kind == "column":
        value = record.get("column_exact")
        if type(value) is dict:
            paths = value.get("header_path_exact")
            if type(paths) is not list:
                issues.append({"field": "header_path_exact", "reason": "NOT_LIST", "json_type": type(paths).__name__, "one_lf_sha256": digest(paths)})
            else:
                issues.extend({"field": "header_path_exact", "member_ordinal": i, "reason": "NON_STRING_MEMBER", "json_type": type(text).__name__, "one_lf_sha256": digest(text)}
                              for i, text in enumerate(paths, 1) if type(text) is not str)
    elif record.get("original_json_type") == "dict" and kind in {"section", "table", "row"}:
        keys = {"section": ("content_kind", "statement_type", "title_exact"),
                "table": ("title_exact", "unit_exact", "continuation"),
                "row": ("row_kind", "label_exact", "hierarchy_path_exact")}[kind]
        for key in keys:
            value = field(record, key)["value"]
            if key == "hierarchy_path_exact" and type(value) is list:
                issues.extend({"field": key, "member_ordinal": i, "reason": "NON_STRING_MEMBER", "json_type": type(text).__name__, "one_lf_sha256": digest(text)}
                              for i, text in enumerate(value, 1) if type(text) is not str)
            elif value is not None and (type(value) is not str or key == "hierarchy_path_exact"):
                issues.append({"field": key, "reason": "UNSUPPORTED_LITERAL_FIELD_TYPE", "json_type": type(value).__name__, "one_lf_sha256": digest(value)})
    return [{"pointer": record["pointer"], "original_object_one_lf_sha256": record["original_object_one_lf_sha256"], **issue} for issue in issues]


def table_occurrences(table, plan):
    """Pure structural/literal candidates; caller writes no monetary coefficients."""
    sources = []
    for context, record, key in (("SECTION_TITLE", table["section"], "title_exact"), ("TABLE_TITLE", table["record"], "title_exact")):
        envelope = field(record, key) if record.get("original_json_type") == "dict" else {"present": False, "value": None}
        if type(envelope["value"]) is str:
            sources.append({"context": context, "pointer": record["pointer"], "field": key, "literal": envelope["value"],
                            "original_object_one_lf_sha256": record["original_object_one_lf_sha256"]})
    for column in table["columns"]:
        value = column["column_exact"]
        if type(value) is dict and type(value.get("header_path_exact")) is list:
            for ordinal, text in enumerate(value["header_path_exact"], 1):
                if type(text) is str:
                    sources.append({"context": "COLUMN_HEADER", "pointer": column["pointer"], "header_level_ordinal": ordinal, "literal": text,
                                    "original_object_one_lf_sha256": column["original_object_one_lf_sha256"]})
    for row in table["rows"]:
        if row["original_json_type"] != "dict":
            continue
        for key in ("label_exact", "hierarchy_path_exact"):
            envelope = field(row, key)
            value = envelope["value"]
            texts = [(1, value)] if type(value) is str else [(i, text) for i, text in enumerate(value, 1) if type(text) is str] if type(value) is list else []
            for ordinal, text in texts:
                sources.append({"context": "ROW_LABEL" if key == "label_exact" else "ROW_HIERARCHY", "pointer": row["pointer"],
                                "field": key, "path_ordinal": ordinal, "literal": text,
                                "original_object_one_lf_sha256": row["original_object_one_lf_sha256"]})
    hits = defaultdict(list)
    for source in sources:
        for family, aliases in plan.hits(source["literal"]).items():
            hits[family].append({**source, "alias_hits": aliases})
    headers = grammar(table["columns"])
    continuation = field(table["record"], "continuation") if table["record"]["original_json_type"] == "dict" else {"present": False, "value": None}
    for family, matches in sorted(hits.items()):
        owner = [m for m in matches if m["context"] in {"SECTION_TITLE", "TABLE_TITLE"}
                 and any(a["kind"] == "OWNER_ALIAS" and not a["generic_short_phrase"]
                         and not a.get("punctuation_only", False) for a in m["alias_hits"])]
        if plan.families[family]["owner_specificity_limit"].startswith("GENERIC_GEOGRAPHY"):
            owner = []
        competing = any(a["kind"] in {"RESET_ALIAS", "HARD_NEGATIVE_ALIAS"}
                        and not a.get("punctuation_only", False) for m in matches for a in m["alias_hits"])
        classification = "STRONG_OWNER_LITERAL_OCCURRENCE_NOT_OWNERSHIP_PROOF" if owner else "WEAK_GENERIC_COMPONENT_OR_ROW_OWNER_LITERAL_ONLY"
        if owner and competing:
            classification = "OWNER_AND_COMPETING_RESET_LITERALS_AMBIGUOUS"
        column_axis = {a["catalog_alias_ordinal"] for m in matches if m["context"] == "COLUMN_HEADER" for a in m["alias_hits"]
                       if a["kind"] == "MATRIX_AXIS_ALIAS" and not a.get("punctuation_only", False)}
        row_axis = {a["catalog_alias_ordinal"] for m in matches if m["context"] in {"ROW_LABEL", "ROW_HIERARCHY"} for a in m["alias_hits"]
                    if a["kind"] == "MATRIX_AXIS_ALIAS" and not a.get("punctuation_only", False)}
        meaningful_literals = any(not a.get("punctuation_only", False) for m in matches for a in m["alias_hits"])
        shapes = ["NO_LAYOUT_OR_AXIS_INFERENCE"]
        if meaningful_literals:
            shapes = ["FLAT_OR_MULTILEVEL_HEADER_TABLE_CANDIDATE"]
            if len(column_axis) >= 2:
                shapes.append("MATRIX_COLUMN_AXIS_LITERAL_CANDIDATE")
            if len(row_axis) >= 2:
                shapes.append("TRANSPOSE_OR_REPEATED_ROW_AXIS_LITERAL_CANDIDATE_UNPROVEN")
            if len(headers["literal_rollforward_words"]) >= 2:
                shapes.append("ROLLFORWARD_HEADER_WORDS_CANDIDATE_UNPROVEN")
        yield family, {"classification": classification, "label_hits": matches,
                       "header_grammar": headers, "shape_candidates": shapes,
                       "continuation_envelope": continuation, "continuation_propagated": False,
                       "blank_metadata": {"null_value_slot_count": sum(len(r.get("value_axis", {}).get("null_column_ordinals", [])) for r in table["rows"]),
                                          "raw_blank_strings_detectable": False, "numeric_zero_count": None},
                       "row_count": len(table["rows"]), "column_count": len(table["columns"]),
                       "unsupported_shape_records": table["unsupported"], "unsupported_literal_field_shapes": table["literal_issues"],
                       "financial_acceptance": False}


class Frontier:
    """Strict ordered ORIGINAL stream decoder; malformed input never becomes absence."""
    def __init__(self, plan, on_occurrence):
        self.plan, self.on_occurrence = plan, on_occurrence
        self.counts = Counter()
        self.document = self.page = self.section = self.table = None
        self.document_closed = True
        self.previous_physical = self.pages_in_document = self.sections_in_page = self.tables_in_section = 0
        self.seen_vids = set()
        self.statuses = Counter()
        self.page_axis = hashlib.sha256(b"[")
        self.page_axis_first = True
        self.family_documents = defaultdict(set)
        self.family_classifications = defaultdict(Counter)
        self.unsupported_documents = Counter()

    def finish_table(self):
        if self.table is None:
            return
        table = self.table
        for family, occurrence in table_occurrences(table, self.plan):
            axis = table["page"]["axis"]
            self.family_documents[family].add(axis["document_ordinal"])
            self.family_classifications[family][occurrence["classification"]] += 1
            self.on_occurrence(family, {"schema": "L3B_SOURCE_JSON_TABLE_LITERAL_OCCURRENCE_V1",
                "source_identity": {"document_ordinal": axis["document_ordinal"], "document_id": axis["document_id"],
                                    "source_logical_name": axis["source_logical_name"], "source_sha256": axis["source_sha256"],
                                    "page_json_version_id": axis["page_json_version_id"], "physical_page": axis["physical_page"],
                                    "selected_page_ordinal": axis["selected_page_ordinal"]},
                "table_pointer": table["record"]["pointer"], "section_id": table["record"]["section_id"],
                "table_id": table["record"]["table_id"], "original_table_one_lf_sha256": table["record"]["original_object_one_lf_sha256"],
                "page_original_object_one_lf_sha256": table["page"]["original_object_one_lf_sha256"],
                "original_source_proof": table["page"]["source_proof"], "bank": None,
                "occurrence_is_financial_acceptance": False, **occurrence})
        self.table = None

    def node_identity(self, record):
        need(self.page is not None and not self.document_closed, "Node outside an open original page")
        need(type(record.get("document_ordinal")) is int
             and record["document_ordinal"] == self.page["axis"]["document_ordinal"]
             and record.get("page_json_version_id") == self.page["axis"]["page_json_version_id"], "Node crossed document/source VID")
        need(type(record.get("pointer")) is str and type(record.get("original_json_type")) is str
             and type(record.get("original_object_one_lf_sha256")) is str
             and SHA.fullmatch(record["original_object_one_lf_sha256"]), "Node pointer/type/object hash missing")

    def add(self, record):
        need(type(record) is dict and record.get("record_type") in KINDS, "Unknown or untyped ORIGINAL record")
        kind = record["record_type"]
        self.counts[kind] += 1
        if kind == "document":
            self.finish_table()
            need(self.document_closed, "New document before exact prior frontier closure")
            index, source = record["index_document"], record["document"]
            need(type(index) is dict and type(source) is dict and type(index.get("source_ordinal")) is int
                 and index["source_ordinal"] == self.counts["document"]
                 and index["relative_path"] == source["source_logical_name"]
                 and index["source_sha256"] == source["source_sha256"]
                 and index["source_size_bytes"] == source["source_size_bytes"]
                 and integer(index["page_count"], 1) and type(index["page_status_counts"]) is dict
                 and set(index["page_status_counts"]) == set(PAGE_STATUSES)
                 and all(integer(n) for n in index["page_status_counts"].values())
                 and sum(index["page_status_counts"].values()) == index["page_count"]
                 and type(source["document_id"]) is str and SHA.fullmatch(source["source_sha256"])
                 and integer(source["source_size_bytes"], 1), "Original document/index/global ordinal/source identity differs")
            self.document, self.page, self.section = record, None, None
            self.document_closed = False
            self.pages_in_document = self.previous_physical = 0
            self.statuses = Counter()
            return
        need(self.document is not None and not self.document_closed, "Record outside open document")
        ordinal = self.document["index_document"]["source_ordinal"]
        if kind == "page":
            self.finish_table()
            axis, proof = record["axis"], record["source_proof"]
            source = self.document["document"]
            need(type(axis) is dict and type(proof) is dict and record["pointer"] == ""
                 and record["original_json_type"] == "dict" and SHA.fullmatch(record["original_object_one_lf_sha256"])
                 and type(axis["document_ordinal"]) is int and axis["document_ordinal"] == ordinal
                 and all(axis[k] == source[k] for k in ("document_id", "source_logical_name", "source_sha256"))
                 and integer(axis["selected_page_ordinal"], 1) and axis["selected_page_ordinal"] == self.pages_in_document + 1
                 and integer(axis["physical_page"], 1) and axis["physical_page"] > self.previous_physical
                 and type(axis["page_json_version_id"]) is str and axis["page_json_version_id"] not in self.seen_vids,
                 "Original selected page/global/source/version axis differs")
            need(all(canonical(proof[k]) == canonical(axis[k]) for k in ("page_json_version_id", "source_logical_name", "source_sha256", "physical_page"))
                 and integer(proof["stored_blob_size_bytes"], 1) and SHA.fullmatch(proof["stored_blob_two_lf_sha256"])
                 and type(proof["page_status"]) is str and proof["page_status"] in PAGE_STATUSES, "Original page/source proof differs")
            self.seen_vids.add(axis["page_json_version_id"])
            self.pages_in_document += 1
            self.previous_physical = axis["physical_page"]
            self.statuses[proof["page_status"]] += 1
            if not self.page_axis_first:
                self.page_axis.update(b",")
            self.page_axis_first = False
            self.page_axis.update(canonical(axis)[:-1])
            self.page, self.section = record, None
            self.sections_in_page = self.tables_in_section = 0
            return
        if kind == "document_frontier_verified":
            self.finish_table()
            need(type(record["document_ordinal"]) is int and record["document_ordinal"] == ordinal
                 and self.pages_in_document == self.document["index_document"]["page_count"]
                 and canonical(dict(self.statuses)) == canonical(record["page_status_counts"])
                 and canonical({status: self.statuses[status] for status in PAGE_STATUSES})
                 == canonical(self.document["index_document"]["page_status_counts"]), "Original document frontier/status denominator differs")
            need("registered_prompt_encoding_witness" in record, "Original frontier witness field missing")
            self.document_closed = True
            self.page = self.section = None
            return
        self.node_identity(record)
        pointer = record["pointer"]
        if kind == "unsupported_shape":
            need(pointer.startswith("/sections"), "Unsupported shape pointer outside ORIGINAL section tree")
            self.unsupported_documents[ordinal] += 1
            if self.table is not None and (pointer == self.table["record"]["pointer"] or pointer.startswith(self.table["record"]["pointer"] + "/")):
                self.table["unsupported"].append({k: record[k] for k in record if k not in {"document_ordinal", "page_json_version_id"}})
                self.table["metadata_bytes"] += len(canonical(record))
                need(self.table["metadata_bytes"] <= MAX_TABLE_METADATA, "Original table metadata exceeds bound; no truncation")
            return
        issues = literal_shape_issues(record)
        if issues:
            self.unsupported_documents[ordinal] += len(issues)
        match = POINTER.fullmatch(pointer)
        need(match is not None, "Malformed ORIGINAL positional pointer")
        section_number = int(match[1]) + 1
        if kind == "section":
            self.finish_table()
            need(match[2] is None and section_number == self.sections_in_page + 1
                 and type(record["section_ordinal"]) is int and record["section_ordinal"] == section_number, "Section positional frontier differs")
            if record["original_json_type"] == "dict":
                for key in ("content_kind", "statement_type", "title_exact"):
                    field(record, key)
            self.sections_in_page += 1
            self.section, self.tables_in_section = record, 0
            return
        need(self.section is not None and section_number == self.sections_in_page and match[2] is not None,
             "Table/row crossed original section ownership")
        table_number = int(match[2]) + 1
        if kind == "table":
            self.finish_table()
            need(match[3] is None and table_number == self.tables_in_section + 1
                 and record["section_id"] == f"s{section_number}" and record["table_id"] == f"t{table_number}", "Table positional frontier differs")
            if record["original_json_type"] == "dict":
                for key in ("title_exact", "unit_exact", "continuation"):
                    field(record, key)
            self.tables_in_section += 1
            self.table = {"record": record, "page": self.page, "section": self.section, "columns": [], "rows": [], "unsupported": [],
                          "literal_issues": literal_shape_issues(self.section) + issues, "metadata_bytes": len(canonical(record))}
            return
        need(self.table is not None and table_number == self.tables_in_section and match[3] is not None,
             "Column/row outside original table ownership")
        need(match[3] == ("columns" if kind == "column" else "rows"), "Node kind/pointer axis differs")
        items = self.table["columns" if kind == "column" else "rows"]
        order_key = "column_ordinal" if kind == "column" else "row_ordinal"
        need(type(record[order_key]) is int and record[order_key] == int(match[4]) + 1 == len(items) + 1,
             "Original row/column ordinal omitted, duplicated or reordered")
        if kind == "column":
            need(not self.table["rows"] and "column_exact" in record, "Original column after rows or exact metadata missing")
        else:
            if record["original_json_type"] == "dict":
                for key in ("row_kind", "label_exact", "hierarchy_path_exact"):
                    field(record, key)
            if "value_axis" in record:
                value = record["value_axis"]
                need(type(value) is dict and set(value) == {"count", "item_types", "null_column_ordinals", "items_one_lf_sha256"}
                     and integer(value["count"]) and type(value["item_types"]) is list
                     and type(value["items_one_lf_sha256"]) is list
                     and len(value["item_types"]) == len(value["items_one_lf_sha256"]) == value["count"]
                     and all(type(t) is str for t in value["item_types"])
                     and all(type(s) is str and SHA.fullmatch(s) for s in value["items_one_lf_sha256"])
                     and type(value["null_column_ordinals"]) is list
                     and all(integer(n, 1) and n <= value["count"] for n in value["null_column_ordinals"])
                     and value["null_column_ordinals"] == sorted(set(value["null_column_ordinals"]))
                     and value["null_column_ordinals"] == [n for n, t in enumerate(value["item_types"], 1) if t == "NoneType"],
                     "Original typed/null/value-hash axis differs; no coercion")
                self.counts["value_slots"] += value["count"]
        self.table["metadata_bytes"] += len(canonical(record))
        need(self.table["metadata_bytes"] <= MAX_TABLE_METADATA, "Original table metadata exceeds bound; no truncation")
        self.table["literal_issues"].extend(issues)
        items.append(record)

    def finish(self, expected_counts, expected_page_axis_sha256):
        self.finish_table()
        need(self.document_closed and self.counts["document_frontier_verified"] == self.counts["document"], "Unclosed original document frontier")
        need(dict(self.counts) == expected_counts, "Complete ORIGINAL record/value-slot denominator differs")
        self.page_axis.update(b"]\n")
        need(self.page_axis.hexdigest() == expected_page_axis_sha256, "Entire ordered original page axis differs")
        return {"counts": dict(self.counts), "ordered_selected_page_axis_one_lf_sha256": self.page_axis.hexdigest(),
                "selected_source_version_count": len(self.seen_vids), "source_versions_collapsed": False}


def stream_records(stream, reference, check_headroom):
    """Hash exact bytes while parsing once. No blank lines or unterminated tail."""
    value, size = hashlib.sha256(), 0
    while raw := stream.readline(MAX_LINE + 1):
        need(len(raw) <= MAX_LINE and raw.endswith(b"\n"), "Oversized/unterminated inventory line; retain failure")
        value.update(raw)
        size += len(raw)
        record = strict_json(raw)
        need(type(record) is dict and raw == canonical(record), "Inventory must retain exact canonical one-LF record bytes")
        if record.get("record_type") in {"document", "page"}:
            check_headroom()
        yield record
    need((value.hexdigest(), size) == (reference["sha256"], reference["size_bytes"]), "Entire parsed inventory raw hash/bytes differ")


def mem_available():
    raw = Path("/proc/meminfo").read_text(encoding="ascii")
    values = re.findall(r"^MemAvailable:\s+([0-9]+) kB$", raw, re.MULTILINE)
    need(len(values) == 1 and int(values[0]) * 1024 >= MIN_MEM, "MemAvailable below1.5GiB; no retry or cap increase")


def output_root(path):
    path = safe(path)
    roots = (Path("/home/bctc/codex-runs"), Path("/mnt/d/bctc_bank/restore-receipts/CODEX_L3B_CENSUS_20261026_V1"))
    need(any(path != r and path.is_relative_to(r) for r in roots)
         and path.parent.is_dir() and not os.path.lexists(path), "Fresh output under authorized CODEX/home prefix only")
    return path


def write_once(path, value):
    raw = canonical(value)
    with path.open("xb") as stream:
        need(stream.write(raw) == len(raw), "Incomplete exclusive output")
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--expected-helper-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--root-lease-id", required=True)
    args = parser.parse_args(argv)
    import resource
    need(sys.platform == "linux" and sys.version_info[:2] == (3, 12) and sys.flags.isolated
         and sys.dont_write_bytecode and not sys.flags.optimize, "Linux Python3.12 -I -B required")
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (300, 360))
    os.nice(19)
    need(os.getpriority(os.PRIO_PROCESS, 0) == 19, "Nice19 required")
    need(bool(args.root_lease_id.strip()) and len(args.root_lease_id) <= 256, "Root-owned serialized lease identifier required; text is not independent scheduler attestation")
    def stop(number, _frame):
        raise CensusError("TERMINATED_BY_SIGNAL:" + str(number) + "; no retry")
    for number in (signal.SIGTERM, signal.SIGINT, signal.SIGXCPU, signal.SIGALRM):
        signal.signal(number, stop)
    signal.alarm(600)
    mem_available()
    held, out, outputs = Held(), None, []
    started = time.monotonic()
    record = {"schema": "CODEX_L3B_SOURCE_JSON_LABEL_CENSUS_V1", "status": "FAIL", "errors": [],
              "classification": "SOURCE_JSON_LABEL_OCCURRENCES_NOT_PDF_VISIBLE_OR_ACCEPTANCE",
              "financial_acceptance": False, "family_terminal": False, "production_F41_unlocked": False,
              "database_pdf_or_provider_opened": False, "source_json_parse_passes_attempted": 0,
              "notes_join": {"status": "NOT_REQUESTED_NO_APPROVED_PINS", "counts": None},
              "bank_counts": None, "bank_identity_status": "BANK_IDENTITY_NOT_SUPPLIED",
              "root_lease_id": args.root_lease_id, "automatic_retry_permitted": False}
    try:
        own = safe(Path(__file__).absolute())
        need(SHA.fullmatch(args.expected_helper_sha256) is not None, "Reviewed helper SHA required")
        own_ref = {"path": str(own), "sha256": args.expected_helper_sha256, "size_bytes": own.stat().st_size}
        held.open(own_ref)
        catalog_ref = {"path": str(safe(args.catalog)), "sha256": CATALOG_SHA, "size_bytes": CATALOG_BYTES}
        catalog = held.read_json(catalog_ref, 1024**2)
        need(catalog["schema"] == "L3B_REGISTERED_LITERAL_CATALOG_V1"
             and [f["family_number"] for f in catalog["families"]] == list(range(41, 54)), "Pinned complete13-family catalog required")
        plan = LiteralPlan(catalog["families"])
        inventory = held.read_json(INPUTS["inventory"], 64 * 1024)
        controlled = held.read_json(INPUTS["controlled"], 2 * 1024**2)
        expected_counts = validate_completion(inventory, controlled)
        record["historical_producer_reference_metadata"] = {
            "inventory_stream_ref": validate_historical_producer_ref(controlled["inventory_stream_ref"], INPUTS["stream"]),
            "inventory_receipt_ref": validate_historical_producer_ref(controlled["inventory_receipt_ref"], INPUTS["inventory"]),
        }
        record["historical_identity_is_current_inode_authority"] = False
        input_fd = held.open(INPUTS["stream"])
        mem_available()
        out = output_root(args.out)
        os.umask(0o077)
        out.mkdir(mode=0o700)
        total_bytes = 0
        with ExitStack() as stack:
            streams = {n: stack.enter_context((out / f"F{n:02d}-source-json-label-occurrences.jsonl").open("xb")) for n in range(41, 54)}
            hashes = {n: hashlib.sha256() for n in streams}
            sizes = Counter()
            def emit(family, occurrence):
                nonlocal total_bytes
                raw = canonical(occurrence)
                need(total_bytes + len(raw) <= MAX_OUTPUT, "Output cap exceeded; no truncation")
                need(streams[family].write(raw) == len(raw), "Short occurrence write")
                total_bytes += len(raw)
                sizes[family] += len(raw)
                hashes[family].update(raw)
            frontier = Frontier(plan, emit)
            with os.fdopen(os.dup(input_fd), "rb") as source:
                source.seek(0)
                record["source_json_parse_passes_attempted"] = 1
                for item in stream_records(source, INPUTS["stream"], mem_available):
                    frontier.add(item)
            record["frontier"] = frontier.finish(expected_counts, inventory["ordered_selected_page_axis_one_lf_sha256"])
            for number, stream in streams.items():
                stream.flush()
                os.fsync(stream.fileno())
                outputs.append({"path": str(out / f"F{number:02d}-source-json-label-occurrences.jsonl"),
                                "sha256": hashes[number].hexdigest(), "size_bytes": sizes[number]})
        family_reports = []
        for number in range(41, 54):
            family = plan.families[number]
            report = {"family_number": number, "family_id": family["family_id"],
                "documents_with_literal_hits": sorted(frontier.family_documents[number]),
                "document_count_with_literal_hits": len(frontier.family_documents[number]),
                "table_occurrence_classifications": dict(frontier.family_classifications[number]),
                "bank_count": None, "accepted_financial_positions": None, "source_json_no_hit_is_pdf_absence": False,
                "no_hit_documents": sorted(set(range(1, 272)) - frontier.family_documents[number]),
                "no_hit_status": "NO_HIT_IN_INVENTORIED_TITLES_HEADERS_ROW_LABELS_HIERARCHIES_NOT_WHOLE_JSON_FAMILY_OR_PDF_ABSENCE",
                "inventoried_text_fields": ["section.title_exact", "table.title_exact", "column.header_path_exact", "row.label_exact", "row.hierarchy_path_exact"],
                "section_narratives_or_full_text_available": False,
                "documents_with_unsupported_original_shapes": dict(frontier.unsupported_documents),
                "no_hit_documents_with_unsupported_shapes": sorted(set(frontier.unsupported_documents) - frontier.family_documents[number]),
                "unsupported_source_status": "UNSUPPORTED_RAW_SHAPES_RETAINED_NOT_EMPTY_OR_NUMERIC_ZERO",
                "catalog_ref": catalog_ref, "dossier_ref": family["dossier_ref"], "occurrences_ref": outputs[number - 41],
                "notes_join_status": "NOT_REQUESTED_NO_APPROVED_PINS", "financial_acceptance": False}
            outputs.append(write_once(out / f"F{number:02d}-census-summary.json", report))
            family_reports.append({k: v for k, v in report.items() if k not in {"catalog_ref", "dossier_ref"}})
        held.validate()
        record.update(status="COMPLETE_SOURCE_JSON_LABEL_CENSUS_NOT_FINANCIAL_OR_PDF_PROOF", inputs_unchanged=True,
                      input_refs=INPUTS, helper_ref=own_ref, catalog_ref=catalog_ref,
                      family_reports=family_reports, output_refs=outputs, financial_accepted_count=None,
                      selected_version_identity_preserved=True, continuation_propagation_performed=False)
    except BaseException as error:
        record["errors"].append(type(error).__name__ + ": " + str(error))
    finally:
        signal.alarm(0)
        try:
            held.validate()
        except BaseException as error:
            record["errors"].append("FINAL_INPUT_BARRIER:" + str(error))
        finally:
            held.close()
        if record["errors"]:
            record["status"] = "FAIL"
            record["inputs_unchanged"] = False
        record["wall_seconds"] = round(time.monotonic() - started, 3)
        record["limits"] = {"as_bytes": list(resource.getrlimit(resource.RLIMIT_AS)), "cpu_seconds": list(resource.getrlimit(resource.RLIMIT_CPU)),
                            "nice": os.getpriority(os.PRIO_PROCESS, 0), "minimum_mem_available_bytes": MIN_MEM,
                            "wall_alarm_work_phase_seconds": 600, "requires_owner_outer_watchdog_for_cleanup": True}
        if out is not None:
            try:
                write_once(out / "CODEX_L3B_CENSUS_RECEIPT_V1.json", record)
            except BaseException as error:
                record["status"] = "FAIL"
                record["errors"].append("FINAL_RECEIPT_WRITE:" + str(error))
        print(json.dumps({"status": record["status"], "errors": record["errors"]}, ensure_ascii=False), flush=True)
    return 0 if record["status"] == "COMPLETE_SOURCE_JSON_LABEL_CENSUS_NOT_FINANCIAL_OR_PDF_PROOF" else 1


if __name__ == "__main__":
    raise SystemExit(main())
