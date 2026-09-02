# Gemini JSON-first — yêu cầu vận hành của người dùng

Tài liệu này là checklist bắt buộc cho nhánh làm lại dữ liệu báo cáo tài chính
bằng Gemini. Khi nội dung hội thoại, code hoặc tài liệu cũ mâu thuẫn với các yêu
cầu dưới đây, phải dừng và cập nhật thiết kế trước khi tiếp tục chạy tốn phí.

> **Xác nhận của người dùng ngày 2026-09-02, phạm vi cuối cùng:** chỉ xử lý báo
> cáo từ **Quý 1/2025 đến thời điểm hiện tại**. Năm 2024 không thuộc hàng đợi
> Gemini của đợt này. Toàn bộ JSON đã có của tám ngân hàng ACB, BID, CTG, HDB,
> MBB, VCB, VIB và VPB và mọi task của mười chín ngân hàng mới phải được tái sử
> dụng theo exact source/page/image identity, không gửi trùng.

## 0. Phạm vi mở rộng 27 ngân hàng — checkpoint 2026-09-02

- Khoảng thời gian chính thức là **từ Quý 1/2025 đến thời điểm hiện tại**.
  Không lập hoặc chạy paid Gemini frontier cho năm 2024.
- Tám ngân hàng **ACB, BID, CTG, HDB, MBB, VCB, VIB và VPB** đã hoàn tất bước
  Gemini trả JSON. Mọi PDF/page đã có trong manifest hiện hành của tám ngân hàng
  này phải dùng lại từ store/cache bất biến; **tuyệt đối không gửi lại Gemini
  hoặc OpenRouter**.
- PDF/page đã có trong corpus tám ngân hàng hoặc ledger mười chín ngân hàng là
  reuse-only. Việc đổi tên file, đổi plan hoặc khởi động lại process không cấp
  quyền gửi lại.
- Mọi request mới chỉ được đi qua **OpenRouter → `google/gemini-3.7-flash` →
  `google-vertex/global/flex`**, service tier `flex`. Direct Google, Google
  Standard, Google Batch và mọi fallback provider/model đều bị cấm.
- Runner phải dừng trước request đầu tiên nếu paid frontier giao với bất kỳ
  source/page/image identity nào trong corpus đã hoàn tất hoặc ledger đang
  chạy. Khi resume, chỉ page chưa có kết quả hợp lệ mới được retry; không gửi
  lại cả PDF hoặc page đã có cache chỉ vì process khởi động lại.
- Chính sách Git, snapshot/restore S3 và backup Codex tiếp tục giữ nguyên.

### Cổng chống gửi trùng dữ liệu đã có

Đây là điều kiện bắt buộc, không phải khuyến nghị:

| Nhóm | Phạm vi | Quyền gọi Gemini mới |
| --- | --- | --- |
| Đã có/đang xử lý, chỉ tái sử dụng | Corpus tám ngân hàng và ledger mười chín ngân hàng 2025-current | **CẤM GỬI LẠI** exact PDF/page/image; chỉ đọc manifest/store/cache/ledger |
| Paid frontier hiện hành | 271 PDF của mười chín ngân hàng mới, Quý 1/2025–hiện tại | Chỉ gửi page tiếng Việt chưa có JSON qua OpenRouter Vertex Flex |
| Năm 2024 | Ngoài phạm vi đợt này | **KHÔNG GỬI GEMINI** |

Trước mỗi lần `run`, `resume` hoặc `repair`, runner phải đối chiếu toàn bộ
source SHA, page-image SHA, đường dẫn và ranh giới trang với corpus manifest đã
hoàn tất và mọi ledger đang hoạt động. Nếu có overlap chưa được đánh dấu reuse
thì phải dừng **trước request đầu tiên**. Việc đổi tên file, đổi plan, khởi động
lại process hoặc chạy repair không tự tạo quyền gửi lại. Page đã có JSON hợp lệ
phải được lấy lại theo source/image hash và manifest; repair chỉ được phép nhắm
đúng page thất bại có receipt.

Kiểm tra vận hành ngày 2026-09-02: paid ledger có **271 PDF / 14.947 trang tiếng
Việt**, chỉ thuộc đúng 19 ngân hàng mới nêu trên; giao với
`ACB/BID/CTG/HDB/MBB/VCB/VIB/VPB` là **rỗng**. Điều kiện này phải được kiểm tra
lại ở mỗi checkpoint. Không được gộp bất kỳ inventory hoặc plan năm 2024 vào
ledger hiện hành.

#### Tiến độ paid frontier — 18:18 UTC ngày 2026-09-02

- **Phạm vi dùng để tính:** 271 PDF / 14.947 trang tiếng Việt của 19 ngân hàng
  mới, chỉ gồm **205 PDF kỳ 2025 và 66 PDF kỳ 2026**; số PDF kỳ 2024 là **0**.
- **Đã bắt đầu xử lý:** 124/271 PDF (**45,8%**), tương ứng 6.443/14.947 trang
  thuộc các PDF đã vào luồng (**43,1%**).
- **Đã có Gemini JSON hợp lệ trong store:** 6.008/14.947 trang (**40,20%**),
  thuộc 123 PDF.
- **Đã hoàn tất trọn PDF:** 37/271 PDF (**13,7%**). Phần còn lại gồm 25 PDF chỉ
  cần retry một số trang, 62 PDF đã hết lượt thường và đang chờ sửa đúng trang,
  cùng 147 PDF chưa bắt đầu.
- Các con số tiến độ trước đó dùng mẫu số 279 PDF / 15.335 trang cũng **không
  bao gồm PDF năm 2024**. Chênh lệch với mẫu số hiện tại là do đợt kiểm tra trực
  quan sau đó loại 7 PDF hoàn toàn bằng tiếng Anh và 1 bản ABB trùng nội dung.
  Ngày `31/12/2024` xuất hiện trong JSON chỉ là kỳ so sánh của báo cáo
  2025/2026, không phải một PDF năm 2024 và không được tính vào paid frontier.
- Bảng chi tiết theo từng mã được lưu tại
  [`GEMINI_19_BANK_PROGRESS.md`](GEMINI_19_BANK_PROGRESS.md).

### Cổng chỉ gửi phần tiếng Việt của PDF

Xác nhận của người dùng ngày 2026-09-02: OCB có những PDF ghép bản tiếng Việt
và bản tiếng Anh trong cùng một file; **không gửi phần tiếng Anh cho Gemini**.
Từ checkpoint này:

- mọi PDF trên 100 trang phải được kiểm tra ranh giới ngôn ngữ trước khi đưa
  vào paid ledger;
- mọi PDF OCB phải được kiểm tra, kể cả file không quá 100 trang;
- số trang dưới đây là **trang vật lý của file PDF**, không phải số trang in ở
  chân trang;
- `run`, `resume` và `repair` chỉ được phép nhắm các trang trong cột “Trang được
  gửi”; file chưa có kết luận ngôn ngữ phải fail closed trước provider request;
- page tiếng Việt đã có JSON hợp lệ tiếp tục dùng cache; việc thay frontier
  không cho phép gửi lại page đã hoàn tất.

#### PDF trên 100 trang đã kiểm tra

| Ngân hàng | Tên file PDF | Tổng trang | Trang được gửi | Kết luận dễ đọc |
| --- | --- | ---: | ---: | --- |
| OCB | BCTC Công ty mẹ Kiểm toán năm 2025.pdf | 202 | 1–102 | Trang 102 là trang tiếng Việt cuối; trang 103 bắt đầu bản tiếng Anh |
| OCB | BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf | 200 | 1–101 | Trang 101 là trang tiếng Việt cuối; trang 102 bắt đầu bản tiếng Anh |
| OCB | BCTC Hợp nhất Kiểm toán năm 2025.pdf | 206 | 1–104 | Trang 104 là trang tiếng Việt cuối; trang 105 bắt đầu bản tiếng Anh |
| OCB | BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf | 202 | 1–102 | Trang 102 là trang tiếng Việt cuối; trang 103 bắt đầu bản tiếng Anh |
| STB | BCTC Công ty mẹ Kiểm toán năm 2025.pdf | 101 | 1–101 | Tiếng Việt đến trang cuối, giữ toàn bộ |
| STB | BCTC Hợp nhất Kiểm toán năm 2025.pdf | 108 | 1–108 | Tiếng Việt đến trang cuối, giữ toàn bộ |
| STB | BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf | 104 | 1–104 | Tiếng Việt đến trang cuối, giữ toàn bộ |
| TCB | BCTC Hợp nhất Kiểm toán năm 2025.pdf | 104 | 1–103 | Trang 103 kết thúc báo cáo tiếng Việt; trang 104 là trang giới thiệu tiếng Anh của EY |
| TPB | BCTC Hợp nhất Kiểm toán năm 2025.pdf | 108 | 1–108 | Tiếng Việt đến trang cuối, giữ toàn bộ |

#### Các PDF OCB dưới 100 trang đã kiểm tra

| Tên file PDF | Tổng trang | Trang được gửi | Kết luận |
| --- | ---: | ---: | --- |
| BCTC Công ty mẹ quý 1 năm 2025.pdf | 78 | 1–40 | Trang 41 bắt đầu bản tiếng Anh |
| BCTC Công ty mẹ quý 2 năm 2025.pdf | 79 | 1–40 | Trang 41 bắt đầu bản tiếng Anh |
| BCTC Hợp nhất quý 1 năm 2025.pdf | 79 | 1–40 | Trang 41 bắt đầu bản tiếng Anh |
| BCTC Hợp nhất quý 2 năm 2025.pdf | 79 | 1–40 | Trang 41 bắt đầu bản tiếng Anh |
| BCTC Công ty mẹ quý 1 năm 2026.pdf | 78 | 1–40 | Trang 41 bắt đầu bản tiếng Anh |
| BCTC Hợp nhất quý 1 năm 2026.pdf | 78 | 1–40 | Trang 41 bắt đầu bản tiếng Anh |
| BCTC Công ty mẹ quý 3 năm 2025.pdf | 41 | 1–41 | Tiếng Việt đến trang cuối |
| BCTC Công ty mẹ quý 4 năm 2025.pdf | 42 | 1–42 | Tiếng Việt đến trang cuối |
| BCTC Hợp nhất quý 3 năm 2025.pdf | 41 | 1–41 | Tiếng Việt đến trang cuối |
| BCTC Hợp nhất quý 4 năm 2025.pdf | 43 | 1–43 | Tiếng Việt đến trang cuối |
| BCTC Công ty mẹ quý 2 năm 2026.pdf | 41 | 1–41 | Tiếng Việt đến trang cuối |
| BCTC Hợp nhất quý 2 năm 2026.pdf | 42 | 1–42 | Tiếng Việt đến trang cuối |

Sau khi chỉ áp dụng bảng cắt phần tiếng Anh nối cuối ở trên, frontier trung gian
vẫn có 279 PDF nhưng giảm từ 15.968 xuống **15.335 trang được phép gửi**;
**633 trang tiếng Anh bị loại**.
Đợt rà trực quan toàn bộ tên file và các cặp đáng ngờ sau đó loại thêm **7 PDF
hoàn toàn bằng tiếng Anh (360 trang)** và **1 PDF ABB trùng nội dung (28
trang)**. Paid frontier cuối cùng vì vậy là **271 PDF / 14.947 trang**. JSON đã
nhận của tài liệu bị loại chỉ được giữ làm bằng chứng kỹ thuật, không được tính
tiến độ, map dữ liệu hoặc cấp quyền gửi tiếp.

Đây là denominator bảo vệ của giai đoạn 2025-current: 8.947 trang JSON cũ được
tái sử dụng và 14.947 trang paid frontier tiếng Việt, tương ứng **23.894
trang**. Năm 2024 nằm ngoài phạm vi và không được cộng vào denominator này.
Mọi plan cũ 15.968 hoặc 15.335 trang không được resume.

#### Tài liệu đã loại toàn bộ sau kiểm tra trực quan

- BAB: `BCTC Consolidated 2025_Audited.pdf` và
  `BCTC Separate 2025_Audited.pdf` — bản tiếng Anh, đã có bản tiếng Việt tương
  ứng.
- KLB: `bao-cao-tai-chinh-giua-nien-do-q4.2025-hop-nhat-_ta.pdf` và
  `bao-cao-tai-chinh-giua-nien-do-q4.2025-rieng_ta.pdf` — bản tiếng Anh.
- LPB: `BCTC 31.12.2025 E color.pdf` — bản tiếng Anh.
- VAB: `BCTC HOP NHAT QUY 2.2025 TANH_0001-da nen.pdf` — bản tiếng Anh.
- VBB: `28-BCTC-Q1_2026-hopnhat-E.pdf` — bản tiếng Anh.
- ABB: `BCTC Hợp nhất quý 4 năm 2025__d2af87de__phpaedoan-...pdf` — bản trùng
  nội dung với file ABB Q4/2025 được giữ lại; khác biệt chỉ là lớp chữ ký số ở
  trang đầu.

## 1. Provider và credential

- **Operational override 2026-08-27:** hai Google API key đã hết ngân sách.
  Từ checkpoint này, mọi request OCR mới phải đi duy nhất qua OpenRouter với
  model `google/gemini-3.7-flash`, provider
  `google-vertex/global/flex`; Google standard, Google Batch và mọi Google
  fallback đều bị vô hiệu hóa. CLI cũ có thể vẫn nhận `--google-key-file` để
  tương thích ngược, nhưng `--openrouter-only` và child
  `--google-standard-mode disabled` là bắt buộc. Không được thử lại Google để
  dò quota.
- Page-version Google đã hoàn thành trước override vẫn được giữ làm dữ liệu
  bất biến, không OCR lại chỉ vì đổi route. Khi có nhiều version hợp lệ cùng
  source/image/prompt/schema, manifest chọn theo thứ tự đã niêm phong
  `OPENROUTER/flex → GOOGLE_GEMINI_BATCH_API/batch →
  GOOGLE_GEMINI_API/standard`; thứ tự này chỉ chọn dữ liệu đã có và tuyệt đối
  không cấp quyền gọi Google.
- Giai đoạn thử prompt/case khó dùng OpenRouter trước.
- Model thử nghiệm chính là `google/gemini-3.7-flash`.
- OpenRouter phải khóa đúng provider Google Vertex Flex
  `google-vertex/global/flex`, tắt provider/model fallback và yêu cầu provider hỗ
  trợ đầy đủ tham số. Không được tự chuyển sang host rẻ, model lượng tử hóa hoặc
  model khác.
- Hai key Google trong `docs/experiments/gemma.txt` chỉ còn là credential lịch
  sử, không được gọi trong lượt chạy hiện hành và không bao giờ được chuyển qua
  OpenAI/OpenRouter. Việc từng kiểm tra key đuôi `UrJOHw` bằng `generateContent`
  không còn là quyền gọi lại sau override.
- Kế hoạch cũ chạy song song Google Batch/OpenRouter Batch đã kết thúc khi quota
  Google cạn và image Batch OpenRouter không cung cấp đường ảnh dùng được.
  OpenRouter Google Vertex Flex đồng bộ, stateless và bounded-concurrency là
  route corpus duy nhất hiện tại. Semantic JSON sai chỉ được đổi prompt theo
  receipt; không đổi provider/model.
- Batch phải resumable theo batch/document/page: lưu batch ID, request ID,
  provider, credential slot ẩn danh, trạng thái poll, request thành công/thất
  bại, token và chi phí; không submit lại job khi process khởi động lại.
- Batch failure phải được phân tuyến từ receipt có kiểu ngay ở cấp page:
  `RECITATION → scope`, lỗi JSON/semantic → `items`, lỗi transport/provider →
  prompt mặc định và được phép chuyển OpenRouter ↔ Google theo policy. Một
  upload bị ngắt trước khi có JSONL/manifest/submission response phải được dời
  nguyên vẹn vào quarantine có content hash rồi mới tạo attempt sạch; không xóa
  receipt upload và không suy đoán rằng một batch đã hoặc chưa được submit khi
  đã vượt qua ranh giới này.
- Nếu đúng page vẫn thất bại semantic sau `items` vì vector hàng không khớp số
  cột, cho phép đúng một retry `balanced` có prompt hash riêng để bắt model giữ
  `null` cho ô thật sự trống. Không tự chèn placeholder, không nới kiểm tra độ
  rộng hàng và không OCR lại các page đã hợp lệ.
- Không in, commit, upload hoặc ghi key vào artifact/log/database. File key phải
  có mode `0600`.

## 2. Ảnh đầu vào

- Chỉ dùng 200 hoặc 300 DPI. Không dùng DPI thấp hơn cho pilot hay corpus.
- Mặc định 300 DPI cho PDF scan, chữ nhỏ hoặc mờ. Chỉ dùng 200 DPI khi trang
  born-digital/scan rõ đã qua kiểm tra đọc được.
- Ảnh gửi LLM phải là **toàn bộ trang vật lý**, không crop theo bảng, vùng chữ
  hay `CropBox` lỗi của PDF. Renderer lấy toàn `MediaBox` và chỉ được mở rộng
  canvas có giới hạn khi chứng minh có nét vẽ thật nằm ngoài box; tọa độ chỉ
  dùng để phục hồi canvas, không được dùng làm authority bảng/hierarchy/family.
- Mỗi kết quả phải bind SHA-256 PDF, số trang vật lý, SHA-256 ảnh, DPI, kích
  thước pixel và MIME type.
- Manifest hoàn tất của tài liệu phải bind đúng SHA-256 ảnh nguyên trang của
  từng page-version. Kết quả OCR cũ sinh từ ảnh bị cắt hoặc image SHA khác phải
  được coi là stale và không được tái sử dụng.
- Trước khi chạy toàn corpus phải thử trọn một PDF có nhiều loại trang: báo cáo
  chính, thuyết minh/bảng, continuation và trang không liên quan.

## 3. Prompt và JSON

- Prompt phải ngắn, rõ, schema-blind và có cùng một contract ổn định.
- **Operational override 2026-08-27 — prompt cố định, thuật toán bao quát:**
  không được đẩy logic mapping, graph, phương trình, điều kiện family hoặc việc
  chép lại dữ liệu ngoài scope vào prompt. Gemini chỉ đọc cấu trúc/ô nhìn thấy
  theo một schema nhỏ và ổn định; code phải chuẩn hóa các biểu diễn tương đương,
  chiếu output lên JSON nguồn bất biến rồi tự xử lý hierarchy, lane, period,
  unit, graph và phương trình. Với repair theo vùng, model chỉ trả các
  observation mục tiêu dạng `cell_id + source_text`; mọi ô ngoài allowlist luôn
  lấy nguyên từ DB và không được bắt Gemini echo byte-exact.
- Chỉ duy trì một tập nhỏ prompt version được khai báo trước, dùng tự động theo
  typed failure: mặc định `simple`; thiếu khoản mục dùng `items`; lệch độ rộng
  hàng/cột dùng `balanced`; thiếu owner/header/continuation mới dùng một prompt
  bổ sung context có giới hạn. Không được ngồi canh rồi sửa prompt ad hoc theo
  từng bank/file/page, không retry chỉ để ép một serialization ưa thích, và
  không đổi prompt khi output đã đủ dữ liệu để code map chính xác.
- Validator cứng chỉ bảo vệ dữ liệu thực sự cần để map: JSON parse/type, target
  bắt buộc, độ đầy đủ hàng/cột cần thiết, xung đột quan sát và source binding.
  Khác newline/whitespace/header placement, dash spelling, field mềm hoặc thay
  đổi ngoài scope phải được canonicalizer/projection xử lý và lưu diagnostic,
  không làm mất mapping đúng. Graph và phương trình xác minh projection sau đó;
  validator không được biến thành một layout parser thứ hai.
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
  tổng hợp phải bind đúng page-version được chọn. Retry phải phân loại theo từng
  page: `RECITATION` dùng prompt `scope`; JSON/semantic `UNRESOLVED_PAGE` dùng
  prompt `items`; lỗi provider khác mới dùng lại prompt mặc định. Mỗi biến thể
  có artifact/cache key riêng và bị giới hạn số lần thử.
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
- Không tạo snapshot database theo từng prompt, attempt, job hoặc từng biến thể
  output của Gemini. Một run chỉ được dùng một source view bất biến và một cặp
  database staging dùng chung (page + results); chỉ publish cặp staging sau khi
  toàn bộ frontier đã được thuật toán chuẩn hóa, graph/mapping xác minh và đóng
  đầy đủ. Retry chỉ thêm observation/receipt có version, không nhân bản toàn bộ
  database.
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
- Khi chạy nhiều request song song, mỗi future/page hoàn tất phải ghi ngay raw
  response, canonical JSON, telemetry và database; không giữ cả tài liệu trong
  RAM rồi mới ghi cuối cùng. Khởi động lại phải tiếp tục từ page/batch ledger và
  không gửi lại page đã có manifest hiện hành.
- Retry provider chỉ dành cho lỗi chưa tính phí hoặc retryable có kiểu rõ ràng.
  Lỗi JSON/semantic chỉ được thử đúng một projection prompt đã khai báo
  (`items`) để kiểm tra tính đầy đủ; không lặp cùng prompt/provider để che lỗi,
  và nếu vẫn sai phải giữ `UNRESOLVED_PAGE` cùng toàn bộ chi phí/attempt.
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
