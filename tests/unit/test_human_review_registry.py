from __future__ import annotations

from collections import Counter
from decimal import Decimal

from bctc_ai.core.contracts import ValueStatus
from bctc_ai.reference.human_review import (
    TemplateMembership,
    load_human_review_registry,
    verify_human_review_source_files,
)
from bctc_ai.schema.registry import load_all


def _registry(project_root):
    return load_human_review_registry(
        project_root / "config/reference/human-review-v1.yaml", project_root
    )


def test_reviewed_registry_is_hash_bound_and_semantically_complete(project_root):
    registry = _registry(project_root)
    assert registry.review_id == "HR-2026-08-06-CTG-ACB-MBB"
    assert registry.dataset_sha256 == (
        "32c86c0bf7642d3bd7596225331fc6f10906970476e1a9ba982b2f478d0f8e74"
    )
    assert len(registry.documents) == 3
    assert len(registry.decisions) == 30
    counts = Counter(decision.value_status for decision in registry.decisions)
    assert counts == {
        ValueStatus.OBSERVED_VALUE: 12,
        ValueStatus.OBSERVED_ZERO: 6,
        ValueStatus.NOT_OBSERVED: 1,
        ValueStatus.OUT_OF_SCOPE_FOR_TARGET_TEMPLATE: 11,
    }
    assert (
        sum(
            decision.current is not None and decision.comparative is not None
            for decision in registry.decisions
        )
        == 29
    )


def test_ctg_period_orientation_and_zero_absence_scope_are_distinct(project_root):
    registry = _registry(project_root)
    ctg = next(document for document in registry.documents if document.bank == "CTG")
    periods = ctg.period_maps[0]
    assert len(ctg.period_maps) == 2
    assert periods.applies_to_pages == (4,)
    assert ctg.period_maps[1].applies_to_pages == (5,)
    assert periods.column_for_role("CURRENT").side == "LEFT"
    assert periods.column_for_role("CURRENT").period_end.isoformat() == "2026-06-30"
    assert periods.column_for_role("COMPARATIVE").side == "RIGHT"
    assert periods.column_for_role("COMPARATIVE").period_end.isoformat() == "2025-12-31"

    by_id = {decision.reviewed_item_id: decision for decision in ctg.decisions}
    assert by_id[4340].current.normalized_numeric_value == Decimal(0)
    assert by_id[4340].current.raw_value == "-"
    assert by_id[4337].value_status is ValueStatus.NOT_OBSERVED
    assert by_id[4337].current is None
    assert by_id[4373].value_status is ValueStatus.OBSERVED_ZERO
    assert by_id[4373].metadata["forbidden_duplicate_id"] == 4337
    assert by_id[5711].value_status is ValueStatus.OUT_OF_SCOPE_FOR_TARGET_TEMPLATE
    assert by_id[5711].metadata["forbidden_target_id"] == 4366


def test_reviewed_numeric_digit_corrections_are_exact(project_root):
    registry = _registry(project_root)
    mbb = next(document for document in registry.documents if document.bank == "MBB")
    by_id = {decision.reviewed_item_id: decision for decision in mbb.decisions}
    assert by_id[4317].comparative.normalized_numeric_value == Decimal(468396)
    assert by_id[4357].comparative.normalized_numeric_value == Decimal(13549018)
    assert by_id[4335].comparative.normalized_numeric_value == Decimal(34339)
    assert by_id[4366].comparative.normalized_numeric_value == Decimal(7894091)
    acb = next(document for document in registry.documents if document.bank == "ACB")
    acb_by_id = {decision.reviewed_item_id: decision for decision in acb.decisions}
    assert acb_by_id[4368].current.raw_value == "(3.801.708)"
    assert acb_by_id[4368].current.normalized_numeric_value == Decimal(-3801708)


def test_external_off_balance_reference_ids_do_not_collide_with_any_template(project_root):
    registry = _registry(project_root)
    _, schema = load_all(project_root / "template", project_root)
    schema_ids = {item.schema_id for item in schema}
    outside_ids = {
        decision.reviewed_item_id
        for decision in registry.decisions
        if decision.template_membership is TemplateMembership.OUTSIDE_CURRENT_TARGET_TEMPLATE
    }
    assert outside_ids == set(range(5701, 5712))
    assert outside_ids.isdisjoint(schema_ids)


def test_reviewed_pdf_files_match_registered_hash_size_and_page_count(project_root):
    registry = _registry(project_root)
    results = verify_human_review_source_files(registry, project_root, require_present=True)
    assert len(results) == 3
    assert all(
        result.present and result.hash_matches and result.size_matches and result.page_count_matches
        for result in results
    )
