"""Authenticated, reference-blind archive for the family-first OCR cache.

The detector cache is deliberately created before the semantic reader exists.
This module therefore validates the historical detector plan at its pinned Git
commit while permitting a clean descendant HEAD *only* when every detector
trust-closure file is byte-identical at the pinned commit, current HEAD, and
working tree.  It never treats an arbitrary descendant source tree as detector
authority.

Hundreds of thousands of individual crop paths are unsuitable as a formal
reader interface.  A sealer writes them once, in exact batch order, to one
length-framed archive.  A reader session copies that archive to a Linux memfd,
checks its content identity, applies write/grow/shrink seals, and then exposes
only ordered opaque sample IDs, crop digests and immutable bytes.  Bank, filing,
page, period, scope, source text and schema metadata stay outside the reader.
"""

from __future__ import annotations

import ctypes
import errno
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import tempfile
import weakref
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from bctc_ai.evaluation import family_first_semantic_label_plan_v1 as plan_v1
from bctc_ai.evaluation.family_first_filing_inventory_v1 import (
    read_family_first_filing_inventory_v1,
)
from bctc_ai.evaluation.family_first_semantic_label_freeze_v1 import (
    validate_family_first_semantic_label_page_freeze_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "AuthenticatedFamilyFirstSemanticLabelArchiveV1",
    "AuthenticatedFamilyFirstSemanticLabelReaderSessionV1",
    "FamilyFirstSemanticLabelArchiveV1Error",
    "authenticate_family_first_semantic_label_archive_v1",
    "assert_authenticated_family_first_semantic_label_archive_project_root_v1",
    "open_authenticated_family_first_semantic_label_reader_session_v1",
    "open_authenticated_family_first_semantic_label_reader_snapshot_v1",
    "project_authenticated_family_first_semantic_label_archive_v1",
    "read_authenticated_family_first_semantic_label_chunk_v1",
    "read_authenticated_family_first_semantic_label_source_join_v1",
    "seal_family_first_semantic_label_archive_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_SEMANTIC_LABEL_ARCHIVE_V1"
MANIFEST_PATH = Path(
    "output/calibration/family-first-semantic-label-cache-v1/"
    "sealed-semantic-reader-v1/archive-manifest.json"
)
ARCHIVE_PATH = Path(
    "output/calibration/family-first-semantic-label-cache-v1/"
    "sealed-semantic-reader-v1/crops.ffslcpack"
)
PLAN_PATH = Path("output/calibration/family-first-semantic-label-cache-v1/plan.json")
BATCH_PATH = Path(
    "output/calibration/family-first-semantic-label-cache-v1/semantic-reader-batch.json"
)
PRIVATE_INDEX_PATH = Path(
    "output/calibration/family-first-semantic-label-cache-v1/private-source-index.json"
)
_MAGIC = b"FFSLCPACKV1\n"
_FRAME = struct.Struct(">Q")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_RENAME_NOREPLACE = 1
_MFD_CLOEXEC = 0x0001
_MFD_ALLOW_SEALING = 0x0002
_F_ADD_SEALS = 1033
_F_GET_SEALS = 1034
_F_SEAL_SEAL = 0x0001
_F_SEAL_SHRINK = 0x0002
_F_SEAL_GROW = 0x0004
_F_SEAL_WRITE = 0x0008
_BATCH_FORMAT = "FAMILY_FIRST_SEMANTIC_LABEL_READER_BATCH_V1"
_INDEX_FORMAT = "FAMILY_FIRST_SEMANTIC_LABEL_PRIVATE_SOURCE_INDEX_V1"
_BATCH_AUTHORITY = {
    "bank_page_period_path_available_to_reader": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "reference_text_available_to_reader": False,
    "semantic_reader_input_only": True,
}
_INDEX_AUTHORITY = {"private_provenance_only": True, "reader_access": False}
_PAGE_FORMAT = "FAMILY_FIRST_SEMANTIC_LABEL_CACHE_PAGE_ARTIFACT_V1"
_DOCUMENT_FORMAT = "FAMILY_FIRST_SEMANTIC_LABEL_CACHE_DOCUMENT_ARTIFACT_V1"
_PAGE_AUTHORITY = {
    "all_detected_lines_retained": True,
    "detector_recognition_text_accessed": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "semantic_authority": False,
}
_DOCUMENT_AUTHORITY = {
    "all_pages_retained": True,
    "all_detected_lines_retained": True,
    "bank_period_scope_used_for_detection_or_line_selection": False,
    "mapping_authority": False,
    "numeric_authority": False,
    "semantic_authority": False,
}
_AUTHORITY = {
    "archive_bytes_immutable_only_inside_kernel_sealed_reader_session": True,
    "bank_file_page_period_scope_available_to_reader": False,
    "detector_cache_historical_commit_and_exact_trust_closure_authenticated": True,
    "mapping_authority": False,
    "numeric_authority": False,
    "reference_text_available_to_reader": False,
    "semantic_proposal_only": True,
}
_CLAIM_BOUNDARY = (
    "CLEAN_DESCENDANT_EXACT_HISTORICAL_DETECTOR_TRUST_CLOSURE_AND_ORDERED_"
    "CONTENT_ADDRESSED_CROP_ARCHIVE_TO_KERNEL_SEALED_REFERENCE_BLIND_READER_"
    "SESSION_ONLY_NO_TEXT_NUMERIC_PERIOD_UNIT_STRUCTURE_SCHEMA_MAPPING_OR_EXPORT_AUTHORITY"
)
_MANIFEST_FIELDS = {
    "archive_id",
    "archive_ref",
    "authority",
    "batch_id",
    "batch_ref",
    "claim_boundary",
    "format_version",
    "plan_id",
    "private_index_ref",
    "sample_count",
}


class FamilyFirstSemanticLabelArchiveV1Error(RuntimeError):
    """The plan, Git ledger, cache, archive or opaque reader session drifted."""


def _error(message: str) -> FamilyFirstSemanticLabelArchiveV1Error:
    return FamilyFirstSemanticLabelArchiveV1Error(message)


def _git(root: Path, *arguments: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", os.fspath(root), *arguments],
            check=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise _error("family-first archive Git trust query failed") from exc


def _root(value: Any) -> Path:
    if not isinstance(value, Path):
        raise _error("project root must be one pathlib Path")
    root = value.resolve()
    try:
        top = Path(
            _git(root, "rev-parse", "--show-toplevel").decode("utf-8", errors="strict").strip()
        ).resolve()
    except UnicodeDecodeError as exc:
        raise _error("Git toplevel is not strict UTF-8") from exc
    if root != top:
        raise _error("project root must be the exact Git toplevel")
    return root


def _relative(value: Any, label: str) -> PurePosixPath:
    if type(value) is not str or not value:
        raise _error(f"{label} path must be one non-empty exact string")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise _error(f"{label} path is not one canonical project-relative path")
    return path


def _read_exact_fd(descriptor: int, size: int, label: str) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = os.read(descriptor, min(1024 * 1024, remaining))
        if not chunk:
            raise _error(f"{label} ended before its stable size")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        raise _error(f"{label} grew while being read")
    return b"".join(chunks)


def _root_bytes(root: Path, relative: str | Path, label: str) -> bytes:
    canonical = _relative(PurePosixPath(relative).as_posix(), label)
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in canonical.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        leaf = os.open(canonical.parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=descriptor)
        try:
            before = os.fstat(leaf)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise _error(f"{label} must be one single-link regular file")
            payload = _read_exact_fd(leaf, before.st_size, label)
            after = os.fstat(leaf)
            if (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
            ) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
                raise _error(f"{label} changed while being read")
            return payload
        finally:
            os.close(leaf)
    except OSError as exc:
        raise _error(f"cannot read stable nofollow {label}") from exc
    finally:
        os.close(descriptor)


def _canonical_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict JSON") from exc
    if type(value) is not dict or payload != canonical_json_bytes_v1(value):
        raise _error(f"{label} is not one canonical JSON object")
    return value


def _historical_cache_object(payload: bytes, label: str) -> dict[str, Any]:
    """Decode the already-sealed V1 cache's historical double-LF serialization."""

    try:
        value = json.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"{label} is not strict historical cache JSON") from exc
    if type(value) is not dict or payload != canonical_json_bytes_v1(value) + b"\n":
        raise _error(f"{label} differs from the sealed historical cache serialization")
    return value


def _content_ref(path: str | Path, payload: bytes) -> dict[str, Any]:
    return {
        "path": PurePosixPath(path).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"path", "sha256", "size_bytes"}
        or type(value["path"]) is not str
        or type(value["sha256"]) is not str
        or _SHA256.fullmatch(value["sha256"]) is None
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] <= 0
    ):
        raise _error(f"{label} content reference drifted")
    _relative(value["path"], label)
    return value


def _matches_ref(payload: bytes, reference: Any, label: str) -> None:
    expected = _ref(reference, label)
    if (
        len(payload) != expected["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != expected["sha256"]
    ):
        raise _error(f"{label} bytes differ from their content reference")


def _clean_head(root: Path) -> str:
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise _error("family-first archive requires one clean Git worktree")
    head = _git(root, "rev-parse", "HEAD").decode("ascii", errors="strict").strip()
    if _COMMIT.fullmatch(head) is None:
        raise _error("current Git HEAD is not one exact commit")
    return head


def _validate_descendant_plan(root: Path, payload: bytes, *, model_cache: Path) -> dict[str, Any]:
    plan = plan_v1._validate_plan(_historical_cache_object(payload, "family-first detector plan"))
    binding = plan["git_binding"]
    if (
        type(binding) is not dict
        or set(binding) != {"commit", "implementation_refs", "source_tree_oid", "worktree_clean"}
        or type(binding["commit"]) is not str
        or _COMMIT.fullmatch(binding["commit"]) is None
        or type(binding["worktree_clean"]) is not bool
        or binding["worktree_clean"] is not True
        or type(binding["implementation_refs"]) is not list
    ):
        raise _error("historical detector Git binding drifted")
    pinned = binding["commit"]
    head = _clean_head(root)
    try:
        subprocess.run(
            ["git", "-C", os.fspath(root), "merge-base", "--is-ancestor", pinned, head],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise _error("historical detector commit is not an ancestor of clean HEAD") from exc
    expected_paths = [
        *(path.as_posix() for path in plan_v1._IMPLEMENTATION_PATHS),
        plan_v1.RUNTIME_CONFIG_PATH.as_posix(),
        plan_v1.INVENTORY_PATH.as_posix(),
    ]
    observed_paths = [
        item.get("path") if type(item) is dict else None for item in binding["implementation_refs"]
    ]
    if observed_paths != expected_paths:
        raise _error("historical detector trust-closure path denominator drifted")
    for reference in binding["implementation_refs"]:
        expected = _ref(reference, "historical detector trust file")
        committed = _git(root, "show", f"{pinned}:{expected['path']}")
        current = _git(root, "show", f"{head}:{expected['path']}")
        disk = _root_bytes(root, expected["path"], "historical detector trust file")
        _matches_ref(committed, expected, "historical detector commit trust file")
        if committed != current or committed != disk:
            raise _error("historical detector trust file changed on the descendant chain")
    pinned_tree = (
        _git(root, "rev-parse", f"{pinned}:src/bctc_ai").decode("ascii", errors="strict").strip()
    )
    if binding["source_tree_oid"] != pinned_tree:
        raise _error("historical detector source-tree identity drifted")
    by_path = {item["path"]: item for item in binding["implementation_refs"]}
    if not same_typed_json_v1(
        plan["input_refs"]["runtime_config_ref"], by_path[plan_v1.RUNTIME_CONFIG_PATH.as_posix()]
    ) or not same_typed_json_v1(
        plan["input_refs"]["inventory_ref"], by_path[plan_v1.INVENTORY_PATH.as_posix()]
    ):
        raise _error("plan input refs do not cross-link its historical trust closure")
    runtime, _runtime_bytes = plan_v1._runtime(root)
    detector = plan_v1._model_projection(model_cache, runtime["detector"])
    if not same_typed_json_v1(plan["detector"], detector):
        raise _error("live detector executable closure differs from the historical plan")
    inventory = read_family_first_filing_inventory_v1(root)
    expected_documents: list[dict[str, Any]] = []
    total_pages = 0
    for ordinal, filing in enumerate(inventory["filings"], 1):
        source_ref = filing["content_ref"]
        source = _root_bytes(root, source_ref["path"], "planned source PDF")
        _matches_ref(source, source_ref, "planned source PDF")
        count = plan_v1._page_count(source, source_ref["path"])
        total_pages += count
        expected_documents.append(
            {
                "document_ordinal": ordinal,
                "page_count": count,
                "private_provenance": {
                    "bank": filing["bank_provenance"],
                    "period": filing["period"],
                    "scope": filing["scope"],
                    "year": filing["year"],
                },
                "source_pdf_ref": canonical_clone_v1(source_ref),
            }
        )
    if (
        not same_typed_json_v1(plan["documents"], expected_documents)
        or not same_typed_json_v1(plan["missing_filings"], inventory["missing_filings"])
        or not same_typed_json_v1(
            plan["metrics"],
            {
                "document_count": len(expected_documents),
                "explicit_missing_filing_count": len(inventory["missing_filings"]),
                "page_count": total_pages,
            },
        )
    ):
        raise _error("historical detector filing/page denominator does not replay")
    if _clean_head(root) != head:
        raise _error("Git HEAD/worktree changed during historical detector validation")
    return canonical_clone_v1(plan)


def _validate_batch(value: Any, plan: dict[str, Any]) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value)
        != {"authority", "batch_id", "format_version", "plan_id", "sample_count", "samples"}
        or value["format_version"] != _BATCH_FORMAT
        or value["plan_id"] != plan["plan_id"]
        or not same_typed_json_v1(value["authority"], _BATCH_AUTHORITY)
        or type(value["sample_count"]) is not int
        or value["sample_count"] <= 0
        or type(value["samples"]) is not list
        or len(value["samples"]) != value["sample_count"]
    ):
        raise _error("semantic reader batch contract drifted")
    for ordinal, sample in enumerate(value["samples"], 1):
        if (
            type(sample) is not dict
            or set(sample) != {"crop_ref", "sample_id"}
            or sample["sample_id"] != f"sample-{ordinal:09d}"
        ):
            raise _error("semantic reader batch sample identity/order drifted")
        _ref(sample["crop_ref"], "semantic reader crop")
    material = canonical_clone_v1(value)
    batch_id = material.pop("batch_id")
    if batch_id != "ffslcv1:batch:" + canonical_json_sha256_v1(material):
        raise _error("semantic reader batch hash identity drifted")
    return canonical_clone_v1(value)


def _validate_private_index(
    value: Any, batch: dict[str, Any], plan: dict[str, Any]
) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value)
        != {
            "authority",
            "batch_id",
            "documents",
            "format_version",
            "index_id",
            "plan_id",
            "sample_count",
            "samples",
        }
        or value["format_version"] != _INDEX_FORMAT
        or value["plan_id"] != plan["plan_id"]
        or value["batch_id"] != batch["batch_id"]
        or value["sample_count"] != batch["sample_count"]
        or type(value["sample_count"]) is not int
        or not same_typed_json_v1(value["authority"], _INDEX_AUTHORITY)
        or not same_typed_json_v1(value["documents"], plan["documents"])
        or type(value["samples"]) is not list
        or len(value["samples"]) != value["sample_count"]
    ):
        raise _error("private semantic source index contract drifted")
    prior_locator = (0, 0, -1)
    for ordinal, (sample, batch_sample) in enumerate(
        zip(value["samples"], batch["samples"], strict=True), 1
    ):
        if (
            type(sample) is not dict
            or set(sample)
            != {
                "document_ordinal",
                "line_ordinal",
                "physical_page",
                "sample_id",
                "source_bbox_raw_pixels",
            }
            or sample["sample_id"] != f"sample-{ordinal:09d}"
            or any(
                type(sample[key]) is not int
                for key in ("document_ordinal", "line_ordinal", "physical_page")
            )
            or type(sample["source_bbox_raw_pixels"]) is not list
            or len(sample["source_bbox_raw_pixels"]) != 4
            or any(type(item) is not int for item in sample["source_bbox_raw_pixels"])
        ):
            raise _error("private semantic source sample contract drifted")
        bbox = sample["source_bbox_raw_pixels"]
        if bbox[0] < 0 or bbox[1] < 0 or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            raise _error("private semantic source bbox is not one positive-area pixel box")
        locator = (sample["document_ordinal"], sample["physical_page"], sample["line_ordinal"])
        if locator <= prior_locator:
            raise _error("private semantic source sample order drifted")
        expected_crop_path = (
            "output/calibration/family-first-semantic-label-cache-v1/documents/"
            f"document-{sample['document_ordinal']:04d}/page-{sample['physical_page']:04d}/"
            f"crops/line-{sample['line_ordinal']:04d}.png"
        )
        if (
            batch_sample["sample_id"] != sample["sample_id"]
            or batch_sample["crop_ref"]["path"] != expected_crop_path
        ):
            raise _error("public crop reference does not cross-link the private source axis")
        prior_locator = locator
    material = canonical_clone_v1(value)
    index_id = material.pop("index_id")
    if index_id != "ffslcv1:index:" + canonical_json_sha256_v1(material):
        raise _error("private semantic source index hash identity drifted")
    return canonical_clone_v1(value)


def _page_artifact(value: Any) -> dict[str, Any]:
    fields = {
        "artifact_id",
        "authority",
        "detector_payload",
        "document_ordinal",
        "format_version",
        "page_freeze",
        "physical_page",
        "plan_id",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != _PAGE_FORMAT
        or not same_typed_json_v1(value["authority"], _PAGE_AUTHORITY)
        or type(value["document_ordinal"]) is not int
        or value["document_ordinal"] <= 0
        or type(value["physical_page"]) is not int
        or value["physical_page"] <= 0
    ):
        raise _error("semantic-label page artifact contract drifted")
    material = canonical_clone_v1(value)
    artifact_id = material.pop("artifact_id")
    if artifact_id != "ffslcv1:page:" + canonical_json_sha256_v1(material):
        raise _error("semantic-label page artifact hash identity drifted")
    return canonical_clone_v1(value)


def _document_artifact(value: Any) -> dict[str, Any]:
    fields = {
        "artifact_id",
        "authority",
        "document_ordinal",
        "format_version",
        "metrics",
        "page_artifact_refs",
        "plan_id",
        "source_pdf_ref",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value["format_version"] != _DOCUMENT_FORMAT
        or not same_typed_json_v1(value["authority"], _DOCUMENT_AUTHORITY)
        or type(value["document_ordinal"]) is not int
        or value["document_ordinal"] <= 0
        or type(value["page_artifact_refs"]) is not list
    ):
        raise _error("semantic-label document artifact contract drifted")
    material = canonical_clone_v1(value)
    artifact_id = material.pop("artifact_id")
    if artifact_id != "ffslcv1:document:" + canonical_json_sha256_v1(material):
        raise _error("semantic-label document artifact hash identity drifted")
    return canonical_clone_v1(value)


def _entry_names(path: Path, label: str) -> dict[str, bool]:
    try:
        with os.scandir(path) as entries:
            return {entry.name: entry.is_dir(follow_symlinks=False) for entry in entries}
    except OSError as exc:
        raise _error(f"cannot enumerate nofollow {label}") from exc


def _validate_cache_replay(
    root: Path,
    plan: dict[str, Any],
    batch: dict[str, Any],
    private_index: dict[str, Any],
) -> None:
    """Replay every render/crop and exact public/private sample join once."""

    try:
        import fitz
    except ImportError as exc:
        raise _error("pinned PyMuPDF is required to replay the detector cache") from exc

    sample_cursor = 0
    document_parent_relative = Path(
        "output/calibration/family-first-semantic-label-cache-v1/documents"
    )
    document_parent = root / document_parent_relative
    expected_document_names = {
        f"document-{item['document_ordinal']:04d}" for item in plan["documents"]
    }
    observed_document_entries = _entry_names(document_parent, "semantic-label document root")
    if set(observed_document_entries) != expected_document_names or not all(
        observed_document_entries.values()
    ):
        raise _error("semantic-label document directory denominator drifted")

    for document in plan["documents"]:
        ordinal = document["document_ordinal"]
        document_relative = document_parent_relative / f"document-{ordinal:04d}"
        document_root = root / document_relative
        expected_page_names = {f"page-{page:04d}" for page in range(1, document["page_count"] + 1)}
        observed_entries = _entry_names(document_root, "semantic-label document")
        if set(observed_entries) != expected_page_names | {"document.json"}:
            raise _error("semantic-label document page/file denominator drifted")
        if observed_entries["document.json"] or not all(
            observed_entries[name] for name in expected_page_names
        ):
            raise _error("semantic-label document entry types drifted")
        persisted_document_payload = _root_bytes(
            root, document_relative / "document.json", "semantic-label document artifact"
        )
        persisted_document = _document_artifact(
            _historical_cache_object(persisted_document_payload, "semantic-label document artifact")
        )
        source = _root_bytes(root, document["source_pdf_ref"]["path"], "planned source PDF")
        _matches_ref(source, document["source_pdf_ref"], "planned source PDF")
        page_refs: list[dict[str, Any]] = []
        total_lines = 0
        try:
            pdf = fitz.open(stream=source, filetype="pdf")
        except (RuntimeError, ValueError) as exc:
            raise _error("planned source PDF cannot be opened for cache replay") from exc
        try:
            if pdf.page_count != document["page_count"]:
                raise _error("planned source PDF page denominator changed during cache replay")
            for page_index in range(pdf.page_count):
                physical_page = page_index + 1
                page_relative = document_relative / f"page-{physical_page:04d}"
                page_root = root / page_relative
                if _entry_names(page_root, "semantic-label page") != {
                    "crops": True,
                    "page.json": False,
                }:
                    raise _error("semantic-label page entry denominator drifted")
                page_payload = _root_bytes(
                    root, page_relative / "page.json", "semantic-label page artifact"
                )
                page = _page_artifact(
                    _historical_cache_object(page_payload, "semantic-label page artifact")
                )
                if (
                    page["plan_id"] != plan["plan_id"]
                    or page["document_ordinal"] != ordinal
                    or page["physical_page"] != physical_page
                    or type(page["page_freeze"]) is not dict
                    or type(page["detector_payload"]) is not dict
                ):
                    raise _error("semantic-label page does not belong to the replayed plan")
                crops = page["page_freeze"].get("crops")
                if type(crops) is not list:
                    raise _error("semantic-label page crop axis drifted")
                expected_crop_names = {f"line-{line:04d}.png" for line in range(len(crops))}
                crop_root = page_root / "crops"
                crop_entries = _entry_names(crop_root, "semantic-label crop directory")
                if set(crop_entries) != expected_crop_names or any(crop_entries.values()):
                    raise _error("semantic-label page crop denominator/type drifted")
                crop_payloads: list[bytes] = []
                for line_ordinal, crop_record in enumerate(crops):
                    if (
                        type(crop_record) is not dict
                        or set(crop_record)
                        != {
                            "crop_ref",
                            "line_ordinal",
                            "padded_source_bbox_raw_pixels",
                            "source_bbox_raw_pixels",
                        }
                        or crop_record["line_ordinal"] != line_ordinal
                        or type(crop_record["padded_source_bbox_raw_pixels"]) is not list
                        or len(crop_record["padded_source_bbox_raw_pixels"]) != 4
                        or any(
                            type(item) is not int
                            for item in crop_record["padded_source_bbox_raw_pixels"]
                        )
                    ):
                        raise _error("semantic-label crop record shape/order drifted")
                    crop_payload = _root_bytes(
                        root,
                        page_relative / "crops" / f"line-{line_ordinal:04d}.png",
                        "semantic-label crop",
                    )
                    crop_payloads.append(crop_payload)
                    if sample_cursor >= batch["sample_count"]:
                        raise _error("detector cache has more crops than the reader denominator")
                    public_sample = batch["samples"][sample_cursor]
                    private_sample = private_index["samples"][sample_cursor]
                    if (
                        not same_typed_json_v1(public_sample["crop_ref"], crop_record["crop_ref"])
                        or private_sample["document_ordinal"] != ordinal
                        or private_sample["physical_page"] != physical_page
                        or private_sample["line_ordinal"] != line_ordinal
                        or not same_typed_json_v1(
                            private_sample["source_bbox_raw_pixels"],
                            crop_record["source_bbox_raw_pixels"],
                        )
                    ):
                        raise _error("detector crop does not cross-link public/private reader axes")
                    sample_cursor += 1
                pixmap = pdf[page_index].get_pixmap(
                    matrix=fitz.Matrix(
                        plan["render_policy"]["dpi"] / 72,
                        plan["render_policy"]["dpi"] / 72,
                    ),
                    colorspace=fitz.csRGB,
                    alpha=False,
                )
                render = pixmap.tobytes("png")
                validate_family_first_semantic_label_page_freeze_replay_v1(
                    page["page_freeze"],
                    tuple(crop_payloads),
                    render_png_bytes=render,
                    detector_payload=page["detector_payload"],
                    physical_page=physical_page,
                    crop_path_prefix=(page_relative / "crops").as_posix(),
                )
                page_refs.append(_content_ref(page_relative / "page.json", page_payload))
                total_lines += len(crop_payloads)
        finally:
            pdf.close()
        expected_document_material = {
            "authority": canonical_clone_v1(_DOCUMENT_AUTHORITY),
            "document_ordinal": ordinal,
            "format_version": _DOCUMENT_FORMAT,
            "metrics": {
                "crop_count": total_lines,
                "detected_line_count": total_lines,
                "excluded_detected_line_count": 0,
                "page_count": len(page_refs),
            },
            "page_artifact_refs": page_refs,
            "plan_id": plan["plan_id"],
            "source_pdf_ref": document["source_pdf_ref"],
        }
        expected_document = {
            **expected_document_material,
            "artifact_id": "ffslcv1:document:"
            + canonical_json_sha256_v1(expected_document_material),
        }
        if not same_typed_json_v1(persisted_document, expected_document):
            raise _error("semantic-label document artifact does not replay exactly")
    if sample_cursor != batch["sample_count"]:
        raise _error("detector cache has fewer crops than the reader denominator")


def _manifest(value: Any) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != _MANIFEST_FIELDS
        or value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != _CLAIM_BOUNDARY
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["sample_count"]) is not int
        or value["sample_count"] <= 0
    ):
        raise _error("family-first semantic archive manifest fields drifted")
    for field in ("archive_ref", "batch_ref", "private_index_ref"):
        _ref(value[field], f"archive manifest {field}")
    material = canonical_clone_v1(value)
    archive_id = material.pop("archive_id")
    if archive_id != "ffslav1:archive:" + canonical_json_sha256_v1(material):
        raise _error("family-first semantic archive identity drifted")
    return canonical_clone_v1(value)


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        count = os.write(descriptor, view)
        if count <= 0:
            raise _error("archive write made no progress")
        view = view[count:]


def _write_exclusive(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o444)
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rename_noreplace(parent: Path, source_name: str, destination_name: str) -> None:
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise _error("renameat2 is required for no-replace archive publication")
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        if (
            renameat2(
                parent_fd,
                os.fsencode(source_name),
                parent_fd,
                os.fsencode(destination_name),
                _RENAME_NOREPLACE,
            )
            != 0
        ):
            number = ctypes.get_errno()
            if number == errno.EEXIST:
                raise _error("fixed family-first semantic archive appeared during publication")
            raise OSError(number, os.strerror(number), destination_name)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def _build_archive_stage(
    root: Path,
    stage: Path,
    plan: dict[str, Any],
    batch: dict[str, Any],
    batch_payload: bytes,
    index_payload: bytes,
) -> dict[str, Any]:
    archive_path = stage / ARCHIVE_PATH.name
    descriptor = os.open(
        archive_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o444,
    )
    digest = hashlib.sha256()
    size = 0
    try:
        _write_all(descriptor, _MAGIC)
        digest.update(_MAGIC)
        size += len(_MAGIC)
        for sample in batch["samples"]:
            reference = sample["crop_ref"]
            crop = _root_bytes(root, reference["path"], "semantic reader crop")
            _matches_ref(crop, reference, "semantic reader crop")
            frame = _FRAME.pack(len(crop))
            _write_all(descriptor, frame)
            _write_all(descriptor, crop)
            digest.update(frame)
            digest.update(crop)
            size += len(frame) + len(crop)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    material = {
        "archive_ref": {
            "path": ARCHIVE_PATH.as_posix(),
            "sha256": digest.hexdigest(),
            "size_bytes": size,
        },
        "authority": canonical_clone_v1(_AUTHORITY),
        "batch_id": batch["batch_id"],
        "batch_ref": _content_ref(BATCH_PATH, batch_payload),
        "claim_boundary": _CLAIM_BOUNDARY,
        "format_version": FORMAT_VERSION,
        "plan_id": plan["plan_id"],
        "private_index_ref": _content_ref(PRIVATE_INDEX_PATH, index_payload),
        "sample_count": batch["sample_count"],
    }
    manifest = _manifest(
        {**material, "archive_id": "ffslav1:archive:" + canonical_json_sha256_v1(material)}
    )
    _write_exclusive(stage / MANIFEST_PATH.name, canonical_json_bytes_v1(manifest))
    directory_fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return manifest


def seal_family_first_semantic_label_archive_v1(
    project_root: Path, *, model_cache: Path
) -> dict[str, Any]:
    """Seal the already-verified ordered crop batch into one fixed archive."""

    root = _root(project_root)
    plan_payload = _root_bytes(root, PLAN_PATH, "family-first detector plan")
    plan = _validate_descendant_plan(root, plan_payload, model_cache=model_cache)
    captured_head = _clean_head(root)
    batch_payload = _root_bytes(root, BATCH_PATH, "semantic reader batch")
    batch = _validate_batch(_historical_cache_object(batch_payload, "semantic reader batch"), plan)
    index_payload = _root_bytes(root, PRIVATE_INDEX_PATH, "private semantic source index")
    private_index = _validate_private_index(
        _historical_cache_object(index_payload, "private semantic source index"), batch, plan
    )
    _validate_cache_replay(root, plan, batch, private_index)
    destination = root / MANIFEST_PATH.parent
    if destination.exists() or destination.is_symlink():
        raise _error("fixed family-first semantic archive already exists")
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    stage: Path | None = Path(tempfile.mkdtemp(prefix=".sealed-semantic-reader-v1-", dir=parent))
    stage_stat = stage.stat(follow_symlinks=False)
    try:
        assert stage is not None
        manifest = _build_archive_stage(root, stage, plan, batch, batch_payload, index_payload)
        if _clean_head(root) != captured_head:
            raise _error("Git HEAD/worktree changed before semantic archive publication")
        _rename_noreplace(parent, stage.name, destination.name)
        stage = None
        if _clean_head(root) != captured_head:
            raise _error("Git HEAD/worktree changed while publishing semantic archive")
        return manifest
    finally:
        if stage is not None and stage.exists():
            current = stage.stat(follow_symlinks=False)
            if (current.st_dev, current.st_ino) == (stage_stat.st_dev, stage_stat.st_ino):
                shutil.rmtree(stage)


class AuthenticatedFamilyFirstSemanticLabelArchiveV1:
    """Opaque exact archive handle; only this module can mint one."""

    __slots__ = ("__weakref__",)

    def __new__(cls, token: object | None = None) -> AuthenticatedFamilyFirstSemanticLabelArchiveV1:
        if token is not _MINT:
            raise TypeError("family-first semantic archive handles cannot be constructed")
        return super().__new__(cls)

    def __copy__(self) -> None:
        raise TypeError("family-first semantic archive handles cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]) -> None:
        raise TypeError("family-first semantic archive handles cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("family-first semantic archive handles cannot be pickled")


class AuthenticatedFamilyFirstSemanticLabelReaderSessionV1:
    """Opaque cursor over one kernel-sealed immutable archive snapshot."""

    __slots__ = ("__weakref__",)

    def __new__(
        cls, token: object | None = None
    ) -> AuthenticatedFamilyFirstSemanticLabelReaderSessionV1:
        if token is not _MINT:
            raise TypeError("family-first semantic reader sessions cannot be constructed")
        return super().__new__(cls)

    def __copy__(self) -> None:
        raise TypeError("family-first semantic reader sessions cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]) -> None:
        raise TypeError("family-first semantic reader sessions cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("family-first semantic reader sessions cannot be pickled")


@dataclass(frozen=True)
class _ArchiveState:
    root: Path
    model_cache: Path
    plan_payload: bytes
    manifest_payload: bytes
    batch_payload: bytes
    private_index_payload: bytes


@dataclass
class _SessionState:
    descriptor: int
    batch: dict[str, Any]
    cursor: int
    offset: int
    archive: AuthenticatedFamilyFirstSemanticLabelArchiveV1


_MINT = object()
_ARCHIVES: weakref.WeakKeyDictionary[
    AuthenticatedFamilyFirstSemanticLabelArchiveV1, _ArchiveState
] = weakref.WeakKeyDictionary()
_SESSIONS: weakref.WeakKeyDictionary[
    AuthenticatedFamilyFirstSemanticLabelReaderSessionV1, _SessionState
] = weakref.WeakKeyDictionary()


def _archive_payloads(
    capability: Any,
) -> tuple[
    _ArchiveState,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    if type(capability) is not AuthenticatedFamilyFirstSemanticLabelArchiveV1:
        raise _error("one exact live family-first semantic archive handle is required")
    state = _ARCHIVES.get(capability)
    if state is None:
        raise _error("family-first semantic archive handle is not live")
    plan = _validate_descendant_plan(
        state.root,
        state.plan_payload,
        model_cache=state.model_cache,
    )
    manifest = _manifest(_canonical_object(state.manifest_payload, "archive manifest snapshot"))
    live_manifest = _root_bytes(state.root, MANIFEST_PATH, "family-first semantic archive manifest")
    if live_manifest != state.manifest_payload:
        raise _error("family-first semantic archive manifest changed after authentication")
    batch = _validate_batch(
        _historical_cache_object(state.batch_payload, "semantic reader batch snapshot"), plan
    )
    live_plan = _root_bytes(state.root, PLAN_PATH, "family-first detector plan")
    live_batch = _root_bytes(state.root, BATCH_PATH, "semantic reader batch")
    live_index = _root_bytes(state.root, PRIVATE_INDEX_PATH, "private semantic source index")
    if (
        live_plan != state.plan_payload
        or live_batch != state.batch_payload
        or live_index != state.private_index_payload
    ):
        raise _error("family-first semantic plan/batch/index changed after authentication")
    _matches_ref(state.batch_payload, manifest["batch_ref"], "archive batch")
    _matches_ref(
        state.private_index_payload, manifest["private_index_ref"], "archive private index"
    )
    private_index = _validate_private_index(
        _historical_cache_object(
            state.private_index_payload, "private semantic source index snapshot"
        ),
        batch,
        plan,
    )
    if (
        manifest["plan_id"] != plan["plan_id"]
        or manifest["batch_id"] != batch["batch_id"]
        or manifest["sample_count"] != batch["sample_count"]
    ):
        raise _error("family-first semantic archive lineage drifted")
    return state, manifest, batch, plan, private_index


def authenticate_family_first_semantic_label_archive_v1(
    project_root: Path,
    *,
    model_cache: Path,
) -> AuthenticatedFamilyFirstSemanticLabelArchiveV1:
    """Authenticate the fixed archive and retain immutable metadata snapshots."""

    root = _root(project_root)
    plan_payload = _root_bytes(root, PLAN_PATH, "family-first detector plan")
    manifest_payload = _root_bytes(root, MANIFEST_PATH, "family-first semantic archive manifest")
    batch_payload = _root_bytes(root, BATCH_PATH, "semantic reader batch")
    index_payload = _root_bytes(root, PRIVATE_INDEX_PATH, "private semantic source index")
    capability = AuthenticatedFamilyFirstSemanticLabelArchiveV1(_MINT)
    _ARCHIVES[capability] = _ArchiveState(
        root,
        model_cache.resolve(),
        plan_payload,
        manifest_payload,
        batch_payload,
        index_payload,
    )
    _archive_payloads(capability)
    return capability


def project_authenticated_family_first_semantic_label_archive_v1(
    capability: AuthenticatedFamilyFirstSemanticLabelArchiveV1,
) -> dict[str, Any]:
    """Project provenance-free denominator/identity metadata for orchestration."""

    _state, manifest, _batch, _plan, _private_index = _archive_payloads(capability)
    return {
        "archive_id": manifest["archive_id"],
        "authority": canonical_clone_v1(_AUTHORITY),
        "batch_id": manifest["batch_id"],
        "format_version": FORMAT_VERSION,
        "plan_id": manifest["plan_id"],
        "sample_count": manifest["sample_count"],
    }


def assert_authenticated_family_first_semantic_label_archive_project_root_v1(
    project_root: Path,
    capability: AuthenticatedFamilyFirstSemanticLabelArchiveV1,
) -> None:
    """Require a capability minted from this exact resolved Git root."""

    supplied = _root(project_root)
    state, _manifest_value, _batch, _plan, _private_index = _archive_payloads(capability)
    if supplied != state.root:
        raise _error("family-first semantic archive belongs to another project root")


def _copy_archive_to_sealed_memfd(root: Path, reference: dict[str, Any]) -> int:
    source = _root_bytes(root, reference["path"], "family-first semantic crop archive")
    _matches_ref(source, reference, "family-first semantic crop archive")
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        memfd_create = libc.memfd_create
        memfd_create.argtypes = [ctypes.c_char_p, ctypes.c_uint]
        memfd_create.restype = ctypes.c_int
        descriptor = memfd_create(
            b"family-first-semantic-label-archive-v1",
            _MFD_CLOEXEC | _MFD_ALLOW_SEALING,
        )
        if descriptor < 0:
            number = ctypes.get_errno()
            raise OSError(number, os.strerror(number))
    except (AttributeError, OSError) as exc:
        raise _error("Linux memfd sealing is required for the semantic reader") from exc
    try:
        _write_all(descriptor, source)
        os.lseek(descriptor, 0, os.SEEK_SET)
        seals = _F_SEAL_WRITE | _F_SEAL_GROW | _F_SEAL_SHRINK | _F_SEAL_SEAL
        fcntl.fcntl(descriptor, _F_ADD_SEALS, seals)
        if fcntl.fcntl(descriptor, _F_GET_SEALS) != seals:
            raise _error("semantic reader memfd did not retain the complete seal set")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def open_authenticated_family_first_semantic_label_reader_session_v1(
    capability: AuthenticatedFamilyFirstSemanticLabelArchiveV1,
) -> AuthenticatedFamilyFirstSemanticLabelReaderSessionV1:
    """Validate once and open a sequential immutable crop-byte session."""

    state, manifest, batch, _plan, _private_index = _archive_payloads(capability)
    descriptor = _copy_archive_to_sealed_memfd(state.root, manifest["archive_ref"])
    if os.pread(descriptor, len(_MAGIC), 0) != _MAGIC:
        os.close(descriptor)
        raise _error("family-first semantic archive magic drifted")
    session = AuthenticatedFamilyFirstSemanticLabelReaderSessionV1(_MINT)
    _SESSIONS[session] = _SessionState(
        descriptor=descriptor,
        batch=batch,
        cursor=0,
        offset=len(_MAGIC),
        archive=capability,
    )
    weakref.finalize(session, os.close, descriptor)
    return session


def open_authenticated_family_first_semantic_label_reader_snapshot_v1(
    project_root: Path,
    capability: AuthenticatedFamilyFirstSemanticLabelArchiveV1,
) -> tuple[dict[str, Any], AuthenticatedFamilyFirstSemanticLabelReaderSessionV1]:
    """Return one projection plus one immutable session from one live replay."""

    supplied = _root(project_root)
    state, manifest, batch, _plan, _private_index = _archive_payloads(capability)
    if supplied != state.root:
        raise _error("family-first semantic archive belongs to another project root")
    descriptor = _copy_archive_to_sealed_memfd(state.root, manifest["archive_ref"])
    if os.pread(descriptor, len(_MAGIC), 0) != _MAGIC:
        os.close(descriptor)
        raise _error("family-first semantic archive magic drifted")
    session = AuthenticatedFamilyFirstSemanticLabelReaderSessionV1(_MINT)
    _SESSIONS[session] = _SessionState(
        descriptor=descriptor,
        batch=batch,
        cursor=0,
        offset=len(_MAGIC),
        archive=capability,
    )
    weakref.finalize(session, os.close, descriptor)
    projection = {
        "archive_id": manifest["archive_id"],
        "authority": canonical_clone_v1(_AUTHORITY),
        "batch_id": manifest["batch_id"],
        "format_version": FORMAT_VERSION,
        "plan_id": manifest["plan_id"],
        "sample_count": manifest["sample_count"],
    }
    return projection, session


def read_authenticated_family_first_semantic_label_chunk_v1(
    session: AuthenticatedFamilyFirstSemanticLabelReaderSessionV1,
    *,
    maximum_samples: int,
) -> tuple[dict[str, Any], ...]:
    """Read the next exact ordered chunk; an empty tuple means complete."""

    if type(session) is not AuthenticatedFamilyFirstSemanticLabelReaderSessionV1:
        raise _error("one exact live family-first semantic reader session is required")
    state = _SESSIONS.get(session)
    if state is None:
        raise _error("family-first semantic reader session is not live")
    if type(maximum_samples) is not int or not 1 <= maximum_samples <= 4096:
        raise _error("semantic reader chunk denominator must be an integer in [1,4096]")
    stop = min(state.cursor + maximum_samples, state.batch["sample_count"])
    records: list[dict[str, Any]] = []
    while state.cursor < stop:
        raw_length = os.pread(state.descriptor, _FRAME.size, state.offset)
        if len(raw_length) != _FRAME.size:
            raise _error("semantic reader archive ended before a crop frame")
        crop_size = _FRAME.unpack(raw_length)[0]
        sample = state.batch["samples"][state.cursor]
        expected = sample["crop_ref"]
        if crop_size != expected["size_bytes"]:
            raise _error("semantic reader crop frame size drifted")
        crop = os.pread(state.descriptor, crop_size, state.offset + _FRAME.size)
        if len(crop) != crop_size or hashlib.sha256(crop).hexdigest() != expected["sha256"]:
            raise _error("semantic reader crop frame bytes drifted")
        records.append(
            {
                "crop_png_bytes": crop,
                "crop_sha256": expected["sha256"],
                "sample_id": sample["sample_id"],
            }
        )
        state.offset += _FRAME.size + crop_size
        state.cursor += 1
    if state.cursor == state.batch["sample_count"]:
        size = os.fstat(state.descriptor).st_size
        if state.offset != size:
            raise _error("semantic reader archive has trailing unbound bytes")
    return tuple(records)


def read_authenticated_family_first_semantic_label_source_join_v1(
    capability: AuthenticatedFamilyFirstSemanticLabelArchiveV1,
) -> dict[str, Any]:
    """Return the trusted post-reader provenance join; never pass it to the model."""

    _state, manifest, batch, _plan, private_index = _archive_payloads(capability)
    samples = []
    for public, private in zip(batch["samples"], private_index["samples"], strict=True):
        samples.append(
            {
                **canonical_clone_v1(private),
                "crop_ref": canonical_clone_v1(public["crop_ref"]),
            }
        )
    return {
        "archive_id": manifest["archive_id"],
        "authority": {
            "intended_for_post_reader_provenance_join": True,
            "mapping_authority": False,
            "reader_access": False,
            "trusted_post_reader_provenance_join_only": True,
        },
        "batch_id": manifest["batch_id"],
        "documents": canonical_clone_v1(private_index["documents"]),
        "format_version": "FAMILY_FIRST_SEMANTIC_LABEL_SOURCE_JOIN_V1",
        "plan_id": manifest["plan_id"],
        "sample_count": manifest["sample_count"],
        "samples": samples,
    }
