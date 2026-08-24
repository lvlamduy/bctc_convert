"""Declarative Vietnamese aliases and safety policy for loan Family 12.

Family 12 is report-normalization node 766 (``Phân tích theo loại hình
doanh nghiệp``), owned by node 716 (``Cho vay khách hàng``).  This module is
data only: it contains no bank, filename, page, numeric, or model route.

The historical counts describe the closed 140-filing study supplied for this
family.  They are evidence metadata, not priors that can turn text into a
mapping.  In particular, RNID 775 and RNID 777 were not observed exactly in
that study, and broad source rows remain ambiguous even when their wording is
similar to those schema labels.
"""

from __future__ import annotations

from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1

__all__ = [
    "FAMILY_ID",
    "FORMAT_VERSION",
    "PARENT_REPORT_NORM_ID",
    "REPORT_NORM_ID",
    "build_loan_enterprise_family12_spec_v1",
]


FORMAT_VERSION = "LOAN_ENTERPRISE_FAMILY12_SPEC_V1"
FAMILY_ID = "LOAN_ENTERPRISE_FAMILY12"
REPORT_NORM_ID = 766
PARENT_REPORT_NORM_ID = 716


_BRANCH_ALIASES = [
    "Phân tích theo loại hình doanh nghiệp",
    "Theo loại hình doanh nghiệp",
    "Loại hình doanh nghiệp",
    "Phân loại dư nợ cho vay theo loại hình doanh nghiệp",
    "Phân tích cho vay khách hàng theo loại hình doanh nghiệp",
    "Phân tích dư nợ cho vay theo loại hình doanh nghiệp",
    "Phân tích dư nợ cho vay khách hàng theo loại hình doanh nghiệp",
    "Phân tích dư nợ cho vay theo đối tượng khách hàng và loại hình doanh nghiệp",
    "Phân tích dư nợ cho vay theo đối tượng khách hàng và theo loại hình doanh nghiệp",
    "Phân tích dư nợ cho vay khách hàng theo đối tượng và loại hình doanh nghiệp",
    "Phân tích dư nợ cho vay khách hàng theo đối tượng khách hàng và loại hình doanh nghiệp",
    "Phân tích dư nợ cho vay khách hàng theo đối tượng khách hàng và theo loại hình doanh nghiệp",
    "Phân tích dư nợ cho vay theo đối tượng khách hàng theo loại hình doanh nghiệp",
]

_BRANCH_COMPONENTS = [
    {
        "aliases": ["Loại hình doanh nghiệp"],
        "bounded_edit_on_exact_miss": True,
        "component_id": "BRANCH_LOAI_HINH_DOANH_NGHIEP",
    },
    {
        "aliases": ["Theo đối tượng khách hàng"],
        "bounded_edit_on_exact_miss": True,
        "component_id": "BRANCH_THEO_DOI_TUONG_KHACH_HANG",
    },
]

_OWNER_ALIASES = [
    "Cho vay khách hàng",
    "Cho vay khách hàng (tiếp theo)",
    "Các khoản cho vay khách hàng",
    "Dư nợ cho vay khách hàng",
]

_CONTEXT_CLASSES = [
    {
        "aliases": _OWNER_ALIASES,
        "context_id": "OWNER_716",
        "disposition": "REQUIRED_OWNER",
        "report_norm_ids": [716],
    },
    {
        "allow_token_subsequence_fence": True,
        "aliases": [
            "Tiền gửi của khách hàng",
            "Tiền gửi khách hàng",
        ],
        "context_id": "DEPOSIT_1055",
        "disposition": "HARD_VETO",
        "report_norm_ids": [1055],
    },
    {
        "allow_token_subsequence_fence": True,
        "aliases": [
            "Theo loại hình doanh nghiệp tiền gửi",
            "Phân tích tiền gửi khách hàng theo loại hình doanh nghiệp",
            "Phân tích tiền gửi khách hàng theo đối tượng khách hàng",
        ],
        "context_id": "DEPOSIT_1075",
        "disposition": "HARD_VETO",
        "report_norm_ids": [1075],
    },
    {
        "allow_token_subsequence_fence": True,
        "aliases": [
            "IV. Một số thông tin khác",
            "Một số thông tin khác",
        ],
        "context_id": "RELATED_1259",
        "disposition": "HARD_VETO",
        "report_norm_ids": [1259],
    },
    {
        "allow_token_subsequence_fence": True,
        "aliases": [
            "Giao dịch với các bên liên quan",
            "Các giao dịch với bên liên quan",
            "Các giao dịch với các bên liên quan",
        ],
        "context_id": "RELATED_5750",
        "disposition": "HARD_VETO",
        "report_norm_ids": [5750],
    },
    {
        "allow_token_subsequence_fence": True,
        "aliases": [
            "Giao dịch tiền gửi tại MB",
            "Giao dịch tiền gửi với MB",
        ],
        "context_id": "RELATED_5751",
        "disposition": "HARD_VETO",
        "report_norm_ids": [5751],
    },
]

_STRUCTURAL_RESET_ALIASES = [
    "Tiền gửi của khách hàng",
    "Theo tiền tệ và loại tiền gửi",
    "Giao dịch với các bên liên quan",
    "Giao dịch tiền gửi tại MB",
    "IV. Một số thông tin khác",
    "Một số thông tin khác",
    "Chứng khoán đầu tư",
    "Tài sản cố định",
    "Các khoản đầu tư dài hạn khác",
    "Biến động số dư dự phòng rủi ro cho vay khách hàng",
    "Phân tích theo loại hình cho vay",
    "Phân tích theo ngành nghề kinh doanh",
    "Phân tích theo loại hình tiền tệ",
    "Phân tích chất lượng nợ cho vay",
    "Phân tích dư nợ theo thời gian đáo hạn",
    "Phân tích dư nợ theo ngành kinh tế",
    "Phân tích dư nợ theo khu vực địa lý",
    "Phân tích dư nợ theo loại tiền tệ",
]


def _child(
    report_norm_id: int,
    canonical_name: str,
    aliases: list[str],
    *,
    historical_disposition: str = "OBSERVED_OR_SCHEMA_DECLARED",
    bounded_edit: bool = True,
    binding_class: str = "STANDARD_SCHEMA_ROW",
) -> dict[str, Any]:
    return {
        "aliases": aliases,
        "binding_class": binding_class,
        "bounded_edit_on_exact_miss": bounded_edit,
        "canonical_name": canonical_name,
        "historical_disposition": historical_disposition,
        "report_norm_id": report_norm_id,
    }


_CHILDREN = [
    _child(
        767,
        "Doanh nghiệp nhà nước",
        ["Doanh nghiệp nhà nước", "Công ty nhà nước"],
    ),
    _child(
        768,
        "Công ty TNHH",
        ["Công ty TNHH", "Công ty trách nhiệm hữu hạn", "Doanh nghiệp TNHH"],
    ),
    _child(
        769,
        "Công ty TNHH MTV vốn nhà nước 100%",
        [
            "Công ty TNHH MTV vốn nhà nước 100%",
            "Công ty TNHH một thành viên vốn nhà nước 100%",
            "Công ty TNHH MTV do Nhà nước sở hữu 100% vốn điều lệ",
            "Công ty TNHH một thành viên do Nhà nước sở hữu 100% vốn điều lệ",
        ],
    ),
    _child(
        770,
        "Công ty TNHH MTV (hoặc trên MTV) vốn nhà nước trên 50%",
        [
            "Công ty TNHH MTV (hoặc trên MTV) vốn nhà nước trên 50%",
            "Công ty TNHH MTV vốn nhà nước trên 50%",
            "Công ty TNHH có vốn nhà nước trên 50%",
            "Công ty TNHH có trên 50% vốn điều lệ do Nhà nước sở hữu",
        ],
    ),
    _child(
        771,
        "Công ty TNHH khác",
        ["Công ty TNHH khác", "Công ty trách nhiệm hữu hạn khác"],
    ),
    _child(
        772,
        "Công ty cổ phần có vốn nhà nước trên 50%",
        [
            "Công ty cổ phần có vốn nhà nước trên 50%",
            "Công ty cổ phần có trên 50% vốn điều lệ do Nhà nước sở hữu",
            "Công ty cổ phần do Nhà nước nắm giữ trên 50% vốn điều lệ",
        ],
    ),
    _child(773, "Công ty cổ phần khác", ["Công ty cổ phần khác", "Công ty CP khác"]),
    _child(774, "Doanh nghiệp tư nhân", ["Doanh nghiệp tư nhân", "DN tư nhân"]),
    _child(
        775,
        "Công ty CP, TNHH, DN tư nhân",
        ["Công ty CP, TNHH, DN tư nhân"],
        historical_disposition="BOUNDED_ABSENCE_IN_HISTORICAL_140",
        bounded_edit=False,
    ),
    _child(
        776,
        "Hợp tác xã và liên hợp tác xã",
        [
            "Hợp tác xã và liên hợp tác xã",
            "Hợp tác xã và liên hiệp hợp tác xã",
            "Hợp tác xã và liên hiệp HTX",
        ],
    ),
    _child(
        6074,
        "Hợp tác xã và công ty tư nhân",
        ["Hợp tác xã và công ty tư nhân", "Hợp tác xã và doanh nghiệp tư nhân"],
    ),
    _child(
        777,
        "Công ty liên doanh, hợp doanh",
        ["Công ty liên doanh, hợp doanh"],
        historical_disposition="BOUNDED_ABSENCE_IN_HISTORICAL_140",
        bounded_edit=False,
    ),
    _child(778, "Công ty hợp danh", ["Công ty hợp danh"]),
    _child(
        779,
        "Công ty vốn nước ngoài",
        [
            "Công ty vốn nước ngoài",
            "Doanh nghiệp có vốn đầu tư nước ngoài",
            "Doanh nghiệp vốn đầu tư nước ngoài",
            "Doanh nghiệp có vốn nước ngoài",
        ],
    ),
    _child(
        780,
        "Hộ kinh doanh, cá nhân",
        [
            "Hộ kinh doanh, cá nhân",
            "Cá nhân và hộ kinh doanh cá thể",
            "Hộ kinh doanh và cá nhân",
            "Hộ gia đình và cá nhân",
        ],
    ),
    _child(
        781,
        "Dịch vụ hành chính sự nghiệp, Đảng, đoàn thể, hiệp hội",
        [
            "Dịch vụ hành chính sự nghiệp, Đảng, đoàn thể, hiệp hội",
            "Đơn vị hành chính sự nghiệp, Đảng, đoàn thể và hiệp hội",
            "Đơn vị hành chính sự nghiệp, đoàn thể và hiệp hội",
            "Các đơn vị hành chính sự nghiệp, Đảng, đoàn thể, hiệp hội",
        ],
    ),
    _child(
        782,
        "Khác",
        [
            "Khác",
            "Thành phần kinh tế khác",
            "Cho vay tại chi nhánh và ngân hàng con nước ngoài",
            "Dư nợ tại chi nhánh và ngân hàng con nước ngoài",
            "Dư nợ tại chi nhánh ngân hàng con ở nước ngoài",
            "Chi nhánh và ngân hàng con tại nước ngoài",
            "Chi nhánh và công ty con tại nước ngoài",
            "Chi nhánh và công ty con ở nước ngoài",
        ],
        binding_class="FOREIGN_BRANCH_OR_SUBSIDIARY_COMPONENT_TO_OTHER",
    ),
    _child(
        5748,
        "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
        [
            "Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
            "Cho vay ký quỹ và ứng trước tiền bán chứng khoán",
            "Cho vay giao dịch ký quỹ",
            "Ứng trước tiền bán chứng khoán",
        ],
    ),
]

_SOURCE_ONLY_AMBIGUITIES = [
    {
        "aliases": ["Công ty cổ phần", "Công ty CP"],
        "candidate_report_norm_ids": [772, 773],
        "reason": "UNQUALIFIED_JOINT_STOCK_COMPANY",
    },
    {
        "aliases": ["Hợp tác xã", "HTX"],
        "candidate_report_norm_ids": [776, 6074],
        "reason": "UNQUALIFIED_COOPERATIVE",
    },
    {
        "aliases": ["Cá nhân"],
        "candidate_report_norm_ids": [780],
        "reason": "PERSON_ONLY_DOES_NOT_PROVE_COMBINED_SCHEMA_SCOPE",
    },
    {
        "aliases": [
            "Công ty cổ phần, công ty TNHH và doanh nghiệp khác",
            "Công ty cổ phần, TNHH và doanh nghiệp khác",
            "Công ty CP, công ty TNHH và doanh nghiệp khác",
        ],
        "candidate_report_norm_ids": [768, 773, 774, 775],
        "reason": "MIXED_ACB_LEGAL_FORM_ROW_DOES_NOT_EQUAL_SCHEMA_775",
    },
]


_SPEC: dict[str, Any] = {
    "branch_aliases": _BRANCH_ALIASES,
    "branch_components": _BRANCH_COMPONENTS,
    "children": _CHILDREN,
    "context_classes": _CONTEXT_CLASSES,
    "family_id": FAMILY_ID,
    "format_version": FORMAT_VERSION,
    "historical_evidence_summary": {
        "bounded_absence_filing_count": 56,
        "exact_child_absence_report_norm_ids": [775, 777],
        "owner_carried_at_most_two_pages_present_count": 20,
        "present_filing_count": 84,
        "same_page_owner_present_count": 64,
        "studied_filing_count": 140,
    },
    "limits": {
        "branch_line_span": 3,
        "context_line_span": 3,
        "context_page_budget": 2,
        "maximum_body_lines_per_page": 96,
    },
    "parent_report_norm_id": PARENT_REPORT_NORM_ID,
    "report_norm_id": REPORT_NORM_ID,
    "source_only_ambiguities": _SOURCE_ONLY_AMBIGUITIES,
    "structural_reset_aliases": _STRUCTURAL_RESET_ALIASES,
    "structural_reset_component_aliases": _STRUCTURAL_RESET_ALIASES,
    "safety": {
        "branch_heading_alone_is_owner": False,
        "bounded_edit_runs_when_any_exact_row_candidate_exists": False,
        "deposit_report_norm_ids_are_hard_veto": [1055, 1075],
        "distinct_fuzzy_branch_regions_are_retained_for_topology_resolution": True,
        "foreign_branch_or_subsidiary_allowed_report_norm_ids": [782],
        "foreign_branch_or_subsidiary_forbidden_report_norm_ids": [765, 6058],
        "mapping_authority": False,
        "numeric_authority": False,
        "related_party_report_norm_ids_are_hard_veto": [1259, 5750, 5751],
        "source_only_ambiguous_rows_can_map": False,
    },
}


def build_loan_enterprise_family12_spec_v1() -> dict[str, Any]:
    """Return an isolated exact copy of the declarative Family 12 policy."""

    return canonical_clone_v1(_SPEC)
