# Family 9 — Phân tích dư nợ cho vay theo thời hạn

Checkpoint này lưu kết quả audit cuối trên tập bất biến 204 PDF của 19 ngân hàng mới, chỉ từ năm 2025 đến hiện tại và chỉ gồm PDF đã có JSON toàn tài liệu. Đây là bằng chứng staging để tổng hợp vào hai bảng cuối dự án; chưa thay thế `COMPLETED_TM_FAMILIES.md` hoặc `UNRESOLVED_MAPPING_LEDGER.md`.

## Kết quả kiểm tra chéo

| Trạng thái | Baseline | Sau audit | Chênh lệch |
|---|---:|---:|---|
| READY | 177 | 203 | +26 |
| NOT_OBSERVED | 0 | 0 | 0 |
| UNRESOLVED | 27 | 1 | -26 |
| Mapping | 533 | 620 | +87 |

- Kiểm tra tổng: **203 READY + 0 NOT_OBSERVED + 1 UNRESOLVED = 204 PDF**.
- Cả 177 PDF READY cũ giữ nguyên chính xác status, candidate count, candidate được chọn, reasons và toàn bộ mapping.
- Có 26 PDF chuyển từ UNRESOLVED sang READY; không phát sinh false NOT_OBSERVED.
- Kết quả có đúng 203 mapping cho từng ReportNormId 753, 754 và 755; 11 PDF có thêm ReportNormId 5747. Không PDF nào có ID trùng và mọi mapping giữ đúng thứ tự schema.

## Tiến độ theo ngân hàng trên tập 204 PDF bất biến

| Ngân hàng | PDF khảo sát | Baseline READY | Baseline UNRESOLVED | Sau audit READY | Sau audit UNRESOLVED |
|---|---:|---:|---:|---:|---:|
| ABB | 7 | 7 | 0 | 7 | 0 |
| BAB | 5 | 5 | 0 | 5 | 0 |
| BVB | 8 | 8 | 0 | 8 | 0 |
| EIB | 13 | 10 | 3 | 13 | 0 |
| KLB | 11 | 7 | 4 | 11 | 0 |
| LPB | 6 | 6 | 0 | 6 | 0 |
| MSB | 13 | 13 | 0 | 13 | 0 |
| NAB | 11 | 11 | 0 | 11 | 0 |
| NVB | 8 | 8 | 0 | 8 | 0 |
| OCB | 13 | 13 | 0 | 13 | 0 |
| PGB | 7 | 2 | 5 | 6 | 1 |
| SGB | 12 | 12 | 0 | 12 | 0 |
| SHB | 14 | 14 | 0 | 14 | 0 |
| SSB | 13 | 13 | 0 | 13 | 0 |
| STB | 13 | 9 | 4 | 13 | 0 |
| TCB | 16 | 9 | 7 | 16 | 0 |
| TPB | 10 | 8 | 2 | 10 | 0 |
| VAB | 13 | 13 | 0 | 13 | 0 |
| VBB | 11 | 9 | 2 | 11 | 0 |
| **Tổng** | **204** | **177** | **27** | **203** | **1** |

## Cấu trúc schema

| Khoản mục | ReportNormId | Cách sử dụng |
|---|---:|---|
| Phân tích dư nợ cho vay theo thời hạn | 752 | Context family, không tạo mapping riêng |
| Nợ ngắn hạn | 753 | Mapping trực tiếp từ dòng ngắn hạn |
| Nợ trung hạn | 754 | Mapping trực tiếp từ dòng trung hạn |
| Nợ dài hạn | 755 | Mapping trực tiếp từ dòng dài hạn |
| Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán | 5747 | Mapping khi PDF có cấu phần riêng cùng bản chất |

Ba dòng 753–755 phải cộng đúng tổng dư nợ cốt lõi ở cả hai kỳ. Nếu PDF có cấu phần 5747 riêng, tổng cuối còn phải khép đúng theo cấu trúc in trên PDF. Dòng tổng và owner “Dư nợ cho vay/Cho vay khách hàng” là bằng chứng cấu trúc, không phải khoản mục SOURCE_ONLY.

## Hai alias đã bổ sung, không tạo ID mới

- `Nợ trung hạn (Trên 01 tới 05 năm)` và `Nợ trung hạn (Từ 1 đến 5 năm)` là biến thể cách viết của ReportNormId 754.
- `Các khoản cho vay hoạt động ký quỹ và cho vay hoạt động ứng trước tiền bán của khách hàng` cùng bản chất với ReportNormId 5747.

Hai alias được thêm vào config family và có unit test riêng. Hồi quy trên 140 PDF của 8 ngân hàng cũ đạt **140 READY / 0 NOT_OBSERVED / 0 UNRESOLVED / 438 mapping**; cả status, candidate count, mapping, candidate được chọn và reasons đều giống chính xác baseline cũ.

## Toàn bộ 27 PDF UNRESOLVED ở baseline

### 1. Tám PDF thiếu alias “nợ trung hạn”

Các bảng dưới đây đều có đủ nợ ngắn hạn, nợ trung hạn, nợ dài hạn và tổng; cả hai cột đều khép số học. Bảy PDF chuyển được sang READY nhờ alias. Riêng PGB Q1/2025 phải giữ UNRESOLVED vì mâu thuẫn kỳ nguồn, trình bày riêng ở mục sau.

| Ngân hàng | File PDF | Kỳ / loại báo cáo | Trang | Tổng kỳ hiện tại / so sánh | Kết luận |
|---|---|---|---:|---:|---|
| EIB | `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` | 6 tháng/2025, công ty mẹ, soát xét | 30 | 182.741.228 / 165.154.897 triệu đồng | Alias `Trên 01 tới 05 năm`; đủ điều kiện READY |
| EIB | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | Năm 2025, hợp nhất, kiểm toán | 31 | 184.215.863 / 165.154.897 triệu đồng | Alias `Trên 01 tới 05 năm`; đủ điều kiện READY |
| EIB | `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` | 6 tháng/2025, hợp nhất, soát xét | 30 | 182.741.228 / 165.154.897 triệu đồng | Alias `Trên 01 tới 05 năm`; đủ điều kiện READY |
| PGB | `3_pgb_2025_10_22_8eac562_vi_baocaotaichinh_q3_2025.pdf` | Q3/2025; phạm vi/kiểm toán chưa xác định từ tên file | 26 | 44.348.532 / 41.236.482 triệu đồng | Alias `Từ 1 đến 5 năm`; đủ điều kiện READY |
| PGB | `4_pgb_2026_1_22_d793078_vi_baocaotaichinh_q4_2025.pdf` | Q4/2025; phạm vi/kiểm toán chưa xác định từ tên file | 26 | 46.340.642 / 41.236.482 triệu đồng | Alias `Từ 1 đến 5 năm`; đủ điều kiện READY |
| PGB | `BCTC quý 1 năm 2025.pdf` | Q1/2025; phạm vi/kiểm toán chưa xác định từ tên file | 26 | 45.348.567 / 41.236.482 triệu đồng | **Giữ UNRESOLVED do mâu thuẫn kỳ nguồn** |
| PGB | `1_pgb_2026_4_28_15bbc70_vi_baocaotaichinh_q1_2026.pdf` | Q1/2026; phạm vi/kiểm toán chưa xác định từ tên file | 26 | 44.382.596 / 46.340.642 triệu đồng | Alias `Từ 1 đến 5 năm`; đủ điều kiện READY |
| PGB | `2_pgb_2026_7_22_3a0f521_vi_baocaotaichinh_q2_2026.pdf` | Q2/2026; phạm vi/kiểm toán chưa xác định từ tên file | 26 | 48.349.047 / 46.340.642 triệu đồng | Alias `Từ 1 đến 5 năm`; đủ điều kiện READY |

### 2. Bốn PDF KLB — bảng family nằm trong bảng “Cho vay khách hàng” rộng

Các PDF đều có một group explicit “Phân tích dư nợ theo thời gian” với ba hàng con và tổng khép đúng. Lỗi cũ là so độ cụ thể của title với alias cha ngắn nhất toàn config, thay vì alias thực sự khớp title. Sau sửa, engine chỉ cắt group explicit khi nó cụ thể hơn title thực tế, có subtree liên tục và khép số học; sibling chất lượng nợ, loại hình và ngành không bị kéo vào.

| File PDF | Kỳ / loại báo cáo | Trang | Nợ ngắn / trung / dài kỳ hiện tại | Tổng hiện tại / so sánh | Kết luận |
|---|---|---:|---:|---:|---|
| `BAO CAO TAI CHINH QUY 3.2025 HOP NHAT.pdf` | Q3/2025, hợp nhất | 21 | 36.265.037 / 28.201.309 / 6.456.044 | 70.922.390 / 61.431.909 | READY sau generic specificity guard |
| `BAO CAO TAI CHINH QUY 3.2025 RIENG.pdf` | Q3/2025, công ty mẹ | 22 | 36.265.037 / 28.201.309 / 6.456.044 | 70.922.390 / 61.431.909 | READY |
| `BCTC Công ty mẹ quý 2 năm 2025.pdf` | Q2/2025, công ty mẹ | 21 | 43.647.387 / 21.465.613 / 4.434.023 | 69.547.023 / 61.431.909 | READY |
| `bao-cao-tai-chinh-giua-nien-do-q4.2025-rieng_tv.pdf` | Q4/2025, công ty mẹ | 23 | 37.632.322 / 26.907.503 / 7.047.877 | 71.587.702 / 61.431.909 | READY sau generic specificity guard |

Rule so group explicit với **alias cha thực sự khớp title**; không route theo KLB, tên file hoặc số trang. Test dương KLB và các test âm chống kéo sibling/hierarchy leak đều đạt.

### 3. Năm PDF có bảng bị tách đúng hướng qua hai trang liền kề

Mỗi cặp có marker tiếp nối rõ ràng, hai cột MONEY tương thích, đúng một total ở phần sau và số học khép ở cả hai kỳ. Replay toàn corpus xác nhận cả năm PDF đều READY.

| Ngân hàng | File PDF | Kỳ / loại báo cáo | Trang | Tổng hiện tại / so sánh |
|---|---|---|---:|---:|
| STB | `BCTC Hợp nhất quý 1 năm 2025.pdf` | Q1/2025, hợp nhất | 31–32 | 564.327.201 / 539.314.658 triệu đồng |
| STB | `BCTC Hợp nhất quý 2 năm 2025.pdf` | Q2/2025, hợp nhất | 31–32 | 587.960.029 / 539.314.658 triệu đồng |
| STB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | Q3/2025, hợp nhất | 30–31 | 606.048.204 / 539.314.658 triệu đồng |
| STB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất | 30–31 | 626.392.336 / 539.314.658 triệu đồng |
| VBB | `000000014895177_VI_BaoCaoTaiChinh_RiengLe_Q1_2025.pdf` | Q1/2025, riêng lẻ | 16–17 | 97.298.822 / 93.637.036 triệu đồng |

### 4. Chín PDF TCB/TPB có cấu phần cho vay ký quỹ/ứng trước

Ba bucket cốt lõi và dòng cho vay ký quỹ/ứng trước đều hiện rõ; subtotal/grand total khép đúng. Dòng dài chỉ là biến thể tên, map vào ReportNormId 5747, không tạo ID mới.

| Ngân hàng | File PDF | Kỳ / loại báo cáo | Trang | Tổng cuối kỳ hiện tại / so sánh |
|---|---|---|---:|---:|
| TCB | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | Năm 2025, hợp nhất, kiểm toán | 51 | 767.617.129 / 631.724.964 triệu đồng |
| TCB | `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` | 6 tháng/2025, hợp nhất, soát xét | 46 | 710.313.010 / 631.724.964 triệu đồng |
| TCB | `BCTC Hợp nhất quý 2 năm 2025.pdf` | Q2/2025, hợp nhất | 41 | 710.313.010 / 631.724.964 triệu đồng |
| TCB | `BCTC Hợp nhất quý 3 năm 2025.pdf` | Q3/2025, hợp nhất | 43 | 766.709.929 / 631.724.964 triệu đồng |
| TCB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất | 44 | 767.617.129 / 631.724.964 triệu đồng |
| TCB | `BCTC Hợp nhất quý 1 năm 2026.pdf` | Q1/2026, hợp nhất | 43 | 796.863.951 / 767.617.129 triệu đồng |
| TCB | `BCTC Hợp nhất quý 2 năm 2026.pdf` | Q2/2026, hợp nhất | 42 | 847.335.568 / 767.617.129 triệu đồng |
| TPB | `BCTC Hợp nhất quý 4 năm 2025.pdf` | Q4/2025, hợp nhất | 38 | 305.816.635 / 250.331.368 triệu đồng |
| TPB | `BCTC Hợp nhất quý 1 năm 2026.pdf` | Q1/2026, hợp nhất | 40 | 316.042.203 / 305.816.635 triệu đồng |

### 5. Một PDF VBB dùng header vai trò kỳ

`1_vbb_2025_8_1_de20fa4_vi_baocaotaichinh_riengle_q2_2025.pdf`, trang 16, riêng lẻ Q2/2025, dùng header `Số cuối quý / Số đầu năm`. Engine semantic-period hiện tại đã đánh giá READY trực tiếp: nợ ngắn 65.258.442 / 58.480.666; trung 20.135.437 / 17.826.226; dài 17.053.579 / 17.330.144; tổng 102.447.458 / 93.637.036 triệu đồng. Không bịa ngày từ header vai trò này.

### 6. Kiểm tra mở rộng trên đầy đủ 271 PDF của 19 ngân hàng mới

Tập 271 PDF đạt **270 READY / 0 NOT_OBSERVED / 1 UNRESOLVED / 822 mapping**. U duy nhất vẫn là PGB Q1/2025 bên dưới.

PDF VBB `92-BCTC-hopnhat-Q3-VIE.pdf`, hợp nhất Q3/2025, trang 26, từng bị U vì JSON giữ line-break trong header dưới dạng literal `Ngày 30 tháng 9\\nnăm 2025`. PDF và JSON có đủ bảng: nợ ngắn hạn 71.954.600 / 58.480.666; nợ trung hạn 15.123.007 / 17.826.226; nợ dài hạn 18.117.653 / 17.330.144; tổng 105.195.260 / 93.637.036 triệu đồng. Parser nay chỉ coi literal `\\n` là whitespace khi đọc ngày, đồng thời giữ nguyên text và span nguồn; không sửa OCR và không bịa endpoint. Kết quả chuyển U → READY.

## Trường hợp phải giữ UNRESOLVED — PGB Q1/2025

**Ngân hàng:** PGB  
**File PDF:** `BCTC quý 1 năm 2025.pdf`  
**Kỳ công bố:** Quý 1/2025  
**Loại báo cáo/kiểm toán:** Chưa xác định chắc từ tên file  
**Trang PDF:** 26  
**Khoản mục cha:** Cho vay khách hàng  
**Khoản mục:** Nợ ngắn hạn; Nợ trung hạn (Từ 1 đến 5 năm); Nợ dài hạn  
**Schema gần nhất:** 753, 754, 755  
**Giá trị:** 25.493.298 / 23.240.985; 6.170.734 / 5.152.172; 13.684.535 / 12.843.325; tổng 45.348.567 / 41.236.482 triệu đồng.

PDF trang 26 hiển thị running header “Cho giai đoạn từ ngày 01/01/2025 đến 31/03/2025”, nhưng cả bốn bảng trên chính trang đó lại in header cột `31/12/2025 | 31/12/2024`. Ảnh PDF đã được kiểm tra trực quan, nên đây không phải lỗi OCR của Gemini. JSON trang 27 cũng giữ nguyên title typed “Cho giai đoạn từ ngày 01/01/2025 đến 31/03/2025”.

**Lý do chưa map:** kỳ hiện tại của bảng mâu thuẫn với kỳ báo cáo của chính tài liệu; không có căn cứ để tự sửa `31/12/2025` thành `31/03/2025`.  
**Phân loại:** `KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ` và `MÂU THUẪN NGUỒN PDF`.  
**Kết luận:** giữ UNRESOLVED; alias không được phép che mâu thuẫn endpoint.

## SOURCE_ONLY và NOT_OBSERVED

- **NOT_OBSERVED:** baseline không có trường hợp nào và audit chưa có bằng chứng để tạo trường hợp mới.
- **SOURCE_ONLY:** chưa phát hiện khoản mục kinh doanh nào cần ghi riêng. Owner, subtotal và total chỉ làm bằng chứng khép cấu trúc. Cấu phần cho vay ký quỹ/ứng trước đã có ReportNormId 5747 nên không phải SOURCE_ONLY.
- Không phát hiện dòng nghiệp vụ thư tín dụng trả chậm trong 204 PDF mới cần một mapping riêng cho Family 9; nếu xuất hiện ở corpus khác, nó chỉ được dùng theo cấu trúc khai báo và không được tự tạo ID.

## Kiểm tra hồi quy

- **204 PDF Family 9:** 203 READY / 0 NOT_OBSERVED / 1 UNRESOLVED / 620 mapping. 177 READY cũ giữ nguyên toàn bộ trial semantics.
- **271 PDF của 19 ngân hàng mới:** 270 READY / 0 NOT_OBSERVED / 1 UNRESOLVED / 822 mapping; không còn job repair chờ xử lý.
- **140 PDF của 8 ngân hàng cũ:** 140 READY / 0 NOT_OBSERVED / 0 UNRESOLVED / 438 mapping. Toàn bộ status, candidate count, candidate được chọn, reasons và mapping giống baseline cũ; file envelope khác hash vì config alias có phiên bản mới.
- **Family 7:** byte-identical checkpoint đã chốt, vẫn 112 READY / 89 NOT_OBSERVED / 3 UNRESOLVED / 1.946 mapping.
- **Family 8:** byte-identical checkpoint đã chốt, vẫn 204 READY / 0 NOT_OBSERVED / 0 UNRESOLVED / 1.235 mapping.
- **Test:** 120 test liên quan runner, flat/hierarchical evaluator, adjacent continuation, structural context và Family 7/8/9 đều đạt. Riêng file Family 9 có 14 test. Ruff và `git diff --check` đạt.

Guard mâu thuẫn endpoint được giới hạn bằng semantic capability `LOAN_MATURITY_BUCKETS`, không route theo ngân hàng/file/trang. Điều này giữ nguyên kết quả Family 7/8; mâu thuẫn nguồn tương tự nếu cần thay đổi các family khác phải được audit và phê duyệt riêng.

## Truy vết kỹ thuật ở cuối tài liệu

- Baseline 204 PDF: `/dev/shm/bctc-ai-27-bank-family-live-v1/family-09-loan-maturity-buckets.json`.
- Kết quả cuối 204 PDF: `/dev/shm/family09-audit-rerun-v4.json`; SHA-256 `7afe081212bd0654f53fd4219bf4e60f997546c384da839a26d3a04b9bd8fd15`.
- Database replay 204 PDF: `/dev/shm/family09-audit-rerun-v4.sqlite3`.
- Kết quả full-271: `/dev/shm/family09-full271-v2.json`; SHA-256 `be29dfb8466cfeade0a7051148492727523f3a7e0f6e2d0a6f75c580663ea585`.
- Hồi quy 8 ngân hàng: `/dev/shm/family09-old8-final-regression-v3.json`; SHA-256 `435c5db6b82c551a48da671db57860ecd7a574db8cb9c81f212e345a407e155e`.
- Hồi quy Family 7: `/dev/shm/family07-after-f9-regression-v2.json`; SHA-256 `7ae3fcc6e0ee788ebffb0c89475388bce834088a428db20bac4b48751af49852`.
- Hồi quy Family 8: `/dev/shm/family08-after-f9-regression-v2.json`; SHA-256 `48a61d00c0e69e20f921d43cbe6f3cc9e28d07eec2e0e0d4fc6a247b253f56f8`.
- PDF nguồn PGB: `vietstock_bctc/PGB/2025/BCTC quý 1 năm 2025.pdf`.
- PDF nguồn VBB full-271: `vietstock_bctc/VBB/2025/92-BCTC-hopnhat-Q3-VIE.pdf`.

Hash code/config/test tại lúc release ownership:

- Runner: `168905abb6bab34dee4a1534f6d1262a3cb3e38a8c757cb538c82fdbd3db5bb0`.
- Hierarchical evaluator: `e1aeb91966bfa3d0d8c81e2396253bd84566028973ac400630e972d2f63253e4`.
- Config Family 9: `4f977d6e78934c5599b55f3afbd4ec1943eb3cb0e89aea47d57de5012ae7017d`.
- Unit test Family 9: `4ecb60513b67cb187dbb6eacf64c354fdc02b1be86548456809dc35bcc9adf5d`.
- Unit test runner: `8c16cfb3582e5bd0fd31a3774a8280bcca5d43b9d90518b8a41ff2433dcdece7`.
