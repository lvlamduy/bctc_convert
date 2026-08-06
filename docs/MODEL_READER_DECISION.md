# Reader-model decision — 2026-08-06

## Outcome

The pipeline will use a complementary-reader architecture rather than select a
single model as universal OCR truth:

1. Implement Microsoft TATR v1.1 All now as a non-generative row/column/cell
   structure proposal reader.
2. Benchmark DeepSeek-OCR-2 next as an independent semantic, Vietnamese-text,
   table-serialization, and reading-order proposal reader in an isolated
   runtime.
3. Keep IBM TableFormer Accurate as the maintained structure challenger once
   the TATR baseline is frozen.
4. Do not make ClusterTabNet a production dependency. Reuse its word-relation
   idea in the planned custom row/cell graph model and retain its released
   checkpoint only as a research baseline.

No model in this decision can assign a `ReportNormId`, determine template order,
bind a period without visible/inherited table headers, replace a numeric value,
or promote confidence. The visible PDF remains authoritative.

## Why this ordering fits the measured failures

E-0016 shows that the unresolved problem is not simply OCR character quality.
On the dense MBB LCTT crop, the generative reader joined rows and emitted 14
multi-number cells, while PP-OCRv6 retained 27 geometric rows. A structure-only
model that predicts rows, columns, headers, projected row headers, and spanning
cells directly tests row ownership without asking another language decoder to
serialize the entire table.

TATR is the lowest-risk first addition. Its official
`microsoft/table-transformer-structure-recognition-v1.1-all` checkpoint is
trained on PubTables-1M plus the corrected FinTabNet financial-table data. It is
28,847,819 FP32 parameters and has a 115,437,156-byte safetensors file. The
checkpoint is natively supported by the already locked Transformers runtime;
there is no new Python or CUDA dependency. It still requires separate OCR, which
is desirable here: TATR proposes geometry and PP-OCRv6/source-PDF text supplies
the observed tokens.

DeepSeek-OCR-2 is the strongest new semantic-reader candidate. Its 2026 paper
reports improved table and reading-order scores on OmniDocBench v1.5 through
dynamic visual-token reordering. The released model is approximately 3.39B BF16
parameters with a 6,778,573,880-byte weight file. However, the published main
benchmark is Chinese/English, not Vietnamese bank reports, and the output is
generative. A separate study of the predecessor DeepSeek-OCR found strong
dependence on linguistic priors under corrupted-text tests. That study does not
directly evaluate OCR-2, but it is sufficient reason to require source-exact
digit/sign tests and an independent geometry reader before any output is
accepted.

The official DeepSeek-OCR-2 instructions pin CUDA 11.8, PyTorch 2.6,
Transformers 4.46.3, and remote model code. CUDA 11.8 is not an appropriate
native runtime for this Blackwell `sm_120` host. The model must therefore be
tested in a separate hash-pinned environment using a Blackwell-capable PyTorch
build; remote code and weights must be pinned and hashed before network access
is disabled for inference. Its 6.78 GB weight file also exceeds the current
5.7 GB persistent workspace headroom, so the first benchmark cache must use the
16 GB currently free in `/dev/shm` or storage must be expanded. An ephemeral
cache is acceptable for a replayable calibration run, not for deployment.

IBM's maintained Docling model package is a credible second structure reader.
The inspected 3.13.3 source accepts PyTorch 2.2.2–2.x and provides an Accurate
TableFormer checkpoint of 212,758,388 bytes. It recognizes table structure and
content boxes; the package documents training-data support for PubTabNet,
FinTabNet, and TableBank.
It adds `docling-core`, `rtree`, and other runtime dependencies, so it follows
the dependency-free TATR baseline rather than being introduced simultaneously.

ClusterTabNet is technically attractive because it clusters OCR words by row,
column, header, and table relations and is rotation-agnostic at the relation
output. Its paper reports 7–19M-parameter variants. But its released structure
model is below the released TATR result in the paper's four-class comparison,
its requirements pin PyTorch 1.13.1, and SAP archived the official repository
on 2026-06-16. Its graph formulation remains useful; the archived implementation
is not the first production dependency.

## Frozen source snapshot

| Candidate | Code/model revision inspected | Weight identity | License | Installation state |
|---|---|---|---|---|
| TATR v1.1 All | HF `7587a7ef111d9dcbf8ac695f1376ab7014340a0c`; Microsoft code `16d124f616109746b7785f03085100f1f6247575` | 115,437,156 bytes; SHA-256 `9df416…6a501` | MIT | selected for immediate calibration |
| DeepSeek-OCR-2 | HF `aaa02f3811945a91062062994c5c4a3f4c0af2b0`; code `2f3699ebbb96fa8af32212e8c170f2cc28730fad` | 6,778,573,880 bytes; SHA-256 `d8ff67…70fa` | Apache-2.0 | not installed; isolated benchmark next |
| IBM TableFormer Accurate | code `5787142002b4063efe30f172dd91fbc7a94b43a6`; HF bundle `2199320848bb9a8a519d22e4b528185a4f9a6f64` | 212,758,388 bytes; SHA-256 `2a7d6c…74d9` | MIT | not installed; challenger |
| ClusterTabNet | archived code `e1051c05cd337ad1ac82aabbb0530c784ea21cb0` | released `table_recognition.pth`, 30,292,814 bytes | Apache-2.0 | not installed; deferred |

Ellipsized hashes in this human-readable table are not verification inputs.
Machine verification uses the full hashes in the relevant model configuration.

Primary sources:

- [DeepSeek-OCR-2 paper](https://arxiv.org/abs/2601.20552) and
  [official code](https://github.com/deepseek-ai/DeepSeek-OCR-2)
- [Microsoft Table Transformer code and model descriptions](https://github.com/microsoft/table-transformer)
- [IBM TableFormer paper](https://research.ibm.com/publications/tableformer-table-structure-understanding-with-transformers)
  and [maintained Docling IBM models](https://github.com/docling-project/docling-ibm-models)
- [ClusterTabNet paper](https://arxiv.org/abs/2402.07502) and
  [archived official implementation](https://github.com/SAP-archive/clustertabnet)
- [DeepSeek-OCR linguistic-prior stress test](https://arxiv.org/abs/2601.03714)

## Fusion contract

```text
source PDF crop
  ├─ PP-OCRv6 word boxes and source-visible punctuation
  ├─ TATR row/column/header/spanning-cell boxes
  └─ DeepSeek-OCR-2 semantic text/table proposal (later benchmark)
          ↓
canonical logical-row graph
  - geometry assigns word ownership to candidate cells
  - labels/order align rows; values never choose the alignment
  - inherited table headers bind periods on continuation crops
  - disagreement/missing evidence remains explicit
          ↓
hierarchy-first schema mapping in workbook display order
```

The first TATR calibration uses only the two original full-table crops already
frozen by E-0016. It reports every one of the model's object-query probabilities
so confidence thresholds can be analyzed later without rerunning or silently
discarding boxes. The checkpoint's native 800-pixel longest-edge preprocessing
is retained for the first pass; a high-resolution override, tiling, or
fine-tuning is a separate experiment.

## Evaluation and promotion rules

Calibration must report table coverage, row/column boundary precision and
recall, cell adjacency, false row merges/splits, wrapped-label ownership,
source-exact Vietnamese labels, exact numeric strings, exact sign/dash/zero
states, wall time, and peak VRAM. Conditional reader agreement is reported
separately from coverage and human-gold accuracy.

No candidate becomes production-capable from the E-0016 development crops. A
promotion threshold will be fixed only after a human-reviewed split is frozen
by bank and reporting period. The split must include clean, blurred, dark-header,
skewed/warped, multiline, page-continuation, direct/indirect LCTT, separate/
consolidated, quarterly, and annual examples.
