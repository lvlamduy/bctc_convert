from __future__ import annotations

import copy
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from bctc_ai.core.hashing import sha256_bytes
from bctc_ai.mapping import native_tm_canonical as canonical
from bctc_ai.rows import native_tm_observations


@pytest.fixture(scope="module")
def policy(project_root: Path) -> dict:
    return canonical.load_native_tm_canonical_mapping_policy(
        project_root / canonical.POLICY_RELATIVE_PATH,
        project_root,
    )


def _schema_bundle(*families: tuple[int, tuple[str, ...]]) -> tuple[list[dict], list[dict]]:
    records: list[dict] = []
    contexts: list[dict] = []
    used_ids: set[int] = set()

    def add(
        identifier: int,
        name: str,
        *,
        parent: int | None,
        children: list[int],
        family_root: int | None,
    ) -> None:
        assert identifier not in used_ids
        used_ids.add(identifier)
        display_order = len(records)
        records.append(
            {
                "schema_id": identifier,
                "canonical_name": name,
                "normalized_name": canonical.retrieval_key(name),
                "statement_type": "TM",
                "display_order": display_order,
                "parent_id": parent,
                "children": children,
                "allowed_period_type": ["SNAPSHOT"],
                "allowed_unit": [],
                "allowed_sign": ["POSITIVE", "NEGATIVE", "ZERO"],
                "scope": ["SEPARATE", "CONSOLIDATED"],
                "hierarchy_level": 1 if parent is None else 2,
                "structural_aliases": [],
            }
        )
        contexts.append(
            {
                "report_norm_id": identifier,
                "canonical_name": name,
                "statement_type": "TM",
                "section": "SYNTHETIC",
                "section_root_id": identifier if parent is None else parent,
                "note_family_root_id": family_root,
                "ancestor_path": [identifier] if parent is None else [parent, identifier],
                "parent_report_norm_id": parent,
                "hierarchy_level": 1 if parent is None else 2,
                "derived_hierarchy_level": 1 if parent is None else 2,
                "display_order": display_order,
                "context_status": "RESOLVED",
                "mapping_eligible": True,
            }
        )

    for root_id, labels in families:
        child_ids = [root_id + offset for offset in range(1, len(labels) + 1)]
        add(
            root_id,
            f"Synthetic family {root_id}",
            parent=None,
            children=child_ids,
            family_root=root_id,
        )
        for child_id, label in zip(child_ids, labels, strict=True):
            add(child_id, label, parent=root_id, children=[], family_root=root_id)
    next_id = 900_000
    while len(records) < 1713:
        while next_id in used_ids:
            next_id += 1
        add(
            next_id,
            f"Unrelated synthetic item {next_id}",
            parent=None,
            children=[],
            family_root=None,
        )
        next_id += 1
    return records, contexts


def _empty_observations() -> dict:
    page = {
        "record_type": "PAGE_CONTEXT",
        "source_object_id": "PAGE_CONTEXT::synthetic",
        "source_disposition": "QUANTITATIVE_TM",
        "page_id": "PAGE_CONTEXT::synthetic",
        "region_context_ids": [],
    }
    return {
        "format_version": "REGISTERED_NATIVE_TM_OBSERVATIONS_RESULT_V1",
        "policy": "REGISTERED_NATIVE_TM_OBSERVATIONS_V1",
        "claim_boundary": "SOURCE_ONLY_NATIVE_TM_OBSERVATION_FLATTENING",
        "status": "COMPLETE_NATIVE_TM_SOURCE_OBJECT_ACCOUNTING",
        "run_id": "synthetic-observations",
        "source": {"dataset_role": "LOGIC_DEVELOPMENT", "relative_path": "synthetic.pdf"},
        "code": {"commit": "0" * 40, "dirty": False, "implementation": []},
        "inputs": {},
        "producer_snapshots": {},
        "report_scope_binding": {
            "scope": "CONSOLIDATED",
            "binding_status": "RESOLVED_UNANIMOUS_SOURCE_VISIBLE_TM_HEADERS",
        },
        "source_accounting": {
            "source_object_accounting_complete": True,
            "full_document_context_complete": False,
        },
        "page_inventory": [page],
        "contexts": [],
        "rows": [],
        "dimensions": [],
        "observations": [],
        "source_evidence": {
            "inter_table_contexts": [],
            "geometry_runs": [],
            "inter_table_context_runs": [],
            "unassigned_page_runs": [],
            "excluded_spans": [],
            "detached_margin_runs": [],
            "unit_group_diagnostics": [],
        },
        "source_references": {"region_unassigned_runs": []},
        "source_dispositions": [
            {
                "source_object_id": page["source_object_id"],
                "source_object_type": page["record_type"],
                "source_disposition": page["source_disposition"],
            }
        ],
    }


def _add_table(
    payload: dict,
    *,
    table_key: str,
    labels: tuple[str, ...],
    values: tuple[int, ...] = (10, 20, 30),
    total: int | None = None,
    shared_run_owner: str | None = None,
) -> None:
    assert len(labels) == len(values)
    total = sum(values) if total is None else total
    context_id = f"CONTEXT::{table_key}"
    dimension_id = f"DIMENSION::{table_key}::axis"
    dimension = {
        "record_type": "DIMENSION",
        "source_object_id": dimension_id,
        "source_disposition": "QUANTITATIVE_TM",
        "dimension_id": dimension_id,
        "context_id": context_id,
        "source_table_id": table_key,
        "axis_id": "axis",
        "axis_ordinal": 0,
        "binding_status": "RESOLVED",
        "period_type": "SNAPSHOT",
        "period_start": "2030-12-31",
        "period_end": "2030-12-31",
        "unit": "VND",
        "unit_multiplier": 1,
        "period_materialization": {"resolution_status": "SOURCE_BINDING_RESOLVED"},
        "unit_materialization": {"resolution_status": "SOURCE_BINDING_RESOLVED"},
    }
    rows: list[dict] = []
    observations: list[dict] = []
    for ordinal, (label, value) in enumerate(
        [*zip(labels, values, strict=True), ("", total)], start=1
    ):
        row_id = f"{table_key}:row-{ordinal}"
        row_object_id = f"ROW::{row_id}"
        observation_id = f"OBSERVATION::{row_id}::axis"
        row = {
            "record_type": "ROW",
            "source_object_id": row_object_id,
            "source_disposition": "QUANTITATIVE_TM",
            "row_source_kind": "REGION_ROW",
            "context_id": context_id,
            "source_table_id": table_key,
            "page_classification": "QUANTITATIVE_TM",
            "row_id": row_id,
            "row_ordinal": ordinal,
            "label": label,
            "source_cells": [{"axis_id": "axis"}],
            "observation_ids": [observation_id],
            "value_bearing": True,
        }
        observation = {
            "record_type": "OBSERVATION",
            "source_object_id": observation_id,
            "source_disposition": "QUANTITATIVE_TM",
            "observation_id": observation_id,
            "observation_source_kind": "GRID_SLOT",
            "context_id": context_id,
            "row_id": row_id,
            "dimension_id": dimension_id,
            "source_table_id": table_key,
            "source_status": "OBSERVED_VALUE" if value else "OBSERVED_ZERO",
            "observation_kind": "VALUE" if value else "ZERO",
            "parsed": {"value": str(value)},
            "source_slot_record_sha256": f"{ordinal:064x}",
            "source_run_owner_id": (
                shared_run_owner if shared_run_owner is not None else f"RUN::{table_key}::{ordinal}"
            ),
        }
        rows.append(row)
        observations.append(observation)
    context = {
        "record_type": "CONTEXT",
        "source_object_id": context_id,
        "source_disposition": "QUANTITATIVE_TM",
        "context_id": context_id,
        "source_table_id": table_key,
        "page_classification": "QUANTITATIVE_TM",
        "row_ids": [row["row_id"] for row in rows],
        "dimension_ids": [dimension_id],
        "observation_ids": [record["observation_id"] for record in observations],
    }
    payload["contexts"].append(context)
    payload["rows"].extend(rows)
    payload["dimensions"].append(dimension)
    payload["observations"].extend(observations)
    payload["page_inventory"][0]["region_context_ids"].append(context_id)
    primary = [context, *rows, dimension, *observations]
    for record in primary:
        payload["source_dispositions"].append(
            {
                "source_object_id": record["source_object_id"],
                "source_object_type": record["record_type"],
                "source_disposition": record["source_disposition"],
            }
        )
    owners = {record["source_run_owner_id"] for record in observations}
    for owner_id in sorted(owners):
        if any(record["source_object_id"] == owner_id for record in payload["source_dispositions"]):
            continue
        source_run = {
            "run_id": owner_id,
            "raw_text": owner_id,
            "normalized_text": owner_id,
            "bbox": [0, 0, 1, 1],
            "block_number": 0,
            "line_number": 0,
            "word_indices": [],
        }
        payload["source_evidence"]["geometry_runs"].append(
            {
                "record_type": "SOURCE_RUN",
                "source_object_id": owner_id,
                "source_disposition": "QUANTITATIVE_TM",
                "evidence_id": owner_id,
                "source_record": source_run,
                "source_record_sha256": canonical._record_sha256(source_run),
            }
        )
        payload["source_dispositions"].append(
            {
                "source_object_id": owner_id,
                "source_object_type": "SOURCE_RUN",
                "source_disposition": "QUANTITATIVE_TM",
            }
        )


def _resolve(
    policy: dict,
    payload: dict,
    schema: list[dict],
    contexts: list[dict],
    aliases: tuple[dict, ...] = (),
) -> dict:
    return canonical._resolve_native_tm_canonical_mapping(
        payload,
        observations_sha256="a" * 64,
        tm_schema=schema,
        tm_contexts=contexts,
        accepted_typed_aliases=aliases,
        policy=policy,
    )


def test_zero_qualified_roots_is_valid_complete_disposition_artifact(policy: dict):
    schema, contexts = _schema_bundle()
    result = _resolve(policy, _empty_observations(), schema, contexts)

    assert result["accepted_subtrees"] == []
    assert result["root_assessments"] == []
    assert result["canonical_observations"] == []
    assert result["coverage"]["terminal_outcome_counts"]["UNRESOLVED"] == 1713
    assert result["coverage"]["reason_counts"] == {"UNASSESSED_OUTSIDE_BOUNDED_TABLE_SUBTREE": 1713}
    assert len(result["source_dispositions"]) == 1


def test_two_disjoint_roots_are_accepted_independently(policy: dict):
    family_a = (10_000, ("Alpha one", "Alpha two", "Alpha three", "Alpha absent"))
    family_b = (20_000, ("Beta one", "Beta two", "Beta three", "Beta absent"))
    schema, contexts = _schema_bundle(family_a, family_b)
    payload = _empty_observations()
    _add_table(payload, table_key="table-alpha", labels=family_a[1][:3])
    _add_table(payload, table_key="table-beta", labels=family_b[1][:3])

    result = _resolve(policy, payload, schema, contexts)

    assert [item["inferred_root_report_norm_id"] for item in result["accepted_subtrees"]] == [
        family_a[0],
        family_b[0],
    ]
    assert result["completion"]["accepted_root_count"] == 2
    assert result["coverage"]["terminal_outcome_counts"] == {
        "OBSERVED_VALUE": 8,
        "OBSERVED_ZERO": 0,
        "DASH": 0,
        "BLANK": 0,
        "NOT_OBSERVED": 2,
        "NOT_APPLICABLE": 0,
        "AMBIGUOUS": 0,
        "UNRESOLVED": 1703,
    }


def test_duplicate_same_root_is_local_and_does_not_harm_other_root(policy: dict):
    family_a = (30_000, ("Gamma one", "Gamma two", "Gamma three", "Gamma absent"))
    family_b = (40_000, ("Delta one", "Delta two", "Delta three", "Delta absent"))
    schema, contexts = _schema_bundle(family_a, family_b)
    payload = _empty_observations()
    _add_table(payload, table_key="gamma-first", labels=family_a[1][:3])
    _add_table(payload, table_key="gamma-second", labels=family_a[1][:3])
    _add_table(payload, table_key="delta-only", labels=family_b[1][:3])

    result = _resolve(policy, payload, schema, contexts)
    assessments = {
        record["inferred_root_report_norm_id"]: record for record in result["root_assessments"]
    }

    assert assessments[family_a[0]]["status"] == "AMBIGUOUS_MULTIPLE_SOURCE_CONTEXTS"
    assert assessments[family_b[0]]["status"] == "ACCEPTED"
    assert [item["inferred_root_report_norm_id"] for item in result["accepted_subtrees"]] == [
        family_b[0]
    ]
    by_id = {record["report_norm_id"]: record for record in result["schema_dispositions"]}
    assert by_id[family_a[0]]["terminal_outcome"] == "UNRESOLVED"
    assert by_id[family_a[0]]["reason"] == "AMBIGUOUS_MULTIPLE_CONTEXTS_CLAIM_ROOT"
    assert by_id[family_b[0]]["terminal_outcome"] == "OBSERVED_VALUE"


def test_equation_cannot_select_between_duplicate_root_claims(policy: dict):
    family = (50_000, ("Epsilon one", "Epsilon two", "Epsilon three", "Epsilon absent"))
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="epsilon-exact", labels=family[1][:3])
    _add_table(payload, table_key="epsilon-mismatch", labels=family[1][:3], total=999)

    result = _resolve(policy, payload, schema, contexts)

    assert result["accepted_subtrees"] == []
    assert result["root_assessments"][0]["status"] == "AMBIGUOUS_MULTIPLE_SOURCE_CONTEXTS"
    assert result["equation_checks"] == []


def test_cross_root_source_owner_collision_blocks_only_affected_roots(policy: dict):
    family_a = (60_000, ("Zeta one", "Zeta two", "Zeta three", "Zeta absent"))
    family_b = (70_000, ("Eta one", "Eta two", "Eta three", "Eta absent"))
    family_c = (80_000, ("Theta one", "Theta two", "Theta three", "Theta absent"))
    schema, contexts = _schema_bundle(family_a, family_b, family_c)
    payload = _empty_observations()
    _add_table(
        payload,
        table_key="zeta",
        labels=family_a[1][:3],
        shared_run_owner="RUN::shared-cross-root",
    )
    _add_table(
        payload,
        table_key="eta",
        labels=family_b[1][:3],
        shared_run_owner="RUN::shared-cross-root",
    )
    _add_table(payload, table_key="theta", labels=family_c[1][:3])

    result = _resolve(policy, payload, schema, contexts)
    statuses = {
        item["inferred_root_report_norm_id"]: item["status"] for item in result["root_assessments"]
    }

    assert statuses[family_a[0]] == "UNRESOLVED_SOURCE_OWNERSHIP_COLLISION"
    assert statuses[family_b[0]] == "UNRESOLVED_SOURCE_OWNERSHIP_COLLISION"
    assert statuses[family_c[0]] == "ACCEPTED"


def test_typed_alias_is_the_only_noncanonical_mapping_authority(policy: dict):
    family = (
        90_000,
        ("Canonical first", "Canonical second", "Canonical third", "Canonical absent"),
    )
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    alias_labels = ("Typed first", "Typed second", "Typed third")
    _add_table(payload, table_key="typed-alias", labels=alias_labels)
    aliases = tuple(
        {
            "statement_type": "TM",
            "report_norm_id": family[0] + offset,
            "alias": alias,
            "authority_type": "AUDITED_SCHEMA_ALIAS",
            "authority_evidence_sha256": f"{offset:064x}",
        }
        for offset, alias in enumerate(alias_labels, start=1)
    )

    without_aliases = _resolve(policy, payload, schema, contexts)
    with_aliases = _resolve(policy, payload, schema, contexts, aliases)

    assert without_aliases["accepted_subtrees"] == []
    assert with_aliases["completion"]["accepted_root_count"] == 1
    mapped_rows = [
        record
        for record in with_aliases["source_dispositions"]
        if record["source_object_type"] == "ROW"
        and record["mapping_disposition"] == "MAPPED_EXISTING_ITEM"
        and record["match_basis"] == "ACCEPTED_TYPED_ALIAS_RETRIEVAL_KEY_EXACT"
    ]
    assert len(mapped_rows) == 3
    assert all(record["alias_authority_type"] == "AUDITED_SCHEMA_ALIAS" for record in mapped_rows)


def test_canonical_and_typed_alias_global_key_collision_abstains(policy: dict):
    family = (
        95_000,
        ("Collision first", "Collision second", "Collision third", "Collision absent"),
    )
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="canonical-alias-collision", labels=family[1][:3])
    unrelated_id = schema[-1]["schema_id"]
    aliases = (
        {
            "statement_type": "TM",
            "report_norm_id": unrelated_id,
            "alias": family[1][0],
            "authority_type": "AUDITED_SCHEMA_ALIAS",
            "authority_evidence_sha256": "a" * 64,
        },
    )

    result = _resolve(policy, payload, schema, contexts, aliases)

    assert result["accepted_subtrees"] == []
    first_row = next(
        record
        for record in result["source_dispositions"]
        if record["source_object_type"] == "ROW"
        and record["row_id"] == "canonical-alias-collision:row-1"
    )
    assert first_row["candidate_report_norm_ids"] == [family[0] + 1, unrelated_id]


def test_source_and_table_title_metadata_never_selects_or_changes_targets(policy: dict):
    family = (97_000, ("Title one", "Title two", "Title three", "Title absent"))
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="title-metamorphism", labels=family[1][:3])
    baseline = _resolve(policy, payload, schema, contexts)

    payload["source"]["source_title"] = "Unrelated source title with arbitrary numbers 561"
    payload["contexts"][0]["table_title"] = "A different note and table title"
    payload["contexts"][0]["source_title"] = "Another arbitrary title"
    mutated = _resolve(policy, payload, schema, contexts)

    assert mutated["root_assessments"] == baseline["root_assessments"]
    assert mutated["accepted_subtrees"] == baseline["accepted_subtrees"]
    assert [item["report_norm_id"] for item in mutated["canonical_observations"]] == [
        item["report_norm_id"] for item in baseline["canonical_observations"]
    ]


@pytest.mark.parametrize(
    "source_labels",
    [
        ("1. Iota one", "2. Iota two", "3. Iota three"),
        ("Iota acct one", "Iota acct two", "Iota acct three"),
    ],
)
def test_enumerator_and_abbreviation_convenience_are_not_mapping_authority(
    policy: dict, source_labels: tuple[str, ...]
):
    family = (100_000, ("Iota one", "Iota two", "Iota three", "Iota absent"))
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="no-convenience", labels=source_labels)

    result = _resolve(policy, payload, schema, contexts)

    assert result["accepted_subtrees"] == []
    assert result["coverage"]["terminal_outcome_counts"]["UNRESOLVED"] == 1713


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "authorized_root_ids",
        "source_bank",
        "source_page",
        "source_note_number",
        "source_title",
        "expected_table_count",
    ],
)
def test_policy_rejects_source_or_expected_result_selectors(policy: dict, forbidden_key: str):
    mutated = copy.deepcopy(policy)
    mutated["routing"][forbidden_key] = []

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="routing.*drifted"):
        canonical._validate_policy_payload(mutated)


def test_production_policy_and_code_contain_no_gold_fixture_selectors(project_root: Path):
    policy_text = (project_root / canonical.POLICY_RELATIVE_PATH).read_text(encoding="utf-8")
    module_text = Path(canonical.__file__).read_text(encoding="utf-8")
    combined = f"{policy_text}\n{module_text}"

    assert "VPB" not in combined.upper()
    assert re.search(r"(?<![0-9])561(?![0-9])", combined) is None
    assert "expected_table_count" not in combined
    assert "accounting_abbreviation" in policy_text
    assert "accounting_abbreviation_expansion_allowed: false" in policy_text


def test_generic_anchor_floor_is_not_an_exact_source_count(policy: dict):
    family = (
        110_000,
        ("Kappa one", "Kappa two", "Kappa three", "Kappa four", "Kappa absent"),
    )
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(
        payload,
        table_key="four-anchors",
        labels=family[1][:4],
        values=(1, 2, 3, 4),
    )

    result = _resolve(policy, payload, schema, contexts)

    assert result["completion"]["accepted_root_count"] == 1
    assert result["coverage"]["terminal_outcome_counts"]["OBSERVED_VALUE"] == 5
    assert result["coverage"]["terminal_outcome_counts"]["NOT_OBSERVED"] == 1


def test_unique_root_equation_mismatch_abstains(policy: dict):
    family = (120_000, ("Lambda one", "Lambda two", "Lambda three", "Lambda absent"))
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="bad-equation", labels=family[1][:3], total=61)

    result = _resolve(policy, payload, schema, contexts)

    assert result["accepted_subtrees"] == []
    assert result["root_assessments"][0]["status"] == ("UNRESOLVED_LOCAL_COMPLETENESS_OR_EQUATION")
    assert result["root_assessments"][0]["blockers"] == ["EXACT_EQUATION_MISMATCH"]
    assert result["equation_checks"][0]["delta_source_units"] == "1"
    assert result["equation_checks"][0]["used_for_target_selection"] is False


def test_incompatible_absent_child_axis_blocks_local_not_observed(policy: dict):
    family = (125_000, ("Lambda A", "Lambda B", "Lambda C", "Lambda absent"))
    schema, contexts = _schema_bundle(family)
    absent = next(record for record in schema if record["schema_id"] == family[0] + 4)
    absent["allowed_unit"] = ["USD"]
    payload = _empty_observations()
    _add_table(payload, table_key="incompatible-absent", labels=family[1][:3])

    result = _resolve(policy, payload, schema, contexts)

    assert result["accepted_subtrees"] == []
    assert result["root_assessments"][0]["blockers"] == [
        "DIMENSION_OR_REPORT_SCOPE_INCOMPATIBLE_WITH_SCHEMA"
    ]
    assert result["coverage"]["terminal_outcome_counts"]["NOT_OBSERVED"] == 0


def test_mapped_value_sign_must_be_schema_compatible(policy: dict):
    family = (127_000, ("Lambda sign A", "Lambda sign B", "Lambda sign C", "Absent"))
    schema, contexts = _schema_bundle(family)
    first = next(record for record in schema if record["schema_id"] == family[0] + 1)
    first["allowed_sign"] = ["POSITIVE", "ZERO"]
    payload = _empty_observations()
    _add_table(
        payload,
        table_key="incompatible-sign",
        labels=family[1][:3],
        values=(-10, 20, 30),
    )

    result = _resolve(policy, payload, schema, contexts)

    assert result["accepted_subtrees"] == []
    assert result["root_assessments"][0]["blockers"] == ["VALUE_SIGN_INCOMPATIBLE_WITH_SCHEMA"]


def test_global_exact_label_collision_abstains_before_family_context(policy: dict):
    family = (130_000, ("Mu one", "Mu two", "Mu three", "Mu absent"))
    schema, contexts = _schema_bundle(family)
    schema[-1]["canonical_name"] = "Mu two"
    schema[-1]["normalized_name"] = canonical.retrieval_key("Mu two")
    contexts[-1]["canonical_name"] = "Mu two"
    payload = _empty_observations()
    _add_table(payload, table_key="global-collision", labels=family[1][:3])

    result = _resolve(policy, payload, schema, contexts)

    assert result["accepted_subtrees"] == []
    source_rows = {
        record["row_id"]: record
        for record in result["source_dispositions"]
        if record["source_object_type"] == "ROW"
    }
    assert source_rows["global-collision:row-2"]["candidate_report_norm_ids"] == [
        family[0] + 2,
        schema[-1]["schema_id"],
    ]


def test_typed_alias_requires_exact_evidence_receipt(policy: dict):
    family = (140_000, ("Nu one", "Nu two", "Nu three", "Nu absent"))
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="bad-alias", labels=("Alias one", "Nu two", "Nu three"))
    aliases = (
        {
            "statement_type": "TM",
            "report_norm_id": family[0] + 1,
            "alias": "Alias one",
            "authority_type": "AUDITED_SCHEMA_ALIAS",
            "authority_evidence_sha256": "not-a-sha",
        },
    )

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="alias.*authority"):
        _resolve(policy, payload, schema, contexts, aliases)


def _add_following_context(payload: dict, table_key: str, *, value_bearing: bool) -> None:
    row_id = f"{table_key}:following-row"
    row = {
        "record_type": "ROW",
        "source_object_id": f"ROW::{row_id}",
        "source_disposition": "UNRESOLVED_INTER_TABLE_OWNERSHIP",
        "row_source_kind": "INTER_TABLE_CONTEXT_ROW",
        "context_id": None,
        "source_table_id": None,
        "page_classification": "QUANTITATIVE_TM",
        "row_id": row_id,
        "row_ordinal": None,
        "label": "Unconsumed following heading",
        "source_cells": [{"synthetic": True}] if value_bearing else [],
        "observation_ids": [],
        "value_bearing": value_bearing,
    }
    evidence_id = f"INTER_TABLE_CONTEXT::{table_key}"
    evidence = {
        "record_type": "INTER_TABLE_CONTEXT",
        "source_object_id": evidence_id,
        "source_disposition": "UNRESOLVED_INTER_TABLE_OWNERSHIP",
        "evidence_id": evidence_id,
        "source_record": {
            "preceding_table_id": table_key,
            "following_table_id": f"{table_key}-next",
            "ownership_status": "UNRESOLVED_INTER_TABLE_OWNERSHIP",
            "source_row_ids": [row_id],
            "runs": [{"raw_text": "Unconsumed following heading"}],
        },
    }
    payload["rows"].append(row)
    payload["source_evidence"]["inter_table_contexts"].append(evidence)
    for record in (row, evidence):
        payload["source_dispositions"].append(
            {
                "source_object_id": record["source_object_id"],
                "source_object_type": record["record_type"],
                "source_disposition": record["source_disposition"],
            }
        )


def test_cell_free_following_context_permits_local_completion_without_routing(policy: dict):
    family = (150_000, ("Xi one", "Xi two", "Xi three", "Xi absent"))
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="cell-free-boundary", labels=family[1][:3])
    _add_following_context(payload, "cell-free-boundary", value_bearing=False)

    result = _resolve(policy, payload, schema, contexts)

    assert result["completion"]["accepted_root_count"] == 1
    boundary = result["accepted_subtrees"][0]["boundary_contexts"][0]
    assert boundary["cell_free_after_terminal"] is True
    assert boundary["heading_used_for_routing"] is False
    assert boundary["diagnostic_heading_resolution_required"] is False


def test_value_bearing_following_context_blocks_local_not_observed(policy: dict):
    family = (160_000, ("Omicron one", "Omicron two", "Omicron three", "Omicron absent"))
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="occupied-boundary", labels=family[1][:3])
    _add_following_context(payload, "occupied-boundary", value_bearing=True)

    result = _resolve(policy, payload, schema, contexts)

    assert result["accepted_subtrees"] == []
    assert (
        "FOLLOWING_INTER_TABLE_CONTEXT_HAS_VALUE_POSITION"
        in result["root_assessments"][0]["blockers"]
    )
    assert result["coverage"]["terminal_outcome_counts"]["NOT_OBSERVED"] == 0


def test_every_primary_source_object_requires_upstream_disposition(policy: dict):
    family = (170_000, ("Pi one", "Pi two", "Pi three", "Pi absent"))
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="missing-accounting", labels=family[1][:3])
    removed = payload["source_dispositions"].pop()
    assert removed["source_object_type"] == "SOURCE_RUN"
    payload["source_dispositions"] = [
        record
        for record in payload["source_dispositions"]
        if record["source_object_type"] != "OBSERVATION"
        or record["source_object_id"] != payload["observations"][0]["source_object_id"]
    ]

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="observations identity"):
        _resolve(policy, payload, schema, contexts)


def test_context_row_partition_must_cover_every_owned_source_row(policy: dict):
    family = (175_000, ("Rho one", "Rho two", "Rho three", "Rho absent"))
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="row-partition", labels=family[1][:3])
    omitted = payload["contexts"][0]["row_ids"].pop()
    assert any(row["row_id"] == omitted for row in payload["rows"])

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="row foreign keys"):
        _resolve(policy, payload, schema, contexts)


def test_observation_row_and_context_must_agree_exactly(policy: dict):
    family = (176_000, ("Sigma one", "Sigma two", "Sigma three", "Sigma absent"))
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="row-context-left", labels=family[1][:3])
    _add_table(payload, table_key="row-context-right", labels=family[1][:3])
    left_context, right_context = payload["contexts"]
    observation = payload["observations"][0]
    left_context["observation_ids"].remove(observation["observation_id"])
    right_context["observation_ids"].append(observation["observation_id"])
    observation["context_id"] = right_context["context_id"]
    observation["source_table_id"] = right_context["source_table_id"]
    observation["dimension_id"] = right_context["dimension_ids"][0]

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="observation foreign keys"):
        _resolve(policy, payload, schema, contexts)


def test_dimension_table_owner_must_equal_its_context(policy: dict):
    family = (177_000, ("Tau one", "Tau two", "Tau three", "Tau absent"))
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="dimension-owner", labels=family[1][:3])
    payload["dimensions"][0]["source_table_id"] = "different-table"

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="dimension foreign keys"):
        _resolve(policy, payload, schema, contexts)


def test_schema_and_context_denominator_requires_unique_exact_ids(policy: dict):
    schema, contexts = _schema_bundle()
    schema[-1]["schema_id"] = schema[0]["schema_id"]
    contexts[-1]["report_norm_id"] = contexts[0]["report_norm_id"]

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="denominator drifted"):
        _resolve(policy, _empty_observations(), schema, contexts)


def test_phantom_source_disposition_is_rejected(policy: dict):
    schema, contexts = _schema_bundle()
    payload = _empty_observations()
    payload["source_dispositions"].append(
        {
            "source_object_id": "SOURCE_RUN::phantom",
            "source_object_type": "SOURCE_RUN",
            "source_disposition": "QUANTITATIVE_TM",
        }
    )

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="partition drifted"):
        _resolve(policy, payload, schema, contexts)


def test_nested_source_evidence_requires_an_exact_disposition(policy: dict):
    schema, contexts = _schema_bundle()
    payload = _empty_observations()
    payload["source_evidence"]["geometry_runs"].append(
        {
            "record_type": "SOURCE_RUN",
            "source_object_id": "SOURCE_RUN::unledgered-evidence",
            "source_disposition": "QUANTITATIVE_TM",
            "source_record": {"run_id": "unledgered-evidence"},
        }
    )

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="evidence accounting"):
        _resolve(policy, payload, schema, contexts)


def test_nested_source_reference_requires_a_dispositioned_evidence_owner(policy: dict):
    schema, contexts = _schema_bundle()
    payload = _empty_observations()
    payload["source_references"]["region_unassigned_runs"].append(
        {
            "record_type": "SOURCE_RUN_REFERENCE",
            "reference_id": "SOURCE_RUN_REFERENCE::phantom",
            "owner_source_object_id": "SOURCE_RUN::phantom",
        }
    )

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="reference owner"):
        _resolve(policy, payload, schema, contexts)


@pytest.mark.parametrize("record_kind", ["primary", "evidence"])
def test_record_local_and_ledger_source_dispositions_must_match(policy: dict, record_kind: str):
    family = (178_000, ("Upsilon one", "Upsilon two", "Upsilon three", "Upsilon absent"))
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="disposition-match", labels=family[1][:3])
    if record_kind == "primary":
        payload["contexts"][0]["source_disposition"] = "OUTSIDE_QUANTITATIVE_TM"
        error = "contexts identity"
    else:
        payload["source_evidence"]["geometry_runs"][0]["source_disposition"] = (
            "OUTSIDE_QUANTITATIVE_TM"
        )
        error = "evidence accounting"

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match=error):
        _resolve(policy, payload, schema, contexts)


def test_following_context_evidence_must_be_in_source_dispositions(policy: dict):
    family = (179_000, ("Phi one", "Phi two", "Phi three", "Phi absent"))
    schema, contexts = _schema_bundle(family)
    payload = _empty_observations()
    _add_table(payload, table_key="following-evidence-ledger", labels=family[1][:3])
    _add_following_context(payload, "following-evidence-ledger", value_bearing=False)
    evidence_id = payload["source_evidence"]["inter_table_contexts"][0]["source_object_id"]
    payload["source_dispositions"] = [
        record
        for record in payload["source_dispositions"]
        if record["source_object_id"] != evidence_id
    ]

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="evidence accounting"):
        _resolve(policy, payload, schema, contexts)


def test_live_authority_bundle_is_exact_and_typed_alias_only(project_root: Path, policy: dict):
    guards, authority_bytes, ledger = canonical._open_runtime_authorities(project_root, policy)
    try:
        schema, contexts, aliases, identity = canonical._load_authority_bundle(
            authority_bytes, policy
        )
    finally:
        for guard in reversed(guards):
            canonical._close_guard(guard)

    assert len(schema) == len(contexts) == 1713
    assert len(aliases) == 2
    assert identity["typed_alias_projection_sha256"] == (
        "cea637baa097229d871656954f88902d4357915c44c9033f67372e70b9991ea1"
    )
    assert {record["authority_type"] for record in aliases} == {"USER_SUPPLIED_HIERARCHY_LABEL"}
    assert {record["kind"] for record in ledger} == set(
        policy["role_isolation"]["direct_runtime_input_kinds"]
    ) - {"NATIVE_TM_OBSERVATIONS_ARTIFACT", "THIS_POLICY"}


def test_real_observation_projection_discovers_the_gold_bundle_without_fixture_selectors(
    project_root: Path, policy: dict
):
    document_path = project_root / (
        "output/development/vpb-q1-2026-native-tm-document-v1/native-tm-document.json"
    )
    if not document_path.is_file():
        pytest.skip("registered real native TM document is not present")
    document_bytes = document_path.read_bytes()
    observation_policy_path = project_root / native_tm_observations.POLICY_RELATIVE_PATH
    observation_policy_bytes = observation_policy_path.read_bytes()
    observation_policy = native_tm_observations.load_native_tm_observations_policy(
        observation_policy_path, project_root
    )
    document_relative = document_path.relative_to(project_root).as_posix()
    document_identity = {
        "path": document_relative,
        "sha256": sha256_bytes(document_bytes),
        "size_bytes": len(document_bytes),
    }
    runtime_inputs = sorted(
        [
            {
                "kind": "NATIVE_TM_DOCUMENT_ARTIFACT",
                **document_identity,
            },
            {
                "kind": "THIS_POLICY",
                "path": native_tm_observations.POLICY_RELATIVE_PATH.as_posix(),
                "sha256": sha256_bytes(observation_policy_bytes),
                "size_bytes": len(observation_policy_bytes),
            },
        ],
        key=lambda record: (record["kind"], record["path"]),
    )
    projection = native_tm_observations._build_projection(
        native_document=json.loads(document_bytes),
        native_document_identity=document_identity,
        policy_relative=native_tm_observations.POLICY_RELATIVE_PATH.as_posix(),
        policy_bytes=observation_policy_bytes,
        policy=observation_policy,
        runtime_inputs=runtime_inputs,
        implementation=[
            {"path": path, "sha256": "0" * 64, "size_bytes": 0}
            for path in native_tm_observations._IMPLEMENTATION_PATHS
        ],
        producer_commit="0" * 40,
        run_id="real-mapper-regression",
    )
    guards, authority_bytes, _ledger = canonical._open_runtime_authorities(project_root, policy)
    try:
        schema, contexts, aliases, _identity = canonical._load_authority_bundle(
            authority_bytes, policy
        )
    finally:
        for guard in reversed(guards):
            canonical._close_guard(guard)
    projection_bytes = native_tm_observations._canonical_json_bytes(projection)

    result = canonical._resolve_native_tm_canonical_mapping(
        projection,
        observations_sha256=sha256_bytes(projection_bytes),
        tm_schema=schema,
        tm_contexts=contexts,
        accepted_typed_aliases=aliases,
        policy=policy,
    )

    assert result["source_accounting"]["upstream_source_object_count"] == 11032
    assert result["source_accounting"]["mapping_source_disposition_count"] == 11032
    assert result["completion"]["accepted_root_count"] == 1
    assert result["accepted_subtrees"][0]["inferred_root_report_norm_id"] == 561
    assert result["accepted_subtrees"][0]["anchor_report_norm_ids"] == [562, 563, 565]
    assert result["accepted_subtrees"][0]["not_observed_direct_child_report_norm_ids"] == [
        564,
        566,
        567,
        568,
    ]
    assert len(result["canonical_observations"]) == 8
    canonical_tuple_fields = (
        "report_norm_id",
        "reported_value",
        "canonical_value",
        "period_end",
        "unit",
        "unit_multiplier",
        "presentation_scope",
    )
    assert [
        tuple(record[field] for field in canonical_tuple_fields)
        for record in result["canonical_observations"]
    ] == [
        (561, "4065152", "4065152000000", "2026-03-31", "VND", 1_000_000, "CONSOLIDATED"),
        (561, "2774182", "2774182000000", "2025-12-31", "VND", 1_000_000, "CONSOLIDATED"),
        (562, "2970048", "2970048000000", "2026-03-31", "VND", 1_000_000, "CONSOLIDATED"),
        (562, "2292077", "2292077000000", "2025-12-31", "VND", 1_000_000, "CONSOLIDATED"),
        (563, "1094895", "1094895000000", "2026-03-31", "VND", 1_000_000, "CONSOLIDATED"),
        (563, "481921", "481921000000", "2025-12-31", "VND", 1_000_000, "CONSOLIDATED"),
        (565, "209", "209000000", "2026-03-31", "VND", 1_000_000, "CONSOLIDATED"),
        (565, "184", "184000000", "2025-12-31", "VND", 1_000_000, "CONSOLIDATED"),
    ]
    assert len(result["equation_checks"]) == 2
    assert {record["status"] for record in result["equation_checks"]} == {"EXACT"}
    boundary = result["accepted_subtrees"][0]["boundary_contexts"]
    assert len(boundary) == 1
    assert boundary[0]["cell_free_after_terminal"] is True
    assert boundary[0]["heading_used_for_routing"] is False
    assert result["coverage"]["terminal_outcome_counts"] == {
        "OBSERVED_VALUE": 4,
        "OBSERVED_ZERO": 0,
        "DASH": 0,
        "BLANK": 0,
        "NOT_OBSERVED": 4,
        "NOT_APPLICABLE": 0,
        "AMBIGUOUS": 0,
        "UNRESOLVED": 1705,
    }
    assert result["coverage"]["reason_counts"]["UNASSESSED_OUTSIDE_BOUNDED_TABLE_SUBTREE"] == 1705


def test_snapshot_envelope_detects_authority_record_tamper(project_root: Path, policy: dict):
    guards, authority_bytes, _ledger = canonical._open_runtime_authorities(project_root, policy)
    try:
        schema, contexts, aliases, _identity = canonical._load_authority_bundle(
            authority_bytes, policy
        )
    finally:
        for guard in reversed(guards):
            canonical._close_guard(guard)
    policy_bytes = (project_root / canonical.POLICY_RELATIVE_PATH).read_bytes()
    snapshots = canonical._producer_snapshots(
        policy_relative=canonical.POLICY_RELATIVE_PATH.as_posix(),
        policy_bytes=policy_bytes,
        policy=policy,
        schema=schema,
        contexts=contexts,
        aliases=aliases,
    )
    canonical._validate_snapshot_envelope(
        snapshots,
        producer_policy_bytes=policy_bytes,
        producer_policy=policy,
    )
    snapshots["tm_schema"]["records"][0]["canonical_name"] = "tampered"

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="snapshots drifted"):
        canonical._validate_snapshot_envelope(
            snapshots,
            producer_policy_bytes=policy_bytes,
            producer_policy=policy,
        )


@pytest.mark.parametrize(
    ("section", "field", "weakened_value"),
    [
        ("accepted_native_tm_observations", "exact_source_accounting_required", False),
        ("typed_alias_authority", "fuzzy_matching_allowed", True),
        ("routing", "minimum_distinct_direct_child_anchors", 2),
        ("routing", "zero_accepted_roots_allowed", False),
        ("local_completion", "require_every_context_row_accounted", False),
        ("coverage", "outside_bounded_subtree_reason", "UNASSESSED"),
        ("output", "rollback_after_failed_strict_replay", False),
    ],
)
def test_replay_policy_minimum_rejects_weakened_generic_gates(
    policy: dict, section: str, field: str, weakened_value: object
):
    weakened = copy.deepcopy(policy)
    weakened[section][field] = weakened_value

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="policy was weakened"):
        canonical._validate_replay_policy_minimum(weakened)


def test_replay_policy_minimum_does_not_depend_on_current_authority_hash(policy: dict):
    producer_policy = copy.deepcopy(policy)
    producer_policy["schema_authority"]["schema_registry"]["sha256"] = "0" * 64

    assert canonical._validate_replay_policy_minimum(producer_policy) == producer_policy


def test_replay_policy_rejects_forbidden_producer_authority_path_before_commit_read(
    policy: dict,
):
    producer_policy = copy.deepcopy(policy)
    producer_policy["schema_authority"]["schema_registry"]["path"] = (
        "output/development/role-a/schema-registry.json"
    )

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="role isolation"):
        canonical._validate_replay_policy_minimum(producer_policy)


@pytest.mark.parametrize(
    ("section", "selector_key", "selector_value"),
    [
        ("routing", "authorized_root_ids", [1]),
        ("routing", "source_title", "selected title"),
        ("routing", "source_page", 1),
        ("routing", "source_note_number", 2),
        ("routing", "source_table", "selected table"),
        ("routing", "expected_table_count", 1),
        ("routing", "bank_id", "selected bank"),
        ("routing", "source_filename", "selected.pdf"),
    ],
)
def test_replay_policy_minimum_rejects_historical_selector_fields(
    policy: dict, section: str, selector_key: str, selector_value: object
):
    producer_policy = copy.deepcopy(policy)
    producer_policy[section][selector_key] = selector_value

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="selector policy key"):
        canonical._validate_replay_policy_minimum(producer_policy)


@pytest.mark.parametrize(
    ("layer", "section", "selector_key", "selector_value"),
    [
        ("observations", "flattening", "source_title", "selected title"),
        ("observations", "role_isolation", "page_number_rules_used_for_routing", True),
        ("native", "classification", "source_table", "selected table"),
        ("native", "role_isolation", "bank_identity_used_for_routing", True),
    ],
)
def test_transitive_replay_policy_minima_reject_selector_semantics(
    project_root: Path,
    layer: str,
    section: str,
    selector_key: str,
    selector_value: object,
):
    if layer == "observations":
        path = project_root / canonical._OBSERVATION_POLICY_PATH
        validator = canonical._validate_observation_replay_policy_minimum
    else:
        path = project_root / canonical._NATIVE_DOCUMENT_POLICY_PATH
        validator = canonical._validate_native_replay_policy_minimum
    producer_policy = canonical._yaml_bytes(path.read_bytes(), f"{layer} producer policy")
    producer_policy[section][selector_key] = selector_value

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="selector policy key"):
        validator(producer_policy)


def test_isolated_producer_replay_uses_committed_helper_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    repository = tmp_path / "repository"
    repository.mkdir()

    def git(*arguments: str) -> str:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    git("init", "--quiet")
    git("config", "user.email", "native-tm-mapper@example.invalid")
    git("config", "user.name", "Native TM Mapper Test")
    (repository / ".gitignore").write_text("output/\n", encoding="utf-8")
    committed_helper = b"committed-helper-bytes\n"
    for relative in canonical._IMPLEMENTATION_PATHS:
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            committed_helper
            if relative == "src/bctc_ai/core/text.py"
            else f"committed::{relative}\n".encode()
        )
    git("add", ".")
    git("commit", "--quiet", "-m", "frozen producer")
    producer_commit = git("rev-parse", "HEAD")
    implementation = canonical._implementation_ledger_at_commit(repository, producer_commit)
    (repository / "src/bctc_ai/core/text.py").write_bytes(b"current-helper-is-broken\n")
    observations_relative = "output/development/observations/input.json"
    observations_bytes = b"frozen-observations\n"
    bootstrap = r"""
import pathlib
import sys

source_tree = pathlib.Path(sys.argv[1])
repository = pathlib.Path(sys.argv[2])
helper = (source_tree / "src/bctc_ai/core/text.py").read_bytes()
observations = (repository / sys.argv[3]).read_bytes()
sys.stdout.buffer.write(helper + b"|" + observations + b"|" + sys.argv[5].encode())
"""
    monkeypatch.setattr(canonical, "_PRODUCER_REPLAY_BOOTSTRAP", bootstrap)

    replayed = canonical._producer_commit_replay(
        project_root=repository,
        producer_commit=producer_commit,
        implementation=implementation,
        observations_relative=observations_relative,
        observations_bytes=observations_bytes,
        observations_sha256=sha256_bytes(observations_bytes),
        transitive_installs=[],
        run_id="isolated-replay",
    )

    assert replayed == committed_helper + b"|" + observations_bytes + b"|isolated-replay"


def _synthetic_loader_artifact(
    project_root: Path,
    tmp_path: Path,
    policy: dict,
    *,
    observation_payload: dict | None = None,
    schema: list[dict] | None = None,
    contexts: list[dict] | None = None,
    aliases: tuple[dict, ...] = (),
) -> tuple[Path, Path, dict, dict, bytes, bytes]:
    observation_payload = (
        _empty_observations() if observation_payload is None else observation_payload
    )
    observation_bytes = native_tm_observations._canonical_json_bytes(observation_payload)
    observation_path = tmp_path / "output/development/observations/input.json"
    observation_path.parent.mkdir(parents=True, exist_ok=True)
    observation_path.write_bytes(observation_bytes)
    if schema is None or contexts is None:
        schema, contexts = _schema_bundle()
    resolved = _resolve(policy, observation_payload, schema, contexts, aliases)
    policy_bytes = (project_root / canonical.POLICY_RELATIVE_PATH).read_bytes()
    producer_commit = "f" * 40
    observation_identity = {
        "kind": "NATIVE_TM_OBSERVATIONS_ARTIFACT",
        "path": observation_path.relative_to(tmp_path).as_posix(),
        "sha256": sha256_bytes(observation_bytes),
        "size_bytes": len(observation_bytes),
    }
    policy_identity = {
        "kind": "THIS_POLICY",
        "path": canonical.POLICY_RELATIVE_PATH.as_posix(),
        "sha256": sha256_bytes(policy_bytes),
        "size_bytes": len(policy_bytes),
    }
    ledger = sorted(
        [observation_identity, policy_identity],
        key=lambda record: (record["kind"], record["path"]),
    )
    inherited = {
        "inputs": copy.deepcopy(observation_payload["inputs"]),
        "inputs_sha256": canonical._record_sha256(observation_payload["inputs"]),
        "implementation": copy.deepcopy(observation_payload["code"]["implementation"]),
        "implementation_sha256": canonical._record_sha256(
            observation_payload["code"]["implementation"]
        ),
        "producer_snapshots": copy.deepcopy(observation_payload["producer_snapshots"]),
        "producer_snapshots_sha256": canonical._record_sha256(
            observation_payload["producer_snapshots"]
        ),
        "source_accounting": copy.deepcopy(observation_payload["source_accounting"]),
        "source_accounting_sha256": canonical._record_sha256(
            observation_payload["source_accounting"]
        ),
    }
    payload = {
        "format_version": "REGISTERED_NATIVE_TM_CANONICAL_MAPPING_RESULT_V1",
        "policy": "REGISTERED_NATIVE_TM_CANONICAL_MAPPING_V1",
        "claim_boundary": "BOUNDED_SOURCE_EVIDENCE_TM_CANONICAL_MAPPING_ONLY",
        "status": "COMPLETE_NATIVE_TM_CANONICAL_DISPOSITION_ACCOUNTING",
        "run_id": "synthetic-loader",
        "source": copy.deepcopy(observation_payload["source"]),
        "native_tm_observations": {
            "path": observation_identity["path"],
            "sha256": observation_identity["sha256"],
            "size_bytes": observation_identity["size_bytes"],
            "format_version": observation_payload["format_version"],
            "policy": observation_payload["policy"],
            "claim_boundary": observation_payload["claim_boundary"],
            "status": observation_payload["status"],
            "run_id": observation_payload["run_id"],
            "producer_git_commit": observation_payload["code"]["commit"],
        },
        "schema": {},
        "code": {"commit": producer_commit, "dirty": False, "implementation": []},
        "authority": {},
        "isolation": {},
        "non_decision_features": {},
        "inputs": {
            "direct_runtime_input_ledger": ledger,
            "direct_runtime_input_ledger_sha256": canonical._runtime_ledger_sha256(ledger),
            "inherited_upstream_replay_provenance": inherited,
        },
        "producer_snapshots": {},
        **resolved,
    }
    encoded = canonical._canonical_json_bytes(payload)
    artifact_path = tmp_path / "output/development/archive/native-tm-canonical.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(encoded)
    return artifact_path, observation_path, payload, observation_payload, encoded, policy_bytes


@pytest.fixture(scope="module")
def real_observation_lineage_repository(
    project_root: Path, tmp_path_factory: pytest.TempPathFactory
) -> dict:
    repository = tmp_path_factory.mktemp("native-tm-canonical-lineage") / "repository"
    subprocess.run(
        ["git", "clone", "--quiet", "--no-hardlinks", "--", str(project_root), str(repository)],
        check=True,
        capture_output=True,
    )
    document_relative = (
        "output/development/vpb-q1-2026-native-tm-document-v1/native-tm-document.json"
    )
    document_bytes = (project_root / document_relative).read_bytes()
    document_payload = json.loads(document_bytes)
    producer_commit = subprocess.run(
        [
            "git",
            "log",
            "-n1",
            "--format=%H",
            "--",
            canonical._OBSERVATION_POLICY_PATH,
            "src/bctc_ai/rows/native_tm_observations.py",
        ],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    policy_bytes = canonical._git_file_bytes(
        project_root, producer_commit, canonical._OBSERVATION_POLICY_PATH
    )
    observation_policy = canonical._validate_observation_replay_policy_minimum(
        canonical._yaml_bytes(policy_bytes, "observation fixture policy")
    )
    runtime_inputs = sorted(
        [
            {
                "kind": "NATIVE_TM_DOCUMENT_ARTIFACT",
                "path": document_relative,
                "sha256": sha256_bytes(document_bytes),
                "size_bytes": len(document_bytes),
            },
            canonical._file_identity_at_commit(
                project_root,
                producer_commit,
                canonical._OBSERVATION_POLICY_PATH,
                kind="THIS_POLICY",
            ),
        ],
        key=lambda record: (record["kind"], record["path"]),
    )
    implementation = [
        canonical._file_identity_at_commit(project_root, producer_commit, relative)
        for relative in canonical._OBSERVATION_IMPLEMENTATION_PATHS
    ]
    observation_payload = native_tm_observations._build_projection(
        native_document=document_payload,
        native_document_identity={
            "path": document_relative,
            "sha256": sha256_bytes(document_bytes),
            "size_bytes": len(document_bytes),
        },
        policy_relative=canonical._OBSERVATION_POLICY_PATH,
        policy_bytes=policy_bytes,
        policy=observation_policy,
        runtime_inputs=runtime_inputs,
        implementation=implementation,
        producer_commit=producer_commit,
        run_id="strict-loader-current-semantics-regression",
    )
    source_relative = document_payload["source"]["relative_path"]
    discovery_relative = document_payload["statement_discovery"]["path"]
    for relative, payload in (
        (document_relative, document_bytes),
        (source_relative, (project_root / source_relative).read_bytes()),
        (discovery_relative, (project_root / discovery_relative).read_bytes()),
    ):
        destination = repository / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
    return {
        "root": repository,
        "observation_payload": observation_payload,
        "document_path": repository / document_relative,
        "source_path": repository / source_relative,
        "discovery_path": repository / discovery_relative,
    }


def _real_loader_artifact(
    project_root: Path, policy: dict, fixture: dict
) -> tuple[Path, Path, dict, dict, bytes, bytes]:
    guards, authority_bytes, _ledger = canonical._open_runtime_authorities(project_root, policy)
    try:
        schema, contexts, aliases, _identity = canonical._load_authority_bundle(
            authority_bytes, policy
        )
    finally:
        for guard in reversed(guards):
            canonical._close_guard(guard)
    return _synthetic_loader_artifact(
        project_root,
        fixture["root"],
        policy,
        observation_payload=copy.deepcopy(fixture["observation_payload"]),
        schema=schema,
        contexts=contexts,
        aliases=tuple(aliases),
    )


def _bind_observation_to_native_payload(
    observation_payload: dict, native_payload: dict, native_bytes: bytes
) -> None:
    observation_payload["source"] = copy.deepcopy(native_payload["source"])
    native_identity = observation_payload["native_tm_document"]
    native_identity.update(
        {
            "sha256": sha256_bytes(native_bytes),
            "size_bytes": len(native_bytes),
            "format_version": native_payload["format_version"],
            "policy": native_payload["policy"],
            "claim_boundary": native_payload["claim_boundary"],
            "status": native_payload["status"],
            "run_id": native_payload["run_id"],
            "producer_git_commit": native_payload["code"]["commit"],
        }
    )
    ledger = observation_payload["inputs"]["direct_runtime_input_ledger"]
    native_record = next(
        record for record in ledger if record["kind"] == "NATIVE_TM_DOCUMENT_ARTIFACT"
    )
    native_record.update(
        {
            "path": native_identity["path"],
            "sha256": native_identity["sha256"],
            "size_bytes": native_identity["size_bytes"],
        }
    )
    ledger.sort(key=lambda record: (record["kind"], record["path"]))
    observation_payload["inputs"]["direct_runtime_input_ledger_sha256"] = (
        canonical._runtime_ledger_sha256(ledger)
    )
    observation_payload["inputs"]["inherited_upstream_replay_provenance"] = {
        "inputs": copy.deepcopy(native_payload["inputs"]),
        "inputs_sha256": canonical._record_sha256(native_payload["inputs"]),
        "implementation": copy.deepcopy(native_payload["code"]["implementation"]),
        "implementation_sha256": canonical._record_sha256(native_payload["code"]["implementation"]),
        "producer_snapshots": copy.deepcopy(native_payload["producer_snapshots"]),
        "producer_snapshots_sha256": canonical._record_sha256(native_payload["producer_snapshots"]),
        "inventories": {
            "completeness": copy.deepcopy(native_payload["completeness"]),
            "completeness_sha256": canonical._record_sha256(native_payload["completeness"]),
            "note_inventory": copy.deepcopy(native_payload["note_inventory"]),
            "note_inventory_sha256": canonical._record_sha256(native_payload["note_inventory"]),
            "table_inventory": copy.deepcopy(native_payload["table_inventory"]),
            "table_inventory_sha256": canonical._record_sha256(native_payload["table_inventory"]),
        },
    }


def _patch_synthetic_loader_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    policy: dict,
    observation_payload: dict,
    policy_bytes: bytes,
    patch_lineage: bool = True,
) -> None:
    producer_commit = "f" * 40
    original_git_file_bytes = canonical._git_file_bytes
    original_file_identity_at_commit = canonical._file_identity_at_commit
    policy_identity = {
        "path": canonical.POLICY_RELATIVE_PATH.as_posix(),
        "sha256": sha256_bytes(policy_bytes),
        "size_bytes": len(policy_bytes),
    }
    monkeypatch.setattr(
        canonical,
        "_validate_replay_implementation",
        lambda _project_root, _code: (producer_commit, []),
    )
    monkeypatch.setattr(
        canonical,
        "_git_file_bytes",
        lambda project_root, commit, relative: (
            policy_bytes
            if commit == producer_commit and relative == canonical.POLICY_RELATIVE_PATH.as_posix()
            else original_git_file_bytes(project_root, commit, relative)
        ),
    )
    monkeypatch.setattr(
        canonical,
        "_validate_replay_policy_minimum",
        lambda _payload: copy.deepcopy(policy),
    )
    monkeypatch.setattr(canonical, "_validate_snapshot_envelope", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(canonical, "_authority_specs", lambda _policy: [])

    def policy_identity_at_commit(
        project_root: Path,
        commit: str,
        relative: str,
        kind: str | None = None,
    ) -> dict:
        if commit == producer_commit and relative == canonical.POLICY_RELATIVE_PATH.as_posix():
            return {"kind": kind, **policy_identity} if kind is not None else policy_identity
        return original_file_identity_at_commit(project_root, commit, relative, kind=kind)

    monkeypatch.setattr(canonical, "_file_identity_at_commit", policy_identity_at_commit)
    if patch_lineage:
        monkeypatch.setattr(
            canonical,
            "_preflight_observation_replay_lineage",
            lambda **_kwargs: {
                "producer_commit": observation_payload["code"]["commit"],
                "implementation": [],
                "producer_policy": {},
                "native_identity": {},
                "native_relative": "output/development/native/document.json",
            },
        )
        monkeypatch.setattr(
            canonical,
            "_open_transitive_replay_guards",
            lambda *_args, **_kwargs: ([], []),
        )

    def current_observation_semantics_must_not_run(*_args, **_kwargs):
        raise AssertionError("current observation semantics ran")

    for name in (
        "load_registered_native_tm_observations",
        "build_registered_native_tm_observations",
        "_validate_policy_payload",
        "_validate_native_document",
        "_preflight_native_replay_lineage",
        "_canonical_json_bytes",
    ):
        monkeypatch.setattr(
            native_tm_observations,
            name,
            current_observation_semantics_must_not_run,
        )


def test_strict_loader_requires_byte_exact_producer_replay(
    monkeypatch: pytest.MonkeyPatch,
    project_root: Path,
    tmp_path: Path,
    policy: dict,
):
    artifact, _observations, payload, observation_payload, encoded, policy_bytes = (
        _synthetic_loader_artifact(project_root, tmp_path, policy)
    )
    _patch_synthetic_loader_dependencies(
        monkeypatch,
        policy=policy,
        observation_payload=observation_payload,
        policy_bytes=policy_bytes,
    )
    monkeypatch.setattr(canonical, "_producer_commit_replay", lambda **_kwargs: encoded)
    assert canonical.load_registered_native_tm_canonical_mapping(
        artifact,
        project_root=tmp_path,
        expected_sha256=sha256_bytes(encoded),
    ) == copy.deepcopy(payload)

    monkeypatch.setattr(canonical, "_producer_commit_replay", lambda **_kwargs: b"not-replayed")
    with pytest.raises(
        canonical.NativeTMCanonicalMappingError,
        match="producer-commit deterministic replay",
    ):
        canonical.load_registered_native_tm_canonical_mapping(
            artifact,
            project_root=tmp_path,
            expected_sha256=sha256_bytes(encoded),
        )


def test_strict_loader_uses_frozen_lineage_when_all_current_observation_semantics_explode(
    monkeypatch: pytest.MonkeyPatch,
    project_root: Path,
    policy: dict,
    real_observation_lineage_repository: dict,
):
    fixture = real_observation_lineage_repository
    artifact, _observations, payload, observation_payload, encoded, policy_bytes = (
        _real_loader_artifact(project_root, policy, fixture)
    )
    _patch_synthetic_loader_dependencies(
        monkeypatch,
        policy=policy,
        observation_payload=observation_payload,
        policy_bytes=policy_bytes,
        patch_lineage=False,
    )

    def current_mapper_semantics_must_not_run(*_args, **_kwargs):
        raise AssertionError("current mapper semantics ran")

    for name in (
        "_load_authority_bundle",
        "_load_tm_schema",
        "_derive_tm_context",
        "_candidate_index",
        "_resolve_native_tm_canonical_mapping",
    ):
        monkeypatch.setattr(canonical, name, current_mapper_semantics_must_not_run)
    monkeypatch.setattr(canonical, "_producer_commit_replay", lambda **_kwargs: encoded)

    loaded = canonical.load_registered_native_tm_canonical_mapping(
        artifact,
        project_root=fixture["root"],
        expected_sha256=sha256_bytes(encoded),
    )

    assert loaded == payload
    assert loaded["coverage"]["schema_item_count"] == 1713
    assert loaded["completion"]["accepted_root_count"] == 1


def test_unauthenticated_nested_native_path_is_rejected_before_any_live_read(
    monkeypatch: pytest.MonkeyPatch,
    real_observation_lineage_repository: dict,
):
    fixture = real_observation_lineage_repository
    observation_payload = copy.deepcopy(fixture["observation_payload"])
    malicious = "output/development/role-a/attacker-native.json"
    observation_payload["native_tm_document"]["path"] = malicious
    ledger = observation_payload["inputs"]["direct_runtime_input_ledger"]
    next(record for record in ledger if record["kind"] == "NATIVE_TM_DOCUMENT_ARTIFACT")["path"] = (
        malicious
    )
    ledger.sort(key=lambda record: (record["kind"], record["path"]))
    observation_payload["inputs"]["direct_runtime_input_ledger_sha256"] = (
        canonical._runtime_ledger_sha256(ledger)
    )

    def live_read_must_not_start(*_args, **_kwargs):
        raise AssertionError("live transitive read started before receipt authentication")

    monkeypatch.setattr(canonical, "_open_guard", live_read_must_not_start)

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="role isolation"):
        canonical._preflight_observation_replay_lineage(
            project_root=fixture["root"],
            observation_payload=observation_payload,
            observations_relative="output/development/observations/input.json",
        )


@pytest.mark.parametrize("input_kind", ["source", "discovery"])
def test_unauthenticated_source_or_discovery_path_is_never_opened(
    monkeypatch: pytest.MonkeyPatch,
    real_observation_lineage_repository: dict,
    input_kind: str,
):
    fixture = real_observation_lineage_repository
    observation_payload = copy.deepcopy(fixture["observation_payload"])
    original_native_bytes = fixture["document_path"].read_bytes()
    native_payload = json.loads(original_native_bytes)
    malicious = f"output/development/role-a/attacker-{input_kind}.json"
    ledger_kind = "SOURCE_PDF" if input_kind == "source" else "ACCEPTED_STATEMENT_DISCOVERY"
    if input_kind == "source":
        malicious = malicious.removesuffix(".json") + ".pdf"
        native_payload["source"]["relative_path"] = malicious
    else:
        native_payload["statement_discovery"]["path"] = malicious
    native_ledger = native_payload["inputs"]["runtime_read_ledger"]
    next(record for record in native_ledger if record["kind"] == ledger_kind)["path"] = malicious
    native_ledger.sort(key=lambda record: (record["kind"], record["path"]))
    native_payload["inputs"]["runtime_read_ledger_sha256"] = canonical._runtime_ledger_sha256(
        native_ledger
    )
    mutated_native_bytes = canonical._canonical_json_bytes(native_payload)
    _bind_observation_to_native_payload(observation_payload, native_payload, mutated_native_bytes)
    preflight = canonical._preflight_observation_replay_lineage(
        project_root=fixture["root"],
        observation_payload=observation_payload,
        observations_relative="output/development/observations/input.json",
    )
    fixture["document_path"].write_bytes(mutated_native_bytes)
    opened: list[str] = []
    original_open_guard = canonical._open_guard

    def record_live_read(project_root: Path, path: Path, relative: str, label: str):
        opened.append(relative)
        return original_open_guard(project_root, path, relative, label)

    monkeypatch.setattr(canonical, "_open_guard", record_live_read)
    try:
        with pytest.raises(canonical.NativeTMCanonicalMappingError, match="role isolation"):
            canonical._open_transitive_replay_guards(
                fixture["root"], observation_payload, preflight
            )
    finally:
        fixture["document_path"].write_bytes(original_native_bytes)

    assert opened == [preflight["native_relative"]]
    assert malicious not in opened


@pytest.mark.parametrize("target_kind", ["native", "source", "discovery"])
@pytest.mark.parametrize("alias_kind", ["final", "parent"])
def test_transitive_replay_inputs_reject_final_and_parent_symlink_aliases(
    real_observation_lineage_repository: dict,
    target_kind: str,
    alias_kind: str,
):
    fixture = real_observation_lineage_repository
    observation_payload = copy.deepcopy(fixture["observation_payload"])
    preflight = canonical._preflight_observation_replay_lineage(
        project_root=fixture["root"],
        observation_payload=observation_payload,
        observations_relative="output/development/observations/input.json",
    )
    target = fixture[f"{target_kind}_path"] if target_kind != "native" else fixture["document_path"]
    if alias_kind == "final":
        real_target = target.with_name(f"{target.name}.real")
        target.rename(real_target)
        target.symlink_to(real_target.name)
        try:
            with pytest.raises(canonical.NativeTMCanonicalMappingError, match="symlink|unreadable"):
                canonical._open_transitive_replay_guards(
                    fixture["root"], observation_payload, preflight
                )
        finally:
            target.unlink(missing_ok=True)
            real_target.rename(target)
    else:
        parent = target.parent
        real_parent = parent.with_name(f"{parent.name}.real")
        parent.rename(real_parent)
        parent.symlink_to(real_parent.name, target_is_directory=True)
        try:
            with pytest.raises(canonical.NativeTMCanonicalMappingError, match="symlink|unreadable"):
                canonical._open_transitive_replay_guards(
                    fixture["root"], observation_payload, preflight
                )
        finally:
            parent.unlink(missing_ok=True)
            real_parent.rename(parent)


@pytest.mark.parametrize("target_kind", ["native", "source", "discovery"])
def test_transitive_replay_time_name_swap_is_detected_and_foreign_inode_survives(
    monkeypatch: pytest.MonkeyPatch,
    project_root: Path,
    policy: dict,
    real_observation_lineage_repository: dict,
    target_kind: str,
):
    fixture = real_observation_lineage_repository
    artifact, _observations, _payload, observation_payload, encoded, policy_bytes = (
        _real_loader_artifact(project_root, policy, fixture)
    )
    _patch_synthetic_loader_dependencies(
        monkeypatch,
        policy=policy,
        observation_payload=observation_payload,
        policy_bytes=policy_bytes,
        patch_lineage=False,
    )
    target = fixture["document_path"] if target_kind == "native" else fixture[f"{target_kind}_path"]
    backup = target.with_name(f"{target.name}.{target_kind}.backup")
    replacement = target.with_name(f"{target.name}.{target_kind}.replacement")
    foreign_bytes = f"foreign-{target_kind}-replacement".encode()
    os.link(target, backup)
    replacement.write_bytes(foreign_bytes)

    def swap_during_replay(**_kwargs):
        os.replace(replacement, target)
        return encoded

    monkeypatch.setattr(canonical, "_producer_commit_replay", swap_during_replay)
    try:
        with pytest.raises(
            canonical.NativeTMCanonicalMappingError, match="changed during processing"
        ):
            canonical.load_registered_native_tm_canonical_mapping(
                artifact,
                project_root=fixture["root"],
                expected_sha256=sha256_bytes(encoded),
            )
        assert target.read_bytes() == foreign_bytes
    finally:
        target.unlink(missing_ok=True)
        backup.rename(target)
        replacement.unlink(missing_ok=True)


def test_semantic_observation_tamper_reaches_and_fails_frozen_mapper_replay(
    monkeypatch: pytest.MonkeyPatch,
    project_root: Path,
    policy: dict,
    real_observation_lineage_repository: dict,
):
    fixture = real_observation_lineage_repository
    artifact, observations, payload, observation_payload, _encoded, policy_bytes = (
        _real_loader_artifact(project_root, policy, fixture)
    )
    observation_payload["rows"][0]["label"] = "semantically tampered row label"
    observation_bytes = canonical._canonical_json_bytes(observation_payload)
    observations.write_bytes(observation_bytes)
    observation_identity = payload["native_tm_observations"]
    observation_identity.update(
        {"sha256": sha256_bytes(observation_bytes), "size_bytes": len(observation_bytes)}
    )
    ledger = payload["inputs"]["direct_runtime_input_ledger"]
    ledger_record = next(
        record for record in ledger if record["kind"] == "NATIVE_TM_OBSERVATIONS_ARTIFACT"
    )
    ledger_record.update(
        {"sha256": observation_identity["sha256"], "size_bytes": len(observation_bytes)}
    )
    ledger.sort(key=lambda record: (record["kind"], record["path"]))
    payload["inputs"]["direct_runtime_input_ledger_sha256"] = canonical._runtime_ledger_sha256(
        ledger
    )
    encoded = canonical._canonical_json_bytes(payload)
    artifact.write_bytes(encoded)
    _patch_synthetic_loader_dependencies(
        monkeypatch,
        policy=policy,
        observation_payload=observation_payload,
        policy_bytes=policy_bytes,
        patch_lineage=False,
    )
    replay_called = False

    def frozen_mapper_rejects_semantic_tamper(**_kwargs):
        nonlocal replay_called
        replay_called = True
        return b"frozen producer rejected observation semantics"

    monkeypatch.setattr(canonical, "_producer_commit_replay", frozen_mapper_rejects_semantic_tamper)

    with pytest.raises(
        canonical.NativeTMCanonicalMappingError,
        match="producer-commit deterministic replay",
    ):
        canonical.load_registered_native_tm_canonical_mapping(
            artifact,
            project_root=fixture["root"],
            expected_sha256=sha256_bytes(encoded),
        )
    assert replay_called is True


@pytest.mark.parametrize("swap_target", ["artifact", "observations"])
def test_strict_loader_detects_replay_time_name_swap_and_preserves_replacement(
    monkeypatch: pytest.MonkeyPatch,
    project_root: Path,
    tmp_path: Path,
    policy: dict,
    swap_target: str,
):
    artifact, observations, _payload, observation_payload, encoded, policy_bytes = (
        _synthetic_loader_artifact(project_root, tmp_path, policy)
    )
    _patch_synthetic_loader_dependencies(
        monkeypatch,
        policy=policy,
        observation_payload=observation_payload,
        policy_bytes=policy_bytes,
    )
    target = artifact if swap_target == "artifact" else observations
    replacement = target.with_name(f"{target.name}.replacement")
    foreign_bytes = f"foreign-{swap_target}-replacement".encode()
    replacement.write_bytes(foreign_bytes)

    def swap_during_replay(**_kwargs):
        os.replace(replacement, target)
        return encoded

    monkeypatch.setattr(canonical, "_producer_commit_replay", swap_during_replay)

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="changed during processing"):
        canonical.load_registered_native_tm_canonical_mapping(
            artifact,
            project_root=tmp_path,
            expected_sha256=sha256_bytes(encoded),
        )
    assert target.read_bytes() == foreign_bytes


def test_loader_rejects_parent_and_final_symlink_aliases(tmp_path: Path):
    real_parent = tmp_path / "output" / "development" / "real"
    real_parent.mkdir(parents=True)
    artifact = real_parent / "native-tm-canonical.json"
    artifact.write_text("{}\n", encoding="utf-8")
    alias_parent = tmp_path / "output" / "development" / "alias"
    alias_parent.symlink_to(real_parent, target_is_directory=True)

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="symlink|unreadable"):
        canonical.load_registered_native_tm_canonical_mapping(
            alias_parent / artifact.name,
            project_root=tmp_path,
            expected_sha256="0" * 64,
        )
    final_alias = tmp_path / "output" / "development" / "final-alias.json"
    final_alias.symlink_to(artifact)
    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="symlink|unreadable"):
        canonical.load_registered_native_tm_canonical_mapping(
            final_alias,
            project_root=tmp_path,
            expected_sha256="0" * 64,
        )


@pytest.mark.parametrize(
    "forbidden_directory",
    [
        "role-a",
        "role_a",
        "human_review",
        "human-review",
        "review",
        "history",
        "holdout",
        "comparisons",
    ],
)
def test_loader_rejects_forbidden_lexical_role_paths(tmp_path: Path, forbidden_directory: str):
    artifact = (
        tmp_path / "output" / "development" / forbidden_directory / "native-tm-canonical.json"
    )
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n", encoding="utf-8")

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="role isolation"):
        canonical.load_registered_native_tm_canonical_mapping(
            artifact,
            project_root=tmp_path,
            expected_sha256=sha256_bytes(artifact.read_bytes()),
        )


def test_loader_permits_benign_development_sibling_path(tmp_path: Path):
    artifact = tmp_path / "output/development/archive/native-tm-canonical.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n", encoding="utf-8")

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="envelope drifted"):
        canonical.load_registered_native_tm_canonical_mapping(
            artifact,
            project_root=tmp_path,
            expected_sha256=sha256_bytes(artifact.read_bytes()),
        )


def test_publication_is_exclusive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    output = tmp_path / "output" / "development" / "mapping.json"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"foreign-existing")
    payload = {"synthetic": True}
    monkeypatch.setattr(
        canonical, "build_registered_native_tm_canonical_mapping", lambda *_args: payload
    )
    monkeypatch.setattr(
        canonical, "load_registered_native_tm_canonical_mapping", lambda *_args, **_kwargs: payload
    )

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="overwrite|exists"):
        canonical.publish_registered_native_tm_canonical_mapping(
            tmp_path,
            tmp_path / "unused.json",
            "a" * 64,
            tmp_path / "unused.yaml",
            "synthetic",
            output,
        )
    assert output.read_bytes() == b"foreign-existing"


def test_publication_rejects_forbidden_role_path_before_build(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    def build_must_not_start(*_args, **_kwargs):
        raise AssertionError("build started for a forbidden publication path")

    monkeypatch.setattr(
        canonical, "build_registered_native_tm_canonical_mapping", build_must_not_start
    )

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="role isolation"):
        canonical.publish_registered_native_tm_canonical_mapping(
            tmp_path,
            tmp_path / "unused.json",
            "a" * 64,
            tmp_path / "unused.yaml",
            "synthetic",
            tmp_path / "output/development/role-a/mapping.json",
        )


def test_foreign_replacement_survives_failed_post_publication_replay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    output = tmp_path / "output" / "development" / "mapping.json"
    payload = {"synthetic": True}
    replacement = b"foreign-replacement"
    monkeypatch.setattr(
        canonical, "build_registered_native_tm_canonical_mapping", lambda *_args: payload
    )

    def fail_after_swap(path: Path, **_kwargs):
        path.unlink()
        path.write_bytes(replacement)
        raise canonical.NativeTMCanonicalMappingError("forced replay failure")

    monkeypatch.setattr(canonical, "load_registered_native_tm_canonical_mapping", fail_after_swap)

    with pytest.raises(canonical.NativeTMCanonicalMappingError):
        canonical.publish_registered_native_tm_canonical_mapping(
            tmp_path,
            tmp_path / "unused.json",
            "a" * 64,
            tmp_path / "unused.yaml",
            "synthetic",
            output,
        )
    assert output.read_bytes() == replacement


def test_failed_post_publication_replay_removes_only_created_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    output = tmp_path / "output" / "development" / "mapping.json"
    payload = {"synthetic": True}
    monkeypatch.setattr(
        canonical, "build_registered_native_tm_canonical_mapping", lambda *_args: payload
    )

    def reject_replay(*_args, **_kwargs):
        raise canonical.NativeTMCanonicalMappingError("forced replay failure")

    monkeypatch.setattr(canonical, "load_registered_native_tm_canonical_mapping", reject_replay)

    with pytest.raises(canonical.NativeTMCanonicalMappingError, match="forced replay failure"):
        canonical.publish_registered_native_tm_canonical_mapping(
            tmp_path,
            tmp_path / "unused.json",
            "a" * 64,
            tmp_path / "unused.yaml",
            "synthetic",
            output,
        )
    assert not output.exists()
