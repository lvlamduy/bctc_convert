"""Close E-0077 source rows through the project-owner approved `Khác` bucket."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_PATH = Path(
    "docs/experiments/E-0077-other-payables-liabilities-8bank-codex-verified-mapping-v1.json"
)
BASE_SHA256 = "0c5e01ee030f99a2743e65206c24ae2068424314eec0982c8693176fccea8347"
BASE_RESULT_ID = "e0077:result:489111c8ab70038c0004e1a8242fa2c7e96b405d3e59fdfa0b5878d9414db912"
OUTPUT_PATH = Path("docs/experiments/E-0132A-other-payables-project-owner-other-closure-v1.json")
FORMAT_VERSION = "OTHER_PAYABLES_PROJECT_OWNER_OTHER_CLOSURE_V1"
CLAIM_BOUNDARY = (
    "FIXED_E0077_EIGHT_BOUND_REPORT_PROJECT_OWNER_CLOSURE_OF_OPL_001_TO_OPL_018_"
    "THROUGH_REPORT_NORM_ID_1127_OTHER_EXACT_BASE_VALUES_LIVE_TM_SCHEMA_SOURCE_"
    "GROUP_AND_DETAIL_NOT_DOUBLE_COUNTED_NO_CANONICAL_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_mapping_rule": False,
    "base_artifact_rewritten_or_relabelled": False,
    "canonicalization_or_export_authority": False,
    "live_tm_schema_checked": True,
    "persisted_result_self_authenticating": False,
    "project_owner_adjudication_authority": True,
    "public_exact_replay_required": True,
    "source_detail_and_verified_group_parent_double_counted": False,
    "source_locator_fields_are_evidence_only": True,
    "text_similarity_alone_used_for_mapping": False,
}
_EXPECTED_IDS = {f"OPL-{ordinal:03d}" for ordinal in range(1, 19)}
_EXPECTED_BANK_COUNTS = {"ACB": 2, "VPB": 8, "CTG": 1, "VIB": 7}


class OtherPayablesProjectOwnerOtherClosureV1Error(ValueError):
    """The pinned base, live schema or project-owner closure drifted."""


def _error(message: str) -> OtherPayablesProjectOwnerOtherClosureV1Error:
    return OtherPayablesProjectOwnerOtherClosureV1Error(message)


def _fixed_base() -> tuple[dict[str, Any], dict[str, Any]]:
    payload = (PROJECT_ROOT / BASE_PATH).read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("E-0077 base is not valid UTF-8 JSON") from exc
    if (
        type(value) is not dict
        or digest != BASE_SHA256
        or value.get("result_id") != BASE_RESULT_ID
        or value.get("metrics", {}).get("open_source_row_count") != 18
    ):
        raise _error("pinned E-0077 base drifted")
    return value, {
        "path": BASE_PATH.as_posix(),
        "result_id": BASE_RESULT_ID,
        "sha256": digest,
        "size_bytes": len(payload),
    }


def _schema_binding() -> tuple[dict[str, Any], dict[str, Any]]:
    authority, by_id = _authority_snapshot(PROJECT_ROOT)
    item = by_id.get(1127)
    if (
        item is None
        or item.statement_type != "TM"
        or item.canonical_name != "Khác"
        or item.parent_id != 1118
        or item.display_order != 645
    ):
        raise _error("live ReportNormId 1127 schema binding drifted")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }, authority


def _mappings(base: Mapping[str, Any], schema: Mapping[str, Any]) -> list[dict[str, Any]]:
    trials = base.get("trials")
    if type(trials) is not list or len(trials) != 8:
        raise _error("E-0077 trial denominator drifted")
    rows: list[dict[str, Any]] = []
    for trial in trials:
        bank = trial.get("document_provenance")
        page_span = trial.get("page_span")
        unresolved = trial.get("unmapped_source_rows")
        if type(bank) is not str or type(page_span) is not list or type(unresolved) is not list:
            raise _error("E-0077 unresolved trial shape drifted")
        for source in unresolved:
            item_id = source.get("item_id")
            if item_id not in _EXPECTED_IDS:
                raise _error("unexpected E-0077 unresolved item")
            rows.append(
                {
                    "bank_provenance": bank,
                    "ledger_id": item_id,
                    "page_span": canonical_clone_v1(page_span),
                    "project_owner_decision": (
                        "SOURCE_ROW_WITHOUT_DEDICATED_SCHEMA_LEAF_MAPS_TO_1127_OTHER; "
                        "IT_REMAINS_A_NONADDITIVE_BREAKDOWN_OF_ITS_ALREADY_VERIFIED_PRINTED_"
                        "GROUP_OR_FAMILY_PARENT"
                    ),
                    "schema_binding": canonical_clone_v1(schema),
                    "source_label_evidence": canonical_clone_v1(source.get("label_evidence")),
                    "source_values": canonical_clone_v1(source.get("values")),
                    "status": "VERIFIED_BY_PROJECT_OWNER_AND_CODEX",
                }
            )
    ids = {row["ledger_id"] for row in rows}
    bank_counts = {
        bank: sum(row["bank_provenance"] == bank for row in rows) for bank in _EXPECTED_BANK_COUNTS
    }
    if ids != _EXPECTED_IDS or bank_counts != _EXPECTED_BANK_COUNTS or len(rows) != 18:
        raise _error("E-0077 owner-closure denominator drifted")
    return rows


def _metrics(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "affected_document_count": len({row["bank_provenance"] for row in rows}),
        "closed_ledger_row_count": len(rows),
        "remaining_e0077_open_row_count": 0,
        "verified_source_value_component_count": sum(
            len(value["components"]) for row in rows for value in row["source_values"]
        ),
    }


def _validate(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "authority",
        "base_result_ref",
        "claim_boundary",
        "format_version",
        "mappings",
        "metrics",
        "result_id",
        "schema_authority",
        "state",
    }:
        raise _error("other-payables owner-closure fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "OTHER_PAYABLES_PROJECT_OWNER_OTHER_CLOSURE_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["mappings"]) is not list
        or not same_typed_json_v1(value["metrics"], _metrics(value["mappings"]))
    ):
        raise _error("other-payables owner-closure identity drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0132a:result:" + canonical_json_sha256_v1(material):
        raise _error("other-payables owner-closure result ID drifted")
    return canonical_clone_v1(value)


def build_other_payables_project_owner_other_closure_v1() -> dict[str, Any]:
    base, base_ref = _fixed_base()
    schema, schema_authority = _schema_binding()
    mappings = _mappings(base, schema)
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "base_result_ref": base_ref,
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "mappings": mappings,
        "metrics": _metrics(mappings),
        "schema_authority": schema_authority,
        "state": "OTHER_PAYABLES_PROJECT_OWNER_OTHER_CLOSURE_COMPLETE",
    }
    return _validate(
        {**material, "result_id": "e0132a:result:" + canonical_json_sha256_v1(material)}
    )


def validate_other_payables_project_owner_other_closure_v1(value: Any) -> dict[str, Any]:
    supplied = _validate(value)
    rebuilt = build_other_payables_project_owner_other_closure_v1()
    if not same_typed_json_v1(supplied, rebuilt):
        raise _error("other-payables owner closure does not replay exactly")
    return supplied


def main() -> int:
    value = build_other_payables_project_owner_other_closure_v1()
    (PROJECT_ROOT / OUTPUT_PATH).write_bytes(canonical_json_bytes_v1(value))
    print(value["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
