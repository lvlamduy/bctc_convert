# Yêu cầu người dùng và chiến lược mapping — bàn giao VPS/laptop

Ngày 2026-09-05. Đây là chiến lược và kế hoạch kiểm chứng, không phải chứng nhận
family đã hoàn thành. Phạm vi production: 27 ngân hàng, năm báo cáo **2025 đến
hiện tại**. Cột so sánh 2024 trong báo cáo 2025 vẫn là bằng chứng nguồn; không
tạo thêm hàng đợi production/Gemini cho báo cáo năm 2024.

## Yêu cầu mới của người dùng

- Tối đa hoá mapping những khoản mục rõ ràng vào schema/template; không để dữ
  liệu đọc rõ bị bỏ lại chỉ vì tên hoặc cách trình bày khác.
- Sub-agent phải tự xem PDF thật, kiểm tra biến thể và tối ưu thuật toán; không
  chỉ chạy test mô phỏng hoặc đọc kết quả do agent khác mô tả.
- Hiểu quan hệ cha–con, trước–sau, các dòng lân cận và phạm vi nhóm. Khoản con
  có thể đi vào khoản gộp phù hợp; nhiều khoản tách biệt có thể cộng thành khoản
  gộp khi bằng chứng đầy đủ và schema cho phép.
- Bucket “khác” phải tiếp nhận khoản rõ ràng thuộc đúng nhóm nhưng không có
  loại riêng trong template; không dùng làm nơi đổ dữ liệu chưa hiểu.
- Bao quát bảng nối trang và thay đổi trình bày bằng quy tắc cấu trúc dùng
  chung, không hardcode ngân hàng, ordinal hoặc số trang.
- Dùng tối đa sáu sub-agent hữu ích song song với root, không nhiều writer cho
  một file; tiếp tục trao đổi với laptop và push Git/S3 sau mỗi family.
- Gửi các yêu cầu này cùng chiến lược cho laptop, yêu cầu xác nhận đã đọc.

## Kiến trúc và nguyên tắc không thay đổi

PDF → Gemini JSON → xác thực/đánh giá → SQLite/database. Giữ raw observations
và provenance kể cả khi chưa có mapping. Không tái đưa PPOCR6, VietOCR,
geometry OCR, DeepSeek OCR, Gemma hoặc cache/model cũ vào đường production.
Không gọi provider trong vòng hiện tại. Không đưa secrets/passphrase vào Git
hoặc hộp thư. PDF/corpus đã backup chỉ được tham chiếu, không upload trùng.

Tách giá trị **in trên nguồn** khỏi giá trị **tổng hợp từ các thành phần**.
Một phép cộng phải có danh sách thành phần và nguồn từng ô; cùng kỳ, đơn vị,
phạm vi báo cáo và nội hàm; chứng minh không trùng hoặc chứa nhau. Không giả
một tổng tính toán là một ô PDF, không cộng cả parent lẫn children, không suy
thành phần còn thiếu bằng phép trừ, không biến ô trắng/null thành số 0, không
suy đơn vị theo độ lớn. Dấu gạch nhìn thấy trên PDF cần receipt sửa nguồn đúng
quy trình nếu Gemini làm mất, không sửa ngầm raw JSON.

## Chiến lược triển khai có kiểm chứng

1. Lập danh mục dòng/ô định lượng ở mỗi vùng nguồn: mapped, derived-component,
   source-only có lý do, unresolved hoặc không áp dụng. Theo dõi cả coverage
   khoản mục/ô và độ chính xác; số document READY không thay thế coverage.
2. Nhận diện owner và cây dòng từ nhãn, heading, parent/sibling, thứ tự và
   hàng lân cận; tách “khác” theo đúng parent. Nhãn đồng nghĩa cần bằng chứng
   schema và ngữ cảnh, không mở catch-all toàn cục.
3. Phân biệt breakdown đầy đủ với disclosure một phần, nhất là “Trong đó”.
   Parent đã in rõ không phải sai chỉ vì các dòng “Trong đó” cộng chưa đủ.
   Không tạo phần còn thiếu hoặc bỏ các kiểm tra tổng khác. Giữ quan hệ này
   thành bằng chứng có thể tái dựng, không chỉ xoá lý do UNRESOLVED.
4. Ghép continuation dựa trên nguồn đã xác thực: trật tự trang, owner, cột/kỳ/
   đơn vị, context kế thừa và dấu hiệu chuyển nhóm. Xử lý header lặp/mất, cột
   đổi thứ tự, nhãn bị tách, parent nằm trang trước và footer/total lặp. Không
   ghép chỉ vì hai trang kề nhau; nhiều ứng viên hoặc bằng chứng xung đột phải
   có lý do unresolved rõ ràng.
5. Với phép tổng hợp mới, kiểm tra khả năng biểu diễn derived-value/provenance
   của schema/store trước khi sửa. Nếu engine hiện tại chỉ hỗ trợ ô in, không
   giả source locator hoặc lén nới shared engine để tăng số mapping.
6. Viết regression từ PDF đã xem + ca đối nghịch: đổi thứ tự cột, Q so với YTD,
   đơn vị xung đột, parent reset, hai loại “khác”, subtotal một phần/đầy đủ,
   duplicated total, missing/null/dash và ambiguous continuation.
7. Chạy diagnostic mới từ exact code/config và frozen source, kiểm replay và
   denominator độc lập full271/common204. Không dùng kết quả cũ như bằng chứng
   hiện tại. Manual PDF audit phải dựa trên trang thực sự đã xem.
8. Sau sửa: focused/shared regression, audit/replay/coverage, result DB riêng,
   SQLite integrity, ledger, Git worker push và S3 immutable/readback. Chỉ đóng
   family khi toàn bộ gate yêu cầu PASS; WIP luôn ghi là WIP.

Không thể chứng minh “mọi cách trình bày” chỉ từ tập đã xem. Phải kiểm trên
báo cáo chưa dùng phát triển và theo dõi rõ source-visible items còn chưa map.

## Bằng chứng mới, chưa phải full-corpus acceptance

- Nhóm A: trực tiếp xem 9 trang của BVB/EIB/STB/VAB. Bốn subtotal bị chặn trong
  baseline là printed parent kèm “Trong đó” một phần, chưa chứng minh sai tổng.
  Template cũng có disclosure không đầy đủ. STB “Chi trang phục giao dịch”
  22.554/23.076 là ứng viên rõ cho employee Other (1211); cần sửa và test theo
  nghĩa schema, không theo ngân hàng. Năm ô null có dấu gạch trên PDF cần
  receipt sửa nguồn riêng.
- Nhóm B: trực tiếp xem 11 trang của bảy tài liệu KLB/PGB/STB. Probe riêng từng
  document trên code hiện tại cho 7 READY/87 mappings; không thay kết quả
  full271/common204. KLB có children ADMIN nối trang; “khác” ASSET khác “khác”
  ADMIN. STB có dòng gộp payroll+uniform, không được map toàn bộ thành payroll
  hoặc backsolve để chia. PGB có cột ngày cần phân biệt quarter/YTD.
- Patch F36 visible owner + invalid unit đã sửa NOT_OBSERVED → UNRESOLVED và
  qua 165 focused tests Python 3.12 cùng sáu reproduction. Đang review độc lập,
  chưa replay corpus hoặc coi family terminal.

## Phối hợp hiện tại

VPS chỉ sửa F36 trên `codex/f36-operating-expense-vps`; laptop giữ F39;
F37 read-only/reserved. Shared evaluator và generic runner vẫn đóng băng.
Không push nhánh chung hoặc tự đổi contract. Formal laptop join còn pending;
ACK sở hữu không thay gate restore/release. Các chuẩn bị code/test và probe
riêng không phải nghiệm thu hoặc quyền ghi authority database.

Laptop event 07:06 UTC: Linux/Python 3.12 đã hoạt động, báo 221 focused/shared
tests PASS và output restore PASS, nhưng scan archive dev-shm dừng vì chứa
đường dẫn tài liệu GEMMA cũ trái chính sách loại trừ. Đây là báo cáo từ laptop,
chưa là xác minh độc lập của VPS; không có bằng chứng hash archive hỏng và không
có quyền tự bỏ gate/sửa migration. VPS sẽ kiểm tra bằng chứng riêng và phản hồi.

Hộp thư S3: `s3://test-s3-duylv/bctc-ai/coordination/2025-current/v1/events/`.
Mỗi tin/artifact mới là immutable, có SHA-256, VersionId và readback. Yêu cầu
laptop ACK đúng event/hash, nêu điểm đồng ý/khác biệt và kế hoạch áp dụng F39
khi preflight cho phép. Upload thành công không có nghĩa laptop đã đọc; S3
không tự đánh thức phiên đã dừng. Không suy quyền mới từ im lặng.
