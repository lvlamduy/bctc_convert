from __future__ import annotations

import copy

import pytest

from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (
    GeminiCurrentCorpusManifestIndexV1Error,
    build_current_corpus_manifest_index_v1,
    validate_current_corpus_manifest_index_v1,
)


def _ref(name: str, digit: str) -> dict[str, object]:
    return {"path": name, "sha256": digit * 64, "size_bytes": 100}


def _document(ordinal: int, *, digit: str, path: str) -> dict[str, object]:
    return {
        "document_manifest_id": "gfdmv1:manifest:" + digit * 64,
        "document_manifest_ref": _ref(f"documents/{digit}/manifest.json", digit),
        "document_plan_id": "gjfpdocv1:" + digit * 64,
        "page_count": 2,
        "page_json_frontier_sha256": digit * 64,
        "page_status_counts": {
            "FINANCIAL_NOTE_CONTENT": 1,
            "MIXED_FINANCIAL_CONTENT": 0,
            "NO_RELEVANT_FINANCIAL_CONTENT": 1,
            "PRIMARY_FINANCIAL_STATEMENT": 0,
        },
        "provider_counts": [
            {
                "count": 2,
                "gateway": "OPENROUTER",
                "selected_provider": "Google",
                "selected_service_tier": "flex",
            }
        ],
        "relative_path": path,
        "selection_id": "gjfcdmsv1:selection:" + digit * 64,
        "selection_ref": _ref(f"documents/{digit}/selection.json", digit),
        "source_ordinal": ordinal,
        "source_sha256": digit * 64,
        "source_size_bytes": 200,
    }


def _usage() -> dict[str, object]:
    return {
        "attempts": [
            {
                "count": 4,
                "credential_slot": "OPENROUTER_SLOT_1",
                "outcome": "COMPLETED",
                "provider": "OPENROUTER",
            }
        ],
        "cached_input_tokens": 0,
        "input_tokens": 100,
        "output_tokens": 50,
        "run_count": 4,
        "thought_tokens": 2,
        "total_cost_usd": "0.010000000000",
    }


def _index():
    return build_current_corpus_manifest_index_v1(
        corpus_plan_id="gjfpcorpusv1:" + "a" * 64,
        corpus_run_id="gjfpcrunv1:" + "b" * 64,
        corpus_plan_ref=_ref("freeze/corpus-plan.json", "a"),
        database_ref=_ref("freeze/store.sqlite3", "b"),
        ledger_ref=_ref("freeze/ledger.sqlite3", "c"),
        documents=[
            _document(1, digit="1", path="bank/a.pdf"),
            _document(2, digit="2", path="bank/b.pdf"),
        ],
        store_usage_summary=_usage(),
    )


def test_current_corpus_index_binds_ordered_complete_documents_and_usage() -> None:
    index = _index()
    assert validate_current_corpus_manifest_index_v1(index) == index
    assert index["summary"] == {
        "document_count": 2,
        "page_count": 4,
        "page_status_counts": {
            "FINANCIAL_NOTE_CONTENT": 2,
            "MIXED_FINANCIAL_CONTENT": 0,
            "NO_RELEVANT_FINANCIAL_CONTENT": 2,
            "PRIMARY_FINANCIAL_STATEMENT": 0,
        },
        "provider_counts": [
            {
                "count": 4,
                "gateway": "OPENROUTER",
                "selected_provider": "Google",
                "selected_service_tier": "flex",
            }
        ],
    }


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value["documents"].reverse(),
            "document order",
        ),
        (
            lambda value: value["documents"][0]["page_status_counts"].update(
                {"FINANCIAL_NOTE_CONTENT": 0}
            ),
            "page status counts",
        ),
        (
            lambda value: value["documents"][0]["provider_counts"][0].update({"count": 1}),
            "provider frontier",
        ),
        (
            lambda value: value["store_usage_summary"].update({"total_cost_usd": "0.01"}),
            "cost is not canonical",
        ),
        (
            lambda value: value["summary"].update({"page_count": 3}),
            "summary does not replay",
        ),
        (
            lambda value: value.update({"document_selection_frontier_sha256": "f" * 64}),
            "selection frontier does not replay",
        ),
    ],
)
def test_current_corpus_index_rejects_incomplete_or_coherently_unsealed_tamper(
    mutate, message: str
) -> None:
    value = copy.deepcopy(_index())
    mutate(value)
    with pytest.raises(GeminiCurrentCorpusManifestIndexV1Error, match=message):
        validate_current_corpus_manifest_index_v1(value)
