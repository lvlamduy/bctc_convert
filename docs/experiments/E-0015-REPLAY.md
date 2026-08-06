# E-0015 replay — MBB/VCB structural reader fusion v2

## Claim boundary

E-0015 is a post-inspection calibration comparison of two machine readers on
the sealed E-0014 pages. It measures structural coverage and conditional
cross-reader agreement. It is not human-gold row/cell accuracy, schema mapping,
an untouched holdout, confidence calibration, or production approval.

Role B proposes labels/context; Role C proposes geometry/values. Neither is
truth. Values, notes, row codes, history, schema IDs, arithmetic, and YTD data
do not affect the ordered alignment path. Agreement has confidence effect
`NONE`.

## Frozen implementation

- Clean evaluator commit:
  `94a2c7c4c4809764a59f9f8c977fcd6318e2d6ad`.
- Experiment config SHA-256:
  `12b1cc8fd4f539af363d6f8dcb5b157e50f2e3c2137de639b4727ebe44a79cb2`.
- Role B parser config SHA-256:
  `dd6779c8951fff530941e16643b52638b5abfe5d1c3f977d6d65367eb0f842f2`.
- Role C v2 config SHA-256:
  `3dc1ccb331c6601b8c23e59966feb84429f04e372c6961672949e6f9565e64ee`.
- Role C base config SHA-256:
  `5aefee12f3ab760bcd203aa647bc76a0232897f16b11fec221eed0244cbbe5da`.
- Scope policy SHA-256:
  `79e4dabdce260c96f52446421a93660042558478b78f0a11a68be99f92fe0dc9`.
- Upstream E-0014 artifact SHA-256:
  `0c174f9974388c3e41374954e0620b9ba565144d832cd963d3874bfe81a2e187`.
- Formal E-0015 result SHA-256:
  `ee49ea1595c0d6507366739046005023308529352a3457d2d925cfd10c70d35a`.

Every algorithm hash, source identity, reader-seal identity, page result hash,
grid/geometry record, and safety flag is embedded in
`E-0015-mbb-vcb-structural-fusion.json`.

## Preconditions

1. Check out the exact evaluator commit and require an empty
   `git status --porcelain`.
2. Restore/verify the two E-0014 source PDFs and four reader seals with
   `E-0014-REPLAY.md`. Every selected render and OCR result used by the seals
   must be present and hash-correct.
3. Rebuild `.venv` from `uv.lock`. E-0015 adds no package, model, weight,
   driver, system library, or runtime setting; GPU/model inference is not rerun.
4. Use a new output path. The evaluator refuses overwrite and formal execution
   from a dirty worktree.

## Exact command

```bash
git checkout 94a2c7c4c4809764a59f9f8c977fcd6318e2d6ad
git status --porcelain

PYTHONPATH=src .venv/bin/python \
  scripts/experiments/compare_e0015_structural_fusion.py \
  --config config/experiments/e0015-mbb-vcb-structural-fusion.yaml \
  --output output/calibration/e0015-mbb-vcb-structural-fusion-replay.json
```

`--allow-dirty` is development-smoke-only. It records a non-formal status and
must never replace the tracked result.

## Expected mechanism contract

- 2 calibration documents, 13 pages, and 14 Role B table blocks.
- 12 parsed Role B bodies, one VCB page-10 header-only block whose roles are
  consumed by its immediately following body, and one deliberately unresolved
  VCB page-9 block.
- 13/13 Role C pages with exactly two period axes; seven expose a separate
  leading index band.
- 288 Role C rows versus 244 safe Role B rows.
- Alignment actions: 235 `MATCH`, 2 `MERGE_CANDIDATE`, 3
  `MERGE_REFERENCE`, 1 `MISSING_CANDIDATE`, and 46 `EXTRA_CANDIDATE`.
- 454 paired observed cells, 432 exact; conditional cross-reader agreement
  0.95154185. This is not an accuracy rate.
- Role B financial-row structural coverage 0.99565217; Role C coverage
  0.83636364. The lower Role C-side coverage is dominated by Role B truncation
  on VCB page 9 and MBB page 14.
- 94 note comparisons/86 exact; 104 row-code comparisons/97 exact.
- Source-exact labels 7/240 and semantic-key exact labels 50/240. Role C remains
  unsuitable as a label authority even when its cells agree.
- Role B contains eight invalid serialized cells; Role C contains zero invalid
  cells, ten pixel-backed dash cells, and three quarantined numeric margin
  lines.
- Both off-balance pages produce zero mapping-eligible alignment units.
- All five table-continuation edges are accepted, but page boundaries are hard
  alignment separators and automatic cross-page row merge remains false.
- Zero schema mapping, ReportNormId addition, Q-BOOT-001 branch assignment,
  history lookup, arithmetic generation, YTD derivation, or confidence
  promotion.

Wall time is not an acceptance identity. Any different source/seal/result,
config, code hash, page contract, or metric is a new experiment and must not
overwrite E-0015.

## Retained failures and next gate

- VCB page 9 stays fail-closed: Role B's comparative header is corrupted and
  the body is truncated, while Role C retains 25 rows.
- MBB page 14 has six Role B rows versus 27 Role C rows and eight invalid Role B
  cells caused by serialized row concatenation.
- MBB pages 10–11 expose three Role B two-row collapses against Role C geometry;
  MBB page 13 has one row missing on each reader plus a collapse.
- Exact label agreement remains very low because PP-OCRv6 word recognition is
  intentionally the geometry/value reader.

The next gate is targeted region rereading and canonical logical-row fusion for
these explicit escalations, followed by schema-order/parent-child mapping on a
separate version. No failure may be repaired from history or arithmetic.

