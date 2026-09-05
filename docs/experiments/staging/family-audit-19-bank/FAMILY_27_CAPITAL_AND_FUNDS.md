# Family 27 — Vốn và các quỹ

Checkpoint ngày 04/09/2026 trên tập bất biến 271 PDF của 19 ngân hàng mới,
chỉ gồm báo cáo từ năm 2025 đến hiện tại. Đây là checkpoint thuật toán, chưa
phải kết luận hoàn tất family.

## Trạng thái kiểm tra chéo

| Chỉ tiêu | Số lượng |
| --- | ---: |
| PDF đã khảo sát | 271 |
| READY | 211 |
| NOT_OBSERVED | 0 |
| UNRESOLVED | 60 |
| Mapping trong 211 PDF READY | 1.799 |
| PDF READY qua hợp đồng kiểm tra nguồn quan sát | 211/211 |
| Mapping có ít nhất một lane nhìn thấy và một lane trống giữ `null` | 139 |
| Ô nguồn trống được giữ `null`, không suy thành 0 | 228 |

Đối chiếu với checkpoint trước: 184 PDF READY cũ vẫn giữ READY; 27 PDF từ
UNRESOLVED đã thành READY; không có READY regression và không có false
NOT_OBSERVED.

## Các sửa đổi generic đã chứng minh bằng PDF

- Nhận các alias đúng bản chất trong schema như `Vốn góp chủ sở hữu`, `Vốn cổ
  phần`, `Thặng dư vốn`, các biến thể lợi nhuận chưa phân phối/lỗ lũy kế và lợi
  ích cổ đông không kiểm soát.
- Phân biệt `Triệu đồng Việt Nam` với token `VND` nằm bên trong cùng một cụm,
  nhưng vẫn fail-closed nếu PDF thật sự ghi nhiều đơn vị mâu thuẫn.
- Nhận subtotal quỹ theo hai dạng nguồn: `Tổng cộng các quỹ` và
  `Quỹ của TCTD / Tổng cộng Quỹ của TCTD`. Subtotal chỉ sở hữu các dòng con
  liên tiếp có cùng nhãn nhóm; không nuốt khoản mục ngoài nhóm.
- Bỏ cột đánh số/ký hiệu `A` khỏi trục biến động khi cột đó được nguồn khai báo
  là TEXT; bốn cột MONEY vẫn giữ nguyên locator và thứ tự nguồn.
- Nhận đúng nhãn kỳ `Tăng/Giảm trong 03, 06, 09 hoặc 12 tháng`. Đây chỉ là vai
  trò biến động; thuật toán không dùng số tháng để bịa ngày đầu/cuối kỳ.
- Khi PDF đồng thời in dòng tổng `Tăng/Giảm` và các dòng chi tiết bên dưới,
  chỉ dùng dòng tổng làm frontier nếu toàn bộ ô đều quan sát được và vector
  tổng bằng chính xác tổng vector các con liên tiếp. Các dòng con được giữ làm
  bằng chứng kiểm soát, không cộng lần hai.
- Với hai block so sánh không ghi ngày, chỉ chọn block hiện tại khi cả hai biên
  nguồn ghi rõ `năm nay` hoặc `kỳ này`; trường hợp hòa hoặc thiếu một biên vẫn
  UNRESOLVED.

Các bằng chứng nổi bật:

- 12 PDF SeABank được sửa bởi cấu trúc subtotal quỹ lặp đúng nhãn.
- 8 PDF Techcombank được sửa bởi subtotal `Tổng cộng các quỹ` và phạm vi con
  liên tiếp.
- 4 PDF VAB (hai báo cáo bán niên và hai báo cáo kiểm toán năm 2025) được sửa
  bởi quan hệ tổng biến động bằng đúng tổng các dòng con, không phụ thuộc mã
  ngân hàng, tên file hoặc số trang.
- Ba PDF khác chuyển READY nhờ cùng tập alias/reset generic; danh sách exact
  nằm trong log differential của checkpoint và cần được đưa vào ledger cuối
  khi family hoàn tất.

## UNRESOLVED còn lại

| Ngân hàng | PDF còn vướng |
| --- | ---: |
| ABB | 1 |
| KLB | 12 |
| LPB | 1 |
| MSB | 2 |
| NAB | 5 |
| NVB | 3 |
| OCB | 5 |
| PGB | 5 |
| SHB | 10 |
| STB | 4 |
| TPB | 1 |
| VAB | 11 |

Các nhóm nguyên nhân hiện tại, chưa được phép gom thành thiếu schema:

- Ranh giới owner/reset hoặc continuation chưa chọn đúng bảng: KLB, PGB và một
  số OCB/NAB/VAB.
- Hai fragment có trục khoản mục khác nhau hoặc bảng bị tách qua trang: KLB,
  NAB, OCB và VAB.
- Tổng ngang/dọc trên JSON chưa khép hoặc solver chưa tìm được placement duy
  nhất: ABB, LPB, MSB, NVB, SHB và STB. Từng trường hợp phải kiểm tra lại PDF
  trước khi sửa; không được dùng equation để biến ô trống thành 0.
- Ô tiền nguồn không phải số nguyên hợp lệ trong JSON: một số NAB, NVB, SHB,
  TPB và VAB. Cần đối chiếu ảnh PDF để phân biệt lỗi nguồn/OCR với cấu trúc.
- Không xác định chắc đơn vị tại chính bảng: 8 PDF. Ví dụ STB hợp nhất quý
  1/2025 có bảng mục tiêu không in đơn vị trong khi cùng tài liệu dùng cả VND
  và triệu đồng; giữ UNRESOLVED là đúng, không suy theo độ lớn giá trị.

Inventory SOURCE_ONLY trong 211 PDF READY vẫn là khoản mục nhìn thấy trên PDF,
không phải lỗi: quỹ đầu tư phát triển (117 lần), vốn đầu tư xây dựng cơ bản
(48), cổ phiếu quỹ (48), chênh lệch đánh giá lại tài sản (21), và nhóm `Quỹ
của TCTD` (15). Chúng chỉ được giữ SOURCE_ONLY khi không có ReportNormId phù
hợp trong subtree Family 27 hoặc khi đó là control nhóm; khoản mục có ID phù
hợp phải tiếp tục được map.

## Gate đã chạy

- 71 test chuyên evaluator/indexed wiring: đạt.
- Ruff trên evaluator và hai test chuyên biệt: đạt.
- Replay 271 PDF hai lần trên cùng snapshot: cùng kết quả 211/0/60.
- Differential: 27 U→R, 184 R→R, không có R→U/N.
- Hợp đồng quan sát nguồn: 211/211 candidate READY đạt; không có blank-derived
  zero.

