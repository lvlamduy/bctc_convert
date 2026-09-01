"""Read-only federation of exact family runs for the 27-bank review UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import FAMILY_ORDER
from .repository import ReviewRepository, ReviewSettings

_FORMAT_VERSION = "BCTC_FAMILY_REVIEW_RUN_MANIFEST_V1"


def _path(base: Path, value: Any, *, directory: bool) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Review manifest có đường dẫn không hợp lệ")
    unresolved = Path(value).expanduser()
    if not unresolved.is_absolute():
        unresolved = base / unresolved
    if unresolved.is_symlink():
        raise ValueError("Review manifest không được dùng symlink")
    candidate = unresolved.resolve(strict=False)
    if not (candidate.is_dir() if directory else candidate.is_file()):
        raise ValueError("Review manifest trỏ tới nguồn không tồn tại hoặc không an toàn")
    return candidate


def _load_manifest(settings: ReviewSettings) -> list[ReviewRepository]:
    manifest_path = settings.run_manifest
    if manifest_path is None:
        return [ReviewRepository(settings)]
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("BCTC_REVIEW_RUN_MANIFEST không phải file hợp lệ")
    try:
        value = json.loads(manifest_path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Review manifest không phải JSON hợp lệ") from exc
    sources = value.get("sources") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or value.get("format_version") != _FORMAT_VERSION
        or not isinstance(sources, list)
        or not sources
    ):
        raise ValueError("Review manifest sai format hoặc không có nguồn")

    repositories: list[ReviewRepository] = []
    identities: set[tuple[str, str]] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Review manifest có source không hợp lệ")
        family_id = source.get("family_id")
        family_run_id = source.get("family_run_id")
        if not isinstance(family_id, str) or not family_id:
            raise ValueError("Review manifest thiếu family_id")
        if not isinstance(family_run_id, str) or not family_run_id:
            raise ValueError("Review manifest thiếu family_run_id")
        results_database = _path(
            manifest_path.parent, source.get("results_database"), directory=False
        )
        page_database = _path(manifest_path.parent, source.get("page_database"), directory=False)
        pdf_root = _path(manifest_path.parent, source.get("pdf_root"), directory=True)
        identity = (family_id, family_run_id)
        if identity in identities:
            raise ValueError("Review manifest lặp cùng một family run")
        identities.add(identity)
        repositories.append(
            ReviewRepository(
                ReviewSettings(
                    results_database=results_database,
                    page_database=page_database,
                    pdf_root=pdf_root,
                    schema_path=settings.schema_path,
                    cache_directory=settings.cache_directory,
                    family_id=family_id,
                    family_run_id=family_run_id,
                )
            )
        )
    # Force exact run/family validation before the Flask server accepts traffic.
    for repository in repositories:
        repository.families()
    return repositories


class FederatedReviewRepository:
    """Present several immutable run sources as one read-only review corpus."""

    def __init__(self, settings: ReviewSettings):
        self.settings = settings
        self._repositories = _load_manifest(settings)
        self._source_repositories: dict[str, ReviewRepository] = {}
        self._repository_families = [
            (repository, repository.families()) for repository in self._repositories
        ]
        # Filter labels are repository-independent.  Cache one template while
        # the exact run is being authenticated so request handling never has
        # to rescan a child run merely to rebuild the same option catalogue.
        self._option_template = self._repositories[0].options()
        repositories_by_family: dict[str, list[ReviewRepository]] = {}
        for repository, families in self._repository_families:
            for family in families:
                repositories_by_family.setdefault(family["id"], []).append(repository)
        self._repositories_by_family = repositories_by_family

    @property
    def ready(self) -> bool:
        return bool(self._repositories) and all(
            repository.ready for repository in self._repositories
        )

    def configuration_status(self) -> dict[str, Any]:
        return {
            "results_database": all(
                repository.configuration_status()["results_database"]
                for repository in self._repositories
            ),
            "page_database": all(
                repository.configuration_status()["page_database"]
                for repository in self._repositories
            ),
            "pdf_root": all(
                repository.configuration_status()["pdf_root"] for repository in self._repositories
            ),
            "schema": self.settings.schema_path.exists(),
            "run_manifest": self.settings.run_manifest is not None,
            "source_count": len(self._repositories),
            "ready": self.ready,
        }

    def families(self) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for _repository, families in self._repository_families:
            for family in families:
                existing = grouped.setdefault(
                    family["id"],
                    {
                        **family,
                        "document_count": 0,
                        "ready_count": 0,
                        "not_observed_count": 0,
                        "unresolved_count": 0,
                        "mapping_count": 0,
                        "run_source_count": 0,
                    },
                )
                for key in (
                    "document_count",
                    "ready_count",
                    "not_observed_count",
                    "unresolved_count",
                    "mapping_count",
                ):
                    existing[key] += family[key]
                existing["run_source_count"] += 1
        order = {family_id: ordinal for ordinal, family_id in enumerate(FAMILY_ORDER, start=1)}
        return sorted(
            grouped.values(),
            key=lambda item: (order.get(item["id"], len(FAMILY_ORDER) + 1), item["name"]),
        )

    def _repositories_for_family(self, family_id: str) -> list[ReviewRepository]:
        return list(self._repositories_by_family.get(family_id, []))

    def options(self) -> dict[str, Any]:
        families = self.families()
        default_family = (
            "LOAN_QUALITY_CLASSIFICATION"
            if any(family["id"] == "LOAN_QUALITY_CLASSIFICATION" for family in families)
            else families[0]["id"]
            if families
            else ""
        )
        payload = dict(self._option_template)
        documents = self.documents(default_family, {}) if default_family else []
        payload.update(
            {
                "families": families,
                "banks": sorted({document["bank"] for document in documents}),
                "years": sorted({document["year"] for document in documents}, reverse=True),
                "default_family": default_family,
                "configuration": self.configuration_status(),
            }
        )
        return payload

    def documents(self, family_id: str, filters: dict[str, str]) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        seen: set[str] = set()
        for repository in self._repositories_for_family(family_id):
            for document in repository.documents(family_id, filters):
                source_sha256 = document["source_sha256"]
                if source_sha256 in seen:
                    raise ValueError("Review manifest làm trùng PDF trong cùng family")
                seen.add(source_sha256)
                self._source_repositories.setdefault(source_sha256, repository)
                documents.append(document)
        return sorted(
            documents,
            key=lambda item: (
                item["bank"],
                item["year"],
                item["period_code"],
                item["scope_code"],
                item["filename"],
            ),
        )

    def review(self, family_id: str, source_sha256: str) -> dict[str, Any]:
        matches: list[ReviewRepository] = []
        for repository in self._repositories_for_family(family_id):
            try:
                repository._trial(family_id, source_sha256)  # noqa: SLF001
            except LookupError:
                continue
            matches.append(repository)
        if not matches:
            raise LookupError("Không tìm thấy PDF trong family đang chọn")
        if len(matches) != 1:
            raise ValueError("Review manifest làm trùng PDF trong cùng family")
        self._source_repositories.setdefault(source_sha256, matches[0])
        return matches[0].review(family_id, source_sha256)

    def render_page(self, source_sha256: str, physical_page: int) -> Path:
        cached = self._source_repositories.get(source_sha256)
        if cached is not None:
            return cached.render_page(source_sha256, physical_page)
        matches: list[ReviewRepository] = []
        for repository in self._repositories:
            try:
                repository.source_logical_name(source_sha256)
            except LookupError:
                continue
            matches.append(repository)
        unique = {id(repository): repository for repository in matches}
        if not unique:
            raise LookupError("Không tìm thấy PDF trong page store")
        # The same immutable PDF may be referenced by several family runs that
        # share one page store; using any matching repository is byte-equivalent.
        return next(iter(unique.values())).render_page(source_sha256, physical_page)


def build_review_repository(
    settings: ReviewSettings,
) -> ReviewRepository | FederatedReviewRepository:
    """Build the legacy single-store or manifest-driven federated repository."""

    if settings.run_manifest is None:
        return ReviewRepository(settings)
    return FederatedReviewRepository(settings)
