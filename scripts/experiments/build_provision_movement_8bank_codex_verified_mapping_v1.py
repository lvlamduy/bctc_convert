"""Verify eight-bank customer-loan provision movements and map the core lanes.

The complete-PDF matcher remains bank blind.  This post-scan Role-A verifier
binds its unique regions to an independent visible-pixel review, challenges
digits with the exact upstream PP-OCRv6/native line axis, treats only visible
dashes as zero, checks every lane roll-forward, and maps only the overall
customer-loan general/specific lanes to the live TM schema.  Geographic,
margin, deferred-LC, and combined lanes remain non-additive check evidence.
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
from io import BytesIO
from pathlib import Path
from types import ModuleType
from typing import Any

import fitz
from PIL import Image

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
    EXPECTED_DOCUMENT_ORDER,
    project_full_document_vietocr_accounting_axis_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import _authority_snapshot
from bctc_ai.rendering.page_reader import render_composited_displayed_page
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "ProvisionMovement8BankCodexVerifiedMappingV1Error",
    "build_live_provision_movement_8bank_codex_verified_mapping_v1",
    "build_provision_movement_8bank_codex_verified_mapping_v1",
    "validate_provision_movement_8bank_codex_verified_mapping_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "PROVISION_MOVEMENT_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "PROVISION_MOVEMENT_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_VIETOCR_GENERIC_CUSTOMER_LOAN_"
    "PROVISION_MOVEMENT_STRUCTURE_PLUS_INDEPENDENT_VISIBLE_PIXEL_UPSTREAM_NUMERIC_"
    "CHALLENGER_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
REVIEW_PATH = Path("docs/experiments/E-0057-provision-movement-8bank-codex-pixel-review-v1.json")
RESULT_PATH = Path(
    "docs/experiments/E-0057-provision-movement-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "pmfdsv1:scan:61e30d784dd91ec666d6db7e46833c9a3493d51c4451ab11b97ae7771b2b9e5a"
REVIEW_SHA256 = "7c7cbbb8e755b0855202ff969c44bf44bce135deaed4e83bb96605a270779c4a"

_LANE_PARENT = {"GENERAL": 784, "SPECIFIC": 792, "MARGIN_ADVANCE": 6061}
_ROLE_IDS = {
    "GENERAL": {
        "OPENING": 785,
        "PROVISION": 786,
        "USE": 787,
        "FX": 788,
        "DECREASE": 789,
        "OTHER": 790,
        "CLOSING": 791,
    },
    "SPECIFIC": {
        "OPENING": 793,
        "PROVISION": 794,
        "USE": 795,
        "FX": 796,
        "DECREASE": 797,
        "OTHER": 798,
        "CLOSING": 799,
    },
    "MARGIN_ADVANCE": {
        "OPENING": 6062,
        "PROVISION": 6063,
        "USE": 6064,
        "CLOSING": 6065,
    },
}
_SCHEMA_NAMES = {
    783: "Biến động số dư dự phòng rủi ro cho vay KH",
    784: "Dự phòng chung",
    785: "Số dư đầu kỳ này",
    786: "+ Dự phòng rủi ro trích lập trong kỳ/(Hoàn nhập dự phòng trong kỳ)",
    787: "+ Sử dụng dự phòng rủi ro tín dụng trong kỳ",
    788: "+ Chênh lệch tỷ giá ngoại tệ",
    789: "+ Giảm dự phòng rủi ro tín dụng trong năm",
    790: "+ Điều chỉnh khác",
    791: "Số dư cuối kỳ này",
    792: "Dự phòng cụ thể",
    793: "Số dư đầu kỳ này",
    794: "+ Dự phòng rủi ro trích lập trong kỳ/(Hoàn nhập dự phòng trong kỳ)",
    795: "+ Sử dụng dự phòng rủi ro tín dụng trong kỳ",
    796: "+ Chênh lệch tỷ giá ngoại tệ",
    797: "+ Giảm dự phòng rủi ro tín dụng trong năm",
    798: "+ Điều chỉnh khác",
    799: "Số dư cuối kỳ này",
    6061: "Dự phòng rủi ro cho vay giao dịch ký quỹ và ứng trước khách hàng",
    6062: "Số dư đầu kỳ này",
    6063: "+ Dự phòng rủi ro trích lập trong kỳ/(Hoàn nhập dự phòng trong kỳ)",
    6064: "+ Sử dụng dự phòng rủi ro tín dụng trong kỳ",
    6065: "Số dư cuối kỳ này",
}
_REQUIRED_ROLES = frozenset({"OPENING", "PROVISION", "CLOSING"})
_ROLE_ORDER = ("OPENING", "PROVISION", "USE", "FX", "DECREASE", "OTHER", "CLOSING")
_REVIEW_CHECKS = [
    "COMPLETE_PDF_UNIQUE_REGION_ENUMERATION",
    "VISIBLE_CONSOLIDATED_REPORT_SCOPE",
    "CUSTOMER_LOAN_PROVISION_OWNER",
    "GENERAL_AND_SPECIFIC_LANE_IDENTITY",
    "PERIOD_AND_UNIT_SCOPE",
    "ROW_LABEL_ROLE_AND_ORDER",
    "VALUE_GEOMETRY",
    "VISIBLE_PIXEL_DIGITS_SIGN_AND_DASH",
    "UPSTREAM_PPOCRV6_OR_NATIVE_NUMERIC_CHALLENGER",
    "OPENING_PLUS_MOVEMENTS_EQUALS_CLOSING",
    "SOURCE_ONLY_AUXILIARY_LANES_NOT_DOUBLE_COUNTED",
    "LIVE_TM_SCHEMA_PARENT_CHILD_AND_DISPLAY_ORDER",
    "NEGATIVE_PROVISION_EXPENSE_POLICY_AND_SECURITIES_CONTROLS",
]
_REVIEW_SAFETY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_or_absent_cell_interpreted_as_zero": False,
    "fresh_vietocr_used_as_numeric_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_UPSTREAM_NUMERIC_CHALLENGER_AND_ACCOUNTING",
    "only_visible_dash_interpreted_as_zero": True,
    "old_ocr_used_as_semantic_anchor": False,
    "source_only_auxiliary_lanes_mapped_additively": False,
    "comparison_period_used_as_mapping_authority": False,
    "current_reporting_period_only_mapped": True,
    "whole_pdf_uniqueness_replayed": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "dash_zero_policy_applied_only_to_visible_dash": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_hierarchy_checked": True,
    "mapping_authority_is_bounded_to_reviewed_general_and_specific_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_only_auxiliary_lanes_exported_additively": False,
    "comparison_period_used_as_mapping_authority": False,
    "current_reporting_period_only_mapped": True,
    "text_similarity_alone_used_for_mapping": False,
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


class ProvisionMovement8BankCodexVerifiedMappingV1Error(ValueError):
    """The review, pixels, numeric challenger, accounting, or schema drifted."""


def _error(message: str) -> ProvisionMovement8BankCodexVerifiedMappingV1Error:
    return ProvisionMovement8BankCodexVerifiedMappingV1Error(message)


def _sha256(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(char not in _HEX for char in value):
        raise _error(f"{label} SHA-256 drifted")
    return value


def _scanner() -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments/scan_provision_movement_full_document_vietocr_v1.py"
    spec = importlib.util.spec_from_file_location("provision_scan_for_e0057_mapping", path)
    if spec is None or spec.loader is None:
        raise _error("cannot load provision full-document scanner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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

    def identity(item: os.stat_result) -> tuple[int, int, int, int, int]:
        return item.st_dev, item.st_ino, item.st_mode, item.st_size, item.st_mtime_ns

    if identity(before) != identity(after):
        raise _error(f"fixed artifact changed while reading: {path}")
    payload = b"".join(chunks)
    if len(payload) != before.st_size:
        raise _error(f"fixed artifact read was incomplete: {path}")
    return payload


def _fixed_json(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], bytes]:
    payload = _stable_bytes(path)
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise _error(f"fixed artifact content identity drifted: {path}")
    try:
        value = json.loads(
            payload, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token))
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _error(f"fixed artifact is not strict JSON: {path}") from exc
    if type(value) is not dict:
        raise _error(f"fixed artifact root is not one object: {path}")
    return value, payload


def _pixel_binding(bbox: Sequence[int], rgb_sha256: str) -> dict[str, Any]:
    return {"bbox_raw_pixels": list(bbox), "rgb_sha256": rgb_sha256}


def _row(
    role: str,
    label: str,
    label_lines: Sequence[int],
    value_line: int | None,
    pixel_value: str,
    pixel_binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "label_line_indices": list(label_lines),
        "label_pixel_transcription": label,
        "pixel_binding": canonical_clone_v1(pixel_binding),
        "pixel_value_transcription": pixel_value,
        "role": role,
        "value_line_index": value_line,
    }


def _series(
    period: str,
    lane: str,
    page: int,
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "lane": lane,
        "period": period,
        "physical_page": page,
        "rows": canonical_clone_v1(rows),
    }


def _document(
    code: str,
    pages: Sequence[int],
    series: Sequence[Mapping[str, Any]],
    source_only_lanes: Sequence[str],
) -> dict[str, Any]:
    current = [item for item in series if str(item.get("period", "")).startswith("2026-")]
    comparison_periods = [
        str(item["period"])
        for item in series
        if not str(item.get("period", "")).startswith("2026-")
    ]
    return {
        "comparison_periods_excluded_from_mapping": list(dict.fromkeys(comparison_periods)),
        "disposition": "UNIQUE_COMPLETE_REGION_VISIBLE_PIXEL_REVIEWED",
        "document_provenance": code,
        "page_sequences": list(pages),
        "series": canonical_clone_v1(current),
        "source_only_auxiliary_lanes": list(source_only_lanes),
        "whole_document_family_absence_claim": False,
    }


def _review_blueprint() -> dict[str, Any]:
    """Return the manually reviewed pixel ledger; values are never OCR-generated here."""

    acb_current_general_dash = _pixel_binding(
        [1018, 1620, 1065, 1672],
        "a00710290dc703d78759160667979287cc1570938fe71d4ecda1796c8f1c2d16",
    )
    acb_prior_general_dash = _pixel_binding(
        [1018, 1828, 1065, 1884],
        "db0e6cd64cc6e86ea4be065219ba84ea4cd1e80e89691d6d26b921a71e2bd99a",
    )
    mbb_prior_general_dash = _pixel_binding(
        [1875, 1115, 1928, 1165],
        "9b3c208cc667f1a34f9a2b1fff9427edf8324aaa1651a8111fa91fe23329446a",
    )
    mbb_current_general_dash = _pixel_binding(
        [1903, 629, 1916, 644],
        "9fe0688f6cae9233a9bda89450112a8e0496f5ae78a59952f87fb73e0df7da9d",
    )
    vpb_current_margin_provision_dash = _pixel_binding(
        [1295, 1043, 1305, 1076],
        "0d854f40461b64da5547c6b1545b3d7f90e81bfb0f7ab508b0443de858108492",
    )
    vpb_current_margin_use_dash = _pixel_binding(
        [1295, 1079, 1305, 1111],
        "a9a8be2291464f4689bbf4ab20f6b8ad2da318f23210bd02cb0c4af67a1f45b1",
    )
    hdb_current_general_dash = _pixel_binding(
        [1025, 600, 1075, 650],
        "9ce2ccee30b37a309af2cf54c11f013badf127c6700f7d41842e89492f4c07a9",
    )
    hdb_prior_general_dash = _pixel_binding(
        [1025, 1000, 1075, 1050],
        "a6bfd2c770a34ecb9a55f9a6e61e1d021ebd56964b650a8024724b9032c55bb3",
    )
    vcb_current_specific_dash = _pixel_binding(
        [1210, 1980, 1258, 2008],
        "6b1e3a7d0a55c416f63418db7034d2a09006f7e0324d96aee6695c083ebe2952",
    )
    ctg_current_general_dash = _pixel_binding(
        [1570, 2075, 1635, 2140],
        "75990d233ea4b4ec19f6954e1d3dbcce91e5b8c6d266c15e335a889e1b500fdf",
    )
    ctg_prior_general_dash = _pixel_binding(
        [1570, 2615, 1640, 2685],
        "5fb53e1171cf5e5fcef978e27e68641aae97db9dad17ee019230878ef6ed3ee1",
    )
    bid_current_general_dash = _pixel_binding(
        [1125, 425, 1180, 480],
        "e369b3f49cc13e22765a86b9b533e22a885e0376054dddc96ad2eb5cab2be829",
    )
    bid_prior_general_dash = _pixel_binding(
        [1125, 680, 1180, 735],
        "59e8703fd51e49608e85fb4e478e59c9fed2788fdd66f280ad20b09006a37ff5",
    )
    vib_current_general_dash = _pixel_binding(
        [1000, 1760, 1050, 1815],
        "ffbaff7e6717ea8b8caa2ebfd55ee7b1c02cd5e0ffd423658c711e922308c097",
    )
    vib_prior_general_dash = _pixel_binding(
        [1000, 665, 1050, 720],
        "95a7ac348b3bb9f6220bfec0d14a951682e72ef59d5e0c0555d1b9857d3d29ce",
    )

    documents = [
        _document(
            "ACB",
            [18],
            [
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "GENERAL",
                    18,
                    [
                        _row("OPENING", "Tại ngày 1 tháng 1 năm 2026", [58], 59, "4.982.250"),
                        _row(
                            "PROVISION",
                            "Trích lập trong kỳ/(Hoàn nhập trong kỳ)",
                            [62],
                            63,
                            "418.853",
                        ),
                        _row("USE", "Sử dụng trong kỳ", [65], None, "-", acb_current_general_dash),
                        _row("CLOSING", "Tại ngày 30 tháng 6 năm 2026", [67], 68, "5.401.103"),
                    ],
                ),
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "SPECIFIC",
                    18,
                    [
                        _row("OPENING", "Tại ngày 1 tháng 1 năm 2026", [58], 60, "2.525.003"),
                        _row(
                            "PROVISION",
                            "Trích lập trong kỳ/(Hoàn nhập trong kỳ)",
                            [62],
                            64,
                            "1.327.192",
                        ),
                        _row("USE", "Sử dụng trong kỳ", [65], 66, "(1.305.430)"),
                        _row("CLOSING", "Tại ngày 30 tháng 6 năm 2026", [67], 69, "2.546.765"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-12-31",
                    "GENERAL",
                    18,
                    [
                        _row("OPENING", "Tại ngày 1 tháng 1 năm 2025", [71], 72, "4.239.076"),
                        _row(
                            "PROVISION",
                            "Trích lập trong kỳ/(Hoàn nhập trong kỳ)",
                            [75],
                            76,
                            "743.174",
                        ),
                        _row("USE", "Sử dụng trong kỳ", [78], None, "-", acb_prior_general_dash),
                        _row("CLOSING", "Tại ngày 31 tháng 12 năm 2025", [80], 81, "4.982.250"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-12-31",
                    "SPECIFIC",
                    18,
                    [
                        _row("OPENING", "Tại ngày 1 tháng 1 năm 2025", [71], 73, "2.383.004"),
                        _row(
                            "PROVISION",
                            "Trích lập trong kỳ/(Hoàn nhập trong kỳ)",
                            [75],
                            77,
                            "2.592.268",
                        ),
                        _row("USE", "Sử dụng trong kỳ", [78], 79, "(2.450.269)"),
                        _row("CLOSING", "Tại ngày 31 tháng 12 năm 2025", [80], 82, "2.525.003"),
                    ],
                ),
            ],
            ["MARGIN_LOAN_PROVISION_LANE"],
        ),
        _document(
            "MBB",
            [34],
            [
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "GENERAL",
                    34,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [22], 30, "8.098.145"),
                        _row(
                            "PROVISION",
                            "Dự phòng rủi ro trích lập/(hoàn nhập) thuần trong kỳ",
                            [32, 33, 34],
                            42,
                            "1.058.640",
                        ),
                        _row(
                            "USE",
                            "Sử dụng quỹ",
                            [44],
                            53,
                            "-",
                            mbb_current_general_dash,
                        ),
                        _row("FX", "Chênh lệch tỷ giá", [54], 59, "17"),
                        _row("CLOSING", "Số dư cuối kỳ", [62], 70, "9.156.802"),
                    ],
                ),
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "SPECIFIC",
                    34,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [22], 29, "5.052.448"),
                        _row(
                            "PROVISION",
                            "Dự phòng rủi ro trích lập/(hoàn nhập) thuần trong kỳ",
                            [32, 33, 34],
                            41,
                            "6.636.930",
                        ),
                        _row("USE", "Sử dụng quỹ", [44], 49, "(4.184.760)"),
                        _row("FX", "Chênh lệch tỷ giá", [54], 58, "1.461"),
                        _row("CLOSING", "Số dư cuối kỳ", [62], 69, "7.506.079"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-12-31",
                    "GENERAL",
                    34,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [92], 100, "5.795.573"),
                        _row(
                            "PROVISION",
                            "Dự phòng rủi ro trích lập/(hoàn nhập) thuần trong kỳ",
                            [102, 103, 104],
                            112,
                            "2.301.538",
                        ),
                        _row("USE", "Sử dụng quỹ", [114], None, "-", mbb_prior_general_dash),
                        _row(
                            "OTHER",
                            "Điều chỉnh theo Kiểm toán Nhà nước",
                            [120, 121],
                            126,
                            "(1.444)",
                        ),
                        _row("FX", "Chênh lệch tỷ giá", [128], 133, "2.478"),
                        _row("CLOSING", "Số dư cuối kỳ", [135], 143, "8.098.145"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-12-31",
                    "SPECIFIC",
                    34,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [92], 99, "5.814.288"),
                        _row(
                            "PROVISION",
                            "Dự phòng rủi ro trích lập/(hoàn nhập) thuần trong kỳ",
                            [102, 103, 104],
                            111,
                            "11.388.818",
                        ),
                        _row("USE", "Sử dụng quỹ", [114], 117, "(12.185.137)"),
                        _row(
                            "OTHER",
                            "Điều chỉnh theo Kiểm toán Nhà nước",
                            [120, 121],
                            125,
                            "33.942",
                        ),
                        _row("FX", "Chênh lệch tỷ giá", [128], 132, "537"),
                        _row("CLOSING", "Số dư cuối kỳ", [135], 142, "5.052.448"),
                    ],
                ),
            ],
            [
                "DOMESTIC_SPECIFIC",
                "DOMESTIC_GENERAL",
                "DOMESTIC_COMBINED",
                "FOREIGN_SPECIFIC",
                "FOREIGN_GENERAL",
                "FOREIGN_COMBINED",
                "OVERALL_COMBINED",
            ],
        ),
        _document(
            "VPB",
            [45],
            [
                _series(
                    "2026-01-01_TO_2026-03-31",
                    "GENERAL",
                    45,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [41], 42, "6.754.832"),
                        _row(
                            "PROVISION",
                            "Dự phòng rủi ro trích lập trong kỳ (Thuyết minh số 36)",
                            [46, 47],
                            48,
                            "697.978",
                        ),
                        _row(
                            "USE",
                            "Sử dụng dự phòng xử lý rủi ro tín dụng trong kỳ",
                            [52, 57],
                            53,
                            "-",
                        ),
                        _row("CLOSING", "Số dư cuối kỳ", [58], 59, "7.452.810"),
                    ],
                ),
                _series(
                    "2026-01-01_TO_2026-03-31",
                    "SPECIFIC",
                    45,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [41], 43, "10.512.525"),
                        _row(
                            "PROVISION",
                            "Dự phòng rủi ro trích lập trong kỳ (Thuyết minh số 36)",
                            [46, 47],
                            49,
                            "6.974.438",
                        ),
                        _row(
                            "USE",
                            "Sử dụng dự phòng xử lý rủi ro tín dụng trong kỳ",
                            [52, 57],
                            54,
                            "(5.416.280)",
                        ),
                        _row("CLOSING", "Số dư cuối kỳ", [58], 60, "12.070.683"),
                    ],
                ),
                _series(
                    "2026-01-01_TO_2026-03-31",
                    "MARGIN_ADVANCE",
                    45,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [41], 44, "161.614"),
                        _row(
                            "PROVISION",
                            "Dự phòng rủi ro trích lập trong kỳ (Thuyết minh số 36)",
                            [46, 47],
                            50,
                            "-",
                            vpb_current_margin_provision_dash,
                        ),
                        _row(
                            "USE",
                            "Sử dụng dự phòng xử lý rủi ro tín dụng trong kỳ",
                            [52, 57],
                            55,
                            "-",
                            vpb_current_margin_use_dash,
                        ),
                        _row("CLOSING", "Số dư cuối kỳ", [58], 61, "161.614"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-03-31",
                    "GENERAL",
                    45,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [79], 80, "5.079.275"),
                        _row(
                            "PROVISION",
                            "Dự phòng rủi ro trích lập trong kỳ (Thuyết minh số 36)",
                            [84, 85],
                            86,
                            "268.907",
                        ),
                        _row(
                            "USE",
                            "Sử dụng dự phòng xử lý rủi ro tín dụng và bán nợ trong kỳ",
                            [90, 91],
                            92,
                            "(40.436)",
                        ),
                        _row("CLOSING", "Số dư cuối kỳ", [96], 97, "5.307.746"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-03-31",
                    "SPECIFIC",
                    45,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [79], 81, "11.203.918"),
                        _row(
                            "PROVISION",
                            "Dự phòng rủi ro trích lập trong kỳ (Thuyết minh số 36)",
                            [84, 85],
                            87,
                            "6.338.779",
                        ),
                        _row(
                            "USE",
                            "Sử dụng dự phòng xử lý rủi ro tín dụng và bán nợ trong kỳ",
                            [90, 91],
                            93,
                            "(6.518.097)",
                        ),
                        _row("CLOSING", "Số dư cuối kỳ", [96], 98, "11.024.600"),
                    ],
                ),
            ],
            ["MARGIN_AND_SECURITIES_ADVANCE_PROVISION", "OVERALL_COMBINED"],
        ),
        _document(
            "HDB",
            [28],
            [
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "GENERAL",
                    28,
                    [
                        _row("OPENING", "Tại ngày 01 tháng 01 năm 2026", [22], 23, "4.069.255"),
                        _row(
                            "PROVISION",
                            "Trích lập/(Hoàn nhập) dự phòng trong kỳ",
                            [26],
                            27,
                            "815.347",
                        ),
                        _row(
                            "USE",
                            "Sử dụng dự phòng rủi ro tín dụng trong kỳ",
                            [30],
                            None,
                            "-",
                            hdb_current_general_dash,
                        ),
                        _row("CLOSING", "Tại ngày 30 tháng 06 năm 2026", [33], 34, "4.884.602"),
                    ],
                ),
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "SPECIFIC",
                    28,
                    [
                        _row("OPENING", "Tại ngày 01 tháng 01 năm 2026", [22], 24, "3.230.190"),
                        _row(
                            "PROVISION",
                            "Trích lập/(Hoàn nhập) dự phòng trong kỳ",
                            [26],
                            28,
                            "3.048.420",
                        ),
                        _row(
                            "USE",
                            "Sử dụng dự phòng rủi ro tín dụng trong kỳ",
                            [30],
                            31,
                            "(1.966.127)",
                        ),
                        _row("CLOSING", "Tại ngày 30 tháng 06 năm 2026", [33], 35, "4.312.483"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-12-31",
                    "GENERAL",
                    28,
                    [
                        _row("OPENING", "Tại ngày 01 tháng 01 năm 2025", [51], 52, "3.216.873"),
                        _row(
                            "PROVISION",
                            "Trích lập/(Hoàn nhập) dự phòng trong năm",
                            [56],
                            57,
                            "852.382",
                        ),
                        _row(
                            "USE",
                            "Sử dụng dự phòng rủi ro tín dụng trong năm",
                            [61],
                            None,
                            "-",
                            hdb_prior_general_dash,
                        ),
                        _row("CLOSING", "Tại ngày 31 tháng 12 năm 2025", [64], 65, "4.069.255"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-12-31",
                    "SPECIFIC",
                    28,
                    [
                        _row("OPENING", "Tại ngày 01 tháng 01 năm 2025", [51], 53, "2.577.890"),
                        _row(
                            "PROVISION",
                            "Trích lập/(Hoàn nhập) dự phòng trong năm",
                            [56],
                            58,
                            "8.806.336",
                        ),
                        _row(
                            "USE",
                            "Sử dụng dự phòng rủi ro tín dụng trong năm",
                            [61],
                            62,
                            "(8.154.036)",
                        ),
                        _row("CLOSING", "Tại ngày 31 tháng 12 năm 2025", [64], 66, "3.230.190"),
                    ],
                ),
            ],
            ["DEFERRED_LC_GENERAL", "DEFERRED_LC_SPECIFIC", "OVERALL_COMBINED"],
        ),
        _document(
            "VCB",
            [31],
            [
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "GENERAL",
                    31,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [50], 51, "12.422.684"),
                        _row("PROVISION", "Trích lập dự phòng", [53], 54, "588.311"),
                        _row("FX", "Chênh lệch tỷ giá", [56], 57, "(171)"),
                        _row("CLOSING", "Số dư cuối kỳ", [61], 62, "13.010.824"),
                    ],
                ),
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "SPECIFIC",
                    31,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [76], 77, "12.552.995"),
                        _row(
                            "PROVISION",
                            "Trích lập/(Hoàn nhập) dự phòng",
                            [81],
                            79,
                            "4.420.733",
                        ),
                        _row(
                            "USE",
                            "Xử lý các khoản nợ xấu bằng nguồn dự phòng",
                            [83],
                            None,
                            "-",
                            vcb_current_specific_dash,
                        ),
                        _row("FX", "Chênh lệch tỷ giá", [86], 84, "143"),
                        _row("CLOSING", "Số dư cuối kỳ", [87], 88, "16.973.871"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-12-31",
                    "GENERAL",
                    31,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [50], 52, "10.687.999"),
                        _row("PROVISION", "Trích lập dự phòng", [53], 55, "1.733.057"),
                        _row("FX", "Chênh lệch tỷ giá", [56], 58, "1.628"),
                        _row("CLOSING", "Số dư cuối kỳ", [61], 63, "12.422.684"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-12-31",
                    "SPECIFIC",
                    31,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [76], 78, "20.495.176"),
                        _row(
                            "PROVISION",
                            "Trích lập/(Hoàn nhập) dự phòng",
                            [81],
                            80,
                            "(656.394)",
                        ),
                        _row(
                            "USE",
                            "Xử lý các khoản nợ xấu bằng nguồn dự phòng",
                            [83],
                            82,
                            "(7.287.783)",
                        ),
                        _row("FX", "Chênh lệch tỷ giá", [86], 85, "1.996"),
                        _row("CLOSING", "Số dư cuối kỳ", [87], 89, "12.552.995"),
                    ],
                ),
            ],
            ["SUMMARY_COMBINED_TOTAL"],
        ),
        _document(
            "CTG",
            [39],
            [
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "GENERAL",
                    39,
                    [
                        _row("OPENING", "Số dư đầu năm (01/01/2026)", [50], 51, "14.817.251"),
                        _row(
                            "PROVISION",
                            "Dự phòng rủi ro trích lập trong năm",
                            [54],
                            55,
                            "760.240",
                        ),
                        _row(
                            "USE",
                            "Sử dụng dự phòng rủi ro tín dụng trong năm",
                            [58],
                            None,
                            "-",
                            ctg_current_general_dash,
                        ),
                        _row("CLOSING", "Số dư cuối kỳ (30/06/2026)", [61], 62, "15.577.491"),
                    ],
                ),
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "SPECIFIC",
                    39,
                    [
                        _row("OPENING", "Số dư đầu năm (01/01/2026)", [50], 52, "19.993.114"),
                        _row(
                            "PROVISION",
                            "Dự phòng rủi ro trích lập trong năm",
                            [54],
                            56,
                            "12.213.789",
                        ),
                        _row(
                            "USE",
                            "Sử dụng dự phòng rủi ro tín dụng trong năm",
                            [58],
                            59,
                            "(14.189.942)",
                        ),
                        _row("CLOSING", "Số dư cuối kỳ (30/06/2026)", [61], 63, "18.016.961"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-06-30",
                    "GENERAL",
                    39,
                    [
                        _row("OPENING", "Số dư đầu kỳ (01/01/2025)", [72], 73, "12.782.431"),
                        _row(
                            "PROVISION",
                            "Dự phòng rủi ro trích lập trong năm",
                            [76],
                            77,
                            "1.387.561",
                        ),
                        _row(
                            "USE",
                            "Sử dụng dự phòng rủi ro tín dụng trong năm",
                            [80],
                            None,
                            "-",
                            ctg_prior_general_dash,
                        ),
                        _row("CLOSING", "Số dư cuối kỳ (30/06/2025)", [83], 84, "14.169.992"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-06-30",
                    "SPECIFIC",
                    39,
                    [
                        _row("OPENING", "Số dư đầu kỳ (01/01/2025)", [72], 74, "23.881.694"),
                        _row(
                            "PROVISION",
                            "Dự phòng rủi ro trích lập trong năm",
                            [76],
                            78,
                            "9.682.011",
                        ),
                        _row(
                            "USE",
                            "Sử dụng dự phòng rủi ro tín dụng trong năm",
                            [80],
                            81,
                            "(14.296.266)",
                        ),
                        _row("CLOSING", "Số dư cuối kỳ (30/06/2025)", [83], 85, "19.267.439"),
                    ],
                ),
            ],
            ["OVERALL_COMBINED"],
        ),
        _document(
            "BID",
            [23],
            [
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "GENERAL",
                    23,
                    [
                        _row("OPENING", "Tại 01/01/2026", [8], 9, "17,577,903"),
                        _row("PROVISION", "Số trích lập/hoàn nhập", [11], 12, "949,411"),
                        _row(
                            "USE",
                            "Dự phòng giảm do xử lý các khoản nợ khó thu hồi bằng nguồn dự phòng",
                            [14, 16],
                            None,
                            "-",
                            bid_current_general_dash,
                        ),
                        _row("OTHER", "Giảm khác", [17], 18, "(1,712)"),
                        _row("CLOSING", "Tại 30/06/2026", [20], 21, "18,525,602"),
                    ],
                ),
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "SPECIFIC",
                    23,
                    [
                        _row("OPENING", "Tại 01/01/2026", [8], 10, "17,367,650"),
                        _row("PROVISION", "Số trích lập/hoàn nhập", [11], 13, "10,361,887"),
                        _row(
                            "USE",
                            "Dự phòng giảm do xử lý các khoản nợ khó thu hồi bằng nguồn dự phòng",
                            [14, 16],
                            15,
                            "(11,565,551)",
                        ),
                        _row("OTHER", "Giảm khác", [17], 19, "5,136"),
                        _row("CLOSING", "Tại 30/06/2026", [20], 22, "16,169,122"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-06-30",
                    "GENERAL",
                    23,
                    [
                        _row("OPENING", "Tại 01/01/2025", [23], 24, "15,257,425"),
                        _row("PROVISION", "Số trích lập/hoàn nhập", [26], 27, "849,141"),
                        _row(
                            "USE",
                            "Dự phòng giảm do xử lý các khoản nợ khó thu hồi bằng nguồn dự phòng",
                            [29, 31],
                            None,
                            "-",
                            bid_prior_general_dash,
                        ),
                        _row("OTHER", "Tăng khác", [32], 33, "13,017"),
                        _row("CLOSING", "Tại 30/06/2025", [35], 36, "16,119,583"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-06-30",
                    "SPECIFIC",
                    23,
                    [
                        _row("OPENING", "Tại 01/01/2025", [23], 25, "22,781,346"),
                        _row("PROVISION", "Số trích lập/hoàn nhập", [26], 28, "9,805,315"),
                        _row(
                            "USE",
                            "Dự phòng giảm do xử lý các khoản nợ khó thu hồi bằng nguồn dự phòng",
                            [29, 31],
                            30,
                            "(10,316,604)",
                        ),
                        _row("OTHER", "Tăng khác", [32], 34, "46,163"),
                        _row("CLOSING", "Tại 30/06/2025", [35], 37, "22,316,220"),
                    ],
                ),
            ],
            [],
        ),
        _document(
            "VIB",
            [34, 35],
            [
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "GENERAL",
                    34,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [89], 90, "2.817.081"),
                        _row("PROVISION", "Trích lập dự phòng trong kỳ", [93], 94, "117.980"),
                        _row(
                            "USE",
                            "Sử dụng dự phòng rủi ro tín dụng trong kỳ",
                            [97],
                            None,
                            "-",
                            vib_current_general_dash,
                        ),
                        _row("CLOSING", "Số dư cuối kỳ", [100], 101, "2.935.061"),
                    ],
                ),
                _series(
                    "2026-01-01_TO_2026-06-30",
                    "SPECIFIC",
                    34,
                    [
                        _row("OPENING", "Số dư đầu kỳ", [89], 91, "2.041.740"),
                        _row("PROVISION", "Trích lập dự phòng trong kỳ", [93], 95, "2.367.883"),
                        _row(
                            "USE",
                            "Sử dụng dự phòng rủi ro tín dụng trong kỳ",
                            [97],
                            98,
                            "(2.281.670)",
                        ),
                        _row("CLOSING", "Số dư cuối kỳ", [100], 102, "2.127.953"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-12-31",
                    "GENERAL",
                    35,
                    [
                        _row("OPENING", "Số dư đầu năm", [16], 17, "2.382.092"),
                        _row("PROVISION", "Trích lập dự phòng trong năm", [21], 22, "434.989"),
                        _row(
                            "USE",
                            "Sử dụng dự phòng rủi ro tín dụng trong năm",
                            [25],
                            None,
                            "-",
                            vib_prior_general_dash,
                        ),
                        _row("CLOSING", "Số dư cuối năm", [28], 29, "2.817.081"),
                    ],
                ),
                _series(
                    "2025-01-01_TO_2025-12-31",
                    "SPECIFIC",
                    35,
                    [
                        _row("OPENING", "Số dư đầu năm", [16], 18, "3.311.542"),
                        _row("PROVISION", "Trích lập dự phòng trong năm", [21], 23, "3.032.307"),
                        _row(
                            "USE",
                            "Sử dụng dự phòng rủi ro tín dụng trong năm",
                            [25],
                            26,
                            "(4.302.109)",
                        ),
                        _row("CLOSING", "Số dư cuối năm", [28], 30, "2.041.740"),
                    ],
                ),
            ],
            ["OVERALL_COMBINED"],
        ),
    ]
    material = {
        "claim_boundary": (
            "Independent visible-PDF review of every unique eight-bank customer-loan provision "
            "movement region, general/specific lane, visible dash, and accounting equation; "
            "source-only auxiliary lanes are retained without additive mapping."
        ),
        "documents": documents,
        "format_version": REVIEW_FORMAT,
        "review_checks": canonical_clone_v1(_REVIEW_CHECKS),
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_PDF_PIXEL_REVIEW",
            "review_run_id": "E-0057-2026-08-14-visible-pdf-review-v1",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "scan_id": EXPECTED_SCAN_ID,
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }
    return {**material, "review_id": "e0057:pixel-review:" + canonical_json_sha256_v1(material)}


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("Codex provision pixel review differs from the fixed reviewed ledger")
    return canonical_clone_v1(expected)


def _artifact_bytes(reference: Any, label: str) -> bytes:
    if (
        type(reference) is not dict
        or set(reference) != {"path", "sha256", "size_bytes"}
        or type(reference["path"]) is not str
        or type(reference["size_bytes"]) is not int
        or reference["size_bytes"] < 0
    ):
        raise _error(f"{label} reference fields drifted")
    digest = _sha256(reference["sha256"], f"{label} reference")
    payload = _stable_bytes(Path(reference["path"]))
    if len(payload) != reference["size_bytes"] or hashlib.sha256(payload).hexdigest() != digest:
        raise _error(f"{label} bytes drifted")
    return payload


def _json_payload(payload: bytes, label: str) -> dict[str, Any]:
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


def _page_by_number(document: Mapping[str, Any], physical_page: int, label: str) -> dict[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error(f"{label} page axis drifted")
    matches = [
        page
        for page in pages
        if type(page) is dict
        and page.get("physical_page", page.get("page_sequence")) == physical_page
    ]
    if len(matches) != 1:
        raise _error(f"{label} does not contain physical page {physical_page}")
    return matches[0]


def _source_line_axis(page: Mapping[str, Any]) -> list[str]:
    result = _json_payload(_artifact_bytes(page.get("result_ref"), "page result"), "page result")
    lines = result.get("lines")
    if type(lines) is list and lines:
        if len(lines) != page.get("primary_line_count"):
            raise _error("page result primary line denominator drifted")
        texts: list[str] = []
        for line in lines:
            if type(line) is not dict or type(line.get("raw_text")) is not str:
                raise _error("page result source line text drifted")
            texts.append(line["raw_text"])
        return texts
    backend = _json_payload(
        _artifact_bytes(page.get("backend_ref"), "page backend"), "page backend"
    )
    raw = backend.get("raw_provider_payload")
    texts = raw.get("rec_texts") if type(raw) is dict else None
    if (
        type(texts) is not list
        or len(texts) != page.get("supplement_line_count")
        or not all(type(text) is str for text in texts)
    ):
        raise _error("terminal backend recognition challenger axis drifted")
    return list(texts)


def _render_bytes(document: Mapping[str, Any], page: Mapping[str, Any]) -> bytes:
    binding = page.get("render_binding")
    if type(binding) is not dict:
        raise _error("page render binding drifted")
    if "path" in binding:
        return _artifact_bytes(binding, "page render")
    required = {
        "dpi",
        "origin",
        "pixel_height",
        "pixel_width",
        "render_profile",
        "sha256",
        "size_bytes",
        "upstream_render_ref",
    }
    if (
        set(binding) != required
        or binding["origin"] != "DETERMINISTIC_SOURCE_REPLAY_FOR_NATIVE_GEOMETRY"
        or binding["upstream_render_ref"] is not None
        or type(binding["dpi"]) is not int
        or binding["dpi"] not in {200, 300}
    ):
        raise _error("native deterministic render binding drifted")
    source_payload = _artifact_bytes(document.get("source_pdf"), "source PDF")
    try:
        pdf = fitz.open(stream=source_payload, filetype="pdf")
    except (RuntimeError, ValueError, TypeError) as exc:
        raise _error("source PDF cannot be rendered") from exc
    try:
        physical_page = page.get("physical_page")
        if type(physical_page) is not int or not 1 <= physical_page <= pdf.page_count:
            raise _error("native physical page drifted")
        first = render_composited_displayed_page(
            pdf.load_page(physical_page - 1), dpi=binding["dpi"]
        )
        second = render_composited_displayed_page(
            pdf.load_page(physical_page - 1), dpi=binding["dpi"]
        )
    finally:
        pdf.close()
    if (
        first.payload != second.payload
        or first.sha256 != binding["sha256"]
        or first.size_bytes != binding["size_bytes"]
        or first.pixel_width != binding["pixel_width"]
        or first.pixel_height != binding["pixel_height"]
    ):
        raise _error("native deterministic render replay drifted")
    return first.payload


def _verify_pixel_binding(binding: Any, render_payload: bytes) -> None:
    if (
        type(binding) is not dict
        or set(binding) != {"bbox_raw_pixels", "rgb_sha256"}
        or type(binding["bbox_raw_pixels"]) is not list
        or len(binding["bbox_raw_pixels"]) != 4
        or not all(type(value) is int for value in binding["bbox_raw_pixels"])
    ):
        raise _error("visible pixel binding fields drifted")
    expected = _sha256(binding["rgb_sha256"], "visible pixel binding")
    try:
        with Image.open(BytesIO(render_payload)) as image:
            rgb = image.convert("RGB")
            x0, y0, x1, y1 = binding["bbox_raw_pixels"]
            if not (0 <= x0 < x1 <= rgb.width and 0 <= y0 < y1 <= rgb.height):
                raise _error("visible pixel binding is outside the authenticated render")
            actual = hashlib.sha256(rgb.crop((x0, y0, x1, y1)).tobytes()).hexdigest()
    except (OSError, ValueError) as exc:
        if isinstance(exc, ProvisionMovement8BankCodexVerifiedMappingV1Error):
            raise
        raise _error("authenticated render is not a readable image") from exc
    if actual != expected:
        raise _error("visible pixel crop content drifted")


_MONEY = re.compile(r"^[+-]?[0-9][0-9.,]*$")


def _money(value: Any) -> int:
    if type(value) is not str or not value.strip() or value != value.strip():
        raise _error("visible numeric transcription is invalid")
    if value == "-":
        return 0
    negative = value.startswith("(") and value.endswith(")")
    token = value[1:-1] if negative else value
    if _MONEY.fullmatch(token) is None:
        raise _error(f"visible numeric transcription is unsupported: {value!r}")
    digits = token.replace(".", "").replace(",", "")
    if not digits.isdigit():
        raise _error("visible numeric digits drifted")
    numeric = int(digits)
    return -numeric if negative else numeric


def _axis_line(page: Mapping[str, Any], line_index: int) -> dict[str, Any]:
    lines = page.get("lines")
    if type(lines) is not list or not 0 <= line_index < len(lines):
        raise _error("fresh VietOCR semantic line index drifted")
    line = lines[line_index]
    if (
        type(line) is not dict
        or line.get("source_line_index") != line_index
        or type(line.get("vietocr_text")) is not str
        or type(line.get("vietocr_text_accentless")) is not str
    ):
        raise _error("fresh VietOCR semantic line identity drifted")
    return line


def _event_for_row(
    graph: Mapping[str, Any], physical_page: int, role: str, label_lines: Sequence[int]
) -> dict[str, Any]:
    page_records = graph.get("page_records")
    if type(page_records) is not list:
        raise _error("provision graph page records drifted")
    records = [item for item in page_records if item.get("page_sequence") == physical_page]
    if len(records) != 1:
        raise _error("provision graph does not bind the reviewed physical page")
    candidates = [
        event
        for event in records[0].get("events", [])
        if event.get("role") == role and set(event.get("label_line_indices", [])) & set(label_lines)
    ]
    if len(candidates) != 1:
        raise _error("reviewed movement row is not uniquely bound to the structural graph")
    return candidates[0]


def _layout_variant(series: Sequence[Mapping[str, Any]]) -> str:
    signatures = [
        tuple((row["role"], tuple(row["label_line_indices"])) for row in lane["rows"])
        for lane in series
    ]
    if signatures and all(signature == signatures[0] for signature in signatures[1:]):
        return "HORIZONTAL_SHARED_ROLE_ROWS_WITH_PARALLEL_PROVISION_LANES"
    intervals = sorted(
        (
            min(index for row in lane["rows"] for index in row["label_line_indices"]),
            max(index for row in lane["rows"] for index in row["label_line_indices"]),
        )
        for lane in series
    )
    if all(left[1] < right[0] for left, right in zip(intervals, intervals[1:], strict=False)):
        return "VERTICAL_STACKED_PROVISION_LANE_BLOCKS"
    return "MIXED_HORIZONTAL_VERTICAL_PROVISION_LANE_BLOCKS"


def _cluster_boundary(document: Mapping[str, Any], graph: Mapping[str, Any]) -> dict[str, Any]:
    by_page: dict[int, list[tuple[str, str, int]]] = {}
    for lane in document["series"]:
        for row in lane["rows"]:
            indices = [*row["label_line_indices"]]
            if row["value_line_index"] is not None:
                indices.append(row["value_line_index"])
            by_page.setdefault(lane["physical_page"], []).extend(
                (lane["lane"], row["role"], index) for index in indices
            )
    page_records = {item["page_sequence"]: item for item in graph["page_records"]}
    boundaries: list[dict[str, Any]] = []
    for physical_page in sorted(by_page):
        entries = by_page[physical_page]
        first = min(index for _, _, index in entries)
        last = max(index for _, _, index in entries)
        record = page_records.get(physical_page)
        if type(record) is not dict or type(record.get("root")) is not dict:
            raise _error("cluster root anchor is absent from the structural graph")
        start_items = sorted({f"{lane}:{role}" for lane, role, index in entries if index == first})
        end_items = sorted({f"{lane}:{role}" for lane, role, index in entries if index == last})
        boundaries.append(
            {
                "continuation": record.get("continuation") is True,
                "first_boundary_items": start_items,
                "first_line_index": first,
                "last_boundary_items": end_items,
                "last_line_index": last,
                "physical_page": physical_page,
                "root_anchor_line_index": record["root"].get("source_line_index"),
                "root_anchor_vietocr_text": record["root"].get("vietocr_text"),
            }
        )
    return {
        "comparison_page_sequences_excluded_from_mapping": [
            page for page in document["page_sequences"] if page not in by_page
        ],
        "current_period_page_boundaries": boundaries,
        "selection_rule": ("ROOT_ANCHOR_THEN_FIRST_OPENING_THROUGH_LAST_CLOSING_IN_PDF_ORDER"),
    }


def _schema_bindings(
    schema_authority: Mapping[str, Any], schema_by_id: Mapping[int, Any]
) -> dict[int, dict[str, Any]]:
    if (
        schema_authority.get("schema_revision") != "UNIVERSAL_BANK_BCTC_SCHEMA@6068"
        or schema_authority.get("tm_item_count") != 1713
    ):
        raise _error("live TM schema authority revision drifted")
    expected_parents = {
        783: 560,
        784: 783,
        **{identifier: 784 for identifier in range(785, 792)},
        792: 783,
        **{identifier: 792 for identifier in range(793, 800)},
        6061: 783,
        **{identifier: 6061 for identifier in range(6062, 6066)},
    }
    bound: dict[int, dict[str, Any]] = {}
    for identifier, expected_name in _SCHEMA_NAMES.items():
        item = schema_by_id.get(identifier)
        if (
            item is None
            or item.canonical_name != expected_name
            or item.statement_type != "TM"
            or item.parent_id != expected_parents[identifier]
            or type(item.display_order) is not int
            or item.hierarchy_level
            != (1 if identifier == 783 else 2 if identifier in {784, 792, 6061} else 3)
        ):
            raise _error(f"live TM provision schema identity drifted for {identifier}")
        bound[identifier] = {
            "canonical_name": item.canonical_name,
            "display_order": item.display_order,
            "hierarchy_level": item.hierarchy_level,
            "report_norm_id": identifier,
            "schema_parent_report_norm_id": item.parent_id,
        }
    if (
        schema_by_id[783].children != [784, 792, 6061]
        or schema_by_id[784].children != list(range(785, 792))
        or schema_by_id[792].children != list(range(793, 800))
        or schema_by_id[6061].children != list(range(6062, 6066))
    ):
        raise _error("live TM provision schema child order drifted")
    return bound


def _selected_axis(graph: Mapping[str, Any], document: Mapping[str, Any]) -> dict[str, Any]:
    header_roles = [item.get("header_role") for item in graph.get("headers", [])]
    has_geographic = any(role in {"TAI_VIET_NAM", "TAI_NUOC_NGOAI"} for role in header_roles)
    has_total = "TONG_CONG" in header_roles
    return {
        "comparison_periods_excluded": canonical_clone_v1(
            document["comparison_periods_excluded_from_mapping"]
        ),
        "excluded_auxiliary_lanes": canonical_clone_v1(document["source_only_auxiliary_lanes"]),
        "observed_header_roles": header_roles,
        "period_scope": "CURRENT_PERIOD_IN_SUPPLIED_REPORT_ONLY",
        "value_axis": (
            "OVERALL_TOTAL_ONLY_GEOGRAPHIC_SUBCOLUMNS_EXCLUDED"
            if has_geographic and has_total
            else "GENERAL_SPECIFIC_AND_SEPARATELY_MEANINGFUL_PROVISION_LANES"
        ),
    }


def _period_status(period: str) -> str:
    if period.endswith("2026-06-30"):
        return "VERIFIED_SOURCE_PERIOD_Q2_2026"
    if period.endswith("2026-03-31"):
        return "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
    raise _error("reviewed current source period is unsupported")


def build_provision_movement_8bank_codex_verified_mapping_v1(
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
    """Build the exact eight-bank current-period provision mapping result."""

    review = _review(review_value)
    _sha256(crop_manifest_sha256, "crop manifest")
    _sha256(review_sha256, "Codex pixel review")
    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if (
        axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or structure_scan.get("state") != "FULL_DOCUMENT_PROVISION_MOVEMENT_STRUCTURE_SCAN_COMPLETE"
        or type(structure_scan.get("trials")) is not list
        or len(structure_scan["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
        or type(crop_manifest) is not dict
        or type(crop_manifest.get("documents")) is not list
    ):
        raise _error("full-document provision input authority drifted")
    schema = _schema_bindings(schema_authority, schema_by_id)
    trials: list[dict[str, Any]] = []
    for ordinal, code in enumerate(EXPECTED_DOCUMENT_ORDER, 1):
        review_document = _document_by_code(review["documents"], code, "pixel review")
        crop_document = _document_by_code(crop_manifest["documents"], code, "crop manifest")
        axis_document = _document_by_code(axis["documents"], code, "fresh VietOCR axis")
        scan_trial = _document_by_code(structure_scan["trials"], code, "structure scan")
        if (
            scan_trial.get("document_ordinal") != ordinal
            or scan_trial.get("source_pdf_sha256") != crop_document["source_pdf"]["sha256"]
        ):
            raise _error("structure scan document identity/order drifted")
        matcher = scan_trial.get("matcher_result")
        if (
            type(matcher) is not dict
            or matcher.get("status") != "ACCEPTED_UNIQUE_VARIANT_GRAPH"
            or matcher.get("uniqueness") != {"full_match_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or type(matcher.get("graphs")) is not list
            or len(matcher["graphs"]) != 1
        ):
            raise _error("whole-PDF provision region is not exactly unique")
        graph = matcher["graphs"][0]
        if (
            graph.get("status") != "STRUCTURALLY_COMPLETE_PROVISION_MOVEMENT_REGION"
            or graph.get("page_sequences") != review_document["page_sequences"]
        ):
            raise _error("reviewed provision region and complete-PDF graph disagree")

        lane_results: list[dict[str, Any]] = []
        semantic_evidence: list[dict[str, Any]] = []
        for lane in review_document["series"]:
            lane_name = lane.get("lane")
            if lane_name not in _LANE_PARENT or lane.get("period", "").startswith("2026-") is False:
                raise _error("reviewed current provision lane identity drifted")
            rows = lane.get("rows")
            if (
                type(rows) is not list
                or not _REQUIRED_ROLES <= {row.get("role") for row in rows}
                or rows[0].get("role") != "OPENING"
                or rows[-1].get("role") != "CLOSING"
            ):
                raise _error(
                    "reviewed provision lane lacks its core opening/movement/closing order"
                )
            role_positions = [_ROLE_ORDER.index(row["role"]) for row in rows]
            if role_positions != sorted(role_positions) or len(set(role_positions)) != len(rows):
                raise _error("reviewed provision movement roles are reordered or duplicated")
            physical_page = lane.get("physical_page")
            crop_page = _page_by_number(crop_document, physical_page, "crop manifest")
            axis_page = _page_by_number(axis_document, physical_page, "fresh VietOCR axis")
            source_texts = _source_line_axis(crop_page)
            render_payload: bytes | None = None
            mapped_rows: list[dict[str, Any]] = []
            parsed: dict[str, int] = {}
            for row in rows:
                role = row["role"]
                if role not in _ROLE_IDS[lane_name]:
                    raise _error("reviewed provision role has no lane-specific schema identity")
                event = _event_for_row(graph, physical_page, role, row["label_line_indices"])
                labels = [_axis_line(axis_page, index) for index in row["label_line_indices"]]
                semantic_evidence.append(
                    {
                        "label_line_indices": canonical_clone_v1(row["label_line_indices"]),
                        "lane": lane_name,
                        "normalized_anchor": normalize_vietnamese_anchor_v1(
                            " ".join(item["vietocr_text"] for item in labels)
                        ),
                        "physical_page": physical_page,
                        "role": role,
                        "structural_event_vietocr_label": event["vietocr_label"],
                        "vietocr_transformer_text": [item["vietocr_text"] for item in labels],
                    }
                )
                pixel_binding = row.get("pixel_binding")
                if pixel_binding is not None:
                    if render_payload is None:
                        render_payload = _render_bytes(crop_document, crop_page)
                    _verify_pixel_binding(pixel_binding, render_payload)
                numeric = _money(row["pixel_value_transcription"])
                value_line_index = row["value_line_index"]
                if value_line_index is None:
                    if row["pixel_value_transcription"] != "-" or pixel_binding is None:
                        raise _error(
                            "missing source line is not an independently bound visible dash"
                        )
                    challenger = {
                        "raw_text": None,
                        "source_line_index": None,
                        "status": "VISIBLE_PIXEL_DASH_WITH_NO_SOURCE_TEXT_LINE",
                    }
                else:
                    if type(value_line_index) is not int or not 0 <= value_line_index < len(
                        source_texts
                    ):
                        raise _error("numeric challenger source line index drifted")
                    raw_source = source_texts[value_line_index]
                    try:
                        source_numeric = _money(raw_source)
                    except ProvisionMovement8BankCodexVerifiedMappingV1Error:
                        source_numeric = None
                    if source_numeric == numeric:
                        challenger_status = "UPSTREAM_NUMERIC_CHALLENGER_MATCHED_VISIBLE_PIXEL"
                    elif (
                        numeric == 0
                        and row["pixel_value_transcription"] == "-"
                        and pixel_binding is not None
                    ):
                        challenger_status = "UPSTREAM_GLYPH_DISAGREES_VISIBLE_PIXEL_DASH_VERIFIED"
                    else:
                        raise _error("visible numeric value and upstream challenger disagree")
                    challenger = {
                        "raw_text": raw_source,
                        "source_line_index": value_line_index,
                        "status": challenger_status,
                    }
                identifier = _ROLE_IDS[lane_name][role]
                parsed[role] = numeric
                mapped_rows.append(
                    {
                        **canonical_clone_v1(schema[identifier]),
                        "independent_pixel_label": row["label_pixel_transcription"],
                        "pixel_binding": canonical_clone_v1(pixel_binding),
                        "pixel_value_transcription": row["pixel_value_transcription"],
                        "normalized_value": numeric,
                        "role": role,
                        "source_numeric_challenger": challenger,
                        "status": "VERIFIED_BY_CODEX",
                    }
                )
            computed = parsed["OPENING"] + sum(
                value for role, value in parsed.items() if role not in {"OPENING", "CLOSING"}
            )
            if computed != parsed["CLOSING"]:
                raise _error("reviewed provision movement accounting equation does not close")
            parent_id = _LANE_PARENT[lane_name]
            lane_results.append(
                {
                    "accounting_check": {
                        "computed_closing": computed,
                        "printed_closing": parsed["CLOSING"],
                        "status": "CORROBORATED_EXACT",
                    },
                    "lane": lane_name,
                    "parent_mapping": {
                        **canonical_clone_v1(schema[parent_id]),
                        "status": "VERIFIED_BY_CODEX",
                    },
                    "period": lane["period"],
                    "physical_page": physical_page,
                    "rows": mapped_rows,
                    "source_period_status": _period_status(lane["period"]),
                }
            )
        source_period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if any(
                lane["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                for lane in lane_results
            )
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        trials.append(
            {
                "cluster_boundary": _cluster_boundary(review_document, graph),
                "document_ordinal": ordinal,
                "document_provenance": code,
                "layout_variant": _layout_variant(review_document["series"]),
                "selected_axes": _selected_axis(graph, review_document),
                "source_only_auxiliary_lanes": canonical_clone_v1(
                    review_document["source_only_auxiliary_lanes"]
                ),
                "source_pdf_sha256": crop_document["source_pdf"]["sha256"],
                "source_period_status": source_period_status,
                "status": (
                    "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT"
                    if source_period_status == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                    else "VERIFIED_BY_CODEX"
                ),
                "transformer_semantic_evidence": semantic_evidence,
                "verified_lane_mappings": lane_results,
                "whole_document_family_absence_claim": False,
                "whole_document_uniqueness": canonical_clone_v1(matcher["uniqueness"]),
            }
        )

    metrics = {
        "accounting_equation_verified_count": sum(
            len(trial["verified_lane_mappings"]) for trial in trials
        ),
        "current_period_lane_parent_verified_count": sum(
            len(trial["verified_lane_mappings"]) for trial in trials
        ),
        "current_period_role_mapping_verified_count": sum(
            len(lane["rows"]) for trial in trials for lane in trial["verified_lane_mappings"]
        ),
        "document_count": len(trials),
        "document_unique_region_count": sum(
            trial["whole_document_uniqueness"]["full_match_count"] == 1 for trial in trials
        ),
        "q1_source_period_caveat_document_count": sum(
            trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            for trial in trials
        ),
        "visible_dash_verified_as_zero_count": sum(
            row["pixel_value_transcription"] == "-"
            for trial in trials
            for lane in trial["verified_lane_mappings"]
            for row in lane["rows"]
        ),
    }
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "codex_pixel_review": {
                "path": REVIEW_PATH.as_posix(),
                "sha256": review_sha256,
            },
            "crop_manifest_sha256": crop_manifest_sha256,
            "semantic_axis_sha256": axis["semantic_axis_sha256"],
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": structure_scan["scan_id"],
            "tm_schema_authority": canonical_clone_v1(schema_authority),
        },
        "metrics": metrics,
        "state": "PROVISION_MOVEMENT_8BANK_BOUNDED_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {**material, "result_id": "pm8bcv1:result:" + canonical_json_sha256_v1(material)}
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _RESULT_FIELDS:
        raise _error("verified provision result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "PROVISION_MOVEMENT_8BANK_BOUNDED_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["input_refs"]) is not dict
        or type(value["metrics"]) is not dict
        or type(value["trials"]) is not list
        or len(value["trials"]) != len(EXPECTED_DOCUMENT_ORDER)
    ):
        raise _error("verified provision result identity/authority drifted")
    refs = value["input_refs"]
    if (
        set(refs)
        != {
            "codex_pixel_review",
            "crop_manifest_sha256",
            "semantic_axis_sha256",
            "semantic_index_sha256",
            "structure_scan_id",
            "tm_schema_authority",
        }
        or refs["codex_pixel_review"] != {"path": REVIEW_PATH.as_posix(), "sha256": REVIEW_SHA256}
        or refs["crop_manifest_sha256"] != EXPECTED_CROP_MANIFEST_SHA256
        or refs["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256
        or refs["semantic_index_sha256"] != EXPECTED_INDEX_SHA256
        or refs["structure_scan_id"] != EXPECTED_SCAN_ID
    ):
        raise _error("verified provision input identities drifted")
    clone = canonical_clone_v1(value)
    result_id = clone.pop("result_id")
    if result_id != "pm8bcv1:result:" + canonical_json_sha256_v1(clone):
        raise _error("verified provision result content identity drifted")
    lane_count = row_count = equation_count = dash_count = q1_count = unique_count = 0
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        expected_fields = {
            "cluster_boundary",
            "document_ordinal",
            "document_provenance",
            "layout_variant",
            "selected_axes",
            "source_only_auxiliary_lanes",
            "source_pdf_sha256",
            "source_period_status",
            "status",
            "transformer_semantic_evidence",
            "verified_lane_mappings",
            "whole_document_family_absence_claim",
            "whole_document_uniqueness",
        }
        if (
            type(trial) is not dict
            or set(trial) != expected_fields
            or trial["document_ordinal"] != ordinal
            or trial["document_provenance"] != code
            or trial["whole_document_family_absence_claim"] is not False
            or trial["layout_variant"]
            not in {
                "HORIZONTAL_SHARED_ROLE_ROWS_WITH_PARALLEL_PROVISION_LANES",
                "VERTICAL_STACKED_PROVISION_LANE_BLOCKS",
                "MIXED_HORIZONTAL_VERTICAL_PROVISION_LANE_BLOCKS",
            }
            or trial["whole_document_uniqueness"]
            != {"full_match_count": 1, "status": "UNIQUE_FULL_MATCH"}
            or type(trial["verified_lane_mappings"]) is not list
            or not trial["verified_lane_mappings"]
        ):
            raise _error("verified provision trial shape/order drifted")
        _sha256(trial["source_pdf_sha256"], "verified source PDF")
        unique_count += 1
        if trial["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2":
            q1_count += 1
            if trial["status"] != "VERIFIED_BY_CODEX_WITH_SUPPLIED_SOURCE_PERIOD_CAVEAT":
                raise _error("Q1 source-period caveat was not preserved")
        elif (
            trial["source_period_status"] != "VERIFIED_SOURCE_PERIOD_Q2_2026"
            or trial["status"] != "VERIFIED_BY_CODEX"
        ):
            raise _error("verified source-period status drifted")
        seen_lanes: set[str] = set()
        for lane in trial["verified_lane_mappings"]:
            if (
                type(lane) is not dict
                or set(lane)
                != {
                    "accounting_check",
                    "lane",
                    "parent_mapping",
                    "period",
                    "physical_page",
                    "rows",
                    "source_period_status",
                }
                or lane["lane"] not in _LANE_PARENT
                or lane["lane"] in seen_lanes
                or lane["parent_mapping"].get("report_norm_id") != _LANE_PARENT[lane["lane"]]
                or lane["parent_mapping"].get("status") != "VERIFIED_BY_CODEX"
                or lane["accounting_check"].get("status") != "CORROBORATED_EXACT"
                or lane["accounting_check"].get("computed_closing")
                != lane["accounting_check"].get("printed_closing")
                or type(lane["rows"]) is not list
            ):
                raise _error("verified provision lane mapping drifted")
            seen_lanes.add(lane["lane"])
            lane_count += 1
            equation_count += 1
            parsed_roles: dict[str, int] = {}
            row_roles: list[str] = []
            for row in lane["rows"]:
                expected_row_fields = {
                    "canonical_name",
                    "display_order",
                    "hierarchy_level",
                    "independent_pixel_label",
                    "normalized_value",
                    "pixel_binding",
                    "pixel_value_transcription",
                    "report_norm_id",
                    "role",
                    "schema_parent_report_norm_id",
                    "source_numeric_challenger",
                    "status",
                }
                if (
                    type(row) is not dict
                    or set(row) != expected_row_fields
                    or row.get("status") != "VERIFIED_BY_CODEX"
                    or row.get("role") not in _ROLE_IDS[lane["lane"]]
                    or row.get("report_norm_id") != _ROLE_IDS[lane["lane"]][row["role"]]
                    or row.get("schema_parent_report_norm_id") != _LANE_PARENT[lane["lane"]]
                    or type(row.get("display_order")) is not int
                    or row.get("hierarchy_level") != 3
                    or type(row.get("independent_pixel_label")) is not str
                    or not row["independent_pixel_label"]
                    or type(row.get("pixel_value_transcription")) is not str
                    or type(row.get("normalized_value")) is not int
                    or _money(row["pixel_value_transcription"]) != row["normalized_value"]
                    or type(row.get("source_numeric_challenger")) is not dict
                    or set(row["source_numeric_challenger"])
                    != {"raw_text", "source_line_index", "status"}
                ):
                    raise _error("verified provision role mapping drifted")
                row_roles.append(row["role"])
                parsed_roles[row["role"]] = row["normalized_value"]
                row_count += 1
                if row.get("pixel_value_transcription") == "-":
                    if row["normalized_value"] != 0:
                        raise _error("visible DASH was not retained and normalized to zero")
                    dash_count += 1
            positions = [_ROLE_ORDER.index(role) for role in row_roles]
            if (
                positions != sorted(positions)
                or len(set(row_roles)) != len(row_roles)
                or row_roles[0] != "OPENING"
                or row_roles[-1] != "CLOSING"
                or not _REQUIRED_ROLES <= set(row_roles)
            ):
                raise _error("verified provision role order drifted")
            computed = parsed_roles["OPENING"] + sum(
                numeric
                for role, numeric in parsed_roles.items()
                if role not in {"OPENING", "CLOSING"}
            )
            if computed != parsed_roles["CLOSING"] or lane["accounting_check"] != {
                "computed_closing": computed,
                "printed_closing": parsed_roles["CLOSING"],
                "status": "CORROBORATED_EXACT",
            }:
                raise _error("verified provision accounting payload drifted")
        derived_period_status = (
            "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
            if any(
                lane["source_period_status"] == "VERIFIED_SOURCE_PERIOD_Q1_2026_NOT_Q2"
                for lane in trial["verified_lane_mappings"]
            )
            else "VERIFIED_SOURCE_PERIOD_Q2_2026"
        )
        if trial["source_period_status"] != derived_period_status:
            raise _error("verified trial/lane source-period binding drifted")
    expected_metrics = {
        "accounting_equation_verified_count": equation_count,
        "current_period_lane_parent_verified_count": lane_count,
        "current_period_role_mapping_verified_count": row_count,
        "document_count": len(EXPECTED_DOCUMENT_ORDER),
        "document_unique_region_count": unique_count,
        "q1_source_period_caveat_document_count": q1_count,
        "visible_dash_verified_as_zero_count": dash_count,
    }
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("verified provision result metrics drifted")
    return canonical_clone_v1(value)


def build_live_provision_movement_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay all fixed inputs and construct the live bounded result."""

    semantic_index, _ = _fixed_json(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256)
    crop_manifest, _ = _fixed_json(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256)
    review_value, _ = _fixed_json(REVIEW_PATH, REVIEW_SHA256)
    scanner = _scanner()
    structure_scan = scanner.build_provision_movement_full_document_scan_v1(semantic_index)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_provision_movement_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review_value,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=EXPECTED_CROP_MANIFEST_SHA256,
        review_sha256=REVIEW_SHA256,
    )


def validate_provision_movement_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Rebuild the result from every live fixed authority."""

    persisted = _validate_result(value)
    rebuilt = build_live_provision_movement_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("verified provision result does not replay exactly")
    return rebuilt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-blueprint", action="store_true")
    args = parser.parse_args()
    value = (
        _review_blueprint()
        if args.review_blueprint
        else build_live_provision_movement_8bank_codex_verified_mapping_v1()
    )
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
