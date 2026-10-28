"""UNRUN actual-source streamed-store/workbook goldens and publication failures.

The positive fixture ingests two real tiny page-store source records, runs the
real F36 financial rules, writes the real T8 store and independently cold-replays
it. No replay/financial validator is replaced by a passing fake.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from contextlib import contextmanager
from copy import deepcopy
from io import BytesIO
from pathlib import Path

import openpyxl
import pytest
from test_f36_notes_core_adapter_v1 import example as example
from test_f36_notes_stream_store_v1 import _ref, _two_actual

from bctc_ai.evaluation import gemini_json_f36_notes_stream_store_v1 as store
from bctc_ai.notes import f36_streamed_workbooks_v1 as target
from bctc_ai.notes.export_v1 import tm_template_rows_v1
from bctc_ai.notes.f36_canonical_workbook_v1 import build_f36_canonical_workbook_v1
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1, canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def actual_store(example, tmp_path, monkeypatch):
    corpus, trials, options = _two_actual(example, tmp_path, monkeypatch, requested=[1])
    path = tmp_path / "checked.sqlite3"
    receipt = store.ingest_f36_notes_streamed_sweep_v1(path, **options)
    return corpus, trials, options, path, receipt


def _export(case, output):
    _corpus, _trials, options, path, _receipt = case
    return target.export_f36_streamed_canonical_workbooks_v1(store_ref=_ref(path), output_directory=output, **options)


def _load(path):
    return json.loads(path.read_bytes())


def _cli():
    script = ROOT / "scripts/experiments/export_f36_streamed_canonical_workbooks_v1.py"
    spec = importlib.util.spec_from_file_location("f36_bridge_cli_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_store_all_originals_including_u_have_exact_canonical_workbooks(actual_store, tmp_path, capsys):
    corpus, trials, options, path, stored = actual_store
    original_store_ref = _ref(path)
    output = tmp_path / "publication"
    request = tmp_path / "request.json"
    request.write_bytes(canonical_json_bytes_v1({"store_ref": original_store_ref, "output_directory": str(output), **options}))
    assert _cli().main(["--request", str(request), "--expected-request-sha256", _ref(request)["sha256"]]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "PASS_EXTERNAL_PUBLICATION" and result["financial_acceptance"] is False
    assert (result["document_count"], result["ready_count"], result["unresolved_count"]) == (2, 1, 1)
    manifest = _load(output / "manifest.json")
    assert manifest["bindings"]["family_run_id"] == stored["family_run_id"]
    assert manifest["bindings"]["compiled_document_axis_sha256"] == canonical_json_sha256_v1(
        options["compiled_specs"]["topology"]["source"]["document_axis"])
    assert manifest["bindings"]["store_ref"] == original_store_ref == _ref(path)
    assert [r["document_ordinal"] for r in manifest["documents"]] == [1, 2]
    pins = {"family_run_id": stored["family_run_id"], "store_sha256": original_store_ref["sha256"],
            "bindings_sha256": result["bindings_sha256"], "product_label": target.PRODUCT_LABEL}
    for document, trial, record in zip(corpus.documents, trials, manifest["documents"], strict=True):
        expected, _ = build_f36_canonical_workbook_v1(document.identity(), trial, tm_template_rows_v1(ROOT), pins)
        assert (output / record["workbook_ref"]["path"]).read_bytes() == expected
        audit = _load(output / record["audit_ref"]["path"])
        assert audit["trial_one_lf_sha256"] == canonical_json_sha256_v1(trial)
        assert audit["trial_status"] == trial["status"] and audit["trial_reasons"] == trial["reasons"]
        assert audit["readback"]["dimensional_rows"] == len(trial["notes_ledger"]["cells"])
        workbook = openpyxl.load_workbook(BytesIO(expected))
        assert workbook.sheetnames == ["README", "TM", "DIMENSIONAL"]
        if document.ordinal == 1:
            # Independent printed-source goldens: not merely the builder oracle.
            tm = list(workbook["TM"].values)
            header = tm[0]
            current = header.index("DURATION:YEAR:2025|value")
            comparative = header.index("DURATION:YEAR:2024|value")
            placed = {row[1]: (row[current], row[comparative]) for row in tm[1:] if row[current] is not None}
            assert set(placed.values()) == {(10, 9), (20, 18), (30, 27), (60, 54)}
            assert all(row[current + 1] == "MILLION_VND" for row in tm[1:] if row[current] is not None)
        else:
            assert trial["status"] == "UNRESOLVED" and trial["reasons"] == ["DOCUMENT_OUTSIDE_REQUESTED_SCOPE"]
            assert audit["readback"]["tm_values"] == 0 and audit["mapping_count"] == 0
            assert list(workbook["TM"].values)[0] == ("order", "ReportNormId", "name")
    # Existing T8 invariants are still mandatory after projection.
    with sqlite3.connect(path) as connection:
        for table in ("family_export", "family_current_selection", "family_selection_event"):
            assert connection.execute("SELECT COUNT(*) FROM " + table).fetchone() == (0,)
    with store.open_f36_notes_streamed_run_v1(path, **options) as reader:
        assert reader.original_trial(2) == trials[1]


def test_same_authenticated_inputs_produce_identical_workbooks_and_manifests(actual_store, tmp_path):
    left, right = tmp_path / "left", tmp_path / "right"
    _export(actual_store, left)
    _export(actual_store, right)
    left_files = {p.relative_to(left).as_posix(): p.read_bytes() for p in left.rglob("*") if p.is_file()}
    right_files = {p.relative_to(right).as_posix(): p.read_bytes() for p in right.rglob("*") if p.is_file()}
    assert left_files == right_files


def test_existing_destination_is_never_overwritten_or_cleaned(actual_store, tmp_path):
    output = tmp_path / "occupied"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_bytes(b"user-owned")
    with pytest.raises(FileExistsError):
        _export(actual_store, output)
    assert sentinel.read_bytes() == b"user-owned" and list(output.iterdir()) == [sentinel]


def test_wrong_store_pin_is_rejected_before_output_creation(actual_store, tmp_path):
    _corpus, _trials, options, path, _receipt = actual_store
    wrong = {**_ref(path), "sha256": "0" * 64}
    output = tmp_path / "wrong-pin"
    with pytest.raises(target.F36StreamedWorkbookError, match="store reference differs"):
        target.export_f36_streamed_canonical_workbooks_v1(store_ref=wrong, output_directory=output, **options)
    assert not output.exists()


def test_original_axis_cannot_be_subset_to_ready_documents(actual_store, tmp_path):
    _corpus, _trials, options, path, _receipt = actual_store
    options = deepcopy(options)
    options["compiled_specs"]["topology"]["source"]["document_axis"].pop()
    output = tmp_path / "subset"
    with pytest.raises(ValueError):
        target.export_f36_streamed_canonical_workbooks_v1(store_ref=_ref(path), output_directory=output, **options)
    assert not output.exists()


def test_historical_producer_axis_without_new_bridge_is_not_silently_extended(actual_store, tmp_path):
    _corpus, _trials, options, path, _receipt = actual_store
    options = deepcopy(options)
    options["producer_refs"] = [r for r in options["producer_refs"] if r["path"] != str(Path(target.__file__).absolute())]
    output = tmp_path / "stale-code-axis"
    with pytest.raises(ValueError, match="complete exact producer package pins required"):
        target.export_f36_streamed_canonical_workbooks_v1(store_ref=_ref(path), output_directory=output, **options)
    assert not output.exists()


def test_cli_rejects_request_byte_tamper_before_creating_output(tmp_path):
    request = tmp_path / "request.json"
    request.write_bytes(b"{}\n")
    with pytest.raises(ValueError, match="exact request SHA-256 required"):
        _cli().main(["--request", str(request), "--expected-request-sha256", "0" * 64])
    assert sorted(p.name for p in tmp_path.iterdir()) == ["request.json"]


def test_real_t8_late_store_mutation_fails_and_removes_every_staged_output(actual_store, tmp_path, monkeypatch):
    _corpus, _trials, _options, path, _receipt = actual_store
    original = target._write
    observed = []

    def mutate_after_staging(destination, raw, owned):
        ref = original(destination, raw, owned)
        if destination.name == "document-000002.audit.json":
            assert not (destination.parent.parent / "manifest.json").exists()
            assert not (destination.parent.parent / "receipt.json").exists()
            with sqlite3.connect(path) as connection:
                connection.execute("UPDATE family_trial SET mapping_count=mapping_count+1 WHERE document_ordinal=1")
            observed.append(True)
        return ref

    monkeypatch.setattr(target, "_write", mutate_after_staging)
    output = tmp_path / "late-mutation"
    with pytest.raises(ValueError):
        _export(actual_store, output)
    assert observed == [True] and not output.exists()


def test_reader_exit_failure_cannot_publish_or_leave_staged_workbooks(actual_store, tmp_path, monkeypatch):
    original = target.open_f36_notes_streamed_run_v1
    observed = []

    @contextmanager
    def fail_after_real_reader(*args, **kwargs):
        with original(*args, **kwargs) as reader:
            yield reader
        observed.append(True)
        raise RuntimeError("injected after genuine reader exit")

    monkeypatch.setattr(target, "open_f36_notes_streamed_run_v1", fail_after_real_reader)
    output = tmp_path / "late-verification"
    with pytest.raises(RuntimeError, match="after genuine reader exit"):
        _export(actual_store, output)
    assert observed == [True] and not output.exists()


def test_staged_workbook_tamper_is_detected_before_publication(actual_store, tmp_path, monkeypatch):
    original = target._write

    def corrupt_staged_workbook(destination, raw, owned):
        ref = original(destination, raw, owned)
        if destination.name == "document-000002.audit.json":
            (destination.parent / "document-000001.xlsx").write_bytes(b"tampered workbook")
        return ref

    monkeypatch.setattr(target, "_write", corrupt_staged_workbook)
    output = tmp_path / "tamper"
    with pytest.raises(target.F36StreamedWorkbookError, match="staged output changed"):
        _export(actual_store, output)
    assert not output.exists()


@pytest.mark.parametrize("name", ["document-000001.xlsx", "manifest.json", "receipt.json"])
def test_publication_write_failure_has_no_leftbehind(actual_store, tmp_path, monkeypatch, name):
    original = target._write

    def fail_owned_write(destination, raw, owned):
        if destination.name == name:
            # A real partial exclusive file is owned and must also be removed.
            original(destination, b"partial", owned)
            raise OSError("injected publication write failure")
        return original(destination, raw, owned)

    monkeypatch.setattr(target, "_write", fail_owned_write)
    output = tmp_path / "write-failure"
    with pytest.raises(OSError, match="publication write failure"):
        _export(actual_store, output)
    assert not output.exists()
