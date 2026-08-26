# Gemini JSON-first prompt pilot

Ngày cập nhật: 2026-08-26.

Đây là log pilot trước corpus, không phải artifact hoàn thành toàn PDF hay toàn
140 filing. Mọi request dùng đúng Gemini 3.7 Flash. Các dòng OpenRouter khóa
`google/gemini-3.7-flash` với provider `google-vertex/global/flex` và không
fallback; các dòng Google gọi trực tiếp `gemini-3.7-flash` bằng credential Google.

## Kết quả hiện có

| Trang | DPI | Kết quả | Input | Output | Chi phí USD | Nhận xét |
|---|---:|---|---:|---:|---:|---|
| MBB Q1/2025 p31, thuyết minh nested | 200 | valid | 2.472 | 1.970 | 0,002310375 | Đúng label/value; thiếu một ancestor ở 3 hàng. |
| MBB Q1/2025 p31, thuyết minh nested | 300 | valid | 2.472 | 2.011 | 0,0023488125 | Đúng label/value và hierarchy; 6 phương trình nhiều tầng khép exact. |
| MBB Q1/2025 p1, cover | 300 | valid NO_RELEVANT | 2.472 | 316 | 0,00075975 | JSON tối thiểu đúng. |
| MBB Q1/2025 p5, statement continuation | 300 | valid | — | — | 0,0013546875 | 10 hàng, 30 cell/19 populated; note column và hai money column đúng. |
| MBB Q1/2025 p6, KQKD | 300 | valid | 2.472 | 2.136 | 0,002466 | 22 hàng, 110 cell/98 populated; đúng năm cột dữ liệu. |
| MBB Q1/2025 p8, LCTT continuation | 300 | pre-V3 reject | 2.472 | 888 | 0,001296 | Nội dung đúng nhưng hai dash có whitespace đầu; strict V3 phải reject. |
| MBB Q1/2025 p7, LCTT dày | 300 | valid V3 | 3.166 | 3.653 | 0,0040183125 | 33/33 hàng, 99 cell/63 populated, hierarchy và toàn bộ value kiểm tra trực quan đúng. |
| MBB Q1/2025 p3, CĐKT phần tài sản | 300 | valid offline replay | 3.188 | 3.061 | 0,0034674375 | 39/39 hàng, 117 cell/94 populated; label/value/hierarchy đúng, 11/11 direct-frontier equation khép cả hai kỳ. |
| MBB Q1/2025 p3, CĐKT phần tài sản | 300 | valid Google direct standard V5 | 1.754 | 4.121 | 0,01676925 ước tính | 8,256 giây; 39/39 hàng, 117 cell/94 populated; label/value/hierarchy đúng. |
| MBB Q1/2025 p3, CĐKT phần tài sản | 300 | valid OpenRouter Vertex Flex V5 | 3.042 | 3.008 | 0,003390375 thực trả | 35,826 giây; label, value và hierarchy byte-semantic giống Google direct; chỉ khác 8 proposal `row_kind=ITEM/SUBTOTAL`. |
| MBB Q1/2025 p3, CĐKT phần tài sản | 300 | valid Google direct JSONL Batch V5 | 1.754 | 4.138 | 0,0084165 ước tính | 1.123,614 giây từ submit đến result; 39/39 hàng, 117 cell/94 populated; thứ tự/label/value/hierarchy giống Google standard, chỉ khác 10 proposal `row_kind=ITEM/SUBTOTAL`. |
| OpenRouter Vertex Flex panel p1/p3/p7/p31/p60 | 300 | 5 luồng + bounded retry | 15.295 | 9.472 | 0,0117478125 thực trả | Wave đầu 23,827 giây, 3/5 thành công; p3/p7 zero-usage rồi thành công sau retry. Cả 5 page JSON hợp lệ; 103 hàng, 320 cell, 257 populated. |

## Pilot Batch song song

- Google inline Batch nhận job nhưng từ chối ảnh inline và ảnh Files API trong
  inline request bằng `INVALID_ARGUMENT`. File ảnh đó vẫn chạy đúng qua
  `generateContent` thường; vì vậy lỗi nằm ở transport inline Batch, không phải
  ảnh, prompt hay model.
- Đường Google chính thức cho multimodal Batch đã chuyển sang JSONL: upload ảnh
  bằng Files API, ghi từng `GenerateContentRequest` vào JSONL, upload JSONL, rồi
  tạo batch bằng `inputConfig.fileName`. Mỗi ảnh, JSONL, request, poll và kết quả
  đều có receipt SHA/size/credential slot; job không được submit lại khi resume.
- Positive image gate đã hoàn tất: job một trang kết thúc
  `BATCH_STATE_SUCCEEDED`, tải được `batch-results.jsonl`, ingest đúng 1/1 request,
  0 failed và 0 unfinalized. Provider dùng 1.754 input token (662 text + 1.092
  image), 4.138 output token, 0 thought token; chi phí Batch ước tính
  0,0084165 USD. Kết quả và SQLite store ở
  `/tmp/gemini-json-first-google-jsonl-page3/`.
- OpenRouter true Batch đã thử cả data-URI và URL HTTPS ký từ object S3 bất biến.
  Probe lặp có kiểm soát với hai ảnh 300 DPI, hai `custom_id` trong cùng batch,
  tạo body base64 3.404.103 byte và được nhận ở `PENDING`, nhưng kết thúc 0/2
  completed, 2/2 failed, `usage=null`: validator báo chỉ nhận public HTTP(S),
  từ chối base64/data-URI. URL HTTPS vượt validator đầu vào nhưng Google Vertex adapter
  vẫn trả lỗi rõ ràng rằng serializer Batch không hỗ trợ image input. Vì vậy
  OpenRouter true Batch hiện chỉ dùng được cho text, không dùng cho image→JSON.
  Tài liệu Batch Beta chính thức được kiểm tra lại ngày 2026-08-26 cũng ghi rõ
  endpoint hiện `text-only` và reject mọi `image`, `input_image`, `input_file`,
  audio/video/file content part; phải dùng sync API cho multimodal. Dòng mô tả
  model `google/gemini-3.7-flash:batch` là multimodal chỉ phản ánh capability của
  model, không ghi đè giới hạn transport Batch. Files API chỉ chứng minh có thể
  upload file cho API tương lai/khác; tài liệu không công bố một `file_id` media
  binding nào cho `/api/beta/batches`.
  Khi text Batch hoàn tất, OpenRouter trả inline `results[]`; model content nằm ở
  `results[i].response.body.choices[0].message.content`. Nội dung không bắt buộc
  là JSON, nhưng pipeline yêu cầu JSON và tự lưu poll envelope, raw response,
  parsed page JSON, usage/cost và database. Google file Batch khác ở chỗ provider
  tạo một output JSONL để client tải xuống.
- Với hàng trăm/nghìn request text, OpenRouter nhận một inline `requests[]`,
  stream-parse được mảng rất lớn, hoàn tất trong cửa sổ 24 giờ và trả kết quả
  inline theo `custom_id`; OpenRouter tự giữ JSONL nội bộ 30 ngày. Chưa có giới
  hạn số request công khai trong trang quickstart, nên production phải shard
  theo document/page và ngân sách token thay vì giả định một batch vô hạn. Với
  ảnh, tăng số lượng S3 object hoặc kéo dài presigned URL không thay đổi giới hạn
  `text-only`; không submit corpus ảnh cho tới khi một capability probe thật sự
  thành công trên đúng Batch endpoint.
- Nhánh song song khả dụng là Google direct Batch + OpenRouter Google Vertex
  Flex đồng bộ. OpenRouter Flex vẫn khóa model/provider, tắt fallback và lưu
  chi phí thực. Nếu OpenRouter bổ sung image Batch sau này phải chạy lại pilot
  capability; không suy đoán từ Batch text.
- Gate hai Google credential trên PDF 60 trang: slot sinh viên upload được 30
  ảnh và JSONL nhưng create Batch trả `FAILED_PRECONDITION`; một bounded standard
  request trên đúng slot đó chờ 849,178 giây rồi kết thúc HTTP 503
  `CAPACITY_SHED`, `usage=null`. Vì vậy slot này chưa đủ capability cho corpus và
  không được retry hàng loạt. Slot trả phí có hậu tố `UrJOHw` đã nhận hai job
  30+30 trang, cả hai chuyển sang `BATCH_STATE_RUNNING`, 0 failed; kết quả cuối
  vẫn phải qua page validator và document-manifest gate trước khi freeze prompt.
- Multithread OpenRouter gate chạy đồng thời p1/p3/p7/p31/p60. Ba request thành
  công ngay; hai trang primary statement dày trả HTTP 200 nhưng zero usage ở
  wave đầu. Bounded retry hoàn tất cả hai mà các attempt lỗi không bị tính phí.
  Năm kết quả hợp lệ dùng tổng 15.295 input, 9.472 output, 199 thought token và
  0,0117478125 USD thực trả. Trên cùng p3, OpenRouter dùng 3.059/3.039 token và
  0,003422625 USD, bằng 40,67% chi phí Google JSONL Batch 0,0084165 USD; label,
  value và hierarchy vẫn tương đương. Đây là so sánh một trang, chưa phải ước
  lượng corpus; whole-PDF Batch phải cung cấp phân phối đại diện trước dự toán.

## Gate chống cắt output trên trang dày

Pilot p7 cho ba bằng chứng riêng:

1. Receipt đặt trước `sections` tự khai 26 hàng/78 cell, trong khi JSON thật có
   33 hàng/99 cell; validator reject.
2. Chuyển receipt xuống cuối làm section/table/row/value-cell khớp 1/1/33/99,
   nhưng self-count populated-cell vẫn lệch 61/63; validator reject.
3. Contract cuối bỏ self-count không hữu ích, giữ receipt cấu trúc có thể replay.
   Request hoàn thành một lượt trong 28,023 giây, `finish_reason=stop`, chỉ dùng
   3.653/65.536 output token. JSON cuối có 33 hàng, từ group hoạt động kinh doanh
   đến total hoạt động đầu tư, không mất phần cuối.

Artifact cuối:

- page JSON: `/tmp/gemini-json-first-v3-dense/page007-final-contract/page.json`,
  SHA-256 `779858023c8d460c9811268db78d0efe62bdd4d80b3732efaa116b87322ab9dd`;
- observation: `/tmp/gemini-json-first-v3-dense/page007-final-contract/observation.json`,
  SHA-256 `24132d70348f37ac85a15730fbdd453dea094c11e6695fdd5467a1da443e23fd`;
- raw response: `/tmp/gemini-json-first-v3-dense/page007-final-contract/raw-response.json`,
  SHA-256 `939f3bed88c7eaa621e32c2c90fd189a1bd78c9b460e27b70b093bd89c40d23e`.

## Pilot prompt ngắn và validator tối thiểu — 2026-08-26

- Thêm variant `simple`, khoảng 1 KB UTF-8, chỉ yêu cầu: đúng JSON Schema; giữ
  đủ tiêu đề/hàng/cột/giá trị và thứ tự; không sửa/đoán; dash có thể là `0`; trả
  `NO_RELEVANT_FINANCIAL_CONTENT` hoặc `UNRESOLVED_PAGE` đúng trường hợp.
- Trang MBB Q1/2025 p13 bị Google Batch chặn `RECITATION` hai lần với prompt
  balanced (1.771 input, 0 output mỗi lần). Prompt simple qua OpenRouter Vertex
  Flex sync thành công lần đầu trong 19,6 giây: 2.592 input, 1.266 output,
  0,001672875 USD. Đối chiếu ảnh xác nhận đủ 2 mục thuyết minh, đủ 4 đoạn mục 8
  và toàn bộ đoạn/bullet mục 9.
- P3 bảng cân đối: simple và balanced cùng 39 hàng/117 ô/94 ô có dữ liệu; mọi số
  giữ nguyên. Simple dùng 2.592/3.027 token và 0,0033238125 USD, so với balanced
  3.059/3.039 và 0,003422625 USD. Khác biệt chỉ ở proposal `GROUP/SUBTOTAL`,
  header path và dash→`0` được phép.
- P31 bảng thuyết minh: cả hai cùng 21 hàng/84 ô/80 ô có dữ liệu. Simple dùng
  2.592/2.042 token và 0,002400375 USD, so với balanced 3.059/2.026 và
  0,0024729375 USD. Tiêu đề giống nhau được đặt ở section/table thay vì narrative;
  validator chấp nhận cả hai, graph chuẩn hóa sau.
- OpenRouter true Batch vẫn không chạy image: base64 bị từ chối vì chỉ nhận URL;
  S3 presigned URL vượt transport nhưng Vertex adapter trả typed error rằng image
  Batch chưa có serializer. Dùng sync Vertex Flex cho nhánh OpenRouter.

## Quyết định tạm thời

- Dùng 300 DPI mặc định; 200 DPI chỉ cho trang rõ. Không dùng dưới 200 DPI.
- Dùng prompt `simple` làm mặc định mới. Giữ `compact`/`balanced` làm fixture đối
  chứng, không tự động nâng prompt chỉ vì khác `row_kind` hoặc vị trí title. Chỉ
  escalation khi thiếu hàng/cột/giá trị hoặc output bị cắt được chứng minh.
- Validator cứng chỉ bao phủ JSON envelope, kiểu dữ liệu, trạng thái mâu thuẫn và
  độ rộng giá trị thực. Cột nhãn in trên ảnh có thể vừa xuất hiện trong
  `columns` vừa được tách sang `label_exact`; code bỏ cột nhãn dư khỏi canonical
  JSON nếu và chỉ nếu mọi hàng cùng tuân theo quy ước đó. Raw response không bị
  sửa. `row_kind`, hierarchy, title placement là proposal; graph và phương trình
  kế toán mới là tầng xác nhận cha-con/subtotal.
- Giới hạn output 65.536; chỉ nhận kết thúc bình thường.
- `completion` đứng cuối JSON, chỉ khai `all_relevant_content_transcribed` và
  danh sách uncertainty. Section/table/row/value-cell/populated-cell, ID và
  source-order đều do code/database suy ra; không bắt model tự làm bookkeeping
  dễ sai. `false` hoặc uncertainty không rỗng thành `UNRESOLVED_PAGE`.
- Whitespace quanh đúng một dash được giữ nguyên trong raw `values_exact` và
  chiếu dẫn xuất thành `DASH`; không trim/sửa raw. Một `_` biệt lập cũng được
  giữ nguyên raw và chiếu thành `DASH`, vì Google standard và JSONL Batch cùng
  chép hai dash trên p3 thành `_`; chuỗi chứa `_` cùng ký tự khác vẫn là `VALUE`.
  Prompt mới cấm dùng `_` cho dash để giảm lỗi lặp lại. Whitespace quanh chữ/số
  vẫn reject. Google structured-output subset không hỗ trợ regex `pattern` cho
  string nên prompt/schema không thể cưỡng chế lexical rule này hoàn toàn.
- `row_kind` chỉ là proposal. Pilot CĐKT p3 giữ đúng hierarchy nhưng gọi một số
  subtotal là `ITEM`; tầng graph/equation phải tái xác nhận subtotal/total bằng
  direct frontier, không lấy nhãn loại của model làm authority.
- Trước whole-PDF, V5 đã qua CDKT/KQKD/LCTT/note/continuation/irrelevant,
  repeat Google/OpenRouter trên CDKT và Google JSONL image Batch positive. Gate
  đầy đủ 60 trang, fallback và supervisor end-to-end được ghi ngay dưới đây;
  gate đang chạy là corpus production 140 PDF.

## Corpus production checkpoint và prompt chỉ-khoản-mục

- Checkpoint 2026-08-26 có 1.462/8.947 trang đã ingest JSON hợp lệ trong 27
  tài liệu: 1.161 `FINANCIAL_NOTE_CONTENT`, 173
  `PRIMARY_FINANCIAL_STATEMENT`, 127 `NO_RELEVANT_FINANCIAL_CONTENT` và một
  `UNRESOLVED_PAGE`. Kho có 15.595 row và 54.320 value cell tại checkpoint gần
  trước; các counters tiếp tục tăng trong supervisor.
- Tổng usage tại checkpoint là 2.916.346 input, 2.247.429 output, 78.134 thought
  token và `5.086646 USD`. Supervisor chạy 25 OpenRouter Vertex Flex request
  song song với tối đa 12 Google Batch job; task/batch/page state đều ở ledger
  để resume.
- Prompt `items` chỉ giữ primary statements, bảng và danh sách khoản mục có giá
  trị; prose-only trả `NO_RELEVANT_FINANCIAL_CONTENT`. Sáu hard-page request
  thành công dùng tổng `0.012789 USD`. Prompt này có hash/cache key riêng, không
  masquerade thành output `simple`.
- ACB H1/2025 hợp nhất p22 là current OPEN: nguyên trang và crop bảng 5 nhóm nợ
  vẫn `RECITATION`, còn crop bảng tài sản bảo đảm qua Google standard giữ đúng
  12 hàng và các tỷ lệ, không cắt output. OpenRouter Batch đã được thử cả
  data-URI và S3-presigned URL; cả hai không tính usage và fail vì transport
  Vertex Gemini Batch không hỗ trợ image. Chi tiết ở
  `GEMINI_JSON_FIRST_UNRESOLVED_LEDGER.md`.

## Whole-PDF simple pilot — MBB Q1/2025, 60 trang

- Hai Google JSONL Batch 30+30 trang hoàn tất sau 958,06 và 941,57 giây.
  Validator cũ ingest 50/60. Replay raw bằng canonical validator V7 khôi phục 9
  trang mà không gọi API: tám trang chỉ lặp cột nhãn trong `columns`, một trang
  chỉ khác dấu gạch đầu dòng ở hierarchy proposal.
- Trang 13 là failure thật: Google Batch trả `RECITATION` hai lượt, không có JSON.
  OpenRouter Vertex Flex fallback đúng riêng trang 13 hoàn tất trong khoảng 21
  giây. Không trang Google thành công nào bị OCR lại.
- Manifest V2 đủ 60/60 trang: 52 `FINANCIAL_NOTE_CONTENT`, 6
  `PRIMARY_FINANCIAL_STATEMENT`, 2 `NO_RELEVANT_FINANCIAL_CONTENT`; 726 hàng,
  2.376 ô, 75 bảng. Tổng 79.528 input, 105.949 output, 4.395 thought token,
  0,235045125 USD. Google giữ 59 trang/0,23337225 USD; OpenRouter giữ đúng một
  trang/0,001672875 USD.
- Artifact: `/tmp/gemini-json-first-mbb-q1-2025-simple-v1/document-manifest-v2.json`,
  SHA-256 `0f4ff40583a9ada334a6f47443c7b5b5f53c5b3365aee1ed72851645480590db`,
  72.007 byte; manifest ID
  `gfdmv1:manifest:a85574fb34dfdbde5827ffd577a81c2f32444d3d70c6f3c773ccf57c33b9e083`.

## Supervisor fallback end-to-end

- Một corpus plan một trang được dựng từ đúng trang 13 gây `RECITATION`, với
  Google Batch là route chính, `max_task_attempts=1` và OpenRouter Vertex Flex
  là fallback theo trang.
- Ledger V2 ghi đúng chuỗi trạng thái bất biến
  `PENDING → SUBMITTED → RUNNING → FALLBACK_PENDING → FALLBACK_RUNNING →
  SUCCEEDED`. Google job kết thúc `BATCH_STATE_SUCCEEDED` nhưng request trang
  vẫn có typed failure `finish_reason=RECITATION`, 1.304 input token, 0 output;
  vì vậy batch thành công không bị nhầm thành extraction thành công.
- Supervisor chỉ gửi lại physical page 1 qua OpenRouter. Fallback thành công
  ngay attempt đầu với 2.592 input, 1.266 output, 0 thought token và
  0,001672875 USD. Document manifest V2 bind route của trang là
  `OPENROUTER/google-vertex/global/flex`; không có trang Google thành công nào
  bị chạy lại.
- Artifact root:
  `/tmp/gemini-json-first-fallback-e2e-v1`; corpus run ID
  `gjfpcrunv1:242f109b5caa4fa179fe4df1bfa22a311d670790272fcd22570411c43a988330`.
  Gate supervisor tự động đã PASS; corpus 140 PDF được phép dùng cùng state
  machine, prompt `simple`, canonical validator V7/store V9 và bounded fallback.
