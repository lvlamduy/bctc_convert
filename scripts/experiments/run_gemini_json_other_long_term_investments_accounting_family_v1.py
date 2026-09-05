#!/usr/bin/env python3
"""Run the other-long-term-investments family over one authenticated selected JSON corpus."""

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
from bctc_ai.evaluation.gemini_json_other_long_term_investments_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_other_long_term_investments_region_query_receipt_v1,
    evaluate_gemini_json_other_long_term_investments_family_cluster_v1,
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
    query_selected_other_long_term_investments_family_regions_v1,
    validate_selected_other_long_term_investments_family_candidate_replays_v1,
    validate_selected_other_long_term_investments_family_query_evidence_v1,
)


class RunGeminiJsonOtherLongTermInvestmentsAccountingFamilyV1Error(RuntimeError):
    """The corpus, policy, result, or replay boundary drifted."""


def _error(message: str) -> RunGeminiJsonOtherLongTermInvestmentsAccountingFamilyV1Error:
    return RunGeminiJsonOtherLongTermInvestmentsAccountingFamilyV1Error(message)


AUDIT_FORMAT_VERSION = "GEMINI_JSON_OTHER_LONG_TERM_INVESTMENTS_EXPERIMENTAL_AUDIT_V1"
PINNED_CORPUS_MANIFEST_INDEX_ID = (
    "gjfccmiv1:index:61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3"
)
PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256 = (
    "601be9fc2a894af2ce4f4c982d5347521a6268a46c075d9cc96f9828baef8ae8"
)
PINNED_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "689d3511ad9c3dde89697e65d68837b3dd02c236a4b85c5ab8a1d5db6440b745"
    ),
    "accepted_cluster_count": 140,
    "accepted_fragment_count": 290,
    "candidate_disposition_axis_sha256": (
        "78208f8a7006d93d541a316d0b79e148fc27959386675b8d390c01c00e86fdcb"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 0, READY: 140, UNRESOLVED: 0},
    "query_policy_sha256": "29e686499f9f41c2c9a7009d647f0f1a420909696916fd567e70cd9a9a13d5ef",
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
    "mapping_count": 431,
    "not_observed_count": 0,
    "ready_count": 140,
    "unresolved_count": 0,
}
PINNED_RELEASE_AUDIT_METRICS = {
    "equation_count": 480,
    "historical_value_match_count": 57,
    "mapping_count": 431,
}
PINNED_RELEASE_AXIS_SHA256 = {
    "clusters": "4c928e994c385513679760b84458f88b390a7468feb22f0eed236653f70b938f",
    "equations": "ea62e49a9ee4f3ae18b3863dd7a6dec6de079dfbf13e48953b4844b5f390ec02",
    "historical_comparator": ("07bfecaf4fc1c38b1579f61fe1d075e52c8185241aa8c58b3d61bde401402681"),
    "mappings": "c40dc03a1030a091cee28c221c6854c566f2ec8b6a2282aac5af54257e836a41",
}
PINNED_HISTORICAL_ORACLES = (
    {
        "format_version": "LONG_TERM_INVESTMENTS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0068-long-term-investments-8bank-codex-verified-mapping-v1.json",
        "sha256": "6a83a386074494fe0b68761f66f4a1c09f50bb07f3d5a4ded3756167c5a8716a",
        "size_bytes": 54580,
    },
    {
        "format_version": "ANNUAL_2025_LONG_TERM_INVESTMENTS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0122-annual-2025-long-term-investments-8bank-codex-verified-mapping-v1.json",
        "sha256": "e47b3e479025fa8f919df0099748def15a9a695ccde33851c9754a06a55adc9c",
        "size_bytes": 53884,
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
        raise _error("other-long-term-investments SQLite source has a journal/WAL sidecar")


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
            raise _error(
                "authenticated other-long-term-investments SQLite path disappeared"
            ) from exc
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
            raise _error(
                "authenticated other-long-term-investments SQLite bytes changed during use"
            )


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
            raise _error(
                "other-long-term-investments SQLite source identity drifted before snapshot"
            )
        with tempfile.TemporaryDirectory(prefix="family17-authenticated-sqlite-") as directory:
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
                raise _error(
                    "other-long-term-investments SQLite snapshot bytes do not authenticate"
                )
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
        raise _error(
            "selected other-long-term-investments JSON frontier is incomplete or duplicate"
        )
    return version_ids


def _authenticate_source_repair_manifest_axis_v1(
    *,
    index: Mapping[str, Any],
    artifact_root: Path,
    compiled_specs: Mapping[str, Any],
) -> list[str]:
    """Bind every in-corpus repair to its authenticated document/page render."""

    overlay = compiled_specs.get("source_repair_overlay")
    if type(overlay) is not dict or type(overlay.get("repairs")) is not list:
        raise _error("other-long-term-investments source-repair overlay is absent")
    document_by_source = {}
    for document in index["documents"]:
        source_sha256 = document.get("source_sha256")
        if type(source_sha256) is not str or source_sha256 in document_by_source:
            raise _error("other-long-term-investments manifest source axis is invalid")
        document_by_source[source_sha256] = document
    authenticated = []
    for repair in overlay["repairs"]:
        document = document_by_source.get(repair["source_sha256"])
        if document is None:
            continue
        if document.get("relative_path") != repair["source_logical_name"]:
            raise _error("other-long-term-investments source-repair document path drifted")
        manifest = _json(_content_ref(artifact_root, document["document_manifest_ref"]))
        pages = manifest.get("pages")
        if (
            manifest.get("document_manifest_id") != document["document_manifest_id"]
            or manifest.get("page_count") != document["page_count"]
            or type(pages) is not list
            or len(pages) != document["page_count"]
        ):
            raise _error("other-long-term-investments source-repair manifest drifted")
        matches = [
            page
            for page in pages
            if type(page) is dict
            and page.get("physical_page") == repair["physical_page"]
            and page.get("page_json_version_id") == repair["page_json_version_id"]
        ]
        if len(matches) != 1 or not same_typed_json_v1(
            matches[0].get("image"), repair["page_image"]
        ):
            raise _error("other-long-term-investments source-repair page/image drifted")
        authenticated.append(repair["repair_id"])
    if authenticated != sorted(authenticated):
        authenticated.sort()
    if len(authenticated) != len(set(authenticated)):
        raise _error("other-long-term-investments source-repair manifest axis is duplicate")
    return authenticated


def _validate_source_repair_application_axis_v1(
    *,
    expected_repair_ids: Sequence[str],
    trials: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Require every authenticated in-corpus repair to be applied exactly once."""

    observed = []
    for trial in trials:
        for candidate in trial.get("candidates", []):
            closure = candidate.get("closure_receipt") if type(candidate) is dict else None
            receipts = (
                closure.get("source_repair_overlay_receipts", []) if type(closure) is dict else []
            )
            if type(receipts) is not list:
                raise _error("other-long-term-investments source-repair receipt axis is invalid")
            for receipt in receipts:
                repair_id = receipt.get("repair_id") if type(receipt) is dict else None
                if type(repair_id) is not str:
                    raise _error("other-long-term-investments source-repair receipt is invalid")
                observed.append(repair_id)
    observed.sort()
    if observed != sorted(expected_repair_ids) or len(observed) != len(set(observed)):
        raise _error("other-long-term-investments source-repair application axis is incomplete")
    return observed


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
            raise _error("pinned other-long-term-investments historical oracle drifted")
        result.append(({**pinned, "expected_trial_count": len(trials)}, value))
    return result


def _normalised_historical_oracle_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    refs = []
    rows = []
    for oracle_ref_index, (oracle_ref, oracle) in enumerate(_historical_oracles()):
        refs.append(oracle_ref)
        for oracle_trial in oracle["trials"]:
            source_sha256 = oracle_trial.get("source_pdf_sha256")
            if type(source_sha256) is not str:
                raise _error("historical other-long-term-investments source identity is invalid")
            rows.append(
                {
                    "oracle_format_version": oracle["format_version"],
                    "oracle_ref_index": oracle_ref_index,
                    "oracle_trial": oracle_trial,
                    "source_sha256": source_sha256,
                }
            )
    return refs, rows


def _strict_historical_compare(
    oracle_row: Mapping[str, Any],
    current_trial: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    candidates = current_trial.get("candidates")
    if current_trial.get("status") != READY or type(candidates) is not list or len(candidates) != 1:
        raise _error(
            "historical other-long-term-investments source does not join one READY candidate"
        )
    candidate = candidates[0]
    current_role_by_id = {
        report_norm_id: role for role, report_norm_id in compiled_specs["bindings"].items()
    }
    axis = []
    actual_by_id = {}
    for mapping in candidate.get("mappings", []):
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
            raise _error("current other-long-term-investments comparator mapping axis is invalid")
        actual_by_id[report_norm_id] = mapping
    oracle_trial = oracle_row["oracle_trial"]
    for historical in oracle_trial.get("verified_mappings", []):
        binding = historical.get("schema_binding")
        source_values = historical.get("values")
        old_report_norm_id = binding.get("report_norm_id") if type(binding) is dict else None
        historical_coefficients = (
            [value.get("normalized_value") for value in source_values]
            if type(source_values) is list
            else None
        )
        current = actual_by_id.get(old_report_norm_id)
        current_coefficients = (
            [value["coefficient"] for value in current["values"]] if type(current) is dict else None
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
                "canonical_name": binding.get("canonical_name") if type(binding) is dict else None,
                "current_coefficients": current_coefficients,
                "current_role": current.get("role") if type(current) is dict else None,
                "declared_role": current_role_by_id.get(old_report_norm_id),
                "disposition": "EXACT" if exact else "MISMATCH",
                "historical_coefficients": historical_coefficients,
                "historical_report_norm_id": old_report_norm_id,
                "oracle_format_version": oracle_row["oracle_format_version"],
                "source_sha256": oracle_row["source_sha256"],
            }
        )
    if not axis or any(item["disposition"] != "EXACT" for item in axis):
        raise _error("historical other-long-term-investments comparator is not exact")
    return {"axis": axis, "disposition": EXACT_HISTORICAL_COMPARISON}


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
    oracle_refs, oracle_rows = _normalised_historical_oracle_rows()
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
        strict_compare=(
            lambda oracle, current: _strict_historical_compare(
                oracle, current, compiled_specs=compiled_specs
            )
        )
        if policy == STRICT_RELEASE
        else None,
    )
    if policy == DISJOINT_EXPANSION:
        if (
            policy_receipt["disposition"] != NOT_APPLICABLE_DISJOINT_CORPUS
            or policy_receipt["comparison_axis"] != []
        ):
            raise _error("disjoint other-long-term-investments comparator receipt drifted")
        return [], oracle_refs, policy_receipt
    axis = [
        row
        for comparison in policy_receipt["comparison_axis"]
        for row in comparison["comparison"]["axis"]
    ]
    expected_mapping_count = sum(
        oracle["metrics"]["mapping_verified_count"] for _ref, oracle in _historical_oracles()
    )
    if len(axis) != expected_mapping_count or any(item["disposition"] != "EXACT" for item in axis):
        raise _error("historical other-long-term-investments comparator denominator drifted")
    return axis, oracle_refs, policy_receipt


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
        raise _error("other-long-term-investments indexed candidate/replay axes drifted")
    comparator, oracle_refs, comparator_policy_receipt = _historical_comparator_axis(
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
        },
        oracle_refs,
        comparator_policy_receipt,
    )


def build_other_long_term_investments_experimental_audit_v1(
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
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    """Build transparent semantic axes after the exact SQLite candidate replay."""

    if sweep.get("corpus_manifest_index_id") != current_manifest_index_id:
        raise _error("other-long-term-investments sweep/current manifest identity drifted")
    axes, oracle_refs, comparator_policy_receipt = _audit_axes(
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
    audit_metrics = {
        "equation_count": axis_counts["equations"],
        "historical_value_match_count": sum(
            item["disposition"] == "EXACT" for item in axes["historical_comparator"]
        )
        if historical_comparator_policy == STRICT_RELEASE
        else None,
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
        "historical_comparator_policy_receipt": comparator_policy_receipt,
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
        "audit_id": "gjfoltieav1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_other_long_term_investments_experimental_audit_content_v1(
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
        "historical_comparator_policy_receipt",
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
        raise _error("other-long-term-investments experimental audit shape drifted")
    counts = {name: len(axis) for name, axis in value["axes"].items()}
    hashes = {name: canonical_json_sha256_v1(axis) for name, axis in value["axes"].items()}
    if value.get("axis_counts") != counts or value.get("axis_sha256") != hashes:
        raise _error("other-long-term-investments experimental audit axis seal drifted")
    policy_receipt = value.get("historical_comparator_policy_receipt")
    policy = policy_receipt.get("policy") if type(policy_receipt) is dict else None
    disposition = policy_receipt.get("disposition") if type(policy_receipt) is dict else None
    expected_oracle_refs = [reference for reference, _oracle in _historical_oracles()]
    if (
        type(policy_receipt) is not dict
        or policy_receipt.get("format_version") != HISTORICAL_COMPARATOR_POLICY_FORMAT_VERSION
        or policy not in {STRICT_RELEASE, DISJOINT_EXPANSION}
        or type(policy_receipt.get("comparison_axis")) is not list
        or type(policy_receipt.get("oracle_authentication")) is not dict
        or type(policy_receipt.get("corpus_relation")) is not dict
        or type(policy_receipt.get("current_axis_validation")) is not dict
        or value.get("historical_oracle_refs") != expected_oracle_refs
        or policy_receipt["oracle_authentication"].get("refs") != expected_oracle_refs
        or policy_receipt["current_axis_validation"].get("manifest_document_count")
        != value.get("query_receipt", {}).get("selected_document_count")
        or policy_receipt["current_axis_validation"].get("trial_source_count")
        != value.get("query_receipt", {}).get("selected_document_count")
        or policy_receipt["current_axis_validation"].get("candidate_source_count")
        != value.get("query_receipt", {}).get("accepted_cluster_count")
        or policy_receipt["current_axis_validation"].get("replay_source_count")
        != value.get("query_receipt", {}).get("accepted_cluster_count")
        or policy_receipt["current_axis_validation"].get("selected_page_json_version_count")
        != value.get("query_receipt", {}).get("selected_page_count")
    ):
        raise _error("other-long-term-investments historical comparator policy receipt drifted")
    metrics = value.get("audit_metrics")
    if policy == STRICT_RELEASE:
        if (
            disposition != EXACT_HISTORICAL_COMPARISON
            or not value["axes"]["historical_comparator"]
            or type(metrics) is not dict
            or type(metrics.get("historical_value_match_count")) is not int
        ):
            raise _error("other-long-term-investments strict comparator audit drifted")
    elif (
        disposition != NOT_APPLICABLE_DISJOINT_CORPUS
        or policy_receipt["comparison_axis"] != []
        or policy_receipt["corpus_relation"].get("overlap_count") != 0
        or value["axes"]["historical_comparator"] != []
        or type(metrics) is not dict
        or metrics.get("historical_value_match_count") is not None
    ):
        raise _error("other-long-term-investments disjoint comparator audit drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    if value.get("audit_id") != "gjfoltieav1:audit:" + canonical_json_sha256_v1(material):
        raise _error("other-long-term-investments experimental audit identity drifted")
    return json.loads(canonical_json_bytes_v1(value))


def validate_other_long_term_investments_experimental_audit_replay_v1(
    value: Any,
    *,
    database: Path,
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
    if not same_typed_json_v1(embedded, compiled_specs):
        raise _error("other-long-term-investments caller and embedded compiled specs differ")
    if not same_typed_json_v1(checked_sweep["trials"], trials) or not same_typed_json_v1(
        checked_sweep["indexed_query_evidence"], indexed_query_evidence
    ):
        raise _error("other-long-term-investments audit sweep/query/trial axis drifted")
    validate_selected_other_long_term_investments_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=embedded,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
    )
    expected = build_other_long_term_investments_experimental_audit_v1(
        sweep=checked_sweep,
        sweep_output=sweep_output,
        historical_comparator_policy=historical_comparator_policy,
        current_manifest_index_id=current_manifest_index_id,
        current_manifest_source_sha256s=current_manifest_source_sha256s,
        selected_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
        compiled_specs=embedded,
        spec_refs=spec_refs,
    )
    validate_other_long_term_investments_experimental_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("other-long-term-investments experimental audit does not replay exactly")
    return expected


def _assert_release_pins(
    *,
    historical_comparator_policy: str,
    run_kind: str,
    index: Mapping[str, Any],
    selected_ids: Sequence[str],
    sweep: Mapping[str, Any],
    indexed: Mapping[str, Any],
    audit: Mapping[str, Any],
) -> None:
    if historical_comparator_policy == DISJOINT_EXPANSION:
        if run_kind != "EXPERIMENTAL":
            raise _error("OFFICIAL other-long-term-investments run requires STRICT_RELEASE policy")
        return
    if historical_comparator_policy != STRICT_RELEASE:
        raise _error("other-long-term-investments historical comparator policy is undeclared")
    actual = {
        "audit_metrics": audit.get("audit_metrics"),
        "axis_counts": audit.get("axis_counts"),
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
        "clusters": 140,
        "equations": 480,
        "historical_comparator": 57,
        "mappings": 431,
    }
    if any(
        actual["axis_counts"].get(name) != count for name, count in expected_axis_counts.items()
    ):
        mismatches.append("axis_counts")
    if mismatches:
        raise _error(
            "other-long-term-investments frozen corpus release pin drifted: "
            + ",".join(mismatches)
            + "; actual="
            + json.dumps(actual, ensure_ascii=False, sort_keys=True)
        )


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical_json_bytes_v1(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error("other-long-term-investments output exists with different bytes")
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
        raise _error("other-long-term-investments selected page/evidence order drifted")
    result: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        connection.execute(
            "CREATE TEMP TABLE selected_other_long_term_investments_runner_page("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_other_long_term_investments_runner_page VALUES (?,?)",
            enumerate(selected_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT selected.page_json_version_id, version.canonical_json_bytes
            FROM selected_other_long_term_investments_runner_page AS selected
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
                raise _error(
                    "other-long-term-investments selected canonical page JSON is invalid"
                ) from exc
            if type(page_json) is not dict:
                raise _error(
                    "other-long-term-investments selected canonical page is not one object"
                )
            axis = axis_by_version[page_json_version_id]
            result[axis["document_ordinal"]][page_json_version_id] = page_json
    finally:
        connection.close()
    if loaded_ids != list(selected_ids):
        raise _error("other-long-term-investments selected canonical page frontier is incomplete")
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
    expected_source_repair_ids: Sequence[str],
    spec_refs: dict[str, Any],
) -> dict[str, Any]:
    database = database_guard.path
    indexed = query_selected_other_long_term_investments_family_regions_v1(
        database, selected_page_json_version_ids=selected_ids, compiled_specs=compiled
    )
    validate_selected_other_long_term_investments_family_query_evidence_v1(
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
            evaluate_gemini_json_other_long_term_investments_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[cluster["document_ordinal"]],
                compiled_specs=compiled,
                query_receipt=build_gemini_json_other_long_term_investments_region_query_receipt_v1(
                    regions
                ),
            )
        )
    trials = _trials(indexed=indexed, candidates_by_ordinal=candidates_by_ordinal)
    _validate_source_repair_application_axis_v1(
        expected_repair_ids=expected_source_repair_ids,
        trials=trials,
    )
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=indexed,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    validate_selected_other_long_term_investments_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    audit = build_other_long_term_investments_experimental_audit_v1(
        sweep=sweep,
        sweep_output=args.output,
        historical_comparator_policy=args.historical_comparator_policy,
        current_manifest_index_id=index["corpus_manifest_index_id"],
        current_manifest_source_sha256s=[
            document["source_sha256"] for document in index["documents"]
        ],
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    validate_other_long_term_investments_experimental_audit_replay_v1(
        audit,
        database=database,
        sweep=sweep,
        sweep_output=args.output,
        historical_comparator_policy=args.historical_comparator_policy,
        current_manifest_index_id=index["corpus_manifest_index_id"],
        current_manifest_source_sha256s=[
            document["source_sha256"] for document in index["documents"]
        ],
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    _assert_release_pins(
        historical_comparator_policy=args.historical_comparator_policy,
        run_kind=args.run_kind,
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
        / "scripts/experiments/run_gemini_json_other_long_term_investments_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_other_long_term_investments_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/historical_comparator_policy_v1.py",
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
        raise _error(
            "stored other-long-term-investments sweep differs from authenticated evaluation"
        )
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
        "historical_comparator_policy": args.historical_comparator_policy,
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "output_ref": output_ref,
        "results_database": str(args.results_database),
        "run_kind": args.run_kind,
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.run_kind == "OFFICIAL" and args.historical_comparator_policy != STRICT_RELEASE:
        raise _error("OFFICIAL other-long-term-investments run requires STRICT_RELEASE policy")
    index = validate_current_corpus_manifest_index_v1(_json(args.corpus_index))
    artifact_root = args.artifact_root.resolve()
    source_database = _content_ref(artifact_root, index["database_ref"])
    selected_ids = _selected_page_axis(index=index, artifact_root=artifact_root)
    topology = _json(args.topology_spec)
    evaluation = _json(args.evaluation_spec)
    schema = _json(args.schema_binding_spec)
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    expected_source_repair_ids = _authenticate_source_repair_manifest_axis_v1(
        index=index,
        artifact_root=artifact_root,
        compiled_specs=compiled,
    )
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
            expected_source_repair_ids=expected_source_repair_ids,
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
