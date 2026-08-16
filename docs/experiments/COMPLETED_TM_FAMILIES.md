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

## 22. Tài sản Có khác

- **Đã xác minh:** MBB p42, VPB p51–53 và VIB p39. Đã map 58 khoản mục
  nguồn/126 thành phần giá trị hiện tại–so sánh; 30 phép cộng trừ cha–con,
  subtotal, chất lượng, lãi phí, lợi thế thương mại và tổng family đóng đúng.
  MBB dùng hai note anh em `Các khoản phải thu`/`Tài sản Có khác`; VPB dùng
  một owner nối ba trang và các bảng con; VIB dùng một bảng tổng kèm hai bảng
  chi tiết ngay dưới. Mỗi PDF chỉ có một vùng thỏa đầy đủ trên toàn báo cáo.
- **Không có bảng thuyết minh chi tiết trong báo cáo:** ACB, HDB, VCB, CTG
  và BID. Năm báo cáo đi từ family đầu tư dài hạn sang các khoản nợ Chính phủ/
  NHNN mà không có note `Tài sản Có khác`; các dòng bảng cân đối, chính sách và
  quản trị rủi ro chỉ là đối chứng âm.
- **Còn thiếu:** 12 dòng nguồn dưới đây chưa có schema tương đương hoặc có
  nghĩa rộng/hẹp khác, nên vẫn `UNRESOLVED` thay vì ép vào khoản mục gần nhất.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 51 | Phải thu bán tài sản tài chính | Rộng hơn 976 `Phải thu từ bán chứng khoán`. |
| VPB | 51 | Dự phòng phí và bồi thường nghiệp vụ nhượng tái bảo hiểm | Chưa có khoản mục con tương đương. |
| VPB | 52 | Số dư đầu kỳ dự phòng rủi ro tài sản Có nội bảng khác | Chưa có nhánh biến động dự phòng tương ứng. |
| VPB | 52 | Trích lập dự phòng rủi ro trong kỳ | Chưa có nhánh biến động dự phòng tương ứng. |
| VPB | 52 | Số dư cuối kỳ dự phòng rủi ro tài sản Có nội bảng khác | Chưa có nhánh biến động dự phòng tương ứng. |
| VPB | 52 | Dự phòng tài sản Có rủi ro tín dụng | Không đồng nhất với population chất lượng 1018. |
| VPB | 52 | Dự phòng cụ thể | Chưa có khoản mục dự phòng `Tài sản Có khác`. |
| VPB | 52 | Dự phòng rủi ro phải thu khó đòi | Chưa có khoản mục con tương đương. |
| VIB | 39 | Phải thu từ Ngân sách Nhà nước | Không đồng nhất với 979 `Phải thu từ NHNN Việt Nam`. |
| VIB | 39 | Phải thu từ hoạt động tài trợ thương mại | Chưa có khoản mục con tương đương. |
| VIB | 39 | Phải thu hoa hồng bảo hiểm | Chưa chứng minh tương đương khoản phải thu từ công ty bảo hiểm con. |
| VIB | 39 | Tài sản thuế TNDN hoãn lại | Chưa có khoản mục con tương đương trong family 966–1023. |

Ghi chú kỳ: PDF VPB được cung cấp là tại 31/03/2026 nên kết quả VPB giữ đúng
Q1/2026, không relabel thành Q2/2026.

## 23. Các khoản nợ Chính phủ và Ngân hàng Nhà nước

- **Đã xác minh:** ACB p20, MBB p42, VPB p53, HDB p30, VCB p34, CTG p41,
  BID p24 và VIB p40. Toàn bộ tám PDF chỉ có một vùng thỏa cấu trúc đầy đủ.
  Đã map 32 khoản mục/66 thành phần giá trị và kiểm tra 28 phương trình tổng,
  subtotal, tiền gửi Kho bạc, khoản vay NHNN và repo. Hai dấu `-` tại HDB/VIB
  được đọc lại trực tiếp từ pixel và chuẩn hóa thành 0. Ba cách gọi `Vay Ngân
  hàng Nhà nước`, `Vay NHNN`, `Vay Ngân hàng Trung ương` cùng map vào 6070;
  tiền gửi có kỳ hạn KBNN map 6071. `Tiền gửi của Bộ Tài chính` tại BID được
  chuyển khỏi catch-all 1039 sang khoản mục riêng 6072.
- **Không có cụm này trong báo cáo:** Không có; cả 8 bank đều có đúng một vùng.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. PDF VPB là nguồn Q1/2026.

## 24. Vốn nhận tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro

- **Đã xác minh:** MBB p43, VPB p56 và VIB p42. Đã map sáu khoản mục/12
  thành phần giá trị hiện tại–so sánh. MBB map tổng family 1092 và `Vốn nhận
  của tổ chức, cá nhân khác` vào 1093. Hai nguồn nhỏ chưa có leaf riêng — dự
  án ODA của VPB và chương trình nhà ở qua NHNN của VIB — được giữ nguyên nhãn
  nguồn và map vào leaf `Khác` 1099; không ép vào hai nhánh tổ chức quốc tế/VND
  gần giống. Bốn phương trình dòng con bằng tổng in lặp tại MBB/VPB đóng đúng.
- **Không có cụm này trong báo cáo:** ACB, HDB, VCB, CTG và BID. Whole-PDF
  scan không có vùng thỏa; trên phần thuyết minh của từng PDF, cụm tiền gửi
  khách hàng chuyển thẳng sang phát hành giấy tờ có giá hoặc family nợ kế tiếp.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong ba vùng có cụm.
  PDF VPB được cung cấp là Q1/2026 và được giữ đúng kỳ 31/03/2026.

## 25. Phát hành giấy tờ có giá

- **Đã xác minh:** ACB p21, MBB p44, VPB p56, HDB p31, VCB p35, CTG p42,
  BID p25 và VIB p43. Whole-PDF scan tìm đúng một vùng hoàn chỉnh trên mỗi
  bank. Đã map 71 khoản mục/132 thành phần giá trị và kiểm tra 36 phương trình
  theo công cụ, kỳ hạn và tổng family. CTG dùng biến thể kỳ hạn theo hàng × công
  cụ theo cột; bốn ô dấu `-` được khóa trực tiếp bằng pixel và chuẩn hóa thành
  0. ACB chỉ dùng cột giá trị ghi sổ để map, cột mệnh giá làm đối chứng. VCB
  dùng nhánh gộp `Kỳ phiếu, trái phiếu`; VPB giữ đúng nguồn Q1/2026. Mốc đúng
  5 năm của ACB được nhận vào leaf 1103/1111 có biên trên bao gồm 5 năm. MBB
  map trực tiếp `Trái phiếu — Dưới 5 năm` vào 6010 và `Chứng chỉ tiền gửi —
  Trên 12 tháng` vào 6009, không tự chia số in thành các kỳ hạn nhỏ hơn. Trái
  phiếu tăng vốn BIDV map riêng vào 1117 và vẫn là detail không cộng lặp với
  parent trái phiếu.
- **Không có cụm này trong báo cáo:** Không có; cả 8 bank đều có đúng một vùng.
- **Còn thiếu:** Chỉ còn ba hàng VPB dưới đây. Đây là trục kỳ hạn của toàn cụm,
  không chỉ rõ số thuộc chứng chỉ tiền gửi, kỳ phiếu hay trái phiếu.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 56 | Toàn family — Dưới 12 tháng | Trục kỳ hạn áp dụng cho toàn family, không riêng một công cụ. |
| VPB | 56 | Toàn family — Từ trên 12 tháng đến 5 năm | Trục kỳ hạn toàn family, không riêng một leaf công cụ. |
| VPB | 56 | Toàn family — Từ trên 5 năm trở lên | Trục kỳ hạn toàn family, không riêng một leaf công cụ. |

## 26. Các khoản phải trả và công nợ khác

- **Đã xác minh:** ACB p22, MBB p44, VPB p57, HDB p31, VCB p35, CTG p43,
  BID p26 và VIB p43. Whole-PDF scan tìm đúng một vùng hoàn chỉnh trên mỗi
  bank và giữ 36 vùng gần giống làm đối chứng âm. Đã map 39 khoản mục/78 thành
  phần giá trị, kiểm tra 28 phương trình parent–child/tổng. Hai dấu `-` của dự
  phòng ACB được khóa bằng pixel và chuẩn hóa thành 0. VPB giữ đúng nguồn
  Q1/2026.
- **Không có cụm này trong báo cáo:** Không có; cả 8 bank đều có đúng một vùng.
- **Còn thiếu:** 18 hàng nguồn dưới đây chưa có leaf tương đương. Các giá trị
  vẫn được giữ trong parent/tổng nguồn và không bị cộng hai lần.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| ACB | 22 | Thu nhập chưa thực hiện | Chưa có leaf tương đương trong family 1118–1127. |
| ACB | 22 | Quỹ phát triển khoa học và công nghệ | Chưa có leaf tương đương trong family. |
| VPB | 57 | Các khoản khách hàng trả trước | Chưa có leaf tương đương; chỉ nằm trong parent phải trả bên ngoài. |
| VPB | 57 | Doanh thu chờ phân bổ | Chưa có leaf tương đương. |
| VPB | 57 | Dự phòng nghiệp vụ bảo hiểm | Không đồng nhất với `Dự phòng rủi ro khác` 1125. |
| VPB | 57 | Các khoản treo chờ chuyển tiền | Chưa có leaf tương đương. |
| VPB | 57 | Phải trả hoạt động thanh toán thẻ | Chưa có leaf tương đương. |
| VPB | 57 | Phải trả nhà cung cấp | Chưa có leaf tương đương. |
| VPB | 57 | Phải trả các khoản vay khách hàng của VPBankS | Chưa có leaf tương đương cho nghĩa vụ của công ty con. |
| VPB | 57 | Tiền giữ hộ và đợi thanh toán | Chưa có leaf tương đương. |
| CTG | 43 | Các khoản lãi, phí phải trả | Chưa có leaf tương đương; vẫn nằm trong tổng family đã kiểm tra. |
| VIB | 43 | Các khoản lãi, phí phải trả | Chưa có leaf tương đương. |
| VIB | 43 | Phải trả cổ tức cho cổ đông | Chưa có leaf tương đương. |
| VIB | 43 | Tiền giữ hộ và đợi thanh toán | Chưa có leaf tương đương. |
| VIB | 43 | Phải trả thanh toán giữa các TCTD | Chưa có leaf tương đương. |
| VIB | 43 | Phải trả chuyển tiền chờ thanh toán | Chưa có leaf tương đương. |
| VIB | 43 | Các khoản chờ thanh toán khác | Chưa có leaf tương đương. |
| VIB | 43 | Doanh thu chờ phân bổ | Chưa có leaf tương đương. |

## 27. Vốn và các quỹ

- **Đã map/xác minh:** ACB p23–24, MBB p44–45, VPB p60–61, HDB p33–34,
  VCB p36–37 và CTG p43–44. Whole-PDF scan tìm đúng một vùng tại cả 8 bank;
  65 mapping/131 ô số và 20 phương trình mở đầu–tăng–giảm–cuối kỳ hoặc
  cột vốn–tổng đã được kiểm tra. VPB giữ đúng nguồn Q1/2026.
- **Không có cụm này trong báo cáo:** Không có.
- **Có cụm nhưng còn khoản mục chưa map:** BID p27–28 và VIB p44–45 đã xác
  minh cấu trúc bảng xoay, nhưng chưa map số vì OCR số nguồn trên bảng xoay
  chưa đủ tin cậy; VietOCR xoay chỉ được dùng cho text/anchor. Các cột nguồn
  chưa có leaf tương đương tại VPB/HDB/VCB/CTG cũng giữ `UNRESOLVED`.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 60 | Quỹ đầu tư phát triển | Chưa có cột số dư vốn tương đương trong schema; số vẫn nằm trong tổng vốn đã kiểm tra. |
| VPB | 60 | Cổ phiếu quỹ | Không đồng nhất với nhánh số lượng cổ phiếu 5953; các ô dấu gạch không cần dùng để đóng tổng. |
| HDB | 33 | Cổ phiếu quỹ | Không có leaf số dư vốn tương đương; cột trống không bị tự đổi thành 0. |
| HDB | 33 | Quỹ đầu tư xây dựng cơ bản | Chưa có leaf tương đương; số vẫn nằm trong tổng vốn đã kiểm tra. |
| VCB | 36 | Quỹ đầu tư phát triển | Chưa có leaf tương đương; số được giữ trong subtotal quỹ và tổng vốn. |
| CTG | 43 | Cổ phiếu quỹ | Không có leaf số dư vốn tương đương; dòng trống không bị tự đổi thành 0. |
| CTG | 43 | Chênh lệch đánh giá lại tài sản | Chưa có cột số dư vốn tương đương trong schema. |
| CTG | 43 | Quỹ đầu tư phát triển | Chưa có leaf tương đương; số vẫn nằm trong tổng vốn đã kiểm tra. |
| BID | 27–28 | Báo cáo tình hình thay đổi vốn chủ sở hữu | Bảng xoay đã unique về cấu trúc nhưng nguồn OCR số chưa đủ tin cậy để map. |
| VIB | 44–45 | Báo cáo tình hình thay đổi vốn chủ sở hữu | Bảng xoay đã unique về cấu trúc nhưng nguồn OCR số chưa đủ tin cậy để map. |

## 28. Thu nhập lãi và các khoản thu nhập tương tự

- **Đã map/xác minh:** ACB p24, MBB p46, VPB p62, HDB p34, VCB p38,
  CTG p45, BID p28 và VIB p45. Whole-PDF scan tìm đúng một vùng đầy đủ trong
  mỗi PDF; 54 mapping/108 ô số và 28 phương trình tổng family hoặc subtotal
  chứng khoán đều đóng đúng.
- **Biến thể đã đóng:** Bảy bank in tổng family sau các dòng con; VIB in tổng
  trước các dòng con. Thứ tự các dòng con được phép thay đổi, các dòng cho thuê
  tài chính, bảo lãnh, mua bán nợ và thu tín dụng khác là tùy chọn. VCB dùng
  trục số PaddleOCR ở trang terminal; VietOCR chỉ làm text anchor.
- **Lỗi OCR số đã xử lý:** VietOCR VIB bỏ chữ số đầu ở hai ô (`293.978` thay
  vì `1.293.978`, `357.506` thay vì `1.357.506`). Kết quả map dùng pixel và
  trục số nguồn, giữ nguyên hai proposal sai làm đối chứng, không sửa ngầm.
- **Không có trong báo cáo:** Không có; cả 8 bank đều có cụm.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong tám vùng đã bind.
  VPB là nguồn Q1/2026 và được giữ đúng kỳ, không relabel thành Q2.

## 29. Chi phí lãi và các khoản tương tự chi phí lãi

- **Đã map/xác minh:** ACB p24, MBB p46, VPB p62, HDB p34, VCB p39,
  CTG p45, BID p29 và VIB p45. Whole-PDF scan tìm đúng một vùng đầy đủ trong
  mỗi PDF; 40 mapping/80 ô số và 16 phương trình `bốn dòng con = tổng family`
  đều đóng đúng.
- **Biến thể đã đóng:** Bảy bank in tổng family sau các dòng con; VIB in tổng
  trước các dòng con. MBB/VIB kế thừa trục kỳ và đơn vị từ phần đầu của cùng
  bảng; BID kế thừa `Triệu VND` từ trang thuyết minh ngay trước đó. VCB gộp
  `Trả lãi tiền gửi và vay các tổ chức tín dụng khác` vào đúng dòng
  `Trả lãi tiền vay` 1153, không tính trùng vào tiền gửi.
- **Lỗi OCR số đã xử lý:** VietOCR MBB đọc `(3:975.549)` thay vì
  `(3.975.549)`. Pixel và trục số nguồn xác minh `-3.975.549`; proposal sai
  được giữ làm đối chứng và không dùng làm numeric truth.
- **Không có trong báo cáo:** Không có; cả 8 bank đều có cụm. Dòng
  `Trả lãi tiền thuê tài chính` 1155 không xuất hiện trong tám vùng family đã
  bind; đây là non-observation trong vùng, không phải suy diễn từ text gần đúng.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map. VPB là nguồn Q1/2026 và
  được giữ đúng kỳ, không relabel thành Q2.

## 30. Thu nhập, chi phí và lãi thuần từ hoạt động dịch vụ

- **Đã map/xác minh:** MBB p46, VPB p62 và VIB p45. Whole-PDF scan tìm đúng
  một vùng chi tiết ở mỗi bank này; 43 mapping/86 ô số và 18 phương trình
  `các dòng thu = tổng thu`, `các dòng chi = tổng chi`, `thu + chi = lãi
  thuần` đều đóng đúng cho cả hai kỳ.
- **Biến thể đã đóng:** MBB in tổng thu và tổng chi sau các dòng con; VPB/VIB
  in hai tổng này trước các dòng con. Net có thể có nhãn ở cuối hoặc chỉ có
  hai số dưới owner đầu bảng. Các dòng thanh toán/ngân quỹ, tư vấn, bảo hiểm,
  ủy thác/đại lý, xử lý nợ/định giá, môi giới, thẻ, viễn thông và khác đều là
  nhánh tùy chọn, không bị ép cùng thứ tự. Hai dấu `-` của chi tư vấn MBB được
  khóa trực tiếp bằng pixel và chuẩn hóa thành 0.
- **Không có cụm thuyết minh chi tiết trong báo cáo:** ACB, HDB, VCB, CTG và
  BID. ACB/HDB/CTG/BID chỉ có ba dòng tổng trên báo cáo kết quả kinh doanh;
  VCB còn có các dòng gần giống trong báo cáo bộ phận. Các vùng này không có
  hàng con dịch vụ nên được giữ làm đối chứng âm, không relabel thành note.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong ba vùng chi tiết.
  VPB là nguồn Q1/2026 và được giữ đúng kỳ, không relabel thành Q2.

## 31. Lãi thuần từ hoạt động kinh doanh vàng và ngoại hối

- **Đã map/xác minh:** MBB p47, VPB p63 và VIB p46. Whole-PDF scan tìm đúng
  một vùng chi tiết ở mỗi bank này; 23 mapping/46 ô số và 18 phương trình
  `các dòng thu = tổng thu`, `các dòng chi = tổng chi`, `thu + chi = lãi/lỗ
  thuần` đều đóng đúng cho cả hai kỳ.
- **Biến thể đã đóng:** MBB gộp kinh doanh ngoại tệ giao ngay và vàng thành
  một dòng, đồng thời in tổng thu/tổng chi sau các dòng con. VPB tách riêng
  ngoại tệ giao ngay, vàng và phái sinh tiền tệ; VIB không có dòng vàng riêng;
  hai bank này in tổng thu/tổng chi trước các dòng con. Thứ tự và sự hiện diện
  của dòng vàng là tùy chọn, không có rule theo bank/trang.
- **Không có cụm thuyết minh chi tiết trong báo cáo:** ACB, HDB, VCB, CTG và
  BID. Các PDF này chỉ có dòng lãi/lỗ thuần trên báo cáo kết quả kinh doanh,
  hoặc các vùng chính sách, rủi ro tiền tệ, báo cáo bộ phận và tỷ giá gần giống;
  không vùng nào có đủ cha thu/chi và các dòng con nên không bị relabel thành
  note chi tiết.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong ba vùng chi tiết.
  VPB là nguồn Q1/2026 và được giữ đúng kỳ, không relabel thành Q2.

## 32. Lãi/lỗ thuần từ mua bán chứng khoán kinh doanh

- **Đã map/xác minh:** ACB p24, MBB p47, VPB p63, HDB p34, VCB p39,
  CTG p45 và BID p29. Whole-PDF scan tìm đúng một vùng chi tiết tại mỗi bank;
  28 mapping/56 ô số và 14 phương trình `thu nhập + chi phí + dự phòng =
  lãi/lỗ thuần` đều đóng đúng cho hai kỳ.
- **Biến thể đã đóng:** MBB có owner con xuống dòng dưới tiêu đề chung chứng
  khoán kinh doanh/đầu tư; CTG in hai số dự phòng trước nhãn; BID kế thừa đơn vị
  `Triệu VND` từ đầu section ở trang trước; VPB là bảng Q1/2026. HDB in đúng
  nhãn nguồn `Trích lập dự phòng rủi ro chứng khoán đầu tư` bên trong bảng mua
  bán chứng khoán kinh doanh. Nhãn này được giữ nguyên, còn owner, vị trí hàng,
  trục hai kỳ và hai phương trình đóng đúng xác nhận vai trò 1191. Dấu `-` kỳ
  so sánh của HDB được khóa trực tiếp bằng pixel và chuẩn hóa thành 0.
- **Không có cụm thuyết minh chi tiết trong báo cáo:** VIB. VIB có vùng lãi/lỗ
  mua bán chứng khoán đầu tư tại p46; đây là family kế tiếp và được giữ làm đối
  chứng âm, không relabel thành chứng khoán kinh doanh.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong bảy vùng chi tiết.
  ReportNormId 1192 `Khác` không xuất hiện trong các vùng này. VPB giữ đúng kỳ
  Q1/2026, không relabel thành Q2.

## 33. Lãi/lỗ thuần từ mua bán chứng khoán đầu tư

- **Đã map/xác minh:** ACB p25, MBB p47, VPB p63, HDB p35, CTG p46,
  BID p29 và VIB p46. Whole-PDF scan tìm đúng một vùng chi tiết tại mỗi bank;
  28 mapping/56 ô số và 14 phương trình `thu nhập + chi phí + các nhánh dự
  phòng nhìn thấy = lãi/lỗ thuần` đều đóng đúng cho hai kỳ.
- **Biến thể đã đóng:** MBB dùng owner con dưới tiêu đề chung chứng khoán kinh
  doanh/đầu tư, kế thừa trục kỳ/đơn vị của cùng bảng và có thêm nhánh dự phòng
  giảm giá góp vốn, đầu tư dài hạn 6028; VIB không in dòng dự phòng; CTG/BID
  gọi dòng dự phòng là `Chi phí dự phòng`; BID kế thừa đơn vị `Triệu VND` từ
  đầu section ở trang trước. Ba dấu `-` của ACB và một dấu `-` của MBB được
  khóa trực tiếp bằng pixel rồi chuẩn hóa thành 0. VPB giữ đúng nguồn Q1/2026.
- **Không có cụm thuyết minh chi tiết trong báo cáo:** VCB. VCB chỉ có số tổng
  chứng khoán đầu tư trong báo cáo bộ phận tại p42–43, không có các hàng thu
  nhập/chi phí/dự phòng nên được giữ làm đối chứng âm, không relabel thành note.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong bảy vùng chi tiết.
  ReportNormId 1197 `Khác` không xuất hiện trong các vùng đã bind.

## 34. Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư

- **Đã map/xác minh:** MBB p47. Whole-PDF scan tìm đúng một dòng tổng hợp có
  hai giá trị cùng hàng; dòng tiêu đề cùng tên ở đầu note không có giá trị cùng
  hàng nên chỉ là đối chứng âm. ReportNormId 5990 được xác minh với 2 ô số.
- **Quan hệ kiểm tra:** `249.524 + 3.587 = 253.111` và
  `415.700 + 1.295.273 = 1.710.973`; cả hai kỳ đều đóng đúng với hai family
  chứng khoán kinh doanh và chứng khoán đầu tư đã xác minh độc lập.
- **Không có dòng tổng hợp này trong báo cáo:** ACB, VPB, HDB, VCB, CTG, BID
  và VIB. Đây là bounded non-observation trong tám PDF cố định, không phải khẳng
  định vắng mặt trên mọi kỳ/báo cáo.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map.

## 35. Thu nhập từ góp vốn, mua cổ phần và thu nhập cổ tức

- **Đã map/xác minh:** ACB p25, MBB p48, VPB p64, HDB p35, VCB p39,
  CTG p46 và BID p29. Whole-PDF scan tìm đúng một note chi tiết ở mỗi bank;
  27 mapping/54 ô số và 16 phương trình giữa các nhánh cổ tức, góp vốn, phương
  pháp vốn chủ sở hữu, thu nhập khác và tổng đều đóng đúng.
- **Biến thể đã đóng:** ACB tách ba nguồn cổ tức; MBB chỉ in một dòng parent và
  tổng lặp lại; VPB có một dòng cổ tức và giữ đúng nguồn Q1/2026; HDB có thêm
  thu nhập hợp nhất kinh doanh; VCB/BID có subtotal cổ tức rồi cộng phần chia
  lãi theo phương pháp vốn chủ sở hữu; CTG gộp `Thu từ chứng khoán Vốn`; BID
  kế thừa đơn vị `Triệu VND` từ đầu section ở trang trước.
- **Dấu gạch và lỗi OCR:** 5 dấu `-` được xác minh bằng nguồn/pixel rồi chuẩn
  hóa thành 0. VietOCR đọc hai dấu gạch VPB thành `1`; nguồn native và pixel
  bác bỏ hai proposal này nên kết quả số vẫn là 0.
- **Không có cụm thuyết minh chi tiết trong báo cáo:** VIB. VIB chỉ có dòng
  tổng trên báo cáo kết quả kinh doanh p8, không có note đánh số với trục kỳ,
  đơn vị và các hàng con nên không bị relabel thành note chi tiết.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong bảy note chi tiết.

## 36. Chi phí quản lý chung (Chi phí hoạt động)

- **Đã map/xác minh:** ACB p25, MBB p48, VPB p65, HDB p35, VCB p40,
  CTG p47, BID p30 và VIB p46. Whole-PDF scan tìm đúng một note chi tiết trong
  từng PDF; 99 mapping/198 ô số và 30 phương trình tổng, nhân viên, tài sản hoặc
  quản lý công vụ đóng chính xác.
- **Biến thể đã đóng:** các hàng con nhân viên/tài sản/quản lý có thể có hoặc
  không và đổi thứ tự; MBB/CTG/BID có nhãn xuống dòng; BID kế thừa đơn vị
  `Triệu VND` ở cuối section; VPB là kỳ Q1/2026. VietOCR đọc thiếu một chữ số ở
  VCB (`1.771.726`); pixel và trục số nguồn cùng xác minh `1.777.726` nên số
  VietOCR bị bác bỏ.
- **Không có:** Không có bank nào; cả tám PDF đều có một vùng family duy nhất.
- **Còn thiếu:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 65 | Chi thuê tài sản | Schema 1205–1220 chưa có leaf riêng dưới `Chi về tài sản`. |
| VPB | 65 | Chi phí công nghệ thông tin | Chưa có leaf chi phí CNTT tương đương. |
| VPB | 65 | Chi về thuế GTGT đầu vào không được khấu trừ | Chưa có leaf chi phí VAT đầu vào không khấu trừ tương đương. |
| CTG | 47 | Chi khác về TSCĐ | Chưa có leaf riêng dưới `Chi về tài sản`; số vẫn tham gia phương trình nguồn. |

## 37. Chi phí dự phòng rủi ro tín dụng

- **Đã map/xác minh:** MBB p49, VPB p66 và VIB p47. Whole-PDF scan tìm đúng
  một note chi tiết tại mỗi bank này; 15 mapping/30 ô số và 8 phương trình
  thành phần–tổng đóng chính xác. MBB map các nhánh cho vay khách hàng, TCTD,
  mua nợ, rủi ro khác và cam kết; VPB map cho vay khách hàng, mua nợ và VAMC;
  VIB map parent cho vay khách hàng cùng dự phòng chung/cụ thể và mua nợ.
- **Biến thể đã đóng:** nhãn có thể xuống dòng; các nhánh là tùy chọn; VIB có
  parent cho vay khách hàng rồi hai con chung/cụ thể; tổng family không có nhãn
  và nằm cuối bảng. Hai dấu gạch bị OCR bỏ tại MBB/VIB được khóa bằng pixel và
  chuẩn hóa thành 0. Hai dấu gạch VPB bị VietOCR đọc thành `1`; source native
  `-` bác bỏ proposal và giữ giá trị 0. VPB giữ đúng kỳ Q1/2026.
- **Không có cụm thuyết minh chi tiết trong báo cáo:** ACB, HDB, VCB, CTG và
  BID. Các PDF này chỉ có số tổng KQKD hoặc diễn giải/chính sách gần giống,
  không có note đánh số với trục kỳ, đơn vị, các hàng thành phần và tổng.
- **Còn thiếu:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 66 | Chi phí dự phòng cho vay giao dịch ký quỹ và ứng trước | Chưa có leaf chi phí dự phòng margin/ứng trước trong family 1221. |
| VIB | 47 | Biến động dự phòng rủi ro các khoản phải thu từ hoạt động tài trợ thương mại | Chưa có leaf chi phí dự phòng khoản phải thu tài trợ thương mại. |

## 38. Thu nhập, chi phí và lãi thuần từ hoạt động khác

- **Đã map/xác minh:** MBB p47, VPB p64 và VIB p46. Whole-PDF scan tìm đúng
  một note chi tiết tại mỗi bank; 23 mapping/46 ô số và 14 phương trình thu,
  chi và lãi thuần đóng chính xác. MBB dùng biến thể net-only; VPB/VIB tách
  parent thu nhập, parent chi phí, các con tùy chọn và lãi thuần.
- **Biến thể đã đóng:** dòng tổng có thể có hoặc không có nhãn; các nhánh
  thanh lý tài sản có thể được cộng có kiểm soát; hàng con có thể thiếu hoặc
  đổi thứ tự nhưng parent thu/chi phải đứng trước con. VPB giữ đúng kỳ
  Q1/2026. ACB/HDB/VCB/CTG/BID chỉ có tổng KQKD, segment hoặc diễn giải nên
  không bị relabel thành note chi tiết.
- **Không có cụm thuyết minh chi tiết trong báo cáo:** ACB, HDB, VCB, CTG,
  BID.
- **Còn thiếu:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 64 | Thu từ phạt vi phạm hợp đồng | Family thu nhập hoạt động khác 1229–1239 chưa có leaf riêng cho khoản phạt vi phạm hợp đồng; dòng vẫn tham gia phương trình parent thu nhập đã xác minh. |

## 39. Chi phí thuế thu nhập doanh nghiệp

- **Đã map/xác minh:** MBB p50, VPB p59 và VIB p48. Whole-PDF scan tìm đúng
  một bảng đối chiếu thuế chi tiết tại mỗi bank; 28 mapping/56 ô số và 20
  phương trình từ lợi nhuận trước thuế qua điều chỉnh, thu nhập chịu thuế đến
  chi phí thuế đều đóng chính xác. Toàn bộ ReportNormId 5723–5737 xuất hiện và
  được xác minh ở ít nhất một biến thể.
- **Biến thể đã đóng:** MBB có cả bảng tóm tắt thuế hiện hành/hoãn lại và bảng
  đối chiếu năm thành phần; VPB là Q1/2026 và gộp có kiểm soát thu nhập không
  chịu thuế, điều chỉnh hợp nhất và điều chỉnh khác vào 5729; VIB có một dòng
  điều chỉnh chỉ in số kỳ so sánh. Hai dấu `-` của VPB được giữ là dấu nguồn
  rồi chuẩn hóa thành 0; ô trống kỳ hiện tại của VIB không bị đổi thành 0.
- **Không có cụm thuyết minh chi tiết trong báo cáo:** ACB, HDB, VCB, CTG và
  BID. Các dòng tổng trên KQKD, nghĩa vụ thuế hoặc số dư thuế hoãn lại là đối
  chứng âm, không được relabel thành bảng đối chiếu chi phí thuế.
- **Còn thiếu:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VIB | 48 | Điều chỉnh khác | Nhãn rộng hơn leaf 5733 về điều chỉnh thuế của các năm trước; kỳ hiện tại để trống, kỳ so sánh là `163`, nên giữ `TAX-001` chờ schema thay vì ép nghĩa hoặc coi ô trống là 0. |

## 40. Tiền và các khoản tương đương tiền

- **Đã map/xác minh:** ACB p8, MBB p50, VPB p66, VCB p40, CTG p47 và
  VIB p45. Đã map 31 khoản mục/60 ô số vào đầy đủ family 1248–1254; 12
  phương trình tổng đều đóng đúng.
- **Không có cụm thuyết minh chi tiết trong báo cáo:** HDB và BID. Hai PDF
  chỉ có số dư tiền đầu/cuối kỳ hoặc chính sách gần giống, không có bảng thành
  phần tiền và tương đương tiền với trục kỳ và tổng.
- **Còn thiếu:** Không có khoản mục nguồn chưa map trong sáu vùng đã xác minh.
  Ô chứng khoán kỳ hiện tại của ACB và ô kỳ so sánh của VCB để trống trên PDF
  nên được giữ trống, không đổi thành 0. VPB là nguồn Q1/2026.

## 41. Mua mới và thanh lý các công ty con

- **Đã map/xác minh:** Không có mapping vì cả tám PDF đều không trình bày bảng
  chi tiết 1255–1258 gồm tổng giá trị giao dịch, phần thanh toán bằng tiền và
  tiền thực có trong công ty con/đơn vị kinh doanh.
- **Không có cụm thuyết minh chi tiết trong báo cáo:** ACB, MBB, VPB, HDB,
  VCB, CTG, BID và VIB.
- **Còn thiếu:** Không có khoản mục nguồn chưa map. HDB có giao dịch HDS trở
  thành công ty con nhưng chỉ nêu giao dịch và việc đang xác định giá trị hợp
  lý; CTG chỉ có caption dòng tiền đầu tư. Hai trường hợp này không đủ ba dòng
  của family và không được relabel thành bảng chi tiết.

## 42. Thu nhập nhân viên của ngân hàng

- **Đã map/xác minh:** ACB p26, VPB p66 và VIB p49. Đã map 13 khoản mục/26 ô
  số vào 1261–1268 và kiểm tra 14 phương trình tổng hoặc tỷ lệ. VPB là nguồn
  Q1/2026; các số bình quân tháng được chia theo đúng ba tháng. VIB được chia
  theo sáu tháng.
- **Không có cụm thuyết minh chi tiết trong báo cáo:** MBB, HDB, VCB, CTG và
  BID. Các câu chính sách trợ cấp thôi việc hoặc số nhân viên đứng riêng không
  được relabel thành bảng thu nhập nhân viên.
- **Còn thiếu:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| ACB | 26 | Tiền lương bình quân | Số nguồn là bình quân mỗi nhân viên cho cả kỳ sáu tháng, trong khi 1267 là bình quân người/tháng. |
| ACB | 26 | Thu nhập bình quân | Số nguồn là bình quân mỗi nhân viên cho cả kỳ sáu tháng, trong khi 1268 là bình quân người/tháng. |

## 43. Tình hình thực hiện nghĩa vụ với ngân sách nhà nước

- **Đã map/xác minh:** ACB p22, MBB p49, VPB p58, HDB p32, CTG p43,
  BID p26 và VIB p47. Đã map 33 khoản mục/147 ô số vào 1269–1279 và kiểm
  tra 37 phương trình cuốn chiếu hoặc đối chiếu phải nộp/phải thu. HDB dùng
  thêm trục tăng do hợp nhất kinh doanh; CTG tách số cuối kỳ thành phải nộp,
  phải thu và số thuần. VPB là nguồn Q1/2026.
- **Không có cụm thuyết minh chi tiết trong báo cáo:** VCB.
- **Còn thiếu:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| HDB | 32 | Tiền thuê đất | Không đồng nhất với 1277 `Thuế nhà - đất`; schema 1269–1279 chưa có leaf riêng. |

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
| Tài sản Có khác | — | ✓ p42 | ✓\* p51–53 | — | — | — | — | ✓\* p39 | 12 dòng OPEN; 58 mapping, 30 phương trình, 5 bank không có bảng chi tiết; VPB là nguồn Q1 |
| Các khoản nợ Chính phủ/NHNN | ✓ p20 | ✓ p42 | ✓\* p53 | ✓ p30 | ✓ p34 | ✓ p41 | ✓ p24 | ✓ p40 | 0 dòng; 32 mapping, 28 phương trình; 2 DASH→0; VPB là nguồn Q1 |
| Vốn nhận tài trợ/ủy thác đầu tư | — | ✓ p43 | ✓\* p56 | — | — | — | — | ✓ p42 | 0 dòng; 6 mapping, 4 phương trình; 5 bank xác nhận không có cụm; VPB là nguồn Q1 |
| Phát hành giấy tờ có giá | ✓ p21 | ✓ p44 | ✓\* p56 | ✓ p31 | ✓ p35 | ✓ p42 | ✓ p25 | ✓ p43 | 3 dòng OPEN; 71 mapping, 36 phương trình; 4 DASH→0; VPB là nguồn Q1 |
| Các khoản phải trả và công nợ khác | ✓\* p22 | ✓ p44 | ✓\* p57 | ✓ p31 | ✓ p35 | ✓\* p43 | ✓ p26 | ✓\* p43 | 18 dòng OPEN; 39 mapping, 28 phương trình; 2 DASH→0; VPB là nguồn Q1 |
| Vốn và các quỹ | ✓ p23–24 | ✓ p44–45 | ✓\* p60–61 | ✓\* p33–34 | ✓\* p36–37 | ✓\* p43–44 | △ p27–28 | △ p44–45 | 10 mục OPEN; 65 mapping, 20 phương trình; BID/VIB structure-only; VPB là nguồn Q1 |
| Thu nhập lãi và các khoản thu nhập tương tự | ✓ p24 | ✓ p46 | ✓\* p62 | ✓ p34 | ✓ p38 | ✓ p45 | ✓ p28 | ✓ p45 | 0 dòng; 54 mapping, 108 ô số, 28 phương trình; VPB là nguồn Q1 |
| Chi phí lãi và các khoản tương tự chi phí lãi | ✓ p24 | ✓ p46 | ✓\* p62 | ✓ p34 | ✓ p39 | ✓ p45 | ✓ p29 | ✓ p45 | 0 dòng; 40 mapping, 80 ô số, 16 phương trình; VPB là nguồn Q1 |
| Thu nhập/chi phí/lãi thuần hoạt động dịch vụ | — | ✓ p46 | ✓\* p62 | — | — | — | — | ✓ p45 | 0 dòng; 43 mapping, 86 ô số, 18 phương trình; 5 bank không có note chi tiết; VPB là nguồn Q1 |
| Lãi/lỗ thuần kinh doanh vàng và ngoại hối | — | ✓ p47 | ✓\* p63 | — | — | — | — | ✓ p46 | 0 dòng; 23 mapping, 46 ô số, 18 phương trình; 5 bank không có note chi tiết; VPB là nguồn Q1 |
| Lãi/lỗ thuần mua bán chứng khoán kinh doanh | ✓ p24 | ✓ p47 | ✓\* p63 | ✓ p34 | ✓ p39 | ✓ p45 | ✓ p29 | — | 0 dòng; 28 mapping, 56 ô số, 14 phương trình; HDB 1 DASH→0; VIB không có note trading chi tiết; VPB là nguồn Q1 |
| Lãi/lỗ thuần mua bán chứng khoán đầu tư | ✓ p25 | ✓ p47 | ✓\* p63 | ✓ p35 | — | ✓ p46 | ✓ p29 | ✓ p46 | 0 dòng; 28 mapping, 56 ô số, 14 phương trình; ACB/MBB 4 DASH→0; VCB không có note chi tiết; VPB là nguồn Q1 |
| Lãi thuần CK kinh doanh + CK đầu tư | — | ✓ p47 | — | — | — | — | — | — | 0 dòng; 1 mapping, 2 ô số, 2 phương trình; 7 PDF không in dòng tổng hợp |
| Thu nhập góp vốn/mua cổ phần/cổ tức | ✓ p25 | ✓ p48 | ✓\* p64 | ✓ p35 | ✓ p39 | ✓ p46 | ✓ p29 | — | 0 dòng; 27 mapping, 54 ô số, 16 phương trình; 5 DASH→0; VIB không có note chi tiết; VPB là nguồn Q1 |
| Chi phí quản lý chung/Chi phí hoạt động | ✓ p25 | ✓ p48 | ✓\* p65 | ✓ p35 | ✓ p40 | ✓\* p47 | ✓ p30 | ✓ p46 | 4 dòng OPEN; 99 mapping, 198 ô số, 30 phương trình; VCB 1 lỗi số VietOCR bị nguồn/pixel bác bỏ; VPB là nguồn Q1 |
| Chi phí dự phòng rủi ro tín dụng | — | ✓ p49 | ✓\* p66 | — | — | — | — | ✓\* p47 | 2 dòng OPEN; 15 mapping, 30 ô số, 8 phương trình; 4 DASH→0; 5 bank không có note chi tiết; VPB là nguồn Q1 |
| Thu nhập/chi phí/lãi thuần hoạt động khác | — | ✓ p47 | ✓\* p64 | — | — | — | — | ✓ p46 | 1 dòng OPEN; 23 mapping, 46 ô số, 14 phương trình; 5 bank không có note chi tiết; VPB là nguồn Q1 |
| Chi phí thuế thu nhập doanh nghiệp | — | ✓ p50 | ✓\* p59 | — | — | — | — | ✓\* p48 | 1 dòng OPEN; 28 mapping, 56 ô số, 20 phương trình; 2 DASH→0, 1 ô trống giữ nguyên; 5 bank không có note chi tiết; VPB là nguồn Q1 |
| Tiền và các khoản tương đương tiền | ✓ p8 | ✓ p50 | ✓\* p66 | — | ✓ p40 | ✓ p47 | — | ✓ p45 | 0 dòng; 31 mapping, 60 ô số, 12 phương trình; 2 ô trống giữ nguyên; HDB/BID không có note chi tiết; VPB là nguồn Q1 |
| Mua mới và thanh lý các công ty con | — | — | — | — | — | — | — | — | 0 dòng; cả 8 PDF không có bảng chi tiết 1255–1258; HDB/CTG có đối chứng giao dịch/cash-flow nhưng thiếu ba dòng bắt buộc |
| Thu nhập nhân viên | ✓\* p26 | — | ✓\* p66 | — | — | — | — | ✓ p49 | 2 dòng ACB OPEN; 13 mapping, 26 ô số, 14 phương trình; 5 bank không có note chi tiết; VPB là nguồn Q1 |
| Nghĩa vụ với ngân sách nhà nước | ✓ p22 | ✓ p49 | ✓\* p58 | ✓\* p32 | — | ✓ p43 | ✓ p26 | ✓ p47 | 1 dòng HDB OPEN; 33 mapping, 147 ô số, 37 phương trình; 13 DASH→0; VCB không có note chi tiết; VPB là nguồn Q1 |
