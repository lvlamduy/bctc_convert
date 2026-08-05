# Backup and restore runbook

## Required protection classes

1. Git remote: code, configs, contracts, migrations, tests, and small manifests. Work occurs on feature branches; `main` should be protected remotely.
2. Versioned artifact store: source PDFs, schema/template copies, renders, OCR, references, workbooks, experiments, and model manifests. Use S3/MinIO/NAS/DVC/LFS with versioning; an off-machine location is mandatory.
3. MongoDB: read-only pipeline access plus timestamped compressed `mongodump`, hash manifest, off-machine copy, and periodic test restore into an isolated database.

## Local control-plane backup

This command writes a timestamped archive outside the repository and immediately restores it into a temporary directory to verify every file hash:

```bash
bctc-ai backup --destination /absolute/backup/path
```

The local archive is an allowlisted **control-plane** backup: tracked source code, tests, configs, small registries/manifests, templates, hierarchy references, and operating Markdown. It intentionally excludes source PDFs, `.gpu-venv`, `.venv`, `.local-mongodb`, `.tools`, `.model-cache`, generated output, and model caches/weights. Those large or reconstructable assets use their own hash registries, rebuild manifests, or future versioned artifact store. A regression test asserts this boundary so installing a large runtime cannot silently inflate every routine backup.

`data/local/historical_weak_reference.duckdb` is also excluded. Its versioned registry contains archive/source/code/policy/database hashes and it is rebuilt from the allowlisted `data_chart` collection. A copied DuckDB without a passing current-host registry verification is not an accepted restore.

Use `--off-machine` only when the mounted destination is independently versioned and failure-isolated. The flag is an operator assertion and must be documented in the run record.

Re-run a verification without restoring into the workspace:

```bash
bctc-ai restore-test \
  --archive /absolute/path/archive.tar.gz \
  --manifest /absolute/path/archive.tar.gz.manifest.json
```

## Artifact-store restore acceptance

- Retrieve a version by immutable object version ID, not only its latest name.
- Verify the published SHA-256 manifest before opening artifacts.
- Restore into a new empty prefix/directory.
- Verify every object hash, record count, and run-manifest parent link.
- Open a sample PDF, OCR page, reference JSONL, and workbook.
- Replay validation/export without rerunning OCR.
- Record date, operator, source version, restore location, and result.

## MongoDB restore acceptance

- Never restore over the historical source database.
- Restore the latest dump into an isolated database name with network access restricted.
- Verify archive hash, collection counts, required indexes, sampled documents, and normalized-index rebuild.
- Drop the isolated restore only after the evidence record is retained.

## Current status

The bootstrap creates and verifies a local control-plane backup. Production status remains `FAIL` until the user supplies a versioned off-machine artifact target and that target passes a restore test.
