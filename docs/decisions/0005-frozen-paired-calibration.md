# Decision 0005 — Frozen paired calibration and evidence isolation

## Status

Accepted for calibration infrastructure on 2026-08-05. It is not a production-accuracy approval.

## Context

The existing VPB experiment compared two readers on one logic-development page, but it could not establish scan OCR accuracy because the native text and VLM operated on the same searchable filing. The corpus contains a TCB 2024 filing in both searchable-vector and scan-only forms. It also contains image-heavy MBB and VCB filings suitable for later cross-bank calibration.

All four source hashes were assigned `CALIBRATION` before their contents were opened. This is weaker than an untouched holdout—calibration results may guide thresholds—but stronger than an informal cherry-picked fixture. The assignment is append-only in `data/registered/dataset_roles.jsonl`.

## Decision

1. Align paired PDF pages using a global ordered dynamic program over pixel fingerprints. Fingerprints combine normalized page ink, low-resolution layout, and row/column projections. Text, values, filenames, and fixed offsets are excluded.
2. Retain every skipped or low-confidence page explicitly. A pair enters evaluation only when visual similarity is sufficient and either the runner-up margin or adjacent monotonic sequence supports it.
3. Keep stage-specific evidence manifests. Role B cannot read the searchable Role A source, Role A output, `machine_reference.jsonl`, or a comparison file. Compare begins only after Role B output is sealed.
4. Keep historical values out of Role B mapping. A resolved-ID-only lookup is permitted during post-mapping validation solely to trigger reread/review; it cannot generate candidates, overwrite PDF values, promote confidence, or supply YTD operands.
5. Explicit target page numbers belong only to the hash-locked fixture expectation. They must never become a production bank/page routing rule.
6. Seal Role B OCR before Role A output is admitted to comparison. The seal verifies all render/output/metric hashes, the clean inference code revision, package freeze, exact model revisions and weight hashes, and the sealing implementation.
7. Propagate configured exclusions as section state. Once the visible outside-balance heading is detected, every following CDKT candidate row remains excluded even when its individual name is not on an anchor list.

## Initial evidence

- Searchable TCB: 83/83 pages with native text and no page images.
- Scan TCB: 85/85 image-only pages.
- Ordered alignment: 83 matched, 71 accepted, two scan-only pages retained.
- Target pages 9–14 paired to scan pages 10–15 with similarity 0.834–0.948 and large runner-up margins.
- The target block covers CDKT, a visible off-balance section, KQKD, and direct LCTT across two pages.
- MBB 2025 is predominantly scanned (101 image-only of 103 pages); VCB 2025 is 84/84 image-only.

## Consequences and next gate

The searchable-side rows can now seed an independent Role A machine reference while PaddleOCR-VL and later geometry OCR read only the paired scan pages for Role B. No OCR, mapping, or full-tuple accuracy claim is valid until both outputs are independently produced, sealed by hash, and compared.
