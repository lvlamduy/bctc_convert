"""Independent, replay-bound verification for local-accounting schema items.

The request is assembled only after the authenticated semantic graph, visible
statement context, schema-candidate seam, and independent numeric challenger
have replayed.  A reviewer can record PASS/FAIL checks, but cannot provide a
final item status.  The final ``VERIFIED_BY_CODEX``/``UNRESOLVED`` decision is
derived mechanically from the closed check denominator.

This first version intentionally supports the strict loan-maturity core used
to calibrate SHB page 24.  It grants a bounded mapping-verification claim for
the exact source observations only.  The unlabeled total remains source-only,
and schema near-neighbours remain unresolved.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
import weakref
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, cast

from bctc_ai.evaluation.semantic_graph_numeric_proposal_receipt_v1 import (
    _validate_result as _validate_numeric_verification_result,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    _authority_snapshot,
    validate_semantic_local_accounting_schema_candidate_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.local_accounting_graph_v1 import FamilySpecV1
from bctc_ai.source_structure.semantic_local_accounting_graph_v2 import (
    validate_semantic_local_accounting_graph_replay_v2,
)
from bctc_ai.source_structure.semantic_statement_context_v1 import (
    validate_semantic_statement_context_replay_v1,
)

__all__ = [
    "REQUEST_FORMAT_VERSION",
    "REVIEW_FORMAT_VERSION",
    "VERIFICATION_FORMAT_VERSION",
    "CodexMappedItemVerificationV1Error",
    "AuthenticatedCodexMappedItemVerificationRequestV1",
    "AuthenticatedCodexMappedItemReviewV1",
    "build_codex_mapped_item_verification_request_v1",
    "validate_codex_mapped_item_verification_request_replay_v1",
    "build_codex_mapped_item_review_v1",
    "authenticate_codex_mapped_item_review_v1",
    "validate_codex_mapped_item_review_v1",
    "assemble_codex_mapped_item_verification_v1",
    "validate_codex_mapped_item_verification_replay_v1",
]


REQUEST_FORMAT_VERSION = "CODEX_MAPPED_ITEM_VERIFICATION_REQUEST_V1"
REVIEW_FORMAT_VERSION = "CODEX_MAPPED_ITEM_SOURCE_REVIEW_V1"
VERIFICATION_FORMAT_VERSION = "CODEX_MAPPED_ITEM_VERIFICATION_V1"

REQUEST_STATE = "FROZEN_BEFORE_CODEX_REVIEW"
REVIEW_STATE = "INDEPENDENT_CODEX_SOURCE_REVIEW_COMPLETE"
VERIFICATION_STATE = "CODEX_MAPPED_ITEM_VERIFICATION_ASSEMBLED"

REQUEST_CLAIM_BOUNDARY = (
    "REPLAY_BOUND_SOURCE_SCHEMA_AND_NUMERIC_EVIDENCE_REQUEST_ONLY_NO_CODEX_DECISION_"
    "ACCEPTED_MAPPING_CANONICALIZATION_VALUE_MATERIALIZATION_ABSENCE_EXPORT_OR_PRODUCTION_"
    "AUTHORITY"
)
REVIEW_CLAIM_BOUNDARY = (
    "INDEPENDENT_CODEX_PIXEL_AND_SOURCE_REVIEW_ASSERTIONS_BOUND_TO_ONE_FROZEN_REQUEST_"
    "ONLY_NO_CALLER_SET_FINAL_STATUS_NO_WHOLE_DOCUMENT_ABSENCE_CANONICALIZATION_EXPORT_"
    "OR_PRODUCTION_AUTHORITY"
)
VERIFICATION_CLAIM_BOUNDARY = (
    "DERIVED_INDEPENDENT_CODEX_VERIFICATION_OF_EXACT_BOUND_SOURCE_OBSERVATION_TO_EXACT_"
    "REPORTNORMID_ONLY_SOURCE_TOTAL_REMAINS_UNMAPPED_NO_WHOLE_DOCUMENT_ABSENCE_"
    "CANONICALIZATION_VALUE_MATERIALIZATION_ACCOUNTING_TRUTH_EXPORT_OR_PRODUCTION_AUTHORITY"
)

VERIFIED = "VERIFIED_BY_CODEX"
UNRESOLVED = "UNRESOLVED"
MAPPED_SCHEMA_ROW = "MAPPED_SCHEMA_ROW"
SOURCE_ONLY_VALIDATION = "SOURCE_ONLY_VALIDATION"

_SUPPORTED_FAMILY_ID = "LOAN_MATURITY_BUCKETS"
_SUPPORTED_ROLES = ("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "TOTAL")
_SUPPORTED_SCHEMA_IDS = {
    "SHORT_TERM": 753,
    "MEDIUM_TERM": 754,
    "LONG_TERM": 755,
}
_NEAR_NEIGHBOUR_IDS = (5747, 1944)

_PINNED_NUMERIC_RELATIVE_PATH = Path(
    "docs/experiments/E-0042-shb-maturity-numeric-verification.json"
)
_PINNED_NUMERIC_SHA256 = "929c1c81b0e08e14b5908087d866dc7bacc67c19cc62eb832353c5efb6c1801e"
_PINNED_NUMERIC_SIZE_BYTES = 18_835
_PINNED_NUMERIC_VERIFICATION_ID = (
    "sgnpvv1:verification:92b2d1d0ad293fb5ee2953128db9fb93c1c7f588eefff1bc00cfdeae16b61f1d"
)
_PINNED_REVIEW_RELATIVE_PATH = Path(
    "docs/experiments/E-0045-shb-maturity-codex-independent-review.json"
)
# Filled from the externally selected UTF-8 review artifact below.  These are
# deliberately source constants rather than caller-supplied expected values.
_PINNED_REVIEW_SHA256 = "ad6b1c11419ca5911f1613d05aeb12daf8b2ae08b47e372b0ff6896813010778"
_PINNED_REVIEW_SIZE_BYTES = 18_158
_PINNED_REVIEW_ID = (
    "codexmirv1:review:8e1f41013a9d950f70f57abb9f2166585eca75659de1735dc0dd0cb7684f43b1"
)

_TABLE_CHECKS = (
    "SOURCE_BYTES_AND_PAGE",
    "AUTHENTICATED_PIXEL_BINDING",
    "ROLE_A_FIREWALL",
    "STATEMENT_TYPE_SCOPE",
    "OWNER_BRANCH_LOCALITY",
    "AXIS_PERIOD_IDENTITY_AND_ORDER",
    "PER_AXIS_UNIT_SCOPE",
    "OPTIONAL_ROW_POPULATION_BOUNDARY",
    "ARITHMETIC_CLOSURE",
    "PROVENANCE_COMPLETENESS",
)
_MAPPED_ITEM_CHECKS = (
    "ROW_LABEL_TYPED_ROLE",
    "ROW_VALUE_GEOMETRY",
    "NUMERIC_DIGIT_AND_SIGN_AGREEMENT",
    "SCHEMA_NAMESPACE_PARENT_ANCESTOR",
    "SCHEMA_SINGLETON_AND_MAPPING_ELIGIBILITY",
    "SIBLING_DISPLAY_ORDER",
    "NO_DUPLICATE_ROLE_OR_ID",
)
_SOURCE_ONLY_CHECKS = (
    "ROW_VALUE_GEOMETRY",
    "NUMERIC_DIGIT_AND_SIGN_AGREEMENT",
    "TOTAL_SCOPE",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FALSIFIER = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")

_REQUEST_SAFETY = {
    "upstream_exact_replay_required": True,
    "role_a_or_human_answer_used": False,
    "history_or_mongodb_used": False,
    "bank_page_note_identity_used_for_routing": False,
    "caller_final_status_allowed": False,
    "accepted_mapping_authority": False,
    "whole_document_absence_authority": False,
    "canonicalization_authority": False,
    "value_materialization_authority": False,
    "export_authority": False,
    "production_authority": False,
}

_REVIEW_ACCESS = {
    "frozen_request_opened": True,
    "authenticated_source_pdf_and_render_inspected": True,
    "role_a_opened": False,
    "human_review_answer_opened": False,
    "history_or_mongodb_opened": False,
    "holdout_answer_opened": False,
    "final_status_supplied_by_reviewer": False,
}

_VERIFICATION_SAFETY = {
    "final_status_derived_from_closed_checks": True,
    "source_only_total_report_norm_id_is_null": True,
    "near_neighbours_remain_unresolved": True,
    "whole_document_absence_claimed": False,
    "canonicalization_authority": False,
    "value_materialization_authority": False,
    "accounting_truth_beyond_enumerated_local_closure": False,
    "export_authority": False,
    "production_authority": False,
}

_MINT_TOKEN = object()


class CodexMappedItemVerificationV1Error(ValueError):
    """An upstream authority, review assertion, or derived verdict drifted."""


class AuthenticatedCodexMappedItemVerificationRequestV1:
    """Opaque live authority minted only after exact upstream/source replay."""

    __slots__ = ("__weakref__",)

    def __init__(self, token: object) -> None:
        if token is not _MINT_TOKEN:
            raise _error("authenticated verification request cannot be caller-constructed")

    def __copy__(self) -> None:
        raise _error("authenticated verification request cannot be copied")

    def __deepcopy__(self, _memo: object) -> None:
        raise _error("authenticated verification request cannot be deep-copied")

    def __reduce__(self) -> None:
        raise _error("authenticated verification request cannot be serialized")


class AuthenticatedCodexMappedItemReviewV1:
    """Opaque authority for one exact externally selected Codex review."""

    __slots__ = ("__weakref__",)

    def __init__(self, token: object) -> None:
        if token is not _MINT_TOKEN:
            raise _error("authenticated Codex review cannot be caller-constructed")

    def __copy__(self) -> None:
        raise _error("authenticated Codex review cannot be copied")

    def __deepcopy__(self, _memo: object) -> None:
        raise _error("authenticated Codex review cannot be deep-copied")

    def __reduce__(self) -> None:
        raise _error("authenticated Codex review cannot be serialized")


_REQUEST_RECEIPTS: weakref.WeakKeyDictionary[
    AuthenticatedCodexMappedItemVerificationRequestV1, tuple[bytes, str]
] = weakref.WeakKeyDictionary()
_REVIEW_RECEIPTS: weakref.WeakKeyDictionary[
    AuthenticatedCodexMappedItemReviewV1, tuple[bytes, str, str]
] = weakref.WeakKeyDictionary()


def _error(message: str) -> CodexMappedItemVerificationV1Error:
    return CodexMappedItemVerificationV1Error(message)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return cast(dict[str, Any], value)


def _exact_sha256(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise _error(f"{label} is not one exact lowercase SHA-256")
    return value


def _exact_digest_identity(value: Any, prefix: str, label: str) -> str:
    if (
        type(value) is not str
        or not value.startswith(prefix)
        or _SHA256.fullmatch(value.removeprefix(prefix)) is None
    ):
        raise _error(f"{label} identity drifted")
    return value


def _closed_json_object(payload: bytes, label: str) -> dict[str, Any]:
    if type(payload) is not bytes or not payload:
        raise _error(f"{label} must be non-empty exact bytes")

    def reject_constant(value: str) -> None:
        raise _error(f"{label} contains non-finite constant {value}")

    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _error(f"{label} contains duplicate key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicate,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise _error(f"cannot decode {label} as strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} must be one JSON object")
    return cast(dict[str, Any], value)


def _stable_nofollow_bytes(root: Path, relative: Path | str, label: str) -> bytes:
    raw = Path(relative)
    if raw.is_absolute() or not raw.parts or ".." in raw.parts:
        raise _error(f"{label} path must be safe and project-relative")
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        current = os.open(root, directory_flags)
    except OSError as exc:
        raise _error(f"cannot open project root for {label}") from exc
    descriptor: int | None = None
    try:
        for part in raw.parts[:-1]:
            following = os.open(part, directory_flags, dir_fd=current)
            os.close(current)
            current = following
        descriptor = os.open(raw.parts[-1], file_flags, dir_fd=current)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error(f"{label} is not a regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)

        def identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
            return (
                value.st_dev,
                value.st_ino,
                value.st_mode,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
            )

        if identity(before) != identity(after):
            raise _error(f"{label} changed during stable read")
        payload = b"".join(chunks)
        if len(payload) != before.st_size:
            raise _error(f"{label} stable read size drifted")
        return payload
    except OSError as exc:
        raise _error(f"cannot stably read nofollow {label}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(current)


def _safe_file(root: Path, relative: Path | str, label: str) -> tuple[Path, bytes, dict[str, Any]]:
    raw = Path(relative)
    payload = _stable_nofollow_bytes(root, raw, label)
    path = root / raw
    return (
        path,
        payload,
        {
            "path": raw.as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
    )


def _assert_pin(root: Path, record: Any, label: str) -> tuple[Path, bytes]:
    pin = _exact_dict(record, set(record) if type(record) is dict else set(), label)
    if not {"path", "sha256", "size_bytes"} <= set(pin):
        raise _error(f"{label} lacks path/hash/size")
    path, payload, actual = _safe_file(root, pin["path"], label)
    if actual["sha256"] != pin["sha256"] or actual["size_bytes"] != pin["size_bytes"]:
        raise _error(f"{label} is hash- or size-drifted")
    return path, payload


def _minted(value: Mapping[str, Any], id_key: str, prefix: str, label: str) -> None:
    clone = canonical_clone_v1(value)
    identity = clone.pop(id_key, None)
    if identity != f"{prefix}{canonical_json_sha256_v1(clone)}":
        raise _error(f"{label} identity drifted")


def _request_payload(
    receipt: AuthenticatedCodexMappedItemVerificationRequestV1,
) -> dict[str, Any]:
    if type(receipt) is not AuthenticatedCodexMappedItemVerificationRequestV1:
        raise _error("verification requires one exact authenticated request receipt")
    stored = _REQUEST_RECEIPTS.get(receipt)
    if stored is None:
        raise _error("verification request receipt is unknown or expired")
    payload, digest = stored
    if hashlib.sha256(payload).hexdigest() != digest:
        raise _error("authenticated verification request receipt bytes drifted")
    decoded = decode_canonical_json_bytes_v1(payload)
    return _validate_request(decoded)


def _mint_request_receipt(
    request: Mapping[str, Any],
) -> AuthenticatedCodexMappedItemVerificationRequestV1:
    payload = canonical_json_bytes_v1(_validate_request(request))
    receipt = AuthenticatedCodexMappedItemVerificationRequestV1(_MINT_TOKEN)
    _REQUEST_RECEIPTS[receipt] = (payload, hashlib.sha256(payload).hexdigest())
    return receipt


def _review_payload(
    receipt: AuthenticatedCodexMappedItemReviewV1,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    if type(receipt) is not AuthenticatedCodexMappedItemReviewV1:
        raise _error("verification requires one exact authenticated Codex review receipt")
    stored = _REVIEW_RECEIPTS.get(receipt)
    if stored is None:
        raise _error("Codex review receipt is unknown or expired")
    payload, digest, request_id = stored
    if hashlib.sha256(payload).hexdigest() != digest or request_id != request["request_id"]:
        raise _error("authenticated Codex review receipt bytes/request binding drifted")
    decoded = decode_canonical_json_bytes_v1(payload)
    return _validate_review(decoded, request)


def _mint_review_receipt(
    review: Mapping[str, Any], request: Mapping[str, Any]
) -> AuthenticatedCodexMappedItemReviewV1:
    validated = _validate_review(review, request)
    payload = canonical_json_bytes_v1(validated)
    receipt = AuthenticatedCodexMappedItemReviewV1(_MINT_TOKEN)
    _REVIEW_RECEIPTS[receipt] = (
        payload,
        hashlib.sha256(payload).hexdigest(),
        request["request_id"],
    )
    return receipt


def _node_map(graph: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    nodes = graph.get("nodes")
    if type(nodes) is not list:
        raise _error("semantic graph contains no nodes")
    result = {node["node_id"]: node for node in nodes if type(node) is dict}
    if len(result) != len(nodes):
        raise _error("semantic graph repeats or corrupts a node identity")
    return result


def _atoms(source: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    neutral = source.get("neutral_page_v1")
    records = neutral.get("atoms") if type(neutral) is dict else None
    if type(records) is not list:
        raise _error("source projection contains no neutral atoms")
    result = {
        atom["source_local_id"]: atom
        for atom in records
        if type(atom) is dict and atom.get("kind") == "LINE"
    }
    if not result:
        raise _error("source projection contains no authenticated LINE atoms")
    return result


def _evidence_by_atom(graph: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for node in graph["nodes"]:
        if node["kind"] != "EVIDENCE":
            continue
        atom_ids = node["source_ref"]["source_atom_ids"]
        if type(atom_ids) is not list or len(atom_ids) != 1 or atom_ids[0] in result:
            raise _error("graph evidence is not one-to-one with source atoms")
        result[atom_ids[0]] = node
    return result


def _span_refs(
    node: Mapping[str, Any],
    atoms: Mapping[str, Mapping[str, Any]],
    evidence: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for atom_id in node["source_ref"]["source_atom_ids"]:
        atom = atoms.get(atom_id)
        support = evidence.get(atom_id)
        if atom is None or support is None:
            raise _error("graph node lacks authenticated atom/evidence support")
        line_index = atom.get("upstream_locator", {}).get("line_index")
        attributes = support["attributes"]
        if attributes["source_line_index"] != line_index:
            raise _error("graph evidence line index differs from authenticated atom")
        refs.append(
            {
                "source_atom_id": atom_id,
                "source_evidence_node_id": support["node_id"],
                "source_line_index": line_index,
                "raw_text_utf8": attributes["raw_text_utf8"],
                "text_source": attributes["text_source"],
                "pixel_bbox": canonical_clone_v1(atom["pixel_bbox"]),
                "canonical_bbox_mpt": canonical_clone_v1(atom["canonical_bbox_mpt"]),
            }
        )
    return refs


def _ancestor_ids(by_id: Mapping[int, Any], schema_id: int) -> list[int]:
    result: list[int] = []
    parent = by_id[schema_id].parent_id
    while parent is not None:
        if parent in result or parent not in by_id:
            raise _error("schema ancestor chain is cyclic or incomplete")
        result.append(parent)
        parent = by_id[parent].parent_id
    return result


def _decimal(value: Any, label: str) -> Decimal:
    if type(value) is not str:
        raise _error(f"{label} is not one canonical decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise _error(f"{label} is invalid") from exc
    if not parsed.is_finite() or str(parsed) != value:
        raise _error(f"{label} is not canonical")
    return parsed


def _validate_numeric_input(
    root: Path,
    payload: bytes,
    graph: Mapping[str, Any],
    source_projection: Mapping[str, Any],
    semantic_binding: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Mapping[str, Any]], dict[str, Any]]:
    if (
        len(payload) != _PINNED_NUMERIC_SIZE_BYTES
        or hashlib.sha256(payload).hexdigest() != _PINNED_NUMERIC_SHA256
    ):
        raise _error("numeric verification is not the fixed sealed E-0042 trust root")
    raw = _closed_json_object(payload, "independent numeric verification")
    try:
        verification = _validate_numeric_verification_result(raw)
    except ValueError as exc:
        raise _error("independent numeric verification contract or identity drifted") from exc
    inputs = verification["inputs"]
    if inputs["semantic_graph"] != {
        "graph_id": graph["graph_id"],
        "sha256": canonical_json_sha256_v1(graph),
    }:
        raise _error("numeric verification belongs to another semantic graph")
    if inputs["source_projection_sha256"] != canonical_json_sha256_v1(source_projection) or inputs[
        "semantic_page_binding_sha256"
    ] != canonical_json_sha256_v1(semantic_binding):
        raise _error("numeric verification source/binding lineage drifted")
    if (
        verification["verification_id"] != _PINNED_NUMERIC_VERIFICATION_ID
        or verification["status"] != "COMPLETE_WITH_EXACT_EIGHT_CELL_AGREEMENT"
    ):
        raise _error("numeric verification is not the fixed complete E-0042 authority")
    for name, pin in inputs["pins"].items():
        _assert_pin(root, pin, f"numeric {name} pin")
    registry_pin = inputs["pins"]["registry"]
    registry_path, registry_bytes = _assert_pin(root, registry_pin, "numeric registry pin")
    registry = _closed_json_object(registry_bytes, "numeric crop registry")
    registry_cells = registry.get("cells")
    if type(registry_cells) is not list:
        raise _error("numeric crop registry contains no cells")
    by_cell_id: dict[str, Mapping[str, Any]] = {}
    for cell in registry_cells:
        if type(cell) is not dict or type(cell.get("cell_id")) is not str:
            raise _error("numeric crop registry cell is invalid")
        if cell["cell_id"] in by_cell_id:
            raise _error("numeric crop registry repeats a cell")
        crop_relative = Path(cell["crop_path"])
        if crop_relative.is_absolute() or ".." in crop_relative.parts:
            raise _error("numeric crop path is unsafe")
        crop_path = registry_path.parent / crop_relative
        try:
            project_relative_crop = crop_path.relative_to(root)
        except ValueError as exc:
            raise _error("numeric crop escapes the project root") from exc
        _, _, crop_ref = _safe_file(root, project_relative_crop, "numeric crop")
        if (
            crop_ref["sha256"] != cell["crop_sha256"]
            or crop_ref["size_bytes"] != cell["crop_size_bytes"]
        ):
            raise _error("numeric crop is missing, hash-drifted, or size-drifted")
        by_cell_id[cell["cell_id"]] = cell
    return (
        verification,
        by_cell_id,
        {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "verification_id": verification["verification_id"],
            "path": _PINNED_NUMERIC_RELATIVE_PATH.as_posix(),
        },
    )


def _build_request_payload(
    root: Path,
    graph: Mapping[str, Any],
    candidate: Mapping[str, Any],
    context: Mapping[str, Any],
    numeric_bytes: bytes,
    source: Mapping[str, Any],
    binding: Mapping[str, Any],
    source_pdf_path: Path | str,
    target_page_render_path: Path | str,
) -> dict[str, Any]:
    if graph["status"] != "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE":
        raise _error("Codex verification requires one accepted source graph")
    if graph["family_id"] != _SUPPORTED_FAMILY_ID:
        raise _error("verification v1 supports only the loan-maturity calibration family")
    if candidate["status"] != "CANDIDATE_SET_READY":
        raise _error("schema candidate set is not ready")
    if context["status"] != "RESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT":
        raise _error("visible page statement context is unresolved")

    _source_pdf, source_pdf_bytes, pdf_ref = _safe_file(root, source_pdf_path, "source PDF")
    _render, render_bytes, render_ref = _safe_file(
        root, target_page_render_path, "target page render"
    )
    locator = source["source_locator"]
    page_record = source["page_record_v2"]
    if (
        pdf_ref["sha256"] != locator["source_sha256"]
        or pdf_ref["size_bytes"] != locator["source_size_bytes"]
        or page_record["document_id"] != f"sha256:{pdf_ref['sha256']}"
        or page_record["physical_page"] != locator["physical_page"]
    ):
        raise _error("source PDF identity/page differs from authenticated projection")
    expected_render = page_record["render_ref"]
    if (
        render_ref["sha256"] != expected_render["sha256"]
        or render_ref["size_bytes"] != expected_render["size_bytes"]
    ):
        raise _error("target page render differs from authenticated projection")
    pixel_dimensions = source["coordinate_authority"]["pixel_dimensions"]
    if type(pixel_dimensions) is not list or len(pixel_dimensions) != 2:
        raise _error("authenticated page pixel dimensions are invalid")
    # The resolved variables make the successful nofollow/hash reads explicit.
    if (
        len(source_pdf_bytes) != pdf_ref["size_bytes"]
        or len(render_bytes) != render_ref["size_bytes"]
    ):
        raise _error("source file changed during request construction")

    numeric, registry_cells, numeric_ref = _validate_numeric_input(
        root, numeric_bytes, graph, source, binding
    )
    nodes = _node_map(graph)
    source_atoms = _atoms(source)
    source_evidence = _evidence_by_atom(graph)

    role_candidates = {item["typed_role"]: item for item in candidate["role_candidates"]}
    if set(role_candidates) != {
        "OWNER_LABEL",
        "BRANCH_LABEL",
        "SHORT_TERM",
        "MEDIUM_TERM",
        "LONG_TERM",
        "TOTAL",
    }:
        raise _error("schema candidate role frontier drifted")

    rows = sorted(
        (node for node in nodes.values() if node["kind"] == "LOGICAL_ROW"),
        key=lambda node: node["attributes"]["ordinal"],
    )
    if [row["attributes"]["row_role"] for row in rows] != list(_SUPPORTED_ROLES):
        raise _error("semantic graph row frontier differs from strict maturity core")
    values = [node for node in nodes.values() if node["kind"] == "VALUE_POSITION"]
    values_by_coordinate = {
        (node["attributes"]["row_ordinal"], node["attributes"]["axis_index"]): node
        for node in values
    }
    if len(values_by_coordinate) != 8:
        raise _error("semantic graph does not contain exact eight value coordinates")
    numeric_cells = {(cell["row_ordinal"], cell["axis_ordinal"]): cell for cell in numeric["cells"]}
    if len(numeric_cells) != 8:
        raise _error("numeric verification does not contain exact eight coordinates")

    _, by_id = _authority_snapshot(root)
    claims: list[dict[str, Any]] = []
    for row in rows:
        ordinal = row["attributes"]["ordinal"]
        role = row["attributes"]["row_role"]
        schema_candidate = role_candidates[role]
        candidate_ids = schema_candidate["candidate_report_norm_ids"]
        if role == "TOTAL":
            if candidate_ids != [] or schema_candidate["disposition"] != SOURCE_ONLY_VALIDATION:
                raise _error("TOTAL is not an exact source-only schema candidate")
            claim_kind = SOURCE_ONLY_VALIDATION
            report_norm_id = None
            schema_binding = None
            label = None
        else:
            expected_id = _SUPPORTED_SCHEMA_IDS[role]
            if candidate_ids != [expected_id]:
                raise _error("mapped row does not have one exact schema candidate")
            item = by_id[expected_id]
            claim_kind = MAPPED_SCHEMA_ROW
            report_norm_id = expected_id
            schema_binding = {
                "schema_namespace": "TM",
                "canonical_name": item.canonical_name,
                "parent_report_norm_id": item.parent_id,
                "ancestor_report_norm_ids": _ancestor_ids(by_id, expected_id),
                "display_order": item.display_order,
                "mapping_eligible": True,
                "candidate_disposition": schema_candidate["disposition"],
            }
            label_refs = _span_refs(row, source_atoms, source_evidence)
            if len(label_refs) != 1:
                raise _error("mapped row must have exactly one visible label atom")
            label = label_refs[0]

        value_records: list[dict[str, Any]] = []
        for axis_index in (0, 1):
            value = values_by_coordinate[(ordinal, axis_index)]
            verified = numeric_cells[(ordinal, axis_index)]
            registry = registry_cells.get(verified["cell_id"])
            refs = _span_refs(value, source_atoms, source_evidence)
            if registry is None or len(refs) != 1:
                raise _error("value cell lacks one registry/source evidence record")
            ref = refs[0]
            attributes = value["attributes"]
            primary = verified["primary"]
            challenger = verified["challenger"]
            if (
                verified["source_graph_node_id"] != value["node_id"]
                or verified["source_evidence_node_id"] != ref["source_evidence_node_id"]
                or verified["source_atom_id"] != ref["source_atom_id"]
                or verified["source_line_index"] != ref["source_line_index"]
                or registry["source_bbox_raw_pixels"] != ref["pixel_bbox"]
                or registry["source_graph_node_id"] != value["node_id"]
                or registry["source_atom_id"] != ref["source_atom_id"]
                or primary["raw_text"] != attributes["raw_text"]
                or primary["value"] != attributes["normalized_decimal"]
                or challenger["raw_text"] != primary["raw_text"]
                or challenger["parsed_value"] != primary["value"]
                or challenger["sign_evidence"] != primary["sign_evidence"]
                or verified["verification_status"] != "VERIFIED_OBSERVED_VALUE"
                or verified["decision"] != "ACCEPT_EXACT_VALUE_AND_SIGN_AGREEMENT"
            ):
                raise _error("numeric, graph, registry, or source cell evidence disagrees")
            value_records.append(
                {
                    "axis_index": axis_index,
                    "graph_node_id": value["node_id"],
                    "source_evidence": ref,
                    "raw_text": attributes["raw_text"],
                    "normalized_decimal": attributes["normalized_decimal"],
                    "state": attributes["state"],
                    "sign_evidence": canonical_clone_v1(primary["sign_evidence"]),
                    "independent_numeric": {
                        "cell_id": verified["cell_id"],
                        "verification_status": verified["verification_status"],
                        "decision": verified["decision"],
                        "challenger_raw_text": challenger["raw_text"],
                        "challenger_parsed_value": challenger["parsed_value"],
                        "challenger_sign_evidence": canonical_clone_v1(challenger["sign_evidence"]),
                        "crop_path": registry["crop_path"],
                        "crop_sha256": registry["crop_sha256"],
                        "crop_size_bytes": registry["crop_size_bytes"],
                    },
                }
            )
        claim = {
            "claim_kind": claim_kind,
            "typed_role": role,
            "report_norm_id": report_norm_id,
            "schema_binding": schema_binding,
            "row_graph_node_id": row["node_id"],
            "row_ordinal": ordinal,
            "label_evidence": label,
            "values": value_records,
            "population_scope": "STRICT_THREE_ROW_CORE"
            if role != "TOTAL"
            else "SOURCE_ONLY_TOTAL_OF_STRICT_THREE_ROW_CORE",
        }
        claim["claim_id"] = f"cimvrqv1:claim:{canonical_json_sha256_v1(claim)}"
        claims.append(claim)

    graph_roles = {
        node["attributes"]["accounting_role"]: node
        for node in nodes.values()
        if node["kind"] == "ACCOUNTING_ROLE"
    }
    owner = graph_roles.get("OWNER_LABEL")
    branch = graph_roles.get("BRANCH_LABEL")
    if owner is None or branch is None:
        raise _error("semantic graph lacks owner/branch roles")
    axes = sorted(
        (node for node in nodes.values() if node["kind"] == "AXIS"),
        key=lambda node: node["attributes"]["axis_index"],
    )
    units = sorted(
        (node for node in nodes.values() if node["kind"] == "UNIT_SCOPE"),
        key=lambda node: node["attributes"]["axis_index"],
    )
    if len(axes) != 2 or len(units) != 2:
        raise _error("semantic graph lacks exact comparative axes/unit scopes")

    table_context = {
        "statement": {
            "statement_type": context["statement_type"],
            "report_scope": context["report_scope"],
            "continuation": context["continuation"],
            "heading_evidence": canonical_clone_v1(context["heading_evidence"]),
        },
        "owner": {
            "graph_node_id": owner["node_id"],
            "source_evidence": _span_refs(owner, source_atoms, source_evidence)[0],
        },
        "branch": {
            "graph_node_id": branch["node_id"],
            "source_evidence": _span_refs(branch, source_atoms, source_evidence)[0],
        },
        "axes": [
            {
                "axis_index": node["attributes"]["axis_index"],
                "period": node["attributes"]["period"],
                "graph_node_id": node["node_id"],
                "source_evidence": _span_refs(node, source_atoms, source_evidence)[0],
            }
            for node in axes
        ],
        "unit_scopes": [
            {
                "axis_index": node["attributes"]["axis_index"],
                "unit": canonical_clone_v1(node["attributes"]["unit"]),
                "graph_node_id": node["node_id"],
                "source_evidence": _span_refs(node, source_atoms, source_evidence)[0],
            }
            for node in units
        ],
        "row_order": list(_SUPPORTED_ROLES),
        "population_scope": "STRICT_THREE_ROW_CORE_PLUS_SOURCE_ONLY_TOTAL",
    }

    amounts = {
        claim["typed_role"]: [
            _decimal(value["normalized_decimal"], "claim value") for value in claim["values"]
        ]
        for claim in claims
    }
    equations = []
    for axis_index in (0, 1):
        addends = [amounts[role][axis_index] for role in _SUPPORTED_ROLES[:-1]]
        total = amounts["TOTAL"][axis_index]
        if sum(addends, Decimal()) != total:
            raise _error("strict maturity core does not close arithmetically")
        equations.append(
            {
                "axis_index": axis_index,
                "addends": [str(value) for value in addends],
                "total": str(total),
                "status": "CORROBORATED",
            }
        )

    near_neighbours = []
    for schema_id in _NEAR_NEIGHBOUR_IDS:
        item = by_id[schema_id]
        near_neighbours.append(
            {
                "report_norm_id": schema_id,
                "schema_namespace": "TM",
                "canonical_name": item.canonical_name,
                "parent_report_norm_id": item.parent_id,
                "display_order": item.display_order,
                "mapping_eligible": schema_id == 5747,
                "schema_context_status": "RESOLVED" if schema_id == 5747 else "UNRESOLVED_ORPHAN",
                "verification_policy": "ALWAYS_UNRESOLVED_NEAR_NEIGHBOUR",
                "whole_document_absence_claim_allowed": False,
            }
        )

    payload: dict[str, Any] = {
        "format_version": REQUEST_FORMAT_VERSION,
        "state": REQUEST_STATE,
        "claim_boundary": REQUEST_CLAIM_BOUNDARY,
        "family_id": graph["family_id"],
        "family_spec_sha256": graph["family_spec_sha256"],
        "source_authority": {
            "document_id": page_record["document_id"],
            "physical_page": page_record["physical_page"],
            "source_pdf": pdf_ref,
            "target_page_render": {
                **render_ref,
                "pixel_width": pixel_dimensions[0],
                "pixel_height": pixel_dimensions[1],
            },
            "source_local_page_id": source["source_local_page_id"],
            "source_projection_sha256": canonical_json_sha256_v1(source),
            "page_result_sha256": source["page_result_sha256"],
        },
        "input_identities": {
            "semantic_graph": {
                "graph_id": graph["graph_id"],
                "sha256": canonical_json_sha256_v1(graph),
            },
            "semantic_page_binding_sha256": canonical_json_sha256_v1(binding),
            "statement_context": {
                "context_id": context["context_id"],
                "sha256": canonical_json_sha256_v1(context),
            },
            "schema_candidate": {
                "candidate_set_id": candidate["candidate_set_id"],
                "sha256": canonical_json_sha256_v1(candidate),
            },
            "numeric_verification": numeric_ref,
            "schema_authority": canonical_clone_v1(candidate["schema_authority"]),
        },
        "inference_firewall": {
            "semantic_text_authority": "VIETOCR_VGG_TRANSFORMER",
            "numeric_and_geometry_authority": "PPOCR_AND_INDEPENDENT_NUMERIC_CHALLENGER",
            "role_a_or_human_answer_available": False,
            "history_or_mongodb_available": False,
            "bank_page_note_identity_used_for_routing": False,
        },
        "table_context": table_context,
        "item_claims": claims,
        "arithmetic_closure": {
            "population_roles": list(_SUPPORTED_ROLES[:-1]),
            "source_only_total_role": "TOTAL",
            "same_population_claimed": False,
            "equations": equations,
        },
        "near_neighbour_candidates": near_neighbours,
        "required_check_policy": {
            "table_checks": list(_TABLE_CHECKS),
            "mapped_schema_row_checks": list(_MAPPED_ITEM_CHECKS),
            "source_only_validation_checks": list(_SOURCE_ONLY_CHECKS),
            "any_fail_or_missing_check_status": UNRESOLVED,
            "all_required_checks_pass_status": VERIFIED,
        },
        "safety": copy.deepcopy(_REQUEST_SAFETY),
    }
    payload["request_id"] = f"cimvrqv1:request:{canonical_json_sha256_v1(payload)}"
    return _validate_request(payload)


def _validate_request(value: Any) -> dict[str, Any]:
    request = _exact_dict(
        value,
        {
            "format_version",
            "state",
            "claim_boundary",
            "request_id",
            "family_id",
            "family_spec_sha256",
            "source_authority",
            "input_identities",
            "inference_firewall",
            "table_context",
            "item_claims",
            "arithmetic_closure",
            "near_neighbour_candidates",
            "required_check_policy",
            "safety",
        },
        "verification request",
    )
    if (
        request["format_version"] != REQUEST_FORMAT_VERSION
        or request["state"] != REQUEST_STATE
        or request["claim_boundary"] != REQUEST_CLAIM_BOUNDARY
        or request["family_id"] != _SUPPORTED_FAMILY_ID
        or request["safety"] != _REQUEST_SAFETY
        or request["required_check_policy"]
        != {
            "table_checks": list(_TABLE_CHECKS),
            "mapped_schema_row_checks": list(_MAPPED_ITEM_CHECKS),
            "source_only_validation_checks": list(_SOURCE_ONLY_CHECKS),
            "any_fail_or_missing_check_status": UNRESOLVED,
            "all_required_checks_pass_status": VERIFIED,
        }
    ):
        raise _error("verification request contract, family, or safety drifted")
    _minted(request, "request_id", "cimvrqv1:request:", "verification request")
    claims = request["item_claims"]
    if type(claims) is not list or [claim.get("typed_role") for claim in claims] != list(
        _SUPPORTED_ROLES
    ):
        raise _error("verification request item frontier drifted")
    ids: list[int] = []
    claim_ids: set[str] = set()
    for claim in claims:
        _exact_dict(
            claim,
            {
                "claim_id",
                "claim_kind",
                "typed_role",
                "report_norm_id",
                "schema_binding",
                "row_graph_node_id",
                "row_ordinal",
                "label_evidence",
                "values",
                "population_scope",
            },
            "item claim",
        )
        _minted(claim, "claim_id", "cimvrqv1:claim:", "item claim")
        if claim["claim_id"] in claim_ids:
            raise _error("verification request repeats a claim identity")
        claim_ids.add(claim["claim_id"])
        if claim["typed_role"] == "TOTAL":
            if (
                claim["claim_kind"] != SOURCE_ONLY_VALIDATION
                or claim["report_norm_id"] is not None
                or claim["schema_binding"] is not None
                or claim["label_evidence"] is not None
            ):
                raise _error("source-only TOTAL acquired schema or label authority")
        else:
            expected_id = _SUPPORTED_SCHEMA_IDS[claim["typed_role"]]
            if (
                claim["claim_kind"] != MAPPED_SCHEMA_ROW
                or claim["report_norm_id"] != expected_id
                or type(claim["schema_binding"]) is not dict
                or claim["schema_binding"].get("parent_report_norm_id") != 752
                or claim["schema_binding"].get("mapping_eligible") is not True
                or type(claim["label_evidence"]) is not dict
            ):
                raise _error("mapped item schema/label contract drifted")
            ids.append(expected_id)
        if type(claim["values"]) is not list or [
            item.get("axis_index") for item in claim["values"]
        ] != [0, 1]:
            raise _error("item claim lacks exact two ordered values")
    if ids != [753, 754, 755]:
        raise _error("mapped ReportNormId order drifted")
    neighbours = request["near_neighbour_candidates"]
    if (
        type(neighbours) is not list
        or [item.get("report_norm_id") for item in neighbours] != [5747, 1944]
        or neighbours[0].get("parent_report_norm_id") != 752
        or neighbours[0].get("mapping_eligible") is not True
        or neighbours[1].get("parent_report_norm_id") is not None
        or neighbours[1].get("mapping_eligible") is not False
        or neighbours[1].get("schema_context_status") != "UNRESOLVED_ORPHAN"
        or any(item.get("whole_document_absence_claim_allowed") is not False for item in neighbours)
    ):
        raise _error("schema near-neighbour contract drifted")
    return canonical_clone_v1(request)


def _verification_input_identities_from_request(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Project the exact replayed upstream identities into the final receipt."""

    identities = _exact_dict(
        request["input_identities"],
        {
            "semantic_graph",
            "semantic_page_binding_sha256",
            "statement_context",
            "schema_candidate",
            "numeric_verification",
            "schema_authority",
        },
        "verification request input identities",
    )
    return _validate_verification_input_identities(
        {
            "semantic_graph": canonical_clone_v1(identities["semantic_graph"]),
            "schema_candidate": canonical_clone_v1(identities["schema_candidate"]),
            "statement_context": canonical_clone_v1(identities["statement_context"]),
            "source_projection_sha256": request["source_authority"]["source_projection_sha256"],
            "semantic_page_binding_sha256": identities["semantic_page_binding_sha256"],
            "numeric_verification": canonical_clone_v1(identities["numeric_verification"]),
        }
    )


def _validate_verification_input_identities(value: Any) -> dict[str, Any]:
    identities = _exact_dict(
        value,
        {
            "semantic_graph",
            "schema_candidate",
            "statement_context",
            "source_projection_sha256",
            "semantic_page_binding_sha256",
            "numeric_verification",
        },
        "Codex mapped-item verification input identities",
    )
    graph = _exact_dict(
        identities["semantic_graph"], {"graph_id", "sha256"}, "semantic graph identity"
    )
    _exact_digest_identity(graph["graph_id"], "slagv2:graph:", "semantic graph")
    _exact_sha256(graph["sha256"], "semantic graph")
    candidate = _exact_dict(
        identities["schema_candidate"],
        {"candidate_set_id", "sha256"},
        "schema candidate identity",
    )
    _exact_digest_identity(candidate["candidate_set_id"], "slascv1:candidate:", "schema candidate")
    _exact_sha256(candidate["sha256"], "schema candidate")
    context = _exact_dict(
        identities["statement_context"],
        {"context_id", "sha256"},
        "statement context identity",
    )
    _exact_digest_identity(context["context_id"], "sscxtv1:context:", "statement context")
    _exact_sha256(context["sha256"], "statement context")
    _exact_sha256(identities["source_projection_sha256"], "source projection")
    _exact_sha256(identities["semantic_page_binding_sha256"], "semantic page binding")
    numeric = _exact_dict(
        identities["numeric_verification"],
        {"sha256", "size_bytes", "verification_id", "path"},
        "numeric verification identity",
    )
    _exact_sha256(numeric["sha256"], "numeric verification")
    if type(numeric["size_bytes"]) is not int or numeric["size_bytes"] <= 0:
        raise _error("numeric verification size drifted")
    _exact_digest_identity(
        numeric["verification_id"], "sgnpvv1:verification:", "numeric verification"
    )
    if type(numeric["path"]) is not str or not numeric["path"]:
        raise _error("numeric verification path drifted")
    return canonical_clone_v1(identities)


def build_codex_mapped_item_verification_request_v1(
    project_root: Path,
    semantic_graph_v2: Any,
    schema_candidate_v1: Any,
    statement_context_v1: Any,
    numeric_verification_bytes: bytes,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: Sequence[FamilySpecV1],
    *,
    source_pdf_path: Path | str,
    target_page_render_path: Path | str,
) -> tuple[dict[str, Any], AuthenticatedCodexMappedItemVerificationRequestV1]:
    """Build one frozen request and mint its opaque replay authority."""

    root = project_root.resolve(strict=True)
    try:
        graph = validate_semantic_local_accounting_graph_replay_v2(
            semantic_graph_v2,
            source_projection_v2,
            semantic_page_binding_v2,
            authenticated_transformer_receipt_v2,
            family_spec,
            family_specs_for_collision_scope,
        )
        candidate = validate_semantic_local_accounting_schema_candidate_replay_v1(
            schema_candidate_v1,
            root,
            graph,
            source_projection_v2,
            semantic_page_binding_v2,
            authenticated_transformer_receipt_v2,
            family_spec,
            family_specs_for_collision_scope,
        )
        context = validate_semantic_statement_context_replay_v1(
            statement_context_v1,
            source_projection_v2,
            semantic_page_binding_v2,
            authenticated_transformer_receipt_v2,
        )
    except ValueError as exc:
        raise _error("verification request upstream replay failed") from exc
    request = _build_request_payload(
        root,
        graph,
        candidate,
        context,
        numeric_verification_bytes,
        source_projection_v2,
        semantic_page_binding_v2,
        source_pdf_path,
        target_page_render_path,
    )
    return request, _mint_request_receipt(request)


def validate_codex_mapped_item_verification_request_replay_v1(
    value: Any,
    project_root: Path,
    semantic_graph_v2: Any,
    schema_candidate_v1: Any,
    statement_context_v1: Any,
    numeric_verification_bytes: bytes,
    source_projection_v2: Any,
    semantic_page_binding_v2: Any,
    authenticated_transformer_receipt_v2: Any,
    family_spec: FamilySpecV1,
    family_specs_for_collision_scope: Sequence[FamilySpecV1],
    *,
    source_pdf_path: Path | str,
    target_page_render_path: Path | str,
) -> tuple[dict[str, Any], AuthenticatedCodexMappedItemVerificationRequestV1]:
    """Rebuild/compare one request and mint a new opaque replay authority."""

    persisted = _validate_request(value)
    rebuilt, receipt = build_codex_mapped_item_verification_request_v1(
        project_root,
        semantic_graph_v2,
        schema_candidate_v1,
        statement_context_v1,
        numeric_verification_bytes,
        source_projection_v2,
        semantic_page_binding_v2,
        authenticated_transformer_receipt_v2,
        family_spec,
        family_specs_for_collision_scope,
        source_pdf_path=source_pdf_path,
        target_page_render_path=target_page_render_path,
    )
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("verification request does not replay from exact upstream authorities")
    return canonical_clone_v1(rebuilt), receipt


def _expected_pixel_readback(request: Mapping[str, Any]) -> dict[str, Any]:
    context = request["table_context"]
    return {
        "source_pdf_sha256": request["source_authority"]["source_pdf"]["sha256"],
        "target_page_render_sha256": request["source_authority"]["target_page_render"]["sha256"],
        "physical_page": request["source_authority"]["physical_page"],
        "statement_heading": context["statement"]["heading_evidence"]["raw_transformer_text_utf8"],
        "owner": context["owner"]["source_evidence"]["raw_text_utf8"],
        "branch": context["branch"]["source_evidence"]["raw_text_utf8"],
        "axes": [item["source_evidence"]["raw_text_utf8"] for item in context["axes"]],
        "units": [item["source_evidence"]["raw_text_utf8"] for item in context["unit_scopes"]],
        "rows": [
            {
                "claim_id": claim["claim_id"],
                "typed_role": claim["typed_role"],
                "label": (
                    None
                    if claim["label_evidence"] is None
                    else claim["label_evidence"]["raw_text_utf8"]
                ),
                "values": [value["raw_text"] for value in claim["values"]],
            }
            for claim in request["item_claims"]
        ],
        "row_order": list(_SUPPORTED_ROLES),
        "closure_equations": canonical_clone_v1(request["arithmetic_closure"]["equations"]),
    }


def _required_check_keys(request: Mapping[str, Any]) -> list[tuple[str | None, str]]:
    result = [(None, check_id) for check_id in _TABLE_CHECKS]
    for claim in request["item_claims"]:
        checks = (
            _MAPPED_ITEM_CHECKS if claim["claim_kind"] == MAPPED_SCHEMA_ROW else _SOURCE_ONLY_CHECKS
        )
        result.extend((claim["claim_id"], check_id) for check_id in checks)
    return result


def _validate_review(value: Any, request_value: Any) -> dict[str, Any]:
    request = _validate_request(request_value)
    review = _exact_dict(
        value,
        {
            "format_version",
            "state",
            "claim_boundary",
            "review_id",
            "request_id",
            "request_sha256",
            "reviewer",
            "access_contract",
            "pixel_readback",
            "check_results",
            "near_neighbour_dispositions",
        },
        "Codex review",
    )
    if (
        review["format_version"] != REVIEW_FORMAT_VERSION
        or review["state"] != REVIEW_STATE
        or review["claim_boundary"] != REVIEW_CLAIM_BOUNDARY
        or review["request_id"] != request["request_id"]
        or review["request_sha256"] != canonical_json_sha256_v1(request)
        or review["access_contract"] != _REVIEW_ACCESS
        or review["pixel_readback"] != _expected_pixel_readback(request)
    ):
        raise _error("Codex review request binding, access, or pixel readback drifted")
    _exact_dict(review["reviewer"], {"kind", "review_run_id"}, "Codex reviewer")
    if (
        review["reviewer"]["kind"] != "CODEX_INDEPENDENT_SOURCE_REVIEW"
        or type(review["reviewer"]["review_run_id"]) is not str
        or not review["reviewer"]["review_run_id"]
    ):
        raise _error("Codex reviewer identity metadata is invalid")
    _minted(review, "review_id", "codexmirv1:review:", "Codex review")

    results = review["check_results"]
    expected_keys = _required_check_keys(request)
    if type(results) is not list or len(results) != len(expected_keys):
        raise _error("Codex review check denominator drifted")
    observed: list[tuple[str | None, str]] = []
    allowed_refs = {
        request["request_id"],
        request["source_authority"]["source_pdf"]["sha256"],
        request["source_authority"]["target_page_render"]["sha256"],
        *(claim["claim_id"] for claim in request["item_claims"]),
    }
    for record in results:
        _exact_dict(
            record,
            {"claim_id", "check_id", "status", "evidence_refs", "falsifier_code", "rationale"},
            "Codex check result",
        )
        key = (record["claim_id"], record["check_id"])
        observed.append(key)
        if record["status"] not in {"PASS", "FAIL"}:
            raise _error("Codex check status must be PASS or FAIL")
        if (
            type(record["evidence_refs"]) is not list
            or not record["evidence_refs"]
            or any(reference not in allowed_refs for reference in record["evidence_refs"])
            or type(record["rationale"]) is not str
            or not record["rationale"].strip()
        ):
            raise _error("Codex check evidence/rationale is invalid")
        if record["status"] == "PASS" and record["falsifier_code"] is not None:
            raise _error("passing Codex check carries a falsifier")
        if record["status"] == "FAIL" and (
            type(record["falsifier_code"]) is not str
            or _FALSIFIER.fullmatch(record["falsifier_code"]) is None
        ):
            raise _error("failed Codex check lacks a closed falsifier code")
    if observed != expected_keys:
        raise _error("Codex review checks are missing, duplicated, or reordered")

    neighbours = review["near_neighbour_dispositions"]
    if type(neighbours) is not list or [item.get("report_norm_id") for item in neighbours] != [
        5747,
        1944,
    ]:
        raise _error("Codex review near-neighbour denominator drifted")
    expected_dispositions = {
        5747: "NOT_OBSERVED_IN_BOUND_SOURCE_TABLE",
        1944: "SCHEMA_CONTEXT_UNRESOLVED_ORPHAN_MAPPING_INELIGIBLE",
    }
    for item in neighbours:
        _exact_dict(
            item,
            {
                "report_norm_id",
                "status",
                "disposition",
                "whole_document_absence_claim",
                "evidence_refs",
            },
            "near-neighbour disposition",
        )
        if (
            item["status"] != UNRESOLVED
            or item["disposition"] != expected_dispositions[item["report_norm_id"]]
            or item["whole_document_absence_claim"] is not False
            or type(item["evidence_refs"]) is not list
            or not item["evidence_refs"]
            or any(reference not in allowed_refs for reference in item["evidence_refs"])
        ):
            raise _error("near-neighbour disposition or absence boundary drifted")
    return canonical_clone_v1(review)


def build_codex_mapped_item_review_v1(
    request_receipt: AuthenticatedCodexMappedItemVerificationRequestV1,
    *,
    reviewer: Mapping[str, Any],
    pixel_readback: Mapping[str, Any],
    check_results: Sequence[Mapping[str, Any]],
    near_neighbour_dispositions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build an unauthenticated review proposal; it cannot drive assembly."""

    request = _request_payload(request_receipt)
    payload: dict[str, Any] = {
        "format_version": REVIEW_FORMAT_VERSION,
        "state": REVIEW_STATE,
        "claim_boundary": REVIEW_CLAIM_BOUNDARY,
        "request_id": request["request_id"],
        "request_sha256": canonical_json_sha256_v1(request),
        "reviewer": canonical_clone_v1(reviewer),
        "access_contract": copy.deepcopy(_REVIEW_ACCESS),
        "pixel_readback": canonical_clone_v1(pixel_readback),
        "check_results": canonical_clone_v1(check_results),
        "near_neighbour_dispositions": canonical_clone_v1(near_neighbour_dispositions),
    }
    payload["review_id"] = f"codexmirv1:review:{canonical_json_sha256_v1(payload)}"
    return _validate_review(payload, request)


def validate_codex_mapped_item_review_v1(
    value: Any, request_receipt: AuthenticatedCodexMappedItemVerificationRequestV1
) -> dict[str, Any]:
    """Validate shape/binding only; this does not authenticate a Codex review."""

    return _validate_review(value, _request_payload(request_receipt))


def authenticate_codex_mapped_item_review_v1(
    project_root: Path,
    request_receipt: AuthenticatedCodexMappedItemVerificationRequestV1,
    *,
    review_path: Path | str = _PINNED_REVIEW_RELATIVE_PATH,
) -> tuple[dict[str, Any], AuthenticatedCodexMappedItemReviewV1]:
    """Authenticate the exact externally selected review and mint its opaque receipt."""

    root = project_root.resolve(strict=True)
    request = _request_payload(request_receipt)
    raw = Path(review_path)
    if raw != _PINNED_REVIEW_RELATIVE_PATH:
        raise _error("Codex review v1 must use the fixed externally selected artifact path")
    _path, payload, artifact = _safe_file(root, raw, "pinned Codex review")
    if (
        artifact["sha256"] != _PINNED_REVIEW_SHA256
        or artifact["size_bytes"] != _PINNED_REVIEW_SIZE_BYTES
    ):
        raise _error("pinned Codex review artifact hash or size drifted")
    review = _validate_review(_closed_json_object(payload, "pinned Codex review"), request)
    if review["review_id"] != _PINNED_REVIEW_ID:
        raise _error("pinned Codex review identity drifted")
    return review, _mint_review_receipt(review, request)


def _assemble(
    request_receipt: AuthenticatedCodexMappedItemVerificationRequestV1,
    review_receipt: AuthenticatedCodexMappedItemReviewV1,
) -> dict[str, Any]:
    request = _request_payload(request_receipt)
    review = _review_payload(review_receipt, request)
    checks = {
        (record["claim_id"], record["check_id"]): record for record in review["check_results"]
    }
    table_failed = [
        check_id for check_id in _TABLE_CHECKS if checks[(None, check_id)]["status"] != "PASS"
    ]
    verdicts: list[dict[str, Any]] = []
    for claim in request["item_claims"]:
        required = (
            _MAPPED_ITEM_CHECKS if claim["claim_kind"] == MAPPED_SCHEMA_ROW else _SOURCE_ONLY_CHECKS
        )
        failed = [
            *table_failed,
            *(
                check_id
                for check_id in required
                if checks[(claim["claim_id"], check_id)]["status"] != "PASS"
            ),
        ]
        status = VERIFIED if not failed else UNRESOLVED
        if claim["claim_kind"] == MAPPED_SCHEMA_ROW:
            authority = {
                "accepted_mapping_for_exact_bound_source_observation": status == VERIFIED,
                "source_value_readback": status == VERIFIED,
                "source_total_readback_and_local_closure": False,
                "canonicalization": False,
                "value_materialization": False,
                "export": False,
                "production": False,
            }
        else:
            authority = {
                "accepted_mapping_for_exact_bound_source_observation": False,
                "source_value_readback": status == VERIFIED,
                "source_total_readback_and_local_closure": status == VERIFIED,
                "canonicalization": False,
                "value_materialization": False,
                "export": False,
                "production": False,
            }
        verdicts.append(
            {
                "claim_id": claim["claim_id"],
                "claim_kind": claim["claim_kind"],
                "typed_role": claim["typed_role"],
                "report_norm_id": claim["report_norm_id"],
                "schema_binding": canonical_clone_v1(claim["schema_binding"]),
                "row_graph_node_id": claim["row_graph_node_id"],
                "values": [
                    {
                        "axis_index": value["axis_index"],
                        "raw_text": value["raw_text"],
                        "normalized_decimal": value["normalized_decimal"],
                        "state": value["state"],
                    }
                    for value in claim["values"]
                ],
                "status": status,
                "failed_check_ids": failed,
                "authority": authority,
            }
        )
    payload: dict[str, Any] = {
        "format_version": VERIFICATION_FORMAT_VERSION,
        "state": VERIFICATION_STATE,
        "claim_boundary": VERIFICATION_CLAIM_BOUNDARY,
        "request": {
            "request_id": request["request_id"],
            "sha256": canonical_json_sha256_v1(request),
        },
        "review": {
            "review_id": review["review_id"],
            "sha256": canonical_json_sha256_v1(review),
        },
        "source_authority": canonical_clone_v1(request["source_authority"]),
        "input_identities": _verification_input_identities_from_request(request),
        "family_id": request["family_id"],
        "item_verdicts": verdicts,
        "source_only_arithmetic_closure": canonical_clone_v1(request["arithmetic_closure"]),
        "near_neighbour_verdicts": canonical_clone_v1(review["near_neighbour_dispositions"]),
        "metrics": {
            "verified_mapped_row_count": sum(
                item["claim_kind"] == MAPPED_SCHEMA_ROW and item["status"] == VERIFIED
                for item in verdicts
            ),
            "verified_source_only_validation_count": sum(
                item["claim_kind"] == SOURCE_ONLY_VALIDATION and item["status"] == VERIFIED
                for item in verdicts
            ),
            "unresolved_item_count": sum(item["status"] == UNRESOLVED for item in verdicts),
            "unresolved_near_neighbour_count": len(review["near_neighbour_dispositions"]),
        },
        "safety": copy.deepcopy(_VERIFICATION_SAFETY),
    }
    payload["verification_id"] = f"codexmiv1:verification:{canonical_json_sha256_v1(payload)}"
    return _validate_verification(payload)


def _validate_verification(value: Any) -> dict[str, Any]:
    verification = _exact_dict(
        value,
        {
            "format_version",
            "state",
            "claim_boundary",
            "verification_id",
            "request",
            "review",
            "source_authority",
            "input_identities",
            "family_id",
            "item_verdicts",
            "source_only_arithmetic_closure",
            "near_neighbour_verdicts",
            "metrics",
            "safety",
        },
        "Codex mapped-item verification",
    )
    if (
        verification["format_version"] != VERIFICATION_FORMAT_VERSION
        or verification["state"] != VERIFICATION_STATE
        or verification["claim_boundary"] != VERIFICATION_CLAIM_BOUNDARY
        or verification["family_id"] != _SUPPORTED_FAMILY_ID
        or verification["safety"] != _VERIFICATION_SAFETY
    ):
        raise _error("Codex mapped-item verification contract or safety drifted")
    _minted(
        verification,
        "verification_id",
        "codexmiv1:verification:",
        "Codex mapped-item verification",
    )
    _validate_verification_input_identities(verification["input_identities"])
    verdicts = verification["item_verdicts"]
    if type(verdicts) is not list or [item.get("typed_role") for item in verdicts] != list(
        _SUPPORTED_ROLES
    ):
        raise _error("Codex mapped-item verdict frontier drifted")
    for item in verdicts:
        if item["status"] not in {VERIFIED, UNRESOLVED}:
            raise _error("Codex item verdict has an unsupported status")
        if item["typed_role"] == "TOTAL" and (
            item["claim_kind"] != SOURCE_ONLY_VALIDATION
            or item["report_norm_id"] is not None
            or item["schema_binding"] is not None
            or item["authority"]["accepted_mapping_for_exact_bound_source_observation"] is not False
        ):
            raise _error("verified source-only TOTAL acquired mapping authority")
    neighbours = verification["near_neighbour_verdicts"]
    if (
        type(neighbours) is not list
        or [item.get("report_norm_id") for item in neighbours] != [5747, 1944]
        or any(
            item.get("status") != UNRESOLVED
            or item.get("whole_document_absence_claim") is not False
            for item in neighbours
        )
    ):
        raise _error("Codex near-neighbour verdict or absence boundary drifted")
    return canonical_clone_v1(verification)


def assemble_codex_mapped_item_verification_v1(
    request_receipt: AuthenticatedCodexMappedItemVerificationRequestV1,
    review_receipt: AuthenticatedCodexMappedItemReviewV1,
) -> dict[str, Any]:
    """Derive all final item statuses from the closed reviewer checks."""

    return _assemble(request_receipt, review_receipt)


def validate_codex_mapped_item_verification_replay_v1(
    value: Any,
    request_receipt: AuthenticatedCodexMappedItemVerificationRequestV1,
    review_receipt: AuthenticatedCodexMappedItemReviewV1,
) -> dict[str, Any]:
    """Reassemble and typed-compare a persisted verification."""

    persisted = _validate_verification(value)
    rebuilt = _assemble(request_receipt, review_receipt)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("Codex mapped-item verification does not replay exactly")
    return canonical_clone_v1(rebuilt)
