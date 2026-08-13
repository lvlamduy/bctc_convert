from __future__ import annotations

from copy import deepcopy

import pytest

from bctc_ai.source_structure import semantic_statement_context_v1 as context_module
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.source_structure.semantic_statement_context_v1 import (
    SemanticStatementContextV1Error,
    _build,
    _validate,
)


def _sample(index: int, text: str) -> dict:
    return {
        "sample_id": f"page-0001-line-{index:04d}",
        "source_line_index": index,
        "source_bbox_raw_pixels": [10, 20 + index * 20, 200, 35 + index * 20],
        "crop_ref": {"path": f"crop-{index}.png", "sha256": "a" * 64, "size_bytes": 1},
        "raw_prediction": text,
        "source_atom": {
            "source_atom_id": f"ssv1:atom:{index:064x}",
            "canonical_bbox_mpt": [100, 200, 2000, 350],
        },
    }


def _binding(*texts: str) -> dict:
    return {
        "source_local_page_id": f"ssv2:page:{'b' * 64}",
        "source_projection_sha256": "c" * 64,
        "samples": [_sample(index, text) for index, text in enumerate(texts)],
    }


@pytest.mark.parametrize(
    ("heading", "statement", "scope", "continuation"),
    (
        ("THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT", "TM", "CONSOLIDATED", False),
        (
            "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT (TIẾP THEO)",
            "TM",
            "CONSOLIDATED",
            True,
        ),
        ("THUYẾT MINH BÁO CÁO TÀI CHÍNH RIÊNG", "TM", "SEPARATE", False),
        (
            "THUYẾT MINH BÁO CÁO TÀI CHÍNH RIÊNG (TIẾP THEO)",
            "TM",
            "SEPARATE",
            True,
        ),
    ),
)
def test_exact_utf8_heading_resolves_page_local_context(
    heading, statement, scope, continuation
) -> None:
    result = _validate(_build(_binding("noise", heading)))

    assert result["status"] == "RESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT"
    assert (result["statement_type"], result["report_scope"], result["continuation"]) == (
        statement,
        scope,
        continuation,
    )
    assert result["heading_evidence"]["raw_transformer_text_utf8"] == heading
    assert result["readiness"]["schema_mapping_ready"] is False
    assert result["readiness"]["export_eligible"] is False


@pytest.mark.parametrize(
    "heading",
    (
        "THUYET MINH BAO CAO TAI CHINH HOP NHAT (TIEP THEO)",
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT (TIẾP THE0)",
        "BÁO CÁO TÀI CHÍNH HỢP NHẤT",
        "TM BCTC HỢP NHẤT",
    ),
)
def test_accentless_typo_partial_or_abbreviated_heading_never_accepts(heading) -> None:
    result = _validate(_build(_binding(heading)))

    assert result["status"] == "UNRESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT"
    assert result["statement_type"] is None
    assert result["report_scope"] is None
    assert result["heading_evidence"] is None


def test_multiple_supported_headings_fail_closed_even_when_semantics_match() -> None:
    result = _validate(
        _build(
            _binding(
                "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT",
                "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT",
            )
        )
    )

    assert result["status"] == "UNRESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT"
    assert result["unresolved_reasons"] == ["MULTIPLE_OR_CONFLICTING_VISIBLE_PAGE_HEADINGS"]


def test_self_rehashed_semantic_tamper_still_fails_exact_replay_contract(monkeypatch) -> None:
    binding = _binding("THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT")
    result = _build(binding)
    tampered = deepcopy(result)
    tampered["report_scope"] = "SEPARATE"

    identity_payload = deepcopy(tampered)
    identity_payload.pop("context_id")
    tampered["context_id"] = f"sscxtv1:context:{canonical_json_sha256_v1(identity_payload)}"

    assert _validate(tampered) == tampered
    monkeypatch.setattr(
        context_module,
        "validate_vietocr_semantic_page_binding_v2",
        lambda *_args: binding,
    )
    with pytest.raises(SemanticStatementContextV1Error, match="does not replay"):
        context_module.validate_semantic_statement_context_replay_v1(
            tampered, object(), object(), object()
        )


def test_exported_safety_view_cannot_weaken_minted_policy(monkeypatch) -> None:
    monkeypatch.setattr(context_module, "SAFETY", {"schema_mapping_authority": True})
    result = _build(_binding("THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT"))

    assert result["safety"]["schema_mapping_authority"] is False
    assert result["safety"]["export_authority"] is False
