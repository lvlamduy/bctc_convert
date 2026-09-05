# Family 7 — Phân tích dư nợ cho vay theo ngành kinh tế

Checkpoint audit trên tập bất biến 204 PDF của 19 ngân hàng, chỉ gồm báo cáo từ năm 2025 đến hiện tại. Các PDF chưa có đủ JSON ở thời điểm đóng tập không bị đưa vào mẫu số và không thể bị kết luận nhầm là NOT_OBSERVED. Đây là bằng chứng staging; chưa thay thế hai bảng tổng hợp cuối dự án.

| Trạng thái | Baseline | Sau audit | Chênh lệch |
|---|---:|---:|---:|
| READY | 3 | 112 | +109 |
| NOT_OBSERVED | 89 | 89 | 0 |
| UNRESOLVED | 112 | 3 | -109 |

- Kết quả cuối có 1.946 mapping trên 112 PDF READY; không có ReportNormId trùng trong cùng PDF.
- 104/104 PDF READY ở checkpoint trước bước ghép trang vẫn giữ nguyên toàn bộ mapping; 89/89 PDF NOT_OBSERVED giữ nguyên.
- Tám PDF cuối cùng được chuyển từ UNRESOLVED sang READY bằng cách ghép đúng hai trang liền kề hoặc cắt đúng nhóm ngành trong bảng hỗn hợp. Mỗi phép ghép giữ nguyên trang, bảng, hàng và chỉ chấp nhận khi đơn vị, hai cột giá trị và dòng tổng khớp.
- Không nới sai số số học. Vì vậy ba PDF có bảng nguồn không khép kín vẫn UNRESOLVED.

## Cấu trúc schema đã nhận diện

ReportNormId 716 là owner “Cho vay khách hàng”; 727 là nhánh “Phân tích dư nợ cho vay theo ngành kinh tế”. Các cách viết khác nhau giữa ngân hàng chỉ được coi là alias khi bản chất giống nhau.

| Khoản mục schema | ReportNormId | Số PDF READY có mapping |
|---|---:|---:|
| Tổng dư nợ cho vay theo ngành kinh tế | 727 | 112 |
| Nông nghiệp, lâm nghiệp và thủy sản | 728 | 106 |
| Khai khoáng | 729 | 97 |
| Sản xuất và phân phối điện, khí đốt… | 730 | 90 |
| Cung cấp nước; quản lý, xử lý rác thải và nước thải | 731 | 74 |
| Xây dựng | 732 | 110 |
| Công nghiệp chế biến, chế tạo | 733 | 112 |
| Bán buôn, bán lẻ; sửa chữa xe có động cơ | 734 | 112 |
| Hoạt động kinh doanh bất động sản | 735 | 96 |
| Vận tải, kho bãi | 736 | 103 |
| Giáo dục và đào tạo | 737 | 77 |
| Dịch vụ lưu trú và ăn uống | 738 | 87 |
| Dịch vụ cá nhân và cộng đồng | 739 | 0 |
| Thông tin và truyền thông | 740 | 90 |
| Hoạt động tài chính, ngân hàng và bảo hiểm | 741 | 99 |
| Hoạt động chuyên môn, khoa học và công nghệ | 742 | 78 |
| Hoạt động hành chính và dịch vụ hỗ trợ | 743 | 81 |
| Hoạt động của các tổ chức và cơ quan quốc tế | 744 | 15 |
| Các ngành khác | 745 | 77 |
| Y tế và hoạt động trợ giúp xã hội | 5719 | 83 |
| Nghệ thuật, vui chơi và giải trí | 5720 | 75 |
| Hoạt động dịch vụ khác | 5721 | 78 |
| Hoạt động làm thuê/sản xuất tự tiêu dùng của hộ gia đình | 5722 | 80 |
| Cho vay cá nhân để mua nhà ở/quyền sử dụng đất để xây nhà | 6059 | 3 |
| Cho vay tại chi nhánh hoặc ngân hàng con nước ngoài | 6058 | 0 |
| Dịch vụ nói chung | 6060 | 0 |
| Thương mại, dịch vụ gộp | 6073 | 0 |
| Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán | 5749 | 11 |

Các biến thể đáng chú ý:

- KLB và SGB có bảng bị chia qua hai trang. Hệ thống chỉ ghép một trang liền kề khi trang sau tự nhận là phần tiếp theo và toàn bộ cấu trúc cột/đơn vị phù hợp.
- MSB trình bày chi tiết hơn schema: 13–14 dòng sản xuất được cộng đúng vào 733, năm dòng thương mại vào 734 và ba dòng vận tải vào 736. Các dòng nguồn vẫn được giữ để kiểm tra tổng.
- TCB, MSB, ABB và NVB tách “Cá nhân/Cho vay cá nhân” khỏi subtotal tổ chức kinh tế; dòng cá nhân chung không bị ép vào 6059 vì 6059 chỉ là cho vay cá nhân mua nhà.
- NVB có dòng gộp “Xây dựng và kinh doanh bất động sản”; không tự chia số vào 732 và 735.
- “Hoạt động của các tổ chức và cơ quan quốc tế” được map riêng vào 744, không còn bị gộp vào “Các ngành khác” 745.

## Ba PDF còn UNRESOLVED

Ba trường hợp này đều có schema phù hợp. Nguyên nhân là số liệu nhìn thấy ngay trên bảng nguồn không khép kín; không được backsolve từ báo cáo khác và không được tự tăng dung sai.

| # | Ngân hàng | File PDF | Kỳ / loại báo cáo | Trang PDF | Khoản mục nhìn thấy | Khoản mục cha | Schema gần nhất | Kết luận dễ đọc | Phân loại |
|---:|---|---|---|---:|---|---|---|---|---|
| 1 | KLB | `BCTC Công ty mẹ quý 1 năm 2026.pdf` | Q1/2026, công ty mẹ, chưa kiểm toán | 26–27 | Bảng “Phân tích dư nợ cho vay theo ngành kinh tế”; tổng các ngành kỳ hiện tại là 73.234.995 nhưng dòng tổng in 73.234.993 | Cho vay khách hàng | 727 và các child 728–745 | Hai trang ghép đúng, kỳ so sánh khớp; kỳ hiện tại lệch +2 theo đơn vị trình bày. Không sửa nguồn thành số khác. | **LỖI SOURCE / BẢNG NGUỒN KHÔNG KHÉP KÍN** |
| 2 | KLB | `BCTC Hợp nhất quý 1 năm 2026.pdf` | Q1/2026, hợp nhất, chưa kiểm toán | 26 | Cùng bảng; tổng các dòng kỳ hiện tại là 73.234.995 nhưng dòng tổng in 73.234.993 | Cho vay khách hàng | 727 và các child 728–745 | Bảng nằm trọn một trang và JSON khớp nội dung nhìn thấy; chênh +2 là bất nhất nguồn, không phải thiếu schema hay lỗi ghép trang. | **LỖI SOURCE / BẢNG NGUỒN KHÔNG KHÉP KÍN** |
| 3 | SSB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất, chưa kiểm toán | 35 | Tổng các ngành nhìn thấy là 237.042.157 nhưng dòng tổng in 237.047.100; thiếu đúng 4.943 | Cho vay khách hàng | 727; dòng gần nhất bị thiếu là 731 | PDF thật không in dòng “Cung cấp nước; quản lý và xử lý rác thải, nước thải” 4.943 trong bảng này. Báo cáo khác có dòng đó nhưng không được dùng để điền ngược. | **LỖI SOURCE / NGUỒN BỎ SÓT DÒNG** |

### Phân loại ba residual

| Nhóm nguyên nhân | Số PDF | Ý nghĩa |
|---|---:|---|
| Chưa có khoản mục phù hợp trong schema | 0 | Schema đã có đủ các ngành cần dùng trong ba bảng. |
| Thuật toán chưa xác định được cột/kỳ/đơn vị | 0 | Cột, kỳ và đơn vị đều đã xác định được. |
| Bảng nguồn không khép kín | 3 | Dữ liệu nhìn thấy mâu thuẫn với dòng tổng nên phải giữ UNRESOLVED. |

## SOURCE_ONLY trong PDF READY

SOURCE_ONLY không đồng nghĩa UNRESOLVED. Các dòng dưới đây vẫn được giữ trong phép kiểm tra tổng; candidate chỉ READY khi toàn bộ số nguồn khép kín. Chúng không có mapping một-một vì là subtotal trung gian, chi tiết sâu hơn schema hoặc một dòng gộp nhiều bản chất.

| Nhóm SOURCE_ONLY | Số PDF READY | Xử lý hiện tại | Vì sao không tạo mapping riêng |
|---|---:|---|---|
| “Cho vay các tổ chức kinh tế” / subtotal ngành | 112 | Dùng làm subtotal trung gian để khép tổng 727 | Đây là subtotal cấu trúc, không phải một ngành kinh tế độc lập. |
| “Cá nhân” / “Cho vay cá nhân” | 34 | Cộng vào tổng 727 | 6059 chỉ áp dụng cho cá nhân mua nhà; dòng cá nhân chung rộng hơn và không được ép vào 6059. |
| “Xây dựng và kinh doanh bất động sản” | 2 | Giữ nguyên trong tổng 727 | Dòng gộp đồng thời 732 và 735, không có căn cứ tách tỷ lệ. |
| Các ngành sản xuất chi tiết của MSB | 13 | Cộng toàn bộ nhóm, map kết quả vào 733 | Schema có 733 ở cấp ngành lớn nhưng không có child một-một cho từng sản phẩm. |
| Năm ngành thương mại chi tiết của MSB | 13 | Cộng toàn bộ nhóm, map kết quả vào 734 | Các dòng là chi tiết sâu hơn 734. |
| Ba ngành vận tải chi tiết của MSB | 13 | Cộng toàn bộ nhóm, map kết quả vào 736 | Các dòng là chi tiết sâu hơn 736. |
| Năm nhãn gộp nhiều ngành của MSB | 13 | Chỉ tham gia tổng 727 | Mỗi nhãn bao phủ từ hai ReportNormId trở lên hoặc còn mơ hồ, nên không ép vào một ID. |

### 34 PDF có dòng “Cá nhân/Cho vay cá nhân”

- **ABB (2):** `1_abb_2025_9_9_0dee6d3_bctc_hn_ktsx_30_06_2025_tv.pdf` trang 42; `3_abb_2025_9_9_5fa7e09_bctc_rl_ktsx_30_06_2025_tv.pdf` trang 40.
- **MSB (13):** `BCTC Công ty mẹ Kiểm toán năm 2025.pdf` trang 36; `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` trang 37; `BCTC Công ty mẹ quý 1 năm 2025.pdf` trang 32; `BCTC Công ty mẹ quý 2 năm 2025.pdf` trang 32; `BCTC Công ty mẹ quý 3 năm 2025.pdf` trang 32; `BCTC Công ty mẹ quý 4 năm 2025.pdf` trang 32; `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` trang 37; `BCTC Hợp nhất quý 1 năm 2025.pdf` trang 33; `BCTC Hợp nhất quý 2 năm 2025.pdf` trang 33; `BCTC Hợp nhất quý 3 năm 2025.pdf` trang 33; `MSB 20260130 - MSB - Bao cao tai chinh Hop nhat Quy 4 2025.pdf` trang 32; `BCTC Công ty mẹ quý 1 năm 2026.pdf` trang 34; `BCTC Công ty mẹ quý 2 năm 2026.pdf` trang 29.
- **NVB (3):** `BCTC Công ty mẹ Kiểm toán năm 2025.pdf` trang 31; `BCTC Hợp nhất Kiểm toán năm 2025.pdf` trang 31; `VI_BaoCaoTaiChinh_BanNien_2025_HopNhat.pdf` trang 30.
- **TCB (16):** `BCTC Công ty mẹ Kiểm toán năm 2025.pdf` trang 44; `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` trang 42; `BCTC Công ty mẹ quý 1 năm 2025.pdf` trang 37; `BCTC Công ty mẹ quý 2 năm 2025.pdf` trang 37; `BCTC Công ty mẹ quý 3 năm 2025.pdf` trang 37; `BCTC Công ty mẹ quý 4 năm 2025.pdf` trang 36; `BCTC Hợp nhất Kiểm toán năm 2025.pdf` trang 52; `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` trang 47; `BCTC Hợp nhất quý 1 năm 2025.pdf` trang 38; `BCTC Hợp nhất quý 2 năm 2025.pdf` trang 41; `BCTC Hợp nhất quý 3 năm 2025.pdf` trang 44; `BCTC Hợp nhất quý 4 năm 2025.pdf` trang 45; `BCTC Công ty mẹ quý 1 năm 2026.pdf` trang 35; `BCTC Công ty mẹ quý 2 năm 2026.pdf` trang 34; `BCTC Hợp nhất quý 1 năm 2026.pdf` trang 43; `BCTC Hợp nhất quý 2 năm 2026.pdf` trang 43.

### Hai PDF có dòng gộp “Xây dựng và kinh doanh bất động sản”

- **NVB:** `BCTC Công ty mẹ Kiểm toán năm 2025.pdf` trang 31.
- **NVB:** `BCTC Hợp nhất Kiểm toán năm 2025.pdf` trang 31.

### 13 PDF MSB có bảng chi tiết sâu hơn schema

- `BCTC Công ty mẹ Kiểm toán năm 2025.pdf` trang 36.
- `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` trang 37.
- `BCTC Công ty mẹ quý 1 năm 2025.pdf` trang 32.
- `BCTC Công ty mẹ quý 2 năm 2025.pdf` trang 32.
- `BCTC Công ty mẹ quý 3 năm 2025.pdf` trang 32.
- `BCTC Công ty mẹ quý 4 năm 2025.pdf` trang 32.
- `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` trang 37.
- `BCTC Hợp nhất quý 1 năm 2025.pdf` trang 33.
- `BCTC Hợp nhất quý 2 năm 2025.pdf` trang 33.
- `BCTC Hợp nhất quý 3 năm 2025.pdf` trang 33.
- `MSB 20260130 - MSB - Bao cao tai chinh Hop nhat Quy 4 2025.pdf` trang 32.
- `BCTC Công ty mẹ quý 1 năm 2026.pdf` trang 34.
- `BCTC Công ty mẹ quý 2 năm 2026.pdf` trang 29.

Các dòng chi tiết được cộng vào 733 gồm chế biến thủy hải sản; lương thực/thực phẩm; dệt may/da giày; gỗ; giấy/in ấn; hóa dược/cao su/nhựa; vật liệu xây dựng; thép thành phẩm; phôi thép (không có trong mẫu 2026); inox/luyện kim; máy móc/phương tiện; điện tử; đóng tàu; thiết bị khác. Năm dòng thương mại được cộng vào 734; ba dòng vận tải bộ/sông, biển và kho bãi được cộng vào 736.

Năm nhãn MSB vẫn SOURCE_ONLY vì gộp nhiều bản chất: “Sản xuất và phân phối điện, năng lượng, cung cấp nước…” (730 + 731); “Khách sạn, du lịch, ăn uống, vui chơi giải trí” (738 + 5720); “Kinh doanh bất động sản và cơ sở hạ tầng” (ít nhất gần 735 nhưng phần cơ sở hạ tầng rộng hơn); “Dịch vụ bưu chính viễn thông” (có thể liên quan 736 hoặc 740); và nhóm dịch vụ công nghệ/khoa học/hành chính/giáo dục/y tế/thông tin tổng hợp (nhiều ID). Đây là **CÓ NỘI DUNG TRÊN PDF NHƯNG CHƯA CÓ QUAN HỆ MỘT-MỘT VỚI SCHEMA**, không phải lỗi của PDF READY.

## 89 PDF NOT_OBSERVED

NOT_OBSERVED nghĩa là sau khi kiểm tra đúng phạm vi báo cáo, không thấy bảng phân tích dư nợ cho vay theo ngành kinh tế; đây không phải lỗi. Danh sách dưới đây thuộc đúng tập 204 PDF đã đủ JSON.

- **ABB (5 PDF):** `2025/BCTC Hợp nhất quý 1 năm 2025.pdf`; `2025/phpkgbljk-bctc-hn-q3-2025-68fb4c313c9de.pdf`; `2025/phplpiamp-bctc-q2-2025-rl-6889fde02c284.pdf`; `2025/phppidjcp-bctc-rl-q3-2025-68fb4c6b97d59.pdf`; `2026/phpbbdkfl-bctc-rl-q1-2026-69e18d88eace3.pdf`.
- **BAB (4 PDF):** `2025/1_bab_2026_2_4_4d13ce7_vi_baocaotaichinh_q4_2025.pdf`; `2025/BAB_BCTC Hop nhat Quy 3.2025_Tieng Viet.pdf`; `2025/BCTC Hợp nhất quý 1 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 4 năm 2025.pdf`.
- **EIB (10 PDF):** `2025/20260130 - EIB - BCTC hop nhat Q4.2025.pdf`; `2025/BCTC Công ty mẹ quý 2 năm 2025.pdf`; `2025/BCTC Công ty mẹ quý 3 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 1 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 2 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 3 năm 2025.pdf`; `2026/BCTC Công ty mẹ quý 1 năm 2026.pdf`; `2026/BCTC Công ty mẹ quý 2 năm 2026.pdf`; `2026/BCTC Hợp nhất quý 1 năm 2026.pdf`; `2026/BCTC Hợp nhất quý 2 năm 2026.pdf`.
- **NAB (10 PDF):** `2025/BCTC Công ty mẹ quý 3 năm 2025.pdf`; `2025/BCTC Công ty mẹ quý 4 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 3 năm 2025.pdf`; `2025/NAB NAMABANK_2025_Q2_BCTC HN.pdf`; `2025/NAB NAMABANK_2025_Q2_BCTC RL.pdf`; `2025/NAB namabank_2025_q4_bctc-hn.pdf`; `2026/BCTC Công ty mẹ quý 1 năm 2026.pdf`; `2026/BCTC Công ty mẹ quý 2 năm 2026.pdf`; `2026/BCTC Hợp nhất quý 1 năm 2026.pdf`; `2026/BCTC Hợp nhất quý 2 năm 2026.pdf`.
- **NVB (5 PDF):** `2025/6_nvb_2026_2_3_925648e_vi_baocaotaichinh_q1_2025_riengle_signed.pdf`; `2025/BCTC Công ty mẹ quý 1 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 1 năm 2025.pdf`; `2026/2_nvb_2026_7_30_2bf1dd5_bctc__rieng_le__tieng_viet__q2_2026_signed.pdf`; `2026/BCTC - HOP NHAT - TIENG VIET - Q1.2026.pdf`.
- **OCB (10 PDF):** `2025/BCTC Công ty mẹ quý 1 năm 2025.pdf`; `2025/BCTC Công ty mẹ quý 2 năm 2025.pdf`; `2025/BCTC Công ty mẹ quý 3 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 1 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 2 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 3 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 4 năm 2025.pdf`; `2026/BCTC Công ty mẹ quý 1 năm 2026.pdf`; `2026/BCTC Hợp nhất quý 1 năm 2026.pdf`; `2026/BCTC Hợp nhất quý 2 năm 2026.pdf`.
- **PGB (1 PDF):** `2025/BCTC Soát xét 6 tháng đầu năm 2025.pdf`.
- **SGB (5 PDF):** `2025/BAO-CAO-TAI-CHINH-HOP-NHAT-QUY-3---20205.pdf`; `2025/BAO-CAO-TAI-CHINH-RIENG-LE-QUY-3---2025.pdf`; `2025/BCTC Hợp nhất quý 1 năm 2025.pdf`; `2026/BCTC-HN-quy-1---2026_VIE_0001.pdf`; `2026/BCTC-Rieng-le-quy-1---2026_VIE.pdf`.
- **SHB (2 PDF):** `2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf`; `2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf`.
- **SSB (9 PDF):** `2025/BCTC Công ty mẹ quý 2 năm 2025.pdf`; `2025/BCTC Công ty mẹ quý 3 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 1 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 2 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 3 năm 2025.pdf`; `2025/source_revisions/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025 - Nguồn chính thức SeABank.pdf`; `2025/source_revisions/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025 - Nguồn chính thức SeABank.pdf`; `2026/BCTC Công ty mẹ quý 1 năm 2026.pdf`; `2026/BCTC Công ty mẹ quý 2 năm 2026.pdf`.
- **STB (10 PDF):** `2025/BCTC Công ty mẹ quý 1 năm 2025.pdf`; `2025/BCTC Công ty mẹ quý 2 năm 2025.pdf`; `2025/BCTC Công ty mẹ quý 4 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 1 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 2 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 3 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 4 năm 2025.pdf`; `2026/BCTC Công ty mẹ quý 1 năm 2026.pdf`; `2026/BCTC Hợp nhất quý 1 năm 2026.pdf`; `2026/BCTC Hợp nhất quý 2 năm 2026.pdf`.
- **VAB (13 PDF):** `2025/20250815 - VAB - BCTC HN BAN NIEN 2025_0001.pdf`; `2025/2_vab_2025_4_15_527ed46_vi_baocaotaichinh_q1_2025.pdf`; `2025/2_vab_2025_4_15_d453cb6_vn_baocaotaichinh_q1_2025.pdf`; `2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf`; `2025/BCTC Công ty mẹ quý 3 năm 2025.pdf`; `2025/BCTC Công ty mẹ quý 4 năm 2025.pdf`; `2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf`; `2025/BCTC Hợp nhất quý 3 năm 2025.pdf`; `2025/BCTC Hợp nhất quý 4 năm 2025.pdf`; `2025/BCTC RIENG LE QUY 2.2025-TV_0001-da nen.pdf`; `2026/BCTC Công ty mẹ quý 2 năm 2026.pdf`; `2026/BCTC Hợp nhất quý 2 năm 2026.pdf`; `2026/BCTC Q1.2026 RIENG LE_0001.pdf`.
- **VBB (5 PDF):** `2025/3_vbb_2026_2_2_a18dc42_vi_baocaotaichinh_riengle_q4_2025.pdf`; `2025/BCTC Hợp nhất quý 4 năm 2025.pdf`; `2026/3_vbb_2026_5_2_fa0b162_vi_baocaotaichinh_riengle_q1_2026.pdf`; `2026/BCTC Công ty mẹ quý 2 năm 2026.pdf`; `2026/BCTC Hợp nhất quý 2 năm 2026.pdf`.

## Truy vết kỹ thuật

- Baseline: `/dev/shm/bctc-ai-27-bank-family-live-v1/family-07-loan-industry-classification.json`
- Kết quả audit cuối: `/dev/shm/family07-root-current-v7.json`
- Database replay: `/dev/shm/family07-root-results-v7.sqlite3`
- Tập PDF bất biến: `/dev/shm/bctc-ai-27-bank-family-live-v1/current-corpus-manifest-indexes/32c474f657f9484244e9675a0ca4801cb49b4923971dfb7bea17081904154747.json`
