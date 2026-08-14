# Tình trạng các cụm thuyết minh trên 8 ngân hàng

Phạm vi: ACB, MBB, VPB, HDB, VCB, CTG, BID, VIB.

Quy ước:

- **Đã xác minh**: các khoản mục mục tiêu đã được map và kiểm tra lại.
- **Không có**: báo cáo trong phạm vi này không trình bày family tương ứng.
- **Còn thiếu**: đã thấy vùng nguồn nhưng chưa đủ điều kiện map.
- Dòng tổng hoặc subtotal chỉ dùng để kiểm tra cộng trừ không được tính là khoản
  mục còn thiếu map.

## 1. Phân tích dư nợ theo thời gian/thời hạn gốc

- **Đã xác minh:** ACB p18, MBB p31, VPB p42, HDB p26, VCB p31, CTG p39,
  BID p22, VIB p33. Ba hàng `Nợ ngắn hạn`, `Nợ trung hạn`, `Nợ dài hạn`
  đã được map cho cả 8 bank; hai hàng margin hợp lệ của MBB và VPB cũng đã
  được map.
- **Không có:** Không có bank nào.
- **Còn thiếu:** Không còn khoản mục mục tiêu chưa map. Các dòng tổng vẫn là
  dòng kiểm tra nguồn, không map thành khoản mục chi tiết.

## 2. Phân tích chất lượng cho vay

- **Đã xác minh:** ACB p18, MBB p31, VPB p42, HDB p26, VCB p30, CTG p39,
  BID p22, VIB p60. Năm nhóm chất lượng nợ đã được map cho cả 8 bank.
- **Không có:** Không có bank nào.
- **Còn thiếu ngoài lõi quality:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map trong family này |
| --- | ---: | --- | --- |
| ACB | 18 | Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán | Là population cộng thêm ngoài năm nhóm chất lượng; giữ source-only để tránh cộng trùng. |
| VPB | 42 | Cho vay giao dịch ký quỹ và ứng trước cho khách hàng | Là population cộng thêm ngoài năm nhóm chất lượng; giữ source-only để tránh cộng trùng. |

## 3. Phân tích theo loại hình cho vay

- **Đã xác minh:** ACB p17, MBB p31, VPB p42, HDB p26, VCB p30, CTG p38,
  BID p22, VIB p33. Tổng cộng 46 khoản mục nguồn đã được map; gồm ACB
  `Cho vay theo chỉ định của Chính phủ` và VPB `Cấp tín dụng khác`.
- **Không có:** Không có bank nào. ACB, VCB, CTG và BID là biến thể không có
  tiêu đề family riêng nhưng các hàng con nằm trực tiếp dưới `Cho vay khách hàng`.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong các vùng đã xác minh.

## 4. Phân tích cho vay theo ngành nghề kinh doanh

- **Đã xác minh:** MBB p33, VPB p44, HDB p27, BID p22, VIB p33; tổng cộng
  80 khoản mục nguồn đã được map.
- **Không có trong báo cáo:** ACB, VCB, CTG.
- **Còn thiếu:** Không còn khoản mục nguồn chưa map trong năm vùng được tìm
  thấy. Các quyết định đã gồm `Vận tải kho bãi` → 736, population chi nhánh
  nước ngoài → 6058, khoản vay mua nhà ở cá nhân → khoản mục schema riêng,
  `Dịch vụ` của BID → khoản mục schema riêng, và các ngành nhỏ phù hợp → 745.

## 5. Phân tích theo loại hình doanh nghiệp/đối tượng khách hàng

- **Đã xác minh:** MBB p32, VPB p43, HDB p26, VIB p34; 44 khoản mục nguồn
  đã được map. `Cho vay cá nhân` tương đương không cộng thêm với 780,
  `Cho vay khác` tương đương không cộng thêm với 782, và population chi nhánh
  nước ngoài dùng 6058.
- **Không có vùng enterprise/customer-type hoàn chỉnh:** ACB, VCB, CTG, BID.
  Các hàng không tiêu đề của bốn bank này thuộc family loại hình cho vay và đã
  được xử lý ở mục 3; không ép sang family doanh nghiệp.
- **Còn thiếu:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| MBB | 32 | Cho vay các TCKT | Giữ làm group parent để kiểm tra tổng các hàng con; chưa xuất thêm một mapping cộng dồn nhằm tránh double count. |

## 6. Dự phòng rủi ro cho vay khách hàng

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

## 7. Tiền gửi của khách hàng — phân loại theo loại/kỳ hạn/đối tượng

- **Đã xác minh:** Chưa có khoản mục schema nào được xác minh; đã tìm đúng
  vùng nguồn và kiểm tra tổng cấp cao cho 8/8 bank.
- **Không có:** Không có bank nào.
- **Còn thiếu:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| ACB | 21 | Tiền gửi của khách hàng | Kỳ trình bày theo chiều dọc, có nhiều lane tiền tệ và nhánh tiết kiệm lồng nhau. |
| MBB | 43 | Thuyết minh theo loại tiền gửi | Có các nhánh VND/ngoại tệ và phân nhóm đối tượng; chưa khóa graph lồng nhau. |
| VPB | 55 | Tiền gửi của khách hàng | Cùng trang có cả loại tiền gửi và đối tượng/loại hình doanh nghiệp; cần tách hai nhánh không cộng trùng. |
| HDB | 31 | Tiền gửi của khách hàng | Có parent không kỳ hạn/có kỳ hạn và các child VND/ngoại tệ; chưa map hierarchy. |
| VCB | 35 | Tiền gửi của khách hàng | Có các nhánh VND, vàng/ngoại tệ và nhiều cấp subtotal; chưa map hierarchy. |
| CTG | 42 | Tiền, vàng gửi không kỳ hạn/có kỳ hạn | Có tiền/vàng, VND/ngoại tệ và các subtotal lồng nhau; chưa map. |
| BID | 25 | Tiền, vàng gửi không kỳ hạn/có kỳ hạn | Thiếu đơn vị cục bộ và có hierarchy nhiều cấp; cần authority đơn vị kế thừa. |
| VIB | 41 | Thuyết minh theo loại hình tiền gửi | Có nhánh tiết kiệm và VND/ngoại tệ lồng nhau; chưa map. |

## 8. Chứng khoán

- **Đã xác minh:** Chưa có khoản mục schema nào được xác minh; đã tìm được
  vùng nguồn cho 8/8 bank.
- **Không có:** VIB không có `Chứng khoán kinh doanh` trong phạm vi nguồn đã
  kiểm tra, nhưng có `Chứng khoán đầu tư sẵn sàng để bán` tại p36. Vì vậy VIB
  không được coi là không có family chứng khoán nói chung.
- **Còn thiếu:**

| Bank | Trang | Khoản mục nguồn | Lý do chưa map |
| --- | ---: | --- | --- |
| ACB | 16 | Chứng khoán kinh doanh | Chưa có graph chung cho loại chứng khoán, gross, dự phòng và net. |
| MBB | 31 | Chứng khoán kinh doanh | Có cấu trúc niêm yết/chưa niêm yết và dự phòng; chưa map nhánh thay thế. |
| VPB | 40 | Chứng khoán kinh doanh | Có snapshot và roll-forward dự phòng trên cùng vùng; chưa tách quan hệ không cộng trùng. |
| HDB | 24 | Chứng khoán kinh doanh | Có nhiều loại chứng khoán và dự phòng chung/cụ thể; chưa khóa graph tổng quát. |
| VCB | 30 | Chứng khoán kinh doanh | Có các nhánh issuer và dự phòng giảm giá; chưa map hierarchy. |
| CTG | 37 | Chứng khoán kinh doanh | Có các nhánh loại chứng khoán, khoản khác và dự phòng; chưa map hierarchy. |
| BID | 20 | Chứng khoán kinh doanh | Có các nhánh loại chứng khoán và dự phòng rủi ro; chưa map hierarchy. |
| VIB | 36 | Chứng khoán đầu tư sẵn sàng để bán | Là biến thể AFS thay vì trading; cần graph securities cho các branch thay thế trước khi map. |

## Bảng tổng hợp

Ký hiệu: **✓** đã map/xác minh; **—** không có vùng family tương ứng; **△** đã
thấy vùng nguồn nhưng chưa map; **✓\*** đã map phần mục tiêu, còn hàng ngoài lõi
hoặc group parent chỉ giữ để kiểm tra.

| Cụm | ACB | MBB | VPB | HDB | VCB | CTG | BID | VIB | Còn chưa map |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dư nợ theo thời gian | ✓ p18 | ✓ p31 | ✓ p42 | ✓ p26 | ✓ p31 | ✓ p39 | ✓ p22 | ✓ p33 | 0 khoản mục mục tiêu |
| Chất lượng cho vay | ✓\* p18 | ✓ p31 | ✓\* p42 | ✓ p26 | ✓ p30 | ✓ p39 | ✓ p22 | ✓ p60 | 2 population ngoài lõi |
| Loại hình cho vay | ✓ p17 | ✓ p31 | ✓ p42 | ✓ p26 | ✓ p30 | ✓ p38 | ✓ p22 | ✓ p33 | 0 |
| Ngành nghề kinh doanh | — | ✓ p33 | ✓ p44 | ✓ p27 | — | — | ✓ p22 | ✓ p33 | 0 trong 5 vùng; 3 bank không có |
| Doanh nghiệp/đối tượng KH | — | ✓\* p32 | ✓ p43 | ✓ p26 | — | — | — | ✓ p34 | 1 group parent check-only |
| Dự phòng cho vay | ✓ p18 | ✓ p34 | ✓\* p45 | ✓ p28 | ✓ p31 | ✓ p39 | ✓ p23 | ✓ p34 | 0 dòng; VPB còn thiếu nguồn Q2 |
| Tiền gửi khách hàng | △ p21 | △ p43 | △ p55 | △ p31 | △ p35 | △ p42 | △ p25 | △ p41 | 8 vùng chưa map |
| Chứng khoán | △ p16 | △ p31 | △ p40 | △ p24 | △ p30 | △ p37 | △ p20 | △ AFS p36 | 8 vùng chưa map |
