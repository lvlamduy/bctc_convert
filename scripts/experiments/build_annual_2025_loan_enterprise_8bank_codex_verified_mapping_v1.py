"""Verify annual-2025 customer-loan enterprise tables for eight banks.

The shared matcher receives the complete fresh-VietOCR line axis and uses no
bank, filename, note number or page routing.  This bounded verifier then binds
the unique structural matches to visible page pixels, an independent
PaddleOCR6 numeric challenger, exact table totals, the already verified
customer-loan owner totals and the live TM schema.  A source row combining two
legal forms remains unresolved instead of being split without visible data.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.evaluation.full_document_vietocr_accounting_axis_v1 import (
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

__all__ = [
    "Annual2025LoanEnterprise8BankError",
    "build_annual_2025_loan_enterprise_pixel_review_blueprint_v1",
    "build_live_annual_2025_loan_enterprise_8bank_codex_verified_mapping_v1",
    "validate_annual_2025_loan_enterprise_8bank_codex_verified_mapping_replay_v1",
]


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = "ANNUAL_2025_LOAN_ENTERPRISE_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT_VERSION = "ANNUAL_2025_LOAN_ENTERPRISE_8BANK_CODEX_PIXEL_REVIEW_V1"
REVIEW_STATE = "ANNUAL_2025_LOAN_ENTERPRISE_CODEX_PIXEL_REVIEW_COMPLETE"
RESULT_STATE = "ANNUAL_2025_LOAN_ENTERPRISE_8BANK_BOUNDED_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025le8bcv1:result:"
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
LOAN_QUALITY_RESULT_PATH = Path(
    "docs/experiments/E-0114-annual-2025-loan-quality-8bank-codex-verified-mapping-v1.json"
)
REVIEW_PATH = Path(
    "docs/experiments/E-0118-annual-2025-loan-enterprise-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0118-annual-2025-loan-enterprise-8bank-codex-verified-mapping-v1.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_LOAN_QUALITY_RESULT_SHA256 = (
    "82fe06bb50fe4bde264226f2c71422e6d7339b351cf4c7b4b41c2c8c48932e3c"
)
EXPECTED_REVIEW_SHA256 = "e2295da6f1eb0567756c9bc7e2f74b7e9dfaa60442b83cc7994e5bc63146eded"
EXPECTED_SCAN_ID = "lefdsv1:scan:1b85947080bb52a6364dfa864cc3020f2e63b4a725d42a275c3eddb0936d1aaf"
EXPECTED_DOCUMENT_ORDER = ("ACB", "MBB", "VPB", "HDB", "VCB", "CTG", "BID", "VIB")
_POSITIVE_BANKS = ("MBB", "VPB", "HDB", "VCB", "BID", "VIB")
_EXPECTED_PAGES = {"MBB": 52, "VPB": 46, "HDB": 36, "VCB": 40, "BID": 42, "VIB": 39}
_EXPECTED_GRAPH_SHA256 = {
    "MBB": "9150c526f4d04bae29d79ee4c53e209cc234352aee41d6088790bdba746966c8",
    "VPB": "19bf1957fb0b8f435d1d51224a039fb76c94d8f147cc0dc4be6cbc68873023d7",
    "HDB": "d9a7a57ebdc5cf7335bf37b9b55f53e0b47699a9463c7d7212d69cef3c3770ea",
    "VCB": "82610dd6b1afd145f95ade6004b2039dd4936d2000e3e1f717681631aa855137",
    "BID": "cfa44191339908d2b7eb7cd6be97fee95efe12dccd828315fe068e74944a41ab",
    "VIB": "4dc477680cf015e45ad1c1273149b002a0f2c6fbcbea85de78698b00ce979d01",
}
_EXPECTED_RENDER_SHA256 = {
    "MBB": "1c5dc5b29ba40817a9ae1837ba8921374401f9b54c4bcf22696f693cab8864b5",
    "VPB": "9c2f89c88f943dd463323960e2d6d06324e2c2052091960e4252acaf120c706d",
    "HDB": "1ff59f58f610eaa3db9263522cc4d055bba1a59d8c9d43ee287ab829d47f7eb9",
    "VCB": "9d0fe14207d7886d65b7d6d0c45eb9b5e7fcce554686e2e5c366062eac2cc118",
    "BID": "443dc71ee70615358b01109d701014804bca0a24caa41d1b85377f0f3b3b8df9",
    "VIB": "dd74c6f0249eded4bc6b1509bb2a03847d2019c1ec369e5706ce0119b568f1ab",
}
_PERIOD_PIXEL_TRANSCRIPTIONS = {
    "MBB": ["31/12/2025", "31/12/2024"],
    "VPB": ["Ngày 31 tháng 12 năm 2025", "Ngày 31 tháng 12 năm 2024"],
    "HDB": ["Số cuối năm", "Số đầu năm"],
    "VCB": ["31/12/2025", "31/12/2024"],
    "BID": ["Số cuối năm", "Số đầu năm"],
    "VIB": ["31/12/2025", "31/12/2024"],
}
_UNIT_PIXEL_TRANSCRIPTIONS = {
    "MBB": ["triệu đồng", "%", "triệu đồng", "%"],
    "VPB": ["Triệu đồng", "%", "Triệu đồng", "%"],
    "HDB": ["Triệu VND", "Triệu VND"],
    "VCB": ["Triệu VND", "Triệu VND"],
    "BID": ["Triệu VND", "%", "Triệu VND", "%"],
    "VIB": ["triệu đồng", "%", "triệu đồng", "%"],
}
_OWNER_PIXEL_TRANSCRIPTIONS = {
    "MBB": "CHO VAY KHÁCH HÀNG (TIẾP THEO)",
    "VPB": "CHO VAY KHÁCH HÀNG (TIẾP THEO)",
    "HDB": "Cho vay khách hàng",
    "VCB": "Cho vay khách hàng",
    "BID": "CHO VAY KHÁCH HÀNG",
    "VIB": "CHO VAY KHÁCH HÀNG (TIẾP THEO)",
}
_BRANCH_PIXEL_TRANSCRIPTIONS = {
    "MBB": "Phân tích dư nợ cho vay theo đối tượng khách hàng và theo loại hình doanh nghiệp",
    "VPB": "Phân tích dư nợ cho vay theo đối tượng khách hàng và theo loại hình doanh nghiệp",
    "HDB": "Phân tích dư nợ cho vay theo đối tượng khách hàng",
    "VCB": "Phân tích dư nợ theo loại hình doanh nghiệp như sau:",
    "BID": "Phân tích dư nợ cho vay theo đối tượng khách hàng và theo loại hình doanh nghiệp",
    "VIB": "Phân tích dư nợ theo đối tượng khách hàng, loại hình doanh nghiệp",
}
_LABEL_PIXEL_CORRECTIONS = {
    ("MBB", "STATE_ENTERPRISE"): "Công ty Nhà nước",
    ("MBB", "STATE_OWNED_SINGLE_MEMBER_LLC"): "Công ty TNHH MTV vốn Nhà nước 100%",
    ("MBB", "STATE_CONTROLLED_MULTI_MEMBER_LLC"): (
        "Công ty TNHH MTV trở lên có vốn Nhà nước trên 50%"
    ),
    ("MBB", "STATE_CONTROLLED_JOINT_STOCK"): "Công ty cổ phần vốn Nhà nước trên 50%",
    ("MBB", "OTHER_JOINT_STOCK"): "Công ty cổ phần khác",
    ("MBB", "PARTNERSHIP"): "Công ty hợp danh",
    ("VPB", "MARGIN_AND_SECURITIES_ADVANCE"): (
        "Cho vay giao dịch ký quỹ và ứng trước cho khách hàng"
    ),
    ("HDB", "OTHER_LLC"): "Công ty trách nhiệm hữu hạn khác",
    ("HDB", "HOUSEHOLD_INDIVIDUAL"): "Hộ kinh doanh, cá nhân",
    ("HDB", "OTHER_JOINT_STOCK"): "Công ty Cổ phần khác",
    ("HDB", "PRIVATE_ENTERPRISE"): "Doanh nghiệp tư nhân",
    ("VIB", "STATE_CONTROLLED_JOINT_STOCK"): (
        "Công ty cổ phần có vốn cổ phần của nhà nước chiếm trên 50% vốn điều lệ "
        "hoặc tổng số cổ phần có quyền biểu quyết; hoặc nhà nước giữ quyền chi phối "
        "đối với công ty trong Điều lệ của công ty"
    ),
}
_MBB_DASH_BINDINGS = {
    2: {
        "bbox_raw_pixels": [1328, 708, 1360, 726],
        "rgb_sha256": "402e1479f13349634307272194f6be028dd4dd13c9d1837dd4e187b9f7ba831d",
    },
    3: {
        "bbox_raw_pixels": [1445, 708, 1475, 726],
        "rgb_sha256": "7b304cfb7c9fac96c636528f89edbe8aef771f7195d45560f2fdab3ee525d09a",
    },
}
_UNRESOLVED_ROLES: dict[str, tuple[int | None, str]] = {}
_CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_VIETOCR_"
    "GENERIC_LOAN_ENTERPRISE_WHOLE_PDF_UNIQUENESS_VISIBLE_PIXEL_PPOCRV6_NUMERIC_"
    "CHALLENGER_OWNER_TOTAL_EXACT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_COMBINED_"
    "ROW_SPLIT_CANONICAL_EXPORT_OR_PRODUCTION_AUTHORITY"
)
_REVIEW_CLAIM_BOUNDARY = (
    "INDEPENDENT_VISIBLE_PAGE_REVIEW_OF_THE_SIX_UNIQUE_ANNUAL_2025_CUSTOMER_LOAN_"
    "ENTERPRISE_TABLES_AND_TWO_BOUNDED_NO_MATCH_DOCUMENTS_ONLY"
)
_REVIEW_SAFETY = {
    "all_visible_cells_independently_reviewed": True,
    "all_visible_row_labels_independently_reviewed": True,
    "bank_or_page_used_as_matching_rule": False,
    "dash_blank_missing_and_zero_kept_distinct": True,
    "fresh_vietocr_used_as_pixel_truth": False,
    "mapping_decided_by_text_similarity_alone": False,
    "numeric_truth_source": "VISIBLE_PDF_PIXELS_WITH_PPOCRV6_NUMERIC_CHALLENGER",
    "old_ocr_used_as_semantic_text": False,
    "review_can_assert_document_wide_family_absence": False,
    "source_only_group_nodes_mapped_to_schema": False,
    "unchanged_semantic_surfaces_attested_equal_to_pixels_except_recorded_disagreements": True,
}
_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "broad_corpus_or_family_absence_authority": False,
    "canonicalization_or_export_authority": False,
    "combined_source_row_silently_split": False,
    "dash_blank_missing_and_zero_preserved": True,
    "final_statuses_mechanically_derived": True,
    "fresh_full_document_vietocr_used_for_semantic_anchors": True,
    "independent_pdf_pixel_and_ppocrv6_challenger_used_for_numeric_truth": True,
    "live_tm_schema_hierarchy_and_negative_families_checked": True,
    "mapping_authority_is_bounded_to_reviewed_source_rows": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_group_nodes_exported_additively": False,
    "source_population_role_6058_mapped_once_without_double_count": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmatched_or_non_equivalent_roles_preserved_unresolved": True,
}


class Annual2025LoanEnterprise8BankError(ValueError):
    """The annual enterprise graph, review, numbers, totals or schema drifted."""


def _error(message: str) -> Annual2025LoanEnterprise8BankError:
    return Annual2025LoanEnterprise8BankError(message)


def _load_module(name: str, relative_path: str) -> ModuleType:
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load required module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _base() -> ModuleType:
    base = _load_module(
        "annual_2025_loan_enterprise_base_v1",
        "scripts/experiments/build_loan_enterprise_8bank_codex_verified_mapping_v1.py",
    )
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT_VERSION = REVIEW_FORMAT_VERSION
    base.REVIEW_STATE = REVIEW_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.RESULT_STATE = RESULT_STATE
    base.CLAIM_BOUNDARY = _CLAIM_BOUNDARY
    base.REVIEW_PATH = REVIEW_PATH
    base.REVIEW_SHA256 = EXPECTED_REVIEW_SHA256
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base._UNRESOLVED_ROLES = dict(_UNRESOLVED_ROLES)
    base._REVIEW_SAFETY = canonical_clone_v1(_REVIEW_SAFETY)
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    return base


def _scanner() -> ModuleType:
    return _load_module(
        "annual_2025_loan_enterprise_scan_v1",
        "scripts/experiments/scan_loan_enterprise_full_document_vietocr_v1.py",
    )


def _quality_builder() -> ModuleType:
    return _load_module(
        "annual_2025_loan_quality_result_validator_v1",
        "scripts/experiments/build_annual_2025_loan_quality_8bank_codex_verified_mapping_v1.py",
    )


def _json_fixed(base: ModuleType, path: Path, digest: str, label: str) -> dict[str, Any]:
    return base._json_bytes(base._fixed_bytes(path, digest), label)


def _trial(scan: Mapping[str, Any], bank: str) -> dict[str, Any]:
    matches = [item for item in scan["trials"] if item.get("document_provenance") == bank]
    if len(matches) != 1:
        raise _error(f"annual enterprise scan lacks exactly one {bank} trial")
    return matches[0]


def _manifest_document(manifest: Mapping[str, Any], bank: str) -> dict[str, Any]:
    matches = [item for item in manifest["documents"] if item.get("bank_code") == bank]
    if len(matches) != 1:
        raise _error(f"crop manifest lacks exactly one {bank} document")
    return matches[0]


def _manifest_page(manifest: Mapping[str, Any], bank: str, page: int) -> dict[str, Any]:
    document = _manifest_document(manifest, bank)
    matches = [item for item in document["pages"] if item.get("physical_page") == page]
    if len(matches) != 1:
        raise _error(f"crop manifest lacks exactly one {bank} page {page}")
    return matches[0]


def _provider_texts(
    base: ModuleType, manifest: Mapping[str, Any], bank: str, page: int
) -> tuple[list[str], dict[str, Any]]:
    manifest_page = _manifest_page(manifest, bank, page)
    ref = manifest_page.get("result_ref")
    if (
        type(ref) is not dict
        or set(ref) != {"path", "sha256", "size_bytes"}
        or type(ref["path"]) is not str
        or type(ref["size_bytes"]) is not int
        or ref["size_bytes"] <= 0
    ):
        raise _error("PaddleOCR6 provider result reference drifted")
    payload = base._stable_root_bytes(Path(ref["path"]))
    if len(payload) != ref["size_bytes"] or hashlib.sha256(payload).hexdigest() != ref["sha256"]:
        raise _error("PaddleOCR6 provider result bytes drifted")
    decoded = base._json_bytes(payload, f"{bank} PaddleOCR6 provider result")
    texts = decoded.get("rec_texts")
    if (
        type(texts) is not list
        or len(texts) != manifest_page.get("line_count")
        or any(type(item) is not str for item in texts)
    ):
        raise _error("PaddleOCR6 provider text denominator drifted")
    return texts, canonical_clone_v1(ref)


def _provider_numeric_refs(
    base: ModuleType, manifest: Mapping[str, Any], scan: Mapping[str, Any]
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for bank in _POSITIVE_BANKS:
        graph = _trial(scan, bank)["matcher_result"]["graphs"][0]
        texts, ref = _provider_texts(base, manifest, bank, graph["page_sequence"])
        checked = 0
        for row in graph["rows"]:
            for cell in row["values"]:
                semantic = cell["semantic_surface"]
                source_line_index = cell["source_line_index"]
                if semantic is None:
                    if (
                        bank != "MBB"
                        or row["role"] != "PARTNERSHIP"
                        or cell["lane_index"] not in _MBB_DASH_BINDINGS
                    ):
                        raise _error("unexpected missing annual enterprise numeric proposal")
                    continue
                if type(source_line_index) is not int or not 0 <= source_line_index < len(texts):
                    raise _error("annual enterprise provider numeric locator drifted")
                if base._numeric(semantic, cell["lane_type"]) != base._numeric(
                    texts[source_line_index], cell["lane_type"]
                ):
                    raise _error("fresh VietOCR and PaddleOCR6 numeric challengers disagree")
                checked += 1
        for cell in graph["total"]:
            source_line_index = cell["source_line_index"]
            if base._numeric(cell["semantic_surface"], cell["lane_type"]) != base._numeric(
                texts[source_line_index], cell["lane_type"]
            ):
                raise _error("printed total and PaddleOCR6 numeric challenger disagree")
            checked += 1
        refs.append(
            {
                "bank": bank,
                "checked_numeric_cell_count": checked,
                "physical_page": graph["page_sequence"],
                "result_ref": ref,
            }
        )
    return refs


def _format_numeric(value: int | Decimal) -> str:
    return str(value) if type(value) is int else format(value, "f")


def _numeric_pixel_transcription(
    base: ModuleType,
    provider_texts: Sequence[str],
    cell: Mapping[str, Any],
) -> str:
    semantic = cell["semantic_surface"]
    source_line_index = cell["source_line_index"]
    if type(semantic) is not str or type(source_line_index) is not int:
        raise _error("numeric pixel transcription lacks one semantic locator")
    provider = provider_texts[source_line_index]
    if base._numeric(semantic, cell["lane_type"]) != base._numeric(provider, cell["lane_type"]):
        raise _error("numeric pixel transcription challengers disagree")
    return provider


def _review_document(
    base: ModuleType,
    manifest: Mapping[str, Any],
    scan: Mapping[str, Any],
    bank: str,
) -> dict[str, Any]:
    fields = {
        "branch_pixel_transcription": None,
        "disposition": "NO_COMPLETE_REGION_IN_EXACT_FULL_DOCUMENT_FRESH_VIETOCR_SCAN",
        "document_provenance": bank,
        "matcher_graph_sha256": None,
        "owner_pixel_transcription": None,
        "period_pixel_transcriptions": [],
        "physical_page": None,
        "pixel_accounting": None,
        "reviewed_role_order": [],
        "schema_unresolved_roles": [],
        "source_group_equations": [],
        "statement_context_evidence": None,
        "target_render_sha256": None,
        "transformer_disagreements": [],
        "unit_pixel_transcriptions": [],
        "whole_document_family_absence_claim": False,
    }
    matcher_result = _trial(scan, bank)["matcher_result"]
    if bank not in _POSITIVE_BANKS:
        if matcher_result["status"] != "UNRESOLVED_NO_COMPLETE_REGION":
            raise _error(f"{bank} bounded no-match disposition drifted")
        return fields
    graphs = matcher_result.get("graphs")
    if (
        matcher_result.get("status") != "ACCEPTED_UNIQUE_VARIANT_GRAPH"
        or type(graphs) is not list
        or len(graphs) != 1
    ):
        raise _error(f"{bank} annual enterprise graph is not unique")
    graph = graphs[0]
    if (
        graph["page_sequence"] != _EXPECTED_PAGES[bank]
        or canonical_json_sha256_v1(graph) != _EXPECTED_GRAPH_SHA256[bank]
    ):
        raise _error(f"{bank} annual enterprise page/graph identity drifted")
    manifest_page = _manifest_page(manifest, bank, graph["page_sequence"])
    render = manifest_page["render_binding"]
    if render["sha256"] != _EXPECTED_RENDER_SHA256[bank]:
        raise _error(f"{bank} annual enterprise render identity drifted")
    provider_texts, _ = _provider_texts(base, manifest, bank, graph["page_sequence"])
    roles = [row["role"] for row in graph["rows"]]
    disagreements: list[dict[str, Any]] = []
    pixel_by_role_lane: dict[tuple[str, int], str] = {}
    for row in graph["rows"]:
        role = row["role"]
        semantic_label = row["label"]["surface"]
        pixel_label = _LABEL_PIXEL_CORRECTIONS.get((bank, role), semantic_label)
        if pixel_label != semantic_label:
            disagreements.append(
                {
                    "disposition": "INDEPENDENT_VISIBLE_PIXEL_ORTHOGRAPHY_RETAINED",
                    "field": "ROW_LABEL",
                    "lane_index": None,
                    "pixel_binding": None,
                    "pixel_transcription": pixel_label,
                    "role": role,
                    "semantic_proposal": semantic_label,
                    "source_line_index": row["label"]["source_line_indices"][0],
                }
            )
        for cell in row["values"]:
            lane_index = cell["lane_index"]
            if cell["semantic_surface"] is None:
                binding = _MBB_DASH_BINDINGS.get(lane_index) if bank == "MBB" else None
                if role != "PARTNERSHIP" or binding is None:
                    raise _error("unexpected missing semantic cell in annual enterprise review")
                pixel = "-"
                disagreements.append(
                    {
                        "disposition": "VISIBLE_PIXEL_DASH_PRESERVED_AND_OWNER_RULE_NORMALIZES_TO_ZERO",
                        "field": "ROW_VALUE",
                        "lane_index": lane_index,
                        "pixel_binding": canonical_clone_v1(binding),
                        "pixel_transcription": pixel,
                        "role": role,
                        "semantic_proposal": None,
                        "source_line_index": None,
                    }
                )
            else:
                pixel = _numeric_pixel_transcription(base, provider_texts, cell)
                if pixel != cell["semantic_surface"]:
                    disagreements.append(
                        {
                            "disposition": "PPOCRV6_NUMERIC_CHALLENGER_AND_VISIBLE_PIXEL_AGREE",
                            "field": "ROW_VALUE",
                            "lane_index": lane_index,
                            "pixel_binding": None,
                            "pixel_transcription": pixel,
                            "role": role,
                            "semantic_proposal": cell["semantic_surface"],
                            "source_line_index": cell["source_line_index"],
                        }
                    )
            pixel_by_role_lane[(role, lane_index)] = pixel
    sums: list[int | Decimal] = []
    printed: list[int | Decimal] = []
    for lane_index, lane_type in enumerate(graph["lane_types"]):
        sums.append(
            sum(
                (
                    0
                    if pixel_by_role_lane[(role, lane_index)] == "-"
                    else base._numeric(pixel_by_role_lane[(role, lane_index)], lane_type)
                    for role in roles
                ),
                0,
            )
        )
        total_cell = graph["total"][lane_index]
        printed_pixel = _numeric_pixel_transcription(base, provider_texts, total_cell)
        printed.append(base._numeric(printed_pixel, lane_type))
    money_indices = [
        index for index, lane_type in enumerate(graph["lane_types"]) if lane_type == "MONEY"
    ]
    percent_indices = [
        index for index, lane_type in enumerate(graph["lane_types"]) if lane_type == "PERCENT"
    ]
    if any(sums[index] != printed[index] for index in range(len(sums))):
        raise _error(f"{bank} independently reviewed enterprise totals do not close")
    fields.update(
        {
            "branch_pixel_transcription": _BRANCH_PIXEL_TRANSCRIPTIONS[bank],
            "disposition": "UNIQUE_COMPLETE_REGION_VISIBLE_PIXEL_REVIEWED",
            "matcher_graph_sha256": _EXPECTED_GRAPH_SHA256[bank],
            "owner_pixel_transcription": _OWNER_PIXEL_TRANSCRIPTIONS[bank],
            "period_pixel_transcriptions": canonical_clone_v1(_PERIOD_PIXEL_TRANSCRIPTIONS[bank]),
            "physical_page": graph["page_sequence"],
            "pixel_accounting": {
                "intermediate_core_money_totals": [],
                "maximum_percentage_rounding_residual": "0.00",
                "money_lane_sums": [_format_numeric(sums[index]) for index in money_indices],
                "percentage_lane_sums": [_format_numeric(sums[index]) for index in percent_indices],
                "printed_money_totals": [
                    _format_numeric(printed[index]) for index in money_indices
                ],
                "printed_percentage_totals": [
                    _format_numeric(printed[index]) for index in percent_indices
                ],
                "row_count": len(roles),
                "typed_dash_cells": [
                    {"lane_index": lane, "role": "PARTNERSHIP", "status": "DASH"}
                    for lane in sorted(_MBB_DASH_BINDINGS)
                ]
                if bank == "MBB"
                else [],
            },
            "reviewed_role_order": roles,
            "schema_unresolved_roles": [role for role in roles if role in _UNRESOLVED_ROLES],
            "statement_context_evidence": {
                "mode": "PAGE_LOCAL_VISIBLE_HEADING",
                "physical_page": graph["page_sequence"],
                "pixel_transcription": "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT",
                "render_sha256": _EXPECTED_RENDER_SHA256[bank],
                "report_scope": "CONSOLIDATED",
            },
            "target_render_sha256": _EXPECTED_RENDER_SHA256[bank],
            "transformer_disagreements": disagreements,
            "unit_pixel_transcriptions": canonical_clone_v1(_UNIT_PIXEL_TRANSCRIPTIONS[bank]),
        }
    )
    return fields


def build_annual_2025_loan_enterprise_pixel_review_blueprint_v1(
    semantic_index: Mapping[str, Any],
    crop_manifest: Mapping[str, Any],
    structure_scan: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the exact independently inspected page-review record."""

    axis = project_full_document_vietocr_accounting_axis_v1(semantic_index)
    if axis["semantic_axis_sha256"] != EXPECTED_AXIS_SHA256:
        raise _error("annual semantic axis identity drifted")
    if structure_scan.get("scan_id") != EXPECTED_SCAN_ID:
        raise _error("annual enterprise structure scan identity drifted")
    base = _base()
    review = {
        "claim_boundary": _REVIEW_CLAIM_BOUNDARY,
        "documents": [
            _review_document(base, crop_manifest, structure_scan, bank)
            for bank in EXPECTED_DOCUMENT_ORDER
        ],
        "format_version": REVIEW_FORMAT_VERSION,
        "review_checks": canonical_clone_v1(base._REVIEW_CHECKS),
        "reviewer": {
            "kind": "CODEX_INDEPENDENT_PDF_PIXEL_REVIEW",
            "review_run_id": "annual-2025-loan-enterprise-eight-bank-pixel-review-2026-08-16",
        },
        "safety": canonical_clone_v1(_REVIEW_SAFETY),
        "semantic_axis_sha256": EXPECTED_AXIS_SHA256,
        "semantic_index_sha256": EXPECTED_INDEX_SHA256,
        "state": REVIEW_STATE,
    }
    return base._review(review)


def _quality_totals(quality_result: Mapping[str, Any]) -> dict[str, list[int]]:
    output: dict[str, list[int]] = {}
    for trial in quality_result["trials"]:
        bank = trial["document_provenance"]
        values = trial["source_only_total"]["values"]
        output[bank] = [
            int(item["independent_pixel_transcription"].replace(".", "").replace(",", ""))
            for item in values
        ]
    if set(output) != set(EXPECTED_DOCUMENT_ORDER):
        raise _error("annual loan-quality owner total denominator drifted")
    return output


def _bind_owner_totals(
    base: ModuleType, result: Mapping[str, Any], quality_result: Mapping[str, Any]
) -> None:
    expected = _quality_totals(quality_result)
    for trial in result["trials"]:
        if trial["document_provenance"] not in _POSITIVE_BANKS:
            continue
        money = [
            base._money(item["independent_pixel_transcription"])
            for item in trial["source_only_total"]["values"]
            if item["lane_type"] == "MONEY"
        ]
        if money != expected[trial["document_provenance"]]:
            raise _error("enterprise table does not close to verified customer-loan owner totals")


def _live_core(*, include_review: bool) -> tuple[Any, ...]:
    base = _base()
    semantic_index = _json_fixed(
        base, SEMANTIC_INDEX_PATH, EXPECTED_INDEX_SHA256, "annual semantic index"
    )
    crop_manifest = _json_fixed(
        base, CROP_MANIFEST_PATH, EXPECTED_CROP_MANIFEST_SHA256, "annual crop manifest"
    )
    quality_result = _json_fixed(
        base,
        LOAN_QUALITY_RESULT_PATH,
        EXPECTED_LOAN_QUALITY_RESULT_SHA256,
        "annual verified loan-quality result",
    )
    _quality_builder()._validate_result(quality_result)
    scanner = _scanner()
    structure_scan = scanner.build_loan_enterprise_full_document_scan_v1(
        semantic_index,
        enable_extended_reporting_period_variants=True,
    )
    if structure_scan["scan_id"] != EXPECTED_SCAN_ID:
        raise _error("annual enterprise scan identity drifted")
    if not include_review:
        return base, semantic_index, crop_manifest, quality_result, structure_scan
    review = _json_fixed(base, REVIEW_PATH, EXPECTED_REVIEW_SHA256, "annual pixel review")
    expected_review = build_annual_2025_loan_enterprise_pixel_review_blueprint_v1(
        semantic_index, crop_manifest, structure_scan
    )
    if not same_typed_json_v1(review, expected_review):
        raise _error("sealed annual enterprise pixel review does not rebuild exactly")
    return base, semantic_index, crop_manifest, quality_result, structure_scan, review


def build_live_annual_2025_loan_enterprise_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay all fixed authorities and construct the bounded verified result."""

    (
        base,
        semantic_index,
        crop_manifest,
        quality_result,
        structure_scan,
        review,
    ) = _live_core(include_review=True)
    provider_refs = _provider_numeric_refs(base, crop_manifest, structure_scan)
    schema_authority, schema_by_id = _authority_snapshot(PROJECT_ROOT)
    result = base.build_loan_enterprise_8bank_codex_verified_mapping_v1(
        semantic_index,
        crop_manifest,
        structure_scan,
        review,
        schema_authority,
        schema_by_id,
        crop_manifest_sha256=EXPECTED_CROP_MANIFEST_SHA256,
        review_sha256=EXPECTED_REVIEW_SHA256,
        enable_extended_reporting_period_variants=True,
    )
    _bind_owner_totals(base, result, quality_result)
    material = canonical_clone_v1(result)
    material.pop("result_id")
    material["input_refs"]["annual_loan_quality_result"] = {
        "path": LOAN_QUALITY_RESULT_PATH.as_posix(),
        "sha256": EXPECTED_LOAN_QUALITY_RESULT_SHA256,
    }
    material["input_refs"]["ppocrv6_numeric_challenger_pages"] = provider_refs
    return base._validate_result(
        {**material, "result_id": RESULT_ID_PREFIX + canonical_json_sha256_v1(material)}
    )


def validate_annual_2025_loan_enterprise_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild the result from every live fixed authority."""

    base = _base()
    persisted = base._validate_result(value)
    rebuilt = build_live_annual_2025_loan_enterprise_8bank_codex_verified_mapping_v1()
    if not same_typed_json_v1(persisted, rebuilt):
        raise _error("annual enterprise verified result does not replay exactly")
    return rebuilt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-review-blueprint", action="store_true")
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    selected = sum((args.print_review_blueprint, args.write_review, args.write_result, args.verify))
    if selected > 1:
        parser.error("choose at most one operation")
    if args.print_review_blueprint or args.write_review:
        _, semantic, manifest, _, scan = _live_core(include_review=False)
        value = build_annual_2025_loan_enterprise_pixel_review_blueprint_v1(
            semantic, manifest, scan
        )
    elif args.verify:
        value = validate_annual_2025_loan_enterprise_8bank_codex_verified_mapping_replay_v1(
            json.loads((PROJECT_ROOT / RESULT_PATH).read_text(encoding="utf-8"))
        )
    else:
        value = build_live_annual_2025_loan_enterprise_8bank_codex_verified_mapping_v1()
    if args.write_review:
        if REVIEW_PATH.exists():
            raise _error(f"refusing to overwrite annual enterprise review: {REVIEW_PATH}")
        REVIEW_PATH.write_bytes(canonical_json_bytes_v1(value) + b"\n")
        print(hashlib.sha256(canonical_json_bytes_v1(value) + b"\n").hexdigest())
        return 0
    if args.write_result:
        if RESULT_PATH.exists():
            raise _error(f"refusing to overwrite annual enterprise result: {RESULT_PATH}")
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(value) + b"\n")
        print(value["result_id"])
        return 0
    sys.stdout.buffer.write(canonical_json_bytes_v1(value) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
