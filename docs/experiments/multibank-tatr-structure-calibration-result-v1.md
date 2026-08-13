# Multi-bank TATR structure calibration result v1

Date: 2026-08-13

## Decision

Do not promote TATR-v1.1-All to production table/cell authority. Retain it as a
structure-only shadow challenger on tightly bounded table crops. The production
stack remains:

1. VietOCR 0.3.13 VGG Transformer for Vietnamese semantic text;
2. PP-OCRv6 for authenticated source locations, dates, numbers, signs and
   dashes, with its Vietnamese transcript excluded from semantic identity;
3. deterministic source geometry for the current table/row/value-lane
   baseline;
4. TATR proposals only for explicitly triggered unresolved structural regions.

PP-DocLayoutV3 and PaddleOCR-VL-1.6 remain excluded because the sealed local
experiments show cell-coordinate/ownership drift, row collapse, shifted values
and truncation. IBM TableFormer remains deferred rather than adding a second
competing topology.

## Frozen evaluation

- Model: official TATR-v1.1-All checkpoint, 115,437,156 bytes, SHA-256
  `9df416575a3a36ebd0129342d4f597f14d6e5170268f3d52d28584ab4466a501`.
- Panel: 7 tight table crops from 5 banks, comprising 5 positive family tables
  and 2 hard controls.
- Gold: 6 TATR structure classes, 139 authenticated source-value anchors, and
  explicit unscored/ignored source cases.
- Panel commit: `8894bbc`.
- Gold commit: `44cc471`.
- Crop manifest SHA-256:
  `cf6ef2007533c38885d66485c659d43106e31fa416750bf42b3670773aad17b7`.
- Opaque model request SHA-256:
  `2369f53eadb71793b5a007c8deaf3fd0538f212e286325714cf89cce429728aa`.
- Frozen gold SHA-256:
  `7b7620593a6252d376c56c4c1f1554520edd2bee5af5646e8d87135771456fe5`.
- Full score SHA-256:
  `3b14b36dee8a07b0918019e3c7c091f651e2e9b6870669c80258529521ea4d85`.
- Status: `SCORED_NO_THRESHOLD_SELECTED`.

The request was reference-blind and contained opaque crop identities and pixels
only. It contained no Vietnamese OCR transcript, bank, family, page or expected
structure. Truth was opened only after all seven result/run pairs authenticated.

## Results

The score threshold was swept over the predeclared values
`[0.05, 0.30, 0.50, 0.70, 0.90]`; no threshold was selected after seeing the
expected row counts.

| Score threshold | IoU | Precision | Recall | F1 | Exact topology | Positive exact topology |
|---:|---:|---:|---:|---:|---:|---:|
| 0.05 / 0.30 / 0.50 | 0.50 | 0.8205 | 0.8649 | 0.8421 | 1/7 | 1/5 |
| 0.05 / 0.30 / 0.50 | 0.75 | 0.7179 | 0.7568 | 0.7368 | 0/7 | 0/5 |
| 0.70 | 0.50 | 0.8868 | 0.8468 | 0.8664 | 0/7 | 0/5 |
| 0.70 | 0.75 | 0.7736 | 0.7387 | 0.7558 | 0/7 | 0/5 |
| 0.90 | 0.50 | 0.9175 | 0.8018 | 0.8558 | 0/7 | 0/5 |
| 0.90 | 0.75 | 0.8144 | 0.7117 | 0.7596 | 0/7 | 0/5 |

Only the SHB loan-maturity table achieved exact topology, at score thresholds
up to 0.50 and IoU 0.50. No sample achieved exact topology at IoU 0.75.

Table-region and column detection were strong on this panel: both classes were
7/7 and 27/27 respectively at both IoU thresholds throughout the sweep. The
material failures were row boundaries, projected-row headers and spanning
cells. This distinction is why TATR may remain useful as a bounded proposal
source but cannot own canonical cell coordinates.

At every score threshold, 5/7 samples passed the scoped source-anchored numeric
lane assignment check. This is not full-cell coverage: the panel contains 214
logical value slots, of which 139 have authenticated source-line anchors, 2 are
visible dash cells without an authenticated line box, and 73 are otherwise
unanchored for this metric. The score makes no full-cell-coverage claim.

## Runtime

- 7/7 runs completed with 125 queries each.
- Total inference-only wall time: 1.5454 seconds.
- Mean: 0.2208 seconds per table crop.
- Maximum: 0.2487 seconds.
- Maximum allocated GPU memory: 167.3 MiB.
- Maximum reserved GPU memory: 200 MiB.

Runtime is not the blocker; coordinate/topology exactness is.

## Promotion boundary

Automatic promotion is false and the eligible-threshold set is empty. This
calibration has no independently authenticated production geometry baseline,
untouched holdout, downstream graph-gain receipt or predeclared runtime budget.
Before TATR can be promoted, it must demonstrate exact downstream topology gain
on at least three banks, zero hard-control false merges, no increase in
unresolved cases, and no number/date ownership regression on a separate frozen
holdout.

Until then, TATR output may diagnose or propose structure but must not replace
source coordinates, Vietnamese text, numeric values, family identity, schema
mapping or exported accounting data.
