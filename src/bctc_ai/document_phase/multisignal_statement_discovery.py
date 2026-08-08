from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import ratio

from bctc_ai.core.contracts import ObservationKind
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import parse_financial_number, retrieval_key
from bctc_ai.document_phase.statement_locator import (
    OCRLine,
    OCRPage,
    StatementLocatorError,
    StatementPageType,
    StatementScope,
    detect_cash_flow_method,
)
from bctc_ai.document_phase.statement_locator_v2 import (
    _core_is_token_bounded,
    _form_family_evidence,
    load_statement_locator_v2_config,
)

_MAIN_TYPES = (
    StatementPageType.CDKT,
    StatementPageType.KQKD,
    StatementPageType.LCTT,
)
_TARGET_TYPES = (*_MAIN_TYPES, StatementPageType.TM)
_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_SECTION_MARKER = re.compile(r"^(?:\d{1,3}|[ivxlcdm]{1,6}|[a-z])[.)]?$", re.IGNORECASE)


@dataclass(frozen=True)
class TextWindow:
    source: str
    line_indices: tuple[int, ...]
    text: str
    key: str
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class AnchorHit:
    anchor: str
    source: str
    line_indices: tuple[int, ...]
    text: str
    bbox: tuple[float, float, float, float]
    similarity: float


@dataclass(frozen=True)
class NumericGeometry:
    passes: bool
    axes: tuple[float, ...]
    axis_cell_counts: tuple[int, ...]
    financial_cell_count: int
    first_cell_y_fraction: float | None
    last_cell_y_fraction: float | None


@dataclass(frozen=True)
class PeriodEvidence:
    passes_main_axis: bool
    axis_positions: tuple[float, ...]
    axis_year_signatures: tuple[tuple[str, ...], ...]
    report_years: tuple[str, ...]


@dataclass(frozen=True)
class UnitEvidence:
    passes: bool
    axis_positions: tuple[float, ...]
    canonical_signatures: tuple[str, ...]
    raw_texts: tuple[str, ...]


@dataclass(frozen=True)
class PageTypeCandidate:
    page_type: StatementPageType
    scope: StatementScope
    score: float
    independent_signal_groups: tuple[str, ...]
    accounting_hits: tuple[AnchorHit, ...]
    locally_accepted: bool
    inferred_from_page: int | None = None
    inference_direction: str | None = None
    inference_checks: tuple[str, ...] = ()


@dataclass(frozen=True)
class PageSignalRecord:
    page: int
    header_candidate_type: StatementPageType | None
    header_conflict: bool
    form_types: tuple[StatementPageType, ...]
    title_scores: dict[str, float]
    title_sources: dict[str, str | None]
    period: PeriodEvidence
    unit: UnitEvidence
    numeric_geometry: NumericGeometry
    continuation_marker: bool
    narrative_fraction: float
    narrative_penalty: bool
    audit_suppression: bool
    toc_suppression: bool
    notes_structure: bool
    off_balance_heading_score: float
    off_balance_item_hits: tuple[AnchorHit, ...]
    candidates: tuple[PageTypeCandidate, ...]


@dataclass(frozen=True)
class _Path:
    score: float
    states: tuple[str, ...]


def load_multisignal_statement_config(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise StatementLocatorError(f"cannot load statement-discovery v3 config: {path}") from exc
    if not isinstance(payload, dict):
        raise StatementLocatorError("statement-discovery v3 config must be a mapping")
    identities = {
        "version": 3,
        "policy": "MULTI_LINE_MULTI_SIGNAL_ORDERED_DOCUMENT_DISCOVERY_V3",
        "geometry_authority": "PP_OCRV6_WORD_BOXES",
        "semantic_reader_authority": "HEADING_AND_LABEL_PROPOSAL_ONLY",
        "ordered_statement_types": ["CDKT", "KQKD", "LCTT"],
    }
    if any(payload.get(key) != value for key, value in identities.items()):
        raise StatementLocatorError("statement-discovery v3 identity/order policy drifted")
    expected_forbidden = {
        "bank_identity",
        "filename_identity",
        "page_number_rules",
        "numeric_values_for_page_type",
        "historical_values",
        "mongodb_values",
        "report_norm_id_numeric_order",
        "role_a_text_for_threshold_tuning",
    }
    if set(payload.get("forbidden_inputs", ())) != expected_forbidden:
        raise StatementLocatorError("statement-discovery v3 forbidden-input policy drifted")
    base_name = payload.get("header_candidate_config")
    if not isinstance(base_name, str) or Path(base_name).name != base_name:
        raise StatementLocatorError("statement-discovery v3 header config path is invalid")
    base_path = (path.parent / base_name).resolve()
    if not base_path.is_file() or base_path.parent != path.parent.resolve():
        raise StatementLocatorError("statement-discovery v3 header config is absent or escapes")
    if sha256_file(base_path) != payload.get("header_candidate_config_sha256"):
        raise StatementLocatorError("statement-discovery v3 header config hash drifted")

    required_mappings = (
        "text_windows",
        "header_identity",
        "period_axis",
        "unit",
        "numeric_geometry",
        "accounting_rows",
        "off_balance_scope",
        "narrative",
        "notes_structure",
        "signal_weights",
        "acceptance",
        "neighbor_inference",
        "document_sequence",
    )
    if any(not isinstance(payload.get(key), dict) for key in required_mappings):
        raise StatementLocatorError("statement-discovery v3 is missing a policy mapping")
    accounting = payload["accounting_rows"].get("anchors")
    if not isinstance(accounting, dict) or set(accounting) != {
        item.value for item in _TARGET_TYPES
    }:
        raise StatementLocatorError("statement-discovery v3 accounting anchors are incomplete")
    if any(not isinstance(values, list) or len(values) < 2 for values in accounting.values()):
        raise StatementLocatorError("statement-discovery v3 accounting anchor list is too small")
    if payload["neighbor_inference"].get("max_distance_pages") != 1:
        raise StatementLocatorError("statement-discovery neighbor inference must be one page")
    if payload["document_sequence"].get("states") != [
        "PRE",
        "CDKT",
        "KQKD",
        "LCTT",
        "TM",
        "POST",
    ]:
        raise StatementLocatorError("statement-discovery state order drifted")
    if payload["document_sequence"].get("allow_interstitial_inside_statement_block") is not False:
        raise StatementLocatorError("statement-discovery cannot permit internal interstitial pages")
    if payload["document_sequence"].get("notes_boundary_page_count") != 1:
        raise StatementLocatorError("statement-discovery TM must be a one-page boundary state")
    for mapping_name, keys in {
        "signal_weights": (
            "header_identity",
            "period_axis",
            "unit",
            "accounting_rows",
            "numeric_geometry",
            "notes_structure",
            "continuation",
            "off_balance_scope",
            "narrative_penalty",
            "audit_or_toc_penalty",
        ),
        "acceptance": (
            "main_min_independent_groups",
            "notes_min_independent_groups",
            "min_local_score",
            "page_type_runner_up_margin",
            "document_path_runner_up_margin",
        ),
    }.items():
        mapping = payload[mapping_name]
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
                raise StatementLocatorError(
                    f"statement-discovery v3 {mapping_name}.{key} is invalid"
                )
    config = copy.deepcopy(payload)
    config["header_candidate"] = load_statement_locator_v2_config(base_path)
    return config


def _center_y(line: OCRLine | TextWindow) -> float:
    return (line.bbox[1] + line.bbox[3]) / 2


def _is_text_line(line: OCRLine) -> bool:
    parsed = parse_financial_number(line.text)
    return parsed.observation not in {
        ObservationKind.VALUE,
        ObservationKind.ZERO,
        ObservationKind.DASH,
    }


def _windows_for_page(
    page: OCRPage,
    *,
    source: str,
    config: dict[str, Any],
    header_only: bool,
    label_only: bool,
) -> tuple[TextWindow, ...]:
    policy = config["text_windows"]
    eligible: list[tuple[int, OCRLine]] = []
    for index, line in enumerate(page.lines):
        if not line.key or not _is_text_line(line):
            continue
        if header_only and _center_y(line) > page.height * float(policy["header_fraction"]):
            continue
        if label_only and line.bbox[0] > page.width * float(policy["label_x_max_fraction"]):
            continue
        eligible.append((index, line))
    eligible.sort(key=lambda item: (_center_y(item[1]), item[1].bbox[0], item[0]))
    windows: list[TextWindow] = []
    for index, line in eligible:
        windows.append(
            TextWindow(
                source=source,
                line_indices=(index,),
                text=line.text,
                key=line.key,
                bbox=line.bbox,
            )
        )
        joined: list[tuple[int, OCRLine]] = [(index, line)]
        current = line
        for _ in range(1, int(policy["max_joined_lines"])):
            current_height = max(1.0, current.bbox[3] - current.bbox[1])
            choices = []
            for next_index, following in eligible:
                if next_index in {item[0] for item in joined}:
                    continue
                vertical_delta = _center_y(following) - _center_y(current)
                if vertical_delta <= current_height * 0.30:
                    continue
                if vertical_delta > current_height * float(
                    policy["max_vertical_gap_height_ratio"]
                ):
                    continue
                left_delta = abs(following.bbox[0] - current.bbox[0]) / page.width
                if left_delta > float(policy["max_left_edge_delta_fraction"]):
                    continue
                choices.append((vertical_delta, left_delta, next_index, following))
            if not choices:
                break
            _, _, next_index, following = min(choices)
            joined.append((next_index, following))
            current = following
            text = " ".join(item[1].text for item in joined)
            x0 = min(item[1].bbox[0] for item in joined)
            y0 = min(item[1].bbox[1] for item in joined)
            x1 = max(item[1].bbox[2] for item in joined)
            y1 = max(item[1].bbox[3] for item in joined)
            windows.append(
                TextWindow(
                    source=source,
                    line_indices=tuple(item[0] for item in joined),
                    text=text,
                    key=retrieval_key(text),
                    bbox=(x0, y0, x1, y1),
                )
            )
    unique = {
        (window.source, window.line_indices, window.key): window
        for window in windows
        if window.key
    }
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                _center_y(item),
                item.bbox[0],
                len(item.line_indices),
                item.key,
            ),
        )
    )


def _semantic_windows(
    geometry_page: OCRPage,
    semantic_page: OCRPage | None,
    config: dict[str, Any],
    *,
    header_only: bool,
) -> tuple[TextWindow, ...]:
    geometry_source = config.get("geometry_evidence_source")
    if geometry_source is None:
        if config.get("geometry_authority") != "PP_OCRV6_WORD_BOXES":
            raise StatementLocatorError(
                "non-PP-OCR geometry requires an explicit evidence-source authority"
            )
        geometry_source = "PP_OCRV6_GEOMETRY"
    if not isinstance(geometry_source, str) or not geometry_source.strip():
        raise StatementLocatorError("geometry evidence-source authority is invalid")
    windows = list(
        _windows_for_page(
            geometry_page,
            source=geometry_source,
            config=config,
            header_only=header_only,
            label_only=not header_only,
        )
    )
    if semantic_page is not None:
        if semantic_page.page != geometry_page.page:
            raise StatementLocatorError("semantic-reader page identity differs from geometry page")
        width_ratio = semantic_page.width / geometry_page.width
        height_ratio = semantic_page.height / geometry_page.height
        if not 0.98 <= width_ratio <= 1.02 or not 0.98 <= height_ratio <= 1.02:
            raise StatementLocatorError("semantic-reader page dimensions differ from geometry page")
        windows.extend(
            _windows_for_page(
                semantic_page,
                source="INDEPENDENT_SEMANTIC_READER",
                config=config,
                header_only=header_only,
                label_only=not header_only,
            )
        )
    return tuple(windows)


def _similarity(key: str, anchor: str) -> float:
    if not key or not anchor:
        return 0.0
    if _core_is_token_bounded(key, anchor):
        return 1.0
    return ratio(key, anchor) / 100.0


def _best_anchor(
    windows: tuple[TextWindow, ...], anchors: list[str], *, plain_ratio: bool = False
) -> AnchorHit | None:
    best: AnchorHit | None = None
    for raw_anchor in anchors:
        anchor = retrieval_key(str(raw_anchor))
        for window in windows:
            similarity = (
                ratio(window.key, anchor) / 100.0
                if plain_ratio
                else _similarity(window.key, anchor)
            )
            candidate = AnchorHit(
                anchor=str(raw_anchor),
                source=window.source,
                line_indices=window.line_indices,
                text=window.text,
                bbox=window.bbox,
                similarity=round(similarity, 6),
            )
            if best is None or (
                candidate.similarity,
                -len(candidate.line_indices),
                candidate.source,
                candidate.line_indices,
            ) > (
                best.similarity,
                -len(best.line_indices),
                best.source,
                best.line_indices,
            ):
                best = candidate
    return best


def _distinct_anchor_hits(
    windows: tuple[TextWindow, ...],
    raw_anchors: list[str],
    minimum: float,
    *,
    plain_ratio: bool = False,
) -> tuple[AnchorHit, ...]:
    proposals: list[AnchorHit] = []
    for raw_anchor in raw_anchors:
        anchor = retrieval_key(str(raw_anchor))
        for window in windows:
            similarity = (
                ratio(window.key, anchor) / 100.0
                if plain_ratio
                else _similarity(window.key, anchor)
            )
            if similarity >= minimum:
                proposals.append(
                    AnchorHit(
                        anchor=str(raw_anchor),
                        source=window.source,
                        line_indices=window.line_indices,
                        text=window.text,
                        bbox=window.bbox,
                        similarity=round(similarity, 6),
                    )
                )
    proposals.sort(
        key=lambda item: (
            -item.similarity,
            item.anchor,
            item.source,
            item.line_indices,
        )
    )
    selected: list[AnchorHit] = []
    used_anchors: set[str] = set()
    used_line_indices: dict[str, set[int]] = {}
    used_vertical_intervals: list[tuple[float, float]] = []
    for proposal in proposals:
        source_indices = used_line_indices.setdefault(proposal.source, set())
        overlaps_source_lines = bool(source_indices.intersection(proposal.line_indices))
        proposal_height = max(1.0, proposal.bbox[3] - proposal.bbox[1])
        overlaps_spatially = any(
            max(0.0, min(proposal.bbox[3], y1) - max(proposal.bbox[1], y0))
            / min(proposal_height, max(1.0, y1 - y0))
            >= 0.50
            for y0, y1 in used_vertical_intervals
        )
        if proposal.anchor in used_anchors or overlaps_source_lines or overlaps_spatially:
            continue
        selected.append(proposal)
        used_anchors.add(proposal.anchor)
        source_indices.update(proposal.line_indices)
        used_vertical_intervals.append((proposal.bbox[1], proposal.bbox[3]))
    return tuple(sorted(selected, key=lambda item: (item.line_indices, item.anchor, item.source)))


def _cluster_positions(values: list[float], tolerance: float) -> tuple[tuple[float, int], ...]:
    clusters: list[list[float]] = []
    for value in sorted(values):
        if not clusters or abs(value - sum(clusters[-1]) / len(clusters[-1])) > tolerance:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    return tuple((round(sum(items) / len(items), 6), len(items)) for items in clusters)


def _numeric_geometry(page: OCRPage, config: dict[str, Any]) -> NumericGeometry:
    policy = config["numeric_geometry"]
    positions: list[float] = []
    y_positions: list[float] = []
    accepted = {ObservationKind.VALUE, ObservationKind.ZERO, ObservationKind.DASH}
    for line in page.lines:
        center_y = _center_y(line) / page.height
        if center_y < float(policy["content_min_y_fraction"]):
            continue
        if (
            line.bbox[0] / page.width < float(policy["numeric_min_x_fraction"])
            or line.bbox[2] / page.width < float(policy["numeric_min_right_edge_fraction"])
        ):
            continue
        if parse_financial_number(line.text).observation not in accepted:
            continue
        positions.append(line.bbox[2] / page.width)
        y_positions.append(center_y)
    clustered = _cluster_positions(
        positions, float(policy["axis_cluster_tolerance_fraction"])
    )
    qualified = tuple(
        (axis, count)
        for axis, count in clustered
        if count >= int(policy["min_cells_per_axis"])
    )
    return NumericGeometry(
        passes=len(qualified) >= int(policy["min_axis_count"]),
        axes=tuple(axis for axis, _ in qualified),
        axis_cell_counts=tuple(count for _, count in qualified),
        financial_cell_count=len(positions),
        first_cell_y_fraction=round(min(y_positions), 6) if y_positions else None,
        last_cell_y_fraction=round(max(y_positions), 6) if y_positions else None,
    )


def _unit_line_hits(
    page: OCRPage, config: dict[str, Any]
) -> list[tuple[float, float, float, str, str]]:
    policy = config["unit"]
    hits: list[tuple[float, float, float, str, str]] = []
    anchors = [(str(value), retrieval_key(str(value))) for value in policy["anchors"]]
    for line in page.lines:
        if _center_y(line) / page.height > float(policy["top_fraction"]):
            continue
        if line.bbox[0] / page.width < float(policy["right_region_min_x_fraction"]):
            continue
        ranked = sorted(
            ((_similarity(line.key, anchor_key), raw_anchor) for raw_anchor, anchor_key in anchors),
            reverse=True,
        )
        similarity, raw_anchor = ranked[0]
        if similarity < float(policy["min_similarity"]):
            continue
        hits.append(
            (
                (line.bbox[0] + line.bbox[2]) / (2 * page.width),
                _center_y(line) / page.height,
                similarity,
                retrieval_key(raw_anchor),
                line.text,
            )
        )
    return hits


def _period_evidence(page: OCRPage, config: dict[str, Any]) -> PeriodEvidence:
    policy = config["period_axis"]
    candidates: list[tuple[float, float, tuple[str, ...], int]] = []
    report_years: set[str] = set()
    for line in page.lines:
        y_fraction = _center_y(line) / page.height
        if y_fraction > float(policy["top_fraction"]):
            continue
        years = tuple(_YEAR.findall(line.text))
        if not years:
            continue
        key_tokens = line.key.split()
        if line.bbox[0] / page.width < 0.65 and len(key_tokens) <= 12:
            report_years.update(years)
        if (
            line.bbox[0] / page.width
            < float(policy["right_region_min_x_fraction"])
            or len(key_tokens) > int(policy["max_token_count"])
            or any(
                phrase in line.key
                for phrase in ("thong tu", "ban hanh", "ngan hang nha nuoc")
            )
        ):
            continue
        candidates.append(
            (
                (line.bbox[0] + line.bbox[2]) / (2 * page.width),
                y_fraction,
                years,
                len(key_tokens),
            )
        )
    paired: list[tuple[float, float, tuple[str, ...], int]] = []
    for unit_x, unit_y, _, _, _ in _unit_line_hits(page, config):
        compatible = [
            candidate
            for candidate in candidates
            if abs(candidate[0] - unit_x) <= 0.09
            and -0.01 <= unit_y - candidate[1] <= 0.08
        ]
        if compatible:
            paired.append(
                min(
                    compatible,
                    key=lambda item: (abs(unit_y - item[1]), abs(unit_x - item[0]), item[3]),
                )
            )
    selected_candidates = paired
    if len(_cluster_positions([item[0] for item in paired], 0.055)) < int(
        policy["min_distinct_columns"]
    ):
        selected_candidates = [candidate for candidate in candidates if candidate[3] <= 4]
    clustered = _cluster_positions(
        [position for position, _, _, _ in selected_candidates],
        float(policy["axis_cluster_tolerance_fraction"]),
    )
    axes = tuple(axis for axis, _ in clustered)
    signatures = []
    for axis in axes:
        years = {
            year
            for position, _, raw_years, _ in selected_candidates
            if abs(position - axis) <= float(policy["axis_cluster_tolerance_fraction"])
            for year in raw_years
        }
        signatures.append(tuple(sorted(years)))
    return PeriodEvidence(
        passes_main_axis=len(axes) >= int(policy["min_distinct_columns"]),
        axis_positions=axes,
        axis_year_signatures=tuple(signatures),
        report_years=tuple(sorted(report_years)),
    )


def _unit_evidence(page: OCRPage, config: dict[str, Any]) -> UnitEvidence:
    hits = _unit_line_hits(page, config)
    clusters = _cluster_positions(
        [position for position, _, _, _, _ in hits],
        float(config["period_axis"]["axis_cluster_tolerance_fraction"]),
    )
    return UnitEvidence(
        passes=bool(hits),
        axis_positions=tuple(axis for axis, _ in clusters),
        canonical_signatures=tuple(
            sorted({canonical for _, _, _, canonical, _ in hits})
        ),
        raw_texts=tuple(text for _, _, _, _, text in sorted(hits)),
    )


def _narrative_fraction(page: OCRPage, config: dict[str, Any]) -> float:
    policy = config["narrative"]
    text_lines = [line for line in page.lines if line.key and _is_text_line(line)]
    if not text_lines:
        return 0.0
    long_lines = sum(
        len(line.text.strip()) >= int(policy["long_line_min_characters"])
        and (line.bbox[2] - line.bbox[0]) / page.width
        >= float(policy["long_line_min_span_fraction"])
        for line in text_lines
    )
    return long_lines / len(text_lines)


def _notes_structure(page: OCRPage, config: dict[str, Any]) -> bool:
    policy = config["notes_structure"]
    has_section_marker = any(
        line.bbox[0] / page.width <= float(policy["section_marker_max_x_fraction"])
        and _SECTION_MARKER.fullmatch(line.key) is not None
        for line in page.lines
    )
    narrative = config["narrative"]
    long_prose = sum(
        _is_text_line(line)
        and len(line.text.strip()) >= int(narrative["long_line_min_characters"])
        and (line.bbox[2] - line.bbox[0]) / page.width
        >= float(narrative["long_line_min_span_fraction"])
        for line in page.lines
    )
    return has_section_marker and long_prose >= int(policy["min_long_prose_lines"])


def _header_identity(
    header_windows: tuple[TextWindow, ...], config: dict[str, Any]
) -> tuple[
    StatementPageType | None,
    bool,
    tuple[StatementPageType, ...],
    dict[str, float],
    dict[str, str | None],
]:
    base = config["header_candidate"]
    forms: set[StatementPageType] = set()
    for source in {window.source for window in header_windows}:
        source_windows = tuple(window for window in header_windows if window.source == source)
        lines = tuple(OCRLine(window.text, window.bbox, 1.0) for window in source_windows)
        forms.update(item.page_type for item in _form_family_evidence(lines, base["form_anchors"]))
    title_scores: dict[str, float] = {}
    title_sources: dict[str, str | None] = {}
    for raw_type, raw_anchors in base["title_anchors"].items():
        page_type = StatementPageType(raw_type)
        best_score = 0.0
        best_source: str | None = None
        for raw_anchor in raw_anchors:
            anchor = retrieval_key(str(raw_anchor))
            for window in header_windows:
                score = _similarity(window.key, anchor)
                if score > best_score:
                    best_score = score
                    best_source = window.source
        title_scores[page_type.value] = round(best_score, 6)
        title_sources[page_type.value] = best_source
    policy = config["header_identity"]
    ranked = sorted(title_scores.items(), key=lambda item: (-item[1], item[0]))
    title_type = StatementPageType(ranked[0][0])
    title_is_decisive = (
        ranked[0][1] >= float(policy["title_candidate_min_similarity"])
        and ranked[0][1] - ranked[1][1] >= float(policy["title_candidate_min_margin"])
    )
    form_types = tuple(sorted(forms, key=lambda item: item.value))
    conflict = len(form_types) > 1
    if len(form_types) == 1:
        selected = form_types[0]
        if title_is_decisive and title_type is not selected:
            conflict = True
    elif title_is_decisive:
        selected = title_type
    else:
        selected = None
    return selected, conflict, form_types, title_scores, title_sources


def _local_acceptance_thresholds(
    page_type: StatementPageType,
    form_types: tuple[StatementPageType, ...],
    continuation_marker: bool,
    title_scores: dict[str, float],
    config: dict[str, Any],
    *,
    notes_boundary_transition: bool = False,
) -> tuple[int, float]:
    acceptance = config["acceptance"]
    minimum_groups = int(
        acceptance[
            "notes_min_independent_groups"
            if page_type is StatementPageType.TM
            else "main_min_independent_groups"
        ]
    )
    minimum_score = float(acceptance["min_local_score"])
    override = config.get("notes_boundary_acceptance_override")
    if (
        override is None
        or page_type is not StatementPageType.TM
        or not notes_boundary_transition
    ):
        return minimum_groups, minimum_score
    if (
        not isinstance(override, dict)
        or override.get("policy") != "EXACT_FORM_TITLE_THREE_GROUP_NOTES_BOUNDARY"
        or override.get("geometry_authority") != "PYMUPDF_NATIVE_TEXT_WORDS"
        or config.get("geometry_authority") != "PYMUPDF_NATIVE_TEXT_WORDS"
        or config.get("geometry_evidence_source") != "PYMUPDF_NATIVE_TEXT_GEOMETRY"
        or config.get("policy") != "NATIVE_TEXT_MULTI_SIGNAL_ORDERED_DOCUMENT_DISCOVERY_V1"
        or override.get("require_form_type") != "TM"
        or override.get("require_continuation_marker") is not False
        or override.get("require_notes_anchors") is not True
        or override.get("require_notes_structure") is not True
    ):
        raise StatementLocatorError("notes-boundary acceptance override is invalid")
    if (
        page_type in form_types
        and not continuation_marker
        and title_scores[page_type.value] >= float(override["minimum_title_similarity"])
    ):
        return int(override["minimum_independent_groups"]), float(
            override["minimum_local_score"]
        )
    return minimum_groups, minimum_score


def _signal_record(
    geometry_page: OCRPage,
    semantic_page: OCRPage | None,
    config: dict[str, Any],
) -> PageSignalRecord:
    header_windows = _semantic_windows(
        geometry_page, semantic_page, config, header_only=True
    )
    label_windows = _semantic_windows(
        geometry_page, semantic_page, config, header_only=False
    )
    header_type, header_conflict, forms, title_scores, title_sources = _header_identity(
        header_windows, config
    )
    period = _period_evidence(geometry_page, config)
    unit = _unit_evidence(geometry_page, config)
    numeric = _numeric_geometry(geometry_page, config)
    continuation = _best_anchor(
        header_windows, config["header_candidate"]["continuation_anchors"]
    )
    continuation_marker = bool(
        continuation
        and continuation.similarity
        >= float(config["header_candidate"]["continuation_anchor_min_similarity"])
    )
    narrative_fraction = _narrative_fraction(geometry_page, config)
    narrative_penalty = narrative_fraction >= float(config["narrative"]["penalty_fraction"])
    audit = _best_anchor(header_windows, config["narrative"]["audit_anchors"])
    toc = _best_anchor(header_windows, config["header_candidate"]["toc_anchors"])
    audit_suppression = bool(
        audit and audit.similarity >= float(config["header_identity"]["audit_min_similarity"])
    )
    toc_suppression = bool(
        toc and toc.similarity >= float(config["header_identity"]["toc_min_similarity"])
    )

    off_policy = config["off_balance_scope"]
    off_heading = _best_anchor(
        label_windows + header_windows,
        off_policy["headings"],
        plain_ratio=True,
    )
    off_heading_score = off_heading.similarity if off_heading else 0.0
    off_heading_key = retrieval_key(off_heading.text) if off_heading else ""
    off_heading_has_discriminator = any(
        phrase in f" {off_heading_key} "
        for phrase in (" chi tieu ngoai ", " ngoai bao cao ", " off balance ")
    )
    off_hits = _distinct_anchor_hits(
        label_windows,
        off_policy["items"],
        float(off_policy["item_min_similarity"]),
        plain_ratio=True,
    )
    off_balance = (
        (
            off_heading_has_discriminator
            and off_heading_score >= float(off_policy["heading_min_similarity"])
        )
        or len(off_hits) >= int(off_policy["min_distinct_item_hits"])
    )
    notes_structure = _notes_structure(geometry_page, config)
    accounting_policy = config["accounting_rows"]
    min_hits = int(accounting_policy["min_distinct_hits"])
    weights = config["signal_weights"]
    acceptance = config["acceptance"]
    candidates: list[PageTypeCandidate] = []
    for page_type in _TARGET_TYPES:
        accounting_hits = _distinct_anchor_hits(
            label_windows,
            accounting_policy["anchors"][page_type.value],
            float(accounting_policy["min_similarity"]),
        )
        header_pass = header_type is page_type and not header_conflict
        accounting_pass = len(accounting_hits) >= min_hits
        groups: list[str] = []
        score = 0.0
        if header_pass:
            groups.append("HEADER_IDENTITY")
            header_quality = max(
                1.0 if page_type in forms else 0.0,
                title_scores[page_type.value],
            )
            score += float(weights["header_identity"]) * header_quality
        if page_type is StatementPageType.TM:
            if period.report_years:
                groups.append("REPORTING_PERIOD")
                score += float(weights["period_axis"])
            if accounting_pass:
                groups.append("NOTES_ANCHORS")
                score += float(weights["accounting_rows"])
            if notes_structure:
                groups.append("NOTES_STRUCTURE")
                score += float(weights["notes_structure"])
        else:
            if period.passes_main_axis:
                groups.append("PERIOD_AXIS")
                score += float(weights["period_axis"])
            if unit.passes:
                groups.append("UNIT")
                score += float(weights["unit"])
            row_support = accounting_pass or (
                page_type is StatementPageType.CDKT and off_balance
            )
            if row_support:
                groups.append("ACCOUNTING_ROWS")
                score += float(weights["accounting_rows"])
            if numeric.passes:
                groups.append("NUMERIC_GEOMETRY")
                score += float(weights["numeric_geometry"])
            if page_type is StatementPageType.CDKT and off_balance:
                groups.append("OFF_BALANCE_SCOPE")
                score += float(weights["off_balance_scope"])
        if continuation_marker:
            groups.append("CONTINUATION")
            score += float(weights["continuation"])
        if narrative_penalty and page_type is not StatementPageType.TM:
            score -= float(weights["narrative_penalty"])
        if audit_suppression or toc_suppression:
            score -= float(weights["audit_or_toc_penalty"])

        minimum_groups, local_minimum_score = _local_acceptance_thresholds(
            page_type,
            forms,
            continuation_marker,
            title_scores,
            config,
        )
        if page_type is StatementPageType.TM:
            gate = (
                header_pass
                and accounting_pass
                and notes_structure
                and len(groups) >= minimum_groups
            )
        else:
            row_gate = accounting_pass or (
                page_type is StatementPageType.CDKT and off_balance
            )
            gate = (
                header_pass
                and row_gate
                and numeric.passes
                and len(groups) >= minimum_groups
            )
        locally_accepted = (
            gate
            and not header_conflict
            and not audit_suppression
            and not toc_suppression
            and score >= local_minimum_score
        )
        scope = (
            StatementScope.OFF_BALANCE_SHEET
            if page_type is StatementPageType.CDKT and off_balance
            else StatementScope.MAIN_STATEMENT
            if page_type in _MAIN_TYPES
            else StatementScope.NOT_APPLICABLE
        )
        candidates.append(
            PageTypeCandidate(
                page_type=page_type,
                scope=scope,
                score=round(score, 6),
                independent_signal_groups=tuple(groups),
                accounting_hits=accounting_hits,
                locally_accepted=locally_accepted,
            )
        )

    accepted = sorted(
        (candidate for candidate in candidates if candidate.locally_accepted),
        key=lambda item: (-item.score, item.page_type.value),
    )
    if len(accepted) > 1 and accepted[0].score - accepted[1].score < float(
        acceptance["page_type_runner_up_margin"]
    ):
        candidates = [
            replace(candidate, locally_accepted=False)
            if candidate.locally_accepted
            else candidate
            for candidate in candidates
        ]
    return PageSignalRecord(
        page=geometry_page.page,
        header_candidate_type=header_type,
        header_conflict=header_conflict,
        form_types=forms,
        title_scores=title_scores,
        title_sources=title_sources,
        period=period,
        unit=unit,
        numeric_geometry=numeric,
        continuation_marker=continuation_marker,
        narrative_fraction=round(narrative_fraction, 6),
        narrative_penalty=narrative_penalty,
        audit_suppression=audit_suppression,
        toc_suppression=toc_suppression,
        notes_structure=notes_structure,
        off_balance_heading_score=round(off_heading_score, 6),
        off_balance_item_hits=off_hits,
        candidates=tuple(candidates),
    )


def _candidate(record: PageSignalRecord, page_type: StatementPageType) -> PageTypeCandidate:
    return next(item for item in record.candidates if item.page_type is page_type)


def _axes_compatible(left: NumericGeometry, right: NumericGeometry, maximum: float) -> bool:
    if not left.passes or not right.passes:
        return False
    remaining = list(right.axes)
    matches = 0
    for axis in left.axes:
        if not remaining:
            break
        closest = min(remaining, key=lambda value: abs(axis - value))
        if abs(axis - closest) <= maximum:
            matches += 1
            remaining.remove(closest)
    return matches >= 2


def _period_compatible(left: PeriodEvidence, right: PeriodEvidence) -> bool:
    if not left.passes_main_axis or not right.passes_main_axis:
        return False
    left_years = tuple(signature for signature in left.axis_year_signatures if signature)
    right_years = tuple(signature for signature in right.axis_year_signatures if signature)
    return bool(left_years and right_years and left_years == right_years)


def _unit_compatible(left: UnitEvidence, right: UnitEvidence) -> bool:
    return bool(
        left.passes
        and right.passes
        and set(left.canonical_signatures).intersection(right.canonical_signatures)
    )


def _table_edge_continuity(
    earlier: NumericGeometry, later: NumericGeometry, config: dict[str, Any]
) -> bool:
    policy = config["numeric_geometry"]
    return bool(
        earlier.last_cell_y_fraction is not None
        and later.first_cell_y_fraction is not None
        and earlier.last_cell_y_fraction >= float(policy["bottom_table_edge_fraction"])
        and later.first_cell_y_fraction <= float(policy["top_table_edge_fraction"])
    )


def _add_bounded_neighbor_inference(
    records: tuple[PageSignalRecord, ...], config: dict[str, Any]
) -> tuple[PageSignalRecord, ...]:
    policy = config["neighbor_inference"]
    accounting_min_hits = int(config["accounting_rows"]["min_distinct_hits"])
    local_accepted = {
        (index, candidate.page_type): candidate
        for index, record in enumerate(records)
        for candidate in record.candidates
        if candidate.locally_accepted
    }
    updated: list[PageSignalRecord] = []
    for index, record in enumerate(records):
        if any(candidate.locally_accepted for candidate in record.candidates):
            updated.append(record)
            continue
        proposals: list[PageTypeCandidate] = []
        for page_type in _MAIN_TYPES:
            weak = _candidate(record, page_type)
            if (
                record.audit_suppression
                or record.toc_suppression
                or record.header_conflict
                or weak.scope is StatementScope.OFF_BALANCE_SHEET
                or len(weak.accounting_hits) < accounting_min_hits
                or not record.numeric_geometry.passes
            ):
                continue
            for neighbor_index in (index - 1, index + 1):
                neighbor = local_accepted.get((neighbor_index, page_type))
                if neighbor is None or neighbor.scope is not StatementScope.MAIN_STATEMENT:
                    continue
                neighbor_record = records[neighbor_index]
                axes = _axes_compatible(
                    record.numeric_geometry,
                    neighbor_record.numeric_geometry,
                    float(policy["axis_max_delta_fraction"]),
                )
                period = _period_compatible(record.period, neighbor_record.period)
                unit = _unit_compatible(record.unit, neighbor_record.unit)
                if neighbor_index < index:
                    edge = _table_edge_continuity(
                        neighbor_record.numeric_geometry, record.numeric_geometry, config
                    )
                    direction = "FORWARD_FROM_PREVIOUS"
                else:
                    edge = _table_edge_continuity(
                        record.numeric_geometry, neighbor_record.numeric_geometry, config
                    )
                    direction = "BACKWARD_FROM_NEXT"
                metadata_verified = (period and unit) or (
                    record.continuation_marker and (period or unit)
                )
                if not axes or not (metadata_verified or edge):
                    continue
                checks = ["ACCOUNTING_ROWS", "NUMERIC_GEOMETRY", "SHARED_NUMERIC_AXES"]
                if period:
                    checks.append("SHARED_PERIOD_AXIS")
                if unit:
                    checks.append("SHARED_UNIT")
                if record.continuation_marker:
                    checks.append("CONTINUATION_MARKER")
                if edge:
                    checks.append("TABLE_EDGE_CONTINUITY")
                proposals.append(
                    PageTypeCandidate(
                        page_type=page_type,
                        scope=StatementScope.MAIN_STATEMENT,
                        score=round(
                            weak.score * float(policy["score_discount"]), 6
                        ),
                        independent_signal_groups=weak.independent_signal_groups,
                        accounting_hits=weak.accounting_hits,
                        locally_accepted=False,
                        inferred_from_page=neighbor_record.page,
                        inference_direction=direction,
                        inference_checks=tuple(checks),
                    )
                )
        distinct_types = {proposal.page_type for proposal in proposals}
        if len(distinct_types) == 1:
            best = max(
                proposals,
                key=lambda item: (
                    item.score,
                    -(item.inferred_from_page or 0),
                    item.inference_direction or "",
                ),
            )
            candidates = tuple(
                best if candidate.page_type is best.page_type else candidate
                for candidate in record.candidates
            )
            updated.append(replace(record, candidates=candidates))
        else:
            updated.append(record)
    return tuple(updated)


def _candidate_is_usable(candidate: PageTypeCandidate) -> bool:
    return candidate.locally_accepted or candidate.inferred_from_page is not None


def _k_best_document_paths(
    records: tuple[PageSignalRecord, ...], config: dict[str, Any]
) -> tuple[_Path, ...]:
    states = tuple(config["document_sequence"]["states"])
    transitions = {
        "PRE": ("PRE", "CDKT"),
        "CDKT": ("CDKT", "KQKD"),
        "KQKD": ("KQKD", "LCTT"),
        "LCTT": ("LCTT", "TM"),
        "TM": ("POST",),
        "POST": ("POST",),
    }
    k = int(config["document_sequence"]["k_best_paths_per_state"])
    active: dict[str, list[_Path]] = {state: [] for state in states}
    active["PRE"] = [_Path(score=0.0, states=())]
    for record in records:
        following: dict[str, list[_Path]] = {state: [] for state in states}
        for previous_state, paths in active.items():
            for path in paths:
                for next_state in transitions[previous_state]:
                    emission = 0.0
                    if next_state in {item.value for item in _TARGET_TYPES}:
                        candidate = _candidate(record, StatementPageType(next_state))
                        if not _candidate_is_usable(candidate):
                            continue
                        emission = candidate.score
                    following[next_state].append(
                        _Path(score=path.score + emission, states=(*path.states, next_state))
                    )
        for state in states:
            unique = {path.states: path for path in following[state]}
            active[state] = sorted(
                unique.values(), key=lambda item: (-item.score, item.states)
            )[:k]
    complete = [*active["TM"], *active["POST"]]
    unique_blocks: dict[tuple[tuple[int, str], ...], _Path] = {}
    for path in complete:
        signature = tuple(
            (records[index].page, state)
            for index, state in enumerate(path.states)
            if state in {item.value for item in _TARGET_TYPES}
        )
        previous = unique_blocks.get(signature)
        if previous is None or path.score > previous.score:
            unique_blocks[signature] = path
    return tuple(
        sorted(unique_blocks.values(), key=lambda item: (-item.score, item.states))
    )


def _json_candidate(candidate: PageTypeCandidate) -> dict[str, Any]:
    payload = asdict(candidate)
    payload["page_type"] = candidate.page_type.value
    payload["scope"] = candidate.scope.value
    return payload


def _json_record(record: PageSignalRecord) -> dict[str, Any]:
    return {
        "page": record.page,
        "header_candidate_type": (
            record.header_candidate_type.value if record.header_candidate_type else None
        ),
        "header_conflict": record.header_conflict,
        "form_types": [item.value for item in record.form_types],
        "title_scores": record.title_scores,
        "title_sources": record.title_sources,
        "period": asdict(record.period),
        "unit": asdict(record.unit),
        "numeric_geometry": asdict(record.numeric_geometry),
        "continuation_marker": record.continuation_marker,
        "narrative_fraction": record.narrative_fraction,
        "narrative_penalty": record.narrative_penalty,
        "audit_suppression": record.audit_suppression,
        "toc_suppression": record.toc_suppression,
        "notes_structure": record.notes_structure,
        "off_balance_heading_score": record.off_balance_heading_score,
        "off_balance_item_hits": [asdict(item) for item in record.off_balance_item_hits],
        "candidates": [_json_candidate(item) for item in record.candidates],
    }


def _path_summary(path: _Path, records: tuple[PageSignalRecord, ...]) -> dict[str, Any]:
    typed = [
        (records[index], StatementPageType(state))
        for index, state in enumerate(path.states)
        if state in {item.value for item in _TARGET_TYPES}
    ]
    return {
        "score": round(path.score, 6),
        "start_page": typed[0][0].page,
        "end_page": next(
            record.page for record, page_type in reversed(typed) if page_type is not StatementPageType.TM
        ),
        "notes_boundary_page": next(
            record.page for record, page_type in typed if page_type is StatementPageType.TM
        ),
        "typed_pages": [
            {"page": record.page, "statement_type": page_type.value}
            for record, page_type in typed
        ],
    }


def discover_statement_pages(
    geometry_pages: tuple[OCRPage, ...],
    config: dict[str, Any],
    *,
    semantic_pages: tuple[OCRPage, ...] | None = None,
) -> dict[str, Any]:
    if config.get("version") != 3 or not isinstance(config.get("header_candidate"), dict):
        raise StatementLocatorError("statement-discovery v3 config is required")
    if not geometry_pages:
        raise StatementLocatorError("statement discovery requires geometry pages")
    observed = tuple(page.page for page in geometry_pages)
    if observed != tuple(range(observed[0], observed[-1] + 1)):
        raise StatementLocatorError("statement discovery requires contiguous geometry pages")
    semantic_by_page: dict[int, OCRPage] = {}
    if semantic_pages is not None:
        semantic_by_page = {page.page: page for page in semantic_pages}
        if len(semantic_by_page) != len(semantic_pages) or set(semantic_by_page) != set(observed):
            raise StatementLocatorError(
                "semantic-reader pages must be unique and cover the geometry-page sequence"
            )
    records = tuple(
        _signal_record(page, semantic_by_page.get(page.page), config)
        for page in geometry_pages
    )
    records = _add_bounded_neighbor_inference(records, config)
    paths = _k_best_document_paths(records, config)
    summaries = [_path_summary(path, records) for path in paths]
    margin = paths[0].score - paths[1].score if len(paths) > 1 else None
    common = {
        "algorithm_revision": 3,
        "policy": config["policy"],
        "geometry_authority": config["geometry_authority"],
        "semantic_reader_authority": config["semantic_reader_authority"],
        "observed_pages": list(observed),
        "page_signals": [_json_record(record) for record in records],
        "candidate_path_count": len(paths),
        "candidate_path_summaries": summaries,
        "runner_up_margin": round(margin, 6) if margin is not None else None,
    }
    errors = []
    if not paths:
        errors.append("no complete multi-signal CDKT->KQKD->LCTT->TM path")
    elif margin is not None and margin < float(
        config["acceptance"]["document_path_runner_up_margin"]
    ):
        errors.append(f"document-path runner-up margin too small: {margin:.6f}")
    if errors:
        return {"status": "UNRESOLVED", **common, "errors": errors}

    accepted = paths[0]
    typed = [
        (index, records[index], StatementPageType(state))
        for index, state in enumerate(accepted.states)
        if state in {item.value for item in _TARGET_TYPES}
    ]
    statement_pages = [item for item in typed if item[2] is not StatementPageType.TM]
    notes_page = next(record.page for _, record, kind in typed if kind is StatementPageType.TM)
    page_contracts = []
    for position, (_, record, page_type) in enumerate(statement_pages):
        candidate = _candidate(record, page_type)
        previous = statement_pages[position - 1] if position else None
        following = statement_pages[position + 1] if position + 1 < len(statement_pages) else None
        page_contracts.append(
            {
                "page": record.page,
                "statement_type": page_type.value,
                "scope": candidate.scope.value,
                "mapping_eligible": candidate.scope is StatementScope.MAIN_STATEMENT,
                "continuation_from_page": (
                    previous[1].page if previous and previous[2] is page_type else None
                ),
                "continuation_to_page": (
                    following[1].page if following and following[2] is page_type else None
                ),
                "locally_accepted": candidate.locally_accepted,
                "inferred_from_page": candidate.inferred_from_page,
                "inference_direction": candidate.inference_direction,
                "inference_checks": list(candidate.inference_checks),
                "score": candidate.score,
                "independent_signal_groups": list(candidate.independent_signal_groups),
            }
        )
    recognized = {
        page_type.value: [
            record.page
            for _, record, observed_type in statement_pages
            if observed_type is page_type
        ]
        for page_type in _MAIN_TYPES
    }
    eligible = {
        page_type.value: [
            record.page
            for _, record, observed_type in statement_pages
            if observed_type is page_type
            and _candidate(record, page_type).scope is StatementScope.MAIN_STATEMENT
        ]
        for page_type in _MAIN_TYPES
    }
    lctt_page_numbers = set(recognized[StatementPageType.LCTT.value])
    lctt_pages = tuple(page for page in geometry_pages if page.page in lctt_page_numbers)
    return {
        "status": "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK",
        **common,
        "block": {
            "start_page": statement_pages[0][1].page,
            "end_page": statement_pages[-1][1].page,
            "notes_boundary_page": notes_page,
            "score": round(accepted.score, 6),
            "recognized_pages_by_statement_type": recognized,
            "mapping_eligible_pages_by_statement_type": eligible,
            "mapping_eligible_pages": [
                contract["page"] for contract in page_contracts if contract["mapping_eligible"]
            ],
            "off_balance_excluded_pages": [
                contract["page"]
                for contract in page_contracts
                if contract["scope"] == StatementScope.OFF_BALANCE_SHEET.value
            ],
            "page_contracts": page_contracts,
        },
        "cash_flow": detect_cash_flow_method(lctt_pages, config["header_candidate"]),
        "errors": [],
    }
