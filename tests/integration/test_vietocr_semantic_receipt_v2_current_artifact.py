from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.source_structure import vietocr_semantic_receipt_v2 as receipt_v2
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.vietocr_semantic_receipt_v2 import (
    TRANSFORMER_PROFILE_ID,
    VietOCRSemanticReceiptV2Error,
    bind_vietocr_semantic_page_v2,
    validate_vietocr_semantic_page_binding_v2,
    validate_vietocr_semantic_receipt_v2,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = Path("output/development/vietocr-multibank-family-ocr-benchmark-v1/frozen-run")
MANIFEST = RUN_ROOT / "frozen/crop_manifest.json"
REQUEST = RUN_ROOT / "frozen/reader_request.json"
RESULT = RUN_ROOT / "outputs/vgg-transformer/ocr_result.json"
RUN = RUN_ROOT / "outputs/vgg-transformer/run_manifest.json"
TIER1 = Path("tests/fixtures/source_structure/local_accounting_graph_v1_tier1_cases.json")

EXPECTED_PAGE_COUNTS = [53, 62, 99, 48, 125]
EXPECTED_RESULT_SHA256 = "4277307a95738975bb720f3d5cff19b4e432e741a5052002efffcac5343197d1"
EXPECTED_RUN_SHA256 = "6e7d3a9038ba2af6c449eff4f5bfe88df6380c02b9d378f49df21b7876ab5db7"


def _json(path: Path | str) -> dict:
    return json.loads((PROJECT_ROOT / path).read_bytes())


def _hydrated() -> bool:
    required = [MANIFEST, REQUEST, RESULT, RUN, TIER1]
    if not all((PROJECT_ROOT / path).is_file() for path in required):
        return False
    run = _json(RUN)
    external_root = Path(run["runtime"]["external_root"])
    return all(
        (external_root / artifact["path"]).is_file()
        for artifact in run["runtime"]["artifacts"].values()
    )


@contextmanager
def _temporary_json(parent: Path, value: dict) -> Iterator[Path]:
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    descriptor, raw_path = tempfile.mkstemp(
        prefix=".vietocr-v2-tamper-",
        suffix=".json",
        dir=PROJECT_ROOT / parent,
    )
    path = Path(raw_path)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
        yield path.relative_to(PROJECT_ROOT)
    finally:
        path.unlink(missing_ok=True)


@pytest.fixture(scope="module")
def authenticated_receipt():
    if not _hydrated():
        pytest.skip("frozen five-page Transformer run or pinned runtime is not hydrated")
    return validate_vietocr_semantic_receipt_v2(
        PROJECT_ROOT,
        MANIFEST,
        REQUEST,
        RESULT,
        RUN,
        expected_ocr_result_sha256=EXPECTED_RESULT_SHA256,
        expected_run_manifest_sha256=EXPECTED_RUN_SHA256,
    )


def _target_projections() -> dict[str, dict]:
    fixture = _json(TIER1)
    manifest_pages = _json(MANIFEST)["pages"]
    targets: dict[str, tuple[dict, dict]] = {}
    wanted_hashes = {page["result_ref"]["sha256"] for page in manifest_pages}
    for case in fixture["cases"]:
        provenance = case["provenance_only_not_inference"]
        for page in provenance["page_inputs"]:
            reference = page["result_ref"]
            if reference is not None and reference["sha256"] in wanted_hashes:
                targets.setdefault(reference["sha256"], (provenance, page))
    projections = {}
    for opaque_page in manifest_pages:
        result_sha = opaque_page["result_ref"]["sha256"]
        provenance, page = targets[result_sha]
        document_manifest = _json(provenance["v3_document_manifest_ref"]["path"])
        pointer = page["page_record_json_pointer"]
        record = document_manifest["page_records"][int(pointer.removeprefix("/page_records/"))]
        result = _json(page["result_ref"]["path"])
        projections[opaque_page["page_id"]] = project_authenticated_page_v2(
            page_record=record,
            page_result=result,
        )
    return projections


def _plain_payload(receipt) -> dict:
    return {
        key: receipt[key]
        for key in (
            "format_version",
            "claim_boundary",
            "experiment_id",
            "dataset_role",
            "evidence_role",
            "reader_profile",
            "inputs",
            "pages",
            "samples",
            "metrics",
            "safety",
        )
    }


def test_real_transformer_receipt_replays_complete_387_all_line_denominator(
    authenticated_receipt,
) -> None:
    receipt = authenticated_receipt
    assert receipt["metrics"] == {
        "page_count": 5,
        "sample_count": 387,
        "all_line_denominator_complete": True,
    }
    assert [page["authenticated_line_count"] for page in receipt["pages"]] == (EXPECTED_PAGE_COUNTS)
    assert receipt["reader_profile"] == {
        "profile_id": TRANSFORMER_PROFILE_ID,
        "model_name": "VietOCR VGG Transformer",
        "architecture": "vgg19_bn_transformer",
        "package_version": "0.3.13",
        "configuration_ref": {
            "path": "config/models/vietocr-0.3.13-rtx4090.toml",
            "sha256": "aa007448e2ed4f940693c3b4c03ae47111cf1ed00580d13c05a41941e5094119",
            "size_bytes": 2342,
        },
        "runtime_identity_sha256": "2f999ae5c15f209e11e0a32769a251055d970272c53fb0bc9a520fe334ae0179",
        "runtime_artifact_sha256": {
            "base_config": "9c8283fadb950f06f5d3400475f80d5355700ff315c9c48b7875e6ea66647d1c",
            "model_config": "0df9feee197754c7381871e5dfd07c6f3e292a4853eece6f1af240923e57c907",
            "weights": "380512193a8b6cbf6fad80deacdc9b6939d10d473d199892fc6408d13775ea59",
            "wheel": "07b3777e5176b0d733cb056b68bd817371605f4b3514795fbf91ad4e181b8ccf",
        },
        "runner_implementation_refs": {
            "cli": {
                "path": "scripts/models/run_vietocr_line_reader.py",
                "sha256": "0000d41962f8311c93c6817a0b9fb0f28b5405b9f5aefb876fbbfc1909d08df5",
                "size_bytes": 1169,
            },
            "reader": {
                "path": "src/bctc_ai/ocr/vietocr_line_reader.py",
                "sha256": "9b6a48d14eab452f97f80fbaeb157c625553bafee0a2411403ab1a3cf53200b6",
                "size_bytes": 21081,
            },
        },
        "selected_run_git_commit": "2f8cab8f8b352f4515c39809c2a826f0dc7a813e",
    }


def test_all_five_pages_bind_exact_projection_lines_without_ppocr_text_identity(
    authenticated_receipt,
) -> None:
    projections = _target_projections()
    bindings = []
    for page in authenticated_receipt["pages"]:
        projection = projections[page["page_id"]]
        binding = bind_vietocr_semantic_page_v2(projection, authenticated_receipt)
        assert binding["page_id"] == page["page_id"]
        assert binding["metrics"] == {
            "sample_count": page["authenticated_line_count"],
            "authenticated_line_count": page["authenticated_line_count"],
            "unique_source_line_count": page["authenticated_line_count"],
            "all_line_denominator_complete": True,
        }
        assert [sample["source_line_index"] for sample in binding["samples"]] == list(
            range(page["authenticated_line_count"])
        )
        assert all("raw_text" not in sample["source_atom"] for sample in binding["samples"])
        assert (
            validate_vietocr_semantic_page_binding_v2(
                binding,
                projection,
                authenticated_receipt,
            )
            == binding
        )
        bindings.append(binding)
    assert sum(binding["metrics"]["sample_count"] for binding in bindings) == 387


def test_plain_or_forged_dictionary_cannot_bind(authenticated_receipt) -> None:
    projection = _target_projections()["page-0001"]
    plain = _plain_payload(authenticated_receipt)
    with pytest.raises(VietOCRSemanticReceiptV2Error, match="replay-authenticated"):
        bind_vietocr_semantic_page_v2(projection, plain)

    forged = deepcopy(plain)
    forged["samples"][0]["raw_prediction"] = "Nội dung giả mạo"
    forged["samples"][0]["normalized_prediction"] = "Nội dung giả mạo"
    with pytest.raises(VietOCRSemanticReceiptV2Error, match="replay-authenticated"):
        bind_vietocr_semantic_page_v2(projection, forged)


def test_receipt_payload_rejects_one_omitted_authenticated_line(authenticated_receipt) -> None:
    omitted = _plain_payload(authenticated_receipt)
    omitted["samples"].pop(0)
    omitted["metrics"]["sample_count"] -= 1
    omitted["pages"][0]["line_sample_count"] -= 1
    with pytest.raises(VietOCRSemanticReceiptV2Error, match="all-LINE denominator"):
        receipt_v2._validate_receipt_payload(omitted)


def test_transformer_run_validator_rejects_model_artifact_hash_tamper() -> None:
    if not _hydrated():
        pytest.skip("frozen five-page Transformer run or pinned runtime is not hydrated")
    run = _json(RUN)
    run["runtime"]["artifacts"]["weights"]["sha256"] = "0" * 64
    with pytest.raises(VietOCRSemanticReceiptV2Error, match="registry drifted"):
        receipt_v2._validate_transformer_run(
            PROJECT_ROOT,
            run,
            PROJECT_ROOT / RUN,
            PROJECT_ROOT / REQUEST,
            (PROJECT_ROOT / REQUEST).read_bytes(),
            PROJECT_ROOT / RESULT,
            (PROJECT_ROOT / RESULT).read_bytes(),
            387,
        )


def test_public_validator_rejects_coordinated_transcript_and_run_manifest_tamper() -> None:
    if not _hydrated():
        pytest.skip("frozen five-page Transformer run or pinned runtime is not hydrated")
    changed_result = _json(RESULT)
    changed_result["samples"][0]["raw_prediction"] = "Nội dung giả mạo phối hợp"
    with _temporary_json(RESULT.parent, changed_result) as result_path:
        result_bytes = (PROJECT_ROOT / result_path).read_bytes()
        changed_run = _json(RUN)
        changed_run["artifacts"]["ocr_result"] = {
            "path": (PROJECT_ROOT / result_path).name,
            "sha256": hashlib.sha256(result_bytes).hexdigest(),
            "size_bytes": len(result_bytes),
        }
        with _temporary_json(RUN.parent, changed_run) as run_path:
            with pytest.raises(VietOCRSemanticReceiptV2Error, match="externally selected"):
                validate_vietocr_semantic_receipt_v2(
                    PROJECT_ROOT,
                    MANIFEST,
                    REQUEST,
                    result_path,
                    run_path,
                    expected_ocr_result_sha256=EXPECTED_RESULT_SHA256,
                    expected_run_manifest_sha256=EXPECTED_RUN_SHA256,
                )
            with pytest.raises(VietOCRSemanticReceiptV2Error, match="run manifest differs"):
                validate_vietocr_semantic_receipt_v2(
                    PROJECT_ROOT,
                    MANIFEST,
                    REQUEST,
                    result_path,
                    run_path,
                    expected_ocr_result_sha256=hashlib.sha256(result_bytes).hexdigest(),
                    expected_run_manifest_sha256=EXPECTED_RUN_SHA256,
                )


def test_crop_receipt_uses_cached_verified_bytes_not_a_swapped_path_reread(monkeypatch) -> None:
    if not _hydrated():
        pytest.skip("frozen five-page Transformer run or pinned runtime is not hydrated")
    original_file_ref = receipt_v2._file_ref
    unverified_crop_rereads: list[Path] = []

    def simulated_path_swap(root: Path, path: Path, payload: bytes | None = None):
        if path.suffix == ".png" and payload is None:
            unverified_crop_rereads.append(path)
            return {
                "path": path.relative_to(root).as_posix(),
                "sha256": "0" * 64,
                "size_bytes": 1,
            }
        return original_file_ref(root, path, payload)

    monkeypatch.setattr(receipt_v2, "_file_ref", simulated_path_swap)
    receipt = validate_vietocr_semantic_receipt_v2(
        PROJECT_ROOT,
        MANIFEST,
        REQUEST,
        RESULT,
        RUN,
        expected_ocr_result_sha256=EXPECTED_RESULT_SHA256,
        expected_run_manifest_sha256=EXPECTED_RUN_SHA256,
    )
    manifest = _json(MANIFEST)
    assert unverified_crop_rereads == []
    assert receipt["samples"][0]["crop_ref"]["sha256"] == manifest["samples"][0]["crop_sha256"]


def test_final_stable_snapshot_rejects_project_artifact_swap(monkeypatch) -> None:
    if not _hydrated():
        pytest.skip("frozen five-page Transformer run or pinned runtime is not hydrated")
    original_stable_bytes = receipt_v2._stable_bytes
    request_path = (PROJECT_ROOT / REQUEST).resolve()
    request_reads = 0

    def simulated_swap(path: Path, label: str) -> bytes:
        nonlocal request_reads
        payload = original_stable_bytes(path, label)
        if path.resolve() == request_path:
            request_reads += 1
            if request_reads >= 2:
                return payload + b" "
        return payload

    monkeypatch.setattr(receipt_v2, "_stable_bytes", simulated_swap)
    with pytest.raises(VietOCRSemanticReceiptV2Error, match="changed during receipt replay"):
        validate_vietocr_semantic_receipt_v2(
            PROJECT_ROOT,
            MANIFEST,
            REQUEST,
            RESULT,
            RUN,
            expected_ocr_result_sha256=EXPECTED_RESULT_SHA256,
            expected_run_manifest_sha256=EXPECTED_RUN_SHA256,
        )
