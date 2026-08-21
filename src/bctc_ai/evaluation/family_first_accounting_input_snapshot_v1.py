"""Efficient authenticated snapshots for generic family-first accounting sweeps.

The formal OCR runners deliberately pin their executable trust closures.  New
family-engine read patterns must therefore live outside those sealed runner and
index modules.  This module composes their existing private live verifiers into
source-ordered semantic- and numeric-document snapshots: the complete roots
are authenticated immediately before and after each bounded pass, selected
semantic files are re-read byte-for-byte, and every numeric proposal remains
bound to its source sample and immutable crop reference.
"""

from __future__ import annotations

from typing import Any

from bctc_ai.evaluation import family_first_ppocrv6_numeric_index_v3 as numeric_v3
from bctc_ai.evaluation import family_first_semantic_index_v1 as semantic_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    same_typed_json_v1,
)

__all__ = [
    "FamilyFirstAccountingInputSnapshotV1Error",
    "read_authenticated_family_first_numeric_documents_snapshot_v1",
    "read_authenticated_family_first_semantic_documents_snapshot_v1",
    "validate_authenticated_family_first_semantic_documents_snapshot_v1",
]


class FamilyFirstAccountingInputSnapshotV1Error(RuntimeError):
    """The requested live numeric corpus snapshot could not be established."""


def _error(message: str) -> FamilyFirstAccountingInputSnapshotV1Error:
    return FamilyFirstAccountingInputSnapshotV1Error(message)


def _document_ordinals(value: Any, *, document_count: int) -> tuple[int, ...]:
    if (
        type(value) is not tuple
        or not value
        or any(type(ordinal) is not int for ordinal in value)
        or tuple(sorted(set(value))) != value
        or value[0] <= 0
        or value[-1] > document_count
    ):
        raise _error(
            "document snapshot must be one non-empty source-ordered unique "
            "tuple inside the corpus denominator"
        )
    return value


def _semantic_snapshot_inputs(
    capability: semantic_v1.AuthenticatedFamilyFirstSemanticIndexV1,
    document_ordinals: Any,
) -> tuple[Any, dict[str, Any], tuple[int, ...], list[dict[str, Any]]]:
    try:
        state, manifest = semantic_v1._live_index(capability)
        plan_documents = semantic_v1._canonical_object(
            state.plan_documents_payload, "semantic index plan document snapshot"
        )["documents"]
    except semantic_v1.FamilyFirstSemanticIndexV1Error as exc:
        raise _error("semantic live index authentication failed") from exc
    ordinals = _document_ordinals(
        document_ordinals, document_count=manifest["metrics"]["document_count"]
    )
    if (
        type(plan_documents) is not list
        or len(plan_documents) != manifest["metrics"]["document_count"]
    ):
        raise _error("semantic plan document denominator drifted")
    return state, manifest, ordinals, plan_documents


def read_authenticated_family_first_semantic_documents_snapshot_v1(
    capability: semantic_v1.AuthenticatedFamilyFirstSemanticIndexV1,
    *,
    document_ordinals: tuple[int, ...],
) -> tuple[dict[str, Any], ...]:
    """Read selected semantic documents from one stable live-index snapshot."""

    state, manifest, ordinals, plan_documents = _semantic_snapshot_inputs(
        capability, document_ordinals
    )
    documents = []
    payloads = []
    for ordinal in ordinals:
        reference = manifest["documents"][ordinal - 1]
        try:
            payload = semantic_v1._root_bytes(
                state.root, reference["content_ref"]["path"], "semantic index document"
            )
            semantic_v1._matches(payload, reference["content_ref"], "semantic index document")
            document = semantic_v1._validate_document(
                semantic_v1._canonical_object(payload, "semantic index document"),
                plan_documents[ordinal - 1],
            )
        except semantic_v1.FamilyFirstSemanticIndexV1Error as exc:
            raise _error("semantic document snapshot drifted") from exc
        if document["document_id"] != reference["document_id"]:
            raise _error("semantic document snapshot identity drifted")
        documents.append(document)
        payloads.append(payload)

    # Re-read every selected file, not only the manifest, so a document cannot
    # change between its consumption and the end of this bounded snapshot.
    for ordinal, expected_payload in zip(ordinals, payloads, strict=True):
        reference = manifest["documents"][ordinal - 1]
        try:
            final_payload = semantic_v1._root_bytes(
                state.root, reference["content_ref"]["path"], "semantic index document"
            )
        except semantic_v1.FamilyFirstSemanticIndexV1Error as exc:
            raise _error("semantic document changed during snapshot read") from exc
        if final_payload != expected_payload:
            raise _error("semantic document changed during snapshot read")
    try:
        final_state, final_manifest = semantic_v1._live_index(capability)
    except semantic_v1.FamilyFirstSemanticIndexV1Error as exc:
        raise _error("semantic live index changed during snapshot read") from exc
    if final_state is not state or not same_typed_json_v1(final_manifest, manifest):
        raise _error("semantic live index changed during snapshot read")
    return tuple(documents)


def validate_authenticated_family_first_semantic_documents_snapshot_v1(
    capability: semantic_v1.AuthenticatedFamilyFirstSemanticIndexV1,
    documents: tuple[dict[str, Any], ...],
) -> None:
    """Re-read exact selected bytes immediately before a sweep result is minted."""

    if (
        type(documents) is not tuple
        or not documents
        or any(type(document) is not dict for document in documents)
    ):
        raise _error("semantic document validation requires one non-empty exact tuple")
    ordinals = tuple(document.get("document_ordinal") for document in documents)
    state, manifest, parsed_ordinals, plan_documents = _semantic_snapshot_inputs(
        capability, ordinals
    )
    if parsed_ordinals != ordinals:
        raise _error("semantic document validation source order drifted")
    for ordinal, document in zip(ordinals, documents, strict=True):
        reference = manifest["documents"][ordinal - 1]
        expected_payload = canonical_json_bytes_v1(document)
        try:
            live_payload = semantic_v1._root_bytes(
                state.root, reference["content_ref"]["path"], "semantic index document"
            )
            semantic_v1._matches(live_payload, reference["content_ref"], "semantic index document")
            semantic_v1._validate_document(document, plan_documents[ordinal - 1])
        except semantic_v1.FamilyFirstSemanticIndexV1Error as exc:
            raise _error("semantic document validation drifted") from exc
        if live_payload != expected_payload or document["document_id"] != reference["document_id"]:
            raise _error("semantic document changed after snapshot consumption")
    try:
        final_state, final_manifest = semantic_v1._live_index(capability)
    except semantic_v1.FamilyFirstSemanticIndexV1Error as exc:
        raise _error("semantic live index changed during final validation") from exc
    if final_state is not state or not same_typed_json_v1(final_manifest, manifest):
        raise _error("semantic live index changed during final validation")


def read_authenticated_family_first_numeric_documents_snapshot_v1(
    capability: numeric_v3.AuthenticatedFamilyFirstPPocrV6NumericIndexV3,
    *,
    document_ordinals: tuple[int, ...],
) -> tuple[dict[str, Any], ...]:
    """Read selected complete numeric documents from one live corpus snapshot."""

    try:
        state, receipt, batch, plan, private = numeric_v3._live_index(capability)
    except numeric_v3.FamilyFirstPPocrV6NumericIndexV3Error as exc:
        raise _error("numeric V3 live index authentication failed") from exc
    ordinals = _document_ordinals(
        document_ordinals, document_count=receipt["metrics"]["document_count"]
    )
    requested = set(ordinals)
    lines_by_document: dict[int, list[dict[str, Any]]] = {ordinal: [] for ordinal in ordinals}
    for zero_index, source in enumerate(private["samples"]):
        document_ordinal = source["document_ordinal"]
        if document_ordinal not in requested:
            continue
        public = batch["samples"][zero_index]
        try:
            proposal = numeric_v3._proposal_at(state, zero_index + 1)
        except numeric_v3.FamilyFirstPPocrV6NumericIndexV3Error as exc:
            raise _error("numeric proposal snapshot drifted") from exc
        if (
            proposal["sample_id"] != source["sample_id"]
            or public["sample_id"] != source["sample_id"]
            or proposal["crop_sha256"] != public["crop_ref"]["sha256"]
        ):
            raise _error("numeric proposal/source/crop axis drifted")
        lines_by_document[document_ordinal].append(
            {
                "crop_ref": canonical_clone_v1(public["crop_ref"]),
                "line_ordinal": source["line_ordinal"],
                "physical_page": source["physical_page"],
                "raw_prediction": proposal["raw_prediction"],
                "reader_score": proposal["reader_score"],
                "sample_id": source["sample_id"],
                "source_bbox_raw_pixels": canonical_clone_v1(source["source_bbox_raw_pixels"]),
            }
        )

    documents = []
    for ordinal in ordinals:
        if not lines_by_document[ordinal]:
            raise _error("selected numeric source document retained no samples")
        planned = plan["documents"][ordinal - 1]
        documents.append(
            {
                "document_ordinal": ordinal,
                "lines": lines_by_document[ordinal],
                "private_provenance": canonical_clone_v1(planned["private_provenance"]),
                "source_pdf_ref": canonical_clone_v1(planned["source_pdf_ref"]),
            }
        )

    try:
        final_state, final_receipt, final_batch, final_plan, final_private = numeric_v3._live_index(
            capability
        )
    except numeric_v3.FamilyFirstPPocrV6NumericIndexV3Error as exc:
        raise _error("numeric V3 live index changed during snapshot read") from exc
    if (
        final_state is not state
        or not same_typed_json_v1(final_receipt, receipt)
        or not same_typed_json_v1(final_batch, batch)
        or not same_typed_json_v1(final_plan, plan)
        or not same_typed_json_v1(final_private, private)
    ):
        raise _error("numeric V3 live corpus changed during document snapshot read")
    return tuple(documents)
