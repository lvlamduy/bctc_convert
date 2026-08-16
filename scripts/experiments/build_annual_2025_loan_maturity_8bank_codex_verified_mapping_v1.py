"""Verify annual-2025 loan-maturity tables across eight audited bank PDFs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
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
FORMAT_VERSION = "ANNUAL_2025_LOAN_MATURITY_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_LOAN_MATURITY_8BANK_CODEX_PIXEL_REVIEW_V1"
CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_DOCUMENT_COMPLETE_PDF_FRESH_"
    "VIETOCR_GENERIC_MATURITY_OWNER_CHILD_BBOX_PERIOD_UNIT_TOTAL_AND_ACCOUNTING_"
    "VARIANTS_PLUS_INDEPENDENT_VISIBLE_PIXEL_AND_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_"
    "OR_PRODUCTION_AUTHORITY"
)
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0115-annual-2025-loan-maturity-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0115-annual-2025-loan-maturity-8bank-codex-verified-mapping-v1.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_SCAN_ID = "lmfdsv1:scan:c11df08875bb3757212b53e793d32de3e6995e66431a760d24473d6bf64010ac"
EXPECTED_REVIEW_SHA256 = "1d871a81671c5d351dd7f950b661728705316d65dc18d3a66d2094786f135f10"
_ROLES = (
    ("SHORT_TERM", 753, "+ Ngắn hạn"),
    ("MEDIUM_TERM", 754, "+ Trung hạn"),
    ("LONG_TERM", 755, "+ Dài hạn"),
)
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_mapping_rule": False,
    "broad_corpus_authority": False,
    "canonicalization_or_export_authority": False,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_visible_pdf_pixels_used_for_numeric_truth": True,
    "live_tm_schema_hierarchy_checked": True,
    "mapping_authority_is_bounded_to_reviewed_source_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "transformer_numeric_or_diacritic_conflicts_silently_corrected": False,
}


class Annual2025LoanMaturity8BankError(ValueError):
    """The annual maturity scan, pixels, accounting, or schema drifted."""


def _error(message: str) -> Annual2025LoanMaturity8BankError:
    return Annual2025LoanMaturity8BankError(message)


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required experiment module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _fixed_bytes(path: Path, expected_sha256: str) -> bytes:
    full = PROJECT_ROOT / path
    descriptor = os.open(
        full,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error(f"fixed input is not a regular file: {path}")
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
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
        raise _error(f"fixed input changed while reading: {path}")
    payload = b"".join(chunks)
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise _error(f"fixed input SHA-256 drifted: {path}")
    return payload


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise _error(f"{label} contains duplicate JSON key {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                _error(f"{label} contains non-finite number {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise _error(f"{label} must be one JSON object")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _review_blueprint() -> dict[str, Any]:
    banks = [
        {
            "bank_code": "ACB",
            "physical_page": 50,
            "target_render_sha256": "d09d8579c3cefdce5158fae5529195e147956a8af088295130c3117eadbfa349",
            "owner_evidence": [
                50,
                "CHO VAY KHÁCH HÀNG",
                "d09d8579c3cefdce5158fae5529195e147956a8af088295130c3117eadbfa349",
            ],
            "branch": "Theo kỳ hạn",
            "periods": ["31.12.2025", "31.12.2024"],
            "lane_types": ["MONEY", "MONEY"],
            "rows": [
                ["SHORT_TERM", "Ngắn hạn", ["444.709.964", "391.723.409"]],
                ["MEDIUM_TERM", "Trung hạn", ["21.569.837", "17.286.255"]],
                ["LONG_TERM", "Dài hạn", ["220.497.551", "171.676.584"]],
            ],
            "core_total": ["686.777.352", "580.686.248"],
            "optional_margin": None,
            "additional_source_population": None,
            "grand_total": [],
            "transformer_disagreements": [],
        },
        {
            "bank_code": "MBB",
            "physical_page": 51,
            "target_render_sha256": "35d892c6a207fd426cad7d4da67376c980707babdc82bb0b7dd958b9086c1da7",
            "owner_evidence": [
                51,
                "CHO VAY KHÁCH HÀNG",
                "35d892c6a207fd426cad7d4da67376c980707babdc82bb0b7dd958b9086c1da7",
            ],
            "branch": "Phân tích dư nợ theo thời gian",
            "periods": ["31/12/2025", "31/12/2024"],
            "lane_types": ["MONEY", "MONEY"],
            "rows": [
                ["SHORT_TERM", "Nợ ngắn hạn", ["587.136.924", "413.956.564"]],
                ["MEDIUM_TERM", "Nợ trung hạn", ["127.883.727", "88.454.207"]],
                ["LONG_TERM", "Nợ dài hạn", ["353.958.134", "263.953.346"]],
            ],
            "core_total": [],
            "optional_margin": [
                "Các khoản cho vay giao dịch ký quỹ và ứng trước cho khách hàng giao dịch đầu tư chứng khoán - ngắn hạn",
                ["15.040.585", "10.293.729"],
            ],
            "additional_source_population": None,
            "grand_total": ["1.084.019.370", "776.657.846"],
            "transformer_disagreements": [],
        },
        {
            "bank_code": "VPB",
            "physical_page": 45,
            "target_render_sha256": "7731043083c02a34caf583425c5a1cce03ffe29233e2febccc39fe3df342e842",
            "owner_evidence": [
                45,
                "CHO VAY KHÁCH HÀNG",
                "7731043083c02a34caf583425c5a1cce03ffe29233e2febccc39fe3df342e842",
            ],
            "branch": "Phân tích dư nợ theo thời gian cho vay gốc",
            "periods": ["Ngày 31 tháng 12 năm 2025", "Ngày 31 tháng 12 năm 2024 (Trình bày lại)"],
            "lane_types": ["MONEY", "MONEY"],
            "rows": [
                ["SHORT_TERM", "Nợ ngắn hạn", ["341.736.692", "248.405.690"]],
                ["MEDIUM_TERM", "Nợ trung hạn", ["329.817.543", "270.968.248"]],
                ["LONG_TERM", "Nợ dài hạn", ["238.254.176", "168.884.649"]],
            ],
            "core_total": [],
            "optional_margin": [
                "Cho vay giao dịch ký quỹ và ứng trước cho khách hàng",
                ["34.093.219", "9.512.536"],
            ],
            "additional_source_population": None,
            "grand_total": ["943.901.630", "697.771.123"],
            "transformer_disagreements": [
                [
                    "LONG_TERM_CURRENT",
                    "238,254.176",
                    "238.254.176",
                    "PUNCTUATION_ONLY_PIXEL_RECONCILIATION",
                ]
            ],
        },
        {
            "bank_code": "HDB",
            "physical_page": 36,
            "target_render_sha256": "1ff59f58f610eaa3db9263522cc4d055bba1a59d8c9d43ee287ab829d47f7eb9",
            "owner_evidence": [
                36,
                "Cho vay khách hàng",
                "1ff59f58f610eaa3db9263522cc4d055bba1a59d8c9d43ee287ab829d47f7eb9",
            ],
            "branch": "Phân tích dư nợ cho vay theo thời hạn gốc của khoản vay",
            "periods": ["Số cuối năm", "Số đầu năm"],
            "lane_types": ["MONEY", "MONEY"],
            "rows": [
                ["SHORT_TERM", "Nợ ngắn hạn (đến 01 năm)", ["270.919.421", "227.158.574"]],
                [
                    "MEDIUM_TERM",
                    "Nợ trung hạn (trên 01 đến 05 năm)",
                    ["175.459.659", "138.247.896"],
                ],
                ["LONG_TERM", "Nợ dài hạn (trên 05 năm)", ["99.991.699", "65.899.599"]],
            ],
            "core_total": ["546.370.779", "431.306.069"],
            "optional_margin": None,
            "additional_source_population": {
                "label": "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày 01 tháng 7 năm 2024",
                "parent_values": ["-", "11.178.772"],
                "breakdown_label": "Nợ ngắn hạn (đến 01 năm)",
                "breakdown_values": ["-", "11.178.772"],
            },
            "grand_total": ["546.370.779", "442.484.841"],
            "transformer_disagreements": [
                [
                    "SHORT_TERM_LABEL",
                    "Nơ ngần hạn (đến 01 năm)",
                    "Nợ ngắn hạn (đến 01 năm)",
                    "DIACRITIC_ONLY_PIXEL_RECONCILIATION",
                ],
                [
                    "GRAND_TOTAL_COMPARATIVE",
                    "442.464.841",
                    "442.484.841",
                    "ONE_DIGIT_PIXEL_RECONCILIATION",
                ],
            ],
        },
        {
            "bank_code": "VCB",
            "physical_page": 40,
            "target_render_sha256": "9d0fe14207d7886d65b7d6d0c45eb9b5e7fcce554686e2e5c366062eac2cc118",
            "owner_evidence": [
                39,
                "Cho vay khách hàng",
                "f6680605fdd69b8973a97de5949f4222bac54d62970255ad0713454b529cf2de",
            ],
            "branch": "Phân tích dư nợ theo thời hạn cho vay như sau:",
            "periods": ["31/12/2025", "31/12/2024"],
            "lane_types": ["MONEY", "MONEY"],
            "rows": [
                ["SHORT_TERM", "Nợ ngắn hạn", ["981.706.312", "915.576.792"]],
                ["MEDIUM_TERM", "Nợ trung hạn", ["81.371.777", "59.453.709"]],
                ["LONG_TERM", "Nợ dài hạn", ["610.447.586", "474.168.398"]],
            ],
            "core_total": ["1.673.525.675", "1.449.198.899"],
            "optional_margin": None,
            "additional_source_population": None,
            "grand_total": [],
            "transformer_disagreements": [
                [
                    "MEDIUM_TERM_LABEL",
                    "Nợ trùng hạn",
                    "Nợ trung hạn",
                    "DIACRITIC_ONLY_PIXEL_RECONCILIATION",
                ]
            ],
        },
        {
            "bank_code": "CTG",
            "physical_page": 44,
            "target_render_sha256": "06bac9233047b7679b7d40e2a11d40ebea3c3f69fc139a3da2d6419c1c0e5223",
            "owner_evidence": [
                44,
                "CHO VAY KHÁCH HÀNG (TIẾP THEO)",
                "06bac9233047b7679b7d40e2a11d40ebea3c3f69fc139a3da2d6419c1c0e5223",
            ],
            "branch": "Theo kỳ hạn",
            "periods": ["31.12.2025", "31.12.2024"],
            "lane_types": ["MONEY", "MONEY"],
            "rows": [
                ["SHORT_TERM", "Cho vay ngắn hạn", ["1.232.479.318", "1.137.144.961"]],
                ["MEDIUM_TERM", "Cho vay trung hạn", ["129.395.349", "99.036.675"]],
                ["LONG_TERM", "Cho vay dài hạn", ["630.398.201", "485.773.078"]],
            ],
            "core_total": ["1.992.272.868", "1.721.954.714"],
            "optional_margin": None,
            "additional_source_population": None,
            "grand_total": [],
            "transformer_disagreements": [
                [
                    "MEDIUM_TERM_LABEL",
                    "Cho vay trùng hạn",
                    "Cho vay trung hạn",
                    "DIACRITIC_ONLY_PIXEL_RECONCILIATION",
                ]
            ],
        },
        {
            "bank_code": "BID",
            "physical_page": 42,
            "target_render_sha256": "443dc71ee70615358b01109d701014804bca0a24caa41d1b85377f0f3b3b8df9",
            "owner_evidence": [
                41,
                "CHO VAY KHÁCH HÀNG",
                "5b7980206c405decc1ddf5064bf2e2f5acf8906875698cc108268376b45bc488",
            ],
            "branch": "Phân tích dư nợ theo thời gian gốc của khoản vay",
            "periods": ["Số cuối năm", "Số đầu năm (Trình bày lại)"],
            "lane_types": ["MONEY", "MONEY"],
            "rows": [
                ["SHORT_TERM", "Nợ ngắn hạn (Dưới 1 năm)", ["1.441.586.157", "1.332.621.811"]],
                ["MEDIUM_TERM", "Nợ trung hạn (Từ 1 tới 5 năm)", ["164.058.293", "104.835.026"]],
                ["LONG_TERM", "Nợ dài hạn (Trên 5 năm)", ["767.310.624", "618.625.583"]],
            ],
            "core_total": ["2.372.955.074", "2.056.082.420"],
            "optional_margin": None,
            "additional_source_population": None,
            "grand_total": [],
            "transformer_disagreements": [],
        },
        {
            "bank_code": "VIB",
            "physical_page": 38,
            "target_render_sha256": "f2a3aab2957c7f60330e3ae1dd2ee86b80289b2c3142f32a82e944f9d9500f44",
            "owner_evidence": [
                38,
                "CHO VAY KHÁCH HÀNG (tiếp theo)",
                "f2a3aab2957c7f60330e3ae1dd2ee86b80289b2c3142f32a82e944f9d9500f44",
            ],
            "branch": "Phân tích dư nợ theo thời gian cho vay gốc",
            "periods": ["31/12/2025", "31/12/2024"],
            "lane_types": ["MONEY", "PERCENT", "MONEY", "PERCENT"],
            "rows": [
                ["SHORT_TERM", "Nợ ngắn hạn", ["158.864.423", "41,59", "142.051.273", "43,84"]],
                ["MEDIUM_TERM", "Nợ trung hạn", ["43.794.654", "11,47", "20.244.697", "6,25"]],
                ["LONG_TERM", "Nợ dài hạn", ["179.312.939", "46,94", "161.713.743", "49,91"]],
            ],
            "core_total": ["381.972.016", "100,00", "324.009.713", "100,00"],
            "optional_margin": None,
            "additional_source_population": None,
            "grand_total": [],
            "transformer_disagreements": [
                [
                    "SHORT_TERM_CURRENT",
                    "158.864 423",
                    "158.864.423",
                    "PUNCTUATION_ONLY_PIXEL_RECONCILIATION",
                ],
                [
                    "MEDIUM_TERM_CURRENT_PERCENT",
                    "11.47",
                    "11,47",
                    "DECIMAL_SEPARATOR_PIXEL_RECONCILIATION",
                ],
                [
                    "LONG_TERM_CURRENT_PERCENT",
                    "46.94",
                    "46,94",
                    "DECIMAL_SEPARATOR_PIXEL_RECONCILIATION",
                ],
                [
                    "LONG_TERM_COMPARATIVE_PERCENT",
                    "49 91",
                    "49,91",
                    "MISSING_DECIMAL_SEPARATOR_PIXEL_RECONCILIATION",
                ],
            ],
        },
    ]
    normalized_banks: list[dict[str, Any]] = []
    for bank in banks:
        owner_page, owner_text, owner_render = bank.pop("owner_evidence")
        normalized_banks.append(
            {
                **bank,
                "owner_evidence": {
                    "physical_page": owner_page,
                    "pixel_transcription": owner_text,
                    "render_sha256": owner_render,
                },
                "statement_context_evidence": {
                    "mode": "PAGE_LOCAL_VISIBLE_HEADING",
                    "physical_page": bank["physical_page"],
                    "pixel_transcription": "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT",
                    "render_sha256": bank["target_render_sha256"],
                    "report_scope": "CONSOLIDATED",
                },
            }
        )
    return {
        "banks": normalized_banks,
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": REVIEW_FORMAT,
        "review_checks": {
            "accounting_equations_independently_recomputed": True,
            "bbox_row_and_column_associations_visually_confirmed": True,
            "branch_owner_and_ordered_children_visually_confirmed": True,
            "period_unit_and_report_scope_visually_confirmed": True,
            "source_pdf_and_bound_whole_page_render_opened": True,
            "totals_optional_margin_and_extra_population_boundaries_confirmed": True,
        },
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_VISIBLE_PDF_PIXEL_AND_ACCOUNTING_REVIEW",
            "review_run_id": "E-0115-ANNUAL-2025",
        },
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": "CODEX_PIXEL_REVIEW_COMPLETE",
    }


def _review(value: Any) -> dict[str, Any]:
    expected = _review_blueprint()
    if not same_typed_json_v1(value, expected):
        raise _error("annual maturity pixel review differs from the fixed visible-pixel ledger")
    return canonical_clone_v1(value)


def _money(value: str) -> int:
    compact = value.strip().replace(" ", "")
    if compact in {"-", "–", "—"}:
        return 0
    negative = compact.startswith("(") and compact.endswith(")")
    compact = compact.strip("()").lstrip("+")
    if compact.startswith("-"):
        negative = True
        compact = compact[1:]
    digits = compact.replace(".", "").replace(",", "")
    if not digits.isdigit():
        raise _error(f"money surface is invalid: {value}")
    number = int(digits)
    return -number if negative else number


def _percent(value: str) -> Decimal:
    try:
        number = Decimal(value.strip().replace(" ", ".").replace(",", "."))
    except InvalidOperation as exc:
        raise _error(f"percentage surface is invalid: {value}") from exc
    if not number.is_finite():
        raise _error("percentage surface is non-finite")
    return number


def _has_disagreement(disagreements: Sequence[Sequence[str]], semantic: str, pixel: str) -> bool:
    return any(item[1] == semantic and item[2] == pixel for item in disagreements)


def _typed_value(
    semantic: str,
    pixel: str,
    lane_type: str,
    disagreements: Sequence[Sequence[str]],
) -> int | Decimal:
    parser = _money if lane_type == "MONEY" else _percent if lane_type == "PERCENT" else None
    if parser is None:
        raise _error("unsupported annual maturity lane type")
    pixel_value = parser(pixel)
    try:
        semantic_value = parser(semantic)
    except Annual2025LoanMaturity8BankError:
        if not _has_disagreement(disagreements, semantic, pixel):
            raise
        return pixel_value
    if semantic_value != pixel_value and not _has_disagreement(disagreements, semantic, pixel):
        raise _error("Transformer/pixel numeric conflict lacks explicit reconciliation")
    return pixel_value


def _compatible_text(semantic: str, pixel: str) -> bool:
    left = normalize_vietnamese_anchor_v1(semantic)
    right = normalize_vietnamese_anchor_v1(pixel)
    return left == right or left in right or right in left


def _document(documents: Sequence[Mapping[str, Any]], bank_code: str) -> Mapping[str, Any]:
    matches = [item for item in documents if item.get("bank_code") == bank_code]
    if len(matches) != 1:
        raise _error("annual document provenance denominator drifted")
    return matches[0]


def _page(document: Mapping[str, Any], physical_page: int) -> Mapping[str, Any]:
    pages = document.get("pages")
    if type(pages) is not list:
        raise _error("annual crop-manifest page inventory drifted")
    matches = [item for item in pages if item.get("physical_page") == physical_page]
    if len(matches) != 1:
        raise _error("review page is not unique in annual crop manifest")
    return matches[0]


def _render_sha256(page: Mapping[str, Any]) -> str:
    binding = page.get("render_binding")
    if type(binding) is not dict or type(binding.get("sha256")) is not str:
        raise _error("annual render binding drifted")
    return binding["sha256"]


def _schema(schema_by_id: Mapping[int, Any]) -> dict[str, Any]:
    required = {716, 752, 753, 754, 755, 5747}
    if not required.issubset(schema_by_id):
        raise _error("live TM schema lacks the maturity hierarchy")
    owner = schema_by_id[716]
    parent = schema_by_id[752]
    if (
        owner.canonical_name != "Cho vay khách hàng"
        or parent.canonical_name != "Phân tích dư nợ theo thời gian đáo hạn"
        or parent.parent_id != 716
        or list(parent.children) != [753, 754, 755, 5747]
    ):
        raise _error("live TM maturity owner/parent hierarchy drifted")
    mappings: list[dict[str, Any]] = []
    display_orders: list[int] = []
    for role, report_norm_id, canonical_name in _ROLES:
        item = schema_by_id[report_norm_id]
        if (
            item.canonical_name != canonical_name
            or item.parent_id != 752
            or item.statement_type != "TM"
            or "CONSOLIDATED" not in item.scope
        ):
            raise _error(f"live maturity child {report_norm_id} drifted")
        display_orders.append(item.display_order)
        mappings.append(
            {
                "canonical_name": canonical_name,
                "report_norm_id": report_norm_id,
                "role": role,
            }
        )
    margin = schema_by_id[5747]
    if (
        display_orders != sorted(display_orders)
        or margin.canonical_name != "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán"
        or margin.parent_id != 752
        or margin.display_order <= display_orders[-1]
    ):
        raise _error("live maturity child ordering or optional margin drifted")
    return {
        "mapped_roles": mappings,
        "optional_margin": {
            "canonical_name": margin.canonical_name,
            "report_norm_id": 5747,
        },
    }


def _target_region(trial: Mapping[str, Any], graph: Mapping[str, Any]) -> Mapping[str, Any]:
    regions = trial["region_scan"]["regions"]
    matches = [
        region
        for region in regions
        if region["branch_source_line_index"] == graph["branch"]["source_line_index"]
        and region["branch_match"]["surface"] == graph["branch"]["surface"]
    ]
    if len(matches) != 1:
        raise _error("annual maturity target region is not unique")
    return matches[0]


def _compare_graph_vector(
    graph_vector: Sequence[Mapping[str, Any]],
    pixel_vector: Sequence[str],
    lane_types: Sequence[str],
    disagreements: Sequence[Sequence[str]],
) -> list[int | Decimal]:
    if len(graph_vector) != len(pixel_vector) or len(pixel_vector) != len(lane_types):
        raise _error("annual maturity graph/pixel lane denominator drifted")
    return [
        _typed_value(item["surface"], pixel, lane_type, disagreements)
        for item, pixel, lane_type in zip(graph_vector, pixel_vector, lane_types, strict=True)
    ]


def build_annual_2025_loan_maturity_8bank_codex_verified_mapping_v1(
    semantic_index: Any,
    crop_manifest: Any,
    structure_scan: Any,
    review: Any,
    schema_by_id: Mapping[int, Any],
    *,
    review_sha256: str,
) -> dict[str, Any]:
    """Derive all bounded annual maturity mappings from exact live inputs."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("annual semantic accounting axis drifted")
    reviewed = _review(review)
    if review_sha256 != EXPECTED_REVIEW_SHA256:
        raise _error("annual maturity pixel review SHA-256 drifted")
    expected_metrics = {
        "accepted_numeric_graph_count": 0,
        "complete_context_region_count": 8,
        "document_count": 8,
        "document_multiple_complete_context_region_count": 0,
        "document_unique_candidate_count": 8,
        "mapping_verified_count": 0,
        "near_region_count": 309,
        "ordered_anchor_region_count": 8,
        "structure_resolved_numeric_unresolved_count": 8,
        "total_document_candidate_count": 8,
        "unresolved_document_count": 0,
    }
    if (
        type(structure_scan) is not dict
        or structure_scan.get("scan_id") != EXPECTED_SCAN_ID
        or not same_typed_json_v1(structure_scan.get("metrics"), expected_metrics)
    ):
        raise _error("annual maturity full-document structure scan drifted")
    if type(crop_manifest) is not dict or type(crop_manifest.get("documents")) is not list:
        raise _error("annual crop manifest shape drifted")
    if len(crop_manifest["documents"]) != 8 or len(structure_scan.get("trials", [])) != 8:
        raise _error("annual maturity input document denominator drifted")
    schema = _schema(schema_by_id)
    trials: list[dict[str, Any]] = []
    mapped_value_cells = 0
    percentage_cells = 0
    margin_count = 0
    additional_population_count = 0
    disagreement_count = 0
    for bank_review, scan_trial, expected_bank in zip(
        reviewed["banks"],
        structure_scan["trials"],
        EXPECTED_DOCUMENT_ORDER,
        strict=True,
    ):
        if (
            bank_review["bank_code"] != expected_bank
            or scan_trial["bank_provenance"] != expected_bank
        ):
            raise _error("annual maturity bank order drifted")
        matcher_result = scan_trial["matcher_result"]
        if (
            matcher_result["status"] != "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
            or matcher_result["document_candidate_count"] != 1
            or matcher_result["unresolved_reasons"]
        ):
            raise _error("annual bank lacks one unique maturity structure")
        graph = matcher_result["result"]["graph"]
        if type(graph) is not dict or graph["arithmetic_status"] != (
            "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
        ):
            raise _error("annual maturity graph authority boundary drifted")
        region = _target_region(scan_trial, graph)
        if region["page_sequence"] != bank_review["physical_page"]:
            raise _error("annual maturity review page and unique region disagree")
        manifest_document = _document(crop_manifest["documents"], expected_bank)
        target_page = _page(manifest_document, bank_review["physical_page"])
        if _render_sha256(target_page) != bank_review["target_render_sha256"]:
            raise _error("annual maturity target render drifted")
        for evidence_name in ("owner_evidence", "statement_context_evidence"):
            evidence = bank_review[evidence_name]
            if (
                _render_sha256(_page(manifest_document, evidence["physical_page"]))
                != evidence["render_sha256"]
            ):
                raise _error(f"annual maturity {evidence_name} render drifted")
        if (
            bank_review["statement_context_evidence"]["report_scope"] != "CONSOLIDATED"
            or not _compatible_text(graph["branch"]["surface"], bank_review["branch"])
            or not _compatible_text(
                graph["owner"]["surface"],
                bank_review["owner_evidence"]["pixel_transcription"],
            )
            or graph["unit_scope"]["lane_types"] != bank_review["lane_types"]
        ):
            raise _error("annual maturity scope/owner/branch/lane review drifted")
        expected_periods = (
            ["CURRENT_PERIOD_END", "COMPARATIVE_PERIOD_START"]
            if normalize_vietnamese_anchor_v1(bank_review["periods"][0]) == "so cuoi nam"
            else ["31/12/2025", "31/12/2024"]
        )
        if [item["period"] for item in graph["axes"]] != expected_periods:
            raise _error("annual maturity period axis drifted")
        disagreements = bank_review["transformer_disagreements"]
        disagreement_count += len(disagreements)
        row_money: list[list[int]] = []
        mappings: list[dict[str, Any]] = []
        if len(graph["rows"]) != 3 or len(bank_review["rows"]) != 3:
            raise _error("annual maturity row denominator drifted")
        for graph_row, review_row, schema_row in zip(
            graph["rows"], bank_review["rows"], schema["mapped_roles"], strict=True
        ):
            role, pixel_label, pixel_values = review_row
            if (
                graph_row["role"] != role
                or schema_row["role"] != role
                or not _compatible_text(graph_row["label_surface"], pixel_label)
            ):
                raise _error("annual maturity row role/label/schema drifted")
            typed = _compare_graph_vector(
                graph_row["values"], pixel_values, bank_review["lane_types"], disagreements
            )
            money_values = [
                int(value)
                for value, lane_type in zip(typed, bank_review["lane_types"], strict=True)
                if lane_type == "MONEY"
            ]
            row_money.append(money_values)
            mapped_value_cells += len(money_values)
            percentage_cells += sum(
                lane_type == "PERCENT" for lane_type in bank_review["lane_types"]
            )
            mappings.append(
                {
                    **schema_row,
                    "source_label": pixel_label,
                    "source_values": [
                        pixel
                        for pixel, lane_type in zip(
                            pixel_values, bank_review["lane_types"], strict=True
                        )
                        if lane_type == "MONEY"
                    ],
                    "status": "VERIFIED_BY_CODEX",
                }
            )
        sums = [sum(row[axis_index] for row in row_money) for axis_index in range(2)]
        core_pixel = bank_review["core_total"]
        if core_pixel:
            core_typed = _compare_graph_vector(
                graph["total"]["core_values"],
                core_pixel,
                bank_review["lane_types"],
                disagreements,
            )
            core_money = [
                int(value)
                for value, lane_type in zip(core_typed, bank_review["lane_types"], strict=True)
                if lane_type == "MONEY"
            ]
            if core_money != sums:
                raise _error("annual maturity core total does not equal three roles")
        margin_mapping: dict[str, Any] | None = None
        margin = bank_review["optional_margin"]
        margin_money = [0, 0]
        if margin is not None:
            graph_margin = graph["optional_margin"]
            if type(graph_margin) is not dict or not _compatible_text(
                graph_margin["label_surface"], margin[0]
            ):
                raise _error("annual maturity optional margin label drifted")
            margin_typed = _compare_graph_vector(
                graph_margin["values"], margin[1], bank_review["lane_types"], disagreements
            )
            margin_money = [int(value) for value in margin_typed]
            margin_count += 1
            mapped_value_cells += 2
            margin_mapping = {
                **schema["optional_margin"],
                "source_label": margin[0],
                "source_values": margin[1],
                "status": "VERIFIED_BY_CODEX",
            }
        elif graph["optional_margin"] is not None:
            raise _error("annual graph exposes an unreviewed optional margin")
        additional = bank_review["additional_source_population"]
        additional_result: dict[str, Any] | None = None
        additional_money = [0, 0]
        if additional is not None:
            if len(graph.get("additional_source_populations", [])) != 1:
                raise _error("annual graph lost the reviewed extra source population")
            additional_money = [_money(value) for value in additional["parent_values"]]
            if additional_money != [_money(value) for value in additional["breakdown_values"]]:
                raise _error("annual extra population parent/breakdown does not reconcile")
            additional_population_count += 1
            additional_result = {
                **additional,
                "accounting_role": "OUTSIDE_STRICT_THREE_BUCKET_CORE",
                "dash_interpreted_as_zero": True,
                "mapping_status": "VERIFIED_SOURCE_ONLY_NOT_MAPPED_IN_MATURITY_SCHEMA",
            }
        elif graph.get("additional_source_populations"):
            raise _error("annual graph exposes an unreviewed extra source population")
        grand_pixel = bank_review["grand_total"]
        if grand_pixel:
            grand_typed = _compare_graph_vector(
                graph["total"]["grand_values"],
                grand_pixel,
                bank_review["lane_types"],
                disagreements,
            )
            grand_money = [
                int(value)
                for value, lane_type in zip(grand_typed, bank_review["lane_types"], strict=True)
                if lane_type == "MONEY"
            ]
            if grand_money != [
                sums[index] + margin_money[index] + additional_money[index] for index in range(2)
            ]:
                raise _error("annual maturity grand total equation does not close")
        if "PERCENT" in bank_review["lane_types"]:
            percent_positions = [
                index
                for index, lane_type in enumerate(bank_review["lane_types"])
                if lane_type == "PERCENT"
            ]
            for position in percent_positions:
                if sum(_percent(row[2][position]) for row in bank_review["rows"]) != Decimal(
                    "100.00"
                ):
                    raise _error("annual maturity percentage population does not close")
            percentage_cells += len(percent_positions)
        trials.append(
            {
                "accounting_check": "THREE_BUCKET_CORE_AND_ALL_PRESENTED_TOTALS_CORROBORATED",
                "additional_source_population": additional_result,
                "bank_code": expected_bank,
                "branch_pixel_transcription": bank_review["branch"],
                "graph_id": matcher_result["graph_id"],
                "mapped_items": mappings,
                "optional_margin_mapping": margin_mapping,
                "period_pixel_transcriptions": bank_review["periods"],
                "physical_page": bank_review["physical_page"],
                "source_only_total": {
                    "core_total": core_pixel,
                    "grand_total": grand_pixel,
                    "status": "VERIFIED_SOURCE_ONLY_NO_REPORT_NORM_ID",
                },
                "status": "VERIFIED_BY_CODEX",
                "target_render_sha256": bank_review["target_render_sha256"],
                "transformer_disagreements": disagreements,
                "unit_lane_types": bank_review["lane_types"],
            }
        )
    material = {
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "crop_manifest_sha256": EXPECTED_CROP_MANIFEST_SHA256,
            "pixel_review_path": REVIEW_PATH.as_posix(),
            "pixel_review_sha256": review_sha256,
            "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
            "semantic_index_sha256": EXPECTED_INDEX_SHA256,
            "structure_scan_id": EXPECTED_SCAN_ID,
        },
        "metrics": {
            "accounting_equation_count": 26,
            "additional_source_population_count": additional_population_count,
            "document_count": 8,
            "document_unique_structure_count": 8,
            "mapped_item_verified_by_codex_count": 24 + margin_count,
            "mapped_money_value_cell_count": mapped_value_cells,
            "mapped_optional_margin_count": margin_count,
            "mapped_percentage_corroboration_cell_count": percentage_cells,
            "source_only_total_verified_count": 8,
            "transformer_disagreement_preserved_count": disagreement_count,
            "unresolved_mapping_count": 0,
        },
        "state": "ANNUAL_2025_LOAN_MATURITY_8BANK_CODEX_VERIFICATION_COMPLETE",
        "trials": trials,
    }
    return _validate_result(
        {
            **material,
            "result_id": "annual2025lm8bcv1:result:" + canonical_json_sha256_v1(material),
        }
    )


def _validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "authority",
        "claim_boundary",
        "format_version",
        "input_refs",
        "metrics",
        "result_id",
        "state",
        "trials",
    }:
        raise _error("annual maturity verified result fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "ANNUAL_2025_LOAN_MATURITY_8BANK_CODEX_VERIFICATION_COMPLETE"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["trials"]) is not list
        or len(value["trials"]) != 8
    ):
        raise _error("annual maturity verified result identity/authority drifted")
    material = canonical_clone_v1(value)
    result_id = material.pop("result_id")
    if result_id != "annual2025lm8bcv1:result:" + canonical_json_sha256_v1(material):
        raise _error("annual maturity result content identity drifted")
    expected_metrics = {
        "accounting_equation_count": 26,
        "additional_source_population_count": 1,
        "document_count": 8,
        "document_unique_structure_count": 8,
        "mapped_item_verified_by_codex_count": 26,
        "mapped_money_value_cell_count": 52,
        "mapped_optional_margin_count": 2,
        "mapped_percentage_corroboration_cell_count": 8,
        "source_only_total_verified_count": 8,
        "transformer_disagreement_preserved_count": 9,
        "unresolved_mapping_count": 0,
    }
    if not same_typed_json_v1(value["metrics"], expected_metrics):
        raise _error("annual maturity result metrics drifted")
    for trial, expected_bank in zip(value["trials"], EXPECTED_DOCUMENT_ORDER, strict=True):
        if (
            type(trial) is not dict
            or trial.get("bank_code") != expected_bank
            or trial.get("status") != "VERIFIED_BY_CODEX"
            or type(trial.get("mapped_items")) is not list
            or len(trial["mapped_items"]) != 3
            or [item.get("report_norm_id") for item in trial["mapped_items"]] != [753, 754, 755]
            or any(item.get("status") != "VERIFIED_BY_CODEX" for item in trial["mapped_items"])
        ):
            raise _error("annual maturity verified trial shape/order drifted")
    return canonical_clone_v1(value)


def build_live_annual_2025_loan_maturity_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay fixed annual authorities and derive the verified mapping."""

    semantic_index = _strict_json(
        _fixed_bytes(SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256),
        "annual maturity semantic index",
    )
    crop_manifest = _strict_json(
        _fixed_bytes(CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256),
        "annual maturity crop manifest",
    )
    review = _review(
        _strict_json(
            _fixed_bytes(REVIEW_PATH, EXPECTED_REVIEW_SHA256),
            "annual maturity pixel review",
        )
    )
    scanner = _load_module(
        PROJECT_ROOT / "scripts/experiments/scan_loan_maturity_full_document_vietocr_v1.py",
        "annual_2025_maturity_scanner_live",
    )
    structure_scan = scanner.build_loan_maturity_full_document_scan_v1(
        semantic_index,
        enable_extended_annual_variants=True,
    )
    _schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    return build_annual_2025_loan_maturity_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_by_id,
        review_sha256=EXPECTED_REVIEW_SHA256,
    )


def validate_annual_2025_loan_maturity_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild the annual verified result from all fixed authorities."""

    persisted = _validate_result(value)
    rebuilt = build_live_annual_2025_loan_maturity_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("annual maturity verified result does not replay exactly")
    return rebuilt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    args = parser.parse_args()
    if args.write_review:
        review_bytes = canonical_json_bytes_v1(_review_blueprint())
        review_path = PROJECT_ROOT / REVIEW_PATH
        if review_path.exists():
            if review_path.read_bytes() != review_bytes:
                raise _error("refusing to overwrite a different annual maturity pixel review")
        else:
            review_path.parent.mkdir(parents=True, exist_ok=True)
            review_path.write_bytes(review_bytes)
        print(_file_sha256(review_path))
        return 0
    if args.validate is not None:
        path = args.validate if args.validate.is_absolute() else PROJECT_ROOT / args.validate
        validate_annual_2025_loan_maturity_8bank_codex_verified_mapping_replay_v1(
            _strict_json(path.read_bytes(), "persisted annual maturity result")
        )
        return 0
    result = build_live_annual_2025_loan_maturity_8bank_codex_verified_mapping_v1()
    output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    payload = canonical_json_bytes_v1(result)
    if output.exists():
        if output.read_bytes() != payload:
            raise _error(f"refusing to overwrite different annual maturity result: {output}")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
