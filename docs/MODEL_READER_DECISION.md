# Reader-model decision — 2026-08-06

## Outcome

The pipeline uses specialized readers rather than one universal OCR truth:

1. PP-OCRv6 detection is the source-space authority for polygons, words, lines,
   logical-row grouping inputs and numeric-cell locations. Its Vietnamese text
   prediction is retained as raw evidence, not the preferred semantic reading.
2. DeepSeek-OCR-2 is the primary Vietnamese semantic recognizer on bounded
   title, line and logical-row crops. Its text and reading order are attached
   only to unions of immutable PP-OCRv6 source boxes.
3. A separate numeric path verifies values, final digits, parentheses, minus
   signs and visible dashes. Semantic-reader text cannot alter those cells.
4. VietOCR remains an optional frozen-crop challenger. It is not a planned
   production component unless a bank- and period-separated comparison proves
   that it improves downstream title/accounting-label accuracy over DeepSeek.
5. TATR/TableFormer and relation-graph methods remain structure proposals when
   PP geometry is insufficient. `PP-OCRv6-VI-BCTC` fine-tuning is a gated future
   fallback only after validated end-to-end evidence shows semantic recognition
   remains material; no large dataset/training effort is currently authorized.

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
native runtime for this Blackwell `sm_120` host. All 14 model artifacts are now
hash-verified in an ephemeral `/dev/shm` cache. A hash-locked external overlay
provides the official Transformers 4.46.3/tokenizers 0.20.3 API while retaining
the host's Blackwell-capable Torch 2.12/CUDA 13 runtime. Inference denies
network access and uses eager BF16 attention; no base environment or model file
is modified. The exact reconstruction command is recorded in
`docs/experiments/E-0026-REPLAY.md`.

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
| DeepSeek-OCR-2 | HF `aaa02f3811945a91062062994c5c4a3f4c0af2b0`; code `2f3699ebbb96fa8af32212e8c170f2cc28730fad` | 6,778,573,880 bytes; SHA-256 `d8ff67…70fa` | Apache-2.0 | hash-verified ephemeral runtime; bounded semantic-proposal gate passed on calibration |
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
source PDF page
  → PP-OCRv6 polygons/word/line boxes
  → geometry-only title/line/logical-row/numeric-cell grouping
  → bounded source crops with padding
  → DeepSeek-OCR-2 Vietnamese semantic proposals
  → attach proposals to immutable PP box/box-union identities
  → independent numeric/sign/dash verification on numeric cells
  → multi-signal statement discovery and continuation graph
  → canonical logical rows and ordered SchemaGraph mapping
  → accounting/period/unit/sign validation
  → provenance-bearing Excel output
```

VietOCR is evaluated only on the same frozen semantic crops. It is not fused
into production merely because it beats the PP-OCRv6 text baseline. DeepSeek or
any challenger must improve downstream page/row/schema behavior while all raw
reader disagreements remain available for review.

The first DeepSeek bounded-line run is rejected. With `crop_mode=false`, the
official path resized 98–616 by 27–35 pixel crops directly to 768×768; the
unbounded 8,192-token decoder also produced one 36,314-character hallucination.
The result was 0/37 exact lines, 123.7138% CER and seven structural rejections.
E-0026 changes only these general mechanics: the official aspect-preserving pad
path and a predeclared 128-token/512-character fail-closed budget. It produces
27/37 exact lines, 5/10 exact titles, 0.9646% CER and zero structural or
truncation rejects in 23.1651 seconds at 7,058.903 MiB peak allocated VRAM.
Nineteen MBB and eighteen VCB fixed-grid proposals preserve all existing
statement-discovery decisions and margins. This passes only the bounded
semantic-proposal gate. VietOCR is slightly better on the same crops but remains
challenger-only pending bank/period-separated downstream evidence. Development
now moves to logical rows, SchemaGraph, validation and Excel rather than further
retuning these 37 lines.

The first clean TATR attempt stopped before inference because the official
checkpoint serializes an obsolete top-level `dilation` field as `null`, while
Transformers 5.14.1 now validates it as a strict boolean. The hashed artifact
is not edited. The runner has a version-bound in-memory compatibility rule that
accepts exactly this null field and resolves it to `false`, the current
`TableTransformerConfig` default and the non-dilated checkpoint behavior; any
other field/value/runtime version fails closed.

A subsequent dirty development smoke exposed the same compatibility class in
the image processor before tensor inference: the legacy processor stores only
`longest_edge=800`, while Transformers 5.14.1 requires a complete
`shortest_edge`/`longest_edge` pair. The in-memory resolution sets both to 800,
which preserves aspect ratio and the checkpoint's maximum-edge behavior. The
preprocessor artifact remains unchanged; unexpected keys, sizes, or runtime
versions fail closed.

After both guards were added, a dirty mechanism smoke completed the MBB crop in
0.187929 seconds at 249.096680 MiB peak allocated VRAM and retained all 125
queries. It proposed 36, 30, and 23 table-row boxes at score thresholds 0.5,
0.7, and 0.9. These differing counts prohibit selecting a threshold merely
because it resembles the 27-row PP-OCRv6 proposal; the formal comparison must
use source-coordinate geometry and report precision/recall across thresholds.

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
