from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.frozen_suite import (
    EvidenceItem,
    EvidenceKind,
    EvidenceStage,
    load_frozen_suite,
    validate_evidence_manifest,
)
from bctc_ai.evaluation.page_pairing import (
    align_pdf_pages,
    pairing_config_from_dict,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a hash-locked scan/searchable calibration fixture"
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/experiments/e0009-frozen-paired-calibration.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0009-frozen-paired-calibration.json"),
    )
    return parser.parse_args()


def _pdf_profile(path: Path) -> dict[str, object]:
    native_text_pages = 0
    image_only_pages = 0
    mixed_pages = 0
    with fitz.open(path) as document:
        for page in document:
            has_text = bool(page.get_text("words"))
            has_images = bool(page.get_images(full=True))
            native_text_pages += has_text
            image_only_pages += has_images and not has_text
            mixed_pages += has_images and has_text
        page_count = len(document)
    if native_text_pages == page_count and not mixed_pages:
        document_kind = "BORN_DIGITAL_OR_SEARCHABLE_VECTOR"
    elif image_only_pages == page_count:
        document_kind = "SCAN_IMAGE_ONLY"
    else:
        document_kind = "MIXED"
    return {
        "page_count": page_count,
        "native_text_pages": native_text_pages,
        "image_only_pages": image_only_pages,
        "mixed_pages": mixed_pages,
        "document_kind": document_kind,
    }


def _evidence_record(item: EvidenceItem) -> dict[str, object]:
    return {"kind": item.kind.value, "path": item.path, "sha256": item.sha256}


def main() -> int:
    args = _parse_args()
    project_root = args.project_root.resolve()
    config_path = (project_root / args.config).resolve()
    output_path = (project_root / args.output).resolve()
    suite = load_frozen_suite(project_root, config_path)
    reference = suite.source(str(suite.pairing["reference_fixture_id"]))
    candidate = suite.source(str(suite.pairing["candidate_fixture_id"]))
    reference_path = project_root / reference.path
    candidate_path = project_root / candidate.path

    pairing_config = pairing_config_from_dict(suite.pairing["visual_fingerprint"])
    pairing = align_pdf_pages(reference_path, candidate_path, pairing_config)
    accepted_by_reference = {
        step.reference_page: step
        for step in pairing.accepted
        if step.reference_page is not None
    }
    target_pages = [int(page) for page in suite.pairing["target_reference_pages"]]
    target_pairs = [accepted_by_reference.get(page) for page in target_pages]
    missing_target_pages = [
        page for page, step in zip(target_pages, target_pairs, strict=True) if step is None
    ]

    pair_registration_evidence = (
        EvidenceItem(EvidenceKind.ROLE_A_SOURCE_PDF, reference.path, reference.sha256),
        EvidenceItem(EvidenceKind.ROLE_B_SOURCE_PDF, candidate.path, candidate.sha256),
        EvidenceItem(
            EvidenceKind.CONFIG,
            config_path.relative_to(project_root).as_posix(),
            sha256_file(config_path),
        ),
    )
    role_a_evidence = (
        EvidenceItem(EvidenceKind.ROLE_A_SOURCE_PDF, reference.path, reference.sha256),
        EvidenceItem(EvidenceKind.CONFIG, "config/tables/geometry.yaml"),
    )
    role_b_evidence = (
        EvidenceItem(EvidenceKind.ROLE_B_SOURCE_PDF, candidate.path, candidate.sha256),
        EvidenceItem(EvidenceKind.CONFIG, "config/models/paddleocr-vl-1.6-transformers.yaml"),
        EvidenceItem(EvidenceKind.MODEL, "PaddleOCR-VL-1.6@pinned-revision"),
    )
    post_mapping_evidence = (
        EvidenceItem(EvidenceKind.ROLE_B_RESULT, "pipeline_results.jsonl"),
        EvidenceItem(
            EvidenceKind.HISTORICAL_WEAK_REFERENCE,
            "data/local/historical_weak_reference.duckdb",
        ),
    )
    for stage, evidence in (
        (EvidenceStage.PAIR_REGISTRATION, pair_registration_evidence),
        (EvidenceStage.ROLE_A_BUILD, role_a_evidence),
        (EvidenceStage.ROLE_B_READ, role_b_evidence),
        (EvidenceStage.ROLE_B_POST_MAPPING_VALIDATION, post_mapping_evidence),
    ):
        validate_evidence_manifest(stage, evidence)

    algorithm_paths = (
        Path("src/bctc_ai/evaluation/page_pairing.py"),
        Path("src/bctc_ai/evaluation/frozen_suite.py"),
        Path("scripts/experiments/build_paired_calibration_fixture.py"),
    )
    payload = {
        "experiment_id": suite.experiment_id,
        "suite_id": suite.suite_id,
        "status": (
            "PASS_FROZEN_PAIRING_FOUND"
            if not missing_target_pages
            else "FAIL_TARGET_PAGE_PAIRING"
        ),
        "claim_boundary": (
            "Page correspondence and evidence isolation only; this is not OCR, mapping, "
            "full-tuple, or production accuracy."
        ),
        "dataset_role": suite.dataset_role.value,
        "frozen_at": suite.frozen_at,
        "config": {
            "path": config_path.relative_to(project_root).as_posix(),
            "sha256": sha256_file(config_path),
        },
        "registries": {
            "sources_sha256": sha256_file(project_root / "data/registered/source_registry.jsonl"),
            "dataset_roles_sha256": sha256_file(
                project_root / "data/registered/dataset_roles.jsonl"
            ),
        },
        "sources": [
            {
                "fixture_id": source.fixture_id,
                "bank": source.bank,
                "fixture_role": source.fixture_role,
                "path": source.path,
                "sha256": source.sha256,
                "dataset_role": source.dataset_role.value,
                "profile": _pdf_profile(project_root / source.path),
            }
            for source in suite.sources
        ],
        "pairing": {
            "method": "ORDERED_DYNAMIC_PROGRAMMING_ON_PIXEL_FINGERPRINTS",
            "uses_text": False,
            "uses_values": False,
            "config": suite.pairing["visual_fingerprint"],
            "result": pairing.to_dict(),
            "target_reference_pages": target_pages,
            "target_pairs": [step.to_dict() if step is not None else None for step in target_pairs],
            "missing_target_pages": missing_target_pages,
            "target_content": suite.pairing["target_content"],
        },
        "evidence_isolation": {
            "policy": suite.evidence_policy,
            "validated_manifests": {
                EvidenceStage.PAIR_REGISTRATION.value: [
                    _evidence_record(item) for item in pair_registration_evidence
                ],
                EvidenceStage.ROLE_A_BUILD.value: [
                    _evidence_record(item) for item in role_a_evidence
                ],
                EvidenceStage.ROLE_B_READ.value: [
                    _evidence_record(item) for item in role_b_evidence
                ],
                EvidenceStage.ROLE_B_POST_MAPPING_VALIDATION.value: [
                    _evidence_record(item) for item in post_mapping_evidence
                ],
            },
        },
        "historical_weak_reference_policy": suite.historical_policy,
        "algorithm_files_sha256": {
            path.as_posix(): sha256_file(project_root / path) for path in algorithm_paths
        },
        "next_gate": (
            "Run Role A on searchable pages and Role B on paired scan pages independently, "
            "then compare only after Role B artifacts are sealed."
        ),
    }
    atomic_write_json(output_path, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "accepted_pairs": len(pairing.accepted),
                "target_pairs": len(target_pages) - len(missing_target_pages),
                "missing_target_pages": missing_target_pages,
            },
            sort_keys=True,
        )
    )
    return 0 if not missing_target_pages else 1


if __name__ == "__main__":
    raise SystemExit(main())

