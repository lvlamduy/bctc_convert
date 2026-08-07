from __future__ import annotations

import copy
import hashlib
import json

import pytest

from bctc_ai.evaluation import e0037_sealed_mapping as sealed_mapping
from bctc_ai.evaluation.e0037_sealed_mapping import (
    E0037SealedMappingError,
    _assemble_postjoin_cells,
    _build_mapper_rows,
    _encoded_json,
    _exclusive_publish_json,
    _numeric_cell_status,
    _read_stable_file,
    _StableFile,
    _validate_mapping_rows,
)


def _sample_ids() -> list[str]:
    return [
        f"page-{page:04d}-row-{row:03d}-label"
        for page, count in ((3, 39), (4, 25))
        for row in range(count)
    ]


def _source_payload() -> dict[str, object]:
    rows = []
    for order, row_id in enumerate(_sample_ids()):
        page, row = sealed_mapping._sample_coordinates(row_id)
        rows.append(
            {
                "row_id": row_id,
                "source_order": order,
                "page": page,
                "row_ordinal": row,
                "raw_label": f"label {order}",
                "row_role": "DETAIL",
                "typography_role": "REGULAR_UPRIGHT",
                "physical_parent_row_id": None,
                "section_row_id": None,
                "child_set_complete": "UNKNOWN",
            }
        )
    rows[0]["row_role"] = "SECTION"
    rows[1]["physical_parent_row_id"] = rows[0]["row_id"]
    rows[2]["section_row_id"] = rows[0]["row_id"]
    return {
        "rows": rows,
        "edges": [
            {
                "parent_row_id": rows[0]["row_id"],
                "child_row_id": rows[1]["row_id"],
                "relation_type": "PHYSICAL_PARENT",
                "evidence": ["fixture"],
            },
            {
                "parent_row_id": rows[0]["row_id"],
                "child_row_id": rows[2]["row_id"],
                "relation_type": "SECTION_MEMBER",
                "evidence": ["fixture"],
            },
        ],
    }


def _mapping_rows_and_schema() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    row_ids = _sample_ids()
    schema_ids = list(range(1000, 1077))
    rows: list[dict[str, object]] = []
    for index, row_id in enumerate(row_ids):
        mapping: dict[str, object] = {
            "row_id": row_id,
            "status": "NO_ADMISSIBLE_PAIR",
            "selected_report_norm_id": None,
            "candidate_report_norm_ids": [],
            "interval_index": 0,
            "reason": "fixture unmatched",
        }
        if index == 0:
            mapping.update(
                {
                    "status": "AMBIGUOUS_ACROSS_PATHS",
                    "candidate_report_norm_ids": [schema_ids[0]],
                    "reason": "fixture ambiguity",
                }
            )
        elif index == 1:
            mapping.update(
                {
                    "status": "RESOLVED_PATH",
                    "selected_report_norm_id": schema_ids[1],
                    "candidate_report_norm_ids": [schema_ids[1]],
                    "reason": "fixture accepted",
                }
            )
        rows.append({"row_id": row_id, "mapping": mapping})

    dispositions: list[dict[str, object]] = []
    for index, schema_id in enumerate(schema_ids):
        disposition: dict[str, object] = {
            "report_norm_id": schema_id,
            "status": "UNMATCHED_SCHEMA_NODE",
            "selected_row_id": None,
            "candidate_row_ids": [],
            "reason": "fixture unmatched",
        }
        if index == 0:
            disposition.update(
                {
                    "status": "AMBIGUOUS_ACROSS_PATHS",
                    "candidate_row_ids": [row_ids[0]],
                    "reason": "fixture ambiguity",
                }
            )
        elif index == 1:
            disposition.update(
                {
                    "status": "MAPPED",
                    "selected_row_id": row_ids[1],
                    "candidate_row_ids": [row_ids[1]],
                    "reason": "fixture accepted",
                }
            )
        dispositions.append(disposition)
    return rows, dispositions


def test_source_edges_are_converted_without_treating_section_as_direct_parent(project_root):
    labels = {
        row_id: {"vietocr": f"label {index}", "deepseek_ocr2": f"label {index}"}
        for index, row_id in enumerate(_sample_ids())
    }
    mapper_rows, evidence_rows, _counts = _build_mapper_rows(
        _source_payload(),
        _sample_ids(),
        labels,
        sealed_mapping.load_scope_policy(project_root / "config/mapping/scope_exclusions.yaml"),
    )

    assert mapper_rows[1].relation_type == "DIRECT_PARENT"
    assert mapper_rows[1].parent_row_id == _sample_ids()[0]
    assert mapper_rows[2].relation_type == "UNKNOWN"
    assert mapper_rows[2].parent_row_id is None
    assert evidence_rows[2]["source_structure"]["physical_parent_row_id"] is None
    assert evidence_rows[2]["source_structure"]["physical_section_id"] == _sample_ids()[0]
    assert all(row.report_scope == "UNKNOWN" for row in mapper_rows)

    mapping_rows, dispositions = _mapping_rows_and_schema()
    assembled_rows = [
        {**evidence, "mapping": mapping_row["mapping"]}
        for evidence, mapping_row in zip(evidence_rows, mapping_rows, strict=True)
    ]
    _validate_mapping_rows(
        assembled_rows,
        dispositions,
        expected_graph_ids=list(range(1000, 1077)),
        require_evidence=True,
    )
    qwen_contaminated = copy.deepcopy(assembled_rows)
    qwen_contaminated[0]["semantic_proposals"]["qwen"] = "forbidden"
    with pytest.raises(E0037SealedMappingError, match="proposal firewall"):
        _validate_mapping_rows(
            qwen_contaminated,
            dispositions,
            expected_graph_ids=list(range(1000, 1077)),
            require_evidence=True,
        )
    scope_contaminated = copy.deepcopy(assembled_rows)
    scope_contaminated[0]["source_structure"]["report_scope"] = "CONSOLIDATED"
    with pytest.raises(E0037SealedMappingError, match="structure value"):
        _validate_mapping_rows(
            scope_contaminated,
            dispositions,
            expected_graph_ids=list(range(1000, 1077)),
            require_evidence=True,
        )


def test_mapping_validation_keeps_ambiguity_unselected_and_cross_links_schema():
    rows, dispositions = _mapping_rows_and_schema()
    validated_rows, validated_schema = _validate_mapping_rows(
        rows,
        dispositions,
        expected_graph_ids=list(range(1000, 1077)),
    )

    assert validated_rows[0]["mapping"]["selected_report_norm_id"] is None
    assert validated_rows[0]["mapping"]["candidate_report_norm_ids"] == [1000]
    assert validated_rows[1]["mapping"]["selected_report_norm_id"] == 1001
    assert validated_schema[0]["candidate_row_ids"] == [_sample_ids()[0]]

    contaminated = copy.deepcopy(rows)
    contaminated[0]["mapping"]["selected_report_norm_id"] = 1000
    with pytest.raises(E0037SealedMappingError, match="non-accepted row leaked"):
        _validate_mapping_rows(
            contaminated,
            dispositions,
            expected_graph_ids=list(range(1000, 1077)),
        )


def test_numeric_status_keeps_dash_blank_and_value_distinct():
    value = {
        "verification_status": "VERIFIED_OBSERVED_VALUE",
        "primary": {"observation": "VALUE"},
        "normalized_numeric_value": "123",
        "selected_raw_value": "123",
    }
    dash = {
        "verification_status": "VERIFIED_OBSERVED_DASH",
        "primary": {"observation": "DASH"},
    }
    blank = {
        "verification_status": "UNRESOLVED_BLANK_PENDING_ROW_SEMANTICS",
        "primary": {"observation": "BLANK"},
    }

    assert _numeric_cell_status(value) == ("OBSERVED_VALUE", "123", "123")
    assert _numeric_cell_status(dash) == ("DASH", None, None)
    assert _numeric_cell_status(blank) == ("UNRESOLVED", None, None)


def test_postjoin_scales_only_selected_displayed_values_and_never_dash(tmp_path):
    rows, _dispositions = _mapping_rows_and_schema()
    cells: list[dict[str, object]] = []
    for page, count in ((3, 39), (4, 25)):
        for row in range(count):
            for axis in range(2):
                status = "VERIFIED_OBSERVED_VALUE"
                primary = {"observation": "VALUE", "raw_text": "2"}
                normalized: str | None = "2"
                raw: str | None = "2"
                if page == 3 and row == 1 and axis == 1:
                    status = "VERIFIED_OBSERVED_DASH"
                    primary = {"observation": "DASH", "raw_text": "-"}
                    normalized = "0"
                    raw = "-"
                cells.append(
                    {
                        "cell_id": f"page-{page:04d}-row-{row:03d}-axis-{axis + 1}",
                        "page": page,
                        "row_ordinal": row,
                        "axis_ordinal": axis,
                        "verification_status": status,
                        "primary": primary,
                        "normalized_numeric_value": normalized,
                        "selected_raw_value": raw,
                    }
                )
    axes = {
        (page, axis): {
            "raw_unit_text": "triu đồng",
            "canonical_unit": "VND",
            "unit_multiplier": 1_000_000,
        }
        for page in (3, 4)
        for axis in (0, 1)
    }

    assembled = _assemble_postjoin_cells(tmp_path, rows, cells, axes)

    assert assembled[0]["selected_report_norm_id"] is None
    assert assembled[0]["canonical_unit_value"] is None
    accepted_value = next(
        cell
        for cell in assembled
        if cell["row_id"] == _sample_ids()[1] and cell["axis_ordinal"] == 0
    )
    accepted_dash = next(
        cell
        for cell in assembled
        if cell["row_id"] == _sample_ids()[1] and cell["axis_ordinal"] == 1
    )
    assert accepted_value["displayed_unit_value"] == "2"
    assert accepted_value["canonical_unit_value"] == "2000000"
    assert accepted_dash["cell_status"] == "DASH"
    assert accepted_dash["visible_raw_value"] == "-"
    assert accepted_dash["canonical_unit_value"] is None


def test_exclusive_publisher_uses_canonical_bytes_and_refuses_overwrite(tmp_path):
    target = tmp_path / "nested/artifact.json"
    payload = {"b": 2, "a": "Việt"}

    digest = _exclusive_publish_json(tmp_path, target, payload, canonical_compact=True)
    expected = _encoded_json(payload, canonical_compact=True)

    assert target.read_bytes() == expected
    assert digest == hashlib.sha256(expected).hexdigest()
    with pytest.raises(E0037SealedMappingError, match="overwrite"):
        _exclusive_publish_json(tmp_path, target, payload, canonical_compact=True)


def test_stable_reader_rejects_intermediate_symlink(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "payload.json").write_text("{}", encoding="utf-8")
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(E0037SealedMappingError, match="nofollow"):
        _read_stable_file(tmp_path, tmp_path / "linked/payload.json", "fixture")


def test_stable_reader_bounds_the_initial_size_and_rejects_concurrent_growth(
    tmp_path,
    monkeypatch,
):
    target = tmp_path / "payload.json"
    target.write_bytes(b"{}")
    original_read = sealed_mapping.os.read
    appended = False

    def racing_read(descriptor, size):
        nonlocal appended
        block = original_read(descriptor, size)
        if not appended:
            appended = True
            with target.open("ab") as stream:
                stream.write(b"x")
                stream.flush()
        return block

    monkeypatch.setattr(sealed_mapping.os, "read", racing_read)

    with pytest.raises(E0037SealedMappingError, match="changed while being read"):
        _read_stable_file(tmp_path, target, "growing fixture", maximum_size=2)


@pytest.mark.parametrize("constant", [b"NaN", b"Infinity", b"-Infinity"])
def test_json_loader_rejects_nonfinite_constants(constant):
    with pytest.raises(E0037SealedMappingError, match="cannot decode fixture as JSON"):
        sealed_mapping._load_json_bytes(b'{"value":' + constant + b"}", "fixture")


def test_mapping_seal_rejects_bytes_that_do_not_match_authentication_replay(
    tmp_path,
    monkeypatch,
):
    mapping_payload = {"state": "fixture"}
    tampered_bytes = json.dumps(mapping_payload).encode("utf-8")
    mapping_file = tmp_path / "mapping.json"
    mapping_file.write_bytes(tampered_bytes)
    stable = _StableFile(
        path=mapping_file,
        payload=tampered_bytes,
        identity=(1, 2, 3, len(tampered_bytes), 4, 5),
        artifact={
            "path": "output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/mapping_only.json",
            "size_bytes": len(tampered_bytes),
            "sha256": hashlib.sha256(tampered_bytes).hexdigest(),
        },
    )
    control = {
        "mapping_seal_phase": {
            "permitted_dynamic_input": "mapping_only_output_plus_exact_deterministic_replay",
            "mapper_authentication_replay_required": True,
            "exact_replay_byte_equality_required": True,
            "postjoin_inputs_may_be_opened": False,
        }
    }
    control_stable = copy.deepcopy(stable)
    events: list[str] = []
    monkeypatch.setattr(sealed_mapping, "_clean_git_commit", lambda _root: "a" * 40)
    monkeypatch.setattr(
        sealed_mapping,
        "_load_control",
        lambda _root, _path: (control, control_stable),
    )
    monkeypatch.setattr(
        sealed_mapping,
        "_phase_output_path",
        lambda *_args: tmp_path / "seal.json",
    )
    monkeypatch.setattr(
        sealed_mapping,
        "_canonical_argument",
        lambda *_args: mapping_file,
    )
    monkeypatch.setattr(sealed_mapping, "_read_stable_file", lambda *_args, **_kwargs: stable)
    monkeypatch.setattr(sealed_mapping, "_load_json_bytes", lambda *_args: mapping_payload)
    monkeypatch.setattr(
        sealed_mapping,
        "_validate_mapping_only_payload",
        lambda _payload: ([], []),
    )

    def replay(*_args, **_kwargs):
        events.append("replay")
        return {"state": "independently replayed"}

    monkeypatch.setattr(sealed_mapping, "capture_e0037_mapping_only", replay)
    monkeypatch.setattr(
        sealed_mapping,
        "_exclusive_publish_json",
        lambda *_args, **_kwargs: events.append("published"),
    )

    with pytest.raises(E0037SealedMappingError, match="authentication replay"):
        sealed_mapping.capture_e0037_mapping_seal(tmp_path)
    assert events == ["replay"]
