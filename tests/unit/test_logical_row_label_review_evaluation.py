from __future__ import annotations

from decimal import Decimal

import pytest

from bctc_ai.core.contracts import ValueStatus
from bctc_ai.evaluation.logical_row_label_review_evaluation import (
    LogicalRowLabelReviewEvaluationError,
    bind_reviewed_rows,
    determine_qwen_trigger,
)
from bctc_ai.reference.human_review import (
    ReviewedDecision,
    ReviewedValue,
    TemplateMembership,
)


def _zero_decision():
    return ReviewedDecision(
        document_key="mbb-q1-2026-consolidated",
        visible_row_id="mbb-p3-4354",
        page=3,
        statement_type="CDKT",
        reviewed_item_id=4354,
        template_membership=TemplateMembership.CURRENT_TARGET_TEMPLATE,
        canonical_name="Đầu tư vào công ty liên kết",
        pdf_label="Đầu tư vào công ty liên kết",
        period_map_id="mbb-cdkt-2026q1",
        mapping_action="MAP_ONCE",
        value_status=ValueStatus.OBSERVED_ZERO,
        current=ReviewedValue("-", Decimal(0)),
        comparative=ReviewedValue("-", Decimal(0)),
        metadata={},
    )


def test_review_binding_uses_unresolved_numeric_as_wildcard_then_ppocr_tiebreak():
    decision = _zero_decision()
    numeric_rows = {
        (3, 7): {0: Decimal(0), 1: Decimal(0)},
        (3, 19): {0: Decimal(0), 1: None},
    }
    crop_rows = {
        (3, 7): {
            "sample_id": "page-0003-row-007-label",
            "ppocr_text": "Các công cụ tài chính phái sinh",
        },
        (3, 19): {
            "sample_id": "page-0003-row-019-label",
            "ppocr_text": "Đu tư vào công ty liên kêt",
        },
    }

    bound, evidence = bind_reviewed_rows(
        (decision,),
        numeric_rows,
        crop_rows,
        minimum_label_similarity=0.75,
        minimum_runner_up_margin=0.15,
    )

    assert set(bound) == {"page-0003-row-019-label"}
    assert evidence[0]["numeric_compatible_candidate_count"] == 2
    assert evidence[0]["numeric_observed_cell_count"] == 1
    assert evidence[0]["ppocr_tiebreak_margin"] > 0.15


def test_review_binding_rejects_weak_or_ambiguous_label_tiebreak():
    decision = _zero_decision()
    numeric_rows = {
        (3, 18): {0: Decimal(0), 1: None},
        (3, 19): {0: Decimal(0), 1: None},
    }
    crop_rows = {
        (3, 18): {"sample_id": "page-0003-row-018-label", "ppocr_text": "Đầu tư"},
        (3, 19): {"sample_id": "page-0003-row-019-label", "ppocr_text": "Đầu tư"},
    }

    with pytest.raises(LogicalRowLabelReviewEvaluationError, match="binding is ambiguous"):
        bind_reviewed_rows(
            (decision,),
            numeric_rows,
            crop_rows,
            minimum_label_similarity=0.75,
            minimum_runner_up_margin=0.15,
        )


def test_qwen_trigger_uses_only_predeclared_reviewed_failures():
    evaluations = {
        "vietocr": {
            "labels": {"aggregate": {"exact_line_count": 5}},
            "mapping": {"reviewed_best_path_exact_count": 6},
        },
        "deepseek_ocr2": {
            "labels": {"aggregate": {"exact_line_count": 6}},
            "mapping": {"reviewed_best_path_exact_count": 6},
        },
    }

    trigger = determine_qwen_trigger(evaluations)

    assert trigger["triggered"] is True
    assert trigger["decision"] == "RUN_QWEN_SAME_REQUEST"
    assert trigger["reviewed_source_inexact_count_by_reader"] == {
        "vietocr": 1,
        "deepseek_ocr2": 0,
    }
