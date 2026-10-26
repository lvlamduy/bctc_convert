#!/usr/bin/env python3
"""UNRUN V3 candidate: READY_FOR_PROFILE_BINDING, never old-proof promotion.

Approved scope: exchange0440. Source/census/trial structures are pinned5ea0499e.
SQLite input is read-only/immutable, its sweep BLOB is hashed incrementally.
Every original census row requires exactly one owner-reviewed category.
Every N/U document requires all physical PDF pages plus its exact runner reasons.
Missing immutable approved new-FULL profile stops before source/PDF work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import stat
import struct
import subprocess
import sys
import tempfile
import types
from collections import Counter, defaultdict
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime
from pathlib import Path

BASE_COMMIT = "5ea0499e8745366c8a9cc11246484fabde78ee6c"
FAMILY_ID = "INCOME_TAX"
# These are source-registered authority, never CLI/caller overrides. A later
# additive reviewed revision must bind the actual new FULL run and reader bytes.
APPROVED_RUN_PROFILE_REF = None
APPROVED_GATE_READER_REF = None
REJECTED_SWEEPS = {"2c472bd1009eb42d18080221ad22f6ba1344d6a19f3757f39d6d39d227a1aa2e"}
READY = "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
UNRESOLVED = "UNRESOLVED_GEMINI_JSON_FAMILY"
NOT_OBSERVED = "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
VISIBLE_FORMAT = "F39_ORIGINAL_CENSUS_PDF_VISIBLE_SOURCE_ROW_AUDIT_V3"
RESIDUAL_FORMAT = "F39_EXHAUSTIVE_PDF_NU_RESIDUAL_SPEC_V3"
VISIBLE_PREFIX = "f39pdfvisiblev3:"
RESIDUAL_PREFIX = "f39pdfresidualv3:"
SOURCE_PINS = {
    "scripts/experiments/run_gemini_json_income_tax_accounting_family_v1.py": "f94b6c6b732cf259eed04b6a07ca57124f2ae84076111c5429b6e81f2af462fe",
    "src/bctc_ai/evaluation/gemini_json_income_tax_family_v1.py": "370236b18345bea95315e9e41492ea4306dce35b5da0a2fb7dad6b54cdf26d88",
    "src/bctc_ai/evaluation/gemini_json_income_tax_source_label_discrepancy_v1.py": "96f72e7343e20b888414bd1ff9fb62719acf85d6743a27c4e5ba2e0e9aa879f4",
    "config/families/tm-income-tax-source-label-discrepancies-v1.json": "c8788461c2e3aed5068c9ba3c329f39bfd13d2cf8dea7aede724bbff6b017bcf",
    "src/bctc_ai/storage/gemini_income_tax_raw_money_census_v1.py": "483e635fb3d01e819c2c87cf649ef84f4917dc654c89cbd227cd6ced602213bd",
    "src/bctc_ai/storage/gemini_accounting_family_store_v1.py": "6c6638bde3a1eea25c5382321a0a256323ea737bd691014c6e04d2308c8e8a17",
    "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py": "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2",
    "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py": "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5",
}
LOCATOR_KEYS = (
    "document_id", "document_ordinal", "source_logical_name", "source_sha256",
    "page_json_version_id", "physical_page", "selected_page_ordinal", "section_id", "table_id",
)
CATEGORIES = {
    "ACCEPTED_MAPPING_SOURCE",
    "STRUCTURAL_NO_MONEY_OR_UNKNOWN_COLUMNS",
    "SOURCE_ONLY_OUTSIDE_F39_SCHEMA",
    "RETAINED_ALGORITHM_HOLD",
    "RETAINED_SOURCE_AMBIGUITY",
    "RETAINED_SOURCE_CONFLICT",
    "RETAINED_ILLEGIBLE_OR_MISSING_PRINTED_INFORMATION",
    "RETAINED_SOURCE_TRANSCRIPTION_DISCREPANCY",
}
RESIDUAL_DISPOSITIONS = {
    "ALGORITHM_UNSUPPORTED_SOURCE_LAYOUT",
    "SOURCE_PERIOD_OR_ROLE_AUTHORITY_INCOMPLETE",
    "GENUINE_SOURCE_AMBIGUITY",
    "GENUINE_SOURCE_CONFLICT",
    "SOURCE_ONLY_NO_SCHEMA_MAPPABLE_F39_ROW",
    "NOT_OBSERVED_AFTER_FULL_PDF_REVIEW",
    "ILLEGIBLE_OR_MISSING_PRINTED_INFORMATION",
    "RETAINED_REGISTERED_SOURCE_TRANSCRIPTION_DISCREPANCY",
    "RETAINED_ALGORITHM_ROLE_UNPROVEN",
}
RETAINED_HOLD_RULES = {
    "110": {"reason": "SOURCE_TRANSCRIPTION_DISCREPANCY",
            "residual_disposition": "RETAINED_REGISTERED_SOURCE_TRANSCRIPTION_DISCREPANCY"},
    "225": {"reason": "ALGORITHM_CURRENT_TAX_PARENT_PAYABLE_SUBTOTAL_ROLE_UNPROVEN",
            "residual_disposition": "RETAINED_ALGORITHM_ROLE_UNPROVEN"},
}
NEGATIVE_ROW_FINDING = "REGISTERED_5EA_F39_SOURCE_LABEL_SUBSTITUTION_HOLD"
NEGATIVE_SOURCE_SHA256 = "82d67a1543618eb9b59e1cdc819049e54dcc35eeace90a5b745d77f03ed8940f"
NEGATIVE_VID = "gfpstorev1:json:860d1b7f024750929d3880fa06c13f62b1c074baecb463847a07a0bd5b8dbb7a"
RENDER_CONTRACT = {
    "renderer": "pdftoppm", "format": "PNG", "resolution_dpi": 72,
    "color": "RGB", "alpha": False, "single_page": True,
    "arguments": ["-f", "PAGE", "-l", "PAGE", "-r", "72", "-singlefile", "-png", "PDF", "PREFIX"],
}
MAX_JSON = 64 * 1024 * 1024
MAX_DOCUMENT_BLOB = 128 * 1024 * 1024
MAX_PDF_PAGES = 5000
CHUNK = 1024 * 1024


class F39AuditError(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise F39AuditError(message)


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(F39AuditError("Nonfinite JSON token")))


def same(left, right):
    return canonical(left) == canonical(right)


def safe(path):
    path = Path(path)
    need(path.is_absolute() and ".." not in path.parts, "Explicit absolute path without '..' required")
    for item in (path, *path.parents):
        need(not item.is_symlink(), "Symlink path prohibited: " + str(item))
    return path


def identity(stat):
    return tuple(getattr(stat, key) for key in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns"))


def stream_hash(stream):
    stream.seek(0)
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(CHUNK), b""):
        value.update(block)
    stream.seek(0)
    return value.hexdigest()


@contextmanager
def pinned_file(path, expected=None):
    path = safe(path)
    need(path.is_file(), "Regular existing input file required: " + str(path))
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode), "Nonregular input prohibited")
        need(identity(before) == identity(path.stat()), "File identity differs before read")
        reference = {"path": str(path), "sha256": stream_hash(stream), "size_bytes": before.st_size}
        if expected is not None:
            need(reference["sha256"] == expected["sha256"] and reference["size_bytes"] == expected["size_bytes"],
                 "Pinned file bytes differ: " + str(path))
            if "path" in expected:
                need(Path(expected["path"]) == path, "Pinned absolute input path differs")
        try:
            yield stream, reference
        finally:
            need(identity(before) == identity(os.fstat(stream.fileno())) == identity(path.stat()),
                 "Held-file identity changed: " + str(path))
            need(stream_hash(stream) == reference["sha256"], "Held-file bytes changed: " + str(path))


def small_json(stream, limit=MAX_JSON):
    stream.seek(0)
    raw = stream.read(limit + 1)
    need(len(raw) <= limit, "Bounded JSON input exceeds reviewed limit")
    stream.seek(0)
    return parse(raw)


def file_json(path):
    with pinned_file(path) as (stream, reference):
        return small_json(stream), reference


def reference_shape_v3(reference, *, path_required=True):
    fields = {"sha256", "size_bytes"} | ({"path"} if path_required else set())
    need(type(reference) is dict and set(reference) == fields, "Exact immutable reference fields required")
    need(type(reference["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", reference["sha256"])
         and type(reference["size_bytes"]) is int and reference["size_bytes"] > 0, "Reference hash/bytes invalid")
    if path_required:
        need(type(reference["path"]) is str, "Reference path must be text")
        safe(reference["path"])


def approved_profile_reference_v3():
    need(APPROVED_RUN_PROFILE_REF is not None,
         "READY_FOR_PROFILE_BINDING: missing source-registered immutable new FULL run profile")
    reference_shape_v3(APPROVED_RUN_PROFILE_REF)
    return parse(canonical(APPROVED_RUN_PROFILE_REF))


def validate_run_profile_contract_v3(profile):
    fields = {"format_version", "reviewed_and_approved", "resolved", "expected_head", "family_id",
              "family_run_id", "sweep_id", "expected_refs", "metrics", "selected_page_count",
              "full_run_receipt_ref", "full_run_receipt_bindings", "synthetic_gate_receipt_ref",
              "gate_reader_ref", "negative_admission_axis_sha256", "retained_hold_bindings"}
    need(type(profile) is dict and set(profile) == fields, "Exact new FULL run profile required")
    need(profile["format_version"] == "F39_CLOSEOUT_5EA_APPROVED_FULL_RUN_PROFILE_V3"
         and profile["reviewed_and_approved"] is True and profile["resolved"] is True,
         "Run profile is unreviewed, pending or unresolved")
    need(profile["expected_head"] == BASE_COMMIT and profile["family_id"] == FAMILY_ID,
         "Run profile belongs to different code/family; no old-proof upgrade")
    need(type(profile["family_run_id"]) is str and profile["family_run_id"].startswith("gjfafstorev1:run:")
         and type(profile["sweep_id"]) is str and bool(profile["sweep_id"]), "Run/sweep identity missing")
    refs = profile["expected_refs"]
    need(type(refs) is dict and set(refs) == {"sweep", "audit", "results", "corpus_index"}, "Whole new run-reference axis required")
    for name, reference in refs.items():
        reference_shape_v3(reference, path_required=name == "corpus_index")
    need(refs["sweep"]["sha256"] not in REJECTED_SWEEPS, "Rejected 11380 sweep cannot be promoted or reassigned")
    metrics = profile["metrics"]
    need(type(metrics) is dict and set(metrics) == {"document_count", "ready_count", "not_observed_count", "unresolved_count", "mapping_count"}
         and all(type(value) is int and value >= 0 for value in metrics.values())
         and metrics["document_count"] == 271
         and metrics["ready_count"] + metrics["not_observed_count"] + metrics["unresolved_count"] == 271,
         "Complete authoritative FULL metrics required; no guessed/subset denominator")
    need(type(profile["selected_page_count"]) is int and profile["selected_page_count"] == 14945,
         "Complete unchanged FULL selected-page frontier required")
    for key in ("full_run_receipt_ref", "synthetic_gate_receipt_ref", "gate_reader_ref"):
        reference_shape_v3(profile[key])
    bindings = profile["full_run_receipt_bindings"]
    need(type(bindings) is dict and set(bindings) == {"head", "run_id", "sweep_sha256", "audit_sha256", "results_sha256", "exit_status"},
         "Complete new FULL receipt code/run/artifact/success bindings required")
    for pointer in bindings.values():
        need(type(pointer) is list and 0 < len(pointer) <= 16
             and all((type(item) is str and bool(item)) or (type(item) is int and item >= 0) for item in pointer),
             "Owner-reviewed exact JSON pointer tokens required, no guessed receipt fields")
    need(type(profile["negative_admission_axis_sha256"]) is str
         and re.fullmatch(r"[0-9a-f]{64}", profile["negative_admission_axis_sha256"]), "Whole warm negative admission digest required")
    holds = profile["retained_hold_bindings"]
    need(type(holds) is dict and set(holds) == set(RETAINED_HOLD_RULES), "Both retained source/algorithm HOLD bindings required")
    for ordinal, binding in holds.items():
        need(type(binding) is dict and set(binding) == {"index_document_sha256", "trial_reasons"}
             and type(binding["index_document_sha256"]) is str
             and re.fullmatch(r"[0-9a-f]{64}", binding["index_document_sha256"])
             and type(binding["trial_reasons"]) is list
             and RETAINED_HOLD_RULES[ordinal]["reason"] in binding["trial_reasons"], "Retained HOLD authority/reasons incomplete")
    return parse(canonical(profile))


def _json_pointer_v3(value, tokens):
    for token in tokens:
        need((type(value) is dict and type(token) is str and token in value)
             or (type(value) is list and type(token) is int and 0 <= token < len(value)),
             "Reviewed full-run receipt pointer is absent or changes type")
        value = value[token]
    return value


def validate_full_run_receipt_bindings_v3(profile, proof):
    expected = {"head": BASE_COMMIT, "run_id": profile["family_run_id"], "exit_status": 0,
                **{name + "_sha256": profile["expected_refs"][name]["sha256"] for name in ("sweep", "audit", "results")}}
    for name, wanted in expected.items():
        need(same(_json_pointer_v3(proof, profile["full_run_receipt_bindings"][name]), wanted),
             "New FULL completion receipt does not bind exact code/run/artifact/success: " + name)


def read_approved_run_profile_v3(*, guards, repo):
    reference = approved_profile_reference_v3()
    stream, actual = guards.enter_context(pinned_file(reference["path"], reference))
    profile = validate_run_profile_contract_v3(small_json(stream, 1024 * 1024))
    proof_stream, _ = guards.enter_context(pinned_file(profile["full_run_receipt_ref"]["path"], profile["full_run_receipt_ref"]))
    proof = small_json(proof_stream, 4 * 1024 * 1024)
    validate_full_run_receipt_bindings_v3(profile, proof)
    need(APPROVED_GATE_READER_REF is not None and same(profile["gate_reader_ref"], APPROVED_GATE_READER_REF),
         "Missing or unreviewed independent synthetic gate reader")
    reader_stream, reader_ref = guards.enter_context(pinned_file(profile["gate_reader_ref"]["path"], profile["gate_reader_ref"]))
    guards.enter_context(pinned_file(profile["synthetic_gate_receipt_ref"]["path"], profile["synthetic_gate_receipt_ref"]))
    reader = types.ModuleType("_reviewed_f39_synthetic_gate_reader_v3")
    reader.__file__, reader.__package__ = reader_ref["path"], ""
    sys.modules[reader.__name__] = reader
    raw = reader_stream.read(1024 * 1024 + 1)
    need(len(raw) <= 1024 * 1024, "Gate reader exceeds reviewed metadata bound")
    exec(compile(raw, reader_ref["path"], "exec"), reader.__dict__)
    gate = reader.validate_f39_synthetic_gate_v1(
        repo=Path(repo), receipt_ref=profile["synthetic_gate_receipt_ref"], expected_head=BASE_COMMIT)
    need(type(gate) is dict and gate.get("status") == "VERIFIED_53B_SOURCE_EQUIVALENT_TO_5EA",
         "Complete reviewed synthetic gate and source equivalence required")
    return profile, actual, gate


def checked_source_receipt_v3(value, prefix):
    """Exact T5 source protocol at5ea contracts433-451: final LF, no fallback.

    Kept separate from the audit content-ID helper so changing an audit codec
    cannot silently change the producer's source-receipt hash grammar.
    """
    need(type(value) is dict and type(value.get("receipt_id")) is str, "Source receipt object required")
    material = {key: item for key, item in value.items() if key != "receipt_id"}
    raw = (json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    need(value["receipt_id"] == prefix + hashlib.sha256(raw).hexdigest(), "Exact production source receipt content ID differs")
    return material


def validate_negative_admission_axis_v3(audit, index, profile):
    axis = audit.get("registered_source_label_discrepancy_admission_axis")
    need(type(axis) is list and len(axis) == 271 and all(type(entry) is list for entry in axis),
         "Complete ordered per-document warm negative admission axis required, including empty slots")
    need(digest(axis) == profile["negative_admission_axis_sha256"], "Warm negative admission axis differs from approved new FULL profile")
    need(len(index["documents"]) == 271, "Admission/index document frontier differs")
    for ordinal, entries in enumerate(axis, 1):
        document = index["documents"][ordinal - 1]
        for receipt in entries:
            need(type(receipt) is dict, "Negative pixel admission receipt must be an object")
            material = checked_source_receipt_v3(receipt, "gjitflabelv1:pdf-auth:")
            source, observation = material["source_pdf"], material["source_observation_receipt"]
            checked_source_receipt_v3(observation, "gjitflabelv1:source:")
            need(material["status"] == "PASS_FRESH_PDF_PIXELS_REGISTERED_MANUAL_NEGATIVE_REVIEW_NOT_FINANCIAL_ACCEPTANCE"
                 and material["text_layer_claimed"] is False and material["source_values_changed"] is False,
                 "Warm negative source admission boundary differs")
            need(source["source_sha256"] == document["source_sha256"]
                 and source["source_logical_name"] == document["relative_path"]
                 and source["source_size_bytes"] == document["source_size_bytes"]
                 and observation["source_locator"]["document_ordinal"] == ordinal
                 and observation["source_locator"]["source_sha256"] == source["source_sha256"],
                 "Warm negative receipt is detached from its original ordered source document")
    need(bool(axis[109]), "Registered doc110 negative pixel authority cannot be absent")
    return parse(canonical(axis))


def bind_cold_replay_v3(factory, *, negative_admission_axis, **options):
    need(type(negative_admission_axis) is list and len(negative_admission_axis) == 271
         and all(type(entry) is list for entry in negative_admission_axis), "Never compact, omit or default the complete warm negative axis")
    need("expected_source_label_discrepancy_axis" not in options, "Duplicate cold negative admission argument")
    return factory(**options, expected_source_label_discrepancy_axis=parse(canonical(negative_admission_axis)))


def validate_retained_hold_trial_v3(profile, summary, document):
    ordinal = str(summary["document_ordinal"])
    if ordinal not in RETAINED_HOLD_RULES:
        return
    binding = profile["retained_hold_bindings"][ordinal]
    need(digest(document) == binding["index_document_sha256"]
         and summary["status"] == UNRESOLVED and summary["mapping_count"] == 0
         and summary["selected_candidate_id"] is None
         and same(summary["reasons"], binding["trial_reasons"]),
         "Required source-bound110/225 HOLD is absent, changed, accepted or has mappings")


def write_once(path, payload):
    path = safe(path)
    with path.open("xb") as stream:
        need(stream.write(payload) == len(payload), "Incomplete exclusive write")
        stream.flush()
        os.fsync(stream.fileno())


def seal(material, key, prefix):
    need(key not in material, "ID field already exists")
    return {**material, key: prefix + digest(material)}


def checked_seal(value, key, prefix):
    need(type(value) is dict and type(value.get(key)) is str, "Sealed audit object required")
    material = {k: v for k, v in value.items() if k != key}
    need(value[key] == prefix + digest(material), "Audit content ID differs")
    return material


def review_is_complete(review, *, allow_known_unprinted=False, row_counterpart_required=True):
    need(type(review) is dict, "Owner review object required")
    for key in ("reviewer", "reviewed_at_utc", "evidence"):
        need(type(review.get(key)) is str and review[key].strip() and review[key] != "PENDING", "Owner review incomplete: " + key)
    need(len(review["evidence"].strip()) >= 24, "Concrete owner source-review evidence required")
    parsed = datetime.fromisoformat(review["reviewed_at_utc"].replace("Z", "+00:00"))
    need(parsed.tzinfo is not None, "Review timestamp must include timezone")
    need(review.get("all_listed_source_rows_or_pages_reviewed") is True, "Explicit complete review required")
    if allow_known_unprinted:
        need(review.get("printed_counterpart_verified") is False
             and review.get("printed_label_discrepancy_documented") is True,
             "Known unprinted-label finding must retain the negative printed-counterpart result")
    elif row_counterpart_required:
        need(review.get("printed_counterpart_verified") is True, "Printed row counterpart must be reviewed")
    need(review.get("raw_sign_unit_blank_preserved") is True, "Original sign/unit/blank preservation must be reviewed")


def pending_review():
    return {
        "reviewer": "PENDING", "reviewed_at_utc": "PENDING", "evidence": "PENDING",
        "all_listed_source_rows_or_pages_reviewed": False, "printed_counterpart_verified": False,
        "raw_sign_unit_blank_preserved": False, "mapping_role_period_population_checked": False,
        "printed_label_discrepancy_documented": False, "mapping_semantics_approved": False,
    }


def known_findings_for_row(row):
    locator = row["locator"]
    if (row["document_ordinal"] == 110 and locator["source_sha256"] == NEGATIVE_SOURCE_SHA256
            and locator["page_json_version_id"] == NEGATIVE_VID
            and locator["physical_page"] == 6 and locator["section_id"] == "s1"
            and locator["table_id"] == "t1" and row["original_row_ordinal"] == 17):
        return [NEGATIVE_ROW_FINDING]
    return []


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, timeout=30).stdout.strip()


class Inputs:
    def __init__(self, *, repo, run_dir, source_pdf_root, expected_refs):
        self.repo, self.run_dir, self.pdf_root = map(safe, (repo, run_dir, source_pdf_root))
        self.expected = parse(canonical(expected_refs))
        self.stack = ExitStack()
        self.pdf_files = {}
        self.run_refs = {}

    def __enter__(self):
        try:
            need(sys.version_info[:2] == (3, 12) and sys.dont_write_bytecode, "Python3.12 -B required")
            _adapter_stream, self.adapter_ref = self.stack.enter_context(pinned_file(Path(__file__).absolute()))
            self.profile, self.profile_ref, self.synthetic_gate = read_approved_run_profile_v3(guards=self.stack, repo=self.repo)
            self.run_id = self.profile["family_run_id"]
            expected = self.profile["expected_refs"]
            need(set(self.expected) == set(expected), "Exact expected run-reference fields required")
            for name, pinned in expected.items():
                supplied = self.expected[name]
                need(type(supplied) is dict and set(supplied) <= {"path", "sha256", "size_bytes"}
                     and set(supplied) >= {"sha256", "size_bytes"}, "Malformed expected reference")
                need(supplied["sha256"] == pinned["sha256"] and supplied["size_bytes"] == pinned["size_bytes"],
                     "Changed run/code requires a new reviewed adapter and receipts")
            need("path" in self.expected["corpus_index"], "Explicit corpus-index path required")
            need(same(self.expected["corpus_index"], expected["corpus_index"]), "Exact approved new FULL index reference required")
            need(_git(self.repo, "rev-parse", "HEAD") == BASE_COMMIT and not _git(self.repo, "status", "--porcelain", "--untracked-files=all"),
                 "Clean exact F39 clone required")
            for relative, sha in SOURCE_PINS.items():
                stream, actual = self.stack.enter_context(pinned_file(self.repo / relative))
                need(actual["sha256"] == sha, "Pinned F39/frozen source differs: " + relative)
            names = {"sweep": "income-tax-sweep.json", "audit": "income-tax-audit.json", "results": "results.sqlite3"}
            self.streams = {}
            for name in expected:
                path = Path(self.expected[name]["path"]) if name == "corpus_index" else self.run_dir / names[name]
                stream, reference = self.stack.enter_context(pinned_file(path, self.expected[name]))
                self.streams[name], self.run_refs[name] = stream, reference
            self.index = small_json(self.streams["corpus_index"], 1024 * 1024)
            self.audit = small_json(self.streams["audit"])
            need(type(self.index) is dict and type(self.audit) is dict, "Index/audit objects required")
            need(self.audit["family_id"] == FAMILY_ID and self.audit["family_run_id"] == self.run_id
                 and self.audit["run_kind"] == "EXPERIMENTAL" and self.audit["terminal_or_final_acceptance_claimed"] is False
                 and self.audit["provider_calls_performed"] is False
                 and self.audit["cold_source_replay"] == "PASS_EXACT_INDEPENDENT_STORAGE_QUERY_NO_CACHE"
                 and self.audit["results_reload"] == "PASS_EXACT",
                 "Existing run identity/acceptance boundary differs")
            documents = self.index["documents"]
            need(len(documents) == 271 and [d["source_ordinal"] for d in documents] == list(range(1, 272)),
                 "Complete original FULL271 source axis required")
            need(self.index["summary"]["page_count"] == 14945, "Complete original selected-page denominator required")
            self.negative_admission_axis = validate_negative_admission_axis_v3(self.audit, self.index, self.profile)
            for document in documents:
                logical = Path(document["relative_path"])
                years = [int(x) for x in logical.parts if x.isdigit() and len(x) == 4]
                need(not logical.is_absolute() and ".." not in logical.parts and len(years) == 1
                     and 2025 <= years[0] <= datetime.now(UTC).year, "Out-of-scope or unsafe source PDF")
            database = self.run_dir / "results.sqlite3"
            need(not any(Path(str(database) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")),
                 "Unclosed SQLite sidecar exists")
            self.db = sqlite3.connect(database.as_uri() + "?mode=ro&immutable=1", uri=True)
            self.stack.callback(self.db.close)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA query_only=ON")
            self.db.execute("PRAGMA trusted_schema=OFF")
            need(self.db.execute("PRAGMA query_only").fetchone()[0] == 1, "Query-only connection required")
            need(self.db.execute("SELECT COUNT(*) FROM family_run").fetchone()[0] == 1, "Single pinned original run required")
            run = self.db.execute(
                "SELECT rowid,family_run_id,sweep_id,family_id,corpus_manifest_index_id,corpus_index_sha256,"
                "implementation_refs_json,sweep_sha256,length(sweep_bytes) AS size,document_count,ready_count,"
                "not_observed_count,unresolved_count,mapping_count FROM family_run"
            ).fetchone()
            need(run["family_run_id"] == self.run_id and run["family_id"] == FAMILY_ID
                 and run["corpus_manifest_index_id"] == self.index["corpus_manifest_index_id"]
                 and run["corpus_index_sha256"] == self.run_refs["corpus_index"]["sha256"], "Store/index run binding differs")
            need(all(run[key] == value for key, value in self.profile["metrics"].items()), "Approved new FULL run metrics differ")
            need(run["size"] == self.expected["sweep"]["size_bytes"] and run["sweep_sha256"] == self.expected["sweep"]["sha256"],
                 "Stored sweep file reference differs")
            with self.db.blobopen("family_run", "sweep_bytes", run["rowid"], readonly=True) as blob:
                need(stream_hash(blob) == run["sweep_sha256"], "Incrementally hashed stored sweep differs")
            need(same(parse(bytes(run["implementation_refs_json"])), self.audit["implementation_refs"]), "Stored producer code refs differ")
            for relative, sha in SOURCE_PINS.items():
                matching = [ref for ref in self.audit["implementation_refs"]
                            if Path(ref["path"]).as_posix().endswith("/" + relative)]
                need(len(matching) == 1 and matching[0]["sha256"] == sha,
                     "New FULL audit does not bind exact5ea producer/registry: " + relative)
            self.sweep_id = run["sweep_id"]
            need(self.audit["sweep_id"] == self.sweep_id == self.profile["sweep_id"], "Audit/store/approved sweep ID differs")
            self.census_descriptors = self.audit["original_raw_money_census"]["document_census_refs"]
            need(len(self.census_descriptors) == 271
                 and [d["document_ordinal"] for d in self.census_descriptors] == list(range(1, 272))
                 and [d["corpus_document_ordinal"] for d in self.census_descriptors] == list(range(1, 272)),
                 "Complete original raw-census descriptor axis required")
            need(self.db.execute("SELECT COUNT(*) FROM f39_raw_money_census_v1 WHERE family_run_id=?", (self.run_id,)).fetchone()[0] == 271,
                 "Raw-census SQL denominator differs")
            need(self.db.execute("SELECT COUNT(*) FROM family_trial WHERE family_run_id=?", (self.run_id,)).fetchone()[0] == 271,
                 "Trial SQL denominator differs")
            self.tools = {}
            for name in ("pdfinfo", "pdftoppm"):
                stream, reference = self.stack.enter_context(pinned_file(Path("/usr/bin") / name))
                version = subprocess.run([reference["path"], "-v"], check=True, capture_output=True, text=True, timeout=30)
                self.tools[name] = {**reference, "version_first_line": (version.stdout + version.stderr).splitlines()[0]}
            self.render_contract = {**RENDER_CONTRACT, "tool_refs": self.tools}
            return self
        except BaseException:
            self.stack.close()
            raise

    def __exit__(self, kind, value, trace):
        database = self.run_dir / "results.sqlite3"
        if any(Path(str(database) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")):
            self.stack.close()
            raise F39AuditError("SQLite sidecar appeared during read-only audit")
        return self.stack.__exit__(kind, value, trace)

    def pdf(self, ordinal):
        if ordinal not in self.pdf_files:
            document = self.index["documents"][ordinal - 1]
            expected = {"sha256": document["source_sha256"], "size_bytes": document["source_size_bytes"]}
            stream, reference = self.stack.enter_context(pinned_file(self.pdf_root / document["relative_path"], expected))
            self.pdf_files[ordinal] = (stream, reference)
        return self.pdf_files[ordinal][1]

    def pdf_pages(self, ordinal):
        reference = self.pdf(ordinal)
        result = subprocess.run([self.tools["pdfinfo"]["path"], "-enc", "UTF-8", reference["path"]],
                                check=True, capture_output=True, text=True, timeout=60)
        matches = re.findall(r"^Pages:\s+([0-9]+)\s*$", result.stdout, flags=re.MULTILINE)
        need(len(matches) == 1 and 0 < int(matches[0]) <= MAX_PDF_PAGES, "Unsupported/ambiguous PDF page count")
        return int(matches[0])

    def render(self, ordinal, page, destination):
        reference = self.pdf(ordinal)
        destination = safe(destination)
        need(not destination.exists() and destination.suffix == ".png", "Fresh page PNG required")
        prefix = destination.with_suffix("")
        result = subprocess.run([
            self.tools["pdftoppm"]["path"], "-f", str(page), "-l", str(page),
            "-r", "72", "-singlefile", "-png", reference["path"], str(prefix),
        ], capture_output=True, timeout=120)
        need(result.returncode == 0 and destination.is_file(), "PDF page render failed; retain output, no retry")
        with pinned_file(destination) as (stream, png):
            header = stream.read(26)
            need(len(header) == 26 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR", "PNG header differs")
            width, height = struct.unpack(">II", header[16:24])
            need(header[24] == 8 and header[25] == 2 and width > 0 and height > 0, "Expected8-bit RGB PNG without alpha")
        return {"render_sha256": png["sha256"], "pixel_width": width, "pixel_height": height, "png_ref": png}

    def documents(self):
        for ordinal, document in enumerate(self.index["documents"], 1):
            descriptor = self.census_descriptors[ordinal - 1]
            metadata = self.db.execute(
                "SELECT corpus_document_ordinal,census_id,census_sha256,length(census_bytes) AS size "
                "FROM f39_raw_money_census_v1 WHERE family_run_id=? AND document_ordinal=?", (self.run_id, ordinal)
            ).fetchone()
            need(metadata is not None and metadata["size"] <= MAX_DOCUMENT_BLOB, "Missing/oversized document census")
            record = self.db.execute(
                "SELECT census_bytes,source_ref_json FROM f39_raw_money_census_v1 WHERE family_run_id=? AND document_ordinal=?",
                (self.run_id, ordinal),
            ).fetchone()
            raw = bytes(record["census_bytes"])
            need(hashlib.sha256(raw).hexdigest() == metadata["census_sha256"] == descriptor["census_ref"]["sha256"]
                 and len(raw) == descriptor["census_ref"]["size_bytes"], "Census SQL/audit bytes differ")
            need(same(parse(bytes(record["source_ref_json"])), descriptor["census_ref"]), "Retained original census-ref metadata differs")
            census = parse(raw)
            need(raw == canonical(census), "Original census serialization differs")
            material = {k: v for k, v in census.items() if k != "census_id"}
            need(census["census_id"] == metadata["census_id"] == descriptor["census_id"] == "f39rawcellv1:census:" + digest(material),
                 "Original census content ID differs")
            need(census["format_version"] == "F39_AUTHENTICATED_ORIGINAL_RAW_MONEY_CELL_CENSUS_V1"
                 and census["family_acceptance_claimed"] is False and census["source_values_modified"] is False
                 and census["dispositions_classified"] is False and census["pdf_bytes_or_visuals_verified"] is False,
                 "Original census boundary differs")
            binding = census["source_binding"]
            source = binding["document_source_axis"]
            need(binding["run_document_ordinal"] == binding["corpus_document_ordinal"] == metadata["corpus_document_ordinal"] == ordinal
                 and same(binding["index_document"], document)
                 and source["source_logical_name"] == document["relative_path"]
                 and source["source_sha256"] == document["source_sha256"]
                 and source["source_size_bytes"] == document["source_size_bytes"]
                 and binding["corpus_manifest_index_id"] == self.index["corpus_manifest_index_id"]
                 and same(binding["database_ref"], self.index["database_ref"]), "Original census/source/index binding differs")
            need(same(census["counts"], descriptor["counts"]), "Original census count metadata differs")
            pages = census["pages"]
            need(len(pages) == document["page_count"] and [p["locator"]["physical_page"] for p in pages] == list(range(1, len(pages) + 1)),
                 "Complete selected original page axis required")
            need(same([p["locator"] for p in pages], binding["ordered_selected_page_axis"])
                 and digest(binding["ordered_selected_page_axis"]) == binding["ordered_selected_page_axis_sha256"],
                 "Census selected page identity axis differs")
            source_material = {k: source[k] for k in ("source_logical_name", "source_sha256", "source_size_bytes")}
            need(source["document_id"] == "gfpstorev1:document:" + digest(source_material), "Original source document ID differs")
            need(len({p["locator"]["page_json_version_id"] for p in pages}) == len(pages), "Duplicate selected page JSON version")
            for page_ordinal, page in enumerate(pages, 1):
                locator = page["locator"]
                need(locator["document_id"] == source["document_id"] and locator["document_ordinal"] == ordinal
                     and locator["source_logical_name"] == document["relative_path"]
                     and locator["source_sha256"] == document["source_sha256"]
                     and locator["selected_page_ordinal"] == locator["physical_page"] == page_ordinal,
                     "Original page/source/global document ordinal binding differs")
            selected = {p["locator"]["physical_page"]: p["locator"]["page_json_version_id"] for p in pages}
            trial = self.db.execute(
                "SELECT rowid,source_logical_name,source_sha256,status,candidate_count,selected_candidate_id,mapping_count,reasons_json,"
                "trial_sha256,length(trial_bytes) AS size FROM family_trial WHERE family_run_id=? AND document_ordinal=?",
                (self.run_id, ordinal),
            ).fetchone()
            need(trial is not None and trial["size"] <= MAX_DOCUMENT_BLOB
                 and trial["source_logical_name"] == document["relative_path"]
                 and trial["source_sha256"] == document["source_sha256"]
                 and trial["status"] in {READY, UNRESOLVED, NOT_OBSERVED}, "Trial/source/status binding differs")
            with self.db.blobopen("family_trial", "trial_bytes", trial["rowid"], readonly=True) as blob:
                need(stream_hash(blob) == trial["trial_sha256"], "Stored trial bytes differ")
            summary = {
                "document_ordinal": ordinal, "source_logical_name": document["relative_path"], "source_sha256": document["source_sha256"],
                "source_size_bytes": document["source_size_bytes"], "status": trial["status"],
                "reasons": parse(bytes(trial["reasons_json"])), "trial_sha256": trial["trial_sha256"],
                "selected_candidate_id": trial["selected_candidate_id"], "mapping_count": trial["mapping_count"],
            }
            validate_retained_hold_trial_v3(self.profile, summary, document)
            tables = {t["table_census_id"]: t for t in census["tables"]}
            need(len(tables) == len(census["tables"]), "Duplicate original census table")
            locator_to_table = {tuple(t["locator"][k] for k in LOCATOR_KEYS): t for t in tables.values()}
            need(len(locator_to_table) == len(tables), "Duplicate original source table locator")
            cited = defaultdict(list)
            mapping_count = 0
            for mapping_row in self.db.execute(
                "SELECT rowid,mapping_ordinal,report_norm_id,role,mapping_sha256,length(mapping_bytes) AS size "
                "FROM family_mapping WHERE family_run_id=? AND document_ordinal=? ORDER BY mapping_ordinal", (self.run_id, ordinal)
            ):
                mapping_count += 1
                need(mapping_row["mapping_ordinal"] == mapping_count and mapping_row["size"] <= MAX_DOCUMENT_BLOB, "Mapping order/size differs")
                with self.db.blobopen("family_mapping", "mapping_bytes", mapping_row["rowid"], readonly=True) as blob:
                    mapping_raw = blob.read(MAX_DOCUMENT_BLOB + 1)
                need(len(mapping_raw) == mapping_row["size"], "Stored mapping BLOB size differs")
                need(hashlib.sha256(mapping_raw).hexdigest() == mapping_row["mapping_sha256"], "Stored mapping bytes differ")
                mapping = parse(mapping_raw)
                need(mapping_raw == canonical(mapping) and mapping.get("role", mapping.get("movement_role")) == mapping_row["role"]
                     and mapping["report_norm_id"] == mapping_row["report_norm_id"], "Mapping typed metadata differs")
                need(type(mapping.get("source_refs")) is list and bool(mapping["source_refs"]), "Selected mapping source refs missing")
                for ref_ordinal, ref in enumerate(mapping["source_refs"], 1):
                    key = tuple(ref["locator"][k] for k in LOCATOR_KEYS)
                    need(key in locator_to_table, "Selected mapping source table absent from original census")
                    table = locator_to_table[key]
                    row_ordinal = ref["row_ordinal"]
                    columns = ref["money_column_ordinals"]
                    need(type(row_ordinal) is int and 1 <= row_ordinal <= table["row_count"]
                         and type(columns) is list and columns and len(set(columns)) == len(columns)
                         and all(type(c) is int and c in table["raw_money_column_ordinals"] for c in columns),
                         "Selected mapping original row/money-column binding unsupported")
                    cited[(table["table_census_id"], row_ordinal)].append({
                        "mapping_ordinal": mapping_count, "source_ref_ordinal": ref_ordinal,
                        "mapping_sha256": mapping_row["mapping_sha256"], "role": mapping_row["role"],
                        "report_norm_id": mapping_row["report_norm_id"], "money_column_ordinals": columns,
                    })
            need(mapping_count == trial["mapping_count"], "Trial/mapping SQL denominator differs")
            need((trial["status"] == READY) == bool(mapping_count), "Selected mappings under non-READY trial")
            cell_iter = iter(census["raw_money_cells"])
            rows, by_table, table_ordinals = [], defaultdict(list), defaultdict(list)
            for row in census["rows"]:
                table_id, row_ordinal = row["table_census_id"], row["original_row_ordinal"]
                need(table_id in tables and type(row_ordinal) is int, "Unknown original row table/ordinal")
                table = tables[table_id]
                table_ordinals[table_id].append(row_ordinal)
                need(row["row_census_id"] == "f39rawcellv1:row:" + digest({"table_census_id": table_id, "original_row_ordinal": row_ordinal}),
                     "Original census row ID differs")
                values = row["row_exact"]["values_exact"]
                need(type(values) is list and len(values) == len(table["columns_exact"])
                     and all(v is None or type(v) is str for v in values), "Original raw row width/types differ")
                for column in table["raw_money_column_ordinals"]:
                    cell = next(cell_iter, None)
                    identity_material = {"row_census_id": row["row_census_id"], "original_raw_column_ordinal": column}
                    need(cell is not None and cell["cell_census_id"] == "f39rawcellv1:cell:" + digest(identity_material)
                         and cell["row_census_id"] == row["row_census_id"] and cell["table_census_id"] == table_id
                         and cell["original_raw_column_ordinal"] == column and same(cell["raw_value_exact"], values[column - 1]),
                         "Original raw-money cell axis omitted/duplicated/changed")
                material = {
                    "document_ordinal": ordinal, "census_id": census["census_id"], "census_sha256": metadata["census_sha256"],
                    "row_census_id": row["row_census_id"], "table_census_id": table_id, "locator": table["locator"],
                    "original_row_ordinal": row_ordinal, "raw_row_sha256": digest(row["row_exact"]),
                    "columns_exact_sha256": digest(table["columns_exact"]),
                    "raw_money_column_ordinals": table["raw_money_column_ordinals"],
                    "unknown_column_ordinals": table["unassessed_unknown_column_ordinals"],
                    "mapping_citations": cited.pop((table_id, row_ordinal), []),
                }
                item = {
                    **material, "frontier_row_id": "f39pdfrowv1:" + digest(material),
                    "raw_row_exact": row["row_exact"], "raw_columns_exact": table["columns_exact"],
                    "raw_table_title_exact": table["title_exact"], "raw_table_unit_exact": table["unit_exact"],
                }
                rows.append(item)
                by_table[(table_id, bool(item["mapping_citations"]), bool(item["raw_money_column_ordinals"]),
                          bool(item["unknown_column_ordinals"]), tuple(known_findings_for_row(item)))].append(item["frontier_row_id"])
            need(next(cell_iter, None) is None and not cited, "Extra original money cells or unmapped source refs")
            for table_id, table in tables.items():
                need(table_ordinals[table_id] == list(range(1, table["row_count"] + 1)), "Original table row frontier incomplete")
            counts = census["counts"]
            need((counts["pages"], counts["tables"], counts["rows"], counts["raw_money_cells"])
                 == (len(pages), len(tables), len(rows), len(census["raw_money_cells"])), "Census raw frontier counts differ")
            physical_count = self.pdf_pages(ordinal)
            checked_pdf = self.audit["pdf_source_byte_bindings"][ordinal - 1]
            need(checked_pdf["source_logical_name"] == document["relative_path"] and checked_pdf["source_sha256"] == document["source_sha256"]
                 and checked_pdf["source_size_bytes"] == document["source_size_bytes"]
                 and checked_pdf["source_physical_page_count"] == physical_count
                 and checked_pdf["selected_page_count"] == len(pages), "Existing PDF physical/selected frontier differs")
            required = set(range(1, physical_count + 1)) if trial["status"] in {UNRESOLVED, NOT_OBSERVED} else {r["locator"]["physical_page"] for r in rows}
            need(all(1 <= p <= physical_count for p in required), "Source row outside physical PDF")
            yield summary, rows, by_table, selected, sorted(required), physical_count


def base_material(inputs):
    return {
        "base_commit": BASE_COMMIT, "family_id": FAMILY_ID, "family_run_id": inputs.run_id, "sweep_id": inputs.sweep_id,
        "run_refs": inputs.run_refs, "render_contract": inputs.render_contract,
        "adapter_ref": inputs.adapter_ref,
        "financial_acceptance": False, "family_terminal": False,
        "official_promotion_eligible": False, "retained_hold_bindings": inputs.profile["retained_hold_bindings"],
        "approved_run_profile_ref": inputs.profile_ref, "synthetic_gate": inputs.synthetic_gate,
        "negative_admission_axis_sha256": digest(inputs.negative_admission_axis),
        "manual_review_origin": "CALLER_SUPPLIED_OWNER_ASSERTIONS_NOT_IDENTITY_AUTHENTICATION",
    }


def page_identity(summary, page, selected):
    return {
        "document_ordinal": summary["document_ordinal"], "physical_page": page,
        "page_json_version_id": selected.get(page), "source_logical_name": summary["source_logical_name"],
        "source_sha256": summary["source_sha256"],
    }


def prepare_f39_audits_v3(*, repo, run_dir, source_pdf_root, expected_refs, out_dir):
    """Writes fresh review material. Every manual classification starts PENDING."""
    out = safe(out_dir)
    need(not out.exists() and out.parent.is_dir(), "Fresh external preparation directory required")
    for authority in map(safe, (repo, run_dir, source_pdf_root, Path(expected_refs["corpus_index"]["path"]).parent.parent)):
        need(not (out == authority or out.is_relative_to(authority) or authority.is_relative_to(out)), "Output overlaps source authority")
    with Inputs(repo=repo, run_dir=run_dir, source_pdf_root=source_pdf_root, expected_refs=expected_refs) as inputs:
        out.mkdir(mode=0o700)
        visible = {**base_material(inputs), "format_version": VISIBLE_FORMAT, "groups": [], "rendered_pages": [], "render_root": str(out)}
        residual = {**base_material(inputs), "format_version": RESIDUAL_FORMAT, "residuals": [], "render_root": str(out)}
        frontier_hash, trial_hash = hashlib.sha256(), hashlib.sha256()
        counters = Counter()
        with (out / "original-source-row-frontier.jsonl").open("xb") as frontier:
            for summary, rows, grouped, selected, required, physical_count in inputs.documents():
                ordinal = summary["document_ordinal"]
                trial_hash.update(canonical(summary))
                counters["documents"] += 1
                counters["selected_pages"] += len(selected)
                directory = out / f"document-{ordinal:04d}"
                directory.mkdir(mode=0o700)
                renders = {}
                for page in required:
                    rendered = inputs.render(ordinal, page, directory / f"page-{page:04d}.png")
                    record = {**page_identity(summary, page, selected), **rendered}
                    renders[page] = record
                    visible["rendered_pages"].append(record)
                for row in rows:
                    encoded = canonical(row)
                    frontier_hash.update(encoded)
                    need(frontier.write(encoded) == len(encoded), "Incomplete original frontier write")
                    counters["source_rows"] += 1
                lookup = {r["frontier_row_id"]: r for r in rows}
                for (_table, _mapped, _money, _unknown, findings), ids in grouped.items():
                    first = lookup[ids[0]]
                    page = first["locator"]["physical_page"]
                    visible["groups"].append({
                        "group_id": "f39pdfgroupv1:" + digest(ids), "frontier_row_ids": ids,
                        "category": "PENDING", "review": pending_review(),
                        "known_finding_id": findings[0] if findings else None,
                        "reviewed_page": {k: renders[page][k] for k in ("document_ordinal", "physical_page", "render_sha256")},
                    })
                if summary["status"] in {UNRESOLVED, NOT_OBSERVED}:
                    residual["residuals"].append({
                        "trial": summary, "physical_page_count": physical_count,
                        "pdf_page_axis": [renders[p] for p in range(1, physical_count + 1)],
                        "disposition": "PENDING", "review": pending_review(), "source_exception_evidence": [],
                    })
                    counters["residual_documents"] += 1
            frontier.flush()
            os.fsync(frontier.fileno())
        need((counters["documents"], counters["selected_pages"], counters["residual_documents"])
             == (271, inputs.profile["selected_page_count"], inputs.profile["metrics"]["unresolved_count"] + inputs.profile["metrics"]["not_observed_count"]),
             "Whole-corpus preparation denominator differs")
        for material in (visible, residual):
            material["census_frontier_sha256"] = frontier_hash.hexdigest()
            material["trial_axis_sha256"] = trial_hash.hexdigest()
            material["counts"] = dict(counters)
        write_once(out / "visible-owner-review-template.json", canonical(visible))
        write_once(out / "residual-owner-review-template.json", canonical(residual))
        write_once(out / "PREPARED_NOT_VALIDATED.json", canonical({
            "status": "PREPARED_OWNER_REVIEW_REQUIRED_RETAINED_HOLDS", **base_material(inputs), "counts": dict(counters),
            "tests_executed": False, "new_store_created": False,
        }))
    return {"status": "PREPARED_OWNER_REVIEW_REQUIRED_RETAINED_HOLDS", "counts": dict(counters), "official_promotion_eligible": False}


def assemble_f39_audits_v3(*, visible_review_path, residual_review_path, out_dir):
    """Seal owner-filled COPIES of prepared templates. This is not validation."""
    need(sys.version_info[:2] == (3, 12) and sys.dont_write_bytecode, "Python3.12 -B required")
    reference = approved_profile_reference_v3()
    with pinned_file(reference["path"], reference) as (profile_stream, _profile_ref):
        validate_run_profile_contract_v3(small_json(profile_stream, 1024 * 1024))
    visible, _ = file_json(visible_review_path)
    residual, _ = file_json(residual_review_path)
    need(visible.get("format_version") == VISIBLE_FORMAT and residual.get("format_version") == RESIDUAL_FORMAT, "F39-local formats required")
    for group in visible["groups"]:
        need(group["category"] in CATEGORIES, "Pending/unknown source-row category")
        review_is_complete(group["review"], allow_known_unprinted=group["category"] == "RETAINED_SOURCE_TRANSCRIPTION_DISCREPANCY")
    for entry in residual["residuals"]:
        need(entry["disposition"] in RESIDUAL_DISPOSITIONS, "Pending/unknown residual disposition")
        review_is_complete(entry["review"], row_counterpart_required=False)
    out = safe(out_dir)
    need(out.parent.is_dir() and not out.exists(), "Fresh assembled-audit directory required")
    for reference in visible["run_refs"].values():
        authority = safe(Path(reference["path"]).parent)
        need(not (out == authority or out.is_relative_to(authority) or authority.is_relative_to(out)), "Assembled audits overlap input authority")
    need(not any((parent / ".git").exists() for parent in (out, *out.parents)), "Assembled audits must be outside Git repositories")
    out.mkdir(mode=0o700)
    write_once(out / "F39_PDF_VISIBLE_SOURCE_ROW_AUDIT_V3.json", canonical(seal(visible, "audit_id", VISIBLE_PREFIX)))
    write_once(out / "F39_PDF_RESIDUAL_SPEC_V3.json", canonical(seal(residual, "residual_spec_id", RESIDUAL_PREFIX)))
    return {"status": "SEALED_OWNER_ASSERTIONS_NOT_VALIDATED", "official_promotion_eligible": False, "financial_acceptance": False}


def validate_f39_closeout_bundle_v1(*, repo: Path, run_dir: Path, source_pdf_root: Path,
                                  visible_audit_path: Path, residual_spec_path: Path, expected_refs: dict) -> dict:
    """Fresh whole audit verification; only the pinned NEW run can become eligible.

    Eligibility is permission for a private replayed OFFICIAL copy, not financial
    acceptance, family terminality, COMMON204 completion or an integration write.
    """
    with ExitStack() as guards:
        vstream, visible_ref = guards.enter_context(pinned_file(visible_audit_path))
        rstream, residual_ref = guards.enter_context(pinned_file(residual_spec_path))
        visible = checked_seal(small_json(vstream), "audit_id", VISIBLE_PREFIX)
        residual = checked_seal(small_json(rstream), "residual_spec_id", RESIDUAL_PREFIX)
        with Inputs(repo=repo, run_dir=run_dir, source_pdf_root=source_pdf_root, expected_refs=expected_refs) as inputs:
            need(visible["format_version"] == VISIBLE_FORMAT and residual["format_version"] == RESIDUAL_FORMAT, "Wrong F39-local audit formats")
            for key, expected in base_material(inputs).items():
                need(same(visible.get(key), expected) and same(residual.get(key), expected), "Audit/base/source/render boundary differs: " + key)
            assignments, group_ids = {}, set()
            for group in visible["groups"]:
                ids = group["frontier_row_ids"]
                need(type(ids) is list and ids and len(ids) == len(set(ids)), "Nonempty unique source-row partition required")
                need(group["group_id"] == "f39pdfgroupv1:" + digest(ids) and group["group_id"] not in group_ids, "Group identity duplicated/different")
                group_ids.add(group["group_id"])
                need(group["category"] in CATEGORIES, "Pending/unsupported source-row category")
                review_is_complete(group["review"], allow_known_unprinted=group["category"] == "RETAINED_SOURCE_TRANSCRIPTION_DISCREPANCY")
                for row_id in ids:
                    need(type(row_id) is str and row_id not in assignments, "Source row appears in more than one category")
                    assignments[row_id] = group
            expected_renders = {}
            for record in visible["rendered_pages"]:
                key = (record["document_ordinal"], record["physical_page"])
                need(key not in expected_renders, "Duplicate rendered page")
                expected_renders[key] = record
            residuals = {}
            for entry in residual["residuals"]:
                ordinal = entry["trial"]["document_ordinal"]
                need(type(ordinal) is int and ordinal not in residuals, "Duplicate residual document")
                need(entry["disposition"] in RESIDUAL_DISPOSITIONS, "Pending/unsupported residual disposition")
                review_is_complete(entry["review"], row_counterpart_required=False)
                if entry["disposition"].startswith("GENUINE_SOURCE_"):
                    need(type(entry.get("source_exception_evidence")) is list and entry["source_exception_evidence"],
                         "Independent printed-source exception evidence required; algorithm reasons are not issuer ambiguity")
                residuals[ordinal] = entry
            frontier_hash, trial_hash = hashlib.sha256(), hashlib.sha256()
            counts = Counter()
            seen_known_findings = set()
            with tempfile.TemporaryDirectory(prefix="f39-closeout-revalidate-", dir=str(safe(Path("/tmp")))) as scratch_text:
                scratch = Path(scratch_text)
                for summary, rows, _grouped, selected, required, physical_count in inputs.documents():
                    ordinal = summary["document_ordinal"]
                    trial_hash.update(canonical(summary))
                    counts["documents"] += 1
                    counts["selected_pages"] += len(selected)
                    current_page_records = {}
                    for page in required:
                        key = (ordinal, page)
                        need(key in expected_renders, "Required PDF source-row/residual page unrendered")
                        old = expected_renders.pop(key)
                        rendered = inputs.render(ordinal, page, scratch / f"document-{ordinal:04d}-page-{page:04d}.png")
                        actual = {**page_identity(summary, page, selected), **{k: rendered[k] for k in ("render_sha256", "pixel_width", "pixel_height")}}
                        need(same({k: old[k] for k in actual}, actual), "Fresh PDF-render/source identity differs")
                        # The reviewed PNG must still exist at its exclusively generated preparation path.
                        render_root = safe(Path(visible["render_root"]))
                        png_path = render_root / f"document-{ordinal:04d}" / f"page-{page:04d}.png"
                        need(old["png_ref"]["path"] == str(png_path), "Reviewed PNG path differs from preparation structure")
                        with pinned_file(png_path, old["png_ref"]):
                            pass
                        current_page_records[page] = old
                    for row in rows:
                        frontier_hash.update(canonical(row))
                        counts["source_rows"] += 1
                        group = assignments.pop(row["frontier_row_id"], None)
                        need(group is not None, "Original source row lacks exactly one reviewed category")
                        category, review = group["category"], group["review"]
                        page = row["locator"]["physical_page"]
                        page_binding = {k: current_page_records[page][k] for k in ("document_ordinal", "physical_page", "render_sha256")}
                        need(same(group["reviewed_page"], page_binding), "Owner row group detached from its rendered original page")
                        known = known_findings_for_row(row)
                        if known:
                            need(not row["mapping_citations"] and category == "RETAINED_SOURCE_TRANSCRIPTION_DISCREPANCY"
                                 and group.get("known_finding_id") == NEGATIVE_ROW_FINDING
                                 and review.get("mapping_semantics_approved") is False,
                                 "Registered negative-label row must remain a bound unmapped source HOLD")
                            seen_known_findings.add(NEGATIVE_ROW_FINDING)
                        elif row["mapping_citations"]:
                            need(category == "ACCEPTED_MAPPING_SOURCE" and review.get("mapping_role_period_population_checked") is True
                                 and review.get("mapping_semantics_approved") is True,
                                 "Selected mapping source row is held/source-only or lacks positive semantic owner review")
                        else:
                            need(category not in {"ACCEPTED_MAPPING_SOURCE", "RETAINED_SOURCE_TRANSCRIPTION_DISCREPANCY"},
                                 "Uncited source row cannot become accepted or inherit a selected-mapping finding")
                        if category == "STRUCTURAL_NO_MONEY_OR_UNKNOWN_COLUMNS":
                            need(not row["raw_money_column_ordinals"] and not row["unknown_column_ordinals"], "Money/unknown source row mislabeled structural")
                    if summary["status"] in {UNRESOLVED, NOT_OBSERVED}:
                        entry = residuals.pop(ordinal, None)
                        need(entry is not None and same(entry["trial"], summary) and entry["physical_page_count"] == physical_count,
                             "Residual runner reasons/source/trial axis differs")
                        need(same(entry["pdf_page_axis"], [current_page_records[p] for p in range(1, physical_count + 1)]),
                             "Residual every-physical-PDF-page frontier differs")
                        if str(ordinal) in RETAINED_HOLD_RULES:
                            need(entry["disposition"] == RETAINED_HOLD_RULES[str(ordinal)]["residual_disposition"],
                                 "Required algorithm/transcription HOLD cannot become issuer ambiguity or NOT_OBSERVED")
                        if entry["disposition"] == "NOT_OBSERVED_AFTER_FULL_PDF_REVIEW":
                            need(summary["status"] == NOT_OBSERVED, "UNRESOLVED cannot be relabeled NOT_OBSERVED")
                        for exception in entry["source_exception_evidence"]:
                            need(type(exception) is dict and type(exception.get("physical_page")) is int
                                 and exception.get("document_ordinal") == ordinal
                                 and exception["physical_page"] in current_page_records,
                                 "Source exception lacks a bound page of its own residual document")
                            need(exception.get("render_sha256") == current_page_records[exception["physical_page"]]["render_sha256"]
                                 and type(exception.get("evidence")) is str and len(exception["evidence"].strip()) >= 24,
                                 "Source exception lacks concrete evidence on an authenticated rendered page")
                        counts["residual_documents"] += 1
            need(not assignments and not expected_renders and not residuals, "Unclosed/extra source row, PDF page or residual frontier")
            need(seen_known_findings == {NEGATIVE_ROW_FINDING}, "Exact retained negative source row must remain visible and unmapped")
            need((counts["documents"], counts["selected_pages"], counts["residual_documents"])
                 == (271, inputs.profile["selected_page_count"], inputs.profile["metrics"]["unresolved_count"] + inputs.profile["metrics"]["not_observed_count"]),
                 "Complete original FULL271/N-U denominator differs")
            for value in (visible, residual):
                need(value["census_frontier_sha256"] == frontier_hash.hexdigest()
                     and value["trial_axis_sha256"] == trial_hash.hexdigest() and same(value["counts"], dict(counts)),
                     "Source census/trial/count frontier digest differs")
            need([tuple(r) for r in inputs.db.execute("PRAGMA quick_check")] == [("ok",)],
                 "Read-only result SQLite quick_check failed")
            need(not list(inputs.db.execute("PRAGMA foreign_key_check")), "Read-only result SQLite foreign_key_check failed")
            result = {
                "status": "VALIDATED_F39_CLOSEOUT_AUDITS_NOT_ACCEPTANCE", "family_run_id": inputs.run_id, "sweep_id": inputs.sweep_id,
                "visible_audit_ref": visible_ref, "residual_spec_ref": residual_ref, "run_refs": inputs.run_refs,
                "source_database_ref": inputs.index["database_ref"], "census_frontier_sha256": frontier_hash.hexdigest(),
                "trial_axis_sha256": trial_hash.hexdigest(), "counts": dict(counts),
                "official_promotion_eligible": True, "blocking_findings": [],
                "approved_run_profile_ref": inputs.profile_ref, "approved_run_profile": inputs.profile,
                "synthetic_gate": inputs.synthetic_gate, "retained_holds_preserved": [110, 225],
                "negative_admission_axis_sha256": digest(inputs.negative_admission_axis),
                "financial_acceptance": False, "family_terminal": False, "new_store_created": False,
                "original_audit_metadata": {
                    key: inputs.audit[key] for key in (
                        "implementation_refs", "immutable_input_refs", "original_raw_money_census",
                        "registered_section_caption_admission", "registered_source_label_discrepancy_admission_axis", "pdf_source_byte_bindings",
                    )
                },
            }
        return result


def main():
    need(sys.version_info[:2] == (3, 12) and sys.dont_write_bytecode, "Python3.12 -B required")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "validate"):
        item = sub.add_parser(name)
        item.add_argument("--repo", type=Path, required=True)
        item.add_argument("--run-dir", type=Path, required=True)
        item.add_argument("--pdf-root", type=Path, required=True)
        item.add_argument("--corpus-index", type=Path, required=True)
        if name == "prepare":
            item.add_argument("--out-dir", type=Path, required=True)
        else:
            item.add_argument("--visible-audit", type=Path, required=True)
            item.add_argument("--residual-spec", type=Path, required=True)
            item.add_argument("--receipt-path", type=Path, required=True)
    assemble = sub.add_parser("assemble")
    assemble.add_argument("--visible-review", type=Path, required=True)
    assemble.add_argument("--residual-review", type=Path, required=True)
    assemble.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "assemble":
        result = assemble_f39_audits_v3(visible_review_path=args.visible_review, residual_review_path=args.residual_review, out_dir=args.out_dir)
    else:
        with ExitStack() as profile_guards:
            profile, _profile_ref, _gate = read_approved_run_profile_v3(guards=profile_guards, repo=args.repo)
            refs = parse(canonical(profile["expected_refs"]))
            need(Path(refs["corpus_index"]["path"]) == safe(args.corpus_index), "CLI cannot replace approved corpus authority")
        keywords = {"repo": args.repo, "run_dir": args.run_dir, "source_pdf_root": args.pdf_root, "expected_refs": refs}
        if args.command == "prepare":
            result = prepare_f39_audits_v3(**keywords, out_dir=args.out_dir)
        else:
            result = validate_f39_closeout_bundle_v1(**keywords, visible_audit_path=args.visible_audit, residual_spec_path=args.residual_spec)
            receipt_path = safe(args.receipt_path)
            for authority in map(safe, (args.repo, args.run_dir, args.pdf_root, args.corpus_index.parent.parent)):
                need(not (receipt_path == authority or receipt_path.is_relative_to(authority) or authority.is_relative_to(receipt_path)),
                     "Validation receipt overlaps source authority")
            need(not any((parent / ".git").exists() for parent in receipt_path.parents), "Validation receipt must be outside Git repositories")
            write_once(receipt_path, canonical(result))
    print(json.dumps({k: result[k] for k in ("status", "official_promotion_eligible")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

