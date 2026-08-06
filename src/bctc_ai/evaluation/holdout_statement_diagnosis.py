from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import fitz
import yaml

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.core.text import retrieval_key
from bctc_ai.document_phase.statement_locator import (
    OCRLine,
    OCRPage,
    load_statement_locator_config,
    locate_statement_pages,
)
from bctc_ai.evaluation.page_pairing import (
    align_pdf_pages,
    pairing_config_from_dict,
)
from bctc_ai.ocr.pdf_text import PDFTextPage, extract_pdf_text


class HoldoutStatementDiagnosisError(RuntimeError):
    pass


@dataclass(frozen=True)
class NativeLine:
    text: str
    key: str
    bbox: tuple[float, float, float, float]


_FORM_CODE = re.compile(r"\bb0?([234])([a-z]?)\s+tctd(?:\s+hn)?\b")


def _git(project_root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=check,
        capture_output=True,
        text=False,
    )


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HoldoutStatementDiagnosisError(f"cannot read JSON artifact: {path}") from exc
    if not isinstance(payload, dict):
        raise HoldoutStatementDiagnosisError(f"JSON artifact is not an object: {path}")
    return payload


def _load_config(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise HoldoutStatementDiagnosisError(f"cannot read diagnosis config: {path}") from exc
    required = {
        "version": 1,
        "experiment_id": "E-0022",
        "phase": "POST_ROLE_B_SEAL_ROLE_A_PAGE_SCOPE_DIAGNOSIS",
        "dataset_role": "UNTOUCHED_HOLDOUT",
        "created_after_role_a_access": True,
        "eligible_for_holdout_retuning": False,
    }
    if not isinstance(payload, dict) or any(
        payload.get(key) != value for key, value in required.items()
    ):
        raise HoldoutStatementDiagnosisError("Role A diagnosis identity/policy drifted")
    for section in (
        "upstream_role_b_seal",
        "sources",
        "native_page_reference",
        "visual_pairing",
        "frozen_diagnostic_components",
        "outputs",
    ):
        if not isinstance(payload.get(section), dict):
            raise HoldoutStatementDiagnosisError(f"Role A diagnosis section is absent: {section}")
    return payload


def _safe_path(project_root: Path, value: str) -> Path:
    path = (project_root / value).resolve()
    try:
        path.relative_to(project_root)
    except ValueError as exc:
        raise HoldoutStatementDiagnosisError(f"path escapes project root: {value}") from exc
    return path


def _relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError as exc:
        raise HoldoutStatementDiagnosisError(f"artifact escapes project root: {path}") from exc


def _git_file_sha256(project_root: Path, commit: str, relative_path: str) -> str:
    result = _git(project_root, "show", f"{commit}:{relative_path}", check=False)
    if result.returncode != 0:
        raise HoldoutStatementDiagnosisError(
            f"frozen diagnostic file is absent: {commit}:{relative_path}"
        )
    return hashlib.sha256(result.stdout).hexdigest()


def _verify_frozen_components(project_root: Path, config: dict[str, Any]) -> dict[str, str]:
    frozen = config["frozen_diagnostic_components"]
    commit = str(frozen.get("git_commit", ""))
    files = frozen.get("files")
    if not commit or not isinstance(files, dict) or not files:
        raise HoldoutStatementDiagnosisError("frozen diagnostic components are incomplete")
    verified = {}
    for relative_path, raw_digest in files.items():
        relative = str(relative_path)
        digest = str(raw_digest)
        path = _safe_path(project_root, relative)
        if not path.is_file() or sha256_file(path) != digest:
            raise HoldoutStatementDiagnosisError(
                f"diagnostic component drifted locally: {relative}"
            )
        if _git_file_sha256(project_root, commit, relative) != digest:
            raise HoldoutStatementDiagnosisError(
                f"diagnostic component drifted at freeze: {relative}"
            )
        verified[relative] = digest
    return dict(sorted(verified.items()))


def _verify_source(project_root: Path, record: dict[str, Any]) -> Path:
    path = _safe_path(project_root, str(record.get("path", "")))
    digest = str(record.get("sha256", ""))
    size = int(record.get("size_bytes", -1))
    page_count = int(record.get("expected_page_count", -1))
    if not path.is_file() or path.stat().st_size != size or sha256_file(path) != digest:
        raise HoldoutStatementDiagnosisError(f"diagnostic source is absent or drifted: {path}")
    with fitz.open(path) as document:
        if document.page_count != page_count:
            raise HoldoutStatementDiagnosisError(f"diagnostic source page count drifted: {path}")
    return path


def _native_lines(page: PDFTextPage) -> tuple[NativeLine, ...]:
    grouped: dict[tuple[int, int], list[Any]] = {}
    for word in page.words:
        grouped.setdefault((word.block_number, word.line_number), []).append(word)
    lines = []
    for words in grouped.values():
        ordered = sorted(words, key=lambda word: (word.word_number, word.bbox_points.x0))
        text = " ".join(word.raw_text for word in ordered)
        lines.append(
            NativeLine(
                text=text,
                key=retrieval_key(text),
                bbox=(
                    min(word.bbox_points.x0 for word in ordered),
                    min(word.bbox_points.y0 for word in ordered),
                    max(word.bbox_points.x1 for word in ordered),
                    max(word.bbox_points.y1 for word in ordered),
                ),
            )
        )
    return tuple(sorted(lines, key=lambda line: (line.bbox[1], line.bbox[0], line.text)))


def _match_evidence(lines: tuple[NativeLine, ...], cores: list[str]) -> list[dict[str, Any]]:
    normalized = [(core, retrieval_key(core)) for core in cores]
    return [
        {
            "text": line.text,
            "retrieval_key": line.key,
            "bbox": list(line.bbox),
            "matched_core": core,
        }
        for line in lines
        for core, core_key in normalized
        if core_key and core_key in line.key
    ]


def _form_evidence(lines: tuple[NativeLine, ...]) -> dict[str, Any] | None:
    for line in lines:
        match = _FORM_CODE.search(line.key)
        if match:
            number, suffix = match.groups()
            return {
                "text": line.text,
                "retrieval_key": line.key,
                "normalized_family": f"B0{number}",
                "suffix": suffix or None,
            }
    return None


def _classify_native_page(
    page: PDFTextPage,
    lines: tuple[NativeLine, ...],
    policy: dict[str, Any],
) -> dict[str, Any]:
    title_cores = policy.get("title_cores")
    if not isinstance(title_cores, dict):
        raise HoldoutStatementDiagnosisError("native reference title cores are incomplete")
    title_evidence = {
        statement_type: _match_evidence(lines, list(cores))
        for statement_type, cores in title_cores.items()
    }
    main_hits = [kind for kind in ("CDKT", "KQKD", "LCTT") if title_evidence.get(kind)]
    toc_evidence = _match_evidence(lines, list(policy.get("table_of_contents_cores", [])))
    if toc_evidence or len(main_hits) >= 2:
        page_type = "TABLE_OF_CONTENTS"
    else:
        all_hits = [kind for kind in ("CDKT", "KQKD", "LCTT", "TM") if title_evidence.get(kind)]
        page_type = all_hits[0] if len(all_hits) == 1 else ("AMBIGUOUS" if all_hits else "OTHER")
    off_balance = _match_evidence(lines, list(policy.get("off_balance_cores", [])))
    if page_type in {"CDKT", "KQKD", "LCTT"}:
        scope = "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE" if off_balance else "MAIN_STATEMENT"
    else:
        scope = "NOT_APPLICABLE"
    method_evidence = {
        method: _match_evidence(lines, list(cores))
        for method, cores in policy.get("cash_flow_method_cores", {}).items()
    }
    method_hits = [method for method, evidence in method_evidence.items() if evidence]
    if len(method_hits) > 1:
        raise HoldoutStatementDiagnosisError(
            f"native cash-flow method is ambiguous on page {page.page}"
        )
    return {
        "page": page.page,
        "page_type": page_type,
        "scope": scope,
        "line_count": len(lines),
        "source_text_quality": page.text_quality,
        "source_corruption_markers": list(page.corruption_markers),
        "title_evidence": title_evidence,
        "off_balance_evidence": off_balance,
        "cash_flow_method": method_hits[0] if method_hits else None,
        "cash_flow_method_evidence": method_evidence,
        "form": _form_evidence(lines),
    }


def _validate_reference_sequence(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    main = [decision for decision in decisions if decision["scope"] == "MAIN_STATEMENT"]
    collapsed = []
    for decision in main:
        if not collapsed or collapsed[-1] != decision["page_type"]:
            collapsed.append(decision["page_type"])
    if collapsed != ["CDKT", "KQKD", "LCTT"]:
        raise HoldoutStatementDiagnosisError(
            f"native main-statement order is not CDKT->KQKD->LCTT: {collapsed}"
        )
    lctt = [decision for decision in main if decision["page_type"] == "LCTT"]
    if not lctt or any(decision["cash_flow_method"] != "DIRECT" for decision in lctt):
        raise HoldoutStatementDiagnosisError("native LCTT method is not consistently DIRECT")
    return main


def _native_locator_pages(
    pages: list[PDFTextPage],
    lines_by_page: dict[int, tuple[NativeLine, ...]],
) -> tuple[OCRPage, ...]:
    return tuple(
        OCRPage(
            page=page.page,
            width=max(1, round(page.width_points)),
            height=max(1, round(page.height_points)),
            lines=tuple(
                OCRLine(text=line.text, bbox=line.bbox, score=1.0)
                for line in lines_by_page[page.page]
            ),
        )
        for page in pages
    )


def _role_b_title_text(
    project_root: Path,
    role_b_seal: dict[str, Any],
    candidate_page: int,
) -> str | None:
    validation = role_b_seal["validation"]
    batch_root = _safe_path(project_root, str(validation["batch_root"]))
    result_path = batch_root / f"ppocrv6-page-{candidate_page:04d}" / "ocr_result.json"
    record_by_path = {record["path"]: record for record in role_b_seal["artifact_records"]}
    relative = _relative(project_root, result_path)
    record = record_by_path.get(relative)
    if not isinstance(record, dict) or sha256_file(result_path) != record.get("sha256"):
        raise HoldoutStatementDiagnosisError(f"sealed Role B OCR page drifted: {candidate_page}")
    payload = _load_json(result_path)
    texts = payload.get("rec_texts")
    if not isinstance(texts, list):
        raise HoldoutStatementDiagnosisError(f"sealed Role B OCR text is invalid: {candidate_page}")
    matches = [text for text in texts if isinstance(text, str) and "bao cao" in retrieval_key(text)]
    return matches[0] if matches else None


def build_e0022_statement_diagnosis(
    project_root: Path,
    *,
    config_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    project_root = project_root.resolve()
    config_path = config_path if config_path.is_absolute() else project_root / config_path
    config_path = config_path.resolve()
    config = _load_config(config_path)
    frozen_files = _verify_frozen_components(project_root, config)

    upstream = config["upstream_role_b_seal"]
    role_b_seal_path = _safe_path(project_root, str(upstream.get("path", "")))
    if sha256_file(role_b_seal_path) != upstream.get("sha256"):
        raise HoldoutStatementDiagnosisError("upstream unresolved Role B seal hash drifted")
    role_b_seal = _load_json(role_b_seal_path)
    if role_b_seal.get("state") != upstream.get("required_state"):
        raise HoldoutStatementDiagnosisError("upstream Role B state drifted")
    if role_b_seal.get("allowed_next_action") != (
        "HYDRATE_ROLE_A_AND_BUILD_MACHINE_REFERENCE_FOR_ONE_SHOT_DIAGNOSIS"
    ):
        raise HoldoutStatementDiagnosisError(
            "upstream Role B seal does not permit Role A diagnosis"
        )

    sources = config["sources"]
    role_a_path = _verify_source(project_root, sources["role_a"])
    role_b_path = _verify_source(project_root, sources["role_b"])
    pages = extract_pdf_text(role_a_path)
    if len(pages) != 33 or any(not page.words for page in pages):
        raise HoldoutStatementDiagnosisError("Role A native text does not cover all 33 pages")
    policy = config["native_page_reference"]
    full_text = " ".join(word.raw_text for page in pages for word in page.words)
    forbidden_sequences = {
        sequence: full_text.count(sequence) for sequence in policy["actual_mojibake_sequences"]
    }
    if any(forbidden_sequences.values()):
        raise HoldoutStatementDiagnosisError(
            f"Role A contains actual mojibake/replacement sequences: {forbidden_sequences}"
        )
    unicode_letter_tokens = {
        marker: sorted(
            {word.raw_text for page in pages for word in page.words if marker in word.raw_text}
        )
        for marker in policy["unicode_letters_not_sufficient_for_corruption"]
    }
    lines_by_page = {page.page: _native_lines(page) for page in pages}
    decisions = [_classify_native_page(page, lines_by_page[page.page], policy) for page in pages]
    main_decisions = _validate_reference_sequence(decisions)

    visual = dict(config["visual_pairing"])
    if visual.pop("uses_text_or_values", None) is not False:
        raise HoldoutStatementDiagnosisError("visual pairing evidence policy drifted")
    pairing_config = pairing_config_from_dict(visual)
    alignment = align_pdf_pages(role_a_path, role_b_path, pairing_config)
    accepted_by_reference = {
        step.reference_page: step for step in alignment.accepted if step.reference_page is not None
    }
    target_pairs = []
    for decision in main_decisions:
        step = accepted_by_reference.get(int(decision["page"]))
        if step is None or step.candidate_page is None:
            raise HoldoutStatementDiagnosisError(
                f"main statement page lacks accepted visual pairing: {decision['page']}"
            )
        target_pairs.append(
            {
                "reference_page": decision["page"],
                "candidate_page": step.candidate_page,
                "statement_type": decision["page_type"],
                "expected_scope": "MAIN_STATEMENT",
                "cash_flow_method": decision["cash_flow_method"],
                "visual_similarity": step.similarity,
                "visual_runner_up_margin": step.runner_up_margin,
                "visual_sequence_supported": step.sequence_supported,
            }
        )

    locator_config_path = project_root / "config/document_phase/statement-locator-v1.yaml"
    locator_config = load_statement_locator_config(locator_config_path)
    native_locator = locate_statement_pages(
        _native_locator_pages(pages, lines_by_page), locator_config
    )
    reference = {
        "format_version": 1,
        "experiment_id": "E-0022",
        "state": "ROLE_A_STATEMENT_PAGE_REFERENCE_COMPLETE",
        "reference_kind": "POST_ROLE_B_SEAL_NATIVE_PAGE_SCOPE_MACHINE_REFERENCE",
        "dataset_role": "UNTOUCHED_HOLDOUT",
        "source": {
            "path": _relative(project_root, role_a_path),
            "sha256": sha256_file(role_a_path),
            "size_bytes": role_a_path.stat().st_size,
            "page_count": len(pages),
            "native_text_page_count": sum(bool(page.words) for page in pages),
        },
        "upstream_role_b_seal": {
            "path": _relative(project_root, role_b_seal_path),
            "sha256": sha256_file(role_b_seal_path),
            "state": role_b_seal["state"],
        },
        "configuration": {
            "path": _relative(project_root, config_path),
            "sha256": sha256_file(config_path),
        },
        "native_text_quality_audit": {
            "parser_reported_corrupt_pages": sum(
                page.text_quality == "CORRUPT_TEXT_LAYER" for page in pages
            ),
            "actual_mojibake_sequence_counts": forbidden_sequences,
            "valid_vietnamese_marker_tokens": unicode_letter_tokens,
            "policy": (
                "Standalone Unicode Vietnamese letters Â/Ã do not establish mojibake; "
                "replacement/encoded-byte sequences remain forbidden."
            ),
        },
        "page_decisions": decisions,
        "main_statement_pages": [decision["page"] for decision in main_decisions],
        "off_balance_pages": [
            decision["page"]
            for decision in decisions
            if decision["scope"] == "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE"
        ],
        "target_pairs": target_pairs,
        "visual_pairing": {
            "uses_text_or_values": False,
            "config": asdict(pairing_config),
            "result": alignment.to_dict(),
        },
        "frozen_locator_on_exact_native_text": native_locator,
        "frozen_component_files_sha256": frozen_files,
        "eligible_for_holdout_retuning": False,
        "claim_boundary": config["claim_boundary"],
    }

    location_path = _safe_path(project_root, str(role_b_seal["validation"]["location_path"]))
    if sha256_file(location_path) != role_b_seal["validation"]["location_sha256"]:
        raise HoldoutStatementDiagnosisError("sealed Role B statement-location artifact drifted")
    role_b_location = _load_json(location_path)
    role_b_result = role_b_location.get("result")
    if not isinstance(role_b_result, dict) or role_b_result.get("status") != "UNRESOLVED":
        raise HoldoutStatementDiagnosisError("sealed Role B location is no longer unresolved")
    role_b_by_page = {
        int(decision["page"]): decision
        for decision in role_b_result["page_decisions"]
        if isinstance(decision, dict)
    }
    native_by_page = {
        int(decision["page"]): decision
        for decision in native_locator["page_decisions"]
        if isinstance(decision, dict)
    }
    threshold = float(locator_config["title_min_similarity"])
    page_comparisons = []
    for pair in target_pairs:
        statement_type = str(pair["statement_type"])
        candidate_page = int(pair["candidate_page"])
        reference_page = int(pair["reference_page"])
        role_b_decision = role_b_by_page[candidate_page]
        native_decision = native_by_page[reference_page]
        page_comparisons.append(
            {
                **pair,
                "reference_title": reference["page_decisions"][reference_page - 1][
                    "title_evidence"
                ][statement_type][0]["text"],
                "role_b_ocr_title": _role_b_title_text(project_root, role_b_seal, candidate_page),
                "role_b": {
                    "page_type": role_b_decision["page_type"],
                    "scope": role_b_decision["scope"],
                    "mapping_eligible": role_b_decision["mapping_eligible"],
                    "form_hits": role_b_decision["form_hits"],
                    "title_score": role_b_decision["title_scores"][statement_type],
                    "title_score_gap_to_gate": round(
                        threshold - float(role_b_decision["title_scores"][statement_type]), 6
                    ),
                },
                "frozen_locator_on_exact_native_text": {
                    "page_type": native_decision["page_type"],
                    "scope": native_decision["scope"],
                    "mapping_eligible": native_decision["mapping_eligible"],
                    "form_hits": native_decision["form_hits"],
                    "title_score": native_decision["title_scores"][statement_type],
                    "title_score_gap_to_gate": round(
                        threshold - float(native_decision["title_scores"][statement_type]), 6
                    ),
                },
                "reference_form": reference["page_decisions"][reference_page - 1]["form"],
            }
        )
    strict_role_b = [
        item
        for item in page_comparisons
        if item["role_b"]["page_type"] == item["statement_type"]
        and item["role_b"]["scope"] == "MAIN_STATEMENT"
        and item["role_b"]["mapping_eligible"] is True
    ]
    strict_native = [
        item
        for item in page_comparisons
        if item["frozen_locator_on_exact_native_text"]["page_type"] == item["statement_type"]
        and item["frozen_locator_on_exact_native_text"]["scope"] == "MAIN_STATEMENT"
        and item["frozen_locator_on_exact_native_text"]["mapping_eligible"] is True
    ]
    expected_count = len(page_comparisons)
    reference_counts = {
        statement_type: sum(item["statement_type"] == statement_type for item in page_comparisons)
        for statement_type in ("CDKT", "KQKD", "LCTT")
    }
    role_b_counts = {
        statement_type: sum(
            item["statement_type"] == statement_type
            and item["role_b"]["mapping_eligible"] is True
            and item["role_b"]["page_type"] == statement_type
            for item in page_comparisons
        )
        for statement_type in ("CDKT", "KQKD", "LCTT")
    }
    comparison = {
        "format_version": 1,
        "experiment_id": "E-0022",
        "state": "STATEMENT_DISCOVERY_COMPARISON_COMPLETE",
        "dataset_role": "UNTOUCHED_HOLDOUT",
        "role_b_was_sealed_before_role_a_access": True,
        "upstream_role_b_seal": reference["upstream_role_b_seal"],
        "role_b_location": {
            "path": _relative(project_root, location_path),
            "sha256": sha256_file(location_path),
            "state": role_b_location["state"],
        },
        "configuration": reference["configuration"],
        "page_comparisons": page_comparisons,
        "metrics": {
            "expected_main_statement_pages": expected_count,
            "role_b_correct_mapping_eligible_pages": len(strict_role_b),
            "role_b_main_statement_page_recall": len(strict_role_b) / expected_count,
            "role_b_mapping_eligible_false_positive_pages": sum(
                decision["mapping_eligible"]
                and int(decision["page"])
                not in {int(item["candidate_page"]) for item in page_comparisons}
                for decision in role_b_result["page_decisions"]
            ),
            "role_b_complete_ordered_block": role_b_result["candidate_count"] > 0,
            "frozen_locator_exact_native_correct_pages": len(strict_native),
            "frozen_locator_exact_native_page_recall": len(strict_native) / expected_count,
            "reference_expected_by_statement": reference_counts,
            "role_b_correct_by_statement": role_b_counts,
        },
        "root_cause": {
            "primary_class": "STATEMENT_DISCOVERY_HEADER_MATCHING",
            "exact_native_pages_missed_by_frozen_matcher": expected_count - len(strict_native),
            "pages_lost_only_after_ocr_title_degradation": len(strict_native) - len(strict_role_b),
            "target_pages_with_form_suffix_not_recognized_by_frozen_anchor": sum(
                bool(item["reference_form"] and item["reference_form"]["suffix"])
                and not item["frozen_locator_on_exact_native_text"]["form_hits"]
                for item in page_comparisons
            ),
            "native_pages_falsely_flagged_corrupt_by_unicode_letters": reference[
                "native_text_quality_audit"
            ]["parser_reported_corrupt_pages"],
            "interpretation": (
                "Long exact Vietnamese statement titles are penalized by whole-string ratio "
                "against shorter cores; form-family suffixes such as B02a are not normalized; "
                "OCR diacritic loss then pushes the remaining LCTT titles below the gate."
            ),
        },
        "threshold_or_page_selection_tuning_performed": False,
        "role_b_rerun_after_reference_access": False,
        "historical_reference_invoked": False,
        "mapping_invoked": False,
        "reference_classifier_metric_is_holdout_accuracy": False,
        "next_bounded_action": (
            "Develop Unicode-aware native-text quality and form/title containment changes on "
            "separate development/validation documents, then freeze before a new holdout."
        ),
        "claim_boundary": (
            "This one-shot comparison measures statement-page discovery only. The Role A "
            "classifier was built after Role B was sealed and is a diagnostic machine reference, "
            "not human gold or an accuracy estimate for that classifier."
        ),
    }
    return reference, comparison


def capture_e0022_statement_diagnosis(
    project_root: Path,
    *,
    config_path: Path,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    if _git(project_root, "status", "--porcelain").stdout.strip():
        raise HoldoutStatementDiagnosisError("formal Role A diagnosis requires a clean worktree")
    config = _load_config(
        config_path if config_path.is_absolute() else (project_root / config_path).resolve()
    )
    outputs = config["outputs"]
    reference_path = _safe_path(project_root, str(outputs["role_a_reference"]))
    comparison_path = _safe_path(project_root, str(outputs["comparison"]))
    if reference_path.exists() or comparison_path.exists():
        raise HoldoutStatementDiagnosisError("refusing to overwrite Role A diagnosis outputs")
    reference, comparison = build_e0022_statement_diagnosis(
        project_root,
        config_path=config_path,
    )
    capture_commit = _git(project_root, "rev-parse", "HEAD").stdout.decode().strip()
    implementation = Path(__file__).resolve()
    capture_record = {
        "capture_git_commit": capture_commit,
        "capture_git_dirty": False,
        "diagnosis_implementation": {
            "path": _relative(project_root, implementation),
            "sha256": sha256_file(implementation),
        },
    }
    reference.update(capture_record)
    atomic_write_json(reference_path, reference)
    comparison.update(
        capture_record,
        role_a_reference={
            "path": _relative(project_root, reference_path),
            "sha256": sha256_file(reference_path),
            "state": reference["state"],
        },
    )
    atomic_write_json(comparison_path, comparison)
    return {
        "reference_path": _relative(project_root, reference_path),
        "reference_sha256": sha256_file(reference_path),
        "comparison_path": _relative(project_root, comparison_path),
        "comparison_sha256": sha256_file(comparison_path),
        "metrics": comparison["metrics"],
        "root_cause": comparison["root_cause"],
    }
