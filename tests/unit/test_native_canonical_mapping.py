from __future__ import annotations

import copy
import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from bctc_ai.cli.main import build_parser
from bctc_ai.core.hashing import sha256_file
from bctc_ai.mapping import native_canonical as native
from bctc_ai.mapping.ordered_subgraph_v2 import build_schema_projection_v2

_ROWS_RELATIVE = Path("output/development/vpb-q1-2026-native-rows-v1/statement-rows.json")
_ROWS_SHA256 = "fa1c5d1cbc0237b2fc7c65791857b21e6f6884d2acbe9fc2a17d0da5e661521f"


def _page(payload: dict, page_number: int) -> dict:
    return next(page for page in payload["pages"] if page["page"] == page_number)


def _row(payload: dict, page_number: int, page_row_order: int) -> dict:
    return next(
        row
        for row in _page(payload, page_number)["rows"]
        if row["row_id"].endswith(f":row-{page_row_order:04d}")
    )


@pytest.fixture(scope="session")
def real_inputs(project_root: Path) -> dict:
    rows = json.loads((project_root / _ROWS_RELATIVE).read_text(encoding="utf-8"))
    policy = native.load_native_canonical_mapping_policy(
        project_root / native.POLICY_RELATIVE_PATH, project_root
    )
    items, projections, coverage, accepted_aliases, schema_identity = native._load_schema_bundle(
        project_root, policy
    )
    rules = schema_identity.pop("_cash_flow_rules")
    audited_formulas = schema_identity.pop("_audited_formulas")
    return {
        "rows": rows,
        "items": items,
        "projections": projections,
        "coverage": coverage,
        "rules": rules,
        "accepted_aliases": accepted_aliases,
        "audited_formulas": audited_formulas,
        "policy": policy,
        "schema_identity": schema_identity,
    }


def _resolve(real_inputs: dict, rows: dict) -> dict:
    return native.resolve_native_canonical_mapping(
        rows,
        rows_sha256=_ROWS_SHA256,
        schema_items=real_inputs["items"],
        projections=real_inputs["projections"],
        coverage=real_inputs["coverage"],
        cash_flow_rules=real_inputs["rules"],
        accepted_aliases=real_inputs["accepted_aliases"],
        audited_formulas=real_inputs["audited_formulas"],
        policy=real_inputs["policy"],
    )


def _mock_current_bytes_as_producer_commit(
    monkeypatch: pytest.MonkeyPatch,
    project_root: Path,
    snapshots: dict,
) -> None:
    policy_path = native.POLICY_RELATIVE_PATH.as_posix()
    source_config_path = snapshots["policy"]["payload"]["schema_authority"]["source_config"]["path"]

    def committed_identity(_root: Path, _commit: str, raw_path: str) -> dict:
        path = project_root / raw_path
        if raw_path == policy_path:
            digest = snapshots["policy"]["source_sha256"]
        elif raw_path == source_config_path:
            digest = snapshots["policy"]["payload"]["schema_authority"]["source_config"]["sha256"]
        else:
            formula = next(
                record
                for record in snapshots["audited_formulas"]["records"]
                if record["authority_evidence"]["audit_path"] == raw_path
            )
            digest = formula["authority_evidence"]["audit_sha256"]
        return {"path": raw_path, "sha256": digest, "size_bytes": path.stat().st_size}

    def committed_yaml(_root: Path, _commit: str, raw_path: str) -> dict:
        if raw_path == policy_path:
            return copy.deepcopy(snapshots["policy"]["payload"])
        assert raw_path == source_config_path
        return native.yaml.safe_load((project_root / raw_path).read_text(encoding="utf-8"))

    monkeypatch.setattr(native, "_file_identity_at_commit", committed_identity)
    monkeypatch.setattr(native, "_yaml_payload_at_commit", committed_yaml)
    monkeypatch.setattr(
        native,
        "_json_payload_at_commit",
        lambda _root, _commit, raw_path: json.loads(
            (project_root / raw_path).read_text(encoding="utf-8")
        ),
    )


@pytest.fixture(scope="session")
def real_resolution(real_inputs: dict) -> dict:
    return _resolve(real_inputs, real_inputs["rows"])


def _expected_existing_items() -> dict[tuple[int, int], int]:
    expected: dict[tuple[int, int], int] = {}
    for row, report_norm_id in enumerate(
        (
            4302,
            4310,
            4311,
            4312,
            4344,
            4326,
            4313,
            4346,
            6035,
            4315,
            4348,
            4349,
            5322,
            5323,
            5324,
            4316,
            4350,
            6036,
            4317,
            4334,
            4307,
            4328,
            4367,
            4368,
            4330,
            4371,
            4372,
            4327,
            4356,
            4357,
            4335,
            4366,
            4358,
            4375,
        ),
        start=1,
    ):
        expected[(5, row)] = report_norm_id
    expected.update(
        {
            (6, 2): 4318,
            (6, 3): 6037,
            (6, 4): 4319,
            (6, 5): 4359,
            (6, 6): 4360,
            (6, 7): 4320,
            (6, 8): 4321,
            (6, 9): 4322,
            (6, 10): 4323,
            (6, 11): 4324,
            (6, 12): 4361,
            (6, 13): 4336,
            (6, 14): 4362,
            (6, 15): 4304,
            (6, 18): 4364,
            (6, 19): 4337,
            (6, 20): 4338,
            (6, 21): 4365,
            (6, 22): 4343,
            (6, 23): 5699,
            (6, 24): 5712,
            (6, 25): 4305,
        }
    )
    expected.update({(7, row): 6038 + row for row in range(1, 16)})
    expected[(7, 16)] = 6055
    for row, report_norm_id in enumerate(
        (
            4399,
            4396,
            4385,
            4397,
            4398,
            4386,
            4387,
            4388,
            4389,
            4394,
            4395,
            4390,
            4393,
            5713,
            4391,
            4376,
            4392,
            4377,
            4383,
            4384,
            4382,
            4378,
            4379,
            4380,
            4381,
        ),
        start=1,
    ):
        expected[(8, row)] = report_norm_id
    for row, report_norm_id in enumerate(
        (
            4104,
            4123,
            4124,
            4125,
            4126,
            4154,
            4127,
            4122,
            4128,
            4109,
            4107,
            4129,
            4130,
            4131,
            6054,
            4133,
            4134,
            4108,
            4135,
            4136,
            4137,
            4138,
            4139,
            4140,
            4141,
            4110,
        ),
        start=1,
    ):
        if report_norm_id is not None:
            expected[(9, row)] = report_norm_id
    for row, report_norm_id in enumerate((4105, 4118, 4119, 4147, 4111, 4114, 4115, 4116), start=1):
        expected[(10, row)] = report_norm_id
    return expected


def test_real_vpb_rows_have_exhaustive_source_driven_dispositions(real_resolution: dict):
    result = real_resolution
    summary = result["summary"]
    assert summary["visible_source_items"] == 134
    assert summary["mapped_to_existing_canonical_items"] == 131
    assert summary["new_schema_item_proposals"] == 0
    assert summary["ambiguous"] == 0
    assert summary["unresolved"] == 0
    assert summary["structural"] == 3
    assert summary["source_items_successfully_accounted_for"] == 134
    assert summary["universal_schema_counts"] == {
        "CDKT": 99,
        "KQKD": 25,
        "LCTT": 110,
        "TM": 1701,
    }

    dispositions = {
        (item["page"], item["page_row_order"]): item for item in result["source_dispositions"]
    }
    assert {
        key: item["selected_report_norm_id"]
        for key, item in dispositions.items()
        if item["disposition"] == "EXISTING_ITEM"
    } == _expected_existing_items()
    assert not {
        key for key, item in dispositions.items() if item["disposition"] == "NEW_ITEM_PROPOSAL"
    }
    assert {key for key, item in dispositions.items() if item["disposition"] == "STRUCTURAL"} == {
        (6, 1),
        (6, 16),
        (6, 17),
    }
    assert not {key for key, item in dispositions.items() if item["disposition"] == "UNRESOLVED"}
    repeated_detail = dispositions[(5, 11)]
    assert repeated_detail["selected_report_norm_id"] == 4348
    assert repeated_detail["match_basis"] == (
        "REPEATED_PARENT_DETAIL_WITH_COMPLETE_HIERARCHY_AND_EQUATION"
    )


def test_real_vpb_user_resolved_aliases_and_terminal_total_have_audited_receipts(
    real_resolution: dict,
):
    result = real_resolution
    assert result["new_item_proposals"] == []
    assert result["alias_proposals"] == []
    dispositions = {
        (item["page"], item["page_row_order"]): item for item in result["source_dispositions"]
    }
    assert dispositions[(6, 4)]["selected_report_norm_id"] == 4319
    assert dispositions[(6, 6)]["selected_report_norm_id"] == 4360
    assert dispositions[(9, 20)]["selected_report_norm_id"] == 4136
    terminal_total = dispositions[(7, 16)]
    assert terminal_total["selected_report_norm_id"] == 6055
    assert terminal_total["match_basis"] == native._AUDITED_TERMINAL_AGGREGATE_MATCH_BASIS
    receipt = terminal_total["aggregate_match_receipt"]
    assert receipt["selection_status"] == "ACCEPTED_EXACT_EVERY_AXIS"
    assert receipt["equation_used_for_target_selection"] is False
    assert receipt["equation_used_as_acceptance_gate"] is True
    assert receipt["exact_tolerance_source_units"] == 0
    assert receipt["topology"]["physical_table_id"] == (
        "native-614be8877c21ef18-cdkt-off-balance-sheet-page-0007"
    )
    assert receipt["topology"]["direct_child_report_norm_ids"] == [6039, 6050]
    evidence = [result["equations"][index] for index in terminal_total["equation_evidence_indexes"]]
    assert len(evidence) == 1
    assert evidence[0]["equation_type"] == "AUDITED_FORMULA_TERMINAL_AGGREGATE_EXACT_SUM"
    assert evidence[0]["target_report_norm_id"] == 6055
    assert evidence[0]["status"] == "PASS"


def test_terminal_aggregate_exact_equation_is_a_veto_only_and_preserves_children(
    real_inputs: dict,
) -> None:
    payload = copy.deepcopy(real_inputs["rows"])
    terminal = _row(payload, 7, 16)
    terminal["cells"][0]["value"] = str(int(terminal["cells"][0]["value"]) + 1)
    result = _resolve(real_inputs, payload)
    dispositions = {
        (item["page"], item["page_row_order"]): item for item in result["source_dispositions"]
    }
    rejected = dispositions[(7, 16)]
    assert rejected["disposition"] == "UNRESOLVED"
    assert rejected["aggregate_match_receipt"]["selection_status"] == (
        "VETOED_NOT_EXACT_EVERY_AXIS"
    )
    assert rejected["aggregate_match_receipt"]["equation_status"] == (
        "PASS_WITHIN_ONE_SOURCE_UNIT_ROUNDING"
    )
    assert rejected["aggregate_match_receipt"]["equation_axes"][0]["residual"] == "1"
    assert dispositions[(7, 1)]["selected_report_norm_id"] == 6039
    assert dispositions[(7, 12)]["selected_report_norm_id"] == 6050
    assert not any(
        conflict["conflict_type"] == "COMPLETE_STRUCTURE_EQUATION_CONFLICT"
        and rejected["row_id"] in conflict["affected_row_ids"]
        for conflict in result["conflicts"]
    )


def test_terminal_aggregate_is_revoked_when_a_frozen_dependency_is_demoted(
    real_inputs: dict,
) -> None:
    payload = copy.deepcopy(real_inputs["rows"])
    branch_total = _row(payload, 7, 3)
    branch_total["cells"][0]["value"] = str(int(branch_total["cells"][0]["value"]) + 2)
    result = _resolve(real_inputs, payload)
    dispositions = {
        (item["page"], item["page_row_order"]): item for item in result["source_dispositions"]
    }
    assert dispositions[(7, 3)]["disposition"] == "AMBIGUOUS"
    terminal_record = dispositions[(7, 16)]
    assert terminal_record["disposition"] == "UNRESOLVED"
    assert terminal_record["aggregate_match_receipt"]["selection_status"] == (
        "VETOED_DEPENDENCY_MAPPING_DEMOTED"
    )
    assert terminal_record["aggregate_match_receipt"]["dependency_validation_status"] == (
        "FAIL_FROZEN_VALUE_INDEPENDENT_DESCENDANT_NOT_RETAINED"
    )


@pytest.mark.parametrize(
    "mutation",
    ["LABELED", "INCOMPLETE_CHILD", "AXIS_MISMATCH", "DESCENDANT_AXIS_MISMATCH"],
)
def test_terminal_aggregate_requires_unlabeled_complete_same_axis_topology(
    real_inputs: dict,
    mutation: str,
) -> None:
    payload = copy.deepcopy(real_inputs["rows"])
    terminal = _row(payload, 7, 16)
    if mutation == "LABELED":
        terminal["raw_label"] = "Tổng cộng không được ủy quyền"
        terminal["normalized_label"] = terminal["raw_label"]
    elif mutation == "INCOMPLETE_CHILD":
        component = _row(payload, 7, 12)
        component["raw_label"] = "Khoản mục không khớp"
        component["normalized_label"] = component["raw_label"]
    elif mutation == "AXIS_MISMATCH":
        terminal["cells"][0]["axis_id"] = "different-axis"
    else:
        _row(payload, 7, 4)["cells"][0]["axis_id"] = "different-descendant-axis"
    result = _resolve(real_inputs, payload)
    record = next(
        item
        for item in result["source_dispositions"]
        if item["page"] == 7 and item["page_row_order"] == 16
    )
    assert record["selected_report_norm_id"] is None
    assert record["match_basis"] is None


def test_terminal_aggregate_contiguity_uses_unfiltered_global_block_order(
    real_inputs: dict,
) -> None:
    payload = copy.deepcopy(real_inputs["rows"])
    page = _page(payload, 7)
    terminal = _row(payload, 7, 16)
    terminal["row_id"] = terminal["row_id"].rsplit(":row-", 1)[0] + ":row-0017"
    terminal["provenance"]["row_id"] = terminal["row_id"]
    for cell in terminal["cells"]:
        cell["provenance"]["row_id"] = terminal["row_id"]
    foreign = copy.deepcopy(terminal)
    foreign["row_id"] = foreign["row_id"].rsplit(":row-", 1)[0] + ":row-0016"
    foreign["raw_label"] = "Dòng vật lý xen giữa"
    foreign["normalized_label"] = foreign["raw_label"]
    foreign["provenance"]["row_id"] = foreign["row_id"]
    foreign["provenance"]["table_id"] = "foreign-physical-table"
    for cell in foreign["cells"]:
        cell["provenance"]["row_id"] = foreign["row_id"]
        cell["provenance"]["table_id"] = "foreign-physical-table"
    page["rows"].append(foreign)
    page["reconstructed_row_count"] += 1
    result = _resolve(real_inputs, payload)
    terminal_record = next(
        item for item in result["source_dispositions"] if item["row_id"] == terminal["row_id"]
    )
    assert terminal_record["selected_report_norm_id"] is None
    assert terminal_record["aggregate_match_receipt"] is None


def test_terminal_aggregate_is_independent_of_unrelated_equation_inference(
    real_inputs: dict,
) -> None:
    payload = copy.deepcopy(real_inputs["rows"])
    repeated_parent = _row(payload, 5, 10)
    repeated_parent["cells"][0]["value"] = str(int(repeated_parent["cells"][0]["value"]) + 7)
    result = _resolve(real_inputs, payload)
    terminal = next(
        item
        for item in result["source_dispositions"]
        if item["page"] == 7 and item["page_row_order"] == 16
    )
    assert terminal["selected_report_norm_id"] == 6055
    assert terminal["match_basis"] == native._AUDITED_TERMINAL_AGGREGATE_MATCH_BASIS


def test_terminal_aggregate_rejects_value_derived_descendants_and_multiple_roots(
    real_inputs: dict,
    real_resolution: dict,
) -> None:
    rows = native._source_rows(real_inputs["rows"])
    dispositions = {
        record["row_id"]: record
        for record in real_resolution["source_dispositions"]
        if record["disposition"] == "EXISTING_ITEM" and record["selected_report_norm_id"] != 6055
    }
    selected = {
        row_id: native._Candidate(
            report_norm_id=record["selected_report_norm_id"],
            match_basis=record["match_basis"],
            matched_label=record["matched_schema_label"],
            alias_authority_type=record["alias_authority_type"],
            alias_authority_evidence_sha256=record["alias_authority_evidence_sha256"],
        )
        for row_id, record in dispositions.items()
    }
    descendant = next(row for row in rows if row.row["page"] == 7 and row.page_order == 2)
    selected[descendant.row_id] = native.replace(
        selected[descendant.row_id],
        match_basis="REPEATED_PARENT_DETAIL_WITH_COMPLETE_HIERARCHY_AND_EQUATION",
    )
    schema_by_id = {item.schema_id: item for item in real_inputs["items"]}
    formula = next(
        formula for formula in real_inputs["audited_formulas"] if formula.schema_id == 6055
    )
    promotions, receipts, _equations, ambiguities = native._promote_audited_terminal_aggregate(
        rows,
        selected,
        schema_by_id,
        [formula],
        native._observed_blocks(real_inputs["rows"]),
    )
    assert promotions == {}
    assert receipts == {}
    assert ambiguities == {}

    selected[descendant.row_id] = native.replace(
        selected[descendant.row_id], match_basis="CANONICAL_RETRIEVAL_KEY_EXACT"
    )
    duplicate_id = 7000
    duplicate = native.replace(
        schema_by_id[6055],
        schema_id=duplicate_id,
        canonical_name="Synthetic duplicate aggregate",
        normalized_name="synthetic duplicate aggregate",
        display_order=99,
    )
    schema_with_duplicate = {**schema_by_id, duplicate_id: duplicate}
    duplicate_formula = native.replace(formula, schema_id=duplicate_id)
    promotions, receipts, _equations, ambiguities = native._promote_audited_terminal_aggregate(
        rows,
        selected,
        schema_with_duplicate,
        [formula, duplicate_formula],
        native._observed_blocks(real_inputs["rows"]),
    )
    terminal_row_id = _row(real_inputs["rows"], 7, 16)["row_id"]
    assert promotions == {}
    assert set(ambiguities[terminal_row_id]) == {6055, duplicate_id}
    assert receipts[terminal_row_id]["selection_status"] == (
        "AMBIGUOUS_MULTIPLE_PRE_VALUE_TOPOLOGY_CANDIDATES"
    )
    assert receipts[terminal_row_id]["equation_used_for_target_selection"] is False

    one_component = native.replace(formula, component_schema_ids=(6039,))
    promotions, receipts, _equations, ambiguities = native._promote_audited_terminal_aggregate(
        rows,
        selected,
        schema_by_id,
        [one_component],
        native._observed_blocks(real_inputs["rows"]),
    )
    assert promotions == receipts == ambiguities == {}


def test_real_vpb_role_b_schema_coverage_is_universal_and_scope_honest(
    real_resolution: dict,
):
    result = real_resolution
    assert len(result["schema_dispositions"]) == 1935
    assert result["mandatory_search"]["status"] == "PASS"
    assert result["mandatory_search"]["evaluation_scope"] == ("ROLE_B_ONLY_NO_ROLE_A_OUTPUT_LOADED")
    by_id = {item["report_norm_id"]: item for item in result["schema_dispositions"]}
    assert by_id[6038]["terminal_outcome"] == "BLANK"
    assert by_id[6038]["source_row_id"] is None
    assert by_id[6038]["observation_basis"] == "OBSERVED_STRUCTURAL_SCOPE_ROOT"
    assert by_id[6038]["source_scope_evidence"]["presentation_scope"] == ("OFF_BALANCE_SHEET")
    assert (
        "OFF_BALANCE_SCOPE"
        in by_id[6038]["source_scope_evidence"]["independent_signal_groups_by_page"]["7"]
    )
    assert by_id[6039]["terminal_outcome"] == "OBSERVED_VALUE"
    assert by_id[6055]["terminal_outcome"] == "OBSERVED_VALUE"
    assert by_id[6056]["terminal_outcome"] == "UNRESOLVED"
    assert by_id[6056]["observation_basis"] == "UNKNOWN_DOCUMENT_REPORTING_SCOPE"
    assert by_id[4155]["terminal_outcome"] == "NOT_APPLICABLE"
    assert by_id[560]["terminal_outcome"] == "UNRESOLVED"
    assert result["lctt_method"]["method"] == "DIRECT"
    assert result["lctt_method"]["opposite_branch_not_applicable_applied"] is True


def test_all_reconstructed_rows_include_explicit_outside_span_disposition(real_inputs: dict):
    payload = copy.deepcopy(real_inputs["rows"])
    page = _page(payload, 6)
    outside = copy.deepcopy(_row(payload, 6, 1))
    outside["row_id"] = outside["row_id"].rsplit(":row-", 1)[0] + ":row-0026"
    outside["raw_label"] = "Dòng ngoài vùng bảng cần kiểm tra"
    outside["normalized_label"] = outside["raw_label"]
    outside["row_type"] = "SECTION_HEADER"
    outside["cells"] = []
    outside["within_financial_table_span"] = False
    outside["provenance"]["row_id"] = outside["row_id"]
    page["outside_financial_table_span_rows"].append(outside)
    page["reconstructed_row_count"] += 1

    result = _resolve(real_inputs, payload)
    disposition = next(
        item for item in result["source_dispositions"] if item["row_id"] == outside["row_id"]
    )
    assert disposition["disposition"] == "UNRESOLVED"
    assert disposition["within_financial_table_span"] is False
    assert disposition["candidate_report_norm_ids"] == []
    assert result["summary"]["visible_source_items"] == 135
    assert result["summary"]["outside_financial_table_span_source_items"] == 1


def test_unique_label_only_accounting_parent_is_schema_gap_not_structural(real_inputs: dict):
    payload = copy.deepcopy(real_inputs["rows"])
    parent = _row(payload, 6, 1)
    child = _row(payload, 6, 2)
    child["indentation"] = float(parent["indentation"]) + 12
    result = _resolve(real_inputs, payload)
    disposition = next(
        item
        for item in result["source_dispositions"]
        if item["page"] == 6 and item["page_row_order"] == 1
    )
    assert disposition["disposition"] == "NEW_ITEM_PROPOSAL"
    assert any(
        proposal["source_evidence"]["row_id"] == disposition["row_id"]
        for proposal in result["new_item_proposals"]
    )


def test_scope_exhaustiveness_requires_reciprocal_cross_scope_chain(real_inputs: dict):
    payload = copy.deepcopy(real_inputs["rows"])
    _page(payload, 6)["discovery_contract"]["continuation_to_page"] = None
    blocks = native._observed_blocks(payload)
    assert blocks[("CDKT", "MAIN_STATEMENT")][0].exhaustive is False
    assert blocks[("CDKT", "OFF_BALANCE_SHEET")][0].exhaustive is False


def test_bounded_continuation_is_valid_but_incomplete_lctt_chain_is_not(
    real_inputs: dict, real_resolution: dict
):
    bounded = copy.deepcopy(real_inputs["rows"])
    contract = _page(bounded, 10)["discovery_contract"]
    contract.update(
        {
            "locally_accepted": False,
            "inferred_from_page": 9,
            "inference_direction": "FORWARD_FROM_PREVIOUS",
            "inference_checks": [
                "ACCOUNTING_ROWS",
                "NUMERIC_GEOMETRY",
                "SHARED_NUMERIC_AXES",
                "SHARED_PERIOD_AXIS",
                "SHARED_UNIT",
            ],
        }
    )
    assert native._observed_blocks(bounded)[("LCTT", "MAIN_STATEMENT")][0].exhaustive

    incomplete = copy.deepcopy(real_inputs["rows"])
    _page(incomplete, 9)["discovery_contract"]["continuation_to_page"] = None
    result = _resolve(real_inputs, incomplete)
    baseline_target = next(
        record["report_norm_id"]
        for record in real_resolution["schema_dispositions"]
        if record["statement"] == "LCTT" and record["terminal_outcome"] == "NOT_OBSERVED"
    )
    by_id = {record["report_norm_id"]: record for record in result["schema_dispositions"]}
    assert by_id[baseline_target]["terminal_outcome"] == "UNRESOLVED"
    assert by_id[baseline_target]["block_exhaustive"] is False


def test_main_only_cdkt_does_not_imply_off_balance_absence(real_inputs: dict):
    payload = copy.deepcopy(real_inputs["rows"])
    payload["pages"] = [page for page in payload["pages"] if page["page"] != 7]
    _page(payload, 6)["discovery_contract"]["continuation_to_page"] = None
    result = _resolve(real_inputs, payload)
    by_id = {record["report_norm_id"]: record for record in result["schema_dispositions"]}
    assert by_id[6039]["terminal_outcome"] == "UNRESOLVED"
    assert by_id[6039]["source_statement_scope"] is None
    assert by_id[6038]["terminal_outcome"] == "UNRESOLVED"


def test_ambiguous_source_candidate_propagates_without_schema_ownership(
    real_inputs: dict, real_resolution: dict
):
    rows = native._source_rows(real_inputs["rows"])
    by_row_id = {row.row_id: row for row in rows}
    mapped = {
        int(record["selected_report_norm_id"]): by_row_id[record["row_id"]]
        for record in real_resolution["source_dispositions"]
        if record["disposition"] == "EXISTING_ITEM"
    }
    candidate_row = mapped.pop(6039)
    lctt_rows = [
        row.label
        for row in rows
        if row.statement_type == "LCTT" and row.within_financial_table_span
    ]
    method = native.classify_cash_flow_method(lctt_rows, real_inputs["rules"])
    records = native._schema_disposition_records(
        row_payload=real_inputs["rows"],
        rows=rows,
        schema_items=real_inputs["items"],
        mapped_row_by_id=mapped,
        ambiguous_candidate_rows={6039: [candidate_row.row_id]},
        lctt_method=method,
    )
    record = next(item for item in records if item["report_norm_id"] == 6039)
    assert record["terminal_outcome"] == "AMBIGUOUS"
    assert record["source_row_id"] is None
    assert record["candidate_source_row_ids"] == [candidate_row.row_id]


def test_mapped_schema_owner_precedes_an_additional_ambiguous_candidate(
    real_inputs: dict, real_resolution: dict
):
    rows = native._source_rows(real_inputs["rows"])
    by_row_id = {row.row_id: row for row in rows}
    mapped = {
        int(record["selected_report_norm_id"]): by_row_id[record["row_id"]]
        for record in real_resolution["source_dispositions"]
        if record["disposition"] == "EXISTING_ITEM"
    }
    owner = mapped[6039]
    additional_candidate = next(row for row in rows if row.row_id != owner.row_id)
    method = native.classify_cash_flow_method(
        [
            row.label
            for row in rows
            if row.statement_type == "LCTT" and row.within_financial_table_span
        ],
        real_inputs["rules"],
    )
    records = native._schema_disposition_records(
        row_payload=real_inputs["rows"],
        rows=rows,
        schema_items=real_inputs["items"],
        mapped_row_by_id=mapped,
        ambiguous_candidate_rows={6039: [additional_candidate.row_id]},
        lctt_method=method,
    )
    record = next(item for item in records if item["report_norm_id"] == 6039)
    assert record["terminal_outcome"] in {"OBSERVED_VALUE", "OBSERVED_ZERO", "DASH"}
    assert record["source_row_id"] == owner.row_id
    assert record["observation_basis"] == "SOURCE_ROW"
    assert record["candidate_source_row_ids"] == [additional_candidate.row_id]


def test_source_abbreviation_expansion_has_an_explicit_match_receipt(real_inputs: dict):
    schema_by_id = {item.schema_id: item for item in real_inputs["items"]}
    row = native._SourceRow(
        row={
            "row_id": "synthetic-cdkt:row-0001",
            "page": 1,
            "raw_label": "TSCĐ",
            "normalized_label": "TSCĐ",
            "indentation": 0.0,
            "cells": [],
        },
        page_record={},
        order=1,
        page_order=1,
        statement_type="CDKT",
        scope="MAIN_STATEMENT",
        within_financial_table_span=True,
    )
    resolution = native._resolve_monotone_exact_path(
        [row],
        real_inputs["projections"]["CDKT"],
        schema_by_id,
        lctt_method=None,
        accepted_aliases=real_inputs["accepted_aliases"],
    )
    candidate = resolution.selected[row.row_id]
    assert candidate.report_norm_id == 4307
    assert candidate.matched_label == "Tài sản cố định"
    assert candidate.match_basis == "ACCEPTED_ACCOUNTING_ABBREVIATION_NORMALIZATION"


def test_only_typed_accepted_aliases_enter_candidate_authority(real_inputs: dict):
    by_id = {item.schema_id: item for item in real_inputs["items"]}
    _, cdkt = native._candidate_index(
        real_inputs["projections"]["CDKT"],
        by_id,
        lctt_method=None,
        accepted_aliases=real_inputs["accepted_aliases"],
    )
    loan_ids = {
        candidate.report_norm_id for candidate in cdkt[native.retrieval_key("Cho vay khách hàng")]
    }
    assert 4315 in loan_ids
    assert 4348 not in loan_ids

    _, tm = native._candidate_index(
        real_inputs["projections"]["TM"],
        by_id,
        lctt_method=None,
        accepted_aliases=real_inputs["accepted_aliases"],
    )
    untyped_ids = {
        candidate.report_norm_id
        for candidate in tm.get(native.retrieval_key("Khai thác nợ Quản lý tài sản"), ())
    }
    assert 5828 not in untyped_ids

    _, kqkd = native._candidate_index(
        real_inputs["projections"]["KQKD"],
        by_id,
        lctt_method=None,
        accepted_aliases=real_inputs["accepted_aliases"],
    )
    corrected = next(
        candidate
        for candidate in kqkd[native.retrieval_key("Thuế Thu nhập doanh nghiệp phải nộp")]
        if candidate.report_norm_id == 4382
    )
    assert corrected.alias_authority_type == "AUDITED_SCHEMA_ALIAS"
    assert corrected.alias_authority_evidence_sha256


def test_alias_receipt_must_join_exact_typed_authority(real_inputs: dict, real_resolution: dict):
    record = next(
        item
        for item in real_resolution["source_dispositions"]
        if item["match_basis"] == "ACCEPTED_STRUCTURAL_ALIAS_RETRIEVAL_KEY_EXACT"
    )
    source_row = next(
        row for row in native._source_rows(real_inputs["rows"]) if row.row_id == record["row_id"]
    )
    item = next(
        item for item in real_inputs["items"] if item.schema_id == record["selected_report_norm_id"]
    )
    index = native._accepted_alias_index(real_inputs["accepted_aliases"])
    native._validate_mapping_alias_authority(record, source_row, item, index)
    mutated = {**record, "alias_authority_evidence_sha256": "0" * 64}
    with pytest.raises(native.NativeCanonicalMappingError, match="typed evidence"):
        native._validate_mapping_alias_authority(mutated, source_row, item, index)


def test_lctt_branch_and_cdkt_scope_filters_fail_closed(real_inputs: dict):
    by_id = {item.schema_id: item for item in real_inputs["items"]}
    unproven = native.CashFlowEvidence(
        native.CashFlowMethod.DIRECT,
        None,
        (1, 2),
        "synthetic unproven method",
        False,
    )
    nodes, _ = native._candidate_index(
        real_inputs["projections"]["LCTT"],
        by_id,
        lctt_method=unproven,
        accepted_aliases=real_inputs["accepted_aliases"],
    )
    assert {by_id[node.report_norm_id].cash_flow_branch for node in nodes} == {
        "DIRECT",
        "INDIRECT",
    }

    items = copy.deepcopy(real_inputs["items"])
    copied_by_id = {item.schema_id: item for item in items}
    copied_by_id[6039].canonical_name = copied_by_id[4315].canonical_name
    copied_by_id[6039].normalized_name = copied_by_id[4315].normalized_name
    projection = build_schema_projection_v2(items, "CDKT")
    source = next(
        row
        for row in native._source_rows(real_inputs["rows"])
        if row.row["page"] == 5 and row.page_order == 10
    )
    resolution = native._resolve_monotone_exact_path(
        [source],
        projection,
        copied_by_id,
        lctt_method=None,
        accepted_aliases=(),
    )
    assert {candidate.report_norm_id for candidate in resolution.all_candidates[source.row_id]} == {
        4315
    }


def test_q078_shared_legacy_label_is_branch_gated_before_monotone_selection(
    real_inputs: dict,
) -> None:
    schema_by_id = {item.schema_id: item for item in real_inputs["items"]}

    def source_row(order: int, label: str) -> native._SourceRow:
        return native._SourceRow(
            row={
                "row_id": f"synthetic-lctt:row-{order:04d}",
                "page": 1,
                "raw_label": label,
                "normalized_label": label,
                "indentation": 0.0,
                "cells": [],
            },
            page_record={},
            order=order,
            page_order=order,
            statement_type="LCTT",
            scope="MAIN_STATEMENT",
            within_financial_table_span=True,
        )

    shared = "Tăng, giảm các khoản tiền gửi và vay các TCTD"
    direct = native.CashFlowEvidence(
        native.CashFlowMethod.DIRECT,
        None,
        (1, 2),
        "synthetic proven direct",
        True,
    )
    indirect = native.CashFlowEvidence(
        native.CashFlowMethod.INDIRECT,
        (1, 2),
        None,
        "synthetic proven indirect",
        True,
    )
    for method, expected_id in ((direct, 4136), (indirect, 4179)):
        row = source_row(1, shared)
        resolution = native._resolve_monotone_exact_path(
            [row],
            real_inputs["projections"]["LCTT"],
            schema_by_id,
            lctt_method=method,
            accepted_aliases=real_inputs["accepted_aliases"],
        )
        assert resolution.selected[row.row_id].report_norm_id == expected_id
    legacy_direct = source_row(1, "Tăng/(Giảm) tiền gửi, tiền vay các TCTD khác")
    legacy_resolution = native._resolve_monotone_exact_path(
        [legacy_direct],
        real_inputs["projections"]["LCTT"],
        schema_by_id,
        lctt_method=direct,
        accepted_aliases=real_inputs["accepted_aliases"],
    )
    assert legacy_resolution.selected[legacy_direct.row_id].report_norm_id == 4136

    unknown = native.CashFlowEvidence(
        native.CashFlowMethod.UNKNOWN,
        None,
        None,
        "synthetic conflicting method",
        False,
    )
    rows = [
        source_row(1, schema_by_id[6054].canonical_name),
        source_row(2, shared),
        source_row(3, schema_by_id[4138].canonical_name),
    ]
    resolution = native._resolve_monotone_exact_path(
        rows,
        real_inputs["projections"]["LCTT"],
        schema_by_id,
        lctt_method=unknown,
        accepted_aliases=real_inputs["accepted_aliases"],
    )
    assert resolution.selected[rows[0].row_id].report_norm_id == 6054
    assert resolution.selected[rows[2].row_id].report_norm_id == 4138
    assert rows[1].row_id not in resolution.selected
    assert set(resolution.ambiguous[rows[1].row_id]) == {4136, 4179}


@pytest.mark.parametrize(
    ("label", "expected_id"),
    [
        ("Vay các TCTD khác", 4360),
        ("Tiền gửi và vay các TCTD khác", 4319),
    ],
)
def test_q074_q077_old_narrow_labels_remain_typed_exact_aliases(
    real_inputs: dict,
    label: str,
    expected_id: int,
) -> None:
    schema_by_id = {item.schema_id: item for item in real_inputs["items"]}
    row = native._SourceRow(
        row={
            "row_id": "synthetic-cdkt:row-0001",
            "page": 1,
            "raw_label": label,
            "normalized_label": label,
            "indentation": 0.0,
            "cells": [],
        },
        page_record={},
        order=1,
        page_order=1,
        statement_type="CDKT",
        scope="MAIN_STATEMENT",
        within_financial_table_span=True,
    )
    resolution = native._resolve_monotone_exact_path(
        [row],
        real_inputs["projections"]["CDKT"],
        schema_by_id,
        lctt_method=None,
        accepted_aliases=real_inputs["accepted_aliases"],
    )
    candidate = resolution.selected[row.row_id]
    assert candidate.report_norm_id == expected_id
    assert candidate.match_basis == "ACCEPTED_STRUCTURAL_ALIAS_RETRIEVAL_KEY_EXACT"
    assert candidate.alias_authority_type == "AUDITED_SCHEMA_ALIAS"


def test_hierarchy_and_equation_conflicts_are_local_not_document_fatal(
    real_inputs: dict, real_resolution: dict
):
    hierarchy_payload = copy.deepcopy(real_inputs["rows"])
    _row(hierarchy_payload, 5, 4)["indentation"] = (
        float(_row(hierarchy_payload, 5, 3)["indentation"]) + 12
    )
    hierarchy_result = _resolve(real_inputs, hierarchy_payload)
    hierarchy_dispositions = {
        (record["page"], record["page_row_order"]): record
        for record in hierarchy_result["source_dispositions"]
    }
    assert hierarchy_dispositions[(5, 4)]["disposition"] == "AMBIGUOUS"
    assert hierarchy_dispositions[(8, 1)]["disposition"] == "EXISTING_ITEM"
    assert any(
        conflict["conflict_type"] == "OBSERVED_HIERARCHY_CONFLICT"
        for conflict in hierarchy_result["conflicts"]
    )

    equation = next(
        evidence
        for evidence in real_resolution["equations"]
        if evidence["equation_type"] == "MAPPED_PARENT_EQUALS_ALL_MAPPED_SCHEMA_CHILDREN"
        and evidence["status"].startswith("PASS")
        and "page-0005:row-0010" not in evidence["total_row_id"]
    )
    equation_payload = copy.deepcopy(real_inputs["rows"])
    total = next(
        row
        for page in equation_payload["pages"]
        for row in page["rows"]
        if row["row_id"] == equation["total_row_id"]
    )
    total["cells"][0]["value"] = str(int(total["cells"][0]["value"]) + 100)
    equation_result = _resolve(real_inputs, equation_payload)
    by_row_id = {record["row_id"]: record for record in equation_result["source_dispositions"]}
    assert by_row_id[equation["total_row_id"]]["disposition"] == "AMBIGUOUS"
    unaffected = next(
        record
        for record in equation_result["source_dispositions"]
        if record["row_id"] not in set(equation["component_row_ids"]) | {equation["total_row_id"]}
        and record["page"] == 5
    )
    assert unaffected["disposition"] == "EXISTING_ITEM"
    assert any(
        conflict["conflict_type"] == "COMPLETE_STRUCTURE_EQUATION_CONFLICT"
        for conflict in equation_result["conflicts"]
    )


def test_producer_snapshots_survive_future_current_schema_change(
    project_root: Path,
    real_inputs: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    policy_path = project_root / native.POLICY_RELATIVE_PATH
    snapshots = native._producer_snapshots(
        project_root=project_root,
        policy_path=policy_path,
        policy=real_inputs["policy"],
        schema_items=real_inputs["items"],
        accepted_aliases=real_inputs["accepted_aliases"],
        audited_formulas=real_inputs["audited_formulas"],
        coverage=real_inputs["coverage"],
        cash_flow_rules=real_inputs["rules"],
    )
    _mock_current_bytes_as_producer_commit(monkeypatch, project_root, snapshots)
    monkeypatch.setattr(
        native,
        "_load_schema_bundle",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("current schema read")),
    )
    loaded_policy, loaded_items, loaded_aliases, loaded_formulas, loaded_coverage, _ = (
        native._load_producer_snapshots(
            snapshots,
            project_root=project_root,
            producer_commit="a" * 40,
        )
    )
    native._validate_snapshot_schema_identity(
        loaded_policy,
        real_inputs["schema_identity"],
        loaded_items,
        loaded_aliases,
        loaded_formulas,
        loaded_coverage,
    )
    assert len(loaded_items) == 1935
    assert len(loaded_aliases) == 197
    assert len(loaded_formulas) == 69
    assert len(loaded_coverage.targets) == 1935


def test_producer_formula_snapshot_is_commit_bound_and_approved(
    project_root: Path,
    real_inputs: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshots = native._producer_snapshots(
        project_root=project_root,
        policy_path=project_root / native.POLICY_RELATIVE_PATH,
        policy=real_inputs["policy"],
        schema_items=real_inputs["items"],
        accepted_aliases=real_inputs["accepted_aliases"],
        audited_formulas=real_inputs["audited_formulas"],
        coverage=real_inputs["coverage"],
        cash_flow_rules=real_inputs["rules"],
    )
    mutated = copy.deepcopy(snapshots)
    record = mutated["audited_formulas"]["records"][0]
    record["component_schema_ids"] = [record["component_schema_ids"][0]]
    expected_formula_record = {
        "statement_type": record["statement_type"],
        "schema_id": record["schema_id"],
        "operator": record["operator"],
        "component_schema_ids": record["component_schema_ids"],
    }
    record["authority_evidence"]["record_sha256"] = native._record_hash(expected_formula_record)
    record["authority_evidence_sha256"] = native._record_hash(record["authority_evidence"])
    mutated["audited_formulas"]["records_sha256"] = native._record_hash(
        mutated["audited_formulas"]["records"]
    )
    _mock_current_bytes_as_producer_commit(monkeypatch, project_root, mutated)
    with pytest.raises(native.NativeCanonicalMappingError, match="formula authority drifted"):
        native._load_producer_snapshots(
            mutated,
            project_root=project_root,
            producer_commit="a" * 40,
        )

    unapproved = copy.deepcopy(snapshots)
    source_path = unapproved["policy"]["payload"]["schema_authority"]["source_config"]["path"]
    unapproved["policy"]["payload"]["schema_authority"]["source_config"]["sha256"] = "f" * 64
    unapproved["policy"]["canonical_payload_sha256"] = native._record_hash(
        unapproved["policy"]["payload"]
    )
    source_payload = native.yaml.safe_load((project_root / source_path).read_text(encoding="utf-8"))
    source_payload["approved_business_update_audits"] = []

    def identity(_root: Path, _commit: str, raw_path: str) -> dict:
        if raw_path == native.POLICY_RELATIVE_PATH.as_posix():
            digest = unapproved["policy"]["source_sha256"]
        elif raw_path == source_path:
            digest = "f" * 64
        else:
            digest = next(
                formula["authority_evidence"]["audit_sha256"]
                for formula in unapproved["audited_formulas"]["records"]
                if formula["authority_evidence"]["audit_path"] == raw_path
            )
        return {
            "path": raw_path,
            "sha256": digest,
            "size_bytes": (project_root / raw_path).stat().st_size,
        }

    monkeypatch.setattr(native, "_file_identity_at_commit", identity)
    monkeypatch.setattr(
        native,
        "_yaml_payload_at_commit",
        lambda _root, _commit, raw_path: (
            copy.deepcopy(unapproved["policy"]["payload"])
            if raw_path == native.POLICY_RELATIVE_PATH.as_posix()
            else copy.deepcopy(source_payload)
        ),
    )
    with pytest.raises(native.NativeCanonicalMappingError, match="formula authority drifted"):
        native._load_producer_snapshots(
            unapproved,
            project_root=project_root,
            producer_commit="a" * 40,
        )


def test_strict_loader_replays_producer_snapshot_without_current_schema(
    project_root: Path,
    tmp_path: Path,
    real_inputs: dict,
    real_resolution: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    policy_path = project_root / native.POLICY_RELATIVE_PATH
    rows_path = project_root / _ROWS_RELATIVE
    snapshots = native._producer_snapshots(
        project_root=project_root,
        policy_path=policy_path,
        policy=real_inputs["policy"],
        schema_items=real_inputs["items"],
        accepted_aliases=real_inputs["accepted_aliases"],
        audited_formulas=real_inputs["audited_formulas"],
        coverage=real_inputs["coverage"],
        cash_flow_rules=real_inputs["rules"],
    )
    row_payload = real_inputs["rows"]
    runtime = native._runtime_ledger(
        project_root,
        rows_path,
        policy_path,
        project_root / native.ROWS_POLICY_RELATIVE_PATH,
        real_inputs["policy"],
        row_payload,
    )
    payload = {
        "format_version": native._OUTPUT_FORMAT,
        "policy": native._POLICY_NAME,
        "claim_boundary": native._CLAIM_BOUNDARY,
        "status": native._OUTPUT_STATUS,
        "run_id": "strict-snapshot-test",
        "source": copy.deepcopy(row_payload["source"]),
        "native_rows": {
            "path": _ROWS_RELATIVE.as_posix(),
            "sha256": _ROWS_SHA256,
            "size_bytes": rows_path.stat().st_size,
            "format_version": row_payload["format_version"],
            "policy": row_payload["policy"],
            "claim_boundary": row_payload["claim_boundary"],
            "status": row_payload["status"],
            "run_id": row_payload["run_id"],
            "producer_git_commit": row_payload["code"]["commit"],
            "denominator": "ALL_RECONSTRUCTED_SOURCE_ROWS",
        },
        "schema": copy.deepcopy(real_inputs["schema_identity"]),
        "producer_snapshots": snapshots,
        "code": {"commit": "a" * 40, "dirty": False, "implementation": []},
        "authority": {
            "canonical_labels": "CURRENT_UNIVERSAL_SCHEMA_WORKBOOKS",
            "aliases": "CURRENT_TYPED_ACCEPTED_ALIAS_AUTHORITY_ONLY",
            "ordering": "WORKBOOK_DISPLAY_ORDER",
            "hierarchy": "CURRENT_VALIDATED_SCHEMA_GRAPH",
            "source_rows_and_cells": "TRUSTED_REGISTERED_NATIVE_ROWS_SHA256_JOIN",
            "business_formulas": "HASH_BOUND_APPROVED_BUSINESS_UPDATE_AUDIT_RECORDS",
            "historical_values": None,
            "role_a": None,
            "human_review": None,
        },
        "isolation": {
            "prior_answer_artifacts_loaded": False,
            "historical_values_loaded": False,
            "historical_aliases_loaded": False,
            "role_a_outputs_loaded": False,
            "human_review_outputs_loaded": False,
            "bank_identity_used_for_mapping": False,
            "filename_identity_used_for_mapping": False,
            "page_number_rules_used_for_mapping": False,
            "source_row_count_rules_used_for_mapping": False,
            "same_run_alias_proposals_mapping_eligible": False,
            "new_item_proposals_allocate_report_norm_id": False,
        },
        "inputs": {
            "runtime_read_ledger": runtime,
            "runtime_read_ledger_sha256": native.stable_records_hash(
                json.dumps(record, ensure_ascii=False, sort_keys=True) for record in runtime
            ),
        },
        **copy.deepcopy(real_resolution),
    }
    encoded = native._canonical_json_bytes(payload)
    artifact = tmp_path / "mapping.json"
    artifact.write_bytes(encoded)
    monkeypatch.setattr(native, "_implementation_ledger_at_commit", lambda *_args: [])
    monkeypatch.setattr(
        native,
        "_expected_runtime_ledger_at_commit",
        lambda **_kwargs: copy.deepcopy(runtime),
    )
    _mock_current_bytes_as_producer_commit(monkeypatch, project_root, snapshots)
    monkeypatch.setattr(
        native,
        "_load_schema_bundle",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("current schema read")),
    )
    loaded = native.load_registered_native_canonical_mapping(
        artifact,
        project_root=project_root,
        expected_sha256=native.sha256_bytes(encoded),
    )
    assert loaded["summary"]["mapped_to_existing_canonical_items"] == 131

    tampered_receipt = copy.deepcopy(payload)
    aggregate = next(
        record
        for record in tampered_receipt["source_dispositions"]
        if record["selected_report_norm_id"] == 6055
    )
    aggregate["aggregate_match_receipt"]["topology"]["physical_table_id"] = (
        "tampered-physical-table"
    )
    receipt_encoded = native._canonical_json_bytes(tampered_receipt)
    receipt_artifact = tmp_path / "mapping-receipt-tampered.json"
    receipt_artifact.write_bytes(receipt_encoded)
    with pytest.raises(native.NativeCanonicalMappingError, match="topology/formula join"):
        native.load_registered_native_canonical_mapping(
            receipt_artifact,
            project_root=project_root,
            expected_sha256=native.sha256_bytes(receipt_encoded),
        )

    tampered_code = copy.deepcopy(payload)
    tampered_code["code"]["implementation"] = [
        {"path": "src/untrusted.py", "sha256": "f" * 64, "size_bytes": 1}
    ]
    tampered_encoded = native._canonical_json_bytes(tampered_code)
    tampered_artifact = tmp_path / "mapping-code-tampered.json"
    tampered_artifact.write_bytes(tampered_encoded)
    with pytest.raises(native.NativeCanonicalMappingError, match="producer code identity"):
        native.load_registered_native_canonical_mapping(
            tampered_artifact,
            project_root=project_root,
            expected_sha256=native.sha256_bytes(tampered_encoded),
        )


def test_legacy_6054_registered_artifact_strictly_replays_byte_identically(
    project_root: Path,
) -> None:
    artifact = (
        project_root / "output/development/vpb-q1-2026-native-canonical-v1/canonical-mapping.json"
    )
    expected_sha256 = "94d24bdc307101f0024a18e72cd94100fecb937e525dfbca37baa622d7475597"
    assert sha256_file(artifact) == expected_sha256
    loaded = native.load_registered_native_canonical_mapping(
        artifact,
        project_root=project_root,
        expected_sha256=expected_sha256,
    )
    assert loaded["schema"]["revision"] == "UNIVERSAL_BANK_BCTC_SCHEMA@6054"
    assert "audited_formulas" not in loaded["producer_snapshots"]
    assert all(
        "aggregate_match_receipt" not in disposition
        for disposition in loaded["source_dispositions"]
    )
    assert loaded["summary"]["mapped_to_existing_canonical_items"] == 127


def test_embedded_runtime_ledger_requires_exact_inventory_and_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    rows_path = tmp_path / "output/development/rows.json"
    rows_path.parent.mkdir(parents=True)
    rows_path.write_bytes(b"{}\n")
    expected = [
        {
            "kind": "REGISTERED_NATIVE_STATEMENT_ROWS",
            "path": "output/development/rows.json",
            "sha256": native.sha256_bytes(rows_path.read_bytes()),
            "size_bytes": rows_path.stat().st_size,
        },
        {
            "kind": "THIS_POLICY",
            "path": native.POLICY_RELATIVE_PATH.as_posix(),
            "sha256": "a" * 64,
            "size_bytes": 10,
        },
    ]
    expected.sort(key=lambda record: (record["kind"], record["path"]))
    monkeypatch.setattr(
        native,
        "_expected_runtime_ledger_at_commit",
        lambda **_kwargs: copy.deepcopy(expected),
    )

    def envelope(records: list[dict]) -> dict:
        return {
            "runtime_read_ledger": records,
            "runtime_read_ledger_sha256": native.stable_records_hash(
                json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records
            ),
        }

    kwargs = {
        "project_root": tmp_path,
        "producer_commit": "b" * 40,
        "rows_path": rows_path,
        "rows_sha256": expected[0]["sha256"],
        "policy_snapshot": {},
        "row_payload": {},
    }
    native._validate_embedded_runtime_ledger(envelope(copy.deepcopy(expected)), **kwargs)

    mutations = []
    mutations.append(copy.deepcopy(expected[:-1]))
    extra = copy.deepcopy(expected)
    extra.append(
        {
            "kind": "EXTRA_INPUT",
            "path": "config/extra.yaml",
            "sha256": "c" * 64,
            "size_bytes": 1,
        }
    )
    extra.sort(key=lambda record: (record["kind"], record["path"]))
    mutations.append(extra)
    changed_hash = copy.deepcopy(expected)
    changed_hash[0]["sha256"] = "d" * 64
    mutations.append(changed_hash)
    for mutation in mutations:
        with pytest.raises(native.NativeCanonicalMappingError, match="inventory"):
            native._validate_embedded_runtime_ledger(envelope(mutation), **kwargs)


def test_expected_runtime_ledger_is_derived_from_the_producer_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path.resolve()
    rows_path = root / "output/development/rows.json"
    rows_path.parent.mkdir(parents=True)
    rows_path.write_bytes(b"trusted rows\n")
    statement_types = ("CDKT", "KQKD", "LCTT", "TM")
    source_config_path = "config/schemas/sources.yaml"
    hierarchy_config_path = "config/schemas/hierarchy.yaml"
    schema_registry_path = "data/schema-registry.json"
    hierarchy_registry_path = "data/hierarchy-registry.json"
    coverage_config_path = "config/schemas/coverage.yaml"
    coverage_registry_path = "data/coverage-registry.json"
    policy_path = native.POLICY_RELATIVE_PATH.as_posix()

    source_workbooks = {
        statement: f"template/{statement.casefold()}-v2.xlsx" for statement in statement_types
    }
    base_paths = {
        statement: f"template/{statement.casefold()}-base.xlsx" for statement in statement_types
    }
    hierarchy_paths = {
        statement: f"{statement.casefold()}-hierarchy.xlsx" for statement in statement_types
    }
    all_paths = {
        policy_path,
        native.ROWS_POLICY_RELATIVE_PATH.as_posix(),
        source_config_path,
        hierarchy_config_path,
        schema_registry_path,
        hierarchy_registry_path,
        coverage_config_path,
        coverage_registry_path,
        "config/mapping/cash-flow.yaml",
        "data/schema-append.json",
        "data/schema-business-update.json",
        *source_workbooks.values(),
        *base_paths.values(),
        *(f"vst_level/{path}" for path in hierarchy_paths.values()),
    }
    identities = {
        path: {
            "path": path,
            "sha256": native.sha256_bytes(f"producer:{path}".encode()),
            "size_bytes": len(f"producer:{path}".encode()),
        }
        for path in all_paths
    }
    authority = {
        "source_config": {
            "path": source_config_path,
            "sha256": identities[source_config_path]["sha256"],
        },
        "hierarchy_config": {
            "path": hierarchy_config_path,
            "sha256": identities[hierarchy_config_path]["sha256"],
        },
        "schema_registry": {
            "path": schema_registry_path,
            "sha256": identities[schema_registry_path]["sha256"],
        },
        "hierarchy_registry": {
            "path": hierarchy_registry_path,
            "sha256": identities[hierarchy_registry_path]["sha256"],
        },
        "coverage_config": {
            "path": coverage_config_path,
            "sha256": identities[coverage_config_path]["sha256"],
        },
        "coverage_registry": {
            "path": coverage_registry_path,
            "sha256": identities[coverage_registry_path]["sha256"],
        },
    }
    policy_payload = {"schema_authority": authority}
    source_config = {
        "sources": source_workbooks,
        "base_schema": {
            "workbooks": {
                statement: {
                    "path": base_paths[statement],
                    "sha256": identities[base_paths[statement]]["sha256"],
                }
                for statement in statement_types
            }
        },
        "cash_flow_rules": "config/mapping/cash-flow.yaml",
        "approved_append_audits": ["data/schema-append.json"],
        "approved_business_update_audits": ["data/schema-business-update.json"],
    }
    hierarchy_config = {
        "root": "vst_level",
        "sources": {
            statement: {"path": hierarchy_paths[statement]} for statement in statement_types
        },
    }
    yaml_payloads = {
        policy_path: policy_payload,
        source_config_path: source_config,
        hierarchy_config_path: hierarchy_config,
    }

    def committed_identity(_root: Path, _commit: str, raw_path: str) -> dict:
        return copy.deepcopy(identities[raw_path])

    def committed_yaml(_root: Path, _commit: str, raw_path: str) -> dict:
        return copy.deepcopy(yaml_payloads[raw_path])

    monkeypatch.setattr(native, "_file_identity_at_commit", committed_identity)
    monkeypatch.setattr(native, "_yaml_payload_at_commit", committed_yaml)
    upstream = [
        {
            "kind": "SOURCE_PDF",
            "path": "data/source.pdf",
            "sha256": "e" * 64,
            "size_bytes": 123,
        }
    ]
    row_payload = {
        "inputs": {
            "runtime_read_ledger": upstream,
            "runtime_read_ledger_sha256": native.stable_records_hash(
                json.dumps(record, ensure_ascii=False, sort_keys=True) for record in upstream
            ),
        }
    }
    policy_snapshot = {
        "path": policy_path,
        "source_sha256": identities[policy_path]["sha256"],
        "payload": policy_payload,
    }
    records = native._expected_runtime_ledger_at_commit(
        project_root=root,
        producer_commit="f" * 40,
        rows_path=rows_path,
        rows_sha256=native.sha256_bytes(rows_path.read_bytes()),
        policy_snapshot=policy_snapshot,
        row_payload=row_payload,
    )
    kinds = {record["kind"] for record in records}
    assert {
        "REGISTERED_NATIVE_STATEMENT_ROWS",
        "THIS_POLICY",
        "NATIVE_STATEMENT_ROWS_POLICY",
        "SCHEMA_SOURCE_CONFIG",
        "HIERARCHY_CONFIG",
        "SCHEMA_WORKBOOK",
        "BASE_SCHEMA_WORKBOOK",
        "CASH_FLOW_RULES",
        "SCHEMA_APPEND_AUDIT",
        "SCHEMA_BUSINESS_UPDATE_AUDIT",
        "HIERARCHY_WORKBOOK",
        "SCHEMA_REGISTRY",
        "HIERARCHY_REGISTRY",
        "SCHEMA_COVERAGE_CONFIG",
        "SCHEMA_COVERAGE_REGISTRY",
        "UPSTREAM_SOURCE_PDF",
    } <= kinds
    assert records == sorted(records, key=lambda record: (record["kind"], record["path"]))

    identities[schema_registry_path]["sha256"] = "0" * 64
    with pytest.raises(native.NativeCanonicalMappingError, match="policy pin"):
        native._expected_runtime_ledger_at_commit(
            project_root=root,
            producer_commit="f" * 40,
            rows_path=rows_path,
            rows_sha256=native.sha256_bytes(rows_path.read_bytes()),
            policy_snapshot=policy_snapshot,
            row_payload=row_payload,
        )


def test_alias_proposal_is_side_evidence_and_never_same_run_authority():
    policy = {
        "mapping": {
            "alias_proposal_threshold": 0.96,
            "alias_proposal_minimum_margin": 0.10,
            "alias_proposal_maximum_token_symmetric_difference": 1,
        }
    }
    row = native._SourceRow(
        row={
            "row_id": "row-1",
            "raw_label": "Phí dịch vụ khác",
            "normalized_label": "Phí dịch vụ khác",
        },
        page_record={},
        order=1,
        page_order=1,
        statement_type="KQKD",
        scope="MAIN_STATEMENT",
        within_financial_table_span=True,
    )
    proposal = native._alias_proposal(
        row,
        [
            {
                "report_norm_id": 1,
                "canonical_name": "Phí dịch vụ",
                "similarity": 0.98,
                "diagnostic_variant": "Phí dịch vụ",
            },
            {
                "report_norm_id": 2,
                "canonical_name": "Thu nhập",
                "similarity": 0.40,
                "diagnostic_variant": "Thu nhập",
            },
        ],
        policy,
    )
    assert proposal is not None
    assert proposal["mapping_eligible_this_run"] is False
    assert proposal["candidate_report_norm_id"] == 1


def test_cli_has_stable_mapping_defaults_and_forwards_trusted_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    root = tmp_path.resolve()
    output = root / "output/calibration/mapping/result.json"
    arguments = build_parser().parse_args(
        [
            "--project-root",
            str(root),
            "map-native-rows",
            "--rows",
            "output/calibration/rows.json",
            "--rows-sha256",
            "a" * 64,
            "--output",
            output.relative_to(root).as_posix(),
        ]
    )
    assert arguments.policy == native.POLICY_RELATIVE_PATH.as_posix()
    assert arguments.rows_policy == native.ROWS_POLICY_RELATIVE_PATH.as_posix()
    assert arguments.run_id == "registered-native-canonical-mapping-v1"
    calls = []

    def fake_publish(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            path=output,
            sha256="b" * 64,
            size_bytes=1234,
            payload={
                "status": "ACCEPTED_NATIVE_CANONICAL_MAPPING",
                "summary": {
                    "mapped_to_existing_canonical_items": 10,
                    "new_schema_item_proposals": 2,
                    "ambiguous": 1,
                    "unresolved": 1,
                    "structural": 3,
                    "source_items_successfully_accounted_for": 17,
                    "source_item_accounting_denominator": 17,
                },
            },
        )

    monkeypatch.setattr(native, "publish_registered_native_canonical_mapping", fake_publish)
    assert arguments.handler(arguments) == 0
    assert calls == [
        {
            "project_root": root,
            "rows_path": root / "output/calibration/rows.json",
            "rows_sha256": "a" * 64,
            "policy_path": root / native.POLICY_RELATIVE_PATH,
            "rows_policy_path": root / native.ROWS_POLICY_RELATIVE_PATH,
            "run_id": "registered-native-canonical-mapping-v1",
            "output_path": output,
        }
    ]
    stdout = capsys.readouterr().out
    assert "NATIVE_CANONICAL_MAPPING_STATUS=ACCEPTED_NATIVE_CANONICAL_MAPPING" in stdout
    assert "NATIVE_CANONICAL_MAPPING_NEW_ITEM_PROPOSALS=2" in stdout
    assert "NATIVE_CANONICAL_MAPPING_ACCOUNTED=17/17" in stdout
    assert str(root) not in stdout


def test_exclusive_writer_rejects_overwrite_and_rolls_back_after_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    output = tmp_path / "mapping.json"
    native._write_exclusive(output, b"{}\n")
    with pytest.raises(native.NativeCanonicalMappingError, match="overwrite"):
        native._write_exclusive(output, b"{}\n")

    target = tmp_path / "rollback.json"
    real_fsync = native.os.fsync
    calls = 0

    def fail_after_link(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("post-link failure")
        real_fsync(descriptor)

    monkeypatch.setattr(native.os, "fsync", fail_after_link)
    with pytest.raises(OSError, match="post-link"):
        native._write_exclusive(target, b"{}\n")
    assert not target.exists()


def test_publisher_rolls_back_and_fsyncs_after_strict_replay_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = tmp_path.resolve()
    output = root / "output/development/mapping/result.json"
    monkeypatch.setattr(native, "_current_git_state", lambda _root: {"clean": True})
    monkeypatch.setattr(
        native,
        "build_registered_native_canonical_mapping",
        lambda *_args, **_kwargs: {"source": {"dataset_role": "LOGIC_DEVELOPMENT"}},
    )

    def reject_strict_replay(*_args, **_kwargs):
        raise native.NativeCanonicalMappingError("forced strict replay failure")

    monkeypatch.setattr(native, "load_registered_native_canonical_mapping", reject_strict_replay)
    real_fsync = native.os.fsync
    directory_fsync_count = 0

    def track_fsync(descriptor: int) -> None:
        nonlocal directory_fsync_count
        if stat.S_ISDIR(os.fstat(descriptor).st_mode):
            directory_fsync_count += 1
        real_fsync(descriptor)

    monkeypatch.setattr(native.os, "fsync", track_fsync)
    with pytest.raises(native.NativeCanonicalMappingError, match="forced strict replay failure"):
        native.publish_registered_native_canonical_mapping(
            project_root=root,
            rows_path=root / "rows.json",
            rows_sha256="a" * 64,
            policy_path=root / "policy.yaml",
            rows_policy_path=root / "rows-policy.yaml",
            run_id="test-run",
            output_path=output,
        )
    assert not output.exists()
    assert directory_fsync_count >= 2


def test_real_row_artifact_hash_is_fixture_bound(project_root: Path):
    assert sha256_file(project_root / _ROWS_RELATIVE) == _ROWS_SHA256
