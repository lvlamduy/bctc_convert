"""Immutable corpus-wide index for selected Gemini document manifests."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "GEMINI_CURRENT_CORPUS_MANIFEST_INDEX_V1"
_PAGE_STATUSES = (
    "FINANCIAL_NOTE_CONTENT",
    "MIXED_FINANCIAL_CONTENT",
    "NO_RELEVANT_FINANCIAL_CONTENT",
    "PRIMARY_FINANCIAL_STATEMENT",
)


class GeminiCurrentCorpusManifestIndexV1Error(ValueError):
    """A corpus manifest index is incomplete, inconsistent, or not canonical."""


def _error(message: str) -> GeminiCurrentCorpusManifestIndexV1Error:
    return GeminiCurrentCorpusManifestIndexV1Error(message)


def _digest(value: Any, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise _error(f"corpus manifest index {field} is invalid")
    return value


def _identifier(value: Any, prefix: str, field: str) -> str:
    if type(value) is not str or not value.startswith(prefix) or len(value) != len(prefix) + 64:
        raise _error(f"corpus manifest index {field} is invalid")
    _digest(value[len(prefix) :], field)
    return value


def _safe_path(value: Any, field: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.startswith("/")
        or "\\" in value
        or ".." in value.split("/")
    ):
        raise _error(f"corpus manifest index {field} is invalid")
    return value


def _content_ref(value: Any, field: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"path", "sha256", "size_bytes"}:
        raise _error(f"corpus manifest index {field} fields drifted")
    checked = canonical_clone_v1(value)
    _safe_path(checked["path"], f"{field} path")
    _digest(checked["sha256"], f"{field} SHA-256")
    if type(checked["size_bytes"]) is not int or checked["size_bytes"] <= 0:
        raise _error(f"corpus manifest index {field} size is invalid")
    return checked


def _status_counts(value: Any, *, page_count: int) -> dict[str, int]:
    if (
        type(value) is not dict
        or set(value) != set(_PAGE_STATUSES)
        or any(type(value[status]) is not int or value[status] < 0 for status in _PAGE_STATUSES)
        or sum(value.values()) != page_count
    ):
        raise _error("corpus manifest index page status counts are invalid")
    return {status: value[status] for status in _PAGE_STATUSES}


def _provider_counts(value: Any, *, page_count: int) -> list[dict[str, Any]]:
    if type(value) is not list or not value:
        raise _error("corpus manifest index provider frontier is invalid")
    checked = []
    keys = []
    for item in value:
        if type(item) is not dict or set(item) != {
            "count",
            "gateway",
            "selected_provider",
            "selected_service_tier",
        }:
            raise _error("corpus manifest index provider record fields drifted")
        if (
            any(
                type(item[field]) is not str or not item[field]
                for field in ("gateway", "selected_provider", "selected_service_tier")
            )
            or type(item["count"]) is not int
            or item["count"] <= 0
        ):
            raise _error("corpus manifest index provider record is invalid")
        key = (item["gateway"], item["selected_provider"], item["selected_service_tier"])
        keys.append(key)
        checked.append(canonical_clone_v1(item))
    if keys != sorted(set(keys)) or sum(item["count"] for item in checked) != page_count:
        raise _error("corpus manifest index provider frontier is not exhaustive")
    return checked


def _document(value: Any, *, expected_ordinal: int) -> dict[str, Any]:
    required = {
        "document_manifest_id",
        "document_manifest_ref",
        "document_plan_id",
        "page_count",
        "page_json_frontier_sha256",
        "page_status_counts",
        "provider_counts",
        "relative_path",
        "selection_id",
        "selection_ref",
        "source_ordinal",
        "source_sha256",
        "source_size_bytes",
    }
    if type(value) is not dict or set(value) != required:
        raise _error("corpus manifest index document fields drifted")
    checked = canonical_clone_v1(value)
    if checked["source_ordinal"] != expected_ordinal:
        raise _error("corpus manifest index document order is invalid")
    _identifier(checked["document_plan_id"], "gjfpdocv1:", "document plan identity")
    _identifier(checked["document_manifest_id"], "gfdmv1:manifest:", "document identity")
    _identifier(checked["selection_id"], "gjfcdmsv1:selection:", "selection identity")
    _safe_path(checked["relative_path"], "document source path")
    _digest(checked["source_sha256"], "document source SHA-256")
    _digest(checked["page_json_frontier_sha256"], "page JSON frontier SHA-256")
    if (
        type(checked["source_size_bytes"]) is not int
        or checked["source_size_bytes"] <= 0
        or type(checked["page_count"]) is not int
        or checked["page_count"] <= 0
    ):
        raise _error("corpus manifest index document size or page count is invalid")
    checked["document_manifest_ref"] = _content_ref(
        checked["document_manifest_ref"], "document manifest reference"
    )
    checked["selection_ref"] = _content_ref(checked["selection_ref"], "selection reference")
    checked["page_status_counts"] = _status_counts(
        checked["page_status_counts"], page_count=checked["page_count"]
    )
    checked["provider_counts"] = _provider_counts(
        checked["provider_counts"], page_count=checked["page_count"]
    )
    return checked


def _usage_summary(value: Any) -> dict[str, Any]:
    required = {
        "attempts",
        "cached_input_tokens",
        "input_tokens",
        "output_tokens",
        "run_count",
        "thought_tokens",
        "total_cost_usd",
    }
    if type(value) is not dict or set(value) != required:
        raise _error("corpus manifest index usage summary fields drifted")
    checked = canonical_clone_v1(value)
    for field in (
        "cached_input_tokens",
        "input_tokens",
        "output_tokens",
        "run_count",
        "thought_tokens",
    ):
        if type(checked[field]) is not int or checked[field] < 0:
            raise _error(f"corpus manifest index usage {field} is invalid")
    try:
        cost = Decimal(checked["total_cost_usd"])
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise _error("corpus manifest index usage cost is invalid") from exc
    if cost < 0 or checked["total_cost_usd"] != format(cost, ".12f"):
        raise _error("corpus manifest index usage cost is not canonical")
    attempts = checked["attempts"]
    if type(attempts) is not list:
        raise _error("corpus manifest index attempt summary is invalid")
    keys = []
    for item in attempts:
        if type(item) is not dict or set(item) != {
            "count",
            "credential_slot",
            "outcome",
            "provider",
        }:
            raise _error("corpus manifest index attempt record fields drifted")
        if (
            any(
                type(item[field]) is not str or not item[field]
                for field in item
                if field != "count"
            )
            or type(item["count"]) is not int
            or item["count"] <= 0
        ):
            raise _error("corpus manifest index attempt record is invalid")
        keys.append((item["provider"], item["credential_slot"], item["outcome"]))
    if keys != sorted(set(keys)):
        raise _error("corpus manifest index attempt summary is not canonical")
    return checked


def _summary(documents: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    statuses: Counter[str] = Counter()
    providers: Counter[tuple[str, str, str]] = Counter()
    for document in documents:
        statuses.update(document["page_status_counts"])
        for item in document["provider_counts"]:
            providers[
                (item["gateway"], item["selected_provider"], item["selected_service_tier"])
            ] += item["count"]
    return {
        "document_count": len(documents),
        "page_count": sum(document["page_count"] for document in documents),
        "page_status_counts": {status: statuses[status] for status in _PAGE_STATUSES},
        "provider_counts": [
            {
                "count": providers[key],
                "gateway": key[0],
                "selected_provider": key[1],
                "selected_service_tier": key[2],
            }
            for key in sorted(providers)
        ],
    }


def build_current_corpus_manifest_index_v1(
    *,
    corpus_plan_id: str,
    corpus_run_id: str,
    corpus_plan_ref: Mapping[str, Any],
    database_ref: Mapping[str, Any],
    ledger_ref: Mapping[str, Any],
    documents: Sequence[Mapping[str, Any]],
    store_usage_summary: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one content-addressed index over the complete selected corpus."""

    material = {
        "corpus_plan_id": corpus_plan_id,
        "corpus_plan_ref": canonical_clone_v1(dict(corpus_plan_ref)),
        "corpus_run_id": corpus_run_id,
        "database_ref": canonical_clone_v1(dict(database_ref)),
        "document_selection_frontier_sha256": canonical_json_sha256_v1(
            [
                {
                    "document_manifest_id": document["document_manifest_id"],
                    "document_plan_id": document["document_plan_id"],
                    "selection_id": document["selection_id"],
                }
                for document in documents
            ]
        ),
        "documents": [canonical_clone_v1(dict(document)) for document in documents],
        "format_version": FORMAT_VERSION,
        "ledger_ref": canonical_clone_v1(dict(ledger_ref)),
        "store_usage_summary": canonical_clone_v1(dict(store_usage_summary)),
        "summary": _summary(documents),
    }
    return validate_current_corpus_manifest_index_v1(
        {
            **material,
            "corpus_manifest_index_id": "gjfccmiv1:index:" + canonical_json_sha256_v1(material),
        }
    )


def validate_current_corpus_manifest_index_v1(value: Any) -> dict[str, Any]:
    """Validate and canonicalize one complete corpus manifest index."""

    if type(value) is not dict:
        raise _error("corpus manifest index must be one object")
    checked = canonical_clone_v1(value)
    required = {
        "corpus_manifest_index_id",
        "corpus_plan_id",
        "corpus_plan_ref",
        "corpus_run_id",
        "database_ref",
        "document_selection_frontier_sha256",
        "documents",
        "format_version",
        "ledger_ref",
        "store_usage_summary",
        "summary",
    }
    if set(checked) != required or checked["format_version"] != FORMAT_VERSION:
        raise _error("corpus manifest index fields drifted")
    _identifier(
        checked["corpus_manifest_index_id"],
        "gjfccmiv1:index:",
        "corpus index identity",
    )
    _identifier(checked["corpus_plan_id"], "gjfpcorpusv1:", "corpus plan identity")
    _identifier(checked["corpus_run_id"], "gjfpcrunv1:", "corpus run identity")
    checked["corpus_plan_ref"] = _content_ref(checked["corpus_plan_ref"], "plan reference")
    checked["database_ref"] = _content_ref(checked["database_ref"], "database reference")
    checked["ledger_ref"] = _content_ref(checked["ledger_ref"], "ledger reference")
    _digest(
        checked["document_selection_frontier_sha256"],
        "document selection frontier SHA-256",
    )
    if type(checked["documents"]) is not list or not checked["documents"]:
        raise _error("corpus manifest index document frontier is empty")
    checked["documents"] = [
        _document(document, expected_ordinal=ordinal)
        for ordinal, document in enumerate(checked["documents"], start=1)
    ]
    paths = [document["relative_path"] for document in checked["documents"]]
    plan_ids = [document["document_plan_id"] for document in checked["documents"]]
    selection_ids = [document["selection_id"] for document in checked["documents"]]
    if (
        paths != sorted(set(paths))
        or len(set(plan_ids)) != len(plan_ids)
        or len(set(selection_ids)) != len(selection_ids)
    ):
        raise _error("corpus manifest index document frontier is duplicate or unordered")
    expected_frontier = canonical_json_sha256_v1(
        [
            {
                "document_manifest_id": document["document_manifest_id"],
                "document_plan_id": document["document_plan_id"],
                "selection_id": document["selection_id"],
            }
            for document in checked["documents"]
        ]
    )
    if checked["document_selection_frontier_sha256"] != expected_frontier:
        raise _error("corpus manifest index selection frontier does not replay")
    checked["store_usage_summary"] = _usage_summary(checked["store_usage_summary"])
    if checked["summary"] != _summary(checked["documents"]):
        raise _error("corpus manifest index summary does not replay")
    material = {key: checked[key] for key in checked if key != "corpus_manifest_index_id"}
    expected_id = "gjfccmiv1:index:" + canonical_json_sha256_v1(material)
    if checked["corpus_manifest_index_id"] != expected_id:
        raise _error("corpus manifest index identity does not replay")
    return checked
