#!/usr/bin/env python3
"""Build an append-only status snapshot for whole-PDF-page Gemini repairs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_first_corpus_ledger_v1 import (  # noqa: E402
    list_corpus_tasks_v1,
    validate_gemini_json_first_corpus_plan_v1,
)
from bctc_ai.evaluation.gemini_json_first_page_render_v1 import (  # noqa: E402
    inspect_full_pdf_page_box_v1,
    render_full_pdf_page_v1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_current_document_manifest_selection_v1 import (  # noqa: E402
    GeminiCurrentDocumentManifestSelectionV1Error,
    load_current_document_manifest_selection_v1,
)

FORMAT_VERSION = "GEMINI_JSON_FIRST_WHOLE_PAGE_REPAIR_STATUS_V1"
TERMINAL_STATES = frozenset({"FAILED", "SUCCEEDED"})


class GeminiJsonFirstWholePageRepairStatusV1Error(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def _load_plan(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise GeminiJsonFirstWholePageRepairStatusV1Error("corpus plan is absent or not regular")
    try:
        value = json.loads(path.read_bytes())
        return validate_gemini_json_first_corpus_plan_v1(value)
    except Exception as exc:
        raise GeminiJsonFirstWholePageRepairStatusV1Error("corpus plan is invalid") from exc


def _manifest_ref(
    path: Path,
    *,
    document: dict[str, Any],
    expected_page_count: int,
) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "ABSENT"
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        return None, "NOT_ONE_REGULAR_SINGLE_LINK_FILE"
    raw = path.read_bytes()
    try:
        manifest = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "NOT_JSON"
    if type(manifest) is not dict or raw != canonical_json_bytes_v1(manifest) + b"\n":
        return None, "NOT_CANONICAL_JSON"
    claimed_id = manifest.get("document_manifest_id")
    material = {key: value for key, value in manifest.items() if key != "document_manifest_id"}
    if claimed_id != "gfdmv1:manifest:" + canonical_json_sha256_v1(material):
        return None, "MANIFEST_ID_MISMATCH"
    if (
        manifest.get("format_version") != "GEMINI_FINANCIAL_DOCUMENT_MANIFEST_V4"
        or manifest.get("page_count") != expected_page_count
        or manifest.get("document", {}).get("source_logical_name") != document["relative_path"]
        or manifest.get("document", {}).get("source_sha256") != document["source_sha256"]
        or manifest.get("document", {}).get("source_size_bytes") != document["source_size_bytes"]
    ):
        return None, "DOCUMENT_BINDING_MISMATCH"
    pages = manifest.get("pages")
    if (
        type(pages) is not list
        or [page.get("physical_page") for page in pages if type(page) is dict]
        != list(range(1, expected_page_count + 1))
        or any(page.get("status") == "UNRESOLVED_PAGE" for page in pages)
    ):
        return None, "PAGE_FRONTIER_MISMATCH"
    image_frontier = manifest.get("extraction_contract", {}).get("page_image_sha256s")
    if (
        type(image_frontier) is not list
        or [item.get("physical_page") for item in image_frontier if type(item) is dict]
        != list(range(1, expected_page_count + 1))
        or any(
            type(item.get("image_sha256")) is not str or len(item["image_sha256"]) != 64
            for item in image_frontier
        )
    ):
        return None, "IMAGE_FRONTIER_MISMATCH"
    return (
        {
            "document_manifest_id": claimed_id,
            "path": str(path),
            "sha256": sha256(raw).hexdigest(),
            "size_bytes": len(raw),
            "status_counts": manifest["status_counts"],
            "totals": manifest["totals"],
            "image_sha256s": {
                item["physical_page"]: item["image_sha256"] for item in image_frontier
            },
        },
        None,
    )


def build_whole_page_repair_status_v1(
    *,
    plan: dict[str, Any],
    ledger: Path,
    source_root: Path,
    artifact_root: Path,
) -> dict[str, Any]:
    tasks = {task["task_id"]: task for task in list_corpus_tasks_v1(ledger)}
    documents = []
    affected_page_count = 0
    disposition_counts: Counter[str] = Counter()
    for planned in plan["documents"]:
        document = planned["document"]
        source = source_root / document["relative_path"]
        if source.is_symlink() or not source.is_file() or source.stat().st_nlink != 1:
            raise GeminiJsonFirstWholePageRepairStatusV1Error(
                "planned source is absent or not one regular single-link file"
            )
        source_bytes = source.read_bytes()
        if (
            len(source_bytes) != document["source_size_bytes"]
            or sha256(source_bytes).hexdigest() != document["source_sha256"]
        ):
            raise GeminiJsonFirstWholePageRepairStatusV1Error("planned source binding drifted")
        planned_tasks = [tasks.get(item["task_id"]) for item in planned["tasks"]]
        if any(task is None for task in planned_tasks):
            raise GeminiJsonFirstWholePageRepairStatusV1Error(
                "planned document task is absent from the ledger"
            )
        document_root = artifact_root / "documents" / planned["document_plan_id"].split(":", 1)[1]
        selection_id = None
        try:
            selected = load_current_document_manifest_selection_v1(
                document_root,
                document_plan_id=planned["document_plan_id"],
                source_sha256=document["source_sha256"],
            )
        except GeminiCurrentDocumentManifestSelectionV1Error as exc:
            manifest = None
            manifest_error = "SELECTION_ERROR:" + str(exc)
        else:
            manifest_path = (
                document_root / "current-document-manifest.json"
                if selected is None
                else selected[1]
            )
            selection_id = None if selected is None else selected[0]["selection_id"]
            manifest, manifest_error = _manifest_ref(
                manifest_path,
                document=document,
                expected_page_count=document["page_count"],
            )
            if (
                manifest is not None
                and selected is not None
                and manifest["document_manifest_id"] != selected[0]["document_manifest_id"]
            ):
                manifest = None
                manifest_error = "SELECTION_MANIFEST_ID_MISMATCH"
        affected_pages = []
        manifest_image_mismatches = []
        with fitz.open(source) as pdf:
            if pdf.page_count != document["page_count"]:
                raise GeminiJsonFirstWholePageRepairStatusV1Error(
                    "planned source page count drifted"
                )
            for physical_page, page in enumerate(pdf, 1):
                inspection = inspect_full_pdf_page_box_v1(page)
                if inspection.mode == "DECLARED_PAGE_BOX":
                    continue
                affected_pages.append({"mode": inspection.mode, "physical_page": physical_page})
                if manifest is not None:
                    current = render_full_pdf_page_v1(
                        page,
                        physical_page=physical_page,
                        dpi=plan["policy"]["dpi"],
                        source_sha256=document["source_sha256"],
                    )
                    if manifest["image_sha256s"].get(physical_page) != current.page["image_sha256"]:
                        manifest_image_mismatches.append(physical_page)
        task_states = Counter(task["state"] for task in planned_tasks)
        if not affected_pages:
            disposition = "NOT_REQUIRED"
        elif manifest is not None and not manifest_image_mismatches:
            disposition = "COMPLETE_CURRENT_WHOLE_PAGE_MANIFEST"
        elif all(task["state"] in TERMINAL_STATES for task in planned_tasks):
            disposition = "REPAIR_REQUIRED"
        else:
            disposition = "PENDING_CURRENT_RENDERER"
        affected_page_count += len(affected_pages)
        disposition_counts[disposition] += 1
        manifest_record = None
        if manifest is not None:
            manifest_record = {
                key: value for key, value in manifest.items() if key != "image_sha256s"
            }
            manifest_record["selection_id"] = selection_id
        documents.append(
            {
                "affected_page_count": len(affected_pages),
                "affected_pages": affected_pages,
                "current_manifest": manifest_record,
                "current_manifest_error": manifest_error,
                "disposition": disposition,
                "document_plan_id": planned["document_plan_id"],
                "manifest_image_mismatch_pages": manifest_image_mismatches,
                "relative_path": document["relative_path"],
                "source_sha256": document["source_sha256"],
                "task_state_counts": dict(sorted(task_states.items())),
            }
        )
    material = {
        "corpus_plan_id": plan["corpus_plan_id"],
        "documents": documents,
        "format_version": FORMAT_VERSION,
        "policy": {
            "dpi": plan["policy"]["dpi"],
            "full_page_only": True,
            "semantic_geometry_authority": False,
        },
        "summary": {
            "affected_document_count": sum(
                1 for document in documents if document["affected_page_count"]
            ),
            "affected_page_count": affected_page_count,
            "disposition_counts": dict(sorted(disposition_counts.items())),
            "document_count": len(documents),
        },
    }
    return {
        **material,
        "repair_status_id": "gjfprsv1:status:" + canonical_json_sha256_v1(material),
    }


def _write_snapshot(output_dir: Path, status: dict[str, Any]) -> Path:
    if output_dir.is_symlink() or (output_dir.exists() and not output_dir.is_dir()):
        raise GeminiJsonFirstWholePageRepairStatusV1Error("output directory is invalid")
    output_dir.mkdir(parents=True, exist_ok=True)
    digest = status["repair_status_id"].split(":", 2)[2]
    output = output_dir / f"{digest}.json"
    payload = canonical_json_bytes_v1(status) + b"\n"
    if output.exists():
        if output.is_symlink() or not output.is_file() or output.read_bytes() != payload:
            raise GeminiJsonFirstWholePageRepairStatusV1Error("status snapshot path conflicts")
        return output
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o444)
        temporary.replace(output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return output


def main() -> int:
    args = _parser().parse_args()
    status = build_whole_page_repair_status_v1(
        plan=_load_plan(args.plan),
        ledger=args.ledger,
        source_root=args.source_root,
        artifact_root=args.artifact_root,
    )
    output = _write_snapshot(args.output_dir, status)
    print(
        json.dumps(
            {
                "output": str(output),
                "repair_status_id": status["repair_status_id"],
                "summary": status["summary"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
