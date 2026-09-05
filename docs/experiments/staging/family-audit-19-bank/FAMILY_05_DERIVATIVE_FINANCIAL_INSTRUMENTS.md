# Family 5 — Công cụ tài chính phái sinh

Checkpoint audit trên tập bất biến 204 PDF của 19 ngân hàng mới, chỉ gồm báo cáo từ năm 2025 đến hiện tại. Đây là bằng chứng staging; chưa thay thế hai bảng tổng hợp cuối dự án.

| Trạng thái | Baseline | Sau audit | Chênh lệch |
|---|---:|---:|---:|
| READY | 74 | 128 | +54 |
| NOT_OBSERVED | 25 | 25 | 0 |
| UNRESOLVED | 105 | 51 | -54 |

- Kết quả cuối có 1.905 mapping.
- 74/74 PDF READY cũ vẫn READY. Một PDF SHB được bổ sung ba mapping cha/tổng có cùng số liệu nguồn; không mất hoặc đổi mapping cũ.
- 25/25 PDF NOT_OBSERVED giữ nguyên; không biến trường hợp không thấy family thành lỗi.
- 52 test engine/runner passed; Ruff, kiểm tra format và `git diff --check` đều sạch.

## Cấu trúc đã nhận diện

Hệ thống nhận diện hai khối kỳ hiện tại/kỳ so sánh; các hàng giao dịch kỳ hạn tiền tệ, hoán đổi tiền tệ, hợp đồng tương lai tiền tệ, hoán đổi lãi suất và nhóm phái sinh khác; cùng các cột giá trị hợp đồng, tài sản và công nợ. Dòng tổng được đối chiếu bằng phương trình trực tiếp. Dòng “giá trị thuần” chỉ dùng để kiểm tra `tài sản ± công nợ`, không tự tạo thêm khoản mục schema.

Các biến thể đã xử lý gồm tiêu đề ngày đầy đủ hoặc “cuối kỳ/đầu kỳ”, số thứ tự ở cột riêng, tổng đặt cuối bảng, số âm đặt ở phía tài sản/công nợ, và hai kỳ trình bày thành hai cụm hàng liên tiếp.

## 51 PDF còn UNRESOLVED

### Lỗi nguồn hoặc JSON — 10 PDF

| # | Ngân hàng | File PDF | Kỳ / loại báo cáo | Kiểm toán | Trang | Nội dung nhìn thấy | Schema gần nhất | Kết luận |
|---:|---|---|---|---|---:|---|---|---|
| 1 | EIB | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | Năm 2025, hợp nhất | Kiểm toán | 40 | Bảng phái sinh có tài sản, công nợ, giá trị thuần và tổng | 631; các nhánh 633–714 | **LỖI SOURCE/OCR** — số âm/tài sản/công nợ bị dịch hàng trong JSON nên tổng nhìn thấy không khép kín; không sửa số bằng suy đoán. |
| 2 | EIB | `BCTC Công ty mẹ quý 1 năm 2026.pdf` | Q1/2026, công ty mẹ | Chưa nêu | 22 | Các hàng phái sinh có số nhưng một số ô chứa chuỗi rác `畅-` | 631; các nhánh 633–714 | **LỖI SOURCE/OCR** — chuỗi tiền không thể xác thực là số hay dấu gạch. |
| 3 | PGB | `BCTC quý 1 năm 2025.pdf` | Q1/2025, báo cáo ngân hàng | Chưa nêu | 25 | Bảng phái sinh và dòng tổng | 631; các nhánh 633–714 | **LỖI SOURCE/OCR** — giá trị `2.263.649'` có dấu nháy thừa; chưa có bằng chứng pixel để tự bỏ ký tự. |
| 4 | SGB | `BAO-CAO-TAI-CHINH-HOP-NHAT-QUY-3---20205.pdf` | Q3/2025, hợp nhất | Chưa nêu | 24 | Nhóm phái sinh tiền tệ, hai kỳ | 631; 633–714 | **LỖI SOURCE/OCR** — nhiều ô tiền bị ghi thành chuỗi gạch/ký tự không hợp lệ và một kỳ chưa xác thực được. |
| 5 | SGB | `BAO-CAO-TAI-CHINH-RIENG-LE-QUY-3---2025.pdf` | Q3/2025, riêng lẻ | Chưa nêu | 23 | Nhóm phái sinh tiền tệ, kỳ so sánh | 631; 647–714 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — JSON tạo hai lần cùng vai trò nhóm tiền tệ ở kỳ so sánh. |
| 6 | SGB | `BAO-CAO-TAI-CHINH-RIENG-LE-QUY-4---2025.pdf` | Q4/2025, riêng lẻ | Chưa nêu | 23 | Bảng phái sinh hai kỳ | 631; 633–714 | **LỖI SOURCE/OCR** — ô tiền không hợp lệ và tiêu đề kỳ không đủ chắc chắn. |
| 7 | SGB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | Q1/2025, hợp nhất | Chưa nêu | 21 | Nhóm phái sinh tiền tệ | 631; 647–714 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — cùng vai trò nhóm xuất hiện lặp ở kỳ so sánh; chưa thể chọn một hàng. |
| 8 | SGB | `BCTC-rieng-le-da-duoc-kiem-toan-2025.pdf` | Năm 2025, riêng lẻ | Kiểm toán | 27 | Bảng phái sinh hai kỳ | 631; 633–714 | **LỖI SOURCE/OCR** — chuỗi tiền không hợp lệ và cả hai kỳ chưa được gắn chắc chắn. |
| 9 | SGB | `BCTCBNHN.pdf` | Năm 2025, hợp nhất | Chưa nêu trong tên file | 27 | Nhóm phái sinh tiền tệ | 631; 647–714 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — hàng nhóm kỳ so sánh bị lặp. |
| 10 | SGB | `BCTCBNRL.pdf` | Năm 2025, riêng lẻ | Chưa nêu trong tên file | 27 | Nhóm phái sinh tiền tệ | 631; 647–714 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — hàng nhóm kỳ so sánh bị lặp. |

### Bảng trải qua hai trang hoặc chỉ lấy được một kỳ — 14 PDF

Schema đã có các ID cần thiết; đây là khoảng trống ghép cấu trúc/trang, không phải thiếu schema.

| # | Ngân hàng | File PDF | Kỳ / loại báo cáo | Trang | Nội dung nhìn thấy | Kết luận |
|---:|---|---|---|---:|---|---|
| 1 | LPB | `BCTC 31.12.2025 VN color.pdf` | Năm 2025, báo cáo ngân hàng | 37–38 | Kỳ hiện tại và kỳ so sánh nằm trên hai trang kế tiếp | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — mỗi trang riêng chỉ có một kỳ; cần ghép hai trang với receipt nguồn. |
| 2 | LPB | `BCTC Q3.2025 VN.pdf` | Q3/2025, báo cáo ngân hàng | 36–37 | Hai khối kỳ nằm trên hai trang | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — PDF đầy đủ nhưng evaluator hiện nhóm candidate theo từng trang. |
| 3 | LPB | `BCTC quý 1 năm 2025.pdf` | Q1/2025, báo cáo ngân hàng | 35–36 | Hai khối kỳ nằm trên hai trang | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — cần bằng chứng ghép trang liền kề; không tự gán kỳ. |
| 4 | LPB | `BCTC quý 2 năm 2026.pdf` | Q2/2026, báo cáo ngân hàng | 36–37 | Hai khối kỳ nằm trên hai trang | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — PDF không thiếu; thuật toán chưa ghép hai candidate trang. |
| 5 | VAB | `2_vab_2025_4_15_527ed46_vi_baocaotaichinh_q1_2025.pdf` | Q1/2025, hợp nhất | Vùng liên quan chưa được chọn | Có tín hiệu tiêu đề nhưng chưa tạo được bảng family đầy đủ | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — chỉ có biên anchor một phần; cần lấy lại vùng/trang liên quan. |
| 6 | VAB | `2_vab_2025_4_15_d453cb6_vn_baocaotaichinh_q1_2025.pdf` | Q1/2025, riêng lẻ | 34 | Chỉ một khối kỳ trong candidate | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — kỳ còn lại có khả năng ở trang tiếp nối; chưa ghép nguồn. |
| 7 | VAB | `BCTC Công ty mẹ quý 3 năm 2025.pdf` | Q3/2025, công ty mẹ | 35 | Chỉ một kỳ | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — thiếu carrier kỳ so sánh trong candidate hiện tại. |
| 8 | VAB | `BCTC Công ty mẹ quý 4 năm 2025.pdf` | Q4/2025, công ty mẹ | 35 | Chỉ một kỳ | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — chưa ghép khối tiếp nối. |
| 9 | VAB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | Q3/2025, hợp nhất | 36 | Chỉ một kỳ | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — chưa có bằng chứng kỳ thứ hai trong cùng closure. |
| 10 | VAB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất | 36 | Chỉ một kỳ | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — cần ghép trang/cụm tiếp nối. |
| 11 | VAB | `BCTC RIENG LE QUY 2.2025-TV_0001-da nen.pdf` | Q2/2025, riêng lẻ | 33 | Một khối bảng tiếp nối | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — candidate chưa có đủ hai kỳ. |
| 12 | VAB | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | Q2/2026, công ty mẹ | 36 | Chỉ một kỳ | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — cần truy vết khối kỳ so sánh. |
| 13 | VAB | `BCTC Hợp nhất quý 2 năm 2026.pdf` | Q2/2026, hợp nhất | 36 | Chỉ một kỳ | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — chưa ghép kỳ thứ hai. |
| 14 | VAB | `BCTC Q1.2026 RIENG LE_0001.pdf` | Q1/2026, riêng lẻ | 36 | Chỉ một kỳ | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — candidate hiện tại chưa đủ hai kỳ. |

### Tên giao dịch chưa đủ để chọn đúng ID — 27 PDF

Các PDF MSB/OCB dùng tên “Giao dịch hoán đổi” hoặc “Giao dịch kỳ hạn” mà không ghi rõ tiền tệ hay lãi suất. Schema tách bản chất này thành giao dịch tiền tệ (ví dụ 634/635 và các ID theo kỳ/cột) và hoán đổi lãi suất (644 cùng các ID theo kỳ/cột). Không ép alias chỉ dựa trên chữ “hoán đổi/kỳ hạn”. Ba PDF SSB ghi rõ “Giao dịch kỳ hạn lãi suất”, trong khi schema hiện chỉ có hoán đổi lãi suất, nên đây là khoản mục khác bản chất.

| # | Ngân hàng | File PDF | Kỳ / loại báo cáo | Trang | Khoản mục thực tế | Kết luận |
|---:|---|---|---|---:|---|---|
| 1 | MSB | `BCTC Công ty mẹ Kiểm toán năm 2025.pdf` | Năm 2025, công ty mẹ, kiểm toán | 33 | “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP** — thiếu dấu hiệu tiền tệ/lãi suất. |
| 2 | MSB | `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` | 6T/2025, công ty mẹ, soát xét | 34 | “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 3 | MSB | `BCTC Công ty mẹ quý 1 năm 2025.pdf` | Q1/2025, công ty mẹ | 29 | “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 4 | MSB | `BCTC Công ty mẹ quý 2 năm 2025.pdf` | Q2/2025, công ty mẹ | 29 | “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 5 | MSB | `BCTC Công ty mẹ quý 3 năm 2025.pdf` | Q3/2025, công ty mẹ | 29 | “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 6 | MSB | `BCTC Công ty mẹ quý 4 năm 2025.pdf` | Q4/2025, công ty mẹ | 29 | “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 7 | MSB | `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` | 6T/2025, hợp nhất, soát xét | 35 | “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 8 | MSB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | Q1/2025, hợp nhất | 31 | “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 9 | MSB | `BCTC Hợp nhất quý 2 năm 2025.pdf` | Q2/2025, hợp nhất | 31 | “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 10 | MSB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | Q3/2025, hợp nhất | 31 | “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 11 | MSB | `MSB 20260130 - MSB - Bao cao tai chinh Hop nhat Quy 4 2025.pdf` | Q4/2025, hợp nhất | 30 | “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 12 | MSB | `BCTC Công ty mẹ quý 1 năm 2026.pdf` | Q1/2026, công ty mẹ | 31 | “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 13 | MSB | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | Q2/2026, công ty mẹ | 27 | “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 14 | OCB | `BCTC Công ty mẹ quý 1 năm 2025.pdf` | Q1/2025, công ty mẹ | 21 | “Giao dịch kỳ hạn”; “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP** — tên nguồn không phân biệt tiền tệ/lãi suất. |
| 15 | OCB | `BCTC Công ty mẹ quý 2 năm 2025.pdf` | Q2/2025, công ty mẹ | 21 | “Giao dịch kỳ hạn”; “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 16 | OCB | `BCTC Công ty mẹ quý 3 năm 2025.pdf` | Q3/2025, công ty mẹ | 21 | Các hàng kỳ hạn/hoán đổi; nhóm số lỗi | **LỖI SOURCE/OCR** — ngoài tên chung, JSON còn gom ô tiền sai. |
| 17 | OCB | `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` | 6T/2025, hợp nhất, soát xét | 57–58 | Hai phần bảng trên hai trang | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — vừa thiếu định danh giao dịch, vừa cần ghép trang. |
| 18 | OCB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | Q1/2025, hợp nhất | 22 | “Giao dịch kỳ hạn”; “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 19 | OCB | `BCTC Hợp nhất quý 2 năm 2025.pdf` | Q2/2025, hợp nhất | 22 | “Giao dịch kỳ hạn”; “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 20 | OCB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | Q3/2025, hợp nhất | 22 | “Giao dịch kỳ hạn”; “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 21 | OCB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất | 23 | “Giao dịch kỳ hạn”; “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 22 | OCB | `BCTC Công ty mẹ quý 1 năm 2026.pdf` | Q1/2026, công ty mẹ | 23 | “Giao dịch kỳ hạn”; “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 23 | OCB | `BCTC Hợp nhất quý 1 năm 2026.pdf` | Q1/2026, hợp nhất | 23 | “Giao dịch kỳ hạn”; “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 24 | OCB | `BCTC Hợp nhất quý 2 năm 2026.pdf` | Q2/2026, hợp nhất | 23 | “Giao dịch kỳ hạn”; “Giao dịch hoán đổi” | **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 25 | SSB | `BCTC Công ty mẹ quý 2 năm 2025.pdf` | Q2/2025, công ty mẹ | 41 | “Giao dịch kỳ hạn lãi suất” | **CHƯA CÓ TRONG SCHEMA** — ID hoán đổi lãi suất không cùng bản chất với hợp đồng kỳ hạn lãi suất. Cần đánh giá có tạo ID mới hay không. |
| 26 | SSB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | Q1/2025, hợp nhất | 42 | “Giao dịch kỳ hạn lãi suất” | **CHƯA CÓ TRONG SCHEMA** — không ép vào hoán đổi lãi suất. |
| 27 | SSB | `BCTC Hợp nhất quý 2 năm 2025.pdf` | Q2/2025, hợp nhất | 43 | “Giao dịch kỳ hạn lãi suất” | **CHƯA CÓ TRONG SCHEMA** — khoản mục mới cần đánh giá schema. |

## Dòng nhìn thấy nhưng không map trong PDF READY

Đây là ba nhóm riêng; không tính chúng là UNRESOLVED của cả PDF.

### 1. Dòng giá trị thuần — 46 PDF READY

“Giá trị thuần” là kết quả trình bày từ tài sản và công nợ phái sinh. Hệ thống giữ dòng này làm phương trình kiểm tra, còn các giá trị hợp đồng/tài sản/công nợ đã map vào các ID 633–714. Vì vậy đây không phải khoản mục bị bỏ sót và không phải lý do tạo ID mới.

| Ngân hàng | Số PDF | File PDF và trang |
|---|---:|---|
| EIB | 2 | `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` p37; `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` p36 |
| NAB | 11 | `BCTC Công ty mẹ quý 3 năm 2025.pdf` p27; `BCTC Công ty mẹ quý 4 năm 2025.pdf` p27; `BCTC Hợp nhất Kiểm toán năm 2025.pdf` p39; `BCTC Hợp nhất quý 3 năm 2025.pdf` p26; `NAB NAMABANK_2025_Q2_BCTC HN.pdf` p26; `NAB NAMABANK_2025_Q2_BCTC RL.pdf` p27; `NAB namabank_2025_q4_bctc-hn.pdf` p26; bốn báo cáo Q1/Q2 năm 2026 công ty mẹ/hợp nhất p25 |
| NVB | 8 | `6_nvb_2026_2_3_925648e_vi_baocaotaichinh_q1_2025_riengle_signed.pdf` p31; `BCTC Công ty mẹ Kiểm toán năm 2025.pdf` p30; `BCTC Công ty mẹ quý 1 năm 2025.pdf` p37; `BCTC Hợp nhất Kiểm toán năm 2025.pdf` p30; `BCTC Hợp nhất quý 1 năm 2025.pdf` p37; `VI_BaoCaoTaiChinh_BanNien_2025_HopNhat.pdf` p39; Q2/2026 riêng lẻ p29; Q1/2026 hợp nhất p32 |
| SHB | 4 | Hai báo cáo công ty mẹ năm/6 tháng 2025 p31/p29; hai báo cáo hợp nhất năm/6 tháng 2025 p34/p31 |
| SSB | 10 | Công ty mẹ năm/Q3/Q4 2025 p47/p37/p43; hợp nhất năm/Q3/Q4 p48/p42/p44; hai nguồn chính thức soát xét 6T/2025 p43/p45; công ty mẹ Q1/Q2 2026 p42/p41 |
| TPB | 3 | `BCTC Công ty mẹ quý 2 năm 2025.pdf` p30; `BCTC Công ty mẹ quý 3 năm 2025.pdf` p30; `BCTC Công ty mẹ quý 1 năm 2026.pdf` p35 |
| VBB | 8 | Kiểm toán riêng lẻ 2025 p40; bán niên riêng/hợp nhất p38/p39; Q4 riêng lẻ p24; kiểm toán hợp nhất p40; Q1/2026 riêng lẻ p28; Q2/2026 công ty mẹ/hợp nhất p30/p31 |

### 2. Cột số thứ tự — 1 PDF READY

| Ngân hàng | File PDF | Trang | Nội dung | Kết luận |
|---|---|---:|---|---|
| BVB | `VI_BaoCaoTaiChinhRiengLe_Q3_2025.pdf` | 22 | Cột `STT` gồm 1, 2, 3… | **SOURCE_ONLY / CONTROL** — chỉ là số thứ tự trình bày, không phải số kế toán và không có ReportNormId. |

### 3. Dòng tổng chỉ in một phần cột — 2 PDF READY

| Ngân hàng | File PDF | Trang | Nội dung | Kết luận |
|---|---|---:|---|---|
| VAB | `BCTC Công ty mẹ Kiểm toán năm 2025.pdf` | 30 | Dòng tổng kỳ chỉ in ở một số cột | **SOURCE_ONLY / CONTROL** — dùng đối chiếu các cột nhìn thấy; mapping chi tiết và tổng đầy đủ được suy ra từ frontier trực tiếp đã khép kín. |
| VAB | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | 30 | Dòng tổng kỳ chỉ in ở một số cột | **SOURCE_ONLY / CONTROL** — không tạo ID mới cho một bản trình bày tổng bị khuyết cột. |

## 25 PDF NOT_OBSERVED

Đã kiểm tra đúng phạm vi nhưng không thấy bảng công cụ tài chính phái sinh đủ anchor. Đây không phải lỗi.

| Ngân hàng | Số PDF | File PDF |
|---|---:|---|
| BVB | 2 | `VI_BaoCaoTaiChinhHopNhat_Kiemtoan_2025.pdf`; `VI_BaoCaoTaiChinhRiengLe_Kiemtoan_2025.pdf` |
| KLB | 2 | `BCTC Hợp nhất Kiểm toán năm 2025.pdf`; `VI_BaoCaoTaiChinh_KiemToan_BanNien_2025_HN.pdf` |
| SGB | 4 | Hai báo cáo Q1/2026 riêng lẻ/hợp nhất; hai báo cáo Q2/2026 riêng lẻ/hợp nhất |
| TCB | 13 | Toàn bộ báo cáo trong tập hoàn chỉnh: công ty mẹ Q1–Q4/2025, hợp nhất năm và Q1–Q4/2025, cùng công ty mẹ/hợp nhất Q1–Q2/2026 |
| TPB | 3 | `BCTC Công ty mẹ Kiểm toán năm 2025.pdf`; `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf`; `BCTC Hợp nhất Kiểm toán năm 2025.pdf` |
| VBB | 1 | `BCTC Hợp nhất quý 4 năm 2025.pdf` |

## Truy vết kỹ thuật

- Baseline: `/dev/shm/bctc-ai-27-bank-family-live-v1/family-05-derivative-financial-instruments.json`
- Kết quả audit: `/dev/shm/family05-root-rerun-v6.json`
- Database replay: `/dev/shm/family05-root-results-v6.sqlite3`

