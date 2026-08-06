# Targeted reread v1

## Purpose and authority boundary

This stage converts explicit structural/cell failures into small, reproducible
high-resolution rereads. It does not search every page again and does not use a
bank name, fixed page, absolute coordinate, ReportNormId, historical value, or
accounting equation to choose a crop or a value.

The evidence flow is:

```text
E-0015 page scope + ordered reader comparison
  -> relative failure localization on sealed Role C line boxes
  -> normalized page crop
  -> direct rerender from the registered PDF at 450/600 DPI
  -> original plus quality-gated, provenance-preserving candidates
  -> independent reader outputs (later stage)
  -> canonical-row review/fusion (later stage)
```

The registered PDF remains authoritative. A 200-DPI PNG is used only to locate
the normalized region; it is never enlarged and presented as new source
detail. Every rerender checks the source PDF SHA-256 again.

## General localization algorithm

`targeted_reread.py` consumes the current page's Role B/Role C comparison and
Role C line geometry. Distances and margins are multiples of the page's median
OCR line height. The configuration contains no institution, document, page, or
absolute-coordinate exception.

Three region profiles are permitted:

| Failure shape | Region | DPI | Readers requested |
|---|---|---:|---|
| unresolved Role B table or dense structural failures | full table including period headers | 450 | PaddleOCR-VL-1.6 and PP-OCRv6 |
| isolated collapsed/missing/wrapped/invalid row | affected row band plus one neighboring logical row on each side | 450 | PaddleOCR-VL-1.6 and PP-OCRv6 |
| isolated numeric disagreement | label-to-period cell strip | 600 | PP-OCRv6 |

Nearby failures are grouped by relative line-height distance, with a bounded
number of trigger units per band. When Role C has no row for a Role B-only
candidate, the crop is bracketed by the nearest observed rows in document
order. If neither neighbor exists, localization fails closed instead of
guessing a y-coordinate.

A full-table crop includes the visible period headers and may therefore propose
a new header/value binding. A row-band or numeric strip does not include those
headers, so it cannot independently change the existing period binding.

## Scope, long rows, and page continuation

The upstream ordered statement locator is checked first. A page marked
off-balance or otherwise mapping-ineligible receives no crop even if a label
resembles CDKT. This preserves the exclusion for guarantees, foreign-exchange
commitments, and other off-balance indicators.

Long labels that wrap over several visual lines retain all Role C line IDs and
receive neighboring-row context. This permits a later canonical-row assembler
to distinguish one wrapped item from two adjacent accounting items.

A targeted region never crosses a PDF page. A table broken across pages is
represented by separate page crops connected through the already verified
continuation graph. Automatic cross-page row merging remains disabled until
both sides carry explicit incomplete-row geometry; values cannot be shifted
across the boundary to make the table fit.

## Image-quality candidates and geometry provenance

Each crop is assessed before OCR for blur, contrast, uneven background, noise,
compression, skew, perspective, and dark/reversed header regions. The original
RGB crop is always retained. Grayscale is retained as a neutral candidate;
other candidates are generated only when their corresponding quality signal is
present:

- contrast normalization, CLAHE, and adaptive threshold for low contrast or
  uneven background;
- non-local-means denoising for noise or compression;
- light unsharp masking for blur;
- deskew and perspective correction only after geometric detection; and
- local CLAHE/gamma/inversion only inside detected dark header tiles.

Photometric candidates keep identity geometry. Deskew/perspective candidates
store a 3×3 transform back to the original crop, plus composed transforms back
to PDF points and the sealed baseline render. This makes every future word/cell
box traceable even when candidate dimensions change. The source crop and all
candidate hashes are immutable; no transform overwrites its input.

Candidate creation is not candidate selection. V1 leaves every candidate at
`PENDING_OCR_EVIDENCE`. It does not let history, schema, arithmetic, reader
agreement, or OCR confidence automatically replace a value or promote
confidence. A later selection rule must separately measure exact digit/sign,
Vietnamese label quality, box stability, table-line preservation, and
independent-reader behavior, and must retain disagreement.

## E-0016 input contract

The frozen MBB/VCB E-0015 artifact produces 13 page decisions:

- 6 pages planned and 5 pages with no reread trigger;
- 2 off-balance pages skipped before crop creation;
- 8 regions: 2 full tables, 5 row bands, and 1 numeric strip;
- 7 regions at 450 DPI and 1 at 600 DPI; and
- zero unsupported escalation, schema mutation, ReportNormId proposal, value
  replacement, or confidence promotion.

The observed full-table targets are the dense MBB LCTT page and the truncated
VCB CDKT continuation page. These page identities are frozen calibration data,
not production routing rules. The unchanged algorithm must discover future
targets from scope, failure type, order, and relative geometry.

## Files, tests, and rebuild

- Policy: `config/preprocessing/targeted-reread-v1.yaml`.
- Planner: `src/bctc_ai/preprocessing/targeted_reread.py`.
- PDF rerender/variants: `src/bctc_ai/preprocessing/targeted_render.py`.
- Evidence-chain builder: `src/bctc_ai/preprocessing/targeted_run.py`.
- Frozen calibration contract:
  `config/experiments/e0016-mbb-vcb-targeted-reread.yaml`.
- CLI:
  `scripts/experiments/build_e0016_targeted_reread_inputs.py`.

Unit tests cover dense-table collapse, local numeric grouping, Role B-only
order-gap localization, mapping-ineligible exclusion, unknown escalation,
out-of-axis line IDs, source-PDF rerendering, inverse deskew geometry, overwrite
refusal, dirty-Git refusal, and upstream hash tampering. E-0016 must be built
from a clean commit into a new output directory; its formal tracked manifest
will bind all algorithms, configs, upstream evidence, source PDFs, baseline
renders, OCR results, and generated crop manifests.

The follow-on original-crop evidence sealer is deliberately a separate gate.
It traverses the input manifest rather than a bank/page list, verifies the full
E-0015→source/seal/baseline→targeted-render chain, and requires exactly the
readers requested by each region. It rejects extra reader outputs, variant
outputs, missing metrics, dirty PP-OCRv6 inference, input/result hash drift,
implicit geometry preprocessing, runtime/model/config drift, and overwrite.
Only the `original` image is read in this phase as a neutral baseline; that is
recorded as `NO_VARIANT_SELECTED_BASELINE_EVIDENCE_ONLY`, not as a decision that
the original is best.

Full-table regions may reuse the frozen Role B/Role C parsers and order/label
comparison to measure structural recovery. Headerless row bands and numeric
strips are not allowed to infer period axes. A parser failure, unresolved table,
multi-number cell, or reader row-count disagreement is retained in the evidence
artifact; successful process execution does not convert it into a successful
row/value extraction. Conditional cross-reader equality remains explicitly
different from human-gold accuracy.

This stage adds no package, model, weight, driver, or operating-system setting.
It reuses the control-plane PyMuPDF/OpenCV/NumPy/PyYAML lock and the existing
pinned PaddleOCR-VL-1.6 and PP-OCRv6 model runtime for subsequent reads.
