# Family 4 — Chứng khoán kinh doanh

Checkpoint audit trên tập bất biến 204 PDF của 19 ngân hàng, chỉ gồm báo cáo từ năm 2025 đến hiện tại. Đây là bằng chứng staging; chưa thay thế hai bảng tổng hợp cuối dự án.

| Trạng thái | Baseline | Sau audit | Chênh lệch |
|---|---:|---:|---:|
| READY | 61 | 80 | +19 |
| NOT_OBSERVED | 94 | 92 | -2 |
| UNRESOLVED theo trạng thái tài liệu | 49 | 32 | -17 |

Trong 32 PDF mang trạng thái kỹ thuật `UNRESOLVED`, có 26 PDF thực sự còn vướng Family 4 và 6 PDF chỉ chứa bảng của **chứng khoán đầu tư** bị shortlist do dùng cùng tên dòng. Sáu PDF sau được tách riêng thành `SOURCE_ONLY / NGHI THUỘC FAMILY KHÁC`, không được diễn giải là thiếu schema Family 4.

- 61/61 PDF READY cũ vẫn READY; không có READY regression.
- Hai PDF TPB từng bị ghi sai là NOT_OBSERVED đã được sửa thành READY: `BCTC Hợp nhất quý 2 năm 2025.pdf` và `BCTC Hợp nhất quý 3 năm 2025.pdf`.
- 92 PDF NOT_OBSERVED còn lại đã được rà lại theo đúng phạm vi; không thấy bảng chi tiết Family 4. Dòng bảng cân đối, chính sách kế toán, lãi/lỗ mua bán chứng khoán và bảng rủi ro thị trường không được coi là bảng Family 4.
- Kết quả cuối có 615 mapping, không trùng ReportNormId trong cùng PDF và đúng thứ tự schema.
- 57 test engine/Family 4 passed. Hai replay lịch sử 8 ngân hàng giữ nguyên toàn bộ trials và metrics; chỉ metadata tham chiếu schema/result thay đổi do schema toàn cục đã tăng revision.

## Cấu trúc schema đã nhận diện

| Cách trình bày trên PDF | ReportNormId được dùng | Ghi chú |
|---|---|---|
| Giá trị thuần chứng khoán kinh doanh | 592 | Root có số, được map khi cấu trúc khép kín. |
| Phân theo tổ chức phát hành | 594–610 | 594/600/606 là tổng lần lượt của chứng khoán nợ/vốn/khác; các ID con giữ nguyên thứ tự schema. |
| Tổng trước dự phòng; dự phòng | 611; 612–615 | 612 là tổng dự phòng giảm giá/rủi ro; 613–615 là giảm giá, chung, cụ thể khi PDF tách riêng. |
| Phân theo tình trạng niêm yết | 617–625 | 617/620/623 là tổng nợ/vốn/khác; 618–619, 621–622, 624–625 là đã/chưa niêm yết. |

ReportNormId 593 và 616 là các **nút tiêu đề/cách trình bày**, không phải dòng số bắt buộc. Hệ thống không tự tạo giá trị cho hai ID này. Riêng 612 hiện đã được map trong 41 PDF READY. Các ID 617–625 đã xuất hiện trong kết quả như sau:

| ReportNormId | Ý nghĩa ngắn | Số PDF READY có mapping |
|---:|---|---:|
| 617 | Tổng chứng khoán nợ theo niêm yết | 22 |
| 618 | Chứng khoán nợ đã niêm yết | 20 |
| 619 | Chứng khoán nợ chưa niêm yết | 22 |
| 620 | Tổng chứng khoán vốn theo niêm yết | 13 |
| 621 | Chứng khoán vốn đã niêm yết | 13 |
| 622 | Chứng khoán vốn chưa niêm yết | 2 |
| 623 | Tổng chứng khoán khác theo niêm yết | 8 |
| 624 | Chứng khoán khác đã niêm yết | 3 |
| 625 | Chứng khoán khác chưa niêm yết | 5 |

## 26 PDF thực sự còn UNRESOLVED

Các trường hợp này đều đã rà schema. Không trường hợp nào dưới đây được kết luận là `CHƯA CÓ TRONG SCHEMA`.

| # | Ngân hàng | File PDF | Kỳ / loại báo cáo | Trang | Khoản mục nhìn thấy | Schema gần nhất | Kết luận dễ đọc |
|---:|---|---|---|---:|---|---|---|
| 1 | OCB | `BCTC Công ty mẹ quý 2 năm 2025.pdf` | Q2/2025, công ty mẹ | 21 | Chứng khoán nợ; chứng khoán Chính phủ; tổng; bảng đã niêm yết | 592, 594, 595, 617, 618 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — có hai cột ngày và số tiền nguyên VND nhưng bảng không ghi đơn vị; không tự suy đơn vị từ độ lớn số. |
| 2 | OCB | `BCTC Hợp nhất quý 2 năm 2025.pdf` | Q2/2025, hợp nhất | 21 | Cùng cấu trúc chứng khoán nợ/Chính phủ/niêm yết | 592, 594, 595, 617, 618 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — `unit_exact` không có; một số ô kỳ trước là blank thay vì dấu gạch rõ ràng. |
| 3 | OCB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất | 23 | Chứng khoán nợ; Chính phủ; đã niêm yết; tổng | 592, 594, 595, 617, 618 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — không có đơn vị nguồn trong bảng. |
| 4 | OCB | `BCTC Công ty mẹ quý 1 năm 2026.pdf` | Q1/2026, công ty mẹ | 22 | Chứng khoán nợ; Chính phủ; đã niêm yết; tổng | 592, 594, 595, 617, 618 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — bảng có ngày 31/03/2026 và 31/12/2025 nhưng không ghi đơn vị. |
| 5 | OCB | `BCTC Hợp nhất quý 1 năm 2026.pdf` | Q1/2026, hợp nhất | 22 | Cùng cấu trúc chứng khoán nợ/Chính phủ/niêm yết | 592, 594, 595, 617, 618 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — thiếu đơn vị nguồn; không dùng tên ngân hàng để đoán. |
| 6 | OCB | `BCTC Hợp nhất quý 2 năm 2026.pdf` | Q2/2026, hợp nhất | 23 | Cùng cấu trúc chứng khoán nợ/Chính phủ/niêm yết | 592, 594, 595, 617, 618 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — thiếu đơn vị nguồn. |
| 7 | SHB | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | Q2/2026, công ty mẹ | 22 | Các dòng chứng khoán kinh doanh và dự phòng | 592, 594–615 | **LỖI SOURCE/OCR** — các ô tiền bị trả về chuỗi ký tự hỏng như `-发出-`, không phải số hay dấu gạch xác thực. |
| 8 | SSB | `BCTC Công ty mẹ quý 4 năm 2025.pdf` | Q4/2025, công ty mẹ | 33 | “Đã niêm yết”, “Chưa niêm yết”, tổng | 618–619 hoặc 621–622 hoặc 624–625 | **KHÔNG XÁC ĐỊNH ĐƯỢC QUAN HỆ CHA/CON** — PDF/JSON không cho biết hai dòng thuộc chứng khoán nợ, vốn hay khác; không ép vào một nhánh. |
| 9 | STB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | Q1/2025, hợp nhất | 31 | “Chứng khoán Chính phủ” và “Chứng khoán NHNN” là hai dòng riêng | 595 | **CÓ ID GẦN NGHĨA NHƯNG KHÁC CÁCH BIỂU DIỄN** — schema 595 gộp Chính phủ và NHNN; cần phép cộng có bằng chứng thay vì map hai dòng độc lập vào cùng ID. |
| 10 | STB | `BCTC Hợp nhất quý 2 năm 2025.pdf` | Q2/2025, hợp nhất | 31 | Cùng hai dòng Chính phủ/NHNN | 595 | **CÓ ID GẦN NGHĨA NHƯNG KHÁC CÁCH BIỂU DIỄN** — chờ aggregation generic. |
| 11 | STB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | Q3/2025, hợp nhất | 30 | Chính phủ; NHNN; các dòng chi tiết khác | 595 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** đồng thời cần aggregation Chính phủ + NHNN. |
| 12 | STB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất | 30 | Cùng hai dòng Chính phủ/NHNN | 595 | **CÓ ID GẦN NGHĨA NHƯNG KHÁC CÁCH BIỂU DIỄN** — không tạo ID mới, cần cộng đúng hai dòng vào 595. |
| 13 | VAB | `2_vab_2025_4_15_527ed46_vi_baocaotaichinh_q1_2025.pdf` | Q1/2025, hợp nhất | 29–30 | Nợ/vốn/khác và bảng đã/chưa niêm yết; cột “Cuối kỳ”, “Đầu kỳ” | 592–625 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — không có ngày và đơn vị ngay trên hai bảng; nhiều hierarchy path bị dính chữ. |
| 14 | VAB | `2_vab_2025_4_15_d453cb6_vn_baocaotaichinh_q1_2025.pdf` | Q1/2025, riêng lẻ | 28–29 | Cùng cấu trúc “Cuối kỳ/Đầu kỳ” | 592–625 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — không fabricate ngày cuối kỳ hay đơn vị. |
| 15 | VAB | `BCTC Công ty mẹ quý 3 năm 2025.pdf` | Q3/2025, công ty mẹ | 30 | Nợ/vốn/khác; các dòng viết tắt CK; cột tương đối | 592–625 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — ngày/đơn vị không nằm trong bảng. |
| 16 | VAB | `BCTC Công ty mẹ quý 4 năm 2025.pdf` | Q4/2025, công ty mẹ | 30–31 | Bảng tổ chức phát hành và bảng niêm yết | 592–625 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — chỉ có vai trò tương đối “Cuối kỳ/Đầu kỳ”. |
| 17 | VAB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | Q3/2025, hợp nhất | 31 | Bảng chứng khoán kinh doanh | 592–625 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — thiếu endpoint/đơn vị tại bảng. |
| 18 | VAB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất | 30–31 | Bảng tổ chức phát hành và niêm yết | 592–625 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — không suy ngày 31/12 chỉ từ chữ “Cuối kỳ”. |
| 19 | VAB | `BCTC RIENG LE QUY 2.2025-TV_0001-da nen.pdf` | Q2/2025, riêng lẻ | 28–29 | Nợ/vốn/khác và bảng niêm yết | 592–625 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — header tương đối, đơn vị vắng mặt. |
| 20 | VAB | `BCTC Công ty mẹ quý 2 năm 2026.pdf` | Q2/2026, công ty mẹ | 30–31 | Nợ/vốn/khác và bảng niêm yết, chủ yếu dấu gạch | 592–625 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — dấu gạch có thể là zero nhưng chưa đủ trục kỳ/đơn vị để materialize. |
| 21 | VAB | `BCTC Hợp nhất quý 2 năm 2026.pdf` | Q2/2026, hợp nhất | 31–32 | Cùng cấu trúc, chủ yếu dấu gạch | 592–625 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — giữ fail-closed. |
| 22 | VAB | `BCTC Q1.2026 RIENG LE_0001.pdf` | Q1/2026, riêng lẻ | 30–31 | Nợ/vốn/khác; bảng niêm yết; “Cuối kỳ/Đầu kỳ” | 592–625 | **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/ĐƠN VỊ** — header không đủ endpoint/đơn vị. |
| 23 | VBB | `3_vbb_2025_8_6_8bb1ede_vi_baocaotaichinh_riengle_bannien_2025.pdf` | 6T/2025, riêng lẻ | 38 | “Trái phiếu Chính phủ” → “Niêm yết” | 595 và 617–618 | **KHÔNG XÁC ĐỊNH ĐƯỢC QUAN HỆ CHA/CON** — trục niêm yết được đặt dưới một khoản mục tổ chức phát hành, không dưới nhóm nợ; không trộn hai cách phân loại. |
| 24 | VBB | `3_vbb_2025_8_6_d00b2c1_vi_baocaotaichinh_hopnhat_bannien_2025.pdf` | 6T/2025, hợp nhất | 38 | Cùng cấu trúc Trái phiếu Chính phủ/Niêm yết | 595 và 617–618 | **KHÔNG XÁC ĐỊNH ĐƯỢC QUAN HỆ CHA/CON** — cần quy tắc generic cho hai trục lồng nhau. |
| 25 | VBB | `3_vbb_2026_2_2_a18dc42_vi_baocaotaichinh_riengle_q4_2025.pdf` | Q4/2025, riêng lẻ | 24 | Trái phiếu Chính phủ; niêm yết; tổng | 595 và 617–618 | **KHÔNG XÁC ĐỊNH ĐƯỢC QUAN HỆ CHA/CON** — không đồng nhất “Trái phiếu Chính phủ” với toàn bộ nhóm chứng khoán nợ. |
| 26 | VBB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất | 24 | Trái phiếu Chính phủ; niêm yết; tổng | 595 và 617–618 | **KHÔNG XÁC ĐỊNH ĐƯỢC QUAN HỆ CHA/CON** — cùng nguyên nhân; schema đã có nhưng quan hệ nguồn chưa đủ rõ. |

## Sáu PDF trạng thái kỹ thuật UNRESOLVED nhưng thực chất SOURCE_ONLY của family khác

| # | Ngân hàng | File PDF | Trang | Nội dung nhìn thấy | Kết luận |
|---:|---|---|---:|---|---|
| 1 | BVB | `VI_BaoCaoTaiChinhRiengLe_Kiemtoan_2025.pdf` | 42–43 | Chứng khoán nợ theo đã/chưa niêm yết | **NGHI LÀ THUỘC FAMILY KHÁC** — trang 43 ghi rõ “Chứng khoán đầu tư giữ đến ngày đáo hạn (tiếp theo)”; trang 42 là phần tiếp diễn của nhánh chứng khoán đầu tư. |
| 2 | NAB | `BCTC Công ty mẹ quý 3 năm 2025.pdf` | 28 | Nợ/vốn theo tổ chức phát hành, dự phòng sẵn sàng để bán | **NGHI LÀ THUỘC FAMILY KHÁC** — dòng cha/dự phòng xác nhận chứng khoán đầu tư sẵn sàng để bán. |
| 3 | NAB | `BCTC Công ty mẹ quý 4 năm 2025.pdf` | 28 | Cùng cấu trúc chứng khoán sẵn sàng để bán | **NGHI LÀ THUỘC FAMILY KHÁC** — không phải chứng khoán kinh doanh. |
| 4 | NAB | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | 44–45 | Mục 11 Chứng khoán đầu tư; sẵn sàng để bán/giữ đến đáo hạn | **NGHI LÀ THUỘC FAMILY KHÁC** — owner hiển thị trực tiếp là chứng khoán đầu tư. |
| 5 | NVB | `BCTC Công ty mẹ quý 1 năm 2025.pdf` | 31 | Chứng khoán đầu tư sẵn sàng để bán, giữ đến đáo hạn và dự phòng | **NGHI LÀ THUỘC FAMILY KHÁC** — không map sang Family 4 dù tên các dòng con giống nhau. |
| 6 | STB | `BCTC Công ty mẹ Kiểm toán năm 2025.pdf` | 46 | Mục 10 “Chứng khoán đầu tư” | **NGHI LÀ THUỘC FAMILY KHÁC** — giữ làm SOURCE_ONLY cho Family 16. |

## SOURCE_ONLY còn nằm trong 10 PDF READY

Các PDF dưới đây vẫn READY vì đã có ít nhất một bảng Family 4 được map chắc chắn. Tuy nhiên, một cách trình bày song song trong cùng PDF còn chưa map; vì vậy phải ghi rõ thay vì che dưới trạng thái READY.

| # | Ngân hàng | File PDF | Trang | Dòng/bảng chưa map | Schema gần nhất | Vì sao giữ SOURCE_ONLY |
|---:|---|---|---:|---|---|---|
| 1 | ABB | `1_abb_2025_9_9_0dee6d3_bctc_hn_ktsx_30_06_2025_tv.pdf` | 41 | Chứng khoán nợ: đã niêm yết 51.963/80.846; chưa niêm yết 66.740/37.426; tổng 118.703/118.272 | 617–619 | Bảng là trang tiếp theo, JSON không giữ owner Family 4; cần adjacent-page coalescing, không đoán từ tên dòng đơn lẻ. |
| 2 | SSB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | 33 | “Đã niêm yết” 7.726.185/4.745.046; “Chưa niêm yết” 3.731.450/4.123.920 | 618–619 hoặc 621–622 hoặc 624–625 | Tiêu đề là phân tích niêm yết nhưng không có nhóm cha nợ/vốn/khác; **NHIỀU ID CÓ THỂ PHÙ HỢP**. |
| 3 | TCB | `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` | 40 | Bảng theo tổ chức phát hành: Chính phủ/chính quyền địa phương; TCTD khác | 594–596 | Bảng niêm yết cùng trang đã map 617–619; bảng tổ chức phát hành chưa tạo được một frontier duy nhất. Đây là gap biểu diễn, không phải thiếu schema. |
| 4 | TCB | `BCTC Công ty mẹ quý 3 năm 2025.pdf` | 35 | Chứng khoán nợ: đã/chưa niêm yết và tổng | 617–619 | Bảng issuer cùng trang đã READY; bảng niêm yết mất owner trong JSON nên không ghép tự động. |
| 5 | TCB | `BCTC Hợp nhất quý 2 năm 2025.pdf` | 40 | Nợ đã/chưa niêm yết; vốn đã niêm yết; tổng | 617–622 | Bảng issuer trang 39 đã map; bảng trang 40 không giữ owner Family 4 và unit chỉ có ở bảng trước. |
| 6 | TCB | `BCTC Công ty mẹ quý 1 năm 2026.pdf` | 33 | Chứng khoán nợ chưa niêm yết 406.749/4.778.366; tổng | 617, 619 | Bảng issuer cùng trang đã READY; phần niêm yết bị tách thành bảng không có owner. |
| 7 | TPB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | 37 | Bảng issuer gồm nợ, vốn, khác và dự phòng chung/cụ thể/giảm giá | 594–615 | Bảng niêm yết cùng trang đã map 617–624; bảng issuer có nhiều subtotal và dự phòng song song nên solver chưa tạo được frontier duy nhất. Schema đã có đầy đủ. |
| 8 | TPB | `BCTC Hợp nhất quý 1 năm 2026.pdf` | 38 | Cùng bảng issuer; dự phòng giảm giá/chung/cụ thể; tổng | 594–615 | Bảng niêm yết đã map; bảng issuer còn xung đột frontier. Không ghi “chưa có schema”. |
| 9 | VBB | `000000014895177_VI_BaoCaoTaiChinh_RiengLe_Q1_2025.pdf` | 16 | Nợ niêm yết/chưa niêm yết; “Số cuối quý/Số đầu năm” | 617–619 | Bảng issuer cùng trang đã READY; bảng niêm yết không ghi đơn vị và chỉ dùng header tương đối. |
| 10 | VBB | `1_vbb_2025_8_1_de20fa4_vi_baocaotaichinh_riengle_q2_2025.pdf` | 15 | Nợ niêm yết/chưa niêm yết; tổng | 617–619 | JSON mất cả owner và đơn vị ở bảng song song; giữ SOURCE_ONLY để không biến READY thành kết quả “đã map hết”. |

## 92 PDF NOT_OBSERVED

NOT_OBSERVED nghĩa là sau khi kiểm tra đúng phạm vi báo cáo không có bảng chi tiết Family 4; đây không phải lỗi. Phân bố theo ngân hàng: ABB 1, BVB 7, KLB 11, MSB 13, NAB 8, NVB 7, OCB 4, PGB 7, SGB 12, SHB 1, STB 8, TPB 5, VAB 3 và VBB 5.

<details>
<summary>Danh sách đầy đủ 92 file NOT_OBSERVED</summary>

- **ABB:** `3_abb_2025_9_9_5fa7e09_bctc_rl_ktsx_30_06_2025_tv.pdf`.
- **BVB:** `BCTC Công ty mẹ quý 4 năm 2025.pdf`; `BCTC Hợp nhất quý 1 năm 2025.pdf`; `BCTC Hợp nhất quý 4 năm 2025.pdf`; `VI_BaoCaoTaiChinhHopNhat_Kiemtoan_2025.pdf`; `VI_BaoCaoTaiChinhRiengLe_Q2_2025.pdf`; `VI_BaoCaoTaiChinhRiengLe_Q3_2025.pdf`; `BCTC Hợp nhất quý 2 năm 2026.pdf`.
- **KLB:** `BAO CAO TAI CHINH QUY 3.2025 HOP NHAT.pdf`; `BAO CAO TAI CHINH QUY 3.2025 RIENG.pdf`; `BCTC Công ty mẹ quý 2 năm 2025.pdf`; `BCTC Hợp nhất Kiểm toán năm 2025.pdf`; `BCTC Hợp nhất quý 2 năm 2025.pdf`; `VI_BaoCaoTaiChinh_KiemToan_BanNien_2025_HN.pdf`; `bao-cao-tai-chinh-giua-nien-do-q4.2025-hop-nhat-_tv.pdf`; `bao-cao-tai-chinh-giua-nien-do-q4.2025-rieng_tv.pdf`; `BCTC Công ty mẹ quý 1 năm 2026.pdf`; `BCTC Công ty mẹ quý 2 năm 2026.pdf`; `BCTC Hợp nhất quý 1 năm 2026.pdf`.
- **MSB:** `BCTC Công ty mẹ Kiểm toán năm 2025.pdf`; `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf`; `BCTC Công ty mẹ quý 1 năm 2025.pdf`; `BCTC Công ty mẹ quý 2 năm 2025.pdf`; `BCTC Công ty mẹ quý 3 năm 2025.pdf`; `BCTC Công ty mẹ quý 4 năm 2025.pdf`; `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf`; `BCTC Hợp nhất quý 1 năm 2025.pdf`; `BCTC Hợp nhất quý 2 năm 2025.pdf`; `BCTC Hợp nhất quý 3 năm 2025.pdf`; `MSB 20260130 - MSB - Bao cao tai chinh Hop nhat Quy 4 2025.pdf`; `BCTC Công ty mẹ quý 1 năm 2026.pdf`; `BCTC Công ty mẹ quý 2 năm 2026.pdf`.
- **NAB:** `BCTC Hợp nhất quý 3 năm 2025.pdf`; `NAB NAMABANK_2025_Q2_BCTC HN.pdf`; `NAB NAMABANK_2025_Q2_BCTC RL.pdf`; `NAB namabank_2025_q4_bctc-hn.pdf`; `BCTC Công ty mẹ quý 1 năm 2026.pdf`; `BCTC Công ty mẹ quý 2 năm 2026.pdf`; `BCTC Hợp nhất quý 1 năm 2026.pdf`; `BCTC Hợp nhất quý 2 năm 2026.pdf`.
- **NVB:** `6_nvb_2026_2_3_925648e_vi_baocaotaichinh_q1_2025_riengle_signed.pdf`; `BCTC Công ty mẹ Kiểm toán năm 2025.pdf`; `BCTC Hợp nhất Kiểm toán năm 2025.pdf`; `BCTC Hợp nhất quý 1 năm 2025.pdf`; `VI_BaoCaoTaiChinh_BanNien_2025_HopNhat.pdf`; `2_nvb_2026_7_30_2bf1dd5_bctc__rieng_le__tieng_viet__q2_2026_signed.pdf`; `BCTC - HOP NHAT - TIENG VIET - Q1.2026.pdf`.
- **OCB:** `BCTC Công ty mẹ quý 1 năm 2025.pdf`; `BCTC Công ty mẹ quý 3 năm 2025.pdf`; `BCTC Hợp nhất quý 1 năm 2025.pdf`; `BCTC Hợp nhất quý 3 năm 2025.pdf`.
- **PGB:** `3_pgb_2025_10_22_8eac562_vi_baocaotaichinh_q3_2025.pdf`; `4_pgb_2026_1_22_d793078_vi_baocaotaichinh_q4_2025.pdf`; `BCTC Kiểm toán năm 2025.pdf`; `BCTC Soát xét 6 tháng đầu năm 2025.pdf`; `BCTC quý 1 năm 2025.pdf`; `1_pgb_2026_4_28_15bbc70_vi_baocaotaichinh_q1_2026.pdf`; `2_pgb_2026_7_22_3a0f521_vi_baocaotaichinh_q2_2026.pdf`.
- **SGB:** `BAO-CAO-TAI-CHINH-HOP-NHAT-QUY-3---20205.pdf`; `BAO-CAO-TAI-CHINH-RIENG-LE-QUY-3---2025.pdf`; `BAO-CAO-TAI-CHINH-RIENG-LE-QUY-4---2025.pdf`; `BCTC Hợp nhất quý 1 năm 2025.pdf`; `BCTC-hop-nhat-da-duoc-kiem-toan-2025.pdf`; `BCTC-rieng-le-da-duoc-kiem-toan-2025.pdf`; `BCTCBNHN.pdf`; `BCTCBNRL.pdf`; `5_sgb_2026_7_27_989deeb_vi__bao_cao_tai_chinh_hop_nhat_q22026_daky.pdf`; `7_sgb_2026_7_27_a0f7e4f_vi__bao_cao_tai_chinh_q22026_daky.pdf`; `BCTC-HN-quy-1---2026_VIE_0001.pdf`; `BCTC-Rieng-le-quy-1---2026_VIE.pdf`.
- **SHB:** `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf`.
- **STB:** `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf`; `BCTC Công ty mẹ quý 1 năm 2025.pdf`; `BCTC Công ty mẹ quý 2 năm 2025.pdf`; `BCTC Công ty mẹ quý 4 năm 2025.pdf`; `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf`; `BCTC Công ty mẹ quý 1 năm 2026.pdf`; `BCTC Hợp nhất quý 1 năm 2026.pdf`; `BCTC Hợp nhất quý 2 năm 2026.pdf`.
- **TPB:** `BCTC Công ty mẹ Kiểm toán năm 2025.pdf`; `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf`; `BCTC Công ty mẹ quý 2 năm 2025.pdf`; `BCTC Công ty mẹ quý 3 năm 2025.pdf`; `BCTC Công ty mẹ quý 1 năm 2026.pdf`.
- **VAB:** `20250815 - VAB - BCTC HN BAN NIEN 2025_0001.pdf`; `BCTC Công ty mẹ Kiểm toán năm 2025.pdf`; `BCTC Hợp nhất Kiểm toán năm 2025.pdf`.
- **VBB:** `2_vbb_2026_3_23_b2c1e44_vi_baocaotaichinh_kiemtoan_riengle_2025.pdf`; `3_vbb_2026_3_23_3110a7d_vi_baocaotaichinh_kiemtoan_hopnhat_2025.pdf`; `3_vbb_2026_5_2_fa0b162_vi_baocaotaichinh_riengle_q1_2026.pdf`; `BCTC Công ty mẹ quý 2 năm 2026.pdf`; `BCTC Hợp nhất quý 2 năm 2026.pdf`.

</details>

## Truy vết kỹ thuật

- Baseline: `/dev/shm/bctc-ai-27-bank-family-live-v1/family-04-trading-securities.json`
- Kết quả audit cuối: `/dev/shm/family04-audit-rerun-v6.json`
- Database replay: `/dev/shm/family04-audit-rerun-v6.sqlite3`
- Tập PDF bất biến: `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`

