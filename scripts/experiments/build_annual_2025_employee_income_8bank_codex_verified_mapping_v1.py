"""Verify annual-2025 employee-income disclosures across eight bank reports."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1, canonical_json_bytes_v1

PROJECT_ROOT = Path(__file__).resolve().parents[2]

FORMAT_VERSION = "ANNUAL_2025_EMPLOYEE_INCOME_8BANK_CODEX_VERIFIED_MAPPING_V1"
REVIEW_FORMAT = "ANNUAL_2025_EMPLOYEE_INCOME_8BANK_CODEX_PIXEL_REVIEW_V1"
RESULT_STATE = "ANNUAL_2025_EMPLOYEE_INCOME_8BANK_CODEX_VERIFICATION_COMPLETE"
RESULT_ID_PREFIX = "annual2025ei8bcv1:result:"
REVIEW_STATE = "ANNUAL_2025_EMPLOYEE_INCOME_PIXEL_REVIEW_COMPLETE"
REVIEW_ID_PREFIX = "annual2025ei8bcv1:pixel-review:"
REVIEW_PATH = Path(
    "docs/experiments/E-0149-annual-2025-employee-income-8bank-codex-pixel-review-v1.json"
)
RESULT_PATH = Path(
    "docs/experiments/E-0149-annual-2025-employee-income-8bank-codex-verified-mapping-v1.json"
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
EXPECTED_SCAN_ID = "eifdsv1:scan:da9fc093ef069ef1e86445906842a33ce7b855796b47524ca4b1825254902bfa"
EXPECTED_RESULT_ID: str | None = (
    "annual2025ei8bcv1:result:3e7e95b4ce6c10fac3442e77d6e9e3bbe4c5dd013997e0d9a76e065daa2e0a52"
)

CLAIM_BOUNDARY = (
    "AUDITED_CONSOLIDATED_ANNUAL_2025_FIXED_EIGHT_COMPLETE_PDFS_FRESH_"
    "VIETOCR_BANK_BLIND_EMPLOYEE_INCOME_GRAPH_VISIBLE_PDF_SOURCE_NUMERIC_"
    "CHALLENGER_ANNUAL_PERIOD_UNIT_TOTAL_AND_DERIVED_MONTHLY_AVERAGE_"
    "ACCOUNTING_LIVE_TM_SCHEMA_ONLY_NO_EXPORT_AUTHORITY"
)

_AUTHORITY = {
    "annual_average_corroborates_derived_monthly_value": True,
    "bank_filename_note_or_page_used_as_matching_rule": False,
    "canonicalization_or_export_authority": False,
    "complete_pdf_scanned_for_every_document": True,
    "fresh_vietocr_used_as_numeric_truth": False,
    "live_tm_schema_checked": True,
    "mapping_authority_bounded_to_reviewed_annual_employee_income_rows": True,
    "monthly_average_derived_from_verified_numerator_denominator_and_twelve_months": True,
    "paddleocr_or_native_source_axis_used_as_numeric_challenger": True,
    "persisted_result_self_authenticating": False,
    "public_exact_replay_required": True,
    "source_period_average_rows_retained_unmapped": False,
    "text_similarity_alone_used_for_mapping": False,
    "unmapped_source_rows_discarded": False,
    "whole_pdf_uniqueness_replayed": True,
}

_SCHEMA_EXPECTED = {
    1259: ("IV. MỘT SỐ THÔNG TIN KHÁC", None, 839),
    1260: ("Thu nhập nhân viên của ngân hàng", 1259, 840),
    1261: ("Số lượng nhân viên", 1260, 841),
    1262: ("Thu nhập nhân viên", 1260, 842),
    1263: ("Tổng quỹ lương", 1260, 843),
    1264: ("Thưởng", 1260, 844),
    1265: ("Thu nhập khác", 1260, 845),
    1266: ("Tổng thu nhập", 1260, 846),
    1267: ("Lương bình quân người/tháng", 1260, 847),
    1268: ("Thu nhập bình quân người/tháng", 1260, 848),
}


class Annual2025EmployeeIncome8BankError(ValueError):
    """The annual employee-income graph, values, derivations, or schema drifted."""


def _error(message: str) -> Annual2025EmployeeIncome8BankError:
    return Annual2025EmployeeIncome8BankError(message)


def _load_base() -> ModuleType:
    path = (
        PROJECT_ROOT
        / "scripts/experiments/build_employee_income_8bank_codex_verified_mapping_v1.py"
    )
    name = "annual_2025_employee_income_mapping_base_v1"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _error(f"cannot load annual employee-income support: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _values(
    base: ModuleType,
    page: int,
    current: tuple[int, str],
    comparative: tuple[int, str],
    *,
    decimal_value: bool = False,
) -> dict[str, Any]:
    constructor = base._decimal_line if decimal_value else base._line
    return {
        "COMPARATIVE_PERIOD": constructor(page, *comparative),
        "CURRENT_PERIOD": constructor(page, *current),
    }


def _mapping(
    base: ModuleType,
    role: str,
    report_norm_id: int,
    page: int,
    labels: list[tuple[int, str]],
    current: tuple[int, str],
    comparative: tuple[int, str],
    *,
    decimal_value: bool = False,
    topology: str = "DIRECT_OR_WRAPPED_LABEL_TWO_ANNUAL_PERIOD_LANES",
) -> dict[str, Any]:
    material = base._mapping(
        role,
        report_norm_id,
        page,
        labels,
        base._line(page, *current),
        base._line(page, *comparative),
        topology=topology,
    )
    if decimal_value:
        material["values"] = _values(base, page, current, comparative, decimal_value=True)
    return material


def _derived_monthly_mapping(
    base: ModuleType,
    role: str,
    report_norm_id: int,
    page: int,
    label: tuple[int, str],
    printed_current: tuple[int, str],
    printed_comparative: tuple[int, str],
    numerator_role: str,
) -> dict[str, Any]:
    return {
        "derived_monthly": {
            "decimal_places": 2,
            "denominator_role": "EMPLOYEE_COUNT",
            "months": 12,
            "numerator_role": numerator_role,
            "printed_annual_values": _values(base, page, printed_current, printed_comparative),
        },
        "labels": [base._ref(page, *label)],
        "report_norm_id": report_norm_id,
        "role": role,
        "topology": "PRINTED_ANNUAL_AVERAGE_CORROBORATES_DERIVED_MONTHLY_SCHEMA_VALUE",
    }


def _document(
    base: ModuleType,
    code: str,
    page: int,
    *,
    owner: list[tuple[int, str]],
    mappings: list[dict[str, Any]],
    equations: list[dict[str, Any]],
    ratio_equations: list[list[Any]],
    period_axis: list[tuple[int, str]],
    units: list[tuple[int, str]],
    presentation: str,
) -> dict[str, Any]:
    return {
        "absence_evidence": None,
        "bank_code": code,
        "equations": canonical_clone_v1(equations),
        "mappings": canonical_clone_v1(mappings),
        "owner": [base._ref(page, *item) for item in owner],
        "page_span": [page, page],
        "period_axis": [base._ref(page, *item) for item in period_axis],
        "presentation": presentation,
        "ratio_equations": canonical_clone_v1(ratio_equations),
        "source_only_rows": [],
        "source_period": "2025-12-31",
        "unit_evidence": [base._ref(page, *item) for item in units],
    }


def _review_documents(base: ModuleType) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    page = 73
    docs.append(
        _document(
            base,
            "ACB",
            page,
            owner=[(26, "TÌNH HÌNH THU NHẬP CỦA NHÂN VIÊN")],
            mappings=[
                _mapping(
                    base,
                    "EMPLOYEE_COUNT",
                    1261,
                    page,
                    [(31, "Số lượng nhân viên bình quân (người)")],
                    (32, "13.241"),
                    (33, "13.449"),
                ),
                _mapping(
                    base,
                    "SALARY_FUND",
                    1263,
                    page,
                    [(35, "Tổng quỹ lương")],
                    (36, "2.250.273"),
                    (37, "2.250.339"),
                ),
                _mapping(
                    base,
                    "OTHER_INCOME",
                    1265,
                    page,
                    [(38, "Thu nhập khác")],
                    (39, "3.718.889"),
                    (40, "3.898.203"),
                ),
                _mapping(
                    base,
                    "TOTAL_INCOME",
                    1266,
                    page,
                    [(41, "Tổng thu nhập")],
                    (42, "5.969.162"),
                    (43, "6.148.542"),
                ),
                _derived_monthly_mapping(
                    base,
                    "AVERAGE_SALARY_MONTH",
                    1267,
                    page,
                    (44, "Tiền lương bình quân/người/năm"),
                    (45, "170"),
                    (46, "167"),
                    "SALARY_FUND",
                ),
                _derived_monthly_mapping(
                    base,
                    "AVERAGE_INCOME_MONTH",
                    1268,
                    page,
                    (47, "Thu nhập bình quân/người/năm"),
                    (48, "451"),
                    (49, "457"),
                    "TOTAL_INCOME",
                ),
            ],
            equations=[
                {
                    "name": "SALARY_PLUS_OTHER_EQUALS_TOTAL_INCOME",
                    "parent_role": "TOTAL_INCOME",
                    "term_roles": ["SALARY_FUND", "OTHER_INCOME"],
                }
            ],
            ratio_equations=[
                ["AVERAGE_SALARY_MONTH", "SALARY_FUND", "EMPLOYEE_COUNT", 12, 2],
                ["AVERAGE_INCOME_MONTH", "TOTAL_INCOME", "EMPLOYEE_COUNT", 12, 2],
            ],
            period_axis=[(27, "Năm 2025"), (28, "Năm 2024")],
            units=[(29, "Triệu VND"), (30, "Triệu VND")],
            presentation="ANNUAL_AVERAGES_WITH_COMPONENT_INCOME_DERIVED_TO_MONTHLY_SCHEMA",
        )
    )
    docs.append(base._absence("MBB"))
    page = 73
    docs.append(
        _document(
            base,
            "VPB",
            page,
            owner=[(63, "TÌNH HÌNH THU NHẬP CỦA NHÂN VIÊN")],
            mappings=[
                _mapping(
                    base,
                    "EMPLOYEE_COUNT",
                    1261,
                    page,
                    [(66, "Tổng số nhân viên bình quân (người)")],
                    (68, "28.098"),
                    (69, "26.199"),
                ),
                _mapping(
                    base,
                    "SALARY_FUND",
                    1263,
                    page,
                    [(71, "Tổng quỹ lương")],
                    (72, "10.081.576"),
                    (73, "7.416.358"),
                ),
                _mapping(
                    base,
                    "OTHER_INCOME",
                    1265,
                    page,
                    [(74, "Thu nhập khác")],
                    (75, "1.121.327"),
                    (76, "979.205"),
                ),
                _mapping(
                    base,
                    "TOTAL_INCOME",
                    1266,
                    page,
                    [(77, "Tổng thu nhập")],
                    (78, "11.202.903"),
                    (79, "8.395.563"),
                ),
                _mapping(
                    base,
                    "AVERAGE_SALARY_MONTH",
                    1267,
                    page,
                    [(80, "Tiền lương bình quân tháng")],
                    (81, "29,90"),
                    (82, "23,59"),
                    decimal_value=True,
                ),
                _mapping(
                    base,
                    "AVERAGE_INCOME_MONTH",
                    1268,
                    page,
                    [(83, "Thu nhập bình quân tháng")],
                    (84, "33,23"),
                    (85, "26,70"),
                    decimal_value=True,
                ),
            ],
            equations=[
                {
                    "name": "SALARY_PLUS_OTHER_EQUALS_TOTAL_INCOME",
                    "parent_role": "TOTAL_INCOME",
                    "term_roles": ["SALARY_FUND", "OTHER_INCOME"],
                }
            ],
            ratio_equations=[
                ["AVERAGE_SALARY_MONTH", "SALARY_FUND", "EMPLOYEE_COUNT", 12, 2],
                ["AVERAGE_INCOME_MONTH", "TOTAL_INCOME", "EMPLOYEE_COUNT", 12, 2],
            ],
            period_axis=[(64, "Năm 2025"), (65, "Năm 2024")],
            units=[(70, "Thu nhập của nhân viên (Triệu đồng)")],
            presentation="MONTHLY_AVERAGES_WITH_COMPONENT_INCOME",
        )
    )
    docs.extend([base._absence("HDB"), base._absence("VCB"), base._absence("CTG")])
    page = 58
    docs.append(
        _document(
            base,
            "BID",
            page,
            owner=[(81, "TÌNH HÌNH THU NHẬP CỦA CÁN BỘ, NHÂN VIÊN")],
            mappings=[
                _mapping(
                    base,
                    "EMPLOYEE_COUNT",
                    1261,
                    page,
                    [(85, "Tổng số cán bộ, nhân viên bình quân trong năm"), (88, "(người)")],
                    (86, "29.525"),
                    (87, "29.337"),
                    topology="WRAPPED_LABEL_TWO_ANNUAL_PERIOD_LANES",
                ),
                _mapping(
                    base,
                    "TOTAL_INCOME",
                    1266,
                    page,
                    [(90, "Tổng thu nhập")],
                    (91, "14.506.803"),
                    (92, "13.016.911"),
                ),
                _mapping(
                    base,
                    "AVERAGE_INCOME_MONTH",
                    1268,
                    page,
                    [(93, "Thu nhập bình quân tháng (triệu đồng/người)")],
                    (94, "40,94"),
                    (95, "36,98"),
                    decimal_value=True,
                ),
            ],
            equations=[],
            ratio_equations=[["AVERAGE_INCOME_MONTH", "TOTAL_INCOME", "EMPLOYEE_COUNT", 12, 2]],
            period_axis=[(83, "Năm nay"), (84, "Năm trước")],
            units=[
                (89, "Thu nhập của cán bộ, nhân viên (triệu đồng)"),
                (93, "Thu nhập bình quân tháng (triệu đồng/người)"),
            ],
            presentation="WRAPPED_EMPLOYEE_COUNT_LABEL_TOTAL_INCOME_AND_MONTHLY_AVERAGE",
        )
    )
    page = 54
    docs.append(
        _document(
            base,
            "VIB",
            page,
            owner=[(5, "TÌNH HÌNH THU NHẬP CỦA CÁN BỘ NHÂN VIÊN")],
            mappings=[
                _mapping(
                    base,
                    "EMPLOYEE_COUNT",
                    1261,
                    page,
                    [(10, "Bình quân số cán bộ, nhân viên (người)")],
                    (11, "10.782"),
                    (12, "11.824"),
                ),
                _mapping(
                    base,
                    "EMPLOYEE_INCOME",
                    1262,
                    page,
                    [(13, "Thu nhập của cán bộ, nhân viên")],
                    (14, "4.756.035"),
                    (15, "4.396.571"),
                ),
                _mapping(
                    base,
                    "AVERAGE_INCOME_MONTH",
                    1268,
                    page,
                    [(18, "Thu nhập bình quân/tháng")],
                    (16, "36.76"),
                    (17, "30,99"),
                    decimal_value=True,
                    topology="VALUES_PRECEDE_TRAILING_LABEL_TWO_ANNUAL_PERIOD_LANES",
                ),
            ],
            equations=[],
            ratio_equations=[["AVERAGE_INCOME_MONTH", "EMPLOYEE_INCOME", "EMPLOYEE_COUNT", 12, 2]],
            period_axis=[(6, "2025"), (7, "2024")],
            units=[(8, "triệu đồng"), (9, "triệu đồng")],
            presentation="DIRECT_EMPLOYEE_INCOME_VALUES_PRECEDE_MONTHLY_AVERAGE_LABEL",
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
        raise _error("annual employee-income document order drifted")
    return docs


def _base() -> ModuleType:
    base = _load_base()
    base.FORMAT_VERSION = FORMAT_VERSION
    base.REVIEW_FORMAT = REVIEW_FORMAT
    base.RESULT_STATE = RESULT_STATE
    base.RESULT_ID_PREFIX = RESULT_ID_PREFIX
    base.REVIEW_STATE = REVIEW_STATE
    base.REVIEW_ID_PREFIX = REVIEW_ID_PREFIX
    base.FAMILY_END_DISPLAY_ORDER = 848
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
    base._review_documents = lambda: _review_documents(base)
    return base


def build_annual_2025_employee_income_pixel_review_blueprint_v1() -> dict[str, Any]:
    return _base()._review_blueprint()


def build_live_annual_2025_employee_income_8bank_codex_verified_mapping_v1() -> dict[str, Any]:
    try:
        return _base().build_live_employee_income_8bank_codex_verified_mapping_v1()
    except Annual2025EmployeeIncome8BankError:
        raise
    except Exception as exc:
        raise _error(str(exc)) from exc


def validate_annual_2025_employee_income_8bank_codex_verified_mapping_replay_v1(
    value: Any,
) -> dict[str, Any]:
    try:
        return _base().validate_live_employee_income_8bank_codex_verified_mapping_v1(value)
    except Annual2025EmployeeIncome8BankError:
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
            canonical_json_bytes_v1(build_annual_2025_employee_income_pixel_review_blueprint_v1())
        )
        return 0
    if args.write_result:
        result = build_live_annual_2025_employee_income_8bank_codex_verified_mapping_v1()
        RESULT_PATH.write_bytes(canonical_json_bytes_v1(result))
        print(result["result_id"])
        return 0
    result, _ = _base()._stable_json(RESULT_PATH)
    verified = validate_annual_2025_employee_income_8bank_codex_verified_mapping_replay_v1(result)
    print(verified["result_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
