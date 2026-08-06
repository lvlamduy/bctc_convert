from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0022_post_seal_statement_diagnosis_is_hash_locked(project_root):
    reference_path = project_root / "docs/experiments/E-0022-role-a-statement-reference.json"
    comparison_path = project_root / "docs/experiments/E-0022-statement-discovery-comparison.json"
    assert sha256_file(reference_path) == (
        "e9c14d49ba30451aaebdfb8f8632bc342f58517c6bf1e4ba29d892366706fcba"
    )
    assert sha256_file(comparison_path) == (
        "f47036761c4d00c5d4b7734a9e1183f9146be5fead604b9e08e9de0c4efd3234"
    )

    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    capture_commit = "08dec6cada1f0237109c9c4e303061c4ddab2d9b"

    assert reference["state"] == "ROLE_A_STATEMENT_PAGE_REFERENCE_COMPLETE"
    assert reference["capture_git_commit"] == capture_commit
    assert reference["capture_git_dirty"] is False
    assert reference["eligible_for_holdout_retuning"] is False
    assert reference["source"] == {
        "native_text_page_count": 33,
        "page_count": 33,
        "path": "vietstock_bctc/ACB/2026/ACB BCTC HOP NHAT Q1_26_ban tra cuu.pdf",
        "sha256": "d8be301b9169577a0be2bbd8721cdaaab7cb37a32493ead0de5871bfcbc168dd",
        "size_bytes": 1060293,
    }
    assert reference["main_statement_pages"] == [3, 4, 6, 7, 8]
    assert reference["off_balance_pages"] == [5]
    assert len(reference["page_decisions"]) == 33
    assert [
        (
            pair["reference_page"],
            pair["candidate_page"],
            pair["statement_type"],
            pair["cash_flow_method"],
        )
        for pair in reference["target_pairs"]
    ] == [
        (3, 3, "CDKT", None),
        (4, 4, "CDKT", None),
        (6, 6, "KQKD", None),
        (7, 7, "LCTT", "DIRECT"),
        (8, 8, "LCTT", "DIRECT"),
    ]
    assert all(pair["visual_sequence_supported"] for pair in reference["target_pairs"])
    assert reference["visual_pairing"]["uses_text_or_values"] is False
    assert reference["frozen_locator_on_exact_native_text"]["status"] == "UNRESOLVED"
    assert reference["frozen_locator_on_exact_native_text"]["candidate_count"] == 0

    quality = reference["native_text_quality_audit"]
    assert quality["parser_reported_corrupt_pages"] == 33
    assert quality["actual_mojibake_sequence_counts"] == {
        "Ä": 0,
        "áº": 0,
        "á»": 0,
        "�": 0,
    }
    assert quality["valid_vietnamese_marker_tokens"] == {
        "Â": ["CHÂU", "NGÂN", "NHÂN"],
        "Ã": ["HOÃN", "LÃI", "LÃI/(LỖ)"],
    }

    assert comparison["state"] == "STATEMENT_DISCOVERY_COMPARISON_COMPLETE"
    assert comparison["capture_git_commit"] == capture_commit
    assert comparison["role_b_was_sealed_before_role_a_access"] is True
    assert comparison["role_b_rerun_after_reference_access"] is False
    assert comparison["threshold_or_page_selection_tuning_performed"] is False
    assert comparison["historical_reference_invoked"] is False
    assert comparison["mapping_invoked"] is False
    assert comparison["reference_classifier_metric_is_holdout_accuracy"] is False
    assert comparison["metrics"] == {
        "expected_main_statement_pages": 5,
        "frozen_locator_exact_native_correct_pages": 2,
        "frozen_locator_exact_native_page_recall": 0.4,
        "reference_expected_by_statement": {"CDKT": 2, "KQKD": 1, "LCTT": 2},
        "role_b_complete_ordered_block": False,
        "role_b_correct_by_statement": {"CDKT": 0, "KQKD": 0, "LCTT": 0},
        "role_b_correct_mapping_eligible_pages": 0,
        "role_b_main_statement_page_recall": 0.0,
        "role_b_mapping_eligible_false_positive_pages": 0,
    }
    assert comparison["root_cause"] == {
        "exact_native_pages_missed_by_frozen_matcher": 3,
        "interpretation": (
            "Long exact Vietnamese statement titles are penalized by whole-string ratio "
            "against shorter cores; form-family suffixes such as B02a are not normalized; "
            "OCR diacritic loss then pushes the remaining LCTT titles below the gate."
        ),
        "native_pages_falsely_flagged_corrupt_by_unicode_letters": 33,
        "pages_lost_only_after_ocr_title_degradation": 2,
        "primary_class": "STATEMENT_DISCOVERY_HEADER_MATCHING",
        "target_pages_with_form_suffix_not_recognized_by_frozen_anchor": 5,
    }
    assert "not human gold" in comparison["claim_boundary"]
    assert comparison["role_a_reference"]["sha256"] == sha256_file(reference_path)
    implementation = comparison["diagnosis_implementation"]
    assert sha256_file(project_root / implementation["path"]) == implementation["sha256"]
