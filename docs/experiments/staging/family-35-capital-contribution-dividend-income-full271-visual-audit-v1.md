# Family 35 — Thu nhập từ góp vốn, mua cổ phần và cổ tức

Checkpoint này tổng hợp Family 35
(`CAPITAL_CONTRIBUTION_DIVIDEND_INCOME`) trên 271 báo cáo của 19 ngân hàng.
Toàn bộ PDF nguồn thuộc năm 2025 đến hiện tại; các cột so sánh năm 2024 nếu có
chỉ là cột nằm trong báo cáo 2025, không phải PDF năm 2024. Không gọi provider,
không sửa PDF hay page store và không coi kết quả là dữ liệu canonical.

Nguồn chạy được khóa bởi:

- full271 index
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-manifest-indexes/8d0a2a14b822d72a082ab3f0d5b416681fa998c964bb5462d5a067ea6706ce3a.json`
  (SHA-256 `969ff5f80732c39e4b7543ca1f5c1e5b5b827260f19981ed02945fe0c7379219`)
  và page store
  `/dev/shm/bctc-ai-27-bank-complete-corpus-v1.BSOm0s/artifacts/current-corpus-freeze-inputs/store-ea9dec62fc52705298fc590f64302c031bc298fb204297afb3186b10585e18d7.sqlite3`;
- old140 index
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-corpus-manifest-indexes/61be9e5dc44a261d2dbf3f396b9624e29cb4ae591ea0a7fdb83051352e7b60e3.json`
  (SHA-256 `79b80d5729d433d6ae06a03272e2f387b646f8bbf28a92b7941e7d3709444c8f`)
  và page store
  `/tmp/gemini-json-first-corpus-production-v2/artifacts/current-corpus-freeze-inputs/store-5962a19e86001f2effed5d954808a707ee43e562b807f40511bb19df772d3c1b.sqlite3`.

## Kết quả đọc nhanh

| Phạm vi | PDF khảo sát | READY | NOT_OBSERVED | UNRESOLVED | Mapping |
|---|---:|---:|---:|---:|---:|
| 19 ngân hàng, full271 | 271 | 217 | 52 | 2 | 639 |
| Hồi quy lịch sử, old140 | 140 | 133 | 7 | 0 | 431 |

Đối với 204 PDF đã có ở baseline ban đầu, kết quả cũ là 42 READY / 94
NOT_OBSERVED / 68 UNRESOLVED. Chiếu kết quả cuối theo đúng SHA nguồn của 204
PDF này cho 167 READY / 36 NOT_OBSERVED / 1 UNRESOLVED và 514 mapping. Đây là
phép chiếu cùng nguồn, không trộn mẫu số 204 với mẫu số 271.

### Theo ngân hàng

| Ngân hàng | PDF | READY | NOT_OBSERVED | UNRESOLVED |
|---|---:|---:|---:|---:|
| ABB | 12 | 12 | 0 | 0 |
| BAB | 10 | 8 | 0 | 2 |
| BVB | 14 | 13 | 1 | 0 |
| EIB | 16 | 16 | 0 | 0 |
| KLB | 16 | 16 | 0 | 0 |
| LPB | 7 | 7 | 0 | 0 |
| MSB | 16 | 0 | 16 | 0 |
| NAB | 16 | 7 | 9 | 0 |
| NVB | 16 | 5 | 11 | 0 |
| OCB | 16 | 15 | 1 | 0 |
| PGB | 7 | 7 | 0 | 0 |
| SGB | 14 | 14 | 0 | 0 |
| SHB | 16 | 16 | 0 | 0 |
| SSB | 16 | 16 | 0 | 0 |
| STB | 16 | 16 | 0 | 0 |
| TCB | 16 | 16 | 0 | 0 |
| TPB | 16 | 14 | 2 | 0 |
| VAB | 15 | 15 | 0 | 0 |
| VBB | 16 | 4 | 12 | 0 |
| **Tổng** | **271** | **217** | **52** | **2** |

## Cấu trúc schema đã nhận diện

| ReportNormId | Khoản mục | Số PDF có mapping |
|---:|---|---:|
| 1198 | Tổng thu nhập từ góp vốn, mua cổ phần và cổ tức | 211 |
| 1199 | Cổ tức/lợi nhuận được chia từ góp vốn, mua cổ phần | 129 |
| 1200 | Trong đó: từ chứng khoán vốn kinh doanh | 51 |
| 1201 | Trong đó: từ chứng khoán vốn đầu tư | 63 |
| 1202 | Trong đó: từ góp vốn, đầu tư dài hạn | 110 |
| 1203 | Phần lãi/lỗ theo phương pháp vốn chủ sở hữu | 11 |
| 1204 | Các khoản thu nhập khác | 64 |

Các biến thể đáng chú ý đã được xử lý bằng quy tắc chung:

- tên gọi `cổ tức`, `lợi tức`, `lợi nhuận được chia`, `thu từ chứng khoán đầu
  tư`, `công ty con` và `đầu tư dài hạn khác` được nhận diện theo đúng quan hệ
  cha/con, không tạo ID mới chỉ vì cách gọi khác;
- bảng chi tiết, dòng tổng trên báo cáo kết quả kinh doanh và bảng có tổng
  không ghi nhãn đều chỉ được nhận khi cột kỳ, đơn vị và phép cộng khép kín;
- 610 mapping dùng đơn vị triệu đồng và 29 mapping dùng VND; VND chỉ được nhận
  khi có bằng chứng đơn vị nguồn rõ ràng;
- ô trắng giữ `null`, dấu gạch nhìn thấy trên PDF mới được coi là zero; không
  suy zero từ phép cộng;
- 48 trang có lỗi chép nguồn đã được sửa trên bản sao riêng từ đúng ký tự/số
  nhìn thấy trên PDF, tổng cộng 125 ô. Mỗi sửa chữa khóa PDF, trang, ảnh render,
  bảng, hàng, cột, before-image và crop; phép cộng chỉ có quyền bác bỏ, không
  được sinh giá trị;
- hai bảng SGB dùng `Thu nhập góp vốn, mua cổ phần` như một dòng con độc lập,
  trong khi BAB dùng cùng câu đó làm nhãn nhóm. Adapter phân biệt bằng hình dạng
  cây và phép cộng, không route theo ngân hàng/file/trang;
- ba số VND có hậu tố thập phân bằng không được đọc nguyên giá trị, không scale
  và vẫn giữ nguyên chuỗi nguồn.

## UNRESOLVED — nội dung có trên PDF nhưng không có giá trị để map

Hai trường hợp dưới đây không phải thiếu schema và không phải OCR hỏng. Tên
bảng, hàng, hai kỳ và đơn vị đều rõ; tuy nhiên mọi ô tiền của cả năm hiện tại
và năm so sánh đều để trắng thật trên PDF. Theo hợp đồng nguồn, không được đổi
ô trắng thành 0 và cũng không được tạo mapping chỉ từ tên hàng.

| Ngân hàng | Kỳ | Báo cáo | Trạng thái kiểm tra | File PDF | Tổng trang | Trang | Khoản mục cha | Các hàng nhìn thấy | Schema gần nhất | Kết luận |
|---|---|---|---|---|---:|---:|---|---|---|---|
| BAB | Quý 1/2025 | Công ty mẹ | Chưa kiểm toán/không ghi | [BCTC Công ty mẹ quý 1 năm 2025.pdf](</workspace/bctc-ai/vietstock_bctc/BAB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf>) | 41 | 32 | `26. THU NHẬP TỪ GÓP VỐN, MUA CỔ PHẦN` | Cổ tức nhận được; từ chứng khoán vốn kinh doanh; từ chứng khoán vốn đầu tư; từ góp vốn, đầu tư dài hạn; các khoản thu nhập khác | 1199–1204, tổng 1198 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — tất cả ô Q1/2025 và Q1/2024 đều trắng; giữ UNRESOLVED, không suy 0. |
| BAB | Quý 1/2025 | Hợp nhất | Chưa kiểm toán/không ghi | [BCTC Hợp nhất quý 1 năm 2025.pdf](</workspace/bctc-ai/vietstock_bctc/BAB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf>) | 43 | 33 | `26. THU NHẬP TỪ GÓP VỐN, MUA CỔ PHẦN` | Cổ tức nhận được; từ chứng khoán vốn kinh doanh; từ chứng khoán vốn đầu tư; từ góp vốn, đầu tư dài hạn; các khoản thu nhập khác | 1199–1204, tổng 1198 | **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH** — tất cả ô Q1/2025 và Q1/2024 đều trắng; giữ UNRESOLVED, không suy 0. |

Lý do kỹ thuật tương ứng là `MAPPABLE_SCHEMA_ROLE_FRONTIER_IS_EMPTY`: hệ thống
nhận đúng cấu trúc nhưng không có ô giá trị nguồn nào để phát hành mapping.

## SOURCE_ONLY trong các PDF READY

Audit có 104 bản ghi bookkeeping mang tên `source_only_rows`, nhưng không được
hiểu rằng có 104 khoản mục chưa map:

| Nhóm | Số dòng | Cách xử lý |
|---|---:|---|
| Dòng tổng/kiểm soát đồng thời là nguồn của mapping | 85 | Đã map hoặc đã dùng trực tiếp để chứng minh mapping; không phải tồn đọng. |
| Dòng dự phòng EIB thuộc Family 33 | 12 | Không map vào cây Family 35; ghi chi tiết bên dưới. |
| Nhãn nhóm BAB không có giá trị | 1 | Chỉ là nhãn cấu trúc, đã dùng để xác định cha/con. |
| Dòng gộp hai loại chứng khoán vốn của SHB | 1 | Không thể tách chắc thành 1200 và 1201; ghi chi tiết bên dưới. |
| Dòng `Chi phí hoạt động` ngoài family | 5 | False positive trong vùng nguồn; không map. |
| **Tổng** | **104** | 85 đã là bằng chứng mapping; 19 là SOURCE_ONLY có lý do rõ. |

### 12 dòng EIB thuộc family khác

Khoản mục thực tế là `Chi dự phòng giảm giá khoản góp vốn, đầu tư dài hạn`,
nằm trong bảng thu nhập của EIB và được dùng để kiểm tra số tổng. Schema hiện
có RNID 6028 `(Trích lập)/Hoàn nhập dự phòng giảm giá góp vốn, đầu tư dài
hạn`, nhưng ID này là con của RNID 1193 thuộc Family 33 — Lãi thuần từ mua bán
chứng khoán đầu tư, không phải con của RNID 1198 của Family 35. Vì vậy không
được ép RNID 6028 vào mapping Family 35. Phân loại nguyên nhân:
**NGHI LÀ THUỘC FAMILY KHÁC**. Đây cũng không phải `CHƯA CÓ TRONG SCHEMA`.

| Kỳ | Báo cáo | Kiểm tra | File PDF | Tổng trang | Trang |
|---|---|---|---|---:|---:|
| Quý 4/2025 | Hợp nhất | Chưa kiểm toán/không ghi | [20260130 - EIB - BCTC hop nhat Q4.2025.pdf](</workspace/bctc-ai/vietstock_bctc/EIB/2025/20260130 - EIB - BCTC hop nhat Q4.2025.pdf>) | 40 | 29 |
| Quý 4/2025 | Riêng lẻ | Chưa kiểm toán/không ghi | [20260130 - EIB - BCTC rieng le Q4.2025.pdf](</workspace/bctc-ai/vietstock_bctc/EIB/2025/20260130 - EIB - BCTC rieng le Q4.2025.pdf>) | 39 | 29 |
| Quý 1/2025 | Công ty mẹ | Chưa kiểm toán/không ghi | [BCTC Công ty mẹ quý 1 năm 2025.pdf](</workspace/bctc-ai/vietstock_bctc/EIB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf>) | 39 | 29 |
| Quý 2/2025 | Công ty mẹ | Chưa kiểm toán/không ghi | [BCTC Công ty mẹ quý 2 năm 2025.pdf](</workspace/bctc-ai/vietstock_bctc/EIB/2025/BCTC Công ty mẹ quý 2 năm 2025.pdf>) | 39 | 29 |
| Quý 3/2025 | Công ty mẹ | Chưa kiểm toán/không ghi | [BCTC Công ty mẹ quý 3 năm 2025.pdf](</workspace/bctc-ai/vietstock_bctc/EIB/2025/BCTC Công ty mẹ quý 3 năm 2025.pdf>) | 39 | 29 |
| Quý 1/2025 | Hợp nhất | Chưa kiểm toán/không ghi | [BCTC Hợp nhất quý 1 năm 2025.pdf](</workspace/bctc-ai/vietstock_bctc/EIB/2025/BCTC Hợp nhất quý 1 năm 2025.pdf>) | 40 | 29 |
| Quý 2/2025 | Hợp nhất | Chưa kiểm toán/không ghi | [BCTC Hợp nhất quý 2 năm 2025.pdf](</workspace/bctc-ai/vietstock_bctc/EIB/2025/BCTC Hợp nhất quý 2 năm 2025.pdf>) | 40 | 29 |
| Quý 3/2025 | Hợp nhất | Chưa kiểm toán/không ghi | [BCTC Hợp nhất quý 3 năm 2025.pdf](</workspace/bctc-ai/vietstock_bctc/EIB/2025/BCTC Hợp nhất quý 3 năm 2025.pdf>) | 40 | 29 |
| Quý 1/2026 | Công ty mẹ | Chưa kiểm toán/không ghi | [BCTC Công ty mẹ quý 1 năm 2026.pdf](</workspace/bctc-ai/vietstock_bctc/EIB/2026/BCTC Công ty mẹ quý 1 năm 2026.pdf>) | 39 | 29 |
| Quý 2/2026 | Công ty mẹ | Chưa kiểm toán/không ghi | [BCTC Công ty mẹ quý 2 năm 2026.pdf](</workspace/bctc-ai/vietstock_bctc/EIB/2026/BCTC Công ty mẹ quý 2 năm 2026.pdf>) | 40 | 30 |
| Quý 1/2026 | Hợp nhất | Chưa kiểm toán/không ghi | [BCTC Hợp nhất quý 1 năm 2026.pdf](</workspace/bctc-ai/vietstock_bctc/EIB/2026/BCTC Hợp nhất quý 1 năm 2026.pdf>) | 40 | 29 |
| Quý 2/2026 | Hợp nhất | Chưa kiểm toán/không ghi | [BCTC Hợp nhất quý 2 năm 2026.pdf](</workspace/bctc-ai/vietstock_bctc/EIB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf>) | 41 | 30 |

Các ô của dòng này được PDF trình bày bằng dấu gạch. Dấu gạch là quan sát
nguồn hợp lệ, nhưng quyền sở hữu schema vẫn thuộc Family 33; Family 35 chỉ dùng
dòng làm kiểm soát số tổng. Regression riêng khóa việc không phát hành RNID
6028 từ Family 35.

### Dòng gộp không thể tách thành hai ID

| Ngân hàng | Kỳ | Báo cáo | Kiểm tra | File PDF | Tổng trang | Trang | Khoản mục | Khoản mục cha | Schema gần nhất | Kết luận |
|---|---|---|---|---|---:|---:|---|---|---|---|
| SHB | Năm 2025 | Hợp nhất | Kiểm toán | [BCTC Hợp nhất Kiểm toán năm 2025.pdf](</workspace/bctc-ai/vietstock_bctc/SHB/2025/BCTC Hợp nhất Kiểm toán năm 2025.pdf>) | 68 | 50 | `- Từ chứng khoán vốn` — 1.998 triệu đồng / dấu gạch | Cổ tức nhận được trong năm | 1200 và 1201 | **NHIỀU ID CÓ THỂ PHÙ HỢP** — PDF gộp chứng khoán vốn kinh doanh và đầu tư, không có bằng chứng để chia 1.998 cho hai ID. Tổng/cổ tức trực tiếp vẫn map được; dòng gộp giữ SOURCE_ONLY. |

### Nhãn cấu trúc không có giá trị

| Ngân hàng | Kỳ | Báo cáo | Kiểm tra | File PDF | Tổng trang | Trang | Khoản mục | Kết luận |
|---|---|---|---|---|---:|---:|---|---|
| BAB | Năm 2025 | Riêng lẻ | Kiểm toán | [BCTC Rieng le 2025_Kiem toan.pdf](</workspace/bctc-ai/vietstock_bctc/BAB/2025/BCTC Rieng le 2025_Kiem toan.pdf>) | 50 | 36 | `Thu nhập góp vốn, mua cổ phần` | Nhãn nhóm không có ô tiền; các dòng con và tổng đã map. Không phát hành một mapping trùng chỉ từ nhãn. |

### Năm dòng ngoài family

Các dòng dưới đây là khoản mục `Chi phí hoạt động` trên báo cáo kết quả kinh
doanh, không phải thu nhập góp vốn/mua cổ phần. Chúng được giữ SOURCE_ONLY với
phân loại **NGHI LÀ THUỘC FAMILY KHÁC**, không biến thành UNRESOLVED và không
map vào 1198–1204.

| Ngân hàng | Kỳ | Báo cáo | Kiểm tra | File PDF | Tổng trang | Trang | Khoản mục |
|---|---|---|---|---|---:|---:|---|
| KLB | Quý 3/2025 | Hợp nhất | Chưa kiểm toán/không ghi | [BAO CAO TAI CHINH QUY 3.2025 HOP NHAT.pdf](</workspace/bctc-ai/vietstock_bctc/KLB/2025/BAO CAO TAI CHINH QUY 3.2025 HOP NHAT.pdf>) | 35 | 5 | `Chi phí hoạt động` |
| KLB | Quý 3/2025 | Riêng lẻ | Chưa kiểm toán/không ghi | [BAO CAO TAI CHINH QUY 3.2025 RIENG.pdf](</workspace/bctc-ai/vietstock_bctc/KLB/2025/BAO CAO TAI CHINH QUY 3.2025 RIENG.pdf>) | 36 | 5 | `Chi phí hoạt động` |
| NVB | Năm 2025 | Công ty mẹ | Kiểm toán | [BCTC Công ty mẹ Kiểm toán năm 2025.pdf](</workspace/bctc-ai/vietstock_bctc/NVB/2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf>) | 57 | 13 | `VIII. Chi phí hoạt động` |
| TPB | Quý 1/2025 | Công ty mẹ | Chưa kiểm toán/không ghi | [BCTC Công ty mẹ quý 1 năm 2025.pdf](</workspace/bctc-ai/vietstock_bctc/TPB/2025/BCTC Công ty mẹ quý 1 năm 2025.pdf>) | 54 | 10 | `Chi phí hoạt động` |
| VBB | Quý 2/2025 | Hợp nhất | Chưa kiểm toán/không ghi | [2_vbb_2025_8_1_afc1d54_vi_baocaotaichinh_hopnhat_q2_2025.pdf](</workspace/bctc-ai/vietstock_bctc/VBB/2025/2_vbb_2025_8_1_afc1d54_vi_baocaotaichinh_hopnhat_q2_2025.pdf>) | 25 | 4 | `Chi phí hoạt động` |

## NOT_OBSERVED — không phải lỗi

52 PDF dưới đây đã được kiểm tra đúng phạm vi toàn báo cáo và không có khoản
mục Family 35 mang giá trị nguồn. Vì vậy `NOT_OBSERVED` là kết luận vắng mặt,
không phải lỗi mapping, thiếu schema hay OCR.

- **BVB (1):** `2025/VI_BaoCaoTaiChinhHopNhat_Kiemtoan_2025.pdf` (81 trang).
- **MSB (16):** `2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf` (72);
  `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` (73); `BCTC Công ty mẹ
  quý 1 năm 2025.pdf` (58); `quý 2` (58); `quý 3` (58); `quý 4` (56); `BCTC
  Hợp nhất Kiểm toán năm 2025.pdf` (76); `BCTC Hợp nhất Soát xét 6 tháng đầu
  năm 2025.pdf` (76); `BCTC Hợp nhất quý 1 năm 2025.pdf` (60); `quý 2` (60);
  `quý 3` (60); `MSB 20260130 - MSB - Bao cao tai chinh Hop nhat Quy 4
  2025.pdf` (59); `2026/BCTC Công ty mẹ quý 1 năm 2026.pdf` (60); `quý 2`
  (54); `BCTC Hợp nhất quý 1 năm 2026.pdf` (61); `quý 2` (57).
- **NAB (9):** `2025/BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` (83);
  `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` (83); `BCTC Hợp nhất quý
  1 năm 2025.pdf` (42); `NAB NAMABANK_2025_Q2_BCTC HN.pdf` (44); `NAB
  NAMABANK_2025_Q2_BCTC RL.pdf` (44); `2026/BCTC Công ty mẹ quý 1 năm
  2026.pdf` (42); `quý 2` (42); `BCTC Hợp nhất quý 1 năm 2026.pdf` (42);
  `quý 2` (42).
- **NVB (11):** `2025/6_nvb_2026_2_3_925648e_vi_baocaotaichinh_q1_2025_riengle_signed.pdf`
  (56); `BCTC Công ty mẹ quý 1 năm 2025.pdf` (52); `quý 3` (53); `BCTC Hợp
  nhất quý 1 năm 2025.pdf` (51); `quý 3` (54); `quý 4` (55);
  `NVB VI_BaoCaoTaiChinh_Q2_2025_hopnhat.pdf` (54);
  `VI_BaoCaoTaiChinh_Q2_2025_riengle.pdf` (52);
  `2026/4_nvb_2026_5_4_fbaa039_vi_baocaotaichinh_riengle_q1_2026_signed.pdf`
  (53); `BCTC - HOP NHAT - TIENG VIET - Q1.2026.pdf` (54); `Q2.2026.pdf`
  (53).
- **OCB (1):** `2025/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf` (102).
- **TPB (2):** `2025/BCTC Công ty mẹ Kiểm toán năm 2025.pdf` (93); `BCTC
  Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf` (91).
- **VBB (12):** `2025/2_vbb_2026_3_23_b2c1e44_vi_baocaotaichinh_kiemtoan_riengle_2025.pdf`
  (83); `3_vbb_2025_8_6_8bb1ede_vi_baocaotaichinh_riengle_bannien_2025.pdf`
  (81); `3_vbb_2025_8_6_d00b2c1_vi_baocaotaichinh_hopnhat_bannien_2025.pdf`
  (82); `3_vbb_2026_2_2_a18dc42_vi_baocaotaichinh_riengle_q4_2025.pdf` (40);
  `3_vbb_2026_3_23_3110a7d_vi_baocaotaichinh_kiemtoan_hopnhat_2025.pdf`
  (83); `92-BCTC-hopnhat-Q3-VIE.pdf` (41); `92-BCTC-riengle-Q3-VIE(1).pdf`
  (40); `BCTC Hợp nhất quý 4 năm 2025.pdf` (40);
  `2026/28-BCTC-Q1_2026-hopnhat-V.pdf` (45);
  `3_vbb_2026_5_2_fa0b162_vi_baocaotaichinh_riengle_q1_2026.pdf` (43);
  `BCTC Công ty mẹ quý 2 năm 2026.pdf` (46); `BCTC Hợp nhất quý 2 năm
  2026.pdf` (47).

## Ví dụ đã giải quyết được

- BAB năm 2025, hợp nhất và riêng lẻ, trang 36: tổng 1198 là
  `53.838 / 12.638`; 1201 là `42.706 / 0`; 1202 là `11.132 / 12.638`.
- SGB riêng lẻ kiểm toán năm 2025, trang 42: hai dòng dài hạn được cộng đúng
  vào 1202 là `9.887 / 2.902`; bản hợp nhất trang 43 cho `3.766 / 0`.
- STB riêng lẻ kiểm toán năm 2025, trang 68: công ty con và đầu tư dài hạn
  được cộng vào 1202 là `18.932 / 303.435`.
- TPB hợp nhất kiểm toán năm 2025, trang 70: chênh lệch đánh giá lại khoản đầu
  tư map vào 1204 là `127.798 / 0`.
- VAB riêng lẻ kiểm toán năm 2025, trang 45: số VND
  `8.303.955.000,00` được giữ đúng bản chất VND và đúng chuỗi nguồn.

## Kiểm tra chéo và artifact

- Tổng trạng thái: `217 + 52 + 2 = 271`; không có trial thiếu hoặc trùng.
- 639 mapping phân bổ đúng `211 + 129 + 51 + 63 + 110 + 11 + 64 = 639`.
- Ledger UNRESOLVED có đúng 2 PDF duy nhất; 19 SOURCE_ONLY chưa phát hành
  mapping là duy nhất theo PDF/trang/bảng/hàng.
- Hợp đồng quan sát nguồn full271 kiểm 1.278 occurrence mapping / 2.556 ô,
  gồm 24 mapping partial và 24 ô trắng; số vi phạm bằng 0.
- Hồi quy old140 dùng `STRICT_RELEASE`: 71 bản ghi so sánh lịch sử hợp lệ,
  không có regression không giải thích; hợp đồng quan sát nguồn cũng có 0 lỗi.
- Shared evaluator và generic runner được dùng read-only. Adapter không sửa
  shared engine, flat evaluator, store hay provider.

| Artifact | SHA-256 |
|---|---|
| `/dev/shm/f35-full271-specialized-final-v2.json` | `f2e857cea5755f3e4a515fba9b41e95c27dfed19a4fec871935d6bbfe79d70ef` |
| `/dev/shm/f35-full271-specialized-final-v2.audit.json` | `ba50f769c4ee42d42c6c7f36770b3137e34324b2e4805ead2ef11c62e430ea39` |
| `/dev/shm/f35-old140-specialized-final-v3.json` | `a02aac5498b653625889de43534462588f46249085c3d3abd21104b00b8720b1` |
| `/dev/shm/f35-old140-specialized-final-v3.audit.json` | `f901fa506da9bc0a11e188528f9d53484ad9632f968dc5def01abac7c0b89c0b` |

Các file family-local tại checkpoint:

| File | SHA-256 |
|---|---|
| `config/families/tm-capital-contribution-dividend-income-topology-v1.json` | `b0f7393fd079788695996f7f4cb3f9d32910e3ac29720675b8ca34886f9c4fd8` |
| `config/families/tm-capital-contribution-dividend-income-evaluation-v1.json` | `131e77b22b6d0698209ea88dc09b4b8f675d3e543b975e5608a5783784e90e0c` |
| `config/families/tm-capital-contribution-dividend-income-schema-binding-v1.json` | `1bc808c7ddd6d2db5409e86a4a443a0dfcb661dcabb6a8712f066eb348782d85` |
| `config/families/tm-capital-contribution-dividend-income-adapter-v1.json` | `fe235f80761861fb9c4db1de12839204d85c17b899e48439bc43894075fa6a65` |
| `data/registered/gemini_json_capital_contribution_dividend_income_source_repairs_v1.json` | `51514b48549b73f0410f9d3dda683bffc1f29570c112b80c675dc38de0875d5f` |
| `src/bctc_ai/evaluation/gemini_json_capital_contribution_dividend_income_family_v1.py` | `c49c11003fecd870807d023ebb4902fb6832f3123a0432e3e2fcc7e8cdd73e0c` |
| `scripts/experiments/run_gemini_json_capital_contribution_dividend_income_accounting_family_v1.py` | `ad78911d2b8eb453a24cb37e72253161a44c04070b4798d6caf263242852f2f7` |
| `tests/unit/test_gemini_json_capital_contribution_dividend_income_family_v1.py` | `0abe813c0d1ba084eef61457be481833f210528719b293a049eb39da82f2500d` |
| `tests/unit/test_gemini_json_capital_contribution_dividend_income_adapter_v1.py` | `248d17f9c7ca034e236acf4bae4d83d1c2c1f159704504dc92656fabf76c9425` |
| `tests/unit/test_run_gemini_json_capital_contribution_dividend_income_accounting_family_v1.py` | `befca242ea4f17dee1ca08c99ca1f4102990fa267485e58f0ca8d1dc8f178113` |

Shared evaluator/runner được giữ nguyên ở
`bb3190765919666c559de8c0f6d79003245da94c7b18708a4bf2676059d9afa2`
và `d9b1fa9f4c05a737bd999a98e58c16936a5431d662171c20b096a6e389a856c5`.

Full271 sweep ID là
`gjfafsv1:sweep:89c4c20d7b696dea3ff33e2fdf504790814059afab6fbc082c37821f9007d08d`;
audit ID là
`gjccdifav1:audit:e0f6a8c3e053ee7a302539e499ed0df85ce4ff435ca11f1661a160bcfe99e198`.
Các mã kỹ thuật chỉ đặt ở cuối để truy vết, không dùng làm cách nhận diện nội
dung chính.
