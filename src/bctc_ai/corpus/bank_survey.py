from __future__ import annotations

import json
import os
import re
import stat
import unicodedata
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from bctc_ai.core.hashing import sha256_bytes, sha256_file


class BankCorpusSurveyError(ValueError):
    """The registered banking corpus cannot be inventoried without guessing."""


POLICY_RELATIVE_PATH = Path("config/corpus/bank-corpus-survey-v1.yaml")
IMPLEMENTATION_RELATIVE_PATH = Path("src/bctc_ai/corpus/bank_survey.py")
OUTPUT_RELATIVE_PATH = Path("output/development/bank-corpus-survey-v1/corpus-inventory.json")
SOURCE_PROFILE_OUTPUT_RELATIVE_PATH = Path(
    "output/development/bank-corpus-survey-v1/wave-1-source-profile.json"
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DATASET_ROLES = {
    "LOGIC_DEVELOPMENT",
    "CALIBRATION",
    "UNTOUCHED_HOLDOUT",
    "VALIDATION",
    "PRODUCTION_INPUT",
}
_QUARTER_PATTERNS = {
    "Q1": re.compile(r"(?:^| )(?:q1(?:20\d{2})?|quy 1|quy i)(?: |$)"),
    "Q2": re.compile(r"(?:^| )(?:q2(?:20\d{2})?|quy 2|quy ii)(?: |$)"),
    "Q3": re.compile(r"(?:^| )(?:q3(?:20\d{2})?|quy 3|quy iii)(?: |$)"),
    "Q4": re.compile(r"(?:^| )(?:q4(?:20\d{2})?|quy 4|quy iv)(?: |$)"),
}
_SUPPORTING_DOCUMENT_PHRASES = (
    "giai trinh",
    "giaitrinh",
    "explanation relating",
    "explanations relating",
    "explanationsrelatingtofss",
    "information disclosure",
    "informationdisclosureoffss",
    "cong bo thong tin",
    "congbothongtin",
    "thuyet minh bctc",
    "thuyet minh bao cao tai chinh",
    "bao cao thuong nien",
    "annual report",
    "kqkd",
    "ket qua kinh doanh",
    "bao cao soat xet",
    "independent auditor report",
)
_FULL_STATEMENT_PHRASES = (
    "bctc",
    "bao cao tai chinh",
    "baocaotaichinh",
    "financial statement",
    "financial statements",
    "financialstatement",
    "financialstatements",
)


def _canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _read_stable_bytes(path: Path, label: str) -> bytes:
    before = path.stat()
    payload = path.read_bytes()
    after = path.stat()
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after or len(payload) != before.st_size:
        raise BankCorpusSurveyError(f"{label} changed while it was read")
    return payload


def _canonical_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise BankCorpusSurveyError(f"{label} must be a nonempty project-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise BankCorpusSurveyError(f"{label} is not canonical")
    return value


def _resolve_under_root(project_root: Path, relative: str, label: str) -> Path:
    canonical = _canonical_relative_path(relative, label)
    path = (project_root / Path(*PurePosixPath(canonical).parts)).resolve()
    if not path.is_relative_to(project_root):
        raise BankCorpusSurveyError(f"{label} escapes the project root")
    return path


def _normalize_filename(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold().translate(str.maketrans({"đ": "d"})))
    unaccented = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", " ", unaccented).strip()


def _filename_metadata(relative_path: str, year: int | None) -> dict[str, Any]:
    name = PurePosixPath(relative_path).name
    key = _normalize_filename(name)
    supporting_matches = [phrase for phrase in _SUPPORTING_DOCUMENT_PHRASES if phrase in key]
    full_matches = [phrase for phrase in _FULL_STATEMENT_PHRASES if phrase in key]
    document_kind = (
        "SUPPORTING_OR_PARTIAL_DOCUMENT"
        if supporting_matches
        else "FULL_FINANCIAL_STATEMENT_CANDIDATE"
        if full_matches
        else "UNCLASSIFIED_DOCUMENT_KIND"
    )

    consolidated = any(
        phrase in key for phrase in ("hop nhat", "hopnhat", "consolidated", "consol financial")
    )
    separate = any(
        phrase in key
        for phrase in (
            "rieng le",
            "riengle",
            "cong ty me",
            "congtyme",
            "separate",
            "single financial",
        )
    )
    scope = (
        "AMBIGUOUS"
        if consolidated and separate
        else "CONSOLIDATED"
        if consolidated
        else "SEPARATE"
        if separate
        else "UNKNOWN"
    )

    quarters = [quarter for quarter, pattern in _QUARTER_PATTERNS.items() if pattern.search(key)]
    if len(quarters) == 1:
        period = quarters[0]
    elif len(quarters) > 1:
        period = "AMBIGUOUS"
    elif any(
        phrase in key
        for phrase in (
            "6 thang dau nam",
            "6thangdaunam",
            "ban nien",
            "bannien",
            "half year",
        )
    ):
        period = "H1"
    elif any(phrase in key for phrase in ("kiem toan nam", "audited", "year ended", "ye24")):
        period = "ANNUAL"
    else:
        period = "UNKNOWN"

    unaudited = any(
        phrase in key
        for phrase in (
            "chua kiem toan",
            "chuakiemtoan",
            "chua duoc kiem toan",
            "unaudited",
            "not audited",
        )
    )
    audited = not unaudited and any(
        phrase in key for phrase in ("kiem toan", "kiemtoan", "audited")
    )
    reviewed = any(
        phrase in key for phrase in ("soat xet", "soatxet", "ktsx", "reviewed", "review")
    )
    assurance = (
        "AMBIGUOUS"
        if (audited and reviewed) or (unaudited and reviewed)
        else "UNAUDITED"
        if unaudited
        else "AUDITED"
        if audited
        else "REVIEWED"
        if reviewed
        else "UNKNOWN"
    )

    english = any(
        phrase in key
        for phrase in (
            "tieng anh",
            "english",
            "financial statement",
            "financial statements",
            "financialstatement",
            "financialstatements",
            "consolidated financial",
            "separate financial",
        )
    ) or bool(re.search(r"(?:^| )(?:en|eng)(?: |$)", key))
    vietnamese = any(
        phrase in key
        for phrase in (
            "tieng viet",
            "bao cao tai chinh",
            "bctc",
            "hop nhat",
            "rieng le",
        )
    ) or bool(re.search(r"(?:^| )(?:vi|vn|tv)(?: |$)", key))
    language = (
        "BILINGUAL_OR_AMBIGUOUS"
        if english and vietnamese
        else "EN"
        if english
        else "VI"
        if vietnamese
        else "UNKNOWN"
    )

    source_type_hint = (
        "SEARCHABLE_FILENAME_HINT"
        if any(phrase in key for phrase in ("searchable", "ban tra cuu", "tra cuu"))
        else "UNASSESSED_REQUIRES_PDF_INSPECTION"
    )
    return {
        "normalized_filename": key,
        "document_kind": document_kind,
        "document_kind_evidence": sorted({*supporting_matches, *full_matches}),
        "scope_hint": scope,
        "reporting_period_hint": period,
        "reporting_year": year,
        "assurance_hint": assurance,
        "language_hint": language,
        "source_type_hint": source_type_hint,
        "metadata_authority": "FILENAME_DERIVED_NON_AUTHORITATIVE",
    }


def _load_json_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BankCorpusSurveyError(f"{label} is not valid JSON") from error
    if not isinstance(value, dict):
        raise BankCorpusSurveyError(f"{label} must be a JSON object")
    return value


def _load_jsonl(payload: bytes, label: str) -> list[dict[str, Any]]:
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise BankCorpusSurveyError(f"{label} is not UTF-8") from error
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise BankCorpusSurveyError(f"{label} line {line_number} is not valid JSON") from error
        if not isinstance(record, dict):
            raise BankCorpusSurveyError(f"{label} line {line_number} is not an object")
        records.append(record)
    return records


def load_bank_corpus_survey_policy(path: Path, project_root: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    if path.resolve() != (project_root / POLICY_RELATIVE_PATH).resolve():
        raise BankCorpusSurveyError(
            f"bank corpus survey requires canonical policy {POLICY_RELATIVE_PATH}"
        )
    try:
        policy = yaml.safe_load(_read_stable_bytes(path, "bank corpus survey policy"))
    except yaml.YAMLError as error:
        raise BankCorpusSurveyError("bank corpus survey policy is invalid YAML") from error
    if not isinstance(policy, dict):
        raise BankCorpusSurveyError("bank corpus survey policy must be an object")
    if policy.get("version") != 1 or policy.get("policy") != "BANK_CORPUS_BREADTH_FIRST_SURVEY_V1":
        raise BankCorpusSurveyError("bank corpus survey policy identity drifted")
    if policy.get("claim_boundary") != (
        "REGISTERED_PDF_METADATA_AND_SOURCE_FIRST_SURVEY_SELECTION_ONLY"
    ):
        raise BankCorpusSurveyError("bank corpus survey claim boundary drifted")
    expected_top = {
        "version",
        "policy",
        "claim_boundary",
        "inputs",
        "inventory",
        "wave_1",
        "source_profile",
        "safety",
        "output",
    }
    if set(policy) != expected_top:
        raise BankCorpusSurveyError("bank corpus survey policy fields drifted")
    inputs = policy.get("inputs")
    if inputs != {
        "bank_registry": "data/registered/bank_registry.json",
        "source_registry": "data/registered/source_registry.jsonl",
        "dataset_role_registry": "data/registered/dataset_roles.jsonl",
    }:
        raise BankCorpusSurveyError("bank corpus survey input inventory drifted")
    for name, relative in inputs.items():
        _resolve_under_root(project_root, relative, name)
    inventory = policy.get("inventory")
    if inventory != {
        "sector": "BANK",
        "require_every_registered_bank_represented": True,
        "require_stable_registered_pdf_identity": True,
        "filename_metadata_is_authoritative": False,
        "source_type_requires_pdf_inspection": True,
    }:
        raise BankCorpusSurveyError("bank corpus inventory safety gates drifted")
    wave = policy.get("wave_1")
    if (
        not isinstance(wave, dict)
        or set(wave)
        != {
            "selection_status",
            "documents_per_bank",
            "preferred_year",
            "preferred_period",
            "preferred_language",
            "scope_preference",
            "assurance_preference",
            "exclude_dataset_roles",
            "require_full_financial_statement_candidate",
            "source_type_used_for_selection",
            "registered_development_role_used_only_as_tie_breaker",
            "bank_identity_used_for_parser_routing",
            "fallback",
        }
        or wave.get("selection_status") != "SELECTED_PENDING_SOURCE_SURVEY"
        or wave.get("documents_per_bank") != 1
        or not isinstance(wave.get("preferred_year"), int)
        or wave.get("preferred_period") not in _QUARTER_PATTERNS
        or wave.get("preferred_language") != "VI"
        or wave.get("scope_preference") != ["CONSOLIDATED", "SEPARATE", "UNKNOWN"]
        or wave.get("assurance_preference") != ["REVIEWED", "AUDITED", "UNKNOWN"]
        or wave.get("exclude_dataset_roles") != ["UNTOUCHED_HOLDOUT"]
        or wave.get("require_full_financial_statement_candidate") is not True
        or wave.get("source_type_used_for_selection") is not False
        or wave.get("registered_development_role_used_only_as_tie_breaker") is not True
        or wave.get("bank_identity_used_for_parser_routing") is not False
        or wave.get("fallback") != "RANK_YEAR_THEN_PERIOD_LANGUAGE_SCOPE_ASSURANCE_ROLE_AND_PATH"
    ):
        raise BankCorpusSurveyError("bank corpus Wave 1 selection gates drifted")
    safety = policy.get("safety")
    if safety != {
        "schema_inputs_allowed": False,
        "prior_mapping_outputs_allowed": False,
        "historical_values_allowed": False,
        "bank_specific_parser_rules_allowed": False,
        "expected_document_count_rules_allowed": False,
        "preserve_unclassified_metadata": True,
    }:
        raise BankCorpusSurveyError("bank corpus survey isolation gates drifted")
    source_profile = policy.get("source_profile")
    if source_profile != {
        "engine": "PYMUPDF_PAGE_EVIDENCE_V1",
        "substantive_text_layer_min_non_whitespace_chars": 40,
        "text_layer_visibility_proxy": "RAWDICT_SPAN_ALPHA_NONZERO",
        "image_presence_source": "PAGE_GET_IMAGE_INFO_PAINTED",
        "dominant_raster_min_page_coverage": 0.5,
        "ocr_allowed": False,
        "schema_allowed": False,
        "structural_survey_claimed": False,
        "route_vocabulary": [
            "SCAN_ROUTE",
            "MIXED_PAGE_HYBRID_ROUTE",
            "SEARCHABLE_OVER_IMAGE_REQUIRES_GHOST_TEXT_VALIDATION",
            "NATIVE_SEARCHABLE_ROUTE",
            "UNRESOLVED_SOURCE_ROUTE",
        ],
    }:
        raise BankCorpusSurveyError("bank corpus source-profile contract drifted")
    output = policy.get("output")
    if output != {
        "format": "BANK_CORPUS_SURVEY_INVENTORY_RESULT_V1",
        "source_profile_format": "BANK_CORPUS_WAVE_1_SOURCE_PROFILE_V1",
        "canonical_json": True,
        "exclusive_no_overwrite": True,
        "output_directory": "output/development/bank-corpus-survey-v1",
        "inventory_filename": "corpus-inventory.json",
        "source_profile_filename": "wave-1-source-profile.json",
    }:
        raise BankCorpusSurveyError("bank corpus survey output contract drifted")
    return policy


def _selection_key(
    record: dict[str, Any],
    *,
    preferred_year: int,
    preferred_period: str,
    scope_preference: list[str],
    assurance_preference: list[str],
) -> tuple[Any, ...]:
    metadata = record["filename_metadata"]
    year = record["year"]
    period = metadata["reporting_period_hint"]
    language = metadata["language_hint"]
    scope = metadata["scope_hint"]
    assurance = metadata["assurance_hint"]
    period_rank = {
        preferred_period: 0,
        "Q1": 1,
        "H1": 2,
        "Q3": 3,
        "Q4": 4,
        "ANNUAL": 5,
        "UNKNOWN": 6,
        "AMBIGUOUS": 7,
    }.get(period, 8)
    scope_rank = (
        scope_preference.index(scope) if scope in scope_preference else len(scope_preference)
    )
    assurance_rank = (
        assurance_preference.index(assurance)
        if assurance in assurance_preference
        else len(assurance_preference)
    )
    basename = PurePosixPath(record["relative_path"]).name
    return (
        0 if year == preferred_year else 1,
        abs(preferred_year - year) if isinstance(year, int) else 10_000,
        period_rank,
        0 if language == "VI" else 1 if language == "BILINGUAL_OR_AMBIGUOUS" else 2,
        scope_rank,
        assurance_rank,
        0 if record["dataset_role"] == "LOGIC_DEVELOPMENT" else 1,
        len(basename),
        record["relative_path"],
    )


def build_bank_corpus_inventory(project_root: Path, policy_path: Path) -> dict[str, Any]:
    project_root = project_root.resolve()
    policy = load_bank_corpus_survey_policy(policy_path, project_root)
    input_bytes: dict[str, bytes] = {}
    input_paths: dict[str, Path] = {}
    for name, relative in policy["inputs"].items():
        path = _resolve_under_root(project_root, relative, name)
        input_paths[name] = path
        input_bytes[name] = _read_stable_bytes(path, name)

    bank_registry = _load_json_object(input_bytes["bank_registry"], "bank registry")
    source_records = _load_jsonl(input_bytes["source_registry"], "source registry")
    role_records = _load_jsonl(input_bytes["dataset_role_registry"], "dataset role registry")
    bank_entities = bank_registry.get("entities")
    if not isinstance(bank_entities, list):
        raise BankCorpusSurveyError("bank registry has no entity inventory")
    bank_codes = sorted(
        {
            str(entity["code"])
            for entity in bank_entities
            if isinstance(entity, dict) and entity.get("category") == "BANK"
        }
    )
    if not bank_codes:
        raise BankCorpusSurveyError("bank registry has no BANK entities")

    content_counts = Counter(str(record.get("sha256")) for record in source_records)
    paths_seen: set[str] = set()
    source_identity_by_path: dict[str, str] = {}
    documents: list[dict[str, Any]] = []
    for source in source_records:
        relative = _canonical_relative_path(source.get("relative_path"), "source path")
        if relative in paths_seen:
            raise BankCorpusSurveyError("source registry repeats a source path")
        paths_seen.add(relative)
        bank = source.get("bank")
        year = source.get("year")
        digest = source.get("sha256")
        size = source.get("size_bytes")
        document_id = source.get("document_id")
        if (
            bank not in bank_codes
            or source.get("kind") != "PDF"
            or source.get("state") != "REGISTERED"
            or source.get("hash_verified_stable") is not True
            or not isinstance(year, int)
            or not isinstance(digest, str)
            or _SHA256.fullmatch(digest) is None
            or document_id != f"sha256:{digest}"
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size <= 0
        ):
            raise BankCorpusSurveyError(
                f"source registry record is not a stable bank PDF: {relative}"
            )
        source_identity_by_path[relative] = document_id
        documents.append(
            {
                "document_id": document_id,
                "sha256": digest,
                "size_bytes": size,
                "relative_path": relative,
                "bank": bank,
                "year": year,
                "dataset_role": None,
                "duplicate_content_path_count": content_counts[digest],
                "filename_metadata": _filename_metadata(relative, year),
                "source_survey_status": "NOT_YET_SOURCE_INSPECTED",
            }
        )

    role_by_document: dict[str, str] = {}
    for record in role_records:
        if set(record) != {
            "assigned_at",
            "dataset_role",
            "document_id",
            "immutable",
            "source_path",
        }:
            raise BankCorpusSurveyError("dataset role registry fields drifted")
        document_id = record.get("document_id")
        role = record.get("dataset_role")
        source_path = _canonical_relative_path(
            record.get("source_path"), "dataset role source path"
        )
        if (
            not isinstance(document_id, str)
            or role not in _DATASET_ROLES
            or record.get("immutable") is not True
            or not isinstance(record.get("assigned_at"), str)
            or not record["assigned_at"]
            or source_identity_by_path.get(source_path) != document_id
        ):
            raise BankCorpusSurveyError("dataset role registry contains a malformed record")
        if document_id in role_by_document:
            raise BankCorpusSurveyError("dataset role registry repeats a document identity")
        role_by_document[document_id] = role
    for document in documents:
        document["dataset_role"] = role_by_document.get(document["document_id"])

    documents.sort(key=lambda record: record["relative_path"])
    represented = {record["bank"] for record in documents}
    if represented != set(bank_codes):
        raise BankCorpusSurveyError("source registry does not represent every registered bank")

    wave_policy = policy["wave_1"]
    excluded_roles = set(wave_policy["exclude_dataset_roles"])
    selected: list[dict[str, Any]] = []
    for bank in bank_codes:
        candidates = [
            record
            for record in documents
            if record["bank"] == bank
            and record["dataset_role"] not in excluded_roles
            and record["filename_metadata"]["document_kind"] == "FULL_FINANCIAL_STATEMENT_CANDIDATE"
        ]
        if not candidates:
            raise BankCorpusSurveyError(f"Wave 1 has no eligible financial statement for {bank}")
        ranked = sorted(
            candidates,
            key=lambda record: _selection_key(
                record,
                preferred_year=wave_policy["preferred_year"],
                preferred_period=wave_policy["preferred_period"],
                scope_preference=wave_policy["scope_preference"],
                assurance_preference=wave_policy["assurance_preference"],
            ),
        )
        chosen = ranked[0]
        metadata = chosen["filename_metadata"]
        chosen_key = _selection_key(
            chosen,
            preferred_year=wave_policy["preferred_year"],
            preferred_period=wave_policy["preferred_period"],
            scope_preference=wave_policy["scope_preference"],
            assurance_preference=wave_policy["assurance_preference"],
        )
        selected.append(
            {
                "bank": bank,
                "document_id": chosen["document_id"],
                "sha256": chosen["sha256"],
                "size_bytes": chosen["size_bytes"],
                "relative_path": chosen["relative_path"],
                "dataset_role": chosen["dataset_role"],
                "filename_metadata": metadata,
                "selection_status": wave_policy["selection_status"],
                "selection_rationale_code": (
                    "PRIMARY_COMPARABLE_VI_Q2_2026_CONSOLIDATED"
                    if (
                        chosen["year"] == wave_policy["preferred_year"]
                        and metadata["reporting_period_hint"] == wave_policy["preferred_period"]
                        and metadata["language_hint"] == wave_policy["preferred_language"]
                        and metadata["scope_hint"] == wave_policy["scope_preference"][0]
                    )
                    else "FALLBACK_Q2_2026_SEPARATE_SCOPE"
                    if (
                        chosen["year"] == wave_policy["preferred_year"]
                        and metadata["reporting_period_hint"] == wave_policy["preferred_period"]
                        and metadata["language_hint"] == wave_policy["preferred_language"]
                        and metadata["scope_hint"] == "SEPARATE"
                    )
                    else "FALLBACK_Q2_2026_SCOPE_UNKNOWN"
                    if (
                        chosen["year"] == wave_policy["preferred_year"]
                        and metadata["reporting_period_hint"] == wave_policy["preferred_period"]
                        and metadata["language_hint"] == wave_policy["preferred_language"]
                        and metadata["scope_hint"] == "UNKNOWN"
                    )
                    else "REUSED_REGISTERED_DEVELOPMENT_EVIDENCE_AFTER_METADATA_TIE"
                    if chosen["dataset_role"] == "LOGIC_DEVELOPMENT"
                    else "EXPLICIT_METADATA_FALLBACK"
                ),
                "selection_rationale": [
                    "one source-first representative is selected for every registered bank",
                    "preferred year and period are evaluated before PDF content or source type",
                    "Vietnamese and consolidated presentation are preferred when registered",
                    "an explicitly marked fallback is used when the preferred variant is absent",
                    "UNTOUCHED_HOLDOUT documents are excluded",
                    "a registered development input is reused only after preferred metadata ties",
                    "schema labels, prior mappings, bank-specific parser rules, and PDF ease are unused",
                ],
                "preferred_variant_matched": {
                    "year": chosen["year"] == wave_policy["preferred_year"],
                    "period": metadata["reporting_period_hint"] == wave_policy["preferred_period"],
                    "language": metadata["language_hint"] == wave_policy["preferred_language"],
                    "scope": metadata["scope_hint"] == wave_policy["scope_preference"][0],
                },
                "source_type_used_for_selection": False,
                "eligible_candidate_count": len(candidates),
                "selection_rank": 1,
                "selection_key": list(chosen_key),
            }
        )

    def counts(records: list[dict[str, Any]], field: str) -> dict[str, int]:
        return dict(sorted(Counter(str(record[field]) for record in records).items()))

    filename_vocabularies = {
        "document_kind": (
            "FULL_FINANCIAL_STATEMENT_CANDIDATE",
            "SUPPORTING_OR_PARTIAL_DOCUMENT",
            "UNCLASSIFIED_DOCUMENT_KIND",
        ),
        "scope_hint": ("CONSOLIDATED", "SEPARATE", "UNKNOWN", "AMBIGUOUS"),
        "reporting_period_hint": (
            "ANNUAL",
            "H1",
            "Q1",
            "Q2",
            "Q3",
            "Q4",
            "UNKNOWN",
            "AMBIGUOUS",
        ),
        "assurance_hint": (
            "AUDITED",
            "REVIEWED",
            "UNAUDITED",
            "UNKNOWN",
            "AMBIGUOUS",
        ),
        "language_hint": ("VI", "EN", "BILINGUAL_OR_AMBIGUOUS", "UNKNOWN"),
        "source_type_hint": (
            "SEARCHABLE_FILENAME_HINT",
            "UNASSESSED_REQUIRES_PDF_INSPECTION",
        ),
    }

    def filename_counts_for(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        for field, vocabulary in filename_vocabularies.items():
            observed = Counter(record["filename_metadata"][field] for record in records)
            result[field] = {value: observed[value] for value in vocabulary}
        return result

    filename_counts = filename_counts_for(documents)
    selected_filename_counts = filename_counts_for(selected)
    unique_hashes = {record["sha256"] for record in documents}
    duplicate_content_group_count = sum(count > 1 for count in content_counts.values())
    bank_year_counts: dict[str, dict[str, int]] = {}
    for bank in bank_codes:
        observed = Counter(record["year"] for record in documents if record["bank"] == bank)
        bank_year_counts[bank] = {str(year): observed[year] for year in sorted(observed)}
    selection_projection = [
        {
            key: record[key]
            for key in ("bank", "document_id", "sha256", "size_bytes", "relative_path")
        }
        for record in selected
    ]
    selection_projection_bytes = _canonical_json_bytes(selection_projection)
    selection_reason_counts = dict(
        sorted(Counter(record["selection_rationale_code"] for record in selected).items())
    )
    selection_role_counts = dict(
        sorted(Counter(record["dataset_role"] or "UNASSIGNED" for record in selected).items())
    )
    implementation_path = _resolve_under_root(
        project_root,
        IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        "bank corpus survey implementation",
    )
    return {
        "format_version": policy["output"]["format"],
        "policy": policy["policy"],
        "claim_boundary": policy["claim_boundary"],
        "status": "COMPLETE_REGISTERED_BANK_PDF_METADATA_INVENTORY",
        "inputs": [
            {
                "kind": name.upper(),
                "path": policy["inputs"][name],
                "sha256": sha256_bytes(input_bytes[name]),
                "size_bytes": len(input_bytes[name]),
            }
            for name in sorted(policy["inputs"])
        ],
        "implementation": {
            "path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
            "sha256": sha256_file(implementation_path),
            "policy_path": POLICY_RELATIVE_PATH.as_posix(),
            "policy_sha256": sha256_file(project_root / POLICY_RELATIVE_PATH),
        },
        "accounting": {
            "registered_bank_count": len(bank_codes),
            "registered_pdf_path_count": len(documents),
            "unique_pdf_content_count": len(unique_hashes),
            "duplicate_content_group_count": duplicate_content_group_count,
            "duplicate_extra_path_count": len(documents) - len(unique_hashes),
            "registered_pdf_bytes": sum(record["size_bytes"] for record in documents),
            "bank_path_counts": counts(documents, "bank"),
            "year_path_counts": counts(documents, "year"),
            "bank_year_path_counts": bank_year_counts,
            "filename_derived_counts": filename_counts,
            "filename_metadata_authoritative": False,
            "source_type_assessment_status": "PENDING_PDF_INSPECTION",
            "s3_parity_status": "OUTSIDE_THIS_ARTIFACT_CLAIM",
        },
        "wave_1": {
            "status": "COMPLETE_WAVE_1_SELECTION_PENDING_SOURCE_SURVEY",
            "strategy": (
                "ONE_DOCUMENT_PER_BANK_PREFERRED_VIETNAMESE_Q2_2026_"
                "CONSOLIDATED_WITH_EXPLICIT_FALLBACKS"
            ),
            "selected_bank_count": len(selected),
            "selected_document_count": len(selected),
            "selected_document_bytes": sum(record["size_bytes"] for record in selected),
            "selection_receipt_sha256": sha256_bytes(selection_projection_bytes),
            "selection_receipt_size_bytes": len(selection_projection_bytes),
            "selection_rationale_counts": selection_reason_counts,
            "selected_dataset_role_counts": selection_role_counts,
            "filename_derived_counts": selected_filename_counts,
            "source_type_used_for_selection": False,
            "source_profiled_by_this_artifact": 0,
            "structurally_surveyed_by_this_artifact": 0,
            "source_accounted_statement_blocks_by_this_artifact": 0,
            "selected_documents": selected,
        },
        "documents": documents,
    }


def _classify_source_route(
    *,
    page_count: int,
    substantive_extracted_text_pages: int,
    substantive_nonzero_alpha_text_pages: int,
    displayed_image_pages: int,
    dominant_raster_pages: int,
) -> str:
    if (
        page_count <= 0
        or substantive_extracted_text_pages < 0
        or substantive_extracted_text_pages > page_count
        or substantive_nonzero_alpha_text_pages < 0
        or substantive_nonzero_alpha_text_pages > substantive_extracted_text_pages
        or displayed_image_pages < 0
        or displayed_image_pages > page_count
        or dominant_raster_pages < 0
        or dominant_raster_pages > displayed_image_pages
    ):
        raise BankCorpusSurveyError("PDF page-evidence counts are invalid")
    if substantive_extracted_text_pages == page_count and dominant_raster_pages == page_count:
        return "SEARCHABLE_OVER_IMAGE_REQUIRES_GHOST_TEXT_VALIDATION"
    if substantive_nonzero_alpha_text_pages == page_count:
        return "NATIVE_SEARCHABLE_ROUTE"
    if substantive_nonzero_alpha_text_pages == 0 and dominant_raster_pages == page_count:
        return "SCAN_ROUTE"
    if substantive_nonzero_alpha_text_pages == 0:
        return "UNRESOLVED_SOURCE_ROUTE"
    return "MIXED_PAGE_HYBRID_ROUTE"


def build_wave_one_source_profile(project_root: Path, policy_path: Path) -> dict[str, Any]:
    import fitz

    project_root = project_root.resolve()
    policy = load_bank_corpus_survey_policy(policy_path, project_root)
    inventory = build_bank_corpus_inventory(project_root, policy_path)
    threshold = policy["source_profile"]["substantive_text_layer_min_non_whitespace_chars"]
    dominant_raster_threshold = policy["source_profile"]["dominant_raster_min_page_coverage"]
    profiles: list[dict[str, Any]] = []
    for selected in inventory["wave_1"]["selected_documents"]:
        source_path = _resolve_under_root(
            project_root, selected["relative_path"], "Wave 1 source PDF"
        )
        if source_path.is_symlink() or not source_path.is_file():
            raise BankCorpusSurveyError(
                f"Wave 1 source PDF is not a regular local file: {selected['relative_path']}"
            )
        source_bytes = _read_stable_bytes(source_path, "Wave 1 source PDF")
        if (
            len(source_bytes) != selected["size_bytes"]
            or sha256_bytes(source_bytes) != selected["sha256"]
        ):
            raise BankCorpusSurveyError(
                f"Wave 1 source PDF identity drifted: {selected['relative_path']}"
            )
        try:
            document = fitz.open(stream=source_bytes, filetype="pdf")
        except Exception as error:
            raise BankCorpusSurveyError(
                f"Wave 1 source PDF cannot be opened: {selected['relative_path']}"
            ) from error
        try:
            if not document.is_pdf or document.page_count <= 0:
                raise BankCorpusSurveyError(
                    f"Wave 1 source is not a nonempty PDF: {selected['relative_path']}"
                )
            page_evidence: list[dict[str, Any]] = []
            for page_index in range(document.page_count):
                page = document.load_page(page_index)
                raw_text = page.get_text("rawdict")
                text_spans = [
                    span
                    for block in raw_text.get("blocks", [])
                    if block.get("type") == 0
                    for line in block.get("lines", [])
                    for span in line.get("spans", [])
                ]
                alpha_span_counts = Counter(str(span.get("alpha")) for span in text_spans)
                alpha_character_counts = Counter()
                non_whitespace_chars = 0
                for span in text_spans:
                    span_non_whitespace_chars = sum(
                        isinstance(character.get("c"), str) and not character["c"].isspace()
                        for character in span.get("chars", ())
                    )
                    non_whitespace_chars += span_non_whitespace_chars
                    alpha_character_counts[str(span.get("alpha"))] += span_non_whitespace_chars
                zero_alpha_character_count = alpha_character_counts["0"]
                nonzero_alpha_character_count = sum(
                    count
                    for alpha, count in alpha_character_counts.items()
                    if alpha.isdigit() and int(alpha) > 0
                )
                image_info = page.get_image_info()
                page_area = page.rect.width * page.rect.height
                maximum_image_coverage = 0.0
                for image in image_info:
                    bbox = fitz.Rect(image["bbox"]) & page.rect
                    bbox_area = max(0.0, bbox.width) * max(0.0, bbox.height)
                    maximum_image_coverage = max(
                        maximum_image_coverage,
                        bbox_area / page_area if page_area else 0.0,
                    )
                substantive_extracted = non_whitespace_chars >= threshold
                dominant_displayed_raster = maximum_image_coverage >= dominant_raster_threshold
                route_quadrant = (
                    "TEXT_LAYER_AND_DOMINANT_RASTER"
                    if substantive_extracted and dominant_displayed_raster
                    else "TEXT_LAYER_AND_NONDOMINANT_RASTER"
                    if substantive_extracted
                    else "NO_TEXT_LAYER_AND_DOMINANT_RASTER"
                    if dominant_displayed_raster
                    else "NO_TEXT_LAYER_AND_NONDOMINANT_RASTER"
                )
                page_evidence.append(
                    {
                        "page_number": page_index + 1,
                        "extractable_text_layer_non_whitespace_char_count": (non_whitespace_chars),
                        "has_any_extractable_text_layer": non_whitespace_chars > 0,
                        "substantive_extractable_text_layer": substantive_extracted,
                        "substantive_nonzero_alpha_text_layer": (
                            substantive_extracted and nonzero_alpha_character_count >= threshold
                        ),
                        "substantive_zero_alpha_text_layer": (
                            substantive_extracted and zero_alpha_character_count >= threshold
                        ),
                        "text_layer_span_count_by_alpha": dict(sorted(alpha_span_counts.items())),
                        "text_layer_character_count_by_alpha": dict(
                            sorted(alpha_character_counts.items())
                        ),
                        "displayed_image_count": len(image_info),
                        "has_displayed_image": bool(image_info),
                        "maximum_displayed_image_page_coverage": round(maximum_image_coverage, 8),
                        "has_dominant_displayed_raster": dominant_displayed_raster,
                        "source_route_quadrant": route_quadrant,
                        "no_extracted_text_or_displayed_image": non_whitespace_chars == 0
                        and not image_info,
                    }
                )
        finally:
            document.close()
        page_count = len(page_evidence)
        any_text_pages = sum(page["has_any_extractable_text_layer"] for page in page_evidence)
        extracted_text_pages = sum(
            page["substantive_extractable_text_layer"] for page in page_evidence
        )
        nonzero_alpha_text_pages = sum(
            page["substantive_nonzero_alpha_text_layer"] for page in page_evidence
        )
        zero_alpha_text_pages = sum(
            page["substantive_zero_alpha_text_layer"] for page in page_evidence
        )
        image_pages = sum(page["has_displayed_image"] for page in page_evidence)
        dominant_raster_pages = sum(page["has_dominant_displayed_raster"] for page in page_evidence)
        no_evidence_pages = sum(
            page["no_extracted_text_or_displayed_image"] for page in page_evidence
        )
        route = _classify_source_route(
            page_count=page_count,
            substantive_extracted_text_pages=extracted_text_pages,
            substantive_nonzero_alpha_text_pages=nonzero_alpha_text_pages,
            displayed_image_pages=image_pages,
            dominant_raster_pages=dominant_raster_pages,
        )
        fingerprint_projection = {
            "page_count": page_count,
            "page_evidence": page_evidence,
            "source_route_recommendation": route,
            "substantive_text_layer_min_non_whitespace_chars": threshold,
            "dominant_raster_min_page_coverage": dominant_raster_threshold,
            "text_layer_visibility_proxy": policy["source_profile"]["text_layer_visibility_proxy"],
        }
        profiles.append(
            {
                "bank": selected["bank"],
                "document_id": selected["document_id"],
                "relative_path": selected["relative_path"],
                "sha256": selected["sha256"],
                "size_bytes": selected["size_bytes"],
                "selection_rationale_code": selected["selection_rationale_code"],
                "filename_metadata": selected["filename_metadata"],
                "source_profile_status": (
                    "SOURCE_ROUTE_PROFILE_COMPLETE_STRUCTURE_FINGERPRINT_PENDING"
                ),
                "source_route_recommendation": route,
                "page_count": page_count,
                "any_extractable_text_layer_page_count": any_text_pages,
                "substantive_extractable_text_layer_page_count": extracted_text_pages,
                "substantive_nonzero_alpha_text_layer_page_count": (nonzero_alpha_text_pages),
                "substantive_zero_alpha_text_layer_page_count": zero_alpha_text_pages,
                "displayed_image_page_count": image_pages,
                "dominant_displayed_raster_page_count": dominant_raster_pages,
                "no_extracted_text_or_displayed_image_page_count": no_evidence_pages,
                "page_evidence": page_evidence,
                "source_route_fingerprint_sha256": sha256_bytes(
                    _canonical_json_bytes(fingerprint_projection)
                ),
                "source_route_is_canonical_accounting_identity": False,
                "source_route_recommendation_is_candidate": True,
                "visibility_and_render_validation_status": "NOT_RUN",
            }
        )

    route_observed = Counter(profile["source_route_recommendation"] for profile in profiles)
    route_counts = {
        value: route_observed[value] for value in policy["source_profile"]["route_vocabulary"]
    }
    route_quadrant_observed = Counter(
        page["source_route_quadrant"] for profile in profiles for page in profile["page_evidence"]
    )
    route_quadrant_counts = {
        value: route_quadrant_observed[value]
        for value in (
            "TEXT_LAYER_AND_DOMINANT_RASTER",
            "TEXT_LAYER_AND_NONDOMINANT_RASTER",
            "NO_TEXT_LAYER_AND_DOMINANT_RASTER",
            "NO_TEXT_LAYER_AND_NONDOMINANT_RASTER",
        )
    }
    implementation_path = _resolve_under_root(
        project_root,
        IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        "bank corpus survey implementation",
    )
    return {
        "format_version": policy["output"]["source_profile_format"],
        "policy": policy["policy"],
        "claim_boundary": (
            "SELECTED_WAVE_1_PDF_PAGE_EVIDENCE_AND_SOURCE_ROUTE_RECOMMENDATIONS_ONLY"
        ),
        "status": "COMPLETE_WAVE_1_SOURCE_ROUTE_PROFILE_STRUCTURE_SURVEY_PENDING",
        "selection_receipt_sha256": inventory["wave_1"]["selection_receipt_sha256"],
        "selection_source_type_used": False,
        "implementation": {
            "path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
            "sha256": sha256_file(implementation_path),
            "policy_path": POLICY_RELATIVE_PATH.as_posix(),
            "policy_sha256": sha256_file(project_root / POLICY_RELATIVE_PATH),
            "pymupdf_binding_version": fitz.VersionBind,
            "pymupdf_runtime_versions": list(fitz.version),
        },
        "accounting": {
            "selected_document_count": len(profiles),
            "source_profiled_document_count": len(profiles),
            "structurally_surveyed_document_count": 0,
            "source_accounted_statement_block_count": 0,
            "source_accounted_visible_row_count": 0,
            "source_accounted_visible_value_cell_count": 0,
            "total_pdf_page_count": sum(profile["page_count"] for profile in profiles),
            "any_extractable_text_layer_page_count": sum(
                profile["any_extractable_text_layer_page_count"] for profile in profiles
            ),
            "substantive_extractable_text_layer_page_count": sum(
                profile["substantive_extractable_text_layer_page_count"] for profile in profiles
            ),
            "substantive_nonzero_alpha_text_layer_page_count": sum(
                profile["substantive_nonzero_alpha_text_layer_page_count"] for profile in profiles
            ),
            "substantive_zero_alpha_text_layer_page_count": sum(
                profile["substantive_zero_alpha_text_layer_page_count"] for profile in profiles
            ),
            "displayed_image_page_count": sum(
                profile["displayed_image_page_count"] for profile in profiles
            ),
            "dominant_displayed_raster_page_count": sum(
                profile["dominant_displayed_raster_page_count"] for profile in profiles
            ),
            "no_extracted_text_or_displayed_image_page_count": sum(
                profile["no_extracted_text_or_displayed_image_page_count"] for profile in profiles
            ),
            "source_route_counts": route_counts,
            "source_route_page_quadrant_counts": route_quadrant_counts,
            "ocr_executed": False,
            "schema_used": False,
            "canonical_mapping_attempted": False,
        },
        "profiles": profiles,
    }


def publish_bank_corpus_inventory(
    project_root: Path,
    *,
    policy_path: Path | None = None,
    output_path: Path | None = None,
) -> tuple[Path, str, int]:
    project_root = project_root.resolve()
    policy_path = (policy_path or project_root / POLICY_RELATIVE_PATH).resolve()
    output_path = (output_path or project_root / OUTPUT_RELATIVE_PATH).resolve()
    expected_root = (project_root / "output/development/bank-corpus-survey-v1").resolve()
    if output_path.parent != expected_root or not output_path.is_relative_to(project_root):
        raise BankCorpusSurveyError("bank corpus inventory output location is invalid")
    payload = build_bank_corpus_inventory(project_root, policy_path)
    encoded = _canonical_json_bytes(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(output_path, flags, 0o644)
    except FileExistsError as error:
        raise BankCorpusSurveyError("bank corpus inventory output already exists") from error
    try:
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
        identity = os.fstat(descriptor)
        if not stat.S_ISREG(identity.st_mode) or identity.st_size != len(encoded):
            raise BankCorpusSurveyError("bank corpus inventory publication identity drifted")
    except Exception:
        os.close(descriptor)
        output_path.unlink(missing_ok=True)
        raise
    os.close(descriptor)
    return output_path, sha256_bytes(encoded), len(encoded)


def publish_wave_one_source_profile(
    project_root: Path,
    *,
    policy_path: Path | None = None,
    output_path: Path | None = None,
) -> tuple[Path, str, int]:
    project_root = project_root.resolve()
    policy_path = (policy_path or project_root / POLICY_RELATIVE_PATH).resolve()
    output_path = (output_path or project_root / SOURCE_PROFILE_OUTPUT_RELATIVE_PATH).resolve()
    expected_root = (project_root / "output/development/bank-corpus-survey-v1").resolve()
    if output_path.parent != expected_root or not output_path.is_relative_to(project_root):
        raise BankCorpusSurveyError("bank corpus source-profile output location is invalid")
    payload = build_wave_one_source_profile(project_root, policy_path)
    encoded = _canonical_json_bytes(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(output_path, flags, 0o644)
    except FileExistsError as error:
        raise BankCorpusSurveyError("bank corpus source-profile output already exists") from error
    try:
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
        identity = os.fstat(descriptor)
        if not stat.S_ISREG(identity.st_mode) or identity.st_size != len(encoded):
            raise BankCorpusSurveyError("bank corpus source-profile publication drifted")
    except Exception:
        os.close(descriptor)
        output_path.unlink(missing_ok=True)
        raise
    os.close(descriptor)
    return output_path, sha256_bytes(encoded), len(encoded)


__all__ = [
    "BankCorpusSurveyError",
    "IMPLEMENTATION_RELATIVE_PATH",
    "OUTPUT_RELATIVE_PATH",
    "POLICY_RELATIVE_PATH",
    "SOURCE_PROFILE_OUTPUT_RELATIVE_PATH",
    "_classify_source_route",
    "build_bank_corpus_inventory",
    "build_wave_one_source_profile",
    "load_bank_corpus_survey_policy",
    "publish_bank_corpus_inventory",
    "publish_wave_one_source_profile",
]
