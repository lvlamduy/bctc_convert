from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/experiments/run_gemini_json_first_accounting_family_v1.py"
SPEC = importlib.util.spec_from_file_location("run_gemini_json_first_accounting_family_v1", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
target = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(target)


def _compiled() -> dict:
    paths = (
        "config/families/tm-interbank-deposits-loans-topology-v4.json",
        "config/families/tm-interbank-deposits-loans-evaluation-v4.json",
        "config/families/tm-interbank-deposits-loans-schema-binding-v4.json",
    )
    topology, evaluation, schema = (
        json.loads((ROOT / path).read_text(encoding="utf-8")) for path in paths
    )
    return target.compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)


def _mapping(role: str, report_norm_id: int, values: tuple[int, int]) -> dict:
    return {
        "columns": [{"value_kind": "MONEY"}, {"value_kind": "MONEY"}],
        "report_norm_id": report_norm_id,
        "role": role,
        "values": [
            {"coefficient": value, "source_text": str(value), "state": "RAW_SIGNED_INTEGER"}
            for value in values
        ],
    }


def _candidate(candidate_id: str, roles: list[tuple[str, int]]) -> dict:
    return {
        "candidate_id": candidate_id,
        "mappings": [
            _mapping(
                role,
                report_norm_id,
                (170, 139) if role == "INTERBANK_DEPOSITS_AND_LOANS" else (1, 1),
            )
            for role, report_norm_id in roles
        ],
    }


def test_exact_role_rich_detail_uniquely_supersedes_its_summary() -> None:
    summary = _candidate(
        "summary",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("INTERBANK_DEPOSIT_GROUP", 576),
            ("INTERBANK_LOAN_GROUP", 585),
            ("TOTAL_INTERBANK_PROVISION", 5718),
        ],
    )
    detail = _candidate(
        "detail",
        [
            ("INTERBANK_DEPOSITS_AND_LOANS", 575),
            ("INTERBANK_DEPOSIT_GROUP", 576),
            ("DEMAND_DEPOSIT_GROUP", 577),
            ("DEMAND_DEPOSIT_VND", 578),
            ("TERM_DEPOSIT_GROUP", 580),
            ("TERM_DEPOSIT_VND", 581),
            ("INTERBANK_LOAN_GROUP", 585),
            ("INTERBANK_LOAN_VND", 586),
            ("INTERBANK_LOAN_PROVISION", 590),
        ],
    )
    assert target._selected_ready_candidate([summary, detail], compiled_specs=_compiled()) == detail


def test_candidate_selection_rejects_root_drift_and_equal_detail_ambiguity() -> None:
    roles = [
        ("INTERBANK_DEPOSITS_AND_LOANS", 575),
        ("INTERBANK_DEPOSIT_GROUP", 576),
        ("INTERBANK_LOAN_GROUP", 585),
    ]
    first = _candidate("first", roles)
    second = _candidate("second", roles)
    assert target._selected_ready_candidate([first, second], compiled_specs=_compiled()) is None

    second["mappings"][0]["values"][0]["coefficient"] += 1
    assert target._selected_ready_candidate([first, second], compiled_specs=_compiled()) is None
