"""Verify annual-2025 corporate-income-tax notes in eight bank reports.

The annual profile configures the existing income-tax graph, source numeric
challenger and replay validator.  It adds only generic annual presentation
variants: issuer-specific tax components, optional adjustment rows, blank
comparative cells and net deferred-tax subtables.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1, canonical_json_bytes_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]

FORMAT_VERSION = "ANNUAL_2025_INCOME_TAX_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_INCOME_TAX_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_INCOME_TAX_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025it8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_INCOME_TAX_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025it8bcv1:pixel-review:"
REVIEW_RUN_ID = "E-0146"
REVIEW_PATH = Path(
    "docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0146-annual-2025-income-tax-8bank-codex-verified-mapping-v1.json"
)
SEMANTIC_INDEX_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/verified-index/"
    "semantic_index.json"
)
CROP_MANIFEST_PATH = Path(
    "output/calibration/annual-2025-8bank-full-document-vietocr-v1/crop_manifest.json"
)
EXPECTED_INDEX_SHA256 = "98bb9854e699230da86538cf024ef3f4817b9e2f4dd2b2a75f46198f00e4247d"
EXPECTED_CROP_MANIFEST_SHA256 = "17d12a4d6b1dfaf0e243300757fd225b8c9cca80810a2d856efdb55a5b4ac000"
EXPECTED_AXIS_SHA256 = "aa81f553fda69315e84b7adbda13347c25a4490b016fc9660ff4f2cd49795ce7"
EXPECTED_SCAN_ID = "itfdsv1:scan:0d2375111d922f4082595dd791f7dc9765f7c59d8aae00e92c93374c656bad26"
EXPECTED_RESULT_ID: str | None = (
    "annual2025it8bcv1:result:013190ee28e94bcff30b92e68e9aa08c5c88d5d26b8e4a5da8170aa1c8d26863"
)
VARIANT_PROFILE = "GENERIC_ANNUAL_AND_INTERIM_V2"

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_INCOME_TAX_VARIANT_GRAPH_VISIBLE_PDF_PPOCRV6_"
    "NUMERIC_CHALLENGER_ANNUAL_PERIOD_UNIT_OPTIONAL_COMPONENT_BLANK_"
    "PRESERVATION_EXACT_ACCOUNTING_AND_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)

_AUTHORITY = {
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "blank_cell_interpreted_as_zero": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "dash_zero_policy_applied_only_to_visible_source_dash": True,
    "detailed_note_absence_bounded_to_bound_report": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_income_tax_rows": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_numeric_challenger_and_accounting_closure_required": True,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
    "whole_pdf_uniqueness_replayed": True,
}

_REVIEW_SAFETY = {
    "bank_page_or_filename_used_as_graph_rule": False,
    "blank_cell_interpreted_as_zero": False,
    "mapping_decided_by_text_similarity_alone": False,
    "old_ocr_used_as_semantic_anchor": False,
    "only_visible_source_dash_interpreted_as_zero": True,
    "source_parent_and_children_double_counted": False,
    "unmapped_source_rows_retained": True,
    "vietocr_used_as_numeric_truth": False,
    "visible_pdf_pixels_reviewed": True,
    "whole_pdf_uniqueness_replayed": True,
}

_SCHEMA_EXPECTED = {
    1142: (
        "II. THÔNG TIN BỔ SUNG CHO CÁC KHOẢN MỤC TRÌNH BÀY TRONG BẢNG KẾT QUẢ KINH DOANH",
        None,
        686,
    ),
    5723: ("Chi phí thuế thu nhập hiện hành", 5727, 812),
    5724: ("Năm hiện hành", 5723, 813),
    5725: ("Chi phí/(hoàn nhập) thuế thu nhập hoãn lại", 5727, 814),
    5726: ("Chi phí/(thu nhập) thuế thu nhập hoãn lại", 5725, 815),
    5727: ("Chi phí thuế thu nhập", 1142, 816),
    5728: ("Tổng lợi nhuận theo kế toán trước thuế hợp nhất", 5731, 817),
    5729: (
        "Thu nhập không chịu thuế (bao gồm cổ tức, lợi nhuận từ các đơn vị, các khoản điều chỉnh hợp nhất không chịu thuế) và các khoản khác",
        5731,
        818,
    ),
    5730: ("Các chi phí không được khấu trừ của riêng Ngân hàng", 5731, 819),
    5731: ("Thu nhập chịu thuế TNDN ước tính tại Việt Nam", 1142, 820),
    5732: ("Chi phí thuế TNDN hiện hành riêng Ngân hàng (i)", 5737, 821),
    5733: ("Điều chỉnh trong năm cho thuế thu nhập hiện hành của các năm trước (ii)", 5737, 822),
    5734: ("Chi phí thuế TNDN chi nhánh nước ngoài (iii)", 5737, 823),
    5735: ("Chi phí thuế TNDN của các công ty con (iv)", 5737, 824),
    5736: ("Chi phí/(hoàn nhập) thuế TNDN hoãn lại (v)", 5737, 825),
    5737: ("Chi phí thuế TNDN (i+ii+iii+iv+v)", 1142, 826),
}

_EXPECTED_PAGES = {
    "ACB": [71, 71],
    "MBB": [76, 76],
    "VPB": [64, 64],
    "HDB": [52, 52],
    "VCB": [62, 62],
    "CTG": [60, 60],
    "BID": [57, 57],
    "VIB": [53, 53],
}


class Annual2025IncomeTax8BankError(ValueError):
    """The annual tax graph, pixels, numbers, equations, or schema drifted."""


def _error(message: str) -> Annual2025IncomeTax8BankError:
    return Annual2025IncomeTax8BankError(message)


def _load_base() -> ModuleType:
    path = PROJECT_ROOT / "scripts/experiments/build_income_tax_8bank_codex_verified_mapping_v1.py"
    name = "annual_2025_income_tax_mapping_base_v1"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual income-tax support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _mapping_axes(
    base: ModuleType,
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    values: Mapping[str, Mapping[str, Any]],
    topology: str = "DIRECT_OR_WRAPPED_LABEL_TWO_ANNUAL_PERIOD_LANES",
) -> dict[str, Any]:
    return {
        "labels": [base._ref(page, line, text) for line, text in labels],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": topology,
        "values": canonical_clone_v1(values),
    }


def _mapping(
    base: ModuleType,
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: Mapping[str, Any],
    comparative: Mapping[str, Any],
    topology: str = "DIRECT_OR_WRAPPED_LABEL_TWO_ANNUAL_PERIOD_LANES",
) -> dict[str, Any]:
    return _mapping_axes(
        base,
        role,
        report_norm_id,
        page,
        labels,
        {"COMPARATIVE_PERIOD": comparative, "CURRENT_PERIOD": current},
        topology,
    )


def _direct(
    base: ModuleType,
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: tuple[int, str],
    comparative: tuple[int, str],
    topology: str = "DIRECT_OR_WRAPPED_LABEL_TWO_ANNUAL_PERIOD_LANES",
) -> dict[str, Any]:
    return _mapping(
        base,
        role,
        report_norm_id,
        page,
        labels,
        base._line(page, *current),
        base._line(page, *comparative),
        topology,
    )


def _aggregate(
    base: ModuleType,
    role: str,
    report_norm_id: int,
    page: int,
    labels: Sequence[tuple[int, str]],
    current: Sequence[tuple[int, str]],
    comparative: Sequence[tuple[int, str]],
) -> dict[str, Any]:
    return _mapping(
        base,
        role,
        report_norm_id,
        page,
        labels,
        base._sum(page, current),
        base._sum(page, comparative),
        "CONTROLLED_SUM_OF_VISIBLE_TAX_RECONCILIATION_COMPONENTS",
    )


def _period(page: int, *items: tuple[int, str]) -> list[dict[str, Any]]:
    return [
        {"line_index": line, "page_sequence": page, "pixel_transcription": text}
        for line, text in items
    ]


def _document(
    base: ModuleType,
    code: str,
    page: int,
    owner: Sequence[tuple[int, str]],
    graph_roles: Sequence[str],
    mappings: Sequence[Mapping[str, Any]],
    equations: Sequence[Mapping[str, Any]],
    source_only_rows: Sequence[Mapping[str, Any]],
    period_axis: Sequence[Mapping[str, Any]],
    unit_evidence: Sequence[tuple[int, str]],
    presentation: str,
) -> dict[str, Any]:
    return {
        "absence_evidence": None,
        "bank_code": code,
        "equations": canonical_clone_v1(equations),
        "graph_roles": list(graph_roles),
        "mappings": canonical_clone_v1(mappings),
        "owner": [base._ref(page, line, text) for line, text in owner],
        "page_span": [page, page],
        "period_axis": canonical_clone_v1(period_axis),
        "presentation": presentation,
        "source_only_rows": canonical_clone_v1(source_only_rows),
        "source_period": "2025-12-31",
        "unit_evidence": [base._ref(page, line, text) for line, text in unit_evidence],
    }


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []

    page = 71
    acb_mappings = [
        _direct(
            base,
            "PROFIT_BEFORE_TAX",
            5728,
            page,
            [(13, "Lợi nhuận trước thuế TNDN")],
            (14, "19.538.776"),
            (15, "21.005.871"),
        ),
        _direct(
            base,
            "NON_TAXABLE_INCOME",
            5729,
            page,
            [
                (17, "Trừ (-) Thu nhập được miễn thuế TNDN:"),
                (20, "Thu nhập từ góp vốn, mua cổ phần"),
            ],
            (18, "119.175"),
            (19, "36.214"),
            "SUBTRACT_DIRECTION_IS_EXPLICIT_IN_SOURCE_LABEL",
        ),
        _direct(
            base,
            "NON_DEDUCTIBLE_EXPENSE",
            5730,
            page,
            [(23, "Cộng (4) Chi phí không được khấu trừ khi xác định thu nhập"), (24, "chịu thuế")],
            (25, "34.760"),
            (26, "13.945"),
        ),
        _direct(
            base,
            "TAXABLE_INCOME",
            5731,
            page,
            [(30, "Thu nhập chịu thuế")],
            (31, "19.485.685"),
            (32, "20.838.082"),
        ),
        _direct(
            base,
            "CURRENT_TAX_AT_RATE",
            5724,
            page,
            [(33, "Chi phí thuế TNDN tính trên thu nhập chịu thuế kỳ hiện hành")],
            (34, "3.897.137"),
            (35, "4.167.616"),
        ),
        _direct(
            base,
            "PRIOR_PERIOD_TAX_ADJUSTMENT",
            5733,
            page,
            [
                (36, "Điều chỉnh chi phí thuế TNDN của các năm trước vào chi phí"),
                (37, "thuế TNDN hiện hành năm nay"),
            ],
            (38, "16.885"),
            (39, "32.083"),
        ),
        _direct(
            base,
            "CURRENT_TAX_PARENT",
            5723,
            page,
            [(40, "Tổng chi phí thuế TNDN hiện hành")],
            (41, "3.914.022"),
            (42, "4.199.699"),
        ),
        _direct(
            base,
            "DEFERRED_TAX_NET",
            5726,
            page,
            [(56, "Chi phí thuế thu nhập doanh nghiệp hoãn lại")],
            (70, "55"),
            (72, "16.404"),
            "TRAILING_NET_OF_TWO_VISIBLE_DEFERRED_TAX_COMPONENTS",
        ),
    ]
    acb_source = [
        base._source_only(
            "A2025-ITAX-ACB-001",
            "OTHER_TAXABLE_INCOME_ADJUSTMENT",
            page,
            [(27, "Các khoản điều chỉnh làm tăng/(giảm) thu nhập chịu thuế khác")],
            {
                "COMPARATIVE_PERIOD": base._line(page, 29, "(145.520)"),
                "CURRENT_PERIOD": base._line(page, 28, "31.324"),
            },
            [],
            "The broad increase/decrease row has no independently named leaf outside the already source-bound non-taxable-income row.",
        ),
        base._source_only(
            "A2025-ITAX-ACB-002",
            "DEFERRED_ASSET_REVERSAL_COMPONENT",
            page,
            [
                (61, "Chi phí thuế thu nhập doanh nghiệp hoãn lại phát sinh từ hoàn"),
                (62, "nhập tài sản thuế thu nhập hoãn lại (Thuyết minh 14.2)"),
            ],
            {
                "COMPARATIVE_PERIOD": base._line(page, 64, "33.594"),
                "CURRENT_PERIOD": base._line(page, 63, "14.913"),
            },
            [],
            "The live schema contains the deferred-tax net but no source-specific reversal component leaf.",
        ),
        base._source_only(
            "A2025-ITAX-ACB-003",
            "DEFERRED_DEDUCTIBLE_DIFFERENCE_COMPONENT",
            page,
            [
                (65, "Thu nhập thuế thu nhập doanh nghiệp hoãn lại phát sinh từ các"),
                (66, "khoản chênh lệch tạm thời được khấu trừ (Thuyết minh 14.2)"),
            ],
            {
                "COMPARATIVE_PERIOD": base._line(page, 68, "(17.190)"),
                "CURRENT_PERIOD": base._line(page, 67, "(14.858)"),
            },
            [],
            "The live schema contains the deferred-tax net but no source-specific deductible-difference component leaf.",
        ),
    ]
    docs.append(
        _document(
            base,
            "ACB",
            page,
            [(5, "THUÉ THU NHẬP DOANH NGHIỆP (?TNDN?)")],
            [
                "CURRENT_TAX_AT_RATE",
                "PROFIT_BEFORE_TAX",
                "NON_TAXABLE_INCOME",
                "NON_DEDUCTIBLE_EXPENSE",
                "TAXABLE_INCOME",
                "PRIOR_PERIOD_TAX_ADJUSTMENT",
                "CURRENT_TAX_TOTAL",
                "DEFERRED_TAX_EXPENSE_CHILD",
            ],
            acb_mappings,
            [
                base._equation(
                    "CURRENT_RATE_PLUS_PRIOR_EQUALS_CURRENT_TAX",
                    "CURRENT_TAX_PARENT",
                    ["CURRENT_TAX_AT_RATE", "PRIOR_PERIOD_TAX_ADJUSTMENT"],
                ),
                base._equation(
                    "DEFERRED_COMPONENTS_EQUAL_NET",
                    "DEFERRED_TAX_NET",
                    [
                        "DEFERRED_ASSET_REVERSAL_COMPONENT",
                        "DEFERRED_DEDUCTIBLE_DIFFERENCE_COMPONENT",
                    ],
                ),
            ],
            acb_source,
            _period(page, (9, "Năm 2025"), (10, "Năm 2024")),
            [(11, "Triệu VND"), (12, "Triệu VND")],
            "ANNUAL_CURRENT_TAX_RECONCILIATION_PLUS_SEPARATE_DEFERRED_COMPONENT_TABLE",
        )
    )

    page = 76
    mbb_mappings = [
        _direct(
            base,
            "PROFIT_BEFORE_TAX",
            5728,
            page,
            [(16, "Lợi nhuận kế toán hợp nhất trước thuế")],
            (17, "34.268.358"),
            (18, "28.829.328"),
        ),
        _aggregate(
            base,
            "NON_TAXABLE_AGGREGATE",
            5729,
            page,
            [
                (20, "Lợi nhuận kế toán của các công ty con"),
                (27, "Lợi nhuận của các chi nhánh nước ngoài"),
                (30, "Thu nhập từ cổ tức không chịu thuế của Ngân hàng mẹ"),
                (33, "Thu nhập từ thoái vốn tại công ty con"),
                (35, "Các bút ítoán điều chỉnh hợp nhất"),
            ],
            [
                (21, "(3.297.760)"),
                (28, "(23.268)"),
                (31, "(19.084)"),
                (34, "1.709.275"),
                (36, "31.058"),
            ],
            [(22, "(2.134.540)"), (29, "(20.865)"), (32, "(19.149)"), (37, "22.778")],
        ),
        _direct(
            base,
            "NON_DEDUCTIBLE_EXPENSE",
            5730,
            page,
            [(23, "Chi phí không được khẩu trừ khi tính thuế của Ngân"), (24, "hàng mẹ")],
            (25, "32.555"),
            (26, "446.806"),
        ),
        _direct(
            base,
            "TAXABLE_INCOME",
            5731,
            page,
            [(38, "Thu nhập chịu thuế ước tính trong năm của"), (39, "Ngân hàng tại Việt Nam")],
            (40, "32.701.134"),
            (41, "27.124.358"),
        ),
        _direct(
            base,
            "CURRENT_TAX_BANK",
            5732,
            page,
            [(42, "Thuế TNDN của Ngân hàng tại Việt Nam")],
            (43, "6.540.227"),
            (44, "5.424.872"),
        ),
        _direct(
            base,
            "FOREIGN_BRANCH_TAX",
            5734,
            page,
            [(46, "Thuễ TNDN của chi nhánh nước ngoài")],
            (47, "4.654"),
            (48, "4.172"),
        ),
        _direct(
            base,
            "SUBSIDIARY_TAX",
            5735,
            page,
            [(49, "Thuế TNDN của công ty con")],
            (50, "659.246"),
            (51, "444.314"),
        ),
        _direct(
            base,
            "PRIOR_PERIOD_TAX_ADJUSTMENT",
            5733,
            page,
            [(52, "Điều chỉnh theo quyết toán thuế")],
            (53, "14.599"),
            (54, "14.908"),
        ),
        _direct(
            base,
            "CURRENT_TAX_PARENT",
            5723,
            page,
            [(57, "Chi phí thuế TNDN trọng năm")],
            (58, "6.876.871"),
            (59, "5.888.266"),
        ),
    ]
    mbb_source = [
        base._source_only(
            "A2025-ITAX-MBB-001",
            "DIVESTMENT_CURRENT_TAX",
            page,
            [(55, "Thuế TNDN do thoái vốn tại công ty con")],
            {"CURRENT_PERIOD": base._line(page, 56, "(341.855)")},
            ["COMPARATIVE_PERIOD"],
            "The source-specific divestment tax has no exact current-tax component leaf; the comparative source cell is visibly blank and is not zero-filled.",
        )
    ]
    docs.append(
        _document(
            base,
            "MBB",
            page,
            [(10, "CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP HIỆN HÀNH (TIẾP THEO)")],
            [
                "PROFIT_BEFORE_TAX",
                "NON_DEDUCTIBLE_EXPENSE",
                "NON_TAXABLE_INCOME",
                "TAXABLE_INCOME",
                "CURRENT_TAX_BANK",
                "CURRENT_TAX_FOREIGN_BRANCH",
                "CURRENT_TAX_SUBSIDIARIES",
                "CURRENT_TAX_TOTAL",
            ],
            mbb_mappings,
            [
                base._equation(
                    "PROFIT_PLUS_ADJUSTMENTS_EQUALS_TAXABLE",
                    "TAXABLE_INCOME",
                    ["PROFIT_BEFORE_TAX", "NON_TAXABLE_AGGREGATE", "NON_DEDUCTIBLE_EXPENSE"],
                ),
                base._equation(
                    "CURRENT_COMPONENTS_INCLUDE_DIVESTMENT_EQUAL_TOTAL",
                    "CURRENT_TAX_PARENT",
                    [
                        "CURRENT_TAX_BANK",
                        "FOREIGN_BRANCH_TAX",
                        "SUBSIDIARY_TAX",
                        "PRIOR_PERIOD_TAX_ADJUSTMENT",
                        "DIVESTMENT_CURRENT_TAX",
                    ],
                    ("CURRENT_PERIOD",),
                ),
                base._equation(
                    "COMPARATIVE_VISIBLE_COMPONENTS_EQUAL_TOTAL",
                    "CURRENT_TAX_PARENT",
                    [
                        "CURRENT_TAX_BANK",
                        "FOREIGN_BRANCH_TAX",
                        "SUBSIDIARY_TAX",
                        "PRIOR_PERIOD_TAX_ADJUSTMENT",
                    ],
                    ("COMPARATIVE_PERIOD",),
                ),
            ],
            mbb_source,
            _period(page, (12, "Năm 2025"), (13, "Năm 2024")),
            [(14, "triệu đồng"), (15, "triệu đồng")],
            "ANNUAL_ISSUER_COMPONENT_RECONCILIATION_WITH_BLANK_COMPARATIVE_DIVESTMENT_TAX",
        )
    )

    page = 64
    vp_mappings = [
        _direct(
            base,
            "PROFIT_BEFORE_TAX",
            5728,
            page,
            [(58, "Lợi nhuận thuần trước thuế TNDN")],
            (59, "30.624.949"),
            (60, "20.012.700"),
        ),
        _aggregate(
            base,
            "NON_TAXABLE_AGGREGATE",
            5729,
            page,
            [
                (62, "Thu nhập không chịu thuế"),
                (68, "Điều chỉnh liễn quan đến hợp nhất"),
                (71, "Các khoản điều chỉnh khác"),
            ],
            [(63, "(35.161)"), (69, "22.932"), (72, "(55.996)")],
            [(64, "(12.854)"), (70, "(273.708)"), (73, "(4.727)")],
        ),
        _direct(
            base,
            "NON_DEDUCTIBLE_EXPENSE",
            5730,
            page,
            [(65, "Chi phi không được khẩu trừ")],
            (66, "191.034"),
            (67, "52.191"),
        ),
        _direct(
            base,
            "TAXABLE_INCOME",
            5731,
            page,
            [(74, "Thu nhập chịu thuế ước tính trong năm")],
            (75, "30.747.758"),
            (76, "19.773.602"),
        ),
        _direct(
            base,
            "CURRENT_TAX_AT_RATE",
            5724,
            page,
            [(77, "Chi phí thuế TNDN theo thuế suất hiện hành")],
            (78, "6.149.552"),
            (79, "3.954.720"),
        ),
        _direct(
            base,
            "PRIOR_PERIOD_TAX_ADJUSTMENT",
            5733,
            page,
            [(80, "Điều chỉnh số thuế phải nộp các kỳ trước")],
            (81, "21.076"),
            (82, "8.059"),
        ),
        _direct(
            base,
            "CURRENT_TAX_PARENT",
            5723,
            page,
            [(83, "Chi phí thuế TNDN trong năm")],
            (84, "6.170.628"),
            (85, "3.962.779"),
        ),
    ]
    vp_source = [
        base._source_only(
            "A2025-ITAX-VPB-001",
            "OTHER_PAYABLE_ADJUSTMENT",
            page,
            [(86, "Các điều chỉnh khác")],
            {"CURRENT_PERIOD": base._line(page, 87, "45.695")},
            ["COMPARATIVE_PERIOD"],
            "This row belongs to the subsequent tax-payable rollforward, has no exact expense leaf, and its comparative cell is visibly blank.",
        )
    ]
    docs.append(
        _document(
            base,
            "VPB",
            page,
            [(36, "Thuế thu nhập doanh nghiệp hiện hành")],
            [
                "PROFIT_BEFORE_TAX",
                "NON_TAXABLE_INCOME",
                "NON_DEDUCTIBLE_EXPENSE",
                "CONSOLIDATION_ADJUSTMENT",
                "OTHER_TAXABLE_INCOME_ADJUSTMENT",
                "TAXABLE_INCOME",
                "CURRENT_TAX_AT_RATE",
                "PRIOR_PERIOD_TAX_ADJUSTMENT",
                "CURRENT_TAX_TOTAL",
            ],
            vp_mappings,
            [
                base._equation(
                    "PROFIT_PLUS_ADJUSTMENTS_EQUALS_TAXABLE",
                    "TAXABLE_INCOME",
                    ["PROFIT_BEFORE_TAX", "NON_TAXABLE_AGGREGATE", "NON_DEDUCTIBLE_EXPENSE"],
                ),
                base._equation(
                    "RATE_PLUS_PRIOR_EQUALS_CURRENT_TAX",
                    "CURRENT_TAX_PARENT",
                    ["CURRENT_TAX_AT_RATE", "PRIOR_PERIOD_TAX_ADJUSTMENT"],
                ),
            ],
            vp_source,
            _period(page, (54, "Năm 2025"), (55, "Năm 2024")),
            [(56, "Triệu đồng"), (57, "Triệu đồng")],
            "ANNUAL_TAX_RECONCILIATION_FOLLOWED_BY_SEPARATE_PAYABLE_ROLLFORWARD",
        )
    )

    page = 52
    hdb_mappings = [
        _direct(
            base,
            "PROFIT_BEFORE_TAX",
            5728,
            page,
            [(13, "Lợi nhuận trước thuế TNDN")],
            (14, "21.346.491"),
            (15, "16.729.995"),
        ),
        _aggregate(
            base,
            "NON_TAXABLE_AGGREGATE",
            5729,
            page,
            [
                (20, "- Thu nhập từ góp vốn, mua cổ phần"),
                (22, "- Các khoản doanh thu đã tính thuế các năm trước"),
                (25, "- Các khoản điều chỉnh tính thuế thu nhập hoãn lại"),
                (28, "- Điều chỉnh khác"),
            ],
            [(21, "(8.521)"), (23, "(18.009)"), (26, "(381.784)"), (29, "(380.036)")],
            [(24, "(64.398)"), (27, "396.038"), (30, "(178.832)")],
        ),
        _direct(
            base,
            "NON_DEDUCTIBLE_EXPENSE",
            5730,
            page,
            [(17, "- Chi phí không được trừ")],
            (18, "246.920"),
            (19, "789.279"),
        ),
        _direct(
            base,
            "TAXABLE_INCOME",
            5731,
            page,
            [(31, "Thu nhập chịu thuế")],
            (32, "20.805.061"),
            (33, "17.672.082"),
        ),
        _direct(
            base,
            "CURRENT_TAX_AT_RATE",
            5724,
            page,
            [(37, "Chi phí thuế TNDN theo thuế suất")],
            (38, "4.161.012"),
            (39, "3.534.416"),
        ),
        _direct(
            base,
            "PRIOR_PERIOD_TAX_ADJUSTMENT",
            5733,
            page,
            [(40, "Điều chỉnh thuế TNDN các năm trước")],
            (41, "28.667"),
            (42, "27.139"),
        ),
        _direct(
            base,
            "CURRENT_TAX_PARENT",
            5723,
            page,
            [(43, "Chi phí thuế TNDN trong năm")],
            (44, "4.189.679"),
            (45, "3.561.555"),
        ),
    ]
    docs.append(
        _document(
            base,
            "HDB",
            page,
            [(8, "CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP")],
            [
                "PROFIT_BEFORE_TAX",
                "NON_DEDUCTIBLE_EXPENSE",
                "NON_TAXABLE_INCOME",
                "OTHER_CURRENT_TAX_ADJUSTMENT",
                "TAXABLE_INCOME",
                "CURRENT_TAX_AT_RATE",
                "PRIOR_PERIOD_TAX_ADJUSTMENT",
                "CURRENT_TAX_TOTAL",
            ],
            hdb_mappings,
            [
                base._equation(
                    "PROFIT_PLUS_ADJUSTMENTS_EQUALS_TAXABLE",
                    "TAXABLE_INCOME",
                    ["PROFIT_BEFORE_TAX", "NON_TAXABLE_AGGREGATE", "NON_DEDUCTIBLE_EXPENSE"],
                ),
                base._equation(
                    "RATE_PLUS_PRIOR_EQUALS_CURRENT_TAX",
                    "CURRENT_TAX_PARENT",
                    ["CURRENT_TAX_AT_RATE", "PRIOR_PERIOD_TAX_ADJUSTMENT"],
                ),
            ],
            [],
            _period(page, (9, "Năm nay"), (10, "Năm trước")),
            [(11, "Triệu VND"), (12, "Triệu VND")],
            "ANNUAL_CURRENT_PREVIOUS_COLUMNS_WITH_OPTIONAL_ONE_PERIOD_ADJUSTMENT",
        )
    )

    page = 62
    vcb_mappings = [
        _direct(
            base,
            "PROFIT_BEFORE_TAX",
            5728,
            page,
            [(16, "Lợi nhuận trước thuế")],
            (18, "44.019.637"),
            (19, "42.236.135"),
        ),
        _aggregate(
            base,
            "NON_TAXABLE_AGGREGATE",
            5729,
            page,
            [
                (21, "Lợi nhuận tính thuế của các công ty con"),
                (24, "Cổ tức nhận được trong năm (Thuyết minh 30)"),
                (27, "Phân chia lãi theo phương pháp vốn chủ sở hữu của"),
                (28, "các khoản đầu tư vào các công ty liên doanh, liên kết"),
                (30, "(Thuyết minh 30)"),
                (36, "Các khoản điều chỉnh giảm"),
                (39, "Thu nhập chịu thuế tương ứng khoản lợi nhuận từ VFC"),
                (40, "chuyển về trong năm 2025"),
                (42, "Hoàn nhập chi phí không được khấu trừ thuế của năm trước"),
            ],
            [
                (22, "(1.072.732)"),
                (25, "(118.576)"),
                (31, "(163.286)"),
                (37, "(4.939)"),
                (41, "11.288"),
                (43, "(4.931.869)"),
            ],
            [(23, "(974.570)"), (26, "(160.709)"), (32, "(145.723)"), (38, "(12.493)")],
        ),
        _direct(
            base,
            "NON_DEDUCTIBLE_EXPENSE",
            5730,
            page,
            [(33, "Các khoản chi phí không được khấu trừ trong năm")],
            (34, "424.959"),
            (35, "734.375"),
        ),
        _direct(
            base,
            "TAXABLE_INCOME",
            5731,
            page,
            [(44, "Thu nhập chịu thuế")],
            (45, "38.164.482"),
            (46, "41.677.015"),
        ),
        _direct(
            base,
            "CURRENT_TAX_BANK",
            5732,
            page,
            [(50, "Chi phí thuế TNDN hiện hành ước tính của Ngân hàng"), (51, "(thuế suất: 20%)")],
            (52, "7.632.896"),
            (53, "8.335.403"),
        ),
        _direct(
            base,
            "SUBSIDIARY_TAX",
            5735,
            page,
            [(55, "Chi phí thuế TNDN hiện hành của công ty con")],
            (56, "211.418"),
            (57, "191.093"),
        ),
        _mapping_axes(
            base,
            "FOREIGN_BRANCH_TAX",
            5734,
            page,
            [(58, "Thuế TNDN đã nộp ở nước ngoài trong kỳ tính thuế (VFC)")],
            {"CURRENT_PERIOD": base._line(page, 59, "(1.317)")},
            "DIRECT_CURRENT_PERIOD_WITH_VISIBLE_BLANK_COMPARATIVE_CELL",
        ),
        _direct(
            base,
            "CURRENT_TAX_PARENT",
            5723,
            page,
            [(60, "Thuế thu nhập doanh nghiệp hiện hành theo thuế suất"), (63, "áp dụng")],
            (61, "7.842.997"),
            (62, "8.526.496"),
        ),
        _direct(
            base,
            "DEFERRED_TAX_NET",
            5726,
            page,
            [
                (65, "(Chi phí)/thu nhập thuế thu nhập doanh nghiệp hoãn lại"),
                (70, "(Chi phí)/thu nhập thuế thu nhập doanh nghiệp hoãn lại"),
                (71, "phát sinh từ các khoản chênh lệch tạm thời phải chịu thuế"),
            ],
            (72, "(978.700)"),
            (73, "143.478"),
        ),
    ]
    docs.append(
        _document(
            base,
            "VCB",
            page,
            [(9, "Thuế thu nhập doanh nghiệp")],
            [
                "PROFIT_BEFORE_TAX",
                "NON_DEDUCTIBLE_EXPENSE",
                "TAXABLE_INCOME",
                "CURRENT_TAX_BANK",
                "CURRENT_TAX_SUBSIDIARIES",
            ],
            vcb_mappings,
            [
                base._equation(
                    "PROFIT_PLUS_ADJUSTMENTS_EQUALS_TAXABLE",
                    "TAXABLE_INCOME",
                    ["PROFIT_BEFORE_TAX", "NON_TAXABLE_AGGREGATE", "NON_DEDUCTIBLE_EXPENSE"],
                ),
                base._equation(
                    "CURRENT_COMPONENTS_EQUAL_TOTAL",
                    "CURRENT_TAX_PARENT",
                    ["CURRENT_TAX_BANK", "SUBSIDIARY_TAX", "FOREIGN_BRANCH_TAX"],
                    ("CURRENT_PERIOD",),
                ),
                base._equation(
                    "COMPARATIVE_VISIBLE_COMPONENTS_EQUAL_TOTAL",
                    "CURRENT_TAX_PARENT",
                    ["CURRENT_TAX_BANK", "SUBSIDIARY_TAX"],
                    ("COMPARATIVE_PERIOD",),
                ),
            ],
            [],
            _period(page, (12, "2025"), (13, "2024")),
            [(14, "Triệu VND"), (15, "Triệu VND")],
            "ANNUAL_PLAIN_PROFIT_LABEL_ISSUER_COMPONENTS_AND_SEPARATE_DEFERRED_TAX_TABLE",
        )
    )

    page = 60
    ctg_mappings = [
        _direct(
            base,
            "PROFIT_BEFORE_TAX",
            5728,
            page,
            [(69, "Lợi nhuận kế toán hợp nhất trước thuế TNDN")],
            (70, "43.443.809"),
            (71, "31.763.925"),
        ),
        _aggregate(
            base,
            "NON_TAXABLE_AGGREGATE",
            5729,
            page,
            [
                (73, "- Thu nhập từ cổ tức và lợi nhuận được chia không chịu thuế"),
                (76, "Lợi nhuận của công ty con"),
                (79, "- Thu nhập từ lợi ích tăng lên tại các công ty liên doanh"),
                (82, "- Biến động dự phòng/đánh giá lại cho các khoản cho vay và"),
                (83, "trái phiếu khi hợp nhất báo cáo tài chính"),
                (86, "- Khác"),
            ],
            [
                (74, "(71.352)"),
                (77, "(1.619.426)"),
                (80, "(369.015)"),
                (84, "(384.615)"),
                (87, "185.197"),
            ],
            [
                (75, "(20.539)"),
                (78, "(891.368)"),
                (81, "(370.109)"),
                (85, "(161.384)"),
                (88, "188.471"),
            ],
        ),
        _direct(
            base,
            "TAXABLE_INCOME",
            5731,
            page,
            [(89, "Thu nhập chịu thuế TNDN hiện hành của ngân hàng mẹ")],
            (90, "41.184.598"),
            (91, "30.508.996"),
        ),
        _direct(
            base,
            "CURRENT_TAX_BANK",
            5732,
            page,
            [
                (95, "Chi phí thuê TNDN hiện hành của Ngân hàng mẹ tính trên"),
                (96, "thu nhập chịu thuế ở trong nước"),
            ],
            (97, "8.236.920"),
            (98, "6.101.799"),
        ),
        _mapping_axes(
            base,
            "FOREIGN_BRANCH_TAX",
            5734,
            page,
            [
                (99, "Chi phí thuế TNDN hiện hành của Ngân hàng mẹ tính trên"),
                (100, "thu nhập chịu thuế ở nước ngoài"),
            ],
            {"CURRENT_PERIOD": base._line(page, 101, "2.335")},
            "DIRECT_CURRENT_PERIOD_WITH_VISIBLE_BLANK_COMPARATIVE_CELL",
        ),
        _direct(
            base,
            "SUBSIDIARY_TAX",
            5735,
            page,
            [(102, "Chi phí thuế TNDN hiện hành của công ty con")],
            (103, "329.353"),
            (104, "184.099"),
        ),
        _direct(
            base,
            "CURRENT_TAX_PARENT",
            5723,
            page,
            [(105, "Chị phí thuế TNDN hiện hành tinh trên thu nhập chịu thuế (t)")],
            (106, "8.568.608"),
            (107, "6.285.898"),
        ),
    ]
    ctg_source = [
        base._source_only(
            "A2025-ITAX-CTG-001",
            "OTHER_PAYABLE_ADJUSTMENT",
            page,
            [(114, "Điều chính khác")],
            {
                "COMPARATIVE_PERIOD": base._line(page, 116, "(61.403)"),
                "CURRENT_PERIOD": base._line(page, 115, "1.396"),
            },
            [],
            "This row belongs to the subsequent tax-payable rollforward and has no exact tax-expense leaf.",
        )
    ]
    docs.append(
        _document(
            base,
            "CTG",
            page,
            [(61, "THUÉ TNDN HIỆN HÀNH")],
            [
                "PROFIT_BEFORE_TAX",
                "NON_TAXABLE_INCOME",
                "TAXABLE_INCOME",
                "CURRENT_TAX_BANK",
                "CURRENT_TAX_SUBSIDIARIES",
                "CURRENT_TAX_AT_RATE",
                "OTHER_CURRENT_TAX_ADJUSTMENT",
            ],
            ctg_mappings,
            [
                base._equation(
                    "PROFIT_PLUS_ADJUSTMENTS_EQUALS_TAXABLE",
                    "TAXABLE_INCOME",
                    ["PROFIT_BEFORE_TAX", "NON_TAXABLE_AGGREGATE"],
                ),
                base._equation(
                    "CURRENT_COMPONENTS_EQUAL_TOTAL",
                    "CURRENT_TAX_PARENT",
                    ["CURRENT_TAX_BANK", "FOREIGN_BRANCH_TAX", "SUBSIDIARY_TAX"],
                    ("CURRENT_PERIOD",),
                ),
                base._equation(
                    "COMPARATIVE_VISIBLE_COMPONENTS_EQUAL_TOTAL",
                    "CURRENT_TAX_PARENT",
                    ["CURRENT_TAX_BANK", "SUBSIDIARY_TAX"],
                    ("COMPARATIVE_PERIOD",),
                ),
            ],
            ctg_source,
            _period(page, (65, "31.12.2025"), (66, "31.12.2024")),
            [(67, "Triệu đóng"), (68, "Triệu đông")],
            "ANNUAL_DOMESTIC_FOREIGN_AND_SUBSIDIARY_COMPONENTS_FOLLOWED_BY_PAYABLE_ROLLFORWARD",
        )
    )

    page = 57
    bid_mappings = [
        _direct(
            base,
            "PROFIT_BEFORE_TAX",
            5728,
            page,
            [(60, "Tổng lợi nhuận kế toán trước thuế")],
            (61, "37.787.518"),
            (62, "32.076.221"),
        ),
        _aggregate(
            base,
            "NON_TAXABLE_AGGREGATE",
            5729,
            page,
            [
                (64, "Lợi nhuận trước thuế của các công ty con"),
                (68, "Các khoản điều chỉnh hợp nhất"),
                (76, "- Thu nhập từ cổ tức không chịu thuế"),
                (84, "- Chênh lệch tạm thời chi phí dự phòng đầu tư dài"),
                (88, "hạn theo quy định tại Thông tư 48"),
            ],
            [(65, "(1.533.565)"), (69, "(745.107)"), (77, "(220.392)"), (85, "(913)")],
            [(66, "(1.218.197)"), (70, "(160.153)"), (78, "(205.774)"), (86, "(312)")],
        ),
        _direct(
            base,
            "NON_DEDUCTIBLE_EXPENSE",
            5730,
            page,
            [(80, "Các chi phí không được khấu trừ")],
            (81, "14.691"),
            (82, "97.678"),
        ),
        _direct(
            base,
            "TAXABLE_INCOME",
            5731,
            page,
            [(89, "Thu nhập chịu thuế ước tính của Ngân hàng mẹ")],
            (90, "35.302.232"),
            (91, "30.589.463"),
        ),
        _direct(
            base,
            "CURRENT_TAX_BANK",
            5732,
            page,
            [(92, "Chi phí thuế TNDN hiện hành ước tính của Ngân hàng"), (95, "mẹ")],
            (93, "7.063.145"),
            (94, "6.117.892"),
        ),
        _direct(
            base,
            "SUBSIDIARY_TAX",
            5735,
            page,
            [(97, "Chi phí thuế TNDN hiện hành của các công ty con")],
            (98, "308.178"),
            (99, "285.006"),
        ),
        _direct(
            base,
            "CURRENT_TAX_PARENT",
            5723,
            page,
            [(100, "Chi phí thuế TNDN trong năm của toàn hệ thống")],
            (101, "7.371.323"),
            (102, "6.402.898"),
        ),
    ]
    docs.append(
        _document(
            base,
            "BID",
            page,
            [(52, "CHI PHÍ THUẾ THU NHẬP DOANH NGHIỆP (?TNDN?)")],
            [
                "PROFIT_BEFORE_TAX",
                "NON_TAXABLE_INCOME",
                "NON_DEDUCTIBLE_EXPENSE",
                "TAXABLE_INCOME",
                "CURRENT_TAX_BANK",
                "CURRENT_TAX_SUBSIDIARIES",
                "CURRENT_TAX_TOTAL",
            ],
            bid_mappings,
            [
                base._equation(
                    "PROFIT_PLUS_ADJUSTMENTS_EQUALS_TAXABLE",
                    "TAXABLE_INCOME",
                    ["PROFIT_BEFORE_TAX", "NON_TAXABLE_AGGREGATE", "NON_DEDUCTIBLE_EXPENSE"],
                ),
                base._equation(
                    "BANK_PLUS_SUBSIDIARY_EQUALS_TOTAL",
                    "CURRENT_TAX_PARENT",
                    ["CURRENT_TAX_BANK", "SUBSIDIARY_TAX"],
                ),
            ],
            [],
            _period(page, (56, "Năm nay"), (55, "Năm trước")),
            [(58, "Triệu VND"), (59, "Triệu VND")],
            "ANNUAL_CONSOLIDATED_TO_PARENT_BANK_TAXABLE_INCOME_AND_SYSTEM_CURRENT_TAX",
        )
    )

    page = 53
    vib_mappings = [
        _direct(
            base,
            "PROFIT_BEFORE_TAX",
            5728,
            page,
            [(12, "Lọi nhuận trước thuế TNDN")],
            (13, "9.104.616"),
            (14, "9.004.302"),
        ),
        _aggregate(
            base,
            "NON_TAXABLE_AGGREGATE",
            5729,
            page,
            [
                (15, "Điều chỉnh thu nhập từ cỏ tức không chịu thuế"),
                (18, "Điều chình giảm thu nhập chịu thuế"),
            ],
            [(16, "(2.745)"), (19, "(8.151)")],
            [(17, "(3.746)"), (20, "2.401")],
        ),
        _direct(
            base,
            "NON_DEDUCTIBLE_EXPENSE",
            5730,
            page,
            [(21, "Chi phí không được khẩu trừ")],
            (22, "1.211"),
            (23, "370"),
        ),
        _direct(
            base,
            "TAXABLE_INCOME",
            5731,
            page,
            [(24, "Thu nhập chịu thuế TNDN")],
            (25, "9.094.931"),
            (26, "9.003.327"),
        ),
        _direct(
            base,
            "CURRENT_TAX_AT_RATE",
            5724,
            page,
            [(30, "Chi phí thuế TNDN tính trên thu nhập chịu thuế"), (31, "kỳ hiện hành")],
            (32, "1.818.986"),
            (33, "1.800.665"),
        ),
        _direct(
            base,
            "CURRENT_TAX_PARENT",
            5723,
            page,
            [(37, "Tổng chi phí thuế TNDN hiện hành")],
            (38, "1.819.149"),
            (39, "1.800.834"),
        ),
        _direct(
            base,
            "DEFERRED_TAX_NET",
            5726,
            page,
            [
                (63, "(Chi phí)/thu nhập thuế TNDN hoãn lại liên quạn đến"),
                (64, "khoản chênh lệch tạm thời được khẩu trừ thuế"),
            ],
            (65, "(37)"),
            (66, "1.002"),
        ),
    ]
    vib_source = [
        base._source_only(
            "A2025-ITAX-VIB-001",
            "OTHER_CURRENT_TAX_ADJUSTMENT",
            page,
            [(34, "Điều chỉnh khác")],
            {
                "COMPARATIVE_PERIOD": base._line(page, 36, "169"),
                "CURRENT_PERIOD": base._line(page, 35, "163"),
            },
            [],
            "The broad source label does not establish the prior-period nature required by ReportNormId 5733; it remains visible and participates in the verified total equation.",
        )
    ]
    docs.append(
        _document(
            base,
            "VIB",
            page,
            [
                (
                    6,
                    "Chi phí thuế TNDN hiện hành trong năm tài chính kết thúc ngày 31 tháng 12 năm 2025 và",
                ),
                (7, "ngày 31 tháng 12 năm 2024 được ước tính như sau:"),
            ],
            [
                "PROFIT_BEFORE_TAX",
                "NON_TAXABLE_INCOME",
                "NON_DEDUCTIBLE_EXPENSE",
                "TAXABLE_INCOME",
                "CURRENT_TAX_AT_RATE",
                "OTHER_CURRENT_TAX_ADJUSTMENT",
                "CURRENT_TAX_TOTAL",
                "DEFERRED_TAX_COMPONENT",
            ],
            vib_mappings,
            [
                base._equation(
                    "PROFIT_PLUS_ADJUSTMENTS_EQUALS_TAXABLE",
                    "TAXABLE_INCOME",
                    ["PROFIT_BEFORE_TAX", "NON_TAXABLE_AGGREGATE", "NON_DEDUCTIBLE_EXPENSE"],
                ),
                base._equation(
                    "RATE_PLUS_OTHER_ADJUSTMENT_EQUALS_CURRENT_TAX",
                    "CURRENT_TAX_PARENT",
                    ["CURRENT_TAX_AT_RATE", "OTHER_CURRENT_TAX_ADJUSTMENT"],
                ),
            ],
            vib_source,
            _period(page, (8, "2025"), (9, "2024")),
            [(10, "triệu đồng"), (11, "triệu đồng")],
            "ANNUAL_CURRENT_TAX_RECONCILIATION_PLUS_DEFERRED_TAX_ASSET_MOVEMENT",
        )
    )

    if [item["bank_code"] for item in docs] != [
        "ACB",
        "MBB",
        "VPB",
        "HDB",
        "VCB",
        "CTG",
        "BID",
        "VIB",
    ]:
        raise _error("annual income-tax review document order drifted")
    return docs


def _base() -> ModuleType:
    base = _load_base()
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.REVIEW_RUN_ID = REVIEW_RUN_ID
    base.VARIANT_PROFILE = VARIANT_PROFILE
    base.FAMILY_END_DISPLAY_ORDER = 826
    base.SOURCE_PERIOD_STATUS_BY_PERIOD = {
        "2025-12-31": "VERIFIED_AUDITED_CONSOLIDATED_ANNUAL_2025_CURRENT_AND_2024_COMPARATIVE_PERIODS"
    }
    base.CLAIM_BOUNDARY = CLAIM_BOUNDARY
    base.REVIEW_PATH = REVIEW_PATH
    base.RESULT_PATH = RESULT_PATH
    base.SEMANTIC_INDEX_PATH = SEMANTIC_INDEX_PATH
    base.CROP_MANIFEST_PATH = CROP_MANIFEST_PATH
    base.EXPECTED_INDEX_SHA256 = EXPECTED_INDEX_SHA256
    base.EXPECTED_CROP_MANIFEST_SHA256 = EXPECTED_CROP_MANIFEST_SHA256
    base.EXPECTED_AXIS_SHA256 = EXPECTED_AXIS_SHA256
    base.EXPECTED_SCAN_ID = EXPECTED_SCAN_ID
    base.EXPECTED_RESULT_ID = EXPECTED_RESULT_ID
    base.ALLOW_HISTORICAL_DISPLAY_ORDER_SNAPSHOT = False
    base._SCHEMA_EXPECTED = dict(_SCHEMA_EXPECTED)
    base._AUTHORITY = canonical_clone_v1(_AUTHORITY)
    base._REVIEW_SAFETY = canonical_clone_v1(_REVIEW_SAFETY)
    base._review_documents = lambda: _review_documents(base)
    return base


def build_annual_2025_income_tax_pixel_review_blueprint_v1() -> dict[str, Any]:
    """Return the exact annual visible-PDF review ledger."""

    return _base()._review_blueprint()


def build_live_annual_2025_income_tax_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    """Replay all annual inputs and build the bounded result."""

    try:
        return _base().build_live_income_tax_8bank_codex_verified_mapping_v1()
    except Annual2025IncomeTax8BankError:
        raise
    except Exception as exc:
        raise _error(str(exc)) from exc


def validate_annual_2025_income_tax_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    """Exact-rebuild the annual result and reject coordinated rehashes."""

    try:
        return _base().validate_live_income_tax_8bank_codex_verified_mapping_v1(value)
    except Annual2025IncomeTax8BankError:
        raise
    except Exception as exc:
        raise _error(str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-review", action="store_true")
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if sum((args.write_review, args.write_result, args.verify)) != 1:
        parser.error("choose exactly one action")
    if args.write_review:
        REVIEW_PATH.write_bytes(
            canonical_json_bytes_v1(build_annual_2025_income_tax_pixel_review_blueprint_v1())
        )
        return 0
    if args.write_result:
        result = build_live_annual_2025_income_tax_8bank_codex_verified_mapping_v1()
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
        print(result["result_id"])
        return 0
    value, _ = _base()._stable_json(RESULT_PATH)
    result = validate_annual_2025_income_tax_8bank_codex_verified_mapping_replay_v1(value)
    print(result["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
