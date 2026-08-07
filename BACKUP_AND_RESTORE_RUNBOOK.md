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

## S3 immutable snapshot

The authorized off-machine target is `s3://test-s3-duylv/bctc-ai/`. Its exact
policy is `config/backup/s3-v1.toml`. The VPS uses AWS CLI profile
`bctc-backup`; credentials remain in the host credential store and must never be
written to Git, a manifest, or command output. The verified bucket is in
`us-east-1`, has default `AES256` encryption, and blocks all public access.

Bucket versioning was approved and enabled on 2026-08-06. Every data object also
uses a content-addressed key:

```text
bctc-ai/objects/sha256/<first-two-hex>/<full-sha256>
```

Every PUT supplies the base64 SHA-256 checksum, `AES256`, expected bucket owner,
and `If-None-Match: *`. An existing object is reused only after its length,
SHA-256 metadata, S3 checksum, and encryption all match. There is no delete API
or overwrite mode in the snapshot implementation. A timestamped snapshot
manifest is written last; the restore/run record is then stored under another
unique content-derived name.

The full initial inventory contains:

- all 2,567 hash-registered PDFs and the small acquisition metadata alongside
  them;
- all files below `output/`, including calibration renders and OCR evidence;
- `financial_20_02_2022.gz`, verified against its tracked dump registry;
- the accepted local historical DuckDB, verified against its registry;
- a newly restored-and-verified control-plane archive; and
- a verified `git bundle --all` so repository history is recoverable without the
  normal Git remote.

Virtual environments, downloaded model weights, MongoDB data files, and local
tool binaries are excluded because their exact rebuild versions/scripts/hashes
are tracked. They must be reconstructed; they are not silently treated as
backed up.

Run only from a clean committed worktree:

```bash
.venv/bin/bctc-ai s3-backup \
  --config config/backup/s3-v1.toml \
  --staging /workspace/bctc-ai-backups/s3 \
  --restore-temp-root /dev/shm
```

The default restore gate independently downloads the published manifest, HEAD
verifies every unique object, downloads at least one object from every asset
class plus every control/Git/Mongo/DuckDB singleton, opens a sample PDF,
restores every control-plane file, and verifies the Git bundle. The temporary
restore is removed afterward. `--full-content-restore` additionally downloads
and hashes every unique object sequentially without retaining the whole corpus
on local disk.

The production gate additionally requires a full sequential content restore;
the initial operational run therefore uses `--full-content-restore`. Object
Lock is not enabled and must remain disabled unless separately approved.

## Safe local offload and hydration

After a passing S3 snapshot, first preview the exact deletion plan:

```bash
.venv/bin/bctc-ai s3-offload \
  --config config/backup/s3-v1.toml \
  --manifest /absolute/staging/run/snapshot-manifest.json \
  --run-record /absolute/staging/run/s3-backup-run.json \
  --asset-class source_pdf \
  --asset-class mongodb_dump
```

Only after checking the planned file count and bytes, repeat with `--apply`.
The command accepts only `source_pdf` and `mongodb_dump`; it never deletes a
directory, follows no glob, and cannot target `output`, environments, tools, or
the DuckDB. Before deletion it downloads and byte-compares the remote manifest,
rehashes every local target, and HEAD-verifies every remote object. It then
checks inode/size/mtime immediately before each exact `unlink`, fsyncs a JSONL
journal after each removal, writes a final record, and uploads that record to an
immutable S3 key. If interrupted, the journal is the recovery authority.

Restore one exact file later without overwriting any conflicting local file:

```bash
.venv/bin/bctc-ai s3-hydrate \
  --config config/backup/s3-v1.toml \
  --manifest-key '<recorded-manifest-key>' \
  --manifest-sha256 '<recorded-manifest-sha256>' \
  --logical-path 'vietstock_bctc/ACB/2026/<exact-file>.pdf'
```

Use `--asset-class source_pdf` only when the entire corpus is intentionally
needed. Hydration downloads to a temporary sibling, verifies SHA-256 and size,
then installs it by a no-overwrite hard link. An existing matching file is
reused; an existing mismatched file is a hard failure.

## Codex-session backup

Codex session history is protected independently from both Git and the project
snapshot. The backup command reads only `~/.codex/sessions/`; files merely
adjacent to that directory, including `~/.codex/auth*`, AWS credentials, SSH
material, Git credentials and `.env` files, are outside its collection root.
Symlinks and special files fail closed.

```bash
PYTHONPATH=src .venv/bin/python scripts/backup/backup_codex_sessions.py
```

The script stages a stable copy of every regular session file, records its
relative path, SHA-256, byte size, mode and nanosecond modification time, and
scans both UTF-8 paths and file bytes for known credential formats. Version 2
builds the archive only from that exact scanned inventory, then independently
rescans and restores it locally **before** the first AWS preflight or PUT. A
detector match fails closed without printing the matched value or path; there
is no default redaction or bypass. It creates a dedicated archive under:

```text
s3://test-s3-duylv/codex-sessions/<host>/<UTC timestamp>-<archive hash>/
```

Both archive and manifest are written with SHA-256 checksums, `AES256`, the
expected bucket owner and `If-None-Match: *`. The manifest is uploaded last.
The command then downloads both objects into a new temporary directory,
verifies their hashes, safely extracts only the `sessions/` tree, reapplies
recorded modes/timestamps, and verifies the complete restored inventory. A PUT
response alone is not a successful backup; both the pre-upload local gate and
`"restore_verified": true` after download are required. Clean legacy V1
archives can be restored only after exact-inventory validation and a current V2
rescan; their historical manifest scan claims are not trusted.

Security status on 2026-08-07: the three historical V1 session-archive
versions predate this content gate and contain a GitHub credential that was
entered in a captured conversation. They are integrity-restorable but
**security-quarantined**, not accepted backups. Do not create another session
backup until that credential has been revoked and the source sessions pass the
V2 scan. Removing the contaminated immutable S3 versions is a destructive
operation and remains pending explicit user approval.

Run this command after important project checkpoints, before environment or
host changes, and before reboot/shutdown/migration. A scheduler may invoke the
same command periodically. This VPS currently has neither a running systemd
manager nor `crontab`, so no misleading local timer is installed; the command
is the portable scheduling target for the host/orchestrator.

## MongoDB restore acceptance

- Never restore over the historical source database.
- Restore the latest dump into an isolated database name with network access restricted.
- Verify archive hash, collection counts, required indexes, sampled documents, and normalized-index rebuild.
- Drop the isolated restore only after the evidence record is retained.

## Current status

Snapshot `20260806T050030130746Z-4a469fab2334` uploaded 4,192 unique objects and
published manifest SHA-256
`74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b`.
Its run record verifies all 4,192 catalog objects, a full sequential content
restore, the control plane, Git bundle and a sample PDF; the subsequent guarded
offload removed 2,567 verified PDFs and the MongoDB dump from local disk.
Versioning, default AES-256 encryption and public-access blocking remain active.

Recovery on 2026-08-07 also found that the later E-0027 batch manifest SHA-256
`0d94762ba4a0d383793fe93a56e48fa7b79d6a3f7faaf62e9dcf40935b8c2889`,
referenced by Git checkpoints E-0028 through E-0034, was created after that
snapshot and was never enrolled as an S3 content object. Therefore the snapshot
itself remains verified, but it does not prove recoverability of every artifact
referenced by the newer Git tip. This gap must be resolved with a transparent
reproduction seal; the historical hash must not be fabricated.

The first dedicated Codex-session backups were uploaded and fully
restore-tested on 2026-08-07, but the later credential audit quarantined all
three historical versions as described above. No host scheduler is available
in the current container, and the command remains disabled operationally until
its source tree passes the V2 scan.

## Bounded post-offload artifact snapshots

After the source corpus has been safely offloaded, a new full snapshot must not
force hydration of all 2,567 PDFs merely to protect a bounded experiment. Back
up exact generated-output paths as a restore-tested child of the last passing
full snapshot:

```bash
PYTHONPATH=src .venv/bin/python scripts/backup/backup_project_artifacts.py \
  --label '<bounded-run-label>' \
  --path 'output/<exact-run-directory>' \
  --parent-manifest-key \
    'bctc-ai/snapshots/20260806T050030130746Z-4a469fab2334/manifest-74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b.json' \
  --parent-manifest-sha256 \
    '74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b' \
  --parent-run-record-key \
    'bctc-ai/runs/20260806T050030130746Z-4a469fab2334/run-24eb066b51443066dfd14538ef7aeb21e9b700cc6ce995c49e56ff23b6701b04.json' \
  --parent-run-record-sha256 \
    '24eb066b51443066dfd14538ef7aeb21e9b700cc6ce995c49e56ff23b6701b04'
```

The command accepts only existing paths below `output/`, refuses symlinks and
special files, requires a clean Git commit, and verifies that the supplied
parent run record binds a production-`PASS` full-content restore. It hashes and
uploads every selected file to the standard content-addressed object store,
publishes an immutable child manifest, downloads and verifies every unique
incremental object, then publishes a passing run record. It never deletes or
overwrites an object and does not weaken the parent snapshot.

The child manifest retains normal `files` records and can be supplied directly
to `s3-hydrate` for exact no-overwrite restoration of any enrolled logical
path. Restore the parent full snapshot/control plane separately when rebuilding
the entire project.
