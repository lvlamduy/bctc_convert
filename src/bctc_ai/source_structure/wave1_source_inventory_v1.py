"""Build the compact deterministic source-first inventory for finalized Wave 1.

The builder consumes the single authenticated V3 survey stream, projects each
page into the closed V2 neutral evidence view, and runs the page-local geometry
proposal generator.  Its return value retains only identities and accounting
metrics.  It deliberately drops visible text, boxes, atom payloads, and source
object payloads; no statement, table, row, cell, axis, hierarchy, or accounting
meaning is promoted here.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from bctc_ai.corpus import wave1_role_b_sentinel as sentinel
from bctc_ai.source_structure.contracts_v1 import (
    TOPOLOGY_FEATURE_FORMAT_VERSION,
    PrimaryDisposition,
    ProposalKind,
    canonical_clone_v1,
    canonical_json_sha256_v1,
    make_topology_fingerprint_v1,
    same_typed_json_v1,
)
from bctc_ai.source_structure.contracts_v2 import make_page_proposal_set_v2
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.finalized_v3_survey_stream_v1 import (
    FINALIZED_V3_SURVEY_AUTHORITY_V1,
    FinalizedV3SurveyAuthority,
    open_finalized_v3_survey_stream_v1,
)
from bctc_ai.source_structure.page_geometry_proposals_v1 import (
    generate_page_geometry_proposals_v1,
)

__all__ = [
    "WAVE1_SOURCE_INVENTORY_CLAIM_BOUNDARY_V1",
    "WAVE1_SOURCE_INVENTORY_FORMAT_VERSION_V1",
    "Wave1SourceInventoryError",
    "build_wave1_source_inventory_v1",
    "validate_wave1_source_inventory_v1",
]


class Wave1SourceInventoryError(ValueError):
    """A compact Wave-1 source inventory failed its no-drop accounting."""


WAVE1_SOURCE_INVENTORY_FORMAT_VERSION_V1 = "BANK_CORPUS_WAVE_1_ROLE_B_SOURCE_FIRST_INVENTORY_V1"
WAVE1_SOURCE_INVENTORY_CLAIM_BOUNDARY_V1 = (
    "SOURCE_EVIDENCE_IDENTITIES_GEOMETRY_CANDIDATE_COUNTS_AND_"
    "NONSEMANTIC_TOPOLOGY_FINGERPRINTS_ONLY_NO_SEMANTIC_CLAIM"
)

_SAFETY = {
    "external_routing_metadata_used": False,
    "full_atom_payload_retained": False,
    "semantic_claims_made": False,
    "source_geometry_payload_retained": False,
    "v2_geometry_candidate_projection_bound": True,
    "visible_text_retained": False,
}
_ROUTES = ("CAUSAL_NATIVE_TEXT", "DOMINANT_RASTER_OCR")
_STATUSES = (
    "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
    "OCR_WORD_BOX_READ_COMPLETE",
    "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
    "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
)
_STATUS_ROUTE = {
    "CAUSAL_NATIVE_TEXT_READ_COMPLETE": "CAUSAL_NATIVE_TEXT",
    "OCR_WORD_BOX_READ_COMPLETE": "DOMINANT_RASTER_OCR",
    "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY": "CAUSAL_NATIVE_TEXT",
    "UNRESOLVED_OCR_WORD_BOX_GEOMETRY": "DOMINANT_RASTER_OCR",
}
_PROPOSAL_KINDS = tuple(sorted(item.value for item in ProposalKind))
_DISPOSITIONS = tuple(sorted(item.value for item in PrimaryDisposition))
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DOCUMENT_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PROJECTION_ID_RE = re.compile(r"^ssv2:page:[0-9a-f]{64}$")
_TOPOLOGY_ID_RE = re.compile(r"^sstfv1:[0-9a-f]{64}$")

_PAGE_METRIC_FIELDS = {
    "atom_count",
    "upstream_line_axis_count",
    "upstream_word_axis_count",
    "upstream_quarantined_span_axis_count",
    "primary_line_count",
    "primary_word_count",
    "excluded_empty_line_axis_count",
    "excluded_empty_word_axis_count",
    "supplemental_line_count",
    "quarantined_atom_count",
    "proposal_count",
    "proposal_kind_counts",
    "source_accounted_atom_count",
    "disposition_counts",
}
_ADDITIVE_PAGE_METRICS = (
    "atom_count",
    "upstream_line_axis_count",
    "upstream_word_axis_count",
    "upstream_quarantined_span_axis_count",
    "primary_line_count",
    "primary_word_count",
    "excluded_empty_line_axis_count",
    "excluded_empty_word_axis_count",
    "supplemental_line_count",
    "quarantined_atom_count",
    "proposal_count",
    "source_accounted_atom_count",
)
_PAGE_FIELDS = {
    "request_ordinal",
    "document_id",
    "physical_page",
    "route",
    "status",
    "terminal",
    "page_inventory_identity_sha256",
    "projection_identity",
    "projection_sha256",
    "v2_geometry_proposal_projection_sha256",
    "topology_fingerprint",
    "metrics",
}
_DOCUMENT_FIELDS = {
    "document_id",
    "page_count",
    "terminal_page_count",
    "atom_count",
    "proposal_count",
    "source_accounted_atom_count",
}
_AUTHORITY_FIELDS = {
    "aggregate_artifact_sha256",
    "aggregate_size_bytes",
    "aggregate_identity_sha256",
    "control_artifact_sha256",
    "control_size_bytes",
    "control_identity_sha256",
    "sealed_plan_sha256",
    "document_ids",
    "document_count",
    "request_count",
    "referenced_object_count",
}
_CORPUS_FIELDS = {
    "document_count",
    "page_count",
    "source_accounted_page_count",
    "complete_page_count",
    "terminal_page_count",
    "route_counts",
    "status_counts",
    *_ADDITIVE_PAGE_METRICS,
    "proposal_kind_counts",
    "disposition_counts",
    "distinct_topology_fingerprint_count",
}
_INVENTORY_FIELDS = {
    "format_version",
    "claim_boundary",
    "authority",
    "documents",
    "pages",
    "corpus_metrics",
    "source_structure_producer",
    "safety",
    "inventory_identity_sha256",
}
_PRODUCER_FIELDS = {"git", "implementation_ledger"}
_PRODUCER_GIT_FIELDS = {"commit", "dirty"}
_IMPLEMENTATION_LEDGER_FIELDS = {"records", "sha256"}
_IMPLEMENTATION_RECORD_FIELDS = {"phase", "kind", "path", "sha256", "size_bytes"}
_SOURCE_STRUCTURE_IMPLEMENTATION_PATHS = (
    Path("src/bctc_ai/source_structure/__init__.py"),
    Path("src/bctc_ai/source_structure/contracts_v1.py"),
    Path("src/bctc_ai/source_structure/contracts_v2.py"),
    Path("src/bctc_ai/source_structure/evidence_projection_v1.py"),
    Path("src/bctc_ai/source_structure/evidence_projection_v2.py"),
    Path("src/bctc_ai/source_structure/finalized_v3_survey_stream_v1.py"),
    Path("src/bctc_ai/source_structure/page_geometry_proposals_v1.py"),
    Path("src/bctc_ai/source_structure/wave1_source_inventory_v1.py"),
)


def _error(message: str) -> Wave1SourceInventoryError:
    return Wave1SourceInventoryError(message)


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise _error(f"{label} fields drifted")
    return value


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise _error(f"{label} must be a nonnegative integer")
    return value


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be a positive integer")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise _error(f"{label} must be a lowercase SHA-256")
    return value


def _closed_counts(
    value: Any,
    vocabulary: tuple[str, ...],
    label: str,
) -> dict[str, int]:
    counts = _exact_dict(value, set(vocabulary), label)
    for key in vocabulary:
        _nonnegative(counts[key], f"{label} {key}")
    return counts


def _authority_payload(authority: FinalizedV3SurveyAuthority) -> dict[str, Any]:
    return {
        "aggregate_artifact_sha256": authority.aggregate_artifact_sha256,
        "aggregate_size_bytes": authority.aggregate_size_bytes,
        "aggregate_identity_sha256": authority.aggregate_identity_sha256,
        "control_artifact_sha256": authority.control_artifact_sha256,
        "control_size_bytes": authority.control_size_bytes,
        "control_identity_sha256": authority.control_identity_sha256,
        "sealed_plan_sha256": authority.sealed_plan_sha256,
        "document_ids": list(authority.document_ids),
        "document_count": authority.document_count,
        "request_count": authority.request_count,
        "referenced_object_count": authority.referenced_object_count,
    }


def _source_structure_producer_receipt(project_root: Path) -> dict[str, Any]:
    """Bind the derivation code to one clean committed source tree."""

    project_root = project_root.resolve()
    try:
        git = sentinel._git_identity(project_root, require_clean=True)  # noqa: SLF001
        ledger = sentinel._implementation_ledger(  # noqa: SLF001
            project_root,
            git["commit"],
            _SOURCE_STRUCTURE_IMPLEMENTATION_PATHS,
        )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise _error(
            f"source-structure producer is not a clean committed authority: {error}"
        ) from (error)
    return {
        "git": canonical_clone_v1(git),
        "implementation_ledger": canonical_clone_v1(ledger),
    }


def _validate_source_structure_producer(value: Any) -> dict[str, Any]:
    producer = _exact_dict(value, _PRODUCER_FIELDS, "source-structure producer")
    git = _exact_dict(producer["git"], _PRODUCER_GIT_FIELDS, "source-structure producer Git")
    if (
        type(git["commit"]) is not str
        or re.fullmatch(r"[0-9a-f]{40}", git["commit"]) is None
        or git["dirty"] is not False
    ):
        raise _error("source-structure producer Git identity drifted")
    ledger = _exact_dict(
        producer["implementation_ledger"],
        _IMPLEMENTATION_LEDGER_FIELDS,
        "source-structure implementation ledger",
    )
    records = ledger["records"]
    expected_paths = [path.as_posix() for path in sorted(_SOURCE_STRUCTURE_IMPLEMENTATION_PATHS)]
    if type(records) is not list or len(records) != len(expected_paths):
        raise _error("source-structure implementation record denominator drifted")
    for expected_path, value_record in zip(expected_paths, records, strict=True):
        record = _exact_dict(
            value_record,
            _IMPLEMENTATION_RECORD_FIELDS,
            "source-structure implementation record",
        )
        if (
            record["phase"] != "READ"
            or record["kind"] != "IMPLEMENTATION"
            or record["path"] != expected_path
        ):
            raise _error("source-structure implementation path/role drifted")
        _sha(record["sha256"], "source-structure implementation digest")
        _positive(record["size_bytes"], "source-structure implementation size")
    ledger_sha = _sha(ledger["sha256"], "source-structure implementation ledger identity")
    if ledger_sha != canonical_json_sha256_v1(records):
        raise _error("source-structure implementation ledger identity drifted")
    return producer


def _bucket(count: int) -> str:
    if count == 0:
        return "ZERO"
    if count == 1:
        return "ONE"
    if count <= 4:
        return "TWO_TO_FOUR"
    if count <= 9:
        return "FIVE_TO_NINE"
    if count <= 19:
        return "TEN_TO_NINETEEN"
    if count <= 49:
        return "TWENTY_TO_FORTY_NINE"
    return "FIFTY_PLUS"


def _page_orientation(projection: Mapping[str, Any]) -> str:
    authority = projection["coordinate_authority"]
    if projection["route"] == "DOMINANT_RASTER_OCR":
        width, height = authority["unrotated_dimensions_mpt"]
    else:
        x0, y0, x1, y1 = authority["canonical_cropbox_bounds_mpt"]
        width, height = x1 - x0, y1 - y0
    if width == height:
        return "SQUARE"
    return "LANDSCAPE" if width > height else "PORTRAIT"


def _topology_fingerprint(
    projection: Mapping[str, Any],
    proposal_set: Mapping[str, Any],
) -> str:
    metrics = projection["neutral_page_v1"]["metrics"]
    if projection["terminal"]:
        evidence_mode = (
            "OCR_TERMINAL_WITH_LINE_SUPPLEMENT"
            if metrics["supplemental_line_count"] > 0
            else "UPSTREAM_TERMINAL_NO_TEXT"
        )
    else:
        evidence_mode = (
            "OCR_PRIMARY" if projection["route"] == "DOMINANT_RASTER_OCR" else "NATIVE_PRIMARY"
        )
    relations: list[str] = []
    for proposal in proposal_set["proposals"]:
        codes = proposal["evidence_codes"]
        if "DENSE_TABULAR_ALIGNMENT" in codes:
            relations.append("DENSE_COLUMN_ALIGNMENT")
        if "HORIZONTAL_ALIGNMENT" in codes:
            relations.append("SAME_HORIZONTAL_BAND")
        if "VERTICAL_GAP_COHERENCE" in codes:
            relations.append("VERTICAL_SUCCESSOR")
    return make_topology_fingerprint_v1(
        {
            "format_version": TOPOLOGY_FEATURE_FORMAT_VERSION,
            "evidence_mode": evidence_mode,
            "page_orientation": _page_orientation(projection),
            "primary_line_count_bucket": _bucket(metrics["primary_line_count"]),
            "primary_word_count_bucket": _bucket(metrics["primary_word_count"]),
            "supplemental_line_count_bucket": _bucket(metrics["supplemental_line_count"]),
            "quarantine_count_bucket": _bucket(metrics["quarantined_atom_count"]),
            "source_object_kind_sequence": [
                proposal["kind"] for proposal in proposal_set["proposals"]
            ],
            "relation_code_sequence": relations,
        }
    )


def _page_metrics(
    projection: Mapping[str, Any],
    proposal_set: Mapping[str, Any],
) -> dict[str, Any]:
    neutral_metrics = projection["neutral_page_v1"]["metrics"]
    proposal_counts = Counter(proposal["kind"] for proposal in proposal_set["proposals"])
    disposition_counts = Counter(
        item["primary_disposition"] for item in proposal_set["dispositions"]
    )
    return {
        "atom_count": neutral_metrics["atom_count"],
        "upstream_line_axis_count": neutral_metrics["upstream_line_axis_count"],
        "upstream_word_axis_count": neutral_metrics["upstream_word_axis_count"],
        "upstream_quarantined_span_axis_count": neutral_metrics[
            "upstream_quarantined_span_axis_count"
        ],
        "primary_line_count": neutral_metrics["primary_line_count"],
        "primary_word_count": neutral_metrics["primary_word_count"],
        "excluded_empty_line_axis_count": neutral_metrics["excluded_empty_line_axis_count"],
        "excluded_empty_word_axis_count": neutral_metrics["excluded_empty_word_axis_count"],
        "supplemental_line_count": neutral_metrics["supplemental_line_count"],
        "quarantined_atom_count": neutral_metrics["quarantined_atom_count"],
        "proposal_count": len(proposal_set["proposals"]),
        "proposal_kind_counts": {kind: proposal_counts[kind] for kind in _PROPOSAL_KINDS},
        "source_accounted_atom_count": len(proposal_set["dispositions"]),
        "disposition_counts": {
            disposition: disposition_counts[disposition] for disposition in _DISPOSITIONS
        },
    }


def _page_inventory(
    *,
    page_record: Mapping[str, Any],
    projection: Mapping[str, Any],
    proposal_projection: Mapping[str, Any],
) -> dict[str, Any]:
    proposal_set = proposal_projection["proposal_set_v1"]
    item = {
        "request_ordinal": page_record["request_ordinal"],
        "document_id": page_record["document_id"],
        "physical_page": page_record["physical_page"],
        "route": projection["route"],
        "status": projection["upstream_status"],
        "terminal": projection["terminal"],
        "projection_identity": projection["source_local_page_id"],
        "projection_sha256": canonical_json_sha256_v1(projection),
        "v2_geometry_proposal_projection_sha256": canonical_json_sha256_v1(proposal_projection),
        "topology_fingerprint": _topology_fingerprint(projection, proposal_set),
        "metrics": _page_metrics(projection, proposal_set),
    }
    item["page_inventory_identity_sha256"] = canonical_json_sha256_v1(item)
    return item


def _rollup_documents(
    document_ids: tuple[str, ...],
    pages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for page in pages:
        grouped[page["document_id"]].append(page)
    return [
        {
            "document_id": document_id,
            "page_count": len(grouped[document_id]),
            "terminal_page_count": sum(page["terminal"] for page in grouped[document_id]),
            "atom_count": sum(page["metrics"]["atom_count"] for page in grouped[document_id]),
            "proposal_count": sum(
                page["metrics"]["proposal_count"] for page in grouped[document_id]
            ),
            "source_accounted_atom_count": sum(
                page["metrics"]["source_accounted_atom_count"] for page in grouped[document_id]
            ),
        }
        for document_id in document_ids
    ]


def _rollup_corpus(
    authority: FinalizedV3SurveyAuthority,
    pages: list[dict[str, Any]],
) -> dict[str, Any]:
    route_counts = Counter(page["route"] for page in pages)
    status_counts = Counter(page["status"] for page in pages)
    result: dict[str, Any] = {
        "document_count": authority.document_count,
        "page_count": len(pages),
        "source_accounted_page_count": len(pages),
        "complete_page_count": sum(not page["terminal"] for page in pages),
        "terminal_page_count": sum(page["terminal"] for page in pages),
        "route_counts": {route: route_counts[route] for route in _ROUTES},
        "status_counts": {status: status_counts[status] for status in _STATUSES},
        "proposal_kind_counts": {
            kind: sum(page["metrics"]["proposal_kind_counts"][kind] for page in pages)
            for kind in _PROPOSAL_KINDS
        },
        "disposition_counts": {
            disposition: sum(page["metrics"]["disposition_counts"][disposition] for page in pages)
            for disposition in _DISPOSITIONS
        },
        "distinct_topology_fingerprint_count": len(
            {page["topology_fingerprint"] for page in pages}
        ),
    }
    for metric in _ADDITIVE_PAGE_METRICS:
        result[metric] = sum(page["metrics"][metric] for page in pages)
    return result


def _validate_authority(value: Any) -> dict[str, Any]:
    authority = _exact_dict(value, _AUTHORITY_FIELDS, "inventory authority")
    for field in (
        "aggregate_artifact_sha256",
        "aggregate_identity_sha256",
        "control_artifact_sha256",
        "control_identity_sha256",
        "sealed_plan_sha256",
    ):
        _sha(authority[field], f"inventory authority {field}")
    _positive(authority["aggregate_size_bytes"], "aggregate artifact size")
    _positive(authority["control_size_bytes"], "control artifact size")
    _positive(authority["document_count"], "authority document count")
    _positive(authority["request_count"], "authority request count")
    _positive(authority["referenced_object_count"], "authority object count")
    document_ids = authority["document_ids"]
    if (
        type(document_ids) is not list
        or any(
            type(document_id) is not str or _DOCUMENT_ID_RE.fullmatch(document_id) is None
            for document_id in document_ids
        )
        or document_ids != sorted(set(document_ids))
        or len(document_ids) != authority["document_count"]
    ):
        raise _error("inventory authority document identities drifted")
    if not same_typed_json_v1(
        authority,
        _authority_payload(FINALIZED_V3_SURVEY_AUTHORITY_V1),
    ):
        raise _error("inventory authority differs from the exact finalized V3 pin")
    return authority


def _validate_page(value: Any, *, expected_ordinal: int) -> dict[str, Any]:
    page = _exact_dict(value, _PAGE_FIELDS, "inventory page")
    if page["request_ordinal"] != expected_ordinal:
        raise _error("inventory request ordinal axis drifted")
    if (
        type(page["document_id"]) is not str
        or _DOCUMENT_ID_RE.fullmatch(page["document_id"]) is None
    ):
        raise _error("inventory page document identity drifted")
    _positive(page["physical_page"], "inventory physical page")
    if (
        page["route"] not in _ROUTES
        or page["status"] not in _STATUSES
        or _STATUS_ROUTE.get(page["status"]) != page["route"]
    ):
        raise _error("inventory page route/status drifted")
    if type(page["terminal"]) is not bool or page["terminal"] != page["status"].startswith(
        "UNRESOLVED_"
    ):
        raise _error("inventory page terminal state drifted")
    if (
        type(page["projection_identity"]) is not str
        or _PROJECTION_ID_RE.fullmatch(page["projection_identity"]) is None
    ):
        raise _error("inventory page projection identity drifted")
    _sha(page["projection_sha256"], "inventory page projection digest")
    _sha(
        page["v2_geometry_proposal_projection_sha256"],
        "inventory page V2 geometry-proposal projection digest",
    )
    if (
        type(page["topology_fingerprint"]) is not str
        or _TOPOLOGY_ID_RE.fullmatch(page["topology_fingerprint"]) is None
    ):
        raise _error("inventory topology fingerprint drifted")
    metrics = _exact_dict(page["metrics"], _PAGE_METRIC_FIELDS, "inventory page metrics")
    for metric in _ADDITIVE_PAGE_METRICS:
        _nonnegative(metrics[metric], f"inventory page {metric}")
    proposal_counts = _closed_counts(
        metrics["proposal_kind_counts"], _PROPOSAL_KINDS, "page proposal-kind counts"
    )
    disposition_counts = _closed_counts(
        metrics["disposition_counts"], _DISPOSITIONS, "page disposition counts"
    )
    if (
        sum(proposal_counts.values()) != metrics["proposal_count"]
        or sum(disposition_counts.values()) != metrics["source_accounted_atom_count"]
        or metrics["source_accounted_atom_count"] != metrics["atom_count"]
        or metrics["upstream_line_axis_count"]
        != metrics["primary_line_count"] + metrics["excluded_empty_line_axis_count"]
        or metrics["upstream_word_axis_count"]
        != metrics["primary_word_count"] + metrics["excluded_empty_word_axis_count"]
        or metrics["atom_count"]
        != metrics["primary_line_count"]
        + metrics["primary_word_count"]
        + metrics["excluded_empty_line_axis_count"]
        + metrics["excluded_empty_word_axis_count"]
        + metrics["supplemental_line_count"]
        + metrics["quarantined_atom_count"]
    ):
        raise _error("inventory page source accounting drifted")
    if page["terminal"]:
        if (
            metrics["primary_line_count"] != 0
            or metrics["primary_word_count"] != 0
            or metrics["proposal_count"] != 0
            or disposition_counts[PrimaryDisposition.OWNED_BY_SOURCE_OBJECT.value] != 0
            or disposition_counts[PrimaryDisposition.RETAINED_UNOWNED.value] != 0
        ):
            raise _error("terminal page promoted primary geometry or a source candidate")
    elif disposition_counts[PrimaryDisposition.UPSTREAM_TERMINAL_UNRESOLVED.value] != 0:
        raise _error("complete page carried a terminal-unresolved disposition")
    page_identity = _sha(page["page_inventory_identity_sha256"], "page inventory binding identity")
    page_identity_payload = {
        key: page[key] for key in page if key != "page_inventory_identity_sha256"
    }
    if page_identity != canonical_json_sha256_v1(page_identity_payload):
        raise _error("page inventory projection/proposal/topology binding drifted")
    return page


def validate_wave1_source_inventory_v1(value: Any) -> dict[str, Any]:
    """Validate the compact inventory and every page/document/corpus no-drop sum."""

    inventory = _exact_dict(value, _INVENTORY_FIELDS, "Wave-1 source inventory")
    if inventory["format_version"] != WAVE1_SOURCE_INVENTORY_FORMAT_VERSION_V1:
        raise _error("Wave-1 source inventory format drifted")
    if inventory["claim_boundary"] != WAVE1_SOURCE_INVENTORY_CLAIM_BOUNDARY_V1:
        raise _error("Wave-1 source inventory claim boundary drifted")
    if inventory["safety"] != _SAFETY:
        raise _error("Wave-1 source inventory safety drifted")
    authority = _validate_authority(inventory["authority"])
    _validate_source_structure_producer(inventory["source_structure_producer"])
    pages_value = inventory["pages"]
    if type(pages_value) is not list:
        raise _error("Wave-1 source inventory pages must be an array")
    pages = [
        _validate_page(page, expected_ordinal=index)
        for index, page in enumerate(pages_value, start=1)
    ]
    if len(pages) != authority["request_count"]:
        raise _error("Wave-1 source inventory request denominator drifted")
    document_ids = authority["document_ids"]
    if (
        {page["document_id"] for page in pages} != set(document_ids)
        or len({page["projection_identity"] for page in pages}) != len(pages)
        or len({page["projection_sha256"] for page in pages}) != len(pages)
        or len({page["page_inventory_identity_sha256"] for page in pages}) != len(pages)
        or len({(page["document_id"], page["physical_page"]) for page in pages}) != len(pages)
    ):
        raise _error("Wave-1 source inventory page coverage/identity drifted")

    documents_value = inventory["documents"]
    if type(documents_value) is not list or len(documents_value) != len(document_ids):
        raise _error("Wave-1 source inventory document rollup drifted")
    documents: list[dict[str, Any]] = []
    for expected_id, item in zip(document_ids, documents_value, strict=True):
        document = _exact_dict(item, _DOCUMENT_FIELDS, "inventory document")
        if document["document_id"] != expected_id:
            raise _error("inventory document order/identity drifted")
        for field in _DOCUMENT_FIELDS - {"document_id"}:
            _nonnegative(document[field], f"inventory document {field}")
        documents.append(document)
    expected_documents = _rollup_documents(tuple(document_ids), pages)
    if documents != expected_documents:
        raise _error("Wave-1 source inventory per-document accounting drifted")

    corpus = _exact_dict(inventory["corpus_metrics"], _CORPUS_FIELDS, "corpus metrics")
    for field in _CORPUS_FIELDS - {
        "route_counts",
        "status_counts",
        "proposal_kind_counts",
        "disposition_counts",
    }:
        _nonnegative(corpus[field], f"corpus metric {field}")
    _closed_counts(corpus["route_counts"], _ROUTES, "corpus route counts")
    _closed_counts(corpus["status_counts"], _STATUSES, "corpus status counts")
    _closed_counts(corpus["proposal_kind_counts"], _PROPOSAL_KINDS, "corpus proposal counts")
    _closed_counts(corpus["disposition_counts"], _DISPOSITIONS, "corpus disposition counts")
    expected_corpus = _rollup_corpus(
        FinalizedV3SurveyAuthority(
            aggregate_artifact_sha256=authority["aggregate_artifact_sha256"],
            aggregate_size_bytes=authority["aggregate_size_bytes"],
            aggregate_identity_sha256=authority["aggregate_identity_sha256"],
            control_artifact_sha256=authority["control_artifact_sha256"],
            control_size_bytes=authority["control_size_bytes"],
            control_identity_sha256=authority["control_identity_sha256"],
            sealed_plan_sha256=authority["sealed_plan_sha256"],
            document_ids=tuple(document_ids),
            document_count=authority["document_count"],
            request_count=authority["request_count"],
            referenced_object_count=authority["referenced_object_count"],
        ),
        pages,
    )
    if corpus != expected_corpus or corpus["source_accounted_atom_count"] != corpus["atom_count"]:
        raise _error("Wave-1 source inventory corpus accounting drifted")

    identity = _sha(inventory["inventory_identity_sha256"], "inventory identity")
    identity_payload = {
        key: inventory[key] for key in inventory if key != "inventory_identity_sha256"
    }
    if identity != canonical_json_sha256_v1(identity_payload):
        raise _error("Wave-1 source inventory identity drifted")
    return canonical_clone_v1(inventory)


def build_wave1_source_inventory_v1(project_root: Path) -> dict[str, Any]:
    """Build, but do not publish, the one compact finalized Wave-1 inventory."""

    project_root = project_root.resolve()
    producer_before = _source_structure_producer_receipt(project_root)
    pages: list[dict[str, Any]] = []
    with open_finalized_v3_survey_stream_v1(project_root) as stream:
        authority = stream.authority
        for authenticated_page in stream:
            projection = project_authenticated_page_v2(
                page_record=authenticated_page.page_record,
                page_result=authenticated_page.page_result,
            )
            proposal_set_v1 = generate_page_geometry_proposals_v1(projection)
            proposal_projection = make_page_proposal_set_v2(
                projection,
                proposal_set_v1=proposal_set_v1,
            )
            pages.append(
                _page_inventory(
                    page_record=authenticated_page.page_record,
                    projection=projection,
                    proposal_projection=proposal_projection,
                )
            )
    producer_after = _source_structure_producer_receipt(project_root)
    if not same_typed_json_v1(producer_after, producer_before):
        raise _error("source-structure producer changed during inventory construction")
    inventory = {
        "format_version": WAVE1_SOURCE_INVENTORY_FORMAT_VERSION_V1,
        "claim_boundary": WAVE1_SOURCE_INVENTORY_CLAIM_BOUNDARY_V1,
        "authority": _authority_payload(authority),
        "documents": _rollup_documents(authority.document_ids, pages),
        "pages": pages,
        "corpus_metrics": _rollup_corpus(authority, pages),
        "source_structure_producer": producer_before,
        "safety": canonical_clone_v1(_SAFETY),
    }
    inventory["inventory_identity_sha256"] = canonical_json_sha256_v1(inventory)
    return validate_wave1_source_inventory_v1(inventory)
