from __future__ import annotations

import ast
import json
from dataclasses import asdict
from fractions import Fraction
from hashlib import sha256
from pathlib import Path

import fitz
import pytest
import yaml

from bctc_ai.core.coordinates import round_fraction_half_away_from_zero
from bctc_ai.ocr.causal_native_text import (
    CausalNativeTextError,
    bbox_to_millipoints,
    extract_visible_native_text_page,
    load_causal_native_text_policy,
    read_causal_native_text_page,
    round_points_to_millipoints,
)
from bctc_ai.tables.native_tm_regions import (
    extract_visible_native_text_page as extract_visible_native_tm_text_page,
)
from bctc_ai.tables.native_tm_regions import (
    load_native_tm_region_policy,
)

_CAUSAL_POLICY = Path("config/ocr/causal-native-text-v1.yaml")
_TM_POLICY = Path("config/tables/native-tm-regions-v1.yaml")
_QUALITY_POLICY = Path("config/ocr/native-text-quality-v2.yaml")


def _snap(result: object) -> dict[str, object]:
    visible = result
    return {
        "page": visible.page.to_dict(),
        "excluded_spans": [asdict(span) for span in visible.excluded_spans],
    }


def _assert_generic_tm_parity(page: fitz.Page, project_root: Path) -> dict[str, object]:
    generic = extract_visible_native_text_page(
        page,
        load_causal_native_text_policy(project_root / _CAUSAL_POLICY),
    )
    frozen_tm = extract_visible_native_tm_text_page(
        page,
        load_native_tm_region_policy(project_root / _TM_POLICY),
    )
    generic_snapshot = _snap(generic)
    assert generic_snapshot == _snap(frozen_tm)
    return generic_snapshot


def test_generic_engine_has_no_table_or_accounting_layer_imports(project_root: Path):
    forbidden_prefixes = (
        "bctc_ai.axes",
        "bctc_ai.tables",
        "bctc_ai.rows",
        "bctc_ai.mapping",
        "bctc_ai.schema",
        "bctc_ai.role_a",
    )
    for relative_path in (
        Path("src/bctc_ai/ocr/_causal_visibility_core.py"),
        Path("src/bctc_ai/ocr/causal_native_text.py"),
    ):
        tree = ast.parse((project_root / relative_path).read_text(encoding="utf-8"))
        imports = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        ]
        assert not any(
            imported.startswith(prefix) for imported in imports for prefix in forbidden_prefixes
        )


@pytest.mark.parametrize(
    ("points", "expected"),
    (
        (1.2344, 1234),
        (1.2345, 1235),
        (-1.2344, -1234),
        (-1.2345, -1235),
        (0, 0),
    ),
)
def test_millipoint_rounding_is_half_away_from_zero(points: float, expected: int):
    assert round_points_to_millipoints(points) == expected


def test_millipoint_rounding_rejects_nonfinite_coordinates():
    with pytest.raises(CausalNativeTextError, match="must be finite"):
        round_points_to_millipoints(float("nan"))


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (Fraction(3, 2), 2),
        (Fraction(-3, 2), -2),
        (Fraction(7, 4), 2),
        (Fraction(-7, 4), -2),
    ),
)
def test_shared_exact_rounding_resolves_ties_away_from_zero(
    value: Fraction,
    expected: int,
):
    assert round_fraction_half_away_from_zero(value) == expected


@pytest.mark.parametrize(
    ("section", "extra_key"),
    (
        (None, "bank_selector"),
        ("visibility", "page_number_selector"),
        ("safety", "filename_selector"),
    ),
)
def test_policy_rejects_extra_top_or_nested_selector_fields(
    project_root: Path,
    tmp_path: Path,
    section: str | None,
    extra_key: str,
):
    payload = yaml.safe_load((project_root / _CAUSAL_POLICY).read_text(encoding="utf-8"))
    target = payload if section is None else payload[section]
    target[extra_key] = "FORBIDDEN"
    mutated = tmp_path / f"{section or 'root'}-{extra_key}.yaml"
    mutated.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(CausalNativeTextError, match="drifted|boundary"):
        load_causal_native_text_policy(mutated)


def test_bbox_millipoints_use_the_shared_rounding_rule():
    assert bbox_to_millipoints(fitz.Rect(-1.2345, -0.0005, 1.2345, 0.0005)) == [
        -1235,
        -1,
        1235,
        1,
    ]


def test_generic_engine_matches_frozen_tm_for_visible_nonopaque_text(project_root: Path):
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text(
        (100, 100),
        "VISIBLE",
        color=(0, 0, 0),
        fill_opacity=0.5,
    )

    snapshot = _assert_generic_tm_parity(page, project_root)
    document.close()

    assert [word["raw_text"] for word in snapshot["page"]["words"]] == ["VISIBLE"]
    assert snapshot["excluded_spans"] == []


def test_generic_engine_matches_frozen_tm_for_ghost_and_sanitizes_payload(
    project_root: Path,
):
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((20, 35), "VISIBLE BLACK", color=(0, 0, 0))
    page.insert_text((20, 70), "WHITE GHOST", color=(1, 1, 1))
    page.draw_rect(
        fitz.Rect(15, 90, 180, 130),
        color=(0, 0, 0),
        fill=(0, 0, 0),
    )
    page.insert_text((20, 115), "WHITE ON DARK", color=(1, 1, 1))

    snapshot = _assert_generic_tm_parity(page, project_root)
    payload = read_causal_native_text_page(
        page,
        policy=load_causal_native_text_policy(project_root / _CAUSAL_POLICY),
        quality_policy_path=project_root / _QUALITY_POLICY,
    )
    document.close()

    assert {span["raw_text"] for span in snapshot["excluded_spans"]} == {"WHITE GHOST"}
    assert payload["status"] == "CAUSAL_NATIVE_TEXT_READ_COMPLETE"
    assert len(payload["quarantined_spans"]) == 1
    quarantined = payload["quarantined_spans"][0]
    assert "raw_text" not in quarantined
    assert "normalized_text" not in quarantined
    assert quarantined["text_sha256"] == sha256(b"WHITE GHOST").hexdigest()
    assert quarantined["nonwhitespace_character_count"] == len("WHITEGHOST")
    assert len(quarantined["bbox_mpt"]) == 4
    assert "WHITE GHOST" not in json.dumps(
        payload["quarantined_spans"],
        ensure_ascii=False,
        sort_keys=True,
    )


@pytest.mark.parametrize("rotation", (90, 180, 270))
def test_generic_engine_matches_frozen_tm_on_rotated_pages(
    project_root: Path,
    rotation: int,
):
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "VISIBLE", color=(0, 0, 0))
    page.set_rotation(rotation)

    snapshot = _assert_generic_tm_parity(page, project_root)
    document.close()

    assert [word["raw_text"] for word in snapshot["page"]["words"]] == ["VISIBLE"]
    assert snapshot["excluded_spans"] == []


def test_generic_engine_matches_frozen_tm_for_fully_occluded_text(project_root: Path):
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "HIDDEN", color=(0, 0, 0))
    painted_bbox = fitz.Rect(page.get_bboxlog()[0][1])
    page.draw_rect(
        painted_bbox,
        color=(1, 1, 1),
        fill=(1, 1, 1),
    )

    snapshot = _assert_generic_tm_parity(page, project_root)
    document.close()

    assert snapshot["page"]["words"] == []
    assert len(snapshot["excluded_spans"]) == 1
    assert (
        snapshot["excluded_spans"][0]["reason"]
        == "later opaque render object fully covers painted native text"
    )
    assert snapshot["excluded_spans"][0]["occluding_object_type"] == "fill-path"


def test_partial_occlusion_wrapper_fails_closed_without_ocr_fallback(project_root: Path):
    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((100, 100), "PARTIAL", color=(0, 0, 0))
    painted_bbox = fitz.Rect(page.get_bboxlog()[0][1])
    page.draw_rect(
        fitz.Rect(
            painted_bbox.x0,
            painted_bbox.y0,
            painted_bbox.x1 - painted_bbox.width * 0.05,
            painted_bbox.y1,
        ),
        color=(1, 1, 1),
        fill=(1, 1, 1),
    )

    payload = read_causal_native_text_page(
        page,
        policy=load_causal_native_text_policy(project_root / _CAUSAL_POLICY),
        quality_policy_path=project_root / _QUALITY_POLICY,
    )
    document.close()

    assert payload == {
        "status": "UNRESOLVED_CAUSAL_NATIVE_VISIBILITY",
        "failure_type": "CausalNativeTextError",
        "lines": [],
        "words": [],
        "quarantined_spans": [],
        "ocr_fallback_used": False,
        "source_blank_claimed": False,
    }
