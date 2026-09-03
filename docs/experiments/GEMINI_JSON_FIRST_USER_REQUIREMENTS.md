# Gemini JSON-first — yêu cầu vận hành của người dùng

Tài liệu này là checklist bắt buộc cho nhánh làm lại dữ liệu báo cáo tài chính
bằng Gemini. Khi nội dung hội thoại, code hoặc tài liệu cũ mâu thuẫn với các yêu
cầu dưới đây, phải dừng và cập nhật thiết kế trước khi tiếp tục chạy tốn phí.

## 0. Phạm vi mở rộng 27 ngân hàng — checkpoint 2026-09-01

- Khoảng thời gian chính thức của đợt mở rộng là **từ Quý 1/2025 đến thời
  điểm hiện tại**. Không đưa năm 2024 vào hàng đợi Gemini của đợt này.
- **Tái xác nhận 2026-09-03:** thao tác đọc/kiểm kê file năm 2024 ở local không
  phải quyền gửi Gemini. Không được đưa bất kỳ PDF/page năm 2024 nào vào plan,
  task, retry hoặc request trả phí của đợt hiện hành.
- Tổng universe gồm 27 ngân hàng. Tám ngân hàng đã hoàn tất JSON là **ACB,
  BID, CTG, HDB, MBB, VCB, VIB và VPB**. Các PDF/page đã có manifest hiện hành
  của tám ngân hàng này phải tái sử dụng từ store/cache bất biến; **không được
  gửi lại Gemini/OpenRouter**.
- Mười chín ngân hàng mới được phép vào paid provider frontier là **ABB, BAB,
  BVB, EIB, KLB, LPB, MSB, NAB, NVB, OCB, PGB, SGB, SHB, SSB, STB, TCB, TPB,
  VAB và VBB**.
- Ma trận kiểm kê có thể hiển thị đủ 27 ngân hàng để con người theo dõi, nhưng
  corpus plan phải tách rõ `REUSE_EXISTING_GEMINI_JSON` cho tám ngân hàng cũ và
  `NEW_VERTEX_FLEX_FRONTIER` cho mười chín ngân hàng mới. Một plan chứa ngân
  hàng cũ trong paid frontier phải fail-closed trước request đầu tiên.
- Nếu phát hiện PDF mới của một trong tám ngân hàng chưa có trong manifest cũ,
  không được tự gọi Gemini. Trường hợp đó phải ghi riêng vào inventory và chờ
  người dùng cấp quyền mở rộng frontier.
- Mọi request API mới chỉ được đi qua **OpenRouter → Google Vertex Flex**, model
  `google/gemini-3.7-flash`, provider `google-vertex/global/flex`, service tier
  `flex`. Direct Google, Google Standard, Google Batch và mọi provider/model
  fallback đều bị cấm.
- **Bổ sung Agy 2026-09-03:** được dùng Agy trên VPS song song cho đúng PDF/page
  chưa có JSON, nhưng phải claim task khỏi supervisor Vertex Flex trước khi gửi.
  Agy dùng cùng ảnh 300 DPI, prompt, JSON Schema và validator; effort đầu tiên
  bắt buộc là `gemini-3.7-flash-low`. Chỉ output lỗi schema/completeness hoặc
  `UNRESOLVED_PAGE` mới được thử Medium rồi High. Cả ba không đạt thì chỉ page
  lỗi quay về Vertex Flex. Không gửi lại page đã đạt, không gắn nhãn Agy thành
  Vertex Flex, và lưu rõ provider/model/effort/token thực tế. Gemini 3.8 Flash
  High chỉ làm reviewer read-only, không được tạo JSON đưa vào corpus.
- **Tạm dừng Agy theo quota ngày:** lúc `2026-09-03 05:24 UTC`, người dùng xác
  nhận Agy đã chạm giới hạn ngày và yêu cầu chờ **3 giờ 34 phút**. Không được
  gọi Agy, kể cả health-check, trước `2026-09-03 08:58 UTC`. Trong thời gian
  này chỉ OpenRouter Vertex Flex tiếp tục frontier. Sau mốc trên, Agy được mở
  lại từ `gemini-3.7-flash-low`; không dùng Medium/High nếu Low chưa trả lỗi
  theo đúng điều kiện escalation ở trên.
- **Thứ tự thử Gemini 3.8 Flash:** khi được người dùng yêu cầu canary trang lỗi,
  phải thử `low → medium → high`; tuyệt đối không nhảy từ Low thẳng lên High.
  Canary năm trang ngày 2026-09-03 được lưu ngoài production store: Low đạt
  1/5; Medium đạt cả 4/4 trang Low còn lỗi; High chỉ đạt 2/4, với chi phí
  0,212226 USD so với 0,082774 USD của Medium trên cùng bốn trang. Kết quả này
  chỉ làm bằng chứng chọn escalation; chưa cấp quyền đổi reader toàn corpus từ
  3.7 Low sang 3.8 hoặc ghi đè page JSON hiện hành.
- Chính sách Git, snapshot/restore S3 và backup Codex tiếp tục giữ nguyên; không
  được vì mở rộng corpus mà bỏ qua checkpoint hoặc ghi đè artifact cũ.
- Inventory byte/page đã xác thực tại checkpoint này gồm **140 PDF / 8.947
  trang** của tám ngân hàng cũ chỉ để tái sử dụng, và **271 PDF / 14.947 trang**
  của mười chín ngân hàng mới trong frontier disjoint. Tổng này phải
  được kiểm tra lại nếu nguồn thay đổi; tuyệt đối không biến 140 PDF cũ thành
  request mới chỉ vì chạy lại inventory hoặc đổi manifest trình bày.

## 1. Provider và credential

- **Operational override 2026-08-27:** hai Google API key đã hết ngân sách.
  Từ checkpoint này, mọi request API mới phải đi duy nhất qua OpenRouter với
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
  OpenRouter Google Vertex Flex đồng bộ và worker Agy có task lease tách biệt là
  hai execution route hiện hành. Semantic JSON sai ở Agy được tăng effort đúng
  `Low → Medium → High`; sau đó mới trả riêng page lỗi về retry Vertex Flex theo
  receipt. Hai route không bao giờ được sở hữu cùng một PDF/page đồng thời.
- Batch phải resumable theo batch/document/page: lưu batch ID, request ID,
  provider, credential slot ẩn danh, trạng thái poll, request thành công/thất
  bại, token và chi phí; không submit lại job khi process khởi động lại.
- Batch failure phải được phân tuyến từ receipt có kiểu ngay ở cấp page:
  `RECITATION → scope`, lỗi JSON/semantic → `items`, lỗi transport/provider →
  retry có giới hạn trên đúng OpenRouter Google Vertex Flex với prompt mặc định;
  không được chuyển sang Google trực tiếp hoặc provider khác. Một
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
- **Kiểm tra nguồn SSB ngày 2026-09-03:** hai file Vietstock dưới đây có tổng
  cộng 22 trang bị mất nội dung ở hai mép ngay trong các ảnh JPEG nhúng:
  - `SSB/2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf`: trang vật lý
    39, 40, 46, 53, 58, 59, 60, 61, 63 và 64;
  - `SSB/2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf`: trang vật lý
    41, 42, 48, 56, 61, 62, 63, 64, 66, 67, 69 và 70.
  `CropBox` trùng `MediaBox`; mỗi trang lỗi chứa ba dải JPEG 1.190 pixel bề
  ngang nhưng chỉ còn tổng 1.203 pixel chiều dọc, so với 1.695 pixel ở trang
  bình thường cùng loại. Nội dung chữ đã cụt ngay trong JPEG gốc, vì vậy mở
  rộng canvas hoặc đổi DPI không thể khôi phục phần đã mất. Không gửi lại các
  ảnh này qua Agy/OpenRouter chỉ để thử vận may. Quét cấu trúc ảnh nhúng của
  toàn bộ 271 PDF trong corpus 2025-hiện tại không tìm thấy PDF nào khác có
  cùng mẫu hỏng này; bốn cảnh báo TCB là trang mục lục/bố cục ảnh khác và không
  bị cắt nội dung.
- Nguồn chính thức của SeABank cho hai báo cáo trên lần lượt là
  `https://cloud-cdn.seabank.com.vn/seabank-web/FS%20Separate%20SeABank_VN.pdf`
  và
  `https://cloud-cdn.seabank.com.vn/seabank-web/FS%20Conso%20SeABank_VN.pdf`.
  Bản riêng lẻ có 64 trang đầy đủ (54 dọc, 10 ngang); bản hợp nhất có 70 trang
  đầy đủ (58 dọc, 12 ngang). Tất cả đều là ảnh nguyên trang. Phải đăng ký mỗi
  bản như một source revision mới và giữ nguyên bản Vietstock lỗi để truy vết;
  tuyệt đối không ghi đè bytes hoặc gắn JSON đọc từ source mới vào page identity
  của source cũ. Các báo cáo quý 2 năm 2025 chỉ được dùng làm đối chiếu bổ sung,
  không tự động thay thế báo cáo soát xét.

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
