from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.contracts import DatasetRole
from bctc_ai.core.hashing import sha256_file


class FrozenSuiteError(RuntimeError):
    pass


class EvidenceStage(StrEnum):
    PAIR_REGISTRATION = "PAIR_REGISTRATION"
    ROLE_A_BUILD = "ROLE_A_BUILD"
    ROLE_B_READ = "ROLE_B_READ"
    ROLE_B_MAPPING = "ROLE_B_MAPPING"
    ROLE_B_POST_MAPPING_VALIDATION = "ROLE_B_POST_MAPPING_VALIDATION"
    INDEPENDENT_GEOMETRY_READ = "INDEPENDENT_GEOMETRY_READ"
    INDEPENDENT_GEOMETRY_COMPARE = "INDEPENDENT_GEOMETRY_COMPARE"
    COMPARE = "COMPARE"


class EvidenceKind(StrEnum):
    ROLE_A_SOURCE_PDF = "ROLE_A_SOURCE_PDF"
    ROLE_B_SOURCE_PDF = "ROLE_B_SOURCE_PDF"
    SOURCE_RENDER = "SOURCE_RENDER"
    PREPROCESS_VARIANT = "PREPROCESS_VARIANT"
    OCR_OUTPUT = "OCR_OUTPUT"
    LAYOUT_OUTPUT = "LAYOUT_OUTPUT"
    SCHEMA = "SCHEMA"
    HIERARCHY = "HIERARCHY"
    CONFIG = "CONFIG"
    MODEL = "MODEL"
    HISTORICAL_WEAK_REFERENCE = "HISTORICAL_WEAK_REFERENCE"
    ROLE_A_RESULT = "ROLE_A_RESULT"
    ROLE_B_RESULT = "ROLE_B_RESULT"
    INDEPENDENT_GEOMETRY_RESULT = "INDEPENDENT_GEOMETRY_RESULT"


@dataclass(frozen=True)
class EvidenceItem:
    kind: EvidenceKind
    path: str
    sha256: str | None = None


_ALLOWED_EVIDENCE: dict[EvidenceStage, set[EvidenceKind]] = {
    EvidenceStage.PAIR_REGISTRATION: {
        EvidenceKind.ROLE_A_SOURCE_PDF,
        EvidenceKind.ROLE_B_SOURCE_PDF,
        EvidenceKind.CONFIG,
    },
    EvidenceStage.ROLE_A_BUILD: {
        EvidenceKind.ROLE_A_SOURCE_PDF,
        EvidenceKind.SOURCE_RENDER,
        EvidenceKind.PREPROCESS_VARIANT,
        EvidenceKind.OCR_OUTPUT,
        EvidenceKind.LAYOUT_OUTPUT,
        EvidenceKind.SCHEMA,
        EvidenceKind.HIERARCHY,
        EvidenceKind.CONFIG,
        EvidenceKind.MODEL,
        EvidenceKind.HISTORICAL_WEAK_REFERENCE,
    },
    EvidenceStage.ROLE_B_READ: {
        EvidenceKind.ROLE_B_SOURCE_PDF,
        EvidenceKind.SOURCE_RENDER,
        EvidenceKind.PREPROCESS_VARIANT,
        EvidenceKind.CONFIG,
        EvidenceKind.MODEL,
    },
    EvidenceStage.ROLE_B_MAPPING: {
        EvidenceKind.OCR_OUTPUT,
        EvidenceKind.LAYOUT_OUTPUT,
        EvidenceKind.SCHEMA,
        EvidenceKind.HIERARCHY,
        EvidenceKind.CONFIG,
        EvidenceKind.MODEL,
    },
    EvidenceStage.ROLE_B_POST_MAPPING_VALIDATION: {
        EvidenceKind.ROLE_B_RESULT,
        EvidenceKind.CONFIG,
        EvidenceKind.HISTORICAL_WEAK_REFERENCE,
    },
    EvidenceStage.INDEPENDENT_GEOMETRY_READ: {
        EvidenceKind.ROLE_B_SOURCE_PDF,
        EvidenceKind.SOURCE_RENDER,
        EvidenceKind.CONFIG,
        EvidenceKind.MODEL,
    },
    EvidenceStage.INDEPENDENT_GEOMETRY_COMPARE: {
        EvidenceKind.ROLE_A_RESULT,
        EvidenceKind.ROLE_B_RESULT,
        EvidenceKind.INDEPENDENT_GEOMETRY_RESULT,
        EvidenceKind.CONFIG,
    },
    EvidenceStage.COMPARE: {
        EvidenceKind.ROLE_A_RESULT,
        EvidenceKind.ROLE_B_RESULT,
        EvidenceKind.CONFIG,
    },
}


def validate_evidence_manifest(
    stage: EvidenceStage, items: tuple[EvidenceItem, ...]
) -> None:
    allowed = _ALLOWED_EVIDENCE[stage]
    forbidden = [item.kind.value for item in items if item.kind not in allowed]
    if forbidden:
        raise FrozenSuiteError(
            f"evidence kinds forbidden during {stage.value}: {sorted(set(forbidden))}"
        )
    if stage in {
        EvidenceStage.ROLE_B_READ,
        EvidenceStage.ROLE_B_MAPPING,
        EvidenceStage.ROLE_B_POST_MAPPING_VALIDATION,
        EvidenceStage.INDEPENDENT_GEOMETRY_READ,
    }:
        forbidden_tokens = ("machine_reference", "role_a_result", "pipeline_vs_reference")
        leaked = [
            item.path
            for item in items
            if any(token in item.path.casefold() for token in forbidden_tokens)
        ]
        if leaked:
            raise FrozenSuiteError(f"Role B evidence path leaks reference answers: {leaked}")


@dataclass(frozen=True)
class FrozenSource:
    fixture_id: str
    bank: str
    fixture_role: str
    path: str
    sha256: str
    dataset_role: DatasetRole


@dataclass(frozen=True)
class FrozenSuite:
    suite_id: str
    experiment_id: str
    dataset_role: DatasetRole
    frozen_at: str
    config_path: Path
    sources: tuple[FrozenSource, ...]
    pairing: dict[str, Any]
    evidence_policy: dict[str, Any]
    historical_policy: dict[str, Any]

    def source(self, fixture_id: str) -> FrozenSource:
        matches = [source for source in self.sources if source.fixture_id == fixture_id]
        if len(matches) != 1:
            raise FrozenSuiteError(f"expected one source for fixture_id {fixture_id!r}")
        return matches[0]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FrozenSuiteError(f"required registry is missing: {path}")
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    except json.JSONDecodeError as exc:
        raise FrozenSuiteError(f"invalid JSONL registry: {path}") from exc


def _parse_timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FrozenSuiteError(f"invalid {field} timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise FrozenSuiteError(f"{field} timestamp must include a timezone")
    return parsed


def _validate_historical_policy(policy: dict[str, Any]) -> None:
    required = {
        "lookup_stage": "POST_SCHEMA_RESOLUTION_ONLY",
        "lookup_requires_resolved_id": True,
        "mapping_candidate_generation": False,
        "pdf_confidence_promotion": False,
        "pdf_value_overwrite": False,
        "pdf_ytd_operand": False,
    }
    mismatches = {
        key: {"expected": expected, "actual": policy.get(key)}
        for key, expected in required.items()
        if policy.get(key) != expected
    }
    if mismatches:
        raise FrozenSuiteError(f"historical weak-reference policy is unsafe: {mismatches}")


def load_frozen_suite(project_root: Path, config_path: Path) -> FrozenSuite:
    project_root = project_root.resolve()
    config_path = config_path.resolve()
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise FrozenSuiteError("frozen suite config must be a version-1 mapping")
    if payload.get("content_inspected_before_role_assignment") is not False:
        raise FrozenSuiteError("suite cannot claim a pre-inspection freeze")
    try:
        dataset_role = DatasetRole(payload["dataset_role"])
    except (KeyError, ValueError) as exc:
        raise FrozenSuiteError("suite dataset_role is missing or invalid") from exc
    if dataset_role not in {
        DatasetRole.CALIBRATION,
        DatasetRole.VALIDATION,
        DatasetRole.UNTOUCHED_HOLDOUT,
    }:
        raise FrozenSuiteError("benchmark suites must use calibration, validation, or holdout")
    frozen_at = str(payload.get("frozen_at", ""))
    frozen_timestamp = _parse_timestamp(frozen_at, "frozen_at")
    source_registry = _read_jsonl(project_root / "data/registered/source_registry.jsonl")
    role_registry = _read_jsonl(project_root / "data/registered/dataset_roles.jsonl")
    source_by_path = {record["relative_path"]: record for record in source_registry}
    roles_by_document = {record["document_id"]: record for record in role_registry}

    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list) or len(raw_sources) < 2:
        raise FrozenSuiteError("suite must declare at least two frozen sources")
    sources: list[FrozenSource] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for raw_source in raw_sources:
        if not isinstance(raw_source, dict):
            raise FrozenSuiteError("every suite source must be a mapping")
        fixture_id = str(raw_source.get("fixture_id", ""))
        relative_path = str(raw_source.get("path", ""))
        digest = str(raw_source.get("sha256", ""))
        if not fixture_id or fixture_id in seen_ids:
            raise FrozenSuiteError(f"missing or duplicate fixture_id: {fixture_id!r}")
        if not relative_path or relative_path in seen_paths:
            raise FrozenSuiteError(f"missing or duplicate source path: {relative_path!r}")
        seen_ids.add(fixture_id)
        seen_paths.add(relative_path)
        path = (project_root / relative_path).resolve()
        try:
            path.relative_to(project_root)
        except ValueError as exc:
            raise FrozenSuiteError(f"source escapes project root: {relative_path}") from exc
        if not path.is_file() or sha256_file(path) != digest:
            raise FrozenSuiteError(f"source is absent or hash-drifted: {relative_path}")
        registered = source_by_path.get(relative_path)
        if registered is None or registered.get("sha256") != digest:
            raise FrozenSuiteError(f"source registry mismatch: {relative_path}")
        document_id = f"sha256:{digest}"
        role_record = roles_by_document.get(document_id)
        if role_record is None or role_record.get("dataset_role") != dataset_role.value:
            raise FrozenSuiteError(f"dataset role is not frozen for {relative_path}")
        if role_record.get("source_path") != relative_path:
            raise FrozenSuiteError(f"dataset-role source path mismatch: {relative_path}")
        assigned_at = _parse_timestamp(str(role_record.get("assigned_at", "")), "assigned_at")
        if assigned_at > frozen_timestamp:
            raise FrozenSuiteError(f"source role was assigned after suite freeze: {relative_path}")
        sources.append(
            FrozenSource(
                fixture_id=fixture_id,
                bank=str(raw_source.get("bank", "")),
                fixture_role=str(raw_source.get("fixture_role", "")),
                path=relative_path,
                sha256=digest,
                dataset_role=dataset_role,
            )
        )

    pairing = payload.get("pairing")
    if not isinstance(pairing, dict):
        raise FrozenSuiteError("pairing config is required")
    reference_id = str(pairing.get("reference_fixture_id", ""))
    candidate_id = str(pairing.get("candidate_fixture_id", ""))
    if reference_id == candidate_id:
        raise FrozenSuiteError("paired reference and candidate must be different sources")
    fixture_ids = {source.fixture_id for source in sources}
    if reference_id not in fixture_ids or candidate_id not in fixture_ids:
        raise FrozenSuiteError("pairing references an unknown fixture_id")
    target_pages = pairing.get("target_reference_pages")
    if (
        not isinstance(target_pages, list)
        or not target_pages
        or any(not isinstance(page, int) or page < 1 for page in target_pages)
        or target_pages != sorted(set(target_pages))
    ):
        raise FrozenSuiteError("target_reference_pages must be sorted unique positive integers")
    contracts = pairing.get("target_page_contracts")
    if not isinstance(contracts, list) or len(contracts) != len(target_pages):
        raise FrozenSuiteError("one target_page_contract is required per target page")
    contract_reference_pages = [
        contract.get("reference_page") for contract in contracts if isinstance(contract, dict)
    ]
    if contract_reference_pages != target_pages:
        raise FrozenSuiteError("target page contracts do not match target_reference_pages")
    if any(
        not isinstance(contract.get("candidate_page"), int)
        or contract.get("statement_type") not in {"CDKT", "KQKD", "LCTT", "TM"}
        or contract.get("expected_scope") not in {"MAIN_STATEMENT", "OFF_BALANCE_SHEET"}
        for contract in contracts
        if isinstance(contract, dict)
    ) or any(not isinstance(contract, dict) for contract in contracts):
        raise FrozenSuiteError("target page contract contains invalid fields")

    evidence_policy = payload.get("evidence_policy")
    if not isinstance(evidence_policy, dict):
        raise FrozenSuiteError("evidence_policy is required")
    required_evidence_flags = {
        "role_b_can_read_role_a_source": False,
        "role_b_can_read_role_a_result": False,
        "compare_starts_after_role_b_complete": True,
        "page_pairing_uses_text_or_values": False,
    }
    if any(evidence_policy.get(key) != value for key, value in required_evidence_flags.items()):
        raise FrozenSuiteError("evidence isolation policy is incomplete or unsafe")
    historical_policy = payload.get("historical_policy")
    if not isinstance(historical_policy, dict):
        raise FrozenSuiteError("historical_policy is required")
    _validate_historical_policy(historical_policy)
    return FrozenSuite(
        suite_id=str(payload.get("suite_id", "")),
        experiment_id=str(payload.get("experiment_id", "")),
        dataset_role=dataset_role,
        frozen_at=frozen_at,
        config_path=config_path,
        sources=tuple(sources),
        pairing=pairing,
        evidence_policy=evidence_policy,
        historical_policy=historical_policy,
    )
