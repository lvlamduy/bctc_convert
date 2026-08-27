"""Content-addressed page-version overlay produced by targeted Gemini repairs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "GEMINI_FAMILY_EFFECTIVE_PAGE_FRONTIER_V1"


class GeminiFamilyEffectivePageFrontierV1Error(ValueError):
    """One repair overlay is incomplete, ambiguous, or not content-addressed."""


def _error(message: str) -> GeminiFamilyEffectivePageFrontierV1Error:
    return GeminiFamilyEffectivePageFrontierV1Error(message)


def _content_ref(value: Any) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"path", "sha256", "size_bytes"}:
        raise _error("effective page frontier content reference fields drifted")
    checked = canonical_clone_v1(value)
    if (
        type(checked["path"]) is not str
        or not checked["path"]
        or checked["path"].startswith("/")
        or ".." in checked["path"].split("/")
        or type(checked["sha256"]) is not str
        or len(checked["sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in checked["sha256"])
        or type(checked["size_bytes"]) is not int
        or checked["size_bytes"] <= 0
    ):
        raise _error("effective page frontier content reference is invalid")
    return checked


def _version_id(value: Any) -> str:
    if (
        type(value) is not str
        or not value.startswith("gfpstorev1:json:")
        or len(value.removeprefix("gfpstorev1:json:")) != 64
    ):
        raise _error("effective page frontier page version identity is invalid")
    return value


def _frontier_hash(version_ids: Sequence[str]) -> str:
    return canonical_json_sha256_v1(list(version_ids))


def build_gemini_family_effective_page_frontier_v1(
    *,
    base_corpus_manifest_index_id: str,
    base_page_json_version_ids: Sequence[str],
    database_ref: Mapping[str, Any],
    family_id: str,
    job_status_counts: Mapping[str, int],
    repair_source_family_run_id: str,
    replacements: Sequence[Mapping[str, Any]],
    results_database_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one immutable overlay and prove the resulting ordered page frontier."""

    base_ids = [_version_id(value) for value in base_page_json_version_ids]
    if (
        type(base_corpus_manifest_index_id) is not str
        or not base_corpus_manifest_index_id.startswith("gjfccmiv1:index:")
        or not base_ids
        or len(base_ids) != len(set(base_ids))
        or type(family_id) is not str
        or not family_id
        or type(repair_source_family_run_id) is not str
        or not repair_source_family_run_id.startswith("gjfafstorev1:run:")
        or type(job_status_counts) is not dict
        or set(job_status_counts) != {"ABSTAINED", "RESOLVED"}
        or any(type(value) is not int or value < 0 for value in job_status_counts.values())
    ):
        raise _error("effective page frontier input contract is invalid")
    checked_replacements = []
    required = {
        "base_page_json_version_id",
        "candidate_id",
        "document_ordinal",
        "physical_page",
        "repair_id",
        "repair_job_id",
        "repair_receipt_sha256",
        "selected_page_json_version_id",
    }
    for replacement in replacements:
        if type(replacement) is not dict or set(replacement) != required:
            raise _error("effective page frontier replacement fields drifted")
        checked = canonical_clone_v1(replacement)
        _version_id(checked["base_page_json_version_id"])
        _version_id(checked["selected_page_json_version_id"])
        if (
            type(checked["candidate_id"]) is not str
            or not checked["candidate_id"].startswith("gjfafcv1:candidate:")
            or type(checked["document_ordinal"]) is not int
            or checked["document_ordinal"] <= 0
            or type(checked["physical_page"]) is not int
            or checked["physical_page"] <= 0
            or type(checked["repair_id"]) is not str
            or not checked["repair_id"].startswith("gjfrrv1:repair:")
            or type(checked["repair_job_id"]) is not str
            or not checked["repair_job_id"].startswith("gjfrrqv1:job:")
            or type(checked["repair_receipt_sha256"]) is not str
            or len(checked["repair_receipt_sha256"]) != 64
        ):
            raise _error("effective page frontier replacement is invalid")
        checked_replacements.append(checked)
    checked_replacements.sort(
        key=lambda item: (item["document_ordinal"], item["physical_page"], item["repair_job_id"])
    )
    if (
        len(checked_replacements) != job_status_counts["RESOLVED"]
        or len({item["base_page_json_version_id"] for item in checked_replacements})
        != len(checked_replacements)
        or any(
            item["base_page_json_version_id"] not in set(base_ids) for item in checked_replacements
        )
    ):
        raise _error("effective page frontier replacement axis is incomplete or duplicate")
    by_base = {
        item["base_page_json_version_id"]: item["selected_page_json_version_id"]
        for item in checked_replacements
    }
    effective_ids = [by_base.get(version_id, version_id) for version_id in base_ids]
    if len(effective_ids) != len(set(effective_ids)):
        raise _error("effective page frontier aliases two physical pages")
    material = {
        "base_corpus_manifest_index_id": base_corpus_manifest_index_id,
        "base_page_count": len(base_ids),
        "base_page_json_frontier_sha256": _frontier_hash(base_ids),
        "database_ref": _content_ref(dict(database_ref)),
        "effective_page_count": len(effective_ids),
        "effective_page_json_frontier_sha256": _frontier_hash(effective_ids),
        "family_id": family_id,
        "format_version": FORMAT_VERSION,
        "job_status_counts": canonical_clone_v1(dict(job_status_counts)),
        "repair_source_family_run_id": repair_source_family_run_id,
        "replacements": checked_replacements,
        "results_database_ref": _content_ref(dict(results_database_ref)),
    }
    return validate_gemini_family_effective_page_frontier_v1(
        {
            **material,
            "effective_page_frontier_id": "gjfepfv1:frontier:" + canonical_json_sha256_v1(material),
        }
    )


def validate_gemini_family_effective_page_frontier_v1(value: Any) -> dict[str, Any]:
    """Validate the self-addressed envelope without reopening its external databases."""

    required = {
        "base_corpus_manifest_index_id",
        "base_page_count",
        "base_page_json_frontier_sha256",
        "database_ref",
        "effective_page_count",
        "effective_page_frontier_id",
        "effective_page_json_frontier_sha256",
        "family_id",
        "format_version",
        "job_status_counts",
        "repair_source_family_run_id",
        "replacements",
        "results_database_ref",
    }
    if type(value) is not dict or set(value) != required:
        raise _error("effective page frontier envelope fields drifted")
    checked = canonical_clone_v1(value)
    if (
        checked["format_version"] != FORMAT_VERSION
        or type(checked["base_page_count"]) is not int
        or checked["base_page_count"] <= 0
        or checked["effective_page_count"] != checked["base_page_count"]
        or type(checked["base_page_json_frontier_sha256"]) is not str
        or len(checked["base_page_json_frontier_sha256"]) != 64
        or type(checked["effective_page_json_frontier_sha256"]) is not str
        or len(checked["effective_page_json_frontier_sha256"]) != 64
        or type(checked["family_id"]) is not str
        or not checked["family_id"]
        or type(checked["job_status_counts"]) is not dict
        or set(checked["job_status_counts"]) != {"ABSTAINED", "RESOLVED"}
        or any(type(item) is not int or item < 0 for item in checked["job_status_counts"].values())
        or type(checked["replacements"]) is not list
        or len(checked["replacements"]) != checked["job_status_counts"]["RESOLVED"]
    ):
        raise _error("effective page frontier envelope is invalid")
    _content_ref(checked["database_ref"])
    _content_ref(checked["results_database_ref"])
    material = {key: checked[key] for key in checked if key != "effective_page_frontier_id"}
    if checked["effective_page_frontier_id"] != "gjfepfv1:frontier:" + canonical_json_sha256_v1(
        material
    ):
        raise _error("effective page frontier identity does not replay")
    return checked


def apply_gemini_family_effective_page_frontier_v1(
    value: Any, *, base_page_json_version_ids: Sequence[str]
) -> tuple[dict[str, Any], list[str]]:
    """Validate an overlay and return its exact effective ordered version axis."""

    checked = validate_gemini_family_effective_page_frontier_v1(value)
    rebuilt = build_gemini_family_effective_page_frontier_v1(
        base_corpus_manifest_index_id=checked.get("base_corpus_manifest_index_id"),
        base_page_json_version_ids=base_page_json_version_ids,
        database_ref=checked.get("database_ref"),
        family_id=checked.get("family_id"),
        job_status_counts=checked.get("job_status_counts"),
        repair_source_family_run_id=checked.get("repair_source_family_run_id"),
        replacements=checked.get("replacements"),
        results_database_ref=checked.get("results_database_ref"),
    )
    if rebuilt != checked:
        raise _error("effective page frontier does not replay exactly")
    by_base = {
        item["base_page_json_version_id"]: item["selected_page_json_version_id"]
        for item in checked["replacements"]
    }
    return checked, [
        by_base.get(version_id, version_id) for version_id in base_page_json_version_ids
    ]
