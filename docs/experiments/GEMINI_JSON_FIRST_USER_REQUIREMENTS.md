# Gemini JSON-first — yêu cầu vận hành của người dùng

Tài liệu này là checklist bắt buộc cho nhánh làm lại dữ liệu báo cáo tài chính
bằng Gemini. Khi nội dung hội thoại, code hoặc tài liệu cũ mâu thuẫn với các yêu
cầu dưới đây, phải dừng và cập nhật thiết kế trước khi tiếp tục chạy tốn phí.

## 1. Provider và credential

- Giai đoạn thử prompt/case khó dùng OpenRouter trước.
- Model thử nghiệm chính là `google/gemini-3.7-flash`.
- OpenRouter phải khóa đúng provider Google Vertex Flex
  `google-vertex/global/flex`, tắt provider/model fallback và yêu cầu provider hỗ
  trợ đầy đủ tham số. Không được tự chuyển sang host rẻ, model lượng tử hóa hoặc
  model khác.
- Hai key Google trong `docs/experiments/gemma.txt` được gọi thẳng Google API,
  ưu tiên Google Batch sau khi prompt/contract freeze; key không bao giờ chuyển
  qua OpenAI/OpenRouter. Key đuôi `UrJOHw` đã được kiểm tra trực tiếp bằng
  `generateContent` và dùng được. Có thể dùng một request Google standard có
  kiểm soát để xác minh transport/model, nhưng không đốt quota bằng retry vô ích.
- Sau pilot phải chạy song song Google Batch trực tiếp và OpenRouter Batch nếu
  image Batch thật sự được provider hỗ trợ; nếu không, dùng OpenRouter Google
  Vertex Flex song song. Capability phải được chứng minh bằng request ảnh, không
  suy từ Batch text. Chỉ fallback theo lỗi quota/capacity/unsupported có kiểu rõ
  ràng; semantic JSON sai không được dùng làm lý do đổi credential/provider.
- Batch phải resumable theo batch/document/page: lưu batch ID, request ID,
  provider, credential slot ẩn danh, trạng thái poll, request thành công/thất
  bại, token và chi phí; không submit lại job khi process khởi động lại.
- Không in, commit, upload hoặc ghi key vào artifact/log/database. File key phải
  có mode `0600`.

## 2. Ảnh đầu vào

- Chỉ dùng 200 hoặc 300 DPI. Không dùng DPI thấp hơn cho pilot hay corpus.
- Mặc định 300 DPI cho PDF scan, chữ nhỏ hoặc mờ. Chỉ dùng 200 DPI khi trang
  born-digital/scan rõ đã qua kiểm tra đọc được.
- Mỗi kết quả phải bind SHA-256 PDF, số trang vật lý, SHA-256 ảnh, DPI, kích
  thước pixel và MIME type.
- Trước khi chạy toàn corpus phải thử trọn một PDF có nhiều loại trang: báo cáo
  chính, thuyết minh/bảng, continuation và trang không liên quan.

## 3. Prompt và JSON

- Prompt phải ngắn, rõ, schema-blind và có cùng một contract ổn định.
- Gemini chuyển từng trang thành JSON nhiều tầng, giữ nguyên chính tả, thứ tự,
  chữ số, dấu phân cách, ngoặc âm, phần trăm, dấu gạch và ô trống. Không dịch,
  sửa digit, tính lại hoặc tự đặt nhãn cho hàng không nhãn.
- Phải chép đầy đủ mọi khoản mục, hàng và cột giá trị nhìn thấy; không bỏ, gộp,
  tách hoặc đổi thứ tự. `values_exact` phải khớp ngang đúng hàng và đúng số cột.
  Nếu có nội dung tài chính nhưng không chắc chắn/đầy đủ thì trả
  `UNRESOLVED_PAGE`, không đoán hoặc âm thầm bỏ phần khó.
- `columns` gồm mọi cột dữ liệu ngoài cột nhãn khoản mục, kể cả Mã số/Thuyết
  minh với `value_kind=TEXT`; không tạo column riêng cho `label_exact`. Không
  thêm khoảng trắng đầu/cuối vào label/header/cell. Nếu model vẫn trả whitespace
  quanh đúng một dash, phải giữ raw nguyên vẹn và chỉ tạo projection `DASH`;
  không trim raw. Whitespace quanh chữ hoặc số vẫn fail-closed.
- Thu thập cả Bảng cân đối kế toán, Báo cáo kết quả kinh doanh, Báo cáo lưu
  chuyển tiền tệ, bảng thuyết minh và danh sách khoản mục thuyết minh có giá
  trị. Không chép các đoạn văn diễn giải thuần túy không chứa bảng/danh sách
  khoản mục cần số hóa. Trang chỉ có prose hoặc không có các nội dung trên phải
  trả `NO_RELEVANT_FINANCIAL_CONTENT` và `sections=[]`.
- Prompt `items` là một prompt version riêng cho projection chỉ-khoản-mục; không
  được ghi output `items` dưới cache key/hash của prompt `simple`. Trang
  `simple` đã hợp lệ có thể được chiếu bỏ narrative bằng code, nhưng receipt
  tổng hợp phải bind đúng page-version được chọn. Trang bị `RECITATION` mới
  được gọi lại bằng `items` hoặc route khác theo failure policy.
- ID và số thứ tự kỹ thuật phải được suy ra từ vị trí mảng trong code/database,
  không bắt LLM sinh để tránh tốn token và sai bộ đếm.
- Raw response luôn được lưu trước validation. Chỉ lỗi JSON/hợp đồng dữ liệu cơ
  học mới fail-closed: không parse được, thiếu khóa bắt buộc, sai kiểu, hoặc số ô
  của hàng không khớp số cột. `row_kind`, vị trí title và hierarchy do Gemini đề
  xuất là dữ liệu mềm để graph/phương trình kiểm lại; không loại cả trang chỉ vì
  hai JSON tương đương trình bày các trường này khác nhau. Không âm thầm sửa hoặc
  quay về PP-OCR/VietOCR/geometry.
- Dash và printed zero được giữ nguyên khi model đọc được, nhưng validator không
  fail chỉ vì model chiếu một dash kế toán thành `0`: numeric view được phép coi
  dash/0 là cùng hệ số zero và vẫn giữ raw output riêng. Không áp dụng tương
  đương này cho chữ số khác, dấu âm hoặc phần trăm.
- Trang dày không được rút gọn để giảm output. Request phải dành tối đa 65.536
  output token và chỉ nhận kết thúc bình thường. `completion` được sinh sau
  `sections`, chỉ xác nhận đã chép hết trang và liệt kê uncertainty. Toàn bộ
  section/table/row/value-cell/populated-cell do code tái đếm; không buộc model
  tự đếm vì pilot đã chứng minh self-count không ổn định. Thiếu đuôi, complete
  false hoặc uncertainty không rỗng phải thành `UNRESOLVED_PAGE`.

## 4. Kiểm tra và suy luận kế toán

- JSON của Gemini là dữ liệu đọc nguồn; graph và phương trình kế toán là lớp
  kiểm tra/suy luận cấu trúc tiếp theo.
- Phải hỗ trợ nhiều tầng: dòng con cộng thành subtotal; các subtotal trực tiếp
  cộng thành subtotal lớn hơn hoặc khoản mục mẹ. Không cộng đồng thời một
  subtotal với chính descendants của nó; không trộn level, duplicate hoặc
  backsolve digit.
- Có thể dùng phương trình exact trên mọi cột để suy ra quan hệ cha-con gần nhau
  khi hierarchy của Gemini thiếu/sai, nhưng phải lưu receipt thành phần được
  chọn và chỉ chọn một direct frontier exhaustive.

## 5. Database và truy xuất family

- Lưu raw response, canonical page JSON và các projection section/table/row/cell
  vào database có index.
- Giữ nguyên tiếng Việt có dấu làm authority. Bản không dấu chỉ là projection
  tìm kiếm có version, không được ghi đè hay làm mapping authority.
- Sau khi toàn corpus đã có JSON, bắt đầu mapping lại từ Family 1 đến Family cuối
  cùng, không tiếp tục từ Family 12.
- Mỗi family tìm trước bằng hai anchor có quan hệ cha-con hoặc con-con trong vùng
  page/table lân cận; nếu chưa duy nhất mới tăng lên ba anchor. Chỉ đưa vùng ứng
  viên, page trước/sau và hàng xóm cần thiết vào graph matcher.
- Không hard-code bank/file/page/ordinal/value. Sinh đủ biến thể graph cho thứ tự
  cha-con, trước-sau, hàng xóm, continuation và subtotal nhiều lớp.

## 6. Chi phí, telemetry và tài liệu trạng thái

- Lưu theo từng attempt: provider/model/tier ẩn danh credential slot, elapsed,
  HTTP/outcome, input/output/thought/cached/total token và chi phí USD thực tế
  hoặc nhãn ước tính rõ ràng.
- Retry chỉ cho lỗi provider chưa tính phí hoặc lỗi retryable có kiểu rõ ràng;
  không retry JSON/semantic sai để che lỗi và tiêu tiền.
- `RECITATION` là finish reason độc lập của từng response, không phải context
  giữa các request. Mỗi request vẫn stateless; không dùng chat history hay
  `cachedContent`. Retry nguyên ảnh/prompt/provider giống hệt phải bounded vì
  thường lặp lại cùng failure.
- `GEMINI_JSON_FIRST_UNRESOLVED_LEDGER.md` phải để case OPEN lên đầu.
- Giữ nguyên `COMPLETED_TM_FAMILIES.md` như hồ sơ lịch sử. Dùng bộ file JSON-first
  mới cho tiến độ làm lại từ đầu.
- Ghi failure pattern mới vào `RECURRING_FAILURE_PATTERNS.md` sau khi đã có bằng
  chứng/falsifier; không xóa lịch sử cũ.
- Chính sách Git, S3 checkpoint/restore và lưu Codex vẫn áp dụng như trước.
