# Statement-location runbook

## Purpose and boundary

This runner finds the ordered CDKT/KQKD/LCTT block, the first TM boundary, the
off-balance exclusions, and PDF cash-flow method evidence. It does not map rows,
choose the unresolved LCTT workbook branch, approve OCR values, or measure
production accuracy.

## Software and configuration

This feature adds no operating-system package, Python distribution, model, or
weight. It uses the control-plane versions already frozen by `uv.lock`, chiefly
Python 3.11, PyYAML, and RapidFuzz. OCR input is the existing pinned PP-OCRv6
batch artifact. Rebuild the control plane and GPU/OCR runtime from
`SOFTWARE_INVENTORY.md`, `SERVER_REBUILD.md`, and `BATCH_OCR_RUNBOOK.md`.

Versioned inputs:

- `config/document_phase/statement-locator-v1.yaml`
- `src/bctc_ai/document_phase/statement_locator.py`
- `src/bctc_ai/document_phase/statement_evidence.py`
- `scripts/experiments/locate_statement_pages.py`

## Preconditions

1. Register and role-freeze the PDF before inspection.
2. Complete a clean preprocessing manifest and a PP-OCRv6 batch checkpoint.
3. The completed batch pages must be contiguous and extend through the first
   TM page; a full-document OCR run is unnecessary for this stage.
4. Keep the Git tree clean for formal evidence. `--allow-dirty` is only for a
   disposable development smoke and is recorded as dirty in the output.
5. Choose a new output path. The runner refuses overwrite.

The loader verifies the preprocess-manifest hash, batch identity/role/page set,
all render/run/result hashes, artifact paths, page identities, render geometry,
OCR axes, bbox bounds, and confidence bounds before classification.

## Run

```bash
.venv/bin/python scripts/experiments/locate_statement_pages.py \
  --batch-root output/calibration/<batch-directory> \
  --config config/document_phase/statement-locator-v1.yaml \
  --output output/calibration/<batch-directory>/statement-location-v1.json
```

Exit status `0` means an ordered block was accepted. Exit status `2` means
evidence was readable but the block remained unresolved. An integrity/config
failure raises an error and must not be converted into an accepted result.

## Required output checks

- `state == STATEMENT_LOCATION_COMPLETE`;
- no `errors`;
- winner/runner-up margin meets the configured threshold;
- no interstitial page was skipped;
- `mapping_eligible_pages_by_statement_type` excludes every off-balance page;
- page contracts do not continue across a scope boundary;
- direct/indirect evidence uses title competition and ordered row anchors;
- for historical E-0013 replay, `schema_branch_assignment_permitted == false` because Q-BOOT-001 was open at freeze time;
- code/config/batch paths are project-relative and hashes match.

After reproducing E-0013, use `config/mapping/lctt-v2.yaml` for current mapping.
Q-BOOT-001 was resolved on 2026-08-06: template-order block 4155→4168 is
INDIRECT and 4104→4116 is DIRECT. Never edit the v1 locator artifact/config to
retrofit this later authority.

## MBB/VCB clean calibration result (E-0013)

The unchanged locator at clean commit
`b165c6001b914d1d2ab234903c45c91f557974ed` used the first 18 pages of each
120-DPI calibration batch and found:

| Source | Eligible CDKT | Excluded off-balance | KQKD | LCTT | TM boundary | Method |
|---|---:|---:|---:|---:|---:|---|
| MBB 2025 consolidated | 10–11 | 12 | 13 | 14–15 | 16 | DIRECT |
| VCB 2025 consolidated | 8–9 | 10 | 11–12 | 13–14 | 15 | DIRECT |

Both direct-method decisions have a direct-title winner and a globally ordered
interest-income-received then interest-expense-paid sequence. Both runs had two
valid block candidates, winner/runner-up margin 2.0, no hidden interstitial
page, and no continuation crossing the off-balance boundary. The clean output
hashes are `6e8c5826…f0f70d` (MBB) and `2e9e556e…574b` (VCB). Exact paths,
identities, full hashes, replay commands, and claim boundaries are in
`../experiments/E-0013-REPLAY.md` and
`../experiments/E-0013-mbb-vcb-statement-location.json`.

E-0013 approves only the coarse calibration locator for selected-page
rerendering. It does not approve rows, schema IDs, numeric cells, or production
confidence. No ReportNormId was proposed or added.

## Routine audit

Run `.venv/bin/bctc-ai audit` after cloning or transferring artifacts. The
`statement_location` section of `BOOTSTRAP_MANIFEST.json` verifies the tracked
E-0013 code/config/runtime identities, exact page/scope/method contract, safety
and claim boundaries, and all locally present source, preprocess, batch, and
location-output hashes. `PASS_TRACKED_ARTIFACT` means only the tracked record is
available; `PASS_TRACKED_AND_LOCAL_ARTIFACTS` additionally reports counts for
verified external files. A present mismatch, unsafe path, or contract drift is
`FAIL` and disables the page contracts.

## Transfer/recovery

Transfer the registered PDFs, preprocessing directories, PP-OCRv6 batch
directories, and formal statement-location JSON outside Git. After transfer:

1. verify registered source and manifest hashes;
2. rebuild environments from the tracked locks;
3. run the batch audit/replay checks;
4. run the locator to a new path from the exact committed code/config;
5. compare the accepted page/scope/method contract and artifact SHA-256;
6. run the full regression suite before any downstream row extraction.

Never edit a batch manifest or location result to make a transferred artifact
pass. Recreate a new versioned experiment when any identity changes.
