"""Verify annual-2025 customer-loan currency disclosures for eight banks.

The complete-PDF matcher supplies structure proposals only.  This builder binds
the two unique annual disclosures to independently reviewed whole-page pixels,
the primary numeric axis, live TM schema rows 756--758 and exact accounting
equations.  Six bounded-report absences remain explicit; nearby interest-rate,
interbank and deposit currency pairs are negative controls rather than matches.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    _authority_snapshot,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "Annual2025LoanCurrency8BankError",
    "build_live_annual_2025_loan_currency_8bank_codex_verified_mapping_v1",
    "validate_annual_2025_loan_currency_8bank_codex_verified_mapping_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_LOAN_CURRENCY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_LOAN_CURRENCY_8BANK_CODEX_PIXEL_REVIEW_V1"
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0116-annual-2025-loan-currency-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0116-annual-2025-loan-currency-8bank-codex-verified-mapping-v1.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_SCAN_ID = "lcfdsv1:scan:d54085cef9458925505b5ecc8570c3d2bbbcff39209ad7eaa2bc3169c4942209"
EXPECTED_REVIEW_SHA256 = "0aa00f47c7df19d0c1ea147105d89c7f18a4589caf00f157bff00d101ee2c656"
EXPECTED_DOCUMENT_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")
_MAPPED_BANKS = ("ACB", "HDB")
_SCHEMA_ROWS = {
    756: ("Phân tích theo loại hình tiền tệ", 716),
    757: ("+ Cho vay bằng đồng Việt Nam", 756),
    758: ("+ Cho vay bằng ngoại tệ và vàng", 756),
}
_EXPECTED_SCHEMA_SNAPSHOT = {
    "rows": [
        {
            "canonical_name": "Phân tích theo loại hình tiền tệ",
            "display_order": 209,
            "parent_id": 716,
            "report_norm_id": 756,
        },
        {
            "canonical_name": "+ Cho vay bằng đồng Việt Nam",
            "display_order": 210,
            "parent_id": 756,
            "report_norm_id": 757,
        },
        {
            "canonical_name": "+ Cho vay bằng ngoại tệ và vàng",
            "display_order": 211,
            "parent_id": 756,
            "report_norm_id": 758,
        },
    ]
}
_CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "SHARED_LOAN_CURRENCY_GRAPH_WHOLE_PDF_UNIQUENESS_AND_NEGATIVE_CONTROLS_PLUS_"
    "INDEPENDENT_VISIBLE_PIXEL_PRIMARY_NUMERIC_AXIS_LIVE_TM_SCHEMA_AND_EXACT_"
    "ACCOUNTING_ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "bounded_report_absence_authority": True,
    "broad_corpus_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "fresh_vietocr_used_for_semantic_anchors": True,
    "independent_visible_pixels_and_primary_numeric_axis_used_for_numbers": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "text_similarity_alone_used_for_mapping": False,
}
_ABSENCE_LOCATORS = {
    "MBB": ((51, 10), (52, 96), (53, 10)),
    "VPB": ((45, 5), (47, 7), (48, 5)),
    "VCB": ((39, 46), (40, 54), (41, 8)),
    "CTG": ((43, 5), (44, 25), (45, 5)),
    "BID": ((41, 99), (42, 103), (43, 4)),
    "VIB": ((37, 43), (39, 7), (39, 64)),
}
_NEGATIVE_CONTROLS = {
    "MBB": ((51, 37), (51, 42), (51, 45), "CUSTOMER_LOAN_INTEREST_RATE_TABLE"),
    "VPB": ((46, 8), (46, 15), (46, 18), "CUSTOMER_LOAN_INTEREST_RATE_TABLE"),
    "VCB": ((36, 38), (36, 59), (36, 62), "INTERBANK_LOAN_CURRENCY_TABLE"),
    "VIB": ((37, 61), (37, 64), (37, 67), "CUSTOMER_LOAN_INTEREST_RATE_TABLE"),
}


class Annual2025LoanCurrency8BankError(ValueError):
    """The fixed annual currency review, graph, schema or result drifted."""


def _error(message: str) -> Annual2025LoanCurrency8BankError:
    return Annual2025LoanCurrency8BankError(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _strict_json(payload: bytes, label: str) -> Any:
    def reject_constant(value: str) -> None:
        raise _error(f"{label} contains non-finite JSON: {value}")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise _error(f"{label} contains duplicate key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(
            payload,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _error(f"{label} is not strict UTF-8 JSON") from error


def _fixed_bytes(path: Path, expected_sha256: str) -> bytes:
    absolute = path if path.is_absolute() else PROJECT_ROOT / path
    before = absolute.stat()
    payload = absolute.read_bytes()
    after = absolute.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise _error(f"fixed artifact changed while reading: {path}")
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"fixed artifact SHA-256 drifted: {path}")
    return payload


def _document(value: Mapping[str, Any], bank: str) -> dict[str, Any]:
    documents = value.get("documents")
    if type(documents) is not list:
        raise _error("document collection drifted")
    matches = [item for item in documents if type(item) is dict and item.get("bank_code") == bank]
    if len(matches) != 1:
        raise _error(f"expected one {bank} document")
    return matches[0]


def _page(document: Mapping[str, Any], physical_page: int) -> dict[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error("document page collection drifted")
    matches = [
        item for item in pages if type(item) is dict and item.get("physical_page") == physical_page
    ]
    if len(matches) != 1:
        raise _error(f"expected one physical page {physical_page}")
    return matches[0]


def _event(
    semantic_index: Mapping[str, Any], bank: str, locator: tuple[int, int]
) -> dict[str, Any]:
    physical_page, source_line_index = locator
    page = _page(_document(semantic_index, bank), physical_page)
    lines = page.get("lines")
    if type(lines) is not list or not 0 <= source_line_index < len(lines):
        raise _error(f"{bank} review locator drifted")
    line = lines[source_line_index]
    if type(line) is not dict or line.get("source_line_index") != source_line_index:
        raise _error(f"{bank} review line axis drifted")
    crop_ref = line.get("crop_ref")
    if type(crop_ref) is not dict:
        raise _error(f"{bank} review crop ref drifted")
    return {
        "bbox": canonical_clone_v1(line["source_bbox_raw_pixels"]),
        "crop_ref": canonical_clone_v1(crop_ref),
        "physical_page": physical_page,
        "source_line_index": source_line_index,
        "vietocr_text": line["vietocr_text"],
    }


def _render_ref(manifest: Mapping[str, Any], bank: str, physical_page: int) -> dict[str, Any]:
    page = _page(_document(manifest, bank), physical_page)
    binding = page.get("render_binding")
    if type(binding) is not dict:
        raise _error(f"{bank} page render binding drifted")
    return canonical_clone_v1(binding)


def _review_row(
    semantic_index: Mapping[str, Any],
    bank: str,
    physical_page: int,
    role: str,
    label_index: int,
    value_indices: Sequence[int],
    pixel_label: str,
    pixel_values: Sequence[str],
) -> dict[str, Any]:
    if len(value_indices) != len(pixel_values):
        raise _error("review row value denominator drifted")
    events = [_event(semantic_index, bank, (physical_page, index)) for index in value_indices]
    return {
        "label_event": _event(semantic_index, bank, (physical_page, label_index)),
        "pixel_label": pixel_label,
        "pixel_values": list(pixel_values),
        "role": role,
        "transformer_values": [event["vietocr_text"] for event in events],
        "value_events": events,
    }


def _review_blueprint(
    semantic_index: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    acb_rows = [
        _review_row(
            semantic_index,
            "ACB",
            51,
            "VND_LOANS",
            12,
            (13, 14),
            "Cho vay bằng Đồng Việt Nam",
            ("668.933.408", "566.297.638"),
        ),
        _review_row(
            semantic_index,
            "ACB",
            51,
            "FOREIGN_CURRENCY_AND_GOLD_LOANS",
            15,
            (16, 17),
            "Cho vay bằng ngoại tệ",
            ("17.843.944", "14.388.610"),
        ),
    ]
    hdb_rows = [
        _review_row(
            semantic_index,
            "HDB",
            37,
            "VND_LOANS",
            76,
            (77, 78),
            "Bằng VND",
            ("527.584.876", "418.599.063"),
        ),
        _review_row(
            semantic_index,
            "HDB",
            37,
            "FOREIGN_CURRENCY_AND_GOLD_LOANS",
            79,
            (80, 81),
            "Bằng ngoại tệ",
            ("18.785.903", "12.707.006"),
        ),
    ]
    mapped = {
        "ACB": {
            "bank_code": "ACB",
            "branch_event": _event(semantic_index, "ACB", (51, 7)),
            "branch_pixel_transcription": "Theo loại tiền tệ",
            "owner_event": _event(semantic_index, "ACB", (51, 5)),
            "owner_pixel_transcription": "CHO VAY KHÁCH HÀNG (tiếp theo)",
            "period_pixel_transcriptions": ["31.12.2025", "31.12.2024"],
            "physical_page": 51,
            "render_ref": _render_ref(manifest, "ACB", 51),
            "rows": acb_rows,
            "status": "PIXEL_REVIEW_COMPLETE",
            "total_pixel_values": ["686.777.352", "580.686.248"],
            "total_value_events": [
                _event(semantic_index, "ACB", (51, 18)),
                _event(semantic_index, "ACB", (51, 19)),
            ],
            "unit_pixel_transcriptions": ["Triệu VND", "Triệu VND"],
        },
        "HDB": {
            "additional_source_population": {
                "label_events": [
                    _event(semantic_index, "HDB", (37, 82)),
                    _event(semantic_index, "HDB", (37, 84)),
                ],
                "pixel_label": (
                    "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày "
                    "01 tháng 7 năm 2024"
                ),
                "pixel_values": ["-", "11.178.772"],
                "rows": [
                    {
                        **_review_row(
                            semantic_index,
                            "HDB",
                            37,
                            "ADDITIONAL_VND",
                            85,
                            (86,),
                            "Bằng VND",
                            ("4.915.109",),
                        ),
                        "current_visible_dash_provider_omitted": True,
                    },
                    {
                        **_review_row(
                            semantic_index,
                            "HDB",
                            37,
                            "ADDITIONAL_FOREIGN",
                            87,
                            (88,),
                            "Bằng ngoại tệ",
                            ("6.263.663",),
                        ),
                        "current_visible_dash_provider_omitted": True,
                    },
                ],
                "value_events": [_event(semantic_index, "HDB", (37, 83))],
            },
            "bank_code": "HDB",
            "branch_event": _event(semantic_index, "HDB", (37, 68)),
            "branch_pixel_transcription": "Phân tích dư nợ cho vay theo loại tiền tệ",
            "grand_total_pixel_values": ["546.370.779", "442.484.841"],
            "grand_total_value_events": [
                _event(semantic_index, "HDB", (37, 89)),
                _event(semantic_index, "HDB", (37, 90)),
            ],
            "owner_event": _event(semantic_index, "HDB", (37, 73)),
            "owner_pixel_transcription": "Cho vay khách hàng",
            "period_pixel_transcriptions": ["Số cuối năm", "Số đầu năm"],
            "physical_page": 37,
            "render_ref": _render_ref(manifest, "HDB", 37),
            "rows": hdb_rows,
            "status": "PIXEL_REVIEW_COMPLETE",
            "total_pixel_values": ["546.370.779", "431.306.069"],
            "total_value_events": [
                _event(semantic_index, "HDB", (37, 74)),
                _event(semantic_index, "HDB", (37, 75)),
            ],
            "unit_pixel_transcriptions": ["Triệu VND", "Triệu VND"],
        },
    }
    banks: list[dict[str, Any]] = []
    for bank in EXPECTED_DOCUMENT_ORDER:
        if bank in mapped:
            banks.append(mapped[bank])
            continue
        start, last, next_boundary = _ABSENCE_LOCATORS[bank]
        negative = None
        if bank in _NEGATIVE_CONTROLS:
            context, vnd, foreign, family = _NEGATIVE_CONTROLS[bank]
            negative = {
                "context_event": _event(semantic_index, bank, context),
                "foreign_event": _event(semantic_index, bank, foreign),
                "negative_family": family,
                "vnd_event": _event(semantic_index, bank, vnd),
            }
        banks.append(
            {
                "bank_code": bank,
                "first_loan_note_event": _event(semantic_index, bank, start),
                "last_loan_subfamily_event": _event(semantic_index, bank, last),
                "negative_control": negative,
                "next_family_boundary_event": _event(semantic_index, bank, next_boundary),
                "status": "CONFIRMED_NOT_PRESENT_IN_BOUND_REPORT",
            }
        )
    material = {
        "banks": banks,
        "claim_boundary": _CLAIM_BOUNDARY,
        "format_version": REVIEW_FORMAT,
        "review_checks": {
            "complete_pdf_scanned": True,
            "mapped_page_pixels_opened": True,
            "negative_currency_pairs_assigned_to_their_actual_family": True,
            "period_unit_owner_children_totals_and_accounting_checked": True,
            "six_loan_note_first_last_and_next_family_boundaries_checked": True,
        },
        "reviewer": {"kind": "CODEX_INDEPENDENT_SOURCE_REVIEW"},
    }
    return {
        **material,
        "review_id": "e0116:pixel-review:" + canonical_json_sha256_v1(material),
    }


def _validate_review(
    value: Any, semantic_index: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    expected = _review_blueprint(semantic_index, manifest)
    if not same_typed_json_v1(value, expected):
        raise _error("annual currency pixel review differs from exact reviewed sources")
    return canonical_clone_v1(expected)


def _schema_snapshot(schema_by_id: Mapping[int, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for report_norm_id, (canonical_name, parent_id) in _SCHEMA_ROWS.items():
        item = schema_by_id.get(report_norm_id)
        if (
            item is None
            or item.canonical_name != canonical_name
            or item.parent_id != parent_id
            or item.statement_type != "TM"
            or "CONSOLIDATED" not in item.scope
        ):
            raise _error(f"live TM currency row {report_norm_id} drifted")
        rows.append(
            {
                "canonical_name": canonical_name,
                "display_order": item.display_order,
                "parent_id": parent_id,
                "report_norm_id": report_norm_id,
            }
        )
    if [row["display_order"] for row in rows] != sorted(row["display_order"] for row in rows):
        raise _error("live TM currency display order drifted")
    return {"rows": rows}


def _money(value: str) -> int:
    token = value.strip().replace(" ", "")
    if token in {"-", "–", "—"}:
        return 0
    negative = token.startswith("(") and token.endswith(")")
    if negative:
        token = token[1:-1]
    compact = token.replace(".", "").replace(",", "")
    if not compact.isdigit():
        raise _error(f"reviewed money is not exact: {value}")
    parsed = int(compact)
    return -parsed if negative else parsed


def _compatible_text(left: str, right: str) -> bool:
    return normalize_vietnamese_anchor_v1(left) == normalize_vietnamese_anchor_v1(right)


def _scan_trial(scan: Mapping[str, Any], bank: str) -> dict[str, Any]:
    matches = [
        trial
        for trial in scan["trials"]
        if type(trial) is dict and trial.get("document_provenance") == bank
    ]
    if len(matches) != 1:
        raise _error(f"annual scan must contain one {bank} trial")
    return matches[0]


def _review_bank(review: Mapping[str, Any], bank: str) -> dict[str, Any]:
    matches = [item for item in review["banks"] if item.get("bank_code") == bank]
    if len(matches) != 1:
        raise _error(f"annual review must contain one {bank} record")
    return matches[0]


def _mapped_trial(
    bank: str,
    scan_trial: Mapping[str, Any],
    review: Mapping[str, Any],
) -> dict[str, Any]:
    matcher = scan_trial["matcher_result"]
    if matcher["status"] != "ACCEPTED_UNIQUE_VARIANT_GRAPH" or len(matcher["regions"]) != 1:
        raise _error(f"{bank} must have exactly one annual currency graph")
    region = matcher["regions"][0]
    if (
        region["owner_context"]["page_sequence"] != review["physical_page"]
        or not _compatible_text(
            region["owner_context"]["surface"], review["owner_pixel_transcription"]
        )
        or region["branch_match"] is None
        or not _compatible_text(
            region["branch_match"]["surface"], review["branch_pixel_transcription"]
        )
    ):
        raise _error(f"{bank} graph owner or branch differs from reviewed pixels")
    events = {event["role"]: event for event in region["events"]}
    mapped_items: list[dict[str, Any]] = []
    for row in review["rows"]:
        event = events.get(row["role"])
        if (
            event is None
            or not _compatible_text(event["surface"], row["pixel_label"])
            or [item["vietocr_text"] for item in event["value_proposals"]]
            != row["transformer_values"]
        ):
            raise _error(f"{bank} reviewed currency row differs from graph")
        report_norm_id = 757 if row["role"] == "VND_LOANS" else 758
        mapped_items.append(
            {
                "canonical_name": _SCHEMA_ROWS[report_norm_id][0],
                "report_norm_id": report_norm_id,
                "role": row["role"],
                "source_label": row["pixel_label"],
                "source_values": canonical_clone_v1(row["pixel_values"]),
                "status": "VERIFIED_BY_CODEX",
            }
        )
    for axis in range(2):
        if sum(_money(item["source_values"][axis]) for item in mapped_items) != _money(
            review["total_pixel_values"][axis]
        ):
            raise _error(f"{bank} currency core total does not close")
    equations = 2
    additional = review.get("additional_source_population")
    grand_total = review.get("grand_total_pixel_values")
    if additional is not None:
        additional_rows = additional["rows"]
        for axis in range(2):
            components = [
                0 if axis == 0 else _money(row["pixel_values"][0]) for row in additional_rows
            ]
            if sum(components) != _money(additional["pixel_values"][axis]):
                raise _error("HDB additional currency population does not close")
            if _money(review["total_pixel_values"][axis]) + _money(
                additional["pixel_values"][axis]
            ) != _money(grand_total[axis]):
                raise _error("HDB currency grand total does not close")
        equations += 4
    disagreements: list[list[str]] = []
    for row in review["rows"]:
        for axis, (transformer, pixel) in enumerate(
            zip(row["transformer_values"], row["pixel_values"], strict=True)
        ):
            if transformer != pixel:
                disagreements.append(
                    [row["role"], str(axis), transformer, pixel, "PIXEL_NUMERIC_RECONCILIATION"]
                )
    if grand_total is not None:
        for axis, (event, pixel) in enumerate(
            zip(review["grand_total_value_events"], grand_total, strict=True)
        ):
            if event["vietocr_text"] != pixel:
                disagreements.append(
                    [
                        "GRAND_TOTAL",
                        str(axis),
                        event["vietocr_text"],
                        pixel,
                        "PIXEL_NUMERIC_RECONCILIATION",
                    ]
                )
    return {
        "accounting_equation_count": equations,
        "additional_source_population": canonical_clone_v1(additional),
        "bank_code": bank,
        "branch_pixel_transcription": review["branch_pixel_transcription"],
        "graph_id": region["region_id"],
        "mapped_items": mapped_items,
        "period_pixel_transcriptions": canonical_clone_v1(review["period_pixel_transcriptions"]),
        "physical_page": review["physical_page"],
        "render_sha256": review["render_ref"]["sha256"],
        "source_only_total": {
            "core_total": canonical_clone_v1(review["total_pixel_values"]),
            "grand_total": canonical_clone_v1(grand_total or []),
            "status": "VERIFIED_SOURCE_ONLY_NO_REPORT_NORM_ID",
        },
        "status": "VERIFIED_BY_CODEX",
        "transformer_disagreements": disagreements,
        "unit_pixel_transcriptions": canonical_clone_v1(review["unit_pixel_transcriptions"]),
    }


def _absence_trial(
    bank: str, scan_trial: Mapping[str, Any], review: Mapping[str, Any]
) -> dict[str, Any]:
    matcher = scan_trial["matcher_result"]
    if matcher["status"] != "UNRESOLVED_NO_COMPLETE_REGION" or matcher["regions"] != []:
        raise _error(f"{bank} bounded-report absence conflicts with annual scan")
    return {
        "bank_code": bank,
        "first_loan_note_event": canonical_clone_v1(review["first_loan_note_event"]),
        "last_loan_subfamily_event": canonical_clone_v1(review["last_loan_subfamily_event"]),
        "matcher_result_id": matcher["result_id"],
        "near_region_count": matcher["metrics"]["near_region_count"],
        "negative_control": canonical_clone_v1(review["negative_control"]),
        "next_family_boundary_event": canonical_clone_v1(review["next_family_boundary_event"]),
        "report_norm_ids_not_observed": [756, 757, 758],
        "status": "VERIFIED_NOT_OBSERVED_IN_BOUND_REPORT",
    }


def _metrics(trials: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    mapped = [trial for trial in trials if trial["status"] == "VERIFIED_BY_CODEX"]
    return {
        "accounting_equation_count": sum(trial["accounting_equation_count"] for trial in mapped),
        "bounded_report_absence_count": sum(
            trial["status"] == "VERIFIED_NOT_OBSERVED_IN_BOUND_REPORT" for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_mapping_region_count": len(mapped),
        "mapped_item_verified_by_codex_count": sum(len(trial["mapped_items"]) for trial in mapped),
        "mapped_money_value_cell_count": sum(
            len(item["source_values"]) for trial in mapped for item in trial["mapped_items"]
        ),
        "source_only_additional_population_count": sum(
            trial["additional_source_population"] is not None for trial in mapped
        ),
        "transformer_numeric_disagreement_count": sum(
            len(trial["transformer_disagreements"]) for trial in mapped
        ),
        "unresolved_mapping_count": 0,
    }


def _validate_result(value: Any) -> dict[str, Any]:
    fields = {
        "authority",
        "claim_boundary",
        "format_version",
        "input_refs",
        "metrics",
        "result_id",
        "schema_snapshot",
        "state",
        "trials",
    }
    if type(value) is not dict or set(value) != fields:
        raise _error("annual currency result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != _CLAIM_BOUNDARY
        or value["state"] != "ANNUAL_2025_LOAN_CURRENCY_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or [trial.get("bank_code") for trial in value["trials"]] != list(EXPECTED_DOCUMENT_ORDER)
        or not same_typed_json_v1(value["schema_snapshot"], _EXPECTED_SCHEMA_SNAPSHOT)
        or not same_typed_json_v1(value["metrics"], _metrics(value["trials"]))
    ):
        raise _error("annual currency result identity, order or metrics drifted")
    mapped_fields = {
        "accounting_equation_count",
        "additional_source_population",
        "bank_code",
        "branch_pixel_transcription",
        "graph_id",
        "mapped_items",
        "period_pixel_transcriptions",
        "physical_page",
        "render_sha256",
        "source_only_total",
        "status",
        "transformer_disagreements",
        "unit_pixel_transcriptions",
    }
    absence_fields = {
        "bank_code",
        "first_loan_note_event",
        "last_loan_subfamily_event",
        "matcher_result_id",
        "near_region_count",
        "negative_control",
        "next_family_boundary_event",
        "report_norm_ids_not_observed",
        "status",
    }
    for trial in value["trials"]:
        bank = trial["bank_code"]
        if bank in _MAPPED_BANKS:
            if (
                set(trial) != mapped_fields
                or trial["status"] != "VERIFIED_BY_CODEX"
                or trial["physical_page"] != {"ACB": 51, "HDB": 37}[bank]
                or trial["accounting_equation_count"] != {"ACB": 2, "HDB": 6}[bank]
                or type(trial["mapped_items"]) is not list
                or [item.get("report_norm_id") for item in trial["mapped_items"]] != [757, 758]
                or [item.get("role") for item in trial["mapped_items"]]
                != ["VND_LOANS", "FOREIGN_CURRENCY_AND_GOLD_LOANS"]
            ):
                raise _error(f"{bank} mapped trial shape or schema rows drifted")
            for item in trial["mapped_items"]:
                expected_name = _SCHEMA_ROWS[item["report_norm_id"]][0]
                if (
                    item.get("canonical_name") != expected_name
                    or item.get("status") != "VERIFIED_BY_CODEX"
                    or type(item.get("source_values")) is not list
                    or len(item["source_values"]) != 2
                    or any(type(raw) is not str for raw in item["source_values"])
                ):
                    raise _error(f"{bank} mapped item shape drifted")
        elif (
            set(trial) != absence_fields
            or trial["status"] != "VERIFIED_NOT_OBSERVED_IN_BOUND_REPORT"
            or not same_typed_json_v1(trial["report_norm_ids_not_observed"], [756, 757, 758])
        ):
            raise _error(f"{bank} bounded-report absence shape drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id")
    if result_id != "annual2025lcbcv1:result:" + canonical_json_sha256_v1(material):
        raise _error("annual currency result identity drifted")
    return canonical_clone_v1(value)


def build_annual_2025_loan_currency_8bank_codex_verified_mapping_v1(
    semantic_index: Mapping[str, Any],
    manifest: Mapping[str, Any],
    scan: Mapping[str, Any],
    review: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    review_sha256: str,
) -> dict[str, Any]:
    if (
        scan.get("scan_id") != EXPECTED_SCAN_ID
        or scan.get("input_semantic_axis_sha256") != EXPECTED_AXIS_SHA256
    ):
        raise _error("annual currency scan identity drifted")
    checked_review = _validate_review(review, semantic_index, manifest)
    if review_sha256 != EXPECTED_REVIEW_SHA256:
        raise _error("annual currency review SHA-256 drifted")
    schema = _schema_snapshot(schema_by_id)
    trials = []
    for bank in EXPECTED_DOCUMENT_ORDER:
        scan_trial = _scan_trial(scan, bank)
        bank_review = _review_bank(checked_review, bank)
        trials.append(
            _mapped_trial(bank, scan_trial, bank_review)
            if bank in _MAPPED_BANKS
            else _absence_trial(bank, scan_trial, bank_review)
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": _CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest_sha256": EXPECTED_CROP_MANIFEST_SHA256,
            "pixel_review_path": REVIEW_PATH.as_posix(),
            "pixel_review_sha256": review_sha256,
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": _metrics(trials),
        "schema_snapshot": schema,
        "state": "ANNUAL_2025_LOAN_CURRENCY_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {
            **material,
            "result_id": "annual2025lcbcv1:result:" + canonical_json_sha256_v1(material),
        }
    )


def _live_inputs() -> tuple[Any, Any, Any, Any, Mapping[int, Any]]:
    semantic = _strict_json(
        _fixed_bytes(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256), "annual semantic index"
    )
    manifest = _strict_json(
        _fixed_bytes(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256), "annual crop manifest"
    )
    scanner = _load_module(
        "annual_2025_loan_currency_scan_for_verified_mapping",
        "scripts/experiments/scan_loan_currency_full_document_vietocr_v1.py",
    )
    scan = scanner.build_loan_currency_full_document_scan_v1(
        semantic, enable_extended_annual_variants=True
    )
    review = _strict_json(
        _fixed_bytes(REVIEW_PATH, EXPECTED_REVIEW_SHA256), "annual currency pixel review"
    )
    _authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return semantic, manifest, scan, review, schema_by_id


def build_live_annual_2025_loan_currency_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Rebuild the fixed annual result from every live bounded authority."""

    semantic, manifest, scan, review, schema_by_id = _live_inputs()
    return build_annual_2025_loan_currency_8bank_codex_verified_mapping_v1(
        semantic,
        manifest,
        scan,
        review,
        schema_by_id,
        review_sha256=EXPECTED_REVIEW_SHA256,
    )


def validate_annual_2025_loan_currency_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild a persisted annual result from every fixed input."""

    persisted = _validate_result(value)
    rebuilt = build_live_annual_2025_loan_currency_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("annual currency verified result does not replay exactly")
    return rebuilt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    args = parser.parse_args()
    if args.write_review:
        semantic = _strict_json(
            _fixed_bytes(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256), "annual semantic index"
        )
        manifest = _strict_json(
            _fixed_bytes(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256),
            "annual crop manifest",
        )
        payload = canonical_json_bytes_v1(_review_blueprint(semantic, manifest))
        path = PROJECT_ROOT / REVIEW_PATH
        if path.exists() and path.read_bytes() != payload:
            raise _error("refusing to overwrite a different annual currency review")
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        print(hashlib.sha256(payload).hexdigest())
        return 0
    if args.validate is not None:
        path = args.validate if args.validate.is_absolute() else PROJECT_ROOT / args.validate
        validate_annual_2025_loan_currency_8bank_codex_verified_mapping_replay_v1(
            _strict_json(path.read_bytes(), "persisted annual currency result")
        )
        return 0
    result = build_live_annual_2025_loan_currency_8bank_codex_verified_mapping_v1()
    output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    payload = canonical_json_bytes_v1(result)
    if output.exists() and output.read_bytes() != payload:
        raise _error("refusing to overwrite a different annual currency result")
    if not output.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
