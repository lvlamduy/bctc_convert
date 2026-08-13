from __future__ import annotations

import unicodedata

import pytest

from bctc_ai.source_structure.local_accounting_graph_v1 import (
    FamilySpecV1,
    RowRoleSpecV1,
)
from bctc_ai.source_structure.vietnamese_semantic_surface_v1 import (
    VietnameseSemanticSurfaceContractError,
    compile_vietnamese_family_alias_index_v1,
    propose_vietnamese_semantic_surface_v1,
)


def _spec(
    family_id: str,
    *,
    ordered_children: tuple[RowRoleSpecV1, ...],
    owner_aliases: tuple[str, ...] = ("Cho vay khách hàng",),
    branch_aliases: tuple[str, ...] = ("Phân tích",),
    total_aliases: tuple[str, ...] = ("Tổng cộng",),
) -> FamilySpecV1:
    return FamilySpecV1(
        family_id=family_id,
        owner_aliases=owner_aliases,
        branch_aliases=branch_aliases,
        ordered_children=ordered_children,
        optional_children=(),
        total_aliases=total_aliases,
        closure_child_roles=tuple(child.role for child in ordered_children),
    )


def test_decomposed_transformer_text_is_preserved_as_nfc_and_shortlisted_without_accents():
    spec = _spec(
        "LOAN_QUALITY",
        ordered_children=(RowRoleSpecV1("STANDARD", ("no du tieu chuan",)),),
    )
    index = compile_vietnamese_family_alias_index_v1((spec,))
    decomposed = unicodedata.normalize("NFD", "  1. Nợ đủ tiêu chuẩn:  ")

    proposal = propose_vietnamese_semantic_surface_v1(decomposed, index)

    assert proposal.raw_transcript_nfc == unicodedata.normalize("NFC", decomposed)
    assert proposal.normalized_vietnamese_surface == "nợ đủ tiêu chuẩn"
    assert proposal.accentless_comparison_key == "no du tieu chuan"
    assert proposal.comparison_keys_consulted == ("no du tieu chuan", "du tieu chuan")
    assert proposal.presentation_prefix_removed is True
    assert proposal.status == "UNRESOLVED_ACCENTLESS_ALIAS_CANDIDATE"
    assert len(proposal.candidates) == 1
    candidate = proposal.candidates[0]
    assert candidate.match_kind == "ACCENTLESS_ALIAS_ONLY"
    assert candidate.family_id == "LOAN_QUALITY"
    assert candidate.role_kind == "ORDERED_CHILD"
    assert candidate.role == "STANDARD"
    assert candidate.family_spec_json_pointer == "/ordered_children/0/aliases/0"
    assert candidate.alias_text_nfc == "no du tieu chuan"
    assert candidate.observed_comparison_key == "no du tieu chuan"
    assert candidate.presentation_normalization == "NONE"
    assert proposal.accentless_key_shortlist_only is True
    assert proposal.semantic_identity_authority is False
    assert proposal.structure_acceptance_authority is False
    assert proposal.independent_local_topology_required is True
    assert proposal.automatic_correction_applied is False
    assert proposal.fuzzy_edit_matching_used is False


def test_d_stroke_and_casefold_have_one_deterministic_accentless_key():
    spec = _spec(
        "INVESTMENT",
        ordered_children=(RowRoleSpecV1("INVESTMENT_ROW", ("dau tu",)),),
    )
    index = compile_vietnamese_family_alias_index_v1((spec,))

    proposal = propose_vietnamese_semantic_surface_v1("ĐẦU TƯ", index)

    assert proposal.normalized_vietnamese_surface == "đầu tư"
    assert proposal.accentless_comparison_key == "dau tu"
    assert proposal.status == "UNRESOLVED_ACCENTLESS_ALIAS_CANDIDATE"


def test_exact_accented_surface_is_a_candidate_but_never_acceptance_authority():
    spec = _spec(
        "LOAN_QUALITY",
        ordered_children=(RowRoleSpecV1("STANDARD", ("Nợ đủ tiêu chuẩn",)),),
    )
    index = compile_vietnamese_family_alias_index_v1((spec,))

    proposal = propose_vietnamese_semantic_surface_v1("Nợ đủ tiêu chuẩn", index)

    assert proposal.status == "EXACT_VIETNAMESE_SURFACE_CANDIDATE"
    assert [candidate.match_kind for candidate in proposal.candidates] == [
        "EXACT_VIETNAMESE_SURFACE"
    ]
    assert proposal.semantic_identity_authority is False
    assert proposal.structure_acceptance_authority is False
    assert proposal.independent_local_topology_required is True


def test_same_accentless_key_collision_retains_every_claim_and_stays_unresolved():
    first = _spec(
        "FIRST_FAMILY",
        ordered_children=(RowRoleSpecV1("FIRST_ROLE", ("má",)),),
    )
    second = _spec(
        "SECOND_FAMILY",
        ordered_children=(RowRoleSpecV1("SECOND_ROLE", ("mà",)),),
    )
    index = compile_vietnamese_family_alias_index_v1((second, first))

    accentless = propose_vietnamese_semantic_surface_v1("ma", index)
    exact_but_colliding = propose_vietnamese_semantic_surface_v1("má", index)

    assert accentless.status == "UNRESOLVED_ALIAS_KEY_COLLISION"
    assert exact_but_colliding.status == "UNRESOLVED_ALIAS_KEY_COLLISION"
    assert [(item.family_id, item.role) for item in accentless.candidates] == [
        ("FIRST_FAMILY", "FIRST_ROLE"),
        ("SECOND_FAMILY", "SECOND_ROLE"),
    ]
    assert accentless.collision_set == accentless.candidates
    assert exact_but_colliding.collision_set == exact_but_colliding.candidates
    assert [item.match_kind for item in exact_but_colliding.candidates] == [
        "EXACT_VIETNAMESE_SURFACE",
        "ACCENTLESS_ALIAS_ONLY",
    ]
    collision = next(
        collision
        for collision in index.collisions
        if collision.comparison_scope == "FULL_ACCENTLESS_KEY"
        and collision.accentless_comparison_key == "ma"
    )
    assert [(item.family_id, item.role) for item in collision.candidates] == [
        ("FIRST_FAMILY", "FIRST_ROLE"),
        ("SECOND_FAMILY", "SECOND_ROLE"),
    ]


@pytest.mark.parametrize(
    ("raw_transcript", "expected_status"),
    [
        ("30/06/2026", "PROTECTED_PERIOD_CONTEXT"),
        ("Quý II năm 2026", "PROTECTED_PERIOD_CONTEXT"),
        ("Đơn vị tính: triệu đồng", "PROTECTED_UNIT_CONTEXT"),
        ("%", "PROTECTED_UNIT_CONTEXT"),
        ("(1.234.567)", "PROTECTED_NUMERIC_CONTEXT"),
        ("-", "PROTECTED_NUMERIC_CONTEXT"),
    ],
)
def test_period_unit_and_numeric_surfaces_never_enter_alias_matching(
    raw_transcript, expected_status
):
    spec = _spec(
        "PROTECTED_CONTEXT_CHECK",
        ordered_children=(RowRoleSpecV1("ROW", ("Nợ đủ tiêu chuẩn",)),),
    )
    index = compile_vietnamese_family_alias_index_v1((spec,))

    proposal = propose_vietnamese_semantic_surface_v1(raw_transcript, index)

    assert proposal.status == expected_status
    assert proposal.candidates == ()
    assert proposal.collision_set == ()
    assert proposal.independent_local_topology_required is False


def test_no_fuzzy_edit_or_automatic_vietnamese_correction_is_attempted():
    spec = _spec(
        "LOAN_QUALITY",
        ordered_children=(RowRoleSpecV1("STANDARD", ("Nợ đủ tiêu chuẩn",)),),
    )
    index = compile_vietnamese_family_alias_index_v1((spec,))

    proposal = propose_vietnamese_semantic_surface_v1("Nợ đũ tiêu chuẩnn", index)

    assert proposal.raw_transcript_nfc == "Nợ đũ tiêu chuẩnn"
    assert proposal.normalized_vietnamese_surface == "nợ đũ tiêu chuẩnn"
    assert proposal.status == "NO_ALIAS_CANDIDATE"
    assert proposal.candidates == ()
    assert proposal.automatic_correction_applied is False
    assert proposal.fuzzy_edit_matching_used is False


def test_non_string_artifact_or_metadata_envelope_is_forbidden():
    spec = _spec(
        "LOAN_QUALITY",
        ordered_children=(RowRoleSpecV1("STANDARD", ("Nợ đủ tiêu chuẩn",)),),
    )
    index = compile_vietnamese_family_alias_index_v1((spec,))

    with pytest.raises(VietnameseSemanticSurfaceContractError, match="exact string"):
        propose_vietnamese_semantic_surface_v1(
            {"raw_transcript": "Nợ đủ tiêu chuẩn", "metadata": {"bank": "forbidden"}},
            index,
        )


def test_compiler_rejects_duplicate_family_identities_and_foreign_specs():
    spec = _spec(
        "LOAN_QUALITY",
        ordered_children=(RowRoleSpecV1("STANDARD", ("Nợ đủ tiêu chuẩn",)),),
    )

    with pytest.raises(VietnameseSemanticSurfaceContractError, match="unique"):
        compile_vietnamese_family_alias_index_v1((spec, spec))
    with pytest.raises(VietnameseSemanticSurfaceContractError, match="FamilySpecV1"):
        compile_vietnamese_family_alias_index_v1((spec, object()))


def test_compiled_index_cannot_be_constructed_or_mutated_by_a_consumer():
    spec = _spec(
        "LOAN_QUALITY",
        ordered_children=(RowRoleSpecV1("STANDARD", ("Nợ đủ tiêu chuẩn",)),),
    )
    index = compile_vietnamese_family_alias_index_v1((spec,))

    with pytest.raises(VietnameseSemanticSurfaceContractError, match="compiler"):
        type(index)()
    with pytest.raises(TypeError):
        index.family_spec_sha256_by_id["FORGED"] = "0" * 64
    with pytest.raises(TypeError):
        index.accentless_comparison_key_index["forged"] = ()
    with pytest.raises(TypeError):
        index.child_row_presentation_key_index["forged"] = ()


def test_leading_debt_prefix_fallback_cannot_match_owner_or_branch_aliases():
    spec = _spec(
        "ROLE_SCOPE_CONTROL",
        branch_aliases=("ngắn hạn",),
        ordered_children=(RowRoleSpecV1("LONG_TERM", ("dài hạn",)),),
    )
    index = compile_vietnamese_family_alias_index_v1((spec,))

    proposal = propose_vietnamese_semantic_surface_v1("Nơ ngắn hạn", index)

    assert proposal.status == "NO_ALIAS_CANDIDATE"
    assert proposal.candidates == ()
    assert proposal.semantic_identity_authority is False
    assert proposal.structure_acceptance_authority is False
