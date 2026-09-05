# Family 3 — Tiền gửi tại và cho vay các tổ chức tín dụng khác

Checkpoint audit trên tập bất biến 204 PDF của 19 ngân hàng, chỉ gồm báo cáo từ năm 2025 đến hiện tại. Đây là bằng chứng staging; chưa thay thế hai bảng tổng hợp cuối dự án.

| Trạng thái | Baseline | Sau audit | Chênh lệch |
|---|---:|---:|---:|
| READY | 129 | 184 | +55 |
| NOT_OBSERVED | 4 | 4 | 0 |
| UNRESOLVED | 71 | 16 | -55 |

- 129/129 PDF READY cũ vẫn READY; vector hệ số của ReportNormId 575 không đổi.
- 4/4 PDF NOT_OBSERVED cũ vẫn NOT_OBSERVED; không phát sinh false-N.
- Kết quả cuối có 1.035 mapping, không trùng ReportNormId trong cùng PDF và đúng thứ tự schema.
- 103 test Family 3, engine và regression 8 ngân hàng cũ passed.

## 16 PDF còn UNRESOLVED

Schema đã có các ReportNormId cần thiết. Các trường hợp dưới đây vướng biểu diễn nguồn, thiếu bằng chứng về nhánh cho vay, hoặc hai candidate cùng đúng nhưng khác đơn vị.

| # | Ngân hàng | File PDF | Kỳ / loại báo cáo | Kiểm toán | Trang | Nội dung nhìn thấy | Schema gần nhất | Kết luận |
|---:|---|---|---|---|---:|---|---|---|
| 1 | EIB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | Q3/2025, hợp nhất | Không nêu | 2 | Family; tiền gửi; cho vay; dự phòng | 575, 576, 585, 5718 | **LỖI SOURCE/OCR** — giá trị bị dịch hàng, phép cộng không khép kín. |
| 2 | EIB | `BCTC Công ty mẹ quý 1 năm 2026.pdf` | Q1/2026, công ty mẹ | Không nêu | 2 | Family và các dòng tiền gửi/cho vay có chữ và số | 575, 576, 585, 5718 | **LỖI SOURCE/OCR** — số thứ tự nằm ở `label`, tên khoản mục bị đưa vào cột TEXT; cần sửa nguồn hoặc descriptor-promotion generic có replay riêng. |
| 3 | KLB | `BAO CAO TAI CHINH QUY 3.2025 RIENG.pdf` | Q3/2025, riêng lẻ | Không nêu | 21 | Tiền gửi không kỳ hạn/có kỳ hạn, VND/ngoại tệ, “Cộng” | 575–582 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — chỉ thấy nhánh tiền gửi; không có bằng chứng nhánh cho vay 585 bằng 0. |
| 4 | KLB | `BCTC Công ty mẹ quý 2 năm 2025.pdf` | Q2/2025, công ty mẹ | Không nêu | 20 | Cùng cấu trúc tiền gửi | 575–582 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — thiếu bằng chứng trực tiếp cho nhánh 585. |
| 5 | KLB | `bao-cao-tai-chinh-giua-nien-do-q4.2025-rieng_tv.pdf` | Q4/2025, riêng lẻ | Không nêu | 22 | Cùng cấu trúc tiền gửi | 575–582 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — thiếu bằng chứng trực tiếp cho nhánh 585. |
| 6 | KLB | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | Q2/2026, công ty mẹ | Không nêu | 25 | Cùng cấu trúc tiền gửi | 575–582 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — thiếu bằng chứng trực tiếp cho nhánh 585. |
| 7 | NVB | `BCTC Công ty mẹ quý 1 năm 2025.pdf` | Q1/2025, công ty mẹ | Không nêu | 29 | Chi tiết tiền gửi; không có bảng số cho vay | 575–582 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — không mặc định nhánh 585 bằng 0. |
| 8 | NVB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | Q1/2025, hợp nhất | Không nêu | 29 | Chi tiết tiền gửi; không có bảng số cho vay | 575–582 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — thiếu bằng chứng trực tiếp cho nhánh 585. |
| 9 | PGB | `BCTC Kiểm toán năm 2025.pdf` | Năm 2025, báo cáo ngân hàng | Kiểm toán | 28 | Tổng tiền gửi và các dòng chi tiết; bảng cho vay kế tiếp không có số | 575–582 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — chưa có bằng chứng số học để kết luận nhánh 585 bằng 0. |
| 10 | SGB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | Q1/2025, hợp nhất | Không nêu | 2 | “3. Dự phòng rủi ro” | 5718 | **LỖI SOURCE/OCR** — ô tiền là chuỗi diễn giải dấu gạch, không phải số hay dấu gạch nguyên văn. |
| 11 | SGB | `BCTC-rieng-le-da-duoc-kiem-toan-2025.pdf` | Năm 2025, riêng lẻ | Kiểm toán | 8 | “3. Dự phòng rủi ro” | 5718 | **LỖI SOURCE/OCR** — ô tiền chứa ký tự rác `-边-`. |
| 12 | SGB | `BCTC-HN-quy-1---2026_VIE_0001.pdf` | Q1/2026, hợp nhất | Không nêu | 3 | “3. Dự phòng rủi ro” | 5718 | **LỖI SOURCE/OCR** — ô tiền chứa chuỗi rác `- tieu-`. |
| 13 | VAB | `2_vab_2025_4_15_527ed46_vi_baocaotaichinh_q1_2025.pdf` | Q1/2025, hợp nhất | Không nêu | 1, 3; chi tiết 29 | Hai bảng cùng family, một bảng VND và một bảng triệu đồng | 575, 576, 585, 5718; gần nhất 579/582/588 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — hai candidate cùng khép kín nhưng chênh đúng hệ số 1.000.000. Dòng “Bằng ngoại tệ, vàng” chỉ SOURCE_ONLY. |
| 14 | VAB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | Q3/2025, hợp nhất | Không nêu | 3, 5; chi tiết 30 | Hai bảng cùng số liệu, VND và triệu đồng | 575, 576, 585, 5718; gần nhất 579/582/588 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — chưa có chính sách generic để chọn một trong hai bản khác scale. |
| 15 | VAB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất | Không nêu | 3, 5; chi tiết 30 | Hai bảng cùng số liệu, VND và triệu đồng | 575, 576, 585, 5718; gần nhất 579/582/588 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — hai candidate cùng hợp lệ nhưng khác scale; giữ UNRESOLVED. |
| 16 | VAB | `BCTC Hợp nhất quý 2 năm 2026.pdf` | Q2/2026, hợp nhất | Không nêu | 3, 5; chi tiết 30–31 | Hai bảng cùng số liệu, VND và triệu đồng | 575, 576, 585, 5718; gần nhất 579/582/588 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — hai candidate cùng hợp lệ nhưng khác scale; giữ UNRESOLVED. |

## SOURCE_ONLY trong PDF READY

23 PDF READY còn dòng “Bằng ngoại tệ, vàng”. Đây không phải lỗi thiếu schema: PDF gộp ngoại tệ và vàng thành một số, còn schema tách ngoại tệ theo từng nhánh 579/582/588. Không ép số gộp vào ID chỉ có ngoại tệ. Danh sách PDF/trang đầy đủ được giữ trong artifact audit bất biến ghi ở phần truy vết kỹ thuật.

## Bốn PDF NOT_OBSERVED

| Ngân hàng | File PDF |
|---|---|
| EIB | `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` |
| EIB | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` |
| EIB | `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` |
| PGB | `BCTC Soát xét 6 tháng đầu năm 2025.pdf` |

## Truy vết kỹ thuật

- Baseline: `/dev/shm/bctc-ai-27-bank-family-live-v1/family-03-interbank-deposits-and-loans.json`
- Kết quả audit: `/dev/shm/family03-audit-rerun-v4.json`
- Ledger đọc cho người: `/dev/shm/family03-residual-human-audit-v1.md`
- Database replay: `/dev/shm/family03-audit-rerun-v4.sqlite3`

