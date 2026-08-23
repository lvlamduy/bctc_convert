"""Schema-free graph specification for customer-loan currency analysis.

The family is identified from one complete financial-statement document by an
explicit currency-analysis branch and the smallest useful pair of currency
children.  The pair by itself is intentionally *not* an accepting graph: the
same ``VND``/``foreign currency`` labels occur in interbank, deposit and risk
tables throughout the corpus.

Two layouts share this one declarative topology:

* qualified currency rows directly under the branch; and
* repeated generic currency rows scoped by visible structural groups.  The
  latter covers a customer-loan subtotal followed by a source-only deferred-LC
  population without assigning either population by bank, page or ordinal.

This module contains no schema IDs and emits no mapping.  Periods, units,
numeric reconciliation and pixel-dash evidence are independent downstream
gates.  In particular, a blank detector lane is never treated as zero here.
"""

from __future__ import annotations

from typing import Any

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    SPEC_FORMAT_VERSION_V3 as TOPOLOGY_SPEC_FORMAT_VERSION,
)
from bctc_ai.evaluation.accounting_family_topology_v1 import (
    AccountingFamilyTopologyV1Error,
    build_accounting_family_topology_scan_v1,
    validate_accounting_family_topology_scan_replay_v1,
)
from bctc_ai.evaluation.accounting_hierarchical_table_closure_v1 import (
    SPEC_FORMAT_VERSION_V3 as HIERARCHY_SPEC_FORMAT_VERSION,
)

__all__ = [
    "FAMILY_ID",
    "FORMAT_VERSION",
    "LOAN_CURRENCY_EVALUATION_SPEC_V2",
    "LOAN_CURRENCY_HIERARCHY_SPEC_V2",
    "LOAN_CURRENCY_TOPOLOGY_SPEC_V2",
    "LoanCurrencyVariantGraphV2Error",
    "build_loan_currency_topology_scan_v2",
    "validate_loan_currency_topology_scan_replay_v2",
]


FORMAT_VERSION = "LOAN_CURRENCY_VARIANT_GRAPH_SPEC_V2"
FAMILY_ID = "LOAN_CURRENCY_CLASSIFICATION"

_BRANCH_ALIASES = (
    "Theo loại tiền tệ",
    "Theo loại hình tiền tệ",
    "Phân tích theo loại hình tiền tệ",
    "Phân tích theo loại tiền tệ",
    "Phân tích dư nợ theo loại hình tiền tệ",
    "Phân tích dư nợ theo loại tiền tệ",
    "Phân tích dư nợ cho vay theo loại tiền tệ",
    "Phân tích dư nợ theo loại tiền",
    "Phân loại dư nợ theo loại tiền tệ",
    "Phân tích cho vay theo loại tiền tệ",
)
_CORE_GROUP_ALIASES = (
    "Cho vay khách hàng",
    "Các khoản cho vay khách hàng",
    "Dư nợ cho vay khách hàng",
)
_QUALIFIED_VND_ALIASES = (
    "Cho vay bằng VND",
    "Cho vay bằng đồng Việt Nam",
    "Dư nợ bằng VND",
    "Dư nợ bằng đồng Việt Nam",
    "Dư nợ cho vay bằng VND",
    "Dư nợ cho vay bằng đồng Việt Nam",
)
_CONTEXTUAL_VND_ALIASES = (
    "Bằng VND",
    "Bằng đồng Việt Nam",
)
_QUALIFIED_FOREIGN_ALIASES = (
    "Cho vay bằng ngoại tệ",
    "Cho vay bằng ngoại tệ và vàng",
    "Cho vay bằng vàng và ngoại tệ",
    "Dư nợ bằng ngoại tệ",
    "Dư nợ bằng ngoại tệ và vàng",
    "Dư nợ bằng vàng và ngoại tệ",
    "Dư nợ cho vay bằng ngoại tệ",
    "Dư nợ cho vay bằng ngoại tệ và vàng",
    "Dư nợ cho vay bằng vàng và ngoại tệ",
)
_CONTEXTUAL_FOREIGN_ALIASES = (
    "Bằng ngoại tệ",
    "Bằng ngoại tệ và vàng",
    "Bằng vàng và ngoại tệ",
)
_DEFERRED_LC_GROUP_ALIASES = (
    "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày 01 tháng 7 năm 2024",
    "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày 1 tháng 7 năm 2024",
    "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày 01/07/2024",
    "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày 1/7/2024",
)


def _matcher(aliases: tuple[str, ...], within_role: str | None) -> dict[str, Any]:
    return {"aliases": list(aliases), "within_role": within_role}


# All roles are optional because V3 expresses the minimal accepting core as an
# alternative role combination.  The explicit parent scopes that combination;
# a loose VND/foreign-currency pair can therefore never create a positive.
LOAN_CURRENCY_TOPOLOGY_SPEC_V2 = {
    "children": [
        {
            "matchers": [_matcher(_CORE_GROUP_ALIASES, None)],
            "presence": "OPTIONAL",
            "role": "CORE_TOTAL_GROUP",
            "role_kind": "STRUCTURAL_GROUP",
        },
        {
            "matchers": [
                _matcher(_QUALIFIED_VND_ALIASES, None),
                _matcher(_CONTEXTUAL_VND_ALIASES, "CORE_TOTAL_GROUP"),
            ],
            "presence": "OPTIONAL",
            "role": "VND_LOANS",
            "role_kind": "ADDITIVE_CHILD",
        },
        {
            "matchers": [
                _matcher(_QUALIFIED_FOREIGN_ALIASES, None),
                _matcher(_CONTEXTUAL_FOREIGN_ALIASES, "CORE_TOTAL_GROUP"),
            ],
            "presence": "OPTIONAL",
            "role": "FOREIGN_CURRENCY_AND_GOLD_LOANS",
            "role_kind": "ADDITIVE_CHILD",
        },
        {
            "matchers": [_matcher(_DEFERRED_LC_GROUP_ALIASES, None)],
            "presence": "OPTIONAL",
            "role": "DEFERRED_LC_PRE_2024_GROUP",
            "role_kind": "STRUCTURAL_GROUP",
        },
        {
            "matchers": [_matcher(_CONTEXTUAL_VND_ALIASES, "DEFERRED_LC_PRE_2024_GROUP")],
            "presence": "OPTIONAL",
            "role": "DEFERRED_LC_VND",
            "role_kind": "ADDITIVE_CHILD",
        },
        {
            "matchers": [_matcher(_CONTEXTUAL_FOREIGN_ALIASES, "DEFERRED_LC_PRE_2024_GROUP")],
            "presence": "OPTIONAL",
            "role": "DEFERRED_LC_FOREIGN",
            "role_kind": "ADDITIVE_CHILD",
        },
        {
            "matchers": [_matcher(("Tổng cộng", "Tổng"), None)],
            "presence": "OPTIONAL",
            "role": "EXPLICIT_GRAND_TOTAL",
            "role_kind": "TOTAL",
        },
    ],
    "family_id": FAMILY_ID,
    "format_version": TOPOLOGY_SPEC_FORMAT_VERSION,
    "hard_negative_aliases": [
        "Phân tích rủi ro tiền tệ",
        "Rủi ro tiền tệ",
        "Phân tích rủi ro lãi suất",
        "Rủi ro lãi suất",
        "Tiền gửi tại và cho vay các tổ chức tín dụng khác",
        "Tiền gửi và cho vay các tổ chức tín dụng khác",
    ],
    "limits": {
        "max_cluster_span_lines": 80,
        "max_continuation_pages": 1,
        "max_label_line_span": 3,
    },
    "parent": {
        "aliases": list(_BRANCH_ALIASES),
        "resolution_mode": "EXPLICIT_ONLY",
        "role": "LOAN_CURRENCY_BRANCH",
    },
    "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
    "required_role_combinations": [["VND_LOANS", "FOREIGN_CURRENCY_AND_GOLD_LOANS"]],
    "structural_reset_aliases": [
        "Phân tích dư nợ theo thời gian",
        "Phân tích dư nợ theo thời hạn",
        "Phân tích chất lượng dư nợ cho vay",
        "Phân tích chất lượng nợ cho vay",
        "Theo ngành nghề kinh doanh",
        "Theo ngành kinh tế",
        "Phân tích dư nợ theo ngành nghề kinh doanh",
        "Phân tích dư nợ theo ngành kinh tế",
        "Theo đối tượng khách hàng",
        "Theo loại hình doanh nghiệp",
        "Phân tích dư nợ theo đối tượng khách hàng",
        "Phân tích dư nợ theo loại hình doanh nghiệp",
        "Dự phòng rủi ro cho vay khách hàng",
    ],
}


# The source-only deferred-LC population is retained for accounting closure,
# but it is deliberately outside the two mapping-eligible roles.
LOAN_CURRENCY_HIERARCHY_SPEC_V2 = {
    "equations": [
        {
            "component_role_alternatives": [
                {
                    "component_roles": [
                        "VND_LOANS",
                        "FOREIGN_CURRENCY_AND_GOLD_LOANS",
                    ],
                    "coverage_policy": "EXHAUSTIVE_COMPONENT_SET",
                    "minimum_component_count": 2,
                }
            ],
            "result_role": "CORE_TOTAL_GROUP",
            "trailing_result_policy": "CORROBORATE_UNIQUE_MATCH_IF_PRESENT",
            "visible_result_roles": ["CORE_TOTAL_GROUP"],
        },
        {
            "component_role_alternatives": [
                {
                    "component_roles": ["DEFERRED_LC_VND", "DEFERRED_LC_FOREIGN"],
                    "coverage_policy": "EXHAUSTIVE_COMPONENT_SET",
                    "minimum_component_count": 2,
                }
            ],
            "result_role": "DEFERRED_LC_PRE_2024_GROUP",
            "trailing_result_policy": "IGNORE",
            "visible_result_roles": ["DEFERRED_LC_PRE_2024_GROUP"],
        },
        {
            "component_role_alternatives": [
                {
                    "component_roles": [
                        "CORE_TOTAL_GROUP",
                        "DEFERRED_LC_PRE_2024_GROUP",
                    ],
                    "coverage_policy": "EXHAUSTIVE_COMPONENT_SET",
                    "minimum_component_count": 2,
                }
            ],
            "result_role": "LOAN_CURRENCY_BRANCH",
            "trailing_result_policy": "CORROBORATE_UNIQUE_MATCH_IF_PRESENT",
            "visible_result_roles": ["EXPLICIT_GRAND_TOTAL"],
        },
    ],
    "family_id": FAMILY_ID,
    "format_version": HIERARCHY_SPEC_FORMAT_VERSION,
}


LOAN_CURRENCY_EVALUATION_SPEC_V2 = {
    "closure_policy": "HIERARCHICAL_RECURSIVE_CORROBORATE_OR_DERIVE",
    "expected_lane_unit_kinds": ["MONEY", "MONEY"],
    "family_id": FAMILY_ID,
    "format_version": "ACCOUNTING_FAMILY_EVALUATION_SPEC_V3",
    "hierarchical_closure_spec": LOAN_CURRENCY_HIERARCHY_SPEC_V2,
    "period_semantics": "BALANCE_COMPARATIVE",
}


class LoanCurrencyVariantGraphV2Error(ValueError):
    """The complete-document currency topology or exact replay drifted."""


def build_loan_currency_topology_scan_v2(document_pages: Any) -> dict[str, Any]:
    """Enumerate the currency family from a complete semantic document."""

    try:
        return build_accounting_family_topology_scan_v1(
            document_pages, LOAN_CURRENCY_TOPOLOGY_SPEC_V2
        )
    except AccountingFamilyTopologyV1Error as exc:
        raise LoanCurrencyVariantGraphV2Error(
            "loan-currency complete-document topology input drifted"
        ) from exc


def validate_loan_currency_topology_scan_replay_v2(
    value: Any, document_pages: Any
) -> dict[str, Any]:
    """Rebuild the complete-document topology and require typed equality."""

    try:
        return validate_accounting_family_topology_scan_replay_v1(
            value, document_pages, LOAN_CURRENCY_TOPOLOGY_SPEC_V2
        )
    except AccountingFamilyTopologyV1Error as exc:
        raise LoanCurrencyVariantGraphV2Error(
            "loan-currency topology scan does not replay exactly"
        ) from exc
