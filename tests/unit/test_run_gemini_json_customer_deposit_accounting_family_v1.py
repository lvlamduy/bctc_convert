from __future__ import annotations

import copy
import importlib.util
import os
import shutil
import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest
from test_gemini_json_customer_deposit_indexed_wiring_v1 import (
    _fixture as _indexed_fixture,
)
from test_gemini_json_customer_deposit_indexed_wiring_v1 import (
    _json as _family_spec,
)

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    build_gemini_json_flat_family_sweep_v1,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "scripts/experiments/run_gemini_json_customer_deposit_accounting_family_v1.py"
SPEC = importlib.util.spec_from_file_location("run_customer_deposit_family_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _database(path: Path) -> dict[str, object]:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE authority(value TEXT NOT NULL)")
    connection.execute("INSERT INTO authority VALUES ('source-a')")
    connection.commit()
    connection.close()
    payload = path.read_bytes()
    return {"path": path.name, "sha256": sha256(payload).hexdigest(), "size_bytes": len(payload)}


def test_authenticated_snapshot_is_one_immutable_source_view(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    reference = _database(source)
    with runner._authenticated_sqlite_snapshot(source, reference=reference) as guard:
        assert guard.path != source
        assert guard.path.read_bytes() == source.read_bytes()
        assert oct(guard.path.stat().st_mode & 0o777) == "0o444"
        connection = sqlite3.connect(f"file:{guard.path}?mode=ro", uri=True)
        assert connection.execute("SELECT value FROM authority").fetchone()[0] == "source-a"
        connection.close()
        guard.validate()


def test_authenticated_snapshot_rejects_sidecar_and_path_replacement(tmp_path: Path) -> None:
    source = tmp_path / "source.sqlite3"
    reference = _database(source)
    sidecar = Path(f"{source}-wal")
    sidecar.write_bytes(b"not-authoritative")
    with pytest.raises(
        runner.RunGeminiJsonCustomerDepositAccountingFamilyV1Error,
        match="sidecar",
    ):
        with runner._authenticated_sqlite_snapshot(source, reference=reference):
            pass
    sidecar.unlink()

    original = tmp_path / "original.sqlite3"
    with pytest.raises(
        runner.RunGeminiJsonCustomerDepositAccountingFamilyV1Error,
        match="changed during use",
    ):
        with runner._authenticated_sqlite_snapshot(source, reference=reference):
            os.replace(source, original)
            shutil.copyfile(original, source)


def test_authenticated_source_repair_replays_full_page_and_crop(tmp_path: Path) -> None:
    source = tmp_path / "fixture.pdf"
    document = runner.fitz.open()
    page = document.new_page(width=72, height=72)
    page.insert_text((30, 36), "-")
    document.save(source)
    document.close()
    payload = source.read_bytes()
    source_sha256 = sha256(payload).hexdigest()
    with runner.fitz.open(stream=payload, filetype="pdf") as opened:
        rendered = runner.render_full_pdf_page_v1(
            opened[0], physical_page=1, dpi=300, source_sha256=source_sha256
        )
    with runner.Image.open(runner.BytesIO(rendered.image)) as image:
        image.load()
        rgb = image.convert("RGB")
        bbox = [0, 0, rgb.width, rgb.height]
        crop = rgb.crop(tuple(bbox))
    repair = {
        "crop_evidence": {
            "bbox_pixels_xyxy": bbox,
            "pixel_height": crop.height,
            "pixel_width": crop.width,
            "rgb_sha256": sha256(crop.tobytes()).hexdigest(),
        },
        "locator": {"physical_page": 1},
        "render": {
            "image_sha256": sha256(rendered.image).hexdigest(),
            "image_size_bytes": len(rendered.image),
            "media_type": "image/png",
            "physical_page": 1,
            "pixel_height": rgb.height,
            "pixel_width": rgb.width,
            "render_dpi": 300,
            "render_receipt_sha256": runner.canonical_json_sha256_v1(
                rendered.receipt
            ),
        },
        "source": {
            "source_logical_name": source.name,
            "source_sha256": source_sha256,
            "source_size_bytes": len(payload),
        },
    }

    assert runner._authenticate_source_repairs_v1(
        repairs=[repair], source_pdf_root=tmp_path
    ) == [repair]
    tampered = copy.deepcopy(repair)
    tampered["crop_evidence"]["rgb_sha256"] = "0" * 64
    with pytest.raises(
        runner.RunGeminiJsonCustomerDepositAccountingFamilyV1Error,
        match="render or crop evidence drifted",
    ):
        runner._authenticate_source_repairs_v1(
            repairs=[tampered], source_pdf_root=tmp_path
        )


def test_audit_content_rejects_changed_axis_without_matching_seals() -> None:
    axes = {
        "clusters": [],
        "equations": [],
        "historical_comparator": [],
        "mappings": [],
        "optional_customer_views": [],
        "source_repairs": [],
    }
    material = {
        "axes": axes,
        "axis_counts": {name: 0 for name in axes},
        "axis_sha256": {name: runner.canonical_json_sha256_v1(axis) for name, axis in axes.items()},
        "audit_metrics": {},
        "claim_boundary": "fixture",
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_oracle_ref": {},
        "query_evidence_id": "fixture",
        "query_receipt": {},
        "selected_page_json_frontier_sha256": "0" * 64,
        "spec_refs": {},
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_ref": {},
    }
    value = {
        **material,
        "audit_id": "gjfcdeav1:audit:" + runner.canonical_json_sha256_v1(material),
    }
    assert runner.validate_customer_deposit_experimental_audit_content_v1(value) == value
    value["axes"]["mappings"].append({"coefficient": 999})
    with pytest.raises(
        runner.RunGeminiJsonCustomerDepositAccountingFamilyV1Error,
        match="axis seal",
    ):
        runner.validate_customer_deposit_experimental_audit_content_v1(value)


def test_historical_comparator_allows_only_fully_disjoint_expansion_corpus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oracle = {
        "metrics": {"mapping_verified_count": 0},
        "trials": [
            {"source_pdf_sha256": "a" * 64, "verified_mappings": []},
            {"source_pdf_sha256": "b" * 64, "verified_mappings": []},
        ],
    }
    monkeypatch.setattr(
        runner,
        "_historical_oracle",
        lambda: ({"fixture": "oracle"}, oracle),
    )

    axis, oracle_ref = runner._historical_comparator_axis(
        trials=[{"source_sha256": "c" * 64, "status": "fixture"}],
        compiled_specs={"bindings": {}},
    )

    assert axis == []
    assert oracle_ref == {"fixture": "oracle"}


def test_historical_comparator_rejects_partial_oracle_source_frontier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oracle = {
        "metrics": {"mapping_verified_count": 0},
        "trials": [
            {"source_pdf_sha256": "a" * 64, "verified_mappings": []},
            {"source_pdf_sha256": "b" * 64, "verified_mappings": []},
        ],
    }
    monkeypatch.setattr(
        runner,
        "_historical_oracle",
        lambda: ({"fixture": "oracle"}, oracle),
    )

    with pytest.raises(
        runner.RunGeminiJsonCustomerDepositAccountingFamilyV1Error,
        match="only partially present",
    ):
        runner._historical_comparator_axis(
            trials=[{"source_sha256": "a" * 64, "status": "fixture"}],
            compiled_specs={"bindings": {}},
        )


def test_release_pins_allow_nonrelease_corpus_only_for_experimental_run() -> None:
    kwargs = {
        "index": {"corpus_manifest_index_id": "gjfccmiv1:index:" + "f" * 64},
        "selected_ids": [],
        "sweep": {},
        "indexed": {},
        "audit": {},
    }

    runner._assert_release_pins(**kwargs, run_kind="EXPERIMENTAL")
    with pytest.raises(
        runner.RunGeminiJsonCustomerDepositAccountingFamilyV1Error,
        match="requires the frozen release corpus",
    ):
        runner._assert_release_pins(**kwargs, run_kind="OFFICIAL")


def test_audit_replay_rejects_coherent_axis_and_embedded_schema_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "_historical_comparator_axis",
        lambda **_kwargs: ([], {"fixture": "historical-oracle"}),
    )
    database, selected, evidence, trials, compiled = _indexed_fixture(tmp_path)
    topology = _family_spec("tm-customer-deposit-classification-topology-v1.json")
    evaluation = _family_spec("tm-customer-deposit-classification-evaluation-v1.json")
    schema = _family_spec("tm-customer-deposit-classification-schema-binding-v1.json")
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "a" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=evidence,
    )
    sweep_output = tmp_path / "sweep.json"
    sweep_output.write_bytes(runner.canonical_json_bytes_v1(sweep))
    spec_refs = {
        "evaluation": {"fixture": "evaluation"},
        "schema_binding": {"fixture": "schema_binding"},
        "topology": {"fixture": "topology"},
    }
    audit = runner.build_customer_deposit_experimental_audit_v1(
        sweep=sweep,
        sweep_output=sweep_output,
        selected_page_json_version_ids=selected,
        indexed_query_evidence=evidence,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    replay_args = {
        "database": database,
        "sweep": sweep,
        "sweep_output": sweep_output,
        "selected_page_json_version_ids": selected,
        "indexed_query_evidence": evidence,
        "trials": trials,
        "compiled_specs": compiled,
        "spec_refs": spec_refs,
    }
    assert (
        runner.validate_customer_deposit_experimental_audit_replay_v1(audit, **replay_args) == audit
    )

    forged_audit = copy.deepcopy(audit)
    forged_audit["axes"]["mappings"][0]["coefficients"][0] += 777
    forged_audit["axis_sha256"]["mappings"] = runner.canonical_json_sha256_v1(
        forged_audit["axes"]["mappings"]
    )
    material = {key: value for key, value in forged_audit.items() if key != "audit_id"}
    forged_audit["audit_id"] = "gjfcdeav1:audit:" + runner.canonical_json_sha256_v1(material)
    runner.validate_customer_deposit_experimental_audit_content_v1(forged_audit)
    with pytest.raises(
        runner.RunGeminiJsonCustomerDepositAccountingFamilyV1Error,
        match="does not replay exactly",
    ):
        runner.validate_customer_deposit_experimental_audit_replay_v1(forged_audit, **replay_args)

    forged_sweep = copy.deepcopy(sweep)
    forged_sweep["specs"]["schema_binding"]["value"]["family_root_report_norm_id"] = 999999
    forged_sweep["specs"]["schema_binding"]["sha256"] = runner.canonical_json_sha256_v1(
        forged_sweep["specs"]["schema_binding"]["value"]
    )
    sweep_material = {key: value for key, value in forged_sweep.items() if key != "sweep_id"}
    forged_sweep["sweep_id"] = "gjfafsv1:sweep:" + runner.canonical_json_sha256_v1(sweep_material)
    with pytest.raises(
        runner.RunGeminiJsonCustomerDepositAccountingFamilyV1Error,
        match="caller and embedded compiled specs differ",
    ):
        runner.validate_customer_deposit_experimental_audit_replay_v1(
            audit,
            **{
                **replay_args,
                "sweep": forged_sweep,
                "indexed_query_evidence": forged_sweep["indexed_query_evidence"],
                "trials": forged_sweep["trials"],
            },
        )
