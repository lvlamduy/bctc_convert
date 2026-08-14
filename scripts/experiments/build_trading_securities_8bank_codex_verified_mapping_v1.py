"""Verify and map the eight-bank trading-securities note family.

The complete-PDF detector remains bank blind.  This bounded post-scan review
binds each unique region to visible page/crop evidence, preserves PDF row order
and cluster boundaries, selects current-period monetary columns, verifies the
accounting equations, and maps only exact live TM-schema rows.  VIB's distinct
investment-securities table is retained as an unresolved negative control.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
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
    "TradingSecurities8BankCodexVerifiedMappingV1Error",
    "build_live_trading_securities_8bank_codex_verified_mapping_v1",
    "build_trading_securities_8bank_codex_verified_mapping_v1",
    "validate_trading_securities_8bank_codex_verified_mapping_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "TRADING_SECURITIES_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "TRADING_SECURITIES_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_GENERIC_TRADING_SECURITIES_"
    "FIRST_LAST_CLUSTER_BOUNDARY_LAYOUT_PERIOD_UNIT_STRUCTURE_PLUS_INDEPENDENT_"
    "VISIBLE_PIXEL_UPSTREAM_NUMERIC_CHALLENGER_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_"
    "NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0059-trading-securities-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path(
    "docs/experiments/E-0059-trading-securities-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/verified-index/semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/development/loan-maturity-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "f84fd9ca56fe06af230e011ecad85b0a576e27e1eca32ee141e654a6776b78b4"
EXPECTED_CROP_MANIFEST_SHA256 = "a9f80cf9104af1177ba43d8a85de00b28c735223a91b663a5a79401bb038d94e"
EXPECTED_AXIS_SHA256 = "e99873cd16a7234702d0ee6e5fa9eb37637a1a75621228381e3dbcd7c5cfdcca"
EXPECTED_SCAN_ID = "tsfdsv1:scan:e3c26b48abdf6f792c153c7953fe6772611dcfaeaa17d7e286998b7f76873243"

_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION_ENUMERATION",
    "TRADING_NOT_INVESTMENT_OR_PROVISION_MOVEMENT_SUBFAMILY",
    "FIRST_OWNER_AND_LAST_NET_OR_PROVISION_ITEM_IN_PDF_ORDER",
    "HORIZONTAL_VERTICAL_OR_MIXED_LAYOUT",
    "PARENT_PRECEDES_CHILD",
    "ISSUER_OR_LISTED_UNLISTED_VARIANT",
    "CURRENT_PERIOD_MONETARY_AXIS_ONLY",
    "PERIOD_AND_UNIT_AXIS_VISIBLE",
    "PERCENTAGE_OR_AUXILIARY_COLUMNS_EXCLUDED_FROM_MONEY",
    "VISIBLE_PIXEL_DIGITS_AND_SIGN",
    "UPSTREAM_PPOCRV6_OR_NATIVE_NUMERIC_CHALLENGER",
    "PARENT_CHILD_GROSS_PROVISION_NET_ACCOUNTING",
    "LIVE_TM_SCHEMA_PARENT_AND_DISPLAY_ORDER",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "comparison_period_used_as_mapping_authority": False,
    "current_reporting_period_only_mapped": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "investment_securities_subfamily_mapped_as_trading": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": ("VISIBLE_PDF_PIXELS_WITH_UPSTREAM_NUMERIC_CHALLENGER_AND_ACCOUNTING"),
    "old_ocr_used_as_semantic_anchor": False,
    "source_order_and_cluster_boundaries_required": True,
    "unlabeled_total_requires_topology_and_accounting": True,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "comparison_period_used_as_mapping_authority": False,
    "current_reporting_period_only_mapped": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_trading_securities_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_order_and_cluster_boundaries_preserved": True,
    "text_similarity_alone_used_for_mapping": False,
    "unlabeled_total_requires_topology_and_exact_equation": True,
    "upstream_ppocrv6_or_native_text_used_only_as_numeric_challenger": True,
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
_MONEY = re.compile(r"^(?:[0-9][0-9.,]*|\([0-9][0-9.,]*\)|[-–—])$")


class TradingSecurities8BankCodexVerifiedMappingV1Error(ValueError):
    """The structure, pixel ledger, accounting, or live schema drifted."""


def _error(message: str) -> TradingSecurities8BankCodexVerifiedMappingV1Error:
    return TradingSecurities8BankCodexVerifiedMappingV1Error(message)


def _sha256(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise _error(f"{label} SHA-256 drifted")
    return value


def _relative_parts(path: Path) -> tuple[str, ...]:
    if not isinstance(path, Path) or path.is_absolute() or not path.parts:
        raise _error(f"fixed path is not one safe relative path: {path}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise _error(f"fixed path escapes the project root: {path}")
    return tuple(path.parts)


def _stable_bytes(path: Path) -> bytes:
    parts = _relative_parts(path)
    directory_fd = os.open(PROJECT_ROOT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in parts[:-1]:
            child_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = child_fd
        descriptor = os.open(
            parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd
        )
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise _error(f"fixed artifact is not a regular file: {path}")
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1024 * 1024):
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        before.st_mtime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        after.st_mtime_ns,
    )
    payload = b"".join(chunks)
    if before_identity != after_identity or len(payload) != before.st_size:
        raise _error(f"fixed artifact changed or was incomplete while reading: {path}")
    return payload


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error(f"{label} is not strict JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} root is not one object")
    return value


def _fixed_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], bytes]:
    payload = _stable_bytes(path)
    if expected_sha256 is not None and hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"fixed artifact content identity drifted: {path}")
    return _strict_json(payload, path.as_posix()), payload


def _scanner() -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments/scan_trading_securities_full_document_vietocr_v1.py"
    spec = importlib.util.spec_from_file_location("trading_securities_scan_for_e0059", path)
    if spec is None or spec.loader is None:
        raise _error("cannot load trading-securities full-document scanner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _value(line_index: int, transcription: str) -> dict[str, Any]:
    return {"line_index": line_index, "pixel_transcription": transcription}


def _mapping(
    report_norm_id: int,
    role: str,
    page: int,
    label: str | None,
    label_lines: Sequence[int],
    value: Mapping[str, Any],
    *,
    topology: str = "DIRECT_VISIBLE_LABELED_ROW",
) -> dict[str, Any]:
    return {
        "label_line_indices": list(label_lines),
        "label_pixel_transcription": label,
        "physical_page": page,
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "value": canonical_clone_v1(value),
    }


def _equation(
    name: str,
    page: int,
    components: Sequence[Mapping[str, Any]],
    total: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "component_values": canonical_clone_v1(components),
        "equation": "SIGNED_SUM_COMPONENTS_EQUALS_VISIBLE_TOTAL",
        "name": name,
        "physical_page": page,
        "visible_total": canonical_clone_v1(total),
    }


def _doc(
    code: str,
    page: int | None,
    layout: str | None,
    period: str,
    mappings: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    *,
    disposition: str = "UNIQUE_COMPLETE_REGION_VISIBLE_PIXEL_REVIEWED",
) -> dict[str, Any]:
    return {
        "comparison_period_excluded": "31/12/2025" if page is not None else None,
        "disposition": disposition,
        "document_provenance": code,
        "equations": canonical_clone_v1(equations),
        "layout_variant": layout,
        "mappings": canonical_clone_v1(mappings),
        "page_sequence": page,
        "selected_monetary_axis": (
            "CURRENT_PERIOD_MONETARY_VALUES_ONLY_PERCENTAGE_OR_AUXILIARY_COLUMNS_EXCLUDED"
            if page is not None
            else None
        ),
        "source_period": period,
        "whole_document_family_absence_claim": False,
    }


def _review_documents() -> list[dict[str, Any]]:
    return [
        _doc(
            "ACB",
            16,
            "ISSUER_CLASSIFICATION_ROWS_X_PERIOD_COLUMNS",
            "2026-06-30",
            [
                _mapping(594, "DEBT", 16, "Chứng khoán nợ", [47], _value(48, "2.796.807")),
                _mapping(
                    595,
                    "DEBT_GOVERNMENT",
                    16,
                    "Chứng khoán Chính phủ",
                    [50],
                    _value(51, "1.474.269"),
                ),
                _mapping(
                    596,
                    "DEBT_TCTD",
                    16,
                    "Chứng khoán do các TCTD khác trong nước phát hành",
                    [53],
                    _value(54, "1.052.230"),
                ),
                _mapping(
                    597,
                    "DEBT_DOMESTIC_TCKT",
                    16,
                    "Chứng khoán do các tổ chức kinh tế trong nước phát hành",
                    [56, 57],
                    _value(58, "270.308"),
                ),
                _mapping(600, "EQUITY", 16, "Chứng khoán vốn", [60], _value(61, "2.935.780")),
                _mapping(
                    602,
                    "EQUITY_TCTD",
                    16,
                    "Chứng khoán vốn do các TCTD khác trong nước phát hành",
                    [63, 64],
                    _value(65, "1.408.698"),
                ),
                _mapping(
                    603,
                    "EQUITY_DOMESTIC_TCKT",
                    16,
                    "Chứng khoán vốn do các TCKT trong nước phát hành",
                    [67],
                    _value(68, "1.527.082"),
                ),
                _mapping(
                    606,
                    "OTHER_TRADING",
                    16,
                    "Chứng khoán kinh doanh khác",
                    [70],
                    _value(71, "201.368"),
                ),
                _mapping(
                    612,
                    "PROVISION",
                    16,
                    "Dự phòng rủi ro chứng khoán kinh doanh",
                    [72],
                    _value(73, "(171.845)"),
                ),
            ],
            [
                _equation(
                    "DEBT_CHILDREN_TO_DEBT",
                    16,
                    [_value(51, "1.474.269"), _value(54, "1.052.230"), _value(58, "270.308")],
                    _value(48, "2.796.807"),
                ),
                _equation(
                    "EQUITY_CHILDREN_TO_EQUITY",
                    16,
                    [_value(65, "1.408.698"), _value(68, "1.527.082")],
                    _value(61, "2.935.780"),
                ),
                _equation(
                    "DEBT_EQUITY_OTHER_PROVISION_TO_NET",
                    16,
                    [
                        _value(48, "2.796.807"),
                        _value(61, "2.935.780"),
                        _value(71, "201.368"),
                        _value(73, "(171.845)"),
                    ],
                    _value(75, "5.762.110"),
                ),
            ],
        ),
        _doc(
            "MBB",
            31,
            "LISTED_UNLISTED_CLASSIFICATION_ROWS_X_PERIOD_COLUMNS",
            "2026-06-30",
            [
                _mapping(618, "DEBT_LISTED", 31, "Đã niêm yết", [8], _value(9, "1.363.309")),
                _mapping(619, "DEBT_UNLISTED", 31, "Chưa niêm yết", [11], _value(12, "7.171.301")),
                _mapping(621, "EQUITY_LISTED", 31, "Đã niêm yết", [15], _value(16, "182.924")),
                _mapping(622, "EQUITY_UNLISTED", 31, "Chưa niêm yết", [18], _value(19, "170.995")),
                _mapping(
                    626,
                    "GROSS",
                    31,
                    None,
                    [],
                    _value(21, "8.888.529"),
                    topology="UNLABELED_TOTAL_AFTER_LAST_EQUITY_CHILD_BEFORE_PROVISION",
                ),
                _mapping(
                    627,
                    "PROVISION",
                    31,
                    "Dự phòng giảm giá chứng khoán kinh doanh",
                    [23],
                    _value(24, "(35.170)"),
                ),
            ],
            [
                _equation(
                    "LISTED_UNLISTED_CHILDREN_TO_GROSS",
                    31,
                    [
                        _value(9, "1.363.309"),
                        _value(12, "7.171.301"),
                        _value(16, "182.924"),
                        _value(19, "170.995"),
                    ],
                    _value(21, "8.888.529"),
                ),
                _equation(
                    "GROSS_PROVISION_TO_NET",
                    31,
                    [_value(21, "8.888.529"), _value(24, "(35.170)")],
                    _value(26, "8.853.359"),
                ),
            ],
        ),
        _doc(
            "VPB",
            40,
            "ISSUER_CLASSIFICATION_ROWS_X_PERIOD_COLUMNS",
            "2026-03-31",
            [
                _mapping(
                    596,
                    "DEBT_TCTD",
                    40,
                    "Chứng khoán nợ do các TCTD khác phát hành",
                    [15],
                    _value(16, "2.811.917"),
                ),
                _mapping(
                    597,
                    "DEBT_DOMESTIC_TCKT",
                    40,
                    "Chứng khoán nợ do các TCKT trong nước phát hành",
                    [18],
                    _value(19, "15.139.431"),
                ),
                _mapping(
                    602,
                    "EQUITY_TCTD",
                    40,
                    "Chứng khoán vốn do các TCTD khác phát hành",
                    [22],
                    _value(23, "1.941.189"),
                ),
                _mapping(
                    603,
                    "EQUITY_DOMESTIC_TCKT",
                    40,
                    "Chứng khoán vốn do các TCKT trong nước phát hành",
                    [25],
                    _value(26, "5.514.369"),
                ),
                _mapping(
                    611,
                    "GROSS",
                    40,
                    None,
                    [],
                    _value(28, "25.406.906"),
                    topology="UNLABELED_TOTAL_AFTER_LAST_EQUITY_CHILD_BEFORE_PROVISION",
                ),
                _mapping(
                    612,
                    "PROVISION",
                    40,
                    "Dự phòng rủi ro chứng khoán kinh doanh",
                    [30],
                    _value(31, "(516.155)"),
                ),
                _mapping(
                    614, "PROVISION_GENERAL", 40, "Dự phòng chung", [33], _value(34, "(113.365)")
                ),
                _mapping(
                    613,
                    "PROVISION_PRICE_DECREASE",
                    40,
                    "Dự phòng giảm giá",
                    [36],
                    _value(37, "(402.790)"),
                ),
            ],
            [
                _equation(
                    "ISSUER_CHILDREN_TO_GROSS",
                    40,
                    [
                        _value(16, "2.811.917"),
                        _value(19, "15.139.431"),
                        _value(23, "1.941.189"),
                        _value(26, "5.514.369"),
                    ],
                    _value(28, "25.406.906"),
                ),
                _equation(
                    "PROVISION_DETAILS_TO_PROVISION",
                    40,
                    [_value(34, "(113.365)"), _value(37, "(402.790)")],
                    _value(31, "(516.155)"),
                ),
                _equation(
                    "GROSS_PROVISION_TO_NET",
                    40,
                    [_value(28, "25.406.906"), _value(31, "(516.155)")],
                    _value(39, "24.890.751"),
                ),
            ],
        ),
        _doc(
            "HDB",
            24,
            "ISSUER_CLASSIFICATION_ROWS_X_PERIOD_COLUMNS_WITH_TRAILING_PARENT_TOTALS",
            "2026-06-30",
            [
                _mapping(
                    594,
                    "DEBT",
                    24,
                    "Chứng khoán Nợ",
                    [36],
                    _value(44, "10.761.164"),
                    topology="TRAILING_PARENT_TOTAL_AFTER_LAST_DEBT_CHILD",
                ),
                _mapping(
                    595, "DEBT_GOVERNMENT", 24, "Chứng khoán Chính phủ", [37], _value(38, "12.544")
                ),
                _mapping(
                    596,
                    "DEBT_TCTD",
                    24,
                    "Chứng khoán Nợ do các TCTD khác trong nước phát hành",
                    [40],
                    _value(41, "3.108.925"),
                ),
                _mapping(
                    597,
                    "DEBT_DOMESTIC_TCKT",
                    24,
                    "Chứng khoán Nợ do các TCKT khác trong nước phát hành",
                    [42],
                    _value(43, "7.639.695"),
                ),
                _mapping(
                    600,
                    "EQUITY",
                    24,
                    "Chứng khoán Vốn",
                    [46],
                    _value(51, "226.907"),
                    topology="TRAILING_PARENT_TOTAL_AFTER_LAST_EQUITY_CHILD",
                ),
                _mapping(
                    602,
                    "EQUITY_TCTD",
                    24,
                    "Chứng khoán Vốn do các TCTD khác phát hành",
                    [47],
                    _value(48, "81.818"),
                ),
                _mapping(
                    603,
                    "EQUITY_DOMESTIC_TCKT",
                    24,
                    "Chứng khoán Vốn do các TCKT trong nước phát hành",
                    [49],
                    _value(50, "145.089"),
                ),
                _mapping(
                    612,
                    "PROVISION",
                    24,
                    "Dự phòng rủi ro Chứng khoán kinh doanh",
                    [52],
                    _value(57, "(178.762)"),
                    topology="TRAILING_PROVISION_TOTAL_AFTER_DETAILS",
                ),
                _mapping(
                    614, "PROVISION_GENERAL", 24, "Dự phòng chung", [53], _value(54, "(56.962)")
                ),
                _mapping(
                    615, "PROVISION_SPECIFIC", 24, "Dự phòng cụ thể", [55], _value(56, "(121.800)")
                ),
            ],
            [
                _equation(
                    "DEBT_CHILDREN_TO_DEBT",
                    24,
                    [_value(38, "12.544"), _value(41, "3.108.925"), _value(43, "7.639.695")],
                    _value(44, "10.761.164"),
                ),
                _equation(
                    "EQUITY_CHILDREN_TO_EQUITY",
                    24,
                    [_value(48, "81.818"), _value(50, "145.089")],
                    _value(51, "226.907"),
                ),
                _equation(
                    "PROVISION_DETAILS_TO_PROVISION",
                    24,
                    [_value(54, "(56.962)"), _value(56, "(121.800)")],
                    _value(57, "(178.762)"),
                ),
                _equation(
                    "DEBT_EQUITY_PROVISION_TO_NET",
                    24,
                    [_value(44, "10.761.164"), _value(51, "226.907"), _value(57, "(178.762)")],
                    _value(58, "10.809.309"),
                ),
            ],
        ),
        _doc(
            "VCB",
            30,
            "ISSUER_CLASSIFICATION_ROWS_X_PERIOD_COLUMNS",
            "2026-06-30",
            [
                _mapping(
                    595, "DEBT_GOVERNMENT", 30, "Trái phiếu Chính phủ", [15], _value(16, "875.470")
                ),
                _mapping(
                    596,
                    "DEBT_TCTD",
                    30,
                    "Trái phiếu do các TCTD khác trong nước phát hành",
                    [18],
                    _value(19, "19.017.739"),
                ),
                _mapping(
                    597,
                    "DEBT_DOMESTIC_TCKT",
                    30,
                    "Trái phiếu do các TCKT trong nước phát hành",
                    [21],
                    _value(22, "158.300"),
                ),
                _mapping(
                    602,
                    "EQUITY_TCTD",
                    30,
                    "Chứng khoán vốn do các TCTD khác phát hành",
                    [25],
                    _value(26, "51.393"),
                ),
                _mapping(
                    603,
                    "EQUITY_DOMESTIC_TCKT",
                    30,
                    "Chứng khoán vốn do các TCKT trong nước phát hành",
                    [28],
                    _value(29, "154.517"),
                ),
                _mapping(
                    611,
                    "GROSS",
                    30,
                    None,
                    [],
                    _value(31, "20.257.419"),
                    topology="UNLABELED_TOTAL_AFTER_LAST_EQUITY_CHILD_BEFORE_PROVISION",
                ),
                _mapping(
                    612,
                    "PROVISION",
                    30,
                    "Dự phòng giảm giá chứng khoán kinh doanh",
                    [33],
                    _value(34, "(97.883)"),
                ),
            ],
            [
                _equation(
                    "ISSUER_CHILDREN_TO_GROSS",
                    30,
                    [
                        _value(16, "875.470"),
                        _value(19, "19.017.739"),
                        _value(22, "158.300"),
                        _value(26, "51.393"),
                        _value(29, "154.517"),
                    ],
                    _value(31, "20.257.419"),
                ),
                _equation(
                    "GROSS_PROVISION_TO_NET",
                    30,
                    [_value(31, "20.257.419"), _value(34, "(97.883)")],
                    _value(36, "20.159.536"),
                ),
            ],
        ),
        _doc(
            "CTG",
            37,
            "ISSUER_CLASSIFICATION_ROWS_X_PERIOD_COLUMNS",
            "2026-06-30",
            [
                _mapping(594, "DEBT", 37, "Chứng khoán Nợ", [35], _value(36, "3.094.760")),
                _mapping(
                    595,
                    "DEBT_GOVERNMENT",
                    37,
                    "Chứng khoán Chính phủ, chính quyền địa phương",
                    [38],
                    _value(39, "2.014.414"),
                ),
                _mapping(
                    596,
                    "DEBT_TCTD",
                    37,
                    "Chứng khoán do các TCTD khác trong nước phát hành",
                    [41],
                    _value(42, "901.082"),
                ),
                _mapping(
                    597,
                    "DEBT_DOMESTIC_TCKT",
                    37,
                    "Chứng khoán do các TCKT trong nước phát hành",
                    [44],
                    _value(45, "179.264"),
                ),
                _mapping(600, "EQUITY", 37, "Chứng khoán Vốn", [47], _value(48, "1.002.446")),
                _mapping(
                    602,
                    "EQUITY_TCTD",
                    37,
                    "Chứng khoán Vốn do các TCTD khác phát hành",
                    [50],
                    _value(51, "281.699"),
                ),
                _mapping(
                    603,
                    "EQUITY_DOMESTIC_TCKT",
                    37,
                    "Chứng khoán Vốn do các TCKT trong nước phát hành",
                    [53],
                    _value(54, "720.747"),
                ),
                _mapping(
                    606,
                    "OTHER_TRADING",
                    37,
                    "Chứng khoán kinh doanh khác",
                    [56],
                    _value(57, "85.000"),
                ),
                _mapping(
                    612,
                    "PROVISION",
                    37,
                    "Dự phòng rủi ro chứng khoán",
                    [59],
                    _value(60, "(112.995)"),
                ),
            ],
            [
                _equation(
                    "DEBT_CHILDREN_TO_DEBT",
                    37,
                    [_value(39, "2.014.414"), _value(42, "901.082"), _value(45, "179.264")],
                    _value(36, "3.094.760"),
                ),
                _equation(
                    "EQUITY_CHILDREN_TO_EQUITY",
                    37,
                    [_value(51, "281.699"), _value(54, "720.747")],
                    _value(48, "1.002.446"),
                ),
                _equation(
                    "DEBT_EQUITY_OTHER_PROVISION_TO_NET",
                    37,
                    [
                        _value(36, "3.094.760"),
                        _value(48, "1.002.446"),
                        _value(57, "85.000"),
                        _value(60, "(112.995)"),
                    ],
                    _value(62, "4.069.211"),
                ),
            ],
        ),
        _doc(
            "BID",
            20,
            "ISSUER_CLASSIFICATION_ROWS_X_PERIOD_COLUMNS",
            "2026-06-30",
            [
                _mapping(594, "DEBT", 20, "Chứng khoán Nợ", [51], _value(52, "23,205,846")),
                _mapping(
                    595,
                    "DEBT_GOVERNMENT",
                    20,
                    "Chứng khoán Chính phủ, chính quyền địa phương",
                    [54],
                    _value(55, "821,178"),
                ),
                _mapping(
                    596,
                    "DEBT_TCTD",
                    20,
                    "Chứng khoán do các TCTD khác trong nước phát hành",
                    [57],
                    _value(58, "20,568,905"),
                ),
                _mapping(
                    597,
                    "DEBT_DOMESTIC_TCKT",
                    20,
                    "Chứng khoán do các TCKT trong nước phát hành",
                    [60],
                    _value(61, "1,815,763"),
                ),
                _mapping(600, "EQUITY", 20, "Chứng khoán Vốn", [63], _value(64, "1,552,760")),
                _mapping(
                    602,
                    "EQUITY_TCTD",
                    20,
                    "Chứng khoán do các TCTD khác trong nước phát hành",
                    [66],
                    _value(67, "478,017"),
                ),
                _mapping(
                    603,
                    "EQUITY_DOMESTIC_TCKT",
                    20,
                    "Chứng khoán do các TCKT trong nước phát hành",
                    [69],
                    _value(70, "1,074,350"),
                ),
                _mapping(
                    604,
                    "EQUITY_FOREIGN_TCKT",
                    20,
                    "Chứng khoán nước ngoài",
                    [72],
                    _value(73, "393"),
                ),
                _mapping(
                    612,
                    "PROVISION",
                    20,
                    "Dự phòng rủi ro chứng khoán kinh doanh",
                    [75],
                    _value(76, "(57,202)"),
                ),
            ],
            [
                _equation(
                    "DEBT_CHILDREN_TO_DEBT",
                    20,
                    [_value(55, "821,178"), _value(58, "20,568,905"), _value(61, "1,815,763")],
                    _value(52, "23,205,846"),
                ),
                _equation(
                    "EQUITY_CHILDREN_TO_EQUITY",
                    20,
                    [_value(67, "478,017"), _value(70, "1,074,350"), _value(73, "393")],
                    _value(64, "1,552,760"),
                ),
                _equation(
                    "DEBT_EQUITY_PROVISION_TO_NET",
                    20,
                    [_value(52, "23,205,846"), _value(64, "1,552,760"), _value(76, "(57,202)")],
                    _value(78, "24,701,404"),
                ),
            ],
        ),
        _doc(
            "VIB",
            None,
            None,
            "2026-06-30",
            [],
            [],
            disposition="UNRESOLVED_NO_TRADING_SECURITIES_REGION_IN_BOUND_COMPLETE_PDF_SCAN_DISTINCT_AFS_REGION_EXCLUDED",
        ),
    ]


def _review_blueprint() -> dict[str, Any]:
    material = {
        "claim_boundary": CLAIM_BOUNDARY,
        "documents": _review_documents(),
        "format_version": REVIEW_FORMAT,
        "review_checks": list(_REVIEW_CHECKS),
        "reviewer": {"kind": "CODEX_INDEPENDENT_VISIBLE_PDF_REVIEW", "review_run_id": "E-0059"},
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0059:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex trading-securities pixel review differs from the fixed ledger")
    return canonical_clone_v1(expected)


def _money(value: Any) -> int:
    if type(value) is not str or value != value.strip() or _MONEY.fullmatch(value) is None:
        raise _error(f"visible money transcription is invalid: {value!r}")
    if value in {"-", "–", "—"}:
        return 0
    negative = value.startswith("(") and value.endswith(")")
    digits = value.strip("()").replace(".", "").replace(",", "")
    if not digits.isdigit():
        raise _error("visible money digits drifted")
    result = int(digits)
    return -result if negative else result


def _document_by_code(documents: Any, code: str, label: str) -> dict[str, Any]:
    if type(documents) is not list:
        raise _error(f"{label} document axis drifted")
    matches = [
        item
        for item in documents
        if type(item) is dict and item.get("document_provenance", item.get("bank_code")) == code
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain one exact document {code}")
    return matches[0]


def _page_by_number(document: Mapping[str, Any], page_number: int, label: str) -> dict[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error(f"{label} page axis drifted")
    matches = [
        page
        for page in pages
        if type(page) is dict
        and page.get("physical_page", page.get("page_sequence")) == page_number
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain page {page_number}")
    return matches[0]


def _artifact_bytes(reference: Any, label: str) -> bytes:
    if (
        type(reference) is not dict
        or set(reference) != {"path", "sha256", "size_bytes"}
        or type(reference["path"]) is not str
        or type(reference["size_bytes"]) is not int
    ):
        raise _error(f"{label} reference fields drifted")
    payload = _stable_bytes(Path(reference["path"]))
    if len(payload) != reference["size_bytes"] or hashlib.sha256(payload).hexdigest() != _sha256(
        reference["sha256"], label
    ):
        raise _error(f"{label} bytes drifted")
    return payload


def _source_line_axis(page: Mapping[str, Any]) -> list[str]:
    result = _strict_json(_artifact_bytes(page.get("result_ref"), "page result"), "page result")
    lines = result.get("lines")
    if type(lines) is list and lines:
        texts = [line.get("raw_text") if type(line) is dict else None for line in lines]
        if len(texts) != page.get("primary_line_count") or not all(
            type(text) is str for text in texts
        ):
            raise _error("page result source line axis drifted")
        return texts
    backend = _strict_json(_artifact_bytes(page.get("backend_ref"), "page backend"), "page backend")
    raw = backend.get("raw_provider_payload")
    texts = raw.get("rec_texts") if type(raw) is dict else None
    if (
        type(texts) is not list
        or len(texts) != page.get("supplement_line_count")
        or not all(type(text) is str for text in texts)
    ):
        raise _error("terminal backend source line axis drifted")
    return list(texts)


def _axis_line(page: Mapping[str, Any], line_index: int) -> dict[str, Any]:
    lines = page.get("lines")
    if type(lines) is not list or not 0 <= line_index < len(lines):
        raise _error("fresh VietOCR line index drifted")
    line = lines[line_index]
    if (
        type(line) is not dict
        or line.get("source_line_index") != line_index
        or type(line.get("vietocr_text")) is not str
    ):
        raise _error("fresh VietOCR semantic line identity drifted")
    return line


def _source_value(
    axis_page: Mapping[str, Any],
    semantic_page: Mapping[str, Any],
    crop_page: Mapping[str, Any],
    source_texts: Sequence[str],
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"line_index", "pixel_transcription"}
        or type(value["line_index"]) is not int
    ):
        raise _error("reviewed source value fields drifted")
    line_index = value["line_index"]
    pixel_value = _money(value["pixel_transcription"])
    axis = _axis_line(axis_page, line_index)
    semantic_lines = semantic_page.get("lines")
    if type(semantic_lines) is not list or not 0 <= line_index < len(semantic_lines):
        raise _error("semantic-index crop line axis drifted")
    semantic_line = semantic_lines[line_index]
    if (
        type(semantic_line) is not dict
        or semantic_line.get("source_line_index") != line_index
        or semantic_line.get("vietocr_text") != axis["vietocr_text"]
        or type(semantic_line.get("crop_ref")) is not dict
        or type(semantic_line.get("sample_id")) is not str
        or not 0 <= line_index < len(source_texts)
    ):
        raise _error("semantic-index crop/source binding drifted")
    source_raw = source_texts[line_index]
    if _money(source_raw) != pixel_value:
        raise _error("visible pixel transcription and source numeric challenger disagree")
    crop_ref = semantic_line["crop_ref"]
    sample_first = crop_page.get("sample_offset_start")
    sample_stop = crop_page.get("sample_offset_stop")
    sample_id = semantic_line["sample_id"]
    if type(sample_first) is not int or type(sample_stop) is not int:
        raise _error("crop page/sample binding drifted")
    expected_sample_ordinal = sample_first + line_index + 1
    expected_sample_id = f"sample-{expected_sample_ordinal:08d}"
    if (
        not sample_first <= expected_sample_ordinal - 1 < sample_stop
        or sample_id != expected_sample_id
        or type(crop_ref.get("path")) is not str
        or not crop_ref["path"].endswith(f"/{expected_sample_id}.png")
    ):
        raise _error("crop page/sample ordinal or content binding drifted")
    return {
        "crop_ref": canonical_clone_v1(crop_ref),
        "fresh_vietocr_numeric_proposal": axis["vietocr_text"],
        "normalized_value": pixel_value,
        "pixel_transcription": value["pixel_transcription"],
        "source_line_index": line_index,
        "source_numeric_challenger": source_raw,
        "source_numeric_challenger_status": "MATCHED_VISIBLE_PIXEL_TRANSCRIPTION",
    }


def _schema_binding(item: Any) -> dict[str, Any]:
    if (
        item is None
        or item.statement_type != "TM"
        or item.schema_id not in range(594, 631)
        or item.parent_id not in {593, 616}
    ):
        raise _error("reviewed mapping does not bind one supported live trading TM item")
    return {
        "canonical_name": item.canonical_name,
        "display_order": item.display_order,
        "hierarchy_level": item.hierarchy_level,
        "report_norm_id": item.schema_id,
        "schema_parent_report_norm_id": item.parent_id,
    }


def build_trading_securities_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review_value: Any,
    schema_authority: Mapping[str, Any],
    schema_by_id: Mapping[int, Any],
    *,
    crop_manifest_sha256: str,
    review_sha256: str,
) -> dict[str, Any]:
    """Build the exact eight-bank bounded trading-securities mapping result."""

    review = _review(review_value)
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or structure_scan.get("state") != "FULL_DOCUMENT_TRADING_SECURITIES_STRUCTURE_SCAN_COMPLETE"
        or type(crop_manifest) is not dict
    ):
        raise _error("trading-securities input authority drifted")
    _sha256(crop_manifest_sha256, "crop manifest")
    _sha256(review_sha256, "pixel review")
    trials: list[dict[str, Any]] = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        reviewed = _document_by_code(review["documents"], code, "pixel review")
        semantic_document = _document_by_code(
            semantic_index.get("documents"), code, "semantic index"
        )
        axis_document = _document_by_code(axis["documents"], code, "fresh VietOCR axis")
        crop_document = _document_by_code(crop_manifest.get("documents"), code, "crop manifest")
        scan_trial = _document_by_code(structure_scan.get("trials"), code, "structure scan")
        matcher = scan_trial.get("matcher_result")
        if scan_trial.get("document_ordinal") != ordinal or type(matcher) is not dict:
            raise _error("whole-PDF trading-securities scan identity drifted")
        page_number = reviewed["page_sequence"]
        if page_number is None:
            if (
                matcher.get("status") != "UNRESOLVED_NO_COMPLETE_REGION"
                or matcher.get("regions") != []
                or reviewed["mappings"]
                or reviewed["equations"]
            ):
                raise _error("negative trading-securities disposition drifted")
            trials.append(
                {
                    "cluster_boundary": None,
                    "document_ordinal": ordinal,
                    "document_provenance": code,
                    "disposition": reviewed["disposition"],
                    "layout": None,
                    "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                    "source_period": reviewed["source_period"],
                    "status": "UNRESOLVED",
                    "verified_accounting_equations": [],
                    "verified_mappings": [],
                    "whole_document_family_absence_claim": False,
                    "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
                }
            )
            continue
        if (
            matcher.get("status") != "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            or matcher.get("uniqueness")
            != {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or type(matcher.get("regions")) is not list
            or len(matcher["regions"]) != 1
        ):
            raise _error("whole-PDF trading-securities region is not exactly unique")
        region = matcher["regions"][0]
        meaningful_axes = region.get("layout", {}).get("meaningful_axes", {})
        if (
            region.get("page_sequence") != page_number
            or not reviewed["layout_variant"].startswith(
                region.get("layout", {}).get("branch_variant", "")
            )
            or meaningful_axes.get("unit_header_count", 0) < 1
            or meaningful_axes.get("period_header_count", 0) < 2
        ):
            raise _error("reviewed page/layout disagrees with generic structure graph")
        axis_page = _page_by_number(axis_document, page_number, "fresh VietOCR axis")
        semantic_page = _page_by_number(semantic_document, page_number, "semantic index")
        crop_page = _page_by_number(crop_document, page_number, "crop manifest")
        source_texts = _source_line_axis(crop_page)
        mapped_rows = []
        for row in reviewed["mappings"]:
            label_lines = row["label_line_indices"]
            if type(label_lines) is not list or any(
                type(index) is not int for index in label_lines
            ):
                raise _error("reviewed trading-securities label line axis drifted")
            if not label_lines and not row["topology"].startswith("UNLABELED_TOTAL"):
                raise _error("only exact topology-bound totals may omit a visible label")
            transformer_text = [
                _axis_line(axis_page, index)["vietocr_text"] for index in label_lines
            ]
            source_value = _source_value(
                axis_page, semantic_page, crop_page, source_texts, row["value"]
            )
            schema = _schema_binding(schema_by_id.get(row["report_norm_id"]))
            mapped_rows.append(
                {
                    **schema,
                    "independent_pixel_label": row["label_pixel_transcription"],
                    "normalized_anchor": (
                        normalize_vietnamese_anchor_v1(" ".join(transformer_text))
                        if transformer_text
                        else None
                    ),
                    "normalized_value": source_value["normalized_value"],
                    "physical_page": page_number,
                    "role": row["role"],
                    "source_value": source_value,
                    "status": "VERIFIED_BY_CODEX",
                    "topology": row["topology"],
                    "vietocr_transformer_text": transformer_text,
                }
            )
        equations = []
        for equation in reviewed["equations"]:
            components = [
                _source_value(axis_page, semantic_page, crop_page, source_texts, value)
                for value in equation["component_values"]
            ]
            total = _source_value(
                axis_page, semantic_page, crop_page, source_texts, equation["visible_total"]
            )
            computed = sum(item["normalized_value"] for item in components)
            if computed != total["normalized_value"]:
                raise _error(f"trading-securities accounting equation does not close: {code}")
            equations.append(
                {
                    "computed_total": computed,
                    "name": equation["name"],
                    "physical_page": page_number,
                    "status": "CORROBORATED_EXACT",
                    "visible_total": total["normalized_value"],
                }
            )
        source_period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if reviewed["source_period"] == "2026-03-31"
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        trials.append(
            {
                "cluster_boundary": canonical_clone_v1(region["cluster_boundary"]),
                "document_ordinal": ordinal,
                "document_provenance": code,
                "disposition": reviewed["disposition"],
                "layout": canonical_clone_v1(region["layout"]),
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period": reviewed["source_period"],
                "source_period_status": source_period_status,
                "status": (
                    "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT"
                    if source_period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                    else "VERIFIED_BY_CODEX"
                ),
                "verified_accounting_equations": equations,
                "verified_mappings": mapped_rows,
                "visible_page_render_binding": canonical_clone_v1(crop_page["render_binding"]),
                "whole_document_family_absence_claim": False,
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
        )
    metrics = {
        "accounting_equation_verified_count": sum(
            len(trial["verified_accounting_equations"]) for trial in trials
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["complete_region_count"] == 1 for trial in trials
        ),
        "mapping_verified_count": sum(len(trial["verified_mappings"]) for trial in trials),
        "q1_source_period_caveat_document_count": sum(
            trial.get("source_period_status") == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "unresolved_document_count": sum(trial["status"] == "UNRESOLVED" for trial in trials),
    }
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "codex_pixel_review": {"path": REVIEW_PATH.as_posix(), "sha256": review_sha256},
            "crop_manifest_sha256": crop_manifest_sha256,
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": structure_scan["scan_id"],
            "tm_schema_authority": canonical_clone_v1(schema_authority),
        },
        "metrics": metrics,
        "state": "TRADING_SECURITIES_8BANK_BOUNDED_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "ts8bcv1:result:" + canonical_json_sha256_v1(material)}
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("verified trading-securities result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "TRADING_SECURITIES_8BANK_BOUNDED_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
    ):
        raise _error("verified trading-securities result identity/authority drifted")
    material = canonical_clone_v1(value)
    identity = material.pop("result_id")
    if identity != "ts8bcv1:result:" + canonical_json_sha256_v1(material):
        raise _error("verified trading-securities result identity drifted")
    return canonical_clone_v1(value)


def build_live_trading_securities_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    semantic_index, _ = _fixed_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, crop_bytes = _fixed_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review_value, review_bytes = _fixed_json(REVIEW_PATH)
    scan = _scanner().build_trading_securities_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_trading_securities_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        scan,
        review_value,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=hashlib.sha256(crop_bytes).hexdigest(),
        review_sha256=hashlib.sha256(review_bytes).hexdigest(),
    )


def validate_trading_securities_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    persisted = _validate_result(value)
    rebuilt = build_live_trading_securities_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("verified trading-securities result does not replay exactly")
    return rebuilt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.write_review:
        output = REVIEW_PATH
        value = _review_blueprint()
    else:
        output = args.output
        value = build_live_trading_securities_8bank_codex_verified_mapping_v1()
    if output.exists() and not args.replace:
        raise _error(f"refusing to overwrite fixed trading-securities artifact: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes_v1(value))
    print(output.as_posix())
    print(hashlib.sha256(output.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
