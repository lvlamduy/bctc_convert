from __future__ import annotations

import fcntl
import json
import os
import re
import secrets
import stat
import subprocess
import time
from collections import Counter, defaultdict
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from math import isfinite
from pathlib import Path
from typing import Any, BinaryIO

import fitz
import yaml

from bctc_ai.core.hashing import sha256_bytes
from bctc_ai.corpus import wave1_role_b_sentinel as sentinel
from bctc_ai.corpus.wave1_role_b_word_box_normalization import (
    WORD_BOX_NORMALIZATION_POLICY,
    WaveOneRoleBWordBoxNormalizationError,
    model_neutral_result_from_normalized_payload,
    normalization_policy_sha256,
    normalize_ppocrv6_word_boxes,
    validate_normalization_authority,
)
from bctc_ai.ocr.ppocrv6_page_session import validate_ppocrv6_payload
from bctc_ai.rendering.page_reader import (
    public_coordinate_authority,
    render_composited_displayed_page,
)


class WaveOneRoleBFullReaderError(RuntimeError):
    """The authenticated Wave-1 full reader cannot proceed fail-closed."""


POLICY_RELATIVE_PATH = Path("config/corpus/bank-corpus-wave-1-role-b-full-reader-v2.yaml")
POLICY_SHA256 = "20876ed26b7644840e0cc5f9af491edea831866de451ffd089f5301db4e48947"
POLICY_SIZE_BYTES = 8_339
SEALED_PLAN_RELATIVE_PATH = sentinel.SEALED_PLAN_RELATIVE_PATH
SEALED_PLAN_SHA256 = sentinel.SEALED_PLAN_SHA256
SEALED_PLAN_SIZE_BYTES = sentinel.SEALED_PLAN_SIZE_BYTES
PRODUCER_GIT_COMMIT = sentinel.PRODUCER_GIT_COMMIT
EXECUTION_PLAN_SHA256 = sentinel.EXECUTION_PLAN_SHA256
SENTINEL_SHA256 = sentinel.SENTINEL_SHA256
SELECTION_RECEIPT_SHA256 = sentinel.SELECTION_RECEIPT_SHA256
SENTINEL_RELATIVE_ROOT = sentinel.OUTPUT_RELATIVE_ROOT
SENTINEL_AGGREGATE_SHA256 = "75ef770f1d04bed75b83bfd6580d824b61769866e29786aba0bde32de2a62460"
SENTINEL_AGGREGATE_SIZE_BYTES = 33_861
SENTINEL_AGGREGATE_IDENTITY_SHA256 = (
    "a50a2ca136fea3211bd78ca4af9f7149b2a1ddf8776508d9683555d6051b8eea"
)
SENTINEL_CONTROL_SHA256 = "a6884e0d46741ce98af2129528f210ccd3d077f614281826eaf6f8ea0f63b2f2"
SENTINEL_CONTROL_SIZE_BYTES = 47_134
OUTPUT_RELATIVE_ROOT = Path("output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v2")

FULL_READER_IMPLEMENTATION_RELATIVE_PATHS = (
    POLICY_RELATIVE_PATH,
    Path("config/corpus/bank-corpus-wave-1-role-b-page-reader-v1.yaml"),
    Path("config/ocr/causal-native-text-v1.yaml"),
    Path("config/ocr/native-text-quality-v2.yaml"),
    Path("src/bctc_ai/__init__.py"),
    Path("src/bctc_ai/core/__init__.py"),
    Path("src/bctc_ai/core/coordinates.py"),
    Path("src/bctc_ai/core/contracts.py"),
    Path("src/bctc_ai/core/hashing.py"),
    Path("src/bctc_ai/core/text.py"),
    Path("src/bctc_ai/corpus/__init__.py"),
    Path("src/bctc_ai/corpus/wave1_pre_ocr_structure.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_page_reader.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_sentinel.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_word_box_normalization.py"),
    Path("src/bctc_ai/corpus/wave1_role_b_full_reader_v2.py"),
    Path("src/bctc_ai/ocr/__init__.py"),
    Path("src/bctc_ai/ocr/_causal_visibility_core.py"),
    Path("src/bctc_ai/ocr/causal_native_text.py"),
    Path("src/bctc_ai/ocr/causal_native_text_evidence_v1.py"),
    Path("src/bctc_ai/ocr/native_text_quality_v2.py"),
    Path("src/bctc_ai/ocr/pdf_text.py"),
    Path("src/bctc_ai/ocr/ppocrv6_page_session.py"),
    Path("src/bctc_ai/rendering/__init__.py"),
    Path("src/bctc_ai/rendering/page_reader.py"),
    Path("src/bctc_ai/storage/__init__.py"),
    Path("src/bctc_ai/storage/content_store.py"),
    Path("scripts/corpus/run_wave1_role_b_page_reader.py"),
    Path("scripts/models/run_ppocrv6_sentinel_worker.py"),
    Path("scripts/models/run_ppocrv6_wave1_full_worker_v2.py"),
    Path("scripts/corpus/run_wave1_role_b_full_reader_v2.py"),
)

_SHA256 = frozenset("0123456789abcdef")
_OCR_ROUTE = "DOMINANT_RASTER_OCR"
_NATIVE_ROUTE = "CAUSAL_NATIVE_TEXT"
_NATIVE_TERMINAL = frozenset(
    {
        "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
        "UNRESOLVED_NATIVE_TEXT_QUALITY",
    }
)
_COMPLETE_STATUS = "COMPLETE_AUTHENTICATED_WAVE_1_PAGE_READS"
_ZERO_INTERPRETATION = {
    "statement_classification_count": 0,
    "table_classification_count": 0,
    "row_reconstruction_count": 0,
    "cell_interpretation_count": 0,
    "absence_declaration_count": 0,
}


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_sha256(value: Any) -> str:
    return sha256_bytes(_canonical_bytes(value))


def _same_typed_json(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            _same_typed_json(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same_typed_json(a, b) for a, b in zip(left, right, strict=True)
        )
    try:
        return left == right and _canonical_bytes(left) == _canonical_bytes(right)
    except (TypeError, ValueError):
        return False


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256


def _json_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as error:
        raise WaveOneRoleBFullReaderError(f"{label} is invalid JSON") from error
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise WaveOneRoleBFullReaderError(f"{label} is not a canonical JSON object")
    return value


def _stable_bytes(path: Path, label: str) -> bytes:
    try:
        return sentinel._stable_bytes(path, label)  # noqa: SLF001 - authenticated substrate
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error


def _project_path(project_root: Path, relative: str | Path, label: str) -> Path:
    try:
        return sentinel._project_path(  # noqa: SLF001 - authenticated substrate
            project_root, relative, label
        )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error


def _load_policy(project_root: Path) -> dict[str, Any]:
    path = _project_path(project_root, POLICY_RELATIVE_PATH, "full-reader policy")
    payload = _stable_bytes(path, "full-reader policy")
    if len(payload) != POLICY_SIZE_BYTES or sha256_bytes(payload) != POLICY_SHA256:
        raise WaveOneRoleBFullReaderError("full-reader policy byte identity drifted")
    try:
        policy = yaml.safe_load(payload)
    except yaml.YAMLError as error:
        raise WaveOneRoleBFullReaderError("full-reader policy is invalid YAML") from error
    expected_root = {
        "version": 2,
        "policy": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_READER_V2",
        "claim_boundary": ("EXACT_SEALED_WAVE_1_SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_ONLY"),
    }
    expected_keys = {
        *expected_root,
        "sealed_plan",
        "successful_sentinel",
        "sharding",
        "word_box_normalization",
        "worker",
        "native_reader",
        "execution",
        "safety",
        "expected",
        "output",
    }
    if (
        not isinstance(policy, dict)
        or set(policy) != expected_keys
        or any(not _same_typed_json(policy.get(k), v) for k, v in expected_root.items())
        or not _same_typed_json(policy.get("word_box_normalization"), WORD_BOX_NORMALIZATION_POLICY)
    ):
        raise WaveOneRoleBFullReaderError("full-reader policy identity or fields drifted")
    exact = {
        "sealed_plan": {
            "path": SEALED_PLAN_RELATIVE_PATH.as_posix(),
            "sha256": SEALED_PLAN_SHA256,
            "size_bytes": SEALED_PLAN_SIZE_BYTES,
            "producer_git_commit": PRODUCER_GIT_COMMIT,
            "execution_plan_sha256": EXECUTION_PLAN_SHA256,
            "route_plan_sha256": (
                "82b4b387754060419da37a1616336bf32d6a9248945cfc3974b936dbeace609d"
            ),
            "input_ledger_sha256": (
                "7a83f8ff7fa007832578f586b01715a7023e21bc9bf9840f6d4cd301c4df927e"
            ),
            "implementation_ledger_sha256": (
                "694b44b5dfd56324473c85693b634710b910c95bf101d158aadac0a5076a4ec2"
            ),
            "ppocrv6_runtime_model_ledger_sha256": (
                "58049a9bd187b2991716b6c2eac9d33679bb3785027a28dddd20a210e3ea234a"
            ),
            "render_runtime_ledger_sha256": (
                "7850768660fa7aead1d83592e83cde09c8b52e480c5d33b73c40e7f3b837eb80"
            ),
            "causal_native_runtime_ledger_sha256": (
                "57a50855a2669f07b0f9606a59de70f574615cdc490f7130f7bf2e2abce744e0"
            ),
            "sentinel_sha256": SENTINEL_SHA256,
            "selection_receipt_sha256": SELECTION_RECEIPT_SHA256,
        },
        "successful_sentinel": {
            "root": SENTINEL_RELATIVE_ROOT.as_posix(),
            "aggregate_filename": "sentinel-aggregate.json",
            "aggregate_sha256": SENTINEL_AGGREGATE_SHA256,
            "aggregate_size_bytes": SENTINEL_AGGREGATE_SIZE_BYTES,
            "aggregate_identity_sha256": SENTINEL_AGGREGATE_IDENTITY_SHA256,
            "control_filename": "sentinel-execution-control.json",
            "control_sha256": SENTINEL_CONTROL_SHA256,
            "control_size_bytes": SENTINEL_CONTROL_SIZE_BYTES,
            "control_identity_sha256": (
                "6bdc9e2285cf3af62c03a343b7f4e2ba5dc62a4ed4ee78c9d1fea3797ee2e472"
            ),
            "executor_git_commit": "6dc8a5af601901343bec7abb1ef96fb51517ede1",
            "executor_implementation_ledger_sha256": (
                "4d704753e514f1ae6c9ca68628ccb462359089ada03385129629e69a882d442f"
            ),
            "normalization_policy_sha256": (
                "cc7c35d71011541a207c4a6e0ff581142d218cc7392f1d7e7d33d4828a50891c"
            ),
            "adopted_request_count": 24,
            "copied_object_count": 72,
            "required_status": "COMPLETE_AUTHENTICATED_WAVE_1_24_PAGE_OCR_SENTINEL",
        },
        "expected": {
            "document_count": 27,
            "request_count": 1449,
            "ocr_request_count": 1356,
            "native_request_count": 93,
            "sentinel_adopted_ocr_request_count": 24,
            "remaining_ocr_request_count": 1332,
            "shard_count": 2,
            "remaining_ocr_requests_per_shard": [665, 667],
            "remaining_ocr_documents_per_shard": [13, 13],
            **_ZERO_INTERPRETATION,
        },
        "output": {
            "root": OUTPUT_RELATIVE_ROOT.as_posix(),
            "control_filename": "full-reader-execution-control.json",
            "object_directory": "objects",
            "checkpoint_directory": "checkpoints",
            "document_index_directory": "documents",
            "lock_directory": "locks",
            "runtime_directory": "runtime",
            "upstream_directory": "upstream",
            "aggregate_filename": "full-reader-aggregate.json",
            "canonical_json": True,
            "exclusive_no_overwrite": True,
        },
    }
    if any(not _same_typed_json(policy.get(k), v) for k, v in exact.items()):
        raise WaveOneRoleBFullReaderError("full-reader anchored policy section drifted")
    expected_safety = {
        "production_authentication_bypass_allowed": False,
        "injectable_production_worker_allowed": False,
        "injectable_production_provider_allowed": False,
        "test_output_can_publish_production_status": False,
        "bank_registry_metadata_allowed_in_execution_decisions": False,
        "filename_metadata_allowed_in_execution_decisions": False,
        "role_a_inputs_allowed": False,
        "schema_inputs_allowed": False,
        "mapping_inputs_allowed": False,
        "historical_values_allowed": False,
        "source_visible_text_preserved_verbatim": True,
        "semantic_interpretation_allowed": False,
        "absence_declarations_allowed": False,
    }
    if not _same_typed_json(policy.get("safety"), expected_safety):
        raise WaveOneRoleBFullReaderError("full-reader safety policy drifted")
    adapter = policy["native_reader"]
    adapter_bytes = _stable_bytes(
        _project_path(project_root, adapter["evidence_adapter_path"], "native evidence adapter"),
        "native evidence adapter",
    )
    if sha256_bytes(adapter_bytes) != adapter["evidence_adapter_sha256"]:
        raise WaveOneRoleBFullReaderError("native evidence adapter byte identity drifted")
    try:
        normalization_policy_sha256(policy["word_box_normalization"])
    except RuntimeError as error:
        raise WaveOneRoleBFullReaderError("normalization policy drifted") from error
    return policy


def _implementation_ledger(project_root: Path, commit: str) -> dict[str, Any]:
    try:
        return sentinel._implementation_ledger(  # noqa: SLF001 - authenticated substrate
            project_root, commit, FULL_READER_IMPLEMENTATION_RELATIVE_PATHS
        )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error


def _authenticate_plan(
    project_root: Path,
    model_cache: Path,
    *,
    require_clean_executor: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    project_root = project_root.resolve()
    policy = _load_policy(project_root)
    try:
        sealed, _sentinel_policy, authority = sentinel._authenticate_sealed_plan(  # noqa: SLF001
            project_root,
            model_cache.resolve(),
            require_clean_executor=require_clean_executor,
        )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    expected_anchors = {
        "route_plan_sha256": ("82b4b387754060419da37a1616336bf32d6a9248945cfc3974b936dbeace609d"),
        "input_ledger_sha256": ("7a83f8ff7fa007832578f586b01715a7023e21bc9bf9840f6d4cd301c4df927e"),
        "execution_plan_sha256": EXECUTION_PLAN_SHA256,
        "sentinel_sha256": SENTINEL_SHA256,
        "selection_receipt_sha256": SELECTION_RECEIPT_SHA256,
    }
    if any(sealed.get(key) != value for key, value in expected_anchors.items()):
        raise WaveOneRoleBFullReaderError("sealed plan anchor drifted")
    ledger_anchors = {
        "implementation_ledger": (
            "694b44b5dfd56324473c85693b634710b910c95bf101d158aadac0a5076a4ec2"
        ),
        "ppocrv6_runtime_model_ledger": (
            "58049a9bd187b2991716b6c2eac9d33679bb3785027a28dddd20a210e3ea234a"
        ),
        "render_runtime_ledger": (
            "7850768660fa7aead1d83592e83cde09c8b52e480c5d33b73c40e7f3b837eb80"
        ),
        "causal_native_runtime_ledger": (
            "57a50855a2669f07b0f9606a59de70f574615cdc490f7130f7bf2e2abce744e0"
        ),
    }
    if any(sealed.get(key, {}).get("sha256") != value for key, value in ledger_anchors.items()):
        raise WaveOneRoleBFullReaderError("sealed runtime or implementation ledger drifted")
    native = sealed["causal_native_runtime_ledger"]
    expected_native = {
        "provider": "PYMUPDF_CAUSAL_NATIVE_TEXT_VISIBILITY_V1",
        "pymupdf_distribution_version": "1.28.0",
        "pymupdf_binding_version": "1.28.0",
        "pymupdf_runtime_versions": ["1.28.0", "1.29.0", None],
        "config_records": [
            {
                "path": "config/ocr/causal-native-text-v1.yaml",
                "sha256": ("4c6df806a7ded7d7a6c5241f1c523c7b9cbbf24829332293d8aa783a3044d647"),
                "size_bytes": 876,
            },
            {
                "path": "config/ocr/native-text-quality-v2.yaml",
                "sha256": ("af0d735ea026abc7b189da46d36f103d1390687325324ecc1a325ba6ab51a660"),
                "size_bytes": 596,
            },
        ],
        "ocr_fallback_allowed": False,
        "sha256": ledger_anchors["causal_native_runtime_ledger"],
    }
    if not _same_typed_json(native, expected_native):
        raise WaveOneRoleBFullReaderError("sealed causal native runtime ledger drifted")
    ledger = _implementation_ledger(project_root, authority["git"]["commit"])
    return sealed, policy, {"git": authority["git"], "implementation_ledger": ledger}


def _full_request_records(sealed: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    ordinal = 0
    seen: set[str] = set()
    for document in sorted(sealed.get("documents", []), key=lambda item: item["document_id"]):
        document_id = document.get("document_id")
        if document_id != f"sha256:{document.get('sha256')}":
            raise WaveOneRoleBFullReaderError("sealed document identity drifted")
        pages = document.get("pages")
        if not isinstance(pages, list) or len(pages) != document.get("page_count"):
            raise WaveOneRoleBFullReaderError("sealed document page accounting drifted")
        request_hashes = []
        for page in sorted(pages, key=lambda item: item["page"]):
            ordinal += 1
            request = page.get("request")
            request_sha = page.get("request_sha256")
            route = page.get("route")
            if (
                route not in {_OCR_ROUTE, _NATIVE_ROUTE}
                or not isinstance(request, dict)
                or _canonical_sha256(request) != request_sha
                or request_sha in seen
                or request.get("route") != route
                or request.get("source_sha256") != document["sha256"]
                or request.get("source_size_bytes") != document["size_bytes"]
                or request.get("physical_page") != page.get("page")
                or request.get("bank_identity_used") is not False
                or request.get("filename_used") is not False
                or request.get("role_a_used") is not False
                or request.get("schema_used") is not False
                or request.get("historical_values_used") is not False
            ):
                raise WaveOneRoleBFullReaderError("sealed page request identity drifted")
            seen.add(request_sha)
            request_hashes.append(request_sha)
            records.append(
                {
                    "request_ordinal": ordinal,
                    "document_id": document_id,
                    "source_sha256": document["sha256"],
                    "source_size_bytes": document["size_bytes"],
                    "physical_page": page["page"],
                    "route": route,
                    "request_sha256": request_sha,
                    "request": request,
                }
            )
        if _canonical_sha256(request_hashes) != document.get("request_set_sha256"):
            raise WaveOneRoleBFullReaderError("sealed document request set drifted")
    if len(records) != 1449 or ordinal != 1449:
        raise WaveOneRoleBFullReaderError("sealed full request count drifted")
    if Counter(record["route"] for record in records) != {
        _OCR_ROUTE: 1356,
        _NATIVE_ROUTE: 93,
    }:
        raise WaveOneRoleBFullReaderError("sealed route request counts drifted")
    return records


def _sentinel_request_hashes(sealed: dict[str, Any]) -> list[str]:
    by_document = {
        document["document_id"]: {page["page"]: page for page in document["pages"]}
        for document in sealed["documents"]
    }
    hashes = []
    for selection in sorted(sealed["sentinel"], key=lambda item: item["sentinel_ordinal"]):
        page = by_document[selection["document_id"]][selection["page"]]
        if page["route"] != _OCR_ROUTE or selection["route"] != _OCR_ROUTE:
            raise WaveOneRoleBFullReaderError("sealed sentinel route drifted")
        hashes.append(page["request_sha256"])
    if len(hashes) != 24 or len(set(hashes)) != 24:
        raise WaveOneRoleBFullReaderError("sealed sentinel request set drifted")
    return hashes


def _assign_remaining_ocr_shards(
    records: list[dict[str, Any]], sentinel_hashes: set[str]
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record["route"] == _OCR_ROUTE and record["request_sha256"] not in sentinel_hashes:
            grouped[record["document_id"]].append(record)
    shards = [
        {"shard_id": 0, "document_ids": [], "requests": []},
        {"shard_id": 1, "document_ids": [], "requests": []},
    ]
    for document_id in sorted(grouped, key=lambda key: (-len(grouped[key]), key)):
        shard = min(shards, key=lambda item: (len(item["requests"]), item["shard_id"]))
        shard["document_ids"].append(document_id)
        shard["requests"].extend(
            sorted(grouped[document_id], key=lambda item: item["request_ordinal"])
        )
    for shard in shards:
        shard["document_ids"].sort()
        shard["requests"].sort(key=lambda item: item["request_ordinal"])
        shard["document_count"] = len(shard["document_ids"])
        shard["request_count"] = len(shard["requests"])
        shard["request_set_sha256"] = _canonical_sha256(
            [record["request_sha256"] for record in shard["requests"]]
        )
        if any(record["document_id"] not in shard["document_ids"] for record in shard["requests"]):
            raise WaveOneRoleBFullReaderError("whole-document shard accounting drifted")
    if [item["request_count"] for item in shards] != [665, 667] or [
        item["document_count"] for item in shards
    ] != [13, 13]:
        raise WaveOneRoleBFullReaderError("remaining OCR LPT shard projection drifted")
    if set(shards[0]["document_ids"]) & set(shards[1]["document_ids"]):
        raise WaveOneRoleBFullReaderError("one document was split across OCR shards")
    return shards


def _control_index(control: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = [page for document in control["documents"] for page in document["pages"]]
    index = {record["request_sha256"]: record for record in records}
    if len(records) != 1449 or len(index) != 1449:
        raise WaveOneRoleBFullReaderError("full control request index drifted")
    return index


def _normalization_authority(control: dict[str, Any]) -> dict[str, Any]:
    contract = control.get("word_box_normalization")
    implementation = control.get("executor_implementation_ledger")
    if (
        not isinstance(contract, dict)
        or set(contract)
        != {
            "policy",
            "policy_sha256",
            "normalization_producer_implementation_ledger_sha256",
        }
        or not isinstance(implementation, dict)
        or contract["normalization_producer_implementation_ledger_sha256"]
        != implementation.get("sha256")
    ):
        raise WaveOneRoleBFullReaderError("normalization authority binding drifted")
    try:
        return validate_normalization_authority(
            {**contract, "control_identity_sha256": control.get("control_identity_sha256")}
        )
    except RuntimeError as error:
        raise WaveOneRoleBFullReaderError("normalization authority failed validation") from error


def build_authenticated_control(project_root: Path, *, model_cache: Path) -> dict[str, Any]:
    """Build the only production control; authentication and providers are not injectable."""

    sealed, policy, executor = _authenticate_plan(
        project_root.resolve(), model_cache.resolve(), require_clean_executor=True
    )
    records = _full_request_records(sealed)
    sentinel_hashes = _sentinel_request_hashes(sealed)
    shards = _assign_remaining_ocr_shards(records, set(sentinel_hashes))
    documents = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["document_id"]].append(record)
    for document_id in sorted(grouped):
        pages = []
        for record in sorted(grouped[document_id], key=lambda item: item["request_ordinal"]):
            pages.append(
                {
                    key: record[key]
                    for key in (
                        "request_ordinal",
                        "document_id",
                        "source_sha256",
                        "source_size_bytes",
                        "physical_page",
                        "route",
                        "request_sha256",
                        "request",
                    )
                }
            )
        documents.append(
            {
                "document_id": document_id,
                "source_sha256": pages[0]["source_sha256"],
                "source_size_bytes": pages[0]["source_size_bytes"],
                "request_count": len(pages),
                "request_set_sha256": _canonical_sha256([page["request_sha256"] for page in pages]),
                "pages": pages,
            }
        )
    control = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_READER_CONTROL_V2",
        "status": "READY_FOR_AUTHENTICATED_WAVE_1_FULL_PAGE_READ",
        "claim_boundary": policy["claim_boundary"],
        "sealed_plan": policy["sealed_plan"],
        "successful_sentinel": policy["successful_sentinel"],
        "executor_git": executor["git"],
        "executor_implementation_ledger": executor["implementation_ledger"],
        "word_box_normalization": {
            "policy": policy["word_box_normalization"],
            "policy_sha256": normalization_policy_sha256(policy["word_box_normalization"]),
            "normalization_producer_implementation_ledger_sha256": executor[
                "implementation_ledger"
            ]["sha256"],
        },
        "worker_contract": policy["worker"],
        "native_reader_contract": policy["native_reader"],
        "sharding": {
            "algorithm": policy["sharding"]["algorithm"],
            "document_split_allowed": False,
            "bank_identity_used": False,
            "filename_used": False,
            "sentinel_requests_excluded_before_assignment": True,
            "shards": shards,
        },
        "sentinel_request_sha256s": sentinel_hashes,
        "documents": documents,
        "accounting": policy["expected"],
        "safety": {
            "source_locator_excluded_from_control": True,
            "bank_registry_metadata_used": False,
            "filename_metadata_used": False,
            "role_a_used": False,
            "schema_used": False,
            "mapping_used": False,
            "historical_values_used": False,
            "semantic_interpretation_attempted": False,
            "absence_claimed": False,
            "source_visible_text_preserved_verbatim": True,
        },
    }
    control["control_identity_sha256"] = _canonical_sha256(control)
    _normalization_authority(control)
    return control


def _publish_exclusive(project_root: Path, directory: Path, filename: str, payload: bytes) -> Path:
    try:
        return sentinel._publish_exclusive(  # noqa: SLF001 - link-safe publication substrate
            project_root, directory, filename, payload
        )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error


def _put_object(project_root: Path, payload: bytes, *, suffix: str) -> dict[str, Any]:
    if suffix not in {".json", ".png"}:
        raise WaveOneRoleBFullReaderError("full-reader object suffix is not allowed")
    digest = sha256_bytes(payload)
    relative_directory = OUTPUT_RELATIVE_ROOT / "objects" / "sha256" / digest[:2]
    path = _publish_exclusive(
        project_root,
        relative_directory,
        f"{digest}{suffix}",
        payload,
    )
    return {
        "path": path.relative_to(project_root / OUTPUT_RELATIVE_ROOT).as_posix(),
        "sha256": digest,
        "size_bytes": len(payload),
    }


def _read_ref_from_root(
    project_root: Path,
    output_root: Path,
    reference: dict[str, Any],
    suffix: str,
) -> tuple[bytes, os.stat_result]:
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256", "size_bytes"}:
        raise WaveOneRoleBFullReaderError("object reference fields drifted")
    digest = reference.get("sha256")
    size = reference.get("size_bytes")
    expected_path = f"objects/sha256/{str(digest)[:2]}/{digest}{suffix}"
    if (
        not _is_sha256(digest)
        or isinstance(size, bool)
        or not isinstance(size, int)
        or size < 0
        or reference.get("path") != expected_path
    ):
        raise WaveOneRoleBFullReaderError("object reference identity is malformed")
    relative_directory = output_root / "objects" / "sha256" / digest[:2]
    try:
        with sentinel._held_directory(  # noqa: SLF001 - link-safe held hierarchy
            project_root, relative_directory, create=False
        ) as (_directory, directory_fd):
            payload, identity = sentinel._hash_open_at(  # noqa: SLF001
                directory_fd, f"{digest}{suffix}"
            )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    if (
        len(payload) != size
        or sha256_bytes(payload) != digest
        or stat.S_IMODE(identity.st_mode) != 0o444
        or identity.st_nlink != 1
    ):
        raise WaveOneRoleBFullReaderError("content-addressed object identity drifted")
    return payload, identity


def _read_object(project_root: Path, reference: dict[str, Any], suffix: str) -> bytes:
    return _read_ref_from_root(project_root, OUTPUT_RELATIVE_ROOT, reference, suffix)[0]


def _copy_sentinel_object(
    project_root: Path, reference: dict[str, Any], suffix: str
) -> dict[str, Any]:
    payload, source_before = _read_ref_from_root(
        project_root, SENTINEL_RELATIVE_ROOT, reference, suffix
    )
    source_identity = (
        source_before.st_dev,
        source_before.st_ino,
        source_before.st_size,
        source_before.st_mtime_ns,
        stat.S_IMODE(source_before.st_mode),
        source_before.st_nlink,
    )
    copied = _put_object(project_root, payload, suffix=suffix)
    copied_payload, destination = _read_ref_from_root(
        project_root, OUTPUT_RELATIVE_ROOT, copied, suffix
    )
    source_after_payload, source_after = _read_ref_from_root(
        project_root, SENTINEL_RELATIVE_ROOT, reference, suffix
    )
    source_after_identity = (
        source_after.st_dev,
        source_after.st_ino,
        source_after.st_size,
        source_after.st_mtime_ns,
        stat.S_IMODE(source_after.st_mode),
        source_after.st_nlink,
    )
    if (
        copied != reference
        or copied_payload != payload
        or source_after_payload != payload
        or source_after_identity != source_identity
        or (destination.st_dev, destination.st_ino) == (source_before.st_dev, source_before.st_ino)
        or destination.st_nlink != 1
        or stat.S_IMODE(destination.st_mode) != 0o444
    ):
        raise WaveOneRoleBFullReaderError(
            "sentinel object was not copied to an independent immutable inode"
        )
    return copied


def _read_successful_sentinel(
    project_root: Path,
    sealed: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    try:
        with sentinel._held_directory(  # noqa: SLF001
            project_root, SENTINEL_RELATIVE_ROOT, create=False
        ) as (_directory, directory_fd):
            aggregate_payload, aggregate_stat = sentinel._hash_open_at(  # noqa: SLF001
                directory_fd, "sentinel-aggregate.json"
            )
            control_payload, control_stat = sentinel._hash_open_at(  # noqa: SLF001
                directory_fd, "sentinel-execution-control.json"
            )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    if (
        len(aggregate_payload) != SENTINEL_AGGREGATE_SIZE_BYTES
        or sha256_bytes(aggregate_payload) != SENTINEL_AGGREGATE_SHA256
        or len(control_payload) != SENTINEL_CONTROL_SIZE_BYTES
        or sha256_bytes(control_payload) != SENTINEL_CONTROL_SHA256
        or stat.S_IMODE(aggregate_stat.st_mode) != 0o444
        or aggregate_stat.st_nlink != 1
        or stat.S_IMODE(control_stat.st_mode) != 0o444
        or control_stat.st_nlink != 1
    ):
        raise WaveOneRoleBFullReaderError("successful sentinel byte identity drifted")
    aggregate = _json_object(aggregate_payload, "successful sentinel aggregate")
    control = _json_object(control_payload, "successful sentinel control")
    if (
        aggregate.get("status") != "COMPLETE_AUTHENTICATED_WAVE_1_24_PAGE_OCR_SENTINEL"
        or aggregate.get("aggregate_identity_sha256") != SENTINEL_AGGREGATE_IDENTITY_SHA256
        or _canonical_sha256(
            {key: value for key, value in aggregate.items() if key != "aggregate_identity_sha256"}
        )
        != SENTINEL_AGGREGATE_IDENTITY_SHA256
        or control.get("control_identity_sha256")
        != "6bdc9e2285cf3af62c03a343b7f4e2ba5dc62a4ed4ee78c9d1fea3797ee2e472"
        or aggregate.get("control", {}).get("identity_sha256")
        != control.get("control_identity_sha256")
        or aggregate.get("executor_git", {}).get("commit")
        != "6dc8a5af601901343bec7abb1ef96fb51517ede1"
        or aggregate.get("executor_implementation_ledger", {}).get("sha256")
        != "4d704753e514f1ae6c9ca68628ccb462359089ada03385129629e69a882d442f"
        or aggregate.get("word_box_normalization", {}).get("policy_sha256")
        != "cc7c35d71011541a207c4a6e0ff581142d218cc7392f1d7e7d33d4828a50891c"
        or aggregate.get("accounting", {}).get("request_count") != 24
        or aggregate.get("accounting", {}).get("complete_result_count") != 24
        or aggregate.get("accounting", {}).get("unresolved_count") != 0
    ):
        raise WaveOneRoleBFullReaderError("successful sentinel logical identity drifted")
    _validate_historical_sentinel_ledger(project_root, aggregate, control)
    try:
        sentinel_records = sentinel._sentinel_request_records(sealed)  # noqa: SLF001
        renders = sentinel._render_exact_sentinel_sources(  # noqa: SLF001
            project_root, sealed, control, require_existing=True
        )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    expected_by_sha = {record["request_sha256"]: record for record in sentinel_records}
    results = aggregate.get("results")
    if not isinstance(results, list) or len(results) != 24:
        raise WaveOneRoleBFullReaderError("successful sentinel result list drifted")
    result_by_sha: dict[str, dict[str, Any]] = {}
    for result in results:
        request_sha = result.get("request_sha256") if isinstance(result, dict) else None
        expected = expected_by_sha.get(request_sha)
        render = renders.get(request_sha)
        if expected is None or render is None or request_sha in result_by_sha:
            raise WaveOneRoleBFullReaderError("successful sentinel request set drifted")
        try:
            sentinel._validate_result_record(  # noqa: SLF001
                project_root, control, result, expected, render
            )
        except sentinel.WaveOneRoleBSentinelError as error:
            raise WaveOneRoleBFullReaderError(str(error)) from error
        result_by_sha[request_sha] = result
    if set(result_by_sha) != set(expected_by_sha):
        raise WaveOneRoleBFullReaderError("successful sentinel is not request-complete")
    return aggregate, control, result_by_sha


def _git_blob(project_root: Path, commit: str, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        raise WaveOneRoleBFullReaderError(
            f"historical sentinel implementation is absent: {relative}"
        )
    return result.stdout


def _validate_historical_sentinel_ledger(
    project_root: Path, aggregate: dict[str, Any], control: dict[str, Any]
) -> None:
    commit = "6dc8a5af601901343bec7abb1ef96fb51517ede1"
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=project_root,
        check=False,
    )
    if ancestor.returncode:
        raise WaveOneRoleBFullReaderError("successful sentinel executor commit is not an ancestor")
    ledger = aggregate.get("executor_implementation_ledger")
    if (
        not isinstance(ledger, dict)
        or set(ledger) != {"records", "sha256"}
        or ledger.get("sha256")
        != "4d704753e514f1ae6c9ca68628ccb462359089ada03385129629e69a882d442f"
        or not _same_typed_json(ledger, control.get("executor_implementation_ledger"))
        or _canonical_sha256(ledger.get("records")) != ledger.get("sha256")
    ):
        raise WaveOneRoleBFullReaderError("historical sentinel ledger identity drifted")
    records = ledger["records"]
    if not isinstance(records, list) or len(records) != len(
        sentinel.MILESTONE_B_IMPLEMENTATION_RELATIVE_PATHS
    ):
        raise WaveOneRoleBFullReaderError("historical sentinel ledger cardinality drifted")
    expected_paths = {
        path.as_posix() for path in sentinel.MILESTONE_B_IMPLEMENTATION_RELATIVE_PATHS
    }
    if {record.get("path") for record in records if isinstance(record, dict)} != expected_paths:
        raise WaveOneRoleBFullReaderError("historical sentinel ledger path set drifted")
    for record in records:
        if (
            not isinstance(record, dict)
            or set(record) != {"phase", "kind", "path", "sha256", "size_bytes"}
            or record["phase"] != "READ"
            or record["kind"] != "IMPLEMENTATION"
            or not _is_sha256(record["sha256"])
            or isinstance(record["size_bytes"], bool)
            or not isinstance(record["size_bytes"], int)
            or record["size_bytes"] < 0
        ):
            raise WaveOneRoleBFullReaderError("historical sentinel ledger record drifted")
        historical = _git_blob(project_root, commit, record["path"])
        if len(historical) != record["size_bytes"] or sha256_bytes(historical) != record["sha256"]:
            raise WaveOneRoleBFullReaderError(
                "historical sentinel Git blob differs from sealed ledger"
            )
        current = _stable_bytes(
            _project_path(project_root, record["path"], "current sentinel substrate"),
            "current sentinel substrate",
        )
        if current != historical:
            raise WaveOneRoleBFullReaderError(
                "imported sentinel validation substrate differs from historical executor"
            )


def _publish_upstream_sentinel_copies(
    project_root: Path, aggregate: dict[str, Any], control: dict[str, Any]
) -> None:
    _publish_exclusive(
        project_root,
        OUTPUT_RELATIVE_ROOT / "upstream",
        "sentinel-aggregate.json",
        _canonical_bytes(aggregate),
    )
    _publish_exclusive(
        project_root,
        OUTPUT_RELATIVE_ROOT / "upstream",
        "sentinel-execution-control.json",
        _canonical_bytes(control),
    )


def _safe_result_safety() -> dict[str, bool]:
    return {
        "statement_classified": False,
        "table_classified": False,
        "rows_reconstructed": False,
        "cells_interpreted": False,
        "absence_claimed": False,
        "bank_registry_metadata_used": False,
        "filename_metadata_used": False,
        "role_a_used": False,
        "schema_used": False,
        "mapping_used": False,
        "historical_values_used": False,
    }


def _page_record(
    expected: dict[str, Any],
    *,
    status: str,
    origin: str,
    render_ref: dict[str, Any] | None,
    backend_payload_ref: dict[str, Any],
    result_ref: dict[str, Any],
    line_count: int,
    word_token_count: int,
    unresolved: bool,
    quarantined_span_count: int = 0,
    word_box_correction_count: int = 0,
    word_box_corrected_edge_count: int = 0,
) -> dict[str, Any]:
    return {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V1",
        "request_ordinal": expected["request_ordinal"],
        "document_id": expected["document_id"],
        "source_sha256": expected["source_sha256"],
        "source_size_bytes": expected["source_size_bytes"],
        "physical_page": expected["physical_page"],
        "route": expected["route"],
        "request_sha256": expected["request_sha256"],
        "request": expected["request"],
        "status": status,
        "origin": origin,
        "render_ref": render_ref,
        "backend_payload_ref": backend_payload_ref,
        "result_ref": result_ref,
        "line_count": line_count,
        "word_token_count": word_token_count,
        "unresolved": unresolved,
        "quarantined_span_count": quarantined_span_count,
        "word_box_correction_count": word_box_correction_count,
        "word_box_corrected_edge_count": word_box_corrected_edge_count,
        "statement_classification_count": 0,
        "table_classification_count": 0,
        "row_reconstruction_count": 0,
        "cell_interpretation_count": 0,
        "absence_declaration_count": 0,
    }


def _adopt_successful_sentinel(
    project_root: Path,
    control: dict[str, Any],
    sentinel_results: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    index = _control_index(control)
    adopted = []
    copied_refs: set[tuple[str, str]] = set()
    for request_sha in control["sentinel_request_sha256s"]:
        expected = index[request_sha]
        source = sentinel_results.get(request_sha)
        if source is None or expected["route"] != _OCR_ROUTE:
            raise WaveOneRoleBFullReaderError("sentinel adoption request drifted")
        for key, suffix in (
            ("render_ref", ".png"),
            ("backend_payload_ref", ".json"),
            ("result_ref", ".json"),
        ):
            ref = source[key]
            copied = _copy_sentinel_object(project_root, ref, suffix)
            if copied != ref:
                raise WaveOneRoleBFullReaderError("sentinel copied reference drifted")
            copied_refs.add((suffix, ref["sha256"]))
        adopted.append(
            _page_record(
                expected,
                status=source["status"],
                origin="AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY",
                render_ref=source["render_ref"],
                backend_payload_ref=source["backend_payload_ref"],
                result_ref=source["result_ref"],
                line_count=source["line_count"],
                word_token_count=source["word_token_count"],
                unresolved=False,
                word_box_correction_count=source["word_box_correction_count"],
                word_box_corrected_edge_count=source["word_box_corrected_edge_count"],
            )
        )
    if len(adopted) != 24 or len(copied_refs) != 72:
        raise WaveOneRoleBFullReaderError("sentinel copied object accounting drifted")
    return sorted(adopted, key=lambda item: item["request_ordinal"])


def _read_only_adopted_sentinel_records(
    project_root: Path,
    control: dict[str, Any],
    sentinel_results: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    index = _control_index(control)
    adopted = []
    seen_objects = set()
    for request_sha in control["sentinel_request_sha256s"]:
        expected = index[request_sha]
        source = sentinel_results[request_sha]
        for key, suffix in (
            ("render_ref", ".png"),
            ("backend_payload_ref", ".json"),
            ("result_ref", ".json"),
        ):
            source_payload, source_stat = _read_ref_from_root(
                project_root, SENTINEL_RELATIVE_ROOT, source[key], suffix
            )
            copied_payload, copied_stat = _read_ref_from_root(
                project_root, OUTPUT_RELATIVE_ROOT, source[key], suffix
            )
            if copied_payload != source_payload or (copied_stat.st_dev, copied_stat.st_ino) == (
                source_stat.st_dev,
                source_stat.st_ino,
            ):
                raise WaveOneRoleBFullReaderError("standalone sentinel object copy drifted")
            seen_objects.add((suffix, source[key]["sha256"]))
        adopted.append(
            _page_record(
                expected,
                status=source["status"],
                origin="AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY",
                render_ref=source["render_ref"],
                backend_payload_ref=source["backend_payload_ref"],
                result_ref=source["result_ref"],
                line_count=source["line_count"],
                word_token_count=source["word_token_count"],
                unresolved=False,
                word_box_correction_count=source["word_box_correction_count"],
                word_box_corrected_edge_count=source["word_box_corrected_edge_count"],
            )
        )
    if len(adopted) != 24 or len(seen_objects) != 72:
        raise WaveOneRoleBFullReaderError("read-only sentinel adoption accounting drifted")
    return sorted(adopted, key=lambda item: item["request_ordinal"])


def _validate_nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise WaveOneRoleBFullReaderError(f"{label} is not a nonnegative integer")
    return value


def _restore_in_memory_coordinate_authority(public: Any) -> dict[str, Any]:
    if not isinstance(public, dict):
        raise WaveOneRoleBFullReaderError("public coordinate authority is malformed")
    authority = deepcopy(public)
    for public_key, private_key in (
        ("pixel_to_unrotated_mpt", "_pixel_to_unrotated_matrix"),
        ("unrotated_mpt_to_pixel", "_unrotated_to_pixel_matrix"),
    ):
        matrix = public.get(public_key)
        if (
            not isinstance(matrix, list)
            or len(matrix) != 3
            or any(not isinstance(row, list) or len(row) != 3 for row in matrix)
        ):
            raise WaveOneRoleBFullReaderError("coordinate matrix shape drifted")
        restored = []
        for row in matrix:
            restored_row = []
            for coefficient in row:
                if (
                    not isinstance(coefficient, dict)
                    or set(coefficient) != {"numerator", "denominator"}
                    or type(coefficient["numerator"]) is not int
                    or type(coefficient["denominator"]) is not int
                    or coefficient["denominator"] <= 0
                ):
                    raise WaveOneRoleBFullReaderError("coordinate rational coefficient drifted")
                restored_row.append((coefficient["numerator"], coefficient["denominator"]))
            restored.append(tuple(restored_row))
        authority[private_key] = tuple(restored)
    return authority


def _validate_ocr_result(
    project_root: Path,
    control: dict[str, Any],
    record: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    render_ref = record["render_ref"]
    if render_ref is None:
        raise WaveOneRoleBFullReaderError("OCR page lacks a render reference")
    _read_object(project_root, render_ref, ".png")
    backend = _json_object(
        _read_object(project_root, record["backend_payload_ref"], ".json"),
        "OCR backend payload",
    )
    result = _json_object(
        _read_object(project_root, record["result_ref"], ".json"),
        "OCR page result",
    )
    if (
        set(backend)
        != {
            "format_version",
            "claim_boundary",
            "request_sha256",
            "request",
            "provider_identity_sha256",
            "render_ref",
            "raw_provider_payload",
            "word_box_normalization_ledger",
        }
        or backend.get("format_version") != "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V2"
        or backend.get("claim_boundary")
        != (
            "RAW_PINNED_PROVIDER_PAYLOAD_AND_BOUND_WORD_BOX_NORMALIZATION_LEDGER_"
            "FOR_ONE_EXACT_PAGE_REQUEST_ONLY"
        )
        or backend.get("request_sha256") != expected["request_sha256"]
        or not _same_typed_json(backend.get("request"), expected["request"])
        or not _same_typed_json(backend.get("render_ref"), render_ref)
        or backend.get("provider_identity_sha256")
        != expected["request"]["provider_identity_sha256"]
    ):
        raise WaveOneRoleBFullReaderError("OCR backend request identity drifted")
    if (
        set(result)
        != {
            "format_version",
            "status",
            "claim_boundary",
            "request_sha256",
            "request",
            "source_sha256",
            "source_size_bytes",
            "physical_page",
            "route",
            "provider_identity_sha256",
            "render_runtime_identity_sha256",
            "input_render_ref",
            "backend_payload_ref",
            "word_box_normalization_ledger",
            "coordinate_authority",
            "lines",
            "words",
            "metrics",
            "source_blank_claimed",
            "safety",
        }
        or result.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2"
        or result.get("claim_boundary") != "SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY"
        or result.get("status") != "OCR_WORD_BOX_READ_COMPLETE"
        or result.get("request_sha256") != expected["request_sha256"]
        or not _same_typed_json(result.get("request"), expected["request"])
        or result.get("source_sha256") != expected["source_sha256"]
        or result.get("source_size_bytes") != expected["source_size_bytes"]
        or result.get("physical_page") != expected["physical_page"]
        or result.get("route") != _OCR_ROUTE
        or result.get("provider_identity_sha256") != expected["request"]["provider_identity_sha256"]
        or result.get("render_runtime_identity_sha256")
        != expected["request"]["render_runtime_identity_sha256"]
        or not _same_typed_json(result.get("input_render_ref"), render_ref)
        or not _same_typed_json(result.get("backend_payload_ref"), record["backend_payload_ref"])
        or result.get("source_blank_claimed") is not False
        or not _same_typed_json(result.get("safety"), _safe_result_safety())
    ):
        raise WaveOneRoleBFullReaderError("OCR model-neutral result identity drifted")
    pixel_dimensions = result.get("coordinate_authority", {}).get("pixel_dimensions")
    if (
        not isinstance(pixel_dimensions, list)
        or len(pixel_dimensions) != 2
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in pixel_dimensions
        )
    ):
        raise WaveOneRoleBFullReaderError("OCR pixel dimensions drifted")
    raw_payload = backend.get("raw_provider_payload")
    if not isinstance(raw_payload, dict):
        raise WaveOneRoleBFullReaderError("OCR raw provider payload is absent")
    if record["origin"] == "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY":
        ledger = backend.get("word_box_normalization_ledger")
        if not isinstance(ledger, dict):
            raise WaveOneRoleBFullReaderError("sentinel normalization ledger is absent")
        normalized, replay = normalize_ppocrv6_word_boxes(
            raw_payload,
            pixel_width=pixel_dimensions[0],
            pixel_height=pixel_dimensions[1],
            authority={
                "policy": WORD_BOX_NORMALIZATION_POLICY,
                "policy_sha256": (
                    "cc7c35d71011541a207c4a6e0ff581142d218cc7392f1d7e7d33d4828a50891c"
                ),
                "normalization_producer_implementation_ledger_sha256": (
                    "4d704753e514f1ae6c9ca68628ccb462359089ada03385129629e69a882d442f"
                ),
                "control_identity_sha256": (
                    "6bdc9e2285cf3af62c03a343b7f4e2ba5dc62a4ed4ee78c9d1fea3797ee2e472"
                ),
            },
        )
    else:
        normalized, replay = normalize_ppocrv6_word_boxes(
            raw_payload,
            pixel_width=pixel_dimensions[0],
            pixel_height=pixel_dimensions[1],
            authority=_normalization_authority(control),
        )
        ledger = backend.get("word_box_normalization_ledger")
    if not _same_typed_json(ledger, replay) or not _same_typed_json(
        result.get("word_box_normalization_ledger"), replay
    ):
        raise WaveOneRoleBFullReaderError("OCR normalization replay drifted")
    counts = validate_ppocrv6_payload(
        normalized,
        pixel_width=pixel_dimensions[0],
        pixel_height=pixel_dimensions[1],
    )
    neutral = model_neutral_result_from_normalized_payload(
        normalized,
        coordinate_authority=_restore_in_memory_coordinate_authority(
            result["coordinate_authority"]
        ),
    )
    for key in ("status", "coordinate_authority", "lines", "words", "metrics"):
        if not _same_typed_json(result.get(key), neutral.get(key)):
            raise WaveOneRoleBFullReaderError("OCR deterministic projection drifted")
    if (
        counts["line_count"] != record["line_count"]
        or counts["word_token_count"] != record["word_token_count"]
        or replay["correction_count"] != record["word_box_correction_count"]
        or replay["corrected_edge_count"] != record["word_box_corrected_edge_count"]
    ):
        raise WaveOneRoleBFullReaderError("OCR record accounting drifted")


def _validate_unresolved_ocr_geometry(
    project_root: Path,
    control: dict[str, Any],
    record: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    render_ref = record["render_ref"]
    if render_ref is None:
        raise WaveOneRoleBFullReaderError("unresolved OCR page lacks its render")
    _read_object(project_root, render_ref, ".png")
    backend = _json_object(
        _read_object(project_root, record["backend_payload_ref"], ".json"),
        "unresolved OCR backend",
    )
    result = _json_object(
        _read_object(project_root, record["result_ref"], ".json"),
        "unresolved OCR result",
    )
    backend_keys = {
        "format_version",
        "claim_boundary",
        "request_sha256",
        "request",
        "provider_identity_sha256",
        "render_ref",
        "raw_provider_payload",
        "word_box_normalization_ledger",
        "normalization_failure",
    }
    result_keys = {
        "format_version",
        "status",
        "claim_boundary",
        "request_sha256",
        "request",
        "source_sha256",
        "source_size_bytes",
        "physical_page",
        "route",
        "provider_identity_sha256",
        "render_runtime_identity_sha256",
        "input_render_ref",
        "backend_payload_ref",
        "normalization_failure",
        "coordinate_authority",
        "lines",
        "words",
        "metrics",
        "ocr_fallback_used",
        "source_blank_claimed",
        "safety",
    }
    if (
        set(backend) != backend_keys
        or backend.get("format_version") != "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V3"
        or backend.get("claim_boundary")
        != "RAW_PINNED_PROVIDER_PAYLOAD_WITH_TERMINAL_BOUNDED_WORD_BOX_GEOMETRY_FAILURE"
        or backend.get("request_sha256") != expected["request_sha256"]
        or not _same_typed_json(backend.get("request"), expected["request"])
        or not _same_typed_json(backend.get("render_ref"), render_ref)
        or backend.get("provider_identity_sha256")
        != expected["request"]["provider_identity_sha256"]
        or backend.get("word_box_normalization_ledger") is not None
        or set(result) != result_keys
        or result.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3"
        or result.get("claim_boundary")
        != "SOURCE_VISIBLE_PAGE_RAW_OCR_EVIDENCE_WITH_UNRESOLVED_GEOMETRY"
        or result.get("status") != "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
        or result.get("request_sha256") != expected["request_sha256"]
        or not _same_typed_json(result.get("request"), expected["request"])
        or result.get("source_sha256") != expected["source_sha256"]
        or result.get("source_size_bytes") != expected["source_size_bytes"]
        or result.get("physical_page") != expected["physical_page"]
        or result.get("route") != _OCR_ROUTE
        or result.get("provider_identity_sha256") != expected["request"]["provider_identity_sha256"]
        or result.get("render_runtime_identity_sha256")
        != expected["request"]["render_runtime_identity_sha256"]
        or not _same_typed_json(result.get("input_render_ref"), render_ref)
        or not _same_typed_json(result.get("backend_payload_ref"), record["backend_payload_ref"])
        or not _same_typed_json(
            result.get("normalization_failure"), backend.get("normalization_failure")
        )
        or result.get("lines") != []
        or result.get("words") != []
        or result.get("metrics") != {"line_count": 0, "word_token_count": 0}
        or result.get("ocr_fallback_used") is not False
        or result.get("source_blank_claimed") is not False
        or not _same_typed_json(result.get("safety"), _safe_result_safety())
    ):
        raise WaveOneRoleBFullReaderError("unresolved OCR evidence envelope drifted")
    raw = backend.get("raw_provider_payload")
    dimensions = result.get("coordinate_authority", {}).get("pixel_dimensions")
    if not isinstance(raw, dict) or not isinstance(dimensions, list) or len(dimensions) != 2:
        raise WaveOneRoleBFullReaderError("unresolved OCR raw geometry authority drifted")
    _validate_ppocrv6_schema_except_word_geometry(
        raw, pixel_width=dimensions[0], pixel_height=dimensions[1]
    )
    try:
        normalize_ppocrv6_word_boxes(
            raw,
            pixel_width=dimensions[0],
            pixel_height=dimensions[1],
            authority=_normalization_authority(control),
        )
    except WaveOneRoleBWordBoxNormalizationError:
        pass
    else:
        raise WaveOneRoleBFullReaderError("unresolved OCR geometry is actually normalizable")
    expected_failure = {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_NORMALIZATION_FAILURE_V1",
        "status": "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        "reason": "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED",
        "policy_sha256": control["word_box_normalization"]["policy_sha256"],
        "control_identity_sha256": control["control_identity_sha256"],
        "normalization_producer_implementation_ledger_sha256": control["word_box_normalization"][
            "normalization_producer_implementation_ledger_sha256"
        ],
        "pixel_dimensions": dimensions,
        "raw_payload_sha256": _canonical_sha256(raw),
    }
    if not _same_typed_json(backend.get("normalization_failure"), expected_failure):
        raise WaveOneRoleBFullReaderError("unresolved OCR failure ledger drifted")
    if any(
        record[key] != value
        for key, value in (
            ("line_count", 0),
            ("word_token_count", 0),
            ("word_box_correction_count", 0),
            ("word_box_corrected_edge_count", 0),
        )
    ):
        raise WaveOneRoleBFullReaderError("unresolved OCR page counters drifted")


def _validate_native_result(
    project_root: Path,
    control: dict[str, Any],
    record: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    if record["render_ref"] is not None:
        raise WaveOneRoleBFullReaderError("native page unexpectedly has an OCR render")
    backend = _json_object(
        _read_object(project_root, record["backend_payload_ref"], ".json"),
        "causal native backend payload",
    )
    result = _json_object(
        _read_object(project_root, record["result_ref"], ".json"),
        "causal native page result",
    )
    from bctc_ai.ocr.causal_native_text_evidence_v1 import (  # noqa: PLC0415
        _validate_observed_envelopes,
        _validate_provider_runtime_ledger,
    )

    try:
        _validate_observed_envelopes(backend, result, physical_page=expected["physical_page"])
    except RuntimeError as error:
        raise WaveOneRoleBFullReaderError(
            "causal native closed evidence validation failed"
        ) from error
    native_contract = control["native_reader_contract"]
    try:
        provider_ledger, _causal_bytes, _quality_bytes, causal_identity, quality_identity = (
            _validate_provider_runtime_ledger(
                backend.get("provider_runtime_ledger"),
                causal_policy_path=_project_path(
                    project_root,
                    native_contract["policy_path"],
                    "causal native policy",
                ),
                quality_policy_path=_project_path(
                    project_root,
                    native_contract["quality_policy_path"],
                    "native quality policy",
                ),
            )
        )
    except RuntimeError as error:
        raise WaveOneRoleBFullReaderError(
            "causal native provider/config identity failed validation"
        ) from error
    if (
        provider_ledger.get("sha256") != expected["request"]["provider_identity_sha256"]
        or not _same_typed_json(backend.get("causal_native_policy_identity"), causal_identity)
        or not _same_typed_json(
            backend.get("native_text_quality_policy_identity"), quality_identity
        )
    ):
        raise WaveOneRoleBFullReaderError("causal native provider binding drifted")
    backend_keys = {
        "format_version",
        "status",
        "claim_boundary",
        "document_id",
        "source_sha256",
        "source_size_bytes",
        "physical_page",
        "route",
        "request_sha256",
        "request",
        "full_control_identity_sha256",
        "provider_identity_sha256",
        "provider_runtime_ledger",
        "causal_native_policy_identity",
        "native_text_quality_policy_identity",
        "coordinate_authority",
        "causal_native_payload",
        "ocr_fallback_used",
        "source_blank_claimed",
        "safety",
    }
    result_keys = {
        "format_version",
        "status",
        "claim_boundary",
        "document_id",
        "source_sha256",
        "source_size_bytes",
        "physical_page",
        "route",
        "request_sha256",
        "request",
        "full_control_identity_sha256",
        "provider_identity_sha256",
        "backend_payload_sha256",
        "coordinate_authority",
        "failure_type",
        "native_text_quality",
        "corruption_markers",
        "lines",
        "words",
        "quarantined_spans",
        "metrics",
        "ocr_fallback_used",
        "source_blank_claimed",
        "safety",
    }
    if (
        set(backend) != backend_keys
        or backend.get("format_version") != "BANK_CORPUS_WAVE_1_CAUSAL_NATIVE_BACKEND_PAYLOAD_V1"
        or backend.get("claim_boundary")
        != "AUTHENTICATED_SEALED_CAUSAL_NATIVE_WRAPPER_OUTPUT_FOR_ONE_EXACT_PAGE_REQUEST_ONLY"
        or set(result) != result_keys
        or backend.get("request_sha256") != expected["request_sha256"]
        or not _same_typed_json(backend.get("request"), expected["request"])
        or backend.get("provider_identity_sha256")
        != expected["request"]["provider_identity_sha256"]
        or backend.get("document_id") != expected["document_id"]
        or backend.get("source_sha256") != expected["source_sha256"]
        or backend.get("source_size_bytes") != expected["source_size_bytes"]
        or backend.get("physical_page") != expected["physical_page"]
        or backend.get("route") != _NATIVE_ROUTE
        or backend.get("full_control_identity_sha256") != control["control_identity_sha256"]
        or backend.get("ocr_fallback_used") is not False
        or backend.get("source_blank_claimed") is not False
        or result.get("format_version")
        != "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V1"
        or result.get("claim_boundary")
        != "SOURCE_VISIBLE_NATIVE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY"
        or result.get("request_sha256") != expected["request_sha256"]
        or not _same_typed_json(result.get("request"), expected["request"])
        or result.get("document_id") != expected["document_id"]
        or result.get("source_sha256") != expected["source_sha256"]
        or result.get("source_size_bytes") != expected["source_size_bytes"]
        or result.get("physical_page") != expected["physical_page"]
        or result.get("status") not in _NATIVE_TERMINAL
        or result.get("status") != record["status"]
        or result.get("route") != _NATIVE_ROUTE
        or result.get("full_control_identity_sha256") != control["control_identity_sha256"]
        or result.get("provider_identity_sha256") != expected["request"]["provider_identity_sha256"]
        or result.get("backend_payload_sha256") != record["backend_payload_ref"]["sha256"]
        or result.get("ocr_fallback_used") is not False
        or result.get("source_blank_claimed") is not False
        or not _same_typed_json(result.get("safety"), _safe_result_safety())
    ):
        raise WaveOneRoleBFullReaderError("causal native result identity drifted")
    raw = backend.get("causal_native_payload")
    if not isinstance(raw, dict):
        raise WaveOneRoleBFullReaderError("causal native payload is absent")
    expected_projection = {
        "status": raw.get("status"),
        "failure_type": raw.get("failure_type"),
        "native_text_quality": raw.get("native_text_quality"),
        "corruption_markers": raw.get("corruption_markers"),
        "lines": raw.get("lines"),
        "words": raw.get("words"),
        "quarantined_spans": raw.get("quarantined_spans"),
        "ocr_fallback_used": raw.get("ocr_fallback_used"),
        "source_blank_claimed": raw.get("source_blank_claimed"),
    }
    observed_projection = {key: result.get(key) for key in expected_projection}
    if not _same_typed_json(observed_projection, expected_projection):
        raise WaveOneRoleBFullReaderError("causal native deterministic projection drifted")
    lines = raw.get("lines")
    words = raw.get("words")
    if not isinstance(lines, list) or not isinstance(words, list):
        raise WaveOneRoleBFullReaderError("causal native text arrays drifted")
    expected_metrics = {
        "line_count": len(lines),
        "word_token_count": len(words),
        "quarantined_span_count": len(raw.get("quarantined_spans", [])),
    }
    if (
        not _same_typed_json(result.get("metrics"), expected_metrics)
        or len(lines) != record["line_count"]
        or len(words) != record["word_token_count"]
        or expected_metrics["quarantined_span_count"] != record["quarantined_span_count"]
    ):
        raise WaveOneRoleBFullReaderError("causal native record accounting drifted")


def _validate_page_record(
    project_root: Path,
    control: dict[str, Any],
    record: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    required = {
        "format_version",
        "request_ordinal",
        "document_id",
        "source_sha256",
        "source_size_bytes",
        "physical_page",
        "route",
        "request_sha256",
        "request",
        "status",
        "origin",
        "render_ref",
        "backend_payload_ref",
        "result_ref",
        "line_count",
        "word_token_count",
        "unresolved",
        "quarantined_span_count",
        "word_box_correction_count",
        "word_box_corrected_edge_count",
        *_ZERO_INTERPRETATION,
    }
    if not isinstance(record, dict) or set(record) != required:
        raise WaveOneRoleBFullReaderError("full page record fields drifted")
    for key in (
        "request_ordinal",
        "source_size_bytes",
        "physical_page",
        "line_count",
        "word_token_count",
        "quarantined_span_count",
        "word_box_correction_count",
        "word_box_corrected_edge_count",
        *_ZERO_INTERPRETATION,
    ):
        _validate_nonnegative_int(record[key], f"page record {key}")
    if (
        record["format_version"] != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V1"
        or any(
            not _same_typed_json(record.get(key), expected.get(key))
            for key in (
                "request_ordinal",
                "document_id",
                "source_sha256",
                "source_size_bytes",
                "physical_page",
                "route",
                "request_sha256",
                "request",
            )
        )
        or any(record[key] != 0 for key in _ZERO_INTERPRETATION)
        or not isinstance(record["unresolved"], bool)
    ):
        raise WaveOneRoleBFullReaderError("full page record request identity drifted")
    if record["route"] == _OCR_ROUTE:
        if (
            record["status"]
            not in {"OCR_WORD_BOX_READ_COMPLETE", "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"}
            or record["unresolved"] != (record["status"] == "UNRESOLVED_OCR_WORD_BOX_GEOMETRY")
            or record["origin"]
            not in {
                "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY",
                "PINNED_PPOCRV6_FULL_READER",
            }
            or record["quarantined_span_count"] != 0
        ):
            raise WaveOneRoleBFullReaderError("OCR page outcome drifted")
        if record["status"] == "OCR_WORD_BOX_READ_COMPLETE":
            _validate_ocr_result(project_root, control, record, expected)
        else:
            _validate_unresolved_ocr_geometry(project_root, control, record, expected)
    elif record["route"] == _NATIVE_ROUTE:
        if (
            record["status"] not in _NATIVE_TERMINAL
            or record["unresolved"] != (record["status"] != "CAUSAL_NATIVE_TEXT_READ_COMPLETE")
            or record["origin"] != "SEALED_CAUSAL_NATIVE_TEXT_GATE"
            or record["word_box_correction_count"] != 0
            or record["word_box_corrected_edge_count"] != 0
        ):
            raise WaveOneRoleBFullReaderError("native page outcome drifted")
        _validate_native_result(project_root, control, record, expected)
    else:
        raise WaveOneRoleBFullReaderError("full page route drifted")


def _checkpoint_payload(
    control: dict[str, Any],
    document_id: str,
    record: dict[str, Any],
    generation: int,
    previous_sha256: str | None,
) -> dict[str, Any]:
    return {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_DELTA_CHECKPOINT_V1",
        "status": "COMPLETE_ONE_AUTHENTICATED_PAGE_REQUEST",
        "claim_boundary": "ONE_EXACT_SEALED_PAGE_REQUEST_ACCOUNTING_ONLY",
        "sealed_plan_sha256": SEALED_PLAN_SHA256,
        "control_identity_sha256": control["control_identity_sha256"],
        "document_id": document_id,
        "source_sha256": document_id.removeprefix("sha256:"),
        "generation": generation,
        "previous_checkpoint_sha256": previous_sha256,
        "page_record": record,
    }


def _document_completion_order(control: dict[str, Any], document_id: str) -> list[str]:
    sentinel_hashes = set(control["sentinel_request_sha256s"])
    matches = [
        document for document in control["documents"] if document["document_id"] == document_id
    ]
    if len(matches) != 1:
        raise WaveOneRoleBFullReaderError("completion-order document identity drifted")
    pages = matches[0]["pages"]
    stages = (
        [page for page in pages if page["request_sha256"] in sentinel_hashes],
        [
            page
            for page in pages
            if page["route"] == _OCR_ROUTE and page["request_sha256"] not in sentinel_hashes
        ],
        [page for page in pages if page["route"] == _NATIVE_ROUTE],
    )
    ordered = [
        page["request_sha256"]
        for stage in stages
        for page in sorted(stage, key=lambda item: item["request_ordinal"])
    ]
    if len(ordered) != len(pages) or len(set(ordered)) != len(pages):
        raise WaveOneRoleBFullReaderError("completion-order request accounting drifted")
    return ordered


def _publish_checkpoint(
    project_root: Path,
    control: dict[str, Any],
    document_id: str,
    record: dict[str, Any],
    generation: int,
    previous_sha256: str | None,
) -> str:
    checkpoint = _checkpoint_payload(control, document_id, record, generation, previous_sha256)
    payload = _canonical_bytes(checkpoint)
    digest = sha256_bytes(payload)
    _publish_exclusive(
        project_root,
        OUTPUT_RELATIVE_ROOT / "checkpoints" / document_id.removeprefix("sha256:"),
        f"{generation:04d}-{digest}.json",
        payload,
    )
    return digest


def _load_document_checkpoints(
    project_root: Path,
    control: dict[str, Any],
    document_id: str,
    *,
    recover_temporaries: bool = True,
) -> tuple[list[dict[str, Any]], str | None]:
    relative = OUTPUT_RELATIVE_ROOT / "checkpoints" / document_id.removeprefix("sha256:")
    try:
        context = sentinel._held_directory(  # noqa: SLF001
            project_root, relative, create=False
        )
        _directory, directory_fd = context.__enter__()
    except sentinel.WaveOneRoleBSentinelError as error:
        if "is absent" in str(error):
            return [], None
        raise WaveOneRoleBFullReaderError(str(error)) from error
    try:
        if recover_temporaries:
            try:
                sentinel._recover_owned_hardlink_temporaries(directory_fd)  # noqa: SLF001
            except sentinel.WaveOneRoleBSentinelError as error:
                raise WaveOneRoleBFullReaderError(str(error)) from error
        raw_names = sorted(os.listdir(directory_fd))
        grammar = re.compile(r"^(?P<generation>[0-9]{4})-(?P<sha>[0-9a-f]{64})\.json$")
        interrupted = re.compile(r"^\.[0-9]{4}-[0-9a-f]{64}\.json\.[0-9a-f]{32}\.tmp$")
        names = []
        for name in raw_names:
            if interrupted.fullmatch(name):
                temporary = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if (
                    not stat.S_ISREG(temporary.st_mode)
                    or stat.S_IMODE(temporary.st_mode) not in {0o600, 0o444}
                    or temporary.st_nlink != 1
                ):
                    raise WaveOneRoleBFullReaderError(
                        "interrupted checkpoint temporary is not safely quarantinable"
                    )
                continue
            names.append(name)
        if any(grammar.fullmatch(name) is None for name in names):
            raise WaveOneRoleBFullReaderError("checkpoint directory has a foreign entry")
        expected_index = {
            page["request_sha256"]: page
            for document in control["documents"]
            if document["document_id"] == document_id
            for page in document["pages"]
        }
        records = []
        previous = None
        seen = set()
        completion_order = _document_completion_order(control, document_id)
        for generation, name in enumerate(names, start=1):
            match = grammar.fullmatch(name)
            assert match is not None
            try:
                payload, identity = sentinel._hash_open_at(directory_fd, name)  # noqa: SLF001
            except sentinel.WaveOneRoleBSentinelError as error:
                raise WaveOneRoleBFullReaderError(str(error)) from error
            digest = sha256_bytes(payload)
            checkpoint = _json_object(payload, "page delta checkpoint")
            record = checkpoint.get("page_record")
            expected = expected_index.get(
                record.get("request_sha256") if isinstance(record, dict) else None
            )
            if (
                int(match.group("generation")) != generation
                or match.group("sha") != digest
                or stat.S_IMODE(identity.st_mode) != 0o444
                or identity.st_nlink != 1
                or expected is None
                or record["request_sha256"] in seen
                or record["request_sha256"] != completion_order[generation - 1]
                or not _same_typed_json(
                    checkpoint,
                    _checkpoint_payload(control, document_id, record, generation, previous),
                )
            ):
                raise WaveOneRoleBFullReaderError("page delta checkpoint chain drifted")
            _validate_page_record(project_root, control, record, expected)
            seen.add(record["request_sha256"])
            records.append(record)
            previous = digest
        return records, previous
    finally:
        context.__exit__(None, None, None)


def _append_checkpoint(
    project_root: Path,
    control: dict[str, Any],
    records_by_document: dict[str, list[dict[str, Any]]],
    heads_by_document: dict[str, str | None],
    record: dict[str, Any],
) -> None:
    document_id = record["document_id"]
    records = records_by_document[document_id]
    if any(item["request_sha256"] == record["request_sha256"] for item in records):
        raise WaveOneRoleBFullReaderError("page request is already checkpointed")
    order = _document_completion_order(control, document_id)
    if len(records) >= len(order) or record["request_sha256"] != order[len(records)]:
        raise WaveOneRoleBFullReaderError(
            "page checkpoint violates deterministic per-document stage order"
        )
    _validate_page_record(
        project_root, control, record, _control_index(control)[record["request_sha256"]]
    )
    generation = len(records) + 1
    head = _publish_checkpoint(
        project_root,
        control,
        document_id,
        record,
        generation,
        heads_by_document[document_id],
    )
    records.append(record)
    heads_by_document[document_id] = head


@contextmanager
def _execution_lease(project_root: Path) -> Iterator[int]:
    relative = OUTPUT_RELATIVE_ROOT / "locks"
    try:
        context = sentinel._held_directory(  # noqa: SLF001
            project_root, relative, create=True
        )
        _directory, directory_fd = context.__enter__()
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    descriptor = -1
    try:
        descriptor = os.open(
            "full-reader-execution.lease",
            os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=directory_fd,
        )
        before = os.fstat(descriptor)
        named = os.stat("full-reader-execution.lease", dir_fd=directory_fd, follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
            or before.st_size != 0
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
        ):
            raise WaveOneRoleBFullReaderError("global execution lease identity drifted")
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        try:
            acquired = os.fstat(descriptor)
            named_acquired = os.stat(
                "full-reader-execution.lease",
                dir_fd=directory_fd,
                follow_symlinks=False,
            )
        except OSError as error:
            raise WaveOneRoleBFullReaderError(
                "global execution lease changed while acquiring the lock"
            ) from error
        if (
            not stat.S_ISREG(acquired.st_mode)
            or stat.S_IMODE(acquired.st_mode) != 0o600
            or acquired.st_nlink != 1
            or acquired.st_size != 0
            or (acquired.st_dev, acquired.st_ino) != (before.st_dev, before.st_ino)
            or (named_acquired.st_dev, named_acquired.st_ino) != (before.st_dev, before.st_ino)
        ):
            raise WaveOneRoleBFullReaderError(
                "global execution lease changed while acquiring the lock"
            )
        yield descriptor
        after = os.fstat(descriptor)
        named_after = os.stat(
            "full-reader-execution.lease", dir_fd=directory_fd, follow_symlinks=False
        )
        if (
            not stat.S_ISREG(after.st_mode)
            or stat.S_IMODE(after.st_mode) != 0o600
            or after.st_nlink != 1
            or after.st_size != 0
            or (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino)
            or (named_after.st_dev, named_after.st_ino) != (before.st_dev, before.st_ino)
        ):
            raise WaveOneRoleBFullReaderError("held execution lease changed")
    finally:
        if descriptor >= 0:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)
        context.__exit__(None, None, None)


@contextmanager
def _document_locks(project_root: Path, document_ids: list[str]) -> Iterator[None]:
    relative = OUTPUT_RELATIVE_ROOT / "locks" / "documents"
    try:
        context = sentinel._held_directory(  # noqa: SLF001
            project_root, relative, create=True
        )
        _directory, directory_fd = context.__enter__()
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    held: list[tuple[str, int, tuple[int, int]]] = []
    try:
        for document_id in sorted(set(document_ids)):
            source_sha = document_id.removeprefix("sha256:")
            if not _is_sha256(source_sha):
                raise WaveOneRoleBFullReaderError("document lock identity is malformed")
            name = f"{source_sha}.lock"
            descriptor = os.open(
                name,
                os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=directory_fd,
            )
            identity = os.fstat(descriptor)
            named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if (
                not stat.S_ISREG(identity.st_mode)
                or stat.S_IMODE(identity.st_mode) != 0o600
                or identity.st_nlink != 1
                or identity.st_size != 0
                or (identity.st_dev, identity.st_ino) != (named.st_dev, named.st_ino)
            ):
                os.close(descriptor)
                raise WaveOneRoleBFullReaderError("document lock identity drifted")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                try:
                    acquired = os.fstat(descriptor)
                    named_acquired = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                except OSError as error:
                    raise WaveOneRoleBFullReaderError(
                        "document lock changed while acquiring the lock"
                    ) from error
                if (
                    not stat.S_ISREG(acquired.st_mode)
                    or stat.S_IMODE(acquired.st_mode) != 0o600
                    or acquired.st_nlink != 1
                    or acquired.st_size != 0
                    or (acquired.st_dev, acquired.st_ino) != (identity.st_dev, identity.st_ino)
                    or (named_acquired.st_dev, named_acquired.st_ino)
                    != (identity.st_dev, identity.st_ino)
                ):
                    raise WaveOneRoleBFullReaderError(
                        "document lock changed while acquiring the lock"
                    )
            except BaseException:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)
                raise
            held.append((name, descriptor, (identity.st_dev, identity.st_ino)))
        yield
    finally:
        cleanup_error = None
        for name, descriptor, expected in reversed(held):
            observed = os.fstat(descriptor)
            try:
                named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                named = None
            if cleanup_error is None and (
                named is None
                or (observed.st_dev, observed.st_ino) != expected
                or (named.st_dev, named.st_ino) != expected
                or not stat.S_ISREG(observed.st_mode)
                or observed.st_size != 0
                or stat.S_IMODE(observed.st_mode) != 0o600
                or observed.st_nlink != 1
            ):
                cleanup_error = WaveOneRoleBFullReaderError("held document lock changed")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)
        context.__exit__(None, None, None)
        if cleanup_error is not None:
            raise cleanup_error


def _sealed_documents(sealed: dict[str, Any]) -> dict[str, dict[str, Any]]:
    documents = {document["document_id"]: document for document in sealed.get("documents", [])}
    if len(documents) != 27:
        raise WaveOneRoleBFullReaderError("sealed document index drifted")
    return documents


def _source_payload(project_root: Path, document: dict[str, Any]) -> tuple[Path, bytes]:
    path = _project_path(
        project_root, document["relative_path"], "receipt-bound selected source PDF"
    )
    payload = _stable_bytes(path, "receipt-bound selected source PDF")
    if (
        len(payload) != document["size_bytes"]
        or sha256_bytes(payload) != document["sha256"]
        or document["document_id"] != f"sha256:{document['sha256']}"
    ):
        raise WaveOneRoleBFullReaderError("receipt-bound source PDF identity drifted")
    return path, payload


def _render_missing_ocr_requests(
    project_root: Path,
    sealed: dict[str, Any],
    missing: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in missing:
        if record["route"] != _OCR_ROUTE:
            raise WaveOneRoleBFullReaderError("non-OCR request reached the render stage")
        grouped[record["document_id"]].append(record)
    documents = _sealed_documents(sealed)
    renders: dict[str, dict[str, Any]] = {}
    for document_id in sorted(grouped):
        document = documents[document_id]
        source_path, payload = _source_payload(project_root, document)
        try:
            pdf = fitz.open(stream=payload, filetype="pdf")
        except Exception as error:
            raise WaveOneRoleBFullReaderError("source PDF cannot be opened") from error
        try:
            if pdf.page_count != document["page_count"]:
                raise WaveOneRoleBFullReaderError("source PDF page count drifted")
            for expected in sorted(grouped[document_id], key=lambda item: item["request_ordinal"]):
                specification = expected["request"].get("render_specification")
                if specification not in (
                    {
                        "source": "FULL_COMPOSITED_DISPLAYED_PDF_PAGE",
                        "dpi": 200,
                        "colorspace": "RGB",
                        "alpha": False,
                        "annotations": "INCLUDED",
                    },
                    {
                        "source": "FULL_COMPOSITED_DISPLAYED_PDF_PAGE",
                        "dpi": 300,
                        "colorspace": "RGB",
                        "alpha": False,
                        "annotations": "INCLUDED",
                    },
                ):
                    raise WaveOneRoleBFullReaderError("sealed render specification drifted")
                page = pdf.load_page(expected["physical_page"] - 1)
                rendered = render_composited_displayed_page(page, dpi=specification["dpi"])
                reference = _put_object(project_root, rendered.payload, suffix=".png")
                renders[expected["request_sha256"]] = {
                    "ref": reference,
                    "pixel_width": rendered.pixel_width,
                    "pixel_height": rendered.pixel_height,
                    "dpi": rendered.dpi,
                    "coordinate_authority": rendered.coordinate_authority,
                }
        finally:
            pdf.close()
        if _stable_bytes(source_path, "receipt-bound selected source PDF") != payload:
            raise WaveOneRoleBFullReaderError("source PDF changed during rendering")
    if set(renders) != {record["request_sha256"] for record in missing}:
        raise WaveOneRoleBFullReaderError("OCR render accounting drifted")
    return renders


def _ensure_capacity(project_root: Path, minimum_bytes: int) -> None:
    descriptor = os.open(
        project_root,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        filesystem = os.fstatvfs(descriptor)
        available = filesystem.f_bavail * filesystem.f_frsize
    finally:
        os.close(descriptor)
    if available < minimum_bytes:
        raise WaveOneRoleBFullReaderError(
            f"full reader requires {minimum_bytes} free bytes; found {available}"
        )


def _create_runtime_root(project_root: Path, execution_nonce: str) -> Path:
    if not _is_sha256(execution_nonce):
        raise WaveOneRoleBFullReaderError("runtime execution nonce is malformed")
    root_relative = OUTPUT_RELATIVE_ROOT / "runtime" / f"execution-{execution_nonce}"
    try:
        with sentinel._held_directory(  # noqa: SLF001
            project_root, OUTPUT_RELATIVE_ROOT / "runtime", create=True
        ) as (_directory, directory_fd):
            try:
                os.mkdir(f"execution-{execution_nonce}", 0o700, dir_fd=directory_fd)
                os.fsync(directory_fd)
            except FileExistsError as error:
                raise WaveOneRoleBFullReaderError("runtime nonce already exists") from error
        for shard_id in (0, 1):
            for relative in (
                Path(f"shard-{shard_id}/inputs"),
                Path(f"shard-{shard_id}/responses"),
                Path(f"shard-{shard_id}/environment/home"),
                Path(f"shard-{shard_id}/environment/.paddlex-cache"),
                Path(f"shard-{shard_id}/environment/xdg-cache"),
                Path(f"shard-{shard_id}/environment/xdg-config"),
                Path(f"shard-{shard_id}/environment/xdg-data"),
                Path(f"shard-{shard_id}/environment/tmp"),
            ):
                with sentinel._held_directory(  # noqa: SLF001
                    project_root, root_relative / relative, create=True
                ):
                    pass
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    return project_root / root_relative


def _worker_environment(
    project_root: Path,
    runtime_root: Path,
    policy: dict[str, Any],
    shard_id: int,
) -> dict[str, str]:
    environment_root = runtime_root / f"shard-{shard_id}" / "environment"
    environment = dict(policy["worker"]["environment"])
    environment["PADDLE_PDX_CACHE_HOME"] = (environment_root / ".paddlex-cache").as_posix()
    for key, relative in policy["worker"]["isolated_runtime_directories"].items():
        environment[key] = (environment_root / relative).as_posix()
    for key, value in policy["worker"]["supervisor_environment"].items():
        if key == "PATH":
            first, *remaining = value.split(":")
            environment[key] = ":".join(
                [_project_path(project_root, first, "worker PATH").as_posix(), *remaining]
            )
        else:
            environment[key] = value
    expected_keys = {
        "PADDLE_PDX_CACHE_HOME",
        "PADDLE_PDX_MODEL_SOURCE",
        "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK",
        "FLAGS_allocator_strategy",
        "OMP_NUM_THREADS",
        "PYTHONHASHSEED",
        "PYTHONNOUSERSITE",
        "HOME",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "TMPDIR",
        "LANG",
        "LC_ALL",
        "PYTHONUTF8",
        "PYTHONCOERCECLOCALE",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONSAFEPATH",
        "PATH",
    }
    if set(environment) != expected_keys or "PYTHONPATH" in environment:
        raise WaveOneRoleBFullReaderError("worker environment allowlist drifted")
    return dict(sorted(environment.items()))


def _materialize_private_inputs(
    project_root: Path,
    runtime_root: Path,
    shard_id: int,
    requests: list[dict[str, Any]],
    renders: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    relative = runtime_root.relative_to(project_root) / f"shard-{shard_id}" / "inputs"
    materialized = {}
    for request in requests:
        request_sha = request["request_sha256"]
        render = renders[request_sha]
        payload = _read_object(project_root, render["ref"], ".png")
        path = _publish_exclusive(project_root, relative, f"{request_sha}.png", payload)
        source_payload, source_stat = _read_ref_from_root(
            project_root, OUTPUT_RELATIVE_ROOT, render["ref"], ".png"
        )
        private_stat = path.stat(follow_symlinks=False)
        if (
            source_payload != payload
            or stat.S_IMODE(private_stat.st_mode) != 0o444
            or private_stat.st_nlink != 1
            or (private_stat.st_dev, private_stat.st_ino)
            == (source_stat.st_dev, source_stat.st_ino)
        ):
            raise WaveOneRoleBFullReaderError("private provider input copy drifted")
        materialized[request_sha] = {
            "path": path.as_posix(),
            "sha256": render["ref"]["sha256"],
            "size_bytes": render["ref"]["size_bytes"],
        }
    return materialized


def _worker_model_contract(
    project_root: Path, model_cache: Path, sealed: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        return sentinel._worker_model_contract(  # noqa: SLF001 - sealed model ledger adapter
            project_root, model_cache, sealed
        )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error


def _build_worker_task(
    project_root: Path,
    model_cache: Path,
    sealed: dict[str, Any],
    control: dict[str, Any],
    shard_id: int,
    requests: list[dict[str, Any]],
    renders: dict[str, dict[str, Any]],
    private_inputs: dict[str, dict[str, Any]],
    execution_nonce: str,
    environment: dict[str, str],
    execution_lease_fd: int,
) -> dict[str, Any]:
    if not 1 <= len(requests) <= 128:
        raise WaveOneRoleBFullReaderError("worker batch exceeds the 128-page session cap")
    configuration, models = _worker_model_contract(project_root, model_cache, sealed)
    lease = os.fstat(execution_lease_fd)
    if (
        not stat.S_ISREG(lease.st_mode)
        or stat.S_IMODE(lease.st_mode) != 0o600
        or lease.st_nlink != 1
        or lease.st_size != 0
    ):
        raise WaveOneRoleBFullReaderError("inherited execution lease identity drifted")
    page_tasks = []
    for request in sorted(requests, key=lambda item: item["request_ordinal"]):
        request_sha = request["request_sha256"]
        render = renders[request_sha]
        private = private_inputs[request_sha]
        expected_path = (
            project_root
            / OUTPUT_RELATIVE_ROOT
            / "runtime"
            / f"execution-{execution_nonce}"
            / f"shard-{shard_id}"
            / "inputs"
            / f"{request_sha}.png"
        )
        if (
            private["path"] != expected_path.as_posix()
            or private["sha256"] != render["ref"]["sha256"]
            or private["size_bytes"] != render["ref"]["size_bytes"]
        ):
            raise WaveOneRoleBFullReaderError("worker private input binding drifted")
        page_tasks.append(
            {
                "request_sha256": request_sha,
                "render_sha256": render["ref"]["sha256"],
                "render_size_bytes": render["ref"]["size_bytes"],
                "image_path": private["path"],
                "pixel_width": render["pixel_width"],
                "pixel_height": render["pixel_height"],
                "response_filename": f"{request_sha}.response.json",
            }
        )
    return {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_FULL_WORKER_TASK_V2",
        "protocol": "EXCLUSIVE_CANONICAL_JSON_RESPONSE_FILES_WITH_PUBLICATION_STATE_V2",
        "execution_nonce": execution_nonce,
        "shard_id": shard_id,
        "provider_identity_sha256": sealed["ppocrv6_runtime_model_ledger"]["sha256"],
        "word_box_normalization_authority": _normalization_authority(control),
        "cpu_threads": 6,
        "expected_environment": environment,
        "execution_lease": {
            "fd": execution_lease_fd,
            "device": lease.st_dev,
            "inode": lease.st_ino,
        },
        "configuration": configuration,
        "models": models,
        "max_request_count": 128,
        "requests": page_tasks,
    }


def _validate_ppocrv6_schema_except_word_geometry(
    payload: dict[str, Any], *, pixel_width: int, pixel_height: int
) -> dict[str, int]:
    """Validate every strict PP field while replacing only finite positive word boxes."""

    if not isinstance(payload, dict):
        raise WaveOneRoleBFullReaderError("raw PP-OCR payload is not an object")
    required_axes = (
        "rec_texts",
        "rec_scores",
        "rec_polys",
        "rec_boxes",
        "text_word_boxes",
        "text_word",
    )
    if payload.get("return_word_box") is not True or any(
        not isinstance(payload.get(key), list) for key in required_axes
    ):
        raise WaveOneRoleBFullReaderError(
            "raw PP-OCR payload is not schema-valid before geometry normalization"
        )
    counts = {key: len(payload[key]) for key in required_axes}
    if len(set(counts.values())) != 1:
        raise WaveOneRoleBFullReaderError("raw PP-OCR line axes are inconsistent")
    sanitized = deepcopy(payload)
    for line_index in range(counts["rec_texts"]):
        boxes = payload["text_word_boxes"][line_index]
        words = payload["text_word"][line_index]
        line_box = payload["rec_boxes"][line_index]
        if (
            not isinstance(boxes, list)
            or not isinstance(words, list)
            or len(boxes) != len(words)
            or not isinstance(line_box, list)
            or len(line_box) != 4
        ):
            raise WaveOneRoleBFullReaderError("raw PP-OCR word axes are malformed")
        replacement = []
        for box, word in zip(boxes, words, strict=True):
            if (
                not isinstance(word, str)
                or not isinstance(box, list)
                or len(box) != 4
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not isfinite(value)
                    for value in box
                )
                or not box[0] < box[2]
                or not box[1] < box[3]
            ):
                raise WaveOneRoleBFullReaderError("raw PP-OCR word box schema is malformed")
            replacement.append(deepcopy(line_box))
        sanitized["text_word_boxes"][line_index] = replacement
    try:
        return validate_ppocrv6_payload(
            sanitized, pixel_width=pixel_width, pixel_height=pixel_height
        )
    except RuntimeError as error:
        raise WaveOneRoleBFullReaderError(
            "raw PP-OCR payload has a non-word-geometry structural failure"
        ) from error


def _unresolved_ocr_geometry_record(
    project_root: Path,
    control: dict[str, Any],
    expected: dict[str, Any],
    render: dict[str, Any],
    raw: dict[str, Any],
) -> dict[str, Any]:
    failure = {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_NORMALIZATION_FAILURE_V1",
        "status": "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        "reason": "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED",
        "policy_sha256": control["word_box_normalization"]["policy_sha256"],
        "control_identity_sha256": control["control_identity_sha256"],
        "normalization_producer_implementation_ledger_sha256": control["word_box_normalization"][
            "normalization_producer_implementation_ledger_sha256"
        ],
        "pixel_dimensions": [render["pixel_width"], render["pixel_height"]],
        "raw_payload_sha256": _canonical_sha256(raw),
    }
    backend = {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V3",
        "claim_boundary": (
            "RAW_PINNED_PROVIDER_PAYLOAD_WITH_TERMINAL_BOUNDED_WORD_BOX_GEOMETRY_FAILURE"
        ),
        "request_sha256": expected["request_sha256"],
        "request": expected["request"],
        "provider_identity_sha256": expected["request"]["provider_identity_sha256"],
        "render_ref": render["ref"],
        "raw_provider_payload": raw,
        "word_box_normalization_ledger": None,
        "normalization_failure": failure,
    }
    backend_ref = _put_object(project_root, _canonical_bytes(backend), suffix=".json")
    result = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3",
        "status": "UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        "claim_boundary": "SOURCE_VISIBLE_PAGE_RAW_OCR_EVIDENCE_WITH_UNRESOLVED_GEOMETRY",
        "request_sha256": expected["request_sha256"],
        "request": expected["request"],
        "source_sha256": expected["source_sha256"],
        "source_size_bytes": expected["source_size_bytes"],
        "physical_page": expected["physical_page"],
        "route": _OCR_ROUTE,
        "provider_identity_sha256": expected["request"]["provider_identity_sha256"],
        "render_runtime_identity_sha256": expected["request"]["render_runtime_identity_sha256"],
        "input_render_ref": render["ref"],
        "backend_payload_ref": backend_ref,
        "normalization_failure": failure,
        "coordinate_authority": public_coordinate_authority(render["coordinate_authority"]),
        "lines": [],
        "words": [],
        "metrics": {"line_count": 0, "word_token_count": 0},
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
        "safety": _safe_result_safety(),
    }
    result_ref = _put_object(project_root, _canonical_bytes(result), suffix=".json")
    return _page_record(
        expected,
        status="UNRESOLVED_OCR_WORD_BOX_GEOMETRY",
        origin="PINNED_PPOCRV6_FULL_READER",
        render_ref=render["ref"],
        backend_payload_ref=backend_ref,
        result_ref=result_ref,
        line_count=0,
        word_token_count=0,
        unresolved=True,
    )


def _consume_worker_response(
    project_root: Path,
    control: dict[str, Any],
    expected: dict[str, Any],
    render: dict[str, Any],
    response_payload: bytes,
    *,
    execution_nonce: str,
    shard_id: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    response = _json_object(response_payload, "PP-OCR worker response")
    required = {
        "format_version",
        "execution_nonce",
        "shard_id",
        "request_sha256",
        "render_sha256",
        "provider_identity_sha256",
        "payload",
        "word_box_normalization_ledger",
        "normalization_outcome",
        "observational",
    }
    observation = response.get("observational")
    if (
        set(response) != required
        or response.get("format_version") != "BANK_CORPUS_WAVE_1_PPOCRV6_FULL_WORKER_RESPONSE_V2"
        or response.get("execution_nonce") != execution_nonce
        or type(response.get("shard_id")) is not int
        or response.get("shard_id") != shard_id
        or response.get("request_sha256") != expected["request_sha256"]
        or response.get("render_sha256") != render["ref"]["sha256"]
        or response.get("provider_identity_sha256")
        != expected["request"]["provider_identity_sha256"]
        or not isinstance(observation, dict)
        or set(observation) != {"inference_wall_seconds", "model_load_wall_seconds"}
        or any(
            isinstance(observation[key], bool)
            or not isinstance(observation[key], (int, float))
            or not isfinite(observation[key])
            or observation[key] < 0
            for key in observation
        )
    ):
        raise WaveOneRoleBFullReaderError("PP-OCR worker response identity drifted")
    raw = response.get("payload")
    if not isinstance(raw, dict):
        raise WaveOneRoleBFullReaderError("PP-OCR worker payload is absent")
    outcome = response.get("normalization_outcome")
    if outcome not in {
        "NORMALIZATION_COMPLETE",
        "BOUNDED_NORMALIZATION_FAILURE_CANDIDATE",
    }:
        raise WaveOneRoleBFullReaderError("worker normalization outcome drifted")
    try:
        normalized, ledger = normalize_ppocrv6_word_boxes(
            raw,
            pixel_width=render["pixel_width"],
            pixel_height=render["pixel_height"],
            authority=_normalization_authority(control),
        )
    except WaveOneRoleBWordBoxNormalizationError as error:
        if (
            outcome != "BOUNDED_NORMALIZATION_FAILURE_CANDIDATE"
            or response["word_box_normalization_ledger"] is not None
        ):
            raise WaveOneRoleBFullReaderError(
                "worker normalization failure classification drifted"
            ) from error
        _validate_ppocrv6_schema_except_word_geometry(
            raw,
            pixel_width=render["pixel_width"],
            pixel_height=render["pixel_height"],
        )
        return _unresolved_ocr_geometry_record(
            project_root, control, expected, render, raw
        ), observation
    if outcome != "NORMALIZATION_COMPLETE" or not _same_typed_json(
        response["word_box_normalization_ledger"], ledger
    ):
        raise WaveOneRoleBFullReaderError("worker normalization replay drifted")
    counts = validate_ppocrv6_payload(
        normalized,
        pixel_width=render["pixel_width"],
        pixel_height=render["pixel_height"],
    )
    backend = {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V2",
        "claim_boundary": (
            "RAW_PINNED_PROVIDER_PAYLOAD_AND_BOUND_WORD_BOX_NORMALIZATION_LEDGER_"
            "FOR_ONE_EXACT_PAGE_REQUEST_ONLY"
        ),
        "request_sha256": expected["request_sha256"],
        "request": expected["request"],
        "provider_identity_sha256": expected["request"]["provider_identity_sha256"],
        "render_ref": render["ref"],
        "raw_provider_payload": raw,
        "word_box_normalization_ledger": ledger,
    }
    backend_ref = _put_object(project_root, _canonical_bytes(backend), suffix=".json")
    neutral = model_neutral_result_from_normalized_payload(
        normalized, coordinate_authority=render["coordinate_authority"]
    )
    result = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2",
        "status": neutral["status"],
        "claim_boundary": "SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY",
        "request_sha256": expected["request_sha256"],
        "request": expected["request"],
        "source_sha256": expected["source_sha256"],
        "source_size_bytes": expected["source_size_bytes"],
        "physical_page": expected["physical_page"],
        "route": _OCR_ROUTE,
        "provider_identity_sha256": expected["request"]["provider_identity_sha256"],
        "render_runtime_identity_sha256": expected["request"]["render_runtime_identity_sha256"],
        "input_render_ref": render["ref"],
        "backend_payload_ref": backend_ref,
        "word_box_normalization_ledger": ledger,
        "coordinate_authority": neutral["coordinate_authority"],
        "lines": neutral["lines"],
        "words": neutral["words"],
        "metrics": neutral["metrics"],
        "source_blank_claimed": False,
        "safety": _safe_result_safety(),
    }
    result_ref = _put_object(project_root, _canonical_bytes(result), suffix=".json")
    record = _page_record(
        expected,
        status=result["status"],
        origin="PINNED_PPOCRV6_FULL_READER",
        render_ref=render["ref"],
        backend_payload_ref=backend_ref,
        result_ref=result_ref,
        line_count=counts["line_count"],
        word_token_count=counts["word_token_count"],
        unresolved=False,
        word_box_correction_count=ledger["correction_count"],
        word_box_corrected_edge_count=ledger["corrected_edge_count"],
    )
    _validate_page_record(project_root, control, record, expected)
    return record, observation


def _open_runtime_log(path: Path) -> BinaryIO:
    descriptor = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    return os.fdopen(descriptor, "wb", closefd=True)


def _append_timing(runtime_root: Path, observation: dict[str, Any]) -> None:
    path = runtime_root / "timing-observations.jsonl"
    descriptor = os.open(
        path,
        os.O_WRONLY
        | os.O_APPEND
        | os.O_CREAT
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        os.write(descriptor, _canonical_bytes(observation))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


_WORKER_RESPONSE_READY = "READY"
_WORKER_RESPONSE_PUBLICATION_IN_PROGRESS = "PUBLICATION_IN_PROGRESS"
_WORKER_RESPONSE_TEMPORARY_RE = re.compile(
    r"^\.(?P<final>[0-9a-f]{64}\.response\.json)\.(?P<nonce>[0-9a-f]{32})\.tmp$"
)


class _ResponsePublicationTransition(RuntimeError):
    """A legitimate hardlink publication boundary moved while being observed."""


def _worker_response_temporaries(
    directory_fd: int, filename: str, allowed_filenames: frozenset[str]
) -> list[tuple[str, str]]:
    try:
        names = sorted(os.listdir(directory_fd))
    except OSError as error:
        raise WaveOneRoleBFullReaderError("worker response directory cannot be listed") from error
    temporary_like = [name for name in names if name.startswith(".") or name.endswith(".tmp")]
    if len(temporary_like) > 1:
        raise WaveOneRoleBFullReaderError(
            "worker response publication has multiple or foreign temporaries"
        )
    temporaries: list[tuple[str, str]] = []
    for name in temporary_like:
        match = _WORKER_RESPONSE_TEMPORARY_RE.fullmatch(name)
        if match is None or match.group("final") not in allowed_filenames:
            raise WaveOneRoleBFullReaderError("worker response publication temporary name drifted")
        temporaries.append((name, match.group("final")))
    for name in names:
        if name in temporary_like:
            continue
        if name not in allowed_filenames:
            raise WaveOneRoleBFullReaderError("worker response directory contains a foreign entry")
    if filename not in allowed_filenames:
        raise WaveOneRoleBFullReaderError("current worker response is outside the active batch")
    return temporaries


def _nofollow_response_stat(directory_fd: int, name: str) -> os.stat_result | None:
    try:
        identity = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise WaveOneRoleBFullReaderError("worker response identity cannot be read") from error
    if not stat.S_ISREG(identity.st_mode):
        raise WaveOneRoleBFullReaderError("worker response publication is not a regular file")
    return identity


def _read_response_bytes_at(
    directory_fd: int,
    name: str,
    *,
    cleanup_transition_allowed: bool,
) -> tuple[bytes, os.stat_result]:
    try:
        return sentinel._hash_open_at(directory_fd, name)  # noqa: SLF001
    except FileNotFoundError as error:
        if cleanup_transition_allowed:
            raise _ResponsePublicationTransition from error
        raise WaveOneRoleBFullReaderError("ready worker response disappeared") from error
    except (OSError, sentinel.WaveOneRoleBSentinelError) as error:
        raise WaveOneRoleBFullReaderError("worker response changed while being read") from error


def _response_pair_identity(identity: os.stat_result) -> tuple[int, ...]:
    return (
        identity.st_dev,
        identity.st_ino,
        identity.st_size,
        identity.st_mtime_ns,
        identity.st_ctime_ns,
    )


def _classify_worker_response_publication_once(
    directory_fd: int,
    filename: str,
    allowed_filenames: frozenset[str],
) -> tuple[str, bytes | None]:
    if re.fullmatch(r"[0-9a-f]{64}\.response\.json", filename) is None:
        raise WaveOneRoleBFullReaderError("worker response filename is malformed")
    temporaries = _worker_response_temporaries(directory_fd, filename, allowed_filenames)
    current_temporaries = [name for name, target in temporaries if target == filename]
    final = _nofollow_response_stat(directory_fd, filename)
    if final is None:
        if not current_temporaries and not temporaries:
            return _WORKER_RESPONSE_PUBLICATION_IN_PROGRESS, None
        if not current_temporaries:
            raise WaveOneRoleBFullReaderError(
                "worker advanced before publishing the current response"
            )
        temporary = _nofollow_response_stat(directory_fd, current_temporaries[0])
        if temporary is None:
            raise _ResponsePublicationTransition
        if stat.S_IMODE(temporary.st_mode) not in {0o600, 0o444} or temporary.st_nlink != 1:
            if temporary.st_nlink == 2 and stat.S_IMODE(temporary.st_mode) == 0o444:
                raise _ResponsePublicationTransition
            raise WaveOneRoleBFullReaderError("pre-link worker response temporary identity drifted")
        return _WORKER_RESPONSE_PUBLICATION_IN_PROGRESS, None

    if stat.S_IMODE(final.st_mode) != 0o444:
        raise WaveOneRoleBFullReaderError("worker response final mode drifted")
    if final.st_nlink == 1:
        if current_temporaries:
            temporary = _nofollow_response_stat(directory_fd, current_temporaries[0])
            if temporary is None:
                raise _ResponsePublicationTransition
            raise WaveOneRoleBFullReaderError("ready worker response retains a foreign temporary")
        payload, ready = _read_response_bytes_at(
            directory_fd, filename, cleanup_transition_allowed=False
        )
        if (
            stat.S_IMODE(ready.st_mode) != 0o444
            or ready.st_nlink != 1
            or _response_pair_identity(ready) != _response_pair_identity(final)
        ):
            raise WaveOneRoleBFullReaderError("ready worker response identity drifted")
        return _WORKER_RESPONSE_READY, payload
    if final.st_nlink != 2:
        raise WaveOneRoleBFullReaderError("worker response final link count drifted")
    if not current_temporaries:
        raise _ResponsePublicationTransition
    temporary_name = current_temporaries[0]
    temporary = _nofollow_response_stat(directory_fd, temporary_name)
    if temporary is None:
        raise _ResponsePublicationTransition
    if (
        stat.S_IMODE(temporary.st_mode) != 0o444
        or temporary.st_nlink != 2
        or _response_pair_identity(temporary) != _response_pair_identity(final)
    ):
        raise WaveOneRoleBFullReaderError(
            "worker response hardlink publication pair identity drifted"
        )
    final_payload, final_read = _read_response_bytes_at(
        directory_fd, filename, cleanup_transition_allowed=True
    )
    temporary_payload, temporary_read = _read_response_bytes_at(
        directory_fd, temporary_name, cleanup_transition_allowed=True
    )
    if (
        stat.S_IMODE(final_read.st_mode) != 0o444
        or stat.S_IMODE(temporary_read.st_mode) != 0o444
        or final_read.st_nlink != 2
        or temporary_read.st_nlink != 2
        or _response_pair_identity(final_read) != _response_pair_identity(temporary_read)
        or _response_pair_identity(final_read) != _response_pair_identity(final)
        or final_payload != temporary_payload
    ):
        raise _ResponsePublicationTransition
    return _WORKER_RESPONSE_PUBLICATION_IN_PROGRESS, None


def _read_worker_response_publication(
    directory_fd: int,
    filename: str,
    *,
    allowed_filenames: frozenset[str] | None = None,
) -> tuple[str, bytes | None]:
    """Classify one response without recovering or mutating active worker files."""

    allowed = allowed_filenames if allowed_filenames is not None else frozenset({filename})
    for _attempt in range(4):
        try:
            return _classify_worker_response_publication_once(directory_fd, filename, allowed)
        except _ResponsePublicationTransition:
            continue
    raise WaveOneRoleBFullReaderError("worker response publication topology is unstable")


def _poll_worker_response_publication(
    process: subprocess.Popen[bytes],
    directory_fd: int,
    filename: str,
    *,
    allowed_filenames: frozenset[str],
) -> tuple[str, bytes | None, int | None]:
    state, payload = _read_worker_response_publication(
        directory_fd, filename, allowed_filenames=allowed_filenames
    )
    code = process.poll()
    if code is not None and code != 0:
        raise WaveOneRoleBFullReaderError(f"pinned PP-OCR worker failed: {code}")
    if code == 0 and state != _WORKER_RESPONSE_READY:
        state, payload = _read_worker_response_publication(
            directory_fd, filename, allowed_filenames=allowed_filenames
        )
        if state != _WORKER_RESPONSE_READY:
            raise WaveOneRoleBFullReaderError(
                "worker exited before response publication became immutable"
            )
    return state, payload, code


def _run_ocr_batches(
    project_root: Path,
    model_cache: Path,
    sealed: dict[str, Any],
    policy: dict[str, Any],
    control: dict[str, Any],
    renders: dict[str, dict[str, Any]],
    records_by_document: dict[str, list[dict[str, Any]]],
    heads_by_document: dict[str, str | None],
    execution_lease_fd: int,
) -> dict[str, Any]:
    completed = {
        record["request_sha256"] for records in records_by_document.values() for record in records
    }
    missing_by_shard = {
        shard["shard_id"]: [
            request for request in shard["requests"] if request["request_sha256"] not in completed
        ]
        for shard in control["sharding"]["shards"]
    }
    total_missing = sum(len(requests) for requests in missing_by_shard.values())
    if total_missing == 0:
        return {
            "status": "COMPLETE_OCR_RESUME_WITH_ZERO_INFERENCE",
            "worker_process_count": 0,
            "worker_batch_count": 0,
            "inference_request_count": 0,
            "observational_runtime_paths": [],
        }
    if set(renders) != {
        request["request_sha256"] for requests in missing_by_shard.values() for request in requests
    }:
        raise WaveOneRoleBFullReaderError("missing OCR render set drifted")
    _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
    batches = {
        shard_id: [requests[index : index + 128] for index in range(0, len(requests), 128)]
        for shard_id, requests in missing_by_shard.items()
    }
    wave_count = max(len(value) for value in batches.values())
    interpreter = project_root / policy["worker"]["interpreter"]
    script = _project_path(project_root, policy["worker"]["script"], "full OCR worker")
    interpreter_target = interpreter.resolve()
    interpreter_payload = _stable_bytes(interpreter_target, "isolated PP-OCR interpreter")
    runtime_paths = []
    process_count = 0
    for wave_index in range(wave_count):
        _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
        active = {
            shard_id: shard_batches[wave_index]
            for shard_id, shard_batches in sorted(batches.items())
            if wave_index < len(shard_batches)
        }
        if (
            not active
            or len(active) > 2
            or any(not 1 <= len(requests) <= 128 for requests in active.values())
        ):
            raise WaveOneRoleBFullReaderError("OCR worker batch wave drifted")
        execution_nonce = secrets.token_hex(32)
        runtime_root = _create_runtime_root(project_root, execution_nonce)
        runtime_paths.append(runtime_root.relative_to(project_root).as_posix())
        response_stack = ExitStack()
        processes: dict[int, subprocess.Popen[bytes]] = {}
        logs: list[BinaryIO] = []
        states: dict[int, dict[str, Any]] = {}
        try:
            response_directories: dict[int, tuple[Path, int]] = {}
            for shard_id, requests in active.items():
                environment = _worker_environment(project_root, runtime_root, policy, shard_id)
                shard_relative = runtime_root.relative_to(project_root) / f"shard-{shard_id}"
                try:
                    response_directories[shard_id] = response_stack.enter_context(
                        sentinel._held_directory(  # noqa: SLF001
                            project_root,
                            shard_relative / "responses",
                            create=False,
                        )
                    )
                except sentinel.WaveOneRoleBSentinelError as error:
                    raise WaveOneRoleBFullReaderError(str(error)) from error
                private = _materialize_private_inputs(
                    project_root, runtime_root, shard_id, requests, renders
                )
                task = _build_worker_task(
                    project_root,
                    model_cache,
                    sealed,
                    control,
                    shard_id,
                    requests,
                    renders,
                    private,
                    execution_nonce,
                    environment,
                    execution_lease_fd,
                )
                task_path = _publish_exclusive(
                    project_root, shard_relative, "task.json", _canonical_bytes(task)
                )
                stdout = _open_runtime_log(runtime_root / f"shard-{shard_id}" / "stdout.log")
                stderr = _open_runtime_log(runtime_root / f"shard-{shard_id}" / "stderr.log")
                logs.extend((stdout, stderr))
                process = subprocess.Popen(
                    [
                        interpreter.as_posix(),
                        script.as_posix(),
                        "--task",
                        task_path.as_posix(),
                        "--response-directory",
                        response_directories[shard_id][0].as_posix(),
                    ],
                    cwd=project_root,
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    close_fds=True,
                    pass_fds=(execution_lease_fd,),
                )
                processes[shard_id] = process
                states[shard_id] = {
                    "expected": sorted(requests, key=lambda item: item["request_ordinal"]),
                    "next_index": 0,
                    "response_filenames": frozenset(
                        f"{request['request_sha256']}.response.json" for request in requests
                    ),
                }
            process_count += len(processes)
            last_progress = time.monotonic()
            while True:
                made_progress = False
                poll_codes: dict[int, int | None] = {}
                for shard_id, process in sorted(processes.items()):
                    _response_path, response_fd = response_directories[shard_id]
                    state = states[shard_id]
                    response_state = _WORKER_RESPONSE_PUBLICATION_IN_PROGRESS
                    response_payload = None
                    if state["next_index"] < len(state["expected"]):
                        expected = state["expected"][state["next_index"]]
                        request_sha = expected["request_sha256"]
                        response_state, response_payload, code = _poll_worker_response_publication(
                            process,
                            response_fd,
                            f"{request_sha}.response.json",
                            allowed_filenames=state["response_filenames"],
                        )
                    else:
                        code = process.poll()
                    poll_codes[shard_id] = code
                    if code is not None and code != 0:
                        raise WaveOneRoleBFullReaderError(
                            f"pinned PP-OCR worker shard {shard_id} failed: {code}"
                        )
                    if response_state == _WORKER_RESPONSE_READY:
                        if response_payload is None:
                            raise WaveOneRoleBFullReaderError(
                                "ready worker response payload is absent"
                            )
                        if state["next_index"] < len(state["expected"]):
                            record, observation = _consume_worker_response(
                                project_root,
                                control,
                                expected,
                                renders[request_sha],
                                response_payload,
                                execution_nonce=execution_nonce,
                                shard_id=shard_id,
                            )
                            _append_checkpoint(
                                project_root,
                                control,
                                records_by_document,
                                heads_by_document,
                                record,
                            )
                            state["next_index"] += 1
                            _append_timing(
                                runtime_root,
                                {
                                    "kind": "NON_IDENTITY_OBSERVATIONAL_WORKER_TIMING",
                                    "wave_index": wave_index,
                                    "execution_nonce": execution_nonce,
                                    "shard_id": shard_id,
                                    "request_sha256": request_sha,
                                    **observation,
                                },
                            )
                            made_progress = True
                all_consumed = all(
                    state["next_index"] == len(state["expected"]) for state in states.values()
                )
                all_exited = all(code is not None for code in poll_codes.values())
                if all_consumed and all_exited:
                    break
                if all_exited and not all_consumed and not made_progress:
                    raise WaveOneRoleBFullReaderError("worker exited without all exact responses")
                if made_progress:
                    last_progress = time.monotonic()
                elif time.monotonic() - last_progress > policy["worker"]["max_no_progress_seconds"]:
                    raise WaveOneRoleBFullReaderError(
                        "pinned PP-OCR worker batch exceeded the no-progress watchdog"
                    )
                else:
                    time.sleep(0.05)
        except BaseException:
            for process in processes.values():
                if process.poll() is None:
                    process.terminate()
            for process in processes.values():
                try:
                    process.wait(timeout=policy["worker"]["worker_shutdown_grace_seconds"])
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=policy["worker"]["worker_shutdown_grace_seconds"])
            raise
        finally:
            response_stack.close()
            for stream in logs:
                stream.close()
    if _stable_bytes(interpreter_target, "isolated PP-OCR interpreter") != interpreter_payload:
        raise WaveOneRoleBFullReaderError("PP-OCR interpreter changed during execution")
    return {
        "status": "COMPLETE_PINNED_PPOCRV6_BATCHES_CHECKPOINTED",
        "worker_process_count": process_count,
        "worker_batch_count": process_count,
        "inference_request_count": total_missing,
        "observational_runtime_paths": runtime_paths,
    }


def _scan_result_orphans(
    project_root: Path,
    control: dict[str, Any],
    completed_hashes: set[str],
) -> list[dict[str, Any]]:
    expected = {
        request_sha: record
        for request_sha, record in _control_index(control).items()
        if request_sha not in completed_hashes
        and request_sha not in set(control["sentinel_request_sha256s"])
    }
    if not expected:
        return []
    objects_relative = OUTPUT_RELATIVE_ROOT / "objects" / "sha256"
    objects_path = project_root / objects_relative
    if not objects_path.exists():
        return []
    candidates: list[dict[str, Any]] = []
    json_refs_by_sha: dict[str, dict[str, Any]] = {}
    try:
        with sentinel._held_directory(  # noqa: SLF001
            project_root, objects_relative, create=False
        ) as (_root, root_fd):
            shard_names = sorted(os.listdir(root_fd))
        for shard_name in shard_names:
            if len(shard_name) != 2 or set(shard_name) - _SHA256:
                raise WaveOneRoleBFullReaderError("object store shard name is malformed")
            with sentinel._held_directory(  # noqa: SLF001
                project_root, objects_relative / shard_name, create=False
            ) as (_shard, shard_fd):
                standalone_temporaries = sentinel._recover_owned_hardlink_temporaries(  # noqa: SLF001
                    shard_fd
                )
                for name in sorted(os.listdir(shard_fd)):
                    if name in standalone_temporaries:
                        continue
                    if name.endswith(".png"):
                        if (
                            len(name) != 68
                            or name[:-4][:2] != shard_name
                            or not _is_sha256(name[:-4])
                        ):
                            raise WaveOneRoleBFullReaderError(
                                "content-addressed PNG name is malformed"
                            )
                        continue
                    if (
                        not name.endswith(".json")
                        or len(name) != 69
                        or name[:-5][:2] != shard_name
                        or not _is_sha256(name[:-5])
                    ):
                        raise WaveOneRoleBFullReaderError(
                            "content-addressed JSON name is malformed"
                        )
                    payload, identity = sentinel._hash_open_at(shard_fd, name)  # noqa: SLF001
                    if (
                        stat.S_IMODE(identity.st_mode) != 0o444
                        or identity.st_nlink != 1
                        or sha256_bytes(payload) != name[:-5]
                    ):
                        raise WaveOneRoleBFullReaderError("orphan object identity drifted")
                    value = _json_object(payload, "orphan candidate object")
                    json_refs_by_sha[name[:-5]] = {
                        "path": (Path("objects/sha256") / shard_name / name).as_posix(),
                        "sha256": name[:-5],
                        "size_bytes": len(payload),
                    }
                    if value.get("format_version") not in {
                        "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2",
                        "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3",
                        "BANK_CORPUS_WAVE_1_ROLE_B_CAUSAL_NATIVE_PAGE_READ_RESULT_V1",
                    }:
                        continue
                    candidates.append(
                        {
                            "value": value,
                            "ref": {
                                "path": (Path("objects/sha256") / shard_name / name).as_posix(),
                                "sha256": name[:-5],
                                "size_bytes": len(payload),
                            },
                        }
                    )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    matches: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        request_sha = candidate["value"].get("request_sha256")
        if request_sha in expected:
            matches[request_sha].append(candidate)
    adopted = []
    for request_sha, choices in matches.items():
        if len(choices) != 1:
            raise WaveOneRoleBFullReaderError(
                "conflicting result objects exist for one full request identity"
            )
        result = choices[0]["value"]
        expected_record = expected[request_sha]
        if expected_record["route"] == _OCR_ROUTE:
            ledger = result.get("word_box_normalization_ledger", {}) or {}
            unresolved = result.get("status") == "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
            correction_count = 0 if unresolved else ledger.get("correction_count")
            corrected_edge_count = 0 if unresolved else ledger.get("corrected_edge_count")
            record = _page_record(
                expected_record,
                status=result.get("status"),
                origin="PINNED_PPOCRV6_FULL_READER",
                render_ref=result.get("input_render_ref"),
                backend_payload_ref=result.get("backend_payload_ref"),
                result_ref=choices[0]["ref"],
                line_count=result.get("metrics", {}).get("line_count"),
                word_token_count=result.get("metrics", {}).get("word_token_count"),
                unresolved=unresolved,
                word_box_correction_count=correction_count,
                word_box_corrected_edge_count=corrected_edge_count,
            )
        else:
            backend_ref = json_refs_by_sha.get(result.get("backend_payload_sha256"))
            if backend_ref is None:
                raise WaveOneRoleBFullReaderError(
                    "native orphan lacks its content-addressed backend"
                )
            record = _page_record(
                expected_record,
                status=result.get("status"),
                origin="SEALED_CAUSAL_NATIVE_TEXT_GATE",
                render_ref=None,
                backend_payload_ref=backend_ref,
                result_ref=choices[0]["ref"],
                line_count=result.get("metrics", {}).get("line_count"),
                word_token_count=result.get("metrics", {}).get("word_token_count"),
                unresolved=result.get("status") != "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
                quarantined_span_count=result.get("metrics", {}).get("quarantined_span_count"),
            )
        _validate_page_record(project_root, control, record, expected_record)
        adopted.append(record)
    return sorted(adopted, key=lambda item: item["request_ordinal"])


def _run_native_requests(
    project_root: Path,
    sealed: dict[str, Any],
    control: dict[str, Any],
    records_by_document: dict[str, list[dict[str, Any]]],
    heads_by_document: dict[str, str | None],
) -> dict[str, Any]:
    from bctc_ai.ocr.causal_native_text_evidence_v1 import (  # noqa: PLC0415
        build_causal_native_text_evidence,
        validate_causal_native_text_evidence_replay,
    )

    completed = {
        record["request_sha256"] for records in records_by_document.values() for record in records
    }
    missing = [
        record
        for record in _control_index(control).values()
        if record["route"] == _NATIVE_ROUTE and record["request_sha256"] not in completed
    ]
    if not missing:
        return {
            "status": "COMPLETE_NATIVE_RESUME_WITH_ZERO_NEW_READS",
            "native_read_request_count": 0,
        }
    native_contract = control["native_reader_contract"]
    causal_path = _project_path(
        project_root, native_contract["policy_path"], "causal native policy"
    )
    quality_path = _project_path(
        project_root,
        native_contract["quality_policy_path"],
        "native text quality policy",
    )
    for path, digest, size, label in (
        (
            causal_path,
            native_contract["policy_sha256"],
            native_contract["policy_size_bytes"],
            "causal native policy",
        ),
        (
            quality_path,
            native_contract["quality_policy_sha256"],
            native_contract["quality_policy_size_bytes"],
            "native text quality policy",
        ),
    ):
        payload = _stable_bytes(path, label)
        if len(payload) != size or sha256_bytes(payload) != digest:
            raise WaveOneRoleBFullReaderError(f"{label} byte identity drifted")
    documents = _sealed_documents(sealed)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in missing:
        grouped[record["document_id"]].append(record)
    completed_new = 0
    for document_id in sorted(grouped):
        _ensure_capacity(project_root, 53_687_091_200)
        source_path, source_bytes = _source_payload(project_root, documents[document_id])
        for expected in sorted(grouped[document_id], key=lambda item: item["request_ordinal"]):
            try:
                backend, result = build_causal_native_text_evidence(
                    request=expected["request"],
                    request_sha256=expected["request_sha256"],
                    source_bytes=source_bytes,
                    document_id=document_id,
                    physical_page=expected["physical_page"],
                    provider_runtime_ledger=sealed["causal_native_runtime_ledger"],
                    causal_policy_path=causal_path,
                    quality_policy_path=quality_path,
                    full_control_identity_sha256=control["control_identity_sha256"],
                )
                validate_causal_native_text_evidence_replay(
                    request=expected["request"],
                    request_sha256=expected["request_sha256"],
                    source_bytes=source_bytes,
                    document_id=document_id,
                    physical_page=expected["physical_page"],
                    provider_runtime_ledger=sealed["causal_native_runtime_ledger"],
                    causal_policy_path=causal_path,
                    quality_policy_path=quality_path,
                    full_control_identity_sha256=control["control_identity_sha256"],
                    backend=backend,
                    result=result,
                )
            except RuntimeError as error:
                raise WaveOneRoleBFullReaderError(
                    "causal native evidence construction failed"
                ) from error
            backend_ref = _put_object(project_root, _canonical_bytes(backend), suffix=".json")
            result_ref = _put_object(project_root, _canonical_bytes(result), suffix=".json")
            status = result.get("status")
            metrics = result.get("metrics")
            if status not in _NATIVE_TERMINAL or not isinstance(metrics, dict):
                raise WaveOneRoleBFullReaderError("native evidence outcome drifted")
            record = _page_record(
                expected,
                status=status,
                origin="SEALED_CAUSAL_NATIVE_TEXT_GATE",
                render_ref=None,
                backend_payload_ref=backend_ref,
                result_ref=result_ref,
                line_count=metrics.get("line_count"),
                word_token_count=metrics.get("word_token_count"),
                unresolved=status != "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
                quarantined_span_count=metrics.get("quarantined_span_count"),
            )
            _append_checkpoint(
                project_root,
                control,
                records_by_document,
                heads_by_document,
                record,
            )
            completed_new += 1
        if _stable_bytes(source_path, "receipt-bound selected source PDF") != source_bytes:
            raise WaveOneRoleBFullReaderError("source PDF changed during native reading")
    return {
        "status": "COMPLETE_CAUSAL_NATIVE_REQUESTS_CHECKPOINTED",
        "native_read_request_count": completed_new,
    }


def _document_index_payload(
    control: dict[str, Any], document_id: str, records: list[dict[str, Any]], head: str
) -> dict[str, Any]:
    expected = _document_completion_order(control, document_id)
    observed = [record["request_sha256"] for record in records]
    if observed != expected:
        raise WaveOneRoleBFullReaderError("document index is not request-complete")
    ordered_records = sorted(records, key=lambda item: item["request_ordinal"])
    return {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_DOCUMENT_INDEX_V1",
        "status": "COMPLETE_DOCUMENT_PAGE_REQUEST_ACCOUNTING",
        "claim_boundary": "SOURCE_VISIBLE_PAGE_TEXT_AND_GEOMETRY_EVIDENCE_ONLY",
        "sealed_plan_sha256": SEALED_PLAN_SHA256,
        "control_identity_sha256": control["control_identity_sha256"],
        "document_id": document_id,
        "source_sha256": document_id.removeprefix("sha256:"),
        "final_checkpoint_sha256": head,
        "request_count": len(records),
        "request_set_sha256": _canonical_sha256(
            [record["request_sha256"] for record in ordered_records]
        ),
        "page_records": ordered_records,
        "accounting": {
            "source_accounted_page_count": len(records),
            "ocr_page_count": sum(record["route"] == _OCR_ROUTE for record in records),
            "native_page_count": sum(record["route"] == _NATIVE_ROUTE for record in records),
            "unresolved_page_count": sum(record["unresolved"] for record in records),
            "line_count": sum(record["line_count"] for record in records),
            "word_token_count": sum(record["word_token_count"] for record in records),
            "quarantined_span_count": sum(record["quarantined_span_count"] for record in records),
            **_ZERO_INTERPRETATION,
        },
    }


def _publish_document_indexes(
    project_root: Path,
    control: dict[str, Any],
    records_by_document: dict[str, list[dict[str, Any]]],
    heads_by_document: dict[str, str | None],
) -> list[dict[str, Any]]:
    references = []
    for document_id in sorted(records_by_document):
        head = heads_by_document[document_id]
        if head is None:
            raise WaveOneRoleBFullReaderError("complete document lacks a checkpoint head")
        payload = _document_index_payload(
            control, document_id, records_by_document[document_id], head
        )
        encoded = _canonical_bytes(payload)
        digest = sha256_bytes(encoded)
        filename = f"{document_id.removeprefix('sha256:')}.json"
        _publish_exclusive(project_root, OUTPUT_RELATIVE_ROOT / "documents", filename, encoded)
        references.append(
            {
                "document_id": document_id,
                "path": (Path("documents") / filename).as_posix(),
                "sha256": digest,
                "size_bytes": len(encoded),
            }
        )
    if len(references) != 27:
        raise WaveOneRoleBFullReaderError("document index count drifted")
    return references


def publish_authenticated_control(project_root: Path, *, model_cache: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    control = build_authenticated_control(project_root, model_cache=model_cache.resolve())
    _ensure_capacity(project_root, 53_687_091_200)
    _publish_exclusive(
        project_root,
        OUTPUT_RELATIVE_ROOT,
        "full-reader-execution-control.json",
        _canonical_bytes(control),
    )
    return control


def _read_published_control(project_root: Path, expected: dict[str, Any]) -> None:
    observed = _load_published_control(project_root)
    if not _same_typed_json(observed, expected):
        raise WaveOneRoleBFullReaderError("published full-reader control drifted")


def _load_published_control(project_root: Path) -> dict[str, Any]:
    try:
        with sentinel._held_directory(  # noqa: SLF001
            project_root, OUTPUT_RELATIVE_ROOT, create=False
        ) as (_directory, directory_fd):
            payload, identity = sentinel._hash_open_at(  # noqa: SLF001
                directory_fd, "full-reader-execution-control.json"
            )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    if stat.S_IMODE(identity.st_mode) != 0o444 or identity.st_nlink != 1:
        raise WaveOneRoleBFullReaderError("published full-reader control drifted")
    control = _json_object(payload, "published full-reader control")
    identity_sha = control.get("control_identity_sha256")
    if (
        not _is_sha256(identity_sha)
        or _canonical_sha256(
            {key: value for key, value in control.items() if key != "control_identity_sha256"}
        )
        != identity_sha
    ):
        raise WaveOneRoleBFullReaderError("published full-reader logical identity drifted")
    return control


def _validate_published_executor_on_descendant(
    project_root: Path, published: dict[str, Any]
) -> None:
    git = published.get("executor_git")
    ledger = published.get("executor_implementation_ledger")
    if (
        not isinstance(git, dict)
        or set(git) != {"commit", "dirty"}
        or not isinstance(git.get("commit"), str)
        or re.fullmatch(r"[0-9a-f]{40}", git["commit"]) is None
        or git.get("dirty") is not False
        or not isinstance(ledger, dict)
        or set(ledger) != {"records", "sha256"}
        or _canonical_sha256(ledger.get("records")) != ledger.get("sha256")
    ):
        raise WaveOneRoleBFullReaderError("published executor authority drifted")
    try:
        current_git = sentinel._git_identity(  # noqa: SLF001
            project_root, require_clean=True
        )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", git["commit"], current_git["commit"]],
        cwd=project_root,
        check=False,
    )
    if ancestor.returncode:
        raise WaveOneRoleBFullReaderError("published executor is not an ancestor")
    records = ledger["records"]
    expected_paths = {path.as_posix() for path in FULL_READER_IMPLEMENTATION_RELATIVE_PATHS}
    if (
        not isinstance(records, list)
        or {record.get("path") for record in records if isinstance(record, dict)} != expected_paths
    ):
        raise WaveOneRoleBFullReaderError("published executor ledger path set drifted")
    for record in records:
        if (
            not isinstance(record, dict)
            or set(record) != {"phase", "kind", "path", "sha256", "size_bytes"}
            or record["phase"] != "READ"
            or record["kind"] != "IMPLEMENTATION"
            or not _is_sha256(record["sha256"])
            or type(record["size_bytes"]) is not int
            or record["size_bytes"] < 0
        ):
            raise WaveOneRoleBFullReaderError("published executor ledger record drifted")
        historical = _git_blob(project_root, git["commit"], record["path"])
        current = _stable_bytes(
            _project_path(project_root, record["path"], "current full-reader implementation"),
            "current full-reader implementation",
        )
        if (
            len(historical) != record["size_bytes"]
            or sha256_bytes(historical) != record["sha256"]
            or current != historical
        ):
            raise WaveOneRoleBFullReaderError(
                "full-reader implementation differs from published producer"
            )


def run_authenticated_full_reader(project_root: Path, *, model_cache: Path) -> dict[str, Any]:
    """Run all missing sealed Wave-1 page reads with fixed authenticated providers."""

    project_root = project_root.resolve()
    model_cache = model_cache.resolve()
    sealed, policy, executor = _authenticate_plan(
        project_root, model_cache, require_clean_executor=True
    )
    control = build_authenticated_control(project_root, model_cache=model_cache)
    if (
        control["executor_git"] != executor["git"]
        or control["executor_implementation_ledger"] != executor["implementation_ledger"]
    ):
        raise WaveOneRoleBFullReaderError("run authority differs from full control")
    _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
    _publish_exclusive(
        project_root,
        OUTPUT_RELATIVE_ROOT,
        "full-reader-execution-control.json",
        _canonical_bytes(control),
    )
    aggregate, sentinel_control, sentinel_results = _read_successful_sentinel(project_root, sealed)
    document_ids = [document["document_id"] for document in control["documents"]]
    with _execution_lease(project_root) as lease_fd, _document_locks(project_root, document_ids):
        _publish_upstream_sentinel_copies(project_root, aggregate, sentinel_control)
        records_by_document: dict[str, list[dict[str, Any]]] = {}
        heads_by_document: dict[str, str | None] = {}
        for document_id in document_ids:
            records, head = _load_document_checkpoints(project_root, control, document_id)
            records_by_document[document_id] = records
            heads_by_document[document_id] = head
        completed = {
            record["request_sha256"]
            for records in records_by_document.values()
            for record in records
        }
        for record in _adopt_successful_sentinel(project_root, control, sentinel_results):
            if record["request_sha256"] not in completed:
                _append_checkpoint(
                    project_root,
                    control,
                    records_by_document,
                    heads_by_document,
                    record,
                )
                completed.add(record["request_sha256"])
        orphans = _scan_result_orphans(project_root, control, completed)
        for record in orphans:
            _append_checkpoint(
                project_root,
                control,
                records_by_document,
                heads_by_document,
                record,
            )
            completed.add(record["request_sha256"])
        missing_ocr = [
            record
            for shard in control["sharding"]["shards"]
            for record in shard["requests"]
            if record["request_sha256"] not in completed
        ]
        renders = _render_missing_ocr_requests(project_root, sealed, missing_ocr)
        ocr_execution = _run_ocr_batches(
            project_root,
            model_cache,
            sealed,
            policy,
            control,
            renders,
            records_by_document,
            heads_by_document,
            lease_fd,
        )
        native_execution = _run_native_requests(
            project_root,
            sealed,
            control,
            records_by_document,
            heads_by_document,
        )
        completed = {
            record["request_sha256"]
            for records in records_by_document.values()
            for record in records
        }
        if completed != set(_control_index(control)):
            raise WaveOneRoleBFullReaderError("full reader did not checkpoint all 1,449 requests")
        document_indexes = _publish_document_indexes(
            project_root, control, records_by_document, heads_by_document
        )
    return {
        "status": "COMPLETE_AUTHENTICATED_WAVE_1_FULL_PAGE_READ_CHECKPOINTS",
        "control_identity_sha256": control["control_identity_sha256"],
        "request_count": 1449,
        "document_count": 27,
        "sentinel_adopted_request_count": 24,
        "orphan_adopted_request_count": len(orphans),
        "ocr_execution": ocr_execution,
        "native_execution": native_execution,
        "document_index_count": len(document_indexes),
    }


def _verify_upstream_copies(
    project_root: Path, aggregate: dict[str, Any], sentinel_control: dict[str, Any]
) -> None:
    try:
        with sentinel._held_directory(  # noqa: SLF001
            project_root, OUTPUT_RELATIVE_ROOT / "upstream", create=False
        ) as (_directory, directory_fd):
            aggregate_payload, aggregate_stat = sentinel._hash_open_at(  # noqa: SLF001
                directory_fd, "sentinel-aggregate.json"
            )
            control_payload, control_stat = sentinel._hash_open_at(  # noqa: SLF001
                directory_fd, "sentinel-execution-control.json"
            )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    if (
        aggregate_payload != _canonical_bytes(aggregate)
        or control_payload != _canonical_bytes(sentinel_control)
        or stat.S_IMODE(aggregate_stat.st_mode) != 0o444
        or aggregate_stat.st_nlink != 1
        or stat.S_IMODE(control_stat.st_mode) != 0o444
        or control_stat.st_nlink != 1
    ):
        raise WaveOneRoleBFullReaderError("standalone upstream sentinel copies drifted")


def _read_document_index(project_root: Path, reference: dict[str, Any]) -> dict[str, Any]:
    if (
        not isinstance(reference, dict)
        or set(reference) != {"document_id", "path", "sha256", "size_bytes"}
        or reference["path"] != f"documents/{reference['document_id'].removeprefix('sha256:')}.json"
    ):
        raise WaveOneRoleBFullReaderError("document index reference drifted")
    filename = Path(reference["path"]).name
    try:
        with sentinel._held_directory(  # noqa: SLF001
            project_root, OUTPUT_RELATIVE_ROOT / "documents", create=False
        ) as (_directory, directory_fd):
            payload, identity = sentinel._hash_open_at(directory_fd, filename)  # noqa: SLF001
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBFullReaderError(str(error)) from error
    if (
        len(payload) != reference["size_bytes"]
        or sha256_bytes(payload) != reference["sha256"]
        or stat.S_IMODE(identity.st_mode) != 0o444
        or identity.st_nlink != 1
    ):
        raise WaveOneRoleBFullReaderError("document index object drifted")
    return _json_object(payload, "document index")


def _replay_native_records(
    project_root: Path,
    sealed: dict[str, Any],
    control: dict[str, Any],
    records: list[dict[str, Any]],
) -> None:
    from bctc_ai.ocr.causal_native_text_evidence_v1 import (  # noqa: PLC0415
        validate_causal_native_text_evidence_replay,
    )

    native_contract = control["native_reader_contract"]
    causal_path = _project_path(
        project_root, native_contract["policy_path"], "causal native policy"
    )
    quality_path = _project_path(
        project_root,
        native_contract["quality_policy_path"],
        "native text quality policy",
    )
    documents = _sealed_documents(sealed)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record["route"] == _NATIVE_ROUTE:
            grouped[record["document_id"]].append(record)
    if sum(len(value) for value in grouped.values()) != 93:
        raise WaveOneRoleBFullReaderError("native replay request count drifted")
    for document_id in sorted(grouped):
        source_path, source_bytes = _source_payload(project_root, documents[document_id])
        for record in sorted(grouped[document_id], key=lambda item: item["request_ordinal"]):
            backend = _json_object(
                _read_object(project_root, record["backend_payload_ref"], ".json"),
                "native replay backend",
            )
            result = _json_object(
                _read_object(project_root, record["result_ref"], ".json"),
                "native replay result",
            )
            try:
                validate_causal_native_text_evidence_replay(
                    request=record["request"],
                    request_sha256=record["request_sha256"],
                    source_bytes=source_bytes,
                    document_id=document_id,
                    physical_page=record["physical_page"],
                    provider_runtime_ledger=sealed["causal_native_runtime_ledger"],
                    causal_policy_path=causal_path,
                    quality_policy_path=quality_path,
                    full_control_identity_sha256=control["control_identity_sha256"],
                    backend=backend,
                    result=result,
                )
            except RuntimeError as error:
                raise WaveOneRoleBFullReaderError(
                    "causal native final source replay failed"
                ) from error
        if _stable_bytes(source_path, "receipt-bound selected source PDF") != source_bytes:
            raise WaveOneRoleBFullReaderError("source PDF changed during native replay")


def _replay_all_ocr_renders(
    project_root: Path,
    sealed: dict[str, Any],
    control: dict[str, Any],
    records: list[dict[str, Any]],
) -> None:
    ocr_records = [record for record in records if record["route"] == _OCR_ROUTE]
    if len(ocr_records) != 1356:
        raise WaveOneRoleBFullReaderError("OCR source-rerender request count drifted")
    expected_index = _control_index(control)
    documents = _sealed_documents(sealed)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in ocr_records:
        grouped[record["document_id"]].append(record)
    for document_id in sorted(grouped):
        source_path, source_bytes = _source_payload(project_root, documents[document_id])
        pdf = fitz.open(stream=source_bytes, filetype="pdf")
        try:
            for record in sorted(grouped[document_id], key=lambda item: item["request_ordinal"]):
                expected = expected_index[record["request_sha256"]]
                dpi = expected["request"]["render_specification"]["dpi"]
                rendered = render_composited_displayed_page(
                    pdf.load_page(record["physical_page"] - 1), dpi=dpi
                )
                result = _json_object(
                    _read_object(project_root, record["result_ref"], ".json"),
                    "OCR render replay result",
                )
                expected_ref = {
                    "path": (
                        Path("objects/sha256") / rendered.sha256[:2] / f"{rendered.sha256}.png"
                    ).as_posix(),
                    "sha256": rendered.sha256,
                    "size_bytes": rendered.size_bytes,
                }
                stored = _read_object(project_root, expected_ref, ".png")
                if (
                    stored != rendered.payload
                    or not _same_typed_json(record["render_ref"], expected_ref)
                    or not _same_typed_json(
                        result.get("coordinate_authority"),
                        public_coordinate_authority(rendered.coordinate_authority),
                    )
                ):
                    raise WaveOneRoleBFullReaderError(
                        "OCR render or coordinate authority differs from authenticated source"
                    )
        finally:
            pdf.close()
        if _stable_bytes(source_path, "receipt-bound selected source PDF") != source_bytes:
            raise WaveOneRoleBFullReaderError("source PDF changed during OCR render replay")


def _exact_partition_accounting(records: list[dict[str, Any]]) -> dict[str, Any]:
    routes = Counter(record["route"] for record in records)
    origins = Counter(record["origin"] for record in records)
    dpi_counts = Counter(
        (
            record["request"]["render_specification"]["dpi"]
            if record["route"] == _OCR_ROUTE
            else "NOT_APPLICABLE"
        )
        for record in records
    )
    adopted = [
        record
        for record in records
        if record["origin"] == "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY"
    ]
    new = [
        record
        for record in records
        if record["origin"] != "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY"
    ]
    adopted_dpi = Counter(record["request"]["render_specification"]["dpi"] for record in adopted)
    new_dpi = Counter(
        (
            record["request"]["render_specification"]["dpi"]
            if record["route"] == _OCR_ROUTE
            else "NOT_APPLICABLE"
        )
        for record in new
    )
    if (
        len(records) != 1449
        or routes != {_OCR_ROUTE: 1356, _NATIVE_ROUTE: 93}
        or origins
        != {
            "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY": 24,
            "PINNED_PPOCRV6_FULL_READER": 1332,
            "SEALED_CAUSAL_NATIVE_TEXT_GATE": 93,
        }
        or dpi_counts != {200: 1250, 300: 106, "NOT_APPLICABLE": 93}
        or adopted_dpi != {200: 20, 300: 4}
        or new_dpi != {200: 1230, 300: 102, "NOT_APPLICABLE": 93}
    ):
        raise WaveOneRoleBFullReaderError("aggregate route/origin/DPI partition drifted")
    return {
        "routes": routes,
        "origins": origins,
        "dpi_counts": dpi_counts,
        "adopted_dpi": adopted_dpi,
        "new_dpi": new_dpi,
    }


def verify_authenticated_full_reader(project_root: Path, *, model_cache: Path) -> dict[str, Any]:
    """Replay all immutable page evidence and source-bound native reads."""

    project_root = project_root.resolve()
    model_cache = model_cache.resolve()
    published_control = _load_published_control(project_root)
    _validate_published_executor_on_descendant(project_root, published_control)
    sealed, policy, current_executor = _authenticate_plan(
        project_root, model_cache, require_clean_executor=True
    )
    current_candidate = build_authenticated_control(project_root, model_cache=model_cache)
    if current_executor["implementation_ledger"] != published_control.get(
        "executor_implementation_ledger"
    ):
        raise WaveOneRoleBFullReaderError("published implementation ledger drifted")
    expected_control = deepcopy(current_candidate)
    expected_control["executor_git"] = deepcopy(published_control["executor_git"])
    expected_control.pop("control_identity_sha256", None)
    expected_control["control_identity_sha256"] = _canonical_sha256(expected_control)
    if not _same_typed_json(expected_control, published_control):
        raise WaveOneRoleBFullReaderError("published control structural replay drifted")
    control = published_control
    executor = {
        "git": control["executor_git"],
        "implementation_ledger": control["executor_implementation_ledger"],
    }
    sentinel_aggregate, sentinel_control, sentinel_results = _read_successful_sentinel(
        project_root, sealed
    )
    _verify_upstream_copies(project_root, sentinel_aggregate, sentinel_control)
    adopted = _read_only_adopted_sentinel_records(project_root, control, sentinel_results)
    adopted_by_sha = {record["request_sha256"]: record for record in adopted}
    records = []
    document_references = []
    for document_id in sorted(document["document_id"] for document in control["documents"]):
        document_records, head = _load_document_checkpoints(
            project_root, control, document_id, recover_temporaries=False
        )
        if head is None:
            raise WaveOneRoleBFullReaderError("complete document has no checkpoint head")
        expected_document = _document_index_payload(control, document_id, document_records, head)
        encoded = _canonical_bytes(expected_document)
        reference = {
            "document_id": document_id,
            "path": (Path("documents") / f"{document_id.removeprefix('sha256:')}.json").as_posix(),
            "sha256": sha256_bytes(encoded),
            "size_bytes": len(encoded),
        }
        observed_document = _read_document_index(project_root, reference)
        if not _same_typed_json(observed_document, expected_document):
            raise WaveOneRoleBFullReaderError("document index replay drifted")
        records.extend(document_records)
        document_references.append(reference)
    records.sort(key=lambda item: item["request_ordinal"])
    if (
        len(records) != 1449
        or [record["request_ordinal"] for record in records] != list(range(1, 1450))
        or {record["request_sha256"] for record in records} != set(_control_index(control))
    ):
        raise WaveOneRoleBFullReaderError("full aggregate request accounting drifted")
    for request_sha, expected_adopted in adopted_by_sha.items():
        observed = next(record for record in records if record["request_sha256"] == request_sha)
        if not _same_typed_json(observed, expected_adopted):
            raise WaveOneRoleBFullReaderError("sentinel adoption checkpoint drifted")
    _replay_all_ocr_renders(project_root, sealed, control, records)
    _replay_native_records(project_root, sealed, control, records)
    outcomes = Counter(record["status"] for record in records)
    partitions = _exact_partition_accounting(records)
    routes = partitions["routes"]
    origins = partitions["origins"]
    dpi_counts = partitions["dpi_counts"]
    adopted_dpi = partitions["adopted_dpi"]
    new_dpi = partitions["new_dpi"]
    unresolved_count = sum(record["unresolved"] for record in records)
    status = (
        _COMPLETE_STATUS
        if unresolved_count == 0
        else "COMPLETE_WAVE_1_PAGE_REQUEST_ACCOUNTING_WITH_UNRESOLVED_READS"
    )
    aggregate = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READS_V1",
        "status": status,
        "claim_boundary": policy["claim_boundary"],
        "sealed_plan": control["sealed_plan"],
        "control": {
            "identity_sha256": control["control_identity_sha256"],
            "artifact": {
                "path": "full-reader-execution-control.json",
                "sha256": sha256_bytes(_canonical_bytes(control)),
                "size_bytes": len(_canonical_bytes(control)),
            },
        },
        "successful_sentinel": {
            "aggregate_sha256": SENTINEL_AGGREGATE_SHA256,
            "aggregate_identity_sha256": SENTINEL_AGGREGATE_IDENTITY_SHA256,
            "control_sha256": SENTINEL_CONTROL_SHA256,
            "control_identity_sha256": sentinel_control["control_identity_sha256"],
            "adopted_request_count": 24,
            "copied_object_count": 72,
            "copy_semantics": "BYTE_COPY_NEW_INODE_NO_HARDLINK_V1",
        },
        "executor_git": executor["git"],
        "executor_implementation_ledger": executor["implementation_ledger"],
        "provider_identities": {
            "ocr": sealed["ppocrv6_runtime_model_ledger"]["sha256"],
            "render": sealed["render_runtime_ledger"]["sha256"],
            "causal_native": sealed["causal_native_runtime_ledger"]["sha256"],
        },
        "word_box_normalization": control["word_box_normalization"],
        "execution_contract": {
            "remaining_ocr_shard_request_counts": [665, 667],
            "remaining_ocr_shard_document_counts": [13, 13],
            "max_process_count": 2,
            "max_new_requests_per_shard_per_batch": 128,
            "one_model_session_per_worker_batch": True,
            "completed_resume_inference_count": 0,
            "checkpoint": "ONE_IMMUTABLE_DELTA_PER_PAGE_WITH_CHAIN_HEAD",
            "orphan_adoption": "FULL_REQUEST_IDENTITY_ONLY",
            "timings_in_identity": False,
        },
        "document_indexes": document_references,
        "page_records": records,
        "accounting": {
            "document_count": 27,
            "request_count": 1449,
            "source_accounted_page_count": 1449,
            "ocr_page_count": routes[_OCR_ROUTE],
            "native_page_count": routes[_NATIVE_ROUTE],
            "sentinel_adopted_page_count": 24,
            "new_page_count": 1425,
            "new_ocr_page_count": 1332,
            "new_native_page_count": 93,
            "missing_request_count": 0,
            "duplicate_request_count": 0,
            "foreign_request_count": 0,
            "complete_text_read_page_count": outcomes["OCR_WORD_BOX_READ_COMPLETE"]
            + outcomes["CAUSAL_NATIVE_TEXT_READ_COMPLETE"],
            "terminal_unresolved_page_count": unresolved_count,
            "line_count": sum(record["line_count"] for record in records),
            "word_token_count": sum(record["word_token_count"] for record in records),
            "quarantined_span_count": sum(record["quarantined_span_count"] for record in records),
            "outcome_counts": dict(sorted(outcomes.items())),
            "route_outcome_counts": {
                route: dict(
                    sorted(
                        Counter(
                            record["status"] for record in records if record["route"] == route
                        ).items()
                    )
                )
                for route in (_OCR_ROUTE, _NATIVE_ROUTE)
            },
            "origin_counts": dict(sorted(origins.items())),
            "dpi_counts": {
                "all": {
                    "200": dpi_counts[200],
                    "300": dpi_counts[300],
                    "NOT_APPLICABLE": dpi_counts["NOT_APPLICABLE"],
                },
                "sentinel_adopted": {
                    "200": adopted_dpi[200],
                    "300": adopted_dpi[300],
                    "NOT_APPLICABLE": 0,
                },
                "new": {
                    "200": new_dpi[200],
                    "300": new_dpi[300],
                    "NOT_APPLICABLE": new_dpi["NOT_APPLICABLE"],
                },
            },
            **_ZERO_INTERPRETATION,
        },
        "word_box_normalization_accounting": {
            "corrected_page_count": sum(
                record["word_box_correction_count"] > 0 for record in records
            ),
            "no_change_ocr_page_count": sum(
                record["route"] == _OCR_ROUTE
                and record["status"] == "OCR_WORD_BOX_READ_COMPLETE"
                and record["word_box_correction_count"] == 0
                for record in records
            ),
            "unresolved_geometry_page_count": outcomes["UNRESOLVED_OCR_WORD_BOX_GEOMETRY"],
            "corrected_word_box_count": sum(
                record["word_box_correction_count"] for record in records
            ),
            "corrected_edge_count": sum(
                record["word_box_corrected_edge_count"] for record in records
            ),
            "counts_are_extraction_success_metrics": False,
        },
        "safety": {
            "bank_registry_metadata_used": False,
            "filename_metadata_used": False,
            "role_a_used": False,
            "schema_used": False,
            "mapping_used": False,
            "historical_values_used": False,
            **_ZERO_INTERPRETATION,
            "source_visible_text_preserved_verbatim": True,
            "native_ocr_fallback_used": False,
        },
    }
    aggregate["aggregate_identity_sha256"] = _canonical_sha256(aggregate)
    return aggregate


def finalize_authenticated_full_reader(project_root: Path, *, model_cache: Path) -> dict[str, Any]:
    aggregate = verify_authenticated_full_reader(project_root, model_cache=model_cache)
    _publish_exclusive(
        project_root.resolve(),
        OUTPUT_RELATIVE_ROOT,
        "full-reader-aggregate.json",
        _canonical_bytes(aggregate),
    )
    replay = verify_authenticated_full_reader(project_root, model_cache=model_cache)
    if not _same_typed_json(replay, aggregate):
        raise WaveOneRoleBFullReaderError("full aggregate replay changed after publication")
    return aggregate
