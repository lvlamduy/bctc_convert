"""Verify that the loan-currency TM family is absent from the fixed eight PDFs.

The bank-blind matcher performs the actual complete-PDF search.  This module
adds a bounded image review of each customer-loan note's first and last item,
the next-family boundary, and a nearby VND/foreign-currency negative control.
Bank/page identities are evidence locators only; they never route matching.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "LoanCurrency8BankCodexVerifiedAbsenceV1Error",
    "build_loan_currency_8bank_codex_verified_absence_v1",
    "build_live_loan_currency_8bank_codex_verified_absence_v1",
    "validate_live_loan_currency_8bank_codex_verified_absence_v1",
    "validate_loan_currency_8bank_codex_verified_absence_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "LOAN_CURRENCY_8BANK_CODEX_VERIFIED_ABSENCE_V1"
REVIEW_FORMAT = "LOAN_CURRENCY_8BANK_CODEX_PIXEL_ABSENCE_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_BOUND_COMPLETE_PDFS_FRESH_VIETOCR_SHARED_LOAN_CURRENCY_GRAPH_"
    "CUSTOMER_LOAN_NOTE_FIRST_LAST_IMAGE_REVIEW_CURRENCY_PAIR_NEGATIVE_CONTROLS_"
    "LIVE_TM_SCHEMA_756_TO_758_NO_BROAD_CORPUS_NUMERIC_MAPPING_OR_EXPORT_AUTHORITY"
)
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
REVIEW_PATH = Path("docs/experiments/E-0064-loan-currency-8bank-codex-pixel-absence-review-v1.json")
RESULT_PATH = Path("docs/experiments/E-0064-loan-currency-8bank-codex-verified-absence-v1.json")
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
_REVIEW_CLAIM = (
    "FIXED_EIGHT_BOUND_PDF_COMPLETE_LOAN_NOTE_FIRST_LAST_PIXEL_REVIEW_WITH_"
    "CURRENCY_PAIR_NEGATIVE_CONTROLS_NO_NUMERIC_MAPPING_OR_EXPORT_AUTHORITY"
)
_REVIEW_SAFETY = {
    "bank_page_or_filename_used_for_matching": False,
    "broad_corpus_absence_claim": False,
    "currency_pair_text_alone_can_establish_family": False,
    "fixed_eight_pdf_loan_note_absence_claim": True,
    "mapping_authority": False,
}
_AUTHORITY = {
    "bank_page_or_filename_used_for_matching_or_routing": False,
    "broad_corpus_or_other_period_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fixed_eight_bound_pdf_loan_note_absence_authority": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority": False,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_order_and_cluster_boundaries_preserved": True,
    "text_similarity_alone_used_for_decision": False,
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
_SCHEMA_EXPECTED = {
    756: ("Phân tích theo loại hình tiền tệ", 716, 209),
    757: ("+ Cho vay bằng đồng Việt Nam", 756, 210),
    758: ("+ Cho vay bằng ngoại tệ và vàng", 756, 211),
}
_LOCATORS = {
    "ACB": ([17, 18], (17, 51), (18, 30), (18, 46), (16, 15, 18)),
    "MBB": ([31, 32, 33], (31, 29), (33, 0), (34, 1), (30, 60, 63)),
    "VPB": ([42, 43, 44], (42, 5), (44, 7), (45, 5), (39, 18, 22)),
    "HDB": ([26, 27], (26, 7), (27, 6), (28, 7), (30, 84, 87)),
    "VCB": ([30, 31], (30, 38), (31, 8), (31, 25), (34, 49, 52)),
    "CTG": ([38, 39], (38, 33), (39, 26), (39, 42), (41, 36, 39)),
    "BID": ([22], (22, 5), (22, 59), (23, 5), (25, 11, 14)),
    "VIB": ([33, 34], (33, 5), (34, 7), (34, 65), (32, 11, 14)),
}


class LoanCurrency8BankCodexVerifiedAbsenceV1Error(ValueError):
    """The full scan, image review, or live schema absence proof drifted."""


def _error(message: str) -> LoanCurrency8BankCodexVerifiedAbsenceV1Error:
    return LoanCurrency8BankCodexVerifiedAbsenceV1Error(message)


def _load_module(name: str, filename: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load experiment support module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


scanner = _load_module(
    "loan_currency_full_document_scan_for_absence",
    "scan_loan_currency_full_document_vietocr_v1.py",
)


def _strict_json(payload: bytes, label: str) -> Any:
    def reject_constant(value: str) -> None:
        raise _error(f"{label} contains non-finite JSON number: {value}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _error(f"{label} contains duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(
            payload,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict UTF-8 JSON") from exc


def _stable_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], str]:
    before = path.stat()
    payload = path.read_bytes()
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise _error(f"JSON changed while reading: {path}")
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed JSON bytes drifted: {path}")
    value = _strict_json(payload, path.as_posix())
    if type(value) is not dict:
        raise _error(f"fixed JSON root must be one object: {path}")
    return value, digest


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise _error(f"{label} SHA-256 drifted")
    return value


def _document(value: dict[str, Any], bank: str) -> dict[str, Any]:
    documents = value.get("documents")
    if type(documents) is not list:
        raise _error("full-document artifact documents drifted")
    matches = [item for item in documents if type(item) is dict and item.get("bank_code") == bank]
    if len(matches) != 1:
        raise _error(f"full-document artifact must contain one {bank} document")
    return matches[0]


def _page(document: dict[str, Any], physical_page: int) -> dict[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error("document pages drifted")
    matches = [
        item for item in pages if type(item) is dict and item.get("physical_page") == physical_page
    ]
    if len(matches) != 1:
        raise _error(f"document must contain physical page {physical_page}")
    return matches[0]


def _event(
    semantic_document: dict[str, Any],
    manifest_document: dict[str, Any],
    locator: tuple[int, int],
) -> dict[str, Any]:
    physical_page, line_index = locator
    semantic_page = _page(semantic_document, physical_page)
    manifest_page = _page(manifest_document, physical_page)
    lines = semantic_page.get("lines")
    if type(lines) is not list or not (0 <= line_index < len(lines)):
        raise _error("review source-line locator drifted")
    line = lines[line_index]
    if type(line) is not dict or line.get("source_line_index") != line_index:
        raise _error("review source line drifted")
    crop_ref = line.get("crop_ref")
    render_ref = manifest_page.get("render_binding")
    if type(crop_ref) is not dict or type(render_ref) is not dict:
        raise _error("review crop or page-render binding drifted")
    text = line.get("vietocr_text")
    if type(text) is not str:
        raise _error("review fresh-VietOCR text must be one exact string")
    return {
        "crop_sha256": _sha256(crop_ref.get("sha256"), "review crop"),
        "page": physical_page,
        "render_sha256": _sha256(render_ref.get("sha256"), "review page render"),
        "source_line_index": line_index,
        "text": text,
    }


def _expected_review(semantic_index: Any, crop_manifest: Any) -> dict[str, Any]:
    if type(semantic_index) is not dict or type(crop_manifest) is not dict:
        raise _error("review inputs must be exact JSON objects")
    documents: list[dict[str, Any]] = []
    for bank in EXPECTED_DOCUMENT_ORDER:
        span, owner, last, next_family, negative = _LOCATORS[bank]
        semantic_document = _document(semantic_index, bank)
        manifest_document = _document(crop_manifest, bank)
        negative_page, vnd_line, foreign_line = negative
        documents.append(
            {
                "bank": bank,
                "disposition": "NOT_OBSERVED_IN_BOUND_COMPLETE_PDF_LOAN_NOTE_SCOPE",
                "last_observed_loan_subfamily": _event(semantic_document, manifest_document, last),
                "loan_note_owner": _event(semantic_document, manifest_document, owner),
                "loan_note_span_pages": list(span),
                "negative_control": {
                    "family": "INTERBANK_DEPOSITS_AND_LOANS",
                    "foreign": _event(
                        semantic_document,
                        manifest_document,
                        (negative_page, foreign_line),
                    ),
                    "vnd": _event(semantic_document, manifest_document, (negative_page, vnd_line)),
                },
                "next_family_boundary": _event(semantic_document, manifest_document, next_family),
                "source_pdf_sha256": _sha256(
                    semantic_document.get("source_pdf", {}).get("sha256"), "source PDF"
                ),
            }
        )
    material = {
        "claim_boundary": _REVIEW_CLAIM,
        "documents": documents,
        "experiment_id": "E-0064",
        "format_version": REVIEW_FORMAT,
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "state": "COMPLETE",
    }
    return {
        **material,
        "review_id": "e0064:review:" + canonical_json_sha256_v1(material),
    }


def _validate_review(review: Any, semantic_index: Any, crop_manifest: Any) -> dict[str, Any]:
    expected = _expected_review(semantic_index, crop_manifest)
    if not same_typed_json_v1(review, expected):
        raise _error("fixed pixel-boundary review does not replay against live artifacts")
    return canonical_clone_v1(expected)


def _schema_projection(project_root: Path) -> dict[str, Any]:
    authority, by_id = _authority_snapshot(project_root)
    rows = []
    for report_norm_id, (name, parent, order) in _SCHEMA_EXPECTED.items():
        item = by_id.get(report_norm_id)
        if (
            item is None
            or item.canonical_name != name
            or item.parent_id != parent
            or item.display_order != order
            or item.statement_type != "TM"
        ):
            raise _error(f"live TM schema row {report_norm_id} drifted")
        rows.append(
            {
                "canonical_name": item.canonical_name,
                "display_order": item.display_order,
                "parent_report_norm_id": item.parent_id,
                "report_norm_id": report_norm_id,
            }
        )
    return {
        "order_authority": authority["order_authority"],
        "rows": rows,
        "tm_context_projection_sha256": authority["tm_context_projection_sha256"],
        "tm_schema_projection_sha256": authority["tm_schema_projection_sha256"],
    }


def _metrics(trials: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "bound_pdf_family_absence_verified_count": sum(
            item["status"] == "VERIFIED_NOT_OBSERVED_IN_BOUND_PDF" for item in trials
        ),
        "document_count": len(trials),
        "mapped_value_count": 0,
        "mapping_verified_count": 0,
        "schema_row_count": len(_SCHEMA_EXPECTED),
        "unresolved_item_count": 0,
    }


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("loan-currency verified-absence fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FIXED_EIGHT_BOUND_PDF_LOAN_CURRENCY_ABSENCE_VERIFIED"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("loan-currency verified-absence identity or authority drifted")
    for ordinal, (trial, bank) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if type(trial) is not dict or set(trial) != {
            "bank",
            "document_ordinal",
            "loan_note_span_pages",
            "matcher_result_id",
            "matcher_status",
            "report_norm_ids_not_observed",
            "source_pdf_sha256",
            "status",
        }:
            raise _error("loan-currency verified-absence trial fields drifted")
        if (
            trial["bank"] != bank
            or type(trial["document_ordinal"]) is not int
            or trial["document_ordinal"] != ordinal
            or trial["matcher_status"] != "UNRESOLVED_NO_COMPLETE_REGION"
            or not same_typed_json_v1(trial["report_norm_ids_not_observed"], [756, 757, 758])
            or trial["status"] != "VERIFIED_NOT_OBSERVED_IN_BOUND_PDF"
        ):
            raise _error("loan-currency trial status or schema interval drifted")
        _sha256(trial["source_pdf_sha256"], "trial source PDF")
    if not same_typed_json_v1(value["metrics"], _metrics(value["trials"])):
        raise _error("loan-currency verified-absence metrics drifted")
    if type(value["input_refs"]) is not dict:
        raise _error("loan-currency verified-absence inputs drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "e0064:result:" + canonical_json_sha256_v1(material):
        raise _error("loan-currency verified-absence identity drifted")
    return canonical_clone_v1(value)


def build_loan_currency_8bank_codex_verified_absence_v1(
    project_root: Path,
    semantic_index: Any,
    crop_manifest: Any,
    review: Any,
    *,
    input_refs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the bounded absence result from the live scan, review and TM schema."""

    checked_review = _validate_review(review, semantic_index, crop_manifest)
    scan = scanner.build_loan_currency_full_document_scan_v1(semantic_index)
    if (
        scan["metrics"]["loan_currency_region_count"] != 0
        or scan["metrics"]["document_unique_structural_match_count"] != 0
        or any(
            item["matcher_result"]["status"] != "UNRESOLVED_NO_COMPLETE_REGION"
            for item in scan["trials"]
        )
    ):
        raise _error("a complete loan-currency region exists; absence cannot be admitted")
    schema = _schema_projection(project_root)
    review_by_bank = {item["bank"]: item for item in checked_review["documents"]}
    trials = [
        {
            "bank": scan_trial["document_provenance"],
            "document_ordinal": scan_trial["document_ordinal"],
            "loan_note_span_pages": review_by_bank[scan_trial["document_provenance"]][
                "loan_note_span_pages"
            ],
            "matcher_result_id": scan_trial["matcher_result"]["result_id"],
            "matcher_status": scan_trial["matcher_result"]["status"],
            "report_norm_ids_not_observed": [756, 757, 758],
            "source_pdf_sha256": scan_trial["source_pdf_sha256"],
            "status": "VERIFIED_NOT_OBSERVED_IN_BOUND_PDF",
        }
        for scan_trial in scan["trials"]
    ]
    refs = input_refs or {
        "crop_manifest_payload_sha256": canonical_json_sha256_v1(crop_manifest),
        "pixel_review_id": checked_review["review_id"],
        "scan_id": scan["scan_id"],
        "semantic_index_payload_sha256": canonical_json_sha256_v1(semantic_index),
        "tm_schema": schema,
    }
    if type(refs) is not dict:
        raise _error("input refs must be one exact object")
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": canonical_clone_v1(refs),
        "metrics": _metrics(trials),
        "state": "FIXED_EIGHT_BOUND_PDF_LOAN_CURRENCY_ABSENCE_VERIFIED",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "e0064:result:" + canonical_json_sha256_v1(material)}
    )


def validate_loan_currency_8bank_codex_verified_absence_replay_v1(
    value: Any,
    project_root: Path,
    semantic_index: Any,
    crop_manifest: Any,
    review: Any,
    *,
    input_refs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Exact-rebuild the bounded result and reject coordinated self-rehashes."""

    checked = _validate_result(value)
    expected = build_loan_currency_8bank_codex_verified_absence_v1(
        project_root,
        semantic_index,
        crop_manifest,
        review,
        input_refs=input_refs,
    )
    if not same_typed_json_v1(checked, expected):
        raise _error("loan-currency verified-absence result does not replay exactly")
    return checked


def _live_inputs(
    project_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    semantic, semantic_sha = _stable_json(project_root / SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    manifest, manifest_sha = _stable_json(
        project_root / CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256
    )
    review, review_sha = _stable_json(project_root / REVIEW_PATH)
    refs = {
        "crop_manifest": {
            "path": CROP_MANIFEST_PATH.as_posix(),
            "sha256": manifest_sha,
        },
        "pixel_review": {
            "path": REVIEW_PATH.as_posix(),
            "review_id": review.get("review_id"),
            "sha256": review_sha,
        },
        "semantic_index": {
            "path": SEMANTIC_INDEX_PATH.as_posix(),
            "sha256": semantic_sha,
        },
        "tm_schema": _schema_projection(project_root),
    }
    return semantic, manifest, review, refs


def build_live_loan_currency_8bank_codex_verified_absence_v1(
    project_root: Path,
) -> dict[str, Any]:
    """Build from the fixed current-artifact paths."""

    semantic, manifest, review, refs = _live_inputs(project_root)
    return build_loan_currency_8bank_codex_verified_absence_v1(
        project_root, semantic, manifest, review, input_refs=refs
    )


def validate_live_loan_currency_8bank_codex_verified_absence_v1(
    project_root: Path,
) -> dict[str, Any]:
    """Validate the persisted fixed result against every live input."""

    persisted, _ = _stable_json(project_root / RESULT_PATH)
    semantic, manifest, review, refs = _live_inputs(project_root)
    return validate_loan_currency_8bank_codex_verified_absence_replay_v1(
        persisted,
        project_root,
        semantic,
        manifest,
        review,
        input_refs=refs,
    )


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    result = (
        validate_live_loan_currency_8bank_codex_verified_absence_v1(PROJECT_ROOT)
        if args.validate
        else build_live_loan_currency_8bank_codex_verified_absence_v1(PROJECT_ROOT)
    )
    payload = canonical_json_bytes_v1(result)
    if args.output is None:
        sys.stdout.buffer.write(payload)
    else:
        args.output.write_bytes(payload)


if __name__ == "__main__":
    _main()
