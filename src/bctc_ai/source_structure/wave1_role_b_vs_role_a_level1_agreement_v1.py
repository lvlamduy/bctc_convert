"""Compare sealed Role-B hypotheses with the sealed Role-A Level-1 reference.

The comparison is diagnostic only.  Role-B candidates remain hypotheses and
Role-A remains a machine reference rather than human gold.  Documents are
joined solely by source SHA-256; bank labels are copied only as output
provenance and never participate in selection or comparison behavior.

Publication is exclusive and crash-bounded: canonical bytes are sealed in an
owned temporary inode and atomically hard-linked to the absent final name.
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

from bctc_ai.corpus import wave1_role_a_level1_boundaries as role_a_level1
from bctc_ai.corpus import wave1_role_b_sentinel as sentinel
from bctc_ai.source_structure import (
    wave1_document_statement_hypotheses_inventory_v1 as role_b_inventory_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)

__all__ = [
    "WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_CLAIM_BOUNDARY_V1",
    "WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_FORMAT_VERSION_V1",
    "WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_OUTPUT_RELATIVE_PATH_V1",
    "Wave1RoleBVsRoleALevel1AgreementV1Error",
    "build_wave1_role_b_vs_role_a_level1_agreement_v1",
    "publish_wave1_role_b_vs_role_a_level1_agreement_v1",
    "validate_wave1_role_b_vs_role_a_level1_agreement_v1",
]


class Wave1RoleBVsRoleALevel1AgreementV1Error(ValueError):
    """The sealed Level-1 agreement boundary was crossed or became ambiguous."""


WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_FORMAT_VERSION_V1 = (
    "BANK_CORPUS_WAVE_1_ROLE_B_VS_ROLE_A_LEVEL_1_AGREEMENT_V1"
)
WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_CLAIM_BOUNDARY_V1 = (
    "ROLE_B_HYPOTHESIS_VS_SEALED_ROLE_A_LEVEL_1_MACHINE_REFERENCE_"
    "DIAGNOSTICS_ONLY_NO_ACCURACY_OR_SEMANTIC_ACCEPTANCE"
)
WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_OUTPUT_RELATIVE_PATH_V1 = Path(
    "output/development/bank-corpus-survey-v1/wave-1-role-b-vs-role-a-level-1-agreement-v1.json"
)

_ROLE_B_RELATIVE_PATH = Path(
    "output/development/bank-corpus-survey-v1/wave-1-role-b-document-statement-hypotheses-v1.json"
)
_ROLE_B_SHA256 = "9e4c849ec17d01cc683df223bc44c29f0949bf4d8b46c557144537056bcc15b8"
_ROLE_B_SIZE_BYTES = 1_908_210
_ROLE_B_LOGICAL_IDENTITY = "b6b6c2153fd39af2a85ecb9de144b9b8ac6df9d5fdbaf0fa2c9db791dbaaaba7"
_ROLE_A_RELATIVE_PATH = Path(
    "output/development/bank-corpus-survey-v1/wave-1-role-a-level-1-statement-boundaries.json"
)
_ROLE_A_SHA256 = "2be9843943114602ab6a1e901dbb475ca80642068cfe31b1ba7e0a6d550c3577"
_ROLE_A_SIZE_BYTES = 98_577
_SOURCE_INVENTORY_RELATIVE_PATH = Path(
    "output/development/bank-corpus-survey-v1/wave-1-role-b-source-first-inventory-v1.json"
)
_SOURCE_INVENTORY_SHA256 = "c20c9b42ff6f96baf6eff6607e12b27681146d8d968e4e86f0e792bde1429162"
_SOURCE_INVENTORY_SIZE_BYTES = 1_920_845
_SOURCE_INVENTORY_IDENTITY = "63c5988b80cc9893cc20f1b7476d9124880c838d8e4bc6a9d5f4df195550ad84"

_ROLE_B_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_DOCUMENT_STATEMENT_HYPOTHESES_INVENTORY_V1"
_ROLE_B_STATUS = "COMPLETE_CANDIDATE_HYPOTHESIS_INVENTORY"
_ROLE_B_CLAIM = (
    "EXHAUSTIVE_DOCUMENT_AND_PAGE_STATEMENT_BLOCK_HYPOTHESES_ONLY_"
    "NO_SEMANTIC_ACCEPTANCE_MAPPING_SCOPE_OR_ABSENCE_TRUTH"
)
_ROLE_A_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_A_LEVEL_1_BOUNDARIES_V1"
_ROLE_A_STATUS = "ROLE_A_LEVEL_1_MACHINE_REFERENCE"
_ROLE_A_CLAIM = "STRUCTURAL_BOUNDARIES_ONLY"
_OUTPUT_STATUS = "COMPLETE_MACHINE_REFERENCE_AGREEMENT_DIAGNOSTICS"

_ROLE_A_PRIMARY_FAMILIES = (
    "CDKT",
    "KQKD",
    "LCTT",
    "TM",
    "TABLE_OF_CONTENTS",
    "OTHER",
)
_ROLE_B_COMPLETE_FAMILIES = (
    "CDKT",
    "KQKD",
    "LCTT",
    "TM",
    "TABLE_OF_CONTENTS",
    "AUDIT_REPORT",
    "AMBIGUOUS",
    "OTHER",
)
_RANGE_FAMILIES = ("CDKT", "KQKD", "LCTT")
_MAIN_FAMILIES = (*_RANGE_FAMILIES, "TM")
_REFERENCE_BLOCK_TYPE = {
    "CDKT": "CDKT_MAIN",
    "KQKD": "KQKD",
    "LCTT": "LCTT",
    "TM": "TM",
}
_PRIMARY_SEGMENT_FAMILY = {
    "CDKT_MAIN": "CDKT",
    "KQKD": "KQKD",
    "LCTT": "LCTT",
    "TM": "TM",
    "TABLE_OF_CONTENTS": "TABLE_OF_CONTENTS",
}
_FAILURE_CLASSES = (
    "ZERO_CANDIDATE_WITH_TERMINAL_BARRIER",
    "ZERO_CANDIDATE_WITHOUT_TERMINAL_BARRIER",
    "MULTI_ALTERNATIVE_HYPOTHESES",
    "TOP1_CDKT_OVERLAP_NOT_EXACT",
)

_SAFETY = {
    "agreement_is_machine_reference_diagnostic_only": True,
    "human_gold": False,
    "accuracy_claimed": False,
    "role_b_hypothesis_promoted_to_truth": False,
    "statement_block_accepted": False,
    "statement_family_accepted": False,
    "table_claimed": False,
    "row_claimed": False,
    "cell_claimed": False,
    "axis_claimed": False,
    "tm_coverage_claimed": False,
    "off_balance_block_inferred_by_role_b": False,
    "off_balance_signal_is_diagnostic_only": True,
    "role_a_off_balance_compared_only_on_separate_signal_axis": True,
    "other_family_is_closed_comparison_projection_not_semantic_truth": True,
    "absence_claimed": False,
    "mapping_claimed": False,
    "scope_truth_claimed": False,
    "schema_truth_claimed": False,
    "role_a_used_for_discovery_or_routing": False,
    "bank_identity_used_for_join_or_routing": False,
    "document_name_used_for_join_or_routing": False,
    "source_sha256_is_sole_document_join_key": True,
    "raw_artifacts_exact_sha256_pinned": True,
    "raw_text_persisted": False,
    "pdf_or_model_or_ocr_invoked": False,
}

_TOP_LEVEL_FIELDS = {
    "format_version",
    "status",
    "claim_boundary",
    "authority",
    "documents",
    "corpus_metrics",
    "failure_class_rollups",
    "producer",
    "safety",
    "agreement_identity_sha256",
}
_PRODUCER_FIELDS = {"git", "implementation_ledger"}
_GIT_FIELDS = {"commit", "dirty"}
_LEDGER_FIELDS = {"records", "sha256"}
_LEDGER_RECORD_FIELDS = {"phase", "kind", "path", "sha256", "size_bytes"}
_IMPLEMENTATION_RELATIVE_PATH = Path(
    "src/bctc_ai/source_structure/wave1_role_b_vs_role_a_level1_agreement_v1.py"
)
_IMPLEMENTATION_PATHS = tuple(
    sorted(
        {
            *role_b_inventory_v1._IMPLEMENTATION_PATHS,  # noqa: SLF001
            Path("src/bctc_ai/corpus/wave1_role_a_level1_boundaries.py"),
            _IMPLEMENTATION_RELATIVE_PATH,
        }
    )
)

_FINALIZED_CONFUSION = {
    "CDKT": {
        "CDKT": 44,
        "KQKD": 0,
        "LCTT": 0,
        "TM": 0,
        "TABLE_OF_CONTENTS": 0,
        "AUDIT_REPORT": 0,
        "AMBIGUOUS": 0,
        "OTHER": 11,
    },
    "KQKD": {
        "CDKT": 0,
        "KQKD": 27,
        "LCTT": 0,
        "TM": 0,
        "TABLE_OF_CONTENTS": 0,
        "AUDIT_REPORT": 0,
        "AMBIGUOUS": 0,
        "OTHER": 5,
    },
    "LCTT": {
        "CDKT": 0,
        "KQKD": 0,
        "LCTT": 41,
        "TM": 1,
        "TABLE_OF_CONTENTS": 0,
        "AUDIT_REPORT": 0,
        "AMBIGUOUS": 0,
        "OTHER": 15,
    },
    "TM": {
        "CDKT": 1,
        "KQKD": 0,
        "LCTT": 1,
        "TM": 795,
        "TABLE_OF_CONTENTS": 2,
        "AUDIT_REPORT": 0,
        "AMBIGUOUS": 1,
        "OTHER": 347,
    },
    "TABLE_OF_CONTENTS": {
        "CDKT": 1,
        "KQKD": 0,
        "LCTT": 0,
        "TM": 0,
        "TABLE_OF_CONTENTS": 10,
        "AUDIT_REPORT": 0,
        "AMBIGUOUS": 2,
        "OTHER": 1,
    },
    "OTHER": {
        "CDKT": 19,
        "KQKD": 0,
        "LCTT": 0,
        "TM": 0,
        "TABLE_OF_CONTENTS": 0,
        "AUDIT_REPORT": 0,
        "AMBIGUOUS": 0,
        "OTHER": 66,
    },
}
_FINALIZED_METRIC_PROJECTION = {
    "document_count": 27,
    "page_count": 1_449,
    "complete_page_count": 1_390,
    "terminal_page_count": 59,
    "complete_family_agreement_count": 983,
    "complete_family_disagreement_count": 407,
    "role_a_reference_block_count": 139,
    "role_a_main_reference_block_count": 111,
    "role_a_reference_block_counts": {
        "CDKT_MAIN": 28,
        "OFF_BALANCE": 28,
        "KQKD": 28,
        "LCTT": 28,
        "TM": 27,
    },
    "role_b_block_hypothesis_count": 24,
    "top1": {
        "candidate_comparison_count": 52,
        "reference_denominator": 111,
        "exact_candidate_match_count": 40,
        "overlap_candidate_match_count": 52,
        "exact_candidate_precision_against_machine_reference": 0.769230769231,
        "overlap_candidate_precision_against_machine_reference": 1.0,
        "unique_exact_reference_match_count": 40,
        "unique_overlap_reference_match_count": 52,
        "exact_candidate_match_counts_by_family": {
            "CDKT": 1,
            "KQKD": 13,
            "LCTT": 13,
            "TM": 13,
        },
        "overlap_candidate_match_counts_by_family": {
            "CDKT": 13,
            "KQKD": 13,
            "LCTT": 13,
            "TM": 13,
        },
        "unique_exact_reference_match_counts_by_family": {
            "CDKT": 1,
            "KQKD": 13,
            "LCTT": 13,
            "TM": 13,
        },
        "unique_overlap_reference_match_counts_by_family": {
            "CDKT": 13,
            "KQKD": 13,
            "LCTT": 13,
            "TM": 13,
        },
    },
    "oracle_any": {
        "candidate_comparison_count": 96,
        "reference_denominator": 111,
        "exact_candidate_match_count": 73,
        "overlap_candidate_match_count": 96,
        "exact_candidate_precision_against_machine_reference": 0.760416666667,
        "overlap_candidate_precision_against_machine_reference": 1.0,
        "unique_exact_reference_match_count": 40,
        "unique_overlap_reference_match_count": 52,
        "exact_candidate_match_counts_by_family": {
            "CDKT": 1,
            "KQKD": 24,
            "LCTT": 24,
            "TM": 24,
        },
        "overlap_candidate_match_counts_by_family": {
            "CDKT": 24,
            "KQKD": 24,
            "LCTT": 24,
            "TM": 24,
        },
        "unique_exact_reference_match_counts_by_family": {
            "CDKT": 1,
            "KQKD": 13,
            "LCTT": 13,
            "TM": 13,
        },
        "unique_overlap_reference_match_counts_by_family": {
            "CDKT": 13,
            "KQKD": 13,
            "LCTT": 13,
            "TM": 13,
        },
    },
    "off_balance_signal": {
        "reference_count": 28,
        "reference_with_signal_hit_count": 20,
    },
    "page_family_confusion": _FINALIZED_CONFUSION,
}
_FINALIZED_FAILURE_ROLLUPS = {
    "zero_candidate_document_count": 14,
    "zero_candidate_with_terminal_barrier_count": 7,
    "zero_candidate_without_terminal_barrier_count": 7,
    "multi_alternative_document_count": 10,
    "top1_cdkt_overlap_not_exact_document_count": 12,
    "tm_reference_page_hypothesized_other_count": 347,
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _error(message: str) -> Wave1RoleBVsRoleALevel1AgreementV1Error:
    return Wave1RoleBVsRoleALevel1AgreementV1Error(message)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _required_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or not fields <= set(value):
        raise _error(f"{label} required fields drifted")
    return value


def _string(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise _error(f"{label} must be a nonempty string")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise _error(f"{label} is not a SHA-256 digest")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value < 1:
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


def _read_pinned_json(
    project_root: Path,
    *,
    relative_path: Path,
    expected_sha256: str,
    expected_size: int,
    label: str,
) -> dict[str, Any]:
    path = project_root / relative_path
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size != expected_size:
            raise _error(f"{label} topology/size differs from its exact pin")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    token = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        stat.S_IFMT(item.st_mode),
        item.st_nlink,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    payload = b"".join(chunks)
    if token(before) != token(after) or len(payload) != expected_size:
        raise _error(f"{label} changed while it was read")
    if sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"{label} bytes differ from their exact raw SHA-256 pin")
    try:
        value = decode_canonical_json_bytes_v1(payload)
    except ValueError as exc:
        raise _error(f"{label} is not canonical JSON") from exc
    if type(value) is not dict or canonical_json_bytes_v1(value) != payload:
        raise _error(f"{label} canonical JSON shape drifted")
    return value


def _load_pinned_inputs(
    project_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    project_root = project_root.resolve()
    role_b = _read_pinned_json(
        project_root,
        relative_path=_ROLE_B_RELATIVE_PATH,
        expected_sha256=_ROLE_B_SHA256,
        expected_size=_ROLE_B_SIZE_BYTES,
        label="Role-B hypothesis inventory",
    )
    role_a = _read_pinned_json(
        project_root,
        relative_path=_ROLE_A_RELATIVE_PATH,
        expected_sha256=_ROLE_A_SHA256,
        expected_size=_ROLE_A_SIZE_BYTES,
        label="Role-A Level-1 reference",
    )
    source_inventory = _read_pinned_json(
        project_root,
        relative_path=_SOURCE_INVENTORY_RELATIVE_PATH,
        expected_sha256=_SOURCE_INVENTORY_SHA256,
        expected_size=_SOURCE_INVENTORY_SIZE_BYTES,
        label="Role-B compact source inventory",
    )
    if (
        role_b.get("format_version") != _ROLE_B_FORMAT
        or role_b.get("status") != _ROLE_B_STATUS
        or role_b.get("claim_boundary") != _ROLE_B_CLAIM
        or role_b.get("inventory_identity_sha256") != _ROLE_B_LOGICAL_IDENTITY
    ):
        raise _error("Role-B hypothesis artifact identity/status drifted")
    if (
        canonical_json_sha256_v1(
            {key: value for key, value in role_b.items() if key != "inventory_identity_sha256"}
        )
        != role_b["inventory_identity_sha256"]
    ):
        raise _error("Role-B hypothesis logical identity is invalid")
    if (
        role_a.get("format_version") != _ROLE_A_FORMAT
        or role_a.get("status") != _ROLE_A_STATUS
        or role_a.get("claim_boundary") != _ROLE_A_CLAIM
        or role_a.get("authority", {}).get("human_gold") is not False
    ):
        raise _error("Role-A Level-1 artifact identity/status drifted")
    if source_inventory.get("inventory_identity_sha256") != _SOURCE_INVENTORY_IDENTITY:
        raise _error("Role-B compact inventory logical identity drifted")
    try:
        role_b_validated = (
            role_b_inventory_v1.validate_wave1_document_statement_hypotheses_inventory_v1(
                role_b,
                project_root=project_root,
                source_inventory=source_inventory,
            )
        )
    except ValueError as exc:
        raise _error("Role-B hypothesis artifact failed its sealed validator") from exc
    rebuilt_role_a = role_a_level1.build_wave_one_role_a_level_one_boundaries(
        project_root,
        project_root / role_a_level1.POLICY_RELATIVE_PATH,
        verify_source_pdfs=False,
    )
    if not same_typed_json_v1(role_b, role_b_validated) or not same_typed_json_v1(
        role_a, rebuilt_role_a
    ):
        raise _error("sealed Role-A/Role-B artifacts fail deterministic authority replay")
    return role_b, role_a, source_inventory


def _authority_receipt(role_b: Mapping[str, Any], role_a: Mapping[str, Any]) -> dict[str, Any]:
    role_b_authority = _required_dict(
        role_b.get("authority"),
        {"finalized_v3", "source_inventory", "locator_policy"},
        "Role-B upstream authority",
    )
    finalized_v3 = _required_dict(
        role_b_authority["finalized_v3"],
        {
            "aggregate_artifact_sha256",
            "aggregate_size_bytes",
            "aggregate_identity_sha256",
            "control_artifact_sha256",
            "control_size_bytes",
            "control_identity_sha256",
            "sealed_plan_sha256",
        },
        "Role-B finalized V3 authority",
    )
    locator_policy = _required_dict(
        role_b_authority["locator_policy"],
        {"path", "sha256", "size_bytes", "used_policy_sha256"},
        "Role-B locator policy authority",
    )
    source_inventory = _required_dict(
        role_b_authority["source_inventory"],
        {"path", "sha256", "size_bytes", "inventory_identity_sha256"},
        "Role-B compact inventory authority",
    )
    for label, value in (
        ("aggregate artifact", finalized_v3["aggregate_artifact_sha256"]),
        ("aggregate identity", finalized_v3["aggregate_identity_sha256"]),
        ("control artifact", finalized_v3["control_artifact_sha256"]),
        ("control identity", finalized_v3["control_identity_sha256"]),
        ("sealed plan", finalized_v3["sealed_plan_sha256"]),
        ("locator policy", locator_policy["sha256"]),
        ("normalized locator policy", locator_policy["used_policy_sha256"]),
        ("compact inventory", source_inventory["sha256"]),
        ("compact inventory identity", source_inventory["inventory_identity_sha256"]),
    ):
        _sha(value, label)
    role_a_authority = _required_dict(
        role_a.get("authority"),
        {"reference_role", "human_gold", "evidence_authority", "page_basis"},
        "Role-A authority",
    )
    if (
        role_a_authority["reference_role"] != "ROLE_A"
        or role_a_authority["human_gold"] is not False
    ):
        raise _error("Role-A authority boundary drifted")
    return {
        "document_join": {
            "key": "SOURCE_SHA256_ONLY",
            "bank_is_output_provenance_only": True,
            "document_name_is_not_read_or_used": True,
        },
        "role_b_hypothesis_artifact": {
            "path": _ROLE_B_RELATIVE_PATH.as_posix(),
            "sha256": _ROLE_B_SHA256,
            "size_bytes": _ROLE_B_SIZE_BYTES,
            "logical_identity_sha256": _ROLE_B_LOGICAL_IDENTITY,
            "format_version": _ROLE_B_FORMAT,
            "status": _ROLE_B_STATUS,
            "claim_boundary": _ROLE_B_CLAIM,
            "upstream_authority": canonical_clone_v1(role_b_authority),
        },
        "role_a_level_1_artifact": {
            "path": _ROLE_A_RELATIVE_PATH.as_posix(),
            "sha256": _ROLE_A_SHA256,
            "size_bytes": _ROLE_A_SIZE_BYTES,
            "format_version": _ROLE_A_FORMAT,
            "status": _ROLE_A_STATUS,
            "claim_boundary": _ROLE_A_CLAIM,
            "authority": canonical_clone_v1(role_a_authority),
            "selection_receipt_sha256": _sha(
                role_a.get("selection_receipt_sha256"),
                "Role-A selection receipt",
            ),
            "reference_source": canonical_clone_v1(role_a.get("reference_source")),
        },
    }


def _producer_receipt(project_root: Path) -> dict[str, Any]:
    try:
        git = sentinel._git_identity(project_root.resolve(), require_clean=True)  # noqa: SLF001
        ledger = sentinel._implementation_ledger(  # noqa: SLF001
            project_root.resolve(), git["commit"], _IMPLEMENTATION_PATHS
        )
    except (OSError, sentinel.WaveOneRoleBSentinelError) as exc:
        raise _error(f"agreement producer is not a clean commit: {exc}") from exc
    return {"git": canonical_clone_v1(git), "implementation_ledger": canonical_clone_v1(ledger)}


def _validate_producer(value: Any, *, project_root: Path) -> dict[str, Any]:
    producer = _exact_dict(value, _PRODUCER_FIELDS, "producer")
    git = _exact_dict(producer["git"], _GIT_FIELDS, "producer Git")
    if (
        type(git["commit"]) is not str
        or re.fullmatch(r"[0-9a-f]{40}", git["commit"]) is None
        or git["dirty"] is not False
    ):
        raise _error("producer Git identity drifted")
    ledger = _exact_dict(producer["implementation_ledger"], _LEDGER_FIELDS, "implementation ledger")
    records = ledger["records"]
    paths = [path.as_posix() for path in sorted(set(_IMPLEMENTATION_PATHS))]
    if type(records) is not list or len(records) != len(paths):
        raise _error("implementation ledger denominator drifted")
    for path, raw in zip(paths, records, strict=True):
        record = _exact_dict(raw, _LEDGER_RECORD_FIELDS, "implementation record")
        if (
            record["phase"] != "READ"
            or record["kind"] != "IMPLEMENTATION"
            or record["path"] != path
        ):
            raise _error("implementation ledger role/path drifted")
        _sha(record["sha256"], "implementation digest")
        _positive(record["size_bytes"], "implementation size")
    if _sha(ledger["sha256"], "implementation ledger identity") != canonical_json_sha256_v1(
        records
    ):
        raise _error("implementation ledger identity drifted")
    try:
        replay = sentinel._implementation_ledger(  # noqa: SLF001
            project_root.resolve(), git["commit"], _IMPLEMENTATION_PATHS
        )
    except (OSError, sentinel.WaveOneRoleBSentinelError) as exc:
        raise _error("producer ledger cannot be replayed from its stored commit") from exc
    if not same_typed_json_v1(ledger, replay):
        raise _error("producer ledger differs from committed implementation bytes")
    return producer


def _reference_page_axis(
    document: Mapping[str, Any], page_count: int
) -> tuple[dict[int, str], list[dict[str, Any]]]:
    segments_raw = document.get("page_segments")
    if type(segments_raw) is not list or not segments_raw:
        raise _error("Role-A page partition is empty")
    page_axis: dict[int, str] = {}
    segments: list[dict[str, Any]] = []
    for index, raw in enumerate(segments_raw, start=1):
        segment = _required_dict(
            raw,
            {"kind", "start_page", "end_page", "copy_id", "embedded_off_balance_pages"},
            f"Role-A page segment {index}",
        )
        kind = _string(segment["kind"], "Role-A page segment kind")
        start = _positive(segment["start_page"], "Role-A page segment start")
        end = _positive(segment["end_page"], "Role-A page segment end")
        if end < start:
            raise _error("Role-A page segment range is inverted")
        receipt = {
            "kind": kind,
            "start_page": start,
            "end_page": end,
            "copy_id": _string(segment["copy_id"], "Role-A page segment copy ID"),
            "embedded_off_balance_pages": canonical_clone_v1(segment["embedded_off_balance_pages"]),
        }
        segments.append(receipt)
        family = _PRIMARY_SEGMENT_FAMILY.get(kind, "OTHER")
        for page in range(start, end + 1):
            if page in page_axis or page > page_count:
                raise _error("Role-A primary page partition overlaps or exceeds its document")
            page_axis[page] = family
    if list(page_axis) != list(range(1, page_count + 1)):
        raise _error("Role-A primary page partition is not exact and contiguous")
    return page_axis, segments


def _reference_blocks(document: Mapping[str, Any], page_count: int) -> list[dict[str, Any]]:
    blocks_raw = document.get("statement_blocks")
    if type(blocks_raw) is not list:
        raise _error("Role-A statement blocks must be a list")
    blocks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in blocks_raw:
        block = _required_dict(
            raw,
            {
                "block_id",
                "block_type",
                "copy_id",
                "start_page",
                "end_page",
                "placement",
                "parent_block_id",
                "visible_unit_override",
            },
            "Role-A statement block",
        )
        block_id = _string(block["block_id"], "Role-A statement block ID")
        if block_id in seen:
            raise _error("Role-A statement block ID is duplicated")
        seen.add(block_id)
        block_type = _string(block["block_type"], "Role-A statement block type")
        if block_type not in {*_REFERENCE_BLOCK_TYPE.values(), "OFF_BALANCE"}:
            raise _error("Role-A statement block type is outside the Level-1 comparison")
        start = _positive(block["start_page"], "Role-A statement block start")
        end = _positive(block["end_page"], "Role-A statement block end")
        if end < start or end > page_count:
            raise _error("Role-A statement block range is invalid")
        parent = block["parent_block_id"]
        if parent is not None and type(parent) is not str:
            raise _error("Role-A parent block ID is invalid")
        blocks.append(
            {
                "block_id": block_id,
                "block_type": block_type,
                "copy_id": _string(block["copy_id"], "Role-A block copy ID"),
                "start_page": start,
                "end_page": end,
                "placement": _string(block["placement"], "Role-A block placement"),
                "parent_block_id": parent,
                "visible_unit_override": canonical_clone_v1(block["visible_unit_override"]),
            }
        )
    return blocks


def _role_b_pages(
    document: Mapping[str, Any],
    page_count: int,
    *,
    source_sha256: str,
    source_pages_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    hypotheses_raw = document.get("page_hypotheses")
    bindings_raw = document.get("page_projection_bindings")
    dispositions_raw = document.get("page_dispositions")
    if not all(
        type(value) is list and len(value) == page_count
        for value in (hypotheses_raw, bindings_raw, dispositions_raw)
    ):
        raise _error("Role-B page hypotheses/bindings/dispositions denominator drifted")
    pages: list[dict[str, Any]] = []
    hypothesis_ids: set[str] = set()
    for ordinal, (raw_hypothesis, raw_binding, raw_disposition) in enumerate(
        zip(hypotheses_raw, bindings_raw, dispositions_raw, strict=True), start=1
    ):
        hypothesis = _required_dict(
            raw_hypothesis,
            {
                "input_ordinal",
                "page_hypothesis_id",
                "source_local_page_id",
                "source_projection_sha256",
                "upstream_status",
                "terminal",
                "family_hypothesis",
                "diagnostic_score",
                "evidence_codes",
                "continuation_marker_hypothesis",
            },
            "Role-B page hypothesis",
        )
        binding = _required_dict(
            raw_binding,
            {
                "input_ordinal",
                "source_local_page_id",
                "source_projection_sha256",
                "route",
                "upstream_status",
                "terminal",
            },
            "Role-B page projection binding",
        )
        disposition = _required_dict(
            raw_disposition,
            {
                "input_ordinal",
                "page_hypothesis_id",
                "source_local_page_id",
                "primary_disposition",
                "block_hypothesis_ids",
            },
            "Role-B page disposition",
        )
        page_hypothesis_id = _string(hypothesis["page_hypothesis_id"], "Role-B page hypothesis ID")
        if page_hypothesis_id in hypothesis_ids:
            raise _error("Role-B page hypothesis ID is duplicated")
        hypothesis_ids.add(page_hypothesis_id)
        source_local_page_id = _string(
            hypothesis["source_local_page_id"], "Role-B source-local page ID"
        )
        projection_sha = _sha(hypothesis["source_projection_sha256"], "Role-B projection SHA-256")
        if source_local_page_id not in source_pages_by_id:
            raise _error("Role-B page is absent from its pinned compact inventory")
        source_page = source_pages_by_id[source_local_page_id]
        physical_page = _positive(source_page["physical_page"], "authenticated physical page")
        terminal = hypothesis["terminal"]
        family = _string(hypothesis["family_hypothesis"], "Role-B family hypothesis")
        if type(terminal) is not bool:
            raise _error("Role-B terminal flag is not Boolean")
        if terminal != (family == "UPSTREAM_TERMINAL"):
            raise _error("Role-B terminal/family boundary drifted")
        if not terminal and family not in _ROLE_B_COMPLETE_FAMILIES:
            raise _error("Role-B complete-page family vocabulary drifted")
        evidence_codes = hypothesis["evidence_codes"]
        if type(evidence_codes) is not list or any(
            type(code) is not str for code in evidence_codes
        ):
            raise _error("Role-B page evidence codes are invalid")
        if evidence_codes != sorted(set(evidence_codes)):
            raise _error("Role-B page evidence codes are not closed and sorted")
        if (
            hypothesis["input_ordinal"] != ordinal
            or binding["input_ordinal"] != ordinal
            or disposition["input_ordinal"] != ordinal
            or binding["source_local_page_id"] != source_local_page_id
            or disposition["source_local_page_id"] != source_local_page_id
            or disposition["page_hypothesis_id"] != page_hypothesis_id
            or binding["source_projection_sha256"] != projection_sha
            or binding["upstream_status"] != hypothesis["upstream_status"]
            or binding["terminal"] is not terminal
            or source_page["document_id"] != f"sha256:{source_sha256}"
            or source_page["projection_sha256"] != projection_sha
            or source_page["route"] != binding["route"]
            or source_page["status"] != hypothesis["upstream_status"]
            or source_page["terminal"] is not terminal
        ):
            raise _error("Role-B page binding/disposition cross-reference drifted")
        block_ids = disposition["block_hypothesis_ids"]
        if type(block_ids) is not list or any(type(value) is not str for value in block_ids):
            raise _error("Role-B page disposition block references are invalid")
        if type(hypothesis["continuation_marker_hypothesis"]) is not bool:
            raise _error("Role-B continuation-marker hypothesis is not Boolean")
        pages.append(
            {
                "input_ordinal": ordinal,
                "physical_page": physical_page,
                "page_hypothesis_id": page_hypothesis_id,
                "source_local_page_id": source_local_page_id,
                "source_projection_sha256": projection_sha,
                "route": _string(binding["route"], "Role-B page route"),
                "upstream_status": _string(hypothesis["upstream_status"], "Role-B upstream status"),
                "terminal": terminal,
                "family_hypothesis": family,
                "diagnostic_score": _finite(
                    hypothesis["diagnostic_score"], "Role-B page diagnostic score"
                ),
                "evidence_codes": list(evidence_codes),
                "continuation_marker_hypothesis": hypothesis["continuation_marker_hypothesis"],
                "primary_disposition": _string(
                    disposition["primary_disposition"], "Role-B page disposition"
                ),
                "block_hypothesis_ids": list(block_ids),
            }
        )
    return pages


def _range_comparisons(
    *,
    family: str,
    start: int,
    end: int,
    references: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], bool, bool]:
    comparisons: list[dict[str, Any]] = []
    for reference in references:
        ref_start = reference["start_page"]
        ref_end = reference["end_page"]
        intersection = max(0, min(end, ref_end) - max(start, ref_start) + 1)
        union = (end - start + 1) + (ref_end - ref_start + 1) - intersection
        exact = start == ref_start and end == ref_end
        overlap = intersection > 0
        comparisons.append(
            {
                "role_a_block_id": reference["block_id"],
                "exact_range": exact,
                "overlap": overlap,
                "intersection_page_count": intersection,
                "union_page_count": union,
                "intersection_over_union": round(intersection / union, 12),
            }
        )
    return (
        comparisons,
        any(item["exact_range"] for item in comparisons),
        any(item["overlap"] for item in comparisons),
    )


def _derive_candidate(
    raw: Any,
    *,
    expected_rank: int,
    pages_by_id: Mapping[str, Mapping[str, Any]],
    references_by_family: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    candidate = _required_dict(
        raw,
        {
            "block_hypothesis_id",
            "rank",
            "diagnostic_score",
            "diagnostic_score_components",
            "start_input_ordinal",
            "end_input_ordinal",
            "family_sequence_hypothesis",
            "family_evidence_codes",
            "member_page_hypothesis_ids",
            "tm_boundary_hypothesis_id",
        },
        "Role-B block hypothesis",
    )
    if candidate["rank"] != expected_rank:
        raise _error("Role-B block hypothesis ranks are not exact and contiguous")
    start = _positive(candidate["start_input_ordinal"], "Role-B candidate start")
    end = _positive(candidate["end_input_ordinal"], "Role-B candidate end")
    sequence = candidate["family_sequence_hypothesis"]
    family_evidence_codes = candidate["family_evidence_codes"]
    member_ids = candidate["member_page_hypothesis_ids"]
    if (
        type(sequence) is not list
        or type(member_ids) is not list
        or len(sequence) != len(member_ids)
        or type(family_evidence_codes) is not list
        or len(family_evidence_codes) != len(sequence)
        or len(sequence) != end - start + 1
    ):
        raise _error("Role-B candidate member sequence denominator drifted")
    member_pages: list[Mapping[str, Any]] = []
    for offset, (family, page_id) in enumerate(zip(sequence, member_ids, strict=True)):
        if family not in _RANGE_FAMILIES or type(page_id) is not str or page_id not in pages_by_id:
            raise _error("Role-B candidate family/member reference drifted")
        page = pages_by_id[page_id]
        evidence = family_evidence_codes[offset]
        if (
            page["input_ordinal"] != start + offset
            or page["family_hypothesis"] != family
            or type(evidence) is not list
            or evidence != page["evidence_codes"]
        ):
            raise _error("Role-B candidate member order/family drifted")
        member_pages.append(page)
    runs: list[tuple[str, int, int]] = []
    index = 0
    while index < len(sequence):
        end_index = index
        while end_index + 1 < len(sequence) and sequence[end_index + 1] == sequence[index]:
            end_index += 1
        run_pages = [
            member_pages[position]["physical_page"] for position in range(index, end_index + 1)
        ]
        if run_pages != list(range(run_pages[0], run_pages[-1] + 1)):
            raise _error("Role-B candidate source pages are not physically contiguous")
        runs.append((sequence[index], run_pages[0], run_pages[-1]))
        index = end_index + 1
    if [family for family, _start, _end in runs] != list(_RANGE_FAMILIES):
        raise _error("Role-B candidate is not one ordered CDKT/KQKD/LCTT hypothesis")
    tm_id = _string(candidate["tm_boundary_hypothesis_id"], "Role-B TM boundary hypothesis ID")
    if tm_id not in pages_by_id:
        raise _error("Role-B TM boundary hypothesis is foreign")
    tm_page = pages_by_id[tm_id]
    if (
        tm_page["family_hypothesis"] != "TM"
        or tm_page["input_ordinal"] != end + 1
        or tm_page["physical_page"] != member_pages[-1]["physical_page"] + 1
    ):
        raise _error("Role-B TM boundary is not the exact next TM hypothesis")
    derived: list[dict[str, Any]] = []
    for family, run_start, run_end in runs:
        comparisons, exact, overlap = _range_comparisons(
            family=family,
            start=run_start,
            end=run_end,
            references=references_by_family[family],
        )
        derived.append(
            {
                "family": family,
                "comparison_kind": "EXACT_RANGE_OVERLAP_AND_IOU",
                "start_page": run_start,
                "end_page": run_end,
                "reference_comparisons": comparisons,
                "candidate_exact_match": exact,
                "candidate_overlap_match": overlap,
            }
        )
    tm_comparisons = [
        {
            "role_a_block_id": reference["block_id"],
            "exact_start": tm_page["physical_page"] == reference["start_page"],
        }
        for reference in references_by_family["TM"]
    ]
    tm_exact = any(item["exact_start"] for item in tm_comparisons)
    derived.append(
        {
            "family": "TM",
            "comparison_kind": "START_PAGE_ONLY_NO_END_OR_COVERAGE_CLAIM",
            "start_page": tm_page["physical_page"],
            "reference_comparisons": tm_comparisons,
            "candidate_exact_match": tm_exact,
            "candidate_overlap_match": tm_exact,
        }
    )
    return {
        "role_b_block_hypothesis_id": _string(
            candidate["block_hypothesis_id"], "Role-B block hypothesis ID"
        ),
        "rank": expected_rank,
        "diagnostic_score": _finite(candidate["diagnostic_score"], "Role-B block diagnostic score"),
        "diagnostic_score_components": canonical_clone_v1(candidate["diagnostic_score_components"]),
        "start_input_ordinal": start,
        "end_input_ordinal": end,
        "family_sequence_hypothesis": list(sequence),
        "family_evidence_codes": canonical_clone_v1(family_evidence_codes),
        "member_page_hypothesis_ids": list(member_ids),
        "tm_boundary_hypothesis_id": tm_id,
        "derived_family_hypotheses": derived,
    }


def _document_comparison(
    role_b_document: Any,
    role_a_document: Any,
    *,
    source_pages_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    role_b = _required_dict(
        role_b_document,
        {
            "source_sha256",
            "status",
            "document_hypotheses_identity",
            "page_hypotheses",
            "page_projection_bindings",
            "page_dispositions",
            "block_hypotheses",
        },
        "Role-B document",
    )
    role_a = _required_dict(
        role_a_document,
        {
            "bank",
            "source",
            "statement_blocks",
            "page_segments",
            "reference_status",
            "claim_boundary",
            "page_basis",
        },
        "Role-A document",
    )
    source_sha = _sha(role_b["source_sha256"], "Role-B source SHA-256")
    source = _required_dict(
        role_a["source"], {"sha256", "document_id", "page_count"}, "Role-A source"
    )
    if source["sha256"] != source_sha or source["document_id"] != f"sha256:{source_sha}":
        raise _error("Role-A/Role-B source-SHA join authority drifted")
    page_count = _positive(source["page_count"], "document page count")
    page_axis, segment_receipts = _reference_page_axis(role_a, page_count)
    reference_blocks = _reference_blocks(role_a, page_count)
    pages = _role_b_pages(
        role_b,
        page_count,
        source_sha256=source_sha,
        source_pages_by_id=source_pages_by_id,
    )
    physical_pages = [page["physical_page"] for page in pages]
    if physical_pages != list(range(1, page_count + 1)):
        raise _error("Role-B authenticated physical-page axis is not exact and contiguous")
    pages_by_id = {page["page_hypothesis_id"]: page for page in pages}
    references_by_family = {
        family: [
            block
            for block in reference_blocks
            if block["block_type"] == _REFERENCE_BLOCK_TYPE[family]
        ]
        for family in _MAIN_FAMILIES
    }
    if any(not references_by_family[family] for family in _MAIN_FAMILIES):
        raise _error("Role-A document lacks a required main Level-1 family reference")

    page_comparisons: list[dict[str, Any]] = []
    for page in pages:
        reference_family = page_axis[page["physical_page"]]
        if page["terminal"]:
            comparison_status = "UPSTREAM_TERMINAL_SEPARATE"
        elif page["family_hypothesis"] == reference_family:
            comparison_status = "EXACT_PRIMARY_FAMILY_AGREEMENT"
        else:
            comparison_status = "PRIMARY_FAMILY_DISAGREEMENT"
        page_comparisons.append(
            {
                **page,
                "role_a_primary_family": reference_family,
                "comparison_status": comparison_status,
                "off_balance_signal_hypothesis": (
                    "OFF_BALANCE_SIGNAL_HYPOTHESIS" in page["evidence_codes"]
                ),
            }
        )

    candidates_raw = role_b["block_hypotheses"]
    if type(candidates_raw) is not list:
        raise _error("Role-B block hypotheses must be a list")
    candidate_receipts = [
        _derive_candidate(
            raw,
            expected_rank=rank,
            pages_by_id=pages_by_id,
            references_by_family=references_by_family,
        )
        for rank, raw in enumerate(candidates_raw, start=1)
    ]
    expected_status = (
        "CANDIDATES_EMITTED" if candidate_receipts else "UNRESOLVED_NO_COMPLETE_ORDERED_HYPOTHESIS"
    )
    if role_b["status"] != expected_status:
        raise _error("Role-B document status/candidate denominator drifted")
    all_candidate_ids = {
        candidate["role_b_block_hypothesis_id"] for candidate in candidate_receipts
    }
    if len(all_candidate_ids) != len(candidate_receipts):
        raise _error("Role-B candidate ID is duplicated")
    for page in pages:
        if not set(page["block_hypothesis_ids"]) <= all_candidate_ids:
            raise _error("Role-B page disposition cites a foreign candidate")

    off_balance: list[dict[str, Any]] = []
    page_by_physical = {page["physical_page"]: page for page in page_comparisons}
    for reference in reference_blocks:
        if reference["block_type"] != "OFF_BALANCE":
            continue
        signal_pages = [
            ordinal
            for ordinal in range(reference["start_page"], reference["end_page"] + 1)
            if page_by_physical[ordinal]["off_balance_signal_hypothesis"]
        ]
        off_balance.append(
            {
                "role_a_block_id": reference["block_id"],
                "start_page": reference["start_page"],
                "end_page": reference["end_page"],
                "placement": reference["placement"],
                "signal_page_hits": signal_pages,
                "has_off_balance_signal_hypothesis": bool(signal_pages),
                "diagnostic_only_no_block_inference": True,
            }
        )

    failures: list[str] = []
    terminal_count = sum(page["terminal"] for page in page_comparisons)
    if not candidate_receipts:
        failures.append(
            "ZERO_CANDIDATE_WITH_TERMINAL_BARRIER"
            if terminal_count
            else "ZERO_CANDIDATE_WITHOUT_TERMINAL_BARRIER"
        )
    if len(candidate_receipts) > 1:
        failures.append("MULTI_ALTERNATIVE_HYPOTHESES")
    if candidate_receipts:
        cdkt = candidate_receipts[0]["derived_family_hypotheses"][0]
        if cdkt["candidate_overlap_match"] and not cdkt["candidate_exact_match"]:
            failures.append("TOP1_CDKT_OVERLAP_NOT_EXACT")
    failures.sort(key=_FAILURE_CLASSES.index)
    complete_count = page_count - terminal_count
    agreement_count = sum(
        page["comparison_status"] == "EXACT_PRIMARY_FAMILY_AGREEMENT" for page in page_comparisons
    )
    return {
        "bank": _string(role_a["bank"], "Role-A bank provenance"),
        "source_sha256": source_sha,
        "page_count": page_count,
        "role_a_reference_receipt": {
            "reference_status": _string(role_a["reference_status"], "Role-A reference status"),
            "claim_boundary": _string(role_a["claim_boundary"], "Role-A claim boundary"),
            "page_basis": _string(role_a["page_basis"], "Role-A page basis"),
            "page_segments": segment_receipts,
            "statement_blocks": reference_blocks,
        },
        "role_b_hypothesis_receipt": {
            "document_hypotheses_identity": _string(
                role_b["document_hypotheses_identity"], "Role-B document identity"
            ),
            "status": _string(role_b["status"], "Role-B document status"),
            "block_hypothesis_count": len(candidate_receipts),
        },
        "page_comparisons": page_comparisons,
        "candidate_comparisons": candidate_receipts,
        "off_balance_signal_comparisons": off_balance,
        "failure_classes": failures,
        "metrics": {
            "complete_page_count": complete_count,
            "terminal_page_count": terminal_count,
            "complete_family_agreement_count": agreement_count,
            "complete_family_disagreement_count": complete_count - agreement_count,
            "role_a_reference_block_count": len(reference_blocks),
            "role_a_main_reference_block_count": sum(
                block["block_type"] != "OFF_BALANCE" for block in reference_blocks
            ),
            "role_b_block_hypothesis_count": len(candidate_receipts),
            "off_balance_reference_count": len(off_balance),
            "off_balance_reference_with_signal_hit_count": sum(
                item["has_off_balance_signal_hypothesis"] for item in off_balance
            ),
        },
    }


def _candidate_rollup(
    documents: Sequence[Mapping[str, Any]],
    *,
    top1_only: bool,
    reference_denominator: int,
) -> dict[str, Any]:
    candidate_count = 0
    exact_candidates = 0
    overlap_candidates = 0
    exact_candidates_by_family: Counter[str] = Counter()
    overlap_candidates_by_family: Counter[str] = Counter()
    unique_exact_references: dict[tuple[str, str], str] = {}
    unique_overlap_references: dict[tuple[str, str], str] = {}
    for document in documents:
        candidates = document["candidate_comparisons"]
        selected = candidates[:1] if top1_only else candidates
        for candidate in selected:
            for hypothesis in candidate["derived_family_hypotheses"]:
                family = hypothesis["family"]
                candidate_count += 1
                if hypothesis["candidate_exact_match"]:
                    exact_candidates += 1
                    exact_candidates_by_family[family] += 1
                if hypothesis["candidate_overlap_match"]:
                    overlap_candidates += 1
                    overlap_candidates_by_family[family] += 1
                for comparison in hypothesis["reference_comparisons"]:
                    key = (document["source_sha256"], comparison["role_a_block_id"])
                    exact = comparison.get("exact_range", comparison.get("exact_start"))
                    overlap = comparison.get("overlap", comparison.get("exact_start"))
                    if exact:
                        unique_exact_references[key] = family
                    if overlap:
                        unique_overlap_references[key] = family
    exact_reference_families = Counter(unique_exact_references.values())
    overlap_reference_families = Counter(unique_overlap_references.values())
    return {
        "candidate_comparison_count": candidate_count,
        "reference_denominator": reference_denominator,
        "exact_candidate_match_count": exact_candidates,
        "overlap_candidate_match_count": overlap_candidates,
        "exact_candidate_precision_against_machine_reference": round(
            exact_candidates / candidate_count, 12
        )
        if candidate_count
        else 0.0,
        "overlap_candidate_precision_against_machine_reference": round(
            overlap_candidates / candidate_count, 12
        )
        if candidate_count
        else 0.0,
        "unique_exact_reference_match_count": len(unique_exact_references),
        "unique_overlap_reference_match_count": len(unique_overlap_references),
        "exact_candidate_match_counts_by_family": {
            family: exact_candidates_by_family[family] for family in _MAIN_FAMILIES
        },
        "overlap_candidate_match_counts_by_family": {
            family: overlap_candidates_by_family[family] for family in _MAIN_FAMILIES
        },
        "unique_exact_reference_match_counts_by_family": {
            family: exact_reference_families[family] for family in _MAIN_FAMILIES
        },
        "unique_overlap_reference_match_counts_by_family": {
            family: overlap_reference_families[family] for family in _MAIN_FAMILIES
        },
    }


def _rollup(documents: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], dict[str, int]]:
    reference_block_counts: Counter[str] = Counter()
    confusion = {
        reference_family: {hypothesis_family: 0 for hypothesis_family in _ROLE_B_COMPLETE_FAMILIES}
        for reference_family in _ROLE_A_PRIMARY_FAMILIES
    }
    failure_counts: Counter[str] = Counter()
    page_count = 0
    complete_count = 0
    terminal_count = 0
    agreement_count = 0
    reference_count = 0
    main_reference_count = 0
    role_b_block_count = 0
    off_balance_count = 0
    off_balance_hit_count = 0
    tm_to_other = 0
    for document in documents:
        page_count += document["page_count"]
        metrics = document["metrics"]
        complete_count += metrics["complete_page_count"]
        terminal_count += metrics["terminal_page_count"]
        agreement_count += metrics["complete_family_agreement_count"]
        reference_count += metrics["role_a_reference_block_count"]
        main_reference_count += metrics["role_a_main_reference_block_count"]
        role_b_block_count += metrics["role_b_block_hypothesis_count"]
        off_balance_count += metrics["off_balance_reference_count"]
        off_balance_hit_count += metrics["off_balance_reference_with_signal_hit_count"]
        reference_block_counts.update(
            block["block_type"]
            for block in document["role_a_reference_receipt"]["statement_blocks"]
        )
        failure_counts.update(document["failure_classes"])
        for page in document["page_comparisons"]:
            if page["terminal"]:
                continue
            reference_family = page["role_a_primary_family"]
            hypothesis_family = page["family_hypothesis"]
            confusion[reference_family][hypothesis_family] += 1
            if reference_family == "TM" and hypothesis_family == "OTHER":
                tm_to_other += 1
    metrics = {
        "document_count": len(documents),
        "page_count": page_count,
        "complete_page_count": complete_count,
        "terminal_page_count": terminal_count,
        "complete_family_agreement_count": agreement_count,
        "complete_family_disagreement_count": complete_count - agreement_count,
        "role_a_reference_block_count": reference_count,
        "role_a_main_reference_block_count": main_reference_count,
        "role_a_reference_block_counts": {
            block_type: reference_block_counts[block_type]
            for block_type in ("CDKT_MAIN", "OFF_BALANCE", "KQKD", "LCTT", "TM")
        },
        "role_b_block_hypothesis_count": role_b_block_count,
        "top1": _candidate_rollup(
            documents, top1_only=True, reference_denominator=main_reference_count
        ),
        "oracle_any": _candidate_rollup(
            documents, top1_only=False, reference_denominator=main_reference_count
        ),
        "off_balance_signal": {
            "reference_count": off_balance_count,
            "reference_with_signal_hit_count": off_balance_hit_count,
        },
        "page_family_confusion": confusion,
    }
    failures = {
        "zero_candidate_document_count": (
            failure_counts["ZERO_CANDIDATE_WITH_TERMINAL_BARRIER"]
            + failure_counts["ZERO_CANDIDATE_WITHOUT_TERMINAL_BARRIER"]
        ),
        "zero_candidate_with_terminal_barrier_count": failure_counts[
            "ZERO_CANDIDATE_WITH_TERMINAL_BARRIER"
        ],
        "zero_candidate_without_terminal_barrier_count": failure_counts[
            "ZERO_CANDIDATE_WITHOUT_TERMINAL_BARRIER"
        ],
        "multi_alternative_document_count": failure_counts["MULTI_ALTERNATIVE_HYPOTHESES"],
        "top1_cdkt_overlap_not_exact_document_count": failure_counts["TOP1_CDKT_OVERLAP_NOT_EXACT"],
        "tm_reference_page_hypothesized_other_count": tm_to_other,
    }
    return metrics, failures


def _compare_inputs(
    role_b_inventory: Any,
    role_a_reference: Any,
    source_inventory: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, int]]:
    role_b = _required_dict(
        role_b_inventory,
        {"format_version", "status", "claim_boundary", "documents"},
        "Role-B hypothesis inventory",
    )
    role_a = _required_dict(
        role_a_reference,
        {"format_version", "status", "claim_boundary", "documents"},
        "Role-A Level-1 reference",
    )
    source = _required_dict(
        source_inventory,
        {"pages"},
        "Role-B compact source inventory",
    )
    if (
        role_b["format_version"] != _ROLE_B_FORMAT
        or role_b["status"] != _ROLE_B_STATUS
        or role_b["claim_boundary"] != _ROLE_B_CLAIM
    ):
        raise _error("Role-B hypothesis input header drifted")
    if (
        role_a["format_version"] != _ROLE_A_FORMAT
        or role_a["status"] != _ROLE_A_STATUS
        or role_a["claim_boundary"] != _ROLE_A_CLAIM
    ):
        raise _error("Role-A Level-1 input header drifted")
    role_b_documents = role_b["documents"]
    role_a_documents = role_a["documents"]
    if (
        type(role_b_documents) is not list
        or not role_b_documents
        or type(role_a_documents) is not list
    ):
        raise _error("agreement document inputs are empty or invalid")
    source_pages = source["pages"]
    if type(source_pages) is not list or not source_pages:
        raise _error("Role-B compact source page inventory is empty")
    source_pages_by_id: dict[str, Mapping[str, Any]] = {}
    for raw_page in source_pages:
        page = _required_dict(
            raw_page,
            {
                "document_id",
                "physical_page",
                "projection_identity",
                "projection_sha256",
                "route",
                "status",
                "terminal",
            },
            "compact source page",
        )
        projection_id = _string(page["projection_identity"], "compact projection identity")
        if projection_id in source_pages_by_id:
            raise _error("compact projection identity is duplicated")
        _sha(page["projection_sha256"], "compact projection SHA-256")
        source_pages_by_id[projection_id] = page
    role_a_by_source: dict[str, Mapping[str, Any]] = {}
    for raw in role_a_documents:
        document = _required_dict(raw, {"source"}, "Role-A document join receipt")
        source = _required_dict(document["source"], {"sha256"}, "Role-A source join receipt")
        source_sha = _sha(source["sha256"], "Role-A source SHA-256")
        if source_sha in role_a_by_source:
            raise _error("Role-A source SHA-256 is duplicated")
        role_a_by_source[source_sha] = raw
    documents: list[dict[str, Any]] = []
    joined: set[str] = set()
    for raw in role_b_documents:
        role_b_document = _required_dict(raw, {"source_sha256"}, "Role-B document join receipt")
        source_sha = _sha(role_b_document["source_sha256"], "Role-B source SHA-256")
        if source_sha in joined or source_sha not in role_a_by_source:
            raise _error("Role-B source SHA-256 is duplicate or absent from Role-A")
        joined.add(source_sha)
        documents.append(
            _document_comparison(
                raw,
                role_a_by_source[source_sha],
                source_pages_by_id=source_pages_by_id,
            )
        )
    if joined != set(role_a_by_source):
        raise _error("Role-A/Role-B source-SHA join is not exhaustive")
    compared_page_ids = {
        page["source_local_page_id"]
        for document in documents
        for page in document["page_comparisons"]
    }
    if compared_page_ids != set(source_pages_by_id):
        raise _error("agreement does not consume the exact compact page denominator")
    metrics, failures = _rollup(documents)
    if metrics["page_count"] != metrics["complete_page_count"] + metrics["terminal_page_count"]:
        raise _error("agreement complete/terminal page denominator drifted")
    if metrics["complete_page_count"] != sum(
        sum(row.values()) for row in metrics["page_family_confusion"].values()
    ):
        raise _error("agreement page confusion denominator drifted")
    if metrics["role_a_reference_block_count"] != (
        metrics["role_a_main_reference_block_count"]
        + metrics["off_balance_signal"]["reference_count"]
    ):
        raise _error("agreement Role-A block denominator drifted")
    return documents, metrics, failures


def _build_from_inputs(
    role_b_inventory: Mapping[str, Any],
    role_a_reference: Mapping[str, Any],
    source_inventory: Mapping[str, Any],
    *,
    authority: Mapping[str, Any],
    producer: Mapping[str, Any],
    enforce_finalized_baseline: bool,
) -> dict[str, Any]:
    documents, metrics, failures = _compare_inputs(
        role_b_inventory, role_a_reference, source_inventory
    )
    if enforce_finalized_baseline and (
        not same_typed_json_v1(metrics, _FINALIZED_METRIC_PROJECTION)
        or not same_typed_json_v1(failures, _FINALIZED_FAILURE_ROLLUPS)
    ):
        raise _error("sealed Wave-1 agreement baseline drifted")
    result = {
        "format_version": WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_FORMAT_VERSION_V1,
        "status": _OUTPUT_STATUS,
        "claim_boundary": WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_CLAIM_BOUNDARY_V1,
        "authority": canonical_clone_v1(authority),
        "documents": documents,
        "corpus_metrics": metrics,
        "failure_class_rollups": failures,
        "producer": canonical_clone_v1(producer),
        "safety": canonical_clone_v1(_SAFETY),
    }
    result["agreement_identity_sha256"] = canonical_json_sha256_v1(result)
    return result


def _validate_from_inputs(
    value: Any,
    *,
    project_root: Path,
    role_b_inventory: Mapping[str, Any],
    role_a_reference: Mapping[str, Any],
    source_inventory: Mapping[str, Any],
    authority: Mapping[str, Any],
    enforce_finalized_baseline: bool,
    validate_producer: bool,
) -> dict[str, Any]:
    agreement = _exact_dict(value, _TOP_LEVEL_FIELDS, "agreement artifact")
    if (
        agreement["format_version"] != WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_FORMAT_VERSION_V1
        or agreement["status"] != _OUTPUT_STATUS
        or agreement["claim_boundary"] != WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_CLAIM_BOUNDARY_V1
        or agreement["safety"] != _SAFETY
        or not same_typed_json_v1(agreement["authority"], authority)
    ):
        raise _error("agreement header/authority/safety drifted")
    if validate_producer:
        _validate_producer(agreement["producer"], project_root=project_root)
    expected_documents, expected_metrics, expected_failures = _compare_inputs(
        role_b_inventory, role_a_reference, source_inventory
    )
    if (
        not same_typed_json_v1(agreement["documents"], expected_documents)
        or not same_typed_json_v1(agreement["corpus_metrics"], expected_metrics)
        or not same_typed_json_v1(agreement["failure_class_rollups"], expected_failures)
    ):
        raise _error("agreement receipts/accounting differ from exact input replay")
    if enforce_finalized_baseline and (
        not same_typed_json_v1(expected_metrics, _FINALIZED_METRIC_PROJECTION)
        or not same_typed_json_v1(expected_failures, _FINALIZED_FAILURE_ROLLUPS)
    ):
        raise _error("sealed Wave-1 agreement baseline drifted")
    identity = _sha(agreement["agreement_identity_sha256"], "agreement identity")
    if identity != canonical_json_sha256_v1(
        {key: agreement[key] for key in agreement if key != "agreement_identity_sha256"}
    ):
        raise _error("agreement logical identity drifted")
    return canonical_clone_v1(agreement)


def build_wave1_role_b_vs_role_a_level1_agreement_v1(project_root: Path) -> dict[str, Any]:
    """Build the sealed, diagnostic-only Role-B/Role-A agreement artifact."""

    project_root = project_root.resolve()
    role_b, role_a, source_inventory = _load_pinned_inputs(project_root)
    authority = _authority_receipt(role_b, role_a)
    producer_before = _producer_receipt(project_root)
    result = _build_from_inputs(
        role_b,
        role_a,
        source_inventory,
        authority=authority,
        producer=producer_before,
        enforce_finalized_baseline=True,
    )
    role_b_after, role_a_after, source_after = _load_pinned_inputs(project_root)
    if (
        not same_typed_json_v1(role_b, role_b_after)
        or not same_typed_json_v1(role_a, role_a_after)
        or not same_typed_json_v1(source_inventory, source_after)
    ):
        raise _error("sealed agreement inputs changed during construction")
    if not same_typed_json_v1(producer_before, _producer_receipt(project_root)):
        raise _error("agreement producer changed during construction")
    return _validate_from_inputs(
        result,
        project_root=project_root,
        role_b_inventory=role_b_after,
        role_a_reference=role_a_after,
        source_inventory=source_after,
        authority=authority,
        enforce_finalized_baseline=True,
        validate_producer=True,
    )


def validate_wave1_role_b_vs_role_a_level1_agreement_v1(
    value: Any, *, project_root: Path
) -> dict[str, Any]:
    """Replay exact sealed inputs and validate every agreement receipt/account."""

    project_root = project_root.resolve()
    role_b, role_a, source_inventory = _load_pinned_inputs(project_root)
    return _validate_from_inputs(
        value,
        project_root=project_root,
        role_b_inventory=role_b,
        role_a_reference=role_a,
        source_inventory=source_inventory,
        authority=_authority_receipt(role_b, role_a),
        enforce_finalized_baseline=True,
        validate_producer=True,
    )


def _open_output_directory(project_root: Path) -> tuple[Path, int]:
    relative_parent = WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_OUTPUT_RELATIVE_PATH_V1.parent
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
            raise _error("agreement output parent is not a directory")
    except Exception:
        os.close(descriptor)
        raise
    return project_root / relative_parent, descriptor


def _require_destination_absent(project_root: Path) -> None:
    _parent, directory_fd = _open_output_directory(project_root)
    try:
        try:
            os.stat(
                WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_OUTPUT_RELATIVE_PATH_V1.name,
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return
        raise _error("agreement destination already exists")
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
            raise _error("published agreement is not regular")
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
        raise _error("published agreement changed during validation")
    return b"".join(chunks), after


def _publish_canonical_exclusive(project_root: Path, payload: bytes) -> Path:
    if not payload.endswith(b"\n") or payload.endswith(b"\n\n"):
        raise _error("agreement publication is not canonical newline JSON")
    try:
        decode_canonical_json_bytes_v1(payload)
    except ValueError as exc:
        raise _error("agreement publication bytes are not canonical JSON") from exc
    parent, directory_fd = _open_output_directory(project_root)
    filename = WAVE1_ROLE_B_VS_ROLE_A_LEVEL1_AGREEMENT_OUTPUT_RELATIVE_PATH_V1.name
    temporary_pattern = re.compile(rf"^\.{re.escape(filename)}\.[0-9a-f]{{32}}\.tmp$")
    temporary_name = f".{filename}.{secrets.token_hex(16)}.tmp"
    descriptor = -1
    owned_identity: tuple[int, int] | None = None
    final_linked = False
    publication_committed = False
    try:
        if any(temporary_pattern.fullmatch(name) for name in os.listdir(directory_fd)):
            raise _error("agreement publication temporary already exists")
        try:
            os.stat(filename, dir_fd=directory_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise _error("agreement destination already exists")
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise _error("owned agreement temporary identity drifted")
        owned_identity = (opened.st_dev, opened.st_ino)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise _error("agreement publication write made no progress")
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
            raise _error("sealed agreement temporary identity drifted")
        try:
            os.link(
                temporary_name,
                filename,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except FileExistsError as exc:
            raise _error("agreement publication lost its exclusive race") from exc
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
            raise _error("linked agreement publication identity drifted")
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
            raise _error("published agreement bytes/topology drifted")
    except OSError as exc:
        raise _error("agreement publication failed") from exc
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
                and (observed_final.st_dev, observed_final.st_ino) == owned_identity
            ):
                os.unlink(filename, dir_fd=directory_fd)
                os.fsync(directory_fd)
        if owned_identity is not None:
            try:
                observed_temporary = os.stat(
                    temporary_name, dir_fd=directory_fd, follow_symlinks=False
                )
            except FileNotFoundError:
                observed_temporary = None
            if (
                observed_temporary is not None
                and (
                    observed_temporary.st_dev,
                    observed_temporary.st_ino,
                )
                == owned_identity
            ):
                os.unlink(temporary_name, dir_fd=directory_fd)
                os.fsync(directory_fd)
        os.close(directory_fd)
    return parent / filename


def publish_wave1_role_b_vs_role_a_level1_agreement_v1(
    project_root: Path,
) -> tuple[Path, str, int, str]:
    """Build and exclusively publish the canonical agreement artifact once."""

    project_root = project_root.resolve()
    _require_destination_absent(project_root)
    agreement = build_wave1_role_b_vs_role_a_level1_agreement_v1(project_root)
    validate_wave1_role_b_vs_role_a_level1_agreement_v1(agreement, project_root=project_root)
    if not same_typed_json_v1(_producer_receipt(project_root), agreement["producer"]):
        raise _error("agreement producer changed before publication")
    payload = canonical_json_bytes_v1(agreement)
    path = _publish_canonical_exclusive(project_root, payload)
    return (
        path,
        sha256(payload).hexdigest(),
        len(payload),
        agreement["agreement_identity_sha256"],
    )
