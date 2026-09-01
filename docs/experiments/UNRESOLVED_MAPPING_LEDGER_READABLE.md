# Các PDF và khoản mục chưa map — bản dễ đọc

Cập nhật: 2026-09-01. Đây là bản hiện hành dành cho người kiểm tra PDF. Bản
đầy đủ có lịch sử kỹ thuật nằm tại
[`UNRESOLVED_MAPPING_LEDGER.md`](UNRESOLVED_MAPPING_LEDGER.md).

## Cách đọc

- **NOT_OBSERVED**: đã kiểm tra đúng phạm vi nhưng family không xuất hiện trong
  PDF. Đây không phải lỗi và không được liệt kê như một khoản mục chưa map.
- **UNRESOLVED**: nhìn thấy nội dung thật trong PDF nhưng chưa thể xác định chắc
  mapping, kỳ/cột, quan hệ cha–con hoặc giá trị nguồn.
- **SOURCE_ONLY**: nhìn thấy trong PDF nhưng chưa map ở family đang xét. Nó có
  thể là parent, subtotal, control, thuộc family khác hoặc là ứng viên cần schema
  review; không tự động làm cả PDF thành `UNRESOLVED`.

<a id="unresolved"></a>

## 15 PDF UNRESOLVED hiện hành

### 1. Vốn và các quỹ — 3 PDF

#### BID — BCTC hợp nhất kiểm toán năm 2025

- **File:** `BCTC Hợp nhất Kiểm toán năm 2025.pdf`
- **Trang PDF:** 53
- **Khoản mục:** `Quỹ đầu tư phát triển`.
- **Cha/con liên quan:** cha `Vốn và các quỹ`; nằm cùng ma trận với vốn điều lệ,
  các quỹ khác và lợi nhuận chưa phân phối.
- **Schema gần nhất:** root 1128; các leaf 6013 `Quỹ dự trữ bổ sung vốn điều
  lệ`, 6014 `Quỹ dự phòng tài chính`, 6015 `Quỹ khác` đều khác bản chất.
- **Lý do:** chưa có leaf đồng nhất với `Quỹ đầu tư phát triển`; đồng thời tổng
  ngang và roll-forward dọc chưa khép thành một cấu trúc duy nhất. Không ép vào
  `Quỹ khác`.
- **Phân loại:** **CHƯA CÓ TRONG SCHEMA**; **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH CẤU TRÚC**.

#### BID — BCTC hợp nhất quý 1/2026, chưa kiểm toán

- **File:** `BCTC Hợp nhất quý 1 năm 2026.pdf`
- **Trang PDF:** 26
- **Khoản mục:** `Quỹ đầu tư phát triển`.
- **Cha/con liên quan:** cha `Vốn và các quỹ`; các hàng đầu kỳ, phát sinh và cuối kỳ.
- **Schema gần nhất:** root 1128; các ID 6013–6015 chỉ gần nghĩa.
- **Lý do:** thiếu leaf chính xác; căn hàng và các phép kiểm tra ma trận vốn còn
  mâu thuẫn, nên không thể chọn một mapping duy nhất.
- **Phân loại:** **CHƯA CÓ TRONG SCHEMA**; **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/QUAN HỆ**.

#### VIB — BCTC hợp nhất soát xét quý 1/2025

- **File:** `BCTC Hợp nhất Soát xét quý 1 năm 2025.pdf`
- **Trang PDF:** 50
- **Khoản mục:** `Quỹ đầu tư phát triển`.
- **Cha/con liên quan:** cha `Vốn và các quỹ`; cùng các hàng biến động vốn.
- **Schema gần nhất:** root 1128; các leaf 6013–6015 không tương đương.
- **Lý do:** thành phần có số nhưng chưa có leaf đúng; căn hàng và tổng vốn chưa
  cho một nghiệm cấu trúc duy nhất.
- **Phân loại:** **CHƯA CÓ TRONG SCHEMA**; **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH**.

### 2. Thu nhập nhân viên — 6 PDF

#### MBB — BCTC công ty mẹ soát xét 6 tháng 2025

- **File:** `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2025.pdf`
- **Trang PDF:** 60
- **Khoản mục:** `Số lượng cán bộ, công nhân (người)`.
- **Cha/con liên quan:** cùng bảng với tổng thu nhập và thu nhập bình quân tháng.
- **Schema gần nhất:** 1261 `Số lượng nhân viên`.
- **Lý do:** nguồn không ghi “bình quân”; không thể chỉ dựa vào phép chia gần
  khớp để kết luận đó là headcount bình quân dùng làm mẫu số.
- **Phân loại:** **CÓ ID GẦN NGHĨA NHƯNG CHƯA RÕ BẢN CHẤT**.

#### MBB — BCTC hợp nhất soát xét 6 tháng 2025

- **File:** `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf`
- **Trang PDF:** 77
- **Khoản mục:** `Số lượng cán bộ, công nhân viên (người)`.
- **Cha/con liên quan:** cùng tổng thu nhập và thu nhập bình quân.
- **Schema gần nhất:** 1261 `Số lượng nhân viên`.
- **Lý do:** chưa xác định đây là số tại thời điểm hay số bình quân; bộ ba số
  người–thu nhập–bình quân chưa khép chắc cho cả kỳ.
- **Phân loại:** **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH**.

#### MBB — BCTC công ty mẹ soát xét 6 tháng 2026

- **File:** `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2026.pdf`
- **Trang PDF:** 63
- **Khoản mục:** `Số lượng cán bộ, công nhân viên (người)`.
- **Cha/con liên quan:** tổng thu nhập và thu nhập bình quân tháng.
- **Schema gần nhất:** 1261 `Số lượng nhân viên`.
- **Lý do:** nhãn không nói rõ loại số người theo kỳ; không suy bản chất từ phép chia.
- **Phân loại:** **CÓ ID GẦN NGHĨA NHƯNG CHƯA RÕ BẢN CHẤT**.

#### MBB — BCTC hợp nhất soát xét 6 tháng 2026

- **File:** `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2026.pdf`
- **Trang PDF:** 80
- **Khoản mục:** `Số lượng cán bộ, công nhân viên (người)`.
- **Cha/con liên quan:** tổng thu nhập và thu nhập bình quân tháng.
- **Schema gần nhất:** 1261 `Số lượng nhân viên`.
- **Lý do:** thiếu qualifier “bình quân”; ratio metric chưa được chứng minh hoàn
  chỉnh cho hai kỳ.
- **Phân loại:** **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH**.

#### VCB — BCTC công ty mẹ kiểm toán năm 2025

- **File:** `BCTC Công ty mẹ Kiểm toán năm 2025.pdf`
- **Trang PDF:** 59
- **Khoản mục:** `Tổng số cán bộ, công nhân viên tại ngày 31 tháng 12 (người)`.
- **Cha/con liên quan:** cha `Thu nhập của cán bộ, công nhân viên`; liên quan
  `Tổng quỹ lương và phụ cấp`, `Thu nhập bình quân tháng/người`.
- **Schema gần nhất:** 1261 số lượng nhân viên; 1263 quỹ lương; 1268 thu nhập bình quân.
- **Lý do:** số người tại ngày cuối kỳ không chắc đồng nhất với denominator bình
  quân dùng để tính thu nhập tháng.
- **Phân loại:** **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**.

#### VCB — BCTC hợp nhất kiểm toán năm 2025

- **File:** `BCTC Hợp nhất Kiểm toán năm 2025.pdf`
- **Trang PDF:** 64
- **Khoản mục:** `Tổng số cán bộ, công nhân viên tại ngày 31 tháng 12 (người)`.
- **Cha/con liên quan:** cùng quỹ lương và thu nhập bình quân tháng/người.
- **Schema gần nhất:** 1261, 1263 và 1268.
- **Lý do:** chưa có căn cứ cho phép dùng trực tiếp số cuối kỳ làm headcount của
  phép tính bình quân.
- **Phân loại:** **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH**.

### 3. Thu nhập lãi — 4 PDF

#### BID — BCTC hợp nhất soát xét 6 tháng 2025

- **File:** `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2025.pdf`
- **Trang PDF:** 44
- **Khoản mục:** cha `Thu lãi từ kinh doanh, đầu tư chứng khoán Nợ` =
  4.973.626; các con `chứng khoán kinh doanh` = 126.852 và `chứng khoán đầu
  tư` = 4.846.773.
- **Schema gần nhất:** 1146 `Thu lãi từ kinh doanh, đầu tư chứng khoán`.
- **Lý do:** hai child cộng 4.973.625, lệch 1 so với parent. Schema có ID đúng
  nghĩa; vướng mắc là phương trình nguồn, không phải thiếu schema.
- **Phân loại:** **LỆCH PHƯƠNG TRÌNH NGUỒN**; **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH**.

#### MBB — BCTC hợp nhất quý 2/2025, chưa kiểm toán

- **File:** `BCTC Hợp nhất quý 2 năm 2025.pdf`
- **Trang PDF:** 46
- **Khoản mục:** group `Thu nhập lãi và các khoản thu nhập tương tự`; các child
  tiền gửi, cho vay, chứng khoán, bảo lãnh, mua nợ và khác; subtotal không nhãn.
- **Schema gần nhất:** 1143 `Thu nhập lãi và các khoản thu nhập tương tự`.
- **Lý do:** root được biểu diễn bằng group trống và subtotal không nhãn trong
  bảng còn chứa family chi phí lãi; chưa đủ authority để bind root.
- **Phân loại:** **KHÔNG XÁC ĐỊNH ĐƯỢC QUAN HỆ CHA/CON**.

#### VPB — BCTC công ty mẹ soát xét 6 tháng 2026

- **File:** `BCTC Công ty mẹ Soát xét 6 tháng đầu năm 2026.pdf`
- **Trang PDF:** 61
- **Khoản mục:** `Thu nhập lãi tiền gửi và cho vay TCTD khác`.
- **Cha/con liên quan:** cha `Thu nhập lãi và các khoản thu nhập tương tự`.
- **Schema gần nhất:** 1144 chỉ là lãi tiền gửi; 6075 là lãi cho vay khách hàng
  và TCTD khác. Mỗi ID chỉ phù hợp một phần.
- **Lý do:** một số nguồn gộp hai bản chất, không có căn cứ tách hoặc dồn toàn
  bộ vào một ID.
- **Phân loại:** **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**; **CẦN ĐÁNH GIÁ CÓ TẠO ID MỚI HAY KHÔNG**.

#### VPB — BCTC hợp nhất soát xét 6 tháng 2026

- **File:** `BCTC Hợp nhất Soát xét 6 tháng đầu năm 2026.pdf`
- **Trang PDF:** 71
- **Khoản mục:** `Thu nhập lãi tiền gửi và cho vay TCTD khác`.
- **Cha/con liên quan:** cha `Thu nhập lãi và các khoản thu nhập tương tự`.
- **Schema gần nhất:** 1144 và 6075 đều chỉ phù hợp một phần.
- **Lý do:** dòng có tiền và tham gia đúng tổng nhưng schema chưa có concept gộp
  đồng nhất; không phân bổ suy diễn.
- **Phân loại:** **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT**.

### 4. Chi phí hoạt động — 2 PDF

#### HDB — BCTC công ty mẹ quý 1/2025, chưa kiểm toán

- **File:** `BCTC Công ty mẹ quý 1 năm 2025.pdf`
- **Trang PDF:** 43
- **Khoản mục:** `Chi về các hoạt động đoàn thể`; hiện kỳ 214, kỳ so sánh để trống.
- **Cha/con liên quan:** dưới `Chi phí cho hoạt động quản lý công vụ`.
- **Schema gần nhất:** 1216 `Chi về hoạt động đoàn thể của TCTD`.
- **Lý do:** ID đã đúng nhưng ô so sánh là blank; không có phương trình đủ mạnh
  để kết luận blank bằng 0.
- **Phân loại:** **KHÔNG XÁC ĐỊNH ĐƯỢC CỘT/KỲ/GIÁ TRỊ**.

#### VPB — BCTC riêng lẻ/công ty mẹ quý 1/2026, chưa kiểm toán

- **File:** `4-bctc-rieng-le-ban-tra-cuu.pdf`
- **Trang PDF:** 57
- **Khoản mục:** `Trích lập/(hoàn nhập) dự phòng rủi ro khác` và child về nợ
  phải thu khó đòi có token `494带有`; source-only thêm `Chi thuê tài sản`,
  `Chi phí công nghệ thông tin`, `Chi về thuế GTGT đầu vào không được khấu trừ`.
- **Cha/con liên quan:** nhóm dự phòng, `Chi về tài sản` và root chi phí hoạt động.
- **Schema gần nhất:** 1218/1220 gần nhóm dự phòng nhưng qualifier khác; 1212
  chỉ là parent chi tài sản; chưa có leaf chính xác cho thuê tài sản/CNTT/VAT.
- **Lý do:** token tiền có ký tự lạ nên không biết số thật; family root không
  khép. Ba child nhìn rõ là source-only/schema review, không phải lý do duy nhất
  làm PDF unresolved.
- **Phân loại:** **LỖI SOURCE/OCR**; **CHƯA CÓ TRONG SCHEMA** (ba child);
  **CHƯA ĐỦ THÔNG TIN ĐỂ XÁC ĐỊNH**.

## Kiểm tra trùng và tổng

- Khóa kiểm tra: `(family, ngân hàng, tên file, trang)`.
- Kết quả: **15/15 khóa duy nhất**, không có dòng trùng.
- Phân bố: Vốn và các quỹ 3; Thu nhập nhân viên 6; Thu nhập lãi 4; Chi phí hoạt động 2.

<a id="source-only"></a>

## SOURCE_ONLY hiện hành

Các số dưới đây là instance nguồn, không phải số concept schema duy nhất và
không cộng vào `UNRESOLVED`.

| Family | PDF READY có SOURCE_ONLY | Số lượng | Ví dụ và cách hiểu |
| --- | ---: | ---: | --- |
| Tài sản Có khác | 67 | 304 dòng | Parent/subtotal và child riêng; một phần cần schema review. |
| Nợ Chính phủ và NHNN | 31 | 45 dòng | Parent chương trình/tiền tệ; chủ yếu là control. |
| Vốn tài trợ/ủy thác | 4 | 12 dòng | Tên dự án/chương trình dưới aggregate. |
| Phát hành giấy tờ có giá | 54 | 336 dòng | Header kỳ hạn, subtotal, mệnh giá và điều chỉnh. |
| Các khoản phải trả khác | 77 | 412 dòng | Parent và chi tiết lãi theo công cụ. |
| Vốn và các quỹ | 91 | 147 cột | Component ngoài binding; một phần là schema gap thật. |
| Thu nhập lãi | 34 | 42 dòng | Root, child chứng khoán và dòng gộp TCTD. |
| Chi phí lãi | 32 | 32 dòng | Root/control hoặc tiền gửi–vay TCTD gộp. |
| Thu nhập/chi phí dịch vụ | 10 | 51 dòng | Nhãn `Trong đó` và dịch vụ gộp. |
| Kinh doanh vàng và ngoại hối | 61 | 61 dòng | Parent hoặc component để kiểm tra net. |
| Mua bán chứng khoán kinh doanh | 11 | 11 dòng | Component ngoài topology mục tiêu. |
| Mua bán chứng khoán đầu tư | 26 | 62 dòng | Parent/subtotal và component dự phòng. |
| Chứng khoán gộp | 4 | 4 dòng | Dòng thành phần; không tự tổng hợp net. |
| Thu nhập góp vốn/cổ tức | 36 | 36 dòng | Parent/subtotal hoặc cổ tức nguồn gộp. |
| Chi phí hoạt động | 108 | 284 dòng | `Trong đó`, thuê tài sản, CNTT, VAT và control. |
| Chi phí dự phòng tín dụng | 21 | 51 dòng | Component trích lập/hoàn nhập dùng kiểm tra tổng. |
| Chi phí thuế TNDN | 69 | 282 dòng | Reconciliation và điều chỉnh ngoài leaf lõi. |
| Tiền và tương đương tiền | 1 | 1 dòng | Owner/group không có số. |
| Nghĩa vụ ngân sách | 20 | 43 cột | Cột cấu trúc ngoài binding. |
| Tài sản bảo đảm khách hàng | 20 | 25 dòng | Owner/`Trong đó` dùng kiểm tra. |
| Tài sản ngân hàng cầm cố/thế chấp | 36 | 74 dòng | Parent và GTCG gộp ngoài binding. |
| Nợ tiềm ẩn và cam kết | 44 | 249 dòng | Parent, `Trong đó`, khoản khấu trừ và control. |
| Tỷ giá ngoại tệ | 64 | 323 loại tiền | Mã tiền hiếm/XAU ngoài danh sách family. |
| Tiền gửi và vay TCTD khác — nguồn vốn | 54 | 135 dòng | IFC, UPAS L/C, subgroup repo và parent. |
| Chứng khoán theo địa lý | 6 | 6 ô trống | Blank thật, không đổi thành dấu gạch hoặc 0. |
| Báo cáo bộ phận hợp nhất | 39 | 1.149 dòng + 132 cột | Axis/metric ngoài sáu metric lõi; 6.860 ô vẫn được lưu để kiểm tra tổng. |

### Khi nào SOURCE_ONLY là ứng viên schema?

- Chỉ đưa sang schema review khi nhãn có bản chất riêng, lặp lại hoặc có số độc
  lập và đã rà hết ID gần nghĩa.
- Parent, subtotal, `Trong đó`, cột trục, blank và component chỉ dùng kiểm tra
  không phải lý do tạo ID mới.
- Danh sách quyết định schema/source lịch sử gồm 205 source-row vẫn được giữ tại
  [ledger kỹ thuật](UNRESOLVED_MAPPING_LEDGER.md#canonical-open-source-rows).
