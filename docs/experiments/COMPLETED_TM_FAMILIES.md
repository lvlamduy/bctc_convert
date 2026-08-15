# Tình trạng các cụm thuyết minh trên 8 ngân hàng

Phạm vi: ACB, MBB, VPB, HDB, VCB, CTG, BID, VIB.

Thứ tự các mục dưới đây theo `display_order` của schema TM và thứ tự trình bày
thông dụng trong PDF; mỗi family được khóa bằng khoản mục đầu cụm, khoản mục cuối
cụm và ranh giới family/note kế tiếp trước khi chọn các trục/cột có ý nghĩa.

Quy ước:

- **Đã xác minh**: các khoản mục mục tiêu đã được map và kiểm tra lại.
- **Không có**: báo cáo trong phạm vi này không trình bày family tương ứng.
- **Còn thiếu**: đã thấy vùng nguồn nhưng chưa đủ điều kiện map.
- Dòng tổng hoặc subtotal chỉ dùng để kiểm tra cộng trừ không được tính là khoản
  mục còn thiếu map.

## 1. Tiền, kim loại quý và đá quý

- **Đã xác minh:** MBB p30, VPB p38 và VIB p31. Mỗi vùng map bốn dòng
  `Tiền mặt bằng VND`, `Tiền mặt bằng ngoại tệ`, `Vàng/Vàng tiền tệ` và tổng
  family; cả ba phương trình hiện kỳ `VND + ngoại tệ + vàng = tổng` đóng đúng.
- **Không có cụm thuyết minh trong PDF đã bind:** ACB, HDB, VCB, CTG, BID.
  Chủ dự án xác nhận ACB bắt đầu phần thuyết minh từ cụm tiền gửi/cho vay TCTD
  khác tại p16; HDB, VCB, CTG và BID bắt đầu lần lượt từ cụm `Chứng khoán kinh
  doanh` tại p25, p30, p37 và p20. Dòng tổng trên báo cáo tình hình tài chính
  không được relabel thành một cụm thuyết minh chi tiết.
- **Còn thiếu:** Không còn khoản mục nguồn của family này chờ map trong tám PDF.

Ghi chú kỳ: PDF VPB được cung cấp là tại 31/03/2026 nên kết quả VPB giữ đúng
Q1/2026, không relabel thành Q2/2026.

## 2. Tiền gửi tại NHNN

- **Đã xác minh:** MBB p30, VPB p38 và VIB p31. Cả ba cụm được giới hạn từ
  owner đầu cụm qua nhánh `Tiền gửi tại NHNN`, hai hàng `Bằng VND` / `Bằng
  ngoại tệ` đến dòng tổng đầu tiên. Chỉ hai cột kỳ tiền tệ được dùng; bảng tỷ
  lệ dự trữ sau dòng tổng không thuộc cụm này. MBB `Tiền gửi tại Ngân hàng Nhà
  nước Lào` và `Tiền gửi tại Ngân hàng Quốc gia Campuchia` được cộng thành
  `Tiền gửi khác` ReportNormId 574 theo quyết định của chủ dự án; `934.855 +
  1.213.504 = 2.148.359`, và `25.269.011 + 2.148.359 = 27.417.370` đóng đúng.
- **Không có cụm thuyết minh trong PDF đã bind:** ACB, HDB, VCB, CTG, BID.
  Các mốc bắt đầu phần thuyết minh đã được chủ dự án xác nhận như mục 1; dòng
  tổng hoặc bảng thanh khoản/rủi ro không được relabel thành note `Tiền gửi tại
  NHNN`.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong family này.

Ghi chú kỳ: PDF VPB được cung cấp là tại 31/03/2026 nên kết quả VPB giữ đúng
Q1/2026, không relabel thành Q2/2026.

## 3. Tiền, vàng gửi tại và cho vay/vay các TCTD khác

- **Đã xác minh:** ACB p16, MBB p30, VPB p39, CTG p41, BID p25 và VIB p32.
  Đã map 63 dòng tiền gửi không/có kỳ hạn, VND, ngoại tệ, cho vay/vay, dự
  phòng và chiết khấu/tái chiết khấu; 23 phương trình cha–con, subtotal và tổng
  family đóng đúng. BID dùng biến thể có `vàng và ngoại tệ` và đơn vị triệu VND
  được kế thừa từ công bố đơn vị ở cấp tài liệu. CTG/BID dùng từ `vay` thay cho
  `cho vay`. Dòng chiết khấu/tái chiết khấu chỉ là chi tiết không cộng thêm.
- **Không có cụm thuyết minh trong PDF đã bind:** HDB, VCB. Chủ dự án xác nhận
  phần thuyết minh của hai báo cáo bắt đầu từ `Chứng khoán kinh doanh` tại p25
  và p30; dòng tổng hoặc bảng rủi ro không được relabel thành family 575.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. Ba ô dấu
  `-` hiện kỳ của ACB được giữ trạng thái `DASH`, khóa bằng pixel và chuẩn hóa
  thành 0 theo quy ước của chủ dự án.

Ghi chú kỳ: PDF VPB được cung cấp là tại 31/03/2026 nên kết quả VPB giữ đúng
Q1/2026, không relabel thành Q2/2026.

## 4. Chứng khoán kinh doanh

- **Đã xác minh:** ACB p16, MBB p31, VPB p40, HDB p24, VCB p30, CTG p37 và
  BID p20. Đã map 58 dòng chứng khoán nợ/vốn, nhánh tổ chức hoặc niêm
  yết/chưa niêm yết, khoản khác, tổng gộp và dự phòng; 20 phương trình
  cha–con, gross–dự phòng–net đóng chính xác. MBB dùng biến thể niêm
  yết/chưa niêm yết; sáu bank còn lại dùng biến thể theo tổ chức phát hành.
- **Không có vùng `Chứng khoán kinh doanh` hoàn chỉnh trong phạm vi PDF:**
  VIB. Đây không phải tuyên bố VIB không có family chứng khoán nói chung vì
  VIB có `Chứng khoán đầu tư sẵn sàng để bán` tại p36, đã xử lý riêng ở mục 16.
- **Còn thiếu:** Không còn khoản mục trading chờ map.

Ghi chú kỳ: PDF VPB được cung cấp là tại 31/03/2026 nên kết quả VPB giữ đúng
Q1/2026, không relabel thành Q2/2026.

## 5. Công cụ tài chính phái sinh và tài sản/công nợ tài chính khác

- **Đã xác minh:** ACB p17, MBB p43, VPB p41, HDB p25, CTG p38, BID p21
  và VIB p32. Đã map 86 giao điểm hàng × trục có đúng khoản mục schema:
  giá trị hợp đồng, giá trị ghi sổ tài sản và giá trị ghi sổ công nợ cho kỳ
  hiện tại/so sánh; 30 phương trình cha–con hoặc tài sản trừ công nợ đóng
  chính xác. Các cột dòng tiền vào/ra và giá trị thuần chỉ dùng kiểm tra vì
  schema không có trục tương đương. Mười một dấu `-` nhìn thấy ở HDB được giữ
  nguyên trạng thái `DASH` trước khi chuẩn hóa thành 0; ô trống không bị đổi
  thành 0.
- **Không có cụm thuyết minh trong PDF đã bind:** VCB. Chủ dự án xác nhận PDF
  này không có phần thuyết minh cho ReportNormId 631; các dòng tổng/chính sách,
  giá trị hợp lý hoặc kiểm soát rủi ro không được relabel thành bảng giao dịch.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong family này.

Ghi chú OCR số: BID `6,270,0ss` được đọc lại từ pixel/Paddle là `6,270,055`;
VIB `2.126.217` được đọc lại là `12.126.217`. VietOCR Transformer chỉ giữ vai
trò anchor/geometry và không được dùng để tự sửa số. PDF VPB là Q1/2026.

## 6. Phân tích theo loại hình cho vay

- **Đã xác minh:** ACB p17, MBB p31, VPB p42, HDB p26, VCB p30, CTG p38,
  BID p22, VIB p33. Tổng cộng 46 khoản mục nguồn đã được map; gồm ACB
  `Cho vay theo chỉ định của Chính phủ` và VPB `Cấp tín dụng khác`.
- **Không có:** Không có bank nào. ACB, VCB, CTG và BID là biến thể không có
  tiêu đề family riêng nhưng các hàng con nằm trực tiếp dưới `Cho vay khách hàng`.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong các vùng đã xác minh.

## 7. Phân tích cho vay theo ngành nghề kinh doanh

- **Đã xác minh:** MBB p33, VPB p44, HDB p27, BID p22, VIB p33; tổng cộng
  80 khoản mục nguồn đã được map.
- **Không có trong báo cáo:** ACB, VCB, CTG.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong năm vùng được tìm
  thấy. Các quyết định đã gồm `Vận tải kho bãi` → 736, population chi nhánh
  nước ngoài → 6058, khoản vay mua nhà ở cá nhân → khoản mục schema riêng,
  `Dịch vụ` của BID → khoản mục schema riêng, và các ngành nhỏ phù hợp → 745.

## 8. Phân tích chất lượng cho vay

- **Đã xác minh:** ACB p18, MBB p31, VPB p42, HDB p26, VCB p30, CTG p39,
  BID p22, VIB p60. Năm nhóm chất lượng nợ đã được map cho cả 8 bank. Bản
  chuẩn hóa E-0067B còn tách `Cho vay giao dịch ký quỹ và ứng trước tiền bán
  chứng khoán` thành ReportNormId 1944, là con trực tiếp của 746 trong context
  đã được chủ dự án phê duyệt: ACB `20.644.553 / 17.340.705`, MBB
  `16.828.054 / 15.040.585`, VPB `36.278.045 / 34.093.219`.
- **Không có:** Không có bank nào.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. Với ACB/VPB, 747 giữ
  nguyên vì margin là dòng đứng ngoài năm nhóm. Với MBB, 5746 chỉ giữ làm cầu
  nối cách trình bày nguồn; 747 được điều chỉnh từ
  `1.197.767.532 / 1.059.781.834` xuống
  `1.180.939.478 / 1.044.741.249`, còn giá trị tách ra map vào 1944. Tổng sau
  chuẩn hóa vẫn đóng đúng và không double count.

Kết quả exact-replay:
`docs/experiments/E-0067B-loan-quality-margin-separation-project-owner-v1.json`.

## 9. Phân tích dư nợ theo thời gian/thời hạn gốc

- **Đã xác minh:** ACB p18, MBB p31, VPB p42, HDB p26, VCB p31, CTG p39,
  BID p22, VIB p33. Ba hàng `Nợ ngắn hạn`, `Nợ trung hạn`, `Nợ dài hạn`
  đã được map cho cả 8 bank; hai hàng margin hợp lệ của MBB và VPB cũng đã
  được map.
- **Không có:** Không có bank nào.
- **Còn thiếu:** Không còn khoản mục mục tiêu chưa map. Các dòng tổng vẫn là
  dòng kiểm tra nguồn, không map thành khoản mục chi tiết.

## 10. Phân tích cho vay theo loại hình tiền tệ

- **Đã xác minh mapping:** Không phát sinh mapping vì cả tám PDF cố định không
  trình bày family 756–758 trong note `Cho vay khách hàng`.
- **Không có trong báo cáo:** ACB p17–18, MBB p31–33, VPB p42–44, HDB
  p26–27, VCB p30–31, CTG p38–39, BID p22 và VIB p33–34. Ranh giới được
  kiểm tra từ owner đầu note qua family con cuối cùng đến family/note kế tiếp.
- **Còn thiếu:** Không có khoản mục nguồn cần map. Whole-PDF scan giữ 38 cặp
  `VND`/`ngoại tệ` gần giống làm đối chứng âm; chúng thuộc tiền gửi/liên ngân
  hàng, nằm ngoài ranh giới `Cho vay khách hàng`, nên không được gán vào 757/758.

## 11. Phân tích dư nợ cho vay theo khu vực địa lý

- **Đã xác minh:** MBB p52 và VIB p53–54. MBB dùng biến thể khu vực theo hàng ×
  family theo cột; VIB dùng family theo hàng × khu vực theo cột và nối hai trang
  hiện tại/so sánh. Đã map `Trong nước` (5752) và `Nước ngoài` (765) cho hai
  bank; ba phương trình `trong nước + nước ngoài = tổng Cho vay khách hàng`
  đóng đúng. Hai dấu `-` nhìn thấy của VIB được giữ `DASH` rồi chuẩn hóa thành 0.
- **Không có cụm cho vay khách hàng theo khu vực:** ACB, VPB, HDB, VCB, CTG,
  BID trong các PDF đã cung cấp. Các bảng địa lý tại ACB/VPB/HDB/CTG/BID có
  population `Tổng dư nợ` rộng hơn `Cho vay khách hàng` nên được giữ làm đối
  chứng, không thu hẹp hay map ngầm. VCB p42 là báo cáo bộ phận thu nhập/chi phí,
  thuộc family khác.
- **Còn thiếu:** Không còn review mở cho family này.

## 12. Phân tích theo loại hình doanh nghiệp/đối tượng khách hàng

- **Đã xác minh:** MBB p32, VPB p43, HDB p26, VIB p34; 44 khoản mục nguồn
  đã được map. `Cho vay cá nhân` tương đương không cộng thêm với 780,
  `Cho vay khác` tương đương không cộng thêm với 782, và population chi nhánh
  nước ngoài dùng 6058.
- **Không có vùng enterprise/customer-type hoàn chỉnh:** ACB, VCB, CTG, BID.
  Các hàng không tiêu đề của bốn bank này thuộc family loại hình cho vay và đã
  được xử lý ở mục 6; không ép sang family doanh nghiệp.
- **Còn thiếu:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| MBB | 32 | Cho vay các TCKT | Giữ làm group parent để kiểm tra tổng các hàng con; chưa xuất thêm một mapping cộng dồn nhằm tránh double count. |

## 13. Dự phòng rủi ro cho vay khách hàng

- **Đã xác minh:** ACB p18, MBB p34, VPB p45, HDB p28, VCB p31, CTG p39,
  BID p23, VIB p34. Đã map `Dự phòng chung`, `Dự phòng cụ thể` và các dòng
  đầu kỳ, trích lập/hoàn nhập, sử dụng, chênh lệch/điều chỉnh (nếu có), cuối
  kỳ. VPB còn map riêng nhánh dự phòng cho vay margin/ứng trước.
- **Không có:** Không có bank nào.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong kỳ hiện tại của báo
  cáo được cung cấp. Riêng PDF VPB là báo cáo tại 31/03/2026 nên kết quả VPB
  được xác minh cho Q1/2026; chưa có nguồn VPB Q2/2026 để thay thế.

| Bank | Trang | Khoản mục nguồn | Ghi chú |
| --- | ---: | --- | --- |
| VPB | 45 | Dự phòng chung, cụ thể và cho vay margin/ứng trước | Đã map từ kỳ 01/01–31/03/2026; nguồn Q2/2026 chưa có trong PDF được cung cấp. |

## 14. Hoạt động mua nợ

- **Đã xác minh:** MBB p35, VPB p46, HDB p29 và VIB p35. Đã map 17 dòng
  `Mua nợ bằng VNĐ`, `Mua nợ bằng ngoại tệ` (HDB), `Dự phòng rủi ro`, `Nợ
  gốc đã mua`, `Lãi của khoản nợ đã mua`; 34 ô hiện tại/so sánh và 16 phương
  trình lõi đều đóng đúng. Năm dấu `-` nhìn thấy được giữ trạng thái `DASH`
  rồi chuẩn hóa thành 0.
- **Không có trong báo cáo:** ACB, VCB, CTG, BID. Whole-PDF scan không tìm
  thấy vùng nào đi từ owner `Hoạt động mua nợ` qua hai khối số dư/gốc-lãi đến
  ranh giới family kế tiếp.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong bốn vùng đã xác minh.
  Nhánh chất lượng và biến động dự phòng của VPB cùng khối mua nợ lịch sử 2017
  của VIB chỉ dùng kiểm tra, không cộng hoặc map lại vào số dư hiện tại.

Ghi chú kỳ: PDF VPB được cung cấp là tại 31/03/2026 nên kết quả VPB giữ đúng
Q1/2026, không relabel thành Q2/2026.

## 15. Tiền gửi của khách hàng — phân loại theo loại/kỳ hạn/đối tượng

- **Đã xác minh:** ACB p21, MBB p43, VPB p55, HDB p31, VCB p35, CTG p42,
  BID p25 và VIB p41–42. Đã map 120 dòng loại tiền gửi, VND/ngoại tệ và
  các dòng đối tượng khách hàng đủ chắc; 43 phương trình parent–child, tổng cột
  và tổng bảng đều đóng đúng. ACB dùng biến thể hai khối kỳ theo chiều dọc ×
  ba cột VND/ngoại tệ/tổng; cột tổng chỉ kiểm tra. MBB map `Tiền gửi của TCKT`
  vào 1084 và `Tiền gửi của cá nhân` vào 1089; `Tiền gửi vốn chuyên dùng`
  không tách tiền tệ được đưa vào VND theo quyết định của chủ dự án. VIB nối
  bảng đối tượng ở trang 42 và giữ nhánh tiết kiệm là subset không cộng trùng.
- **Điều chỉnh đã đóng:** Dòng `Công ty TNHH 2 thành viên trở lên có phần vốn
  góp của Nhà nước trên 50%` tại VPB p55 (`64.165`) và VIB p42 (`174`) cùng
  map vào ReportNormId 770 `Công ty TNHH MTV (hoặc trên MTV) vốn nhà nước trên
  50%` theo quyết định của chủ dự án.
- **Không có:** Không có bank nào.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong tám vùng đã xác minh.

Ghi chú kỳ: PDF VPB được cung cấp là tại 31/03/2026 nên kết quả VPB giữ đúng
Q1/2026, không relabel thành Q2/2026.

## 16. Chứng khoán đầu tư

- **Đã xác minh:** ACB p19, MBB p35–36, VPB p47–48, HDB p29, VCB p32,
  CTG p40, BID p23 và VIB p36. Đã map 99 khoản mục nguồn/198 ô hiện tại–so sánh của
  các nhánh sẵn sàng để bán, giữ đến ngày đáo hạn, dự phòng, chất lượng và
  VAMC đủ chắc; 39 phương trình gross–dự phòng–net hoặc cha–con đóng đúng.
  VIB p36 được giữ đúng dưới nhánh 805 của owner 804; cây owner có bốn nhánh
  805/829/853/859 và toàn family kết thúc tại 861, không bị ép sang trading 592.
- **Điều chỉnh đã đóng:** BID p23 kế thừa đơn vị `Triệu VND` từ tuyên bố đơn vị
  nhìn thấy trên p13 của chính PDF; toàn vùng AFS/HTM và các phương trình đều
  được xác minh. Tại VIB p36, `5.894.320 + 32.879.230 = 38.773.550` và
  `12.104.102 + 28.252.422 = 40.356.524`; hai dòng trái phiếu/chứng chỉ tiền gửi
  do TCTD khác phát hành được cộng có kiểm soát rồi map một lần vào 808.
- **Không có:** Không có bank nào được xác nhận vắng toàn bộ family này.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong tám vùng đã xác minh.

Ghi chú kỳ: PDF VPB được cung cấp là tại 31/03/2026 nên kết quả VPB giữ đúng
Q1/2026, không relabel thành Q2/2026.

## 17. Các khoản đầu tư dài hạn khác

- **Đã xác minh:** ACB p19, MBB p36, VPB p48, HDB p30, VCB p33,
  CTG p40, BID p24 và VIB p36. Đã map 29 khoản mục nguồn/58 ô hiện
  tại–so sánh; chín phương trình chi tiết–tổng hoặc giá gốc–dự
  phòng–giá trị thuần đóng đúng. Mỗi PDF chỉ có một vùng thỏa khung
  family trên toàn báo cáo.
- **Biến thể đã đóng:** ACB/VIB chỉ có `Đầu tư dài hạn khác`;
  MBB tách `Tổ chức kinh tế, dự án dài hạn` và `Quỹ đầu tư`; VPB
  có bảng chi tiết tổ chức/dự án; HDB/VCB/BID có công ty liên
  kết; VCB/CTG/BID có công ty liên doanh. Schema đã bổ sung 6066
  `Đầu tư vào công ty liên doanh` và 6067 `Đầu tư vào công ty
  liên kết`; dấu `-` hiện kỳ của HDB được giữ `DASH` rồi chuẩn hóa
  thành 0.
- **Không có:** Không có bank nào.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong tám vùng đã
  xác minh.

Ghi chú kỳ: PDF VPB được cung cấp là tại 31/03/2026 nên kết quả VPB giữ đúng
Q1/2026, không relabel thành Q2/2026.

## 18. Tăng, giảm tài sản cố định hữu hình

- **Đã xác minh:** MBB p37, VPB p49 và VIB p37. Đã map 35 dòng giá
  gốc/hao mòn lũy kế/giá trị còn lại; 12 phương trình tăng–giảm–cuối kỳ và
  giá gốc trừ hao mòn đều đóng đúng. MBB p38 chỉ là vùng so sánh năm 2025,
  không được trộn vào kỳ hiện tại.
- **Không có trong báo cáo:** ACB, HDB, VCB, CTG và BID không trình bày bảng
  biến động tài sản cố định hữu hình chi tiết trong các PDF đã cung cấp.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong ba vùng có bảng.
  Trang VIB xoay được nhận dạng lại bằng đúng VietOCR Transformer cho text và
  PP-OCRv6 trên ảnh đã xoay cho số; bốn số sai từ OCR nguồn cũ đã được pixel và
  quan hệ kế toán bác bỏ, không dùng Gemma để nhận số.

Ghi chú kỳ: PDF VPB được cung cấp là tại 31/03/2026 nên kết quả VPB giữ đúng
Q1/2026, không relabel thành Q2/2026.

## 19. Tăng, giảm tài sản cố định thuê tài chính

- **Đã xác minh:** Không có bank nào có bảng biến động TSCĐ thuê tài chính
  chi tiết trong tám báo cáo đã cung cấp.
- **Không có trong báo cáo:** ACB, MBB, VPB, HDB, VCB, CTG, BID và VIB.
  Whole-PDF scan đã phân biệt các bảng TSCĐ hữu hình/vô hình với tên công ty
  cho thuê tài chính, chính sách kế toán, dòng cho vay và thu nhập cho thuê tài
  chính; các đối chứng gần này không được nâng thành family 896–912.
- **Còn thiếu:** Không có khoản mục nguồn chờ map trong tám PDF đã bind.

## 20. Tăng, giảm tài sản cố định vô hình

- **Đã xác minh:** MBB p39, VPB p50 và VIB p38. Đã map 32 dòng nguyên giá,
  hao mòn lũy kế, giá trị còn lại và 12 phương trình tăng–giảm–cuối kỳ hoặc
  nguyên giá trừ hao mòn; MBB p40 chỉ là vùng so sánh và không được trộn vào
  kỳ hiện tại.
- **Bổ sung schema:** ReportNormId 6068 là `Tổng giảm nguyên giá TSCĐ vô hình
  trong kỳ`, đối xứng với tổng tăng 5997. ReportNormId 6069 được thêm cho
  `Nguyên giá TSCĐ vô hình đã hao mòn hết nhưng vẫn còn sử dụng`, nhìn thấy và
  map tại VPB/VIB.
- **Không có trong báo cáo:** ACB, HDB, VCB, CTG và BID không trình bày bảng
  biến động TSCĐ vô hình chi tiết trong các PDF đã cung cấp.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong ba vùng có bảng.
  PDF VPB là nguồn Q1/2026 và được giữ đúng kỳ, không relabel thành Q2.

## 21. Tăng, giảm bất động sản đầu tư

- **Đã xác minh:** MBB p41. Vùng hiện kỳ 30/06/2026 được tách khỏi vùng so
  sánh 31/12/2025 nằm ngay bên dưới trên cùng trang. Đã map 9 dòng tổng của
  nguyên giá, giá trị hao mòn và giá trị còn lại; 11 phương trình
  roll-forward, tổng cột tài sản và `nguyên giá - hao mòn = giá trị còn lại`
  đều đóng đúng.
- **Biến thể đã đóng:** MBB dùng nhãn `Giá trị hao mòn` thay cho `Giá trị hao
  mòn lũy kế`; hai cột tài sản được giữ làm thành phần kiểm tra và chỉ cột
  `Tổng cộng` được map. Ô `Tăng trong kỳ` của nguyên giá là dấu `-`, được khóa
  trực tiếp bằng pixel và chuẩn hóa thành 0 trước khi kiểm tra phương trình.
- **Không có bảng biến động chi tiết trong báo cáo:** ACB, VPB, HDB, VCB,
  CTG, BID và VIB. Các dòng trên báo cáo tình hình tài chính, chính sách kế
  toán, dòng tiền hoặc chi phí gộp `TSCĐ và bất động sản đầu tư` chỉ là đối
  chứng âm, không được relabel thành family 942–5974.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong vùng MBB đã xác minh.

## Bảng tổng hợp

Ký hiệu: **✓** đã map/xác minh; **—** không có vùng family tương ứng; **△** đã
thấy vùng nguồn nhưng chưa map; **✓\*** đã map phần mục tiêu, còn hàng ngoài lõi
hoặc group parent chỉ giữ để kiểm tra.

| Cụm | ACB | MBB | VPB | HDB | VCB | CTG | BID | VIB | Còn chưa map |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tiền, kim loại quý, đá quý | — | ✓ p30 | ✓\* p38 | — | — | — | — | ✓ p31 | 0 dòng; 5 bank xác nhận không có cụm; VPB là nguồn Q1 |
| Tiền gửi tại NHNN | — | ✓ p30 | ✓\* p38 | — | — | — | — | ✓ p31 | 0 dòng; Lào+Campuchia → 574; 5 bank xác nhận không có cụm; VPB là nguồn Q1 |
| Tiền gửi/vay TCTD khác | ✓ p16 | ✓ p30 | ✓\* p39 | — | — | ✓ p41 | ✓ p25 | ✓ p32 | 0 dòng; HDB/VCB xác nhận không có cụm; VPB là nguồn Q1 |
| Chứng khoán kinh doanh | ✓ p16 | ✓ p31 | ✓\* p40 | ✓ p24 | ✓ p30 | ✓ p37 | ✓ p20 | — | 0 dòng trading; AFS VIB ở cụm Chứng khoán đầu tư; VPB là nguồn Q1 |
| Công cụ tài chính phái sinh | ✓ p17 | ✓ p43 | ✓\* p41 | ✓ p25 | — | ✓ p38 | ✓ p21 | ✓ p32 | 0 dòng; VCB xác nhận không có cụm; VPB là nguồn Q1 |
| Loại hình cho vay | ✓ p17 | ✓ p31 | ✓ p42 | ✓ p26 | ✓ p30 | ✓ p38 | ✓ p22 | ✓ p33 | 0 |
| Ngành nghề kinh doanh | — | ✓ p33 | ✓ p44 | ✓ p27 | — | — | ✓ p22 | ✓ p33 | 0 trong 5 vùng; 3 bank không có |
| Chất lượng cho vay | ✓ p18 | ✓ p31 | ✓ p42 | ✓ p26 | ✓ p30 | ✓ p39 | ✓ p22 | ✓ p60 | 0; 1944 tách riêng tại ACB/MBB/VPB, MBB 747 đã trừ đúng 5746 |
| Dư nợ theo thời gian | ✓ p18 | ✓ p31 | ✓ p42 | ✓ p26 | ✓ p31 | ✓ p39 | ✓ p22 | ✓ p33 | 0 khoản mục mục tiêu |
| Cho vay theo loại tiền tệ | — p17–18 | — p31–33 | — p42–44 | — p26–27 | — p30–31 | — p38–39 | — p22 | — p33–34 | 0; family không có trong 8 PDF cố định |
| Cho vay theo khu vực địa lý | — | ✓ p52 | — | — | — | — | — | ✓ p53–54 | 0; sáu PDF không có đúng family cho vay khách hàng theo khu vực |
| Doanh nghiệp/đối tượng KH | — | ✓\* p32 | ✓ p43 | ✓ p26 | — | — | — | ✓ p34 | 1 group parent check-only |
| Dự phòng cho vay | ✓ p18 | ✓ p34 | ✓\* p45 | ✓ p28 | ✓ p31 | ✓ p39 | ✓ p23 | ✓ p34 | 0 dòng; VPB còn thiếu nguồn Q2 |
| Hoạt động mua nợ | — | ✓ p35 | ✓\* p46 | ✓ p29 | — | — | — | ✓\* p35 | 0 dòng; 4 bank không có; VPB là nguồn Q1 |
| Tiền gửi khách hàng | ✓ p21 | ✓ p43 | ✓\* p55 | ✓ p31 | ✓ p35 | ✓ p42 | ✓ p25 | ✓ p41–42 | 0 dòng; VPB là nguồn Q1 |
| Chứng khoán đầu tư | ✓ p19 | ✓ p35–36 | ✓\* p47–48 | ✓ p29 | ✓ p32 | ✓ p40 | ✓ p23 | ✓ p36 | 0 dòng; BID dùng đơn vị cấp tài liệu, VIB gộp hai dòng TCTD vào 808; VPB là nguồn Q1 |
| Đầu tư dài hạn khác | ✓ p19 | ✓ p36 | ✓\* p48 | ✓ p30 | ✓ p33 | ✓ p40 | ✓ p24 | ✓ p36 | 0 dòng; VPB là nguồn Q1 |
| Tăng, giảm TSCĐ hữu hình | — | ✓ p37 | ✓\* p49 | — | — | — | — | ✓ p37 | 0 dòng; 5 bank xác nhận không có bảng chi tiết; VPB là nguồn Q1 |
| Tăng, giảm TSCĐ thuê tài chính | — | — | — | — | — | — | — | — | 0 dòng; cả 8 PDF xác nhận không có bảng chi tiết |
| Tăng, giảm TSCĐ vô hình | — | ✓ p39 | ✓\* p50 | — | — | — | — | ✓ p38 | 0 dòng; 32 mapping, 12 phương trình, 5 bank không có bảng; VPB là nguồn Q1 |
| Tăng, giảm bất động sản đầu tư | — | ✓ p41 | — | — | — | — | — | — | 0 dòng; 9 mapping, 11 phương trình, 7 bank không có bảng chi tiết |
