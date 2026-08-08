from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.mapping import tm_note_page34_mapping as page34
from bctc_ai.mapping import tm_note_page36_mapping as page36
from bctc_ai.mapping import tm_note_page41_mapping as page41
from bctc_ai.mapping import tm_note_page42_mapping as page42
from bctc_ai.mapping import tm_note_page43_mapping as page43
from bctc_ai.mapping import tm_note_page44_mapping as page44
from bctc_ai.mapping import tm_note_page46_mapping as page46
from bctc_ai.mapping import tm_note_page47_mapping as page47
from bctc_ai.mapping import tm_note_page48_mapping as page48
from bctc_ai.mapping import tm_note_page49_mapping as page49
from bctc_ai.mapping import tm_note_page50_mapping as page50
from bctc_ai.mapping import tm_note_page51_mapping as page51
from bctc_ai.mapping import tm_note_page52_mapping as page52
from bctc_ai.mapping import tm_note_page53_mapping as page53
from bctc_ai.mapping import tm_note_page54_mapping as page54
from bctc_ai.mapping import tm_note_page57_mapping as page57
from bctc_ai.mapping import tm_note_page58_mapping as page58
from bctc_ai.mapping import tm_note_page60_mapping as page60
from bctc_ai.mapping import tm_note_page61_mapping as page61
from bctc_ai.mapping import tm_note_pages32_33_mapping as pages32_33
from bctc_ai.mapping import tm_note_pages37_38_mapping as pages37_38
from bctc_ai.mapping import tm_note_pages39_40_mapping as pages39_40
from bctc_ai.mapping.tm_note_mapping import (
    TM_PAGE30_FIXED_IDS,
    TM_PAGE30_NOT_OBSERVED_IDS,
)
from bctc_ai.mapping.tm_note_page31_mapping import load_tm_page31_mapping_policy
from bctc_ai.mapping.tm_note_page35_mapping import load_tm_page35_mapping_policy
from bctc_ai.mapping.tm_note_residual_mapping import (
    TM_RESIDUAL_SCOPE_IDS,
    TMOwnedSchemaPartition,
    TMResidualMappingError,
    load_tm_residual_mapping_policy,
    reconcile_tm_residual_items,
    validate_tm_full_schema_partition,
)
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import load_all

_SOURCE_PDF = Path("vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf")
_SCHEMA_WORKBOOK = Path("template/Bank_TM_ReportNormId.v2.xlsx")


def _owned(
    owner_scope: str,
    *,
    mapped: set[int] | frozenset[int],
    unresolved: set[int] | frozenset[int] = frozenset(),
    not_observed: set[int] | frozenset[int] = frozenset(),
    not_applicable: set[int] | frozenset[int] = frozenset(),
) -> TMOwnedSchemaPartition:
    return TMOwnedSchemaPartition(
        owner_scope=owner_scope,
        mapped_ids=frozenset(mapped),
        unresolved_ids=frozenset(unresolved),
        not_observed_ids=frozenset(not_observed),
        not_applicable_ids=frozenset(not_applicable),
    )


def _page31_partition(project_root: Path) -> TMOwnedSchemaPartition:
    policy = load_tm_page31_mapping_policy(project_root / "config/mapping/tm-note-page31-v1.yaml")
    mapped = {
        schema_id
        for rule in policy.rows
        for schema_id in (
            *((rule.report_norm_id,) if rule.report_norm_id is not None else ()),
            *rule.additional_report_norm_ids,
        )
    }
    return _owned(
        "page-0031",
        mapped=mapped,
        not_observed=set(policy.not_observed_schema_ids),
        not_applicable=set(policy.not_applicable_schema_ids),
    )


def _page35_partition(project_root: Path) -> TMOwnedSchemaPartition:
    policy = load_tm_page35_mapping_policy(project_root / "config/mapping/tm-note-page35-v1.yaml")
    mapped = {rule.report_norm_id for rule in policy.rows if rule.report_norm_id is not None}
    return _owned(
        "page-0035",
        mapped=mapped,
        not_observed=set(policy.not_observed_schema_ids),
    )


def _base_page_partitions(project_root: Path) -> list[TMOwnedSchemaPartition]:
    return [
        _owned(
            "page-0030",
            mapped=set(TM_PAGE30_FIXED_IDS),
            not_observed=set(TM_PAGE30_NOT_OBSERVED_IDS),
        ),
        _page31_partition(project_root),
        _owned(
            "pages-0032-0033",
            mapped=pages32_33._MAPPED_IDS,
            not_observed=pages32_33._NOT_OBSERVED_IDS,
        ),
        _owned(
            "page-0034",
            mapped=page34._MAPPED_IDS,
            not_observed=page34._NOT_OBSERVED_IDS,
        ),
        _page35_partition(project_root),
        _owned(
            "page-0036",
            mapped=page36._MAPPED_IDS,
            not_observed=page36._SCOPED_IDS - page36._MAPPED_IDS,
        ),
        _owned(
            "pages-0037-0038",
            mapped=pages37_38._MAPPED_IDS,
            unresolved=pages37_38._UNRESOLVED_IDS,
            not_observed=pages37_38._NOT_OBSERVED_IDS,
        ),
        _owned(
            "pages-0039-0040",
            mapped=pages39_40._MAPPED_IDS,
            unresolved=pages39_40._UNRESOLVED_IDS,
            not_observed=pages39_40._NOT_OBSERVED_IDS,
        ),
        _owned(
            "page-0041",
            mapped=page41._MAPPED_IDS,
            unresolved=page41._UNRESOLVED_IDS,
            not_observed=page41._NOT_OBSERVED_IDS,
        ),
        _owned(
            "page-0042",
            mapped=page42._MAPPED_IDS,
            unresolved=page42._AMBIGUOUS_IDS,
            not_observed=page42._SCOPED_IDS - page42._MAPPED_IDS - page42._AMBIGUOUS_IDS,
        ),
        _owned(
            "page-0043",
            mapped=page43._MAPPED_IDS,
            unresolved=page43._AMBIGUOUS_IDS,
            not_observed=page43._SCOPED_IDS - page43._MAPPED_IDS - page43._AMBIGUOUS_IDS,
        ),
        _owned(
            "page-0044",
            mapped=page44._MAPPED_IDS,
            unresolved=page44._AMBIGUOUS_IDS | page44._UNRESOLVED_IDS,
            not_observed=page44._NOT_OBSERVED_IDS,
        ),
        _owned(
            "page-0046",
            mapped=page46._MAPPED_IDS,
            unresolved=page46._AMBIGUOUS_IDS,
            not_observed=page46._NOT_OBSERVED_IDS,
        ),
        _owned(
            "page-0047",
            mapped=page47._MAPPED_IDS,
            unresolved=page47._AMBIGUOUS_IDS,
            not_observed=page47._NOT_OBSERVED_IDS,
        ),
        _owned(
            "page-0048",
            mapped=page48._MAPPED_IDS,
            not_observed=page48._NOT_OBSERVED_IDS,
        ),
        _owned(
            "page-0049",
            mapped=page49._MAPPED_IDS,
            unresolved=page49._AMBIGUOUS_IDS,
            not_observed=page49._NOT_OBSERVED_IDS,
        ),
        _owned(
            "page-0050",
            mapped=page50._MAPPED_IDS,
            not_observed=page50._NOT_OBSERVED_IDS,
        ),
        _owned(
            "page-0051",
            mapped=page51._MAPPED_IDS,
            not_observed=page51._NOT_OBSERVED_IDS,
        ),
        _owned(
            "page-0052",
            mapped=page52._MAPPED_IDS,
            not_observed=page52._NOT_OBSERVED_IDS,
        ),
        _owned("page-0053", mapped=page53._SCOPE_IDS),
        _owned("page-0054", mapped=page54._SCOPE_IDS),
        _owned(
            "page-0057",
            mapped=page57._MAPPED_IDS,
            not_observed=page57._NOT_OBSERVED_IDS,
        ),
        _owned(
            "page-0058",
            mapped=page58._MAPPED_IDS,
            not_observed=page58._NOT_OBSERVED_IDS,
        ),
        _owned(
            "page-0060",
            mapped=page60.TM_PAGE60_MAPPED_SCHEMA_IDS,
            not_observed=page60.TM_PAGE60_NOT_OBSERVED_SCHEMA_IDS,
        ),
        _owned(
            "page-0061",
            mapped=page61.TM_PAGE61_MAPPED_SCHEMA_IDS,
            not_observed=page61.TM_PAGE61_NOT_OBSERVED_SCHEMA_IDS,
        ),
    ]


def test_all_26_tm_owners_are_pairwise_disjoint_and_exhaustive(project_root: Path) -> None:
    _, schema = load_all(project_root / "template", project_root)
    _, hierarchy = load_hierarchy_reference(
        project_root / "config/schemas/hierarchy_reference.yaml",
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    page_partitions = _base_page_partitions(project_root)
    existing_owned_ids = set().union(*(partition.scope_ids for partition in page_partitions))
    assert len(page_partitions) == 25
    assert len(existing_owned_ids) == 1_528
    assert not existing_owned_ids & TM_RESIDUAL_SCOPE_IDS

    residual = reconcile_tm_residual_items(
        schema,
        policy=load_tm_residual_mapping_policy(
            project_root / "config/mapping/tm-note-residual-v1.yaml"
        ),
        project_root=project_root,
        source_pdf_path=project_root / _SOURCE_PDF,
        schema_workbook_path=project_root / _SCHEMA_WORKBOOK,
        existing_owned_schema_ids=existing_owned_ids,
    )
    aggregate = validate_tm_full_schema_partition(
        schema,
        [*page_partitions, residual.owned_partition],
    )

    assert aggregate.schema_item_count == 1_613
    assert aggregate.owner_scope_count == 26
    assert aggregate.mapped_schema_count == 799
    assert aggregate.unresolved_schema_count == 85
    assert aggregate.not_observed_schema_count == 706
    assert aggregate.not_applicable_schema_count == 23
    assert aggregate.unassessed_schema_count == 0
    assert aggregate.ownership_sha256 == (
        "0a63d0eceb3265e5f03328e86bab2990fc1ad70c290b693a42fb6f8ba80f33f3"
    )


def test_full_partition_validator_rejects_any_duplicate_owner(project_root: Path) -> None:
    _, schema = load_all(project_root / "template", project_root)
    partitions = _base_page_partitions(project_root)
    with pytest.raises(TMResidualMappingError, match="pairwise disjoint"):
        validate_tm_full_schema_partition(schema, [*partitions, partitions[0]])
