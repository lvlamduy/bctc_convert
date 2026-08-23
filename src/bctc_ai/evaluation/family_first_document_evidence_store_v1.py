"""Authenticated document-root store over the materialized family-first evidence axis.

The legacy semantic and numeric capabilities remain the migration authority.
This store is sealed once after a full audit rebuild, then lets downstream
family code authenticate one tracked manifest plus one immutable SQLite content
reference instead of canonicalizing 667,224 observations for every family.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import weakref
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as render_v1
from bctc_ai.evaluation import family_first_filing_inventory_v1 as inventory_v1
from bctc_ai.evaluation import family_first_ocr_query_cache_v1 as cache_v1
from bctc_ai.evaluation import family_first_ppocrv6_numeric_index_v3 as numeric_v3
from bctc_ai.evaluation import family_first_semantic_index_v1 as semantic_v1
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "MANIFEST_PATH",
    "REGISTRY_PATH",
    "AuthenticatedFamilyFirstDocumentEvidenceStoreV1",
    "FamilyFirstDocumentEvidenceStoreV1Error",
    "authenticate_family_first_document_evidence_store_v1",
    "build_authenticated_family_first_document_evidence_manifest_v1",
    "project_authenticated_family_first_document_evidence_store_v1",
    "read_authenticated_family_first_document_evidence_snapshot_v1",
    "read_authenticated_family_first_document_packet_v1",
    "read_authenticated_family_first_document_page_renders_v1",
    "read_authenticated_family_first_topology_scans_v1",
    "validate_family_first_document_evidence_manifest_shape_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_DOCUMENT_EVIDENCE_STORE_MANIFEST_V1"
MANIFEST_PATH = Path("output/calibration/family-first-document-evidence-store-v1/manifest.json")
REGISTRY_PATH = Path("data/registered/family_first_document_evidence_store_v1.json")
CLAIM_BOUNDARY = (
    "TRACKED_FULL_AUDIT_MATERIALIZED_DOCUMENT_PACKET_ROOTS_OVER_EXACT_SEMANTIC_"
    "NUMERIC_GEOMETRY_CROP_PAGE_RENDER_FILING_PERIOD_SCOPE_ASSURANCE_EVIDENCE_"
    "NO_FAMILY_MAPPING_SCHEMA_OR_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "accounting_authority": False,
    "cache_database_self_authenticating": False,
    "document_packet_content_roots_authenticated": True,
    "family_matching_authority": False,
    "full_upstream_audit_required_to_publish_new_store_revision": True,
    "mapping_authority": False,
    "schema_authority": False,
    "tracked_manifest_and_database_content_ref_required": True,
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PACKET_FIELDS = {
    "assurance",
    "bank_provenance",
    "document_evidence_root_sha256",
    "document_id",
    "document_ordinal",
    "line_count",
    "packet_id",
    "page_count",
    "period",
    "scope",
    "source_pdf_ref",
    "year",
}
_MANIFEST_FIELDS = {
    "audit_commit",
    "authority",
    "claim_boundary",
    "database_ref",
    "documents",
    "format_version",
    "implementation_refs",
    "input_indices",
    "inventory_ref",
    "manifest_id",
    "metrics",
    "state",
}


class FamilyFirstDocumentEvidenceStoreV1Error(RuntimeError):
    """The document evidence store, tracked manifest, or migration audit drifted."""


def _error(message: str) -> FamilyFirstDocumentEvidenceStoreV1Error:
    return FamilyFirstDocumentEvidenceStoreV1Error(message)


def _stable_bytes(path: Path, label: str) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise _error(f"{label} is not one single-link regular file")
        payload = path.read_bytes()
        after = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise _error(f"cannot read stable {label}") from exc

    def identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
        return (
            value.st_dev,
            value.st_ino,
            value.st_mode,
            value.st_nlink,
            value.st_size,
            value.st_mtime_ns,
        )

    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise _error(f"{label} changed while being read")
    return payload


def _stream_ref(root: Path, path: Path, label: str) -> dict[str, Any]:
    absolute = Path(os.path.abspath(path))
    try:
        relative = absolute.relative_to(root)
        before = absolute.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise _error(f"{label} is not one single-link regular file")
        digest = hashlib.sha256()
        size = 0
        with absolute.open("rb") as stream:
            while chunk := stream.read(8 * 1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
        after = absolute.stat(follow_symlinks=False)
    except (OSError, ValueError) as exc:
        raise _error(f"cannot hash root-contained {label}") from exc
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ) or size != before.st_size:
        raise _error(f"{label} changed while being hashed")
    return {
        "path": relative.as_posix(),
        "sha256": digest.hexdigest(),
        "size_bytes": size,
    }


def _content_ref(value: Any, label: str) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"path", "sha256", "size_bytes"}
        or type(value["path"]) is not str
        or not value["path"]
        or Path(value["path"]).is_absolute()
        or ".." in Path(value["path"]).parts
        or type(value["sha256"]) is not str
        or _SHA256.fullmatch(value["sha256"]) is None
        or type(value["size_bytes"]) is not int
        or value["size_bytes"] < 0
    ):
        raise _error(f"{label} content reference drifted")
    return canonical_clone_v1(value)


def _packet(value: Any, expected_ordinal: int) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _PACKET_FIELDS:
        raise _error("document evidence packet fields drifted")
    if (
        value["document_ordinal"] != expected_ordinal
        or type(value["document_id"]) is not str
        or not value["document_id"]
        or type(value["document_evidence_root_sha256"]) is not str
        or _SHA256.fullmatch(value["document_evidence_root_sha256"]) is None
        or type(value["packet_id"]) is not str
        or not value["packet_id"].startswith("ffdesv1:document:")
        or type(value["bank_provenance"]) is not str
        or not value["bank_provenance"]
        or type(value["year"]) is not int
        or not 2000 <= value["year"] <= 2100
        or type(value["period"]) is not str
        or not value["period"]
        or type(value["scope"]) is not str
        or not value["scope"]
        or value["assurance"] not in {"AUDITED", "REVIEWED", "UNAUDITED"}
        or type(value["page_count"]) is not int
        or value["page_count"] <= 0
        or type(value["line_count"]) is not int
        or value["line_count"] <= 0
    ):
        raise _error("document evidence packet identity/denominator drifted")
    source = _content_ref(value["source_pdf_ref"], "document source PDF")
    material = canonical_clone_v1(value)
    packet_id = material.pop("packet_id")
    if packet_id != "ffdesv1:document:" + canonical_json_sha256_v1(material):
        raise _error("document evidence packet ID drifted")
    material["packet_id"] = packet_id
    material["source_pdf_ref"] = source
    return canonical_clone_v1(material)


def validate_family_first_document_evidence_manifest_shape_v1(value: Any) -> dict[str, Any]:
    """Validate closed manifest shape without granting tracked-store authority."""

    if type(value) is not dict or set(value) != _MANIFEST_FIELDS:
        raise _error("document evidence manifest fields drifted")
    if (
        value["format_version"] != FORMAT_VERSION
        or value["claim_boundary"] != CLAIM_BOUNDARY
        or value["state"] != "FULL_AUDIT_DOCUMENT_EVIDENCE_ROOTS_SEALED"
        or not same_typed_json_v1(value["authority"], _AUTHORITY)
        or type(value["documents"]) is not list
        or not value["documents"]
        or type(value["audit_commit"]) is not str
        or re.fullmatch(r"[0-9a-f]{40,64}", value["audit_commit"]) is None
        or type(value["input_indices"]) is not dict
        or set(value["input_indices"])
        != {"numeric_axis_sha256", "numeric_receipt_id", "semantic_index_id"}
        or type(value["implementation_refs"]) is not dict
        or set(value["implementation_refs"]) != {"document_store", "query_cache_builder"}
        or type(value["metrics"]) is not dict
        or set(value["metrics"]) != {"document_count", "line_count", "page_count"}
    ):
        raise _error("document evidence manifest identity/shape drifted")
    documents = [_packet(item, ordinal) for ordinal, item in enumerate(value["documents"], 1)]
    metrics = value["metrics"]
    if (
        type(metrics["document_count"]) is not int
        or type(metrics["page_count"]) is not int
        or type(metrics["line_count"]) is not int
        or metrics["document_count"] != len(documents)
        or metrics["page_count"] != sum(item["page_count"] for item in documents)
        or metrics["line_count"] != sum(item["line_count"] for item in documents)
        or len({item["packet_id"] for item in documents}) != len(documents)
    ):
        raise _error("document evidence manifest denominators drifted")
    _content_ref(value["database_ref"], "document evidence database")
    _content_ref(value["inventory_ref"], "filing inventory")
    for label, reference in value["implementation_refs"].items():
        _content_ref(reference, f"{label} implementation")
    indices = value["input_indices"]
    if (
        type(indices["semantic_index_id"]) is not str
        or not indices["semantic_index_id"]
        or type(indices["numeric_receipt_id"]) is not str
        or not indices["numeric_receipt_id"]
        or type(indices["numeric_axis_sha256"]) is not str
        or _SHA256.fullmatch(indices["numeric_axis_sha256"]) is None
    ):
        raise _error("document evidence input index identity drifted")
    material = canonical_clone_v1(value)
    manifest_id = material.pop("manifest_id")
    if manifest_id != "ffdesv1:manifest:" + canonical_json_sha256_v1(material):
        raise _error("document evidence manifest ID drifted")
    return canonical_clone_v1(value)


def _hash_record(digest: Any, kind: str, value: dict[str, Any]) -> None:
    digest.update(canonical_json_bytes_v1({"kind": kind, "value": value}))


def _document_packet_from_connection(
    connection: Any,
    *,
    expected_ordinal: int,
    filing: dict[str, Any],
) -> dict[str, Any]:
    document_row = connection.execute(
        "SELECT * FROM documents WHERE document_ordinal = ?",
        (expected_ordinal,),
    ).fetchone()
    if document_row is None:
        raise _error("document evidence database source order drifted")
    document = dict(document_row)
    if document["document_ordinal"] != expected_ordinal or not same_typed_json_v1(
        filing["content_ref"],
        {
            "path": document["source_path"],
            "sha256": document["source_sha256"],
            "size_bytes": document["source_size_bytes"],
        },
    ):
        raise _error("document evidence database/inventory source differs")
    if (
        filing["bank_provenance"] != document["bank"]
        or filing["year"] != document["year"]
        or filing["period"] != document["period"]
        or filing["scope"] != document["scope"]
    ):
        raise _error("document evidence database/inventory provenance differs")
    digest = hashlib.sha256()
    # Transport/global ordinals are deliberately absent from the evidence
    # root. If one document gains a line, later global sample IDs and crop
    # paths may shift even though their local pixels/text/numbers did not.
    _hash_record(
        digest,
        "DOCUMENT",
        {
            key: document[key]
            for key in (
                "bank",
                "year",
                "period",
                "scope",
                "source_sha256",
                "source_size_bytes",
                "page_count",
                "line_count",
            )
        },
    )
    pages = connection.execute(
        "SELECT * FROM pages WHERE document_ordinal = ? ORDER BY physical_page",
        (expected_ordinal,),
    ).fetchall()
    lines = connection.execute(
        """
        SELECT physical_page, line_ordinal,
               bbox_left, bbox_top, bbox_right, bbox_bottom,
               crop_sha256, crop_size_bytes,
               vietocr_text, vietocr_text_nfc, accentless_text,
               semantic_probability, processed_width, processed_height,
               numeric_text, numeric_score
          FROM lines WHERE document_ordinal = ?
        ORDER BY physical_page, line_ordinal
        """,
        (expected_ordinal,),
    ).fetchall()
    if len(pages) != document["page_count"] or len(lines) != document["line_count"]:
        raise _error("document evidence packet page/line denominator drifted")
    for row in pages:
        _hash_record(digest, "PAGE", dict(row))
    for row in lines:
        _hash_record(digest, "LINE", dict(row))
    material = {
        "assurance": filing["assurance"],
        "bank_provenance": filing["bank_provenance"],
        "document_evidence_root_sha256": digest.hexdigest(),
        "document_id": document["document_id"],
        "document_ordinal": expected_ordinal,
        "line_count": document["line_count"],
        "page_count": document["page_count"],
        "period": filing["period"],
        "scope": filing["scope"],
        "source_pdf_ref": canonical_clone_v1(filing["content_ref"]),
        "year": filing["year"],
    }
    return {
        **material,
        "packet_id": "ffdesv1:document:" + canonical_json_sha256_v1(material),
    }


def _document_packets(database_path: Path, inventory: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    filings = inventory["filings"]
    by_source = {item["content_ref"]["sha256"]: item for item in filings}
    if len(by_source) != len(filings):
        raise _error("filing inventory source hashes are not unique")
    packets = []
    with cache_v1._connect(database_path) as connection:
        document_rows = connection.execute(
            "SELECT * FROM documents ORDER BY document_ordinal"
        ).fetchall()
        for expected_ordinal, document_row in enumerate(document_rows, 1):
            document = dict(document_row)
            if document["document_ordinal"] != expected_ordinal:
                raise _error("document evidence database source order drifted")
            filing = by_source.get(document["source_sha256"])
            if filing is None:
                raise _error("document evidence database/inventory source differs")
            packets.append(
                _document_packet_from_connection(
                    connection,
                    expected_ordinal=expected_ordinal,
                    filing=filing,
                )
            )
    return tuple(packets)


def _implementation_ref(root: Path, relative: Path) -> dict[str, Any]:
    payload = _stable_bytes(root / relative, f"{relative} implementation")
    return {
        "path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _manifest_from_database(
    root: Path,
    database_path: Path,
    semantic_projection: dict[str, Any],
    numeric_projection: dict[str, Any],
    *,
    audit_commit: str,
    inventory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    database_projection = cache_v1.project_family_first_ocr_query_cache_v1(database_path)
    sources = database_projection["sources"]
    if (
        sources["semantic_index_id"] != semantic_projection["index_id"]
        or sources["numeric_receipt_id"] != numeric_projection["receipt_id"]
        or sources["numeric_axis_sha256"] != numeric_projection["numeric_axis_sha256"]
    ):
        raise _error("document evidence database belongs to another index snapshot")
    if inventory is None:
        inventory = inventory_v1.read_family_first_filing_inventory_v1(root)
    documents = list(_document_packets(database_path, inventory))
    metrics = {
        "document_count": len(documents),
        "line_count": sum(item["line_count"] for item in documents),
        "page_count": sum(item["page_count"] for item in documents),
    }
    if not same_typed_json_v1(
        metrics,
        {
            "document_count": semantic_projection["metrics"]["document_count"],
            "line_count": semantic_projection["metrics"]["sample_count"],
            "page_count": semantic_projection["metrics"]["page_count"],
        },
    ) or any(
        semantic_projection["metrics"][key] != numeric_projection["metrics"][key]
        for key in ("document_count", "page_count", "sample_count")
    ):
        raise _error("document evidence store/index denominators differ")
    material = {
        "audit_commit": audit_commit,
        "authority": canonical_clone_v1(_AUTHORITY),
        "claim_boundary": CLAIM_BOUNDARY,
        "database_ref": _stream_ref(root, database_path, "document evidence database"),
        "documents": documents,
        "format_version": FORMAT_VERSION,
        "implementation_refs": {
            "document_store": _implementation_ref(
                root,
                Path("src/bctc_ai/evaluation/family_first_document_evidence_store_v1.py"),
            ),
            "query_cache_builder": _implementation_ref(
                root,
                Path("src/bctc_ai/evaluation/family_first_ocr_query_cache_v1.py"),
            ),
        },
        "input_indices": {
            "numeric_axis_sha256": sources["numeric_axis_sha256"],
            "numeric_receipt_id": sources["numeric_receipt_id"],
            "semantic_index_id": sources["semantic_index_id"],
        },
        "inventory_ref": canonical_clone_v1(inventory["inventory_ref"]),
        "metrics": metrics,
        "state": "FULL_AUDIT_DOCUMENT_EVIDENCE_ROOTS_SEALED",
    }
    return validate_family_first_document_evidence_manifest_shape_v1(
        {**material, "manifest_id": "ffdesv1:manifest:" + canonical_json_sha256_v1(material)}
    )


def _numeric_projection(
    capability: numeric_v3.AuthenticatedFamilyFirstPPocrV6NumericIndexV3,
) -> dict[str, Any]:
    try:
        _state, receipt, _batch, _plan, _private = numeric_v3._live_index(capability)
    except numeric_v3.FamilyFirstPPocrV6NumericIndexV3Error as exc:
        raise _error("numeric index changed during document store migration") from exc
    return {
        "format_version": numeric_v3.FORMAT_VERSION,
        "metrics": canonical_clone_v1(receipt["metrics"]),
        "numeric_axis_sha256": receipt["numeric_axis_sha256"],
        "receipt_id": receipt["receipt_id"],
        "state": receipt["state"],
    }


def build_authenticated_family_first_document_evidence_manifest_v1(
    project_root: Path,
    semantic_index_capability: semantic_v1.AuthenticatedFamilyFirstSemanticIndexV1,
    numeric_index_capability: numeric_v3.AuthenticatedFamilyFirstPPocrV6NumericIndexV3,
    *,
    database_path: Path = cache_v1.DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    """Perform one full migration audit and return the sealable store manifest."""

    root = project_root.resolve()
    audit_commit = _clean_head(root)
    database = database_path if database_path.is_absolute() else root / database_path
    semantic_projection = semantic_v1.project_authenticated_family_first_semantic_index_v1(
        semantic_index_capability
    )
    numeric_projection = _numeric_projection(numeric_index_capability)
    database.parent.mkdir(parents=True, exist_ok=True)
    audit_directory = Path(
        tempfile.mkdtemp(prefix=".family-first-document-store-audit-", dir=database.parent)
    )
    try:
        audit_database = audit_directory / "audit.sqlite3"
        cache_v1.build_family_first_ocr_query_cache_v1(root, audit_database)
        inventory = inventory_v1.read_family_first_filing_inventory_v1(root)
        live_packets = _document_packets(database, inventory)
        audit_packets = _document_packets(audit_database, inventory)
        if not same_typed_json_v1(live_packets, audit_packets):
            raise _error("materialized document evidence differs from full audit rebuild")
    finally:
        shutil.rmtree(audit_directory)
    final_semantic = semantic_v1.project_authenticated_family_first_semantic_index_v1(
        semantic_index_capability
    )
    final_numeric = _numeric_projection(numeric_index_capability)
    if not same_typed_json_v1(semantic_projection, final_semantic) or not same_typed_json_v1(
        numeric_projection, final_numeric
    ):
        raise _error("upstream indices changed during document evidence migration audit")
    if _clean_head(root) != audit_commit:
        raise _error("Git HEAD/worktree changed during document evidence migration audit")
    return _manifest_from_database(
        root,
        database,
        semantic_projection,
        numeric_projection,
        audit_commit=audit_commit,
        inventory=inventory,
    )


def _git(root: Path, *arguments: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", os.fspath(root), *arguments],
            check=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise _error("document evidence tracked Git check failed") from exc


def _clean_head(root: Path) -> str:
    top = Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != root or _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise _error("document evidence store requires exact clean Git toplevel")
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    if re.fullmatch(r"[0-9a-f]{40,64}", head) is None:
        raise _error("document evidence store Git HEAD drifted")
    return head


def _tracked_manifest(root: Path) -> tuple[dict[str, Any], bytes]:
    _clean_head(root)
    relative = REGISTRY_PATH.as_posix()
    disk = _stable_bytes(root / REGISTRY_PATH, "tracked document evidence manifest")
    committed = _git(root, "show", f"HEAD:{relative}")
    if disk != committed:
        raise _error("tracked document evidence manifest differs from clean HEAD")
    try:
        value = json.loads(disk.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error("tracked document evidence manifest is not strict JSON") from exc
    if type(value) is not dict or disk != canonical_json_bytes_v1(value) + b"\n":
        raise _error("tracked document evidence manifest is not canonical JSON")
    return validate_family_first_document_evidence_manifest_shape_v1(value), disk


@dataclass(frozen=True)
class _StoreState:
    root: Path
    manifest: dict[str, Any]
    manifest_payload: bytes
    database_path: Path
    database_identity: tuple[int, int, int, int]


class AuthenticatedFamilyFirstDocumentEvidenceStoreV1:
    """Opaque live handle for the tracked immutable document evidence store."""

    __slots__ = ("__weakref__",)

    def __new__(cls, token: object | None = None):
        if token is not _MINT:
            raise TypeError("document evidence store handles cannot be constructed")
        return super().__new__(cls)

    def __copy__(self) -> None:
        raise TypeError("document evidence store handles cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]) -> None:
        raise TypeError("document evidence store handles cannot be copied")

    def __reduce__(self) -> None:
        raise TypeError("document evidence store handles cannot be pickled")


_MINT = object()
_STORES: weakref.WeakKeyDictionary[AuthenticatedFamilyFirstDocumentEvidenceStoreV1, _StoreState] = (
    weakref.WeakKeyDictionary()
)


def authenticate_family_first_document_evidence_store_v1(
    project_root: Path,
) -> AuthenticatedFamilyFirstDocumentEvidenceStoreV1:
    """Authenticate the tracked manifest and its exact immutable SQLite bytes once."""

    if not isinstance(project_root, Path):
        raise _error("document evidence project root must be one pathlib Path")
    root = project_root.resolve()
    manifest, payload = _tracked_manifest(root)
    try:
        subprocess.run(
            [
                "git",
                "-C",
                os.fspath(root),
                "merge-base",
                "--is-ancestor",
                manifest["audit_commit"],
                "HEAD",
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise _error("document evidence audit commit is not an ancestor of clean HEAD") from exc
    database_ref = manifest["database_ref"]
    database_path = root / database_ref["path"]
    observed_ref = _stream_ref(root, database_path, "document evidence database")
    if not same_typed_json_v1(database_ref, observed_ref):
        raise _error("document evidence database differs from tracked content reference")
    projection = cache_v1.project_family_first_ocr_query_cache_v1(database_path)
    if (
        projection["document_count"] != manifest["metrics"]["document_count"]
        or projection["page_count"] != manifest["metrics"]["page_count"]
        or projection["line_count"] != manifest["metrics"]["line_count"]
        or projection["sources"]["semantic_index_id"]
        != manifest["input_indices"]["semantic_index_id"]
        or projection["sources"]["numeric_receipt_id"]
        != manifest["input_indices"]["numeric_receipt_id"]
        or projection["sources"]["numeric_axis_sha256"]
        != manifest["input_indices"]["numeric_axis_sha256"]
    ):
        raise _error("document evidence database metadata differs from tracked manifest")
    for reference in manifest["implementation_refs"].values():
        historical = _git(root, "show", f"{manifest['audit_commit']}:{reference['path']}")
        observed = {
            "path": reference["path"],
            "sha256": hashlib.sha256(historical).hexdigest(),
            "size_bytes": len(historical),
        }
        if not same_typed_json_v1(reference, observed):
            raise _error("document evidence implementation differs from its audit commit")
    inventory_ref = _stream_ref(root, root / manifest["inventory_ref"]["path"], "filing inventory")
    if not same_typed_json_v1(manifest["inventory_ref"], inventory_ref):
        raise _error("filing inventory differs from tracked document evidence manifest")
    metadata = database_path.stat(follow_symlinks=False)
    capability = AuthenticatedFamilyFirstDocumentEvidenceStoreV1(_MINT)
    _STORES[capability] = _StoreState(
        root,
        manifest,
        payload,
        database_path,
        (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns),
    )
    return capability


def _live_store(capability: Any) -> _StoreState:
    if type(capability) is not AuthenticatedFamilyFirstDocumentEvidenceStoreV1:
        raise _error("one exact live document evidence store handle is required")
    state = _STORES.get(capability)
    if state is None:
        raise _error("document evidence store handle is not live")
    manifest, payload = _tracked_manifest(state.root)
    metadata = state.database_path.stat(follow_symlinks=False)
    identity = (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns)
    if (
        payload != state.manifest_payload
        or not same_typed_json_v1(manifest, state.manifest)
        or identity != state.database_identity
    ):
        raise _error("document evidence store changed after authentication")
    return state


def project_authenticated_family_first_document_evidence_store_v1(
    capability: AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
) -> dict[str, Any]:
    state = _live_store(capability)
    return {
        "authority": canonical_clone_v1(_AUTHORITY),
        "format_version": FORMAT_VERSION,
        "input_indices": canonical_clone_v1(state.manifest["input_indices"]),
        "manifest_id": state.manifest["manifest_id"],
        "metrics": canonical_clone_v1(state.manifest["metrics"]),
        "state": state.manifest["state"],
    }


def read_authenticated_family_first_document_packet_v1(
    capability: AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    *,
    document_ordinal: int,
) -> dict[str, Any]:
    state = _live_store(capability)
    if (
        type(document_ordinal) is not int
        or not 1 <= document_ordinal <= state.manifest["metrics"]["document_count"]
    ):
        raise _error("document evidence packet ordinal lies outside the store")
    return copy.deepcopy(state.manifest["documents"][document_ordinal - 1])


def read_authenticated_family_first_document_page_renders_v1(
    capability: AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    *,
    document_ordinal: int,
    physical_pages: tuple[int, ...],
) -> tuple[dict[str, Any], ...]:
    """Re-render only shortlisted pages and authenticate their sealed pixels.

    This accessor deliberately does not reopen OCR or the full semantic axis.
    The tracked document packet pins the exact source PDF, while the immutable
    SQLite page record pins the 200-DPI PNG bytes and dimensions.  The returned
    snapshots use the common authenticated-render shape so downstream dash-cell
    crops retain the same replay and provenance checks as the full live lane.
    """

    state = _live_store(capability)
    if (
        type(document_ordinal) is not int
        or not 1 <= document_ordinal <= state.manifest["metrics"]["document_count"]
        or type(physical_pages) is not tuple
        or not physical_pages
        or any(type(page) is not int or page <= 0 for page in physical_pages)
        or tuple(sorted(set(physical_pages))) != physical_pages
    ):
        raise _error("document evidence render selection drifted")
    packet = state.manifest["documents"][document_ordinal - 1]
    if any(page > packet["page_count"] for page in physical_pages):
        raise _error("document evidence render page lies outside the source PDF")
    source_path = state.root / packet["source_pdf_ref"]["path"]
    source = _stable_bytes(source_path, "document evidence source PDF")
    if not same_typed_json_v1(
        packet["source_pdf_ref"],
        _stream_ref(state.root, source_path, "document evidence source PDF"),
    ):
        raise _error("document evidence source PDF differs from its packet")
    with cache_v1._connect(state.database_path) as connection:
        references = {
            row["physical_page"]: {
                "pixel_height": row["pixel_height"],
                "pixel_width": row["pixel_width"],
                "sha256": row["render_sha256"],
                "size_bytes": row["render_size_bytes"],
            }
            for row in connection.execute(
                "SELECT physical_page, pixel_width, pixel_height, render_sha256, "
                "render_size_bytes FROM pages WHERE document_ordinal = ? "
                "AND physical_page IN ("
                + ",".join("?" for _page in physical_pages)
                + ") ORDER BY physical_page",
                (document_ordinal, *physical_pages),
            )
        }
    if tuple(references) != physical_pages:
        raise _error("document evidence render selection is absent from the page axis")
    snapshots = []
    for physical_page in physical_pages:
        render = render_v1._render_page(source, physical_page=physical_page, dpi=200)
        reference = render_v1._render_reference(references[physical_page])
        image = render_v1._png_image(render)
        if (
            len(render) != reference["size_bytes"]
            or hashlib.sha256(render).hexdigest() != reference["sha256"]
            or image.width != reference["pixel_width"]
            or image.height != reference["pixel_height"]
        ):
            raise _error("document evidence page pixels differ from the sealed render reference")
        material = {
            "archive_id": state.manifest["manifest_id"],
            "authority": canonical_clone_v1(render_v1._RENDER_AUTHORITY),
            "document_ordinal": document_ordinal,
            "format_version": render_v1.RENDER_FORMAT_VERSION,
            "index_id": state.manifest["input_indices"]["semantic_index_id"],
            "physical_page": physical_page,
            "plan_id": state.manifest["manifest_id"],
            "render_ref": reference,
            "state": "AUTHENTICATED_EXACT_SOURCE_PAGE_RENDER_SNAPSHOT",
        }
        snapshot = {
            **material,
            "render_id": "ffaprv1:render:" + canonical_json_sha256_v1(material),
            "render_png_bytes": render,
        }
        render_v1._validated_render_snapshot(snapshot)
        snapshots.append(snapshot)
    if (
        _live_store(capability) is not state
        or _stable_bytes(source_path, "document evidence source PDF") != source
    ):
        raise _error("document evidence store or source changed during page render replay")
    return tuple(snapshots)


def read_authenticated_family_first_topology_scans_v1(
    capability: AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    family_spec: Any,
    *,
    jobs: int = 12,
) -> tuple[dict[str, Any], ...]:
    """Return exact source-ordered topology scans through a disposable result cache.

    The SQLite evidence store remains the authenticated source.  Cache hits are
    keyed by each document identity, the exact family specification, and the
    topology-engine trust closure; misses alone are recomputed in parallel.
    """

    state = _live_store(capability)
    topology_path = state.root / cache_v1.DEFAULT_TOPOLOGY_DATABASE_PATH
    try:
        cache_v1.refresh_cached_topology_results_v1(
            state.database_path,
            topology_path,
            family_spec,
            jobs=jobs,
        )
        scans = cache_v1.read_cached_topology_results_v1(
            state.database_path,
            topology_path,
            family_spec,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise _error("cannot build exact authenticated family topology cache") from exc
    if len(scans) != state.manifest["metrics"]["document_count"]:
        raise _error("authenticated family topology denominator drifted")
    final = _live_store(capability)
    if final is not state:
        raise _error("document evidence store changed during family topology scan")
    return tuple(canonical_clone_v1(scan) for scan in scans)


def read_authenticated_family_first_document_evidence_snapshot_v1(
    capability: AuthenticatedFamilyFirstDocumentEvidenceStoreV1,
    *,
    document_ordinal: int,
    selected_pages: tuple[int, ...],
) -> dict[str, Any]:
    """Read and root-check one document for bounded downstream recomputation.

    The full document line axis is returned because topology regions use
    document-local offsets. Page widths/heights are exposed only for the
    selected region pages. The accessor recomputes the document packet root
    from SQLite before returning, so a family edit never needs to replay the
    other 139 filings.
    """

    state = _live_store(capability)
    if (
        type(document_ordinal) is not int
        or not 1 <= document_ordinal <= state.manifest["metrics"]["document_count"]
        or type(selected_pages) is not tuple
        or not selected_pages
        or any(type(page) is not int or page <= 0 for page in selected_pages)
        or len(selected_pages) != len(set(selected_pages))
    ):
        raise _error("document evidence snapshot selection drifted")
    expected = state.manifest["documents"][document_ordinal - 1]
    filing = {
        "assurance": expected["assurance"],
        "bank_provenance": expected["bank_provenance"],
        "content_ref": expected["source_pdf_ref"],
        "period": expected["period"],
        "scope": expected["scope"],
        "year": expected["year"],
    }
    with cache_v1._connect(state.database_path) as connection:
        observed = _document_packet_from_connection(
            connection,
            expected_ordinal=document_ordinal,
            filing=filing,
        )
        if not same_typed_json_v1(observed, expected):
            raise _error("document evidence snapshot differs from its authenticated packet root")
        dimensions = {
            row["physical_page"]: {
                "pixel_height": row["pixel_height"],
                "pixel_width": row["pixel_width"],
                "render_sha256": row["render_sha256"],
                "render_size_bytes": row["render_size_bytes"],
            }
            for row in connection.execute(
                "SELECT physical_page, pixel_width, pixel_height, render_sha256, "
                "render_size_bytes FROM pages WHERE document_ordinal = ?",
                (document_ordinal,),
            )
        }
        records = cache_v1._line_records(connection, document_ordinal)
    if any(page not in dimensions for page in selected_pages) or not records:
        raise _error("document evidence snapshot selected page is absent")
    pages: dict[int, list[dict[str, Any]]] = {}
    for row in records:
        pages.setdefault(row["physical_page"], []).append(
            {
                "bbox": [
                    row["bbox_left"],
                    row["bbox_top"],
                    row["bbox_right"],
                    row["bbox_bottom"],
                ],
                "crop_ref": {
                    "path": row["crop_path"],
                    "sha256": row["crop_sha256"],
                    "size_bytes": row["crop_size_bytes"],
                },
                "line_ordinal": row["line_ordinal"],
                "numeric_recognition": {
                    "raw_prediction": row["numeric_text"],
                    "reader_score": row["numeric_score"],
                },
                "sample_id": row["sample_id"],
                "vietocr_text": row["vietocr_text"],
            }
        )
    selected = set(selected_pages)
    joined_pages = [
        {
            "lines": lines,
            "page_sequence": page,
            "page_width": dimensions[page]["pixel_width"] if page in selected else None,
        }
        for page, lines in sorted(pages.items())
    ]
    material = {
        "document_packet": canonical_clone_v1(expected),
        "joined_pages": joined_pages,
        "manifest_id": state.manifest["manifest_id"],
        "selected_page_dimensions": [
            {"physical_page": page, **dimensions[page]} for page in selected_pages
        ],
    }
    return canonical_clone_v1(
        {
            **material,
            "snapshot_id": "ffdesv1:snapshot:" + canonical_json_sha256_v1(material),
        }
    )
