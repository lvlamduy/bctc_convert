# Historical weak-reference runbook

## Scope and authority

The historical index is a post-mapping discrepancy aid for registered banks. The visible PDF remains authoritative. The index cannot generate mapping candidates, overwrite a PDF value, promote confidence, or supply an operand for PDF YTD-to-quarter derivation. Its unit and separate/consolidated scope are explicitly `UNKNOWN`; a mismatch may only trigger targeted rereading or review.

The machine-readable policy is `config/reference/historical-weak-reference.yaml`. Both the policy loader and DuckDB table constraints reject any attempt to enable mapping or confidence promotion. Lookup code accepts `stock_id`, an already-resolved `report_norm_id`, and source term; it has no label or PDF-value lookup argument.

## Source selection measured in E-0008

| Collection | Documents | Registered bank coverage | Decision |
|---|---:|---:|---|
| `report_yearly` | 5,723 | 0/27 | Reject for bank reference |
| `report_quaterly` | 2,581 | 0/27 | Reject for bank reference |
| `data_chart` | 1,318 total; 54 bank | 27/27, annual + quarterly | Allowlist |

The first two collections intersect the supplied financial-entity registry only at six securities/fund codes and one insurance code. They must not be used as if they described bank forms. `data_chart` contains one `yearly` and one source-spelled `quaterly` document for every registered bank. It contains 91 numeric features, of which 79 are existing supplied ReportNormIDs; the other 12 are excluded and audited. ID 1944 is absent from raw and `YTD_` keys.

## Persistent local rebuild

Install/start the pinned loopback MongoDB runtime and restore the template reference as documented in `SOFTWARE_INVENTORY.md`. On a clean local reference database, restore only the bank weak-reference collection:

```bash
bash scripts/mongodb/restore_financial_reference.sh \
  financial_20_02_2022.gz bank-weak-reference
```

The mode includes only `financial_20_02_2022.data_chart`; it does not touch an existing `financial_report_templates` collection and never restores `user` or `chat_sessions`. `mongorestore` is intentionally not run with `--drop`. Repeated restore into an already-populated collection should fail on duplicate identity instead of silently replacing data.

Build the local DuckDB artifact without placing the URI on the command line or in a manifest:

```bash
export BCTC_HISTORY_MONGO_URI=mongodb://127.0.0.1:27018
.venv/bin/bctc-ai history-index
.venv/bin/bctc-ai audit
```

Use `--replace` only for an intentional rebuild from a verified source. The builder verifies the 526,178,025-byte archive SHA-256, bank-list workbook SHA-256, schema, source-document BSON hash, series lengths, term grammar, and duplicate bank/term pairs before atomically replacing the database. It writes the URI nowhere.

## Artifacts and measured capacity

- Local database: `data/local/historical_weak_reference.duckdb`; excluded from Git and control-plane backup, reconstructable from the registered archive.
- Versioned registry: `data/registered/historical_weak_reference_registry.json`.
- Policy: `config/reference/historical-weak-reference.yaml`.
- Detailed evaluation: `docs/experiments/E-0008-mongodb-historical-reference.json`.
- Current size: 17,838,080 bytes for 112,147 cells across 27 banks.
- Current coverage: 99,619 upstream numeric-series cells and 12,528 separately marked upstream-derived YTD cells; 79 unique supplied ReportNormIDs.
- Value states: 79,455 VALUE, 26,869 ZERO, and 5,823 NAN. NAN and negative zero are preserved and never converted to ordinary zero.

The first Python row-wise writer attempts were intentionally terminated without publishing an artifact after lower bounds of 216 seconds (autocommit) and 194 seconds (single transaction). Transactional DuckDB CSV `COPY` wrote the first accepted index in 3.54 seconds and the final warm-cache rebuild in 1.84 seconds. Temporary CSV, DuckDB, and WAL files are removed on success or ordinary exceptions; the destination changes only after close, fsync, and atomic replace.

## Query contract

Application code may query only after PDF mapping has independently resolved an ID:

```python
from pathlib import Path
from bctc_ai.reference.historical import lookup_resolved_historical_reference

matches = lookup_resolved_historical_reference(
    Path("data/local/historical_weak_reference.duckdb"),
    stock_id="VPB",
    report_norm_id=4385,
    norm_term="Q4/2025",
    include_upstream_ytd=True,
)
```

Q1 raw and YTD series can be equal, while later-quarter raw and YTD series differ. E-0008 records VPB ID 4385 Q4/2025 as 16,767.175 in the upstream numeric series and 58,635.939 in the upstream YTD series. This is evidence about the upstream archive representation, not permission to derive or replace a PDF value. A PDF quarter derivation still requires two visible, compatible PDF operands and both cell provenances.

## Verification and recovery behavior

Routine `bctc-ai audit` checks database SHA-256, module/policy hashes, archive identity, row count, bank count, duplicate identity, ID 1944, and database-enforced no-map/no-promote flags. A missing local database reports `ABSENT_REBUILD_REQUIRED`; code/config drift or corruption reports `FAIL`. A prior E-0008 pass cannot override a current-host failure.

The E-0008 evaluator additionally requires an isolated diagnostic restore of `report_yearly`, `report_quaterly`, and `data_chart`; this broader restore is for source-selection evidence, not routine operation. Keep such diagnostics in a dedicated temporary MongoDB instance, stop it with the pinned `mongod --shutdown --dbpath ...` command, and remove only its explicitly created temporary root after the evaluation artifact and hashes pass.
