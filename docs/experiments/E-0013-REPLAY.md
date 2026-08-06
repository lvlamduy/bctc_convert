# E-0013 replay — MBB/VCB statement location

## Claim boundary

E-0013 locks the coarse page/type/scope boundary and direct-method evidence for
two frozen calibration documents. It does not measure human-gold, row/schema,
numeric-cell, full-tuple, holdout, or production accuracy. Both upstream OCR
batches are intentionally `PARTIAL`: pages 1–18 contain the complete ordered
main-statement block and first TM boundary, so later notes were not needed for
this coarse stage.

## Frozen implementation

- Locator commit: `b165c6001b914d1d2ab234903c45c91f557974ed`
- Locator config SHA-256:
  `d25ff6da2a1ce48428b4ab1ac20a31b989a27849d93326ae839507dce2ff107e`
- Runner SHA-256:
  `a274aad0b7090fd1d0a162608d4240e64a6356573ed0e24519537e0321f2bd79`
- Evidence loader SHA-256:
  `7cf1074d62c2fa133fdf2277a17df20163d0c504c191fbe9fb1901c115713954`
- Locator algorithm SHA-256:
  `8b4b283cb3eeaa3e2457e84950574cc79502143e09ae4b3b712e93e1dde8b35c`

Exact source, preprocess, batch, output, runtime, and model/config identities
are in `E-0013-mbb-vcb-statement-location.json`.

## Required local artifacts

```text
vietstock_bctc/MBB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf
vietstock_bctc/VCB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf
output/calibration/e0013-mbb-phase120/9853cc4909dc73ddea99/
output/calibration/e0013-vcb-phase120/295f397de287f84c26da/
output/calibration/e0013-mbb-phase120-role-c/
output/calibration/e0013-vcb-phase120-role-c/
```

The runner verifies the source and every manifest/render/run/result identity.
Missing or drifted artifacts must fail; do not edit a manifest after transfer.
An old absolute render path in a transferred preprocess manifest may relocate
only through the batch's project-relative path with the identical render hash
and geometry.

## Verify code and tests

```bash
git checkout b165c6001b914d1d2ab234903c45c91f557974ed
git status --porcelain
.venv/bin/ruff check src tests scripts
.venv/bin/ruff format --check \
  src/bctc_ai/document_phase/statement_locator.py \
  src/bctc_ai/document_phase/statement_evidence.py \
  scripts/experiments/locate_statement_pages.py \
  tests/unit/test_statement_locator.py \
  tests/unit/test_statement_location_evidence.py
.venv/bin/pytest -q -ra
```

Expected result at the frozen commit: 143 passed, two explicitly skipped
immutable historical replays, and no failure.

## Replay to new immutable paths

The original outputs are immutable. Use new paths when replaying:

```bash
.venv/bin/python scripts/experiments/locate_statement_pages.py \
  --batch-root output/calibration/e0013-mbb-phase120-role-c \
  --config config/document_phase/statement-locator-v1.yaml \
  --output output/calibration/e0013-mbb-phase120-role-c/statement-location-replay.json

.venv/bin/python scripts/experiments/locate_statement_pages.py \
  --batch-root output/calibration/e0013-vcb-phase120-role-c \
  --config config/document_phase/statement-locator-v1.yaml \
  --output output/calibration/e0013-vcb-phase120-role-c/statement-location-replay.json
```

Do not pass `--allow-dirty`. Each output must record the frozen commit and
`dirty=false`. The generation timestamp means a replay JSON need not have the
same whole-file hash; compare the bound input/code/config identities and result
contract.

## Expected contract

| Source | Eligible CDKT | Excluded | KQKD | LCTT | TM boundary | Method | Margin |
|---|---:|---:|---:|---:|---:|---|---:|
| MBB | 10–11 | 12 | 13 | 14–15 | 16 | DIRECT | 2.0 |
| VCB | 8–9 | 10 | 11–12 | 13–14 | 15 | DIRECT | 2.0 |

Both outputs must additionally have:

- zero interstitial pages;
- zero off-balance pages in eligible CDKT;
- no continuation link crossing into the excluded page;
- a winning direct title and a complete ordered received/paid sequence;
- an incomplete indirect sequence;
- `schema_branch_assignment_permitted=false`;
- no history, arithmetic generation, YTD derivation, schema ID, or confidence
  promotion.

## Original clean outputs

- MBB:
  `output/calibration/e0013-mbb-phase120-role-c/statement-location-clean-b165c60.json`,
  SHA-256 `6e8c5826ac8d8150d77aa29ebea9362a56accf51b49f1760b4736afc87f0f70d`.
- VCB:
  `output/calibration/e0013-vcb-phase120-role-c/statement-location-clean-b165c60.json`,
  SHA-256 `2e9e556eef8cbe91603a8c39d62fafff33b11b5b21730835cd457f7ee644574b`.

The next experiment must rerender only the eligible statement pages plus the
off-balance exclusion boundary at 200 DPI and apply the frozen Role B/Role C
row logic. It must not treat E-0013 page location as row-level ground truth.
