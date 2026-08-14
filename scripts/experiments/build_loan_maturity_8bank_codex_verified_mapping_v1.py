"""Verify eight loan-maturity graphs from fresh full-PDF VietOCR and Codex pixels.

The common matcher first scans every page of every document without bank/page
routing.  This verifier then joins the unique graph to a fixed, source-controlled
Codex review of the exact PDF pixels, recomputes all typed accounting equations,
and checks the live TM schema hierarchy.  The review contains observations only;
all final statuses are derived here.

VietOCR text is anchor evidence, never numeric truth.  In particular, the VCB
comparative medium-term proposal ``81.371.771`` remains preserved while the
independent pixel transcription ``81.371.777`` is used for the accounting check.
No broad-corpus, canonicalization, export, or production authority is granted.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    match_vietnamese_anchor_alias_v1,
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    _authority_snapshot,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "LoanMaturity8BankCodexVerifiedMappingV1Error",
    "build_live_loan_maturity_8bank_codex_verified_mapping_v1",
    "build_loan_maturity_8bank_codex_verified_mapping_v1",
    "validate_loan_maturity_8bank_codex_verified_mapping_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "LOAN_MATURITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_UNIQUE_FULL_PDF_VIETOCR_STRUCTURE_PLUS_PINNED_CODEX_"
    "PIXEL_REVIEW_ACCOUNTING_CLOSURE_AND_LIVE_TM_SCHEMA_HIERARCHY_ONLY_NO_BROAD_"
    "CORPUS_CANONICALIZATION_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0051-loan-maturity-8bank-codex-pixel-review-v1.json")
REVIEW_SHA256 = "30a7b40953e3578b0758bd93f83dbde238c80e01f20d06a64b4470e36f68113c"
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
_ROLE_BINDINGS = (
    ("SHORT_TERM", 753, "+ Ngắn hạn"),
    ("MEDIUM_TERM", 754, "+ Trung hạn"),
    ("LONG_TERM", 755, "+ Dài hạn"),
)
_ROLE_ALIASES = {
    "SHORT_TERM": ("Nợ ngắn hạn", "Cho vay ngắn hạn"),
    "MEDIUM_TERM": ("Nợ trung hạn", "Cho vay trung hạn"),
    "LONG_TERM": ("Nợ dài hạn", "Cho vay dài hạn"),
}
_EXPECTED_REVIEW_CHECKS = {
    "accounting_equations_independently_recomputed": True,
    "branch_and_ordered_children_visually_confirmed": True,
    "owner_parent_visually_confirmed": True,
    "period_and_unit_axes_visually_confirmed": True,
    "schema_parent_child_order_and_orphan_neighbour_independently_checked": True,
    "source_pdf_and_bound_render_opened": True,
    "statement_scope_heading_visually_confirmed": True,
    "totals_and_optional_population_boundaries_visually_confirmed": True,
}
_EXPECTED_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_mapping_rule": False,
    "broad_corpus_authority": False,
    "canonicalization_or_export_authority": False,
    "digit_conflict_silently_corrected": False,
    "reviewer_final_status_supplied": False,
    "semantic_similarity_alone_used_for_mapping": False,
    "transformer_numeric_proposal_used_as_pixel_truth": False,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_mapping_rule": False,
    "broad_corpus_authority": False,
    "canonicalization_or_export_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_hierarchy_checked": True,
    "mapping_authority_is_bounded_to_reviewed_source_rows": True,
    "old_ocr_transcript_used_for_semantic_matching": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "transformer_digit_conflicts_silently_corrected": False,
}
_RESULT_FIELDS = {
    "authority",
    "claim_boundary",
    "format_version",
    "input_refs",
    "metrics",
    "result_id",
    "state",
    "trials",
}
_HEX = set("0123456789abcdef")


class LoanMaturity8BankCodexVerifiedMappingV1Error(ValueError):
    """The fixed review, live graph, accounting closure, or schema drifted."""


def _error(message: str) -> LoanMaturity8BankCodexVerifiedMappingV1Error:
    return LoanMaturity8BankCodexVerifiedMappingV1Error(message)


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(char not in _HEX for char in value):
        raise _error(f"{label} SHA-256 drifted")
    return value


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise _error(f"{label} must be one non-empty string")
    return value


def _positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise _error(f"{label} must be one positive integer")
    return value


def _fixed_bytes(path: Path, expected_sha256: str) -> bytes:
    full = PROJECT_ROOT / path
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(full, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error(f"fixed artifact is not one regular file: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise _error(f"fixed artifact changed while reading: {path}")
    payload = b"".join(chunks)
    if len(payload) != before.st_size or hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"fixed artifact content identity drifted: {path}")
    return payload


def _json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise _error(f"{label} contains a duplicate JSON key")
            value[key] = item
        return value

    try:
        decoded = payload.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                _error(f"{label} contains non-finite JSON: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} must be one JSON object")
    return value


def _string_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if type(value) is not list or (not allow_empty and not value):
        raise _error(f"{label} must be one {'possibly empty' if allow_empty else 'non-empty'} list")
    return [_text(item, f"{label} item") for item in value]


def _review(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "banks",
        "claim_boundary",
        "format_version",
        "review_checks",
        "reviewer",
        "safety",
        "semantic_axis_sha256",
        "semantic_index_sha256",
        "state",
    }:
        raise _error("Codex pixel review top-level fields drifted")
    if (
        value["format_version"] != "LOAN_MATURITY_8BANK_CODEX_PIXEL_REVIEW_V1"
        or value["state"] != "CODEX_PIXEL_REVIEW_COMPLETE"
        or value["semantic_index_sha256"] != EXPECTED_INDEX_SHA256
        or value["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256
        or not same_typed_json_v1(value["review_checks"], _EXPECTED_REVIEW_CHECKS)
        or not same_typed_json_v1(value["safety"], _EXPECTED_REVIEW_SAFETY)
        or type(value["banks"]) is not list
        or len(value["banks"]) != len(EXPECTED_DOCUMENT_ORDER)
        or type(value["reviewer"]) is not dict
        or set(value["reviewer"]) != {"kind", "review_run_id"}
        or value["reviewer"]["kind"] != "CODEX_INDEPENDENT_PDF_PIXEL_AND_ACCOUNTING_REVIEW"
    ):
        raise _error("Codex pixel review identity, denominator, or safety drifted")
    _text(value["claim_boundary"], "review claim boundary")
    _text(value["reviewer"]["review_run_id"], "review run ID")
    for bank_offset, (bank, expected_bank) in enumerate(
        zip(value["banks"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(bank) is not dict or set(bank) != {
            "bank_code",
            "branch_pixel_transcription",
            "core_total",
            "grand_total",
            "optional_margin",
            "owner_evidence",
            "period_pixel_transcriptions",
            "physical_page",
            "rows",
            "statement_context_evidence",
            "target_render_sha256",
            "transformer_disagreements",
            "unit_lane_types",
        }:
            raise _error(f"review bank {bank_offset} fields drifted")
        if bank["bank_code"] != expected_bank:
            raise _error("review bank order drifted")
        _positive_int(bank["physical_page"], "review target physical page")
        _sha256(bank["target_render_sha256"], "review target render")
        _text(bank["branch_pixel_transcription"], "review branch pixel transcription")
        _string_list(bank["period_pixel_transcriptions"], "review period pixels")
        lane_types = _string_list(bank["unit_lane_types"], "review lane types")
        if lane_types not in (["MONEY", "MONEY"], ["MONEY", "PERCENT", "MONEY", "PERCENT"]):
            raise _error("review typed lane layout drifted")
        for evidence_name in ("owner_evidence", "statement_context_evidence"):
            evidence = bank[evidence_name]
            fields = {"physical_page", "pixel_transcription", "render_sha256"}
            if evidence_name == "statement_context_evidence":
                fields |= {"mode", "report_scope"}
            if type(evidence) is not dict or set(evidence) != fields:
                raise _error(f"review {evidence_name} fields drifted")
            _positive_int(evidence["physical_page"], f"review {evidence_name} page")
            _sha256(evidence["render_sha256"], f"review {evidence_name} render")
            _text(evidence["pixel_transcription"], f"review {evidence_name} text")
        context = bank["statement_context_evidence"]
        if (
            context["mode"]
            not in {"PAGE_LOCAL_VISIBLE_HEADING", "DOCUMENT_PRECEDING_VISIBLE_HEADING"}
            or context["report_scope"] != "CONSOLIDATED"
            or context["physical_page"] > bank["physical_page"]
        ):
            raise _error("review statement context mode/scope/order drifted")
        if type(bank["rows"]) is not list or len(bank["rows"]) != len(_ROLE_BINDINGS):
            raise _error("review row denominator drifted")
        for row, (role, _schema_id, _canonical_name) in zip(
            bank["rows"], _ROLE_BINDINGS, strict=True
        ):
            if type(row) is not dict or set(row) != {"pixel_label", "role", "values"}:
                raise _error("review row fields drifted")
            if row["role"] != role or len(_string_list(row["values"], "review row values")) != len(
                lane_types
            ):
                raise _error("review row role/value denominator drifted")
            _text(row["pixel_label"], "review row pixel label")
        for total_name in ("core_total", "grand_total"):
            total = _string_list(bank[total_name], f"review {total_name}", allow_empty=True)
            if total and len(total) != len(lane_types):
                raise _error(f"review {total_name} lane denominator drifted")
        margin = bank["optional_margin"]
        if margin is not None:
            if type(margin) is not dict or set(margin) != {"pixel_label", "values"}:
                raise _error("review optional margin fields drifted")
            _text(margin["pixel_label"], "review optional margin label")
            if len(_string_list(margin["values"], "review optional margin values")) != len(
                lane_types
            ):
                raise _error("review optional margin lane denominator drifted")
        if type(bank["transformer_disagreements"]) is not list:
            raise _error("review Transformer disagreement ledger drifted")
        for disagreement in bank["transformer_disagreements"]:
            if type(disagreement) is not dict or set(disagreement) != {
                "disposition",
                "field",
                "pixel_transcription",
                "semantic_proposal",
            }:
                raise _error("review Transformer disagreement fields drifted")
            for key in disagreement:
                _text(disagreement[key], f"review Transformer disagreement {key}")
    return canonical_clone_v1(value)


def _money(value: str) -> int:
    compact = value.strip().replace(" ", "")
    negative = compact.startswith("(") and compact.endswith(")")
    compact = compact.strip("()").lstrip("+")
    if compact.startswith("-"):
        negative = True
        compact = compact[1:]
    digits = compact.replace(".", "").replace(",", "")
    if not digits.isdigit():
        raise _error(f"review money surface is not one integer: {value}")
    number = int(digits)
    return -number if negative else number


def _percent(value: str) -> Decimal:
    try:
        number = Decimal(value.strip().rstrip("%").replace(",", "."))
    except InvalidOperation as exc:
        raise _error(f"review percent surface is invalid: {value}") from exc
    if not number.is_finite():
        raise _error("review percent surface is non-finite")
    return number


def _render_sha(page: Mapping[str, Any]) -> str:
    binding = page.get("render_binding")
    if type(binding) is not dict:
        raise _error("full-document render binding drifted")
    return _sha256(binding.get("sha256"), "full-document render binding")


def _document_by_bank(documents: Sequence[Mapping[str, Any]], bank_code: str) -> Mapping[str, Any]:
    matches = [document for document in documents if document.get("bank_code") == bank_code]
    if len(matches) != 1:
        raise _error("full-document bank provenance denominator drifted")
    return matches[0]


def _page_by_physical(document: Mapping[str, Any], physical_page: int) -> Mapping[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error("full-document page inventory drifted")
    matches = [page for page in pages if page.get("physical_page") == physical_page]
    if len(matches) != 1:
        raise _error("review physical page is not unique in the bound document")
    return matches[0]


def _surface_compatible(semantic: str, pixel: str, aliases: Sequence[str]) -> bool:
    def _without_enumeration(value: str) -> str:
        normalized = normalize_vietnamese_anchor_v1(value)
        return re.sub(r"^(?:[0-9]+\s+)+", "", normalized)

    semantic_key = _without_enumeration(semantic)
    pixel_key = _without_enumeration(pixel)
    alias_keys = [_without_enumeration(alias) for alias in aliases]
    if match_vietnamese_anchor_alias_v1(pixel_key, aliases) is None and not any(
        alias_key in pixel_key or pixel_key in alias_key for alias_key in alias_keys
    ):
        return False
    return (
        semantic_key == pixel_key
        or match_vietnamese_anchor_alias_v1(semantic, [pixel]) is not None
        or semantic_key in pixel_key
        or pixel_key in semantic_key
    )


def _value(semantic: str, pixel: str, lane_type: str, disagreements: Sequence[Any]) -> Any:
    if lane_type == "MONEY":
        semantic_value = _money(semantic)
        pixel_value = _money(pixel)
    elif lane_type == "PERCENT":
        semantic_value = _percent(semantic)
        pixel_value = _percent(pixel)
    else:
        raise _error("unsupported review lane type")
    if semantic_value != pixel_value and not any(
        item["semantic_proposal"] == semantic and item["pixel_transcription"] == pixel
        for item in disagreements
    ):
        raise _error("semantic/pixel value conflict lacks an explicit review disposition")
    return pixel_value


def _schema(schema_by_id: Mapping[int, Any]) -> dict[str, Any]:
    required = {716, 752, 753, 754, 755, 5747, 1944}
    if any(schema_id not in schema_by_id for schema_id in required):
        raise _error("live TM schema is missing the maturity hierarchy")
    owner = schema_by_id[716]
    parent = schema_by_id[752]
    if (
        owner.canonical_name != "Cho vay khách hàng"
        or parent.canonical_name != "Phân tích dư nợ theo thời gian đáo hạn"
        or parent.parent_id != 716
        or list(parent.children) != [753, 754, 755, 5747]
    ):
        raise _error("live TM maturity owner/parent hierarchy drifted")
    mapped: list[dict[str, Any]] = []
    for role, schema_id, canonical_name in _ROLE_BINDINGS:
        item = schema_by_id[schema_id]
        if (
            item.canonical_name != canonical_name
            or item.parent_id != 752
            or item.display_order != {753: 201, 754: 202, 755: 203}[schema_id]
            or item.statement_type != "TM"
            or "CONSOLIDATED" not in item.scope
        ):
            raise _error(f"live TM maturity role {schema_id} drifted")
        mapped.append({"canonical_name": canonical_name, "report_norm_id": schema_id, "role": role})
    margin = schema_by_id[5747]
    orphan = schema_by_id[1944]
    if (
        margin.canonical_name != "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
        or margin.parent_id != 752
        or margin.display_order != 204
        or orphan.canonical_name != margin.canonical_name
        or orphan.parent_id is not None
        or orphan.hierarchy_level is not None
    ):
        raise _error("live TM maturity optional-margin/orphan distinction drifted")
    return {
        "mapped_roles": mapped,
        "optional_margin": {"canonical_name": margin.canonical_name, "report_norm_id": 5747},
        "orphan_near_neighbour": {"canonical_name": orphan.canonical_name, "report_norm_id": 1944},
    }


def build_loan_maturity_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_by_id: Mapping[int, Any],
    *,
    review_sha256: str,
) -> dict[str, Any]:
    """Derive bounded verified mappings from exact live inputs and one fixed review."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("full-document semantic axis identity drifted")
    reviewed = _review(review)
    _sha256(review_sha256, "Codex pixel review")
    if type(crop_manifest) is not dict or type(crop_manifest.get("documents")) is not list:
        raise _error("full-document crop manifest shape drifted")
    if type(structure_scan) is not dict or type(structure_scan.get("trials")) is not list:
        raise _error("full-document maturity structure scan shape drifted")
    if not same_typed_json_v1(
        structure_scan.get("metrics"),
        {
            "accepted_numeric_graph_count": 0,
            "complete_context_region_count": 8,
            "document_count": 8,
            "document_multiple_complete_context_region_count": 0,
            "document_unique_candidate_count": 8,
            "mapping_verified_count": 0,
            "near_region_count": 14,
            "ordered_anchor_region_count": 8,
            "structure_resolved_numeric_unresolved_count": 8,
            "total_document_candidate_count": 8,
            "unresolved_document_count": 0,
        },
    ):
        raise _error("full-document maturity structure denominator drifted")
    schema = _schema(schema_by_id)
    raw_documents = semantic_index.get("documents")
    manifest_documents = crop_manifest["documents"]
    if type(raw_documents) is not list or len(raw_documents) != 8 or len(manifest_documents) != 8:
        raise _error("full-document input denominator drifted")

    trials: list[dict[str, Any]] = []
    for bank_offset, (bank_review, expected_bank) in enumerate(
        zip(reviewed["banks"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if bank_review["bank_code"] != expected_bank:
            raise _error("review bank order drifted during derivation")
        _document_by_bank(raw_documents, expected_bank)
        manifest_document = _document_by_bank(manifest_documents, expected_bank)
        target_page = _page_by_physical(manifest_document, bank_review["physical_page"])
        if _render_sha(target_page) != bank_review["target_render_sha256"]:
            raise _error("review target render does not bind the full-document manifest")
        for evidence_key in ("owner_evidence", "statement_context_evidence"):
            evidence = bank_review[evidence_key]
            evidence_page = _page_by_physical(manifest_document, evidence["physical_page"])
            if _render_sha(evidence_page) != evidence["render_sha256"]:
                raise _error(f"review {evidence_key} render does not bind the manifest")
        context_key = normalize_vietnamese_anchor_v1(
            bank_review["statement_context_evidence"]["pixel_transcription"]
        )
        if "bao cao tai chinh" not in context_key or "hop nhat" not in context_key:
            raise _error(
                "review statement context is not visibly consolidated financial statements"
            )

        scan_matches = [
            trial
            for trial in structure_scan["trials"]
            if trial.get("bank_provenance") == expected_bank
        ]
        if len(scan_matches) != 1:
            raise _error("structure scan bank trial denominator drifted")
        scan_trial = scan_matches[0]
        matcher = scan_trial["matcher_result"]
        regions = scan_trial["region_scan"]["regions"]
        if (
            matcher.get("status") != "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
            or matcher.get("document_candidate_count") != 1
            or len(regions) != 1
            or regions[0]["page_sequence"] != bank_review["physical_page"]
        ):
            raise _error("review target is not the unique whole-document maturity graph")
        graph = matcher["result"]["graph"]
        if (
            graph is None
            or graph["arithmetic_status"] != "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
        ):
            raise _error("structure scan unexpectedly supplied numeric authority")
        if not _surface_compatible(
            graph["owner"]["surface"],
            bank_review["owner_evidence"]["pixel_transcription"],
            ("Cho vay khách hàng", "Dư nợ cho vay khách hàng", "Các khoản cho vay khách hàng"),
        ):
            raise _error("review owner pixels do not reconcile with the unique graph")
        branch_semantic = normalize_vietnamese_anchor_v1(graph["branch"]["surface"])
        branch_pixel = normalize_vietnamese_anchor_v1(bank_review["branch_pixel_transcription"])
        if branch_semantic not in branch_pixel and branch_pixel not in branch_semantic:
            raise _error("review branch pixels do not reconcile with the unique graph")
        if graph["unit_scope"]["lane_types"] != bank_review["unit_lane_types"]:
            raise _error("review and graph typed lane layouts disagree")
        if len(graph["axes"]) != 2:
            raise _error("unique maturity graph must expose exactly two period populations")

        lane_types = bank_review["unit_lane_types"]
        disagreements = bank_review["transformer_disagreements"]
        verified_rows: list[dict[str, Any]] = []
        parsed_rows: list[list[Any]] = []
        for graph_row, review_row, (role, schema_id, canonical_name) in zip(
            graph["rows"], bank_review["rows"], _ROLE_BINDINGS, strict=True
        ):
            if graph_row["role"] != role or not _surface_compatible(
                graph_row["label_surface"], review_row["pixel_label"], _ROLE_ALIASES[role]
            ):
                raise _error(f"review row label does not reconcile for {expected_bank} {role}")
            if len(graph_row["values"]) != len(lane_types):
                raise _error("unique graph row lane denominator drifted")
            parsed: list[Any] = []
            values: list[dict[str, Any]] = []
            for lane_index, (graph_value, pixel_value, lane_type) in enumerate(
                zip(graph_row["values"], review_row["values"], lane_types, strict=True)
            ):
                parsed.append(_value(graph_value["surface"], pixel_value, lane_type, disagreements))
                values.append(
                    {
                        "independent_pixel_transcription": pixel_value,
                        "lane_index": lane_index,
                        "lane_type": lane_type,
                        "semantic_proposal": graph_value["surface"],
                        "source_line_index": graph_value["source_line_index"],
                    }
                )
            parsed_rows.append(parsed)
            verified_rows.append(
                {
                    "canonical_name": canonical_name,
                    "independent_pixel_label": review_row["pixel_label"],
                    "report_norm_id": schema_id,
                    "role": role,
                    "semantic_proposal_label": graph_row["label_surface"],
                    "status": "VERIFIED_BY_CODEX",
                    "values": values,
                }
            )

        money_positions = [index for index, kind in enumerate(lane_types) if kind == "MONEY"]
        percent_positions = [index for index, kind in enumerate(lane_types) if kind == "PERCENT"]
        sums: list[Any] = [
            sum(row[index] for row in parsed_rows) for index in range(len(lane_types))
        ]
        parsed_core = [
            _money(value) if lane_types[index] == "MONEY" else _percent(value)
            for index, value in enumerate(bank_review["core_total"])
        ]
        if parsed_core and parsed_core != sums:
            raise _error("reviewed core total does not close the three maturity rows")
        for index in percent_positions:
            if sums[index] != Decimal("100.00"):
                raise _error("reviewed percentage population does not close to 100")
        margin_review = bank_review["optional_margin"]
        margin_graph = graph["optional_margin"]
        verified_margin: dict[str, Any] | None = None
        if margin_review is None:
            if margin_graph is not None or bank_review["grand_total"]:
                raise _error("review optional population boundary disagrees with the graph")
        else:
            if margin_graph is None or len(margin_graph["values"]) != len(lane_types):
                raise _error("reviewed optional margin is absent from the unique graph")
            if not _surface_compatible(
                margin_graph["label_surface"],
                margin_review["pixel_label"],
                (
                    "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
                    "Các khoản cho vay margin chứng khoán và ứng trước khách hàng",
                    "Cho vay giao dịch ký quỹ và ứng trước cho khách hàng",
                ),
            ):
                raise _error("reviewed optional-margin label does not reconcile with the graph")
            parsed_margin: list[Any] = []
            margin_values: list[dict[str, Any]] = []
            for lane_index, (graph_value, pixel_value, lane_type) in enumerate(
                zip(margin_graph["values"], margin_review["values"], lane_types, strict=True)
            ):
                parsed_margin.append(
                    _value(graph_value["surface"], pixel_value, lane_type, disagreements)
                )
                margin_values.append(
                    {
                        "independent_pixel_transcription": pixel_value,
                        "lane_index": lane_index,
                        "lane_type": lane_type,
                        "semantic_proposal": graph_value["surface"],
                        "source_line_index": graph_value["source_line_index"],
                    }
                )
            parsed_grand = [
                _money(value) if lane_types[index] == "MONEY" else _percent(value)
                for index, value in enumerate(bank_review["grand_total"])
            ]
            if len(parsed_grand) != len(lane_types) or any(
                parsed_grand[index] != sums[index] + parsed_margin[index]
                for index in money_positions
            ):
                raise _error("reviewed grand total does not close core plus optional margin")
            verified_margin = {
                "canonical_name": schema["optional_margin"]["canonical_name"],
                "independent_pixel_label": margin_review["pixel_label"],
                "report_norm_id": 5747,
                "semantic_proposal_label": margin_graph["label_surface"],
                "status": "VERIFIED_BY_CODEX",
                "values": margin_values,
            }
        source_total = bank_review["core_total"] or bank_review["grand_total"]
        trials.append(
            {
                "bank_provenance": expected_bank,
                "document_ordinal": bank_offset,
                "near_neighbour_dispositions": [
                    {
                        "report_norm_id": 1944,
                        "status": "UNRESOLVED_SCHEMA_ORPHAN_MAPPING_INELIGIBLE",
                        "whole_document_absence_claim": False,
                    },
                    *(
                        []
                        if verified_margin is not None
                        else [
                            {
                                "report_norm_id": 5747,
                                "status": "NOT_OBSERVED_IN_BOUND_SOURCE_TABLE",
                                "whole_document_absence_claim": False,
                            }
                        ]
                    ),
                ],
                "physical_page": bank_review["physical_page"],
                "source_only_total": {
                    "independent_pixel_values": source_total,
                    "report_norm_id": None,
                    "status": "VERIFIED_SOURCE_ONLY",
                },
                "statement_context": canonical_clone_v1(bank_review["statement_context_evidence"]),
                "status": "VERIFIED_BY_CODEX",
                "target_render_sha256": bank_review["target_render_sha256"],
                "transformer_disagreements": canonical_clone_v1(disagreements),
                "verified_mappings": [
                    *verified_rows,
                    *([] if verified_margin is None else [verified_margin]),
                ],
            }
        )

    verified_core = sum(
        mapping["report_norm_id"] in {753, 754, 755}
        for trial in trials
        for mapping in trial["verified_mappings"]
    )
    verified_margin_count = sum(
        mapping["report_norm_id"] == 5747
        for trial in trials
        for mapping in trial["verified_mappings"]
    )
    unresolved_neighbours = sum(len(trial["near_neighbour_dispositions"]) for trial in trials)
    metrics = {
        "document_count": len(trials),
        "document_unique_structure_count": len(trials),
        "mapped_item_verified_by_codex_count": verified_core + verified_margin_count,
        "optional_margin_verified_by_codex_count": verified_margin_count,
        "source_only_total_verified_count": len(trials),
        "transformer_disagreement_preserved_count": sum(
            len(trial["transformer_disagreements"]) for trial in trials
        ),
        "unresolved_near_neighbour_count": unresolved_neighbours,
        "verified_by_codex_core_row_count": verified_core,
    }
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "codex_pixel_review": {"path": REVIEW_PATH.as_posix(), "sha256": review_sha256},
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": structure_scan["scan_id"],
        },
        "metrics": metrics,
        "state": "LOAN_MATURITY_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "lm8bcv1:result:" + canonical_json_sha256_v1(material)}
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("verified mapping result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "LOAN_MATURITY_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
        or type(value["metrics"]) is not dict
        or type(value["input_refs"]) is not dict
    ):
        raise _error("verified mapping result identity/authority drifted")
    clone = canonical_clone_v1(value)
    result_id = clone.pop("result_id")
    if result_id != "lm8bcv1:result:" + canonical_json_sha256_v1(clone):
        raise _error("verified mapping result identity drifted")
    verified_core = 0
    verified_margin = 0
    unresolved = 0
    disagreement_count = 0
    for trial, expected_bank in zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True):
        source_only_total = trial.get("source_only_total") if type(trial) is dict else None
        if (
            type(trial) is not dict
            or set(trial)
            != {
                "bank_provenance",
                "document_ordinal",
                "near_neighbour_dispositions",
                "physical_page",
                "source_only_total",
                "statement_context",
                "status",
                "target_render_sha256",
                "transformer_disagreements",
                "verified_mappings",
            }
            or trial["bank_provenance"] != expected_bank
            or trial["status"] != "VERIFIED_BY_CODEX"
            or type(trial["verified_mappings"]) is not list
            or type(trial["near_neighbour_dispositions"]) is not list
            or type(trial["transformer_disagreements"]) is not list
            or type(source_only_total) is not dict
            or set(source_only_total) != {"independent_pixel_values", "report_norm_id", "status"}
            or source_only_total["status"] != "VERIFIED_SOURCE_ONLY"
            or source_only_total["report_norm_id"] is not None
            or type(source_only_total["independent_pixel_values"]) is not list
            or not source_only_total["independent_pixel_values"]
        ):
            raise _error("verified mapping trial shape/status drifted")
        core_ids = [
            mapping["report_norm_id"]
            for mapping in trial["verified_mappings"]
            if mapping["report_norm_id"] in {753, 754, 755}
        ]
        if core_ids != [753, 754, 755] or any(
            mapping.get("status") != "VERIFIED_BY_CODEX" for mapping in trial["verified_mappings"]
        ):
            raise _error("verified mapping row order/status drifted")
        verified_core += len(core_ids)
        verified_margin += sum(
            mapping["report_norm_id"] == 5747 for mapping in trial["verified_mappings"]
        )
        unresolved += len(trial["near_neighbour_dispositions"])
        disagreement_count += len(trial["transformer_disagreements"])
    expected_metrics = {
        "document_count": 8,
        "document_unique_structure_count": 8,
        "mapped_item_verified_by_codex_count": verified_core + verified_margin,
        "optional_margin_verified_by_codex_count": verified_margin,
        "source_only_total_verified_count": 8,
        "transformer_disagreement_preserved_count": disagreement_count,
        "unresolved_near_neighbour_count": unresolved,
        "verified_by_codex_core_row_count": verified_core,
    }
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("verified mapping metrics drifted")
    return canonical_clone_v1(value)


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required experiment module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _live_inputs() -> tuple[Any, Any, Any, Any, Mapping[int, Any]]:
    builder = _load_module(
        PROJECT_ROOT
        / "scripts/experiments/build_loan_maturity_full_document_vietocr_request_v1.py",
        "full_document_vietocr_builder_for_codex_mapping_v1",
    )
    semantic_index = builder.read_verified_vietocr_proposals_v1()
    index_raw = _fixed_bytes(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    if not same_typed_json_v1(_json_bytes(index_raw, "semantic index"), semantic_index):
        raise _error("semantic index bytes and authenticated projection disagree")
    manifest = _json_bytes(
        _fixed_bytes(
            CROP_MANIFEST_PATH,
            builder.verify_full_document_freeze_v1(replay_geometry=False)["manifest_sha256"],
        ),
        "crop manifest",
    )
    scanner = _load_module(
        PROJECT_ROOT / "scripts/experiments/scan_loan_maturity_full_document_vietocr_v1.py",
        "full_document_maturity_scan_for_codex_mapping_v1",
    )
    structure_scan = scanner.build_loan_maturity_full_document_scan_v1(semantic_index)
    review = _review(_json_bytes(_fixed_bytes(REVIEW_PATH, REVIEW_SHA256), "Codex pixel review"))
    _schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return semantic_index, manifest, structure_scan, review, schema_by_id


def build_live_loan_maturity_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay all fixed sources and derive the bounded eight-bank verification."""

    semantic_index, manifest, structure_scan, review, schema_by_id = _live_inputs()
    return build_loan_maturity_8bank_codex_verified_mapping_v1(
        semantic_index,
        manifest,
        structure_scan,
        review,
        schema_by_id,
        review_sha256=REVIEW_SHA256,
    )


def validate_loan_maturity_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild a persisted result from every fixed live input."""

    persisted = _validate_result(value)
    rebuilt = build_live_loan_maturity_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("verified mapping result does not replay exactly")
    return rebuilt


def main() -> int:
    print(
        json.dumps(
            build_live_loan_maturity_8bank_codex_verified_mapping_v1(),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
