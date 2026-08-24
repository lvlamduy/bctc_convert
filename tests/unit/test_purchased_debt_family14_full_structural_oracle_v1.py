from __future__ import annotations

import copy
import hashlib
import shutil
from pathlib import Path

import pytest

from bctc_ai.evaluation import purchased_debt_family14_full_structural_oracle_v1 as full_v1
from bctc_ai.evaluation.purchased_debt_family14_full_structural_oracle_v1 import (
    CLAIM_BOUNDARY,
    DEPENDENCY_REFS_V1,
    PurchasedDebtFamily14FullStructuralOracleV1Error,
    build_purchased_debt_family14_full_structural_oracle_v1,
    validate_purchased_debt_family14_full_structural_oracle_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _line(index: int, text: str) -> dict[str, object]:
    return {
        "bbox": [40, 30 + 35 * index, 800, 54 + 35 * index],
        "source_line_index": index,
        "source_text": text,
        "vietocr_text": text,
    }


def _page(sequence: int, surfaces: list[str]) -> dict[str, object]:
    return {
        "lines": [_line(index, text) for index, text in enumerate(surfaces)],
        "page_height": 1_400,
        "page_sequence": sequence,
        "page_width": 1_000,
    }


def _ready_pages() -> list[dict[str, object]]:
    return [
        _page(
            1,
            [
                "Hoạt động mua nợ",
                "Mua nợ bằng VND",
                "Dự phòng chung",
                "Nợ gốc đã mua",
            ],
        )
    ]


def _rehash(result: dict[str, object]) -> None:
    material = copy.deepcopy(result)
    material.pop("result_id")
    result["result_id"] = "pdf14fsov1:result:" + canonical_json_sha256_v1(material)


def test_hdb_principal_only_variant_is_one_structural_ready_proposal() -> None:
    result = build_purchased_debt_family14_full_structural_oracle_v1(_ready_pages())

    assert result["status"] == "STRUCTURAL_READY_PROPOSAL_ONLY"
    assert result["metrics"] == {
        "branchless_challenger_count": 0,
        "complete_topology_region_count": 1,
        "mapping_count": 0,
        "near_topology_region_count": 0,
    }
    assert result["topology_proposal"]["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["branchless_oracle_proposal"]["challengers"] == []
    assert result["mappings"] == []
    assert result["observation_scope"] == (
        "CALLER_SUPPLIED_CONTIGUOUS_PAGE_AXIS_ONLY_NO_COMPLETENESS_PROOF"
    )
    assert "NO_AUTHENTICATION_COMPLETENESS_ABSENCE" in CLAIM_BOUNDARY
    assert result["authority"]["structural_proposal_authority"] is True
    assert all(
        result["authority"][key] is False
        for key in (
            "absence_authority",
            "authentication_authority",
            "caller_page_axis_completeness_authority",
            "equation_authority",
            "mapping_authority",
            "numeric_authority",
            "schema_authority",
        )
    )


def test_missing_vnd_with_two_distinctive_roles_is_unresolved_challenger() -> None:
    result = build_purchased_debt_family14_full_structural_oracle_v1(
        [
            _page(
                1,
                [
                    "Hoạt động mua nợ",
                    "Dự phòng rủi ro mua nợ",
                    "Nợ gốc đã mua",
                ],
            )
        ]
    )

    assert result["status"] == "UNRESOLVED_BRANCHLESS_CHALLENGER_PROPOSAL_ONLY"
    assert result["metrics"]["complete_topology_region_count"] == 0
    challenger = result["branchless_oracle_proposal"]["challengers"][0]
    assert challenger["disposition"] == "UNRESOLVED"
    assert challenger["observed_role_ids"] == [
        "PRINCIPAL_DETAIL_ROW",
        "PROVISION_BALANCE_ROW",
    ]
    assert result["mappings"] == []


def test_two_complete_tables_are_structural_ambiguity_not_ready() -> None:
    cluster = [
        "Hoạt động mua nợ",
        "Mua nợ bằng VND",
        "Dự phòng rủi ro mua nợ",
        "Nợ gốc đã mua",
    ]
    result = build_purchased_debt_family14_full_structural_oracle_v1(
        [_page(1, [*cluster, *cluster])]
    )

    assert result["status"] == "UNRESOLVED_STRUCTURAL_AMBIGUITY_PROPOSAL_ONLY"
    assert result["metrics"]["complete_topology_region_count"] == 2
    assert result["topology_proposal"]["status"] == (
        "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS"
    )


def test_zero_is_caller_axis_only_not_observed_and_never_absence() -> None:
    result = build_purchased_debt_family14_full_structural_oracle_v1(
        [_page(1, ["Nội dung không liên quan"])]
    )

    assert result["status"] == "NOT_OBSERVED_PROPOSAL_ONLY"
    assert result["metrics"]["complete_topology_region_count"] == 0
    assert result["metrics"]["branchless_challenger_count"] == 0
    assert result["topology_proposal"]["status"] == (
        "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    )
    assert result["topology_proposal"]["metrics"]["core_semantic_anchor_hit_count"] == 0
    assert result["authority"]["not_observed_is_absence"] is False
    assert result["authority"]["absence_authority"] is False
    assert result["mappings"] == []


@pytest.mark.parametrize(
    "page_surfaces",
    [
        [["Hoạt động mua nợ"]],
        [["Hoạt động mua nợ", "Mua nợ bằng VND"]],
        [
            [
                "Hoạt động mua nợ",
                "Mua nợ bằng VND",
                "Dự phòng rủi ro mua nợ",
                "Chi phí dự phòng rủi ro tín dụng",
                "Nợ gốc đã mua",
            ]
        ],
        [
            [
                "Hoạt động mua nợ",
                "Mua nợ bằng VND",
                "Dự phòng rủi ro mua nợ",
                "Chứng khoán đầu tư",
                "Nợ gốc đã mua",
            ]
        ],
        [
            ["Hoạt động mua nợ", "Mua nợ bằng VND", "Dự phòng rủi ro mua nợ"],
            ["Thuyết minh khác"],
            ["Nợ gốc đã mua"],
        ],
    ],
    ids=["owner", "partial", "hard-veto", "reset", "continuation-budget"],
)
def test_owner_or_partial_near_evidence_is_never_not_observed(
    page_surfaces: list[list[str]],
) -> None:
    pages = [_page(sequence, surfaces) for sequence, surfaces in enumerate(page_surfaces, 1)]
    result = build_purchased_debt_family14_full_structural_oracle_v1(pages)

    assert result["status"] == "UNRESOLVED_STRUCTURAL_AMBIGUITY_PROPOSAL_ONLY"
    assert result["topology_proposal"]["near_regions"]
    assert result["metrics"]["branchless_challenger_count"] == 0


def test_one_page_continuation_is_ready_but_gap_fails_closed() -> None:
    continued = build_purchased_debt_family14_full_structural_oracle_v1(
        [
            _page(
                1,
                ["Hoạt động mua nợ", "Mua nợ bằng VND", "Dự phòng rủi ro mua nợ"],
            ),
            _page(2, ["Nợ gốc đã mua"]),
        ]
    )
    assert continued["status"] == "STRUCTURAL_READY_PROPOSAL_ONLY"
    assert continued["topology_proposal"]["regions"][0]["continuation_page_count"] == 1
    with pytest.raises(PurchasedDebtFamily14FullStructuralOracleV1Error, match="1..N"):
        build_purchased_debt_family14_full_structural_oracle_v1(
            [_page(1, ["Hoạt động mua nợ"]), _page(3, ["Nợ gốc đã mua"])]
        )


def test_provider_page_and_line_reorder_is_canonical() -> None:
    pages = [
        _page(
            1,
            ["Hoạt động mua nợ", "Mua nợ bằng VND", "Dự phòng rủi ro mua nợ"],
        ),
        _page(2, ["Nợ gốc đã mua"]),
    ]
    expected = build_purchased_debt_family14_full_structural_oracle_v1(pages)
    reordered = copy.deepcopy(pages)
    reordered.reverse()
    for page in reordered:
        page["lines"].reverse()

    assert build_purchased_debt_family14_full_structural_oracle_v1(reordered) == expected


def test_build_and_replay_each_run_both_shared_engines_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    topology = full_v1.build_purchased_debt_family14_topology_scan_v1
    branchless = full_v1.build_accounting_owner_local_branchless_oracle_v1
    calls = {"branchless": 0, "topology": 0}

    def counted_topology(pages: object) -> dict[str, object]:
        calls["topology"] += 1
        return topology(pages)

    def counted_branchless(pages: object, spec: object) -> dict[str, object]:
        calls["branchless"] += 1
        return branchless(pages, spec)

    monkeypatch.setattr(full_v1, "build_purchased_debt_family14_topology_scan_v1", counted_topology)
    monkeypatch.setattr(
        full_v1, "build_accounting_owner_local_branchless_oracle_v1", counted_branchless
    )
    pages = _ready_pages()
    result = build_purchased_debt_family14_full_structural_oracle_v1(pages)
    assert calls == {"branchless": 1, "topology": 1}
    assert validate_purchased_debt_family14_full_structural_oracle_replay_v1(
        result, pages
    ) == result
    assert calls == {"branchless": 2, "topology": 2}


def test_replay_rejects_coherent_tamper_and_dependency_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = _ready_pages()
    result = build_purchased_debt_family14_full_structural_oracle_v1(pages)
    forged = copy.deepcopy(result)
    forged["status"] = "FORGED"
    _rehash(forged)
    with pytest.raises(PurchasedDebtFamily14FullStructuralOracleV1Error, match="replay exactly"):
        validate_purchased_debt_family14_full_structural_oracle_replay_v1(forged, pages)

    copied_root = tmp_path / "copied-root"
    for reference in DEPENDENCY_REFS_V1.values():
        source = _PROJECT_ROOT / reference["path"]
        target = copied_root / reference["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert reference["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
        assert reference["size_bytes"] == source.stat().st_size
    monkeypatch.setattr(full_v1, "_PROJECT_ROOT", copied_root)
    assert validate_purchased_debt_family14_full_structural_oracle_replay_v1(
        result, pages
    ) == result
    dependency = copied_root / DEPENDENCY_REFS_V1["shared_topology_engine_ref"]["path"]
    dependency.write_bytes(dependency.read_bytes() + b"\n")
    with pytest.raises(
        PurchasedDebtFamily14FullStructuralOracleV1Error,
        match="dependency content reference drifted",
    ):
        validate_purchased_debt_family14_full_structural_oracle_replay_v1(result, pages)
