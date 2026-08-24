from __future__ import annotations

import copy
import shutil
from pathlib import Path

import pytest

from bctc_ai.evaluation import accounting_owner_local_branchless_oracle_v1 as oracle_v1
from bctc_ai.evaluation.accounting_owner_local_branchless_oracle_v1 import (
    AccountingOwnerLocalBranchlessOracleV1Error,
    build_accounting_owner_local_branchless_oracle_v1,
    validate_accounting_owner_local_branchless_oracle_replay_v1,
)


def _line(index: int, text: str, y: int) -> dict:
    return {
        "bbox": [40, y, 700, y + 24],
        "source_line_index": index,
        "source_text": text,
        "vietocr_text": text,
    }


def _page(sequence: int, lines: list[dict]) -> dict:
    return {"lines": lines, "page_height": 1_000, "page_sequence": sequence, "page_width": 1_000}


def _spec(*, budget: int = 0) -> dict:
    return {
        "explicit_branch_aliases": ["Explicit branch"],
        "family_id": "GENERIC_TEST_FAMILY",
        "format_version": "ACCOUNTING_OWNER_LOCAL_BRANCHLESS_SPEC_V1",
        "hard_veto_aliases": ["Hard veto"],
        "limits": {
            "continuation_page_budget": budget,
            "max_label_line_span": 2,
            "max_owner_distance_lines": 40,
        },
        "owner_aliases": ["Family owner"],
        "role_axis": [
            {"aliases": ["Role alpha"], "role": "ROLE_ALPHA"},
            {"aliases": ["Role beta"], "role": "ROLE_BETA"},
            {"aliases": ["Role gamma"], "role": "ROLE_GAMMA"},
        ],
        "structural_reset_aliases": ["Structural reset"],
    }


def _build(lines: list[dict], *, budget: int = 0) -> dict:
    return build_accounting_owner_local_branchless_oracle_v1(
        [_page(1, lines)], _spec(budget=budget)
    )


def test_distinct_roles_create_one_proposal_only_challenger() -> None:
    result = _build(
        [_line(0, "Family owner", 20), _line(1, "Role alpha", 70), _line(2, "Role beta", 110)]
    )

    assert result["status"] == "BRANCHLESS_CHALLENGERS_RETAINED_PROPOSAL_ONLY"
    assert result["metrics"] == {
        "challenger_count": 1,
        "explicit_branch_suppressed_component_count": 0,
        "owner_component_count": 1,
        "pair_uniqueness_evidence_count": 1,
        "triple_combination_enumeration_count": 0,
    }
    challenger = result["challengers"][0]
    assert challenger["disposition"] == "UNRESOLVED"
    assert challenger["observed_role_ids"] == ["ROLE_ALPHA", "ROLE_BETA"]
    assert challenger["minimal_uniqueness_evidence"] == {
        "combination_size": 2,
        "pair_before_triple_search": True,
        "role_ids": ["ROLE_ALPHA", "ROLE_BETA"],
    }
    assert result["bounded_absences"] == []
    assert all(
        result["authority"][key] is False
        for key in (
            "absence_authority",
            "mapping_authority",
            "numeric_authority",
            "schema_authority",
            "zero_evidence_is_absence",
        )
    )


def test_same_component_branch_suppresses_but_branch_elsewhere_does_not() -> None:
    lines = [
        _line(0, "Family owner", 20),
        _line(1, "Explicit branch", 60),
        _line(2, "Role alpha", 100),
        _line(3, "Role beta", 140),
        _line(4, "Family owner", 240),
        _line(5, "Role alpha", 280),
        _line(6, "Role beta", 320),
    ]
    result = _build(lines)

    assert result["metrics"]["challenger_count"] == 1
    assert result["metrics"]["explicit_branch_suppressed_component_count"] == 1
    assert result["challengers"][0]["owner"]["evidence"][0]["source_line_index"] == 4


def test_one_owner_branchless_sibling_before_later_explicit_branch_is_preserved() -> None:
    result = _build(
        [
            _line(0, "Family owner", 20),
            _line(1, "Role alpha", 60),
            _line(2, "Role beta", 100),
            _line(3, "Explicit branch", 200),
            _line(4, "Role alpha", 240),
            _line(5, "Role beta", 280),
        ]
    )

    assert result["metrics"]["explicit_branch_suppressed_component_count"] == 1
    assert result["metrics"]["challenger_count"] == 1
    assert result["challengers"][0]["role_matches"][0]["evidence"][0]["source_line_index"] == 1


def test_explicit_taint_survives_duplicate_role_split() -> None:
    result = _build(
        [
            _line(0, "Family owner", 20),
            _line(1, "Explicit branch", 60),
            _line(2, "Role alpha", 100),
            _line(3, "Role alpha", 140),
            _line(4, "Role beta", 180),
        ]
    )

    assert result["challengers"] == []
    assert result["metrics"]["explicit_branch_suppressed_component_count"] == 1


def test_suppressed_explicit_signature_is_still_a_uniqueness_competitor() -> None:
    result = _build(
        [
            _line(0, "Family owner", 20),
            _line(1, "Explicit branch", 60),
            _line(2, "Role alpha", 100),
            _line(3, "Role beta", 140),
            _line(4, "Family owner", 240),
            _line(5, "Role alpha", 280),
            _line(6, "Role beta", 320),
        ]
    )

    assert result["metrics"]["challenger_count"] == 1
    assert result["challengers"][0]["minimal_uniqueness_evidence"] is None


@pytest.mark.parametrize("fence", ["Structural reset", "Hard veto"])
def test_reset_and_hard_veto_split_owner_component(fence: str) -> None:
    result = _build(
        [
            _line(0, "Family owner", 20),
            _line(1, "Role alpha", 60),
            _line(2, fence, 100),
            _line(3, "Role beta", 140),
        ]
    )
    assert result["challengers"] == []


def test_repeated_same_role_is_not_a_distinct_role_pair_and_no_triples_are_enumerated() -> None:
    repeated = _build(
        [_line(0, "Family owner", 20), _line(1, "Role alpha", 60), _line(2, "Role alpha", 100)]
    )
    assert repeated["challengers"] == []

    three = _build(
        [
            _line(0, "Family owner", 20),
            _line(1, "Role gamma", 60),
            _line(2, "Role beta", 100),
            _line(3, "Role alpha", 140),
        ]
    )
    assert three["challengers"][0]["observed_role_ids"] == ["ROLE_ALPHA", "ROLE_BETA", "ROLE_GAMMA"]
    assert three["metrics"]["triple_combination_enumeration_count"] == 0


def test_all_independent_owner_clusters_are_retained() -> None:
    result = _build(
        [
            _line(0, "Family owner", 20),
            _line(1, "Role alpha", 60),
            _line(2, "Role beta", 100),
            _line(3, "Family owner", 200),
            _line(4, "Role beta", 240),
            _line(5, "Role gamma", 280),
        ]
    )
    assert result["metrics"]["challenger_count"] == 2
    assert {
        item["owner"]["evidence"][0]["source_line_index"] for item in result["challengers"]
    } == {0, 3}


def test_one_owner_repeated_sibling_clusters_are_all_retained_without_false_uniqueness() -> None:
    result = _build(
        [
            _line(0, "Family owner", 20),
            _line(1, "Role alpha", 60),
            _line(2, "Role beta", 100),
            _line(3, "Role alpha", 200),
            _line(4, "Role beta", 240),
        ]
    )

    assert result["metrics"]["challenger_count"] == 2
    assert all(item["minimal_uniqueness_evidence"] is None for item in result["challengers"])
    assert [
        item["role_matches"][0]["evidence"][0]["source_line_index"]
        for item in result["challengers"]
    ] == [1, 3]


def test_triple_is_lazy_and_only_follows_exhausted_nonunique_pairs() -> None:
    lines = []
    for owner_index, roles in enumerate(
        [
            ("Role alpha", "Role beta", "Role gamma"),
            ("Role alpha", "Role beta"),
            ("Role alpha", "Role gamma"),
            ("Role beta", "Role gamma"),
        ]
    ):
        base = owner_index * 5
        y = 20 + owner_index * 200
        lines.append(_line(base, "Family owner", y))
        lines.extend(
            _line(base + offset, role, y + offset * 40) for offset, role in enumerate(roles, 1)
        )
    result = _build(lines)

    triple = next(item for item in result["challengers"] if len(item["observed_role_ids"]) == 3)
    assert triple["minimal_uniqueness_evidence"]["combination_size"] == 3
    assert result["metrics"]["triple_combination_enumeration_count"] == 1


def test_provider_order_and_wrapped_owner_are_canonical() -> None:
    pages = [
        _page(
            1,
            [
                _line(0, "Family", 20),
                _line(1, "owner", 46),
                _line(2, "Role alpha", 100),
                _line(3, "Role beta", 140),
            ],
        )
    ]
    expected = build_accounting_owner_local_branchless_oracle_v1(pages, _spec())
    reversed_pages = copy.deepcopy(pages)
    reversed_pages[0]["lines"].reverse()
    assert build_accounting_owner_local_branchless_oracle_v1(reversed_pages, _spec()) == expected
    assert expected["metrics"]["challenger_count"] == 1


def test_cross_page_requires_budget_and_every_contiguous_bridge() -> None:
    pages = [
        _page(1, [_line(0, "Family owner", 20)]),
        _page(2, [_line(0, "Role alpha", 20), _line(1, "Role beta", 60)]),
    ]
    assert (
        build_accounting_owner_local_branchless_oracle_v1(pages, _spec(budget=0))["challengers"]
        == []
    )
    assert (
        len(
            build_accounting_owner_local_branchless_oracle_v1(pages, _spec(budget=1))["challengers"]
        )
        == 1
    )
    gap = [pages[0], {**pages[1], "page_sequence": 3}]
    assert (
        build_accounting_owner_local_branchless_oracle_v1(gap, _spec(budget=2))["challengers"] == []
    )


def test_role_axis_and_per_role_alias_work_are_hard_bounded() -> None:
    pages = [_page(1, [_line(0, "Unrelated", 20)])]
    bounded = _spec()
    bounded["role_axis"] = [
        {
            "aliases": [f"Role {role:02d} alias {alias:02d}" for alias in range(64)],
            "role": f"ROLE_{role:02d}",
        }
        for role in range(64)
    ]
    assert build_accounting_owner_local_branchless_oracle_v1(pages, bounded)["challengers"] == []

    too_many_roles = copy.deepcopy(bounded)
    too_many_roles["role_axis"].append({"aliases": ["Overflow role"], "role": "ROLE_64"})
    with pytest.raises(AccountingOwnerLocalBranchlessOracleV1Error, match="fields drifted"):
        build_accounting_owner_local_branchless_oracle_v1(pages, too_many_roles)
    too_many_aliases = copy.deepcopy(bounded)
    too_many_aliases["role_axis"][0]["aliases"].append("Overflow alias")
    with pytest.raises(AccountingOwnerLocalBranchlessOracleV1Error, match="role fields drifted"):
        build_accounting_owner_local_branchless_oracle_v1(pages, too_many_aliases)


@pytest.mark.parametrize(
    ("field", "count"),
    [
        *(
            (field, 0)
            for field in ("explicit_branch_aliases", "owner_aliases", "hard_veto_aliases")
        ),
        *(
            (field, 65)
            for field in (
                "explicit_branch_aliases",
                "owner_aliases",
                "hard_veto_aliases",
                "structural_reset_aliases",
            )
        ),
        *(
            (field, 10_000)
            for field in (
                "explicit_branch_aliases",
                "owner_aliases",
                "hard_veto_aliases",
                "structural_reset_aliases",
            )
        ),
    ],
)
def test_context_alias_cardinality_rejects_before_shared_alias_work(
    field: str, count: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = _spec()
    spec[field] = [f"{field} {index}" for index in range(count)]
    monkeypatch.setattr(
        oracle_v1.semantic_v1,
        "_aliases",
        lambda *_args, **_kwargs: pytest.fail("shared aliases must not run"),
    )
    with pytest.raises(AccountingOwnerLocalBranchlessOracleV1Error, match="fields drifted"):
        build_accounting_owner_local_branchless_oracle_v1(
            [_page(1, [_line(0, "Unrelated", 20)])], spec
        )


def test_replay_rejects_copied_semantic_engine_content_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pages = [_page(1, [_line(0, "Unrelated", 20)])]
    spec = _spec()
    result = build_accounting_owner_local_branchless_oracle_v1(pages, spec)
    relative = Path(oracle_v1.SEMANTIC_ENGINE_CONTENT_REF["path"])
    copied_root = tmp_path / "copied-root"
    target = copied_root / relative
    target.parent.mkdir(parents=True)
    shutil.copyfile(Path(oracle_v1.semantic_v1.__file__), target)
    monkeypatch.setattr(oracle_v1, "_PROJECT_ROOT", copied_root)
    assert (
        validate_accounting_owner_local_branchless_oracle_replay_v1(result, pages, spec) == result
    )

    target.write_bytes(target.read_bytes() + b"\n# coherent copied dependency drift\n")
    with pytest.raises(
        AccountingOwnerLocalBranchlessOracleV1Error,
        match="dependency content reference drifted",
    ):
        validate_accounting_owner_local_branchless_oracle_replay_v1(result, pages, spec)


def test_zero_replay_tamper_and_spec_drift_fail_closed() -> None:
    pages = [_page(1, [_line(0, "Unrelated", 20)])]
    spec = _spec()
    result = build_accounting_owner_local_branchless_oracle_v1(pages, spec)
    assert result["status"] == "ZERO_BRANCHLESS_CHALLENGER_PROPOSAL_ONLY"
    assert (
        validate_accounting_owner_local_branchless_oracle_replay_v1(result, pages, spec) == result
    )

    forged = copy.deepcopy(result)
    forged["status"] = "FORGED"
    with pytest.raises(
        AccountingOwnerLocalBranchlessOracleV1Error, match="content identity drifted"
    ):
        validate_accounting_owner_local_branchless_oracle_replay_v1(forged, pages, spec)
    drifted = copy.deepcopy(spec)
    drifted["owner_aliases"] = ["Different owner"]
    with pytest.raises(
        AccountingOwnerLocalBranchlessOracleV1Error, match="does not replay exactly"
    ):
        validate_accounting_owner_local_branchless_oracle_replay_v1(result, pages, drifted)
