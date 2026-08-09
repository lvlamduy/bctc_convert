from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from bctc_ai.core.hashing import sha256_bytes, sha256_file
from bctc_ai.corpus.wave1_role_a_level1_boundaries import (
    IMPLEMENTATION_RELATIVE_PATH,
    POLICY_RELATIVE_PATH,
    REFERENCE_SOURCE_RELATIVE_PATH,
    WaveOneRoleALevelOneReferenceError,
    _assert_committed_clean_inputs,
    _validate_reference_record,
    build_wave_one_role_a_level_one_boundaries,
    load_wave_one_role_a_level_one_policy,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_SOURCE_SHA256 = "0d27b7248d70ae63533eed8551b08d7d6af6498296f699c0c3fc4f4c16d36451"
EXPECTED_POLICY_SHA256 = "7392d0641ff37c3c2b28c047015935f4a868e23e90cf1414e12a645a75c3ff8f"
EXPECTED_IMPLEMENTATION_SHA256 = "34863c95f94745c7423611aa69db65c6885bb173c7656233cafcd31372f60dd7"
EXPECTED_BOUNDARY_PROJECTION_SHA256 = (
    "440101b4d438d2e97d934c73ad8fd1a1756a763fbde9e4a7c0cdbf79a8553505"
)
EXPECTED_BOUNDARY_PROJECTION_SIZE = 17_528
EXPECTED_IDENTITY_PROJECTION_SHA256 = (
    "1bcd95486253dd746ad0690f31ca902c601be82f37b88e0dad45816a2b6e4e4c"
)
EXPECTED_IDENTITY_PROJECTION_SIZE = 10_392


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _raw_reference_records() -> dict[str, dict[str, object]]:
    source = yaml.safe_load((PROJECT_ROOT / REFERENCE_SOURCE_RELATIVE_PATH).read_bytes())
    return {record["bank"]: record for record in source["records"]}


def _page_counts() -> dict[str, int]:
    source_profile = json.loads(
        (
            PROJECT_ROOT / "output/development/bank-corpus-survey-v1/wave-1-source-profile.json"
        ).read_bytes()
    )
    return {record["bank"]: record["page_count"] for record in source_profile["profiles"]}


def test_sealed_source_policy_and_implementation_hashes_are_frozen() -> None:
    assert sha256_file(PROJECT_ROOT / REFERENCE_SOURCE_RELATIVE_PATH) == EXPECTED_SOURCE_SHA256
    assert sha256_file(PROJECT_ROOT / POLICY_RELATIVE_PATH) == EXPECTED_POLICY_SHA256
    assert sha256_file(PROJECT_ROOT / IMPLEMENTATION_RELATIVE_PATH) == (
        EXPECTED_IMPLEMENTATION_SHA256
    )


def test_real_wave_one_reference_joins_all_exact_selected_identities() -> None:
    payload = build_wave_one_role_a_level_one_boundaries(PROJECT_ROOT)
    assert payload["status"] == "ROLE_A_LEVEL_1_MACHINE_REFERENCE"
    assert payload["claim_boundary"] == "STRUCTURAL_BOUNDARIES_ONLY"
    assert payload["selection_receipt_sha256"] == (
        "832cea1bee22f0bb08c422490dd2afe4e23bc91c56cdee6db382b1bfdc744d28"
    )
    assert payload["accounting"] == {
        "document_count": 27,
        "physical_page_count": 1_449,
        "partitioned_physical_page_count": 1_449,
        "unique_statement_page_count": 1_363,
        "statement_block_page_incidence_count": 1_367,
        "statement_block_count": 139,
        "statement_block_counts": {
            "CDKT_MAIN": 28,
            "KQKD": 28,
            "LCTT": 28,
            "OFF_BALANCE": 28,
            "TM": 27,
        },
        "page_segment_counts": {
            "BLANK_INTERSTITIAL": 1,
            "BLANK_TRAILING": 1,
            "CDKT_MAIN": 28,
            "COVER": 23,
            "GOVERNANCE_GENERAL_INFORMATION": 9,
            "KQKD": 28,
            "LCTT": 28,
            "OFF_BALANCE": 24,
            "SUPPORTING_FRONT": 13,
            "SUPPORTING_TRAILING": 2,
            "TABLE_OF_CONTENTS": 16,
            "TM": 27,
        },
        "embedded_off_balance_block_count": 4,
        "duplicate_presentation_document_count": 1,
        "scope_status_counts": {
            "OBSERVED_CONSOLIDATED": 24,
            "OBSERVED_SEPARATE": 1,
            "UNRESOLVED_SOURCE_UNQUALIFIED": 2,
        },
        "lctt_method_status_counts": {
            "DIRECT_EXPLICIT_TITLE": 14,
            "DIRECT_INFERRED_VISIBLE_ROWS": 10,
            "UNRESOLVED_NOT_PRINTED": 3,
        },
        "source_accounted_visible_row_count": 0,
        "source_accounted_visible_value_cell_count": 0,
        "canonical_mapped_row_count": 0,
        "human_gold_document_count": 0,
        "role_b_document_count": 0,
    }

    inventory = json.loads(
        (
            PROJECT_ROOT / "output/development/bank-corpus-survey-v1/corpus-inventory.json"
        ).read_bytes()
    )
    source_profile = json.loads(
        (
            PROJECT_ROOT / "output/development/bank-corpus-survey-v1/wave-1-source-profile.json"
        ).read_bytes()
    )
    selected = {record["bank"]: record for record in inventory["wave_1"]["selected_documents"]}
    profiles = {record["bank"]: record for record in source_profile["profiles"]}
    assert len(payload["documents"]) == len(selected) == len(profiles) == 27
    for document in payload["documents"]:
        bank = document["bank"]
        source = document["source"]
        assert {
            key: source[key] for key in ("document_id", "relative_path", "sha256", "size_bytes")
        } == {
            key: selected[bank][key]
            for key in ("document_id", "relative_path", "sha256", "size_bytes")
        }
        assert source["page_count"] == profiles[bank]["page_count"]
        assert document["accounting"]["physical_page_count"] == source["page_count"]
        assert document["accounting"]["partitioned_physical_page_count"] == source["page_count"]


def test_all_sealed_boundaries_and_source_identities_have_stable_projections() -> None:
    payload = build_wave_one_role_a_level_one_boundaries(PROJECT_ROOT)
    boundary_projection = [
        {
            "bank": document["bank"],
            "page_segments": [
                [
                    segment["kind"],
                    segment["start_page"],
                    segment["end_page"],
                    segment["copy_id"],
                    segment["embedded_off_balance_pages"],
                ]
                for segment in document["page_segments"]
            ],
            "statement_blocks": [
                [
                    block["block_id"],
                    block["block_type"],
                    block["start_page"],
                    block["end_page"],
                    block["copy_id"],
                    block["placement"],
                    block["parent_block_id"],
                    block["visible_unit_override"],
                ]
                for block in document["statement_blocks"]
            ],
            "tm_subdivisions": [
                [item["kind"], item["start_page"], item["end_page"]]
                for item in document["tm_subdivisions"]
            ],
        }
        for document in payload["documents"]
    ]
    encoded = _canonical_json_bytes(boundary_projection)
    assert len(encoded) == EXPECTED_BOUNDARY_PROJECTION_SIZE
    assert sha256_bytes(encoded) == EXPECTED_BOUNDARY_PROJECTION_SHA256

    identity_projection = [document["source"] for document in payload["documents"]]
    encoded = _canonical_json_bytes(identity_projection)
    assert len(encoded) == EXPECTED_IDENTITY_PROJECTION_SIZE
    assert sha256_bytes(encoded) == EXPECTED_IDENTITY_PROJECTION_SHA256


def test_embedded_blank_trailing_subdivision_and_duplicate_cases_are_preserved() -> None:
    payload = build_wave_one_role_a_level_one_boundaries(PROJECT_ROOT)
    documents = {document["bank"]: document for document in payload["documents"]}

    embedded = {
        bank: [
            block["start_page"]
            for block in document["statement_blocks"]
            if block["placement"] == "EMBEDDED_BOTTOM_REGION"
        ]
        for bank, document in documents.items()
        if any(
            block["placement"] == "EMBEDDED_BOTTOM_REGION" for block in document["statement_blocks"]
        )
    }
    assert embedded == {"PGB": [4], "STB": [3], "VAB": [4, 6]}

    vab = documents["VAB"]
    assert vab["duplicate_presentation"] == {
        "status": "MULTIPLE_FORMAL_SCALE_VARIANTS_OBSERVED",
        "canonical_double_count_claim": "NOT_MADE",
        "copy_groups": [
            {
                "copy_id": "A",
                "block_ids": ["CDKT_A", "OFF_BALANCE_A", "KQKD_A", "LCTT_A"],
                "scale": "VND",
            },
            {
                "copy_id": "B",
                "block_ids": ["CDKT_B", "OFF_BALANCE_B", "KQKD_B", "LCTT_B"],
                "scale": "MILLION_VND",
            },
        ],
    }
    assert [
        (block["block_id"], block["visible_unit_override"]) for block in vab["statement_blocks"]
    ] == [
        ("CDKT_A", "VND"),
        ("OFF_BALANCE_A", "VND"),
        ("CDKT_B", "triệu đồng"),
        ("OFF_BALANCE_B", "triệu đồng"),
        ("KQKD_A", "VND"),
        ("KQKD_B", "triệu đồng"),
        ("LCTT_A", "VND"),
        ("LCTT_B", "triệu VND"),
        ("TM_PRIMARY", None),
    ]

    assert documents["CTG"]["tm_subdivisions"] == [
        {"kind": "GENERAL_INFORMATION", "start_page": 11, "end_page": 17},
        {"kind": "FINANCIAL_STATEMENT_NOTES", "start_page": 18, "end_page": 61},
    ]
    assert [
        (segment["kind"], segment["start_page"], segment["end_page"])
        for segment in documents["STB"]["page_segments"]
        if segment["kind"].startswith("BLANK")
    ] == [("BLANK_INTERSTITIAL", 5, 5), ("BLANK_TRAILING", 46, 46)]
    assert documents["BID"]["page_segments"][-1]["kind"] == "SUPPORTING_TRAILING"
    assert documents["BID"]["page_segments"][-1]["start_page"] == 36
    assert documents["OCB"]["page_segments"][-1] == {
        "kind": "SUPPORTING_TRAILING",
        "start_page": 42,
        "end_page": 42,
        "copy_id": "NONE",
        "embedded_off_balance_pages": [],
    }
    shb_blocks = {
        block["block_type"]: (block["start_page"], block["end_page"])
        for block in documents["SHB"]["statement_blocks"]
    }
    assert shb_blocks["LCTT"] == (8, 9)
    assert shb_blocks["TM"] == (10, 42)


def test_reference_retains_uncertainty_and_never_upgrades_to_gold_or_mapping() -> None:
    payload = build_wave_one_role_a_level_one_boundaries(PROJECT_ROOT)
    documents = {document["bank"]: document for document in payload["documents"]}
    assert {
        bank
        for bank, document in documents.items()
        if document["scope"]["status"] == "UNRESOLVED_SOURCE_UNQUALIFIED"
    } == {"LPB", "PGB"}
    assert {
        bank
        for bank, document in documents.items()
        if document["lctt_method"]["status"] == "UNRESOLVED_NOT_PRINTED"
    } == {"BAB", "EIB", "KLB"}
    assert documents["VPB"]["reporting_period"]["classification"] == "Q1_2026"
    assert payload["negative_claims"] == {
        "human_gold": False,
        "role_b_output": False,
        "source_complete_extraction": False,
        "visible_rows_accounted": False,
        "visible_values_accounted": False,
        "canonical_mapping_attempted": False,
        "canonical_completeness": False,
        "schema_used": False,
        "canonical_double_count_authorized": False,
    }


def test_partition_overlap_and_duplicate_validation_fail_closed() -> None:
    records = _raw_reference_records()
    counts = _page_counts()

    missing_blank = copy.deepcopy(records["STB"])
    missing_blank["page_segments"].pop(3)
    with pytest.raises(WaveOneRoleALevelOneReferenceError, match="gap or overlap"):
        _validate_reference_record(missing_blank, counts["STB"])

    bad_embedded_parent = copy.deepcopy(records["PGB"])
    bad_embedded_parent["statement_blocks"][1][6] = None
    with pytest.raises(WaveOneRoleALevelOneReferenceError, match="parent relationship"):
        _validate_reference_record(bad_embedded_parent, counts["PGB"])

    illegal_overlap = copy.deepcopy(records["ABB"])
    illegal_overlap["statement_blocks"].append(
        ["KQKD_ILLEGAL", "KQKD", 3, 3, "PRIMARY", "PAGE_SEQUENCE", None, None]
    )
    with pytest.raises(WaveOneRoleALevelOneReferenceError):
        _validate_reference_record(illegal_overlap, counts["ABB"])

    collapsed_vab = copy.deepcopy(records["VAB"])
    collapsed_vab["duplicate_presentation"] = {
        "status": "NONE_OBSERVED",
        "canonical_double_count_claim": "NOT_MADE",
    }
    with pytest.raises(WaveOneRoleALevelOneReferenceError, match="copied statement block"):
        _validate_reference_record(collapsed_vab, counts["VAB"])


def test_publication_contract_requires_committed_clean_inputs(tmp_path: Path) -> None:
    policy = load_wave_one_role_a_level_one_policy(
        PROJECT_ROOT / POLICY_RELATIVE_PATH, PROJECT_ROOT
    )
    assert policy["output"]["publication_requires_committed_clean_inputs"] is True
    with pytest.raises(WaveOneRoleALevelOneReferenceError, match="committed inputs"):
        _assert_committed_clean_inputs(tmp_path, policy["output"]["required_committed_paths"])
