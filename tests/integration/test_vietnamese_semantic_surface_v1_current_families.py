from __future__ import annotations

from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
)
from bctc_ai.source_structure.vietnamese_semantic_surface_v1 import (
    compile_vietnamese_family_alias_index_v1,
    propose_vietnamese_semantic_surface_v1,
)


def test_transformer_like_surfaces_are_safe_shortlists_for_current_quality_maturity_specs():
    index = compile_vietnamese_family_alias_index_v1(
        (LOAN_QUALITY_CLASSIFICATION_SPEC_V1, LOAN_MATURITY_BUCKETS_SPEC_V1)
    )

    short_term = propose_vietnamese_semantic_surface_v1("Nơ ngắn hạn", index)
    loss = propose_vietnamese_semantic_surface_v1("Nợ có khả năng mất vôn", index)
    unsupported_branch = propose_vietnamese_semantic_surface_v1(
        "Phân tích dư nợ cho vay góc", index
    )

    assert short_term.status == "UNRESOLVED_ACCENTLESS_ALIAS_CANDIDATE"
    assert short_term.accentless_comparison_key == "no ngan han"
    assert short_term.comparison_keys_consulted == ("no ngan han", "ngan han")
    assert short_term.presentation_prefix_removed is True
    assert [(item.family_id, item.role) for item in short_term.candidates] == [
        ("LOAN_MATURITY_BUCKETS", "SHORT_TERM")
    ]
    assert short_term.candidates[0].observed_comparison_key == "ngan han"
    assert (
        short_term.candidates[0].presentation_normalization
        == "LEADING_DEBT_ROW_PRESENTATION_PREFIX"
    )

    assert loss.status == "UNRESOLVED_ACCENTLESS_ALIAS_CANDIDATE"
    assert [(item.family_id, item.role) for item in loss.candidates] == [
        ("LOAN_QUALITY_CLASSIFICATION", "LOSS")
    ]
    assert loss.candidates[0].observed_comparison_key == "no co kha nang mat von"
    assert loss.candidates[0].presentation_normalization == "NONE"

    # "góc" is not merely an accent variant of any current maturity-branch
    # alias.  The no-fuzzy contract must retain it as no candidate, rather than
    # silently repairing it to "thời gian" or "thời hạn".
    assert unsupported_branch.status == "NO_ALIAS_CANDIDATE"
    assert unsupported_branch.candidates == ()

    for proposal in (short_term, loss, unsupported_branch):
        assert proposal.semantic_identity_authority is False
        assert proposal.structure_acceptance_authority is False
        assert proposal.automatic_correction_applied is False
        assert proposal.fuzzy_edit_matching_used is False


def test_current_unaccented_family_aliases_remain_shortlist_only_for_accented_text():
    index = compile_vietnamese_family_alias_index_v1(
        (LOAN_QUALITY_CLASSIFICATION_SPEC_V1, LOAN_MATURITY_BUCKETS_SPEC_V1)
    )

    proposal = propose_vietnamese_semantic_surface_v1("Nợ đủ tiêu chuẩn", index)

    assert proposal.status == "UNRESOLVED_ACCENTLESS_ALIAS_CANDIDATE"
    assert [(item.family_id, item.role, item.match_kind) for item in proposal.candidates] == [
        ("LOAN_QUALITY_CLASSIFICATION", "STANDARD", "ACCENTLESS_ALIAS_ONLY")
    ]
    assert proposal.independent_local_topology_required is True
    assert proposal.semantic_identity_authority is False
    assert proposal.structure_acceptance_authority is False
