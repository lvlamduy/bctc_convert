from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.word_box_rows import WordBoxReconstructionError
from bctc_ai.evaluation.word_box_rows_v2 import ParsedGeometryPageV2, geometry_row_v2_to_dict
from bctc_ai.evaluation.word_box_rows_v3 import (
    WordBoxReconstructionV3Config,
    load_word_box_reconstruction_v3_config,
    parse_ppocrv6_word_box_page_v3,
)


@dataclass(frozen=True)
class WordBoxReconstructionV4Config:
    base: WordBoxReconstructionV3Config
    source_path: Path
    maximum_note_to_value_anchor_gap_line_heights: float
    require_same_page_source_geometry: bool
    forbid_label_semantics_as_split_feature: bool
    forbid_numeric_magnitude_as_split_feature: bool
    forbid_schema_history_or_review: bool


def load_word_box_reconstruction_v4_config(path: Path) -> WordBoxReconstructionV4Config:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise WordBoxReconstructionError(f"cannot load word-box v4 config: {path}") from exc
    if not isinstance(payload, dict) or (
        payload.get("version") != 4
        or payload.get("policy") != "NOTE_SEPARATED_STRUCTURAL_ANCHOR_V4"
    ):
        raise WordBoxReconstructionError("word-box reconstruction config must be version 4")
    base_name = payload.get("base_config")
    if not isinstance(base_name, str) or Path(base_name).name != base_name:
        raise WordBoxReconstructionError("word-box v4 base_config path is invalid")
    base_path = (path.parent / base_name).resolve()
    if not base_path.is_file() or base_path.parent != path.parent.resolve():
        raise WordBoxReconstructionError("word-box v4 base_config is absent or escapes")
    if sha256_file(base_path) != payload.get("base_config_sha256"):
        raise WordBoxReconstructionError("word-box v4 base_config hash drifted")
    gap = payload.get("maximum_note_to_value_anchor_gap_line_heights")
    if (
        isinstance(gap, bool)
        or not isinstance(gap, (int, float))
        or not 0.20 <= float(gap) <= 0.75
    ):
        raise WordBoxReconstructionError("word-box v4 note/value gap bound is unsafe")
    switches = (
        "require_same_page_source_geometry",
        "forbid_label_semantics_as_split_feature",
        "forbid_numeric_magnitude_as_split_feature",
        "forbid_schema_history_or_review",
    )
    if any(payload.get(name) is not True for name in switches):
        raise WordBoxReconstructionError("word-box v4 safety switch drifted")
    return WordBoxReconstructionV4Config(
        base=load_word_box_reconstruction_v3_config(base_path),
        source_path=path.resolve(),
        maximum_note_to_value_anchor_gap_line_heights=float(gap),
        **{name: True for name in switches},
    )


def parse_ppocrv6_word_box_page_v4(
    result_path: Path,
    config: WordBoxReconstructionV4Config,
    *,
    page_tag: str,
    source_image_path: Path | None = None,
) -> ParsedGeometryPageV2:
    return parse_ppocrv6_word_box_page_v3(
        result_path,
        config.base,
        page_tag=page_tag,
        source_image_path=source_image_path,
        note_to_value_anchor_attach_line_heights=(
            config.maximum_note_to_value_anchor_gap_line_heights
        ),
    )


geometry_row_v4_to_dict = geometry_row_v2_to_dict


__all__ = [
    "WordBoxReconstructionV4Config",
    "geometry_row_v4_to_dict",
    "load_word_box_reconstruction_v4_config",
    "parse_ppocrv6_word_box_page_v4",
]
