from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.distance import DamerauLevenshtein

from bctc_ai.core.text import normalize_text, retrieval_key


class VietnameseLabelCorrectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class VietnameseLabelCorrectionConfig:
    maximum_phrase_tokens: int
    minimum_document_support: int
    minimum_document_support_ratio: float
    protected_function_keys: tuple[str, ...]
    maximum_damerau_distance: int
    minimum_full_label_similarity: float
    minimum_full_label_runner_up_margin: float
    minimum_phrase_similarity: float
    minimum_acronym_similarity: float
    minimum_phrase_runner_up_margin: float
    minimum_acronym_characters: int
    maximum_replacements_per_label: int


@dataclass(frozen=True)
class VocabularyLabel:
    statement_type: str
    label: str
    source_id: str


@dataclass(frozen=True)
class OrderedObservedLabel:
    row_id: str
    statement_type: str
    raw_label: str


@dataclass(frozen=True)
class LabelReplacementEvidence:
    start_token: int
    end_token_exclusive: int
    source_text: str
    proposed_text: str
    source_key: str
    candidate_key: str
    vocabulary_source_ids: tuple[str, ...]
    candidate_kind: str
    damerau_distance: int
    similarity: float
    runner_up_similarity: float | None
    score_margin: float | None
    document_support_count: int
    source_document_support_count: int
    document_support_ratio: float


@dataclass(frozen=True)
class VietnameseLabelCorrectionProposal:
    row_id: str
    row_position: int
    statement_type: str
    raw_label: str
    corrected_label: str
    previous_raw_label: str | None
    next_raw_label: str | None
    status: str
    replacements: tuple[LabelReplacementEvidence, ...]
    raw_label_preserved: bool
    row_order_preserved: bool
    automatic_output_authority: bool
    automatic_schema_mapping_authority: bool


@dataclass(frozen=True)
class VietnameseLabelCorrectionResult:
    status: str
    proposals: tuple[VietnameseLabelCorrectionProposal, ...]
    corrected_count: int
    unchanged_count: int
    raw_labels_preserved: bool
    row_order_preserved: bool
    numeric_or_note_fields_present: bool
    automatic_output_authority: bool
    automatic_schema_mapping_authority: bool


@dataclass(frozen=True)
class _Token:
    text: str
    start: int
    end: int
    key: str


@dataclass(frozen=True)
class _VocabularyCandidate:
    key: str
    surface: str
    source_ids: tuple[str, ...]
    token_count: int


@dataclass(frozen=True)
class _AcceptedReplacement:
    start_token: int
    end_token_exclusive: int
    char_start: int
    char_end: int
    evidence: LabelReplacementEvidence


_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)


def _bounded_float(payload: dict[str, Any], name: str) -> float:
    value = payload.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
        raise VietnameseLabelCorrectionError(f"invalid label-correction threshold: {name}")
    return float(value)


def _positive_integer(payload: dict[str, Any], name: str) -> int:
    value = payload.get(name)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise VietnameseLabelCorrectionError(f"invalid label-correction integer: {name}")
    return value


def _minimum_float(payload: dict[str, Any], name: str, minimum: float) -> float:
    value = payload.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) < minimum:
        raise VietnameseLabelCorrectionError(f"invalid label-correction threshold: {name}")
    return float(value)


def load_vietnamese_label_correction_config(
    path: Path,
) -> VietnameseLabelCorrectionConfig:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, yaml.YAMLError) as exc:
        raise VietnameseLabelCorrectionError(
            f"cannot read label-correction config: {path}"
        ) from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise VietnameseLabelCorrectionError("Vietnamese label-correction config must be version 1")
    if payload.get("algorithm") != "STATEMENT_SCOPED_VIETNAMESE_LABEL_CORRECTION_PROPOSAL_V1":
        raise VietnameseLabelCorrectionError("unexpected Vietnamese label-correction algorithm")
    vocabulary = payload.get("vocabulary")
    gates = payload.get("candidate_gates")
    safety = payload.get("safety")
    if not isinstance(vocabulary, dict) or not isinstance(gates, dict):
        raise VietnameseLabelCorrectionError("label-correction configuration is incomplete")
    required_vocabulary = {
        "source": "APPEND_ONLY_REPORT_TEMPLATE_NAMES",
        "require_same_statement_type": True,
        "require_cross_row_document_support_for_phrases": True,
    }
    if any(vocabulary.get(name) != value for name, value in required_vocabulary.items()):
        raise VietnameseLabelCorrectionError("label-correction vocabulary safety contract drifted")
    if not isinstance(safety, dict) or not safety or any(bool(value) for value in safety.values()):
        raise VietnameseLabelCorrectionError("label correction grants forbidden authority")
    protected_function_keys = vocabulary.get("protected_function_keys")
    if not isinstance(protected_function_keys, list) or not protected_function_keys:
        raise VietnameseLabelCorrectionError("protected_function_keys must be a non-empty list")
    normalized_protected_keys = tuple(
        dict.fromkeys(retrieval_key(str(value)) for value in protected_function_keys)
    )
    if any(not value or " " in value for value in normalized_protected_keys):
        raise VietnameseLabelCorrectionError("protected function keys must be single tokens")
    maximum_distance = gates.get("maximum_damerau_distance")
    if not isinstance(maximum_distance, int) or isinstance(maximum_distance, bool):
        raise VietnameseLabelCorrectionError("maximum_damerau_distance must be an integer")
    if maximum_distance < 0:
        raise VietnameseLabelCorrectionError("maximum_damerau_distance must not be negative")
    return VietnameseLabelCorrectionConfig(
        maximum_phrase_tokens=_positive_integer(vocabulary, "maximum_phrase_tokens"),
        minimum_document_support=_positive_integer(vocabulary, "minimum_document_support"),
        minimum_document_support_ratio=_minimum_float(
            vocabulary, "minimum_document_support_ratio", 1.0
        ),
        protected_function_keys=normalized_protected_keys,
        maximum_damerau_distance=maximum_distance,
        minimum_full_label_similarity=_bounded_float(gates, "minimum_full_label_similarity"),
        minimum_full_label_runner_up_margin=_bounded_float(
            gates, "minimum_full_label_runner_up_margin"
        ),
        minimum_phrase_similarity=_bounded_float(gates, "minimum_phrase_similarity"),
        minimum_acronym_similarity=_bounded_float(gates, "minimum_acronym_similarity"),
        minimum_phrase_runner_up_margin=_bounded_float(gates, "minimum_phrase_runner_up_margin"),
        minimum_acronym_characters=_positive_integer(gates, "minimum_acronym_characters"),
        maximum_replacements_per_label=_positive_integer(gates, "maximum_replacements_per_label"),
    )


def vocabulary_labels_from_schema_items(items: Iterable[Any]) -> tuple[VocabularyLabel, ...]:
    labels = []
    for item in items:
        statement_type = str(item.statement_type)
        canonical_name = normalize_text(str(item.canonical_name))
        schema_id = int(item.schema_id)
        if canonical_name:
            labels.append(
                VocabularyLabel(
                    statement_type=statement_type,
                    label=canonical_name,
                    source_id=f"ReportNormId:{schema_id}",
                )
            )
    return tuple(labels)


def _tokens(value: str) -> tuple[_Token, ...]:
    return tuple(
        _Token(
            text=match.group(0),
            start=match.start(),
            end=match.end(),
            key=retrieval_key(match.group(0)),
        )
        for match in _TOKEN.finditer(value)
        if retrieval_key(match.group(0))
    )


def _surface_for_source(candidate: str, source: str) -> str:
    source_letters = "".join(char for char in source if char.isalpha())
    if source_letters and source_letters.isupper():
        return candidate.upper()
    return candidate


def _candidate_inventory(
    vocabulary: tuple[VocabularyLabel, ...],
    maximum_phrase_tokens: int,
) -> tuple[
    dict[str, tuple[_VocabularyCandidate, ...]],
    dict[tuple[str, int], tuple[_VocabularyCandidate, ...]],
]:
    full_raw: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    phrase_raw: dict[tuple[str, int, str, str], set[str]] = defaultdict(set)
    for item in vocabulary:
        label = normalize_text(item.label)
        key = retrieval_key(label)
        if not label or not key:
            continue
        full_raw[(item.statement_type, key, label)].add(item.source_id)
        label_tokens = _tokens(label)
        for width in range(1, min(maximum_phrase_tokens, len(label_tokens)) + 1):
            for start in range(0, len(label_tokens) - width + 1):
                selected = label_tokens[start : start + width]
                surface = " ".join(token.text for token in selected)
                phrase_key = " ".join(token.key for token in selected)
                phrase_raw[(item.statement_type, width, phrase_key, surface)].add(item.source_id)

    full: dict[str, list[_VocabularyCandidate]] = defaultdict(list)
    for (statement, key, surface), source_ids in full_raw.items():
        full[statement].append(
            _VocabularyCandidate(key, surface, tuple(sorted(source_ids)), len(_tokens(surface)))
        )
    phrases: dict[tuple[str, int], list[_VocabularyCandidate]] = defaultdict(list)
    for (statement, width, key, surface), source_ids in phrase_raw.items():
        phrases[(statement, width)].append(
            _VocabularyCandidate(key, surface, tuple(sorted(source_ids)), width)
        )
    return (
        {
            key: tuple(sorted(value, key=lambda item: (item.key, item.surface)))
            for key, value in full.items()
        },
        {
            key: tuple(sorted(value, key=lambda item: (item.key, item.surface)))
            for key, value in phrases.items()
        },
    )


def _deduplicate_candidate_keys(
    candidates: Iterable[_VocabularyCandidate],
) -> tuple[_VocabularyCandidate, ...]:
    grouped: dict[str, list[_VocabularyCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.key].append(candidate)
    result = []
    for key, variants in grouped.items():
        surfaces = {normalize_text(item.surface) for item in variants}
        casefolded_surfaces = {surface.casefold() for surface in surfaces}
        if len(casefolded_surfaces) != 1:
            # A retrieval key with competing Vietnamese surfaces is not safe to restore.
            continue
        surface = min(surfaces, key=lambda value: (not value.islower(), value))
        result.append(
            _VocabularyCandidate(
                key=key,
                surface=surface,
                source_ids=tuple(
                    sorted({source for item in variants for source in item.source_ids})
                ),
                token_count=variants[0].token_count,
            )
        )
    return tuple(result)


def _document_phrase_support(
    rows: tuple[OrderedObservedLabel, ...],
    maximum_phrase_tokens: int,
) -> tuple[Counter[tuple[str, ...]], tuple[Counter[tuple[str, ...]], ...]]:
    document_counter: Counter[tuple[str, ...]] = Counter()
    row_counters = []
    for row in rows:
        keys = tuple(token.key for token in _tokens(row.raw_label))
        row_counter: Counter[tuple[str, ...]] = Counter()
        for width in range(1, min(maximum_phrase_tokens, len(keys)) + 1):
            for start in range(0, len(keys) - width + 1):
                row_counter[keys[start : start + width]] += 1
        row_counters.append(row_counter)
        document_counter.update(row_counter)
    return document_counter, tuple(row_counters)


def _best_full_label_replacement(
    raw_label: str,
    statement_type: str,
    inventory: dict[str, tuple[_VocabularyCandidate, ...]],
    config: VietnameseLabelCorrectionConfig,
) -> _AcceptedReplacement | None:
    source_key = retrieval_key(raw_label)
    if not source_key:
        return None
    scoped_candidates = _deduplicate_candidate_keys(inventory.get(statement_type, ()))
    if source_key in {candidate.key for candidate in scoped_candidates}:
        return None
    ranked = []
    for candidate in scoped_candidates:
        if candidate.key == source_key:
            continue
        distance = DamerauLevenshtein.distance(source_key, candidate.key)
        similarity = DamerauLevenshtein.normalized_similarity(source_key, candidate.key)
        ranked.append((similarity, -distance, candidate.key, candidate))
    ranked.sort(reverse=True)
    if not ranked:
        return None
    similarity, negative_distance, _key, candidate = ranked[0]
    runner_up_similarity = ranked[1][0] if len(ranked) > 1 else None
    margin = similarity - runner_up_similarity if runner_up_similarity is not None else None
    distance = -negative_distance
    if (
        distance > config.maximum_damerau_distance
        or similarity < config.minimum_full_label_similarity
        or (margin is not None and margin < config.minimum_full_label_runner_up_margin)
    ):
        return None
    proposed = _surface_for_source(candidate.surface, raw_label)
    token_count = len(_tokens(raw_label))
    return _AcceptedReplacement(
        start_token=0,
        end_token_exclusive=token_count,
        char_start=0,
        char_end=len(raw_label),
        evidence=LabelReplacementEvidence(
            start_token=0,
            end_token_exclusive=token_count,
            source_text=raw_label,
            proposed_text=proposed,
            source_key=source_key,
            candidate_key=candidate.key,
            vocabulary_source_ids=candidate.source_ids,
            candidate_kind="SCHEMA_FULL_LABEL",
            damerau_distance=distance,
            similarity=round(similarity, 6),
            runner_up_similarity=(
                round(runner_up_similarity, 6) if runner_up_similarity is not None else None
            ),
            score_margin=round(margin, 6) if margin is not None else None,
            document_support_count=0,
            source_document_support_count=0,
            document_support_ratio=0.0,
        ),
    )


def _phrase_replacements(
    row: OrderedObservedLabel,
    document_support: Counter[tuple[str, ...]],
    current_row_support: Counter[tuple[str, ...]],
    inventory: dict[tuple[str, int], tuple[_VocabularyCandidate, ...]],
    config: VietnameseLabelCorrectionConfig,
) -> tuple[_AcceptedReplacement, ...]:
    tokens = _tokens(row.raw_label)
    accepted = []
    for width in range(1, min(config.maximum_phrase_tokens, len(tokens)) + 1):
        candidates = _deduplicate_candidate_keys(inventory.get((row.statement_type, width), ()))
        for start in range(0, len(tokens) - width + 1):
            selected = tokens[start : start + width]
            source_key = " ".join(token.key for token in selected)
            source_text = row.raw_label[selected[0].start : selected[-1].end]
            acronym = (
                width == 1
                and len(source_text) >= config.minimum_acronym_characters
                and source_text.isupper()
            )
            if width == 1 and not acronym:
                continue
            if source_key in {candidate.key for candidate in candidates}:
                # The observed phrase is itself valid in the statement vocabulary.
                continue
            source_tokens = tuple(source_key.split())
            source_support_count = (
                document_support[source_tokens] - current_row_support[source_tokens]
            )
            ranked = []
            for candidate in candidates:
                if candidate.key == source_key:
                    continue
                proposed_surface = _surface_for_source(candidate.surface, source_text)
                if acronym and re.fullmatch(r"[A-Z0-9Đ]+", candidate.surface) is None:
                    continue
                candidate_tokens = tuple(candidate.key.split())
                if any(
                    source != proposed
                    and (
                        source in config.protected_function_keys
                        or proposed in config.protected_function_keys
                    )
                    for source, proposed in zip(source_tokens, candidate_tokens, strict=True)
                ):
                    continue
                support_count = (
                    document_support[candidate_tokens] - current_row_support[candidate_tokens]
                )
                support_ratio = support_count / max(1, source_support_count)
                if (
                    support_count < config.minimum_document_support
                    or support_ratio < config.minimum_document_support_ratio
                ):
                    continue
                distance = DamerauLevenshtein.distance(source_key, candidate.key)
                similarity = DamerauLevenshtein.normalized_similarity(source_key, candidate.key)
                minimum_similarity = (
                    config.minimum_acronym_similarity
                    if acronym
                    else config.minimum_phrase_similarity
                )
                if distance <= config.maximum_damerau_distance and similarity >= minimum_similarity:
                    ranked.append(
                        (
                            similarity,
                            -distance,
                            candidate.key,
                            candidate,
                            proposed_surface,
                            support_count,
                            support_ratio,
                        )
                    )
            ranked.sort(reverse=True)
            if not ranked:
                continue
            best = ranked[0]
            runner_up_similarity = ranked[1][0] if len(ranked) > 1 else None
            margin = best[0] - runner_up_similarity if runner_up_similarity is not None else None
            if margin is not None and margin < config.minimum_phrase_runner_up_margin:
                continue
            candidate = best[3]
            accepted.append(
                _AcceptedReplacement(
                    start_token=start,
                    end_token_exclusive=start + width,
                    char_start=selected[0].start,
                    char_end=selected[-1].end,
                    evidence=LabelReplacementEvidence(
                        start_token=start,
                        end_token_exclusive=start + width,
                        source_text=source_text,
                        proposed_text=best[4],
                        source_key=source_key,
                        candidate_key=candidate.key,
                        vocabulary_source_ids=candidate.source_ids,
                        candidate_kind=(
                            "SCHEMA_ACRONYM_WITH_DOCUMENT_SUPPORT"
                            if acronym
                            else "SCHEMA_PHRASE_WITH_DOCUMENT_SUPPORT"
                        ),
                        damerau_distance=-best[1],
                        similarity=round(best[0], 6),
                        runner_up_similarity=(
                            round(runner_up_similarity, 6)
                            if runner_up_similarity is not None
                            else None
                        ),
                        score_margin=round(margin, 6) if margin is not None else None,
                        document_support_count=best[5],
                        source_document_support_count=source_support_count,
                        document_support_ratio=round(best[6], 6),
                    ),
                )
            )

    by_start: dict[int, list[_AcceptedReplacement]] = defaultdict(list)
    for candidate in accepted:
        by_start[candidate.start_token].append(candidate)
    for choices in by_start.values():
        choices.sort(
            key=lambda item: (
                item.end_token_exclusive - item.start_token,
                item.evidence.similarity,
                item.evidence.candidate_key,
            ),
            reverse=True,
        )

    @cache
    def choose(position: int) -> tuple[tuple[int, float, int], tuple[_AcceptedReplacement, ...]]:
        if position >= len(tokens):
            return (0, 0.0, 0), ()
        best_score, best_items = choose(position + 1)
        for candidate in by_start.get(position, ()):  # non-overlap is enforced by the jump
            tail_score, tail_items = choose(candidate.end_token_exclusive)
            width = candidate.end_token_exclusive - candidate.start_token
            score = (
                tail_score[0] + width,
                tail_score[1] + candidate.evidence.similarity,
                tail_score[2] - 1,
            )
            if score > best_score:
                best_score = score
                best_items = (candidate, *tail_items)
        return best_score, best_items

    _score, selected = choose(0)
    if len(selected) > config.maximum_replacements_per_label:
        return ()
    return tuple(sorted(selected, key=lambda item: item.char_start))


def _apply_replacements(raw_label: str, replacements: tuple[_AcceptedReplacement, ...]) -> str:
    corrected = raw_label
    for item in reversed(replacements):
        corrected = (
            corrected[: item.char_start] + item.evidence.proposed_text + corrected[item.char_end :]
        )
    return corrected


def propose_vietnamese_label_corrections(
    rows: Iterable[OrderedObservedLabel],
    vocabulary: Iterable[VocabularyLabel],
    config: VietnameseLabelCorrectionConfig,
) -> VietnameseLabelCorrectionResult:
    ordered_rows = tuple(rows)
    vocabulary_items = tuple(vocabulary)
    row_ids = [row.row_id for row in ordered_rows]
    if len(row_ids) != len(set(row_ids)):
        raise VietnameseLabelCorrectionError("ordered observed labels contain duplicate row IDs")
    full_inventory, phrase_inventory = _candidate_inventory(
        vocabulary_items, config.maximum_phrase_tokens
    )
    document_support, row_supports = _document_phrase_support(
        ordered_rows, config.maximum_phrase_tokens
    )
    proposals = []
    for index, row in enumerate(ordered_rows):
        full = _best_full_label_replacement(
            row.raw_label,
            row.statement_type,
            full_inventory,
            config,
        )
        replacements = (
            (full,)
            if full is not None
            else _phrase_replacements(
                row,
                document_support,
                row_supports[index],
                phrase_inventory,
                config,
            )
        )
        corrected = _apply_replacements(row.raw_label, replacements)
        proposals.append(
            VietnameseLabelCorrectionProposal(
                row_id=row.row_id,
                row_position=index,
                statement_type=row.statement_type,
                raw_label=row.raw_label,
                corrected_label=corrected,
                previous_raw_label=ordered_rows[index - 1].raw_label if index else None,
                next_raw_label=(
                    ordered_rows[index + 1].raw_label if index + 1 < len(ordered_rows) else None
                ),
                status=(
                    "PROPOSED_CORRECTION" if replacements else "UNCHANGED_NO_DECISIVE_CANDIDATE"
                ),
                replacements=tuple(item.evidence for item in replacements),
                raw_label_preserved=True,
                row_order_preserved=True,
                automatic_output_authority=False,
                automatic_schema_mapping_authority=False,
            )
        )
    corrected_count = sum(bool(item.replacements) for item in proposals)
    return VietnameseLabelCorrectionResult(
        status="LABEL_CORRECTION_PROPOSALS_COMPLETE",
        proposals=tuple(proposals),
        corrected_count=corrected_count,
        unchanged_count=len(proposals) - corrected_count,
        raw_labels_preserved=True,
        row_order_preserved=True,
        numeric_or_note_fields_present=False,
        automatic_output_authority=False,
        automatic_schema_mapping_authority=False,
    )


def vietnamese_label_correction_to_dict(
    result: VietnameseLabelCorrectionResult,
) -> dict[str, Any]:
    return asdict(result)
