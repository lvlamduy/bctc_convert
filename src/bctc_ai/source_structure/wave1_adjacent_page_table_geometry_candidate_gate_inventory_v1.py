"""Build the compact blind Wave-1 adjacent-page seed-gate inventory.

The production builder consumes the exact finalized V3 stream once.  Each
page is projected, proposed and graphed once, then retained as the previous
page for at most one following-page derivation.  The exhaustive path uses the
committed relation and gate private pure derivations after page-local public
validation; a bounded category sentinel separately proves parity with the
fused public gate builder and validator.

Every pair receipt retains all relation, distance, fragment, physical-axis
and pair dispositions.  Only the identical gate policy/safety header is
factored into ``gate_common_contract``.  Recombining it with a receipt must
reproduce the exact full gate object and canonical SHA-256.  These remain
blind exploratory candidates and unresolved dispositions, never accepted
continuations, table ownership, semantic structure, or accuracy evidence.
"""

from __future__ import annotations

import os
import re
import secrets
import stat
import subprocess
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.corpus import wave1_role_b_sentinel as sentinel
from bctc_ai.source_structure import (
    adjacent_page_table_geometry_candidate_gate_v1 as gate_v1,
)
from bctc_ai.source_structure import adjacent_page_table_geometry_relations_v1 as relation_v1
from bctc_ai.source_structure import wave1_prestructural_graph_inventory_v1 as graph_inventory_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.contracts_v2 import make_page_proposal_set_v2
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.finalized_v3_survey_stream_v1 import (
    FINALIZED_V3_SURVEY_AUTHORITY_V1,
    FinalizedV3SurveyAuthority,
    open_finalized_v3_survey_stream_v1,
)
from bctc_ai.source_structure.page_geometry_proposals_v1 import (
    generate_page_geometry_proposals_v1,
)
from bctc_ai.source_structure.page_prestructural_graph_v1 import (
    build_page_prestructural_graph_v1,
)
from bctc_ai.source_structure.structural_graph_contracts_v1 import (
    validate_page_prestructural_graph_v1,
)
from bctc_ai.source_structure.wave1_source_inventory_v1 import (
    validate_wave1_source_inventory_v1,
)

__all__ = [
    "WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_CLAIM_BOUNDARY_V1",
    "WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_FORMAT_VERSION_V1",
    "WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_OUTPUT_RELATIVE_PATH_V1",
    "Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error",
    "build_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1",
    "publish_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1",
    "validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1",
]


class Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error(ValueError):
    """The compact blind gate inventory failed exact accounting or authority."""


WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_FORMAT_VERSION_V1 = (
    "BANK_CORPUS_WAVE_1_ROLE_B_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_V1"
)
WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_CLAIM_BOUNDARY_V1 = (
    "EXHAUSTIVE_BLIND_WAVE_1_ADJACENT_PAGE_EXPLORATORY_GEOMETRY_SEED_GATE_"
    "DISPOSITION_INVENTORY_ONLY_NO_WINNER_SAME_TABLE_SUCCESSOR_CONTINUATION_"
    "MERGE_OWNERSHIP_SEMANTIC_CALIBRATION_ACCURACY_GENERALIZATION_OR_ABSENCE_CLAIM"
)
WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_OUTPUT_RELATIVE_PATH_V1 = Path(
    "output/development/bank-corpus-survey-v1/"
    "wave-1-role-b-adjacent-page-table-geometry-candidate-gate-inventory-v1.json"
)

_FORMAT_STATUS = "COMPLETE_WAVE_1_ADJACENT_PAGE_EXPLORATORY_GEOMETRY_SEED_GATE_INVENTORY"
_SOURCE_INVENTORY_RELATIVE_PATH = Path(
    "output/development/bank-corpus-survey-v1/wave-1-role-b-source-first-inventory-v1.json"
)
_SOURCE_INVENTORY_SHA256 = "c20c9b42ff6f96baf6eff6607e12b27681146d8d968e4e86f0e792bde1429162"
_SOURCE_INVENTORY_SIZE_BYTES = 1_920_845
_SOURCE_INVENTORY_IDENTITY_SHA256 = (
    "63c5988b80cc9893cc20f1b7476d9124880c838d8e4bc6a9d5f4df195550ad84"
)
_PRESTRUCTURAL_INVENTORY_RELATIVE_PATH = Path(
    "output/development/bank-corpus-survey-v1/wave-1-role-b-prestructural-graph-inventory-v1.json"
)
_PRESTRUCTURAL_INVENTORY_SHA256 = "aa18293824cdf15523fa96972555354a2c478bfe29980def2b6838cf11f346f4"
_PRESTRUCTURAL_INVENTORY_SIZE_BYTES = 136_272_263
_PRESTRUCTURAL_INVENTORY_IDENTITY_SHA256 = (
    "310995ab1c9edee51720236e21053d7fdcdd2fad3bc73a4e25e5e3a16aec88f0"
)

_GATE_PRODUCER_COMMIT = "a157c0a2f2ad6361d20fdef1cac39a358033ef57"
_GATE_MODULE_PATH = Path(
    "src/bctc_ai/source_structure/adjacent_page_table_geometry_candidate_gate_v1.py"
)
_GATE_MODULE_SHA256 = "0bf982e154a043274b5c491aef3f93eecffdead87ce49fd14598fb82c85fb5ef"
_GATE_MODULE_SIZE_BYTES = 47_683
_GATE_TEST_PATH = Path(
    "tests/unit/test_source_structure_adjacent_page_table_geometry_candidate_gate_v1.py"
)
_GATE_TEST_SHA256 = "9c34855ebb7b4d85ca6b3bbae3c406d644a7e1be13099a4153ff09e6bfdc6ac6"
_GATE_TEST_SIZE_BYTES = 41_584
_RELATION_MODULE_PATH = Path(
    "src/bctc_ai/source_structure/adjacent_page_table_geometry_relations_v1.py"
)
_RELATION_MODULE_SHA256 = "63763fa9a4bb91f797b55b2e50c687a2aeb47748476040b974fdafc8640f0013"
_RELATION_MODULE_SIZE_BYTES = 41_559
_GATE_POLICY_IDENTITY = (
    "apgcv1:policy:546be183185551b3eedad630c0f8a425a5f04f370661b5b2674f7e20ac7fbdb8"
)
_GATE_SAFETY_SHA256 = "1cae3d0ce740ebcd0095de10bf69ff5e0eabaed99fea4e4c58475440d790287d"

_GATE_CONTRACT = {
    "producer_commit": _GATE_PRODUCER_COMMIT,
    "module_path": _GATE_MODULE_PATH.as_posix(),
    "module_sha256": _GATE_MODULE_SHA256,
    "module_size_bytes": _GATE_MODULE_SIZE_BYTES,
    "focused_test_path": _GATE_TEST_PATH.as_posix(),
    "focused_test_sha256": _GATE_TEST_SHA256,
    "focused_test_size_bytes": _GATE_TEST_SIZE_BYTES,
    "format_version": gate_v1.ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_FORMAT_VERSION_V1,
    "claim_boundary": gate_v1.ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_CLAIM_BOUNDARY_V1,
    "status": gate_v1.ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_STATUS_V1,
    "policy_identity": _GATE_POLICY_IDENTITY,
    "safety_payload_sha256": _GATE_SAFETY_SHA256,
}

_GATE_COMMON_FIELDS = {
    "format_version",
    "claim_boundary",
    "status",
    "policy",
    "policy_identity",
    "safety",
    "safety_payload_sha256",
}
_GATE_RECEIPT_FIELDS = {
    "gate_artifact_identity",
    "gate_canonical_sha256",
    "upstream_binding",
    "relation_dispositions",
    "axis_distance_dispositions",
    "fragment_dispositions",
    "axis_dispositions",
    "page_pair_disposition",
    "metrics",
}
_GATE_FULL_FIELDS = _GATE_COMMON_FIELDS | {
    "artifact_identity",
    "upstream_binding",
    "relation_dispositions",
    "axis_distance_dispositions",
    "fragment_dispositions",
    "axis_dispositions",
    "page_pair_disposition",
    "metrics",
}

_RELATION_DISPOSITIONS = (
    "RETAINED_OUTSIDE_TABLE_OR_PAGE_ENVELOPE_UNRESOLVED",
    "RETAINED_WITH_INSUFFICIENT_BIDIRECTIONALLY_SINGLETON_AXIS_SUPPORT_UNRESOLVED",
    "GEOMETRY_SUPPORTED_EXPLORATORY_SEED_CANDIDATE",
)
_AXIS_DISTANCE_DISPOSITIONS = (
    "RETAINED_OUTSIDE_AXIS_ENVELOPE_UNRESOLVED",
    "WITHIN_AXIS_ENVELOPE_AMBIGUOUS_SEED_LINK",
    "WITHIN_AXIS_ENVELOPE_BIDIRECTIONALLY_SINGLETON_SEED_LINK",
)
_FRAGMENT_DISPOSITIONS = (
    "UPSTREAM_RETAINED_WITHOUT_MEASURED_COUNTERPART_UNRESOLVED",
    "RETAINED_WITH_ZERO_GEOMETRY_SUPPORTED_RELATIONS_UNRESOLVED",
    "ONE_RECIPROCAL_SINGLETON_FRAGMENT_SEED_CANDIDATE",
    "ONE_NONRECIPROCAL_FRAGMENT_SEED_AMBIGUOUS_UNRESOLVED",
    "MULTIPLE_FRAGMENT_SEEDS_AMBIGUOUS_UNRESOLVED",
)
_PHYSICAL_AXIS_DISPOSITIONS = (
    "UPSTREAM_RETAINED_WITHOUT_AXIS_COUNTERPART_UNRESOLVED",
    "RETAINED_WITH_ZERO_AXIS_ENVELOPE_LINKS_UNRESOLVED",
    "RETAINED_WITH_ONLY_AMBIGUOUS_AXIS_ENVELOPE_LINKS_UNRESOLVED",
    "ONE_BIDIRECTIONALLY_SINGLETON_AXIS_SEED_CANDIDATE",
    "MULTIPLE_OR_MIXED_AXIS_SEED_LINKS_AMBIGUOUS_UNRESOLVED",
)
_UPSTREAM_PAIR_DISPOSITIONS = (
    "MEASURED_CARTESIAN_FRAGMENT_PAIRS",
    "NO_PREVIOUS_TABLE_CANDIDATE",
    "NO_FOLLOWING_TABLE_CANDIDATE",
    "NO_TABLE_CANDIDATES",
    "UPSTREAM_TERMINAL_BARRIER",
)
_PAIR_DISPOSITIONS = (
    "UPSTREAM_NONMEASURED_PAGE_PAIR_RETAINED_UNRESOLVED",
    "NO_GEOMETRY_SUPPORTED_EXPLORATORY_SEED_UNRESOLVED",
    "ONE_OR_MORE_RECIPROCAL_SINGLETON_GEOMETRY_SEEDS_RETAINED",
    "GEOMETRY_SEEDS_WITH_FRAGMENT_AMBIGUITY_RETAINED",
)
_DEGREE_CLASSES = ("ZERO", "ONE", "MULTIPLE")
_TABLE_COMPONENTS = ("left_edge_within_cap", "right_edge_within_cap", "width_within_cap")
_PAGE_COMPONENTS = ("previous_bottom_within_cap", "following_top_within_cap")
_AXIS_COMPONENTS = ("x0_within_cap", "x2_within_cap", "doubled_center2_within_cap")
_RELATION_FAILURE_FIELDS = (
    "table_left_edge_outside_envelope",
    "table_right_edge_outside_envelope",
    "table_width_outside_envelope",
    "previous_bottom_outside_envelope",
    "following_top_outside_envelope",
    "fewer_than_two_bidirectionally_singleton_axis_links",
)
_RELATION_FAILURE_CODES = {
    "table_left_edge_outside_envelope": "TABLE_LEFT_EDGE_OUTSIDE_EXPLORATORY_ENVELOPE",
    "table_right_edge_outside_envelope": "TABLE_RIGHT_EDGE_OUTSIDE_EXPLORATORY_ENVELOPE",
    "table_width_outside_envelope": "TABLE_WIDTH_OUTSIDE_EXPLORATORY_ENVELOPE",
    "previous_bottom_outside_envelope": "PREVIOUS_FRAGMENT_NOT_NEAR_ENOUGH_PAGE_BOTTOM",
    "following_top_outside_envelope": "FOLLOWING_FRAGMENT_NOT_NEAR_ENOUGH_PAGE_TOP",
    "fewer_than_two_bidirectionally_singleton_axis_links": (
        "FEWER_THAN_TWO_BIDIRECTIONALLY_SINGLETON_AXIS_GEOMETRY_LINKS"
    ),
}
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
_REQUIRED_PARITY_CATEGORIES = (
    "MEASURED_FRAGMENT_PAIR",
    "UNEQUAL_AXIS_COUNT_RELATION",
    "TERMINAL_BARRIER_PAIR",
    "ZERO_COUNTERPART_PAIR",
)

_FROZEN_PRESTRUCTURAL_NODE_COUNTS = {
    "AXIS_OR_DIMENSION": 9_517,
    "CELL_OR_VALUE_POSITION": 295_334,
    "DOCUMENT": 1_449,
    "EVIDENCE": 1_454_160,
    "PAGE": 1_449,
    "ROW": 28_247,
    "STATEMENT_BLOCK": 0,
    "TABLE": 970,
    "UNRESOLVED_REGION": 1_449,
}
_FROZEN_CORPUS_DENOMINATORS = {
    "document_count": 27,
    "page_count": 1_449,
    "page_pair_count": 1_422,
    "excluded_cross_document_boundary_count": 26,
    "terminal_page_count": 59,
    "relation_occurrence_count": 899,
    "axis_distance_occurrence_count": 122_573,
    "fragment_occurrence_count": 1_909,
    "physical_axis_occurrence_count": 18_805,
    "distinct_fragment_count": 970,
    "distinct_physical_axis_count": 9_517,
    "distinct_relation_count": 899,
    "distinct_axis_distance_count": 122_573,
}

_SAFETY = {
    "blind_source_local_geometry_only": True,
    "complete_pair_receipts": True,
    "complete_relation_dispositions": True,
    "complete_axis_distance_dispositions": True,
    "complete_fragment_occurrence_dispositions": True,
    "complete_physical_axis_occurrence_dispositions": True,
    "gate_common_contract_factored_once": True,
    "full_gate_exactly_reconstructable": True,
    "neighbor_pair_occurrences_not_globally_deduplicated": True,
    "distinct_page_local_identities_separately_counted": True,
    "one_pass_page_pipeline": True,
    "optimized_private_derivation_used": True,
    "all_pair_public_gate_validation": False,
    "bounded_public_fused_parity_required": True,
    "standalone_validator_is_structural_accounting_only": True,
    "standalone_validator_replays_source_or_gate": False,
    "downstream_exact_raw_artifact_sha256_pin_required": True,
    "accepted_relation_claimed": False,
    "winner_selected": False,
    "same_table_claimed": False,
    "successor_claimed": False,
    "continuation_claimed": False,
    "merge_claimed": False,
    "ownership_claimed": False,
    "statement_claimed": False,
    "table_semantic_claimed": False,
    "logical_rows_claimed": False,
    "financial_cells_claimed": False,
    "period_claimed": False,
    "unit_claimed": False,
    "scope_claimed": False,
    "hierarchy_claimed": False,
    "absence_claimed": False,
    "confidence_claimed": False,
    "accuracy_claimed": False,
    "holdout_claimed": False,
    "generalization_claimed": False,
    "unseen_filing_accuracy_claimed": False,
    "role_a_used": False,
    "schema_used": False,
    "mapping_used": False,
    "bank_identity_used_for_routing": False,
    "filename_identity_used_for_routing": False,
    "source_path_used_for_routing": False,
    "note_number_used_for_routing": False,
    "visible_text_used_for_routing": False,
    "numeric_value_used_for_routing": False,
    "historical_values_used_for_routing": False,
    "physical_page_used_for_routing": False,
    "model_or_reader_invoked": False,
    "source_pdf_opened": False,
    "network_used": False,
}

_TOP_LEVEL_FIELDS = {
    "format_version",
    "claim_boundary",
    "status",
    "authority",
    "gate_common_contract",
    "documents",
    "page_pairs",
    "corpus_metrics",
    "public_fused_parity",
    "producer",
    "safety",
    "inventory_identity_sha256",
}
_AUTHORITY_FIELDS = {
    "finalized_v3",
    "source_inventory",
    "prestructural_inventory",
    "gate_contract",
}
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
_ARTIFACT_AUTHORITY_FIELDS = {"path", "sha256", "size_bytes", "inventory_identity_sha256"}
_GATE_CONTRACT_FIELDS = set(_GATE_CONTRACT)
_PAIR_FIELDS = {"pair_ordinal", "document_id", "previous_page", "following_page", "gate_receipt"}
_PAGE_RECEIPT_FIELDS = {
    "request_ordinal",
    "physical_page",
    "route",
    "upstream_status",
    "terminal",
    "source_projection_identity",
    "source_projection_sha256",
    "source_proposal_projection_sha256",
    "graph_identity",
    "graph_sha256",
    "source_inventory_page_identity_sha256",
    "prestructural_page_inventory_identity_sha256",
    "relation_page_binding_id",
}
_PRODUCER_FIELDS = {"git", "implementation_ledger"}
_GIT_FIELDS = {"commit", "dirty"}
_LEDGER_FIELDS = {"records", "sha256"}
_LEDGER_RECORD_FIELDS = {"phase", "kind", "path", "sha256", "size_bytes"}
_PARITY_FIELDS = {
    "all_pair_public_validation",
    "optimized_private_path",
    "required_observed_categories",
    "covered_categories",
    "pair_receipts",
    "call_count",
    "complete",
}
_PARITY_CALL_COUNT_FIELDS = {
    "distinct_sentinel_pair_count",
    "direct_public_builder_api_call_count",
    "public_validator_api_call_count",
    "total_public_builder_api_invocation_count",
}
_PARITY_PAIR_FIELDS = {
    "pair_ordinal",
    "page_pair_id",
    "covered_categories",
    "optimized_gate_artifact_identity",
    "optimized_gate_canonical_sha256",
    "public_builder_gate_artifact_identity",
    "public_validator_gate_artifact_identity",
    "public_builder_typed_exact_parity",
    "public_validator_typed_exact_parity",
}

_IMPLEMENTATION_PATHS = (
    *graph_inventory_v1._IMPLEMENTATION_PATHS,  # noqa: SLF001
    _RELATION_MODULE_PATH,
    _GATE_MODULE_PATH,
    Path(
        "src/bctc_ai/source_structure/"
        "wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1.py"
    ),
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_DOCUMENT_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SOURCE_PAGE_ID_RE = re.compile(r"^ssv2:page:[0-9a-f]{64}$")
_GRAPH_ID_RE = re.compile(r"^ssgv1:graph:[0-9a-f]{64}$")
_GRAPH_NODE_ID_RE = re.compile(r"^ssgv1:node:[0-9a-f]{64}$")
_RELATION_PAGE_BINDING_ID_RE = re.compile(r"^apgrv1:page_binding:[0-9a-f]{64}$")
_PAGE_PAIR_ID_RE = re.compile(r"^apgrv1:page_pair:[0-9a-f]{64}$")
_FRAGMENT_ID_RE = re.compile(r"^apgrv1:fragment:[0-9a-f]{64}$")
_RELATION_ID_RE = re.compile(r"^apgrv1:relation:[0-9a-f]{64}$")
_AXIS_GEOMETRY_ID_RE = re.compile(r"^apgrv1:axis_geometry:[0-9a-f]{64}$")
_AXIS_DISTANCE_ID_RE = re.compile(r"^apgrv1:axis_distance:[0-9a-f]{64}$")
_UPSTREAM_FRAGMENT_DISPOSITION_ID_RE = re.compile(r"^apgrv1:fragment_disposition:[0-9a-f]{64}$")
_UPSTREAM_AXIS_DISPOSITION_ID_RE = re.compile(r"^apgrv1:axis_disposition:[0-9a-f]{64}$")


def _error(message: str) -> Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error:
    return Wave1AdjacentPageTableGeometryCandidateGateInventoryV1Error(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise _error(message)


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


def _artifact_authority(
    path: Path, sha256_value: str, size_bytes: int, identity: str
) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "sha256": sha256_value,
        "size_bytes": size_bytes,
        "inventory_identity_sha256": identity,
    }


def _source_authority() -> dict[str, Any]:
    return _artifact_authority(
        _SOURCE_INVENTORY_RELATIVE_PATH,
        _SOURCE_INVENTORY_SHA256,
        _SOURCE_INVENTORY_SIZE_BYTES,
        _SOURCE_INVENTORY_IDENTITY_SHA256,
    )


def _prestructural_authority() -> dict[str, Any]:
    return _artifact_authority(
        _PRESTRUCTURAL_INVENTORY_RELATIVE_PATH,
        _PRESTRUCTURAL_INVENTORY_SHA256,
        _PRESTRUCTURAL_INVENTORY_SIZE_BYTES,
        _PRESTRUCTURAL_INVENTORY_IDENTITY_SHA256,
    )


def _gate_common_contract() -> dict[str, Any]:
    return {
        "format_version": gate_v1.ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_FORMAT_VERSION_V1,
        "claim_boundary": gate_v1.ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_CLAIM_BOUNDARY_V1,
        "status": gate_v1.ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_STATUS_V1,
        "policy": canonical_clone_v1(gate_v1.LOWER_QUARTILE_MARGINAL_ENVELOPE_V1),
        "policy_identity": gate_v1.LOWER_QUARTILE_MARGINAL_ENVELOPE_V1["policy_identity"],
        "safety": canonical_clone_v1(gate_v1.ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1),
        "safety_payload_sha256": _GATE_SAFETY_SHA256,
    }


_EXPECTED_GATE_COMMON = _gate_common_contract()


def _read_stable_nofollow(path: Path, label: str, *, expected_mode: int = 0o444) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or stat.S_IMODE(before.st_mode) != expected_mode
        ):
            raise _error(f"{label} is not one sealed regular file")
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
    token = lambda item: (  # noqa: E731
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
    payload = _read_stable_nofollow(
        project_root / _SOURCE_INVENTORY_RELATIVE_PATH, "compact source inventory"
    )
    if len(payload) != _SOURCE_INVENTORY_SIZE_BYTES or sha256(payload).hexdigest() != (
        _SOURCE_INVENTORY_SHA256
    ):
        raise _error("compact source inventory exact raw pin drifted")
    try:
        value = validate_wave1_source_inventory_v1(decode_canonical_json_bytes_v1(payload))
    except ValueError as exc:
        raise _error("compact source inventory contract drifted") from exc
    if value.get("inventory_identity_sha256") != _SOURCE_INVENTORY_IDENTITY_SHA256:
        raise _error("compact source inventory logical identity drifted")
    return value


def _load_prestructural_inventory(
    project_root: Path, *, source_inventory: Mapping[str, Any]
) -> dict[str, Any]:
    payload = _read_stable_nofollow(
        project_root / _PRESTRUCTURAL_INVENTORY_RELATIVE_PATH,
        "compact prestructural inventory",
    )
    if len(payload) != _PRESTRUCTURAL_INVENTORY_SIZE_BYTES or sha256(payload).hexdigest() != (
        _PRESTRUCTURAL_INVENTORY_SHA256
    ):
        raise _error("compact prestructural inventory exact raw pin drifted")
    try:
        value = graph_inventory_v1.validate_wave1_prestructural_graph_inventory_v1(
            decode_canonical_json_bytes_v1(payload),
            project_root=project_root,
            source_inventory=source_inventory,
        )
    except ValueError as exc:
        raise _error("compact prestructural inventory contract drifted") from exc
    if value.get("inventory_identity_sha256") != _PRESTRUCTURAL_INVENTORY_IDENTITY_SHA256:
        raise _error("compact prestructural inventory logical identity drifted")
    return value


def _input_raw_receipts(project_root: Path) -> dict[str, tuple[int, str]]:
    output: dict[str, tuple[int, str]] = {}
    for label, relative, expected_size, expected_sha in (
        (
            "source",
            _SOURCE_INVENTORY_RELATIVE_PATH,
            _SOURCE_INVENTORY_SIZE_BYTES,
            _SOURCE_INVENTORY_SHA256,
        ),
        (
            "prestructural",
            _PRESTRUCTURAL_INVENTORY_RELATIVE_PATH,
            _PRESTRUCTURAL_INVENTORY_SIZE_BYTES,
            _PRESTRUCTURAL_INVENTORY_SHA256,
        ),
    ):
        payload = _read_stable_nofollow(project_root / relative, f"{label} inventory")
        receipt = (len(payload), sha256(payload).hexdigest())
        if receipt != (expected_size, expected_sha):
            raise _error(f"{label} inventory changed from its exact raw pin")
        output[label] = receipt
    return output


def _producer_receipt(project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    try:
        git = sentinel._git_identity(project_root, require_clean=True)  # noqa: SLF001
        ledger = sentinel._implementation_ledger(  # noqa: SLF001
            project_root,
            git["commit"],
            _IMPLEMENTATION_PATHS,
        )
    except (OSError, subprocess.SubprocessError, sentinel.WaveOneRoleBSentinelError) as exc:
        raise _error(f"candidate-gate inventory producer is not a clean commit: {exc}") from exc
    return {
        "git": canonical_clone_v1(git),
        "implementation_ledger": canonical_clone_v1(ledger),
    }


def _validate_producer_structure(value: Any) -> dict[str, Any]:
    producer = _exact_dict(value, _PRODUCER_FIELDS, "producer")
    git = _exact_dict(producer["git"], _GIT_FIELDS, "producer Git")
    if (
        type(git["commit"]) is not str
        or _COMMIT_RE.fullmatch(git["commit"]) is None
        or git["dirty"] is not False
    ):
        raise _error("producer Git identity drifted")
    ledger = _exact_dict(producer["implementation_ledger"], _LEDGER_FIELDS, "producer ledger")
    records = ledger["records"]
    expected_paths = [path.as_posix() for path in sorted(set(_IMPLEMENTATION_PATHS))]
    if type(records) is not list or len(records) != len(expected_paths) or len(records) != 36:
        raise _error("producer runtime implementation denominator drifted")
    observed_by_path: dict[str, dict[str, Any]] = {}
    for expected_path, raw_record in zip(expected_paths, records, strict=True):
        record = _exact_dict(raw_record, _LEDGER_RECORD_FIELDS, "producer ledger record")
        if (
            record["phase"] != "READ"
            or record["kind"] != "IMPLEMENTATION"
            or record["path"] != expected_path
        ):
            raise _error("producer runtime implementation role/path drifted")
        _sha(record["sha256"], "producer implementation digest")
        _positive(record["size_bytes"], "producer implementation size")
        observed_by_path[expected_path] = record
    if _sha(ledger["sha256"], "producer ledger identity") != canonical_json_sha256_v1(records):
        raise _error("producer runtime implementation ledger identity drifted")
    relation_record = observed_by_path[_RELATION_MODULE_PATH.as_posix()]
    gate_record = observed_by_path[_GATE_MODULE_PATH.as_posix()]
    if (relation_record["sha256"], relation_record["size_bytes"]) != (
        _RELATION_MODULE_SHA256,
        _RELATION_MODULE_SIZE_BYTES,
    ):
        raise _error("runtime relation bytes differ from the gate policy upstream authority")
    if (gate_record["sha256"], gate_record["size_bytes"]) != (
        _GATE_MODULE_SHA256,
        _GATE_MODULE_SIZE_BYTES,
    ):
        raise _error("runtime gate bytes differ from the exact gate authority")
    return producer


def _validate_runtime_producer(value: Any, *, project_root: Path) -> dict[str, Any]:
    producer = _validate_producer_structure(value)
    try:
        recomputed = sentinel._implementation_ledger(  # noqa: SLF001
            project_root.resolve(),
            producer["git"]["commit"],
            _IMPLEMENTATION_PATHS,
        )
    except (OSError, subprocess.SubprocessError, sentinel.WaveOneRoleBSentinelError) as exc:
        raise _error("producer ledger cannot be replayed from its stored commit") from exc
    if not same_typed_json_v1(recomputed, producer["implementation_ledger"]):
        raise _error("stored producer ledger differs from committed runtime bytes")
    return producer


def _verify_gate_commit_authority(project_root: Path, *, current_commit: str) -> None:
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", _GATE_PRODUCER_COMMIT, current_commit],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    if ancestor.returncode:
        raise _error("pinned gate producer is not an ancestor of the inventory producer")
    for label, path, expected_sha, expected_size in (
        ("gate module", _GATE_MODULE_PATH, _GATE_MODULE_SHA256, _GATE_MODULE_SIZE_BYTES),
        ("gate focused test", _GATE_TEST_PATH, _GATE_TEST_SHA256, _GATE_TEST_SIZE_BYTES),
    ):
        try:
            payload = sentinel._git_blob(  # noqa: SLF001
                project_root,
                _GATE_PRODUCER_COMMIT,
                path,
            )
        except sentinel.WaveOneRoleBSentinelError as exc:
            raise _error(f"cannot replay pinned {label} authority") from exc
        if len(payload) != expected_size or sha256(payload).hexdigest() != expected_sha:
            raise _error(f"pinned {label} bytes drifted from the accepted gate authority")


def _validate_gate_static_authority() -> None:
    if not same_typed_json_v1(_gate_common_contract(), _EXPECTED_GATE_COMMON):
        raise _error("in-process gate common contract drifted")
    if (
        _EXPECTED_GATE_COMMON["policy_identity"] != _GATE_POLICY_IDENTITY
        or _EXPECTED_GATE_COMMON["safety_payload_sha256"] != _GATE_SAFETY_SHA256
        or canonical_json_sha256_v1(_EXPECTED_GATE_COMMON["safety"]) != _GATE_SAFETY_SHA256
        or _EXPECTED_GATE_COMMON["policy"].get("policy_identity") != _GATE_POLICY_IDENTITY
        or _EXPECTED_GATE_COMMON["policy"].get("upstream_contract", {}).get("module_sha256")
        != _RELATION_MODULE_SHA256
    ):
        raise _error("gate common contract differs from its exact accepted pins")


def _validate_build_authorities(*, project_root: Path, producer: Mapping[str, Any]) -> None:
    _validate_gate_static_authority()
    validated = _validate_runtime_producer(producer, project_root=project_root)
    _verify_gate_commit_authority(
        project_root,
        current_commit=validated["git"]["commit"],
    )


def _content_identity(prefix: str, value: Mapping[str, Any], identity_field: str) -> str:
    return prefix + canonical_json_sha256_v1(
        {key: item for key, item in value.items() if key != identity_field}
    )


def _disposition_identity(item: Mapping[str, Any], *, field: str, namespace: str) -> str:
    return _content_identity(f"apgcv1:{namespace}:", item, field)


_UPSTREAM_BINDING_FIELDS = {
    "upstream_artifact_identity",
    "upstream_artifact_sha256",
    "upstream_format_version",
    "upstream_claim_boundary",
    "upstream_status",
    "page_pair_id",
    "upstream_page_pair_disposition_id",
    "upstream_page_pair_primary_disposition",
    "fragment_ids",
    "relation_ids",
    "axis_distance_ids",
    "upstream_fragment_disposition_ids",
    "axis_geometry_ids",
    "upstream_axis_disposition_ids",
}
_RELATION_RECEIPT_FIELDS = {
    "page_pair_id",
    "relation_id",
    "relation_ordinal",
    "previous_fragment_id",
    "following_fragment_id",
    "table_shape_envelope_checks",
    "table_shape_envelope_mask",
    "table_shape_envelope_joint_pass",
    "page_boundary_envelope_checks",
    "page_boundary_envelope_mask",
    "page_boundary_envelope_joint_pass",
    "table_page_joint_envelope_mask",
    "table_page_joint_envelope_pass",
    "axis_distance_ids",
    "within_axis_envelope_distance_ids",
    "ambiguous_axis_envelope_distance_ids",
    "bidirectionally_singleton_axis_seed_link_ids",
    "bidirectionally_singleton_axis_seed_link_count",
    "minimum_bidirectionally_singleton_axis_seed_links_required",
    "relation_failure_mask",
    "relation_failure_reason_codes",
    "primary_disposition",
    "primary_reason_code",
    "geometry_supported_exploratory_seed_candidate",
    "outside_or_insufficient_is_negative_claim",
    "relation_disposition_id",
    "previous_fragment_geometry_supported_relation_degree",
    "previous_fragment_geometry_supported_relation_degree_class",
    "following_fragment_geometry_supported_relation_degree",
    "following_fragment_geometry_supported_relation_degree_class",
    "reciprocal_singleton_fragment_seed_candidate",
}
_DISTANCE_RECEIPT_FIELDS = {
    "page_pair_id",
    "relation_id",
    "axis_distance_id",
    "relation_axis_distance_ordinal",
    "previous_fragment_id",
    "following_fragment_id",
    "previous_axis_geometry_id",
    "following_axis_geometry_id",
    "axis_envelope_checks",
    "axis_envelope_mask",
    "axis_envelope_joint_pass",
    "failed_axis_envelope_components",
    "previous_axis_within_envelope_degree_in_relation",
    "following_axis_within_envelope_degree_in_relation",
    "bidirectionally_singleton_axis_seed_link",
    "primary_disposition",
    "outside_envelope_is_negative_claim",
    "axis_distance_disposition_id",
    "ordinal",
}
_FRAGMENT_RECEIPT_FIELDS = {
    "ordinal",
    "page_pair_id",
    "fragment_id",
    "side",
    "table_node_id",
    "upstream_fragment_disposition_id",
    "upstream_primary_disposition",
    "upstream_reason_code",
    "upstream_incident_relation_ids",
    "geometry_supported_relation_ids",
    "reciprocal_singleton_fragment_relation_ids",
    "geometry_supported_relation_degree",
    "geometry_supported_relation_degree_class",
    "primary_disposition",
    "unmatched_or_ambiguous_is_negative_claim",
    "fragment_disposition_id",
}
_AXIS_RECEIPT_FIELDS = {
    "ordinal",
    "page_pair_id",
    "fragment_id",
    "side",
    "axis_geometry_id",
    "axis_node_id",
    "upstream_axis_disposition_id",
    "upstream_primary_disposition",
    "upstream_reason_code",
    "upstream_incident_axis_distance_ids",
    "within_axis_envelope_distance_ids",
    "bidirectionally_singleton_axis_seed_link_ids",
    "ambiguous_axis_envelope_distance_ids",
    "outside_axis_envelope_distance_ids",
    "within_axis_envelope_degree",
    "within_axis_envelope_degree_class",
    "bidirectionally_singleton_axis_seed_link_degree",
    "bidirectionally_singleton_axis_seed_link_degree_class",
    "within_axis_envelope_distance_count",
    "bidirectionally_singleton_axis_seed_link_count",
    "ambiguous_axis_envelope_distance_count",
    "outside_axis_envelope_distance_count",
    "primary_disposition",
    "unmatched_or_ambiguous_is_negative_claim",
    "axis_disposition_id",
}
_PAIR_DISPOSITION_FIELDS = {
    "page_pair_id",
    "upstream_page_pair_disposition_id",
    "upstream_primary_disposition",
    "upstream_reason_code",
    "upstream_relation_count",
    "relation_ids",
    "geometry_supported_relation_ids",
    "reciprocal_singleton_fragment_relation_ids",
    "fragment_ambiguous_geometry_supported_relation_ids",
    "primary_disposition",
    "zero_or_ambiguous_is_negative_claim",
    "source_table_absence_claimed",
    "page_pair_disposition_id",
}
_PAIR_METRIC_FIELDS = {
    "page_pair_count",
    "input_relation_count",
    "relation_disposition_count",
    "input_axis_distance_count",
    "axis_distance_disposition_count",
    "input_fragment_count",
    "fragment_disposition_count",
    "input_physical_axis_count",
    "physical_axis_disposition_count",
    "relation_no_drop",
    "axis_distance_no_drop",
    "fragment_no_drop",
    "physical_axis_no_drop",
    "relation_disposition_counts",
    "axis_distance_disposition_counts",
    "fragment_disposition_counts",
    "physical_axis_disposition_counts",
    "fragment_geometry_supported_degree_counts",
    "physical_axis_within_envelope_degree_counts",
    "table_shape_component_pass_counts",
    "page_boundary_component_pass_counts",
    "axis_component_pass_counts",
    "table_shape_joint_pass_count",
    "page_boundary_joint_pass_count",
    "table_page_joint_pass_count",
    "axis_joint_pass_count",
    "upstream_retained_fragment_count",
    "upstream_retained_physical_axis_count",
    "upstream_page_pair_disposition_counts",
    "page_pair_disposition_counts",
}


def _compact_gate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    _require(type(value) is dict and set(value) == _GATE_FULL_FIELDS, "full gate fields drifted")
    common = {field: value[field] for field in _GATE_COMMON_FIELDS}
    if not same_typed_json_v1(common, _EXPECTED_GATE_COMMON):
        raise _error("a pair gate differs from the exact factored common contract")
    receipt = {
        "gate_artifact_identity": value["artifact_identity"],
        "gate_canonical_sha256": canonical_json_sha256_v1(value),
        "upstream_binding": canonical_clone_v1(value["upstream_binding"]),
        "relation_dispositions": canonical_clone_v1(value["relation_dispositions"]),
        "axis_distance_dispositions": canonical_clone_v1(value["axis_distance_dispositions"]),
        "fragment_dispositions": canonical_clone_v1(value["fragment_dispositions"]),
        "axis_dispositions": canonical_clone_v1(value["axis_dispositions"]),
        "page_pair_disposition": canonical_clone_v1(value["page_pair_disposition"]),
        "metrics": canonical_clone_v1(value["metrics"]),
    }
    reconstructed = _reconstruct_full_gate(_EXPECTED_GATE_COMMON, receipt)
    if not same_typed_json_v1(reconstructed, value):
        raise _error("factored gate receipt cannot reconstruct the exact full gate")
    return receipt


def _reconstruct_full_gate(common: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, Any]:
    _exact_dict(common, _GATE_COMMON_FIELDS, "gate common contract")
    _exact_dict(receipt, _GATE_RECEIPT_FIELDS, "compact gate receipt")
    return canonical_clone_v1(
        {
            "format_version": common["format_version"],
            "claim_boundary": common["claim_boundary"],
            "status": common["status"],
            "policy": common["policy"],
            "policy_identity": common["policy_identity"],
            "safety_payload_sha256": common["safety_payload_sha256"],
            "upstream_binding": receipt["upstream_binding"],
            "relation_dispositions": receipt["relation_dispositions"],
            "axis_distance_dispositions": receipt["axis_distance_dispositions"],
            "fragment_dispositions": receipt["fragment_dispositions"],
            "axis_dispositions": receipt["axis_dispositions"],
            "page_pair_disposition": receipt["page_pair_disposition"],
            "metrics": receipt["metrics"],
            "safety": common["safety"],
            "artifact_identity": receipt["gate_artifact_identity"],
        }
    )


def _ordered_unique(values: Sequence[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise _error(f"{label} identities repeat within one page-pair occurrence")


def _degree_class(value: int) -> str:
    if value == 0:
        return "ZERO"
    if value == 1:
        return "ONE"
    return "MULTIPLE"


def _fixed_counts(items: Sequence[Mapping[str, Any]], vocabulary: Sequence[str]) -> dict[str, int]:
    observed = Counter(item["primary_disposition"] for item in items)
    if not set(observed).issubset(vocabulary):
        raise _error("a gate disposition escaped its closed vocabulary")
    return {key: observed[key] for key in vocabulary}


def _boolean_mask(
    checks: Any,
    mask: Any,
    vocabulary: Sequence[str],
    label: str,
) -> dict[str, bool]:
    checked = _exact_dict(checks, set(vocabulary), f"{label} checks")
    if any(type(checked[key]) is not bool for key in vocabulary):
        raise _error(f"{label} checks must be exact booleans")
    expected = [checked[key] for key in vocabulary]
    if type(mask) is not list or mask != expected or any(type(item) is not bool for item in mask):
        raise _error(f"{label} mask drifted from its ordered checks")
    return checked


def _validate_gate_receipt(
    value: Any,
    *,
    common: Mapping[str, Any],
    expected_page_pair_id: str | None = None,
) -> dict[str, Any]:
    receipt = _exact_dict(value, _GATE_RECEIPT_FIELDS, "compact gate receipt")
    gate_identity = receipt["gate_artifact_identity"]
    if (
        type(gate_identity) is not str
        or re.fullmatch(r"apgcv1:artifact:[0-9a-f]{64}", gate_identity) is None
    ):
        raise _error("compact gate artifact identity drifted")
    _sha(receipt["gate_canonical_sha256"], "compact gate canonical identity")
    upstream = _exact_dict(
        receipt["upstream_binding"], _UPSTREAM_BINDING_FIELDS, "upstream binding"
    )
    page_pair_id = upstream["page_pair_id"]
    if (
        type(page_pair_id) is not str
        or _PAGE_PAIR_ID_RE.fullmatch(page_pair_id) is None
        or (expected_page_pair_id is not None and page_pair_id != expected_page_pair_id)
    ):
        raise _error("compact gate page-pair identity drifted")
    for field in ("upstream_artifact_sha256",):
        _sha(upstream[field], f"upstream binding {field}")
    for field, pattern in (
        ("upstream_artifact_identity", r"apgrv1:artifact:[0-9a-f]{64}"),
        ("upstream_page_pair_disposition_id", r"apgrv1:page_pair_disposition:[0-9a-f]{64}"),
    ):
        if type(upstream[field]) is not str or re.fullmatch(pattern, upstream[field]) is None:
            raise _error(f"upstream binding {field} drifted")
    if (
        upstream["upstream_format_version"]
        != relation_v1.ADJACENT_PAGE_TABLE_GEOMETRY_FORMAT_VERSION_V1
        or upstream["upstream_claim_boundary"]
        != relation_v1.ADJACENT_PAGE_TABLE_GEOMETRY_CLAIM_BOUNDARY_V1
        or upstream["upstream_status"] != relation_v1.ADJACENT_PAGE_TABLE_GEOMETRY_STATUS_V1
        or upstream["upstream_page_pair_primary_disposition"] not in _UPSTREAM_PAIR_DISPOSITIONS
    ):
        raise _error("upstream relation contract binding drifted")
    for field in (
        "fragment_ids",
        "relation_ids",
        "axis_distance_ids",
        "upstream_fragment_disposition_ids",
        "axis_geometry_ids",
        "upstream_axis_disposition_ids",
    ):
        if type(upstream[field]) is not list or any(
            type(item) is not str for item in upstream[field]
        ):
            raise _error(f"upstream binding {field} must be an ordered string list")
        _ordered_unique(upstream[field], f"upstream binding {field}")
    for field, pattern in (
        ("fragment_ids", _FRAGMENT_ID_RE),
        ("relation_ids", _RELATION_ID_RE),
        ("axis_distance_ids", _AXIS_DISTANCE_ID_RE),
        ("upstream_fragment_disposition_ids", _UPSTREAM_FRAGMENT_DISPOSITION_ID_RE),
        ("axis_geometry_ids", _AXIS_GEOMETRY_ID_RE),
        ("upstream_axis_disposition_ids", _UPSTREAM_AXIS_DISPOSITION_ID_RE),
    ):
        if any(pattern.fullmatch(item) is None for item in upstream[field]):
            raise _error(f"upstream binding {field} contains an untyped identity")

    raw_relations = receipt["relation_dispositions"]
    raw_distances = receipt["axis_distance_dispositions"]
    raw_fragments = receipt["fragment_dispositions"]
    raw_axes = receipt["axis_dispositions"]
    if any(
        type(items) is not list for items in (raw_relations, raw_distances, raw_fragments, raw_axes)
    ):
        raise _error("compact gate disposition collections must be ordered lists")
    relations = [
        _exact_dict(item, _RELATION_RECEIPT_FIELDS, "relation disposition")
        for item in raw_relations
    ]
    distances = [
        _exact_dict(item, _DISTANCE_RECEIPT_FIELDS, "axis-distance disposition")
        for item in raw_distances
    ]
    fragments = [
        _exact_dict(item, _FRAGMENT_RECEIPT_FIELDS, "fragment disposition")
        for item in raw_fragments
    ]
    axes = [
        _exact_dict(item, _AXIS_RECEIPT_FIELDS, "physical-axis disposition") for item in raw_axes
    ]

    relation_ids = [item["relation_id"] for item in relations]
    distance_ids = [item["axis_distance_id"] for item in distances]
    fragment_ids = [item["fragment_id"] for item in fragments]
    axis_ids = [item["axis_geometry_id"] for item in axes]
    for values, label in (
        (relation_ids, "relation"),
        (distance_ids, "axis-distance"),
        (fragment_ids, "fragment"),
        (axis_ids, "physical-axis"),
    ):
        _ordered_unique(values, label)
    if (
        upstream["relation_ids"] != relation_ids
        or upstream["axis_distance_ids"] != distance_ids
        or upstream["fragment_ids"] != fragment_ids
        or upstream["axis_geometry_ids"] != axis_ids
        or upstream["upstream_fragment_disposition_ids"]
        != [item["upstream_fragment_disposition_id"] for item in fragments]
        or upstream["upstream_axis_disposition_ids"]
        != [item["upstream_axis_disposition_id"] for item in axes]
    ):
        raise _error("compact gate dispositions do not close over the upstream binding")
    if [item["relation_ordinal"] for item in relations] != list(range(1, len(relations) + 1)):
        raise _error("relation disposition order drifted")
    if [item["ordinal"] for item in distances] != list(range(1, len(distances) + 1)):
        raise _error("axis-distance global disposition order drifted")
    if [item["ordinal"] for item in fragments] != list(range(1, len(fragments) + 1)):
        raise _error("fragment occurrence disposition order drifted")
    if [item["ordinal"] for item in axes] != list(range(1, len(axes) + 1)):
        raise _error("physical-axis occurrence disposition order drifted")
    for item in relations:
        _positive(item["relation_ordinal"], "relation disposition ordinal")
    for item in distances:
        _positive(item["ordinal"], "axis-distance global disposition ordinal")
    for item in fragments:
        _positive(item["ordinal"], "fragment occurrence disposition ordinal")
    for item in axes:
        _positive(item["ordinal"], "physical-axis occurrence disposition ordinal")

    fragment_by_id = {item["fragment_id"]: item for item in fragments}
    axis_by_id = {item["axis_geometry_id"]: item for item in axes}
    relation_by_id = {item["relation_id"]: item for item in relations}
    distance_by_id = {item["axis_distance_id"]: item for item in distances}
    supported_relations = [
        item for item in relations if item["geometry_supported_exploratory_seed_candidate"]
    ]
    previous_relation_degrees = Counter(
        item["previous_fragment_id"] for item in supported_relations
    )
    following_relation_degrees = Counter(
        item["following_fragment_id"] for item in supported_relations
    )
    if any(item["side"] not in {"PREVIOUS_PAGE", "FOLLOWING_PAGE"} for item in fragments):
        raise _error("fragment occurrence side drifted")
    if [item["side"] for item in fragments] != sorted(
        (item["side"] for item in fragments),
        key={"PREVIOUS_PAGE": 0, "FOLLOWING_PAGE": 1}.__getitem__,
    ):
        raise _error("fragment occurrences are not ordered previous-page then following-page")
    fragment_order = {item["fragment_id"]: index for index, item in enumerate(fragments)}
    if any(item["fragment_id"] not in fragment_order for item in axes):
        raise _error("physical-axis occurrence referenced a foreign fragment")
    if [fragment_order[item["fragment_id"]] for item in axes] != sorted(
        fragment_order[item["fragment_id"]] for item in axes
    ):
        raise _error("physical-axis occurrences are not grouped in fragment order")
    if distance_ids != [
        distance_id for relation in relations for distance_id in relation["axis_distance_ids"]
    ]:
        raise _error("global axis-distance order is not the relation-list concatenation")

    joint_by_distance: dict[str, bool] = {}
    for item in distances:
        checks = _boolean_mask(
            item["axis_envelope_checks"],
            item["axis_envelope_mask"],
            _AXIS_COMPONENTS,
            "axis envelope",
        )
        joint_by_distance[item["axis_distance_id"]] = all(checks.values())
    passing_previous_degrees = Counter(
        (item["relation_id"], item["previous_axis_geometry_id"])
        for item in distances
        if joint_by_distance[item["axis_distance_id"]]
    )
    passing_following_degrees = Counter(
        (item["relation_id"], item["following_axis_geometry_id"])
        for item in distances
        if joint_by_distance[item["axis_distance_id"]]
    )

    for item in distances:
        if item["page_pair_id"] != page_pair_id or item["relation_id"] not in relation_by_id:
            raise _error("axis-distance disposition escaped its page pair/relation")
        relation = relation_by_id[item["relation_id"]]
        if (
            item["previous_fragment_id"] != relation["previous_fragment_id"]
            or item["following_fragment_id"] != relation["following_fragment_id"]
            or item["previous_axis_geometry_id"] not in axis_by_id
            or item["following_axis_geometry_id"] not in axis_by_id
            or axis_by_id[item["previous_axis_geometry_id"]]["side"] != "PREVIOUS_PAGE"
            or axis_by_id[item["following_axis_geometry_id"]]["side"] != "FOLLOWING_PAGE"
            or axis_by_id[item["previous_axis_geometry_id"]]["fragment_id"]
            != item["previous_fragment_id"]
            or axis_by_id[item["following_axis_geometry_id"]]["fragment_id"]
            != item["following_fragment_id"]
        ):
            raise _error("axis-distance endpoint closure drifted")
        checks = item["axis_envelope_checks"]
        joint = joint_by_distance[item["axis_distance_id"]]
        previous_degree = passing_previous_degrees[
            (item["relation_id"], item["previous_axis_geometry_id"])
        ]
        following_degree = passing_following_degrees[
            (item["relation_id"], item["following_axis_geometry_id"])
        ]
        singleton = joint and previous_degree == 1 and following_degree == 1
        if (
            item["axis_envelope_joint_pass"] is not joint
            or item["failed_axis_envelope_components"]
            != [field for field in _AXIS_COMPONENTS if not checks[field]]
            or item["previous_axis_within_envelope_degree_in_relation"] != previous_degree
            or item["following_axis_within_envelope_degree_in_relation"] != following_degree
            or item["bidirectionally_singleton_axis_seed_link"] is not singleton
            or item["outside_envelope_is_negative_claim"] is not False
            or item["primary_disposition"] not in _AXIS_DISTANCE_DISPOSITIONS
        ):
            raise _error("axis-distance mask/disposition accounting drifted")
        expected_primary = (
            _AXIS_DISTANCE_DISPOSITIONS[0]
            if not joint
            else _AXIS_DISTANCE_DISPOSITIONS[2]
            if singleton
            else _AXIS_DISTANCE_DISPOSITIONS[1]
        )
        if item["primary_disposition"] != expected_primary:
            raise _error("axis-distance primary disposition drifted")
        _positive(item["relation_axis_distance_ordinal"], "axis-distance local ordinal")
        _nonnegative(
            item["previous_axis_within_envelope_degree_in_relation"],
            "axis-distance previous passing degree",
        )
        _nonnegative(
            item["following_axis_within_envelope_degree_in_relation"],
            "axis-distance following passing degree",
        )
        if item["axis_distance_disposition_id"] != _disposition_identity(
            item,
            field="axis_distance_disposition_id",
            namespace="axis_distance_disposition",
        ):
            raise _error("axis-distance disposition identity drifted")

    for relation in relations:
        if (
            relation["page_pair_id"] != page_pair_id
            or relation["previous_fragment_id"] not in fragment_by_id
            or relation["following_fragment_id"] not in fragment_by_id
            or fragment_by_id[relation["previous_fragment_id"]]["side"] != "PREVIOUS_PAGE"
            or fragment_by_id[relation["following_fragment_id"]]["side"] != "FOLLOWING_PAGE"
        ):
            raise _error("relation fragment closure drifted")
        local_distances = [
            item for item in distances if item["relation_id"] == relation["relation_id"]
        ]
        previous_axes = [
            item["axis_geometry_id"]
            for item in axes
            if item["fragment_id"] == relation["previous_fragment_id"]
            and item["side"] == "PREVIOUS_PAGE"
        ]
        following_axes = [
            item["axis_geometry_id"]
            for item in axes
            if item["fragment_id"] == relation["following_fragment_id"]
            and item["side"] == "FOLLOWING_PAGE"
        ]
        if (
            [item["relation_axis_distance_ordinal"] for item in local_distances]
            != list(range(1, len(local_distances) + 1))
            or relation["axis_distance_ids"]
            != [item["axis_distance_id"] for item in local_distances]
            or [
                (item["previous_axis_geometry_id"], item["following_axis_geometry_id"])
                for item in local_distances
            ]
            != [(left, right) for left in previous_axes for right in following_axes]
        ):
            raise _error("relation Cartesian axis-distance incidence/order drifted")
        table_checks = _boolean_mask(
            relation["table_shape_envelope_checks"],
            relation["table_shape_envelope_mask"],
            _TABLE_COMPONENTS,
            "table envelope",
        )
        page_checks = _boolean_mask(
            relation["page_boundary_envelope_checks"],
            relation["page_boundary_envelope_mask"],
            _PAGE_COMPONENTS,
            "page-boundary envelope",
        )
        expected_joint_mask = [*table_checks.values(), *page_checks.values()]
        if (
            relation["table_shape_envelope_joint_pass"] is not all(table_checks.values())
            or relation["page_boundary_envelope_joint_pass"] is not all(page_checks.values())
            or relation["table_page_joint_envelope_mask"] != expected_joint_mask
            or relation["table_page_joint_envelope_pass"] is not all(expected_joint_mask)
        ):
            raise _error("relation table/page envelope accounting drifted")
        within_ids = [
            item["axis_distance_id"] for item in local_distances if item["axis_envelope_joint_pass"]
        ]
        ambiguous_ids = [
            item["axis_distance_id"]
            for item in local_distances
            if item["primary_disposition"] == _AXIS_DISTANCE_DISPOSITIONS[1]
        ]
        singleton_ids = [
            item["axis_distance_id"]
            for item in local_distances
            if item["bidirectionally_singleton_axis_seed_link"]
        ]
        supported = all(expected_joint_mask) and len(singleton_ids) >= 2
        expected_primary = (
            _RELATION_DISPOSITIONS[0]
            if not all(expected_joint_mask)
            else _RELATION_DISPOSITIONS[1]
            if not supported
            else _RELATION_DISPOSITIONS[2]
        )
        expected_failure_mask = {
            "table_left_edge_outside_envelope": not table_checks["left_edge_within_cap"],
            "table_right_edge_outside_envelope": not table_checks["right_edge_within_cap"],
            "table_width_outside_envelope": not table_checks["width_within_cap"],
            "previous_bottom_outside_envelope": not page_checks["previous_bottom_within_cap"],
            "following_top_outside_envelope": not page_checks["following_top_within_cap"],
            "fewer_than_two_bidirectionally_singleton_axis_links": len(singleton_ids) < 2,
        }
        expected_primary_reason = (
            "ONE_OR_MORE_TABLE_OR_PAGE_ENVELOPE_COMPONENTS_FAILED"
            if not all(expected_joint_mask)
            else "UNCALIBRATED_MINIMUM_SINGLETON_AXIS_SUPPORT_NOT_MET"
            if not supported
            else "ALL_ENVELOPES_AND_CONSERVATIVE_SEED_SUPPORT_RULE_MET"
        )
        if (
            relation["within_axis_envelope_distance_ids"] != within_ids
            or relation["ambiguous_axis_envelope_distance_ids"] != ambiguous_ids
            or relation["bidirectionally_singleton_axis_seed_link_ids"] != singleton_ids
            or relation["bidirectionally_singleton_axis_seed_link_count"] != len(singleton_ids)
            or relation["minimum_bidirectionally_singleton_axis_seed_links_required"] != 2
            or relation["geometry_supported_exploratory_seed_candidate"] is not supported
            or relation["primary_disposition"] != expected_primary
            or relation["primary_reason_code"] != expected_primary_reason
            or not same_typed_json_v1(relation["relation_failure_mask"], expected_failure_mask)
            or relation["relation_failure_reason_codes"]
            != [
                _RELATION_FAILURE_CODES[field]
                for field in _RELATION_FAILURE_FIELDS
                if expected_failure_mask[field]
            ]
            or relation["outside_or_insufficient_is_negative_claim"] is not False
        ):
            raise _error("relation seed-support accounting drifted")
        for field in (
            "bidirectionally_singleton_axis_seed_link_count",
            "minimum_bidirectionally_singleton_axis_seed_links_required",
            "previous_fragment_geometry_supported_relation_degree",
            "following_fragment_geometry_supported_relation_degree",
        ):
            _nonnegative(relation[field], f"relation {field}")
        previous_degree = previous_relation_degrees[relation["previous_fragment_id"]]
        following_degree = following_relation_degrees[relation["following_fragment_id"]]
        reciprocal = supported and previous_degree == 1 and following_degree == 1
        if (
            relation["previous_fragment_geometry_supported_relation_degree"] != previous_degree
            or relation["previous_fragment_geometry_supported_relation_degree_class"]
            != _degree_class(previous_degree)
            or relation["following_fragment_geometry_supported_relation_degree"] != following_degree
            or relation["following_fragment_geometry_supported_relation_degree_class"]
            != _degree_class(following_degree)
            or relation["reciprocal_singleton_fragment_seed_candidate"] is not reciprocal
            or relation["relation_disposition_id"]
            != _disposition_identity(
                relation,
                field="relation_disposition_id",
                namespace="relation_disposition",
            )
        ):
            raise _error("relation degree/identity accounting drifted")

    for fragment in fragments:
        if (
            fragment["page_pair_id"] != page_pair_id
            or fragment["side"] not in {"PREVIOUS_PAGE", "FOLLOWING_PAGE"}
            or type(fragment["table_node_id"]) is not str
            or _GRAPH_NODE_ID_RE.fullmatch(fragment["table_node_id"]) is None
            or fragment["primary_disposition"] not in _FRAGMENT_DISPOSITIONS
            or fragment["unmatched_or_ambiguous_is_negative_claim"] is not False
        ):
            raise _error("fragment occurrence disposition drifted")
        incident = [
            item["relation_id"]
            for item in relations
            if fragment["fragment_id"]
            in {item["previous_fragment_id"], item["following_fragment_id"]}
        ]
        supported = [
            relation_id
            for relation_id in incident
            if relation_by_id[relation_id]["geometry_supported_exploratory_seed_candidate"]
        ]
        reciprocal = [
            relation_id
            for relation_id in supported
            if relation_by_id[relation_id]["reciprocal_singleton_fragment_seed_candidate"]
        ]
        degree = len(supported)
        expected_primary = (
            _FRAGMENT_DISPOSITIONS[0]
            if fragment["upstream_primary_disposition"] != "MEASURED_IN_CARTESIAN_FRAGMENT_PAIRS"
            else _FRAGMENT_DISPOSITIONS[1]
            if degree == 0
            else _FRAGMENT_DISPOSITIONS[2]
            if degree == 1 and reciprocal
            else _FRAGMENT_DISPOSITIONS[3]
            if degree == 1
            else _FRAGMENT_DISPOSITIONS[4]
        )
        expected_upstream_primary = (
            "MEASURED_IN_CARTESIAN_FRAGMENT_PAIRS"
            if incident
            else "RETAINED_WITHOUT_CROSS_PAGE_COUNTERPART"
        )
        expected_upstream_reason = (
            "FRAGMENT_PARTICIPATES_IN_EVERY_ORDERED_CARTESIAN_COUNTERPART_PAIR"
            if incident
            else "FRAGMENT_RETAINED_BECAUSE_AN_ADJACENT_PAGE_IS_UPSTREAM_TERMINAL"
            if upstream["upstream_page_pair_primary_disposition"] == "UPSTREAM_TERMINAL_BARRIER"
            else "FRAGMENT_RETAINED_BECAUSE_OPPOSITE_PAGE_HAS_ZERO_TABLE_CANDIDATES"
        )
        if (
            fragment["upstream_incident_relation_ids"] != incident
            or fragment["geometry_supported_relation_ids"] != supported
            or fragment["reciprocal_singleton_fragment_relation_ids"] != reciprocal
            or fragment["geometry_supported_relation_degree"] != degree
            or fragment["geometry_supported_relation_degree_class"] != _degree_class(degree)
            or fragment["primary_disposition"] != expected_primary
            or fragment["upstream_primary_disposition"] != expected_upstream_primary
            or fragment["upstream_reason_code"] != expected_upstream_reason
            or (
                fragment["upstream_primary_disposition"] != "MEASURED_IN_CARTESIAN_FRAGMENT_PAIRS"
                and (incident or supported or reciprocal)
            )
            or fragment["fragment_disposition_id"]
            != _disposition_identity(
                fragment,
                field="fragment_disposition_id",
                namespace="fragment_disposition",
            )
        ):
            raise _error("fragment occurrence incidence/identity accounting drifted")
        _nonnegative(
            fragment["geometry_supported_relation_degree"],
            "fragment geometry-supported relation degree",
        )

    for axis in axes:
        if (
            axis["page_pair_id"] != page_pair_id
            or axis["fragment_id"] not in fragment_by_id
            or axis["side"] != fragment_by_id[axis["fragment_id"]]["side"]
            or type(axis["axis_node_id"]) is not str
            or _GRAPH_NODE_ID_RE.fullmatch(axis["axis_node_id"]) is None
            or axis["primary_disposition"] not in _PHYSICAL_AXIS_DISPOSITIONS
            or axis["unmatched_or_ambiguous_is_negative_claim"] is not False
        ):
            raise _error("physical-axis occurrence disposition drifted")
        incident = [
            item["axis_distance_id"]
            for item in distances
            if axis["axis_geometry_id"]
            in {item["previous_axis_geometry_id"], item["following_axis_geometry_id"]}
        ]
        within = [item for item in incident if distance_by_id[item]["axis_envelope_joint_pass"]]
        singleton = [
            item
            for item in incident
            if distance_by_id[item]["bidirectionally_singleton_axis_seed_link"]
        ]
        ambiguous = [
            item
            for item in incident
            if distance_by_id[item]["primary_disposition"] == _AXIS_DISTANCE_DISPOSITIONS[1]
        ]
        outside = [
            item
            for item in incident
            if distance_by_id[item]["primary_disposition"] == _AXIS_DISTANCE_DISPOSITIONS[0]
        ]
        expected_primary = (
            _PHYSICAL_AXIS_DISPOSITIONS[0]
            if axis["upstream_primary_disposition"] != "MEASURED_IN_CARTESIAN_AXIS_PAIRS"
            else _PHYSICAL_AXIS_DISPOSITIONS[1]
            if not within
            else _PHYSICAL_AXIS_DISPOSITIONS[2]
            if not singleton
            else _PHYSICAL_AXIS_DISPOSITIONS[3]
            if len(singleton) == 1 and len(within) == 1
            else _PHYSICAL_AXIS_DISPOSITIONS[4]
        )
        expected_upstream_primary = (
            "MEASURED_IN_CARTESIAN_AXIS_PAIRS" if incident else "RETAINED_WITHOUT_AXIS_COUNTERPART"
        )
        opposite_side = "FOLLOWING_PAGE" if axis["side"] == "PREVIOUS_PAGE" else "PREVIOUS_PAGE"
        opposite_fragments = [item for item in fragments if item["side"] == opposite_side]
        opposite_axes = [item for item in axes if item["side"] == opposite_side]
        expected_upstream_reason = (
            "AXIS_PARTICIPATES_IN_EVERY_CARTESIAN_OPPOSITE_PAGE_AXIS_PAIR"
            if incident
            else "AXIS_RETAINED_BECAUSE_AN_ADJACENT_PAGE_IS_UPSTREAM_TERMINAL"
            if upstream["upstream_page_pair_primary_disposition"] == "UPSTREAM_TERMINAL_BARRIER"
            else "AXIS_RETAINED_BECAUSE_OPPOSITE_PAGE_HAS_ZERO_TABLE_CANDIDATES"
            if not opposite_fragments
            else "AXIS_RETAINED_BECAUSE_OPPOSITE_PAGE_TABLES_HAVE_ZERO_AXIS_CANDIDATES"
            if not opposite_axes
            else "INVALID_DROPPED_ELIGIBLE_COUNTERPART"
        )
        if (
            axis["upstream_incident_axis_distance_ids"] != incident
            or axis["within_axis_envelope_distance_ids"] != within
            or axis["bidirectionally_singleton_axis_seed_link_ids"] != singleton
            or axis["ambiguous_axis_envelope_distance_ids"] != ambiguous
            or axis["outside_axis_envelope_distance_ids"] != outside
            or axis["within_axis_envelope_degree"] != len(within)
            or axis["within_axis_envelope_degree_class"] != _degree_class(len(within))
            or axis["bidirectionally_singleton_axis_seed_link_degree"] != len(singleton)
            or axis["bidirectionally_singleton_axis_seed_link_degree_class"]
            != _degree_class(len(singleton))
            or axis["within_axis_envelope_distance_count"] != len(within)
            or axis["bidirectionally_singleton_axis_seed_link_count"] != len(singleton)
            or axis["ambiguous_axis_envelope_distance_count"] != len(ambiguous)
            or axis["outside_axis_envelope_distance_count"] != len(outside)
            or axis["primary_disposition"] != expected_primary
            or axis["upstream_primary_disposition"] != expected_upstream_primary
            or axis["upstream_reason_code"] != expected_upstream_reason
            or (
                axis["upstream_primary_disposition"] != "MEASURED_IN_CARTESIAN_AXIS_PAIRS"
                and incident
            )
            or axis["axis_disposition_id"]
            != _disposition_identity(
                axis,
                field="axis_disposition_id",
                namespace="axis_disposition",
            )
        ):
            raise _error("physical-axis occurrence incidence/identity accounting drifted")
        for field in (
            "within_axis_envelope_degree",
            "bidirectionally_singleton_axis_seed_link_degree",
            "within_axis_envelope_distance_count",
            "bidirectionally_singleton_axis_seed_link_count",
            "ambiguous_axis_envelope_distance_count",
            "outside_axis_envelope_distance_count",
        ):
            _nonnegative(axis[field], f"physical-axis {field}")

    pair_disposition = _exact_dict(
        receipt["page_pair_disposition"],
        _PAIR_DISPOSITION_FIELDS,
        "page-pair disposition",
    )
    supported_ids = [
        item["relation_id"]
        for item in relations
        if item["geometry_supported_exploratory_seed_candidate"]
    ]
    reciprocal_ids = [
        item["relation_id"]
        for item in relations
        if item["reciprocal_singleton_fragment_seed_candidate"]
    ]
    ambiguous_ids = [item for item in supported_ids if item not in set(reciprocal_ids)]
    expected_pair_primary = (
        _PAIR_DISPOSITIONS[0]
        if pair_disposition["upstream_primary_disposition"] != "MEASURED_CARTESIAN_FRAGMENT_PAIRS"
        else _PAIR_DISPOSITIONS[1]
        if not supported_ids
        else _PAIR_DISPOSITIONS[3]
        if ambiguous_ids
        else _PAIR_DISPOSITIONS[2]
    )
    previous_fragments = [
        item["fragment_id"] for item in fragments if item["side"] == "PREVIOUS_PAGE"
    ]
    following_fragments = [
        item["fragment_id"] for item in fragments if item["side"] == "FOLLOWING_PAGE"
    ]
    expected_relation_endpoints = [
        (left, right) for left in previous_fragments for right in following_fragments
    ]
    relation_endpoints = [
        (item["previous_fragment_id"], item["following_fragment_id"]) for item in relations
    ]
    if (
        pair_disposition["page_pair_id"] != page_pair_id
        or pair_disposition["upstream_page_pair_disposition_id"]
        != upstream["upstream_page_pair_disposition_id"]
        or pair_disposition["upstream_primary_disposition"]
        != upstream["upstream_page_pair_primary_disposition"]
        or pair_disposition["relation_ids"] != relation_ids
        or pair_disposition["upstream_relation_count"] != len(relations)
        or pair_disposition["geometry_supported_relation_ids"] != supported_ids
        or pair_disposition["reciprocal_singleton_fragment_relation_ids"] != reciprocal_ids
        or pair_disposition["fragment_ambiguous_geometry_supported_relation_ids"] != ambiguous_ids
        or pair_disposition["primary_disposition"] != expected_pair_primary
        or pair_disposition["zero_or_ambiguous_is_negative_claim"] is not False
        or pair_disposition["source_table_absence_claimed"] is not False
        or pair_disposition["page_pair_disposition_id"]
        != _disposition_identity(
            pair_disposition,
            field="page_pair_disposition_id",
            namespace="page_pair_disposition",
        )
    ):
        raise _error("page-pair disposition closure/identity drifted")
    _nonnegative(pair_disposition["upstream_relation_count"], "upstream relation count")
    upstream_primary = pair_disposition["upstream_primary_disposition"]
    expected_upstream_reason = relation_v1._PAIR_REASON[upstream_primary]  # noqa: SLF001
    if (
        (
            upstream_primary == "MEASURED_CARTESIAN_FRAGMENT_PAIRS"
            and relation_endpoints != expected_relation_endpoints
        )
        or (upstream_primary != "MEASURED_CARTESIAN_FRAGMENT_PAIRS" and relations)
        or (
            upstream_primary == "NO_PREVIOUS_TABLE_CANDIDATE"
            and (previous_fragments or not following_fragments)
        )
        or (
            upstream_primary == "NO_FOLLOWING_TABLE_CANDIDATE"
            and (following_fragments or not previous_fragments)
        )
        or (
            upstream_primary == "NO_TABLE_CANDIDATES"
            and (previous_fragments or following_fragments)
        )
        or (
            upstream_primary == "UPSTREAM_TERMINAL_BARRIER"
            and pair_disposition["upstream_relation_count"] != 0
        )
        or pair_disposition["upstream_reason_code"] != expected_upstream_reason
    ):
        raise _error("page-pair Cartesian fragment coverage/disposition drifted")

    metrics = _validate_pair_metrics(
        receipt["metrics"],
        relations=relations,
        distances=distances,
        fragments=fragments,
        axes=axes,
        pair_disposition=pair_disposition,
    )
    reconstructed = _reconstruct_full_gate(common, receipt)
    if (
        set(reconstructed) != _GATE_FULL_FIELDS
        or reconstructed["artifact_identity"]
        != _content_identity("apgcv1:artifact:", reconstructed, "artifact_identity")
        or canonical_json_sha256_v1(reconstructed) != receipt["gate_canonical_sha256"]
    ):
        raise _error("compact receipt does not reconstruct the exact gate identity/SHA")
    _require(metrics["page_pair_count"] == 1, "gate receipt must account exactly one page pair")
    return receipt


def _validate_pair_metrics(
    value: Any,
    *,
    relations: Sequence[Mapping[str, Any]],
    distances: Sequence[Mapping[str, Any]],
    fragments: Sequence[Mapping[str, Any]],
    axes: Sequence[Mapping[str, Any]],
    pair_disposition: Mapping[str, Any],
) -> dict[str, Any]:
    metrics = _exact_dict(value, _PAIR_METRIC_FIELDS, "gate pair metrics")
    for field in (
        "page_pair_count",
        "input_relation_count",
        "relation_disposition_count",
        "input_axis_distance_count",
        "axis_distance_disposition_count",
        "input_fragment_count",
        "fragment_disposition_count",
        "input_physical_axis_count",
        "physical_axis_disposition_count",
        "table_shape_joint_pass_count",
        "page_boundary_joint_pass_count",
        "table_page_joint_pass_count",
        "axis_joint_pass_count",
        "upstream_retained_fragment_count",
        "upstream_retained_physical_axis_count",
    ):
        _nonnegative(metrics[field], f"gate pair metric {field}")
    expected_scalars = {
        "page_pair_count": 1,
        "input_relation_count": len(relations),
        "relation_disposition_count": len(relations),
        "input_axis_distance_count": len(distances),
        "axis_distance_disposition_count": len(distances),
        "input_fragment_count": len(fragments),
        "fragment_disposition_count": len(fragments),
        "input_physical_axis_count": len(axes),
        "physical_axis_disposition_count": len(axes),
        "table_shape_joint_pass_count": sum(
            item["table_shape_envelope_joint_pass"] for item in relations
        ),
        "page_boundary_joint_pass_count": sum(
            item["page_boundary_envelope_joint_pass"] for item in relations
        ),
        "table_page_joint_pass_count": sum(
            item["table_page_joint_envelope_pass"] for item in relations
        ),
        "axis_joint_pass_count": sum(item["axis_envelope_joint_pass"] for item in distances),
        "upstream_retained_fragment_count": sum(
            item["upstream_primary_disposition"] != "MEASURED_IN_CARTESIAN_FRAGMENT_PAIRS"
            for item in fragments
        ),
        "upstream_retained_physical_axis_count": sum(
            item["upstream_primary_disposition"] != "MEASURED_IN_CARTESIAN_AXIS_PAIRS"
            for item in axes
        ),
    }
    if any(metrics[field] != expected for field, expected in expected_scalars.items()):
        raise _error("gate pair scalar/no-drop denominator accounting drifted")
    for field in (
        "relation_no_drop",
        "axis_distance_no_drop",
        "fragment_no_drop",
        "physical_axis_no_drop",
    ):
        if metrics[field] is not True:
            raise _error("gate pair no-drop claim is not exact true")
    expected_closed = {
        "relation_disposition_counts": _fixed_counts(relations, _RELATION_DISPOSITIONS),
        "axis_distance_disposition_counts": _fixed_counts(distances, _AXIS_DISTANCE_DISPOSITIONS),
        "fragment_disposition_counts": _fixed_counts(fragments, _FRAGMENT_DISPOSITIONS),
        "physical_axis_disposition_counts": _fixed_counts(axes, _PHYSICAL_AXIS_DISPOSITIONS),
        "fragment_geometry_supported_degree_counts": {
            key: sum(item["geometry_supported_relation_degree_class"] == key for item in fragments)
            for key in _DEGREE_CLASSES
        },
        "physical_axis_within_envelope_degree_counts": {
            key: sum(item["within_axis_envelope_degree_class"] == key for item in axes)
            for key in _DEGREE_CLASSES
        },
        "table_shape_component_pass_counts": {
            key: sum(item["table_shape_envelope_checks"][key] for item in relations)
            for key in _TABLE_COMPONENTS
        },
        "page_boundary_component_pass_counts": {
            key: sum(item["page_boundary_envelope_checks"][key] for item in relations)
            for key in _PAGE_COMPONENTS
        },
        "axis_component_pass_counts": {
            key: sum(item["axis_envelope_checks"][key] for item in distances)
            for key in _AXIS_COMPONENTS
        },
        "upstream_page_pair_disposition_counts": {
            key: int(pair_disposition["upstream_primary_disposition"] == key)
            for key in _UPSTREAM_PAIR_DISPOSITIONS
        },
        "page_pair_disposition_counts": {
            key: int(pair_disposition["primary_disposition"] == key) for key in _PAIR_DISPOSITIONS
        },
    }
    for field, expected in expected_closed.items():
        if not same_typed_json_v1(metrics[field], expected):
            raise _error(f"gate pair {field} drifted from full dispositions")
    return metrics


_ROLLUP_COUNT_FIELDS = {
    "relation_occurrence_count",
    "axis_distance_occurrence_count",
    "fragment_occurrence_count",
    "physical_axis_occurrence_count",
    "distinct_fragment_count",
    "distinct_physical_axis_count",
    "distinct_relation_count",
    "distinct_axis_distance_count",
    "relation_disposition_counts",
    "axis_distance_disposition_counts",
    "fragment_disposition_counts",
    "physical_axis_disposition_counts",
    "fragment_geometry_supported_degree_counts",
    "physical_axis_within_envelope_degree_counts",
    "table_shape_component_pass_counts",
    "page_boundary_component_pass_counts",
    "axis_component_pass_counts",
    "table_shape_joint_pass_count",
    "page_boundary_joint_pass_count",
    "table_page_joint_pass_count",
    "axis_joint_pass_count",
    "upstream_page_pair_disposition_counts",
    "page_pair_disposition_counts",
    "relation_no_drop",
    "axis_distance_no_drop",
    "fragment_no_drop",
    "physical_axis_no_drop",
}
_DOCUMENT_FIELDS = {
    "document_id",
    "page_count",
    "page_pair_count",
    "terminal_page_count",
    *_ROLLUP_COUNT_FIELDS,
}
_CORPUS_FIELDS = {
    "document_count",
    "page_count",
    "complete_page_count",
    "terminal_page_count",
    "page_pair_count",
    "excluded_cross_document_boundary_count",
    "source_accounted_page_count",
    "prestructural_node_counts",
    "public_fused_parity_distinct_pair_count",
    "public_fused_parity_direct_builder_call_count",
    "public_fused_parity_validator_call_count",
    "public_fused_parity_total_builder_invocation_count",
    "public_fused_parity_complete",
    *_ROLLUP_COUNT_FIELDS,
}


def _sum_metric_counts(
    pairs: Sequence[Mapping[str, Any]], field: str, vocabulary: Sequence[str]
) -> dict[str, int]:
    return {
        key: sum(pair["gate_receipt"]["metrics"][field][key] for pair in pairs)
        for key in vocabulary
    }


def _page_core(value: Mapping[str, Any]) -> dict[str, Any]:
    return canonical_clone_v1(value)


def _page_candidate_signature(pair: Mapping[str, Any], side: str) -> dict[str, Any]:
    receipt = pair["gate_receipt"]
    return {
        "fragments": [
            [item["fragment_id"], item["table_node_id"]]
            for item in receipt["fragment_dispositions"]
            if item["side"] == side
        ],
        "axes": [
            [item["axis_geometry_id"], item["fragment_id"], item["axis_node_id"]]
            for item in receipt["axis_dispositions"]
            if item["side"] == side
        ],
    }


def _document_pages_from_pairs(
    document_id: str, pairs: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    if not pairs:
        raise _error("every frozen Wave-1 document must contribute an adjacent pair")
    pages = [_page_core(pairs[0]["previous_page"])]
    previous_signature = _page_candidate_signature(pairs[0], "PREVIOUS_PAGE")
    for index, pair in enumerate(pairs):
        if pair["document_id"] != document_id:
            raise _error("document rollup received a foreign page pair")
        previous = _page_core(pair["previous_page"])
        following = _page_core(pair["following_page"])
        if not same_typed_json_v1(previous, pages[-1]):
            raise _error("neighbor pair page receipts do not form one exact source-order chain")
        current_previous_signature = _page_candidate_signature(pair, "PREVIOUS_PAGE")
        if not same_typed_json_v1(current_previous_signature, previous_signature):
            raise _error("neighbor pair page-local candidate signature drifted")
        if (
            following["request_ordinal"] != previous["request_ordinal"] + 1
            or following["physical_page"] != previous["physical_page"] + 1
            or pair["pair_ordinal"] <= 0
            or (index and pair["pair_ordinal"] != pairs[index - 1]["pair_ordinal"] + 1)
        ):
            raise _error("neighbor pair source/page order drifted")
        pages.append(following)
        previous_signature = _page_candidate_signature(pair, "FOLLOWING_PAGE")
    if [page["physical_page"] for page in pages] != list(range(1, len(pages) + 1)):
        raise _error("document physical pages are not an exact one-based sequence")
    return pages


def _validate_global_candidate_identity_bindings(pairs: Sequence[Mapping[str, Any]]) -> None:
    fragment_by_id: dict[str, tuple[str, str]] = {}
    fragment_id_by_binding: dict[tuple[str, str], str] = {}
    axis_by_id: dict[str, tuple[str, str, str]] = {}
    axis_identity_by_node: dict[tuple[str, str], tuple[str, str]] = {}
    for pair in pairs:
        page_identity_by_side = {
            "PREVIOUS_PAGE": pair["previous_page"]["source_projection_identity"],
            "FOLLOWING_PAGE": pair["following_page"]["source_projection_identity"],
        }
        for item in pair["gate_receipt"]["fragment_dispositions"]:
            binding = (page_identity_by_side[item["side"]], item["table_node_id"])
            fragment_id = item["fragment_id"]
            if fragment_id in fragment_by_id and fragment_by_id[fragment_id] != binding:
                raise _error("fragment identity maps to inconsistent page/table-node bindings")
            if binding in fragment_id_by_binding and fragment_id_by_binding[binding] != fragment_id:
                raise _error("one page/table-node binding maps to multiple fragment identities")
            fragment_by_id[fragment_id] = binding
            fragment_id_by_binding[binding] = fragment_id
        for item in pair["gate_receipt"]["axis_dispositions"]:
            binding = (
                page_identity_by_side[item["side"]],
                item["fragment_id"],
                item["axis_node_id"],
            )
            axis_id = item["axis_geometry_id"]
            if axis_id in axis_by_id and axis_by_id[axis_id] != binding:
                raise _error("axis identity maps to inconsistent page/fragment/node bindings")
            node_binding = (page_identity_by_side[item["side"]], item["axis_node_id"])
            node_identity = (axis_id, item["fragment_id"])
            if (
                node_binding in axis_identity_by_node
                and axis_identity_by_node[node_binding] != node_identity
            ):
                raise _error("one page axis node maps to multiple fragment/axis identities")
            axis_by_id[axis_id] = binding
            axis_identity_by_node[node_binding] = node_identity


def _rollup_pair_counts(pairs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    relation_ids = {
        item["relation_id"]
        for pair in pairs
        for item in pair["gate_receipt"]["relation_dispositions"]
    }
    distance_ids = {
        item["axis_distance_id"]
        for pair in pairs
        for item in pair["gate_receipt"]["axis_distance_dispositions"]
    }
    fragment_ids = {
        item["fragment_id"]
        for pair in pairs
        for item in pair["gate_receipt"]["fragment_dispositions"]
    }
    axis_ids = {
        item["axis_geometry_id"]
        for pair in pairs
        for item in pair["gate_receipt"]["axis_dispositions"]
    }
    return {
        "relation_occurrence_count": sum(
            pair["gate_receipt"]["metrics"]["relation_disposition_count"] for pair in pairs
        ),
        "axis_distance_occurrence_count": sum(
            pair["gate_receipt"]["metrics"]["axis_distance_disposition_count"] for pair in pairs
        ),
        "fragment_occurrence_count": sum(
            pair["gate_receipt"]["metrics"]["fragment_disposition_count"] for pair in pairs
        ),
        "physical_axis_occurrence_count": sum(
            pair["gate_receipt"]["metrics"]["physical_axis_disposition_count"] for pair in pairs
        ),
        "distinct_fragment_count": len(fragment_ids),
        "distinct_physical_axis_count": len(axis_ids),
        "distinct_relation_count": len(relation_ids),
        "distinct_axis_distance_count": len(distance_ids),
        "relation_disposition_counts": _sum_metric_counts(
            pairs, "relation_disposition_counts", _RELATION_DISPOSITIONS
        ),
        "axis_distance_disposition_counts": _sum_metric_counts(
            pairs, "axis_distance_disposition_counts", _AXIS_DISTANCE_DISPOSITIONS
        ),
        "fragment_disposition_counts": _sum_metric_counts(
            pairs, "fragment_disposition_counts", _FRAGMENT_DISPOSITIONS
        ),
        "physical_axis_disposition_counts": _sum_metric_counts(
            pairs, "physical_axis_disposition_counts", _PHYSICAL_AXIS_DISPOSITIONS
        ),
        "fragment_geometry_supported_degree_counts": _sum_metric_counts(
            pairs, "fragment_geometry_supported_degree_counts", _DEGREE_CLASSES
        ),
        "physical_axis_within_envelope_degree_counts": _sum_metric_counts(
            pairs, "physical_axis_within_envelope_degree_counts", _DEGREE_CLASSES
        ),
        "table_shape_component_pass_counts": _sum_metric_counts(
            pairs, "table_shape_component_pass_counts", _TABLE_COMPONENTS
        ),
        "page_boundary_component_pass_counts": _sum_metric_counts(
            pairs, "page_boundary_component_pass_counts", _PAGE_COMPONENTS
        ),
        "axis_component_pass_counts": _sum_metric_counts(
            pairs, "axis_component_pass_counts", _AXIS_COMPONENTS
        ),
        "table_shape_joint_pass_count": sum(
            pair["gate_receipt"]["metrics"]["table_shape_joint_pass_count"] for pair in pairs
        ),
        "page_boundary_joint_pass_count": sum(
            pair["gate_receipt"]["metrics"]["page_boundary_joint_pass_count"] for pair in pairs
        ),
        "table_page_joint_pass_count": sum(
            pair["gate_receipt"]["metrics"]["table_page_joint_pass_count"] for pair in pairs
        ),
        "axis_joint_pass_count": sum(
            pair["gate_receipt"]["metrics"]["axis_joint_pass_count"] for pair in pairs
        ),
        "upstream_page_pair_disposition_counts": _sum_metric_counts(
            pairs, "upstream_page_pair_disposition_counts", _UPSTREAM_PAIR_DISPOSITIONS
        ),
        "page_pair_disposition_counts": _sum_metric_counts(
            pairs, "page_pair_disposition_counts", _PAIR_DISPOSITIONS
        ),
        "relation_no_drop": all(
            pair["gate_receipt"]["metrics"]["relation_no_drop"] for pair in pairs
        ),
        "axis_distance_no_drop": all(
            pair["gate_receipt"]["metrics"]["axis_distance_no_drop"] for pair in pairs
        ),
        "fragment_no_drop": all(
            pair["gate_receipt"]["metrics"]["fragment_no_drop"] for pair in pairs
        ),
        "physical_axis_no_drop": all(
            pair["gate_receipt"]["metrics"]["physical_axis_no_drop"] for pair in pairs
        ),
    }


def _document_rollup(document_id: str, pairs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    pages = _document_pages_from_pairs(document_id, pairs)
    return {
        "document_id": document_id,
        "page_count": len(pages),
        "page_pair_count": len(pairs),
        "terminal_page_count": sum(page["terminal"] for page in pages),
        **_rollup_pair_counts(pairs),
    }


def _rollup_documents(
    document_ids: Sequence[str], pairs: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for pair in pairs:
        grouped[pair["document_id"]].append(pair)
    return [_document_rollup(document_id, grouped[document_id]) for document_id in document_ids]


def _corpus_rollup(
    authority: Mapping[str, Any],
    documents: Sequence[Mapping[str, Any]],
    pairs: Sequence[Mapping[str, Any]],
    parity: Mapping[str, Any],
) -> dict[str, Any]:
    pair_counts = _rollup_pair_counts(pairs)
    page_count = sum(document["page_count"] for document in documents)
    terminal_count = sum(document["terminal_page_count"] for document in documents)
    calls = parity["call_count"]
    return {
        "document_count": len(documents),
        "page_count": page_count,
        "complete_page_count": page_count - terminal_count,
        "terminal_page_count": terminal_count,
        "page_pair_count": len(pairs),
        "excluded_cross_document_boundary_count": max(len(documents) - 1, 0),
        "source_accounted_page_count": page_count,
        "prestructural_node_counts": canonical_clone_v1(_FROZEN_PRESTRUCTURAL_NODE_COUNTS),
        "public_fused_parity_distinct_pair_count": calls["distinct_sentinel_pair_count"],
        "public_fused_parity_direct_builder_call_count": calls[
            "direct_public_builder_api_call_count"
        ],
        "public_fused_parity_validator_call_count": calls["public_validator_api_call_count"],
        "public_fused_parity_total_builder_invocation_count": calls[
            "total_public_builder_api_invocation_count"
        ],
        "public_fused_parity_complete": parity["complete"],
        **pair_counts,
    }


def _validate_page_receipt(value: Any, label: str) -> dict[str, Any]:
    page = _exact_dict(value, _PAGE_RECEIPT_FIELDS, label)
    _positive(page["request_ordinal"], f"{label} request ordinal")
    _positive(page["physical_page"], f"{label} physical page")
    if (
        page["route"] not in _ROUTES
        or page["upstream_status"] not in _UPSTREAM_STATUSES
        or _STATUS_ROUTE[page["upstream_status"]] != page["route"]
        or type(page["terminal"]) is not bool
        or page["terminal"] != page["upstream_status"].startswith("UNRESOLVED_")
    ):
        raise _error(f"{label} route/status/terminal drifted")
    if (
        type(page["source_projection_identity"]) is not str
        or _SOURCE_PAGE_ID_RE.fullmatch(page["source_projection_identity"]) is None
        or type(page["graph_identity"]) is not str
        or _GRAPH_ID_RE.fullmatch(page["graph_identity"]) is None
        or type(page["relation_page_binding_id"]) is not str
        or _RELATION_PAGE_BINDING_ID_RE.fullmatch(page["relation_page_binding_id"]) is None
    ):
        raise _error(f"{label} source/graph/relation identity drifted")
    for field in (
        "source_projection_sha256",
        "source_proposal_projection_sha256",
        "graph_sha256",
        "source_inventory_page_identity_sha256",
        "prestructural_page_inventory_identity_sha256",
    ):
        _sha(page[field], f"{label} {field}")
    return page


def _validate_pair(value: Any, *, expected_ordinal: int) -> dict[str, Any]:
    pair = _exact_dict(value, _PAIR_FIELDS, "page-pair inventory entry")
    _positive(pair["pair_ordinal"], "page-pair inventory ordinal")
    if pair["pair_ordinal"] != expected_ordinal:
        raise _error("page-pair inventory ordinal drifted")
    if (
        type(pair["document_id"]) is not str
        or _DOCUMENT_ID_RE.fullmatch(pair["document_id"]) is None
    ):
        raise _error("page-pair document identity drifted")
    previous = _validate_page_receipt(pair["previous_page"], "previous-page receipt")
    following = _validate_page_receipt(pair["following_page"], "following-page receipt")
    if (
        following["request_ordinal"] != previous["request_ordinal"] + 1
        or following["physical_page"] != previous["physical_page"] + 1
        or previous["relation_page_binding_id"] == following["relation_page_binding_id"]
    ):
        raise _error("page-pair source adjacency/binding drifted")
    gate_receipt = _validate_gate_receipt(pair["gate_receipt"], common=_EXPECTED_GATE_COMMON)
    if (
        gate_receipt["upstream_binding"]["page_pair_id"]
        != gate_receipt["page_pair_disposition"]["page_pair_id"]
    ):
        raise _error("page-pair gate identity closure drifted")
    upstream_primary = gate_receipt["page_pair_disposition"]["upstream_primary_disposition"]
    if (upstream_primary == "UPSTREAM_TERMINAL_BARRIER") is not (
        previous["terminal"] or following["terminal"]
    ):
        raise _error("page-pair terminal receipt diverged from upstream terminal barrier")
    fragments = gate_receipt["fragment_dispositions"]
    axes = gate_receipt["axis_dispositions"]
    if (
        previous["terminal"]
        and any(item["side"] == "PREVIOUS_PAGE" for item in [*fragments, *axes])
    ) or (
        following["terminal"]
        and any(item["side"] == "FOLLOWING_PAGE" for item in [*fragments, *axes])
    ):
        raise _error("upstream-terminal page promoted table/axis candidates")
    return pair


def _validate_finalized_authority(value: Any) -> dict[str, Any]:
    authority = _exact_dict(value, _FINALIZED_AUTHORITY_FIELDS, "finalized V3 authority")
    for field in (
        "aggregate_artifact_sha256",
        "aggregate_identity_sha256",
        "control_artifact_sha256",
        "control_identity_sha256",
        "sealed_plan_sha256",
    ):
        _sha(authority[field], f"finalized V3 {field}")
    for field in (
        "aggregate_size_bytes",
        "control_size_bytes",
        "document_count",
        "request_count",
        "referenced_object_count",
    ):
        _positive(authority[field], f"finalized V3 {field}")
    document_ids = authority["document_ids"]
    if (
        type(document_ids) is not list
        or any(
            type(document_id) is not str or _DOCUMENT_ID_RE.fullmatch(document_id) is None
            for document_id in document_ids
        )
        or document_ids != sorted(set(document_ids))
        or len(document_ids) != authority["document_count"]
        or not same_typed_json_v1(authority, _authority_payload(FINALIZED_V3_SURVEY_AUTHORITY_V1))
    ):
        raise _error("finalized V3 exact authority drifted")
    return authority


def _validate_artifact_authority(
    value: Any, *, expected: Mapping[str, Any], label: str
) -> dict[str, Any]:
    authority = _exact_dict(value, _ARTIFACT_AUTHORITY_FIELDS, label)
    if not same_typed_json_v1(authority, expected):
        raise _error(f"{label} exact raw/logical authority pin drifted")
    return authority


def _validate_authority(value: Any) -> dict[str, Any]:
    authority = _exact_dict(value, _AUTHORITY_FIELDS, "inventory authority")
    _validate_finalized_authority(authority["finalized_v3"])
    _validate_artifact_authority(
        authority["source_inventory"],
        expected=_source_authority(),
        label="source inventory authority",
    )
    _validate_artifact_authority(
        authority["prestructural_inventory"],
        expected=_prestructural_authority(),
        label="prestructural inventory authority",
    )
    contract = _exact_dict(authority["gate_contract"], _GATE_CONTRACT_FIELDS, "gate authority")
    if not same_typed_json_v1(contract, _GATE_CONTRACT):
        raise _error("gate implementation authority pin drifted")
    if (
        contract["format_version"] != _EXPECTED_GATE_COMMON["format_version"]
        or contract["claim_boundary"] != _EXPECTED_GATE_COMMON["claim_boundary"]
        or contract["status"] != _EXPECTED_GATE_COMMON["status"]
        or contract["policy_identity"] != _EXPECTED_GATE_COMMON["policy_identity"]
        or contract["safety_payload_sha256"] != _EXPECTED_GATE_COMMON["safety_payload_sha256"]
    ):
        raise _error("gate implementation and factored common contract diverged")
    return authority


def _validate_public_parity(
    value: Any,
    *,
    pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    parity = _exact_dict(value, _PARITY_FIELDS, "public fused parity")
    if (
        parity["all_pair_public_validation"] is not False
        or parity["optimized_private_path"] is not True
    ):
        raise _error("public/optimized parity execution claim drifted")
    required = parity["required_observed_categories"]
    covered = parity["covered_categories"]
    if (
        type(required) is not list
        or required != list(_REQUIRED_PARITY_CATEGORIES)
        or type(covered) is not list
        or covered != list(_REQUIRED_PARITY_CATEGORIES)
    ):
        raise _error("public fused parity category coverage drifted")
    raw_receipts = parity["pair_receipts"]
    if type(raw_receipts) is not list:
        raise _error("public fused parity pair receipts must be an ordered list")
    pair_by_ordinal = {pair["pair_ordinal"]: pair for pair in pairs}
    receipts = [
        _exact_dict(item, _PARITY_PAIR_FIELDS, "public fused parity pair receipt")
        for item in raw_receipts
    ]
    if [item["pair_ordinal"] for item in receipts] != sorted(
        {item["pair_ordinal"] for item in receipts}
    ):
        raise _error("public fused parity sentinel pair order/identity drifted")
    observed_categories: list[str] = []
    already_covered: set[str] = set()
    for item in receipts:
        _positive(item["pair_ordinal"], "public parity pair ordinal")
        pair = pair_by_ordinal.get(item["pair_ordinal"])
        if pair is None:
            raise _error("public fused parity cited a foreign pair ordinal")
        gate_receipt = pair["gate_receipt"]
        categories = item["covered_categories"]
        expected_categories = _pair_observed_categories(pair)
        if (
            type(categories) is not list
            or not categories
            or categories != [key for key in _REQUIRED_PARITY_CATEGORIES if key in categories]
            or not set(categories).issubset(_REQUIRED_PARITY_CATEGORIES)
            or categories != expected_categories
            or set(categories).issubset(already_covered)
        ):
            raise _error("public fused parity pair categories drifted")
        observed_categories.extend(categories)
        already_covered.update(categories)
        if (
            item["page_pair_id"] != gate_receipt["upstream_binding"]["page_pair_id"]
            or item["optimized_gate_artifact_identity"] != gate_receipt["gate_artifact_identity"]
            or item["optimized_gate_canonical_sha256"] != gate_receipt["gate_canonical_sha256"]
            or item["public_builder_gate_artifact_identity"]
            != gate_receipt["gate_artifact_identity"]
            or item["public_validator_gate_artifact_identity"]
            != gate_receipt["gate_artifact_identity"]
            or item["public_builder_typed_exact_parity"] is not True
            or item["public_validator_typed_exact_parity"] is not True
        ):
            raise _error("public fused parity pair receipt drifted from its optimized gate")
    if [key for key in _REQUIRED_PARITY_CATEGORIES if key in set(observed_categories)] != covered:
        raise _error("public fused parity pair receipts do not cover every required category")
    calls = _exact_dict(parity["call_count"], _PARITY_CALL_COUNT_FIELDS, "public parity calls")
    for field in _PARITY_CALL_COUNT_FIELDS:
        _nonnegative(calls[field], f"public parity call count {field}")
    expected_count = len(receipts)
    if (
        calls["distinct_sentinel_pair_count"] != expected_count
        or calls["direct_public_builder_api_call_count"] != expected_count
        or calls["public_validator_api_call_count"] != expected_count
        or calls["total_public_builder_api_invocation_count"] != expected_count * 2
        or parity["complete"] is not True
    ):
        raise _error("public fused parity call/complete accounting drifted")
    return parity


def _pair_observed_categories(pair: Mapping[str, Any]) -> list[str]:
    receipt = pair["gate_receipt"]
    upstream_primary = receipt["page_pair_disposition"]["upstream_primary_disposition"]
    axes_by_fragment = Counter(item["fragment_id"] for item in receipt["axis_dispositions"])
    unequal = any(
        axes_by_fragment[item["previous_fragment_id"]]
        != axes_by_fragment[item["following_fragment_id"]]
        for item in receipt["relation_dispositions"]
    )
    observed = {
        "MEASURED_FRAGMENT_PAIR": upstream_primary == "MEASURED_CARTESIAN_FRAGMENT_PAIRS",
        "UNEQUAL_AXIS_COUNT_RELATION": unequal,
        "TERMINAL_BARRIER_PAIR": upstream_primary == "UPSTREAM_TERMINAL_BARRIER",
        "ZERO_COUNTERPART_PAIR": upstream_primary
        in {
            "NO_PREVIOUS_TABLE_CANDIDATE",
            "NO_FOLLOWING_TABLE_CANDIDATE",
            "NO_TABLE_CANDIDATES",
        },
    }
    return [key for key in _REQUIRED_PARITY_CATEGORIES if observed[key]]


def _validate_document_rollup(value: Any, *, expected_id: str) -> dict[str, Any]:
    document = _exact_dict(value, _DOCUMENT_FIELDS, "document gate rollup")
    if document["document_id"] != expected_id:
        raise _error("document gate rollup identity/order drifted")
    for field in (
        _DOCUMENT_FIELDS
        - {"document_id"}
        - {
            "relation_disposition_counts",
            "axis_distance_disposition_counts",
            "fragment_disposition_counts",
            "physical_axis_disposition_counts",
            "fragment_geometry_supported_degree_counts",
            "physical_axis_within_envelope_degree_counts",
            "table_shape_component_pass_counts",
            "page_boundary_component_pass_counts",
            "axis_component_pass_counts",
            "upstream_page_pair_disposition_counts",
            "page_pair_disposition_counts",
            "relation_no_drop",
            "axis_distance_no_drop",
            "fragment_no_drop",
            "physical_axis_no_drop",
        }
    ):
        _nonnegative(document[field], f"document rollup {field}")
    for field in (
        "relation_no_drop",
        "axis_distance_no_drop",
        "fragment_no_drop",
        "physical_axis_no_drop",
    ):
        if document[field] is not True:
            raise _error("document rollup no-drop flag drifted")
    for field, vocabulary in (
        ("relation_disposition_counts", _RELATION_DISPOSITIONS),
        ("axis_distance_disposition_counts", _AXIS_DISTANCE_DISPOSITIONS),
        ("fragment_disposition_counts", _FRAGMENT_DISPOSITIONS),
        ("physical_axis_disposition_counts", _PHYSICAL_AXIS_DISPOSITIONS),
        ("fragment_geometry_supported_degree_counts", _DEGREE_CLASSES),
        ("physical_axis_within_envelope_degree_counts", _DEGREE_CLASSES),
        ("table_shape_component_pass_counts", _TABLE_COMPONENTS),
        ("page_boundary_component_pass_counts", _PAGE_COMPONENTS),
        ("axis_component_pass_counts", _AXIS_COMPONENTS),
        ("upstream_page_pair_disposition_counts", _UPSTREAM_PAIR_DISPOSITIONS),
        ("page_pair_disposition_counts", _PAIR_DISPOSITIONS),
    ):
        _closed_counts(document[field], vocabulary, f"document {field}")
    return document


def validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(
    value: Any,
) -> dict[str, Any]:
    """Validate compact structure/accounting only, without source or gate replay.

    This standalone validator authenticates the embedded exact authority pins,
    reconstructs every full gate byte payload, and closes every retained
    disposition and rollup.  It cannot recompute geometry-envelope truth from
    omitted raw geometry.  Individual relation page-binding IDs are checked as
    typed opaque IDs and are extracted/proved during construction; the
    upstream relation SHA is retained only as a receipt.  This standalone
    validator cannot verify that omitted association.  Downstream authority
    therefore requires the exact raw inventory SHA-256, not this validation
    alone.
    """

    inventory = _exact_dict(value, _TOP_LEVEL_FIELDS, "Wave-1 gate inventory")
    if (
        inventory["format_version"]
        != WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_FORMAT_VERSION_V1
        or inventory["claim_boundary"]
        != WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_CLAIM_BOUNDARY_V1
        or inventory["status"] != _FORMAT_STATUS
        or not same_typed_json_v1(inventory["safety"], _SAFETY)
    ):
        raise _error("Wave-1 gate inventory header/safety drifted")
    authority = _validate_authority(inventory["authority"])
    common = _exact_dict(
        inventory["gate_common_contract"], _GATE_COMMON_FIELDS, "gate common contract"
    )
    if not same_typed_json_v1(common, _EXPECTED_GATE_COMMON):
        raise _error("gate common contract drifted from the exact factored gate")
    _validate_gate_static_authority()
    _validate_producer_structure(inventory["producer"])

    raw_pairs = inventory["page_pairs"]
    if type(raw_pairs) is not list:
        raise _error("page-pair inventory must be an ordered list")
    pairs = [
        _validate_pair(item, expected_ordinal=index) for index, item in enumerate(raw_pairs, 1)
    ]
    finalized = authority["finalized_v3"]
    if len(pairs) != finalized["request_count"] - finalized["document_count"]:
        raise _error("adjacent-pair denominator drifted from the finalized page/document authority")
    document_ids = finalized["document_ids"]
    observed_document_order: list[str] = []
    closed_documents: set[str] = set()
    for pair in pairs:
        document_id = pair["document_id"]
        if not observed_document_order or document_id != observed_document_order[-1]:
            if document_id in closed_documents:
                raise _error("page-pair documents are not contiguous")
            if observed_document_order:
                closed_documents.add(observed_document_order[-1])
            observed_document_order.append(document_id)
    if observed_document_order != document_ids:
        raise _error("page-pair document coverage/order drifted")
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for pair in pairs:
        grouped[pair["document_id"]].append(pair)
    all_pages = [
        page
        for document_id in document_ids
        for page in _document_pages_from_pairs(document_id, grouped[document_id])
    ]
    if (
        [page["request_ordinal"] for page in all_pages]
        != list(range(1, finalized["request_count"] + 1))
        or len({page["source_projection_identity"] for page in all_pages}) != len(all_pages)
        or len({page["source_projection_sha256"] for page in all_pages}) != len(all_pages)
        or len({page["source_proposal_projection_sha256"] for page in all_pages}) != len(all_pages)
        or len({page["graph_identity"] for page in all_pages}) != len(all_pages)
        or len({page["graph_sha256"] for page in all_pages}) != len(all_pages)
        or len({page["source_inventory_page_identity_sha256"] for page in all_pages})
        != len(all_pages)
        or len({page["prestructural_page_inventory_identity_sha256"] for page in all_pages})
        != len(all_pages)
        or len({page["relation_page_binding_id"] for page in all_pages}) != len(all_pages)
    ):
        raise _error("page-pair edge chain does not cover every finalized page exactly once")
    _validate_global_candidate_identity_bindings(pairs)
    relation_ids = [
        item["relation_id"]
        for pair in pairs
        for item in pair["gate_receipt"]["relation_dispositions"]
    ]
    distance_ids = [
        item["axis_distance_id"]
        for pair in pairs
        for item in pair["gate_receipt"]["axis_distance_dispositions"]
    ]
    gate_ids = [pair["gate_receipt"]["gate_artifact_identity"] for pair in pairs]
    pair_ids = [pair["gate_receipt"]["upstream_binding"]["page_pair_id"] for pair in pairs]
    if (
        len(relation_ids) != len(set(relation_ids))
        or len(distance_ids) != len(set(distance_ids))
        or len(gate_ids) != len(set(gate_ids))
        or len(pair_ids) != len(set(pair_ids))
    ):
        raise _error("globally unique pair/relation/distance identities repeat")

    documents_raw = inventory["documents"]
    if type(documents_raw) is not list or len(documents_raw) != len(document_ids):
        raise _error("document gate rollup denominator drifted")
    documents = [
        _validate_document_rollup(item, expected_id=document_id)
        for document_id, item in zip(document_ids, documents_raw, strict=True)
    ]
    expected_documents = _rollup_documents(document_ids, pairs)
    if not same_typed_json_v1(documents, expected_documents):
        raise _error("document gate rollups drifted from compact pair receipts")

    parity = _validate_public_parity(inventory["public_fused_parity"], pairs=pairs)
    corpus = _exact_dict(inventory["corpus_metrics"], _CORPUS_FIELDS, "corpus gate metrics")
    expected_corpus = _corpus_rollup(finalized, documents, pairs, parity)
    if not same_typed_json_v1(corpus, expected_corpus):
        raise _error("corpus gate metrics drifted from document/pair receipts")
    for field, expected in _FROZEN_CORPUS_DENOMINATORS.items():
        if corpus[field] != expected:
            raise _error(f"frozen Wave-1 corpus denominator drifted: {field}")
    if (
        not same_typed_json_v1(
            corpus["prestructural_node_counts"], _FROZEN_PRESTRUCTURAL_NODE_COUNTS
        )
        or corpus["source_accounted_page_count"] != corpus["page_count"]
        or corpus["complete_page_count"] + corpus["terminal_page_count"] != corpus["page_count"]
        or corpus["page_pair_count"] + corpus["excluded_cross_document_boundary_count"]
        != corpus["page_count"] - 1
        or sum(corpus["relation_disposition_counts"].values())
        != corpus["relation_occurrence_count"]
        or sum(corpus["axis_distance_disposition_counts"].values())
        != corpus["axis_distance_occurrence_count"]
        or sum(corpus["fragment_disposition_counts"].values())
        != corpus["fragment_occurrence_count"]
        or sum(corpus["physical_axis_disposition_counts"].values())
        != corpus["physical_axis_occurrence_count"]
    ):
        raise _error("corpus no-drop/authority closure drifted")
    identity = _sha(inventory["inventory_identity_sha256"], "inventory logical identity")
    if identity != canonical_json_sha256_v1(
        {key: inventory[key] for key in inventory if key != "inventory_identity_sha256"}
    ):
        raise _error("gate inventory logical identity drifted")
    return canonical_clone_v1(inventory)


def _page_context(
    *,
    authenticated_page: Any,
    delivered: int,
    source_page: Mapping[str, Any],
    prestructural_page: Mapping[str, Any],
) -> dict[str, Any]:
    record = authenticated_page.page_record
    projection = project_authenticated_page_v2(
        page_record=record,
        page_result=authenticated_page.page_result,
    )
    proposal_v1 = generate_page_geometry_proposals_v1(projection)
    proposal_v2 = make_page_proposal_set_v2(projection, proposal_set_v1=proposal_v1)
    graph = build_page_prestructural_graph_v1(projection, proposal_v2)
    graph = validate_page_prestructural_graph_v1(
        graph,
        projection=projection,
        proposal_projection=proposal_v2,
    )
    source_sha256 = projection["source_locator"]["source_sha256"]
    if (
        record["request_ordinal"] != delivered
        or record["document_id"] != source_page["document_id"]
        or record["document_id"] != prestructural_page["document_id"]
        or record["physical_page"] != source_page["physical_page"]
        or record["physical_page"] != prestructural_page["physical_page"]
        or record["document_id"] != f"sha256:{source_sha256}"
        or projection["source_local_page_id"] != source_page["projection_identity"]
        or canonical_json_sha256_v1(projection) != source_page["projection_sha256"]
        or canonical_json_sha256_v1(proposal_v2)
        != source_page["v2_geometry_proposal_projection_sha256"]
        or projection["route"] != source_page["route"]
        or projection["upstream_status"] != source_page["status"]
        or projection["terminal"] != source_page["terminal"]
    ):
        raise _error("finalized page differs from its exact compact source binding")
    reconstructed_prestructural = graph_inventory_v1._page_inventory(  # noqa: SLF001
        page_record=record,
        source_page=source_page,
        projection=projection,
        proposal_projection=proposal_v2,
        graph=graph,
    )
    if not same_typed_json_v1(reconstructed_prestructural, prestructural_page):
        raise _error("rebuilt page graph differs from the frozen compact graph inventory")
    return {
        "record": canonical_clone_v1(record),
        "projection": projection,
        "proposal": proposal_v2,
        "graph": graph,
        "source_page": source_page,
        "prestructural_page": prestructural_page,
        "graph_sha256": canonical_json_sha256_v1(graph),
    }


def _relation_inputs_from_contexts(
    previous: Mapping[str, Any], following: Mapping[str, Any]
) -> relation_v1._AdjacentInputs:  # noqa: SLF001
    previous_projection = previous["projection"]
    following_projection = following["projection"]
    previous_locator = previous_projection["source_locator"]
    following_locator = following_projection["source_locator"]
    previous_record = previous_projection["page_record_v2"]
    following_record = following_projection["page_record_v2"]
    if (
        previous_record["document_id"] != following_record["document_id"]
        or previous_locator["source_sha256"] != following_locator["source_sha256"]
        or previous_locator["source_size_bytes"] != following_locator["source_size_bytes"]
        or previous_projection["source_local_page_id"]
        == following_projection["source_local_page_id"]
        or following_locator["physical_page"] != previous_locator["physical_page"] + 1
    ):
        raise _error("optimized pair does not satisfy the exact public adjacency preconditions")
    return relation_v1._AdjacentInputs(  # noqa: SLF001
        previous=relation_v1._PageInputs(  # noqa: SLF001
            source=previous_projection,
            proposals=previous["proposal"],
            graph=previous["graph"],
        ),
        following=relation_v1._PageInputs(  # noqa: SLF001
            source=following_projection,
            proposals=following["proposal"],
            graph=following["graph"],
        ),
    )


def _relation_page_receipt(
    context: Mapping[str, Any], *, relation_page_binding_id: str
) -> dict[str, Any]:
    source = context["source_page"]
    prestructural = context["prestructural_page"]
    return {
        "request_ordinal": context["record"]["request_ordinal"],
        "physical_page": context["record"]["physical_page"],
        "route": context["projection"]["route"],
        "upstream_status": context["projection"]["upstream_status"],
        "terminal": context["projection"]["terminal"],
        "source_projection_identity": context["projection"]["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(context["projection"]),
        "source_proposal_projection_sha256": canonical_json_sha256_v1(context["proposal"]),
        "graph_identity": context["graph"]["graph_identity"],
        "graph_sha256": context["graph_sha256"],
        "source_inventory_page_identity_sha256": source["page_inventory_identity_sha256"],
        "prestructural_page_inventory_identity_sha256": prestructural[
            "page_inventory_identity_sha256"
        ],
        "relation_page_binding_id": relation_page_binding_id,
    }


def _optimized_pair(
    previous: Mapping[str, Any],
    following: Mapping[str, Any],
    *,
    pair_ordinal: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        relation = relation_v1._derive(  # noqa: SLF001
            _relation_inputs_from_contexts(previous, following)
        )
        gate = gate_v1._derive_from_validated_relation(relation)  # noqa: SLF001
    except ValueError as exc:
        raise _error("optimized adjacent-page relation/gate derivation failed") from exc
    previous_binding = relation["ordered_page_pair"]["previous_page_binding"]
    following_binding = relation["ordered_page_pair"]["following_page_binding"]
    receipt = _compact_gate_receipt(gate)
    _validate_gate_receipt(
        receipt,
        common=_EXPECTED_GATE_COMMON,
        expected_page_pair_id=relation["ordered_page_pair"]["page_pair_id"],
    )
    pair = {
        "pair_ordinal": pair_ordinal,
        "document_id": previous["record"]["document_id"],
        "previous_page": _relation_page_receipt(
            previous,
            relation_page_binding_id=previous_binding["page_binding_id"],
        ),
        "following_page": _relation_page_receipt(
            following,
            relation_page_binding_id=following_binding["page_binding_id"],
        ),
        "gate_receipt": receipt,
    }
    return pair, gate


def _gate_args(
    previous: Mapping[str, Any], following: Mapping[str, Any]
) -> tuple[Mapping[str, Any], ...]:
    return (
        previous["projection"],
        previous["proposal"],
        previous["graph"],
        following["projection"],
        following["proposal"],
        following["graph"],
    )


def _build_public_fused_parity(
    sentinels: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    observed: set[str] = set()
    for pair_ordinal in sorted(sentinels):
        sentinel_context = sentinels[pair_ordinal]
        pair = sentinel_context["pair"]
        optimized_gate = sentinel_context["gate"]
        categories = _pair_observed_categories(pair)
        if not set(categories) - observed:
            continue
        args = _gate_args(sentinel_context["previous"], sentinel_context["following"])
        try:
            public_built = gate_v1.build_adjacent_page_table_geometry_candidate_gate_v1(*args)
            public_validated = gate_v1.validate_adjacent_page_table_geometry_candidate_gate_v1(
                public_built,
                previous_projection=args[0],
                previous_proposal_projection=args[1],
                previous_graph=args[2],
                following_projection=args[3],
                following_proposal_projection=args[4],
                following_graph=args[5],
            )
        except ValueError as exc:
            raise _error("bounded fused public gate parity replay failed") from exc
        builder_parity = same_typed_json_v1(public_built, optimized_gate)
        validator_parity = same_typed_json_v1(public_validated, optimized_gate)
        if not builder_parity or not validator_parity:
            raise _error("optimized gate differs from its bounded fused public parity replay")
        receipts.append(
            {
                "pair_ordinal": pair_ordinal,
                "page_pair_id": pair["gate_receipt"]["upstream_binding"]["page_pair_id"],
                "covered_categories": categories,
                "optimized_gate_artifact_identity": optimized_gate["artifact_identity"],
                "optimized_gate_canonical_sha256": canonical_json_sha256_v1(optimized_gate),
                "public_builder_gate_artifact_identity": public_built["artifact_identity"],
                "public_validator_gate_artifact_identity": public_validated["artifact_identity"],
                "public_builder_typed_exact_parity": builder_parity,
                "public_validator_typed_exact_parity": validator_parity,
            }
        )
        observed.update(categories)
    if observed != set(_REQUIRED_PARITY_CATEGORIES):
        missing = sorted(set(_REQUIRED_PARITY_CATEGORIES) - observed)
        raise _error(f"frozen corpus did not exercise required public parity categories: {missing}")
    count = len(receipts)
    return {
        "all_pair_public_validation": False,
        "optimized_private_path": True,
        "required_observed_categories": list(_REQUIRED_PARITY_CATEGORIES),
        "covered_categories": list(_REQUIRED_PARITY_CATEGORIES),
        "pair_receipts": receipts,
        "call_count": {
            "distinct_sentinel_pair_count": count,
            "direct_public_builder_api_call_count": count,
            "public_validator_api_call_count": count,
            # The public validator performs one internal public-builder replay.
            "total_public_builder_api_invocation_count": count * 2,
        },
        "complete": True,
    }


def _build_pairs(
    project_root: Path,
    *,
    source_inventory: Mapping[str, Any],
    prestructural_inventory: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], FinalizedV3SurveyAuthority]:
    source_pages = source_inventory["pages"]
    prestructural_pages = prestructural_inventory["pages"]
    if len(source_pages) != len(prestructural_pages):
        raise _error("source and prestructural page denominators diverged")
    pairs: list[dict[str, Any]] = []
    sentinels: dict[int, dict[str, Any]] = {}
    covered_categories: set[str] = set()
    previous: dict[str, Any] | None = None
    cross_document_boundaries = 0
    with open_finalized_v3_survey_stream_v1(project_root) as stream:
        authority = stream.authority
        for delivered, authenticated_page in enumerate(stream, start=1):
            if delivered > len(source_pages):
                raise _error("finalized V3 stream exceeded its frozen page denominator")
            current = _page_context(
                authenticated_page=authenticated_page,
                delivered=delivered,
                source_page=source_pages[delivered - 1],
                prestructural_page=prestructural_pages[delivered - 1],
            )
            if previous is not None:
                previous_record = previous["record"]
                current_record = current["record"]
                if previous_record["document_id"] == current_record["document_id"]:
                    if current_record["physical_page"] != previous_record["physical_page"] + 1:
                        raise _error("same-document finalized pages are not physically adjacent")
                    pair, optimized_gate = _optimized_pair(
                        previous,
                        current,
                        pair_ordinal=len(pairs) + 1,
                    )
                    pairs.append(pair)
                    categories = _pair_observed_categories(pair)
                    if set(categories) - covered_categories:
                        sentinels[pair["pair_ordinal"]] = {
                            "pair": pair,
                            "gate": optimized_gate,
                            "previous": previous,
                            "following": current,
                        }
                        covered_categories.update(categories)
                else:
                    cross_document_boundaries += 1
                    if current_record["physical_page"] != 1:
                        raise _error("new finalized document did not restart at physical page one")
            elif current["record"]["physical_page"] != 1:
                raise _error("first finalized document did not start at physical page one")
            previous = current
    if (
        len(source_pages) != authority.request_count
        or len(pairs) != authority.request_count - authority.document_count
        or cross_document_boundaries != authority.document_count - 1
    ):
        raise _error("finalized page/pair/cross-document denominator drifted")
    if not same_typed_json_v1(source_inventory["authority"], _authority_payload(authority)):
        raise _error("source inventory and live finalized V3 authority diverged")
    if not same_typed_json_v1(
        prestructural_inventory["authority"]["finalized_v3"], _authority_payload(authority)
    ):
        raise _error("prestructural inventory and live finalized V3 authority diverged")
    parity = _build_public_fused_parity(sentinels)
    return pairs, parity, authority


def build_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(
    project_root: Path,
) -> dict[str, Any]:
    """Build one exhaustive optimized blind replay without publishing it."""

    project_root = project_root.resolve()
    producer_before = _producer_receipt(project_root)
    _validate_build_authorities(project_root=project_root, producer=producer_before)
    raw_before = _input_raw_receipts(project_root)
    source = _load_source_inventory(project_root)
    prestructural = _load_prestructural_inventory(project_root, source_inventory=source)
    if not same_typed_json_v1(prestructural["authority"]["source_inventory"], _source_authority()):
        raise _error("prestructural inventory does not bind the exact compact source artifact")
    if not same_typed_json_v1(
        prestructural["corpus_metrics"]["node_counts"], _FROZEN_PRESTRUCTURAL_NODE_COUNTS
    ):
        raise _error("prestructural candidate node denominators drifted")
    pairs, parity, authority = _build_pairs(
        project_root,
        source_inventory=source,
        prestructural_inventory=prestructural,
    )
    if _input_raw_receipts(project_root) != raw_before:
        raise _error("source/prestructural raw authorities changed during gate construction")
    producer_after = _producer_receipt(project_root)
    if not same_typed_json_v1(producer_before, producer_after):
        raise _error("candidate-gate inventory producer changed during construction")
    finalized = _authority_payload(authority)
    documents = _rollup_documents(authority.document_ids, pairs)
    inventory: dict[str, Any] = {
        "format_version": (
            WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_FORMAT_VERSION_V1
        ),
        "claim_boundary": (
            WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_CLAIM_BOUNDARY_V1
        ),
        "status": _FORMAT_STATUS,
        "authority": {
            "finalized_v3": finalized,
            "source_inventory": _source_authority(),
            "prestructural_inventory": _prestructural_authority(),
            "gate_contract": canonical_clone_v1(_GATE_CONTRACT),
        },
        "gate_common_contract": canonical_clone_v1(_EXPECTED_GATE_COMMON),
        "documents": documents,
        "page_pairs": pairs,
        "corpus_metrics": _corpus_rollup(finalized, documents, pairs, parity),
        "public_fused_parity": parity,
        "producer": producer_before,
        "safety": canonical_clone_v1(_SAFETY),
    }
    inventory["inventory_identity_sha256"] = canonical_json_sha256_v1(inventory)
    return validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(inventory)


def _open_output_directory(project_root: Path) -> tuple[Path, int]:
    relative_parent = (
        WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_OUTPUT_RELATIVE_PATH_V1.parent
    )
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
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise _error("candidate-gate inventory output parent is not a directory")
    except Exception:
        os.close(descriptor)
        raise
    return project_root / relative_parent, descriptor


def _require_destination_absent(project_root: Path) -> None:
    _parent, directory_fd = _open_output_directory(project_root)
    try:
        try:
            os.stat(
                WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_OUTPUT_RELATIVE_PATH_V1.name,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return
        raise _error("candidate-gate inventory destination already exists")
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
            raise _error("published candidate-gate inventory is not regular")
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
    token = lambda item: (  # noqa: E731
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
        raise _error("published candidate-gate inventory changed during validation")
    return b"".join(chunks), after


def _publish_canonical_exclusive(project_root: Path, payload: bytes) -> Path:
    if not payload.endswith(b"\n") or payload.endswith(b"\n\n"):
        raise _error("candidate-gate publication is not canonical newline JSON")
    try:
        decode_canonical_json_bytes_v1(payload)
    except ValueError as exc:
        raise _error("candidate-gate publication bytes are not canonical JSON") from exc
    parent, directory_fd = _open_output_directory(project_root)
    filename = (
        WAVE1_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_INVENTORY_OUTPUT_RELATIVE_PATH_V1.name
    )
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
            raise _error("candidate-gate publication temporary already exists")
        try:
            os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise _error("candidate-gate inventory destination already exists")
        descriptor = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise _error("owned candidate-gate publication identity drifted")
        owned_identity = (opened.st_dev, opened.st_ino)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise _error("candidate-gate publication write made no progress")
            offset += written
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o444)
        os.fsync(descriptor)
        sealed = os.fstat(descriptor)
        if (
            not stat.S_ISREG(sealed.st_mode)
            or stat.S_IMODE(sealed.st_mode) != 0o444
            or sealed.st_nlink != 1
            or sealed.st_size != len(payload)
        ):
            raise _error("candidate-gate sealed temporary identity drifted")
        try:
            os.link(
                temporary_name,
                filename,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            raise _error("candidate-gate publication lost its exclusive race") from exc
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
            raise _error("linked candidate-gate publication identity drifted")
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
            raise _error("published candidate-gate inventory bytes/topology drifted")
    except OSError as exc:
        raise _error("candidate-gate inventory publication failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if final_linked and not publication_committed and owned_identity is not None:
            try:
                observed_final = os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                observed_final = None
            if (
                observed_final is not None
                and (
                    observed_final.st_dev,
                    observed_final.st_ino,
                )
                == owned_identity
            ):
                os.unlink(filename, dir_fd=directory_fd)
                os.fsync(directory_fd)
        if owned_identity is not None:
            try:
                observed = os.stat(temporary_name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                observed = None
            if observed is not None and (observed.st_dev, observed.st_ino) == owned_identity:
                os.unlink(temporary_name, dir_fd=directory_fd)
                os.fsync(directory_fd)
        os.close(directory_fd)
    return parent / filename


def publish_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(
    project_root: Path,
) -> tuple[Path, str, int, str]:
    """Build, recheck exact inputs/producer, then exclusively seal one artifact."""

    project_root = project_root.resolve()
    _require_destination_absent(project_root)
    inventory = build_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(project_root)
    validate_wave1_adjacent_page_table_geometry_candidate_gate_inventory_v1(inventory)
    _input_raw_receipts(project_root)
    producer = _producer_receipt(project_root)
    if not same_typed_json_v1(producer, inventory["producer"]):
        raise _error("candidate-gate producer changed before publication")
    _validate_build_authorities(project_root=project_root, producer=producer)
    payload = canonical_json_bytes_v1(inventory)
    path = _publish_canonical_exclusive(project_root, payload)
    return (
        path,
        sha256(payload).hexdigest(),
        len(payload),
        inventory["inventory_identity_sha256"],
    )
