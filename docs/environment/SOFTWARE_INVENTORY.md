# Software and runtime inventory

This is the rebuild manifest for the development VPS. Binary archives, model weights, virtual environments, MongoDB data files, source PDFs, and generated output are intentionally excluded from Git; their exact versions, download locations, hashes, and rebuild commands belong here or in machine-readable manifests.

## Host baseline captured 2026-08-05

- Ubuntu 22.04.5 LTS, x86_64; kernel 6.6.0-hiveos.
- AMD Ryzen 9 5950X, 32 logical CPUs; approximately 125.7 GiB RAM.
- NVIDIA GeForce RTX 5070 Ti, 16,303 MiB, compute capability 12.0; driver 595.80 reports CUDA 13.2.
- The preinstalled PyTorch 2.5.1+cu124 does not contain `sm_120` kernels and failed an actual CUDA operation. It is not an approved model runtime.

## Python control-plane environment

- Python 3.11.10.
- uv 0.12.1; dependency resolution is frozen in `uv.lock`.
- Current resolved core versions: PyMuPDF 1.28.0, OpenCV headless 4.14.0.94, OpenPyXL 3.1.5, NumPy 2.4.6, DuckDB 1.5.5, PyMongo 4.17.0, RapidFuzz 3.14.5, PyYAML 6.0.3, Pillow 12.3.0.
- Test tools: Ruff 0.16.1 and pytest 9.1.1.

Rebuild:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install uv==0.12.1
.venv/bin/uv sync --frozen --extra dev
```

## S3 backup client and settings

- AWS CLI: 2.36.17, bundled Python 3.14.6, installed at `/usr/local/bin/aws`.
- Credential selector: host profile `bctc-backup`; credentials are not tracked.
- Bucket/prefix: `s3://test-s3-duylv/bctc-ai/`, region `us-east-1`.
- Bucket controls observed 2026-08-06: default `AES256` encryption, all four
  public-access-block flags enabled, and versioning `Enabled`. Object Lock is not
  configured, as required by the user's approval boundary.
- Machine-readable policy: `config/backup/s3-v1.toml`.
- Transfer implementation: Python standard library plus the existing AWS CLI;
  no Python package or Ubuntu package was added.
- Runtime settings: standard AWS retry mode, 8 attempts, 8 concurrent object
  workers, expected-owner binding, SHA-256 checksum, and `If-None-Match: *`.
- No S3 delete operation and no overwrite mode exist. The safe offload command
  can unlink only locally verified `source_pdf` and `mongodb_dump` records after
  a passing remote restore record.

On a rebuilt server, install AWS CLI v2, create a least-privilege profile named
`bctc-backup` outside the repository, then run the preflight through
`bctc-ai s3-backup`. Required permissions are bucket location/versioning/
encryption/public-access inspection plus ListBucket, HeadObject, GetObject, and
conditional PutObject within `bctc-ai/`. DeleteObject is neither required nor
used. Exact backup, restore, offload, and hydration commands are in
`BACKUP_AND_RESTORE_RUNBOOK.md`.

## Local MongoDB reference runtime

The uploaded archive reports MongoDB server 7.0.28 and Database Tools 100.14.0. For read-only development restoration, the local server is patched MongoDB 7.0.34 from the same 7.0 major line; Database Tools matches archive tool version 100.14.0.

| Component | Official archive | SHA-256 | Local directory |
|---|---|---|---|
| Database Tools 100.14.0 | `https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2204-x86_64-100.14.0.tgz` | `4104998bda784a0cb16fc2e06d9c21645516d72c4fb481c9b103f1e0a8458fc0` | `.tools/mongodb-database-tools-ubuntu2204-x86_64-100.14.0/` |
| MongoDB Community 7.0.34 | `https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2204-7.0.34.tgz` | `ca1ff8067a219b1dccb50a95305c7bba412c8a98787e4e51dbd3d2222817c8b8` | `.tools/mongodb-linux-x86_64-ubuntu2204-7.0.34/` |

Install and verify:

```bash
bash scripts/bootstrap/install_mongodb_runtime.sh
bash scripts/mongodb/start_local_reference.sh
bash scripts/mongodb/restore_financial_reference.sh financial_20_02_2022.gz templates-only
PYTHONPATH=src .venv/bin/python scripts/mongodb/audit_reference_dump.py \
  --archive financial_20_02_2022.gz \
  --mongo-uri mongodb://127.0.0.1:27018
```

The server binds only to `127.0.0.1:27018`; diagnostic data collection is disabled. Restoration is namespace-allowlisted. `user` and `chat_sessions` are out of scope and must not be restored. `.local-mongodb/` and `.tools/` are excluded from Git.

The persistent reference instance now also contains allowlisted `data_chart`: 1,318 documents total, including exactly 54 documents for all 27 registered banks (one annual and one source-spelled `quaterly` document each). The guarded DuckDB 1.5.5 index contains 112,147 cells and occupies 17,838,080 bytes; PyMongo is 4.17.0. No additional operating-system package was installed for E-0008. Rebuild, policy, query, performance, and teardown details are in `HISTORICAL_REFERENCE_RUNBOOK.md`.

## GPU model runtime

The control plane remains CPU-only and stable. The document-model environment is isolated as `.gpu-venv`; it contains 125 frozen distributions and occupies 6,383,286,857 bytes on this host. The complete freeze is `config/models/gpu-requirements.freeze.txt` (SHA-256 `c0e8c43f84360a8eb0ebeff1ef5de43969bdd291eb2c7cee363c35ef2c78437b`). Direct requirements and all artifact/model hashes are in `config/models/gpu-requirements.in` and `config/models/gpu-runtime.toml`.

Primary runtime versions:

| Component | Frozen version | Purpose |
|---|---:|---|
| PyTorch | 2.12.0+cu130 | Blackwell CUDA execution |
| TorchVision | 0.27.0+cu130 | Transformers image processors and layout model operators |
| PaddlePaddle | 3.3.0 CPU FP32 | PP-OCRv6 detection/recognition without contaminating the PyTorch CUDA closure |
| PaddleOCR | 3.7.0 | document-pipeline API/CLI |
| PaddleX | 3.7.2 | model resolution and pipeline orchestration |
| Transformers | 5.14.1 | common PyTorch inference engine |
| OpenCV contrib | 4.10.0.84 | PaddleOCR image dependency |
| NumPy | 2.3.5 | model/post-process arrays |
| python-docx | 1.2.0 | completion of the CLI `save_all` export path |

Ubuntu 22.04 additionally needs `libgl1` and `libglib2.0-0`. The observed versions are `1.4.0-1` and `2.72.4-0ubuntu2.9`; the exact dependency closure added on this VPS is recorded in `config/system/ubuntu-22.04-gpu-apt-observed.tsv`. The rebuild script installs current security-compatible packages from the configured Ubuntu 22.04 repositories rather than forcing an obsolete patch version.

The approved runtime smoke performs imports, a real PyTorch CUDA matrix multiplication, and a separate Paddle CPU matrix multiplication. It verifies `sm_120`, capability 12.0, package versions, CUDA 13.0, and the declared Paddle device `cpu`. Both kernels and Paddle's official `paddle.utils.run_check()` passed on this host. `uv pip check` also passed for all 125 distributions. This approves the runtime mechanism, not model accuracy.

Every `bctc-ai audit` now re-runs that kernel/import smoke, `uv pip check`, the tracked-freeze SHA-256 check, and an exact installed-versus-tracked package comparison. The machine-readable result is stored at `environment.gpu_model_runtime` in `BOOTSTRAP_MANIFEST.json`. A missing environment, dependency drift, freeze drift, import failure, wrong architecture, or failed CUDA operation changes local acceptance to `ABSENT` or `FAIL`; the recorded historical E-0007 result cannot override a current-host failure.

### Pinned document models

| Model | Revision | Weight bytes | Weight SHA-256 | License |
|---|---|---:|---|---|
| PaddleOCR-VL-1.6 | `cdc88f5feff0e4079e75863205053a68358e52f7` | 1,917,255,968 | `85a479d506a11e724e7285d395c551be69f41dbc16b6342d3cacfb189aed71db` | Apache-2.0 |
| PP-DocLayoutV3 safetensors | `97d101e6db2642e162a1d05392d1b0231c91033e` | 133,270,468 | `5ea422c6cc5fe759a47e1357c35639b58173508e025a3131cbe4b6ac59e2b85e` | Apache-2.0 |
| PP-OCRv6 medium detection | `8e0f56fb2ef86b461d99cfc7ac5c137738985f61` | 61,960,476 | `85218d2e3d98f5a21c58b4220627be923a97aee5db3cc71f39536ab31ac53960` | Apache-2.0 |
| PP-OCRv6 medium recognition | `e5a92bcbc5cc1b494628e458d267778f0704fd7c` | 76,465,087 | `1b01c79a914587933f615569e75de54f2e638ebb5d3f3b3c1b38c24ede8c7319` | Apache-2.0 |

`scripts/bootstrap/download_paddleocr_vl_models.py` downloads those four exact Hugging Face revisions and refuses a weight size/hash mismatch. Model weights and caches remain outside Git. With all four models present, the verified cache occupies 2,213,856,016 bytes. `PADDLE_PDX_CACHE_HOME`, `HF_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` may be routed to `/dev/shm`; that filesystem is suitable for cache but not for a virtual environment because this VPS mounts it `noexec`.

PP-OCRv6 requires the Paddle inference backend. Paddle's [official 3.3 installation guide](https://www.paddlepaddle.org.cn/documentation/docs/zh/install/pip/linux-pip_en.html) publishes both CPU and CUDA 13.0 wheels, and its [hardware table](https://www.paddlepaddle.org.cn/documentation/docs/install/Tables_en.html/) lists CUDA 12.9/13.0 for Blackwell `sm_120`. The CUDA wheel's exact cuDNN, cuBLAS, runtime, and NCCL dependencies conflict with the newer exact versions required by PyTorch 2.12 in this environment. E-0011 therefore uses the official PaddlePaddle 3.3.0 CPU wheel and FP32 inference; this preserves the pinned PP-OCRv6 graph/weights while isolating the dependency closures, at the cost of speed rather than a different model. The CPython 3.11 wheel is 193,703,893 bytes with SHA-256 `a4f2e0595e827c179b4fff4278fb41a24f4abe5927ffd5efb1ace26a916145f2`. `scripts/bootstrap/download_paddle_runtime_wheel.py` verifies it before installation; `create_gpu_runtime.sh` then installs only that local wheel with `--no-index --no-deps` and installs its exact missing dependencies from the tracked freeze.

`scripts/models/run_ppocrv6_word_boxes.sh` invokes a JSON-only Python runner. It verifies the two OCR weight hashes, refuses dirty evidence runs and output replacement, disables MKLDNN plus implicit geometric transforms, blocks process network connections, and atomically records line/word boxes, confidence, runtime/model/config/code hashes, and dataset role. The generic PaddleOCR CLI is not used because its visualization export attempted to download an unpinned font after successful OCR.

`scripts/models/run_ppocrv6_word_boxes_batch.sh` adds no dependency or model.
It reuses the same JSON-only helper and frozen CPU-FP32 runtime, loads the two
models once per process, atomically checkpoints each page, and permits resume
only under an identical source/render/role/code/config/runtime/model identity.
Its settings, output contract, and migration procedure are versioned in
`BATCH_OCR_RUNBOOK.md`.

The pinned full pipeline uses `config/models/paddleocr-vl-1.6-transformers.yaml`: PP-DocLayoutV3 runs FP32, PaddleOCR-VL-1.6 runs BF16, remote code is disabled, and both use the Transformers engine. The split precision is required because PP-DocLayoutV3's Transformers post-process cannot convert a BF16 tensor directly to NumPy in the tested stack.

E-0007 passed a complete 200-DPI VPB KQKD-page inference in 19.52 seconds with peak total GPU memory 3,239 MiB (3,204 MiB over baseline). Cross-reader evaluation recovered 25 logical rows, 50/50 exact value/state cells, and 12/12 exact note references. It also exposed two diacritic-sensitive label errors and one wrapped row split, so the model remains a logic-development candidate and cannot establish truth alone. See `docs/experiments/E-0007-paddleocr-vl-runtime.json`.

E-0010 reused this exact frozen runtime and model cache; no Python distribution, Ubuntu package, driver, or model weight was added. Six TCB scan pages (10–15) were rendered at 200 DPI after the quality gate classified each page `CLEAN`, then processed sequentially in 101.791746 seconds. Peak observed GPU memory was 3,243 MiB. Role B used inference commit `5e4cb033a70735deff3dc136330d078e457e0748`; its sealed artifact-set SHA-256 is `350ce77034a2adf1775b7117d1785588d17b905f5819fcc9e564f486a83b75d9`. The exact staged replay, including the clean Git commits for preprocessing, sealing, Role A, and comparison, is documented in `docs/experiments/E-0010-REPLAY.md`.

E-0011 added no software, system package, driver, or model weight beyond the inventory above. Role C ran the pinned PP-OCRv6 detector/recognizer sequentially on the same six sealed 200-DPI renders using Paddle CPU FP32. It produced 586 line boxes and 4,024 word tokens in 191.635581 seconds; mean line confidence was 0.9876259247 and 5 lines were below 0.8. Inference commit was `d57ceee5ce12bfeac36eaa0b7d059043f45fd16c`; sealed artifact-set SHA-256 is `968e6bf93a5af2e6552a2820350c075415d29905df279c31c54d2b095ae6c3a2`. Deterministic row reconstruction and pixel-dash checks use the already pinned control-plane OpenCV 4.14.0.94 and NumPy 2.4.6. Exact transfer/replay commands are in `docs/experiments/E-0011-REPLAY.md`.

E-0012 also added no software, package, driver, or model. Clean commit
`3291f9dca0843b5d67858b44019a7b2319f69057` ran the batch wrapper on the
existing TCB page-15 render with eight CPU threads. It produced the same
50-line/380-word JSON and exact SHA-256 as E-0011; checkpoint resume kept the
model-load session count at one, and the batch/helper-aware seal passed. This
is a mechanism regression, not another accuracy observation. Exact hashes and
replay commands are in `docs/experiments/E-0012-REPLAY.md`.

The statement-location v1 implementation and clean E-0013 MBB/VCB coarse pass add
no software, operating-system package, model, weight, or runtime setting. They
reuse the locked control-plane PyYAML/RapidFuzz dependencies and the existing
PP-OCRv6 CPU-FP32 batch artifacts. Configuration, execution, recovery, and
failure gates are documented in `STATEMENT_LOCATION_RUNBOOK.md`; exact formal
output identities and replay commands are in
`../experiments/E-0013-REPLAY.md`. Therefore no dependency lock or model
inventory changed for this milestone.

The E-0013 bootstrap audit also adds no dependency. It uses the existing JSON,
path, and SHA-256 control-plane utilities and publishes its result under
`statement_location` in `BOOTSTRAP_MANIFEST.json`.

E-0014 added no software, Python distribution, Ubuntu package, driver, model,
weight, or runtime setting. It reused clean inference commit
`116c1879cef7f3f63b2bf1e7d71561d8c7ef78c8`, the frozen 125-distribution GPU
environment, and the four pinned models above. Role B used PP-DocLayoutV3 FP32
plus PaddleOCR-VL-1.6 BF16 sequentially and took 306.225279 seconds over 13
pages at 3,241 MiB peak. Role C used PP-OCRv6 CPU FP32 with eight threads, one
model load per document, and took 510.263426 seconds over 1,435 lines/10,776
words. Exact environment/config/model/code hashes and replay commands are in
`../experiments/E-0014-mbb-vcb-200dpi-reader-seals.json` and
`../experiments/E-0014-REPLAY.md`; generated images and OCR outputs remain
outside Git.

Structural reader fusion v2 also adds no dependency, runtime setting, model, or
weight. Its HTML span parser uses the Python standard library; YAML, text
normalization, OpenCV pixel evidence, and ordered alignment reuse the pinned
control-plane environment. The new configuration and algorithm are documented
in `../STRUCTURAL_READER_FUSION_STRATEGY.md`. A formal evaluation must be run
from a clean commit and record all new source/config hashes before its result is
accepted.

Formal E-0015 reused that exact control-plane environment from clean commit
`94a2c7c4c4809764a59f9f8c977fcd6318e2d6ad`; it ran no OCR/model inference and
added no Python/Ubuntu package, model, weight, driver, or cache. Its parser and
comparison complete in about 1.4 seconds on this VPS when the 13 sealed page
artifacts are local. Exact code/config/source/seal/result hashes, parameters,
expected metrics, transfer prerequisites, and replay command are in
`../experiments/E-0015-REPLAY.md`. The tracked result is about 2.1 MiB; large
renders/OCR/model assets remain outside Git.

Targeted reread v1 and its E-0016 input builder add no Python distribution,
Ubuntu package, driver, model, weight, or runtime setting. High-resolution
source-PDF clipping and quality candidates reuse the locked control-plane
PyMuPDF 1.28.0, OpenCV headless 4.14.0.94, NumPy 2.4.6, and PyYAML 6.0.3.
Deskew and perspective candidates record inverse 3×3 transforms; photometric
candidates retain identity geometry. Subsequent readers reuse the existing four
pinned Paddle weights. DeepSeek-OCR-2 remains isolated from the base
`.gpu-venv`; it is now load- and inference-tested through the hash-locked
external overlay described below. MinerU remains an uninstalled proposal.

The 2026-08-06 human-review registry, period propagation v1, value-status
normalization, and structural ranking v2 add no Python distribution, Ubuntu
package, driver, model, weight, or runtime setting. Source verification reuses
the pinned control-plane PyMuPDF and SHA-256 utilities; YAML/config validation
reuses PyYAML. The paper candidates GraphTSR/TGRNet, DocTr/DocGeoNet/UVDoc,
FastTab, and TabSniper are research hypotheses only and were not installed.

Ordered SchemaGraph mapping v1 adds no Python distribution, Ubuntu package,
model, weight, driver or runtime setting. It reuses Python 3.11, PyYAML 6.0.3,
RapidFuzz 3.14.5 and the existing schema/hierarchy readers. Search is a bounded
k-best dynamic program on CPU; optional accounting-semantic scores are inputs
from separately governed model components and cause no model installation here.
Configuration, research basis, rebuild behavior and fail-closed gates are in
`config/mapping/ordered-subgraph-v1.yaml` and
`../ORDERED_SCHEMA_GRAPH_MAPPING.md`.

Statement locator v2 and native-text quality v2 add no Python distribution,
Ubuntu package, model, weight, driver or runtime setting. They reuse Python
Unicode metadata, regular expressions, PyYAML 6.0.3, RapidFuzz 3.14.5 and the
existing PyMuPDF text boxes. Rebuilds must preserve
`config/document_phase/statement-locator-v1.yaml` at the SHA-256 pinned by
`statement-locator-v2.yaml`; v2 intentionally inherits the frozen v1 thresholds
while changing only title/form normalization. No DeepSeek, TATR or historical
value is invoked in this header-only mechanism.

The E-0016 original-crop evidence sealer also installs nothing. It reuses the
same locked standard-library JSON/TOML/HTML parsing, PyYAML, strict financial
cell parser, PP-OCRv6 CPU-FP32 configuration, and PaddleOCR-VL-1.6 GPU-BF16
configuration. The PP-OCRv6 per-run manifests self-record clean Git, runner,
runtime, package, model-weight, input, and result identities. The current
PaddleOCR-VL shell runner does not self-record a Git commit; the evidence pack
therefore states `NOT_SELF_RECORDED_BY_RUNNER` and binds the runner/config/runtime
and every output byte without claiming stronger provenance. A future runner
version should add its own atomic inference manifest rather than retroactively
asserting a commit for these completed reads.

## Reader candidates inspected 2026-08-06

The model decision and source snapshot are in `../MODEL_READER_DECISION.md`.
The first implementation candidate is Microsoft TATR v1.1 All. It requires no
new Python package in the existing GPU environment: PyTorch 2.12.0+cu130,
TorchVision 0.27.0+cu130, Transformers 5.14.1, Pillow, and safetensors are
already frozen. Its separate `config/models/tatr-v1.1-all.toml` pins:

- repository `microsoft/table-transformer-structure-recognition-v1.1-all`;
- revision `7587a7ef111d9dcbf8ac695f1376ab7014340a0c`;
- `model.safetensors`, 115,437,156 bytes, SHA-256
  `9df416575a3a36ebd0129342d4f597f14d6e5170268f3d52d28584ab4466a501`;
- `config.json` and `preprocessor_config.json` by exact size/hash; and
- MIT license, checkpoint-native 800-pixel longest-edge preprocessing, and
  no-network/no-map/no-value/no-period/no-confidence authority.

The first clean load attempt on commit `dcf1bbc` stopped before inference and
published no output because Transformers 5.14.1 strictly rejects the official
checkpoint's legacy `dilation=null`. The checkpoint remains byte-identical.
`config/models/tatr-v1.1-all.toml` now binds a single in-memory compatibility
resolution from null to the `TableTransformerConfig` default `false`, only for
Transformers 5.14.1. Tests reject a non-null source value, any other field, or
runtime-version drift.
The next dirty smoke stopped before tensor inference because the legacy image
processor contains only `longest_edge=800`. A second exact compatibility rule
resolves it in memory to `shortest_edge=800,longest_edge=800`, preserving aspect
ratio and the checkpoint's maximum-edge behavior. The original processor JSON
is unchanged and source-key/value drift is rejected.

The resulting dirty mechanism smoke passed a real GPU inference in 0.187929
seconds with 249.096680 MiB peak allocated VRAM. It used the same frozen Python
environment and added no package. The 115,514,291 required TATR artifact bytes
are verified in the ephemeral `/dev/shm/bctc-paddlex-e0007` cache; model caches
remain reconstructible and outside Git.

Rebuild/verify commands:

```bash
.gpu-venv/bin/python scripts/bootstrap/download_tatr_model.py \
  --cache-root "$BCTC_MODEL_CACHE_DIR"
.gpu-venv/bin/python scripts/bootstrap/download_tatr_model.py \
  --cache-root "$BCTC_MODEL_CACHE_DIR" \
  --verify-only
```

DeepSeek-OCR-2 is not installed into the base `.gpu-venv`. All 14 artifacts for
the inspected Apache-2.0 HF revision were instead downloaded and verified in an
ephemeral `/dev/shm` cache. The revision is
`aaa02f3811945a91062062994c5c4a3f4c0af2b0`; its BF16 weight is
6,778,573,880 bytes with SHA-256
`d8ff67a424ba6f4dd077885eb9d6a05d2537e76fe5491f0e2a9b712f8c8870fa`.
The official code snapshot is
`2f3699ebbb96fa8af32212e8c170f2cc28730fad` and declares CUDA 11.8,
PyTorch 2.6.0, Transformers 4.46.3, and FlashAttention 2.7.3. The published
CUDA/PyTorch stack is not installed on this Blackwell `sm_120` host. A separate
11-package, hash-locked overlay supplies Transformers 4.46.3 and tokenizers
0.20.3 on top of the existing PyTorch 2.12.0+cu130 runtime, uses eager attention,
and leaves the base environment unchanged. Its successful model load took
4.255978 seconds and allocated 6,883,116,544 GPU bytes. Two real table-page
inferences completed; observed peak allocated VRAM was 8,189,789,184 bytes.
Inference disables DNS/socket access and has no geometry, value, period, scope,
mapping or confidence authority. Exact overlay hashes/install command are in
`config/models/deepseek-ocr2-v1.toml` and
`config/models/deepseek-ocr2-overlay-requirements.txt`; E-0018 and E-0019 retain
the source/config/model/result evidence. The model cache is reconstructible and
remains outside Git.

VietOCR 0.3.13 is installed only as an inference overlay at
`/workspace/bctc-ai-runtime/vietocr-0.3.13`; no distribution was added to the
control-plane or `.gpu-venv`. The official wheel is 34,641 bytes (SHA-256
`07b3777e5176b0d733cb056b68bd817371605f4b3514795fbf91ad4e181b8ccf`).
The upstream `base.yml` and `vgg-transformer.yml` are respectively 1,809 and
505 bytes with SHA-256 `9c8283fadb950f06f5d3400475f80d5355700ff315c9c48b7875e6ea66647d1c`
and `0df9feee197754c7381871e5dfd07c6f3e292a4853eece6f1af240923e57c907`.
The VGG-Transformer weight is 151,815,373 bytes with SHA-256
`380512193a8b6cbf6fad80deacdc9b6939d10d473d199892fc6408d13775ea59`.
All four URLs, sizes and hashes are locked in
`config/models/vietocr-0.3.13.toml`; the installer verifies existing files and
refuses to overwrite a mismatch.

The wheel is extracted byte-for-byte into an isolated `site-packages` overlay.
The inference-only compatibility path reuses PyTorch 2.12.0+cu130,
TorchVision 0.27.0+cu130, Pillow 12.3.0, NumPy 2.3.5, einops 0.8.2 and PyYAML
6.0.2 from `.gpu-venv`; it deliberately does not install the wheel's old
training/download dependency pins. The runner imports the local translate path
directly, forces `cnn.pretrained=false` so TorchVision cannot download ImageNet
weights, disables beam search and network/DNS, and loads the local state dict
with `weights_only=true`. The PyPI classifier says MIT while the wheel's actual
LICENSE and project description say Apache-2.0; that upstream metadata
inconsistency is recorded rather than silently resolved. Installation has
passed exact artifact and wheel-overlay verification. The frozen E-0024 run
loaded the model in 2.452926 seconds and processed 37 single-line crops in
6.977124 total seconds. Peak allocated/reserved GPU memory was
464.441406/656 MiB. It passed only the bounded semantic-proposal gate; the
runtime has no production, numeric, period, unit, sign, geometry, mapping or
automatic-truth acceptance.

Rebuild/verify command:

```bash
PYTHONPATH=src .venv/bin/python scripts/bootstrap/install_vietocr_line_runtime.py \
  --runtime-root /workspace/bctc-ai-runtime/vietocr-0.3.13
```

The runtime is reconstructible. If it must be rolled back, remove only the
explicit `/workspace/bctc-ai-runtime/vietocr-0.3.13` overlay after preserving
any required run manifests; the base environments are unchanged.

The independent numeric-cell reader adds no Python distribution. It reuses the
existing `.gpu-venv` PaddlePaddle 3.3.0, PaddleOCR 3.7.0 and PaddleX 3.7.2
CPU-FP32 runtime with MKLDNN disabled. The Apache-2.0 checkpoint is
`PaddlePaddle/en_PP-OCRv5_mobile_rec` at revision
`267c36e24c331595590fe7bd72bde2436fd286f2`; `inference.pdiparams` is
7,772,315 bytes with SHA-256
`3ec8a97ed6cefe8568d3e2ee90bb193299b566a7661aa4fd52d224b96b59f66b`.
All six repository files, versions, sizes and hashes are pinned in
`config/models/numeric-recognizer-v1.toml`. The formal E-0031 run loaded the
model once and processed 126 source-pixel crops in 11.938103 seconds on CPU.
The corrected-grid E-0034 run used the same unchanged model/runtime, loaded it
once and processed 128 crops in 12.124202 seconds. It verified 118/119 observed
cells exactly; this adds no distribution, checkpoint or environment change.
The process blocks network connections; input contains only `crop_path`; model
probability has no acceptance authority.

Rebuild/verify commands:

```bash
PYTHONPATH=src .venv/bin/python scripts/bootstrap/download_numeric_recognizer.py \
  --cache-root "$BCTC_NUMERIC_MODEL_CACHE_DIR"
PYTHONPATH=src .venv/bin/python scripts/bootstrap/download_numeric_recognizer.py \
  --cache-root "$BCTC_NUMERIC_MODEL_CACHE_DIR" --verify-only
```

The cache is reconstructible and remains outside Git. Rollback removes only the
explicit `official_models/en_PP-OCRv5_mobile_rec` directory after preserving
required manifests; neither Python environment is changed.

IBM TableFormer and ClusterTabNet are also not installed. The inspected
TableFormer/Docling source revision is
`5787142002b4063efe30f172dd91fbc7a94b43a6` (package version 3.13.3, MIT);
the Accurate weight is 212,758,388 bytes with SHA-256
`2a7d6c924b3cd12fb99a09280ca9c33a89c5d60b93253617d2e088c1a40374d9`.
The official ClusterTabNet repository revision is
`e1051c05cd337ad1ac82aabbb0530c784ea21cb0`, Apache-2.0; its released
`table_recognition.pth` is 30,292,814 bytes. The repository is archived and its
requirements pin PyTorch 1.13.1, so it remains a research/custom-graph baseline.

Detailed commands, disk checks, cache rules, failure history, and rollback are in `docs/environment/GPU_RUNTIME_RUNBOOK.md`.

## Maintenance rule

Every software/model change must record version, upstream URL, archive or model revision/hash, license, install command, CUDA/runtime compatibility, measured VRAM, smoke result, and rollback command before the related code commit.
