#!/usr/bin/env python3
"""Run the fixed-asset-rollforward family over one authenticated selected JSON corpus."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import stat
import sys
import tempfile
from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bctc_ai.evaluation.gemini_json_fixed_asset_rollforward_family_v1 import (  # noqa: E402
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1,
    evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1,
)
from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (  # noqa: E402
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    validate_gemini_json_flat_family_sweep_v1,
)
from bctc_ai.evaluation.historical_comparator_policy_v1 import (  # noqa: E402
    DISJOINT_EXPANSION,
    EXACT_HISTORICAL_COMPARISON,
    NOT_APPLICABLE_DISJOINT_CORPUS,
    STRICT_RELEASE,
    audit_historical_comparator_policy_v1,
)
from bctc_ai.evaluation.historical_comparator_policy_v1 import (  # noqa: E402
    FORMAT_VERSION as HISTORICAL_COMPARATOR_POLICY_FORMAT_VERSION,
)
from bctc_ai.source_structure.contracts_v1 import (  # noqa: E402
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)
from bctc_ai.storage.gemini_accounting_family_store_v1 import (  # noqa: E402
    ingest_gemini_accounting_family_sweep_v1,
    load_gemini_accounting_family_sweep_v1,
    record_gemini_accounting_family_export_v1,
)
from bctc_ai.storage.gemini_current_corpus_manifest_index_v1 import (  # noqa: E402
    validate_current_corpus_manifest_index_v1,
)
from bctc_ai.storage.gemini_financial_page_store_v1 import (  # noqa: E402
    query_selected_fixed_asset_rollforward_family_regions_v1,
    validate_selected_fixed_asset_rollforward_family_candidate_replays_v1,
    validate_selected_fixed_asset_rollforward_family_query_evidence_v1,
)


class RunGeminiJsonFixedAssetRollforwardAccountingFamilyV1Error(RuntimeError):
    """The corpus, policy, result, or replay boundary drifted."""


def _error(message: str) -> RunGeminiJsonFixedAssetRollforwardAccountingFamilyV1Error:
    return RunGeminiJsonFixedAssetRollforwardAccountingFamilyV1Error(message)


AUDIT_FORMAT_VERSION = "GEMINI_JSON_FIXED_ASSET_ROLLFORWARD_EXPERIMENTAL_AUDIT_V1"
PINNED_CORPUS_MANIFEST_INDEX_ID = (
    "gjfccmiv1:index:61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3"
)
PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256 = (
    "601be9fc2a894af2ce4f4c982d5347521a6268a46c075d9cc96f9828baef8ae8"
)
PINNED_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "f416280d2d9d3a44e6367495d6562d1d70d7fefa5d72ae613f3eca46bf90fb06"
    ),
    "accepted_cluster_count": 72,
    "accepted_control_region_count": 20,
    "accepted_current_region_count": 72,
    "candidate_disposition_axis_sha256": (
        "4d065065db35cdd68d3bcc2c15f8288f18ca0a0de44e575e0bf9556ef88766e4"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 68, READY: 72, UNRESOLVED: 0},
    "query_policy_sha256": "d6590aa0f505defd6e32bc6c7c80f3eb8a913cca79b1a9cd748c3b7c5c839a87",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 875,
    "not_observed_count": 68,
    "ready_count": 72,
    "unresolved_count": 0,
}
PINNED_RELEASE_AUDIT_METRICS = {
    "equation_count": 1247,
    "historical_document_match_count": 16,
    "historical_value_match_count": 140,
    "mapping_count": 875,
}
PINNED_RELEASE_AXIS_SHA256 = {
    "clusters": "b569acd21d20f22a226ec25ee1a0c96c341a3ab86baa6b01d62f0ebe3581d57a",
    "equations": "ef463c03e983e32fb4cbdbd4ef440acbf8d5a0b8118c362490d21a9c8a304127",
    "historical_comparator": ("878a47309b237e1bc9dbb2ea03d954c0d966a6d1e607611cc3d8f1035b2466e1"),
    "mappings": "ca4dc6149cfff3a5e0fd84ae0c344f7cde44288508a2e75e5d0d973294dcb413",
}
PINNED_TANGIBLE_SPEC_REFS = {
    "evaluation": {
        "path": "config/families/tm-tangible-fixed-assets-evaluation-v1.json",
        "sha256": "d4198171c3dbbf31a8ecb657821222f417265acc154b5b01d5125990d051207a",
        "size_bytes": 2951,
    },
    "schema_binding": {
        "path": "config/families/tm-tangible-fixed-assets-schema-binding-v1.json",
        "sha256": "8e7656c268ed2e32f1cfac3390e02e6bb71b52113577a2adb37fe74fa710ffd6",
        "size_bytes": 1893,
    },
    "topology": {
        "path": "config/families/tm-tangible-fixed-assets-topology-v1.json",
        "sha256": "7a698e17f3ed4dd6fdbcdd533b0d67963fb8e2dc90115ee7d6c41f9730196420",
        "size_bytes": 7814,
    },
}
PINNED_HISTORICAL_ORACLES = (
    {
        "format_version": "TANGIBLE_FIXED_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0069-tangible-fixed-assets-8bank-codex-verified-mapping-v1.json",
        "sha256": "a7cb421971d881ea016b801e00262b29cb24e92c02735d9760b3281fb868619d",
        "size_bytes": 85521,
    },
    {
        "format_version": "ANNUAL_2025_TANGIBLE_FIXED_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0123-annual-2025-tangible-fixed-assets-8bank-codex-verified-mapping-v1.json",
        "sha256": "0fa5e1212ba840b456fa140670541b3f31a7038504c95ddbf170f4ef1c5d394a",
        "size_bytes": 234208,
    },
)
PINNED_LEASED_HISTORICAL_ORACLES = (
    {
        "format_version": "LEASED_FIXED_ASSETS_8BANK_BOUND_REPORT_ABSENCE_V1",
        "path": "docs/experiments/E-0070-leased-fixed-assets-8bank-bound-report-absence-v1.json",
        "sha256": "fe02fb3a1413bf3ddd08d75c3f492a22eaae86554d070533eeab6c5a7274fa83",
        "size_bytes": 19948,
    },
    {
        "format_version": "ANNUAL_2025_LEASED_FIXED_ASSETS_8BANK_BOUND_REPORT_ABSENCE_V1",
        "path": "docs/experiments/E-0124-annual-2025-leased-fixed-assets-8bank-bound-report-absence-v1.json",
        "sha256": "603274c90736a9acc451ab11665a11dee9ecb75fbbd5c3d938a665e29c5da0f3",
        "size_bytes": 27448,
    },
)
PINNED_LEASED_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570"
    ),
    "accepted_cluster_count": 0,
    "accepted_control_region_count": 0,
    "accepted_current_region_count": 0,
    "candidate_disposition_axis_sha256": (
        "dde6f99282efc1dbfcc1d5df44b3203412fe59c89b69e1f74c32ee128766dae0"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 140, READY: 0, UNRESOLVED: 0},
    "query_policy_sha256": "c9d04d2e573eee333d6ac64e210544f6ecc32761f333be2bb6984c892d7d7281",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_LEASED_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 0,
    "not_observed_count": 140,
    "ready_count": 0,
    "unresolved_count": 0,
}
PINNED_LEASED_RELEASE_AUDIT_METRICS = {
    "equation_count": 0,
    "historical_document_match_count": 16,
    "historical_value_match_count": 0,
    "mapping_count": 0,
}
PINNED_LEASED_RELEASE_AXIS_SHA256 = {
    "clusters": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "equations": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "historical_comparator": ("f4f8a10f7deca884492e0423e41d2c4cecd8fd8eadfd281785beac2819dbd1cb"),
    "mappings": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
}
PINNED_LEASED_SPEC_REFS = {
    "evaluation": {
        "path": "config/families/tm-leased-fixed-assets-evaluation-v1.json",
        "sha256": "c0d51d245d8a1b3586f05067747bf65a25d9b39e49f09c277277e1f6bbbdce34",
        "size_bytes": 3085,
    },
    "schema_binding": {
        "path": "config/families/tm-leased-fixed-assets-schema-binding-v1.json",
        "sha256": "39ada7a39e85846a4c5544001e9fdae68bf9b4f59f08cd4c2104dacabee38ead",
        "size_bytes": 1196,
    },
    "topology": {
        "path": "config/families/tm-leased-fixed-assets-topology-v1.json",
        "sha256": "fcc45f599a2df1190e3fad38190f971d7deeb441ce70b58755200773923442a4",
        "size_bytes": 5560,
    },
}
PINNED_INTANGIBLE_HISTORICAL_ORACLES = (
    {
        "format_version": "INTANGIBLE_FIXED_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0071-intangible-fixed-assets-8bank-codex-verified-mapping-v1.json",
        "sha256": "d3e5d1a5609108379f3bf2618178e1b8a738e00ef7171b0615fd5bf459e2f172",
        "size_bytes": 91222,
    },
    {
        "format_version": "ANNUAL_2025_INTANGIBLE_FIXED_ASSETS_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0125-annual-2025-intangible-fixed-assets-8bank-codex-verified-mapping-v1.json",
        "sha256": "60bec8bfed8432e86947d081e66f0cc6eae8f60c07f80db9ac93091e8c9fb11a",
        "size_bytes": 219131,
    },
)
PINNED_INVESTMENT_PROPERTY_HISTORICAL_ORACLES = (
    {
        "format_version": "INVESTMENT_PROPERTY_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": "docs/experiments/E-0072-investment-property-8bank-codex-verified-mapping-v1.json",
        "sha256": "2831f70486cdd624a222158f0aaffdb1340e378264fa31d688e4f435136b935d",
        "size_bytes": 58162,
    },
    {
        "format_version": "ANNUAL_2025_INVESTMENT_PROPERTY_8BANK_CODEX_VERIFIED_MAPPING_V1",
        "path": (
            "docs/experiments/"
            "E-0126-annual-2025-investment-property-8bank-codex-verified-mapping-v1.json"
        ),
        "sha256": "6bb18468bd27826dc12c5a64377b49a16400c17ebd807f883a3225289fb88d07",
        "size_bytes": 97767,
    },
)
PINNED_INTANGIBLE_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "d6bf4945b30ed3da8277b9c4308ae538726e2395cc826893c955cc2f8a5cbf1b"
    ),
    "accepted_cluster_count": 72,
    "accepted_control_region_count": 20,
    "accepted_current_region_count": 72,
    "candidate_disposition_axis_sha256": (
        "0fef35ac323f2d16ff10dcc6da897d1539d26f94a58734b51460486f1c85c128"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 68, READY: 72, UNRESOLVED: 0},
    "query_policy_sha256": "9f37f6f256e2b7d044604b5dfe363b779523f25d83ba6c48c28b0048e57df212",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_INTANGIBLE_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 829,
    "not_observed_count": 68,
    "ready_count": 72,
    "unresolved_count": 0,
}
PINNED_INTANGIBLE_RELEASE_AUDIT_METRICS = {
    "equation_count": 1120,
    "historical_document_match_count": 16,
    "historical_value_match_count": 139,
    "mapping_count": 829,
}
PINNED_INTANGIBLE_RELEASE_AXIS_SHA256 = {
    "clusters": "0114237396f501ce89588454298de40929bb626d2e8967216cec6c562a85503e",
    "equations": "9e57b971912bf459a603fe7c0af39b429aea04819c06a6edb82640c9d55fedc1",
    "historical_comparator": "1f0a2c42bef1e6da9c6a8767f11f06a36eb7051a901fe9e9df4818278f0f3077",
    "mappings": "880fbae7ddc3cee58bbc097d7386d968faa4ec5d7e47c4cfc5289e01e76b1a19",
}
PINNED_INTANGIBLE_SPEC_REFS = {
    "evaluation": {
        "path": "config/families/tm-intangible-fixed-assets-evaluation-v1.json",
        "sha256": "37387f6698a606eecb1547768630b62a96361df7c633d25c8d814bb7f5d59890",
        "size_bytes": 5101,
    },
    "schema_binding": {
        "path": "config/families/tm-intangible-fixed-assets-schema-binding-v1.json",
        "sha256": "5fab7a4a6701a657e8fcf2ecb450b739c29bbda613d86439a146d0f70da22093",
        "size_bytes": 2850,
    },
    "topology": {
        "path": "config/families/tm-intangible-fixed-assets-topology-v1.json",
        "sha256": "2799465474d48da39992a65b238a9434abcb68aa8b967d0f913722eff82654d8",
        "size_bytes": 16265,
    },
}
PINNED_INVESTMENT_PROPERTY_QUERY_RECEIPT = {
    "accepted_cluster_axis_sha256": (
        "61d40e5aa46b0a709efb5f5d958a3002abffa32da754de48adf82cebac21d606"
    ),
    "accepted_cluster_count": 12,
    "accepted_control_region_count": 9,
    "accepted_current_region_count": 26,
    "candidate_disposition_axis_sha256": (
        "150815486e325565e7e5676165f324728a835bccde2969ee6c4f9cac64fbf870"
    ),
    "candidate_disposition_count": 140,
    "disposition_counts": {NOT_OBSERVED: 128, READY: 12, UNRESOLVED: 0},
    "query_policy_sha256": "ec35a3c2539e7c1c02da7e23b7dd00f2e08cbbd3f43fff832706d4893a972f7e",
    "selected_document_axis_sha256": (
        "54df769ecd6875cc8a7d242d46f6e57bf2a94ac349ad0109db72f3cd6af62e4c"
    ),
    "selected_document_count": 140,
    "selected_page_axis_sha256": (
        "04d461370f74243e4f6e01c27b688afabf6c0e86d9fa6ec5dc12b7ef20c1810c"
    ),
    "selected_page_count": 8947,
    "selected_page_json_frontier_sha256": PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
}
PINNED_INVESTMENT_PROPERTY_RELEASE_METRICS = {
    "document_count": 140,
    "mapping_count": 110,
    "not_observed_count": 128,
    "ready_count": 12,
    "unresolved_count": 0,
}
PINNED_INVESTMENT_PROPERTY_RELEASE_AUDIT_METRICS = {
    "equation_count": 185,
    "historical_document_match_count": 16,
    "historical_value_match_count": 27,
    "mapping_count": 110,
}
PINNED_INVESTMENT_PROPERTY_RELEASE_AXIS_SHA256 = {
    "clusters": "84df976799ec32dc83c4978b13531fd61d0167b0fb08ed6d511dc7862454b81c",
    "equations": "42c6592f209ac3e4c304ddcd332bdfaf37e6847db9c7e60152183feeacd4220c",
    "historical_comparator": ("d725ae72f3c03e465de723e6ebefed2c7b43246567af1d52dac790f08c1b0b97"),
    "mappings": "d0cf840f86b4b5855eba74257d1aeb0e81e42dad0033fb608798fd780df734c9",
}
PINNED_INVESTMENT_PROPERTY_SPEC_REFS = {
    "evaluation": {
        "path": "config/families/tm-investment-property-evaluation-v1.json",
        "sha256": "afd1c0905ee795ac3c3fcbfb03bff1512e926d67ca468d13ef33ece844d422ca",
        "size_bytes": 4772,
    },
    "schema_binding": {
        "path": "config/families/tm-investment-property-schema-binding-v1.json",
        "sha256": "b0f98b9d76a972c2c509cfd8ba66fb7f597ce6b07f0e931b9fa7b8d0a4fdf1ae",
        "size_bytes": 3156,
    },
    "topology": {
        "path": "config/families/tm-investment-property-topology-v1.json",
        "sha256": "2f5e61cecaac0234b489d0da7cbfb6d49c7a0695bf60b6599468b7cbefbd935c",
        "size_bytes": 15747,
    },
}
_SQLITE_SIDECAR_SUFFIXES = ("-journal", "-shm", "-wal")


def _json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise _error(f"JSON input is absent or not regular: {path}")
    try:
        value = json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"JSON input is invalid: {path}") from exc
    if type(value) is not dict:
        raise _error("JSON input is not one object")
    return value


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _file_ref(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise _error(f"traceable input is absent or not regular: {path}")
    resolved = path.resolve()
    logical = str(resolved.relative_to(root.resolve())) if root is not None else str(resolved)
    return {"path": logical, "sha256": _sha256(resolved), "size_bytes": resolved.stat().st_size}


def _content_ref(root: Path, reference: Any) -> Path:
    if type(reference) is not dict or set(reference) != {"path", "sha256", "size_bytes"}:
        raise _error("corpus content reference fields drifted")
    relative = Path(reference["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise _error("corpus content reference escapes its artifact root")
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size != reference["size_bytes"]
        or _sha256(path) != reference["sha256"]
    ):
        raise _error("corpus content reference does not authenticate")
    return path


def _file_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _assert_no_sqlite_sidecars(path: Path) -> None:
    if any(os.path.lexists(f"{path}{suffix}") for suffix in _SQLITE_SIDECAR_SUFFIXES):
        raise _error("fixed-asset-rollforward SQLite source has a journal/WAL sidecar")


def _fd_sha256(descriptor: int) -> str:
    prior = os.lseek(descriptor, 0, os.SEEK_CUR)
    digest = sha256()
    try:
        os.lseek(descriptor, 0, os.SEEK_SET)
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
    finally:
        os.lseek(descriptor, prior, os.SEEK_SET)
    return digest.hexdigest()


class _AuthenticatedSqliteSnapshot:
    def __init__(
        self,
        *,
        source: Path,
        source_descriptor: int,
        source_identity: tuple[int, ...],
        snapshot: Path,
        snapshot_identity: tuple[int, ...],
        expected_sha256: str,
        expected_size_bytes: int,
    ) -> None:
        self.source = source
        self.source_descriptor = source_descriptor
        self.source_identity = source_identity
        self.path = snapshot
        self.snapshot_identity = snapshot_identity
        self.expected_sha256 = expected_sha256
        self.expected_size_bytes = expected_size_bytes

    def validate(self) -> None:
        _assert_no_sqlite_sidecars(self.source)
        _assert_no_sqlite_sidecars(self.path)
        try:
            source_named = os.stat(self.source, follow_symlinks=False)
            snapshot_stat = os.stat(self.path, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise _error("authenticated fixed-asset-rollforward SQLite path disappeared") from exc
        source_fd = os.fstat(self.source_descriptor)
        if (
            not stat.S_ISREG(source_named.st_mode)
            or not stat.S_ISREG(snapshot_stat.st_mode)
            or _file_identity(source_fd) != self.source_identity
            or _file_identity(source_named) != self.source_identity
            or _file_identity(snapshot_stat) != self.snapshot_identity
            or source_fd.st_size != self.expected_size_bytes
            or snapshot_stat.st_size != self.expected_size_bytes
            or _fd_sha256(self.source_descriptor) != self.expected_sha256
            or _sha256(self.path) != self.expected_sha256
        ):
            raise _error("authenticated fixed-asset-rollforward SQLite bytes changed during use")


@contextmanager
def _authenticated_sqlite_snapshot(
    source: Path, *, reference: Mapping[str, Any]
) -> Iterator[_AuthenticatedSqliteSnapshot]:
    """Create one immutable source view for the whole family run."""

    _assert_no_sqlite_sidecars(source)
    descriptor = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        source_stat = os.fstat(descriptor)
        source_identity = _file_identity(source_stat)
        if (
            not stat.S_ISREG(source_stat.st_mode)
            or source_identity != _file_identity(os.stat(source, follow_symlinks=False))
            or source_stat.st_size != reference.get("size_bytes")
        ):
            raise _error("fixed-asset-rollforward SQLite source identity drifted before snapshot")
        with tempfile.TemporaryDirectory(prefix="family17-authenticated-sqlite-") as directory:
            snapshot = Path(directory) / "page-store.sqlite3"
            output_descriptor = os.open(snapshot, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
            digest = sha256()
            copied = 0
            try:
                with os.fdopen(output_descriptor, "wb") as output:
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    while block := os.read(descriptor, 1024 * 1024):
                        output.write(block)
                        digest.update(block)
                        copied += len(block)
                    output.flush()
                    os.fsync(output.fileno())
            except BaseException:
                snapshot.unlink(missing_ok=True)
                raise
            if copied != reference.get("size_bytes") or digest.hexdigest() != reference.get(
                "sha256"
            ):
                raise _error("fixed-asset-rollforward SQLite snapshot bytes do not authenticate")
            os.chmod(snapshot, 0o444)
            guard = _AuthenticatedSqliteSnapshot(
                source=source,
                source_descriptor=descriptor,
                source_identity=source_identity,
                snapshot=snapshot,
                snapshot_identity=_file_identity(os.stat(snapshot, follow_symlinks=False)),
                expected_sha256=reference["sha256"],
                expected_size_bytes=reference["size_bytes"],
            )
            guard.validate()
            try:
                yield guard
            finally:
                guard.validate()
    finally:
        os.close(descriptor)


def _selected_page_axis(*, index: Mapping[str, Any], artifact_root: Path) -> list[str]:
    version_ids = []
    for document in index["documents"]:
        manifest = _json(_content_ref(artifact_root, document["document_manifest_ref"]))
        pages = manifest.get("pages")
        if (
            manifest.get("document_manifest_id") != document["document_manifest_id"]
            or manifest.get("page_count") != document["page_count"]
            or type(pages) is not list
            or len(pages) != document["page_count"]
        ):
            raise _error("selected document manifest identity or page axis drifted")
        version_ids.extend(page.get("page_json_version_id") for page in pages)
    if (
        len(version_ids) != index["summary"]["page_count"]
        or len(version_ids) != len(set(version_ids))
        or any(type(version_id) is not str for version_id in version_ids)
    ):
        raise _error("selected fixed-asset-rollforward JSON frontier is incomplete or duplicate")
    return version_ids


def _historical_oracles(
    *, compiled_specs: Mapping[str, Any]
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    family_id = compiled_specs.get("topology", {}).get("family_id")
    if family_id == "TANGIBLE_FIXED_ASSETS_ROLLFORWARD":
        pinned_oracles = PINNED_HISTORICAL_ORACLES
    elif family_id == "LEASED_FIXED_ASSETS_ROLLFORWARD":
        pinned_oracles = PINNED_LEASED_HISTORICAL_ORACLES
    elif family_id == "INTANGIBLE_FIXED_ASSETS_ROLLFORWARD":
        pinned_oracles = PINNED_INTANGIBLE_HISTORICAL_ORACLES
    elif family_id == "INVESTMENT_PROPERTY_ROLLFORWARD":
        pinned_oracles = PINNED_INVESTMENT_PROPERTY_HISTORICAL_ORACLES
    else:
        raise _error("fixed-asset-rollforward release family is not pinned")
    result = []
    for pinned in pinned_oracles:
        path = ROOT / pinned["path"]
        value = _json(path)
        metrics = value.get("metrics")
        trials = value.get("trials")
        if (
            _sha256(path) != pinned["sha256"]
            or path.stat().st_size != pinned["size_bytes"]
            or value.get("format_version") != pinned["format_version"]
            or type(metrics) is not dict
            or type(metrics.get("mapping_verified_count")) is not int
            or type(trials) is not list
            or len(trials) != 8
            or sum(len(trial.get("mappings", [])) for trial in trials if type(trial) is dict)
            != metrics["mapping_verified_count"]
        ):
            raise _error("pinned fixed-asset-rollforward historical oracle drifted")
        result.append(({**pinned, "expected_trial_count": len(trials)}, value))
    return result


def _trial_by_source(trials: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for trial in trials:
        source_sha256 = trial.get("source_sha256")
        if type(source_sha256) is not str or source_sha256 in result:
            raise _error("fixed-asset-rollforward candidate source axis is ambiguous")
        result[source_sha256] = trial
    return result


def _normalised_historical_oracle_rows(
    *, compiled_specs: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    oracle_refs = []
    rows = []
    for oracle_ref_index, (oracle_ref, oracle) in enumerate(
        _historical_oracles(compiled_specs=compiled_specs)
    ):
        oracle_refs.append(oracle_ref)
        for oracle_trial in oracle["trials"]:
            rows.append(
                {
                    "oracle_format_version": oracle["format_version"],
                    "oracle_ref_index": oracle_ref_index,
                    "oracle_trial": oracle_trial,
                    "source_sha256": oracle_trial.get("source_pdf_sha256"),
                }
            )
    return oracle_refs, rows


def _strict_historical_compare(
    oracle_row: Mapping[str, Any],
    current_trial: Mapping[str, Any],
    *,
    compiled_specs: Mapping[str, Any],
) -> dict[str, Any]:
    oracle_trial = oracle_row.get("oracle_trial")
    if type(oracle_trial) is not dict:
        raise _error("historical fixed-asset-rollforward oracle trial is invalid")
    current_role_by_id = {
        report_norm_id: role for role, report_norm_id in compiled_specs["bindings"].items()
    }
    axis = []
    source_sha256 = oracle_row.get("source_sha256")
    candidates = current_trial.get("candidates")
    candidate = (
        candidates[0]
        if current_trial.get("status") == READY
        and type(candidates) is list
        and len(candidates) == 1
        else None
    )
    expected_present = bool(oracle_trial.get("mappings"))
    document_exact = (candidate is not None) == expected_present
    axis.append(
        {
            "actual_status": current_trial.get("status"),
            "disposition": "EXACT" if document_exact else "MISMATCH",
            "expected_present": expected_present,
            "kind": "DOCUMENT_DISPOSITION",
            "oracle_format_version": oracle_row.get("oracle_format_version"),
            "source_sha256": source_sha256,
        }
    )
    if expected_present:
        if candidate is None:
            raise _error("historical fixed-asset-rollforward present source is not READY")
        actual_by_id = {}
        for mapping in candidate.get("mappings", []):
            report_norm_id = mapping.get("report_norm_id")
            if (
                type(report_norm_id) is not int
                or report_norm_id in actual_by_id
                or type(mapping.get("cell")) is not dict
                or type(mapping["cell"].get("coefficient")) is not int
            ):
                raise _error("current fixed-asset-rollforward comparator mapping axis is invalid")
            actual_by_id[report_norm_id] = mapping
        for historical in oracle_trial.get("mappings", []):
            binding = historical.get("schema_binding")
            old_report_norm_id = historical.get("report_norm_id")
            historical_coefficient = (
                historical.get("value", {}).get("normalized_value")
                if type(historical.get("value")) is dict
                else None
            )
            current = actual_by_id.get(old_report_norm_id)
            current_coefficient = current["cell"]["coefficient"] if current else None
            exact = (
                type(old_report_norm_id) is int
                and type(historical_coefficient) is int
                and current is not None
                and current_coefficient == historical_coefficient
            )
            axis.append(
                {
                    "bank_provenance": oracle_trial.get("document_provenance"),
                    "canonical_name": (
                        binding.get("canonical_name") if type(binding) is dict else None
                    ),
                    "current_coefficient": current_coefficient,
                    "current_role": current.get("role") if type(current) is dict else None,
                    "declared_role": current_role_by_id.get(old_report_norm_id),
                    "disposition": "EXACT" if exact else "MISMATCH",
                    "historical_coefficient": historical_coefficient,
                    "historical_report_norm_id": old_report_norm_id,
                    "kind": "MAPPING_VALUE",
                    "oracle_format_version": oracle_row.get("oracle_format_version"),
                    "source_sha256": source_sha256,
                }
            )
    if any(item["disposition"] != "EXACT" for item in axis):
        raise _error("historical fixed-asset-rollforward comparator is not exact")
    return {"axis": axis, "disposition": EXACT_HISTORICAL_COMPARISON}


def _historical_comparator_axis(
    *,
    policy: str,
    current_manifest_index_id: str,
    current_manifest_source_sha256s: Sequence[str],
    current_manifest_page_json_version_ids: Sequence[str],
    current_candidate_source_sha256s: Sequence[str],
    current_replay_source_sha256s: Sequence[str],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    oracle_refs, oracle_rows = _normalised_historical_oracle_rows(
        compiled_specs=compiled_specs
    )
    policy_receipt = audit_historical_comparator_policy_v1(
        policy=policy,
        pinned_oracle_refs=oracle_refs,
        normalized_oracle_rows=oracle_rows,
        current_manifest_index_id=current_manifest_index_id,
        current_manifest_source_sha256s=current_manifest_source_sha256s,
        current_manifest_page_json_version_ids=current_manifest_page_json_version_ids,
        current_trials=trials,
        current_candidate_source_sha256s=current_candidate_source_sha256s,
        current_replay_source_sha256s=current_replay_source_sha256s,
        current_selected_page_json_version_ids=current_manifest_page_json_version_ids,
        strict_compare=(
            lambda oracle, current: _strict_historical_compare(
                oracle, current, compiled_specs=compiled_specs
            )
        )
        if policy == STRICT_RELEASE
        else None,
    )
    if policy == DISJOINT_EXPANSION:
        if (
            policy_receipt["disposition"] != NOT_APPLICABLE_DISJOINT_CORPUS
            or policy_receipt["comparison_axis"] != []
        ):
            raise _error("disjoint fixed-asset-rollforward comparator receipt drifted")
        return [], oracle_refs, policy_receipt
    axis = [
        row
        for comparison in policy_receipt["comparison_axis"]
        for row in comparison["comparison"]["axis"]
    ]
    expected_mapping_count = sum(
        oracle["metrics"]["mapping_verified_count"]
        for _ref, oracle in _historical_oracles(compiled_specs=compiled_specs)
    )
    if len(axis) != expected_mapping_count + 16:
        raise _error("historical fixed-asset-rollforward comparator denominator drifted")
    return axis, oracle_refs, policy_receipt


def _audit_axes(
    *,
    policy: str,
    current_manifest_index_id: str,
    current_manifest_source_sha256s: Sequence[str],
    current_manifest_page_json_version_ids: Sequence[str],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]], dict[str, Any]]:
    mappings = []
    equations = []
    clusters = []
    for trial in trials:
        candidates = trial.get("candidates")
        if trial.get("status") != READY or type(candidates) is not list or len(candidates) != 1:
            continue
        candidate = candidates[0]
        document = {
            "document_ordinal": trial["document_ordinal"],
            "source_logical_name": trial["source_logical_name"],
            "source_sha256": trial["source_sha256"],
        }
        clusters.append(
            {
                **document,
                "component_regions": candidate["component_regions"],
                "control_regions": candidate["control_regions"],
                "query_receipt_sha256": canonical_json_sha256_v1(
                    candidate["closure_receipt"]["query_receipt"]
                ),
            }
        )
        for mapping in candidate["mappings"]:
            mappings.append(
                {
                    **document,
                    "coefficient": mapping["cell"]["coefficient"],
                    "period_date": mapping["period_date"],
                    "report_norm_id": mapping["report_norm_id"],
                    "role": mapping["role"],
                    "row_id": mapping["row_id"],
                    "state": mapping["cell"]["state"],
                    "unit": mapping["bound_unit"],
                }
            )
        component_population = candidate["closure_receipt"].get("component_population_receipt")
        if type(component_population) is dict:
            for component in component_population.get("components", []):
                table_receipt = component.get("table_receipt")
                component_equations = (
                    table_receipt.get("equations", [])
                    if type(table_receipt) is dict
                    else component.get("summary_control_projection", {}).get(
                        "summary_equations", []
                    )
                )
                for equation in component_equations:
                    equations.append(
                        {
                            **document,
                            "component_region": component["region"],
                            "equation": equation,
                        }
                    )
            for equation in component_population.get("aggregate_equations", []):
                equations.append(
                    {
                        **document,
                        "component_region": None,
                        "equation": equation,
                    }
                )
        else:
            for equation in candidate["closure_receipt"]["table_receipt"]["equations"]:
                equations.append({**document, "equation": equation})
    source_by_ordinal = {
        document["document_ordinal"]: document["source_sha256"]
        for document in indexed_query_evidence["selected_document_axis"]
    }
    candidate_sources = [
        source_by_ordinal[cluster["document_ordinal"]]
        for cluster in indexed_query_evidence["accepted_clusters"]
    ]
    replay_sources = [trial["source_sha256"] for trial in trials if trial["candidates"]]
    if len(candidate_sources) != len(replay_sources) or set(candidate_sources) != set(
        replay_sources
    ):
        raise _error("fixed-asset-rollforward indexed candidate/replay axes drifted")
    comparator, oracle_refs, comparator_policy_receipt = _historical_comparator_axis(
        policy=policy,
        current_manifest_index_id=current_manifest_index_id,
        current_manifest_source_sha256s=current_manifest_source_sha256s,
        current_manifest_page_json_version_ids=current_manifest_page_json_version_ids,
        current_candidate_source_sha256s=candidate_sources,
        current_replay_source_sha256s=replay_sources,
        trials=trials,
        compiled_specs=compiled_specs,
    )
    return (
        {
            "clusters": clusters,
            "equations": equations,
            "historical_comparator": comparator,
            "mappings": mappings,
        },
        oracle_refs,
        comparator_policy_receipt,
    )


def build_fixed_asset_rollforward_experimental_audit_v1(
    *,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    historical_comparator_policy: str,
    current_manifest_index_id: str,
    current_manifest_source_sha256s: Sequence[str],
    selected_page_json_version_ids: Sequence[str],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    """Build transparent semantic axes after the exact SQLite candidate replay."""

    if sweep.get("corpus_manifest_index_id") != current_manifest_index_id:
        raise _error("fixed-asset-rollforward sweep/current manifest identity drifted")
    axes, oracle_refs, comparator_policy_receipt = _audit_axes(
        policy=historical_comparator_policy,
        current_manifest_index_id=current_manifest_index_id,
        current_manifest_source_sha256s=current_manifest_source_sha256s,
        current_manifest_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=indexed_query_evidence,
        trials=trials,
        compiled_specs=compiled_specs,
    )
    axis_counts = {name: len(axis) for name, axis in axes.items()}
    axis_sha256 = {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()}
    audit_metrics = {
        "equation_count": axis_counts["equations"],
        "historical_document_match_count": sum(
            item["kind"] == "DOCUMENT_DISPOSITION" and item["disposition"] == "EXACT"
            for item in axes["historical_comparator"]
        )
        if historical_comparator_policy == STRICT_RELEASE
        else None,
        "historical_value_match_count": sum(
            item["kind"] == "MAPPING_VALUE" and item["disposition"] == "EXACT"
            for item in axes["historical_comparator"]
        )
        if historical_comparator_policy == STRICT_RELEASE
        else None,
        "mapping_count": axis_counts["mappings"],
    }
    sweep_payload = canonical_json_bytes_v1(sweep)
    material = {
        "axes": axes,
        "axis_counts": axis_counts,
        "axis_sha256": axis_sha256,
        "audit_metrics": audit_metrics,
        "claim_boundary": (
            "AUTHENTICATED_SELECTED_GEMINI_JSON_SQLITE_REPLAY_AND_HISTORICAL_ROLE_VALUE_"
            "COMPARATOR_ONLY_NO_PROVIDER_NO_GEOMETRY_NO_CANONICAL_EXPORT_AUTHORITY"
        ),
        "format_version": AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": comparator_policy_receipt,
        "historical_oracle_refs": oracle_refs,
        "query_evidence_id": indexed_query_evidence["query_evidence_id"],
        "query_receipt": indexed_query_evidence["query_receipt"],
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(
            list(selected_page_json_version_ids)
        ),
        "spec_refs": dict(spec_refs),
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_ref": {
            "path": sweep_output.name,
            "sha256": sha256(sweep_payload).hexdigest(),
            "size_bytes": len(sweep_payload),
            "sweep_id": sweep["sweep_id"],
        },
    }
    return {
        **material,
        "audit_id": "gjffareav1:audit:" + canonical_json_sha256_v1(material),
    }


def validate_fixed_asset_rollforward_experimental_audit_content_v1(
    value: Any,
) -> dict[str, Any]:
    fields = {
        "audit_id",
        "axes",
        "axis_counts",
        "axis_sha256",
        "audit_metrics",
        "claim_boundary",
        "format_version",
        "historical_comparator_policy_receipt",
        "historical_oracle_refs",
        "query_evidence_id",
        "query_receipt",
        "selected_page_json_frontier_sha256",
        "spec_refs",
        "state",
        "sweep_ref",
    }
    axis_names = {
        "clusters",
        "equations",
        "historical_comparator",
        "mappings",
    }
    if (
        type(value) is not dict
        or set(value) != fields
        or value.get("format_version") != AUDIT_FORMAT_VERSION
        or value.get("state") != "EXPERIMENTAL_AUDIT_COMPLETE"
        or type(value.get("axes")) is not dict
        or set(value["axes"]) != axis_names
        or any(type(axis) is not list for axis in value["axes"].values())
    ):
        raise _error("fixed-asset-rollforward experimental audit shape drifted")
    counts = {name: len(axis) for name, axis in value["axes"].items()}
    hashes = {name: canonical_json_sha256_v1(axis) for name, axis in value["axes"].items()}
    if value.get("axis_counts") != counts or value.get("axis_sha256") != hashes:
        raise _error("fixed-asset-rollforward experimental audit axis seal drifted")
    policy_receipt = value.get("historical_comparator_policy_receipt")
    policy = policy_receipt.get("policy") if type(policy_receipt) is dict else None
    disposition = policy_receipt.get("disposition") if type(policy_receipt) is dict else None
    metrics = value.get("audit_metrics")
    if (
        type(policy_receipt) is not dict
        or policy_receipt.get("format_version")
        != HISTORICAL_COMPARATOR_POLICY_FORMAT_VERSION
        or policy not in {STRICT_RELEASE, DISJOINT_EXPANSION}
        or type(policy_receipt.get("comparison_axis")) is not list
        or type(policy_receipt.get("oracle_authentication")) is not dict
        or type(policy_receipt.get("corpus_relation")) is not dict
        or type(policy_receipt.get("current_axis_validation")) is not dict
        or policy_receipt["oracle_authentication"].get("refs")
        != value.get("historical_oracle_refs")
        or policy_receipt["current_axis_validation"].get("manifest_document_count")
        != value.get("query_receipt", {}).get("selected_document_count")
        or policy_receipt["current_axis_validation"].get("trial_source_count")
        != value.get("query_receipt", {}).get("selected_document_count")
        or policy_receipt["current_axis_validation"].get("candidate_source_count")
        != value.get("query_receipt", {}).get("accepted_cluster_count")
        or policy_receipt["current_axis_validation"].get("replay_source_count")
        != value.get("query_receipt", {}).get("accepted_cluster_count")
        or policy_receipt["current_axis_validation"].get(
            "selected_page_json_version_count"
        )
        != value.get("query_receipt", {}).get("selected_page_count")
    ):
        raise _error("fixed-asset-rollforward historical comparator policy receipt drifted")
    if policy == STRICT_RELEASE:
        if (
            disposition != EXACT_HISTORICAL_COMPARISON
            or not value["axes"]["historical_comparator"]
            or type(metrics) is not dict
            or type(metrics.get("historical_document_match_count")) is not int
            or type(metrics.get("historical_value_match_count")) is not int
        ):
            raise _error("fixed-asset-rollforward strict comparator audit drifted")
    elif (
        disposition != NOT_APPLICABLE_DISJOINT_CORPUS
        or policy_receipt["comparison_axis"] != []
        or policy_receipt["corpus_relation"].get("overlap_count") != 0
        or value["axes"]["historical_comparator"] != []
        or type(metrics) is not dict
        or metrics.get("historical_document_match_count") is not None
        or metrics.get("historical_value_match_count") is not None
    ):
        raise _error("fixed-asset-rollforward disjoint comparator audit drifted")
    material = {key: value[key] for key in fields - {"audit_id"}}
    if value.get("audit_id") != "gjffareav1:audit:" + canonical_json_sha256_v1(material):
        raise _error("fixed-asset-rollforward experimental audit identity drifted")
    return json.loads(canonical_json_bytes_v1(value))


def validate_fixed_asset_rollforward_experimental_audit_replay_v1(
    value: Any,
    *,
    database: Path,
    sweep: Mapping[str, Any],
    sweep_output: Path,
    historical_comparator_policy: str,
    current_manifest_index_id: str,
    current_manifest_source_sha256s: Sequence[str],
    selected_page_json_version_ids: Sequence[str],
    indexed_query_evidence: Mapping[str, Any],
    trials: Sequence[dict[str, Any]],
    compiled_specs: Mapping[str, Any],
    spec_refs: Mapping[str, Any],
) -> dict[str, Any]:
    checked_sweep = validate_gemini_json_flat_family_sweep_v1(sweep)
    embedded = compile_gemini_json_flat_family_specs_v1(
        checked_sweep["specs"]["topology"]["value"],
        checked_sweep["specs"]["evaluation"]["value"],
        checked_sweep["specs"]["schema_binding"]["value"],
    )
    if not same_typed_json_v1(embedded, compiled_specs):
        raise _error("fixed-asset-rollforward caller and embedded compiled specs differ")
    if not same_typed_json_v1(checked_sweep["trials"], trials) or not same_typed_json_v1(
        checked_sweep["indexed_query_evidence"], indexed_query_evidence
    ):
        raise _error("fixed-asset-rollforward audit sweep/query/trial axis drifted")
    validate_selected_fixed_asset_rollforward_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_page_json_version_ids,
        compiled_specs=embedded,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
    )
    expected = build_fixed_asset_rollforward_experimental_audit_v1(
        sweep=checked_sweep,
        sweep_output=sweep_output,
        historical_comparator_policy=historical_comparator_policy,
        current_manifest_index_id=current_manifest_index_id,
        current_manifest_source_sha256s=current_manifest_source_sha256s,
        selected_page_json_version_ids=selected_page_json_version_ids,
        indexed_query_evidence=checked_sweep["indexed_query_evidence"],
        trials=checked_sweep["trials"],
        compiled_specs=embedded,
        spec_refs=spec_refs,
    )
    validate_fixed_asset_rollforward_experimental_audit_content_v1(value)
    if not same_typed_json_v1(value, expected):
        raise _error("fixed-asset-rollforward experimental audit does not replay exactly")
    return expected


def _assert_release_pins(
    *,
    historical_comparator_policy: str,
    run_kind: str,
    index: Mapping[str, Any],
    selected_ids: Sequence[str],
    sweep: Mapping[str, Any],
    indexed: Mapping[str, Any],
    audit: Mapping[str, Any],
) -> None:
    if historical_comparator_policy == DISJOINT_EXPANSION:
        if run_kind != "EXPERIMENTAL":
            raise _error("OFFICIAL fixed-asset-rollforward run requires STRICT_RELEASE policy")
        return
    if historical_comparator_policy != STRICT_RELEASE:
        raise _error("fixed-asset-rollforward historical comparator policy is undeclared")
    family_id = sweep.get("specs", {}).get("topology", {}).get("value", {}).get("family_id")
    if family_id == "TANGIBLE_FIXED_ASSETS_ROLLFORWARD":
        pinned_query_receipt = PINNED_QUERY_RECEIPT
        pinned_metrics = PINNED_RELEASE_METRICS
        pinned_audit_metrics = PINNED_RELEASE_AUDIT_METRICS
        pinned_axis_sha256 = PINNED_RELEASE_AXIS_SHA256
        pinned_spec_refs = PINNED_TANGIBLE_SPEC_REFS
        expected_axis_counts = {
            "clusters": 72,
            "equations": 1247,
            "historical_comparator": 156,
            "mappings": 875,
        }
    elif family_id == "LEASED_FIXED_ASSETS_ROLLFORWARD":
        pinned_query_receipt = PINNED_LEASED_QUERY_RECEIPT
        pinned_metrics = PINNED_LEASED_RELEASE_METRICS
        pinned_audit_metrics = PINNED_LEASED_RELEASE_AUDIT_METRICS
        pinned_axis_sha256 = PINNED_LEASED_RELEASE_AXIS_SHA256
        pinned_spec_refs = PINNED_LEASED_SPEC_REFS
        expected_axis_counts = {
            "clusters": 0,
            "equations": 0,
            "historical_comparator": 16,
            "mappings": 0,
        }
    elif family_id == "INTANGIBLE_FIXED_ASSETS_ROLLFORWARD":
        pinned_query_receipt = PINNED_INTANGIBLE_QUERY_RECEIPT
        pinned_metrics = PINNED_INTANGIBLE_RELEASE_METRICS
        pinned_audit_metrics = PINNED_INTANGIBLE_RELEASE_AUDIT_METRICS
        pinned_axis_sha256 = PINNED_INTANGIBLE_RELEASE_AXIS_SHA256
        pinned_spec_refs = PINNED_INTANGIBLE_SPEC_REFS
        expected_axis_counts = {
            "clusters": 72,
            "equations": 1120,
            "historical_comparator": 155,
            "mappings": 829,
        }
    elif family_id == "INVESTMENT_PROPERTY_ROLLFORWARD":
        pinned_query_receipt = PINNED_INVESTMENT_PROPERTY_QUERY_RECEIPT
        pinned_metrics = PINNED_INVESTMENT_PROPERTY_RELEASE_METRICS
        pinned_audit_metrics = PINNED_INVESTMENT_PROPERTY_RELEASE_AUDIT_METRICS
        pinned_axis_sha256 = PINNED_INVESTMENT_PROPERTY_RELEASE_AXIS_SHA256
        pinned_spec_refs = PINNED_INVESTMENT_PROPERTY_SPEC_REFS
        expected_axis_counts = {
            "clusters": 12,
            "equations": 185,
            "historical_comparator": 43,
            "mappings": 110,
        }
    else:
        raise _error("fixed-asset-rollforward release family is not pinned")
    actual = {
        "audit_metrics": audit.get("audit_metrics"),
        "axis_counts": audit.get("axis_counts"),
        "axis_sha256": audit.get("axis_sha256"),
        "corpus_manifest_index_id": index.get("corpus_manifest_index_id"),
        "query_receipt": indexed.get("query_receipt"),
        "selected_page_json_frontier_sha256": canonical_json_sha256_v1(list(selected_ids)),
        "spec_refs": audit.get("spec_refs"),
        "sweep_metrics": sweep.get("metrics"),
    }
    mismatches = []
    if actual["corpus_manifest_index_id"] != PINNED_CORPUS_MANIFEST_INDEX_ID:
        mismatches.append("corpus_manifest_index_id")
    if actual["selected_page_json_frontier_sha256"] != PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256:
        mismatches.append("selected_page_json_frontier_sha256")
    if not same_typed_json_v1(actual["query_receipt"], pinned_query_receipt):
        mismatches.append("query_receipt")
    if not same_typed_json_v1(actual["sweep_metrics"], pinned_metrics):
        mismatches.append("sweep_metrics")
    if not same_typed_json_v1(actual["audit_metrics"], pinned_audit_metrics):
        mismatches.append("audit_metrics")
    if not same_typed_json_v1(audit.get("axis_sha256"), pinned_axis_sha256):
        mismatches.append("axis_sha256")
    if not same_typed_json_v1(actual["spec_refs"], pinned_spec_refs):
        mismatches.append("spec_refs")
    if any(
        actual["axis_counts"].get(name) != count for name, count in expected_axis_counts.items()
    ):
        mismatches.append("axis_counts")
    if mismatches:
        raise _error(
            "fixed-asset-rollforward frozen corpus release pin drifted: "
            + ",".join(mismatches)
            + "; actual="
            + json.dumps(actual, ensure_ascii=False, sort_keys=True)
        )


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical_json_bytes_v1(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
            raise _error("fixed-asset-rollforward output exists with different bytes")
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _trials(
    *, indexed: Mapping[str, Any], candidates_by_ordinal: Mapping[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    trials = []
    for document, disposition in zip(
        indexed["selected_document_axis"], indexed["candidate_dispositions"], strict=True
    ):
        ordinal = document["document_ordinal"]
        candidate = candidates_by_ordinal.get(ordinal)
        if candidate is not None and candidate["status"] == READY:
            status = READY
            reasons = []
            mappings = candidate["mappings"]
            selected_candidate_id = candidate["candidate_id"]
        elif candidate is not None:
            status = UNRESOLVED
            reasons = candidate["reasons"]
            mappings = []
            selected_candidate_id = None
        elif disposition["disposition"] == NOT_OBSERVED:
            status = NOT_OBSERVED
            reasons = []
            mappings = []
            selected_candidate_id = None
        else:
            status = UNRESOLVED
            reasons = disposition["cluster"]["reasons"]
            mappings = []
            selected_candidate_id = None
        trials.append(
            {
                "candidate_count": int(candidate is not None),
                "candidates": [] if candidate is None else [candidate],
                "document_ordinal": ordinal,
                "mappings": mappings,
                "reasons": reasons,
                "selected_candidate_id": selected_candidate_id,
                "source_logical_name": document["source_logical_name"],
                "source_sha256": document["source_sha256"],
                "status": status,
            }
        )
    return trials


def _load_selected_pages_by_document(
    database: Path,
    *,
    selected_ids: Sequence[str],
    selected_page_axis: Sequence[Mapping[str, Any]],
) -> dict[int, dict[str, dict[str, Any]]]:
    """Decode the exact caller frontier from the already authenticated snapshot."""

    axis_by_version = {item["page_json_version_id"]: item for item in selected_page_axis}
    if len(axis_by_version) != len(selected_ids) or list(axis_by_version) != list(selected_ids):
        raise _error("fixed-asset-rollforward selected page/evidence order drifted")
    result: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        connection.execute(
            "CREATE TEMP TABLE selected_fixed_asset_rollforward_runner_page("
            "selection_ordinal INTEGER PRIMARY KEY, page_json_version_id TEXT NOT NULL UNIQUE)"
        )
        connection.executemany(
            "INSERT INTO selected_fixed_asset_rollforward_runner_page VALUES (?,?)",
            enumerate(selected_ids, start=1),
        )
        rows = connection.execute(
            """
            SELECT selected.page_json_version_id, version.canonical_json_bytes
            FROM selected_fixed_asset_rollforward_runner_page AS selected
            JOIN page_json_version AS version USING(page_json_version_id)
            ORDER BY selected.selection_ordinal
            """
        )
        loaded_ids = []
        for page_json_version_id, canonical_json_bytes in rows:
            loaded_ids.append(page_json_version_id)
            try:
                page_json = json.loads(bytes(canonical_json_bytes))
            except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _error(
                    "fixed-asset-rollforward selected canonical page JSON is invalid"
                ) from exc
            if type(page_json) is not dict:
                raise _error("fixed-asset-rollforward selected canonical page is not one object")
            axis = axis_by_version[page_json_version_id]
            result[axis["document_ordinal"]][page_json_version_id] = page_json
    finally:
        connection.close()
    if loaded_ids != list(selected_ids):
        raise _error("fixed-asset-rollforward selected canonical page frontier is incomplete")
    return result


def _run_with_authenticated_database(
    args: argparse.Namespace,
    *,
    index: Mapping[str, Any],
    database_guard: _AuthenticatedSqliteSnapshot,
    selected_ids: list[str],
    topology: dict[str, Any],
    evaluation: dict[str, Any],
    schema: dict[str, Any],
    compiled: dict[str, Any],
    spec_refs: dict[str, Any],
) -> dict[str, Any]:
    database = database_guard.path
    indexed = query_selected_fixed_asset_rollforward_family_regions_v1(
        database, selected_page_json_version_ids=selected_ids, compiled_specs=compiled
    )
    validate_selected_fixed_asset_rollforward_family_query_evidence_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
    )
    page_json_by_document = _load_selected_pages_by_document(
        database,
        selected_ids=selected_ids,
        selected_page_axis=indexed["selected_page_axis"],
    )
    candidates_by_ordinal = {}
    for cluster in indexed["accepted_clusters"]:
        regions = cluster["component_regions"]
        controls = cluster["control_regions"]
        candidates_by_ordinal[cluster["document_ordinal"]] = (
            evaluate_gemini_json_fixed_asset_rollforward_family_cluster_v1(
                regions=regions,
                control_regions=controls,
                page_json_by_version=page_json_by_document[cluster["document_ordinal"]],
                compiled_specs=compiled,
                query_receipt=build_gemini_json_fixed_asset_rollforward_region_query_receipt_v1(
                    regions, control_regions=controls
                ),
            )
        )
    trials = _trials(indexed=indexed, candidates_by_ordinal=candidates_by_ordinal)
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id=index["corpus_manifest_index_id"],
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
        indexed_query_evidence=indexed,
    )
    validate_gemini_json_flat_family_sweep_v1(sweep)
    validate_selected_fixed_asset_rollforward_family_candidate_replays_v1(
        database,
        selected_page_json_version_ids=selected_ids,
        compiled_specs=compiled,
        indexed_query_evidence=indexed,
        trials=trials,
    )
    audit = build_fixed_asset_rollforward_experimental_audit_v1(
        sweep=sweep,
        sweep_output=args.output,
        historical_comparator_policy=args.historical_comparator_policy,
        current_manifest_index_id=index["corpus_manifest_index_id"],
        current_manifest_source_sha256s=[
            document["source_sha256"] for document in index["documents"]
        ],
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    validate_fixed_asset_rollforward_experimental_audit_replay_v1(
        audit,
        database=database,
        sweep=sweep,
        sweep_output=args.output,
        historical_comparator_policy=args.historical_comparator_policy,
        current_manifest_index_id=index["corpus_manifest_index_id"],
        current_manifest_source_sha256s=[
            document["source_sha256"] for document in index["documents"]
        ],
        selected_page_json_version_ids=selected_ids,
        indexed_query_evidence=indexed,
        trials=trials,
        compiled_specs=compiled,
        spec_refs=spec_refs,
    )
    _assert_release_pins(
        historical_comparator_policy=args.historical_comparator_policy,
        run_kind=args.run_kind,
        index=index,
        selected_ids=selected_ids,
        sweep=sweep,
        indexed=indexed,
        audit=audit,
    )
    database_guard.validate()
    audit_output = args.output.with_suffix(".audit.json")
    _write_once(args.output, sweep)
    _write_once(audit_output, audit)
    implementation_paths = (
        ROOT
        / "scripts/experiments/run_gemini_json_fixed_asset_rollforward_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/accounting_family_topology_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_fixed_asset_rollforward_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/gemini_json_flat_accounting_family_v1.py",
        ROOT / "src/bctc_ai/evaluation/historical_comparator_policy_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_accounting_family_store_v1.py",
        ROOT / "src/bctc_ai/storage/gemini_financial_page_store_v1.py",
    )
    stored = ingest_gemini_accounting_family_sweep_v1(
        args.results_database,
        sweep=sweep,
        corpus_index_ref=_file_ref(args.corpus_index),
        implementation_refs=[_file_ref(path, root=ROOT) for path in implementation_paths],
        run_kind=args.run_kind,
        source_page_database=database,
        selected_page_json_version_ids=selected_ids,
        corpus_artifact_root=args.artifact_root.resolve(),
    )
    stored_sweep = load_gemini_accounting_family_sweep_v1(
        args.results_database, stored["family_run_id"]
    )
    if not same_typed_json_v1(stored_sweep, sweep):
        raise _error("stored fixed-asset-rollforward sweep differs from authenticated evaluation")
    output_ref = record_gemini_accounting_family_export_v1(
        args.results_database, family_run_id=stored["family_run_id"], output_path=args.output
    )
    database_guard.validate()
    return {
        "audit_id": audit["audit_id"],
        "audit_output": str(audit_output),
        "axis_counts": audit["axis_counts"],
        "axis_sha256": audit["axis_sha256"],
        "disposition": "SUCCEEDED",
        "family_run_id": stored["family_run_id"],
        "historical_comparator_policy": args.historical_comparator_policy,
        "metrics": sweep["metrics"],
        "output": str(args.output),
        "output_ref": output_ref,
        "results_database": str(args.results_database),
        "run_kind": args.run_kind,
        "sweep_id": sweep["sweep_id"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.run_kind == "OFFICIAL" and args.historical_comparator_policy != STRICT_RELEASE:
        raise _error("OFFICIAL fixed-asset-rollforward run requires STRICT_RELEASE policy")
    index = validate_current_corpus_manifest_index_v1(_json(args.corpus_index))
    artifact_root = args.artifact_root.resolve()
    source_database = _content_ref(artifact_root, index["database_ref"])
    selected_ids = _selected_page_axis(index=index, artifact_root=artifact_root)
    topology = _json(args.topology_spec)
    evaluation = _json(args.evaluation_spec)
    schema = _json(args.schema_binding_spec)
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    spec_refs = {
        "evaluation": _file_ref(args.evaluation_spec, root=ROOT),
        "schema_binding": _file_ref(args.schema_binding_spec, root=ROOT),
        "topology": _file_ref(args.topology_spec, root=ROOT),
    }
    with _authenticated_sqlite_snapshot(
        source_database, reference=index["database_ref"]
    ) as database_guard:
        return _run_with_authenticated_database(
            args,
            index=index,
            database_guard=database_guard,
            selected_ids=selected_ids,
            topology=topology,
            evaluation=evaluation,
            schema=schema,
            compiled=compiled,
            spec_refs=spec_refs,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-index", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--topology-spec", type=Path, required=True)
    parser.add_argument("--evaluation-spec", type=Path, required=True)
    parser.add_argument("--schema-binding-spec", type=Path, required=True)
    parser.add_argument("--results-database", type=Path, required=True)
    parser.add_argument("--run-kind", choices=("EXPERIMENTAL", "OFFICIAL"), required=True)
    parser.add_argument(
        "--historical-comparator-policy",
        choices=(STRICT_RELEASE, DISJOINT_EXPANSION),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    print(json.dumps(run(_parser().parse_args()), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
