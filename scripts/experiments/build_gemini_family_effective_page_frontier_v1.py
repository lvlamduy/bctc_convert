#!/usr/bin/env python3
"""Freeze terminal Gemini region repairs as one family-specific page frontier."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (  # noqa: E402
    resolved_gemini_family_region_repair_overlay_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_family_effective_page_frontier_v1 import (  # noqa: E402
    build_gemini_family_effective_page_frontier_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    page_json_region_repair_lineages_v1,
)


class BuildGeminiFamilyEffectivePageFrontierV1Error(RuntimeError):
    """The source databases, base corpus, or output identity drifted."""


def _error(message: str) -> BuildGeminiFamilyEffectivePageFrontierV1Error:
    return BuildGeminiFamilyEffectivePageFrontierV1Error(message)


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


def _content_path(artifact_root: Path, reference: dict[str, Any]) -> Path:
    if type(reference) is not dict or set(reference) != {"path", "sha256", "size_bytes"}:
        raise _error("base corpus content reference fields drifted")
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise _error("base corpus content reference escapes its root")
    path = artifact_root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size != reference["size_bytes"]
        or _sha256(path) != reference["sha256"]
    ):
        raise _error("base corpus content reference does not authenticate")
    return path


def _snapshot_sqlite(source: Path, *, artifact_root: Path, label: str) -> dict[str, Any]:
    if source.is_symlink() or not source.is_file():
        raise _error("SQLite snapshot source is absent or not regular")
    directory = artifact_root / "effective-page-frontier-snapshots"
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, stage_name = tempfile.mkstemp(prefix=f".{label}-", suffix=".sqlite3", dir=directory)
    os.close(descriptor)
    stage = Path(stage_name)
    try:
        with sqlite3.connect(f"file:{source.resolve()}?mode=ro", uri=True) as incoming:
            with sqlite3.connect(stage) as outgoing:
                incoming.backup(outgoing)
                result = outgoing.execute("PRAGMA integrity_check").fetchone()
                if result is None or result[0] != "ok":
                    raise _error("SQLite snapshot integrity check failed")
        with stage.open("rb") as stream:
            os.fsync(stream.fileno())
        digest = _sha256(stage)
        destination = directory / f"{label}-{digest}.sqlite3"
        if destination.exists():
            if (
                destination.is_symlink()
                or not destination.is_file()
                or destination.stat().st_size != stage.stat().st_size
                or _sha256(destination) != digest
            ):
                raise _error("existing SQLite snapshot identity drifted")
            stage.unlink()
        else:
            os.chmod(stage, 0o444)
            os.replace(stage, destination)
        return {
            "path": str(destination.relative_to(artifact_root)),
            "sha256": digest,
            "size_bytes": destination.stat().st_size,
        }
    finally:
        stage.unlink(missing_ok=True)


def _write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error("effective page frontier output already exists with different bytes")
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
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--page-database", type=Path, required=True)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--repair-source-family-run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    artifact_root = args.artifact_root.resolve()
    output_dir = args.output_dir.resolve()
    if not output_dir.is_relative_to(artifact_root):
        raise _error("effective page frontier output must lie under its artifact root")
    index = validate_current_corpus_manifest_index_v1(_json(args.corpus_index))
    base_ids = []
    for document in index["documents"]:
        manifest = _json(_content_path(artifact_root, document["document_manifest_ref"]))
        if (
            manifest.get("document_manifest_id") != document["document_manifest_id"]
            or type(manifest.get("pages")) is not list
        ):
            raise _error("base document manifest does not replay")
        base_ids.extend(page.get("page_json_version_id") for page in manifest["pages"])
    if len(base_ids) != index["summary"]["page_count"] or len(set(base_ids)) != len(base_ids):
        raise _error("base page JSON frontier is incomplete or duplicate")

    page_database_ref = _snapshot_sqlite(
        args.page_database, artifact_root=artifact_root, label="page-store"
    )
    results_database_ref = _snapshot_sqlite(
        args.results_database, artifact_root=artifact_root, label="family-results"
    )
    page_snapshot = _content_path(artifact_root, page_database_ref)
    results_snapshot = _content_path(artifact_root, results_database_ref)
    overlay = resolved_gemini_family_region_repair_overlay_v1(
        results_snapshot, family_run_id=args.repair_source_family_run_id
    )
    lineages = page_json_region_repair_lineages_v1(
        page_snapshot,
        observed_page_json_version_ids=[
            item["selected_page_json_version_id"] for item in overlay["replacements"]
        ],
    )
    replacements = []
    for replacement, lineage in zip(overlay["replacements"], lineages, strict=True):
        if (
            replacement["base_page_json_version_id"] != lineage["base_page_json_version_id"]
            or replacement["selected_page_json_version_id"]
            != lineage["observed_page_json_version_id"]
        ):
            raise _error("repair job and page lineage disagree")
        replacements.append(
            {
                **replacement,
                "repair_id": lineage["repair_id"],
                "repair_receipt_sha256": lineage["repair_receipt_sha256"],
            }
        )
    frontier = build_gemini_family_effective_page_frontier_v1(
        base_corpus_manifest_index_id=index["corpus_manifest_index_id"],
        base_page_json_version_ids=base_ids,
        database_ref=page_database_ref,
        family_id=overlay["family_id"],
        job_status_counts=overlay["job_status_counts"],
        repair_source_family_run_id=overlay["repair_source_family_run_id"],
        replacements=replacements,
        results_database_ref=results_database_ref,
    )
    digest = frontier["effective_page_frontier_id"].removeprefix("gjfepfv1:frontier:")
    output = output_dir / f"{digest}.json"
    _write_once(output, canonical_json_bytes_v1(frontier) + b"\n")
    return {
        "database_ref": page_database_ref,
        "disposition": "SUCCEEDED",
        "effective_page_frontier_id": frontier["effective_page_frontier_id"],
        "job_status_counts": frontier["job_status_counts"],
        "output": str(output),
        "replacement_count": len(replacements),
        "results_database_ref": results_database_ref,
    }


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
