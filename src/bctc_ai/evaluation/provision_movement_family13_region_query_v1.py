"""Declarative topology and region-first shortlist policy for Family 13.

Family 13 is the customer-loan provision movement roll-forward rooted at
report-normalization node 783.  This adapter contains only bank-blind source
vocabulary and bounded retrieval policy.  The shared retrieval engine owns
authenticated OCR access, reset-fenced page selection, complete-document
fallback, and receipt replay.  The shared topology engine owns structural
proposal replay.

Neither artifact emitted here has absence, period, unit, numeric, arithmetic,
schema-binding, mapping, or export authority.  In particular, movement rows
are temporal roles rather than additive children.  The diagnostic schema-role
declaration preserves the otherwise easy-to-drop decrease leaves 789 and 797,
but cannot bind any source row to them.
"""

from __future__ import annotations

import hashlib
import stat
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    same_typed_json_v1,
)

__all__ = [
    "CLAIM_BOUNDARY",
    "FAMILY_ID",
    "PROVISION_MOVEMENT_FAMILY13_REGION_QUERY_SPEC_V2",
    "PROVISION_MOVEMENT_FAMILY13_REGION_QUERY_TRUST_CLOSURE_V1",
    "RECOVERY_STATUS_V1",
    "ProvisionMovementFamily13RegionQueryV1Error",
    "build_provision_movement_family13_region_query_spec_v2",
    "build_provision_movement_family13_schema_role_declaration_v1",
    "build_provision_movement_family13_topology_spec_v1",
]


FAMILY_ID = "PROVISION_MOVEMENT_ROLLFORWARD"
CLAIM_BOUNDARY = (
    "EXACT_PRIMARY_CUSTOMER_LOAN_PROVISION_MOVEMENT_OWNER_REGION_SHORTLIST_ONLY_"
    "ANY_INDEXED_RESULT_REQUIRES_FULL_DOCUMENT_RESET_FENCED_TOPOLOGY_AND_TERMINAL_ORACLE_"
    "NO_COMPLETE_FAMILY_RETRIEVAL_ABSENCE_NUMERIC_ARITHMETIC_UNIT_SCHEMA_MAPPING_"
    "OR_EXPORT_AUTHORITY"
)
RECOVERY_STATUS_V1 = {
    "absence_authority": False,
    "branchless_recovery": "NOT_IMPLEMENTED_PENDING_RESET_FENCED_INTERVAL_PRIMITIVE",
    "complete_family_retrieval_authority": False,
    "indexed_result_requirement": "FULL_DOCUMENT_RESET_FENCED_TOPOLOGY_AND_TERMINAL_ORACLE",
    "same_page_reset_interval_fencing": "SAME_PAGE_RESET_INTERVAL_FENCING_NOT_IMPLEMENTED",
    "secondary_owner_recovery": "NOT_IMPLEMENTED_PENDING_RESET_FENCED_INTERVAL_PRIMITIVE",
    "shortlist_authority": True,
}
_QUERY_FORMAT = "FAMILY_FIRST_REGION_QUERY_SPEC_V2"
_TOPOLOGY_FORMAT = "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3"
_ADAPTER_PATH = Path("src/bctc_ai/evaluation/provision_movement_family13_region_query_v1.py")

# Literal pins make shared-engine drift an explicit review event.  The query
# additionally binds this adapter's exact bytes through its adapter reference.
PROVISION_MOVEMENT_FAMILY13_REGION_QUERY_TRUST_CLOSURE_V1 = {
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
        "sha256": "f3e8becbeda665740110773921135da7516346184e47572e9ef04b098af894f1",
        "size_bytes": 76_058,
    },
}


class ProvisionMovementFamily13RegionQueryV1Error(ValueError):
    """The Family-13 declarative policy or literal trust closure drifted."""


def _error(message: str) -> ProvisionMovementFamily13RegionQueryV1Error:
    return ProvisionMovementFamily13RegionQueryV1Error(message)


_PRIMARY_OWNER_SURFACES = [
    "Dự phòng rủi ro cho vay khách hàng",
    "Biến động số dư dự phòng rủi ro cho vay khách hàng",
    "Biến động số dư dự phòng rủi ro cho vay KH",
]
_CORE_ROLE_SURFACES = {
    "CLOSING": [
        "Số dư cuối kỳ",
        "Số dư cuối năm",
        "Số dư dự phòng cuối kỳ",
        "Số dư tại ngày 31 tháng 12",
    ],
    "OPENING": [
        "Số dư đầu kỳ",
        "Số dư đầu năm",
        "Số dư dự phòng đầu kỳ",
        "Số dư tại ngày 1 tháng 1",
    ],
    "PROVISION_OR_REVERSAL": [
        "(Hoàn nhập)/trích lập dự phòng trong kỳ",
        "(Hoàn nhập)/trích lập dự phòng trong năm",
        "Trích lập/(Hoàn nhập) dự phòng trong kỳ",
        "Trích lập/(Hoàn nhập) dự phòng trong năm",
        "Trích lập dự phòng trong kỳ",
        "Trích lập dự phòng trong năm",
        "Trích lập trong kỳ",
        "Trích lập trong năm",
    ],
}
_OPTIONAL_ROLE_SURFACES = {
    "DECREASE_MOVEMENT_ROW": [
        "Giảm dự phòng rủi ro tín dụng trong kỳ",
        "Giảm dự phòng rủi ro tín dụng trong năm",
    ],
    "FOREIGN_EXCHANGE_MOVEMENT_ROW": [
        "Chênh lệch tỷ giá",
        "Chênh lệch tỷ giá hối đoái",
    ],
    "OTHER_MOVEMENT_ROW": ["Điều chỉnh khác", "Biến động khác", "Khác"],
    "USE_MOVEMENT_ROW": [
        "Sử dụng dự phòng trong kỳ",
        "Sử dụng dự phòng trong năm",
        "Sử dụng dự phòng để xử lý các khoản nợ",
        "Sử dụng dự phòng rủi ro tín dụng trong kỳ",
        "Sử dụng dự phòng rủi ro tín dụng trong năm",
    ],
}
_LANE_SURFACES = {
    "GENERAL_PROVISION_LANE": ["Dự phòng chung"],
    "MARGIN_ADVANCE_PROVISION_LANE": [
        "Dự phòng cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán",
        "Dự phòng rủi ro cho vay giao dịch ký quỹ và ứng trước khách hàng",
    ],
    "SPECIFIC_PROVISION_LANE": ["Dự phòng cụ thể"],
}
_HARD_NEGATIVE_SURFACES = [
    "Chi phí dự phòng rủi ro tín dụng",
    "Chính sách dự phòng rủi ro tín dụng",
    "Chứng khoán đầu tư",
    "Dự phòng giảm giá chứng khoán",
    "Dự phòng rủi ro cho các khoản nợ đã mua",
    "Hoạt động mua nợ",
    "Phân loại nợ và trích lập dự phòng",
    "Thay đổi dự phòng rủi ro tín dụng chứng khoán đầu tư",
]
_STRUCTURAL_RESET_SURFACES = [
    *_HARD_NEGATIVE_SURFACES,
    "Phân tích chất lượng nợ cho vay",
    "Phân tích dư nợ cho vay theo ngành nghề kinh doanh",
    "Phân tích theo loại hình doanh nghiệp",
]


def _movement_child(role: str, aliases: Sequence[str]) -> dict[str, Any]:
    return {
        "matchers": [{"aliases": list(aliases), "within_role": None}],
        "presence": "OPTIONAL",
        "role": role,
        "role_kind": "NONADDITIVE_CHILD",
    }


_TOPOLOGY_SPEC = {
    "children": [
        *[
            {
                "matchers": [{"aliases": aliases, "within_role": None}],
                "presence": "OPTIONAL",
                "role": role,
                "role_kind": "STRUCTURAL_GROUP",
            }
            for role, aliases in _LANE_SURFACES.items()
        ],
        _movement_child("OPENING_BALANCE_ROW", _CORE_ROLE_SURFACES["OPENING"]),
        _movement_child(
            "PROVISION_OR_REVERSAL_ROW",
            _CORE_ROLE_SURFACES["PROVISION_OR_REVERSAL"],
        ),
        *[_movement_child(role, aliases) for role, aliases in _OPTIONAL_ROLE_SURFACES.items()],
        _movement_child("CLOSING_BALANCE_ROW", _CORE_ROLE_SURFACES["CLOSING"]),
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
        "aliases": _PRIMARY_OWNER_SURFACES,
        "resolution_mode": "EXPLICIT_ONLY",
        "role": "CUSTOMER_LOAN_PROVISION_MOVEMENT_OWNER",
    },
    "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
    "required_role_combinations": [
        ["OPENING_BALANCE_ROW", "PROVISION_OR_REVERSAL_ROW", "CLOSING_BALANCE_ROW"]
    ],
    "structural_reset_aliases": _STRUCTURAL_RESET_SURFACES,
}

_SCHEMA_ROLE_DECLARATION = {
    "authority": {
        "mapping_authority": False,
        "schema_binding_authority": False,
        "source_row_assignment_authority": False,
    },
    "claim_boundary": "DIAGNOSTIC_LIVE_ROLE_ID_RETENTION_ONLY",
    "lanes": {
        "GENERAL": {
            "CLOSING": 791,
            "DECREASE": 789,
            "FOREIGN_EXCHANGE": 788,
            "OPENING": 785,
            "OTHER": 790,
            "PARENT": 784,
            "PROVISION_OR_REVERSAL": 786,
            "USE": 787,
        },
        "MARGIN_ADVANCE": {
            "CLOSING": 6065,
            "OPENING": 6062,
            "PARENT": 6061,
            "PROVISION_OR_REVERSAL": 6063,
            "USE": 6064,
        },
        "SPECIFIC": {
            "CLOSING": 799,
            "DECREASE": 797,
            "FOREIGN_EXCHANGE": 796,
            "OPENING": 793,
            "OTHER": 798,
            "PARENT": 792,
            "PROVISION_OR_REVERSAL": 794,
            "USE": 795,
        },
    },
    "root_report_norm_id": 783,
}


def build_provision_movement_family13_topology_spec_v1() -> dict[str, Any]:
    """Return an isolated source-structural V3 policy without arithmetic."""

    return canonical_clone_v1(_TOPOLOGY_SPEC)


def build_provision_movement_family13_schema_role_declaration_v1() -> dict[str, Any]:
    """Return diagnostic live IDs; this declaration cannot bind source rows."""

    return canonical_clone_v1(_SCHEMA_ROLE_DECLARATION)


def _stable_bytes(path: Path, label: str) -> bytes:
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            raise _error(f"Family-13 {label} is not one regular nofollow file")
        payload = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise _error(f"Family-13 {label} cannot be read stably") from exc
    identity = lambda value: (  # noqa: E731 - compact exact inode identity
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
    )
    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise _error(f"Family-13 {label} changed during stable read")
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
        for name, reference in sorted(
            PROVISION_MOVEMENT_FAMILY13_REGION_QUERY_TRUST_CLOSURE_V1.items()
        )
    }
    if not same_typed_json_v1(
        observed,
        PROVISION_MOVEMENT_FAMILY13_REGION_QUERY_TRUST_CLOSURE_V1,
    ):
        raise _error("Family-13 query trust closure drifted")


def _surface(value: str) -> str:
    return unicodedata.normalize("NFC", " ".join(value.split()))


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
    anchors: list[dict[str, Any]],
    prefix: str,
    surfaces: Sequence[str],
    role: str,
) -> list[str]:
    ids = []
    for ordinal, surface in enumerate(surfaces, 1):
        anchor_id = f"{prefix}_{ordinal:02d}"
        ids.append(anchor_id)
        anchors.append(_anchor(anchor_id, surface, role))
    return ids


def _query_spec(project_root: Path) -> dict[str, Any]:
    _verified_trust_closure(project_root)
    anchors: list[dict[str, Any]] = []
    primary_ids = _add_anchors(anchors, "PRIMARY_OWNER", _PRIMARY_OWNER_SURFACES, "OWNER")
    core_ids = {
        role: _add_anchors(anchors, f"CORE_{role}", surfaces, "TARGET")
        for role, surfaces in sorted(_CORE_ROLE_SURFACES.items())
    }
    _add_anchors(anchors, "HARD_NEGATIVE", _HARD_NEGATIVE_SURFACES, "HARD_NEGATIVE")

    all_core_ids = sorted(anchor_id for ids in core_ids.values() for anchor_id in ids)
    return {
        "anchors": sorted(anchors, key=lambda item: item["anchor_id"]),
        "family_id": FAMILY_ID,
        "format_version": _QUERY_FORMAT,
        "local_required_groups": [
            {
                "anchor_ids": all_core_ids,
                "group_id": "CORE_MOVEMENT_ROLE_LOCAL",
                "mode": "ANY",
                "page_relation": "SAME_OR_ADJACENT_PAGE",
            }
        ],
        "max_hit_lines": 100_000,
        "max_selected_pages_per_document": 24,
        "neighbor_pages_after": 1,
        "neighbor_pages_before": 2,
        "seed_groups": [
            {
                "anchor_ids": sorted(primary_ids),
                "group_id": "PRIMARY_PROVISION_MOVEMENT_OWNER",
                "mode": "ANY",
                "page_relation": "SAME_PAGE",
                "priority": 1,
            }
        ],
        "semantic_assignment_adapter_ref": _content_ref(
            project_root, _ADAPTER_PATH, "query adapter"
        ),
        "structural_reset_fragments": sorted(set(map(_surface, _STRUCTURAL_RESET_SURFACES))),
        "structural_reset_max_line_ordinal": 3,
        "window_line_span": 1,
        "zero_hit_policy": "FULL_DOCUMENT_FALLBACK",
    }


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROVISION_MOVEMENT_FAMILY13_REGION_QUERY_SPEC_V2 = _query_spec(_PROJECT_ROOT)


def build_provision_movement_family13_region_query_spec_v2(
    project_root: str | Path,
) -> dict[str, Any]:
    """Return the pinned V2 Family-13 retrieval shortlist specification."""

    observed = _query_spec(Path(project_root).resolve())
    if not same_typed_json_v1(
        observed,
        PROVISION_MOVEMENT_FAMILY13_REGION_QUERY_SPEC_V2,
    ):
        raise _error("Family-13 query differs from its loaded trust closure")
    from bctc_ai.evaluation.family_first_region_retrieval_v1 import (
        validate_family_first_region_query_spec_v2,
    )

    return validate_family_first_region_query_spec_v2(observed)
