"""Answer-free E-0039 row-review and schema-steward evidence packet.

The packet is deliberately pre-decision.  It assembles the exact six rows that
E-0038 left unselected and, in a separate section, the two unapproved E-0038
structural-alias hypotheses.  It never loads accounting values, prior review
answers, history, MongoDB, rejected Qwen output, or holdout evidence.
"""

from __future__ import annotations

import copy
import errno
import hashlib
import json
import os
import secrets
import stat
from collections import Counter
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, cast

from bctc_ai.evaluation.e0037_evidence_assembly import (
    E0037SourceStructureError,
    validate_source_only_structure,
)
from bctc_ai.evaluation.e0037_sealed_mapping import (
    E0037SealedMappingError,
    _validate_mapping_only_payload,
)
from bctc_ai.evaluation.e0038_exact_mapping import (
    E0038ExactMappingError,
    _assert_tracked_record_matches_head,
    _assert_unchanged,
    _canonical_path,
    _clean_git_commit,
    _decode_control,
    _load_unique_s3_record,
    _open_existing_parent_directory,
    _open_or_create_parent_directory,
    _read_from_fresh_canonical_path,
    _read_stable_file,
    _rollback_published_link,
    _same_inode,
    _StableFile,
    _validate_e0037_seal_before_mapping_open,
    _validate_e0038_mapping_payload,
    _validate_e0038_mapping_seal_payload,
    _verify_record,
)


class E0039ReviewPacketError(RuntimeError):
    """Raised when the pre-decision E-0039 packet cannot be built safely."""


CONTROL_RELATIVE_PATH = Path("config/experiments/e0039-mbb-cdkt-review-packet.yaml")
OUTPUT_RELATIVE_PATH = Path("output/calibration/e0039-mbb-cdkt-review-packet/evidence_packet.json")
PACKET_BUILDER_RELATIVE_PATH = Path("src/bctc_ai/evaluation/e0039_review_packet.py")
CAPTURE_SCRIPT_RELATIVE_PATH = Path("scripts/experiments/capture_e0039_mbb_cdkt_review_packet.py")

E0035_SEAL_RELATIVE_PATH = Path("docs/experiments/E-0035-mbb-cdkt-logical-row-label-crops.json")
CROP_MANIFEST_RELATIVE_PATH = Path(
    "output/calibration/e0035-mbb-cdkt-logical-row-label-crops/"
    "a177792e8b98f340f562/crop_manifest.json"
)
PAGE_RENDER_0003_RELATIVE_PATH = Path(
    "output/calibration/recovery-e0027-mbb-q1-2026-20260807/"
    "eebeda2ebc09b0d42032/renders/page-0003.png"
)
PAGE_RENDER_0004_RELATIVE_PATH = Path(
    "output/calibration/recovery-e0027-mbb-q1-2026-20260807/"
    "eebeda2ebc09b0d42032/renders/page-0004.png"
)
PAGE_RENDER_IDENTITIES = {
    3: {
        "path": PAGE_RENDER_0003_RELATIVE_PATH.as_posix(),
        "sha256": "40544c98908d2ca59d5e78a840594cbbea1622d33ac6a72b187c413670bef599",
        "size_bytes": 1_709_301,
    },
    4: {
        "path": PAGE_RENDER_0004_RELATIVE_PATH.as_posix(),
        "sha256": "0c872315d09faebaba24c3b4badcc355d235841b0e1e57d4dda443e76f7b16b7",
        "size_bytes": 1_033_463,
    },
}
E0036_BASELINE_SEAL_RELATIVE_PATH = Path(
    "docs/experiments/E-0036-mbb-cdkt-baseline-output-seal.json"
)
VIETOCR_RESULT_RELATIVE_PATH = Path(
    "output/calibration/e0036-mbb-cdkt-semantic-label-readers/vietocr-reader/ocr_result.json"
)
DEEPSEEK_RESULT_RELATIVE_PATH = Path(
    "output/calibration/e0036-mbb-cdkt-semantic-label-readers/deepseek-reader/ocr_result.json"
)
E0037_SOURCE_STRUCTURE_RELATIVE_PATH = Path(
    "output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/source_structure.json"
)
E0037_MAPPING_ONLY_RELATIVE_PATH = Path(
    "output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/mapping_only.json"
)
E0037_MAPPING_SEAL_RELATIVE_PATH = Path("docs/experiments/E-0037-mbb-cdkt-mapping-only-seal.json")
S3_REGISTRY_RELATIVE_PATH = Path("data/registered/s3_artifact_snapshot_registry.jsonl")
E0038_MAPPING_CONTROL_RELATIVE_PATH = Path("config/experiments/e0038-mbb-cdkt-exact-mapping.yaml")
E0038_MAPPING_ONLY_RELATIVE_PATH = Path(
    "output/calibration/e0038-mbb-cdkt-exact-mapping/mapping_only.json"
)
E0038_MAPPING_SEAL_RELATIVE_PATH = Path("docs/experiments/E-0038-mbb-cdkt-exact-mapping-seal.json")
E0038_S3_REGISTRATION_RELATIVE_PATH = Path(
    "docs/experiments/E-0038-mbb-cdkt-exact-mapping-s3-registration.json"
)
E0038_ALIAS_POLICY_RELATIVE_PATH = Path(
    "config/mapping/e0038-cdkt-structural-alias-candidates.yaml"
)
CDKT_WORKBOOK_RELATIVE_PATH = Path("template/Bank_CDKT_ReportNormId.xlsx")

E0037_EVIDENCE_ASSEMBLY_RELATIVE_PATH = Path("src/bctc_ai/evaluation/e0037_evidence_assembly.py")
E0037_SEALED_MAPPING_RELATIVE_PATH = Path("src/bctc_ai/evaluation/e0037_sealed_mapping.py")
E0038_EXACT_MAPPING_RELATIVE_PATH = Path("src/bctc_ai/evaluation/e0038_exact_mapping.py")

READY_STATE = "READY_FOR_E0039_PREDECISION_REVIEW_PACKET_CAPTURE"
PACKET_STATE = "E0039_PREDECISION_REVIEW_AND_STEWARD_EVIDENCE_PACKET"

SOURCE_DOCUMENT = {
    "path": "vietstock_bctc/MBB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf",
    "sha256": "eebeda2ebc09b0d4203259e92cda0169b46fde555557f150a314c72517fc1c83",
    "size_bytes": 3_977_471,
}
BASE_PROJECTION_SHA256 = "7025ca729c01a3f2030af38e9745a0ee8d72b1dad60c8d4e3b7cf749e5eb860c"
RESULT_PROJECTION_SHA256 = "d0934db910063bdb98db83f02bc2444fc1fe6e1dce7e1ebc7e09c7d36e434283"
E0037_SOURCE_STRUCTURE_SHA256 = "ef098a659f8b557ac3a801edccfc7c0848be9a512b47ba7c9278cd3873f70728"
E0037_E0038_SELECTED_PAIR_PROJECTION_SHA256 = (
    "8135658100d83772812aeecff4beb4378ad7163c96a286a3770d430027a87df3"
)
ALIAS_RECEIPT_SHA256 = "768867b636c137b26804e6bcfb4230491e07d91299160e4071b8ac72664aa7b9"
E0037_S3_SNAPSHOT_ID = "20260807T170440Z-e0037-source-and-mapping-seal-e18f6b20825f"
E0038_S3_SNAPSHOT_ID = "20260807T192436Z-e0038-exact-mapping-seal-8b1074d2ca57"
E0038_MAPPING_RESULT_SHA256 = "45133c4c6a441327afc611d6cce6c4711b7fe18b945339d854944817b90a9e86"
E0038_S3_REGISTRATION_STATE = "E0038_EXACT_MAPPING_IMMUTABLY_REGISTERED_IN_S3_POST_SEAL"
E0038_MAPPING_STATE = "E0038_EXACT_MAPPING_ONLY_CALIBRATION_HYPOTHESIS_SEALED_BEFORE_REVIEW"
_EXPECTED_E0038_ROW_STATUS_COUNTS = {
    "BEST_PATH_SKIPPED": 2,
    "NO_ADMISSIBLE_PAIR": 4,
    "RESOLVED_ANCHOR": 41,
    "RESOLVED_PATH": 17,
}
_EXPECTED_E0038_SCHEMA_STATUS_COUNTS = {
    "MAPPED": 58,
    "UNMATCHED_SCHEMA_NODE": 13,
    "UNMATCHED_SCHEMA_NODE_WITH_SKIPPED_CANDIDATES": 6,
}

UNSELECTED_ROW_IDS = (
    "page-0003-row-002-label",
    "page-0003-row-003-label",
    "page-0004-row-000-label",
    "page-0004-row-002-label",
    "page-0004-row-013-label",
    "page-0004-row-023-label",
)
ALIAS_ROW_BINDINGS = (
    (
        "CDKT_4375_TOTAL_ASSETS_BANKING_WORDING",
        "page-0003-row-038-label",
        4375,
        "TỔNG TÀI SẢN CÓ",
    ),
    (
        "CDKT_5699_NCI_POSSESSIVE_PARTICLE",
        "page-0004-row-022-label",
        5699,
        "Lợi ích của cổ đông không kiểm soát",
    ),
)
TARGET_ROW_IDS = (*UNSELECTED_ROW_IDS, *(item[1] for item in ALIAS_ROW_BINDINGS))

_EXPECTED_TARGET_INTERVALS = {
    2: {
        "row_ids": ["page-0003-row-002-label", "page-0003-row-003-label"],
        "report_norm_ids": [4311, 4312, 4344, 4326, 4345],
        "previous_anchor": ["page-0003-row-001-label", 4310],
        "next_anchor": ["page-0003-row-004-label", 4313],
        "status": "BEST_PATH_SKIPPED",
        "reason": "admissible pairs do not improve on the zero skip baseline",
        "canonical_sha256": "ef2d282e8b5efa0104d8a4cdbc28514afb12fb4f396486cf80f0846b3d69003f",
    },
    24: {
        "row_ids": ["page-0004-row-000-label"],
        "report_norm_ids": [4303],
        "previous_anchor": ["page-0003-row-038-label", 4375],
        "next_anchor": ["page-0004-row-001-label", 4318],
        "status": "NO_ADMISSIBLE_PAIR",
        "reason": "no row/schema pair passes strong or mapped-direct-parent admissibility",
        "canonical_sha256": "100ee1a2971fba43a3cf0be3d8880a4c6020ab1f8e67d6c6358eedd36c0fc534",
    },
    25: {
        "row_ids": ["page-0004-row-002-label"],
        "report_norm_ids": [4319, 4359, 4360],
        "previous_anchor": ["page-0004-row-001-label", 4318],
        "next_anchor": ["page-0004-row-003-label", 4320],
        "status": "BEST_PATH_SKIPPED",
        "reason": "admissible pairs do not improve on the zero skip baseline",
        "canonical_sha256": "3006d4fcb9686315979908e30933c058283b00ff205bfb885a2f949737a28b8e",
    },
    32: {
        "row_ids": ["page-0004-row-013-label"],
        "report_norm_ids": [],
        "previous_anchor": ["page-0004-row-012-label", 4304],
        "next_anchor": ["page-0004-row-014-label", 4325],
        "status": "NO_ADMISSIBLE_PAIR",
        "reason": "no row/schema pair passes strong or mapped-direct-parent admissibility",
        "canonical_sha256": "d046e81dc496753488d3defe247e0d40ded6663bc65c4a4baa849b2b01683b81",
    },
    40: {
        "row_ids": ["page-0004-row-023-label"],
        "report_norm_ids": [4306],
        "previous_anchor": ["page-0004-row-022-label", 5699],
        "next_anchor": ["page-0004-row-024-label", 4305],
        "status": "NO_ADMISSIBLE_PAIR",
        "reason": "no row/schema pair passes strong or mapped-direct-parent admissibility",
        "canonical_sha256": "407aa9a06b9646dc02e232ef0d034080aa57228bf62d8c955dc3d9dc102334b8",
    },
}

_EXPECTED_UNSELECTED_DIAGNOSTICS = {
    "page-0003-row-002-label": {
        "e0037_status": "NO_ADMISSIBLE_PAIR",
        "e0037_candidates": [],
        "e0038_status": "NO_ADMISSIBLE_PAIR",
        "e0038_candidates": [],
        "e0038_interval_index": 2,
    },
    "page-0003-row-003-label": {
        "e0037_status": "AMBIGUOUS_ACROSS_PATHS",
        "e0037_candidates": [4344],
        "e0038_status": "BEST_PATH_SKIPPED",
        "e0038_candidates": [4344],
        "e0038_interval_index": 2,
    },
    "page-0004-row-000-label": {
        "e0037_status": "NO_ADMISSIBLE_PAIR",
        "e0037_candidates": [],
        "e0038_status": "NO_ADMISSIBLE_PAIR",
        "e0038_candidates": [],
        "e0038_interval_index": 24,
    },
    "page-0004-row-002-label": {
        "e0037_status": "AMBIGUOUS_ACROSS_PATHS",
        "e0037_candidates": [4359, 4360],
        "e0038_status": "BEST_PATH_SKIPPED",
        "e0038_candidates": [4359, 4360],
        "e0038_interval_index": 25,
    },
    "page-0004-row-013-label": {
        "e0037_status": "NO_ADMISSIBLE_PAIR",
        "e0037_candidates": [],
        "e0038_status": "NO_ADMISSIBLE_PAIR",
        "e0038_candidates": [],
        "e0038_interval_index": 32,
    },
    "page-0004-row-023-label": {
        "e0037_status": "NO_ADMISSIBLE_PAIR",
        "e0037_candidates": [],
        "e0038_status": "NO_ADMISSIBLE_PAIR",
        "e0038_candidates": [],
        "e0038_interval_index": 40,
    },
}

_CROP_PREFIX = (
    "output/calibration/e0035-mbb-cdkt-logical-row-label-crops/a177792e8b98f340f562/crops"
)
CROP_PATHS = {row_id: Path(f"{_CROP_PREFIX}/{row_id}.png") for row_id in TARGET_ROW_IDS}

_EXPECTED_FROZEN_INPUTS: dict[str, dict[str, Any]] = {
    "e0035_seal": {
        "path": E0035_SEAL_RELATIVE_PATH.as_posix(),
        "sha256": "a1bb81e895b45d003910aba523ba121461f15079b9452dde8d508600c5dcc3e3",
        "size_bytes": 5_131,
    },
    "crop_manifest": {
        "path": CROP_MANIFEST_RELATIVE_PATH.as_posix(),
        "sha256": "3b12da05e19467e85bfc6d828b73a3e35598c53d7c57cfb932b76763bec57eac",
        "size_bytes": 70_663,
    },
    "crop_page_0003_row_002": {
        "path": CROP_PATHS[UNSELECTED_ROW_IDS[0]].as_posix(),
        "sha256": "65dbe5ad066c7594f663b0e238704deb39fddb3de106b7f9c2a96dae523faebc",
        "size_bytes": 20_391,
    },
    "crop_page_0003_row_003": {
        "path": CROP_PATHS[UNSELECTED_ROW_IDS[1]].as_posix(),
        "sha256": "006c84ce6e05a2f333aca27d4e799659ca67572c1e20e320fa21f102787a7922",
        "size_bytes": 28_306,
    },
    "crop_page_0004_row_000": {
        "path": CROP_PATHS[UNSELECTED_ROW_IDS[2]].as_posix(),
        "sha256": "92f88087df31e5163d14d2a26241929cb3bf9b41f63a50645424fad9fa780ff8",
        "size_bytes": 6_928,
    },
    "crop_page_0004_row_002": {
        "path": CROP_PATHS[UNSELECTED_ROW_IDS[3]].as_posix(),
        "sha256": "9efc3fb45de4d440770ff8cd217e3fe1b3941e407f8c5e39081e264299322af7",
        "size_bytes": 14_587,
    },
    "crop_page_0004_row_013": {
        "path": CROP_PATHS[UNSELECTED_ROW_IDS[4]].as_posix(),
        "sha256": "14319e9219d628fded8b85569967f011e77eecd16853a4e4fa2dac2603474102",
        "size_bytes": 10_159,
    },
    "crop_page_0004_row_023": {
        "path": CROP_PATHS[UNSELECTED_ROW_IDS[5]].as_posix(),
        "sha256": "6ed40472f6435591c991c21d42faa707e16747bd18fe0e21e6f17b8cc3aca765",
        "size_bytes": 12_642,
    },
    "crop_page_0003_row_038": {
        "path": CROP_PATHS[ALIAS_ROW_BINDINGS[0][1]].as_posix(),
        "sha256": "a7cde46da05efdd8e7fb37a6df332f3d61a3f00fae244f6a9a626dce932f1c48",
        "size_bytes": 12_494,
    },
    "crop_page_0004_row_022": {
        "path": CROP_PATHS[ALIAS_ROW_BINDINGS[1][1]].as_posix(),
        "sha256": "86e999b464befca56f8cd8f60c1f2ef24b483f7b4dd7cee13f211efc85b3f083",
        "size_bytes": 20_010,
    },
    "e0036_baseline_seal": {
        "path": E0036_BASELINE_SEAL_RELATIVE_PATH.as_posix(),
        "sha256": "768f10f564b8a51e60c95af432cf6d11e68e4be4d3b6cb4da31c21b856e8a8a0",
        "size_bytes": 5_459,
    },
    "vietocr_result": {
        "path": VIETOCR_RESULT_RELATIVE_PATH.as_posix(),
        "sha256": "204c897d0d7419be6194f626c033624b52ddbec4d8aa2b3cd0f02f4645ceacf6",
        "size_bytes": 35_990,
    },
    "deepseek_result": {
        "path": DEEPSEEK_RESULT_RELATIVE_PATH.as_posix(),
        "sha256": "3273a5cd3f847e52e1178b888a6b9e246d8c1b73778de5d936fbbc9960909474",
        "size_bytes": 44_781,
    },
    "e0037_source_structure": {
        "path": E0037_SOURCE_STRUCTURE_RELATIVE_PATH.as_posix(),
        "sha256": E0037_SOURCE_STRUCTURE_SHA256,
        "size_bytes": 136_042,
    },
    "e0037_mapping_only": {
        "path": E0037_MAPPING_ONLY_RELATIVE_PATH.as_posix(),
        "sha256": "e18f6b20825f93b20023c0d89caca1737481008b244696594852ca9fa972f99e",
        "size_bytes": 646_393,
    },
    "e0037_mapping_seal": {
        "path": E0037_MAPPING_SEAL_RELATIVE_PATH.as_posix(),
        "sha256": "665aa1b3ac96881df0a4cd7b2f7da2425c3635ad1e8ea024e299b668c79ed0e5",
        "size_bytes": 6_016,
    },
    "s3_registry": {
        "path": S3_REGISTRY_RELATIVE_PATH.as_posix(),
        "sha256": "25da6b205a775d87eca8e4ffe55e3f762ee64e92cbb7190c2834708a7de0d78d",
        "size_bytes": 6_050,
    },
    "e0038_mapping_control": {
        "path": E0038_MAPPING_CONTROL_RELATIVE_PATH.as_posix(),
        "sha256": "59db541208b6295aeff0cead9b0c9cb8624962738726b128432b1ca4cb074855",
        "size_bytes": 8_814,
    },
    "e0038_mapping_only": {
        "path": E0038_MAPPING_ONLY_RELATIVE_PATH.as_posix(),
        "sha256": "8b1074d2ca57efcb1c6da123615ace86438069b4d581b9afb4b6e4cfbf01a9e9",
        "size_bytes": 646_606,
    },
    "e0038_mapping_seal": {
        "path": E0038_MAPPING_SEAL_RELATIVE_PATH.as_posix(),
        "sha256": "bffcaf56d80af458187a646269862b8bf669237d865fa1561ab41b056db06137",
        "size_bytes": 6_421,
    },
    "e0038_s3_registration": {
        "path": E0038_S3_REGISTRATION_RELATIVE_PATH.as_posix(),
        "sha256": "6baf6a90842066e5253533072a800c5066e97248745efed8480cb67c410601e4",
        "size_bytes": 9_555,
    },
    "e0038_alias_policy": {
        "path": E0038_ALIAS_POLICY_RELATIVE_PATH.as_posix(),
        "sha256": "d1cfbfd3782e1c5af1e605f8218d3f656358877f7d70c360e6bc9555e8be8948",
        "size_bytes": 1_496,
    },
    "cdkt_workbook": {
        "path": CDKT_WORKBOOK_RELATIVE_PATH.as_posix(),
        "sha256": "a07ff47f7c41011fe4ca5a66681106d476586ded9013b5874cbb9f67a6ad8486",
        "size_bytes": 10_945,
    },
}

_FROZEN_PATHS = {
    "e0035_seal": E0035_SEAL_RELATIVE_PATH,
    "crop_manifest": CROP_MANIFEST_RELATIVE_PATH,
    "crop_page_0003_row_002": CROP_PATHS[UNSELECTED_ROW_IDS[0]],
    "crop_page_0003_row_003": CROP_PATHS[UNSELECTED_ROW_IDS[1]],
    "crop_page_0004_row_000": CROP_PATHS[UNSELECTED_ROW_IDS[2]],
    "crop_page_0004_row_002": CROP_PATHS[UNSELECTED_ROW_IDS[3]],
    "crop_page_0004_row_013": CROP_PATHS[UNSELECTED_ROW_IDS[4]],
    "crop_page_0004_row_023": CROP_PATHS[UNSELECTED_ROW_IDS[5]],
    "crop_page_0003_row_038": CROP_PATHS[ALIAS_ROW_BINDINGS[0][1]],
    "crop_page_0004_row_022": CROP_PATHS[ALIAS_ROW_BINDINGS[1][1]],
    "e0036_baseline_seal": E0036_BASELINE_SEAL_RELATIVE_PATH,
    "vietocr_result": VIETOCR_RESULT_RELATIVE_PATH,
    "deepseek_result": DEEPSEEK_RESULT_RELATIVE_PATH,
    "e0037_source_structure": E0037_SOURCE_STRUCTURE_RELATIVE_PATH,
    "e0037_mapping_only": E0037_MAPPING_ONLY_RELATIVE_PATH,
    "e0037_mapping_seal": E0037_MAPPING_SEAL_RELATIVE_PATH,
    "s3_registry": S3_REGISTRY_RELATIVE_PATH,
    "e0038_mapping_control": E0038_MAPPING_CONTROL_RELATIVE_PATH,
    "e0038_mapping_only": E0038_MAPPING_ONLY_RELATIVE_PATH,
    "e0038_mapping_seal": E0038_MAPPING_SEAL_RELATIVE_PATH,
    "e0038_s3_registration": E0038_S3_REGISTRATION_RELATIVE_PATH,
    "e0038_alias_policy": E0038_ALIAS_POLICY_RELATIVE_PATH,
    "cdkt_workbook": CDKT_WORKBOOK_RELATIVE_PATH,
}

_IMPLEMENTATION_PATHS = {
    "packet_builder": PACKET_BUILDER_RELATIVE_PATH,
    "capture_script": CAPTURE_SCRIPT_RELATIVE_PATH,
    "source_structure_validator": E0037_EVIDENCE_ASSEMBLY_RELATIVE_PATH,
    "e0037_mapping_validator": E0037_SEALED_MAPPING_RELATIVE_PATH,
    "hardened_io_and_e0038_payload_validator": E0038_EXACT_MAPPING_RELATIVE_PATH,
}

_DIRECT_INPUT_READ_ORDER = (
    "e0035_seal",
    "crop_manifest",
    "crop_page_0003_row_002",
    "crop_page_0003_row_003",
    "crop_page_0004_row_000",
    "crop_page_0004_row_002",
    "crop_page_0004_row_013",
    "crop_page_0004_row_023",
    "crop_page_0003_row_038",
    "crop_page_0004_row_022",
    "e0036_baseline_seal",
    "vietocr_result",
    "deepseek_result",
    "e0038_mapping_control",
    "e0037_mapping_seal",
    "s3_registry",
    "e0037_source_structure",
    "e0037_mapping_only",
    "e0038_mapping_seal",
    "e0038_s3_registration",
    "e0038_mapping_only",
    "e0038_alias_policy",
    "cdkt_workbook",
)

_TARGET_CROP_INPUT_NAMES = (
    "crop_page_0003_row_002",
    "crop_page_0003_row_003",
    "crop_page_0004_row_000",
    "crop_page_0004_row_002",
    "crop_page_0004_row_013",
    "crop_page_0004_row_023",
    "crop_page_0003_row_038",
    "crop_page_0004_row_022",
)

_EXPECTED_OPENED_INPUT_PATHS = [
    CONTROL_RELATIVE_PATH.as_posix(),
    *[path.as_posix() for path in _IMPLEMENTATION_PATHS.values()],
    *[_FROZEN_PATHS[name].as_posix() for name in _DIRECT_INPUT_READ_ORDER],
]

# These canonical digests freeze every nested evidence value and keyset, including
# visible labels, reader proposals, schema snapshots, alias score/collision audits,
# and authority markers.  They are independently backed by the frozen input ledger.
_EXPECTED_ROW_ENTRY_SHA256 = {
    "page-0003-row-002-label": "e3d3ae3e81ae94b2ea271e4dc27680b73f2d0160a8e03c995f4f3a559a4371b9",
    "page-0003-row-003-label": "1e3d3228a5e01925f01150b91d304323d90ed2cda1e4bbee14122a07a86f464f",
    "page-0004-row-000-label": "e08e43540f20ba55198a79131a3fa33f339bc8974e875b6099e95844c1cbfc53",
    "page-0004-row-002-label": "217e981330a512b24274797c5c8043ecb0c1e5f284d97ce4c28f3ece087aa717",
    "page-0004-row-013-label": "07d95d0dc9957cbc43d34ba8b4cfe3b49987bb68ca157bc3b4e0ff2b22620a90",
    "page-0004-row-023-label": "5bc1e6990fbe2d9e9d9795570e1853e233326ed1fab6d407548a6bca9ff49e4a",
}
_EXPECTED_ALIAS_ENTRY_SHA256 = {
    "CDKT_4375_TOTAL_ASSETS_BANKING_WORDING": (
        "3b706bcdbd49bd0e5a9c6663288ee124e58a9416cc7505ed032a35b427d87735"
    ),
    "CDKT_5699_NCI_POSSESSIVE_PARTICLE": (
        "55d3e4dcbbc867c1c1e6e8237d6ce80916ebb043c1c67b740ba8cab228ecb719"
    ),
}
_EXPECTED_EVIDENCE_IDENTITY_SHA256 = (
    "ef3608a824e476a0982477bdc3ae7b31a68fcaa5ecd9ea3f4c51134c0a161260"
)

_TRACKED_FROZEN_INPUTS = {
    "e0035_seal",
    "e0036_baseline_seal",
    "e0037_mapping_seal",
    "s3_registry",
    "e0038_mapping_control",
    "e0038_mapping_seal",
    "e0038_s3_registration",
    "e0038_alias_policy",
    "cdkt_workbook",
}

_INPUT_MAXIMUM_SIZES = {
    name: (
        64 * 1024 if name.startswith("crop_page_") or name == "cdkt_workbook" else 2 * 1024 * 1024
    )
    for name in _FROZEN_PATHS
}

_PACKET_CONTRACT = {
    "exact_unselected_row_count": 6,
    "exact_alias_hypothesis_count": 2,
    "unselected_row_ids": list(UNSELECTED_ROW_IDS),
    "alias_candidate_ids": [item[0] for item in ALIAS_ROW_BINDINGS],
    "reader_proposal_sources": ["deepseek_ocr2", "vietocr"],
    "ppocr_text_role": "SOURCE_VISIBLE_PROVENANCE_NOT_READER_PROPOSAL",
    "full_ordered_interval_universe_required": True,
    "full_schema_node_snapshots_required": True,
    "adjacent_selected_anchors_required": True,
    "row_and_alias_packets_must_be_separate": True,
    "response_templates_must_be_blank": True,
    "recommended_or_selected_response_answers_allowed": False,
    "formal_adjudication_or_steward_decision_allowed": False,
    "automatic_mapping_adoption_allowed": False,
}

_ACCESS_CONTRACT = {
    "e0030_or_e0034_numeric_period_unit_artifacts_allowed": False,
    "e0033_row_contract_direct_access_allowed": False,
    "history_or_mongodb_allowed": False,
    "qwen_raw_rejected_or_token_output_allowed": False,
    "old_human_review_rows_or_answers_allowed": False,
    "prior_review_artifact_or_coverage_receipt_allowed": False,
    "holdout_access_allowed": False,
    "accounting_or_excel_allowed": False,
}

_EXPECTED_PACKET_ACCESS_CONTRACT = {
    **_ACCESS_CONTRACT,
    "opened_input_paths": _EXPECTED_OPENED_INPUT_PATHS,
    "e0030_artifact_opened": False,
    "e0033_artifact_opened": False,
    "e0034_artifact_opened": False,
    "numeric_or_accounting_artifact_opened": False,
    "history_or_mongodb_artifact_opened": False,
    "qwen_raw_rejected_or_token_output_opened": False,
    "old_human_review_rows_or_answers_extracted": False,
    "holdout_artifact_opened": False,
    "mapping_rerun_invocation_count": 0,
    "adjudication_or_steward_decision_invocation_count": 0,
}

_RESOURCE_CAPS = {
    "maximum_control_bytes": 256 * 1024,
    "maximum_total_direct_input_bytes": 4 * 1024 * 1024,
    "maximum_total_control_implementation_and_input_bytes": 6 * 1024 * 1024,
    "maximum_json_input_bytes": 2 * 1024 * 1024,
    "maximum_source_crop_bytes_each": 64 * 1024,
    "maximum_workbook_bytes": 64 * 1024,
    "maximum_packet_bytes": 2 * 1024 * 1024,
    "exact_source_row_count": 64,
    "exact_schema_node_count": 77,
    "exact_e0038_interval_count": 42,
    "maximum_text_codepoints": 512,
}

_PUBLICATION_CONTRACT = {
    "canonical_paths_only": True,
    "clean_git_required_before_any_evidence_read": True,
    "clean_git_required_immediately_before_publication": True,
    "tracked_control_implementation_and_input_head_binding_required": True,
    "stable_nofollow_reads_required": True,
    "all_direct_inputs_rechecked_before_publication": True,
    "atomic_exclusive_no_overwrite": True,
    "exclusive_output_directory_inventory": [OUTPUT_RELATIVE_PATH.name],
    "formal_capture_requires_committed_mechanism": True,
}

ROW_RESPONSE_TEMPLATE = {
    "decision": None,
    "authority_role": None,
    "adjudicated_source_label": None,
    "adjudicated_row_role": None,
    "report_norm_id": None,
    "rationale": None,
    "reviewer_identity": None,
    "reviewed_at_utc": None,
}
ROW_RESPONSE_VOCABULARY = {
    "authority_role": ["INDEPENDENT_ROW_ADJUDICATOR"],
    "decision": [
        "MAP_EXISTING_REPORT_NORM_ID",
        "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE",
        "REQUIRES_SCHEMA_CHANGE",
        "SOURCE_ONLY_STRUCTURAL_ROW",
        "UNRESOLVED",
    ],
}
ALIAS_RESPONSE_TEMPLATE = {
    "decision": None,
    "authority_role": None,
    "replacement_text": None,
    "rationale": None,
    "steward_identity": None,
    "decided_at_utc": None,
}
ALIAS_RESPONSE_VOCABULARY = {
    "decision": ["APPROVE_ID_SCOPED_ALIAS", "DEFER", "REJECT", "REPLACE"],
    "authority_role": ["REVIEW_INDEPENDENT_SCHEMA_STEWARD"],
}
ROW_DECISION_CONSTRAINTS = {
    "MAP_EXISTING_REPORT_NORM_ID_requires_report_norm_id": True,
    "report_norm_id_must_be_from_full_ordered_interval_universe": True,
    "all_other_decisions_require_null_report_norm_id": True,
    "row_adjudicator_may_not_approve_schema_alias": True,
}
ALIAS_DECISION_CONSTRAINTS = {
    "APPROVE_ID_SCOPED_ALIAS_requires_exact_candidate_alias": True,
    "APPROVE_ID_SCOPED_ALIAS_requires_null_replacement_text": True,
    "REJECT_or_DEFER_requires_null_replacement_text": True,
    "REPLACE_requires_nonempty_replacement_text": True,
    "replacement_text_maximum_codepoints": 512,
    "REPLACE_downstream_adoption_allowed": False,
    "REPLACE_requires_new_collision_mapping_calibration_and_seal": True,
    "REJECT_or_DEFER_downstream_adoption_allowed": False,
    "APPROVE_ID_SCOPED_ALIAS_alone_adopts_mapping": False,
    "schema_steward_may_not_adjudicate_source_row": True,
}

_CLAIM_BOUNDARY = (
    "This calibration-only E-0039 artifact is an answer-free pre-decision evidence "
    "packet for exactly the six E-0038 unselected MBB CDKT rows and, separately, the "
    "two unapproved E-0038 structural-alias hypotheses. It records source-visible "
    "label pixels and provenance, sealed VietOCR/DeepSeek label proposals, current "
    "mapping diagnostics, complete ordered interval universes, schema snapshots, "
    "adjacent selected anchors, and immutable seal/S3 identities. No prior-review "
    "artifact, coverage receipt, reviewed row answer, or review-derived identifier is "
    "opened. Both response "
    "templates are blank. It supplies no review "
    "or steward answer, alias approval, mapping adoption, schema authority, numeric, "
    "period, unit, accounting, Excel, history, MongoDB, holdout, or production claim."
)

_CONTROL_KEYS = {
    "version",
    "experiment_id",
    "dataset_role",
    "design",
    "state",
    "frozen_inputs",
    "implementation",
    "packet_contract",
    "access_contract",
    "resource_caps",
    "publication",
    "output",
}

StableReader = Callable[..., _StableFile]


def _fail(label: str, exc: Exception) -> E0039ReviewPacketError:
    return E0039ReviewPacketError(f"{label}: {exc}")


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise E0039ReviewPacketError(f"{label} keyset drifted")
    return cast(dict[str, Any], value)


def _strict_json(stable: _StableFile, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        decoded = json.loads(
            stable.payload.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
        if not isinstance(decoded, dict):
            raise ValueError("top-level JSON value is not an object")
        compact = json.dumps(
            decoded,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        pretty = (
            json.dumps(
                decoded,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        if stable.payload not in {compact, pretty}:
            raise ValueError("bytes are not a supported canonical JSON encoding")
        return cast(dict[str, Any], decoded)
    except (UnicodeDecodeError, TypeError, ValueError) as exc:
        raise _fail(f"cannot decode {label}", exc) from exc


def _validate_canonical_jsonl(payload: bytes, label: str) -> None:
    lines = payload.splitlines()
    if not lines or len(lines) > 1024 or payload != b"\n".join(lines) + b"\n":
        raise E0039ReviewPacketError(f"{label} line inventory is noncanonical")
    for index, line in enumerate(lines, start=1):
        synthetic = _StableFile(
            path=Path(f"{label}-{index}"),
            payload=line,
            identity=(0, 0, 0, len(line), 0, 0),
            artifact={
                "path": label,
                "sha256": hashlib.sha256(line).hexdigest(),
                "size_bytes": len(line),
            },
        )
        _strict_json(synthetic, f"{label} line {index}")


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
        raise _fail("cannot encode canonical projection", exc) from exc
    return hashlib.sha256(encoded).hexdigest()


def _verified_record(
    reader: StableReader,
    root: Path,
    record: object,
    name: str,
) -> _StableFile:
    try:
        return _verify_record(
            reader,
            root,
            record,
            f"E-0039 {name}",
            expected_path=_FROZEN_PATHS[name],
            maximum_size=_INPUT_MAXIMUM_SIZES[name],
        )
    except E0038ExactMappingError as exc:
        raise _fail(f"cannot validate E-0039 input {name}", exc) from exc


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
        or control.get("design")
        != "PREDECISION_SIX_ROW_REVIEW_AND_SEPARATE_TWO_ALIAS_STEWARD_EVIDENCE_PACKET"
        or control.get("state") != READY_STATE
    ):
        raise E0039ReviewPacketError("E-0039 review-packet control drifted")
    frozen = _exact_keys(
        control.get("frozen_inputs"),
        set(_FROZEN_PATHS),
        "E-0039 frozen inputs",
    )
    if frozen != _EXPECTED_FROZEN_INPUTS:
        raise E0039ReviewPacketError("E-0039 frozen input identities drifted")
    implementation = _exact_keys(
        control.get("implementation"),
        set(_IMPLEMENTATION_PATHS),
        "E-0039 implementation ledger",
    )
    if control.get("packet_contract") != _PACKET_CONTRACT:
        raise E0039ReviewPacketError("E-0039 packet contract drifted")
    if control.get("access_contract") != _ACCESS_CONTRACT:
        raise E0039ReviewPacketError("E-0039 access contract drifted")
    if control.get("resource_caps") != _RESOURCE_CAPS:
        raise E0039ReviewPacketError("E-0039 resource caps drifted")
    if control.get("publication") != _PUBLICATION_CONTRACT:
        raise E0039ReviewPacketError("E-0039 publication contract drifted")
    if control.get("output") != {"path": OUTPUT_RELATIVE_PATH.as_posix()}:
        raise E0039ReviewPacketError("E-0039 output path is noncanonical")
    if (
        sum(item["size_bytes"] for item in frozen.values())
        > _RESOURCE_CAPS["maximum_total_direct_input_bytes"]
    ):
        raise E0039ReviewPacketError("E-0039 direct input byte budget exceeded")

    stable: dict[str, _StableFile] = {}
    for name, path in _IMPLEMENTATION_PATHS.items():
        try:
            stable[name] = _verify_record(
                reader,
                root,
                implementation[name],
                f"E-0039 implementation {name}",
                expected_path=path,
                maximum_size=2 * 1024 * 1024,
            )
        except E0038ExactMappingError as exc:
            raise _fail(f"cannot validate E-0039 implementation {name}", exc) from exc
    return cast(dict[str, dict[str, Any]], frozen), stable


def _validate_e0035_seal(payload: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(
        payload,
        {
            "capture_git_commit",
            "capture_git_dirty",
            "claim_boundary",
            "crop_manifest",
            "dataset_role",
            "experiment_config",
            "experiment_id",
            "format_version",
            "gates",
            "metrics",
            "recovery_provenance",
            "reference_isolation",
            "s3_artifact_snapshot",
            "source",
            "status",
            "verified_implementation",
        },
        "E-0035 crop seal",
    )
    s3 = payload.get("s3_artifact_snapshot")
    probe = s3.get("hydrate_probe") if isinstance(s3, dict) else None
    isolation = payload.get("reference_isolation")
    gates = payload.get("gates")
    if (
        payload.get("format_version") != 1
        or payload.get("experiment_id") != "E-0035"
        or payload.get("dataset_role") != "CALIBRATION"
        or payload.get("status") != "PASS_REFERENCE_BLIND_ALL_LOGICAL_ROW_LABEL_CROPS_FROZEN"
        or payload.get("capture_git_dirty") is not False
        or payload.get("crop_manifest") != _EXPECTED_FROZEN_INPUTS["crop_manifest"]
        or payload.get("source") != SOURCE_DOCUMENT
        or not isinstance(gates, dict)
        or any(value is not True for value in gates.values())
        or not isinstance(isolation, dict)
        or any(value is not False for value in isolation.values())
        or not isinstance(s3, dict)
        or s3.get("artifact_snapshot_id")
        != "20260807T050850Z-e0035-logical-row-label-crops-3b12da05e194"
        or s3.get("file_count") != 65
        or s3.get("restore_verified") is not True
        or not isinstance(probe, dict)
        or probe.get("status") != "PASS"
        or probe.get("reused_file_count") != 1
    ):
        raise E0039ReviewPacketError("E-0035 crop seal authority drifted")
    return {
        "artifact_snapshot_id": s3["artifact_snapshot_id"],
        "file_count": s3["file_count"],
        "restore_verified": s3["restore_verified"],
        "hydrate_probe": copy.deepcopy(probe),
    }


def _validate_crop_manifest(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    _exact_keys(
        payload,
        {
            "authority",
            "claim_boundary",
            "config",
            "crop_policy",
            "dataset_role",
            "decoder_visible_sample_fields",
            "experiment_id",
            "format_version",
            "frozen_inputs",
            "git_commit",
            "git_dirty",
            "page_sources",
            "reference_text_available_to_decoder",
            "sample_count",
            "samples",
            "selection_policy",
            "source",
            "state",
            "statement",
        },
        "E-0035 crop manifest",
    )
    samples = payload.get("samples")
    pages = payload.get("page_sources")
    authority = payload.get("authority")
    if (
        payload.get("format_version") != 1
        or payload.get("experiment_id") != "E-0035"
        or payload.get("dataset_role") != "CALIBRATION"
        or payload.get("git_dirty") is not False
        or payload.get("sample_count") != 64
        or payload.get("source") != SOURCE_DOCUMENT
        or payload.get("reference_text_available_to_decoder") is not False
        or payload.get("selection_policy")
        != "ALL_E0033_CDKT_ROWS_SELECTED_BEFORE_ANY_SEMANTIC_READER_OUTPUT"
        or not isinstance(authority, dict)
        or authority.get("source_render_is_pixel_authority") is not True
        or authority.get("reader_receives_crop_pixels_only") is not True
        or authority.get("reader_may_propose_vietnamese_label_text") is not True
        or authority.get("human_review_is_available_to_crop_builder") is not False
        or authority.get("reader_may_assign_period_unit_scope_or_schema_id") is not False
        or not isinstance(samples, list)
        or len(samples) != 64
        or not isinstance(pages, list)
        or len(pages) != 2
    ):
        raise E0039ReviewPacketError("E-0035 crop manifest identity drifted")
    page_records = {item.get("page"): item for item in pages if isinstance(item, dict)}
    if set(page_records) != {3, 4}:
        raise E0039ReviewPacketError("E-0035 page-render inventory drifted")
    for page, expected in PAGE_RENDER_IDENTITIES.items():
        record = page_records[page]
        if record.get("render") != expected or record.get("row_count") != (39 if page == 3 else 25):
            raise E0039ReviewPacketError(f"E-0035 page {page} render linkage drifted")

    expected_sample_keys = {
        "category",
        "crop_height",
        "crop_path",
        "crop_sha256",
        "crop_width",
        "label_line_indices",
        "label_union_bbox",
        "note_right_edge",
        "page",
        "ppocr_boxes",
        "ppocr_scores",
        "ppocr_text",
        "row_ordinal",
        "sample_id",
        "source_crop_bbox",
        "source_row_ids",
    }
    by_id: dict[str, dict[str, Any]] = {}
    for expected_order, sample in enumerate(samples):
        if not isinstance(sample, dict) or set(sample) != expected_sample_keys:
            raise E0039ReviewPacketError("E-0035 crop sample keyset drifted")
        sample_id = sample.get("sample_id")
        expected_page = 3 if expected_order < 39 else 4
        expected_ordinal = expected_order if expected_page == 3 else expected_order - 39
        if (
            not isinstance(sample_id, str)
            or sample_id != f"page-{expected_page:04d}-row-{expected_ordinal:03d}-label"
            or sample.get("page") != expected_page
            or sample.get("row_ordinal") != expected_ordinal
            or sample.get("category") != "LOGICAL_ROW_LABEL"
            or not isinstance(sample.get("ppocr_text"), str)
            or len(sample["ppocr_text"]) > _RESOURCE_CAPS["maximum_text_codepoints"]
            or not isinstance(sample.get("crop_sha256"), str)
            or not isinstance(sample.get("crop_path"), str)
        ):
            raise E0039ReviewPacketError("E-0035 crop sample identity drifted")
        by_id[sample_id] = sample
    if len(by_id) != 64 or any(row_id not in by_id for row_id in TARGET_ROW_IDS):
        raise E0039ReviewPacketError("E-0035 target crop denominator drifted")
    return by_id


def _validate_target_crop_files(
    manifest_rows: Mapping[str, Mapping[str, Any]],
    stable_inputs: Mapping[str, _StableFile],
) -> None:
    input_name_by_row = {
        "page-0003-row-002-label": "crop_page_0003_row_002",
        "page-0003-row-003-label": "crop_page_0003_row_003",
        "page-0004-row-000-label": "crop_page_0004_row_000",
        "page-0004-row-002-label": "crop_page_0004_row_002",
        "page-0004-row-013-label": "crop_page_0004_row_013",
        "page-0004-row-023-label": "crop_page_0004_row_023",
        "page-0003-row-038-label": "crop_page_0003_row_038",
        "page-0004-row-022-label": "crop_page_0004_row_022",
    }
    for row_id, input_name in input_name_by_row.items():
        row = manifest_rows[row_id]
        stable = stable_inputs[input_name]
        if (
            row.get("crop_path") != stable.artifact["path"]
            or row.get("crop_sha256") != stable.artifact["sha256"]
        ):
            raise E0039ReviewPacketError(f"source crop linkage drifted for {row_id}")


def _validate_e0036_seal(payload: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(
        payload,
        {
            "authority",
            "captured_at",
            "claim_boundary",
            "crop_manifest",
            "dataset_role",
            "evaluation_allowed_only_after_this_seal",
            "experiment_config",
            "experiment_id",
            "format_version",
            "inference_git_commit",
            "readers",
            "reference_or_human_review_loaded_by_sealer",
            "request",
            "s3_artifact_snapshot",
            "same_ordered_sample_ids",
            "sample_count_per_reader",
            "seal_git_commit",
            "seal_git_dirty",
            "state",
        },
        "E-0036 baseline output seal",
    )
    readers = payload.get("readers")
    authority = payload.get("authority")
    s3 = payload.get("s3_artifact_snapshot")
    probe = s3.get("hydrate_probe") if isinstance(s3, dict) else None
    if (
        payload.get("format_version") != 1
        or payload.get("experiment_id") != "E-0036"
        or payload.get("dataset_role") != "CALIBRATION"
        or payload.get("state") != "BASELINE_OUTPUTS_HASH_SEALED_BEFORE_REVIEW_ACCESS"
        or payload.get("seal_git_dirty") is not False
        or payload.get("reference_or_human_review_loaded_by_sealer") is not False
        or payload.get("evaluation_allowed_only_after_this_seal") is not True
        or payload.get("same_ordered_sample_ids") is not True
        or payload.get("sample_count_per_reader") != 64
        or payload.get("crop_manifest", {}).get("sha256")
        != _EXPECTED_FROZEN_INPUTS["crop_manifest"]["sha256"]
        or not isinstance(authority, dict)
        or any(value is not False for value in authority.values())
        or not isinstance(readers, dict)
        or set(readers) != {"vietocr", "deepseek_ocr2"}
        or readers["vietocr"].get("result") != _EXPECTED_FROZEN_INPUTS["vietocr_result"]
        or readers["deepseek_ocr2"].get("result") != _EXPECTED_FROZEN_INPUTS["deepseek_result"]
        or readers["vietocr"].get("parsed_proposal_count") != 64
        or readers["deepseek_ocr2"].get("parsed_proposal_count") != 51
        or readers["deepseek_ocr2"].get("structural_rejection_count") != 13
        or not isinstance(s3, dict)
        or s3.get("artifact_snapshot_id")
        != "20260807T055643Z-e0036-baseline-semantic-readers-3273a5cd3f84"
        or s3.get("restore_verified") is not True
        or not isinstance(probe, dict)
        or probe.get("status") != "PASS"
        or probe.get("reused_file_count") != 1
    ):
        raise E0039ReviewPacketError("E-0036 baseline seal authority drifted")
    return {
        "state": payload["state"],
        "artifact_snapshot_id": s3["artifact_snapshot_id"],
        "restore_verified": s3["restore_verified"],
        "reader_result_artifacts": {
            "deepseek_ocr2": copy.deepcopy(readers["deepseek_ocr2"]["result"]),
            "vietocr": copy.deepcopy(readers["vietocr"]["result"]),
        },
    }


def _validate_reader_outputs(
    vietocr: dict[str, Any],
    deepseek: dict[str, Any],
    manifest_rows: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    result_keys = {
        "authority",
        "dataset_role",
        "evidence_role",
        "experiment_id",
        "format_version",
        "reader",
        "reference_text_available_to_reader",
        "sample_count",
        "samples",
        "state",
    }
    for payload, reader_name, evidence_role in (
        (
            vietocr,
            "VIETOCR_VGG_TRANSFORMER",
            "INDEPENDENT_VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY",
        ),
        (deepseek, "DEEPSEEK_OCR_2", "VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY"),
    ):
        _exact_keys(payload, result_keys, f"sealed {reader_name} result")
        authority = payload.get("authority")
        if (
            payload.get("format_version") != 1
            or payload.get("experiment_id") != "E-0036"
            or payload.get("dataset_role") != "CALIBRATION"
            or payload.get("state") != "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE"
            or payload.get("reader") != reader_name
            or payload.get("evidence_role") != evidence_role
            or payload.get("reference_text_available_to_reader") is not False
            or payload.get("sample_count") != 64
            or not isinstance(authority, dict)
            or any(value is not False for value in authority.values())
        ):
            raise E0039ReviewPacketError(f"sealed {reader_name} authority drifted")

    viet_samples = vietocr.get("samples")
    deep_samples = deepseek.get("samples")
    if not isinstance(viet_samples, list) or not isinstance(deep_samples, list):
        raise E0039ReviewPacketError("sealed reader samples are absent")
    viet_keys = {
        "category",
        "crop_path",
        "crop_sha256",
        "mean_decoded_character_probability",
        "processed_height",
        "processed_width",
        "raw_prediction",
        "sample_id",
        "wall_seconds",
    }
    deep_keys = {
        "category",
        "crop_height",
        "crop_path",
        "crop_sha256",
        "crop_width",
        "inference_seconds",
        "nonempty_line_count",
        "proposal_text",
        "raw_output",
        "reader_score",
        "reader_score_available",
        "sample_id",
        "status",
    }
    viet_by_id: dict[str, dict[str, Any]] = {}
    deep_by_id: dict[str, dict[str, Any]] = {}
    expected_ids = list(manifest_rows)
    for expected_id, sample in zip(expected_ids, viet_samples, strict=True):
        if not isinstance(sample, dict) or set(sample) != viet_keys:
            raise E0039ReviewPacketError("VietOCR sample keyset drifted")
        source = manifest_rows[expected_id]
        if (
            sample.get("sample_id") != expected_id
            or sample.get("category") != "LOGICAL_ROW_LABEL"
            or sample.get("crop_path") != source["crop_path"]
            or sample.get("crop_sha256") != source["crop_sha256"]
            or not isinstance(sample.get("raw_prediction"), str)
            or not sample["raw_prediction"]
            or len(sample["raw_prediction"]) > _RESOURCE_CAPS["maximum_text_codepoints"]
        ):
            raise E0039ReviewPacketError("VietOCR sample linkage drifted")
        viet_by_id[expected_id] = sample
    for expected_id, sample in zip(expected_ids, deep_samples, strict=True):
        if not isinstance(sample, dict) or set(sample) != deep_keys:
            raise E0039ReviewPacketError("DeepSeek sample keyset drifted")
        source = manifest_rows[expected_id]
        status = sample.get("status")
        proposal = sample.get("proposal_text")
        if (
            sample.get("sample_id") != expected_id
            or sample.get("category") != "LOGICAL_ROW_LABEL"
            or sample.get("crop_path") != source["crop_path"]
            or sample.get("crop_sha256") != source["crop_sha256"]
            or status
            not in {"PARSED_SEMANTIC_PROPOSAL_ONLY", "REJECT_DOCUMENT_OR_LAYOUT_SERIALIZATION"}
            or not isinstance(proposal, str)
            or len(proposal) > _RESOURCE_CAPS["maximum_text_codepoints"]
            or (status == "PARSED_SEMANTIC_PROPOSAL_ONLY") != bool(proposal)
        ):
            raise E0039ReviewPacketError("DeepSeek sample linkage drifted")
        deep_by_id[expected_id] = sample
    if len(viet_by_id) != 64 or len(deep_by_id) != 64:
        raise E0039ReviewPacketError("sealed reader denominator drifted")
    if Counter(item["status"] for item in deep_samples) != {
        "PARSED_SEMANTIC_PROPOSAL_ONLY": 51,
        "REJECT_DOCUMENT_OR_LAYOUT_SERIALIZATION": 13,
    }:
        raise E0039ReviewPacketError("DeepSeek proposal/rejection counts drifted")
    return viet_by_id, deep_by_id


def _validate_e0038_postseal_registration_answer_free(
    registration: dict[str, Any],
    seal: Mapping[str, Any],
) -> None:
    """Validate only immutable durability/linkage facts; never load review state."""

    _exact_keys(
        registration,
        {
            "access_contract",
            "authority",
            "claim_boundary",
            "dataset_role",
            "experiment_id",
            "formal_result_summary",
            "format_version",
            "local_artifacts",
            "policy",
            "remote_verification",
            "s3_snapshot",
            "seal_linkage",
            "shared_registry",
            "state",
        },
        "E-0038 answer-free post-seal S3 registration",
    )
    access = registration.get("access_contract")
    authority = registration.get("authority")
    s3 = registration.get("s3_snapshot")
    remote = registration.get("remote_verification")
    content = s3.get("content_object") if isinstance(s3, dict) else None
    hydrate = s3.get("isolated_hydrate") if isinstance(s3, dict) else None
    first = hydrate.get("first_hydrate") if isinstance(hydrate, dict) else None
    second = hydrate.get("second_hydrate") if isinstance(hydrate, dict) else None
    run_record = s3.get("run_record") if isinstance(s3, dict) else None
    heads = remote.get("head_objects") if isinstance(remote, dict) else None
    content_head = heads.get("content_object") if isinstance(heads, dict) else None
    mapping_artifact = _EXPECTED_FROZEN_INPUTS["e0038_mapping_only"]
    seal_artifact = _EXPECTED_FROZEN_INPUTS["e0038_mapping_seal"]
    if (
        registration.get("format_version") != 1
        or registration.get("experiment_id") != "E-0038"
        or registration.get("dataset_role") != "CALIBRATION"
        or registration.get("state") != E0038_S3_REGISTRATION_STATE
        or registration.get("policy") != "IMMUTABLE_POST_SEAL_S3_REGISTRATION_V1"
        or registration.get("local_artifacts")
        != {"mapping_only": mapping_artifact, "mapping_seal": seal_artifact}
        or not isinstance(access, dict)
        or access.get("review_artifacts_opened") is not False
        or access.get("numeric_artifacts_opened") is not False
        or access.get("history_artifacts_opened") is not False
        or access.get("seal_identity_validated_before_registration") is not True
        or not isinstance(authority, dict)
        or authority.get("s3_durability_registration") is not True
        or authority.get("mapping_accuracy") is not False
        or authority.get("review_or_steward_approval") is not False
        or authority.get("numeric_period_unit_or_value") is not False
        or authority.get("accounting_excel_holdout_or_production") is not False
        or not isinstance(s3, dict)
        or s3.get("snapshot_id") != E0038_S3_SNAPSHOT_ID
        or s3.get("policy") != "S3_BOUNDED_ARTIFACT_SNAPSHOT_V1"
        or not isinstance(content, dict)
        or content.get("disposition") != "UPLOADED"
        or content.get("logical_path") != mapping_artifact["path"]
        or content.get("sha256") != mapping_artifact["sha256"]
        or content.get("size_bytes") != mapping_artifact["size_bytes"]
        or s3.get("internal_restore") != {"status": "PASS"}
        or not isinstance(hydrate, dict)
        or hydrate.get("status") != "PASS"
        or hydrate.get("logical_path") != mapping_artifact["path"]
        or not isinstance(first, dict)
        or first.get("byte_equal_to_local") is not True
        or first.get("sha256_matches") is not True
        or first.get("size_bytes_matches") is not True
        or first.get("restored_file_count") != 1
        or not isinstance(second, dict)
        or second.get("byte_equal_to_local") is not True
        or second.get("sha256_matches") is not True
        or second.get("size_bytes_matches") is not True
        or second.get("reused_file_count") != 1
        or not isinstance(run_record, dict)
        or run_record.get("status") != "PASS"
        or run_record.get("all_incremental_objects_restore_verified") is not True
        or not isinstance(remote, dict)
        or remote.get("status") != "PASS"
        or remote.get("bucket_preflight", {}).get("status") != "PASS"
        or not isinstance(content_head, dict)
        or content_head.get("status") != "PASS"
        or content_head.get("metadata_sha256") != mapping_artifact["sha256"]
        or content_head.get("content_length") != mapping_artifact["size_bytes"]
    ):
        raise E0039ReviewPacketError("E-0038 answer-free S3 registration drifted")
    if registration.get("seal_linkage") != {
        "mapping_capture_git_commit": seal["mapping_capture_git_commit"],
        "mapping_inventory_identity_matches": True,
        "mapping_ledger_identity_matches": True,
        "result_projection_matches_mapping": True,
        "result_projection_sha256": RESULT_PROJECTION_SHA256,
        "seal_git_commit": seal["seal_git_commit"],
    }:
        raise E0039ReviewPacketError("E-0038 answer-free S3/seal linkage drifted")


def _validate_e0038_mapping_answer_free(
    mapping: dict[str, Any],
    mapping_control: dict[str, Any],
    mapping_control_artifact: Mapping[str, Any],
    seal: Mapping[str, Any],
    registration: Mapping[str, Any],
) -> None:
    """Validate sealed mapping and summary facts without review-derived constants."""

    capture_commit = mapping.get("capture_git_commit")
    if not isinstance(capture_commit, str) or capture_commit != seal.get(
        "mapping_capture_git_commit"
    ):
        raise E0039ReviewPacketError("E-0038 mapping/seal commit linkage drifted")
    try:
        _validate_e0038_mapping_payload(
            mapping,
            mapping_control,
            expected_control_artifact=mapping_control_artifact,
            expected_git_commit=capture_commit,
        )
    except (E0038ExactMappingError, TypeError, ValueError) as exc:
        raise _fail("E-0038 answer-free mapping validation failed", exc) from exc

    exact = mapping["exact_mapping_bundle"]["exact_search"]
    result = exact["mapping_result_without_internal_alias_authority"]
    rows = result["row_mappings"]
    dispositions = result["schema_dispositions"]
    if not isinstance(rows, list) or not isinstance(dispositions, list):
        raise E0039ReviewPacketError("E-0038 mapping rows or schema dispositions are absent")
    row_statuses = dict(sorted(Counter(row["status"] for row in rows).items()))
    schema_statuses = dict(sorted(Counter(item["status"] for item in dispositions).items()))
    selected_count = sum(row["selected_report_norm_id"] is not None for row in rows)
    summary = registration.get("formal_result_summary")
    alias_receipt = mapping["exact_mapping_bundle"]["alias_overlay_receipt"]
    if (
        mapping.get("state") != E0038_MAPPING_STATE
        or mapping.get("result_input_binding", {}).get("mapping_result_sha256")
        != E0038_MAPPING_RESULT_SHA256
        or result.get("schema_projection_sha256") != RESULT_PROJECTION_SHA256
        or len(rows) != 64
        or selected_count != 58
        or len(rows) - selected_count != 6
        or row_statuses != _EXPECTED_E0038_ROW_STATUS_COUNTS
        or len(dispositions) != 77
        or schema_statuses != _EXPECTED_E0038_SCHEMA_STATUS_COUNTS
        or exact.get("main_search_pruned_states") != 0
        or exact.get("counterfactual_search_pruned_states") != 0
        or result.get("search", {}).get("pruned_states") != 0
        or alias_receipt.get("changed_report_norm_ids") != [4375, 5699]
        or alias_receipt.get("review_or_steward_approved") is not False
        or alias_receipt.get("production_allowed") is not False
        or alias_receipt.get("historical_alias_authority_allowed") is not False
        or alias_receipt.get("numeric_period_or_value_features_allowed") is not False
        or not isinstance(summary, dict)
        or summary.get("mapping_state") != mapping.get("state")
        or summary.get("core_result_status") != result.get("status")
        or summary.get("automatic_selection_allowed") != result.get("automatic_selection_allowed")
        or summary.get("align_invocation_count") != exact.get("align_invocation_count")
        or summary.get("exact_status") != exact.get("status")
        or summary.get("source_row_count") != len(rows)
        or summary.get("selected_row_count") != selected_count
        or summary.get("unselected_row_count") != len(rows) - selected_count
        or summary.get("row_mapping_status_counts") != row_statuses
        or summary.get("schema_disposition_status_counts") != schema_statuses
        or summary.get("schema_node_count") != len(dispositions)
        or summary.get("mapping_result_sha256") != E0038_MAPPING_RESULT_SHA256
        or summary.get("result_projection_sha256") != RESULT_PROJECTION_SHA256
        or summary.get("changed_report_norm_ids") != [4375, 5699]
    ):
        raise E0039ReviewPacketError("E-0038 answer-free mapping summary drifted")


def _validate_e0037_e0038_selected_pair_parity(
    e0037: Mapping[str, Any],
    e0038: Mapping[str, Any],
) -> None:
    """Bind the 58 sealed mapping pairs without materializing any review answer."""

    mapping = e0037.get("mapping")
    best_path = mapping.get("best_path") if isinstance(mapping, dict) else None
    matches = best_path.get("matches") if isinstance(best_path, dict) else None
    if not isinstance(matches, list) or len(matches) != 58:
        raise E0039ReviewPacketError("E-0037 selected-pair projection drifted")
    e0037_projection = [
        {"row_id": item["row_id"], "report_norm_id": item["report_norm_id"]} for item in matches
    ]
    e0038_rows = e0038["exact_mapping_bundle"]["exact_search"][
        "mapping_result_without_internal_alias_authority"
    ]["row_mappings"]
    e0038_projection = [
        {
            "row_id": item["row_id"],
            "report_norm_id": item["selected_report_norm_id"],
        }
        for item in e0038_rows
        if item["selected_report_norm_id"] is not None
    ]
    if (
        e0037_projection != e0038_projection
        or len(e0038_projection) != 58
        or _canonical_sha256(e0037_projection) != E0037_E0038_SELECTED_PAIR_PROJECTION_SHA256
        or _canonical_sha256(e0038_projection) != E0037_E0038_SELECTED_PAIR_PROJECTION_SHA256
    ):
        raise E0039ReviewPacketError("E-0037/E-0038 selected-pair parity drifted")


def _validate_source_and_mapping_chain(
    source: dict[str, Any],
    e0037: dict[str, Any],
    e0038: dict[str, Any],
    manifest_rows: Mapping[str, Mapping[str, Any]],
    vietocr_rows: Mapping[str, Mapping[str, Any]],
    deepseek_rows: Mapping[str, Mapping[str, Any]],
) -> None:
    try:
        validate_source_only_structure(source)
        rows, dispositions = _validate_mapping_only_payload(e0037)
    except (E0037SourceStructureError, E0037SealedMappingError, TypeError, ValueError) as exc:
        raise _fail("E-0037 source/mapping payload validation failed", exc) from exc
    if len(rows) != 64 or len(dispositions) != 77:
        raise E0039ReviewPacketError("E-0037 source/mapping cardinality drifted")
    if e0037.get("source_structure") != _EXPECTED_FROZEN_INPUTS["e0037_source_structure"]:
        raise E0039ReviewPacketError("E-0037 source-structure linkage drifted")
    source_rows = source.get("rows")
    if not isinstance(source_rows, list) or len(source_rows) != 64:
        raise E0039ReviewPacketError("E-0037 source rows are absent")
    source_by_id = {row["row_id"]: row for row in source_rows}
    e0037_by_id = {row["row_id"]: row for row in rows}
    for row_id in TARGET_ROW_IDS:
        source_row = source_by_id[row_id]
        mapped_row = e0037_by_id[row_id]
        manifest_row = manifest_rows[row_id]
        deep_sample = deepseek_rows[row_id]
        proposals = mapped_row["semantic_proposals"]
        if (
            source_row["raw_label"] != manifest_row["ppocr_text"]
            or source_row["crop"]["path"] != manifest_row["crop_path"]
            or source_row["crop"]["sha256"] != manifest_row["crop_sha256"]
            or source_row["page_render"]
            != {
                **PAGE_RENDER_IDENTITIES[source_row["page"]],
                "verification": "TRANSITIVELY_HASH_BOUND_BY_E0035_MANIFEST_NOT_OPENED",
            }
            or mapped_row["source_order"] != source_row["source_order"]
            or mapped_row["source_structure"]["row_role"] != source_row["row_role"]
            or proposals.get("ppocrv6_source") != source_row["raw_label"]
            or proposals.get("vietocr") != vietocr_rows[row_id]["raw_prediction"]
            or (
                deep_sample["status"] == "PARSED_SEMANTIC_PROPOSAL_ONLY"
                and proposals.get("deepseek_ocr2") != deep_sample["proposal_text"]
            )
            or (
                deep_sample["status"] != "PARSED_SEMANTIC_PROPOSAL_ONLY"
                and "deepseek_ocr2" in proposals
            )
        ):
            raise E0039ReviewPacketError(f"source/reader/mapping linkage drifted for {row_id}")
    _validate_e0037_e0038_selected_pair_parity(e0037, e0038)


def _validate_alias_policy(
    policy: dict[str, Any],
    e0038: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _exact_keys(
        policy,
        {
            "version",
            "mode",
            "status",
            "statement_type",
            "candidate_count",
            "base_projection",
            "normalization",
            "score_audit",
            "collision_gate",
            "authority",
            "candidates",
        },
        "E-0038 alias policy",
    )
    expected_authority = {
        "source": "E0038_CALIBRATION_FAILURE_HYPOTHESIS",
        "review_or_steward_approved": False,
        "production_allowed": False,
        "holdout_evidence_allowed": False,
        "historical_alias_authority_allowed": False,
        "numeric_period_or_value_features_allowed": False,
    }
    candidates = policy.get("candidates")
    if (
        policy.get("version") != 1
        or policy.get("mode") != "ID_SCOPED_ADDITIVE_EXACT_STRUCTURAL_ALIAS_CANDIDATES"
        or policy.get("status") != "CALIBRATION_HYPOTHESIS_NOT_SCHEMA_AUTHORITY"
        or policy.get("statement_type") != "CDKT"
        or policy.get("candidate_count") != 2
        or policy.get("base_projection") != {"node_count": 77, "sha256": BASE_PROJECTION_SHA256}
        or policy.get("normalization") != "EXISTING_RETRIEVAL_KEY_V1_UNCHANGED"
        or policy.get("authority") != expected_authority
        or not isinstance(candidates, list)
        or len(candidates) != 2
    ):
        raise E0039ReviewPacketError("E-0038 alias policy identity drifted")
    expected_candidates = [
        {
            "candidate_id": candidate_id,
            "report_norm_id": report_norm_id,
            "alias_text": alias_text,
            "provenance": "E0038_CALIBRATION_FAILURE_HYPOTHESIS",
            "approval_status": "NOT_REVIEW_OR_STEWARD_APPROVED",
            "production_allowed": False,
        }
        for candidate_id, _row_id, report_norm_id, alias_text in ALIAS_ROW_BINDINGS
    ]
    if candidates != expected_candidates:
        raise E0039ReviewPacketError("E-0038 alias candidates drifted")
    receipt = e0038["exact_mapping_bundle"]["alias_overlay_receipt"]
    if (
        e0038["exact_mapping_bundle"].get("alias_overlay_receipt_sha256") != ALIAS_RECEIPT_SHA256
        or receipt.get("config_sha256") != _EXPECTED_FROZEN_INPUTS["e0038_alias_policy"]["sha256"]
        or receipt.get("config_size_bytes")
        != _EXPECTED_FROZEN_INPUTS["e0038_alias_policy"]["size_bytes"]
        or receipt.get("changed_report_norm_ids") != [4375, 5699]
        or receipt.get("base_projection_sha256") != BASE_PROJECTION_SHA256
        or receipt.get("result_projection_sha256") != RESULT_PROJECTION_SHA256
        or receipt.get("collision_delta_pair_count") != 0
        or receipt.get("new_collision_pairs") != []
        or receipt.get("review_or_steward_approved") is not False
        or receipt.get("production_allowed") is not False
        or receipt.get("holdout_evidence_allowed") is not False
        or receipt.get("historical_alias_authority_allowed") is not False
        or receipt.get("numeric_period_or_value_features_allowed") is not False
        or not isinstance(receipt.get("score_audits"), list)
        or len(receipt["score_audits"]) != 2
    ):
        raise E0039ReviewPacketError("E-0038 alias receipt drifted")
    return cast(list[dict[str, Any]], candidates), cast(dict[str, Any], receipt)


def _result_projection_nodes(
    base_nodes: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    aliases = {item["report_norm_id"]: item["alias_text"] for item in candidates}
    result: list[dict[str, Any]] = []
    for node in base_nodes:
        structural_aliases = list(node["structural_aliases"])
        if node["report_norm_id"] in aliases:
            structural_aliases.append(aliases[node["report_norm_id"]])
        result.append(
            {
                "report_norm_id": node["report_norm_id"],
                "canonical_name": node["display_name"],
                "structural_aliases": structural_aliases,
                "statement_type": "CDKT",
                "display_order": node["display_order"],
                "parent_report_norm_id": node["parent_report_norm_id"],
                "child_report_norm_ids": list(node["child_report_norm_ids"]),
                "hierarchy_level": node["hierarchy_level"],
                "section_path": list(node["section_path"]),
                "scopes": list(node["scopes"]),
            }
        )
    if _canonical_sha256(result) != RESULT_PROJECTION_SHA256:
        raise E0039ReviewPacketError("reconstructed E-0038 result projection drifted")
    return result


def _validate_target_intervals(intervals: Mapping[int, Mapping[str, Any]]) -> None:
    for interval_index, expected in _EXPECTED_TARGET_INTERVALS.items():
        interval = intervals.get(interval_index)
        if interval is None:
            raise E0039ReviewPacketError(f"target interval {interval_index} is absent")
        if (
            interval.get("row_ids") != expected["row_ids"]
            or interval.get("report_norm_ids") != expected["report_norm_ids"]
            or [
                interval.get("previous_anchor_row_id"),
                interval.get("previous_anchor_report_norm_id"),
            ]
            != expected["previous_anchor"]
            or [
                interval.get("next_anchor_row_id"),
                interval.get("next_anchor_report_norm_id"),
            ]
            != expected["next_anchor"]
            or interval.get("status") != expected["status"]
            or interval.get("reason") != expected["reason"]
            or _canonical_sha256(interval) != expected["canonical_sha256"]
        ):
            raise E0039ReviewPacketError(
                f"target interval {interval_index} content or order drifted"
            )


def _reader_proposals(
    row_id: str,
    vietocr_rows: Mapping[str, Mapping[str, Any]],
    deepseek_rows: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    viet = vietocr_rows[row_id]
    deep = deepseek_rows[row_id]
    return [
        {
            "reader_id": "deepseek_ocr2",
            "reader": "DEEPSEEK_OCR_2",
            "sample_status": deep["status"],
            "proposal_available": deep["status"] == "PARSED_SEMANTIC_PROPOSAL_ONLY",
            "proposal_text": (
                deep["proposal_text"] if deep["status"] == "PARSED_SEMANTIC_PROPOSAL_ONLY" else None
            ),
            "raw_rejected_output_included": False,
        },
        {
            "reader_id": "vietocr",
            "reader": "VIETOCR_VGG_TRANSFORMER",
            "sample_status": "PROPOSAL_AVAILABLE",
            "proposal_available": True,
            "proposal_text": viet["raw_prediction"],
            "raw_rejected_output_included": False,
        },
    ]


def _source_visible_evidence(
    row_id: str,
    manifest_rows: Mapping[str, Mapping[str, Any]],
    source_rows: Mapping[str, Mapping[str, Any]],
    stable_inputs: Mapping[str, _StableFile],
) -> dict[str, Any]:
    manifest = manifest_rows[row_id]
    source = source_rows[row_id]
    page = cast(int, manifest["page"])
    crop_stable = next(
        stable
        for name, stable in stable_inputs.items()
        if name.startswith("crop_page_") and stable.artifact["path"] == manifest["crop_path"]
    )
    return {
        "row_id": row_id,
        "page": page,
        "row_ordinal": manifest["row_ordinal"],
        "source_order": source["source_order"],
        "raw_visible_ppocr_label": source["raw_label"],
        "ppocr_label_provenance": copy.deepcopy(source["label_provenance"]),
        "source_crop": copy.deepcopy(crop_stable.artifact),
        "source_crop_bbox": copy.deepcopy(manifest["source_crop_bbox"]),
        "label_union_bbox": copy.deepcopy(manifest["label_union_bbox"]),
        "page_render": {
            **copy.deepcopy(PAGE_RENDER_IDENTITIES[page]),
            "verification": "TRANSITIVELY_HASH_BOUND_NOT_OPENED_BY_E0039",
        },
        "typography": copy.deepcopy(source["typography"]),
    }


def _adjacent_anchor(
    row_id: str | None,
    report_norm_id: int | None,
    *,
    e0038_anchors: Mapping[str, Mapping[str, Any]],
    e0038_rows: Mapping[str, Mapping[str, Any]],
    e0037_rows: Mapping[str, Mapping[str, Any]],
    source_rows: Mapping[str, Mapping[str, Any]],
    schema_nodes: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any] | None:
    if row_id is None or report_norm_id is None:
        return None
    anchor = e0038_anchors.get(row_id)
    current = e0038_rows.get(row_id)
    source = source_rows.get(row_id)
    prior = e0037_rows.get(row_id)
    node = schema_nodes.get(report_norm_id)
    if (
        anchor is None
        or current is None
        or source is None
        or prior is None
        or node is None
        or anchor.get("selection_allowed") is not True
        or anchor.get("selected_report_norm_id") != report_norm_id
        or current.get("selected_report_norm_id") != report_norm_id
    ):
        raise E0039ReviewPacketError(f"adjacent selected anchor drifted: {row_id}")
    alias_candidate_by_id = {
        report_id: candidate_id
        for candidate_id, _alias_row_id, report_id, _alias_text in ALIAS_ROW_BINDINGS
    }
    dependency = alias_candidate_by_id.get(report_norm_id)
    return {
        "row_id": row_id,
        "page": source["page"],
        "row_ordinal": source["row_ordinal"],
        "source_order": source["source_order"],
        "raw_visible_ppocr_label": source["raw_label"],
        "report_norm_id": report_norm_id,
        "e0037_status": prior["mapping"]["status"],
        "e0038_status": current["status"],
        "schema_node": copy.deepcopy(node),
        "alias_hypothesis_dependency": dependency,
        "authority": (
            "E0038_ALIAS_DEPENDENT_UNAPPROVED_CALIBRATION_HYPOTHESIS"
            if dependency is not None
            else "E0038_SELECTED_MAPPING_FACT_NOT_ROW_REVIEW_ANSWER"
        ),
        "row_adjudicator_may_approve_schema_alias": False,
    }


def _build_unselected_rows(
    *,
    manifest_rows: Mapping[str, Mapping[str, Any]],
    source_rows: Mapping[str, Mapping[str, Any]],
    e0037_rows: Mapping[str, Mapping[str, Any]],
    e0038_rows: Mapping[str, Mapping[str, Any]],
    e0038_anchors: Mapping[str, Mapping[str, Any]],
    intervals: Mapping[int, Mapping[str, Any]],
    schema_nodes: Mapping[int, Mapping[str, Any]],
    schema_dispositions: Mapping[int, Mapping[str, Any]],
    vietocr_rows: Mapping[str, Mapping[str, Any]],
    deepseek_rows: Mapping[str, Mapping[str, Any]],
    stable_inputs: Mapping[str, _StableFile],
) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for row_id in UNSELECTED_ROW_IDS:
        current = e0038_rows[row_id]
        prior = e0037_rows[row_id]
        source = source_rows[row_id]
        anchor = e0038_anchors[row_id]
        interval_index = current.get("interval_index")
        expected = _EXPECTED_UNSELECTED_DIAGNOSTICS[row_id]
        if (
            current.get("selected_report_norm_id") is not None
            or current.get("status") != expected["e0038_status"]
            or current.get("candidate_report_norm_ids") != expected["e0038_candidates"]
            or interval_index != expected["e0038_interval_index"]
            or prior["mapping"].get("selected_report_norm_id") is not None
            or prior["mapping"].get("status") != expected["e0037_status"]
            or prior["mapping"].get("candidate_report_norm_ids") != expected["e0037_candidates"]
            or type(interval_index) is not int
            or interval_index not in intervals
            or anchor.get("selection_allowed") is not False
            or anchor.get("selected_report_norm_id") is not None
        ):
            raise E0039ReviewPacketError(f"E-0038 unselected-row identity drifted: {row_id}")
        interval = intervals[interval_index]
        if row_id not in interval["row_ids"]:
            raise E0039ReviewPacketError(f"E-0038 interval does not contain {row_id}")
        interval_schema_ids = interval["report_norm_ids"]
        node_snapshots = [copy.deepcopy(schema_nodes[item]) for item in interval_schema_ids]
        disposition_snapshots = [
            copy.deepcopy(schema_dispositions[item]) for item in interval_schema_ids
        ]
        previous_anchor = _adjacent_anchor(
            interval["previous_anchor_row_id"],
            interval["previous_anchor_report_norm_id"],
            e0038_anchors=e0038_anchors,
            e0038_rows=e0038_rows,
            e0037_rows=e0037_rows,
            source_rows=source_rows,
            schema_nodes=schema_nodes,
        )
        next_anchor = _adjacent_anchor(
            interval["next_anchor_row_id"],
            interval["next_anchor_report_norm_id"],
            e0038_anchors=e0038_anchors,
            e0038_rows=e0038_rows,
            e0037_rows=e0037_rows,
            source_rows=source_rows,
            schema_nodes=schema_nodes,
        )
        dependencies = [
            item["alias_hypothesis_dependency"]
            for item in (previous_anchor, next_anchor)
            if item is not None and item["alias_hypothesis_dependency"] is not None
        ]
        packets.append(
            {
                "row_id": row_id,
                "source_visible_label_evidence": _source_visible_evidence(
                    row_id,
                    manifest_rows,
                    source_rows,
                    stable_inputs,
                ),
                "sealed_reader_proposals": _reader_proposals(
                    row_id,
                    vietocr_rows,
                    deepseek_rows,
                ),
                "current_source_structure": {
                    "row_role": source["row_role"],
                    "row_role_candidates": copy.deepcopy(source["row_role_candidates"]),
                    "typography_role": source["typography_role"],
                    "physical_parent_row_id": source["physical_parent_row_id"],
                    "section_row_id": source["section_row_id"],
                    "child_set_complete": source["child_set_complete"],
                    "structural_evidence": copy.deepcopy(source["structural_evidence"]),
                },
                "current_mapping_diagnostics": {
                    "e0037": copy.deepcopy(prior["mapping"]),
                    "e0038": copy.deepcopy(current),
                    "e0038_anchor_gate": {
                        "status": anchor["status"],
                        "selection_allowed": anchor["selection_allowed"],
                        "reason": anchor["reason"],
                    },
                },
                "ordered_interval_universe": {
                    "interval": copy.deepcopy(interval),
                    "schema_nodes_in_workbook_order": node_snapshots,
                    "schema_dispositions_in_workbook_order": disposition_snapshots,
                    "universe_is_full_not_candidate_filtered": True,
                },
                "adjacent_selected_anchors": {
                    "previous": previous_anchor,
                    "next": next_anchor,
                },
                "alias_hypothesis_dependencies": dependencies,
                "row_adjudication_cannot_approve_alias_dependencies": True,
            }
        )
    return packets


def _build_alias_rows(
    *,
    candidates: list[dict[str, Any]],
    receipt: Mapping[str, Any],
    manifest_rows: Mapping[str, Mapping[str, Any]],
    source_rows: Mapping[str, Mapping[str, Any]],
    e0037_rows: Mapping[str, Mapping[str, Any]],
    e0038_rows: Mapping[str, Mapping[str, Any]],
    base_nodes: Mapping[int, Mapping[str, Any]],
    result_nodes: Mapping[int, Mapping[str, Any]],
    vietocr_rows: Mapping[str, Mapping[str, Any]],
    deepseek_rows: Mapping[str, Mapping[str, Any]],
    stable_inputs: Mapping[str, _StableFile],
) -> list[dict[str, Any]]:
    audits = {item["candidate_id"]: item for item in receipt["score_audits"]}
    candidate_by_id = {item["candidate_id"]: item for item in candidates}
    packets: list[dict[str, Any]] = []
    for candidate_id, row_id, report_norm_id, alias_text in ALIAS_ROW_BINDINGS:
        candidate = candidate_by_id[candidate_id]
        audit = audits.get(candidate_id)
        current = e0038_rows[row_id]
        if (
            audit is None
            or candidate.get("report_norm_id") != report_norm_id
            or candidate.get("alias_text") != alias_text
            or audit.get("report_norm_id") != report_norm_id
            or audit.get("alias_text") != alias_text
            or current.get("selected_report_norm_id") != report_norm_id
            or current.get("status") != "RESOLVED_ANCHOR"
        ):
            raise E0039ReviewPacketError(f"E-0038 alias-row binding drifted: {candidate_id}")
        packets.append(
            {
                "candidate_id": candidate_id,
                "source_row_id": row_id,
                "source_visible_label_evidence": _source_visible_evidence(
                    row_id,
                    manifest_rows,
                    source_rows,
                    stable_inputs,
                ),
                "sealed_reader_proposals": _reader_proposals(
                    row_id,
                    vietocr_rows,
                    deepseek_rows,
                ),
                "e0037_mapping_diagnostic": copy.deepcopy(e0037_rows[row_id]["mapping"]),
                "e0038_current_mapping_fact": copy.deepcopy(current),
                "hypothesis": copy.deepcopy(candidate),
                "base_schema_node": copy.deepcopy(base_nodes[report_norm_id]),
                "result_projection_node_snapshot": copy.deepcopy(result_nodes[report_norm_id]),
                "score_audit": copy.deepcopy(audit),
                "collision_audit": {
                    "base_collision_groups": copy.deepcopy(receipt["base_collision_groups"]),
                    "result_collision_groups": copy.deepcopy(receipt["result_collision_groups"]),
                    "new_collision_pairs": copy.deepcopy(receipt["new_collision_pairs"]),
                    "collision_delta_pair_count": receipt["collision_delta_pair_count"],
                },
                "unapproved_authority": {
                    "alias_authority": receipt["alias_authority"],
                    "review_or_steward_approved": False,
                    "schema_authority": False,
                    "automatic_mapping_adoption": False,
                    "production_allowed": False,
                    "holdout_evidence_allowed": False,
                    "historical_alias_authority_allowed": False,
                    "numeric_period_or_value_features_allowed": False,
                },
            }
        )
    return packets


def _reject_response_leaks(value: object, label: str) -> None:
    forbidden_fragments = ("answer", "default", "recommend", "response", "suggest")
    response_only_keys = {
        "decision",
        "adjudicated_source_label",
        "adjudicated_row_role",
        "replacement_text",
        "rationale",
        "reviewer_identity",
        "steward_identity",
        "reviewed_at_utc",
        "decided_at_utc",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise E0039ReviewPacketError(f"{label} contains a non-text key")
            folded = key.casefold()
            if key in response_only_keys or any(token in folded for token in forbidden_fragments):
                raise E0039ReviewPacketError(
                    f"{label} leaked a response or preference field: {key}"
                )
            _reject_response_leaks(child, label)
    elif isinstance(value, list):
        for child in value:
            _reject_response_leaks(child, label)


def _validate_exact_artifact_record(
    value: object,
    expected: Mapping[str, Any],
    label: str,
) -> None:
    record = _exact_keys(value, {"path", "sha256", "size_bytes"}, label)
    if record != expected:
        raise E0039ReviewPacketError(f"{label} identity drifted")


def _validate_evidence_identity(value: object) -> None:
    evidence = _exact_keys(
        value,
        {
            "source_document_not_opened",
            "source_pixel_evidence",
            "sealed_semantic_readers",
            "mapping_chain",
            "workbook_and_projections",
        },
        "E-0039 evidence identity",
    )
    if evidence["source_document_not_opened"] != SOURCE_DOCUMENT:
        raise E0039ReviewPacketError("E-0039 unopened source-document identity drifted")

    pixels = _exact_keys(
        evidence["source_pixel_evidence"],
        {
            "e0035_s3",
            "crop_manifest",
            "page_renders",
            "target_source_crops",
            "source_structure",
        },
        "E-0039 source-pixel identity",
    )
    if pixels["e0035_s3"] != {
        "artifact_snapshot_id": ("20260807T050850Z-e0035-logical-row-label-crops-3b12da05e194"),
        "file_count": 65,
        "hydrate_probe": {
            "logical_path": CROP_MANIFEST_RELATIVE_PATH.as_posix(),
            "restored_file_count": 0,
            "reused_file_count": 1,
            "status": "PASS",
        },
        "restore_verified": True,
    }:
        raise E0039ReviewPacketError("E-0039 E-0035 S3 identity drifted")
    _validate_exact_artifact_record(
        pixels["crop_manifest"],
        _EXPECTED_FROZEN_INPUTS["crop_manifest"],
        "E-0039 crop-manifest evidence",
    )
    expected_page_renders = [
        {
            **PAGE_RENDER_IDENTITIES[page],
            "verification": "TRANSITIVELY_HASH_BOUND_NOT_OPENED_BY_E0039",
        }
        for page in (3, 4)
    ]
    if pixels["page_renders"] != expected_page_renders:
        raise E0039ReviewPacketError("E-0039 transitive page-render identities drifted")
    expected_crops = [_EXPECTED_FROZEN_INPUTS[name] for name in _TARGET_CROP_INPUT_NAMES]
    if pixels["target_source_crops"] != expected_crops:
        raise E0039ReviewPacketError("E-0039 exact eight-crop inventory drifted")
    _validate_exact_artifact_record(
        pixels["source_structure"],
        _EXPECTED_FROZEN_INPUTS["e0037_source_structure"],
        "E-0039 source-structure evidence",
    )

    readers = _exact_keys(
        evidence["sealed_semantic_readers"],
        {
            "artifact_snapshot_id",
            "reader_result_artifacts",
            "restore_verified",
            "state",
        },
        "E-0039 sealed-reader identity",
    )
    reader_artifacts = _exact_keys(
        readers["reader_result_artifacts"],
        {"deepseek_ocr2", "vietocr"},
        "E-0039 sealed-reader artifacts",
    )
    if (
        readers["artifact_snapshot_id"]
        != "20260807T055643Z-e0036-baseline-semantic-readers-3273a5cd3f84"
        or readers["restore_verified"] is not True
        or readers["state"] != "BASELINE_OUTPUTS_HASH_SEALED_BEFORE_REVIEW_ACCESS"
    ):
        raise E0039ReviewPacketError("E-0039 sealed-reader authority drifted")
    _validate_exact_artifact_record(
        reader_artifacts["deepseek_ocr2"],
        _EXPECTED_FROZEN_INPUTS["deepseek_result"],
        "E-0039 DeepSeek reader artifact",
    )
    _validate_exact_artifact_record(
        reader_artifacts["vietocr"],
        _EXPECTED_FROZEN_INPUTS["vietocr_result"],
        "E-0039 VietOCR reader artifact",
    )

    chain = _exact_keys(
        evidence["mapping_chain"],
        {
            "e0037_mapping_seal",
            "e0037_s3_snapshot",
            "e0037_mapping_only",
            "e0038_mapping_seal",
            "e0038_s3_registration",
            "e0038_s3_snapshot_id",
            "e0038_mapping_only",
            "review_coverage_identity",
        },
        "E-0039 mapping-chain identity",
    )
    for key in (
        "e0037_mapping_seal",
        "e0037_mapping_only",
        "e0038_mapping_seal",
        "e0038_s3_registration",
        "e0038_mapping_only",
    ):
        _validate_exact_artifact_record(
            chain[key],
            _EXPECTED_FROZEN_INPUTS[key],
            f"E-0039 mapping-chain {key}",
        )
    e0037_s3 = _exact_keys(
        chain["e0037_s3_snapshot"],
        {
            "artifact_snapshot_id",
            "dataset_role",
            "file_count",
            "format_version",
            "git_commit",
            "hydrate_probe",
            "label",
            "manifest",
            "parent_full_snapshot",
            "policy",
            "restore_verified",
            "run_record",
            "total_bytes",
        },
        "E-0039 E-0037 S3 snapshot",
    )
    if (
        e0037_s3["artifact_snapshot_id"] != E0037_S3_SNAPSHOT_ID
        or e0037_s3["dataset_role"] != "CALIBRATION"
        or e0037_s3["file_count"] != 2
        or e0037_s3["restore_verified"] is not True
        or chain["e0038_s3_snapshot_id"] != E0038_S3_SNAPSHOT_ID
    ):
        raise E0039ReviewPacketError("E-0039 S3 snapshot identity drifted")
    if chain["review_coverage_identity"] != {
        "authority_source": "E0038_MAPPING_ONLY_PRE_REVIEW_ACCESS_CONTRACT",
        "review_or_human_labels_opened": False,
        "target_row_adjudication_count": 0,
        "alias_steward_decision_count": 0,
        "prior_review_artifact_or_coverage_receipt_opened": False,
    }:
        raise E0039ReviewPacketError("E-0039 pre-review coverage identity drifted")

    projections = _exact_keys(
        evidence["workbook_and_projections"],
        {
            "workbook",
            "workbook_display_order_used",
            "numeric_report_norm_id_sort_used",
            "base_node_count",
            "base_projection_sha256",
            "result_node_count",
            "result_projection_sha256",
            "alias_receipt_sha256",
            "e0037_e0038_selected_pair_projection_sha256",
        },
        "E-0039 workbook/projection identity",
    )
    _validate_exact_artifact_record(
        projections["workbook"],
        _EXPECTED_FROZEN_INPUTS["cdkt_workbook"],
        "E-0039 workbook identity",
    )
    if projections != {
        "workbook": _EXPECTED_FROZEN_INPUTS["cdkt_workbook"],
        "workbook_display_order_used": True,
        "numeric_report_norm_id_sort_used": False,
        "base_node_count": 77,
        "base_projection_sha256": BASE_PROJECTION_SHA256,
        "result_node_count": 77,
        "result_projection_sha256": RESULT_PROJECTION_SHA256,
        "alias_receipt_sha256": ALIAS_RECEIPT_SHA256,
        "e0037_e0038_selected_pair_projection_sha256": (
            E0037_E0038_SELECTED_PAIR_PROJECTION_SHA256
        ),
    }:
        raise E0039ReviewPacketError("E-0039 workbook/projection values drifted")
    if _canonical_sha256(evidence) != _EXPECTED_EVIDENCE_IDENTITY_SHA256:
        raise E0039ReviewPacketError("E-0039 complete evidence identity drifted")


def _validate_row_packet_entries(rows: list[dict[str, Any]]) -> None:
    source_keys = {
        "row_id",
        "page",
        "row_ordinal",
        "source_order",
        "raw_visible_ppocr_label",
        "ppocr_label_provenance",
        "source_crop",
        "source_crop_bbox",
        "label_union_bbox",
        "page_render",
        "typography",
    }
    proposal_keys = {
        "reader_id",
        "reader",
        "sample_status",
        "proposal_available",
        "proposal_text",
        "raw_rejected_output_included",
    }
    node_keys = {
        "child_report_norm_ids",
        "display_name",
        "display_order",
        "hierarchy_level",
        "next_report_norm_id",
        "parent_report_norm_id",
        "previous_report_norm_id",
        "report_norm_id",
        "scopes",
        "section_path",
        "structural_aliases",
    }
    disposition_keys = {
        "candidate_row_ids",
        "reason",
        "report_norm_id",
        "selected_row_id",
        "status",
    }
    expected_dependency = {
        "page-0004-row-000-label": ["CDKT_4375_TOTAL_ASSETS_BANKING_WORDING"],
        "page-0004-row-023-label": ["CDKT_5699_NCI_POSSESSIVE_PARTICLE"],
    }
    for row in rows:
        row_id = row.get("row_id")
        _exact_keys(
            row,
            {
                "row_id",
                "source_visible_label_evidence",
                "sealed_reader_proposals",
                "current_source_structure",
                "current_mapping_diagnostics",
                "ordered_interval_universe",
                "adjacent_selected_anchors",
                "alias_hypothesis_dependencies",
                "row_adjudication_cannot_approve_alias_dependencies",
            },
            f"E-0039 row entry {row_id}",
        )
        if row_id not in _EXPECTED_UNSELECTED_DIAGNOSTICS:
            raise E0039ReviewPacketError("E-0039 row entry has an unexpected identity")
        source = _exact_keys(
            row["source_visible_label_evidence"],
            source_keys,
            f"E-0039 source evidence {row_id}",
        )
        proposals = row.get("sealed_reader_proposals")
        if (
            source.get("row_id") != row_id
            or not isinstance(proposals, list)
            or len(proposals) != 2
            or [item.get("reader_id") for item in proposals] != ["deepseek_ocr2", "vietocr"]
        ):
            raise E0039ReviewPacketError(f"E-0039 source/reader entry drifted: {row_id}")
        for proposal in proposals:
            _exact_keys(proposal, proposal_keys, f"E-0039 reader proposal {row_id}")
            if proposal.get("raw_rejected_output_included") is not False:
                raise E0039ReviewPacketError(f"rejected raw output leaked for {row_id}")
        expected_crop = next(
            record
            for name, record in _EXPECTED_FROZEN_INPUTS.items()
            if name in _TARGET_CROP_INPUT_NAMES
            and record["path"] == CROP_PATHS[cast(str, row_id)].as_posix()
        )
        expected_page = cast(int, source["page"])
        if source["source_crop"] != expected_crop or source["page_render"] != {
            **PAGE_RENDER_IDENTITIES[expected_page],
            "verification": "TRANSITIVELY_HASH_BOUND_NOT_OPENED_BY_E0039",
        }:
            raise E0039ReviewPacketError(f"E-0039 crop/render identity drifted: {row_id}")
        _exact_keys(
            row["current_source_structure"],
            {
                "row_role",
                "row_role_candidates",
                "typography_role",
                "physical_parent_row_id",
                "section_row_id",
                "child_set_complete",
                "structural_evidence",
            },
            f"E-0039 current source structure {row_id}",
        )
        diagnostics = _exact_keys(
            row["current_mapping_diagnostics"],
            {"e0037", "e0038", "e0038_anchor_gate"},
            f"E-0039 current mapping diagnostics {row_id}",
        )
        for version in ("e0037", "e0038"):
            _exact_keys(
                diagnostics[version],
                {
                    "candidate_report_norm_ids",
                    "interval_index",
                    "reason",
                    "row_id",
                    "selected_report_norm_id",
                    "status",
                },
                f"E-0039 {version} mapping diagnostic {row_id}",
            )
        expected = _EXPECTED_UNSELECTED_DIAGNOSTICS[cast(str, row_id)]
        if (
            diagnostics["e0037"]["status"] != expected["e0037_status"]
            or diagnostics["e0037"]["candidate_report_norm_ids"] != expected["e0037_candidates"]
            or diagnostics["e0038"]["status"] != expected["e0038_status"]
            or diagnostics["e0038"]["candidate_report_norm_ids"] != expected["e0038_candidates"]
            or diagnostics["e0038"]["selected_report_norm_id"] is not None
        ):
            raise E0039ReviewPacketError(f"E-0039 mapping diagnostic drifted: {row_id}")
        universe = _exact_keys(
            row["ordered_interval_universe"],
            {
                "interval",
                "schema_nodes_in_workbook_order",
                "schema_dispositions_in_workbook_order",
                "universe_is_full_not_candidate_filtered",
            },
            f"E-0039 ordered interval universe {row_id}",
        )
        interval = universe["interval"]
        interval_index = expected["e0038_interval_index"]
        expected_interval = _EXPECTED_TARGET_INTERVALS[cast(int, interval_index)]
        nodes = universe["schema_nodes_in_workbook_order"]
        dispositions = universe["schema_dispositions_in_workbook_order"]
        if (
            not isinstance(interval, dict)
            or _canonical_sha256(interval) != expected_interval["canonical_sha256"]
            or not isinstance(nodes, list)
            or [item.get("report_norm_id") for item in nodes]
            != expected_interval["report_norm_ids"]
            or not isinstance(dispositions, list)
            or [item.get("report_norm_id") for item in dispositions]
            != expected_interval["report_norm_ids"]
            or universe["universe_is_full_not_candidate_filtered"] is not True
        ):
            raise E0039ReviewPacketError(f"E-0039 interval universe drifted: {row_id}")
        for node in nodes:
            _exact_keys(node, node_keys, f"E-0039 schema snapshot {row_id}")
        for disposition in dispositions:
            _exact_keys(
                disposition,
                disposition_keys,
                f"E-0039 schema disposition {row_id}",
            )
        anchors = _exact_keys(
            row["adjacent_selected_anchors"],
            {"previous", "next"},
            f"E-0039 adjacent anchors {row_id}",
        )
        for direction in ("previous", "next"):
            anchor = _exact_keys(
                anchors[direction],
                {
                    "row_id",
                    "page",
                    "row_ordinal",
                    "source_order",
                    "raw_visible_ppocr_label",
                    "report_norm_id",
                    "e0037_status",
                    "e0038_status",
                    "schema_node",
                    "alias_hypothesis_dependency",
                    "authority",
                    "row_adjudicator_may_approve_schema_alias",
                },
                f"E-0039 {direction} anchor {row_id}",
            )
            _exact_keys(anchor["schema_node"], node_keys, f"E-0039 anchor node {row_id}")
            if anchor["row_adjudicator_may_approve_schema_alias"] is not False:
                raise E0039ReviewPacketError(f"row authority leaked alias approval: {row_id}")
        if (
            row["alias_hypothesis_dependencies"] != expected_dependency.get(cast(str, row_id), [])
            or row["row_adjudication_cannot_approve_alias_dependencies"] is not True
        ):
            raise E0039ReviewPacketError(f"alias dependency marker drifted: {row_id}")
        _reject_response_leaks(row, f"E-0039 row evidence {row_id}")
        if _canonical_sha256(row) != _EXPECTED_ROW_ENTRY_SHA256[cast(str, row_id)]:
            raise E0039ReviewPacketError(
                f"E-0039 complete canonical row evidence drifted: {row_id}"
            )


def _validate_alias_packet_entries(rows: list[dict[str, Any]]) -> None:
    expected = {item[0]: item for item in ALIAS_ROW_BINDINGS}
    for row in rows:
        candidate_id = row.get("candidate_id")
        _exact_keys(
            row,
            {
                "candidate_id",
                "source_row_id",
                "source_visible_label_evidence",
                "sealed_reader_proposals",
                "e0037_mapping_diagnostic",
                "e0038_current_mapping_fact",
                "hypothesis",
                "base_schema_node",
                "result_projection_node_snapshot",
                "score_audit",
                "collision_audit",
                "unapproved_authority",
            },
            f"E-0039 alias entry {candidate_id}",
        )
        if candidate_id not in expected:
            raise E0039ReviewPacketError("E-0039 alias entry has an unexpected identity")
        _, source_row_id, report_norm_id, alias_text = expected[cast(str, candidate_id)]
        hypothesis = row["hypothesis"]
        if (
            row.get("source_row_id") != source_row_id
            or hypothesis.get("candidate_id") != candidate_id
            or hypothesis.get("report_norm_id") != report_norm_id
            or hypothesis.get("alias_text") != alias_text
            or hypothesis.get("approval_status") != "NOT_REVIEW_OR_STEWARD_APPROVED"
            or hypothesis.get("production_allowed") is not False
            or row["e0038_current_mapping_fact"].get("selected_report_norm_id") != report_norm_id
            or row["e0038_current_mapping_fact"].get("status") != "RESOLVED_ANCHOR"
            or row["unapproved_authority"].get("review_or_steward_approved") is not False
            or row["unapproved_authority"].get("schema_authority") is not False
            or row["unapproved_authority"].get("automatic_mapping_adoption") is not False
        ):
            raise E0039ReviewPacketError(f"E-0039 alias evidence drifted: {candidate_id}")
        _reject_response_leaks(row, f"E-0039 alias evidence {candidate_id}")
        if _canonical_sha256(row) != _EXPECTED_ALIAS_ENTRY_SHA256[cast(str, candidate_id)]:
            raise E0039ReviewPacketError(
                f"E-0039 complete canonical alias evidence drifted: {candidate_id}"
            )


def _validate_packet_payload(
    payload: Mapping[str, Any],
    *,
    expected_control_artifact: Mapping[str, Any],
    expected_implementation_artifacts: Mapping[str, Mapping[str, Any]],
    expected_git_commit: str,
) -> None:
    _exact_keys(
        payload,
        {
            "identity",
            "state",
            "input_artifacts",
            "evidence_identity",
            "deterministic_replay",
            "access_contract",
            "row_review_packet",
            "alias_steward_packet",
            "blank_response_contracts",
            "authority",
            "claim_boundary",
        },
        "E-0039 review packet",
    )
    identity = _exact_keys(
        payload.get("identity"),
        {
            "format_version",
            "experiment_id",
            "dataset_role",
            "capture_git_commit",
            "capture_git_dirty",
            "control",
            "implementation",
        },
        "E-0039 packet identity",
    )
    input_artifacts = _exact_keys(
        payload.get("input_artifacts"),
        set(_EXPECTED_FROZEN_INPUTS),
        "E-0039 packet input artifacts",
    )
    if input_artifacts != _EXPECTED_FROZEN_INPUTS:
        raise E0039ReviewPacketError("E-0039 packet input-artifact identities drifted")
    _validate_evidence_identity(payload.get("evidence_identity"))
    access = _exact_keys(
        payload.get("access_contract"),
        set(_EXPECTED_PACKET_ACCESS_CONTRACT),
        "E-0039 packet access contract",
    )
    if access != _EXPECTED_PACKET_ACCESS_CONTRACT:
        raise E0039ReviewPacketError("E-0039 packet access contract drifted")
    control_identity = _exact_keys(
        identity.get("control"),
        {"path", "sha256", "size_bytes"},
        "E-0039 packet control identity",
    )
    implementation_identity = _exact_keys(
        identity.get("implementation"),
        set(_IMPLEMENTATION_PATHS),
        "E-0039 packet implementation identity",
    )
    if control_identity != expected_control_artifact:
        raise E0039ReviewPacketError("E-0039 packet control identity drifted")
    if set(expected_implementation_artifacts) != set(_IMPLEMENTATION_PATHS):
        raise E0039ReviewPacketError("E-0039 expected implementation ledger drifted")
    for name, path in _IMPLEMENTATION_PATHS.items():
        record = _exact_keys(
            implementation_identity[name],
            {"path", "sha256", "size_bytes"},
            f"E-0039 packet implementation {name}",
        )
        if (
            record != expected_implementation_artifacts[name]
            or record.get("path") != path.as_posix()
        ):
            raise E0039ReviewPacketError(f"E-0039 packet implementation identity drifted: {name}")
    row_packet = _exact_keys(
        payload.get("row_review_packet"),
        {
            "packet_type",
            "row_count",
            "row_ids",
            "rows",
            "decision_status",
            "authority_required",
            "authority_boundary",
        },
        "E-0039 row-review packet",
    )
    alias_packet = _exact_keys(
        payload.get("alias_steward_packet"),
        {
            "packet_type",
            "candidate_count",
            "candidate_ids",
            "rows",
            "decision_status",
            "authority_required",
            "authority_boundary",
        },
        "E-0039 alias-steward packet",
    )
    responses = _exact_keys(
        payload.get("blank_response_contracts"),
        {"vocabulary_ordering", "row_adjudication", "alias_stewardship"},
        "E-0039 blank response contracts",
    )
    row_response = _exact_keys(
        responses.get("row_adjudication"),
        {"template", "allowed_vocabulary", "decision_constraints"},
        "E-0039 row response contract",
    )
    alias_response = _exact_keys(
        responses.get("alias_stewardship"),
        {"template", "allowed_vocabulary", "decision_constraints"},
        "E-0039 alias response contract",
    )
    replay = _exact_keys(
        payload.get("deterministic_replay"),
        {
            "evidence_assembly_invocation_count",
            "exact_canonical_byte_equality",
            "canonical_encoding",
            "evidence_sections_sha256",
        },
        "E-0039 deterministic replay",
    )
    if (
        identity.get("format_version") != 1
        or identity.get("experiment_id") != "E-0039"
        or identity.get("dataset_role") != "CALIBRATION"
        or identity.get("capture_git_commit") != expected_git_commit
        or identity.get("capture_git_dirty") is not False
        or payload.get("state") != PACKET_STATE
        or replay.get("evidence_assembly_invocation_count") != 2
        or replay.get("exact_canonical_byte_equality") is not True
        or replay.get("canonical_encoding")
        != "UTF8_JSON_SORTED_KEYS_COMPACT_NO_NAN_NO_DUPLICATE_KEYS_V1"
        or not isinstance(replay.get("evidence_sections_sha256"), str)
        or len(replay["evidence_sections_sha256"]) != 64
        or row_packet.get("packet_type") != "UNSELECTED_ROW_ADJUDICATION_EVIDENCE_ONLY"
        or row_packet.get("row_count") != 6
        or row_packet.get("row_ids") != list(UNSELECTED_ROW_IDS)
        or row_packet.get("decision_status") != "NOT_STARTED_BLANK_RESPONSE_REQUIRED"
        or row_packet.get("authority_required") != "INDEPENDENT_ROW_ADJUDICATOR"
        or row_packet.get("authority_boundary")
        != "MAY_ADJUDICATE_ROWS_BUT_MAY_NOT_APPROVE_SCHEMA_ALIASES"
        or not isinstance(row_packet.get("rows"), list)
        or [row.get("row_id") for row in row_packet["rows"]] != list(UNSELECTED_ROW_IDS)
        or alias_packet.get("packet_type") != "SCHEMA_ALIAS_STEWARD_EVIDENCE_ONLY"
        or alias_packet.get("candidate_count") != 2
        or alias_packet.get("candidate_ids") != [item[0] for item in ALIAS_ROW_BINDINGS]
        or alias_packet.get("decision_status") != "NOT_STARTED_BLANK_RESPONSE_REQUIRED"
        or alias_packet.get("authority_required") != "REVIEW_INDEPENDENT_SCHEMA_STEWARD"
        or alias_packet.get("authority_boundary")
        != "MAY_DECIDE_ID_SCOPED_ALIAS_BUT_MAY_NOT_ADJUDICATE_SOURCE_ROWS"
        or not isinstance(alias_packet.get("rows"), list)
        or [row.get("candidate_id") for row in alias_packet["rows"]]
        != [item[0] for item in ALIAS_ROW_BINDINGS]
        or responses.get("vocabulary_ordering") != "ALPHABETIC_NON_PREFERENTIAL_NO_DEFAULT"
        or row_response.get("template") != ROW_RESPONSE_TEMPLATE
        or row_response.get("allowed_vocabulary") != ROW_RESPONSE_VOCABULARY
        or row_response.get("decision_constraints") != ROW_DECISION_CONSTRAINTS
        or alias_response.get("template") != ALIAS_RESPONSE_TEMPLATE
        or alias_response.get("allowed_vocabulary") != ALIAS_RESPONSE_VOCABULARY
        or alias_response.get("decision_constraints") != ALIAS_DECISION_CONSTRAINTS
        or any(value is not None for value in row_response["template"].values())
        or any(value is not None for value in alias_response["template"].values())
        or payload.get("claim_boundary") != _CLAIM_BOUNDARY
    ):
        raise E0039ReviewPacketError("E-0039 packet identity or blank responses drifted")
    _validate_row_packet_entries(cast(list[dict[str, Any]], row_packet["rows"]))
    _validate_alias_packet_entries(cast(list[dict[str, Any]], alias_packet["rows"]))
    if replay["evidence_sections_sha256"] != _canonical_sha256(
        {
            "row_review_rows": row_packet["rows"],
            "alias_steward_rows": alias_packet["rows"],
        }
    ):
        raise E0039ReviewPacketError("E-0039 deterministic evidence digest drifted")
    authority = payload.get("authority")
    if not isinstance(authority, dict) or authority != {
        "dataset_role": "CALIBRATION_ONLY",
        "predecision_evidence_packet": True,
        "source_pixel_and_sealed_reader_identity": True,
        "e0037_e0038_mapping_identity": True,
        "prior_review_artifact_or_coverage_receipt_opened": False,
        "row_adjudication_completed": False,
        "schema_steward_decision_completed": False,
        "schema_alias_approval": False,
        "schema_authority": False,
        "automatic_mapping_adoption": False,
        "numeric_period_or_unit": False,
        "accounting_or_excel": False,
        "history_or_mongodb": False,
        "holdout_or_production": False,
    }:
        raise E0039ReviewPacketError("E-0039 packet authority drifted")


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
            name=f"E-0039 {name}",
            expected_path=path,
            reader=reader,
        )
    except E0038ExactMappingError as exc:
        raise _fail(f"cannot bind E-0039 {name} to Git HEAD", exc) from exc


def _encoded_packet_json(payload: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise _fail("E-0039 packet is not canonical JSON data", exc) from exc


def _exclusive_publish_compact_json(
    root: Path,
    path: Path,
    payload: Mapping[str, Any],
    *,
    exclusive_parent_inventory: tuple[str, ...],
) -> str:
    """Use E-0038's hardened link/recheck protocol with compact canonical bytes."""

    if not path.is_relative_to(root):
        raise E0039ReviewPacketError("E-0039 output path escapes project root")
    relative = path.relative_to(root)
    try:
        parent, final_name = _open_or_create_parent_directory(root, relative, "E-0039 output")
    except E0037SealedMappingError as exc:
        raise _fail("cannot open E-0039 output parent", exc) from exc
    encoded = _encoded_packet_json(payload)
    digest = hashlib.sha256(encoded).hexdigest()
    temporary_name = f".{final_name}.{secrets.token_hex(16)}"
    temporary_created = False
    published_identity: os.stat_result | None = None
    try:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = os.open(temporary_name, flags, 0o600, dir_fd=parent)
            temporary_created = True
        except OSError as exc:
            raise E0039ReviewPacketError("cannot create temporary E-0039 packet") from exc
        try:
            view = memoryview(encoded)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise E0039ReviewPacketError("short write for temporary E-0039 packet")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.chmod(temporary_name, 0o644, dir_fd=parent, follow_symlinks=False)
        temporary_identity = os.stat(temporary_name, dir_fd=parent, follow_symlinks=False)
        try:
            os.link(
                temporary_name,
                final_name,
                src_dir_fd=parent,
                dst_dir_fd=parent,
                follow_symlinks=False,
            )
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                raise E0039ReviewPacketError(
                    f"refusing to overwrite E-0039 packet: {path}"
                ) from exc
            raise E0039ReviewPacketError("cannot link E-0039 packet") from exc
        published_identity = os.stat(final_name, dir_fd=parent, follow_symlinks=False)
        if not _same_inode(temporary_identity, published_identity):
            raise E0039ReviewPacketError("E-0039 linked packet identity mismatch")
        os.unlink(temporary_name, dir_fd=parent)
        temporary_created = False
        os.fsync(parent)

        fresh_parent, fresh_name = _open_existing_parent_directory(
            root,
            relative,
            "E-0039 published packet",
        )
        try:
            held_parent = os.fstat(parent)
            canonical_parent = os.fstat(fresh_parent)
            canonical_file = os.stat(fresh_name, dir_fd=fresh_parent, follow_symlinks=False)
            canonical_inventory = tuple(sorted(os.listdir(fresh_parent)))
        finally:
            os.close(fresh_parent)
        if (
            not stat.S_ISDIR(held_parent.st_mode)
            or not stat.S_ISDIR(canonical_parent.st_mode)
            or (held_parent.st_dev, held_parent.st_ino)
            != (canonical_parent.st_dev, canonical_parent.st_ino)
            or not _same_inode(published_identity, canonical_file)
            or canonical_inventory != tuple(sorted(exclusive_parent_inventory))
        ):
            raise E0039ReviewPacketError(
                "E-0039 published parent/file detached from canonical path"
            )
        canonical = _read_from_fresh_canonical_path(
            root,
            path,
            "E-0039 published packet",
            expected_size=len(encoded),
            maximum_size=max(len(encoded), 1),
        )
        if canonical.payload != encoded or canonical.artifact["sha256"] != digest:
            raise E0039ReviewPacketError("E-0039 published bytes failed revalidation")
        final_parent, _ = _open_existing_parent_directory(
            root,
            relative,
            "E-0039 final publication inventory",
        )
        try:
            final_parent_identity = os.fstat(final_parent)
            final_inventory = tuple(sorted(os.listdir(final_parent)))
        finally:
            os.close(final_parent)
        if (final_parent_identity.st_dev, final_parent_identity.st_ino) != (
            held_parent.st_dev,
            held_parent.st_ino,
        ) or final_inventory != tuple(sorted(exclusive_parent_inventory)):
            raise E0039ReviewPacketError("E-0039 final canonical inventory drifted")
        os.fsync(parent)
    except Exception as exc:
        if published_identity is not None:
            try:
                _rollback_published_link(parent, final_name, published_identity)
            except E0038ExactMappingError as rollback_exc:
                raise _fail("cannot safely roll back E-0039 packet", rollback_exc) from rollback_exc
        if isinstance(exc, E0039ReviewPacketError):
            raise
        raise _fail("cannot securely publish E-0039 packet", exc) from exc
    finally:
        if temporary_created:
            try:
                os.unlink(temporary_name, dir_fd=parent)
                os.fsync(parent)
            except FileNotFoundError:
                pass
        os.close(parent)
    return digest


def capture_e0039_review_packet(
    project_root: Path,
    *,
    config_path: Path = CONTROL_RELATIVE_PATH,
    output_path: Path = OUTPUT_RELATIVE_PATH,
    _reader: StableReader | None = None,
) -> dict[str, Any]:
    """Validate all evidence and exclusively publish the blank E-0039 packet."""

    root = project_root.resolve()
    reader = _read_stable_file if _reader is None else _reader
    try:
        control_path = _canonical_path(root, config_path, CONTROL_RELATIVE_PATH, "E-0039 control")
        destination = _canonical_path(root, output_path, OUTPUT_RELATIVE_PATH, "E-0039 output")
        if destination.exists() or destination.is_symlink():
            raise E0039ReviewPacketError(f"refusing to overwrite E-0039 packet: {destination}")
        capture_commit = _clean_git_commit(root)
        control_stable = reader(
            root,
            control_path,
            "E-0039 review-packet control",
            maximum_size=_RESOURCE_CAPS["maximum_control_bytes"],
        )
        control = _decode_control(control_stable.payload)
        frozen, implementation_stable = _validate_control(root, control, reader)

        stable: dict[str, _StableFile] = {}

        # Source-visible crop evidence: seal first, then manifest, renders, and crops.
        stable["e0035_seal"] = _verified_record(reader, root, frozen["e0035_seal"], "e0035_seal")
        e0035_s3 = _validate_e0035_seal(_strict_json(stable["e0035_seal"], "E-0035 seal"))
        stable["crop_manifest"] = _verified_record(
            reader, root, frozen["crop_manifest"], "crop_manifest"
        )
        crop_manifest = _strict_json(stable["crop_manifest"], "E-0035 crop manifest")
        manifest_rows = _validate_crop_manifest(crop_manifest)
        for name in (
            "crop_page_0003_row_002",
            "crop_page_0003_row_003",
            "crop_page_0004_row_000",
            "crop_page_0004_row_002",
            "crop_page_0004_row_013",
            "crop_page_0004_row_023",
            "crop_page_0003_row_038",
            "crop_page_0004_row_022",
        ):
            stable[name] = _verified_record(reader, root, frozen[name], name)
        _validate_target_crop_files(manifest_rows, stable)

        # Reader bytes are opened only after their pre-review seal validates.
        stable["e0036_baseline_seal"] = _verified_record(
            reader, root, frozen["e0036_baseline_seal"], "e0036_baseline_seal"
        )
        e0036_identity = _validate_e0036_seal(
            _strict_json(stable["e0036_baseline_seal"], "E-0036 baseline seal")
        )
        stable["vietocr_result"] = _verified_record(
            reader, root, frozen["vietocr_result"], "vietocr_result"
        )
        stable["deepseek_result"] = _verified_record(
            reader, root, frozen["deepseek_result"], "deepseek_result"
        )
        vietocr = _strict_json(stable["vietocr_result"], "sealed VietOCR result")
        deepseek = _strict_json(stable["deepseek_result"], "sealed DeepSeek result")
        vietocr_rows, deepseek_rows = _validate_reader_outputs(
            vietocr,
            deepseek,
            manifest_rows,
        )

        # Validate the E-0037 seal and unique restore record before either E-0037 payload.
        stable["e0038_mapping_control"] = _verified_record(
            reader, root, frozen["e0038_mapping_control"], "e0038_mapping_control"
        )
        e0038_control = _decode_control(stable["e0038_mapping_control"].payload)
        stable["e0037_mapping_seal"] = _verified_record(
            reader, root, frozen["e0037_mapping_seal"], "e0037_mapping_seal"
        )
        e0037_seal = _strict_json(stable["e0037_mapping_seal"], "E-0037 mapping seal")
        _validate_e0037_seal_before_mapping_open(e0037_seal, e0038_control)
        stable["s3_registry"] = _verified_record(reader, root, frozen["s3_registry"], "s3_registry")
        _validate_canonical_jsonl(stable["s3_registry"].payload, "S3 registry")
        e0037_s3_record = _load_unique_s3_record(
            stable["s3_registry"].payload,
            cast(dict[str, Any], e0038_control["input_authority"])["s3_snapshot"],
        )
        stable["e0037_source_structure"] = _verified_record(
            reader, root, frozen["e0037_source_structure"], "e0037_source_structure"
        )
        stable["e0037_mapping_only"] = _verified_record(
            reader, root, frozen["e0037_mapping_only"], "e0037_mapping_only"
        )
        source_structure = _strict_json(stable["e0037_source_structure"], "E-0037 source structure")
        e0037 = _strict_json(stable["e0037_mapping_only"], "E-0037 mapping only")

        # Validate the E-0038 seal and post-seal S3 record before mapping bytes.
        stable["e0038_mapping_seal"] = _verified_record(
            reader, root, frozen["e0038_mapping_seal"], "e0038_mapping_seal"
        )
        e0038_seal = _strict_json(stable["e0038_mapping_seal"], "E-0038 mapping seal")
        _validate_e0038_mapping_seal_payload(
            e0038_seal,
            e0038_control,
            expected_control_artifact=stable["e0038_mapping_control"].artifact,
            expected_mapping_artifact=frozen["e0038_mapping_only"],
            expected_git_commit=e0038_seal["seal_git_commit"],
        )
        stable["e0038_s3_registration"] = _verified_record(
            reader, root, frozen["e0038_s3_registration"], "e0038_s3_registration"
        )
        e0038_registration = _strict_json(stable["e0038_s3_registration"], "E-0038 S3 registration")
        _validate_e0038_postseal_registration_answer_free(e0038_registration, e0038_seal)
        stable["e0038_mapping_only"] = _verified_record(
            reader, root, frozen["e0038_mapping_only"], "e0038_mapping_only"
        )
        e0038 = _strict_json(stable["e0038_mapping_only"], "E-0038 mapping only")
        _validate_e0038_mapping_answer_free(
            e0038,
            e0038_control,
            stable["e0038_mapping_control"].artifact,
            e0038_seal,
            e0038_registration,
        )
        _validate_source_and_mapping_chain(
            source_structure,
            e0037,
            e0038,
            manifest_rows,
            vietocr_rows,
            deepseek_rows,
        )

        stable["e0038_alias_policy"] = _verified_record(
            reader, root, frozen["e0038_alias_policy"], "e0038_alias_policy"
        )
        alias_policy = _decode_control(stable["e0038_alias_policy"].payload)
        candidates, alias_receipt = _validate_alias_policy(alias_policy, e0038)
        stable["cdkt_workbook"] = _verified_record(
            reader, root, frozen["cdkt_workbook"], "cdkt_workbook"
        )
        if tuple(stable) != _DIRECT_INPUT_READ_ORDER:
            raise E0039ReviewPacketError("E-0039 direct input read order drifted")
        actual_total_bytes = (
            control_stable.artifact["size_bytes"]
            + sum(item.artifact["size_bytes"] for item in implementation_stable.values())
            + sum(item.artifact["size_bytes"] for item in stable.values())
        )
        if (
            actual_total_bytes
            > _RESOURCE_CAPS["maximum_total_control_implementation_and_input_bytes"]
        ):
            raise E0039ReviewPacketError(
                "E-0039 actual control/implementation/input byte budget exceeded"
            )

        source_rows_list = cast(list[dict[str, Any]], source_structure["rows"])
        source_rows = {row["row_id"]: row for row in source_rows_list}
        e0037_rows_list = cast(list[dict[str, Any]], e0037["rows"])
        e0037_rows = {row["row_id"]: row for row in e0037_rows_list}
        base_nodes_list = cast(list[dict[str, Any]], e0037["schema_projection"]["nodes"])
        base_nodes = {node["report_norm_id"]: node for node in base_nodes_list}
        result_nodes_list = _result_projection_nodes(base_nodes_list, candidates)
        result_nodes = {node["report_norm_id"]: node for node in result_nodes_list}
        exact_result = e0038["exact_mapping_bundle"]["exact_search"][
            "mapping_result_without_internal_alias_authority"
        ]
        e0038_rows_list = cast(list[dict[str, Any]], exact_result["row_mappings"])
        e0038_rows = {row["row_id"]: row for row in e0038_rows_list}
        e0038_anchors_list = cast(list[dict[str, Any]], exact_result["anchors"])
        e0038_anchors = {row["row_id"]: row for row in e0038_anchors_list}
        intervals_list = cast(list[dict[str, Any]], exact_result["intervals"])
        if len(intervals_list) != _RESOURCE_CAPS["exact_e0038_interval_count"]:
            raise E0039ReviewPacketError("E-0038 interval count drifted")
        intervals = {row["interval_index"]: row for row in intervals_list}
        _validate_target_intervals(intervals)
        schema_dispositions_list = cast(list[dict[str, Any]], exact_result["schema_dispositions"])
        schema_dispositions = {row["report_norm_id"]: row for row in schema_dispositions_list}

        def assemble_evidence_sections() -> dict[str, list[dict[str, Any]]]:
            return {
                "row_review_rows": _build_unselected_rows(
                    manifest_rows=manifest_rows,
                    source_rows=source_rows,
                    e0037_rows=e0037_rows,
                    e0038_rows=e0038_rows,
                    e0038_anchors=e0038_anchors,
                    intervals=intervals,
                    schema_nodes=base_nodes,
                    schema_dispositions=schema_dispositions,
                    vietocr_rows=vietocr_rows,
                    deepseek_rows=deepseek_rows,
                    stable_inputs=stable,
                ),
                "alias_steward_rows": _build_alias_rows(
                    candidates=candidates,
                    receipt=alias_receipt,
                    manifest_rows=manifest_rows,
                    source_rows=source_rows,
                    e0037_rows=e0037_rows,
                    e0038_rows=e0038_rows,
                    base_nodes=base_nodes,
                    result_nodes=result_nodes,
                    vietocr_rows=vietocr_rows,
                    deepseek_rows=deepseek_rows,
                    stable_inputs=stable,
                ),
            }

        first_sections = assemble_evidence_sections()
        second_sections = assemble_evidence_sections()
        first_section_bytes = _encoded_packet_json(first_sections)
        second_section_bytes = _encoded_packet_json(second_sections)
        if first_section_bytes != second_section_bytes:
            raise E0039ReviewPacketError("E-0039 deterministic evidence assembly replay differs")
        unselected_rows = first_sections["row_review_rows"]
        alias_rows = first_sections["alias_steward_rows"]
        evidence_sections_sha256 = hashlib.sha256(first_section_bytes).hexdigest()

        payload: dict[str, Any] = {
            "identity": {
                "format_version": 1,
                "experiment_id": "E-0039",
                "dataset_role": "CALIBRATION",
                "capture_git_commit": capture_commit,
                "capture_git_dirty": False,
                "control": copy.deepcopy(control_stable.artifact),
                "implementation": {
                    name: copy.deepcopy(item.artifact)
                    for name, item in implementation_stable.items()
                },
            },
            "state": PACKET_STATE,
            "deterministic_replay": {
                "evidence_assembly_invocation_count": 2,
                "exact_canonical_byte_equality": True,
                "canonical_encoding": ("UTF8_JSON_SORTED_KEYS_COMPACT_NO_NAN_NO_DUPLICATE_KEYS_V1"),
                "evidence_sections_sha256": evidence_sections_sha256,
            },
            "input_artifacts": {
                name: copy.deepcopy(item.artifact) for name, item in stable.items()
            },
            "evidence_identity": {
                "source_document_not_opened": copy.deepcopy(SOURCE_DOCUMENT),
                "source_pixel_evidence": {
                    "e0035_s3": e0035_s3,
                    "crop_manifest": copy.deepcopy(stable["crop_manifest"].artifact),
                    "page_renders": [
                        {
                            **copy.deepcopy(PAGE_RENDER_IDENTITIES[3]),
                            "verification": "TRANSITIVELY_HASH_BOUND_NOT_OPENED_BY_E0039",
                        },
                        {
                            **copy.deepcopy(PAGE_RENDER_IDENTITIES[4]),
                            "verification": "TRANSITIVELY_HASH_BOUND_NOT_OPENED_BY_E0039",
                        },
                    ],
                    "target_source_crops": [
                        copy.deepcopy(stable[name].artifact) for name in _TARGET_CROP_INPUT_NAMES
                    ],
                    "source_structure": copy.deepcopy(stable["e0037_source_structure"].artifact),
                },
                "sealed_semantic_readers": e0036_identity,
                "mapping_chain": {
                    "e0037_mapping_seal": copy.deepcopy(stable["e0037_mapping_seal"].artifact),
                    "e0037_s3_snapshot": copy.deepcopy(e0037_s3_record),
                    "e0037_mapping_only": copy.deepcopy(stable["e0037_mapping_only"].artifact),
                    "e0038_mapping_seal": copy.deepcopy(stable["e0038_mapping_seal"].artifact),
                    "e0038_s3_registration": copy.deepcopy(
                        stable["e0038_s3_registration"].artifact
                    ),
                    "e0038_s3_snapshot_id": E0038_S3_SNAPSHOT_ID,
                    "e0038_mapping_only": copy.deepcopy(stable["e0038_mapping_only"].artifact),
                    "review_coverage_identity": {
                        "authority_source": "E0038_MAPPING_ONLY_PRE_REVIEW_ACCESS_CONTRACT",
                        "review_or_human_labels_opened": False,
                        "target_row_adjudication_count": 0,
                        "alias_steward_decision_count": 0,
                        "prior_review_artifact_or_coverage_receipt_opened": False,
                    },
                },
                "workbook_and_projections": {
                    "workbook": copy.deepcopy(stable["cdkt_workbook"].artifact),
                    "workbook_display_order_used": True,
                    "numeric_report_norm_id_sort_used": False,
                    "base_node_count": 77,
                    "base_projection_sha256": BASE_PROJECTION_SHA256,
                    "result_node_count": 77,
                    "result_projection_sha256": RESULT_PROJECTION_SHA256,
                    "alias_receipt_sha256": ALIAS_RECEIPT_SHA256,
                    "e0037_e0038_selected_pair_projection_sha256": (
                        E0037_E0038_SELECTED_PAIR_PROJECTION_SHA256
                    ),
                },
            },
            "access_contract": copy.deepcopy(_EXPECTED_PACKET_ACCESS_CONTRACT),
            "row_review_packet": {
                "packet_type": "UNSELECTED_ROW_ADJUDICATION_EVIDENCE_ONLY",
                "row_count": len(unselected_rows),
                "row_ids": list(UNSELECTED_ROW_IDS),
                "rows": unselected_rows,
                "decision_status": "NOT_STARTED_BLANK_RESPONSE_REQUIRED",
                "authority_required": "INDEPENDENT_ROW_ADJUDICATOR",
                "authority_boundary": ("MAY_ADJUDICATE_ROWS_BUT_MAY_NOT_APPROVE_SCHEMA_ALIASES"),
            },
            "alias_steward_packet": {
                "packet_type": "SCHEMA_ALIAS_STEWARD_EVIDENCE_ONLY",
                "candidate_count": len(alias_rows),
                "candidate_ids": [item[0] for item in ALIAS_ROW_BINDINGS],
                "rows": alias_rows,
                "decision_status": "NOT_STARTED_BLANK_RESPONSE_REQUIRED",
                "authority_required": "REVIEW_INDEPENDENT_SCHEMA_STEWARD",
                "authority_boundary": (
                    "MAY_DECIDE_ID_SCOPED_ALIAS_BUT_MAY_NOT_ADJUDICATE_SOURCE_ROWS"
                ),
            },
            "blank_response_contracts": {
                "vocabulary_ordering": "ALPHABETIC_NON_PREFERENTIAL_NO_DEFAULT",
                "row_adjudication": {
                    "template": copy.deepcopy(ROW_RESPONSE_TEMPLATE),
                    "allowed_vocabulary": copy.deepcopy(ROW_RESPONSE_VOCABULARY),
                    "decision_constraints": copy.deepcopy(ROW_DECISION_CONSTRAINTS),
                },
                "alias_stewardship": {
                    "template": copy.deepcopy(ALIAS_RESPONSE_TEMPLATE),
                    "allowed_vocabulary": copy.deepcopy(ALIAS_RESPONSE_VOCABULARY),
                    "decision_constraints": copy.deepcopy(ALIAS_DECISION_CONSTRAINTS),
                },
            },
            "authority": {
                "dataset_role": "CALIBRATION_ONLY",
                "predecision_evidence_packet": True,
                "source_pixel_and_sealed_reader_identity": True,
                "e0037_e0038_mapping_identity": True,
                "prior_review_artifact_or_coverage_receipt_opened": False,
                "row_adjudication_completed": False,
                "schema_steward_decision_completed": False,
                "schema_alias_approval": False,
                "schema_authority": False,
                "automatic_mapping_adoption": False,
                "numeric_period_or_unit": False,
                "accounting_or_excel": False,
                "history_or_mongodb": False,
                "holdout_or_production": False,
            },
            "claim_boundary": _CLAIM_BOUNDARY,
        }
        _validate_packet_payload(
            payload,
            expected_control_artifact=control_stable.artifact,
            expected_implementation_artifacts={
                name: item.artifact for name, item in implementation_stable.items()
            },
            expected_git_commit=capture_commit,
        )
        replay_payload = copy.deepcopy(payload)
        replay_payload["row_review_packet"]["rows"] = second_sections["row_review_rows"]
        replay_payload["alias_steward_packet"]["rows"] = second_sections["alias_steward_rows"]
        if _encoded_packet_json(payload) != _encoded_packet_json(replay_payload):
            raise E0039ReviewPacketError(
                "E-0039 full packet differs after deterministic evidence replay"
            )
        encoded_packet = _encoded_packet_json(payload)
        if len(encoded_packet) > _RESOURCE_CAPS["maximum_packet_bytes"]:
            raise E0039ReviewPacketError("E-0039 canonical packet exceeds byte budget")

        if destination.exists() or destination.is_symlink():
            raise E0039ReviewPacketError(f"refusing to overwrite E-0039 packet: {destination}")
        if _clean_git_commit(root) != capture_commit:
            raise E0039ReviewPacketError("Git commit changed during E-0039 packet capture")
        all_stable = {
            "control": control_stable,
            **implementation_stable,
            **stable,
        }
        for name, item in all_stable.items():
            try:
                _assert_unchanged(reader, root, item, f"E-0039 final recheck {name}")
            except E0038ExactMappingError as exc:
                raise _fail(f"E-0039 input changed before publication: {name}", exc) from exc

        _head_bind(
            root,
            control_stable.artifact,
            name="control",
            path=CONTROL_RELATIVE_PATH,
            reader=reader,
        )
        for name, path in _IMPLEMENTATION_PATHS.items():
            _head_bind(
                root,
                implementation_stable[name].artifact,
                name=f"implementation {name}",
                path=path,
                reader=reader,
            )
        for name in sorted(_TRACKED_FROZEN_INPUTS):
            _head_bind(
                root,
                stable[name].artifact,
                name=f"input {name}",
                path=_FROZEN_PATHS[name],
                reader=reader,
            )
        if _clean_git_commit(root) != capture_commit:
            raise E0039ReviewPacketError(
                "Git or HEAD-bound identity changed before E-0039 publication"
            )
        try:
            _exclusive_publish_compact_json(
                root,
                destination,
                payload,
                exclusive_parent_inventory=(OUTPUT_RELATIVE_PATH.name,),
            )
        except E0038ExactMappingError as exc:
            raise _fail("cannot exclusively publish E-0039 packet", exc) from exc
        return payload
    except E0039ReviewPacketError:
        raise
    except (
        E0037SourceStructureError,
        E0037SealedMappingError,
        E0038ExactMappingError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise _fail("E-0039 review-packet capture failed closed", exc) from exc


__all__ = [
    "E0039ReviewPacketError",
    "capture_e0039_review_packet",
]
