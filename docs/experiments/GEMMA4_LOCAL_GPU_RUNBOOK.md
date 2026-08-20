# Gemma 4 local GPU runbook

Use this lane only as a bounded page-level table-structure/text challenger.
Run one independent request per page. Do not use Gemma numeric output as final
numeric authority without a separate cell OCR and accounting-equation check.

Before changing this lane, also review
`docs/experiments/OCR_MAPPING_FAILURE_PREVENTION.md`. It is the cumulative
failure-prevention checklist for OCR, geometry, family graphs, schema mapping,
artifact handling, and authority claims.

## Fixed local runtime

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

Start the local-only server. The two reasoning flags are mandatory; without
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

Send the full canonical-upright page as one fresh chat. Use a large output
budget because a wide table can legitimately produce thousands of JSON
tokens. The request content should be only:

> Chuyển bảng trong ảnh thành chuỗi JSON nhiều lớp, giữ đúng chính tả của các
> khoản mục và giữ riêng từng cột của bảng. Không phản hồi gì thêm ngoài JSON.
> Giữ nguyên chính tả cả các key trong JSON.

POST an OpenAI-compatible chat request to
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
