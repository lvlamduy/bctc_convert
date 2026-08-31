#!/usr/bin/env python3
"""Build and replay the Family 53 selected-JSON release audit."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    READY,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    query_selected_dual_axis_family_regions_v1,
    validate_selected_dual_axis_family_candidate_replays_v1,
)


class BuildGeminiJsonSecuritiesGeographyReleaseAuditV1Error(RuntimeError):
    """The selected source, sweep, comparator, or semantic axis drifted."""


def _error(message: str) -> BuildGeminiJsonSecuritiesGeographyReleaseAuditV1Error:
    return BuildGeminiJsonSecuritiesGeographyReleaseAuditV1Error(message)


AUDIT_FORMAT_VERSION = "GEMINI_JSON_SECURITIES_GEOGRAPHY_RELEASE_AUDIT_V1"
AUDIT_ID_PREFIX = "gjsgrauditv1:audit:"
PINNED_CORPUS_MANIFEST_INDEX_ID = (
    "gjfccmiv1:index:61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3"
)
PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256 = (
    "601be9fc2a894af2ce4f4c982d5347521a6268a46c075d9cc96f9828baef8ae8"
)
PINNED_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 232,
    "not_observed_count": 21,
    "ready_count": 119,
    "unresolved_count": 0,
}
PINNED_QUERY_RECEIPT = {
    "candidate_table_count_before_column_decode": 609,
    "decoded_column_header_count": 3631,
    "document_context_period_record_count": 15059,
    "document_context_unit_record_count": 17143,
    "exact_region_axis_sha256": (
        "b4c7eea826d0589b5668e04634568f19e4a74d2ad18b9531006fd8d52da9256c"
    ),
    "exact_region_count": 155,
    "indexed_row_hit_count": 710,
    "orientation_counts": {
        "METRIC_ROW_ROLE_COLUMNS": 56,
        "ROW_ROLES_METRIC_COLUMN": 99,
    },
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
    "selected_page_json_version_count": 8947,
    "target_document_count": 119,
    "target_document_header_record_count": 26832,
    "target_document_title_record_count": 13342,
}
PINNED_RELEASE_AXIS_SHA256 = {
    "clusters": "00f1fdb5bce4edbb1d04c8977c0711ece38d27215613326115932ba674f4c6b6",
    "historical_comparator": ("52a963aa997cb02e57bd595d706afae16c444537f4884b06b4d678a6d2f64969"),
    "mappings": "3de4e514296adeb0f0915cde8ef7566499bb99387b8baa5f042beae3aa942532",
    "source_table_closures": ("65b65de52f8629eb2a63b917cf44e8387698de16828cf881cf864c6dbe182bd1"),
    "unmapped_source_blanks": ("b455fdc37fde5eeb9f32009b0ad5b11e08aa9f00c5ad60c17f45fd8af763bb33"),
}
PINNED_HISTORICAL_ORACLE = {
    "format_version": "ANNUAL_2025_SECURITIES_GEOGRAPHY_8BANK_CODEX_VERIFIED_MAPPING_V1",
    "path": (
        "docs/experiments/"
        "E-0160-annual-2025-securities-geography-8bank-codex-verified-mapping-v1.json"
    ),
    "sha256": "f5a7075df07cfdb58b2aba2d994f9ecb4c74d37a44b7991299fe7e5dbd1a4449",
    "size_bytes": 25804,
}
_SQLITE_SIDECAR_SUFFIXES = ("-journal", "-shm", "-wal")


def _json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise _error(f"JSON input is absent or not regular: {path}")
    try:
        return json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"JSON input is invalid: {path}") from exc


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


def _content_ref(root: Path, reference: Any) -> Path:
    if type(reference) is not dict or set(reference) != {"path", "sha256", "size_bytes"}:
        raise _error("corpus content reference fields drifted")
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise _error("corpus content reference escapes its artifact root")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size != reference["size_bytes"]
        or _sha256(path) != reference["sha256"]
    ):
        raise _error("corpus content reference does not authenticate")
    return path


def _assert_no_sqlite_sidecars(path: Path) -> None:
    if any(os.path.lexists(f"{path}{suffix}") for suffix in _SQLITE_SIDECAR_SUFFIXES):
        raise _error("securities-geography SQLite source has a journal/WAL sidecar")


def _file_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


@contextmanager
def _authenticated_sqlite_source_view(source: Path, *, expected_ref: Mapping[str, Any]):
    """Yield one immutable source view; never snapshot per document or candidate."""

    _assert_no_sqlite_sidecars(source)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(source, flags)
    directory = tempfile.mkdtemp(prefix="f53-selected-source-view-")
    snapshot = Path(directory) / "page-store.sqlite3"
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error("securities-geography SQLite source is not regular")
        with os.fdopen(os.dup(descriptor), "rb", closefd=True) as input_stream:
            snapshot_descriptor = os.open(
                snapshot,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
                0o400,
            )
            try:
                with os.fdopen(snapshot_descriptor, "wb", closefd=True) as output_stream:
                    shutil.copyfileobj(input_stream, output_stream, length=1024 * 1024)
                    output_stream.flush()
                    os.fsync(output_stream.fileno())
            except BaseException:
                snapshot.unlink(missing_ok=True)
                raise
        os.chmod(snapshot, 0o444)
        if (
            snapshot.stat().st_size != expected_ref["size_bytes"]
            or _sha256(snapshot) != expected_ref["sha256"]
        ):
            raise _error("securities-geography SQLite source bytes do not authenticate")
        yield snapshot
        after = os.fstat(descriptor)
        _assert_no_sqlite_sidecars(source)
        if _file_identity(after) != _file_identity(before):
            raise _error("securities-geography SQLite source identity changed during replay")
    finally:
        os.close(descriptor)
        shutil.rmtree(directory, ignore_errors=True)


def _selected_frontier(*, index: Mapping[str, Any], artifact_root: Path) -> tuple[Path, list[str]]:
    database = _content_ref(artifact_root, index["database_ref"])
    selected_ids: list[str] = []
    for document in index["documents"]:
        manifest = _json(_content_ref(artifact_root, document["document_manifest_ref"]))
        if (
            type(manifest) is not dict
            or manifest.get("document_manifest_id") != document["document_manifest_id"]
            or manifest.get("page_count") != document["page_count"]
            or type(manifest.get("pages")) is not list
        ):
            raise _error("selected document manifest identity or page axis drifted")
        page_ids = [page.get("page_json_version_id") for page in manifest["pages"]]
        if len(page_ids) != document["page_count"]:
            raise _error("selected document manifest page frontier is incomplete")
        selected_ids.extend(page_ids)
    if len(selected_ids) != index["summary"]["page_count"] or len(selected_ids) != len(
        set(selected_ids)
    ):
        raise _error("selected corpus page JSON frontier is incomplete or duplicate")
    return database, selected_ids


def _compiled_from_sweep(sweep: Mapping[str, Any]) -> dict[str, Any]:
    return compile_gemini_json_flat_family_specs_v1(
        sweep["specs"]["topology"]["value"],
        sweep["specs"]["evaluation"]["value"],
        sweep["specs"]["schema_binding"]["value"],
    )


def _query_receipt(
    database: Path, *, selected_ids: Sequence[str], compiled: Mapping[str, Any]
) -> dict[str, Any]:
    policy = compiled["dual_axis_projection_policy"]
    queried = query_selected_dual_axis_family_regions_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        metric_aliases=policy["metric_aliases"],
        role_aliases={
            role: compiled["query_aliases_by_role"][role] for role in policy["projected_role_order"]
        },
        unit_aliases=policy["unit_aliases"],
    )
    return queried["query_receipt"]


def _historical_comparator_axis(
    *, sweep: Mapping[str, Any], historical_oracle: Mapping[str, Any]
) -> list[dict[str, Any]]:
    trials_by_source = {trial["source_sha256"]: trial for trial in sweep["trials"]}
    if len(trials_by_source) != len(sweep["trials"]):
        raise _error("securities-geography trial source axis is not unique")
    records = []
    for historical in historical_oracle["trials"]:
        trial = trials_by_source.get(historical["source_pdf_sha256"])
        if trial is None:
            raise _error("historical securities-geography source is absent from the sweep")
        base = {
            "document_ordinal": trial["document_ordinal"],
            "document_provenance": historical["document_provenance"],
            "source_sha256": trial["source_sha256"],
        }
        if historical["status"] == "VERIFIED_BY_CODEX":
            current_by_role = {mapping["role"]: mapping for mapping in trial["mappings"]}
            for mapping in historical["verified_mappings"]:
                role = mapping["semantic_role"]
                current = current_by_role.get(role)
                expected_coefficients = [value["normalized_value"] for value in mapping["values"]]
                current_coefficients = (
                    [] if current is None else [value["coefficient"] for value in current["values"]]
                )
                exact = (
                    current is not None
                    and current["report_norm_id"] == mapping["report_norm_id"]
                    and current_coefficients == expected_coefficients
                )
                records.append(
                    {
                        **base,
                        "current_coefficients": current_coefficients,
                        "current_report_norm_id": (
                            None if current is None else current["report_norm_id"]
                        ),
                        "disposition": "EXACT_MAPPING" if exact else "MISMATCH",
                        "expected_coefficients": expected_coefficients,
                        "expected_report_norm_id": mapping["report_norm_id"],
                        "role": role,
                    }
                )
        elif historical["status"] == "NOT_OBSERVED_IN_BOUND_REPORT":
            if not trial["mappings"]:
                disposition = "EXACT_NOT_OBSERVED"
            elif (
                trial["status"] == READY
                and len(trial["candidates"]) == 1
                and trial["candidates"][0]["reasons"] == []
                and trial["candidates"][0]["source_table_refs"]
            ):
                disposition = "SUPERSEDED_BOUNDED_ABSENCE_BY_AUTHENTICATED_SELECTED_JSON_SOURCE"
            else:
                disposition = "MISMATCH"
            records.append(
                {
                    **base,
                    "current_mapping_roles": [mapping["role"] for mapping in trial["mappings"]],
                    "disposition": disposition,
                    "historical_status": historical["status"],
                }
            )
        else:
            raise _error("historical securities-geography status is unsupported")
    return records


def _audit_axes(
    *, sweep: Mapping[str, Any], historical_oracle: Mapping[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    clusters = []
    mappings = []
    source_table_closures = []
    unmapped_source_blanks = []
    for trial in sweep["trials"]:
        if trial["status"] != READY:
            continue
        if len(trial["candidates"]) != 1:
            raise _error("READY securities-geography trial does not have one candidate")
        candidate = trial["candidates"][0]
        document = {
            "document_ordinal": trial["document_ordinal"],
            "source_logical_name": trial["source_logical_name"],
            "source_sha256": trial["source_sha256"],
        }
        clusters.append(
            {
                **document,
                "candidate_id": candidate["candidate_id"],
                "parent_binding_kind": candidate["parent_binding_kind"],
                "projection_receipt_sha256": canonical_json_sha256_v1(
                    candidate["dual_axis_projection_receipt"]
                ),
                "source_table_refs": candidate["source_table_refs"],
                "unmapped_source_blank_roles": candidate["closure_receipt"].get(
                    "unmapped_source_blank_roles", []
                ),
            }
        )
        for mapping in candidate["mappings"]:
            mappings.append(
                {
                    **document,
                    "columns": mapping["columns"],
                    "dual_axis_lane_source_binding_id": mapping["dual_axis_lane_source_binding_id"],
                    "report_norm_id": mapping["report_norm_id"],
                    "role": mapping["role"],
                    "row_id": mapping["row_id"],
                    "values": mapping["values"],
                }
            )
        for closure in candidate["dual_axis_projection_receipt"]["source_table_equations"]:
            source_table_closures.append({**document, "closure": closure})
            for cell in closure["role_cells"]:
                if cell["value_disposition"] == "UNMAPPED_SOURCE_BLANK":
                    unmapped_source_blanks.append({**document, "cell": cell})
    return {
        "clusters": clusters,
        "historical_comparator": _historical_comparator_axis(
            sweep=sweep, historical_oracle=historical_oracle
        ),
        "mappings": mappings,
        "source_table_closures": source_table_closures,
        "unmapped_source_blanks": unmapped_source_blanks,
    }


def build_securities_geography_release_audit_v1(
    *,
    sweep: Mapping[str, Any],
    sweep_path: Path,
    selected_ids: Sequence[str],
    query_receipt: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
    historical_oracle: Mapping[str, Any],
    historical_oracle_ref: Mapping[str, Any],
) -> dict[str, Any]:
    axes = _audit_axes(sweep=sweep, historical_oracle=historical_oracle)
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
    comparator = axes["historical_comparator"]
    audit_metrics = {
        "historical_exact_mapping_count": sum(
            item["disposition"] == "EXACT_MAPPING" for item in comparator
        ),
        "historical_exact_not_observed_count": sum(
            item["disposition"] == "EXACT_NOT_OBSERVED" for item in comparator
        ),
        "historical_mismatch_count": sum(item["disposition"] == "MISMATCH" for item in comparator),
        "historical_superseded_absence_count": sum(
            item["disposition"]
            == "SUPERSEDED_BOUNDED_ABSENCE_BY_AUTHENTICATED_SELECTED_JSON_SOURCE"
            for item in comparator
        ),
        "mapping_count": axis_counts["mappings"],
        "source_table_closure_count": axis_counts["source_table_closures"],
        "unmapped_source_blank_count": axis_counts["unmapped_source_blanks"],
    }
    sweep_bytes = canonical_json_bytes_v1(sweep)
    material = {
        "axes": axes,
        "axis_counts": axis_counts,
        "axis_sha256": axis_sha256,
        "audit_metrics": audit_metrics,
        "claim_boundary": (
            "AUTHENTICATED_FROZEN_SELECTED_GEMINI_JSON_SQLITE_QUERY_AND_FULL_CANDIDATE_"
            "REPLAY_EXACT_DUAL_AXIS_SOURCE_CLOSURES_VISIBLE_ROLE_MAPPING_TYPED_UNMAPPED_"
            "SOURCE_BLANKS_AND_E0160_COMPARATOR_NO_PROVIDER_GEOMETRY_BLANK_ZERO_"
            "INFERENCE_OR_CANONICAL_EXPORT_AUTHORITY"
        ),
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_oracle_ref": dict(historical_oracle_ref),
        "query_receipt": dict(query_receipt),
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(list(selected_ids)),
        "spec_refs": dict(spec_refs),
        "state": "RELEASE_AUDIT_COMPLETE",
        "sweep_ref": {
            "path": str(sweep_path.resolve()),
            "sha256": sha256(sweep_bytes).hexdigest(),
            "size_bytes": len(sweep_bytes),
            "sweep_id": sweep["sweep_id"],
        },
    }
    return {**material, "audit_id": AUDIT_ID_PREFIX + canonical_json_sha256_v1(material)}


def validate_securities_geography_release_audit_content_v1(value: Any) -> dict[str, Any]:
    fields = {
        "audit_id",
        "axes",
        "axis_counts",
        "axis_sha256",
        "audit_metrics",
        "claim_boundary",
        "format_version",
        "historical_oracle_ref",
        "query_receipt",
        "selected_page_json_frontier_sha256",
        "spec_refs",
        "state",
        "sweep_ref",
    }
    axis_names = {
        "clusters",
        "historical_comparator",
        "mappings",
        "source_table_closures",
        "unmapped_source_blanks",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("state") != "RELEASE_AUDIT_COMPLETE"
        or type(value.get("axes")) is not dict
        or set(value["axes"]) != axis_names
        or any(type(axis) is not list for axis in value["axes"].values())
    ):
        raise _error("securities-geography release audit shape drifted")
    counts = {name: len(axis) for name, axis in value["axes"].items()}
    hashes = {name: canonical_json_sha256_v1(axis) for name, axis in value["axes"].items()}
    if value["axis_counts"] != counts or value["axis_sha256"] != hashes:
        raise _error("securities-geography release audit axis seal drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    if value["audit_id"] != AUDIT_ID_PREFIX + canonical_json_sha256_v1(material):
        raise _error("securities-geography release audit identity drifted")
    return json.loads(canonical_json_bytes_v1(value))


def validate_securities_geography_release_audit_replay_v1(
    value: Any,
    *,
    database: Path,
    sweep: Mapping[str, Any],
    sweep_path: Path,
    selected_ids: Sequence[str],
    compiled: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
    historical_oracle: Mapping[str, Any],
    historical_oracle_ref: Mapping[str, Any],
) -> dict[str, Any]:
    checked_sweep = validate_gemini_json_flat_family_sweep_v1(sweep)
    embedded = _compiled_from_sweep(checked_sweep)
    if not same_typed_json_v1(embedded, compiled):
        raise _error("securities-geography caller and embedded compiled specs differ")
    query_receipt = _query_receipt(database, selected_ids=selected_ids, compiled=embedded)
    replayed_trials = validate_selected_dual_axis_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=embedded,
        trials=checked_sweep["trials"],
    )
    if not same_typed_json_v1(replayed_trials, checked_sweep["trials"]):
        raise _error("securities-geography candidate replay changed the trial axis")
    expected = build_securities_geography_release_audit_v1(
        sweep=checked_sweep,
        sweep_path=sweep_path,
        selected_ids=selected_ids,
        query_receipt=query_receipt,
        spec_refs=spec_refs,
        historical_oracle=historical_oracle,
        historical_oracle_ref=historical_oracle_ref,
    )
    validate_securities_geography_release_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("securities-geography release audit does not replay exactly")
    return expected


def _assert_release_pins(
    *, index: Mapping[str, Any], sweep: Mapping[str, Any], audit: Mapping[str, Any]
) -> None:
    if index["corpus_manifest_index_id"] != PINNED_CORPUS_MANIFEST_INDEX_ID:
        raise _error("securities-geography corpus index release pin drifted")
    if audit["selected_page_json_frontier_sha256"] != PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256:
        raise _error("securities-geography selected frontier release pin drifted")
    if not same_typed_json_v1(sweep["metrics"], PINNED_RELEASE_METRICS):
        raise _error("securities-geography sweep metrics release pin drifted")
    if not same_typed_json_v1(audit["query_receipt"], PINNED_QUERY_RECEIPT):
        raise _error("securities-geography query receipt release pin drifted")
    expected_counts = {
        "clusters": 119,
        "historical_comparator": 14,
        "mappings": 232,
        "source_table_closures": 155,
        "unmapped_source_blanks": 6,
    }
    expected_metrics = {
        "historical_exact_mapping_count": 12,
        "historical_exact_not_observed_count": 1,
        "historical_mismatch_count": 0,
        "historical_superseded_absence_count": 1,
        "mapping_count": 232,
        "source_table_closure_count": 155,
        "unmapped_source_blank_count": 6,
    }
    if (
        audit["axis_counts"] != expected_counts
        or audit["axis_sha256"] != PINNED_RELEASE_AXIS_SHA256
        or audit["audit_metrics"] != expected_metrics
    ):
        raise _error("securities-geography release audit metric/count pins drifted")


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical_json_bytes_v1(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error("securities-geography audit output exists with different bytes")
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
    parser.add_argument("--sweep", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--historical-oracle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    raw_index = _json(args.corpus_index)
    index = validate_current_corpus_manifest_index_v1(raw_index)
    artifact_root = args.artifact_root.resolve()
    database, selected_ids = _selected_frontier(index=index, artifact_root=artifact_root)
    sweep = validate_gemini_json_flat_family_sweep_v1(_json(args.sweep))
    topology = _json(args.topology_spec)
    evaluation = _json(args.evaluation_spec)
    schema = _json(args.schema_binding_spec)
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    if not same_typed_json_v1(compiled, _compiled_from_sweep(sweep)):
        raise _error("securities-geography sweep embedded specs differ from pinned inputs")
    historical_oracle = _json(args.historical_oracle)
    historical_oracle_ref = _file_ref(args.historical_oracle, root=ROOT)
    if (
        type(historical_oracle) is not dict
        or historical_oracle.get("format_version") != PINNED_HISTORICAL_ORACLE["format_version"]
        or historical_oracle_ref
        != {key: PINNED_HISTORICAL_ORACLE[key] for key in ("path", "sha256", "size_bytes")}
    ):
        raise _error("securities-geography historical oracle authority drifted")
    spec_refs = {
        "audit_builder": _file_ref(Path(__file__), root=ROOT),
        "evaluation": _file_ref(args.evaluation_spec, root=ROOT),
        "schema_binding": _file_ref(args.schema_binding_spec, root=ROOT),
        "topology": _file_ref(args.topology_spec, root=ROOT),
    }
    with _authenticated_sqlite_source_view(
        database, expected_ref=index["database_ref"]
    ) as source_view:
        query_receipt = _query_receipt(source_view, selected_ids=selected_ids, compiled=compiled)
        validate_selected_dual_axis_family_candidate_replays_v1(
            source_view,
            selected_page_json_version_ids=selected_ids,
            compiled_specs=compiled,
            trials=sweep["trials"],
        )
        audit = build_securities_geography_release_audit_v1(
            sweep=sweep,
            sweep_path=args.sweep,
            selected_ids=selected_ids,
            query_receipt=query_receipt,
            spec_refs=spec_refs,
            historical_oracle=historical_oracle,
            historical_oracle_ref=historical_oracle_ref,
        )
        _assert_release_pins(index=index, sweep=sweep, audit=audit)
        validate_securities_geography_release_audit_replay_v1(
            audit,
            database=source_view,
            sweep=sweep,
            sweep_path=args.sweep,
            selected_ids=selected_ids,
            compiled=compiled,
            spec_refs=spec_refs,
            historical_oracle=historical_oracle,
            historical_oracle_ref=historical_oracle_ref,
        )
    _write_once(args.output, audit)
    return {
        "audit_id": audit["audit_id"],
        "audit_metrics": audit["audit_metrics"],
        "axis_counts": audit["axis_counts"],
        "disposition": "SUCCEEDED",
        "output": str(args.output),
        "output_ref": _file_ref(args.output),
    }


def main() -> int:
    try:
        result = run(_parser().parse_args())
    except BuildGeminiJsonSecuritiesGeographyReleaseAuditV1Error as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
