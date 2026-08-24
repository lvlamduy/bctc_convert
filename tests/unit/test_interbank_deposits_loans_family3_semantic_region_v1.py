from __future__ import annotations

import copy
import shutil
from pathlib import Path

import pytest

from bctc_ai.evaluation.interbank_deposits_loans_family3_semantic_region_v1 import (
    InterbankDepositsLoansFamily3SemanticRegionV1Error,
    build_interbank_deposits_loans_family3_semantic_region_v1,
    validate_interbank_deposits_loans_family3_semantic_region_replay_v1,
)

_ROOT = Path(__file__).resolve().parents[2]


def _line(index: int, text: str, x1: int, y: int, x2: int) -> dict:
    return {
        "bbox": [x1, y, x2, y + 28],
        "source_line_index": index,
        "source_text": text,
        "vietocr_text": text,
    }


def _page(lines: list[dict]) -> dict:
    return {
        "lines": lines,
        "page_height": 1_400,
        "page_sequence": 1,
        "page_width": 1_000,
    }


def _table(
    y: int = 30,
    index: int = 0,
    *,
    missing_geometry_role: str | None = None,
) -> list[dict]:
    rows = [
        "Tiền gửi không kỳ hạn",
        "Tiền gửi có kỳ hạn",
        "Cho vay các TCTD khác",
    ]
    lines = [_line(index, "Tiền gửi và cho vay các TCTD khác", 40, y, 560)]
    index += 1
    for ordinal, role in enumerate(rows):
        row_y = y + 80 + ordinal * 58
        lines.append(_line(index, role, 60, row_y, 540))
        index += 1
        if role == missing_geometry_role:
            continue
        lines.extend(
            [
                _line(index, str((ordinal + 1) * 100), 700, row_y, 770),
                _line(index + 1, str((ordinal + 1) * 90), 830, row_y, 900),
            ]
        )
        index += 2
    return lines


def _candidates(result: dict) -> list[dict]:
    return [candidate for region in result["regions"] for candidate in region["candidates"]]


def _region_keys(region: dict) -> set[str]:
    return {
        key for candidate in region["candidates"] for key in candidate["evidence_equivalence_keys"]
    }


def test_unique_explicit_table_remains_incomplete_until_branchless_oracle() -> None:
    result = build_interbank_deposits_loans_family3_semantic_region_v1([_page(_table())])

    assert result["status"] == "UNIQUE_EXPLICIT_STRUCTURE_PROPOSAL_REQUIRES_BRANCHLESS_ORACLE"
    assert result["metrics"]["complete_evidence_cluster_count"] == 1
    assert result["metrics"]["branch_candidate_count"] == 1
    assert len(result["regions"]) == 1
    assert result["regions"][0]["disposition"] == "UNRESOLVED"
    complete = [item for item in _candidates(result) if item["complete_required_role_combinations"]]
    assert [item["branch_role"] for item in complete] == ["DEMAND_DEPOSIT_GROUP"]
    assert complete[0]["disposition"] == "UNRESOLVED"
    assert complete[0]["status"] == "EXPLICIT_STRUCTURE_PROPOSAL_REQUIRES_BRANCHLESS_ORACLE"
    assert complete[0]["complete_required_role_combinations"] == [
        ["DEMAND_DEPOSIT_GROUP", "TERM_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"]
    ]
    assert result["absence"]["bounded_absences"] == []
    assert result["requires_full_document_branchless_oracle"] is True
    assert result["branchless_evaluation_status"] == (
        "NOT_RUN_REQUIRES_RESET_FENCED_OWNER_LOCAL_SHARED_PRIMITIVE"
    )
    assert result["safety"]["family_completion_authority"] is False
    assert result["safety"]["numeric_authority"] is False
    assert result["safety"]["mapping_authority"] is False
    assert result["safety"]["multiple_complete_regions_can_select_nearest_or_last"] is False
    assert result["evidence_binding"]["config_binding"] == {
        "evaluation_spec_ref": {
            "path": "config/families/tm-interbank-deposits-loans-evaluation-v3.json",
            "sha256": "0db7cfe8efe522822abf0ab8b716182300d0314c75f26af3197357a966aa9772",
            "size_bytes": 2_280,
        },
        "topology_spec_ref": {
            "path": "config/families/tm-interbank-deposits-loans-topology-v3.json",
            "sha256": "816573106c32e7fa133cc2d371d3b5ff89a10ce307ef148655e04fb00c4614e5",
            "size_bytes": 10_320,
        },
    }


def test_missing_required_lane_is_retained_unresolved() -> None:
    result = build_interbank_deposits_loans_family3_semantic_region_v1(
        [_page(_table(missing_geometry_role="Cho vay các TCTD khác"))]
    )

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_EXPLICIT_STRUCTURE"
    assert result["metrics"]["complete_evidence_cluster_count"] == 0
    demand = next(
        item for item in _candidates(result) if item["branch_role"] == "DEMAND_DEPOSIT_GROUP"
    )
    assert demand["disposition"] == "UNRESOLVED"
    assert demand["unresolved_reasons"] == ["REQUIRED_ROLE_SHARED_LANE_OR_GEOMETRY_NOT_COMPLETE"]
    assert demand["shared_semantic_region"]["row_proposals"][-1]["status"] == (
        "TEXT_ROLE_PROPOSAL_MISSING_ROW_VALUE_GEOMETRY"
    )


def test_declared_pair_uses_interbank_deposit_as_the_only_branch_role() -> None:
    lines = [
        _line(0, "Tiền gửi và cho vay các TCTD khác", 40, 30, 560),
        _line(1, "Tiền gửi tại các TCTD khác", 60, 120, 540),
        _line(2, "100", 700, 120, 770),
        _line(3, "90", 830, 120, 900),
        _line(4, "Cho vay các TCTD khác", 60, 190, 540),
        _line(5, "200", 700, 190, 770),
        _line(6, "180", 830, 190, 900),
    ]

    result = build_interbank_deposits_loans_family3_semantic_region_v1([_page(lines)])

    assert result["status"] == "UNIQUE_EXPLICIT_STRUCTURE_PROPOSAL_REQUIRES_BRANCHLESS_ORACLE"
    assert result["metrics"]["branch_candidate_count"] == 1
    candidate = _candidates(result)[0]
    assert candidate["branch_role"] == "INTERBANK_DEPOSIT_GROUP"
    assert candidate["complete_required_role_combinations"] == [
        ["INTERBANK_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"]
    ]
    assert candidate["disposition"] == "UNRESOLVED"


def test_legitimate_nested_pair_and_triple_share_one_explicit_region() -> None:
    lines = [_line(0, "Tiền gửi và cho vay các TCTD khác", 40, 30, 560)]
    for ordinal, role in enumerate(
        [
            "Tiền gửi tại các TCTD khác",
            "Tiền gửi không kỳ hạn",
            "Tiền gửi có kỳ hạn",
            "Cho vay các TCTD khác",
        ]
    ):
        y = 110 + ordinal * 58
        index = 1 + ordinal * 3
        lines.extend(
            [
                _line(index, role, 60, y, 540),
                _line(index + 1, str((ordinal + 1) * 100), 700, y, 770),
                _line(index + 2, str((ordinal + 1) * 90), 830, y, 900),
            ]
        )

    result = build_interbank_deposits_loans_family3_semantic_region_v1([_page(lines)])

    assert result["status"] == "UNIQUE_EXPLICIT_STRUCTURE_PROPOSAL_REQUIRES_BRANCHLESS_ORACLE"
    assert result["metrics"]["branch_candidate_count"] == 2
    assert result["metrics"]["complete_evidence_cluster_count"] == 1
    assert len(result["regions"]) == 1
    candidates = _candidates(result)
    assert {item["branch_role"] for item in candidates} == {
        "DEMAND_DEPOSIT_GROUP",
        "INTERBANK_DEPOSIT_GROUP",
    }
    assert {tuple(item["complete_required_role_combinations"][0]) for item in candidates} == {
        ("DEMAND_DEPOSIT_GROUP", "TERM_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"),
        ("INTERBANK_DEPOSIT_GROUP", "INTERBANK_LOAN_GROUP"),
    }
    assert all(item["disposition"] == "UNRESOLVED" for item in candidates)


def test_two_complete_physical_regions_are_both_retained_and_never_selected() -> None:
    result = build_interbank_deposits_loans_family3_semantic_region_v1(
        [_page([*_table(30, 0), *_table(430, 50)])]
    )

    assert result["status"] == "UNRESOLVED_MULTIPLE_EXPLICIT_COMPLETE_REGIONS"
    assert result["metrics"]["complete_evidence_cluster_count"] == 2
    assert len(result["regions"]) == 2
    assert all(region["disposition"] == "UNRESOLVED" for region in result["regions"])
    assert not (_region_keys(result["regions"][0]) & _region_keys(result["regions"][1]))
    complete = [item for item in _candidates(result) if item["complete_required_role_combinations"]]
    assert len(complete) == 2
    assert {item["status"] for item in complete} == {
        "EXPLICIT_STRUCTURE_BLOCKED_BY_COMPETING_REGION_EVIDENCE"
    }


def test_one_owner_two_complete_sibling_tables_do_not_bridge() -> None:
    lines = [
        _line(0, "Tiền gửi và cho vay các TCTD khác", 40, 30, 560),
        *_table(100, 20)[1:],
        *_table(430, 50)[1:],
    ]

    result = build_interbank_deposits_loans_family3_semantic_region_v1([_page(lines)])

    assert result["status"] == "UNRESOLVED_MULTIPLE_EXPLICIT_COMPLETE_REGIONS"
    assert result["metrics"]["branch_candidate_count"] == 2
    assert result["metrics"]["complete_evidence_cluster_count"] == 2
    assert len(result["regions"]) == 2
    assert not (_region_keys(result["regions"][0]) & _region_keys(result["regions"][1]))
    assert all(region["disposition"] == "UNRESOLVED" for region in result["regions"])


def test_complete_region_plus_independent_missing_lane_region_is_unresolved() -> None:
    result = build_interbank_deposits_loans_family3_semantic_region_v1(
        [
            _page(
                [
                    *_table(30, 0),
                    *_table(430, 50, missing_geometry_role="Cho vay các TCTD khác"),
                ]
            )
        ]
    )

    assert result["status"] == "UNRESOLVED_COMPETING_EXPLICIT_REGION_PROPOSALS"
    assert result["metrics"]["complete_evidence_cluster_count"] == 1
    assert result["metrics"]["unresolved_competitor_cluster_count"] == 1
    assert all(region["disposition"] == "UNRESOLVED" for region in result["regions"])


@pytest.mark.parametrize(
    "fence",
    ["Phân tích chất lượng", "Tiền gửi và vay các TCTD khác"],
)
def test_reset_and_hard_veto_fence_owner_context(fence: str) -> None:
    lines = [_line(0, "Tiền gửi và cho vay các TCTD khác", 40, 30, 560)]
    lines.append(_line(1, fence, 40, 80, 560))
    table = _table(100, 20)[1:]

    result = build_interbank_deposits_loans_family3_semantic_region_v1([_page([*lines, *table])])

    assert result["metrics"]["complete_evidence_cluster_count"] == 0
    assert result["status"] == "UNRESOLVED_NO_COMPLETE_EXPLICIT_STRUCTURE"
    assert result["safety"]["reset_or_hard_veto_can_be_crossed"] is False


def test_branchless_page_global_replay_is_not_run_or_false_challenger() -> None:
    lines = [_line(0, "Tiền gửi và cho vay các TCTD khác", 40, 30, 560)]
    for ordinal, role in enumerate(
        [
            "Dự phòng rủi ro tiền gửi tại các TCTD khác",
            "Dự phòng rủi ro cho vay các TCTD khác",
        ]
    ):
        y = 120 + ordinal * 70
        index = 1 + ordinal * 3
        lines.extend(
            [
                _line(index, role, 60, y, 560),
                _line(index + 1, str(100 + ordinal), 700, y, 770),
                _line(index + 2, str(90 + ordinal), 830, y, 900),
            ]
        )

    pages = [_page(lines)]
    result = build_interbank_deposits_loans_family3_semantic_region_v1(pages)
    reversed_pages = copy.deepcopy(pages)
    reversed_pages[0]["lines"].reverse()

    assert build_interbank_deposits_loans_family3_semantic_region_v1(reversed_pages) == result
    assert result["status"] == "UNRESOLVED_NO_COMPLETE_EXPLICIT_STRUCTURE"
    assert result["metrics"]["branch_candidate_count"] == 0
    assert result["regions"] == []
    assert "branchless_challengers" not in result
    assert result["branchless_evaluation_status"] == (
        "NOT_RUN_REQUIRES_RESET_FENCED_OWNER_LOCAL_SHARED_PRIMITIVE"
    )
    assert result["requires_full_document_branchless_oracle"] is True
    assert "BRANCHLESS_ORACLE_NOT_RUN_BLOCKS_ABSENCE" in result["absence"]["blockers"]


def test_zero_branch_never_becomes_absence() -> None:
    result = build_interbank_deposits_loans_family3_semantic_region_v1(
        [_page([_line(0, "Thuyết minh không liên quan", 40, 30, 500)])]
    )

    assert result["regions"] == []
    assert result["absence"] == {
        "blockers": [
            "ADAPTER_HAS_NO_ABSENCE_AUTHORITY",
            "BRANCHLESS_ORACLE_NOT_RUN_BLOCKS_ABSENCE",
            "ZERO_BRANCH_CANNOT_PROVE_ABSENCE",
        ],
        "bounded_absences": [],
        "status": "UNRESOLVED_NO_ABSENCE_AUTHORITY",
    }


def test_provider_order_and_public_replay_are_exact() -> None:
    pages = [_page(_table())]
    expected = build_interbank_deposits_loans_family3_semantic_region_v1(pages)
    reversed_pages = copy.deepcopy(pages)
    reversed_pages[0]["lines"].reverse()

    assert build_interbank_deposits_loans_family3_semantic_region_v1(reversed_pages) == expected
    assert (
        validate_interbank_deposits_loans_family3_semantic_region_replay_v1(expected, pages)
        == expected
    )
    forged = copy.deepcopy(expected)
    forged["status"] = "FORGED"
    with pytest.raises(
        InterbankDepositsLoansFamily3SemanticRegionV1Error,
        match="content identity drifted",
    ):
        validate_interbank_deposits_loans_family3_semantic_region_replay_v1(forged, pages)


def test_literal_config_pin_rejects_silent_policy_drift(tmp_path: Path) -> None:
    copied_root = tmp_path / "root"
    for relative in [
        "config/families/tm-interbank-deposits-loans-topology-v3.json",
        "config/families/tm-interbank-deposits-loans-evaluation-v3.json",
    ]:
        target = copied_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_ROOT / relative, target)
    evaluation = copied_root / "config/families/tm-interbank-deposits-loans-evaluation-v3.json"
    evaluation.write_bytes(evaluation.read_bytes() + b"\n")

    with pytest.raises(
        InterbankDepositsLoansFamily3SemanticRegionV1Error,
        match="literal config pin drifted",
    ):
        build_interbank_deposits_loans_family3_semantic_region_v1([_page(_table())], copied_root)
