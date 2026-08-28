#!/usr/bin/env python3
"""Run the other-assets family over one authenticated selected JSON corpus."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import stat
import sys
import tempfile
from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
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
    validate_selected_multitable_hierarchical_family_candidate_replays_v1,
)


class RunGeminiJsonMultitableHierarchicalAccountingFamilyV1Error(RuntimeError):
    """The corpus, policy, result, or replay boundary drifted."""


def _error(message: str) -> RunGeminiJsonMultitableHierarchicalAccountingFamilyV1Error:
    return RunGeminiJsonMultitableHierarchicalAccountingFamilyV1Error(message)


AUDIT_FORMAT_VERSION = "GEMINI_JSON_MULTITABLE_HIERARCHICAL_EXPERIMENTAL_AUDIT_V1"
PINNED_CORPUS_MANIFEST_INDEX_ID = (
    "gjfccmiv1:index:61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3"
)
PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256 = (
    "601be9fc2a894af2ce4f4c982d5347521a6268a46c075d9cc96f9828baef8ae8"
)
PINNED_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "2ef86d5406a1db4d7a4809a010e03b910a2ab2a784578854dcfde0eece93fbe0"
    ),
    "accepted_cluster_count": 78,
    "accepted_fragment_count": 297,
    "candidate_disposition_axis_sha256": (
        "3eb52512f32c57ad6d1616abb0a4e4c32b35e71dc05e77e3b83281409d8de8ec"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 62, READY: 78, UNRESOLVED: 0},
    "query_policy_sha256": "0b1196a0b9f7d4eb7a77b278411414615ab1f654eddce4f3196b809d9269dfc8",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 1290,
    "not_observed_count": 62,
    "ready_count": 78,
    "unresolved_count": 0,
}
PINNED_RELEASE_AUDIT_METRICS = {
    "equation_count": 374,
    "historical_comparator_exact_count": 208,
    "historical_disposition_exact_count": 16,
    "historical_mapping_exact_count": 192,
    "historical_mapping_record_count": 192,
    "mapping_count": 1290,
}
PINNED_RELEASE_AXIS_SHA256 = {
    "clusters": "6fb676b0da7ca42e7822505aeeff6403a506331cb9450753a984b97debb08da9",
    "equations": "854ce081fde9b8e8d801112a727677e1dbc9302e67138804177690688ed4e52d",
    "historical_comparator": ("cd9cedf6863246de57d4fc01896e00a350a6ae0ec2ce1698a3cff8b76d988496"),
    "mappings": "5f33a63aee79f1dba66c0328d39e8532db98127652000c3ef7e798fce12220e3",
}
PINNED_HISTORICAL_ORACLES = (
    {
        "format_version": "OTHER_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0073-other-assets-8bank-codex-verified-mapping-v1.json",
        "sha256": "3af246132f56e8ac1a09592ce8cd4c9e302fc2ee778fe03be6fe102a0e939f5f",
        "size_bytes": 175245,
    },
    {
        "format_version": "ANNUAL_2025_OTHER_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0127-annual-2025-other-assets-8bank-codex-verified-mapping-v1.json",
        "sha256": "9cdd259b4d0d3787e7f8f9da11dfbb654cedeaf10b6c227956edead2a7ee0548",
        "size_bytes": 396487,
    },
)
_SQLITE_SIDECAR_SUFFIXES = ("-journal", "-shm", "-wal")


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
    return {"path": logical, "sha256": _sha256(resolved), "size_bytes": resolved.stat().st_size}


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


def _assert_no_sqlite_sidecars(path: Path) -> None:
    if any(os.path.lexists(f"{path}{suffix}") for suffix in _SQLITE_SIDECAR_SUFFIXES):
        raise _error("other-assets SQLite source has a journal/WAL sidecar")


def _fd_sha256(descriptor: int) -> str:
    prior = os.lseek(descriptor, 0, os.SEEK_CUR)
    digest = sha256()
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
    finally:
        os.lseek(descriptor, prior, os.SEEK_SET)
    return digest.hexdigest()


class _AuthenticatedSqliteSnapshot:
    def __init__(
        self,
        *,
        source: Path,
        source_descriptor: int,
        source_identity: tuple[int, ...],
        snapshot: Path,
        snapshot_identity: tuple[int, ...],
        expected_sha256: str,
        expected_size_bytes: int,
    ) -> None:
        self.source = source
        self.source_descriptor = source_descriptor
        self.source_identity = source_identity
        self.path = snapshot
        self.snapshot_identity = snapshot_identity
        self.expected_sha256 = expected_sha256
        self.expected_size_bytes = expected_size_bytes

    def validate(self) -> None:
        _assert_no_sqlite_sidecars(self.source)
        _assert_no_sqlite_sidecars(self.path)
        try:
            source_named = os.stat(self.source, follow_symlinks=False)
            snapshot_stat = os.stat(self.path, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise _error("authenticated other-assets SQLite path disappeared") from exc
        source_fd = os.fstat(self.source_descriptor)
        if (
            not stat.S_ISREG(source_named.st_mode)
            or not stat.S_ISREG(snapshot_stat.st_mode)
            or _file_identity(source_fd) != self.source_identity
            or _file_identity(source_named) != self.source_identity
            or _file_identity(snapshot_stat) != self.snapshot_identity
            or source_fd.st_size != self.expected_size_bytes
            or snapshot_stat.st_size != self.expected_size_bytes
            or _fd_sha256(self.source_descriptor) != self.expected_sha256
            or _sha256(self.path) != self.expected_sha256
        ):
            raise _error("authenticated other-assets SQLite bytes changed during use")


@contextmanager
def _authenticated_sqlite_snapshot(
    source: Path, *, reference: Mapping[str, Any]
) -> Iterator[_AuthenticatedSqliteSnapshot]:
    """Create one immutable source view for the whole family run."""

    _assert_no_sqlite_sidecars(source)
    descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        source_stat = os.fstat(descriptor)
        source_identity = _file_identity(source_stat)
        if (
            not stat.S_ISREG(source_stat.st_mode)
            or source_identity != _file_identity(os.stat(source, follow_symlinks=False))
            or source_stat.st_size != reference.get("size_bytes")
        ):
            raise _error("other-assets SQLite source identity drifted before snapshot")
        with tempfile.TemporaryDirectory(prefix="family22-authenticated-sqlite-") as directory:
            snapshot = Path(directory) / "page-store.sqlite3"
            output_descriptor = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
            digest = sha256()
            copied = 0
            try:
                with os.fdopen(output_descriptor, "wb") as output:
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    while block := os.read(descriptor, 1024 * 1024):
                        output.write(block)
                        digest.update(block)
                        copied += len(block)
                    output.flush()
                    os.fsync(output.fileno())
            except BaseException:
                snapshot.unlink(missing_ok=True)
                raise
            if copied != reference.get("size_bytes") or digest.hexdigest() != reference.get(
                "sha256"
            ):
                raise _error("other-assets SQLite snapshot bytes do not authenticate")
            os.chmod(snapshot, 0o444)
            guard = _AuthenticatedSqliteSnapshot(
                source=source,
                source_descriptor=descriptor,
                source_identity=source_identity,
                snapshot=snapshot,
                snapshot_identity=_file_identity(os.stat(snapshot, follow_symlinks=False)),
                expected_sha256=reference["sha256"],
                expected_size_bytes=reference["size_bytes"],
            )
            guard.validate()
            try:
                yield guard
            finally:
                guard.validate()
    finally:
        os.close(descriptor)


def _selected_page_axis(*, index: Mapping[str, Any], artifact_root: Path) -> list[str]:
    version_ids = []
    for document in index["documents"]:
        manifest = _json(_content_ref(artifact_root, document["document_manifest_ref"]))
        pages = manifest.get("pages")
        if (
            manifest.get("document_manifest_id") != document["document_manifest_id"]
            or manifest.get("page_count") != document["page_count"]
            or type(pages) is not list
            or len(pages) != document["page_count"]
        ):
            raise _error("selected document manifest identity or page axis drifted")
        version_ids.extend(page.get("page_json_version_id") for page in pages)
    if (
        len(version_ids) != index["summary"]["page_count"]
        or len(version_ids) != len(set(version_ids))
        or any(type(version_id) is not str for version_id in version_ids)
    ):
        raise _error("selected other-assets JSON frontier is incomplete or duplicate")
    return version_ids


def _historical_oracles() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    result = []
    for pinned in PINNED_HISTORICAL_ORACLES:
        path = ROOT / pinned["path"]
        value = _json(path)
        metrics = value.get("metrics")
        trials = value.get("trials")
        if (
            _sha256(path) != pinned["sha256"]
            or path.stat().st_size != pinned["size_bytes"]
            or value.get("format_version") != pinned["format_version"]
            or type(metrics) is not dict
            or type(metrics.get("mapping_verified_count")) is not int
            or type(trials) is not list
            or len(trials) != 8
            or sum(
                len(trial.get("verified_mappings", [])) for trial in trials if type(trial) is dict
            )
            != metrics["mapping_verified_count"]
        ):
            raise _error("pinned other-assets historical oracle drifted")
        result.append((dict(pinned), value))
    return result


def _trial_by_source(trials: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for trial in trials:
        source_sha256 = trial.get("source_sha256")
        if type(source_sha256) is not str or source_sha256 in result:
            raise _error("other-assets trial source axis is ambiguous")
        result[source_sha256] = trial
    return result


def _historical_comparator_axis(
    *, trials: Sequence[dict[str, Any]], compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    current_trials = _trial_by_source(trials)
    current_role_by_id = {
        report_norm_id: role for role, report_norm_id in compiled_specs["bindings"].items()
    }
    axis = []
    oracle_refs = []
    joined_sources = set()
    expected_mapping_count = 0
    for oracle_ref, oracle in _historical_oracles():
        oracle_refs.append(oracle_ref)
        expected_mapping_count += oracle["metrics"]["mapping_verified_count"]
        for oracle_trial in oracle["trials"]:
            source_sha256 = oracle_trial.get("source_pdf_sha256")
            if type(source_sha256) is not str or source_sha256 in joined_sources:
                raise _error("historical other-assets source join is duplicate or invalid")
            joined_sources.add(source_sha256)
            trial = current_trials.get(source_sha256)
            if trial is None:
                raise _error("historical other-assets source does not join one current trial")
            historical_mappings = oracle_trial.get("verified_mappings", [])
            if type(historical_mappings) is not list:
                raise _error("historical other-assets mapping axis is invalid")
            expected_status = READY if historical_mappings else NOT_OBSERVED
            axis.append(
                {
                    "actual_status": trial.get("status"),
                    "bank_provenance": oracle_trial.get("document_provenance"),
                    "disposition": (
                        "EXACT" if trial.get("status") == expected_status else "MISMATCH"
                    ),
                    "expected_status": expected_status,
                    "oracle_format_version": oracle["format_version"],
                    "record_kind": "DOCUMENT_DISPOSITION",
                    "source_sha256": source_sha256,
                }
            )
            candidates = trial.get("candidates")
            candidate = (
                candidates[0]
                if trial.get("status") == READY
                and type(candidates) is list
                and len(candidates) == 1
                else None
            )
            actual_by_id = {}
            for mapping in candidate.get("mappings", []) if candidate is not None else []:
                report_norm_id = mapping.get("report_norm_id")
                values = mapping.get("values")
                if (
                    type(report_norm_id) is not int
                    or report_norm_id in actual_by_id
                    or type(values) is not list
                    or len(values) != 2
                    or any(
                        type(value) is not dict or type(value.get("coefficient")) is not int
                        for value in values
                    )
                ):
                    raise _error("current other-assets comparator mapping axis is invalid")
                actual_by_id[report_norm_id] = mapping
            for historical in historical_mappings:
                binding = historical.get("schema_binding")
                source_values = historical.get("values")
                old_report_norm_id = (
                    binding.get("report_norm_id") if type(binding) is dict else None
                )
                historical_coefficients = (
                    [value.get("normalized_value") for value in source_values]
                    if type(source_values) is list
                    else None
                )
                current = actual_by_id.get(old_report_norm_id)
                current_coefficients = (
                    [value["coefficient"] for value in current["values"]]
                    if type(current) is dict
                    else None
                )
                exact = (
                    type(old_report_norm_id) is int
                    and type(historical_coefficients) is list
                    and len(historical_coefficients) == 2
                    and all(type(value) is int for value in historical_coefficients)
                    and current is not None
                    and current_coefficients == historical_coefficients
                )
                axis.append(
                    {
                        "bank_provenance": oracle_trial.get("document_provenance"),
                        "canonical_name": (
                            binding.get("canonical_name") if type(binding) is dict else None
                        ),
                        "current_coefficients": current_coefficients,
                        "current_role": current.get("role") if type(current) is dict else None,
                        "declared_role": current_role_by_id.get(old_report_norm_id),
                        "disposition": "EXACT" if exact else "MISMATCH",
                        "historical_coefficients": historical_coefficients,
                        "historical_report_norm_id": old_report_norm_id,
                        "oracle_format_version": oracle["format_version"],
                        "record_kind": "MAPPING_VALUE",
                        "source_sha256": source_sha256,
                    }
                )
    if len(axis) != expected_mapping_count + 16:
        raise _error("historical other-assets comparator denominator drifted")
    return axis, oracle_refs


def _audit_axes(
    *, trials: Sequence[dict[str, Any]], compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    mappings = []
    equations = []
    clusters = []
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
            mappings.append(
                {
                    **document,
                    "coefficients": [value["coefficient"] for value in mapping["values"]],
                    "report_norm_id": mapping["report_norm_id"],
                    "role": mapping["role"],
                    "row_id": mapping["row_id"],
                    "states": [value["state"] for value in mapping["values"]],
                    "unit": mapping["unit"],
                }
            )
        for equation in candidate["closure_receipt"]["equations"]:
            equations.append({**document, "equation": equation})
    comparator, oracle_refs = _historical_comparator_axis(
        trials=trials, compiled_specs=compiled_specs
    )
    return {
        "clusters": clusters,
        "equations": equations,
        "historical_comparator": comparator,
        "mappings": mappings,
    }, oracle_refs


def build_multitable_hierarchical_experimental_audit_v1(
    *,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    selected_page_json_version_ids: Sequence[str],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    """Build transparent semantic axes after the exact SQLite candidate replay."""

    axes, oracle_refs = _audit_axes(trials=trials, compiled_specs=compiled_specs)
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
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
            "AUTHENTICATED_SELECTED_GEMINI_JSON_SQLITE_REPLAY_AND_HISTORICAL_ROLE_VALUE_"
            "COMPARATOR_ONLY_NO_PROVIDER_NO_GEOMETRY_NO_CANONICAL_EXPORT_AUTHORITY"
        ),
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_oracle_refs": oracle_refs,
        "query_evidence_id": indexed_query_evidence["query_evidence_id"],
        "query_receipt": indexed_query_evidence["query_receipt"],
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            list(selected_page_json_version_ids)
        ),
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
        "audit_id": "gjmthfeav1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_multitable_hierarchical_experimental_audit_content_v1(
    value: Any,
) -> dict[str, Any]:
    fields = {
        "audit_id",
        "axes",
        "axis_counts",
        "axis_sha256",
        "audit_metrics",
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
    axis_names = {
        "clusters",
        "equations",
        "historical_comparator",
        "mappings",
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
        raise _error("other-assets experimental audit shape drifted")
    counts = {name: len(axis) for name, axis in value["axes"].items()}
    hashes = {name: canonical_json_sha256_v1(axis) for name, axis in value["axes"].items()}
    if value.get("axis_counts") != counts or value.get("axis_sha256") != hashes:
        raise _error("other-assets experimental audit axis seal drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    if value.get("audit_id") != "gjmthfeav1:audit:" + canonical_json_sha256_v1(material):
        raise _error("other-assets experimental audit identity drifted")
    return json.loads(canonical_json_bytes_v1(value))


def validate_multitable_hierarchical_experimental_audit_replay_v1(
    value: Any,
    *,
    database: Path,
    sweep: Mapping[str, Any],
    sweep_output: Path,
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
    if not same_typed_json_v1(embedded, compiled_specs):
        raise _error("other-assets caller and embedded compiled specs differ")
    if not same_typed_json_v1(checked_sweep["trials"], trials) or not same_typed_json_v1(
        checked_sweep["indexed_query_evidence"], indexed_query_evidence
    ):
        raise _error("other-assets audit sweep/query/trial axis drifted")
    validate_selected_multitable_hierarchical_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=embedded,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
    )
    expected = build_multitable_hierarchical_experimental_audit_v1(
        sweep=checked_sweep,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
        compiled_specs=embedded,
        spec_refs=spec_refs,
    )
    validate_multitable_hierarchical_experimental_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("other-assets experimental audit does not replay exactly")
    return expected


def _validate_multitable_hierarchical_experimental_audit_after_sqlite_candidate_replay_v1(
    value: Any,
    *,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    selected_page_json_version_ids: Sequence[str],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the audit envelope after the immediately preceding SQLite gate.

    The public audit replay above remains the source-authenticating entry point.
    This private runner helper avoids a third identical 8,947-page query only
    after ``validate_selected_*_candidate_replays_v1`` has already rebuilt the
    exhaustive query and every candidate from the authenticated SQLite
    snapshot in the same call frame.
    """

    checked_sweep = validate_gemini_json_flat_family_sweep_v1(sweep)
    embedded = compile_gemini_json_flat_family_specs_v1(
        checked_sweep["specs"]["topology"]["value"],
        checked_sweep["specs"]["evaluation"]["value"],
        checked_sweep["specs"]["schema_binding"]["value"],
    )
    if not same_typed_json_v1(embedded, compiled_specs):
        raise _error("other-assets caller and embedded compiled specs differ")
    if not same_typed_json_v1(checked_sweep["trials"], trials) or not same_typed_json_v1(
        checked_sweep["indexed_query_evidence"], indexed_query_evidence
    ):
        raise _error("other-assets audit sweep/query/trial axis drifted")
    expected = build_multitable_hierarchical_experimental_audit_v1(
        sweep=checked_sweep,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
        compiled_specs=embedded,
        spec_refs=spec_refs,
    )
    validate_multitable_hierarchical_experimental_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("other-assets post-SQLite audit envelope does not replay exactly")
    return expected


def _assert_release_pins(
    *,
    index: Mapping[str, Any],
    selected_ids: Sequence[str],
    sweep: Mapping[str, Any],
    indexed: Mapping[str, Any],
    audit: Mapping[str, Any],
) -> None:
    actual = {
        "audit_metrics": audit.get("audit_metrics"),
        "axis_counts": audit.get("axis_counts"),
        "axis_sha256": audit.get("axis_sha256"),
        "corpus_manifest_index_id": index.get("corpus_manifest_index_id"),
        "query_receipt": indexed.get("query_receipt"),
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(list(selected_ids)),
        "sweep_metrics": sweep.get("metrics"),
    }
    mismatches = []
    if actual["corpus_manifest_index_id"] != PINNED_CORPUS_MANIFEST_INDEX_ID:
        mismatches.append("corpus_manifest_index_id")
    if actual["selected_page_json_frontier_sha256"] != PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256:
        mismatches.append("selected_page_json_frontier_sha256")
    if not same_typed_json_v1(actual["query_receipt"], PINNED_QUERY_RECEIPT):
        mismatches.append("query_receipt")
    if not same_typed_json_v1(actual["sweep_metrics"], PINNED_RELEASE_METRICS):
        mismatches.append("sweep_metrics")
    if not same_typed_json_v1(actual["audit_metrics"], PINNED_RELEASE_AUDIT_METRICS):
        mismatches.append("audit_metrics")
    if not same_typed_json_v1(audit.get("axis_sha256"), PINNED_RELEASE_AXIS_SHA256):
        mismatches.append("axis_sha256")
    expected_axis_counts = {
        "clusters": 78,
        "equations": 374,
        "historical_comparator": 208,
        "mappings": 1290,
    }
    if any(
        actual["axis_counts"].get(name) != count for name, count in expected_axis_counts.items()
    ):
        mismatches.append("axis_counts")
    if mismatches:
        raise _error(
            "other-assets frozen corpus release pin drifted: "
            + ",".join(mismatches)
            + "; actual="
            + json.dumps(actual, ensure_ascii=False, sort_keys=True)
        )


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical_json_bytes_v1(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error("other-assets output exists with different bytes")
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


def _trials(
    *, indexed: Mapping[str, Any], candidates_by_ordinal: Mapping[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    trials = []
    for document, disposition in zip(
        indexed["selected_document_axis"], indexed["candidate_dispositions"], strict=True
    ):
        ordinal = document["document_ordinal"]
        candidate = candidates_by_ordinal.get(ordinal)
        if candidate is not None and candidate["status"] == READY:
            status = READY
            reasons = []
            mappings = candidate["mappings"]
            selected_candidate_id = candidate["candidate_id"]
        elif candidate is not None:
            status = UNRESOLVED
            reasons = candidate["reasons"]
            mappings = []
            selected_candidate_id = None
        elif disposition["disposition"] == NOT_OBSERVED:
            status = NOT_OBSERVED
            reasons = []
            mappings = []
            selected_candidate_id = None
        else:
            status = UNRESOLVED
            reasons = disposition["cluster"]["reasons"]
            mappings = []
            selected_candidate_id = None
        trials.append(
            {
                "candidate_count": int(candidate is not None),
                "candidates": [] if candidate is None else [candidate],
                "document_ordinal": ordinal,
                "mappings": mappings,
                "reasons": reasons,
                "selected_candidate_id": selected_candidate_id,
                "source_logical_name": document["source_logical_name"],
                "source_sha256": document["source_sha256"],
                "status": status,
            }
        )
    return trials


def _load_selected_pages_by_document(
    database: Path,
    *,
    selected_ids: Sequence[str],
    selected_page_axis: Sequence[Mapping[str, Any]],
) -> dict[int, dict[str, dict[str, Any]]]:
    """Decode the exact caller frontier from the already authenticated snapshot."""

    axis_by_version = {item["page_json_version_id"]: item for item in selected_page_axis}
    if len(axis_by_version) != len(selected_ids) or list(axis_by_version) != list(selected_ids):
        raise _error("other-assets selected page/evidence order drifted")
    result: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        connection.execute(
            "CREATE TEMP TABLE selected_multitable_hierarchical_runner_page("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_multitable_hierarchical_runner_page VALUES (?,?)",
            enumerate(selected_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT selected.page_json_version_id, version.canonical_json_bytes
            FROM selected_multitable_hierarchical_runner_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            ORDER BY selected.selection_ordinal
            """
        )
        loaded_ids = []
        for page_json_version_id, canonical_json_bytes in rows:
            loaded_ids.append(page_json_version_id)
            try:
                page_json = json.loads(bytes(canonical_json_bytes))
            except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error("other-assets selected canonical page JSON is invalid") from exc
            if type(page_json) is not dict:
                raise _error("other-assets selected canonical page is not one object")
            axis = axis_by_version[page_json_version_id]
            result[axis["document_ordinal"]][page_json_version_id] = page_json
    finally:
        connection.close()
    if loaded_ids != list(selected_ids):
        raise _error("other-assets selected canonical page frontier is incomplete")
    return result


def _run_with_authenticated_database(
    args: argparse.Namespace,
    *,
    index: Mapping[str, Any],
    database_guard: _AuthenticatedSqliteSnapshot,
    selected_ids: list[str],
    topology: dict[str, Any],
    evaluation: dict[str, Any],
    schema: dict[str, Any],
    compiled: dict[str, Any],
    spec_refs: dict[str, Any],
) -> dict[str, Any]:
    database = database_guard.path
    indexed = query_selected_multitable_hierarchical_family_regions_v1(
        database, selected_page_json_version_ids=selected_ids, compiled_specs=compiled
    )
    page_json_by_document = _load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=indexed["selected_page_axis"],
    )
    candidates_by_ordinal = {}
    for cluster in indexed["accepted_clusters"]:
        regions = cluster["component_regions"]
        candidates_by_ordinal[cluster["document_ordinal"]] = (
            evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[cluster["document_ordinal"]],
                compiled_specs=compiled,
                query_receipt=build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                    regions
                ),
            )
        )
    trials = _trials(indexed=indexed, candidates_by_ordinal=candidates_by_ordinal)
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=indexed,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    replayed_trials = validate_selected_multitable_hierarchical_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    if not same_typed_json_v1(replayed_trials, trials):
        raise _error("other-assets SQLite candidate replay returned a different trial axis")
    audit = build_multitable_hierarchical_experimental_audit_v1(
        sweep=sweep,
        sweep_output=args.output,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    _validate_multitable_hierarchical_experimental_audit_after_sqlite_candidate_replay_v1(
        audit,
        sweep=sweep,
        sweep_output=args.output,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    _assert_release_pins(
        index=index,
        selected_ids=selected_ids,
        sweep=sweep,
        indexed=indexed,
        audit=audit,
    )
    database_guard.validate()
    audit_output = args.output.with_suffix(".audit.json")
    _write_once(args.output, sweep)
    _write_once(audit_output, audit)
    implementation_paths = (
        ROOT
        / "scripts/experiments/run_gemini_json_multitable_hierarchical_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_multitable_hierarchical_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
    )
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=_file_ref(args.corpus_index),
        implementation_refs=[_file_ref(path, root=ROOT) for path in implementation_paths],
        run_kind=args.run_kind,
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored other-assets sweep differs from authenticated evaluation")
    output_ref = record_gemini_accounting_family_export_v1(
        args.results_database, family_run_id=stored["family_run_id"], output_path=args.output
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
    selected_ids = _selected_page_axis(index=index, artifact_root=artifact_root)
    topology = _json(args.topology_spec)
    evaluation = _json(args.evaluation_spec)
    schema = _json(args.schema_binding_spec)
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    spec_refs = {
        "evaluation": _file_ref(args.evaluation_spec, root=ROOT),
        "schema_binding": _file_ref(args.schema_binding_spec, root=ROOT),
        "topology": _file_ref(args.topology_spec, root=ROOT),
    }
    with _authenticated_sqlite_snapshot(
        source_database, reference=index["database_ref"]
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
