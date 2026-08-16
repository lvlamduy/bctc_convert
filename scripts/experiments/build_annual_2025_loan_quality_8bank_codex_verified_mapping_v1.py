"""Verify annual-2025 loan-quality tables across eight audited bank PDFs.

The shared matcher enumerates every complete PDF and proposes structural
graphs from fresh VietOCR Transformer text.  This module binds the one selected
customer-loan graph per document to an independent visible-pixel ledger,
recomputes the five-grade equations, checks the live TM schema, and preserves
wrong-owner quality tables as negative controls.  Bank and page identities are
evidence bindings only; they are never matcher rules.
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
from decimal import Decimal, InvalidOperation
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
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    _authority_snapshot,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_LOAN_QUALITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_LOAN_QUALITY_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_"
    "VIETOCR_GENERIC_LOAN_QUALITY_OWNER_CHILD_GEOMETRY_PERIOD_UNIT_TOTAL_AND_"
    "ACCOUNTING_VARIANTS_PLUS_INDEPENDENT_VISIBLE_PIXEL_AND_BOUNDED_SCHEMA_"
    "CONTEXT_ONLY_NO_EXPORT_OR_PRODUCTION_AUTHORITY"
)
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0114-annual-2025-loan-quality-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0114-annual-2025-loan-quality-8bank-codex-verified-mapping-v1.json"
)
MARGIN_CONTEXT_PATH = Path("config/schemas/loan-quality-margin-context-v1.json")
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_SCAN_ID = "lqfdsv1:scan:0df149e298ad21117c245bbf28abaf182ea9219f668dd6727e4ab7a65d3e449e"

_ROLE_BINDINGS = (
    ("STANDARD", 747, "+ Nhóm 1: Nợ đủ tiêu chuẩn"),
    ("SPECIAL_MENTION", 748, "+ Nhóm 2: Nợ cần chú ý"),
    ("SUBSTANDARD", 749, "+ Nhóm 3: Nợ dưới tiêu chuẩn"),
    ("DOUBTFUL", 750, "+ Nhóm 4: Nợ nghi ngờ"),
    ("LOSS", 751, "+ Nhóm 5: Nợ có khả năng mất vốn"),
)
_NEGATIVE_CONTROLS = (
    {
        "candidate_parent_report_norm_id": 853,
        "owner_report_norm_id": 804,
        "role_report_norm_ids": [854, 855, 856, 857, 858],
    },
    {
        "candidate_parent_report_norm_id": 1018,
        "owner_report_norm_id": 966,
        "role_report_norm_ids": [1019, 1020, 1021, 1022, 1023],
    },
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "bounded_margin_context_overlay_used_for_report_norm_id_1944": True,
    "broad_corpus_authority": False,
    "canonicalization_or_export_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_transcription_used_for_numeric_truth": True,
    "live_tm_schema_hierarchy_and_negative_families_checked": True,
    "mapping_authority_is_bounded_to_reviewed_source_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "sparse_blank_cells_imputed_as_zero": False,
    "text_similarity_alone_used_for_mapping": False,
}
_REVIEW_CHECKS = (
    "ALL_EIGHT_COMPLETE_PDFS_SCANNED",
    "ONE_CUSTOMER_LOAN_QUALITY_GRAPH_PER_DOCUMENT",
    "WRONG_OWNER_QUALITY_TABLES_RETAINED_AS_NEGATIVE_CONTROLS",
    "VISIBLE_CONSOLIDATED_REPORT_SCOPE",
    "OWNER_BRANCH_CHILD_ORDER_AND_GEOMETRY",
    "PERIOD_AND_UNIT_AXIS",
    "FIVE_GRADE_MONEY_CELLS",
    "PERCENTAGE_COMPANION_LANES_WHEN_PRESENT",
    "STANDALONE_MARGIN_POPULATION_BOUNDARY",
    "HDB_DEFERRED_LC_POPULATION_BOUNDARY",
    "STACKED_SPARSE_CUSTOMER_LOAN_COLUMN_WITHOUT_ZERO_IMPUTATION",
    "SOURCE_TOTAL_AND_ACCOUNTING_CLOSURE",
    "LIVE_TM_SCHEMA_AND_BOUNDED_1944_CONTEXT",
)
_REVIEW_SAFETY = {
    "bank_or_page_used_as_matching_rule": False,
    "blank_sparse_cells_imputed_as_zero": False,
    "fresh_vietocr_used_as_pixel_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS",
    "old_ocr_used_as_semantic_text": False,
    "review_can_assert_broad_document_absence": False,
}
_HEX = set("0123456789abcdef")


class Annual2025LoanQuality8BankCodexVerifiedMappingV1Error(ValueError):
    """A graph, visible-pixel ledger, equation, or schema binding drifted."""


def _error(message: str) -> Annual2025LoanQuality8BankCodexVerifiedMappingV1Error:
    return Annual2025LoanQuality8BankCodexVerifiedMappingV1Error(message)


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(char not in _HEX for char in value):
        raise _error(f"{label} SHA-256 drifted")
    return value


def _fixed_bytes(path: Path, expected_sha256: str | None = None) -> bytes:
    if path.is_absolute() or ".." in path.parts:
        raise _error("fixed artifact path escaped the project root")
    full = PROJECT_ROOT / path
    descriptor = os.open(
        full, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error(f"fixed artifact is not one regular file: {path}")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1 << 20):
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
    digest = hashlib.sha256(payload).hexdigest()
    if len(payload) != before.st_size or (
        expected_sha256 is not None and digest != expected_sha256
    ):
        raise _error(f"fixed artifact content identity drifted: {path}")
    return payload


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise _error(f"{label} contains duplicate JSON key {key}")
            result[key] = item
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                _error(f"{label} contains non-finite JSON {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} root must be one object")
    return value


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load experiment module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _disagreement(
    field: str,
    role: str,
    source_line_index: int,
    semantic: str,
    pixel: str,
) -> dict[str, Any]:
    return {
        "disposition": "VISIBLE_PDF_PIXEL_ORTHOGRAPHY_OVERRIDES_TRANSFORMER_TEXT_ERROR",
        "field": field,
        "pixel_transcription": pixel,
        "role": role,
        "semantic_proposal": semantic,
        "source_line_index": source_line_index,
    }


def _row(
    role: str, label: str, money: Sequence[str], percent: Sequence[str] = ()
) -> dict[str, Any]:
    return {
        "money_values": list(money),
        "percentage_values": list(percent),
        "pixel_label": label,
        "role": role,
    }


def _review_banks() -> list[dict[str, Any]]:
    specs = (
        {
            "bank": "ACB",
            "page": 50,
            "render": "d09d8579c3cefdce5158fae5529195e147956a8af088295130c3117eadbfa349",
            "graph": "13ed409574354631fb6e82623b9760b0d3614e1280156789b35339a2501b19bd",
            "branch": "Theo chất lượng nợ cho vay",
            "owner": "CHO VAY KHÁCH HÀNG",
            "owner_page": 50,
            "owner_render": "d09d8579c3cefdce5158fae5529195e147956a8af088295130c3117eadbfa349",
            "periods": ("31.12.2025", "31.12.2024"),
            "units": ("Triệu VND", "Triệu VND"),
            "layout": "HORIZONTAL_TYPED_PERIOD_LANES",
            "columns": (None, None),
            "rows": (
                _row("STANDARD", "Nhóm 1 - Nợ đủ tiêu chuẩn", ("660.272.034", "560.567.462")),
                _row("SPECIAL_MENTION", "Nhóm 2 - Nợ cần chú ý", ("2.493.226", "2.779.393")),
                _row("SUBSTANDARD", "Nhóm 3 - Nợ dưới tiêu chuẩn", ("764.791", "923.291")),
                _row("DOUBTFUL", "Nhóm 4 - Nợ nghi ngờ", ("770.229", "978.211")),
                _row("LOSS", "Nhóm 5 - Nợ có khả năng mất vốn", ("5.136.367", "6.748.132")),
            ),
            "margin": {
                "money_values": ["17.340.705", "8.689.759"],
                "pixel_label": "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
            },
            "total": ("686.777.352", "580.686.248"),
            "total_percent": (),
            "excluded": None,
            "disagreements": (
                _disagreement(
                    "ROW_LABEL",
                    "STANDARD",
                    63,
                    "Nhóm 1 - Nợ đủ tiêu chuản",
                    "Nhóm 1 - Nợ đủ tiêu chuẩn",
                ),
            ),
        },
        {
            "bank": "MBB",
            "page": 51,
            "render": "35d892c6a207fd426cad7d4da67376c980707babdc82bb0b7dd958b9086c1da7",
            "graph": "b50d07ab2a74c330d90578396b9c3f6ac36bb3b6920a23c4fe4e3e791d1acc11",
            "branch": "Phân tích chất lượng nợ cho vay",
            "owner": "CHO VAY KHÁCH HÀNG",
            "owner_page": 51,
            "owner_render": "35d892c6a207fd426cad7d4da67376c980707babdc82bb0b7dd958b9086c1da7",
            "periods": ("31/12/2025", "31/12/2024"),
            "units": ("triệu đồng", "triệu đồng"),
            "layout": "HORIZONTAL_TYPED_PERIOD_LANES",
            "columns": (None, None),
            "rows": (
                _row("STANDARD", "Nợ đủ tiêu chuẩn", ("1.044.741.249", "741.581.903")),
                _row("SPECIAL_MENTION", "Nợ cần chú ý", ("10.210.040", "12.196.782")),
                _row("SUBSTANDARD", "Nợ dưới tiêu chuẩn", ("3.276.216", "3.379.646")),
                _row("DOUBTFUL", "Nợ nghi ngờ", ("4.330.016", "4.599.274")),
                _row("LOSS", "Nợ có khả năng mất vốn", ("6.421.264", "4.606.512")),
            ),
            "margin": {
                "money_values": ["15.040.585", "10.293.729"],
                "pixel_label": (
                    "Các khoản cho vay giao dịch ký quỹ và ứng trước cho khách hàng giao dịch "
                    "đầu tư chứng khoán – Nợ đủ tiêu chuẩn"
                ),
            },
            "total": ("1.084.019.370", "776.657.846"),
            "total_percent": (),
            "excluded": None,
            "disagreements": (
                _disagreement(
                    "ROW_LABEL", "LOSS", 75, "Nợ cỗ khả năng mất vốn", "Nợ có khả năng mất vốn"
                ),
                _disagreement(
                    "MARGIN_LABEL",
                    "MARGIN_AND_SECURITIES_ADVANCE",
                    78,
                    "Các khoản cho vay giao dịch ký quỹ và ứng trước cho khách hàng giao dịch đầu tư chứng khoán ? Nợ đủ tiêu chuẩn",
                    "Các khoản cho vay giao dịch ký quỹ và ứng trước cho khách hàng giao dịch đầu tư chứng khoán – Nợ đủ tiêu chuẩn",
                ),
            ),
        },
        {
            "bank": "VPB",
            "page": 45,
            "render": "7731043083c02a34caf583425c5a1cce03ffe29233e2febccc39fe3df342e842",
            "graph": "fbc9ec3ac2a4a68727fe46ca1458cb97968343c712500f632996dfe75e7f851a",
            "branch": "Phân tích chất lượng nợ cho vay",
            "owner": "CHO VAY KHÁCH HÀNG",
            "owner_page": 45,
            "owner_render": "7731043083c02a34caf583425c5a1cce03ffe29233e2febccc39fe3df342e842",
            "periods": ("Ngày 31 tháng 12 năm 2025", "Ngày 31 tháng 12 năm 2024"),
            "units": ("Triệu đồng", "Triệu đồng"),
            "layout": "HORIZONTAL_TYPED_PERIOD_LANES",
            "columns": (None, None),
            "rows": (
                _row("STANDARD", "Nợ đủ tiêu chuẩn", ("847.393.264", "615.824.369")),
                _row("SPECIAL_MENTION", "Nợ cần chú ý", ("30.950.442", "43.364.053")),
                _row("SUBSTANDARD", "Nợ dưới tiêu chuẩn", ("11.429.858", "10.852.509")),
                _row("DOUBTFUL", "Nợ nghi ngờ", ("10.879.958", "12.098.440")),
                _row("LOSS", "Nợ có khả năng mất vốn", ("9.154.889", "6.119.216")),
            ),
            "margin": {
                "money_values": ["34.093.219", "9.512.536"],
                "pixel_label": "Cho vay giao dịch ký quỹ và ứng trước cho khách hàng",
            },
            "total": ("943.901.630", "697.771.123"),
            "total_percent": (),
            "excluded": None,
            "disagreements": (),
        },
        {
            "bank": "HDB",
            "page": 36,
            "render": "1ff59f58f610eaa3db9263522cc4d055bba1a59d8c9d43ee287ab829d47f7eb9",
            "graph": "be1e0455848ed3c02ab1d84a775b7052178dbf88e21ae3857c6881d64d99747b",
            "branch": "Phân tích dư nợ cho vay theo chất lượng nợ",
            "owner": "Cho vay khách hàng",
            "owner_page": 36,
            "owner_render": "1ff59f58f610eaa3db9263522cc4d055bba1a59d8c9d43ee287ab829d47f7eb9",
            "periods": ("Số cuối năm", "Số đầu năm"),
            "units": ("Triệu VND", "Triệu VND"),
            "layout": "HORIZONTAL_TYPED_PERIOD_LANES",
            "columns": (None, None),
            "rows": (
                _row("STANDARD", "Nợ đủ tiêu chuẩn", ("514.257.606", "401.834.768")),
                _row("SPECIAL_MENTION", "Nợ cần chú ý", ("18.792.886", "20.915.070")),
                _row("SUBSTANDARD", "Nợ dưới tiêu chuẩn", ("4.017.065", "4.199.973")),
                _row("DOUBTFUL", "Nợ nghi ngờ", ("5.500.307", "1.967.085")),
                _row("LOSS", "Nợ có khả năng mất vốn", ("3.802.915", "2.389.173")),
            ),
            "margin": None,
            "total": ("546.370.779", "431.306.069"),
            "total_percent": (),
            "excluded": {
                "pixel_label": "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày 01 tháng 7 năm 2024",
                "reason": "SEPARATE_ADJACENT_CREDIT_POPULATION_OUTSIDE_CUSTOMER_LOAN_FIVE_GRADE_CORE",
                "visible_values": ["-", "11.178.772"],
            },
            "disagreements": (
                _disagreement("ROW_LABEL", "SPECIAL_MENTION", 18, "Nơ cần chú ý", "Nợ cần chú ý"),
                _disagreement(
                    "ROW_LABEL", "SUBSTANDARD", 21, "Nợ đưới tiêu chuẩn", "Nợ dưới tiêu chuẩn"
                ),
                _disagreement("ROW_LABEL", "DOUBTFUL", 24, "Nợnghi ngờ", "Nợ nghi ngờ"),
                _disagreement(
                    "ROW_LABEL", "LOSS", 27, "Nợ có khá năng mất vốn", "Nợ có khả năng mất vốn"
                ),
            ),
        },
        {
            "bank": "VCB",
            "page": 39,
            "render": "f6680605fdd69b8973a97de5949f4222bac54d62970255ad0713454b529cf2de",
            "graph": "ed809fda42747defbb195948f28a5a1c9c6a55fbbf5ce514ef9353a2d2f4fb67",
            "branch": "Phân tích dư nợ theo chất lượng nợ cho vay như sau:",
            "owner": "Cho vay khách hàng",
            "owner_page": 39,
            "owner_render": "f6680605fdd69b8973a97de5949f4222bac54d62970255ad0713454b529cf2de",
            "periods": ("31/12/2025", "31/12/2024"),
            "units": ("Triệu VND", "Triệu VND"),
            "layout": "HORIZONTAL_TYPED_PERIOD_LANES",
            "columns": (None, None),
            "rows": (
                _row("STANDARD", "Nợ đủ tiêu chuẩn", ("1.661.151.484", "1.431.299.668")),
                _row("SPECIAL_MENTION", "Nợ cần chú ý", ("2.704.636", "3.935.217")),
                _row("SUBSTANDARD", "Nợ dưới tiêu chuẩn", ("760.561", "2.153.039")),
                _row("DOUBTFUL", "Nợ nghi ngờ", ("222.632", "1.518.558")),
                _row("LOSS", "Nợ có khả năng mất vốn", ("8.686.362", "10.292.417")),
            ),
            "margin": None,
            "total": ("1.673.525.675", "1.449.198.899"),
            "total_percent": (),
            "excluded": None,
            "disagreements": (
                _disagreement(
                    "ROW_LABEL", "LOSS", 87, "Nợ cỗ khả năng mất vốn", "Nợ có khả năng mất vốn"
                ),
            ),
        },
        {
            "bank": "CTG",
            "page": 43,
            "render": "686ffc712a22c2653401646668e8efbbffd34aac303107932c0c5cdc533074ee",
            "graph": "7a8a5b373c2fa3ea6518fbc0999b54de3eec637317dbbb6f628674f6acd94312",
            "branch": "Theo chất lượng nợ cho vay",
            "owner": "CHO VAY KHÁCH HÀNG",
            "owner_page": 43,
            "owner_render": "686ffc712a22c2653401646668e8efbbffd34aac303107932c0c5cdc533074ee",
            "periods": ("31.12.2025", "31.12.2024"),
            "units": ("Triệu đồng", "Triệu đồng"),
            "layout": "HORIZONTAL_TYPED_PERIOD_LANES",
            "columns": (None, None),
            "rows": (
                _row("STANDARD", "Nhóm 1 - Nợ đủ tiêu chuẩn", ("1.953.010.761", "1.677.704.259")),
                _row("SPECIAL_MENTION", "Nhóm 2 - Nợ cần chú ý", ("17.345.911", "22.898.528")),
                _row("SUBSTANDARD", "Nhóm 3 - Nợ dưới tiêu chuẩn", ("1.490.975", "2.817.030")),
                _row("DOUBTFUL", "Nhóm 4 - Nợ nghi ngờ", ("578.479", "4.824.119")),
                _row("LOSS", "Nhóm 5 - Nợ có khả năng mất vốn", ("19.846.742", "13.710.778")),
            ),
            "margin": None,
            "total": ("1.992.272.868", "1.721.954.714"),
            "total_percent": (),
            "excluded": None,
            "disagreements": (
                _disagreement(
                    "OWNER", "CUSTOMER_LOANS", 5, "CHO VAY KHÁCH HẰNG", "CHO VAY KHÁCH HÀNG"
                ),
                _disagreement(
                    "ROW_LABEL", "DOUBTFUL", 99, "Nhóm 4 ? Nợ nghi ngờ", "Nhóm 4 - Nợ nghi ngờ"
                ),
                _disagreement(
                    "ROW_LABEL",
                    "LOSS",
                    102,
                    "Nhóm 5 - Nợ cổ khả năng mắt vốn",
                    "Nhóm 5 - Nợ có khả năng mất vốn",
                ),
            ),
        },
        {
            "bank": "BID",
            "page": 42,
            "render": "443dc71ee70615358b01109d701014804bca0a24caa41d1b85377f0f3b3b8df9",
            "graph": "317a22cf8a065c4366f8c945eca17feb8e4500ec917d3c25a6cbbc00d97b805f",
            "branch": "Phân tích chất lượng nợ cho vay",
            "owner": "CHO VAY KHÁCH HÀNG",
            "owner_page": 41,
            "owner_render": "5b7980206c405decc1ddf5064bf2e2f5acf8906875698cc108268376b45bc488",
            "periods": ("Số cuối năm", "Số đầu năm (Trình bày lại)"),
            "units": ("Triệu VND", "%", "Triệu VND", "%"),
            "layout": "HORIZONTAL_TYPED_PERIOD_LANES",
            "columns": (None, None),
            "rows": (
                _row(
                    "STANDARD",
                    "Nợ đủ tiêu chuẩn",
                    ("2.306.515.484", "1.992.589.394"),
                    ("97,19", "96,92"),
                ),
                _row(
                    "SPECIAL_MENTION",
                    "Nợ cần chú ý",
                    ("31.462.771", "34.428.411"),
                    ("1,33", "1,67"),
                ),
                _row(
                    "SUBSTANDARD",
                    "Nợ dưới tiêu chuẩn",
                    ("4.473.881", "3.666.965"),
                    ("0,19", "0,18"),
                ),
                _row("DOUBTFUL", "Nợ nghi ngờ", ("4.677.985", "5.577.478"), ("0,20", "0,27")),
                _row(
                    "LOSS", "Nợ có khả năng mất vốn", ("25.824.953", "19.820.172"), ("1,09", "0,96")
                ),
            ),
            "margin": None,
            "total": ("2.372.955.074", "2.056.082.420"),
            "total_percent": ("100,00", "100,00"),
            "excluded": None,
            "disagreements": (),
        },
        {
            "bank": "VIB",
            "page": 66,
            "render": "68b98a5015e5a4576ff748b3a826272afe191cfb9b74d62d723f2e2725188f07",
            "graph": "d80c8972126cd227d75635d5bb3710d9fafc1d7a0cb51da9dbbc0e8d10c84efe",
            "branch": "Chi tiết phân loại chất lượng tài sản có rủi ro tín dụng tại Ngân hàng như sau:",
            "owner": "Rủi ro tín dụng (tiếp theo)",
            "owner_page": 66,
            "owner_render": "68b98a5015e5a4576ff748b3a826272afe191cfb9b74d62d723f2e2725188f07",
            "periods": ("Tại ngày 31 tháng 12 năm 2025", "Tại ngày 31 tháng 12 năm 2024"),
            "units": ("triệu đồng", "triệu đồng"),
            "layout": "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS",
            "columns": (0, 4),
            "rows": (
                _row("STANDARD", "Nợ đủ tiêu chuẩn", ("361.491.090", "301.905.639")),
                _row("SPECIAL_MENTION", "Nợ cần chú ý", ("9.146.241", "10.730.560")),
                _row("SUBSTANDARD", "Nợ dưới tiêu chuẩn", ("2.149.202", "2.305.497")),
                _row("DOUBTFUL", "Nợ nghi ngờ", ("2.824.185", "2.670.580")),
                _row("LOSS", "Nợ có khả năng mất vốn", ("6.361.298", "6.397.437")),
            ),
            "margin": None,
            "total": ("381.972.016", "324.009.713"),
            "total_percent": (),
            "excluded": None,
            "disagreements": (
                _disagreement(
                    "OWNER",
                    "CREDIT_RISK",
                    7,
                    "Rũi ro tin dụng (tiếp theo)",
                    "Rủi ro tín dụng (tiếp theo)",
                ),
                _disagreement(
                    "BRANCH",
                    "LOAN_QUALITY_CLASSIFICATION",
                    9,
                    "hàng là 2,16% (31/12/2024: 2.44%). Chi tiết phân loại chất lượng tài sản có rùi ro tỉn dụng tại",
                    "Chi tiết phân loại chất lượng tài sản có rủi ro tín dụng tại Ngân hàng như sau:",
                ),
                _disagreement(
                    "ROW_LABEL", "LOSS", 86, "Nợ có khả năng mắt vốn", "Nợ có khả năng mất vốn"
                ),
            ),
        },
    )
    banks: list[dict[str, Any]] = []
    for spec in specs:
        customer, total = spec["columns"]
        banks.append(
            {
                "bank_code": spec["bank"],
                "branch_pixel_transcription": spec["branch"],
                "customer_loan_column_index": customer,
                "excluded_adjacent_population": spec["excluded"],
                "layout_mode": spec["layout"],
                "mapping_owner_pixel": "Cho vay khách hàng",
                "matcher_graph_sha256": spec["graph"],
                "optional_additive_population": spec["margin"],
                "owner_evidence": {
                    "physical_page": spec["owner_page"],
                    "pixel_transcription": spec["owner"],
                    "render_sha256": spec["owner_render"],
                },
                "percentage_source_only_total": list(spec["total_percent"]),
                "period_pixel_transcriptions": list(spec["periods"]),
                "physical_page": spec["page"],
                "rows": list(spec["rows"]),
                "source_only_total": list(spec["total"]),
                "statement_context_evidence": {
                    "mode": "PAGE_LOCAL_VISIBLE_HEADING",
                    "physical_page": spec["page"],
                    "pixel_transcription": "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT",
                    "render_sha256": spec["render"],
                    "report_scope": "CONSOLIDATED",
                },
                "target_render_sha256": spec["render"],
                "total_column_index": total,
                "transformer_disagreements": list(spec["disagreements"]),
                "unit_pixel_transcriptions": list(spec["units"]),
            }
        )
    return banks


def review_blueprint_v1() -> dict[str, Any]:
    """Return the fixed visible-pixel ledger used by the annual verifier."""

    return {
        "banks": _review_banks(),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": REVIEW_FORMAT,
        "review_checks": list(_REVIEW_CHECKS),
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_PDF_PIXEL_AND_ACCOUNTING_REVIEW",
            "review_run_id": "E-0114-ANNUAL-2025",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }


def _review_file_sha256() -> str:
    return hashlib.sha256(canonical_json_bytes_v1(review_blueprint_v1()) + b"\n").hexdigest()


def _review(value: Any) -> dict[str, Any]:
    expected = review_blueprint_v1()
    if not same_typed_json_v1(value, expected):
        raise _error("annual-2025 Codex loan-quality review differs from fixed pixel ledger")
    return canonical_clone_v1(expected)


def _money(surface: str) -> int:
    compact = surface.strip().replace(" ", "")
    if compact in {"-", "–", "—"}:
        return 0
    negative = compact.startswith("(") and compact.endswith(")")
    digits = compact.strip("()").replace(".", "").replace(",", "")
    if not digits.isdigit():
        raise _error(f"visible money transcription is invalid: {surface}")
    return -int(digits) if negative else int(digits)


def _percent(surface: str) -> Decimal:
    try:
        value = Decimal(surface.strip().replace("%", "").replace(" ", "").replace(",", "."))
    except InvalidOperation as exc:
        raise _error(f"visible percentage transcription is invalid: {surface}") from exc
    if not value.is_finite():
        raise _error("visible percentage is non-finite")
    return value


def _has_disagreement(items: Sequence[Mapping[str, Any]], semantic: str, pixel: str) -> bool:
    return any(
        item.get("semantic_proposal") == semantic and item.get("pixel_transcription") == pixel
        for item in items
    )


def _surface_reconciles(
    semantic: str, pixel: str, disagreements: Sequence[Mapping[str, Any]]
) -> bool:
    left = normalize_vietnamese_anchor_v1(semantic)
    right = normalize_vietnamese_anchor_v1(pixel)
    return (
        left == right
        or left in right
        or right in left
        or _has_disagreement(disagreements, semantic, pixel)
    )


def _value(
    graph_value: Mapping[str, Any], pixel: str, disagreements: Sequence[Mapping[str, Any]]
) -> int:
    semantic = graph_value.get("surface")
    if type(semantic) is not str:
        raise _error("graph numeric surface drifted")
    semantic_value = _money(semantic)
    pixel_value = _money(pixel)
    if semantic_value != pixel_value and not _has_disagreement(disagreements, semantic, pixel):
        raise _error("Transformer/pixel numeric disagreement lacks explicit review")
    return pixel_value


def _period_key(value: str) -> str:
    normalized = normalize_vietnamese_anchor_v1(value.replace(".", "/"))
    match = re.search(r"\b(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})\b", value.replace(".", "/"))
    if match is None:
        match = re.search(r"\bngay (\d{1,2}) thang (\d{1,2}) nam (\d{4})\b", normalized)
    if match is not None:
        day, month, year = (int(item) for item in match.groups())
        return f"{day:02d}/{month:02d}/{year:04d}"
    if "so cuoi nam" in normalized or value == "CURRENT_PERIOD_END":
        return "CURRENT_PERIOD_END"
    if "so dau nam" in normalized or value == "COMPARATIVE_PERIOD_START":
        return "COMPARATIVE_PERIOD_START"
    return normalized


def _page(document: Mapping[str, Any], physical_page: int) -> Mapping[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error("crop manifest page inventory drifted")
    matches = [page for page in pages if page.get("physical_page") == physical_page]
    if len(matches) != 1:
        raise _error("review page is not unique in crop manifest")
    return matches[0]


def _document(documents: Sequence[Mapping[str, Any]], code: str) -> Mapping[str, Any]:
    matches = [document for document in documents if document.get("bank_code") == code]
    if len(matches) != 1:
        raise _error("crop manifest bank denominator drifted")
    return matches[0]


def _render_sha(page: Mapping[str, Any]) -> str:
    binding = page.get("render_binding")
    if type(binding) is not dict:
        raise _error("crop manifest render binding drifted")
    return _sha(binding.get("sha256"), "crop manifest render")


def _selected_graph_rows(
    graph: Mapping[str, Any], review: Mapping[str, Any]
) -> tuple[
    list[tuple[Mapping[str, Any], list[Mapping[str, Any]], list[Mapping[str, Any]]]],
    list[Mapping[str, Any]],
    list[Mapping[str, Any]],
]:
    if graph.get("layout_mode") != review["layout_mode"]:
        raise _error("review and graph layout modes disagree")
    if review["layout_mode"] == "HORIZONTAL_TYPED_PERIOD_LANES":
        rows = graph.get("rows")
        totals = graph.get("totals")
        if type(rows) is not list or type(totals) is not dict:
            raise _error("horizontal quality graph shape drifted")
        total = totals.get("core") or totals.get("grand")
        if type(total) is not list:
            raise _error("horizontal quality total drifted")
        selected = []
        for row in rows:
            values = row.get("values")
            if type(values) is not list:
                raise _error("horizontal quality row values drifted")
            money = [value for value in values if value.get("lane_type") == "MONEY"]
            percentage = [value for value in values if value.get("lane_type") == "PERCENT"]
            selected.append((row, money, percentage))
        return (
            selected,
            [value for value in total if value.get("lane_type") == "MONEY"],
            [value for value in total if value.get("lane_type") == "PERCENT"],
        )

    blocks = graph.get("blocks")
    customer = graph.get("customer_loan_column")
    total_column = graph.get("total_column")
    target = review["customer_loan_column_index"]
    companion = review["total_column_index"]
    if (
        type(blocks) is not list
        or len(blocks) != 2
        or type(customer) is not dict
        or type(total_column) is not dict
        or customer.get("column_index") != target
        or total_column.get("column_index") != companion
    ):
        raise _error("stacked selected customer-loan/total columns drifted")
    by_role: dict[
        str, tuple[Mapping[str, Any], list[Mapping[str, Any]], list[Mapping[str, Any]]]
    ] = {}
    totals: list[Mapping[str, Any]] = []
    for block_index, block in enumerate(blocks):
        if block.get("block_ordinal") != block_index or type(block.get("rows")) is not list:
            raise _error("stacked quality block order drifted")
        selected_total = [value for value in block["total"] if value.get("lane_index") == target]
        if len(selected_total) != 1:
            raise _error("stacked customer-loan total is not unique")
        totals.append(selected_total[0])
        for row in block["rows"]:
            selected_value = [value for value in row["values"] if value.get("lane_index") == target]
            companion_value = [
                value for value in row["values"] if value.get("lane_index") == companion
            ]
            if len(selected_value) != 1 or len(companion_value) != 1:
                raise _error("stacked sparse row lacks selected and total cells")
            if block_index == 0:
                by_role[row["role"]] = (row, [selected_value[0]], [])
            else:
                by_role[row["role"]][1].append(selected_value[0])
    return [by_role[role] for role, _id, _name in _ROLE_BINDINGS], totals, []


def _verify_axes_units(graph: Mapping[str, Any], review: Mapping[str, Any]) -> None:
    axes = graph.get("axes")
    if type(axes) is not list or len(axes) != 2:
        raise _error("quality period axis denominator drifted")
    ordered_axes = axes
    if graph.get("layout_mode") == "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS":
        ordered_axes = sorted(
            axes,
            key=lambda item: min(item.get("evidence_source_line_indices", [10**9])),
        )
    if [_period_key(item["period"]) for item in ordered_axes] != [
        _period_key(item) for item in review["period_pixel_transcriptions"]
    ]:
        raise _error("review and graph period axes disagree")
    unit_scope = graph.get("unit_scope")
    if type(unit_scope) is not dict:
        raise _error("quality unit scope drifted")
    if graph.get("layout_mode") == "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS":
        if unit_scope.get("mode") != "LOCAL_SHARED_MONEY_UNIT" or any(
            "trieu" not in normalize_vietnamese_anchor_v1(item)
            for item in review["unit_pixel_transcriptions"]
        ):
            raise _error("stacked shared million-unit evidence drifted")
        return
    surfaces = unit_scope.get("surfaces")
    if type(surfaces) is not list or [
        normalize_vietnamese_anchor_v1(item) for item in surfaces
    ] != [normalize_vietnamese_anchor_v1(item) for item in review["unit_pixel_transcriptions"]]:
        raise _error("review and graph typed unit lanes disagree")


def _schema(schema_by_id: Mapping[int, Any]) -> list[dict[str, Any]]:
    required = {716, 746, 747, 748, 749, 750, 751, 5746, 804, 853, 966, 1018}
    if any(item not in schema_by_id for item in required):
        raise _error("live TM schema lacks loan-quality or negative-control hierarchy")
    owner = schema_by_id[716]
    parent = schema_by_id[746]
    if (
        owner.canonical_name != "Cho vay khách hàng"
        or 746 not in owner.children
        or parent.canonical_name != "Phân tích chất lượng nợ cho vay"
        or parent.parent_id != 716
        or list(parent.children) != [747, 748, 749, 750, 751]
    ):
        raise _error("live TM customer-loan quality hierarchy drifted")
    mappings: list[dict[str, Any]] = []
    previous_order = parent.display_order
    for role, report_norm_id, canonical_name in _ROLE_BINDINGS:
        item = schema_by_id[report_norm_id]
        if (
            item.canonical_name != canonical_name
            or item.parent_id != 746
            or item.statement_type != "TM"
            or "CONSOLIDATED" not in item.scope
            or type(item.display_order) is not int
            or item.display_order <= previous_order
        ):
            raise _error(f"live TM quality role {report_norm_id} drifted")
        previous_order = item.display_order
        mappings.append(
            {
                "canonical_name": canonical_name,
                "display_order": item.display_order,
                "report_norm_id": report_norm_id,
                "role": role,
            }
        )
    return mappings


def _margin_context() -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _fixed_bytes(MARGIN_CONTEXT_PATH)
    value = _strict_json(payload, "loan-quality margin context")
    standalone = value.get("standalone_item")
    policy = value.get("normalization_policy")
    if (
        value.get("format_version") != "LOAN_QUALITY_MARGIN_CONTEXT_V1"
        or value.get("state") != "PROJECT_OWNER_ADJUDICATED_BOUNDED_SCHEMA_CONTEXT"
        or type(standalone) is not dict
        or standalone.get("report_norm_id") != 1944
        or standalone.get("parent_report_norm_id") != 746
        or standalone.get("mapping_eligible_in_this_bounded_context") is not True
        or type(policy) is not dict
        or policy.get("standalone_after_five_grades") != "KEEP_747_UNCHANGED_AND_EMIT_1944"
        or policy.get("double_count_permitted") is not False
    ):
        raise _error("bounded project-owner margin context drifted")
    return value, {
        "path": MARGIN_CONTEXT_PATH.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def build_annual_2025_loan_quality_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_authority: Any,
    schema_by_id: Mapping[int, Any],
    margin_context: Any,
    *,
    crop_manifest_sha256: str,
    margin_context_ref: Mapping[str, Any],
    review_sha256: str,
) -> dict[str, Any]:
    """Derive the bounded annual eight-bank mappings from exact inputs."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis.get("semantic_axis_sha256") != EXPECTED_AXIS_SHA256:
        raise _error("annual full-document semantic axis drifted")
    scanner = _load_module(
        PROJECT_ROOT / "scripts/experiments/scan_loan_quality_full_document_vietocr_v1.py",
        "annual_2025_quality_scanner_for_mapping",
    )
    scanner.validate_loan_quality_full_document_scan_replay_v1(
        structure_scan,
        semantic_index,
        enable_extended_annual_variants=True,
    )
    if structure_scan.get("scan_id") != EXPECTED_SCAN_ID:
        raise _error("annual quality scan identity drifted")
    reviewed = _review(review)
    expected_review_sha = _review_file_sha256()
    if review_sha256 != expected_review_sha:
        raise _error("annual quality review identity drifted")
    if crop_manifest_sha256 != EXPECTED_CROP_MANIFEST_SHA256:
        raise _error("annual crop manifest identity drifted")
    if type(schema_authority) is not dict or type(crop_manifest) is not dict:
        raise _error("annual schema authority or crop manifest shape drifted")
    manifest_documents = crop_manifest.get("documents")
    if type(manifest_documents) is not list or len(manifest_documents) != 8:
        raise _error("annual crop manifest document denominator drifted")
    schema_roles = _schema(schema_by_id)
    if not same_typed_json_v1(margin_context, _margin_context()[0]):
        raise _error("bounded margin context changed during build")

    trials: list[dict[str, Any]] = []
    for ordinal, (bank_review, expected_code) in enumerate(
        zip(reviewed["banks"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        scan_trial = structure_scan["trials"][ordinal - 1]
        if scan_trial.get("document_provenance") != expected_code:
            raise _error("annual quality scan document order drifted")
        matcher = scan_trial.get("matcher_result")
        graphs = matcher.get("graphs") if type(matcher) is dict else None
        if type(graphs) is not list:
            raise _error("annual quality matcher graph list drifted")
        accepted = [
            graph
            for graph in graphs
            if graph.get("status") == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
        ]
        if len(accepted) != 1 or matcher.get("uniqueness", {}).get("status") != "UNIQUE_FULL_MATCH":
            raise _error("annual document lacks one unique resolved customer-loan quality graph")
        graph = accepted[0]
        if (
            graph.get("page_sequence") != bank_review["physical_page"]
            or graph.get("unresolved_reasons") != []
            or canonical_json_sha256_v1(graph) != bank_review["matcher_graph_sha256"]
        ):
            raise _error("annual review target graph identity drifted")

        manifest_document = _document(manifest_documents, expected_code)
        target_page = _page(manifest_document, bank_review["physical_page"])
        owner_page = _page(manifest_document, bank_review["owner_evidence"]["physical_page"])
        if (
            _render_sha(target_page) != bank_review["target_render_sha256"]
            or _render_sha(owner_page) != bank_review["owner_evidence"]["render_sha256"]
        ):
            raise _error("annual review page render binding drifted")
        context = bank_review["statement_context_evidence"]
        context_page = _page(manifest_document, context["physical_page"])
        if (
            _render_sha(context_page) != context["render_sha256"]
            or context["report_scope"] != "CONSOLIDATED"
            or "hop nhat" not in normalize_vietnamese_anchor_v1(context["pixel_transcription"])
        ):
            raise _error("annual consolidated statement-context evidence drifted")
        disagreements = bank_review["transformer_disagreements"]
        if not _surface_reconciles(
            graph["owner_context"]["surface"],
            bank_review["owner_evidence"]["pixel_transcription"],
            disagreements,
        ) or not _surface_reconciles(
            graph["branch"]["surface"],
            bank_review["branch_pixel_transcription"],
            disagreements,
        ):
            raise _error("annual owner/branch pixels do not reconcile with the graph")
        _verify_axes_units(graph, bank_review)

        selected_rows, graph_total_money, graph_total_percent = _selected_graph_rows(
            graph, bank_review
        )
        if len(selected_rows) != 5 or len(graph_total_money) != 2:
            raise _error("annual five-grade/total denominator drifted")
        verified: list[dict[str, Any]] = []
        parsed_rows: list[list[int]] = []
        parsed_percent_rows: list[list[Decimal]] = []
        for (graph_row, graph_money, graph_percent), review_row, schema_role in zip(
            selected_rows, bank_review["rows"], schema_roles, strict=True
        ):
            role = schema_role["role"]
            semantic_label = graph_row["label"]["surface"]
            if (
                graph_row.get("role") != role
                or review_row["role"] != role
                or not _surface_reconciles(semantic_label, review_row["pixel_label"], disagreements)
                or len(graph_money) != 2
                or len(review_row["money_values"]) != 2
            ):
                raise _error(
                    f"annual quality row reconciliation drifted for {expected_code} {role}"
                )
            parsed = [
                _value(value, pixel, disagreements)
                for value, pixel in zip(graph_money, review_row["money_values"], strict=True)
            ]
            parsed_rows.append(parsed)
            percentages: list[dict[str, Any]] = []
            parsed_percentage: list[Decimal] = []
            if graph_percent or review_row["percentage_values"]:
                if len(graph_percent) != 2 or len(review_row["percentage_values"]) != 2:
                    raise _error("annual percentage companion lane denominator drifted")
                for axis_index, (graph_value, pixel) in enumerate(
                    zip(graph_percent, review_row["percentage_values"], strict=True)
                ):
                    semantic = graph_value["surface"]
                    if _percent(semantic) != _percent(pixel) and not _has_disagreement(
                        disagreements, semantic, pixel
                    ):
                        raise _error("annual Transformer/pixel percentage disagreement drifted")
                    parsed_percentage.append(_percent(pixel))
                    percentages.append(
                        {
                            "axis_index": axis_index,
                            "independent_pixel_transcription": pixel,
                            "lane_type": "PERCENT",
                            "semantic_proposal": semantic,
                            "source_line_index": graph_value["source_line_index"],
                            "status": "VERIFIED_VISIBLE_PIXEL_VALUE",
                        }
                    )
            parsed_percent_rows.append(parsed_percentage)
            verified.append(
                {
                    "canonical_name": schema_role["canonical_name"],
                    "display_order": schema_role["display_order"],
                    "independent_pixel_label": review_row["pixel_label"],
                    "money_values": [
                        {
                            "axis_index": axis_index,
                            "independent_pixel_transcription": pixel,
                            "lane_type": "MONEY",
                            "period_pixel_transcription": bank_review[
                                "period_pixel_transcriptions"
                            ][axis_index],
                            "semantic_proposal": graph_value["surface"],
                            "source_line_index": graph_value["source_line_index"],
                            "status": "VERIFIED_VISIBLE_PIXEL_VALUE",
                        }
                        for axis_index, (graph_value, pixel) in enumerate(
                            zip(graph_money, review_row["money_values"], strict=True)
                        )
                    ],
                    "parent_report_norm_id": 746,
                    "percentage_corroboration": percentages,
                    "report_norm_id": schema_role["report_norm_id"],
                    "role": role,
                    "semantic_proposal_label": semantic_label,
                    "status": "VERIFIED_BY_CODEX",
                }
            )

        graph_margin = graph.get("optional_additive_row")
        review_margin = bank_review["optional_additive_population"]
        margin_values: list[int] = []
        if review_margin is None:
            if graph_margin is not None:
                raise _error("annual graph exposes an unreviewed margin population")
        else:
            if (
                type(graph_margin) is not dict
                or len(graph_margin.get("values", [])) != 2
                or not _surface_reconciles(
                    graph_margin["label_surface"], review_margin["pixel_label"], disagreements
                )
            ):
                raise _error("annual reviewed standalone margin population drifted")
            margin_values = [
                _value(value, pixel, disagreements)
                for value, pixel in zip(
                    graph_margin["values"], review_margin["money_values"], strict=True
                )
            ]
            verified.append(
                {
                    "canonical_name": "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
                    "display_order": None,
                    "independent_pixel_label": review_margin["pixel_label"],
                    "money_values": [
                        {
                            "axis_index": axis_index,
                            "independent_pixel_transcription": pixel,
                            "lane_type": "MONEY",
                            "period_pixel_transcription": bank_review[
                                "period_pixel_transcriptions"
                            ][axis_index],
                            "semantic_proposal": graph_value["surface"],
                            "source_line_index": graph_value["source_line_index"],
                            "status": "VERIFIED_VISIBLE_PIXEL_VALUE",
                        }
                        for axis_index, (graph_value, pixel) in enumerate(
                            zip(graph_margin["values"], review_margin["money_values"], strict=True)
                        )
                    ],
                    "parent_report_norm_id": 746,
                    "percentage_corroboration": [],
                    "report_norm_id": 1944,
                    "role": "MARGIN_AND_SECURITIES_ADVANCE",
                    "semantic_proposal_label": graph_margin["label_surface"],
                    "status": "VERIFIED_BY_PROJECT_OWNER_AND_CODEX",
                }
            )

        parsed_total = [
            _value(value, pixel, disagreements)
            for value, pixel in zip(
                graph_total_money, bank_review["source_only_total"], strict=True
            )
        ]
        grade_sums = [sum(row[axis] for row in parsed_rows) for axis in range(2)]
        expected_total = [
            grade_sums[axis] + (margin_values[axis] if margin_values else 0) for axis in range(2)
        ]
        if expected_total != parsed_total:
            raise _error("annual visible five-grade plus margin equation does not close")
        percentage_equations: list[dict[str, Any]] = []
        if bank_review["percentage_source_only_total"]:
            if len(graph_total_percent) != 2 or any(len(row) != 2 for row in parsed_percent_rows):
                raise _error("annual percentage total/row denominator drifted")
            for axis_index, (graph_value, pixel) in enumerate(
                zip(
                    graph_total_percent,
                    bank_review["percentage_source_only_total"],
                    strict=True,
                )
            ):
                printed = _percent(pixel)
                if _percent(graph_value["surface"]) != printed:
                    raise _error("annual percentage total pixel/Transformer conflict")
                computed = sum(row[axis_index] for row in parsed_percent_rows)
                if abs(computed - printed) > Decimal("0.01"):
                    raise _error("annual percentage grade sum exceeds rounding tolerance")
                percentage_equations.append(
                    {
                        "axis_index": axis_index,
                        "computed_total": str(computed),
                        "printed_total": pixel,
                        "status": "CORROBORATED_WITHIN_DISPLAY_ROUNDING",
                    }
                )
        elif graph_total_percent:
            raise _error("annual graph exposes unreviewed percentage totals")

        trials.append(
            {
                "accounting_equations": [
                    {
                        "addend_report_norm_ids": [
                            747,
                            748,
                            749,
                            750,
                            751,
                            *([1944] if margin_values else []),
                        ],
                        "addends": [
                            *[row[axis_index] for row in parsed_rows],
                            *([margin_values[axis_index]] if margin_values else []),
                        ],
                        "axis_index": axis_index,
                        "computed_total": expected_total[axis_index],
                        "source_total": parsed_total[axis_index],
                        "status": "CORROBORATED",
                    }
                    for axis_index in range(2)
                ],
                "document_ordinal": ordinal,
                "document_provenance": expected_code,
                "excluded_adjacent_population": canonical_clone_v1(
                    bank_review["excluded_adjacent_population"]
                ),
                "layout_mode": graph["layout_mode"],
                "negative_family_controls": [
                    {
                        **canonical_clone_v1(control),
                        "status": "EXCLUDED_WRONG_OR_UNSELECTED_OWNER_POPULATION",
                        "whole_document_absence_claim": False,
                    }
                    for control in _NEGATIVE_CONTROLS
                ],
                "percentage_equations": percentage_equations,
                "physical_page": bank_review["physical_page"],
                "source_only_total": {
                    "report_norm_id": None,
                    "status": "VERIFIED_SOURCE_ONLY",
                    "values": [
                        {
                            "axis_index": axis_index,
                            "independent_pixel_transcription": pixel,
                            "semantic_proposal": graph_value["surface"],
                            "source_line_index": graph_value["source_line_index"],
                        }
                        for axis_index, (graph_value, pixel) in enumerate(
                            zip(
                                graph_total_money,
                                bank_review["source_only_total"],
                                strict=True,
                            )
                        )
                    ],
                },
                "statement_context": canonical_clone_v1(context),
                "status": "SCHEMA_MAPPING_VERIFIED_BY_CODEX",
                "target_render_sha256": bank_review["target_render_sha256"],
                "transformer_disagreements": canonical_clone_v1(disagreements),
                "verified_mappings": verified,
                "whole_document_family_absence_claim": False,
            }
        )

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
            "loan_quality_margin_context": canonical_clone_v1(margin_context_ref),
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": EXPECTED_SCAN_ID,
            "tm_schema_authority": canonical_clone_v1(schema_authority),
        },
        "metrics": {
            "accounting_equation_count": sum(
                len(trial["accounting_equations"]) for trial in trials
            ),
            "document_count": 8,
            "document_unique_structure_count": 8,
            "mapped_item_verified_by_codex_count": sum(
                len(trial["verified_mappings"]) for trial in trials
            ),
            "mapped_money_value_cell_count": sum(
                len(mapping["money_values"])
                for trial in trials
                for mapping in trial["verified_mappings"]
            ),
            "mapped_percentage_corroboration_cell_count": sum(
                len(mapping["percentage_corroboration"])
                for trial in trials
                for mapping in trial["verified_mappings"]
            ),
            "negative_family_control_count": sum(
                len(trial["negative_family_controls"]) for trial in trials
            ),
            "source_only_total_verified_count": 8,
            "standalone_margin_mapping_count": sum(
                any(mapping["report_norm_id"] == 1944 for mapping in trial["verified_mappings"])
                for trial in trials
            ),
            "transformer_disagreement_preserved_count": sum(
                len(trial["transformer_disagreements"]) for trial in trials
            ),
            "unresolved_mapping_count": 0,
        },
        "state": "ANNUAL_2025_LOAN_QUALITY_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {
            **material,
            "result_id": "annual2025lq8bcv1:result:" + canonical_json_sha256_v1(material),
        }
    )


def _validate_result(value: Any) -> dict[str, Any]:
    expected_fields = {
        "authority",
        "claim_boundary",
        "format_version",
        "input_refs",
        "metrics",
        "result_id",
        "state",
        "trials",
    }
    if (
        type(value) is not dict
        or set(value) != expected_fields
        or value.get("format_version") != FORMAT_VERSION
        or value.get("claim_boundary") != CLAIM_BOUNDARY
        or value.get("state") != "ANNUAL_2025_LOAN_QUALITY_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value.get("authority"), _AUTHORITY)
        or type(value.get("trials")) is not list
        or len(value["trials"]) != 8
        or type(value.get("metrics")) is not dict
    ):
        raise _error("annual verified loan-quality result identity/shape drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id")
    if result_id != "annual2025lq8bcv1:result:" + canonical_json_sha256_v1(material):
        raise _error("annual verified loan-quality result content identity drifted")
    mapped = money = percentage = negative = disagreements = margins = equations = 0
    for ordinal, (trial, code) in enumerate(
        zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True), 1
    ):
        if (
            type(trial) is not dict
            or trial.get("document_ordinal") != ordinal
            or trial.get("document_provenance") != code
            or trial.get("status") != "SCHEMA_MAPPING_VERIFIED_BY_CODEX"
            or trial.get("whole_document_family_absence_claim") is not False
            or type(trial.get("verified_mappings")) is not list
            or type(trial.get("negative_family_controls")) is not list
            or type(trial.get("accounting_equations")) is not list
            or len(trial["accounting_equations"]) != 2
            or type(trial.get("percentage_equations")) is not list
            or type(trial.get("transformer_disagreements")) is not list
        ):
            raise _error("annual verified loan-quality trial identity drifted")
        core = [
            mapping["report_norm_id"]
            for mapping in trial["verified_mappings"]
            if mapping.get("report_norm_id") in {747, 748, 749, 750, 751}
        ]
        if core != [747, 748, 749, 750, 751]:
            raise _error("annual verified five-grade mapping order drifted")
        seen_margin = [
            mapping
            for mapping in trial["verified_mappings"]
            if mapping.get("report_norm_id") == 1944
        ]
        if len(seen_margin) > 1:
            raise _error("annual standalone margin mapping duplicated")
        for mapping in trial["verified_mappings"]:
            if (
                type(mapping) is not dict
                or type(mapping.get("money_values")) is not list
                or len(mapping["money_values"]) != 2
                or type(mapping.get("percentage_corroboration")) is not list
                or len(mapping["percentage_corroboration"]) not in {0, 2}
                or mapping.get("parent_report_norm_id") != 746
                or mapping.get("status")
                not in {"VERIFIED_BY_CODEX", "VERIFIED_BY_PROJECT_OWNER_AND_CODEX"}
            ):
                raise _error("annual verified loan-quality mapping shape drifted")
            money += len(mapping["money_values"])
            percentage += len(mapping["percentage_corroboration"])
        mapped += len(trial["verified_mappings"])
        margins += len(seen_margin)
        negative += len(trial["negative_family_controls"])
        disagreements += len(trial["transformer_disagreements"])
        equations += len(trial["accounting_equations"])
    expected_metrics = {
        "accounting_equation_count": equations,
        "document_count": 8,
        "document_unique_structure_count": 8,
        "mapped_item_verified_by_codex_count": mapped,
        "mapped_money_value_cell_count": money,
        "mapped_percentage_corroboration_cell_count": percentage,
        "negative_family_control_count": negative,
        "source_only_total_verified_count": 8,
        "standalone_margin_mapping_count": margins,
        "transformer_disagreement_preserved_count": disagreements,
        "unresolved_mapping_count": 0,
    }
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("annual verified loan-quality result metrics drifted")
    return canonical_clone_v1(value)


def build_live_annual_2025_loan_quality_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay every fixed annual authority and derive the verified result."""

    semantic_index = _strict_json(
        _fixed_bytes(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256),
        "annual semantic index",
    )
    crop_manifest = _strict_json(
        _fixed_bytes(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256),
        "annual crop manifest",
    )
    review_sha = _review_file_sha256()
    review = _review(_strict_json(_fixed_bytes(REVIEW_PATH, review_sha), "annual pixel review"))
    scanner = _load_module(
        PROJECT_ROOT / "scripts/experiments/scan_loan_quality_full_document_vietocr_v1.py",
        "annual_2025_quality_scanner_live",
    )
    structure_scan = scanner.build_loan_quality_full_document_scan_v1(
        semantic_index,
        enable_extended_annual_variants=True,
    )
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    margin_context, margin_ref = _margin_context()
    return build_annual_2025_loan_quality_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        margin_context,
        crop_manifest_sha256=EXPECTED_CROP_MANIFEST_SHA256,
        margin_context_ref=margin_ref,
        review_sha256=review_sha,
    )


def validate_annual_2025_loan_quality_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild the persisted result from all fixed live authorities."""

    persisted = _validate_result(value)
    rebuilt = build_live_annual_2025_loan_quality_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("annual verified loan-quality result does not replay exactly")
    return rebuilt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    args = parser.parse_args()
    if args.write_review:
        raw = canonical_json_bytes_v1(review_blueprint_v1()) + b"\n"
        if REVIEW_PATH.exists():
            if REVIEW_PATH.read_bytes() != raw:
                raise _error("refusing to overwrite a different annual pixel review")
        else:
            REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
            REVIEW_PATH.write_bytes(raw)
        return 0
    if args.validate is not None:
        validate_annual_2025_loan_quality_8bank_codex_verified_mapping_replay_v1(
            _strict_json(args.validate.read_bytes(), "persisted annual result")
        )
        return 0
    result = build_live_annual_2025_loan_quality_8bank_codex_verified_mapping_v1()
    raw = canonical_json_bytes_v1(result) + b"\n"
    if args.output.exists():
        if args.output.read_bytes() != raw:
            raise _error(f"refusing to overwrite a different result: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
