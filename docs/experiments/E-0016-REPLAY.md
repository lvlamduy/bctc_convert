# E-0016 replay — MBB/VCB targeted reread and original-crop evidence

## Claim boundary

E-0016 is post-failure calibration on regions selected from E-0015. It proves
that the general localization/rerender chain produced eight source-PDF crops and
that all 15 requested reads of the neutral `original` variants completed with
hash-bound inputs and outputs. It reports parser recovery and retained failures.

It does not select the original as the best image variant, map a ReportNormId,
use ReportNormId magnitude or numeric order, replace a value, use history or
arithmetic, evaluate human-gold accuracy, calibrate confidence, or approve
production use. Conditional reader agreement is not truth.

## Frozen identities

- Targeted input-generation commit:
  `d9a18d47d950d7be97e6e6d12ddae125714e5f5b` (clean).
- Targeted input manifest SHA-256:
  `9127886eef39a5f0462ff00e0096cbdf20be552402e5feddb64d99063cc3fb98`.
- Evidence-sealer commit:
  `8c2f7fbe08affce491df26113eaee10920fd459c` (clean).
- Evidence config SHA-256:
  `ae97e1187bce0113165add00bcd93bb1104c9cdcf6734c8c04298d4bd8adbf58`.
- Reader-output artifact-set SHA-256:
  `0c993e0192f3bbdf67dfa9e9a3d0f054e2bd20fa2b4b8c7fab57fc970997875d`
  over 52 files.
- Formal tracked evidence SHA-256:
  `fe9c83bc612709630183c7bf871caa5ba59406c6b6dc83c39ede54e6293a4762`.
- Runtime manifest SHA-256:
  `9141e0a4177f66f152bdb9eecbbfdbdd3add566dbabb81b43207a018c1ba18d8`.
- GPU package freeze SHA-256:
  `c0e8c43f84360a8eb0ebeff1ef5de43969bdd291eb2c7cee363c35ef2c78437b`.

The machine-readable artifact contains every algorithm/config/model revision,
crop, reader result, execution metric, source/upstream identity, and safety flag.
Large PDFs, crops, and OCR outputs remain outside Git and must be transferred
with their hashes. Timestamped manifests make a new execution byte-distinct;
never overwrite the formal run to make a replay impersonate it.

## Preconditions

1. Rebuild `.venv`, `.gpu-venv`, and all four exact model weights using the
   environment runbooks. Verify the runtime, package freeze, and model hashes.
2. Restore the E-0014/E-0015 local source, render, result, and seal chain. Replay
   E-0015 first and require its tracked SHA-256.
3. Restore the MBB and VCB source PDFs and verify their registered identities.
4. Use a new output directory. Every builder/reader/sealer refuses overwrite.
5. Before every formal input, PP-OCRv6, or sealer command, require an empty
   `git status --porcelain`.

## Rebuild the targeted inputs

The original input manifest must be transferred for exact verification. To
repeat the mechanism as a new run, check out the input-generation commit and use
a new directory:

```bash
git checkout d9a18d47d950d7be97e6e6d12ddae125714e5f5b
git status --porcelain

PYTHONPATH=src .venv/bin/python \
  scripts/experiments/build_e0016_targeted_reread_inputs.py \
  --config config/experiments/e0016-mbb-vcb-targeted-reread.yaml \
  --output-directory output/calibration/e0016-mbb-vcb-targeted-reread-replay
```

Require 2 documents, 13 page decisions, 6 planned pages, 2 skipped off-balance
pages, and 8 regions: 2 full tables, 5 row bands, and 1 numeric strip. The
builder must retain all 18 generated variants as `PENDING_OCR_EVIDENCE`, use the
registered PDFs directly at 450/600 DPI, and select nothing.

## Run PP-OCRv6 on all eight original crops

For an exact audit, use the transferred root named in the formal input manifest.
For the mechanism replay above, set `e0016_run_root` to the new directory. The
region list below is calibration-fixture data, not production routing logic.

```bash
export BCTC_E0016_MODEL_CACHE=/dev/shm/bctc-paddlex-e0007
export BCTC_DATASET_ROLE=CALIBRATION
export BCTC_PADDLE_CPU_THREADS=8
e0016_run_root=output/calibration/e0016-mbb-vcb-targeted-reread-replay

e0016_originals=(
  documents/mbb-2025-consolidated/page-0010/region-0001/original.png
  documents/mbb-2025-consolidated/page-0010/region-0002/original.png
  documents/mbb-2025-consolidated/page-0011/region-0001/original.png
  documents/mbb-2025-consolidated/page-0013/region-0001/original.png
  documents/mbb-2025-consolidated/page-0013/region-0002/original.png
  documents/mbb-2025-consolidated/page-0014/region-0001/original.png
  documents/mbb-2025-consolidated/page-0015/region-0001/original.png
  documents/vcb-2025-consolidated/page-0009/region-0001/original.png
)

for input_relative in "${e0016_originals[@]}"; do
  reader_tail=${input_relative%.png}
  BCTC_MODEL_CACHE_DIR="$BCTC_E0016_MODEL_CACHE" \
    bash scripts/models/run_ppocrv6_word_boxes.sh \
    "$e0016_run_root/$input_relative" \
    "$e0016_run_root/ocr/ppocrv6/$reader_tail"
done
```

The formal run recorded eight clean PP-OCRv6 manifests, 308 recognized lines,
and 2,241 word tokens. Only the two full-table crops contain their own period
headers and may invoke the two-axis row parser. Headerless rows/strips remain
`NOT_APPLICABLE_REGION_HAS_NO_PERIOD_HEADER`.

## Run PaddleOCR-VL on the seven structural crops

Run one GPU model process at a time. The numeric-only region is deliberately
absent from this list because its input plan requested PP-OCRv6 only.

```bash
e0016_structural_originals=(
  documents/mbb-2025-consolidated/page-0010/region-0002/original.png
  documents/mbb-2025-consolidated/page-0011/region-0001/original.png
  documents/mbb-2025-consolidated/page-0013/region-0001/original.png
  documents/mbb-2025-consolidated/page-0013/region-0002/original.png
  documents/mbb-2025-consolidated/page-0014/region-0001/original.png
  documents/mbb-2025-consolidated/page-0015/region-0001/original.png
  documents/vcb-2025-consolidated/page-0009/region-0001/original.png
)

for input_relative in "${e0016_structural_originals[@]}"; do
  reader_tail=${input_relative%.png}
  PYTHONPATH=src .venv/bin/python scripts/diagnostics/run_gpu_benchmark.py \
    --output "$e0016_run_root/metrics/paddleocr-vl/${reader_tail}.json" \
    --interval-ms 250 \
    -- env BCTC_MODEL_CACHE_DIR="$BCTC_E0016_MODEL_CACHE" \
    bash scripts/models/run_paddleocr_vl.sh \
    "$e0016_run_root/$input_relative" \
    "$e0016_run_root/ocr/paddleocr-vl/$reader_tail"
done
```

The historical PaddleOCR-VL runner did not self-record a Git commit. The formal
artifact states this limitation as `NOT_SELF_RECORDED_BY_RUNNER`; it binds the
runner, config, runtime, command, input, metrics, and every output byte but does
not retroactively invent stronger provenance. A new runner version should emit
an atomic self-contained inference manifest.

## Seal and verify the evidence

The tracked config points to the formal input/output root. A mechanism replay in
a different root needs a new config/hash and is therefore a new experiment
artifact.

```bash
git checkout 8c2f7fbe08affce491df26113eaee10920fd459c
git status --porcelain

PYTHONPATH=src .venv/bin/python \
  scripts/experiments/seal_e0016_targeted_reread_evidence.py \
  --config config/experiments/e0016-mbb-vcb-targeted-reread-evidence.yaml \
  --output output/calibration/e0016-targeted-reread-evidence-replay.json
```

`--allow-dirty` is development-smoke-only. A formal result must record
`dirty=false`. The sealer rejects missing/extra reader outputs—including reads
of non-original variants—so a future variant comparison must use a new phase and
contract.

## Expected evidence contract and retained failures

- 15/15 requested runs completed: 8 PP-OCRv6 and 7 PaddleOCR-VL.
- The input set contains 18 variants; 8 originals were evaluated as neutral
  baselines and 10 variants remain unevaluated. Selected variants: zero.
- PaddleOCR-VL exposed 6 table blocks: 5 parsed and 1 unresolved; another region
  contained no table block. It produced 62 safe rows and retained 14 invalid
  multi-number cells.
- Both full-table PP-OCRv6 reads reconstructed two axes and 54 rows total;
  PaddleOCR-VL proposed 44 rows. Both full-table regions retained reader-count
  disagreements.
- On VCB page 9, the 200-DPI VLM baseline had zero safe rows from a seven-row
  truncated grid. The targeted readers proposed 26 and 27 structural rows and
  agreed on all 48 paired observed cells. This is strong recovery evidence, not
  human-gold accuracy.
- On MBB page 14, the VLM proposal improved from 6 to 18 rows but retained 14
  invalid cells and only 18/36 exact paired observed cells. PP-OCRv6 proposed 27
  rows with zero invalid cells. Higher DPI alone therefore did not solve row
  concatenation.
- One MBB row band remained `PARTIALLY_UNRESOLVED`; another was classified as
  text/image and remained `NO_TABLE_BLOCK`.
- Schema mapping, history, arithmetic, ReportNormId ordering/addition, automatic
  value replacement, variant selection, and confidence promotion all remain
  zero/false.

Wall time, GPU load, and generated timestamps are observational. Different OCR
bytes, configs, algorithms, source hashes, page/region sets, or metrics define a
new experiment and must never overwrite E-0016.
