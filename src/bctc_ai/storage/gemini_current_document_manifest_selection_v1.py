"""Append-only selection chain for current Gemini document manifests."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "GEMINI_CURRENT_DOCUMENT_MANIFEST_SELECTION_V1"


class GeminiCurrentDocumentManifestSelectionV1Error(ValueError):
    """A selection or append-only supersession chain is not exact."""


def _error(message: str) -> GeminiCurrentDocumentManifestSelectionV1Error:
    return GeminiCurrentDocumentManifestSelectionV1Error(message)


def build_current_document_manifest_selection_v1(
    *,
    document_plan_id: str,
    source_sha256: str,
    document_manifest_id: str,
    document_manifest_ref: Mapping[str, Any],
    page_image_frontier_sha256: str,
    page_prompt_frontier_sha256: str,
    prior_selection_ids: Sequence[str],
) -> dict[str, Any]:
    """Build one immutable head that supersedes the prior selection head."""

    material = {
        "document_manifest_id": document_manifest_id,
        "document_manifest_ref": canonical_clone_v1(dict(document_manifest_ref)),
        "document_plan_id": document_plan_id,
        "format_version": FORMAT_VERSION,
        "page_image_frontier_sha256": page_image_frontier_sha256,
        "page_prompt_frontier_sha256": page_prompt_frontier_sha256,
        "prior_selection_ids": list(prior_selection_ids),
        "source_sha256": source_sha256,
    }
    return validate_current_document_manifest_selection_v1(
        {
            **material,
            "selection_id": "gjfcdmsv1:selection:" + canonical_json_sha256_v1(material),
        }
    )


def validate_current_document_manifest_selection_v1(value: Any) -> dict[str, Any]:
    """Validate and canonicalize one selection receipt."""

    if type(value) is not dict:
        raise _error("document manifest selection must be one object")
    checked = canonical_clone_v1(value)
    required = {
        "document_manifest_id",
        "document_manifest_ref",
        "document_plan_id",
        "format_version",
        "page_image_frontier_sha256",
        "page_prompt_frontier_sha256",
        "prior_selection_ids",
        "selection_id",
        "source_sha256",
    }
    if set(checked) != required or checked["format_version"] != FORMAT_VERSION:
        raise _error("document manifest selection fields drifted")
    for field, prefix in (
        ("document_manifest_id", "gfdmv1:manifest:"),
        ("document_plan_id", "gjfpdocv1:"),
        ("selection_id", "gjfcdmsv1:selection:"),
    ):
        if type(checked[field]) is not str or not checked[field].startswith(prefix):
            raise _error(f"document manifest selection {field} is invalid")
    for field in (
        "source_sha256",
        "page_image_frontier_sha256",
        "page_prompt_frontier_sha256",
    ):
        digest = checked[field]
        if (
            type(digest) is not str
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise _error(f"document manifest selection {field} is invalid")
    reference = checked["document_manifest_ref"]
    if (
        type(reference) is not dict
        or set(reference) != {"path", "sha256", "size_bytes"}
        or type(reference["path"]) is not str
        or not reference["path"]
        or reference["path"].startswith("/")
        or ".." in reference["path"].split("/")
        or type(reference["sha256"]) is not str
        or len(reference["sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in reference["sha256"])
        or type(reference["size_bytes"]) is not int
        or reference["size_bytes"] <= 0
    ):
        raise _error("document manifest selection reference is invalid")
    priors = checked["prior_selection_ids"]
    if (
        type(priors) is not list
        or priors != sorted(set(priors))
        or any(
            type(item) is not str or not item.startswith("gjfcdmsv1:selection:") for item in priors
        )
        or checked["selection_id"] in priors
    ):
        raise _error("document manifest prior selection frontier is invalid")
    material = {key: checked[key] for key in checked if key != "selection_id"}
    if checked["selection_id"] != "gjfcdmsv1:selection:" + canonical_json_sha256_v1(material):
        raise _error("document manifest selection identity does not replay")
    return checked


def select_current_document_manifest_selection_v1(
    values: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return the unique append-only head and reject forks or disconnected chains."""

    selections = [validate_current_document_manifest_selection_v1(dict(value)) for value in values]
    if not selections:
        raise _error("document manifest selection chain is empty")
    by_id = {selection["selection_id"]: selection for selection in selections}
    if len(by_id) != len(selections):
        raise _error("document manifest selection identity is duplicate")
    document_bindings = {
        (selection["document_plan_id"], selection["source_sha256"]) for selection in selections
    }
    if len(document_bindings) != 1:
        raise _error("document manifest selection document binding is mixed")
    referenced = {prior for selection in selections for prior in selection["prior_selection_ids"]}
    if not referenced <= set(by_id):
        raise _error("document manifest selection prior is absent")
    heads = set(by_id) - referenced
    if len(heads) != 1:
        raise _error("document manifest selection head is not unique")
    head_id = next(iter(heads))
    reachable = set()
    active = set()

    def visit(selection_id: str) -> None:
        if selection_id in active:
            raise _error("document manifest selection chain is cyclic")
        if selection_id in reachable:
            return
        active.add(selection_id)
        for prior in by_id[selection_id]["prior_selection_ids"]:
            visit(prior)
        active.remove(selection_id)
        reachable.add(selection_id)

    visit(head_id)
    if reachable != set(by_id):
        raise _error("document manifest selection chain is disconnected")
    return by_id[head_id]


def load_current_document_manifest_selection_v1(
    document_root: Path,
    *,
    document_plan_id: str,
    source_sha256: str,
) -> tuple[dict[str, Any], Path] | None:
    """Load the unique selection head and authenticate its content reference."""

    selection_root = document_root / "current-document-manifest-selections"
    if not selection_root.exists():
        return None
    if selection_root.is_symlink() or not selection_root.is_dir():
        raise _error("document manifest selection directory is invalid")
    selections = []
    for path in sorted(selection_root.glob("*.json")):
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise _error("document manifest selection is not one regular single-link file")
        raw = path.read_bytes()
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise _error("document manifest selection JSON is invalid") from exc
        checked = validate_current_document_manifest_selection_v1(value)
        if raw != canonical_json_bytes_v1(checked) + b"\n":
            raise _error("document manifest selection JSON is not canonical")
        if path.name != checked["selection_id"].split(":", 2)[2] + ".json":
            raise _error("document manifest selection filename is invalid")
        selections.append(checked)
    if not selections:
        return None
    head = select_current_document_manifest_selection_v1(selections)
    if head["document_plan_id"] != document_plan_id or head["source_sha256"] != source_sha256:
        raise _error("document manifest selection head binding is invalid")
    reference = head["document_manifest_ref"]
    manifest_path = document_root / reference["path"]
    if (
        manifest_path.is_symlink()
        or not manifest_path.is_file()
        or manifest_path.stat().st_nlink != 1
    ):
        raise _error("selected document manifest is not one regular single-link file")
    raw = manifest_path.read_bytes()
    if len(raw) != reference["size_bytes"] or sha256(raw).hexdigest() != reference["sha256"]:
        raise _error("selected document manifest content reference drifted")
    try:
        manifest = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _error("selected document manifest JSON is invalid") from exc
    if (
        type(manifest) is not dict
        or raw != canonical_json_bytes_v1(manifest) + b"\n"
        or manifest.get("document_manifest_id") != head["document_manifest_id"]
    ):
        raise _error("selected document manifest identity is invalid")
    return head, manifest_path
