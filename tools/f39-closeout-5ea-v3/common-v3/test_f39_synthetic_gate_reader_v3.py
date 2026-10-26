"""Synthetic metadata/Git controls only; no corpus/PDF/SQLite/provider jobs.

Root must capture this packet in its own test branch and run from a fresh Linux
clone under the active synthetic lease. This file has NOT been run by its author.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("f39_gate_reader_v3_owned", HERE / "f39_synthetic_gate_reader_v3.py")
assert SPEC is not None and SPEC.loader is not None
READER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(READER)
RAW = (HERE / "fixtures" / "approved_full_nonlegacy_test_receipt.json").read_bytes()
REPORT = json.loads(RAW)
assert len(RAW) == READER.APPROVED_RECEIPT_BYTES
assert hashlib.sha256(RAW).hexdigest() == READER.APPROVED_RECEIPT_SHA256


def _git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.PIPE)


@pytest.fixture(scope="module")
def owned_repo(tmp_path_factory):
    source_text = os.environ.get("F39_GATE_TEST_SOURCE_REPO")
    assert source_text, "Root must explicitly select its own fresh test-branch source repo"
    source = Path(source_text)
    assert source.is_absolute() and source.is_dir()
    root = tmp_path_factory.mktemp("owned_f39_gate")
    repo = root / "repo"
    # Local shared object reads only; never mutate source branch or use network.
    subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout",
                    str(source), str(repo)], check=True)
    _git(repo, "config", "core.autocrlf", "false")
    _git(repo, "checkout", "--quiet", "--detach", READER.EXPECTED_RUNTIME_HEAD)
    assert not _git(repo, "status", "--porcelain").strip()
    return repo


@pytest.fixture
def approved_ref(tmp_path):
    path = tmp_path / "approved.json"
    path.write_bytes(RAW)  # Verbatim immutable metadata, never caller-resealed.
    return {"path": str(path), "sha256": READER.APPROVED_RECEIPT_SHA256,
            "size_bytes": READER.APPROVED_RECEIPT_BYTES}


def _validate(repo, reference, expected=None):
    return READER.validate_f39_synthetic_gate_v1(
        repo=repo, receipt_ref=reference,
        expected_head=READER.EXPECTED_RUNTIME_HEAD if expected is None else expected,
    )


def test_approved_full_gate_and_exact_docs_only_source_bridge(owned_repo, approved_ref):
    result = _validate(owned_repo, approved_ref)
    assert result["status"] == "VERIFIED_53B_SOURCE_EQUIVALENT_TO_5EA"
    assert result["selected_test_module_count"] == 28
    assert len(result["actual_source_file_proofs"]) == 35
    assert all(p["tested_blob_equals_runtime_blob_equals_actual"]
               for p in result["actual_source_file_proofs"])
    assert result["financial_acceptance"] is False
    assert result["common_or_full_corpus_execution_proven"] is False
    assert result["junit_ruff_bodies_revalidated_by_this_reader"] is False
    assert result["test_execution_evidence"] == (
        "PINNED_APPROVED_OWNER_REPORTED_EXECUTION_NOT_INDEPENDENT_ATTESTATION")


@pytest.mark.parametrize("changed", [
    {"expected": READER.TESTED_COMMIT},
    {"sha256": "0" * 64},
    {"size_bytes": READER.APPROVED_RECEIPT_BYTES + 1},
    {"size_bytes": True},
    {"extra": "caller override"},
])
def test_unapproved_ref_or_commit_does_not_become_gate(owned_repo, approved_ref, changed):
    ref = dict(approved_ref)
    expected = changed.get("expected", READER.EXPECTED_RUNTIME_HEAD)
    ref.update({k: v for k, v in changed.items() if k != "expected"})
    with pytest.raises(READER.F39SyntheticGateError):
        _validate(owned_repo, ref, expected)


@pytest.mark.parametrize("kind", ["focused", "L2", "changed_status", "truncated"])
def test_different_receipt_or_caller_reseal_rejected(owned_repo, approved_ref, kind):
    value = copy.deepcopy(REPORT)
    if kind == "focused":
        value["mode"] = "focused"
    elif kind == "L2":
        value = {"format_version": "L2_SYNTHETIC_PASS", "status": "PASS"}
    else:
        value["status"] = "FAIL_CLOSED"
    raw = json.dumps(value, sort_keys=True).encode()
    if kind == "truncated":
        raw = RAW[:-1]
    Path(approved_ref["path"]).write_bytes(raw)
    # Even a self-consistent hash supplied by the caller is not the approved pin.
    approved_ref.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    with pytest.raises(READER.F39SyntheticGateError):
        _validate(owned_repo, approved_ref)


@pytest.mark.parametrize("field,value", [
    ("mode", "focused"), ("commit", READER.EXPECTED_RUNTIME_HEAD),
    ("status", "PASS"), ("python", "3.14.0"),
    ("ruff_exit_code", 1), ("pytest_exit_code", 2), ("exit_code", False),
    ("address_space_limit", [1073741824, 1073741824]),
    ("nice", 0), ("financial_acceptance", True),
    ("real_corpus_pdf_store_jobs", True),
])
def test_fixed_report_semantics_are_explicit(field, value):
    # Pure private metadata control, not an alternative authenticated API.
    changed = copy.deepcopy(REPORT)
    changed[field] = value
    with pytest.raises(READER.F39SyntheticGateError):
        READER._validate_reported_gate(changed)


@pytest.mark.parametrize("kind", ["missing", "duplicate", "foreign_hash", "frozen", "origin", "driver"])
def test_full_module_source_and_origin_axis_not_relaxed(kind):
    value = copy.deepcopy(REPORT)
    if kind == "missing":
        value["selected_test_modules"].pop()
    elif kind == "duplicate":
        value["selected_test_modules"][0] = value["selected_test_modules"][1]
    elif kind == "foreign_hash":
        value["source_test_sha256"][value["selected_test_modules"][0]] = "f" * 64
    elif kind == "frozen":
        value["frozen_sha256"].clear()
    elif kind == "origin":
        value["import_origins"]["bctc_ai"] = "/foreign/checkout/src/bctc_ai/__init__.py"
    else:
        value["runner_scripts_sha256"].clear()
    with pytest.raises(READER.F39SyntheticGateError):
        READER._validate_reported_gate(value)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'])
def test_strict_metadata_decoder_rejects_duplicate_nonfinite(raw):
    with pytest.raises(READER.F39SyntheticGateError):
        READER._strict_json(raw)


def test_runtime_head_is_strict_even_when_tested_sources_match(owned_repo, approved_ref):
    try:
        _git(owned_repo, "checkout", "--quiet", "--detach", READER.TESTED_COMMIT)
        with pytest.raises(READER.F39SyntheticGateError):
            _validate(owned_repo, approved_ref)
    finally:
        _git(owned_repo, "checkout", "--quiet", "--detach", READER.EXPECTED_RUNTIME_HEAD)


def test_dirty_or_changed_actual_source_fails(owned_repo, approved_ref):
    path = owned_repo / "src/bctc_ai/evaluation/gemini_json_income_tax_source_label_discrepancy_v1.py"
    old = path.read_bytes()
    try:
        path.write_bytes(old + b"\n")
        with pytest.raises(READER.F39SyntheticGateError):
            _validate(owned_repo, approved_ref)
    finally:
        path.write_bytes(old)


def test_crlf_is_not_normalized_into_runtime_lf_authority(owned_repo, approved_ref):
    path = owned_repo / "src/bctc_ai/evaluation/gemini_json_income_tax_source_label_discrepancy_v1.py"
    old = path.read_bytes()
    assert b"\r\n" not in old
    try:
        _git(owned_repo, "config", "core.autocrlf", "true")
        path.write_bytes(old.replace(b"\n", b"\r\n"))
        with pytest.raises(READER.F39SyntheticGateError):
            _validate(owned_repo, approved_ref)
    finally:
        path.write_bytes(old)
        _git(owned_repo, "config", "core.autocrlf", "false")


def test_receipt_symlink_does_not_authorize_gate(owned_repo, approved_ref, tmp_path):
    alias = tmp_path / "alias.json"
    alias.symlink_to(Path(approved_ref["path"]))
    changed = {**approved_ref, "path": str(alias)}
    with pytest.raises(READER.F39SyntheticGateError):
        _validate(owned_repo, changed)


def test_cli_failure_is_nonzero_not_a_printed_pass(owned_repo, approved_ref):
    completed = subprocess.run(
        [sys.executable, "-I", "-B", str(HERE / "f39_synthetic_gate_reader_v3.py"),
         "--repo", str(owned_repo), "--receipt", approved_ref["path"],
         "--receipt-sha256", approved_ref["sha256"],
         "--receipt-bytes", str(approved_ref["size_bytes"]),
         "--expected-head", READER.TESTED_COMMIT],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 2
    assert "FAIL_CLOSED" in completed.stderr
    assert not completed.stdout
