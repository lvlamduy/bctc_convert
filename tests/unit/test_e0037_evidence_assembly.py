from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath

import pytest

import bctc_ai.evaluation.e0037_evidence_assembly as source_structure
from bctc_ai.evaluation.e0037_evidence_assembly import (
    E0035_SEAL_RELATIVE_PATH,
    SOURCE_STRUCTURE_CANONICAL_SHA256,
    SOURCE_STRUCTURE_CANONICAL_SIZE_BYTES,
    SOURCE_STRUCTURE_CANONICALIZATION,
    SOURCE_STRUCTURE_CLAIM_BOUNDARY,
    SOURCE_STRUCTURE_RELATIVE_PATH,
    SOURCE_STRUCTURE_STATE,
    E0037SourceStructureError,
    assemble_source_only_structure,
    canonical_payload_identity,
    load_source_only_structure,
    validate_source_only_structure,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def assembled() -> dict[str, object]:
    return assemble_source_only_structure(PROJECT_ROOT)


def _rows_by_id(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    return {row["row_id"]: row for row in payload["rows"]}  # type: ignore[index, misc]


def test_e0037_source_structure_is_exact_deterministic_source_only_contract(assembled):
    canonical = json.dumps(
        assembled,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    assert assembled["state"] == SOURCE_STRUCTURE_STATE
    assert assembled["metrics"] == {
        "row_count": 64,
        "rows_by_page": {"3": 39, "4": 25},
        "row_role_counts": {
            "DETAIL": 43,
            "GROUP": 13,
            "SECTION": 3,
            "TOTAL": 4,
            "UNKNOWN": 1,
        },
        "typography_role_counts": {
            "BOLD_ITALIC": 4,
            "BOLD_UPRIGHT": 28,
            "REGULAR_ITALIC": 2,
            "REGULAR_UPRIGHT": 30,
        },
        "physical_parent_edge_count": 33,
        "section_member_edge_count": 60,
        "unknown_child_set_count": 64,
    }
    assert len(canonical) == SOURCE_STRUCTURE_CANONICAL_SIZE_BYTES == 136042
    assert hashlib.sha256(canonical).hexdigest() == SOURCE_STRUCTURE_CANONICAL_SHA256
    assert SOURCE_STRUCTURE_CANONICAL_SHA256 == (
        "ef098a659f8b557ac3a801edccfc7c0848be9a512b47ba7c9278cd3873f70728"
    )
    assert canonical_payload_identity(assembled) == {
        "canonicalization": SOURCE_STRUCTURE_CANONICALIZATION,
        "sha256": SOURCE_STRUCTURE_CANONICAL_SHA256,
        "size_bytes": SOURCE_STRUCTURE_CANONICAL_SIZE_BYTES,
    }
    assert assembled["claim_boundary"] == SOURCE_STRUCTURE_CLAIM_BOUNDARY
    validate_source_only_structure(assembled)


def test_e0037_preserves_source_label_crop_render_and_geometry(assembled):
    rows = assembled["rows"]
    first = rows[0]

    assert [row["source_order"] for row in rows] == list(range(64))
    assert first["row_id"] == "page-0003-row-000-label"
    assert first["raw_label"] == "TÀI SÁN"
    assert first["crop"] == {
        "path": (
            "output/calibration/e0035-mbb-cdkt-logical-row-label-crops/"
            "a177792e8b98f340f562/crops/page-0003-row-000-label.png"
        ),
        "sha256": "e10377b3fd5fc6bb78b2511d3dc7891c9ed6f610fb06e64e2f231c6f5ccbec78",
        "size_bytes": 8413,
        "width": 197,
        "height": 77,
    }
    assert first["geometry"]["label_union_bbox"] == [59, 818, 216, 871]
    assert first["geometry"]["source_crop_bbox"] == [51, 814, 224, 875]
    assert first["geometry"]["x_indentation_used"] is False
    assert first["geometry"]["note_reference_used_as_schema_numbering"] is False
    assert all(row["child_set_complete"] == "UNKNOWN" for row in rows)


def test_e0037_authority_distinguishes_pixel_and_frozen_label_derivations(assembled):
    contract = assembled["source_only_contract"]
    authority = assembled["authority"]

    assert contract["typography_authority"] == {
        "font_weight_and_slant": "REGISTERED_SOURCE_PIXELS",
        "case_role": "E0035_FROZEN_PPOCR_TEXT_PROVENANCE_ONLY",
    }
    assert contract["lexical_row_role_authority"] == ("E0035_FROZEN_PPOCR_TEXT_PROVENANCE_ONLY")
    assert contract["derivation_binding"] == (
        "EXACT_CANONICAL_PAYLOAD_IDENTITY_REQUIRED_BEFORE_SCHEMA_ACCESS"
    )
    assert authority["source_pixels_are_font_weight_and_slant_authority"] is True
    assert authority["e0035_frozen_raw_label_is_case_and_lexical_role_authority"] is True


def test_e0037_pixel_typography_and_fixed_asset_hierarchy_are_source_only(assembled):
    rows = _rows_by_id(assembled)

    assert rows["page-0003-row-022-label"]["typography_role"] == "BOLD_UPRIGHT"
    assert rows["page-0003-row-022-label"]["row_role"] == "GROUP"
    assert rows["page-0003-row-023-label"]["typography_role"] == "REGULAR_ITALIC"
    assert rows["page-0003-row-023-label"]["physical_parent_row_id"] == ("page-0003-row-022-label")
    assert rows["page-0003-row-024-label"]["physical_parent_row_id"] == ("page-0003-row-023-label")
    assert rows["page-0003-row-025-label"]["physical_parent_row_id"] == ("page-0003-row-023-label")
    assert rows["page-0003-row-026-label"]["typography_role"] == "REGULAR_ITALIC"
    assert rows["page-0003-row-026-label"]["physical_parent_row_id"] == ("page-0003-row-022-label")
    assert rows["page-0003-row-027-label"]["physical_parent_row_id"] == ("page-0003-row-026-label")
    assert rows["page-0003-row-028-label"]["physical_parent_row_id"] == ("page-0003-row-026-label")


def test_e0037_pixel_typography_and_equity_hierarchy_abstain_where_needed(assembled):
    rows = _rows_by_id(assembled)

    assert rows["page-0004-row-013-label"]["row_role"] == "SECTION"
    assert rows["page-0004-row-014-label"]["row_role"] == "GROUP"
    assert rows["page-0004-row-015-label"]["typography_role"] == "BOLD_ITALIC"
    assert rows["page-0004-row-015-label"]["physical_parent_row_id"] == ("page-0004-row-014-label")
    for ordinal in (16, 17, 18):
        assert rows[f"page-0004-row-{ordinal:03d}-label"]["physical_parent_row_id"] == (
            "page-0004-row-015-label"
        )
    for ordinal in (19, 20, 21):
        assert rows[f"page-0004-row-{ordinal:03d}-label"]["physical_parent_row_id"] is None
    assert rows["page-0004-row-022-label"]["row_role"] == "UNKNOWN"
    assert rows["page-0004-row-022-label"]["row_role_candidates"] == ["SECTION", "DETAIL"]
    assert rows["page-0004-row-024-label"]["section_row_id"] is None


def test_e0037_input_firewall_opens_only_sealed_source_inputs(monkeypatch):
    observed: list[str] = []
    original = source_structure._stable_read

    def recording_read(root, relative, **kwargs):
        observed.append(relative.as_posix())
        return original(root, relative, **kwargs)

    def path_io_is_forbidden(*args, **kwargs):
        raise AssertionError("assembly must perform every read through stable os.open")

    monkeypatch.setattr(source_structure, "_stable_read", recording_read)
    monkeypatch.setattr(Path, "open", path_io_is_forbidden)
    monkeypatch.setattr(Path, "read_text", path_io_is_forbidden)

    payload = assemble_source_only_structure(PROJECT_ROOT)

    assert payload["metrics"]["row_count"] == 64
    assert len(observed) == 66
    assert observed[0] == E0035_SEAL_RELATIVE_PATH.as_posix()
    assert observed[1] == (
        "output/calibration/e0035-mbb-cdkt-logical-row-label-crops/"
        "a177792e8b98f340f562/crop_manifest.json"
    )
    assert sum(path.endswith(".png") and "/crops/" in path for path in observed) == 64
    assert not any(
        path.endswith("page-0003.png") or path.endswith("page-0004.png") for path in observed
    )
    forbidden_fragments = (
        "schema",
        "workbook",
        "template",
        "e0030",
        "e0033",
        "e0034",
        "e0036",
        "review",
        "history",
        "numeric",
        "mongodb",
    )
    assert not any(
        fragment in path.casefold() for path in observed for fragment in forbidden_fragments
    )


@pytest.mark.parametrize(
    "unsafe",
    [
        Path("../docs/experiments/E-0035-mbb-cdkt-logical-row-label-crops.json"),
        Path("docs/experiments/other.json"),
        Path("/tmp/E-0035.json"),
    ],
)
def test_e0037_rejects_noncanonical_or_nonallowlisted_entry_path(unsafe):
    with pytest.raises(E0037SourceStructureError, match="unsafe|outside"):
        assemble_source_only_structure(PROJECT_ROOT, e0035_seal_path=unsafe)


def test_e0037_rejects_seal_hash_drift_before_manifest_access(tmp_path):
    destination = tmp_path / E0035_SEAL_RELATIVE_PATH
    destination.parent.mkdir(parents=True)
    data = (PROJECT_ROOT / E0035_SEAL_RELATIVE_PATH).read_bytes()
    destination.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))

    with pytest.raises(E0037SourceStructureError, match="SHA-256 drifted"):
        assemble_source_only_structure(tmp_path)


def test_e0037_rejects_symlink_component_before_read(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / E0035_SEAL_RELATIVE_PATH.name).write_bytes(
        (PROJECT_ROOT / E0035_SEAL_RELATIVE_PATH).read_bytes()
    )
    (tmp_path / "docs").symlink_to(outside, target_is_directory=True)

    with pytest.raises(E0037SourceStructureError, match="symlink component"):
        assemble_source_only_structure(tmp_path)


def test_e0037_stable_read_detects_path_swap_toctou(tmp_path, monkeypatch):
    relative = PurePosixPath("payload.bin")
    path = tmp_path / relative.as_posix()
    original_bytes = b"a" * (1024 * 1024 + 17)
    path.write_bytes(original_bytes)
    real_read = source_structure.os.read
    call_count = 0

    def racing_read(descriptor, count):
        nonlocal call_count
        result = real_read(descriptor, count)
        call_count += 1
        if call_count == 1:
            replacement = tmp_path / "replacement.bin"
            replacement.write_bytes(b"b" * len(original_bytes))
            os.replace(replacement, path)
        return result

    monkeypatch.setattr(source_structure.os, "read", racing_read)

    with pytest.raises(E0037SourceStructureError, match="changed"):
        source_structure._stable_read(
            tmp_path,
            relative,
            expected_sha256=hashlib.sha256(original_bytes).hexdigest(),
            expected_size=len(original_bytes),
            maximum_size=2 * 1024 * 1024,
        )


def test_e0037_validator_rejects_forbidden_answer_fields(assembled):
    contaminated = copy.deepcopy(assembled)
    contaminated["rows"][0]["report_norm_id"] = 999

    with pytest.raises(E0037SourceStructureError, match="forbidden answer fields"):
        validate_source_only_structure(contaminated)


def test_e0037_validator_rejects_shape_only_parent_forgery(assembled):
    contaminated = copy.deepcopy(assembled)
    child_id = "page-0003-row-024-label"
    forged_parent = "page-0003-row-000-label"
    rows = _rows_by_id(contaminated)
    rows[child_id]["physical_parent_row_id"] = forged_parent
    for edge in contaminated["edges"]:
        if edge["child_row_id"] == child_id and edge["relation_type"] == "PHYSICAL_PARENT":
            edge["parent_row_id"] = forged_parent

    with pytest.raises(E0037SourceStructureError, match="structural-parent derivation"):
        validate_source_only_structure(contaminated)


@pytest.mark.parametrize(
    ("path", "replacement", "message"),
    [
        (("gates",), {"invented_gate": True}, "exact gate contract"),
        (("claim_boundary",), 123, "claim boundary"),
        (("rows", 0, "typography", "metrics", "ink_pixel_count"), {}, "must be integers"),
        (("rows", 0, "label_provenance", "ppocr_scores", 0), 2.0, "label provenance"),
        (
            ("authority", "source_pixels_are_font_weight_and_slant_authority"),
            1,
            "identity or authority",
        ),
    ],
)
def test_e0037_validator_rejects_nonexact_nested_contracts(assembled, path, replacement, message):
    contaminated = copy.deepcopy(assembled)
    target = contaminated
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = replacement

    with pytest.raises(E0037SourceStructureError, match=message):
        validate_source_only_structure(contaminated)


def test_e0037_canonical_identity_rejects_unverifiable_label_substitution(assembled):
    contaminated = copy.deepcopy(assembled)
    original_identity = canonical_payload_identity(contaminated)
    contaminated["rows"][1]["raw_label"] = contaminated["rows"][1]["raw_label"].replace("mt", "zz")

    assert canonical_payload_identity(contaminated) != original_identity
    with pytest.raises(E0037SourceStructureError, match="canonical payload identity"):
        validate_source_only_structure(contaminated)


def test_e0037_loader_requires_canonical_path_hash_and_contract(tmp_path, assembled):
    target = tmp_path / SOURCE_STRUCTURE_RELATIVE_PATH
    target.parent.mkdir(parents=True)
    encoded = (json.dumps(assembled, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    target.write_bytes(encoded)

    with pytest.raises(TypeError, match="expected_sha256.*expected_size_bytes"):
        load_source_only_structure(tmp_path)  # type: ignore[call-arg]

    loaded = load_source_only_structure(
        tmp_path,
        expected_sha256=hashlib.sha256(encoded).hexdigest(),
        expected_size_bytes=len(encoded),
    )

    assert loaded == assembled
    with pytest.raises(E0037SourceStructureError, match="outside"):
        load_source_only_structure(
            tmp_path,
            path=Path("source_structure.json"),
            expected_sha256=hashlib.sha256(encoded).hexdigest(),
            expected_size_bytes=len(encoded),
        )
