# Family 1 — Tiền mặt, vàng bạc và đá quý

Checkpoint audit trên tập bất biến 204 PDF của 19 ngân hàng mới. Đây là tài
liệu staging để nhập vào bảng tổng hợp cuối sau khi replay đủ 271 PDF.

| Trạng thái | Baseline | Sau audit | Chênh lệch |
|---|---:|---:|---:|
| READY | 99 | 131 | +32 |
| NOT_OBSERVED | 61 | 61 | 0 |
| UNRESOLVED | 44 | 12 | -32 |

- Kiểm tra tổng: **131 READY + 61 NOT_OBSERVED + 12 UNRESOLVED = 204 PDF**.
- Số mapping tăng từ 352 lên **452**.
- Đúng 32 PDF chuyển từ UNRESOLVED sang READY; mọi PDF còn lại giữ nguyên
  trạng thái. Không có READY regression và không làm thay đổi ý nghĩa
  NOT_OBSERVED.
- Các sửa đổi là quy tắc chung: nhận diện parent `Tiền mặt`, alias
  `Vàng nữ trang` cho ReportNormId 566, và đơn vị tiền được lặp nguyên văn ở
  toàn bộ header tiền của cùng bảng.

## Tiến độ theo ngân hàng

| Ngân hàng | PDF khảo sát | READY | NOT_OBSERVED | UNRESOLVED |
|---|---:|---:|---:|---:|
| ABB | 7 | 2 | 5 | 0 |
| BAB | 5 | 5 | 0 | 0 |
| BVB | 8 | 6 | 2 | 0 |
| EIB | 13 | 3 | 10 | 0 |
| KLB | 11 | 9 | 0 | 2 |
| LPB | 6 | 6 | 0 | 0 |
| MSB | 13 | 13 | 0 | 0 |
| NAB | 11 | 1 | 10 | 0 |
| NVB | 8 | 8 | 0 | 0 |
| OCB | 13 | 3 | 10 | 0 |
| PGB | 7 | 7 | 0 | 0 |
| SGB | 12 | 12 | 0 | 0 |
| SHB | 14 | 12 | 2 | 0 |
| SSB | 13 | 10 | 3 | 0 |
| STB | 13 | 3 | 10 | 0 |
| TCB | 16 | 16 | 0 | 0 |
| TPB | 10 | 10 | 0 | 0 |
| VAB | 13 | 3 | 0 | 10 |
| VBB | 11 | 2 | 9 | 0 |
| **Tổng** | **204** | **131** | **61** | **12** |

## Cấu trúc schema đã nhận diện

| Khoản mục | ReportNormId | Cách dùng |
|---|---:|---|
| Tiền mặt, vàng bạc và đá quý | 561 | Dòng tổng/parent và control số học |
| Tiền mặt bằng VND | 562 | Mapping trực tiếp |
| Tiền mặt bằng ngoại tệ | 563 | Mapping trực tiếp |
| Chứng từ có giá bằng ngoại tệ | 564 | Mapping trực tiếp khi nhìn thấy đúng bản chất |
| Vàng tiền tệ | 565 | Mapping trực tiếp |
| Vàng phi tiền tệ, gồm vàng nữ trang | 566 | Mapping trực tiếp; `Vàng nữ trang` là biến thể tên gọi |
| Kim loại quý, đá quý khác | 567 | Mapping trực tiếp |
| Khác | 568 | Chỉ dùng khi nguồn xác định đúng vai trò `Khác` |

Các dòng chi tiết chỉ được map khi cùng owner, cùng hai cột kỳ, có đơn vị tiền
xác thực và khép đúng dòng tổng nhìn thấy. Không tách một dòng nguồn gộp nhiều
bản chất thành các ID con nếu PDF không cho biết tỷ trọng.

## 12 PDF còn UNRESOLVED

### KLB — thiếu bằng chứng đơn vị cục bộ

Hai PDF dưới đây có bảng rõ, hai cột kỳ và phép cộng khớp, nhưng chính bảng và
JSON không ghi đơn vị. Đây không phải thiếu schema; chính sách hiện tại không
được tự kế thừa đơn vị từ một vị trí xa khi chưa có receipt tài liệu đủ chặt.

| # | Kỳ / báo cáo | File PDF | Trang PDF | Nội dung nhìn thấy | Schema gần nhất | Kết luận |
|---:|---|---|---:|---|---|---|
| 1 | Năm 2025, hợp nhất, kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | 29 | Tiền mặt bằng VND/ngoại tệ và tổng | 561–568 | **KHÔNG XÁC ĐỊNH ĐƯỢC ĐƠN VỊ** — cần cơ chế kế thừa đơn vị cấp tài liệu có bằng chứng. |
| 2 | 6 tháng 2025, hợp nhất, soát xét | `VI_BaoCaoTaiChinh_KiemToan_BanNien_2025_HN.pdf` | 26 | Cùng cấu trúc, số và tổng đọc rõ | 561–568 | **KHÔNG XÁC ĐỊNH ĐƯỢC ĐƠN VỊ** — không được đoán scale. |

### VAB — dòng nguồn gộp khác bản chất và khoảng trống ghép trang

VAB dùng dòng `Vàng, kim loại quý và đá quý` hoặc `Vàng, kim loại quý, đá quý`.
Dòng này rộng hơn từng child 565, 566 hoặc 567. Không được ép toàn bộ số vào một
ID chỉ vì tên gần nghĩa. PDF không thiếu và không phải OCR mờ.

| # | Kỳ / báo cáo | File PDF | Trang PDF | Nội dung nhìn thấy | Schema gần nhất | Kết luận |
|---:|---|---|---:|---|---|---|
| 3 | Q1/2025, hợp nhất, chưa kiểm toán | `2_vab_2025_4_15_527ed46_vi_baocaotaichinh_q1_2025.pdf` | 28 | Tiền mặt VND/ngoại tệ; dòng gộp vàng + kim loại quý + đá quý; tổng | 565–567 | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**; bảng còn thiếu unit exact. |
| 4 | Q1/2025, riêng lẻ, chưa kiểm toán | `2_vab_2025_4_15_d453cb6_vn_baocaotaichinh_q1_2025.pdf` | 27 | Cùng mẫu dòng gộp | 565–567 | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**; không tách số nguồn bằng suy đoán. |
| 5 | Q3/2025, công ty mẹ, chưa kiểm toán | `BCTC Công ty mẹ quý 3 năm 2025.pdf` | 29 | Dòng gộp vàng/kim loại quý/đá quý có số | 565–567 | **NHIỀU ID CÓ THỂ PHÙ HỢP** nhưng không ID nào bao trùm nguyên văn toàn dòng. |
| 6 | Q4/2025, công ty mẹ, chưa kiểm toán | `BCTC Công ty mẹ quý 4 năm 2025.pdf` | 29 | Cùng mẫu | 565–567 | **NHIỀU ID CÓ THỂ PHÙ HỢP**; giữ nguyên số nguồn. |
| 7 | Q3/2025, hợp nhất, chưa kiểm toán | `BCTC Hợp nhất quý 3 năm 2025.pdf` | 29–30 | Parent ở p29, các dòng đầy đủ ở p30 | 561, 565–567 | **KHOẢNG TRỐNG GHÉP TRANG + DÒNG GỘP KHÁC BẢN CHẤT**. PDF đầy đủ; thuật toán cần giữ owner qua continuation. |
| 8 | Q4/2025, hợp nhất, chưa kiểm toán | `BCTC Hợp nhất quý 4 năm 2025.pdf` | 29–30 | Một phần bảng ở p29, phần còn lại và tổng ở p30 | 561, 565–567 | **KHOẢNG TRỐNG GHÉP TRANG + DÒNG GỘP KHÁC BẢN CHẤT**; không phải PDF bị cắt. |
| 9 | Q2/2025, riêng lẻ, chưa kiểm toán | `BCTC RIENG LE QUY 2.2025-TV_0001-da nen.pdf` | 27 | Dòng gộp và tổng nhìn rõ | 565–567 | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 10 | Q2/2026, công ty mẹ, chưa kiểm toán | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | 29 | Dòng gộp và tổng nhìn rõ | 565–567 | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 11 | Q2/2026, hợp nhất, chưa kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | 30 | Dòng gộp và tổng nhìn rõ | 565–567 | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**. |
| 12 | Q1/2026, riêng lẻ, chưa kiểm toán | `BCTC Q1.2026 RIENG LE_0001.pdf` | 29–30 | p29 có parent + VND; p30 có dòng gộp vàng/kim loại quý/đá quý + tổng | 561, 565–567 | **KHOẢNG TRỐNG GHÉP TRANG + DÒNG GỘP KHÁC BẢN CHẤT**. |

## SOURCE_ONLY / CONTROL trong PDF READY

- Dòng tổng của family được giữ làm control để chứng minh tổng các child nhưng
  không tạo mapping trùng với chính các child.
- Không có dòng ITEM cùng bản chất với một ReportNormId hiện hữu bị bỏ lại trong
  131 PDF READY tại checkpoint này.
- `Vàng nữ trang` đã được xác nhận là biến thể tên của vàng phi tiền tệ và đã
  map vào ReportNormId 566; nó không còn là SOURCE_ONLY.

## NOT_OBSERVED

61 PDF không trình bày family này trong phạm vi báo cáo đã kiểm tra. Phân bố
theo ngân hàng được ghi ở bảng tiến độ; đây là absence hợp lệ, không phải lỗi
schema. Danh sách file chi tiết sẽ được sinh lại từ checkpoint đủ 271 PDF trong
ledger cuối để tránh duy trì song song hai denominator.

## Truy vết kỹ thuật

- Kết quả audit: `/dev/shm/family01-audit-rerun-v2.json`
- Database replay: `/dev/shm/family01-audit-rerun-v2.sqlite3`
- Render đã mở kiểm tra: `/dev/shm/family01-audit-renders/`
