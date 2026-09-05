#!/usr/bin/env python3
"""Run Family 30 over an authenticated local JSON corpus.

The service-activity evaluator is shared with other multi-table families.  This
adapter makes the historical-corpus relationship explicit: expansion runs
authenticate the two eight-bank oracles and prove a zero-source intersection;
strict releases additionally replay the generic historical comparator and a
byte-pinned semantic sweep regression.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (  # noqa: E402
    READY,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
)
from bctc_ai.evaluation.gemini_json_service_activity_family_v1 import (  # noqa: E402
    FAMILY_ID,
    bind_gemini_json_service_activity_source_repair_artifact_v1,
    build_gemini_json_service_activity_region_query_receipt_v1,
    compile_gemini_json_service_activity_family_specs_v1,
    evaluate_gemini_json_service_activity_family_cluster_v1,
    recover_gemini_json_service_activity_query_cluster_v1,
    validate_gemini_json_service_activity_family_candidate_replay_v1,
)
from bctc_ai.evaluation.historical_comparator_policy_v1 import (  # noqa: E402
    DISJOINT_EXPANSION,
    EXACT_HISTORICAL_COMPARISON,
    NOT_APPLICABLE_DISJOINT_CORPUS,
    STRICT_RELEASE,
    audit_historical_comparator_policy_v1,
)
from bctc_ai.evaluation.historical_comparator_policy_v1 import (  # noqa: E402
    FORMAT_VERSION as HISTORICAL_COMPARATOR_POLICY_FORMAT_VERSION,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (  # noqa: E402
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (  # noqa: E402
    ingest_gemini_accounting_family_sweep_v1,
    load_gemini_accounting_family_sweep_v1,
    record_gemini_accounting_family_export_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    query_selected_multitable_hierarchical_family_regions_v1,
)
from scripts.experiments import (  # noqa: E402
    run_gemini_json_multitable_hierarchical_accounting_family_v1 as generic_runner,
)


class RunGeminiJsonServiceActivityAccountingFamilyV1Error(RuntimeError):
    """The Family 30 corpus, policy, result, or replay boundary drifted."""


def _error(message: str) -> RunGeminiJsonServiceActivityAccountingFamilyV1Error:
    return RunGeminiJsonServiceActivityAccountingFamilyV1Error(message)


AUDIT_FORMAT_VERSION = "GEMINI_JSON_SERVICE_ACTIVITY_EXPERIMENTAL_AUDIT_V1"
TOPOLOGY_SPEC_PATH = ROOT / "config/families/tm-service-activity-topology-v1.json"
EVALUATION_SPEC_PATH = ROOT / "config/families/tm-service-activity-evaluation-v1.json"
SCHEMA_BINDING_SPEC_PATH = ROOT / "config/families/tm-service-activity-schema-binding-v1.json"
SOURCE_REPAIR_PATH = ROOT / "data/registered/gemini_json_service_activity_source_repairs_v1.json"
ADAPTER_PATH = ROOT / "src/bctc_ai/evaluation/gemini_json_service_activity_family_v1.py"
SHARED_EVALUATOR_PATH = (
    ROOT / "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py"
)
SHARED_RUNNER_PATH = (
    ROOT / "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py"
)
PINNED_SHARED_EVALUATOR_SHA256 = "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2"
PINNED_SHARED_RUNNER_SHA256 = "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5"
PINNED_STRICT_REGRESSION_SWEEP_SHA256 = (
    "ee3fc0578e74f6a162f1322f266b372bba87da250d0dd70560b222e22d615210"
)
PINNED_STRICT_REGRESSION_SWEEP_SIZE_BYTES = 26_512_691
STRICT_REGRESSION_FORMAT_VERSION = (
    "SERVICE_ACTIVITY_STRICT_RELEASE_EVIDENCE_SAFE_REGRESSION_RECEIPT_V2"
)
PINNED_STRICT_REGRESSION_SEMANTIC_DELTA_COUNT = 50
REGISTERED_SOURCE_REPAIR_COUNT = 8
REGISTERED_SOURCE_REPAIR_ID_AXIS_SHA256 = (
    "cd3ead0dd089b006b315fa1d07bd831534bdc465063566b417e39be69aa103f2"
)


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _assert_shared_pins_v1() -> None:
    expected = {
        SHARED_EVALUATOR_PATH: PINNED_SHARED_EVALUATOR_SHA256,
        SHARED_RUNNER_PATH: PINNED_SHARED_RUNNER_SHA256,
    }
    drifted = [str(path) for path, digest in expected.items() if _sha256(path) != digest]
    if drifted:
        raise _error("Family 30 shared implementation pin drifted: " + ",".join(drifted))


def _assert_current_corpus(index: Mapping[str, Any]) -> None:
    documents = index.get("documents")
    if type(documents) is not list or not documents:
        raise _error("Family 30 conclusion corpus is empty")
    if any(
        "/2025/" not in document.get("relative_path", "")
        and "/2026/" not in document.get("relative_path", "")
        for document in documents
    ):
        raise _error("Family 30 conclusion corpus is outside the current reporting scope")


def _crop_rgb_sha256(pixmap: fitz.Pixmap, bbox: Sequence[int]) -> str:
    x0, y0, x1, y1 = bbox
    if (
        pixmap.alpha
        or pixmap.n != 3
        or not (0 <= x0 < x1 <= pixmap.width)
        or not (0 <= y0 < y1 <= pixmap.height)
    ):
        raise _error("Family 30 source-repair crop boundary drifted")
    samples = memoryview(pixmap.samples)
    row_width = (x1 - x0) * pixmap.n
    digest = sha256()
    for y in range(y0, y1):
        start = y * pixmap.stride + x0 * pixmap.n
        digest.update(samples[start : start + row_width])
    return digest.hexdigest()


def _authenticate_source_repair_images_v1(
    *, repairs: Sequence[Mapping[str, Any]], source_pdf_root: Path
) -> list[dict[str, Any]]:
    """Replay PDF bytes, rendered pages, and every registered RGB crop."""

    root = source_pdf_root.resolve()
    if source_pdf_root.is_symlink() or not root.is_dir():
        raise _error("Family 30 source-PDF root is unavailable")
    payloads: dict[tuple[str, str], bytes] = {}
    rendered_pages: dict[tuple[str, int], fitz.Pixmap] = {}
    checked = []
    for repair in repairs:
        source = repair["source_binding"]
        logical_name = source["source_logical_name"]
        source_sha256 = source["source_sha256"]
        path = (root / logical_name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise _error("Family 30 source-repair PDF path is unavailable")
        source_key = (logical_name, source_sha256)
        payload = payloads.get(source_key)
        if payload is None:
            payload = path.read_bytes()
            if (
                len(payload) != source["source_size_bytes"]
                or sha256(payload).hexdigest() != source_sha256
            ):
                raise _error("Family 30 source-repair PDF bytes drifted")
            payloads[source_key] = payload
        page_key = (logical_name, source["physical_page"])
        pixmap = rendered_pages.get(page_key)
        if pixmap is None:
            try:
                with fitz.open(stream=payload, filetype="pdf") as document:
                    page_index = source["physical_page"] - 1
                    if not 0 <= page_index < len(document):
                        raise _error("Family 30 source-repair physical page is outside its PDF")
                    pixmap = document[page_index].get_pixmap(
                        dpi=source["render_dpi"],
                        colorspace=fitz.csRGB,
                        alpha=False,
                    )
            except (RuntimeError, ValueError) as exc:
                raise _error("Family 30 source-repair PDF cannot be rendered") from exc
            rendered_pages[page_key] = pixmap
        image = pixmap.tobytes("png")
        actual_image = {
            "image_sha256": sha256(image).hexdigest(),
            "image_size_bytes": len(image),
            "media_type": "image/png",
            "pixel_height": pixmap.height,
            "pixel_width": pixmap.width,
            "render_dpi": source["render_dpi"],
        }
        if any(source[key] != value for key, value in actual_image.items()):
            raise _error("Family 30 source-repair page render drifted")
        visual = repair["visual_evidence"]
        if (
            _crop_rgb_sha256(
                pixmap,
                visual["table_crop_bbox_pixels_xyxy"],
            )
            != visual["table_crop_rgb_sha256"]
        ):
            raise _error("Family 30 source-repair table crop drifted")
        for item in [*repair["cell_repairs"], *repair["row_repairs"]]:
            if _crop_rgb_sha256(pixmap, item["crop_bbox_pixels_xyxy"]) != item["crop_rgb_sha256"]:
                raise _error("Family 30 source-repair cell/row crop drifted")
        checked.append(canonical_clone_v1(repair))
    return checked


def _family_id(value: Mapping[str, Any]) -> Any:
    return value.get("topology", {}).get("family_id")


def _mapping_projection(mapping: Any) -> dict[str, Any]:
    if type(mapping) is not dict or type(mapping.get("item_mapping_id")) is not str:
        raise _error("Family 30 regression mapping shape drifted")
    # This identifier seals the complete mapping and legitimately changes when
    # declarative aliases change.  Every semantic and source field remains.
    return {key: value for key, value in mapping.items() if key != "item_mapping_id"}


def _semantic_trial_axis(sweep: Mapping[str, Any]) -> list[dict[str, Any]]:
    if sweep.get("family_id") != FAMILY_ID or type(sweep.get("trials")) is not list:
        raise _error("strict regression sweep is not Family 30")
    axis = []
    seen = set()
    for trial in sweep["trials"]:
        if type(trial) is not dict:
            raise _error("Family 30 regression trial shape drifted")
        source_sha256 = trial.get("source_sha256")
        mappings = trial.get("mappings")
        reasons = trial.get("reasons")
        if (
            type(source_sha256) is not str
            or source_sha256 in seen
            or type(trial.get("source_logical_name")) is not str
            or type(trial.get("status")) is not str
            or type(mappings) is not list
            or type(reasons) is not list
        ):
            raise _error("Family 30 regression source axis is invalid")
        seen.add(source_sha256)
        axis.append(
            {
                "mappings": [_mapping_projection(item) for item in mappings],
                "reasons": reasons,
                "source_logical_name": trial["source_logical_name"],
                "source_sha256": source_sha256,
                "status": trial["status"],
            }
        )
    return axis


def _strict_regression_receipt(
    *, sweep: Mapping[str, Any], baseline_path: Path | None
) -> dict[str, Any]:
    if baseline_path is None:
        raise _error("STRICT_RELEASE requires --strict-regression-sweep")
    try:
        baseline_ref = generic_runner._file_ref(baseline_path)
        baseline = generic_runner._json(baseline_path)
    except generic_runner.RunGeminiJsonMultitableHierarchicalAccountingFamilyV1Error as exc:
        raise _error("Family 30 strict regression sweep does not authenticate") from exc
    if (
        baseline_ref["sha256"] != PINNED_STRICT_REGRESSION_SWEEP_SHA256
        or baseline_ref["size_bytes"] != PINNED_STRICT_REGRESSION_SWEEP_SIZE_BYTES
    ):
        raise _error("Family 30 strict regression sweep bytes drifted")
    expected_axis = _semantic_trial_axis(baseline)
    actual_axis = _semantic_trial_axis(sweep)
    expected_source_axis = [
        {
            "reasons": item["reasons"],
            "source_logical_name": item["source_logical_name"],
            "source_sha256": item["source_sha256"],
            "status": item["status"],
        }
        for item in expected_axis
    ]
    actual_source_axis = [
        {
            "reasons": item["reasons"],
            "source_logical_name": item["source_logical_name"],
            "source_sha256": item["source_sha256"],
            "status": item["status"],
        }
        for item in actual_axis
    ]
    if not same_typed_json_v1(actual_source_axis, expected_source_axis):
        raise _error("Family 30 strict release source/status/reason axis is not exact")
    semantic_delta_axis = _semantic_mapping_delta_axis_v1(
        baseline=baseline,
        current=sweep,
    )
    if len(semantic_delta_axis) != PINNED_STRICT_REGRESSION_SEMANTIC_DELTA_COUNT:
        raise _error("Family 30 strict release semantic delta count drifted")
    observation_contract = validate_source_observation_mapping_contract_v1(sweep)
    material = {
        "baseline_ref": baseline_ref,
        "baseline_semantic_trial_axis_sha256": canonical_json_sha256_v1(expected_axis),
        "current_semantic_trial_axis_sha256": canonical_json_sha256_v1(actual_axis),
        "disposition": (
            "EXACT_SOURCE_STATUS_REASON_AXIS_WITH_AUTHENTICATED_EVIDENCE_SAFE_"
            "SEMANTIC_MAPPING_DELTAS"
        ),
        "format_version": STRICT_REGRESSION_FORMAT_VERSION,
        "mapping_semantic_delta_axis": semantic_delta_axis,
        "mapping_semantic_delta_axis_sha256": canonical_json_sha256_v1(
            semantic_delta_axis
        ),
        "mapping_semantic_delta_count": len(semantic_delta_axis),
        "source_observation_contract": observation_contract,
        "source_status_reason_axis_sha256": canonical_json_sha256_v1(
            actual_source_axis
        ),
        "source_count": len(actual_axis),
    }
    return {
        **material,
        "receipt_id": "f30srsv1:receipt:" + canonical_json_sha256_v1(material),
    }


def _trial_selected_candidate_v1(trial: Mapping[str, Any]) -> Mapping[str, Any]:
    candidates = trial.get("candidates")
    selected_id = trial.get("selected_candidate_id")
    if (
        type(candidates) is not list
        or type(selected_id) is not str
        or trial.get("candidate_count") != len(candidates)
    ):
        raise _error("Family 30 semantic delta trial candidate axis is invalid")
    selected = [
        candidate
        for candidate in candidates
        if type(candidate) is dict and candidate.get("candidate_id") == selected_id
    ]
    if len(selected) != 1:
        raise _error("Family 30 semantic delta selected candidate is not unique")
    candidate = selected[0]
    if (
        not same_typed_json_v1(candidate.get("mappings"), trial.get("mappings"))
        or candidate.get("status") != trial.get("status")
        or not same_typed_json_v1(candidate.get("reasons"), trial.get("reasons"))
    ):
        raise _error("Family 30 semantic delta trial differs from selected candidate")
    return candidate


def _mapping_axis_by_key_v1(mappings: Any) -> dict[tuple[int, str], dict[str, Any]]:
    if type(mappings) is not list:
        raise _error("Family 30 semantic delta mapping axis is invalid")
    result = {}
    for mapping in mappings:
        projected = _mapping_projection(mapping)
        key = (projected.get("report_norm_id"), projected.get("role"))
        if (
            type(key[0]) is not int
            or type(key[1]) is not str
            or key in result
        ):
            raise _error("Family 30 semantic delta mapping key is invalid or duplicate")
        result[key] = projected
    return result


def _mapping_region_keys_v1(mapping: Mapping[str, Any]) -> set[tuple[str, str, str]]:
    refs = mapping.get("source_refs")
    if type(refs) is not list or not refs:
        return set()
    keys = set()
    for source_ref in refs:
        locator = source_ref.get("locator") if type(source_ref) is dict else None
        if type(locator) is not dict or any(
            type(locator.get(key)) is not str
            for key in ("page_json_version_id", "section_id", "table_id")
        ):
            return set()
        keys.add(
            (
                locator["page_json_version_id"],
                locator["section_id"],
                locator["table_id"],
            )
        )
    return keys


def _candidate_region_keys_v1(candidate: Mapping[str, Any]) -> set[tuple[str, str, str]]:
    regions = candidate.get("component_regions")
    if type(regions) is not list or not regions:
        raise _error("Family 30 semantic delta candidate region axis is absent")
    keys = set()
    for region in regions:
        if type(region) is not dict or any(
            type(region.get(key)) is not str
            for key in ("page_json_version_id", "section_id", "table_id")
        ):
            raise _error("Family 30 semantic delta candidate region is invalid")
        keys.add(
            (
                region["page_json_version_id"],
                region["section_id"],
                region["table_id"],
            )
        )
    return keys


def _mapping_value_axis_v1(mapping: Mapping[str, Any]) -> list[dict[str, Any]]:
    values = mapping.get("values")
    if type(values) is not list or not values or any(type(cell) is not dict for cell in values):
        raise _error("Family 30 semantic delta mapping value axis is invalid")
    return [
        {
            "coefficient": cell.get("coefficient"),
            "source_text": cell.get("source_text"),
        }
        for cell in values
    ]


def _blank_zero_removed_v1(
    baseline_mapping: Mapping[str, Any], current_mapping: Mapping[str, Any]
) -> bool:
    baseline_values = baseline_mapping.get("values")
    current_values = current_mapping.get("values")
    if (
        type(baseline_values) is not list
        or type(current_values) is not list
        or len(baseline_values) != len(current_values)
        or not baseline_values
    ):
        return False
    removed = False
    for baseline_cell, current_cell in zip(
        baseline_values, current_values, strict=True
    ):
        if type(baseline_cell) is not dict or type(current_cell) is not dict:
            return False
        if same_typed_json_v1(baseline_cell, current_cell):
            continue
        baseline_state = baseline_cell.get("state")
        current_state = current_cell.get("state")
        if not (
            baseline_cell.get("coefficient") == 0
            and baseline_cell.get("source_text") is None
            and type(baseline_state) is str
            and ("BLANK" in baseline_state or "INFERRED" in baseline_state)
            and current_cell.get("coefficient") is None
            and current_cell.get("source_text") is None
            and current_state
            in {
                "ABSENT_SOURCE_AXIS_ROLE",
                "BLANK_SOURCE_CELL",
                "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
                "UNOBSERVED_SOURCE_LANE",
            }
        ):
            return False
        removed = True
    return removed


def _semantic_mapping_change_reason_v1(
    *,
    baseline_mapping: Mapping[str, Any] | None,
    current_mapping: Mapping[str, Any] | None,
    current_region_keys: set[tuple[str, str, str]],
) -> str:
    if baseline_mapping is None:
        assert current_mapping is not None
        current_keys = _mapping_region_keys_v1(current_mapping)
        if not current_keys or not current_keys <= current_region_keys:
            raise _error("Family 30 added mapping is outside the authenticated cluster")
        return "SOURCE_VISIBLE_SCHEMA_ROLE_ADDED_FROM_AUTHENTICATED_CLUSTER"
    if current_mapping is None:
        baseline_keys = _mapping_region_keys_v1(baseline_mapping)
        if not baseline_keys or baseline_keys & current_region_keys:
            raise _error("Family 30 removed mapping is not outside the current owner fence")
        return "BASELINE_NONOWNER_MAPPING_REMOVED_BY_CURRENT_OWNER_FENCE"
    if baseline_mapping.get("unit") != current_mapping.get("unit"):
        raise _error("Family 30 semantic delta changed a mapping unit")
    current_keys = _mapping_region_keys_v1(current_mapping)
    if not current_keys or not current_keys <= current_region_keys:
        raise _error("Family 30 changed mapping is outside the authenticated cluster")
    if _mapping_value_axis_v1(baseline_mapping) == _mapping_value_axis_v1(current_mapping):
        return "SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED"
    if _blank_zero_removed_v1(baseline_mapping, current_mapping):
        return "BASELINE_BLANK_ZERO_REMOVED_AND_SOURCE_BLANK_PRESERVED"
    values = current_mapping.get("values")
    assert type(values) is list
    if all(
        type(cell.get("coefficient")) is int
        and type(cell.get("source_text")) is str
        for cell in values
        if type(cell) is dict
    ):
        return "MAPPING_REBOUND_TO_EXACT_SOURCE_VISIBLE_ROW"
    if all(
        type(cell) is dict
        and (
            cell.get("coefficient") is None
            or type(cell.get("coefficient")) is int
            and type(cell.get("state")) is str
            and cell["state"].startswith(
                (
                    "AGGREGATED_",
                    "CORROBORATED_",
                    "DERIVED_",
                    "EXACT_",
                    "SOURCE_OBSERVED_",
                    "SOURCE_VISIBLE_",
                )
            )
        )
        for cell in values
    ):
        return "MAPPING_RECOMPUTED_FROM_EXACT_AUTHENTICATED_OWNER_FRONTIER"
    raise _error("Family 30 semantic mapping delta is not evidence-safe")


def _semantic_mapping_delta_axis_v1(
    *, baseline: Mapping[str, Any], current: Mapping[str, Any]
) -> list[dict[str, Any]]:
    baseline_trials = baseline.get("trials")
    current_trials = current.get("trials")
    if (
        baseline.get("family_id") != FAMILY_ID
        or current.get("family_id") != FAMILY_ID
        or type(baseline_trials) is not list
        or type(current_trials) is not list
        or len(baseline_trials) != len(current_trials)
    ):
        raise _error("Family 30 semantic delta sweep axes are invalid")
    delta_axis = []
    for baseline_trial, current_trial in zip(
        baseline_trials, current_trials, strict=True
    ):
        if (
            type(baseline_trial) is not dict
            or type(current_trial) is not dict
            or baseline_trial.get("source_sha256") != current_trial.get("source_sha256")
        ):
            raise _error("Family 30 semantic delta source join drifted")
        baseline_mappings = _mapping_axis_by_key_v1(baseline_trial.get("mappings"))
        current_mappings = _mapping_axis_by_key_v1(current_trial.get("mappings"))
        changed_keys = [
            key
            for key in sorted(set(baseline_mappings) | set(current_mappings))
            if not same_typed_json_v1(
                baseline_mappings.get(key), current_mappings.get(key)
            )
        ]
        if not changed_keys:
            continue
        selected_candidate = _trial_selected_candidate_v1(current_trial)
        current_region_keys = _candidate_region_keys_v1(selected_candidate)
        changes = []
        for report_norm_id, role in changed_keys:
            baseline_mapping = baseline_mappings.get((report_norm_id, role))
            current_mapping = current_mappings.get((report_norm_id, role))
            reason = _semantic_mapping_change_reason_v1(
                baseline_mapping=baseline_mapping,
                current_mapping=current_mapping,
                current_region_keys=current_region_keys,
            )
            changes.append(
                {
                    "baseline_mapping_sha256": (
                        None
                        if baseline_mapping is None
                        else canonical_json_sha256_v1(baseline_mapping)
                    ),
                    "current_mapping_sha256": (
                        None
                        if current_mapping is None
                        else canonical_json_sha256_v1(current_mapping)
                    ),
                    "reason": reason,
                    "report_norm_id": report_norm_id,
                    "role": role,
                }
            )
        delta_axis.append(
            {
                "baseline_mapping_axis_sha256": canonical_json_sha256_v1(
                    list(baseline_mappings.values())
                ),
                "current_mapping_axis_sha256": canonical_json_sha256_v1(
                    list(current_mappings.values())
                ),
                "document_ordinal": current_trial.get("document_ordinal"),
                "mapping_changes": changes,
                "reason_axis": sorted({change["reason"] for change in changes}),
                "source_logical_name": current_trial["source_logical_name"],
                "source_sha256": current_trial["source_sha256"],
            }
        )
    return delta_axis


def validate_service_activity_strict_regression_receipt_v1(
    value: Any,
    *,
    sweep: Mapping[str, Any],
    baseline_path: Path | None,
) -> dict[str, Any]:
    expected = _strict_regression_receipt(
        sweep=sweep,
        baseline_path=baseline_path,
    )
    if type(value) is not dict or not same_typed_json_v1(value, expected):
        raise _error("Family 30 strict regression receipt drifted")
    return expected


def _historical_oracle_material(
    *, compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    refs = []
    rows = []
    for ref_index, (reference, artifact) in enumerate(
        generic_runner._historical_oracles(compiled_specs=compiled_specs)
    ):
        trials = artifact["trials"]
        refs.append({**reference, "expected_trial_count": len(trials)})
        for trial in trials:
            source_sha256 = trial.get("source_pdf_sha256")
            if type(source_sha256) is not str:
                raise _error("Family 30 historical oracle source identity is absent")
            rows.append(
                {
                    "oracle_ref_index": ref_index,
                    "source_sha256": source_sha256,
                }
            )
    return refs, rows


def _historical_comparator_axis(
    *,
    policy: str,
    current_manifest_index_id: str,
    current_manifest_source_sha256s: Sequence[str],
    current_manifest_page_json_version_ids: Sequence[str],
    current_candidate_source_sha256s: Sequence[str],
    current_replay_source_sha256s: Sequence[str],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    oracle_refs, oracle_rows = _historical_oracle_material(compiled_specs=compiled_specs)
    strict_axis: list[dict[str, Any]] = []
    strict_axis_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if policy == STRICT_RELEASE:
        strict_axis, generic_refs = generic_runner._historical_comparator_axis(
            trials=trials, compiled_specs=compiled_specs
        )
        if [
            {**reference, "expected_trial_count": 8} for reference in generic_refs
        ] != oracle_refs or any(item.get("disposition") != "EXACT" for item in strict_axis):
            raise _error("Family 30 strict historical comparator is not exact")
        for item in strict_axis:
            source_sha256 = item.get("source_sha256")
            if type(source_sha256) is not str:
                raise _error("Family 30 historical comparator source identity drifted")
            strict_axis_by_source[source_sha256].append(item)

    def strict_compare(oracle: Mapping[str, Any], current: Mapping[str, Any]) -> Mapping[str, Any]:
        source_sha256 = oracle["source_sha256"]
        if current.get("source_sha256") != source_sha256:
            raise _error("Family 30 strict source join drifted")
        axis = strict_axis_by_source.get(source_sha256, [])
        if not axis or any(item.get("disposition") != "EXACT" for item in axis):
            raise _error("Family 30 strict source comparison is not exact")
        return {
            "axis": axis,
            "disposition": EXACT_HISTORICAL_COMPARISON,
        }

    policy_receipt = audit_historical_comparator_policy_v1(
        policy=policy,
        pinned_oracle_refs=oracle_refs,
        normalized_oracle_rows=oracle_rows,
        current_manifest_index_id=current_manifest_index_id,
        current_manifest_source_sha256s=current_manifest_source_sha256s,
        current_manifest_page_json_version_ids=current_manifest_page_json_version_ids,
        current_trials=trials,
        current_candidate_source_sha256s=current_candidate_source_sha256s,
        current_replay_source_sha256s=current_replay_source_sha256s,
        current_selected_page_json_version_ids=current_manifest_page_json_version_ids,
        strict_compare=strict_compare if policy == STRICT_RELEASE else None,
    )
    if policy == DISJOINT_EXPANSION:
        if (
            policy_receipt["disposition"] != NOT_APPLICABLE_DISJOINT_CORPUS
            or policy_receipt["comparison_axis"] != []
        ):
            raise _error("Family 30 expansion comparator receipt drifted")
        return [], oracle_refs, policy_receipt
    return strict_axis, oracle_refs, policy_receipt


def _audit_axes(
    *,
    policy: str,
    current_manifest_index_id: str,
    current_manifest_source_sha256s: Sequence[str],
    current_manifest_page_json_version_ids: Sequence[str],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]], dict[str, Any]]:
    mappings = []
    equations = []
    clusters = []
    period_normalizations = []
    source_repairs = []
    unit_corroborations = []
    for trial in trials:
        candidates = trial.get("candidates")
        if trial.get("status") != READY or type(candidates) is not list or len(candidates) != 1:
            continue
        candidate = candidates[0]
        document = {
            "document_ordinal": trial["document_ordinal"],
            "source_logical_name": trial["source_logical_name"],
            "source_sha256": trial["source_sha256"],
        }
        clusters.append(
            {
                **document,
                "component_regions": candidate["component_regions"],
                "query_receipt_sha256": canonical_json_sha256_v1(
                    candidate["closure_receipt"]["query_receipt"]
                ),
            }
        )
        for mapping in candidate["mappings"]:
            record = {
                **document,
                "coefficients": [value["coefficient"] for value in mapping["values"]],
                "report_norm_id": mapping["report_norm_id"],
                "role": mapping["role"],
                "row_id": mapping["row_id"],
                "states": [value["state"] for value in mapping["values"]],
                "unit": mapping["unit"],
            }
            decimal_cells = [
                value
                for value in mapping["values"]
                if "decimal_scale" in value or "normalized_decimal" in value
            ]
            if decimal_cells:
                if len(decimal_cells) != len(mapping["values"]) or any(
                    type(value.get("decimal_scale")) is not int
                    or type(value.get("normalized_decimal")) is not str
                    for value in decimal_cells
                ):
                    raise _error("Family 30 audit decimal mapping axis is incomplete")
                record.update(
                    {
                        "decimal_scales": [value["decimal_scale"] for value in decimal_cells],
                        "normalized_decimals": [
                            value["normalized_decimal"] for value in decimal_cells
                        ],
                    }
                )
            mappings.append(record)
        for equation in candidate["closure_receipt"]["equations"]:
            equations.append({**document, "equation": equation})
        adapter = candidate["closure_receipt"].get("service_activity_adapter_receipt")
        if type(adapter) is dict:
            for receipt in adapter["period_normalization_receipts"]:
                period_normalizations.append({**document, **canonical_clone_v1(receipt)})
            for receipt in adapter["source_repair_receipts"]:
                source_repairs.append({**document, **canonical_clone_v1(receipt)})
            for receipt in adapter["unit_corroboration_receipts"]:
                unit_corroborations.append({**document, **canonical_clone_v1(receipt)})
    source_by_ordinal = {
        document["document_ordinal"]: document["source_sha256"]
        for document in indexed_query_evidence["selected_document_axis"]
    }
    candidate_sources = [
        source_by_ordinal[cluster["document_ordinal"]]
        for cluster in indexed_query_evidence["accepted_clusters"]
    ]
    replay_sources = [trial["source_sha256"] for trial in trials if trial["candidates"]]
    if len(candidate_sources) != len(replay_sources) or set(candidate_sources) != set(
        replay_sources
    ):
        raise _error("Family 30 indexed candidate/replay axes drifted")
    comparator, oracle_refs, policy_receipt = _historical_comparator_axis(
        policy=policy,
        current_manifest_index_id=current_manifest_index_id,
        current_manifest_source_sha256s=current_manifest_source_sha256s,
        current_manifest_page_json_version_ids=current_manifest_page_json_version_ids,
        current_candidate_source_sha256s=candidate_sources,
        current_replay_source_sha256s=replay_sources,
        trials=trials,
        compiled_specs=compiled_specs,
    )
    return (
        {
            "clusters": clusters,
            "equations": equations,
            "historical_comparator": comparator,
            "mappings": mappings,
            "period_normalizations": period_normalizations,
            "source_repairs": source_repairs,
            "unit_corroborations": unit_corroborations,
        },
        oracle_refs,
        policy_receipt,
    )


def build_service_activity_experimental_audit_v1(
    *,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    historical_comparator_policy: str,
    current_manifest_index_id: str,
    current_manifest_source_sha256s: Sequence[str],
    selected_page_json_version_ids: Sequence[str],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    observation_contract: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    if sweep.get("corpus_manifest_index_id") != current_manifest_index_id:
        raise _error("Family 30 sweep/current manifest identity drifted")
    axes, oracle_refs, policy_receipt = _audit_axes(
        policy=historical_comparator_policy,
        current_manifest_index_id=current_manifest_index_id,
        current_manifest_source_sha256s=current_manifest_source_sha256s,
        current_manifest_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=indexed_query_evidence,
        trials=trials,
        compiled_specs=compiled_specs,
    )
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
    expected_repair_ids = sorted(
        repair["repair_id"]
        for repair in compiled_specs["service_activity_source_repair_overlay"]["repairs"]
        if repair["base_page_json_version_id"] in set(selected_page_json_version_ids)
    )
    applied_repair_ids = sorted(receipt["repair_id"] for receipt in axes["source_repairs"])
    source_repair_application = {
        "applied_count": len(applied_repair_ids),
        "applied_repair_ids_sha256": canonical_json_sha256_v1(applied_repair_ids),
        "applied_unique_count": len(set(applied_repair_ids)),
        "expected_count": len(expected_repair_ids),
        "expected_repair_ids_sha256": canonical_json_sha256_v1(expected_repair_ids),
        "overlay_id": compiled_specs["service_activity_source_repair_overlay"]["overlay_id"],
    }
    comparator = axes["historical_comparator"]
    audit_metrics = {
        "equation_count": axis_counts["equations"],
        "historical_comparator_exact_count": sum(
            item["disposition"] == "EXACT" for item in comparator
        ),
        "historical_disposition_exact_count": sum(
            item["record_kind"] == "DOCUMENT_DISPOSITION" and item["disposition"] == "EXACT"
            for item in comparator
        ),
        "historical_mapping_exact_count": sum(
            item["record_kind"] == "MAPPING_VALUE" and item["disposition"] == "EXACT"
            for item in comparator
        ),
        "historical_mapping_record_count": sum(
            item["record_kind"] == "MAPPING_VALUE" for item in comparator
        ),
        "mapping_count": axis_counts["mappings"],
    }
    sweep_payload = canonical_json_bytes_v1(sweep)
    material = {
        "axes": axes,
        "axis_counts": axis_counts,
        "axis_sha256": axis_sha256,
        "audit_metrics": audit_metrics,
        "claim_boundary": (
            "AUTHENTICATED_SELECTED_GEMINI_JSON_SQLITE_REPLAY_PDF_RENDER_CROP_"
            "SOURCE_TRANSCRIPTION_AND_HISTORICAL_ROLE_VALUE_COMPARATOR_ONLY_"
            "NO_PROVIDER_NO_EQUATION_BACKSOLVE_NO_CANONICAL_EXPORT_AUTHORITY"
        ),
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": policy_receipt,
        "historical_oracle_refs": oracle_refs,
        "query_evidence_id": indexed_query_evidence["query_evidence_id"],
        "query_receipt": indexed_query_evidence["query_receipt"],
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            list(selected_page_json_version_ids)
        ),
        "source_observation_contract": canonical_clone_v1(observation_contract),
        "source_repair_application": source_repair_application,
        "spec_refs": dict(spec_refs),
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_ref": {
            "path": sweep_output.name,
            "sha256": sha256(sweep_payload).hexdigest(),
            "size_bytes": len(sweep_payload),
            "sweep_id": sweep["sweep_id"],
        },
    }
    return {
        **material,
        "audit_id": "gjf30saeav1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_service_activity_experimental_audit_content_v1(value: Any) -> dict[str, Any]:
    fields = {
        "audit_id",
        "axes",
        "axis_counts",
        "axis_sha256",
        "audit_metrics",
        "claim_boundary",
        "format_version",
        "historical_comparator_policy_receipt",
        "historical_oracle_refs",
        "query_evidence_id",
        "query_receipt",
        "selected_page_json_frontier_sha256",
        "source_observation_contract",
        "source_repair_application",
        "spec_refs",
        "state",
        "sweep_ref",
    }
    axis_names = {
        "clusters",
        "equations",
        "historical_comparator",
        "mappings",
        "period_normalizations",
        "source_repairs",
        "unit_corroborations",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("state") != "EXPERIMENTAL_AUDIT_COMPLETE"
        or type(value.get("axes")) is not dict
        or set(value["axes"]) != axis_names
        or any(type(axis) is not list for axis in value["axes"].values())
    ):
        raise _error("Family 30 experimental audit shape drifted")
    counts = {name: len(axis) for name, axis in value["axes"].items()}
    hashes = {name: canonical_json_sha256_v1(axis) for name, axis in value["axes"].items()}
    if value.get("axis_counts") != counts or value.get("axis_sha256") != hashes:
        raise _error("Family 30 experimental audit axis seal drifted")
    receipt = value.get("historical_comparator_policy_receipt")
    policy = receipt.get("policy") if type(receipt) is dict else None
    expected_repair_count = REGISTERED_SOURCE_REPAIR_COUNT if policy == DISJOINT_EXPANSION else 0
    expected_repair_hash = (
        REGISTERED_SOURCE_REPAIR_ID_AXIS_SHA256
        if policy == DISJOINT_EXPANSION
        else canonical_json_sha256_v1([])
    )
    application = value.get("source_repair_application")
    applied_ids = sorted(
        receipt.get("repair_id")
        for receipt in value["axes"]["source_repairs"]
        if type(receipt) is dict and type(receipt.get("repair_id")) is str
    )
    if (
        value.get("source_observation_contract", {}).get("violation_count") != 0
        or type(application) is not dict
        or application.get("expected_count") != expected_repair_count
        or application.get("applied_count") != expected_repair_count
        or application.get("applied_unique_count") != expected_repair_count
        or len(applied_ids) != expected_repair_count
        or len(set(applied_ids)) != expected_repair_count
        or application.get("expected_repair_ids_sha256") != expected_repair_hash
        or application.get("applied_repair_ids_sha256") != expected_repair_hash
        or canonical_json_sha256_v1(applied_ids) != expected_repair_hash
        or application.get("overlay_id")
        != "gjsafav1:overlay:33575846ee64630de7c4fc5bcc906be946a983b04c8558f7189bf1fc533111f3"
    ):
        raise _error("Family 30 source-repair/source-observation audit drifted")
    disposition = receipt.get("disposition") if type(receipt) is dict else None
    if (
        type(receipt) is not dict
        or receipt.get("format_version") != HISTORICAL_COMPARATOR_POLICY_FORMAT_VERSION
        or policy not in {STRICT_RELEASE, DISJOINT_EXPANSION}
        or receipt.get("oracle_authentication", {}).get("refs")
        != value.get("historical_oracle_refs")
        or receipt.get("current_axis_validation", {}).get("manifest_document_count")
        != value.get("query_receipt", {}).get("selected_document_count")
        or receipt.get("current_axis_validation", {}).get("trial_source_count")
        != value.get("query_receipt", {}).get("selected_document_count")
        or receipt.get("current_axis_validation", {}).get("candidate_source_count")
        != value.get("query_receipt", {}).get("accepted_cluster_count")
        or receipt.get("current_axis_validation", {}).get("replay_source_count")
        != value.get("query_receipt", {}).get("accepted_cluster_count")
        or receipt.get("current_axis_validation", {}).get("selected_page_json_version_count")
        != value.get("query_receipt", {}).get("selected_page_count")
    ):
        raise _error("Family 30 historical comparator policy receipt drifted")
    comparator = value["axes"]["historical_comparator"]
    if policy == STRICT_RELEASE:
        if disposition != EXACT_HISTORICAL_COMPARISON or not comparator:
            raise _error("Family 30 strict comparator audit drifted")
    elif (
        disposition != NOT_APPLICABLE_DISJOINT_CORPUS
        or receipt.get("comparison_axis") != []
        or receipt.get("corpus_relation", {}).get("overlap_count") != 0
        or comparator != []
    ):
        raise _error("Family 30 disjoint comparator audit drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    if value.get("audit_id") != "gjf30saeav1:audit:" + canonical_json_sha256_v1(material):
        raise _error("Family 30 experimental audit identity drifted")
    return json.loads(canonical_json_bytes_v1(value))


def _validate_audit_replay(
    value: Any,
    *,
    database: Path | None,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    historical_comparator_policy: str,
    current_manifest_index_id: str,
    current_manifest_source_sha256s: Sequence[str],
    selected_page_json_version_ids: Sequence[str],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    checked_sweep = validate_gemini_json_flat_family_sweep_v1(sweep)
    embedded = compile_gemini_json_flat_family_specs_v1(
        checked_sweep["specs"]["topology"]["value"],
        checked_sweep["specs"]["evaluation"]["value"],
        checked_sweep["specs"]["schema_binding"]["value"],
    )
    family_embedded = bind_gemini_json_service_activity_source_repair_artifact_v1(
        embedded,
        generic_runner._json(SOURCE_REPAIR_PATH),
    )
    if not same_typed_json_v1(family_embedded, compiled_specs):
        raise _error("Family 30 caller and embedded compiled specs differ")
    if not same_typed_json_v1(checked_sweep["trials"], trials) or not same_typed_json_v1(
        checked_sweep["indexed_query_evidence"], indexed_query_evidence
    ):
        raise _error("Family 30 audit sweep/query/trial axis drifted")
    if database is not None:
        replayed = replay_service_activity_trials_from_source_v1(
            source_page_database=database,
            selected_page_json_version_ids=tuple(selected_page_json_version_ids),
            compiled_specs=embedded,
            indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        )
        if not same_typed_json_v1(replayed, checked_sweep["trials"]):
            raise _error("Family 30 source candidate replay drifted")
    expected = build_service_activity_experimental_audit_v1(
        sweep=checked_sweep,
        sweep_output=sweep_output,
        historical_comparator_policy=historical_comparator_policy,
        current_manifest_index_id=current_manifest_index_id,
        current_manifest_source_sha256s=current_manifest_source_sha256s,
        selected_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
        compiled_specs=family_embedded,
        observation_contract=validate_source_observation_mapping_contract_v1(checked_sweep),
        spec_refs=spec_refs,
    )
    validate_service_activity_experimental_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("Family 30 experimental audit does not replay exactly")
    return expected


def validate_service_activity_experimental_audit_replay_v1(
    value: Any, *, database: Path, **kwargs: Any
) -> dict[str, Any]:
    return _validate_audit_replay(value, database=database, **kwargs)


def _assert_policy_receipt(*, audit: Mapping[str, Any], policy: str) -> None:
    receipt = audit.get("historical_comparator_policy_receipt")
    if type(receipt) is not dict or receipt.get("policy") != policy:
        raise _error("Family 30 historical comparator policy receipt is absent")
    if policy == DISJOINT_EXPANSION:
        if (
            receipt.get("disposition") != NOT_APPLICABLE_DISJOINT_CORPUS
            or receipt.get("comparison_axis") != []
            or receipt.get("corpus_relation", {}).get("overlap_count") != 0
            or audit.get("axes", {}).get("historical_comparator") != []
        ):
            raise _error("Family 30 expansion corpus is not exactly disjoint")
        return
    if policy != STRICT_RELEASE or receipt.get("disposition") != EXACT_HISTORICAL_COMPARISON:
        raise _error("Family 30 strict historical comparator is not exact")


def replay_service_activity_trials_from_source_v1(
    *,
    source_page_database: Path,
    selected_page_json_version_ids: tuple[str, ...],
    compiled_specs: dict[str, Any],
    indexed_query_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Re-query and replay every candidate through the byte-bound adapter."""

    topology = generic_runner._json(TOPOLOGY_SPEC_PATH)
    evaluation = generic_runner._json(EVALUATION_SPEC_PATH)
    schema = generic_runner._json(SCHEMA_BINDING_SPEC_PATH)
    generic_compiled = compile_gemini_json_flat_family_specs_v1(
        topology,
        evaluation,
        schema,
    )
    if not same_typed_json_v1(generic_compiled, compiled_specs):
        raise _error("Family 30 source replay declarative specs drifted")
    family_compiled = bind_gemini_json_service_activity_source_repair_artifact_v1(
        generic_compiled,
        generic_runner._json(SOURCE_REPAIR_PATH),
    )
    indexed = _query_selected_service_activity_family_regions_v1(
        source_page_database,
        selected_ids=selected_page_json_version_ids,
        compiled_specs=family_compiled,
    )
    if not same_typed_json_v1(indexed, indexed_query_evidence):
        raise _error("Family 30 source replay rebuilt different query evidence")
    pages = generic_runner._load_selected_pages_by_document(
        source_page_database,
        selected_ids=list(selected_page_json_version_ids),
        selected_page_axis=indexed["selected_page_axis"],
    )
    candidates = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        receipt = build_gemini_json_service_activity_region_query_receipt_v1(regions)
        candidate = evaluate_gemini_json_service_activity_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages[ordinal],
            compiled_specs=family_compiled,
            query_receipt=receipt,
        )
        candidates[ordinal] = validate_gemini_json_service_activity_family_candidate_replay_v1(
            candidate,
            regions=regions,
            page_json_by_version=pages[ordinal],
            compiled_specs=family_compiled,
            query_receipt=receipt,
        )
    return generic_runner._trials(
        indexed=indexed,
        candidates_by_ordinal=candidates,
    )


def _generic_source_replay_specs_v1(
    *,
    topology: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    schema: Mapping[str, Any],
    family_compiled: Mapping[str, Any],
) -> dict[str, Any]:
    """Recover the generic declarative frontier expected by store replay."""

    generic_compiled = compile_gemini_json_flat_family_specs_v1(
        topology,
        evaluation,
        schema,
    )
    rebound = bind_gemini_json_service_activity_source_repair_artifact_v1(
        generic_compiled,
        generic_runner._json(SOURCE_REPAIR_PATH),
    )
    if not same_typed_json_v1(rebound, family_compiled):
        raise _error("Family 30 generic and adapter declarative specs differ")
    return generic_compiled


def _query_selected_service_activity_family_regions_v1(
    database: Path,
    *,
    selected_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild generic evidence, then apply the exact F30 owner-only recovery."""

    generic = query_selected_multitable_hierarchical_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled_specs,
    )
    pages = generic_runner._load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=generic["selected_page_axis"],
    )
    page_axes: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for axis in generic["selected_page_axis"]:
        page_axes[axis["document_ordinal"]].append(axis)
    generic_clusters = {
        item["document_ordinal"]: item["cluster"]
        for item in generic["candidate_dispositions"]
    }
    clusters = []
    for document in generic["selected_document_axis"]:
        ordinal = document["document_ordinal"]
        records = [
            {
                **canonical_clone_v1(axis),
                "page_json": pages[ordinal][axis["page_json_version_id"]],
            }
            for axis in page_axes[ordinal]
        ]
        clusters.append(
            recover_gemini_json_service_activity_query_cluster_v1(
                page_records=records,
                base_cluster=generic_clusters[ordinal],
                compiled_specs=compiled_specs,
            )
        )
    evidence = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=generic["selected_document_axis"],
        selected_page_axis=generic["selected_page_axis"],
        document_clusters=clusters,
        query_policy_sha256=canonical_json_sha256_v1(compiled_specs["query_policy"]),
    )
    return validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        evidence,
        compiled_specs=compiled_specs,
    )


def _validate_selected_service_activity_query_evidence_v1(
    database: Path,
    *,
    selected_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
    indexed_query_evidence: Any,
) -> dict[str, Any]:
    supplied = validate_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        indexed_query_evidence,
        compiled_specs=compiled_specs,
    )
    replayed = _query_selected_service_activity_family_regions_v1(
        database,
        selected_ids=selected_ids,
        compiled_specs=compiled_specs,
    )
    if not same_typed_json_v1(supplied, replayed):
        raise _error("Family 30 selected query evidence does not replay")
    return replayed


def _implementation_refs() -> list[dict[str, Any]]:
    paths = (
        ROOT / "scripts/experiments/run_gemini_json_service_activity_accounting_family_v1.py",
        ADAPTER_PATH,
        SHARED_EVALUATOR_PATH,
        SHARED_RUNNER_PATH,
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/historical_comparator_policy_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        TOPOLOGY_SPEC_PATH,
        EVALUATION_SPEC_PATH,
        SCHEMA_BINDING_SPEC_PATH,
        SOURCE_REPAIR_PATH,
    )
    return [generic_runner._file_ref(path, root=ROOT) for path in paths]


def _run_with_authenticated_database(
    args: argparse.Namespace,
    *,
    index: Mapping[str, Any],
    database_guard: Any,
    selected_ids: Sequence[str],
    topology: dict[str, Any],
    evaluation: dict[str, Any],
    schema: dict[str, Any],
    compiled: dict[str, Any],
    spec_refs: dict[str, Any],
) -> dict[str, Any]:
    database = database_guard.path
    source_replay_compiled = _generic_source_replay_specs_v1(
        topology=topology,
        evaluation=evaluation,
        schema=schema,
        family_compiled=compiled,
    )
    indexed = _query_selected_service_activity_family_regions_v1(
        database,
        selected_ids=selected_ids,
        compiled_specs=compiled,
    )
    _validate_selected_service_activity_query_evidence_v1(
        database,
        selected_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
    )
    pages = generic_runner._load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=indexed["selected_page_axis"],
    )
    candidates_by_ordinal = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        receipt = build_gemini_json_service_activity_region_query_receipt_v1(regions)
        candidate = evaluate_gemini_json_service_activity_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages[ordinal],
            compiled_specs=compiled,
            query_receipt=receipt,
        )
        candidates_by_ordinal[ordinal] = (
            validate_gemini_json_service_activity_family_candidate_replay_v1(
                candidate,
                regions=regions,
                page_json_by_version=pages[ordinal],
                compiled_specs=compiled,
                query_receipt=receipt,
            )
        )
    trials = generic_runner._trials(indexed=indexed, candidates_by_ordinal=candidates_by_ordinal)
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=indexed,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    observation_contract = validate_source_observation_mapping_contract_v1(sweep)
    replayed_trials = replay_service_activity_trials_from_source_v1(
        source_page_database=database,
        selected_page_json_version_ids=tuple(selected_ids),
        compiled_specs=source_replay_compiled,
        indexed_query_evidence=indexed,
    )
    if not same_typed_json_v1(replayed_trials, trials):
        raise _error("Family 30 SQLite candidate replay returned a different trial axis")
    source_sha256s = [document["source_sha256"] for document in index["documents"]]
    audit = build_service_activity_experimental_audit_v1(
        sweep=sweep,
        sweep_output=args.output,
        historical_comparator_policy=args.historical_comparator_policy,
        current_manifest_index_id=index["corpus_manifest_index_id"],
        current_manifest_source_sha256s=source_sha256s,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        observation_contract=observation_contract,
        spec_refs=spec_refs,
    )
    _validate_audit_replay(
        audit,
        database=None,
        sweep=sweep,
        sweep_output=args.output,
        historical_comparator_policy=args.historical_comparator_policy,
        current_manifest_index_id=index["corpus_manifest_index_id"],
        current_manifest_source_sha256s=source_sha256s,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    _assert_policy_receipt(audit=audit, policy=args.historical_comparator_policy)
    regression_receipt = (
        _strict_regression_receipt(sweep=sweep, baseline_path=args.strict_regression_sweep)
        if args.historical_comparator_policy == STRICT_RELEASE
        else None
    )
    database_guard.validate()
    audit_output = args.output.with_suffix(".audit.json")
    regression_output = (
        args.output.with_suffix(".strict-regression.json")
        if regression_receipt is not None
        else None
    )
    generic_runner._write_once(args.output, sweep)
    generic_runner._write_once(audit_output, audit)
    if regression_output is not None:
        generic_runner._write_once(regression_output, regression_receipt)
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=generic_runner._file_ref(args.corpus_index),
        implementation_refs=_implementation_refs(),
        run_kind=args.run_kind,
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
        source_replay_adapter=replay_service_activity_trials_from_source_v1,
        source_replay_adapter_ref=generic_runner._file_ref(
            ROOT / "scripts/experiments/run_gemini_json_service_activity_accounting_family_v1.py",
            root=ROOT,
        ),
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored Family 30 sweep differs from authenticated evaluation")
    validate_source_observation_mapping_contract_v1(stored_sweep)
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
        "historical_comparator_policy": args.historical_comparator_policy,
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "output_ref": output_ref,
        "results_database": str(args.results_database),
        "run_kind": args.run_kind,
        "strict_regression_output": (
            None if regression_output is None else str(regression_output)
        ),
        "strict_regression_receipt": regression_receipt,
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    policy = args.historical_comparator_policy
    if args.run_kind == "OFFICIAL" and policy != STRICT_RELEASE:
        raise _error("OFFICIAL Family 30 run requires STRICT_RELEASE")
    if policy == DISJOINT_EXPANSION and args.run_kind != "EXPERIMENTAL":
        raise _error("Family 30 expansion run must be EXPERIMENTAL")
    if policy == DISJOINT_EXPANSION and args.strict_regression_sweep is not None:
        raise _error("Family 30 expansion run cannot claim a strict regression sweep")
    _assert_shared_pins_v1()
    index = validate_current_corpus_manifest_index_v1(generic_runner._json(args.corpus_index))
    if policy == DISJOINT_EXPANSION:
        _assert_current_corpus(index)
    artifact_root = args.artifact_root.resolve()
    database = generic_runner._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic_runner._selected_page_axis(index=index, artifact_root=artifact_root)
    topology = generic_runner._json(args.topology_spec)
    evaluation = generic_runner._json(args.evaluation_spec)
    schema = generic_runner._json(args.schema_binding_spec)
    source_repairs = generic_runner._json(args.source_repair_artifact)
    compiled = compile_gemini_json_service_activity_family_specs_v1(
        topology,
        evaluation,
        schema,
        source_repairs,
    )
    if _family_id(compiled) != FAMILY_ID:
        raise _error("runner accepts only SERVICE_ACTIVITY")
    checked_repairs = _authenticate_source_repair_images_v1(
        repairs=compiled["service_activity_source_repair_overlay"]["repairs"],
        source_pdf_root=args.source_pdf_root,
    )
    if not same_typed_json_v1(
        checked_repairs,
        compiled["service_activity_source_repair_overlay"]["repairs"],
    ):
        raise _error("Family 30 source-repair authentication axis drifted")
    spec_refs = {
        "evaluation": generic_runner._file_ref(args.evaluation_spec, root=ROOT),
        "schema_binding": generic_runner._file_ref(args.schema_binding_spec, root=ROOT),
        "source_repair_artifact": generic_runner._file_ref(
            args.source_repair_artifact,
            root=ROOT,
        ),
        "topology": generic_runner._file_ref(args.topology_spec, root=ROOT),
    }
    with generic_runner._authenticated_sqlite_snapshot(
        database, reference=index["database_ref"]
    ) as database_guard:
        return _run_with_authenticated_database(
            args,
            index=index,
            database_guard=database_guard,
            selected_ids=selected_ids,
            topology=topology,
            evaluation=evaluation,
            schema=schema,
            compiled=compiled,
            spec_refs=spec_refs,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--source-pdf-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, default=TOPOLOGY_SPEC_PATH)
    parser.add_argument("--evaluation-spec", type=Path, default=EVALUATION_SPEC_PATH)
    parser.add_argument(
        "--schema-binding-spec",
        type=Path,
        default=SCHEMA_BINDING_SPEC_PATH,
    )
    parser.add_argument(
        "--source-repair-artifact",
        type=Path,
        default=SOURCE_REPAIR_PATH,
    )
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--run-kind", choices=("EXPERIMENTAL", "OFFICIAL"), required=True)
    parser.add_argument(
        "--historical-comparator-policy",
        choices=(STRICT_RELEASE, DISJOINT_EXPANSION),
        required=True,
    )
    parser.add_argument("--strict-regression-sweep", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
