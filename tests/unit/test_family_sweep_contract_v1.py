from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

import bctc_ai.evaluation.family_sweep_contract_v1 as sweep
from bctc_ai.evaluation.family_sweep_contract_v1 import (
    BANK_PANEL_V1,
    AuthenticatedFamilySweepTrialV1,
    FamilySweepContractV1Error,
    authenticate_family_sweep_trial_v1,
    build_family_sweep_manifest_v1,
    build_family_sweep_result_v1,
    validate_family_sweep_manifest_v1,
    validate_family_sweep_result_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    local_accounting_family_spec_sha256_v1,
)

SPECS = (LOAN_QUALITY_CLASSIFICATION_SPEC_V1, LOAN_MATURITY_BUCKETS_SPEC_V1)
SHA = "a" * 64
SOURCE_PAGE = "ssv2:page:" + "b" * 64
PANEL_CAPABILITY = object()
PANEL_PAGES = dict(zip(BANK_PANEL_V1, (18, 31, 42, 26, 31, 39, 22, 33), strict=True))
PANEL_SELECTION = {
    "format_version": "LOAN_MATURITY_8BANK_AUTHENTICATED_PANEL_SELECTION_PROJECTION_V1",
    "experiment_id": "E-0044",
    "family_id": "LOAN_MATURITY_BUCKETS",
    "manifest_sha256": "8" * 64,
    "manifest_size_bytes": 1234,
    "panel_state": "BLOCKED_PENDING_COMPLETE_8_SLOT_HYDRATION",
    "bank_order": list(BANK_PANEL_V1),
    "slots": [
        {
            "bank_code": bank,
            "source_pdf_sha256": f"{ordinal + 1:x}" * 64,
            "physical_page": PANEL_PAGES[bank],
        }
        for ordinal, bank in enumerate(BANK_PANEL_V1)
    ],
    "authority": {
        "selection_provenance_only": True,
        "recognition_routing_authority": False,
        "hydration_authority": False,
        "semantic_authority": False,
        "numeric_authority": False,
        "mapping_authority": False,
        "completed_vietocr_run_authority": False,
    },
}
PANEL_SELECTION["projection_id"] = "lm8bpsv1:projection:" + canonical_json_sha256_v1(
    PANEL_SELECTION
)


@pytest.fixture(autouse=True)
def _authenticated_panel_selection_stub(monkeypatch):
    def project(value):
        if value is not PANEL_CAPABILITY:
            raise FamilySweepContractV1Error("not a live panel selection capability")
        return deepcopy(PANEL_SELECTION)

    monkeypatch.setattr(sweep, "_project_panel_selection", project)


def _plans(*, second_acb_trial: bool = False):
    plans = {bank: [] for bank in BANK_PANEL_V1}
    plans["ACB"] = [
        {
            "trial_id": "trial-0001",
            "source_size_bytes": 1000,
            "source_local_page_id": SOURCE_PAGE,
        }
    ]
    if second_acb_trial:
        plans["ACB"].append(
            {
                "trial_id": "trial-0002",
                "source_size_bytes": 1001,
                "source_local_page_id": "ssv2:page:" + "d" * 64,
            }
        )
    plans["MBB"] = [
        {
            "trial_id": "trial-0003",
            "source_size_bytes": 2000,
            "source_local_page_id": "ssv2:page:" + "f" * 64,
        }
    ]
    return plans


def _manifest(*, second_acb_trial: bool = False):
    return build_family_sweep_manifest_v1(
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
        _plans(second_acb_trial=second_acb_trial),
        panel_selection_authority=PANEL_CAPABILITY,
    )


def _not_evaluated_context():
    return {
        "context_id": None,
        "artifact_sha256": None,
        "status": "NOT_EVALUATED",
        "unresolved_reasons": [],
    }


def _not_evaluated_numeric():
    return {
        "verification_id": None,
        "artifact_sha256": None,
        "status": "NOT_EVALUATED",
        "verified_cell_count": 0,
        "unresolved_cell_count": 0,
    }


def _not_evaluated_mapping():
    return {
        "protocol_id": None,
        "verification_id": None,
        "artifact_sha256": None,
        "status": "NOT_EVALUATED",
        "semantic_graph_id": None,
        "schema_candidate_set_id": None,
        "rows": [],
        "near_neighbor_verdicts": [],
    }


def _accepted_receipt(manifest, *, trial_id="trial-0001", bank="ACB"):
    plan = next(
        trial
        for entry in manifest["banks"]
        for trial in entry["trials"]
        if trial["trial_id"] == trial_id
    )
    return {
        "trial_id": trial_id,
        "bank": bank,
        "family_id": manifest["family_id"],
        "family_spec_sha256": manifest["family_spec_sha256"],
        "supplied_family_collision_scope_spec_sha256_by_id": manifest[
            "supplied_family_collision_scope_spec_sha256_by_id"
        ],
        **{
            key: plan[key]
            for key in (
                "source_sha256",
                "source_size_bytes",
                "physical_page",
                "source_local_page_id",
            )
        },
        "source_projection_sha256": "1" * 64,
        "semantic_page_binding_sha256": "2" * 64,
        "observation": {
            "artifact_sha256": "3" * 64,
            "status": "READY_FOR_GRAPH_V2",
            "unresolved_reasons": [],
        },
        "semantic_graph": {
            "graph_id": "slagv2:graph:" + "4" * 64,
            "artifact_sha256": "5" * 64,
            "status": "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE",
            "accepted_counts": {
                "TABLE": 1,
                "LOGICAL_ROW": 4,
                "VALUE_POSITION": 8,
                "AXIS": 2,
                "HIERARCHY": 12,
            },
            "unresolved_reasons": [],
        },
        "schema_candidate": {
            "candidate_set_id": "slascv1:candidate:" + "6" * 64,
            "artifact_sha256": "7" * 64,
            "status": "CANDIDATE_SET_READY",
            "candidate_role_count": 6,
        },
        "statement_context": _not_evaluated_context(),
        "independent_numeric_source_verification": _not_evaluated_numeric(),
        "independent_schema_mapping_verification": _not_evaluated_mapping(),
    }


def _unresolved_receipt(manifest, *, trial_id="trial-0003", bank="MBB"):
    result = _accepted_receipt(manifest, trial_id=trial_id, bank=bank)
    result["observation"] = {
        "artifact_sha256": "8" * 64,
        "status": "UNRESOLVED",
        "unresolved_reasons": ["BRANCH_NOT_RESOLVED_FROM_TRANSFORMER"],
    }
    result["semantic_graph"] = {
        "graph_id": "slagv2:graph:" + "9" * 64,
        "artifact_sha256": "0" * 64,
        "status": "UNRESOLVED",
        "accepted_counts": {
            "TABLE": 0,
            "LOGICAL_ROW": 0,
            "VALUE_POSITION": 0,
            "AXIS": 0,
            "HIERARCHY": 0,
        },
        "unresolved_reasons": ["BRANCH_NOT_RESOLVED_FROM_TRANSFORMER"],
    }
    result["schema_candidate"] = {
        "candidate_set_id": "slascv1:candidate:" + "a" * 64,
        "artifact_sha256": "b" * 64,
        "status": "UNRESOLVED_GRAPH_NOT_ACCEPTED",
        "candidate_role_count": 0,
    }
    return result


def _checks(value="PASS"):
    return {
        "replay_authenticated_source_or_pdf_evidence": value,
        "exact_visible_label_and_candidate_report_norm_id": value,
        "parent_child_sibling_and_workbook_display_order": value,
        "number_sign_period_unit_and_scope": value,
        "applicable_arithmetic_and_accounting_checks": value,
        "near_neighbor_schema_collision_falsifiers": value,
    }


def _verified_mapping(receipt):
    rows = []
    for ordinal, (role, report_norm_id) in enumerate(
        (("SHORT_TERM", 753), ("MEDIUM_TERM", 754), ("LONG_TERM", 755))
    ):
        rows.append(
            {
                "graph_node_id": f"row-{ordinal}",
                "typed_role": role,
                "candidate_report_norm_id": report_norm_id,
                "verified_report_norm_id": report_norm_id,
                "source_only_total": False,
                "verifier_evidence_projection": _checks(),
                "verdict": "VERIFIED_BY_CODEX",
                "unresolved_reasons": [],
            }
        )
    rows.append(
        {
            "graph_node_id": "row-total",
            "typed_role": "TOTAL",
            "candidate_report_norm_id": None,
            "verified_report_norm_id": None,
            "source_only_total": True,
            "verifier_evidence_projection": {
                **_checks(),
                "exact_visible_label_and_candidate_report_norm_id": "NOT_APPLICABLE",
                "parent_child_sibling_and_workbook_display_order": "NOT_APPLICABLE",
                "near_neighbor_schema_collision_falsifiers": "NOT_APPLICABLE",
            },
            "verdict": "VERIFIED_BY_CODEX",
            "unresolved_reasons": [],
        }
    )
    return {
        "protocol_id": "CODEX_MAPPED_ITEM_VERIFICATION_V1",
        "verification_id": "codexmiv1:verification:" + "c" * 64,
        "artifact_sha256": "d" * 64,
        "status": "VERIFIED_BY_CODEX",
        "semantic_graph_id": receipt["semantic_graph"]["graph_id"],
        "schema_candidate_set_id": receipt["schema_candidate"]["candidate_set_id"],
        "rows": rows,
        "near_neighbor_verdicts": [
            {
                "report_norm_id": report_norm_id,
                "status": "UNRESOLVED",
                "disposition": disposition,
                "whole_document_absence_claim": False,
            }
            for report_norm_id, disposition in (
                (5747, "NOT_OBSERVED_IN_BOUND_SOURCE_TABLE"),
                (1944, "SCHEMA_CONTEXT_UNRESOLVED_ORPHAN_MAPPING_INELIGIBLE"),
            )
        ],
    }


def _authenticate(
    monkeypatch, manifest, raw, *, mapped_verification_mutator=None
) -> AuthenticatedFamilySweepTrialV1:
    plan = next(
        trial
        for entry in manifest["banks"]
        for trial in entry["trials"]
        if trial["trial_id"] == raw["trial_id"]
    )
    source = {
        "source_locator": {
            "source_sha256": plan["source_sha256"],
            "source_size_bytes": plan["source_size_bytes"],
            "physical_page": plan["physical_page"],
            "request_sha256": "0" * 64,
        }
    }
    binding = {"test_binding": raw["trial_id"]}
    graph = {
        "graph_id": raw["semantic_graph"]["graph_id"],
        "status": raw["semantic_graph"]["status"],
        "source_local_page_id": plan["source_local_page_id"],
        "source_projection_sha256": canonical_json_sha256_v1(source),
        "semantic_page_binding_sha256": canonical_json_sha256_v1(binding),
        "observation_candidate_sha256": raw["observation"]["artifact_sha256"],
        "family_id": manifest["family_id"],
        "family_spec_sha256": manifest["family_spec_sha256"],
        "supplied_family_collision_scope_spec_sha256_by_id": manifest[
            "supplied_family_collision_scope_spec_sha256_by_id"
        ],
        "unresolved_reasons": deepcopy(raw["semantic_graph"]["unresolved_reasons"]),
        "metrics": {
            "accepted_counts": deepcopy(raw["semantic_graph"]["accepted_counts"]),
        },
        "nodes": (
            [
                {
                    "node_id": node_id,
                    "kind": "LOGICAL_ROW",
                    "attributes": {"row_role": role},
                }
                for node_id, role in (
                    ("row-0", "SHORT_TERM"),
                    ("row-1", "MEDIUM_TERM"),
                    ("row-2", "LONG_TERM"),
                    ("row-total", "TOTAL"),
                )
            ]
            if raw["semantic_graph"]["status"] == "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE"
            else []
        ),
    }
    if graph["nodes"]:
        graph["nodes"].extend(
            {
                "node_id": f"value-{ordinal}-{axis}",
                "kind": "VALUE_POSITION",
                "attributes": {
                    "row_role": role,
                    "axis_index": axis,
                    "raw_text": str((ordinal + 1) * 100 + axis),
                    "normalized_decimal": str((ordinal + 1) * 100 + axis),
                    "state": "OBSERVED_VALUE",
                },
            }
            for ordinal, role in enumerate(("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "TOTAL"))
            for axis in (0, 1)
        )
    candidate = {
        "candidate_set_id": raw["schema_candidate"]["candidate_set_id"],
        "status": raw["schema_candidate"]["status"],
        "metrics": {
            "candidate_role_count": raw["schema_candidate"]["candidate_role_count"],
        },
        "role_candidates": [
            {"typed_role": "OWNER_LABEL", "candidate_report_norm_ids": [716]},
            {"typed_role": "BRANCH_LABEL", "candidate_report_norm_ids": [752]},
            {"typed_role": "SHORT_TERM", "candidate_report_norm_ids": [753]},
            {"typed_role": "MEDIUM_TERM", "candidate_report_norm_ids": [754]},
            {"typed_role": "LONG_TERM", "candidate_report_norm_ids": [755]},
            {"typed_role": "TOTAL", "candidate_report_norm_ids": []},
        ],
    }
    mapping = raw["independent_schema_mapping_verification"]
    context = None
    if raw["statement_context"]["status"] != "NOT_EVALUATED":
        context = {
            "context_id": raw["statement_context"]["context_id"],
            "status": raw["statement_context"]["status"],
            "unresolved_reasons": deepcopy(raw["statement_context"]["unresolved_reasons"]),
        }
    elif mapping["status"] != "NOT_EVALUATED":
        context = {
            "context_id": "sscxtv1:context:" + "e" * 64,
            "status": "RESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT",
            "unresolved_reasons": [],
        }

    monkeypatch.setattr(
        sweep,
        "validate_semantic_local_accounting_graph_replay_v2",
        lambda *args, **kwargs: deepcopy(graph),
    )
    monkeypatch.setattr(
        sweep,
        "validate_semantic_local_accounting_schema_candidate_replay_v1",
        lambda *args, **kwargs: deepcopy(candidate),
    )
    monkeypatch.setattr(
        sweep,
        "validate_semantic_statement_context_replay_v1",
        lambda *args, **kwargs: deepcopy(context),
    )
    mapped_verification = None
    request_receipt = None
    review_receipt = None
    if mapping["status"] != "NOT_EVALUATED":
        item_verdicts = [
            {
                "claim_kind": (
                    "SOURCE_ONLY_VALIDATION" if row["source_only_total"] else "MAPPED_SCHEMA_ROW"
                ),
                "typed_role": row["typed_role"],
                "report_norm_id": row["candidate_report_norm_id"],
                "row_graph_node_id": row["graph_node_id"],
                "status": row["verdict"],
                "failed_check_ids": deepcopy(row["unresolved_reasons"]),
                "values": [
                    {
                        "axis_index": axis,
                        "raw_text": str((ordinal + 1) * 100 + axis),
                        "normalized_decimal": str((ordinal + 1) * 100 + axis),
                        "state": "OBSERVED_VALUE",
                    }
                    for axis in (0, 1)
                ],
            }
            for ordinal, row in enumerate(mapping["rows"])
        ]
        mapped_verification = {
            "format_version": "CODEX_MAPPED_ITEM_VERIFICATION_V1",
            "verification_id": mapping["verification_id"],
            "family_id": manifest["family_id"],
            "source_authority": {
                "physical_page": plan["physical_page"],
                "source_local_page_id": plan["source_local_page_id"],
                "source_projection_sha256": canonical_json_sha256_v1(source),
                "source_pdf": {
                    "sha256": plan["source_sha256"],
                    "size_bytes": plan["source_size_bytes"],
                },
            },
            "input_identities": {
                "semantic_graph": {
                    "graph_id": graph["graph_id"],
                    "sha256": canonical_json_sha256_v1(graph),
                },
                "schema_candidate": {
                    "candidate_set_id": candidate["candidate_set_id"],
                    "sha256": canonical_json_sha256_v1(candidate),
                },
                "statement_context": {
                    "context_id": context["context_id"],
                    "sha256": canonical_json_sha256_v1(context),
                },
                "source_projection_sha256": canonical_json_sha256_v1(source),
                "semantic_page_binding_sha256": canonical_json_sha256_v1(binding),
                "numeric_verification": {
                    "verification_id": "sgnpvv1:verification:" + "1" * 64,
                    "sha256": "2" * 64,
                    "size_bytes": 1,
                    "path": "sealed-numeric-verification.json",
                },
            },
            "item_verdicts": item_verdicts,
            "near_neighbour_verdicts": [
                {
                    "report_norm_id": item["report_norm_id"],
                    "status": item["status"],
                    "disposition": item["disposition"],
                    "whole_document_absence_claim": item["whole_document_absence_claim"],
                }
                for item in mapping["near_neighbor_verdicts"]
            ],
            "metrics": {
                "verified_mapped_row_count": sum(
                    item["claim_kind"] == "MAPPED_SCHEMA_ROW"
                    and item["status"] == "VERIFIED_BY_CODEX"
                    for item in item_verdicts
                ),
                "verified_source_only_validation_count": sum(
                    item["claim_kind"] == "SOURCE_ONLY_VALIDATION"
                    and item["status"] == "VERIFIED_BY_CODEX"
                    for item in item_verdicts
                ),
                "unresolved_item_count": sum(
                    item["status"] == "UNRESOLVED" for item in item_verdicts
                ),
                "unresolved_near_neighbour_count": len(mapping["near_neighbor_verdicts"]),
            },
        }
        if mapped_verification_mutator is not None:
            mapped_verification_mutator(mapped_verification)
        request_receipt = object()
        review_receipt = object()
        monkeypatch.setattr(
            sweep,
            "_replay_independent_mapping",
            lambda *args, **kwargs: deepcopy(mapped_verification),
        )
    return authenticate_family_sweep_trial_v1(
        manifest,
        panel_selection_authority=PANEL_CAPABILITY,
        trial_id=raw["trial_id"],
        bank=raw["bank"],
        project_root=Path("."),
        semantic_graph_v2=graph,
        schema_candidate_v1=candidate,
        source_projection_v2=source,
        semantic_page_binding_v2=binding,
        authenticated_transformer_receipt_v2=object(),
        family_spec=LOAN_MATURITY_BUCKETS_SPEC_V1,
        family_specs_for_collision_scope=SPECS,
        statement_context_v1=context,
        mapped_item_verification_v1=mapped_verification,
        mapped_item_request_receipt_v1=request_receipt,
        mapped_item_review_receipt_v1=review_receipt,
    )


def test_manifest_freezes_exact_panel_order_family_and_multiple_trials():
    manifest = _manifest(second_acb_trial=True)

    assert (
        validate_family_sweep_manifest_v1(manifest, panel_selection_authority=PANEL_CAPABILITY)
        == manifest
    )
    assert manifest["bank_panel"] == list(BANK_PANEL_V1)
    assert manifest["family_id"] == "LOAN_MATURITY_BUCKETS"
    assert manifest["family_spec_sha256"] == local_accounting_family_spec_sha256_v1(
        LOAN_MATURITY_BUCKETS_SPEC_V1
    )
    assert manifest["metrics"] == {
        "panel_bank_count": 8,
        "planned_bank_count": 2,
        "planned_trial_count": 3,
    }


@pytest.mark.parametrize(
    "mutation",
    (
        lambda plans: plans.pop("VIB"),
        lambda plans: plans.update({"SHB": []}),
        lambda plans: plans["MBB"].__setitem__(0, deepcopy(plans["ACB"][0])),
    ),
)
def test_manifest_rejects_missing_extra_or_duplicate_trial_panel(mutation):
    plans = _plans()
    mutation(plans)
    with pytest.raises(FamilySweepContractV1Error):
        build_family_sweep_manifest_v1(
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            SPECS,
            plans,
            panel_selection_authority=PANEL_CAPABILITY,
        )


def test_manifest_rejects_same_pdf_relabelled_across_all_eight_banks(monkeypatch):
    forged_selection = deepcopy(PANEL_SELECTION)
    source_sha = forged_selection["slots"][0]["source_pdf_sha256"]
    for slot in forged_selection["slots"]:
        slot["source_pdf_sha256"] = source_sha
    forged_selection["projection_id"] = "lm8bpsv1:projection:" + canonical_json_sha256_v1(
        {key: item for key, item in forged_selection.items() if key != "projection_id"}
    )
    monkeypatch.setattr(
        sweep, "_project_panel_selection", lambda _capability: deepcopy(forged_selection)
    )
    plans = {
        bank: [
            {
                "trial_id": f"trial-{ordinal:04d}",
                "source_size_bytes": 1000,
                "source_local_page_id": "ssv2:page:" + f"{ordinal:x}" * 64,
            }
        ]
        for ordinal, bank in enumerate(BANK_PANEL_V1, start=1)
    }

    with pytest.raises(FamilySweepContractV1Error, match="eight distinct bank source PDFs"):
        build_family_sweep_manifest_v1(
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            SPECS,
            plans,
            panel_selection_authority=PANEL_CAPABILITY,
        )


def test_manifest_validator_rejects_rehashed_duplicate_source_locator():
    manifest = _manifest()
    acb_locator = manifest["banks"][0]["trials"][0]
    mbb_locator = manifest["banks"][1]["trials"][0]
    for field in (
        "source_sha256",
        "source_size_bytes",
        "physical_page",
        "source_local_page_id",
    ):
        mbb_locator[field] = acb_locator[field]
    payload = {key: value for key, value in manifest.items() if key != "manifest_id"}
    manifest["manifest_id"] = "fsv1:manifest:" + canonical_json_sha256_v1(payload)

    with pytest.raises(FamilySweepContractV1Error, match="bank/source/page"):
        validate_family_sweep_manifest_v1(manifest, panel_selection_authority=PANEL_CAPABILITY)


def test_raw_panel_projection_cannot_replace_live_selection_capability():
    with pytest.raises(FamilySweepContractV1Error, match="live panel selection replay"):
        build_family_sweep_manifest_v1(
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            SPECS,
            _plans(),
            panel_selection_authority=deepcopy(PANEL_SELECTION),
        )


def test_manifest_refuses_caller_supplied_source_hash_or_physical_page():
    plans = _plans()
    plans["ACB"][0].update({"source_sha256": SHA, "physical_page": 999})

    with pytest.raises(FamilySweepContractV1Error, match="trial plan fields drifted"):
        build_family_sweep_manifest_v1(
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            SPECS,
            plans,
            panel_selection_authority=PANEL_CAPABILITY,
        )


@pytest.mark.parametrize(
    "mutation",
    (
        lambda manifest: manifest["safety"].__setitem__("opaque_live_trial_capability_required", 1),
        lambda manifest: manifest["metrics"].__setitem__("panel_bank_count", 8.0),
    ),
)
def test_manifest_rejects_bool_or_numeric_type_smuggling(mutation):
    manifest = _manifest()
    mutation(manifest)
    payload = {key: value for key, value in manifest.items() if key != "manifest_id"}
    manifest["manifest_id"] = "fsv1:manifest:" + canonical_json_sha256_v1(payload)

    with pytest.raises(FamilySweepContractV1Error):
        validate_family_sweep_manifest_v1(manifest, panel_selection_authority=PANEL_CAPABILITY)


def test_strict_subset_and_unresolved_variants_coexist_without_candidate_mapping_inflation(
    monkeypatch,
):
    manifest = _manifest()
    trials = [
        _authenticate(monkeypatch, manifest, _accepted_receipt(manifest)),
        _authenticate(monkeypatch, manifest, _unresolved_receipt(manifest)),
    ]
    result = build_family_sweep_result_v1(
        manifest,
        trials,
        panel_selection_authority=PANEL_CAPABILITY,
    )

    assert (
        validate_family_sweep_result_v1(
            result,
            manifest,
            trials,
            panel_selection_authority=PANEL_CAPABILITY,
        )
        == result
    )
    assert result["status"] == "PARTIAL_FIXED_PANEL_SWEEP"
    assert result["metrics"]["planned_bank_count"] == 2
    assert result["metrics"]["evaluated_bank_count"] == 2
    assert result["metrics"]["unevaluated_or_partial_bank_count"] == 6
    assert result["banks"][0]["disposition"] == "HAS_ACCEPTED_STRICT_SUBSET"
    assert result["banks"][1]["disposition"] == "UNRESOLVED_ONLY"
    assert result["metrics"]["accepted_strict_subset_trial_count"] == 1
    assert result["metrics"]["unresolved_trial_count"] == 1
    assert result["metrics"]["schema_candidate_role_count"] == 6
    assert result["metrics"]["independently_verified_schema_mapped_row_count"] == 0
    assert result["metrics"]["schema_candidate_counted_as_verified_mapping_count"] == 0
    assert result["metrics"]["accepted_structure_counts"] == {
        "TABLE": 1,
        "LOGICAL_ROW": 4,
        "VALUE_POSITION": 8,
        "AXIS": 2,
        "HIERARCHY": 12,
    }


def test_one_bank_can_preserve_accepted_strict_subset_and_unresolved_variant(monkeypatch):
    manifest = _manifest(second_acb_trial=True)
    accepted = _accepted_receipt(manifest)
    unresolved = _unresolved_receipt(manifest, trial_id="trial-0002", bank="ACB")
    trials = [
        _authenticate(monkeypatch, manifest, accepted),
        _authenticate(monkeypatch, manifest, unresolved),
    ]
    result = build_family_sweep_result_v1(
        manifest, trials, panel_selection_authority=PANEL_CAPABILITY
    )

    assert result["status"] == "PARTIAL_FIXED_PANEL_SWEEP"
    assert result["banks"][0]["disposition"] == "HAS_ACCEPTED_STRICT_SUBSET"
    assert [trial["semantic_graph"]["status"] for trial in result["banks"][0]["trials"]] == [
        "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE",
        "UNRESOLVED",
    ]


def test_opaque_trial_is_bound_to_one_exact_manifest(monkeypatch):
    first = _manifest()
    second = _manifest(second_acb_trial=True)
    trial = _authenticate(monkeypatch, first, _accepted_receipt(first))

    with pytest.raises(FamilySweepContractV1Error, match="another sweep manifest"):
        build_family_sweep_result_v1(second, [trial], panel_selection_authority=PANEL_CAPABILITY)


def test_verified_mapping_counts_only_after_complete_independent_row_gate(monkeypatch):
    manifest = _manifest()
    receipt = _accepted_receipt(manifest)
    receipt["independent_schema_mapping_verification"] = _verified_mapping(receipt)
    trial = _authenticate(monkeypatch, manifest, receipt)
    result = build_family_sweep_result_v1(
        manifest, [trial], panel_selection_authority=PANEL_CAPABILITY
    )

    assert result["metrics"]["schema_candidate_role_count"] == 6
    assert result["metrics"]["independently_verified_schema_mapped_row_count"] == 3
    assert result["metrics"]["verified_source_only_validation_count"] == 1
    assert result["metrics"]["unresolved_schema_mapping_row_count"] == 0
    assert result["metrics"]["unresolved_near_neighbor_count"] == 2
    assert result["metrics"]["verified_numeric_source_trial_count"] == 1
    assert [
        item["report_norm_id"]
        for item in result["banks"][0]["trials"][0]["independent_schema_mapping_verification"][
            "near_neighbor_verdicts"
        ]
    ] == [5747, 1944]


def test_candidate_cannot_self_promote_to_verified_mapping_without_independent_artifact():
    manifest = _manifest()
    receipt = _accepted_receipt(manifest)
    receipt["independent_schema_mapping_verification"] = _verified_mapping(receipt)
    receipt["independent_schema_mapping_verification"]["artifact_sha256"] = None

    with pytest.raises(FamilySweepContractV1Error, match="exact opaque trial capabilities"):
        build_family_sweep_result_v1(
            manifest, [receipt], panel_selection_authority=PANEL_CAPABILITY
        )


def test_unresolved_independent_item_is_not_counted_as_verified_mapping(monkeypatch):
    manifest = _manifest()
    receipt = _accepted_receipt(manifest)
    mapping = _verified_mapping(receipt)
    mapping["status"] = "UNRESOLVED"
    mapping["rows"][0]["verified_report_norm_id"] = None
    mapping["rows"][0]["verdict"] = "UNRESOLVED"
    mapping["rows"][0]["unresolved_reasons"] = ["ROW_LABEL_TYPED_ROLE"]
    receipt["independent_schema_mapping_verification"] = mapping
    trial = _authenticate(monkeypatch, manifest, receipt)
    result = build_family_sweep_result_v1(
        manifest, [trial], panel_selection_authority=PANEL_CAPABILITY
    )

    assert result["metrics"]["independently_verified_schema_mapped_row_count"] == 2
    assert result["metrics"]["verified_source_only_validation_count"] == 1
    assert result["metrics"]["unresolved_schema_mapping_row_count"] == 1
    assert result["metrics"]["unresolved_near_neighbor_count"] == 2
    assert result["metrics"]["verified_numeric_source_trial_count"] == 1


def test_numeric_projection_is_unresolved_only_for_numeric_or_source_failure(monkeypatch):
    manifest = _manifest()
    receipt = _accepted_receipt(manifest)
    mapping = _verified_mapping(receipt)
    mapping["status"] = "UNRESOLVED"
    mapping["rows"][0]["verified_report_norm_id"] = None
    mapping["rows"][0]["verdict"] = "UNRESOLVED"
    mapping["rows"][0]["unresolved_reasons"] = ["NUMERIC_DIGIT_AND_SIGN_AGREEMENT"]
    receipt["independent_schema_mapping_verification"] = mapping
    trial = _authenticate(monkeypatch, manifest, receipt)
    result = build_family_sweep_result_v1(
        manifest, [trial], panel_selection_authority=PANEL_CAPABILITY
    )

    numeric = result["banks"][0]["trials"][0]["independent_numeric_source_verification"]
    assert numeric["status"] == "UNRESOLVED"
    assert numeric["verified_cell_count"] == 6
    assert numeric["unresolved_cell_count"] == 2
    assert result["metrics"]["verified_numeric_source_trial_count"] == 0


@pytest.mark.parametrize(
    "identity_field",
    (
        "semantic_graph",
        "schema_candidate",
        "statement_context",
        "source_projection_sha256",
        "semantic_page_binding_sha256",
    ),
)
def test_mapping_verifier_must_bind_current_graph_candidate_context_and_page(
    monkeypatch, identity_field
):
    manifest = _manifest()
    receipt = _accepted_receipt(manifest)
    receipt["independent_schema_mapping_verification"] = _verified_mapping(receipt)

    def drift_identity(verification):
        identity = verification["input_identities"][identity_field]
        if type(identity) is dict:
            identity["sha256"] = "f" * 64
        else:
            verification["input_identities"][identity_field] = "f" * 64

    with pytest.raises(FamilySweepContractV1Error, match="current graph, candidate, context"):
        _authenticate(
            monkeypatch,
            manifest,
            receipt,
            mapped_verification_mutator=drift_identity,
        )


def test_owner_branch_locality_is_preserved_in_evidence_projection():
    verdict = {"failed_check_ids": ["OWNER_BRANCH_LOCALITY"]}

    mapped = sweep._check_projection_for_verdict(verdict, source_only=False)
    source_only = sweep._check_projection_for_verdict(verdict, source_only=True)

    assert mapped["replay_authenticated_source_or_pdf_evidence"] == "FAIL"
    assert mapped["parent_child_sibling_and_workbook_display_order"] == "FAIL"
    assert source_only["replay_authenticated_source_or_pdf_evidence"] == "FAIL"
    assert source_only["parent_child_sibling_and_workbook_display_order"] == "NOT_APPLICABLE"


def test_source_only_total_can_verify_with_null_ids_but_never_counts_as_mapping(monkeypatch):
    manifest = _manifest()
    receipt = _accepted_receipt(manifest)
    mapping = _verified_mapping(receipt)
    receipt["independent_schema_mapping_verification"] = mapping
    trial = _authenticate(monkeypatch, manifest, receipt)
    result = build_family_sweep_result_v1(
        manifest, [trial], panel_selection_authority=PANEL_CAPABILITY
    )

    assert result["metrics"]["independently_verified_schema_mapped_row_count"] == 3
    assert result["metrics"]["verified_source_only_validation_count"] == 1
    assert result["metrics"]["unresolved_schema_mapping_row_count"] == 0


def test_context_and_numeric_are_separate_nonstructural_dispositions(monkeypatch):
    manifest = _manifest()
    receipt = _accepted_receipt(manifest)
    receipt["statement_context"] = {
        "context_id": "sscxtv1:context:" + "e" * 64,
        "artifact_sha256": "f" * 64,
        "status": "UNRESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT",
        "unresolved_reasons": ["NO_EXACT_SUPPORTED_VISIBLE_PAGE_HEADING"],
    }
    receipt["independent_numeric_source_verification"] = {
        "verification_id": "sgnpvv1:verification:" + "1" * 64,
        "artifact_sha256": "2" * 64,
        "status": "UNRESOLVED",
        "verified_cell_count": 7,
        "unresolved_cell_count": 1,
    }
    trial = _authenticate(monkeypatch, manifest, receipt)
    result = build_family_sweep_result_v1(
        manifest, [trial], panel_selection_authority=PANEL_CAPABILITY
    )

    assert result["metrics"]["accepted_strict_subset_trial_count"] == 1
    assert result["metrics"]["resolved_statement_context_trial_count"] == 0
    assert result["metrics"]["verified_numeric_source_trial_count"] == 0


def test_raw_self_authored_receipt_and_opaque_constructor_fail_closed():
    manifest = _manifest()
    receipt = _accepted_receipt(manifest)
    receipt["upstream_replay_validated"] = True
    receipt["independent_schema_mapping_verification"] = _verified_mapping(receipt)

    with pytest.raises(FamilySweepContractV1Error, match="exact opaque trial capabilities"):
        build_family_sweep_result_v1(
            manifest, [receipt], panel_selection_authority=PANEL_CAPABILITY
        )
    with pytest.raises(FamilySweepContractV1Error, match="cannot be caller-constructed"):
        AuthenticatedFamilySweepTrialV1(object())


def test_result_identity_and_metrics_tamper_fail_replay(monkeypatch):
    manifest = _manifest()
    trial = _authenticate(monkeypatch, manifest, _accepted_receipt(manifest))
    result = build_family_sweep_result_v1(
        manifest, [trial], panel_selection_authority=PANEL_CAPABILITY
    )
    result["metrics"]["independently_verified_schema_mapped_row_count"] = 1
    payload = {key: value for key, value in result.items() if key != "result_id"}
    result["result_id"] = "fsv1:result:" + canonical_json_sha256_v1(payload)

    with pytest.raises(FamilySweepContractV1Error):
        validate_family_sweep_result_v1(
            result,
            manifest,
            [trial],
            panel_selection_authority=PANEL_CAPABILITY,
        )
