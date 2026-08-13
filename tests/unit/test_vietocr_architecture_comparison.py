from __future__ import annotations

import json
import unicodedata
from pathlib import Path

from bctc_ai.evaluation.vietocr_architecture_comparison import (
    SEMANTIC_TEXT_POLICY,
    _detect_family_topology,
    accentless_semantic_shortlist_key,
    resolve_vietnamese_semantic_role,
)


def test_accentless_key_can_shortlist_but_cannot_accept() -> None:
    aliases = {"STANDARD": ["Nợ đủ tiêu chuẩn"]}

    exact = resolve_vietnamese_semantic_role("Nợ đủ tiêu chuẩn", aliases)
    accentless = resolve_vietnamese_semantic_role("No du tieu chuan", aliases)

    assert exact["status"] == "UNIQUE_ACCENT_PRESERVING_ROLE"
    assert exact["accepted_role"] == "STANDARD"
    assert accentless["status"] == "ACCENTLESS_SHORTLIST_ONLY_UNRESOLVED"
    assert accentless["accepted_role"] is None
    assert accentless["accentless_shortlisted_roles"] == ["STANDARD"]
    assert SEMANTIC_TEXT_POLICY["accentless_comparison_key_alone_can_accept"] is False
    assert (
        SEMANTIC_TEXT_POLICY[
            "unique_collision_free_accentless_candidate_may_be_promoted_downstream"
        ]
        is True
    )
    assert SEMANTIC_TEXT_POLICY["this_evaluator_performs_downstream_promotion"] is False


def test_accentless_role_collision_stays_unresolved() -> None:
    aliases = {
        "ROLE_A": ["Nợ đủ"],
        "ROLE_B": ["Nỏ đủ"],
    }

    resolved = resolve_vietnamese_semantic_role("No du", aliases)

    assert accentless_semantic_shortlist_key("Nợ đủ") == "no du"
    assert accentless_semantic_shortlist_key("Nỏ đủ") == "no du"
    assert resolved == {
        "status": "ACCENTLESS_COLLISION_UNRESOLVED",
        "accepted_role": None,
        "accentless_shortlisted_roles": ["ROLE_A", "ROLE_B"],
    }


def test_accentless_topology_is_diagnostic_only() -> None:
    matcher = {
        "owner_aliases": ["CHO VAY KHÁCH HÀNG"],
        "branch_aliases": ["Phân tích dư nợ theo chất lượng"],
        "ordered_children": [
            {"role": "STANDARD", "aliases": ["Nợ đủ tiêu chuẩn"]},
            {"role": "SPECIAL_MENTION", "aliases": ["Nợ cần chú ý"]},
        ],
        "unit": {"canonical": "VND", "multiplier": 1_000_000},
    }
    case = {"source_line_start": 0, "source_line_end": 4, "required_unit_count": 1}
    lines = {
        0: "CHO VAY KHACH HANG",
        1: "Phan tich du no theo chat luong",
        2: "Triệu đồng",
        3: "No du tieu chuan",
        4: "No can chu y",
    }

    topology = _detect_family_topology(lines, case=case, matcher=matcher)

    assert topology["acceptance_shape_detected"] is False
    assert topology["accentless_topology_shortlist_detected"] is True
    assert topology["accentless_shortlist_alone_can_accept"] is False


def test_postfreeze_truth_is_utf8_nfc_and_binds_both_frozen_outputs() -> None:
    project_root = Path(__file__).resolve().parents[2]
    truth_path = (
        project_root / "docs/experiments/vietocr-transformer-seq2seq-postfreeze-truth-v1.json"
    )
    payload = json.loads(truth_path.read_text(encoding="utf-8"))

    assert payload["state"] == "FROZEN_AFTER_BOTH_ARCHITECTURE_OUTPUTS"
    assert payload["input_bindings"]["transformer_result_sha256"] == (
        "4277307a95738975bb720f3d5cff19b4e432e741a5052002efffcac5343197d1"
    )
    assert payload["input_bindings"]["seq2seq_result_sha256"] == (
        "5c21ed137774262f770a8b2b28287efb88e952e6e2e640776066cc1e5031170f"
    )
    expected = {sample["expected_text"] for sample in payload["samples"]}
    assert "Nợ có khả năng mất vốn" in expected
    assert "Phân tích dư nợ theo thời hạn gốc của khoản vay" in expected
    assert all(text == unicodedata.normalize("NFC", text) for text in expected)
