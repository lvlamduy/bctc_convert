"""Human-readable labels used by the review application."""

FAMILY_NAMES_VI = {
    "BANK_PLEDGED_OR_DISCOUNTED_ASSETS": "Tài sản/GTCG ngân hàng đem thế chấp, cầm cố, chiết khấu",
    "CAPITAL_AND_FUNDS": "Vốn và các quỹ",
    "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME": "Thu nhập góp vốn, mua cổ phần và cổ tức",
    "CASH_EQUIVALENTS": "Tiền và các khoản tương đương tiền",
    "CASH_PRECIOUS_METALS": "Tiền, kim loại quý và đá quý",
    "CENTRAL_BANK_DEPOSITS": "Tiền gửi tại Ngân hàng Nhà nước",
    "COMBINED_SECURITIES_NET": "Lãi thuần chứng khoán kinh doanh và đầu tư gộp",
    "CONSOLIDATED_SEGMENT_REPORT": "Báo cáo bộ phận hợp nhất",
    "CONTINGENT_LIABILITIES_AND_COMMITMENTS": "Nghĩa vụ nợ tiềm ẩn và các cam kết",
    "CREDIT_RISK_PROVISION_EXPENSE": "Chi phí dự phòng rủi ro tín dụng",
    "CURRENCY_RISK": "Rủi ro tiền tệ",
    "CUSTOMER_COLLATERAL_HELD": "Tài sản thế chấp của khách hàng ngân hàng đang nắm giữ",
    "CUSTOMER_DEPOSIT_CLASSIFICATION": "Tiền gửi khách hàng theo loại/kỳ hạn/đối tượng",
    "DERIVATIVE_FINANCIAL_INSTRUMENTS": "Công cụ tài chính phái sinh",
    "EMPLOYEE_INCOME": "Thu nhập nhân viên ngân hàng",
    "ENTRUSTED_INVESTMENT_RISK_CAPITAL": "Vốn tài trợ, ủy thác đầu tư và cho vay chịu rủi ro",
    "EXCHANGE_RATE": "Tỷ giá ngoại tệ cuối kỳ",
    "FINANCIAL_INSTRUMENTS": "Công cụ tài chính — giá ghi sổ và giá trị hợp lý",
    "FX_GOLD_ACTIVITY": "Lãi/lỗ thuần kinh doanh vàng và ngoại hối",
    "GOVERNMENT_SBV_LIABILITIES": "Nợ Chính phủ và Ngân hàng Nhà nước",
    "INCOME_TAX": "Chi phí thuế thu nhập doanh nghiệp",
    "INTANGIBLE_FIXED_ASSETS_ROLLFORWARD": "Tăng, giảm tài sản cố định vô hình",
    "INTERBANK_DEPOSITS_AND_LOANS": "Tiền gửi tại và cho vay các TCTD khác — tài sản",
    "INTERBANK_FUNDING": "Tiền gửi và vay các TCTD khác — nguồn vốn",
    "INTEREST_EXPENSE": "Chi phí lãi và các khoản tương tự",
    "INTEREST_INCOME": "Thu nhập lãi và các khoản tương tự",
    "INTEREST_RATE_RISK": "Rủi ro lãi suất",
    "INVESTMENT_PROPERTY_ROLLFORWARD": "Tăng, giảm bất động sản đầu tư",
    "INVESTMENT_SECURITIES": "Chứng khoán đầu tư",
    "INVESTMENT_SECURITIES_ACTIVITY": "Lãi/lỗ thuần mua bán chứng khoán đầu tư",
    "ISSUED_VALUABLE_PAPERS": "Phát hành giấy tờ có giá",
    "LEASED_FIXED_ASSETS_ROLLFORWARD": "Tăng, giảm tài sản cố định thuê tài chính",
    "LIQUIDITY_RISK": "Rủi ro thanh khoản",
    "NET_INTEREST_INCOME": "Thu nhập từ lãi thuần",
    "LOAN_CURRENCY_CLASSIFICATION": "Cho vay theo loại tiền tệ",
    "LOAN_ENTERPRISE_FAMILY12": "Cho vay theo loại hình doanh nghiệp/đối tượng",
    "LOAN_GEOGRAPHIC_CLASSIFICATION": "Cho vay theo khu vực địa lý",
    "LOAN_INDUSTRY_CLASSIFICATION": "Cho vay theo ngành nghề kinh doanh",
    "LOAN_MATURITY_BUCKETS": "Dư nợ theo thời gian/thời hạn gốc",
    "LOAN_QUALITY_CLASSIFICATION": "Phân tích chất lượng cho vay",
    "LOAN_TYPE_CLASSIFICATION": "Cho vay theo loại hình",
    "OPERATING_EXPENSE": "Chi phí quản lý chung/chi phí hoạt động",
    "OTHER_ACTIVITY": "Thu nhập, chi phí và lãi thuần hoạt động khác",
    "OTHER_ASSETS": "Tài sản Có khác",
    "OTHER_LONG_TERM_INVESTMENTS": "Các khoản đầu tư dài hạn khác",
    "OTHER_PAYABLES_LIABILITIES": "Các khoản phải trả và công nợ khác",
    "PROVISION_MOVEMENT_ROLLFORWARD": "Biến động dự phòng rủi ro cho vay",
    "PURCHASED_DEBT_ACTIVITY": "Hoạt động mua nợ",
    "SECURITIES_GEOGRAPHY": "Kinh doanh và đầu tư chứng khoán theo địa lý",
    "SERVICE_ACTIVITY": "Thu nhập, chi phí và lãi thuần dịch vụ",
    "STATE_BUDGET_OBLIGATIONS": "Nghĩa vụ với ngân sách Nhà nước",
    "SUBSIDIARY_ACQUISITION_DISPOSAL": "Mua mới và thanh lý công ty con",
    "TANGIBLE_FIXED_ASSETS_ROLLFORWARD": "Tăng, giảm tài sản cố định hữu hình",
    "TRADING_SECURITIES": "Chứng khoán kinh doanh",
    "TRADING_SECURITIES_ACTIVITY": "Lãi/lỗ thuần mua bán chứng khoán kinh doanh",
}

# Business/schema order used throughout the project's family dashboard. Keep
# this independent from technical IDs so the picker remains stable and easy to
# compare with the completed-family ledger.
FAMILY_ORDER = (
    "CASH_PRECIOUS_METALS",
    "CENTRAL_BANK_DEPOSITS",
    "INTERBANK_DEPOSITS_AND_LOANS",
    "TRADING_SECURITIES",
    "DERIVATIVE_FINANCIAL_INSTRUMENTS",
    "LOAN_TYPE_CLASSIFICATION",
    "LOAN_INDUSTRY_CLASSIFICATION",
    "LOAN_QUALITY_CLASSIFICATION",
    "LOAN_MATURITY_BUCKETS",
    "LOAN_CURRENCY_CLASSIFICATION",
    "LOAN_GEOGRAPHIC_CLASSIFICATION",
    "LOAN_ENTERPRISE_FAMILY12",
    "PROVISION_MOVEMENT_ROLLFORWARD",
    "PURCHASED_DEBT_ACTIVITY",
    "CUSTOMER_DEPOSIT_CLASSIFICATION",
    "INVESTMENT_SECURITIES",
    "OTHER_LONG_TERM_INVESTMENTS",
    "TANGIBLE_FIXED_ASSETS_ROLLFORWARD",
    "LEASED_FIXED_ASSETS_ROLLFORWARD",
    "INTANGIBLE_FIXED_ASSETS_ROLLFORWARD",
    "INVESTMENT_PROPERTY_ROLLFORWARD",
    "OTHER_ASSETS",
    "GOVERNMENT_SBV_LIABILITIES",
    "ENTRUSTED_INVESTMENT_RISK_CAPITAL",
    "ISSUED_VALUABLE_PAPERS",
    "OTHER_PAYABLES_LIABILITIES",
    "CAPITAL_AND_FUNDS",
    "INTEREST_INCOME",
    "INTEREST_EXPENSE",
    "NET_INTEREST_INCOME",
    "SERVICE_ACTIVITY",
    "FX_GOLD_ACTIVITY",
    "TRADING_SECURITIES_ACTIVITY",
    "INVESTMENT_SECURITIES_ACTIVITY",
    "COMBINED_SECURITIES_NET",
    "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME",
    "OPERATING_EXPENSE",
    "CREDIT_RISK_PROVISION_EXPENSE",
    "OTHER_ACTIVITY",
    "INCOME_TAX",
    "CASH_EQUIVALENTS",
    "SUBSIDIARY_ACQUISITION_DISPOSAL",
    "EMPLOYEE_INCOME",
    "STATE_BUDGET_OBLIGATIONS",
    "CUSTOMER_COLLATERAL_HELD",
    "BANK_PLEDGED_OR_DISCOUNTED_ASSETS",
    "CONTINGENT_LIABILITIES_AND_COMMITMENTS",
    "FINANCIAL_INSTRUMENTS",
    "CURRENCY_RISK",
    "INTEREST_RATE_RISK",
    "LIQUIDITY_RISK",
    "EXCHANGE_RATE",
    "INTERBANK_FUNDING",
    "SECURITIES_GEOGRAPHY",
    "CONSOLIDATED_SEGMENT_REPORT",
)

VALUE_STATE_NAMES_VI = {
    "RAW_SIGNED_INTEGER": "Số đọc trực tiếp từ PDF",
    "SOURCE_BLANK": "Ô nguồn để trống",
    "DASH_ZERO": "Dấu gạch được xác nhận là số 0",
    "INVALID_MONEY_SOURCE": "Ô số nguồn không đọc được an toàn",
    "AMBIGUOUS_MONEY_SOURCE": "Ô số nguồn có nhiều cách hiểu",
    "DERIVED_EXACT_RECURSIVE_DIRECT_FRONTIER": (
        "Giá trị được tính chính xác từ các dòng nguồn đã xác thực"
    ),
}

STATUS_NAMES_VI = {
    "READY": "Đã map",
    "NOT_OBSERVED": "Không xuất hiện",
    "UNRESOLVED": "Cần kiểm tra",
}

REASON_NAMES_VI = {
    "SEGMENT_PERIOD_NOT_RESOLVED": "Chưa xác định chắc kỳ của bảng",
    "SEGMENT_MONEY_CELL_INVALID": "Ô số nguồn không hợp lệ",
    "SEGMENT_MONEY_CELL_AMBIGUOUS": "Ô số nguồn có nhiều cách đọc",
    "SEGMENT_PERIOD_END_NOT_RESOLVED": "Chưa xác định chắc ngày kết thúc kỳ",
    "INSUFFICIENT_DECLARED_SEGMENT_AXIS_COVERAGE": "Chưa đủ cột thuộc schema để map an toàn",
    "REQUIRED_COMBINATION_NOT_OBSERVED": "Chưa thấy đủ nhóm khoản mục bắt buộc",
    "VISIBLE_SEGMENT_TOTAL_MISMATCH": "Tổng nhìn thấy trên PDF không khớp các thành phần",
    "FAMILY_PARENT_NOT_VISIBLE_IN_SECTION_TABLE_OR_UNIQUE_ROW": (
        "Không thấy nhãn family cha ngay trong bảng/section; tiêu đề cha có thể nằm ở phần trước"
    ),
    "FAMILY_ROOT_IS_NOT_HIERARCHICALLY_RESOLVED": (
        "Chưa nối chắc được bảng con với khoản mục gốc của family"
    ),
    "HARD_NEGATIVE_FAMILY_TITLE_PRESENT": "Tiêu đề cho thấy bảng có thể thuộc family khác",
    "HIERARCHICAL_SOLUTION_COUNT_NOT_ONE:0": "Không tìm được một cấu trúc cha/con duy nhất",
}


def family_name(family_id: str) -> str:
    """Return a stable Vietnamese display name, with a readable fallback."""

    return FAMILY_NAMES_VI.get(family_id, family_id.replace("_", " ").title())


def status_bucket(status: str) -> str:
    """Normalize verbose persisted dispositions for the human-facing UI."""

    if status.startswith("READY"):
        return "READY"
    if status.startswith("NOT_OBSERVED"):
        return "NOT_OBSERVED"
    if status.startswith("UNRESOLVED"):
        return "UNRESOLVED"
    return status


def reason_name(reason: str) -> str:
    """Return a short Vietnamese explanation for a technical reason code."""

    if reason.startswith("ROLE_OCCURRENCE_COUNT_ABOVE_ONE:"):
        return "Một nhãn xuất hiện nhiều lần nên chưa xác định được đúng dòng cha/con"
    if reason.startswith("EXACT_DIRECT_FRONTIER_SOLUTION_COUNT_NOT_ONE:"):
        return "Không tìm được đúng một phép cộng/đối chiếu khép kín"
    return REASON_NAMES_VI.get(reason, reason.replace("_", " ").lower())
