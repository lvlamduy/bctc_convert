from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from bctc_ai.evaluation import provision_movement_family13_full_structural_oracle_v1 as subject
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

OWNER = "Dự phòng rủi ro cho vay khách hàng"
OPENING = "Số dư đầu kỳ"
PROVISION = "Trích lập dự phòng trong kỳ"
CLOSING = "Số dư cuối kỳ"
CORE = [OPENING, PROVISION, CLOSING]
RESET = "Phân tích chất lượng nợ cho vay"


def _line(index: int, text: str, y: int) -> dict:
    return {
        "bbox": [40, y, 700, y + 24],
        "source_line_index": index,
        "source_text": text,
        "vietocr_text": text,
    }


def _page(sequence: int, texts: list[str]) -> dict:
    return {
        "lines": [_line(index, text, 20 + index * 40) for index, text in enumerate(texts)],
        "page_height": 1000,
        "page_sequence": sequence,
        "page_width": 1000,
    }


def _build(texts: list[str]) -> dict:
    return subject.build_provision_movement_family13_full_structural_oracle_v1([_page(1, texts)])


@pytest.mark.parametrize(
    "owner",
    [
        OWNER,
        "Biến động số dư dự phòng rủi ro cho vay khách hàng",
        "Biến động số dư dự phòng rủi ro cho vay KH",
    ],
)
@pytest.mark.parametrize(
    "lane",
    [
        "Dự phòng chung",
        "Dự phòng cụ thể",
        "Dự phòng cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
    ],
)
def test_primary_owner_and_each_explicit_lane_are_structurally_ready(owner: str, lane: str) -> None:
    result = _build([owner, lane, *CORE])

    assert result["status"] == "STRUCTURAL_READY_PROPOSAL_ONLY"
    assert result["structural_region"] is not None
    assert result["metrics"]["owner_local_challenger_count"] == 0
    assert result["authority"]["complete_document_authority"] is False
    assert result["authority"]["absence_authority"] is False


def test_owner_and_core_without_lane_remains_unresolved_challenger() -> None:
    result = _build([OWNER, *CORE])

    assert result["status"] == "UNRESOLVED_STRUCTURAL_CHALLENGER_PROPOSAL_ONLY"
    assert result["structural_region"] is None
    assert result["metrics"]["owner_local_challenger_count"] == 1
    challenger = result["owner_local_oracle"]["challengers"][0]
    assert challenger["observed_role_ids"] == [
        "CLOSING_BALANCE_ROW",
        "OPENING_BALANCE_ROW",
        "PROVISION_OR_REVERSAL_ROW",
    ]


@pytest.mark.parametrize(
    ("texts", "expected"),
    [
        ([RESET, OWNER, "Dự phòng chung", *CORE], "STRUCTURAL_READY_PROPOSAL_ONLY"),
        (
            [OWNER, "Dự phòng chung", OPENING, RESET, PROVISION, CLOSING],
            "UNRESOLVED_STRUCTURAL_CHALLENGER_PROPOSAL_ONLY",
        ),
        ([OWNER, "Dự phòng chung", *CORE, RESET], "STRUCTURAL_READY_PROPOSAL_ONLY"),
        (
            [
                OWNER,
                "Dự phòng chung",
                OPENING,
                "Chi phí dự phòng rủi ro tín dụng",
                PROVISION,
                CLOSING,
            ],
            "UNRESOLVED_STRUCTURAL_CHALLENGER_PROPOSAL_ONLY",
        ),
    ],
)
def test_same_page_reset_and_hard_veto_fence_exactly(texts: list[str], expected: str) -> None:
    assert _build(texts)["status"] == expected


def test_one_page_continuation_is_ready_and_provider_reordering_is_canonical() -> None:
    pages = [
        _page(1, [OWNER, "Dự phòng cụ thể", OPENING, PROVISION]),
        _page(2, [CLOSING]),
    ]
    expected = subject.build_provision_movement_family13_full_structural_oracle_v1(pages)
    reordered = copy.deepcopy(pages[::-1])
    for page in reordered:
        page["lines"].reverse()

    assert expected["status"] == "STRUCTURAL_READY_PROPOSAL_ONLY"
    assert (
        subject.build_provision_movement_family13_full_structural_oracle_v1(reordered) == expected
    )


def test_continuation_budget_does_not_cross_an_intervening_page() -> None:
    pages = [
        _page(1, [OWNER, "Dự phòng cụ thể", OPENING, PROVISION]),
        _page(2, ["Thuyết minh khác"]),
        _page(3, [CLOSING]),
    ]
    result = subject.build_provision_movement_family13_full_structural_oracle_v1(pages)

    assert result["status"] == "UNRESOLVED_STRUCTURAL_CHALLENGER_PROPOSAL_ONLY"


@pytest.mark.parametrize("sequences", [[1, 3], [1, 1], [True]])
def test_page_axis_gap_duplicate_and_bool_fail_closed(sequences: list[int]) -> None:
    pages = [_page(sequence, ["Khác"]) for sequence in sequences]
    with pytest.raises(subject.ProvisionMovementFamily13FullStructuralOracleV1Error):
        subject.build_provision_movement_family13_full_structural_oracle_v1(pages)


def test_near_and_multiple_candidates_stay_unresolved() -> None:
    near = _build([OWNER, "Dự phòng chung", OPENING, PROVISION])
    multiple = _build(
        [
            OWNER,
            "Dự phòng chung",
            *CORE,
            OWNER,
            "Dự phòng cụ thể",
            *CORE,
        ]
    )

    assert near["status"] == "UNRESOLVED_STRUCTURAL_CHALLENGER_PROPOSAL_ONLY"
    assert near["metrics"]["topology_near_region_count"] == 1
    assert multiple["status"] == "UNRESOLVED_STRUCTURAL_CHALLENGER_PROPOSAL_ONLY"
    assert multiple["metrics"]["topology_complete_region_count"] == 2


def test_double_zero_is_not_observed_proposal_without_absence_authority() -> None:
    result = _build(["Doanh thu hoạt động"])

    assert result["status"] == "NOT_OBSERVED_PROPOSAL_ONLY"
    assert result["structural_region"] is None
    assert result["authority"]["absence_authority"] is False
    assert result["authority"]["complete_document_authority"] is False
    assert result["authority"]["zero_evidence_is_document_absence"] is False


def test_real_owner_and_partial_core_evidence_is_not_collapsed_to_not_observed() -> None:
    result = _build([OWNER, OPENING])

    assert result["status"] == "UNRESOLVED_STRUCTURAL_CHALLENGER_PROPOSAL_ONLY"
    assert result["topology_scan"]["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["topology_scan"]["metrics"]["core_semantic_anchor_hit_count"] == 1


@pytest.mark.parametrize(
    ("status", "core_hits"),
    [
        ("UNRESOLVED_NO_COMPLETE_REGION", 0),
        ("NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY", 1),
        ("NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY", False),
    ],
)
def test_injected_nonexact_topology_zero_cannot_claim_not_observed(
    monkeypatch: pytest.MonkeyPatch, status: str, core_hits: object
) -> None:
    original = subject.build_accounting_family_topology_scan_v1

    def injected(pages: object, spec: object) -> dict:
        result = original(pages, spec)
        result["status"] = status
        result["metrics"]["core_semantic_anchor_hit_count"] = core_hits
        return result

    monkeypatch.setattr(subject, "build_accounting_family_topology_scan_v1", injected)
    result = _build(["Doanh thu hoạt động"])

    assert result["topology_scan"]["regions"] == []
    assert result["topology_scan"]["near_regions"] == []
    assert result["status"] == "UNRESOLVED_STRUCTURAL_CHALLENGER_PROPOSAL_ONLY"


def test_replay_is_exact_and_rejects_plain_and_coordinated_tamper() -> None:
    pages = [_page(1, [OWNER, "Dự phòng chung", *CORE])]
    result = subject.build_provision_movement_family13_full_structural_oracle_v1(pages)
    assert (
        subject.validate_provision_movement_family13_full_structural_oracle_replay_v1(result, pages)
        == result
    )

    plain = copy.deepcopy(result)
    plain["status"] = "NOT_OBSERVED_PROPOSAL_ONLY"
    with pytest.raises(subject.ProvisionMovementFamily13FullStructuralOracleV1Error):
        subject.validate_provision_movement_family13_full_structural_oracle_replay_v1(plain, pages)

    coordinated = copy.deepcopy(plain)
    material = copy.deepcopy(coordinated)
    material.pop("result_id")
    coordinated["result_id"] = "pmf13fsov1:result:" + canonical_json_sha256_v1(material)
    with pytest.raises(subject.ProvisionMovementFamily13FullStructuralOracleV1Error):
        subject.validate_provision_movement_family13_full_structural_oracle_replay_v1(
            coordinated, pages
        )


def test_dependency_refs_are_exact_and_drift_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    for reference in subject.DEPENDENCY_REFS.values():
        payload = Path(reference["path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == reference["sha256"]
        assert len(payload) == reference["size_bytes"]

    monkeypatch.setitem(subject.DEPENDENCY_REFS["owner_local_oracle_ref"], "sha256", "0" * 64)
    with pytest.raises(subject.ProvisionMovementFamily13FullStructuralOracleV1Error):
        _build([OWNER, "Dự phòng chung", *CORE])


def test_contract_contains_no_numeric_mapping_or_complete_document_claim() -> None:
    result = _build([OWNER, "Dự phòng chung", *CORE])
    forbidden = {"amount", "period", "report_norm_id", "sign", "unit"}

    def walk(value: object) -> None:
        if isinstance(value, dict):
            assert not forbidden & value.keys()
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(result)
