#!/usr/bin/env python3
"""Evaluate ordered row/value-lane assignment over the sealed E-0046 capture.

E-0047 is a bounded mechanism test, not a replacement for E-0046.  It reads
the exact hash-sealed ephemeral E-0046 payload, applies one text-blind geometry
primitive only to ordinary trials whose existing observation contains the
row/value-axis blocker, and deterministically rebuilds the observation, graph,
and schema-candidate frontier.  Independent numeric and mapping verification
remain NOT_EVALUATED for every trial.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

import build_loan_maturity_8bank_v3_provisional_sweep as e0046
import ordered_row_value_lane_assignment_v1 as lane_v1

from bctc_ai.mapping import semantic_local_accounting_schema_candidate_v1 as schema_v1
from bctc_ai.source_structure import semantic_local_accounting_graph_v2 as graph_v2
from bctc_ai.source_structure import semantic_local_accounting_observation_v2 as observation_v2
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    local_accounting_family_spec_sha256_v1,
    parse_local_accounting_period_v1,
    parse_local_accounting_unit_v1,
)
from bctc_ai.source_structure.vietnamese_semantic_surface_v1 import (
    compile_vietnamese_family_alias_index_v1,
    propose_vietnamese_semantic_surface_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "E0047OrderedLaneEvaluationError",
    "build_e0047_ordered_row_value_lane_evaluation",
    "validate_e0047_ordered_row_value_lane_evaluation",
]


FORMAT_VERSION = "E0047_ORDERED_ROW_VALUE_LANE_MECHANISM_EVALUATION_V1"
EXPERIMENT_ID = "E-0047"
STATE = "MECHANISM_EVALUATED_NUMERIC_AND_MAPPING_NOT_EVALUATED"
CLAIM_BOUNDARY = (
    "EXACT_HASH_SEALED_E0046_ROW_VALUE_LANE_GEOMETRY_MECHANISM_TEST_ONLY_"
    "NO_SOURCE_SEMANTIC_NUMERIC_ACCOUNTING_MAPPING_CANONICALIZATION_EXPORT_"
    "OR_VERIFIED_BY_CODEX_AUTHORITY"
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
E0046_SEAL_PATH = Path(
    "docs/experiments/"
    "E-0046-loan-maturity-8bank-vietocr-v3-provisional-private-core-sweep-seal.json"
)
E0046_CAPTURE_PATH = Path("/tmp/e0046.json")
_ROW_VALUE_BLOCKER = "ROW_VALUE_AXIS_ASSIGNMENT_NOT_RESOLVED"
_ORDERED_ASSIGNMENT_BLOCKER = "ORDERED_ROW_VALUE_LANE_ASSIGNMENT_NOT_RESOLVED"
_UNTYPED_COMPANION_BLOCKER = "UNTYPED_NUMERIC_COMPANION_LANES_NOT_RESOLVED"
_ORDINARY_MODE = e0046._ORDINARY_MODE
_FAMILY_SPECS = (
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    LOAN_MATURITY_BUCKETS_SPEC_V1,
)
_FAMILY_SPEC_SHA256 = local_accounting_family_spec_sha256_v1(LOAN_MATURITY_BUCKETS_SPEC_V1)
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_DECIMAL_NUMERIC_RE = re.compile(r"[0-9]+[.,][0-9]{1,2}")
_SAFETY = {
    "accounting_acceptance_authority": False,
    "bank_identity_used_for_mechanism_routing": False,
    "canonicalization_authority": False,
    "e0046_mutated_or_superseded": False,
    "extra_numeric_companion_lanes_silently_discarded": False,
    "independent_mapping_verification_performed": False,
    "independent_numeric_verification_performed": False,
    "mapping_authority": False,
    "persisted_result_self_authenticating": False,
    "private_core_mechanism_evaluation": True,
    "schema_candidates_are_mappings": False,
    "lane_assignment_uses_numeric_text_or_values": False,
    "ppocr_numeric_syntax_used_to_select_geometry_frontier": True,
    "verified_by_codex_claimed": False,
}
_RESULT_FIELDS = {
    "bank_order",
    "claim_boundary",
    "experiment_id",
    "family_id",
    "format_version",
    "input_authority",
    "metrics",
    "result_id",
    "safety",
    "state",
    "trials",
}
_TRIAL_FIELDS = {
    "assignment",
    "bank_provenance",
    "binding_mode",
    "independent_mapping_status",
    "independent_numeric_status",
    "mechanism_status",
    "observation",
    "page_ordinal",
    "prior_observation",
    "schema_candidate",
    "semantic_graph",
    "trial_id",
}
_METRIC_FIELDS = {
    "accepted_structure_count",
    "assignment_resolved_count",
    "assignment_unresolved_count",
    "bank_count",
    "independent_mapping_evaluated_count",
    "independent_numeric_evaluated_count",
    "mechanism_target_count",
    "schema_candidate_ready_count",
    "untyped_companion_blocked_count",
    "verified_mapping_count",
}
_REF_FIELDS = {"path", "sha256", "size_bytes"}
_INPUT_AUTHORITY_FIELDS = {"e0046_capture", "e0046_seal", "implementation_refs"}
_CAPTURE_REF_FIELDS = {"path", "sha256", "size_bytes", "sweep_id"}
_PROJECTION_FIELDS = {"payload_sha256", "status", "unresolved_reasons"}
_SCHEMA_PROJECTION_FIELDS = {
    "candidate_report_norm_ids",
    "source_only_roles",
    "structural_context_candidate_report_norm_ids",
    "unassessed_report_norm_ids",
    "value_row_candidate_report_norm_ids",
}
_IMPLEMENTATION_PATHS = (
    "scripts/experiments/evaluate_e0047_ordered_row_value_lane_assignment.py",
    "scripts/experiments/ordered_row_value_lane_assignment_v1.py",
    "src/bctc_ai/source_structure/semantic_local_accounting_observation_v2.py",
    "src/bctc_ai/source_structure/semantic_local_accounting_graph_v2.py",
    "src/bctc_ai/mapping/semantic_local_accounting_schema_candidate_v1.py",
)


class E0047OrderedLaneEvaluationError(RuntimeError):
    """The bounded E-0047 mechanism result or its exact input drifted."""


def _error(message: str) -> E0047OrderedLaneEvaluationError:
    return E0047OrderedLaneEvaluationError(message)


def _strict_json_bytes(raw: bytes, label: str) -> Any:
    if type(raw) is not bytes:
        raise _error(f"{label} bytes are not exact")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _error(f"{label} is not UTF-8 JSON") from exc

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise _error(f"{label} repeats JSON key {key!r}")
            result[key] = value
        return result

    def bad_constant(value: str) -> None:
        raise _error(f"{label} contains non-finite JSON constant {value}")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=bad_constant)
    except (json.JSONDecodeError, TypeError) as exc:
        raise _error(f"{label} is not strict JSON") from exc


def _stable_regular_bytes(path: Path, label: str) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise _error(f"{label} cannot be opened nofollow") from exc
    try:
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
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise _error(f"{label} changed while being read")
        raw = b"".join(chunks)
        if len(raw) != before.st_size:
            raise _error(f"{label} size changed while being read")
        return raw
    finally:
        os.close(descriptor)


def _root(value: Any) -> Path:
    if not isinstance(value, Path):
        raise _error("E-0047 project root must be one pathlib Path")
    root = value.resolve()
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        capture_output=True,
        check=False,
    )
    try:
        top = Path(completed.stdout.decode("utf-8").strip()).resolve()
    except UnicodeDecodeError as exc:
        raise _error("E-0047 Git root is not UTF-8") from exc
    if completed.returncode != 0 or top != root:
        raise _error("E-0047 project root is not the exact Git toplevel")
    return root


def _file_ref(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    raw = _stable_regular_bytes(path, relative)
    return {
        "path": relative,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


def _is_numeric_observation_text(value: Any) -> bool:
    if type(value) is not str:
        return False
    text = value.strip().replace("\u00a0", "").replace("\u202f", "").replace(" ", "")
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    if text.startswith(("+", "-")):
        text = text[1:]
    if text.endswith("%"):
        text = text[:-1]
    return (
        observation_v2._parse_financial_integer(value) is not None
        or _DECIMAL_NUMERIC_RE.fullmatch(text) is not None
    )


def _input_authority(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    seal_raw = _stable_regular_bytes(root / E0046_SEAL_PATH, "E-0046 seal")
    seal = _strict_json_bytes(seal_raw, "E-0046 seal")
    if (
        type(seal) is not dict
        or seal.get("format_version")
        != "E0046_LOAN_MATURITY_8BANK_V3_PROVISIONAL_PRIVATE_CORE_SWEEP_SEAL_V1"
        or seal.get("experiment_id") != "E-0046"
        or type(seal.get("artifact_identity")) is not dict
    ):
        raise _error("E-0046 seal identity drifted")
    identity = seal["artifact_identity"]
    expected_identity_fields = {
        "canonical_encoding",
        "ephemeral_capture_path",
        "payload_sha256",
        "payload_size_bytes",
        "payload_tracked_in_git",
        "seal_only_is_tracked",
        "sweep_id",
    }
    if (
        set(identity) != expected_identity_fields
        or identity["ephemeral_capture_path"] != str(E0046_CAPTURE_PATH)
        or type(identity["payload_sha256"]) is not str
        or _SHA_RE.fullmatch(identity["payload_sha256"]) is None
        or type(identity["payload_size_bytes"]) is not int
        or identity["payload_size_bytes"] <= 0
        or identity["payload_tracked_in_git"] is not False
        or identity["seal_only_is_tracked"] is not True
    ):
        raise _error("E-0046 sealed payload identity drifted")
    capture_raw = _stable_regular_bytes(E0046_CAPTURE_PATH, "E-0046 capture")
    if (
        len(capture_raw) != identity["payload_size_bytes"]
        or hashlib.sha256(capture_raw).hexdigest() != identity["payload_sha256"]
    ):
        raise _error("E-0046 capture differs from its tracked seal")
    payload = _strict_json_bytes(capture_raw, "E-0046 capture")
    if (
        capture_raw != canonical_json_bytes_v1(payload) + b"\n"
        or type(payload) is not dict
        or payload.get("sweep_id") != identity["sweep_id"]
    ):
        raise _error("E-0046 capture is not its canonical sealed payload")
    e0046._validate_sweep_shape(payload)
    authority = {
        "e0046_capture": {
            "path": str(E0046_CAPTURE_PATH),
            "sha256": identity["payload_sha256"],
            "size_bytes": identity["payload_size_bytes"],
            "sweep_id": identity["sweep_id"],
        },
        "e0046_seal": {
            "path": E0046_SEAL_PATH.as_posix(),
            "sha256": hashlib.sha256(seal_raw).hexdigest(),
            "size_bytes": len(seal_raw),
        },
        "implementation_refs": [_file_ref(root, path) for path in _IMPLEMENTATION_PATHS],
    }
    return payload, authority


def _candidate_payload_with_ordered_lanes(
    source: Mapping[str, Any],
    binding: Mapping[str, Any],
    alias_index: Any,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Rebuild observation-v2 with only its row/value selector replaced."""

    spec = LOAN_MATURITY_BUCKETS_SPEC_V1
    samples = binding["samples"]
    lines = source.get("page_result", {}).get("lines")
    if type(samples) is not list or type(lines) is not list or len(samples) != len(lines):
        raise _error("E-0047 page binding and PP-OCR LINE axes are not coextensive")
    for index, (sample, line) in enumerate(zip(samples, lines, strict=True)):
        if (
            type(sample) is not dict
            or sample.get("source_line_index") != index
            or type(line) is not dict
            or type(line.get("raw_text")) is not str
        ):
            raise _error("E-0047 bound LINE axis or numeric/date source drifted")

    family_id = spec.family_id
    reasons: set[str] = set()
    collision = False
    owners: list[dict[str, Any]] = []
    branches: list[dict[str, Any]] = []
    row_matches: dict[str, list[dict[str, Any]]] = {
        item.role: [] for item in spec.ordered_children + spec.optional_children
    }
    for sample in samples:
        text = sample["normalized_prediction"]
        match, collided = observation_v2._target_direct_match(
            text, alias_index, family_id, "OWNER", "OWNER"
        )
        collision |= collided
        if match is not None:
            owners.append(observation_v2._bound_line(sample, "OWNER", match))
        match, collided = observation_v2._target_branch_match(text, alias_index, family_id)
        collision |= collided
        if match is not None:
            branches.append(observation_v2._bound_line(sample, "BRANCH", match))
        for child in spec.ordered_children + spec.optional_children:
            match, collided = observation_v2._target_direct_match(
                text,
                alias_index,
                family_id,
                "ORDERED_CHILD" if child in spec.ordered_children else "OPTIONAL_CHILD",
                child.role,
            )
            collision |= collided
            if match is not None:
                row_matches[child.role].append(
                    observation_v2._bound_line(sample, child.role, match)
                )

    if collision:
        reasons.add("SEMANTIC_ALIAS_COLLISION")
    if len(owners) != 1:
        reasons.add("OWNER_NOT_RESOLVED_FROM_TRANSFORMER")
    if len(branches) != 1:
        reasons.add("BRANCH_NOT_RESOLVED_FROM_TRANSFORMER")
    required_roles = [item.role for item in spec.ordered_children]
    if any(len(row_matches[role]) != 1 for role in required_roles):
        reasons.add("ORDERED_CHILDREN_NOT_RESOLVED_FROM_TRANSFORMER")
    if any(row_matches[item.role] for item in spec.optional_children):
        reasons.add("OPTIONAL_CHILD_TOPOLOGY_NOT_IMPLEMENTED")
    if reasons:
        return (
            observation_v2._final_payload(source, binding, spec, alias_index, [], reasons),
            None,
        )

    owner = owners[0]
    branch = branches[0]
    required_labels = [row_matches[role][0] for role in required_roles]
    owner_y = observation_v2._center_y(owner["raw_pixel_bbox"])
    branch_y = observation_v2._center_y(branch["raw_pixel_bbox"])
    row_y = [observation_v2._center_y(label["raw_pixel_bbox"]) for label in required_labels]
    if not (owner_y < branch_y < row_y[0] and row_y == sorted(row_y)):
        reasons.add("OWNER_BRANCH_ORDERED_SIBLING_TOPOLOGY_NOT_RESOLVED")

    first_row_y = row_y[0]
    periods: list[tuple[Mapping[str, Any], str, str]] = []
    units: list[tuple[Mapping[str, Any], dict[str, Any], str]] = []
    numeric: list[tuple[Mapping[str, Any], str, Decimal]] = []
    numeric_geometry: list[Mapping[str, Any]] = []
    for sample, line in zip(samples, lines, strict=True):
        ppocr_text = line["raw_text"]
        y = observation_v2._center_y(sample["source_bbox_raw_pixels"])
        period = parse_local_accounting_period_v1(ppocr_text)
        if period is not None and branch_y < y < first_row_y:
            periods.append((sample, ppocr_text, period))
        value = observation_v2._parse_financial_integer(ppocr_text)
        if value is not None and period is None:
            numeric.append((sample, ppocr_text, value))
        if period is None and _is_numeric_observation_text(ppocr_text):
            numeric_geometry.append(sample)
        transformer_text = sample["normalized_prediction"]
        unit = parse_local_accounting_unit_v1(transformer_text)
        if unit is not None and branch_y < y < first_row_y:
            key = propose_vietnamese_semantic_surface_v1(
                transformer_text, alias_index
            ).accentless_comparison_key
            units.append((sample, unit, key))

    axis_count = spec.axis_layout.comparative_monetary_period_count
    periods.sort(key=lambda item: observation_v2._center_x(item[0]["source_bbox_raw_pixels"]))
    if (
        len(periods) != axis_count
        or len({item[2] for item in periods}) != axis_count
        or axis_count != 2
    ):
        reasons.add("TWO_COMPARATIVE_PERIOD_AXES_NOT_RESOLVED")
        lanes: list[float] = []
    else:
        lanes = [observation_v2._center_x(item[0]["source_bbox_raw_pixels"]) for item in periods]

    units.sort(key=lambda item: observation_v2._center_x(item[0]["source_bbox_raw_pixels"]))
    if (
        len(units) != axis_count
        or len({canonical_json_sha256_v1(item[1]) for item in units}) != 1
        or not lanes
        or not observation_v2._aligned_to_lanes([item[0] for item in units], lanes)
    ):
        reasons.add("PER_AXIS_UNIT_SCOPE_NOT_RESOLVED")

    assignment: dict[str, Any] | None = None
    row_value_items: dict[str, list[tuple[Mapping[str, Any], str, Decimal]]] = {}
    built_rows: list[dict[str, Any]] = []
    if lanes:
        assignment = lane_v1.build_ordered_row_value_lane_assignment_v1(
            [
                {
                    "bbox": list(label["raw_pixel_bbox"]),
                    "role": role,
                    "source_line_index": label["source_line_index"],
                }
                for role, label in zip(required_roles, required_labels, strict=True)
            ],
            [
                {
                    "bbox": list(sample["source_bbox_raw_pixels"]),
                    "source_line_index": sample["source_line_index"],
                }
                for sample in numeric_geometry
            ],
            [list(item[0]["source_bbox_raw_pixels"]) for item in periods],
        )
        if assignment["status"] != lane_v1.RESOLVED_STATUS:
            reasons.add(_ORDERED_ASSIGNMENT_BLOCKER)
            if assignment["metrics"]["companion_numeric_count"]:
                reasons.add(_UNTYPED_COMPANION_BLOCKER)
        else:
            numeric_by_line = {item[0]["source_line_index"]: item for item in numeric}
            if len(numeric_by_line) != len(numeric):
                raise _error("E-0047 numeric source line axis is not unique")
            selected_lines = {
                line
                for assigned in assignment["rows"]
                for line in assigned["value_source_line_indices"]
            }
            if not selected_lines <= set(numeric_by_line):
                reasons.add("NON_MONETARY_NUMERIC_CELL_IN_TARGET_LANE")
            for role, label, assigned in zip(
                required_roles, required_labels, assignment["rows"], strict=True
            ):
                if reasons:
                    break
                values = [numeric_by_line[index] for index in assigned["value_source_line_indices"]]
                row_value_items[role] = values
                built_rows.append(
                    {
                        "role": role,
                        "label": label,
                        "value_positions": [
                            observation_v2._value_position(item, axis_index)
                            for axis_index, item in enumerate(values)
                        ],
                    }
                )

    total_values: list[tuple[Mapping[str, Any], str, Decimal]] | None = None
    if len(built_rows) == len(required_roles):
        last_label = required_labels[-1]
        last_values = row_value_items[required_roles[-1]]
        previous_index = max(
            last_label["source_line_index"],
            *(item[0]["source_line_index"] for item in last_values),
        )
        by_index = {item[0]["source_line_index"]: item for item in numeric}
        following = [by_index.get(previous_index + offset) for offset in range(1, axis_count + 1)]
        if all(item is not None for item in following):
            narrowed = [item for item in following if item is not None]
            if observation_v2._aligned_to_lanes([item[0] for item in narrowed], lanes) and all(
                observation_v2._overlaps(
                    narrowed[0][0]["source_bbox_raw_pixels"],
                    item[0]["source_bbox_raw_pixels"],
                    1,
                )
                for item in narrowed[1:]
            ):
                total_values = sorted(
                    narrowed,
                    key=lambda item: observation_v2._center_x(item[0]["source_bbox_raw_pixels"]),
                )
        if total_values is None:
            reasons.add("IMMEDIATE_UNLABELED_TOTAL_NOT_RESOLVED")

    arithmetic = {"status": "NOT_EVALUABLE", "evaluated_axis_indexes": []}
    if total_values is not None and all(role in row_value_items for role in required_roles):
        evaluated: list[int] = []
        mismatch: list[int] = []
        for axis_index in range(axis_count):
            expected = sum(
                (row_value_items[role][axis_index][2] for role in spec.closure_child_roles),
                Decimal(),
            )
            observed = total_values[axis_index][2]
            evaluated.append(axis_index)
            if expected != observed:
                mismatch.append(axis_index)
        arithmetic = {
            "status": "VETOED" if mismatch else "CORROBORATED",
            "evaluated_axis_indexes": evaluated,
        }
        if mismatch:
            reasons.add("ARITHMETIC_CLOSURE_VETO")

    if reasons:
        return (
            observation_v2._final_payload(source, binding, spec, alias_index, [], reasons),
            assignment,
        )

    for label in (owner, branch, *required_labels):
        label["promotion_status"] = (
            "PROMOTED_BY_UNIQUE_COMPLETE_TOPOLOGY"
            if label["match_kind"].startswith("ACCENTLESS")
            else "EXACT_SURFACE_IN_COMPLETE_TOPOLOGY"
        )
    built_rows.append(
        {
            "role": "TOTAL",
            "label": None,
            "total_resolution": "IMMEDIATE_UNLABELED_NUMERIC_ROW",
            "value_positions": [
                observation_v2._value_position(item, axis_index)
                for axis_index, item in enumerate(total_values or [])
            ],
        }
    )
    axes = []
    for axis_index, (sample, raw_text, period) in enumerate(periods):
        span = observation_v2._ppocr_span(sample, raw_text, kind="DATE")
        span.update({"axis_index": axis_index, "period": period})
        axes.append(span)
    unit_labels = [observation_v2._unit_span(sample, unit, key) for sample, unit, key in units]
    all_boxes = [
        owner["canonical_bbox_mpt"],
        branch["canonical_bbox_mpt"],
        *(axis["canonical_bbox_mpt"] for axis in axes),
        *(unit["canonical_bbox_mpt"] for unit in unit_labels),
        *(value["canonical_bbox_mpt"] for row in built_rows for value in row["value_positions"]),
        *(label["canonical_bbox_mpt"] for label in required_labels),
    ]
    region = {
        "canonical_bbox_mpt": observation_v2._union_box(all_boxes),
        "owner_label": owner,
        "branch_label": branch,
        "axes": axes,
        "local_unit_labels": unit_labels,
        "rows": built_rows,
        "arithmetic": arithmetic,
        "topology": {
            "owner_resolution": True,
            "parent_child_edge": True,
            "ordered_sibling_set": True,
            "comparative_period_axis": True,
            "unit_scope_edge": True,
            "total_subtotal": True,
            "internal_additive_closure": True,
            "same_population_claimed": False,
            "row_frontier": True,
        },
    }
    return (
        observation_v2._final_payload(source, binding, spec, alias_index, [region], set()),
        assignment,
    )


def _projection(value: Mapping[str, Any], *, id_field: str | None = None) -> dict[str, Any]:
    result = {
        "payload_sha256": canonical_json_sha256_v1(value),
        "status": value["status"],
        "unresolved_reasons": canonical_clone_v1(value.get("unresolved_reasons", [])),
    }
    if id_field is not None:
        result[id_field] = value[id_field]
    if "metrics" in value:
        result["metrics"] = canonical_clone_v1(value["metrics"])
    return result


def _schema_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    result = _projection(value, id_field="candidate_set_id")
    result.update(
        {
            "candidate_report_norm_ids": sorted(
                {
                    report_norm_id
                    for role in value["role_candidates"]
                    for report_norm_id in role["candidate_report_norm_ids"]
                }
            ),
            "source_only_roles": sorted(
                role["typed_role"]
                for role in value["role_candidates"]
                if role["disposition"] == "SOURCE_ONLY_VALIDATION"
            ),
            "structural_context_candidate_report_norm_ids": sorted(
                report_norm_id
                for role in value["role_candidates"]
                if role["graph_node_kind"] == "ACCOUNTING_ROLE"
                for report_norm_id in role["candidate_report_norm_ids"]
            ),
            "unassessed_report_norm_ids": sorted(
                item["report_norm_id"] for item in value["unassessed_schema_children"]
            ),
            "value_row_candidate_report_norm_ids": sorted(
                report_norm_id
                for role in value["role_candidates"]
                if role["graph_node_kind"] == "LOGICAL_ROW"
                for report_norm_id in role["candidate_report_norm_ids"]
            ),
        }
    )
    return result


def _trial(
    trial: Mapping[str, Any],
    alias_index: Any,
    schema_authority: dict[str, Any],
    schema_by_id: dict[int, Any],
) -> dict[str, Any]:
    prior = trial["observation_candidate"]
    reasons = prior["unresolved_reasons"]
    targeted = (
        trial["semantic_page_binding"]["binding_mode"] == _ORDINARY_MODE
        and _ROW_VALUE_BLOCKER in reasons
    )
    if targeted:
        observation, assignment = _candidate_payload_with_ordered_lanes(
            trial["source_projection"],
            trial["semantic_page_binding"],
            alias_index,
        )
        if assignment is None:
            raise _error("E-0047 targeted row/value blocker produced no assignment")
        graph = graph_v2._build_from_observation(
            observation,
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            _FAMILY_SPECS,
        )
        candidate = schema_v1._validate_payload(
            schema_v1._build_payload(graph, schema_authority, schema_by_id)
        )
        mechanism_status = (
            "ASSIGNMENT_RESOLVED_FRONTIER_REBUILT"
            if assignment["status"] == lane_v1.RESOLVED_STATUS
            else "ASSIGNMENT_UNRESOLVED_FAIL_CLOSED"
        )
    else:
        assignment = None
        observation = prior
        graph = trial["semantic_graph"]
        candidate = trial["schema_candidate"]
        mechanism_status = "NOT_APPLICABLE_NO_EXISTING_ROW_VALUE_AXIS_BLOCKER"
    return {
        "trial_id": trial["trial_id"],
        "bank_provenance": trial["bank_provenance"],
        "page_ordinal": trial["selection_provenance"]["page_ordinal"],
        "binding_mode": trial["semantic_page_binding"]["binding_mode"],
        "mechanism_status": mechanism_status,
        "assignment": canonical_clone_v1(assignment),
        "prior_observation": _projection(prior),
        "observation": _projection(observation),
        "semantic_graph": _projection(graph, id_field="graph_id"),
        "schema_candidate": _schema_projection(candidate),
        "independent_numeric_status": "NOT_EVALUATED",
        "independent_mapping_status": "NOT_EVALUATED",
    }


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    targeted = [trial for trial in trials if trial["assignment"] is not None]
    return {
        "bank_count": len(trials),
        "mechanism_target_count": len(targeted),
        "assignment_resolved_count": sum(
            trial["assignment"]["status"] == lane_v1.RESOLVED_STATUS for trial in targeted
        ),
        "assignment_unresolved_count": sum(
            trial["assignment"]["status"] == lane_v1.UNRESOLVED_STATUS for trial in targeted
        ),
        "untyped_companion_blocked_count": sum(
            trial["assignment"]["metrics"]["companion_numeric_count"] > 0 for trial in targeted
        ),
        "accepted_structure_count": sum(
            trial["semantic_graph"]["status"] == "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE"
            for trial in trials
        ),
        "schema_candidate_ready_count": sum(
            trial["schema_candidate"]["status"] == "CANDIDATE_SET_READY" for trial in trials
        ),
        "independent_numeric_evaluated_count": 0,
        "independent_mapping_evaluated_count": 0,
        "verified_mapping_count": 0,
    }


def _build_payload(
    project_root: Path,
    e0046_payload: dict[str, Any],
    input_authority: dict[str, Any],
) -> dict[str, Any]:
    e0046._validate_sweep_shape(e0046_payload)
    alias_index = compile_vietnamese_family_alias_index_v1(_FAMILY_SPECS)
    schema_authority, schema_by_id = schema_v1._authority_snapshot(project_root)
    trials = [
        _trial(trial, alias_index, schema_authority, schema_by_id)
        for trial in e0046_payload["trials"]
    ]
    payload = {
        "format_version": FORMAT_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "state": STATE,
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": LOAN_MATURITY_BUCKETS_SPEC_V1.family_id,
        "bank_order": canonical_clone_v1(e0046_payload["bank_order"]),
        "input_authority": canonical_clone_v1(input_authority),
        "trials": trials,
        "metrics": _metrics(trials),
        "safety": canonical_clone_v1(_SAFETY),
    }
    payload["result_id"] = "e0047:lane-evaluation:" + canonical_json_sha256_v1(payload)
    return payload


def _contains_verified_claim(value: Any) -> bool:
    if type(value) is str:
        return value == "VERIFIED_BY_CODEX"
    if type(value) is list:
        return any(_contains_verified_claim(item) for item in value)
    if type(value) is dict:
        return any(
            _contains_verified_claim(key) or _contains_verified_claim(item)
            for key, item in value.items()
        )
    return False


def _validate_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _REF_FIELDS
        or type(value["path"]) is not str
        or not value["path"]
        or type(value["sha256"]) is not str
        or _SHA_RE.fullmatch(value["sha256"]) is None
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"E-0047 {label} ref drifted")
    return value


def _validate_input_authority(value: Any) -> None:
    if type(value) is not dict or set(value) != _INPUT_AUTHORITY_FIELDS:
        raise _error("E-0047 input authority fields drifted")
    capture = value["e0046_capture"]
    if (
        type(capture) is not dict
        or set(capture) != _CAPTURE_REF_FIELDS
        or capture["path"] != str(E0046_CAPTURE_PATH)
        or type(capture["sha256"]) is not str
        or _SHA_RE.fullmatch(capture["sha256"]) is None
        or type(capture["size_bytes"]) is not int
        or capture["size_bytes"] <= 0
        or type(capture["sweep_id"]) is not str
        or not capture["sweep_id"].startswith("e0046:provisional-sweep:")
    ):
        raise _error("E-0047 E-0046 capture authority drifted")
    seal = _validate_ref(value["e0046_seal"], "E-0046 seal")
    if seal["path"] != E0046_SEAL_PATH.as_posix():
        raise _error("E-0047 E-0046 seal path drifted")
    refs = value["implementation_refs"]
    if type(refs) is not list or len(refs) != len(_IMPLEMENTATION_PATHS):
        raise _error("E-0047 implementation ref denominator drifted")
    for expected_path, ref in zip(_IMPLEMENTATION_PATHS, refs, strict=True):
        if _validate_ref(ref, "implementation")["path"] != expected_path:
            raise _error("E-0047 implementation ref order/path drifted")


def _validate_projection(
    value: Any,
    label: str,
    *,
    id_field: str | None = None,
    metrics_required: bool = False,
    extra_fields: set[str] | None = None,
) -> None:
    fields = set(_PROJECTION_FIELDS)
    if id_field is not None:
        fields.add(id_field)
    if metrics_required:
        fields.add("metrics")
    fields.update(extra_fields or set())
    if (
        type(value) is not dict
        or set(value) != fields
        or type(value["payload_sha256"]) is not str
        or _SHA_RE.fullmatch(value["payload_sha256"]) is None
        or type(value["status"]) is not str
        or not value["status"]
        or type(value["unresolved_reasons"]) is not list
        or any(type(item) is not str for item in value["unresolved_reasons"])
        or value["unresolved_reasons"] != sorted(set(value["unresolved_reasons"]))
    ):
        raise _error(f"E-0047 {label} projection drifted")
    if id_field is not None and (type(value[id_field]) is not str or not value[id_field]):
        raise _error(f"E-0047 {label} identity drifted")
    if metrics_required:
        metrics = value["metrics"]

        def valid_metric_tree(item: Any) -> bool:
            if type(item) is int:
                return item >= 0
            return type(item) is dict and all(
                type(key) is str and valid_metric_tree(child) for key, child in item.items()
            )

        if type(metrics) is not dict or not metrics or not valid_metric_tree(metrics):
            raise _error(f"E-0047 {label} metrics drifted")


def _validate_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("E-0047 result fields drifted")
    result = value
    if (
        result["format_version"] != FORMAT_VERSION
        or result["experiment_id"] != EXPERIMENT_ID
        or result["state"] != STATE
        or result["claim_boundary"] != CLAIM_BOUNDARY
        or result["family_id"] != LOAN_MATURITY_BUCKETS_SPEC_V1.family_id
        or not same_typed_json_v1(result["bank_order"], list(e0046.BANK_ORDER))
        or not same_typed_json_v1(result["safety"], _SAFETY)
        or _contains_verified_claim(result)
    ):
        raise _error("E-0047 identity or safety boundary drifted")
    _validate_input_authority(result["input_authority"])
    trials = result["trials"]
    if type(trials) is not list or len(trials) != 8:
        raise _error("E-0047 trial denominator drifted")
    expected_modes = (
        e0046._ORDINARY_MODE,
        e0046._ORDINARY_MODE,
        e0046._NATIVE_MODE,
        e0046._ORDINARY_MODE,
        e0046._TERMINAL_MODE,
        e0046._ORDINARY_MODE,
        e0046._ORDINARY_MODE,
        e0046._ORDINARY_MODE,
    )
    for ordinal, (trial, bank, expected_mode) in enumerate(
        zip(trials, e0046.BANK_ORDER, expected_modes, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or set(trial) != _TRIAL_FIELDS
            or trial["trial_id"] != f"trial-{ordinal:04d}"
            or trial["page_ordinal"] != ordinal
            or trial["bank_provenance"] != bank
            or trial["binding_mode"] != expected_mode
            or trial["independent_numeric_status"] != "NOT_EVALUATED"
            or trial["independent_mapping_status"] != "NOT_EVALUATED"
        ):
            raise _error("E-0047 trial identity or verification boundary drifted")
        _validate_projection(trial["prior_observation"], "prior observation")
        _validate_projection(trial["observation"], "observation")
        _validate_projection(
            trial["semantic_graph"],
            "semantic graph",
            id_field="graph_id",
            metrics_required=True,
        )
        _validate_projection(
            trial["schema_candidate"],
            "schema candidate",
            id_field="candidate_set_id",
            metrics_required=True,
            extra_fields=_SCHEMA_PROJECTION_FIELDS,
        )
        schema_projection = trial["schema_candidate"]
        for field in _SCHEMA_PROJECTION_FIELDS:
            items = schema_projection[field]
            if type(items) is not list or items != sorted(set(items)):
                raise _error("E-0047 schema frontier details drifted")
            if field == "source_only_roles":
                typed = all(type(item) is str for item in items)
            else:
                typed = all(type(item) is int and item > 0 for item in items)
            if not typed:
                raise _error("E-0047 schema frontier detail types drifted")
        assignment = trial["assignment"]
        if assignment is not None:
            lane_v1._validate_result(assignment)
            expected_mechanism = (
                "ASSIGNMENT_RESOLVED_FRONTIER_REBUILT"
                if assignment["status"] == lane_v1.RESOLVED_STATUS
                else "ASSIGNMENT_UNRESOLVED_FAIL_CLOSED"
            )
            if (
                _ROW_VALUE_BLOCKER not in trial["prior_observation"]["unresolved_reasons"]
                or trial["mechanism_status"] != expected_mechanism
            ):
                raise _error("E-0047 mechanism target/status drifted")
        elif (
            trial["mechanism_status"] != "NOT_APPLICABLE_NO_EXISTING_ROW_VALUE_AXIS_BLOCKER"
            or _ROW_VALUE_BLOCKER in trial["prior_observation"]["unresolved_reasons"]
        ):
            raise _error("E-0047 non-target mechanism disposition drifted")
        if (
            trial["semantic_graph"]["status"] == "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE"
        ) != (trial["schema_candidate"]["status"] == "CANDIDATE_SET_READY"):
            raise _error("E-0047 graph/schema frontier status drifted")
    metrics = result["metrics"]
    if type(metrics) is not dict or set(metrics) != _METRIC_FIELDS:
        raise _error("E-0047 metric fields drifted")
    if any(type(metrics[field]) is not int or metrics[field] < 0 for field in _METRIC_FIELDS):
        raise _error("E-0047 metrics are not exact non-negative integers")
    if not same_typed_json_v1(metrics, _metrics(trials)):
        raise _error("E-0047 metrics are not derived from trials")
    material = canonical_clone_v1(result)
    identifier = material.pop("result_id")
    if type(
        identifier
    ) is not str or identifier != "e0047:lane-evaluation:" + canonical_json_sha256_v1(material):
        raise _error("E-0047 result identity drifted")
    return canonical_clone_v1(result)


def build_e0047_ordered_row_value_lane_evaluation(project_root: Path) -> dict[str, Any]:
    """Build the bounded mechanism result from the fixed sealed E-0046 capture."""

    root = _root(project_root)
    e0046_payload, authority = _input_authority(root)
    return _validate_shape(_build_payload(root, e0046_payload, authority))


def validate_e0047_ordered_row_value_lane_evaluation(
    value: Any,
    project_root: Path,
) -> dict[str, Any]:
    """Exact-rebuild E-0047 from the sealed capture and typed-compare it."""

    persisted = _validate_shape(value)
    root = _root(project_root)
    e0046_payload, authority = _input_authority(root)
    rebuilt = _validate_shape(_build_payload(root, e0046_payload, authority))
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("E-0047 result does not replay from the exact sealed E-0046 capture")
    return canonical_clone_v1(rebuilt)


def _main() -> int:
    result = build_e0047_ordered_row_value_lane_evaluation(PROJECT_ROOT)
    os.write(1, canonical_json_bytes_v1(result) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
