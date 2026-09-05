#!/usr/bin/env python3
"""Run the customer-deposit family over one authenticated selected JSON corpus."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import stat
import sys
import tempfile
from collections import Counter, defaultdict
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_customer_deposit_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    bind_gemini_json_customer_deposit_source_repairs_v1,
    build_gemini_json_customer_deposit_region_query_receipt_v1,
    evaluate_gemini_json_customer_deposit_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_first_page_render_v1 import (  # noqa: E402
    render_full_pdf_page_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
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
    query_selected_customer_deposit_family_regions_v1,
    validate_selected_customer_deposit_family_candidate_replays_v1,
    validate_selected_customer_deposit_family_query_evidence_v1,
)


class RunGeminiJsonCustomerDepositAccountingFamilyV1Error(RuntimeError):
    """The corpus, policy, result, or replay boundary drifted."""


def _error(message: str) -> RunGeminiJsonCustomerDepositAccountingFamilyV1Error:
    return RunGeminiJsonCustomerDepositAccountingFamilyV1Error(message)


AUDIT_FORMAT_VERSION = "GEMINI_JSON_CUSTOMER_DEPOSIT_EXPERIMENTAL_AUDIT_V1"
PINNED_CORPUS_MANIFEST_INDEX_ID = (
    "gjfccmiv1:index:61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3"
)
PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256 = (
    "601be9fc2a894af2ce4f4c982d5347521a6268a46c075d9cc96f9828baef8ae8"
)
PINNED_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "f3bb3807e1f8feb485a7494c95abadc1ffa5f80f3c0f66bbe83a1757d43ab1b6"
    ),
    "accepted_cluster_count": 140,
    "accepted_fragment_count": 222,
    "candidate_disposition_axis_sha256": (
        "0bfb088f30ab9e634bccf4d16f8b34e784732fe2e796c2cb82fb2bb56fed6c99"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 0, READY: 140, UNRESOLVED: 0},
    "query_policy_sha256": "6afb851279e239c8c79a22f26ca26c07c89d39236cd420e36841aef5fd9c308d",
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
    "mapping_count": 2189,
    "not_observed_count": 0,
    "ready_count": 140,
    "unresolved_count": 0,
}
PINNED_RELEASE_AUDIT_METRICS = {
    "equation_count": 732,
    "historical_direct_binding_count": 151,
    "historical_schema_id_migration_count": 2,
    "historical_schema_role_rename_count": 2,
    "historical_value_match_count": 155,
    "optional_customer_view_dispositions": {
        "ABSENT": 70,
        "INCLUDED_EXACT_OPTIONAL_CUSTOMER_VIEW": 70,
    },
    "source_repair_count": 6,
}
PINNED_HISTORICAL_ORACLE = {
    "format_version": "ANNUAL_2025_CUSTOMER_DEPOSIT_8BANK_CODEX_VERIFIED_MAPPING_V1",
    "path": "docs/experiments/E-0129-annual-2025-customer-deposit-8bank-codex-verified-mapping-v1.json",
    "sha256": "0d832b33929523846a45d33644fcd95c4a7b8f5c12072da8457a78fa9030f394",
    "size_bytes": 198448,
}
SOURCE_REPAIR_SPEC_PATH = (
    ROOT / "data/registered/gemini_json_customer_deposit_source_repairs_v1.json"
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


def _authenticate_source_repairs_v1(
    *, repairs: list[dict[str, Any]], source_pdf_root: Path
) -> list[dict[str, Any]]:
    """Replay every registered full-page render and RGB crop binding."""

    root = source_pdf_root.resolve()
    if source_pdf_root.is_symlink() or not root.is_dir():
        raise _error("customer-deposit repair source root is unavailable")
    source_payloads: dict[tuple[str, str, int], bytes] = {}
    render_cache: dict[tuple[str, int], tuple[bytes, dict[str, Any]]] = {}
    checked = []
    for repair in repairs:
        source = repair["source"]
        locator = repair["locator"]
        logical_name = source["source_logical_name"]
        path = (root / logical_name).resolve()
        if not path.is_relative_to(root) or path.is_symlink() or not path.is_file():
            raise _error("customer-deposit repair source path is unavailable")
        source_key = (
            logical_name,
            source["source_sha256"],
            source["source_size_bytes"],
        )
        payload = source_payloads.get(source_key)
        if payload is None:
            payload = path.read_bytes()
            if (
                len(payload) != source["source_size_bytes"]
                or sha256(payload).hexdigest() != source["source_sha256"]
            ):
                raise _error("customer-deposit repair source artifact drifted")
            source_payloads[source_key] = payload
        cache_key = (logical_name, locator["physical_page"])
        cached = render_cache.get(cache_key)
        if cached is None:
            with fitz.open(stream=payload, filetype="pdf") as document:
                if locator["physical_page"] > len(document):
                    raise _error(
                        "customer-deposit repair physical page is outside its PDF"
                    )
                rendered = render_full_pdf_page_v1(
                    document[locator["physical_page"] - 1],
                    physical_page=locator["physical_page"],
                    dpi=300,
                    source_sha256=source["source_sha256"],
                )
            cached = rendered.image, rendered.receipt
            render_cache[cache_key] = cached
        image_bytes, render_receipt = cached
        with Image.open(BytesIO(image_bytes)) as image:
            image.load()
            rgb = image.convert("RGB")
            bbox = repair["crop_evidence"]["bbox_pixels_xyxy"]
            crop = rgb.crop(tuple(bbox))
            actual_render = {
                "image_sha256": sha256(image_bytes).hexdigest(),
                "image_size_bytes": len(image_bytes),
                "media_type": "image/png",
                "physical_page": locator["physical_page"],
                "pixel_height": rgb.height,
                "pixel_width": rgb.width,
                "render_dpi": 300,
                "render_receipt_sha256": canonical_json_sha256_v1(render_receipt),
            }
            actual_crop = {
                "bbox_pixels_xyxy": bbox,
                "pixel_height": crop.height,
                "pixel_width": crop.width,
                "rgb_sha256": sha256(crop.tobytes()).hexdigest(),
            }
        if (
            actual_render != repair["render"]
            or actual_crop != repair["crop_evidence"]
        ):
            raise _error("customer-deposit repair render or crop evidence drifted")
        checked.append(canonical_clone_v1(repair))
    return checked


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
        raise _error("customer-deposit SQLite source has a journal/WAL sidecar")


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
            raise _error("authenticated customer-deposit SQLite path disappeared") from exc
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
            raise _error("authenticated customer-deposit SQLite bytes changed during use")


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
            raise _error("customer-deposit SQLite source identity drifted before snapshot")
        with tempfile.TemporaryDirectory(prefix="family15-authenticated-sqlite-") as directory:
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
                raise _error("customer-deposit SQLite snapshot bytes do not authenticate")
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
        raise _error("selected customer-deposit JSON frontier is incomplete or duplicate")
    return version_ids


def _historical_oracle() -> tuple[dict[str, Any], dict[str, Any]]:
    path = ROOT / PINNED_HISTORICAL_ORACLE["path"]
    value = _json(path)
    if (
        _sha256(path) != PINNED_HISTORICAL_ORACLE["sha256"]
        or path.stat().st_size != PINNED_HISTORICAL_ORACLE["size_bytes"]
        or value.get("format_version") != PINNED_HISTORICAL_ORACLE["format_version"]
        or type(value.get("trials")) is not list
        or len(value["trials"]) != 8
    ):
        raise _error("pinned customer-deposit historical oracle drifted")
    return dict(PINNED_HISTORICAL_ORACLE), value


def _candidate_by_source(trials: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for trial in trials:
        candidates = trial.get("candidates")
        if trial.get("status") != READY or type(candidates) is not list or len(candidates) != 1:
            continue
        source_sha256 = trial.get("source_sha256")
        if type(source_sha256) is not str or source_sha256 in result:
            raise _error("customer-deposit candidate source axis is ambiguous")
        result[source_sha256] = candidates[0]
    return result


def _historical_comparator_axis(
    *, trials: Sequence[dict[str, Any]], compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    oracle_ref, oracle = _historical_oracle()
    oracle_sources = {trial.get("source_pdf_sha256") for trial in oracle["trials"]}
    trial_sources = {trial.get("source_sha256") for trial in trials}
    overlap = oracle_sources & trial_sources
    if not overlap:
        # The immutable 19-bank expansion corpus deliberately excludes the
        # original eight-bank oracle.  An entirely disjoint source frontier has
        # no historical comparisons; a partial overlap is rejected below so a
        # caller cannot silently omit only the inconvenient oracle documents.
        return [], oracle_ref
    if overlap != oracle_sources:
        raise _error("historical customer-deposit source frontier is only partially present")
    candidates = _candidate_by_source(trials)
    current_role_by_id = {
        report_norm_id: role for role, report_norm_id in compiled_specs["bindings"].items()
    }
    axis = []
    for oracle_trial in oracle["trials"]:
        source_sha256 = oracle_trial.get("source_pdf_sha256")
        candidate = candidates.get(source_sha256)
        if candidate is None:
            raise _error("historical customer-deposit source does not join one READY candidate")
        actual_by_role = {}
        for mapping in candidate.get("mappings", []):
            role = mapping.get("role")
            values = mapping.get("values")
            if (
                type(role) is not str
                or role in actual_by_role
                or type(values) is not list
                or len(values) != 2
                or type(values[0].get("coefficient")) is not int
            ):
                raise _error("current customer-deposit comparator mapping axis is invalid")
            actual_by_role[role] = mapping
        for historical in oracle_trial.get("verified_mappings", []):
            historical_role = historical.get("role")
            old_report_norm_id = historical.get("report_norm_id")
            old_coefficient = historical.get("normalized_value")
            current_role = (
                historical_role
                if historical_role in compiled_specs["bindings"]
                else current_role_by_id.get(old_report_norm_id)
            )
            current_report_norm_id = compiled_specs["bindings"].get(current_role)
            current = actual_by_role.get(current_role)
            current_coefficient = (
                current["values"][0]["coefficient"] if type(current) is dict else None
            )
            exact = (
                type(old_report_norm_id) is int
                and type(old_coefficient) is int
                and type(current_report_norm_id) is int
                and current is not None
                and current.get("report_norm_id") == current_report_norm_id
                and current_coefficient == old_coefficient
            )
            axis.append(
                {
                    "current_coefficient": current_coefficient,
                    "current_report_norm_id": current_report_norm_id,
                    "disposition": (
                        "EXACT_SAME_SCHEMA_BINDING"
                        if exact
                        and historical_role == current_role
                        and old_report_norm_id == current_report_norm_id
                        else "EXACT_DECLARED_SCHEMA_ROLE_RENAME"
                        if exact and historical_role != current_role
                        else "EXACT_DECLARED_SCHEMA_ID_MIGRATION"
                        if exact
                        else "MISMATCH"
                    ),
                    "current_role": current_role,
                    "document_provenance": oracle_trial.get("document_provenance"),
                    "historical_coefficient": old_coefficient,
                    "historical_report_norm_id": old_report_norm_id,
                    "historical_role": historical_role,
                    "source_sha256": source_sha256,
                }
            )
    if len(axis) != oracle["metrics"]["mapping_verified_count"]:
        raise _error("historical customer-deposit comparator denominator drifted")
    return axis, oracle_ref


def _audit_axes(
    *, trials: Sequence[dict[str, Any]], compiled_specs: Mapping[str, Any]
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    mappings = []
    equations = []
    optional_customer_views = []
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
                "query_receipt_id": candidate["closure_receipt"]["query_receipt"][
                    "query_receipt_id"
                ],
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
        customer_view = candidate["closure_receipt"].get("customer_view")
        optional_customer_views.append(
            {
                **document,
                "disposition": (
                    customer_view.get("disposition") if type(customer_view) is dict else "ABSENT"
                ),
                "rejection_reasons": (
                    customer_view.get("rejection_reasons", [])
                    if type(customer_view) is dict
                    else []
                ),
            }
        )
    comparator, oracle_ref = _historical_comparator_axis(
        trials=trials, compiled_specs=compiled_specs
    )
    return {
        "clusters": clusters,
        "equations": equations,
        "historical_comparator": comparator,
        "mappings": mappings,
        "optional_customer_views": optional_customer_views,
    }, oracle_ref


def build_customer_deposit_experimental_audit_v1(
    *,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    selected_page_json_version_ids: Sequence[str],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
    source_repair_authentication: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build transparent semantic axes after the exact SQLite candidate replay."""

    axes, oracle_ref = _audit_axes(trials=trials, compiled_specs=compiled_specs)
    axes["source_repairs"] = canonical_clone_v1(list(source_repair_authentication))
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
    optional_counts = dict(
        sorted(Counter(item["disposition"] for item in axes["optional_customer_views"]).items())
    )
    comparator_counts = Counter(item["disposition"] for item in axes["historical_comparator"])
    audit_metrics = {
        "equation_count": axis_counts["equations"],
        "historical_direct_binding_count": comparator_counts["EXACT_SAME_SCHEMA_BINDING"],
        "historical_schema_id_migration_count": comparator_counts[
            "EXACT_DECLARED_SCHEMA_ID_MIGRATION"
        ],
        "historical_schema_role_rename_count": comparator_counts[
            "EXACT_DECLARED_SCHEMA_ROLE_RENAME"
        ],
        "historical_value_match_count": sum(
            item["disposition"] != "MISMATCH" for item in axes["historical_comparator"]
        ),
        "optional_customer_view_dispositions": optional_counts,
        "source_repair_count": axis_counts["source_repairs"],
    }
    sweep_payload = canonical_json_bytes_v1(sweep)
    material = {
        "axes": axes,
        "axis_counts": axis_counts,
        "axis_sha256": axis_sha256,
        "audit_metrics": audit_metrics,
        "claim_boundary": (
            "AUTHENTICATED_SELECTED_GEMINI_JSON_SQLITE_REPLAY_AND_HISTORICAL_ROLE_VALUE_"
            "COMPARATOR_PLUS_REGISTERED_FULL_PAGE_PDF_DASH_RECEIPTS_ONLY_NO_PROVIDER_"
            "NO_UNREGISTERED_GEOMETRY_NO_CANONICAL_EXPORT_AUTHORITY"
        ),
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_oracle_ref": oracle_ref,
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
        "audit_id": "gjfcdeav1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_customer_deposit_experimental_audit_content_v1(value: Any) -> dict[str, Any]:
    fields = {
        "audit_id",
        "axes",
        "axis_counts",
        "axis_sha256",
        "audit_metrics",
        "claim_boundary",
        "format_version",
        "historical_oracle_ref",
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
        "optional_customer_views",
        "source_repairs",
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
        raise _error("customer-deposit experimental audit shape drifted")
    counts = {name: len(axis) for name, axis in value["axes"].items()}
    hashes = {name: canonical_json_sha256_v1(axis) for name, axis in value["axes"].items()}
    if value.get("axis_counts") != counts or value.get("axis_sha256") != hashes:
        raise _error("customer-deposit experimental audit axis seal drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    if value.get("audit_id") != "gjfcdeav1:audit:" + canonical_json_sha256_v1(material):
        raise _error("customer-deposit experimental audit identity drifted")
    return json.loads(canonical_json_bytes_v1(value))


def validate_customer_deposit_experimental_audit_replay_v1(
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
    source_repair_spec: Mapping[str, Any] | None = None,
    source_repair_authentication: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    checked_sweep = validate_gemini_json_flat_family_sweep_v1(sweep)
    embedded = compile_gemini_json_flat_family_specs_v1(
        checked_sweep["specs"]["topology"]["value"],
        checked_sweep["specs"]["evaluation"]["value"],
        checked_sweep["specs"]["schema_binding"]["value"],
    )
    if source_repair_spec is not None:
        embedded = bind_gemini_json_customer_deposit_source_repairs_v1(
            embedded, source_repair_spec
        )
    if not same_typed_json_v1(embedded, compiled_specs):
        raise _error("customer-deposit caller and embedded compiled specs differ")
    if not same_typed_json_v1(checked_sweep["trials"], trials) or not same_typed_json_v1(
        checked_sweep["indexed_query_evidence"], indexed_query_evidence
    ):
        raise _error("customer-deposit audit sweep/query/trial axis drifted")
    validate_selected_customer_deposit_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=embedded,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
    )
    expected = build_customer_deposit_experimental_audit_v1(
        sweep=checked_sweep,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
        compiled_specs=embedded,
        spec_refs=spec_refs,
        source_repair_authentication=source_repair_authentication,
    )
    validate_customer_deposit_experimental_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("customer-deposit experimental audit does not replay exactly")
    return expected


def _assert_release_pins(
    *,
    index: Mapping[str, Any],
    selected_ids: Sequence[str],
    sweep: Mapping[str, Any],
    indexed: Mapping[str, Any],
    audit: Mapping[str, Any],
    run_kind: str,
) -> None:
    if index.get("corpus_manifest_index_id") != PINNED_CORPUS_MANIFEST_INDEX_ID:
        if run_kind == "EXPERIMENTAL":
            return
        raise _error("official customer-deposit run requires the frozen release corpus")
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
    expected_axis_counts = {
        "clusters": 140,
        "historical_comparator": 159,
        "mappings": 2189,
        "source_repairs": 6,
    }
    if any(
        actual["axis_counts"].get(name) != count for name, count in expected_axis_counts.items()
    ):
        mismatches.append("axis_counts")
    if mismatches:
        raise _error(
            "customer-deposit frozen corpus release pin drifted: "
            + ",".join(mismatches)
            + "; actual="
            + json.dumps(actual, ensure_ascii=False, sort_keys=True)
        )


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical_json_bytes_v1(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error("customer-deposit output exists with different bytes")
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
        raise _error("customer-deposit selected page/evidence order drifted")
    result: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        connection.execute(
            "CREATE TEMP TABLE selected_customer_deposit_runner_page("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_customer_deposit_runner_page VALUES (?,?)",
            enumerate(selected_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT selected.page_json_version_id, version.canonical_json_bytes
            FROM selected_customer_deposit_runner_page AS selected
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
                raise _error("customer-deposit selected canonical page JSON is invalid") from exc
            if type(page_json) is not dict:
                raise _error("customer-deposit selected canonical page is not one object")
            axis = axis_by_version[page_json_version_id]
            result[axis["document_ordinal"]][page_json_version_id] = page_json
    finally:
        connection.close()
    if loaded_ids != list(selected_ids):
        raise _error("customer-deposit selected canonical page frontier is incomplete")
    return result


def replay_customer_deposit_trials_from_source_v1(
    *,
    source_page_database: Path,
    selected_page_json_version_ids: tuple[str, ...],
    compiled_specs: dict[str, Any],
    indexed_query_evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    """Re-query, overlay, evaluate, and replay the complete Family-15 axis."""

    source_repairs = _json(SOURCE_REPAIR_SPEC_PATH)
    family_compiled = bind_gemini_json_customer_deposit_source_repairs_v1(
        compiled_specs, source_repairs
    )
    indexed = query_selected_customer_deposit_family_regions_v1(
        source_page_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=family_compiled,
    )
    if not same_typed_json_v1(indexed, indexed_query_evidence):
        raise _error("customer-deposit source replay rebuilt different query evidence")
    page_json_by_document = _load_selected_pages_by_document(
        source_page_database,
        selected_ids=selected_page_json_version_ids,
        selected_page_axis=indexed["selected_page_axis"],
    )
    candidates_by_ordinal = {}
    for cluster in indexed["accepted_clusters"]:
        ordinal = cluster["document_ordinal"]
        regions = cluster["component_regions"]
        candidates_by_ordinal[ordinal] = (
            evaluate_gemini_json_customer_deposit_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[ordinal],
                compiled_specs=family_compiled,
                query_receipt=(
                    build_gemini_json_customer_deposit_region_query_receipt_v1(regions)
                ),
            )
        )
    trials = _trials(indexed=indexed, candidates_by_ordinal=candidates_by_ordinal)
    validate_selected_customer_deposit_family_candidate_replays_v1(
        source_page_database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=family_compiled,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    return trials


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
    source_repair_spec: dict[str, Any],
    source_repair_authentication: list[dict[str, Any]],
) -> dict[str, Any]:
    database = database_guard.path
    indexed = query_selected_customer_deposit_family_regions_v1(
        database, selected_page_json_version_ids=selected_ids, compiled_specs=compiled
    )
    validate_selected_customer_deposit_family_query_evidence_v1(
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
            evaluate_gemini_json_customer_deposit_family_cluster_v1(
                regions=regions,
                page_json_by_version=page_json_by_document[cluster["document_ordinal"]],
                compiled_specs=compiled,
                query_receipt=build_gemini_json_customer_deposit_region_query_receipt_v1(regions),
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
    validate_source_observation_mapping_contract_v1(sweep)
    validate_selected_customer_deposit_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    audit = build_customer_deposit_experimental_audit_v1(
        sweep=sweep,
        sweep_output=args.output,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
        source_repair_authentication=source_repair_authentication,
    )
    validate_customer_deposit_experimental_audit_replay_v1(
        audit,
        database=database,
        sweep=sweep,
        sweep_output=args.output,
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
        source_repair_spec=source_repair_spec,
        source_repair_authentication=source_repair_authentication,
    )
    _assert_release_pins(
        index=index,
        selected_ids=selected_ids,
        sweep=sweep,
        indexed=indexed,
        audit=audit,
        run_kind=args.run_kind,
    )
    database_guard.validate()
    audit_output = args.output.with_suffix(".audit.json")
    _write_once(args.output, sweep)
    _write_once(audit_output, audit)
    implementation_paths = (
        ROOT / "scripts/experiments/run_gemini_json_customer_deposit_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_customer_deposit_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_first_page_render_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_lane_math_v1.py",
        ROOT / "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
        SOURCE_REPAIR_SPEC_PATH,
    )
    implementation_refs = [_file_ref(path, root=ROOT) for path in implementation_paths]
    runner_ref = _file_ref(
        ROOT / "scripts/experiments/run_gemini_json_customer_deposit_accounting_family_v1.py",
        root=ROOT,
    )
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=_file_ref(args.corpus_index),
        implementation_refs=implementation_refs,
        run_kind=args.run_kind,
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
        source_replay_adapter=replay_customer_deposit_trials_from_source_v1,
        source_replay_adapter_ref=runner_ref,
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored customer-deposit sweep differs from authenticated evaluation")
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
    if args.source_repair_spec.resolve() != SOURCE_REPAIR_SPEC_PATH.resolve():
        raise _error("customer-deposit runner requires its registered source-repair path")
    source_repair_spec = _json(args.source_repair_spec)
    compiled = bind_gemini_json_customer_deposit_source_repairs_v1(
        compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema),
        source_repair_spec,
    )
    spec_refs = {
        "evaluation": _file_ref(args.evaluation_spec, root=ROOT),
        "schema_binding": _file_ref(args.schema_binding_spec, root=ROOT),
        "source_repair": _file_ref(args.source_repair_spec, root=ROOT),
        "topology": _file_ref(args.topology_spec, root=ROOT),
    }
    source_repair_authentication = _authenticate_source_repairs_v1(
        repairs=compiled["customer_deposit_source_repairs"],
        source_pdf_root=args.source_pdf_root,
    )
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
            source_repair_spec=source_repair_spec,
            source_repair_authentication=source_repair_authentication,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--source-repair-spec", type=Path, required=True)
    parser.add_argument("--source-pdf-root", type=Path, required=True)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--run-kind", choices=("EXPERIMENTAL", "OFFICIAL"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
