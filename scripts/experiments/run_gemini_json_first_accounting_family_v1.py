#!/usr/bin/env python3
"""Run one declarative accounting family over the frozen Gemini JSON corpus."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (  # noqa: E402
    normalize_vietnamese_anchor_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    evaluate_gemini_json_flat_family_table_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
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
    load_page_json_versions_v1,
    query_selected_family_anchor_hits_v1,
    query_selected_family_anchor_regions_v1,
)


class RunGeminiJsonFirstAccountingFamilyV1Error(RuntimeError):
    """The frozen corpus, family specs, or output frontier drifted."""


def _error(message: str) -> RunGeminiJsonFirstAccountingFamilyV1Error:
    return RunGeminiJsonFirstAccountingFamilyV1Error(message)


def _json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise _error(f"JSON input is absent or not regular: {path}")
    try:
        value = json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"JSON input is invalid: {path}") from exc
    if type(value) is not dict:
        raise _error("JSON input is not one object")
    return value


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _file_ref(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise _error(f"traceable input is absent or not regular: {path}")
    resolved = path.resolve()
    logical = str(resolved.relative_to(root.resolve())) if root is not None else str(resolved)
    return {
        "path": logical,
        "sha256": _sha256(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def _content_ref(root: Path, reference: dict[str, Any]) -> Path:
    if type(reference) is not dict or set(reference) != {"path", "sha256", "size_bytes"}:
        raise _error("frozen corpus content reference fields drifted")
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise _error("frozen corpus content reference escapes its root")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size != reference["size_bytes"]
        or _sha256(path) != reference["sha256"]
    ):
        raise _error("frozen corpus content reference does not authenticate")
    return path


def _node_index(identifier: Any, prefix: str, limit: int) -> int:
    if type(identifier) is not str or not identifier.startswith(prefix):
        raise _error("Gemini JSON query node ID is invalid")
    suffix = identifier.removeprefix(prefix)
    if not suffix.isdigit() or suffix.startswith("0"):
        raise _error("Gemini JSON query node ID is invalid")
    index = int(suffix) - 1
    if not 0 <= index < limit:
        raise _error("Gemini JSON query node ID is out of range")
    return index


def _hit_has_explicit_parent(
    hit: dict[str, Any],
    *,
    allow_row_parent: bool,
    page_json: dict[str, Any],
    parent_aliases: list[str],
) -> bool:
    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("Gemini JSON near-hit page has no section axis")
    section = sections[_node_index(hit["section_id"], "s", len(sections))]
    tables = section.get("tables")
    if type(tables) is not list:
        raise _error("Gemini JSON near-hit section has no table axis")
    table = tables[_node_index(hit["table_id"], "t", len(tables))]
    title = " ".join(
        value
        for value in (section.get("title_exact"), table.get("title_exact"))
        if type(value) is str and value
    )
    folded = normalize_vietnamese_anchor_v1(title)
    if any(alias in folded for alias in parent_aliases):
        return True
    if not allow_row_parent:
        return False
    return any(
        any(
            normalize_vietnamese_anchor_v1(value) == alias
            or normalize_vietnamese_anchor_v1(value).startswith(alias + " ")
            for alias in parent_aliases
        )
        for row in table.get("rows", [])
        for value in [row.get("label_exact"), *row.get("hierarchy_path_exact", [])]
        if type(value) is str and value
    )


def _normalized_column_axis(mapping: dict[str, Any]) -> tuple[tuple[str, str], ...] | None:
    columns = mapping.get("columns")
    if type(columns) is not list or not columns:
        return None
    result = []
    for column in columns:
        if type(column) is not dict or type(column.get("header_path_exact")) is not list:
            return None
        header = " ".join(value for value in column["header_path_exact"] if type(value) is str)
        result.append((column.get("value_kind"), normalize_vietnamese_anchor_v1(header)))
    return tuple(result)


def _net_adjusted_presentation_bundle(
    ready: list[dict[str, Any]], *, compiled_specs: dict[str, Any]
) -> dict[str, Any] | None:
    """Compose one net table with adjacent disjoint gross classification views."""

    root_mapping_role = compiled_specs["topology"]["parent"]["role"]
    root_result_role = compiled_specs.get("family_result_role")
    if type(root_result_role) is not str or len(ready) < 2:
        return None
    root_specs = [
        equation
        for equation in compiled_specs.get("equations", [])
        if equation.get("result_role") == root_result_role
    ]
    if len(root_specs) != 1:
        return None
    declared_root_components = {
        role
        for alternative in root_specs[0]["component_role_alternatives"]
        for role in alternative["component_roles"]
    }
    details = []
    for candidate in ready:
        if not {
            "candidate_id",
            "closure_receipt",
            "mappings",
            "page_json_version_id",
            "physical_page",
            "reasons",
            "section_id",
            "status",
            "table_id",
        } <= set(candidate):
            return None
        roots = [
            mapping for mapping in candidate["mappings"] if mapping["role"] == root_mapping_role
        ]
        equations = candidate["closure_receipt"].get("equations")
        if len(roots) != 1 or type(equations) is not list:
            return None
        root_equations = [
            equation for equation in equations if equation.get("result_role") == root_result_role
        ]
        if len(root_equations) != 1:
            return None
        if not set(root_equations[0].get("component_roles", [])) <= declared_root_components:
            return None
        receipts = {
            equation.get("result_role"): equation
            for equation in equations
            if type(equation) is dict and type(equation.get("result_role")) is str
        }
        adjustment_roles = []
        adjustment_coefficients = None
        for role in root_equations[0].get("component_roles", []):
            receipt = receipts.get(role)
            coefficients = receipt.get("result_coefficients") if receipt is not None else None
            if (
                type(coefficients) is list
                and coefficients
                and all(type(value) is int and value <= 0 for value in coefficients)
                and any(value < 0 for value in coefficients)
            ):
                adjustment_roles.append(role)
                if adjustment_coefficients is None:
                    adjustment_coefficients = [0] * len(coefficients)
                if len(coefficients) != len(adjustment_coefficients):
                    return None
                adjustment_coefficients = [
                    total + value
                    for total, value in zip(adjustment_coefficients, coefficients, strict=True)
                ]
        details.append(
            {
                "adjustment_coefficients": adjustment_coefficients,
                "adjustment_roles": adjustment_roles,
                "candidate": candidate,
                "column_axis": _normalized_column_axis(roots[0]),
                "root": roots[0],
                "values": [value["coefficient"] for value in roots[0]["values"]],
            }
        )
    if (
        any(detail["column_axis"] is None for detail in details)
        or len({detail["column_axis"] for detail in details}) != 1
    ):
        return None
    adjusted = [detail for detail in details if detail["adjustment_roles"]]
    if len(adjusted) != 1:
        return None
    net = adjusted[0]
    gross = [detail for detail in details if detail is not net]
    adjustment = net["adjustment_coefficients"]
    if adjustment is None or any(
        len(detail["values"]) != len(net["values"])
        or [
            gross_value + adjustment_value
            for gross_value, adjustment_value in zip(detail["values"], adjustment, strict=True)
        ]
        != net["values"]
        for detail in gross
    ):
        return None
    net_page = net["candidate"]["physical_page"]
    if any(abs(detail["candidate"]["physical_page"] - net_page) > 1 for detail in gross):
        return None
    nonroot_axes = [
        [
            mapping
            for mapping in detail["candidate"]["mappings"]
            if mapping["role"] != root_mapping_role
        ]
        for detail in details
    ]
    role_axes = [{mapping["role"] for mapping in axis} for axis in nonroot_axes]
    rnid_axes = [{mapping["report_norm_id"] for mapping in axis} for axis in nonroot_axes]
    if any(not axis for axis in role_axes) or any(
        roles & other_roles or rnids & other_rnids
        for index, (roles, rnids) in enumerate(zip(role_axes, rnid_axes, strict=True))
        for other_roles, other_rnids in zip(
            role_axes[index + 1 :], rnid_axes[index + 1 :], strict=True
        )
    ):
        return None
    ordered = [net, *sorted(gross, key=lambda detail: detail["candidate"]["physical_page"])]
    mappings = [canonical_clone_v1(net["root"])]
    for detail in ordered:
        mappings.extend(
            canonical_clone_v1(
                [
                    mapping
                    for mapping in detail["candidate"]["mappings"]
                    if mapping["role"] != root_mapping_role
                ]
            )
        )
    material = {
        "closure_receipt": {
            "adjustment_coefficients": adjustment,
            "adjustment_roles": net["adjustment_roles"],
            "component_candidate_ids": [detail["candidate"]["candidate_id"] for detail in ordered],
            "component_closure_receipt_sha256": [
                canonical_json_sha256_v1(detail["candidate"]["closure_receipt"])
                for detail in ordered
            ],
            "rule": "NET_PRESENTATION_PLUS_ADJACENT_DISJOINT_GROSS_CLASSIFICATION_AXES",
        },
        "component_page_json_version_ids": [
            detail["candidate"]["page_json_version_id"] for detail in ordered
        ],
        "component_table_ids": [detail["candidate"]["table_id"] for detail in ordered],
        "family_id": net["candidate"].get("family_id"),
        "mappings": mappings,
        "page_json_version_id": net["candidate"]["page_json_version_id"],
        "physical_page": net_page,
        "reasons": [],
        "section_id": net["candidate"]["section_id"],
        "status": READY,
        "table_id": net["candidate"]["table_id"],
    }
    return {
        "candidate_id": "gjfafcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def _selected_ready_candidate(
    ready: list[dict[str, Any]],
    *,
    compiled_specs: dict[str, Any],
) -> dict[str, Any] | None:
    """Prefer one exact role-rich detail over its exact JSON summary."""

    if len(ready) == 1:
        return ready[0]
    if not ready:
        return None

    def root_signature(candidate: dict[str, Any]) -> tuple[Any, ...] | None:
        roots = [
            mapping
            for mapping in candidate["mappings"]
            if mapping["report_norm_id"] == compiled_specs["schema"]["family_report_norm_id"]
        ]
        if len(roots) != 1:
            return None
        root = roots[0]
        return (
            len(root["columns"]),
            tuple(value["coefficient"] for value in root["values"]),
        )

    signatures = [root_signature(candidate) for candidate in ready]
    if any(signature is None for signature in signatures):
        return None
    if len(set(signatures)) != 1:
        return _net_adjusted_presentation_bundle(ready, compiled_specs=compiled_specs)
    structural_roles = {
        compiled_specs["topology"]["parent"]["role"],
        *(
            child["role"]
            for child in compiled_specs["topology"]["children"]
            if child["role_kind"] == "STRUCTURAL_GROUP"
        ),
    }
    role_sets = [{mapping["role"] for mapping in candidate["mappings"]} for candidate in ready]
    maximum_size = max(map(len, role_sets))
    winners = [index for index, roles in enumerate(role_sets) if len(roles) == maximum_size]
    if len(winners) == 1:
        winner = winners[0]
        if all(
            (roles & structural_roles) <= (role_sets[winner] & structural_roles)
            for roles in role_sets
        ):
            return ready[winner]
    winners = [
        index
        for index, roles in enumerate(role_sets)
        if all(index == other or roles > other_roles for other, other_roles in enumerate(role_sets))
    ]
    if len(winners) == 1:
        return ready[winners[0]]

    # Gemini may faithfully emit two adjacent tables for two complete views of
    # the same accounting population (for example issuer class and listing
    # status).  Preserve both source-observed role axes rather than arbitrarily
    # selecting one or summing the two presentations.  This composition is
    # valid only on one page/section, with an identical visible root and
    # pairwise-disjoint non-root schema roles.
    required_provenance = {
        "candidate_id",
        "closure_receipt",
        "mappings",
        "page_json_version_id",
        "physical_page",
        "reasons",
        "section_id",
        "status",
        "table_id",
    }
    if any(not required_provenance <= set(candidate) for candidate in ready):
        return None
    scopes = {
        (
            candidate["page_json_version_id"],
            candidate["physical_page"],
            candidate["section_id"],
        )
        for candidate in ready
    }
    table_ids = [candidate["table_id"] for candidate in ready]
    if len(scopes) != 1 or len(set(table_ids)) != len(table_ids):
        return None
    root_role = compiled_specs["topology"]["parent"]["role"]
    roots = []
    nonroot_axes = []
    for candidate in ready:
        root_mappings = [
            mapping for mapping in candidate["mappings"] if mapping["role"] == root_role
        ]
        if len(root_mappings) != 1:
            return None
        roots.append(root_mappings[0])
        nonroot_axes.append(
            [mapping for mapping in candidate["mappings"] if mapping["role"] != root_role]
        )

    def comparable_root(mapping: dict[str, Any]) -> dict[str, Any]:
        return {
            "columns": mapping["columns"],
            "report_norm_id": mapping["report_norm_id"],
            "role": mapping["role"],
            "values": mapping["values"],
        }

    if len({canonical_json_sha256_v1(comparable_root(root)) for root in roots}) != 1:
        return None
    role_axes = [{mapping["role"] for mapping in axis} for axis in nonroot_axes]
    rnid_axes = [{mapping["report_norm_id"] for mapping in axis} for axis in nonroot_axes]
    if any(not axis for axis in role_axes) or any(
        roles & other_roles or rnids & other_rnids
        for index, (roles, rnids) in enumerate(zip(role_axes, rnid_axes, strict=True))
        for other_roles, other_rnids in zip(
            role_axes[index + 1 :], rnid_axes[index + 1 :], strict=True
        )
    ):
        return None
    page_version_id, physical_page, section_id = next(iter(scopes))
    mappings = [canonical_clone_v1(roots[0])]
    for axis in nonroot_axes:
        mappings.extend(canonical_clone_v1(axis))
    material = {
        "closure_receipt": {
            "component_candidate_ids": [candidate["candidate_id"] for candidate in ready],
            "component_closure_receipt_sha256": [
                canonical_json_sha256_v1(candidate["closure_receipt"]) for candidate in ready
            ],
            "rule": "EQUIVALENT_DISJOINT_PRESENTATION_AXES_SHARE_ONE_EXACT_VISIBLE_ROOT",
        },
        "component_table_ids": table_ids,
        "family_id": ready[0].get("family_id"),
        "mappings": mappings,
        "page_json_version_id": page_version_id,
        "physical_page": physical_page,
        "reasons": [],
        "section_id": section_id,
        "status": READY,
        "table_id": table_ids[0],
    }
    return {
        "candidate_id": "gjfafcv1:candidate:" + canonical_json_sha256_v1(material),
        **material,
    }


def _region_table(page_json: dict[str, Any], region: dict[str, Any]) -> dict[str, Any]:
    sections = page_json.get("sections")
    if type(sections) is not list:
        raise _error("Gemini JSON candidate page has no section axis")
    section = sections[_node_index(region["section_id"], "s", len(sections))]
    tables = section.get("tables")
    if type(tables) is not list:
        raise _error("Gemini JSON candidate section has no table axis")
    table = tables[_node_index(region["table_id"], "t", len(tables))]
    if type(table) is not dict:
        raise _error("Gemini JSON candidate table is invalid")
    return table


def _write_once(path: Path, value: dict[str, Any]) -> None:
    payload = canonical_json_bytes_v1(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error("Gemini JSON family output already exists with different bytes")
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument(
        "--results-database",
        type=Path,
        required=True,
        help="Derived family-run SQLite; the sweep is committed here before JSON export.",
    )
    parser.add_argument(
        "--run-kind",
        choices=("EXPERIMENTAL", "OFFICIAL"),
        required=True,
        help="Only OFFICIAL runs advance the database current-selection pointer.",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    index = validate_current_corpus_manifest_index_v1(_json(args.corpus_index))
    artifact_root = args.artifact_root.resolve()
    database = _content_ref(artifact_root, index["database_ref"])
    topology = _json(args.topology_spec)
    evaluation = _json(args.evaluation_spec)
    schema = _json(args.schema_binding_spec)
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)

    selected_ids: list[str] = []
    for document in index["documents"]:
        manifest = _json(_content_ref(artifact_root, document["document_manifest_ref"]))
        if (
            manifest.get("document_manifest_id") != document["document_manifest_id"]
            or manifest.get("page_count") != document["page_count"]
            or type(manifest.get("pages")) is not list
        ):
            raise _error("selected document manifest identity or page axis drifted")
        page_ids = [page.get("page_json_version_id") for page in manifest["pages"]]
        if len(page_ids) != document["page_count"]:
            raise _error("selected document manifest JSON version axis is incomplete")
        selected_ids.extend(page_ids)
    if len(selected_ids) != index["summary"]["page_count"] or len(set(selected_ids)) != len(
        selected_ids
    ):
        raise _error("selected corpus JSON version frontier is incomplete or duplicate")

    regions_by_key: dict[tuple[str, int, str, str], dict[str, Any]] = {}
    for anchor_groups in compiled["anchor_alias_groups"]:
        regions = query_selected_family_anchor_regions_v1(
            database,
            selected_page_json_version_ids=selected_ids,
            anchor_aliases=anchor_groups,
            adjacent_page_radius=1,
        )
        for region in regions:
            key = (
                region["source_logical_name"],
                region["physical_page"],
                region["section_id"],
                region["table_id"],
            )
            regions_by_key[key] = region
    required_roles = {
        role
        for combination in compiled["topology"]["required_role_combinations"]
        for role in combination
    }
    near_aliases = sorted(
        {alias for role in required_roles for alias in compiled["aliases_by_role"][role]}
    )
    near_hits = query_selected_family_anchor_hits_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        anchor_aliases=near_aliases,
    )
    candidate_version_ids = sorted(
        {region["page_json_version_id"] for region in regions_by_key.values()}
    )
    near_version_ids = sorted({hit["page_json_version_id"] for hit in near_hits})
    loaded = load_page_json_versions_v1(
        database,
        page_json_version_ids=sorted(set(candidate_version_ids) | set(near_version_ids)),
    )
    page_by_version = {record["page_json_version_id"]: record for record in loaded}
    near_paths = {
        hit["source_logical_name"]
        for hit in near_hits
        if _hit_has_explicit_parent(
            hit,
            allow_row_parent=(
                compiled.get("engine_format_version")
                == "GEMINI_JSON_HIERARCHICAL_ACCOUNTING_FAMILY_SWEEP_V3"
            ),
            page_json=page_by_version[hit["page_json_version_id"]]["page_json"],
            parent_aliases=compiled["topology"]["parent"]["aliases"],
        )
    }
    candidates_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for key in sorted(regions_by_key):
        region = regions_by_key[key]
        page = page_by_version[region["page_json_version_id"]]
        table = _region_table(page["page_json"], region)
        columns = table.get("columns")
        if (
            type(columns) is list
            and columns
            and all(column.get("value_kind") != "MONEY" for column in columns)
        ):
            # A percentage/rate schedule can repeat the same currency labels
            # under the family heading.  Its declared non-money axis makes it
            # context, not a competing accounting-value population.
            continue
        candidate = evaluate_gemini_json_flat_family_table_v1(
            page_json=page["page_json"],
            page_json_version_id=region["page_json_version_id"],
            physical_page=region["physical_page"],
            section_id=region["section_id"],
            table_id=region["table_id"],
            compiled_specs=compiled,
        )
        if any(reason.startswith("FAMILY_PARENT_NOT_VISIBLE") for reason in candidate["reasons"]):
            # The two/three-anchor database query deliberately searches a
            # one-page neighborhood.  A nearby table without the declarative
            # explicit parent is near evidence, not a family candidate.
            continue
        candidates_by_path[region["source_logical_name"]].append(candidate)

    trials = []
    for document in index["documents"]:
        path = document["relative_path"]
        candidates = candidates_by_path.get(path, [])
        ready = [candidate for candidate in candidates if candidate["status"] == READY]
        unresolved_candidates = [
            candidate for candidate in candidates if candidate["status"] == UNRESOLVED
        ]
        reasons = []
        selected_candidate_id = None
        mappings = []
        selected = _selected_ready_candidate(ready, compiled_specs=compiled)
        if selected is not None:
            if selected["candidate_id"] not in {
                candidate["candidate_id"] for candidate in candidates
            }:
                candidates = [*candidates, selected]
            status = READY
            selected_candidate_id = selected["candidate_id"]
            mappings = selected["mappings"]
        elif not candidates and path not in near_paths:
            status = NOT_OBSERVED
        else:
            status = UNRESOLVED
            if len(ready) > 1:
                reasons.append("MULTIPLE_EXACT_GEMINI_JSON_FAMILY_REGIONS")
            if not candidates and path in near_paths:
                reasons.append("PARTIAL_REQUIRED_ANCHOR_FRONTIER_ONLY")
            reasons.extend(
                reason for candidate in unresolved_candidates for reason in candidate["reasons"]
            )
        trials.append(
            {
                "candidate_count": len(candidates),
                "candidates": candidates,
                "document_ordinal": document["source_ordinal"],
                "mappings": mappings,
                "reasons": sorted(set(reasons)),
                "selected_candidate_id": selected_candidate_id,
                "source_logical_name": path,
                "source_sha256": document["source_sha256"],
                "status": status,
            }
        )
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    implementation_paths = (
        ROOT / "scripts/experiments/run_gemini_json_first_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_hierarchical_accounting_family_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
    )
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=_file_ref(args.corpus_index),
        implementation_refs=[_file_ref(path, root=ROOT) for path in implementation_paths],
        run_kind=args.run_kind,
    )
    # The database is the system of record.  The JSON file is materialized
    # only by loading the just-committed canonical sweep back from SQLite.
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    _write_once(args.output, stored_sweep)
    export_ref = record_gemini_accounting_family_export_v1(
        args.results_database,
        family_run_id=stored["family_run_id"],
        output_path=args.output,
    )
    return {
        "disposition": "SUCCEEDED",
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "output_ref": export_ref,
        "results_database": str(args.results_database),
        "family_run_id": stored["family_run_id"],
        "run_kind": args.run_kind,
        "sweep_id": sweep["sweep_id"],
    }


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
