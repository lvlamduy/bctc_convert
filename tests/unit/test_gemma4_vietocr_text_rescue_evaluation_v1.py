from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "docs/experiments/E-0053-gemma4-vietocr-text-rescue-evaluation-v1.json"


def _load() -> dict[str, Any]:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_receipt_is_content_addressed_and_non_authoritative() -> None:
    value = _load()
    body = dict(value)
    evaluation_id = body.pop("evaluation_id")
    payload = json.dumps(
        body,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert evaluation_id == f"gemma4rescuev1:evaluation:{sha256(payload).hexdigest()}"
    assert value["authority"] == {
        "accounting_authority": False,
        "broad_corpus_accuracy_claim": False,
        "canonicalization_authority": False,
        "export_authority": False,
        "geometry_authority": False,
        "mapping_authority": False,
        "numeric_authority": False,
        "ocr_text_anchor_diagnostic": True,
        "schema_authority": False,
    }


def test_trial_metrics_are_derived_from_exact_and_accentless_comparisons() -> None:
    value = _load()
    trials = value["trials"]
    assert len(trials) == 7
    assert len({trial["sample_id"] for trial in trials}) == 7
    for trial in trials:
        pixel = trial["independent_pixel_text"]
        assert (trial["vietocr_text"] == pixel) is trial["vietocr_exact_pixel_match"]
        assert (trial["gemma4_text"] == pixel) is trial["gemma4_exact_pixel_match"]
        assert (
            normalize_vietnamese_anchor_v1(trial["vietocr_text"])
            == normalize_vietnamese_anchor_v1(pixel)
        ) is trial["vietocr_accentless_pixel_match"]
        assert (
            normalize_vietnamese_anchor_v1(trial["gemma4_text"])
            == normalize_vietnamese_anchor_v1(pixel)
        ) is trial["gemma4_accentless_pixel_match"]

    metrics = value["metrics"]
    assert metrics["vietocr_exact_pixel_match_count"] == sum(
        trial["vietocr_exact_pixel_match"] for trial in trials
    )
    assert metrics["gemma4_exact_pixel_match_count"] == sum(
        trial["gemma4_exact_pixel_match"] for trial in trials
    )
    assert metrics["vietocr_accentless_pixel_match_count"] == sum(
        trial["vietocr_accentless_pixel_match"] for trial in trials
    )
    assert metrics["gemma4_accentless_pixel_match_count"] == sum(
        trial["gemma4_accentless_pixel_match"] for trial in trials
    )


def test_rescue_policy_keeps_text_nondecisive_and_primary_reader_unchanged() -> None:
    value = _load()
    assert value["decision"] == {
        "accentless_text_is_anchor_evidence_only": True,
        "bounded_edit_distance_is_anchor_evidence_only": True,
        "gemma_output_can_silently_replace_vietocr_output": False,
        "invoke_rescue_only_for_clear_vietocr_pixel_or_structural_conflict": True,
        "primary_text_reader": "VIETOCR_0.3.13_VGG19_BN_TRANSFORMER",
        "rescue_requires_owner_parent_children_siblings_order_geometry_axes_units_scope_and_accounting_corroboration": True,
        "rescue_text_reader": "GEMMA4_26B_A4B_IT_QAT_Q4_0",
        "text_alone_can_decide_family_or_mapping": False,
    }
    assert value["metrics"]["stability_replay_count"] == 3
    assert value["metrics"]["stability_replay_matching_count"] == 3
    assert all(replay["matches_primary_output"] for replay in value["stability_replays"])
