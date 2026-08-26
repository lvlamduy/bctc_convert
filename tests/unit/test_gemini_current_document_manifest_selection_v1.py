from __future__ import annotations

import copy

import pytest

from bctc_ai.storage.gemini_current_document_manifest_selection_v1 import (
    GeminiCurrentDocumentManifestSelectionV1Error,
    build_current_document_manifest_selection_v1,
    select_current_document_manifest_selection_v1,
    validate_current_document_manifest_selection_v1,
)


def _selection(*, manifest_digit: str, priors=()):
    return build_current_document_manifest_selection_v1(
        document_plan_id="gjfpdocv1:" + "1" * 64,
        source_sha256="2" * 64,
        document_manifest_id="gfdmv1:manifest:" + manifest_digit * 64,
        document_manifest_ref={
            "path": f"current-document-manifests/{manifest_digit * 64}.json",
            "sha256": manifest_digit * 64,
            "size_bytes": 100,
        },
        page_image_frontier_sha256="3" * 64,
        page_prompt_frontier_sha256="4" * 64,
        prior_selection_ids=priors,
    )


def test_selection_chain_returns_unique_append_only_head() -> None:
    first = _selection(manifest_digit="5")
    second = _selection(manifest_digit="6", priors=[first["selection_id"]])
    assert validate_current_document_manifest_selection_v1(first) == first
    assert select_current_document_manifest_selection_v1([second, first]) == second


def test_selection_chain_rejects_tamper_fork_cycle_and_missing_prior() -> None:
    first = _selection(manifest_digit="5")
    second = _selection(manifest_digit="6", priors=[first["selection_id"]])
    tampered = copy.deepcopy(second)
    tampered["document_manifest_id"] = "gfdmv1:manifest:" + "7" * 64
    with pytest.raises(GeminiCurrentDocumentManifestSelectionV1Error, match="identity"):
        validate_current_document_manifest_selection_v1(tampered)
    fork = _selection(manifest_digit="7", priors=[first["selection_id"]])
    with pytest.raises(GeminiCurrentDocumentManifestSelectionV1Error, match="head"):
        select_current_document_manifest_selection_v1([first, second, fork])
    missing = _selection(manifest_digit="8", priors=["gjfcdmsv1:selection:" + "9" * 64])
    with pytest.raises(GeminiCurrentDocumentManifestSelectionV1Error, match="prior is absent"):
        select_current_document_manifest_selection_v1([missing])
