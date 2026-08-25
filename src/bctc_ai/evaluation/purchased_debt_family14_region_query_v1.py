"""Declarative region-first retrieval and topology policy for Family 14.

Family 14 is the purchased-debt balance/detail disclosure rooted at live TM
node 800.  This adapter contributes only bank-blind source vocabulary and a
bounded shortlist policy.  Authenticated OCR access, page selection, fallback,
reset handling, topology enumeration, and exact replay remain in the shared
engines.

An explicit owner plus the VND-purchase, provision, and principal roles is the
only complete topology.  Foreign-currency and interest rows are optional.
Distinct child-role rescue vocabulary is retained for a later owner-local,
reset-fenced oracle, but it is not an active retrieval seed in this Step-A
adapter.  Nothing here can prove presence, absence, numbers, schema identity,
mapping, or export eligibility.
"""

from __future__ import annotations

import hashlib
import re
import stat
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_clone_v1, same_typed_json_v1

__all__ = [
    "CLAIM_BOUNDARY",
    "FAMILY_ID",
    "PURCHASED_DEBT_FAMILY14_REGION_QUERY_SPEC_V2",
    "PURCHASED_DEBT_FAMILY14_REGION_QUERY_TRUST_CLOSURE_V1",
    "RECOVERY_STATUS_V1",
    "PurchasedDebtFamily14RegionQueryV1Error",
    "build_purchased_debt_family14_region_query_spec_v2",
    "build_purchased_debt_family14_schema_role_declaration_v1",
    "build_purchased_debt_family14_topology_scan_v1",
    "build_purchased_debt_family14_topology_spec_v1",
    "validate_purchased_debt_family14_topology_replay_v1",
]


FAMILY_ID = "PURCHASED_DEBT_ACTIVITY"
CLAIM_BOUNDARY = (
    "PURCHASED_DEBT_EXPLICIT_OWNER_AND_DISTINCT_CHILD_REGION_SHORTLIST_ONLY_"
    "BRANCHLESS_DISTINCT_ROLE_PAIR_DEFERRED_PENDING_OWNER_LOCAL_RESET_FENCED_ORACLE_"
    "EVERY_INDEXED_RESULT_REQUIRES_"
    "LATER_FULL_DOCUMENT_RESET_FENCED_TERMINAL_ORACLE_NO_ABSENCE_PERIOD_UNIT_NUMERIC_"
    "ARITHMETIC_SCHEMA_MAPPING_CANONICALIZATION_OR_EXPORT_AUTHORITY"
)
RECOVERY_STATUS_V1 = {
    "absence_authority": False,
    "branchless_distinct_role_pair": (
        "NOT_IMPLEMENTED_PENDING_OWNER_LOCAL_RESET_FENCED_ORACLE"
    ),
    "complete_family_retrieval_authority": False,
    "indexed_result_requirement": "LATER_FULL_DOCUMENT_RESET_FENCED_TERMINAL_ORACLE",
    "ownerless_distinctive_rescue_scope": "DECLARED_SAME_PAGE_ONLY_NOT_ACTIVE",
    "same_page_reset_interval_fencing": "NOT_IMPLEMENTED_BY_PAGE_LEVEL_QUERY_SHORTLIST",
    "shortlist_authority": True,
}

_QUERY_FORMAT = "FAMILY_FIRST_REGION_QUERY_SPEC_V2"
_TOPOLOGY_FORMAT = "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3"
_ADAPTER_PATH = Path("src/bctc_ai/evaluation/purchased_debt_family14_region_query_v1.py")
_ID_FRAGMENT = re.compile(r"[^A-Z0-9]+")

PURCHASED_DEBT_FAMILY14_REGION_QUERY_TRUST_CLOSURE_V1 = {
    "anchor_normalization_engine_ref": {
        "path": "src/bctc_ai/evaluation/accounting_variant_graph_engine_v1.py",
        "sha256": "6fbd518a09418278e273b0a81eed4db98b013dcb70bcbdf31e81bf9b47058b50",
        "size_bytes": 36_599,
    },
    "shared_region_retrieval_engine_ref": {
        "path": "src/bctc_ai/evaluation/family_first_region_retrieval_v1.py",
        "sha256": "01a4d4a676a25e03eb4fe1733f159ceafbdacad9be6d6ed1196572528e1fae20",
        "size_bytes": 105_116,
    },
    "shared_topology_engine_ref": {
        "path": "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        "sha256": "a9b2787b42a0b49243365731dc1de0bd4ce547c43343b8a679a3410643ee8a12",
        "size_bytes": 75_614,
    },
}


class PurchasedDebtFamily14RegionQueryV1Error(ValueError):
    """The Family-14 declarative policy or literal trust closure drifted."""


def _error(message: str) -> PurchasedDebtFamily14RegionQueryV1Error:
    return PurchasedDebtFamily14RegionQueryV1Error(message)


_OWNER_SURFACES = [
    "Hoạt động mua nợ",
    "Hoạt động mua nợ (tiếp theo)",
]
_CORE_ROLE_SURFACES = {
    "INTEREST_DETAIL_ROW": [
        "Lãi của khoản nợ đã mua",
        "Lãi từ các khoản nợ đã mua",
        "Lãi của khoản nợ đã mua và chênh lệch giá mua nợ",
        "Lãi từ các khoản nợ đã mua và chênh lệch giá mua nợ",
    ],
    "PRINCIPAL_DETAIL_ROW": ["Nợ gốc đã mua"],
    "PROVISION_BALANCE_ROW": [
        "Dự phòng rủi ro",
        "Dự phòng chung",
        "Dự phòng rủi ro mua nợ",
        "Dự phòng rủi ro hoạt động mua nợ",
    ],
    "PURCHASE_FX_BALANCE_ROW": ["Mua nợ bằng ngoại tệ"],
    "PURCHASE_VND_BALANCE_ROW": ["Mua nợ bằng VND"],
}
# Reserved ownerless rescue vocabulary is narrower than explicit-owner
# topology.  Generic provision labels remain valid inside an explicit owner
# cluster, but are excluded here; the entire rescue set stays inactive until a
# reset-fenced owner-local oracle is integrated.
_OWNERLESS_RESCUE_ROLE_SURFACES = {
    "INTEREST_DETAIL_ROW": _CORE_ROLE_SURFACES["INTEREST_DETAIL_ROW"],
    "PRINCIPAL_DETAIL_ROW": _CORE_ROLE_SURFACES["PRINCIPAL_DETAIL_ROW"],
    "PROVISION_BALANCE_ROW": [
        "Dự phòng rủi ro mua nợ",
        "Dự phòng rủi ro hoạt động mua nợ",
    ],
    "PURCHASE_FX_BALANCE_ROW": _CORE_ROLE_SURFACES["PURCHASE_FX_BALANCE_ROW"],
    "PURCHASE_VND_BALANCE_ROW": _CORE_ROLE_SURFACES["PURCHASE_VND_BALANCE_ROW"],
}
_OPTIONAL_CHECK_SURFACES = {
    "HISTORICAL_ACQUISITION_CHECK": ["Giá trị khoản nợ tại thời điểm mua"],
    "PROVISION_MOVEMENT_CHECK": [
        "Biến động dự phòng rủi ro hoạt động mua nợ",
        "Thay đổi dự phòng rủi ro hoạt động mua nợ",
    ],
    "QUALITY_ANALYSIS_CHECK": [
        "Phân tích chất lượng hoạt động mua nợ",
        "Phân tích chất lượng các khoản nợ đã mua",
    ],
}
_HARD_NEGATIVE_SURFACES = [
    "Chi phí dự phòng rủi ro tín dụng",
    "Chi phí/(Hoàn nhập) dự phòng mua nợ",
    "Chính sách dự phòng rủi ro tín dụng",
    "Dự phòng rủi ro cho các khoản nợ đã mua",
    "Tăng, giảm các khoản cho vay khách hàng và mua nợ",
]
_STRUCTURAL_RESET_SURFACES = [
    *_HARD_NEGATIVE_SURFACES,
    "Biến động số dư dự phòng rủi ro cho vay khách hàng",
    "Cho vay khách hàng",
    "Chứng khoán đầu tư",
    "Chứng khoán đầu tư giữ đến ngày đáo hạn",
    "Chứng khoán đầu tư sẵn sàng để bán",
    "Dự phòng rủi ro cho vay khách hàng",
    "Tiền gửi của khách hàng",
]


def _child(role: str, aliases: Sequence[str], role_kind: str) -> dict[str, Any]:
    return {
        "matchers": [{"aliases": list(aliases), "within_role": None}],
        "presence": "OPTIONAL",
        "role": role,
        "role_kind": role_kind,
    }


_TOPOLOGY_SPEC = {
    "children": [
        *[
            _child(role, aliases, "NONADDITIVE_CHILD")
            for role, aliases in _CORE_ROLE_SURFACES.items()
        ],
        *[
            _child(role, aliases, "NONADDITIVE_CHILD")
            for role, aliases in _OPTIONAL_CHECK_SURFACES.items()
        ],
    ],
    "family_id": FAMILY_ID,
    "format_version": _TOPOLOGY_FORMAT,
    "hard_negative_aliases": _HARD_NEGATIVE_SURFACES,
    "limits": {
        "max_cluster_span_lines": 96,
        "max_continuation_pages": 1,
        "max_label_line_span": 3,
    },
    "parent": {
        "aliases": _OWNER_SURFACES,
        "resolution_mode": "EXPLICIT_ONLY",
        "role": "PURCHASED_DEBT_OWNER",
    },
    "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
    "required_role_combinations": [
        ["PURCHASE_VND_BALANCE_ROW", "PROVISION_BALANCE_ROW", "PRINCIPAL_DETAIL_ROW"]
    ],
    "structural_reset_aliases": _STRUCTURAL_RESET_SURFACES,
}

_SCHEMA_ROLE_DECLARATION = {
    "authority": {
        "mapping_authority": False,
        "schema_binding_authority": False,
        "source_row_assignment_authority": False,
    },
    "claim_boundary": "DIAGNOSTIC_CURRENT_LIVE_ROLE_ID_AND_ORDER_RETENTION_ONLY",
    "next_family": {"display_order": 268, "report_norm_id": 804},
    "roles": {
        "INTEREST_DETAIL_ROW": {"display_order": 267, "report_norm_id": 5739},
        "PRINCIPAL_DETAIL_ROW": {"display_order": 266, "report_norm_id": 5738},
        "PROVISION_BALANCE_ROW": {"display_order": 265, "report_norm_id": 803},
        "PURCHASE_FX_BALANCE_ROW": {"display_order": 264, "report_norm_id": 802},
        "PURCHASE_VND_BALANCE_ROW": {"display_order": 263, "report_norm_id": 801},
    },
    "root": {"display_order": 262, "report_norm_id": 800},
}


def build_purchased_debt_family14_topology_spec_v1() -> dict[str, Any]:
    """Return the schema-free shared-V3 source topology policy."""

    return canonical_clone_v1(_TOPOLOGY_SPEC)


def build_purchased_debt_family14_schema_role_declaration_v1() -> dict[str, Any]:
    """Return diagnostic current IDs/order; this cannot bind source rows."""

    return canonical_clone_v1(_SCHEMA_ROLE_DECLARATION)


def build_purchased_debt_family14_topology_scan_v1(pages: Any) -> dict[str, Any]:
    """Build one shared-engine topology proposal without terminal authority."""

    from bctc_ai.evaluation.accounting_family_topology_v1 import (
        build_accounting_family_topology_scan_v1,
    )

    return build_accounting_family_topology_scan_v1(
        pages, build_purchased_debt_family14_topology_spec_v1()
    )


def validate_purchased_debt_family14_topology_replay_v1(
    value: Any, pages: Any
) -> dict[str, Any]:
    """Exact-replay a Family-14 topology proposal through the shared engine."""

    from bctc_ai.evaluation.accounting_family_topology_v1 import (
        validate_accounting_family_topology_scan_replay_v1,
    )

    return validate_accounting_family_topology_scan_replay_v1(
        value, pages, build_purchased_debt_family14_topology_spec_v1()
    )


def _stable_bytes(path: Path, label: str) -> bytes:
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise _error(f"Family-14 {label} is not one regular nofollow file")
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise _error(f"Family-14 {label} cannot be read stably") from exc
    identity = lambda item: (  # noqa: E731 - compact exact inode identity
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_size,
        item.st_mtime_ns,
    )
    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise _error(f"Family-14 {label} changed during stable read")
    return payload


def _content_ref(project_root: Path, relative: Path, label: str) -> dict[str, Any]:
    payload = _stable_bytes(project_root / relative, label)
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _verified_trust_closure(project_root: Path) -> None:
    observed = {
        name: _content_ref(project_root, Path(reference["path"]), name.replace("_", " "))
        for name, reference in sorted(PURCHASED_DEBT_FAMILY14_REGION_QUERY_TRUST_CLOSURE_V1.items())
    }
    if not same_typed_json_v1(observed, PURCHASED_DEBT_FAMILY14_REGION_QUERY_TRUST_CLOSURE_V1):
        raise _error("Family-14 query trust closure drifted")


def _surface(value: str) -> str:
    return unicodedata.normalize("NFC", " ".join(value.split()))


def _anchor_id(prefix: str, ordinal: int) -> str:
    return f"{_ID_FRAGMENT.sub('_', prefix.upper()).strip('_')}_{ordinal:02d}"


def _anchor(anchor_id: str, surface: str, role: str) -> dict[str, Any]:
    surface = _surface(surface)
    return {
        "anchor_id": anchor_id,
        "canonical_alias_id": anchor_id + "_CANONICAL",
        "fts_probes": [normalize_vietnamese_anchor_v1(surface)],
        "max_edit_distance": 0,
        "role": role,
        "surface": surface,
        "verified_historical_variants": [],
    }


def _add_anchors(
    anchors: list[dict[str, Any]], prefix: str, surfaces: Sequence[str], role: str
) -> list[str]:
    ids = []
    for ordinal, surface in enumerate(surfaces, 1):
        anchor_id = _anchor_id(prefix, ordinal)
        ids.append(anchor_id)
        anchors.append(_anchor(anchor_id, surface, role))
    return ids


def _query_spec(project_root: Path) -> dict[str, Any]:
    _verified_trust_closure(project_root)
    anchors: list[dict[str, Any]] = []
    owner_ids = _add_anchors(anchors, "OWNER_PURCHASED_DEBT", _OWNER_SURFACES, "OWNER")
    target_ids_by_role = {
        role: _add_anchors(anchors, f"TARGET_{role}", surfaces, "TARGET")
        for role, surfaces in sorted({**_CORE_ROLE_SURFACES, **_OPTIONAL_CHECK_SURFACES}.items())
    }
    _add_anchors(anchors, "HARD_NEGATIVE", _HARD_NEGATIVE_SURFACES, "HARD_NEGATIVE")

    distinctive_ids_by_role = {
        role: [
            target_ids_by_role[role][_CORE_ROLE_SURFACES[role].index(surface)]
            for surface in surfaces
        ]
        for role, surfaces in _OWNERLESS_RESCUE_ROLE_SURFACES.items()
    }
    target_ids = sorted(
        anchor_id for ids in distinctive_ids_by_role.values() for anchor_id in ids
    )
    return {
        "anchors": sorted(anchors, key=lambda item: item["anchor_id"]),
        "family_id": FAMILY_ID,
        "format_version": _QUERY_FORMAT,
        "local_required_groups": [
            {
                "anchor_ids": target_ids,
                "group_id": "DISTINCTIVE_PURCHASED_DEBT_TARGET_LOCAL",
                "mode": "ANY",
                "page_relation": "SAME_OR_ADJACENT_PAGE",
            }
        ],
        "max_hit_lines": 100_000,
        "max_selected_pages_per_document": 24,
        "neighbor_pages_after": 1,
        "neighbor_pages_before": 1,
        "seed_groups": sorted(
            [
                {
                    "anchor_ids": sorted(owner_ids),
                    "group_id": "EXPLICIT_PURCHASED_DEBT_OWNER",
                    "mode": "ANY",
                    "page_relation": "SAME_OR_ADJACENT_PAGE",
                    "priority": 1,
                },
            ],
            key=lambda item: item["group_id"],
        ),
        "semantic_assignment_adapter_ref": _content_ref(project_root, _ADAPTER_PATH, "query adapter"),
        "structural_reset_fragments": sorted(set(map(_surface, _STRUCTURAL_RESET_SURFACES))),
        "structural_reset_max_line_ordinal": 3,
        "window_line_span": 1,
        "zero_hit_policy": "FULL_DOCUMENT_FALLBACK",
    }


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
PURCHASED_DEBT_FAMILY14_REGION_QUERY_SPEC_V2 = _query_spec(_PROJECT_ROOT)


def build_purchased_debt_family14_region_query_spec_v2(project_root: str | Path) -> dict[str, Any]:
    """Return the pinned shared-V2 Family-14 retrieval shortlist specification."""

    observed = _query_spec(Path(project_root).resolve())
    if not same_typed_json_v1(observed, PURCHASED_DEBT_FAMILY14_REGION_QUERY_SPEC_V2):
        raise _error("Family-14 query differs from its loaded trust closure")
    from bctc_ai.evaluation.family_first_region_retrieval_v1 import (
        validate_family_first_region_query_spec_v2,
    )

    return validate_family_first_region_query_spec_v2(observed)
