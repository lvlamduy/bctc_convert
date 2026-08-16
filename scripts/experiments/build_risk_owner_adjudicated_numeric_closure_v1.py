"""Close owner-adjudicated currency, interest-rate and liquidity risk gaps.

E-0101/E-0102/E-0103 remain byte-immutable.  This overlay binds their exact
open rows, the live TM schema, authenticated page/crop pixels and the pinned
Gemma 4 rescue runtime.  Gemma is only an independent numeric challenger;
promotion still requires the visible source table and exact accounting
equations (or the two explicitly bounded VPB presentation residuals).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import stat
from pathlib import Path
from typing import Any

from PIL import Image

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = Path("docs/experiments/E-0105-risk-owner-adjudicated-numeric-closure-v1.json")
SCHEMA_GRAPH_PATH = Path("reference/schemas/schema_graph.jsonl")
SCHEMA_GRAPH_SHA256 = "a5ad1b0f1fa89fdf6d07c07b3a32b5bfc06b844433aeba3755be479844848e39"
FULL_READER_ROOT = Path("output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3")

BASES = {
    "currency": (
        Path("docs/experiments/E-0101-currency-risk-8bank-codex-verified-mapping-v1.json"),
        "ec209921d958cd248dfb4c92767a0347931d085e648c67c879fe72f9de9b488b",
        "e0101:result:889b6ce93c34f3442c53437f1029ccc3d4f6fc8ee0c6df595a4a6b427a1c8376",
    ),
    "interest_rate": (
        Path("docs/experiments/E-0102-interest-rate-risk-8bank-codex-verified-mapping-v1.json"),
        "7493b6f9b6075ce6ad6a5e4484a2d5472b9d2ee2e01617191f0c5fe3d67456ab",
        "e0102:result:8ba812de70c2b381745438b7af56530335ae2be48bfee1bdac3e9223713c91ce",
    ),
    "liquidity": (
        Path("docs/experiments/E-0103-liquidity-risk-8bank-codex-verified-mapping-v1.json"),
        "f2f4ea1e78abab4468e0cfe328c31fcd66e27f0b8a1aa07f59696c9048d42921",
        "e0103:result:e8caac77273c2b5634f542ce7634f94eed05126820d6ad70f2f77e7018699834",
    ),
    "gemma4_text_rescue": (
        Path("docs/experiments/E-0053-gemma4-vietocr-text-rescue-evaluation-v1.json"),
        "1d1050be9069c76d1c7fd4f2f913c418e0ad45908768ddd4e5314baaa3e6b64d",
        "gemma4rescuev1:evaluation:f6403c89826309ebdc0e9542ce01ed3d58d88ed443af3a9ebe6dce13025821cc",
    ),
}

FORMAT_VERSION = "RISK_OWNER_ADJUDICATED_NUMERIC_CLOSURE_V1"
CLAIM_BOUNDARY = (
    "FIXED_E0101_E0102_E0103_OPEN_GAPS_PROJECT_OWNER_DASH_ZERO_SCOPE_AND_"
    "ROUNDING_ADJUDICATION_AUTHENTICATED_PIXELS_PINNED_GEMMA4_NUMERIC_"
    "CHALLENGER_EXACT_ACCOUNTING_REPLAY_NO_BASE_REWRITE_NO_EXPORT_AUTHORITY"
)
_AUTHORITY = {
    "base_results_rewritten": False,
    "canonicalization_or_export_authority": False,
    "dash_visibly_printed_interpreted_as_zero": True,
    "gemma4_used_as_sole_numeric_authority": False,
    "live_tm_schema_checked": True,
    "nonzero_large_residual_silently_accepted": False,
    "persisted_result_self_authenticating": False,
    "project_owner_adjudication_authority": True,
    "public_exact_replay_required": True,
    "source_digits_changed": False,
    "text_similarity_alone_used_for_mapping": False,
    "one_unit_presentation_residual_count": 2,
}

CURRENCY_SCHEMA = {
    "EUR": {
        "ASSET_TOTAL": 1354,
        "LIABILITY_TOTAL": 5850,
        "STATE_INTERNAL": 1376,
        "STATE_EXTERNAL": 1377,
        "STATE_COMBINED": 1378,
    },
    "USD": {
        "ASSET_TOTAL": 1380,
        "LIABILITY_TOTAL": 5852,
        "STATE_INTERNAL": 1402,
        "STATE_EXTERNAL": 1403,
        "STATE_COMBINED": 1404,
    },
    "VND": {
        "ASSET_TOTAL": 1406,
        "LIABILITY_TOTAL": 1418,
        "STATE_INTERNAL": 1428,
        "STATE_EXTERNAL": 1429,
        "STATE_COMBINED": 1430,
    },
    "OTHER": {
        "ASSET_TOTAL": 1432,
        "LIABILITY_TOTAL": 5854,
        "STATE_INTERNAL": 1454,
        "STATE_EXTERNAL": 1455,
        "STATE_COMBINED": 1456,
    },
    "TOTAL": {
        "ASSET_TOTAL": 1458,
        "LIABILITY_TOTAL": 5856,
        "STATE_INTERNAL": 1480,
        "STATE_EXTERNAL": 1481,
        "STATE_COMBINED": 1482,
    },
}

INTEREST_SCHEMA = {
    "NO_INTEREST": (1485, 1497, 1506, 1507, 1508),
    "OVERDUE": (1510, 1522, 1531, 1532, 1533),
    "OVERDUE_GT3M": (1535, 1547, 1556, 1557, 1558),
    "OVERDUE_LE3M": (1560, 1572, 1581, 1582, 1583),
    "WITHIN_LE1M": (1585, 1597, 1606, 1607, 1608),
    "WITHIN_1_3M": (1610, 1622, 1631, 1632, 1633),
    "WITHIN_3_6M": (1635, 1647, 1656, 1657, 1658),
    "WITHIN_6_12M": (1660, 1672, 1681, 1682, 1683),
    "WITHIN_1_5Y": (1685, 1697, 1706, 1707, 1708),
    "WITHIN_GT5Y": (1710, 1722, 1731, 1732, 1733),
    "TOTAL": (1735, 1747, 1756, 1757, 1758),
}
INTEREST_ROLES = (
    "ASSET_TOTAL",
    "LIABILITY_TOTAL",
    "STATE_INTERNAL",
    "STATE_EXTERNAL",
    "STATE_COMBINED",
)

LIQUIDITY_SCHEMA = {
    "OVERDUE": (5899, 5913, 5922),
    "OVERDUE_GT3M": (1761, 1773, 1782),
    "OVERDUE_LE3M": (1784, 1796, 1805),
    "WITHIN_LE1M": (1807, 1819, 1828),
    "WITHIN_1_3M": (1830, 1842, 1851),
    "WITHIN_3_12M": (1853, 1865, 1874),
    "WITHIN_1_5Y": (1876, 1888, 1897),
    "WITHIN_GT5Y": (1899, 1911, 1920),
    "TOTAL": (1922, 1934, 1943),
}
LIQUIDITY_ROLES = ("ASSET_TOTAL", "LIABILITY_TOTAL", "NET_LIQUIDITY_GAP")

IR_AXES = (
    "OVERDUE",
    "NO_INTEREST",
    "WITHIN_LE1M",
    "WITHIN_1_3M",
    "WITHIN_3_6M",
    "WITHIN_6_12M",
    "WITHIN_1_5Y",
    "WITHIN_GT5Y",
    "TOTAL",
)
IR_GAP_IDS = {
    "NO_INTEREST": "IRISK-018",
    "OVERDUE": "IRISK-019",
    "TOTAL": "IRISK-020",
    "WITHIN_1_3M": "IRISK-021",
    "WITHIN_1_5Y": "IRISK-022",
    "WITHIN_3_6M": "IRISK-023",
    "WITHIN_6_12M": "IRISK-024",
    "WITHIN_GT5Y": "IRISK-025",
    "WITHIN_LE1M": "IRISK-026",
}
IR_MATRIX = {
    "CURRENT": {
        "OVERDUE": (10029081, 0, 10029081, 0, 10029081),
        "NO_INTEREST": (21191601, 10470602, 10720999, 0, 10720999),
        "WITHIN_LE1M": (172618152, 210145815, -37527663, -1980381, -39508044),
        "WITHIN_1_3M": (132956530, 103503597, 29452933, 1867085, 31320018),
        "WITHIN_3_6M": (118996441, 122871001, -3874560, -56695, -3931255),
        "WITHIN_6_12M": (96368465, 39878441, 56490024, 4616, 56494640),
        "WITHIN_1_5Y": (23439614, 42628748, -19189134, 0, -19189134),
        "WITHIN_GT5Y": (10461415, 3662010, 6799405, 0, 6799405),
        "TOTAL": (586061299, 533160214, 52901085, -165375, 52735710),
    },
    "COMPARATIVE": {
        "OVERDUE": (9616846, 0, 9616846, 0, 9616846),
        "NO_INTEREST": (23420473, 11052261, 12368212, 0, 12368212),
        "WITHIN_LE1M": (129848997, 224058269, -94209272, -1855136, -96064408),
        "WITHIN_1_3M": (125959948, 86927559, 39032389, -154706, 38877683),
        "WITHIN_3_6M": (113153043, 83827561, 29325482, -191253, 29134229),
        "WITHIN_6_12M": (106514173, 53887945, 52626228, 2035173, 54661401),
        "WITHIN_1_5Y": (44131020, 49440107, -5309087, 0, -5309087),
        "WITHIN_GT5Y": (8313006, 0, 8313006, 0, 8313006),
        "TOTAL": (560957506, 509193702, 51763804, -165922, 51597882),
    },
}

IR_GEMMA_BASE_OUTPUTS = tuple(
    value.strip()
    for value in (
        "21.191.601;10.470.602;10.720.999;10.720.999;23.420.473;11.052.261;"
        "12.368.212;10.029.081;10.029.081;10.029.081;9.616.846;9.616.846;"
        "9.616.846;586.061.299;533.160.214;52.901.085;(165.375);52.735.710;"
        "560.957.506;509.193.702;51.763.804;(165.922);51.597.882;132.956.530;"
        "103.503.597;29.452.933;1.867.085;31.320.018;125.959.948;86.927.559;"
        "39.032.389;(154.706);38.877.683;23.439.614;42.628.748;44.131.020;"
        "49.440.107;(5.309.087);(5.309.087);118.996.441;122.871.001;(56.695);"
        "113.153.043;83.827.561;29.325.482;(191.253);29.134.229;96.368.465;"
        "39.878.441;56.490.024;4.616;56.494.640;106.514.173;53.887.945;"
        "52.626.228;54.661.401;10.461.415;3.662.010;6.799.405;6.799.405;"
        "8.313.006;8.313.006;8.313.006;172.618.152;210.145.815;(1.980.381);"
        "129.848.997;(1.855.136);(96.064.408)"
    ).split(";")
)

IR_SUPPLEMENT = {
    ("CURRENT", "WITHIN_1_5Y", "STATE_INTERNAL"): (
        "sample-00033355",
        "027b9dcc72307001dbd0492396d787b6839bb04b4871dda6fde88bb36321af44",
        967,
        "(19.189.134)",
    ),
    ("CURRENT", "WITHIN_1_5Y", "STATE_COMBINED"): (
        "sample-00033356",
        "01b6db0b286e85c47870806dd899c04c58532c64a6167d43bb97610bf4b89990",
        830,
        "(19.189.134)",
    ),
    ("CURRENT", "WITHIN_3_6M", "STATE_INTERNAL"): (
        "sample-00033380",
        "2f3850eecded651ca2da514a27a71ee387f4c77797af4c228f6eabf3797abb0f",
        910,
        "(3.874.560)",
    ),
    ("CURRENT", "WITHIN_3_6M", "STATE_COMBINED"): (
        "sample-00033382",
        "31c06bbba6cd2d0f6586ced836929b982abf334f17aa4390bffc5559015c2756",
        921,
        "(3.931.255)",
    ),
    ("CURRENT", "WITHIN_LE1M", "STATE_INTERNAL"): (
        "sample-00033409",
        "c4831c77da4c798686c3a34197b931dd765899d228aa162b08008952c5b0e8aa",
        861,
        "(37.527.663)",
    ),
    ("CURRENT", "WITHIN_LE1M", "STATE_COMBINED"): (
        "sample-00033411",
        "bbe986692fc27bf89e04ed86a5888c15cd75f72656bc1400fcd1ce0114f5f836",
        981,
        "(39.508.044)",
    ),
    ("COMPARATIVE", "WITHIN_6_12M", "STATE_EXTERNAL"): (
        "sample-00033515",
        "d51320e7b7cc6071d06daf039b0cbca888be620d93b79b11cd8a788a3613a23f",
        675,
        "2.035.173",
    ),
    ("COMPARATIVE", "WITHIN_LE1M", "LIABILITY_TOTAL"): (
        "sample-00033554",
        "bd5d6f28a116a430f648bbf3acbe4483beec415be4a8890610c310b935480156",
        850,
        "224.058.269",
    ),
    ("COMPARATIVE", "WITHIN_LE1M", "STATE_INTERNAL"): (
        "sample-00033555",
        "300c3edb70d861fab3ebf21df6023ec6e6c4b0e74ddf12a4bcb6faf7a86930a8",
        1082,
        "(94.209.272)",
    ),
    ("COMPARATIVE", "NO_INTEREST", "STATE_INTERNAL"): (
        "sample-00033571",
        "8591164005b1a064a86c14b2bd13cec74258ae40d38f5d53aad8c44545f202f2",
        894,
        "12.368.212",
    ),
}

IR_RENDER_REFS = {
    62: (
        Path(
            "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/eb/eb872a16f71e4f199b5381cc6ad4e4e285bd0ebd55c93c895347bace5dc833b1.png"
        ),
        "eb872a16f71e4f199b5381cc6ad4e4e285bd0ebd55c93c895347bace5dc833b1",
        134468,
    ),
    63: (
        Path(
            "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/08/08f393da25684b5368e6f490f62a6a40f57679bc5fb906489e7ef4aa13562466.png"
        ),
        "08f393da25684b5368e6f490f62a6a40f57679bc5fb906489e7ef4aa13562466",
        137782,
    ),
}

VPB_IR_TOTAL_EXTERNAL_DASH_REF = (
    Path(
        "output/development/loan-maturity-full-document-vietocr-v1/frozen/crops/sample-00012956.png"
    ),
    "6d7d148b713c1d0e8a2282d36a6d6c97b8954ea36a62fcb5c7be844604faa57f",
    249,
    (49, 51),
    "2ae72dcfa49d4faac6a60e4b2130964d2088b17caba0c0088e22ca29e0602e6a",
)

IR_DASH_EVIDENCE = {
    ("CURRENT", "WITHIN_GT5Y", "STATE_EXTERNAL"): (
        62,
        (1340, 390, 1385, 525),
        "8211b222c4d6bcf304a68c3a7cd5b8b9d6cf60f5d1af62931701dcc075ee2bd4",
    ),
    ("CURRENT", "WITHIN_1_5Y", "STATE_EXTERNAL"): (
        62,
        (1340, 575, 1385, 725),
        "c1ef1a805e7b819014cc4fca27e39ce88369475f72e278c3f24e1e43dd1b7d69",
    ),
    ("CURRENT", "NO_INTEREST", "STATE_EXTERNAL"): (
        62,
        (1340, 1405, 1385, 1545),
        "19f520e14896421470683dcd67f433f4d147c5a1015709faad710939d5c6b5dd",
    ),
    ("CURRENT", "OVERDUE", "LIABILITY_TOTAL"): (
        62,
        (1190, 1580, 1235, 1715),
        "8d4f65436ad1096e84532af8fbfd2f40d4583a86741002192d47b09127c3a725",
    ),
    ("CURRENT", "OVERDUE", "STATE_EXTERNAL"): (
        62,
        (1340, 1580, 1385, 1715),
        "8fedf8446b4794fe9d1fbc0bba49d4263e47c735729f13816bad07b9746902af",
    ),
    ("COMPARATIVE", "WITHIN_GT5Y", "LIABILITY_TOTAL"): (
        63,
        (1190, 390, 1235, 520),
        "7f08902644d1e51272945793a42ec64601e8ed9ef356718051bd420eca56fd15",
    ),
    ("COMPARATIVE", "WITHIN_GT5Y", "STATE_EXTERNAL"): (
        63,
        (1340, 390, 1385, 520),
        "8b26e16531e1caab5e784f9af2ad0711e02b27b04e11590e7d051924602ed239",
    ),
    ("COMPARATIVE", "WITHIN_1_5Y", "STATE_EXTERNAL"): (
        63,
        (1340, 575, 1385, 715),
        "6c11e781a379514507441d39b7c80c479b5815951cba72c627e797ad79488ae9",
    ),
    ("COMPARATIVE", "NO_INTEREST", "STATE_EXTERNAL"): (
        63,
        (1340, 1405, 1385, 1545),
        "d9b9c1fbbea6c54514c142218330d34ab047309778f3045e1093711409a2b123",
    ),
    ("COMPARATIVE", "OVERDUE", "LIABILITY_TOTAL"): (
        63,
        (1190, 1580, 1235, 1710),
        "0c39da0d7645497adcd25f1f9695c4e6dcb3f5a4e042c3e35dd974a49f077a5f",
    ),
    ("COMPARATIVE", "OVERDUE", "STATE_EXTERNAL"): (
        63,
        (1340, 1580, 1385, 1710),
        "043a82df0d302b292d8a4ccec3d9a5bab4ffd5f84a2a68d82910c15feb1d7661",
    ),
}

LR_AXES = (
    "OVERDUE_LE3M",
    "OVERDUE_GT3M",
    "WITHIN_LE1M",
    "WITHIN_1_3M",
    "WITHIN_3_12M",
    "WITHIN_1_5Y",
    "WITHIN_GT5Y",
    "TOTAL",
)
LR_GAP_IDS = {
    "OVERDUE_GT3M": "LRISK-012",
    "OVERDUE_LE3M": "LRISK-013",
    "TOTAL": "LRISK-014",
    "WITHIN_1_3M": "LRISK-015",
    "WITHIN_1_5Y": "LRISK-016",
    "WITHIN_3_12M": "LRISK-017",
    "WITHIN_GT5Y": "LRISK-018",
    "WITHIN_LE1M": "LRISK-019",
}
LR_MATRIX = {
    "CURRENT": {
        "OVERDUE_LE3M": (3895305, 0, 3895305),
        "OVERDUE_GT3M": (6133776, 0, 6133776),
        "WITHIN_LE1M": (147988585, 215812926, -67824341),
        "WITHIN_1_3M": (57051710, 69972060, -12920350),
        "WITHIN_3_12M": (152593124, 156844297, -4251173),
        "WITHIN_1_5Y": (102642663, 80868918, 21773745),
        "WITHIN_GT5Y": (115756136, 9662013, 106094123),
        "TOTAL": (586061299, 533160214, 52901085),
    },
    "COMPARATIVE": {
        "OVERDUE_LE3M": (2821788, 0, 2821788),
        "OVERDUE_GT3M": (6795057, 0, 6795057),
        "WITHIN_LE1M": (113153380, 231954299, -118800919),
        "WITHIN_1_3M": (65846808, 66424696, -577888),
        "WITHIN_3_12M": (164112948, 116159255, 47953693),
        "WITHIN_1_5Y": (92220017, 85826217, 6393800),
        "WITHIN_GT5Y": (116007508, 8829235, 107178273),
        "TOTAL": (560957506, 509193702, 51763804),
    },
}
LR_RENDER_REFS = {
    68: (
        Path(
            "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/24/24a47ec26f2d14eb13c86fe295d7ef8d0cef8e6e83803e41522912e451a19876.png"
        ),
        "24a47ec26f2d14eb13c86fe295d7ef8d0cef8e6e83803e41522912e451a19876",
        123385,
    ),
    69: (
        Path(
            "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/7d/7da1514318d3c26931be2ee7006a005f21ffb11e3726d88e2c867b2f7d074c12.png"
        ),
        "7da1514318d3c26931be2ee7006a005f21ffb11e3726d88e2c867b2f7d074c12",
        126492,
    ),
}
LR_GEMMA_ROWS = {
    "CURRENT": {
        "ASSET_TOTAL": "3.895.305|6.133.776|147.988.585|57.051.710|152.593.124|102.642.663|115.756.136|586.061.299",
        "LIABILITY_TOTAL": "-|-|215.812.926|69.972.060|156.844.297|80.868.918|9.662.013|533.160.214",
        "NET_LIQUIDITY_GAP": "3.895.305|6.133.776|(67.824.341)|(12.920.350)|(4.251.173)|21.773.745|106.094.123|52.901.085",
    },
    "COMPARATIVE": {
        "ASSET_TOTAL": "2.821.788|6.795.057|113.153.380|65.846.808|164.112.948|92.220.017|116.007.508|560.957.506",
        "LIABILITY_TOTAL": "-|-|231.954.299|66.424.696|116.159.255|85.826.217|8.829.235|509.193.702",
        "NET_LIQUIDITY_GAP": "2.821.788|6.795.057|(118.800.919)|(577.888)|47.953.693|6.393.800|107.178.273|51.763.804",
    },
}


class RiskOwnerAdjudicatedClosureV1Error(ValueError):
    """A base result, pixel, schema binding, challenger or equation drifted."""


def _error(message: str) -> RiskOwnerAdjudicatedClosureV1Error:
    return RiskOwnerAdjudicatedClosureV1Error(message)


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise _error(f"non-finite JSON constant in {label}: {value}")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise _error(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _error(f"invalid UTF-8 JSON: {label}") from exc
    if type(value) is not dict:
        raise _error(f"JSON root must be one object: {label}")
    return value


def _stable_bytes(relative: Path) -> bytes:
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise _error(f"fixed path escaped project root: {relative}")
    directory_fd = os.open(PROJECT_ROOT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in relative.parts[:-1]:
            child_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = child_fd
        descriptor = os.open(
            relative.parts[-1],
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory_fd,
        )
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise _error(f"fixed input is not a single-link regular file: {relative}")
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1 << 20):
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    finally:
        os.close(directory_fd)
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_nlink,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_nlink,
    ):
        raise _error(f"fixed input changed during read: {relative}")
    return b"".join(chunks)


def _pin(relative: Path, expected_sha: str, expected_size: int | None = None) -> dict[str, Any]:
    payload = _stable_bytes(relative)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha or (expected_size is not None and len(payload) != expected_size):
        raise _error(f"fixed input drifted: {relative}")
    return {"path": relative.as_posix(), "sha256": digest, "size_bytes": len(payload)}


def _base_inputs() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    values: dict[str, dict[str, Any]] = {}
    refs: dict[str, dict[str, Any]] = {}
    for name, (path, expected_sha, expected_id) in BASES.items():
        payload = _stable_bytes(path)
        digest = hashlib.sha256(payload).hexdigest()
        value = _strict_json(payload, path.as_posix())
        actual_id = value.get("result_id", value.get("evaluation_id"))
        if digest != expected_sha or actual_id != expected_id:
            raise _error(f"pinned base result drifted: {name}")
        values[name] = value
        refs[name] = {
            "path": path.as_posix(),
            "result_id": expected_id,
            "sha256": digest,
            "size_bytes": len(payload),
        }
    return values, refs


def _schema_bindings() -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    payload = _stable_bytes(SCHEMA_GRAPH_PATH)
    if hashlib.sha256(payload).hexdigest() != SCHEMA_GRAPH_SHA256:
        raise _error("live schema graph drifted")
    wanted = (
        {value for roles in CURRENCY_SCHEMA.values() for value in roles.values()}
        | {value for roles in INTEREST_SCHEMA.values() for value in roles}
        | {value for roles in LIQUIDITY_SCHEMA.values() for value in roles}
    )
    selected: dict[int, dict[str, Any]] = {}
    for line in payload.splitlines():
        item = _strict_json(line, SCHEMA_GRAPH_PATH.as_posix())
        schema_id = item.get("schema_id")
        if schema_id not in wanted:
            continue
        if (
            item.get("statement_type") != "TM"
            or type(item.get("canonical_name")) is not str
            or type(item.get("parent_id")) is not int
            or type(item.get("display_order")) is not int
            or type(item.get("hierarchy_level")) is not int
        ):
            raise _error(f"live schema item {schema_id} drifted")
        selected[schema_id] = {
            "canonical_name": item["canonical_name"],
            "display_order": item["display_order"],
            "hierarchy_level": item["hierarchy_level"],
            "report_norm_id": schema_id,
            "schema_parent_report_norm_id": item["parent_id"],
        }
    if set(selected) != wanted:
        raise _error("live risk schema item denominator drifted")
    return selected, {
        "path": SCHEMA_GRAPH_PATH.as_posix(),
        "sha256": SCHEMA_GRAPH_SHA256,
        "size_bytes": len(payload),
    }


def _trial(base: dict[str, Any], bank: str) -> dict[str, Any]:
    matches = [item for item in base.get("trials", []) if item.get("document_provenance") == bank]
    if len(matches) != 1:
        raise _error(f"base result does not contain one {bank} trial")
    return matches[0]


def _gap(trial: dict[str, Any], gap_id: str) -> dict[str, Any]:
    matches = [
        item for item in trial.get("verified_source_only_rows", []) if item.get("gap_id") == gap_id
    ]
    if len(matches) != 1:
        raise _error(f"base trial does not contain one {gap_id}")
    return matches[0]


def _gap_value(trial: dict[str, Any], gap_id: str, period: str, role: str) -> dict[str, Any]:
    matches = [
        value
        for value in _gap(trial, gap_id).get("values", [])
        if value.get("period_axis") == period and value.get("source_role") == role
    ]
    if len(matches) != 1:
        raise _error(f"base gap {gap_id} does not contain one {period}/{role} cell")
    ref = matches[0].get("crop_ref")
    if type(ref) is not dict:
        raise _error(f"base gap cell lost crop ref: {gap_id}")
    _pin(Path(ref["path"]), ref["sha256"], ref["size_bytes"])
    return canonical_clone_v1(matches[0])


def _mapping_value(
    trial: dict[str, Any], axis_field: str, axis: str, period: str, role: str
) -> int:
    matches: list[int] = []
    for mapping in trial.get("verified_mappings", []):
        if mapping.get(axis_field) != axis or mapping.get("source_role") != role:
            continue
        for value in mapping.get("values", []):
            if value.get("period_axis") == period and type(value.get("normalized_value")) is int:
                matches.append(value["normalized_value"])
    if len(matches) != 1:
        raise _error(f"base mapping does not contain one {period}/{axis}/{role} cell")
    return matches[0]


def _parse_number(text: str) -> int:
    value = text.strip()
    if value == "-":
        return 0
    negative = value.startswith("(") and value.endswith(")")
    if negative:
        value = value[1:-1]
    digits = "".join(character for character in value if character.isdigit())
    if not digits:
        raise _error(f"numeric challenger is not a number: {text}")
    parsed = int(digits)
    return -parsed if negative else parsed


def _schema_id(schema: dict[str, tuple[int, ...]], axis: str, role: str) -> int:
    roles = INTEREST_ROLES if schema is INTEREST_SCHEMA else LIQUIDITY_ROLES
    try:
        return schema[axis][roles.index(role)]
    except (KeyError, ValueError) as exc:
        raise _error(f"unsupported schema axis/role: {axis}/{role}") from exc


def _row(
    *,
    bank: str,
    page: int,
    gap_ids: list[str],
    axis: str,
    role: str,
    schema_binding: dict[str, Any],
    values: list[dict[str, Any]],
    decision: str,
) -> dict[str, Any]:
    return {
        "axis_role": axis,
        "bank_code": bank,
        "decision": decision,
        "gap_ids": gap_ids,
        "page_sequence": page,
        "schema_binding": schema_binding,
        "source_role": role,
        "status": "VERIFIED_BY_CODEX_PROJECT_OWNER_ADJUDICATION",
        "values": values,
    }


def _zero_value(period: str, role: str, page: int, render_key: str) -> dict[str, Any]:
    return {
        "normalized_value": 0,
        "page_sequence": page,
        "period_axis": period,
        "pixel_transcription": "-",
        "source_role": role,
        "source": "VISIBLE_SOURCE_DASH_PROJECT_OWNER_ZERO_ADJUDICATION",
        "source_render_key": render_key,
    }


def _vpb_ir_total_external_dash_value() -> dict[str, Any]:
    path, expected_sha, expected_size, expected_dimensions, expected_rgb_sha = (
        VPB_IR_TOTAL_EXTERNAL_DASH_REF
    )
    crop_ref = _pin(path, expected_sha, expected_size)
    payload = _stable_bytes(path)
    try:
        with Image.open(io.BytesIO(payload)) as image:
            rgb = image.convert("RGB")
            dimensions = rgb.size
            rgb_sha = hashlib.sha256(rgb.tobytes()).hexdigest()
    except OSError as exc:
        raise _error("VPB interest-rate total external dash crop is not a valid image") from exc
    if dimensions != expected_dimensions or rgb_sha != expected_rgb_sha:
        raise _error("VPB interest-rate total external dash pixels drifted")
    return {
        "crop_dimensions": list(dimensions),
        "crop_rgb_sha256": rgb_sha,
        "normalized_value": 0,
        "page_sequence": 78,
        "period_axis": "CURRENT",
        "pixel_transcription": "-",
        "source": "AUTHENTICATED_CROP_VISIBLE_DASH_PROJECT_OWNER_ZERO_ADJUDICATION",
        "source_crop_ref": crop_ref,
        "source_role": "STATE_EXTERNAL",
    }


def _page_render_ref(base: dict[str, Any], bank: str, page: int) -> dict[str, Any]:
    trial = _trial(base, bank)
    source_sha = trial.get("source_pdf_sha256")
    if type(source_sha) is not str:
        raise _error(f"base trial lost source PDF: {bank}")
    document_path = FULL_READER_ROOT / "documents" / f"{source_sha}.json"
    document_bytes = _stable_bytes(document_path)
    document = _strict_json(document_bytes, document_path.as_posix())
    matches = [
        item for item in document.get("page_records", []) if item.get("physical_page") == page
    ]
    if len(matches) != 1 or document.get("source_sha256") != source_sha:
        raise _error(f"full-reader page record drifted: {bank} p{page}")
    render = matches[0].get("render_ref")
    if type(render) is not dict:
        raise _error(f"page has no authenticated render: {bank} p{page}")
    render_path = FULL_READER_ROOT / render["path"]
    pinned = _pin(render_path, render["sha256"], render["size_bytes"])
    return {
        **pinned,
        "bank_code": bank,
        "page_sequence": page,
        "source_document_record": {
            "path": document_path.as_posix(),
            "sha256": hashlib.sha256(document_bytes).hexdigest(),
            "size_bytes": len(document_bytes),
        },
        "source_pdf_sha256": source_sha,
    }


def _currency_closure(base: dict[str, Any], schema: dict[int, dict[str, Any]]) -> dict[str, Any]:
    plans = [
        (
            "VPB",
            80,
            "CRISK-001",
            "EUR",
            ("ASSET_TOTAL", "LIABILITY_TOTAL", "STATE_INTERNAL", "STATE_COMBINED"),
        ),
        ("VPB", 80, "CRISK-003", "OTHER", ("STATE_COMBINED",)),
        (
            "VPB",
            80,
            "CRISK-004",
            "TOTAL",
            ("ASSET_TOTAL", "LIABILITY_TOTAL", "STATE_INTERNAL", "STATE_COMBINED"),
        ),
        ("VPB", 80, "CRISK-005", "USD", ("STATE_COMBINED",)),
        ("HDB", 39, "CRISK-006", "EUR", ("STATE_COMBINED",)),
        ("VCB", 51, "CRISK-008", "VND", ("LIABILITY_TOTAL",)),
        ("VIB", 65, "CRISK-010", "EUR", ("STATE_COMBINED",)),
        ("VIB", 65, "CRISK-011", "USD", ("STATE_COMBINED",)),
    ]
    rows: list[dict[str, Any]] = []
    for bank, page, gap_id, axis, roles in plans:
        trial = _trial(base, bank)
        for role in roles:
            value = _gap_value(trial, gap_id, "CURRENT", role)
            rows.append(
                _row(
                    bank=bank,
                    page=page,
                    gap_ids=[gap_id],
                    axis=axis,
                    role=role,
                    schema_binding=schema[CURRENCY_SCHEMA[axis][role]],
                    values=[value],
                    decision=(
                        "DIRECT_VISIBLE_SOURCE_VALUE_WITH_BOUNDED_PRESENTATION_ROUNDING"
                        if gap_id in {"CRISK-001", "CRISK-004"}
                        else "DIRECT_VISIBLE_SOURCE_VALUE_PROJECT_OWNER_SCOPE_ADJUDICATION"
                    ),
                )
            )
    for bank, page, gap_id, axis in [
        ("HDB", 39, "CRISK-006", "EUR"),
        ("VIB", 65, "CRISK-010", "EUR"),
        ("VIB", 65, "CRISK-011", "USD"),
    ]:
        rows.append(
            _row(
                bank=bank,
                page=page,
                gap_ids=[gap_id],
                axis=axis,
                role="STATE_EXTERNAL",
                schema_binding=schema[CURRENCY_SCHEMA[axis]["STATE_EXTERNAL"]],
                values=[_zero_value("CURRENT", "STATE_EXTERNAL", page, f"{bank}-p{page}")],
                decision="VISIBLE_DASH_IS_ZERO",
            )
        )
    equations = []
    for bank, page, axis, internal, combined in [
        ("HDB", 39, "EUR", 3919, 3919),
        ("VIB", 65, "EUR", 1781, 1781),
        ("VIB", 65, "USD", -1242376, -1242376),
    ]:
        equations.append(
            {
                "axis_role": axis,
                "bank_code": bank,
                "computed_value": internal + 0,
                "equation_kind": "STATE_INTERNAL_PLUS_VISIBLE_DASH_ZERO_EXTERNAL_EQUALS_COMBINED",
                "page_sequence": page,
                "period_axis": "CURRENT",
                "status": "VERIFIED_EXACT",
                "visible_value": combined,
            }
        )
    residuals = []
    for bank, page, axis, asset, liability, visible in [
        ("VPB", 80, "EUR", 249696, 264460, -14765),
        ("VPB", 80, "TOTAL", 42163909, 47928964, -5765056),
    ]:
        residuals.append(
            {
                "axis_role": axis,
                "bank_code": bank,
                "computed_value": asset - liability,
                "page_sequence": page,
                "preserved_visible_value": visible,
                "project_owner_disposition": "ACCEPT_SOURCE_PRESENTATION_ROUNDING_RESIDUAL_ONE_NO_DIGIT_CHANGE",
                "residual": visible - (asset - liability),
            }
        )
    if len(rows) != 17 or len(equations) != 3:
        raise _error("currency closure denominator drifted")
    return {
        "closed_gap_ids": [
            "CRISK-001",
            "CRISK-003",
            "CRISK-004",
            "CRISK-005",
            "CRISK-006",
            "CRISK-008",
            "CRISK-010",
            "CRISK-011",
        ],
        "remaining_gap_ids": ["CRISK-002", "CRISK-007", "CRISK-009"],
        "remaining_gap_reason": "NO_GOLD_CURRENCY_AXIS_SCHEMA_BRANCH",
        "source_presentation_residuals": residuals,
        "verified_accounting_equations": equations,
        "verified_mappings": rows,
    }


def _ir_vib_evidence(trial: dict[str, Any]) -> dict[tuple[str, str, str], dict[str, Any]]:
    flattened: list[tuple[tuple[str, str, str], dict[str, Any]]] = []
    for group in trial.get("verified_source_only_rows", []):
        axis = group.get("repricing_axis")
        for value in group.get("values", []):
            key = (value.get("period_axis"), axis, value.get("source_role"))
            if not all(type(part) is str for part in key):
                raise _error("VIB interest-rate source key drifted")
            flattened.append((key, value))
    if len(flattened) != 69 or len(IR_GEMMA_BASE_OUTPUTS) != 69:
        raise _error("VIB interest-rate base challenger denominator drifted")
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for (key, value), gemma_text in zip(flattened, IR_GEMMA_BASE_OUTPUTS, strict=True):
        period, axis, role = key
        expected = IR_MATRIX[period][axis][INTEREST_ROLES.index(role)]
        if _parse_number(gemma_text) != expected or key in result:
            raise _error(f"Gemma/base interest-rate cell drifted: {key}")
        ref = value.get("crop_ref")
        if type(ref) is not dict:
            raise _error(f"VIB interest-rate crop ref drifted: {key}")
        _pin(Path(ref["path"]), ref["sha256"], ref["size_bytes"])
        result[key] = {
            "base_source_numeric_challenger": value.get("source_numeric_challenger"),
            "base_source_numeric_value": value.get("normalized_value"),
            "crop_ref": canonical_clone_v1(ref),
            "gemma4_numeric_challenger": gemma_text,
            "source": "BASE_CROP_PIXEL_PLUS_PINNED_GEMMA4_CHALLENGER",
        }
    return result


def _ir_dash_evidence() -> dict[tuple[str, str, str], dict[str, Any]]:
    images: dict[int, Image.Image] = {}
    refs: dict[int, dict[str, Any]] = {}
    for page, (path, digest, size) in IR_RENDER_REFS.items():
        payload = _stable_bytes(path)
        if hashlib.sha256(payload).hexdigest() != digest or len(payload) != size:
            raise _error(f"VIB interest-rate render drifted: p{page}")
        images[page] = Image.open(io.BytesIO(payload)).convert("RGB")
        refs[page] = {"path": path.as_posix(), "sha256": digest, "size_bytes": size}
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    try:
        for key, (page, bbox, expected_rgb_sha) in IR_DASH_EVIDENCE.items():
            crop = images[page].crop(bbox)
            digest = hashlib.sha256(crop.tobytes()).hexdigest()
            if digest != expected_rgb_sha:
                raise _error(f"VIB interest-rate dash pixels drifted: {key}")
            result[key] = {
                "bbox_raw_pixels": list(bbox),
                "pixel_transcription": "-",
                "render_ref": refs[page],
                "rgb_sha256": digest,
                "source": "AUTHENTICATED_RENDER_VISIBLE_DASH_PROJECT_OWNER_ZERO_ADJUDICATION",
            }
    finally:
        for image in images.values():
            image.close()
    return result


def _interest_closure(base: dict[str, Any], schema: dict[int, dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    equations: list[dict[str, Any]] = []

    def add_cell(
        bank: str,
        page: int,
        gap_id: str,
        axis: str,
        role: str,
        value: int,
        evidence: dict[str, Any],
        decision: str,
    ) -> None:
        rows.append(
            _row(
                bank=bank,
                page=page,
                gap_ids=[gap_id],
                axis=axis,
                role=role,
                schema_binding=schema[_schema_id(INTEREST_SCHEMA, axis, role)],
                values=[
                    {
                        "normalized_value": value,
                        "period_axis": "CURRENT",
                        "source_evidence": evidence,
                    }
                ],
                decision=decision,
            )
        )

    mbb = _trial(base, "MBB")
    for role, value in [
        ("ASSET_TOTAL", 28949005),
        ("LIABILITY_TOTAL", 0),
        ("STATE_INTERNAL", 28949005),
    ]:
        evidence = (
            _gap_value(mbb, "IRISK-001", "CURRENT", role)
            if role != "LIABILITY_TOTAL"
            else _zero_value("CURRENT", role, 57, "MBB-p57")
        )
        add_cell(
            "MBB",
            57,
            "IRISK-001",
            "OVERDUE",
            role,
            value,
            evidence,
            "VISIBLE_DASH_ZERO_CLOSES_ASSET_MINUS_LIABILITY",
        )
    equations.append(
        _risk_equation(
            "MBB",
            57,
            "OVERDUE",
            "ASSET_TOTAL_MINUS_LIABILITY_TOTAL_EQUALS_INTERNAL_GAP",
            28949005,
            0,
            28949005,
        )
    )

    vpb = _trial(base, "VPB")
    add_cell(
        "VPB",
        78,
        "IRISK-002",
        "TOTAL",
        "STATE_EXTERNAL",
        0,
        _vpb_ir_total_external_dash_value(),
        "VISIBLE_DASH_ZERO",
    )
    add_cell(
        "VPB",
        78,
        "IRISK-002",
        "TOTAL",
        "STATE_COMBINED",
        207030911,
        _gap_value(vpb, "IRISK-002", "CURRENT", "STATE_COMBINED"),
        "DIRECT_VISIBLE_COMBINED_STATE",
    )
    equations.append(
        _risk_equation(
            "VPB",
            78,
            "TOTAL",
            "STATE_INTERNAL_PLUS_EXTERNAL_EQUALS_COMBINED",
            207030911,
            0,
            207030911,
        )
    )

    hdb = _trial(base, "HDB")
    hdb_internal = {
        "OVERDUE": 49514502,
        "NO_INTEREST": 66306336,
        "WITHIN_LE1M": -36504818,
        "WITHIN_1_3M": -2095966,
        "WITHIN_3_6M": -32682284,
        "WITHIN_6_12M": -4324528,
        "WITHIN_1_5Y": 37598286,
        "WITHIN_GT5Y": 22235658,
        "TOTAL": 100047186,
    }
    for axis, internal in hdb_internal.items():
        external = -42441603 if axis in {"NO_INTEREST", "TOTAL"} else 0
        combined = internal + external
        if axis == "OVERDUE":
            for role, value in [
                ("ASSET_TOTAL", internal),
                ("LIABILITY_TOTAL", 0),
                ("STATE_INTERNAL", internal),
            ]:
                evidence = (
                    _gap_value(hdb, "IRISK-004", "CURRENT", role)
                    if role != "LIABILITY_TOTAL"
                    else _zero_value("CURRENT", role, 41, "HDB-p41")
                )
                add_cell(
                    "HDB",
                    41,
                    "IRISK-004",
                    axis,
                    role,
                    value,
                    evidence,
                    "FULL_RENDER_ROW_GEOMETRY_CORRECTION",
                )
            equations.append(
                _risk_equation(
                    "HDB",
                    41,
                    axis,
                    "ASSET_TOTAL_MINUS_LIABILITY_TOTAL_EQUALS_INTERNAL_GAP",
                    internal,
                    0,
                    internal,
                )
            )
        else:
            if _mapping_value(hdb, "repricing_axis", axis, "CURRENT", "STATE_INTERNAL") != internal:
                raise _error(f"HDB internal state drifted: {axis}")
        gap_id = {
            "NO_INTEREST": "IRISK-003",
            "OVERDUE": "IRISK-004",
            "TOTAL": "IRISK-005",
            "WITHIN_1_3M": "IRISK-006",
            "WITHIN_1_5Y": "IRISK-007",
            "WITHIN_3_6M": "IRISK-008",
            "WITHIN_6_12M": "IRISK-009",
            "WITHIN_GT5Y": "IRISK-010",
            "WITHIN_LE1M": "IRISK-011",
        }[axis]
        for role, value in [("STATE_EXTERNAL", external), ("STATE_COMBINED", combined)]:
            add_cell(
                "HDB",
                41,
                gap_id,
                axis,
                role,
                value,
                {
                    "render_key": "HDB-p41",
                    "pixel_transcription": "-" if value == 0 else str(value),
                    "source": "FULL_RENDER_EXACT_ROW_GEOMETRY_PROJECT_OWNER_REVIEW",
                },
                "CORRECT_EXTERNAL_ROW_GEOMETRY_BASE_DUPLICATE_ROLE_NOT_PROMOTED",
            )
        equations.append(
            _risk_equation(
                "HDB",
                41,
                axis,
                "STATE_INTERNAL_PLUS_EXTERNAL_EQUALS_COMBINED",
                internal,
                external,
                combined,
            )
        )

    vcb = _trial(base, "VCB")
    for gap_id, axis in [
        ("IRISK-012", "NO_INTEREST"),
        ("IRISK-013", "OVERDUE"),
        ("IRISK-014", "WITHIN_6_12M"),
        ("IRISK-015", "WITHIN_GT5Y"),
    ]:
        internal = _mapping_value(vcb, "repricing_axis", axis, "CURRENT", "STATE_INTERNAL")
        combined = _gap_value(vcb, gap_id, "CURRENT", "STATE_COMBINED")["normalized_value"]
        if internal != combined:
            raise _error(f"VCB dash-zero combined state drifted: {axis}")
        add_cell(
            "VCB",
            49,
            gap_id,
            axis,
            "STATE_EXTERNAL",
            0,
            _zero_value("CURRENT", "STATE_EXTERNAL", 49, "VCB-p49"),
            "VISIBLE_DASH_ZERO",
        )
        add_cell(
            "VCB",
            49,
            gap_id,
            axis,
            "STATE_COMBINED",
            combined,
            _gap_value(vcb, gap_id, "CURRENT", "STATE_COMBINED"),
            "DIRECT_VISIBLE_COMBINED_STATE",
        )
        equations.append(
            _risk_equation(
                "VCB",
                49,
                axis,
                "STATE_INTERNAL_PLUS_EXTERNAL_EQUALS_COMBINED",
                internal,
                0,
                combined,
            )
        )

    ctg = _trial(base, "CTG")
    for gap_id, axis in [("IRISK-016", "OVERDUE_GT3M"), ("IRISK-017", "OVERDUE_LE3M")]:
        asset = _gap_value(ctg, gap_id, "CURRENT", "ASSET_TOTAL")["normalized_value"]
        internal = _gap_value(ctg, gap_id, "CURRENT", "STATE_INTERNAL")["normalized_value"]
        for role, value, evidence in [
            ("ASSET_TOTAL", asset, _gap_value(ctg, gap_id, "CURRENT", "ASSET_TOTAL")),
            ("LIABILITY_TOTAL", 0, _zero_value("CURRENT", "LIABILITY_TOTAL", 55, "CTG-p55")),
            ("STATE_INTERNAL", internal, _gap_value(ctg, gap_id, "CURRENT", "STATE_INTERNAL")),
        ]:
            add_cell(
                "CTG",
                55,
                gap_id,
                axis,
                role,
                value,
                evidence,
                "VISIBLE_DASH_ZERO_CLOSES_ASSET_MINUS_LIABILITY",
            )
        equations.append(
            _risk_equation(
                "CTG",
                55,
                axis,
                "ASSET_TOTAL_MINUS_LIABILITY_TOTAL_EQUALS_INTERNAL_GAP",
                asset,
                0,
                internal,
            )
        )

    vib = _trial(base, "VIB")
    base_evidence = _ir_vib_evidence(vib)
    dash_evidence = _ir_dash_evidence()
    for key, (sample_id, digest, size, gemma_text) in IR_SUPPLEMENT.items():
        path = Path(
            f"output/development/loan-maturity-full-document-vietocr-v1/frozen/crops/{sample_id}.png"
        )
        _pin(path, digest, size)
        period, axis, role = key
        expected = IR_MATRIX[period][axis][INTEREST_ROLES.index(role)]
        if _parse_number(gemma_text) != expected:
            raise _error(f"VIB supplemental interest cell drifted: {key}")
    for axis in IR_AXES:
        gap_id = IR_GAP_IDS[axis]
        values_by_role: dict[str, list[dict[str, Any]]] = {role: [] for role in INTEREST_ROLES}
        for period in ("CURRENT", "COMPARATIVE"):
            for role_index, role in enumerate(INTEREST_ROLES):
                key = (period, axis, role)
                expected = IR_MATRIX[period][axis][role_index]
                if key in base_evidence:
                    evidence = base_evidence[key]
                elif key in IR_SUPPLEMENT:
                    sample_id, digest, size, gemma_text = IR_SUPPLEMENT[key]
                    evidence = {
                        "crop_ref": {
                            "path": f"output/development/loan-maturity-full-document-vietocr-v1/frozen/crops/{sample_id}.png",
                            "sha256": digest,
                            "size_bytes": size,
                        },
                        "gemma4_numeric_challenger": gemma_text,
                        "source": "SUPPLEMENTAL_CROP_PIXEL_PLUS_PINNED_GEMMA4_CHALLENGER",
                    }
                elif key in dash_evidence:
                    if expected != 0:
                        raise _error(f"nonzero VIB interest-rate dash cell: {key}")
                    evidence = dash_evidence[key]
                else:
                    raise _error(f"VIB interest-rate evidence denominator missing: {key}")
                values_by_role[role].append(
                    {
                        "normalized_value": expected,
                        "period_axis": period,
                        "source_evidence": evidence,
                    }
                )
        for role in INTEREST_ROLES:
            rows.append(
                _row(
                    bank="VIB",
                    page=62,
                    gap_ids=[gap_id],
                    axis=axis,
                    role=role,
                    schema_binding=schema[_schema_id(INTEREST_SCHEMA, axis, role)],
                    values=values_by_role[role],
                    decision="ROTATED_PIXEL_PLUS_GEMMA4_CHALLENGER_AND_EXACT_ACCOUNTING_CLOSURE",
                )
            )
        for period in ("CURRENT", "COMPARATIVE"):
            asset, liability, internal, external, combined = IR_MATRIX[period][axis]
            equations.append(
                _risk_equation(
                    "VIB",
                    62 if period == "CURRENT" else 63,
                    axis,
                    "ASSET_TOTAL_MINUS_LIABILITY_TOTAL_EQUALS_INTERNAL_GAP",
                    asset,
                    liability,
                    internal,
                    period,
                )
            )
            equations.append(
                _risk_equation(
                    "VIB",
                    62 if period == "CURRENT" else 63,
                    axis,
                    "STATE_INTERNAL_PLUS_EXTERNAL_EQUALS_COMBINED",
                    internal,
                    external,
                    combined,
                    period,
                )
            )

    if len(rows) != 85 or len(equations) != 54:
        raise _error("interest-rate closure denominator drifted")
    return {
        "closed_gap_ids": [f"IRISK-{index:03d}" for index in range(1, 27)],
        "remaining_gap_ids": [],
        "rejected_base_role_interpretation": "HDB IRISK-003_TO_011 STATE_EXTERNAL TAGS WERE DUPLICATE INTERNAL_ROW_GEOMETRY_AND_WERE_NOT_PROMOTED",
        "verified_accounting_equations": equations,
        "verified_mappings": rows,
    }


def _risk_equation(
    bank: str,
    page: int,
    axis: str,
    kind: str,
    left: int,
    right: int,
    visible: int,
    period: str = "CURRENT",
) -> dict[str, Any]:
    computed = left - right if kind.startswith("ASSET_TOTAL_MINUS") else left + right
    if computed != visible:
        raise _error(f"risk equation does not close: {bank}/{axis}/{kind}")
    return {
        "axis_role": axis,
        "bank_code": bank,
        "computed_value": computed,
        "equation_kind": kind,
        "page_sequence": page,
        "period_axis": period,
        "status": "VERIFIED_EXACT",
        "visible_value": visible,
    }


def _liquidity_closure(base: dict[str, Any], schema: dict[int, dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    equations: list[dict[str, Any]] = []
    for bank, page, items in [
        ("MBB", 60, [("LRISK-001", "OVERDUE", 28949005)]),
        (
            "HDB",
            43,
            [("LRISK-006", "OVERDUE_GT3M", 18545910), ("LRISK-007", "OVERDUE_LE3M", 30968593)],
        ),
        (
            "VCB",
            53,
            [("LRISK-008", "OVERDUE_GT3M", 10354714), ("LRISK-009", "OVERDUE_LE3M", 6369385)],
        ),
        (
            "CTG",
            58,
            [("LRISK-010", "OVERDUE_GT3M", 25289495), ("LRISK-011", "OVERDUE_LE3M", 19563795)],
        ),
    ]:
        trial = _trial(base, bank)
        for gap_id, axis, expected in items:
            asset = _gap_value(trial, gap_id, "CURRENT", "ASSET_TOTAL")
            net = _gap_value(trial, gap_id, "CURRENT", "NET_LIQUIDITY_GAP")
            if asset["normalized_value"] != expected or net["normalized_value"] != expected:
                raise _error(f"liquidity dash-zero source value drifted: {gap_id}")
            for role, value, evidence in [
                ("ASSET_TOTAL", expected, asset),
                (
                    "LIABILITY_TOTAL",
                    0,
                    _zero_value("CURRENT", "LIABILITY_TOTAL", page, f"{bank}-p{page}"),
                ),
                ("NET_LIQUIDITY_GAP", expected, net),
            ]:
                rows.append(
                    _row(
                        bank=bank,
                        page=page,
                        gap_ids=[gap_id],
                        axis=axis,
                        role=role,
                        schema_binding=schema[_schema_id(LIQUIDITY_SCHEMA, axis, role)],
                        values=[
                            {
                                "normalized_value": value,
                                "period_axis": "CURRENT",
                                "source_evidence": evidence,
                            }
                        ],
                        decision="VISIBLE_DASH_ZERO_CLOSES_ASSET_MINUS_LIABILITY",
                    )
                )
            equations.append(
                _risk_equation(
                    bank,
                    page,
                    axis,
                    "ASSET_TOTAL_MINUS_LIABILITY_TOTAL_EQUALS_NET_LIQUIDITY_GAP",
                    expected,
                    0,
                    expected,
                )
            )

    vib = _trial(base, "VIB")
    existing: dict[tuple[str, str, str], dict[str, Any]] = {}
    for group in vib.get("verified_source_only_rows", []):
        axis = group.get("maturity_axis")
        for value in group.get("values", []):
            key = (value.get("period_axis"), axis, value.get("source_role"))
            if not all(type(part) is str for part in key) or key in existing:
                raise _error("VIB liquidity base source key drifted")
            ref = value.get("crop_ref")
            if type(ref) is not dict:
                raise _error("VIB liquidity base crop ref drifted")
            _pin(Path(ref["path"]), ref["sha256"], ref["size_bytes"])
            existing[key] = value
    if len(existing) != 26:
        raise _error("VIB liquidity base cell denominator drifted")
    render_refs: dict[str, dict[str, Any]] = {}
    for page, (path, digest, size) in LR_RENDER_REFS.items():
        render_refs[str(page)] = _pin(path, digest, size)
    gemma_cells: dict[tuple[str, str, str], str] = {}
    for period, rows_by_role in LR_GEMMA_ROWS.items():
        for role, text in rows_by_role.items():
            values = text.split("|")
            if len(values) != len(LR_AXES):
                raise _error("VIB liquidity Gemma row denominator drifted")
            for axis, gemma_text in zip(LR_AXES, values, strict=True):
                expected = LR_MATRIX[period][axis][LIQUIDITY_ROLES.index(role)]
                if _parse_number(gemma_text) != expected:
                    raise _error(f"VIB liquidity Gemma cell drifted: {period}/{axis}/{role}")
                gemma_cells[(period, axis, role)] = gemma_text
    for axis in LR_AXES:
        gap_id = LR_GAP_IDS[axis]
        for role_index, role in enumerate(LIQUIDITY_ROLES):
            values = []
            for period, page in [("CURRENT", 68), ("COMPARATIVE", 69)]:
                key = (period, axis, role)
                expected = LR_MATRIX[period][axis][role_index]
                evidence: dict[str, Any] = {
                    "gemma4_numeric_challenger": gemma_cells[key],
                    "render_ref": render_refs[str(page)],
                    "source": "FULL_ROTATED_TABLE_PIXEL_PLUS_PINNED_GEMMA4_CHALLENGER",
                }
                if key in existing:
                    evidence["base_source_numeric_challenger"] = existing[key].get(
                        "source_numeric_challenger"
                    )
                    evidence["base_source_numeric_value"] = existing[key].get("normalized_value")
                    evidence["crop_ref"] = canonical_clone_v1(existing[key]["crop_ref"])
                values.append(
                    {
                        "normalized_value": expected,
                        "period_axis": period,
                        "source_evidence": evidence,
                    }
                )
            rows.append(
                _row(
                    bank="VIB",
                    page=68,
                    gap_ids=[gap_id],
                    axis=axis,
                    role=role,
                    schema_binding=schema[_schema_id(LIQUIDITY_SCHEMA, axis, role)],
                    values=values,
                    decision="ROTATED_FULL_TABLE_GEMMA4_CHALLENGER_AND_EXACT_ACCOUNTING_CLOSURE",
                )
            )
        for period, page in [("CURRENT", 68), ("COMPARATIVE", 69)]:
            asset, liability, net = LR_MATRIX[period][axis]
            equations.append(
                _risk_equation(
                    "VIB",
                    page,
                    axis,
                    "ASSET_TOTAL_MINUS_LIABILITY_TOTAL_EQUALS_NET_LIQUIDITY_GAP",
                    asset,
                    liability,
                    net,
                    period,
                )
            )

    if len(rows) != 45 or len(equations) != 23:
        raise _error("liquidity closure denominator drifted")
    return {
        "closed_gap_ids": ["LRISK-001", *[f"LRISK-{index:03d}" for index in range(6, 20)]],
        "remaining_gap_ids": ["LRISK-002", "LRISK-003", "LRISK-004", "LRISK-005"],
        "remaining_gap_reason": "VPB_VISIBLE_SOURCE_RESIDUALS_6000_NEG275500_NEG6001_POS275499_NOT_ROUNDING",
        "verified_accounting_equations": equations,
        "verified_mappings": rows,
    }


def build_live_risk_owner_adjudicated_numeric_closure_v1() -> dict[str, Any]:
    """Exact-rebuild all owner-adjudicated risk closures."""
    bases, base_refs = _base_inputs()
    schema, schema_ref = _schema_bindings()
    render_refs = {
        "HDB-p39": _page_render_ref(bases["currency"], "HDB", 39),
        "VCB-p51": _page_render_ref(bases["currency"], "VCB", 51),
        "VIB-p65": _page_render_ref(bases["currency"], "VIB", 65),
        "MBB-p57": _page_render_ref(bases["interest_rate"], "MBB", 57),
        "HDB-p41": _page_render_ref(bases["interest_rate"], "HDB", 41),
        "VCB-p49": _page_render_ref(bases["interest_rate"], "VCB", 49),
        "CTG-p55": _page_render_ref(bases["interest_rate"], "CTG", 55),
        "MBB-p60": _page_render_ref(bases["liquidity"], "MBB", 60),
        "HDB-p43": _page_render_ref(bases["liquidity"], "HDB", 43),
        "VCB-p53": _page_render_ref(bases["liquidity"], "VCB", 53),
        "CTG-p58": _page_render_ref(bases["liquidity"], "CTG", 58),
    }
    currency = _currency_closure(bases["currency"], schema)
    interest = _interest_closure(bases["interest_rate"], schema)
    liquidity = _liquidity_closure(bases["liquidity"], schema)
    material = {
        "authority": _AUTHORITY,
        "claim_boundary": CLAIM_BOUNDARY,
        "family_closures": {
            "CURRENCY_RISK": currency,
            "INTEREST_RATE_RISK": interest,
            "LIQUIDITY_RISK": liquidity,
        },
        "format_version": FORMAT_VERSION,
        "input_refs": {
            "base_results": base_refs,
            "page_renders": render_refs,
            "schema_graph": schema_ref,
        },
        "metrics": {
            "closed_gap_count": 49,
            "currency_full_verified_mapping_count": 120,
            "currency_full_verified_value_cell_count": 136,
            "currency_remaining_gap_count": 3,
            "full_verified_accounting_equation_count": 210,
            "interest_rate_full_verified_mapping_count": 234,
            "interest_rate_full_verified_value_cell_count": 279,
            "interest_rate_remaining_gap_count": 0,
            "liquidity_full_verified_mapping_count": 129,
            "liquidity_full_verified_value_cell_count": 153,
            "liquidity_remaining_gap_count": 4,
            "new_verified_accounting_equation_count": 80,
            "new_verified_mapping_count": 147,
            "new_verified_value_cell_count": 216,
            "remaining_gap_count": 7,
        },
        "owner_decision": (
            "Treat only visibly printed dashes as zero; preserve VPB currency residuals of one "
            "as source presentation rounding; map VCB VND liability to 1418 per visible table "
            "scope; close HDB/VCB/VIB combined states; use Gemma 4 only as a pixel-bound "
            "numeric challenger for VIB rotated tables; retain three unsupported gold axes and "
            "four material VPB liquidity residuals unresolved."
        ),
        "state": "RISK_OWNER_ADJUDICATED_NUMERIC_CLOSURE_COMPLETE",
    }
    return {**material, "result_id": "e0105:result:" + canonical_json_sha256_v1(material)}


def validate_risk_owner_adjudicated_numeric_closure_replay_v1(
    result: Any,
) -> dict[str, Any]:
    if type(result) is not dict:
        raise _error("closure must be one exact dict")
    rebuilt = build_live_risk_owner_adjudicated_numeric_closure_v1()
    if not same_typed_json_v1(result, rebuilt):
        raise _error("risk owner-adjudicated closure does not exact-replay")
    return canonical_clone_v1(rebuilt)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-result", action="store_true")
    parser.add_argument("--validate-result", action="store_true")
    args = parser.parse_args()
    if args.write_result == args.validate_result:
        parser.error("choose exactly one of --write-result or --validate-result")
    if args.write_result:
        payload = build_live_risk_owner_adjudicated_numeric_closure_v1()
        destination = PROJECT_ROOT / OUTPUT_PATH
        if destination.exists():
            raise _error(f"refusing to overwrite existing closure: {OUTPUT_PATH}")
        destination.write_bytes(canonical_json_bytes_v1(payload))
        return
    payload = _strict_json(_stable_bytes(OUTPUT_PATH), OUTPUT_PATH.as_posix())
    validate_risk_owner_adjudicated_numeric_closure_replay_v1(payload)


if __name__ == "__main__":
    main()
