# Family 6 — Phân tích cho vay theo loại hình

Checkpoint audit trên tập bất biến 204 PDF của 19 ngân hàng, chỉ gồm báo cáo từ năm 2025 đến hiện tại. Đây là bằng chứng staging; chưa thay thế hai bảng tổng hợp cuối dự án.

| Trạng thái | Baseline | Sau audit | Chênh lệch |
|---|---:|---:|---:|
| READY | 102 | 173 | +71 |
| NOT_OBSERVED | 12 | 12 | 0 |
| UNRESOLVED | 90 | 19 | -71 |

- 102/102 PDF READY cũ vẫn READY; không có READY regression.
- 12/12 PDF NOT_OBSERVED giữ nguyên sau khi rà đúng phạm vi; không có false-N hoặc N drift.
- 71 PDF chuyển đúng từ UNRESOLVED sang READY nhờ alias cách viết, cặp anchor generic và header kỳ `Số cuối quý`; không có logic theo ngân hàng, tên file hoặc số trang.
- Kết quả cuối có 915 mapping; không trùng ReportNormId trong cùng PDF và đúng thứ tự schema.
- 70 test engine/query/runner liên quan passed; Ruff passed.
- Regression trên toàn bộ 140 PDF lịch sử của 8 ngân hàng cũ vẫn là 140 READY / 0 NOT_OBSERVED / 0 UNRESOLVED và 861 mapping. Trạng thái, candidate count và toàn bộ nội dung mapping không đổi so với checkpoint cũ.

## Cấu trúc schema đã nhận diện

| Cách trình bày trên PDF | ReportNormId | Số PDF READY có mapping |
|---|---:|---:|
| Tổng phân tích theo loại hình cho vay | 717 | 173 |
| Cho vay tổ chức kinh tế, cá nhân trong nước | 718 | 173 |
| Cho thuê tài chính | 719 | 25 |
| Cho vay từ vốn Chính phủ/tổ chức quốc tế | 720 | 0 |
| Cho vay theo chỉ định của Chính phủ | 6057 | 23 |
| Cho vay tổ chức/cá nhân nước ngoài | 721 | 66 |
| Cho vay chiết khấu thương phiếu, công cụ chuyển nhượng và giấy tờ có giá | 722 | 121 |
| Các khoản trả thay khách hàng | 723 | 142 |
| Nợ cho vay được khoanh và nợ chờ xử lý | 724 | 52 |
| Cho vay bằng vốn tài trợ, ủy thác đầu tư | 725 | 101 |
| Cho vay khác | 726 | 28 |
| Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán | 5745 | 11 |

ReportNormId 716 là owner “Cho vay khách hàng”; 717 là nhánh “Phân tích theo loại hình cho vay”. Các cách viết tắt như `TCKT`, `GTCG`, cách có/không có dấu phẩy và hậu tố chú thích `(i)` chỉ là alias nguồn, không tạo ID mới.

Các biến thể nguồn đáng chú ý:

- KLB và một số báo cáo VAB chỉ có một loại là “Cho vay các tổ chức kinh tế, cá nhân trong nước”, sau đó là dòng tổng bằng đúng khoản mục này.
- BAB dùng “Cho vay khác đối với các tổ chức kinh tế, cá nhân trong nước”.
- OCB dùng “Các khoản nợ chờ xử lý”.
- PGB dùng “Cho vay bằng vốn tài trợ, ủy thác đầu tư”.
- SGB dùng “Cấp tín dụng khác”; VBB dùng “Cho vay thấu chi”. Hai cách trình bày này được cộng vào 726, không tạo ID riêng.
- SSB có khoản cho vay trong nghiệp vụ thư tín dụng trả chậm; khoản này được giữ SOURCE_ONLY và chỉ tham gia kiểm tra tổng 717 vì schema hiện chưa có child cùng bản chất.

## 19 PDF còn UNRESOLVED

Đã rà toàn bộ schema cho các dòng dưới đây. Không trường hợp nào là thiếu ID cho các khoản mục chuẩn 717–725. Có 12 trường hợp là gap biểu diễn/ghép trang của thuật toán và 7 trường hợp là JSON nguồn thiếu hoặc hỏng; không ép blank thành zero và không sửa chuỗi OCR hỏng thành dấu gạch.

| # | Ngân hàng | File PDF | Kỳ / loại báo cáo | Trang | Khoản mục nhìn thấy | Schema gần nhất | Kết luận dễ đọc |
|---:|---|---|---|---:|---|---|---|
| 1 | ABB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | Q1/2025, hợp nhất, chưa kiểm toán | 17 | Bảng đầy đủ; ô kỳ hiện tại của “Cho thuê tài chính” là `-接着` | 717, 718–725 | **LỖI SOURCE/OCR** — chuỗi không phải số hoặc dấu gạch xác thực; không tự đổi thành zero. |
| 2 | ABB | `phpkgbljk-bctc-hn-q3-2025-68fb4c313c9de.pdf` | Q3/2025, hợp nhất, chưa kiểm toán | 17 | Bảng đầy đủ; các ô kỳ trước của cho thuê tài chính, chỉ định Chính phủ và nợ chờ xử lý bị blank | 717, 718–725 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — tổng chỉ khớp nếu tự coi blank là zero; nguồn JSON không cho phép kết luận đó. |
| 3 | KLB | `BAO CAO TAI CHINH QUY 3.2025 HOP NHAT.pdf` | Q3/2025, hợp nhất | 21 | “Cho vay các tổ chức kinh tế, cá nhân trong nước”; “Cộng” bằng đúng dòng trên | 717, 718 | **CÓ ID PHÙ HỢP, THUẬT TOÁN CHƯA HỖ TRỢ BẢNG CHỈ MỘT LOẠI** — query hiện yêu cầu hai role con; không phải thiếu schema. |
| 4 | KLB | `BAO CAO TAI CHINH QUY 3.2025 RIENG.pdf` | Q3/2025, riêng lẻ | 21 | Cùng cấu trúc một dòng trong nước + tổng | 717, 718 | **GAP BIỂU DIỄN THUẬT TOÁN** — mapping có thể xác định, nhưng cần policy generic một-child + total. |
| 5 | KLB | `BCTC Công ty mẹ quý 2 năm 2025.pdf` | Q2/2025, công ty mẹ | 20 | Cùng cấu trúc một dòng trong nước + tổng | 717, 718 | **GAP BIỂU DIỄN THUẬT TOÁN** — chưa hạ điều kiện hai role vì có thể làm tăng false positive ở bảng ghép nhiều family. |
| 6 | KLB | `BCTC Hợp nhất quý 2 năm 2025.pdf` | Q2/2025, hợp nhất | 20 | Cùng cấu trúc một dòng trong nước + tổng | 717, 718 | **GAP BIỂU DIỄN THUẬT TOÁN** — số và ngày nguồn rõ; chưa có policy query an toàn. |
| 7 | KLB | `bao-cao-tai-chinh-giua-nien-do-q4.2025-hop-nhat-_tv.pdf` | Q4/2025, hợp nhất | 22 | Cùng cấu trúc một dòng trong nước + tổng | 717, 718 | **GAP BIỂU DIỄN THUẬT TOÁN**. |
| 8 | KLB | `bao-cao-tai-chinh-giua-nien-do-q4.2025-rieng_tv.pdf` | Q4/2025, riêng lẻ | 23 | Cùng cấu trúc một dòng trong nước + tổng | 717, 718 | **GAP BIỂU DIỄN THUẬT TOÁN**. |
| 9 | KLB | `BCTC Công ty mẹ quý 1 năm 2026.pdf` | Q1/2026, công ty mẹ | 25 | Cùng cấu trúc một dòng trong nước + tổng | 717, 718 | **GAP BIỂU DIỄN THUẬT TOÁN**. |
| 10 | KLB | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | Q2/2026, công ty mẹ | 25 | Cùng cấu trúc một dòng trong nước + tổng | 717, 718 | **GAP BIỂU DIỄN THUẬT TOÁN**. |
| 11 | KLB | `BCTC Hợp nhất quý 1 năm 2026.pdf` | Q1/2026, hợp nhất | 25 | Cùng cấu trúc một dòng trong nước + tổng | 717, 718 | **GAP BIỂU DIỄN THUẬT TOÁN**. |
| 12 | VAB | `20250815 - VAB - BCTC HN BAN NIEN 2025_0001.pdf` | 6T/2025, hợp nhất | 30 | Một dòng cho vay trong nước + “Tổng cộng”; đơn vị VND | 717, 718 | **GAP BIỂU DIỄN THUẬT TOÁN** — family chắc chắn, nhưng query chưa nhận một-child + total. |
| 13 | VAB | `2_vab_2025_4_15_527ed46_vi_baocaotaichinh_q1_2025.pdf` | Q1/2025, hợp nhất | 30 | Các dòng 718–725; nhiều ô kỳ trước blank và không có dòng tổng trong JSON | 717, 718–725 | **LỖI SOURCE/OCR** — source JSON thiếu total/zero evidence nên không thể khép arithmetic. |
| 14 | VAB | `2_vab_2025_4_15_d453cb6_vn_baocaotaichinh_q1_2025.pdf` | Q1/2025, riêng lẻ | 30 | Bảng đủ và có tổng; ô chiết khấu là `-接着` | 717, 718–725 | **LỖI SOURCE/OCR** — cần đọc lại vùng ô tiền, không sửa bằng rule chuỗi. |
| 15 | VAB | `BCTC Công ty mẹ Kiểm toán năm 2025.pdf` | Năm 2025, công ty mẹ, kiểm toán | 30 | Một dòng cho vay trong nước + “Tổng cộng”; đơn vị VND | 717, 718 | **GAP BIỂU DIỄN THUẬT TOÁN** — mapping rõ nhưng chưa có policy một-child an toàn. |
| 16 | VAB | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | Năm 2025, hợp nhất, kiểm toán | 30 | Một dòng cho vay trong nước + “Tổng cộng”; header `Số cuối năm/Số đầu năm`, JSON không giữ đơn vị | 717, 718 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** đồng thời là gap một-child; không suy VND từ độ lớn số. |
| 17 | VAB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất | 32 | Bảng đủ và có tổng; ô chiết khấu là `-带有` | 717, 718–725 | **LỖI SOURCE/OCR** — source cell hỏng. |
| 18 | VAB | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | Q2/2026, công ty mẹ | 31–32 | Bảng bắt đầu/tiếp diễn qua trang; trang 32 mất owner và ô chiết khấu là `-軟` | 717, 718–725 | **LỖI SOURCE/OCR** và **CHƯA GHÉP ĐƯỢC OWNER GIỮA HAI TRANG**. |
| 19 | VAB | `BCTC Q1.2026 RIENG LE_0001.pdf` | Q1/2026, riêng lẻ | 31–32 | Bốn dòng đầu ở trang 31; bốn dòng sau và tổng ở trang 32 | 717, 718–725 | **GAP GHÉP TRANG** — hai page JSON cộng lại đủ và tổng khớp, nhưng evaluator hiện chỉ giải phần table ở trang đầu. |

### Phân loại 19 residual

| Nhóm nguyên nhân | Số PDF | Ý nghĩa |
|---|---:|---|
| Thuật toán chưa hỗ trợ bảng chỉ một child + total hoặc bảng tách hai trang | 12 | Source/schema đủ; cần policy generic mới và regression rộng trước khi chuyển READY. |
| JSON nguồn thiếu, blank mơ hồ, mất đơn vị hoặc có chuỗi OCR hỏng | 7 | Cần region repair/đọc lại nguồn; không nên chữa bằng alias hay giả định zero. |
| Chưa có khoản mục tương ứng trong schema | 0 | Không có residual nào do thiếu ID 717–725. |

## SOURCE_ONLY nằm trong 38 PDF READY

Các PDF này vẫn READY vì tổng và các khoản mục schema đã khép kín. Dòng SOURCE_ONLY không bị bỏ khỏi arithmetic, nhưng không có mapping 1:1:

- `Cho vay khác`, `Cấp tín dụng khác` và `Cho vay thấu chi` được cộng có bằng chứng vào ReportNormId 726 “Cho vay khác”. Không tạo ID mới chỉ vì ngân hàng dùng cách gọi khác.
- `Cho vay trong nghiệp vụ phát hành thư tín dụng trả chậm có điều khoản trả ngay` có bản chất riêng và không có child tương ứng dưới 717. Dòng này chỉ tham gia tổng 717; giữ `SOURCE_ONLY / KHOẢN MỤC MỚI, CẦN ĐÁNH GIÁ CÓ TẠO ID MỚI HAY KHÔNG`, không ép vào 726.

<details>
<summary>Danh sách đầy đủ 38 dòng SOURCE_ONLY trong PDF READY</summary>

### Được cộng vào ReportNormId 726 — Cho vay khác

- **BAB, “Cho vay khác đối với các tổ chức kinh tế, cá nhân trong nước”:** `1_bab_2026_2_4_4d13ce7_vi_baocaotaichinh_q4_2025.pdf` trang 22; `BAB_BCTC Hop nhat Quy 3.2025_Tieng Viet.pdf` trang 22; `BCTC Hợp nhất quý 1 năm 2025.pdf` trang 22; `BCTC Hợp nhất quý 4 năm 2025.pdf` trang 22.
- **BAB, “Cho vay khác”:** `BCTC Rieng le 2025_Kiem toan.pdf` trang 25.
- **STB, “Cho vay khác”:** `BCTC Công ty mẹ Kiểm toán năm 2025.pdf` trang 41; `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` trang 42; `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` trang 44.
- **VBB, “Cho vay khác”:** `000000014895177_VI_BaoCaoTaiChinh_RiengLe_Q1_2025.pdf` trang 16; `1_vbb_2025_8_1_de20fa4_vi_baocaotaichinh_riengle_q2_2025.pdf` trang 15.
- **SGB, “Cấp tín dụng khác”:** `BAO-CAO-TAI-CHINH-HOP-NHAT-QUY-3---20205.pdf` trang 24; `BAO-CAO-TAI-CHINH-RIENG-LE-QUY-3---2025.pdf` trang 23; `BAO-CAO-TAI-CHINH-RIENG-LE-QUY-4---2025.pdf` trang 23; `BCTC-hop-nhat-da-duoc-kiem-toan-2025.pdf` trang 27; `BCTC-rieng-le-da-duoc-kiem-toan-2025.pdf` trang 27; `5_sgb_2026_7_27_989deeb_vi__bao_cao_tai_chinh_hop_nhat_q22026_daky.pdf` trang 22; `7_sgb_2026_7_27_a0f7e4f_vi__bao_cao_tai_chinh_q22026_daky.pdf` trang 22; `BCTC-HN-quy-1---2026_VIE_0001.pdf` trang 23; `BCTC-Rieng-le-quy-1---2026_VIE.pdf` trang 23.
- **VBB, “Cho vay thấu chi”:** `2_vbb_2026_3_23_b2c1e44_vi_baocaotaichinh_kiemtoan_riengle_2025.pdf` trang 40; `3_vbb_2025_8_6_8bb1ede_vi_baocaotaichinh_riengle_bannien_2025.pdf` trang 39; `3_vbb_2025_8_6_d00b2c1_vi_baocaotaichinh_hopnhat_bannien_2025.pdf` trang 39; `3_vbb_2026_2_2_a18dc42_vi_baocaotaichinh_riengle_q4_2025.pdf` trang 24; `3_vbb_2026_3_23_3110a7d_vi_baocaotaichinh_kiemtoan_hopnhat_2025.pdf` trang 40; `BCTC Hợp nhất quý 4 năm 2025.pdf` trang 25; `3_vbb_2026_5_2_fa0b162_vi_baocaotaichinh_riengle_q1_2026.pdf` trang 28; `BCTC Công ty mẹ quý 2 năm 2026.pdf` trang 30; `BCTC Hợp nhất quý 2 năm 2026.pdf` trang 31.

### Không có child tương ứng; chỉ tham gia tổng ReportNormId 717

- **SSB, “Cho vay trong nghiệp vụ phát hành thư tín dụng trả chậm có điều khoản trả ngay”:** `BCTC Công ty mẹ Kiểm toán năm 2025.pdf` trang 36; `BCTC Công ty mẹ quý 3 năm 2025.pdf` trang 29; `BCTC Công ty mẹ quý 4 năm 2025.pdf` trang 34; `BCTC Hợp nhất Kiểm toán năm 2025.pdf` trang 37; `BCTC Hợp nhất quý 3 năm 2025.pdf` trang 33; `BCTC Hợp nhất quý 4 năm 2025.pdf` trang 34; `source_revisions/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025 - Nguồn chính thức SeABank.pdf` trang 34; `source_revisions/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025 - Nguồn chính thức SeABank.pdf` trang 36; `BCTC Công ty mẹ quý 1 năm 2026.pdf` trang 33; `BCTC Công ty mẹ quý 2 năm 2026.pdf` trang 32.

</details>

## 12 PDF NOT_OBSERVED

NOT_OBSERVED nghĩa là đã kiểm tra đúng phạm vi báo cáo nhưng không có bảng phân tích cho vay theo loại hình; đây không phải lỗi. Các PDF có thể vẫn có tổng cho vay, phân tích chất lượng nợ, thời hạn, ngành hoặc loại hình doanh nghiệp, nhưng các bảng đó thuộc family khác.

- **KLB:** `BCTC Hợp nhất Kiểm toán năm 2025.pdf`; `VI_BaoCaoTaiChinh_KiemToan_BanNien_2025_HN.pdf`.
- **SHB:** `20260130 - SHB - Bao cao tai chinh Q4.2025 Rieng le.pdf`; `BCTC Công ty mẹ quý 1 năm 2025.pdf`; `BCTC Công ty mẹ quý 2 năm 2025.pdf`; `BCTC Hợp nhất quý 1 năm 2025.pdf`; `BCTC Hợp nhất quý 2 năm 2025.pdf`; `BCTC Hợp nhất quý 4 năm 2025.pdf`; `BCTC Công ty mẹ quý 1 năm 2026.pdf`; `BCTC Công ty mẹ quý 2 năm 2026.pdf`; `BCTC Hợp nhất quý 1 năm 2026.pdf`; `BCTC Hợp nhất quý 2 năm 2026.pdf`.

## Truy vết kỹ thuật

- Baseline: `/dev/shm/bctc-ai-27-bank-family-live-v1/family-06-loan-type-classification.json`
- Kết quả audit cuối: `/dev/shm/family06-audit-rerun-v4.json`
- Database replay: `/dev/shm/family06-audit-rerun-v4.sqlite3`
- Kết quả regression 8 ngân hàng cũ: `/dev/shm/family06-old8-current-regression-v1.json`
- Tập PDF bất biến: `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`

