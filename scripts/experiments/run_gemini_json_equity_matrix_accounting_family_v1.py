#!/usr/bin/env python3
"""Run the equity-matrix family over one authenticated selected JSON corpus."""

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
    query_selected_equity_matrix_family_regions_v1,
    validate_selected_equity_matrix_family_candidate_replays_v1,
    validate_selected_equity_matrix_family_query_evidence_v1,
)


class RunGeminiJsonEquityMatrixAccountingFamilyV1Error(RuntimeError):
    """The corpus, policy, result, or replay boundary drifted."""


def _error(message: str) -> RunGeminiJsonEquityMatrixAccountingFamilyV1Error:
    return RunGeminiJsonEquityMatrixAccountingFamilyV1Error(message)


AUDIT_FORMAT_VERSION = "GEMINI_JSON_EQUITY_MATRIX_EXPERIMENTAL_AUDIT_V1"
PINNED_CORPUS_MANIFEST_INDEX_ID = (
    "gjfccmiv1:index:61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3"
)
PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256 = (
    "601be9fc2a894af2ce4f4c982d5347521a6268a46c075d9cc96f9828baef8ae8"
)
PINNED_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "51e99f3e10256a76e353d8c3a8eae140139b4c67bc3cc27023188f292442077a"
    ),
    "accepted_cluster_count": 140,
    "accepted_fragment_count": 143,
    "candidate_disposition_axis_sha256": (
        "8b7fe87e00f4dec152c53af67fc48b57908eb87a682a8380e7ba84ad7dce85c3"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 0, READY: 140, UNRESOLVED: 0},
    "query_policy_sha256": "62cfe73bd32d59ddd76d0698fa3ca41f8db90cdbe7083b8bb414ccdf49a4318f",
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
    "mapping_count": 1295,
    "not_observed_count": 0,
    "ready_count": 137,
    "unresolved_count": 3,
}
PINNED_RELEASE_AUDIT_METRICS = {
    "alignment_receipt_count": 9,
    "equation_count": 2252,
    "historical_value_match_count": 128,
    "historical_value_unresolved_count": 11,
    "mapping_count": 1295,
    "period_block_receipt_count": 95,
    "unresolved_document_count": 3,
}
PINNED_AXIS_SHA256 = {
    "alignments": "033d1a373d6235b6d68a43dd1f2207e78ff5770f4f6d4c043e7bf9b16d30be50",
    "clusters": "90c73ff6bce5366e42538f11317ce083d6ac3a19bf50e7b78c3da43008dfcb80",
    "equations": "5bf7fea93a402149052e6de8b267b9b1cdd86cbaf024c70971d520e0be8ad056",
    "historical_documents": ("68c299b58b38d439b55c7d8efee35580c715fa58a32d4f0f0abd18f9d58a63c9"),
    "historical_mappings": ("8a66588c1be57c5372dd4848bede43d7a9e286f960583070147e702b976976df"),
    "mappings": "4684728e562bfb6cfcabdd36ac276bed5534e5e55a3583b5d727d446c45af747",
    "period_blocks": "01e39b415297c45c7bf04a6bf06aa78785476bd30b9e08c6fe1be97d3cb39b8e",
    "unresolved_documents": ("03748e9a3d2535a4f335a1b815941f22829d64c68569eaa1948a970e116c9174"),
}
PINNED_HISTORICAL_ORACLES = [
    {
        "format_version": "CAPITAL_AND_FUNDS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0078-capital-and-funds-8bank-codex-verified-mapping-v1.json",
        "sha256": "f0389456e9d99abf96e98bef9fac301326106e09b6bbf3b0b44f127c0ff63aa3",
        "size_bytes": 212753,
    },
    {
        "format_version": "ANNUAL_2025_CAPITAL_AND_FUNDS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0133-annual-2025-capital-and-funds-8bank-codex-verified-mapping-v1.json",
        "sha256": "a3f1df5d8647dc0df60563d53737bafefc34604086edf94b72d7dc412559c889",
        "size_bytes": 275489,
    },
]
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
        raise _error("equity-matrix SQLite source has a journal/WAL sidecar")


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
            raise _error("authenticated equity-matrix SQLite path disappeared") from exc
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
            raise _error("authenticated equity-matrix SQLite bytes changed during use")


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
            raise _error("equity-matrix SQLite source identity drifted before snapshot")
        with tempfile.TemporaryDirectory(prefix="family27-authenticated-sqlite-") as directory:
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
                raise _error("equity-matrix SQLite snapshot bytes do not authenticate")
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
        raise _error("selected equity-matrix JSON frontier is incomplete or duplicate")
    return version_ids


def _historical_oracles() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    result = []
    for reference in PINNED_HISTORICAL_ORACLES:
        path = ROOT / reference["path"]
        value = _json(path)
        if (
            _sha256(path) != reference["sha256"]
            or path.stat().st_size != reference["size_bytes"]
            or value.get("format_version") != reference["format_version"]
            or type(value.get("trials")) is not list
            or len(value["trials"]) != 8
            or type(value.get("metrics")) is not dict
        ):
            raise _error("pinned equity-matrix historical oracle drifted")
        result.append((dict(reference), value))
    return result


def _trial_by_source(trials: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for trial in trials:
        source_sha256 = trial.get("source_sha256")
        if type(source_sha256) is not str or source_sha256 in result:
            raise _error("equity-matrix trial source axis is ambiguous")
        result[source_sha256] = trial
    return result


def _historical_comparator_axis(
    *, trials: Sequence[dict[str, Any]], compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    trials_by_source = _trial_by_source(trials)
    declared_role_by_id = {
        **{
            report_norm_id: role
            for role, report_norm_id in compiled_specs["component_report_norm_id_by_role"].items()
        },
        **{
            report_norm_id: role
            for role, report_norm_id in compiled_specs[
                "movement_total_report_norm_id_by_role"
            ].items()
        },
    }
    documents = []
    mappings = []
    oracle_refs = []
    for oracle_ref, oracle in _historical_oracles():
        oracle_refs.append(oracle_ref)
        mapping_count = 0
        for oracle_trial in oracle["trials"]:
            source_sha256 = oracle_trial.get("source_pdf_sha256")
            trial = trials_by_source.get(source_sha256)
            if trial is None:
                raise _error("historical equity-matrix source does not join one current trial")
            candidates = trial.get("candidates")
            candidate = candidates[0] if type(candidates) is list and len(candidates) == 1 else None
            current_by_id = (
                {mapping["report_norm_id"]: mapping for mapping in candidate.get("mappings", [])}
                if type(candidate) is dict
                else {}
            )
            historical_mappings = oracle_trial.get("verified_mappings")
            if type(historical_mappings) is not list:
                raise _error("historical equity-matrix mapping axis is invalid")
            documents.append(
                {
                    "current_document_ordinal": trial["document_ordinal"],
                    "current_status": trial["status"],
                    "disposition": (
                        "CURRENT_READY" if trial["status"] == READY else "CURRENT_UNRESOLVED"
                    ),
                    "document_provenance": oracle_trial.get("document_provenance"),
                    "historical_mapping_count": len(historical_mappings),
                    "historical_status": oracle_trial.get("status"),
                    "oracle_format_version": oracle["format_version"],
                    "source_sha256": source_sha256,
                }
            )
            for historical in historical_mappings:
                mapping_count += 1
                binding = historical.get("schema_binding")
                report_norm_id = binding.get("report_norm_id") if type(binding) is dict else None
                source_values = historical.get("values")
                if (
                    type(report_norm_id) is not int
                    or type(source_values) is not list
                    or not source_values
                ):
                    raise _error("historical equity-matrix mapping value axis is invalid")
                historical_axis = {}
                raw_axis_roles = {}
                for value in source_values:
                    raw_role = value.get("axis_role") if type(value) is dict else None
                    axis_role = "DECREASE" if raw_role == "DECREASE_MAGNITUDE" else raw_role
                    coefficient = value.get("normalized_value") if type(value) is dict else None
                    if (
                        axis_role not in {"OPENING", "INCREASE", "DECREASE", "CLOSING"}
                        or type(coefficient) is not int
                        or axis_role in historical_axis
                    ):
                        raise _error("historical equity-matrix movement values are invalid")
                    historical_axis[axis_role] = coefficient
                    raw_axis_roles[axis_role] = raw_role
                current = current_by_id.get(report_norm_id)
                historical_role = historical.get("role")
                comparable_historical_role = (
                    "DECREASE_TOTAL"
                    if historical_role == "DECREASE_TOTAL_MAGNITUDE"
                    else historical_role
                )
                current_axis = (
                    {
                        value["axis_role"]: (
                            abs(value["coefficient"])
                            if raw_axis_roles.get(value["axis_role"]) == "DECREASE_MAGNITUDE"
                            else value["coefficient"]
                        )
                        for value in current["values"]
                    }
                    if type(current) is dict
                    else {}
                )
                exact = (
                    current is not None
                    and current.get("role") == comparable_historical_role
                    and all(
                        current_axis.get(role) == coefficient
                        for role, coefficient in historical_axis.items()
                    )
                )
                mappings.append(
                    {
                        "current_axis": current_axis,
                        "current_role": current.get("role") if type(current) is dict else None,
                        "current_status": trial["status"],
                        "declared_role": declared_role_by_id.get(report_norm_id),
                        "disposition": (
                            "EXACT"
                            if exact
                            else "CURRENT_UNRESOLVED"
                            if trial["status"] == UNRESOLVED
                            else "MISMATCH"
                        ),
                        "document_provenance": oracle_trial.get("document_provenance"),
                        "historical_axis": historical_axis,
                        "historical_report_norm_id": report_norm_id,
                        "historical_role": historical_role,
                        "oracle_format_version": oracle["format_version"],
                        "source_sha256": source_sha256,
                    }
                )
        if mapping_count != oracle["metrics"]["mapping_verified_count"]:
            raise _error("historical equity-matrix comparator denominator drifted")
    return {"historical_documents": documents, "historical_mappings": mappings}, oracle_refs


def _audit_axes(
    *, trials: Sequence[dict[str, Any]], compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    mappings = []
    equations = []
    clusters = []
    alignments = []
    period_blocks = []
    unresolved_documents = []
    for trial in trials:
        candidates = trial.get("candidates")
        if type(candidates) is not list or len(candidates) != 1:
            continue
        candidate = candidates[0]
        document = {
            "document_ordinal": trial["document_ordinal"],
            "source_logical_name": trial["source_logical_name"],
            "source_sha256": trial["source_sha256"],
        }
        if trial.get("status") != READY:
            unresolved_documents.append(
                {
                    **document,
                    "candidate_id": candidate["candidate_id"],
                    "component_regions": candidate["component_regions"],
                    "orientation": candidate["closure_receipt"]["orientation"],
                    "reasons": candidate["reasons"],
                }
            )
            continue
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
        for receipt in candidate["closure_receipt"]["alignment_receipts"]:
            alignments.append({**document, "alignment_receipt": receipt})
        if candidate["closure_receipt"]["period_block_receipt"] is not None:
            period_blocks.append(
                {
                    **document,
                    "period_block_receipt": candidate["closure_receipt"]["period_block_receipt"],
                }
            )
    comparator_axes, oracle_refs = _historical_comparator_axis(
        trials=trials, compiled_specs=compiled_specs
    )
    return {
        "alignments": alignments,
        "clusters": clusters,
        "equations": equations,
        **comparator_axes,
        "mappings": mappings,
        "period_blocks": period_blocks,
        "unresolved_documents": unresolved_documents,
    }, oracle_refs


def build_equity_matrix_experimental_audit_v1(
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
    audit_metrics = {
        "alignment_receipt_count": axis_counts["alignments"],
        "equation_count": axis_counts["equations"],
        "historical_value_match_count": sum(
            item["disposition"] == "EXACT" for item in axes["historical_mappings"]
        ),
        "historical_value_unresolved_count": sum(
            item["disposition"] == "CURRENT_UNRESOLVED" for item in axes["historical_mappings"]
        ),
        "mapping_count": axis_counts["mappings"],
        "period_block_receipt_count": axis_counts["period_blocks"],
        "unresolved_document_count": axis_counts["unresolved_documents"],
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
        "audit_id": "gjeqmeav1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_equity_matrix_experimental_audit_content_v1(value: Any) -> dict[str, Any]:
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
        "alignments",
        "clusters",
        "equations",
        "historical_documents",
        "historical_mappings",
        "mappings",
        "period_blocks",
        "unresolved_documents",
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
        raise _error("equity-matrix experimental audit shape drifted")
    counts = {name: len(axis) for name, axis in value["axes"].items()}
    hashes = {name: canonical_json_sha256_v1(axis) for name, axis in value["axes"].items()}
    if value.get("axis_counts") != counts or value.get("axis_sha256") != hashes:
        raise _error("equity-matrix experimental audit axis seal drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    if value.get("audit_id") != "gjeqmeav1:audit:" + canonical_json_sha256_v1(material):
        raise _error("equity-matrix experimental audit identity drifted")
    return json.loads(canonical_json_bytes_v1(value))


def validate_equity_matrix_experimental_audit_replay_v1(
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
        raise _error("equity-matrix caller and embedded compiled specs differ")
    if not same_typed_json_v1(checked_sweep["trials"], trials) or not same_typed_json_v1(
        checked_sweep["indexed_query_evidence"], indexed_query_evidence
    ):
        raise _error("equity-matrix audit sweep/query/trial axis drifted")
    validate_selected_equity_matrix_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=embedded,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
    )
    expected = build_equity_matrix_experimental_audit_v1(
        sweep=checked_sweep,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
        compiled_specs=embedded,
        spec_refs=spec_refs,
    )
    validate_equity_matrix_experimental_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("equity-matrix experimental audit does not replay exactly")
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
    expected_axis_counts = {
        "alignments": 9,
        "clusters": 137,
        "equations": 2252,
        "historical_documents": 16,
        "historical_mappings": 139,
        "mappings": 1295,
        "period_blocks": 95,
        "unresolved_documents": 3,
    }
    if any(
        actual["axis_counts"].get(name) != count for name, count in expected_axis_counts.items()
    ):
        mismatches.append("axis_counts")
    if not same_typed_json_v1(actual["axis_sha256"], PINNED_AXIS_SHA256):
        mismatches.append("axis_sha256")
    if mismatches:
        raise _error(
            "equity-matrix frozen corpus release pin drifted: "
            + ",".join(mismatches)
            + "; actual="
            + json.dumps(actual, ensure_ascii=False, sort_keys=True)
        )


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical_json_bytes_v1(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error("equity-matrix output exists with different bytes")
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
        raise _error("equity-matrix selected page/evidence order drifted")
    result: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        connection.execute(
            "CREATE TEMP TABLE selected_equity_matrix_runner_page("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_equity_matrix_runner_page VALUES (?,?)",
            enumerate(selected_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT selected.page_json_version_id, version.canonical_json_bytes
            FROM selected_equity_matrix_runner_page AS selected
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
                raise _error("equity-matrix selected canonical page JSON is invalid") from exc
            if type(page_json) is not dict:
                raise _error("equity-matrix selected canonical page is not one object")
            axis = axis_by_version[page_json_version_id]
            result[axis["document_ordinal"]][page_json_version_id] = page_json
    finally:
        connection.close()
    if loaded_ids != list(selected_ids):
        raise _error("equity-matrix selected canonical page frontier is incomplete")
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
    indexed = query_selected_equity_matrix_family_regions_v1(
        database, selected_page_json_version_ids=selected_ids, compiled_specs=compiled
    )
    validate_selected_equity_matrix_family_query_evidence_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
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
            evaluate_gemini_json_equity_matrix_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[cluster["document_ordinal"]],
                compiled_specs=compiled,
                query_receipt=build_gemini_json_equity_matrix_region_query_receipt_v1(
                    regions, owner_receipt=cluster["owner_receipt"]
                ),
                document_unit_context_evidence=cluster["document_unit_context_evidence"],
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
    validate_selected_equity_matrix_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    audit = build_equity_matrix_experimental_audit_v1(
        sweep=sweep,
        sweep_output=args.output,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    validate_equity_matrix_experimental_audit_replay_v1(
        audit,
        database=database,
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
        ROOT / "scripts/experiments/run_gemini_json_equity_matrix_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_equity_matrix_accounting_family_v1.py",
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
        raise _error("stored equity-matrix sweep differs from authenticated evaluation")
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
