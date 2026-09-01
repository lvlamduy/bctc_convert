#!/usr/bin/env python3
"""Run Family54 consolidated segment reports over one authenticated JSON corpus."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sqlite3
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bctc_ai.evaluation.gemini_json_equity_matrix_accounting_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_equity_matrix_region_query_receipt_v1,
    evaluate_gemini_json_equity_matrix_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (  # noqa: E402
    gemini_accounting_family_store_summary_v1,
    ingest_gemini_accounting_family_sweep_v1,
    load_gemini_accounting_family_sweep_v1,
    record_gemini_accounting_family_export_v1,
    resolved_gemini_family_region_repair_overlay_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_family_effective_page_frontier_v1 import (  # noqa: E402
    apply_gemini_family_effective_page_frontier_v1,
    effective_page_frontier_stages_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    page_json_region_repair_lineages_v1,
    query_selected_equity_matrix_family_regions_v1,
    validate_selected_equity_matrix_family_candidate_replays_v1,
    validate_selected_equity_matrix_family_query_evidence_v1,
)
from scripts.experiments.run_gemini_json_equity_matrix_accounting_family_v1 import (  # noqa: E402
    _authenticated_sqlite_snapshot,
    _content_ref,
    _file_ref,
    _json,
    _load_selected_pages_by_document,
    _selected_page_axis,
    _trials,
    _write_once,
)


class RunGeminiJsonSegmentReportAccountingFamilyV1Error(RuntimeError):
    """The Family54 source, comparator, release, or persistence boundary drifted."""


def _error(message: str) -> RunGeminiJsonSegmentReportAccountingFamilyV1Error:
    return RunGeminiJsonSegmentReportAccountingFamilyV1Error(message)


FAMILY_ID = "CONSOLIDATED_SEGMENT_REPORT"
AUDIT_FORMAT_VERSION = "GEMINI_JSON_SEGMENT_REPORT_EXPERIMENTAL_AUDIT_V1"
AUDIT_AXIS_NAMES = {
    "accepted_clusters",
    "blank_cells",
    "component_regions",
    "document_dispositions",
    "equations",
    "historical_assignments",
    "historical_blank_cells",
    "historical_bounded_absences",
    "historical_documents",
    "historical_equations",
    "historical_open_source_items",
    "historical_source_only_equation_components",
    "historical_structures",
    "mapping_values",
    "mappings",
    "period_assignments",
    "query_dispositions",
    "source_only_cells",
    "table_receipts",
    "unresolved_documents",
}
PINNED_HISTORICAL_ORACLE = {
    "format_version": "ANNUAL_2025_CONSOLIDATED_SEGMENT_REPORT_8BANK_CODEX_VERIFIED_MAPPING_V1",
    "path": (
        "docs/experiments/"
        "E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json"
    ),
    "result_id": (
        "annual2025csr8bcv1:result:8395c0524c6b1345910d057fc8bca97aba732231d7379e7c7d0eccb645f79707"
    ),
    "sha256": "a5f05672ce4ba96142020645e072925be829ab3cff34fefc0c373527b813e416",
    "size_bytes": 451303,
}
PINNED_HISTORICAL_CORRIGENDUM = {
    "format_version": "ANNUAL_2025_CONSOLIDATED_SEGMENT_REPORT_E0161_CORRIGENDUM_V1",
    "path": (
        "docs/experiments/E-0179-annual-2025-consolidated-segment-report-e0161-corrigendum-v1.json"
    ),
    "result_id": ("e0179:result:27886c57fa294481460dcb65b7b219c0304c5f62c3c43459d79b95ebbfb9253b"),
    "sha256": "b290057eddf06d355065788748d35bed2c7f49b9db5f90a2f7d1741e9c707d50",
    "size_bytes": 34060,
}
PINNED_HISTORICAL_METRICS = {
    "accounting_equation_verified_count": 43,
    "blank_cell_preserved_count": 2,
    "detailed_business_report_absence_count": 2,
    "detailed_geographic_report_absence_count": 1,
    "document_count": 8,
    "document_unique_region_count": 8,
    "numeric_assignment_verified_count": 208,
    "related_party_family_processed_count": 0,
    "source_only_equation_component_count": 32,
    "source_only_open_item_count": 17,
    "structure_binding_verified_count": 73,
}
PINNED_HISTORICAL_CORRECTED_AXIS_COUNTS = {
    "historical_assignments": 205,
    "historical_blank_cells": 0,
    "historical_bounded_absences": 3,
    "historical_documents": 8,
    "historical_equations": 44,
    "historical_open_source_items": 18,
    "historical_source_only_equation_components": 30,
    "historical_structures": 73,
}

# Populate only from two byte-identical final-corpus EXPERIMENTAL runs.  Keeping this
# empty deliberately permits diagnostic EXPERIMENTAL runs while making OFFICIAL fail closed.
PINNED_RELEASE_PINS: dict[str, Any] = {
    "audit_id": "gjsrmeav1:audit:fd15242ea263b5f8dd29f9461bba7abb8e7a3a49ca854ce0b992a3c609756b51",
    "audit_metrics": {
        "blank_cell_count": 152,
        "component_region_count": 140,
        "equation_count": 1578,
        "historical_assignment_exact_count": 205,
        "historical_assignment_expected_count": 205,
        "historical_comparator_failure_count": 0,
        "historical_current_extra_count": 864,
        "historical_expected_axis_counts": {
            "historical_assignments": 205,
            "historical_blank_cells": 0,
            "historical_bounded_absences": 3,
            "historical_documents": 8,
            "historical_equations": 44,
            "historical_open_source_items": 18,
            "historical_source_only_equation_components": 30,
            "historical_structures": 73,
        },
        "historical_open_source_item_count": 18,
        "mapping_count": 1311,
        "mapping_value_count": 2283,
        "period_assignment_count": 8998,
        "query_unresolved_count": 0,
        "source_only_cell_count": 6860,
        "table_receipt_count": 140,
        "unresolved_document_count": 0,
    },
    "axis_counts": {
        "accepted_clusters": 45,
        "blank_cells": 152,
        "component_regions": 140,
        "document_dispositions": 140,
        "equations": 1578,
        "historical_assignments": 340,
        "historical_blank_cells": 23,
        "historical_bounded_absences": 3,
        "historical_documents": 8,
        "historical_equations": 312,
        "historical_open_source_items": 18,
        "historical_source_only_equation_components": 468,
        "historical_structures": 73,
        "mapping_values": 2283,
        "mappings": 1311,
        "period_assignments": 8998,
        "query_dispositions": 140,
        "source_only_cells": 6860,
        "table_receipts": 140,
        "unresolved_documents": 0,
    },
    "axis_sha256": {
        "accepted_clusters": "a8aff3c7801bb1a17f4cb726e7fd40fdac87b676875d17b230d47a84a1ba3dac",
        "blank_cells": "d4020cb6b3a047c86854e243e64f865d74113debca1052535f2a964424ee51a4",
        "component_regions": "99c1db1238957429d49a7edb82021614c2d1e2f47814d22cd4adc6fb68cc7ed3",
        "document_dispositions": "a57c41e6ff8751141cee0d4fbe31df2931c04ed9b03c5b41c00b480dd2018679",
        "equations": "ef430c16f9ca9d49c3128c0b98aba9762e8385d8a7eb4971e639356cefa2bdf0",
        "historical_assignments": "83e56186396560cb61c4cd1545eed7dd1a5af150ff4fe52b652f40e25542cc57",
        "historical_blank_cells": "8806b09e014d5b38e40a8f0bbff96456e83fee6cb737e7133503757843d237ae",
        "historical_bounded_absences": "9bf1146e64cf9026c9a465126c622a639b50758c412142c428509082f0700e70",
        "historical_documents": "a2aff2a4f9abb1fef314155fa65d67eb9b3605d9049b09e92e6c4509c26eeea8",
        "historical_equations": "cdb61fd5361eb906e4fcd81e310e86038b8744f25ac8677655b352df32c09ffe",
        "historical_open_source_items": "77353e5ed686fe5ad9c36134428e17b52c463f20baba39d1047838c6d8696622",
        "historical_source_only_equation_components": "6fc8389694dc86143306dc55c2c679e9f5dae6cbe9cd6b11ddfc391c9f890c5d",
        "historical_structures": "1bd9274ac19382620f0288c0d9500f14db0db0ed40ba5be856c900671d7e1300",
        "mapping_values": "f38c528844d2115aadb56c4f4a9e615a9d790f1162172a5c0c6719bb3bbf13d4",
        "mappings": "ee94f2443bc9ac27095bc5fbabd448e316638a9f44682dba968b17a63bdb69ce",
        "period_assignments": "8a0c5de638eaeb9659276435f1b9cf98c53939a3b8b2cf98fce44698b59d24b9",
        "query_dispositions": "457fc413b46bd8f7374f9857dff52124fc00eb5fa5b13b6cf4ed2b8fd508846c",
        "source_only_cells": "d146057ff0f0ef11b62f83b93dad12a617e3fe0fcabab9aaa0b083b67205d08b",
        "table_receipts": "360751eb57087c41e8efa76b82cbc2e4bf77f51dd6066108e61dc76fd29013af",
        "unresolved_documents": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    },
    "compiled_triplet_sha256": "7f7b28f0b59463eae35a397ddbeeb3b0d35ba36b58b45cac35a8f9c24fb834f1",
    "corpus_manifest_index_id": "gjfccmiv1:index:61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3",
    "embedded_spec_value_sha256": {
        "evaluation": "3857f929833cae2f2c1b2669dd85513d000fb7ebef17cc98dc5a6e5184ca1cdf",
        "schema_binding": "671e7787380c4037f896a5cde06fe38b76af75507c3e164eb0f3a7400a836f9d",
        "topology": "2ab0ad87f057f09d0cf86816334ac82ad57ed93dacf3cf9b677fc87c3ab086f0",
    },
    "historical_oracle_refs": [
        {
            "format_version": "ANNUAL_2025_CONSOLIDATED_SEGMENT_REPORT_8BANK_CODEX_VERIFIED_MAPPING_V1",
            "path": "docs/experiments/E-0161-annual-2025-consolidated-segment-report-8bank-codex-verified-mapping-v1.json",
            "result_id": "annual2025csr8bcv1:result:8395c0524c6b1345910d057fc8bca97aba732231d7379e7c7d0eccb645f79707",
            "sha256": "a5f05672ce4ba96142020645e072925be829ab3cff34fefc0c373527b813e416",
            "size_bytes": 451303,
        },
        {
            "format_version": "ANNUAL_2025_CONSOLIDATED_SEGMENT_REPORT_E0161_CORRIGENDUM_V1",
            "path": "docs/experiments/E-0179-annual-2025-consolidated-segment-report-e0161-corrigendum-v1.json",
            "result_id": "e0179:result:27886c57fa294481460dcb65b7b219c0304c5f62c3c43459d79b95ebbfb9253b",
            "sha256": "b290057eddf06d355065788748d35bed2c7f49b9db5f90a2f7d1741e9c707d50",
            "size_bytes": 34060,
        },
    ],
    "implementation_refs": [
        {
            "path": "scripts/experiments/run_gemini_json_segment_report_accounting_family_v1.py",
            "sha256": "aa6914ff3259016ada612311dd5202c7845bd7aa82ba90ffa2b45593e1c37a20",
            "size_bytes": 78255,
        },
        {
            "path": "scripts/experiments/run_gemini_json_equity_matrix_accounting_family_v1.py",
            "sha256": "e44d904e044d04e56a52ba23ab75697f064c4dd93183d086cd953b38ddd01c0f",
            "size_bytes": 52381,
        },
        {
            "path": "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
            "sha256": "7d7846e1a8b15379a1489fce01e1f59a88b9ec0aa7e5ea54e506280fa90758ae",
            "size_bytes": 82226,
        },
        {
            "path": "src/bctc_ai/evaluation/gemini_json_equity_matrix_accounting_family_v1.py",
            "sha256": "496ff40a312f351a585d8b66b0946fb1ae4109fae3110c7514a869d97f98d948",
            "size_bytes": 261061,
        },
        {
            "path": "src/bctc_ai/evaluation/gemini_json_segment_report_matrix_v1.py",
            "sha256": "a69f3a1d62dffad069aea6e0228b68c94871a1ae791ae17c724154e5a9ea3411",
            "size_bytes": 265862,
        },
        {
            "path": "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
            "sha256": "ffd5dbc44bc8159103b2ca7038d2ce9dba9d01aa003d1fe1ba2b64178fd594e0",
            "size_bytes": 185034,
        },
        {
            "path": "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
            "sha256": "4c87f7868640bb09a33418526ff7b14c9160230f88d9879c1918d8d2373bb071",
            "size_bytes": 65013,
        },
        {
            "path": "src/bctc_ai/storage/gemini_family_effective_page_frontier_v1.py",
            "sha256": "7eccf934d77a1c72411c555017e03c4b8173ff5b52faf9b19de48ea5d3f292a2",
            "size_bytes": 16770,
        },
        {
            "path": "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
            "sha256": "64702b1f97c08b0f599352d6fb0ce0ab3baa9e3c199327e52bc51e2093b6ed4d",
            "size_bytes": 299227,
        },
    ],
    "query_receipt": {
        "accepted_cluster_axis_sha256": "a8aff3c7801bb1a17f4cb726e7fd40fdac87b676875d17b230d47a84a1ba3dac",
        "accepted_cluster_count": 45,
        "accepted_fragment_count": 140,
        "candidate_disposition_axis_sha256": "457fc413b46bd8f7374f9857dff52124fc00eb5fa5b13b6cf4ed2b8fd508846c",
        "candidate_disposition_count": 140,
        "disposition_counts": {
            "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY": 95,
            "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY": 45,
            "UNRESOLVED_GEMINI_JSON_FAMILY": 0,
        },
        "query_policy_sha256": "5605330e68307b67bd70394ade226b263fdffd6ffb230b6eedc1c52a582d0a57",
        "selected_document_axis_sha256": "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c",
        "selected_document_count": 140,
        "selected_page_axis_sha256": "831f0a7e3189fee5ce0c138f46de54e0e8d064223ea6155f85ed2b05dd0527d1",
        "selected_page_count": 8947,
        "selected_page_json_frontier_sha256": "0b375a562b4df4016ef74dd49dc4d589edbae737fdd3db854986994f0079001b",
    },
    "selected_page_json_frontier_sha256": "0b375a562b4df4016ef74dd49dc4d589edbae737fdd3db854986994f0079001b",
    "spec_refs": {
        "evaluation": {
            "path": "config/families/tm-consolidated-segment-report-evaluation-v1.json",
            "sha256": "6c13339b81d7603ebf564cf9d5ae507725ef80d0869347d07b111e32c0a0b5e8",
            "size_bytes": 3498,
        },
        "schema_binding": {
            "path": "config/families/tm-consolidated-segment-report-schema-binding-v1.json",
            "sha256": "a4199fcf5c12dd006f4710d5a6c50113f1a92a6acb4a1f4a6866caa99781bd87",
            "size_bytes": 1411,
        },
        "topology": {
            "path": "config/families/tm-consolidated-segment-report-topology-v1.json",
            "sha256": "4a8e603aeea0bd7f355cd4ef3ff11c6bd69036148de0dad20bec0e14ff81cc69",
            "size_bytes": 2526,
        },
    },
    "sweep_id": "gjfafsv1:sweep:f64f58eb3c277afd6a587cfda71b53e81c8db4bf14ff03a46174eacf56d8ab2f",
    "sweep_metrics": {
        "document_count": 140,
        "mapping_count": 1311,
        "not_observed_count": 95,
        "ready_count": 45,
        "unresolved_count": 0,
    },
}


def _assert_disjoint_results_store(*, source_database: Path, results_database: Path) -> None:
    """Reject every pathname or inode alias between immutable input and mutable output."""

    if source_database.is_symlink() or not source_database.is_file():
        raise _error("Family54 source database is absent or not a regular non-symlink file")
    source_resolved = source_database.resolve(strict=True)
    # Resolve even a not-yet-created output through every existing/symlinked parent.
    # This closes lexical aliases before EXP is allowed to initialize a new store.
    results_resolved = results_database.resolve(strict=False)
    if results_resolved == source_resolved:
        raise _error("Family54 results store aliases the authenticated source database path")
    if not os.path.lexists(results_database):
        return
    try:
        source_stat = os.stat(source_database, follow_symlinks=True)
        results_stat = os.stat(results_database, follow_symlinks=True)
    except OSError as exc:
        raise _error("Family54 results store identity cannot be resolved safely") from exc
    if os.path.samefile(source_database, results_database) or (
        source_stat.st_dev,
        source_stat.st_ino,
    ) == (results_stat.st_dev, results_stat.st_ino):
        raise _error("Family54 results store aliases the authenticated source database inode")


def _canonical_sort(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    cloned = [canonical_clone_v1(item) for item in items]
    return sorted(cloned, key=canonical_json_bytes_v1)


def _historical_oracle() -> tuple[dict[str, Any], dict[str, Any]]:
    reference = canonical_clone_v1(PINNED_HISTORICAL_ORACLE)
    path = ROOT / reference["path"]
    value = _json(path)
    actual_ref = _file_ref(path, root=ROOT)
    if (
        actual_ref["sha256"] != reference["sha256"]
        or actual_ref["size_bytes"] != reference["size_bytes"]
        or value.get("format_version") != reference["format_version"]
        or value.get("result_id") != reference["result_id"]
        or not same_typed_json_v1(value.get("metrics"), PINNED_HISTORICAL_METRICS)
        or type(value.get("trials")) is not list
        or len(value["trials"]) != PINNED_HISTORICAL_METRICS["document_count"]
    ):
        raise _error("Family54 pinned E-0161 historical oracle drifted")
    return reference, value


def _historical_corrigendum() -> tuple[dict[str, Any], dict[str, Any]]:
    reference = canonical_clone_v1(PINNED_HISTORICAL_CORRIGENDUM)
    path = ROOT / reference["path"]
    value = _json(path)
    actual_ref = _file_ref(path, root=ROOT)
    material = {key: item for key, item in value.items() if key != "result_id"}
    operations = value.get("axis_operations")
    if (
        actual_ref["sha256"] != reference["sha256"]
        or actual_ref["size_bytes"] != reference["size_bytes"]
        or value.get("format_version") != reference["format_version"]
        or value.get("result_id") != reference["result_id"]
        or value.get("result_id") != "e0179:result:" + canonical_json_sha256_v1(material)
        or not same_typed_json_v1(value.get("base_oracle_ref"), PINNED_HISTORICAL_ORACLE)
        or type(operations) is not list
        or type(value.get("source_evidence")) is not list
        or type(value.get("metrics")) is not dict
    ):
        raise _error("Family54 pinned E-0179 historical corrigendum drifted")
    expected_fields = {
        "authority",
        "axis_operations",
        "base_oracle_ref",
        "claim_boundary",
        "format_version",
        "metrics",
        "result_id",
        "source_evidence",
        "state",
    }
    if set(value) != expected_fields:
        raise _error("Family54 E-0179 historical corrigendum schema drifted")
    allowed_axes = {
        "assignments",
        "blank_cells",
        "equations",
        "open_source_items",
        "source_only_components",
    }
    operation_counts: dict[tuple[str, str], int] = defaultdict(int)
    operation_receipts: set[str] = set()
    for operation in operations:
        if type(operation) is not dict:
            raise _error("Family54 E-0179 historical operation is invalid")
        operation_name = operation.get("operation")
        axis_name = operation.get("axis_name")
        expected_operation_fields = {
            "ADD_EXACT": {"after", "axis_name", "operation"},
            "REMOVE_EXACT": {"axis_name", "before", "operation"},
            "REPLACE_EXACT": {"after", "axis_name", "before", "operation"},
        }.get(operation_name)
        if (
            axis_name not in allowed_axes
            or expected_operation_fields is None
            or set(operation) != expected_operation_fields
            or ("before" in operation and type(operation["before"]) is not dict)
            or ("after" in operation and type(operation["after"]) is not dict)
        ):
            raise _error("Family54 E-0179 historical operation schema is invalid")
        receipt = canonical_json_sha256_v1(operation)
        if receipt in operation_receipts:
            raise _error("Family54 E-0179 historical operation is duplicated")
        operation_receipts.add(receipt)
        operation_counts[(str(axis_name), str(operation_name))] += 1
    expected_operation_counts = {
        ("assignments", "ADD_EXACT"): 2,
        ("assignments", "REMOVE_EXACT"): 5,
        ("assignments", "REPLACE_EXACT"): 4,
        ("blank_cells", "REMOVE_EXACT"): 2,
        ("equations", "REMOVE_EXACT"): 1,
        ("equations", "REPLACE_EXACT"): 12,
        ("open_source_items", "ADD_EXACT"): 1,
        ("source_only_components", "REMOVE_EXACT"): 2,
        ("source_only_components", "REPLACE_EXACT"): 3,
    }
    if (
        operation_counts != expected_operation_counts
        or len(value["source_evidence"]) != 5
        or not same_typed_json_v1(
            value["metrics"],
            {
                "corrected_axis_counts": PINNED_HISTORICAL_CORRECTED_AXIS_COUNTS,
                "operation_count": 32,
                "source_evidence_count": 5,
            },
        )
    ):
        raise _error("Family54 E-0179 historical corrigendum inventory drifted")
    return reference, value


def _apply_historical_corrigendum(
    *,
    expected: Mapping[str, Sequence[Mapping[str, Any]]],
    corrigendum: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    corrected = {
        name: [canonical_clone_v1(item) for item in axis] for name, axis in expected.items()
    }
    for operation in corrigendum["axis_operations"]:
        axis = corrected[operation["axis_name"]]
        operation_name = operation["operation"]
        if operation_name in {"REMOVE_EXACT", "REPLACE_EXACT"}:
            matches = [
                index
                for index, item in enumerate(axis)
                if same_typed_json_v1(item, operation["before"])
            ]
            if len(matches) != 1:
                raise _error("Family54 E-0179 historical operation target drifted")
            index = matches[0]
            if operation_name == "REMOVE_EXACT":
                axis.pop(index)
            else:
                axis[index] = canonical_clone_v1(operation["after"])
        else:
            if any(same_typed_json_v1(item, operation["after"]) for item in axis):
                raise _error("Family54 E-0179 historical addition already exists")
            axis.append(canonical_clone_v1(operation["after"]))
    corrected = {name: _canonical_sort(axis) for name, axis in corrected.items()}
    actual_counts = {
        "historical_assignments": len(corrected["assignments"]),
        "historical_blank_cells": len(corrected["blank_cells"]),
        "historical_bounded_absences": len(corrected["bounded_absences"]),
        "historical_documents": len(corrected["documents"]),
        "historical_equations": len(corrected["equations"]),
        "historical_open_source_items": len(corrected["open_source_items"]),
        "historical_source_only_equation_components": len(corrected["source_only_components"]),
        "historical_structures": len(corrected["structures"]),
    }
    if not same_typed_json_v1(actual_counts, PINNED_HISTORICAL_CORRECTED_AXIS_COUNTS):
        raise _error("Family54 E-0179 corrected historical axis inventory drifted")
    return corrected


def _candidate(trial: Mapping[str, Any]) -> dict[str, Any] | None:
    candidates = trial.get("candidates")
    return candidates[0] if type(candidates) is list and len(candidates) == 1 else None


def _trial_by_source(trials: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for trial in trials:
        source_sha256 = trial.get("source_sha256")
        if type(source_sha256) is not str or source_sha256 in result:
            raise _error("Family54 current trial source axis is ambiguous")
        result[source_sha256] = trial
    return result


def _checked_period_end(value: Any) -> str | None:
    if type(value) is not str:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed.isoformat() if parsed.isoformat() == value else None


def _semantic_period_role(value: Any) -> Any:
    return {
        "COMPARATIVE": "COMPARATIVE_PERIOD",
        "COMPARATIVE_PERIOD": "COMPARATIVE_PERIOD",
        "CURRENT": "CURRENT_PERIOD",
        "CURRENT_PERIOD": "CURRENT_PERIOD",
    }.get(value, value)


def _semantic_period_end(
    *,
    closure: Mapping[str, Any],
    period_role: Any,
    period_year: Any,
    cell_ref: Mapping[str, Any] | None = None,
    explicit_period_end: Any = None,
) -> str | None:
    del period_year  # A year alone never authenticates a reporting endpoint.
    explicit = _checked_period_end(explicit_period_end)
    if explicit is not None:
        return explicit
    normalized_role = _semantic_period_role(period_role)
    assignments = closure.get("period_receipt", {}).get("period_assignment_axis", [])
    if type(assignments) is not list:
        return None
    cell_key = canonical_json_sha256_v1(cell_ref) if type(cell_ref) is dict else None
    matches = [
        item
        for item in assignments
        if type(item) is dict
        and item.get("period_role") == normalized_role
        and (cell_key is None or canonical_json_sha256_v1(item.get("cell_ref")) == cell_key)
        and _checked_period_end(item.get("period_end")) is not None
    ]
    endpoints = {item["period_end"] for item in matches}
    if len(endpoints) == 1:
        return next(iter(endpoints))
    return None


def _period_role_for_cell(
    *, closure: Mapping[str, Any], receipt: Mapping[str, Any], cell: Mapping[str, Any]
) -> str | None:
    year = cell.get("period_year")
    owner_years = (
        closure.get("query_receipt", {}).get("owner_receipt", {}).get("reporting_year_axis", [])
    )
    if type(owner_years) is list and owner_years and type(owner_years[0]) is int:
        if year == owner_years[0]:
            return "CURRENT_PERIOD"
        if year == owner_years[0] - 1:
            return "COMPARATIVE_PERIOD"
    metric_roles = receipt.get("period_role_by_metric", {})
    if type(metric_roles) is dict and metric_roles.get(cell.get("metric_role")) in {
        "CURRENT_PERIOD",
        "COMPARATIVE_PERIOD",
    }:
        return metric_roles[cell["metric_role"]]
    return (
        receipt.get("period_role")
        if receipt.get("period_role") in {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"}
        else None
    )


def _semantic_source_state(cell: Mapping[str, Any]) -> str:
    coefficient = cell.get("coefficient")
    raw_state = cell.get("state")
    if type(coefficient) is int:
        # Numeric comparison intentionally treats a visible dash and a printed zero as
        # coefficient-equivalent while the raw state remains in the audit diagnostic.
        return "VALUE"
    if coefficient is None and raw_state == "SOURCE_BLANK":
        return "BLANK"
    return "UNRESOLVED"


def _declared_schema_by_id(compiled: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    root_id = compiled["family_root_report_norm_id"]
    declared: dict[int, dict[str, Any]] = {
        root_id: {
            "axis_role": None,
            "branch": None,
            "kind": "FAMILY_ROOT",
            "metric_role": None,
            "parent_report_norm_id": None,
            "report_norm_id": root_id,
        }
    }
    for branch, binding in compiled["branch_bindings_by_role"].items():
        branch_id = binding["branch_report_norm_id"]
        declared[branch_id] = {
            "axis_role": None,
            "branch": branch,
            "kind": "BRANCH_ROOT",
            "metric_role": None,
            "parent_report_norm_id": root_id,
            "report_norm_id": branch_id,
        }
        for axis_role, parent_id in binding["axis_parent_report_norm_id_by_role"].items():
            declared[parent_id] = {
                "axis_role": axis_role,
                "branch": branch,
                "kind": "AXIS_ROOT",
                "metric_role": None,
                "parent_report_norm_id": branch_id,
                "report_norm_id": parent_id,
            }
            for metric_role, offset in compiled["metric_offset_by_role"].items():
                report_norm_id = parent_id + offset
                if report_norm_id in declared:
                    raise _error("Family54 declared schema leaf identity collides")
                declared[report_norm_id] = {
                    "axis_role": axis_role,
                    "branch": branch,
                    "kind": "MAPPED_LEAF",
                    "metric_role": metric_role,
                    "parent_report_norm_id": parent_id,
                    "report_norm_id": report_norm_id,
                }
    return declared


def _mapping_role(
    mapping: Mapping[str, Any], *, compiled: Mapping[str, Any]
) -> tuple[str, str, str, int]:
    role = mapping.get("role")
    parts = role.split(":") if type(role) is str else []
    if len(parts) != 3:
        raise _error("Family54 mapping role is not branch:axis:metric")
    branch, axis_role, metric_role = parts
    branch_binding = compiled["branch_bindings_by_role"].get(branch)
    parent_id = (
        branch_binding.get("axis_parent_report_norm_id_by_role", {}).get(axis_role)
        if type(branch_binding) is dict
        else None
    )
    if (
        type(parent_id) is not int
        or metric_role not in compiled["metric_offset_by_role"]
        or mapping.get("report_norm_id")
        != parent_id + compiled["metric_offset_by_role"][metric_role]
    ):
        raise _error("Family54 mapping role and ReportNormID disagree")
    return branch, axis_role, metric_role, parent_id


def _current_semantic_axes(
    *, trials: Sequence[Mapping[str, Any]], compiled_specs: Mapping[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    assignments: list[dict[str, Any]] = []
    equations: list[dict[str, Any]] = []
    blank_cells: list[dict[str, Any]] = []
    source_only_components: list[dict[str, Any]] = []
    for trial in trials:
        candidate = _candidate(trial)
        if candidate is None:
            continue
        closure = candidate.get("closure_receipt")
        if type(closure) is not dict:
            raise _error("Family54 candidate closure is absent")
        receipts = closure.get("table_receipts")
        if type(receipts) is not list:
            raise _error("Family54 table receipt axis is absent")
        cells_by_ref: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
        for receipt in receipts:
            if type(receipt) is not dict or type(receipt.get("cell_axis")) is not list:
                raise _error("Family54 table receipt is invalid")
            for cell in receipt["cell_axis"]:
                if type(cell) is not dict or type(cell.get("cell_ref")) is not dict:
                    raise _error("Family54 table cell lineage is invalid")
                key = canonical_json_sha256_v1(cell["cell_ref"])
                if key in cells_by_ref:
                    raise _error("Family54 table cell lineage is duplicate")
                cells_by_ref[key] = (receipt, cell)
                axis_role = cell.get("axis_role")
                if type(axis_role) is str and axis_role.startswith("SOURCE_ONLY:"):
                    cell_period_role = _period_role_for_cell(
                        closure=closure, receipt=receipt, cell=cell
                    )
                    current = {
                        "axis_label": axis_role,
                        "branch": cell.get("branch"),
                        "cell_ref": canonical_clone_v1(cell["cell_ref"]),
                        "metric_role": cell.get("metric_role"),
                        "normalized_value": cell.get("coefficient"),
                        "period_end": _semantic_period_end(
                            closure=closure,
                            period_role=cell_period_role,
                            period_year=cell.get("period_year"),
                            cell_ref=cell.get("cell_ref"),
                        ),
                        "period_role": cell_period_role,
                        "raw_state": cell.get("state"),
                        "source_sha256": trial["source_sha256"],
                        "source_state": _semantic_source_state(cell),
                        "trial_status": trial["status"],
                    }
                    if current["source_state"] == "BLANK":
                        blank_cells.append(current)
                    else:
                        source_only_components.append(current)
        if trial.get("status") == READY:
            for mapping in candidate.get("mappings", []):
                branch, axis_role, metric_role, parent_id = _mapping_role(
                    mapping, compiled=compiled_specs
                )
                for value in mapping.get("values", []):
                    if type(value) is not dict or type(value.get("cell_ref")) is not dict:
                        raise _error("Family54 mapping value lineage is invalid")
                    source_cell = cells_by_ref.get(canonical_json_sha256_v1(value["cell_ref"]))
                    if source_cell is None:
                        raise _error("Family54 mapping value does not join one table cell")
                    receipt, cell = source_cell
                    value_period_role = value.get("axis_role") or _period_role_for_cell(
                        closure=closure, receipt=receipt, cell=cell
                    )
                    assignments.append(
                        {
                            "axis_role": axis_role,
                            "branch": branch,
                            "cell_ref": canonical_clone_v1(value["cell_ref"]),
                            "metric_role": metric_role,
                            "normalized_value": value.get("coefficient"),
                            "parent_report_norm_id": parent_id,
                            "period_end": _semantic_period_end(
                                closure=closure,
                                period_role=value_period_role,
                                period_year=cell.get("period_year"),
                                cell_ref=value.get("cell_ref"),
                                explicit_period_end=value.get("period_end"),
                            ),
                            "period_role": value_period_role,
                            "raw_state": value.get("state"),
                            "report_norm_id": mapping.get("report_norm_id"),
                            "source_sha256": trial["source_sha256"],
                            "source_state": _semantic_source_state(value),
                            "trial_status": trial["status"],
                        }
                    )
        for equation in closure.get("equations", []):
            if type(equation) is not dict:
                raise _error("Family54 equation receipt is invalid")
            term_cells = equation.get("term_cells")
            result_cell = equation.get("result_cell")
            if type(term_cells) is not list or type(result_cell) is not dict:
                raise _error("Family54 equation cells are invalid")
            raw_status = equation.get("status")
            normalized_status = (
                "EXACT"
                if raw_status == "EXACT"
                else "NOT_TESTABLE"
                if raw_status == "NOT_TESTABLE_SOURCE_BLANK"
                else raw_status
            )
            component_values = [
                cell.get("coefficient") if type(cell) is dict else None for cell in term_cells
            ]
            equation_period_role = equation.get("axis_role")
            equations.append(
                {
                    "branch": equation.get("branch"),
                    "component_values": sorted(
                        component_values, key=lambda item: canonical_json_bytes_v1(item)
                    ),
                    "computed_total": equation.get("computed_value"),
                    "metric_role": equation.get("metric_role"),
                    "period_end": _semantic_period_end(
                        closure=closure,
                        period_role=equation_period_role,
                        period_year=equation.get("period_year"),
                        cell_ref=result_cell.get("cell_ref"),
                        explicit_period_end=equation.get("period_end"),
                    ),
                    "period_role": equation_period_role,
                    "raw_status": raw_status,
                    "source_sha256": trial["source_sha256"],
                    "status": normalized_status,
                    "trial_status": trial["status"],
                    "visible_total": result_cell.get("coefficient"),
                }
            )
    return {
        "assignments": _canonical_sort(assignments),
        "blank_cells": _canonical_sort(blank_cells),
        "equations": _canonical_sort(equations),
        "source_only_components": _canonical_sort(source_only_components),
    }


def _historical_expected_axes(
    *, oracle: Mapping[str, Any], compiled_specs: Mapping[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    declared = _declared_schema_by_id(compiled_specs)
    documents: list[dict[str, Any]] = []
    structures: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    equations: list[dict[str, Any]] = []
    blanks: list[dict[str, Any]] = []
    source_only: list[dict[str, Any]] = []
    open_items: list[dict[str, Any]] = []
    absences: list[dict[str, Any]] = []
    for trial in oracle["trials"]:
        source_sha256 = trial.get("source_pdf_sha256")
        if type(source_sha256) is not str:
            raise _error("Family54 E-0161 source identity is invalid")
        scan = trial.get("scan")
        if type(scan) is not dict:
            raise _error("Family54 E-0161 scan receipt is invalid")
        documents.append(
            {
                "evidence_page_sequence": trial.get("evidence_page_sequence"),
                "historical_status": trial.get("status"),
                "page_count_scanned": scan.get("page_count_scanned"),
                "scan_status": scan.get("status"),
                "source_sha256": source_sha256,
            }
        )
        for binding in trial.get("verified_structure_bindings", []):
            if type(binding) is not dict:
                raise _error("Family54 E-0161 structure binding is invalid")
            structures.append(
                {
                    "canonical_name": binding.get("canonical_name"),
                    "hierarchy_level": binding.get("hierarchy_level"),
                    "parent_report_norm_id": binding.get("parent_report_norm_id"),
                    "report_norm_id": binding.get("report_norm_id"),
                    "source_sha256": source_sha256,
                    "status": binding.get("status"),
                }
            )
        for assignment in trial.get("verified_numeric_assignments", []):
            if type(assignment) is not dict:
                raise _error("Family54 E-0161 numeric assignment is invalid")
            report_norm_id = assignment.get("report_norm_id")
            schema_item = declared.get(report_norm_id)
            assignments.append(
                {
                    "axis_role": assignment.get("axis_key"),
                    "branch": schema_item.get("branch") if schema_item else None,
                    "metric_role": assignment.get("metric_key"),
                    "normalized_value": assignment.get("normalized_value"),
                    "oracle_status": assignment.get("status"),
                    "parent_report_norm_id": assignment.get("parent_report_norm_id"),
                    "period_end": assignment.get("period_end"),
                    "period_role": _semantic_period_role(assignment.get("period_role")),
                    "report_norm_id": report_norm_id,
                    "source_sha256": source_sha256,
                    "source_state": assignment.get("source_cell_status"),
                }
            )
        for row in trial.get("verified_numeric_rows", []):
            if type(row) is not dict or type(row.get("verified_accounting_equation")) is not dict:
                raise _error("Family54 E-0161 accounting row is invalid")
            equation = row["verified_accounting_equation"]
            status = (
                "EXACT"
                if equation.get("status") == "CORROBORATED_EXACT"
                else equation.get("status")
            )
            component_values = equation.get("component_values")
            equations.append(
                {
                    "branch": row.get("branch"),
                    "component_values": (
                        sorted(component_values, key=lambda item: canonical_json_bytes_v1(item))
                        if type(component_values) is list
                        else None
                    ),
                    "computed_total": equation.get("computed_total"),
                    "metric_role": row.get("metric_key"),
                    "oracle_name": equation.get("name"),
                    "period_end": row.get("period_end"),
                    "period_role": _semantic_period_role(row.get("period_role")),
                    "source_sha256": source_sha256,
                    "status": status,
                    "visible_total": equation.get("visible_total"),
                }
            )
            for cell in row.get("cells", []):
                if type(cell) is not dict or cell.get("report_norm_id") is not None:
                    continue
                expected = {
                    "axis_role": cell.get("axis_key"),
                    "branch": row.get("branch"),
                    "metric_role": row.get("metric_key"),
                    "normalized_value": cell.get("normalized_value"),
                    "period_end": row.get("period_end"),
                    "period_role": _semantic_period_role(row.get("period_role")),
                    "source_sha256": source_sha256,
                    "source_state": cell.get("source_cell_status"),
                }
                (blanks if expected["source_state"] == "BLANK" else source_only).append(expected)
        for item in trial.get("open_source_items", []):
            if type(item) is not dict:
                raise _error("Family54 E-0161 open source item is invalid")
            open_items.append(
                {
                    "physical_page": item.get("physical_page"),
                    "reason": item.get("reason"),
                    "source_label": item.get("source_label"),
                    "source_sha256": source_sha256,
                    "status": item.get("status"),
                }
            )
        bounded = trial.get("bounded_absences")
        if type(bounded) is not dict:
            raise _error("Family54 E-0161 bounded absence receipt is invalid")
        for name, status in bounded.items():
            if status is not None:
                branch = {
                    "detailed_business_report": "BUSINESS",
                    "detailed_geographic_report": "GEOGRAPHIC",
                }.get(name)
                if branch is None:
                    raise _error("Family54 E-0161 absence branch is invalid")
                absences.append(
                    {
                        "branch": branch,
                        "oracle_status": status,
                        "source_sha256": source_sha256,
                    }
                )
    axes = {
        "assignments": assignments,
        "blank_cells": blanks,
        "bounded_absences": absences,
        "documents": documents,
        "equations": equations,
        "open_source_items": open_items,
        "source_only_components": source_only,
        "structures": structures,
    }
    return {name: _canonical_sort(axis) for name, axis in axes.items()}


def _typed_key(item: Mapping[str, Any], fields: Sequence[str]) -> str:
    return canonical_json_sha256_v1([{field: item.get(field)} for field in fields])


def _missing_disposition(
    source_sha256: str, trials_by_source: Mapping[str, Mapping[str, Any]]
) -> str:
    trial = trials_by_source.get(source_sha256)
    if trial is None:
        return "CURRENT_DOCUMENT_MISSING"
    if trial.get("status") == UNRESOLVED:
        return "CURRENT_UNRESOLVED"
    if trial.get("status") == NOT_OBSERVED:
        return "CURRENT_NOT_OBSERVED"
    return "CURRENT_MISSING"


def _compare_expected_axis(
    *,
    expected: Sequence[Mapping[str, Any]],
    current: Sequence[Mapping[str, Any]],
    key_fields: Sequence[str],
    value_fields: Sequence[str],
    trials_by_source: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    current_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in current:
        current_by_key[_typed_key(item, key_fields)].append(canonical_clone_v1(item))
    compared: list[dict[str, Any]] = []
    for expected_item in expected:
        key = _typed_key(expected_item, key_fields)
        options = current_by_key.get(key, [])
        if len(options) == 1:
            current_item = options.pop()
            exact = same_typed_json_v1(
                {field: expected_item.get(field) for field in value_fields},
                {field: current_item.get(field) for field in value_fields},
            )
            disposition = "EXACT" if exact else "VALUE_MISMATCH"
        elif not options:
            current_item = None
            disposition = _missing_disposition(
                str(expected_item.get("source_sha256")), trials_by_source
            )
        else:
            current_item = None
            disposition = "CURRENT_AMBIGUOUS"
        compared.append(
            {
                "current": current_item,
                "disposition": disposition,
                "expected": canonical_clone_v1(expected_item),
            }
        )
    for options in current_by_key.values():
        for current_item in options:
            compared.append(
                {"current": current_item, "disposition": "CURRENT_EXTRA", "expected": None}
            )
    return _canonical_sort(compared)


def _historical_comparator_axes(
    *, trials: Sequence[Mapping[str, Any]], compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    oracle_ref, oracle = _historical_oracle()
    corrigendum_ref, corrigendum = _historical_corrigendum()
    expected = _historical_expected_axes(oracle=oracle, compiled_specs=compiled_specs)
    expected = _apply_historical_corrigendum(expected=expected, corrigendum=corrigendum)
    current = _current_semantic_axes(trials=trials, compiled_specs=compiled_specs)
    trials_by_source = _trial_by_source(trials)
    oracle_sources = {item["source_sha256"] for item in expected["documents"]}
    current = {
        name: [item for item in axis if item["source_sha256"] in oracle_sources]
        for name, axis in current.items()
    }

    historical_documents = []
    for item in expected["documents"]:
        trial = trials_by_source.get(item["source_sha256"])
        status = trial.get("status") if trial is not None else None
        historical_documents.append(
            {
                "current_document_ordinal": (
                    trial.get("document_ordinal") if trial is not None else None
                ),
                "current_status": status,
                "disposition": (
                    "CURRENT_READY"
                    if status == READY
                    else _missing_disposition(item["source_sha256"], trials_by_source)
                ),
                "expected": item,
            }
        )

    declared = _declared_schema_by_id(compiled_specs)
    historical_structures = []
    for item in expected["structures"]:
        actual = declared.get(item["report_norm_id"])
        parent_exact = (
            item["report_norm_id"] == compiled_specs["family_root_report_norm_id"]
            or actual is not None
            and actual["parent_report_norm_id"] == item["parent_report_norm_id"]
        )
        historical_structures.append(
            {
                "declared": actual,
                "disposition": "EXACT"
                if actual is not None and parent_exact
                else "SCHEMA_MISMATCH",
                "expected": item,
            }
        )

    assignments = _compare_expected_axis(
        expected=expected["assignments"],
        current=current["assignments"],
        key_fields=(
            "source_sha256",
            "report_norm_id",
            "parent_report_norm_id",
            "branch",
            "axis_role",
            "metric_role",
            "period_role",
            "period_end",
        ),
        value_fields=("normalized_value", "source_state"),
        trials_by_source=trials_by_source,
    )
    equations = _compare_expected_axis(
        expected=expected["equations"],
        current=current["equations"],
        key_fields=(
            "source_sha256",
            "branch",
            "metric_role",
            "period_role",
            "period_end",
        ),
        value_fields=(
            "status",
            "component_values",
            "computed_total",
            "visible_total",
        ),
        trials_by_source=trials_by_source,
    )
    source_component_key = (
        "source_sha256",
        "branch",
        "metric_role",
        "period_role",
        "period_end",
        "normalized_value",
        "source_state",
    )
    blank_cells = _compare_expected_axis(
        expected=expected["blank_cells"],
        current=current["blank_cells"],
        key_fields=source_component_key,
        value_fields=(),
        trials_by_source=trials_by_source,
    )
    source_only = _compare_expected_axis(
        expected=expected["source_only_components"],
        current=current["source_only_components"],
        key_fields=source_component_key,
        value_fields=(),
        trials_by_source=trials_by_source,
    )

    branches_by_source: dict[str, set[str]] = defaultdict(set)
    for trial in trials:
        candidate = _candidate(trial)
        if candidate is None:
            continue
        for receipt in candidate.get("closure_receipt", {}).get("table_receipts", []):
            if type(receipt) is dict and type(receipt.get("branch")) is str:
                branches_by_source[trial["source_sha256"]].add(receipt["branch"])
    absences = []
    for item in expected["bounded_absences"]:
        trial = trials_by_source.get(item["source_sha256"])
        if trial is None or trial.get("status") != READY:
            disposition = _missing_disposition(item["source_sha256"], trials_by_source)
        elif item["branch"] in branches_by_source[item["source_sha256"]]:
            disposition = "CURRENT_CONTRADICTION"
        else:
            disposition = "EXACT"
        absences.append(
            {
                "current_observed_branches": sorted(branches_by_source[item["source_sha256"]]),
                "disposition": disposition,
                "expected": item,
            }
        )

    open_items = [
        {"disposition": "HISTORICAL_OPEN_SOURCE_CONTEXT", "expected": item}
        for item in expected["open_source_items"]
    ]
    return {
        "historical_assignments": assignments,
        "historical_blank_cells": blank_cells,
        "historical_bounded_absences": _canonical_sort(absences),
        "historical_documents": _canonical_sort(historical_documents),
        "historical_equations": equations,
        "historical_open_source_items": _canonical_sort(open_items),
        "historical_source_only_equation_components": source_only,
        "historical_structures": _canonical_sort(historical_structures),
    }, [oracle_ref, corrigendum_ref]


def _audit_axes(
    *, sweep: Mapping[str, Any], compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    indexed = sweep["indexed_query_evidence"]
    trials = sweep["trials"]
    axes: dict[str, list[dict[str, Any]]] = {
        "accepted_clusters": canonical_clone_v1(indexed["accepted_clusters"]),
        "blank_cells": [],
        "component_regions": [],
        "document_dispositions": [],
        "equations": [],
        "mapping_values": [],
        "mappings": [],
        "period_assignments": [],
        "query_dispositions": canonical_clone_v1(indexed["candidate_dispositions"]),
        "source_only_cells": [],
        "table_receipts": [],
        "unresolved_documents": [],
    }
    for cluster in indexed["accepted_clusters"]:
        for region in cluster["component_regions"]:
            axes["component_regions"].append(
                {
                    "document_ordinal": cluster["document_ordinal"],
                    "region": canonical_clone_v1(region),
                }
            )
    for trial in trials:
        document = {
            "document_ordinal": trial["document_ordinal"],
            "source_logical_name": trial["source_logical_name"],
            "source_sha256": trial["source_sha256"],
        }
        candidate = _candidate(trial)
        axes["document_dispositions"].append(
            {
                **document,
                "candidate_count": trial["candidate_count"],
                "reasons": canonical_clone_v1(trial["reasons"]),
                "selected_candidate_id": trial["selected_candidate_id"],
                "status": trial["status"],
            }
        )
        if trial["status"] == UNRESOLVED:
            axes["unresolved_documents"].append(
                {
                    **document,
                    "candidate_id": candidate.get("candidate_id") if candidate else None,
                    "component_regions": (
                        canonical_clone_v1(candidate.get("component_regions", []))
                        if candidate
                        else []
                    ),
                    "reasons": canonical_clone_v1(trial["reasons"]),
                }
            )
        if candidate is None:
            continue
        closure = candidate["closure_receipt"]
        for receipt_ordinal, receipt in enumerate(closure["table_receipts"], start=1):
            axes["table_receipts"].append(
                {
                    **document,
                    "candidate_id": candidate["candidate_id"],
                    "receipt": canonical_clone_v1(receipt),
                    "receipt_ordinal": receipt_ordinal,
                }
            )
            for cell in receipt["cell_axis"]:
                axis_source_only = type(cell.get("axis_role")) is str and cell[
                    "axis_role"
                ].startswith("SOURCE_ONLY:")
                metric_source_only = type(cell.get("metric_role")) is str and cell[
                    "metric_role"
                ].startswith("SOURCE_ONLY_METRIC:")
                if axis_source_only or metric_source_only:
                    axes["source_only_cells"].append(
                        {
                            **document,
                            "candidate_id": candidate["candidate_id"],
                            "cell": canonical_clone_v1(cell),
                            "receipt_ordinal": receipt_ordinal,
                            "source_only_kinds": [
                                kind
                                for kind, present in (
                                    ("AXIS", axis_source_only),
                                    ("METRIC", metric_source_only),
                                )
                                if present
                            ],
                        }
                    )
        period_receipt = closure.get("period_receipt")
        period_assignment_axis = (
            period_receipt.get("period_assignment_axis") if type(period_receipt) is dict else None
        )
        if type(period_assignment_axis) is not list:
            raise _error("Family54 period assignment audit axis is absent")
        for assignment_ordinal, assignment in enumerate(period_assignment_axis, start=1):
            if type(assignment) is not dict:
                raise _error("Family54 period assignment audit item is invalid")
            axes["period_assignments"].append(
                {
                    **document,
                    "assignment": canonical_clone_v1(assignment),
                    "assignment_ordinal": assignment_ordinal,
                    "candidate_id": candidate["candidate_id"],
                }
            )
        for mapping_ordinal, mapping in enumerate(candidate["mappings"], start=1):
            axes["mappings"].append(
                {
                    **document,
                    "candidate_id": candidate["candidate_id"],
                    "mapping": canonical_clone_v1(mapping),
                    "mapping_ordinal": mapping_ordinal,
                }
            )
            for value_ordinal, value in enumerate(mapping["values"], start=1):
                axes["mapping_values"].append(
                    {
                        **document,
                        "item_mapping_id": mapping["item_mapping_id"],
                        "report_norm_id": mapping["report_norm_id"],
                        "role": mapping["role"],
                        "value": canonical_clone_v1(value),
                        "value_ordinal": value_ordinal,
                    }
                )
        for equation in closure["equations"]:
            axes["equations"].append({**document, "equation": canonical_clone_v1(equation)})
        for blank in closure["blank_cell_axis"]:
            axes["blank_cells"].append({**document, "blank": canonical_clone_v1(blank)})
    comparator_axes, oracle_refs = _historical_comparator_axes(
        trials=trials, compiled_specs=compiled_specs
    )
    return {**axes, **comparator_axes}, oracle_refs


def _audit_metrics(axes: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    comparator_names = {
        "historical_assignments": "EXACT",
        "historical_blank_cells": "EXACT",
        "historical_bounded_absences": "EXACT",
        "historical_documents": "CURRENT_READY",
        "historical_equations": "EXACT",
        "historical_source_only_equation_components": "EXACT",
        "historical_structures": "EXACT",
    }
    comparator_failures = sum(
        item.get("expected") is not None and item.get("disposition") != accepted
        for name, accepted in comparator_names.items()
        for item in axes[name]
    )
    historical_expected_axis_counts = {
        name: sum(item.get("expected") is not None for item in axes[name])
        for name in (
            "historical_assignments",
            "historical_blank_cells",
            "historical_bounded_absences",
            "historical_documents",
            "historical_equations",
            "historical_open_source_items",
            "historical_source_only_equation_components",
            "historical_structures",
        )
    }
    return {
        "blank_cell_count": len(axes["blank_cells"]),
        "component_region_count": len(axes["component_regions"]),
        "equation_count": len(axes["equations"]),
        "historical_assignment_exact_count": sum(
            item.get("disposition") == "EXACT" for item in axes["historical_assignments"]
        ),
        "historical_assignment_expected_count": sum(
            item.get("expected") is not None for item in axes["historical_assignments"]
        ),
        "historical_comparator_failure_count": comparator_failures,
        "historical_current_extra_count": sum(
            item.get("disposition") == "CURRENT_EXTRA"
            for name in comparator_names
            for item in axes[name]
        ),
        "historical_expected_axis_counts": historical_expected_axis_counts,
        "historical_open_source_item_count": len(axes["historical_open_source_items"]),
        "mapping_count": len(axes["mappings"]),
        "mapping_value_count": len(axes["mapping_values"]),
        "period_assignment_count": len(axes["period_assignments"]),
        "query_unresolved_count": sum(
            item.get("disposition") == UNRESOLVED for item in axes["query_dispositions"]
        ),
        "source_only_cell_count": len(axes["source_only_cells"]),
        "table_receipt_count": len(axes["table_receipts"]),
        "unresolved_document_count": len(axes["unresolved_documents"]),
    }


def build_segment_report_experimental_audit_v1(
    *,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_gemini_json_flat_family_sweep_v1(sweep)
    axes, oracle_refs = _audit_axes(sweep=checked, compiled_specs=compiled_specs)
    if set(axes) != AUDIT_AXIS_NAMES:
        raise _error("Family54 audit axis inventory drifted")
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
    sweep_payload = canonical_json_bytes_v1(checked)
    material = {
        "audit_metrics": _audit_metrics(axes),
        "axes": axes,
        "axis_counts": axis_counts,
        "axis_sha256": axis_sha256,
        "claim_boundary": (
            "AUTHENTICATED_SELECTED_GEMINI_JSON_SQLITE_SEGMENT_REPORT_REPLAY_AND_E0161_"
            "PLUS_PINNED_E0179_CORRIGENDUM_SEMANTIC_COMPARATOR_ONLY_NO_PROVIDER_NO_GEOMETRY_"
            "NO_CANONICAL_EXPORT_AUTHORITY"
        ),
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_oracle_refs": oracle_refs,
        "query_evidence_id": checked["indexed_query_evidence"]["query_evidence_id"],
        "query_receipt": checked["indexed_query_evidence"]["query_receipt"],
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            list(selected_page_json_version_ids)
        ),
        "spec_refs": canonical_clone_v1(spec_refs),
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_ref": {
            "path": sweep_output.name,
            "sha256": canonical_json_sha256_v1(checked),
            "size_bytes": len(sweep_payload),
            "sweep_id": checked["sweep_id"],
        },
    }
    return {
        **material,
        "audit_id": "gjsrmeav1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_segment_report_experimental_audit_content_v1(value: Any) -> dict[str, Any]:
    fields = {
        "audit_id",
        "audit_metrics",
        "axes",
        "axis_counts",
        "axis_sha256",
        "claim_boundary",
        "format_version",
        "historical_oracle_refs",
        "query_evidence_id",
        "query_receipt",
        "selected_page_json_frontier_sha256",
        "spec_refs",
        "state",
        "sweep_ref",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("state") != "EXPERIMENTAL_AUDIT_COMPLETE"
        or type(value.get("axes")) is not dict
        or set(value["axes"]) != AUDIT_AXIS_NAMES
        or any(type(axis) is not list for axis in value["axes"].values())
    ):
        raise _error("Family54 experimental audit shape drifted")
    counts = {name: len(axis) for name, axis in value["axes"].items()}
    hashes = {name: canonical_json_sha256_v1(axis) for name, axis in value["axes"].items()}
    if value.get("axis_counts") != counts or value.get("axis_sha256") != hashes:
        raise _error("Family54 experimental audit axis seal drifted")
    if value.get("audit_metrics") != _audit_metrics(value["axes"]):
        raise _error("Family54 experimental audit metrics drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    if value.get("audit_id") != "gjsrmeav1:audit:" + canonical_json_sha256_v1(material):
        raise _error("Family54 experimental audit identity drifted")
    return canonical_clone_v1(value)


def _validate_sqlite_replay(
    *,
    database: Path,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[Mapping[str, Any]],
) -> None:
    validate_selected_equity_matrix_family_query_evidence_v1(
        database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
        indexed_query_evidence=indexed_query_evidence,
    )
    validate_selected_equity_matrix_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=compiled_specs,
        indexed_query_evidence=indexed_query_evidence,
        trials=trials,
    )


def validate_segment_report_experimental_audit_replay_v1(
    value: Any,
    *,
    database: Path,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    selected_page_json_version_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_gemini_json_flat_family_sweep_v1(sweep)
    embedded = compile_gemini_json_flat_family_specs_v1(
        checked["specs"]["topology"]["value"],
        checked["specs"]["evaluation"]["value"],
        checked["specs"]["schema_binding"]["value"],
    )
    if (
        embedded.get("family_id") != FAMILY_ID
        or embedded.get("segment_report_mode") is not True
        or not same_typed_json_v1(embedded, compiled_specs)
    ):
        raise _error("Family54 caller and embedded compiled triplet differ")
    _validate_sqlite_replay(
        database=database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=embedded,
        indexed_query_evidence=checked["indexed_query_evidence"],
        trials=checked["trials"],
    )
    expected = build_segment_report_experimental_audit_v1(
        sweep=checked,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=embedded,
        spec_refs=spec_refs,
    )
    validate_segment_report_experimental_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("Family54 experimental audit does not replay exactly")
    return expected


def build_segment_report_experimental_bundle_v1(
    *,
    corpus_manifest_index_id: str,
    database: Path,
    selected_ids: Sequence[str],
    topology: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    schema: Mapping[str, Any],
    sweep_output: Path,
    spec_refs: Mapping[str, Any],
    effective_page_frontier: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    if compiled.get("family_id") != FAMILY_ID or compiled.get("segment_report_mode") is not True:
        raise _error("Family54 runner received a different family triplet")
    indexed = query_selected_equity_matrix_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
    )
    validate_selected_equity_matrix_family_query_evidence_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
    )
    pages = _load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=indexed["selected_page_axis"],
    )
    candidates = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        candidates[ordinal] = evaluate_gemini_json_equity_matrix_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages[ordinal],
            compiled_specs=compiled,
            query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                regions, owner_receipt=cluster["owner_receipt"]
            ),
            document_unit_context_evidence=cluster["document_unit_context_evidence"],
        )
    trials = _trials(indexed=indexed, candidates_by_ordinal=candidates)
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=corpus_manifest_index_id,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        indexed_query_evidence=indexed,
        trials=trials,
        effective_page_frontier=effective_page_frontier,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    _validate_sqlite_replay(
        database=database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    audit = build_segment_report_experimental_audit_v1(
        sweep=sweep,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    validate_segment_report_experimental_audit_replay_v1(
        audit,
        database=database,
        sweep=sweep,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    return sweep, audit, compiled


def _release_pin_actual(
    *, sweep: Mapping[str, Any], audit: Mapping[str, Any], selected_ids: Sequence[str]
) -> dict[str, Any]:
    spec_names = {"evaluation", "schema_binding", "topology"}
    specs = sweep.get("specs")
    spec_refs = audit.get("spec_refs")
    if type(specs) is not dict or set(specs) != spec_names:
        raise _error("Family54 embedded release spec inventory drifted")
    if type(spec_refs) is not dict or set(spec_refs) != spec_names:
        raise _error("Family54 release spec reference inventory drifted")
    embedded_spec_value_sha256: dict[str, str] = {}
    embedded_values: dict[str, Any] = {}
    for name in sorted(spec_names):
        embedded_ref = specs[name]
        if type(embedded_ref) is not dict or set(embedded_ref) != {"sha256", "value"}:
            raise _error("Family54 embedded release spec reference drifted")
        value_sha256 = canonical_json_sha256_v1(embedded_ref["value"])
        if embedded_ref["sha256"] != value_sha256:
            raise _error("Family54 embedded release spec value hash drifted")
        embedded_spec_value_sha256[name] = value_sha256
        embedded_values[name] = embedded_ref["value"]

        source_ref = spec_refs[name]
        if (
            type(source_ref) is not dict
            or set(source_ref) != {"path", "sha256", "size_bytes"}
            or type(source_ref["path"]) is not str
            or not source_ref["path"]
            or Path(source_ref["path"]).is_absolute()
            or ".." in Path(source_ref["path"]).parts
            or type(source_ref["sha256"]) is not str
            or len(source_ref["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in source_ref["sha256"])
            or type(source_ref["size_bytes"]) is not int
            or source_ref["size_bytes"] < 0
        ):
            raise _error("Family54 release spec file reference drifted")

    compiled = compile_gemini_json_flat_family_specs_v1(
        embedded_values["topology"],
        embedded_values["evaluation"],
        embedded_values["schema_binding"],
    )
    if compiled.get("family_id") != FAMILY_ID or compiled.get("segment_report_mode") is not True:
        raise _error("Family54 embedded release spec triplet drifted")
    return {
        "audit_id": audit["audit_id"],
        "audit_metrics": audit["audit_metrics"],
        "axis_counts": audit["axis_counts"],
        "axis_sha256": audit["axis_sha256"],
        "compiled_triplet_sha256": canonical_json_sha256_v1(compiled),
        "corpus_manifest_index_id": sweep["corpus_manifest_index_id"],
        "embedded_spec_value_sha256": embedded_spec_value_sha256,
        "historical_oracle_refs": canonical_clone_v1(audit["historical_oracle_refs"]),
        "implementation_refs": _release_implementation_refs(),
        "query_receipt": sweep["indexed_query_evidence"]["query_receipt"],
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(list(selected_ids)),
        "spec_refs": canonical_clone_v1(spec_refs),
        "sweep_id": sweep["sweep_id"],
        "sweep_metrics": sweep["metrics"],
    }


def _assert_release_pins(
    *, sweep: Mapping[str, Any], audit: Mapping[str, Any], selected_ids: Sequence[str]
) -> None:
    fields = {
        "audit_id",
        "audit_metrics",
        "axis_counts",
        "axis_sha256",
        "compiled_triplet_sha256",
        "corpus_manifest_index_id",
        "embedded_spec_value_sha256",
        "historical_oracle_refs",
        "implementation_refs",
        "query_receipt",
        "selected_page_json_frontier_sha256",
        "spec_refs",
        "sweep_id",
        "sweep_metrics",
    }
    if set(PINNED_RELEASE_PINS) != fields:
        raise _error("Family54 release pins have not been frozen from final-corpus EXP runs")
    actual = _release_pin_actual(sweep=sweep, audit=audit, selected_ids=selected_ids)
    if not same_typed_json_v1(actual, PINNED_RELEASE_PINS):
        raise _error(
            "Family54 frozen release pins drifted; actual="
            + json.dumps(actual, ensure_ascii=False, sort_keys=True)
        )


def _assert_persistence_gate(
    *,
    run_kind: str,
    results_database: Path,
    sweep: Mapping[str, Any],
    audit: Mapping[str, Any],
    selected_ids: Sequence[str],
) -> None:
    if run_kind == "EXPERIMENTAL":
        return
    if run_kind != "OFFICIAL":
        raise _error("Family54 run kind is invalid")
    if results_database.is_symlink() or not results_database.is_file():
        raise _error("Family54 OFFICIAL requires an existing regular results store")
    try:
        gemini_accounting_family_store_summary_v1(results_database)
    except (RuntimeError, sqlite3.DatabaseError) as exc:
        raise _error("Family54 OFFICIAL results store does not validate") from exc
    metrics = audit["audit_metrics"]
    if (
        sweep["metrics"]["unresolved_count"] != 0
        or metrics["query_unresolved_count"] != 0
        or metrics["unresolved_document_count"] != 0
        or metrics["historical_comparator_failure_count"] != 0
        or metrics.get("historical_expected_axis_counts") != PINNED_HISTORICAL_CORRECTED_AXIS_COUNTS
    ):
        raise _error("Family54 OFFICIAL readiness gates are not closed")
    _assert_release_pins(sweep=sweep, audit=audit, selected_ids=selected_ids)


def _implementation_paths() -> tuple[Path, ...]:
    return (
        ROOT / "scripts/experiments/run_gemini_json_segment_report_accounting_family_v1.py",
        ROOT / "scripts/experiments/run_gemini_json_equity_matrix_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_equity_matrix_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_segment_report_matrix_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_family_effective_page_frontier_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
    )


def _release_pin_redacted_runner_bytes_v1(payload: bytes) -> bytes:
    """Normalize only the release-pin literal so it cannot hash itself."""

    try:
        source = payload.decode("utf-8")
        tree = ast.parse(source)
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise _error("Family54 release runner source cannot be parsed") from exc
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "PINNED_RELEASE_PINS"
    ]
    if len(assignments) != 1 or not isinstance(assignments[0].value, ast.Dict):
        raise _error("Family54 release pin literal cannot be isolated")
    value = assignments[0].value
    if (
        value.end_lineno is None
        or value.end_col_offset is None
        or value.lineno < 1
        or value.end_lineno < value.lineno
    ):
        raise _error("Family54 release pin literal source span is absent")
    lines = payload.splitlines(keepends=True)
    start = sum(len(line) for line in lines[: value.lineno - 1]) + value.col_offset
    stop = sum(len(line) for line in lines[: value.end_lineno - 1]) + value.end_col_offset
    if not 0 <= start < stop <= len(payload):
        raise _error("Family54 release pin literal source span is invalid")
    return payload[:start] + b"{}" + payload[stop:]


def _release_implementation_refs() -> list[dict[str, Any]]:
    """Bind implementation bytes without creating a self-referential runner hash."""

    runner = Path(__file__).resolve()
    references = []
    for path in _implementation_paths():
        reference = _file_ref(path, root=ROOT)
        if path.resolve() == runner:
            normalized = _release_pin_redacted_runner_bytes_v1(path.read_bytes())
            reference = {
                **reference,
                "sha256": hashlib.sha256(normalized).hexdigest(),
                "size_bytes": len(normalized),
            }
        references.append(reference)
    return references


def _run_with_authenticated_database(
    args: argparse.Namespace,
    *,
    index: Mapping[str, Any],
    database_guard: Any,
    selected_ids: Sequence[str],
    topology: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    schema: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
    effective_page_frontier: Mapping[str, Any] | None,
    effective_page_artifact_root: Path | None,
) -> dict[str, Any]:
    sweep, audit, _compiled = build_segment_report_experimental_bundle_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        database=database_guard.path,
        selected_ids=selected_ids,
        topology=topology,
        evaluation=evaluation,
        schema=schema,
        sweep_output=args.output,
        spec_refs=spec_refs,
        effective_page_frontier=effective_page_frontier,
    )
    _assert_persistence_gate(
        run_kind=args.run_kind,
        results_database=args.results_database,
        sweep=sweep,
        audit=audit,
        selected_ids=selected_ids,
    )
    database_guard.validate()
    audit_output = args.output.with_suffix(".audit.json")
    _write_once(args.output, sweep)
    _write_once(audit_output, audit)
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=_file_ref(args.corpus_index),
        implementation_refs=[_file_ref(path, root=ROOT) for path in _implementation_paths()],
        run_kind=args.run_kind,
        source_page_database=database_guard.path,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
        effective_page_artifact_root=effective_page_artifact_root,
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("Family54 stored sweep differs from authenticated evaluation")
    output_ref = record_gemini_accounting_family_export_v1(
        args.results_database,
        family_run_id=stored["family_run_id"],
        output_path=args.output,
    )
    database_guard.validate()
    return {
        "audit_id": audit["audit_id"],
        "audit_output": str(audit_output),
        "axis_counts": audit["axis_counts"],
        "axis_sha256": audit["axis_sha256"],
        "disposition": "SUCCEEDED",
        "family_run_id": stored["family_run_id"],
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "output_ref": output_ref,
        "results_database": str(args.results_database),
        "run_kind": args.run_kind,
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    index = validate_current_corpus_manifest_index_v1(_json(args.corpus_index))
    artifact_root = args.artifact_root.resolve()
    source_database = _content_ref(artifact_root, index["database_ref"])
    source_database_ref = index["database_ref"]
    _assert_disjoint_results_store(
        source_database=source_database,
        results_database=args.results_database,
    )
    selected_ids = _selected_page_axis(index=index, artifact_root=artifact_root)
    effective_page_frontier = None
    effective_page_artifact_root = None
    frontier_path = getattr(args, "effective_page_frontier", None)
    frontier_root_path = getattr(args, "effective_page_artifact_root", None)
    if frontier_path is None and frontier_root_path is not None:
        raise _error("effective page artifact root requires an effective page frontier")
    if frontier_path is not None:
        effective_page_artifact_root = (
            artifact_root if frontier_root_path is None else frontier_root_path.resolve()
        )
        if frontier_root_path is not None and (
            frontier_root_path.is_symlink() or not effective_page_artifact_root.is_dir()
        ):
            raise _error("effective page artifact root is absent or not trusted")
        effective_page_frontier, selected_ids = apply_gemini_family_effective_page_frontier_v1(
            _json(frontier_path), base_page_json_version_ids=selected_ids
        )
        if (
            effective_page_frontier["base_corpus_manifest_index_id"]
            != index["corpus_manifest_index_id"]
            or effective_page_frontier["family_id"] != FAMILY_ID
        ):
            raise _error("effective page frontier does not bind Family54 and this corpus")
        authenticated_stages = []
        for stage in effective_page_frontier_stages_v1(effective_page_frontier):
            stage_source_database_ref = stage["database_ref"]
            stage_source_database = _content_ref(
                effective_page_artifact_root, stage_source_database_ref
            )
            _assert_disjoint_results_store(
                source_database=stage_source_database,
                results_database=args.results_database,
            )
            repair_results_database = _content_ref(
                effective_page_artifact_root, stage["results_database_ref"]
            )
            _assert_disjoint_results_store(
                source_database=repair_results_database,
                results_database=args.results_database,
            )
            authenticated_stages.append(
                (
                    stage,
                    stage_source_database_ref,
                    stage_source_database,
                    repair_results_database,
                )
            )
        for (
            stage,
            stage_source_database_ref,
            source_database,
            repair_results_database,
        ) in authenticated_stages:
            source_database_ref = stage_source_database_ref
            source_overlay = resolved_gemini_family_region_repair_overlay_v1(
                repair_results_database,
                family_run_id=stage["repair_source_family_run_id"],
            )
            if (
                source_overlay["family_id"] != stage["family_id"]
                or source_overlay["job_status_counts"] != stage["job_status_counts"]
            ):
                raise _error("Family54 effective frontier source jobs do not replay")
            lineages = page_json_region_repair_lineages_v1(
                source_database,
                observed_page_json_version_ids=[
                    replacement["selected_page_json_version_id"]
                    for replacement in source_overlay["replacements"]
                ],
            )
            replacements = []
            for replacement, lineage in zip(source_overlay["replacements"], lineages, strict=True):
                if (
                    lineage["base_page_json_version_id"] != replacement["base_page_json_version_id"]
                    or lineage["observed_page_json_version_id"]
                    != replacement["selected_page_json_version_id"]
                ):
                    raise _error("Family54 effective frontier repair lineage does not replay")
                replacements.append(
                    {
                        **replacement,
                        "repair_id": lineage["repair_id"],
                        "repair_receipt_sha256": lineage["repair_receipt_sha256"],
                    }
                )
            if replacements != stage["replacements"]:
                raise _error("Family54 effective frontier replacement evidence drifted")
    _assert_disjoint_results_store(
        source_database=source_database,
        results_database=args.results_database,
    )
    topology = _json(args.topology_spec)
    evaluation = _json(args.evaluation_spec)
    schema = _json(args.schema_binding_spec)
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    if compiled.get("family_id") != FAMILY_ID or compiled.get("segment_report_mode") is not True:
        raise _error("Family54 runner received a different family triplet")
    spec_refs = {
        "evaluation": _file_ref(args.evaluation_spec, root=ROOT),
        "schema_binding": _file_ref(args.schema_binding_spec, root=ROOT),
        "topology": _file_ref(args.topology_spec, root=ROOT),
    }
    with _authenticated_sqlite_snapshot(
        source_database, reference=source_database_ref
    ) as database_guard:
        return _run_with_authenticated_database(
            args,
            index=index,
            database_guard=database_guard,
            selected_ids=selected_ids,
            topology=topology,
            evaluation=evaluation,
            schema=schema,
            spec_refs=spec_refs,
            effective_page_frontier=effective_page_frontier,
            effective_page_artifact_root=effective_page_artifact_root,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--effective-page-frontier", type=Path)
    parser.add_argument("--effective-page-artifact-root", type=Path)
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--run-kind", choices=("EXPERIMENTAL", "OFFICIAL"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
