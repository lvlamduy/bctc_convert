"""Build and exclusively publish the finalized Wave-1 statement hypotheses.

The producer consumes the one authenticated 1,449-page V3 survey stream and
the already-published compact source inventory.  It projects every page and
applies the document-local candidate-only statement hypothesis builder once
per source document.  The resulting corpus artifact retains every page
binding, page hypothesis, disposition, evidence code, and ranked block
hypothesis; it does not promote any hypothesis to statement truth.

Publication is deliberately exclusive and crash-bounded. Canonical bytes are
sealed under one owned temporary inode, then hard-linked atomically to the
absent final name. No overwrite/replace operation exists in this module.
"""

from __future__ import annotations

import os
import re
import secrets
import stat
from collections import Counter
from collections.abc import Mapping, Sequence
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any

from bctc_ai.corpus import wave1_role_b_sentinel as sentinel
from bctc_ai.document_phase.statement_locator_v2 import (
    load_statement_locator_v2_config,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.document_statement_hypotheses_v1 import (
    DOCUMENT_STATEMENT_HYPOTHESES_CLAIM_BOUNDARY_V1,
    DOCUMENT_STATEMENT_HYPOTHESES_FORMAT_VERSION_V1,
    build_document_statement_block_hypotheses_v1,
)
from bctc_ai.source_structure.evidence_projection_v2 import (
    project_authenticated_page_v2,
)
from bctc_ai.source_structure.finalized_v3_survey_stream_v1 import (
    FINALIZED_V3_SURVEY_AUTHORITY_V1,
    FinalizedV3SurveyAuthority,
    open_finalized_v3_survey_stream_v1,
)
from bctc_ai.source_structure.wave1_source_inventory_v1 import (
    validate_wave1_source_inventory_v1,
)

__all__ = [
    "WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_INVENTORY_CLAIM_BOUNDARY_V1",
    "WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_INVENTORY_FORMAT_VERSION_V1",
    "WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_OUTPUT_RELATIVE_PATH_V1",
    "Wave1DocumentStatementHypothesesInventoryV1Error",
    "build_wave1_document_statement_hypotheses_inventory_v1",
    "publish_wave1_document_statement_hypotheses_inventory_v1",
    "validate_wave1_document_statement_hypotheses_inventory_v1",
]


class Wave1DocumentStatementHypothesesInventoryV1Error(ValueError):
    """The corpus hypothesis inventory crossed its sealed candidate boundary."""


WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_INVENTORY_FORMAT_VERSION_V1 = (
    "BANK_CORPUS_WAVE_1_ROLE_B_DOCUMENT_STATEMENT_HYPOTHESES_INVENTORY_V1"
)
WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_INVENTORY_CLAIM_BOUNDARY_V1 = (
    "EXHAUSTIVE_DOCUMENT_AND_PAGE_STATEMENT_BLOCK_HYPOTHESES_ONLY_"
    "NO_SEMANTIC_ACCEPTANCE_MAPPING_SCOPE_OR_ABSENCE_TRUTH"
)
WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_OUTPUT_RELATIVE_PATH_V1 = Path(
    "output/development/bank-corpus-survey-v1/wave-1-role-b-document-statement-hypotheses-v1.json"
)

_SOURCE_INVENTORY_RELATIVE_PATH = Path(
    "output/development/bank-corpus-survey-v1/wave-1-role-b-source-first-inventory-v1.json"
)
_SOURCE_INVENTORY_SHA256 = "c20c9b42ff6f96baf6eff6607e12b27681146d8d968e4e86f0e792bde1429162"
_SOURCE_INVENTORY_SIZE_BYTES = 1_920_845
_SOURCE_INVENTORY_IDENTITY_SHA256 = (
    "63c5988b80cc9893cc20f1b7476d9124880c838d8e4bc6a9d5f4df195550ad84"
)
_LOCATOR_POLICY_RELATIVE_PATH = Path("config/document_phase/statement-locator-v2.yaml")
_LOCATOR_POLICY_SHA256 = "503f3fdb62dd5dcd1a460200750edfe18d7cf50039b62278666e572c6cccb730"
_LOCATOR_POLICY_SIZE_BYTES = 1_104
_USED_POLICY_SHA256 = "a55cb6fb9281fff6d20d7883b0fc761111a88406e6398d3ab8af8a9aefa61fe5"
_FINALIZED_AGGREGATE_IDENTITY_SHA256 = (
    "45eea722bb298fd0ef8b77afef141f15311705bdd8c65a2ee6e4bfd232e1ab44"
)

_FORMAT_STATUS = "COMPLETE_CANDIDATE_HYPOTHESIS_INVENTORY"
_ARTIFACT_STATUSES = (
    "CANDIDATES_EMITTED",
    "UNRESOLVED_NO_COMPLETE_ORDERED_HYPOTHESIS",
)
_ROUTES = ("CAUSAL_NATIVE_TEXT", "DOMINANT_RASTER_OCR")
_UPSTREAM_STATUSES = (
    "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
    "OCR_WORD_BOX_READ_COMPLETE",
    "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
    "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
)
_STATUS_ROUTE = {
    "CAUSAL_NATIVE_TEXT_READ_COMPLETE": "CAUSAL_NATIVE_TEXT",
    "OCR_WORD_BOX_READ_COMPLETE": "DOMINANT_RASTER_OCR",
    "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY": "CAUSAL_NATIVE_TEXT",
    "UNRESOLVED_OCR_WORD_BOX_GEOMETRY": "DOMINANT_RASTER_OCR",
}
_PAGE_FAMILIES = (
    "CDKT",
    "KQKD",
    "LCTT",
    "TM",
    "AUDIT_REPORT",
    "TABLE_OF_CONTENTS",
    "AMBIGUOUS",
    "OTHER",
    "UPSTREAM_TERMINAL",
)
_PAGE_DISPOSITIONS = (
    "SUPPORTS_STATEMENT_BLOCK_HYPOTHESIS",
    "RETAINED_UNRESOLVED",
    "UPSTREAM_TERMINAL_UNRESOLVED",
)
_EVIDENCE_CODES = (
    "AMBIGUOUS_FAMILY_SIGNAL_HYPOTHESIS",
    "AUDIT_SUPPRESSION_SIGNAL_HYPOTHESIS",
    "CONTINUATION_MARKER_SIGNAL_HYPOTHESIS",
    "FORM_FAMILY_SIGNAL_HYPOTHESIS",
    "NO_FAMILY_SIGNAL_RETAINED",
    "NUMERIC_TOKEN_DENSITY_SIGNAL_HYPOTHESIS",
    "OFF_BALANCE_SIGNAL_HYPOTHESIS",
    "TITLE_DISCRIMINATOR_SIGNAL_HYPOTHESIS",
    "TITLE_SIGNAL_HYPOTHESIS",
    "TOC_SUPPRESSION_SIGNAL_HYPOTHESIS",
    "UPSTREAM_TERMINAL_BARRIER",
)
_POLICY_RECEIPT_KEYS = (
    "version",
    "policy",
    "v2",
    "form_anchors",
    "title_anchors",
    "title_discriminator_anchors",
    "audit_anchors",
    "toc_anchors",
    "continuation_anchors",
    "off_balance_heading_anchors",
    "off_balance_item_anchors",
    "header_fraction",
    "title_min_similarity",
    "title_min_margin",
    "continuation_title_min_similarity",
    "continuation_anchor_min_similarity",
    "title_only_min_numeric_line_fraction",
    "title_discriminator_min_similarity",
    "audit_min_similarity",
    "toc_min_similarity",
    "off_balance_heading_min_similarity",
    "off_balance_item_min_similarity",
    "toc_min_distinct_statement_titles",
    "off_balance_min_item_hits",
    "max_interstitial_pages",
    "candidate_score_weights",
)

_SAFETY = {
    "hypothesis_only": True,
    "validated_projection_primary_line_evidence_used": True,
    "direct_raw_text_input_used": False,
    "source_text_persisted": False,
    "semantic_acceptance_claimed": False,
    "statement_identity_claimed": False,
    "statement_block_accepted": False,
    "statement_family_accepted": False,
    "table_claimed": False,
    "row_claimed": False,
    "cell_claimed": False,
    "axis_claimed": False,
    "hierarchy_claimed": False,
    "tm_coverage_claimed": False,
    "scope_truth_claimed": False,
    "mapping_claimed": False,
    "cash_flow_method_claimed": False,
    "schema_truth_claimed": False,
    "absence_claimed": False,
    "bank_identity_used_for_routing": False,
    "filename_or_path_used_for_routing": False,
    "document_name_used_for_routing": False,
    "note_number_rules_used_for_routing": False,
    "exact_page_number_used_for_routing": False,
    "role_a_used": False,
    "historical_values_used": False,
    "source_pdf_opened": False,
    "model_or_ocr_invoked": False,
    "geometry_proposals_used": False,
    "compact_source_inventory_used_for_binding_only": True,
    "standalone_validator_is_structural_accounting_only": True,
    "downstream_exact_raw_artifact_sha256_pin_required": True,
}

_TOP_LEVEL_FIELDS = {
    "format_version",
    "claim_boundary",
    "status",
    "authority",
    "documents",
    "corpus_metrics",
    "producer",
    "safety",
    "inventory_identity_sha256",
}
_AUTHORITY_FIELDS = {"finalized_v3", "source_inventory", "locator_policy"}
_FINALIZED_AUTHORITY_FIELDS = {
    "aggregate_artifact_sha256",
    "aggregate_size_bytes",
    "aggregate_identity_sha256",
    "control_artifact_sha256",
    "control_size_bytes",
    "control_identity_sha256",
    "sealed_plan_sha256",
    "document_ids",
    "document_count",
    "request_count",
    "referenced_object_count",
}
_SOURCE_INVENTORY_AUTHORITY_FIELDS = {
    "path",
    "sha256",
    "size_bytes",
    "inventory_identity_sha256",
}
_POLICY_AUTHORITY_FIELDS = {"path", "sha256", "size_bytes", "used_policy_sha256"}
_DOCUMENT_FIELDS = {
    "format_version",
    "claim_boundary",
    "status",
    "source_sha256",
    "locator_policy_receipt",
    "page_projection_bindings",
    "page_hypotheses",
    "block_hypotheses",
    "page_dispositions",
    "metrics",
    "safety",
    "document_hypotheses_identity",
}
_POLICY_RECEIPT_FIELDS = {
    "format_version",
    "classifier_revision",
    "block_scorer_revision",
    "used_keys",
    "used_policy_sha256",
}
_BINDING_FIELDS = {
    "input_ordinal",
    "source_local_page_id",
    "source_projection_sha256",
    "route",
    "upstream_status",
    "terminal",
}
_PAGE_HYPOTHESIS_FIELDS = {
    "page_hypothesis_id",
    *_BINDING_FIELDS - {"route"},
    "family_hypothesis",
    "diagnostic_score",
    "evidence_codes",
    "continuation_marker_hypothesis",
}
_BLOCK_FIELDS = {
    "block_hypothesis_id",
    "rank",
    "start_input_ordinal",
    "end_input_ordinal",
    "member_page_hypothesis_ids",
    "family_sequence_hypothesis",
    "family_evidence_codes",
    "tm_boundary_hypothesis_id",
    "diagnostic_score",
    "diagnostic_score_components",
}
_BLOCK_SCORE_FIELDS = {
    "start_form_signal",
    "form_signal_page_count",
    "average_family_confidence",
}
_BLOCK_SCORE_WEIGHTS = {
    "start_form_signal": 4.0,
    "form_signal_page_count": 2.0,
    "average_family_confidence": 2.0,
}
_PAGE_DISPOSITION_FIELDS = {
    "input_ordinal",
    "source_local_page_id",
    "page_hypothesis_id",
    "primary_disposition",
    "block_hypothesis_ids",
}
_DOCUMENT_METRIC_FIELDS = {
    "page_count",
    "terminal_page_count",
    "block_hypothesis_count",
    "page_disposition_counts",
    "family_hypothesis_counts",
    "evidence_code_counts",
}
_CORPUS_METRIC_FIELDS = {
    "document_count",
    "page_count",
    "terminal_page_count",
    "page_hypothesis_count",
    "page_disposition_count",
    "block_hypothesis_count",
    "candidate_document_count",
    "unresolved_document_count",
    "artifact_status_counts",
    "page_disposition_counts",
    "family_hypothesis_counts",
    "evidence_code_counts",
}
_FINALIZED_CORPUS_METRICS = {
    "document_count": 27,
    "page_count": 1_449,
    "terminal_page_count": 59,
    "page_hypothesis_count": 1_449,
    "page_disposition_count": 1_449,
    "block_hypothesis_count": 24,
    "candidate_document_count": 13,
    "unresolved_document_count": 14,
    "artifact_status_counts": {
        "CANDIDATES_EMITTED": 13,
        "UNRESOLVED_NO_COMPLETE_ORDERED_HYPOTHESIS": 14,
    },
    "page_disposition_counts": {
        "SUPPORTS_STATEMENT_BLOCK_HYPOTHESIS": 96,
        "RETAINED_UNRESOLVED": 1_294,
        "UPSTREAM_TERMINAL_UNRESOLVED": 59,
    },
    "family_hypothesis_counts": {
        "CDKT": 65,
        "KQKD": 27,
        "LCTT": 42,
        "TM": 796,
        "AUDIT_REPORT": 0,
        "TABLE_OF_CONTENTS": 12,
        "AMBIGUOUS": 3,
        "OTHER": 445,
        "UPSTREAM_TERMINAL": 59,
    },
    "evidence_code_counts": {
        "AMBIGUOUS_FAMILY_SIGNAL_HYPOTHESIS": 3,
        "AUDIT_SUPPRESSION_SIGNAL_HYPOTHESIS": 0,
        "CONTINUATION_MARKER_SIGNAL_HYPOTHESIS": 188,
        "FORM_FAMILY_SIGNAL_HYPOTHESIS": 790,
        "NO_FAMILY_SIGNAL_RETAINED": 88,
        "NUMERIC_TOKEN_DENSITY_SIGNAL_HYPOTHESIS": 776,
        "OFF_BALANCE_SIGNAL_HYPOTHESIS": 49,
        "TITLE_DISCRIMINATOR_SIGNAL_HYPOTHESIS": 1_189,
        "TITLE_SIGNAL_HYPOTHESIS": 744,
        "TOC_SUPPRESSION_SIGNAL_HYPOTHESIS": 12,
        "UPSTREAM_TERMINAL_BARRIER": 59,
    },
}
_PRODUCER_FIELDS = {"git", "implementation_ledger"}
_GIT_FIELDS = {"commit", "dirty"}
_LEDGER_FIELDS = {"records", "sha256"}
_LEDGER_RECORD_FIELDS = {"phase", "kind", "path", "sha256", "size_bytes"}

_DOCUMENT_SAFETY = {
    "candidate_hypotheses_only": True,
    "source_text_persisted": False,
    "semantic_acceptance_claimed": False,
    "statement_identity_claimed": False,
    "statement_block_accepted": False,
    "statement_family_accepted": False,
    "table_claimed": False,
    "row_claimed": False,
    "cell_claimed": False,
    "axis_claimed": False,
    "hierarchy_claimed": False,
    "scope_truth_claimed": False,
    "mapping_claimed": False,
    "cash_flow_method_claimed": False,
    "schema_used_for_routing": False,
    "absence_claimed": False,
    "bank_identity_used_for_routing": False,
    "filename_identity_used_for_routing": False,
    "note_number_rules_used_for_routing": False,
    "exact_page_number_used_for_routing": False,
    "role_a_used_for_routing": False,
    "historical_values_used_for_routing": False,
    "external_identity_routing_used": False,
    "source_location_used_for_family_classification": False,
    "exact_sequence_number_used_for_routing": False,
    "numeric_magnitude_used_for_family_classification": False,
    "role_a_or_schema_reference_data_used": False,
    "upstream_provider_invoked": False,
}

_IMPLEMENTATION_PATHS = (
    Path("src/bctc_ai/__init__.py"),
    Path("src/bctc_ai/core/__init__.py"),
    Path("src/bctc_ai/core/contracts.py"),
    Path("src/bctc_ai/core/coordinates.py"),
    Path("src/bctc_ai/core/hashing.py"),
    Path("src/bctc_ai/core/text.py"),
    Path("src/bctc_ai/corpus/__init__.py"),
    Path("src/bctc_ai/corpus/wave1_pre_ocr_structure.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_full_reader_v3.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_page_reader.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_sentinel.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_word_box_normalization.py"),
    Path("src/bctc_ai/document_phase/__init__.py"),
    Path("src/bctc_ai/document_phase/statement_locator.py"),
    Path("src/bctc_ai/document_phase/statement_locator_v2.py"),
    Path("src/bctc_ai/ocr/__init__.py"),
    Path("src/bctc_ai/ocr/_causal_visibility_core.py"),
    Path("src/bctc_ai/ocr/causal_native_text.py"),
    Path("src/bctc_ai/ocr/causal_native_text_evidence_v1.py"),
    Path("src/bctc_ai/ocr/causal_native_text_evidence_v2.py"),
    Path("src/bctc_ai/ocr/native_text_quality_v2.py"),
    Path("src/bctc_ai/ocr/pdf_text.py"),
    Path("src/bctc_ai/ocr/ppocrv6_page_session.py"),
    Path("src/bctc_ai/rendering/__init__.py"),
    Path("src/bctc_ai/rendering/page_reader.py"),
    Path("src/bctc_ai/source_structure/__init__.py"),
    Path("src/bctc_ai/source_structure/contracts_v1.py"),
    Path("src/bctc_ai/source_structure/contracts_v2.py"),
    Path("src/bctc_ai/source_structure/document_statement_hypotheses_v1.py"),
    Path("src/bctc_ai/source_structure/evidence_projection_v1.py"),
    Path("src/bctc_ai/source_structure/evidence_projection_v2.py"),
    Path("src/bctc_ai/source_structure/finalized_v3_survey_stream_v1.py"),
    Path("src/bctc_ai/source_structure/page_geometry_proposals_v1.py"),
    Path("src/bctc_ai/source_structure/wave1_source_inventory_v1.py"),
    Path("src/bctc_ai/source_structure/wave1_document_statement_hypotheses_inventory_v1.py"),
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DOCUMENT_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PAGE_ID_RE = re.compile(r"^ssv2:page:[0-9a-f]{64}$")
_PAGE_HYPOTHESIS_ID_RE = re.compile(r"^ssdv1:page-hypothesis:[0-9a-f]{64}$")
_BLOCK_HYPOTHESIS_ID_RE = re.compile(r"^ssdv1:block-hypothesis:[0-9a-f]{64}$")
_DOCUMENT_HYPOTHESIS_ID_RE = re.compile(r"^ssdv1:document:[0-9a-f]{64}$")


def _error(message: str) -> Wave1DocumentStatementHypothesesInventoryV1Error:
    return Wave1DocumentStatementHypothesesInventoryV1Error(message)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise _error(f"{label} must be a lowercase SHA-256")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be a positive integer")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be a nonnegative integer")
    return value


def _finite(value: Any, label: str) -> float:
    if type(value) is not float or not isfinite(value):
        raise _error(f"{label} must be a finite float")
    return value


def _closed_counts(value: Any, vocabulary: Sequence[str], label: str) -> dict[str, int]:
    counts = _exact_dict(value, set(vocabulary), label)
    for key in vocabulary:
        _nonnegative(counts[key], f"{label} {key}")
    return counts


def _authority_payload(authority: FinalizedV3SurveyAuthority) -> dict[str, Any]:
    return {
        "aggregate_artifact_sha256": authority.aggregate_artifact_sha256,
        "aggregate_size_bytes": authority.aggregate_size_bytes,
        "aggregate_identity_sha256": authority.aggregate_identity_sha256,
        "control_artifact_sha256": authority.control_artifact_sha256,
        "control_size_bytes": authority.control_size_bytes,
        "control_identity_sha256": authority.control_identity_sha256,
        "sealed_plan_sha256": authority.sealed_plan_sha256,
        "document_ids": list(authority.document_ids),
        "document_count": authority.document_count,
        "request_count": authority.request_count,
        "referenced_object_count": authority.referenced_object_count,
    }


def _producer_receipt(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    try:
        git = sentinel._git_identity(project_root, require_clean=True)  # noqa: SLF001
        ledger = sentinel._implementation_ledger(  # noqa: SLF001
            project_root,
            git["commit"],
            _IMPLEMENTATION_PATHS,
        )
    except (OSError, sentinel.WaveOneRoleBSentinelError) as exc:
        raise _error(f"statement-hypothesis producer is not a clean commit: {exc}") from exc
    return {
        "git": canonical_clone_v1(git),
        "implementation_ledger": canonical_clone_v1(ledger),
    }


def _validate_producer(value: Any, *, project_root: Path) -> dict[str, Any]:
    producer = _exact_dict(value, _PRODUCER_FIELDS, "producer")
    git = _exact_dict(producer["git"], _GIT_FIELDS, "producer Git")
    if (
        type(git["commit"]) is not str
        or re.fullmatch(r"[0-9a-f]{40}", git["commit"]) is None
        or git["dirty"] is not False
    ):
        raise _error("producer Git identity drifted")
    ledger = _exact_dict(
        producer["implementation_ledger"],
        _LEDGER_FIELDS,
        "producer implementation ledger",
    )
    records = ledger["records"]
    expected_paths = [path.as_posix() for path in sorted(set(_IMPLEMENTATION_PATHS))]
    if type(records) is not list or len(records) != len(expected_paths):
        raise _error("producer implementation denominator drifted")
    for expected_path, raw_record in zip(expected_paths, records, strict=True):
        record = _exact_dict(raw_record, _LEDGER_RECORD_FIELDS, "implementation record")
        if (
            record["phase"] != "READ"
            or record["kind"] != "IMPLEMENTATION"
            or record["path"] != expected_path
        ):
            raise _error("producer implementation role/path drifted")
        _sha(record["sha256"], "implementation digest")
        _positive(record["size_bytes"], "implementation size")
    if _sha(ledger["sha256"], "implementation ledger identity") != canonical_json_sha256_v1(
        records
    ):
        raise _error("implementation ledger identity drifted")
    try:
        recomputed = sentinel._implementation_ledger(  # noqa: SLF001
            project_root.resolve(),
            git["commit"],
            _IMPLEMENTATION_PATHS,
        )
    except (OSError, sentinel.WaveOneRoleBSentinelError) as exc:
        raise _error("producer implementation cannot be replayed from its stored commit") from exc
    if not same_typed_json_v1(ledger, recomputed):
        raise _error("stored producer ledger differs from committed implementation bytes")
    return producer


def _read_stable_nofollow(
    path: Path,
    label: str,
    *,
    expected_mode: int | None = None,
) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or (expected_mode is not None and stat.S_IMODE(before.st_mode) != expected_mode)
        ):
            raise _error(f"{label} is not a canonical regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise _error(f"cannot read {label}: {path}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    try:
        named = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise _error(f"cannot revalidate {label}: {path}") from exc
    token = lambda item: (  # noqa: E731 - compact immutable identity token
        item.st_dev,
        item.st_ino,
        stat.S_IFMT(item.st_mode),
        stat.S_IMODE(item.st_mode),
        item.st_nlink,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if token(before) != token(after) or token(after) != token(named):
        raise _error(f"{label} changed while being read")
    payload = b"".join(chunks)
    if len(payload) != before.st_size:
        raise _error(f"{label} byte count drifted")
    return payload


def _load_source_inventory(project_root: Path) -> dict[str, Any]:
    path = project_root / _SOURCE_INVENTORY_RELATIVE_PATH
    payload = _read_stable_nofollow(
        path,
        "compact source inventory",
        expected_mode=0o444,
    )
    if (
        len(payload) != _SOURCE_INVENTORY_SIZE_BYTES
        or sha256(payload).hexdigest() != _SOURCE_INVENTORY_SHA256
    ):
        raise _error("compact source inventory artifact identity drifted")
    try:
        decoded = decode_canonical_json_bytes_v1(payload)
        validated = validate_wave1_source_inventory_v1(decoded)
    except ValueError as exc:
        raise _error("compact source inventory contract drifted") from exc
    if validated.get("inventory_identity_sha256") != _SOURCE_INVENTORY_IDENTITY_SHA256:
        raise _error("compact source inventory logical identity drifted")
    return validated


def _load_locator_policy(project_root: Path) -> dict[str, Any]:
    path = project_root / _LOCATOR_POLICY_RELATIVE_PATH
    payload_before = _read_stable_nofollow(
        path,
        "statement locator V2 policy",
        expected_mode=0o644,
    )
    if (
        len(payload_before) != _LOCATOR_POLICY_SIZE_BYTES
        or sha256(payload_before).hexdigest() != _LOCATOR_POLICY_SHA256
    ):
        raise _error("statement locator V2 policy artifact identity drifted")
    try:
        policy = load_statement_locator_v2_config(path)
    except (OSError, ValueError) as exc:
        raise _error("statement locator V2 policy contract drifted") from exc
    if (
        _read_stable_nofollow(
            path,
            "statement locator V2 policy",
            expected_mode=0o644,
        )
        != payload_before
    ):
        raise _error("statement locator V2 policy changed while loading")
    return policy


def _source_inventory_authority() -> dict[str, Any]:
    return {
        "path": _SOURCE_INVENTORY_RELATIVE_PATH.as_posix(),
        "sha256": _SOURCE_INVENTORY_SHA256,
        "size_bytes": _SOURCE_INVENTORY_SIZE_BYTES,
        "inventory_identity_sha256": _SOURCE_INVENTORY_IDENTITY_SHA256,
    }


def _locator_policy_authority() -> dict[str, Any]:
    return {
        "path": _LOCATOR_POLICY_RELATIVE_PATH.as_posix(),
        "sha256": _LOCATOR_POLICY_SHA256,
        "size_bytes": _LOCATOR_POLICY_SIZE_BYTES,
        "used_policy_sha256": _USED_POLICY_SHA256,
    }


def _validate_finalized_authority(value: Any) -> dict[str, Any]:
    authority = _exact_dict(value, _FINALIZED_AUTHORITY_FIELDS, "finalized V3 authority")
    for field in (
        "aggregate_artifact_sha256",
        "aggregate_identity_sha256",
        "control_artifact_sha256",
        "control_identity_sha256",
        "sealed_plan_sha256",
    ):
        _sha(authority[field], f"finalized V3 authority {field}")
    for field in (
        "aggregate_size_bytes",
        "control_size_bytes",
        "document_count",
        "request_count",
        "referenced_object_count",
    ):
        _positive(authority[field], f"finalized V3 authority {field}")
    if not same_typed_json_v1(authority, _authority_payload(FINALIZED_V3_SURVEY_AUTHORITY_V1)):
        raise _error("finalized V3 authority differs from the exact pin")
    return authority


def _validate_authority(value: Any, source_inventory: Mapping[str, Any]) -> dict[str, Any]:
    authority = _exact_dict(value, _AUTHORITY_FIELDS, "inventory authority")
    finalized = _validate_finalized_authority(authority["finalized_v3"])
    source = _exact_dict(
        authority["source_inventory"],
        _SOURCE_INVENTORY_AUTHORITY_FIELDS,
        "compact source inventory authority",
    )
    policy = _exact_dict(
        authority["locator_policy"],
        _POLICY_AUTHORITY_FIELDS,
        "statement locator policy authority",
    )
    if source != _source_inventory_authority():
        raise _error("compact source inventory authority pin drifted")
    if policy != _locator_policy_authority():
        raise _error("statement locator policy authority pin drifted")
    if not same_typed_json_v1(source_inventory["authority"], finalized):
        raise _error("compact inventory and finalized V3 authority diverged")
    return authority


def _validate_policy_receipt(value: Any) -> dict[str, Any]:
    receipt = _exact_dict(value, _POLICY_RECEIPT_FIELDS, "locator policy receipt")
    if (
        receipt["format_version"]
        != "BANK_CORPUS_WAVE_1_ROLE_B_STATEMENT_HYPOTHESIS_POLICY_RECEIPT_V1"
        or receipt["classifier_revision"] != "STATEMENT_PAGE_CLASSIFIER_V2"
        or receipt["block_scorer_revision"] != "ORDERED_CANDIDATE_BLOCK_SCORER_V1"
        or receipt["used_keys"] != list(_POLICY_RECEIPT_KEYS)
        or receipt["used_policy_sha256"] != _USED_POLICY_SHA256
    ):
        raise _error("locator policy receipt drifted")
    return receipt


def _validate_binding(value: Any, *, expected_ordinal: int) -> dict[str, Any]:
    binding = _exact_dict(value, _BINDING_FIELDS, "page projection binding")
    if binding["input_ordinal"] != expected_ordinal:
        raise _error("document page input ordinal drifted")
    if (
        type(binding["source_local_page_id"]) is not str
        or _PAGE_ID_RE.fullmatch(binding["source_local_page_id"]) is None
    ):
        raise _error("document source-local page identity drifted")
    _sha(binding["source_projection_sha256"], "document source projection digest")
    if (
        binding["route"] not in _ROUTES
        or binding["upstream_status"] not in _UPSTREAM_STATUSES
        or _STATUS_ROUTE[binding["upstream_status"]] != binding["route"]
        or type(binding["terminal"]) is not bool
        or binding["terminal"] != binding["upstream_status"].startswith("UNRESOLVED_")
    ):
        raise _error("document page route/status/terminal binding drifted")
    return binding


def _validate_page_hypothesis(
    value: Any,
    *,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    hypothesis = _exact_dict(value, _PAGE_HYPOTHESIS_FIELDS, "page hypothesis")
    shared = {key: binding[key] for key in _BINDING_FIELDS if key != "route"}
    if any(not same_typed_json_v1(hypothesis[key], shared[key]) for key in shared):
        raise _error("page hypothesis source binding drifted")
    if (
        type(hypothesis["page_hypothesis_id"]) is not str
        or _PAGE_HYPOTHESIS_ID_RE.fullmatch(hypothesis["page_hypothesis_id"]) is None
        or hypothesis["family_hypothesis"] not in _PAGE_FAMILIES
    ):
        raise _error("page hypothesis identity/family drifted")
    diagnostic_score = _finite(
        hypothesis["diagnostic_score"],
        "page hypothesis diagnostic score",
    )
    if not 0.0 <= diagnostic_score <= 1.0:
        raise _error("page hypothesis diagnostic score lies outside [0, 1]")
    evidence = hypothesis["evidence_codes"]
    if (
        type(evidence) is not list
        or not evidence
        or evidence != sorted(set(evidence))
        or any(code not in _EVIDENCE_CODES for code in evidence)
        or type(hypothesis["continuation_marker_hypothesis"]) is not bool
    ):
        raise _error("page hypothesis evidence/continuation receipt drifted")
    if binding["terminal"]:
        if (
            hypothesis["family_hypothesis"] != "UPSTREAM_TERMINAL"
            or hypothesis["diagnostic_score"] != 0.0
            or evidence != ["UPSTREAM_TERMINAL_BARRIER"]
            or hypothesis["continuation_marker_hypothesis"] is not False
        ):
            raise _error("terminal page hypothesis barrier drifted")
    elif (
        hypothesis["family_hypothesis"] == "UPSTREAM_TERMINAL"
        or "UPSTREAM_TERMINAL_BARRIER" in evidence
    ):
        raise _error("complete page carried an upstream terminal hypothesis")
    payload = {key: hypothesis[key] for key in hypothesis if key != "page_hypothesis_id"}
    expected_id = "ssdv1:page-hypothesis:" + canonical_json_sha256_v1(
        {"used_policy_sha256": _USED_POLICY_SHA256, **payload}
    )
    if hypothesis["page_hypothesis_id"] != expected_id:
        raise _error("page hypothesis content identity drifted")
    return hypothesis


def _validate_block(
    value: Any,
    *,
    expected_rank: int,
    source_sha256: str,
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    block = _exact_dict(value, _BLOCK_FIELDS, "block hypothesis")
    if (
        block["rank"] != expected_rank
        or type(block["block_hypothesis_id"]) is not str
        or _BLOCK_HYPOTHESIS_ID_RE.fullmatch(block["block_hypothesis_id"]) is None
    ):
        raise _error("block hypothesis rank/identity drifted")
    start = _positive(block["start_input_ordinal"], "block start ordinal")
    end = _positive(block["end_input_ordinal"], "block end ordinal")
    if start > end or end >= len(pages):
        raise _error("block hypothesis page range drifted")
    members = list(pages[start - 1 : end])
    expected_ids = [page["page_hypothesis_id"] for page in members]
    expected_families = [page["family_hypothesis"] for page in members]
    expected_evidence = [page["evidence_codes"] for page in members]
    boundary = pages[end]
    if (
        block["member_page_hypothesis_ids"] != expected_ids
        or block["family_sequence_hypothesis"] != expected_families
        or block["family_evidence_codes"] != expected_evidence
        or block["tm_boundary_hypothesis_id"] != boundary["page_hypothesis_id"]
        or boundary["family_hypothesis"] != "TM"
        or not {"CDKT", "KQKD", "LCTT"} <= set(expected_families)
        or any(family not in {"CDKT", "KQKD", "LCTT"} for family in expected_families)
    ):
        raise _error("block hypothesis ordered family/page binding drifted")
    block_score = _finite(block["diagnostic_score"], "block diagnostic score")
    scores = _exact_dict(
        block["diagnostic_score_components"],
        _BLOCK_SCORE_FIELDS,
        "block diagnostic score components",
    )
    if (
        type(scores["start_form_signal"]) is not bool
        or type(scores["form_signal_page_count"]) is not int
        or scores["form_signal_page_count"] < 0
    ):
        raise _error("block diagnostic categorical/count receipt drifted")
    _finite(scores["average_family_confidence"], "block average family confidence")
    raw_average_confidence = sum(page["diagnostic_score"] for page in members) / len(members)
    expected_scores = {
        "start_form_signal": ("FORM_FAMILY_SIGNAL_HYPOTHESIS" in members[0]["evidence_codes"]),
        "form_signal_page_count": sum(
            "FORM_FAMILY_SIGNAL_HYPOTHESIS" in page["evidence_codes"] for page in members
        ),
        "average_family_confidence": round(raw_average_confidence, 6),
    }
    expected_block_score = round(
        _BLOCK_SCORE_WEIGHTS["start_form_signal"] * expected_scores["start_form_signal"]
        + _BLOCK_SCORE_WEIGHTS["form_signal_page_count"] * expected_scores["form_signal_page_count"]
        + _BLOCK_SCORE_WEIGHTS["average_family_confidence"] * raw_average_confidence,
        6,
    )
    if not same_typed_json_v1(scores, expected_scores) or block_score != expected_block_score:
        raise _error("block diagnostic score/components drifted from member page hypotheses")
    payload = {key: block[key] for key in block if key not in {"block_hypothesis_id", "rank"}}
    expected_id = "ssdv1:block-hypothesis:" + canonical_json_sha256_v1(
        {
            "source_sha256": source_sha256,
            "used_policy_sha256": _USED_POLICY_SHA256,
            **payload,
        }
    )
    if block["block_hypothesis_id"] != expected_id:
        raise _error("block hypothesis content identity drifted")
    return block


def _validate_document(value: Any, *, document_id: str) -> dict[str, Any]:
    document = _exact_dict(value, _DOCUMENT_FIELDS, "document hypothesis artifact")
    if (
        document["format_version"] != DOCUMENT_STATEMENT_HYPOTHESES_FORMAT_VERSION_V1
        or document["claim_boundary"] != DOCUMENT_STATEMENT_HYPOTHESES_CLAIM_BOUNDARY_V1
        or document["status"] not in _ARTIFACT_STATUSES
        or document["source_sha256"] != document_id.removeprefix("sha256:")
        or document["safety"] != _DOCUMENT_SAFETY
    ):
        raise _error("document hypothesis header/source/safety drifted")
    _validate_policy_receipt(document["locator_policy_receipt"])
    bindings_raw = document["page_projection_bindings"]
    pages_raw = document["page_hypotheses"]
    dispositions_raw = document["page_dispositions"]
    blocks_raw = document["block_hypotheses"]
    if (
        type(bindings_raw) is not list
        or not bindings_raw
        or type(pages_raw) is not list
        or type(dispositions_raw) is not list
        or type(blocks_raw) is not list
        or len(bindings_raw) != len(pages_raw)
        or len(bindings_raw) != len(dispositions_raw)
    ):
        raise _error("document hypothesis page/block arrays drifted")
    bindings = [
        _validate_binding(item, expected_ordinal=ordinal)
        for ordinal, item in enumerate(bindings_raw, start=1)
    ]
    pages = [
        _validate_page_hypothesis(item, binding=binding)
        for item, binding in zip(pages_raw, bindings, strict=True)
    ]
    if len({page["page_hypothesis_id"] for page in pages}) != len(pages):
        raise _error("document page hypothesis identities repeat")
    blocks = [
        _validate_block(
            item,
            expected_rank=rank,
            source_sha256=document["source_sha256"],
            pages=pages,
        )
        for rank, item in enumerate(blocks_raw, start=1)
    ]
    block_ids = {block["block_hypothesis_id"] for block in blocks}
    expected_block_order = sorted(
        blocks,
        key=lambda block: (
            -block["diagnostic_score"],
            block["start_input_ordinal"],
        ),
    )
    if (
        len(block_ids) != len(blocks)
        or len({block["start_input_ordinal"] for block in blocks}) != len(blocks)
        or [block["block_hypothesis_id"] for block in blocks]
        != [block["block_hypothesis_id"] for block in expected_block_order]
    ):
        raise _error("document block hypothesis identity/rank order drifted")
    cited_by_page = {page["page_hypothesis_id"]: [] for page in pages}
    for block in blocks:
        for page_id in [
            *block["member_page_hypothesis_ids"],
            block["tm_boundary_hypothesis_id"],
        ]:
            cited_by_page[page_id].append(block["block_hypothesis_id"])
    dispositions: list[dict[str, Any]] = []
    for binding, page, raw_disposition in zip(bindings, pages, dispositions_raw, strict=True):
        disposition = _exact_dict(
            raw_disposition,
            _PAGE_DISPOSITION_FIELDS,
            "page disposition",
        )
        expected_block_ids = cited_by_page[page["page_hypothesis_id"]]
        expected_primary = (
            "UPSTREAM_TERMINAL_UNRESOLVED"
            if binding["terminal"]
            else (
                "SUPPORTS_STATEMENT_BLOCK_HYPOTHESIS"
                if expected_block_ids
                else "RETAINED_UNRESOLVED"
            )
        )
        if disposition != {
            "input_ordinal": binding["input_ordinal"],
            "source_local_page_id": binding["source_local_page_id"],
            "page_hypothesis_id": page["page_hypothesis_id"],
            "primary_disposition": expected_primary,
            "block_hypothesis_ids": expected_block_ids,
        }:
            raise _error("page disposition no-drop/candidate binding drifted")
        dispositions.append(disposition)
    if document["status"] != (
        "CANDIDATES_EMITTED" if blocks else "UNRESOLVED_NO_COMPLETE_ORDERED_HYPOTHESIS"
    ):
        raise _error("document hypothesis status/count drifted")
    metrics = _exact_dict(document["metrics"], _DOCUMENT_METRIC_FIELDS, "document metrics")
    disposition_counts = Counter(item["primary_disposition"] for item in dispositions)
    family_counts = Counter(item["family_hypothesis"] for item in pages)
    evidence_counts = Counter(code for item in pages for code in item["evidence_codes"])
    expected_metrics = {
        "page_count": len(bindings),
        "terminal_page_count": sum(binding["terminal"] for binding in bindings),
        "block_hypothesis_count": len(blocks),
        "page_disposition_counts": {key: disposition_counts[key] for key in _PAGE_DISPOSITIONS},
        "family_hypothesis_counts": {key: family_counts[key] for key in _PAGE_FAMILIES},
        "evidence_code_counts": {key: evidence_counts[key] for key in _EVIDENCE_CODES},
    }
    if not same_typed_json_v1(metrics, expected_metrics):
        raise _error("document hypothesis exact metrics drifted")
    identity = document["document_hypotheses_identity"]
    if (
        type(identity) is not str
        or _DOCUMENT_HYPOTHESIS_ID_RE.fullmatch(identity) is None
        or identity
        != "ssdv1:document:"
        + canonical_json_sha256_v1(
            {key: document[key] for key in document if key != "document_hypotheses_identity"}
        )
    ):
        raise _error("document hypotheses logical identity drifted")
    return document


def _source_pages_by_document(
    source_inventory: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {
        document_id: [] for document_id in source_inventory["authority"]["document_ids"]
    }
    for page in source_inventory["pages"]:
        result[page["document_id"]].append(page)
    return result


def _cross_bind_documents(
    documents: Sequence[Mapping[str, Any]],
    source_inventory: Mapping[str, Any],
) -> None:
    grouped = _source_pages_by_document(source_inventory)
    document_ids = source_inventory["authority"]["document_ids"]
    for document_id, document in zip(document_ids, documents, strict=True):
        source_pages = grouped[document_id]
        bindings = document["page_projection_bindings"]
        if len(bindings) != len(source_pages):
            raise _error("document hypothesis/source inventory page denominator drifted")
        for binding, source_page in zip(bindings, source_pages, strict=True):
            if (
                binding["source_local_page_id"] != source_page["projection_identity"]
                or binding["source_projection_sha256"] != source_page["projection_sha256"]
                or binding["route"] != source_page["route"]
                or binding["upstream_status"] != source_page["status"]
                or binding["terminal"] != source_page["terminal"]
            ):
                raise _error("document page binding differs from compact source inventory")


def _rollup(documents: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(document["status"] for document in documents)
    disposition_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    evidence_counts: Counter[str] = Counter()
    for document in documents:
        metrics = document["metrics"]
        disposition_counts.update(metrics["page_disposition_counts"])
        family_counts.update(metrics["family_hypothesis_counts"])
        evidence_counts.update(metrics["evidence_code_counts"])
    page_count = sum(document["metrics"]["page_count"] for document in documents)
    return {
        "document_count": len(documents),
        "page_count": page_count,
        "terminal_page_count": sum(
            document["metrics"]["terminal_page_count"] for document in documents
        ),
        "page_hypothesis_count": page_count,
        "page_disposition_count": page_count,
        "block_hypothesis_count": sum(
            document["metrics"]["block_hypothesis_count"] for document in documents
        ),
        "candidate_document_count": status_counts["CANDIDATES_EMITTED"],
        "unresolved_document_count": status_counts["UNRESOLVED_NO_COMPLETE_ORDERED_HYPOTHESIS"],
        "artifact_status_counts": {key: status_counts[key] for key in _ARTIFACT_STATUSES},
        "page_disposition_counts": {key: disposition_counts[key] for key in _PAGE_DISPOSITIONS},
        "family_hypothesis_counts": {key: family_counts[key] for key in _PAGE_FAMILIES},
        "evidence_code_counts": {key: evidence_counts[key] for key in _EVIDENCE_CODES},
    }


def validate_wave1_document_statement_hypotheses_inventory_v1(
    value: Any,
    *,
    project_root: Path,
    source_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate canonical structure, committed producer bytes, and no-drop sums.

    This standalone validator cannot recompute page-family diagnostics without
    the deliberately unpersisted projection text. Downstream consumers must
    therefore pin the exact raw artifact SHA-256 returned by the publisher;
    the inventory's self-hash is only canonical structural integrity.
    """

    try:
        source = validate_wave1_source_inventory_v1(source_inventory)
    except ValueError as exc:
        raise _error("compact source inventory authority is invalid") from exc
    if source["authority"]["aggregate_identity_sha256"] == _FINALIZED_AGGREGATE_IDENTITY_SHA256:
        source_payload = canonical_json_bytes_v1(source)
        if (
            len(source_payload) != _SOURCE_INVENTORY_SIZE_BYTES
            or sha256(source_payload).hexdigest() != _SOURCE_INVENTORY_SHA256
            or source["inventory_identity_sha256"] != _SOURCE_INVENTORY_IDENTITY_SHA256
        ):
            raise _error("supplied compact source inventory differs from its exact artifact pin")
    inventory = _exact_dict(value, _TOP_LEVEL_FIELDS, "statement hypothesis inventory")
    if (
        inventory["format_version"]
        != WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_INVENTORY_FORMAT_VERSION_V1
        or inventory["claim_boundary"]
        != WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_INVENTORY_CLAIM_BOUNDARY_V1
        or inventory["status"] != _FORMAT_STATUS
        or inventory["safety"] != _SAFETY
    ):
        raise _error("statement hypothesis inventory header/safety drifted")
    authority = _validate_authority(inventory["authority"], source)
    _validate_producer(inventory["producer"], project_root=project_root)
    documents_raw = inventory["documents"]
    document_ids = authority["finalized_v3"]["document_ids"]
    if type(documents_raw) is not list or len(documents_raw) != len(document_ids):
        raise _error("statement hypothesis document denominator drifted")
    documents = [
        _validate_document(document, document_id=document_id)
        for document_id, document in zip(document_ids, documents_raw, strict=True)
    ]
    _cross_bind_documents(documents, source)
    corpus_metrics = _exact_dict(
        inventory["corpus_metrics"],
        _CORPUS_METRIC_FIELDS,
        "statement hypothesis corpus metrics",
    )
    expected_metrics = _rollup(documents)
    if not same_typed_json_v1(corpus_metrics, expected_metrics):
        raise _error("statement hypothesis corpus accounting drifted")
    if authority["finalized_v3"][
        "aggregate_identity_sha256"
    ] == _FINALIZED_AGGREGATE_IDENTITY_SHA256 and not same_typed_json_v1(
        corpus_metrics, _FINALIZED_CORPUS_METRICS
    ):
        raise _error("finalized blind statement-hypothesis baseline drifted")
    if (
        corpus_metrics["document_count"] != authority["finalized_v3"]["document_count"]
        or corpus_metrics["page_count"] != authority["finalized_v3"]["request_count"]
        or corpus_metrics["page_count"] != source["corpus_metrics"]["page_count"]
        or corpus_metrics["terminal_page_count"] != source["corpus_metrics"]["terminal_page_count"]
        or sum(corpus_metrics["artifact_status_counts"].values())
        != corpus_metrics["document_count"]
        or sum(corpus_metrics["page_disposition_counts"].values()) != corpus_metrics["page_count"]
        or sum(corpus_metrics["family_hypothesis_counts"].values()) != corpus_metrics["page_count"]
    ):
        raise _error("statement hypothesis authority/no-drop denominator drifted")
    identity = _sha(inventory["inventory_identity_sha256"], "inventory identity")
    if identity != canonical_json_sha256_v1(
        {key: inventory[key] for key in inventory if key != "inventory_identity_sha256"}
    ):
        raise _error("statement hypothesis inventory logical identity drifted")
    return canonical_clone_v1(inventory)


def _finish_document(
    projections: Sequence[Mapping[str, Any]],
    *,
    locator_policy: Mapping[str, Any],
) -> dict[str, Any]:
    artifact = build_document_statement_block_hypotheses_v1(
        projections,
        locator_policy=locator_policy,
    )
    if artifact["locator_policy_receipt"]["used_policy_sha256"] != _USED_POLICY_SHA256:
        raise _error("document hypothesis normalized policy identity drifted")
    return artifact


def _build_documents(
    project_root: Path,
    *,
    source_inventory: Mapping[str, Any],
    locator_policy: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], FinalizedV3SurveyAuthority]:
    source_pages = source_inventory["pages"]
    documents: list[dict[str, Any]] = []
    current_source: str | None = None
    current_projections: list[dict[str, Any]] = []
    closed_sources: set[str] = set()
    delivered = 0
    with open_finalized_v3_survey_stream_v1(project_root) as stream:
        authority = stream.authority
        for authenticated_page in stream:
            delivered += 1
            if delivered > len(source_pages):
                raise _error("finalized V3 stream exceeded compact inventory denominator")
            record = authenticated_page.page_record
            source_page = source_pages[delivered - 1]
            projection = project_authenticated_page_v2(
                page_record=record,
                page_result=authenticated_page.page_result,
            )
            source_sha256 = projection["source_locator"]["source_sha256"]
            if (
                record["request_ordinal"] != delivered
                or record["document_id"] != source_page["document_id"]
                or record["physical_page"] != source_page["physical_page"]
                or record["document_id"] != f"sha256:{source_sha256}"
                or projection["source_local_page_id"] != source_page["projection_identity"]
                or canonical_json_sha256_v1(projection) != source_page["projection_sha256"]
                or projection["route"] != source_page["route"]
                or projection["upstream_status"] != source_page["status"]
                or projection["terminal"] != source_page["terminal"]
            ):
                raise _error("finalized stream page differs from compact source inventory")
            if current_source is None:
                current_source = source_sha256
            elif source_sha256 != current_source:
                if source_sha256 in closed_sources:
                    raise _error("finalized stream document source is not contiguous")
                documents.append(
                    _finish_document(current_projections, locator_policy=locator_policy)
                )
                closed_sources.add(current_source)
                current_source = source_sha256
                current_projections = []
            current_projections.append(projection)
        if current_source is not None:
            documents.append(_finish_document(current_projections, locator_policy=locator_policy))
            closed_sources.add(current_source)
    if delivered != len(source_pages) or delivered != authority.request_count:
        raise _error("finalized V3 stream was not consumed at its exact denominator")
    observed_document_ids = [f"sha256:{document['source_sha256']}" for document in documents]
    if observed_document_ids != list(authority.document_ids):
        raise _error("finalized V3 stream document order/coverage drifted")
    return documents, authority


def build_wave1_document_statement_hypotheses_inventory_v1(
    project_root: Path,
) -> dict[str, Any]:
    """Build, validate, and return the one finalized candidate inventory."""

    project_root = project_root.resolve()
    producer_before = _producer_receipt(project_root)
    source_before = _load_source_inventory(project_root)
    policy_before = _load_locator_policy(project_root)
    documents, authority = _build_documents(
        project_root,
        source_inventory=source_before,
        locator_policy=policy_before,
    )
    source_after = _load_source_inventory(project_root)
    policy_after = _load_locator_policy(project_root)
    producer_after = _producer_receipt(project_root)
    if not same_typed_json_v1(source_before, source_after):
        raise _error("compact source inventory changed during hypothesis construction")
    if not same_typed_json_v1(policy_before, policy_after):
        raise _error("statement locator policy changed during hypothesis construction")
    if not same_typed_json_v1(producer_before, producer_after):
        raise _error("statement hypothesis producer changed during construction")
    inventory = {
        "format_version": WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_INVENTORY_FORMAT_VERSION_V1,
        "claim_boundary": WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_INVENTORY_CLAIM_BOUNDARY_V1,
        "status": _FORMAT_STATUS,
        "authority": {
            "finalized_v3": _authority_payload(authority),
            "source_inventory": _source_inventory_authority(),
            "locator_policy": _locator_policy_authority(),
        },
        "documents": documents,
        "corpus_metrics": _rollup(documents),
        "producer": producer_before,
        "safety": canonical_clone_v1(_SAFETY),
    }
    inventory["inventory_identity_sha256"] = canonical_json_sha256_v1(inventory)
    return validate_wave1_document_statement_hypotheses_inventory_v1(
        inventory,
        project_root=project_root,
        source_inventory=source_before,
    )


def _open_output_directory(project_root: Path) -> tuple[Path, int]:
    relative_parent = WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_OUTPUT_RELATIVE_PATH_V1.parent
    descriptor = os.open(
        project_root,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0),
    )
    try:
        for part in relative_parent.parts:
            child = os.open(
                part,
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        identity = os.fstat(descriptor)
        if not stat.S_ISDIR(identity.st_mode):
            raise _error("statement hypothesis output parent is not a directory")
    except Exception:
        os.close(descriptor)
        raise
    return project_root / relative_parent, descriptor


def _require_destination_absent(project_root: Path) -> None:
    _parent, directory_fd = _open_output_directory(project_root)
    try:
        try:
            os.stat(
                WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_OUTPUT_RELATIVE_PATH_V1.name,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return
        raise _error("statement hypothesis inventory destination already exists")
    finally:
        os.close(directory_fd)


def _read_regular_at(directory_fd: int, filename: str) -> tuple[bytes, os.stat_result]:
    descriptor = os.open(
        filename,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=directory_fd,
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error("published statement hypothesis inventory is not regular")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        named = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
    finally:
        os.close(descriptor)
    token = lambda item: (  # noqa: E731 - compact immutable identity token
        item.st_dev,
        item.st_ino,
        stat.S_IFMT(item.st_mode),
        stat.S_IMODE(item.st_mode),
        item.st_nlink,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if token(before) != token(after) or token(after) != token(named):
        raise _error("published statement hypothesis inventory changed during validation")
    return b"".join(chunks), after


def _publish_canonical_exclusive(project_root: Path, payload: bytes) -> Path:
    if not payload.endswith(b"\n") or payload.endswith(b"\n\n"):
        raise _error("statement hypothesis publication is not canonical newline JSON")
    try:
        decode_canonical_json_bytes_v1(payload)
    except ValueError as exc:
        raise _error("statement hypothesis publication bytes are not canonical JSON") from exc
    parent, directory_fd = _open_output_directory(project_root)
    filename = WAVE1_DOCUMENT_STATEMENT_HYPOTHESES_OUTPUT_RELATIVE_PATH_V1.name
    temporary_pattern = re.compile(rf"^\.{re.escape(filename)}\.[0-9a-f]{{32}}\.tmp$")
    temporary_name = f".{filename}.{secrets.token_hex(16)}.tmp"
    descriptor = -1
    owned_identity: tuple[int, int] | None = None
    final_linked = False
    publication_committed = False
    try:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        if any(temporary_pattern.fullmatch(name) for name in os.listdir(directory_fd)):
            raise _error("statement hypothesis publication temporary already exists")
        try:
            os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise _error("statement hypothesis inventory destination already exists")
        try:
            descriptor = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
        except FileExistsError as exc:
            raise _error("statement hypothesis temporary publication collided") from exc
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise _error("owned statement hypothesis publication identity drifted")
        owned_identity = (opened.st_dev, opened.st_ino)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise _error("statement hypothesis publication write made no progress")
            offset += written
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o444)
        os.fsync(descriptor)
        final_open = os.fstat(descriptor)
        if (
            not stat.S_ISREG(final_open.st_mode)
            or stat.S_IMODE(final_open.st_mode) != 0o444
            or final_open.st_nlink != 1
            or final_open.st_size != len(payload)
        ):
            raise _error("statement hypothesis sealed temporary identity drifted")
        try:
            os.link(
                temporary_name,
                filename,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            raise _error(
                "statement hypothesis inventory publication lost its exclusive race"
            ) from exc
        final_linked = True
        linked = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
        temporary = os.stat(temporary_name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            (linked.st_dev, linked.st_ino) != owned_identity
            or (temporary.st_dev, temporary.st_ino) != owned_identity
            or stat.S_IMODE(linked.st_mode) != 0o444
            or linked.st_nlink != 2
            or temporary.st_nlink != 2
            or linked.st_size != len(payload)
        ):
            raise _error("linked statement hypothesis publication identity drifted")
        os.fsync(directory_fd)
        publication_committed = True
        os.unlink(temporary_name, dir_fd=directory_fd)
        os.fsync(directory_fd)
        published, identity = _read_regular_at(directory_fd, filename)
        if (
            published != payload
            or stat.S_IMODE(identity.st_mode) != 0o444
            or identity.st_nlink != 1
            or any(temporary_pattern.fullmatch(name) for name in os.listdir(directory_fd))
        ):
            raise _error("published statement hypothesis inventory bytes/topology drifted")
    except OSError as exc:
        raise _error("statement hypothesis inventory publication failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if final_linked and not publication_committed and owned_identity is not None:
            try:
                observed_final = os.stat(
                    filename,
                    dir_fd=directory_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                observed_final = None
            if (
                observed_final is not None
                and (observed_final.st_dev, observed_final.st_ino) == owned_identity
            ):
                os.unlink(filename, dir_fd=directory_fd)
                os.fsync(directory_fd)
        if owned_identity is not None:
            try:
                observed = os.stat(
                    temporary_name,
                    dir_fd=directory_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                observed = None
            if observed is not None and (observed.st_dev, observed.st_ino) == owned_identity:
                os.unlink(temporary_name, dir_fd=directory_fd)
                os.fsync(directory_fd)
        os.close(directory_fd)
    return parent / filename


def publish_wave1_document_statement_hypotheses_inventory_v1(
    project_root: Path,
) -> tuple[Path, str, int, str]:
    """Build and exclusively publish the canonical finalized inventory once."""

    project_root = project_root.resolve()
    _require_destination_absent(project_root)
    inventory = build_wave1_document_statement_hypotheses_inventory_v1(project_root)
    source_inventory = _load_source_inventory(project_root)
    validate_wave1_document_statement_hypotheses_inventory_v1(
        inventory,
        project_root=project_root,
        source_inventory=source_inventory,
    )
    if not same_typed_json_v1(_producer_receipt(project_root), inventory["producer"]):
        raise _error("statement hypothesis producer changed before publication")
    _load_locator_policy(project_root)
    payload = canonical_json_bytes_v1(inventory)
    path = _publish_canonical_exclusive(project_root, payload)
    return (
        path,
        sha256(payload).hexdigest(),
        len(payload),
        inventory["inventory_identity_sha256"],
    )
