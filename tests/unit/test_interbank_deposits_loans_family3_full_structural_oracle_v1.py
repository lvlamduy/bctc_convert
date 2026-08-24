from __future__ import annotations

import copy
import shutil
from pathlib import Path

import pytest

from bctc_ai.evaluation import interbank_deposits_loans_family3_full_structural_oracle_v1 as full_v1
from bctc_ai.evaluation.interbank_deposits_loans_family3_full_structural_oracle_v1 import (
    InterbankDepositsLoansFamily3FullStructuralOracleV1Error,
    build_interbank_deposits_loans_family3_full_structural_oracle_v1,
    validate_interbank_deposits_loans_family3_full_structural_oracle_replay_v1,
)

_ROOT = Path(__file__).resolve().parents[2]


def _line(index: int, text: str, x1: int, y: int, x2: int) -> dict:
    return {
        "bbox": [x1, y, x2, y + 28],
        "source_line_index": index,
        "source_text": text,
        "vietocr_text": text,
    }


def _page(lines: list[dict], sequence: int = 1) -> dict:
    return {
        "lines": lines,
        "page_height": 1_400,
        "page_sequence": sequence,
        "page_width": 1_000,
    }


def _table(y: int = 30, index: int = 0, *, missing_loan_geometry: bool = False) -> list[dict]:
    roles = ["Tiền gửi không kỳ hạn", "Tiền gửi có kỳ hạn", "Cho vay các TCTD khác"]
    lines = [_line(index, "Tiền gửi và cho vay các TCTD khác", 40, y, 560)]
    index += 1
    for ordinal, role in enumerate(roles):
        row_y = y + 80 + ordinal * 58
        lines.append(_line(index, role, 60, row_y, 540))
        index += 1
        if missing_loan_geometry and role == "Cho vay các TCTD khác":
            continue
        lines.extend(
            [
                _line(index, str((ordinal + 1) * 100), 700, row_y, 770),
                _line(index + 1, str((ordinal + 1) * 90), 830, row_y, 900),
            ]
        )
        index += 2
    return lines


def test_unique_explicit_structure_and_zero_oracle_is_ready_proposal_only() -> None:
    pages = [_page(_table())]
    result = build_interbank_deposits_loans_family3_full_structural_oracle_v1(pages)

    assert result["status"] == "STRUCTURAL_READY_PROPOSAL_ONLY"
    assert result["disposition"] == "PROPOSAL_ONLY"
    assert result["structural_metrics"] == {
        "explicit_complete_cluster_count": 1,
        "independent_near_region_count": 0,
        "oracle_branchless_challenger_count": 0,
        "semantic_region_cluster_count": 1,
        "topology_complete_region_count": 1,
        "topology_core_semantic_anchor_hit_count": 3,
        "topology_near_region_count": 0,
        "topology_semantic_anchor_hit_count": 4,
    }
    assert result["absence"] == {"authority": False, "bounded_absences": []}
    assert not any(result["safety"].values())
    assert result["evidence_binding"]["dependency_content_refs"] == full_v1.TRUST_CLOSURE
    assert (
        result["semantic_proposal"]["result_id"]
        == result["evidence_binding"]["semantic_adapter_result_id"]
    )
    assert result["selected_structural_region"] == result["semantic_proposal"]["regions"][0]
    assert (
        result["selected_structural_region_id"] == result["selected_structural_region"]["region_id"]
    )
    assert result["selected_structural_candidates"] == [
        item
        for item in result["selected_structural_region"]["candidates"]
        if item["complete_required_role_combinations"]
    ]
    assert result["selected_structural_candidate_ids"] == [
        item["candidate_id"] for item in result["selected_structural_candidates"]
    ]
    assert result["selected_topology_region"] == result["topology_proposal"]["regions"][0]
    assert result["source_locator_alignment"]["status"] == (
        "EXACT_NONEMPTY_STRUCTURAL_SOURCE_LOCATOR_ALIGNMENT"
    )
    assert (
        full_v1.semantic_v1.validate_interbank_deposits_loans_family3_semantic_region_replay_v1(
            result["semantic_proposal"], pages, _ROOT
        )
        == result["semantic_proposal"]
    )


def test_topology_derives_combo_heads_and_all_remaining_child_roles() -> None:
    _refs, topology = full_v1._dependencies(_ROOT)
    spec = full_v1._oracle_spec(topology)
    heads = {item[0] for item in topology["required_role_combinations"]}
    roles = {item["role"] for item in spec["role_axis"]}

    assert heads == {"DEMAND_DEPOSIT_GROUP", "INTERBANK_DEPOSIT_GROUP"}
    assert not (heads & roles)
    assert roles == {item["role"] for item in topology["children"]} - heads
    assert set(spec["owner_aliases"]) == set(topology["parent"]["aliases"])
    assert spec["limits"] == {
        "continuation_page_budget": 1,
        "max_label_line_span": 3,
        "max_owner_distance_lines": 96,
    }


def test_semantic_and_oracle_zero_is_not_observed_without_absence_authority() -> None:
    result = build_interbank_deposits_loans_family3_full_structural_oracle_v1(
        [_page([_line(0, "Thuyết minh không liên quan", 40, 30, 500)])]
    )

    assert result["status"] == "NOT_OBSERVED_PROPOSAL_ONLY"
    assert result["disposition"] == "PROPOSAL_ONLY"
    assert result["absence"]["authority"] is False
    assert result["safety"]["authenticated_input_authority"] is False
    assert result["safety"]["document_completeness_authority"] is False
    assert result["input_axis"]["status"] == (
        "CALLER_SUPPLIED_CONTIGUOUS_1_TO_N_COMPLETE_LOOKING_ONLY"
    )
    assert result["topology_proposal"]["status"] == (
        "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    )
    assert result["topology_proposal"]["regions"] == []
    assert result["topology_proposal"]["near_regions"] == []
    assert result["structural_metrics"]["topology_core_semantic_anchor_hit_count"] == 0
    assert result["structural_metrics"]["topology_semantic_anchor_hit_count"] == 0


@pytest.mark.parametrize(
    "lines",
    [
        [_line(0, "Tiền gửi và cho vay các TCTD khác", 40, 30, 560)],
        [
            _line(0, "Tiền gửi có kỳ hạn", 60, 30, 540),
            _line(1, "Cho vay các TCTD khác", 60, 90, 540),
        ],
    ],
    ids=["owner-only", "ownerless-distinctive-pair"],
)
def test_nonzero_topology_anchor_evidence_is_unresolved(lines: list[dict]) -> None:
    result = build_interbank_deposits_loans_family3_full_structural_oracle_v1([_page(lines)])

    assert result["status"] == "UNRESOLVED_STRUCTURAL_EVIDENCE"
    assert result["disposition"] == "UNRESOLVED"
    assert result["structural_metrics"]["topology_semantic_anchor_hit_count"] > 0
    assert result["selected_structural_region"] is None
    assert result["selected_topology_region"] is None


def test_legitimate_nested_structural_candidates_align_to_one_topology_region() -> None:
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
    result = build_interbank_deposits_loans_family3_full_structural_oracle_v1([_page(lines)])

    assert result["status"] == "STRUCTURAL_READY_PROPOSAL_ONLY"
    assert len(result["selected_structural_candidates"]) == 2
    assert (
        result["source_locator_alignment"]["semantic_structural_locators"]
        == result["source_locator_alignment"]["topology_structural_locators"]
    )
    assert result["selected_topology_region"] == result["topology_proposal"]["regions"][0]


def test_branchless_multirole_challenger_forces_unresolved() -> None:
    lines = [
        _line(0, "Tiền gửi và cho vay các TCTD khác", 40, 30, 560),
        _line(1, "Tiền gửi có kỳ hạn", 60, 110, 540),
        _line(2, "100", 700, 110, 770),
        _line(3, "Cho vay các TCTD khác", 60, 180, 540),
        _line(4, "200", 700, 180, 770),
    ]
    result = build_interbank_deposits_loans_family3_full_structural_oracle_v1([_page(lines)])

    assert result["status"] == "UNRESOLVED_STRUCTURAL_EVIDENCE"
    assert result["disposition"] == "UNRESOLVED"
    assert result["structural_metrics"]["oracle_branchless_challenger_count"] == 1


@pytest.mark.parametrize(
    "lines",
    [
        [*_table(30, 0), *_table(430, 50)],
        [*_table(30, 0), *_table(430, 50, missing_loan_geometry=True)],
    ],
    ids=["multiple-complete", "complete-plus-independent-incomplete"],
)
def test_multiple_or_independent_competing_semantic_region_is_unresolved(
    lines: list[dict],
) -> None:
    result = build_interbank_deposits_loans_family3_full_structural_oracle_v1([_page(lines)])

    assert result["status"] == "UNRESOLVED_STRUCTURAL_EVIDENCE"
    assert result["disposition"] == "UNRESOLVED"
    assert result["structural_metrics"]["semantic_region_cluster_count"] == 2


def test_provider_order_public_replay_tamper_and_page_gap() -> None:
    pages = [_page(_table(), 1), _page([_line(0, "Không liên quan", 40, 30, 500)], 2)]
    expected = build_interbank_deposits_loans_family3_full_structural_oracle_v1(pages)
    reordered = copy.deepcopy(pages)
    reordered.reverse()
    for page in reordered:
        page["lines"].reverse()

    assert build_interbank_deposits_loans_family3_full_structural_oracle_v1(reordered) == expected
    assert (
        validate_interbank_deposits_loans_family3_full_structural_oracle_replay_v1(expected, pages)
        == expected
    )
    forged = copy.deepcopy(expected)
    forged["status"] = "FORGED"
    with pytest.raises(
        InterbankDepositsLoansFamily3FullStructuralOracleV1Error,
        match="content identity drifted",
    ):
        validate_interbank_deposits_loans_family3_full_structural_oracle_replay_v1(forged, pages)
    with pytest.raises(
        InterbankDepositsLoansFamily3FullStructuralOracleV1Error,
        match="exactly page_sequence 1..N",
    ):
        build_interbank_deposits_loans_family3_full_structural_oracle_v1(
            [pages[0], {**pages[1], "page_sequence": 3}]
        )


def test_each_dependency_builds_once_per_terminal_build_without_inner_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantic_build = full_v1.semantic_v1.build_interbank_deposits_loans_family3_semantic_region_v1
    topology_build = full_v1.topology_v1.build_accounting_family_topology_scan_v1
    oracle_build = full_v1.owner_v1.build_accounting_owner_local_branchless_oracle_v1
    calls = {"oracle": 0, "semantic": 0, "topology": 0}

    def counted_semantic(*args: object, **kwargs: object) -> dict:
        calls["semantic"] += 1
        return semantic_build(*args, **kwargs)

    def counted_topology(*args: object, **kwargs: object) -> dict:
        calls["topology"] += 1
        return topology_build(*args, **kwargs)

    def counted_oracle(*args: object, **kwargs: object) -> dict:
        calls["oracle"] += 1
        return oracle_build(*args, **kwargs)

    monkeypatch.setattr(
        full_v1.semantic_v1,
        "build_interbank_deposits_loans_family3_semantic_region_v1",
        counted_semantic,
    )
    monkeypatch.setattr(
        full_v1.topology_v1, "build_accounting_family_topology_scan_v1", counted_topology
    )
    monkeypatch.setattr(
        full_v1.owner_v1,
        "build_accounting_owner_local_branchless_oracle_v1",
        counted_oracle,
    )
    monkeypatch.setattr(
        full_v1.semantic_v1,
        "validate_interbank_deposits_loans_family3_semantic_region_replay_v1",
        lambda *_args, **_kwargs: pytest.fail("inner semantic replay must not run"),
    )
    monkeypatch.setattr(
        full_v1.owner_v1,
        "validate_accounting_owner_local_branchless_oracle_replay_v1",
        lambda *_args, **_kwargs: pytest.fail("inner oracle replay must not run"),
    )
    pages = [_page(_table())]
    result = build_interbank_deposits_loans_family3_full_structural_oracle_v1(pages)
    assert calls == {"oracle": 1, "semantic": 1, "topology": 1}
    assert (
        validate_interbank_deposits_loans_family3_full_structural_oracle_replay_v1(result, pages)
        == result
    )
    assert calls == {"oracle": 2, "semantic": 2, "topology": 2}


@pytest.mark.parametrize(
    "dependency",
    [
        "accounting_topology_engine",
        "evaluation_config",
        "owner_local_oracle",
        "semantic_adapter",
        "topology_config",
    ],
)
def test_replay_rejects_copied_config_and_dependency_ref_drift(
    dependency: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = [_page([_line(0, "Không liên quan", 40, 30, 500)])]
    result = build_interbank_deposits_loans_family3_full_structural_oracle_v1(pages)
    copied_root = tmp_path / "copied-root"
    for reference in full_v1.TRUST_CLOSURE.values():
        target = copied_root / reference["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_ROOT / reference["path"], target)
    monkeypatch.setattr(full_v1, "_PROJECT_ROOT", copied_root)
    assert (
        validate_interbank_deposits_loans_family3_full_structural_oracle_replay_v1(result, pages)
        == result
    )

    target = copied_root / full_v1.TRUST_CLOSURE[dependency]["path"]
    target.write_bytes(target.read_bytes() + b"\n# copied coherent drift\n")
    with pytest.raises(
        InterbankDepositsLoansFamily3FullStructuralOracleV1Error,
        match="dependency content reference drifted",
    ):
        validate_interbank_deposits_loans_family3_full_structural_oracle_replay_v1(result, pages)
