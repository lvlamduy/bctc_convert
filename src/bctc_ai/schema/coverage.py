from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.hashing import sha256_file, stable_records_hash
from bctc_ai.schema.registry import SchemaItem, load_all

SCHEMA_CONSUMERS = (
    "ROLE_A",
    "ROLE_B",
    "EXCEL_OUTPUT",
    "EVALUATION",
    "MANDATORY_SEARCH",
)


class SchemaCoverageError(ValueError):
    pass


@dataclass(frozen=True)
class SchemaCoverageTarget:
    schema_id: int
    canonical_name: str
    statement_type: str
    display_order: int
    source_workbook: str
    source_row: int


@dataclass(frozen=True)
class SchemaSearchEvidence:
    document_id: str
    role: str
    schema_id: int
    terminal_outcome: str


@dataclass(frozen=True)
class MandatorySearchEvaluation:
    document_id: str
    status: str
    target_count: int
    universal_target_count: int
    target_count_by_statement: dict[str, int]
    missing_by_role: dict[str, tuple[int, ...]]
    duplicate_by_role: dict[str, tuple[int, ...]]
    unexpected_by_role: dict[str, tuple[int, ...]]
    completed_count_by_role: dict[str, int]
    outcome_count_by_role: dict[str, dict[str, int]]
    outcome_count_by_role_and_statement: dict[str, dict[str, dict[str, int]]]
    applicable_count_by_role: dict[str, int]
    observed_count_by_role: dict[str, int]
    mapped_numeric_count_by_role: dict[str, int]
    not_observed_count_by_role: dict[str, int]
    not_applicable_count_by_role: dict[str, int]
    ambiguous_count_by_role: dict[str, int]
    unresolved_count_by_role: dict[str, int]
    tm_1944_completed_by_role: dict[str, bool]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SchemaCoverageContract:
    version: int
    config_path: str
    config_sha256: str
    selection: str
    order_authority: str
    targets: tuple[SchemaCoverageTarget, ...]
    consumers: dict[str, tuple[int, ...]]
    mandatory_search_roles: tuple[str, ...]
    terminal_outcomes: tuple[str, ...]
    completion_rule: str
    ordered_targets_sha256: str

    def ids_for(self, consumer: str) -> tuple[int, ...]:
        try:
            return self.consumers[consumer]
        except KeyError as exc:
            raise SchemaCoverageError(f"unknown schema consumer: {consumer}") from exc

    def assert_exact_consumer_order(self, consumer: str, schema_ids: Iterable[int]) -> None:
        actual = tuple(schema_ids)
        expected = self.ids_for(consumer)
        if actual == expected:
            return
        missing = [schema_id for schema_id in expected if schema_id not in set(actual)]
        unexpected = [schema_id for schema_id in actual if schema_id not in set(expected)]
        raise SchemaCoverageError(
            f"{consumer} schema coverage/order mismatch: missing={missing}, "
            f"unexpected={unexpected}, order_equal={actual == expected}"
        )

    def to_registry(self) -> dict[str, object]:
        ordered_ids_sha256 = stable_records_hash(str(target.schema_id) for target in self.targets)
        by_statement: dict[str, list[SchemaCoverageTarget]] = {}
        for target in self.targets:
            by_statement.setdefault(target.statement_type, []).append(target)
        tm_1944 = next(
            (
                target
                for target in self.targets
                if target.statement_type == "TM" and target.schema_id == 1944
            ),
            None,
        )
        return {
            "format_version": self.version,
            "status": "PASS_ALL_TEMPLATE_ITEMS_ENROLLED",
            "config": {"path": self.config_path, "sha256": self.config_sha256},
            "selection": self.selection,
            "order_authority": self.order_authority,
            "target_count": len(self.targets),
            "ordered_targets_sha256": self.ordered_targets_sha256,
            "ordered_schema_ids_sha256": ordered_ids_sha256,
            "contains_tm_1944": tm_1944 is not None,
            "tm_1944_target": asdict(tm_1944) if tm_1944 is not None else None,
            "by_statement": {
                statement: {
                    "target_count": len(statement_targets),
                    "first_schema_id": statement_targets[0].schema_id,
                    "last_schema_id": statement_targets[-1].schema_id,
                    "ordered_schema_ids_sha256": stable_records_hash(
                        str(target.schema_id) for target in statement_targets
                    ),
                }
                for statement, statement_targets in by_statement.items()
            },
            "consumers": {
                consumer: {
                    "selection": "ALL_TEMPLATE_ITEMS",
                    "target_count": len(schema_ids),
                    "ordered_schema_ids_sha256": ordered_ids_sha256,
                    "contains_tm_1944": 1944 in schema_ids,
                    "last_schema_id": schema_ids[-1],
                }
                for consumer, schema_ids in self.consumers.items()
            },
            "mandatory_search": {
                "roles": list(self.mandatory_search_roles),
                "completion_rule": self.completion_rule,
                "terminal_outcomes": list(self.terminal_outcomes),
            },
        }


def _ordered_target_hash(targets: tuple[SchemaCoverageTarget, ...]) -> str:
    return stable_records_hash(
        json.dumps(asdict(target), ensure_ascii=False, sort_keys=True) for target in targets
    )


def load_schema_coverage(
    project_root: Path,
    *,
    schema_items: list[SchemaItem] | None = None,
) -> SchemaCoverageContract:
    project_root = project_root.resolve()
    config_path = project_root / "config/schemas/coverage-v1.yaml"
    payload: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if schema_items is None:
        _, schema_items = load_all(project_root / "template", project_root)
    if payload.get("selection") != "ALL_TEMPLATE_ITEMS":
        raise SchemaCoverageError("schema coverage must select every template item")
    if payload.get("order_authority") != "WORKBOOK_DISPLAY_ORDER":
        raise SchemaCoverageError("schema coverage must preserve workbook display order")
    consumers = payload.get("consumers")
    if not isinstance(consumers, dict) or tuple(consumers) != SCHEMA_CONSUMERS:
        raise SchemaCoverageError(
            f"schema coverage consumers must be exactly and in order {SCHEMA_CONSUMERS}"
        )
    if any(value != "ALL_TEMPLATE_ITEMS" for value in consumers.values()):
        raise SchemaCoverageError("every schema consumer must select all template items")
    mandatory = payload.get("mandatory_search")
    if not isinstance(mandatory, dict):
        raise SchemaCoverageError("mandatory-search configuration is missing")
    roles = mandatory.get("roles")
    if roles != ["ROLE_A", "ROLE_B"]:
        raise SchemaCoverageError("mandatory search must be independent for ROLE_A and ROLE_B")
    if mandatory.get("completion_rule") != (
        "EXACTLY_ONE_TERMINAL_OUTCOME_PER_SCHEMA_ID_PER_DOCUMENT"
    ):
        raise SchemaCoverageError("mandatory-search completion rule was weakened")
    outcomes = mandatory.get("terminal_outcomes")
    if (
        not isinstance(outcomes, list)
        or not outcomes
        or not all(isinstance(outcome, str) and outcome for outcome in outcomes)
    ):
        raise SchemaCoverageError("mandatory-search terminal outcomes are invalid")

    targets = tuple(
        SchemaCoverageTarget(
            schema_id=item.schema_id,
            canonical_name=item.canonical_name,
            statement_type=item.statement_type,
            display_order=item.display_order,
            source_workbook=item.source_workbook,
            source_row=item.source_row,
        )
        for item in schema_items
    )
    ordered_ids = tuple(target.schema_id for target in targets)
    if len(ordered_ids) != len(set(ordered_ids)):
        raise SchemaCoverageError("schema coverage contains duplicate ReportNormIds")
    return SchemaCoverageContract(
        version=int(payload.get("version", 0)),
        config_path=config_path.relative_to(project_root).as_posix(),
        config_sha256=sha256_file(config_path),
        selection=str(payload["selection"]),
        order_authority=str(payload["order_authority"]),
        targets=targets,
        consumers={consumer: ordered_ids for consumer in SCHEMA_CONSUMERS},
        mandatory_search_roles=tuple(roles),
        terminal_outcomes=tuple(outcomes),
        completion_rule=str(mandatory["completion_rule"]),
        ordered_targets_sha256=_ordered_target_hash(targets),
    )


def evaluate_mandatory_search(
    contract: SchemaCoverageContract,
    document_id: str,
    evidence: Iterable[SchemaSearchEvidence],
) -> MandatorySearchEvaluation:
    if not document_id:
        raise SchemaCoverageError("mandatory-search evaluation requires a document ID")
    expected = contract.ids_for("MANDATORY_SEARCH")
    expected_set = set(expected)
    statement_by_id = {target.schema_id: target.statement_type for target in contract.targets}
    target_count_by_statement: dict[str, int] = {}
    for target in contract.targets:
        target_count_by_statement[target.statement_type] = (
            target_count_by_statement.get(target.statement_type, 0) + 1
        )
    by_role: dict[str, list[SchemaSearchEvidence]] = {
        role: [] for role in contract.mandatory_search_roles
    }
    for record in evidence:
        if record.document_id != document_id:
            raise SchemaCoverageError("search evidence belongs to a different document")
        if record.role not in by_role:
            raise SchemaCoverageError(f"unexpected mandatory-search role: {record.role}")
        if record.terminal_outcome not in contract.terminal_outcomes:
            raise SchemaCoverageError(
                f"non-terminal or unknown search outcome: {record.terminal_outcome}"
            )
        by_role[record.role].append(record)

    missing_by_role: dict[str, tuple[int, ...]] = {}
    duplicate_by_role: dict[str, tuple[int, ...]] = {}
    unexpected_by_role: dict[str, tuple[int, ...]] = {}
    completed_count_by_role: dict[str, int] = {}
    outcome_count_by_role: dict[str, dict[str, int]] = {}
    outcome_count_by_role_and_statement: dict[str, dict[str, dict[str, int]]] = {}
    applicable_count_by_role: dict[str, int] = {}
    observed_count_by_role: dict[str, int] = {}
    mapped_numeric_count_by_role: dict[str, int] = {}
    not_observed_count_by_role: dict[str, int] = {}
    not_applicable_count_by_role: dict[str, int] = {}
    ambiguous_count_by_role: dict[str, int] = {}
    unresolved_count_by_role: dict[str, int] = {}
    tm_1944_completed_by_role: dict[str, bool] = {}
    for role, records in by_role.items():
        counts: dict[int, int] = {}
        records_by_id: dict[int, list[SchemaSearchEvidence]] = {}
        for record in records:
            counts[record.schema_id] = counts.get(record.schema_id, 0) + 1
            records_by_id.setdefault(record.schema_id, []).append(record)
        missing_by_role[role] = tuple(item for item in expected if item not in counts)
        duplicate_by_role[role] = tuple(item for item in expected if counts.get(item, 0) > 1)
        unexpected_by_role[role] = tuple(
            sorted(item for item in counts if item not in expected_set)
        )
        completed_count_by_role[role] = sum(counts.get(item, 0) == 1 for item in expected)
        tm_1944_completed_by_role[role] = counts.get(1944, 0) == 1
        terminal_records = [
            records_by_id[schema_id][0]
            for schema_id in expected
            if len(records_by_id.get(schema_id, ())) == 1
        ]
        role_outcomes = {outcome: 0 for outcome in contract.terminal_outcomes}
        role_statement_outcomes = {
            statement: {outcome: 0 for outcome in contract.terminal_outcomes}
            for statement in target_count_by_statement
        }
        for record in terminal_records:
            role_outcomes[record.terminal_outcome] += 1
            role_statement_outcomes[statement_by_id[record.schema_id]][record.terminal_outcome] += 1
        outcome_count_by_role[role] = role_outcomes
        outcome_count_by_role_and_statement[role] = role_statement_outcomes

        observed_statuses = {"OBSERVED_VALUE", "OBSERVED_ZERO", "DASH", "BLANK"}
        numeric_statuses = {"OBSERVED_VALUE", "OBSERVED_ZERO"}
        not_applicable_statuses = {"NOT_APPLICABLE", "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE"}
        ambiguous_statuses = {"AMBIGUOUS", "AMBIGUOUS_MAPPING"}
        unresolved_statuses = {"UNRESOLVED", "REFERENCE_NOT_YET_BUILT"}
        observed_count_by_role[role] = sum(
            role_outcomes.get(outcome, 0) for outcome in observed_statuses
        )
        mapped_numeric_count_by_role[role] = sum(
            role_outcomes.get(outcome, 0) for outcome in numeric_statuses
        )
        not_observed_count_by_role[role] = role_outcomes.get("NOT_OBSERVED", 0)
        not_applicable_count_by_role[role] = sum(
            role_outcomes.get(outcome, 0) for outcome in not_applicable_statuses
        )
        ambiguous_count_by_role[role] = sum(
            role_outcomes.get(outcome, 0) for outcome in ambiguous_statuses
        )
        unresolved_count_by_role[role] = sum(
            role_outcomes.get(outcome, 0) for outcome in unresolved_statuses
        )
        applicable_count_by_role[role] = len(terminal_records) - not_applicable_count_by_role[role]
    passed = not any(
        missing_by_role[role] or duplicate_by_role[role] or unexpected_by_role[role]
        for role in contract.mandatory_search_roles
    )
    return MandatorySearchEvaluation(
        document_id=document_id,
        status="PASS" if passed else "INCOMPLETE",
        target_count=len(expected),
        universal_target_count=len(expected),
        target_count_by_statement=target_count_by_statement,
        missing_by_role=missing_by_role,
        duplicate_by_role=duplicate_by_role,
        unexpected_by_role=unexpected_by_role,
        completed_count_by_role=completed_count_by_role,
        outcome_count_by_role=outcome_count_by_role,
        outcome_count_by_role_and_statement=outcome_count_by_role_and_statement,
        applicable_count_by_role=applicable_count_by_role,
        observed_count_by_role=observed_count_by_role,
        mapped_numeric_count_by_role=mapped_numeric_count_by_role,
        not_observed_count_by_role=not_observed_count_by_role,
        not_applicable_count_by_role=not_applicable_count_by_role,
        ambiguous_count_by_role=ambiguous_count_by_role,
        unresolved_count_by_role=unresolved_count_by_role,
        tm_1944_completed_by_role=tm_1944_completed_by_role,
    )
