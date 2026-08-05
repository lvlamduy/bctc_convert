# PP-OCRv6 batch and checkpoint runbook

## Purpose and approval boundary

`scripts/models/run_ppocrv6_word_boxes_batch.sh` runs the already pinned
PP-OCRv6 detector/recognizer over many preprocessed pages while loading both
models only once per process. Each page is published atomically, followed by an
atomic batch checkpoint. A stopped process can therefore resume without
repeating verified pages.

This mechanism produces independent geometry/value proposals only. Batch
completion, reader agreement, confidence scores, arithmetic balance, or a
successful resume do not establish PDF truth, schema mapping, or production
accuracy. Role B remains the label/context proposal reader; Role C cannot
promote a value automatically.

No new Python distribution, Ubuntu package, driver, or model weight is needed.
The exact runtime remains the 125-package `.gpu-venv` and the two PP-OCRv6
revisions recorded in `config/models/gpu-runtime.toml` and
`config/models/gpu-requirements.freeze.txt`.

## Required input contract

Pass the top-level `manifest.json` produced by `bctc-ai preprocess`, not
`renders/manifest.json` and not a directory of loose images. Before model load,
the batch runner requires all of the following:

- top-level state is `PREPROCESSED` and upstream `code.git_dirty` is false;
- sibling `run_manifest.json` binds the exact preprocess-manifest SHA-256;
- the requested role equals both the preprocess role and the append-only entry
  in `data/registered/dataset_roles.jsonl`;
- the registered source PDF is present and has the recorded SHA-256;
- every selected render is present and has the recorded source/render hashes;
- the current inference code is clean, unless the explicit development-smoke
  exception is set;
- config, helper, batch runner, runtime manifest, installed Paddle packages,
  and both local model weights match their frozen identities.

Paths inside the repository are stored relative to the project root. If an old
manifest contains absolute render paths from another server, relocation is
accepted only when a same-named render beside the transferred manifest matches
the exact recorded hash. No basename match can bypass hash verification.

## Run and resume

Use one output directory for exactly one immutable batch identity:

```bash
export BCTC_MODEL_CACHE_DIR=/dev/shm/bctc-paddlex-e0007
export BCTC_DATASET_ROLE=CALIBRATION
export BCTC_PADDLE_CPU_THREADS=8

bash scripts/models/run_ppocrv6_word_boxes_batch.sh \
  output/calibration/RUN/DOCUMENT/manifest.json \
  output/calibration/ROLE_C_BATCH \
  10-15
```

Omit the third argument to process every page present in the preprocess
manifest. Page syntax accepts comma-separated positive pages and inclusive
ranges, for example `5-10,14,16-18`; it sorts and deduplicates them.

After interruption, use the same Git commit, input manifest, page selection,
role, thread count, config, runtime, and model weights:

```bash
BCTC_BATCH_RESUME=true \
  bash scripts/models/run_ppocrv6_word_boxes_batch.sh \
  output/calibration/RUN/DOCUMENT/manifest.json \
  output/calibration/ROLE_C_BATCH \
  10-15
```

Resume first re-hashes every recorded result and manifest. It also safely
adopts a page directory that was atomically published immediately before a
crash, but only when the page's full batch, source, render, code, config,
runtime, model, and role identity matches. Any drift stops the run; it never
silently starts a different experiment in the same directory.

For a non-evidence development smoke only, set
`BCTC_ALLOW_DIRTY_OCR_SMOKE=true`. The output records `code.dirty=true` and is
ineligible for sealing or accuracy claims.

## Parameters and resource planning

| Variable | Default | Meaning |
|---|---:|---|
| `BCTC_MODEL_CACHE_DIR` | required | verified cache containing both pinned `official_models/PP-OCRv6_*` directories |
| `BCTC_DATASET_ROLE` | required | `CALIBRATION`, `VALIDATION`, or `UNTOUCHED_HOLDOUT`; must already be frozen for the source hash |
| `BCTC_PADDLE_CPU_THREADS` | `8` | Paddle CPU threads; value is part of immutable batch identity |
| `BCTC_BATCH_RESUME` | `false` | set exactly `true` to verify and continue an existing batch |
| `BCTC_XDG_CACHE_DIR` | model-cache `xdg/` | writable non-code cache |
| `BCTC_MODEL_TMP_DIR` | model-cache `tmp/` | writable inference temporary directory |
| `BCTC_ALLOW_DIRTY_OCR_SMOKE` | `false` | development-only dirty-worktree exception |

One process loads one detector and one recognizer, then executes its pages
sequentially. Multiple documents may run in separate processes only after RAM,
CPU saturation, disk bandwidth, and output paths are checked. Never let two
processes target the same batch directory. Keep at least the rendered-page size
plus OCR JSON/checkpoint headroom; use `df -h /workspace /dev/shm` before a
large run. Generated renders/results remain outside Git.

## Output and audit fields

```text
ROLE_C_BATCH/
├── batch_manifest.json
├── ppocrv6-page-0010/
│   ├── ocr_result.json
│   └── run_manifest.json
└── ppocrv6-page-0011/
    ├── ocr_result.json
    └── run_manifest.json
```

`batch_manifest.json` records the stable batch identity, source and preprocess
manifest hashes, immutable dataset registration, selected render hashes, exact
code/config/helper/runtime/model identities, page artifact hashes, inference
sessions, page/word counts, confidence summaries, model-load time, and page
inference time. Timestamps and timings are observational; identity is derived
only from immutable inputs and settings.

The independent-geometry sealer accepts either the original single-page runner
or this batch runner. For batch output it verifies both the batch-runner hash
and the reused single-page helper hash; an unknown runner or helper drift is a
hard failure.

## Server transfer and rebuild

1. Check out the exact inference commit and rebuild `.gpu-venv` using
   `GPU_RUNTIME_RUNBOOK.md`.
2. Rebuild/verify the model cache from the recorded revisions and hashes.
3. Transfer the registered PDF and, when resuming, the complete preprocess and
   batch directories. Verify the PDF against the source registry.
4. Prefer rerunning preprocessing on the new server when output paths or the
   preprocessing implementation changed. Never edit old manifests to make them
   fit a new path.
5. Resume only if the exact batch identity passes. A newer code/config commit
   requires a new output directory and experiment identity.
6. Run the unit/full regression suites and `bctc-ai audit` before sealing or
   comparing any output.

The batch code is portable; model weights and generated data are intentionally
not stored in Git. The repository contains everything needed to reconstruct
their versions, settings, and verification procedure.

## Mechanism tests

Unit tests cover page-range normalization, old-server path relocation by exact
hash, source-role immutability, preprocess-envelope drift, render drift, exact
resume identity, full-identity orphan adoption, multi-session timing, and the
no-download wrapper contract. A real development smoke on TCB page 15 produced
50 lines and 380 word tokens and was byte-identical to the previously sealed
E-0011 OCR JSON (`91779b3e22fadc01eeca7605c71a356e577e56541363ac91ea2750645721c54b`).
That first dirty-worktree smoke was mechanism-only. E-0012 then repeated the
run from clean commit `3291f9d`, retained the same byte hash, completed a no-op
resume without another model load, and passed the batch-aware geometry sealer.
Exact commands and artifact hashes are in `docs/experiments/E-0012-REPLAY.md`.
Because page 15 was already measured in E-0011, E-0012 adds no accuracy sample.
`bctc-ai audit` re-hashes the tracked E-0012 code/config/runtime identities and
every retained local source, render, result, checkpoint, baseline, and seal; a
present-but-drifted artifact changes the mechanism status to `FAIL`.
