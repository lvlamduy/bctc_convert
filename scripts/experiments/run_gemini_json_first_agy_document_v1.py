#!/usr/bin/env python3
"""Process one disjoint corpus document through Agy Gemini 3.7 Flash.

The worker reserves an OpenRouter-planned task as ``SUBMITTED`` before doing
any work, so the ordinary Vertex Flex supervisor cannot send the same PDF.  It
uses the exact production render, prompt and JSON Schema.  Each missing page is
attempted at low effort first, then medium and high only when the prior result
is unusable.  Existing authenticated page JSON is always reused.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_financial_page_json_v1 import (  # noqa: E402
    build_financial_page_json_prompt_v1,
    count_financial_page_content_v1,
    decode_financial_page_json_text_v1,
    financial_page_json_response_schema_v1,
)
from bctc_ai.evaluation.gemini_json_first_corpus_ledger_v1 import (  # noqa: E402
    AGY_PROVIDER_JOB_PREFIX,
    GeminiJsonFirstCorpusLedgerV1Error,
    acquire_corpus_task_execution_lock_v1,
    claim_agy_schema_alignment_recovery_pages_v1,
    claim_agy_tool_denied_orientation_repaired_pages_v1,
    claim_exhausted_openrouter_unaccepted_pages_for_agy_v1,
    claim_failed_openrouter_provider_pages_for_agy_v1,
    claim_legacy_failed_openrouter_provider_pages_for_agy_v1,
    claim_pending_openrouter_corpus_task_for_agy_v1,
    claim_source_render_repaired_pages_for_agy_v1,
    corpus_ledger_summary_v1,
    list_corpus_tasks_v1,
    openrouter_failed_task_repair_frontier_v1,
    seal_agy_corpus_task_v1,
    transition_corpus_task_v1,
    validate_gemini_json_first_corpus_plan_v1,
)
from bctc_ai.evaluation.gemini_json_first_page_render_v1 import (  # noqa: E402
    GeminiJsonFirstPageRenderV1Error,
    render_full_pdf_page_v1,
)
from bctc_ai.evaluation.gemini_json_first_provider_v1 import (  # noqa: E402
    CKEY_GATEWAY,
    CKEY_SERVICE_TIER,
    GOOGLE_BATCH_SERVICE_TIER,
    GOOGLE_MODEL,
    GOOGLE_STANDARD_SERVICE_TIER,
    OPENROUTER_SERVICE_TIER,
    OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
    ProviderResultV1,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    GeminiFinancialPageStoreV1Error,
    build_financial_document_manifest_v1,
    ingest_financial_page_extraction_v1,
)

FORMAT_VERSION = "GEMINI_JSON_FIRST_AGY_DOCUMENT_RUNNER_V1"
AGY_GATEWAY = "AGY_CLI"
AGY_SELECTED_PROVIDER = "Agy"
AGY_BINARY_DEFAULT = Path("/root/.local/bin/agy")
EFFORT_ORDER = ("low", "medium", "high")
AGY_MODEL_BY_EFFORT = {effort: f"gemini-3.7-flash-{effort}" for effort in EFFORT_ORDER}
REUSABLE_PROMPT_VARIANTS = ("simple", "items", "balanced", "scope", "compact")


class RunGeminiJsonFirstAgyDocumentV1Error(RuntimeError):
    pass


class _AgyPageImageIdentityV1Error(RuntimeError):
    """A page no longer matches the image identity authorized by its claim."""


@dataclass(frozen=True)
class _RenderedPage:
    image: bytes
    page: dict[str, Any]
    receipt: dict[str, Any]


@dataclass(frozen=True)
class _PageResult:
    physical_page: int
    disposition: str
    page: dict[str, Any]
    effort: str | None = None
    failure_kind: str | None = None
    prompt_variant: str | None = None


def _error(message: str) -> RunGeminiJsonFirstAgyDocumentV1Error:
    return RunGeminiJsonFirstAgyDocumentV1Error(message)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--task-id")
    repair = parser.add_mutually_exclusive_group()
    repair.add_argument("--terminal-provider-repair", action="store_true")
    repair.add_argument("--terminal-unaccepted-repair", action="store_true")
    repair.add_argument("--source-render-recovery", action="store_true")
    repair.add_argument("--tool-denied-orientation-recovery", action="store_true")
    repair.add_argument("--schema-alignment-recovery", action="store_true")
    parser.add_argument("--source-revision-registry", type=Path)
    parser.add_argument("--orientation-repair-registry", type=Path)
    parser.add_argument("--schema-alignment-repair-registry", type=Path)
    parser.add_argument("--historical-ledger", type=Path)
    parser.add_argument("--agy-binary", type=Path, default=AGY_BINARY_DEFAULT)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    return parser


def _json_file(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise _error(f"required JSON file is absent: {path}")
    try:
        value = json.loads(path.read_bytes())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _error(f"required JSON file is invalid: {path}") from exc
    if type(value) is not dict:
        raise _error(f"required JSON file is not one object: {path}")
    return value


def _write_or_verify(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error(f"immutable Agy artifact drifted: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _source(task: dict[str, Any], source_root: Path) -> Path:
    root = source_root.resolve()
    path = (root / task["relative_path"]).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise _error("Agy source path escapes its source root") from exc
    if path.is_symlink() or not path.is_file():
        raise _error("Agy source PDF is absent or not regular")
    source = path.read_bytes()
    if (
        sha256(source).hexdigest() != task["source_sha256"]
        or len(source) != task["source_size_bytes"]
    ):
        raise _error("Agy source PDF identity drifted")
    with fitz.open(stream=source, filetype="pdf") as document:
        if document.page_count < task["last_physical_page"]:
            raise _error("Agy source PDF page frontier drifted")
    return path


def _is_strict_legacy_subprocess_failure_v1(task: dict[str, Any]) -> bool:
    raw = task.get("last_receipt_json")
    try:
        receipt = json.loads(raw) if type(raw) is bytes else None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    fields = {
        "disposition",
        "provider_returncode",
        "provider_stderr_bytes",
        "provider_stderr_sha256",
        "provider_stdout_bytes",
        "provider_stdout_sha256",
        "retry_allowed",
    }
    return bool(
        type(receipt) is dict
        and set(receipt) == fields
        and receipt["disposition"] == "OPENROUTER_PROVIDER_SUBPROCESS_FAILURE"
        and type(receipt["provider_returncode"]) is int
        and receipt["provider_returncode"] == 1
        and type(receipt["provider_stderr_bytes"]) is int
        and receipt["provider_stderr_bytes"] > 0
        and type(receipt["provider_stdout_bytes"]) is int
        and receipt["provider_stdout_bytes"] == 0
        and receipt["provider_stdout_sha256"] == sha256(b"").hexdigest()
        and receipt["retry_allowed"] is False
        and all(
            type(receipt[field]) is str
            and len(receipt[field]) == 64
            and all(character in "0123456789abcdef" for character in receipt[field])
            for field in ("provider_stderr_sha256", "provider_stdout_sha256")
        )
    )


def _source_bound_store_frontier_v1(
    *,
    task: dict[str, Any],
    database: Path,
    artifact_root: Path,
) -> dict[str, Any]:
    """Partition one task using only its exact source-bound store rows."""
    if database.is_symlink() or not database.is_file():
        raise _error("Agy store database is absent or not regular")
    expected_pages = list(range(task["first_physical_page"], task["last_physical_page"] + 1))
    with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as connection:
        documents = connection.execute(
            "SELECT document_id FROM document WHERE source_sha256=? AND source_logical_name=? "
            "ORDER BY document_id",
            (task["source_sha256"], task["relative_path"]),
        ).fetchall()
        if len(documents) > 1:
            raise _error("Agy source-bound store document identity is ambiguous")
        stored_pages: list[int] = []
        if documents:
            stored_pages = [
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT p.physical_page FROM page AS p "
                    "JOIN page_json_version AS v USING(page_id) "
                    "WHERE p.document_id=? ORDER BY p.physical_page",
                    (documents[0][0],),
                )
            ]
    if any(type(page) is not int or page not in expected_pages for page in stored_pages):
        raise _error("Agy source-bound stored page frontier is invalid")
    failed_pages = sorted(set(expected_pages) - set(stored_pages))
    if not failed_pages:
        raise _error("Agy task has no store-missing page")
    task_root = artifact_root / task["artifact_relative_path"]
    semantic_pages = [
        page
        for page in failed_pages
        if any(task_root.glob(f"**/page-{page:05d}/**/semantic-validation-failure.json"))
    ]
    return {
        "failed_pages": failed_pages,
        "format_version": "GEMINI_JSON_FIRST_SOURCE_BOUND_STORE_FRONTIER_V1",
        "semantic_failure_artifact_pages": semantic_pages,
        "source_logical_name": task["relative_path"],
        "source_sha256": task["source_sha256"],
        "stored_pages": stored_pages,
    }


def _superseded_source_identities_v1(registry_path: Path) -> dict[str, str]:
    """Load the exact old-source identities that must never reach a provider."""

    registry = _json_file(registry_path)
    policy = registry.get("policy")
    revisions = registry.get("revisions")
    if (
        registry.get("format_version") != "GEMINI_JSON_FIRST_SOURCE_REVISION_REGISTRY_V1"
        or type(policy) is not dict
        or policy.get("replacement_json_must_use_replacement_source_identity") is not True
        or type(revisions) is not list
        or not revisions
    ):
        raise _error("Agy source-revision registry is invalid")
    superseded: dict[str, str] = {}
    identity_fields = {"page_count", "relative_path", "sha256", "size_bytes"}
    for revision in revisions:
        original = revision.get("original") if type(revision) is dict else None
        replacement = revision.get("replacement") if type(revision) is dict else None
        if (
            type(original) is not dict
            or set(original) != identity_fields
            or type(replacement) is not dict
            or set(replacement) != identity_fields
            or any(
                type(identity.get("relative_path")) is not str
                or not identity["relative_path"]
                or type(identity.get("sha256")) is not str
                or len(identity["sha256"]) != 64
                or any(character not in "0123456789abcdef" for character in identity["sha256"])
                or type(identity.get("page_count")) is not int
                or identity["page_count"] <= 0
                or type(identity.get("size_bytes")) is not int
                or identity["size_bytes"] <= 0
                for identity in (original, replacement)
            )
            or original["relative_path"] == replacement["relative_path"]
            or original["sha256"] == replacement["sha256"]
        ):
            raise _error("Agy source-revision identity is invalid")
        previous = superseded.setdefault(original["relative_path"], original["sha256"])
        if previous != original["sha256"]:
            raise _error("Agy source-revision registry contains a conflicting original")
    return superseded


def _assert_not_superseded_source_v1(
    task: dict[str, Any], *, superseded_sources: dict[str, str]
) -> None:
    expected_sha = superseded_sources.get(task["relative_path"])
    if expected_sha is None:
        return
    if expected_sha != task["source_sha256"]:
        raise _error("Agy source-revision task identity drifted")
    raise _error("Agy refused a superseded source identity")


def _orientation_repairs_v1(registry_path: Path) -> dict[tuple[str, str, int], dict[str, Any]]:
    """Load explicit human-verified rotations; implicit orientation guesses are forbidden."""

    registry = _json_file(registry_path)
    policy = registry.get("policy")
    repairs = registry.get("repairs")
    if (
        registry.get("format_version") != "GEMINI_JSON_FIRST_AGY_ORIENTATION_REPAIR_REGISTRY_V1"
        or policy
        != {
            "exact_source_page_only": True,
            "implicit_orientation_detection": False,
        }
        or type(repairs) is not list
        or not repairs
    ):
        raise _error("Agy orientation-repair registry is invalid")
    required = {
        "clockwise_degrees",
        "corrected_image_sha256",
        "original_image_sha256",
        "physical_page",
        "reason",
        "source_logical_name",
        "source_sha256",
    }
    result: dict[tuple[str, str, int], dict[str, Any]] = {}
    for raw in repairs:
        if (
            type(raw) is not dict
            or set(raw) != required
            or type(raw["source_logical_name"]) is not str
            or not raw["source_logical_name"]
            or type(raw["source_sha256"]) is not str
            or len(raw["source_sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in raw["source_sha256"])
            or type(raw["physical_page"]) is not int
            or raw["physical_page"] <= 0
            or raw["clockwise_degrees"] not in {90, 270}
            or type(raw["reason"]) is not str
            or not raw["reason"]
            or any(
                type(raw[field]) is not str
                or len(raw[field]) != 64
                or any(character not in "0123456789abcdef" for character in raw[field])
                for field in ("original_image_sha256", "corrected_image_sha256")
            )
            or raw["original_image_sha256"] == raw["corrected_image_sha256"]
        ):
            raise _error("Agy orientation-repair registry entry is invalid")
        key = (raw["source_logical_name"], raw["source_sha256"], raw["physical_page"])
        if key in result:
            raise _error("Agy orientation-repair registry contains a duplicate page")
        result[key] = dict(raw)
    return result


def _schema_alignment_repairs_v1(
    registry_path: Path,
) -> dict[tuple[str, str, int], dict[str, Any]]:
    """Load explicit page-specific alignment hints; generic retries are forbidden."""

    registry = _json_file(registry_path)
    policy = registry.get("policy")
    repairs = registry.get("repairs")
    if (
        registry.get("format_version")
        != "GEMINI_JSON_FIRST_AGY_SCHEMA_ALIGNMENT_REPAIR_REGISTRY_V1"
        or policy
        != {
            "exact_source_page_only": True,
            "implicit_alignment_hints": False,
            "tools_forbidden": True,
        }
        or type(repairs) is not list
        or not repairs
    ):
        raise _error("Agy schema-alignment repair registry is invalid")
    required = {
        "image_sha256",
        "physical_page",
        "reason",
        "repair_instruction",
        "source_logical_name",
        "source_sha256",
    }
    result: dict[tuple[str, str, int], dict[str, Any]] = {}
    for raw in repairs:
        if (
            type(raw) is not dict
            or set(raw) != required
            or type(raw["source_logical_name"]) is not str
            or not raw["source_logical_name"]
            or type(raw["source_sha256"]) is not str
            or len(raw["source_sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in raw["source_sha256"])
            or type(raw["image_sha256"]) is not str
            or len(raw["image_sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in raw["image_sha256"])
            or type(raw["physical_page"]) is not int
            or raw["physical_page"] <= 0
            or type(raw["reason"]) is not str
            or not raw["reason"]
            or type(raw["repair_instruction"]) is not str
            or not raw["repair_instruction"].strip()
        ):
            raise _error("Agy schema-alignment repair registry entry is invalid")
        key = (raw["source_logical_name"], raw["source_sha256"], raw["physical_page"])
        if key in result:
            raise _error("Agy schema-alignment repair registry contains a duplicate page")
        result[key] = dict(raw)
    return result


def _rotate_rendered_page_v1(
    rendered: _RenderedPage,
    *,
    source_sha256: str,
    physical_page: int,
    clockwise_degrees: int,
) -> _RenderedPage:
    """Rotate an already complete page raster without authorizing arbitrary commands."""

    transpose = {
        90: Image.Transpose.ROTATE_270,
        270: Image.Transpose.ROTATE_90,
    }.get(clockwise_degrees)
    if transpose is None:
        raise _error("Agy orientation repair rotation is invalid")
    try:
        with Image.open(BytesIO(rendered.image)) as source_image:
            rotated_image = source_image.convert("RGB").transpose(transpose)
            output = BytesIO()
            rotated_image.save(output, format="PNG", compress_level=6)
            image = output.getvalue()
            width, height = rotated_image.size
    except (OSError, ValueError) as exc:
        raise _error("Agy orientation repair could not rotate the page raster") from exc
    image_sha256 = sha256(image).hexdigest()
    base_receipt_sha256 = canonical_json_sha256_v1(rendered.receipt)
    page = {
        **rendered.page,
        "image_sha256": image_sha256,
        "image_size_bytes": len(image),
        "pixel_height": height,
        "pixel_width": width,
    }
    receipt = {
        "base_image_sha256": rendered.page["image_sha256"],
        "base_render_receipt_sha256": base_receipt_sha256,
        "clockwise_degrees": clockwise_degrees,
        "format_version": "GEMINI_JSON_FIRST_AGY_ORIENTATION_REPAIRED_RENDER_V1",
        "image": {
            "height": height,
            "media_type": "image/png",
            "sha256": image_sha256,
            "size_bytes": len(image),
            "width": width,
        },
        "physical_page": physical_page,
        "source_sha256": source_sha256,
    }
    return _RenderedPage(image=image, page=page, receipt=receipt)


def _failure_evidence_sha256s_v1(
    *,
    task: dict[str, Any],
    artifact_root: Path,
    physical_page: int,
) -> list[str]:
    """Bind one B-queue page to immutable prior receipts and page failures."""

    prior = task.get("last_receipt_json")
    if type(prior) is not bytes:
        raise _error("Agy unaccepted-page task has no immutable prior receipt")
    root = artifact_root.resolve()
    task_root = (root / task["artifact_relative_path"]).resolve()
    try:
        task_root.relative_to(root)
    except ValueError as exc:
        raise _error("Agy unaccepted-page artifact path escapes its root") from exc
    candidates = list(
        (task_root / "openrouter-exhausted-page-repair" / "receipts").glob("attempt-*.json")
    )
    candidates.extend(
        task_root.glob(f"**/page-{physical_page:05d}/**/semantic-validation-failure.json")
    )
    candidates.extend(task_root.glob(f"**/page-{physical_page:05d}/**/render-failure.json"))
    candidates.extend(task_root.glob(f"**/page-{physical_page:05d}/**/failure.json"))
    digests = {sha256(prior).hexdigest()}
    for candidate in sorted(set(candidates)):
        if candidate.is_symlink() or not candidate.is_file():
            raise _error("Agy unaccepted-page failure evidence is not a regular file")
        digests.add(sha256(candidate.read_bytes()).hexdigest())
    return sorted(digests)


def _tool_denied_rotation_evidence_v1(
    *,
    task: dict[str, Any],
    artifact_root: Path,
    physical_pages: list[int],
    original_image_sha256s: dict[int, str],
) -> list[dict[str, Any]]:
    """Authenticate the exact three Agy calls that tried to rotate via a command."""

    root = artifact_root.resolve()
    task_root = (root / task["artifact_relative_path"]).resolve()
    try:
        task_root.relative_to(root)
    except ValueError as exc:
        raise _error("Agy tool-denial artifact path escapes its root") from exc
    evidence = []
    for page in physical_pages:
        for effort in EFFORT_ORDER:
            effort_root = (
                task_root
                / "agy-exhausted-unaccepted-repair"
                / f"page-{page:05d}"
                / f"effort-{effort}"
            )
            paths = {
                "failure": effort_root / "failure.json",
                "invocation": effort_root / "invocation.json",
                "response": effort_root / "agy-response.json",
                "stderr": effort_root / "agy-stderr.log",
            }
            if any(path.is_symlink() or not path.is_file() for path in paths.values()):
                raise _error("Agy orientation recovery tool-denial evidence is absent")
            raw = {name: path.read_bytes() for name, path in paths.items()}
            try:
                failure = json.loads(raw["failure"])
                invocation = json.loads(raw["invocation"])
                response = json.loads(raw["response"])
                stderr = raw["stderr"].decode("utf-8")
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise _error("Agy orientation recovery tool-denial evidence is invalid") from exc
            if (
                type(failure) is not dict
                or failure.get("failure_kind") != "AGY_PROVIDER_OR_SCHEMA_FAILED"
                or failure.get("error_message")
                != "Agy successful envelope lacks structured output or usage"
                or type(invocation) is not dict
                or invocation.get("format_version") != FORMAT_VERSION
                or invocation.get("effort") != effort
                or invocation.get("model") != AGY_MODEL_BY_EFFORT[effort]
                or invocation.get("image_sha256") != original_image_sha256s.get(page)
                or type(response) is not dict
                or response.get("status") != "SUCCESS"
                or response.get("response") != ""
                or response.get("structured_output") is not None
                or response.get("denied_actions")
                != [{"action": "command", "display_name": "RunCommand"}]
                or "headless mode cannot prompt" not in stderr
                or "auto-denied" not in stderr
            ):
                raise _error("Agy orientation recovery is not an exact command-tool denial")
            evidence.append(
                {
                    "effort": effort,
                    "failure_sha256": sha256(raw["failure"]).hexdigest(),
                    "invocation_sha256": sha256(raw["invocation"]).hexdigest(),
                    "physical_page": page,
                    "response_sha256": sha256(raw["response"]).hexdigest(),
                    "stderr_sha256": sha256(raw["stderr"]).hexdigest(),
                }
            )
    return evidence


def _schema_alignment_attempt_evidence_v1(
    *,
    task: dict[str, Any],
    artifact_root: Path,
    physical_page: int,
    image_sha256: str,
) -> list[dict[str, Any]]:
    """Authenticate one alignment failure followed by two exact tool denials."""

    root = artifact_root.resolve()
    task_root = (root / task["artifact_relative_path"]).resolve()
    try:
        task_root.relative_to(root)
    except ValueError as exc:
        raise _error("Agy schema-alignment artifact path escapes its root") from exc
    evidence = []
    for effort in EFFORT_ORDER:
        effort_root = (
            task_root
            / "agy-exhausted-unaccepted-repair"
            / f"page-{physical_page:05d}"
            / f"effort-{effort}"
        )
        paths = {
            "failure": effort_root / "failure.json",
            "invocation": effort_root / "invocation.json",
            "response": effort_root / "agy-response.json",
            "stderr": effort_root / "agy-stderr.log",
        }
        if any(path.is_symlink() or not path.is_file() for path in paths.values()):
            raise _error("Agy schema-alignment prior-attempt evidence is absent")
        raw = {name: path.read_bytes() for name, path in paths.items()}
        try:
            failure = json.loads(raw["failure"])
            invocation = json.loads(raw["invocation"])
            response = json.loads(raw["response"])
            stderr = raw["stderr"].decode("utf-8")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise _error("Agy schema-alignment prior-attempt evidence is invalid") from exc
        common_valid = bool(
            type(failure) is dict
            and failure.get("failure_kind") == "AGY_PROVIDER_OR_SCHEMA_FAILED"
            and type(invocation) is dict
            and invocation.get("format_version") == FORMAT_VERSION
            and invocation.get("effort") == effort
            and invocation.get("model") == AGY_MODEL_BY_EFFORT[effort]
            and invocation.get("image_sha256") == image_sha256
            and type(response) is dict
        )
        if effort == "low":
            valid = bool(
                common_valid
                and failure.get("error_message")
                == "row values do not align with table value columns"
                and response.get("status") == "SUCCESS"
                and type(response.get("response")) is str
                and bool(response["response"])
                and type(response.get("structured_output")) is dict
            )
            failure_kind = "ROW_COLUMN_ALIGNMENT"
        elif effort == "medium":
            valid = bool(
                common_valid
                and failure.get("error_message")
                == "Agy successful envelope lacks structured output or usage"
                and response.get("status") == "SUCCESS"
                and response.get("response") == ""
                and response.get("structured_output") is None
                and "headless mode cannot prompt" in stderr
                and "auto-denied" in stderr
            )
            failure_kind = "COMMAND_TOOL_DENIED"
        else:
            valid = bool(
                common_valid
                and failure.get("error_message") == "Agy did not return a successful envelope"
                and response.get("status") == "CANCELED"
                and response.get("response") == ""
                and response.get("structured_output") is None
                and "headless mode cannot prompt" in stderr
                and "auto-denied" in stderr
            )
            failure_kind = "COMMAND_TOOL_DENIED"
        if not valid:
            raise _error("Agy schema-alignment prior-attempt evidence is not exact")
        evidence.append(
            {
                "effort": effort,
                "failure_kind": failure_kind,
                "failure_sha256": sha256(raw["failure"]).hexdigest(),
                "invocation_sha256": sha256(raw["invocation"]).hexdigest(),
                "physical_page": physical_page,
                "response_sha256": sha256(raw["response"]).hexdigest(),
                "stderr_sha256": sha256(raw["stderr"]).hexdigest(),
            }
        )
    return evidence


def _bounded_flex_exhaustion_evidence_v1(
    *,
    task: dict[str, Any],
    artifact_root: Path,
    prior_receipt_bytes: bytes | None = None,
) -> list[dict[str, Any]]:
    """Authenticate both completed Flex page-repair attempts for queue B."""

    prior = (
        prior_receipt_bytes if prior_receipt_bytes is not None else task.get("last_receipt_json")
    )
    if type(prior) is not bytes:
        raise _error("Agy unaccepted-page task has no immutable prior receipt")
    root = artifact_root.resolve()
    task_root = (root / task["artifact_relative_path"]).resolve()
    try:
        task_root.relative_to(root)
    except ValueError as exc:
        raise _error("Agy unaccepted-page artifact path escapes its root") from exc
    receipts_root = task_root / "openrouter-exhausted-page-repair" / "receipts"
    if receipts_root.is_symlink() or not receipts_root.is_dir():
        raise _error("Agy unaccepted-page task has not exhausted bounded Flex repair")
    paths = sorted(receipts_root.glob("attempt-*.json"))
    path_names = [path.name for path in paths]
    if path_names not in (["attempt-01.json"], ["attempt-01.json", "attempt-02.json"]):
        raise _error("Agy unaccepted-page bounded Flex history is incomplete")
    prior_sha = sha256(prior).hexdigest()
    evidence = []
    for repair_attempt, path in enumerate(paths, 1):
        if path.is_symlink() or not path.is_file():
            raise _error("Agy unaccepted-page Flex receipt is not a regular file")
        raw = path.read_bytes()
        try:
            receipt = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise _error("Agy unaccepted-page Flex receipt is invalid") from exc
        failed_pages = receipt.get("failed_pages") if type(receipt) is dict else None
        if (
            type(receipt) is not dict
            or raw != canonical_json_bytes_v1(receipt)
            or receipt.get("format_version")
            not in {
                "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V1",
                "GEMINI_JSON_FIRST_OPENROUTER_EXHAUSTED_PAGE_REPAIR_V2",
            }
            or receipt.get("disposition") != "NEEDS_REPAIR"
            or receipt.get("repair_attempt") != repair_attempt
            or receipt.get("prior_failed_receipt_sha256") != prior_sha
            or type(failed_pages) is not list
            or not failed_pages
            or failed_pages != sorted(set(failed_pages))
        ):
            raise _error("Agy unaccepted-page Flex receipt binding is invalid")
        evidence.append(
            {
                "disposition": receipt["disposition"],
                "failed_pages": failed_pages,
                "format_version": receipt["format_version"],
                "prior_failed_receipt_sha256": receipt["prior_failed_receipt_sha256"],
                "receipt_sha256": sha256(raw).hexdigest(),
                "repair_attempt": repair_attempt,
            }
        )
    if len(evidence) == 1:
        receipt = json.loads(paths[0].read_bytes())
        semantic_pages = receipt.get("semantic_failed_pages")
        provider_results = receipt.get("provider_results")
        balanced_semantic_pages: set[int] = set()
        if type(provider_results) is list:
            for item in provider_results:
                if type(item) is not dict or item.get("prompt_variant") != "balanced":
                    continue
                physical_pages = item.get("physical_pages")
                result = item.get("result")
                result_semantic = (
                    result.get("semantic_failed_pages") if type(result) is dict else None
                )
                if (
                    type(physical_pages) is not list
                    or not physical_pages
                    or physical_pages != sorted(set(physical_pages))
                    or type(result_semantic) is not list
                    or result_semantic != sorted(set(result_semantic))
                    or not set(result_semantic).issubset(physical_pages)
                ):
                    raise _error("Agy unaccepted-page balanced Flex history is invalid")
                balanced_semantic_pages.update(result_semantic)
        if (
            type(semantic_pages) is not list
            or not semantic_pages
            or semantic_pages != sorted(set(semantic_pages))
            or not set(semantic_pages).issubset(evidence[0]["failed_pages"])
            or not balanced_semantic_pages
            or not balanced_semantic_pages.issubset(semantic_pages)
        ):
            raise _error("Agy unaccepted-page bounded Flex history is incomplete")
        evidence[0].update(
            {
                "balanced_semantic_failed_pages": sorted(balanced_semantic_pages),
                "exhaustion_kind": "BALANCED_SEMANTIC_RETRY_BLOCKS_SECOND_ATTEMPT",
            }
        )
    elif not set(evidence[1]["failed_pages"]).issubset(evidence[0]["failed_pages"]):
        raise _error("Agy unaccepted-page Flex failure frontier expanded")
    return evidence


def _cross_corpus_flex_history_evidence_v1(
    *,
    task: dict[str, Any],
    current_ledger: Path,
    historical_ledger: Path,
    artifact_root: Path,
    missing_pages: list[int],
    current_image_sha256s: dict[int, str],
) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    """Authenticate Flex exhaustion written under an earlier corpus ledger.

    Task IDs are source-derived and can legitimately survive a corpus-plan
    narrowing.  This bridge is only for that exact situation: the two ledgers
    must have different run identities but the task source and page bounds must
    match byte-for-byte.  Both historical Flex receipts must prove actual
    provider requests for only the current store-missing frontier.
    """

    for label, path in (("current", current_ledger), ("historical", historical_ledger)):
        if path.is_symlink() or not path.is_file():
            raise _error(f"Agy cross-corpus {label} ledger is absent or not regular")
    historical_bytes = historical_ledger.read_bytes()
    historical_ledger_sha256 = sha256(historical_bytes).hexdigest()
    identities = []
    rows = []
    for path in (current_ledger, historical_ledger):
        with sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            identity = connection.execute("SELECT * FROM run_identity WHERE singleton=1").fetchone()
            row = connection.execute(
                "SELECT * FROM task WHERE task_id=?", (task["task_id"],)
            ).fetchone()
            if identity is None or row is None:
                raise _error("Agy cross-corpus ledger identity is incomplete")
            identities.append(dict(identity))
            rows.append(dict(row))
    current_identity, historical_identity = identities
    current_row, historical_row = rows
    identity_fields = {
        "artifact_relative_path",
        "document_page_count",
        "first_physical_page",
        "last_physical_page",
        "relative_path",
        "route",
        "source_sha256",
        "source_size_bytes",
        "task_id",
        "task_kind",
    }
    if (
        current_identity["corpus_run_id"] == historical_identity["corpus_run_id"]
        or current_identity["corpus_plan_id"] == historical_identity["corpus_plan_id"]
        or any(current_row[field] != historical_row[field] for field in identity_fields)
        or any(current_row[field] != task[field] for field in identity_fields)
        or historical_row["state"] != "FAILED"
        or historical_row["attempt_count"] != historical_identity["max_task_attempts"]
    ):
        raise _error("Agy cross-corpus task identity is invalid")
    historical_prior = historical_row.get("last_receipt_json")
    if type(historical_prior) is not bytes:
        raise _error("Agy cross-corpus historical receipt is absent")
    try:
        prior = json.loads(historical_prior)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _error("Agy cross-corpus historical receipt is invalid") from exc
    with sqlite3.connect(f"file:{historical_ledger.resolve()}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        event = connection.execute(
            "SELECT * FROM task_event WHERE task_id=? ORDER BY event_ordinal DESC LIMIT 1",
            (task["task_id"],),
        ).fetchone()
    historical_failed = prior.get("failed_pages") if type(prior) is dict else None
    provider_child = prior.get("provider_child") if type(prior) is dict else None
    provider_result = provider_child.get("result") if type(provider_child) is dict else None
    provider_failed = provider_result.get("failed_pages") if type(provider_result) is dict else None
    prior_failure_partitions = [
        prior.get(field) if type(prior) is dict else None
        for field in (
            "recitation_failed_pages",
            "semantic_failed_pages",
            "source_failed_pages",
            "unresolved_pages",
        )
    ]
    prior_failure_partitions = [
        [] if partition is None else partition for partition in prior_failure_partitions
    ]
    image_items = (
        provider_result.get("page_image_sha256s") if type(provider_result) is dict else None
    )
    image_by_page = (
        {
            item.get("physical_page"): item.get("image_sha256")
            for item in image_items
            if type(item) is dict
        }
        if type(image_items) is list
        else {}
    )
    if (
        type(prior) is not dict
        or historical_prior != canonical_json_bytes_v1(prior)
        or prior.get("format_version")
        != "GEMINI_JSON_FIRST_INTERRUPTED_OPENROUTER_RETRY_RECOVERY_V1"
        or type(historical_failed) is not list
        or historical_failed != sorted(set(historical_failed))
        or not set(missing_pages).issubset(historical_failed)
        or event is None
        or event["next_state"] != "FAILED"
        or event["receipt_json"] != historical_prior
        or type(provider_result) is not dict
        or type(provider_failed) is not list
        or provider_failed != sorted(set(provider_failed))
        or not set(missing_pages).issubset(provider_failed)
        or any(image_by_page.get(page) != current_image_sha256s.get(page) for page in missing_pages)
        or any(
            type(partition) is not list or partition != sorted(set(partition))
            for partition in prior_failure_partitions
        )
        or any(set(partition) & set(missing_pages) for partition in prior_failure_partitions)
    ):
        raise _error("Agy cross-corpus historical failure frontier is invalid")
    exhaustion = _bounded_flex_exhaustion_evidence_v1(
        task=task,
        artifact_root=artifact_root,
        prior_receipt_bytes=historical_prior,
    )
    if len(exhaustion) != 2 or not set(missing_pages).issubset(exhaustion[-1]["failed_pages"]):
        raise _error("Agy cross-corpus Flex exhaustion is incomplete")
    receipts_root = (
        artifact_root.resolve()
        / task["artifact_relative_path"]
        / "openrouter-exhausted-page-repair"
        / "receipts"
    )
    for attempt in (1, 2):
        receipt = json.loads((receipts_root / f"attempt-{attempt:02d}.json").read_bytes())
        provider_results = receipt.get("provider_results")
        current_results = (
            [
                item
                for item in provider_results
                if type(item) is dict and item.get("repair_attempt") == attempt
            ]
            if type(provider_results) is list
            else []
        )
        if len(current_results) != 1:
            raise _error("Agy cross-corpus Flex provider history is ambiguous")
        item = current_results[0]
        result = item.get("result")
        result_images = (
            {
                image.get("physical_page"): image.get("image_sha256")
                for image in result.get("page_image_sha256s", [])
                if type(image) is dict
            }
            if type(result) is dict
            else {}
        )
        if (
            item.get("physical_pages") != missing_pages
            or item.get("accepted_pages") != []
            or type(result) is not dict
            or result.get("execution_mode") != "PROVIDER_OR_CACHE"
            or result.get("physical_pages") != missing_pages
            or result.get("provider_request_pages") != missing_pages
            or result.get("failed_pages") != missing_pages
            or result.get("ingested_pages") != []
            or result.get("cached_pages") != []
            or result.get("recitation_failed_pages") != []
            or result.get("semantic_failed_pages") != []
            or result.get("unresolved_pages") != []
            or result_images != current_image_sha256s
        ):
            raise _error("Agy cross-corpus Flex provider request evidence is invalid")
    historical_prior_sha256 = sha256(historical_prior).hexdigest()
    history = {
        "current_corpus_plan_id": current_identity["corpus_plan_id"],
        "current_corpus_run_id": current_identity["corpus_run_id"],
        "format_version": "GEMINI_JSON_FIRST_AGY_CROSS_CORPUS_FLEX_HISTORY_V1",
        "historical_corpus_plan_id": historical_identity["corpus_plan_id"],
        "historical_corpus_run_id": historical_identity["corpus_run_id"],
        "historical_ledger_sha256": historical_ledger_sha256,
        "historical_prior_failed_receipt_sha256": historical_prior_sha256,
        "historical_task_event_ordinal": event["event_ordinal"],
        "historical_task_identity_sha256": canonical_json_sha256_v1(
            {field: historical_row[field] for field in sorted(identity_fields)}
        ),
    }
    if sha256(historical_ledger.read_bytes()).hexdigest() != historical_ledger_sha256:
        raise _error("Agy cross-corpus historical ledger changed during authentication")
    return exhaustion, history, historical_prior_sha256


def _claim_unaccepted_task_with_execution_lock_v1(
    *,
    ledger: Path,
    source_root: Path,
    database: Path,
    artifact_root: Path,
    source_revision_registry: Path,
    historical_ledger: Path | None = None,
    dpi: int,
    task_id: str | None,
) -> tuple[dict[str, Any], Any]:
    """Preflight and atomically lease one exhausted no-JSON frontier."""

    superseded_sources = _superseded_source_identities_v1(source_revision_registry)
    tasks = list_corpus_tasks_v1(ledger, states=["FAILED"])
    if task_id is not None:
        tasks = [task for task in tasks if task["task_id"] == task_id]
        if len(tasks) != 1:
            raise _error("Agy unaccepted-page task ID is absent or not failed")
    else:
        tasks.sort(key=lambda task: (task["relative_path"], task["task_id"]))
    last_error: Exception | None = None
    for candidate in tasks:
        try:
            task_lock = acquire_corpus_task_execution_lock_v1(
                ledger,
                task_id=candidate["task_id"],
            )
        except GeminiJsonFirstCorpusLedgerV1Error as exc:
            last_error = exc
            continue
        try:
            _assert_not_superseded_source_v1(
                candidate,
                superseded_sources=superseded_sources,
            )
            source = _source(candidate, source_root)
            store_frontier = _source_bound_store_frontier_v1(
                task=candidate,
                database=database,
                artifact_root=artifact_root,
            )
            try:
                authenticated = openrouter_failed_task_repair_frontier_v1(
                    ledger,
                    task_id=candidate["task_id"],
                )
            except GeminiJsonFirstCorpusLedgerV1Error:
                if not _is_strict_legacy_subprocess_failure_v1(candidate):
                    raise
                authenticated = {
                    "failed_pages": store_frontier["failed_pages"],
                    "recitation_failed_pages": [],
                    "semantic_failed_pages": store_frontier["semantic_failure_artifact_pages"],
                    "unresolved_pages": [],
                }
            missing_pages = store_frontier["failed_pages"]
            if not set(missing_pages).issubset(authenticated["failed_pages"]):
                raise _error("Agy unaccepted pages exceed the authenticated failure frontier")
            if set(missing_pages) & set(authenticated.get("recitation_failed_pages", [])):
                raise _error("Agy unaccepted pages contain a recitation failure")
            try:
                prior = json.loads(candidate["last_receipt_json"])
            except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise _error("Agy unaccepted-page prior receipt is invalid") from exc
            source_failed = prior.get("source_failed_pages", []) if type(prior) is dict else []
            if type(source_failed) is not list or set(source_failed) & set(missing_pages):
                raise _error("Agy unaccepted pages contain a source/render failure")
            rendered_by_page = {
                page: _render_page(
                    source,
                    physical_page=page,
                    dpi=dpi,
                    source_sha256=candidate["source_sha256"],
                )
                for page in missing_pages
            }
            cross_corpus_history = None
            historical_prior_sha256 = None
            if historical_ledger is None:
                exhaustion_evidence = _bounded_flex_exhaustion_evidence_v1(
                    task=candidate,
                    artifact_root=artifact_root,
                )
            else:
                (
                    exhaustion_evidence,
                    cross_corpus_history,
                    historical_prior_sha256,
                ) = _cross_corpus_flex_history_evidence_v1(
                    task=candidate,
                    current_ledger=ledger,
                    historical_ledger=historical_ledger,
                    artifact_root=artifact_root,
                    missing_pages=missing_pages,
                    current_image_sha256s={
                        page: rendered_by_page[page].page["image_sha256"] for page in missing_pages
                    },
                )
            if not set(missing_pages).issubset(exhaustion_evidence[-1]["failed_pages"]):
                raise _error("Agy unaccepted pages exceed bounded Flex exhaustion")
            semantic_pages = (
                set(authenticated.get("semantic_failed_pages", []))
                | set(authenticated.get("unresolved_pages", []))
                | set(store_frontier["semantic_failure_artifact_pages"])
            )
            page_evidence = []
            for page in missing_pages:
                rendered = rendered_by_page[page]
                failure_digests = _failure_evidence_sha256s_v1(
                    task=candidate,
                    artifact_root=artifact_root,
                    physical_page=page,
                )
                if historical_prior_sha256 is not None:
                    failure_digests = sorted(set(failure_digests) | {historical_prior_sha256})
                page_evidence.append(
                    {
                        "failure_evidence_sha256s": failure_digests,
                        "failure_kind": (
                            "SEMANTIC_NO_ACCEPTED_JSON"
                            if page in semantic_pages
                            else "PROVIDER_NO_ACCEPTED_JSON"
                        ),
                        "image_sha256": rendered.page["image_sha256"],
                        "physical_page": page,
                    }
                )
            claimed = claim_exhausted_openrouter_unaccepted_pages_for_agy_v1(
                ledger,
                task_id=candidate["task_id"],
                source_bound_store_frontier=store_frontier,
                exhaustion_evidence=exhaustion_evidence,
                page_evidence=page_evidence,
                cross_corpus_history_evidence=cross_corpus_history,
            )
            return claimed, task_lock
        except (
            GeminiJsonFirstCorpusLedgerV1Error,
            GeminiJsonFirstPageRenderV1Error,
            RunGeminiJsonFirstAgyDocumentV1Error,
        ) as exc:
            task_lock.close()
            last_error = exc
            if task_id is not None:
                raise _error(str(exc)) from exc
    message = "no authenticated exhausted no-JSON task is available for Agy"
    if task_id is not None and last_error is not None:
        message += ": " + str(last_error)
    raise _error(message)


def _claim_source_render_recovery_with_execution_lock_v1(
    *,
    ledger: Path,
    source_root: Path,
    database: Path,
    artifact_root: Path,
    source_revision_registry: Path,
    dpi: int,
    task_id: str | None,
) -> tuple[dict[str, Any], Any]:
    """Render-check and lease one exact prior source/render failure frontier."""

    superseded_sources = _superseded_source_identities_v1(source_revision_registry)
    tasks = list_corpus_tasks_v1(ledger, states=["FAILED"])
    if task_id is not None:
        tasks = [task for task in tasks if task["task_id"] == task_id]
        if len(tasks) != 1:
            raise _error("Agy source-render recovery task ID is absent or not failed")
    else:
        tasks.sort(key=lambda task: (task["relative_path"], task["task_id"]))
    renderer_path = ROOT / "src/bctc_ai/evaluation/gemini_json_first_page_render_v1.py"
    if renderer_path.is_symlink() or not renderer_path.is_file():
        raise _error("Agy source-render recovery renderer source is absent")
    renderer_source_sha256 = sha256(renderer_path.read_bytes()).hexdigest()
    last_error: Exception | None = None
    for candidate in tasks:
        try:
            task_lock = acquire_corpus_task_execution_lock_v1(
                ledger,
                task_id=candidate["task_id"],
            )
        except GeminiJsonFirstCorpusLedgerV1Error as exc:
            last_error = exc
            continue
        try:
            _assert_not_superseded_source_v1(
                candidate,
                superseded_sources=superseded_sources,
            )
            try:
                prior = json.loads(candidate["last_receipt_json"])
            except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise _error("Agy source-render recovery prior receipt is invalid") from exc
            source_failed = prior.get("source_failed_pages") if type(prior) is dict else None
            if (
                type(prior) is not dict
                or prior.get("disposition") != "AGY_TERMINAL_PROVIDER_REPAIR_FAILED"
                or type(source_failed) is not list
                or not source_failed
                or source_failed != sorted(set(source_failed))
            ):
                raise _error("Agy task has no authenticated source/render failure")
            source = _source(candidate, source_root)
            store_frontier = _source_bound_store_frontier_v1(
                task=candidate,
                database=database,
                artifact_root=artifact_root,
            )
            missing_pages = store_frontier["failed_pages"]
            if not set(source_failed).issubset(missing_pages):
                raise _error("Agy source-render failures exceed the current store frontier")
            recovery_root = (
                artifact_root
                / candidate["artifact_relative_path"]
                / "agy-source-render-recovery"
                / "preflight"
            )
            rendered_by_page: dict[int, _RenderedPage] = {}
            render_receipt_sha256s: dict[int, str] = {}
            for page in missing_pages:
                rendered = _render_page(
                    source,
                    physical_page=page,
                    dpi=dpi,
                    source_sha256=candidate["source_sha256"],
                )
                rendered_by_page[page] = rendered
                receipt_bytes = canonical_json_bytes_v1(rendered.receipt)
                receipt_path = recovery_root / f"page-{page:05d}" / "render-receipt.json"
                _write_or_verify(receipt_path, receipt_bytes)
                render_receipt_sha256s[page] = sha256(receipt_bytes).hexdigest()
            local_evidence = [
                {
                    "image_sha256": rendered_by_page[page].page["image_sha256"],
                    "physical_page": page,
                    "render_receipt_sha256": render_receipt_sha256s[page],
                }
                for page in source_failed
            ]
            page_evidence = []
            for page in missing_pages:
                digests = set(
                    _failure_evidence_sha256s_v1(
                        task=candidate,
                        artifact_root=artifact_root,
                        physical_page=page,
                    )
                )
                digests.add(render_receipt_sha256s[page])
                page_evidence.append(
                    {
                        "failure_evidence_sha256s": sorted(digests),
                        "failure_kind": (
                            "LOCAL_RENDER_REPAIRED"
                            if page in source_failed
                            else "PROVIDER_NO_ACCEPTED_JSON"
                        ),
                        "image_sha256": rendered_by_page[page].page["image_sha256"],
                        "physical_page": page,
                    }
                )
            claimed = claim_source_render_repaired_pages_for_agy_v1(
                ledger,
                task_id=candidate["task_id"],
                source_bound_store_frontier=store_frontier,
                local_render_repair_evidence=local_evidence,
                page_evidence=page_evidence,
                renderer_source_sha256=renderer_source_sha256,
            )
            return claimed, task_lock
        except (
            GeminiJsonFirstCorpusLedgerV1Error,
            GeminiJsonFirstPageRenderV1Error,
            RunGeminiJsonFirstAgyDocumentV1Error,
        ) as exc:
            task_lock.close()
            last_error = exc
            if task_id is not None:
                raise _error(str(exc)) from exc
    message = "no authenticated source-render recovery task is available for Agy"
    if task_id is not None and last_error is not None:
        message += ": " + str(last_error)
    raise _error(message)


def _claim_tool_denied_orientation_recovery_with_execution_lock_v1(
    *,
    ledger: Path,
    source_root: Path,
    database: Path,
    artifact_root: Path,
    source_revision_registry: Path,
    orientation_repair_registry: Path,
    dpi: int,
    task_id: str | None,
) -> tuple[dict[str, Any], Any]:
    """Rotate an explicitly registered sideways page and atomically lease it."""

    superseded_sources = _superseded_source_identities_v1(source_revision_registry)
    repairs = _orientation_repairs_v1(orientation_repair_registry)
    tasks = list_corpus_tasks_v1(ledger, states=["FAILED"])
    if task_id is not None:
        tasks = [task for task in tasks if task["task_id"] == task_id]
        if len(tasks) != 1:
            raise _error("Agy orientation recovery task ID is absent or not failed")
    else:
        tasks.sort(key=lambda task: (task["relative_path"], task["task_id"]))
    last_error: Exception | None = None
    for candidate in tasks:
        try:
            task_lock = acquire_corpus_task_execution_lock_v1(
                ledger,
                task_id=candidate["task_id"],
            )
        except GeminiJsonFirstCorpusLedgerV1Error as exc:
            last_error = exc
            continue
        try:
            _assert_not_superseded_source_v1(
                candidate,
                superseded_sources=superseded_sources,
            )
            try:
                prior = json.loads(candidate["last_receipt_json"])
            except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise _error("Agy orientation recovery prior receipt is invalid") from exc
            if (
                type(prior) is not dict
                or prior.get("format_version") != FORMAT_VERSION
                or prior.get("disposition") != "AGY_EXHAUSTED_UNACCEPTED_REPAIR_FAILED"
            ):
                raise _error("Agy task has no authenticated command-tool denial")
            source = _source(candidate, source_root)
            store_frontier = _source_bound_store_frontier_v1(
                task=candidate,
                database=database,
                artifact_root=artifact_root,
            )
            missing_pages = store_frontier["failed_pages"]
            entries = []
            for page in missing_pages:
                entry = repairs.get((candidate["relative_path"], candidate["source_sha256"], page))
                if entry is None:
                    raise _error("Agy missing page has no explicit orientation repair")
                entries.append(entry)
            recovery_root = (
                artifact_root
                / candidate["artifact_relative_path"]
                / "agy-tool-denied-orientation-recovery"
                / "preflight"
            )
            orientation_evidence = []
            original_image_sha256s: dict[int, str] = {}
            for entry in entries:
                page = entry["physical_page"]
                original = _render_page(
                    source,
                    physical_page=page,
                    dpi=dpi,
                    source_sha256=candidate["source_sha256"],
                )
                if original.page["image_sha256"] != entry["original_image_sha256"]:
                    raise _error("Agy orientation repair original image identity drifted")
                corrected = _rotate_rendered_page_v1(
                    original,
                    source_sha256=candidate["source_sha256"],
                    physical_page=page,
                    clockwise_degrees=entry["clockwise_degrees"],
                )
                if corrected.page["image_sha256"] != entry["corrected_image_sha256"]:
                    raise _error("Agy orientation repair corrected image identity drifted")
                receipt_bytes = canonical_json_bytes_v1(corrected.receipt)
                receipt_path = recovery_root / f"page-{page:05d}" / "orientation-receipt.json"
                _write_or_verify(receipt_path, receipt_bytes)
                original_image_sha256s[page] = original.page["image_sha256"]
                orientation_evidence.append(
                    {
                        "clockwise_degrees": entry["clockwise_degrees"],
                        "corrected_image_sha256": corrected.page["image_sha256"],
                        "orientation_receipt_sha256": sha256(receipt_bytes).hexdigest(),
                        "original_image_sha256": original.page["image_sha256"],
                        "physical_page": page,
                    }
                )
            denial_evidence = _tool_denied_rotation_evidence_v1(
                task=candidate,
                artifact_root=artifact_root,
                physical_pages=missing_pages,
                original_image_sha256s=original_image_sha256s,
            )
            claimed = claim_agy_tool_denied_orientation_repaired_pages_v1(
                ledger,
                task_id=candidate["task_id"],
                source_bound_store_frontier=store_frontier,
                orientation_repair_evidence=orientation_evidence,
                tool_denial_evidence=denial_evidence,
            )
            return claimed, task_lock
        except (
            GeminiJsonFirstCorpusLedgerV1Error,
            GeminiJsonFirstPageRenderV1Error,
            RunGeminiJsonFirstAgyDocumentV1Error,
        ) as exc:
            task_lock.close()
            last_error = exc
            if task_id is not None:
                raise _error(str(exc)) from exc
    message = "no authenticated tool-denied orientation task is available for Agy"
    if task_id is not None and last_error is not None:
        message += ": " + str(last_error)
    raise _error(message)


def _claim_schema_alignment_recovery_with_execution_lock_v1(
    *,
    ledger: Path,
    source_root: Path,
    database: Path,
    artifact_root: Path,
    source_revision_registry: Path,
    schema_alignment_repair_registry: Path,
    dpi: int,
    task_id: str | None,
) -> tuple[dict[str, Any], Any]:
    """Lease one registered alignment retry after authenticating all prior calls."""

    superseded_sources = _superseded_source_identities_v1(source_revision_registry)
    repairs = _schema_alignment_repairs_v1(schema_alignment_repair_registry)
    tasks = list_corpus_tasks_v1(ledger, states=["FAILED"])
    if task_id is not None:
        tasks = [task for task in tasks if task["task_id"] == task_id]
        if len(tasks) != 1:
            raise _error("Agy schema-alignment recovery task ID is absent or not failed")
    else:
        tasks.sort(key=lambda task: (task["relative_path"], task["task_id"]))
    last_error: Exception | None = None
    for candidate in tasks:
        try:
            task_lock = acquire_corpus_task_execution_lock_v1(
                ledger,
                task_id=candidate["task_id"],
            )
        except GeminiJsonFirstCorpusLedgerV1Error as exc:
            last_error = exc
            continue
        try:
            _assert_not_superseded_source_v1(candidate, superseded_sources=superseded_sources)
            try:
                prior = json.loads(candidate["last_receipt_json"])
            except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise _error("Agy schema-alignment prior receipt is invalid") from exc
            if (
                type(prior) is not dict
                or prior.get("format_version") != FORMAT_VERSION
                or prior.get("disposition") != "AGY_EXHAUSTED_UNACCEPTED_REPAIR_FAILED"
            ):
                raise _error("Agy task has no authenticated schema-alignment failure")
            store_frontier = _source_bound_store_frontier_v1(
                task=candidate,
                database=database,
                artifact_root=artifact_root,
            )
            missing_pages = store_frontier["failed_pages"]
            if len(missing_pages) != 1:
                raise _error("Agy schema-alignment recovery requires one missing page")
            page = missing_pages[0]
            entry = repairs.get((candidate["relative_path"], candidate["source_sha256"], page))
            if entry is None:
                raise _error("Agy missing page has no explicit schema-alignment repair")
            source = _source(candidate, source_root)
            rendered = _render_page(
                source,
                physical_page=page,
                dpi=dpi,
                source_sha256=candidate["source_sha256"],
            )
            if rendered.page["image_sha256"] != entry["image_sha256"]:
                raise _error("Agy schema-alignment repair image identity drifted")
            attempts = _schema_alignment_attempt_evidence_v1(
                task=candidate,
                artifact_root=artifact_root,
                physical_page=page,
                image_sha256=rendered.page["image_sha256"],
            )
            entry_sha256 = canonical_json_sha256_v1(entry)
            claimed = claim_agy_schema_alignment_recovery_pages_v1(
                ledger,
                task_id=candidate["task_id"],
                source_bound_store_frontier=store_frontier,
                page_evidence=[
                    {
                        "image_sha256": rendered.page["image_sha256"],
                        "physical_page": page,
                    }
                ],
                prior_attempt_evidence=attempts,
                repair_instruction_sha256=sha256(
                    entry["repair_instruction"].encode("utf-8")
                ).hexdigest(),
                repair_registry_entry_sha256=entry_sha256,
            )
            return claimed, task_lock
        except (
            GeminiJsonFirstCorpusLedgerV1Error,
            GeminiJsonFirstPageRenderV1Error,
            RunGeminiJsonFirstAgyDocumentV1Error,
        ) as exc:
            task_lock.close()
            last_error = exc
            if task_id is not None:
                raise _error(str(exc)) from exc
    message = "no authenticated schema-alignment task is available for Agy"
    if task_id is not None and last_error is not None:
        message += ": " + str(last_error)
    raise _error(message)


def _claim_terminal_task_with_execution_lock_v1(
    *,
    ledger: Path,
    source_root: Path,
    database: Path,
    artifact_root: Path,
    task_id: str | None,
) -> tuple[dict[str, Any], Any]:
    """Lock, source-check and atomically claim one disjoint repair task."""

    tasks = list_corpus_tasks_v1(ledger, states=["FAILED"])
    if task_id is not None:
        tasks = [task for task in tasks if task["task_id"] == task_id]
        if len(tasks) != 1:
            raise _error("Agy terminal-repair task ID is absent or not failed")
    else:
        tasks.sort(key=lambda task: (task["relative_path"], task["task_id"]), reverse=True)
    last_error: Exception | None = None
    for candidate in tasks:
        try:
            task_lock = acquire_corpus_task_execution_lock_v1(
                ledger,
                task_id=candidate["task_id"],
            )
        except GeminiJsonFirstCorpusLedgerV1Error as exc:
            last_error = exc
            continue
        try:
            _source(candidate, source_root)
            frontier = _source_bound_store_frontier_v1(
                task=candidate,
                database=database,
                artifact_root=artifact_root,
            )
            try:
                claimed = claim_failed_openrouter_provider_pages_for_agy_v1(
                    ledger,
                    task_id=candidate["task_id"],
                    source_bound_store_frontier=frontier,
                )
            except GeminiJsonFirstCorpusLedgerV1Error:
                if not _is_strict_legacy_subprocess_failure_v1(candidate):
                    raise
                claimed = claim_legacy_failed_openrouter_provider_pages_for_agy_v1(
                    ledger,
                    task_id=candidate["task_id"],
                    source_bound_store_frontier=frontier,
                )
            return claimed, task_lock
        except (GeminiJsonFirstCorpusLedgerV1Error, RunGeminiJsonFirstAgyDocumentV1Error) as exc:
            task_lock.close()
            last_error = exc
            if task_id is not None:
                raise _error(str(exc)) from exc
    message = "no authenticated provider-only failed task is available for Agy"
    if task_id is not None and last_error is not None:
        message += ": " + str(last_error)
    raise _error(message)


def _routes() -> list[dict[str, str]]:
    return [
        {"gateway": AGY_GATEWAY, "requested_service_tier": f"agy-{effort}"}
        for effort in EFFORT_ORDER
    ] + [
        {"gateway": CKEY_GATEWAY, "requested_service_tier": CKEY_SERVICE_TIER},
        {"gateway": "GOOGLE_GEMINI_API", "requested_service_tier": GOOGLE_STANDARD_SERVICE_TIER},
        {"gateway": "GOOGLE_GEMINI_BATCH_API", "requested_service_tier": GOOGLE_BATCH_SERVICE_TIER},
        {"gateway": "OPENROUTER", "requested_service_tier": OPENROUTER_SERVICE_TIER},
        {
            "gateway": "OPENROUTER",
            "requested_service_tier": OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER,
        },
    ]


def _preferred_routes() -> list[dict[str, str]]:
    allowed = _routes()
    keys = {(route["gateway"], route["requested_service_tier"]): route for route in allowed}
    order = [
        ("OPENROUTER", OPENROUTER_SERVICE_TIER),
        (AGY_GATEWAY, "agy-low"),
        (AGY_GATEWAY, "agy-medium"),
        (AGY_GATEWAY, "agy-high"),
        (CKEY_GATEWAY, CKEY_SERVICE_TIER),
        ("OPENROUTER", OPENROUTER_STANDARD_FALLBACK_SERVICE_TIER),
        ("GOOGLE_GEMINI_BATCH_API", GOOGLE_BATCH_SERVICE_TIER),
        ("GOOGLE_GEMINI_API", GOOGLE_STANDARD_SERVICE_TIER),
    ]
    return [keys[key] for key in order]


def _render_page(pdf: Path, *, physical_page: int, dpi: int, source_sha256: str) -> _RenderedPage:
    with fitz.open(pdf) as document:
        rendered = render_full_pdf_page_v1(
            document[physical_page - 1],
            physical_page=physical_page,
            dpi=dpi,
            source_sha256=source_sha256,
        )
    return _RenderedPage(rendered.image, rendered.page, rendered.receipt)


def _page_manifest(
    database: Path,
    *,
    task: dict[str, Any],
    rendered: _RenderedPage,
    prompt_sha256: str,
    response_schema_sha256: str,
) -> dict[str, Any] | None:
    try:
        return build_financial_document_manifest_v1(
            database,
            source_sha256=task["source_sha256"],
            source_logical_name=task["relative_path"],
            expected_physical_pages=[rendered.page["physical_page"]],
            page_image_sha256s={rendered.page["physical_page"]: rendered.page["image_sha256"]},
            prompt_sha256=prompt_sha256,
            response_schema_sha256=response_schema_sha256,
            requested_model=GOOGLE_MODEL,
            allowed_gateway_service_tiers=_routes(),
            preferred_gateway_service_tiers=_preferred_routes(),
        )
    except GeminiFinancialPageStoreV1Error as exc:
        if str(exc) in {
            "document manifest page frontier is incomplete",
            "document manifest source is not unique in the store",
        }:
            return None
        raise


def _reusable_page_manifest(
    database: Path,
    *,
    task: dict[str, Any],
    rendered: _RenderedPage,
    simple_prompt_sha256: str,
    response_schema_sha256: str,
    additional_prompt_sha256s: dict[str, str] | None = None,
) -> tuple[dict[str, Any], str] | None:
    """Find an authenticated page under any production prompt variant.

    Adaptive OpenRouter retries can legitimately store a usable page under
    ``items``, ``balanced``, ``scope`` or ``compact``.  Agy must reuse that
    page instead of paying for a second transcription merely because its own
    first-pass prompt is ``simple``.
    """

    prompt_sha256s = {
        variant: sha256(
            build_financial_page_json_prompt_v1(variant=variant).encode("utf-8")
        ).hexdigest()
        for variant in REUSABLE_PROMPT_VARIANTS
    }
    if prompt_sha256s["simple"] != simple_prompt_sha256:
        raise _error("Agy simple prompt identity drifted")
    additional = additional_prompt_sha256s or {}
    if set(additional) & set(prompt_sha256s) or any(
        type(variant) is not str
        or not variant
        or type(digest) is not str
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        for variant, digest in additional.items()
    ):
        raise _error("Agy additional prompt identity is invalid")
    prompt_sha256s.update(additional)
    for variant in (*REUSABLE_PROMPT_VARIANTS, *additional):
        manifest = _page_manifest(
            database,
            task=task,
            rendered=rendered,
            prompt_sha256=prompt_sha256s[variant],
            response_schema_sha256=response_schema_sha256,
        )
        if manifest is not None:
            return manifest, variant
    return None


def _stored_reusable_page_contexts_v1(
    database: Path,
    *,
    task: dict[str, Any],
    expected_pages: list[int],
    simple_prompt_sha256: str,
    response_schema_sha256: str,
    additional_prompt_sha256s: dict[str, str] | None = None,
) -> dict[int, tuple[str, str]]:
    """Recover full manifest context without rendering cached pages again."""

    with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as connection:
        documents = connection.execute(
            "SELECT document_id FROM document WHERE source_sha256=? AND source_logical_name=? "
            "ORDER BY document_id",
            (task["source_sha256"], task["relative_path"]),
        ).fetchall()
        if len(documents) != 1:
            raise _error("Agy completed store document identity is not unique")
        rows = connection.execute(
            "SELECT DISTINCT p.physical_page,p.image_sha256 FROM page AS p "
            "JOIN page_json_version AS v USING(page_id) "
            "WHERE p.document_id=? ORDER BY p.physical_page,p.image_sha256",
            (documents[0][0],),
        ).fetchall()
    images: dict[int, set[str]] = {}
    for physical_page, image_sha256 in rows:
        images.setdefault(physical_page, set()).add(image_sha256)
    if set(images) != set(expected_pages) or any(len(values) != 1 for values in images.values()):
        raise _error("Agy completed store image frontier is incomplete or ambiguous")
    contexts: dict[int, tuple[str, str]] = {}
    for page in expected_pages:
        image_sha256 = next(iter(images[page]))
        stored = _reusable_page_manifest(
            database,
            task=task,
            rendered=_RenderedPage(
                image=b"",
                page={"image_sha256": image_sha256, "physical_page": page},
                receipt={},
            ),
            simple_prompt_sha256=simple_prompt_sha256,
            response_schema_sha256=response_schema_sha256,
            additional_prompt_sha256s=additional_prompt_sha256s,
        )
        if stored is None:
            raise _error("Agy completed store prompt frontier is incomplete")
        _manifest, variant = stored
        contexts[page] = image_sha256, variant
    return contexts


def _checked_agy_envelope(raw: bytes) -> tuple[dict[str, Any], dict[str, int], str]:
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _error("Agy output is not one JSON envelope") from exc
    if type(envelope) is not dict or envelope.get("status") != "SUCCESS":
        raise _error("Agy did not return a successful envelope")
    structured = envelope.get("structured_output")
    usage = envelope.get("usage")
    conversation_id = envelope.get("conversation_id")
    if (
        type(structured) is not dict
        or type(usage) is not dict
        or type(conversation_id) is not str
        or not conversation_id
    ):
        raise _error("Agy successful envelope lacks structured output or usage")
    required_usage = {
        "input_tokens",
        "output_tokens",
        "thinking_tokens",
        "cache_read_tokens",
        "total_tokens",
    }
    normalized = {key: usage.get(key) for key in required_usage}
    if any(type(value) is not int or value < 0 for value in normalized.values()):
        raise _error("Agy usage is invalid")
    page_json = decode_financial_page_json_text_v1(
        json.dumps(structured, ensure_ascii=False, separators=(",", ":"))
    )
    return page_json, normalized, conversation_id


def _call_agy(
    *,
    agy_binary: Path,
    effort: str,
    image: bytes,
    prompt: str,
    schema_path: Path,
    timeout_seconds: int,
) -> tuple[bytes, bytes, float]:
    if effort not in EFFORT_ORDER:
        raise _error("Agy effort is invalid")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="gemini-json-first-agy-") as temporary:
        image_path = Path(temporary) / "page.png"
        image_path.write_bytes(image)
        transport_prompt = prompt.rstrip() + "\nẢnh đầu vào duy nhất: @" + str(image_path)
        result = subprocess.run(
            [
                str(agy_binary),
                "--model",
                AGY_MODEL_BY_EFFORT[effort],
                "--effort",
                effort,
                "--json-schema",
                str(schema_path),
                "--output-format",
                "json",
                "--sandbox",
                "--disable-slash-commands",
                "--add-dir",
                temporary,
                "--print-timeout",
                f"{timeout_seconds}s",
                "--print",
                transport_prompt,
            ],
            cwd=ROOT,
            capture_output=True,
            timeout=timeout_seconds + 30,
            check=False,
        )
    elapsed = time.monotonic() - started
    if result.returncode != 0:
        raise _error("Agy subprocess failed with return code " + str(result.returncode))
    return result.stdout, result.stderr, elapsed


def _provider_result(
    *,
    raw: bytes,
    page_json: dict[str, Any],
    usage: dict[str, int],
    conversation_id: str,
    effort: str,
    elapsed: float,
) -> ProviderResultV1:
    normalized_usage = {
        "actual_cost_usd": "0.000000000000",
        "billing_disposition": "AGY_LOCAL_SUBSCRIPTION_NO_INCREMENTAL_API_CHARGE",
        "cached_input_tokens": usage["cache_read_tokens"],
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "thought_tokens": usage["thinking_tokens"],
        "total_tokens": usage["total_tokens"],
    }
    attempt = {
        "attempt_ordinal": 1,
        "credential_slot": "AGY_AUTHENTICATED_LOCAL_SESSION",
        "elapsed_seconds": format(elapsed, ".6f"),
        "http_status": None,
        "outcome": "COMPLETED",
        "provider": AGY_GATEWAY,
        "usage": normalized_usage,
    }
    return ProviderResultV1(
        output_text=canonical_json_bytes_v1(page_json).decode("utf-8"),
        raw_response_bytes=raw,
        provider_name=AGY_SELECTED_PROVIDER,
        provider_model=AGY_MODEL_BY_EFFORT[effort],
        service_tier=f"agy-{effort}",
        attempts=(attempt,),
        usage=normalized_usage,
        response_id_sha256=sha256(conversation_id.encode("utf-8")).hexdigest(),
    )


def _ingest_with_lock_retry(database: Path, **kwargs: Any) -> dict[str, str]:
    for attempt in range(1, 21):
        try:
            return ingest_financial_page_extraction_v1(database, **kwargs)
        except Exception as exc:
            if "database is locked" not in str(exc).lower() or attempt == 20:
                raise
            time.sleep(min(0.05 * attempt, 0.5))
    raise AssertionError("unreachable SQLite retry frontier")


def _process_page(
    *,
    task: dict[str, Any],
    source: Path,
    database: Path,
    artifact_root: Path,
    agy_binary: Path,
    dpi: int,
    prompt: str,
    prompt_sha256: str,
    prompt_variant: str = "simple",
    reusable_simple_prompt_sha256: str | None = None,
    schema_path: Path,
    response_schema_sha256: str,
    timeout_seconds: int,
    physical_page: int,
    provider_authorized: bool = True,
    expected_image_sha256: str | None = None,
    clockwise_rotation_degrees: int | None = None,
) -> _PageResult:
    rendered = _render_page(
        source,
        physical_page=physical_page,
        dpi=dpi,
        source_sha256=task["source_sha256"],
    )
    if clockwise_rotation_degrees is not None:
        rendered = _rotate_rendered_page_v1(
            rendered,
            source_sha256=task["source_sha256"],
            physical_page=physical_page,
            clockwise_degrees=clockwise_rotation_degrees,
        )
    if expected_image_sha256 is not None and rendered.page["image_sha256"] != expected_image_sha256:
        raise _AgyPageImageIdentityV1Error(
            "Agy refused a page whose image changed after its atomic claim"
        )
    page_root = artifact_root / f"page-{physical_page:05d}"
    _write_or_verify(page_root / "render-receipt.json", canonical_json_bytes_v1(rendered.receipt))
    existing = _reusable_page_manifest(
        database,
        task=task,
        rendered=rendered,
        simple_prompt_sha256=reusable_simple_prompt_sha256 or prompt_sha256,
        response_schema_sha256=response_schema_sha256,
        additional_prompt_sha256s=(
            {prompt_variant: prompt_sha256}
            if prompt_variant not in REUSABLE_PROMPT_VARIANTS
            else None
        ),
    )
    if existing is not None:
        _manifest, prompt_variant = existing
        return _PageResult(
            physical_page,
            "REUSED",
            rendered.page,
            prompt_variant=prompt_variant,
        )
    if not provider_authorized:
        raise _error("Agy refused provider work outside its exact claimed page frontier")

    last_failure_kind = "AGY_PROVIDER_FAILED"
    for effort in EFFORT_ORDER:
        attempt_root = page_root / f"effort-{effort}"
        invocation = {
            "base_prompt_sha256": prompt_sha256,
            "effort": effort,
            "format_version": FORMAT_VERSION,
            "image_sha256": rendered.page["image_sha256"],
            "model": AGY_MODEL_BY_EFFORT[effort],
            "response_schema_sha256": response_schema_sha256,
        }
        _write_or_verify(attempt_root / "invocation.json", canonical_json_bytes_v1(invocation))
        raw_path = attempt_root / "agy-response.json"
        stderr_path = attempt_root / "agy-stderr.log"
        elapsed_path = attempt_root / "elapsed-seconds.txt"
        try:
            if raw_path.exists():
                raw = raw_path.read_bytes()
                stderr = stderr_path.read_bytes()
                elapsed = float(elapsed_path.read_text(encoding="utf-8").strip())
            else:
                raw, stderr, elapsed = _call_agy(
                    agy_binary=agy_binary,
                    effort=effort,
                    image=rendered.image,
                    prompt=prompt,
                    schema_path=schema_path,
                    timeout_seconds=timeout_seconds,
                )
                _write_or_verify(raw_path, raw)
                _write_or_verify(stderr_path, stderr)
                _write_or_verify(elapsed_path, (format(elapsed, ".6f") + "\n").encode("utf-8"))
            page_json, usage, conversation_id = _checked_agy_envelope(raw)
        except Exception as exc:
            last_failure_kind = "AGY_PROVIDER_OR_SCHEMA_FAILED"
            _write_or_verify(
                attempt_root / "failure.json",
                canonical_json_bytes_v1(
                    {
                        "error_message": str(exc),
                        "error_type": type(exc).__name__,
                        "failure_kind": last_failure_kind,
                    }
                ),
            )
            continue
        page_bytes = canonical_json_bytes_v1(page_json)
        _write_or_verify(attempt_root / "page.json", page_bytes)
        _write_or_verify(
            attempt_root / "observation.json",
            canonical_json_bytes_v1(
                {
                    "content_counts": count_financial_page_content_v1(page_json),
                    "effort": effort,
                    "page_json_sha256": sha256(page_bytes).hexdigest(),
                    "status": page_json["status"],
                    "usage": usage,
                }
            ),
        )
        if page_json["status"] == "UNRESOLVED_PAGE":
            last_failure_kind = "AGY_UNRESOLVED_PAGE"
            continue
        provider_result = _provider_result(
            raw=raw,
            page_json=page_json,
            usage=usage,
            conversation_id=conversation_id,
            effort=effort,
            elapsed=elapsed,
        )
        identities = _ingest_with_lock_retry(
            database,
            document={
                "source_logical_name": task["relative_path"],
                "source_sha256": task["source_sha256"],
                "source_size_bytes": task["source_size_bytes"],
            },
            page=rendered.page,
            prompt_variant=prompt_variant,
            output_contract_mode="JSON_SCHEMA",
            prompt_sha256=prompt_sha256,
            response_schema_sha256=response_schema_sha256,
            requested_model=GOOGLE_MODEL,
            requested_service_tier=f"agy-{effort}",
            thinking_level=effort,
            provider_result=provider_result,
            page_json=page_json,
        )
        _write_or_verify(attempt_root / "ingestion.json", canonical_json_bytes_v1(identities))
        return _PageResult(
            physical_page,
            "INGESTED",
            rendered.page,
            effort=effort,
            prompt_variant=prompt_variant,
        )
    return _PageResult(
        physical_page,
        "FAILED",
        rendered.page,
        effort="high",
        failure_kind=last_failure_kind,
    )


def run_agy_document_v1(args: argparse.Namespace) -> dict[str, Any]:
    if not 1 <= args.workers <= 20:
        raise _error("Agy worker bound lies outside 1..20")
    if not 30 <= args.timeout_seconds <= 1_800:
        raise _error("Agy timeout lies outside 30..1800 seconds")
    if args.agy_binary.is_symlink() or not args.agy_binary.is_file():
        raise _error("Agy binary is absent or not regular")
    plan = validate_gemini_json_first_corpus_plan_v1(_json_file(args.plan))
    summary = corpus_ledger_summary_v1(args.ledger)
    if plan["corpus_plan_id"] != summary["corpus_plan_id"]:
        raise _error("Agy plan and corpus ledger disagree")
    terminal_provider_repair = getattr(args, "terminal_provider_repair", False)
    terminal_unaccepted_repair = getattr(args, "terminal_unaccepted_repair", False)
    source_render_recovery = getattr(args, "source_render_recovery", False)
    tool_denied_orientation_recovery = getattr(args, "tool_denied_orientation_recovery", False)
    schema_alignment_recovery = getattr(args, "schema_alignment_recovery", False)
    repair_mode = (
        terminal_provider_repair
        or terminal_unaccepted_repair
        or source_render_recovery
        or tool_denied_orientation_recovery
        or schema_alignment_recovery
    )
    source_revision_registry = getattr(args, "source_revision_registry", None)
    orientation_repair_registry = getattr(args, "orientation_repair_registry", None)
    schema_alignment_repair_registry = getattr(args, "schema_alignment_repair_registry", None)
    historical_ledger = getattr(args, "historical_ledger", None)
    if (
        terminal_unaccepted_repair
        or source_render_recovery
        or tool_denied_orientation_recovery
        or schema_alignment_recovery
    ) and source_revision_registry is None:
        raise _error("Agy evidence-bound repair requires a source-revision registry")
    if tool_denied_orientation_recovery and orientation_repair_registry is None:
        raise _error("Agy orientation recovery requires an orientation-repair registry")
    if schema_alignment_recovery and schema_alignment_repair_registry is None:
        raise _error("Agy schema-alignment recovery requires a repair registry")
    if historical_ledger is not None and not terminal_unaccepted_repair:
        raise _error("Agy historical ledger is only valid for unaccepted-page repair")
    dpi = plan["policy"]["dpi"]
    _task_execution_lock = None
    if repair_mode and args.task_id is None:
        if schema_alignment_recovery:
            task, _task_execution_lock = _claim_schema_alignment_recovery_with_execution_lock_v1(
                ledger=args.ledger,
                source_root=args.source_root,
                database=args.database,
                artifact_root=args.artifact_root,
                source_revision_registry=source_revision_registry,
                schema_alignment_repair_registry=schema_alignment_repair_registry,
                dpi=dpi,
                task_id=None,
            )
        elif tool_denied_orientation_recovery:
            task, _task_execution_lock = (
                _claim_tool_denied_orientation_recovery_with_execution_lock_v1(
                    ledger=args.ledger,
                    source_root=args.source_root,
                    database=args.database,
                    artifact_root=args.artifact_root,
                    source_revision_registry=source_revision_registry,
                    orientation_repair_registry=orientation_repair_registry,
                    dpi=dpi,
                    task_id=None,
                )
            )
        elif source_render_recovery:
            task, _task_execution_lock = _claim_source_render_recovery_with_execution_lock_v1(
                ledger=args.ledger,
                source_root=args.source_root,
                database=args.database,
                artifact_root=args.artifact_root,
                source_revision_registry=source_revision_registry,
                dpi=dpi,
                task_id=None,
            )
        elif terminal_unaccepted_repair:
            task, _task_execution_lock = _claim_unaccepted_task_with_execution_lock_v1(
                ledger=args.ledger,
                source_root=args.source_root,
                database=args.database,
                artifact_root=args.artifact_root,
                source_revision_registry=source_revision_registry,
                historical_ledger=historical_ledger,
                dpi=dpi,
                task_id=None,
            )
        else:
            task, _task_execution_lock = _claim_terminal_task_with_execution_lock_v1(
                ledger=args.ledger,
                source_root=args.source_root,
                database=args.database,
                artifact_root=args.artifact_root,
                task_id=None,
            )
    elif args.task_id is None:
        task = claim_pending_openrouter_corpus_task_for_agy_v1(args.ledger)
    else:
        matches = [
            task for task in list_corpus_tasks_v1(args.ledger) if task["task_id"] == args.task_id
        ]
        if len(matches) != 1:
            raise _error("Agy task ID is absent from the corpus ledger")
        task = matches[0]
        if repair_mode and task["state"] == "FAILED":
            if schema_alignment_recovery:
                task, _task_execution_lock = (
                    _claim_schema_alignment_recovery_with_execution_lock_v1(
                        ledger=args.ledger,
                        source_root=args.source_root,
                        database=args.database,
                        artifact_root=args.artifact_root,
                        source_revision_registry=source_revision_registry,
                        schema_alignment_repair_registry=schema_alignment_repair_registry,
                        dpi=dpi,
                        task_id=args.task_id,
                    )
                )
            elif tool_denied_orientation_recovery:
                task, _task_execution_lock = (
                    _claim_tool_denied_orientation_recovery_with_execution_lock_v1(
                        ledger=args.ledger,
                        source_root=args.source_root,
                        database=args.database,
                        artifact_root=args.artifact_root,
                        source_revision_registry=source_revision_registry,
                        orientation_repair_registry=orientation_repair_registry,
                        dpi=dpi,
                        task_id=args.task_id,
                    )
                )
            elif source_render_recovery:
                task, _task_execution_lock = _claim_source_render_recovery_with_execution_lock_v1(
                    ledger=args.ledger,
                    source_root=args.source_root,
                    database=args.database,
                    artifact_root=args.artifact_root,
                    source_revision_registry=source_revision_registry,
                    dpi=dpi,
                    task_id=args.task_id,
                )
            elif terminal_unaccepted_repair:
                task, _task_execution_lock = _claim_unaccepted_task_with_execution_lock_v1(
                    ledger=args.ledger,
                    source_root=args.source_root,
                    database=args.database,
                    artifact_root=args.artifact_root,
                    source_revision_registry=source_revision_registry,
                    historical_ledger=historical_ledger,
                    dpi=dpi,
                    task_id=args.task_id,
                )
            else:
                task, _task_execution_lock = _claim_terminal_task_with_execution_lock_v1(
                    ledger=args.ledger,
                    source_root=args.source_root,
                    database=args.database,
                    artifact_root=args.artifact_root,
                    task_id=args.task_id,
                )
        elif repair_mode and task["state"] == "SUBMITTED":
            _task_execution_lock = acquire_corpus_task_execution_lock_v1(
                args.ledger,
                task_id=args.task_id,
            )
        elif not repair_mode and task["state"] == "PENDING":
            task = claim_pending_openrouter_corpus_task_for_agy_v1(
                args.ledger, task_id=args.task_id
            )
        elif not (
            task["state"] == "SUBMITTED"
            and type(task["provider_job_ref"]) is str
            and task["provider_job_ref"].startswith(AGY_PROVIDER_JOB_PREFIX)
        ):
            expected = (
                "failed repair candidate or reserved" if repair_mode else "pending or reserved"
            )
            raise _error(f"Agy task is not {expected} by Agy")
    try:
        claim_receipt = json.loads(task["last_receipt_json"])
    except (TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _error("Agy task claim receipt is invalid") from exc
    expected_claim_format = (
        "GEMINI_JSON_FIRST_AGY_SCHEMA_ALIGNMENT_RECOVERY_CLAIM_V1"
        if schema_alignment_recovery
        else "GEMINI_JSON_FIRST_AGY_TOOL_DENIED_ORIENTATION_RECOVERY_CLAIM_V1"
        if tool_denied_orientation_recovery
        else "GEMINI_JSON_FIRST_AGY_SOURCE_RENDER_RECOVERY_CLAIM_V1"
        if source_render_recovery
        else "GEMINI_JSON_FIRST_AGY_EXHAUSTED_UNACCEPTED_PAGE_CLAIM_V1"
        if terminal_unaccepted_repair
        else "GEMINI_JSON_FIRST_AGY_TERMINAL_PROVIDER_REPAIR_CLAIM_V1"
    )
    if repair_mode:
        if (
            type(claim_receipt) is not dict
            or claim_receipt.get("format_version") != expected_claim_format
            or claim_receipt.get("provider_job_ref") != task["provider_job_ref"]
            or claim_receipt.get("source_sha256") != task["source_sha256"]
            or claim_receipt.get("task_id") != task["task_id"]
            or claim_receipt.get("execution_provider") != "AGY_CLI"
        ):
            raise _error("Agy terminal repair claim is invalid")
        claimed_provider_pages = claim_receipt.get("failed_pages")
        if (
            type(claimed_provider_pages) is not list
            or not claimed_provider_pages
            or claimed_provider_pages != sorted(set(claimed_provider_pages))
            or any(
                type(page) is not int
                or page < task["first_physical_page"]
                or page > task["last_physical_page"]
                for page in claimed_provider_pages
            )
        ):
            raise _error("Agy terminal claimed page frontier is invalid")
    else:
        claimed_provider_pages = list(
            range(task["first_physical_page"], task["last_physical_page"] + 1)
        )
    expected_image_sha256s: dict[int, str] = {}
    rotation_degrees_by_page: dict[int, int] = {}
    if (
        terminal_unaccepted_repair
        or source_render_recovery
        or tool_denied_orientation_recovery
        or schema_alignment_recovery
    ):
        page_evidence = claim_receipt.get("page_evidence")
        if (
            type(page_evidence) is not list
            or [item.get("physical_page") for item in page_evidence if type(item) is dict]
            != claimed_provider_pages
            or (
                not tool_denied_orientation_recovery
                and claim_receipt.get("page_evidence_sha256")
                != canonical_json_sha256_v1(page_evidence)
            )
        ):
            raise _error("Agy evidence-bound claim is invalid")
        if schema_alignment_recovery:
            attempt_evidence = claim_receipt.get("prior_attempt_evidence")
            claim_material = {
                key: value
                for key, value in claim_receipt.items()
                if key not in {"execution_provider", "initial_effort", "provider_job_ref"}
            }
            expected_axis = [
                (page, effort) for page in claimed_provider_pages for effort in EFFORT_ORDER
            ]
            if (
                len(claimed_provider_pages) != 1
                or type(attempt_evidence) is not list
                or [
                    (item.get("physical_page"), item.get("effort"))
                    for item in attempt_evidence
                    if type(item) is dict
                ]
                != expected_axis
                or [item.get("failure_kind") for item in attempt_evidence if type(item) is dict]
                != ["ROW_COLUMN_ALIGNMENT", "COMMAND_TOOL_DENIED", "COMMAND_TOOL_DENIED"]
                or claim_receipt.get("prior_attempt_evidence_sha256")
                != canonical_json_sha256_v1(attempt_evidence)
                or claim_receipt.get("provider_job_ref")
                != AGY_PROVIDER_JOB_PREFIX + canonical_json_sha256_v1(claim_material)
            ):
                raise _error("Agy schema-alignment recovery claim evidence is invalid")
        elif tool_denied_orientation_recovery:
            orientation_evidence = claim_receipt.get("orientation_repair_evidence")
            tool_denial_evidence = claim_receipt.get("tool_denial_evidence")
            claim_material = {
                key: value
                for key, value in claim_receipt.items()
                if key not in {"execution_provider", "initial_effort", "provider_job_ref"}
            }
            expected_denial_axis = [
                (page, effort) for page in claimed_provider_pages for effort in EFFORT_ORDER
            ]
            if (
                type(orientation_evidence) is not list
                or [
                    item.get("physical_page") for item in orientation_evidence if type(item) is dict
                ]
                != claimed_provider_pages
                or any(
                    type(item) is not dict
                    or set(item)
                    != {
                        "clockwise_degrees",
                        "corrected_image_sha256",
                        "orientation_receipt_sha256",
                        "original_image_sha256",
                        "physical_page",
                    }
                    or item.get("clockwise_degrees") not in {90, 270}
                    for item in orientation_evidence
                )
                or claim_receipt.get("orientation_repair_evidence_sha256")
                != canonical_json_sha256_v1(orientation_evidence)
                or type(tool_denial_evidence) is not list
                or [
                    (item.get("physical_page"), item.get("effort"))
                    for item in tool_denial_evidence
                    if type(item) is dict
                ]
                != expected_denial_axis
                or claim_receipt.get("tool_denial_evidence_sha256")
                != canonical_json_sha256_v1(tool_denial_evidence)
                or claim_receipt.get("provider_job_ref")
                != AGY_PROVIDER_JOB_PREFIX + canonical_json_sha256_v1(claim_material)
                or any(
                    item.get("image_sha256")
                    != orientation_evidence[index].get("corrected_image_sha256")
                    for index, item in enumerate(page_evidence)
                )
            ):
                raise _error("Agy orientation recovery claim evidence is invalid")
            rotation_degrees_by_page = {
                item["physical_page"]: item["clockwise_degrees"] for item in orientation_evidence
            }
        elif terminal_unaccepted_repair:
            exhaustion_evidence = claim_receipt.get("exhaustion_evidence")
            cross_history = claim_receipt.get("cross_corpus_history_evidence")
            one_attempt_balanced_exhaustion = bool(
                type(exhaustion_evidence) is list
                and len(exhaustion_evidence) == 1
                and type(exhaustion_evidence[0]) is dict
                and exhaustion_evidence[0].get("exhaustion_kind")
                == "BALANCED_SEMANTIC_RETRY_BLOCKS_SECOND_ATTEMPT"
                and type(exhaustion_evidence[0].get("balanced_semantic_failed_pages")) is list
                and bool(exhaustion_evidence[0]["balanced_semantic_failed_pages"])
            )
            if (
                type(exhaustion_evidence) is not list
                or len(exhaustion_evidence) not in {1, 2}
                or [
                    item.get("repair_attempt") for item in exhaustion_evidence if type(item) is dict
                ]
                != ([1] if one_attempt_balanced_exhaustion else [1, 2])
                or claim_receipt.get("exhaustion_evidence_sha256")
                != canonical_json_sha256_v1(exhaustion_evidence)
                or (
                    cross_history is not None
                    and (
                        historical_ledger is None
                        or historical_ledger.is_symlink()
                        or not historical_ledger.is_file()
                        or type(cross_history) is not dict
                        or claim_receipt.get("cross_corpus_history_evidence_sha256")
                        != canonical_json_sha256_v1(cross_history)
                        or cross_history.get("historical_ledger_sha256")
                        != sha256(historical_ledger.read_bytes()).hexdigest()
                    )
                )
                or (historical_ledger is not None and cross_history is None)
            ):
                raise _error("Agy unaccepted-page exhaustion evidence is invalid")
        else:
            local_evidence = claim_receipt.get("local_render_repair_evidence")
            renderer_path = ROOT / "src/bctc_ai/evaluation/gemini_json_first_page_render_v1.py"
            if (
                type(local_evidence) is not list
                or not local_evidence
                or claim_receipt.get("local_render_repair_evidence_sha256")
                != canonical_json_sha256_v1(local_evidence)
                or renderer_path.is_symlink()
                or not renderer_path.is_file()
                or claim_receipt.get("renderer_source_sha256")
                != sha256(renderer_path.read_bytes()).hexdigest()
            ):
                raise _error("Agy source-render recovery evidence is invalid")
        expected_image_sha256s = {
            item["physical_page"]: item["image_sha256"] for item in page_evidence
        }
        if len(expected_image_sha256s) != len(claimed_provider_pages) or any(
            type(digest) is not str
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            for digest in expected_image_sha256s.values()
        ):
            raise _error("Agy unaccepted-page image evidence is invalid")
    source = _source(task, args.source_root)
    prompt = build_financial_page_json_prompt_v1(variant="simple")
    reusable_simple_prompt_sha256 = sha256(prompt.encode("utf-8")).hexdigest()
    execution_prompt_variant = "simple"
    if schema_alignment_recovery:
        repairs = _schema_alignment_repairs_v1(schema_alignment_repair_registry)
        page = claimed_provider_pages[0]
        entry = repairs.get((task["relative_path"], task["source_sha256"], page))
        if (
            entry is None
            or canonical_json_sha256_v1(entry) != claim_receipt.get("repair_registry_entry_sha256")
            or sha256(entry["repair_instruction"].encode("utf-8")).hexdigest()
            != claim_receipt.get("repair_instruction_sha256")
        ):
            raise _error("Agy schema-alignment repair registry drifted after claim")
        prompt = prompt.rstrip() + "\n\n" + entry["repair_instruction"].strip() + "\n"
        execution_prompt_variant = "schema_alignment"
    prompt_bytes = prompt.encode("utf-8")
    schema = financial_page_json_response_schema_v1()
    schema_bytes = canonical_json_bytes_v1(schema)
    prompt_sha256 = sha256(prompt_bytes).hexdigest()
    response_schema_sha256 = canonical_json_sha256_v1(schema)
    task_root = (
        args.artifact_root
        / task["artifact_relative_path"]
        / (
            "agy-exhausted-unaccepted-repair"
            if terminal_unaccepted_repair
            else "agy-schema-alignment-recovery"
            if schema_alignment_recovery
            else "agy-tool-denied-orientation-recovery"
            if tool_denied_orientation_recovery
            else "agy-source-render-recovery"
            if source_render_recovery
            else "agy-terminal-provider-repair"
            if terminal_provider_repair
            else "agy"
        )
    )
    _write_or_verify(task_root / "prompt.txt", prompt_bytes)
    _write_or_verify(task_root / "response-schema.json", schema_bytes)
    expected_pages = list(range(task["first_physical_page"], task["last_physical_page"] + 1))
    execution_pages = claimed_provider_pages if repair_mode else expected_pages
    outcomes: list[_PageResult] = []
    with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix="agy-page") as executor:
        futures = {
            executor.submit(
                _process_page,
                task=task,
                source=source,
                database=args.database,
                artifact_root=task_root,
                agy_binary=args.agy_binary,
                dpi=dpi,
                prompt=prompt,
                prompt_sha256=prompt_sha256,
                prompt_variant=execution_prompt_variant,
                reusable_simple_prompt_sha256=reusable_simple_prompt_sha256,
                schema_path=task_root / "response-schema.json",
                response_schema_sha256=response_schema_sha256,
                timeout_seconds=args.timeout_seconds,
                physical_page=page,
                provider_authorized=page in claimed_provider_pages,
                expected_image_sha256=expected_image_sha256s.get(page),
                clockwise_rotation_degrees=rotation_degrees_by_page.get(page),
            ): page
            for page in execution_pages
        }
        for future in as_completed(futures):
            physical_page = futures[future]
            try:
                outcomes.append(future.result())
            except GeminiJsonFirstPageRenderV1Error as exc:
                page_root = task_root / f"page-{physical_page:05d}"
                _write_or_verify(
                    page_root / "render-failure.json",
                    canonical_json_bytes_v1(
                        {
                            "error_message": str(exc),
                            "error_type": type(exc).__name__,
                            "failure_kind": "AGY_SOURCE_OR_RENDER_FAILED",
                            "physical_page": physical_page,
                        }
                    ),
                )
                outcomes.append(
                    _PageResult(
                        physical_page,
                        "FAILED",
                        {},
                        failure_kind="AGY_SOURCE_OR_RENDER_FAILED",
                    )
                )
            except _AgyPageImageIdentityV1Error as exc:
                page_root = task_root / f"page-{physical_page:05d}"
                _write_or_verify(
                    page_root / "image-identity-failure.json",
                    canonical_json_bytes_v1(
                        {
                            "error_message": str(exc),
                            "error_type": type(exc).__name__,
                            "failure_kind": "AGY_SOURCE_OR_RENDER_IDENTITY_FAILED",
                            "physical_page": physical_page,
                        }
                    ),
                )
                outcomes.append(
                    _PageResult(
                        physical_page,
                        "FAILED",
                        {},
                        failure_kind="AGY_SOURCE_OR_RENDER_IDENTITY_FAILED",
                    )
                )
    outcomes.sort(key=lambda item: item.physical_page)
    failed = [item for item in outcomes if item.disposition == "FAILED"]
    source_failed_pages = [
        item.physical_page
        for item in failed
        if item.failure_kind
        in {"AGY_SOURCE_OR_RENDER_FAILED", "AGY_SOURCE_OR_RENDER_IDENTITY_FAILED"}
    ]
    result = {
        "effort_counts": {
            effort: sum(
                item.effort == effort and item.disposition == "INGESTED" for item in outcomes
            )
            for effort in EFFORT_ORDER
        },
        "failed_pages": [item.physical_page for item in failed],
        "format_version": FORMAT_VERSION,
        "provider_authorized_pages": claimed_provider_pages,
        "provider_request_pages": [
            item.physical_page
            for item in outcomes
            if item.disposition != "REUSED"
            and item.failure_kind
            not in {"AGY_SOURCE_OR_RENDER_FAILED", "AGY_SOURCE_OR_RENDER_IDENTITY_FAILED"}
        ],
        "provider_job_ref": task["provider_job_ref"],
        "reused_pages": sorted(
            (set(expected_pages) - set(execution_pages))
            | {item.physical_page for item in outcomes if item.disposition == "REUSED"}
        ),
        "task_id": task["task_id"],
    }
    if failed:
        semantic_unresolved = [
            item.physical_page for item in failed if item.failure_kind == "AGY_UNRESOLVED_PAGE"
        ]
        receipt = {
            **result,
            "provider_failed_pages": sorted(
                set(result["failed_pages"]) - set(semantic_unresolved) - set(source_failed_pages)
            ),
            "recitation_failed_pages": [],
            "semantic_failed_pages": semantic_unresolved,
            "source_failed_pages": source_failed_pages,
            "unresolved_pages": sorted(set(semantic_unresolved) | set(source_failed_pages)),
        }
        next_state = "FAILED" if repair_mode else "NEEDS_RETRY"
        if terminal_provider_repair:
            receipt = {
                **receipt,
                "disposition": "AGY_TERMINAL_PROVIDER_REPAIR_FAILED",
                "prior_failed_receipt_sha256": claim_receipt["prior_failed_receipt_sha256"],
            }
        elif terminal_unaccepted_repair:
            receipt = {
                **receipt,
                "disposition": "AGY_EXHAUSTED_UNACCEPTED_REPAIR_FAILED",
                "prior_failed_receipt_sha256": claim_receipt["prior_failed_receipt_sha256"],
            }
        elif source_render_recovery:
            receipt = {
                **receipt,
                "disposition": "AGY_SOURCE_RENDER_RECOVERY_FAILED",
                "prior_failed_receipt_sha256": claim_receipt["prior_failed_receipt_sha256"],
            }
        elif tool_denied_orientation_recovery:
            receipt = {
                **receipt,
                "disposition": "AGY_TOOL_DENIED_ORIENTATION_RECOVERY_FAILED",
                "prior_failed_receipt_sha256": claim_receipt["prior_failed_receipt_sha256"],
            }
        elif schema_alignment_recovery:
            receipt = {
                **receipt,
                "disposition": "AGY_SCHEMA_ALIGNMENT_RECOVERY_FAILED",
                "prior_failed_receipt_sha256": claim_receipt["prior_failed_receipt_sha256"],
            }
        transition_corpus_task_v1(
            args.ledger,
            task_id=task["task_id"],
            expected_state="SUBMITTED",
            next_state=next_state,
            receipt=receipt,
            provider_job_ref=task["provider_job_ref"],
        )
        _write_or_verify(task_root / "agy-run-result.json", canonical_json_bytes_v1(receipt))
        if repair_mode:
            return receipt
        return {**receipt, "disposition": "NEEDS_VERTEX_FLEX_RETRY"}
    stored_contexts = _stored_reusable_page_contexts_v1(
        args.database,
        task=task,
        expected_pages=expected_pages,
        simple_prompt_sha256=reusable_simple_prompt_sha256,
        response_schema_sha256=response_schema_sha256,
        additional_prompt_sha256s=(
            {execution_prompt_variant: prompt_sha256}
            if execution_prompt_variant not in REUSABLE_PROMPT_VARIANTS
            else None
        ),
    )
    image_frontier = {page: stored_contexts[page][0] for page in expected_pages}
    page_prompt_sha256s = {
        page: (
            prompt_sha256
            if stored_contexts[page][1] == execution_prompt_variant
            and execution_prompt_variant not in REUSABLE_PROMPT_VARIANTS
            else sha256(
                build_financial_page_json_prompt_v1(variant=stored_contexts[page][1]).encode(
                    "utf-8"
                )
            ).hexdigest()
        )
        for page in expected_pages
    }
    if sorted(page_prompt_sha256s) != expected_pages:
        raise _error("Agy completed page prompt frontier is incomplete")
    manifest = build_financial_document_manifest_v1(
        args.database,
        source_sha256=task["source_sha256"],
        source_logical_name=task["relative_path"],
        expected_physical_pages=expected_pages,
        page_image_sha256s=image_frontier,
        prompt_sha256=page_prompt_sha256s,
        response_schema_sha256=response_schema_sha256,
        requested_model=GOOGLE_MODEL,
        allowed_gateway_service_tiers=_routes(),
        preferred_gateway_service_tiers=_preferred_routes(),
    )
    seal_agy_corpus_task_v1(
        args.ledger,
        task_id=task["task_id"],
        provider_job_ref=task["provider_job_ref"],
        document_manifest=manifest,
    )
    complete = {
        **result,
        "disposition": "SUCCEEDED",
        "document_manifest_id": manifest["document_manifest_id"],
    }
    _write_or_verify(task_root / "agy-document-manifest.json", canonical_json_bytes_v1(manifest))
    _write_or_verify(task_root / "agy-run-result.json", canonical_json_bytes_v1(complete))
    return complete


def main() -> int:
    try:
        result = run_agy_document_v1(_parser().parse_args())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["disposition"] == "SUCCEEDED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
