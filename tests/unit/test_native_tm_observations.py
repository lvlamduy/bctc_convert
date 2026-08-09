from __future__ import annotations

import copy
import importlib.util
import inspect
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import fitz
import pytest

from bctc_ai.core.hashing import sha256_bytes
from bctc_ai.core.text import retrieval_key
from bctc_ai.document_phase import native_tm_document_artifact as native_document
from bctc_ai.rows import native_tm_observations as native

_REAL_NATIVE_DOCUMENT = Path(
    "output/development/vpb-q1-2026-native-tm-document-v1/native-tm-document.json"
)


def _real_projection_inputs(project_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    document_path = project_root / _REAL_NATIVE_DOCUMENT
    if not document_path.is_file():
        pytest.skip("the registered VPB native TM document is not present")
    document_bytes = document_path.read_bytes()
    document = json.loads(document_bytes)
    policy_path = project_root / native.POLICY_RELATIVE_PATH
    policy_bytes = policy_path.read_bytes()
    policy = native.load_native_tm_observations_policy(policy_path, project_root)
    runtime_inputs = sorted(
        [
            {
                "kind": "NATIVE_TM_DOCUMENT_ARTIFACT",
                "path": _REAL_NATIVE_DOCUMENT.as_posix(),
                "sha256": sha256_bytes(document_bytes),
                "size_bytes": len(document_bytes),
            },
            {
                "kind": "THIS_POLICY",
                "path": native.POLICY_RELATIVE_PATH.as_posix(),
                "sha256": sha256_bytes(policy_bytes),
                "size_bytes": len(policy_bytes),
            },
        ],
        key=lambda record: (record["kind"], record["path"]),
    )
    projection = native._build_projection(
        native_document=document,
        native_document_identity={
            "path": _REAL_NATIVE_DOCUMENT.as_posix(),
            "sha256": sha256_bytes(document_bytes),
            "size_bytes": len(document_bytes),
        },
        policy_relative=native.POLICY_RELATIVE_PATH.as_posix(),
        policy_bytes=policy_bytes,
        policy=policy,
        runtime_inputs=runtime_inputs,
        implementation=[
            {"path": path, "sha256": "0" * 64, "size_bytes": 0}
            for path in native._IMPLEMENTATION_PATHS
        ],
        producer_commit="0" * 40,
        run_id="vpb-real-regression",
    )
    return projection, document


@pytest.fixture(scope="module")
def real_projection(project_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    return _real_projection_inputs(project_root)


def _all_evidence(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [record for records in payload["source_evidence"].values() for record in records]


def _owner_records(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        record["source_object_id"]: record
        for record in _all_evidence(payload)
        if record["record_type"] == "SOURCE_RUN" or record["record_type"] == "UNASSIGNED_PAGE_RUN"
    }


def test_policy_and_public_api_are_generic_source_only(project_root: Path) -> None:
    policy = native.load_native_tm_observations_policy(
        project_root / native.POLICY_RELATIVE_PATH, project_root
    )

    assert policy["flattening"]["grains"] == [
        "PAGE",
        "CONTEXT",
        "ROW",
        "DIMENSION",
        "OBSERVATION",
    ]
    assert policy["role_isolation"]["direct_runtime_input_allowlist"] == [
        "NATIVE_TM_DOCUMENT_ARTIFACT",
        "THIS_POLICY",
    ]
    assert policy["flattening"]["preserve_every_page"] is True
    assert policy["flattening"]["preserve_unit_group_diagnostics"] is True
    assert policy["flattening"]["row_dependent_bindings_materialized"] is False
    assert policy["flattening"]["unresolved_bindings_coerced"] is False
    assert policy["report_scope"]["consolidated_retrieval_lexemes"] == ["hop nhat"]
    assert policy["report_scope"]["separate_retrieval_lexemes"] == [
        "rieng",
        "rieng le",
    ]
    assert all(
        policy["role_isolation"][key] is False
        for key in (
            "schema_inputs_allowed",
            "aliases_allowed",
            "mapping_inputs_allowed",
            "bank_identity_used_for_routing",
            "filename_identity_used_for_routing",
            "page_number_rules_used_for_routing",
            "note_number_rules_used_for_routing",
            "expected_count_rules_used_for_routing",
        )
    )
    assert (
        "git_state"
        not in inspect.signature(native.build_registered_native_tm_observations).parameters
    )


def test_real_primary_denominators_and_six_state_distributions(
    real_projection: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    payload, _document = real_projection
    accounting = payload["source_accounting"]
    counts = accounting["counts"]

    assert payload["status"] == "COMPLETE_NATIVE_TM_SOURCE_OBJECT_ACCOUNTING"
    assert payload["run_id"] == "vpb-real-regression"
    assert accounting["source_object_accounting_complete"] is True
    assert accounting["full_document_context_complete"] is False
    assert accounting["unresolved_inter_table_context_count"] == 30
    assert counts == {
        **counts,
        "page_record_count": 91,
        "context_record_count": 97,
        "outside_quantitative_tm_context_count": 6,
        "row_record_count": 934,
        "dimension_record_count": 265,
        "observation_record_count": 2523,
        "quantitative_context_count": 91,
        "quantitative_region_row_count": 734,
        "quantitative_outside_financial_span_row_count": 31,
        "quantitative_scalar_row_count": 4,
        "quantitative_inter_table_context_row_count": 32,
        "quantitative_value_bearing_row_count": 694,
        "quantitative_dimension_count": 251,
        "quantitative_grid_slot_count": 2218,
        "quantitative_observation_position_count": 2222,
        "quantitative_visible_observation_count": 2163,
        "all_observation_position_count": 2523,
        "all_visible_observation_count": 2438,
        "quantitative_invalid_source_marker_count": 14,
        "row_local_scalar_observation_count": 4,
    }
    assert accounting["quantitative_grid_slot_source_status_counts"] == {
        "OBSERVED_VALUE": 1844,
        "OBSERVED_ZERO": 18,
        "DASH": 283,
        "INVALID_SOURCE_MARKER": 14,
        "BLANK": 57,
        "UNRESOLVED_EMPTY_SLOT": 2,
    }
    assert accounting["quantitative_scalar_source_status_counts"] == {
        "OBSERVED_VALUE": 4,
        "OBSERVED_ZERO": 0,
        "DASH": 0,
        "INVALID_SOURCE_MARKER": 0,
    }
    assert accounting["quantitative_position_source_status_counts"] == {
        "OBSERVED_VALUE": 1848,
        "OBSERVED_ZERO": 18,
        "DASH": 283,
        "INVALID_SOURCE_MARKER": 14,
        "BLANK": 57,
        "UNRESOLVED_EMPTY_SLOT": 2,
    }
    assert accounting["all_grid_slot_source_status_counts"] == {
        "OBSERVED_VALUE": 2116,
        "OBSERVED_ZERO": 18,
        "DASH": 286,
        "INVALID_SOURCE_MARKER": 14,
        "BLANK": 83,
        "UNRESOLVED_EMPTY_SLOT": 2,
    }
    assert accounting["all_position_source_status_counts"] == {
        "OBSERVED_VALUE": 2120,
        "OBSERVED_ZERO": 18,
        "DASH": 286,
        "INVALID_SOURCE_MARKER": 14,
        "BLANK": 83,
        "UNRESOLVED_EMPTY_SLOT": 2,
    }


def test_real_pages_contexts_rows_and_dispositions_are_exactly_partitioned(
    real_projection: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    payload, document = real_projection
    row_kinds = Counter(row["row_source_kind"] for row in payload["rows"])
    classifications = Counter(page["classification"] for page in payload["page_inventory"])

    assert classifications == {
        "NON_TM": 10,
        "QUALITATIVE_TM_CONTEXT": 36,
        "QUANTITATIVE_TM": 45,
    }
    assert row_kinds == {
        "REGION_ROW": 867,
        "OUTSIDE_FINANCIAL_SPAN_ROW": 31,
        "ROW_LOCAL_SCALAR": 4,
        "INTER_TABLE_CONTEXT_ROW": 32,
    }
    assert payload["source_identity_contract"] == {
        "upstream_row_id_scope": "GLOBALLY_PRODUCER_QUALIFIED",
        "upstream_scalar_id_scope": "GLOBALLY_PRODUCER_QUALIFIED",
        "table_owned_id_prefix": "<source_table_id>:",
        "grid_observation_natural_key": ["row_id", "axis_id"],
        "scalar_observation_natural_key": ["scalar_id"],
        "context_row_ownership_natural_key": [
            "inter_table_context_id",
            "row_id",
        ],
        "context_row_table_owner_status": "NOT_FABRICATED",
    }
    assert payload["source_accounting"]["source_identity_accounting"] == {
        "globally_unique_upstream_row_id_count": 934,
        "globally_unique_upstream_scalar_id_count": 4,
        "unique_grid_observation_natural_key_count": 2519,
        "unique_context_row_ownership_key_count": 32,
        "table_owned_id_prefix_consistency": True,
        "context_rows_have_no_fabricated_table_owner": True,
    }
    assert len({row["row_id"] for row in payload["rows"]}) == 934
    assert (
        len(
            {
                observation["scalar_id"]
                for observation in payload["observations"]
                if observation["observation_source_kind"] == "ROW_LOCAL_SCALAR"
            }
        )
        == 4
    )
    assert (
        len(
            {
                (observation["row_id"], observation["axis_id"])
                for observation in payload["observations"]
                if observation["observation_source_kind"] == "GRID_SLOT"
            }
        )
        == 2519
    )
    assert all(
        row["row_id"].startswith(f"{row['source_table_id']}:")
        for row in payload["rows"]
        if row["row_source_kind"] != "INTER_TABLE_CONTEXT_ROW"
    )
    assert sum(row["page_classification"] == "QUANTITATIVE_TM" for row in payload["rows"]) == 801
    assert payload["ordering"] == {
        "rows_list_position": "NON_AUTHORITATIVE_GROUPED_BY_EXTRACTION_PASS",
        "within_source_container_order": "AUTHORITATIVE",
        "cross_container_row_order": "NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE",
        "context_row_run_partition": "UNRESOLVED_CONTEXT_LEVEL_ONLY",
    }
    assert all(
        row["source_order"]["page"] == row["page"]
        and row["source_order"]["cross_container_order_status"]
        == "NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE"
        for row in payload["rows"]
    )
    context_rows = [
        row for row in payload["rows"] if row["row_source_kind"] == "INTER_TABLE_CONTEXT_ROW"
    ]
    assert all(
        row["run_partition_status"] == "UNRESOLVED_CONTEXT_LEVEL_ONLY"
        and "source_record_sha256" not in row
        and "context_row_reference_sha256" in row
        for row in context_rows
    )
    assert Counter(row["page"] for row in context_rows)[61] == 2
    assert Counter(row["page"] for row in context_rows)[67] == 2

    outside_context_ids = {
        context["context_id"]
        for context in payload["contexts"]
        if context["source_disposition"] == "OUTSIDE_QUANTITATIVE_TM"
    }
    assert len(outside_context_ids) == 6
    assert sum(row.get("context_id") in outside_context_ids for row in payload["rows"]) == 133
    assert (
        sum(dimension["context_id"] in outside_context_ids for dimension in payload["dimensions"])
        == 14
    )
    assert (
        sum(
            observation["context_id"] in outside_context_ids
            for observation in payload["observations"]
        )
        == 301
    )

    accounted = [
        *payload["page_inventory"],
        *payload["contexts"],
        *payload["rows"],
        *payload["dimensions"],
        *payload["observations"],
        *_all_evidence(payload),
    ]
    accounted_ids = [record["source_object_id"] for record in accounted]
    disposition_ids = [
        disposition["source_object_id"] for disposition in payload["source_dispositions"]
    ]
    assert len(accounted_ids) == len(set(accounted_ids)) == 11032
    assert set(disposition_ids) == set(accounted_ids)
    assert len(disposition_ids) == len(set(disposition_ids))
    assert (
        payload["inputs"]["inherited_upstream_replay_provenance"]["inventories"]["note_inventory"]
        == document["note_inventory"]
    )
    assert (
        payload["inputs"]["inherited_upstream_replay_provenance"]["inventories"]["table_inventory"]
        == document["table_inventory"]
    )
    assert len(document["note_inventory"]["records"]) == 85
    assert len(document["table_inventory"]["records"]) == 97
    assert len(document["table_inventory"]["inter_table_contexts"]) == 30


def test_real_multirow_inter_table_contexts_keep_context_grain_run_ownership(
    real_projection: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    payload, _document = real_projection
    context_evidence = payload["source_evidence"]["inter_table_contexts"]
    context_rows = [
        row for row in payload["rows"] if row["row_source_kind"] == "INTER_TABLE_CONTEXT_ROW"
    ]

    for page_number in (61, 67):
        page_contexts = [record for record in context_evidence if record["page"] == page_number]
        page_rows = [row for row in context_rows if row["page"] == page_number]
        assert len(page_contexts) == 1
        assert len(page_contexts[0]["source_record"]["source_row_ids"]) == 2
        assert len(page_contexts[0]["source_record"]["runs"]) == 3
        assert len(page_rows) == 2
        assert {row["inter_table_context_id"] for row in page_rows} == {
            page_contexts[0]["evidence_id"]
        }
        assert all(
            row["run_partition_status"] == "UNRESOLVED_CONTEXT_LEVEL_ONLY"
            and row["label"] is None
            and row["label_boxes"] == []
            and row["source_cells"] == []
            and "runs" not in row
            and "source_run_ids" not in row
            for row in page_rows
        )


def test_real_dimensions_preserve_headers_and_never_fabricate_row_bindings(
    real_projection: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    payload, _document = real_projection
    quantitative = [
        dimension
        for dimension in payload["dimensions"]
        if dimension["page_classification"] == "QUANTITATIVE_TM"
    ]
    statuses = Counter(dimension["binding_status"] for dimension in quantitative)
    binding = payload["source_accounting"]["binding_accounting"]

    assert statuses == {
        "RESOLVED": 169,
        "PARTIALLY_RESOLVED": 80,
        "RESOLVED_WITH_SOURCE_CONFLICT": 2,
    }
    assert binding == {
        "period_row_dependent_dimension_count": 57,
        "period_row_dependent_position_count": 459,
        "period_row_dependent_visible_observation_count": 459,
        "period_unresolved_dimension_count": 15,
        "period_unresolved_position_count": 182,
        "period_unresolved_visible_observation_count": 126,
        "unit_row_dependent_dimension_count": 8,
        "unit_row_dependent_position_count": 60,
        "unit_row_dependent_visible_observation_count": 60,
        "source_conflict_dimension_count": 2,
        "source_conflict_position_count": 10,
    }
    assert payload["source_accounting"]["period_group_accounting"] == {
        "axis_use_count": 218,
        "qualified_natural_group_count": 164,
        "unqualified_source_id_count": 2,
        "natural_key_fields": ["source_table_id", "period_group_id"],
        "qualified_identity_is_lossless": True,
    }
    assert all(
        dimension["qualified_period_group_id"]
        == (
            None
            if dimension.get("period_group_id") is None
            else (f"PERIOD_GROUP::{dimension['source_table_id']}::{dimension['period_group_id']}")
        )
        for dimension in payload["dimensions"]
    )
    assert all(
        [component["component_order"] for component in dimension["header_components"]]
        == list(range(1, len(dimension["header_components"]) + 1))
        and all(
            component["semantic_component_kind"] == "UNAVAILABLE_IN_UPSTREAM_BINDING"
            and component["semantic_assignment_status"] == "NOT_MATERIALIZED"
            for component in dimension["header_components"]
        )
        for dimension in payload["dimensions"]
    )
    conflict_dimensions = [
        dimension for dimension in quantitative if "CONFLICT" in dimension["binding_status"]
    ]
    assert len(conflict_dimensions) == 2
    assert all(
        dimension[grain]["resolution_status"] == "SOURCE_CONFLICT"
        and dimension[grain]["materialization_status"] == "NOT_MATERIALIZED"
        for dimension in conflict_dimensions
        for grain in ("period_materialization", "unit_materialization")
    )
    unresolved_or_row_dependent = [
        dimension
        for dimension in quantitative
        if dimension["period_scope"] in {"ROW_DEPENDENT", "UNRESOLVED"}
        or dimension["unit_scope"] in {"ROW_DEPENDENT", "UNRESOLVED"}
    ]
    assert all(
        materialization["materialization_status"] == "NOT_MATERIALIZED"
        and materialization["row_override_evidence_status"]
        == "NOT_SERIALIZED_BY_UPSTREAM_SOURCE_STAGE"
        for dimension in unresolved_or_row_dependent
        for materialization in (
            dimension["period_materialization"],
            dimension["unit_materialization"],
        )
        if materialization["resolution_status"]
        in {"ROW_DEPENDENT", "UNRESOLVED", "SOURCE_CONFLICT"}
    )
    assert all(
        observation["dimension_binding_materialized_on_observation"] is False
        for observation in payload["observations"]
    )


def test_real_run_owners_aliases_words_and_unit_diagnostics_reconcile(
    real_projection: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    payload, _document = real_projection
    owners = _owner_records(payload)
    accounting = payload["source_accounting"]
    counts = accounting["counts"]
    aliases = accounting["source_run_alias_accounting"]

    assert len(owners) == counts["canonical_source_run_count"] == 6942
    assert counts == {
        **counts,
        "geometry_source_run_count": 4582,
        "inter_table_context_source_run_count": 61,
        "unassigned_page_source_run_count": 2299,
        "detached_margin_source_run_count": 0,
        "unit_group_diagnostic_count": 99,
        "accepted_unit_group_diagnostic_count": 97,
        "rejected_unit_group_diagnostic_count": 2,
        "quantitative_unit_group_diagnostic_count": 93,
        "quantitative_accepted_unit_group_diagnostic_count": 91,
        "quantitative_rejected_unit_group_diagnostic_count": 2,
    }
    assert aliases == {
        "region_header_reference_count": 992,
        "binding_source_run_reference_count": 870,
        "source_visible_tm_header_reference_count": 81,
        "source_visible_continuation_reference_count": 167,
        "source_visible_note_heading_reference_count": 92,
        "unique_alias_page_run_count": 1199,
        "every_alias_references_one_canonical_source_run_owner": True,
    }

    word_indices_by_page: defaultdict[int, list[int]] = defaultdict(list)
    for owner in owners.values():
        word_indices_by_page[owner["page"]].extend(owner["source_record"]["word_indices"])
    for page in payload["page_inventory"]:
        indices = word_indices_by_page[page["page"]]
        assert len(indices) == len(set(indices))
        assert sorted(indices) == list(range(page["visible_native_word_count"]))

    diagnostics = payload["source_evidence"]["unit_group_diagnostics"]
    accepted_groups = Counter(
        (record["page"], tuple(record["source_record"]["unit_run_ids"]))
        for record in diagnostics
        if record["source_record"]["accepted"]
    )
    region_groups = Counter(
        (context["page"], tuple(context["geometry_metadata"]["unit_run_ids"]))
        for context in payload["contexts"]
    )
    assert accepted_groups == region_groups
    assert all(
        owner_id in owners for record in diagnostics for owner_id in record["unit_run_owner_ids"]
    )

    observations_by_id = {
        observation["observation_id"]: observation for observation in payload["observations"]
    }
    scalar_groups = Counter()
    for context in payload["contexts"]:
        unit_ids = tuple(
            observations_by_id[observation_id]["unit_run_id"]
            for observation_id in context["observation_ids"]
            if observations_by_id[observation_id]["observation_source_kind"] == "ROW_LOCAL_SCALAR"
        )
        if unit_ids:
            scalar_groups[(context["page"], unit_ids)] += 1
    rejected_groups = Counter(
        (record["page"], tuple(record["source_record"]["unit_run_ids"]))
        for record in diagnostics
        if not record["source_record"]["accepted"]
    )
    assert rejected_groups == scalar_groups
    assert set(page for page, _unit_ids in rejected_groups) == {49, 50}
    assert sum(len(unit_ids) for _page, unit_ids in rejected_groups) == 4


def test_real_report_scope_is_source_visible_unanimous_and_non_routing(
    real_projection: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    payload, _document = real_projection
    scope = payload["report_scope_binding"]

    assert scope["scope"] == "CONSOLIDATED"
    assert scope["binding_status"] == ("RESOLVED_UNANIMOUS_SOURCE_VISIBLE_TM_HEADERS")
    assert scope["source_header_run_count"] == 81
    assert scope["signal_counts"] == {
        "CONSOLIDATED": 81,
        "SEPARATE": 0,
        "CONFLICT": 0,
        "UNCLASSIFIED": 0,
    }
    texts = Counter(evidence["source_run"]["raw_text"] for evidence in scope["evidence_runs"])
    assert texts == {
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT GIỮA NIÊN ĐỘ": 1,
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT GIỮA NIÊN ĐỘ (tiếp theo)": 80,
    }
    assert all(
        evidence["source_owner_id"] in _owner_records(payload)
        for evidence in scope["evidence_runs"]
    )
    assert all(
        feature["used_for_routing"] is False
        for feature in payload["non_decision_features"].values()
    )
    assert {record["kind"] for record in payload["inputs"]["direct_runtime_input_ledger"]} == {
        "NATIVE_TM_DOCUMENT_ARTIFACT",
        "THIS_POLICY",
    }


def test_scope_binding_fails_closed_for_absent_mixed_conflicting_and_unclassified(
    project_root: Path,
) -> None:
    policy = native.load_native_tm_observations_policy(
        project_root / native.POLICY_RELATIVE_PATH, project_root
    )

    def page(*texts: str) -> dict[str, Any]:
        return {
            "page": 1,
            "source_visible_tm_header_runs": [
                {"run_id": f"r{ordinal}", "raw_text": text} for ordinal, text in enumerate(texts)
            ],
        }

    assert native._scope_binding([], policy)["binding_status"] == (
        "UNRESOLVED_NO_SOURCE_VISIBLE_TM_HEADER"
    )
    assert (
        native._scope_binding([page("Bao cao hop nhat", "Bao cao rieng")], policy)["binding_status"]
        == "UNRESOLVED_CONFLICTING_SOURCE_VISIBLE_TM_HEADERS"
    )
    assert (
        native._scope_binding([page("Bao cao hop nhat rieng")], policy)["binding_status"]
        == "UNRESOLVED_CONFLICTING_SOURCE_VISIBLE_TM_HEADERS"
    )
    assert (
        native._scope_binding([page("Bao cao tai chinh")], policy)["binding_status"]
        == "UNRESOLVED_UNCLASSIFIED_SOURCE_VISIBLE_TM_HEADERS"
    )


def test_full_and_reduced_run_alias_contracts_are_distinct_and_exact() -> None:
    owner = {
        "run_id": "b1:l2:s3",
        "raw_text": "Hợp nhất",
        "normalized_text": "Hợp nhất",
        "bbox": {"x0": 1.0, "y0": 2.0, "x1": 3.0, "y1": 4.0},
        "block_number": 1,
        "line_number": 2,
        "word_indices": [7, 8],
    }
    assert native._full_run_reference_matches(owner, owner)
    mutated_full = copy.deepcopy(owner)
    mutated_full["word_indices"] = [7]
    assert not native._full_run_reference_matches(mutated_full, owner)

    reduced = {key: copy.deepcopy(value) for key, value in owner.items() if key != "word_indices"}
    reduced["retrieval_key"] = retrieval_key(reduced["raw_text"])
    assert native._page_evidence_reference_matches(reduced, owner)
    with_word_indices = {**reduced, "word_indices": [7, 8]}
    assert not native._page_evidence_reference_matches(with_word_indices, owner)
    bad_key = {**reduced, "retrieval_key": "invented"}
    assert not native._page_evidence_reference_matches(bad_key, owner)


def test_real_projection_rejects_reclassified_orphan_accepted_unit_group(
    project_root: Path,
) -> None:
    _projection, document = _real_projection_inputs(project_root)
    mutated = copy.deepcopy(document)
    rejected = next(
        diagnostic
        for page in mutated["pages"]
        for diagnostic in page["native_tm_regions"]["unit_group_diagnostics"]
        if diagnostic["accepted"] is False
    )
    rejected["accepted"] = True
    with pytest.raises(
        native.NativeTMObservationsError,
        match="does not exactly equal one ordered region geometry unit group",
    ):
        _projection_from_document(project_root, mutated)


def test_real_projection_rejects_unmaterialized_outside_row_cells(
    project_root: Path,
) -> None:
    _projection, document = _real_projection_inputs(project_root)
    mutated = copy.deepcopy(document)
    outside_row = next(
        row
        for page in mutated["pages"]
        for region in page["native_tm_regions"]["regions"]
        for row in region["outside_financial_span_rows"]
    )
    outside_row["cells"] = [{"axis_id": "fabricated"}]
    with pytest.raises(native.NativeTMObservationsError, match="cannot be dropped"):
        _projection_from_document(project_root, mutated)


def _projection_from_document(project_root: Path, document: dict[str, Any]) -> dict[str, Any]:
    document_path = project_root / _REAL_NATIVE_DOCUMENT
    document_bytes = document_path.read_bytes()
    policy_path = project_root / native.POLICY_RELATIVE_PATH
    policy_bytes = policy_path.read_bytes()
    policy = native.load_native_tm_observations_policy(policy_path, project_root)
    runtime_inputs = sorted(
        [
            {
                "kind": "NATIVE_TM_DOCUMENT_ARTIFACT",
                "path": _REAL_NATIVE_DOCUMENT.as_posix(),
                "sha256": sha256_bytes(document_bytes),
                "size_bytes": len(document_bytes),
            },
            {
                "kind": "THIS_POLICY",
                "path": native.POLICY_RELATIVE_PATH.as_posix(),
                "sha256": sha256_bytes(policy_bytes),
                "size_bytes": len(policy_bytes),
            },
        ],
        key=lambda record: (record["kind"], record["path"]),
    )
    return native._build_projection(
        native_document=document,
        native_document_identity={
            "path": _REAL_NATIVE_DOCUMENT.as_posix(),
            "sha256": sha256_bytes(document_bytes),
            "size_bytes": len(document_bytes),
        },
        policy_relative=native.POLICY_RELATIVE_PATH.as_posix(),
        policy_bytes=policy_bytes,
        policy=policy,
        runtime_inputs=runtime_inputs,
        implementation=[
            {"path": path, "sha256": "0" * 64, "size_bytes": 0}
            for path in native._IMPLEMENTATION_PATHS
        ],
        producer_commit="0" * 40,
        run_id="mutated-real-regression",
    )


def _load_native_document_test_helpers(project_root: Path) -> ModuleType:
    helper_path = project_root / "tests/unit/test_native_tm_document_artifact.py"
    module_name = "_native_tm_document_test_helpers_for_observations"
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _make_consolidated_pdf(helpers: ModuleType, path: Path, *, last_page_header: bool) -> None:
    document = fitz.open()
    page = document.new_page(width=600, height=800)
    helpers._table_page(
        page,
        top_text="BANG CAN DOI KE TOAN",
        heading="Tai san va no phai tra",
    )
    page = document.new_page(width=600, height=800)
    helpers._table_page(
        page,
        top_text="THUYET MINH BAO CAO TAI CHINH HOP NHAT",
        heading="1 Tien mat va tuong duong tien",
    )
    page = document.new_page(width=600, height=800)
    helpers._table_page(
        page,
        top_text="TIEP THEO",
        heading="2 Cho vay khach hang",
    )
    page = document.new_page(width=600, height=800)
    helpers._table_page(
        page,
        top_text=("THUYET MINH BAO CAO TAI CHINH HOP NHAT" if last_page_header else None),
        heading="3 Tai san khac",
    )
    document.save(path)
    document.close()


@dataclass(frozen=True)
class _SyntheticPublication:
    root: Path
    source_path: Path
    discovery_path: Path
    native_path: Path
    native_sha256: str
    policy_path: Path
    output_path: Path
    publication: native.NativeTMObservationsPublication


@pytest.fixture(scope="module")
def synthetic_publication(
    project_root: Path, tmp_path_factory: pytest.TempPathFactory
) -> _SyntheticPublication:
    helpers = _load_native_document_test_helpers(project_root)
    original_make_pdf = helpers._make_pdf
    helpers._make_pdf = lambda path, last_page_header: _make_consolidated_pdf(
        helpers, path, last_page_header=last_page_header
    )
    try:
        root, source, discovery, native_policy, discovery_sha256 = helpers._make_registered_project(
            tmp_path_factory.mktemp("native-tm-observations"),
            project_root,
            last_page_header=True,
        )
    finally:
        helpers._make_pdf = original_make_pdf

    nested_discovery = root / "output/development/discovery/input.json"
    nested_discovery.parent.mkdir(parents=True, exist_ok=True)
    discovery.replace(nested_discovery)
    discovery = nested_discovery

    for relative in (
        native.POLICY_RELATIVE_PATH.as_posix(),
        "src/bctc_ai/rows/native_tm_observations.py",
    ):
        helpers._copy(root, project_root, relative)
    helpers._run_git(root, "add", ".")
    helpers._run_git(root, "commit", "-m", "add observation producer")

    native_path = root / "output/development/native/native-tm-document.json"
    native_path.parent.mkdir(parents=True, exist_ok=True)
    document_publication = native_document.publish_registered_native_tm_document_artifact(
        root,
        source,
        discovery,
        discovery_sha256,
        native_policy,
        "synthetic-native-tm-v1",
        native_path,
    )
    output_path = root / "output/development/observations/native-tm-observations.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    publication = native.publish_registered_native_tm_observations(
        root,
        native_path,
        document_publication.sha256,
        root / native.POLICY_RELATIVE_PATH,
        "synthetic-native-tm-observations-v1",
        output_path,
    )
    return _SyntheticPublication(
        root=root,
        source_path=source,
        discovery_path=discovery,
        native_path=native_path,
        native_sha256=document_publication.sha256,
        policy_path=root / native.POLICY_RELATIVE_PATH,
        output_path=output_path,
        publication=publication,
    )


def test_publication_is_canonical_exclusive_and_strictly_replayable(
    synthetic_publication: _SyntheticPublication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = synthetic_publication
    publication = fixture.publication
    assert publication.payload["run_id"] == "synthetic-native-tm-observations-v1"
    assert fixture.output_path.read_bytes() == native._canonical_json_bytes(publication.payload)
    assert sha256_bytes(fixture.output_path.read_bytes()) == publication.sha256
    assert (
        native.load_registered_native_tm_observations(
            fixture.output_path,
            project_root=fixture.root,
            expected_sha256=publication.sha256,
        )
        == publication.payload
    )

    monkeypatch.setattr(
        native,
        "build_registered_native_tm_observations",
        lambda *_args, **_kwargs: publication.payload,
    )
    with pytest.raises(native.NativeTMObservationsError, match="refusing to overwrite"):
        native.publish_registered_native_tm_observations(
            fixture.root,
            fixture.native_path,
            fixture.native_sha256,
            fixture.policy_path,
            "synthetic-native-tm-observations-v1",
            fixture.output_path,
        )


def test_strict_loader_uses_frozen_producer_when_current_native_loader_explodes(
    synthetic_publication: _SyntheticPublication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = synthetic_publication

    def current_loader_must_not_run(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("current native TM semantic loader ran")

    monkeypatch.setattr(
        native._native_document,
        "load_registered_native_tm_document_artifact",
        current_loader_must_not_run,
    )
    assert (
        native.load_registered_native_tm_observations(
            fixture.output_path,
            project_root=fixture.root,
            expected_sha256=fixture.publication.sha256,
        )
        == fixture.publication.payload
    )


def test_strict_loader_rejects_rehashed_tampering_via_producer_replay(
    synthetic_publication: _SyntheticPublication,
    tmp_path: Path,
) -> None:
    fixture = synthetic_publication
    tampered = copy.deepcopy(fixture.publication.payload)
    tampered["authority"]["rows"] = "TAMPERED"
    encoded = native._canonical_json_bytes(tampered)
    tampered_path = fixture.root / "output/development/tampered-observations.json"
    tampered_path.write_bytes(encoded)
    try:
        with pytest.raises(
            native.NativeTMObservationsError,
            match="producer-commit deterministic replay",
        ):
            native.load_registered_native_tm_observations(
                tampered_path,
                project_root=fixture.root,
                expected_sha256=sha256_bytes(encoded),
            )
    finally:
        tampered_path.unlink(missing_ok=True)
    assert tmp_path.is_dir()


def test_nested_native_input_rejects_lexical_and_final_symlink_aliases(
    synthetic_publication: _SyntheticPublication,
) -> None:
    fixture = synthetic_publication
    lexical_alias = fixture.root / "output/development/native/native-alias.json"
    lexical_alias.symlink_to(fixture.native_path.name)
    try:
        with pytest.raises(native.NativeTMObservationsError, match="symlink"):
            native.build_registered_native_tm_observations(
                fixture.root,
                lexical_alias,
                fixture.native_sha256,
                fixture.policy_path,
                "symlink-input",
            )
    finally:
        lexical_alias.unlink(missing_ok=True)

    held_name = fixture.native_path.with_name("native-tm-document.real.json")
    fixture.native_path.rename(held_name)
    fixture.native_path.symlink_to(held_name.name)
    try:
        with pytest.raises(native.NativeTMObservationsError, match="symlink"):
            native.load_registered_native_tm_observations(
                fixture.output_path,
                project_root=fixture.root,
                expected_sha256=fixture.publication.sha256,
            )
    finally:
        fixture.native_path.unlink(missing_ok=True)
        held_name.rename(fixture.native_path)


def test_authenticated_preflight_rejects_malicious_transitive_paths_before_read(
    synthetic_publication: _SyntheticPublication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = synthetic_publication
    native_bytes = fixture.native_path.read_bytes()
    native_payload = json.loads(native_bytes)
    producer_policy = native.load_native_tm_observations_policy(fixture.policy_path, fixture.root)

    def transitive_read_must_not_start(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("unauthenticated transitive path was opened")

    monkeypatch.setattr(
        native._native_document,
        "_open_artifact_read_guard",
        transitive_read_must_not_start,
    )
    mutations = (
        ("source", "relative_path", "data/arbitrary-nonregistered.pdf"),
        (
            "statement_discovery",
            "path",
            "output/development/arbitrary-discovery.json",
        ),
    )
    for section, field, malicious_path in mutations:
        mutated = copy.deepcopy(native_payload)
        mutated[section][field] = malicious_path
        with pytest.raises(native.NativeTMObservationsError):
            native._producer_commit_replay(
                project_root=fixture.root,
                producer_commit=fixture.publication.payload["code"]["commit"],
                implementation=fixture.publication.payload["code"]["implementation"],
                native_document_relative=fixture.publication.payload["native_tm_document"]["path"],
                native_document_bytes=native._canonical_json_bytes(mutated),
                native_document_sha256=sha256_bytes(native._canonical_json_bytes(mutated)),
                native_document_payload=mutated,
                producer_policy=producer_policy,
                run_id=fixture.publication.payload["run_id"],
            )


def _assert_strict_load_rejects_final_symlink(fixture: _SyntheticPublication, target: Path) -> None:
    backup = target.with_name(f"{target.name}.real")
    target.rename(backup)
    target.symlink_to(backup.name)
    try:
        with pytest.raises(native.NativeTMObservationsError, match="symlink"):
            native.load_registered_native_tm_observations(
                fixture.output_path,
                project_root=fixture.root,
                expected_sha256=fixture.publication.sha256,
            )
    finally:
        target.unlink(missing_ok=True)
        backup.rename(target)


def _assert_strict_load_rejects_parent_symlink(
    fixture: _SyntheticPublication, target: Path
) -> None:
    parent = target.parent
    real_parent = parent.with_name(f"{parent.name}.real")
    parent.rename(real_parent)
    parent.symlink_to(real_parent.name, target_is_directory=True)
    try:
        with pytest.raises(native.NativeTMObservationsError, match="symlink"):
            native.load_registered_native_tm_observations(
                fixture.output_path,
                project_root=fixture.root,
                expected_sha256=fixture.publication.sha256,
            )
    finally:
        parent.unlink(missing_ok=True)
        real_parent.rename(parent)


def test_source_and_discovery_final_and_parent_symlink_aliases_fail_closed(
    synthetic_publication: _SyntheticPublication,
) -> None:
    fixture = synthetic_publication
    _assert_strict_load_rejects_final_symlink(fixture, fixture.source_path)
    _assert_strict_load_rejects_parent_symlink(fixture, fixture.source_path)
    _assert_strict_load_rejects_final_symlink(fixture, fixture.discovery_path)
    _assert_strict_load_rejects_parent_symlink(fixture, fixture.discovery_path)


def test_nested_native_name_replacement_is_detected_after_replay(
    synthetic_publication: _SyntheticPublication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = synthetic_publication
    backup = fixture.native_path.with_name("native-tm-document.backup.json")
    replacement = fixture.native_path.with_name("native-tm-document.replacement.json")
    os.link(fixture.native_path, backup)
    replacement.write_bytes(fixture.native_path.read_bytes())
    encoded = fixture.output_path.read_bytes()

    def replace_during_replay(**_kwargs: Any) -> bytes:
        os.replace(replacement, fixture.native_path)
        return encoded

    monkeypatch.setattr(native, "_producer_commit_replay", replace_during_replay)
    try:
        with pytest.raises(native.NativeTMObservationsError, match="changed"):
            native.load_registered_native_tm_observations(
                fixture.output_path,
                project_root=fixture.root,
                expected_sha256=fixture.publication.sha256,
            )
    finally:
        fixture.native_path.unlink(missing_ok=True)
        backup.rename(fixture.native_path)
        replacement.unlink(missing_ok=True)


@pytest.mark.parametrize("input_kind", ["source", "discovery"])
def test_transitive_input_name_replacement_is_detected_and_foreign_inode_survives(
    synthetic_publication: _SyntheticPublication,
    monkeypatch: pytest.MonkeyPatch,
    input_kind: str,
) -> None:
    fixture = synthetic_publication
    target = fixture.source_path if input_kind == "source" else fixture.discovery_path
    backup = target.with_name(f"{target.name}.{input_kind}.backup")
    replacement = target.with_name(f"{target.name}.{input_kind}.replacement")
    foreign_bytes = f"foreign-{input_kind}-replacement".encode()
    os.link(target, backup)
    replacement.write_bytes(foreign_bytes)
    original_run_checked_process = native._run_checked_process
    replacement_made = False

    def replace_during_replay(
        arguments: Any,
        *,
        cwd: Path,
        environment: Any,
        timeout: int = 900,
    ) -> bytes:
        nonlocal replacement_made
        if not replacement_made and len(arguments) > 1 and arguments[1] == "-I":
            os.replace(replacement, target)
            replacement_made = True
        return original_run_checked_process(
            arguments,
            cwd=cwd,
            environment=environment,
            timeout=timeout,
        )

    monkeypatch.setattr(native, "_run_checked_process", replace_during_replay)
    try:
        with pytest.raises(
            native.NativeTMObservationsError,
            match="transitive inputs changed",
        ):
            native.load_registered_native_tm_observations(
                fixture.output_path,
                project_root=fixture.root,
                expected_sha256=fixture.publication.sha256,
            )
        assert replacement_made is True
        assert target.read_bytes() == foreign_bytes
    finally:
        target.unlink(missing_ok=True)
        backup.rename(target)
        replacement.unlink(missing_ok=True)


def test_failed_post_publication_replay_rolls_back_only_created_inode(
    synthetic_publication: _SyntheticPublication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = synthetic_publication
    output = fixture.root / "output/development/observations/rollback.json"
    monkeypatch.setattr(
        native,
        "build_registered_native_tm_observations",
        lambda *_args, **_kwargs: fixture.publication.payload,
    )

    def reject_replay(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise native.NativeTMObservationsError("forced strict replay failure")

    monkeypatch.setattr(native, "load_registered_native_tm_observations", reject_replay)
    with pytest.raises(native.NativeTMObservationsError, match="forced strict replay"):
        native.publish_registered_native_tm_observations(
            fixture.root,
            fixture.native_path,
            fixture.native_sha256,
            fixture.policy_path,
            "rollback-test",
            output,
        )
    assert not output.exists()
