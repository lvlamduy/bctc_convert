# Tiến độ Gemini của 19 ngân hàng mới

Checkpoint: **23:51 UTC ngày 02/09/2026**.

## Phạm vi được tính

- Chỉ tính báo cáo từ **Quý 1/2025 đến thời điểm hiện tại**.
- Gồm **205 PDF / 11.636 trang kỳ 2025** và **66 PDF / 3.311 trang
  kỳ 2026**, tổng cộng **271 PDF / 14.947 trang tiếng Việt**.
- Số PDF kỳ 2024 trong hàng đợi này là **0**. Ngày `31/12/2024` nếu xuất hiện
  chỉ là cột so sánh trong báo cáo 2025/2026.
- Đây là khóa vận hành: không tạo task, không gửi Gemini và không cộng vào mẫu
  số tiến độ bất kỳ PDF kỳ 2024 nào.
- Không tính ACB, BID, CTG, HDB, MBB, VCB, VIB và VPB vì tám ngân hàng này đã
  có Gemini JSON và chỉ được tái sử dụng, không gửi lại.

## Tiến độ theo ngân hàng

| Mã ngân hàng | PDF | Trang tiếng Việt | Trang JSON hợp lệ | Hoàn thành theo trang | PDF đã bắt đầu | PDF hoàn tất | PDF đang chạy | PDF cần retry | PDF chờ sửa trang lỗi | PDF chưa bắt đầu |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ABB | 12 | 453 | 414 | 91,39% | 12 | 1 | 0 | 0 | 11 | 0 |
| BAB | 10 | 441 | 420 | 95,24% | 10 | 2 | 0 | 0 | 8 | 0 |
| BVB | 14 | 742 | 571 | 76,95% | 14 | 1 | 0 | 0 | 13 | 0 |
| EIB | 16 | 703 | 687 | 97,72% | 16 | 7 | 0 | 0 | 9 | 0 |
| KLB | 16 | 680 | 657 | 96,62% | 16 | 3 | 0 | 3 | 10 | 0 |
| LPB | 7 | 607 | 598 | 98,52% | 7 | 2 | 0 | 2 | 3 | 0 |
| MSB | 16 | 998 | 981 | 98,30% | 16 | 8 | 0 | 1 | 7 | 0 |
| NAB | 16 | 853 | 819 | 96,01% | 16 | 8 | 0 | 4 | 4 | 0 |
| NVB | 16 | 864 | 790 | 91,44% | 16 | 5 | 0 | 7 | 4 | 0 |
| OCB | 16 | 899 | 74 | 8,23% | 1 | 0 | 0 | 0 | 1 | 15 |
| PGB | 7 | 357 | 0 | 0,00% | 0 | 0 | 0 | 0 | 0 | 7 |
| SGB | 14 | 703 | 0 | 0,00% | 0 | 0 | 0 | 0 | 0 | 14 |
| SHB | 16 | 729 | 0 | 0,00% | 0 | 0 | 0 | 0 | 0 | 16 |
| SSB | 16 | 1.063 | 0 | 0,00% | 0 | 0 | 0 | 0 | 0 | 16 |
| STB | 16 | 972 | 0 | 0,00% | 0 | 0 | 0 | 0 | 0 | 16 |
| TCB | 16 | 1.293 | 0 | 0,00% | 0 | 0 | 0 | 0 | 0 | 16 |
| TPB | 16 | 1.080 | 0 | 0,00% | 0 | 0 | 0 | 0 | 0 | 16 |
| VAB | 15 | 737 | 0 | 0,00% | 0 | 0 | 0 | 0 | 0 | 15 |
| VBB | 16 | 773 | 0 | 0,00% | 0 | 0 | 0 | 0 | 0 | 16 |
| **Tổng** | **271** | **14.947** | **6.011** | **40,22%** | **124** | **37** | **0** | **17** | **70** | **147** |

So với checkpoint trước, mẫu số giảm 8 PDF / 388 trang sau kiểm tra trực quan:
7 PDF hoàn toàn bằng tiếng Anh được loại khỏi paid frontier và 1 PDF ABB là
bản trùng nội dung với một PDF đã giữ lại. JSON đã nhận của các tài liệu bị
loại vẫn được giữ làm bằng chứng kỹ thuật, nhưng không được tính vào tiến độ và
không được dùng để map dữ liệu.

## Xác nhận về năm 2024

- Tiến độ trong bảng này và tất cả mốc tiến độ đã báo cho đợt mở rộng 19 ngân
  hàng đều **không bao gồm PDF năm 2024**. Mẫu số cũ 279 PDF / 15.335 trang chỉ
  bị điều chỉnh vì tài liệu tiếng Anh và bản trùng, không phải vì loại năm 2024.
- Hàng đợi hiện có **205 PDF kỳ 2025, 66 PDF kỳ 2026 và 0 PDF kỳ 2024**.
- Dữ liệu mang ngày `31/12/2024` vẫn có thể xuất hiện trong JSON vì đó là cột
  so sánh của một PDF kỳ 2025 hoặc 2026. Nó không làm PDF đó trở thành PDF năm
  2024 và không mở rộng phạm vi xử lý.

## Cách đọc trạng thái

- **PDF hoàn tất:** toàn bộ trang tiếng Việt trong phạm vi PDF đã có JSON hợp
  lệ và manifest toàn PDF đã được xác thực.
- **PDF đang chạy:** supervisor đang xử lý đúng frontier còn thiếu của PDF;
  các trang đã hợp lệ vẫn được lấy từ cache và không gửi lại.
- **PDF cần retry:** PDF đã chạy nhưng còn một số trang cần thử lại trong giới
  hạn thông thường; trang đã có JSON hợp lệ được lấy từ cache, không gửi lại.
- **PDF chờ sửa trang lỗi:** PDF đã hết lượt thông thường. Sau khi hàng đợi
  thường kết thúc, terminal-repair mới được phép xử lý tối đa hai lượt, chỉ
  đúng các trang lỗi có receipt.
- **PDF chưa bắt đầu:** chưa gửi bất kỳ trang nào của PDF đó.

Tỷ lệ chính để theo dõi chi phí và khối lượng là **trang JSON hợp lệ / tổng
trang tiếng Việt**. Tỷ lệ PDF hoàn tất thấp hơn vì nhiều PDF chỉ còn thiếu một
hoặc vài trang nhưng chưa được phép coi là hoàn tất.

Audit terminal-repair tại checkpoint này xác nhận 69 PDF còn quyền sửa đúng
369 page-ref đã ghi trong receipt; 23 PDF trong số đó chỉ thiếu một trang. Một PDF
BAB công ty mẹ Quý 2/2026 đã dùng đủ hai lượt và vẫn thiếu trang 3 do hai lần
HTTP 504 không có response, nên được giữ riêng là lỗi provider chứ không phải
lỗi nội dung hoặc schema.

Audit hàng đợi thông thường cũng xác nhận 17/17 PDF `NEEDS_RETRY` có receipt
hợp lệ. Frontier gồm 74 page-ref: 72 trang chưa có JSON và 2 trang đã có JSON
cơ sở nhưng cần replay/biến thể prompt để sửa lỗi cấu trúc ngữ nghĩa. Không có
PDF nào trong nhóm này đã đủ toàn bộ trang mà còn bị giữ sai trạng thái.

Sau audit, MSB công ty mẹ Quý 1/2025 đã chạy attempt cuối: trang 8–9 replay
offline thành công và chỉ trang 14 được gửi. Provider trả HTTP 200 nhưng không
có usage/response hợp lệ, nên không phát sinh cost hoặc JSON mới; task chuyển
từ `NEEDS_RETRY` sang `FAILED` và cooldown tăng tới mức trần 60 phút.

Sau cooldown, NVB hợp nhất Quý 3/2025 replay offline thành công trang 4,
rồi chỉ gửi trang 8 trong frontier còn lại. OpenRouter trả HTTP 200 nhưng
Gemini Vertex Flex kết thúc bằng lỗi 429 upstream và usage bằng 0; raw
response có nội dung dở dang nên không được ingest. PDF chuyển sang `FAILED`
với đúng năm trang cần terminal repair: 8, 10, 14, 39 và 40; không có
cost hay JSON mới.

Sau cooldown kế tiếp, scheduler claim đúng LPB Quý 1/2025 và chỉ xử lý trang
60 theo semantic frontier. Offline replay không sửa được trang này; request
Vertex Flex trả HTTP 200 nhưng choice kết thúc bằng lỗi 429 upstream,
`finish_reason=error`, toàn bộ token và cost đều bằng 0. Không có JSON được
ingest; PDF chuyển từ `NEEDS_RETRY` sang `FAILED` và trang 60 được giữ nguyên
cho terminal repair.

Sau cooldown tiếp theo, LPB kiểm toán năm 2025 được claim với frontier trang
38 và 64. Trang 64 được chấp nhận lại hoàn toàn offline từ JSON nền; chỉ trang
38 được gửi. Vertex Flex tiếp tục trả lỗi 429 upstream với usage/cost bằng 0,
không có JSON mới. PDF chuyển sang `FAILED` và chỉ trang 38 được giữ cho
terminal repair.

Sau cooldown kế tiếp, NVB riêng lẻ Quý 2/2026 chạy attempt 3 trên đúng chín
page-ref còn lỗi. Trang 8 được chấp nhận lại hoàn toàn offline và không gọi
provider. Provider chỉ đi tới trang 3, 6, 20, 30 và 35; trang 6, 20 và 30 được
ingest, trang 3 bị loại vì số giá trị không khớp số cột, còn trang 35 mở circuit
với `ZERO_USAGE_PROVIDER_ERROR`. Trang 39, 40 và 46 chưa được gửi. PDF chuyển
sang `FAILED` với đúng năm trang 3, 35, 39, 40 và 46 cho terminal repair.

Nhóm `PENDING` gồm đúng 147 PDF / 8.504 trang: 110 PDF năm 2025 và 37 PDF năm
2026. Nhóm này có 0 PDF năm 2024, không giao với tám ngân hàng cũ và không chứa
trang ngoài frontier tiếng Việt đã đăng ký.
Artifact V2 của nhóm này có 0 raw response và 0 raw-before-validation, nên
không có lượt trả phí cũ bị bỏ quên để replay; đây thực sự là các PDF chưa chạy.

Đối chiếu 37 PDF `SUCCEEDED` với store xác nhận đủ đúng 1.933/1.933 trang,
không thiếu/thừa trang, không orphan và không có nhiều JSON version cho cùng
một page. SQLite integrity và foreign-key check đều sạch.

Phân rã toàn bộ 14.947 trang theo trạng thái ledger cũng khớp tuyệt đối:

| Trạng thái PDF | Tổng trang | Đã có JSON | Còn thiếu |
| --- | ---: | ---: | ---: |
| `SUCCEEDED` | 1.933 | 1.933 | 0 |
| `NEEDS_RETRY` | 965 | 893 | 72 |
| `FAILED` chờ terminal repair | 3.545 | 3.185 | 360 |
| `PENDING` | 8.504 | 0 | 8.504 |
| **Tổng** | **14.947** | **6.011** | **8.936** |

## Chi phí đã phát sinh

- 6.011 trang thuộc frontier 271 PDF hiện hành: **21,687696000 USD**.
- 280 trang của tài liệu tiếng Anh/bản trùng đã loại: **0,944172750 USD**;
  khoản này được giữ làm lịch sử nhưng không trộn vào tiến độ hiện hành.
- Toàn store: **22,631868750 USD** cho 6.291 extraction hoàn tất. Không có
  extraction run không được page JSON tham chiếu và các lượt HTTP 429/504 vừa
  qua không có usage/cost.
- Riêng response trang 3 của NVB Q2/2026 bị validator loại vẫn có receipt billed
  **0,005352000 USD**; khoản này không nằm trong tổng extraction đã ingest ở
  trên. Trang 35 có usage/cost bằng 0.
