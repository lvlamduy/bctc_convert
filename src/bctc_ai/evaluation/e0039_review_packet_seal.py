"""Hash-seal the immutable, answer-free E-0039 review evidence packet.

This phase reads only the committed packet controls/implementations and the one
already captured packet.  It never reopens source evidence, imports prior
review answers, rebuilds mapping evidence, or captures a replacement packet.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, cast

from bctc_ai.evaluation.e0038_exact_mapping import (
    E0038ExactMappingError,
    _assert_tracked_record_matches_head,
    _assert_unchanged,
    _canonical_path,
    _clean_git_commit,
    _decode_control,
    _exclusive_publish_json,
    _git_bytes,
    _read_stable_file,
    _sanitized_git_environment,
    _StableFile,
    _verify_record,
)
from bctc_ai.evaluation.e0039_review_packet import (
    _ACCESS_CONTRACT as _PACKET_ACCESS_CONTROL,
)
from bctc_ai.evaluation.e0039_review_packet import (
    _CONTROL_KEYS as _PACKET_CONTROL_KEYS,
)
from bctc_ai.evaluation.e0039_review_packet import (
    _EXPECTED_FROZEN_INPUTS as _PACKET_EXPECTED_FROZEN_INPUTS,
)
from bctc_ai.evaluation.e0039_review_packet import (
    _IMPLEMENTATION_PATHS as _PACKET_IMPLEMENTATION_PATHS,
)
from bctc_ai.evaluation.e0039_review_packet import (
    _PACKET_CONTRACT as _PACKET_CAPTURE_CONTRACT,
)
from bctc_ai.evaluation.e0039_review_packet import (
    _PUBLICATION_CONTRACT as _PACKET_PUBLICATION_CONTRACT,
)
from bctc_ai.evaluation.e0039_review_packet import (
    _RESOURCE_CAPS as _PACKET_RESOURCE_CAPS,
)
from bctc_ai.evaluation.e0039_review_packet import (
    ALIAS_RESPONSE_TEMPLATE,
    ALIAS_RESPONSE_VOCABULARY,
    ALIAS_ROW_BINDINGS,
    PACKET_STATE,
    ROW_RESPONSE_TEMPLATE,
    ROW_RESPONSE_VOCABULARY,
    UNSELECTED_ROW_IDS,
    E0039ReviewPacketError,
    _encoded_packet_json,
    _strict_json,
    _validate_packet_payload,
)
from bctc_ai.evaluation.e0039_review_packet import (
    CONTROL_RELATIVE_PATH as PACKET_CONTROL_RELATIVE_PATH,
)
from bctc_ai.evaluation.e0039_review_packet import (
    OUTPUT_RELATIVE_PATH as PACKET_RELATIVE_PATH,
)
from bctc_ai.evaluation.e0039_review_packet import (
    READY_STATE as PACKET_CONTROL_READY_STATE,
)


class E0039ReviewPacketSealError(RuntimeError):
    """Raised when the E-0039 pre-decision packet cannot be sealed safely."""


CONTROL_RELATIVE_PATH = Path("config/experiments/e0039-mbb-cdkt-review-packet-seal.yaml")
OUTPUT_RELATIVE_PATH = Path("docs/experiments/E-0039-mbb-cdkt-review-packet-seal.json")
SEAL_BUILDER_RELATIVE_PATH = Path("src/bctc_ai/evaluation/e0039_review_packet_seal.py")
CAPTURE_SCRIPT_RELATIVE_PATH = Path(
    "scripts/experiments/capture_e0039_mbb_cdkt_review_packet_seal.py"
)

PACKET_CAPTURE_GIT_COMMIT = "35d02d62e96b2fa449f4eb8ee6a13982a5f2fe75"
READY_STATE = "READY_FOR_E0039_PREDECISION_REVIEW_PACKET_HASH_SEAL"
SEAL_STATE = "E0039_PREDECISION_REVIEW_PACKET_HASH_SEALED_BEFORE_RESPONSE_ACCESS"

PACKET_ARTIFACT = {
    "path": PACKET_RELATIVE_PATH.as_posix(),
    "sha256": "04c6b0509713f46423b03857a5e509d36cfa95d9ffd34bbe981f564915cdf93d",
    "size_bytes": 74_601,
}
PACKET_CONTROL_ARTIFACT = {
    "path": PACKET_CONTROL_RELATIVE_PATH.as_posix(),
    "sha256": "c92f37b177afba90e97683296119fa783a58ed959054aabb3476293d21c9927a",
    "size_bytes": 8_361,
}
PACKET_INPUT_ARTIFACTS_SHA256 = "bac9d64913017fee94e6362af8fe49b0155b526b9d1ee3eb6cbf71f0d0734a13"
PACKET_EVIDENCE_IDENTITY_SHA256 = "ef3608a824e476a0982477bdc3ae7b31a68fcaa5ecd9ea3f4c51134c0a161260"
PACKET_ACCESS_CONTRACT_SHA256 = "6a1a2396d00dc14b6a4d34b73d570f2ae36ba7046960a037c03619575d843bd1"
PACKET_BLANK_RESPONSE_CONTRACTS_SHA256 = (
    "5765fa5f61703ad360ff8260a97df879ae1475ef922c1aa4e6b105a3774ebf72"
)
PACKET_AUTHORITY_SHA256 = "d435b75649cc63948b4c727f68a26b67eb418c0771191b199e2aa31cf891e4d5"
PACKET_EVIDENCE_SECTIONS_SHA256 = "a4cd5cb429d5894424c9e50fa8c559ef6ad042cafc940da73b4cd2ed0d831185"

_PACKET_INPUT_NAME_BY_IMPLEMENTATION = {
    "packet_builder": "packet_builder",
    "capture_script": "packet_capture_script",
    "source_structure_validator": "source_structure_validator",
    "e0037_mapping_validator": "e0037_mapping_validator",
    "hardened_io_and_e0038_payload_validator": ("hardened_io_and_e0038_payload_validator"),
}

_EXPECTED_FROZEN_INPUTS: dict[str, dict[str, Any]] = {
    "packet_control": PACKET_CONTROL_ARTIFACT,
    "packet_builder": {
        "path": "src/bctc_ai/evaluation/e0039_review_packet.py",
        "sha256": "9049ae53faf8c8cbd19133020c9d23d80716cd6b9acacd0f7417cd21596814fe",
        "size_bytes": 134_406,
    },
    "packet_capture_script": {
        "path": "scripts/experiments/capture_e0039_mbb_cdkt_review_packet.py",
        "sha256": "5df83d983dd6724e911ed47a76aba2fdcc72af8086bfcd2ec153ecfe1495d576",
        "size_bytes": 1_632,
    },
    "source_structure_validator": {
        "path": "src/bctc_ai/evaluation/e0037_evidence_assembly.py",
        "sha256": "cbef18c15ca23bc08b3539144f89cd8de201194cb29f610fe44d2ef325ffa2c3",
        "size_bytes": 56_692,
    },
    "e0037_mapping_validator": {
        "path": "src/bctc_ai/evaluation/e0037_sealed_mapping.py",
        "sha256": "de92349a1efdd0bc3cc5ab78d4651bf7987006d3883d15bc9a4e1a1753862e04",
        "size_bytes": 133_670,
    },
    "hardened_io_and_e0038_payload_validator": {
        "path": "src/bctc_ai/evaluation/e0038_exact_mapping.py",
        "sha256": "ac1ba96456f9541cd3612b0763dc521f6c916681bafe455e330643ab17739a04",
        "size_bytes": 113_104,
    },
    "packet": PACKET_ARTIFACT,
}

_FROZEN_PATHS = {name: Path(record["path"]) for name, record in _EXPECTED_FROZEN_INPUTS.items()}
_IMPLEMENTATION_PATHS = {
    "seal_builder": SEAL_BUILDER_RELATIVE_PATH,
    "capture_script": CAPTURE_SCRIPT_RELATIVE_PATH,
}
_EXPECTED_OPENED_INPUT_PATHS = [
    CONTROL_RELATIVE_PATH.as_posix(),
    *[path.as_posix() for path in _IMPLEMENTATION_PATHS.values()],
    *[path.as_posix() for path in _FROZEN_PATHS.values()],
]

_PACKET_SUMMARY = {
    "packet_state": PACKET_STATE,
    "row_count": 6,
    "row_ids": list(UNSELECTED_ROW_IDS),
    "row_decision_status": "NOT_STARTED_BLANK_RESPONSE_REQUIRED",
    "row_authority_required": "INDEPENDENT_ROW_ADJUDICATOR",
    "alias_candidate_count": 2,
    "alias_candidate_ids": [item[0] for item in ALIAS_ROW_BINDINGS],
    "alias_decision_status": "NOT_STARTED_BLANK_RESPONSE_REQUIRED",
    "alias_authority_required": "REVIEW_INDEPENDENT_SCHEMA_STEWARD",
    "row_and_alias_authorities_separate": True,
    "row_response_template": copy.deepcopy(ROW_RESPONSE_TEMPLATE),
    "row_response_vocabulary": copy.deepcopy(ROW_RESPONSE_VOCABULARY),
    "alias_response_template": copy.deepcopy(ALIAS_RESPONSE_TEMPLATE),
    "alias_response_vocabulary": copy.deepcopy(ALIAS_RESPONSE_VOCABULARY),
    "all_response_template_values_null": True,
    "recommended_or_default_response_fields_present": False,
    "input_artifacts_sha256": PACKET_INPUT_ARTIFACTS_SHA256,
    "evidence_identity_sha256": PACKET_EVIDENCE_IDENTITY_SHA256,
    "access_contract_sha256": PACKET_ACCESS_CONTRACT_SHA256,
    "blank_response_contracts_sha256": PACKET_BLANK_RESPONSE_CONTRACTS_SHA256,
    "authority_sha256": PACKET_AUTHORITY_SHA256,
    "evidence_sections_sha256": PACKET_EVIDENCE_SECTIONS_SHA256,
}

_SEAL_CONTRACT = {
    "packet_path": PACKET_RELATIVE_PATH.as_posix(),
    "packet_required_state": PACKET_STATE,
    "packet_capture_git_commit": PACKET_CAPTURE_GIT_COMMIT,
    "packet_capture_commit_must_be_ancestor_of_seal_commit": True,
    "packet_control_and_implementation_must_match_capture_commit_and_head": True,
    "seal_state": SEAL_STATE,
    "exact_inventory_file_count": 1,
    "packet_encoding": "UTF8_JSON_SORTED_KEYS_COMPACT_NO_NAN_NO_DUPLICATE_KEYS_V1",
    "seal_encoding": "UTF8_JSON_SORTED_KEYS_INDENT2_NEWLINE_NO_NAN_NO_DUPLICATE_KEYS_V1",
    "packet_validation_invocation_count": 2,
    "packet_rebuild_or_recapture_allowed": False,
    "exact_row_count": 6,
    "exact_alias_candidate_count": 2,
    "blank_response_contract_required": True,
    "separate_row_and_alias_authority_required": True,
}

_ACCESS_CONTROL = {
    "exact_unique_direct_read_path_count": 10,
    "packet_control_and_implementation_opened": True,
    "packet_opened_after_control_and_implementation_validation": True,
    "packet_evidence_inputs_reopened": False,
    "prior_review_module_import_allowed": False,
    "prior_review_module_loaded": False,
    "process_module_isolation_rechecked_before_publication": True,
    "prior_review_artifact_or_answer_opened": False,
    "review_or_steward_response_opened": False,
    "full_page_render_opened": False,
    "numeric_or_accounting_artifact_opened": False,
    "history_or_mongodb_artifact_opened": False,
    "qwen_raw_rejected_or_token_output_opened": False,
    "holdout_artifact_opened": False,
    "network_or_s3_write_allowed": False,
    "packet_builder_or_capture_invocation_count": 0,
    "mapping_invocation_count": 0,
    "review_or_steward_decision_invocation_count": 0,
}

_PACKET_ACCESS_RECEIPT = {
    **_ACCESS_CONTROL,
    "opened_input_paths": _EXPECTED_OPENED_INPUT_PATHS,
}

_RESOURCE_CAPS = {
    "maximum_control_bytes": 256 * 1024,
    "maximum_implementation_bytes_each": 2 * 1024 * 1024,
    "maximum_packet_bytes": 2 * 1024 * 1024,
    "maximum_seal_bytes": 64 * 1024,
    "maximum_total_direct_input_bytes": 4 * 1024 * 1024,
    "exact_unique_direct_read_path_count": 10,
}

_PUBLICATION_CONTRACT = {
    "canonical_paths_only": True,
    "clean_git_required_before_any_input_read": True,
    "clean_git_required_immediately_before_publication": True,
    "capture_commit_ancestor_of_seal_commit_required": True,
    "tracked_control_and_implementation_head_binding_required": True,
    "tracked_packet_mechanism_capture_commit_binding_required": True,
    "stable_nofollow_reads_required": True,
    "all_direct_inputs_rechecked_before_publication": True,
    "atomic_exclusive_no_overwrite": True,
    "post_link_canonical_parent_and_file_revalidation_required": True,
    "formal_seal_requires_committed_mechanism": True,
}

_AUTHORITY = {
    "dataset_role": "CALIBRATION_ONLY",
    "exact_packet_hash_identity": True,
    "blank_predecision_contract_identity": True,
    "row_adjudication_completed": False,
    "schema_steward_decision_completed": False,
    "schema_alias_approval": False,
    "schema_authority": False,
    "automatic_mapping_adoption": False,
    "mapping_accuracy": False,
    "numeric_period_or_unit": False,
    "accounting_or_excel": False,
    "history_or_mongodb": False,
    "holdout_or_production": False,
    "s3_durability_registration": False,
}

_CLAIM_BOUNDARY = (
    "This calibration-only artifact hash-seals exactly one immutable E-0039 "
    "answer-free pre-decision evidence packet. It binds the packet capture commit, "
    "canonical packet bytes, exact six-row and separate two-alias blank response "
    "contracts, and their independent authorities. It opens no packet source-evidence "
    "inputs or response answers and adds no row adjudication, schema-steward decision, "
    "alias approval, mapping adoption or accuracy, schema, numeric, period, unit, "
    "accounting, Excel, history, MongoDB, holdout, S3 durability, or production claim."
)

_CONTROL_KEYS = {
    "version",
    "experiment_id",
    "dataset_role",
    "design",
    "state",
    "frozen_inputs",
    "implementation",
    "seal_contract",
    "access_contract",
    "resource_caps",
    "publication",
    "output",
    "claim_boundary",
}

_GIT_COMMIT = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_FORBIDDEN_REVIEW_MODULE_PREFIXES = (
    "bctc_ai.evaluation.e0038_reviewed_evaluation",
    "bctc_ai.evaluation.logical_row_label_review_evaluation",
    "bctc_ai.evaluation.qwen35_reviewed_evaluation",
    "bctc_ai.reference.human_review",
)
StableReader = Callable[..., _StableFile]


def _fail(label: str, exc: Exception) -> E0039ReviewPacketSealError:
    return E0039ReviewPacketSealError(f"{label}: {exc}")


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise E0039ReviewPacketSealError(f"{label} keyset drifted")
    return cast(dict[str, Any], value)


def _canonical_sha256(value: object) -> str:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise _fail("cannot encode canonical E-0039 seal projection", exc) from exc
    return hashlib.sha256(encoded).hexdigest()


def _assert_process_review_isolated() -> None:
    contaminated = sorted(
        name
        for name in sys.modules
        if any(
            name == prefix or name.startswith(f"{prefix}.")
            for prefix in _FORBIDDEN_REVIEW_MODULE_PREFIXES
        )
    )
    if contaminated:
        raise E0039ReviewPacketSealError(
            "E-0039 sealing process already materialized forbidden prior-review state"
        )


def _encoded_seal_json(payload: Mapping[str, Any]) -> bytes:
    try:
        return (
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise _fail("E-0039 seal is not canonical JSON data", exc) from exc


def _verified_record(
    reader: StableReader,
    root: Path,
    record: object,
    *,
    name: str,
    expected_path: Path,
    maximum_size: int,
) -> _StableFile:
    try:
        return _verify_record(
            reader,
            root,
            record,
            f"E-0039 packet seal {name}",
            expected_path=expected_path,
            maximum_size=maximum_size,
        )
    except E0038ExactMappingError as exc:
        raise _fail(f"cannot validate E-0039 packet seal {name}", exc) from exc


def _validate_control(
    root: Path,
    control: dict[str, Any],
    reader: StableReader,
) -> tuple[dict[str, dict[str, Any]], dict[str, _StableFile]]:
    if (
        set(control) != _CONTROL_KEYS
        or control.get("version") != 1
        or control.get("experiment_id") != "E-0039"
        or control.get("dataset_role") != "CALIBRATION"
        or control.get("design") != "SEPARATE_IMMUTABLE_PREDECISION_REVIEW_PACKET_HASH_SEAL"
        or control.get("state") != READY_STATE
    ):
        raise E0039ReviewPacketSealError("E-0039 packet seal control drifted")
    frozen = _exact_keys(
        control.get("frozen_inputs"),
        set(_EXPECTED_FROZEN_INPUTS),
        "E-0039 packet seal frozen inputs",
    )
    if frozen != _EXPECTED_FROZEN_INPUTS:
        raise E0039ReviewPacketSealError("E-0039 packet seal frozen inputs drifted")
    implementation = _exact_keys(
        control.get("implementation"),
        set(_IMPLEMENTATION_PATHS),
        "E-0039 packet seal implementation",
    )
    if (
        control.get("seal_contract") != _SEAL_CONTRACT
        or control.get("access_contract") != _ACCESS_CONTROL
        or control.get("resource_caps") != _RESOURCE_CAPS
        or control.get("publication") != _PUBLICATION_CONTRACT
        or control.get("output") != {"path": OUTPUT_RELATIVE_PATH.as_posix()}
        or control.get("claim_boundary") != _CLAIM_BOUNDARY
    ):
        raise E0039ReviewPacketSealError("E-0039 packet seal contract drifted")

    stable: dict[str, _StableFile] = {}
    for name, path in _IMPLEMENTATION_PATHS.items():
        stable[name] = _verified_record(
            reader,
            root,
            implementation[name],
            name=f"implementation {name}",
            expected_path=path,
            maximum_size=_RESOURCE_CAPS["maximum_implementation_bytes_each"],
        )
    return cast(dict[str, dict[str, Any]], frozen), stable


def _packet_implementation_records(
    frozen: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        packet_name: copy.deepcopy(frozen[_PACKET_INPUT_NAME_BY_IMPLEMENTATION[packet_name]])
        for packet_name in _PACKET_IMPLEMENTATION_PATHS
    }


def _validate_packet_control(
    control: Mapping[str, Any],
    frozen: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    expected_implementation = _packet_implementation_records(frozen)
    if (
        set(control) != _PACKET_CONTROL_KEYS
        or control.get("version") != 1
        or control.get("experiment_id") != "E-0039"
        or control.get("dataset_role") != "CALIBRATION"
        or control.get("state") != PACKET_CONTROL_READY_STATE
        or control.get("frozen_inputs") != _PACKET_EXPECTED_FROZEN_INPUTS
        or control.get("implementation") != expected_implementation
        or control.get("packet_contract") != _PACKET_CAPTURE_CONTRACT
        or control.get("access_contract") != _PACKET_ACCESS_CONTROL
        or control.get("resource_caps") != _PACKET_RESOURCE_CAPS
        or control.get("publication") != _PACKET_PUBLICATION_CONTRACT
        or control.get("output") != {"path": PACKET_RELATIVE_PATH.as_posix()}
    ):
        raise E0039ReviewPacketSealError("sealed E-0039 packet control drifted")
    return expected_implementation


def _assert_capture_commit_ancestor(
    root: Path,
    capture_commit: str,
    seal_commit: str,
) -> None:
    if _GIT_COMMIT.fullmatch(capture_commit) is None or _GIT_COMMIT.fullmatch(seal_commit) is None:
        raise E0039ReviewPacketSealError("E-0039 packet/seal Git identity is invalid")
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "merge-base",
            "--is-ancestor",
            capture_commit,
            seal_commit,
        ],
        cwd=root,
        check=False,
        capture_output=True,
        env=_sanitized_git_environment(),
    )
    if completed.returncode != 0:
        raise E0039ReviewPacketSealError(
            "E-0039 packet capture commit is not an ancestor of the seal commit"
        )


def _assert_record_matches_git_commit(
    root: Path,
    record: Mapping[str, Any],
    *,
    name: str,
    expected_path: Path,
    commit: str,
) -> None:
    validated = _exact_keys(
        record,
        {"path", "sha256", "size_bytes"},
        f"historical artifact record {name}",
    )
    sha256 = validated["sha256"]
    size_bytes = validated["size_bytes"]
    if (
        validated["path"] != expected_path.as_posix()
        or not isinstance(sha256, str)
        or _SHA256.fullmatch(sha256) is None
        or type(size_bytes) is not int
        or size_bytes < 0
    ):
        raise E0039ReviewPacketSealError(f"invalid historical artifact record: {name}")
    try:
        blob = _git_bytes(root, "cat-file", "blob", f"{commit}:{expected_path.as_posix()}")
    except E0038ExactMappingError as exc:
        raise _fail(f"cannot read historical packet mechanism blob {name}", exc) from exc
    if hashlib.sha256(blob).hexdigest() != sha256 or len(blob) != size_bytes:
        raise E0039ReviewPacketSealError(f"packet mechanism differs from capture commit: {name}")


def _head_bind(
    root: Path,
    record: Mapping[str, Any],
    *,
    name: str,
    path: Path,
    reader: StableReader,
) -> None:
    try:
        _assert_tracked_record_matches_head(
            root,
            record,
            name=f"E-0039 packet seal {name}",
            expected_path=path,
            reader=reader,
        )
    except E0038ExactMappingError as exc:
        raise _fail(f"cannot bind E-0039 packet seal {name} to Git HEAD", exc) from exc


def _packet_summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    row = cast(Mapping[str, Any], packet["row_review_packet"])
    alias = cast(Mapping[str, Any], packet["alias_steward_packet"])
    responses = cast(Mapping[str, Any], packet["blank_response_contracts"])
    return {
        "packet_state": packet["state"],
        "row_count": row["row_count"],
        "row_ids": copy.deepcopy(row["row_ids"]),
        "row_decision_status": row["decision_status"],
        "row_authority_required": row["authority_required"],
        "alias_candidate_count": alias["candidate_count"],
        "alias_candidate_ids": copy.deepcopy(alias["candidate_ids"]),
        "alias_decision_status": alias["decision_status"],
        "alias_authority_required": alias["authority_required"],
        "row_and_alias_authorities_separate": (
            row["authority_required"] != alias["authority_required"]
        ),
        "row_response_template": copy.deepcopy(
            cast(Mapping[str, Any], responses["row_adjudication"])["template"]
        ),
        "row_response_vocabulary": copy.deepcopy(
            cast(Mapping[str, Any], responses["row_adjudication"])["allowed_vocabulary"]
        ),
        "alias_response_template": copy.deepcopy(
            cast(Mapping[str, Any], responses["alias_stewardship"])["template"]
        ),
        "alias_response_vocabulary": copy.deepcopy(
            cast(Mapping[str, Any], responses["alias_stewardship"])["allowed_vocabulary"]
        ),
        "all_response_template_values_null": all(
            value is None
            for section in ("row_adjudication", "alias_stewardship")
            for value in cast(Mapping[str, Any], responses[section])["template"].values()
        ),
        "recommended_or_default_response_fields_present": any(
            token in key.casefold()
            for section in ("row_adjudication", "alias_stewardship")
            for key in cast(Mapping[str, Any], responses[section])
            for token in ("recommend", "default", "suggest")
        ),
        "input_artifacts_sha256": _canonical_sha256(packet["input_artifacts"]),
        "evidence_identity_sha256": _canonical_sha256(packet["evidence_identity"]),
        "access_contract_sha256": _canonical_sha256(packet["access_contract"]),
        "blank_response_contracts_sha256": _canonical_sha256(packet["blank_response_contracts"]),
        "authority_sha256": _canonical_sha256(packet["authority"]),
        "evidence_sections_sha256": cast(Mapping[str, Any], packet["deterministic_replay"])[
            "evidence_sections_sha256"
        ],
    }


def _assemble_seal(
    *,
    seal_commit: str,
    control_artifact: Mapping[str, Any],
    seal_implementation: Mapping[str, Mapping[str, Any]],
    packet_control_artifact: Mapping[str, Any],
    packet_implementation: Mapping[str, Mapping[str, Any]],
    packet_artifact: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "format_version": 1,
        "experiment_id": "E-0039",
        "dataset_role": "CALIBRATION",
        "state": SEAL_STATE,
        "seal_git_commit": seal_commit,
        "seal_git_dirty": False,
        "packet_capture_git_commit": PACKET_CAPTURE_GIT_COMMIT,
        "inventory": {"file_count": 1, "files": [copy.deepcopy(packet_artifact)]},
        "input_hash_ledger": {
            "seal_control": copy.deepcopy(control_artifact),
            "seal_implementation": copy.deepcopy(seal_implementation),
            "packet_control": copy.deepcopy(packet_control_artifact),
            "packet_implementation": copy.deepcopy(packet_implementation),
        },
        "packet_contract": _packet_summary(packet),
        "replay": {
            "packet_validation_invocation_count": 2,
            "exact_canonical_byte_equality": True,
            "canonical_encoding": ("UTF8_JSON_SORTED_KEYS_COMPACT_NO_NAN_NO_DUPLICATE_KEYS_V1"),
            "packet_evidence_assembly_invocation_count": 2,
            "packet_evidence_exact_canonical_byte_equality": True,
            "packet_rebuilt_or_recaptured": False,
            "clean_git_commit_equal_before_publication": True,
        },
        "access_contract": copy.deepcopy(_PACKET_ACCESS_RECEIPT),
        "authority": copy.deepcopy(_AUTHORITY),
        "claim_boundary": _CLAIM_BOUNDARY,
    }


def _validate_seal_payload(
    payload: Mapping[str, Any],
    *,
    expected_seal_commit: str,
    expected_control_artifact: Mapping[str, Any],
    expected_seal_implementation: Mapping[str, Mapping[str, Any]],
    expected_packet_control_artifact: Mapping[str, Any],
    expected_packet_implementation: Mapping[str, Mapping[str, Any]],
    expected_packet_artifact: Mapping[str, Any],
) -> None:
    _exact_keys(
        payload,
        {
            "format_version",
            "experiment_id",
            "dataset_role",
            "state",
            "seal_git_commit",
            "seal_git_dirty",
            "packet_capture_git_commit",
            "inventory",
            "input_hash_ledger",
            "packet_contract",
            "replay",
            "access_contract",
            "authority",
            "claim_boundary",
        },
        "E-0039 review-packet seal",
    )
    inventory = _exact_keys(
        payload.get("inventory"), {"file_count", "files"}, "E-0039 seal inventory"
    )
    ledger = _exact_keys(
        payload.get("input_hash_ledger"),
        {
            "seal_control",
            "seal_implementation",
            "packet_control",
            "packet_implementation",
        },
        "E-0039 seal input ledger",
    )
    replay = _exact_keys(
        payload.get("replay"),
        {
            "packet_validation_invocation_count",
            "exact_canonical_byte_equality",
            "canonical_encoding",
            "packet_evidence_assembly_invocation_count",
            "packet_evidence_exact_canonical_byte_equality",
            "packet_rebuilt_or_recaptured",
            "clean_git_commit_equal_before_publication",
        },
        "E-0039 seal replay",
    )
    if (
        payload.get("format_version") != 1
        or payload.get("experiment_id") != "E-0039"
        or payload.get("dataset_role") != "CALIBRATION"
        or payload.get("state") != SEAL_STATE
        or payload.get("seal_git_commit") != expected_seal_commit
        or payload.get("seal_git_dirty") is not False
        or payload.get("packet_capture_git_commit") != PACKET_CAPTURE_GIT_COMMIT
        or inventory != {"file_count": 1, "files": [expected_packet_artifact]}
        or ledger["seal_control"] != expected_control_artifact
        or ledger["seal_implementation"] != expected_seal_implementation
        or ledger["packet_control"] != expected_packet_control_artifact
        or ledger["packet_implementation"] != expected_packet_implementation
        or payload.get("packet_contract") != _PACKET_SUMMARY
        or replay
        != {
            "packet_validation_invocation_count": 2,
            "exact_canonical_byte_equality": True,
            "canonical_encoding": ("UTF8_JSON_SORTED_KEYS_COMPACT_NO_NAN_NO_DUPLICATE_KEYS_V1"),
            "packet_evidence_assembly_invocation_count": 2,
            "packet_evidence_exact_canonical_byte_equality": True,
            "packet_rebuilt_or_recaptured": False,
            "clean_git_commit_equal_before_publication": True,
        }
        or payload.get("access_contract") != _PACKET_ACCESS_RECEIPT
        or payload.get("authority") != _AUTHORITY
        or payload.get("claim_boundary") != _CLAIM_BOUNDARY
    ):
        raise E0039ReviewPacketSealError("E-0039 review-packet seal drifted")


def capture_e0039_review_packet_seal(
    project_root: Path,
    *,
    config_path: Path = CONTROL_RELATIVE_PATH,
    packet_path: Path = PACKET_RELATIVE_PATH,
    output_path: Path = OUTPUT_RELATIVE_PATH,
    _reader: StableReader | None = None,
) -> dict[str, Any]:
    """Validate and exclusively hash-seal the existing E-0039 packet."""

    root = project_root.resolve()
    reader = _read_stable_file if _reader is None else _reader
    try:
        _assert_process_review_isolated()
        control_path = _canonical_path(root, config_path, CONTROL_RELATIVE_PATH, "seal control")
        canonical_packet = _canonical_path(root, packet_path, PACKET_RELATIVE_PATH, "packet")
        output = _canonical_path(root, output_path, OUTPUT_RELATIVE_PATH, "packet seal")
        if output.exists() or output.is_symlink():
            raise E0039ReviewPacketSealError(f"refusing to overwrite E-0039 seal: {output}")

        seal_commit = _clean_git_commit(root)
        _assert_capture_commit_ancestor(root, PACKET_CAPTURE_GIT_COMMIT, seal_commit)
        control_stable = reader(
            root,
            control_path,
            "E-0039 review-packet seal control",
            maximum_size=_RESOURCE_CAPS["maximum_control_bytes"],
        )
        control = _decode_control(control_stable.payload)
        frozen, seal_implementation_stable = _validate_control(root, control, reader)

        stable: dict[str, _StableFile] = {}
        stable["packet_control"] = _verified_record(
            reader,
            root,
            frozen["packet_control"],
            name="packet_control",
            expected_path=_FROZEN_PATHS["packet_control"],
            maximum_size=_RESOURCE_CAPS["maximum_control_bytes"],
        )
        packet_control = _decode_control(stable["packet_control"].payload)
        expected_packet_implementation = _validate_packet_control(packet_control, frozen)

        for name in tuple(_FROZEN_PATHS)[1:-1]:
            stable[name] = _verified_record(
                reader,
                root,
                frozen[name],
                name=name,
                expected_path=_FROZEN_PATHS[name],
                maximum_size=_RESOURCE_CAPS["maximum_implementation_bytes_each"],
            )
        if {
            name: stable[input_name].artifact
            for name, input_name in _PACKET_INPUT_NAME_BY_IMPLEMENTATION.items()
        } != expected_packet_implementation:
            raise E0039ReviewPacketSealError("opened packet implementation identities drifted")

        stable["packet"] = _verified_record(
            reader,
            root,
            frozen["packet"],
            name="packet",
            expected_path=canonical_packet.relative_to(root),
            maximum_size=_RESOURCE_CAPS["maximum_packet_bytes"],
        )
        if tuple(stable) != tuple(_FROZEN_PATHS):
            raise E0039ReviewPacketSealError("E-0039 seal direct input read order drifted")
        direct_total = (
            control_stable.artifact["size_bytes"]
            + sum(item.artifact["size_bytes"] for item in seal_implementation_stable.values())
            + sum(item.artifact["size_bytes"] for item in stable.values())
        )
        if direct_total > _RESOURCE_CAPS["maximum_total_direct_input_bytes"]:
            raise E0039ReviewPacketSealError("E-0039 seal direct input byte cap exceeded")

        packet = _strict_json(stable["packet"], "sealed E-0039 review packet")
        encoded_replays: list[bytes] = []
        for _invocation in range(2):
            _validate_packet_payload(
                packet,
                expected_control_artifact=stable["packet_control"].artifact,
                expected_implementation_artifacts=expected_packet_implementation,
                expected_git_commit=PACKET_CAPTURE_GIT_COMMIT,
            )
            encoded_replays.append(_encoded_packet_json(packet))
        if (
            encoded_replays[0] != encoded_replays[1]
            or encoded_replays[0] != stable["packet"].payload
            or _packet_summary(packet) != _PACKET_SUMMARY
        ):
            raise E0039ReviewPacketSealError(
                "E-0039 packet canonical replay or blank contract drifted"
            )

        seal_implementation = {
            name: copy.deepcopy(item.artifact) for name, item in seal_implementation_stable.items()
        }
        seal_payload = _assemble_seal(
            seal_commit=seal_commit,
            control_artifact=control_stable.artifact,
            seal_implementation=seal_implementation,
            packet_control_artifact=stable["packet_control"].artifact,
            packet_implementation=expected_packet_implementation,
            packet_artifact=stable["packet"].artifact,
            packet=packet,
        )
        _validate_seal_payload(
            seal_payload,
            expected_seal_commit=seal_commit,
            expected_control_artifact=control_stable.artifact,
            expected_seal_implementation=seal_implementation,
            expected_packet_control_artifact=stable["packet_control"].artifact,
            expected_packet_implementation=expected_packet_implementation,
            expected_packet_artifact=stable["packet"].artifact,
        )
        encoded_seal = _encoded_seal_json(seal_payload)
        if len(encoded_seal) > _RESOURCE_CAPS["maximum_seal_bytes"]:
            raise E0039ReviewPacketSealError("E-0039 seal byte cap exceeded")

        all_stable = {
            "seal_control": control_stable,
            **seal_implementation_stable,
            **stable,
        }
        for name, item in all_stable.items():
            try:
                _assert_unchanged(reader, root, item, f"E-0039 seal final recheck {name}")
            except E0038ExactMappingError as exc:
                raise _fail(f"E-0039 seal input changed before publication: {name}", exc) from exc

        _head_bind(
            root,
            control_stable.artifact,
            name="seal control",
            path=CONTROL_RELATIVE_PATH,
            reader=reader,
        )
        for name, path in _IMPLEMENTATION_PATHS.items():
            _head_bind(
                root,
                seal_implementation_stable[name].artifact,
                name=f"seal implementation {name}",
                path=path,
                reader=reader,
            )
        _head_bind(
            root,
            stable["packet_control"].artifact,
            name="packet control",
            path=PACKET_CONTROL_RELATIVE_PATH,
            reader=reader,
        )
        _assert_record_matches_git_commit(
            root,
            stable["packet_control"].artifact,
            name="packet control",
            expected_path=PACKET_CONTROL_RELATIVE_PATH,
            commit=PACKET_CAPTURE_GIT_COMMIT,
        )
        for packet_name, path in _PACKET_IMPLEMENTATION_PATHS.items():
            input_name = _PACKET_INPUT_NAME_BY_IMPLEMENTATION[packet_name]
            _head_bind(
                root,
                stable[input_name].artifact,
                name=f"packet implementation {packet_name}",
                path=path,
                reader=reader,
            )
            _assert_record_matches_git_commit(
                root,
                stable[input_name].artifact,
                name=f"packet implementation {packet_name}",
                expected_path=path,
                commit=PACKET_CAPTURE_GIT_COMMIT,
            )
        _assert_process_review_isolated()
        if _clean_git_commit(root) != seal_commit:
            raise E0039ReviewPacketSealError("Git identity changed before E-0039 seal publication")
        if output.exists() or output.is_symlink():
            raise E0039ReviewPacketSealError(f"refusing to overwrite E-0039 seal: {output}")
        try:
            _exclusive_publish_json(root, output, seal_payload)
        except E0038ExactMappingError as exc:
            raise _fail("cannot exclusively publish E-0039 packet seal", exc) from exc
        return seal_payload
    except E0039ReviewPacketSealError:
        raise
    except (
        E0038ExactMappingError,
        E0039ReviewPacketError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise _fail("E-0039 review-packet sealing failed closed", exc) from exc


__all__ = [
    "E0039ReviewPacketSealError",
    "capture_e0039_review_packet_seal",
]
