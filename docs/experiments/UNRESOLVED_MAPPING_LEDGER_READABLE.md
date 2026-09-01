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

## Đính chính các khoản mục vừa được người dùng xác nhận

Các dòng dưới đây **không phải “chưa có trong schema”**. Chúng đã được đối
chiếu toàn bộ schema và phân thành hai nhóm:

| Nội dung PDF | Kết luận schema | Trạng thái sau rà soát |
| --- | --- | --- |
| Dự phòng giảm giá chứng khoán kinh doanh | ID 612 | Đã bổ sung binding; 29 PDF chờ replay mapping chính thức. |
| Chứng khoán nợ/vốn — đã niêm yết/chưa niêm yết | ID 618/619/621/622 dưới nhánh 616 | 28 dòng trong 7 PDF chờ replay; nhánh 617/620 là nhãn cấu trúc khi không có ô số riêng. |
| Công ty cổ phần, công ty TNHH và doanh nghiệp khác | ID 775 | Alias chính xác đã bổ sung. |
| Hợp tác xã | ID 776 | Alias chính xác đã bổ sung; không còn giữ mơ hồ với nhãn gộp khác. |
| Cá nhân | ID 780 | Xác nhận `Hộ kinh doanh, cá nhân` bao hàm dòng `Cá nhân`. |
| Các đối tượng khác | ID 782 | Alias chính xác đã bổ sung. |
| Tiền gửi tiết kiệm không kỳ hạn + có kỳ hạn | Cộng vào ID 1063; child 1064/1065 | Đã map trong kết quả hiện hành; không phải unresolved. |
| Tiền gửi ký quỹ | ID 1066; child 1067/1068 | Đã map trong kết quả hiện hành; không phải unresolved. |
| Đầu kỳ/tăng giảm/cuối kỳ của TSCĐ và BĐS đầu tư | Các child dưới 869/883/5964 và các nhánh tương ứng | Đã lấy cột `Tổng cộng` để map; parent là nút cấu trúc, không tự tạo ô số giả. |
| Phát hành giấy tờ có giá | Root 1100 và các leaf 1101–1112 phù hợp | Mapping hiện hành đã có; dòng cùng ID ở bảng phụ được ghi là đối chiếu, không còn báo “chưa map”. |

Tổng phạm vi alias mới chờ replay là **29 dòng ID 612 trong 29 PDF**, **28 dòng
niêm yết trong 7 PDF**, và **31 dòng đối tượng doanh nghiệp trong 13 PDF**.
Chúng được tách khỏi 15 PDF `UNRESOLVED` dưới đây vì nguyên nhân không phải OCR,
thiếu schema hay thiếu quan hệ cha/con; đây là thay đổi chính sách mapping có
bằng chứng người dùng và schema hiện hữu.

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

## 205 khoản mục SOURCE_ONLY cần con người quyết định

Đây là các source-row có nhãn/giá trị hoặc vấn đề cấu trúc riêng cần quyết định.
Chúng được tách khỏi hàng nghìn parent, subtotal, cột trục và blank cơ học ở
bảng trên. Một PDF vẫn có thể `READY` vì phần mapping đã xác định là dùng được;
các dòng dưới đây chỉ nói rằng **khoản mục cụ thể này chưa được map**.

Mỗi dòng giữ tên PDF và trang để mở nguồn. Không có SHA, candidate ID hay tên
artifact trong bảng đọc nhanh. Với 76 dòng mang nhãn “rà lại schema hiện hành”,
kết luận thiếu ID là kết luận lịch sử và **chưa được phép coi là schema gap
hiện tại** cho đến khi replay schema sống.

| Phân loại dễ hiểu | Số khoản mục | Ý nghĩa |
| --- | ---: | --- |
| Cần rà lại schema hiện hành | 76 | Checkpoint cũ chưa thấy leaf phù hợp; phải đối chiếu schema sống trước khi tạo ID. |
| Chưa có trong schema tại checkpoint | 80 | Chưa tìm thấy leaf đồng nhất tại checkpoint; không ép vào ID gần nghĩa. |
| Có ID gần nghĩa nhưng khác bản chất | 17 | Trục/nhãn schema gần nhưng population hoặc ý nghĩa không đồng nhất. |
| Chưa đủ thông tin phạm vi/cấu trúc | 11 | Chưa xác định chắc scope, cột, kỳ hoặc quan hệ cha–con. |
| Cần sửa xử lý cấu trúc | 10 | Nguồn có thể dùng; parser/topology chung chưa xử lý đúng, không phải schema gap. |
| Lỗi hoặc mâu thuẫn nguồn | 6 | Số hoặc quan hệ nguồn mâu thuẫn; không sửa bằng suy đoán. |
| Không có giá trị nguồn | 5 | PDF không cung cấp giá trị đủ xác định; không tự điền 0. |
| **Tổng** | **205** | Mỗi dòng là một source-row/filing duy nhất. |

### Tài sản Có khác — 47 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p51 | “Phải thu bán tài sản tài chính” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 976 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p51 | “Dự phòng phí và bồi thường nghiệp vụ nhượng tái bảo hiểm” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 966-1023 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p52 | “Số dư đầu kỳ dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 966-1023 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p52 | “Trích lập dự phòng rủi ro trong kỳ” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 966-1023 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p52 | “Số dư cuối kỳ dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 966-1023 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p52 | “Dự phòng tài sản Có rủi ro tín dụng” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p52 | “Dự phòng cụ thể” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 966-1023 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p52 | “Dự phòng rủi ro phải thu khó đòi” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 966-1023 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p39 | “Phải thu từ Ngân sách Nhà nước” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 979 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p39 | “Phải thu từ hoạt động tài trợ thương mại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 966-1023 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p39 | “Phải thu hoa hồng bảo hiểm” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p39 | “Tài sản thuế TNDN hoãn lại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 966-1023 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p58 | “Các khoản tạm ứng và phải thu nội bộ” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 975 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p58 | “Phải thu Ngân sách Nhà nước” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 974 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p59 | “Tài sản thuế thu nhập doanh nghiệp hoãn lại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p59 | Pixel artifact xác nhận ô “Tài sản thay thế cho việc thực hiện nghĩa vụ của bên bảo đảm” là dấu gạch; detector thiếu bbox. Chờ generic dash-cell recovery, không còn bất định PDF. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN SỬA XỬ LÝ CẤU TRÚC; KHÔNG PHẢI SCHEMA GAP** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p60 | “Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p62 | “Phải thu liên quan đến tài trợ thương mại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p62 | Pixel artifact xác nhận ô “Các khoản phải thu miễn truy đòi theo bộ chứng từ” là dấu gạch; detector thiếu bbox. Chờ generic dash-cell recovery, không còn bất định PDF. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN SỬA XỬ LÝ CẤU TRÚC; KHÔNG PHẢI SCHEMA GAP** |
| MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p62 | “Các khoản tạm ứng và đặt cọc hợp đồng” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 975 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p62 | “Dự phòng phí và dự phòng bồi thường nghiệp vụ nhượng tái bảo hiểm” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p62 | “Lãi phải thu hoạt động tín dụng và phí phải thu” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 983 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p63 | Pixel artifact xác nhận ô “Lợi thế thương mại” là dấu gạch; detector thiếu bbox. Chờ generic dash-cell recovery, không còn bất định PDF. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN SỬA XỬ LÝ CẤU TRÚC; KHÔNG PHẢI SCHEMA GAP** |
| MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p63 | “Dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p55 | “Phải thu bán tài sản tài chính” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 976 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p55 | “Dự phòng phí và bồi thường nghiệp vụ nhượng tái bảo hiểm” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p55 | Pixel artifact xác nhận ô “Nợ đủ tiêu chuẩn” là dấu gạch; detector thiếu bbox. Chờ generic dash-cell recovery, không còn bất định PDF. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN SỬA XỬ LÝ CẤU TRÚC; KHÔNG PHẢI SCHEMA GAP** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p56 | Pixel artifact xác nhận ô “Tài sản có khác” là dấu gạch; detector thiếu bbox. Chờ generic dash-cell recovery, không còn bất định PDF. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN SỬA XỬ LÝ CẤU TRÚC; KHÔNG PHẢI SCHEMA GAP** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p56 | Pixel artifact xác nhận ô “Lợi thế thương mại” là dấu gạch; detector thiếu bbox. Chờ generic dash-cell recovery, không còn bất định PDF. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN SỬA XỬ LÝ CẤU TRÚC; KHÔNG PHẢI SCHEMA GAP** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p57 | “Dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p42 | “Các khoản tạm ứng và phải thu nội bộ” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 975 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p43 | “Phải thu từ thanh lý TSCĐ” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p44 | “Dự phòng rủi ro các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p50 | “Phải thu từ ngân sách Nhà nước về hỗ trợ lãi suất” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 979 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p51 | “Tài sản thuế thu nhập hoãn lại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p51 | “Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p50 | “Các khoản tạm ứng và phải thu nội bộ” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 975 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p50 | “Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| BID / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p49 | “Các khoản phải thu khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 981 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| BID / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p49 | “Tài sản thuế thu nhập doanh nghiệp hoãn lại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| BID / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p49 | “Dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| BID / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p49 | “Phải thu trong nghiệp vụ tài trợ thương mại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p44 | “Phải thu từ Ngân sách Nhà nước” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p44 | “Phải thu từ hoạt động tài trợ thương mại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p44 | “Phải thu hoa hồng bảo hiểm” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | 978 | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p44 | “Tài sản thuế TNDN hoãn lại” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p44 | “Các khoản dự phòng rủi ro cho các tài sản Có nội bảng khác” không có leaf tương đương hoặc gộp nhiều khái niệm; giữ nhãn/số nguồn, không ép khoản gần nghĩa. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |

### Phát hành giấy tờ có giá — 8 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p56 | Trục/hàng “Phát hành giấy tờ có giá theo kỳ hạn gốc / Dưới 12 tháng” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA ĐỦ THÔNG TIN PHẠM VI/CẤU TRÚC** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p56 | Trục/hàng “Từ trên 12 tháng đến 5 năm” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA ĐỦ THÔNG TIN PHẠM VI/CẤU TRÚC** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p56 | Trục/hàng “Từ trên 5 năm trở lên” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA ĐỦ THÔNG TIN PHẠM VI/CẤU TRÚC** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p62 | Trục/hàng “Dưới 12 tháng” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA ĐỦ THÔNG TIN PHẠM VI/CẤU TRÚC** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p62 | Trục/hàng “Từ 12 tháng đến dưới 5 năm” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA ĐỦ THÔNG TIN PHẠM VI/CẤU TRÚC** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p62 | Trục/hàng “Từ 5 năm trở lên” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA ĐỦ THÔNG TIN PHẠM VI/CẤU TRÚC** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p46 | Trục/hàng “Chi phí phát hành” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p54 | Trục/hàng “Trung, dài hạn bằng ngoại tệ” áp dụng toàn family, là contra hoặc gộp công cụ; PDF không cho phân bổ chắc chắn theo leaf. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |

### Vốn và các quỹ — 17 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p60 | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p60 | Hàng/cột vốn “Cổ phiếu quỹ” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| HDB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p33 | Hàng/cột vốn “Cổ phiếu quỹ” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| HDB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p33 | Hàng/cột vốn “Quỹ đầu tư xây dựng cơ bản” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VCB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p36 | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p43 | Hàng/cột vốn “Cổ phiếu quỹ” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p43 | Hàng/cột vốn “Chênh lệch đánh giá lại tài sản” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p43 | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| BID / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p27–28 | Đã mở trực tiếp BID p27–28: p27/trang in 24 là bảng thay đổi vốn xoay, hàng/cột và số nhìn rõ; p28 đã sang chi tiết vốn/cổ phiếu. Nguồn không mơ hồ; chờ primitive bảng xoay generic. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN SỬA XỬ LÝ CẤU TRÚC; KHÔNG PHẢI SCHEMA GAP** |
| VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p44–45 | Đã mở trực tiếp VIB p44–45: p44/trang in 42 là bảng thay đổi vốn xoay, hàng/cột và số nhìn rõ; p45 đã sang thuyết minh khác. Nguồn không mơ hồ; chờ primitive bảng xoay generic. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN SỬA XỬ LÝ CẤU TRÚC; KHÔNG PHẢI SCHEMA GAP** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p66 | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p48 | Hàng/cột vốn “Cổ phiếu quỹ” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p48 | Hàng/cột vốn “Vốn đầu tư xây dựng cơ bản” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p56 | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p55 | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| BID / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p53 | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p49 | Hàng/cột vốn “Quỹ đầu tư phát triển” nhìn rõ trong tổng vốn nhưng chưa có leaf số dư; giữ source-only tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |

### Chi phí quản lý chung — 18 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p65 | Khoản chi “Chi thuê tài sản” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p65 | Khoản chi “Chi phí công nghệ thông tin” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p65 | Khoản chi “Chi về thuế GTGT đầu vào không được khấu trừ” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p47 | Khoản chi “Chi khác về TSCĐ” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p70 | Khoản chi “Chi khác” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p70 | Khoản chi “Hoàn nhập chi phí dự phòng” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p74 | Khoản chi “Chi khác về tài sản” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p72 | Khoản chi “Chi thuê tài sản” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p72 | Khoản chi “Chi phí công nghệ thông tin” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p72 | Khoản chi “Chi về thuế GTGT đầu vào không được khấu trừ” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p51 | Khoản chi “Chi thuê tài sản” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p51 | Khoản chi “Chi về bảo dưỡng và sửa chữa tài sản” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p51 | Khoản chi “Chi khác về tài sản” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p51 | Khoản chi “Chi phí quảng cáo, tiếp thị, khuyến mại” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p51 | Khoản chi “Chi phí hội nghị, lễ tân, khánh tiết” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p51 | Khoản chi “Chi phí điện, nước, vệ sinh cơ quan” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p60 | Khoản chi “Chi khác” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p60 | Khoản chi “Chi phí dự phòng” nhìn rõ trong parent/tổng nhưng chưa có leaf chính xác; không thu hẹp hay cộng lại aggregate. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |

### Chi phí thuế TNDN — 8 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p48 | “Điều chỉnh khác” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p71 | “Các khoản điều chỉnh làm tăng/(giảm) thu nhập chịu thuế khác” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p71 | “Chi phí thuế thu nhập doanh nghiệp hoãn lại phát sinh từ hoàn / nhập tài sản thuế thu nhập hoãn lại (Thuyết minh 14.2)” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p71 | “Thu nhập thuế thu nhập doanh nghiệp hoãn lại phát sinh từ các / khoản chênh lệch tạm thời được khấu trừ (Thuyết minh 14.2)” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p76 | “Thuế TNDN do thoái vốn tại công ty con” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p64 | “Các điều chỉnh khác” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p60 | “Điều chính khác” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p53 | “Điều chỉnh khác” là điều chỉnh/component thuế rộng hoặc riêng theo nguồn; chưa có leaf chính xác, blank giữ blank. | 5733 | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |

### Tài sản/GTCG thế chấp, cầm cố, chiết khấu — 3 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p67 | Parent “Giấy tờ có giá đưa đi thế chấp, cầm cố” bằng hai con nhưng tổng in cộng cả parent và con; nguồn mâu thuẫn, không double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **LỖI/CONFLICT NGUỒN** |
| VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p49 | “Giấy tờ có giá đưa đi thế chấp, cầm cố” không tách loại chứng khoán; không ép phân bổ. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p49 | “Giấy tờ có giá đưa đi chiết khấu, tái chiết khấu” không tách loại chứng khoán; không ép phân bổ. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |

### Nghĩa vụ nợ tiềm ẩn và cam kết — 26 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| ACB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p26 | “Thư tín dụng trả ngay” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| ACB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p26 | “Thư tín dụng trả chậm” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| ACB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p26 | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm L/C; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent L/C. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| ACB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p26 | “Bảo lãnh khác” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| ACB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p26 | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm bảo lãnh; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent bảo lãnh. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p68 | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm L/C; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent L/C. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p68 | “Cam kết bảo lãnh khác” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p68 | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm bảo lãnh; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent bảo lãnh. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p68 | “Cam kết hoán đổi lãi suất tiền tệ chéo - nhận” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p68 | “Cam kết hoán đổi lãi suất tiền tệ chéo - trả” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p68 | “Cam kết hoán đổi lãi suất một đồng tiền” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p68 | “Cam kết khác” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p68 | “Trong đó: hạn mức tín dụng chưa sử dụng có thể / hủy ngang” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN RÀ LẠI SCHEMA HIỆN HÀNH** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p75 | “Cam kết trong nghiệp vụ L/C trả ngay” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p75 | “Cam kết trong nghiệp vụ L/C trả chậm” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p75 | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm L/C; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent L/C. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p75 | “Bảo lãnh khác” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p75 | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm bảo lãnh; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent bảo lãnh. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p75 | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm L/C; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent L/C. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p75 | “Cam kết bảo lãnh khác” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p75 | “Trừ: Tiền ký quỹ” là khoản khấu trừ nằm trong nhóm bảo lãnh; schema không có leaf kiểm soát tương đương. Giữ source-only để không trừ/cộng lặp parent bảo lãnh. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p75 | “Cam kết hoán đổi lãi suất tiền tệ chéo - nhận” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p75 | “Cam kết hoán đổi lãi suất tiền tệ chéo - trả” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p75 | “Cam kết hoán đổi lãi suất một đồng tiền” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p75 | “Cam kết khác” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p75 | “Trong đó: hạn mức tín dụng chưa sử dụng có thể hủy ngang” là leaf/khấu trừ/Trong đó chưa có leaf TM; giữ source-only để không cộng lặp parent. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |

### Công cụ tài chính — giá trị hợp lý — 5 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p86 | PDF ghi giá trị hợp lý “(*) Giá trị hợp lý của các tài sản tài chính này không thể xác định được / giá trị hợp lý của các công cụ tài chính” bằng (*) hoặc không ước tính tin cậy; không đổi thành 0 hay dùng giá trị ghi sổ. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **KHÔNG CÓ GIÁ TRỊ NGUỒN** |
| VCB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p45 | PDF ghi giá trị hợp lý “(*) Do không đủ thông tin để sử dụng các kỹ thuật định giá / đáng tin cậy và do đó, không được thuyết minh” bằng (*) hoặc không ước tính tin cậy; không đổi thành 0 hay dùng giá trị ghi sổ. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **KHÔNG CÓ GIÁ TRỊ NGUỒN** |
| CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p51 | PDF ghi giá trị hợp lý “(*) Ngân hàng chưa đánh giá giá trị hợp lý / chưa có hướng dẫn cụ thể về việc xác định giá trị hợp lý” bằng (*) hoặc không ước tính tin cậy; không đổi thành 0 hay dùng giá trị ghi sổ. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **KHÔNG CÓ GIÁ TRỊ NGUỒN** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p94 | PDF ghi giá trị hợp lý “(*) Ngân hàng chưa xác định giá trị của khoản mục này / chưa có hướng dẫn về xác định giá trị hợp lý” bằng (*) hoặc không ước tính tin cậy; không đổi thành 0 hay dùng giá trị ghi sổ. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **KHÔNG CÓ GIÁ TRỊ NGUỒN** |
| VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p74 | PDF ghi giá trị hợp lý “(*) Do không đủ thông tin để sử dụng các kỹ thuật định giá / giá trị hợp lý không được ước tính một cách đáng tin cậy / không được thuyết minh” bằng (*) hoặc không ước tính tin cậy; không đổi thành 0 hay dùng giá trị ghi sổ. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **KHÔNG CÓ GIÁ TRỊ NGUỒN** |

### Rủi ro tiền tệ — 10 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p80 | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| HDB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p39 | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p60 | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p84 | Trục AUD có năm ô nguồn đã pixel-review (Tổng tài sản, Tổng nợ phải trả, trạng thái nội bảng, ngoại bảng và tổng nội/ngoại bảng), nhưng schema lõi chưa có trục AUD tương đương; giữ source-only, không gộp vào ngoại tệ khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p84 | Trục CAD có năm ô nguồn đã pixel-review (Tổng tài sản, Tổng nợ phải trả, trạng thái nội bảng, ngoại bảng và tổng nội/ngoại bảng), nhưng schema lõi chưa có trục CAD tương đương; giữ source-only, không gộp vào ngoại tệ khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p84 | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p84 | Trục JPY có năm ô nguồn đã pixel-review (Tổng tài sản, Tổng nợ phải trả, trạng thái nội bảng, ngoại bảng và tổng nội/ngoại bảng), nhưng schema lõi chưa có trục JPY tương đương; giữ source-only, không gộp vào ngoại tệ khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p88 | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p63 | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p71 | Trục “Vàng” nhìn rõ nhưng schema chưa có nhánh vàng/ngoại tệ tương đương; không gộp vào ngoại tệ khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |

### Rủi ro thanh khoản — 4 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p82 | Ba ô tại “1–3 tháng” đã pixel-review nhưng phép trừ lệch 6.000 triệu đồng so với số in; giữ source, không backsolve. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **LỖI/CONFLICT NGUỒN** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p82 | Ba ô tại “1–5 năm” đã pixel-review nhưng phép trừ lệch 275.500 triệu đồng so với số in; giữ source, không backsolve. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **LỖI/CONFLICT NGUỒN** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p82 | Ba ô tại “3–12 tháng” đã pixel-review nhưng phép trừ lệch 6.001 triệu đồng so với số in; giữ source, không backsolve. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **LỖI/CONFLICT NGUỒN** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p82 | Ba ô tại “Tổng tài sản / Tổng nợ phải trả / Mức chếnh thanh khoản ròng” đã pixel-review nhưng phép trừ lệch 275.499 triệu đồng so với số in; giữ source, không backsolve. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **LỖI/CONFLICT NGUỒN** |

### Tỷ giá ngoại tệ — 34 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p90 | Mã “CNY” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p90 | Mã “DKK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p90 | Mã “NZD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Q1 2026 / BCTC hợp nhất / không kiểm toán | `3-bctc-hop-nhat-ban-tra-cuu.pdf` | p90 | Mã “XAU” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p61 | Mã “NZD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p61 | Mã “NOK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p61 | Mã “DKK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p61 | Mã “HKD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p61 | Mã “CNY” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p61 | Mã “KRW” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p61 | Mã “LAK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p71 | Mã “DKK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p71 | Mã “HKD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p71 | Mã “NOK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VIB / Q2 2026 / BCTC hợp nhất / không kiểm toán | `BCTC Hợp nhất quý 2 năm 2026.pdf` | p71 | Mã “XAU” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p98 | Mã “CNY” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p98 | Mã “DKK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p98 | Mã “NZD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p98 | Mã “XAU” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p69 | Mã “CNY” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p69 | Mã “HKD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p69 | Mã “KRW” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p69 | Mã “NZD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p85 | Mã “NZD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p85 | Mã “NOK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p85 | Mã “DKK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p85 | Mã “HKD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p85 | Mã “CNY” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p85 | Mã “KRW” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p85 | Mã “LAK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p77 | Mã “DKK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p77 | Mã “HKD” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p77 | Mã “NOK” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p77 | Mã “XAU” và tỷ giá nhìn rõ nhưng schema chưa có leaf; giữ source-only, không ép vào mã khác. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |

### Tiền gửi khách hàng — 2 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| BID / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p51 | Dòng “Công ty cổ phần” gộp nhiều loại khách hàng pháp lý; không có dữ liệu phân bổ theo leaf. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA ĐỦ THÔNG TIN PHẠM VI/CẤU TRÚC** |
| BID / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p51 | Dòng “Doanh nghiệp tư nhân, cá nhân” gộp nhiều loại khách hàng pháp lý; không có dữ liệu phân bổ theo leaf. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA ĐỦ THÔNG TIN PHẠM VI/CẤU TRÚC** |

### Thu nhập/chi phí dịch vụ — 2 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p58 | Dòng “Thu từ dịch vụ tư vấn, ủy thác và đại lý” gộp tư vấn với ủy thác/đại lý; không có căn cứ tách dù tổng khép. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA ĐỦ THÔNG TIN PHẠM VI/CẤU TRÚC** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p58 | Dòng “Chi về dịch vụ tư vấn, ủy thác và đại lý” gộp tư vấn với ủy thác/đại lý; không có căn cứ tách dù tổng khép. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA ĐỦ THÔNG TIN PHẠM VI/CẤU TRÚC** |

### Thu nhập góp vốn/cổ tức — 1 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p59 | Dòng “Từ chứng khoán vốn” gộp nhiều loại chứng khoán vốn; không có căn cứ phân bổ. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA ĐỦ THÔNG TIN PHẠM VI/CẤU TRÚC** |

### Rủi ro lãi suất — 1 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p85 | Tổng kết hợp tại “Tổng tài sản / Tổng nợ phải trà / Mức chênh nhạy cảm với lãi suất nội, ngoại bảng / Mức chênh nhạy cảm với lãi suất ngoại bảng / Mức chếnh nhạy cảm với lãi suất nội bảng” lệch 2 triệu so với nội bảng cộng ngoại bảng; giữ số nguồn. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **LỖI/CONFLICT NGUỒN** |

### Tiền gửi/vay TCTD khác — nguồn vốn — 2 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p59 | “Vốn vay từ IFC” là detail/parent trung gian chưa có leaf và không cộng thêm vào subtotal vay; tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p44 | “Phải trả nghiệp vụ UPAS L/C” là detail/parent trung gian chưa có leaf và không cộng thêm vào subtotal vay; tránh double-count. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CHƯA CÓ TRONG SCHEMA TẠI CHECKPOINT** |

### Báo cáo bộ phận hợp nhất — 17 khoản mục

| Ngân hàng / kỳ / báo cáo | Tên PDF | Trang PDF | Khoản mục nguồn, quan hệ và lý do chưa map | ReportNormId/range gần nhất nếu có | Phân loại |
| --- | --- | --- | --- | --- | --- |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p95 | “Cho thuê tài chính” là một trục kinh doanh nhìn thấy trong bảng ACB, nhưng schema 5807–5842 không có trục tương đương; giữ source-only, không ép vào trục khác. | 5807–5842 | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p95 | ACB trình bày riêng “Chứng khoán” và “Quản lý quỹ”, trong khi schema chỉ có trục kết hợp; chưa có rule cộng có kiểm soát hai trục nguồn nên chưa map. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| ACB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p95 | Nhãn “Kết quả kinh doanh bộ phận” không xác lập rõ đây là “Lợi nhuận trước thuế”; không thu hẹp nghĩa để map. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p87 | Trục địa lý “Nước ngoài” của MBB không đồng nhất với schema “Khu vực khác”; giữ source-only, không relabel. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| MBB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p83 | Đã mở trực tiếp MBB p83/trang in 79: bảng bộ phận, cột loại trừ và dòng Thu nhập/Chi phí nội bộ đọc rõ; chờ binding generic cho hàng đối trừ. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN SỬA XỬ LÝ CẤU TRÚC; KHÔNG PHẢI SCHEMA GAP** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p96 | “Hoạt động công ty tài chính” của VPB không có trục tương đương trong schema 5807–5842; giữ source-only. | 5807–5842 | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| VPB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p96 | “Hoạt động chứng khoán” hẹp hơn trục schema kết hợp “Chứng khoán/Quản lý quỹ”; không mở rộng population để map. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p61 | Trục “Nước ngoài” của HDB không đồng nhất với “Khu vực khác”; giữ source-only. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| HDB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p61 | Nhãn “Kết quả kinh doanh bộ phận” không xác lập rõ đây là “Lợi nhuận trước thuế”; không thu hẹp nghĩa để map. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p71 | “Miền Trung và Tây Nguyên” rộng hơn schema “Miền Trung”; không thu hẹp population để map. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p71 | VCB có trục “Nước ngoài” nhưng schema địa lý hiện hành không có trục tương đương; giữ source-only. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| VCB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p72 | Các trục “Dịch vụ tài chính phi ngân hàng / Chứng khoán / Khác” của VCB không đồng nhất với các trục kinh doanh schema; không ép gần nghĩa. | 0161 | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p82 | Các trục “Dịch vụ tài chính phi ngân hàng / Khác” của CTG không đồng nhất với các trục kinh doanh schema; không ép gần nghĩa. | 0161 | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| CTG / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p82 | Đã mở trực tiếp CTG p82/trang in 80: toàn bộ bảng bộ phận xoay, hàng kết quả và số đọc rõ; chờ promote/bind đủ hàng bằng primitive generic. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CẦN SỬA XỬ LÝ CẤU TRÚC; KHÔNG PHẢI SCHEMA GAP** |
| BID / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p37 | Các trục “Cho thuê tài chính / Chứng khoán / Khác” của BID không đồng nhất với các trục kinh doanh schema; không ép gần nghĩa. | 0161 | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| BID / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p38 | BID chỉ trình bày “Trong nước / Nước ngoài”, không tương đương trục schema “Miền Bắc / Miền Trung / Miền Nam”; không phân bổ suy diễn. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |
| VIB / Năm 2025 / BCTC hợp nhất / kiểm toán | `BCTC Hợp nhất Kiểm toán năm 2025.pdf` | p61 | Ô “Tài sản cố định — Miền Trung” của VIB nhìn thấy là blank thật, không phải dấu gạch và không phải 0; giữ unresolved value, không tự điền 0. | Chưa có RNID gần nhất được niêm phong; cần rà family hiện hành | **CÓ ID GẦN NGHĨA NHƯNG KHÁC BẢN CHẤT** |


### Khi nào SOURCE_ONLY là ứng viên schema?

- Chỉ đưa sang schema review khi nhãn có bản chất riêng, lặp lại hoặc có số độc
  lập và đã rà hết ID gần nghĩa.
- Parent, subtotal, `Trong đó`, cột trục, blank và component chỉ dùng kiểm tra
  không phải lý do tạo ID mới.
- Danh sách quyết định schema/source lịch sử gồm 205 source-row vẫn được giữ tại
  [ledger kỹ thuật](UNRESOLVED_MAPPING_LEDGER.md#canonical-open-source-rows).
