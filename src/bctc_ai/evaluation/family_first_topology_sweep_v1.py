"""Generic family-first topology sweep over every authenticated filing.

The sweep is deliberately family-agnostic.  A caller supplies one declarative
``ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V1``; the same engine receives a provenance-
blind complete-document page/line axis for each filing.  Filing provenance is
joined only after each topology scan has returned and is never a routing or
matching input.
"""

from __future__ import annotations

from typing import Any

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation.family_first_semantic_index_v1 import (
    AuthenticatedFamilyFirstSemanticIndexV1,
    project_authenticated_family_first_semantic_index_v1,
    read_authenticated_family_first_semantic_document_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "FamilyFirstTopologySweepV1Error",
    "build_authenticated_family_first_topology_sweep_v1",
    "validate_authenticated_family_first_topology_sweep_replay_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_ACCOUNTING_TOPOLOGY_SWEEP_V1"
CLAIM_BOUNDARY = (
    "AUTHENTICATED_ALL_FILING_BANK_BLIND_COMPLETE_DOCUMENT_DECLARATIVE_FAMILY_"
    "TOPOLOGY_ENUMERATION_ONLY_NO_PERIOD_UNIT_NUMERIC_ACCOUNTING_SCHEMA_MAPPING_"
    "CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "all_authenticated_documents_scanned": True,
    "bank_file_page_period_scope_used_for_matching_or_routing": False,
    "family_layout_logic_is_declarative": True,
    "mapping_authority": False,
    "not_observed_authority": False,
    "numeric_authority": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "schema_authority": False,
    "topology_proposal_only": True,
}
_FIELDS = {
    "authority",
    "claim_boundary",
    "family_id",
    "family_spec",
    "format_version",
    "input_index_id",
    "metrics",
    "state",
    "sweep_id",
    "trials",
}
_TRIAL_FIELDS = {
    "document_ordinal",
    "private_provenance",
    "source_pdf_ref",
    "topology_scan",
}


class FamilyFirstTopologySweepV1Error(ValueError):
    """The semantic index, family specification, or all-filing sweep drifted."""


def _error(message: str) -> FamilyFirstTopologySweepV1Error:
    return FamilyFirstTopologySweepV1Error(message)


def _blind_pages(document: dict[str, Any]) -> list[dict[str, Any]]:
    pages = []
    for expected_page, page in enumerate(document["pages"], 1):
        if page["physical_page"] != expected_page:
            raise _error("semantic document page sequence drifted before topology scan")
        pages.append(
            {
                "lines": [
                    {
                        "bbox": canonical_clone_v1(line["source_bbox_raw_pixels"]),
                        "source_line_index": line["line_ordinal"],
                        "source_text": None,
                        "vietocr_text": line["vietocr_text"],
                    }
                    for line in page["lines"]
                ],
                "page_sequence": expected_page,
            }
        )
    return pages


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    accepted = sum(
        trial["topology_scan"]["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL" for trial in trials
    )
    multiple = sum(
        trial["topology_scan"]["status"] == "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS"
        for trial in trials
    )
    no_complete = sum(
        trial["topology_scan"]["status"] == "UNRESOLVED_NO_COMPLETE_REGION" for trial in trials
    )
    return {
        "accepted_unique_topology_proposal_count": accepted,
        "document_count": len(trials),
        "mapping_verified_count": 0,
        "multiple_or_nonunique_document_count": multiple,
        "no_complete_region_document_count": no_complete,
        "not_observed_count": 0,
        "unresolved_document_count": len(trials),
    }


def _validate(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "ALL_FILING_FAMILY_TOPOLOGY_SWEEP_COMPLETE_PROPOSAL_ONLY"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["family_id"]) is not str
        or not value["family_id"]
        or type(value["input_index_id"]) is not str
        or not value["input_index_id"].startswith("ffsiv1:index:")
        or type(value["family_spec"]) is not dict
        or set(value["family_spec"]) != {"sha256", "value"}
        or value["family_spec"]["sha256"] != canonical_json_sha256_v1(value["family_spec"]["value"])
        or type(value["trials"]) is not list
    ):
        raise _error("family-first topology sweep identity/shape drifted")
    for ordinal, trial in enumerate(value["trials"], 1):
        if (
            type(trial) is not dict
            or set(trial) != _TRIAL_FIELDS
            or trial["document_ordinal"] != ordinal
            or type(trial["document_ordinal"]) is not int
            or type(trial["private_provenance"]) is not dict
            or type(trial["source_pdf_ref"]) is not dict
            or type(trial["topology_scan"]) is not dict
            or trial["topology_scan"].get("family_id") != value["family_id"]
        ):
            raise _error("family-first topology sweep trial axis drifted")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("family-first topology sweep metrics drifted")
    material = canonical_clone_v1(value)
    sweep_id = material.pop("sweep_id")
    if sweep_id != "fftsv1:sweep:" + canonical_json_sha256_v1(material):
        raise _error("family-first topology sweep hash identity drifted")
    return canonical_clone_v1(value)


def build_authenticated_family_first_topology_sweep_v1(
    semantic_index_capability: AuthenticatedFamilyFirstSemanticIndexV1,
    family_spec: Any,
) -> dict[str, Any]:
    """Run one declarative family topology over every authenticated filing."""

    try:
        compiled_spec = topology_v1._spec(family_spec)
        projection = project_authenticated_family_first_semantic_index_v1(semantic_index_capability)
    except (ValueError, RuntimeError) as exc:
        raise _error("family-first topology sweep inputs are not authenticated") from exc
    trials = []
    document_count = projection["metrics"]["document_count"]
    for document_ordinal in range(1, document_count + 1):
        document = read_authenticated_family_first_semantic_document_v1(
            semantic_index_capability, document_ordinal=document_ordinal
        )
        scan = topology_v1.build_accounting_family_topology_scan_v1(
            _blind_pages(document), family_spec
        )
        trials.append(
            {
                "document_ordinal": document_ordinal,
                "private_provenance": canonical_clone_v1(document["private_provenance"]),
                "source_pdf_ref": canonical_clone_v1(document["source_pdf_ref"]),
                "topology_scan": scan,
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "family_id": compiled_spec["family_id"],
        "family_spec": {
            "sha256": canonical_json_sha256_v1(family_spec),
            "value": canonical_clone_v1(family_spec),
        },
        "format_version": FORMAT_VERSION,
        "input_index_id": projection["index_id"],
        "metrics": _metrics(trials),
        "state": "ALL_FILING_FAMILY_TOPOLOGY_SWEEP_COMPLETE_PROPOSAL_ONLY",
        "trials": trials,
    }
    return _validate({**material, "sweep_id": "fftsv1:sweep:" + canonical_json_sha256_v1(material)})


def validate_authenticated_family_first_topology_sweep_replay_v1(
    value: Any,
    semantic_index_capability: AuthenticatedFamilyFirstSemanticIndexV1,
    family_spec: Any,
) -> dict[str, Any]:
    """Exact-rebuild the persisted all-filing topology proposal."""

    persisted = _validate(value)
    expected = build_authenticated_family_first_topology_sweep_v1(
        semantic_index_capability, family_spec
    )
    if not same_typed_json_v1(persisted, expected):
        raise _error("family-first topology sweep does not replay exactly")
    return persisted
