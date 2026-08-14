#!/usr/bin/env python3
"""Join MBB structure and numeric evidence without promoting schema mappings.

E-0049 is the fail-closed hand-off between automated checks and exceptional
source review.  It exact-replays E-0047 and E-0048, reconstructs the full MBB
schema-candidate payload, and derives the smallest review queue.  No item is
marked mapped or VERIFIED_BY_CODEX here.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import capture_e0048_mbb_maturity_numeric_verification as e0048
import evaluate_e0047_ordered_row_value_lane_assignment as e0047

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.mapping import semantic_local_accounting_schema_candidate_v1 as schema_v1
from bctc_ai.source_structure import semantic_local_accounting_graph_v2 as graph_v2
from bctc_ai.source_structure import semantic_statement_context_v1 as context_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.vietnamese_semantic_surface_v1 import (
    compile_vietnamese_family_alias_index_v1,
)

__all__ = [
    "E0049MBBMappingReadinessError",
    "build_e0049_mbb_maturity_mapping_readiness_v1",
    "validate_e0049_mbb_maturity_mapping_readiness_v1",
]


FORMAT_VERSION = "E0049_MBB_MATURITY_MAPPING_READINESS_AUDIT_V1"
EXPERIMENT_ID = "E-0049"
STATE = "AUTOMATED_STRUCTURE_AND_NUMERIC_CHECKS_COMPLETE_EXCEPTIONAL_REVIEW_PENDING"
STATUS = "UNRESOLVED_MAPPING_EXCEPTIONAL_SOURCE_REVIEW_REQUIRED"
CLAIM_BOUNDARY = (
    "EXACT_E0047_STRUCTURE_AND_E0048_NUMERIC_READINESS_JOIN_ONLY_"
    "NO_STATEMENT_CONTEXT_INHERITANCE_PIXEL_TRANSCRIPTION_SCHEMA_MAPPING_"
    "VERIFIED_BY_CODEX_CANONICALIZATION_EXPORT_OR_DOCUMENT_ABSENCE_AUTHORITY"
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path("docs/experiments/E-0049-mbb-maturity-mapping-readiness.json")
_ROLES = ("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "TOTAL")
_ROLE_IDS = {"SHORT_TERM": 753, "MEDIUM_TERM": 754, "LONG_TERM": 755, "TOTAL": None}
_VALUE_IDS = (753, 754, 755)
_EXPECTED_CANDIDATE_SET_ID = (
    "slascv1:candidate:2544ffdd12338be6b968cdc68137a42b85fd612c73ddc264e5593fa029d1669a"
)
_SAFETY = {
    "automatic_numeric_checks_completed": True,
    "candidate_ids_are_mappings": False,
    "document_absence_claimed": False,
    "exceptional_review_queue_only": True,
    "mapping_authority": False,
    "persisted_result_self_authenticating": False,
    "source_only_total_has_report_norm_id": False,
    "verified_by_codex_claimed": False,
}
_TOP_FIELDS = {
    "automated_checks",
    "candidate_items",
    "claim_boundary",
    "exceptional_review_queue",
    "experiment_id",
    "format_version",
    "inputs",
    "metrics",
    "near_neighbours",
    "readiness_id",
    "safety",
    "state",
    "status",
}


class E0049MBBMappingReadinessError(RuntimeError):
    """The joined readiness result or one of its exact inputs drifted."""


def _error(message: str) -> E0049MBBMappingReadinessError:
    return E0049MBBMappingReadinessError(message)


def _strict_json(raw: bytes, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise _error(f"{label} repeats JSON key {key!r}")
            result[key] = value
        return result

    def reject(value: str) -> None:
        raise _error(f"{label} contains non-finite JSON constant {value}")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict UTF-8 JSON") from exc


def _ref(path: Path, raw: bytes, **extra: Any) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        **extra,
    }


def _read(root: Path, path: Path, label: str) -> bytes:
    return e0047._stable_regular_bytes(root / path, label)


def _contains_verified(value: Any) -> bool:
    if type(value) is str:
        return value == "VERIFIED_BY_CODEX"
    if type(value) is list:
        return any(_contains_verified(item) for item in value)
    if type(value) is dict:
        return any(
            _contains_verified(key) or _contains_verified(item) for key, item in value.items()
        )
    return False


def _readiness_id(value: dict[str, Any]) -> str:
    material = canonical_clone_v1(value)
    material.pop("readiness_id", None)
    return "e0049:mapping-readiness:" + canonical_json_sha256_v1(material)


def _source_frontier(
    root: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    e0047_raw = _read(root, e0048.E0047_PATH, "E-0047 result")
    evaluated = e0047.validate_e0047_ordered_row_value_lane_evaluation(
        e0047._strict_json_bytes(e0047_raw, "E-0047 result"), root
    )
    e0046_payload, _authority = e0047._input_authority(root)
    trial = e0046_payload["trials"][e0048._MBB_PAGE_ORDINAL - 1]
    if trial["bank_provenance"] != e0048._MBB_BANK:
        raise _error("E-0049 MBB trial order drifted")
    alias_index = compile_vietnamese_family_alias_index_v1(e0047._FAMILY_SPECS)
    observation, assignment = e0047._candidate_payload_with_ordered_lanes(
        trial["source_projection"], trial["semantic_page_binding"], alias_index
    )
    if assignment is None or assignment["status"] != "RESOLVED_ORDERED_ROW_VALUE_LANES":
        raise _error("E-0049 MBB ordered-lane assignment drifted")
    graph = graph_v2._build_from_observation(
        observation, e0047.LOAN_MATURITY_BUCKETS_SPEC_V1, e0047._FAMILY_SPECS
    )
    authority, by_id = schema_v1._authority_snapshot(root)
    candidate = schema_v1._build_payload(graph, authority, by_id)
    if (
        graph["status"] != "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE"
        or candidate["status"] != "CANDIDATE_SET_READY"
        or candidate["candidate_set_id"] != _EXPECTED_CANDIDATE_SET_ID
        or evaluated["trials"][1]["semantic_graph"]["graph_id"] != graph["graph_id"]
        or evaluated["trials"][1]["schema_candidate"]["candidate_set_id"]
        != candidate["candidate_set_id"]
    ):
        raise _error("E-0049 structure/schema frontier differs from E-0047")
    return (
        canonical_clone_v1(evaluated),
        canonical_clone_v1(trial["source_projection"]),
        canonical_clone_v1(trial["semantic_page_binding"]),
        canonical_clone_v1(graph),
        canonical_clone_v1(candidate),
    )


def _numeric_frontier(root: Path) -> tuple[dict[str, Any], bytes]:
    raw = _read(root, e0048.VERIFICATION_PATH, "E-0048 verification")
    value = e0048.validate_e0048_mbb_maturity_numeric_verification_v1(
        _strict_json(raw, "E-0048 verification"), root
    )
    if (
        value["status"] != "COMPLETE_WITH_EXACT_EIGHT_CELL_AGREEMENT_AND_TWO_AXIS_CLOSURE"
        or value["metrics"]["verified_cell_count"] != 8
        or value["metrics"]["corroborated_closure_axis_count"] != 2
        or value["metrics"]["mapped_cell_count"] != 0
    ):
        raise _error("E-0049 requires the exact complete numeric-only E-0048 result")
    return value, raw


def _candidate_items(candidate: dict[str, Any], numeric: dict[str, Any]) -> list[dict[str, Any]]:
    role_candidates = {item["typed_role"]: item for item in candidate["role_candidates"]}
    numeric_by_role: dict[str, list[dict[str, Any]]] = {role: [] for role in _ROLES}
    for cell in numeric["cells"]:
        numeric_by_role[cell["row_role"]].append(cell)
    items = []
    for role in _ROLES:
        schema = role_candidates[role]
        expected_id = _ROLE_IDS[role]
        ids = schema["candidate_report_norm_ids"]
        if ids != ([] if expected_id is None else [expected_id]):
            raise _error("E-0049 candidate role/schema identity drifted")
        cells = sorted(numeric_by_role[role], key=lambda item: item["axis_ordinal"])
        if len(cells) != 2 or any(
            cell["verification_status"] != "VERIFIED_OBSERVED_VALUE" for cell in cells
        ):
            raise _error("E-0049 role numeric verification frontier drifted")
        items.append(
            {
                "automatic_checks": {
                    "exact_digit_and_sign_agreement": "PASS",
                    "source_crop_identity": "PASS",
                    "source_graph_value_role": "PASS",
                    "two_axis_core_closure": "PASS",
                },
                "disposition": (
                    "SOURCE_ONLY_VALIDATION_MAPPING_INELIGIBLE"
                    if role == "TOTAL"
                    else "SCHEMA_CANDIDATE_MAPPING_UNRESOLVED"
                ),
                "numeric_values": [cell["normalized_numeric_value"] for cell in cells],
                "report_norm_id": expected_id,
                "source_line_indices": [cell["source_line_index"] for cell in cells],
                "typed_role": role,
            }
        )
    return items


def _exception_queue(
    source: dict[str, Any], binding: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    context = context_v1._build(binding)
    if context["status"] != context_v1.UNRESOLVED_STATUS or context["unresolved_reasons"] != [
        "NO_EXACT_SUPPORTED_VISIBLE_PAGE_HEADING"
    ]:
        raise _error("E-0049 expected one page-local statement-context exception")
    samples = binding["samples"]
    lines = source["page_result"]["lines"]
    medium_sample = samples[94]
    medium_line = lines[94]
    margin = [
        {
            "crop_sha256": samples[index]["crop_ref"]["sha256"],
            "semantic_proposal_text": samples[index]["raw_prediction"],
            "source_line_index": index,
            "source_primary_text": lines[index]["raw_text"],
        }
        for index in range(102, 108)
    ]
    queue = [
        {
            "automatic_disposition": "UNRESOLVED",
            "code": "DOCUMENT_STATEMENT_CONTEXT_INHERITANCE_NOT_AUTHENTICATED",
            "evidence": {
                "page_local_context_diagnostic": context,
                "required_anchor": "PRIOR_VISIBLE_DOCUMENT_STATEMENT_HEADING",
            },
            "review_scope": "TABLE",
        },
        {
            "automatic_disposition": "UNRESOLVED",
            "code": "MEDIUM_TERM_SEMANTIC_PIXEL_TRANSCRIPTION_RECONCILIATION_REQUIRED",
            "evidence": {
                "crop_sha256": medium_sample["crop_ref"]["sha256"],
                "independent_pixel_transcription_status": "NOT_EVALUATED",
                "semantic_proposal_text": medium_sample["raw_prediction"],
                "source_line_index": 94,
                "source_primary_text": medium_line["raw_text"],
            },
            "review_scope": "ITEM_MEDIUM_TERM",
        },
        {
            "automatic_disposition": "UNRESOLVED",
            "code": "VISIBLE_OPTIONAL_MARGIN_CHILD_NOT_ADJUDICATED",
            "evidence": {
                "excluded_from_strict_core": True,
                "lines": margin,
                "schema_near_neighbour_report_norm_id": 5747,
            },
            "review_scope": "NEAR_NEIGHBOUR_AND_POPULATION_BOUNDARY",
        },
    ]
    return queue, context


def _build(root: Path) -> dict[str, Any]:
    evaluated, source, binding, graph, candidate = _source_frontier(root)
    numeric, numeric_raw = _numeric_frontier(root)
    items = _candidate_items(candidate, numeric)
    queue, context = _exception_queue(source, binding)
    e0047_raw = _read(root, e0048.E0047_PATH, "E-0047 result")
    result = {
        "automated_checks": {
            "candidate_set_id": candidate["candidate_set_id"],
            "candidate_value_report_norm_ids": list(_VALUE_IDS),
            "numeric_verification_id": numeric["verification_id"],
            "schema_candidate_status": candidate["status"],
            "semantic_graph_id": graph["graph_id"],
            "semantic_graph_status": graph["status"],
            "source_only_roles": ["TOTAL"],
            "two_axis_closure": canonical_clone_v1(numeric["closure_equations"]),
        },
        "candidate_items": items,
        "claim_boundary": CLAIM_BOUNDARY,
        "exceptional_review_queue": queue,
        "experiment_id": EXPERIMENT_ID,
        "format_version": FORMAT_VERSION,
        "inputs": {
            "e0047": _ref(e0048.E0047_PATH, e0047_raw, result_id=evaluated["result_id"]),
            "e0048": _ref(
                e0048.VERIFICATION_PATH,
                numeric_raw,
                verification_id=numeric["verification_id"],
            ),
            "schema_candidate": {
                "candidate_set_id": candidate["candidate_set_id"],
                "sha256": canonical_json_sha256_v1(candidate),
            },
            "semantic_page_binding_sha256": canonical_json_sha256_v1(binding),
            "source_projection_sha256": canonical_json_sha256_v1(source),
            "statement_context_page_local_diagnostic_id": context["context_id"],
        },
        "metrics": {
            "candidate_value_row_count": 3,
            "exceptional_review_item_count": len(queue),
            "mapping_verified_row_count": 0,
            "numeric_verified_cell_count": numeric["metrics"]["verified_cell_count"],
            "source_only_validation_row_count": 1,
            "unresolved_mapping_row_count": 3,
        },
        "near_neighbours": [
            {
                "disposition": "VISIBLE_OUTSIDE_STRICT_THREE_ROW_CORE_NOT_ADJUDICATED",
                "report_norm_id": 5747,
                "status": "UNRESOLVED",
                "whole_document_absence_claim": False,
            },
            {
                "disposition": "SCHEMA_CONTEXT_UNRESOLVED_ORPHAN_MAPPING_INELIGIBLE",
                "report_norm_id": 1944,
                "status": "UNRESOLVED",
                "whole_document_absence_claim": False,
            },
        ],
        "readiness_id": "",
        "safety": canonical_clone_v1(_SAFETY),
        "state": STATE,
        "status": STATUS,
    }
    result["readiness_id"] = _readiness_id(result)
    return result


def _validate_shape(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _TOP_FIELDS:
        raise _error("E-0049 result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["experiment_id"] != EXPERIMENT_ID
        or value["state"] != STATE
        or value["status"] != STATUS
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or not same_typed_json_v1(value["safety"], _SAFETY)
        or value["readiness_id"] != _readiness_id(value)
        or _contains_verified(value)
    ):
        raise _error("E-0049 identity or safety boundary drifted")
    items = value["candidate_items"]
    if (
        type(items) is not list
        or len(items) != 4
        or [item.get("typed_role") for item in items] != list(_ROLES)
        or [item.get("report_norm_id") for item in items] != [753, 754, 755, None]
        or items[-1].get("disposition") != "SOURCE_ONLY_VALIDATION_MAPPING_INELIGIBLE"
    ):
        raise _error("E-0049 candidate item frontier drifted")
    queue = value["exceptional_review_queue"]
    expected_codes = [
        "DOCUMENT_STATEMENT_CONTEXT_INHERITANCE_NOT_AUTHENTICATED",
        "MEDIUM_TERM_SEMANTIC_PIXEL_TRANSCRIPTION_RECONCILIATION_REQUIRED",
        "VISIBLE_OPTIONAL_MARGIN_CHILD_NOT_ADJUDICATED",
    ]
    if (
        type(queue) is not list
        or [item.get("code") for item in queue] != expected_codes
        or any(item.get("automatic_disposition") != "UNRESOLVED" for item in queue)
    ):
        raise _error("E-0049 exceptional review queue drifted")
    metrics = value["metrics"]
    if not same_typed_json_v1(
        metrics,
        {
            "candidate_value_row_count": 3,
            "exceptional_review_item_count": 3,
            "mapping_verified_row_count": 0,
            "numeric_verified_cell_count": 8,
            "source_only_validation_row_count": 1,
            "unresolved_mapping_row_count": 3,
        },
    ):
        raise _error("E-0049 metrics drifted")
    neighbours = value["near_neighbours"]
    if (
        type(neighbours) is not list
        or [item.get("report_norm_id") for item in neighbours] != [5747, 1944]
        or any(
            item.get("status") != "UNRESOLVED"
            or item.get("whole_document_absence_claim") is not False
            for item in neighbours
        )
    ):
        raise _error("E-0049 near-neighbour boundary drifted")
    return canonical_clone_v1(value)


def build_e0049_mbb_maturity_mapping_readiness_v1(project_root: Path) -> dict[str, Any]:
    root = e0047._root(project_root)
    return _validate_shape(_build(root))


def validate_e0049_mbb_maturity_mapping_readiness_v1(
    value: Any, project_root: Path
) -> dict[str, Any]:
    persisted = _validate_shape(value)
    rebuilt = build_e0049_mbb_maturity_mapping_readiness_v1(project_root)
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("persisted E-0049 readiness differs from exact live replay")
    return rebuilt


def _main() -> int:
    value = build_e0049_mbb_maturity_mapping_readiness_v1(PROJECT_ROOT)
    target = PROJECT_ROOT / OUTPUT_PATH
    if target.exists():
        raise _error("refusing to overwrite E-0049 mapping-readiness artifact")
    atomic_write_json(target, value)
    os.write(
        1,
        (
            json.dumps(
                {
                    "exceptional_review_item_count": 3,
                    "readiness_id": value["readiness_id"],
                    "status": value["status"],
                },
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
