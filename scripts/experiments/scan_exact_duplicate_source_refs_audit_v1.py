"""Read-only scanner for exact duplicate mapping source references.

The scanner never rewrites an input artifact.  It emits one canonical JSON
receipt beside this script so the bounded audit can be reproduced locally.
"""

from __future__ import annotations

from collections import Counter
import glob
import hashlib
import json
from pathlib import Path


ROOT = Path("/dev/shm/shared-provenance-audit-views")
COMMON_ROOT = Path("/dev/shm/bctc-ai-27-bank-family-live-v1")
OUTPUT = ROOT / "SCAN.json"

EXPECTED_COMMON_FAMILIES = {
    "OTHER_LONG_TERM_INVESTMENTS",
    "OTHER_ASSETS",
    "GOVERNMENT_SBV_LIABILITIES",
    "ENTRUSTED_INVESTMENT_RISK_CAPITAL",
    "ISSUED_VALUABLE_PAPERS",
    "OTHER_PAYABLES_LIABILITIES",
    "INTEREST_INCOME",
    "INTEREST_EXPENSE",
    "SERVICE_ACTIVITY",
    "FX_GOLD_ACTIVITY",
    "TRADING_SECURITIES_ACTIVITY",
    "INVESTMENT_SECURITIES_ACTIVITY",
    "CAPITAL_CONTRIBUTION_DIVIDEND_INCOME",
}

EXPECTED_FULL271_FAMILIES = (
    EXPECTED_COMMON_FAMILIES - {"OTHER_PAYABLES_LIABILITIES"}
) | {"INVESTMENT_SECURITIES"}

FULL271_CURRENT_AFFECTED = [
    Path("/dev/shm/f16-acceptance-full271-v8-final.VXxHpQ/family16.json"),
    Path("/dev/shm/f17-source-repair-full271.cyJpNa/family17.json"),
    Path("/dev/shm/f22-bb319-full271-v3.json"),
    Path("/dev/shm/family23-full271-v16.json"),
    Path("/dev/shm/f24-full271-release-v3.json"),
    Path("/dev/shm/f25-full271-bb319-final-v2/family25.json"),
    Path("/dev/shm/f28-acceptance-bb319.psXwrU/family28.json"),
    Path("/dev/shm/f29-full271-authoritative.B0v23G/family29.json"),
    Path("/dev/shm/family30-authoritative-bb319-v3.tXqkaT/sweep.json"),
    Path("/dev/shm/f31-bb319-full271-final-v2/family31.json"),
    Path("/dev/shm/f32-full271-authoritative-v2/sweep.json"),
    Path("/dev/shm/family33-authoritative-v3/sweep.json"),
    Path("/dev/shm/f35-full271-specialized-final-v2.json"),
]

COMMON204_CURRENT_F16 = Path(
    "/dev/shm/f16-acceptance-current204-v9-final.uKoaWc/family16.json"
)
CURRENT_F26_COMMON204 = Path(
    "/dev/shm/f26-bb319-common204-release-v1/family26.json"
)
CURRENT_F26_FULL271 = Path(
    "/dev/shm/f26-bb319-full271-release-v2/family26.json"
)
CROSS_FAMILY_FULL271_REPORT = Path("/dev/shm/cross-family-audit-s3-readback.md")
CROSS_FAMILY_FULL271_REPORT_SHA256 = (
    "2a71885bc3a7eae4b526bfa39de49fa6f4a15d17dd8ba3ae3f8c791c9d8fe784"
)


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def exact_key(value: object) -> str:
    # The canonical JSON text itself is the identity key, avoiding hash-only
    # equality and retaining Python JSON scalar types.
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def scan(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    sweep = json.loads(raw)
    state_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    multiplicity_counts: Counter[str] = Counter()
    affected_documents: set[str] = set()
    mapping_count = 0
    source_ref_count = 0
    duplicate_mapping_count = 0
    redundant_ref_count = 0
    singleton_row_id_churn_count = 0
    numeric_axis = []

    for trial in sweep.get("trials", []):
        for mapping in trial.get("mappings", []):
            mapping_count += 1
            source_refs = mapping.get("source_refs", [])
            source_ref_count += len(source_refs)
            counts = Counter(exact_key(ref) for ref in source_refs)
            redundant = sum(count - 1 for count in counts.values() if count > 1)
            numeric_axis.append(
                {
                    "report_norm_id": mapping.get("report_norm_id"),
                    "role": mapping.get("role"),
                    "source_sha256": trial.get("source_sha256"),
                    "state": mapping.get("state"),
                    "unit": mapping.get("unit"),
                    "values": mapping.get("values"),
                }
            )
            if not redundant:
                continue
            duplicate_mapping_count += 1
            redundant_ref_count += redundant
            affected_documents.add(trial["source_sha256"])
            state_counts[mapping["state"]] += 1
            role_counts[mapping["role"]] += 1
            multiplicity_counts[f"{len(source_refs)}->{len(counts)}"] += 1
            if len(counts) == 1 and str(mapping.get("row_id", "")).startswith(
                ("corroborated:", "aggregate:")
            ):
                singleton_row_id_churn_count += 1

    return {
        "affected_document_count": len(affected_documents),
        "duplicate_mapping_count": duplicate_mapping_count,
        "family_id": sweep.get("family_id"),
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "format_version": sweep.get("format_version"),
        "mapping_count": mapping_count,
        "metrics": sweep.get("metrics"),
        "multiplicity_counts_before_to_unique": dict(sorted(multiplicity_counts.items())),
        "numeric_axis_sha256": hashlib.sha256(canonical_bytes(numeric_axis)).hexdigest(),
        "path": str(path),
        "redundant_ref_count": redundant_ref_count,
        "role_counts": dict(sorted(role_counts.items())),
        "singleton_row_id_churn_count_if_rebuilt_before_seal": (
            singleton_row_id_churn_count
        ),
        "source_ref_count": source_ref_count,
        "state_counts": dict(sorted(state_counts.items())),
        "unique_source_ref_count_after_exact_stable_dedup": (
            source_ref_count - redundant_ref_count
        ),
    }


def aggregate(records: list[dict[str, object]]) -> dict[str, object]:
    totals: Counter[str] = Counter()
    states: Counter[str] = Counter()
    multiplicities: Counter[str] = Counter()
    for record in records:
        for key in (
            "mapping_count",
            "source_ref_count",
            "duplicate_mapping_count",
            "redundant_ref_count",
            "unique_source_ref_count_after_exact_stable_dedup",
            "singleton_row_id_churn_count_if_rebuilt_before_seal",
        ):
            totals[key] += int(record[key])
        states.update(record["state_counts"])
        multiplicities.update(record["multiplicity_counts_before_to_unique"])
    return {
        "family_count": len(records),
        "multiplicity_counts_before_to_unique": dict(sorted(multiplicities.items())),
        "state_counts": dict(sorted(states.items())),
        "totals": dict(sorted(totals.items())),
    }


def main() -> None:
    common_paths = sorted(
        Path(path)
        for path in glob.glob(str(COMMON_ROOT / "family-[0-9][0-9]-*.json"))
        if not path.endswith(".audit.json")
    )
    common_all = [scan(path) for path in common_paths]
    common_affected = [row for row in common_all if row["duplicate_mapping_count"]]
    actual = {row["family_id"] for row in common_affected}
    assert actual == EXPECTED_COMMON_FAMILIES, (actual, EXPECTED_COMMON_FAMILIES)
    assert len(common_paths) == 50
    assert sum(int(row["mapping_count"]) for row in common_all) == 32_404

    full271 = [scan(path) for path in FULL271_CURRENT_AFFECTED]
    assert all(row["duplicate_mapping_count"] for row in full271)
    actual_full271 = {row["family_id"] for row in full271}
    assert actual_full271 == EXPECTED_FULL271_FAMILIES, (
        actual_full271,
        EXPECTED_FULL271_FAMILIES,
    )

    common_f16_compatibility = next(
        row for row in common_all if row["family_id"] == "INVESTMENT_SECURITIES"
    )
    common_f16_current = scan(COMMON204_CURRENT_F16)
    current_f26_common204 = scan(CURRENT_F26_COMMON204)
    current_f26_full271 = scan(CURRENT_F26_FULL271)
    assert common_f16_compatibility["duplicate_mapping_count"] == 0
    assert common_f16_current["duplicate_mapping_count"] == 12
    assert current_f26_common204["family_id"] == "LOAN_INTEREST_ACCRUAL_CLASSIFICATION"
    assert current_f26_full271["family_id"] == "LOAN_INTEREST_ACCRUAL_CLASSIFICATION"
    assert current_f26_common204["duplicate_mapping_count"] == 0
    assert current_f26_full271["duplicate_mapping_count"] == 0
    assert file_sha256(CROSS_FAMILY_FULL271_REPORT) == CROSS_FAMILY_FULL271_REPORT_SHA256

    intersection = actual.intersection(actual_full271)
    union = actual.union(actual_full271)

    result = {
        "authority": {
            "code_checkpoint_commit": "7b2e33d900d6d10fe6e339cd31847b8a86707060",
            "investment_securities_engine_sha256": (
                "809e6c11d50e3970f4fff26588a84a62e031fe238a9d6cf2282ac01ff0ca7783"
            ),
            "migration_branch_tip": "8efd618b6c77f0cdbb402a440e7ba3b3549184f1",
            "other_long_term_engine_sha256": (
                "af4cbdbf3eb63eb799b2a1a475db66726b8e9d1f3a133b0d897ebdd47d567fc5"
            ),
            "read_only": True,
            "release_authority": False,
            "shared_multitable_evaluator_sha256": (
                "bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2"
            ),
        },
        "classification": {
            "numeric_double_count_proven": False,
            "reason": (
                "The shared lane reconciler appends one row-level source_refs vector "
                "for each selected period lane while selecting exactly one value cell "
                "per lane. Exact stable dedup changes provenance multiplicity and "
                "content-addressed identities, not role/unit/state/value vectors."
            ),
            "systemic_exact_provenance_redundancy": True,
        },
        "common204_exhaustive": {
            "affected": common_affected,
            "aggregate": aggregate(common_affected),
            "all_family_artifact_count": len(common_all),
            "all_family_mapping_count": sum(
                int(row["mapping_count"]) for row in common_all
            ),
            "scope_note": (
                "Frozen 19-new-bank/204-complete-document baseline restored by the "
                "migration. Artifact ordinals are historical; family_id is authoritative."
            ),
        },
        "format_version": "SHARED_EXACT_DUPLICATE_SOURCE_REF_AUDIT_V2",
        "full271_current_operational": {
            "affected": full271,
            "aggregate": aggregate(full271),
            "cross_family_surface_audit": {
                "affected_family_count": 13,
                "duplicate_mapping_count": 12_779,
                "path": str(CROSS_FAMILY_FULL271_REPORT),
                "redundant_ref_count": 13_918,
                "scanned_mapping_count": 24_011,
                "sha256": CROSS_FAMILY_FULL271_REPORT_SHA256,
            },
            "scope_note": (
                "Current operational full271 terminal-artifact scan. Historical F27 "
                "was omitted by the independent surface audit because its artifact has "
                "a different query shape. Retired legacy OTHER_PAYABLES_LIABILITIES is "
                "not part of the current operational axis; current ordinal F26 is "
                "LOAN_INTEREST_ACCRUAL_CLASSIFICATION."
            ),
        },
        "authority_reconciliation": {
            "common204_affected_family_ids": sorted(actual),
            "common204_only_family_ids": sorted(actual - actual_full271),
            "current_f26_negative_controls": {
                "common204": current_f26_common204,
                "full271": current_f26_full271,
            },
            "f16_artifact_freshness_query_shape": {
                "frozen_common204_compatibility_artifact": common_f16_compatibility,
                "later_current204_terminal_artifact": common_f16_current,
                "note": (
                    "The restored family-live F16 artifact is an older 573-mapping, "
                    "56-ready/148-unresolved compatibility/query-shape result and has "
                    "zero duplicates. The later terminal current204 F16 artifact has "
                    "2,539 mappings, 204 ready and the same 12 duplicates seen on "
                    "full271. Therefore F16's absence from the frozen directory scan is "
                    "artifact freshness/query-shape omission, not evidence of safety."
                ),
            },
            "full271_affected_family_ids": sorted(actual_full271),
            "full271_only_family_ids": sorted(actual_full271 - actual),
            "intersection_family_count": len(intersection),
            "intersection_family_ids": sorted(intersection),
            "union_family_count": len(union),
            "union_family_ids": sorted(union),
        },
        "pdf_witnesses": [
            {
                "family_id": "OTHER_LONG_TERM_INVESTMENTS",
                "image_path": str(ROOT / "ABB-doc003-p019.png"),
                "image_sha256": file_sha256(ROOT / "ABB-doc003-p019.png"),
                "mapping_role": "JOINT_VENTURE",
                "physical_page": 19,
                "source_path": (
                    "/workspace/bctc-ai/vietstock_bctc/ABB/2025/"
                    "BCTC Hợp nhất quý 1 năm 2025.pdf"
                ),
                "source_sha256": (
                    "58bd3fe4b64b1b569631d335c31b6616771c54fa059b016eceaba68029060810"
                ),
                "source_ref_multiplicity": "2->1",
                "values": [0, 0],
            },
            {
                "family_id": "INTEREST_INCOME",
                "image_path": str(ROOT / "ABB-doc003-p023.png"),
                "image_sha256": file_sha256(ROOT / "ABB-doc003-p023.png"),
                "mapping_role": "DEPOSIT_INTEREST",
                "physical_page": 23,
                "source_path": (
                    "/workspace/bctc-ai/vietstock_bctc/ABB/2025/"
                    "BCTC Hợp nhất quý 1 năm 2025.pdf"
                ),
                "source_sha256": (
                    "58bd3fe4b64b1b569631d335c31b6616771c54fa059b016eceaba68029060810"
                ),
                "source_ref_multiplicity": "2->1",
                "values": [475263, 202330],
            },
        ],
        "proposed_invariant": (
            "Every emitted mapping.source_refs list is non-empty and pairwise unique "
            "under exact typed canonical JSON identity; distinct source rows, pages, "
            "tables, hierarchy paths, labels, or money-column frontiers remain distinct."
        ),
        "root_cause": {
            "direct_and_shared_function": (
                "src/bctc_ai/evaluation/"
                "gemini_json_other_long_term_investments_family_v1.py:_global_records"
            ),
            "fault_site": "lines 2802-2804 at migration authority: extend full record source_refs once per lane",
            "shared_import": (
                "src/bctc_ai/evaluation/"
                "gemini_json_multitable_hierarchical_family_v1.py:42-53"
            ),
            "shared_wrapper": (
                "src/bctc_ai/evaluation/"
                "gemini_json_multitable_hierarchical_family_v1.py:_multitable_global_records"
            ),
            "f16_distinct_origin": (
                "src/bctc_ai/evaluation/"
                "gemini_json_investment_securities_family_v1.py:"
                "_corroborate_identical lines 2715-2777; exact refs from identical "
                "records are concatenated and a derived parent can inherit that vector"
            ),
        },
        "verdict": (
            "CONFIRMED_SYSTEMIC_PROVENANCE_REDUNDANCY_WITH_AUTHORITY_DEPENDENT_"
            "AFFECTED_SET_REQUIRES_STAGED_RESEAL"
        ),
    }
    result["audit_id"] = "sharedsourcerefsv1:audit:" + hashlib.sha256(
        canonical_bytes(result)
    ).hexdigest()
    OUTPUT.write_bytes(canonical_bytes(result))
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "sha256": file_sha256(OUTPUT),
                "size_bytes": OUTPUT.stat().st_size,
                "common204": result["common204_exhaustive"]["aggregate"],
                "full271": result["full271_current_operational"]["aggregate"],
                "reconciliation": result["authority_reconciliation"],
                "verdict": result["verdict"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
