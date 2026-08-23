# Gemma 4 API-first rescue runbook

Use Gemma only as a bounded page-level table-structure or crop-level
text/number challenger. Run one fresh independent request per page or crop. Do
not use Gemma numeric output as final numeric authority without separate cell
OCR/pixel evidence and an accounting-equation check.

The production rescue order is API-first:

1. call hosted `gemma-4-26b-a4b-it` on the exact full canonical page with a
   fresh context, `thinking_level=MINIMAL`, temperature zero and a generous
   output limit;
2. if deterministic visible-row/column checks reject the response, repeat the
   same page and prompt with a higher supported thinking level;
3. if it is still rejected, use the hosted 31B or a stronger 26B thinking
   configuration when that model is available;
4. use the local 31B/26B Q4 lanes only as recorded independent comparisons,
   not as the default rescue path.

Never copy an API key into this document, logs, request artifacts or result
JSON. Load the credential at execution time from the protected local secret
source. Persist only the model/version, non-secret request policy, input image
digest, raw-response digest, token counts and validation outcome.

Before changing this lane, also review
`docs/experiments/OCR_MAPPING_FAILURE_PREVENTION.md`. It is the cumulative
failure-prevention checklist for OCR, geometry, family graphs, schema mapping,
artifact handling, and authority claims.

## Local fallback runtime

- Model: `/workspace/bctc-ai-runtime/gemma-4-26b-a4b-it-q4_0/gemma-4-26B_q4_0-it.gguf`
- Multimodal projector: `/workspace/bctc-ai-runtime/gemma-4-26b-a4b-it-q4_0/gemma-4-26B-it-mmproj.gguf`
- CUDA server: `/workspace/bctc-ai-runtime/llama.cpp-b10425-cuda-build/bin/llama-server`
- CUDA libraries: `/workspace/bctc-ai-runtime/cuda-13.0.3-toolkit/lib`

Do not use the `llama.cpp-b10425-vulkan` binary on this host: its device list is
empty and it falls back to CPU.

Verify CUDA visibility:

```bash
cd /workspace/bctc-ai-runtime/llama.cpp-b10425-cuda-build/bin
LD_LIBRARY_PATH=/workspace/bctc-ai-runtime/cuda-13.0.3-toolkit/lib:/workspace/bctc-ai-runtime/llama.cpp-b10425-cuda-build/bin \
  ./llama-server --list-devices
```

Start this server only for a bounded fallback comparison. The two reasoning
flags are mandatory; without
them the model can consume the output budget in hidden thinking and return no
JSON.

```bash
cd /workspace/bctc-ai-runtime/llama.cpp-b10425-cuda-build/bin
LD_LIBRARY_PATH=/workspace/bctc-ai-runtime/cuda-13.0.3-toolkit/lib:/workspace/bctc-ai-runtime/llama.cpp-b10425-cuda-build/bin \
  ./llama-server \
  -m /workspace/bctc-ai-runtime/gemma-4-26b-a4b-it-q4_0/gemma-4-26B_q4_0-it.gguf \
  --mmproj /workspace/bctc-ai-runtime/gemma-4-26b-a4b-it-q4_0/gemma-4-26B-it-mmproj.gguf \
  --gpu-layers all --ctx-size 16384 --parallel 1 \
  --host 127.0.0.1 --port 18089 --alias gemma-4-26b-a4b-it \
  --temp 0 --jinja --reasoning off --reasoning-budget 0
```

Send the full canonical-upright page as one fresh chat. Pass the exact
authenticated PNG bytes without resizing, thumbnailing, sharpening, or
cropping. A PDF page has no single intrinsic raster resolution; the
content-addressed canonical page render is the reproducible image authority.
Start with the sealed 200-DPI render. If visible-row/column completeness or
independent digit checks fail, render the original PDF page again at 300 DPI,
bind that new image hash, and issue a fresh request. Never enlarge the 200-DPI
bitmap and call it 300 DPI. Retain both attempts so the higher-resolution retry
cannot silently replace contradictory evidence. Use a large output budget
because a wide table can legitimately produce thousands of JSON tokens. The
request content should be only:

> Chuyển các khoản mục thuyết minh và giá trị tương ứng trong ảnh thành JSON
> nhiều lớp, giữ riêng từng cột của bảng, giữ nguyên chính tả các tên khoản
> mục, không thay đổi chính tả. Trường hợp ảnh không có khoản mục nào thuyết
> minh, chỉ là phần diễn giải thì trả lời đúng chuỗi JSON
> {"ket_qua":"không có khoản mục thuyết minh nào"}. Không phản hồi gì thêm
> ngoài JSON.

For a page rejected specifically because row/column geometry cannot be
reconstructed, use one fresh request on the same full-page bytes and keep the
prompt equally short:

> Chuyển các khoản mục thuyết minh và giá trị tương ứng trong ảnh thành JSON
> nhiều lớp, giữ riêng từng cột của bảng, giữ nguyên chính tả. Với mỗi tên
> khoản mục, header và giá trị, thêm `box_2d` theo thứ tự
> `[ymin,xmin,ymax,xmax]`, tọa độ chuẩn hóa từ 0 đến 1000 theo toàn bộ ảnh.
> Trường hợp ảnh không có khoản mục nào thuyết minh, chỉ là phần diễn giải thì
> trả lời đúng chuỗi JSON
> {"ket_qua":"không có khoản mục thuyết minh nào"}. Không phản hồi gì thêm
> ngoài JSON.

Convert a returned normalized box to the exact source-render frame only as
`x = round(x_norm * image_width / 1000)` and
`y = round(y_norm * image_height / 1000)`. Reject inverted, empty,
out-of-range or overlapping label/value boxes. A Gemma box is a proposal, not
pixel geometry authority: snap/challenge it against the immutable full-page
pixels, PP-OCR polygons/word boxes, repeated numeric column centres and source
order. Keep the ordinary hierarchy-only response and the coordinate-bearing
response as separate attempts; never silently add coordinates to a prior JSON
answer.

For the local fallback, POST an OpenAI-compatible chat request to
`http://127.0.0.1:18089/v1/chat/completions` with:

- model `gemma-4-26b-a4b-it`;
- one user text part and one `data:image/png;base64,...` image part;
- `temperature: 0`, a fixed seed, and `max_tokens: 8192` or more;
- `stream: false`.

The model may wrap valid JSON in a Markdown `json` fence. Strip only that
outer fence, parse strict JSON, and reject duplicate keys/non-finite values.
Bind the result to the exact input image SHA-256. Treat its header hierarchy,
row/column grouping, and spelling rescue as challenger evidence. Reconcile
every numeric cell against independently segmented pixel cells and table
equations before mapping.

Use page-first rescue for table reconstruction. A crop loses multi-level
headers, parent/child context, repeated period axes, and continuation cues.
Only issue a second independent crop request after the full-page response when
one bounded label or cell still needs a challenger. Never splice a crop-only
answer into the reconstructed table without the full-page hierarchy and the
deterministic geometry/accounting checks.

## Hosted primary lane and escalation

The local model is not an older Gemma generation. Its repository is
`google/gemma-4-26B-A4B-it-qat-q4_0-gguf`; the hosted Google catalog reports
`models/gemma-4-26b-a4b-it`, version `001`. The local lane is a QAT Q4_0 GGUF
executed through llama.cpp, so quantization and multimodal runtime can still
produce materially different table transcription from the hosted model.

On the exact authenticated ACB Q1/2025 parent page-15 render (200 DPI,
1654x2339, SHA-256
`38f8090b1b3914863fde0a5962a723770d84d2cdc3ee53c33e247ce2217269cf`),
the local Q4_0 lane preserved the hierarchy but omitted the comparison values
and changed visible digits. The hosted version-001 lane with
`thinking_level=MINIMAL` returned JSON-only, retained both period columns and
all visible DASH cells. A hosted request with no thinking setting emitted a
long self-correction trace instead of JSON; `thinking_budget=0` was rejected
as unsupported.

Therefore the bounded execution order is:

1. deterministic OCR/geometry and accounting engine;
2. the exact full-page bytes and short JSON-only prompt through hosted Gemma
   version 001 with thinking level `MINIMAL`;
3. if visible-column/row completeness still fails, retry the identical page
   with a higher supported thinking level, then try a hosted 31B or stronger
   26B configuration when available;
4. use local 31B/26B Q4 only as an independent comparison after the hosted
   attempts are rejected, never as an automatic replacement;
5. independent cell pixels and accounting closure remain mandatory for every
   number or DASH-to-zero decision.

Do not choose among hosted thinking levels or local/hosted output by which
result maps more rows.
The completeness validator uses visible headers, row/column geometry and
source equations without schema IDs or expected values.

### Precision and hardware boundary

The installed 26B checkpoint is Google's official QAT Q4_0 release, not an
unrelated community quantization, but it is still four-bit and is not
bit-equivalent to the hosted runtime.  Google's published approximate inference
memory is 14.4 GB for 26B Q4_0, 28.8 GB for SFP8 and 57.7 GB for BF16.  The
current RTX 4090 has 24 GB VRAM, so neither SFP8 nor BF16 can run fully on this
GPU.  The official unquantized QAT checkpoint has two weight shards of roughly
49.91 GB and 1.70 GB before runtime overhead.  Installing it therefore also
requires at least about 60--70 GB of persistent free storage; the current host
does not have that space.

Do not label a local run as an unquantized/API-equivalent comparison unless the
exact BF16 checkpoint revision is pinned and its full precision/runtime is
recorded.  A BF16 test on this host would require added storage plus CPU offload
and would be much slower; a clean full-GPU comparison requires a GPU with about
64 GB or more usable memory.  Google does not expose enough hosted deployment
detail to assert that a local runtime is byte-for-byte identical merely from the
public model name.

The practical no-API experiment on this host is the official 31B QAT Q4_0
checkpoint.  It is still four-bit, but Google reports stronger document/vision
benchmarks than 26B A4B and an approximate 17.5 GB model-memory requirement, so
it fits the RTX 4090 for a bounded one-page benchmark.  It must be compared on
the identical canonical image and prompt; it does not inherit authority from
its larger parameter count.

### 31B Q4_0 canonical-page benchmark (2026-08-22)

The bounded local comparison used repository
`google/gemma-4-31B-it-qat-q4_0-gguf`, revision
`59dde24573e7e61570dba08b18a2e1fe246955ed`, with exact files:

- model: 17,651,001,568 bytes, SHA-256
  `179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b`;
- projector: 1,200,726,368 bytes, SHA-256
  `6bd60bdb958548b4093196d38744b0f2290c12503a3fddd7486bffa9c5eb07a4`.

The CUDA server used 20,580 MiB on the RTX 4090 at an 8,192-token context.
Reasoning was off, temperature was zero, and every image/request was a fresh
chat.  Results:

- ACB Q1/2025 parent page 15, canonical 200 DPI image SHA-256
  `38f8090b1b3914863fde0a5962a723770d84d2cdc3ee53c33e247ce2217269cf`:
  local 31B retained both period columns, visible DASH cells, hierarchy and all
  inspected digits.  The response content SHA-256 was
  `71b48084d06f2c9a5dfb3c01228fc9f886ed46a92b3080e85f8bb1f0973c4924`.
- The same ACB page rerendered from the PDF at 300 DPI omitted visible parent
  subtotals even though its remaining digits were correct.  Higher DPI was not
  more complete.
- MBB Q1/2025 consolidated page 30, canonical 200 DPI image SHA-256
  `fa46496ece1a245cd86b59f54ab0fa27cd814ee5b9e4b1f567091cb32299fbbc`:
  local 31B reconstructed the three visible sections, including the complete
  loan-maturity hierarchy, but changed one source label and at least two
  inspected digits.  Its content SHA-256 was
  `558605008e9c526ed1161065551accc1c9560d146d55284dfaae8d3a6bc1714d`.
- The MBB 300-DPI retry was materially worse: it omitted cells and changed
  several digits.  The hosted 26B version-001 request at 200 DPI corrected the
  inspected maturity digits and the `Các khoản trả thay khách hàng` label, but
  still changed another visible Vietnamese phrase.  Hosted content SHA-256 was
  `cbd7359a09c6a8166e2aa1f0d3539d09b9b0fec574c0712353c892547df906fe`.

This falsifies a blanket `300 DPI is more accurate` rule and a blanket
`hosted output is pixel truth` rule.  Use 200 DPI first.  Retry at 300 DPI only
after a visible-completeness failure, retain both outputs, and select neither by
mapping yield. The hosted 26B lane is now the first Gemma rescue. Increase its
thinking level or try a hosted 31B/stronger 26B only for pages/cells rejected
by deterministic completeness or cross-reader checks; use local Q4 only for a
bounded comparison. VietOCR remains the primary semantic reader;
PP-OCR/pixel cells and accounting closure remain the numeric authority
boundary.

### Hosted full-page coordinate benchmark (2026-08-22)

On the exact VPB H1/2025 separate page 37 canonical 200-DPI image, hosted
`gemma-4-26b-a4b-it` with `thinking_level=MINIMAL`, temperature zero and a
16,384-token limit returned JSON-only with 83/83 valid normalized boxes. The
response content SHA-256 was
`01144bec19b6c58a97de92ec4159da514607e104c5aadeef41a9d39a41c5ef43`.
It retained both trading-security period columns and all visible comparison
DASH cells. The same page through local 26B Q4 produced response SHA-256
`aee988ea028fff35107ba8ef55b217d0cac8a7c6d189fe3eba30039c2e095e2f`,
omitted the comparison DASH cells and changed inspected derivative digits.
This benchmark establishes API-first ordering, but not numeric authority: the
accepted DASH cells were independently recovered from authenticated pixel
crops and the period/unit-supported geometric column grid.

On VPB annual-2025 consolidated page 43, a red stamp overlapped the comparison
value `3.202.820`.  The exact 300-DPI page render SHA-256 was
`7c2dfd93c8b49e861c5dc551287def01c9ed58296765c739df7af28e4404f2771`
(628,903 bytes).  A fresh hosted `gemma-4-26b-a4b-it` request with minimal
thinking returned the first table row with `3.202.820`; the raw response
SHA-256 was
`eff53acb76e4431a791d5e07ce20c62e57daf993917885e501815ef15fd79b22`
(4,723 bytes).  This was only an independent challenger.  The accepted value
also retained the same complete grouped-integer prefix in VietOCR, was reread
by PP-OCRv6 after five generic high-chroma suppression thresholds, and closed
the exact leaf-plus-provision equation to the printed net.  Gemma coordinates
in this response are normalized model coordinates, not authoritative PDF or
pixel bboxes.

For one difficult label or number crop, start another fresh chat with no prior
page context and use only this short request:

> Chuyển nội dung nhìn thấy trong ảnh thành JSON {"text":"..."}, giữ nguyên
> chính tả và dấu câu. Không phản hồi gì thêm ngoài JSON.

The crop request must not contain an expected value, schema label, ReportNormId,
bank, page, or accounting result. Bind the response to the exact crop SHA-256,
retain the raw response, and compare it with VietOCR/PP-OCRv6 plus the source
pixels. A Gemma-only number remains a challenger, not numeric truth.

## Failure modes already observed

Keep this checklist with every future run so the same mistakes are not
repeated.

1. **The Vulkan executable silently ran on CPU.**
   `llama.cpp-b10425-vulkan/llama-mtmd-cli --list-devices` returned `(none)`;
   the process used about 29 GB host RAM and no NVIDIA compute process. Always
   run `--list-devices` first and require `CUDA0: NVIDIA GeForce RTX 4090`.
2. **The multimodal CLI rejected the model chat template.**
   Running without Jinja raised `this custom template is not supported`.
   Use the CUDA server with `--jinja`; do not retry the deprecated
   `llama-gemma3-cli` path.
3. **The model consumed the entire output budget in thinking and emitted an
   empty content field.** The failed request generated 8,192 completion tokens
   but no JSON. Start the server with both `--reasoning off` and
   `--reasoning-budget 0`, then reject any empty response.
4. **A detector-merged header was mistaken for one semantic column.** On the
   CTG interest-rate table, PP-OCRv6 merged `Quá hạn` and `Không chịu lãi` into
   one text-line bbox, while the rows below had two distinct numeric column
   centres. Never derive the column count from a header line alone. Combine
   the Gemma hierarchy, PP word gaps, repeated numeric x-centres, and table
   order.
5. **Gemma reconstructed the hierarchy correctly but changed text and digits.**
   In the same CTG page it returned separate `Quá hạn`/`Không chịu lãi` keys,
   yet misspelled the second label and altered multiple visible numbers. Use
   Gemma for structural/text rescue only. Final numbers require independent
   cell segmentation, PP-OCRv6/pixel readback, and exact accounting closure.
6. **A compound fallback axis was introduced to accommodate OCR output.** This
   was semantically wrong because the live schema and source table both have
   separate overdue and no-interest branches. OCR representation errors must
   be repaired at the evidence/geometry layer, never by weakening or merging
   schema concepts.
7. **The PP-OCRv6 model-cache root was passed one directory too deep.** Passing
   `/workspace/bctc-ai-models/official_models` made the runner look for
   `official_models/official_models/...` and fail before model load. The pinned
   `run_ppocrv6_word_boxes.py` cache root is `/workspace/bctc-ai-models`.
8. **A vertically split range header created an extra fragment axis.** CTG's
   `Từ trên 1 năm / đến 5 năm` was briefly represented as both `GT1Y` and
   `1-5Y`. When a complete range and its incomplete fragment occupy the same
   header area, retain the complete physical column only. Confirm the final
   axis count against repeated numeric x-centres before mapping.
9. **A whole-page prompt omitted the comparison column.** A prompt that asked
   only for corresponding values allowed the model to choose the current
   period and add an explanation. Requiring `giữ riêng từng cột của bảng` in
   the otherwise short prompt restored both period columns. Reject any
   response that omits a visible column or includes prose outside the optional
   outer Markdown fence.
10. **Correct hierarchy did not imply correct digits.** Whole-page Gemma
    separated debt/equity and listed/unlisted subviews that the OCR line order
    had interleaved, but it also changed a visible digit and on another page
    copied a neighbouring value into a DASH cell. Use the page JSON for
    hierarchy and row/column association; numeric authority still requires the
    independently segmented cell pixels plus accounting closure.
