from __future__ import annotations

import copy
from pathlib import Path

import pytest

import bctc_ai.evaluation.family_first_semantic_label_plan_v1 as plan_v1

ROOT = Path(__file__).resolve().parents[2]
MODEL_CACHE = Path("/workspace/bctc-ai-models")


def _git_binding(_root: Path) -> dict[str, object]:
    return {
        "commit": "1" * 40,
        "implementation_refs": [],
        "source_tree_oid": "2" * 40,
        "worktree_clean": True,
    }


@pytest.fixture
def plan(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    monkeypatch.setattr(plan_v1, "_git_binding", _git_binding)
    return plan_v1.build_family_first_semantic_label_plan_v1(ROOT, model_cache=MODEL_CACHE)


def test_plan_covers_exact_inventory_and_live_pdf_page_denominator(plan) -> None:
    assert plan["metrics"] == {
        "document_count": 140,
        "explicit_missing_filing_count": 4,
        "page_count": 8_947,
    }
    assert [item["document_ordinal"] for item in plan["documents"]] == list(range(1, 141))
    assert sum(item["page_count"] for item in plan["documents"]) == 8_947
    assert plan["authority"]["bank_path_period_scope_used_for_family_matching"] is False
    assert plan["authority"]["related_party_family_in_scope"] is False
    assert plan["detector"]["enable_mkldnn"] is False
    assert len(plan["detector"]["required_files"]) == 3


def test_plan_replays_and_coordinated_tamper_is_rejected(
    plan, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(plan_v1, "_git_binding", _git_binding)
    assert (
        plan_v1.validate_family_first_semantic_label_plan_replay_v1(
            plan,
            ROOT,
            model_cache=MODEL_CACHE,
        )
        == plan
    )
    changed = copy.deepcopy(plan)
    changed["documents"][0]["page_count"] -= 1

    with pytest.raises(plan_v1.FamilyFirstSemanticLabelPlanV1Error):
        plan_v1.validate_family_first_semantic_label_plan_replay_v1(
            changed,
            ROOT,
            model_cache=MODEL_CACHE,
        )


def test_nested_project_root_and_raw_type_coercion_fail_closed(
    plan, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(plan_v1.FamilyFirstSemanticLabelPlanV1Error, match="Git toplevel"):
        plan_v1.build_family_first_semantic_label_plan_v1(
            ROOT / "output",
            model_cache=MODEL_CACHE,
        )
    changed = copy.deepcopy(plan)
    changed["metrics"]["page_count"] = 8_947.0
    monkeypatch.setattr(plan_v1, "_git_binding", _git_binding)

    with pytest.raises(plan_v1.FamilyFirstSemanticLabelPlanV1Error):
        plan_v1.validate_family_first_semantic_label_plan_replay_v1(
            changed,
            ROOT,
            model_cache=MODEL_CACHE,
        )
