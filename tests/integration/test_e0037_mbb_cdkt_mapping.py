from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from bctc_ai.evaluation import e0037_sealed_mapping as sealed_mapping
from bctc_ai.evaluation.e0037_evidence_assembly import (
    SOURCE_STRUCTURE_CANONICAL_SHA256,
    SOURCE_STRUCTURE_CANONICAL_SIZE_BYTES,
    SOURCE_STRUCTURE_CANONICALIZATION,
    assemble_source_only_structure,
    canonical_payload_identity,
    validate_source_only_structure,
)
from bctc_ai.evaluation.e0037_sealed_mapping import (
    CONTROL_RELATIVE_PATH,
    MAPPING_ONLY_RELATIVE_PATH,
    MAPPING_ONLY_STATE,
    MAPPING_SEAL_RELATIVE_PATH,
    MAPPING_SEAL_STATE,
    POSTJOIN_RELATIVE_PATH,
    POSTJOIN_STATE,
    SOURCE_STRUCTURE_RELATIVE_PATH,
    SOURCE_STRUCTURE_STATE,
    E0037SealedMappingError,
    _assemble_postjoin_cells,
    _load_control,
    _load_e0035_from_phase,
    _load_exact_cdkt_projection,
    _materialize_stable_payloads,
    _postjoin_dynamic_claim,
    _postjoin_period_unit_summary,
    _StableFile,
    _validate_e0030_axes,
    _validate_e0034_cells,
    _validated_projection_ids,
    _verify_artifact_record,
)


def _control(project_root: Path) -> dict[str, object]:
    payload = yaml.safe_load((project_root / CONTROL_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _stable_fixture(path: Path, relative: str, payload: bytes = b"{}") -> _StableFile:
    return _StableFile(
        path=path,
        payload=payload,
        identity=(1, 2, 0o100644, len(payload), 3, 4),
        artifact={
            "path": relative,
            "size_bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
    )


def test_control_separates_source_mapping_seal_and_postjoin_authority(project_root):
    control = _control(project_root)

    assert control["phase_outputs"] == {
        "source_structure": {
            "path": SOURCE_STRUCTURE_RELATIVE_PATH.as_posix(),
            "required_state": SOURCE_STRUCTURE_STATE,
            "canonical_payload": {
                "encoding": SOURCE_STRUCTURE_CANONICALIZATION,
                "sha256": SOURCE_STRUCTURE_CANONICAL_SHA256,
                "size_bytes": SOURCE_STRUCTURE_CANONICAL_SIZE_BYTES,
            },
            "published_bytes_equal_canonical_payload": True,
        },
        "mapping_only": {
            "path": MAPPING_ONLY_RELATIVE_PATH.as_posix(),
            "required_state": MAPPING_ONLY_STATE,
        },
        "mapping_seal": {
            "path": MAPPING_SEAL_RELATIVE_PATH.as_posix(),
            "required_state": MAPPING_SEAL_STATE,
        },
        "postjoin": {
            "path": POSTJOIN_RELATIVE_PATH.as_posix(),
            "required_state": POSTJOIN_STATE,
        },
    }
    assert control["fixed_cardinality"] == {
        "page_rows": {3: 39, 4: 25},
        "row_count": 64,
        "schema_disposition_count": 77,
        "period_axis_count_per_page": 2,
        "cell_count": 128,
    }
    phase_claims = control["phase_claim_boundaries"]
    pre_postjoin_claims = " ".join(
        phase_claims[name] for name in ("source_structure", "mapping_only", "mapping_seal")
    )
    assert "2026-03-31" not in pre_postjoin_claims
    assert "2025-12-31" not in pre_postjoin_claims
    assert "VND" not in pre_postjoin_claims
    assert "2026-03-31" not in phase_claims["postjoin"]
    assert "2025-12-31" not in phase_claims["postjoin"]
    assert "VND" not in phase_claims["postjoin"]
    integration_source = (
        project_root / "src/bctc_ai/evaluation/e0037_sealed_mapping.py"
    ).read_text(encoding="utf-8")
    for authoritative_answer in (
        "2026-03-31",
        "2025-12-31",
        '"VND"',
        "1_000_000",
        "triu đồng",
        "triệu đồng",
    ):
        assert authoritative_answer not in integration_source
        assert authoritative_answer not in (project_root / CONTROL_RELATIVE_PATH).read_text(
            encoding="utf-8"
        )

    mapping_phase = control["mapping_only_phase"]
    assert isinstance(mapping_phase, dict)
    permitted = mapping_phase["permitted_frozen_inputs"]
    assert isinstance(permitted, dict)
    assert set(permitted) == {
        "e0035_seal",
        "e0035_crop_manifest",
        "e0036_request",
        "e0036_baseline_output_seal",
        "vietocr_result",
        "deepseek_result",
        "cdkt_workbook",
        "hierarchy_config",
        "cdkt_hierarchy_workbook",
        "scope_policy",
        "mapping_policy",
    }
    forbidden = ("e-0030", "e-0033", "e-0034", "review", "history", "qwen", "numeric")
    assert all(
        not any(token in record["path"].casefold() for token in forbidden)
        for record in permitted.values()
    )
    assert control["mapping_seal_phase"] == {
        "permitted_dynamic_input": "mapping_only_output_plus_exact_deterministic_replay",
        "mapper_authentication_replay_required": True,
        "exact_replay_byte_equality_required": True,
        "postjoin_inputs_may_be_opened": False,
    }
    postjoin = control["postjoin_phase"]
    assert postjoin["mapper_may_be_invoked"] is False
    assert set(postjoin["permitted_frozen_inputs"]) == {
        "table_metadata",
        "numeric_verification",
    }
    assert postjoin["transitive_e0033_binding"]["direct_open_allowed"] is False

    implementation_records = {
        **control["source_structure_phase"]["implementation"],
        **mapping_phase["implementation"],
    }
    assert set(implementation_records) == {
        "source_assembler",
        "source_structure_validator",
        "mapper",
        "integration",
        "capture_script",
    }
    for name, record in implementation_records.items():
        assert set(record) == {"path", "sha256", "size_bytes"}, name
        stable = _verify_artifact_record(project_root, record, f"E-0037 {name}")
        assert stable.artifact == record


def test_source_assembly_matches_the_precommitted_canonical_identity(project_root):
    payload = assemble_source_only_structure(project_root)

    validate_source_only_structure(payload)
    assert canonical_payload_identity(payload) == {
        "canonicalization": SOURCE_STRUCTURE_CANONICALIZATION,
        "sha256": SOURCE_STRUCTURE_CANONICAL_SHA256,
        "size_bytes": SOURCE_STRUCTURE_CANONICAL_SIZE_BYTES,
    }
    source_contract = _control(project_root)["phase_outputs"]["source_structure"]
    assert source_contract["canonical_payload"] == {
        "encoding": SOURCE_STRUCTURE_CANONICALIZATION,
        "sha256": SOURCE_STRUCTURE_CANONICAL_SHA256,
        "size_bytes": SOURCE_STRUCTURE_CANONICAL_SIZE_BYTES,
    }


def test_exact_cdkt_projection_is_history_free_and_in_workbook_display_order(project_root):
    control, _control_stable = _load_control(project_root, CONTROL_RELATIVE_PATH)
    records = control["mapping_only_phase"]["permitted_frozen_inputs"]
    names = {
        "cdkt_workbook",
        "hierarchy_config",
        "cdkt_hierarchy_workbook",
        "scope_policy",
        "mapping_policy",
    }
    stable_inputs = {
        name: _verify_artifact_record(project_root, records[name], f"E-0037 {name}")
        for name in names
    }

    with _materialize_stable_payloads(
        project_root,
        stable_inputs,
        (
            "cdkt_workbook",
            "cdkt_hierarchy_workbook",
            "scope_policy",
        ),
    ) as parser_paths:
        projection, evidence, _scope_policy = _load_exact_cdkt_projection(
            project_root,
            stable_inputs,
            parser_paths,
        )

    assert len(projection.nodes) == 77
    assert _validated_projection_ids(evidence) == [node.report_norm_id for node in projection.nodes]
    assert projection.projection_sha256 == (
        "7025ca729c01a3f2030af38e9745a0ee8d72b1dad60c8d4e3b7cf749e5eb860c"
    )
    assert evidence["projection_sha256"] == projection.projection_sha256
    assert [node["display_order"] for node in evidence["nodes"]] == list(range(77))
    assert [node["report_norm_id"] for node in evidence["nodes"]][64:67] == [4337, 4373, 4338]
    assert all("histor" not in key.casefold() for node in evidence["nodes"] for key in node)
    assert all(
        set(node)
        == {
            "display_order",
            "report_norm_id",
            "display_name",
            "structural_aliases",
            "parent_report_norm_id",
            "child_report_norm_ids",
            "hierarchy_level",
            "section_path",
            "scopes",
            "previous_report_norm_id",
            "next_report_norm_id",
        }
        for node in evidence["nodes"]
    )
    tampered = deepcopy(evidence)
    tampered["nodes"][0]["display_name"] += " forged history alias"
    with pytest.raises(E0037SealedMappingError, match="projection digest"):
        _validated_projection_ids(tampered)


def test_mapping_only_runs_from_authenticated_bytes_without_postjoin_access(
    project_root,
    monkeypatch,
):
    mapping_output = project_root / MAPPING_ONLY_RELATIVE_PATH
    mapping_output_before = mapping_output.read_bytes() if mapping_output.is_file() else None
    source_payload = assemble_source_only_structure(project_root)
    validate_source_only_structure(source_payload)
    source_bytes = json.dumps(
        source_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert hashlib.sha256(source_bytes).hexdigest() == SOURCE_STRUCTURE_CANONICAL_SHA256
    assert len(source_bytes) == SOURCE_STRUCTURE_CANONICAL_SIZE_BYTES
    source_path = project_root / SOURCE_STRUCTURE_RELATIVE_PATH
    source_stable = _StableFile(
        path=source_path,
        payload=source_bytes,
        identity=(1, 2, 0o100644, len(source_bytes), 3, 4),
        artifact={
            "path": SOURCE_STRUCTURE_RELATIVE_PATH.as_posix(),
            "size_bytes": len(source_bytes),
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
        },
    )
    original_read = sealed_mapping._read_stable_file
    opened_paths: list[str] = []

    def read_with_ephemeral_seal_a(root, path, label, **kwargs):
        absolute = path if path.is_absolute() else root / path
        try:
            relative = absolute.relative_to(project_root).as_posix()
        except ValueError:
            relative = absolute.as_posix()
        opened_paths.append(relative.casefold())
        if absolute == source_path:
            return source_stable
        return original_read(root, path, label, **kwargs)

    monkeypatch.setattr(sealed_mapping, "_clean_git_commit", lambda _root: "a" * 40)
    monkeypatch.setattr(sealed_mapping, "_read_stable_file", read_with_ephemeral_seal_a)

    payload = sealed_mapping.capture_e0037_mapping_only(
        project_root,
        _authentication_replay=True,
    )
    rows, dispositions = sealed_mapping._validate_mapping_only_payload(payload)

    assert len(rows) == 64
    assert len(dispositions) == 77
    assert payload["access_contract"]["mapping_function_invocation_count"] == 1
    assert payload["access_contract"]["e0030_opened"] is False
    assert payload["access_contract"]["e0033_opened"] is False
    assert payload["access_contract"]["e0034_opened"] is False
    assert all(
        not any(token in path for token in ("e-0030", "e-0033", "e-0034", "qwen", "review"))
        for path in opened_paths
    )
    if mapping_output_before is None:
        assert not mapping_output.exists()
    else:
        assert mapping_output.read_bytes() == mapping_output_before


def test_postjoin_schema_preserves_scope_axes_units_numeric_statuses_and_scaling(project_root):
    control = _control(project_root)
    postjoin = control["postjoin_phase"]
    table_path = project_root / postjoin["permitted_frozen_inputs"]["table_metadata"]["path"]
    numeric_path = (
        project_root / postjoin["permitted_frozen_inputs"]["numeric_verification"]["path"]
    )
    table_payload = json.loads(table_path.read_text(encoding="utf-8"))
    numeric_payload = json.loads(numeric_path.read_text(encoding="utf-8"))

    axes = _validate_e0030_axes(table_payload)
    period_unit_summary = _postjoin_period_unit_summary(axes)
    numeric_cells = _validate_e0034_cells(
        numeric_payload,
        postjoin["transitive_e0033_binding"],
    )
    mapping_rows = [
        {
            "row_id": f"page-{page:04d}-row-{row:03d}-label",
            "mapping": {
                "status": "RESOLVED_PATH",
                "selected_report_norm_id": 10_000 + order,
                "candidate_report_norm_ids": [10_000 + order],
            },
        }
        for order, (page, row) in enumerate(
            (page, row) for page, count in ((3, 39), (4, 25)) for row in range(count)
        )
    ]

    cells = _assemble_postjoin_cells(project_root, mapping_rows, numeric_cells, axes)

    assert len(cells) == 128
    assert Counter(cell["numeric_verification_status"] for cell in cells) == {
        "VERIFIED_OBSERVED_VALUE": 113,
        "VERIFIED_OBSERVED_DASH": 5,
        "UNRESOLVED_BLANK_PENDING_ROW_SEMANTICS": 9,
        "UNRESOLVED_READER_DISAGREEMENT": 1,
    }
    assert Counter(cell["output_status"] for cell in cells) == {
        "OBSERVED_VALUE": 113,
        "DASH": 5,
        "UNRESOLVED": 10,
    }
    assert all(cell["report_scope"] == "UNKNOWN" for cell in cells)
    assert all(cell["period_axis"]["raw_unit_text"] == "triu đồng" for cell in cells)
    assert all(cell["period_axis"]["matched_unit_anchor"] == "triệu đồng" for cell in cells)
    assert all(cell["canonical_unit"] == "VND" for cell in cells)
    assert all(cell["unit_multiplier"] == 1_000_000 for cell in cells)
    assert all(
        cell["period_axis"]["period_start"] == cell["period_axis"]["period_end"] for cell in cells
    )
    assert period_unit_summary == {
        "period_type": "SNAPSHOT",
        "current_period_start": "2026-03-31",
        "current_period_end": "2026-03-31",
        "comparative_period_start": "2025-12-31",
        "comparative_period_end": "2025-12-31",
        "raw_unit_text": "triu đồng",
        "matched_unit_anchor": "triệu đồng",
        "canonical_unit": "VND",
        "unit_multiplier": 1_000_000,
        "report_scope": "UNKNOWN",
    }
    final_claim = _postjoin_dynamic_claim(period_unit_summary)
    assert "2026-03-31" in final_claim
    assert "2025-12-31" in final_claim
    assert "VND" in final_claim

    for cell in cells:
        assert set(cell) == {
            "cell_id",
            "row_id",
            "page",
            "row_ordinal",
            "axis_ordinal",
            "period_axis",
            "report_scope",
            "mapping_status",
            "candidate_report_norm_ids",
            "selected_report_norm_id",
            "source_observation",
            "numeric_verification_status",
            "cell_status",
            "output_status",
            "selected_raw_value",
            "selected_normalized_value",
            "displayed_unit_value",
            "displayed_unit_raw_text",
            "displayed_unit",
            "canonical_unit",
            "unit_multiplier",
            "canonical_unit_value",
            "visible_raw_value",
            "numeric_evidence",
        }
        if cell["numeric_verification_status"] == "VERIFIED_OBSERVED_VALUE":
            assert cell["canonical_unit_value"] == str(
                int(Decimal(cell["displayed_unit_value"]) * Decimal(1_000_000))
            )
        elif cell["numeric_verification_status"] == "VERIFIED_OBSERVED_DASH":
            assert cell["source_observation"] == "DASH"
            assert cell["visible_raw_value"] == "-"
            assert cell["displayed_unit_value"] is None
            assert cell["canonical_unit_value"] is None
        else:
            assert cell["selected_normalized_value"] is None
            assert cell["canonical_unit_value"] is None
            assert cell["numeric_evidence"]["challenger"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("axis_right_edge", float("nan")),
        ("distinct_semantics_margin", float("inf")),
        ("header_bbox", [10.0, 0.0, 5.0, 1.0]),
        ("unit_bbox", [0.0, 3.0, 2.0, 1.0]),
    ],
)
def test_e0030_axis_validation_rejects_nonfinite_or_inverted_geometry(
    project_root,
    field,
    value,
):
    control = _control(project_root)
    record = control["postjoin_phase"]["permitted_frozen_inputs"]["table_metadata"]
    payload = json.loads((project_root / record["path"]).read_text(encoding="utf-8"))
    payload["after"][0]["axes"][0][field] = value

    with pytest.raises(E0037SealedMappingError, match="visible axis semantics"):
        _validate_e0030_axes(payload)


def test_mapping_rejects_uncommitted_seal_a_before_opening_schema_or_readers(
    tmp_path,
    monkeypatch,
):
    source = tmp_path / "source_structure.json"
    output = tmp_path / "mapping_only.json"
    source_contract = {
        "path": SOURCE_STRUCTURE_RELATIVE_PATH.as_posix(),
        "canonical_payload": {
            "sha256": "f" * 64,
            "size_bytes": 2,
        },
    }
    control = {
        "phase_outputs": {"source_structure": source_contract},
        "mapping_only_phase": {
            "exact_schema_projection": {
                "statement_type": "CDKT",
                "node_count": 77,
                "order_authority": "WORKBOOK_DISPLAY_ORDER_ONLY",
                "numeric_report_norm_id_sort_allowed": False,
                "historical_aliases_allowed": False,
                "projection_sha256": (
                    "7025ca729c01a3f2030af38e9745a0ee8d72b1dad60c8d4e3b7cf749e5eb860c"
                ),
            }
        },
    }
    control_stable = _stable_fixture(tmp_path / "control.yaml", "config/control.yaml")
    tampered = _stable_fixture(source, SOURCE_STRUCTURE_RELATIVE_PATH.as_posix())
    events: list[str] = []

    monkeypatch.setattr(sealed_mapping, "_clean_git_commit", lambda _root: "a" * 40)
    monkeypatch.setattr(
        sealed_mapping,
        "_load_control",
        lambda _root, _path: (control, control_stable),
    )
    monkeypatch.setattr(sealed_mapping, "_phase_output_path", lambda *_args: output)
    monkeypatch.setattr(sealed_mapping, "_canonical_argument", lambda *_args: source)

    def read_source(*_args, **_kwargs):
        events.append("seal_a")
        return tampered

    def forbidden_phase_open(*_args, **_kwargs):
        events.append("schema_or_reader")
        raise AssertionError("schema/readers opened before Seal A authentication")

    monkeypatch.setattr(sealed_mapping, "_read_stable_file", read_source)
    monkeypatch.setattr(sealed_mapping, "_verify_phase_records", forbidden_phase_open)

    with pytest.raises(E0037SealedMappingError, match="Seal A differs"):
        sealed_mapping.capture_e0037_mapping_only(tmp_path)
    assert events == ["seal_a"]


def test_source_registry_rejects_an_extra_input_before_opening_any_record(
    tmp_path,
    monkeypatch,
):
    phase = {
        "permitted_inputs": {
            "e0035_seal": {},
            "e0035_crop_manifest": {},
            "forbidden_schema": {},
        }
    }
    events: list[str] = []

    def forbidden_open(*_args, **_kwargs):
        events.append("opened")
        raise AssertionError("registry was opened before exact-key validation")

    monkeypatch.setattr(sealed_mapping, "_verify_phase_records", forbidden_open)

    with pytest.raises(E0037SealedMappingError, match="registry keyset"):
        _load_e0035_from_phase(tmp_path, phase)
    assert events == []


def test_mapping_preflights_implementation_hashes_before_opening_mapping_inputs(
    tmp_path,
    monkeypatch,
):
    source = tmp_path / "source_structure.json"
    output = tmp_path / "mapping_only.json"
    source_contract = {
        "path": SOURCE_STRUCTURE_RELATIVE_PATH.as_posix(),
        "canonical_payload": {"sha256": "f" * 64, "size_bytes": 2},
    }
    control = {
        "phase_outputs": {"source_structure": source_contract},
        "mapping_only_phase": {
            "exact_schema_projection": {
                "statement_type": "CDKT",
                "node_count": 77,
                "order_authority": "WORKBOOK_DISPLAY_ORDER_ONLY",
                "numeric_report_norm_id_sort_allowed": False,
                "historical_aliases_allowed": False,
                "projection_sha256": (
                    "7025ca729c01a3f2030af38e9745a0ee8d72b1dad60c8d4e3b7cf749e5eb860c"
                ),
            },
            "implementation": {
                "source_structure_validator": {
                    "path": "src/bctc_ai/evaluation/e0037_evidence_assembly.py"
                },
                "mapper": {"path": "src/bctc_ai/mapping/ordered_subgraph_v2.py"},
                "integration": {"path": "src/bctc_ai/evaluation/e0037_sealed_mapping.py"},
                "capture_script": {"path": "scripts/experiments/capture_e0037_mbb_cdkt_mapping.py"},
            },
        },
    }
    control_stable = _stable_fixture(tmp_path / "control.yaml", "config/control.yaml")
    source_stable = _stable_fixture(source, SOURCE_STRUCTURE_RELATIVE_PATH.as_posix())
    source_stable.artifact.update(source_contract["canonical_payload"])
    events: list[str] = []

    monkeypatch.setattr(sealed_mapping, "_clean_git_commit", lambda _root: "a" * 40)
    monkeypatch.setattr(
        sealed_mapping,
        "_load_control",
        lambda _root, _path: (control, control_stable),
    )
    monkeypatch.setattr(sealed_mapping, "_phase_output_path", lambda *_args: output)
    monkeypatch.setattr(sealed_mapping, "_canonical_argument", lambda *_args: source)
    monkeypatch.setattr(
        sealed_mapping,
        "_read_stable_file",
        lambda *_args, **_kwargs: source_stable,
    )

    def forbidden_mapping_input_open(*_args, **_kwargs):
        events.append("mapping_input")
        raise AssertionError("mapping input opened before implementation preflight")

    monkeypatch.setattr(
        sealed_mapping,
        "_verify_phase_records",
        forbidden_mapping_input_open,
    )

    with pytest.raises(E0037SealedMappingError, match="identity is invalid"):
        sealed_mapping.capture_e0037_mapping_only(
            tmp_path,
            _authentication_replay=True,
        )
    assert events == []


def test_postjoin_does_not_open_numeric_or_period_inputs_before_mapping_seal(
    tmp_path,
    monkeypatch,
):
    output = tmp_path / "postjoin.json"
    control = {
        "phase_outputs": {},
        "postjoin_phase": {"mapper_may_be_invoked": False},
    }
    control_stable = _stable_fixture(tmp_path / "control.yaml", "config/control.yaml")
    events: list[str] = []

    monkeypatch.setattr(sealed_mapping, "_clean_git_commit", lambda _root: "a" * 40)
    monkeypatch.setattr(
        sealed_mapping,
        "_load_control",
        lambda _root, _path: (control, control_stable),
    )
    monkeypatch.setattr(sealed_mapping, "_phase_output_path", lambda *_args: output)

    def reject_seal(*_args, **_kwargs):
        events.append("mapping_seal")
        raise E0037SealedMappingError("invalid mapping seal")

    def forbidden_postjoin_open(*_args, **_kwargs):
        events.append("postjoin_inputs")
        raise AssertionError("postjoin input opened before mapping seal")

    monkeypatch.setattr(
        sealed_mapping,
        "_load_valid_mapping_seal_before_postjoin",
        reject_seal,
    )
    monkeypatch.setattr(sealed_mapping, "_verify_phase_records", forbidden_postjoin_open)

    with pytest.raises(E0037SealedMappingError, match="invalid mapping seal"):
        sealed_mapping.capture_e0037_postjoin(tmp_path)
    assert events == ["mapping_seal"]


def test_postjoin_rejects_mapping_seal_from_a_different_git_commit_before_mapping_open(
    project_root,
    monkeypatch,
):
    control, control_stable = _load_control(project_root, CONTROL_RELATIVE_PATH)
    source_contract = control["phase_outputs"]["source_structure"]
    source_identity = {
        "path": source_contract["path"],
        "size_bytes": source_contract["canonical_payload"]["size_bytes"],
        "sha256": source_contract["canonical_payload"]["sha256"],
    }
    mapping_record = {
        "path": MAPPING_ONLY_RELATIVE_PATH.as_posix(),
        "size_bytes": 2,
        "sha256": hashlib.sha256(b"{}").hexdigest(),
    }
    mapping_phase = control["mapping_only_phase"]
    replay_inputs = {
        "control": control_stable.artifact,
        "source_structure": source_identity,
        **mapping_phase["permitted_frozen_inputs"],
    }
    seal = {
        "format_version": 1,
        "experiment_id": "E-0037",
        "dataset_role": "CALIBRATION",
        "state": MAPPING_SEAL_STATE,
        "seal_git_commit": "a" * 40,
        "seal_git_dirty": False,
        "mapping_only": mapping_record,
        "mapping_capture_git_commit": "b" * 40,
        "schema_projection_sha256": (
            "7025ca729c01a3f2030af38e9745a0ee8d72b1dad60c8d4e3b7cf749e5eb860c"
        ),
        "row_count": 64,
        "schema_disposition_count": 77,
        "row_mapping_status_counts": {},
        "postjoin_access": sealed_mapping._MAPPING_SEAL_POSTJOIN_ACCESS,
        "input_hash_ledger": {
            "control": control_stable.artifact,
            "mapping_only": mapping_record,
            "authentication_replay_inputs": replay_inputs,
            "authentication_replay_implementation": mapping_phase["implementation"],
        },
        "authority": sealed_mapping._MAPPING_SEAL_AUTHORITY,
        "claim_boundary": control["phase_claim_boundaries"]["mapping_seal"],
    }
    seal_bytes = json.dumps(seal, sort_keys=True).encode("utf-8")
    seal_stable = _StableFile(
        path=project_root / MAPPING_SEAL_RELATIVE_PATH,
        payload=seal_bytes,
        identity=(1, 2, 0o100644, len(seal_bytes), 3, 4),
        artifact={
            "path": MAPPING_SEAL_RELATIVE_PATH.as_posix(),
            "size_bytes": len(seal_bytes),
            "sha256": hashlib.sha256(seal_bytes).hexdigest(),
        },
    )
    mapping_opened = False

    monkeypatch.setattr(
        sealed_mapping,
        "_read_stable_file",
        lambda *_args, **_kwargs: seal_stable,
    )

    def forbidden_mapping_open(*_args, **_kwargs):
        nonlocal mapping_opened
        mapping_opened = True
        raise AssertionError("mapping bytes opened before seal Git linkage validation")

    monkeypatch.setattr(sealed_mapping, "_verify_artifact_record", forbidden_mapping_open)

    with pytest.raises(E0037SealedMappingError, match="mapping-only seal is incomplete"):
        sealed_mapping._load_valid_mapping_seal_before_postjoin(
            project_root,
            MAPPING_SEAL_RELATIVE_PATH,
            control,
            control_stable,
        )
    assert mapping_opened is False
