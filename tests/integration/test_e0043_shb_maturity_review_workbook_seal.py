from __future__ import annotations

import hashlib
import importlib.util
import json
from io import BytesIO
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from bctc_ai.export.canonical_xlsx import workbook_has_formula
from bctc_ai.export.shb_maturity_review_workbook_v1 import (
    E0042_RELATIVE_PATH,
    build_shb_maturity_review_workbook_v1,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SEAL_PATH = _PROJECT_ROOT / "docs/experiments/E-0043-shb-maturity-review-workbook-seal.json"
_SCRIPT = _PROJECT_ROOT / "scripts/experiments/export_shb_maturity_review_workbook_v1.py"
_SPEC = importlib.util.spec_from_file_location("e0043_review_pair_replay", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_REPLAY = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_REPLAY)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes(), object_pairs_hook=_reject_duplicate_keys)
    assert isinstance(value, dict)
    return value


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def test_e0043_seal_replays_and_validates_exact_review_only_pair() -> None:
    seal = _read_json(_SEAL_PATH)
    candidate, context = _REPLAY._build_exact_inputs()
    verification_bytes = (_PROJECT_ROOT / E0042_RELATIVE_PATH).read_bytes()
    rebuilt = build_shb_maturity_review_workbook_v1(
        candidate,
        context,
        verification_bytes,
    )

    files = {entry["role"]: entry for entry in seal["inventory"]["files"]}
    workbook_entry = files["REVIEW_ONLY_WORKBOOK"]
    provenance_entry = files["REVIEW_ONLY_MACHINE_PROVENANCE"]
    workbook_bytes = (_PROJECT_ROOT / workbook_entry["path"]).read_bytes()
    provenance_bytes = (_PROJECT_ROOT / provenance_entry["path"]).read_bytes()

    assert seal["capture_git"] == {
        "commit": "2f5329867be722e8f33db0a61ec34dee6a7bb26f",
        "dirty": False,
        "required_replay_relationship": (
            "EXACT_COMMIT_OR_CLEAN_DESCENDANT_WITH_UNCHANGED_BOUND_INPUTS_AND_IMPLEMENTATION"
        ),
    }
    assert workbook_bytes == rebuilt.workbook_bytes
    assert provenance_bytes == rebuilt.provenance_bytes
    assert (_sha256(workbook_bytes), len(workbook_bytes)) == (
        workbook_entry["sha256"],
        workbook_entry["size_bytes"],
    )
    assert (_sha256(provenance_bytes), len(provenance_bytes)) == (
        provenance_entry["sha256"],
        provenance_entry["size_bytes"],
    )

    registration = seal["s3_registration"]
    assert registration["snapshot_id"] == (
        "20260813T144429Z-e0042-shb-maturity-review-workbook-pair-4d5df001433c"
    )
    assert registration["manifest"]["sha256"] == (
        "16fea9099bcce9bbdcce1294148ba88c72b80566424aa789506dd904307716f8"
    )
    assert registration["run_record"]["sha256"] == (
        "5f9a6ea538c71808c5587bc0dacc997a29b902deb75574cbef14d1543654ab8e"
    )
    assert registration["inventory"] == {
        "logical_bytes": workbook_entry["size_bytes"] + provenance_entry["size_bytes"],
        "logical_file_count": 2,
        "unique_bytes": workbook_entry["size_bytes"] + provenance_entry["size_bytes"],
        "unique_object_count": 2,
    }
    assert {(entry["sha256"], entry["size_bytes"]) for entry in registration["objects"]} == {
        (workbook_entry["sha256"], workbook_entry["size_bytes"]),
        (provenance_entry["sha256"], provenance_entry["size_bytes"]),
    }
    assert registration["upload"] == {
        "reused_object_count": 0,
        "unique_object_count": 2,
        "uploaded_object_count": 2,
    }
    assert registration["restore"] == {
        "all_incremental_objects_restore_verified": True,
        "status": "PASS",
    }
    assert registration["independent_hydrate"] == {
        "exact_file_hashes_and_sizes": True,
        "status": "PASS",
    }

    provenance = json.loads(
        provenance_bytes,
        object_pairs_hook=_reject_duplicate_keys,
    )
    projection = provenance["projection"]
    contract = seal["review_projection_contract"]
    identities = seal["input_identities"]
    assert provenance["provenance_id"] == contract["provenance_id"]
    assert provenance["projection_sha256"] == contract["projection_sha256"]
    assert projection["projection_id"] == contract["projection_id"]
    assert provenance["workbook"] == {
        "creator": "bctc-ai/shb-maturity-review-v1",
        "formula_count": 0,
        "sha256": workbook_entry["sha256"],
        "sheet_names": contract["sheet_names"],
        "size_bytes": workbook_entry["size_bytes"],
    }
    assert projection["input_identities"] == {
        "e0042_numeric_verification": identities["e0042_numeric_verification"],
        "schema_candidate": identities["schema_candidate"],
        "statement_context": identities["statement_context"],
    }
    assert projection["shared_lineage"] == {
        "semantic_graph_id": identities["semantic_graph"]["graph_id"],
        "semantic_graph_sha256": identities["semantic_graph"]["sha256"],
        "semantic_page_binding_sha256": identities["semantic_page_binding_sha256"],
        "source_local_page_id": identities["source_projection"]["local_page_id"],
        "source_projection_sha256": identities["source_projection"]["sha256"],
    }
    assert projection["metrics"] == {
        "candidate_report_norm_id_count": 3,
        "provenance_cell_count": 8,
        "review_row_count": 4,
        "source_only_null_candidate_row_count": 1,
        "verified_observed_cell_count": 8,
    }
    assert [cell["cell_id"] for cell in projection["provenance_cells"]] == contract["cell_ids"]
    assert [row["candidate_report_norm_id"] for row in projection["review_rows"]] == [
        753,
        754,
        755,
        None,
    ]
    assert provenance["safety"] == seal["safety"]
    assert all(
        provenance["safety"][key] is False
        for key in (
            "accepted_schema_mapping_authority",
            "accounting_truth_authority",
            "canonicalization_authority",
            "export_authority",
            "production_authority",
            "value_materialization_authority",
        )
    )

    workbook = load_workbook(BytesIO(workbook_bytes), data_only=False)
    try:
        assert workbook.sheetnames == contract["sheet_names"]
        assert not workbook_has_formula(workbook)
        assert workbook["CELL_PROVENANCE"].max_row - 2 == 8
    finally:
        workbook.close()
