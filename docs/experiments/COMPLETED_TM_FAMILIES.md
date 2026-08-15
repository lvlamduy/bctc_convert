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
- **Không có vùng thuyết minh chi tiết hoàn chỉnh:** ACB, HDB, VCB, CTG, BID.
  Các PDF này vẫn có dòng tổng trên báo cáo tình hình tài chính hoặc nhắc lại
  trong lưu chuyển tiền tệ/rủi ro/công cụ tài chính; các dòng đó không được ép
  thành bảng phân rã VND–ngoại tệ–vàng.
- **Còn thiếu:** năm bank trên chưa có nguồn chi tiết để map các hàng con 562,
  563 và 565. Đây không phải tuyên bố family tiền/vàng vắng mặt khỏi báo cáo.

| Bank | Trang bằng chứng gần nhất | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| ACB | 3 | Tiền mặt, vàng bạc, đá quý | Chỉ có dòng tổng; không có bảng chi tiết VND/ngoại tệ/vàng. |
| HDB | 3 | Tiền mặt, vàng | Chỉ có dòng tổng; các vùng p39–43 là bảng rủi ro/công cụ tài chính khác family. |
| VCB | 7 | Tiền mặt, vàng bạc, đá quý | Chỉ có dòng tổng; các lần lặp sau thuộc lưu chuyển tiền/rủi ro. |
| CTG | 3 | Tiền mặt, vàng bạc, đá quý | Chỉ có dòng tổng; không có cụm chi tiết đủ trục kỳ/đơn vị/tổng. |
| BID | 4 | Tiền mặt, vàng bạc, đá quý | Chỉ có dòng tổng trên báo cáo tình hình tài chính. |

Ghi chú kỳ: PDF VPB được cung cấp là tại 31/03/2026 nên kết quả VPB giữ đúng
Q1/2026, không relabel thành Q2/2026.

## 2. Tiền gửi tại NHNN

- **Đã xác minh:** MBB p30, VPB p38 và VIB p31. Cả ba cụm được giới hạn từ
  owner đầu cụm qua nhánh `Tiền gửi tại NHNN`, hai hàng `Bằng VND` / `Bằng
  ngoại tệ` đến dòng tổng đầu tiên. Chỉ hai cột kỳ tiền tệ được dùng; bảng tỷ
  lệ dự trữ sau dòng tổng không thuộc cụm này. Đã map 10 dòng và kiểm tra bốn
  phương trình cộng trừ.
- **Không có vùng thuyết minh chi tiết hoàn chỉnh:** ACB, HDB, VCB, CTG, BID.
  Năm PDF vẫn có dòng tổng trên báo cáo tình hình tài chính hoặc các bảng
  thanh khoản/rủi ro gần giống; không ép chúng thành bảng phân rã tiền tệ.
- **Còn thiếu:** MBB có hai dòng địa lý riêng chưa có khoản mục schema tương
  đương. Hai dòng vẫn được giữ trong graph và tham gia phương trình tổng, nhưng
  không bị ép vào `Tiền gửi khác`.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| MBB | 30 | Tiền gửi tại Ngân hàng Nhà nước Lào | Schema hiện chưa có child tiền gửi NHTW theo địa lý tương đương. |
| MBB | 30 | Tiền gửi tại Ngân hàng Quốc gia Campuchia | Cùng khoảng trống schema; không đồng nhất âm thầm với `Tiền gửi khác`. |

Ghi chú kỳ: PDF VPB được cung cấp là tại 31/03/2026 nên kết quả VPB giữ đúng
Q1/2026, không relabel thành Q2/2026.

## 3. Tiền, vàng gửi tại và cho vay/vay các TCTD khác

- **Đã xác minh:** ACB p16, MBB p30, VPB p39, CTG p41, BID p25 và VIB p32.
  Đã map 63 dòng tiền gửi không/có kỳ hạn, VND, ngoại tệ, cho vay/vay, dự
  phòng và chiết khấu/tái chiết khấu; 23 phương trình cha–con, subtotal và tổng
  family đóng đúng. BID dùng biến thể có `vàng và ngoại tệ` và đơn vị triệu VND
  được kế thừa từ công bố đơn vị ở cấp tài liệu. CTG/BID dùng từ `vay` thay cho
  `cho vay`. Dòng chiết khấu/tái chiết khấu chỉ là chi tiết không cộng thêm.
- **Không có vùng thuyết minh chi tiết hoàn chỉnh:** HDB, VCB. Hai PDF có dòng
  tổng hoặc bảng ngoại tệ/giá trị hợp lý gần giống, nhưng không có cụm phân rã
  tiền gửi–vay đủ cha/con, kỳ và subtotal. Đây không phải tuyên bố family vắng
  mặt khỏi toàn bộ báo cáo.
- **Còn thiếu:** HDB và VCB chưa có nguồn chi tiết để map các hàng con. Ba ô dấu
  `-` hiện kỳ của ACB được giữ trạng thái `DASH`, khóa bằng pixel và chuẩn hóa
  thành 0 theo quy ước của chủ dự án.

| Bank | Trang bằng chứng gần nhất | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| HDB | 3 | Tiền gửi tại và cho vay các TCTD khác | Chỉ có dòng tổng; các vùng chi tiết gần nhất là bảng ngoại tệ/rủi ro khác family. |
| VCB | 7 | Tiền gửi tại và cho vay các tổ chức tín dụng khác | Chỉ có dòng tổng; các lần lặp sau thuộc chính sách, giá trị hợp lý hoặc rủi ro. |

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
  VIB có `Chứng khoán đầu tư sẵn sàng để bán` tại p36.
- **Còn thiếu:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VIB | 36 | Chứng khoán đầu tư sẵn sàng để bán | Là subfamily AFS riêng, không được ép vào trading; sẽ xử lý ở lượt securities tiếp theo. |

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
- **Không có:** Không tuyên bố bank nào vắng toàn bộ family phái sinh.
- **Còn thiếu:** VCB có các dòng tổng/chính sách/giá trị hợp lý hoặc kiểm soát
  rủi ro liên quan nhưng whole-PDF scan không tìm thấy một bảng giao dịch phái
  sinh chi tiết đủ hàng con, hai kỳ và trục số để map 632–715.

| Bank | Trang bằng chứng gần nhất | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VCB | 7 và các bảng công cụ tài chính/rủi ro phía sau | Công cụ tài chính phái sinh và tài sản/công nợ tài chính khác | Chỉ có tổng hoặc bề mặt chính sách/giá trị hợp lý/rủi ro; không có vùng giao dịch chi tiết hoàn chỉnh. |

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
  BID p22, VIB p60. Năm nhóm chất lượng nợ đã được map cho cả 8 bank.
- **Không có:** Không có bank nào.
- **Còn thiếu ngoài lõi quality:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map trong family này |
| --- | ---: | --- | --- |
| ACB | 18 | Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán | Là population cộng thêm ngoài năm nhóm chất lượng; giữ source-only để tránh cộng trùng. |
| VPB | 42 | Cho vay giao dịch ký quỹ và ứng trước cho khách hàng | Là population cộng thêm ngoài năm nhóm chất lượng; giữ source-only để tránh cộng trùng. |

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
- **Không có cụm cho vay theo khu vực:** VCB. Vùng p42 là báo cáo bộ phận theo
  khu vực với hàng thu nhập/chi phí, không phải phân tích dư nợ cho vay.
- **Còn thiếu:** ACB, VPB, HDB, CTG và BID có bảng địa lý nhưng trục dư nợ rộng
  hơn `Cho vay khách hàng`; không được thu hẹp ngầm.

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| ACB | 27 | Tổng dư nợ cho vay | Bao gồm cho vay khách hàng và cho vay TCTD khác; lớn hơn owner loan 6.392.840. |
| VPB | 73 | Tổng dư nợ cho vay khách hàng, mua nợ và cấp tín dụng cho các TCTD khác | Population hỗn hợp; lớn hơn owner loan 6.848.104. PDF VPB là Q1/2026. |
| HDB | 37 | Tổng dư nợ cho vay | Footnote gồm cho vay TCTD khác và khách hàng; lớn hơn owner loan 11.439.915. |
| VCB | 42 | Báo cáo bộ phận theo khu vực địa lý | Khác family: hàng thu nhập/chi phí, không có trục dư nợ cho vay khách hàng. |
| CTG | 49 | Tổng dư nợ cho vay | Lớn hơn owner loan 20.241.550. |
| BID | 31 | Tổng dư nợ cho vay | Lớn hơn owner loan 12.677.150. |

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
  BID p25 và VIB p41–42. Đã map 118 dòng loại tiền gửi, VND/ngoại tệ và
  các dòng đối tượng khách hàng đủ chắc; 43 phương trình parent–child, tổng cột
  và tổng bảng đều đóng đúng. ACB dùng biến thể hai khối kỳ theo chiều dọc ×
  ba cột VND/ngoại tệ/tổng; cột tổng chỉ kiểm tra. MBB map `Tiền gửi của TCKT`
  vào 1084 và `Tiền gửi của cá nhân` vào 1089; `Tiền gửi vốn chuyên dùng`
  không tách tiền tệ được đưa vào VND theo quyết định của chủ dự án. VIB nối
  bảng đối tượng ở trang 42 và giữ nhánh tiết kiệm là subset không cộng trùng.
- **Không có:** Không có bank nào.
- **Còn thiếu:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| VPB | 55 | Công ty TNHH 2 thành viên trở lên có phần vốn góp của Nhà nước trên 50% | Schema 1079 hiện chỉ mô tả Công ty TNHH một thành viên; không ép hai khái niệm khác nhau. |
| VIB | 42 | Công ty TNHH 2 thành viên trở lên có phần vốn góp của Nhà nước trên 50% | Cùng khoảng trống schema như VPB; giữ UNRESOLVED. |

Ghi chú kỳ: PDF VPB được cung cấp là tại 31/03/2026 nên kết quả VPB giữ đúng
Q1/2026, không relabel thành Q2/2026.

## Bảng tổng hợp

Ký hiệu: **✓** đã map/xác minh; **—** không có vùng family tương ứng; **△** đã
thấy vùng nguồn nhưng chưa map; **✓\*** đã map phần mục tiêu, còn hàng ngoài lõi
hoặc group parent chỉ giữ để kiểm tra.

| Cụm | ACB | MBB | VPB | HDB | VCB | CTG | BID | VIB | Còn chưa map |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Tiền, kim loại quý, đá quý | — tổng p3 | ✓ p30 | ✓\* p38 | — tổng p3 | — tổng p7 | — tổng p3 | — tổng p4 | ✓ p31 | 5 bank không có bảng chi tiết; VPB là nguồn Q1 |
| Tiền gửi tại NHNN | — tổng p3 | ✓\* p30 | ✓\* p38 | — tổng p3 | — tổng p7 | — tổng p3 | — tổng p4 | ✓ p31 | 2 dòng địa lý MBB; 5 bank không có bảng chi tiết; VPB là nguồn Q1 |
| Tiền gửi/vay TCTD khác | ✓ p16 | ✓ p30 | ✓\* p39 | — tổng p3 | — tổng p7 | ✓ p41 | ✓ p25 | ✓ p32 | 2 bank không có bảng chi tiết; VPB là nguồn Q1 |
| Chứng khoán kinh doanh | ✓ p16 | ✓ p31 | ✓\* p40 | ✓ p24 | ✓ p30 | ✓ p37 | ✓ p20 | △ AFS p36 | 1 subfamily AFS; VPB là nguồn Q1 |
| Công cụ tài chính phái sinh | ✓ p17 | ✓ p43 | ✓\* p41 | ✓ p25 | △ tổng/chính sách | ✓ p38 | ✓ p21 | ✓ p32 | VCB thiếu bảng giao dịch chi tiết; VPB là nguồn Q1 |
| Loại hình cho vay | ✓ p17 | ✓ p31 | ✓ p42 | ✓ p26 | ✓ p30 | ✓ p38 | ✓ p22 | ✓ p33 | 0 |
| Ngành nghề kinh doanh | — | ✓ p33 | ✓ p44 | ✓ p27 | — | — | ✓ p22 | ✓ p33 | 0 trong 5 vùng; 3 bank không có |
| Chất lượng cho vay | ✓\* p18 | ✓ p31 | ✓\* p42 | ✓ p26 | ✓ p30 | ✓ p39 | ✓ p22 | ✓ p60 | 2 population ngoài lõi |
| Dư nợ theo thời gian | ✓ p18 | ✓ p31 | ✓ p42 | ✓ p26 | ✓ p31 | ✓ p39 | ✓ p22 | ✓ p33 | 0 khoản mục mục tiêu |
| Cho vay theo loại tiền tệ | — p17–18 | — p31–33 | — p42–44 | — p26–27 | — p30–31 | — p38–39 | — p22 | — p33–34 | 0; family không có trong 8 PDF cố định |
| Cho vay theo khu vực địa lý | △ p27 | ✓ p52 | △ p73 | △ p37 | — segment p42 | △ p49 | △ p31 | ✓ p53–54 | 5 trục dư nợ rộng hơn; VCB không có cụm loan-geography |
| Doanh nghiệp/đối tượng KH | — | ✓\* p32 | ✓ p43 | ✓ p26 | — | — | — | ✓ p34 | 1 group parent check-only |
| Dự phòng cho vay | ✓ p18 | ✓ p34 | ✓\* p45 | ✓ p28 | ✓ p31 | ✓ p39 | ✓ p23 | ✓ p34 | 0 dòng; VPB còn thiếu nguồn Q2 |
| Hoạt động mua nợ | — | ✓ p35 | ✓\* p46 | ✓ p29 | — | — | — | ✓\* p35 | 0 dòng; 4 bank không có; VPB là nguồn Q1 |
| Tiền gửi khách hàng | ✓ p21 | ✓ p43 | ✓\* p55 | ✓ p31 | ✓ p35 | ✓ p42 | ✓ p25 | ✓\* p41–42 | 2 dòng TNHH cùng một khoảng trống schema; VPB là nguồn Q1 |
