"""Reproducible production assembly for the MBB Q1-2026 consolidated TM export.

This module intentionally binds one immutable source PDF, the tracked PP-OCR
golden fixtures, the page-specific table policies, and the page-specific
production mapping APIs.  It never consults test modules, historical values,
human-review answers, or holdout data.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from bctc_ai.core.hashing import sha256_file, stable_records_hash
from bctc_ai.export.tm_consolidated_development import (
    TM_CONSOLIDATED_POLICY_RELATIVE_PATH,
    TM_CONSOLIDATED_SCHEMA_COUNT,
    TM_DOCUMENT_NEW_REPORT_NORM_IDS,
    TM_UNIVERSAL_SCHEMA_COUNT,
    TMConsolidatedDevelopmentExportResult,
    TMConsolidatedExportPolicy,
    TMConsolidatedOwnerInput,
    audit_tm_consolidated_owner_result_contracts,
    bind_tm_consolidated_owner_results,
    export_tm_consolidated_development,
    load_tm_consolidated_export_policy,
)
from bctc_ai.rendering.pdf import RenderedPage, render_pages
from bctc_ai.schema.hierarchy import apply_hierarchy_reference, load_hierarchy_reference
from bctc_ai.schema.registry import SchemaItem, load_all

TM_PRODUCTION_SOURCE_PDF_RELATIVE_PATH = Path(
    "vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf"
)
TM_PRODUCTION_SOURCE_PDF_SHA256 = "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83"
TM_PRODUCTION_SCHEMA_WORKBOOK_RELATIVE_PATH = Path("template/Bank_TM_ReportNormId.v2.xlsx")
TM_PRODUCTION_HIERARCHY_RELATIVE_PATH = Path("config/schemas/hierarchy_reference.yaml")
TM_PRODUCTION_SCHEMA_GRAPH_RELATIVE_PATH = Path("reference/schemas/schema_graph.jsonl")
TM_PRODUCTION_SCHEMA_GRAPH_SHA256 = (
    "5c90e38c91a2a83f6162430083147491899dd3141d3466102c71d394fb31a880"
)
TM_PRODUCTION_SCHEMA_REGISTRY_RELATIVE_PATH = Path("data/registered/schema_registry.json")
TM_PRODUCTION_RENDER_DPI = 300
TM_PRODUCTION_RENDER_PAGES = (*range(31, 55), 57, 58, 60, 61)
TM_PRODUCTION_WORKBOOK_NAME = "mbb-q1-2026-consolidated-tm-development.xlsx"
TM_PRODUCTION_PROVENANCE_NAME = "mbb-q1-2026-consolidated-tm-development.provenance.json"

_ParserKind = Literal["page30", "page31", "single_image", "paired_inputs", "split_inputs"]
_FORBIDDEN_AUTHORITY_MARKERS = (
    "HISTORICAL",
    "HISTORY",
    "HUMAN_REVIEW",
    "MONGODB",
    "HOLDOUT",
)
_PATH_BOUND_DASH_EVIDENCE_OWNERS = frozenset(
    {"pages-0039-0040", "page-0048", "page-0049", "page-0050"}
)


class TMConsolidatedProductionError(ValueError):
    """Raised when a production source, API, owner, or authority contract drifts."""


@dataclass(frozen=True)
class _OwnerAssemblySpec:
    owner_key: str
    pages: tuple[int, ...]
    parser_kind: _ParserKind
    table_module: str
    table_policy_loader: str
    parser: str
    table_policy_path: Path
    fixture_paths: tuple[Path, ...]
    mapping_module: str
    mapping_policy_loader: str
    reconciler: str
    validator: str | None
    mapping_policy_path: Path
    needs_schema_workbook: bool = False


@dataclass(frozen=True)
class TMConsolidatedProductionAssembly:
    """All 27 actual mapper results plus their frozen schema and input bindings."""

    schema: tuple[SchemaItem, ...]
    policy: TMConsolidatedExportPolicy
    owner_results: Mapping[str, object]
    owner_inputs: tuple[TMConsolidatedOwnerInput, ...]
    source_pdf_path: Path
    schema_workbook_path: Path
    render_paths: Mapping[int, Path]
    input_sha256s: Mapping[str, str]
    input_manifest_sha256: str
    render_manifest_sha256: str


def _single_page_spec(
    page: int,
    *,
    needs_schema_workbook: bool = False,
    validator: bool = True,
) -> _OwnerAssemblySpec:
    page_text = f"{page:02d}"
    return _OwnerAssemblySpec(
        owner_key=f"page-{page:04d}",
        pages=(page,),
        parser_kind="single_image",
        table_module=f"bctc_ai.tables.tm_note_page{page_text}",
        table_policy_loader=f"load_tm_page{page_text}_policy",
        parser=f"parse_tm_page{page_text}",
        table_policy_path=Path(f"config/tables/tm-note-page{page_text}-v1.yaml"),
        fixture_paths=(Path(f"tests/golden/tm/mbb-q1-2026-page-{page:04d}-ppocrv6-word-box.json"),),
        mapping_module=f"bctc_ai.mapping.tm_note_page{page_text}_mapping",
        mapping_policy_loader=f"load_tm_page{page_text}_mapping_policy",
        reconciler=f"reconcile_tm_page{page_text}_items",
        validator=f"validate_tm_page{page_text}_mapping_result" if validator else None,
        mapping_policy_path=Path(f"config/mapping/tm-note-page{page_text}-v1.yaml"),
        needs_schema_workbook=needs_schema_workbook,
    )


_PAGE_OWNER_SPECS = (
    _OwnerAssemblySpec(
        owner_key="page-0030",
        pages=(30,),
        parser_kind="page30",
        table_module="bctc_ai.tables.tm_note_word_box",
        table_policy_loader="load_tm_note_word_box_policy",
        parser="parse_tm_note_word_box_page",
        table_policy_path=Path("config/tables/tm-note-word-box-v1.yaml"),
        fixture_paths=(
            Path("tests/golden/tm/mbb-q1-2026-page-0030-ppocrv6-word-box.json"),
            Path("tests/golden/tm/mbb-q1-2026-page-0030-deepseek-labels.json"),
        ),
        mapping_module="bctc_ai.mapping.tm_note_mapping",
        mapping_policy_loader="load_tm_page30_mapping_policy",
        reconciler="reconcile_tm_page30_items",
        validator="validate_tm_page30_mapping_result",
        mapping_policy_path=Path("config/mapping/tm-note-page30-v1.yaml"),
    ),
    _OwnerAssemblySpec(
        owner_key="page-0031",
        pages=(31,),
        parser_kind="page31",
        table_module="bctc_ai.tables.tm_note_word_box",
        table_policy_loader="load_tm_page31_policy",
        parser="parse_tm_page31",
        table_policy_path=Path("config/tables/tm-note-page31-v1.yaml"),
        fixture_paths=(Path("tests/golden/tm/mbb-q1-2026-page-0031-ppocrv6-word-box.json"),),
        mapping_module="bctc_ai.mapping.tm_note_page31_mapping",
        mapping_policy_loader="load_tm_page31_mapping_policy",
        reconciler="reconcile_tm_page31_items",
        validator="validate_tm_page31_mapping_result",
        mapping_policy_path=Path("config/mapping/tm-note-page31-v1.yaml"),
    ),
    _OwnerAssemblySpec(
        owner_key="pages-0032-0033",
        pages=(32, 33),
        parser_kind="paired_inputs",
        table_module="bctc_ai.tables.tm_note_pages32_33",
        table_policy_loader="load_tm_note_pages32_33_policy",
        parser="parse_tm_note_pages32_33",
        table_policy_path=Path("config/tables/tm-note-pages32-33-v1.yaml"),
        fixture_paths=tuple(
            Path(f"tests/golden/tm/mbb-q1-2026-page-{page:04d}-ppocrv6-word-box.json")
            for page in (32, 33)
        ),
        mapping_module="bctc_ai.mapping.tm_note_pages32_33_mapping",
        mapping_policy_loader="load_tm_note_pages32_33_mapping_policy",
        reconciler="reconcile_tm_note_pages32_33_items",
        validator="validate_tm_note_pages32_33_mapping_result",
        mapping_policy_path=Path("config/mapping/tm-note-pages32-33-v1.yaml"),
    ),
    _single_page_spec(34),
    _single_page_spec(35),
    _single_page_spec(36),
    _OwnerAssemblySpec(
        owner_key="pages-0037-0038",
        pages=(37, 38),
        parser_kind="split_inputs",
        table_module="bctc_ai.tables.tm_note_pages37_38",
        table_policy_loader="load_tm_fixed_asset_pages37_38_policy",
        parser="parse_tm_fixed_asset_pages37_38",
        table_policy_path=Path("config/tables/tm-note-pages37-38-v1.yaml"),
        fixture_paths=tuple(
            Path(f"tests/golden/tm/mbb-q1-2026-page-{page:04d}-ppocrv6-word-box.json")
            for page in (37, 38)
        ),
        mapping_module="bctc_ai.mapping.tm_note_pages37_38_mapping",
        mapping_policy_loader="load_tm_fixed_asset_pages37_38_mapping_policy",
        reconciler="reconcile_tm_fixed_asset_pages37_38_items",
        validator="validate_tm_fixed_asset_pages37_38_mapping_result",
        mapping_policy_path=Path("config/mapping/tm-note-pages37-38-v1.yaml"),
    ),
    _OwnerAssemblySpec(
        owner_key="pages-0039-0040",
        pages=(39, 40),
        parser_kind="paired_inputs",
        table_module="bctc_ai.tables.tm_note_pages39_40",
        table_policy_loader="load_tm_note_pages39_40_policy",
        parser="parse_tm_note_pages39_40",
        table_policy_path=Path("config/tables/tm-note-pages39-40-v1.yaml"),
        fixture_paths=tuple(
            Path(f"tests/golden/tm/mbb-q1-2026-page-{page:04d}-ppocrv6-word-box.json")
            for page in (39, 40)
        ),
        mapping_module="bctc_ai.mapping.tm_note_pages39_40_mapping",
        mapping_policy_loader="load_tm_note_pages39_40_mapping_policy",
        reconciler="reconcile_tm_note_pages39_40_items",
        validator="validate_tm_note_pages39_40_mapping_result",
        mapping_policy_path=Path("config/mapping/tm-note-pages39-40-v1.yaml"),
    ),
    *(_single_page_spec(page) for page in range(41, 45)),
    _single_page_spec(45, needs_schema_workbook=True),
    *(_single_page_spec(page, validator=page != 49) for page in range(46, 52)),
    *(_single_page_spec(page, needs_schema_workbook=True) for page in range(52, 55)),
    _single_page_spec(57, needs_schema_workbook=True),
    _single_page_spec(58, needs_schema_workbook=True),
    _single_page_spec(60, needs_schema_workbook=True),
    _single_page_spec(61, needs_schema_workbook=True),
)

TM_PRODUCTION_PAGE_OWNER_KEYS = tuple(spec.owner_key for spec in _PAGE_OWNER_SPECS)
TM_PRODUCTION_OWNER_KEYS = (*TM_PRODUCTION_PAGE_OWNER_KEYS, "residual")


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_render_manifest_sha256(payload: Mapping[str, Any]) -> str:
    """Hash verified render evidence without binding it to a cache directory."""

    pages = payload.get("pages")
    if not isinstance(pages, list) or not all(isinstance(record, dict) for record in pages):
        raise TMConsolidatedProductionError("malformed TM render cache records")
    normalized = dict(payload)
    normalized["pages"] = [
        {
            key: Path(value).name if key == "path" and isinstance(value, str) else value
            for key, value in record.items()
        }
        for record in pages
    ]
    return _canonical_sha256(normalized)


def _dash_evidence_payload(owner_key: str, parsed: object) -> list[object]:
    rows = getattr(parsed, "rows", None)
    if not isinstance(rows, (tuple, list)):
        raise TMConsolidatedProductionError(
            f"production dash-evidence rows are unavailable for {owner_key}"
        )
    payload: list[object] = []
    for row in rows:
        evidence_items = getattr(row, "visual_cell_evidence", None)
        if not isinstance(evidence_items, (tuple, list)):
            raise TMConsolidatedProductionError(
                f"production dash-evidence cells are unavailable for {owner_key}"
            )
        if owner_key == "pages-0039-0040":
            cells = getattr(getattr(row, "row", None), "cells", None)
            if not isinstance(cells, (tuple, list)) or len(cells) != len(evidence_items):
                raise TMConsolidatedProductionError(
                    "production pages39-40 dash-evidence axes drifted"
                )
            for cell_index, (cell, evidence) in enumerate(zip(cells, evidence_items, strict=True)):
                observation = getattr(cell, "observation", None)
                if isinstance(observation, Enum):
                    observation = observation.value
                if observation != "DASH":
                    continue
                if evidence is None or not is_dataclass(evidence):
                    raise TMConsolidatedProductionError(
                        "production pages39-40 DASH lacks pixel evidence"
                    )
                payload.append(
                    {
                        "row_id": getattr(row, "row_id", None),
                        "cell_index": cell_index,
                        "evidence": asdict(evidence),
                    }
                )
        else:
            for evidence in evidence_items:
                if evidence is not None:
                    if not is_dataclass(evidence):
                        raise TMConsolidatedProductionError(
                            f"production pixel evidence is malformed for {owner_key}"
                        )
                    payload.append(asdict(evidence))
    return payload


def _raw_dash_pixel_evidence_sha256(owner_key: str, parsed: object) -> str:
    payload = _dash_evidence_payload(owner_key, parsed)
    encoded = json.dumps(
        payload,
        ensure_ascii=owner_key == "page-0049",
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalize_evidence_paths(value: object, *, field_name: str | None = None) -> object:
    if isinstance(value, Path):
        return value.name
    if field_name is not None and field_name.endswith("_path") and isinstance(value, str):
        return Path(value).name
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_evidence_paths(item, field_name=str(key))
            for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [_normalize_evidence_paths(item) for item in value]
    return value


def _canonicalize_dash_pixel_evidence(owner_key: str, parsed: object, result: object) -> object:
    if owner_key not in _PATH_BOUND_DASH_EVIDENCE_OWNERS:
        return result
    raw_hash = getattr(result, "dash_pixel_evidence_sha256", None)
    expected_raw_hash = _raw_dash_pixel_evidence_sha256(owner_key, parsed)
    if raw_hash != expected_raw_hash:
        raise TMConsolidatedProductionError(
            f"production dash pixel evidence hash drifted for {owner_key}"
        )
    canonical_payload = _normalize_evidence_paths(_dash_evidence_payload(owner_key, parsed))
    canonical_hash = _canonical_sha256(canonical_payload)
    if not is_dataclass(result):
        raise TMConsolidatedProductionError(
            f"production mapper result is not replaceable for {owner_key}"
        )
    return replace(result, dash_pixel_evidence_sha256=canonical_hash)


def _resolve_project_file(project_root: Path, relative_path: Path) -> Path:
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise TMConsolidatedProductionError(f"non-project TM input path: {relative_path}")
    root = project_root.resolve()
    candidate = root / relative_path
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise TMConsolidatedProductionError(
            f"missing TM production input: {relative_path}"
        ) from exc
    if root not in resolved.parents or not resolved.is_file() or candidate.is_symlink():
        raise TMConsolidatedProductionError(f"invalid TM production input: {relative_path}")
    return resolved


def _record_input_hash(
    project_root: Path,
    relative_path: Path,
    input_sha256s: dict[str, str],
) -> Path:
    path = _resolve_project_file(project_root, relative_path)
    key = relative_path.as_posix()
    digest = sha256_file(path)
    previous = input_sha256s.setdefault(key, digest)
    if previous != digest:
        raise TMConsolidatedProductionError(f"TM input changed during assembly: {key}")
    return path


def _resolve_function(module_name: str, function_name: str) -> Callable[..., Any]:
    try:
        module = importlib.import_module(module_name)
        value = getattr(module, function_name)
    except (ImportError, AttributeError) as exc:
        raise TMConsolidatedProductionError(
            f"missing production TM API: {module_name}.{function_name}"
        ) from exc
    if not callable(value) or getattr(value, "__module__", None) != module_name:
        raise TMConsolidatedProductionError(
            f"production TM API identity drifted: {module_name}.{function_name}"
        )
    return value


def audit_tm_consolidated_production_contracts(project_root: Path) -> dict[str, str]:
    """Audit the exact 27-owner inventory, APIs, and tracked direct inputs."""

    root = Path(project_root).resolve()
    policy = load_tm_consolidated_export_policy(root / TM_CONSOLIDATED_POLICY_RELATIVE_PATH)
    audit_tm_consolidated_owner_result_contracts(policy)
    if tuple(owner.owner_key for owner in policy.owners) != TM_PRODUCTION_OWNER_KEYS:
        raise TMConsolidatedProductionError("production TM owner inventory drifted")
    if len(_PAGE_OWNER_SPECS) != 26 or len(set(TM_PRODUCTION_PAGE_OWNER_KEYS)) != 26:
        raise TMConsolidatedProductionError("production TM page-owner inventory is not exact")
    page_inventory = tuple(page for spec in _PAGE_OWNER_SPECS for page in spec.pages)
    expected_pages = (*range(30, 55), 57, 58, 60, 61)
    if page_inventory != expected_pages:
        raise TMConsolidatedProductionError("production TM source-page inventory drifted")
    result: dict[str, str] = {}
    for spec in _PAGE_OWNER_SPECS:
        for module_name, function_name in (
            (spec.table_module, spec.table_policy_loader),
            (spec.table_module, spec.parser),
            (spec.mapping_module, spec.mapping_policy_loader),
            (spec.mapping_module, spec.reconciler),
        ):
            _resolve_function(module_name, function_name)
        if spec.validator is not None:
            _resolve_function(spec.mapping_module, spec.validator)
        for path in (spec.table_policy_path, spec.mapping_policy_path, *spec.fixture_paths):
            _resolve_project_file(root, path)
        result[spec.owner_key] = spec.mapping_module
    residual_module = "bctc_ai.mapping.tm_note_residual_mapping"
    for function_name in (
        "load_tm_residual_mapping_policy",
        "reconcile_tm_residual_items",
        "validate_tm_residual_mapping_result",
    ):
        _resolve_function(residual_module, function_name)
    _resolve_project_file(root, Path("config/mapping/tm-note-residual-v1.yaml"))
    result["residual"] = residual_module
    return result


def _verified_cached_renders(
    *,
    source_pdf_path: Path,
    source_pdf_sha256: str,
    render_directory: Path,
    pages: Sequence[int],
    dpi: int,
) -> tuple[dict[int, Path], str]:
    render_directory = Path(render_directory).resolve()
    manifest_path = render_directory / "manifest.json"
    expected_pages = tuple(sorted(pages))
    if len(expected_pages) != len(set(expected_pages)):
        raise TMConsolidatedProductionError("duplicate TM render page request")

    def verify_manifest() -> tuple[dict[int, Path], str]:
        try:
            manifest_bytes = manifest_path.read_bytes()
            payload = json.loads(manifest_bytes)
        except (OSError, json.JSONDecodeError) as exc:
            raise TMConsolidatedProductionError("cannot read TM render cache manifest") from exc
        if (
            not isinstance(payload, dict)
            or payload.get("format_version") != 1
            or payload.get("source_sha256") != source_pdf_sha256
            or payload.get("dpi") != dpi
            or not isinstance(payload.get("pages"), list)
        ):
            raise TMConsolidatedProductionError("TM render cache manifest binding drifted")
        records = payload["pages"]
        if [record.get("page") for record in records if isinstance(record, dict)] != list(
            expected_pages
        ) or len(records) != len(expected_pages):
            raise TMConsolidatedProductionError("TM render cache page inventory drifted")
        paths: dict[int, Path] = {}
        for record in records:
            if not isinstance(record, dict):
                raise TMConsolidatedProductionError("malformed TM render cache record")
            page = record.get("page")
            expected_path = render_directory / f"page-{page:04d}.png"
            if (
                record.get("dpi") != dpi
                or record.get("source_sha256") != source_pdf_sha256
                or record.get("path") != expected_path.as_posix()
                or not isinstance(record.get("sha256"), str)
                or not expected_path.is_file()
                or expected_path.is_symlink()
                or sha256_file(expected_path) != record["sha256"]
            ):
                raise TMConsolidatedProductionError(
                    f"TM render cache content drifted for page {page}"
                )
            paths[page] = expected_path
        return paths, _canonical_render_manifest_sha256(payload)

    if manifest_path.exists():
        return verify_manifest()
    if render_directory.exists() and any(render_directory.iterdir()):
        raise TMConsolidatedProductionError("unmanifested TM render cache is not trusted")
    render_directory.mkdir(parents=True, exist_ok=True)
    records = render_pages(
        source_pdf_path,
        render_directory,
        dpi=dpi,
        page_numbers=set(expected_pages),
    )
    if tuple(record.page for record in records) != expected_pages or any(
        not isinstance(record, RenderedPage)
        or record.dpi != dpi
        or record.source_sha256 != source_pdf_sha256
        for record in records
    ):
        raise TMConsolidatedProductionError("fresh TM render result drifted")
    return verify_manifest()


def _load_frozen_schema(
    project_root: Path,
    policy: TMConsolidatedExportPolicy,
    input_sha256s: dict[str, str],
) -> tuple[tuple[SchemaItem, ...], Path]:
    workbook_path = _record_input_hash(
        project_root, TM_PRODUCTION_SCHEMA_WORKBOOK_RELATIVE_PATH, input_sha256s
    )
    if input_sha256s[TM_PRODUCTION_SCHEMA_WORKBOOK_RELATIVE_PATH.as_posix()] != (
        policy.schema_workbook_sha256
    ):
        raise TMConsolidatedProductionError("production TM schema workbook hash drifted")
    _record_input_hash(project_root, TM_PRODUCTION_HIERARCHY_RELATIVE_PATH, input_sha256s)
    graph_path = _record_input_hash(
        project_root, TM_PRODUCTION_SCHEMA_GRAPH_RELATIVE_PATH, input_sha256s
    )
    registry_path = _record_input_hash(
        project_root, TM_PRODUCTION_SCHEMA_REGISTRY_RELATIVE_PATH, input_sha256s
    )
    if (
        input_sha256s[TM_PRODUCTION_SCHEMA_GRAPH_RELATIVE_PATH.as_posix()]
        != TM_PRODUCTION_SCHEMA_GRAPH_SHA256
    ):
        raise TMConsolidatedProductionError("production universal schema artifacts drifted")
    try:
        registry = json.loads(registry_path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise TMConsolidatedProductionError("production schema registry cannot be decoded") from exc
    universal_registry = registry.get("universal_schema", {}) if isinstance(registry, dict) else {}
    if (
        universal_registry.get("schema_graph_sha256") != TM_PRODUCTION_SCHEMA_GRAPH_SHA256
        or universal_registry.get("universal_schema_sha256") != TM_PRODUCTION_SCHEMA_GRAPH_SHA256
        or sha256_file(graph_path) != TM_PRODUCTION_SCHEMA_GRAPH_SHA256
    ):
        raise TMConsolidatedProductionError("production universal schema registry binding drifted")
    _workbooks, schema = load_all(project_root / "template", project_root)
    _payload, hierarchy = load_hierarchy_reference(
        project_root / TM_PRODUCTION_HIERARCHY_RELATIVE_PATH,
        project_root,
        schema,
    )
    apply_hierarchy_reference(schema, hierarchy)
    statement_counts = {
        statement: sum(item.statement_type == statement for item in schema)
        for statement in ("CDKT", "KQKD", "LCTT", "TM")
    }
    universal_ids_hash = stable_records_hash(str(item.schema_id) for item in schema)
    universal_projection_hash = stable_records_hash(
        json.dumps(
            {
                "statement_type": item.statement_type,
                "report_norm_id": item.schema_id,
                "canonical_name": item.canonical_name,
                "display_order": item.display_order,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        for item in schema
    )
    universal_identity = (policy.schema_identity or {}).get("universal_schema", {})
    if (
        len(schema) != TM_UNIVERSAL_SCHEMA_COUNT
        or statement_counts != {"CDKT": 99, "KQKD": 25, "LCTT": 110, "TM": 1_710}
        or max(item.schema_id for item in schema) != 6_065
        or not set(TM_DOCUMENT_NEW_REPORT_NORM_IDS) <= {item.schema_id for item in schema}
        or universal_ids_hash != universal_identity.get("ordered_report_norm_ids_sha256")
        or universal_projection_hash
        != universal_identity.get("ordered_canonical_projection_sha256")
    ):
        raise TMConsolidatedProductionError("production universal schema identity drifted")
    tm_schema = tuple(
        sorted(
            (item for item in schema if item.statement_type == "TM"),
            key=lambda item: item.display_order,
        )
    )
    projection = [
        (
            item.schema_id,
            item.display_order,
            item.canonical_name,
            item.parent_id,
            tuple(item.children),
        )
        for item in tm_schema
    ]
    if (
        len(tm_schema) != TM_CONSOLIDATED_SCHEMA_COUNT
        or tuple(item.display_order for item in tm_schema)
        != tuple(range(TM_CONSOLIDATED_SCHEMA_COUNT))
        or _canonical_sha256(projection) != policy.schema_projection_sha256
    ):
        raise TMConsolidatedProductionError("production TM schema projection drifted")
    return tuple(schema), workbook_path


def _direct_result_hash_check(
    result: object,
    *,
    fixture_sha256s: tuple[str, ...],
    render_sha256s: tuple[str, ...],
    mapping_policy: object,
) -> None:
    for singular, plural, expected in (
        ("source_ocr_sha256", "source_ocr_sha256s", fixture_sha256s),
        ("source_render_sha256", "source_render_sha256s", render_sha256s),
    ):
        field_name = plural if hasattr(result, plural) else singular
        if not hasattr(result, field_name):
            continue
        actual = getattr(result, field_name)
        if isinstance(actual, (tuple, list)):
            matches = tuple(actual) == expected
        else:
            matches = len(expected) == 1 and actual == expected[0]
        if not matches:
            raise TMConsolidatedProductionError(f"production result {field_name} drifted")
    if hasattr(result, "source_pdf_sha256") and (
        result.source_pdf_sha256 != TM_PRODUCTION_SOURCE_PDF_SHA256
    ):
        raise TMConsolidatedProductionError("production result PDF hash drifted")
    expected_policy_hash = getattr(mapping_policy, "policy_sha256", None)
    result_policy_hash = getattr(
        result,
        "policy_sha256",
        getattr(result, "mapping_policy_sha256", None),
    )
    if (
        expected_policy_hash is not None
        and result_policy_hash is not None
        and result_policy_hash != expected_policy_hash
    ):
        raise TMConsolidatedProductionError("production result mapping policy hash drifted")


def _reject_external_authority(result: object, owner_key: str) -> None:
    mapping_inputs = getattr(result, "mapping_inputs", ())
    if mapping_inputs is None:
        mapping_inputs = ()
    if not isinstance(mapping_inputs, (tuple, list)) or any(
        not isinstance(value, str) or not value for value in mapping_inputs
    ):
        raise TMConsolidatedProductionError(f"invalid mapping-input authority for {owner_key}")
    forbidden = sorted(
        value
        for value in mapping_inputs
        if any(marker in value.upper() for marker in _FORBIDDEN_AUTHORITY_MARKERS)
    )
    if forbidden:
        raise TMConsolidatedProductionError(
            f"forbidden mapping-input authority reached {owner_key}: {forbidden}"
        )


def _assemble_page_owner(
    spec: _OwnerAssemblySpec,
    *,
    project_root: Path,
    schema: Sequence[SchemaItem],
    source_pdf_path: Path,
    schema_workbook_path: Path,
    render_paths: Mapping[int, Path],
    render_sha256s: Mapping[int, str],
    input_sha256s: dict[str, str],
) -> object:
    table_policy_path = _record_input_hash(project_root, spec.table_policy_path, input_sha256s)
    mapping_policy_path = _record_input_hash(project_root, spec.mapping_policy_path, input_sha256s)
    fixture_paths = tuple(
        _record_input_hash(project_root, path, input_sha256s) for path in spec.fixture_paths
    )
    table_policy = _resolve_function(spec.table_module, spec.table_policy_loader)(table_policy_path)
    mapping_policy = _resolve_function(spec.mapping_module, spec.mapping_policy_loader)(
        mapping_policy_path
    )
    parser = _resolve_function(spec.table_module, spec.parser)
    reconciler = _resolve_function(spec.mapping_module, spec.reconciler)

    if spec.parser_kind == "page30":
        parsed = parser(fixture_paths[0], table_policy, page_tag="page-0030")
        evidence_loader = _resolve_function(spec.mapping_module, "load_tm_page30_deepseek_evidence")
        result = reconciler(
            parsed,
            schema=schema,
            policy=mapping_policy,
            source_pdf_path=source_pdf_path,
            independent_evidence=evidence_loader(fixture_paths[1]),
        )
    elif spec.parser_kind == "page31":
        parsed = parser(fixture_paths[0], table_policy)
        result = reconciler(
            parsed,
            schema=schema,
            policy=mapping_policy,
            source_pdf_path=source_pdf_path,
            source_render_path=render_paths[31],
        )
    elif spec.parser_kind == "single_image":
        page = spec.pages[0]
        parsed = parser(fixture_paths[0], render_paths[page], table_policy)
        kwargs: dict[str, object] = {
            "schema": schema,
            "policy": mapping_policy,
            "source_pdf_path": source_pdf_path,
        }
        if spec.needs_schema_workbook:
            kwargs["schema_workbook_path"] = schema_workbook_path
        result = reconciler(parsed, **kwargs)
    elif spec.parser_kind == "paired_inputs":
        parsed = parser(
            {
                page: (fixture, render_paths[page])
                for page, fixture in zip(spec.pages, fixture_paths, strict=True)
            },
            table_policy,
        )
        result = reconciler(
            parsed,
            schema=schema,
            policy=mapping_policy,
            source_pdf_path=source_pdf_path,
        )
    elif spec.parser_kind == "split_inputs":
        parsed = parser(
            {page: fixture for page, fixture in zip(spec.pages, fixture_paths, strict=True)},
            {page: render_paths[page] for page in spec.pages},
            table_policy,
        )
        result = reconciler(
            parsed,
            schema=schema,
            policy=mapping_policy,
            source_pdf_path=source_pdf_path,
        )
    else:  # pragma: no cover - the frozen spec constructor makes this unreachable.
        raise TMConsolidatedProductionError(f"unsupported production parser: {spec.parser_kind}")

    if spec.validator is not None:
        validated = _resolve_function(spec.mapping_module, spec.validator)(result)
        if validated is not result:
            raise TMConsolidatedProductionError(
                f"production validator replaced the result for {spec.owner_key}"
            )
    _direct_result_hash_check(
        result,
        fixture_sha256s=tuple(
            input_sha256s[path.as_posix()] for path in spec.fixture_paths[: len(spec.pages)]
        ),
        render_sha256s=tuple(render_sha256s[page] for page in spec.pages if page != 30),
        mapping_policy=mapping_policy,
    )
    _reject_external_authority(result, spec.owner_key)
    return _canonicalize_dash_pixel_evidence(spec.owner_key, parsed, result)


def _owned_schema_ids_by_owner(owner_results: Mapping[str, object]) -> dict[str, set[int]]:
    ownership: dict[int, str] = {}
    by_owner: dict[str, set[int]] = {}
    for owner_key in TM_PRODUCTION_PAGE_OWNER_KEYS:
        result = owner_results[owner_key]
        dispositions = getattr(result, "schema_dispositions", None)
        if not isinstance(dispositions, (tuple, list)) or len(dispositions) != (
            TM_CONSOLIDATED_SCHEMA_COUNT
        ):
            raise TMConsolidatedProductionError(
                f"production schema disposition denominator drifted for {owner_key}"
            )
        owned: set[int] = set()
        for disposition in dispositions:
            status = getattr(disposition, "status", None)
            if isinstance(status, Enum):
                status = status.value
            report_norm_id = getattr(disposition, "report_norm_id", None)
            if status == "UNASSESSED":
                continue
            if isinstance(report_norm_id, bool) or not isinstance(report_norm_id, int):
                raise TMConsolidatedProductionError(f"invalid production schema ID for {owner_key}")
            previous = ownership.setdefault(report_norm_id, owner_key)
            if previous != owner_key:
                raise TMConsolidatedProductionError(
                    f"production schema ID {report_norm_id} has owners {previous} and {owner_key}"
                )
            owned.add(report_norm_id)
        by_owner[owner_key] = owned
    return by_owner


def assemble_mbb_tm_consolidated_production_results(
    *,
    project_root: Path,
    run_directory: Path,
    progress: Callable[[str], None] | None = None,
) -> TMConsolidatedProductionAssembly:
    """Run the 26 production page mappers and residual mapper without exporting files."""

    root = Path(project_root).resolve()
    audit_tm_consolidated_production_contracts(root)
    input_sha256s: dict[str, str] = {}
    export_policy_path = _record_input_hash(
        root, TM_CONSOLIDATED_POLICY_RELATIVE_PATH, input_sha256s
    )
    policy = load_tm_consolidated_export_policy(export_policy_path)
    source_pdf_path = _record_input_hash(
        root, TM_PRODUCTION_SOURCE_PDF_RELATIVE_PATH, input_sha256s
    )
    if sha256_file(source_pdf_path) != TM_PRODUCTION_SOURCE_PDF_SHA256:
        raise TMConsolidatedProductionError("production TM source PDF hash drifted")
    schema, schema_workbook_path = _load_frozen_schema(root, policy, input_sha256s)
    render_paths, render_manifest_sha256 = _verified_cached_renders(
        source_pdf_path=source_pdf_path,
        source_pdf_sha256=TM_PRODUCTION_SOURCE_PDF_SHA256,
        render_directory=Path(run_directory).resolve() / "renders-300dpi",
        pages=TM_PRODUCTION_RENDER_PAGES,
        dpi=TM_PRODUCTION_RENDER_DPI,
    )
    render_sha256s = {page: sha256_file(path) for page, path in render_paths.items()}
    owner_results: dict[str, object] = {}
    for spec in _PAGE_OWNER_SPECS:
        if progress is not None:
            progress(f"ASSEMBLING_TM_OWNER={spec.owner_key}")
        owner_results[spec.owner_key] = _assemble_page_owner(
            spec,
            project_root=root,
            schema=schema,
            source_pdf_path=source_pdf_path,
            schema_workbook_path=schema_workbook_path,
            render_paths=render_paths,
            render_sha256s=render_sha256s,
            input_sha256s=input_sha256s,
        )

    owned_by_owner = _owned_schema_ids_by_owner(owner_results)
    existing_owned_schema_ids = set().union(*owned_by_owner.values())
    residual_policy_relative_path = Path("config/mapping/tm-note-residual-v1.yaml")
    residual_policy_path = _record_input_hash(root, residual_policy_relative_path, input_sha256s)
    residual_module = "bctc_ai.mapping.tm_note_residual_mapping"
    residual_policy = _resolve_function(residual_module, "load_tm_residual_mapping_policy")(
        residual_policy_path
    )
    residual = _resolve_function(residual_module, "reconcile_tm_residual_items")(
        schema,
        policy=residual_policy,
        project_root=root,
        source_pdf_path=source_pdf_path,
        schema_workbook_path=schema_workbook_path,
        existing_owned_schema_ids=existing_owned_schema_ids,
    )
    validated_residual = _resolve_function(residual_module, "validate_tm_residual_mapping_result")(
        residual
    )
    if validated_residual is not residual:
        raise TMConsolidatedProductionError("production residual validator replaced its result")
    _reject_external_authority(residual, "residual")
    owner_results["residual"] = residual
    owner_inputs = bind_tm_consolidated_owner_results(owner_results, policy)

    manifest_payload = {
        "artifact_type": "MBB_Q1_2026_TM_PRODUCTION_INPUT_MANIFEST",
        "direct_inputs": dict(sorted(input_sha256s.items())),
        "render_dpi": TM_PRODUCTION_RENDER_DPI,
        "renders": [
            {"page": page, "sha256": render_sha256s[page]} for page in TM_PRODUCTION_RENDER_PAGES
        ],
        "source_pdf_sha256": TM_PRODUCTION_SOURCE_PDF_SHA256,
    }
    return TMConsolidatedProductionAssembly(
        schema=tuple(schema),
        policy=policy,
        owner_results=dict(owner_results),
        owner_inputs=owner_inputs,
        source_pdf_path=source_pdf_path,
        schema_workbook_path=schema_workbook_path,
        render_paths=dict(render_paths),
        input_sha256s=dict(sorted(input_sha256s.items())),
        input_manifest_sha256=_canonical_sha256(manifest_payload),
        render_manifest_sha256=render_manifest_sha256,
    )


def export_mbb_tm_consolidated_production(
    *,
    project_root: Path,
    run_directory: Path,
    output_directory: Path,
    run_id: str = "mbb-q1-2026-tm-development",
    progress: Callable[[str], None] | None = None,
) -> TMConsolidatedDevelopmentExportResult:
    """Assemble all actual results and write the deterministic paired artifacts once."""

    if not isinstance(run_id, str) or not run_id.strip():
        raise TMConsolidatedProductionError("TM production run ID is required")
    assembly = assemble_mbb_tm_consolidated_production_results(
        project_root=project_root,
        run_directory=run_directory,
        progress=progress,
    )
    output = Path(output_directory).resolve()
    return export_tm_consolidated_development(
        template_path=assembly.schema_workbook_path,
        workbook_path=output / TM_PRODUCTION_WORKBOOK_NAME,
        provenance_path=output / TM_PRODUCTION_PROVENANCE_NAME,
        schema=assembly.schema,
        owner_inputs=assembly.owner_inputs,
        policy=assembly.policy,
        run_metadata={
            "input_manifest_sha256": assembly.input_manifest_sha256,
            "render_manifest_sha256": assembly.render_manifest_sha256,
            "run_id": run_id.strip(),
            "source_pdf_sha256": TM_PRODUCTION_SOURCE_PDF_SHA256,
        },
    )


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="export-mbb-tm-consolidated-development",
        description="Assemble all 27 production TM owners and write paired development artifacts.",
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--run-dir",
        help="verified render-cache directory; defaults to OUTPUT_DIR/.tm-consolidated-run",
    )
    parser.add_argument("--run-id", default="mbb-q1-2026-tm-development")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_cli_parser().parse_args(argv)
    output_directory = Path(args.output_dir).resolve()
    run_directory = (
        Path(args.run_dir).resolve() if args.run_dir else output_directory / ".tm-consolidated-run"
    )
    result = export_mbb_tm_consolidated_production(
        project_root=Path(args.project_root),
        run_directory=run_directory,
        output_directory=output_directory,
        run_id=args.run_id,
        progress=print,
    )
    print(f"TM_WORKBOOK={result.workbook_path}")
    print(f"TM_WORKBOOK_SHA256={result.workbook_sha256}")
    print(f"TM_PROVENANCE={result.provenance_path}")
    print(f"TM_PROVENANCE_SHA256={result.provenance_sha256}")
    print(f"TM_SCHEMA_ITEMS={result.schema_item_count}")
    print(f"TM_OBSERVATIONS={result.observation_count}")
    return 0


__all__ = [
    "TM_PRODUCTION_HIERARCHY_RELATIVE_PATH",
    "TM_PRODUCTION_OWNER_KEYS",
    "TM_PRODUCTION_PAGE_OWNER_KEYS",
    "TM_PRODUCTION_PROVENANCE_NAME",
    "TM_PRODUCTION_RENDER_DPI",
    "TM_PRODUCTION_RENDER_PAGES",
    "TM_PRODUCTION_SCHEMA_WORKBOOK_RELATIVE_PATH",
    "TM_PRODUCTION_SCHEMA_GRAPH_RELATIVE_PATH",
    "TM_PRODUCTION_SCHEMA_GRAPH_SHA256",
    "TM_PRODUCTION_SCHEMA_REGISTRY_RELATIVE_PATH",
    "TM_PRODUCTION_SOURCE_PDF_RELATIVE_PATH",
    "TM_PRODUCTION_SOURCE_PDF_SHA256",
    "TM_PRODUCTION_WORKBOOK_NAME",
    "TMConsolidatedProductionAssembly",
    "TMConsolidatedProductionError",
    "assemble_mbb_tm_consolidated_production_results",
    "audit_tm_consolidated_production_contracts",
    "build_cli_parser",
    "export_mbb_tm_consolidated_production",
    "main",
]
