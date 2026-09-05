#!/usr/bin/env python3
"""Run Family 35 over one authenticated selected-JSON corpus.

This runner keeps the shared multi-table engine byte-pinned and applies only
the Family-35 adapter: authenticated PDF-visible literal repairs, the exact
income-statement root fallback, and source-proven VND parsing projections.
Historical comparison is explicit: the 19-bank expansion must be disjoint;
the frozen 140-document corpus must join and compare both eight-bank oracles.
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

from bctc_ai.evaluation.gemini_json_capital_contribution_dividend_income_family_v1 import (  # noqa: E402
    FAMILY_ID,
    adapt_gemini_json_capital_contribution_dividend_income_indexed_query_evidence_v1,
    build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1,
    compile_gemini_json_capital_contribution_dividend_income_family_specs_v1,
    evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1,
    validate_gemini_json_capital_contribution_dividend_income_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.historical_comparator_policy_v1 import (  # noqa: E402
    DISJOINT_EXPANSION,
    EXACT_HISTORICAL_COMPARISON,
    NOT_APPLICABLE_DISJOINT_CORPUS,
    STRICT_RELEASE,
    audit_historical_comparator_policy_v1,
)
from bctc_ai.evaluation.source_observation_mapping_contract_v1 import (  # noqa: E402
    validate_source_observation_mapping_contract_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    query_selected_multitable_hierarchical_family_regions_v1,
)
from scripts.experiments import (  # noqa: E402
    run_gemini_json_multitable_hierarchical_accounting_family_v1 as generic,
)


class RunGeminiJsonCapitalContributionDividendIncomeV1Error(RuntimeError):
    """The Family-35 corpus, source, mapping, or replay boundary drifted."""


def _error(
    message: str,
) -> RunGeminiJsonCapitalContributionDividendIncomeV1Error:
    return RunGeminiJsonCapitalContributionDividendIncomeV1Error(message)


AUDIT_FORMAT_VERSION = (
    "GEMINI_JSON_CAPITAL_CONTRIBUTION_DIVIDEND_INCOME_EXPERIMENTAL_AUDIT_V1"
)
TOPOLOGY_SPEC_PATH = (
    ROOT / "config/families/tm-capital-contribution-dividend-income-topology-v1.json"
)
EVALUATION_SPEC_PATH = (
    ROOT / "config/families/tm-capital-contribution-dividend-income-evaluation-v1.json"
)
SCHEMA_BINDING_SPEC_PATH = ROOT / (
    "config/families/tm-capital-contribution-dividend-income-schema-binding-v1.json"
)
ADAPTER_SPEC_PATH = ROOT / (
    "config/families/tm-capital-contribution-dividend-income-adapter-v1.json"
)
SOURCE_REPAIR_PATH = ROOT / (
    "data/registered/"
    "gemini_json_capital_contribution_dividend_income_source_repairs_v1.json"
)
ADAPTER_PATH = ROOT / (
    "src/bctc_ai/evaluation/"
    "gemini_json_capital_contribution_dividend_income_family_v1.py"
)
SHARED_EVALUATOR_PATH = ROOT / (
    "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py"
)
SHARED_RUNNER_PATH = ROOT / (
    "scripts/experiments/"
    "run_gemini_json_multitable_hierarchical_accounting_family_v1.py"
)
PINNED_SHARED_EVALUATOR_SHA256 = (
    "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2"
)
PINNED_SHARED_RUNNER_SHA256 = (
    "d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5"
)
PINNED_FULL271_INDEX_ID = (
    "gjfccmiv1:index:8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a"
)
PINNED_FULL271_METRICS = {
    "document_count": 271,
    "mapping_count": 639,
    "not_observed_count": 52,
    "ready_count": 217,
    "unresolved_count": 2,
}
PINNED_OLD140_INDEX_ID = (
    "gjfccmiv1:index:61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3"
)
PINNED_OLD140_METRICS = {
    "document_count": 140,
    "mapping_count": 431,
    "not_observed_count": 7,
    "ready_count": 133,
    "unresolved_count": 0,
}
PINNED_OLD140_SEMANTIC_TRIAL_AXIS_SHA256 = (
    "91a20c320093d94d96bfb0b6a9486b61bd8758188835691823bf1f5db79c0ce9"
)
PINNED_STRICT_HISTORICAL_COMPARATOR_RECORD_COUNT = 71
PINNED_STRICT_LEGACY_BLANK_ZERO_PROJECTION_COUNT = 1
PINNED_STRICT_VISIBLE_PRIMARY_ROOT_ADDITION_COUNT = 2
REGISTERED_SOURCE_REPAIR_COUNT = 48
REGISTERED_SOURCE_REPAIR_CELL_COUNT = 125


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
    drifted = [
        str(path) for path, expected_sha in expected.items() if _sha256(path) != expected_sha
    ]
    if drifted:
        raise _error("Family-35 shared implementation pin drifted: " + ",".join(drifted))


def _assert_corpus_policy_v1(index: Mapping[str, Any], *, policy: str) -> None:
    documents = index.get("documents")
    if type(documents) is not list or not documents:
        raise _error("Family-35 conclusion corpus is empty")
    index_id = index.get("corpus_manifest_index_id")
    if policy == DISJOINT_EXPANSION:
        if index_id != PINNED_FULL271_INDEX_ID or any(
            "/2025/" not in item.get("relative_path", "")
            and "/2026/" not in item.get("relative_path", "")
            for item in documents
        ):
            raise _error("Family-35 expansion corpus is not the pinned 2025-2026 frontier")
    elif policy == STRICT_RELEASE:
        if index_id != PINNED_OLD140_INDEX_ID:
            raise _error("Family-35 strict corpus is not the pinned frozen-140 frontier")
    else:
        raise _error("Family-35 historical comparator policy is invalid")


def _crop_rgb_sha256(pixmap: fitz.Pixmap, bbox: Sequence[int]) -> str:
    x0, y0, x1, y1 = bbox
    if (
        pixmap.alpha
        or pixmap.n != 3
        or not (0 <= x0 < x1 <= pixmap.width)
        or not (0 <= y0 < y1 <= pixmap.height)
    ):
        raise _error("Family-35 source-repair crop boundary drifted")
    samples = memoryview(pixmap.samples)
    row_width = (x1 - x0) * pixmap.n
    digest = sha256()
    for y in range(y0, y1):
        start = y * pixmap.stride + x0 * pixmap.n
        digest.update(samples[start : start + row_width])
    return digest.hexdigest()


def authenticate_capital_contribution_dividend_income_source_repairs_v1(
    *, repairs: Sequence[Mapping[str, Any]], source_pdf_root: Path
) -> list[dict[str, Any]]:
    """Authenticate PDF bytes, full render, table crop, and every cell crop."""

    root = source_pdf_root.resolve()
    if source_pdf_root.is_symlink() or not root.is_dir():
        raise _error("Family-35 source-PDF root is unavailable")
    payloads: dict[tuple[str, str], bytes] = {}
    rendered: dict[tuple[str, int], fitz.Pixmap] = {}
    checked = []
    for repair in repairs:
        source = repair["source_binding"]
        logical_name = source["source_logical_name"]
        path = (root / logical_name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise _error("Family-35 source-repair PDF path is unavailable")
        source_key = (logical_name, source["source_sha256"])
        payload = payloads.get(source_key)
        if payload is None:
            payload = path.read_bytes()
            if (
                len(payload) != source["source_size_bytes"]
                or sha256(payload).hexdigest() != source["source_sha256"]
            ):
                raise _error("Family-35 source-repair PDF bytes drifted")
            payloads[source_key] = payload
        page_key = (logical_name, source["physical_page"])
        pixmap = rendered.get(page_key)
        if pixmap is None:
            try:
                with fitz.open(stream=payload, filetype="pdf") as document:
                    page_index = source["physical_page"] - 1
                    if not 0 <= page_index < len(document):
                        raise _error("Family-35 repair page lies outside its PDF")
                    pixmap = document[page_index].get_pixmap(
                        dpi=source["render_dpi"],
                        colorspace=fitz.csRGB,
                        alpha=False,
                    )
            except (RuntimeError, ValueError) as exc:
                raise _error("Family-35 source-repair PDF cannot be rendered") from exc
            rendered[page_key] = pixmap
        image = pixmap.tobytes("png")
        actual = {
            "image_sha256": sha256(image).hexdigest(),
            "image_size_bytes": len(image),
            "media_type": "image/png",
            "pixel_height": pixmap.height,
            "pixel_width": pixmap.width,
            "render_dpi": source["render_dpi"],
        }
        if any(source[key] != value for key, value in actual.items()):
            raise _error("Family-35 source-repair page render drifted")
        visual = repair["visual_evidence"]
        if (
            _crop_rgb_sha256(pixmap, visual["table_crop_bbox_pixels_xyxy"])
            != visual["table_crop_rgb_sha256"]
        ):
            raise _error("Family-35 source-repair table crop drifted")
        for item in [*repair["cell_repairs"], *repair["row_repairs"]]:
            if (
                _crop_rgb_sha256(pixmap, item["crop_bbox_pixels_xyxy"])
                != item["crop_rgb_sha256"]
            ):
                raise _error("Family-35 source-repair cell crop drifted")
        checked.append(canonical_clone_v1(repair))
    return checked


def _compile_specs_v1() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    topology = generic._json(TOPOLOGY_SPEC_PATH)
    evaluation = generic._json(EVALUATION_SPEC_PATH)
    schema = generic._json(SCHEMA_BINDING_SPEC_PATH)
    compiled = compile_gemini_json_capital_contribution_dividend_income_family_specs_v1(
        topology,
        evaluation,
        schema,
        adapter_spec=generic._json(ADAPTER_SPEC_PATH),
        source_repair_spec=generic._json(SOURCE_REPAIR_PATH),
    )
    if compiled.get("topology", {}).get("family_id") != FAMILY_ID:
        raise _error("Family-35 runner received another family")
    overlay = compiled["capital_contribution_dividend_income_source_repair_overlay"]
    if (
        len(overlay["repairs"]) != REGISTERED_SOURCE_REPAIR_COUNT
        or sum(len(item["cell_repairs"]) for item in overlay["repairs"])
        != REGISTERED_SOURCE_REPAIR_CELL_COUNT
    ):
        raise _error("Family-35 registered source-repair denominator drifted")
    return topology, evaluation, schema, compiled


def _query_indexed_v1(
    database: Path,
    *,
    selected_ids: Sequence[str],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[int, dict[str, dict[str, Any]]]]:
    generic_indexed = query_selected_multitable_hierarchical_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled_specs,
    )
    pages = generic._load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=generic_indexed["selected_page_axis"],
    )
    indexed = (
        adapt_gemini_json_capital_contribution_dividend_income_indexed_query_evidence_v1(
            indexed_query_evidence=generic_indexed,
            page_json_by_document=pages,
            compiled_specs=compiled_specs,
        )
    )
    return indexed, pages


def replay_capital_contribution_dividend_income_trials_from_source_v1(
    *,
    source_page_database: Path,
    selected_page_json_version_ids: tuple[str, ...],
    compiled_specs: Mapping[str, Any] | None = None,
    indexed_query_evidence: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Re-query and replay every Family-35 candidate from immutable JSON."""

    _topology, _evaluation, _schema, compiled = _compile_specs_v1()
    indexed, pages = _query_indexed_v1(
        source_page_database,
        selected_ids=selected_page_json_version_ids,
        compiled_specs=compiled,
    )
    if indexed_query_evidence is not None and not same_typed_json_v1(
        indexed, indexed_query_evidence
    ):
        raise _error("Family-35 indexed query evidence does not replay")
    candidates = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        receipt = build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1(
            regions, cluster=cluster
        )
        candidate = evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1(
            regions=regions,
            page_json_by_version=pages[ordinal],
            compiled_specs=compiled,
            query_receipt=receipt,
        )
        candidates[ordinal] = (
            validate_gemini_json_capital_contribution_dividend_income_family_candidate_replay_v1(
                candidate,
                regions=regions,
                page_json_by_version=pages[ordinal],
                compiled_specs=compiled,
                query_receipt=receipt,
            )
        )
    return generic._trials(indexed=indexed, candidates_by_ordinal=candidates)


def _semantic_trial_axis_v1(sweep: Mapping[str, Any]) -> list[dict[str, Any]]:
    if sweep.get("family_id") != FAMILY_ID or type(sweep.get("trials")) is not list:
        raise _error("Family-35 semantic sweep axis is invalid")
    return [
        {
            "mappings": [
                {key: value for key, value in mapping.items() if key != "item_mapping_id"}
                for mapping in trial["mappings"]
            ],
            "reasons": trial["reasons"],
            "source_logical_name": trial["source_logical_name"],
            "source_sha256": trial["source_sha256"],
            "status": trial["status"],
        }
        for trial in sweep["trials"]
    ]


def _historical_oracle_material_v1(
    *, compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Mapping[str, Any]]]:
    refs = []
    rows = []
    by_source = {}
    for ref_index, (reference, artifact) in enumerate(
        generic._historical_oracles(compiled_specs=compiled_specs)
    ):
        refs.append({**reference, "expected_trial_count": len(artifact["trials"])})
        for trial in artifact["trials"]:
            source_sha256 = trial.get("source_pdf_sha256")
            if type(source_sha256) is not str or source_sha256 in by_source:
                raise _error("Family-35 historical source identity is invalid or duplicate")
            by_source[source_sha256] = trial
            rows.append(
                {"oracle_ref_index": ref_index, "source_sha256": source_sha256}
            )
    return refs, rows, by_source


def _oracle_integer_coefficients_v1(mapping: Mapping[str, Any]) -> list[int] | None:
    values = mapping.get("values")
    if type(values) is not list:
        return None
    by_role = {}
    for value in values:
        if type(value) is not dict or type(value.get("normalized_value")) is not int:
            return None
        role = value.get("period_role")
        if type(role) is not str:
            role = value.get("axis_role")
        if role == "CURRENT":
            role = "CURRENT_PERIOD"
        elif role == "COMPARATIVE":
            role = "COMPARATIVE_PERIOD"
        if role not in {"CURRENT_PERIOD", "COMPARATIVE_PERIOD"} or role in by_role:
            return None
        by_role[role] = value["normalized_value"]
    if "CURRENT_PERIOD" not in by_role:
        return None
    result = [by_role["CURRENT_PERIOD"]]
    if "COMPARATIVE_PERIOD" in by_role:
        result.append(by_role["COMPARATIVE_PERIOD"])
    return result


def _strict_historical_comparator_v1(
    *, trials: Sequence[dict[str, Any]], compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Run the existing comparator with one explicit legacy-blank projection.

    The annual HDB oracle encoded a comparative blank as numeric zero.  The
    current mapping contract correctly retains that lane as ``null``.  A
    comparator-only clone supplies the legacy zero solely to replay the pinned
    oracle; the released sweep remains unchanged and is independently checked
    by the source-observation contract.
    """

    refs, rows, oracle_by_source = _historical_oracle_material_v1(
        compiled_specs=compiled_specs
    )
    trial_by_source = {item["source_sha256"]: item for item in trials}
    projected_trials = canonical_clone_v1(list(trials))
    projected_by_source = {item["source_sha256"]: item for item in projected_trials}
    projections = []
    for source_sha256, oracle_trial in oracle_by_source.items():
        trial = trial_by_source[source_sha256]
        projected = projected_by_source[source_sha256]
        current_by_id = {item["report_norm_id"]: item for item in trial["mappings"]}
        projected_candidates = projected.get("candidates")
        if (
            type(projected_candidates) is not list
            or len(projected_candidates) != 1
            or projected_candidates[0].get("candidate_id")
            != projected.get("selected_candidate_id")
        ):
            raise _error("Family-35 strict selected candidate axis drifted")
        projected_by_id = {
            item["report_norm_id"]: item
            for item in projected_candidates[0]["mappings"]
        }
        projected_trial_by_id = {
            item["report_norm_id"]: item for item in projected["mappings"]
        }
        for historical in oracle_trial.get("verified_mappings", []):
            binding = historical.get("schema_binding")
            report_norm_id = binding.get("report_norm_id") if type(binding) is dict else None
            expected = _oracle_integer_coefficients_v1(historical)
            current = current_by_id.get(report_norm_id)
            target = projected_by_id.get(report_norm_id)
            if expected is None or type(current) is not dict or type(target) is not dict:
                continue
            for lane, expected_value in enumerate(expected):
                if lane >= len(current["values"]):
                    continue
                cell = current["values"][lane]
                if cell.get("coefficient") is not None:
                    continue
                if (
                    expected_value != 0
                    or cell.get("source_text") is not None
                    or cell.get("state") != "BLANK_SOURCE_CELL"
                ):
                    raise _error("Family-35 historical oracle conflicts with a source blank")
                target["values"][lane]["coefficient"] = 0
                target["values"][lane]["state"] = (
                    "HISTORICAL_COMPARATOR_ONLY_LEGACY_BLANK_ZERO_PROJECTION"
                )
                projected_trial_by_id[report_norm_id]["values"][lane]["coefficient"] = 0
                projected_trial_by_id[report_norm_id]["values"][lane]["state"] = (
                    "HISTORICAL_COMPARATOR_ONLY_LEGACY_BLANK_ZERO_PROJECTION"
                )
                projections.append(
                    {
                        "current_state": "BLANK_SOURCE_CELL",
                        "historical_value": 0,
                        "lane": lane,
                        "policy": (
                            "COMPARATOR_ONLY_LEGACY_ZERO_REPLAY_RELEASE_MAPPING_"
                            "REMAINS_NULL"
                        ),
                        "report_norm_id": report_norm_id,
                        "source_sha256": source_sha256,
                    }
                )
    comparator, generic_refs = generic._historical_comparator_axis(
        trials=projected_trials, compiled_specs=compiled_specs
    )
    primary_root_additions = []
    for item in comparator:
        if item.get("disposition") == "EXACT":
            continue
        source_sha256 = item.get("source_sha256")
        oracle_trial = oracle_by_source.get(source_sha256)
        current_trial = trial_by_source.get(source_sha256)
        candidates = (
            current_trial.get("candidates") if type(current_trial) is dict else None
        )
        candidate = (
            candidates[0]
            if type(candidates) is list and len(candidates) == 1
            else None
        )
        mappings = candidate.get("mappings") if type(candidate) is dict else None
        adapter = (
            candidate.get("closure_receipt", {}).get(
                "capital_contribution_dividend_income_adapter_receipt"
            )
            if type(candidate) is dict
            else None
        )
        primary = (
            adapter.get("primary_root_projection_receipt")
            if type(adapter) is dict
            else None
        )
        if (
            item.get("record_kind") != "DOCUMENT_DISPOSITION"
            or item.get("expected_status")
            != "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
            or item.get("actual_status")
            != "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"
            or type(oracle_trial) is not dict
            or oracle_trial.get("verified_mappings") != []
            or type(mappings) is not list
            or len(mappings) != 1
            or mappings[0].get("report_norm_id") != 1198
            or mappings[0].get("role") != "FAMILY_ROOT_TOTAL"
            or mappings[0].get("state")
            != "SOURCE_VISIBLE_PRIMARY_STATEMENT_EXACT_RESULT"
            or type(primary) is not dict
            or primary.get("statement_type_before") != "INCOME_STATEMENT"
            or primary.get("policy")
            != (
                "UNIQUE_EXACT_INCOME_STATEMENT_ROOT_WHEN_DISCLOSURE_NOT_"
                "OBSERVED_PRIVATE_SEMANTIC_PROJECTION"
            )
        ):
            continue
        item["disposition"] = "EVIDENCE_SAFE_VISIBLE_PRIMARY_INCOME_STATEMENT_ROOT_ADDITION"
        primary_root_additions.append(
            {
                "current_mapping": canonical_clone_v1(mappings[0]),
                "historical_status": item["expected_status"],
                "primary_root_projection_receipt": canonical_clone_v1(primary),
                "source_sha256": source_sha256,
            }
        )
    accepted_dispositions = {
        "EXACT",
        "EVIDENCE_SAFE_VISIBLE_PRIMARY_INCOME_STATEMENT_ROOT_ADDITION",
    }
    if (
        generic_refs != [
            {key: value for key, value in reference.items() if key != "expected_trial_count"}
            for reference in refs
        ]
        or any(item.get("disposition") not in accepted_dispositions for item in comparator)
        or len(comparator) != PINNED_STRICT_HISTORICAL_COMPARATOR_RECORD_COUNT
        or len(projections) != PINNED_STRICT_LEGACY_BLANK_ZERO_PROJECTION_COUNT
        or len(primary_root_additions)
        != PINNED_STRICT_VISIBLE_PRIMARY_ROOT_ADDITION_COUNT
    ):
        raise _error(
            "Family-35 strict historical comparator drifted: "
            f"records={len(comparator)}, projections={len(projections)}, "
            f"unaccepted={sum(item.get('disposition') not in accepted_dispositions for item in comparator)}, "
            f"refs_equal={generic_refs == [{key: value for key, value in reference.items() if key != 'expected_trial_count'} for reference in refs]}, "
            f"mismatches={[item for item in comparator if item.get('disposition') not in accepted_dispositions]}"
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in comparator:
        grouped[item["source_sha256"]].append(item)

    def compare(oracle: Mapping[str, Any], current: Mapping[str, Any]) -> Mapping[str, Any]:
        source_sha256 = oracle["source_sha256"]
        if current.get("source_sha256") != source_sha256:
            raise _error("Family-35 strict source join drifted")
        axis = grouped.get(source_sha256, [])
        if not axis or any(
            item.get("disposition") not in accepted_dispositions for item in axis
        ):
            raise _error("Family-35 strict source comparison is not exact")
        return {
            "axis": canonical_clone_v1(axis),
            "disposition": EXACT_HISTORICAL_COMPARISON,
            "legacy_blank_zero_projections": [
                item for item in projections if item["source_sha256"] == source_sha256
            ],
            "visible_primary_root_additions": [
                item
                for item in primary_root_additions
                if item["source_sha256"] == source_sha256
            ],
        }

    return comparator, refs, rows, {
        "callback": compare,
        "primary_root_additions": primary_root_additions,
        "projections": projections,
    }


def _historical_policy_receipt_v1(
    *,
    policy: str,
    index: Mapping[str, Any],
    selected_ids: Sequence[str],
    indexed: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    refs, rows, _oracle = _historical_oracle_material_v1(compiled_specs=compiled_specs)
    comparator = []
    projections = []
    primary_root_additions = []
    callback = None
    if policy == STRICT_RELEASE:
        comparator, strict_refs, strict_rows, strict = _strict_historical_comparator_v1(
            trials=trials, compiled_specs=compiled_specs
        )
        if strict_refs != refs or strict_rows != rows:
            raise _error("Family-35 strict historical oracle axis drifted")
        callback = strict["callback"]
        projections = strict["projections"]
        primary_root_additions = strict["primary_root_additions"]
    source_by_ordinal = {
        item["document_ordinal"]: item["source_sha256"]
        for item in indexed["selected_document_axis"]
    }
    candidate_sources = [
        source_by_ordinal[item["document_ordinal"]]
        for item in indexed["accepted_clusters"]
    ]
    replay_sources = [item["source_sha256"] for item in trials if item["candidates"]]
    receipt = audit_historical_comparator_policy_v1(
        policy=policy,
        pinned_oracle_refs=refs,
        normalized_oracle_rows=rows,
        current_manifest_index_id=index["corpus_manifest_index_id"],
        current_manifest_source_sha256s=[item["source_sha256"] for item in index["documents"]],
        current_manifest_page_json_version_ids=selected_ids,
        current_trials=trials,
        current_candidate_source_sha256s=candidate_sources,
        current_replay_source_sha256s=replay_sources,
        current_selected_page_json_version_ids=selected_ids,
        strict_compare=callback,
    )
    expected = (
        EXACT_HISTORICAL_COMPARISON
        if policy == STRICT_RELEASE
        else NOT_APPLICABLE_DISJOINT_CORPUS
    )
    if receipt.get("disposition") != expected:
        raise _error("Family-35 historical policy disposition drifted")
    return receipt, comparator, projections, primary_root_additions


def _repair_application_receipt_v1(
    *, sweep: Mapping[str, Any], compiled_specs: Mapping[str, Any]
) -> dict[str, Any]:
    corpus_sources = {item["source_sha256"] for item in sweep["trials"]}
    expected = sorted(
        item["repair_id"]
        for item in compiled_specs[
            "capital_contribution_dividend_income_source_repair_overlay"
        ]["repairs"]
        if item["source_binding"]["source_sha256"] in corpus_sources
    )
    applied = []
    for trial in sweep["trials"]:
        for candidate in trial["candidates"]:
            adapter = candidate.get("closure_receipt", {}).get(
                "capital_contribution_dividend_income_adapter_receipt"
            )
            if type(adapter) is not dict:
                continue
            applied.extend(
                item["repair_id"] for item in adapter["source_repair_receipts"]
            )
    applied.sort()
    material = {
        "applied_repair_ids": applied,
        "expected_repair_ids": expected,
        "overlay_id": compiled_specs[
            "capital_contribution_dividend_income_source_repair_overlay"
        ]["overlay_id"],
        "status": "PASS" if applied == expected and len(applied) == len(set(applied)) else "FAILED",
    }
    if material["status"] != "PASS":
        raise _error("Family-35 source-repair application is not exhaustive and unique")
    return {
        **material,
        "receipt_id": "gjccdifarunv1:repair-application:"
        + canonical_json_sha256_v1(material),
    }


def _audit_axes_v1(sweep: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    axes: dict[str, list[dict[str, Any]]] = {
        "clusters": [],
        "equations": [],
        "mappings": [],
        "partial_root_projections": [],
        "primary_root_projections": [],
        "source_only_rows": [],
        "source_repairs": [],
        "standalone_long_term_leaf_retry_receipts": [],
        "unresolved": [],
        "vnd_retry_receipts": [],
        "vnd_zero_decimal_projections": [],
    }
    for trial in sweep["trials"]:
        document = {
            "document_ordinal": trial["document_ordinal"],
            "source_logical_name": trial["source_logical_name"],
            "source_sha256": trial["source_sha256"],
        }
        if trial["status"].startswith("UNRESOLVED"):
            axes["unresolved"].append({**document, "reasons": trial["reasons"]})
        for candidate in trial["candidates"]:
            axes["clusters"].append(
                {**document, "component_regions": candidate["component_regions"]}
            )
            for mapping in candidate["mappings"]:
                axes["mappings"].append(
                    {
                        **document,
                        "report_norm_id": mapping["report_norm_id"],
                        "role": mapping["role"],
                        "unit": mapping["unit"],
                        "values": canonical_clone_v1(mapping["values"]),
                    }
                )
            closure = candidate["closure_receipt"]
            for equation in closure["equations"]:
                axes["equations"].append({**document, "equation": equation})
            for source_only in closure["source_only_unmapped_rows"]:
                axes["source_only_rows"].append({**document, "row": source_only})
            adapter = closure.get(
                "capital_contribution_dividend_income_adapter_receipt"
            )
            if type(adapter) is not dict:
                continue
            projection = adapter["primary_root_projection_receipt"]
            if projection is not None:
                axes["primary_root_projections"].append({**document, **projection})
            partial = adapter["partial_root_projection_receipt"]
            if partial is not None:
                axes["partial_root_projections"].append({**document, **partial})
            retry = adapter["vnd_retry_receipt"]
            if retry is not None:
                axes["vnd_retry_receipts"].append({**document, **retry})
            standalone = adapter["standalone_long_term_leaf_retry_receipt"]
            if standalone is not None:
                axes["standalone_long_term_leaf_retry_receipts"].append(
                    {**document, **standalone}
                )
            axes["source_repairs"].extend(
                {**document, **item} for item in adapter["source_repair_receipts"]
            )
            axes["vnd_zero_decimal_projections"].extend(
                {**document, **item}
                for item in adapter["vnd_zero_decimal_projections"]
            )
    return axes


def build_capital_contribution_dividend_income_audit_v1(
    *,
    sweep: Mapping[str, Any],
    historical_policy_receipt: Mapping[str, Any],
    historical_comparator: Sequence[Mapping[str, Any]],
    legacy_blank_zero_projections: Sequence[Mapping[str, Any]],
    visible_primary_root_additions: Sequence[Mapping[str, Any]],
    repair_application: Mapping[str, Any],
    repair_authentication: Sequence[Mapping[str, Any]],
    implementation_refs: Sequence[Mapping[str, Any]],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    axes = _audit_axes_v1(sweep)
    axes["historical_comparator"] = canonical_clone_v1(list(historical_comparator))
    material = {
        "axes": axes,
        "axis_counts": {key: len(value) for key, value in axes.items()},
        "axis_sha256": {
            key: canonical_json_sha256_v1(value) for key, value in axes.items()
        },
        "family_id": FAMILY_ID,
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": canonical_clone_v1(
            historical_policy_receipt
        ),
        "implementation_refs": canonical_clone_v1(list(implementation_refs)),
        "legacy_blank_zero_comparator_projections": canonical_clone_v1(
            list(legacy_blank_zero_projections)
        ),
        "metrics": canonical_clone_v1(sweep["metrics"]),
        "repair_application": canonical_clone_v1(repair_application),
        "repair_authentication_axis_sha256": canonical_json_sha256_v1(
            repair_authentication
        ),
        "repair_authentication_count": len(repair_authentication),
        "source_observation_contract": validate_source_observation_mapping_contract_v1(
            sweep
        ),
        "spec_refs": canonical_clone_v1(spec_refs),
        "sweep_id": sweep["sweep_id"],
        "visible_primary_income_statement_root_additions": canonical_clone_v1(
            list(visible_primary_root_additions)
        ),
    }
    return {
        **material,
        "audit_id": "gjccdifav1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_capital_contribution_dividend_income_audit_v1(
    value: Any,
) -> dict[str, Any]:
    if type(value) is not dict or value.get("format_version") != AUDIT_FORMAT_VERSION:
        raise _error("Family-35 audit is invalid")
    axes = value.get("axes")
    if type(axes) is not dict or value.get("axis_counts") != {
        key: len(axis) for key, axis in axes.items()
    } or value.get("axis_sha256") != {
        key: canonical_json_sha256_v1(axis) for key, axis in axes.items()
    }:
        raise _error("Family-35 audit axis seals drifted")
    material = {key: item for key, item in value.items() if key != "audit_id"}
    if value.get("audit_id") != "gjccdifav1:audit:" + canonical_json_sha256_v1(
        material
    ):
        raise _error("Family-35 audit identity does not replay")
    if value.get("source_observation_contract", {}).get("status") != "PASS":
        raise _error("Family-35 audit source-observation contract failed")
    policy = value.get("historical_comparator_policy_receipt", {}).get("policy")
    comparator = axes.get("historical_comparator")
    legacy = value.get("legacy_blank_zero_comparator_projections")
    additions = value.get("visible_primary_income_statement_root_additions")
    if (
        type(comparator) is not list
        or type(legacy) is not list
        or type(additions) is not list
        or value.get("repair_authentication_count") != REGISTERED_SOURCE_REPAIR_COUNT
        or value.get("repair_application", {}).get("status") != "PASS"
    ):
        raise _error("Family-35 audit source and comparator gates drifted")
    if policy == STRICT_RELEASE:
        if (
            value.get("metrics") != PINNED_OLD140_METRICS
            or len(comparator) != PINNED_STRICT_HISTORICAL_COMPARATOR_RECORD_COUNT
            or len(legacy) != PINNED_STRICT_LEGACY_BLANK_ZERO_PROJECTION_COUNT
            or len(additions) != PINNED_STRICT_VISIBLE_PRIMARY_ROOT_ADDITION_COUNT
            or sum(
                item.get("disposition")
                == "EVIDENCE_SAFE_VISIBLE_PRIMARY_INCOME_STATEMENT_ROOT_ADDITION"
                for item in comparator
            )
            != PINNED_STRICT_VISIBLE_PRIMARY_ROOT_ADDITION_COUNT
        ):
            raise _error("Family-35 strict audit comparator gates drifted")
    elif policy == DISJOINT_EXPANSION:
        if (
            value.get("metrics") != PINNED_FULL271_METRICS
            or comparator
            or legacy
            or additions
        ):
            raise _error("Family-35 expansion audit comparator gates drifted")
    else:
        raise _error("Family-35 audit comparator policy is invalid")
    return canonical_clone_v1(value)


def _strict_regression_gate_v1(sweep: Mapping[str, Any]) -> None:
    semantic_axis = _semantic_trial_axis_v1(sweep)
    if (
        sweep.get("corpus_manifest_index_id") != PINNED_OLD140_INDEX_ID
        or sweep.get("metrics") != PINNED_OLD140_METRICS
        or canonical_json_sha256_v1(semantic_axis)
        != PINNED_OLD140_SEMANTIC_TRIAL_AXIS_SHA256
    ):
        raise _error("Family-35 frozen-140 strict semantic regression drifted")


def _implementation_refs_v1() -> list[dict[str, Any]]:
    paths = (
        Path(__file__).resolve(),
        ADAPTER_PATH,
        SHARED_EVALUATOR_PATH,
        SHARED_RUNNER_PATH,
        ROOT / "src/bctc_ai/evaluation/historical_comparator_policy_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        TOPOLOGY_SPEC_PATH,
        EVALUATION_SPEC_PATH,
        SCHEMA_BINDING_SPEC_PATH,
        ADAPTER_SPEC_PATH,
        SOURCE_REPAIR_PATH,
    )
    return [generic._file_ref(path, root=ROOT) for path in paths]


def run(args: argparse.Namespace) -> dict[str, Any]:
    _assert_shared_pins_v1()
    index = validate_current_corpus_manifest_index_v1(generic._json(args.corpus_index))
    _assert_corpus_policy_v1(index, policy=args.historical_comparator_policy)
    artifact_root = args.artifact_root.resolve()
    database = generic._content_ref(artifact_root, index["database_ref"])
    selected_ids = generic._selected_page_axis(index=index, artifact_root=artifact_root)
    topology, evaluation, schema, compiled = _compile_specs_v1()
    overlay = compiled[
        "capital_contribution_dividend_income_source_repair_overlay"
    ]
    authenticated_repairs = (
        authenticate_capital_contribution_dividend_income_source_repairs_v1(
            repairs=overlay["repairs"], source_pdf_root=args.source_pdf_root
        )
    )
    if not same_typed_json_v1(authenticated_repairs, overlay["repairs"]):
        raise _error("Family-35 repair authentication axis drifted")
    with generic._authenticated_sqlite_snapshot(
        database, reference=index["database_ref"]
    ) as database_guard:
        indexed, pages = _query_indexed_v1(
            database_guard.path,
            selected_ids=selected_ids,
            compiled_specs=compiled,
        )
        candidates = {}
        for cluster in indexed["accepted_clusters"]:
            ordinal = cluster["document_ordinal"]
            regions = cluster["component_regions"]
            receipt = (
                build_gemini_json_capital_contribution_dividend_income_region_query_receipt_v1(
                    regions, cluster=cluster
                )
            )
            candidate = (
                evaluate_gemini_json_capital_contribution_dividend_income_family_cluster_v1(
                    regions=regions,
                    page_json_by_version=pages[ordinal],
                    compiled_specs=compiled,
                    query_receipt=receipt,
                )
            )
            candidates[ordinal] = (
                validate_gemini_json_capital_contribution_dividend_income_family_candidate_replay_v1(
                    candidate,
                    regions=regions,
                    page_json_by_version=pages[ordinal],
                    compiled_specs=compiled,
                    query_receipt=receipt,
                )
            )
        trials = generic._trials(indexed=indexed, candidates_by_ordinal=candidates)
        sweep = build_gemini_json_flat_family_sweep_v1(
            corpus_manifest_index_id=index["corpus_manifest_index_id"],
            topology_spec=topology,
            evaluation_spec=evaluation,
            schema_binding_spec=schema,
            trials=trials,
            indexed_query_evidence=indexed,
        )
        validate_gemini_json_flat_family_sweep_v1(sweep)
        validate_source_observation_mapping_contract_v1(sweep)
        replayed = replay_capital_contribution_dividend_income_trials_from_source_v1(
            source_page_database=database_guard.path,
            selected_page_json_version_ids=tuple(selected_ids),
            indexed_query_evidence=indexed,
        )
        if not same_typed_json_v1(replayed, trials):
            raise _error("Family-35 source replay returned a different trial axis")
        database_guard.validate()

    expected_metrics = (
        PINNED_OLD140_METRICS
        if args.historical_comparator_policy == STRICT_RELEASE
        else PINNED_FULL271_METRICS
    )
    if sweep["metrics"] != expected_metrics:
        raise _error(
            "Family-35 pinned corpus metrics drifted: actual="
            + json.dumps(sweep["metrics"], sort_keys=True)
            + " expected="
            + json.dumps(expected_metrics, sort_keys=True)
        )
    if args.historical_comparator_policy == STRICT_RELEASE:
        _strict_regression_gate_v1(sweep)
    (
        policy_receipt,
        comparator,
        legacy_projections,
        visible_primary_root_additions,
    ) = _historical_policy_receipt_v1(
        policy=args.historical_comparator_policy,
        index=index,
        selected_ids=selected_ids,
        indexed=indexed,
        trials=trials,
        compiled_specs=compiled,
    )
    repair_application = _repair_application_receipt_v1(
        sweep=sweep, compiled_specs=compiled
    )
    implementation_refs = _implementation_refs_v1()
    spec_refs = {
        "adapter": generic._file_ref(ADAPTER_SPEC_PATH, root=ROOT),
        "evaluation": generic._file_ref(EVALUATION_SPEC_PATH, root=ROOT),
        "schema_binding": generic._file_ref(SCHEMA_BINDING_SPEC_PATH, root=ROOT),
        "source_repair": generic._file_ref(SOURCE_REPAIR_PATH, root=ROOT),
        "topology": generic._file_ref(TOPOLOGY_SPEC_PATH, root=ROOT),
    }
    audit = build_capital_contribution_dividend_income_audit_v1(
        sweep=sweep,
        historical_policy_receipt=policy_receipt,
        historical_comparator=comparator,
        legacy_blank_zero_projections=legacy_projections,
        visible_primary_root_additions=visible_primary_root_additions,
        repair_application=repair_application,
        repair_authentication=authenticated_repairs,
        implementation_refs=implementation_refs,
        spec_refs=spec_refs,
    )
    validate_capital_contribution_dividend_income_audit_v1(audit)
    audit_output = args.output.with_suffix(".audit.json")
    generic._write_once(args.output, sweep)
    generic._write_once(audit_output, audit)
    return {
        "audit_id": audit["audit_id"],
        "audit_output": str(audit_output),
        "axis_counts": audit["axis_counts"],
        "axis_sha256": audit["axis_sha256"],
        "disposition": "SUCCEEDED",
        "historical_comparator_policy": args.historical_comparator_policy,
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "sweep_id": sweep["sweep_id"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--source-pdf-root", type=Path, required=True)
    parser.add_argument(
        "--historical-comparator-policy",
        choices=(STRICT_RELEASE, DISJOINT_EXPANSION),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
