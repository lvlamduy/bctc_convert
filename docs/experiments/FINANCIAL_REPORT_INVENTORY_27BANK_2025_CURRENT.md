# Ma trận BCTC 27 ngân hàng từ Quý 1/2025 đến hiện tại

Cập nhật theo nguồn đã đăng ký đến ngày **2026-09-01**.

Đây là ma trận **file đầu vào cho Gemini**, chưa phải kết luận mapping. Tên file chỉ dùng để sắp xếp; phạm vi, kỳ và tình trạng kiểm toán sẽ được xác thực lại từ nội dung nhìn thấy trong PDF.

## Tổng quan

| Chỉ tiêu | Số lượng |
|---|---:|
| Ngân hàng | 27 |
| Ngân hàng tái sử dụng JSON đã có, không gọi API | 8 |
| Ngân hàng mới trong Vertex Flex frontier | 19 |
| PDF corpus 8 ngân hàng đã có JSON, chỉ tái sử dụng | 140 |
| Trang corpus 8 ngân hàng đã có JSON, không gửi lại | 8,947 |
| PDF ứng viên của 19 ngân hàng mới | 279 |
| Trang ứng viên được phép gọi Vertex Flex | 15,968 |
| Tổng PDF được theo dõi sau khi mở rộng | 419 |
| Tổng trang được theo dõi sau khi mở rộng | 24,915 |
| PDF mới cần Gemini xác thực ít nhất một thuộc tính kỳ/phạm vi/kiểm toán | 235 |
| Đường dẫn trùng nội dung đã loại | 0 |

## Tiến độ theo ngân hàng

| STT | Mã | Xử lý Gemini | PDF mới 2025 | PDF mới 2026 | Tổng PDF mới | Trang mới | Cần xác thực nội dung |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | ABB | Vertex Flex mới | 11 | 2 | 13 | 481 | 13 |
| 2 | ACB | Tái sử dụng JSON đã có; không gọi API | — | — | — | — | — |
| 3 | BAB | Vertex Flex mới | 10 | 2 | 12 | 542 | 10 |
| 4 | BID | Tái sử dụng JSON đã có; không gọi API | — | — | — | — | — |
| 5 | BVB | Vertex Flex mới | 10 | 4 | 14 | 742 | 14 |
| 6 | CTG | Tái sử dụng JSON đã có; không gọi API | — | — | — | — | — |
| 7 | EIB | Vertex Flex mới | 12 | 4 | 16 | 703 | 12 |
| 8 | HDB | Tái sử dụng JSON đã có; không gọi API | — | — | — | — | — |
| 9 | KLB | Vertex Flex mới | 14 | 4 | 18 | 757 | 16 |
| 10 | LPB | Vertex Flex mới | 7 | 1 | 8 | 702 | 8 |
| 11 | MBB | Tái sử dụng JSON đã có; không gọi API | — | — | — | — | — |
| 12 | MSB | Vertex Flex mới | 12 | 4 | 16 | 998 | 12 |
| 13 | NAB | Vertex Flex mới | 12 | 4 | 16 | 853 | 12 |
| 14 | NVB | Vertex Flex mới | 12 | 4 | 16 | 864 | 14 |
| 15 | OCB | Vertex Flex mới | 12 | 4 | 16 | 1,531 | 12 |
| 16 | PGB | Vertex Flex mới | 5 | 2 | 7 | 357 | 7 |
| 17 | SGB | Vertex Flex mới | 10 | 4 | 14 | 703 | 14 |
| 18 | SHB | Vertex Flex mới | 12 | 4 | 16 | 729 | 12 |
| 19 | SSB | Vertex Flex mới | 12 | 4 | 16 | 1,063 | 12 |
| 20 | STB | Vertex Flex mới | 12 | 4 | 16 | 972 | 12 |
| 21 | TCB | Vertex Flex mới | 12 | 4 | 16 | 1,294 | 12 |
| 22 | TPB | Vertex Flex mới | 12 | 4 | 16 | 1,080 | 12 |
| 23 | VAB | Vertex Flex mới | 13 | 3 | 16 | 784 | 14 |
| 24 | VBB | Vertex Flex mới | 12 | 5 | 17 | 813 | 17 |
| 25 | VCB | Tái sử dụng JSON đã có; không gọi API | — | — | — | — | — |
| 26 | VIB | Tái sử dụng JSON đã có; không gọi API | — | — | — | — | — |
| 27 | VPB | Tái sử dụng JSON đã có; không gọi API | — | — | — | — | — |

## Danh sách PDF để kiểm tra

Các nhãn “cần xác thực” không phải lỗi và không phải `UNRESOLVED`; chúng chỉ cho biết tên file chưa đủ mạnh để kết luận trước khi đọc PDF.

### ABB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [1_abb_2025_9_9_0dee6d3_bctc_hn_ktsx_30_06_2025_tv.pdf](<../../vietstock_bctc/ABB/2025/1_abb_2025_9_9_0dee6d3_bctc_hn_ktsx_30_06_2025_tv.pdf>) | 89 | Cần xác thực | Cần xác thực | Soát xét | Scope Requires Source Authentication; Period Requires Source Authentication |
| [3_abb_2025_9_9_5fa7e09_bctc_rl_ktsx_30_06_2025_tv.pdf](<../../vietstock_bctc/ABB/2025/3_abb_2025_9_9_5fa7e09_bctc_rl_ktsx_30_06_2025_tv.pdf>) | 86 | Cần xác thực | Cần xác thực | Soát xét | Scope Requires Source Authentication; Period Requires Source Authentication |
| [3_abb_2026_2_4_dc9ea10_bctc_rl_q4_2025.pdf](<../../vietstock_bctc/ABB/2025/3_abb_2026_2_4_dc9ea10_bctc_rl_q4_2025.pdf>) | 28 | Quý 4 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/ABB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 28 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/ABB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 28 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 4 năm 2025__592d2993__3_abb_2026_2_4_91abe48_bctc_hn_q4_2025.pdf](<../../vietstock_bctc/ABB/2025/BCTC%20Hợp%20nhất%20quý%204%20năm%202025__592d2993__3_abb_2026_2_4_91abe48_bctc_hn_q4_2025.pdf>) | 28 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 4 năm 2025__d2af87de__phpaedoan-bctc-hn-q4-2025-697c794a079fa.pdf](<../../vietstock_bctc/ABB/2025/BCTC%20Hợp%20nhất%20quý%204%20năm%202025__d2af87de__phpaedoan-bctc-hn-q4-2025-697c794a079fa.pdf>) | 28 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [phpkgbljk-bctc-hn-q3-2025-68fb4c313c9de.pdf](<../../vietstock_bctc/ABB/2025/phpkgbljk-bctc-hn-q3-2025-68fb4c313c9de.pdf>) | 28 | Quý 3 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [phplpiamp-bctc-q2-2025-rl-6889fde02c284.pdf](<../../vietstock_bctc/ABB/2025/phplpiamp-bctc-q2-2025-rl-6889fde02c284.pdf>) | 28 | Quý 2 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [phpnjkobf-bctc-q2-2025-hn-6889fad62c419.pdf](<../../vietstock_bctc/ABB/2025/phpnjkobf-bctc-q2-2025-hn-6889fad62c419.pdf>) | 28 | Quý 2 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [phppidjcp-bctc-rl-q3-2025-68fb4c6b97d59.pdf](<../../vietstock_bctc/ABB/2025/phppidjcp-bctc-rl-q3-2025-68fb4c6b97d59.pdf>) | 28 | Quý 3 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [phpbbdkfl-bctc-rl-q1-2026-69e18d88eace3.pdf](<../../vietstock_bctc/ABB/2026/phpbbdkfl-bctc-rl-q1-2026-69e18d88eace3.pdf>) | 27 | Quý 1 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [phpnchaip-bao-cao-tai-chinh-rieng-le-quy-ii-nam-2026-6a5df290b2d0a.pdf](<../../vietstock_bctc/ABB/2026/phpnchaip-bao-cao-tai-chinh-rieng-le-quy-ii-nam-2026-6a5df290b2d0a.pdf>) | 27 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |

### ACB

Đã xử lý trong corpus 8 ngân hàng; **không đưa bất kỳ PDF nào của ngân hàng này vào paid frontier**. Xem danh sách PDF đã chọn tại [ma trận 8 ngân hàng](FINANCIAL_REPORT_INVENTORY_8BANK.md).


### BAB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [1_bab_2026_2_4_4d13ce7_vi_baocaotaichinh_q4_2025.pdf](<../../vietstock_bctc/BAB/2025/1_bab_2026_2_4_4d13ce7_vi_baocaotaichinh_q4_2025.pdf>) | 41 | Quý 4 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [BAB_BCTC Hop nhat Quy 3.2025_Tieng Viet.pdf](<../../vietstock_bctc/BAB/2025/BAB_BCTC%20Hop%20nhat%20Quy%203.2025_Tieng%20Viet.pdf>) | 43 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BAB_BCTC Rieng le Quy 3.2025_Tieng Viet.pdf](<../../vietstock_bctc/BAB/2025/BAB_BCTC%20Rieng%20le%20Quy%203.2025_Tieng%20Viet.pdf>) | 41 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Consolidated 2025_Audited.pdf](<../../vietstock_bctc/BAB/2025/BCTC%20Consolidated%202025_Audited.pdf>) | 51 | Năm | Hợp nhất | Kiểm toán | Không |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/BAB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 41 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hop nhat 2025_Kiem toan.pdf](<../../vietstock_bctc/BAB/2025/BCTC%20Hop%20nhat%202025_Kiem%20toan.pdf>) | 51 | Cần xác thực | Hợp nhất | Kiểm toán | Period Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/BAB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 43 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 4 năm 2025.pdf](<../../vietstock_bctc/BAB/2025/BCTC%20Hợp%20nhất%20quý%204%20năm%202025.pdf>) | 43 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Rieng le 2025_Kiem toan.pdf](<../../vietstock_bctc/BAB/2025/BCTC%20Rieng%20le%202025_Kiem%20toan.pdf>) | 50 | Cần xác thực | Riêng lẻ/CT mẹ | Kiểm toán | Period Requires Source Authentication |
| [BCTC Separate 2025_Audited.pdf](<../../vietstock_bctc/BAB/2025/BCTC%20Separate%202025_Audited.pdf>) | 50 | Năm | Riêng lẻ/CT mẹ | Kiểm toán | Không |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/BAB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 43 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/BAB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 45 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### BID

Đã xử lý trong corpus 8 ngân hàng; **không đưa bất kỳ PDF nào của ngân hàng này vào paid frontier**. Xem danh sách PDF đã chọn tại [ma trận 8 ngân hàng](FINANCIAL_REPORT_INVENTORY_8BANK.md).


### BVB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/BVB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 48 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 4 năm 2025.pdf](<../../vietstock_bctc/BVB/2025/BCTC%20Công%20ty%20mẹ%20quý%204%20năm%202025.pdf>) | 48 | Quý 4 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/BVB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 48 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 4 năm 2025.pdf](<../../vietstock_bctc/BVB/2025/BCTC%20Hợp%20nhất%20quý%204%20năm%202025.pdf>) | 48 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [VI_BaoCaoTaiChinhHopNhat_Kiemtoan_2025.pdf](<../../vietstock_bctc/BVB/2025/VI_BaoCaoTaiChinhHopNhat_Kiemtoan_2025.pdf>) | 81 | Cần xác thực | Hợp nhất | Kiểm toán | Period Requires Source Authentication |
| [VI_BaoCaoTaiChinhHopNhat_Q2_2025-1.pdf](<../../vietstock_bctc/BVB/2025/VI_BaoCaoTaiChinhHopNhat_Q2_2025-1.pdf>) | 48 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [VI_BaoCaoTaiChinhHopNhat_Q3_2025.pdf](<../../vietstock_bctc/BVB/2025/VI_BaoCaoTaiChinhHopNhat_Q3_2025.pdf>) | 48 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [VI_BaoCaoTaiChinhRiengLe_Kiemtoan_2025.pdf](<../../vietstock_bctc/BVB/2025/VI_BaoCaoTaiChinhRiengLe_Kiemtoan_2025.pdf>) | 81 | Cần xác thực | Riêng lẻ/CT mẹ | Kiểm toán | Period Requires Source Authentication |
| [VI_BaoCaoTaiChinhRiengLe_Q2_2025.pdf](<../../vietstock_bctc/BVB/2025/VI_BaoCaoTaiChinhRiengLe_Q2_2025.pdf>) | 48 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [VI_BaoCaoTaiChinhRiengLe_Q3_2025.pdf](<../../vietstock_bctc/BVB/2025/VI_BaoCaoTaiChinhRiengLe_Q3_2025.pdf>) | 48 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [2_bvb_2026_4_29_66c0e1c_vi_baocaotaichinhriengle_q1_2026.pdf](<../../vietstock_bctc/BVB/2026/2_bvb_2026_4_29_66c0e1c_vi_baocaotaichinhriengle_q1_2026.pdf>) | 48 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [6_bvb_2026_4_29_e2ea743_vi_baocaotaichinhhopnhat_q1_2026.pdf](<../../vietstock_bctc/BVB/2026/6_bvb_2026_4_29_e2ea743_vi_baocaotaichinhhopnhat_q1_2026.pdf>) | 48 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/BVB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 50 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/BVB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 50 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### CTG

Đã xử lý trong corpus 8 ngân hàng; **không đưa bất kỳ PDF nào của ngân hàng này vào paid frontier**. Xem danh sách PDF đã chọn tại [ma trận 8 ngân hàng](FINANCIAL_REPORT_INVENTORY_8BANK.md).


### EIB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [20260130 - EIB - BCTC hop nhat Q4.2025.pdf](<../../vietstock_bctc/EIB/2025/20260130%20-%20EIB%20-%20BCTC%20hop%20nhat%20Q4.2025.pdf>) | 40 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [20260130 - EIB - BCTC rieng le Q4.2025.pdf](<../../vietstock_bctc/EIB/2025/20260130%20-%20EIB%20-%20BCTC%20rieng%20le%20Q4.2025.pdf>) | 39 | Quý 4 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../vietstock_bctc/EIB/2025/BCTC%20Công%20ty%20mẹ%20Kiểm%20toán%20năm%202025.pdf>) | 58 | Năm | Riêng lẻ/CT mẹ | Kiểm toán | Không |
| [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/EIB/2025/BCTC%20Công%20ty%20mẹ%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 53 | 6 tháng | Riêng lẻ/CT mẹ | Soát xét | Không |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/EIB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 39 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2025.pdf](<../../vietstock_bctc/EIB/2025/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202025.pdf>) | 39 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 3 năm 2025.pdf](<../../vietstock_bctc/EIB/2025/BCTC%20Công%20ty%20mẹ%20quý%203%20năm%202025.pdf>) | 39 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../vietstock_bctc/EIB/2025/BCTC%20Hợp%20nhất%20Kiểm%20toán%20năm%202025.pdf>) | 61 | Năm | Hợp nhất | Kiểm toán | Không |
| [BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/EIB/2025/BCTC%20Hợp%20nhất%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 55 | 6 tháng | Hợp nhất | Soát xét | Không |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/EIB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 40 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2025.pdf](<../../vietstock_bctc/EIB/2025/BCTC%20Hợp%20nhất%20quý%202%20năm%202025.pdf>) | 40 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 3 năm 2025.pdf](<../../vietstock_bctc/EIB/2025/BCTC%20Hợp%20nhất%20quý%203%20năm%202025.pdf>) | 40 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ quý 1 năm 2026.pdf](<../../vietstock_bctc/EIB/2026/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202026.pdf>) | 39 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/EIB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 40 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2026.pdf](<../../vietstock_bctc/EIB/2026/BCTC%20Hợp%20nhất%20quý%201%20năm%202026.pdf>) | 40 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/EIB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 41 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### HDB

Đã xử lý trong corpus 8 ngân hàng; **không đưa bất kỳ PDF nào của ngân hàng này vào paid frontier**. Xem danh sách PDF đã chọn tại [ma trận 8 ngân hàng](FINANCIAL_REPORT_INVENTORY_8BANK.md).


### KLB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BAO CAO TAI CHINH QUY 3.2025 HOP NHAT.pdf](<../../vietstock_bctc/KLB/2025/BAO%20CAO%20TAI%20CHINH%20QUY%203.2025%20HOP%20NHAT.pdf>) | 35 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BAO CAO TAI CHINH QUY 3.2025 RIENG.pdf](<../../vietstock_bctc/KLB/2025/BAO%20CAO%20TAI%20CHINH%20QUY%203.2025%20RIENG.pdf>) | 36 | Quý 3 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../vietstock_bctc/KLB/2025/BCTC%20Công%20ty%20mẹ%20Kiểm%20toán%20năm%202025.pdf>) | 59 | Năm | Riêng lẻ/CT mẹ | Kiểm toán | Không |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/KLB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 35 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2025.pdf](<../../vietstock_bctc/KLB/2025/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202025.pdf>) | 35 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../vietstock_bctc/KLB/2025/BCTC%20Hợp%20nhất%20Kiểm%20toán%20năm%202025.pdf>) | 59 | Năm | Hợp nhất | Kiểm toán | Không |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/KLB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 35 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2025.pdf](<../../vietstock_bctc/KLB/2025/BCTC%20Hợp%20nhất%20quý%202%20năm%202025.pdf>) | 35 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [VI_BaoCaoTaiChinh_KiemToan_BanNien_2025_HN.pdf](<../../vietstock_bctc/KLB/2025/VI_BaoCaoTaiChinh_KiemToan_BanNien_2025_HN.pdf>) | 54 | 6 tháng | Cần xác thực | Kiểm toán | Scope Requires Source Authentication |
| [VI_BaoCaoTaiChinh_KiemToan_BanNien_2025_Rieng.pdf](<../../vietstock_bctc/KLB/2025/VI_BaoCaoTaiChinh_KiemToan_BanNien_2025_Rieng.pdf>) | 53 | 6 tháng | Cần xác thực | Kiểm toán | Scope Requires Source Authentication |
| [bao-cao-tai-chinh-giua-nien-do-q4.2025-hop-nhat-_ta.pdf](<../../vietstock_bctc/KLB/2025/bao-cao-tai-chinh-giua-nien-do-q4.2025-hop-nhat-_ta.pdf>) | 38 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [bao-cao-tai-chinh-giua-nien-do-q4.2025-hop-nhat-_tv.pdf](<../../vietstock_bctc/KLB/2025/bao-cao-tai-chinh-giua-nien-do-q4.2025-hop-nhat-_tv.pdf>) | 38 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [bao-cao-tai-chinh-giua-nien-do-q4.2025-rieng_ta.pdf](<../../vietstock_bctc/KLB/2025/bao-cao-tai-chinh-giua-nien-do-q4.2025-rieng_ta.pdf>) | 39 | Quý 4 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [bao-cao-tai-chinh-giua-nien-do-q4.2025-rieng_tv.pdf](<../../vietstock_bctc/KLB/2025/bao-cao-tai-chinh-giua-nien-do-q4.2025-rieng_tv.pdf>) | 40 | Quý 4 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ quý 1 năm 2026.pdf](<../../vietstock_bctc/KLB/2026/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202026.pdf>) | 41 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/KLB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 42 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2026.pdf](<../../vietstock_bctc/KLB/2026/BCTC%20Hợp%20nhất%20quý%201%20năm%202026.pdf>) | 41 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/KLB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 42 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### LPB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC 31.12.2025 E color.pdf](<../../vietstock_bctc/LPB/2025/BCTC%2031.12.2025%20E%20color.pdf>) | 95 | Cần xác thực | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Period Requires Source Authentication; Assurance Requires Source Authentication |
| [BCTC 31.12.2025 VN color.pdf](<../../vietstock_bctc/LPB/2025/BCTC%2031.12.2025%20VN%20color.pdf>) | 95 | Cần xác thực | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Period Requires Source Authentication; Assurance Requires Source Authentication |
| [BCTC Kiểm toán năm 2025.pdf](<../../vietstock_bctc/LPB/2025/BCTC%20Kiểm%20toán%20năm%202025.pdf>) | 70 | Năm | Cần xác thực | Kiểm toán | Scope Requires Source Authentication |
| [BCTC Q3.2025 VN.pdf](<../../vietstock_bctc/LPB/2025/BCTC%20Q3.2025%20VN.pdf>) | 94 | Quý 3 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [BCTC Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/LPB/2025/BCTC%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 70 | 6 tháng | Cần xác thực | Soát xét | Scope Requires Source Authentication |
| [BCTC quý 1 năm 2025.pdf](<../../vietstock_bctc/LPB/2025/BCTC%20quý%201%20năm%202025.pdf>) | 91 | Quý 1 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [BCTC quý 2 năm 2025.pdf](<../../vietstock_bctc/LPB/2025/BCTC%20quý%202%20năm%202025.pdf>) | 94 | Quý 2 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC quý 2 năm 2026.pdf](<../../vietstock_bctc/LPB/2026/BCTC%20quý%202%20năm%202026.pdf>) | 93 | Quý 2 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |

### MBB

Đã xử lý trong corpus 8 ngân hàng; **không đưa bất kỳ PDF nào của ngân hàng này vào paid frontier**. Xem danh sách PDF đã chọn tại [ma trận 8 ngân hàng](FINANCIAL_REPORT_INVENTORY_8BANK.md).


### MSB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../vietstock_bctc/MSB/2025/BCTC%20Công%20ty%20mẹ%20Kiểm%20toán%20năm%202025.pdf>) | 72 | Năm | Riêng lẻ/CT mẹ | Kiểm toán | Không |
| [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/MSB/2025/BCTC%20Công%20ty%20mẹ%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 73 | 6 tháng | Riêng lẻ/CT mẹ | Soát xét | Không |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/MSB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 58 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2025.pdf](<../../vietstock_bctc/MSB/2025/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202025.pdf>) | 58 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 3 năm 2025.pdf](<../../vietstock_bctc/MSB/2025/BCTC%20Công%20ty%20mẹ%20quý%203%20năm%202025.pdf>) | 58 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 4 năm 2025.pdf](<../../vietstock_bctc/MSB/2025/BCTC%20Công%20ty%20mẹ%20quý%204%20năm%202025.pdf>) | 56 | Quý 4 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../vietstock_bctc/MSB/2025/BCTC%20Hợp%20nhất%20Kiểm%20toán%20năm%202025.pdf>) | 76 | Năm | Hợp nhất | Kiểm toán | Không |
| [BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/MSB/2025/BCTC%20Hợp%20nhất%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 76 | 6 tháng | Hợp nhất | Soát xét | Không |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/MSB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 60 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2025.pdf](<../../vietstock_bctc/MSB/2025/BCTC%20Hợp%20nhất%20quý%202%20năm%202025.pdf>) | 60 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 3 năm 2025.pdf](<../../vietstock_bctc/MSB/2025/BCTC%20Hợp%20nhất%20quý%203%20năm%202025.pdf>) | 60 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [MSB 20260130 - MSB - Bao cao tai chinh Hop nhat Quy 4 2025.pdf](<../../vietstock_bctc/MSB/2025/MSB%2020260130%20-%20MSB%20-%20Bao%20cao%20tai%20chinh%20Hop%20nhat%20Quy%204%202025.pdf>) | 59 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ quý 1 năm 2026.pdf](<../../vietstock_bctc/MSB/2026/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202026.pdf>) | 60 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/MSB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 54 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2026.pdf](<../../vietstock_bctc/MSB/2026/BCTC%20Hợp%20nhất%20quý%201%20năm%202026.pdf>) | 61 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/MSB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 57 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### NAB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../vietstock_bctc/NAB/2025/BCTC%20Công%20ty%20mẹ%20Kiểm%20toán%20năm%202025.pdf>) | 84 | Năm | Riêng lẻ/CT mẹ | Kiểm toán | Không |
| [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/NAB/2025/BCTC%20Công%20ty%20mẹ%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 83 | 6 tháng | Riêng lẻ/CT mẹ | Soát xét | Không |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/NAB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 44 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 3 năm 2025.pdf](<../../vietstock_bctc/NAB/2025/BCTC%20Công%20ty%20mẹ%20quý%203%20năm%202025.pdf>) | 45 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 4 năm 2025.pdf](<../../vietstock_bctc/NAB/2025/BCTC%20Công%20ty%20mẹ%20quý%204%20năm%202025.pdf>) | 44 | Quý 4 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../vietstock_bctc/NAB/2025/BCTC%20Hợp%20nhất%20Kiểm%20toán%20năm%202025.pdf>) | 85 | Năm | Hợp nhất | Kiểm toán | Không |
| [BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/NAB/2025/BCTC%20Hợp%20nhất%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 83 | 6 tháng | Hợp nhất | Soát xét | Không |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/NAB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 42 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 3 năm 2025.pdf](<../../vietstock_bctc/NAB/2025/BCTC%20Hợp%20nhất%20quý%203%20năm%202025.pdf>) | 43 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [NAB NAMABANK_2025_Q2_BCTC HN.pdf](<../../vietstock_bctc/NAB/2025/NAB%20NAMABANK_2025_Q2_BCTC%20HN.pdf>) | 44 | Quý 2 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [NAB NAMABANK_2025_Q2_BCTC RL.pdf](<../../vietstock_bctc/NAB/2025/NAB%20NAMABANK_2025_Q2_BCTC%20RL.pdf>) | 44 | Quý 2 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [NAB namabank_2025_q4_bctc-hn.pdf](<../../vietstock_bctc/NAB/2025/NAB%20namabank_2025_q4_bctc-hn.pdf>) | 44 | Quý 4 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ quý 1 năm 2026.pdf](<../../vietstock_bctc/NAB/2026/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202026.pdf>) | 42 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/NAB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 42 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2026.pdf](<../../vietstock_bctc/NAB/2026/BCTC%20Hợp%20nhất%20quý%201%20năm%202026.pdf>) | 42 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/NAB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 42 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### NVB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [6_nvb_2026_2_3_925648e_vi_baocaotaichinh_q1_2025_riengle_signed.pdf](<../../vietstock_bctc/NVB/2025/6_nvb_2026_2_3_925648e_vi_baocaotaichinh_q1_2025_riengle_signed.pdf>) | 56 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../vietstock_bctc/NVB/2025/BCTC%20Công%20ty%20mẹ%20Kiểm%20toán%20năm%202025.pdf>) | 57 | Năm | Riêng lẻ/CT mẹ | Kiểm toán | Không |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/NVB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 52 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 3 năm 2025.pdf](<../../vietstock_bctc/NVB/2025/BCTC%20Công%20ty%20mẹ%20quý%203%20năm%202025.pdf>) | 53 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../vietstock_bctc/NVB/2025/BCTC%20Hợp%20nhất%20Kiểm%20toán%20năm%202025.pdf>) | 58 | Năm | Hợp nhất | Kiểm toán | Không |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/NVB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 51 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 3 năm 2025.pdf](<../../vietstock_bctc/NVB/2025/BCTC%20Hợp%20nhất%20quý%203%20năm%202025.pdf>) | 54 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 4 năm 2025.pdf](<../../vietstock_bctc/NVB/2025/BCTC%20Hợp%20nhất%20quý%204%20năm%202025.pdf>) | 55 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [NVB VI_BaoCaoTaiChinh_Q2_2025_hopnhat.pdf](<../../vietstock_bctc/NVB/2025/NVB%20VI_BaoCaoTaiChinh_Q2_2025_hopnhat.pdf>) | 54 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [VI_BaoCaoTaiChinh_BanNien_2025_HopNhat.pdf](<../../vietstock_bctc/NVB/2025/VI_BaoCaoTaiChinh_BanNien_2025_HopNhat.pdf>) | 57 | 6 tháng | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [VI_BaoCaoTaiChinh_BanNien_2025_Riengle.pdf](<../../vietstock_bctc/NVB/2025/VI_BaoCaoTaiChinh_BanNien_2025_Riengle.pdf>) | 56 | 6 tháng | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [VI_BaoCaoTaiChinh_Q2_2025_riengle.pdf](<../../vietstock_bctc/NVB/2025/VI_BaoCaoTaiChinh_Q2_2025_riengle.pdf>) | 52 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [2_nvb_2026_7_30_2bf1dd5_bctc__rieng_le__tieng_viet__q2_2026_signed.pdf](<../../vietstock_bctc/NVB/2026/2_nvb_2026_7_30_2bf1dd5_bctc__rieng_le__tieng_viet__q2_2026_signed.pdf>) | 49 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [4_nvb_2026_5_4_fbaa039_vi_baocaotaichinh_riengle_q1_2026_signed.pdf](<../../vietstock_bctc/NVB/2026/4_nvb_2026_5_4_fbaa039_vi_baocaotaichinh_riengle_q1_2026_signed.pdf>) | 53 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC - HOP NHAT - TIENG VIET - Q1.2026.pdf](<../../vietstock_bctc/NVB/2026/BCTC%20-%20HOP%20NHAT%20-%20TIENG%20VIET%20-%20Q1.2026.pdf>) | 54 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC - HOP NHAT - TIENG VIET - Q2.2026.pdf](<../../vietstock_bctc/NVB/2026/BCTC%20-%20HOP%20NHAT%20-%20TIENG%20VIET%20-%20Q2.2026.pdf>) | 53 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### OCB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../vietstock_bctc/OCB/2025/BCTC%20Công%20ty%20mẹ%20Kiểm%20toán%20năm%202025.pdf>) | 202 | Năm | Riêng lẻ/CT mẹ | Kiểm toán | Không |
| [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/OCB/2025/BCTC%20Công%20ty%20mẹ%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 200 | 6 tháng | Riêng lẻ/CT mẹ | Soát xét | Không |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/OCB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 78 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2025.pdf](<../../vietstock_bctc/OCB/2025/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202025.pdf>) | 79 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 3 năm 2025.pdf](<../../vietstock_bctc/OCB/2025/BCTC%20Công%20ty%20mẹ%20quý%203%20năm%202025.pdf>) | 41 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 4 năm 2025.pdf](<../../vietstock_bctc/OCB/2025/BCTC%20Công%20ty%20mẹ%20quý%204%20năm%202025.pdf>) | 42 | Quý 4 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../vietstock_bctc/OCB/2025/BCTC%20Hợp%20nhất%20Kiểm%20toán%20năm%202025.pdf>) | 206 | Năm | Hợp nhất | Kiểm toán | Không |
| [BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/OCB/2025/BCTC%20Hợp%20nhất%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 202 | 6 tháng | Hợp nhất | Soát xét | Không |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/OCB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 79 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2025.pdf](<../../vietstock_bctc/OCB/2025/BCTC%20Hợp%20nhất%20quý%202%20năm%202025.pdf>) | 79 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 3 năm 2025.pdf](<../../vietstock_bctc/OCB/2025/BCTC%20Hợp%20nhất%20quý%203%20năm%202025.pdf>) | 41 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 4 năm 2025.pdf](<../../vietstock_bctc/OCB/2025/BCTC%20Hợp%20nhất%20quý%204%20năm%202025.pdf>) | 43 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ quý 1 năm 2026.pdf](<../../vietstock_bctc/OCB/2026/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202026.pdf>) | 78 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/OCB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 41 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2026.pdf](<../../vietstock_bctc/OCB/2026/BCTC%20Hợp%20nhất%20quý%201%20năm%202026.pdf>) | 78 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/OCB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 42 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### PGB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [3_pgb_2025_10_22_8eac562_vi_baocaotaichinh_q3_2025.pdf](<../../vietstock_bctc/PGB/2025/3_pgb_2025_10_22_8eac562_vi_baocaotaichinh_q3_2025.pdf>) | 49 | Quý 3 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [4_pgb_2026_1_22_d793078_vi_baocaotaichinh_q4_2025.pdf](<../../vietstock_bctc/PGB/2025/4_pgb_2026_1_22_d793078_vi_baocaotaichinh_q4_2025.pdf>) | 49 | Quý 4 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [BCTC Kiểm toán năm 2025.pdf](<../../vietstock_bctc/PGB/2025/BCTC%20Kiểm%20toán%20năm%202025.pdf>) | 58 | Năm | Cần xác thực | Kiểm toán | Scope Requires Source Authentication |
| [BCTC Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/PGB/2025/BCTC%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 54 | 6 tháng | Cần xác thực | Soát xét | Scope Requires Source Authentication |
| [BCTC quý 1 năm 2025.pdf](<../../vietstock_bctc/PGB/2025/BCTC%20quý%201%20năm%202025.pdf>) | 49 | Quý 1 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [1_pgb_2026_4_28_15bbc70_vi_baocaotaichinh_q1_2026.pdf](<../../vietstock_bctc/PGB/2026/1_pgb_2026_4_28_15bbc70_vi_baocaotaichinh_q1_2026.pdf>) | 49 | Quý 1 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [2_pgb_2026_7_22_3a0f521_vi_baocaotaichinh_q2_2026.pdf](<../../vietstock_bctc/PGB/2026/2_pgb_2026_7_22_3a0f521_vi_baocaotaichinh_q2_2026.pdf>) | 49 | Quý 2 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |

### SGB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BAO-CAO-TAI-CHINH-HOP-NHAT-QUY-3---20205.pdf](<../../vietstock_bctc/SGB/2025/BAO-CAO-TAI-CHINH-HOP-NHAT-QUY-3---20205.pdf>) | 46 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BAO-CAO-TAI-CHINH-HOP-NHAT-QUY-4---20205.pdf](<../../vietstock_bctc/SGB/2025/BAO-CAO-TAI-CHINH-HOP-NHAT-QUY-4---20205.pdf>) | 53 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BAO-CAO-TAI-CHINH-RIENG-LE-QUY-3---2025.pdf](<../../vietstock_bctc/SGB/2025/BAO-CAO-TAI-CHINH-RIENG-LE-QUY-3---2025.pdf>) | 46 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BAO-CAO-TAI-CHINH-RIENG-LE-QUY-4---2025.pdf](<../../vietstock_bctc/SGB/2025/BAO-CAO-TAI-CHINH-RIENG-LE-QUY-4---2025.pdf>) | 53 | Quý 4 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/SGB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 44 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/SGB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 43 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC-hop-nhat-da-duoc-kiem-toan-2025.pdf](<../../vietstock_bctc/SGB/2025/BCTC-hop-nhat-da-duoc-kiem-toan-2025.pdf>) | 55 | Cần xác thực | Hợp nhất | Kiểm toán | Period Requires Source Authentication |
| [BCTC-rieng-le-da-duoc-kiem-toan-2025.pdf](<../../vietstock_bctc/SGB/2025/BCTC-rieng-le-da-duoc-kiem-toan-2025.pdf>) | 55 | Cần xác thực | Riêng lẻ/CT mẹ | Kiểm toán | Period Requires Source Authentication |
| [BCTCBNHN.pdf](<../../vietstock_bctc/SGB/2025/BCTCBNHN.pdf>) | 56 | Cần xác thực | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Period Requires Source Authentication; Assurance Requires Source Authentication |
| [BCTCBNRL.pdf](<../../vietstock_bctc/SGB/2025/BCTCBNRL.pdf>) | 56 | Cần xác thực | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Period Requires Source Authentication; Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [5_sgb_2026_7_27_989deeb_vi__bao_cao_tai_chinh_hop_nhat_q22026_daky.pdf](<../../vietstock_bctc/SGB/2026/5_sgb_2026_7_27_989deeb_vi__bao_cao_tai_chinh_hop_nhat_q22026_daky.pdf>) | 52 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [7_sgb_2026_7_27_a0f7e4f_vi__bao_cao_tai_chinh_q22026_daky.pdf](<../../vietstock_bctc/SGB/2026/7_sgb_2026_7_27_a0f7e4f_vi__bao_cao_tai_chinh_q22026_daky.pdf>) | 52 | Quý 2 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [BCTC-HN-quy-1---2026_VIE_0001.pdf](<../../vietstock_bctc/SGB/2026/BCTC-HN-quy-1---2026_VIE_0001.pdf>) | 46 | Quý 1 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [BCTC-Rieng-le-quy-1---2026_VIE.pdf](<../../vietstock_bctc/SGB/2026/BCTC-Rieng-le-quy-1---2026_VIE.pdf>) | 46 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |

### SHB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [20260130 - SHB - Bao cao tai chinh Q4.2025 Rieng le.pdf](<../../vietstock_bctc/SHB/2025/20260130%20-%20SHB%20-%20Bao%20cao%20tai%20chinh%20Q4.2025%20Rieng%20le.pdf>) | 41 | Quý 4 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../vietstock_bctc/SHB/2025/BCTC%20Công%20ty%20mẹ%20Kiểm%20toán%20năm%202025.pdf>) | 60 | Năm | Riêng lẻ/CT mẹ | Kiểm toán | Không |
| [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/SHB/2025/BCTC%20Công%20ty%20mẹ%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 51 | 6 tháng | Riêng lẻ/CT mẹ | Soát xét | Không |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/SHB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 39 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2025.pdf](<../../vietstock_bctc/SHB/2025/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202025.pdf>) | 39 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 3 năm 2025.pdf](<../../vietstock_bctc/SHB/2025/BCTC%20Công%20ty%20mẹ%20quý%203%20năm%202025.pdf>) | 41 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../vietstock_bctc/SHB/2025/BCTC%20Hợp%20nhất%20Kiểm%20toán%20năm%202025.pdf>) | 68 | Năm | Hợp nhất | Kiểm toán | Không |
| [BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/SHB/2025/BCTC%20Hợp%20nhất%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 56 | 6 tháng | Hợp nhất | Soát xét | Không |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/SHB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 41 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2025.pdf](<../../vietstock_bctc/SHB/2025/BCTC%20Hợp%20nhất%20quý%202%20năm%202025.pdf>) | 41 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 3 năm 2025.pdf](<../../vietstock_bctc/SHB/2025/BCTC%20Hợp%20nhất%20quý%203%20năm%202025.pdf>) | 43 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 4 năm 2025.pdf](<../../vietstock_bctc/SHB/2025/BCTC%20Hợp%20nhất%20quý%204%20năm%202025.pdf>) | 43 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ quý 1 năm 2026.pdf](<../../vietstock_bctc/SHB/2026/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202026.pdf>) | 41 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/SHB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 41 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2026.pdf](<../../vietstock_bctc/SHB/2026/BCTC%20Hợp%20nhất%20quý%201%20năm%202026.pdf>) | 42 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/SHB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 42 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### SSB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../vietstock_bctc/SSB/2025/BCTC%20Công%20ty%20mẹ%20Kiểm%20toán%20năm%202025.pdf>) | 73 | Năm | Riêng lẻ/CT mẹ | Kiểm toán | Không |
| [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/SSB/2025/BCTC%20Công%20ty%20mẹ%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 65 | 6 tháng | Riêng lẻ/CT mẹ | Soát xét | Không |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/SSB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 60 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2025.pdf](<../../vietstock_bctc/SSB/2025/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202025.pdf>) | 62 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 3 năm 2025.pdf](<../../vietstock_bctc/SSB/2025/BCTC%20Công%20ty%20mẹ%20quý%203%20năm%202025.pdf>) | 60 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 4 năm 2025.pdf](<../../vietstock_bctc/SSB/2025/BCTC%20Công%20ty%20mẹ%20quý%204%20năm%202025.pdf>) | 65 | Quý 4 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../vietstock_bctc/SSB/2025/BCTC%20Hợp%20nhất%20Kiểm%20toán%20năm%202025.pdf>) | 77 | Năm | Hợp nhất | Kiểm toán | Không |
| [BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/SSB/2025/BCTC%20Hợp%20nhất%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 71 | 6 tháng | Hợp nhất | Soát xét | Không |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/SSB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 66 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2025.pdf](<../../vietstock_bctc/SSB/2025/BCTC%20Hợp%20nhất%20quý%202%20năm%202025.pdf>) | 66 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 3 năm 2025.pdf](<../../vietstock_bctc/SSB/2025/BCTC%20Hợp%20nhất%20quý%203%20năm%202025.pdf>) | 68 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 4 năm 2025.pdf](<../../vietstock_bctc/SSB/2025/BCTC%20Hợp%20nhất%20quý%204%20năm%202025.pdf>) | 70 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ quý 1 năm 2026.pdf](<../../vietstock_bctc/SSB/2026/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202026.pdf>) | 63 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/SSB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 62 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2026.pdf](<../../vietstock_bctc/SSB/2026/BCTC%20Hợp%20nhất%20quý%201%20năm%202026.pdf>) | 67 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/SSB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 68 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### STB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../vietstock_bctc/STB/2025/BCTC%20Công%20ty%20mẹ%20Kiểm%20toán%20năm%202025.pdf>) | 101 | Năm | Riêng lẻ/CT mẹ | Kiểm toán | Không |
| [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/STB/2025/BCTC%20Công%20ty%20mẹ%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 99 | 6 tháng | Riêng lẻ/CT mẹ | Soát xét | Không |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/STB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 47 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2025.pdf](<../../vietstock_bctc/STB/2025/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202025.pdf>) | 48 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 3 năm 2025.pdf](<../../vietstock_bctc/STB/2025/BCTC%20Công%20ty%20mẹ%20quý%203%20năm%202025.pdf>) | 47 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 4 năm 2025.pdf](<../../vietstock_bctc/STB/2025/BCTC%20Công%20ty%20mẹ%20quý%204%20năm%202025.pdf>) | 47 | Quý 4 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../vietstock_bctc/STB/2025/BCTC%20Hợp%20nhất%20Kiểm%20toán%20năm%202025.pdf>) | 108 | Năm | Hợp nhất | Kiểm toán | Không |
| [BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/STB/2025/BCTC%20Hợp%20nhất%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 104 | 6 tháng | Hợp nhất | Soát xét | Không |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/STB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 47 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2025.pdf](<../../vietstock_bctc/STB/2025/BCTC%20Hợp%20nhất%20quý%202%20năm%202025.pdf>) | 48 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 3 năm 2025.pdf](<../../vietstock_bctc/STB/2025/BCTC%20Hợp%20nhất%20quý%203%20năm%202025.pdf>) | 47 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 4 năm 2025.pdf](<../../vietstock_bctc/STB/2025/BCTC%20Hợp%20nhất%20quý%204%20năm%202025.pdf>) | 47 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ quý 1 năm 2026.pdf](<../../vietstock_bctc/STB/2026/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202026.pdf>) | 47 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/STB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 44 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2026.pdf](<../../vietstock_bctc/STB/2026/BCTC%20Hợp%20nhất%20quý%201%20năm%202026.pdf>) | 45 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/STB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 46 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### TCB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../vietstock_bctc/TCB/2025/BCTC%20Công%20ty%20mẹ%20Kiểm%20toán%20năm%202025.pdf>) | 90 | Năm | Riêng lẻ/CT mẹ | Kiểm toán | Không |
| [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/TCB/2025/BCTC%20Công%20ty%20mẹ%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 86 | 6 tháng | Riêng lẻ/CT mẹ | Soát xét | Không |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/TCB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 71 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2025.pdf](<../../vietstock_bctc/TCB/2025/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202025.pdf>) | 72 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 3 năm 2025.pdf](<../../vietstock_bctc/TCB/2025/BCTC%20Công%20ty%20mẹ%20quý%203%20năm%202025.pdf>) | 72 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 4 năm 2025.pdf](<../../vietstock_bctc/TCB/2025/BCTC%20Công%20ty%20mẹ%20quý%204%20năm%202025.pdf>) | 73 | Quý 4 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../vietstock_bctc/TCB/2025/BCTC%20Hợp%20nhất%20Kiểm%20toán%20năm%202025.pdf>) | 104 | Năm | Hợp nhất | Kiểm toán | Không |
| [BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/TCB/2025/BCTC%20Hợp%20nhất%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 95 | 6 tháng | Hợp nhất | Soát xét | Không |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/TCB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 75 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2025.pdf](<../../vietstock_bctc/TCB/2025/BCTC%20Hợp%20nhất%20quý%202%20năm%202025.pdf>) | 79 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 3 năm 2025.pdf](<../../vietstock_bctc/TCB/2025/BCTC%20Hợp%20nhất%20quý%203%20năm%202025.pdf>) | 83 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 4 năm 2025.pdf](<../../vietstock_bctc/TCB/2025/BCTC%20Hợp%20nhất%20quý%204%20năm%202025.pdf>) | 87 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ quý 1 năm 2026.pdf](<../../vietstock_bctc/TCB/2026/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202026.pdf>) | 71 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/TCB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 70 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2026.pdf](<../../vietstock_bctc/TCB/2026/BCTC%20Hợp%20nhất%20quý%201%20năm%202026.pdf>) | 82 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/TCB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 84 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### TPB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../vietstock_bctc/TPB/2025/BCTC%20Công%20ty%20mẹ%20Kiểm%20toán%20năm%202025.pdf>) | 93 | Năm | Riêng lẻ/CT mẹ | Kiểm toán | Không |
| [BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/TPB/2025/BCTC%20Công%20ty%20mẹ%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 91 | 6 tháng | Riêng lẻ/CT mẹ | Soát xét | Không |
| [BCTC Công ty mẹ quý 1 năm 2025.pdf](<../../vietstock_bctc/TPB/2025/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202025.pdf>) | 54 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2025.pdf](<../../vietstock_bctc/TPB/2025/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202025.pdf>) | 52 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 3 năm 2025.pdf](<../../vietstock_bctc/TPB/2025/BCTC%20Công%20ty%20mẹ%20quý%203%20năm%202025.pdf>) | 54 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 4 năm 2025.pdf](<../../vietstock_bctc/TPB/2025/BCTC%20Công%20ty%20mẹ%20quý%204%20năm%202025.pdf>) | 61 | Quý 4 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../vietstock_bctc/TPB/2025/BCTC%20Hợp%20nhất%20Kiểm%20toán%20năm%202025.pdf>) | 108 | Năm | Hợp nhất | Kiểm toán | Không |
| [BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf](<../../vietstock_bctc/TPB/2025/BCTC%20Hợp%20nhất%20Soát%20xét%206%20tháng%20đầu%20năm%202025.pdf>) | 97 | 6 tháng | Hợp nhất | Soát xét | Không |
| [BCTC Hợp nhất quý 1 năm 2025.pdf](<../../vietstock_bctc/TPB/2025/BCTC%20Hợp%20nhất%20quý%201%20năm%202025.pdf>) | 54 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2025.pdf](<../../vietstock_bctc/TPB/2025/BCTC%20Hợp%20nhất%20quý%202%20năm%202025.pdf>) | 52 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 3 năm 2025.pdf](<../../vietstock_bctc/TPB/2025/BCTC%20Hợp%20nhất%20quý%203%20năm%202025.pdf>) | 54 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 4 năm 2025.pdf](<../../vietstock_bctc/TPB/2025/BCTC%20Hợp%20nhất%20quý%204%20năm%202025.pdf>) | 63 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ quý 1 năm 2026.pdf](<../../vietstock_bctc/TPB/2026/BCTC%20Công%20ty%20mẹ%20quý%201%20năm%202026.pdf>) | 58 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/TPB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 58 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 1 năm 2026.pdf](<../../vietstock_bctc/TPB/2026/BCTC%20Hợp%20nhất%20quý%201%20năm%202026.pdf>) | 64 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/TPB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 67 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### VAB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [20250815 - VAB - BCTC HN BAN NIEN 2025_0001.pdf](<../../vietstock_bctc/VAB/2025/20250815%20-%20VAB%20-%20BCTC%20HN%20BAN%20NIEN%202025_0001.pdf>) | 53 | 6 tháng | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [20250815 - VAB - BCTC RIENG LE BAN NIEN 2025_0001_0001.pdf](<../../vietstock_bctc/VAB/2025/20250815%20-%20VAB%20-%20BCTC%20RIENG%20LE%20BAN%20NIEN%202025_0001_0001.pdf>) | 53 | 6 tháng | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [2_vab_2025_4_15_527ed46_vi_baocaotaichinh_q1_2025.pdf](<../../vietstock_bctc/VAB/2025/2_vab_2025_4_15_527ed46_vi_baocaotaichinh_q1_2025.pdf>) | 46 | Quý 1 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [2_vab_2025_4_15_d453cb6_vn_baocaotaichinh_q1_2025.pdf](<../../vietstock_bctc/VAB/2025/2_vab_2025_4_15_d453cb6_vn_baocaotaichinh_q1_2025.pdf>) | 46 | Quý 1 | Cần xác thực | Cần xác thực | Scope Requires Source Authentication; Assurance Requires Source Authentication |
| [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](<../../vietstock_bctc/VAB/2025/BCTC%20Công%20ty%20mẹ%20Kiểm%20toán%20năm%202025.pdf>) | 55 | Năm | Riêng lẻ/CT mẹ | Kiểm toán | Không |
| [BCTC Công ty mẹ quý 3 năm 2025.pdf](<../../vietstock_bctc/VAB/2025/BCTC%20Công%20ty%20mẹ%20quý%203%20năm%202025.pdf>) | 48 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 4 năm 2025.pdf](<../../vietstock_bctc/VAB/2025/BCTC%20Công%20ty%20mẹ%20quý%204%20năm%202025.pdf>) | 48 | Quý 4 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC HOP NHAT QUY 2.2025 TANH_0001-da nen.pdf](<../../vietstock_bctc/VAB/2025/BCTC%20HOP%20NHAT%20QUY%202.2025%20TANH_0001-da%20nen.pdf>) | 47 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC HOP NHAT QUY 2.2025 TVIET_0001-da nen.pdf](<../../vietstock_bctc/VAB/2025/BCTC%20HOP%20NHAT%20QUY%202.2025%20TVIET_0001-da%20nen.pdf>) | 46 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất Kiểm toán năm 2025.pdf](<../../vietstock_bctc/VAB/2025/BCTC%20Hợp%20nhất%20Kiểm%20toán%20năm%202025.pdf>) | 55 | Năm | Hợp nhất | Kiểm toán | Không |
| [BCTC Hợp nhất quý 3 năm 2025.pdf](<../../vietstock_bctc/VAB/2025/BCTC%20Hợp%20nhất%20quý%203%20năm%202025.pdf>) | 48 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 4 năm 2025.pdf](<../../vietstock_bctc/VAB/2025/BCTC%20Hợp%20nhất%20quý%204%20năm%202025.pdf>) | 48 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC RIENG LE QUY 2.2025-TV_0001-da nen.pdf](<../../vietstock_bctc/VAB/2025/BCTC%20RIENG%20LE%20QUY%202.2025-TV_0001-da%20nen.pdf>) | 46 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/VAB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 48 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/VAB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 49 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Q1.2026 RIENG LE_0001.pdf](<../../vietstock_bctc/VAB/2026/BCTC%20Q1.2026%20RIENG%20LE_0001.pdf>) | 48 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |

### VBB

#### 2025

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [000000014895152_VI_BaoCaoTaiChinh_HopNhat_Q1_2025.pdf](<../../vietstock_bctc/VBB/2025/000000014895152_VI_BaoCaoTaiChinh_HopNhat_Q1_2025.pdf>) | 26 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [000000014895177_VI_BaoCaoTaiChinh_RiengLe_Q1_2025.pdf](<../../vietstock_bctc/VBB/2025/000000014895177_VI_BaoCaoTaiChinh_RiengLe_Q1_2025.pdf>) | 26 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [1_vbb_2025_8_1_de20fa4_vi_baocaotaichinh_riengle_q2_2025.pdf](<../../vietstock_bctc/VBB/2025/1_vbb_2025_8_1_de20fa4_vi_baocaotaichinh_riengle_q2_2025.pdf>) | 25 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [2_vbb_2025_8_1_afc1d54_vi_baocaotaichinh_hopnhat_q2_2025.pdf](<../../vietstock_bctc/VBB/2025/2_vbb_2025_8_1_afc1d54_vi_baocaotaichinh_hopnhat_q2_2025.pdf>) | 25 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [2_vbb_2026_3_23_b2c1e44_vi_baocaotaichinh_kiemtoan_riengle_2025.pdf](<../../vietstock_bctc/VBB/2025/2_vbb_2026_3_23_b2c1e44_vi_baocaotaichinh_kiemtoan_riengle_2025.pdf>) | 83 | Cần xác thực | Riêng lẻ/CT mẹ | Kiểm toán | Period Requires Source Authentication |
| [3_vbb_2025_8_6_8bb1ede_vi_baocaotaichinh_riengle_bannien_2025.pdf](<../../vietstock_bctc/VBB/2025/3_vbb_2025_8_6_8bb1ede_vi_baocaotaichinh_riengle_bannien_2025.pdf>) | 81 | 6 tháng | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [3_vbb_2025_8_6_d00b2c1_vi_baocaotaichinh_hopnhat_bannien_2025.pdf](<../../vietstock_bctc/VBB/2025/3_vbb_2025_8_6_d00b2c1_vi_baocaotaichinh_hopnhat_bannien_2025.pdf>) | 82 | 6 tháng | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [3_vbb_2026_2_2_a18dc42_vi_baocaotaichinh_riengle_q4_2025.pdf](<../../vietstock_bctc/VBB/2025/3_vbb_2026_2_2_a18dc42_vi_baocaotaichinh_riengle_q4_2025.pdf>) | 40 | Quý 4 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [3_vbb_2026_3_23_3110a7d_vi_baocaotaichinh_kiemtoan_hopnhat_2025.pdf](<../../vietstock_bctc/VBB/2025/3_vbb_2026_3_23_3110a7d_vi_baocaotaichinh_kiemtoan_hopnhat_2025.pdf>) | 83 | Cần xác thực | Hợp nhất | Kiểm toán | Period Requires Source Authentication |
| [92-BCTC-hopnhat-Q3-VIE.pdf](<../../vietstock_bctc/VBB/2025/92-BCTC-hopnhat-Q3-VIE.pdf>) | 41 | Quý 3 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [92-BCTC-riengle-Q3-VIE(1).pdf](<../../vietstock_bctc/VBB/2025/92-BCTC-riengle-Q3-VIE(1).pdf>) | 40 | Quý 3 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 4 năm 2025.pdf](<../../vietstock_bctc/VBB/2025/BCTC%20Hợp%20nhất%20quý%204%20năm%202025.pdf>) | 40 | Quý 4 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
#### 2026

| File PDF | Trang | Kỳ theo tên file | Loại báo cáo theo tên file | Kiểm toán theo tên file | Cần kiểm tra lại |
|---|---:|---|---|---|---|
| [28-BCTC-Q1_2026-hopnhat-E.pdf](<../../vietstock_bctc/VBB/2026/28-BCTC-Q1_2026-hopnhat-E.pdf>) | 40 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [28-BCTC-Q1_2026-hopnhat-V.pdf](<../../vietstock_bctc/VBB/2026/28-BCTC-Q1_2026-hopnhat-V.pdf>) | 45 | Quý 1 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |
| [3_vbb_2026_5_2_fa0b162_vi_baocaotaichinh_riengle_q1_2026.pdf](<../../vietstock_bctc/VBB/2026/3_vbb_2026_5_2_fa0b162_vi_baocaotaichinh_riengle_q1_2026.pdf>) | 43 | Quý 1 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Công ty mẹ quý 2 năm 2026.pdf](<../../vietstock_bctc/VBB/2026/BCTC%20Công%20ty%20mẹ%20quý%202%20năm%202026.pdf>) | 46 | Quý 2 | Riêng lẻ/CT mẹ | Cần xác thực | Assurance Requires Source Authentication |
| [BCTC Hợp nhất quý 2 năm 2026.pdf](<../../vietstock_bctc/VBB/2026/BCTC%20Hợp%20nhất%20quý%202%20năm%202026.pdf>) | 47 | Quý 2 | Hợp nhất | Cần xác thực | Assurance Requires Source Authentication |

### VCB

Đã xử lý trong corpus 8 ngân hàng; **không đưa bất kỳ PDF nào của ngân hàng này vào paid frontier**. Xem danh sách PDF đã chọn tại [ma trận 8 ngân hàng](FINANCIAL_REPORT_INVENTORY_8BANK.md).


### VIB

Đã xử lý trong corpus 8 ngân hàng; **không đưa bất kỳ PDF nào của ngân hàng này vào paid frontier**. Xem danh sách PDF đã chọn tại [ma trận 8 ngân hàng](FINANCIAL_REPORT_INVENTORY_8BANK.md).


### VPB

Đã xử lý trong corpus 8 ngân hàng; **không đưa bất kỳ PDF nào của ngân hàng này vào paid frontier**. Xem danh sách PDF đã chọn tại [ma trận 8 ngân hàng](FINANCIAL_REPORT_INVENTORY_8BANK.md).


## Phân biệt trạng thái

- **Có file nguồn:** PDF đã được xác thực đúng nội dung byte và mở được; chưa nói rằng một family cụ thể có xuất hiện.
- **NOT_OBSERVED:** sau khi đọc đúng phạm vi PDF, family không xuất hiện. Đây không phải lỗi.
- **UNRESOLVED:** family có xuất hiện nhưng kỳ, đơn vị, cấu trúc hoặc mapping chưa đủ chắc chắn.
- **SOURCE_ONLY:** nội dung nhìn thấy nhưng không thuộc khoản mục đích của family đang xét; vẫn được giữ để kiểm toán.

## Truy vết kỹ thuật

Các định danh kỹ thuật được giữ ở manifest JSON đi kèm, không dùng làm tên nhận diện chính trong tài liệu này.
