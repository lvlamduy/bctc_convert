from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import duckdb
from pymongo import MongoClient

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.reference.historical import (
    RAW_SERIES,
    YTD_SERIES,
    historical_documents_hash,
    lookup_resolved_historical_reference,
)
from bctc_ai.schema.registry import load_all


def _collection_stats(database, name: str) -> dict[str, int]:
    stats = database.command("collStats", name)
    return {
        "document_count": database[name].count_documents({}),
        "logical_size_bytes": int(stats.get("size", 0)),
        "storage_size_bytes": int(stats.get("storageSize", 0)),
        "index_size_bytes": int(stats.get("totalIndexSize", 0)),
    }


def _historical_collection_audit(collection, identifier_field: str, category_by_code):
    identifiers = {str(value).strip().upper() for value in collection.distinct(identifier_field)}
    matched = sorted(identifiers & set(category_by_code))
    return {
        "distinct_identifier_count": len(identifiers),
        "registered_financial_code_intersection": matched,
        "intersection_by_category": dict(Counter(category_by_code[code] for code in matched)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-uri-env", default="BCTC_HISTORY_MONGO_URI")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("data/registered/historical_weak_reference_registry.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/experiments/E-0008-mongodb-historical-reference.json"),
    )
    parser.add_argument("--aborted-autocommit-lower-bound-seconds", type=float)
    parser.add_argument("--aborted-transaction-lower-bound-seconds", type=float)
    parser.add_argument("--prior-bulk-copy-seconds", type=float)
    arguments = parser.parse_args()
    mongo_uri = os.environ.get(arguments.mongo_uri_env)
    if not mongo_uri:
        parser.error(f"environment variable {arguments.mongo_uri_env!r} is not set")

    project_root = Path(__file__).resolve().parents[2]
    registry_path = (
        arguments.registry
        if arguments.registry.is_absolute()
        else project_root / arguments.registry
    )
    output_path = (
        arguments.output if arguments.output.is_absolute() else project_root / arguments.output
    )
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    database_path = project_root / registry["database"]["path"]
    bank_registry = json.loads(
        (project_root / "data/registered/bank_registry.json").read_text(encoding="utf-8")
    )
    category_by_code = {entity["code"]: entity["category"] for entity in bank_registry["entities"]}
    bank_codes = sorted(code for code, category in category_by_code.items() if category == "BANK")
    _, schema = load_all(project_root / "template", project_root)
    schema_by_id = {item.schema_id: item for item in schema}

    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5_000)
    try:
        client.admin.command("ping")
        database = client[registry["source"]["archive"]["header"]["database"]]
        yearly_audit = {
            **_collection_stats(database, "report_yearly"),
            **_historical_collection_audit(database.report_yearly, "sid", category_by_code),
        }
        quarterly_audit = {
            **_collection_stats(database, "report_quaterly"),
            **_historical_collection_audit(database.report_quaterly, "stock_id", category_by_code),
        }
        data_chart_stats = _collection_stats(database, "data_chart")
        bank_documents = list(
            database.data_chart.find({"stock_industry": "bank"}).sort(
                [("stock_id", 1), ("term_type", 1), ("_id", 1)]
            )
        )
    finally:
        client.close()

    registered_bank_documents = [
        document
        for document in bank_documents
        if str(document["stock_id"]).strip().upper() in bank_codes
    ]
    unexpected_bank_codes = sorted(
        {str(document["stock_id"]).strip().upper() for document in bank_documents} - set(bank_codes)
    )
    bank_document_pairs = [
        (str(document["stock_id"]).strip().upper(), str(document["term_type"]))
        for document in registered_bank_documents
    ]
    bank_document_codes = sorted({pair[0] for pair in bank_document_pairs})
    numeric_features: set[int] = set()
    ytd_features: set[int] = set()
    source_contains_1944 = False
    terms_by_type: dict[str, set[str]] = {"yearly": set(), "quaterly": set()}
    for document in registered_bank_documents:
        data = document["data"]
        numeric_features.update(int(key) for key in data if str(key).isdigit())
        ytd_features.update(
            int(key.removeprefix("YTD_"))
            for key in data
            if str(key).startswith("YTD_") and str(key).removeprefix("YTD_").isdigit()
        )
        source_contains_1944 |= "1944" in data or "YTD_1944" in data
        terms_by_type[str(document["term_type"])].update(map(str, data["NormTerm"]))
    mapped_numeric = numeric_features & set(schema_by_id)
    mapped_ytd = ytd_features & set(schema_by_id)

    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        database_row_count = connection.execute(
            "SELECT count(*) FROM weak_reference_cells"
        ).fetchone()[0]
        forbidden_row_count = connection.execute(
            "SELECT count(*) FROM weak_reference_cells WHERE can_map_pdf OR can_promote_pdf"
        ).fetchone()[0]
        duplicate_identity_count = connection.execute(
            """
            SELECT count(*) FROM (
                SELECT stock_id, source_term_type, norm_term, source_feature
                FROM weak_reference_cells
                GROUP BY ALL HAVING count(*) > 1
            )
            """
        ).fetchone()[0]
        indexed_bank_count = connection.execute(
            "SELECT count(DISTINCT stock_id) FROM weak_reference_cells"
        ).fetchone()[0]
        indexed_1944_count = connection.execute(
            "SELECT count(*) FROM weak_reference_cells WHERE report_norm_id = 1944"
        ).fetchone()[0]
        value_state_counts = {
            state: count
            for state, count in connection.execute(
                "SELECT value_state, count(*) FROM weak_reference_cells GROUP BY 1 ORDER BY 1"
            ).fetchall()
        }
    finally:
        connection.close()

    q1 = lookup_resolved_historical_reference(
        database_path,
        stock_id="VPB",
        report_norm_id=4385,
        norm_term="Q1/2026",
        include_upstream_ytd=True,
    )
    q4 = lookup_resolved_historical_reference(
        database_path,
        stock_id="VPB",
        report_norm_id=4385,
        norm_term="Q4/2025",
        include_upstream_ytd=True,
    )
    q1_by_kind = {match.series_kind: match for match in q1}
    q4_by_kind = {match.series_kind: match for match in q4}
    checks = {
        "report_yearly_has_no_registered_bank": not any(
            category_by_code[code] == "BANK"
            for code in yearly_audit["registered_financial_code_intersection"]
        ),
        "report_quaterly_has_no_registered_bank": not any(
            category_by_code[code] == "BANK"
            for code in quarterly_audit["registered_financial_code_intersection"]
        ),
        "data_chart_covers_all_registered_banks": bank_document_codes == bank_codes,
        "data_chart_has_no_unregistered_bank_codes": not unexpected_bank_codes,
        "data_chart_has_one_annual_and_quarterly_document_per_bank": (
            Counter(bank_document_pairs)
            == Counter((code, term) for code in bank_codes for term in ("yearly", "quaterly"))
        ),
        "selected_document_hash_matches_registry": (
            historical_documents_hash(registered_bank_documents)
            == registry["source"]["selected_documents_sha256"]
        ),
        "database_hash_matches_registry": (
            sha256_file(database_path) == registry["database"]["sha256"]
        ),
        "database_row_count_matches_registry": (database_row_count == registry["cells"]["count"]),
        "database_has_no_duplicate_identity": duplicate_identity_count == 0,
        "database_has_no_mapping_or_promotion_rows": forbidden_row_count == 0,
        "database_covers_27_banks": indexed_bank_count == len(bank_codes) == 27,
        "source_and_database_have_no_1944": (not source_contains_1944 and indexed_1944_count == 0),
        "mapped_numeric_ids_match_registry": (
            sorted(mapped_numeric) == registry["schema"]["mapped_raw_report_norm_ids"]
        ),
        "mapped_ytd_ids_match_registry": (
            sorted(mapped_ytd) == registry["schema"]["mapped_ytd_report_norm_ids"]
        ),
        "q1_raw_and_ytd_are_separate_equal_series": (
            q1_by_kind[RAW_SERIES].numeric_value == q1_by_kind[YTD_SERIES].numeric_value
        ),
        "q4_raw_and_ytd_are_separate_different_series": (
            q4_by_kind[RAW_SERIES].numeric_value != q4_by_kind[YTD_SERIES].numeric_value
        ),
    }
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise RuntimeError(f"historical reference evaluation failed: {failed}")

    performance_attempts = []
    if arguments.aborted_autocommit_lower_bound_seconds is not None:
        performance_attempts.append(
            {
                "method": "PYTHON_EXECUTEMANY_AUTOCOMMIT",
                "status": "INTENTIONALLY_TERMINATED_BEFORE_PUBLISH",
                "elapsed_lower_bound_seconds": arguments.aborted_autocommit_lower_bound_seconds,
            }
        )
    if arguments.aborted_transaction_lower_bound_seconds is not None:
        performance_attempts.append(
            {
                "method": "PYTHON_EXECUTEMANY_SINGLE_TRANSACTION",
                "status": "INTENTIONALLY_TERMINATED_BEFORE_PUBLISH",
                "elapsed_lower_bound_seconds": arguments.aborted_transaction_lower_bound_seconds,
            }
        )
    if arguments.prior_bulk_copy_seconds is not None:
        performance_attempts.append(
            {
                "method": registry["database"]["bulk_load_method"],
                "status": "PASS_PRIOR_BUILD",
                "write_elapsed_seconds": arguments.prior_bulk_copy_seconds,
            }
        )
    performance_attempts.append(
        {
            "method": registry["database"]["bulk_load_method"],
            "status": "PASS",
            "write_elapsed_seconds": registry["database"]["write_elapsed_seconds"],
        }
    )
    result = {
        "experiment_id": "E-0008",
        "captured_at": datetime.now(UTC).isoformat(),
        "status": "PASS_LOGIC_DEVELOPMENT_WEAK_REFERENCE",
        "hypothesis": (
            "The uploaded Mongo archive can provide post-mapping bank discrepancy evidence "
            "without participating in schema mapping or PDF confidence promotion."
        ),
        "checks": checks,
        "source_audit": {
            "report_yearly": yearly_audit,
            "report_quaterly": quarterly_audit,
            "rejected_for_bank_reference": ["report_yearly", "report_quaterly"],
            "data_chart": {
                **data_chart_stats,
                "bank_document_count": len(bank_documents),
                "selected_registered_bank_document_count": len(registered_bank_documents),
                "unexpected_bank_codes": unexpected_bank_codes,
                "bank_count": len(bank_document_codes),
                "term_type_counts": dict(Counter(pair[1] for pair in bank_document_pairs)),
                "annual_terms": sorted(terms_by_type["yearly"]),
                "quarterly_terms": sorted(terms_by_type["quaterly"]),
                "numeric_feature_count": len(numeric_features),
                "mapped_schema_id_count": len(mapped_numeric),
                "mapped_ytd_schema_id_count": len(mapped_ytd),
                "source_contains_1944": source_contains_1944,
            },
        },
        "database_audit": {
            "path": registry["database"]["path"],
            "size_bytes": registry["database"]["size_bytes"],
            "sha256": registry["database"]["sha256"],
            "row_count": database_row_count,
            "forbidden_row_count": forbidden_row_count,
            "duplicate_identity_count": duplicate_identity_count,
            "indexed_bank_count": indexed_bank_count,
            "indexed_1944_count": indexed_1944_count,
            "value_state_counts": value_state_counts,
        },
        "period_semantics_probe": {
            "stock_id": "VPB",
            "report_norm_id": 4385,
            "q1_2026": {
                kind: {"raw_value": match.raw_value, "numeric_value": match.numeric_value}
                for kind, match in q1_by_kind.items()
            },
            "q4_2025": {
                kind: {"raw_value": match.raw_value, "numeric_value": match.numeric_value}
                for kind, match in q4_by_kind.items()
            },
            "interpretation": (
                "The source keeps quarter-only and upstream YTD series separately. They are "
                "weak discrepancy evidence only and cannot supply PDF derivation operands."
            ),
        },
        "performance_attempts": performance_attempts,
        "safety_contract": registry["safety_contract"],
        "limitations": [
            "Historical scope and unit are not proven by PDF provenance.",
            "The archive can be stale, transformed, rounded, or based on a different filing revision.",
            "NaN is preserved as NAN and never converted to zero.",
            "Only a previously resolved ReportNormID may be queried.",
            "No historical row may map, overwrite, or promote a PDF observation.",
        ],
        "artifacts": {
            "archive_sha256": registry["source"]["archive"]["sha256"],
            "registry_path": registry_path.relative_to(project_root).as_posix(),
            "registry_sha256": sha256_file(registry_path),
            "database_sha256": sha256_file(database_path),
            "policy_sha256": sha256_file(
                project_root / "config/reference/historical-weak-reference.yaml"
            ),
            "implementation_sha256": sha256_file(
                project_root / "src/bctc_ai/reference/historical.py"
            ),
            "builder_sha256": sha256_file(
                project_root / "scripts/mongodb/build_historical_weak_reference.py"
            ),
            "evaluation_sha256": sha256_file(Path(__file__)),
        },
        "software": {
            "duckdb": importlib.metadata.version("duckdb"),
            "pymongo": importlib.metadata.version("pymongo"),
        },
        "mongo_uri_persisted": False,
    }
    atomic_write_json(output_path, result)
    print(f"HISTORICAL_REFERENCE_EVALUATION={output_path}")
    print(f"HISTORICAL_REFERENCE_EVALUATION_STATUS={result['status']}")


if __name__ == "__main__":
    main()
